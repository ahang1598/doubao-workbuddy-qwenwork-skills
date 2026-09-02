#!/usr/bin/env python3
"""
Priority score for FBA planner exception queue.

Example:
  python priority_score.py --cover-days 12 --age-risk OK --ads-pattern A --tier A
  python priority_score.py --cover-days 52 --age-risk WATCH --ads-pattern B --tier B --policy-cover 45
"""

from __future__ import annotations

import argparse


def stockout_component(cover_days: float) -> int:
    if cover_days < 0:
        return 40
    if cover_days < 7:
        return 40
    if cover_days < 14:
        return 30
    if cover_days < 21:
        return 20
    if cover_days < 28:
        return 10
    return 0


def aged_component(age_risk: str) -> int:
    r = (age_risk or "OK").upper()
    if r == "CRITICAL":
        return 25
    if r == "WATCH":
        return 12
    if r in {"NEAR14", "WITHIN14"}:
        return 20
    if r in {"NEAR30", "WITHIN30"}:
        return 12
    return 0


def ads_component(pattern: str) -> int:
    p = (pattern or "n/a").upper()
    if p == "A":
        return 15
    if p == "B":
        return 8
    if p == "C":
        return 5
    return 0


def tier_component(tier: str) -> int:
    t = (tier or "C").upper()
    if t == "A":
        return 15
    if t == "B":
        return 8
    return 3


def overstock_component(cover_days: float, policy_cover: float, stockout_pts: int) -> int:
    if stockout_pts > 0 or policy_cover <= 0:
        return 0
    ratio = cover_days / policy_cover
    if ratio > 2.0:
        return 5
    if ratio > 1.5:
        return 3
    return 0


def severity_from_score(score: int, age_risk: str, cover_days: float) -> str:
    if score >= 55 or cover_days < 7 or (age_risk or "").upper() == "CRITICAL":
        return "S1"
    if score >= 40 or cover_days < 14:
        return "S2"
    if score >= 25:
        return "S3"
    return "S4"


def exception_codes(cover_days: float, age_risk: str, ads_pattern: str, policy_cover: float) -> str:
    codes = []
    if cover_days < 28:
        codes.append("E1")
    ar = (age_risk or "OK").upper()
    if ar in {"WATCH", "CRITICAL", "NEAR14", "NEAR30", "WITHIN14", "WITHIN30"}:
        codes.append("E2")
    ap = (ads_pattern or "").upper()
    if ap == "A":
        codes.append("E3")
    elif ap == "B":
        codes.append("E4")
    if policy_cover > 0 and cover_days > 1.5 * policy_cover:
        codes.append("E5")
    return "|".join(codes) if codes else "none"


def main():
    p = argparse.ArgumentParser(description="FBA exception priority score")
    p.add_argument("--cover-days", type=float, required=True)
    p.add_argument("--age-risk", default="OK", help="OK / WATCH / CRITICAL / NEAR14 / NEAR30")
    p.add_argument("--ads-pattern", default="n/a", help="A / B / C / D / n/a")
    p.add_argument("--tier", default="B", help="A / B / C")
    p.add_argument("--policy-cover", type=float, default=45.0, help="Policy days of cover for overstock test")
    args = p.parse_args()

    s_stock = stockout_component(args.cover_days)
    s_age = aged_component(args.age_risk)
    s_ads = ads_component(args.ads_pattern)
    s_tier = tier_component(args.tier)
    s_over = overstock_component(args.cover_days, args.policy_cover, s_stock)
    score = min(100, s_stock + s_age + s_ads + s_tier + s_over)
    severity = severity_from_score(score, args.age_risk, args.cover_days)
    codes = exception_codes(args.cover_days, args.age_risk, args.ads_pattern, args.policy_cover)

    print("=" * 52)
    print("FBA PRIORITY SCORE")
    print("=" * 52)
    print(f"Cover days:     {args.cover_days:.1f}")
    print(f"Age risk:       {args.age_risk}")
    print(f"Ads pattern:    {args.ads_pattern}")
    print(f"Tier:           {args.tier}")
    print("-" * 52)
    print(f"Stockout pts:   {s_stock}")
    print(f"Aged pts:       {s_age}")
    print(f"Ads pts:        {s_ads}")
    print(f"Tier pts:       {s_tier}")
    print(f"Overstock pts:  {s_over}")
    print("-" * 52)
    print(f"Priority score: {score}")
    print(f"Severity:       {severity}")
    print(f"Exceptions:     {codes}")
    print("=" * 52)


if __name__ == "__main__":
    main()
