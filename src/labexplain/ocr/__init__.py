"""OCR backends behind one small interface.

A backend turns an image file into raw text describing a lab report page.
This mirrors the backend split used in snipmd: MLX in process on Apple
Silicon when the model is already cached, Ollama over HTTP as the portable
fallback. The pipeline handles image preparation and row parsing, so
backends stay thin.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Protocol

from labexplain.config import Config

# GLM-OCR is prompted per task. Lab reports are tabular, so "Table
# Recognition:" asks the model for a markdown table, which the parser reads
# with the same pipe-delimited logic it uses for any other table.
OCR_PROMPT = "Table Recognition:"


class BackendError(RuntimeError):
    """The backend exists but failed (model missing, server down, bad output)."""


class BackendUnavailable(BackendError):
    """The backend cannot run on this machine or is not set up."""


class Backend(Protocol):
    name: str

    def status(self) -> tuple[bool, str]:
        """Return (ready, human readable detail) without loading the model."""
        ...

    def load(self) -> None:
        """Load weights or check the server. Safe to call more than once."""
        ...

    def recognize(self, image: Path, prompt: str, max_tokens: int) -> str: ...


def is_apple_silicon() -> bool:
    return sys.platform == "darwin" and platform.machine() == "arm64"


def make(name: str, cfg: Config) -> Backend:
    if name == "mlx":
        from labexplain.ocr.mlx import MlxBackend

        return MlxBackend(cfg.mlx_model)
    if name == "ollama":
        from labexplain.ocr.ollama import OllamaBackend

        return OllamaBackend(cfg.ollama_ocr_model, cfg.ollama_url)
    raise BackendUnavailable(f"unknown OCR backend '{name}'. Use mlx, ollama or auto.")


def pick(cfg: Config, name: str | None = None) -> Backend:
    """Resolve ``auto`` to a concrete backend.

    Order: MLX with the model already downloaded, then Ollama with the model
    already pulled. Only one model process runs at a time on this machine,
    so we never load both.
    """
    name = name or cfg.ocr_backend
    if name != "auto":
        return make(name, cfg)

    reasons = []
    mlx = make("mlx", cfg) if is_apple_silicon() else None
    if mlx is not None:
        ready, detail = mlx.status()
        if ready:
            return mlx
        reasons.append(f"mlx: {detail}")
    else:
        reasons.append("mlx: needs a Mac with Apple Silicon")

    ollama = make("ollama", cfg)
    ready, detail = ollama.status()
    if ready:
        return ollama
    reasons.append(f"ollama: {detail}")

    raise BackendUnavailable(
        "no OCR backend is ready.\n  "
        + "\n  ".join(reasons)
        + f"\nFix one of them, for example `ollama pull {cfg.ollama_ocr_model}`."
    )
