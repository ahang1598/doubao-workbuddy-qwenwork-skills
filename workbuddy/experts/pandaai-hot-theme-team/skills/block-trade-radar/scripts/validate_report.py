#!/usr/bin/env python3
"""Validate an A-share block-trade-radar Markdown report."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    ("title", r"^#\s+.*(大宗交易|block[ -]?trade)", "一级标题需要标明大宗交易折溢价雷达报告"),
    ("summary", r"^##\s*(?:\d+[.、]\s*)?摘要", "缺少摘要"),
    ("overview", r"^##\s*(?:\d+[.、]\s*)?大宗成交总览", "缺少大宗成交总览章节"),
    ("distribution", r"^##\s*(?:\d+[.、]\s*)?折溢价分布", "缺少折溢价分布章节"),
    ("direction", r"^##\s*(?:\d+[.、]\s*)?机构专用方向", "缺少机构专用方向章节"),
    ("ranking", r"^##\s*(?:\d+[.、]\s*)?(成交额|折价榜|成交额/折价)", "缺少成交额/折价榜章节"),
    ("wash", r"^##\s*(?:\d+[.、]\s*)?对倒", "缺少对倒式提示章节"),
    ("risk", r"^##\s*(?:\d+[.、]\s*)?风险提示", "缺少风险提示章节"),
    ("data_notes", r"^##\s*(?:\d+[.、]\s*)?数据说明", "缺少数据说明章节"),
]


def validate(text: str) -> list[str]:
    issues: list[str] = []

    if len(text.strip()) < 500:
        issues.append("报告内容过短，可能不是完整大宗交易雷达报告")

    for _key, pattern, message in REQUIRED_SECTIONS:
        if not re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE):
            issues.append(message)

    if not re.search(r"(数据来源|来源接口|使用接口|get_block_trade|Pandadata)", text):
        issues.append("缺少数据来源或来源接口说明")

    if not re.search(r"(窗口|快照日|交易日|数据日|截止)", text):
        issues.append("缺少查询窗口/快照日/交易日区间说明")

    # Discount basis: 折溢价率 must name the close it was computed against.
    if not re.search(r"(折溢价|折价|溢价)", text):
        issues.append("缺少折溢价分析（折价/溢价/折溢价率）")
    if not re.search(r"(收盘|close|get_stock_daily|基准)", text):
        issues.append("缺少折溢价基准说明：折溢价率须注明用同日收盘价(get_stock_daily)计算")

    # Institutional / wash-print caveat presence.
    if not re.search(r"(机构专用|接盘|出货|对倒|buyer|seller)", text):
        issues.append("缺少机构专用方向或对倒式（buyer==seller）提示")

    if not re.search(r"不构成任何投资建议", text):
        issues.append("缺少免责声明：本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Path to the Markdown report")
    args = parser.parse_args()

    try:
        text = args.report.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 2

    issues = validate(text)
    if issues:
        print("FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
