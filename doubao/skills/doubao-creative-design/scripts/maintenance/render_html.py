#!/usr/bin/env python3
"""Render a local HTML file to PNG through the bundled capture_canvas.cjs backend."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, help="Optional assertion against data-canvas-width")
    parser.add_argument("--height", type=int, help="Optional assertion against data-canvas-height")
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--node", default=shutil.which("node") or "node")
    parser.add_argument("--node-modules", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    args = parser.parse_args()
    html = args.html.resolve()
    output = args.output.resolve()
    if not html.is_file():
        parser.error(f"HTML not found: {html}")
    if output == html:
        parser.error("Output must not overwrite the HTML source")
    if any(value is not None and value <= 0 for value in (args.width, args.height)):
        parser.error("Width and height must be positive")
    if not math.isfinite(args.scale) or args.scale <= 0:
        parser.error("Scale must be positive and finite")
    backend = Path(__file__).with_name("capture_canvas.cjs")
    command = [
        str(args.node),
        str(backend),
        str(html),
        str(output),
        str(args.width) if args.width is not None else "auto",
        str(args.height) if args.height is not None else "auto",
        str(args.scale),
        str(args.node_modules.resolve()) if args.node_modules else "",
        str(args.browser_executable.resolve()) if args.browser_executable else "",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
