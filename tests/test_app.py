from fastapi.testclient import TestClient

from labexplain.app import app

client = TestClient(app)


def test_index_shows_banner():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Educational only" in resp.text
    assert "Analyze" in resp.text


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_and_export(tmp_path, flat_entry, make_pdf):
    high = flat_entry["range"]["high"]
    pdf = make_pdf(tmp_path / "r.pdf", [f"{flat_entry['name']} {high + 1000} {flat_entry['unit']}"])
    with open(pdf, "rb") as fh:
        resp = client.post(
            "/analyze",
            files={"file": ("r.pdf", fh, "application/pdf")},
            data={"sex": "", "explain": ""},
        )
    assert resp.status_code == 200
    assert "Educational only" in resp.text
    assert flat_entry["name"] in resp.text
    assert "/export/" in resp.text

    start = resp.text.index("/export/")
    report_id = resp.text[start + len("/export/") : start + len("/export/") + 32]

    csv_resp = client.get(f"/export/{report_id}.csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]

    pdf_resp = client.get(f"/export/{report_id}.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")


def test_analyze_rejects_bad_extension(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hi")
    with open(bad, "rb") as fh:
        resp = client.post("/analyze", files={"file": ("notes.txt", fh, "text/plain")})
    assert resp.status_code == 400
    assert "PDF" in resp.text


def test_export_missing_report_returns_404():
    resp = client.get("/export/doesnotexist.csv")
    assert resp.status_code == 404


def test_analyze_rejects_oversized_upload():
    resp = client.post(
        "/analyze",
        files={"file": ("large.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert resp.status_code == 413
