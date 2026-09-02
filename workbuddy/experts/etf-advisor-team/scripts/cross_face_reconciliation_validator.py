#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""交叉勾稽对齐验证器（accuracy-uplift v15 · 分面深写流水线 · 阶段B）

设计动机
─────────────────────────────────────────────────────────────────────
v15 把 Intent-1 综合买卖决策**全周期统一**改为「分面深写流水线」：六个面先各自
独立深写成 6 份单面深稿（OutputReport/分面深稿_{面}_{code}_{简称}_{时间戳}.md），
再汇总（结构统一、深度随周期适配）。分面独立写作的最大风险是——**六份稿子各自
取数、同一事实口径打架**（基本面写营收+30%、资金面引用另一个数），拼进汇总后
自相矛盾却无人发现。

本验证器在汇总报告交付前做「交叉勾稽」软门禁：
─────────────────────────────────────────────────────────────────────
① 齐备性：6 份单面深稿是否都已落盘（基本面/政策面/资金面/筹码面/技术面/消息面）
② 摘要卡：每份深稿末尾是否产出【摘要卡】结构块（供汇总二次综合）
③ 事实一致性：跨深稿引用的「现价」这一**单一客观事实**是否一致（偏离 >0.5% 即冲突）
④ 方向可汇总：6 份摘要卡是否各自给出明确方向（▲/►/▼），供 §5.1.5 矩阵裁决

软门禁性质：只 WARN，不阻断。**全周期统一生效**（所有交易风格的汇总决策报告都跑，
report_quality_checker 未把本校验器纳入 _HEAVY_VALIDATORS 重型跳过集合）。自门控：
找不到任何分面深稿时静默通过（兼容历史内联产出不误伤）。
与 v12/v13/v14 一致：validate_cross_face_reconciliation(report_path) -> List[str]。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_FACES = ("基本面", "政策面", "资金面", "筹码面", "技术面", "消息面")
_PRICE_TOLERANCE = 0.005  # 现价跨稿一致性容忍度 0.5%
_DIRECTION_TOKENS = ("▲", "▼", "►", "▶", "看多", "看空", "中性", "偏多", "偏空")


def _derive_face_draft_paths(report_path: Path) -> Optional[Dict[str, Path]]:
    """由最终报告名推导 6 份单面深稿路径。
    最终报告: 交易决策报告_{code}_{简称}_{时间戳}.md
    单面深稿: 分面深稿_{面}_{code}_{简称}_{时间戳}.md
    """
    m = re.match(r"交易决策报告_(.+)$", report_path.stem)
    if not m:
        return None
    tail = m.group(1)  # {code}_{简称}_{时间戳}
    return {face: report_path.parent / f"分面深稿_{face}_{tail}.md" for face in _FACES}


def _extract_current_price(text: str) -> Optional[float]:
    """抽取首个「现价/当前价/最新价/收盘价」数值（元）。"""
    m = re.search(r"(现价|当前价|最新价|现价格|收盘价)[^\d\-]{0,8}(\d+\.?\d*)", text)
    if m:
        try:
            return float(m.group(2))
        except ValueError:
            return None
    return None


def validate_cross_face_reconciliation(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        return warns
    # 仅对 Intent-1 汇总决策报告生效
    if "交易决策报告_" not in report_path.name:
        return warns
    drafts = _derive_face_draft_paths(report_path)
    if drafts is None:
        return warns

    existing = {f: p for f, p in drafts.items() if p.exists()}
    missing = [f for f in _FACES if f not in existing]

    # ① 齐备性：
    #    ⚠️ v17 修复反向激励——旧逻辑 "一份都没有 → 静默通过" 会奖励"彻底跳过阶段A"
    #    （0 份深稿反而 0 WARN，做一半才被提醒），这正是阶段A 被零成本跳过的根因之一。
    #    现改为：0 份 = 阶段A 完全未执行，是【最严重】情形，必须 WARN（硬拦截已由
    #    report_quality_checker.check_stage_a_face_drafts 负责，此处软门禁再敲一次警钟）。
    if not existing:
        warns.append(
            "[交叉勾稽·WARN] 未发现任何阶段A 单面深稿（分面深稿_{面}_…）——疑似完全跳过了"
            "v15 分面深写流水线的阶段A，直接内联写汇总报告。这会导致六面纵深被压缩、"
            "交叉勾稽与方向矩阵无从建立。请按铁律#1 先六面各产一份分面深稿再汇总。"
            "（注：硬门禁 GATE0·分面深写 会直接 FAIL 拦截缺失情形。）"
        )
        return warns
    if missing:
        warns.append(
            "[交叉勾稽·WARN] 分面深写流水线疑似未完整执行：已落盘单面深稿 "
            f"{sorted(existing.keys())}，但缺 {missing}。波段/中长线 Intent-1 应六面各产一份"
            "「分面深稿_{面}_…」中间稿并保留可追溯，请补齐缺失的面或确认是否走了内联写法。"
        )

    # ② 摘要卡 + ④ 方向可汇总
    no_card = [f for f, p in existing.items() if "摘要卡" not in p.read_text(encoding="utf-8", errors="replace")]
    if no_card:
        warns.append(
            f"[交叉勾稽·WARN] 以下单面深稿缺末尾【摘要卡】结构块：{no_card}。"
            "摘要卡（方向+评级+关键数据+核心依据+信源）是阶段C 汇总二次综合的输入，缺失会导致"
            "汇总退化为重读全文、丢失结构化方向信息。"
        )
    no_dir = []
    for f, p in existing.items():
        txt = p.read_text(encoding="utf-8", errors="replace")
        # 取摘要卡附近文本判断方向
        idx = txt.find("摘要卡")
        seg = txt[idx:] if idx >= 0 else txt
        if not any(t in seg for t in _DIRECTION_TOKENS):
            no_dir.append(f)
    if no_dir:
        warns.append(
            f"[交叉勾稽·WARN] 以下单面深稿摘要卡未给出明确方向（▲看多/►中性/▼看空）：{no_dir}。"
            "无方向则 §5.1.5 六面方向矩阵无法成立、共振/背离裁决落空。"
        )

    # ③ 事实一致性：现价跨稿（含最终报告）必须一致
    prices: Dict[str, float] = {}
    for f, p in existing.items():
        pr = _extract_current_price(p.read_text(encoding="utf-8", errors="replace"))
        if pr is not None:
            prices[f] = pr
    final_price = _extract_current_price(report_path.read_text(encoding="utf-8", errors="replace"))
    if final_price is not None:
        prices["最终报告"] = final_price
    if len(prices) >= 2:
        lo, hi = min(prices.values()), max(prices.values())
        if lo > 0 and (hi - lo) / lo > _PRICE_TOLERANCE:
            detail = "、".join(f"{k}={v}" for k, v in prices.items())
            warns.append(
                f"[交叉勾稽·WARN] 各单面深稿/最终报告引用的「现价」不一致（{detail}），"
                "偏离超 0.5%。现价是单一客观事实，必须全稿统一——请回改对应深稿对齐到同一现价快照，"
                "否则六面分析建立在不同价格基准上，止盈/止损/空间测算全部失真。"
            )

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="交叉勾稽对齐验证器（v15 · 分面深写流水线阶段B）")
    parser.add_argument("report", help="最终汇总决策报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_cross_face_reconciliation(report_path)
    if args.format == "json":
        import json
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 交叉勾稽对齐 PASS: {report_path.name}")
        else:
            print(f"⚠️ 交叉勾稽对齐 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
