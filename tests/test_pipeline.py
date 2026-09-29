from unittest.mock import patch

from labexplain.config import Config
from labexplain.pipeline import analyze_file


def test_analyze_pdf_text_layer(tmp_path, flat_entry, make_pdf):
    high = flat_entry["range"]["high"]
    pdf = make_pdf(
        tmp_path / "report.pdf",
        [
            f"{flat_entry['name']} {high + 1000} {flat_entry['unit']}",
            "Made Up Test 12 foo",
        ],
    )
    result = analyze_file(pdf, Config(), explain=False)
    assert result.extraction_method == "pdf-text"
    assert any(r.test_id == flat_entry["id"] for r in result.rows)
    matched = next(r for r in result.rows if r.test_id == flat_entry["id"])
    assert matched.status in ("high", "critical_high")
    assert any(r.test_id is None for r in result.rows)


def test_analyze_pdf_without_text_layer_uses_ocr_backend(tmp_path, flat_entry):
    from reportlab.pdfgen import canvas

    # A near-blank PDF: no meaningful text layer, so the pipeline must fall
    # back to rendering pages and calling the (mocked) OCR backend.
    path = tmp_path / "scanned.pdf"
    c = canvas.Canvas(str(path), pagesize=(200, 200))
    c.showPage()
    c.save()

    class FakeBackend:
        name = "mlx"

        def recognize(self, image, prompt, max_tokens):
            return f"{flat_entry['name']} {flat_entry['range']['low']} {flat_entry['unit']}"

    with patch("labexplain.pipeline.pick", return_value=FakeBackend()):
        result = analyze_file(path, Config(), explain=False)

    assert result.extraction_method == "mlx"
    assert result.ocr_backend == "mlx"
    assert any(r.test_id == flat_entry["id"] for r in result.rows)


def test_analyze_image_uses_ocr_backend(tmp_path, flat_entry):
    from PIL import Image

    img_path = tmp_path / "photo.png"
    Image.new("RGB", (10, 10), color="white").save(img_path)

    class FakeBackend:
        name = "ollama"

        def recognize(self, image, prompt, max_tokens):
            mid = (flat_entry["range"]["low"] + flat_entry["range"]["high"]) / 2
            return f"{flat_entry['name']} {mid} {flat_entry['unit']}"

    with patch("labexplain.pipeline.pick", return_value=FakeBackend()):
        result = analyze_file(img_path, Config(), explain=False)

    assert result.extraction_method == "ollama"
    matched = next(r for r in result.rows if r.test_id == flat_entry["id"])
    assert matched.status == "normal"


def test_analyze_unsupported_file_type(tmp_path):
    path = tmp_path / "report.txt"
    path.write_text("hello")
    try:
        analyze_file(path, Config())
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_analyze_calls_explain_only_for_flagged_rows(tmp_path, flat_entry, make_pdf):
    high = flat_entry["range"]["high"]
    pdf_lines = [f"{flat_entry['name']} {high + 1000} {flat_entry['unit']}"]
    pdf = make_pdf(tmp_path / "report.pdf", pdf_lines)

    calls = []

    def fake_explain(row, cfg):
        calls.append(row.display_name)
        return "a plain explanation. Discuss this result with a doctor or other clinician."

    with patch("labexplain.pipeline.explain_row", side_effect=fake_explain):
        result = analyze_file(pdf, Config(), explain=True)

    assert calls == [flat_entry["name"]]
    flagged = result.flagged()
    assert flagged and flagged[0].explanation
