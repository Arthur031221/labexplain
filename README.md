# labexplain

Read a blood test PDF or photo on your own computer, with cited example ranges and optional local notes. Educational only, not medical advice.

In a local check, labexplain assigned the planted low, in-range, or high label to **240 of 240 rows** across 20 synthetic text-layer PDFs.[^benchmark] This checks parsing and range matching on generated documents. Photo OCR and clinical validity have not been measured.

[![CI](https://github.com/Arthur031221/labexplain/actions/workflows/ci.yml/badge.svg)](https://github.com/Arthur031221/labexplain/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![version](https://img.shields.io/badge/version-0.1.0-informational)

![CLI demo using a fictional report](demo/demo.gif)

## Why

A lab report can show many abbreviations and narrow reference intervals. It is easy to miss a flag or compare a value in the wrong unit. labexplain extracts rows locally, keeps the report's own printed interval when it can read one, and shows where any fallback interval came from. It does not interpret a group of results as a diagnosis.

## Install

With [uv](https://docs.astral.sh/uv/) installed:

```sh
uv tool install git+https://github.com/Arthur031221/labexplain.git
```

For a source checkout:

```sh
uv sync --locked --group dev
```

The first install downloads Python packages. Processing uses local files and a local Ollama server by default. If you configure a remote Ollama URL, report content will be sent to that server.

## Quick start

From a source checkout, run the included fictional sample without any model:

```sh
uv run labexplain analyze demo/sample.pdf --no-explain
```

After a tool install, run `labexplain analyze /path/to/report.pdf --no-explain`. The terminal output includes the educational-use banner, each parsed value, its unit, a range when available, its source, and any warnings. Use `--json`, `--csv result.csv`, or `--pdf result.pdf` for export.

Start the local web page with `uv run labexplain serve`, then open `http://127.0.0.1:8000`. The server binds to localhost. Uploaded reports remain in memory for the process lifetime so exports can be downloaded. Temporary upload files are deleted after analysis.

## How it works

1. PyMuPDF reads a PDF text layer. A PDF without readable text, or an image, goes through GLM-OCR using a cached MLX model on Apple Silicon or an Ollama model on the configured server.
2. A line parser extracts test name, value, unit, printed flag, and a printed numeric interval when available.
3. A valid printed interval takes precedence. Otherwise, a test name and unit must exactly match a bundled adult example interval. Rows without a usable interval remain unflagged.
4. Optional `qwen3:4b` notes describe flagged values in general terms. The response can be wrong or incomplete. The application adds a clinician reminder, but does not verify the model's medical statements.

The bundled table contains **43 adult examples** for blood counts, metabolic tests, thyroid tests, iron studies, and a few other tests. Every entry links to a public [Labcorp sodium page](https://www.labcorp.com/tests/001198/sodium), [Labcorp TSH page](https://www.labcorp.com/tests/004259/thyroid-stimulating-hormone-tsh), [Gloucestershire Hospitals hematology table](https://www.gloshospitals.nhs.uk/our-services/services-we-offer/pathology/haematology/haematology-reference-ranges/), or [Maidstone and Tunbridge Wells biochemistry table](https://www.mtw.nhs.uk/wp-content/uploads/2018/07/Biochemistry-Reference-ranges-and-traceability.pdf). The source is shown per row. Where the Gloucestershire table uses SI count units, the data uses the numerically equivalent `x10^3/uL` or `x10^6/uL`. Hemoglobin values in g/L were divided by 10 to display g/dL, and hematocrit fractions were multiplied by 100 to display percent. These are unit conversions, not new intervals.

Lab methods, age, pregnancy, sex, and local policy can change the appropriate interval. The range on your own report is the relevant one. A result within a range does not establish health, and a result outside one does not establish disease. See [MedlinePlus on reference ranges](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/) for context.

## OCR and notes

For a scanned PDF or photo, set up one OCR backend before analysis:

```sh
ollama pull glm-ocr:q8_0
```

Alternatively, on Apple Silicon install and cache `mlx-community/GLM-OCR-8bit`, then select `--ocr-backend mlx`. The MLX backend does not download model weights during automatic backend selection. The Ollama backend requires a running local Ollama server. For notes, run `ollama pull qwen3:4b` and omit `--no-explain`. No model is needed for text-layer PDFs with `--no-explain`.

## Command reference

```text
labexplain analyze FILE [--sex male|female] [--no-explain] [--json]
                        [--csv PATH] [--pdf PATH]
                        [--ocr-backend auto|mlx|ollama]
labexplain serve [--port PORT]
labexplain config show
labexplain config set KEY VALUE
labexplain --version
```

`--sex` selects a sex-specific bundled interval when one exists. Without it, the wider combined interval is shown with a warning. It has no effect on an interval printed in the report. `config show` lists all settings, including the model names and Ollama URL. Each command has `--help`.

## Comparison

| Project | Input and matching approach | Where analysis runs |
| --- | --- | --- |
| labexplain | PDF text or optional OCR, printed intervals first, 43 cited fallback examples | Local process by default |
| CBC_report_interpreter | Manual CBC entry and fixed rules | Local script |
| MedLens-AI | Image interpretation | Depends on its configured model |
| Diagnosify | Lab result interpretation | Depends on its configured model |
| medlabreport.com | Uploaded reports and hosted analysis | Hosted service |

This comparison describes the public project descriptions reviewed for this release. Features and hosting options can change.

## Limits and FAQ

- The tool is for education. It does not diagnose, triage, recommend treatment, or replace a clinician. A label such as "high" means only that a number exceeded the interval displayed next to it.
- Adult example intervals cover 43 test names, not every lab test. Lipids and HbA1c can use a printed interval if the parser reads it. They have no bundled fallback in this release because decision limits are not interchangeable with a lab reference interval.
- The line parser works best when each result has its name, value, and unit on one line. It may miss multi-column layouts, unclear scans, inequalities, or intervals with unusual syntax. Check every extracted row against the original report.
- Unit mismatches are shown without a bundled flag. The tool does not guess a conversion for an unknown unit.
- Model-generated notes may be inaccurate even when the numeric flag is correct. Use `--no-explain` for deterministic extraction and matching.
- The benchmark uses generated text-layer PDFs. It says nothing about OCR accuracy on photographs or clinical accuracy on real reports.
- PDF and CSV exports include extracted report data. Store them as you would store the original report.
- The web upload limit is 10 MB per file.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for development instructions. MIT license, [LICENSE](LICENSE).

[^benchmark]: `uv run python eval/generate_synthetic.py` followed by `uv run python eval/benchmark.py`, seed 20260930, 20 generated PDFs, 240 planted rows, macOS on Apple Silicon, Python 3.12, 2026-09-30. The generator draws values against the same bundled intervals used by the matcher. The PDF text layer is read with PyMuPDF. OCR and Ollama notes are disabled. This is a regression check for the supported synthetic format, not an independent field evaluation.
