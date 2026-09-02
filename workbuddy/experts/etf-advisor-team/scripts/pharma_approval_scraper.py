# -*- coding: utf-8 -*-
"""
Pharma Approval Scraper — 医药政策催化 + 药品审评 + 批签发一手信源采集器
                          （Level 4 行业专属信源库 · 医药板块脚本化层）

为什么需要：
  · 医药是政策驱动最强的板块：医保集采/谈判续约/价格机制、药品审评受理/获批、
    疫苗与血制品批签发，是个股最核心的高频催化；
  · 现有 industry_chain_scraper 的 pharma 模块只给 NMPA/NHSA 查询入口，
    本脚本直接抓取**国家医保局官网公告列表（标题+发文号+日期+链接）的真实一手催化流**，
    并对集采/谈判/价格/支付等关键词打标签，供事件驱动分析。

数据源（A 类一手·政府部委公开，无需认证）：
  1. 国家医保局 NHSA  https://www.nhsa.gov.cn/col/col104/index.html  （政策法规，已实测可抓）
                      https://www.nhsa.gov.cn/col/col105/index.html  （政策解读，已实测可抓）
  2. 药品审评中心 CDE  https://www.cde.org.cn/  （受理品种/审评公示，JS 渲染→降级 web_fetch）
  3. 中检院 NIFDC      https://www.nifdc.org.cn/  （生物制品批签发，降级 web_fetch）

⚠ 信源诚信铁律：
  - 仅取上述政府/事业单位官方公开页（A 类一手）；
  - 永不爬 米内网/摩熵/医药魔方/IQVIA/Cortellis/Citeline 等 D 类付费墙；
  - 接口被反爬/JS 渲染 → status=degraded + fallback_urls，绝不编造数字。

输出：FinancialData/pharma_approval.json

用法：
  python pharma_approval_scraper.py                 # 全模块
  python pharma_approval_scraper.py --module nhsa   # 仅医保政策
  python pharma_approval_scraper.py --module cde    # 仅药品审评
  python pharma_approval_scraper.py --module batch  # 仅批签发
  python pharma_approval_scraper.py --out x.json
"""
from __future__ import annotations

import argparse
import json
import re
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
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 关键词 -> 催化类型（用于事件驱动归类）
KEYWORD_TAGS = {
    "集采": "集采", "集中带量采购": "集采", "带量采购": "集采", "国采": "集采", "省采": "集采",
    "联盟采购": "集采",
    "谈判": "医保谈判", "续约": "医保谈判", "目录调整": "医保目录", "医保目录": "医保目录",
    "价格": "价格机制", "挂网": "价格机制", "比价": "价格机制", "形成机制": "价格机制",
    "DRG": "支付改革", "DIP": "支付改革", "支付方式": "支付改革", "支付标准": "支付改革",
    "创新药": "创新药支持", "丙类目录": "创新药支持", "商保": "创新药支持",
    "中药": "中药", "中成药": "中药",
    "耗材": "耗材集采", "医用耗材": "耗材集采",
}


def _clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().strip("\u200b")


def _tag(title: str) -> List[str]:
    tags = []
    for kw, t in KEYWORD_TAGS.items():
        if kw in title and t not in tags:
            tags.append(t)
    return tags


# ============================================================
# Module: NHSA 国家医保局 政策法规 / 政策解读（A 类一手·已实测可抓）
# ============================================================

NHSA_COLS = {
    "col104": "政策法规",
    "col105": "政策解读",
}


def _parse_nhsa_list(html: str, col_name: str) -> List[Dict[str, Any]]:
    """解析国家医保局栏目列表页的 <li> 条目（标题/发文号/日期/链接）。"""
    items: List[Dict[str, Any]] = []
    for li in re.findall(r"<li>(.*?)</li>", html, re.S):
        m = re.search(r'<a[^>]+href="([^"]+)"[^>]*title="([^"]{4,80})"', li)
        if not m:
            continue
        href, title = m.group(1), _clean(m.group(2))
        date_m = re.findall(r"(20\d{2}-\d{2}-\d{2})", li)
        date = date_m[-1] if date_m else ""
        docno_m = re.search(r"〔20\d{2}〕\s*\d+号|第\d+号", li)
        url = href if href.startswith("http") else "https://www.nhsa.gov.cn" + href
        items.append({
            "title": title,
            "date": date,
            "doc_no": _clean(docno_m.group(0)) if docno_m else "",
            "url": url,
            "column": col_name,
            "tags": _tag(title),
        })
    return items


def fetch_nhsa() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "nhsa",
        "source": "国家医疗保障局 NHSA — 政策法规 / 政策解读",
        "compliance": "A 类一手公开（政府部委官网列表，实测可抓）",
        "industry_logic": "医保集采/谈判续约/价格机制/支付改革=医药个股最强政策催化；"
                          "对集采/谈判/价格/创新药/耗材等关键词打标签供事件驱动分析。",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    for col, name in NHSA_COLS.items():
        url = f"https://www.nhsa.gov.cn/col/{col}/index.html"
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.encoding = r.apparent_encoding or "utf-8"
            out["items"].extend(_parse_nhsa_list(r.text, name))
        except Exception as e:
            out.setdefault("errors", []).append(f"{col}: {e}")
    # 去重 + 按日期倒序
    seen = set()
    uniq = []
    for it in out["items"]:
        key = it["url"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    uniq.sort(key=lambda x: x.get("date", ""), reverse=True)
    out["items"] = uniq[:40]
    # 催化高亮：含标签的条目
    out["catalysts"] = [it for it in out["items"] if it["tags"]][:20]
    if not out["items"]:
        out["status"] = "degraded"
        out["fallback_urls"] = {
            "policy": "https://www.nhsa.gov.cn/col/col104/index.html",
            "interpret": "https://www.nhsa.gov.cn/col/col105/index.html",
            "web_search": "国家医保局 集采 谈判 价格 最新公告",
        }
    return out


# ============================================================
# Module: CDE 药品审评中心 — 受理品种 / 审评公示（JS 渲染→降级）
# ============================================================

def fetch_cde() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "cde",
        "source": "国家药品监督管理局药品审评中心 CDE",
        "compliance": "A 类一手公开（事业单位官网，JS 动态渲染/反爬）",
        "industry_logic": "新药受理→纳入优先审评/突破性疗法→获批，是创新药企估值催化主线；"
                          "受理号月度量反映行业研发活跃度。",
        "official_pages": {
            "drug_accept": "https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d",
            "priority_review": "https://www.cde.org.cn/main/news/listpage/9c7a5d9a08bbeae5b8cfabbcc1b1f63b",
            "nmpa_approval": "https://www.nmpa.gov.cn/yaopin/ypjgdt/index.html",
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    # 尝试 NMPA 药品监管动态列表（部分页可静态抓），CDE 本体多为 JS 渲染→降级
    try:
        url = out["official_pages"]["nmpa_approval"]
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        rx = re.compile(r'<a[^>]+href="([^"]+)"[^>]*title="([^"]{6,60})"')
        for href, title in rx.findall(r.text)[:20]:
            title = _clean(title)
            if not title:
                continue
            full = href if href.startswith("http") else f"https://www.nmpa.gov.cn{href}"
            out["items"].append({"title": title, "url": full, "tags": _tag(title)})
    except Exception as e:
        out.setdefault("errors", []).append(str(e))
    if not out["items"]:
        out["status"] = "degraded"
        out["fallback_urls"] = dict(out["official_pages"],
                                    web_search="CDE 药品受理 优先审评 突破性疗法 最新")
        out["fallback_hint"] = ("CDE/NMPA 受理品种页为 JS 渲染，用 web_fetch official_pages "
                                "或 web_search 获取最新受理/获批清单。")
    return out


# ============================================================
# Module: 批签发 — 中检院 NIFDC 生物制品（疫苗/血制品，降级）
# ============================================================

def fetch_batch_release() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "module": "batch",
        "source": "中国食品药品检定研究院 NIFDC — 生物制品批签发",
        "compliance": "A 类一手公开（事业单位官网，多为查询/JS 页）",
        "industry_logic": "疫苗/血制品批签发量=出厂放行先行指标，直接对应当期收入确认节奏；"
                          "批签发同比反映疫苗龙头与血制品景气。",
        "official_pages": {
            "nifdc_batch": "https://bio.nifdc.org.cn/pqf/search.do",
            "nifdc_home": "https://www.nifdc.org.cn/",
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "status": "degraded",
        "fallback_urls": {
            "nifdc": "https://bio.nifdc.org.cn/pqf/search.do",
            "web_search": "中检院 批签发 疫苗 血制品 月度 最新",
        },
        "fallback_hint": ("NIFDC 批签发为查询表单页，用 web_fetch official_pages.nifdc_batch "
                          "或 web_search 获取最新月度批签发量。"),
    }
    return out


# ============================================================
# 主流程
# ============================================================

MODULES = {
    "nhsa": fetch_nhsa,
    "cde": fetch_cde,
    "batch": fetch_batch_release,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="医药政策+审评+批签发一手信源采集")
    ap.add_argument("--module", choices=list(MODULES.keys()) + ["all"], default="all")
    ap.add_argument("--out")
    args = ap.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    fd = Path(__file__).resolve().parents[3] / "FinancialData"

    targets = MODULES if args.module == "all" else {args.module: MODULES[args.module]}
    results: Dict[str, Any] = {}
    for key, fn in targets.items():
        print(f"[pharma_approval] 抓取 {key}...", file=sys.stderr)
        try:
            results[key] = fn()
        except Exception as e:
            results[key] = {"module": key, "status": "degraded", "error": str(e)}

    n_nhsa = len(results.get("nhsa", {}).get("items", []))
    n_cat = len(results.get("nhsa", {}).get("catalysts", []))
    status = "ok" if n_nhsa else "degraded"

    payload = {
        "metadata": {
            "scraper": "pharma_approval_scraper.py",
            "generated_at": now,
            "data_sources": [
                "国家医保局 NHSA 政策法规/政策解读（A 类一手）",
                "CDE 药品审评中心 / NMPA 药监局（A 类一手，JS 渲染降级）",
                "中检院 NIFDC 批签发（A 类一手，查询页降级）",
            ],
            "compliance": "全部政府/事业单位官方公开页；禁用米内/摩熵/医药魔方/IQVIA 等付费墙。",
        },
        "summary": {
            "status": status,
            "nhsa_items": n_nhsa,
            "nhsa_catalysts": n_cat,
        },
        "modules": results,
    }
    out_path = Path(args.out) if args.out else fd / "pharma_approval.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[pharma_approval] status={status} nhsa_items={n_nhsa} catalysts={n_cat} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
