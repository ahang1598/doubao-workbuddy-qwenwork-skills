#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""对手方论证（Devil's Advocate）软门禁验证器

设计目的（accuracy-uplift v12 · 建议 5）
─────────────────────────────────────────────────────────────────────
强制 Intent-1 报告新增一个独立章节「对手方论证 Devil's Advocate」：
不是补充内容，而是**站到对立面用同样严格的方法重做一遍**。

要求
─────────────────────────────────────────────────────────────────────
1. 报告中存在「对手方论证」/「Devil's Advocate」/「空头论点」/「反方论证」/
   「逆向审视」等章节标识
2. 章节内至少出现 ≥3 条独立的空头论点（编号 1./2./3. 或 ①②③ 或 - 列表）
3. 每条空头论点附带数据支撑（含数字/百分号/年份/信源关键词之一）
4. 我方对每条空头论点的反驳（"反驳/我方观点/我们认为"等关键词）
5. 反驳的可证伪条件（"若 X 发生则反驳错误/重估"句式 ≥1 处）
6. 最终置信度调整声明（"置信度从 X 调整为 Y" 或 "维持/上调/下调置信度"）

软门禁：缺失 → WARN，不阻断。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SECTION_MARKERS = [
    r"对手方论证", r"Devil['’]?s?\s*Advocate", r"空头论点", r"反方论证",
    r"逆向审视", r"对立面论证", r"反方观点",
]

MIN_BEAR_POINTS = 3


def _find_section(text: str) -> str:
    """返回对手方论证章节文本（若找不到，返回空）"""
    # 找到匹配标题
    for marker in SECTION_MARKERS:
        m = re.search(r"^#{2,5}\s+.*?" + marker, text, re.M)
        if m:
            start = m.start()
            # 找到下一个同级或更高级标题
            level = len(re.match(r"^(#{2,5})", text[start:]).group(1))
            after = text[m.end():]
            next_h = re.search(r"^#{1," + str(level) + r"}\s", after, re.M)
            end = m.end() + (next_h.start() if next_h else len(after))
            return text[start:end]
    return ""


def validate_devils_advocate(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        warns.append(f"[对手方论证·WARN] 报告不存在: {report_path}")
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")

    section = _find_section(text)
    if not section:
        warns.append(
            "[对手方论证·WARN] 未发现「对手方论证」/「Devil's Advocate」/「空头论点」"
            "等独立章节。建议 5 要求新增独立章节，**站到对立面用同样严格的方法重做一遍**。"
        )
        return warns

    # 计数空头论点：1. / 2. / ① / ② / - 列表项
    bear_count = len(re.findall(r"^\s*(?:\d+\.|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|[-*]\s)", section, re.M))
    # 关键词触发也可计数（如 "空头论点 1"）
    kw_bear = len(re.findall(r"(空头|看空)\s*(论点|观点)\s*\d", section))
    bear_count = max(bear_count, kw_bear)
    if bear_count < MIN_BEAR_POINTS:
        warns.append(
            f"[对手方论证·WARN] 仅识别到 {bear_count} 条空头论点 < {MIN_BEAR_POINTS} 条。"
            "应列出 ≥3 条独立逻辑的空头论点。"
        )

    # 数据支撑（数字 + % / 元 / 年 / "来源"）
    has_numbers = bool(re.search(r"\d+(?:\.\d+)?\s*(%|％|元|倍|年|亿|万)", section))
    has_source = bool(re.search(r"来源|<sup>\d+</sup>|https?://", section))
    if not (has_numbers and has_source):
        warns.append(
            "[对手方论证·WARN] 空头论点缺少数据支撑（数字 + 信源），"
            "不能是凭空反对，必须像我方论点一样有量化与可溯源依据。"
        )

    # 我方反驳关键词
    if not re.search(r"(反驳|我方观点|我们认为|我方反驳|本报告认为)", section):
        warns.append(
            "[对手方论证·WARN] 缺少明确的「我方反驳」表述。"
            "每条空头论点都需要正面回应。"
        )

    # 反驳的可证伪条件
    if not re.search(r"若.{0,40}(发生|出现|证实|实现).{0,40}(反驳|错误|重估|不成立|止损)", section):
        warns.append(
            "[对手方论证·WARN] 缺少反驳的可证伪条件（『若 X 发生则我的反驳错在哪里』）"
        )

    # 置信度调整
    if not re.search(r"置信度.{0,15}(从|由).{0,20}(调|至|为)|置信度.{0,15}(维持|上调|下调|提升|降低)", section):
        warns.append(
            "[对手方论证·WARN] 缺少最终置信度调整声明（"
            "『置信度从 X 调整为 Y / 维持/上调/下调置信度』）"
        )

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="对手方论证软门禁验证器")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_devils_advocate(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 对手方论证软门禁 PASS: {report_path.name}")
        else:
            print(f"⚠️ 对手方论证软门禁 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
