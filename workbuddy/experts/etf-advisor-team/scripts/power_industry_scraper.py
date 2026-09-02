# -*- coding: utf-8 -*-
"""
Power Industry Scraper — 电力运行 + 动力煤价一手信源采集器
                         （Level 4 行业专属信源库 · 公用事业/电新/煤炭/火电脚本化层）

为什么需要：
  · 全社会用电量/发电量分电源/新增装机=公用事业、电力运营、电新（风光储）景气核心量；
  · 电煤采购价格指数（CECI）/动力煤价=火电成本端与煤炭板块盈利的先行指标；
  · 现有脚本（commodity_exchange 期货 / macro 宏观）未覆盖电力运行与电煤价这条主线。

数据源（A 类一手·政府部委/行业协会公开，无需认证）：
  1. 国家能源局 NEA   https://www.nea.gov.cn/   （电力数据/装机/交易电量发布，实测可抓催化流）
  2. 中国电力企业联合会 CEC  https://www.cec.org.cn/   （CECI 中国电煤采购价格指数，实测可抓入口）
  3. 国家统计局（用电量月度，经 macro_data_scraper 间接覆盖）

⚠ 信源诚信铁律：
  - 仅取国家能源局/中电联官方公开页（A 类一手）；
  - 永不爬 Wind/Mysteel/百川/卓创/隆众/汾渭 CCI 付费版等 D 类付费墙；
  - 数值明细（用电量/装机绝对值）官方为 JS 页时 → status=degraded + fallback_urls，绝不编造。

输出：FinancialData/power_industry.json

用法：
  python power_industry_scraper.py                       # 全模块
  python power_industry_scraper.py --module electricity  # 仅电力运行
  python power_industry_scraper.py --module coal_price    # 仅电煤价
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 电力运行相关关键词（用于从能源局新闻流中筛选行业催化）
POWER_KW = ["用电量", "发电量", "发电装机", "装机容量", "新增装机", "交易电量", "电力市场",
            "全社会用电", "风电", "光伏", "新能源", "核电", "水电", "火电", "电力供需",
            "迎峰度", "电价", "绿电", "绿证", "储能", "特高压"]
COAL_KW = ["电煤", "动力煤", "CECI", "煤价", "电煤采购", "燃煤"]


def _clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().strip("\u200b")


def _has_kw(title: str, kws: List[str]) -> List[str]:
    return [k for k in kws if k in title]


# ============================================================
# Module: 电力运行 — 国家能源局 NEA 电力数据催化流（A 类一手·实测可抓）
# ============================================================

def fetch_electricity() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "electricity",
        "source": "国家能源局 NEA — 电力运行/装机/交易电量发布",
        "compliance": "A 类一手公开（政府部委官网新闻流，实测可抓）",
        "industry_logic": "全社会用电量同比=宏观与公用事业景气；分电源发电量/新增装机="
                          "火电/水电/核电/风光运营商业绩驱动；交易电量与电价=电改主线催化。",
        "official_pages": {
            "nea_home": "https://www.nea.gov.cn/",
            "cec_data": "https://www.cec.org.cn/menu/index.html?749",  # 中电联行业统计
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    base = "https://www.nea.gov.cn/"
    try:
        r = requests.get(base, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        rx = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{6,60})</a>')
        seen = set()
        for href, title in rx.findall(r.text):
            title = _clean(title)
            if not re.search(r"[\u4e00-\u9fff]", title):
                continue
            kws = _has_kw(title, POWER_KW)
            if not kws:
                continue
            url = urllib.parse.urljoin(base, href)
            if url in seen:
                continue
            seen.add(url)
            date_m = re.search(r"(20\d{6})", href)
            date = (f"{date_m.group(1)[:4]}-{date_m.group(1)[4:6]}-{date_m.group(1)[6:]}"
                    if date_m else "")
            out["items"].append({"title": title, "date": date, "url": url, "keywords": kws})
    except Exception as e:
        out.setdefault("errors", []).append(str(e))
    out["items"] = out["items"][:25]
    if not out["items"]:
        out["status"] = "degraded"
        out["fallback_urls"] = {
            "nea": "https://www.nea.gov.cn/",
            "cec_stat": "https://www.cec.org.cn/menu/index.html?749",
            "web_search": "国家能源局 全社会用电量 发电装机 1-4月 最新",
        }
        out["fallback_hint"] = ("用电量/发电量/装机的绝对数值多在 PDF/JS 统计页，"
                                "用 web_fetch official_pages 或 web_search 获取明细。")
    return out


# ============================================================
# Module: 电煤价 — 中电联 CECI 中国电煤采购价格指数（A 类一手）
# ============================================================

def fetch_coal_price() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "coal_price",
        "source": "中国电力企业联合会 CEC — CECI 中国电煤采购价格指数",
        "compliance": "A 类一手公开（行业协会官方指数发布页）",
        "industry_logic": "CECI 电煤采购价格指数=火电企业燃料成本核心先行指标，"
                          "与动力煤价同向；煤价下行利好火电盈利、压制煤炭板块，反之亦然。",
        "official_pages": {
            "cec_home": "https://www.cec.org.cn/",
            "ceci_index": "https://www.cec.org.cn/menu/index.html?781",  # CECI 指数专栏
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    try:
        r = requests.get(out["official_pages"]["cec_home"], headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        rx = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{6,60})</a>')
        for href, title in rx.findall(r.text):
            title = _clean(title)
            if not _has_kw(title, COAL_KW):
                continue
            url = urllib.parse.urljoin("https://www.cec.org.cn/", href)
            out["items"].append({"title": title, "url": url, "keywords": _has_kw(title, COAL_KW)})
    except Exception as e:
        out.setdefault("errors", []).append(str(e))
    # 去重
    seen = set(); uniq = []
    for it in out["items"]:
        if it["url"] in seen:
            continue
        seen.add(it["url"]); uniq.append(it)
    out["items"] = uniq[:15]
    # CECI 为周度指数，具体数值需进入专栏页（多为图表/PDF）→ 提供 fallback
    out["status"] = "ok" if out["items"] else "degraded"
    out["fallback_urls"] = {
        "ceci": "https://www.cec.org.cn/menu/index.html?781",
        "qhd_coal": "https://www.cqcoal.com/",   # 秦皇岛煤炭网（环渤海动力煤价格指数）
        "web_search": "CECI 中国电煤采购价格指数 最新一期 环渤海动力煤价",
    }
    out["fallback_hint"] = ("CECI 各期指数点位/动力煤现货价多在专栏图表或 PDF，"
                            "用 web_fetch official_pages.ceci_index 或 web_search 获取最新点位。")
    return out


# ============================================================
# 主流程
# ============================================================

MODULES = {
    "electricity": fetch_electricity,
    "coal_price": fetch_coal_price,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="电力运行+电煤价一手信源采集")
    ap.add_argument("--module", choices=list(MODULES.keys()) + ["all"], default="all")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    fd = Path(__file__).resolve().parents[3] / "FinancialData"

    targets = MODULES if args.module == "all" else {args.module: MODULES[args.module]}
    results: Dict[str, Any] = {}
    for key, fn in targets.items():
        print(f"[power_industry] 抓取 {key}...", file=sys.stderr)
        try:
            results[key] = fn()
        except Exception as e:
            results[key] = {"module": key, "status": "degraded", "error": str(e)}

    n_elec = len(results.get("electricity", {}).get("items", []))
    n_coal = len(results.get("coal_price", {}).get("items", []))
    status = "ok" if (n_elec or n_coal) else "degraded"

    payload = {
        "metadata": {
            "scraper": "power_industry_scraper.py",
            "generated_at": now,
            "data_sources": [
                "国家能源局 NEA 电力数据/装机/交易电量（A 类一手）",
                "中电联 CEC — CECI 中国电煤采购价格指数（A 类一手）",
            ],
            "compliance": "全部政府/行业协会官方公开页；禁用 Wind/Mysteel/百川/卓创/汾渭CCI 等付费墙。",
        },
        "summary": {
            "status": status,
            "electricity_items": n_elec,
            "coal_price_items": n_coal,
        },
        "modules": results,
    }
    out_path = Path(args.out) if args.out else fd / "power_industry.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[power_industry] status={status} electricity={n_elec} coal={n_coal} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
