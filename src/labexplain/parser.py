"""Turn raw OCR or PDF text-layer text into LabRow objects.

Handles two shapes of input:
  - a markdown-ish table (pipe delimited rows), which is what GLM-OCR
    produces when asked for table recognition
  - plain text lines, one lab result per line, which is what a PDF text
    layer or plain OCR text looks like

Both are parsed with the same token logic: the first word-like span is the
test name, the first number-like token after it is the result value, then
any remaining tokens are classified as a unit, a flag (H/L/A and similar),
or a printed reference range (skipped, since labexplain uses its own
bundled reference table instead of trusting a possibly misread range).
"""

from __future__ import annotations

import re

from labexplain.models import LabRow

_NUM_TOKEN = re.compile(r"^[<>]?-?\d+\.?\d*$")
_RANGE_TOKEN = re.compile(r"^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)$")
_FLAG_TOKEN = re.compile(r"^(H|HH|L|LL|A|AB|HIGH|LOW|ABNORMAL|CRITICAL)$", re.I)
_UNIT_TOKEN = re.compile(r"^[A-Za-zµμ%][A-Za-zµμ%/^0-9.]*$")

_SKIP_LINE = re.compile(
    r"^(patient|name|dob|date of birth|collected|reported|specimen|"
    r"physician|ordering|account|fasting|comments?|page \d|"
    r"test\s*\|?\s*result|reference range)\b",
    re.I,
)

# Header-ish separator rows in a markdown table, e.g. "| --- | --- | --- |".
_MD_SEP = re.compile(r"^\|?[\s:|-]+\|?$")


def _clean_value(tok: str) -> float | None:
    tok = tok.strip().lstrip("<>")
    try:
        return float(tok)
    except ValueError:
        return None


def _split_tokens(line: str) -> list[str]:
    if "|" in line:
        return [t.strip() for t in line.split("|") if t.strip()]
    return [t for t in re.split(r"\s{1,}", line.strip()) if t]


def parse_row(line: str) -> LabRow | None:
    raw = line.rstrip("\n")
    stripped = raw.strip()
    if not stripped or len(stripped) < 3:
        return None
    if _MD_SEP.match(stripped):
        return None
    if _SKIP_LINE.match(stripped):
        return None

    tokens = _split_tokens(stripped)
    if len(tokens) < 2:
        return None

    value_idx = None
    for i, tok in enumerate(tokens):
        if i == 0:
            continue
        if _RANGE_TOKEN.match(tok):
            continue
        if _NUM_TOKEN.match(tok):
            value_idx = i
            break
    if value_idx is None:
        return None

    name = " ".join(tokens[:value_idx]).strip(" :•-")
    if not name or not re.search(r"[A-Za-z]", name):
        return None

    value = _clean_value(tokens[value_idx])

    unit = None
    flag = None
    report_low = None
    report_high = None
    for tok in tokens[value_idx + 1 :]:
        range_match = _RANGE_TOKEN.match(tok)
        if range_match:
            candidate_low, candidate_high = map(float, range_match.groups())
            if candidate_low < candidate_high:
                report_low, report_high = candidate_low, candidate_high
            continue
        if _FLAG_TOKEN.match(tok):
            flag = tok.upper()
            continue
        if unit is None and _UNIT_TOKEN.match(tok) and not _FLAG_TOKEN.match(tok):
            unit = tok

    if unit is None and report_low is None and flag is None:
        return None

    return LabRow(
        raw_text=stripped,
        test_name=name,
        value=value,
        unit=unit,
        flag=flag,
        report_low=report_low,
        report_high=report_high,
    )


def parse(text: str) -> list[LabRow]:
    rows: list[LabRow] = []
    for line in text.splitlines():
        row = parse_row(line)
        if row is not None:
            rows.append(row)
    return rows
