# -*- coding: utf-8 -*-
"""
Financial Regulator Scraper — 大金融监管与行业经营一手信源采集器
                              （Level 4 行业专属信源库 · 银行/非银/券商/资管脚本化层）

为什么需要：
  · 证监会 IPO/再融资节奏、退市、稽查处罚、并购重组、做市等制度，是券商与全市场风险偏好核心催化；
  · NFRA（金管总局）商业银行净息差/不良率/拨备覆盖率、保险保费，是银行/保险板块基本面主线；
  · 基金业协会公募/私募规模=资管景气；现有脚本仅覆盖成交额/两融（market_overview / margin_balance），
    缺监管政策催化流与行业经营指标这条线。

数据源（A 类一手·监管机构/行业协会公开，无需认证）：
  1. 中国证监会 CSRC  http://www.csrc.gov.cn/  （新闻发布/IPO/执法，实测可抓催化流）
  2. 国家金管总局 NFRA  https://www.nfra.gov.cn/  （银行保险监管指标，Vue/JS→降级 web_fetch）
  3. 中国证券投资基金业协会 AMAC  https://www.amac.org.cn/  （公募/私募规模，半结构化）
  4. 中国证券业协会 SAC  https://www.sac.net.cn/  （券商经营数据，降级）

⚠ 信源诚信铁律：
  - 仅取监管机构/法定行业协会官方公开页（A 类一手）；
  - 永不爬 Wind/同花顺iFinD/Choice 等 D 类付费墙；
  - 监管指标数值（净息差/不良率）官方为 JS/PDF 页时 → status=degraded + fallback_urls，绝不编造。

输出：FinancialData/financial_regulator.json

用法：
  python financial_regulator_scraper.py                # 全模块
  python financial_regulator_scraper.py --module csrc  # 仅证监会催化流
  python financial_regulator_scraper.py --module nfra  # 仅银行保险监管指标
  python financial_regulator_scraper.py --module amac  # 仅基金业协会规模
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

TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 证监会催化关键词 -> 类型
CSRC_TAGS = {
    "IPO": "IPO节奏", "首发": "IPO节奏", "注册": "IPO节奏", "上市": "IPO节奏",
    "再融资": "再融资", "定增": "再融资", "可转债": "再融资", "配股": "再融资",
    "退市": "退市", "ST": "退市",
    "处罚": "执法监管", "立案": "执法监管", "稽查": "执法监管", "违规": "执法监管",
    "操纵": "执法监管", "内幕": "执法监管", "跨境": "执法监管",
    "减持": "股东行为", "增持": "股东行为", "回购": "股东行为",
    "并购": "并购重组", "重组": "并购重组",
    "分红": "分红", "现金分红": "分红",
    "做市": "板块制度", "北交所": "板块制度", "科创板": "板块制度", "创业板": "板块制度",
    "融资融券": "杠杆资金", "转融通": "杠杆资金", "两融": "杠杆资金",
    "公募": "资管", "私募": "资管", "基金": "资管", "理财": "资管",
    "外资": "外资", "QFII": "外资", "互联互通": "外资",
}


def _clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().strip("\u200b")


def _tag(title: str, table: Dict[str, str]) -> List[str]:
    tags = []
    for kw, t in table.items():
        if kw in title and t not in tags:
            tags.append(t)
    return tags


# ============================================================
# Module: 证监会 CSRC 监管催化流（A 类一手·实测可抓）
# ============================================================

def fetch_csrc() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "csrc",
        "source": "中国证券监督管理委员会 CSRC — 新闻发布/IPO/执法",
        "compliance": "A 类一手公开（监管机构官网，实测可抓）",
        "industry_logic": "IPO/再融资节奏=券商投行收入与一级市场供给；执法处罚/退市=市场风险偏好；"
                          "并购重组/做市/板块制度=主题催化；为券商及全市场情绪事件驱动锚点。",
        "official_pages": {
            "csrc_home": "http://www.csrc.gov.cn/csrc/index.shtml",
            "csrc_news": "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml",
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    base = "http://www.csrc.gov.cn"
    seen = set()
    for page in (out["official_pages"]["csrc_home"], out["official_pages"]["csrc_news"]):
        try:
            r = requests.get(page, headers=HEADERS, timeout=TIMEOUT)
            r.encoding = r.apparent_encoding or "utf-8"
            rx = re.compile(r'<a[^>]+href="([^"]+\.shtml)"[^>]*>([^<]{6,60})</a>')
            for href, title in rx.findall(r.text):
                title = _clean(title)
                if not re.search(r"[\u4e00-\u9fff]", title):
                    continue
                if "content.shtml" not in href and "/c" not in href:
                    continue
                url = urllib.parse.urljoin(base, href)
                if url in seen:
                    continue
                seen.add(url)
                tags = _tag(title, CSRC_TAGS)
                out["items"].append({"title": title, "url": url, "tags": tags})
        except Exception as e:
            out.setdefault("errors", []).append(f"{page}: {e}")
    out["items"] = out["items"][:40]
    out["catalysts"] = [it for it in out["items"] if it["tags"]][:25]
    if not out["items"]:
        out["status"] = "degraded"
        out["fallback_urls"] = {
            "csrc": "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml",
            "web_search": "证监会 IPO 再融资 处罚 并购重组 最新",
        }
    return out


# ============================================================
# Module: NFRA 金管总局 银行/保险监管指标（Vue/JS→降级）
# ============================================================

def fetch_nfra() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "nfra",
        "source": "国家金融监督管理总局 NFRA — 银行业保险业监管指标",
        "compliance": "A 类一手公开（监管机构官网，页面为 Vue/JS 动态渲染）",
        "industry_logic": "商业银行净息差(NIM)/不良率/拨备覆盖率/资本充足率=银行板块基本面主线；"
                          "保险保费收入/赔付=保险景气；季度披露，直接驱动银行保险估值。",
        "official_pages": {
            "nfra_stat": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=923&itemId=925",
            "nfra_news": "https://www.nfra.gov.cn/cn/view/pages/index/index.html",
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "status": "degraded",
        "fallback_urls": {
            "nfra_stat": "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemPId=923&itemId=925",
            "web_search": "金管总局 商业银行 净息差 不良率 拨备覆盖率 保险保费 最新季度",
        },
        "fallback_hint": ("NFRA 监管指标页为 Vue/JS 动态渲染（数据走内部 JSON 接口），"
                          "用 web_fetch official_pages.nfra_stat 或 web_search 获取最新季度"
                          "净息差/不良率/拨备覆盖率/保费收入。"),
    }
    return out


# ============================================================
# Module: 基金业协会 AMAC 公募/私募规模（半结构化→best-effort + 降级）
# ============================================================

def fetch_amac() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "amac",
        "source": "中国证券投资基金业协会 AMAC — 公募/私募规模统计",
        "compliance": "A 类一手公开（法定行业协会官网，数据多为月报/PDF）",
        "industry_logic": "公募基金规模/新发份额=权益市场资金供给与券商代销/基金公司景气；"
                          "私募规模=高净值与机构风险偏好；月度披露。",
        "official_pages": {
            "amac_home": "https://www.amac.org.cn/",
            "public_fund": "https://www.amac.org.cn/researchstatistics/datastatistics/mutualfundindustydata/",
            "private_fund": "https://www.amac.org.cn/researchstatistics/datastatistics/privatefunddata/",
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    try:
        r = requests.get(out["official_pages"]["amac_home"], headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        rx = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{6,50})</a>')
        for href, title in rx.findall(r.text):
            title = _clean(title)
            if not re.search(r"规模|公示|备案|统计|月报|数据", title):
                continue
            url = urllib.parse.urljoin("https://www.amac.org.cn/", href)
            out["items"].append({"title": title, "url": url})
    except Exception as e:
        out.setdefault("errors", []).append(str(e))
    seen = set(); uniq = []
    for it in out["items"]:
        if it["url"] in seen:
            continue
        seen.add(it["url"]); uniq.append(it)
    out["items"] = uniq[:15]
    out["status"] = "ok" if out["items"] else "degraded"
    out["fallback_urls"] = {
        "public_fund": out["official_pages"]["public_fund"],
        "private_fund": out["official_pages"]["private_fund"],
        "web_search": "基金业协会 公募基金 市场数据 私募基金 规模 最新月报",
    }
    out["fallback_hint"] = ("公募/私募规模具体数值多在月报 PDF，用 web_fetch official_pages "
                            "或 web_search 获取最新规模与新发份额。")
    return out


# ============================================================
# 主流程
# ============================================================

MODULES = {
    "csrc": fetch_csrc,
    "nfra": fetch_nfra,
    "amac": fetch_amac,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="大金融监管与行业经营一手信源采集")
    ap.add_argument("--module", choices=list(MODULES.keys()) + ["all"], default="all")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    fd = Path(__file__).resolve().parents[3] / "FinancialData"

    targets = MODULES if args.module == "all" else {args.module: MODULES[args.module]}
    results: Dict[str, Any] = {}
    for key, fn in targets.items():
        print(f"[financial_regulator] 抓取 {key}...", file=sys.stderr)
        try:
            results[key] = fn()
        except Exception as e:
            results[key] = {"module": key, "status": "degraded", "error": str(e)}

    n_csrc = len(results.get("csrc", {}).get("items", []))
    n_csrc_cat = len(results.get("csrc", {}).get("catalysts", []))
    status = "ok" if n_csrc else "degraded"

    payload = {
        "metadata": {
            "scraper": "financial_regulator_scraper.py",
            "generated_at": now,
            "data_sources": [
                "中国证监会 CSRC 新闻/IPO/执法（A 类一手）",
                "国家金管总局 NFRA 银行保险监管指标（A 类一手，JS 降级）",
                "基金业协会 AMAC / 证券业协会 SAC 规模与经营（A 类一手）",
            ],
            "compliance": "全部监管机构/法定行业协会官方公开页；禁用 Wind/同花顺iFinD/Choice 等付费墙。",
        },
        "summary": {
            "status": status,
            "csrc_items": n_csrc,
            "csrc_catalysts": n_csrc_cat,
        },
        "modules": results,
    }
    out_path = Path(args.out) if args.out else fd / "financial_regulator.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[financial_regulator] status={status} csrc_items={n_csrc} catalysts={n_csrc_cat} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
