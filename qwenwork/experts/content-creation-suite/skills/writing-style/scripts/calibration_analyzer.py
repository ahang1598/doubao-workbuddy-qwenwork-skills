#!/usr/bin/env python3
"""Analyze calibration diff records and match patterns to spec update rules.

Takes an array of diff records (from calibration-protocol.md format),
counts category frequencies, matches against the mapping table,
and outputs which style spec fields should be updated.

Usage:
  python calibration_analyzer.py --input diffs.json
  cat diffs.json | python calibration_analyzer.py --stdin

Input format (JSON array of diff records):
[
  {
    "type": "style_calibration",
    "timestamp": "2026-04-14T17:00:00+08:00",
    "source_doc": "关于玻尿酸的科普文",
    "diffs": [
      {"category": "word_replace", "original": "因此", "revised": "所以", "context": "..."},
      {"category": "sentence_split", "original": "...", "revised": "...", "context": "..."}
    ]
  },
  ...
]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict


# Mapping table from calibration-protocol.md §二
PATTERN_RULES = [
    {
        "id": "long_to_short",
        "name": "用户总是把长句拆短",
        "category": "sentence_split",
        "min_count": 3,
        "target_field": "模块三：句式与节奏",
        "action": "降低 avg_sentence_length 目标值，增加'偏好短句'描述",
    },
    {
        "id": "delete_word",
        "name": "用户总是删掉某个词",
        "category": "word_delete",
        "min_count": 2,
        "target_field": "模块五：禁用清单",
        "action": "将高频删除词加入禁用清单，标注来源为'用户校准'",
        "track_specific_words": True,
    },
    {
        "id": "formal_to_casual",
        "name": "用户总是替换某类词（书面→口语）",
        "category": "word_replace",
        "min_count": 3,
        "target_field": "模块二：语气与视角",
        "action": "调整语气描述，如'比之前更口语化'",
    },
    {
        "id": "add_metaphor",
        "name": "用户总是加入口语化比喻",
        "category": "word_add",
        "min_count": 2,
        "target_field": "模块二：语气与视角 + 模块四：标志性表达",
        "action": "更新修辞手法描述，新增标志性表达",
    },
    {
        "id": "rewrite_sentence",
        "name": "用户总是改写整句",
        "category": "sentence_rewrite",
        "min_count": 3,
        "target_field": "模块一：整体调性",
        "action": "重新评估整体调性描述",
    },
    {
        "id": "change_punctuation",
        "name": "用户总是调整标点",
        "category": "punctuation_change",
        "min_count": 3,
        "target_field": "模块三：句式与节奏",
        "action": "更新标点特征描述",
    },
    {
        "id": "change_structure",
        "name": "用户总是调换段落结构",
        "category": "structure_change",
        "min_count": 2,
        "target_field": "模块三：句式与节奏",
        "action": "更新段落习惯描述",
    },
]


def _flatten_diffs(records: list[dict]) -> list[dict]:
    """Flatten nested diff records into a single list of diffs."""
    all_diffs = []
    for record in records:
        for diff in record.get("diffs", []):
            diff_copy = dict(diff)
            diff_copy["source_doc"] = record.get("source_doc", "unknown")
            diff_copy["timestamp"] = record.get("timestamp", "")
            all_diffs.append(diff_copy)
    return all_diffs


def analyze(records: list[dict]) -> dict:
    """Main analysis: count frequencies, match patterns, produce recommendations."""
    all_diffs = _flatten_diffs(records)
    total_diffs = len(all_diffs)

    if total_diffs == 0:
        return {
            "total_records": len(records),
            "total_diffs": 0,
            "should_update": False,
            "reason": "无修改记录",
        }

    # Count by category
    category_counts = Counter(d.get("category", "unknown") for d in all_diffs)

    # Track specific deleted/replaced words
    deleted_words = Counter()
    replaced_pairs = []
    for d in all_diffs:
        cat = d.get("category", "")
        if cat == "word_delete":
            deleted_words[d.get("original", "")] += 1
        elif cat == "word_replace":
            replaced_pairs.append({
                "original": d.get("original", ""),
                "revised": d.get("revised", ""),
            })

    # Match patterns against rules
    triggered_rules = []
    for rule in PATTERN_RULES:
        count = category_counts.get(rule["category"], 0)
        if count >= rule["min_count"]:
            entry = {
                "rule_id": rule["id"],
                "pattern": rule["name"],
                "category": rule["category"],
                "count": count,
                "min_required": rule["min_count"],
                "target_field": rule["target_field"],
                "suggested_action": rule["action"],
            }
            # Add specific word details for word_delete
            if rule.get("track_specific_words") and rule["category"] == "word_delete":
                frequent_words = [
                    {"word": w, "count": c}
                    for w, c in deleted_words.most_common()
                    if c >= 2
                ]
                entry["frequent_words"] = frequent_words
            triggered_rules.append(entry)

    should_update = total_diffs >= 5

    return {
        "total_records": len(records),
        "total_diffs": total_diffs,
        "category_counts": dict(category_counts.most_common()),
        "triggered_rules": triggered_rules,
        "should_update": should_update,
        "update_reason": (
            f"累积 {total_diffs} 次修改，≥5 次阈值，建议更新说明书"
            if should_update
            else f"累积 {total_diffs} 次修改，<5 次阈值，暂不建议更新"
        ),
        "deleted_words_top": [
            {"word": w, "count": c} for w, c in deleted_words.most_common(10)
        ],
        "replaced_pairs_sample": replaced_pairs[:10],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze calibration diff records")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Path to JSON file with diff records")
    group.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    args = parser.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    else:
        # Resolve input path to absolute for robustness
        input_path = os.path.abspath(args.input)
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()

    records = json.loads(raw)
    if not isinstance(records, list):
        print(json.dumps({"error": "Input must be a JSON array of diff records"}, ensure_ascii=False))
        sys.exit(2)

    result = analyze(records)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
