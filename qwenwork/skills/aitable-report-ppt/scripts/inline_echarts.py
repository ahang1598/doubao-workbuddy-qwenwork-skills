#!/usr/bin/env python3
"""Inline the bundled ECharts runtime into a generated HTML report."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


MARKER = '<script data-vendor="echarts"></script>'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("html")
    parser.add_argument("--output")
    parser.add_argument("--vendor")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    vendor = Path(args.vendor) if args.vendor else skill_root / "assets" / "vendor" / "echarts.min.js"
    source = Path(args.html)
    output = Path(args.output) if args.output else source
    html = source.read_text(encoding="utf-8")
    runtime = vendor.read_text(encoding="utf-8").replace("</script", "<\\/script")
    tag = f'<script data-vendor="echarts-inline">\n{runtime}\n</script>'

    if MARKER in html:
        html = html.replace(MARKER, tag, 1)
    else:
        pattern = re.compile(r'<script[^>]+src=["\'][^"\']*echarts[^"\']*["\'][^>]*>\s*</script>', re.I)
        html, count = pattern.subn(tag, html, count=1)
        if count == 0:
            raise SystemExit('No ECharts marker or external ECharts script tag found.')
    output.write_text(html, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
