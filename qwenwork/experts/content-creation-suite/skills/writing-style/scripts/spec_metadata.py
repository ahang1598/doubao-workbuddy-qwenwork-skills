#!/usr/bin/env python3
"""Manage style spec metadata (version, confidence, changelog, merge weights).

Handles deterministic metadata operations so the LLM doesn't have to:
  - Increment version
  - Recalculate confidence based on sample count
  - Append changelog entry
  - Compute weighted merge coefficients for incremental updates

Usage:
  # Create initial metadata
  python spec_metadata.py init --sample-count 5 --changelog "基于5篇原创内容首次生成"

  # Update existing metadata (incremental)
  python spec_metadata.py update \
    --current '{"version":1,"sample_count":5,"confidence":"high"}' \
    --new-samples 2 \
    --changelog "新增2篇样本，更新句式节奏描述"

  # Calculate merge weights
  python spec_metadata.py weights --old-samples 5 --new-samples 2
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime


def _confidence(sample_count: int, topic_count: int = 2) -> str:
    """Determine confidence level per style-spec-template.md rules."""
    if sample_count >= 5 and topic_count >= 2:
        return "high"
    if sample_count >= 3:
        return "medium"
    return "low"


def init_metadata(sample_count: int, changelog: str) -> dict:
    """Create initial metadata for a new style spec."""
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "version": 1,
        "sample_count": sample_count,
        "confidence": _confidence(sample_count),
        "created_at": today,
        "updated_at": today,
        "changelog": [f"v1: {changelog}"],
    }


def update_metadata(current: dict, new_samples: int, changelog: str) -> dict:
    """Update metadata for an existing style spec."""
    today = datetime.now().strftime("%Y-%m-%d")
    new_version = current.get("version", 1) + 1
    total_samples = current.get("sample_count", 0) + new_samples

    return {
        "version": new_version,
        "sample_count": total_samples,
        "confidence": _confidence(total_samples),
        "created_at": current.get("created_at", today),
        "updated_at": today,
        "changelog": current.get("changelog", []) + [f"v{new_version}: {changelog}"],
    }


def calc_weights(old_samples: int, new_samples: int) -> dict:
    """Calculate weighted merge coefficients.

    Formula from style-spec-template.md:
      new_weight = new_samples / (total_samples * 1.5)
      old_weight = 1 - new_weight

    Old features have inertia to prevent style drift from a single new sample.
    """
    total = old_samples + new_samples
    if total == 0:
        return {"error": "Total sample count is 0", "old_weight": 0, "new_weight": 0}

    new_weight = new_samples / (total * 1.5)
    old_weight = 1 - new_weight

    return {
        "old_samples": old_samples,
        "new_samples": new_samples,
        "total_samples": total,
        "old_weight": round(old_weight, 4),
        "new_weight": round(new_weight, 4),
        "interpretation": (
            f"老特征权重 {old_weight:.1%}，新特征权重 {new_weight:.1%}。"
            f"{'新特征影响较小，老特征占主导' if new_weight < 0.3 else '新特征有一定影响力'}"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Style spec metadata manager")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Create initial metadata")
    p_init.add_argument("--sample-count", type=int, required=True)
    p_init.add_argument("--changelog", required=True)

    # update
    p_update = sub.add_parser("update", help="Update existing metadata")
    p_update.add_argument("--current", required=True, help="Current metadata as JSON string")
    p_update.add_argument("--new-samples", type=int, required=True)
    p_update.add_argument("--changelog", required=True)

    # weights
    p_weights = sub.add_parser("weights", help="Calculate merge weights")
    p_weights.add_argument("--old-samples", type=int, required=True)
    p_weights.add_argument("--new-samples", type=int, required=True)

    args = parser.parse_args()

    if args.command == "init":
        result = init_metadata(args.sample_count, args.changelog)
    elif args.command == "update":
        current = json.loads(args.current)
        result = update_metadata(current, args.new_samples, args.changelog)
    elif args.command == "weights":
        result = calc_weights(args.old_samples, args.new_samples)
    else:
        print(json.dumps({"error": f"Unknown command: {args.command}"}, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
