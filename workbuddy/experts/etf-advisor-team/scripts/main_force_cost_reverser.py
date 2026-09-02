#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main_force_cost_reverser — 主力成本反推融合器（v1.21 第 2 件）

融合三源数据反推主力成本带与浮盈/浮亏五档分类：
  1. pytdx 大单 VWAP（来自 pytdx_tick_scraper.py 输出）
  2. 东方财富 5min 资金流（主力净流入加权 VWAP，需 capital_flow_scraper 落盘）
  3. 龙虎榜知名席位的成交均价（来自 longhubang_seat_winrate.py 输出）

按 confidence 加权融合，输出主力浮盈/浮亏 5 档：
    深亏 / 轻亏 / 盈亏临界 / 中盈 / 深盈

CLI：
    python main_force_cost_reverser.py {code} [--current-price P] [--out FinancialData/{code}_main_cost_fused.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pnl_tier(current_price: float, cost: float) -> str:
    if cost <= 0:
        return "未知"
    pct = (current_price - cost) / cost * 100
    if pct < -15:
        return "深亏"
    if pct < -5:
        return "轻亏"
    if pct < 5:
        return "盈亏临界"
    if pct < 15:
        return "中盈"
    return "深盈"


def main() -> None:
    parser = argparse.ArgumentParser(description="主力成本反推融合器（v1.21 第 2 件）")
    parser.add_argument("code", help="6 位股票代码")
    parser.add_argument("--current-price", type=float, default=None, help="当前股价（缺省从 quote 读）")
    parser.add_argument("--out", default=None, help="输出 JSON 路径")
    args = parser.parse_args()

    code = args.code.strip()
    if len(code) != 6 or not code.isdigit():
        print(json.dumps({"error": f"非法股票代码：{code}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

    fdata = Path(__file__).resolve().parents[3] / "FinancialData"

    # 源 1：pytdx 大单 VWAP
    pytdx = _load_json(fdata / f"{code}_pytdx_ticks.json") or {}
    s1_cost = pytdx.get("vwap_large_order") or 0.0
    s1_confidence = 0.40 if s1_cost > 0 and pytdx.get("source") == "pytdx" else 0.10

    # 源 2：东财 5min 资金流加权 VWAP（capital_flow_scraper 输出）
    cap = _load_json(fdata / f"{code}_capital_flow.json") or _load_json(fdata / f"{code}_capital_flow_5min.json") or {}
    s2_cost = cap.get("main_net_flow_vwap") or cap.get("vwap_main_inflow") or 0.0
    s2_confidence = 0.30 if s2_cost > 0 else 0.10

    # 源 3：龙虎榜知名席位加权均价
    lhb = _load_json(fdata / f"{code}_longhubang_seat_signal.json") or {}
    seats = lhb.get("seat_signals", [])
    s3_amounts = [abs(float(s.get("net_amount", 0))) for s in seats]
    s3_cost = 0.0
    total_amt = sum(s3_amounts)
    if total_amt > 0:
        # 没有具体成交均价时，回退到当前价附近 ±2% 作为近似
        # 真正生产环境中 longhubang 应输出 avg_price 字段
        s3_cost = sum(
            (float(s.get("avg_price", 0)) or 0) * abs(float(s.get("net_amount", 0)))
            for s in seats
        ) / total_amt
    s3_confidence = 0.30 if s3_cost > 0 else 0.10

    # 当前价
    cur_price = args.current_price
    if cur_price is None:
        qobj = _load_json(fdata / f"{code}_quote.json") or {}
        cur_price = qobj.get("current_price") or qobj.get("price") or qobj.get("last") or 0.0
    cur_price = float(cur_price or 0)

    # 加权融合
    sources = [
        {"name": "pytdx_large_vwap", "cost": s1_cost, "confidence": s1_confidence},
        {"name": "em_5min_main_flow_vwap", "cost": s2_cost, "confidence": s2_confidence},
        {"name": "longhubang_known_seats_vwap", "cost": s3_cost, "confidence": s3_confidence},
    ]
    eff_sources = [s for s in sources if s["cost"] > 0]
    total_conf = sum(s["confidence"] for s in eff_sources)
    fused_cost = (
        sum(s["cost"] * s["confidence"] for s in eff_sources) / total_conf
        if total_conf > 0
        else 0.0
    )

    tier = _pnl_tier(cur_price, fused_cost)
    pct = (cur_price - fused_cost) / fused_cost * 100 if fused_cost > 0 else None

    out_obj = {
        "code": code,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "current_price": cur_price,
        "sources": sources,
        "effective_source_count": len(eff_sources),
        "fused_main_force_cost": round(fused_cost, 4) if fused_cost > 0 else None,
        "main_force_pnl_pct": round(pct, 2) if pct is not None else None,
        "main_force_pnl_tier": tier,
        "fused_main_cost_band": {
            "lower": round(fused_cost * 0.97, 4) if fused_cost > 0 else None,
            "upper": round(fused_cost * 1.03, 4) if fused_cost > 0 else None,
        },
        "warning": None if len(eff_sources) >= 2 else "有效源 < 2 个，结果可信度低",
    }

    out_path = Path(args.out) if args.out else fdata / f"{code}_main_cost_fused.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out_obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
