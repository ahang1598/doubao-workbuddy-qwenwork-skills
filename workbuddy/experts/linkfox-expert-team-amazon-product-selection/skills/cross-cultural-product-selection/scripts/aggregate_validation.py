#!/usr/bin/env python3
"""
Multi-Source Validation Aggregator

Combines data from Google Trends, Amazon search, and Alexa search
into a unified product comparison table for final prioritization.

Usage:
  python aggregate_validation.py --trends <trends_json> --amazon <amazon_json> [--alexa <alexa_json>] ... [--inline]

Multiple --trends and --amazon flags are supported for multi-keyword comparison.
Each flag can be repeated: --trends file1 --trends file2 --amazon file3 --amazon file4

Output:
  - Always writes full JSON to <cwd>/linkfox/<YYYY-MM-DD>/<session>/data/
  - Prints comparison table to stdout
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from statistics import mean

SLUG = "cross-cultural-product-selection"
SMALL_THRESHOLD = 8000


def resolve_data_path():
    cwd = os.getcwd()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    session_id = os.environ.get("SESSION_ID", "default")
    base = os.path.join(cwd, "linkfox", today, session_id, "data")
    os.makedirs(base, exist_ok=True)
    return base


def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def load_trends(fpaths):
    """Load and summarize Google Trends data."""
    results = []
    for fpath in fpaths:
        if not os.path.isfile(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("errcode") != 200:
            results.append({"keyword": os.path.basename(fpath), "error": data.get("errmsg")})
            continue
        chart_data = data.get("chartOption", {}).get("data", [])
        if not chart_data:
            results.append({"keyword": "unknown", "error": "no data"})
            continue
        keyword = [k for k in chart_data[0].keys() if k != "timeRange"][0]
        values = [d[keyword] for d in chart_data]
        results.append({
            "keyword": keyword,
            "trends_peak": max(values),
            "trends_avg": round(mean(values), 1),
            "trends_recent_avg": round(mean(values[-12:]), 1) if len(values) >= 12 else round(mean(values), 1),
            "trends_data_points": len(values),
        })
    return results


def load_amazon(fpaths):
    """Load and summarize Amazon search data."""
    results = []
    for fpath in fpaths:
        if not os.path.isfile(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("errcode") != 200:
            results.append({"keyword": os.path.basename(fpath), "error": data.get("errmsg")})
            continue
        products = data.get("products", [])
        keyword = data.get("keyword", "unknown")
        total = data.get("total", len(products))

        prices = [safe_float(p.get("price")) for p in products if p.get("price")]
        ratings = [safe_float(p.get("rating")) for p in products if p.get("rating")]
        review_counts = [safe_int(p.get("ratings")) for p in products if p.get("ratings")]
        sponsored = sum(1 for p in products if p.get("sponsored"))

        results.append({
            "keyword": keyword,
            "amazon_total": total,
            "amazon_price_avg": round(mean(prices), 2) if prices else 0,
            "amazon_price_min": round(min(prices), 2) if prices else 0,
            "amazon_price_max": round(max(prices), 2) if prices else 0,
            "amazon_rating_avg": round(mean(ratings), 1) if ratings else 0,
            "amazon_reviews_avg": round(mean(review_counts)) if review_counts else 0,
            "amazon_sponsored_pct": round(sponsored / len(products) * 100, 1) if products else 0,
            "amazon_new_product_pct": round(
                sum(1 for rc in review_counts if rc < 50) / len(review_counts) * 100, 1
            ) if review_counts else 0,
        })
    return results


def load_alexa(fpaths):
    """Load and summarize Alexa search data."""
    results = []
    for fpath in fpaths:
        if not os.path.isfile(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("errcode") != 200:
            results.append({"keyword": os.path.basename(fpath), "error": data.get("errmsg")})
            continue

        turns = data.get("data", [])
        if not turns:
            results.append({"keyword": "unknown", "error": "no data"})
            continue

        turn = turns[0]
        prompt = turn.get("prompt", "")
        product_groups = turn.get("products", [])
        total_recommended = sum(len(g.get("items", [])) for g in product_groups)

        # Extract all recommended ASINs and their ratings
        recommended_items = []
        for group in product_groups:
            group_title = group.get("title", "")
            for item in group.get("items", []):
                recommended_items.append({
                    "asin": item.get("asin", ""),
                    "title": item.get("title", "")[:80],
                    "score": item.get("score", ""),
                    "ratings_count": item.get("ratingsCount", ""),
                    "group": group_title,
                })

        results.append({
            "keyword": prompt[:60],
            "alexa_groups": len(product_groups),
            "alexa_total_items": total_recommended,
            "alexa_group_titles": [g.get("title", "") for g in product_groups],
            "alexa_top_items": recommended_items[:5],
        })
    return results


def merge_by_keyword(trends_data, amazon_data, alexa_data):
    """Merge data from all sources by keyword."""
    # Build lookup by keyword (fuzzy match)
    merged = {}

    for t in trends_data:
        kw = t.get("keyword", "").lower()
        if "error" in t:
            merged[kw] = {"keyword": t["keyword"], "trends": None, "trends_error": t["error"]}
        else:
            merged[kw] = {"keyword": t["keyword"], "trends": t}

    for a in amazon_data:
        kw = a.get("keyword", "").lower()
        if kw not in merged:
            merged[kw] = {"keyword": a.get("keyword", ""), "trends": None}
        if "error" in a:
            merged[kw]["amazon_error"] = a["error"]
        else:
            merged[kw]["amazon"] = a

    # Alexa data is matched by prompt content, not exact keyword
    for al in alexa_data:
        if "error" in al:
            continue
        prompt = al.get("keyword", "").lower()
        # Find best matching keyword
        best_match = None
        best_score = 0
        for kw in merged:
            # Simple word overlap matching
            prompt_words = set(prompt.split())
            kw_words = set(kw.split())
            overlap = len(prompt_words & kw_words)
            if overlap > best_score:
                best_score = overlap
                best_match = kw
        if best_match and best_score > 0:
            merged[best_match]["alexa"] = al

    return list(merged.values())


def compute_priority(row):
    """Compute a priority score for a product based on available data."""
    score = 50  # base
    reasons = []

    # Trends signals
    t = row.get("trends")
    if t and "error" not in t:
        avg = t.get("trends_avg", 0)
        if avg > 20:
            score += 15
            reasons.append(f"Trends avg {avg} (high demand)")
        elif avg > 5:
            score += 5
            reasons.append(f"Trends avg {avg} (moderate demand)")
        recent = t.get("trends_recent_avg", 0)
        if recent > avg * 0.8:
            score += 5
            reasons.append("Recent demand stable")
        elif recent < avg * 0.3:
            score -= 5
            reasons.append("Recent demand low (off-season?)")

    # Amazon signals
    a = row.get("amazon")
    if a and "error" not in a:
        total = a.get("amazon_total", 0)
        if total < 30:
            score += 15
            reasons.append(f"Only {total} results (low competition)")
        elif total > 100:
            score -= 10
            reasons.append(f"{total} results (high competition)")

        reviews_avg = a.get("amazon_reviews_avg", 0)
        if reviews_avg < 100:
            score += 15
            reasons.append(f"Avg reviews {reviews_avg} (low barrier)")
        elif reviews_avg > 500:
            score -= 10
            reasons.append(f"Avg reviews {reviews_avg} (high barrier)")

        sponsored_pct = a.get("amazon_sponsored_pct", 0)
        if sponsored_pct == 0:
            score += 10
            reasons.append("No sponsored ads (zero ad competition)")
        elif sponsored_pct > 30:
            score -= 5
            reasons.append(f"{sponsored_pct}% sponsored (high ad competition)")

        new_pct = a.get("amazon_new_product_pct", 0)
        if new_pct > 30:
            score += 10
            reasons.append(f"{new_pct}% new products (market accepts newcomers)")

    # Alexa signals
    al = row.get("alexa")
    if al:
        groups = al.get("alexa_groups", 0)
        if groups >= 3:
            score += 5
            reasons.append(f"Alexa returned {groups} recommendation groups")

    row["priority_score"] = max(0, min(100, score))
    row["priority_reasons"] = reasons
    return row


def main():
    parser = argparse.ArgumentParser(description="Aggregate multi-source validation data")
    parser.add_argument("--trends", action="append", default=[], help="Google Trends JSON file path(s)")
    parser.add_argument("--amazon", action="append", default=[], help="Amazon search JSON file path(s)")
    parser.add_argument("--alexa", action="append", default=[], help="Alexa search JSON file path(s)")
    parser.add_argument("--inline", action="store_true", help="Force full JSON output")
    args = parser.parse_args()

    if not args.trends and not args.amazon and not args.alexa:
        print("Error: at least one of --trends, --amazon, --alexa is required")
        sys.exit(1)

    trends_data = load_trends(args.trends)
    amazon_data = load_amazon(args.amazon)
    alexa_data = load_alexa(args.alexa)

    merged = merge_by_keyword(trends_data, amazon_data, alexa_data)
    merged = [compute_priority(row) for row in merged]

    # Sort by priority score
    merged.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    output = {
        "analysis_type": "multi_source_aggregation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "trends_files": len(args.trends),
            "amazon_files": len(args.amazon),
            "alexa_files": len(args.alexa),
        },
        "ranking": [r.get("keyword", "?") for r in merged],
        "products": merged,
    }

    # Always write to data directory
    data_path = resolve_data_path()
    ts = int(time.time() * 1_000_000)
    out_file = os.path.join(data_path, f"validation-aggregation-{ts}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    output_json = json.dumps(output, ensure_ascii=False, indent=2)
    output_bytes = len(output_json.encode("utf-8"))

    if args.inline or output_bytes <= SMALL_THRESHOLD:
        print(output_json)
    else:
        print(f"Saved full response: {out_file} ({output_bytes} bytes)")
        print(f"\nFinal Priority Ranking:")
        print(f"{'#':<3} {'Keyword':<30} {'Score':>5} {'Trends':>7} {'Amazon':>7} {'Alexa':>5} Key Reasons")
        print("-" * 100)
        for i, row in enumerate(merged, 1):
            kw = row.get("keyword", "?")[:28]
            score = row.get("priority_score", 0)
            has_trends = "Y" if row.get("trends") else "N"
            has_amazon = "Y" if row.get("amazon") else "N"
            has_alexa = "Y" if row.get("alexa") else "N"
            reasons = "; ".join(row.get("priority_reasons", [])[:2])
            print(f"{i:<3} {kw:<30} {score:>5} {has_trends:>7} {has_amazon:>7} {has_alexa:>5} {reasons}")
        print(f"\nFull details saved to: {out_file}")
        print("Use --inline to see full JSON output.")


if __name__ == "__main__":
    main()
