#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""管理层资本配置能力审计器 — 价值创造的唯一源泉

设计目的（accuracy-uplift v13 · P1-1）
─────────────────────────────────────────────────────────────────────
基本面分析最终落到「内在价值 + 安全边际」，但如果管理层持续把超额利润
投到低回报项目，内在价值的计算基础就塌了。资本配置是 CEO 最重要的职责，
现有框架只做定性高管背景，缺少对资本配置能力的定量评估章节。

本审计校验报告（基本面/汇总决策深稿）是否覆盖资本配置三要素：
─────────────────────────────────────────────────────────────────────
① 增量资本回报率 ROIIC（ΔNOPAT/ΔInvested Capital 或 ΔEBIT/ΔIC）与 WACC
   的比较，以及 ROIC 的多年趋势——回答「每投 1 元新资本创造多少额外利润」
② 资本配置组合历史效率：过去若干年在 并购/回购/分红/再投资/还债 之间
   如何分配，每类决策的事后回报评价
③ 薪酬激励对齐度：管理层薪酬与 ROIC/EVA/长期股东回报 的挂钩程度
   （vs 仅与规模/营收挂钩——后者是典型代理人问题信号）

可选定量产物：{stem}_capital_allocation.json（若存在则做数值校验）
  { "roiic": 0.18, "wacc": 0.09, "roic_trend": [0.12,0.14,0.16],
    "allocation": {"capex":0.5,"ma":0.2,"buyback":0.1,"dividend":0.2},
    "pay_alignment": "high|medium|low" }

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

# 触发该审计的报告类型（基本面深稿 / 含资本配置诉求）
SECTION_HINT = re.compile(r"资本配置|capital\s*allocation|ROIIC|增量资本回报|再投资回报", re.I)

ELEMENT_PATTERNS = {
    "ROIIC/增量资本回报 vs WACC": [
        r"ROIIC", r"增量资本回报", r"增量投入资本回报", r"边际资本回报",
        r"每.{0,3}元.{0,6}(新增|增量).{0,8}资本.{0,12}(回报|利润)",
    ],
    "资本配置组合历史效率（并购/回购/分红/再投资）": [
        r"(并购|收购).{0,30}(回购|分红|再投资|资本开支|CapEx)",
        r"(回购|分红).{0,30}(并购|再投资|资本开支|CapEx)",
        r"资本配置.{0,10}(组合|历史|效率|结构)",
    ],
    "薪酬激励对齐度": [
        r"薪酬.{0,12}(挂钩|对齐|激励|绑定).{0,16}(ROIC|ROE|EVA|股东|业绩|利润)",
        r"(股权激励|管理层激励).{0,20}(考核|对齐|挂钩)",
        r"激励.{0,8}对齐",
    ],
}


def validate_capital_allocation(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")

    # 仅对「具备资本配置分析诉求」的深稿做强校验：
    # 判定：报告含 4.1.5 估值章节 或 ROIC/WACC 讨论 或 基本面深度标识
    is_deep = bool(
        re.search(r"4\.1\.5|估值与定价|内在价值|安全边际|WACC|ROIC|基本面深度", text)
    )
    if not is_deep:
        return warns  # 短线/单面报告不要求资本配置章节

    if not SECTION_HINT.search(text):
        warns.append(
            "[资本配置·WARN] 报告做了估值/内在价值分析，但未见「管理层资本配置能力」专项评估。"
            "资本配置是 CEO 最重要的职责，建议新增章节回答三问："
            "① 增量资本回报率 ROIIC 是否高于 WACC（每投 1 元新资本创造多少额外利润）；"
            "② 并购/回购/分红/再投资 的历史配置效率；③ 薪酬激励与长期股东回报的对齐度。"
        )
        return warns

    # 已有章节 → 逐要素检查
    for elem_name, pats in ELEMENT_PATTERNS.items():
        if not any(re.search(p, text, re.I) for p in pats):
            warns.append(
                f"[资本配置·WARN] 资本配置评估缺少要素「{elem_name}」，建议补齐。"
            )

    # 可选定量产物校验
    qa_path = report_path.parent / f"{report_path.stem}_capital_allocation.json"
    if qa_path.exists():
        try:
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            roiic = qa.get("roiic")
            wacc = qa.get("wacc")
            if roiic is not None and wacc is not None:
                if float(roiic) < float(wacc):
                    warns.append(
                        f"[资本配置·WARN] 量化数据显示 ROIIC {float(roiic):.1%} < WACC {float(wacc):.1%}，"
                        "管理层正在以低于资本成本的回报投放增量资本（价值毁灭信号），"
                        "估值时不应给予增长溢价，正文须显式讨论这一点。"
                    )
            if str(qa.get("pay_alignment", "")).lower() == "low":
                warns.append(
                    "[资本配置·WARN] 量化数据标记薪酬激励对齐度为 low（与规模而非股东回报挂钩），"
                    "存在代理人问题风险，应在治理段提示。"
                )
        except Exception:
            pass

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="管理层资本配置能力审计器（P1-1）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_capital_allocation(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 资本配置审计 PASS: {report_path.name}")
        else:
            print(f"⚠️ 资本配置审计 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
