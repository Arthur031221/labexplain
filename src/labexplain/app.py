"""FastAPI app: one page, upload a report, see matched values and notes."""

from __future__ import annotations

import html
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from labexplain import BANNER, __version__
from labexplain.config import load
from labexplain.export import to_csv, to_pdf
from labexplain.models import ReportResult
from labexplain.ocr import BackendError, BackendUnavailable
from labexplain.pipeline import IMAGE_SUFFIXES, analyze_file

logger = logging.getLogger("labexplain.app")

app = FastAPI(title="labexplain", version=__version__)

_REPORTS: dict[str, ReportResult] = {}
_MAX_REPORTS = 50
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

STYLE = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, "Segoe UI", sans-serif; max-width: 900px; margin: 0 auto;
  padding: 0 1.25rem 3rem; line-height: 1.45; }
.banner { background: #b3261e; color: #fff; padding: 0.6rem 1rem; margin: 0 -1.25rem 1.5rem;
  font-weight: 600; text-align: center; }
h1 { margin-top: 1.5rem; }
.sub { color: #666; margin-top: -0.5rem; }
form.upload { border: 1px dashed #999; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0; }
form.upload label { display: block; margin-bottom: 0.6rem; }
input[type=submit], .btn { background: #222; color: #fff; border: none; padding: 0.5rem 1rem;
  border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.92rem; }
th, td { border: 1px solid #ccc; padding: 0.4rem 0.55rem; text-align: left; }
th { background: #f0f0f0; }
tr.status-high td.status { color: #a11; font-weight: 700; }
tr.status-low td.status { color: #b06a00; font-weight: 700; }
tr.status-unmatched td.status { color: #777; }
.notes { margin-top: 1.5rem; }
.notes .note { background: #f7f2e8; border-left: 4px solid #b3261e; padding: 0.6rem 0.9rem;
  margin-bottom: 0.7rem; }
.warnings { color: #a15c00; margin-top: 1rem; }
.exports { margin: 1rem 0; }
.exports a { margin-right: 0.75rem; }
footer { margin-top: 2.5rem; color: #888; font-size: 0.85rem; }
"""


def _page(body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>labexplain</title>
<style>{STYLE}</style>
</head>
<body>
<div class="banner">{html.escape(BANNER)}</div>
{body}
<footer>labexplain v{__version__}. Runs on this machine with the default local Ollama URL.</footer>
</body>
</html>"""


def _upload_form(error: str | None = None) -> str:
    error_html = f'<p style="color:#a11">{html.escape(error)}</p>' if error else ""
    return f"""
<h1>labexplain</h1>
<p class="sub">Read a blood test PDF or photo. The report's printed intervals take priority.
Other rows use a cited adult example only when the test name and unit match.</p>
{error_html}
<form class="upload" action="/analyze" method="post" enctype="multipart/form-data">
  <label>Report file (PDF, PNG or JPG)
    <input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg" required>
  </label>
  <label>Sex (optional, narrows sex specific ranges like hemoglobin)
    <select name="sex">
      <option value="">Not specified</option>
      <option value="female">Female</option>
      <option value="male">Male</option>
    </select>
  </label>
  <label><input type="checkbox" name="explain" checked style="width:auto;display:inline">
    Generate plain-English notes for flagged values (uses the local Ollama model)</label>
  <input type="submit" value="Analyze">
</form>
"""


def _results_html(report_id: str, result: ReportResult) -> str:
    rows_html = []
    for m in result.rows:
        range_text = "-" if m.low is None and m.high is None else f"{m.low}-{m.high}"
        if m.source_url:
            label = html.escape(m.source_lab or "source")
            url = html.escape(m.source_url)
            source = f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'
        else:
            source = html.escape(m.source_lab or "-")
        rows_html.append(
            f'<tr class="status-{m.status}">'
            f"<td>{html.escape(m.display_name)}</td>"
            f'<td class="status">{m.status.replace("_", " ")}</td>'
            f"<td>{'' if m.value is None else m.value}</td>"
            f"<td>{html.escape(m.unit or '-')}</td>"
            f"<td>{html.escape(range_text)}</td>"
            f"<td>{source}</td>"
            "</tr>"
        )

    notes_html = ""
    flagged = result.flagged()
    if flagged:
        notes = "".join(
            f'<div class="note"><b>{html.escape(m.display_name)}</b>: '
            f"{html.escape(m.explanation) if m.explanation else 'no explanation generated for this value.'}</div>"
            for m in flagged
        )
        notes_html = f'<div class="notes"><h2>Notes on flagged values</h2>{notes}</div>'

    warnings_html = ""
    if result.warnings:
        items = "".join(f"<li>{html.escape(w)}</li>" for w in result.warnings)
        warnings_html = f'<div class="warnings"><ul>{items}</ul></div>'

    return f"""
<h1>Report results</h1>
<p class="sub">Extraction: {html.escape(result.extraction_method or "unknown")}
{" via " + html.escape(result.ocr_backend) if result.ocr_backend else ""}</p>
<div class="exports">
  <a class="btn" href="/export/{report_id}.csv">Download CSV</a>
  <a class="btn" href="/export/{report_id}.pdf">Download PDF</a>
  <a class="btn" href="/">New report</a>
</div>
<table>
<tr><th>Test</th><th>Status</th><th>Value</th><th>Unit</th><th>Reference range</th><th>Source</th></tr>
{"".join(rows_html) if rows_html else '<tr><td colspan="6">No test rows were recognized.</td></tr>'}
</table>
{notes_html}
{warnings_html}
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _page(_upload_form())


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    file: Annotated[UploadFile, File()],
    sex: Annotated[str, Form()] = "",
    explain: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".pdf" and suffix not in IMAGE_SUFFIXES:
        return HTMLResponse(_page(_upload_form("Please upload a PDF, PNG or JPG file.")), status_code=400)

    cfg = load()
    data = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        return HTMLResponse(_page(_upload_form("File is larger than 10 MB.")), status_code=413)
    safe_name = Path(file.filename or f"upload{suffix}").name or f"upload{suffix}"
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td) / safe_name
        tmp_path.write_bytes(data)
        try:
            result = analyze_file(
                tmp_path,
                cfg,
                sex=sex or None,
                explain=bool(explain),
            )
        except (BackendUnavailable, BackendError) as exc:
            return HTMLResponse(_page(_upload_form(str(exc))), status_code=503)
        except ValueError as exc:
            return HTMLResponse(_page(_upload_form(str(exc))), status_code=400)

    report_id = uuid.uuid4().hex
    if len(_REPORTS) >= _MAX_REPORTS:
        _REPORTS.pop(next(iter(_REPORTS)))
    _REPORTS[report_id] = result
    return HTMLResponse(_page(_results_html(report_id, result)))


@app.get("/export/{report_id}.csv")
def export_csv(report_id: str) -> PlainTextResponse:
    result = _REPORTS.get(report_id)
    if result is None:
        raise HTTPException(404, "report not found, it may have expired")
    return PlainTextResponse(
        to_csv(result),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labexplain-report.csv"},
    )


@app.get("/export/{report_id}.pdf")
def export_pdf(report_id: str) -> Response:
    result = _REPORTS.get(report_id)
    if result is None:
        raise HTTPException(404, "report not found, it may have expired")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.pdf"
        to_pdf(result, str(out))
        data = out.read_bytes()
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=labexplain-report.pdf"},
    )
