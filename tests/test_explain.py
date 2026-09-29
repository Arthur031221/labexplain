import json
from unittest.mock import patch

from labexplain.config import Config
from labexplain.explain import CLINICIAN_LINE, ExplainError, build_prompt, explain_row
from labexplain.models import LabRow, MatchedRow


def _row(status="high"):
    return MatchedRow(
        row=LabRow(raw_text="x", test_name="Glucose", value=140, unit="mg/dL"),
        test_id="glucose",
        display_name="Glucose",
        value=140,
        unit="mg/dL",
        low=65,
        high=99,
        status=status,
        source_lab="LabCorp",
        source_url="https://example.com",
    )


def test_build_prompt_contains_no_diagnosis_instruction():
    prompt = build_prompt(_row())
    assert "Glucose" in prompt
    assert "Do not diagnose" in prompt


class _FakeResponse:
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_explain_row_appends_clinician_line_when_missing():
    fake = _FakeResponse({"message": {"content": "This measures blood sugar."}})
    with patch("urllib.request.urlopen", return_value=fake):
        text = explain_row(_row(), Config())
    assert CLINICIAN_LINE in text
    assert "measures blood sugar" in text


def test_explain_row_does_not_duplicate_clinician_line():
    content = f"This measures blood sugar. {CLINICIAN_LINE}"
    fake = _FakeResponse({"message": {"content": content}})
    with patch("urllib.request.urlopen", return_value=fake):
        text = explain_row(_row(), Config())
    assert text.count("Discuss this result") == 1


def test_explain_row_raises_on_ollama_error():
    fake = _FakeResponse({"error": "model not found"})
    with patch("urllib.request.urlopen", return_value=fake):
        try:
            explain_row(_row(), Config())
            raise AssertionError("expected ExplainError")
        except ExplainError:
            pass


def test_explain_row_raises_when_unreachable():
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        try:
            explain_row(_row(), Config())
            raise AssertionError("expected ExplainError")
        except ExplainError:
            pass
