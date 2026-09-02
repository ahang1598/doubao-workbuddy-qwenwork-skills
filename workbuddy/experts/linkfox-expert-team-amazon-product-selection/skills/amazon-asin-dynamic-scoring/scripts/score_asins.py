#!/usr/bin/env python3
"""
amazon-asin-dynamic-scoring 自动化评分脚本

仅使用卖家精灵「选产品」真实字段，按客户期望动态计算：
- 低竞争 / 上升生命周期 / 利润健康 / 准入门槛 四维度得分
- 加权总分
- 一票否决
- 推荐等级

用法示例：
  python score_asins.py --demo
  python score_asins.py --expectations expectations.json --data asins.json
  python score_asins.py --expectations expectations.json --data asins.csv --output result.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ImportError:
    print("需要 pandas: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(1)


DEFAULT_EXPECTATIONS = {
    "risk_preference": "稳健",
    "price_min": 20.0,
    "price_max": 50.0,
    "min_profit_rate": 30.0,
    "max_ratings": 1500,
    "min_units_growth": 10.0,
    "listing_age_preference": "近3个月",
    "accept_amazon_fulfilled": False,
    "weights": {
        "low_competition": 30,
        "rising_lifecycle": 30,
        "profit_health": 25,
        "low_entry_barrier": 15,
    },
}


# ── 画像 → 期望映射 ──

PROFILE_DEFAULTS = {
    "seller_type": "贸易型",      # 工厂型 / 贸易型 / 个人卖家
    "budget": "5-20万",           # <5万 / 5-20万 / 20万+
    "logistics": "FBA",           # FBA / FBM / 混合
    "business_preference": "中等利润",  # 走量薄利 / 中等利润 / 高利润小众
    "risk_preference": "稳健",    # 保守 / 稳健 / 激进
}


def profile_to_expectations(profile: dict[str, Any]) -> dict[str, Any]:
    """将用户画像映射为评分期望参数。

    画像维度:
      seller_type: 工厂型 / 贸易型 / 个人卖家
      budget: <5万 / 5-20万 / 20万+
      logistics: FBA / FBM / 混合
      business_preference: 走量薄利 / 中等利润 / 高利润小众
      risk_preference: 保守 / 稳健 / 激进

    权重调整采用「转移制」：每个画像维度从源权重转 N 点到目标权重，
    总和恒等于 100，不做比例缩放，保留用户意图。
    """
    p = {**PROFILE_DEFAULTS, **profile}
    w = {
        "low_competition": 30,
        "rising_lifecycle": 30,
        "profit_health": 25,
        "low_entry_barrier": 15,
    }

    def transfer(weights: dict, src: str, dst: str, points: int):
        """从 src 转 points 点到 dst，clamp 防止负值。"""
        actual = min(points, weights[src] - 5)  # 源最少保留 5
        weights[src] -= actual
        weights[dst] += actual

    # ── 卖家类型 → 权重转移 ──
    st = p["seller_type"]
    if st == "工厂型":
        transfer(w, "low_entry_barrier", "profit_health", 5)    # 门槛→利润
    elif st == "贸易型":
        transfer(w, "low_competition", "low_entry_barrier", 5)  # 竞争→门槛
    elif st == "个人卖家":
        transfer(w, "profit_health", "low_competition", 5)      # 利润→竞争

    # ── 资金规模 → 价格带 + 评分数上限 + 权重转移 ──
    budget = p["budget"]
    if budget == "<5万":
        exp_price_min, exp_price_max, exp_max_ratings = 15.0, 35.0, 1000
    elif budget == "5-20万":
        exp_price_min, exp_price_max, exp_max_ratings = 20.0, 50.0, 1500
    elif budget == "20万+":
        exp_price_min, exp_price_max, exp_max_ratings = 30.0, 80.0, 2000
        transfer(w, "rising_lifecycle", "low_competition", 5)   # 生命周期→竞争
    else:
        exp_price_min, exp_price_max, exp_max_ratings = 20.0, 50.0, 1500

    # ── 物流模式 → 自营容忍 ──
    accept_amz = p["logistics"] in ("FBM", "混合")

    # ── 经营偏好 → 毛利率门槛 + 价格带偏移 + 权重转移 ──
    bp = p["business_preference"]
    if bp == "走量薄利":
        min_profit = 20.0
        transfer(w, "low_entry_barrier", "rising_lifecycle", 5)  # 门槛→生命周期
    elif bp == "高利润小众":
        min_profit = 40.0
        exp_price_min += 5  # 价格带整体上移
        transfer(w, "rising_lifecycle", "low_competition", 5)    # 生命周期→竞争
    else:
        min_profit = 30.0

    exp = {
        "risk_preference": p["risk_preference"],
        "price_min": exp_price_min,
        "price_max": exp_price_max,
        "min_profit_rate": min_profit,
        "max_ratings": exp_max_ratings,
        "min_units_growth": 10.0,
        "listing_age_preference": "近3个月",
        "accept_amazon_fulfilled": accept_amz,
        "weights": w,
    }
    return exp


def normalize_expectations(raw: dict[str, Any]) -> dict[str, Any]:
    exp = {**DEFAULT_EXPECTATIONS, **{k: v for k, v in raw.items() if k != "weights"}}
    if "weights" in raw:
        exp["weights"] = {**DEFAULT_EXPECTATIONS["weights"], **raw["weights"]}
    w = exp["weights"]
    total = sum(w.values())
    if abs(total - 100) > 0.01:
        raise ValueError(f"权重总和必须为 100，当前为 {total}")
    exp["weight_frac"] = {k: v / 100.0 for k, v in w.items()}
    pref = exp.get("listing_age_preference", "近3个月")
    if pref == "近3个月":
        exp["max_listing_days"] = 90
    elif pref == "近6个月":
        exp["max_listing_days"] = 180
    elif pref == "近12个月":
        exp["max_listing_days"] = 365
    else:
        exp["max_listing_days"] = 99999

    # ── risk_preference 动态调节否决阈值 ──
    risk = exp.get("risk_preference", "稳健")
    if risk == "保守":
        exp["max_ratings"] = int(exp["max_ratings"] * 0.8)
        exp["min_units_growth"] = exp["min_units_growth"] + 5.0
        price_spread = exp["price_max"] - exp["price_min"]
        exp["price_min"] = round(exp["price_min"] + price_spread * 0.1, 2)
        exp["price_max"] = round(exp["price_max"] - price_spread * 0.1, 2)
    elif risk == "激进":
        exp["max_ratings"] = int(exp["max_ratings"] * 1.2)
        exp["min_units_growth"] = max(0.0, exp["min_units_growth"] - 5.0)
        price_spread = exp["price_max"] - exp["price_min"]
        exp["price_min"] = round(max(1.0, exp["price_min"] - price_spread * 0.1), 2)
        exp["price_max"] = round(exp["price_max"] + price_spread * 0.1, 2)

    return exp


COLUMN_ALIASES = {
    "asin": ["asin", "ASIN"],
    "title": ["title", "标题", "商品标题"],
    "brand": ["brand", "品牌"],
    "price": ["price", "价格"],
    "units": ["units", "月销量", "销量", "monthlySalesUnits"],
    "unitsGr": ["unitsGr", "unitsCr", "units_gr", "销量增长率", "月销量增长率", "monthlySalesUnitsGrowthRate"],
    "revenue": ["revenue", "销售额", "月销售额", "monthlySalesRevenue"],
    "bsr": ["bsr", "BSR"],
    "rating": ["rating", "评分", "星级"],
    "ratings": ["ratings", "评分数", "评论数"],
    "ratingsCv": ["ratingsCv", "ratings_cv", "月评新增", "ratingsRate", "ratings_rate", "留评率"],
    "availableDate": ["availableDate", "available_date", "上架时间", "上架日期", "availableDateString"],
    "fulfillment": ["fulfillment", "配送方式", "配送"],
    "profit": ["profit", "毛利率", "预估毛利率"],
    "fba": ["fba", "FBA", "FBA费用", "FBA运费"],
    "sellers": ["sellers", "卖家数", "sellerNum", "seller_num"],
    "badge_newRelease": ["badge_newRelease", "newRelease", "New Release", "新品标识", "badgeNewRelease"],
    "nodeLabelPath": ["nodeLabelPath", "类目", "类目路径"],
}


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    lower_cols = {str(c).lower().strip(): c for c in df.columns}
    for std, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in lower_cols:
                col_map[lower_cols[alias.lower()]] = std
                break
    return df.rename(columns=col_map)


def parse_date(val) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def score_low_competition(row: pd.Series, rank: int) -> float:
    ratings = float(row.get("ratings") or 99999)
    sellers = float(row.get("sellers") or 99)
    if ratings <= 300:
        base = 10
    elif ratings <= 800:
        base = 8
    elif ratings <= 1500:
        base = 5
    elif ratings <= 3000:
        base = 2
    else:
        base = 0
    bonus = 0
    if sellers <= 3:
        bonus += 2
    if rank <= 10:
        bonus += 1
    return min(10.0, base + bonus)


def score_rising_lifecycle(row: pd.Series, in_window: bool) -> float:
    growth = float(row.get("unitsGr") or -999)
    if growth >= 50:
        base = 10
    elif growth >= 30:
        base = 9
    elif growth >= 15:
        base = 7
    elif growth >= 5:
        base = 5
    else:
        base = 2
    bonus = 2 if in_window else 0
    return min(10.0, base + bonus)


def score_profit_health(row: pd.Series, exp: dict, price_match: bool, profit_ok: bool) -> float:
    if not profit_ok:
        return 0.0
    score = 8.0 if price_match else 3.0
    profit = float(row.get("profit") or 0)
    if profit >= exp["min_profit_rate"] + 10:
        score += 2
    elif profit >= exp["min_profit_rate"]:
        score += 1
    return min(10.0, score)


def score_low_entry_barrier(row: pd.Series, in_window: bool) -> float:
    ratings = float(row.get("ratings") or 99999)
    if ratings <= 500:
        base = 10
    elif ratings <= 1000:
        base = 7
    elif ratings <= 2000:
        base = 4
    else:
        base = 1
    bonus = 0
    if in_window:
        bonus += 2
    nr = str(row.get("badge_newRelease") or "").strip().upper()
    if nr in ("Y", "YES", "TRUE", "1"):
        bonus += 1
    return min(10.0, base + bonus)


def evaluate_row(row: pd.Series, exp: dict, rank: int, today: date) -> dict[str, Any]:
    avail = parse_date(row.get("availableDate"))
    listing_days = (today - avail).days if avail else 99999
    in_window = listing_days <= exp["max_listing_days"]
    price = float(row.get("price") or 0)
    price_match = exp["price_min"] <= price <= exp["price_max"]
    profit = float(row.get("profit") or 0)
    profit_ok = profit >= exp["min_profit_rate"]
    ratings = float(row.get("ratings") or 0)
    ratings_over = ratings > exp["max_ratings"]
    growth = float(row.get("unitsGr") or -999)
    growth_ok = growth >= exp["min_units_growth"]
    is_amz = str(row.get("fulfillment") or "").strip().upper() in ("AMZ", "AMAZON")

    s_comp = score_low_competition(row, rank)
    s_life = score_rising_lifecycle(row, in_window)
    s_profit = score_profit_health(row, exp, price_match, profit_ok)
    s_entry = score_low_entry_barrier(row, in_window)

    wf = exp["weight_frac"]
    total = (
        s_comp * wf["low_competition"]
        + s_life * wf["rising_lifecycle"]
        + s_profit * wf["profit_health"]
        + s_entry * wf["low_entry_barrier"]
    )

    veto_reasons = []
    if ratings_over:
        veto_reasons.append("评分数超限")
    if not growth_ok:
        veto_reasons.append("增长率不达标")
    if not profit_ok:
        veto_reasons.append("毛利率不足")
    if not price_match:
        veto_reasons.append("价格不在期望带")
    if is_amz and not exp["accept_amazon_fulfilled"]:
        veto_reasons.append("自营不接受")

    is_veto = len(veto_reasons) > 0
    if is_veto:
        grade = "淘汰"
        reason = "触发否决：" + " / ".join(veto_reasons)
    else:
        if total >= 8.0:
            grade = "S"
        elif total >= 7.0:
            grade = "A"
        elif total >= 6.0:
            grade = "B"
        elif total >= 5.0:
            grade = "C"
        else:
            grade = "淘汰"
        reason = "推荐：竞争/增长/利润/门槛综合达标" if grade in ("S", "A", "B") else "分数偏低"

    return {
        "asin": row.get("asin"),
        "title": row.get("title"),
        "brand": row.get("brand"),
        "price": price,
        "units": row.get("units"),
        "unitsGr": growth,
        "ratings": ratings,
        "profit": profit,
        "fulfillment": row.get("fulfillment"),
        "listing_days": listing_days,
        "in_window": in_window,
        "rank_in_pool": rank,
        "score_low_competition": round(s_comp, 2),
        "score_rising_lifecycle": round(s_life, 2),
        "score_profit_health": round(s_profit, 2),
        "score_low_entry_barrier": round(s_entry, 2),
        "total_score": round(total, 2),
        "veto": "否决" if is_veto else "通过",
        "grade": grade,
        "reason": reason,
    }


def load_data(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        df = pd.DataFrame(data)
    else:
        raise ValueError(f"不支持的文件格式: {path.suffix}")
    return standardize_columns(df)


def run_scoring(expectations: dict, df: pd.DataFrame) -> pd.DataFrame:
    exp = normalize_expectations(expectations)
    today = date.today()
    df = df[df["asin"].notna() & (df["asin"].astype(str).str.strip() != "")].copy()
    if df.empty:
        raise ValueError("没有有效的 ASIN 数据")
    df["_rank"] = df["units"].rank(method="min", ascending=False).astype(int)
    results = [evaluate_row(row, exp, int(row["_rank"]), today) for _, row in df.iterrows()]
    result_df = pd.DataFrame(results)
    result_df["_sort"] = result_df.apply(
        lambda r: (0 if r["veto"] == "通过" else 1, -r["total_score"]), axis=1
    )
    result_df = result_df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    return result_df


def print_summary(result_df: pd.DataFrame) -> None:
    total = len(result_df)
    passed = (result_df["veto"] == "通过").sum()
    print(f"\n===== 评分结果摘要 =====")
    print(f"总 ASIN 数 : {total}")
    print(f"通过       : {passed}")
    print(f"一票否决   : {total - passed}")
    print(f"\n推荐等级分布:")
    print(result_df["grade"].value_counts().to_string())
    print(f"\n----- 推荐清单（通过且总分≥6）-----")
    rec = result_df[(result_df["veto"] == "通过") & (result_df["total_score"] >= 6)]
    if rec.empty:
        print("无符合条件的产品")
    else:
        cols = ["asin", "title", "total_score", "grade", "score_low_competition",
                "score_rising_lifecycle", "score_profit_health", "score_low_entry_barrier", "reason"]
        print(rec[cols].to_string(index=False))


def save_excel(result_df: pd.DataFrame, expectations: dict, output_path: str) -> None:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        exp_rows = [
            ["风险偏好", expectations.get("risk_preference")],
            ["价格下限", expectations.get("price_min")],
            ["价格上限", expectations.get("price_max")],
            ["最低毛利率(%)", expectations.get("min_profit_rate")],
            ["最高评分数", expectations.get("max_ratings")],
            ["最低增长率(%)", expectations.get("min_units_growth")],
            ["上架时间偏好", expectations.get("listing_age_preference")],
            ["接受自营", "是" if expectations.get("accept_amazon_fulfilled") else "否"],
            ["低竞争权重", expectations.get("weights", {}).get("low_competition")],
            ["生命周期权重", expectations.get("weights", {}).get("rising_lifecycle")],
            ["利润健康权重", expectations.get("weights", {}).get("profit_health")],
            ["准入门槛权重", expectations.get("weights", {}).get("low_entry_barrier")],
        ]
        pd.DataFrame(exp_rows, columns=["配置项", "值"]).to_excel(writer, sheet_name="客户期望", index=False)
        result_df.to_excel(writer, sheet_name="评分结果", index=False)
        rec = result_df[(result_df["veto"] == "通过") & (result_df["total_score"] >= 6)]
        rec.to_excel(writer, sheet_name="推荐清单", index=False)
    print(f"\n结果已保存: {output_path}")


DEMO_EXPECTATIONS = {
    "risk_preference": "稳健",
    "price_min": 20,
    "price_max": 50,
    "min_profit_rate": 30,
    "max_ratings": 1500,
    "min_units_growth": 10,
    "listing_age_preference": "近3个月",
    "accept_amazon_fulfilled": False,
    "weights": {
        "low_competition": 30,
        "rising_lifecycle": 30,
        "profit_health": 25,
        "low_entry_barrier": 15,
    },
}

DEMO_ASINS = [
    {"asin": "B0SAMPLE001", "title": "Wireless Earbuds Pro Noise Cancelling", "brand": "TechSound", "price": 39.99, "units": 1250, "unitsGr": 28.5, "revenue": 49987.5, "bsr": 1520, "rating": 4.3, "ratings": 680, "ratingsCv": 45, "availableDate": "2025-11-15", "fulfillment": "FBA", "profit": 42.5, "fba": 5.8, "sellers": 2, "badge_newRelease": "Y", "nodeLabelPath": "Electronics:Headphones"},
    {"asin": "B0SAMPLE002", "title": "USB-C Fast Charging Cable 3-Pack", "brand": "CableKing", "price": 12.99, "units": 8900, "unitsGr": 5.2, "revenue": 115611, "bsr": 320, "rating": 4.6, "ratings": 15200, "ratingsCv": 320, "availableDate": "2023-03-10", "fulfillment": "FBA", "profit": 55.0, "fba": 3.2, "sellers": 8, "badge_newRelease": "N", "nodeLabelPath": "Electronics:Cables"},
    {"asin": "B0SAMPLE003", "title": "Portable Blender for Smoothies", "brand": "BlendGo", "price": 29.99, "units": 2100, "unitsGr": 45.0, "revenue": 62979, "bsr": 890, "rating": 4.1, "ratings": 320, "ratingsCv": 28, "availableDate": "2026-02-20", "fulfillment": "FBA", "profit": 38.0, "fba": 6.5, "sellers": 1, "badge_newRelease": "Y", "nodeLabelPath": "Home:Kitchen"},
    {"asin": "B0SAMPLE004", "title": "Ergonomic Office Chair Lumbar Support", "brand": "SitWell", "price": 189.0, "units": 450, "unitsGr": -8.5, "revenue": 85050, "bsr": 5600, "rating": 4.4, "ratings": 2800, "ratingsCv": 15, "availableDate": "2024-06-01", "fulfillment": "AMZ", "profit": 28.0, "fba": 28.0, "sellers": 1, "badge_newRelease": "N", "nodeLabelPath": "Furniture:Office Chairs"},
    {"asin": "B0SAMPLE005", "title": "LED Desk Lamp with Wireless Charger", "brand": "LightPlus", "price": 45.5, "units": 980, "unitsGr": 18.0, "revenue": 44590, "bsr": 2100, "rating": 4.5, "ratings": 950, "ratingsCv": 60, "availableDate": "2025-08-05", "fulfillment": "FBA", "profit": 48.0, "fba": 7.1, "sellers": 3, "badge_newRelease": "N", "nodeLabelPath": "Home:Lighting"},
]


def main():
    parser = argparse.ArgumentParser(description="客户期望驱动的 ASIN 动态评分脚本")
    parser.add_argument("--expectations", "-e", help="期望配置 JSON 文件路径")
    parser.add_argument("--data", "-d", help="ASIN 数据文件（xlsx/csv/json）")
    parser.add_argument("--output", "-o", help="输出 Excel 路径（可选）")
    parser.add_argument("--demo", action="store_true", help="使用内置示例数据快速测试")
    parser.add_argument("--profile", help="用户画像 JSON 文件路径（自动生成期望参数）")
    parser.add_argument("--json-out", help="同时输出 JSON 结果文件")
    args = parser.parse_args()

    if args.demo:
        expectations = DEMO_EXPECTATIONS
        df = pd.DataFrame(DEMO_ASINS)
        print("【Demo 模式】使用内置示例期望值与 5 条 ASIN 数据")
    elif args.profile:
        if not args.data:
            parser.error("使用 --profile 时必须同时提供 --data")
        with open(args.profile, encoding="utf-8") as f:
            profile = json.load(f)
        expectations = profile_to_expectations(profile)
        print(f"【画像模式】画像: {json.dumps(profile, ensure_ascii=False)}")
        print(f"  → 生成期望: {json.dumps(expectations, ensure_ascii=False)}")
        df = load_data(args.data)
    else:
        if not args.expectations or not args.data:
            parser.error("请提供 --expectations 和 --data，或使用 --profile，或使用 --demo")
        with open(args.expectations, encoding="utf-8") as f:
            expectations = json.load(f)
        df = load_data(args.data)

    try:
        result_df = run_scoring(expectations, df)
    except Exception as e:
        print(f"评分失败: {e}", file=sys.stderr)
        sys.exit(1)

    print_summary(result_df)

    if args.output:
        save_excel(result_df, expectations, args.output)

    if args.json_out:
        result_df.to_json(args.json_out, orient="records", force_ascii=False, indent=2)
        print(f"JSON 已保存: {args.json_out}")

    print("\n===== JSON_RESULT_START =====")
    print(result_df.to_json(orient="records", force_ascii=False))
    print("===== JSON_RESULT_END =====")


if __name__ == "__main__":
    main()
