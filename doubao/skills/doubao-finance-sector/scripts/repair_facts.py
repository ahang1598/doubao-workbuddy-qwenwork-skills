#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch-repair mechanical facts.json schema issues after the first lint run.

This script is intentionally conservative: it normalizes field names, source
lane placement, and summary-style top-level keys. Derived arithmetic and stock
grouping belong to derive_facts.py. This script does not invent missing prices,
7-day turnover sequences, or source URLs.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


GROUPS = ("放量上攻", "缩量上行", "缩量回调", "放量杀跌")
MARKET_KINDS = {"market", "change", "retracement", "rebound", "ratio", "fundamental"}
FINANCE_LANE = "seed_finance_search"
GENERAL_LANE = "general_search"


def as_num(v: Any) -> float | None:
    if v in (None, "") or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def first(d: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return None


def set_if_missing(d: dict[str, Any], key: str, value: Any, changes: list[str], label: str) -> None:
    if value in (None, ""):
        return
    if key not in d or d[key] in (None, ""):
        d[key] = value
        changes.append(f"{label}: 补 {key}")


def move_alias(d: dict[str, Any], target: str, aliases: tuple[str, ...], changes: list[str], label: str) -> None:
    if d.get(target) not in (None, ""):
        return
    for key in aliases:
        if key in d and d[key] not in (None, ""):
            d[target] = d[key]
            changes.append(f"{label}: {key} -> {target}")
            return


def tier_from_level(value: Any) -> int | None:
    s = str(value or "").strip()
    if not s:
        return None
    if s in {"1", "一级", "一手", "权威", "官方", "官方发布"}:
        return 1
    if s in {"2", "二级", "媒体原创", "机构媒体", "新闻网站", "报道"}:
        return 2
    if s in {"3", "三级", "自媒体", "个人", "UGC", "ugc"}:
        return 3
    return as_num(s) if as_num(s) in {1.0, 2.0, 3.0} else None


def stock_names(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            name = str(first(item, "name", "stock_name", "股票名称", "证券简称") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            out.append(name)
    return out


def normalize_meta(obj: dict[str, Any], changes: list[str]) -> None:
    meta = obj.get("meta")
    if not isinstance(meta, dict):
        meta = {}
        obj["meta"] = meta
        changes.append("top: 新建 meta")
    set_if_missing(meta, "sector", first(obj, "sector_name", "sector", "板块"), changes, "meta")
    if not meta.get("index_caliber"):
        sector_name = str(first(obj, "sector_name", "sector") or "").strip()
        sector_code = str(first(obj, "sector_code", "index_code") or "").strip()
        sector_index = obj.get("sector_index")
        if isinstance(sector_index, dict):
            sector_name = sector_name or str(first(sector_index, "name", "index_name") or "").strip()
            sector_code = sector_code or str(first(sector_index, "code", "index_code") or "").strip()
        index_caliber = " ".join(x for x in (sector_name, sector_code) if x)
        set_if_missing(meta, "index_caliber", index_caliber, changes, "meta")
    stocks = meta.get("selected_stocks")
    if not isinstance(stocks, list) or not stock_names(stocks):
        names = stock_names(first(obj, "top_10_stocks", "selected_stocks", "representative_stocks", "stocks"))
        if names:
            meta["selected_stocks"] = names
            changes.append("meta: 顶层股票名单 -> selected_stocks")
    date = str(first(obj, "data_date", "today", "as_of", "date") or "").strip()
    set_if_missing(meta, "today", date, changes, "meta")
    if date and not meta.get("timestamp"):
        meta["timestamp"] = f"数据截至 {date} 收盘"
        changes.append("meta: data_date -> timestamp")
    set_if_missing(meta, "data_mode", "full", changes, "meta")


def normalize_stock_checks(obj: dict[str, Any], changes: list[str]) -> None:
    checks = obj.get("stock_checks")
    if not isinstance(checks, list):
        raw = first(obj, "top_10_stocks", "stocks", "representative_stocks")
        checks = raw if isinstance(raw, list) else []
        obj["stock_checks"] = checks
        changes.append("top: 顶层股票列表 -> stock_checks")
    for i, s in enumerate(checks):
        if not isinstance(s, dict):
            continue
        label = f"stock_checks[{i}]"
        move_alias(s, "name", ("stock_name", "股票名称", "证券简称"), changes, label)
        move_alias(s, "change", ("change_pct", "daily_change", "pct_change", "涨跌幅"), changes, label)
        move_alias(s, "turnover", ("turnover_amount", "amount", "成交额"), changes, label)
        move_alias(s, "pe_ttm", ("pe", "peTTM", "pe_ttm_value", "市盈率TTM", "PE_TTM"), changes, label)
        move_alias(s, "change_7d", ("near_7d_change_pct", "change7d", "change_7days", "7d_change"), changes, label)
        move_alias(s, "turnover_7d", ("near_7d_avg_turnover", "avg_turnover_7d", "turnover7d", "7d_avg_turnover"), changes, label)
        move_alias(s, "d7_close_base", ("close_base", "base_close", "d7_base_close"), changes, label)
        move_alias(s, "d7_close_t", ("close", "latest_close", "last_close"), changes, label)
        move_alias(s, "d7_turnovers", ("turnover_series", "turnovers_7d", "last_7_turnovers"), changes, label)
        move_alias(s, "role", ("type", "tag", "label"), changes, label)
        move_alias(s, "select_reason", ("reason", "note", "why_selected", "selection_reason"), changes, label)
        src = s.get("source")
        if isinstance(src, dict):
            set_if_missing(s, "source_name", first(src, "source_name", "name", "provider"), changes, label)
            set_if_missing(s, "as_of", first(src, "as_of", "date"), changes, label)
        set_if_missing(s, "source_name", "同花顺数据库", changes, label)
        meta_today = str((obj.get("meta") or {}).get("today") or "").strip()
        set_if_missing(s, "as_of", meta_today, changes, label)


def normalize_groups(obj: dict[str, Any], changes: list[str]) -> None:
    groups = obj.get("divergence_groups")
    if not isinstance(groups, dict):
        groups = {}
        obj["divergence_groups"] = groups
        changes.append("top: 新建 divergence_groups")
    for g in GROUPS:
        raw = groups.get(g)
        if isinstance(raw, dict):
            raw = raw.get("stocks")
        if not isinstance(raw, list):
            groups[g] = []
            changes.append(f"divergence_groups: 补空组 {g}")
        else:
            groups[g] = [str(x).strip() for x in raw if str(x).strip() and str(x).strip() != "无"]


def normalize_fact(f: dict[str, Any], i: int, changes: list[str]) -> None:
    label = f"facts[{i}]"
    move_alias(f, "metric", ("title", "name", "indicator", "event", "事件名"), changes, label)
    move_alias(f, "value", ("summary", "fact", "content", "description", "evidence_text"), changes, label)
    move_alias(f, "period", ("date", "event_date", "time", "发生日"), changes, label)
    move_alias(f, "as_of", ("event_date", "date", "data_date"), changes, label)
    move_alias(f, "url", ("link", "original_url", "source_url"), changes, label)
    move_alias(f, "source_name", ("sourceName", "provider", "来源"), changes, label)
    move_alias(f, "kind", ("type", "fact_type", "usage_kind"), changes, label)
    src = f.get("source")
    if isinstance(src, dict):
        set_if_missing(f, "lane", first(src, "lane"), changes, label)
        set_if_missing(f, "source_name", first(src, "source_name", "name", "provider"), changes, label)
        set_if_missing(f, "tier", tier_from_level(first(src, "tier", "level")), changes, label)
        set_if_missing(f, "level", first(src, "level"), changes, label)
        set_if_missing(f, "url", first(src, "url", "link"), changes, label)
        set_if_missing(f, "as_of", first(src, "as_of", "date"), changes, label)
        set_if_missing(f, "source_type", first(src, "type", "source_type"), changes, label)
    elif isinstance(src, str) and f.get("source_name") == src:
        # Keep source_name and leave the original source string untouched for audit.
        pass
    elif isinstance(src, str):
        set_if_missing(f, "source_name", src, changes, label)
    level = first(f, "source_level", "level")
    set_if_missing(f, "tier", tier_from_level(level), changes, label)
    kind = str(f.get("kind") or "").strip().lower()
    if not kind:
        if f.get("url") or f.get("event_date") or f.get("source_level"):
            kind = "catalyst"
        else:
            kind = "market"
        f["kind"] = kind
        changes.append(f"{label}: 补 kind={kind}")
    if not f.get("id"):
        prefix = "cat" if kind == "catalyst" else "fact"
        f["id"] = f"{prefix}_{i + 1}"
        changes.append(f"{label}: 自动补 id")
    if kind == "catalyst":
        set_if_missing(f, "lane", GENERAL_LANE, changes, label)
        set_if_missing(f, "tier", 2, changes, label)
        set_if_missing(f, "level", "二级" if int(f.get("tier") or 2) == 2 else "一手", changes, label)
        set_if_missing(f, "source_type", "mainstream_media" if int(f.get("tier") or 2) == 2 else "official_release", changes, label)
        set_if_missing(f, "usage_type", "media_view" if int(f.get("tier") or 2) == 2 else "hard_fact", changes, label)
        source_name = str(f.get("source_name") or "").strip()
        if int(f.get("tier") or 2) == 2 and not (f.get("allowed_wording") or f.get("suggested_wording")):
            f["allowed_wording"] = [f"据{source_name}报道" if source_name else "据该来源报道"]
            changes.append(f"{label}: 二级催化补 allowed_wording")
    else:
        set_if_missing(f, "lane", FINANCE_LANE, changes, label)
        if kind in MARKET_KINDS:
            set_if_missing(f, "tier", 1, changes, label)
            set_if_missing(f, "source_type", "finance_database", changes, label)
            set_if_missing(f, "usage_type", "hard_fact", changes, label)


def normalize_facts(obj: dict[str, Any], changes: list[str]) -> None:
    facts = obj.get("facts")
    if not isinstance(facts, list):
        facts = []
        for key in ("catalysts", "events"):
            raw = obj.get(key)
            if isinstance(raw, list):
                facts.extend(raw)
        sector_index = obj.get("sector_index")
        if isinstance(sector_index, dict):
            for metric, key, unit in (
                ("板块收盘点位", "close", "点"),
                ("板块当日涨跌幅", "change_pct", "%"),
                ("板块当日成交额", "turnover", "亿"),
                ("板块近7日涨跌幅", "near_7d_change_pct", "%"),
                ("板块近7个交易日日均成交额", "near_7d_avg_turnover", "亿"),
            ):
                val = first(sector_index, key)
                if val not in (None, ""):
                    facts.append({"metric": metric, "value": val, "unit": unit, "kind": "market"})
        obj["facts"] = facts
        changes.append("top: 顶层 catalysts/sector_index -> facts")
    for i, f in enumerate(facts):
        if isinstance(f, dict):
            normalize_fact(f, i, changes)


def repair(obj: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    changes: list[str] = []
    normalize_meta(obj, changes)
    normalize_stock_checks(obj, changes)
    normalize_groups(obj, changes)
    normalize_facts(obj, changes)
    return obj, changes


def main() -> int:
    ap = argparse.ArgumentParser(description="批量修复 facts.json 的机械字段问题（lane / 字段别名 / 摘要结构）")
    ap.add_argument("facts", help="待修复 facts.json")
    ap.add_argument("-o", "--output", help="输出路径；缺省为原地修复并创建 .bak")
    ap.add_argument("--no-backup", action="store_true", help="原地修复时不创建 .bak")
    args = ap.parse_args()

    path = Path(args.facts)
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("[错误] facts.json 顶层必须是对象。")
    repaired, changes = repair(obj)

    out = Path(args.output) if args.output else path
    if out == path and not args.no_backup:
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        print(f"已备份原文件：{backup}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(repaired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入修复后 facts.json：{out}")
    if changes:
        print("批量修复项：")
        for item in changes:
            print(f"- {item}")
    else:
        print("未发现可自动修复的机械字段问题。")
    print("下一步：运行 derive_facts.py 生成派生项，再运行 lint_analysis.py --strict；若仍报错，只处理剩余真实取数 / 来源问题。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
