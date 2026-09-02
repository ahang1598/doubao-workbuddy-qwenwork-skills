#!/usr/bin/env python3
"""Step 4: 净利润核算 — 11项全量成本模型

成本项:
  1. 1688采购成本(USD) = 1688价格(¥) / 汇率
  2. FBA配送费 = fbaFees (Keepa)
  3. 亚马逊佣金 = 售价 × referralFeePercentage / 100
  4. 广告费 = 售价 × nicheTACoS (或回退adTACoS)
  5. COGS = 1688成本 + FBA头程
  6. 退款管理费 = 佣金 × 20%
  7. 弃置费 = disposalFee
  8. 单笔退货亏损 = FBA费 + 退款管理费 + COGS + 弃置费
  9. 每件预期退货损失 = 退货率 × 单笔退货亏损
  10. 月度仓储费 = (L×W×H mm / 28316846.6) × storageRate
  11. 入库配置费 = inboundPlacementFee

净利润 = 售价 - (1+2+3+4+9+10+11+头程)

⚠️ 售价取值规则：
  必须从 --keepa-history-file 的 buyboxPrice 曲线取正常售卖价（非秒杀价）。
  buyboxPrice 曲线中会出现两个价格水平交替，较低的是 Deal/促销价，较高的是正常 Buy Box 价。
  若未传入 --keepa-history-file，回退用 Keepa 商品详情的 price 字段，但会在 stderr 输出警告。

⚠️ 退货率/ACoS 取值规则：
  必须从 --market-metrics-file 的极目 niche 数据中取。
  按 --niche-keyword 指定的 nicheTitle 精确匹配。
  若未匹配到，回退用 --default-return-rate / --ad-tacos，但会在 stderr 输出警告。
"""
import argparse
import json
import os
import sys
import math
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from linkfox_paths import resolve_data_path
except ImportError:
    resolve_data_path = None


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_keepa(data_list):
    result = {}
    for data in data_list:
        if data.get("errcode") != 200:
            continue
        for p in data.get("products", []):
            result[p["asin"]] = p
    return result


def extract_1688(data_list, asin_order=None):
    """从 1688 搜索结果 JSON 列表提取货源商品。

    兼容 B1 (linkfox-dld-product-search) 和 B2 (linkfox-1688-search-by-image) 两种格式：
    - B1 返回 {"products": [...]}，字段含 offerId/title/price/salesQuantity 等
    - B2 返回 {"products": [...]}，字段含 offerId/title/price/monthSold 等

    Args:
        data_list: JSON 文件加载后的 dict 列表
        asin_order: 可选，ASIN 列表用于按 ASIN 分组（兼容旧逻辑）
                    若为 None，所有商品合并到一个列表中
    Returns:
        若 asin_order 提供: {asin: [all_products]} 字典（按销量降序）
        若 asin_order 为 None: {"_all": [all_products]} 字典（按销量降序）
    """
    result = {}
    all_products = []

    for i, data in enumerate(data_list):
        # 兼容两种返回格式：B1 的 {"products": [...]} 和 B2 的 {"products": [...]}
        products = data.get("products", []) if isinstance(data, dict) else []

        for p in products:
            # 标准化销量字段：B1 用 salesQuantity，B2 可能用 monthSold
            sales = p.get("salesQuantity") or p.get("monthSold") or 0
            p["_salesQuantity"] = sales
            # 标准化价格字段：B1 用 price，B2 可能用 price
            p["_price"] = p.get("price", 0) or 0
            all_products.append(p)

        if asin_order and i < len(asin_order):
            asin = asin_order[i]
            products_sorted = sorted(products,
                                     key=lambda x: x.get("_salesQuantity", 0),
                                     reverse=True)
            result[asin] = products_sorted

    if not asin_order:
        # 所有商品合并，按销量降序排列（不截断）
        all_products.sort(key=lambda x: x.get("_salesQuantity", 0), reverse=True)
        result["_all"] = all_products

    return result


def get_normal_price_from_history(keepa_history, asin):
    """从 Keepa 历史时序数据的 buyboxPrice 曲线取正常售卖价（非秒杀价）。

    buyboxPrice 曲线中可能出现两个价格水平交替（如 $44.99↔$49.99），
    较低的是 Deal/促销价，较高的是正常 Buy Box 价。取较高的那个。
    若曲线只有一个价格水平，直接取该值。

    支持多种数据格式：
    - dict 格式: {"asin": "...", "buyboxPrice": [{"value": 49.99}, ...]}
    - dict 格式: {"asin": "...", "buyboxPrice": [[timestamp, value], ...]}
    - list 格式: [{"asin": "...", "buyboxPrice": [...]}]
    """
    if not keepa_history:
        return None

    # 找到目标 ASIN 的历史数据
    hist = None
    if isinstance(keepa_history, dict):
        hist = keepa_history
    elif isinstance(keepa_history, list):
        for item in keepa_history:
            if isinstance(item, dict) and item.get("asin") == asin:
                hist = item
                break
        if not hist and keepa_history:
            hist = keepa_history[0]  # 回退取第一个

    if not hist or not isinstance(hist, dict):
        return None

    bbp = hist.get("buyboxPrice", [])
    if not bbp or not isinstance(bbp, list):
        return None

    # 解析价格列表，兼容两种格式：
    # 1. [{"value": 49.99}, {"value": 44.99}, ...]
    # 2. [[timestamp, value], [timestamp, value], ...]
    prices = []
    for entry in bbp:
        if isinstance(entry, dict):
            val = entry.get("value")
            if val is not None and isinstance(val, (int, float)) and val > 0:
                prices.append(float(val))
        elif isinstance(entry, list) and len(entry) >= 2:
            val = entry[1]
            if val is not None and isinstance(val, (int, float)) and val > 0:
                prices.append(float(val))

    if not prices:
        return None

    # 统计每个价格水平的出现频率
    from collections import Counter
    price_counts = Counter(round(p, 2) for p in prices)
    unique_prices = sorted(price_counts.keys())

    if len(unique_prices) == 1:
        print(f"  [售价校验] buyboxPrice 曲线只有 1 个价格水平: ${unique_prices[0]}", file=sys.stderr)
        return unique_prices[0]

    # 多个价格水平：取频率最高的 2 个，取较高的那个作为正常售价
    # （正常售价出现频率通常高于秒杀价，但取较高的确保不被秒杀价拉低）
    top2 = [p for p, _ in price_counts.most_common(2)]
    normal_price = max(top2)
    deal_price = min(top2)
    print(f"  [售价校验] buyboxPrice 曲线有 {len(unique_prices)} 个价格水平: "
          f"正常售卖价=${normal_price} (出现{price_counts[normal_price]}次), "
          f"秒杀价=${deal_price} (出现{price_counts[deal_price]}次)", file=sys.stderr)
    return normal_price


def build_metrics_map(metrics_data, niche_keyword=None):
    """从极目 niche 数据构建 nicheTitle -> {returnRate, acos, nicheTACoS} 映射。

    支持两种数据格式：
    1. S2-B 极目 niche 数据: {"verified": [...], "unverified": [...]}
    2. 直接的 niche 列表: [{"nicheTitle": "...", "returnRateAnnual": ...}, ...]

    若传入 niche_keyword，优先匹配该 niche，返回该 niche 的指标。
    """
    if not metrics_data:
        return {}, {}

    rate_map = {}
    tacos_map = {}

    # 提取 niche 列表
    items = []
    if isinstance(metrics_data, list):
        items = metrics_data
    elif isinstance(metrics_data, dict):
        if "verified" in metrics_data:
            items = metrics_data["verified"] + metrics_data.get("unverified", [])
        elif "data" in metrics_data:
            items = metrics_data["data"]
        else:
            items = [metrics_data]

    for item in items:
        title = item.get("nicheTitle", item.get("category", ""))
        if not title:
            continue

        rate = item.get("returnRateAnnual", None)
        if rate is not None and isinstance(rate, (int, float)):
            rate_map[title] = rate * 100  # 转为百分比

        acos = item.get("acos", None)
        if acos is not None and isinstance(acos, (int, float)):
            # 极目 API 返回的 acos 可能是小数（0-1）或百分比格式
            # acos > 1 → 已是百分比（如 11.39 表示 11.39%），直接用
            # acos ≤ 1 → 小数格式（如 0.131653 表示 13.17%），需 × 100
            if acos > 1:
                tacos_map[title] = acos
            else:
                tacos_map[title] = acos * 100

    return rate_map, tacos_map


def find_best_niche_match(rate_map, tacos_map, niche_keyword, category):
    """按优先级匹配 niche 指标。

    1. 精确匹配 niche_keyword
    2. 包含匹配 niche_keyword
    3. 按 category 匹配
    4. 回退默认值
    """
    if niche_keyword:
        # 精确匹配
        if niche_keyword in rate_map:
            rate = rate_map[niche_keyword]
            tacos = tacos_map.get(niche_keyword)
            print(f"  [退货率] 来源: 极目 niche '{niche_keyword}' 精确匹配 → {rate:.2f}%", file=sys.stderr)
            if tacos is not None:
                print(f"  [ACoS] 来源: 极目 niche '{niche_keyword}' 精确匹配 → {tacos:.2f}%", file=sys.stderr)
            return rate, tacos

        # 包含匹配
        for title, rate in rate_map.items():
            if niche_keyword.lower() in title.lower() or title.lower() in niche_keyword.lower():
                tacos = tacos_map.get(title)
                print(f"  [退货率] 来源: 极目 niche '{title}' 包含匹配 → {rate:.2f}%", file=sys.stderr)
                if tacos is not None:
                    print(f"  [ACoS] 来源: 极目 niche '{title}' 包含匹配 → {tacos:.2f}%", file=sys.stderr)
                return rate, tacos

    # 按 category 匹配
    if category and category in rate_map:
        rate = rate_map[category]
        tacos = tacos_map.get(category)
        print(f"  [退货率] 来源: 极目 category '{category}' 匹配 → {rate:.2f}%", file=sys.stderr)
        if tacos is not None:
            print(f"  [ACoS] 来源: 极目 category '{category}' 匹配 → {tacos:.2f}%", file=sys.stderr)
        return rate, tacos

    return None, None


def calc_storage_fee(pkg_length_mm, pkg_width_mm, pkg_height_mm, storage_rate):
    """计算月度仓储费: mm³ → 立方英尺 × 费率"""
    if not pkg_length_mm or not pkg_width_mm or not pkg_height_mm:
        return 0.0
    # 1 cubic foot = 28316846.6 mm³
    cubic_feet = (pkg_length_mm * pkg_width_mm * pkg_height_mm) / 28316846.6
    return cubic_feet * storage_rate


def determine_fba_size_tier(pkg_weight_g, pkg_l_mm, pkg_w_mm, pkg_h_mm):
    """根据 Keepa 包装尺寸/重量判断亚马逊 FBA 尺寸分段。

    返回: (size_tier_name, disposal_fee, storage_rate_jan_sep, storage_rate_oct_dec, inbound_placement_fee)

    尺寸分段判断逻辑（美国站 2026 费率）：
    - 标准尺寸: 重量 ≤ 16oz(454g) 且 体积 ≤ 225 in³
    - 小号大件: 重量 ≤ 130oz(3685g)
    - 中号大件: 重量 ≤ 150oz(4252g)
    - 大号大件: 重量 > 150oz(4252g)
    """
    # 默认值（无法判断尺寸时回退）
    DEFAULT = ("未知", 0.50, 0.87, 2.40, 0.30)

    if not pkg_weight_g or not pkg_l_mm or not pkg_w_mm or not pkg_h_mm:
        print(f"  [⚠️ 警告] Keepa 包装尺寸/重量缺失，FBA 费率使用回退默认值", file=sys.stderr)
        return DEFAULT

    # 计算体积（立方英寸）
    # mm³ → in³: 1 in = 25.4mm, 1 in³ = 16387.064 mm³
    volume_in3 = (pkg_l_mm * pkg_w_mm * pkg_h_mm) / 16387.064

    weight_oz = pkg_weight_g / 28.35  # g → oz

    if weight_oz <= 16 and volume_in3 <= 225:
        tier = ("标准尺寸", 0.50, 0.87, 2.40, 0.30)
    elif weight_oz <= 130:
        tier = ("小号大件", 1.00, 0.56, 1.40, 0.40)
    elif weight_oz <= 150:
        tier = ("中号大件", 2.00, 0.56, 1.40, 0.40)
    else:
        tier = ("大号大件", 3.00, 0.56, 1.40, 0.50)

    tier_name, disposal, sr_jan_sep, sr_oct_dec, inbound = tier
    print(f"  [FBA费率] 尺寸分段: {tier_name} "
          f"(重量={weight_oz:.1f}oz, 体积={volume_in3:.1f}in³) → "
          f"弃置费=${disposal}, 仓储费率=${sr_jan_sep}/cu ft(1-9月), "
          f"入库配置费=${inbound}", file=sys.stderr)
    return tier


def calc_profit(keepa_prod, products_1688, exchange_rate, fba_head_cost,
                ad_tacos, return_rate_pct, niche_tacos_pct=None, override_price=None,
                zero_ad=False, return_rate_matched=False):
    # 售价：优先用 override_price（从 Keepa 历史曲线取的正常售卖价）
    price = override_price if override_price is not None else (keepa_prod.get("price", 0) or 0)
    fba_fees = keepa_prod.get("fbaFees", 0) or 0
    referral_pct = keepa_prod.get("referralFeePercentage", 0) or 0
    referral_fee = price * referral_pct / 100 if referral_pct > 0 else 0

    # 零广告策略判断：zero_ad=True 时广告费=$0
    if zero_ad:
        effective_tacos = 0
        ad_cost = 0
        print(f"  [广告费] $0.00 (零广告策略: sponsoredProductsKeywordCount=0)", file=sys.stderr)
    else:
        effective_tacos = niche_tacos_pct if niche_tacos_pct is not None else ad_tacos
        ad_cost = price * effective_tacos / 100 if effective_tacos > 0 else 0

    refund_admin_fee = referral_fee * 0.20

    # 包装尺寸 (mm) 和重量 (g)
    pkg_l = keepa_prod.get("packageLength", 0) or 0
    pkg_w = keepa_prod.get("packageWidth", 0) or 0
    pkg_h = keepa_prod.get("packageHeight", 0) or 0
    pkg_weight_g = keepa_prod.get("packageWeight", 0) or 0
    # packageWeight 可能是字符串如 "1360 g"，需要提取数字
    if isinstance(pkg_weight_g, str):
        import re
        m = re.search(r'[\d.]+', pkg_weight_g)
        pkg_weight_g = float(m.group()) if m else 0

    # 根据 Keepa 包装尺寸自动查 FBA 费率表（弃置费/仓储费率/入库配置费）
    tier_name, disposal_fee, storage_rate_jan_sep, storage_rate_oct_dec, inbound_placement_fee = \
        determine_fba_size_tier(pkg_weight_g, pkg_l, pkg_w, pkg_h)

    # 根据当前月份选择仓储费率（1-9月 vs 10-12月）
    from datetime import datetime as _dt
    current_month = _dt.now().month
    storage_rate = storage_rate_oct_dec if current_month >= 10 else storage_rate_jan_sep
    print(f"  [仓储费率] 当前月份={current_month}月 → ${storage_rate}/cu ft", file=sys.stderr)

    storage_fee = calc_storage_fee(pkg_l, pkg_w, pkg_h, storage_rate)

    category = keepa_prod.get("categoryTree", "").split(":")[-1] if keepa_prod.get("categoryTree") else "N/A"

    print(f"  [售价] ${price:.2f}" + (f" (Keepa buyboxPrice 正常售卖价)" if override_price else " (Keepa 商品详情 price 字段)"), file=sys.stderr)
    print(f"  [FBA费] ${fba_fees:.2f}", file=sys.stderr)
    print(f"  [佣金] ${referral_fee:.2f} ({referral_pct}%)", file=sys.stderr)
    print(f"  [广告费] ${ad_cost:.2f} (TACoS={effective_tacos:.2f}%)", file=sys.stderr)
    print(f"  [退货率] {return_rate_pct:.2f}%", file=sys.stderr)
    print(f"  [弃置费] ${disposal_fee:.2f} (尺寸分段: {tier_name}, 含在退货损失中，不单独计入总成本)", file=sys.stderr)
    print(f"  [仓储费] ${storage_fee:.2f} ({pkg_l}×{pkg_w}×{pkg_h}mm → {storage_fee:.2f})", file=sys.stderr)
    print(f"  [入库配置费] ${inbound_placement_fee:.2f} (尺寸分段: {tier_name})", file=sys.stderr)

    processed_1688 = []
    for p in products_1688:
        cny_price = p.get("price", 0) or 0
        usd_cost = cny_price / exchange_rate if cny_price > 0 else 0
        cogs = usd_cost + fba_head_cost
        single_return_loss = fba_fees + refund_admin_fee + cogs + disposal_fee
        expected_return_loss = (return_rate_pct / 100) * single_return_loss if return_rate_pct > 0 else 0
        # ⚠️ 总成本不含 disposal_fee（已通过 expected_return_loss 包含）
        total_cost = (usd_cost + fba_fees + referral_fee + ad_cost +
                      expected_return_loss + storage_fee + inbound_placement_fee + fba_head_cost)
        net_profit = price - total_cost
        net_margin = (net_profit / price * 100) if price > 0 else 0
        processed_1688.append({
            "offerId": p.get("offerId", ""),
            "title": p.get("title", ""),
            "price_cny": round(cny_price, 2),
            "price_usd": round(usd_cost, 2),
            "salesQuantity": p.get("salesQuantity", 0),
            "repurchaseRate": p.get("repurchaseRate", "N/A"),
            "ad_cost": round(ad_cost, 2),
            "cogs": round(cogs, 2),
            "refund_admin_fee": round(refund_admin_fee, 2),
            "single_return_loss": round(single_return_loss, 2),
            "expected_return_loss": round(expected_return_loss, 4),
            "storage_fee": round(storage_fee, 2),
            "inbound_placement_fee": round(inbound_placement_fee, 2),
            "total_cost": round(total_cost, 2),
            "net_profit": round(net_profit, 2),
            "net_margin": round(net_margin, 1),
        })

    if processed_1688:
        best = min(processed_1688, key=lambda x: x["price_cny"])
        best_profit = best["net_profit"]
        best_margin = best["net_margin"]
        best_cost = best["price_usd"]
    else:
        best_profit = None
        best_margin = None
        best_cost = None

    return {
        "asin": keepa_prod.get("asin", ""),
        "title": keepa_prod.get("title", ""),
        "brand": keepa_prod.get("brand", ""),
        "category": category,
        "price": price,
        "price_source": "keepa_buybox_normal" if override_price else "keepa_product_detail",
        "bsr": keepa_prod.get("salesRank", 0),
        "rating": keepa_prod.get("rating", 0),
        "fba_fees": fba_fees,
        "referral_fee": round(referral_fee, 2),
        "ad_cost": round(ad_cost, 2),
        "cogs": round((best_cost or 0) + fba_head_cost, 2) if best_cost else None,
        "refund_admin_fee": round(refund_admin_fee, 2),
        "disposal_fee": disposal_fee,
        "single_return_loss": best["single_return_loss"] if processed_1688 else None,
        "expected_return_loss": best["expected_return_loss"] if processed_1688 else None,
        "storage_fee": round(storage_fee, 2),
        "inbound_placement_fee": inbound_placement_fee,
        "fba_head_cost": fba_head_cost,
        "total_cost": best["total_cost"] if processed_1688 else None,
        "net_profit": best_profit,
        "net_margin": best_margin,
        "return_rate_pct": round(return_rate_pct, 2),
        "return_rate_source": "niche_matched" if return_rate_matched else "default",
        "niche_tacos": round(effective_tacos, 2),
        "tacos_source": "niche_matched" if niche_tacos_pct is not None else "default_ad_tacos",
        "cost_1688": best_cost,
        "products_1688": processed_1688,
    }


def main():
    parser = argparse.ArgumentParser(description="Step 4: Net profit calculation with 11 cost items")
    parser.add_argument("--keepa-files", nargs="+", required=True, help="Keepa 商品详情 JSON 文件（S2-A 或 S6.4-A）")
    parser.add_argument("--keepa-history-file", default=None, help="Keepa 历史时序 JSON 文件（S6.1），用于取 buyboxPrice 正常售卖价")
    parser.add_argument("--alibaba-files", nargs="+", required=True, help="1688 货源 JSON 文件（S6.4-B）")
    parser.add_argument("--market-metrics-file", default=None, help="极目 niche 数据 JSON（S2-B），用于取退货率和 ACoS")
    parser.add_argument("--niche-keyword", default=None, help="指定匹配的 niche 关键词（如 'laptop screen extender'）")
    parser.add_argument("--exchange-rate", type=float, default=7.2)
    parser.add_argument("--fba-head-cost", type=float, default=3.0)
    parser.add_argument("--ad-tacos", type=float, default=10.0)
    parser.add_argument("--default-return-rate", type=float, default=15.0)
    parser.add_argument("--sif-summary-file", default=None, help="SIF ASIN 流量概览 JSON，用于零广告策略判断（sponsoredProductsKeywordCount=0 时广告费=$0）")
    # 注意：--disposal-fee / --storage-rate / --inbound-placement-fee 已移除，
    # 这三项由 determine_fba_size_tier() 根据 Keepa 包装尺寸自动查表（references/fba-fee-table.md）
    args = parser.parse_args()

    # 加载 SIF 流量概览，判断零广告策略
    zero_ad_map = {}  # asin -> bool
    if args.sif_summary_file and os.path.isfile(args.sif_summary_file):
        sif_data = load_json(args.sif_summary_file)
        sif_items = sif_data.get("data", []) if isinstance(sif_data, dict) else sif_data
        for item in sif_items:
            asin = item.get("asin", "")
            sp_count = item.get("sponsoredProductsKeywordCount", 0) or 0
            zero_ad_map[asin] = (sp_count == 0)
            if sp_count == 0:
                print(f"[零广告策略] ASIN {asin}: sponsoredProductsKeywordCount=0 → 广告费=$0", file=sys.stderr)
        print(f"[参数来源] SIF 流量概览: {args.sif_summary_file}", file=sys.stderr)
    else:
        print(f"[⚠️ 警告] 未传入 --sif-summary-file，无法判断零广告策略，将始终计算广告费。"
              f"建议传入 SIF 流量概览数据。", file=sys.stderr)

    keepa_data_list = [load_json(f) for f in args.keepa_files]
    keepa_products = extract_keepa(keepa_data_list)
    asin_order = list(keepa_products.keys())

    # 加载 Keepa 历史时序数据
    keepa_history = None
    if args.keepa_history_file and os.path.isfile(args.keepa_history_file):
        keepa_history = load_json(args.keepa_history_file)
        print(f"[参数来源] Keepa 历史时序数据: {args.keepa_history_file}", file=sys.stderr)
    else:
        print(f"[⚠️ 警告] 未传入 --keepa-history-file，售价将从 Keepa 商品详情的 price 字段取值，"
              f"可能命中秒杀/促销价。建议始终传入 --keepa-history-file。", file=sys.stderr)

    # 加载极目 niche 指标
    rate_map, tacos_map = {}, {}
    if args.market_metrics_file and os.path.isfile(args.market_metrics_file):
        metrics_data = load_json(args.market_metrics_file)
        rate_map, tacos_map = build_metrics_map(metrics_data, args.niche_keyword)
        print(f"[参数来源] 极目 niche 数据: {args.market_metrics_file}", file=sys.stderr)
        print(f"  已解析 {len(rate_map)} 个 niche 的退货率, {len(tacos_map)} 个 niche 的 TACoS", file=sys.stderr)
    else:
        print(f"[⚠️ 警告] 未传入 --market-metrics-file，退货率和 ACoS 将使用默认值"
              f"（退货率={args.default_return_rate}%, ACoS={args.ad_tacos}%）。"
              f"建议始终传入极目 niche 数据。", file=sys.stderr)

    alibaba_data_list = [load_json(f) for f in args.alibaba_files]
    products_1688 = extract_1688(alibaba_data_list, asin_order)

    results = []
    for asin in asin_order:
        kp = keepa_products.get(asin, {})
        p1688 = products_1688.get(asin, products_1688.get("_all", []))
        category = kp.get("categoryTree", "").split(":")[-1] if kp.get("categoryTree") else "N/A"

        print(f"\n=== ASIN: {asin} ===", file=sys.stderr)

        # 取正常售卖价
        normal_price = None
        if keepa_history:
            normal_price = get_normal_price_from_history(keepa_history, asin)

        # 匹配极目 niche 指标
        niche_rate, niche_tacos = find_best_niche_match(
            rate_map, tacos_map, args.niche_keyword, category
        )

        # 确定最终参数
        return_rate = niche_rate if niche_rate is not None else args.default_return_rate
        effective_tacos = niche_tacos if niche_tacos is not None else None

        if niche_rate is None:
            print(f"  [⚠️ 警告] 退货率未匹配到极目 niche，使用默认值 {args.default_return_rate}%", file=sys.stderr)
        if niche_tacos is None:
            print(f"  [⚠️ 警告] ACoS 未匹配到极目 niche，使用默认值 {args.ad_tacos}%", file=sys.stderr)

        result = calc_profit(
            kp, p1688, args.exchange_rate, args.fba_head_cost,
            args.ad_tacos, return_rate,
            niche_tacos_pct=effective_tacos, override_price=normal_price,
            zero_ad=zero_ad_map.get(asin, False),
            return_rate_matched=(niche_rate is not None)
        )
        results.append(result)

    results.sort(key=lambda x: x.get("net_margin") or -999, reverse=True)

    output_json = json.dumps(results, ensure_ascii=False, indent=2)
    print(output_json)

    if resolve_data_path:
        try:
            data_path = resolve_data_path("profit-analysis", time.time())
            with open(data_path, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"\nSaved full response: {data_path} ({len(output_json.encode('utf-8'))} bytes)")
        except Exception as e:
            print(f"\nWarning: could not save: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
