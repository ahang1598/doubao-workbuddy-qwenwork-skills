#!/usr/bin/env python3
"""Generate reproducible, hypothesis-led PandaAI blind-mining candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


FAMILIES = {
    "momentum": [
        ("close/ref(close,{fast})-1", 1, "price continuation over the lookback"),
        ("ref(close,{fast})/close-1", 0, "short-horizon reversal"),
    ],
    "range": [
        ("(close-low)/(high-low+0.000001)", 1, "close location inside the daily range"),
        ("(high-low)/(ref(close,1)+0.000001)", 0, "large intraday range as uncertainty"),
    ],
    "liquidity": [
        ("volume/ref(volume,{fast})-1", 1, "abnormal volume expansion"),
        ("amount/(volume+0.000001)", 1, "volume-weighted transaction-price proxy"),
    ],
    "price-volume": [
        ("(close/ref(close,{fast})-1)*(volume/ref(volume,{slow})-1)", 1,
         "price movement confirmed by volume"),
        ("(close-open)/(high-low+0.000001)*(volume/ref(volume,{fast}))", 1,
         "signed intraday pressure weighted by volume"),
    ],
}


def canonical_formula(formula: str) -> str:
    return "".join(formula.lower().split())


def candidate_id(formula: str, direction: int) -> str:
    raw = f"{canonical_formula(formula)}|{direction}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def load_seen(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if "candidate_id" in record:
            seen.add(record["candidate_id"])
    return seen


def generate(count: int, seed: int, seen: set[str]) -> list[dict]:
    rng = random.Random(seed)
    candidates: list[dict] = []
    combinations = []
    for family, templates in FAMILIES.items():
        for template, direction, hypothesis in templates:
            for fast in (3, 5, 10, 20):
                for slow in (20, 40, 60):
                    if fast < slow:
                        combinations.append((family, template, direction, hypothesis, fast, slow))
    rng.shuffle(combinations)
    for family, template, direction, hypothesis, fast, slow in combinations:
        formula = template.format(fast=fast, slow=slow)
        cid = candidate_id(formula, direction)
        if cid in seen:
            continue
        candidates.append({
            "candidate_id": cid,
            "family": family,
            "formula": formula,
            "factor_direction": direction,
            "parameters": {"fast": fast, "slow": slow},
            "hypothesis": hypothesis,
            "status": "proposed",
        })
        seen.add(cid)
        if len(candidates) >= count:
            break
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PandaAI blind-mining candidates")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ledger", type=Path, default=None,
                        help="Optional JSONL ledger used only for deduplication")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write JSON output; stdout is used when omitted")
    args = parser.parse_args()
    if not 1 <= args.count <= 100:
        parser.error("--count must be between 1 and 100")
    payload = {
        "mode": "blind-mining",
        "seed": args.seed,
        "count": args.count,
        "candidates": generate(args.count, args.seed, load_seen(args.ledger)),
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
