from __future__ import annotations

from pathlib import Path

import pytest

from labexplain.reference import load_reference_data


def _write_pdf(path: Path, lines: list[str]) -> Path:
    """Write a tiny PDF whose text layer is exactly these lines, one per row."""
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=(612, 792))
    c.setFont("Helvetica", 10)
    y = 740
    for line in lines:
        c.drawString(40, y, line)
        y -= 16
    c.save()
    return path


@pytest.fixture
def make_pdf():
    """Fixture form of _write_pdf, so tests can request it like any other fixture."""
    return _write_pdf


@pytest.fixture(scope="session")
def ref_data():
    return load_reference_data()


@pytest.fixture(scope="session")
def flat_entry(ref_data):
    """A reference entry with one range for all adults (not split by sex)."""
    for entry in ref_data["tests"]:
        rng = entry["range"]
        if ("low" in rng or "high" in rng) and rng.get("low") is not None and rng.get("high") is not None:
            return entry
    raise AssertionError("no flat-range entry found in reference_ranges.json")
