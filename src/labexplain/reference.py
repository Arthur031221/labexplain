"""Load the bundled reference range table and match parsed rows against it."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources

from labexplain.models import LabRow, MatchedRow

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize(name: str) -> str:
    return _NORMALIZE_RE.sub("", name.lower())


@lru_cache(maxsize=1)
def load_reference_data() -> dict:
    raw = resources.files("labexplain.data").joinpath("reference_ranges.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, dict]:
    data = load_reference_data()
    index: dict[str, dict] = {}
    for entry in data.get("tests", []):
        keys = {entry["id"], entry["name"], *entry.get("aliases", [])}
        for key in keys:
            norm = normalize(key)
            if norm and norm not in index:
                index[norm] = entry
    return index


def find_entry(test_name: str) -> dict | None:
    index = _alias_index()
    norm = normalize(test_name)
    if norm in index:
        return index[norm]
    return None


def _same_unit(left: str, right: str) -> bool:
    """Accept spelling variants and exact equivalent count units only."""

    def canonical(unit: str) -> str:
        value = unit.lower().replace("µ", "u").replace("μ", "u").replace(" ", "")
        return {
            "x10e3/ul": "x10^3/ul",
            "x10^9/l": "x10^3/ul",
            "x10e6/ul": "x10^6/ul",
            "x10^12/l": "x10^6/ul",
            "ng/l": "pg/ml",
            "ug/l": "ng/ml",
            "miu/l": "uiu/ml",
            "iu/l": "u/l",
        }.get(value, value)

    return canonical(left) == canonical(right)


def _range_for(entry: dict, sex: str | None) -> tuple[float | None, float | None, str | None]:
    rng = entry["range"]
    warning = None
    if "low" in rng or "high" in rng:
        return rng.get("low"), rng.get("high"), None
    # sex specific range
    if sex in ("male", "female") and sex in rng:
        return rng[sex].get("low"), rng[sex].get("high"), None
    lows = [v["low"] for v in rng.values() if v.get("low") is not None]
    highs = [v["high"] for v in rng.values() if v.get("high") is not None]
    low = min(lows) if lows else None
    high = max(highs) if highs else None
    warning = "sex not given, showing the combined male/female range"
    return low, high, warning


def _status(value: float | None, low: float | None, high: float | None) -> str:
    if value is None:
        return "unmatched"
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


def match_row(row: LabRow, sex: str | None = None) -> tuple[MatchedRow, str | None]:
    """Return the matched row and an optional warning about the match."""
    entry = find_entry(row.test_name)
    if row.report_low is not None and row.report_high is not None:
        return MatchedRow(
            row=row,
            test_id=entry["id"] if entry else None,
            display_name=entry["name"] if entry else row.test_name,
            value=row.value,
            unit=row.unit,
            low=row.report_low,
            high=row.report_high,
            status=_status(row.value, row.report_low, row.report_high),
            source_lab="Report",
            source_url=None,
        ), None
    if entry is None or row.unit is None or not _same_unit(row.unit, entry["unit"]):
        matched = MatchedRow(
            row=row,
            test_id=entry["id"] if entry else None,
            display_name=entry["name"] if entry else row.test_name,
            value=row.value,
            unit=row.unit,
            low=None,
            high=None,
            status="unmatched",
            source_lab=None,
            source_url=None,
        )
        warning = None
        if entry:
            warning = (
                f"{entry['name']}: unit {row.unit or '(missing)'} does not match "
                f"the bundled {entry['unit']} interval; no flag assigned"
            )
        if row.flag:
            printed_warning = f"{row.test_name}: the report printed flag {row.flag}, but no interval was usable"
            warning = f"{warning}. {printed_warning}" if warning else printed_warning
        return matched, warning
    low, high, warning = _range_for(entry, sex)
    status = _status(row.value, low, high)
    matched = MatchedRow(
        row=row,
        test_id=entry["id"],
        display_name=entry["name"],
        value=row.value,
        unit=row.unit or entry.get("unit"),
        low=low,
        high=high,
        status=status,
        source_lab=entry.get("source_lab"),
        source_url=entry.get("source_url"),
    )
    full_warning = f"{entry['name']}: {warning}" if warning else None
    return matched, full_warning


def match_rows(rows: list[LabRow], sex: str | None = None) -> tuple[list[MatchedRow], list[str]]:
    matched_rows: list[MatchedRow] = []
    warnings: list[str] = []
    for row in rows:
        matched, warning = match_row(row, sex)
        matched_rows.append(matched)
        if warning:
            warnings.append(warning)
    return matched_rows, warnings
