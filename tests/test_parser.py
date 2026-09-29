from labexplain.parser import parse, parse_row


def test_parse_plain_line():
    row = parse_row("Hemoglobin    9.0    g/dL    L    11.6-15.0")
    assert row is not None
    assert row.test_name == "Hemoglobin"
    assert row.value == 9.0
    assert row.unit == "g/dL"
    assert row.flag == "L"
    assert (row.report_low, row.report_high) == (11.6, 15.0)


def test_parse_line_without_flag_or_range():
    row = parse_row("Glucose 95 mg/dL")
    assert row is not None
    assert row.test_name == "Glucose"
    assert row.value == 95.0
    assert row.unit == "mg/dL"
    assert row.flag is None


def test_parse_markdown_table_row():
    row = parse_row("| Sodium | 140 | mmol/L | 136-145 |")
    assert row is not None
    assert row.test_name == "Sodium"
    assert row.value == 140.0
    assert row.unit == "mmol/L"


def test_parse_skips_headers_and_separators():
    rows = parse(
        "Patient: Jane Doe\n"
        "TEST | RESULT | UNITS | REFERENCE RANGE\n"
        "| --- | --- | --- | --- |\n"
        "WBC | 6.2 | x10^3/uL | 3.4-10.8 |\n"
    )
    assert len(rows) == 1
    assert rows[0].test_name == "WBC"
    assert rows[0].value == 6.2


def test_parse_ignores_short_or_empty_lines():
    assert parse_row("") is None
    assert parse_row("ab") is None
    assert parse_row("   ") is None


def test_parse_no_numeric_value_returns_none():
    assert parse_row("Comments: none") is None


def test_parse_multiple_rows():
    text = "WBC 6.2 x10^3/uL\nRBC 4.8 x10^6/uL\nPlatelet Count 250 x10^3/uL"
    rows = parse(text)
    assert [r.test_name for r in rows] == ["WBC", "RBC", "Platelet Count"]
