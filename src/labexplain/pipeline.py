"""End to end: file in, ReportResult out. Shared by the CLI and the web app."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from labexplain.config import Config
from labexplain.explain import ExplainError, explain_row
from labexplain.models import ReportResult
from labexplain.ocr import OCR_PROMPT, BackendUnavailable, pick
from labexplain.parser import parse
from labexplain.pdfextract import extract_text_layer, render_pages_to_images
from labexplain.reference import match_rows

logger = logging.getLogger("labexplain")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def analyze_file(
    path: Path,
    cfg: Config,
    sex: str | None = None,
    explain: bool = True,
    ocr_backend_name: str | None = None,
) -> ReportResult:
    path = Path(path)
    warnings: list[str] = []
    extraction_method: str | None = None
    ocr_backend_used: str | None = None
    text_chunks: list[str] = []

    if path.suffix.lower() == ".pdf":
        text = extract_text_layer(path)
        if text is not None:
            extraction_method = "pdf-text"
            text_chunks = [text]
        else:
            backend = pick(cfg, ocr_backend_name)
            ocr_backend_used = backend.name
            extraction_method = backend.name
            with tempfile.TemporaryDirectory() as td:
                images = render_pages_to_images(path, Path(td))
                for image in images:
                    text_chunks.append(backend.recognize(image, OCR_PROMPT, cfg.max_ocr_tokens))
    elif path.suffix.lower() in IMAGE_SUFFIXES:
        backend = pick(cfg, ocr_backend_name)
        ocr_backend_used = backend.name
        extraction_method = backend.name
        text_chunks.append(backend.recognize(path, OCR_PROMPT, cfg.max_ocr_tokens))
    else:
        raise ValueError(f"unsupported file type '{path.suffix}'. Use a PDF or an image (png, jpg).")

    rows = []
    for chunk in text_chunks:
        rows.extend(parse(chunk))
    if not rows:
        warnings.append("no test rows were recognized in this file. Try a clearer photo or a text PDF.")

    matched, match_warnings = match_rows(rows, sex)
    warnings.extend(match_warnings)

    unmatched_count = sum(1 for m in matched if m.status == "unmatched")
    if unmatched_count:
        warnings.append(f"{unmatched_count} row(s) have no usable reference range and are shown without a flag.")

    result = ReportResult(
        rows=matched,
        warnings=warnings,
        ocr_backend=ocr_backend_used,
        extraction_method=extraction_method,
    )

    if explain:
        for m in result.flagged():
            if m.test_id is None:
                continue
            try:
                m.explanation = explain_row(m, cfg)
            except (ExplainError, BackendUnavailable) as exc:
                logger.warning("explanation failed for %s: %s", m.display_name, exc)
                result.warnings.append(f"could not generate an explanation for {m.display_name}")

    return result
