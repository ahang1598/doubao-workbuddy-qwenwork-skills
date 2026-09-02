#!/usr/bin/env python3
"""前台搜索 38 段市场格局聚合 - LinkFox Skill

读取合并后的亚马逊前台搜索商品 JSON（建议已含 page / organic_rank + Keepa 字段），
做 38 段分析 + 新品清单，输出聚合 JSON。

有 Keepa 数据时执行 38 维（竞争格局15 + 进入门槛13 + 趋势生命周期10）；
无 Keepa 数据时自动降级为 6 维。

Usage:
  python aggregate_competition.py <merged_products.json>
  python aggregate_competition.py <merged_products.json> --fixed-buckets
  python aggregate_competition.py <merged_products.json> --buckets <file.json>
  python aggregate_competition.py <merged_products.json> --inline
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime

from linkfox_paths import resolve_data_path

SLUG = "linkfox-amazon-search-competition"
SMALL_THRESHOLD = 8000
MISSING_UNITS_DEFAULT = 50
NEW_PRODUCT_RATINGS_LT = 100

DEFAULT_BUCKETS = {
    "price": [
        {"label": "<$20", "min": 0, "max": 20},
        {"label": "$20-50", "min": 20, "max": 50},
        {"label": "$50-100", "min": 50, "max": 100},
        {"label": "$100-200", "min": 100, "max": 200},
        {"label": "$200+", "min": 200, "max": None},
    ],
    "ratingCount": [
        {"label": "<100", "min": 0, "max": 100},
        {"label": "100-500", "min": 100, "max": 500},
        {"label": "500-2k", "min": 500, "max": 2000},
        {"label": "2k-10k", "min": 2000, "max": 10000},
        {"label": "10k+", "min": 10000, "max": None},
    ],
    "ratingValue": [
        {"label": "<3.5", "min": 0, "max": 3.5},
        {"label": "3.5-4.0", "min": 3.5, "max": 4.0},
        {"label": "4.0-4.5", "min": 4.0, "max": 4.5},
        {"label": "4.5-5.0", "min": 4.5, "max": None},
    ],
}

KEEPA_BUCKETS = {
    "variationNum": [
        {"label": "0", "min": -1, "max": 1},
        {"label": "1-5", "min": 1, "max": 6},
        {"label": "6-20", "min": 6, "max": 21},
        {"label": "21-50", "min": 21, "max": 51},
        {"label": "50+", "min": 51, "max": None},
    ],
    "sellerNum": [
        {"label": "1", "min": 0, "max": 2},
        {"label": "2-3", "min": 2, "max": 4},
        {"label": "4-10", "min": 4, "max": 11},
        {"label": "11+", "min": 11, "max": None},
    ],
    "profit": [
        {"label": "<0%", "min": -999, "max": 0},
        {"label": "0-10%", "min": 0, "max": 10},
        {"label": "10-20%", "min": 10, "max": 20},
        {"label": "20-30%", "min": 20, "max": 30},
        {"label": "30%+", "min": 30, "max": None},
    ],
    "fbaFees": [
        {"label": "<$3", "min": -1, "max": 3},
        {"label": "$3-5", "min": 3, "max": 5},
        {"label": "$5-8", "min": 5, "max": 8},
        {"label": "$8-12", "min": 8, "max": 12},
        {"label": "$12+", "min": 12, "max": None},
    ],
    "availableMonths": [
        {"label": "<6月", "min": -1, "max": 6},
        {"label": "6-12月", "min": 6, "max": 12},
        {"label": "1-2年", "min": 12, "max": 24},
        {"label": "2-3年", "min": 24, "max": 36},
        {"label": "3年+", "min": 36, "max": None},
    ],
}

RANK_SEGMENTS = [
    {"label": "Top10", "min": 1, "max": 10},
    {"label": "11-20", "min": 11, "max": 20},
    {"label": "21-48", "min": 21, "max": 48},
    {"label": "49+", "min": 49, "max": None},
]


# ── helpers ─────────────────────────────────────────────────────

def safe_float(val, default=None):
    if val is None or val == "":
        return default
    try:
        if isinstance(val, str):
            val = val.replace(",", "").replace("$", "").strip()
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_int(val, default=None):
    f = safe_float(val, None)
    if f is None:
        return default
    try:
        return int(f)
    except (TypeError, ValueError):
        return default


def get_price(p):
    return safe_float(p.get("extractedPrice"), None) or safe_float(p.get("price"), 0.0) or 0.0


def get_units(p):
    raw = p.get("monthlySalesUnits")
    if raw is None or raw == "":
        return MISSING_UNITS_DEFAULT, True
    v = safe_int(raw, None)
    if v is None:
        return MISSING_UNITS_DEFAULT, True
    return max(v, 0), False


def get_revenue(p, units, price):
    raw = p.get("monthlySalesRevenue")
    if raw not in (None, ""):
        v = safe_float(raw, None)
        if v is not None:
            return v, False
    return float(units) * float(price or 0), True


def has_variant(p):
    opt = p.get("options")
    return opt not in (None, "", [], {})


def load_products(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "products" in data:
            return data["products"]
        if "items" in data:
            return data["items"]
    raise ValueError("Input must be a list of products or an object with products/items")


def load_buckets(arg):
    if os.path.exists(arg):
        with open(arg, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)


def ensure_organic_rank(products):
    if products and all(p.get("organic_rank") is not None for p in products):
        out = sorted(products, key=lambda p: (safe_int(p.get("organic_rank"), 10**9), p.get("asin") or ""))
        return out, "provided"

    has_page = any(p.get("page") is not None for p in products)
    if not has_page:
        out = []
        for i, p in enumerate(products, 1):
            q = dict(p)
            q["organic_rank"] = i
            q.setdefault("page_position", p.get("position"))
            out.append(q)
        return out, "sequential-fallback"

    by_page = defaultdict(list)
    for p in products:
        if p.get("sponsored") is True:
            continue
        pg = safe_int(p.get("page"), 1) or 1
        by_page[pg].append(p)

    ranked = []
    rank = 0
    for pg in sorted(by_page.keys()):
        page_items = sorted(
            by_page[pg],
            key=lambda x: safe_int(x.get("page_position") or x.get("position"), 999) or 999,
        )
        for p in page_items:
            rank += 1
            q = dict(p)
            q["page"] = pg
            q["page_position"] = p.get("page_position") or p.get("position")
            q["organic_rank"] = rank
            ranked.append(q)

    best = {}
    for item in ranked:
        a = item.get("asin")
        if not a:
            continue
        if a not in best or item["organic_rank"] < best[a]["organic_rank"]:
            best[a] = item
    out = sorted(best.values(), key=lambda x: x["organic_rank"])
    return out, "recomputed"


def enrich(products):
    out = []
    raw_units = 0
    for p in products:
        q = dict(p)
        price = get_price(q)
        units, imputed = get_units(q)
        rev, rev_imputed = get_revenue(q, units, price)
        q["_price"] = price
        q["_units"] = units
        q["_revenue"] = rev
        q["units_imputed"] = imputed
        q["revenue_imputed"] = rev_imputed
        q["has_variant"] = has_variant(q)
        if not imputed:
            raw_units += 1
        out.append(q)
    return out, raw_units


def _in_bucket(val, b):
    if val is None:
        return False
    lo = b["min"]
    hi = b["max"]
    if hi is None:
        return val >= lo
    return lo <= val < hi


def bucket_stats(items, value_fn, bucket_defs):
    total_units = sum(x["_units"] for x in items) or 1
    labels, counts, unit_shares = [], [], []
    for b in bucket_defs:
        sub = [x for x in items if _in_bucket(value_fn(x), b)]
        u = sum(x["_units"] for x in sub)
        labels.append(b["label"])
        counts.append(len(sub))
        unit_shares.append(round(100.0 * u / total_units, 1))
    return {
        "labels": labels,
        "productCounts": counts,
        "salesShares": unit_shares,
    }


# ── Keepa 辅助函数 ──────────────────────────────────────────────

def median(values):
    """中位数，忽略 None。"""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    if n % 2 == 0:
        return (vals[mid - 1] + vals[mid]) / 2.0
    return float(vals[mid])


def coefficient_of_variation(values):
    """CV = stdev / mean，忽略 None。"""
    vals = [v for v in values if v is not None and v > 0]
    if len(vals) < 2:
        return None
    mean = sum(vals) / len(vals)
    if mean == 0:
        return None
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return round(math.sqrt(variance) / mean * 100, 1)


def parse_available_date_to_months(date_str, now=None):
    """解析 availableDate 为上架月数。"""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(date_str.strip()[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    if now is None:
        now = datetime.now()
    delta = now - dt
    return max(0, int(delta.days / 30.44))


def safe_keepa_field(product, field, default=None):
    """安全提取 Keepa 字段，处理 -1/0 表示不可用。"""
    val = product.get(field)
    if val in (None, -1, 0, "0", "-1", ""):
        return default
    return val


def group_by_field(items, field):
    """按字段分组。"""
    groups = defaultdict(list)
    for x in items:
        val = x.get(field) or "Unknown"
        groups[val].append(x)
    return dict(groups)


def calc_cr_n(brand_units, n):
    """计算 CR_n（前 n 个品牌的销量份额之和）。"""
    sorted_brands = sorted(brand_units.items(), key=lambda kv: kv[1], reverse=True)
    top_n = sorted_brands[:n]
    total = sum(brand_units.values()) or 1
    return round(100.0 * sum(v for _, v in top_n) / total, 1), [b for b, _ in top_n]


def keepa_coverage_pct(items):
    """计算 Keepa 数据覆盖率。"""
    if not items:
        return 0, 0, 0
    keepa_count = sum(1 for x in items if x.get("keepa_available"))
    total = len(items)
    return round(100.0 * keepa_count / total, 1), keepa_count, total


# ── 基础 6 段计算（维度 1-6） ───────────────────────────────────

def calc_page_traffic(items):
    total_u = sum(x["_units"] for x in items) or 1
    total_r = sum(x["_revenue"] for x in items) or 1
    by_page = defaultdict(lambda: {"n": 0, "units": 0, "revenue": 0.0})
    for x in items:
        pg = safe_int(x.get("page"), 0) or 0
        by_page[pg]["n"] += 1
        by_page[pg]["units"] += x["_units"]
        by_page[pg]["revenue"] += x["_revenue"]
    pages = []
    for pg in sorted(by_page.keys()):
        d = by_page[pg]
        pages.append({
            "page": pg,
            "productCount": d["n"],
            "units": d["units"],
            "revenue": round(d["revenue"], 2),
            "unitsShare": round(100.0 * d["units"] / total_u, 1),
            "revenueShare": round(100.0 * d["revenue"] / total_r, 1),
        })
    return {
        "dimension": 1,
        "name": "页流量占比",
        "type": "table",
        "data": {"pages": pages, "totalUnits": sum(x["_units"] for x in items),
                 "totalRevenue": round(sum(x["_revenue"] for x in items), 2)},
    }


def calc_rank_concentration(items):
    total_u = sum(x["_units"] for x in items) or 1
    segments = []
    cum = 0
    for seg in RANK_SEGMENTS:
        lo, hi = seg["min"], seg["max"]
        if hi is None:
            sub = [x for x in items if (x.get("organic_rank") or 0) >= lo]
        else:
            sub = [x for x in items if lo <= (x.get("organic_rank") or 0) <= hi]
        u = sum(x["_units"] for x in sub)
        cum += u
        segments.append({
            "label": seg["label"],
            "productCount": len(sub),
            "units": u,
            "unitsShare": round(100.0 * u / total_u, 1),
            "cumulativeShare": round(100.0 * cum / total_u, 1),
        })
    top10 = [x for x in items if 1 <= (x.get("organic_rank") or 0) <= 10]
    top10_share = round(100.0 * sum(x["_units"] for x in top10) / total_u, 1)
    return {
        "dimension": 2,
        "name": "自然位集中度",
        "type": "pareto",
        "data": {
            "segments": segments,
            "top10UnitsShare": top10_share,
            "labels": [s["label"] for s in segments],
            "units": [s["units"] for s in segments],
            "cumulativeShare": [s["cumulativeShare"] for s in segments],
        },
    }


def calc_price_distribution(items, bucket_defs):
    stats = bucket_stats(items, lambda x: x["_price"], bucket_defs)
    total_u = sum(x["_units"] for x in items) or 1
    weighted = sum(x["_price"] * x["_units"] for x in items) / total_u
    simple = (sum(x["_price"] for x in items) / len(items)) if items else 0
    return {
        "dimension": 3,
        "name": "价格分布",
        "type": "distribution",
        "data": {
            **stats,
            "salesWeightedAvgPrice": round(weighted, 2),
            "simpleAvgPrice": round(simple, 2),
        },
    }


def calc_rating_count_distribution(items, bucket_defs):
    def rc(x):
        return safe_int(x.get("ratings"), None)
    stats = bucket_stats(items, rc, bucket_defs)
    return {"dimension": 4, "name": "评分数分布", "type": "distribution", "data": stats}


def calc_rating_value_distribution(items, bucket_defs):
    def rv(x):
        return safe_float(x.get("rating"), None)
    stats = bucket_stats(items, rv, bucket_defs)
    return {"dimension": 5, "name": "评分分布", "type": "distribution", "data": stats}


def calc_has_variant(items):
    total = len(items) or 1
    total_u = sum(x["_units"] for x in items) or 1
    with_v = [x for x in items if x.get("has_variant")]
    u = sum(x["_units"] for x in with_v)
    return {
        "dimension": 6,
        "name": "变体覆盖",
        "type": "data",
        "data": {
            "totalProducts": len(items),
            "hasVariantCount": len(with_v),
            "hasVariantRatio": round(100.0 * len(with_v) / total, 1),
            "hasVariantUnitsShare": round(100.0 * u / total_u, 1),
            "note": "options 非空视为含变体；Keepa variationNum 可补充变体复杂度",
        },
    }


# ── A 组：竞争格局（维度 7-15） ────────────────────────────────

def calc_brand_concentration(items):
    groups = group_by_field(items, "brand")
    total = len(items) or 1
    brands = []
    for brand, sub in sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True):
        brands.append({
            "brand": brand,
            "asinCount": len(sub),
            "asinShare": round(100.0 * len(sub) / total, 1),
        })
    return {
        "dimension": 7, "name": "品牌集中度", "type": "table",
        "data": {"brands": brands[:20], "totalBrands": len(groups)},
    }


def calc_brand_sales_share(items):
    groups = group_by_field(items, "brand")
    total_u = sum(x["_units"] for x in items) or 1
    brands = []
    for brand, sub in sorted(groups.items(), key=lambda kv: sum(x["_units"] for x in kv[1]), reverse=True):
        u = sum(x["_units"] for x in sub)
        brands.append({
            "brand": brand,
            "asinCount": len(sub),
            "units": u,
            "unitsShare": round(100.0 * u / total_u, 1),
        })
    return {
        "dimension": 8, "name": "品牌销量份额", "type": "table",
        "data": {"brands": brands[:20]},
    }


def calc_brand_monopoly_cr(items):
    groups = group_by_field(items, "brand")
    brand_units = {b: sum(x["_units"] for x in sub) for b, sub in groups.items()}
    cr3, top3 = calc_cr_n(brand_units, 3)
    cr5, top5 = calc_cr_n(brand_units, 5)
    return {
        "dimension": 9, "name": "头部品牌垄断系数", "type": "data",
        "data": {"cr3": cr3, "cr5": cr5, "top3Brands": top3, "top5Brands": top5,
                 "label": f"CR3={cr3}% / CR5={cr5}%"},
    }


def calc_seller_concentration(items):
    groups = group_by_field(items, "buyBoxSellerId")
    total = len(items) or 1
    sellers = []
    for sid, sub in sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True):
        sellers.append({
            "sellerId": sid,
            "asinCount": len(sub),
            "asinShare": round(100.0 * len(sub) / total, 1),
        })
    return {
        "dimension": 10, "name": "卖家集中度", "type": "table",
        "data": {"sellers": sellers[:15], "totalSellers": len(groups)},
    }


def calc_fulfillment_distribution(items):
    groups = group_by_field(items, "fulfillment")
    total = len(items) or 1
    total_u = sum(x["_units"] for x in items) or 1
    fulfills = []
    for ftype, sub in sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True):
        u = sum(x["_units"] for x in sub)
        fulfills.append({
            "type": ftype,
            "count": len(sub),
            "share": round(100.0 * len(sub) / total, 1),
            "unitsShare": round(100.0 * u / total_u, 1),
        })
    return {
        "dimension": 11, "name": "配送方式占比", "type": "pie",
        "data": {"fulfillments": fulfills},
    }


def calc_variation_complexity(items, bucket_defs):
    stats = bucket_stats(items, lambda x: safe_keepa_field(x, "variationNum", -1), bucket_defs)
    return {
        "dimension": 12, "name": "变体复杂度分布", "type": "distribution",
        "data": {**stats, "note": "variationNum 来自 Keepa"},
    }


def calc_seller_num_distribution(items, bucket_defs):
    stats = bucket_stats(items, lambda x: safe_keepa_field(x, "sellerNum", -1), bucket_defs)
    return {
        "dimension": 13, "name": "卖家数量分布", "type": "distribution",
        "data": {**stats, "note": "sellerNum 来自 Keepa"},
    }


def calc_multi_seller_ratio(items):
    total = len(items) or 1
    total_u = sum(x["_units"] for x in items) or 1
    multi = [x for x in items if safe_keepa_field(x, "sellerNum", 0) and safe_keepa_field(x, "sellerNum", 0) > 1]
    u = sum(x["_units"] for x in multi)
    return {
        "dimension": 14, "name": "多卖家竞争占比", "type": "data",
        "data": {"totalProducts": len(items), "multiSellerCount": len(multi),
                 "multiSellerRatio": round(100.0 * len(multi) / total, 1),
                 "multiSellerUnitsShare": round(100.0 * u / total_u, 1)},
    }


def calc_category_distribution(items):
    cat_groups = defaultdict(list)
    for x in items:
        subs = x.get("subcategories")
        cat = "Unknown"
        if subs and isinstance(subs, list) and len(subs) > 0:
            cat = subs[0].get("label", "Unknown") if isinstance(subs[0], dict) else str(subs[0])
        elif x.get("categoryTree"):
            parts = x.get("categoryTree", "").split(":")
            cat = parts[-1].strip() if parts else "Unknown"
        cat_groups[cat].append(x)
    total = len(items) or 1
    total_u = sum(x["_units"] for x in items) or 1
    cats = []
    for cat, sub in sorted(cat_groups.items(), key=lambda kv: len(kv[1]), reverse=True):
        u = sum(x["_units"] for x in sub)
        cats.append({"category": cat, "asinCount": len(sub),
                     "asinShare": round(100.0 * len(sub) / total, 1),
                     "units": u, "unitsShare": round(100.0 * u / total_u, 1)})
    return {
        "dimension": 15, "name": "类目分布", "type": "table",
        "data": {"categories": cats[:15]},
    }


# ── B 组：进入门槛（维度 16-28） ───────────────────────────────

def calc_review_threshold_top10(items):
    top10 = [x for x in items if 1 <= (x.get("organic_rank") or 0) <= 10]
    ratings = [safe_int(x.get("ratings"), None) for x in top10]
    ratings = [r for r in ratings if r is not None]
    if not ratings:
        return {"dimension": 16, "name": "评论门槛(Top10)", "type": "data", "data": {"top10Avg": None, "top10Median": None}}
    return {
        "dimension": 16, "name": "评论门槛(Top10)", "type": "data",
        "data": {"top10Avg": round(sum(ratings) / len(ratings), 0),
                 "top10Median": median(ratings),
                 "top10Min": min(ratings), "top10Max": max(ratings)},
    }


def calc_review_median(items):
    ratings = [safe_int(x.get("ratings"), None) for x in items]
    ratings = sorted(r for r in ratings if r is not None)
    if not ratings:
        return {"dimension": 17, "name": "评论中位数", "type": "data", "data": {"median": None}}
    return {
        "dimension": 17, "name": "评论中位数", "type": "data",
        "data": {"median": median(ratings), "p25": round(_percentile(ratings, 25), 0),
                 "p75": round(_percentile(ratings, 75), 0)},
    }


def calc_new_product_review_growth(items):
    scatter = []
    for x in items:
        age = parse_available_date_to_months(x.get("availableDate"))
        ratings = safe_int(x.get("ratings"), None)
        if age is not None and age > 0 and ratings is not None and ratings > 0:
            scatter.append({
                "asin": x.get("asin"),
                "ageMonths": age,
                "ratings": ratings,
                "monthlyGrowthRate": round(ratings / age, 1),
            })
    avg = round(sum(s["monthlyGrowthRate"] for s in scatter) / len(scatter), 1) if scatter else None
    return {
        "dimension": 18, "name": "新品评论增长速度", "type": "scatter",
        "data": {"scatterData": scatter[:50], "avgGrowthRate": avg},
    }


def calc_price_threshold(items):
    prices = sorted(x["_price"] for x in items if x["_price"] is not None and x["_price"] > 0)
    if not prices:
        return {"dimension": 19, "name": "价格门槛", "type": "data", "data": {}}
    return {
        "dimension": 19, "name": "价格门槛", "type": "data",
        "data": {"p25": round(_percentile(prices, 25), 2), "p50": round(_percentile(prices, 50), 2),
                 "p75": round(_percentile(prices, 75), 2), "min": prices[0], "max": prices[-1]},
    }


def calc_bsr_threshold_top10(items):
    top10 = [x for x in items if 1 <= (x.get("organic_rank") or 0) <= 10]
    ranks = [safe_keepa_field(x, "salesRank") for x in top10]
    ranks = [r for r in ranks if r is not None and r > 0]
    cov_pct, cov_n, _ = keepa_coverage_pct(top10)
    if not ranks:
        return {"dimension": 20, "name": "BSR门槛(Top10)", "type": "data",
                "data": {"top10Avg": None, "keepaCoverage": cov_pct}}
    return {
        "dimension": 20, "name": "BSR门槛(Top10)", "type": "data",
        "data": {"top10Avg": round(sum(ranks) / len(ranks), 0), "top10Median": median(ranks),
                 "top10Min": min(ranks), "top10Max": max(ranks), "keepaCoverage": cov_pct},
    }


def calc_bsr_median(items):
    ranks = [safe_keepa_field(x, "salesRank") for x in items]
    ranks = sorted(r for r in ranks if r is not None and r > 0)
    cov_pct, _, _ = keepa_coverage_pct(items)
    if not ranks:
        return {"dimension": 21, "name": "BSR中位数", "type": "data",
                "data": {"median": None, "keepaCoverage": cov_pct}}
    return {
        "dimension": 21, "name": "BSR中位数", "type": "data",
        "data": {"median": median(ranks), "p25": round(_percentile(ranks, 25), 0),
                 "p75": round(_percentile(ranks, 75), 0), "keepaCoverage": cov_pct},
    }


def calc_profit_distribution(items, bucket_defs):
    stats = bucket_stats(items, lambda x: safe_keepa_field(x, "profit", -1), bucket_defs)
    profits = [safe_keepa_field(x, "profit") for x in items]
    profits = [p for p in profits if p is not None]
    cov_pct, _, _ = keepa_coverage_pct(items)
    return {
        "dimension": 22, "name": "利润率分布", "type": "distribution",
        "data": {**stats, "avgProfit": round(sum(profits) / len(profits), 1) if profits else None,
                 "keepaCoverage": cov_pct},
    }


def calc_fba_fee_distribution(items, bucket_defs):
    stats = bucket_stats(items, lambda x: safe_keepa_field(x, "fbaFees", -1), bucket_defs)
    fees = [safe_keepa_field(x, "fbaFees") for x in items]
    fees = [f for f in fees if f is not None]
    cov_pct, _, _ = keepa_coverage_pct(items)
    return {
        "dimension": 23, "name": "FBA费用分布", "type": "distribution",
        "data": {**stats, "avgFbaFee": round(sum(fees) / len(fees), 2) if fees else None,
                 "keepaCoverage": cov_pct},
    }


def calc_referral_fee_distribution(items):
    fees = [safe_keepa_field(x, "referralFeePercentage") for x in items]
    fees = [f for f in fees if f is not None]
    cov_pct, _, _ = keepa_coverage_pct(items)
    if not fees:
        return {"dimension": 24, "name": "佣金率分布", "type": "distribution",
                "data": {"keepaCoverage": cov_pct}}
    fee_counts = defaultdict(int)
    for f in fees:
        fee_counts[round(f, 1)] += 1
    sorted_fees = sorted(fee_counts.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "dimension": 24, "name": "佣金率分布", "type": "distribution",
        "data": {"fees": [{"fee": f, "count": c, "share": round(100.0 * c / len(fees), 1)} for f, c in sorted_fees[:10]],
                 "mostCommonFee": sorted_fees[0][0] if sorted_fees else None,
                 "keepaCoverage": cov_pct},
    }


def calc_hazmat_ratio(items):
    cov_pct, cov_n, total = keepa_coverage_pct(items)
    hazmat = [x for x in items if x.get("keepa_available") and x.get("isHazmat") == True]
    return {
        "dimension": 25, "name": "危险品占比", "type": "data",
        "data": {"totalProducts": total, "hazmatCount": len(hazmat),
                 "hazmatRatio": round(100.0 * len(hazmat) / total, 1) if total else 0,
                 "keepaCoverage": cov_pct},
    }


def calc_adult_product_ratio(items):
    cov_pct, cov_n, total = keepa_coverage_pct(items)
    adult = [x for x in items if x.get("keepa_available") and x.get("isAdultProduct") == True]
    return {
        "dimension": 26, "name": "成人产品占比", "type": "data",
        "data": {"totalProducts": total, "adultCount": len(adult),
                 "adultRatio": round(100.0 * len(adult) / total, 1) if total else 0,
                 "keepaCoverage": cov_pct},
    }


def calc_listing_age_distribution(items, bucket_defs):
    ages = []
    for x in items:
        age = parse_available_date_to_months(x.get("availableDate"))
        if age is not None:
            ages.append(age)
    cov_pct, _, _ = keepa_coverage_pct(items)
    stats = bucket_stats(items, lambda x: parse_available_date_to_months(x.get("availableDate")) or -1, bucket_defs)
    return {
        "dimension": 27, "name": "上架时间分布", "type": "distribution",
        "data": {**stats, "avgAgeMonths": round(sum(ages) / len(ages), 1) if ages else None,
                 "keepaCoverage": cov_pct},
    }


def calc_new_product_ratio(items):
    cov_pct, cov_n, total = keepa_coverage_pct(items)
    new_asins = []
    for x in items:
        age = parse_available_date_to_months(x.get("availableDate"))
        if age is not None and age < 6:
            new_asins.append(x.get("asin"))
    return {
        "dimension": 28, "name": "新品占比", "type": "data",
        "data": {"totalProducts": total, "newCount": len(new_asins),
                 "newRatio": round(100.0 * len(new_asins) / total, 1) if total else 0,
                 "newAsins": new_asins[:20], "keepaCoverage": cov_pct},
    }


# ── C 组：趋势与生命周期（维度 29-38） ─────────────────────────

def calc_sales_trend(items):
    cov_pct, _, _ = keepa_coverage_pct(items)
    per_asin = []
    current_total = 0
    m1_total = 0
    m3_total = 0
    m6_total = 0
    m12_total = 0
    count = 0
    for x in items:
        cur = safe_keepa_field(x, "monthlySalesUnits")
        m1 = safe_keepa_field(x, "monthlySalesUnits1MonthAgo")
        m3 = safe_keepa_field(x, "monthlySalesUnits3MonthsAgo")
        m6 = safe_keepa_field(x, "monthlySalesUnits6MonthsAgo")
        m12 = safe_keepa_field(x, "monthlySalesUnits12MonthsAgo")
        if cur is None:
            continue
        count += 1
        current_total += cur
        if m1: m1_total += m1
        if m3: m3_total += m3
        if m6: m6_total += m6
        if m12: m12_total += m12
        # 趋势判定
        trend = "stable"
        if m6 and cur > m6 * 1.1:
            trend = "growing"
        elif m6 and cur < m6 * 0.9:
            trend = "declining"
        per_asin.append({"asin": x.get("asin"), "current": cur, "m1": m1, "m3": m3, "m6": m6, "m12": m12, "trend": trend})
    market_trend = "stable"
    if count > 0 and m6_total > 0:
        if current_total > m6_total * 1.1:
            market_trend = "growing"
        elif current_total < m6_total * 0.9:
            market_trend = "declining"
    return {
        "dimension": 29, "name": "月销量趋势", "type": "trend",
        "data": {"current": current_total, "m1": m1_total, "m3": m3_total,
                 "m6": m6_total, "m12": m12_total, "trend": market_trend,
                 "perAsin": per_asin[:30], "keepaCoverage": cov_pct},
    }


def calc_market_sales_trend(items):
    cov_pct, _, _ = keepa_coverage_pct(items)
    months = []
    for month_idx in range(12, -1, -1):
        if month_idx == 0:
            field = "monthlySalesUnits"
            label = "当前"
        else:
            field = f"monthlySalesUnits{month_idx}MonthsAgo"
            label = f"{month_idx}月前"
        total = 0
        for x in items:
            v = safe_keepa_field(x, field)
            if v:
                total += v
        months.append({"month": label, "totalUnits": total})
    # 趋势
    vals = [m["totalUnits"] for m in months if m["totalUnits"] > 0]
    trend = "stable"
    if len(vals) >= 4:
        first_half = sum(vals[:len(vals)//2]) / (len(vals)//2)
        second_half = sum(vals[len(vals)//2:]) / (len(vals) - len(vals)//2)
        if second_half > first_half * 1.1:
            trend = "growing"
        elif second_half < first_half * 0.9:
            trend = "declining"
    peak = max(months, key=lambda m: m["totalUnits"]) if months else None
    trough = min((m for m in months if m["totalUnits"] > 0), key=lambda m: m["totalUnits"], default=None)
    return {
        "dimension": 30, "name": "市场总销量趋势", "type": "trend",
        "data": {"monthlyTotals": months, "trend": trend,
                 "peakMonth": peak["month"] if peak else None,
                 "troughMonth": trough["month"] if trough else None,
                 "keepaCoverage": cov_pct},
    }


def calc_bsr_trend(items):
    cov_pct, _, _ = keepa_coverage_pct(items)
    per_asin = []
    for x in items:
        cur = safe_keepa_field(x, "salesRank")
        d30 = safe_keepa_field(x, "salesRank30")
        d90 = safe_keepa_field(x, "salesRank90")
        d180 = safe_keepa_field(x, "salesRank180")
        if cur is None:
            continue
        trend = "stable"
        if d180 and cur < d180 * 0.9:
            trend = "improving"
        elif d180 and cur > d180 * 1.1:
            trend = "declining"
        per_asin.append({"asin": x.get("asin"), "current": cur, "d30": d30, "d90": d90, "d180": d180, "trend": trend})
    return {
        "dimension": 31, "name": "BSR趋势", "type": "trend",
        "data": {"perAsin": per_asin[:30], "keepaCoverage": cov_pct},
    }


def calc_bsr_volatility(items):
    cov_pct, _, _ = keepa_coverage_pct(items)
    cvs = []
    for x in items:
        ranks = [safe_keepa_field(x, f) for f in ("salesRank", "salesRank30", "salesRank90", "salesRank180")]
        ranks = [r for r in ranks if r is not None and r > 0]
        if len(ranks) < 2:
            continue
        mean = sum(ranks) / len(ranks)
        if mean == 0:
            continue
        variance = sum((r - mean) ** 2 for r in ranks) / len(ranks)
        cv = math.sqrt(variance) / mean * 100
        cvs.append(round(cv, 1))
    avg_cv = round(sum(cvs) / len(cvs), 1) if cvs else None
    high_vol = len([c for c in cvs if c > 30])
    return {
        "dimension": 32, "name": "BSR波动度", "type": "data",
        "data": {"avgCV": avg_cv, "highVolatilityCount": high_vol,
                 "highVolatilityRatio": round(100.0 * high_vol / len(cvs), 1) if cvs else 0,
                 "perAsinCVs": cvs[:30], "keepaCoverage": cov_pct},
    }


def calc_new_product_growth_speed(items):
    new_products = []
    for x in items:
        age = parse_available_date_to_months(x.get("availableDate"))
        if age is None or age >= 6:
            continue
        cur = safe_keepa_field(x, "monthlySalesUnits")
        m3 = safe_keepa_field(x, "monthlySalesUnits3MonthsAgo")
        if cur is None:
            continue
        growth = None
        if m3 and m3 > 0:
            growth = round((cur - m3) / m3 * 100, 1)
        new_products.append({"asin": x.get("asin"), "currentUnits": cur,
                            "units3MonthsAgo": m3, "growthRate": growth})
    avg_growth = None
    growths = [p["growthRate"] for p in new_products if p["growthRate"] is not None]
    if growths:
        avg_growth = round(sum(growths) / len(growths), 1)
    return {
        "dimension": 33, "name": "新品起量速度", "type": "scatter",
        "data": {"newProducts": new_products[:30], "avgGrowthRate": avg_growth},
    }


def calc_lifecycle_stage(items):
    stages = {"导入期": [], "成长期": [], "成熟期": [], "衰退期": []}
    for x in items:
        age = parse_available_date_to_months(x.get("availableDate"))
        ratings = safe_int(x.get("ratings"), 0) or 0
        cur = safe_keepa_field(x, "monthlySalesUnits")
        m6 = safe_keepa_field(x, "monthlySalesUnits6MonthsAgo")
        trend = "stable"
        if cur and m6:
            if cur > m6 * 1.1:
                trend = "growing"
            elif cur < m6 * 0.9:
                trend = "declining"
        if age is not None and age < 6 and ratings < 100:
            stage = "导入期"
        elif age is not None and 6 <= age <= 18 and ratings < 1000 and trend == "growing":
            stage = "成长期"
        elif age is not None and age > 18 and ratings >= 1000 and trend == "stable":
            stage = "成熟期"
        elif trend == "declining" and ratings > 500:
            stage = "衰退期"
        else:
            stage = "成熟期" if age and age > 18 else "成长期"
        stages[stage].append(x.get("asin"))
    total = len(items) or 1
    result_stages = []
    for stage, asins in stages.items():
        result_stages.append({
            "stage": stage, "count": len(asins),
            "share": round(100.0 * len(asins) / total, 1),
            "asins": asins[:10],
        })
    return {
        "dimension": 34, "name": "产品生命周期阶段", "type": "table",
        "data": {"stages": result_stages},
    }


def calc_market_maturity(items):
    ages = [parse_available_date_to_months(x.get("availableDate")) for x in items]
    ages = [a for a in ages if a is not None]
    ratings = [safe_int(x.get("ratings"), 0) or 0 for x in items]
    avg_age = round(sum(ages) / len(ages), 1) if ages else None
    avg_ratings = round(sum(ratings) / len(ratings), 0) if ratings else 0
    if avg_age and avg_ratings:
        if avg_age > 24 and avg_ratings > 2000:
            stage = "mature"
        elif avg_age > 12:
            stage = "growing"
        else:
            stage = "emerging"
    else:
        stage = "unknown"
    cov_pct, _, _ = keepa_coverage_pct(items)
    return {
        "dimension": 35, "name": "市场成熟度", "type": "data",
        "data": {"avgAgeMonths": avg_age, "avgRatings": avg_ratings,
                 "stage": stage, "keepaCoverage": cov_pct},
    }


def calc_top_vs_new_sales(items):
    top10 = [x for x in items if 1 <= (x.get("organic_rank") or 0) <= 10]
    new_items = [x for x in items if (parse_available_date_to_months(x.get("availableDate")) or 999) < 6]
    if not new_items:
        new_items = [x for x in items if (safe_int(x.get("ratings"), 999) or 999) < NEW_PRODUCT_RATINGS_LT]
    top10_avg = round(sum(x["_units"] for x in top10) / len(top10), 0) if top10 else 0
    new_avg = round(sum(x["_units"] for x in new_items) / len(new_items), 0) if new_items else 0
    ratio = round(top10_avg / new_avg, 1) if new_avg > 0 else None
    return {
        "dimension": 36, "name": "头部vs新品销量对比", "type": "comparison",
        "data": {"top10AvgUnits": top10_avg, "newAvgUnits": new_avg,
                 "ratio": ratio, "gap": round(top10_avg - new_avg, 0),
                 "top10Count": len(top10), "newCount": len(new_items)},
    }


def calc_price_dispersion(items):
    prices = [x["_price"] for x in items if x["_price"] is not None and x["_price"] > 0]
    cv = coefficient_of_variation(prices)
    if not prices:
        return {"dimension": 37, "name": "价格离散度", "type": "data", "data": {"cv": None}}
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    stdev = math.sqrt(variance)
    label = "high" if cv and cv > 50 else "medium" if cv and cv > 20 else "low"
    return {
        "dimension": 37, "name": "价格离散度", "type": "data",
        "data": {"cv": cv, "mean": round(mean, 2), "stdev": round(stdev, 2),
                 "min": min(prices), "max": max(prices), "range": round(max(prices) - min(prices), 2),
                 "label": label},
    }


def calc_sales_dispersion(items):
    units = [x["_units"] for x in items if x["_units"] is not None and x["_units"] > 0]
    cv = coefficient_of_variation(units)
    if not units:
        return {"dimension": 38, "name": "销量离散度", "type": "data", "data": {"cv": None}}
    mean = sum(units) / len(units)
    variance = sum((u - mean) ** 2 for u in units) / len(units)
    stdev = math.sqrt(variance)
    label = "high" if cv and cv > 100 else "medium" if cv and cv > 50 else "low"
    return {
        "dimension": 38, "name": "销量离散度", "type": "data",
        "data": {"cv": cv, "mean": round(mean, 0), "stdev": round(stdev, 0),
                 "min": min(units), "max": max(units), "range": max(units) - min(units),
                 "label": label},
    }


# ── 新品清单（升级版） ─────────────────────────────────────────

def calc_new_product_list(items, limit=50):
    """新品清单：优先 availableDate<6月，回退 ratings<100。"""
    has_keepa = any(x.get("keepa_available") for x in items)
    rows = []
    for x in items:
        if has_keepa:
            age = parse_available_date_to_months(x.get("availableDate"))
            if age is None or age >= 6:
                continue
        else:
            rc = safe_int(x.get("ratings"), None)
            if rc is None or rc >= NEW_PRODUCT_RATINGS_LT:
                continue
        rows.append({
            "organic_rank": x.get("organic_rank"),
            "page": x.get("page"),
            "asin": x.get("asin"),
            "brand": x.get("brand", ""),
            "title": (x.get("title") or "")[:80],
            "price": x["_price"],
            "rating": safe_float(x.get("rating")),
            "ratings": safe_int(x.get("ratings")),
            "units": x["_units"],
            "availableDate": x.get("availableDate", ""),
            "units_imputed": x.get("units_imputed", False),
            "has_variant": bool(x.get("has_variant")),
            "keepa_available": bool(x.get("keepa_available")),
        })
    rows.sort(key=lambda r: r.get("organic_rank") or 10**9)
    rule = "availableDate<6月（Keepa上架时间）" if has_keepa else f"ratings<{NEW_PRODUCT_RATINGS_LT}（代理口径）"
    note = "基于Keepa上架时间" if has_keepa else "无Keepa数据，以低评分数作代理，可能含老品低评论链接"
    return {
        "name": "新品清单",
        "type": "table",
        "data": {"rule": rule, "note": note, "count": len(rows), "items": rows[:limit]},
    }


# ── smart buckets ───────────────────────────────────────────────

def _percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_vals):
        return sorted_vals[f] + c * (sorted_vals[f + 1] - sorted_vals[f])
    return float(sorted_vals[f])


def generate_smart_buckets(items):
    prices = sorted(x["_price"] for x in items if x["_price"] is not None)
    rcounts = sorted(safe_int(x.get("ratings"), 0) or 0 for x in items)
    rvalues = sorted(safe_float(x.get("rating"), 0) or 0 for x in items if x.get("rating") is not None)

    def price_buckets():
        if len(prices) < 4:
            return list(DEFAULT_BUCKETS["price"])
        breaks = [0]
        for p in (20, 40, 60, 80):
            breaks.append(max(0, round(_percentile(prices, p) / 5) * 5))
        breaks.append(None)
        out, prev = [], -1
        for b in breaks:
            if b is None:
                out.append(None)
            elif b > prev:
                out.append(b)
                prev = b
        if len(out) < 3:
            return list(DEFAULT_BUCKETS["price"])
        buckets = []
        for i in range(len(out) - 1):
            lo, hi = out[i], out[i + 1]
            if hi is None:
                buckets.append({"label": f"${int(lo)}+", "min": lo, "max": None})
            else:
                buckets.append({"label": f"${int(lo)}-{int(hi)}", "min": lo, "max": hi})
        return buckets

    return {
        "price": price_buckets(),
        "ratingCount": list(DEFAULT_BUCKETS["ratingCount"]),
        "ratingValue": list(DEFAULT_BUCKETS["ratingValue"]),
    }


# ── 主聚合 ──────────────────────────────────────────────────────

def aggregate(products, buckets=None, use_smart=True):
    ranked, rank_mode = ensure_organic_rank(products)
    items, raw_units_cnt = enrich(ranked)

    # 检测 Keepa 数据
    keepa_count = sum(1 for x in items if x.get("keepa_available"))
    keepa_cov = round(100.0 * keepa_count / len(items), 1) if items else 0
    has_keepa = keepa_count > 0

    # 分桶
    if buckets is not None:
        bucket_mode = "custom"
    elif use_smart:
        buckets = generate_smart_buckets(items)
        bucket_mode = "smart"
    else:
        buckets = {k: list(v) for k, v in DEFAULT_BUCKETS.items()}
        bucket_mode = "fixed"

    if has_keepa:
        all_buckets = {**buckets, **KEEPA_BUCKETS}
    else:
        all_buckets = buckets

    # 基础 6 段（始终执行）
    dims = [
        calc_page_traffic(items),
        calc_rank_concentration(items),
        calc_price_distribution(items, all_buckets["price"]),
        calc_rating_count_distribution(items, all_buckets["ratingCount"]),
        calc_rating_value_distribution(items, all_buckets["ratingValue"]),
        calc_has_variant(items),
    ]

    # Keepa 增强维度
    if has_keepa:
        # A 组：竞争格局 7-15
        dims.extend([
            calc_brand_concentration(items),
            calc_brand_sales_share(items),
            calc_brand_monopoly_cr(items),
            calc_seller_concentration(items),
            calc_fulfillment_distribution(items),
            calc_variation_complexity(items, all_buckets["variationNum"]),
            calc_seller_num_distribution(items, all_buckets["sellerNum"]),
            calc_multi_seller_ratio(items),
            calc_category_distribution(items),
        ])
        # B 组：进入门槛 16-28
        dims.extend([
            calc_review_threshold_top10(items),
            calc_review_median(items),
            calc_new_product_review_growth(items),
            calc_price_threshold(items),
            calc_bsr_threshold_top10(items),
            calc_bsr_median(items),
            calc_profit_distribution(items, all_buckets["profit"]),
            calc_fba_fee_distribution(items, all_buckets["fbaFees"]),
            calc_referral_fee_distribution(items),
            calc_hazmat_ratio(items),
            calc_adult_product_ratio(items),
            calc_listing_age_distribution(items, all_buckets["availableMonths"]),
            calc_new_product_ratio(items),
        ])
        # C 组：趋势与生命周期 29-38
        dims.extend([
            calc_sales_trend(items),
            calc_market_sales_trend(items),
            calc_bsr_trend(items),
            calc_bsr_volatility(items),
            calc_new_product_growth_speed(items),
            calc_lifecycle_stage(items),
            calc_market_maturity(items),
            calc_top_vs_new_sales(items),
            calc_price_dispersion(items),
            calc_sales_dispersion(items),
        ])

    appendix = calc_new_product_list(items)

    total_dims = 38 if has_keepa else 6
    if has_keepa:
        disclaimer = (
            f"样本=默认排序前3页自然结果；organic_rank为按页去广告后连续编号，非官方rank/BSR；"
            f"月销缺失按{MISSING_UNITS_DEFAULT}计；Keepa覆盖率{keepa_cov}%；"
            f"新品清单基于availableDate<6月；BSR/利润/品牌等维度依赖Keepa数据"
        )
    else:
        disclaimer = (
            f"样本=默认排序前3页自然结果；organic_rank为按页去广告后连续编号，非官方rank/BSR；"
            f"月销缺失按{MISSING_UNITS_DEFAULT}计；Keepa数据不可用，仅执行基础6段分析；"
            f"新品清单为ratings<{NEW_PRODUCT_RATINGS_LT}代理"
        )

    return {
        "meta": {
            "totalProducts": len(items),
            "rawUnitsCoverage": round(100.0 * raw_units_cnt / len(items), 1) if items else 0,
            "rawUnitsCount": raw_units_cnt,
            "imputedUnitsCount": len(items) - raw_units_cnt,
            "missingUnitsDefault": MISSING_UNITS_DEFAULT,
            "rankMode": rank_mode,
            "aggregatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dimensions": total_dims,
            "keepaAvailable": has_keepa,
            "keepaCoverage": keepa_cov,
            "keepaSuccessCount": keepa_count,
            "bucketMode": bucket_mode,
            "disclaimer": disclaimer,
        },
        "bucketDefs": all_buckets,
        "dimensions": dims,
        "appendix": appendix,
    }


def summarize(result):
    print(f"Top-level keys: {list(result.keys())}")
    meta = result.get("meta", {})
    for k, v in meta.items():
        print(f"  {k}: {v}")
    dims = result.get("dimensions", [])
    print(f"\nDimensions: {len(dims)}")
    for d in dims:
        print(f"  [{d.get('dimension')}] {d.get('name')} ({d.get('type')})")
    ap = result.get("appendix", {})
    print(f"\nAppendix: {ap.get('name')} count={ap.get('data', {}).get('count')}")

    if len(dims) > 6:
        print(f"\n--- 竞争格局 (1-15) ---")
        for d in dims[:15]:
            print(f"  [{d['dimension']}] {d['name']}")
        print(f"\n--- 进入门槛 (16-28) ---")
        for d in dims[15:28]:
            print(f"  [{d['dimension']}] {d['name']}")
        print(f"\n--- 趋势与生命周期 (29-38) ---")
        for d in dims[28:]:
            print(f"  [{d['dimension']}] {d['name']}")


def main():
    argv = sys.argv[1:]
    inline = "--inline" in argv
    argv = [a for a in argv if a != "--inline"]
    fixed_buckets = "--fixed-buckets" in argv
    argv = [a for a in argv if a != "--fixed-buckets"]

    buckets_arg = None
    remaining = []
    i = 0
    while i < len(argv):
        if argv[i] == "--buckets" and i + 1 < len(argv):
            buckets_arg = argv[i + 1]
            i += 2
        else:
            remaining.append(argv[i])
            i += 1
    argv = remaining

    if not argv:
        print(
            f"Usage: {os.path.basename(__file__)} <merged_products.json> "
            f"[--inline] [--fixed-buckets] [--buckets <file.json|json_string>]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = argv[0]
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    products = load_products(input_path)
    if not products:
        print("No products found in input file", file=sys.stderr)
        sys.exit(1)

    if buckets_arg:
        result = aggregate(products, buckets=load_buckets(buckets_arg))
    elif fixed_buckets:
        result = aggregate(products, use_smart=False)
    else:
        result = aggregate(products, use_smart=True)

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    ts = int(time.time())
    out_path = resolve_data_path(SLUG, ts)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(serialized)
        print(f"Saved full response: {out_path} ({len(serialized)} bytes)")
    except OSError as e:
        print(f"Failed to save to {out_path}: {e}", file=sys.stderr)

    if inline or len(serialized.encode("utf-8")) <= SMALL_THRESHOLD:
        print(serialized)
    else:
        summarize(result)


if __name__ == "__main__":
    main()
