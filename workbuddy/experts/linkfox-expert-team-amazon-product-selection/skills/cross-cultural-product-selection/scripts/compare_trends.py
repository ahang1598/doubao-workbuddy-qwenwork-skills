#!/usr/bin/env python3
"""
Google Trends Multi-Keyword Comparison Tool

Reads multiple Google Trends JSON files produced by linkfox-google-trend-get-trend-by-keys,
computes comparison statistics across all keywords.

Usage:
  python compare_trends.py <trends_json_1> <trends_json_2> ... [--inline]

Output:
  - Always writes full JSON to <cwd>/linkfox/<YYYY-MM-DD>/<session>/data/
  - Prints comparison table to stdout
  - --inline forces full JSON output
"""

import json
import os
import sys
import time
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


def analyze_trends_file(fpath):
    """Extract trend stats from a single Google Trends JSON file."""
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)

    if data.get("errcode") != 200:
        return {"keyword": os.path.basename(fpath), "error": data.get("errmsg", "unknown")}

    chart_data = data.get("chartOption", {}).get("data", [])
    if not chart_data:
        return {"keyword": "unknown", "error": "No chart data"}

    keyword = [k for k in chart_data[0].keys() if k != "timeRange"][0]
    values = [d[keyword] for d in chart_data]
    dates = [d["timeRange"].strip() for d in chart_data]

    if not values:
        return {"keyword": keyword, "error": "No values"}

    max_val = max(values)
    max_idx = values.index(max_val)
    min_val = min(values)
    min_idx = values.index(min_val)

    # Seasonal analysis: group by month
    monthly_avg = {}
    for d, v in zip(dates, values):
        month_key = d[:7]  # YYYY-MM
        if month_key not in monthly_avg:
            monthly_avg[month_key] = []
        monthly_avg[month_key].append(v)
    monthly_summary = {
        m: round(mean(vs), 1)
        for m, vs in sorted(monthly_avg.items())
    }

    # Recent 12 weeks
    recent = values[-12:]
    recent_avg = round(mean(recent), 1) if recent else 0

    # Year-over-year comparison (if data spans multiple years)
    yearly_avg = {}
    for d, v in zip(dates, values):
        year = d[:4]
        if year not in yearly_avg:
            yearly_avg[year] = []
        yearly_avg[year].append(v)
    yearly_summary = {
        y: round(mean(vs), 1)
        for y, vs in sorted(yearly_avg.items())
    }

    # Detect seasonality: check if peak month is consistent across years
    peak_months = []
    for year in sorted(yearly_avg.keys()):
        year_data = [(d, v) for d, v in zip(dates, values) if d.startswith(year)]
        if year_data:
            peak_month = max(year_data, key=lambda x: x[1])[0][:7]
            peak_months.append(peak_month)

    is_seasonal = False
    seasonal_window = None
    if len(peak_months) >= 2:
        # Check if peaks cluster in same 2-month window
        peak_month_nums = [int(m.split("-")[1]) for m in peak_months]
        if max(peak_month_nums) - min(peak_month_nums) <= 2:
            is_seasonal = True
            seasonal_window = f"Month {min(peak_month_nums)}-{max(peak_month_nums)}"

    return {
        "keyword": keyword,
        "data_points": len(values),
        "date_range": f"{dates[0]} to {dates[-1]}",
        "peak": max_val,
        "peak_date": dates[max_idx],
        "min": min_val,
        "min_date": dates[min_idx],
        "overall_avg": round(mean(values), 1),
        "recent_12wk_avg": recent_avg,
        "yearly_avg": yearly_summary,
        "monthly_avg": monthly_summary,
        "is_seasonal": is_seasonal,
        "seasonal_peak_window": seasonal_window,
        "trend_direction": _detect_trend(values),
    }


def _detect_trend(values):
    """Detect overall trend direction: rising, falling, or stable."""
    if len(values) < 10:
        return "insufficient_data"
    # Compare first quarter avg vs last quarter avg
    q = len(values) // 4
    first_q = mean(values[:q])
    last_q = mean(values[-q:])
    if last_q > first_q * 1.2:
        return "rising"
    elif last_q < first_q * 0.8:
        return "falling"
    else:
        return "stable"


def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_trends.py <trends_json_1> <trends_json_2> ... [--inline]")
        sys.exit(1)

    inline = "--inline" in sys.argv
    files = [f for f in sys.argv[1:] if not f.startswith("--")]

    results = []
    for fpath in files:
        if not os.path.isfile(fpath):
            print(f"Warning: {fpath} not found, skipping", file=sys.stderr)
            continue
        results.append(analyze_trends_file(fpath))

    # Build comparison table
    comparison = []
    for r in results:
        if "error" in r:
            comparison.append({"keyword": r.get("keyword", "?"), "error": r["error"]})
            continue
        comparison.append({
            "keyword": r["keyword"],
            "peak": r["peak"],
            "peak_date": r["peak_date"],
            "overall_avg": r["overall_avg"],
            "recent_12wk_avg": r["recent_12wk_avg"],
            "is_seasonal": r["is_seasonal"],
            "seasonal_peak_window": r["seasonal_peak_window"],
            "trend_direction": r["trend_direction"],
        })

    # Rank by overall_avg (higher = more demand)
    valid = [c for c in comparison if "error" not in c]
    ranked = sorted(valid, key=lambda x: x["overall_avg"], reverse=True)

    output = {
        "analysis_type": "trends_comparison",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_keywords": len(results),
        "comparison_table": comparison,
        "ranking_by_avg_demand": [c["keyword"] for c in ranked],
        "full_details": results,
    }

    # Always write to data directory
    data_path = resolve_data_path()
    ts = int(time.time() * 1_000_000)
    out_file = os.path.join(data_path, f"trends-comparison-{ts}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    output_json = json.dumps(output, ensure_ascii=False, indent=2)
    output_bytes = len(output_json.encode("utf-8"))

    if inline or output_bytes <= SMALL_THRESHOLD:
        print(output_json)
    else:
        print(f"Saved full response: {out_file} ({output_bytes} bytes)")
        print(f"\n{'Keyword':<30} {'Peak':>5} {'Peak Date':<14} {'Avg':>6} {'Recent':>7} {'Seasonal':>9} {'Trend':>10}")
        print("-" * 90)
        for c in comparison:
            if "error" in c:
                print(f"{c.get('keyword', '?'):<30} ERROR: {c['error']}")
                continue
            seasonal = "Yes" if c["is_seasonal"] else "No"
            window = f" ({c['seasonal_peak_window']})" if c.get("seasonal_peak_window") else ""
            print(f"{c['keyword']:<30} {c['peak']:>5} {c['peak_date']:<14} {c['overall_avg']:>6} {c['recent_12wk_avg']:>7} {seasonal:>9}{window:<12} {c['trend_direction']:>10}")
        print(f"\nRanking by avg demand: {' > '.join(r['keyword'] for r in ranked)}")
        print(f"\nFull details saved to: {out_file}")
        print("Use --inline to see full JSON output.")


if __name__ == "__main__":
    main()
