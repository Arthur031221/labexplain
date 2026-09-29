"""PDF handling: use the text layer when the PDF has one, otherwise render
pages to images for OCR.
"""

from __future__ import annotations

from pathlib import Path

from labexplain.parser import parse

MIN_TEXT_LAYER_CHARS = 80


def extract_text_layer(pdf_path: Path) -> str | None:
    """Return the PDF's embedded text if it looks substantial, else None."""
    import fitz

    doc = fitz.open(pdf_path)
    try:
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    if len(text.strip()) >= MIN_TEXT_LAYER_CHARS or parse(text):
        return text
    return None


def render_pages_to_images(pdf_path: Path, out_dir: Path, dpi: int = 200) -> list[Path]:
    """Rasterize every page to a PNG for OCR. Used when there is no text layer."""
    import fitz

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    paths = []
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_path = out_dir / f"page-{i + 1}.png"
            pix.save(str(out_path))
            paths.append(out_path)
    finally:
        doc.close()
    return paths
