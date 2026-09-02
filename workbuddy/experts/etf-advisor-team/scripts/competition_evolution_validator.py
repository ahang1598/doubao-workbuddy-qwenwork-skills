#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""竞争格局演化验证器 — 让产业分析从「快照」走向「电影」

设计目的（accuracy-uplift v13 · P2-2）
─────────────────────────────────────────────────────────────────────
现有产业层（4.1.2）强制 CR3/CR5、技术路线、供应链——这些都是「当下快照」。
但投资是预判 3 年后的格局，不是今天的格局。本验证器要求产业分析包含
动态演化三要素：
─────────────────────────────────────────────────────────────────────
① 竞争格局演化：未来 1-3 年 CR3/CR5 上升/持平/下降的判断 + 驱动因素
   （最好带情景概率），潜在进入者来自哪个方向
② 进入壁垒趋势：品牌/规模/专利/转换成本/网络效应 五类壁垒是上升还是下降
③ 颠覆式创新风险：低端颠覆 / 新市场颠覆 的风险等级，头部公司是在持续性
   创新还是已陷入「创新者的窘境」

软门禁性质：只 WARN，不阻断。短线/单面非基本面报告不强制。
可选：{stem}_decomposition_tree.json 中行业节点若标注份额变化方向可加分。
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

ELEMENT_PATTERNS = {
    "竞争格局演化趋势（未来CR变化+驱动）": [
        r"(CR\d|集中度).{0,20}(上升|提升|提高|下降|降低|持平|维持|演化|演进|趋势)",
        r"格局.{0,8}(演化|演进|变化|趋势|未来)",
        r"未来.{0,6}(1|2|3|三).{0,3}年.{0,12}(格局|集中度|份额)",
        r"潜在(进入者|竞争者|玩家)",
    ],
    "进入壁垒趋势": [
        r"(进入)?壁垒.{0,12}(上升|提升|抬高|下降|降低|减弱|增强|趋势)",
        r"(品牌|规模|专利|转换成本|网络效应).{0,16}壁垒",
        r"护城河.{0,8}(变宽|变窄|加深|收窄|趋势)",
    ],
    "颠覆式创新风险": [
        r"颠覆(式|性)?(创新|技术|风险)",
        r"创新者的窘境",
        r"(低端|新市场).{0,4}颠覆",
        r"(替代|颠覆).{0,12}(技术路线|商业模式)",
    ],
}


def validate_competition_evolution(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")

    # 仅对含产业层分析的报告要求
    has_industry = bool(re.search(r"4\.1\.2|产业层|行业格局|竞争格局|CR\d|行业分析", text, re.I))
    if not has_industry:
        return warns

    missing = []
    for elem_name, pats in ELEMENT_PATTERNS.items():
        if not any(re.search(p, text, re.I) for p in pats):
            missing.append(elem_name)

    if len(missing) == len(ELEMENT_PATTERNS):
        warns.append(
            "[竞争演化·WARN] 产业分析停留在「当下快照」，缺少动态演化三要素："
            "① 未来 1-3 年竞争格局演化趋势（CR 变化+驱动+潜在进入者）；"
            "② 五类进入壁垒的升降趋势；③ 颠覆式创新风险等级。"
            "投资是预判 3 年后的格局，不是今天的格局。"
        )
    else:
        for m in missing:
            warns.append(f"[竞争演化·WARN] 竞争格局动态分析缺少要素「{m}」，建议补齐。")

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="竞争格局演化验证器（P2-2）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_competition_evolution(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 竞争格局演化验证 PASS: {report_path.name}")
        else:
            print(f"⚠️ 竞争格局演化验证 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
