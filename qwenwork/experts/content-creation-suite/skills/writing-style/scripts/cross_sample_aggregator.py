#!/usr/bin/env python3
"""Aggregate style features across multiple samples.

Takes per-sample style cards (JSON) and produces a cross-sample summary:
  - Stable features (appear in ≥60% of samples)
  - Occasional features (appear only once)
  - Contradictory features (conflicting signals)
  - Quantitative summary (mean + std across samples)

Usage:
  python cross_sample_aggregator.py --input cards.json
  cat cards.json | python cross_sample_aggregator.py --stdin

Input format (JSON array of style cards):
[
  {
    "source": "《玻尿酸选购指南》",
    "quantitative": {
      "avg_sentence_length": 18.2,
      "sentence_length_std": 8.1,
      "type_token_ratio": 0.72,
      "avg_paragraph_length": 3.2,
      "paragraph_count": 6
    },
    "tone": "口语化、直接",
    "perspective": "第二人称'你'为主",
    "rhetoric": ["类比", "反问"],
    "signature_expressions": ["说白了就是…", "选错了等于白…"],
    "opening_pattern": "直接抛结论",
    "closing_pattern": "行动建议收尾"
  },
  ...
]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _classify_features(
    feature_counter: Counter, total_samples: int
) -> dict:
    """Classify features into stable / occasional / mid-frequency."""
    threshold = max(1, total_samples * 0.6)
    stable = []
    occasional = []
    mid = []
    for feature, count in feature_counter.most_common():
        ratio = count / total_samples
        entry = {"feature": feature, "count": count, "ratio": round(ratio, 2)}
        if count >= threshold:
            stable.append(entry)
        elif count == 1:
            occasional.append(entry)
        else:
            mid.append(entry)
    return {"stable": stable, "occasional": occasional, "mid_frequency": mid}


def _merge_similar_expressions(counter: Counter) -> Counter:
    """Merge expressions that share a common prefix.

    When a shorter expression is a prefix of a longer one and the shorter
    accounts for ≥50% of the longer's length, they are treated as the same
    feature.  Counts are summed under the shorter (canonical) form.

    Example:
        "说白了" (3) + "说白了就是…" (2) → "说白了" (5)
        "选错了等于…" (2) + "选错了等于白…" (2) → "选错了等于…" (4)
    """
    keys = sorted(counter.keys(), key=len)  # shortest first
    merged = Counter()
    absorbed: set[str] = set()

    for i, short in enumerate(keys):
        if short in absorbed:
            continue
        total = counter[short]
        for longer in keys[i + 1:]:
            if longer in absorbed:
                continue
            # Strip trailing ellipsis for prefix comparison
            short_core = short.rstrip("…").rstrip(".")
            longer_core = longer.rstrip("…").rstrip(".")
            if longer_core.startswith(short_core) and len(short_core) / len(longer_core) >= 0.5:
                total += counter[longer]
                absorbed.add(longer)
        merged[short] = total

    return merged


def _detect_contradictions(cards: list[dict], field: str) -> list[dict]:
    """Detect contradictory values for a given field across cards."""
    values = Counter()
    for card in cards:
        val = card.get(field, "")
        if val:
            values[val] += 1
    if len(values) <= 1:
        return []
    # Multiple distinct values → potential contradiction
    total = sum(values.values())
    return [
        {
            "field": field,
            "value": val,
            "count": cnt,
            "ratio": round(cnt / total, 2),
        }
        for val, cnt in values.most_common()
    ]


def aggregate(cards: list[dict]) -> dict:
    """Main aggregation logic."""
    n = len(cards)
    if n == 0:
        return {"error": "No style cards provided", "total_samples": 0}

    # --- Quantitative aggregation ---
    quant_keys = [
        "avg_sentence_length", "sentence_length_std",
        "type_token_ratio", "avg_paragraph_length", "paragraph_count",
    ]
    quant_summary = {}
    for key in quant_keys:
        values = [
            c["quantitative"][key]
            for c in cards
            if "quantitative" in c and key in c.get("quantitative", {})
        ]
        if values:
            quant_summary[key] = {
                "mean": round(_mean(values), 2),
                "std": round(_std(values), 2),
                "min": round(min(values), 2),
                "max": round(max(values), 2),
            }

    # --- Qualitative feature aggregation ---
    # Collect list-type features
    rhetoric_counter = Counter()
    signature_counter = Counter()
    for card in cards:
        for r in card.get("rhetoric", []):
            rhetoric_counter[r] += 1
        for s in card.get("signature_expressions", []):
            signature_counter[s] += 1

    # Merge similar expressions before classification (DEF-02 fix)
    signature_counter = _merge_similar_expressions(signature_counter)

    rhetoric_classified = _classify_features(rhetoric_counter, n)
    signature_classified = _classify_features(signature_counter, n)

    # Collect scalar features
    tone_counter = Counter(c.get("tone", "") for c in cards if c.get("tone"))
    opening_counter = Counter(c.get("opening_pattern", "") for c in cards if c.get("opening_pattern"))
    closing_counter = Counter(c.get("closing_pattern", "") for c in cards if c.get("closing_pattern"))

    # --- Contradiction detection ---
    contradictions = []
    for field in ["tone", "perspective", "opening_pattern", "closing_pattern"]:
        contras = _detect_contradictions(cards, field)
        if contras:
            contradictions.append({"field": field, "values": contras})

    # --- Build result ---
    return {
        "total_samples": n,
        "quantitative_summary": quant_summary,
        "rhetoric": rhetoric_classified,
        "signature_expressions": signature_classified,
        "tone_distribution": [
            {"value": v, "count": c, "ratio": round(c / n, 2)}
            for v, c in tone_counter.most_common()
        ],
        "opening_pattern_distribution": [
            {"value": v, "count": c, "ratio": round(c / n, 2)}
            for v, c in opening_counter.most_common()
        ],
        "closing_pattern_distribution": [
            {"value": v, "count": c, "ratio": round(c / n, 2)}
            for v, c in closing_counter.most_common()
        ],
        "contradictions": contradictions,
        "confidence": (
            "high" if n >= 5
            else "medium" if n >= 3
            else "low"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate style features across samples")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Path to JSON file with style cards array")
    group.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    args = parser.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    else:
        # Resolve input path to absolute for robustness
        input_path = os.path.abspath(args.input)
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()

    cards = json.loads(raw)
    
    # 兼容模式：支持上游直接输出的 { "files": [...] } 格式，或单个对象
    if isinstance(cards, dict):
        if "files" in cards:
            cards = cards["files"]
        else:
            # 如果是一个单独的分析结果对象，将其包装成列表
            cards = [cards]
    
    if not isinstance(cards, list):
        print(json.dumps({"error": "Input must be a JSON array of style cards or an object with a 'files' key"}, ensure_ascii=False))
        sys.exit(2)

    # 数据标准化：将新版深度分析结构转换为聚合脚本兼容的旧版格式
    normalized_cards = []
    for idx, item in enumerate(cards):
        try:
            card = {}
            q_data = item.get("quantitative", {}) if isinstance(item.get("quantitative"), dict) else {}
            
            # 1. 映射基础统计 (basic_stats -> quantitative)
            if "basic_stats" in q_data and isinstance(q_data["basic_stats"], dict):
                card["quantitative"] = q_data["basic_stats"]
            elif q_data:
                card["quantitative"] = q_data # 兼容旧版直接输出
            else:
                card["quantitative"] = {"avg_sentence_length": 0, "sentence_length_std": 0, "type_token_ratio": 0}

            # 2. 映射修辞锚点 (rhetoric_anchors -> rhetoric list)
            anchors = q_data.get("rhetoric_anchors", {}) if isinstance(q_data.get("rhetoric_anchors"), dict) else {}
            card["rhetoric"] = anchors.get("potential_golden_quotes", []) if isinstance(anchors.get("potential_golden_quotes"), list) else []
            
            # 3. 映射情感极性 (emotional_arc -> tone)
            arc = q_data.get("emotional_arc", {}) if isinstance(q_data.get("emotional_arc"), dict) else {}
            card["tone"] = arc.get("emotional_polarity", "")
            
            # 4. 映射其他定性字段（如果存在）
            card["perspective"] = item.get("perspective", "")
            card["opening_pattern"] = item.get("opening_pattern", "")
            card["closing_pattern"] = item.get("closing_pattern", "")
            card["signature_expressions"] = item.get("signature_expressions", []) if isinstance(item.get("signature_expressions"), list) else []
                
            normalized_cards.append(card)
        except Exception as e:
            print(f"⚠️ Warning: Failed to normalize sample {idx}: {e}", file=sys.stderr)

    result = aggregate(normalized_cards)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
