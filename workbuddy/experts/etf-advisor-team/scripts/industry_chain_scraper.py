# -*- coding: utf-8 -*-
"""
Industry Chain Scraper — 行业产业链高频数据采集
                         （Level 4 行业专属信源库的脚本化层）

覆盖四个高优先级行业（v1.16 缺口 4）：
  1. 乘联会 CPCA   — 乘用车批发/零售周度数据（汽车/电新刚需）
  2. Mysteel       — 螺纹钢/铁矿石/电解铜公开报价（制造周期刚需）
  3. NMPA 药监局   — 药品审评审批/集采中标公告（医药刚需）
  4. CINNO/TrendForce 公开新闻稿 — 半导体/面板月度量价（电子）

v1.17 新增 5 个半结构化单行业景气源（官方/协会一手，按文章发布）：
  5. game      — 国家新闻出版署 游戏版号审批公示（游戏供给侧景气）
  6. machinery — 中国工程机械工业协会 挖掘机月度销量（基建/制造周期）
  7. building  — 中国建材流通协会 全国建材家居景气指数 BHI（地产后周期）
  8. textile   — 中国轻纺城 柯桥纺织指数（纺服需求风向标）
  9. dutyfree  — 海口海关 海南离岛免税销售额（高端可选消费）

v1.18 新增 2 个半结构化单行业景气源：
  10. boxoffice — 灯塔/猫眼专业版 实时票房（传媒/院线景气，A 类公开接口可读片名/占比/累计票房）
  11. land      — 中国土地市场网 土地成交（房地产新开工先行指标，JS 渲染→降级 web_fetch）

⚠ 设计原则（严格遵守 v1.9 信源诚信四铁律）：
  - 乘联会 / Mysteel / NMPA：直接爬官网公开页（A 类一手）
  - CINNO / TrendForce：仅取**公开新闻稿**（B 类权威转引），
    不使用付费版报告中的精确数字
  - 海外付费机构（IDC/Omdia/LightCounting）→ 永远不爬

数据降级策略：
  - 主源失败 → 自动降级为「返回查询 URL + 提示用 web_fetch」
  - 不编造数字、不混入「估算值」

输出：FinancialData/industry_{module}.json

用法：
  python industry_chain_scraper.py --module auto       # 乘联会汽车销量
  python industry_chain_scraper.py --module steel      # Mysteel 钢价
  python industry_chain_scraper.py --module pharma     # NMPA 审批
  python industry_chain_scraper.py --module display    # 面板/半导体公开新闻
  python industry_chain_scraper.py --module game       # 游戏版号
  python industry_chain_scraper.py --module machinery  # 挖掘机销量
  python industry_chain_scraper.py --module building   # BHI 建材家居景气
  python industry_chain_scraper.py --module textile    # 柯桥纺织指数
  python industry_chain_scraper.py --module dutyfree   # 海南离岛免税
  python industry_chain_scraper.py --module all
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ============================================================
# Module 1: 乘联会 CPCA — 乘用车批发/零售周度数据
# ============================================================

def fetch_cpca() -> Dict[str, Any]:
    """乘联会公开数据中心 — cpcaauto.com 公开新闻稿"""
    out: Dict[str, Any] = {
        "module": "auto",
        "source": "乘联会（CPCA）— 中国乘用车市场信息联席会",
        "official_url": "https://www.cpcaauto.com/",
        "data_url": "https://www.cpcaauto.com/newslist.php?types=csdcfx",  # 厂商数据
        "method": "官网公开新闻稿列表抓取",
        "compliance": "A 类一手公开",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    try:
        r = requests.get(out["data_url"], headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        text = r.text
        # 简单提取最近新闻标题（li 列表 + 链接）
        rx = re.compile(r'<a[^>]+href="(/news_detail\.php\?id=\d+)"[^>]*>([^<]+)</a>')
        matches = rx.findall(text)[:30]
        for href, title in matches:
            out["items"].append({
                "title": title.strip(),
                "url": "https://www.cpcaauto.com" + href,
            })
    except Exception as e:
        out["error"] = str(e)
        out["fallback_hint"] = "请用 web_fetch https://www.cpcaauto.com/ 获取最新周度/月度数据"
    return out


# ============================================================
# Module 2: Mysteel — 钢材/有色公开行情
# ============================================================

def fetch_mysteel() -> Dict[str, Any]:
    """Mysteel 我的钢铁网公开新闻 — index.mysteel.com"""
    out: Dict[str, Any] = {
        "module": "steel",
        "source": "Mysteel 我的钢铁网",
        "compliance": "B 类权威转引（公开新闻稿，不使用付费版报告）",
        "official_pages": {
            "rebar_index": "https://index.mysteel.com/xpic/detail.html?tabName=spotPrice",
            "iron_ore": "https://index.mysteel.com/price/getChartMultiCity.ms?priceTypes=1&catalog=&keyword=铁矿石",
            "news_steel": "https://www.mysteel.com/news.html",
            "news_nonferrous": "https://list.mysteel.net/mss/detail.html?productCode=YS",
        },
        "method": "Mysteel 反爬严格，本脚本仅返回公开页面查询 URL",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "fallback_hint": "用 web_fetch 上述 official_pages 任一 URL 获取实时报价",
    }
    return out


# ============================================================
# Module 3: NMPA 药监局 — 药品审评审批 + 集采中标
# ============================================================

def fetch_nmpa() -> Dict[str, Any]:
    """国家药监局 NMPA 公开公告"""
    out: Dict[str, Any] = {
        "module": "pharma",
        "source": "国家药品监督管理局 NMPA",
        "compliance": "A 类一手公开（政府部委）",
        "official_pages": {
            "drug_approval": "https://www.nmpa.gov.cn/yaopin/ypjgdt/index.html",
            "device_approval": "https://www.nmpa.gov.cn/qxxxgk/index.html",
            "medical_insurance": "https://www.nhsa.gov.cn/col/col133/index.html",  # 医保局集采
            "cde_approval": "https://www.cde.org.cn/main/news/listpage/9c7a5d9a08bbeae5b8cfabbcc1b1f63b",
        },
        "method": "NMPA 部分公告页有反爬，本脚本提供查询入口",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    # 尝试取国家药监局首页公告列表
    try:
        url = out["official_pages"]["drug_approval"]
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = "utf-8"
        text = r.text
        rx = re.compile(r'<a[^>]+href="([^"]+)"[^>]+title="([^"]+)"', re.IGNORECASE)
        matches = rx.findall(text)[:20]
        for href, title in matches:
            if not title.strip():
                continue
            full = href if href.startswith("http") else f"https://www.nmpa.gov.cn{href}"
            out["items"].append({"title": title.strip(), "url": full})
    except Exception as e:
        out["error"] = str(e)
        out["fallback_hint"] = "请用 web_fetch 上述 official_pages.drug_approval 获取最新公告"
    return out


# ============================================================
# Module 4: 半导体/面板/存储公开新闻（CINNO / TrendForce 公开稿）
# ============================================================

def fetch_display_semi() -> Dict[str, Any]:
    """半导体/面板/存储 — 官方公开新闻稿（不使用付费版数据）"""
    out: Dict[str, Any] = {
        "module": "display_semi",
        "source": "CINNO Research 公开新闻 + TrendForce 公开稿 + SEMI 公开统计",
        "compliance": "B 类权威转引（公开新闻稿层面，不使用付费报告中的精确数字）",
        "important_note": "v1.9 铁律一·D 类伪信源黑名单"
                          "（IDC / Omdia / LightCounting / Gartner / Counterpoint）— "
                          "本脚本不爬这些；如需面板/存储/光模块的精确出货数字，请走"
                          "「公司公告 + 权威媒体（证券时报/财联社/新华社）转引」路径",
        "official_pages": {
            "cinno_news": "https://www.cinno.com.cn/research/news",
            "trendforce_press": "https://www.trendforce.cn/news",
            "semi_statistics": "https://www.semi.org.cn/site/semi/index.aspx",
            "icinsights_news": "https://www.icinsights.com/news/",  # 公开新闻
            "sigmaintell_press": "https://www.sigmaintell.com/news.html",
        },
        "method": "公开新闻列表抓取（不爬付费报告页）",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    # 尝试取 TrendForce 公开新闻
    try:
        url = "https://www.trendforce.cn/news"
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        text = r.text
        rx = re.compile(r'<a[^>]+href="(/news/\d+\.html)"[^>]*>([^<]+)</a>')
        matches = rx.findall(text)[:15]
        for href, title in matches:
            out["items"].append({
                "title": title.strip(),
                "url": "https://www.trendforce.cn" + href,
                "source": "TrendForce 公开新闻稿",
            })
    except Exception as e:
        out.setdefault("errors", []).append(f"TrendForce: {e}")
        out["fallback_hint"] = "用 web_fetch official_pages.trendforce_press 获取最新公开新闻"
    return out


# ============================================================
# 半结构化单行业景气源（v1.17 扩展）
#   这些源多为「政府/行业协会按文章发布」的景气指数，难以稳定结构化，
#   统一策略：返回 A/B 类官方入口 + 行业逻辑 + best-effort 标题抓取 + web_fetch 兜底。
#   严守铁律：只取官方/协会一手页，绝不爬伽马/艺恩/中指/克而瑞等付费墙。
# ============================================================

def _best_effort_titles(url: str, link_regex: str, base: str = "",
                        limit: int = 15) -> List[Dict[str, str]]:
    """通用 best-effort 文章标题抓取；失败返回空列表（由上层降级）。"""
    items: List[Dict[str, str]] = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        for href, title in re.findall(link_regex, r.text)[:limit]:
            title = re.sub(r"\s+", " ", title).strip()
            if len(title) < 4:
                continue
            full = href if href.startswith("http") else base + href
            items.append({"title": title, "url": full})
    except Exception:
        pass
    return items


def fetch_game_banhao() -> Dict[str, Any]:
    """游戏版号 — 国家新闻出版署（NPPA）国产/进口网络游戏审批公示。"""
    out: Dict[str, Any] = {
        "module": "game",
        "source": "国家新闻出版署 NPPA — 游戏版号审批公示",
        "compliance": "A 类一手公开（政府部委）",
        "industry_logic": "版号月度过审数量与节奏=游戏行业供给侧景气与监管风向核心先行指标；"
                          "进口版号重启=板块催化。",
        "official_pages": {
            "domestic_banhao": "https://www.nppa.gov.cn/bsfw/jggs/yxspmlgs/",   # 国产网游
            "imported_banhao": "https://www.nppa.gov.cn/bsfw/jggs/jkwlyxspmlgs/",  # 进口网游
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": _best_effort_titles(
            "https://www.nppa.gov.cn/bsfw/jggs/yxspmlgs/",
            r'<a[^>]+href="([^"]+)"[^>]*>(\d{4}年.{0,30}游戏|.{0,20}审批信息)[^<]*</a>',
            base="https://www.nppa.gov.cn",
        ),
    }
    if not out["items"]:
        out["fallback_hint"] = ("用 web_fetch official_pages.domestic_banhao 获取最新一批国产网络游戏"
                                "审批数量与名单；统计当月过审款数与同环比。")
    return out


def fetch_machinery() -> Dict[str, Any]:
    """工程机械 — 中国工程机械工业协会 挖掘机/装载机销量月报。"""
    out: Dict[str, Any] = {
        "module": "machinery",
        "source": "中国工程机械工业协会 CCMA",
        "compliance": "A 类一手公开（行业协会官方统计）",
        "industry_logic": "挖掘机月度销量（内销/出口）=基建地产开工与制造周期的强先行指标；"
                          "小松挖掘机开工小时数=终端施工活跃度高频代理。",
        "official_pages": {
            "ccma_stats": "http://www.cncma.org/col/zuixtz",      # 协会统计/最新通知
            "ccma_branch": "http://www.cncma.org/col/fenhdt",     # 分会动态（挖掘机分会）
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": _best_effort_titles(
            "http://www.cncma.org/col/zuixtz",
            r'<a[^>]+href="(/article/\d+)"[^>]*>([^<]{6,80})</a>',
            base="http://www.cncma.org",
        ),
    }
    if not out["items"]:
        out["fallback_hint"] = ("用 web_fetch official_pages.ccma_stats 获取最新挖掘机月度销量"
                                "（总销量/国内/出口及同比）。")
    return out


def fetch_building_materials() -> Dict[str, Any]:
    """建材家居 — 中国建材流通协会 全国建材家居景气指数 BHI。"""
    out: Dict[str, Any] = {
        "module": "building",
        "source": "中国建材流通协会 — 全国建材家居景气指数 BHI",
        "compliance": "A 类一手公开（行业协会官方指数）",
        "industry_logic": "BHI 指数=地产竣工后周期（家居/建材/家电）需求景气核心指标；"
                          "环比回升=家居建材终端回暖信号。",
        "official_pages": {
            "bhi_monitor": "http://www.cbmf.org/yxjc/",       # 运行监测（BHI 发布栏）
            "cbmf_news": "http://www.cbmf.org/xwzx/lhhdt/",   # 流通协会动态
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "items": _best_effort_titles(
            "http://www.cbmf.org/yxjc/",
            r'<a[^>]+href="([^"]+)"[^>]*>([^<]*BHI[^<]*|[^<]*景气指数[^<]*)</a>',
            base="http://www.cbmf.org",
        ),
    }
    if not out["items"]:
        out["fallback_hint"] = ("用 web_fetch official_pages.bhi_monitor 获取最新月度 BHI 指数"
                                "及环比/同比；或 web_search「全国建材家居景气指数 BHI 最新」。")
    return out


def fetch_textile() -> Dict[str, Any]:
    """纺织 — 中国轻纺城·柯桥纺织指数（景气/价格/总指数）。"""
    out: Dict[str, Any] = {
        "module": "textile",
        "source": "中国轻纺城 — 柯桥纺织指数（全国纺织品价格与景气风向标）",
        "compliance": "B 类权威转引（官方指数，按文章发布；脚本仅给入口）",
        "industry_logic": "柯桥纺织指数（总景气/价格/流通景气）=全国纺织面料供需与终端订单"
                          "景气的高频风向标；总指数环比上行=纺服需求回暖。",
        "official_pages": {
            "qfindex": "http://www.qfindex.com/",                 # 柯桥纺织指数官网
            "china_textile_city": "http://www.zgqfc.gov.cn/",     # 中国轻纺城
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "fallback_hint": ("用 web_fetch http://www.qfindex.com/ 获取最新柯桥纺织总指数及价格/景气分项；"
                          "或 web_search「柯桥纺织指数 总景气指数 最新」。"),
    }
    return out


def fetch_duty_free() -> Dict[str, Any]:
    """免税消费 — 海南离岛免税销售额（海口海关 / 海南省商务厅公开发布）。"""
    out: Dict[str, Any] = {
        "module": "dutyfree",
        "source": "海口海关 / 海南省商务厅 — 海南离岛免税购物数据",
        "compliance": "A 类一手公开（海关/政府部门统计，按公告发布）",
        "industry_logic": "海南离岛免税月度销售额/购物人数=高端消费与免税龙头（中免）景气核心"
                          "代理；同比增速反映可选消费复苏强度。",
        "official_pages": {
            "haikou_customs": "http://haikou.customs.gov.cn/",         # 海口海关
            "hainan_commerce": "https://dofcom.hainan.gov.cn/",        # 海南省商务厅
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "fallback_hint": ("海关页反爬，用 web_fetch official_pages 或 "
                          "web_search「海口海关 海南离岛免税 销售额 监管 最新」获取月度数据。"),
    }
    return out


# ============================================================
# Module 10: boxoffice — 灯塔/猫眼 实时票房（传媒院线景气，A 类一手接口）
# ============================================================

def fetch_boxoffice() -> Dict[str, Any]:
    """传媒院线 — 灯塔专业版实时票房接口（影片票房占比/累计票房/上座率）。"""
    out: Dict[str, Any] = {
        "module": "boxoffice",
        "source": "猫眼·灯塔专业版 — 实时票房 dashboard 接口",
        "compliance": "B 类权威转引（灯塔公开实时接口，影片名/占比/累计票房可读，"
                      "绝对实时数字部分字体加密则不取）",
        "industry_logic": "大盘日票房与头部影片累计票房=传媒/院线（万达/横店/上海电影）景气与"
                          "内容公司业绩弹性核心代理；档期表现驱动板块情绪。",
        "data_url": "https://piaofang.maoyan.com/dashboard-ajax",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "movies": [],
    }
    try:
        r = requests.get(out["data_url"], headers={**HEADERS,
                         "Referer": "https://piaofang.maoyan.com/"}, timeout=TIMEOUT)
        j = r.json()
        ml = (j.get("movieList") or {}).get("data") or {}
        for m in (ml.get("list") or [])[:20]:
            info = m.get("movieInfo") or {}
            out["movies"].append({
                "name": info.get("movieName"),
                "box_rate": m.get("boxRate"),         # 当日票房占比
                "seat_rate": m.get("avgSeatView"),    # 上座率
                "sum_box": m.get("sumBoxDesc"),       # 累计票房（可读）
                "release_info": info.get("releaseInfo"),
            })
        nb = ml.get("nationBoxInfo") or {}
        out["nationwide"] = {
            "total_box_desc": nb.get("nationBoxSplitDesc") or nb.get("nationBoxDesc"),
            "update": (ml.get("updateInfo") or {}).get("updateTime"),
        }
    except Exception as e:
        out["error"] = str(e)
    if not out["movies"]:
        out["status"] = "degraded"
        out["fallback_hint"] = ("用 web_fetch https://piaofang.maoyan.com/dashboard "
                                "或 web_search「今日票房 大盘 实时 灯塔」获取最新档期数据。")
    return out


# ============================================================
# Module 11: land — 土地成交（房地产先行指标，JS 页→降级）
# ============================================================

def fetch_land() -> Dict[str, Any]:
    """房地产 — 全国/重点城市土地成交（自然资源部·中国土地市场网，JS 渲染→降级）。"""
    out: Dict[str, Any] = {
        "module": "land",
        "source": "中国土地市场网 / 各地公共资源交易平台 — 土地出让成交",
        "compliance": "A 类一手公开（自然资源部/地方政府平台，页面多为 JS 渲染）",
        "industry_logic": "300 城土地成交建筑面积/成交楼面价/溢价率=房企补库与新开工先行指标，"
                          "领先地产销售与开工约 6-12 个月；溢价率反映房企拿地意愿与市场热度。",
        "official_pages": {
            "landchina": "https://www.landchina.com/",
            "ggzy": "https://www.ggzy.gov.cn/",   # 全国公共资源交易平台
        },
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "status": "degraded",
        "fallback_urls": {
            "landchina": "https://www.landchina.com/",
            "web_search": "300城 土地成交 成交楼面价 溢价率 最新 中指 克而瑞 公开",
        },
        "fallback_hint": ("土地市场网为 JS 渲染、明细成交需查询，用 web_fetch official_pages "
                          "或 web_search 获取 300 城土地成交面积/楼面价/溢价率（仅取公开转引，"
                          "不使用中指 CREIS / 克而瑞 CRIC / 贝壳付费版精确数据）。"),
    }
    return out


# ============================================================
# 主流程
# ============================================================

ALL_MODULES = {
    "auto": fetch_cpca,
    "steel": fetch_mysteel,
    "pharma": fetch_nmpa,
    "display": fetch_display_semi,
    "game": fetch_game_banhao,
    "machinery": fetch_machinery,
    "building": fetch_building_materials,
    "textile": fetch_textile,
    "dutyfree": fetch_duty_free,
    "boxoffice": fetch_boxoffice,
    "land": fetch_land,
}


def main():
    parser = argparse.ArgumentParser(description="Industry chain scraper — 行业产业链高频数据")
    parser.add_argument("--module", choices=list(ALL_MODULES.keys()) + ["all"], default="all")
    parser.add_argument("--output", help="输出 JSON 路径，默认 FinancialData/industry_chain_{module}.json")
    args = parser.parse_args()

    if args.module == "all":
        results: Dict[str, Any] = {}
        for name, fn in ALL_MODULES.items():
            print(f"[industry_chain] 抓取 {name}...", file=sys.stderr)
            results[name] = fn()
            time.sleep(1.0)
        output = {
            "metadata": {
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "skill_version": "v1.16",
                "compliance": "v1.9 信源诚信四铁律 — A 类一手 + B 类权威转引；"
                              "禁用 IDC/Omdia/LightCounting/Gartner/Counterpoint",
            },
            "modules": results,
        }
        out_path = args.output or "FinancialData/industry_chain_all.json"
    else:
        fn = ALL_MODULES[args.module]
        print(f"[industry_chain] 抓取 {args.module}...", file=sys.stderr)
        output = {
            "metadata": {
                "module": args.module,
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "skill_version": "v1.16",
            },
            "data": fn(),
        }
        out_path = args.output or f"FinancialData/industry_chain_{args.module}.json"

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[industry_chain] 写入 {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
