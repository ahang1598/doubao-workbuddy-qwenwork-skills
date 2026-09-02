#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""六面共振 / 背离裁决验证器（accuracy-uplift v14 · P1-6）

设计动机
─────────────────────────────────────────────────────────────────────
Intent-1 汇总决策报告的 §五用「六维加权评分」得出结论。加权法的致命弱点是：
**会把方向相反的信号平均掉**——基本面强烈看多(+) 与筹码面高度获利盘待兑现(-)
加权后可能得到一个温吞的"中性偏多"，从而抹掉了真正的决策 alpha：**背离**。

真正经得起推敲的汇总，不是把六个面的分数一加了事，而是先做一张
「六面方向矩阵」，再显式回答：六面是共振(同向)还是背离(异向)？若背离，
哪个面是领先指标、谁胜出、为什么、对买卖四问的影响是什么。

delivery_spec §4.6 已为「Intent-2 多面专项」定义了共振/背离骨架；本验证器
把同一要求延伸到「Intent-1 汇总报告 §五」，确保汇总层不只有加权、还有背离裁决。

校验（软门禁，只 WARN 不阻断）：
① 方向矩阵：是否给出六个面各自的方向（▲/►/▼ 或 看多/中性/看空）
② 共振/背离判定：是否显式判断"全面共振"还是"方向背离"
③ 背离裁决：若存在背离，是否给出"哪个面胜出 + 领先/滞后逻辑 + 对买卖的影响"

仅对 Intent-1 汇总决策报告（交易决策报告_ 前缀且六面齐全）生效。
"""
from __future__ import annotations

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

_FACES = ("基本面", "政策面", "资金面", "筹码面", "技术面", "消息面")
_DIRECTION_TOKENS = ("▲", "▼", "►", "▶", "看多", "看空", "中性", "偏多", "偏空", "多头", "空头")
_RESONANCE_WORDS = ("共振", "同向", "方向一致", "全面看多", "全面看空")
_DIVERGENCE_WORDS = ("背离", "分歧", "方向冲突", "方向相反", "异向")
_VERDICT_WORDS = ("裁决", "胜出", "领先指标", "领先于", "更可信", "以.{0,6}为准", "优先采信", "孰胜")


def validate_resonance_divergence(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    # 仅 Intent-1 汇总决策报告（六面齐全）
    if "交易决策报告_" not in report_path.name:
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")
    face_hits = sum(1 for f in _FACES if f in text)
    if face_hits < 5:
        return warns  # 非六面汇总报告（单面/专项）跳过

    # ① 方向矩阵：六个面附近是否出现明确方向标记
    has_matrix = (
        bool(re.search(r"(方向|评级)\s*矩阵", text))
        or (sum(1 for f in _FACES if f in text) >= 5
            and sum(1 for t in _DIRECTION_TOKENS if t in text) >= 3)
    )
    has_resonance_judgment = any(w in text for w in _RESONANCE_WORDS) or any(w in text for w in _DIVERGENCE_WORDS)
    has_divergence_word = any(w in text for w in _DIVERGENCE_WORDS)
    has_verdict = any(re.search(w, text) for w in _VERDICT_WORDS)

    if not has_matrix:
        warns.append(
            "[六面共振·WARN] §五汇总未见『六面方向矩阵』：建议在六维加权之外，先列一张表给出"
            "基本面/政策面/资金面/筹码面/技术面/消息面 各自的方向（▲看多 / ►中性 / ▼看空）+ 核心数据依据，"
            "再做共振/背离研判。纯加权评分会把方向相反的信号平均掉，丢失背离这一关键决策信号。"
        )
    if not has_resonance_judgment:
        warns.append(
            "[六面共振·WARN] §五未显式判断六面是『共振（同向）』还是『背离（异向）』。"
            "汇总层的核心价值正是识别共振强度与背离：六面同向 → 强信号；出现异向 → 必须裁决。"
        )
    elif has_divergence_word and not has_verdict:
        warns.append(
            "[六面背离·WARN] 已指出存在背离，但未给出明确『裁决』：须写清哪个面胜出、"
            "为什么（资金/消息/技术常为领先指标，基本面/政策面为同步或滞后），以及对买卖四问"
            "（能不能做/何时做/做多少/何时卖）的具体影响——禁止『看多但需谨慎』式含糊收尾。"
        )
    return warns


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="六面共振/背离裁决验证器（P1-6）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_resonance_divergence(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 六面共振/背离验证 PASS: {report_path.name}")
        else:
            print(f"⚠️ 六面共振/背离验证 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
