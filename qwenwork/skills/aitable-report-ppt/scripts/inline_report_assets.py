#!/usr/bin/env python3
"""General-purpose asset inliner for single-file visual reports.

Replaces marker comments in an HTML file with inlined <script> blocks,
escapes </script> inside the payloads, refuses to double-inline, verifies
every required runtime library made it into the final HTML, and emits the
asset hashes for the verification chain (runtime hash becomes the page's
runtime_asset_sha256 fingerprint).

Markers in the HTML source:
    <!-- INLINE:echarts -->
    <!-- INLINE:runtime -->
    <!-- INLINE:drilldown -->

Note: inline_echarts.py keeps its original single responsibility and is not
used by the runtime-based pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ASSETS = ("echarts", "runtime", "drilldown")


def escape(script: str) -> str:
    return script.replace("</script", "<\\/script")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", help="输入 HTML（含 INLINE 标记）")
    parser.add_argument("--echarts", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--drilldown", required=True)
    parser.add_argument("--output", help="输出路径（缺省覆盖输入）")
    parser.add_argument("--hash-output", help="资源哈希 JSON 输出路径")
    args = parser.parse_args()

    html_path = Path(args.html)
    html = html_path.read_text(encoding="utf-8")

    paths = {"echarts": Path(args.echarts), "runtime": Path(args.runtime), "drilldown": Path(args.drilldown)}
    hashes: dict[str, str] = {}

    for name in ASSETS:
        marker = f"<!-- INLINE:{name} -->"
        inlined_flag = f'data-inlined="{name}"'
        if inlined_flag in html:
            sys.exit(f"拒绝重复内联：{name} 已经内联过（发现 {inlined_flag}）。")
        if marker not in html:
            sys.exit(f"HTML 中缺少标记 {marker}，无法内联 {name}。")
        source = paths[name]
        if not source.exists():
            sys.exit(f"资源文件不存在：{source}")
        payload = source.read_text(encoding="utf-8")
        hashes[name] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        html = html.replace(marker, f'<script {inlined_flag}>{escape(payload)}</script>', 1)

    for name in ASSETS:
        if f'data-inlined="{name}"' not in html:
            sys.exit(f"内联校验失败：{name} 未进入最终 HTML。")

    output = Path(args.output) if args.output else html_path
    output.write_text(html, encoding="utf-8")

    hash_payload = {
        "echarts_sha256": hashes["echarts"],
        "runtime_asset_sha256": hashes["runtime"],
        "drilldown_sha256": hashes["drilldown"],
    }
    if args.hash_output:
        Path(args.hash_output).write_text(json.dumps(hash_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(hash_payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
