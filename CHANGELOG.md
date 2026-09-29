# Changelog

## 0.1.0 (2026-09-30)

First release.

- OCR a lab report photo (PNG, JPG) or a scanned PDF with the cached MLX
  GLM-OCR model, falling back to Ollama `glm-ocr:q8_0` when MLX is not
  available. A PDF with a text layer is read directly with pymupdf, no
  model needed.
- Parse recognized rows into test, value, unit and flag.
- Use a printed report interval when present. Fall back to 43 sourced adult
  example intervals only when the test name and unit match. Leave other rows
  unflagged and show a warning.
- Optional plain-English notes for flagged values from local Ollama
  `qwen3:4b`, with a clinician reminder. Notes are not validated medical
  interpretations.
- Persistent "educational only, not medical advice" banner in the CLI and
  the web UI.
- `labexplain analyze` CLI with `--json`, `--csv`, `--pdf`, `--sex`, and
  `--no-explain`.
- `labexplain serve` FastAPI app: one page, upload a file, see results,
  download CSV or PDF.
- Benchmark in `eval/` on 20 synthetic text-layer PDFs with randomized values.
