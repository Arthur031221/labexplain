# Contributing

Thanks for looking at labexplain. This is a small, focused tool. Contributions
that keep it small are the easiest to merge.

## Setup

```
git clone https://github.com/Arthur031221/labexplain
cd labexplain
uv sync --locked --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Adding reference ranges

`src/labexplain/data/reference_ranges.json` holds the bundled test table. Every
entry needs a `source_url` that displays the interval and unit you used.
Document any unit conversion in the pull request. Do not add a number you
have not checked against the linked source. Run `uv run pytest tests/test_reference.py`
to check the table structure and matching behavior.

## Reporting a bug

Open an issue with the file type you tried (PDF or image), the panel it
covers, and the command or page you used. Attach the actual output, not just
a description. Do not attach a real lab report, real names, or any personal
health information, a synthetic or redacted example is enough to reproduce
most parsing bugs.

## Tests

`uv run pytest` should stay under two minutes and never load a real model.
Tests mock the OCR and explanation backends. If you add a code path that
calls Ollama or MLX, mock it in the test the same way the existing tests do.

## Style

Ruff enforces the lint rules in `pyproject.toml`. No em-dashes or semicolons
in prose files (README, CHANGELOG, comments). Keep functions short and
error messages specific.

## What this project will not do

labexplain will not diagnose or recommend treatment. Localhost is the default
for Ollama. A user can explicitly configure another Ollama URL, so bug reports
should include the configured backend without sharing a real report.
