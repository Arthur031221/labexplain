from labexplain.models import LabRow
from labexplain.reference import find_entry, load_reference_data, match_row, normalize


def test_reference_file_has_enough_entries(ref_data):
    assert len(ref_data["tests"]) >= 40


def test_every_entry_has_a_source(ref_data):
    for entry in ref_data["tests"]:
        assert entry["source_url"].startswith("http")
        assert entry["source_lab"] in ("LabCorp", "Gloucestershire NHS", "Maidstone NHS")
        assert entry["id"]
        assert entry["name"]
        assert entry["unit"]
        assert "range" in entry


def test_entry_ids_are_unique(ref_data):
    ids = [e["id"] for e in ref_data["tests"]]
    assert len(ids) == len(set(ids))


def test_find_entry_matches_its_own_name(ref_data):
    for entry in ref_data["tests"][:25]:
        found = find_entry(entry["name"])
        assert found is not None
        assert found["id"] == entry["id"]


def test_normalize_ignores_case_and_punctuation():
    assert normalize("White Blood Cell") == normalize("white-blood-cell ")


def test_match_row_flags_high_and_low(flat_entry):
    low = flat_entry["range"]["low"]
    high = flat_entry["range"]["high"]
    mid = (low + high) / 2

    normal = LabRow(raw_text="x", test_name=flat_entry["name"], value=mid, unit=flat_entry["unit"])
    matched, _ = match_row(normal)
    assert matched.status == "normal"
    assert matched.test_id == flat_entry["id"]

    too_high = LabRow(raw_text="x", test_name=flat_entry["name"], value=high + 1000, unit=flat_entry["unit"])
    matched_high, _ = match_row(too_high)
    assert matched_high.status in ("high", "critical_high")

    too_low = LabRow(
        raw_text="x", test_name=flat_entry["name"], value=max(low - 1000, -1e9), unit=flat_entry["unit"]
    )
    matched_low, _ = match_row(too_low)
    assert matched_low.status in ("low", "critical_low")


def test_match_row_unmatched_for_unknown_test():
    row = LabRow(raw_text="x", test_name="Zzyzx Quokka Nonexistent Panel", value=1.0, unit=None)
    matched, warning = match_row(row)
    assert matched.status == "unmatched"
    assert matched.test_id is None
    assert warning is None


def test_load_reference_data_is_cached():
    a = load_reference_data()
    b = load_reference_data()
    assert a is b


def test_report_range_overrides_bundled_range():
    row = LabRow("Sodium 140 mmol/L 130-138", "Sodium", 140, "mmol/L", report_low=130, report_high=138)
    matched, warning = match_row(row)
    assert matched.status == "high"
    assert matched.source_lab == "Report"
    assert warning is None


def test_unit_mismatch_does_not_assign_flag():
    row = LabRow("Glucose 95 mg/dL", "Glucose", 95, "mg/dL")
    matched, warning = match_row(row)
    assert matched.status == "unmatched"
    assert "unit" in warning
