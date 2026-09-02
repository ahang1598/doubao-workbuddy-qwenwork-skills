#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""northbound_seat_winrate — 21 海外托管席位库（v1.21 第 7 件）

内置 21 个主流海外托管席位（HKSCC 通过 CCASS 公布）的分类标签：
  - 配置型（长期资金）：JPMorgan、BlackRock、Vanguard、State Street、Northern Trust、
                       BNY Mellon、HSBC、Standard Chartered、Citi（托管）
  - 交易型（短线 / 对冲）：Nomura、Barclays、Morgan Stanley、Goldman Sachs（交易簿）、
                          UBS（自营）、Credit Suisse、Deutsche Bank
  - 量化型：Citi（量化簿）、Susquehanna（虎符）、Citadel、Two Sigma、Renaissance

输出：smart_money_pct vs trading_book_pct + weighted_smart_score 0-100

CLI：
    python northbound_seat_winrate.py {code} [--out FinancialData/chip_intelligence/northbound_seat_db.json]
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


NORTHBOUND_SEATS: Dict[str, Dict[str, Any]] = {
    # 配置型（smart money = True）
    "JPMORGAN CHASE BANK, NATIONAL ASSOCIATION": {"category": "配置型", "smart_money": True, "weight": 1.0},
    "JPMORGAN CHASE BANK, N.A.": {"category": "配置型", "smart_money": True, "weight": 1.0},
    "BLACKROCK (HK) LIMITED": {"category": "配置型", "smart_money": True, "weight": 1.0},
    "VANGUARD INVESTMENTS HONG KONG LIMITED": {"category": "配置型", "smart_money": True, "weight": 1.0},
    "STATE STREET BANK AND TRUST COMPANY": {"category": "配置型", "smart_money": True, "weight": 1.0},
    "THE NORTHERN TRUST COMPANY (AVFC)": {"category": "配置型", "smart_money": True, "weight": 1.0},
    "THE BANK OF NEW YORK MELLON": {"category": "配置型", "smart_money": True, "weight": 0.9},
    "THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED": {"category": "配置型", "smart_money": True, "weight": 0.95},
    "STANDARD CHARTERED BANK (HONG KONG) LIMITED": {"category": "配置型", "smart_money": True, "weight": 0.9},
    "CITIBANK, N.A.": {"category": "配置型", "smart_money": True, "weight": 0.9},

    # 交易型（短线、smart money = 中性）
    "NOMURA INTERNATIONAL (HONG KONG) LIMITED": {"category": "交易型", "smart_money": False, "weight": 0.5},
    "BARCLAYS BANK PLC": {"category": "交易型", "smart_money": False, "weight": 0.5},
    "MORGAN STANLEY HONG KONG SECURITIES LIMITED": {"category": "交易型", "smart_money": False, "weight": 0.6},
    "GOLDMAN SACHS (ASIA) SECURITIES LIMITED": {"category": "交易型", "smart_money": False, "weight": 0.6},
    "UBS AG": {"category": "交易型", "smart_money": False, "weight": 0.55},
    "CREDIT SUISSE (HONG KONG) LIMITED": {"category": "交易型", "smart_money": False, "weight": 0.5},
    "DEUTSCHE BANK AKTIENGESELLSCHAFT": {"category": "交易型", "smart_money": False, "weight": 0.5},

    # 量化型（高频，smart money = False）
    "CITIGROUP GLOBAL MARKETS LIMITED": {"category": "量化型", "smart_money": False, "weight": 0.3},
    "SUSQUEHANNA HONG KONG LIMITED": {"category": "量化型", "smart_money": False, "weight": 0.2},
    "CITADEL SECURITIES (HONG KONG) LIMITED": {"category": "量化型", "smart_money": False, "weight": 0.2},
    "RENAISSANCE TECHNOLOGIES LLC": {"category": "量化型", "smart_money": False, "weight": 0.2},
}


def _normalize(s: str) -> str:
    return (s or "").strip().upper()


def _classify_seat(name: str) -> Dict[str, Any]:
    key = _normalize(name)
    for known_key, info in NORTHBOUND_SEATS.items():
        if known_key.upper() in key or key in known_key.upper():
            return {"seat_name": name, "matched": True, **info}
    return {"seat_name": name, "matched": False, "category": "未识别", "smart_money": False, "weight": 0.3}


def _load_ccass(code: str) -> Optional[List[Dict[str, Any]]]:
    fdata = Path(__file__).resolve().parents[3] / "FinancialData"
    cand = fdata / f"{code}_ccass.json"
    if not cand.exists():
        return None
    try:
        obj = json.loads(cand.read_text(encoding="utf-8"))
        return obj.get("holdings") or obj.get("data") or obj.get("seats") or []
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="北上 21 海外托管席位库（v1.21 第 7 件）")
    parser.add_argument("code", help="6 位股票代码")
    parser.add_argument("--out", default=None, help="单股票快照输出路径")
    parser.add_argument("--db-out", default=None, help="海外托管席位库路径")
    args = parser.parse_args()

    code = args.code.strip()
    if len(code) != 6 or not code.isdigit():
        print(json.dumps({"error": f"非法股票代码：{code}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

    holdings = _load_ccass(code) or []
    classified: List[Dict[str, Any]] = []
    smart_amount = 0.0
    trading_amount = 0.0
    weighted_smart_sum = 0.0
    total_amount = 0.0

    for h in holdings:
        name = h.get("custodian") or h.get("seat") or h.get("name") or ""
        amount = float(h.get("market_value") or h.get("holding_shares") or h.get("amount") or 0)
        info = _classify_seat(name)
        classified.append({**info, "amount": amount})
        total_amount += amount
        if info.get("smart_money"):
            smart_amount += amount
            weighted_smart_sum += amount * info.get("weight", 0.5)
        elif info.get("category") == "交易型":
            trading_amount += amount

    smart_pct = smart_amount / total_amount * 100 if total_amount > 0 else 0.0
    trading_pct = trading_amount / total_amount * 100 if total_amount > 0 else 0.0
    weighted_smart_score = (
        weighted_smart_sum / total_amount * 100 if total_amount > 0 else 0.0
    )

    snapshot = {
        "code": code,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "total_market_value": round(total_amount, 2),
        "seat_count_matched": sum(1 for c in classified if c.get("matched")),
        "smart_money_pct": round(smart_pct, 2),
        "trading_book_pct": round(trading_pct, 2),
        "weighted_smart_score": round(weighted_smart_score, 2),
        "seat_signals": classified,
    }

    fdata = Path(__file__).resolve().parents[3] / "FinancialData"
    snap_path = Path(args.out) if args.out else fdata / f"{code}_northbound_seat_signal.json"
    db_path = Path(args.db_out) if args.db_out else fdata / "chip_intelligence" / "northbound_seat_db.json"
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    db_path.write_text(json.dumps({
        "version": "v1.21",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "seat_count": len(NORTHBOUND_SEATS),
        "seats": NORTHBOUND_SEATS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
