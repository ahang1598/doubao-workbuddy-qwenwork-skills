#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""数字一致性审计器 — 对抗"数字自相矛盾"

设计目的（accuracy-uplift v12 · 建议 4）
─────────────────────────────────────────────────────────────────────
扫描全文带百分号 / 元 / 倍 / 万 / 亿 的数字，按指标类别聚类：
  ① 同一指标在不同章节出现差值 > 显著阈值 → WARN（必须有显式说明）
  ② 量价拆解：Σ 业务线营收 = 总营收 ± 5% 偏差容忍 → WARN
  ③ 与 {stem}_forecast.json 的预测结果做交叉比对（若存在）→ WARN

软门禁性质：只 WARN，不阻断。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 跟踪的关键指标关键词（中文上下文 → 标准化指标名）
TRACKED_INDICATORS = [
    # name, regex_keywords (在数字附近 30 字内出现任一)
    ("营收增速",   ["营收.{0,8}(增速|同比|增长)", "营业收入.{0,8}(增速|同比|增长)", "收入.{0,8}(同比|YoY)"]),
    ("归母净利增速", ["归母净利.{0,8}(增速|同比|增长)", "净利润.{0,8}(增速|同比|增长)", "净利.{0,8}(同比|YoY)"]),
    ("毛利率",     ["毛利率"]),
    ("净利率",     ["净利率"]),
    ("ROE",       ["ROE"]),
    ("目标价",     ["目标价"]),
    ("PE",        ["PE\\s*(估值|倍|=|目标|为)", "市盈率"]),
    ("综合胜率",   ["综合胜率"]),
]

# 同指标跨章节差值容忍度（绝对值差，单位：百分点 / 元）
INDICATOR_TOLERANCE = {
    "营收增速": 3.0,        # 3 个百分点
    "归母净利增速": 3.0,
    "毛利率": 2.0,
    "净利率": 2.0,
    "ROE": 2.0,
    "目标价": 5.0,          # 5 元
    "PE": 5.0,
    "综合胜率": 5.0,
}

NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])(\d{1,4}(?:\.\d{1,2})?)\s*(%|％|元|倍|万|亿)")


def _section_of_pos(text: str, pos: int) -> str:
    """定位 pos 所在的最近一个 ### 或 #### 标题。"""
    # 向前找最近的 ### 标题
    pre = text[:pos]
    m = list(re.finditer(r"^(#{2,5})\s+(.+?)$", pre, re.M))
    return m[-1].group(2).strip() if m else "正文"


def _extract_indicator_values(text: str) -> Dict[str, List[Tuple[float, str, str]]]:
    """提取指标 -> [(value, unit, section_label), ...]"""
    found: Dict[str, List[Tuple[float, str, str]]] = defaultdict(list)
    for num_m in NUMBER_RE.finditer(text):
        value = float(num_m.group(1))
        unit = num_m.group(2)
        ctx_start = max(0, num_m.start() - 30)
        ctx_end = min(len(text), num_m.end() + 10)
        ctx = text[ctx_start:ctx_end]
        for ind_name, patterns in TRACKED_INDICATORS:
            for p in patterns:
                if re.search(p, ctx):
                    sec = _section_of_pos(text, num_m.start())
                    found[ind_name].append((value, unit, sec))
                    break
    return found


def audit_numeric_consistency(report_path: Path) -> List[str]:
    warns: List[str] = []
    if not report_path.exists():
        warns.append(f"[数字一致性·WARN] 报告文件不存在: {report_path}")
        return warns
    text = report_path.read_text(encoding="utf-8", errors="replace")

    # ── ① 同指标跨章节差值 ────────────────────────────
    indicator_map = _extract_indicator_values(text)
    for ind, items in indicator_map.items():
        if len(items) < 2:
            continue
        # 按单位归并
        by_unit: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        for v, u, sec in items:
            by_unit[u].append((v, sec))
        for u, vs in by_unit.items():
            if len(vs) < 2:
                continue
            values = [v for v, _ in vs]
            spread = max(values) - min(values)
            tol = INDICATOR_TOLERANCE.get(ind, 2.0)
            if spread > tol:
                # 找出最大最小所在章节
                vmax_sec = next(s for v, s in vs if v == max(values))
                vmin_sec = next(s for v, s in vs if v == min(values))
                warns.append(
                    f"[数字一致性·WARN] 指标「{ind}」跨章节差异 {min(values)}{u} ~ {max(values)}{u} "
                    f"（差值 {spread:.2f}{u} > 容忍 {tol}{u}）。"
                    f"高值出现在「{vmax_sec[:30]}」，低值出现在「{vmin_sec[:30]}」。"
                    "若刻意分歧（如卖方一致预期 vs 自有预测），请在正文显式说明分歧原因。"
                )

    # ── ② 业务线营收加总 vs 总营收 ───────────────────────
    # 启发式：含 4.1.4 章节，且 decomposition_tree.json 存在
    tree_path = report_path.parent / f"{report_path.stem}_decomposition_tree.json"
    if tree_path.exists():
        try:
            data = json.loads(tree_path.read_text(encoding="utf-8"))
            total = float(data.get("total_revenue_forecast") or 0)
            if total > 0:
                trees = data.get("trees") or []
                share_sum = sum(float(t.get("revenue_share") or 0) for t in trees if isinstance(t, dict))
                if abs(share_sum - 1.0) > 0.05:
                    warns.append(
                        f"[数字一致性·WARN] 顶层业务线 revenue_share 加总 {share_sum:.2f}，"
                        f"偏离 1.00 超过 0.05；与 total_revenue_forecast {total:.0f} 的拆分一致性存疑。"
                    )
        except Exception:
            pass

    # ── ③ 与 forecast.json 交叉比对 ─────────────────────
    fc_path = report_path.parent / f"{report_path.stem}_forecast.json"
    if fc_path.exists():
        try:
            fc = json.loads(fc_path.read_text(encoding="utf-8"))
            # forecast_engine 输出结构常见字段
            target = None
            for key in ("target_price", "目标价"):
                if key in fc:
                    target = float(fc[key])
                    break
            if target and "目标价" in indicator_map:
                yuan_values = [v for v, u, _ in indicator_map["目标价"] if u == "元"]
                if yuan_values:
                    closest = min(yuan_values, key=lambda x: abs(x - target))
                    if abs(closest - target) > 10.0:
                        warns.append(
                            f"[数字一致性·WARN] 报告正文目标价 {closest} 元 vs forecast_engine 输出 "
                            f"{target} 元 差异 > 10 元，请核对引擎参数与正文是否一致。"
                        )
        except Exception:
            pass

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="数字一致性软门禁审计器")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = audit_numeric_consistency(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 数字一致性软门禁 PASS: {report_path.name}")
        else:
            print(f"⚠️ 数字一致性软门禁 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
