#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""逆向估值验证器 — 让市场预期「显性化」再与自己对赌

设计目的（accuracy-uplift v13 · P1-5）
─────────────────────────────────────────────────────────────────────
正向估值（给假设→算出价值）容易陷入「先有目标价、再凑假设」。逆向估值
反过来：从【当前股价】反推【市场隐含的增长/利润假设】，再与自己的独立
判断对比——这是检验「市场是不是疯了 / 还是我错了」的最锋利工具。

本验证器校验估值章节是否完成逆向估值闭环：
─────────────────────────────────────────────────────────────────────
① 反推动作：从当前股价/市值反推「隐含永续增长率 / 隐含 NOPAT 增速 /
   隐含 ROE / 隐含未来 N 年利润 CAGR」之一
② 对比动作：把【市场隐含假设】与【自身独立预测】并列，给出
   「市场过于乐观 / 过于悲观 / 基本合理」的明确判断
③ 落到决策：该判断如何影响买卖结论（预期差是机会还是陷阱）
④ 隐含 PE 反查（对标 FF G18 估值反推自检）：当「当前市值 ÷ 自身预测
   基准净利」推出的隐含 PE 与历史中枢 / 可比中枢偏离 > 2x 时，必须反查
   是「成长溢价合理」还是「漏算了某段业绩 / 假设过激」——防止估值与
   盈利预测脱节而不自知。

软门禁性质：只 WARN，不阻断。短线/单面报告不要求。
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

REVERSE_ACTION = [
    r"逆向估值", r"反向估值", r"隐含(增长|增速|假设|预期|永续)",
    r"市场隐含", r"股价.{0,8}(反推|隐含|倒推)", r"反推.{0,8}(增长|增速|利润|假设|预期)",
    r"implied\s*(growth|assumption)",
]
COMPARE_ACTION = [
    r"(市场|隐含).{0,20}(乐观|悲观|高估|低估|合理|偏高|偏低)",
    r"(隐含|市场预期).{0,20}(vs|对比|相比|高于|低于|对照).{0,20}(自身|我方|独立|预测)",
    r"预期差",
]

# ④ 隐含 PE 反查（FF G18）：识别报告是否做了「市值÷预测净利→隐含PE→与中枢比对」自检
IMPLIED_PE_ACTION = [
    r"隐含\s*PE", r"隐含市盈率",
    r"(市值|总市值|股价).{0,12}(÷|/|除以).{0,12}(预测|预期|基准|未来).{0,8}净利",
    r"(预测|预期|基准).{0,8}净利.{0,12}(对应|隐含|反推).{0,8}(PE|市盈率)",
    r"(隐含|对应)\s*PE.{0,16}(中枢|历史|可比|分位)",
]


def validate_reverse_valuation(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")

    # 仅对含估值章节的报告要求
    has_valuation = bool(re.search(r"4\.1\.5|估值与定价|目标价|内在价值|DCF|PEG|Forward\s*PE", text, re.I))
    if not has_valuation:
        return warns

    has_reverse = any(re.search(p, text, re.I) for p in REVERSE_ACTION)
    has_compare = any(re.search(p, text, re.I) for p in COMPARE_ACTION)
    has_implied_pe = any(re.search(p, text, re.I) for p in IMPLIED_PE_ACTION)

    if not has_reverse:
        warns.append(
            "[逆向估值·WARN] 估值章节缺少「逆向估值」闭环：未从当前股价/市值反推市场隐含假设。"
            "建议补充：以当前股价倒推市场隐含的永续增长率 / 未来 N 年利润 CAGR，"
            "再与自身独立预测并列，判断「市场过于乐观 / 过于悲观 / 基本合理」。"
        )
    elif not has_compare:
        warns.append(
            "[逆向估值·WARN] 已做隐含假设反推，但未把「市场隐含假设 vs 自身独立预测」明确对比并下判断。"
            "逆向估值的价值在于显性化预期差——必须给出市场是否高/低估的结论及其对买卖决策的影响。"
        )

    # ④ 隐含 PE 反查（对标 FF G18 估值反推自检）
    if not has_implied_pe:
        warns.append(
            "[逆向估值·WARN] 缺少「隐含 PE 反查」自检：未用『当前市值 ÷ 自身预测基准净利』推出隐含 PE "
            "并与历史中枢 / 可比公司中枢比对。建议补充：若隐含 PE 与中枢偏离 > 2x，必须反查是"
            "『成长溢价合理』还是『漏算某段业绩 / 假设过激』，防止估值结论与盈利预测悄然脱节。"
        )

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="逆向估值验证器（P1-5）")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_reverse_valuation(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 逆向估值验证 PASS: {report_path.name}")
        else:
            print(f"⚠️ 逆向估值验证 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
