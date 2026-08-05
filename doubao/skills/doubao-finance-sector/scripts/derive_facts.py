#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derive calculable fields in facts.json from raw market inputs.

This script separates data collection from arithmetic. It only computes fields
that are fully determined by existing raw inputs; it never invents prices,
turnover series, valuation, sources, URLs, roles, or selected stocks.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path
from typing import Any


GROUPS = ("放量上攻", "缩量上行", "缩量回调", "放量杀跌")


def as_num(v: Any) -> float | None:
    if v in (None, "") or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def clean_num(v: float, digits: int = 2) -> float:
    out = round(v, digits)
    return 0.0 if out == -0.0 else out


def pct(close_t: float, base: float) -> float | None:
    if base == 0:
        return None
    return clean_num((close_t / base - 1.0) * 100.0)


def avg(nums: list[float]) -> float:
    return clean_num(sum(nums) / len(nums))


def derive_sector(sc: dict[str, Any], changes: list[str]) -> None:
    close_point = as_num(sc.get("close_point"))
    prev_close = as_num(sc.get("prev_close"))
    d7_base = as_num(sc.get("d7_close_base"))
    d7_close_t = as_num(sc.get("d7_close_t"))

    if d7_close_t is None and close_point is not None:
        sc["d7_close_t"] = clean_num(close_point)
        d7_close_t = close_point
        changes.append("sector_checks: close_point -> d7_close_t")

    if close_point is not None and prev_close is not None:
        val = pct(close_point, prev_close)
        if val is not None and sc.get("daily_change") != val:
            sc["daily_change"] = val
            changes.append("sector_checks: 复算 daily_change")

    if d7_close_t is not None and d7_base is not None:
        val = pct(d7_close_t, d7_base)
        if val is not None and sc.get("change_7d") != val:
            sc["change_7d"] = val
            changes.append("sector_checks: 复算 change_7d")

    turns = sc.get("d7_turnovers")
    if isinstance(turns, list) and len(turns) == 7:
        vals = [as_num(x) for x in turns]
        if all(v is not None for v in vals):
            val = avg([float(v) for v in vals])
            if sc.get("turnover_7d") != val:
                sc["turnover_7d"] = val
                changes.append("sector_checks: 复算 turnover_7d")


def derive_stock(s: dict[str, Any], idx: int, changes: list[str]) -> None:
    label = str(s.get("name") or f"stock_checks[{idx}]").strip()
    base = as_num(s.get("d7_close_base"))
    close_t = as_num(s.get("d7_close_t"))
    if base is not None and close_t is not None:
        val = pct(close_t, base)
        if val is not None and s.get("change_7d") != val:
            s["change_7d"] = val
            changes.append(f"{label}: 复算 change_7d")

    turns = s.get("d7_turnovers")
    if isinstance(turns, list) and len(turns) == 7:
        vals = [as_num(x) for x in turns]
        if all(v is not None for v in vals):
            val = avg([float(v) for v in vals])
            if s.get("turnover_7d") != val:
                s["turnover_7d"] = val
                changes.append(f"{label}: 复算 turnover_7d")


def expected_group(change: float | None, turnover: float | None, turnover_7d: float | None) -> str | None:
    if change is None or turnover is None or turnover_7d is None:
        return None
    if change >= 0 and turnover >= turnover_7d:
        return "放量上攻"
    if change >= 0:
        return "缩量上行"
    if turnover >= turnover_7d:
        return "放量杀跌"
    return "缩量回调"


def derive_groups(obj: dict[str, Any], changes: list[str]) -> None:
    checks = obj.get("stock_checks")
    if not isinstance(checks, list):
        return
    groups = {g: [] for g in GROUPS}
    ok = True
    for s in checks:
        if not isinstance(s, dict):
            ok = False
            continue
        name = str(s.get("name") or "").strip()
        group = expected_group(as_num(s.get("change")), as_num(s.get("turnover")), as_num(s.get("turnover_7d")))
        if not name or group is None:
            ok = False
            continue
        groups[group].append(name)
    if ok and obj.get("divergence_groups") != groups:
        obj["divergence_groups"] = groups
        changes.append("divergence_groups: 按 change × turnover/turnover_7d 自动生成四组")


def derive(obj: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    changes: list[str] = []
    sc = obj.get("sector_checks")
    if isinstance(sc, dict):
        derive_sector(sc, changes)
    checks = obj.get("stock_checks")
    if isinstance(checks, list):
        for i, s in enumerate(checks):
            if isinstance(s, dict):
                derive_stock(s, i, changes)
    derive_groups(obj, changes)
    return obj, changes


def main() -> int:
    ap = argparse.ArgumentParser(description="从 facts.json 原始取数字段派生涨跌、近7日日均成交额与四组分化")
    ap.add_argument("facts", help="待派生 facts.json")
    ap.add_argument("-o", "--output", help="输出路径；缺省为原地写回并创建 .bak")
    ap.add_argument("--no-backup", action="store_true", help="原地写回时不创建 .bak")
    args = ap.parse_args()

    path = Path(args.facts)
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("[错误] facts.json 顶层必须是对象。")
    obj, changes = derive(obj)

    out = Path(args.output) if args.output else path
    if out == path and not args.no_backup:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        print(f"已备份原文件：{backup}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入派生后 facts.json：{out}")
    if changes:
        print("派生 / 覆盖项：")
        for item in changes:
            print(f"- {item}")
    else:
        print("未发现可派生字段；若仍有缺口，请回到 seed_finance_search 补原始取数。")
    print("下一步：运行 `python3 scripts/lint_analysis.py --strict <facts.json>` 做验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
