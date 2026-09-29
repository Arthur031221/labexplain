"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from labexplain import BANNER, __version__
from labexplain.config import ConfigError, coerce, load, save
from labexplain.models import ReportResult
from labexplain.ocr import BackendError, BackendUnavailable

STATUS_LABEL = {
    "normal": "  ",
    "unmatched": "? ",
    "low": "L ",
    "high": "H ",
}


def _print_banner() -> None:
    print(BANNER)
    print()


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


def _print_table(result: ReportResult) -> None:
    rows = result.rows
    if not rows:
        print("No test rows were found in this file.")
        return
    name_w = max(4, max(len(r.display_name) for r in rows))
    header = f"{'FLAG':4} {'TEST':<{name_w}} {'VALUE':>8} {'UNIT':<10} {'RANGE':<14} SOURCE"
    print(header)
    print("-" * len(header))
    for m in rows:
        flag = STATUS_LABEL.get(m.status, "? ")
        range_text = "-" if m.low is None and m.high is None else f"{_fmt(m.low)}-{_fmt(m.high)}"
        source = m.source_lab or "-"
        print(
            f"{flag:<4} {m.display_name:<{name_w}} {_fmt(m.value):>8} "
            f"{(m.unit or '-'):<10} {range_text:<14} {source}"
        )
    flagged = result.flagged()
    if flagged:
        print()
        print("Notes on flagged values:")
        for m in flagged:
            if m.explanation:
                print(f"  {m.display_name}: {m.explanation}")
            else:
                print(f"  {m.display_name}: flagged {m.status}, no explanation generated.")
    if result.warnings:
        print()
        for w in result.warnings:
            print(f"warning: {w}")


def cmd_analyze(args: argparse.Namespace) -> int:
    from labexplain.pipeline import analyze_file

    path = Path(args.file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    cfg = load()
    if args.ocr_backend:
        cfg.ocr_backend = args.ocr_backend

    if not args.json:
        _print_banner()

    try:
        result = analyze_file(
            path,
            cfg,
            sex=args.sex,
            explain=not args.no_explain,
            ocr_backend_name=args.ocr_backend,
        )
    except (BackendUnavailable, BackendError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.csv:
        from labexplain.export import to_csv

        Path(args.csv).write_text(to_csv(result), encoding="utf-8")
        print(f"wrote {args.csv}", file=sys.stderr if args.json else sys.stdout)
    if args.pdf:
        from labexplain.export import to_pdf

        to_pdf(result, args.pdf)
        print(f"wrote {args.pdf}", file=sys.stderr if args.json else sys.stdout)

    if args.json:
        payload = result.to_dict()
        payload["disclaimer"] = BANNER
        print(json.dumps(payload, indent=2))
    else:
        _print_table(result)

    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("error: uvicorn is not installed. Run `pip install uvicorn`.", file=sys.stderr)
        return 1
    _print_banner()
    print(f"serving on http://127.0.0.1:{args.port}")
    uvicorn.run("labexplain.app:app", host="127.0.0.1", port=args.port, log_level="warning")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    cfg = load()
    if args.config_cmd == "show":
        for key, value in cfg.to_dict().items():
            print(f"{key} = {value}")
        return 0
    if args.config_cmd == "set":
        try:
            setattr(cfg, args.key, coerce(args.key, args.value))
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        path = save(cfg)
        print(f"saved {path}")
        return 0
    print("usage: labexplain config show | labexplain config set KEY VALUE", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labexplain",
        description="Explain a blood test report offline. " + BANNER,
    )
    parser.add_argument("--version", action="version", version=f"labexplain {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_analyze = sub.add_parser("analyze", help="analyze a lab report PDF or image")
    p_analyze.add_argument("file", help="path to a PDF or image (png, jpg) of a lab report")
    p_analyze.add_argument("--sex", choices=["male", "female"], default=None)
    p_analyze.add_argument("--no-explain", action="store_true", help="skip the Ollama explanations")
    p_analyze.add_argument("--json", action="store_true", help="print JSON instead of a table")
    p_analyze.add_argument("--csv", metavar="PATH", help="also write a CSV report")
    p_analyze.add_argument("--pdf", metavar="PATH", help="also write a PDF report")
    p_analyze.add_argument(
        "--ocr-backend", choices=["auto", "mlx", "ollama"], default=None, help="OCR backend to use"
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_serve = sub.add_parser("serve", help="run the local web UI")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    p_config = sub.add_parser("config", help="show or set config values")
    p_config.add_argument("config_cmd", choices=["show", "set"])
    p_config.add_argument("key", nargs="?")
    p_config.add_argument("value", nargs="?")
    p_config.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
