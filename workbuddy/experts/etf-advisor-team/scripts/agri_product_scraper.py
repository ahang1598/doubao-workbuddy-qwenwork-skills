# -*- coding: utf-8 -*-
"""
Agri Product Scraper — 农产品/养殖业批发价量景气采集器
                      （基本面 §农林牧渔·食品饮料：成本与需求双向先行指标）

为什么需要：
  · 农林牧渔（生猪/禽类/种植/水产）与食品饮料的核心驱动是**农产品现货价格**与**猪周期**；
  · 本脚本补齐农产品免费一手现货价采集能力。

数据源分类与现状（沙箱实测 2026-05）：
  1. 【A 类一手·结构化·可直接脚本化】北京新发地批发市场 价格行情 JSON
     http://www.xinfadi.com.cn/getPriceData.html （POST 表单，全国最大农产品批发市场，
     字段含品名/分类/最低/最高/平均价/产地/单位/发布日；可按品名筛选 白条猪/鸡蛋/玉米 等）
  2. 【A 类一手·需认证】农业农村部「农产品批发价格 200 指数」
     http://ncpscxx.moa.gov.cn/api/indexData/...  → 实测 401，降级为 fallback_url
  3. 【A 类一手·HTML/JS】农业农村部数据中心 能繁母猪/生猪存栏/猪粮比
     https://data.moa.gov.cn/  → 非结构化，降级为 fallback（建议 web_fetch）
  4. 【B 类权威转引】商务部「食用农产品价格指数」商务预报
     http://www.mofcom.gov.cn/  → 路径多变，降级为 fallback

设计原则（信源诚信铁律 + 优雅降级）：
  - 仅取政府/批发市场官方公开接口；永不爬 Wind/Mysteel 农产品等付费墙；
  - 接口失效 → status=degraded + fallback_urls，绝不编造价格。

输出：FinancialData/agri_product.json

用法：
  python agri_product_scraper.py                  # 全量（分类均价 + 关键单品 + 猪周期）
  python agri_product_scraper.py --keyword 白条猪  # 追加自定义关键单品
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

XINFADI_URL = "http://www.xinfadi.com.cn/getPriceData.html"

# 关键单品 -> 所属行业/逻辑（用于个股与景气关联）
KEY_ITEMS = {
    "白条猪": "生猪养殖（猪周期核心，白条猪批发价≈生猪出栏价先行）",
    "鸡蛋": "禽类养殖（蛋价景气）",
    "白条鸡": "禽类养殖（白羽/黄羽肉鸡）",
    "玉米": "种植/饲料成本（养殖成本端）",
    "大豆": "油脂油料/饲料（豆粕成本端）",
    "富士苹果": "水果种植（对标苹果期货）",
}

# 新发地一级分类 -> 行业归类
PCAT_INDUSTRY = {
    "粮油": "种植/粮油加工", "肉类": "畜禽养殖", "水产": "水产养殖",
    "蔬菜": "蔬菜种植", "水果": "水果种植", "禽蛋": "禽类养殖",
}


def _safe_float(v: Any) -> Optional[float]:
    if v in (None, "", "-", "—"):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def _xinfadi_query(prod_name: str = "", current: int = 1, limit: int = 100) -> Dict[str, Any]:
    """调用新发地价格接口；返回解析后的 dict（含 list/count）。失败抛异常由上层捕获。"""
    data = {"limit": str(limit), "current": str(current)}
    if prod_name:
        data["prodName"] = prod_name
    r = requests.post(XINFADI_URL, data=data, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    return r.json()


def fetch_xinfadi_overview() -> Dict[str, Any]:
    """抓取新发地最新一批价格，按一级分类(prodPcat)聚合均价 + 记录发布日。"""
    out: Dict[str, Any] = {
        "source": "北京新发地农产品批发市场",
        "compliance": "A 类一手（全国最大农产品批发市场官方公开接口）",
        "url": XINFADI_URL,
        "by_category": {},
        "items_sampled": 0,
    }
    try:
        # 抓取最新若干页，覆盖当日各品类
        agg: Dict[str, Dict[str, float]] = {}
        pub_dates = set()
        sampled = 0
        for page in (1, 2, 3, 4, 5):
            js = _xinfadi_query(current=page, limit=200)
            rows = js.get("list") or []
            if not rows:
                break
            for row in rows:
                pcat = (row.get("prodPcat") or row.get("prodCat") or "").strip()
                avg = _safe_float(row.get("avgPrice"))
                if not pcat or avg is None or avg <= 0:
                    continue
                a = agg.setdefault(pcat, {"sum": 0.0, "n": 0.0})
                a["sum"] += avg
                a["n"] += 1
                sampled += 1
                pd = (row.get("pubDate") or "")[:10]
                if pd:
                    pub_dates.add(pd)
        out["items_sampled"] = sampled
        out["pub_dates"] = sorted(pub_dates, reverse=True)[:3]
        for pcat, a in sorted(agg.items()):
            if a["n"]:
                out["by_category"][pcat] = {
                    "industry": PCAT_INDUSTRY.get(pcat, ""),
                    "avg_price": round(a["sum"] / a["n"], 3),
                    "sample_count": int(a["n"]),
                    "unit": "元/公斤（各品种均值，仅供横向景气参考）",
                }
        if not out["by_category"]:
            out["status"] = "degraded"
            out["fallback_hint"] = "用 web_fetch http://www.xinfadi.com.cn/priceDetail.html 查看最新批发价"
    except Exception as e:
        out["status"] = "degraded"
        out["error"] = str(e)
        out["fallback_hint"] = "用 web_fetch http://www.xinfadi.com.cn/priceDetail.html 查看最新批发价"
    return out


def fetch_key_items(extra_keywords: List[str]) -> List[Dict[str, Any]]:
    """逐个关键单品查询最新批发价（白条猪=猪周期核心信号）。"""
    items: List[Dict[str, Any]] = []
    names = list(KEY_ITEMS.keys()) + [k for k in extra_keywords if k not in KEY_ITEMS]
    for name in names:
        rec: Dict[str, Any] = {"name": name, "logic": KEY_ITEMS.get(name, "自定义关键单品")}
        try:
            js = _xinfadi_query(prod_name=name, limit=10)
            rows = js.get("list") or []
            if rows:
                latest = rows[0]
                rec.update({
                    "avg_price": _safe_float(latest.get("avgPrice")),
                    "low_price": _safe_float(latest.get("lowPrice")),
                    "high_price": _safe_float(latest.get("highPrice")),
                    "unit": (latest.get("unitInfo") or "元/公斤").strip(),
                    "place": (latest.get("place") or "").strip(),
                    "pub_date": (latest.get("pubDate") or "")[:10],
                    "matched_name": (latest.get("prodName") or "").strip(),
                })
            else:
                rec["status"] = "no_data"
        except Exception as e:
            rec["status"] = "degraded"
            rec["error"] = str(e)
        items.append(rec)
    return items


def build_fallback_sources() -> List[Dict[str, str]]:
    """需认证 / 非结构化的权威一手源，供 LLM 用 web_fetch 兜底。"""
    return [
        {
            "name": "农业农村部·农产品批发价格200指数",
            "compliance": "A 类一手（需认证，脚本不可直采）",
            "fallback_url": "http://ncpscxx.moa.gov.cn/",
            "note": "全国农产品批发价格综合景气指数，含菜篮子产品200指数。",
        },
        {
            "name": "农业农村部·能繁母猪存栏/生猪存栏/猪粮比",
            "compliance": "A 类一手（HTML/JS 非结构化）",
            "fallback_url": "https://data.moa.gov.cn/",
            "note": "猪周期判断核心：能繁母猪存栏拐点领先猪价约 10 个月；猪粮比<6 进入预警去化。",
        },
        {
            "name": "商务部·食用农产品价格指数（商务预报）",
            "compliance": "B 类权威转引",
            "fallback_url": "http://www.mofcom.gov.cn/",
            "note": "周度食用农产品价格指数，反映终端食品 CPI 食品项压力。",
        },
        {
            "name": "Wind/卓创/涌益咨询 生猪现货（付费墙）",
            "compliance": "D 类付费墙——禁止脚本爬取",
            "fallback_url": "（人工或授权终端）",
            "note": "外购仔猪/自繁自养盈利、生猪均价精确版为付费数据，不在本脚本范围。",
        },
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="农产品/养殖业批发价量景气采集（新发地一手 + 权威兜底）")
    ap.add_argument("--keyword", action="append", default=[],
                    help="追加自定义关键单品（可多次），如 --keyword 牛肉 --keyword 草鱼")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    fd = Path(__file__).resolve().parents[3] / "FinancialData"

    print("[agri_product] 抓取新发地批发价概览...", file=sys.stderr)
    overview = fetch_xinfadi_overview()
    print("[agri_product] 抓取关键单品（含白条猪/猪周期）...", file=sys.stderr)
    key_items = fetch_key_items(args.keyword)

    live_ok = bool(overview.get("by_category")) or any(
        i.get("avg_price") is not None for i in key_items)
    status = "ok" if live_ok else "degraded"

    # 组织可读信号
    signals: List[str] = []
    pig = next((i for i in key_items if i["name"] == "白条猪" and i.get("avg_price")), None)
    if pig:
        signals.append(f"白条猪批发价 {pig['avg_price']} {pig.get('unit','元/公斤')}"
                       f"（{pig.get('pub_date','')}，猪周期核心）")
    egg = next((i for i in key_items if i["name"] == "鸡蛋" and i.get("avg_price")), None)
    if egg:
        signals.append(f"鸡蛋批发价 {egg['avg_price']} {egg.get('unit','元/公斤')}")
    corn = next((i for i in key_items if i["name"] == "玉米" and i.get("avg_price")), None)
    if corn:
        signals.append(f"玉米批发价 {corn['avg_price']} {corn.get('unit','元/公斤')}（养殖成本端）")

    payload = {
        "metadata": {
            "scraper": "agri_product_scraper.py",
            "generated_at": now,
            "data_sources": [
                "北京新发地农产品批发市场（A 类一手·结构化）",
                "农业农村部 200 指数 / 能繁母猪（A 类一手·需认证或非结构化，降级 fallback）",
                "商务部食用农产品价格指数（B 类权威转引，降级 fallback）",
            ],
            "compliance": "仅政府/批发市场官方公开接口；禁用 Wind/卓创/涌益 等付费墙精确版生猪数据。",
            "note": "白条猪批发价≈生猪出栏价先行；能繁母猪存栏拐点领先猪价约 10 个月；猪粮比<6 预警。",
        },
        "summary": {
            "status": status,
            "category_count": len(overview.get("by_category", {})),
            "key_item_count": sum(1 for i in key_items if i.get("avg_price") is not None),
            "signals": signals,
        },
        "xinfadi_overview": overview,
        "key_items": key_items,
        "fallback_sources": build_fallback_sources(),
        "fallback_urls": {
            "xinfadi": "http://www.xinfadi.com.cn/priceDetail.html",
            "moa_index200": "http://ncpscxx.moa.gov.cn/",
            "moa_pig": "https://data.moa.gov.cn/",
            "mofcom": "http://www.mofcom.gov.cn/",
            "web_search": "新发地 白条猪 批发价 能繁母猪 存栏 猪粮比 最新",
        },
    }
    out_path = Path(args.out) if args.out else fd / "agri_product.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[agri_product] status={status} categories={len(overview.get('by_category', {}))} "
          f"key_items={payload['summary']['key_item_count']} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
