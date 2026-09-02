#!/usr/bin/env python3
"""Validate an A-share concept-rotation-monitor Markdown report."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    ("title", r"^#\s+.*(概念|题材|板块轮动|concept)", "一级标题需要标明概念题材轮动报告"),
    ("summary", r"^##\s*(?:\d+[.、]\s*)?摘要", "缺少摘要"),
    ("landscape", r"^##\s*(?:\d+[.、]\s*)?概念全景", "缺少概念全景章节"),
    ("momentum", r"^##\s*(?:\d+[.、]\s*)?动量排名", "缺少动量排名章节"),
    ("breadth", r"^##\s*(?:\d+[.、]\s*)?广度", "缺少广度对照章节"),
    ("rotation", r"^##\s*(?:\d+[.、]\s*)?轮动信号", "缺少轮动信号章节"),
    ("new", r"^##\s*(?:\d+[.、]\s*)?新概念", "缺少新概念雷达章节"),
    ("risk", r"^##\s*(?:\d+[.、]\s*)?风险提示", "缺少风险提示章节"),
    ("data_notes", r"^##\s*(?:\d+[.、]\s*)?数据说明", "缺少数据说明章节"),
]


def validate(text: str) -> list[str]:
    issues: list[str] = []

    if len(text.strip()) < 500:
        issues.append("报告内容过短，可能不是完整概念轮动报告")

    for _key, pattern, message in REQUIRED_SECTIONS:
        if not re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE):
            issues.append(message)

    if not re.search(r"(数据来源|来源接口|使用接口|get_concept_list|get_concept_constituents|get_stock_daily|Pandadata)", text):
        issues.append("缺少数据来源或来源接口说明")

    # Aggregation / weighting caveat: bottom-up, equal-weight, no official index.
    if not re.search(r"(等权|中位|median|均值|口径|自下而上|bottom)", text):
        issues.append("缺少动量聚合口径说明：概念动量为自下而上等权(中位/均值)计算，无官方概念指数")

    # Membership snapshot / overlap caveat.
    if not re.search(r"(成分快照|快照日|纳入日|时点|成分随时间|概念重叠|不可加|非独立)", text):
        issues.append("缺少成分时点/概念重叠说明：成分随时间变化须按快照日、概念重叠不可加")

    # Window labeling.
    if not re.search(r"(窗口|动量窗口|短窗|长窗|5D|20D|交易日|快照日)", text):
        issues.append("缺少动量窗口/快照日说明")

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
