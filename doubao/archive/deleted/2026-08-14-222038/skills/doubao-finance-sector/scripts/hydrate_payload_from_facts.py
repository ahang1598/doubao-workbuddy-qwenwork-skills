#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把第一阶段 facts.json 中已验证的 10 股行情与分组映射进飞书文档 payload。

文档生成阶段不应重新手填 stocks / divergence_groups 的行情字段；这些内容已在
facts.json 通过 lint_analysis.py 校验。本脚本负责从 stock_checks 与
divergence_groups 自动覆盖 payload，避免转写漏填、改值或换名单。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_checks  # noqa: E402


GROUPS = ["放量上攻", "缩量上行", "缩量回调", "放量杀跌"]
__all__ = [
    "GROUPS",
    "infer_chat_path",
    "extract_divergence_features",
    "extract_sources_from_chat",
    "hydrate_sources_from_chat",
    "group_members",
    "stock_group_map",
    "hydrate",
    "stock_transfer_hash",
]


def _read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def infer_chat_path(facts_path: Path, payload_path: Path) -> Path | None:
    candidates: list[Path] = []
    for path in (facts_path, payload_path):
        stem = path.stem
        for suffix in ("_facts", "_payload", "_payload_hydrated"):
            if stem.endswith(suffix):
                candidates.append(path.with_name(stem[: -len(suffix)] + "_分析草稿.md"))
        candidates.append(path.with_name(stem + "_分析草稿.md"))
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def _section(text: str, heading: str, next_heading: str) -> str:
    m = re.search(rf"^##\s*{re.escape(heading)}\s*$", text, re.M)
    if not m:
        return ""
    start = m.end()
    n = re.search(rf"^##\s*{re.escape(next_heading)}\s*$", text[start:], re.M)
    end = start + n.start() if n else len(text)
    return text[start:end]


def _clean_group_feature(raw: str, members: list[str]) -> str:
    text = re.sub(r"\s+", " ", raw).strip()
    if not text or text in {"无", "无。"}:
        return "无。"
    for sep in ("——", "--", "—"):
        if sep in text:
            right = text.split(sep, 1)[1].strip()
            return right or text
    # 兜底：若模型只用了冒号后正文，尽量去掉开头的股票名单。
    for name in members:
        text = re.sub(rf"^\s*{re.escape(name)}\s*[、,，]?\s*", "", text)
    return text.strip(" ：:，,、") or raw.strip()


def extract_divergence_features(chat_text: str, groups: dict) -> tuple[dict[str, str], str]:
    mod = _section(chat_text, "谁在动、谁没动", "接下来盯什么")
    if not mod:
        return {}, ""

    meaning = ""
    m = re.search(r"\*\*本段结论：\*\*\s*(.+?)(?=\n\s*[-*]\s*\*\*|$)", mod, re.S)
    if m:
        meaning = re.sub(r"\s+", " ", m.group(1)).strip()

    features: dict[str, str] = {}
    for i, g in enumerate(GROUPS):
        nxt = GROUPS[i + 1] if i + 1 < len(GROUPS) else None
        if nxt:
            pat = rf"^\s*[-*]\s*\*\*{re.escape(g)}\*\*[：:]\s*(.+?)(?=^\s*[-*]\s*\*\*{re.escape(nxt)}\*\*[：:]|\Z)"
        else:
            pat = rf"^\s*[-*]\s*\*\*{re.escape(g)}\*\*[：:]\s*(.+?)\Z"
        gm = re.search(pat, mod, re.M | re.S)
        if not gm:
            continue
        raw = gm.group(1).strip()
        features[g] = _clean_group_feature(raw, group_members(groups, g))
    return features, meaning


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "").strip()).lower()


def _norm_date(s: str) -> str:
    raw = str(s or "").strip()
    m = re.search(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})", raw)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?", raw)
    if m:
        return f"{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return _norm(raw)


def extract_sources_from_chat(chat_text: str) -> list[dict[str, str]]:
    mod = _section(chat_text, "信息来源", "")
    if not mod:
        m = re.search(r"^##\s*信息来源\s*$", chat_text, re.M)
        if m:
            mod = chat_text[m.end():]
    if not mod:
        return []
    out: list[dict[str, str]] = []
    for line in mod.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        if not line or line.startswith("下一步"):
            continue
        if "：" not in line and ":" not in line:
            continue
        name, rest = re.split(r"[：:]", line, maxsplit=1)
        name = name.strip()
        rest = rest.strip().rstrip("。")
        if not name or not rest:
            continue
        date = ""
        dm = re.search(r"(20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}\s*[日号]?)", rest)
        if dm:
            date = dm.group(1).replace("年", "-").replace("月", "-").replace("日", "").replace("号", "")
            title = rest[: dm.start()].rstrip(" ，,、")
        else:
            title = rest.rstrip(" ，,、")
        out.append({"name": name, "title": title, "date": date})
    return out


def hydrate_sources_from_chat(payload: dict, chat_text: str) -> None:
    chat_sources = extract_sources_from_chat(chat_text)
    if not chat_sources or not isinstance(payload.get("sources"), list):
        return
    by_name_date = {
        (_norm(s.get("name", "")), _norm_date(s.get("date", ""))): s
        for s in chat_sources
    }
    by_name: dict[str, dict[str, str]] = {}
    for s in chat_sources:
        by_name.setdefault(_norm(s.get("name", "")), s)

    for src in payload.get("sources") or []:
        if not isinstance(src, dict):
            continue
        if str(src.get("title") or "").strip():
            continue
        key = (_norm(src.get("name", "")), _norm_date(src.get("date", "")))
        found = by_name_date.get(key) or by_name.get(_norm(src.get("name", "")))
        if not found and not str(src.get("url") or "").strip():
            found = by_name.get("seed_finance_search")
        if not found:
            continue
        if found.get("title"):
            src["title"] = found["title"]
        if not str(src.get("date") or "").strip() and found.get("date"):
            src["date"] = found["date"]


def load_json(path: Path):
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"{path} 不含 JSON 对象")


def dump_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def group_members(groups: dict, group: str) -> list[str]:
    raw = (groups or {}).get(group)
    if isinstance(raw, dict):
        raw = raw.get("stocks")
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip() and str(x).strip() != "无"]


def stock_group_map(groups: dict) -> dict[str, str]:
    out = {}
    for g in GROUPS:
        for name in group_members(groups, g):
            out[name] = g
    return out


def _stock_transfer_snapshot(payload: dict) -> dict:
    stocks = []
    for s in payload.get("stocks") or []:
        if not isinstance(s, dict):
            continue
        stocks.append(
            {
                "name": s.get("name"),
                "group": s.get("group"),
                "role": s.get("role"),
                "select_reason": s.get("select_reason"),
                "change": s.get("change"),
                "turnover": s.get("turnover"),
                "change_7d": s.get("change_7d"),
                "turnover_7d": s.get("turnover_7d"),
                "d7_close_base": s.get("d7_close_base"),
                "d7_close_t": s.get("d7_close_t"),
                "d7_turnovers": s.get("d7_turnovers"),
                "source": s.get("source"),
            }
        )
    groups = {}
    raw_groups = payload.get("divergence_groups") or {}
    for g in GROUPS:
        raw = raw_groups.get(g)
        groups[g] = list((raw or {}).get("stocks") or []) if isinstance(raw, dict) else []
    return {
        "selected_stocks": payload.get("selected_stocks") or [],
        "stocks": stocks,
        "divergence_groups": groups,
    }


def _stock_transfer_hash(payload: dict) -> str:
    raw = json.dumps(_stock_transfer_snapshot(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# 供 doc.md 新链路复用，避免第二套实现造成映射行为偏差。
stock_transfer_hash = _stock_transfer_hash


def hydrate(facts: dict, payload: dict, chat_text: str = "") -> tuple[dict, list[str]]:
    meta = facts.get("meta") or {}
    checks = facts.get("stock_checks") or []
    groups = facts.get("divergence_groups") or {}
    warnings: list[str] = []

    selected = [str(x).strip() for x in (meta.get("selected_stocks") or []) if str(x).strip()]
    by_name = {str(s.get("name") or "").strip(): s for s in checks if isinstance(s, dict)}
    existing = {
        str(s.get("name") or "").strip(): s
        for s in (payload.get("stocks") or [])
        if isinstance(s, dict) and str(s.get("name") or "").strip()
    }
    gmap = stock_group_map(groups)

    for dst, src_key in (
        ("sector", "sector"),
        ("index_caliber", "index_caliber"),
        ("timestamp", "timestamp"),
        ("data_mode", "data_mode"),
    ):
        val = meta.get(src_key)
        if val not in (None, ""):
            payload[dst] = val
    payload["selected_stocks"] = selected
    payload.setdefault("quote_source", "同花顺数据库")

    hydrated_stocks = []
    for name in selected:
        fact_stock = by_name.get(name) or {}
        old = existing.get(name) or {}
        role = str(fact_stock.get("role") or "").strip()
        reason = str(fact_stock.get("select_reason") or fact_stock.get("note") or "").strip()
        if not role or not reason:
            warnings.append(f"个股“{name}”缺少 role/select_reason；facts_json_checks 应已拦截，请回到第一阶段 facts.json 修正。")
        as_of = fact_stock.get("as_of") or meta.get("today") or ""
        source_name = fact_stock.get("source_name") or "同花顺数据库"
        item = dict(old)
        item.update(
            {
                "name": name,
                "group": gmap.get(name, old.get("group") or ""),
                "role": role,
                "select_reason": reason,
                "change": fact_stock.get("change"),
                "turnover": fact_stock.get("turnover"),
                "change_7d": fact_stock.get("change_7d"),
                "turnover_7d": fact_stock.get("turnover_7d"),
                "d7_close_base": fact_stock.get("d7_close_base"),
                "d7_close_t": fact_stock.get("d7_close_t"),
                "d7_turnovers": fact_stock.get("d7_turnovers") or [],
                "source": {
                    "lane": "seed_finance_search",
                    "as_of": as_of,
                    "name": source_name,
                },
            }
        )
        hydrated_stocks.append(item)
    payload["stocks"] = hydrated_stocks

    old_groups = payload.get("divergence_groups") if isinstance(payload.get("divergence_groups"), dict) else {}
    chat_features, chat_meaning = extract_divergence_features(chat_text, groups)
    hydrated_groups = {}
    for g in GROUPS:
        old_g = old_groups.get(g) if isinstance(old_groups.get(g), dict) else {}
        members = group_members(groups, g)
        feature = str((old_g or {}).get("feature") or chat_features.get(g) or "").strip()
        if not feature:
            feature = "无。" if not members else "组内个股名单来自第一阶段已验证的量价分组。"
        hydrated_groups[g] = {"stocks": members, "feature": feature}
    meaning = str(old_groups.get("meaning") or "").strip()
    if not meaning:
        meaning = chat_meaning
    if not meaning:
        meaning = str((payload.get("section_summaries") or {}).get("divergence") or "").strip()
    if not meaning:
        meaning = "10 只代表股的量价分组已由第一阶段 facts.json 校验，模块3仅复用该分组解释内部结构。"
    hydrated_groups["meaning"] = meaning
    payload["divergence_groups"] = hydrated_groups
    hydrate_sources_from_chat(payload, chat_text)
    payload["_facts_hydration"] = {
        "script": "hydrate_payload_from_facts.py",
        "version": 1,
        "stocks_sha256": _stock_transfer_hash(payload),
    }

    return payload, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="从 facts.json 自动映射 10 股行情与量价分组到 payload.json")
    ap.add_argument("facts", help="第一阶段已通过 lint 的 facts.json")
    ap.add_argument("payload", help="飞书文档 payload 草稿 JSON")
    ap.add_argument("-o", "--output", help="输出 payload 路径；缺省覆盖 payload")
    ap.add_argument("--chat", help="第一阶段分析草稿 markdown；缺省自动查找同目录 <板块>_分析草稿.md")
    args = ap.parse_args(argv)

    facts_path = Path(args.facts)
    payload_path = Path(args.payload)
    out_path = Path(args.output) if args.output else payload_path

    try:
        facts = load_json(facts_path)
        payload = load_json(payload_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 JSON: {exc}")
        return 2

    infos, warnings, errors = market_checks.facts_json_checks(facts)
    for msg in infos:
        print(f"[复算/信息] {msg}")
    for msg in warnings:
        print(f"[警告] facts.json: {msg}")
    if errors:
        for msg in errors:
            print(f"[错误] facts.json: {msg}")
        print("facts.json 未通过第一阶段数据校验，拒绝映射到 payload。")
        return 1

    chat_path = Path(args.chat) if args.chat else infer_chat_path(facts_path, payload_path)
    chat_text = _read_text(chat_path)
    out, hydrate_warnings = hydrate(facts, payload, chat_text)
    dump_json(out_path, out)
    for msg in hydrate_warnings:
        print(f"[警告] {msg}")
    if chat_path and chat_text:
        print(f"[信息] 已从分析草稿抽取模块3四组解释：{chat_path}")
    else:
        print("[警告] 未找到分析草稿，divergence_groups[].feature 将仅使用 payload 已有值或默认句。")
    print(f"已从 facts.json 自动映射 stocks / divergence_groups 到：{out_path}")
    print("下一步：先运行 check_payload_against_chat.py 确认 payload 文本从 chat 原句搬运，再运行 check_market_facts.py 与 validate_doc_payload.py。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
