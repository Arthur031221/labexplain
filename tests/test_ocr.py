from unittest.mock import patch

from labexplain.config import Config
from labexplain.ocr import BackendUnavailable, make, pick
from labexplain.ocr.ollama import OllamaBackend


def test_make_unknown_backend_raises():
    try:
        make("nonsense", Config())
        raise AssertionError("expected BackendUnavailable")
    except BackendUnavailable:
        pass


def test_ollama_status_when_unreachable():
    backend = OllamaBackend("glm-ocr:q8_0", url="http://127.0.0.1:1")
    ready, detail = backend.status()
    assert ready is False
    assert "not reachable" in detail or "Ollama" in detail


def test_pick_raises_when_nothing_ready():
    cfg = Config(ocr_backend="auto")
    with (
        patch("labexplain.ocr.is_apple_silicon", return_value=False),
        patch.object(OllamaBackend, "status", return_value=(False, "not pulled")),
    ):
        try:
            pick(cfg)
            raise AssertionError("expected BackendUnavailable")
        except BackendUnavailable as exc:
            assert "no OCR backend is ready" in str(exc)


def test_pick_explicit_backend_name_bypasses_auto():
    cfg = Config()
    backend = make("ollama", cfg)
    assert backend.name == "ollama"
