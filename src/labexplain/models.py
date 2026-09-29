"""Small dataclasses shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

STATUS_ORDER = ["normal", "unmatched", "low", "high"]


@dataclass
class LabRow:
    """One line parsed out of the OCR text or PDF text layer."""

    raw_text: str
    test_name: str
    value: float | None
    unit: str | None
    flag: str | None = None  # a flag printed on the report itself, e.g. "H" or "L"
    report_low: float | None = None
    report_high: float | None = None


@dataclass
class MatchedRow:
    """A LabRow matched against the reference range table."""

    row: LabRow
    test_id: str | None
    display_name: str
    value: float | None
    unit: str | None
    low: float | None
    high: float | None
    status: str  # one of STATUS_ORDER
    source_lab: str | None
    source_url: str | None
    explanation: str | None = None


@dataclass
class ReportResult:
    rows: list[MatchedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ocr_backend: str | None = None
    extraction_method: str | None = None  # "pdf-text", "mlx", "ollama"

    def flagged(self) -> list[MatchedRow]:
        return [r for r in self.rows if r.status not in ("normal", "unmatched")]

    def to_dict(self) -> dict:
        return {
            "extraction_method": self.extraction_method,
            "ocr_backend": self.ocr_backend,
            "warnings": self.warnings,
            "rows": [
                {
                    "raw_text": m.row.raw_text,
                    "test_id": m.test_id,
                    "name": m.display_name,
                    "value": m.value,
                    "unit": m.unit,
                    "low": m.low,
                    "high": m.high,
                    "status": m.status,
                    "reported_flag": m.row.flag,
                    "source_lab": m.source_lab,
                    "source_url": m.source_url,
                    "explanation": m.explanation,
                }
                for m in self.rows
            ],
        }
