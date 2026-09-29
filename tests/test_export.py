import csv
import io

from labexplain.export import to_csv, to_pdf
from labexplain.models import LabRow, MatchedRow, ReportResult


def _sample_result():
    rows = [
        MatchedRow(
            row=LabRow(raw_text="x", test_name="Glucose", value=140, unit="mg/dL"),
            test_id="glucose",
            display_name="Glucose",
            value=140,
            unit="mg/dL",
            low=65,
            high=99,
            status="high",
            source_lab="LabCorp",
            source_url="https://example.com/glucose",
            explanation="Glucose measures blood sugar. Discuss this result with a doctor or other clinician.",
        ),
        MatchedRow(
            row=LabRow(raw_text="y", test_name="Sodium", value=140, unit="mmol/L"),
            test_id="sodium",
            display_name="Sodium",
            value=140,
            unit="mmol/L",
            low=136,
            high=145,
            status="normal",
            source_lab="Quest",
            source_url="https://example.com/sodium",
        ),
    ]
    return ReportResult(rows=rows, warnings=["1 row(s) were not matched"], extraction_method="pdf-text")


def test_to_csv_contains_banner_and_rows():
    text = to_csv(_sample_result())
    assert "Educational only" in text
    reader = csv.reader(io.StringIO(text))
    lines = list(reader)
    assert lines[0][0].startswith("# Educational only")
    header = lines[1]
    assert header == ["test", "value", "unit", "status", "low", "high", "source_lab", "source_url"]
    body_rows = lines[2:]
    assert any(r[0] == "Glucose" and r[3] == "high" for r in body_rows)


def test_to_pdf_writes_a_file(tmp_path):
    out = tmp_path / "report.pdf"
    to_pdf(_sample_result(), str(out))
    assert out.exists()
    assert out.stat().st_size > 500
    assert out.read_bytes().startswith(b"%PDF")


def test_csv_escapes_spreadsheet_formula():
    result = _sample_result()
    result.rows[0].display_name = "=1+1"
    lines = list(csv.reader(io.StringIO(to_csv(result))))
    assert lines[2][0] == "'=1+1"
