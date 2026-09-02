#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""行为金融偏差侦测器 — 让「避坑指南」从人类自查变成自动侦测

设计目的（accuracy-uplift v13 · P1-3）
─────────────────────────────────────────────────────────────────────
基本面框架列了思维误区清单，但那是给人类 reader 看的，Agent 写报告时
不会自动对照检查自己。本侦测器对正文做启发式统计，自动发现两类高频偏差：

① 确认偏差（Confirmation Bias）
   统计正面措辞 vs 负面措辞的出现次数，比值过高（只找支持论据、忽视反面
   证据）→ WARN。同时检查是否存在独立的风险/对手方章节作为对冲。

② 锚定效应（Anchoring）
   估值是否过度锚定「历史均值/历史中枢/同行平均」，却缺少独立的绝对估值
   （DCF/内在价值）对照 → WARN。

注意：均为启发式，可能误报；WARN 文案已标注「若确属充分论证请忽略」。
软门禁性质：只 WARN，不阻断。
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

POSITIVE_WORDS = [
    "增长", "提升", "提高", "利好", "优势", "领先", "超预期", "看好", "强劲",
    "扩张", "改善", "受益", "高景气", "龙头", "护城河", "稀缺", "放量", "突破",
    "高增", "向好", "回暖", "兑现",
]
NEGATIVE_WORDS = [
    "下滑", "下降", "风险", "劣势", "不及预期", "承压", "减值", "竞争加剧",
    "放缓", "恶化", "亏损", "下修", "回落", "杀估值", "高估", "隐患", "瓶颈",
    "失速", "退坡", "拖累", "减持", "商誉",
]

# 锚定关键词
ANCHOR_WORDS = [r"历史(均值|中枢|中位数|区间|平均)", r"同行(均值|平均|可比)", r"近\s*\d+\s*年.{0,4}(PE|PB|估值).{0,4}(中枢|均值|区间)"]
ABSOLUTE_VAL_WORDS = [r"DCF", r"内在价值", r"绝对估值", r"自由现金流折现", r"DDM", r"现金流贴现"]


def _count(text: str, words: List[str]) -> int:
    return sum(text.count(w) for w in words)


def detect_behavioral_bias(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")

    # 只对有一定篇幅的报告做（对话/短文不适用）
    if len(text) < 1500:
        return warns

    # ── ① 确认偏差 ──────────────────────────────────
    pos = _count(text, POSITIVE_WORDS)
    neg = _count(text, NEGATIVE_WORDS)
    has_risk_section = bool(re.search(r"^#{2,5}.*(风险|对手方论证|空头|逆向审视|看空)", text, re.M))
    if neg == 0:
        if pos >= 8:
            warns.append(
                f"[行为偏差·WARN] 确认偏差信号：检测到 {pos} 处正面措辞、0 处负面措辞。"
                "报告几乎只呈现支持性证据，缺乏反面信号。建议主动列出不利证据与风险。"
            )
    else:
        ratio = pos / neg
        if ratio > 3.0 and not has_risk_section:
            warns.append(
                f"[行为偏差·WARN] 确认偏差信号：正面措辞/负面措辞 ≈ {ratio:.1f}:1（>3:1）"
                "且未见独立风险/对手方章节。可能存在「只找支持论据」倾向，"
                "建议补充负面证据或加强对手方论证。若确属客观结论请忽略。"
            )
        elif ratio > 5.0:
            warns.append(
                f"[行为偏差·WARN] 确认偏差信号偏强：正面/负面措辞 ≈ {ratio:.1f}:1（>5:1）。"
                "即便已有风险章节，正负论据严重失衡仍值得复核是否选择性呈现证据。"
            )

    # ── ② 锚定效应 ──────────────────────────────────
    has_anchor = any(re.search(p, text, re.I) for p in ANCHOR_WORDS)
    has_absolute = any(re.search(p, text, re.I) for p in ABSOLUTE_VAL_WORDS)
    has_valuation = bool(re.search(r"估值|目标价|PE|PB|市盈率|市净率", text, re.I))
    if has_valuation and has_anchor and not has_absolute:
        warns.append(
            "[行为偏差·WARN] 锚定效应信号：估值主要锚定「历史均值/同行平均」，"
            "缺少独立的绝对估值（DCF/内在价值/DDM）作对照。"
            "历史区间锚定在范式切换/景气拐点时会系统性失真，建议补绝对估值交叉验证。"
        )

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="行为金融偏差侦测器（P1-3）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = detect_behavioral_bias(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 行为偏差侦测 PASS: {report_path.name}")
        else:
            print(f"⚠️ 行为偏差侦测 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
