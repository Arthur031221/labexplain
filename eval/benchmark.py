#!/usr/bin/env python3
"""Benchmark: flagging accuracy on the 20 synthetic reports.

Method: eval/generate_synthetic.py writes 20 PDFs with a real text layer
and a known status (normal, high, low) for each test row, drawn against the
bundled reference_ranges.json. This script runs the same pipeline the CLI
and web app use (parse the PDF text, match each row to the reference
table, compute the status) with explanations turned off, and compares the
predicted status to the planted one.

This isolates the parsing and reference-matching accuracy from OCR
accuracy: every report here has a clean, real text layer, the same code
path labexplain uses for a text PDF. It does not measure OCR accuracy on a
photographed or scanned report, that would need a labeled set of real
photos, which is out of scope for this benchmark. See the README limits
section.

Run with `uv run python eval/generate_synthetic.py` first, then
`uv run python eval/benchmark.py`.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import date
from pathlib import Path

from labexplain import __version__
from labexplain.config import Config
from labexplain.pipeline import analyze_file

SYNTHETIC_DIR = Path(__file__).resolve().parent / "synthetic"
RESULTS_PATH = Path(__file__).resolve().parent / "results.json"

# critical_high/critical_low collapse to high/low for this comparison, the
# ground truth generator only plants three buckets (normal, high, low).
_COLLAPSE = {"critical_high": "high", "critical_low": "low"}


def collapse(status: str) -> str:
    return _COLLAPSE.get(status, status)


def main() -> int:
    manifest_path = SYNTHETIC_DIR / "ground_truth.json"
    if not manifest_path.exists():
        print("no synthetic reports found. Run: uv run python eval/generate_synthetic.py", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text())
    cfg = Config()

    total = 0
    correct = 0
    per_report = []
    misses = []

    for entry in manifest:
        pdf_path = SYNTHETIC_DIR / entry["file"]
        result = analyze_file(pdf_path, cfg, sex=entry["sex"], explain=False)
        by_test_id = {m.test_id: m for m in result.rows if m.test_id}

        report_total = 0
        report_correct = 0
        for gt in entry["rows"]:
            report_total += 1
            total += 1
            matched = by_test_id.get(gt["test_id"])
            if matched is None:
                misses.append({"file": entry["file"], "test": gt["name"], "reason": "not parsed or not matched"})
                continue
            predicted = collapse(matched.status)
            if predicted == gt["expected"]:
                correct += 1
                report_correct += 1
            else:
                misses.append(
                    {
                        "file": entry["file"],
                        "test": gt["name"],
                        "expected": gt["expected"],
                        "predicted": predicted,
                    }
                )
        per_report.append({"file": entry["file"], "correct": report_correct, "total": report_total})

    accuracy = correct / total if total else 0.0
    method = {
        "n_reports": len(manifest),
        "n_rows": total,
        "labexplain_version": __version__,
        "explanations": "disabled (Ollama not used for this benchmark)",
        "extraction": "pdf text layer (pymupdf), no OCR model involved",
        "python": platform.python_version(),
        "machine": platform.platform(),
        "date": date.today().isoformat(),
    }
    results = {
        "accuracy": round(accuracy, 4),
        "correct": correct,
        "total": total,
        "method": method,
        "per_report": per_report,
        "misses": misses,
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    print(f"flagging accuracy: {correct}/{total} ({accuracy * 100:.1f}%) across {len(manifest)} synthetic reports")
    print(f"method: {method['extraction']}, explanations {method['explanations']}")
    print(f"wrote {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
