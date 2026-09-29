#!/usr/bin/env python3
"""Generate synthetic lab report PDFs with randomized values and known ground truth.

Run with `uv run python eval/generate_synthetic.py`. Writes 20 PDFs and a
ground_truth.json manifest to eval/synthetic/. benchmark.py reads that
manifest and compares it against what the labexplain pipeline actually
flags.

Each PDF has a real, selectable text layer (built with reportlab), one test
per line as "Name Value Unit", which is the same plain-line shape the
parser handles for a text-layer PDF. Values are drawn to land in one of
three known buckets (normal, high, low) relative to the bundled reference
range for that test and the report's assigned sex, with a safety margin so
generated values never accidentally land in the critical bucket.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from reportlab.pdfgen import canvas

from labexplain.reference import load_reference_data

OUT_DIR = Path(__file__).resolve().parent / "synthetic"
N_REPORTS = 20
MIN_TESTS = 8
MAX_TESTS = 16
SEED = 20260930


def range_for(entry: dict, sex: str) -> tuple[float | None, float | None]:
    rng = entry["range"]
    if "low" in rng or "high" in rng:
        return rng.get("low"), rng.get("high")
    if sex in rng:
        return rng[sex].get("low"), rng[sex].get("high")
    any_sex = next(iter(rng.values()))
    return any_sex.get("low"), any_sex.get("high")


def gen_value(low: float | None, high: float | None, target: str) -> float:
    span = high - low if low is not None and high is not None else abs(high or low or 1)
    span = span or 1.0
    if target == "normal":
        lo = low if low is not None else high - span
        hi = high if high is not None else low + span
        return round(random.uniform(lo, hi), 2)
    if target == "high":
        base = high if high is not None else (low or 0) + span
        return round(base + random.uniform(0.05, 0.30) * span, 2)
    if target == "low":
        base = low if low is not None else (high or 0) - span
        return round(max(base - random.uniform(0.05, 0.30) * span, 0.01), 2)
    raise ValueError(target)


def build_report(index: int, entries: list[dict]) -> tuple[str, list[str], list[dict]]:
    sex = random.choice(["male", "female"])
    n = random.randint(MIN_TESTS, MAX_TESTS)
    picks = random.sample(entries, k=min(n, len(entries)))
    lines = [f"Synthetic Lab Report {index:02d}", f"Sex on file: {sex}", ""]
    ground_truth = []
    for entry in picks:
        low, high = range_for(entry, sex)
        if low is None and high is None:
            continue
        target = random.choices(["normal", "high", "low"], weights=[0.5, 0.25, 0.25])[0]
        if (low is None or low <= 0) and target == "low":
            target = "normal"
        if high is None and target == "high":
            target = "normal"
        value = gen_value(low, high, target)
        lines.append(f"{entry['name']} {value} {entry['unit']}")
        ground_truth.append({"test_id": entry["id"], "name": entry["name"], "value": value, "expected": target})
    return sex, lines, ground_truth


def write_pdf(path: Path, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=(612, 792))
    c.setFont("Helvetica", 10)
    y = 740
    for line in lines:
        c.drawString(40, y, line)
        y -= 16
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 740
    c.save()


def main() -> None:
    random.seed(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_reference_data()["tests"]
    manifest = []
    for i in range(1, N_REPORTS + 1):
        sex, lines, ground_truth = build_report(i, entries)
        pdf_path = OUT_DIR / f"report_{i:02d}.pdf"
        write_pdf(pdf_path, lines)
        manifest.append({"file": pdf_path.name, "sex": sex, "rows": ground_truth})
    (OUT_DIR / "ground_truth.json").write_text(json.dumps(manifest, indent=2))
    total_rows = sum(len(m["rows"]) for m in manifest)
    print(f"wrote {N_REPORTS} synthetic reports ({total_rows} test rows) to {OUT_DIR}")


if __name__ == "__main__":
    main()
