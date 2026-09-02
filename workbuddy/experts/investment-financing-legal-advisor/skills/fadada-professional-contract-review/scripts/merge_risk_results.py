#!/usr/bin/env python3
"""融合本地审查与法大大引擎的风险清单 JSON。

用法:
  python merge_risk_results.py --local <本地风险.json> --engine <引擎风险.json> \
    --output <融合结果.json>

输入为风险 JSON（接受带 {"success":..,"data":{...}} 包裹或裸 {"items":[...]} 两种形态）。
融合规则:
  - 条款匹配: 归一化条款号（「第X.X条/款」数字序列）精确匹配；
    无条款号时对 clause+issue 做相似度匹配（阈值 0.6）。
  - 同项: risk_level 取更高（高>中>低），suggestion 以本地为主、
    引擎不同建议存入 engine_suggestion，source="both"。
  - 独有项: 保留并标 source="local" / "engine"。
输出: 重排 index、重算计数，附 merge_summary{local_only, engine_only, both}。
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

LEVEL_ORDER = {"高": 3, "中": 2, "低": 1}
SIMILARITY_THRESHOLD = 0.6
CLAUSE_NUM_RE = re.compile(r"第\s*([0-9一二三四五六七八九十百]+(?:\s*[.．、]\s*[0-9一二三四五六七八九十]+)*)\s*[条款项]")
CN_DIGITS = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
             "六": "6", "七": "7", "八": "8", "九": "9", "十": "10", "百": "100"}


def load_items(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [dict(item) for item in items if isinstance(item, dict)]


def clause_key(item: dict) -> str | None:
    """提取归一化条款号，如 '第8.2条' -> '8.2'；提取失败返回 None。"""
    match = CLAUSE_NUM_RE.search(str(item.get("clause", "")))
    if not match:
        return None
    raw = match.group(1)
    normalized = "".join(CN_DIGITS.get(ch, ch) for ch in raw)
    normalized = re.sub(r"[．、\s]", ".", normalized)
    return normalized.strip(".")


def similar(a: dict, b: dict) -> bool:
    text_a = f"{a.get('clause', '')} {a.get('issue', '')}"
    text_b = f"{b.get('clause', '')} {b.get('issue', '')}"
    return difflib.SequenceMatcher(None, text_a, text_b).ratio() >= SIMILARITY_THRESHOLD


def higher_level(a: str, b: str) -> str:
    return a if LEVEL_ORDER.get(a, 0) >= LEVEL_ORDER.get(b, 0) else b


def merge(local_items: list[dict], engine_items: list[dict]) -> dict:
    merged: list[dict] = []
    matched_engine: set[int] = set()

    for local in local_items:
        local = dict(local)
        local.setdefault("source", "local")
        l_key = clause_key(local)
        match_idx = None
        for idx, engine in enumerate(engine_items):
            if idx in matched_engine:
                continue
            e_key = clause_key(engine)
            if l_key and e_key:
                if l_key == e_key:
                    match_idx = idx
                    break
            elif similar(local, engine):
                match_idx = idx
                break
        if match_idx is not None:
            engine = engine_items[match_idx]
            matched_engine.add(match_idx)
            local["risk_level"] = higher_level(
                str(local.get("risk_level", "")), str(engine.get("risk_level", "")))
            engine_suggestion = str(engine.get("suggestion", "")).strip()
            if engine_suggestion and engine_suggestion != str(local.get("suggestion", "")).strip():
                local["engine_suggestion"] = engine_suggestion
            local["source"] = "both"
        merged.append(local)

    engine_only = 0
    for idx, engine in enumerate(engine_items):
        if idx in matched_engine:
            continue
        item = dict(engine)
        item["source"] = "engine"
        merged.append(item)
        engine_only += 1

    counts = {"高": 0, "中": 0, "低": 0}
    for i, item in enumerate(merged, start=1):
        item["index"] = i
        level = str(item.get("risk_level", ""))
        if level in counts:
            counts[level] += 1

    both = len(matched_engine)
    return {
        "total": len(merged),
        "high": counts["高"],
        "medium": counts["中"],
        "low": counts["低"],
        "items": merged,
        "merge_summary": {
            "local_only": len(local_items) - both,
            "engine_only": engine_only,
            "both": both,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="融合本地与引擎风险清单")
    parser.add_argument("--local", required=True, type=Path, help="本地风险 JSON")
    parser.add_argument("--engine", required=True, type=Path, help="引擎风险 JSON")
    parser.add_argument("--output", required=True, type=Path, help="融合输出路径")
    args = parser.parse_args()

    try:
        local_items = load_items(args.local)
        engine_items = load_items(args.engine)
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"读取输入失败: {exc}"}, ensure_ascii=False))
        sys.exit(1)

    result = merge(local_items, engine_items)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = dict(result["merge_summary"], total=result["total"],
                   high=result["high"], medium=result["medium"], low=result["low"])
    print(json.dumps({"success": True, "output": str(args.output), **summary},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
