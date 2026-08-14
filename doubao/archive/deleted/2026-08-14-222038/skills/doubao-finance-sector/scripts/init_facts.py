#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a first-stage facts.json scaffold.

This script prevents the common failure mode where an agent invents a summary
JSON shape such as sector_name/top_10_stocks/catalysts instead of the lintable
facts schema required by this skill.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


GROUPS = ["放量上攻", "缩量上行", "缩量回调", "放量杀跌"]


def _split_stocks(raw: str) -> list[str]:
    return [s.strip() for s in raw.replace("，", ",").split(",") if s.strip()]


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_summary(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("summary JSON 顶层必须是对象")
    return obj


def _from_summary(obj: dict) -> dict:
    stocks = obj.get("top_10_stocks") or []
    names = [str(s.get("name") or "").strip() for s in stocks if isinstance(s, dict) and str(s.get("name") or "").strip()]
    data_date = str(obj.get("data_date") or "").strip()
    sector_name = str(obj.get("sector_name") or "").strip()
    sector_code = str(obj.get("sector_code") or "").strip()
    data_source = str(obj.get("data_source") or "seed_finance_search").strip()
    index_caliber = f"{sector_name} {sector_code}".strip()

    checks = []
    groups = {g: [] for g in GROUPS}
    for s in stocks:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or "").strip()
        if not name:
            continue
        group = str(s.get("group") or "").strip()
        if group in groups:
            groups[group].append(name)
        checks.append(
            {
                "name": name,
                "change": _num(s.get("change_pct")),
                "turnover": _num(s.get("turnover")),
                "pe_ttm": _num(s.get("pe_ttm")),
                "change_7d": _num(s.get("near_7d_change_pct")),
                "turnover_7d": _num(s.get("near_7d_avg_turnover")),
                "d7_close_base": None,
                "d7_close_t": _num(s.get("close")),
                "d7_turnovers": [],
                "role": str(s.get("role") or "").strip(),
                "select_reason": str(s.get("select_reason") or s.get("note") or "").strip(),
                "as_of": data_date,
                "source_name": data_source,
                "evidence": str(s.get("evidence") or "").strip(),
            }
        )

    facts = []
    sector_index = obj.get("sector_index") or {}
    sector_checks = {
        "close_point": None,
        "prev_close": None,
        "daily_change": None,
        "turnover_amount": None,
        "change_7d": None,
        "turnover_7d": None,
        "d7_close_base": None,
        "d7_close_t": None,
        "d7_turnovers": [],
        "as_of": data_date,
        "source_name": data_source,
        "evidence": str(sector_index.get("evidence") or "").strip() if isinstance(sector_index, dict) else "",
    }
    if isinstance(sector_index, dict):
        sector_checks.update(
            {
                "close_point": _num(sector_index.get("close")),
                "prev_close": _num(sector_index.get("prev_close")),
                "daily_change": _num(sector_index.get("change_pct")),
                "turnover_amount": _num(sector_index.get("turnover")),
                "change_7d": _num(sector_index.get("near_7d_change_pct")),
                "turnover_7d": _num(sector_index.get("near_7d_avg_turnover")),
                "d7_close_base": _num(sector_index.get("d7_close_base")),
                "d7_close_t": _num(sector_index.get("d7_close_t") or sector_index.get("close")),
                "d7_turnovers": sector_index.get("d7_turnovers") if isinstance(sector_index.get("d7_turnovers"), list) else [],
            }
        )
        metric_map = [
            ("close_point", "板块收盘点位", "close", "点"),
            ("daily_change", "板块当日涨跌幅", "change_pct", "%"),
            ("turnover_amount", "板块当日成交额", "turnover", "亿"),
            ("change_7d", "板块近7日涨跌幅", "near_7d_change_pct", "%"),
            ("turnover_7d", "板块近7个交易日日均成交额", "near_7d_avg_turnover", "亿"),
        ]
        for fid, metric, key, unit in metric_map:
            val = _num(sector_index.get(key))
            if val is None:
                continue
            facts.append(
                {
                    "id": fid,
                    "metric": metric,
                    "value": val,
                    "unit": unit,
                    "period": data_date,
                    "as_of": data_date,
                    "kind": "market",
                    "tier": 1,
                    "source_type": "finance_database",
                    "source_name": data_source,
                    "usage_type": "hard_fact",
                    "evidence": "由摘要型 facts 转换；请核对口径并补齐复算分量。",
                }
            )

    for i, c in enumerate(obj.get("catalysts") or [], start=1):
        if not isinstance(c, dict):
            continue
        facts.append(
            {
                "id": f"cat_{i}",
                "metric": str(c.get("title") or f"催化{i}").strip(),
                "value": str(c.get("summary") or "").strip(),
                "period": str(c.get("date") or "").strip(),
                "as_of": str(c.get("date") or "").strip(),
                "kind": "catalyst",
                "tier": 1 if str(c.get("source_level") or c.get("level") or "").strip() in {"一级", "一手"} else 2,
                "level": str(c.get("source_level") or c.get("level") or "").strip() or "二级",
                "source_type": "official_release" if str(c.get("source_level") or "").strip() in {"一级", "一手"} else "mainstream_media",
                "source_name": str(c.get("source") or c.get("source_name") or "").strip(),
                "url": str(c.get("url") or "").strip(),
                "usage_type": "hard_fact" if str(c.get("source_level") or "").strip() in {"一级", "一手"} else "media_view",
                "evidence": str(c.get("summary") or "").strip(),
            }
        )

    return {
        "meta": {
            "sector": sector_name,
            "index_caliber": index_caliber,
            "selected_stocks": names,
            "timestamp": f"数据截至 {data_date} 收盘" if data_date else "",
            "today": data_date,
            "data_mode": "full",
        },
        "sector_checks": sector_checks,
        "stock_checks": checks,
        "divergence_groups": groups,
        "facts": facts,
    }


def _blank(args) -> dict:
    names = _split_stocks(args.stocks or "")
    return {
        "meta": {
            "sector": args.sector or "",
            "index_caliber": args.index_caliber or "",
            "selected_stocks": names,
            "timestamp": args.timestamp or "",
            "today": args.today or "",
            "data_mode": args.data_mode,
        },
        "sector_checks": {
            "close_point": None,
            "prev_close": None,
            "daily_change": None,
            "turnover_amount": None,
            "change_7d": None,
            "turnover_7d": None,
            "d7_close_base": None,
            "d7_close_t": None,
            "d7_turnovers": [],
            "as_of": args.today or "",
            "source_name": "同花顺数据库",
            "evidence": "",
        },
        "stock_checks": [
            {
                "name": name,
                "change": None,
                "turnover": None,
                "pe_ttm": None,
                "change_7d": None,
                "turnover_7d": None,
                "d7_close_base": None,
                "d7_close_t": None,
                "d7_turnovers": [],
                "role": "",
                "select_reason": "",
                "as_of": args.today or "",
                "source_name": "同花顺数据库",
                "evidence": "",
            }
            for name in names
        ],
        "divergence_groups": {g: [] for g in GROUPS},
        "facts": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="生成本 skill 可校验的 facts.json 骨架")
    ap.add_argument("--from-summary", help="把摘要型 facts JSON 转成标准骨架")
    ap.add_argument("--sector", help="板块名")
    ap.add_argument("--index-caliber", help="目标概念板块名称 + 代码")
    ap.add_argument("--stocks", help="10 只代表股，用逗号分隔")
    ap.add_argument("--timestamp", help="数据截止说明，如：数据截至 2026-06-18 收盘")
    ap.add_argument("--today", help="分析日期 YYYY-MM-DD")
    ap.add_argument("--data-mode", default="full", choices=["full"])
    ap.add_argument("-o", "--output", required=True, help="输出 facts.json 路径")
    args = ap.parse_args()

    if args.from_summary:
        obj = _from_summary(_load_summary(Path(args.from_summary)))
    else:
        obj = _blank(args)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 facts.json 骨架：{out}")
    print("下一步：先回填 sector_checks、stock_checks 与 facts[] 原始字段；再运行 `python3 scripts/derive_facts.py <facts.json>`，写正文前运行 `python3 scripts/lint_analysis.py --strict <facts.json>`。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
