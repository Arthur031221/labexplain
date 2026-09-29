import json

from labexplain.cli import main


def test_cli_no_command_prints_help(capsys):
    rc = main([])
    assert rc == 0
    assert "labexplain" in capsys.readouterr().out


def test_cli_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "labexplain" in out


def test_cli_analyze_missing_file(capsys):
    rc = main(["analyze", "/no/such/file.pdf"])
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_cli_analyze_json_output(tmp_path, flat_entry, make_pdf, capsys):
    high = flat_entry["range"]["high"]
    pdf = make_pdf(tmp_path / "r.pdf", [f"{flat_entry['name']} {high + 1000} {flat_entry['unit']}"])
    rc = main(["analyze", str(pdf), "--json", "--no-explain"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["disclaimer"].startswith("Educational only")
    assert payload["extraction_method"] == "pdf-text"
    assert any(r["test_id"] == flat_entry["id"] for r in payload["rows"])


def test_cli_analyze_table_output_shows_banner(tmp_path, flat_entry, make_pdf, capsys):
    mid = (flat_entry["range"]["low"] + flat_entry["range"]["high"]) / 2
    pdf = make_pdf(tmp_path / "r.pdf", [f"{flat_entry['name']} {mid} {flat_entry['unit']}"])
    rc = main(["analyze", str(pdf), "--no-explain"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Educational only" in out
    assert flat_entry["name"] in out


def test_cli_analyze_writes_csv(tmp_path, flat_entry, make_pdf, capsys):
    pdf = make_pdf(tmp_path / "r.pdf", [f"{flat_entry['name']} {flat_entry['range']['low']} {flat_entry['unit']}"])
    csv_out = tmp_path / "out.csv"
    rc = main(["analyze", str(pdf), "--no-explain", "--csv", str(csv_out)])
    assert rc == 0
    assert csv_out.exists()


def test_cli_config_show(capsys):
    rc = main(["config", "show"])
    assert rc == 0
    assert "ocr_backend" in capsys.readouterr().out
