#!/usr/bin/env python3
"""Capture before/after screenshots of the web UI for the README and demo/.

Starts the labexplain server, opens Safari to the empty upload page for
"before", posts a synthetic sample report to /analyze and opens the
rendered result for "after", screenshots each with macOS screencapture,
then stitches them side by side into demo/before-after.png.

This is a one-off local tool, not part of the test suite. Run it with:

    uv run python demo/capture.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
ROOT = DEMO_DIR.parent
PORT = 8099
BASE_URL = f"http://127.0.0.1:{PORT}"


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def safari_window_id() -> str:
    out = subprocess.run(
        ["osascript", "-e", 'tell application "Safari" to id of front window'],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def screenshot_safari(out_path: Path) -> None:
    wid = safari_window_id()
    sh(["/usr/sbin/screencapture", "-x", "-o", "-l", wid, str(out_path)])


def main() -> int:
    sample_pdf = ROOT / "eval" / "synthetic" / "report_01.pdf"
    if not sample_pdf.exists():
        print(
            "no synthetic sample found, run `uv run python eval/generate_synthetic.py` first",
            file=sys.stderr,
        )
        return 1

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "labexplain.app:app", "--port", str(PORT)],
        cwd=ROOT,
    )
    try:
        time.sleep(2)
        sh(["open", "-a", "Safari", BASE_URL])
        time.sleep(2)
        screenshot_safari(DEMO_DIR / "before.png")

        after_html = DEMO_DIR / "_after.html"
        sh(
            [
                "curl",
                "-s",
                "-F",
                f"file=@{sample_pdf}",
                "-F",
                "sex=",
                "-F",
                "explain=",
                f"{BASE_URL}/analyze",
                "-o",
                str(after_html),
            ]
        )
        sh(["open", "-a", "Safari", str(after_html)])
        time.sleep(2)
        screenshot_safari(DEMO_DIR / "after.png")
        after_html.unlink(missing_ok=True)
    finally:
        server.terminate()
        server.wait(timeout=10)

    stitch(DEMO_DIR / "before.png", DEMO_DIR / "after.png", DEMO_DIR / "before-after.png")
    print(f"wrote {DEMO_DIR / 'before-after.png'}")
    return 0


def stitch(before: Path, after: Path, out: Path) -> None:
    from PIL import Image

    b = Image.open(before)
    a = Image.open(after)
    height = min(b.height, a.height, 900)
    b = b.resize((int(b.width * height / b.height), height))
    a = a.resize((int(a.width * height / a.height), height))
    gap = 16
    combo = Image.new("RGB", (b.width + a.width + gap, height), "white")
    combo.paste(b, (0, 0))
    combo.paste(a, (b.width + gap, 0))
    combo.save(out)


if __name__ == "__main__":
    raise SystemExit(main())
