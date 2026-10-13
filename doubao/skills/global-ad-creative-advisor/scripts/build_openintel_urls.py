#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开放情报链接生成器（P1 同类型产品数据 + P2 付费素材/搜索词，无第三方依赖、零登录）。

为 global-ad-creative-advisor Skill 生成除 Meta Ad Library（由 build_adlibrary_url.py 承载）
与原生内容平台原生热点（由 build_trend_urls.py 承载）之外的全部开放平台入口：

  P2 付费素材：
    gg-transparency  Google Ads 透明度中心（按同类型产品域名，免登录，新广告延迟 48-72h）
    tt-topads        TikTok Creative Center Top Ads（免登录仅前若干卡片，出现登录墙即停）
    tt-ccl           TikTok Commercial Content Library（library.tiktok.com/ads，
                     DSA 法定库，仅 EEA+英国+瑞士，免登录全量，按广告主 adv_name）
    apple-adrepo     Apple Ad Repository（adrepository.apple.com，仅欧盟，SPA 页内选 App/国家/时间）
  P2 ASA 非欧盟替代 / P1 商店数据：
    appstore-search  App Store 某国家店面搜索（ASA 巡查顶部广告位 + listing 素材）
    appstore-chart   App Store 某国家分类榜单
    itunes-search    iTunes 官方公开搜索接口（免 key，App 元数据）
    gplay-search     Google Play 商店搜索
  P1 数据原则：只用官方开放源（上述官方商店/接口）与全网公开搜索；公司背景/融资/技术栈
    一律走公司官网、SEC 等官方披露或全网公开搜索，本脚本不接入任何第三方商业数据/估算平台。
  P2 搜索词：
    gg-suggest       Google SERP（记录搜索下拉 + 相关搜索 + People also ask）
    gtrends-web      Google Trends 网页搜索（近 7 天走势 + Rising 上升词）

市场代码复用 build_adlibrary_url.py 的区域预设/中文名表。
全程零登录：任何入口出现注册/登录墙即停止，换替代源或登记缺口，不自动注册。

示例:
  python3 build_openintel_urls.py --source tt-topads --market ID --period 7 --keyword "AI song"
  python3 build_openintel_urls.py --source tt-ccl --market DE --advertiser Nike
  python3 build_openintel_urls.py --source appstore-search --market US --keyword "AI chatbot"
  python3 build_openintel_urls.py --source gg-transparency --market US --domain replika.com
  # P1/P2 批量侦察计划（域名=同类型产品根域名，app=同类型产品 App/品牌名，keyword=品类/功能词）
  python3 build_openintel_urls.py --plan --markets ID \
      --domain mureka.ai --app Mureka --keyword "AI song" --keyword "lagu AI" \
      --format tsv --out openintel_plan.tsv
  python3 build_openintel_urls.py --selftest
"""
import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_adlibrary_url import normalize_markets  # noqa: E402  复用市场表与区域预设

GG_TRANSPARENCY = "https://adstransparency.google.com/"
TT_TOPADS = "https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
TT_CCL = "https://library.tiktok.com/ads"
APPLE_ADREPO = "https://adrepository.apple.com/"
APPSTORE = "https://apps.apple.com"
ITUNES_SEARCH = "https://itunes.apple.com/search"
GPLAY = "https://play.google.com/store/search"
GOOGLE_SEARCH = "https://www.google.com/search"
GTRENDS = "https://trends.google.com/trends/explore"

TT_PERIODS = {"7", "30", "180"}
GG_DATE_PRESETS = {"Last 7 days", "Last 30 days", "Today", "Yesterday", "Any time"}
# DSA 法定库法域：欧盟 27 国 + 英国 + 瑞士（TT CCL / Apple Ad Repository 覆盖范围，以页面实际可选为准）
DSA_EEA_CH_UK = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    "GB", "CH",
}

SOURCES = [
    "gg-transparency", "tt-topads", "tt-ccl", "apple-adrepo",
    "appstore-search", "appstore-chart", "itunes-search", "gplay-search",
    "gg-suggest", "gtrends-web",
]


def _storefront(market):
    """App Store 国家店面路径段：ISO2 小写（US->us, GB->gb）。"""
    return (market or "us").lower()


def gg_transparency_url(market, domain=None, text=None, preset_date="Last 30 days"):
    if preset_date not in GG_DATE_PRESETS:
        raise ValueError(f"日期预设仅支持 {sorted(GG_DATE_PRESETS)}")
    if not domain and not text:
        raise ValueError("gg-transparency 必须提供 --domain（优先）或 --advertiser")
    pairs = [("region", market if market != "ALL" else "anywhere")]
    if domain:
        pairs.append(("domain", domain.strip()))
    if text:
        pairs.append(("text", text.strip()))
    pairs.append(("preset-date", preset_date))
    note = ("P2付费：页内分 Search/YouTube/Display/Shopping 记录；优先域名覆盖全部广告账户；"
            "仅域名/广告主检索、不支持关键词发现；新广告延迟48-72h；无曝光/花费数值，免登录")
    return GG_TRANSPARENCY + "?" + urllib.parse.urlencode(pairs), note


def tt_topads_url(market, period="30", keyword=None, industry=None,
                  objective=None, fmt=None):
    if period not in TT_PERIODS:
        raise ValueError(f"Top Ads period 仅支持 {sorted(TT_PERIODS)}（天）")
    pairs = [("region", market if market != "ALL" else ""), ("period", period)]
    if keyword:
        pairs.append(("keyword", keyword.strip()))
    if industry:
        pairs.append(("industry", industry.strip()))
    if objective:
        pairs.append(("objective", objective.strip()))
    if fmt:
        pairs.append(("format", fmt.strip()))
    pairs = [(k, v) for k, v in pairs if v != ""]
    note = ("P2付费(TT)：广告主授权样本非全量在投；免登录仅展示前若干卡片，出现登录提示即停、不登录，"
            "采到几条算几条并登记缺口；表现标签只记相对档位不记数值")
    return TT_TOPADS + "?" + urllib.parse.urlencode(pairs), note


def tt_ccl_url(market, advertiser=None):
    if market == "ALL":
        raise ValueError("tt-ccl 必须指定 DSA 法域国家（EEA+GB+CH），不支持 ALL")
    if market not in DSA_EEA_CH_UK:
        raise ValueError(f"TT 商业内容库仅覆盖 EEA+英国+瑞士，{market} 不在法域内，请改用 tt-topads 并登记缺口")
    pairs = [("region", market), ("sort_type", "last_shown_date,desc")]
    if advertiser:
        pairs.insert(1, ("adv_name", advertiser.strip()))
    note = ("P2付费(TT法定库)：DSA 驱动、免登录全量；按广告主 adv_name 查；记录投放地区/时间/形式/广告主体；"
            "仅 EEA+GB+CH 有效")
    return TT_CCL + "?" + urllib.parse.urlencode(pairs), note


def apple_adrepo_url(market=None):
    if market and market != "ALL" and market not in DSA_EEA_CH_UK:
        raise ValueError(f"Apple Ad Repository 仅覆盖欧盟，{market} 无法使用；非欧盟改用 appstore-search 巡查")
    note = ("P2付费(ASA欧盟法定库)：SPA 页内选 App/开发者 + 欧盟国家 + 时间范围；版位=搜索结果/Search Tab/Today；"
            "素材即其自定义产品页CPP/截图/预览视频；无出价/花费，免登录")
    return APPLE_ADREPO, note


def appstore_search_url(market, term):
    if not term:
        raise ValueError("appstore-search 需要 --keyword")
    url = f"{APPSTORE}/{_storefront(market)}/search?" + urllib.parse.urlencode([("term", term)])
    note = ("P1商店/P2-ASA：看搜索结果顶部浅蓝底'Ad/广告'位是谁（ASA 非欧盟巡查，逐词记录命中）+ 自然排名前三 + "
            "同类型产品 listing 素材；记录输入框联想词；时点抽样，免登录")
    return url, note


def appstore_chart_url(market):
    url = f"{APPSTORE}/{_storefront(market)}/charts/iphone"
    note = "P1：分类榜单位次（B级时点值，记录采集时刻），用于市占/活跃代理，免登录"
    return url, note


def itunes_search_url(term, market):
    if not term:
        raise ValueError("itunes-search 需要 --keyword")
    cc = market if market != "ALL" else "US"
    pairs = [("term", term), ("country", cc), ("entity", "software")]
    note = "P1：苹果官方公开接口免 key，返回 App 元数据（开发者/类别/版本/评分计数/描述），无下载量/DAU"
    return ITUNES_SEARCH + "?" + urllib.parse.urlencode(pairs), note


def gplay_search_url(term, market):
    if not term:
        raise ValueError("gplay-search 需要 --keyword")
    pairs = [("q", term), ("c", "apps"), ("gl", market if market != "ALL" else "US")]
    note = "P1：Google Play 搜索与品类，看同类型产品/自然排名/评分评论量，免登录"
    return GPLAY + "?" + urllib.parse.urlencode(pairs), note


def gg_suggest_url(market, term):
    if not term:
        raise ValueError("gg-suggest 需要 --keyword")
    pairs = [("q", term), ("gl", market if market != "ALL" else "US")]
    note = ("P2搜索词(GG)：记录搜索框下拉联想、页底'相关搜索'、People also ask；这些是真实查询扩展，免登录；"
            "不输出精确月搜索量")
    return GOOGLE_SEARCH + "?" + urllib.parse.urlencode(pairs), note


def gtrends_web_url(keywords, market):
    if not keywords:
        raise ValueError("gtrends-web 至少需要一个 --keyword")
    pairs = [("date", "now 7-d"), ("q", ",".join(keywords))]
    if market != "ALL":
        pairs.insert(1, ("geo", market))
    note = "P2搜索词：网页搜索近7天走势 + Rising 上升词（0-100相对指数非搜索量）；直连可能429用浏览器打开"
    return GTRENDS + "?" + urllib.parse.urlencode(pairs), note


def build_plan(markets, domains, apps, keywords):
    """生成 P1/P2 开放情报侦察计划：域名走 GG 透明度；App 名走 TT/ASA/官方商店；
    关键词走 TopAds/商店/搜索词源。公司背景/融资/技术栈走官网/SEC 与全网公开搜索，不在本脚本。"""
    rows = []

    def add(surface, market, query, url, note):
        rows.append({"surface": surface, "market": market, "query": query,
                     "period": "7d/30d", "url": url, "note": note})

    for market in markets:
        for d in domains:
            add("gg-transparency", market, d, *gg_transparency_url(market, domain=d))
        for app in apps:
            in_dsa = market in DSA_EEA_CH_UK
            add("tt-topads", market, app, *tt_topads_url(market, keyword=app))
            if in_dsa:
                add("tt-ccl", market, app, *tt_ccl_url(market, advertiser=app))
                add("apple-adrepo", market, app, *apple_adrepo_url(market))
            add("appstore-search", market, app, *appstore_search_url(market, app))
            add("itunes-search", market, app, *itunes_search_url(app, market))
            add("gplay-search", market, app, *gplay_search_url(app, market))
        for kw in keywords:
            add("tt-topads", market, kw, *tt_topads_url(market, keyword=kw))
            add("appstore-search", market, kw, *appstore_search_url(market, kw))
            add("gplay-search", market, kw, *gplay_search_url(kw, market))
            add("gg-suggest", market, kw, *gg_suggest_url(market, kw))
        if keywords:
            add("gtrends-web", market, ",".join(keywords), *gtrends_web_url(keywords, market))
        add("appstore-chart", market, "-", *appstore_chart_url(market))
    # 同 surface+market+query 去重保序
    seen, dedup = set(), []
    for r in rows:
        key = (r["surface"], r["market"], r["query"])
        if key not in seen:
            seen.add(key)
            dedup.append(r)
    return dedup


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="开放情报链接生成器（P1 同类型产品数据 + P2 付费素材/搜索词，零登录）")
    p.add_argument("--source", choices=SOURCES, help="单个入口；批量用 --plan")
    p.add_argument("--plan", action="store_true", help="按市场一次性生成 P1/P2 侦察计划")
    p.add_argument("--market", default="ALL", help="单入口市场：ISO/中文名/区域预设，默认 ALL")
    p.add_argument("--markets", default="", help="计划模式：逗号分隔多个市场")
    p.add_argument("--keyword", action="append", default=[], help="关键词/App 搜索词，可重复")
    p.add_argument("--domain", action="append", default=[], help="同类型产品根域名，可重复")
    p.add_argument("--app", action="append", default=[], help="同类型产品 App/公司/广告主名，可重复")
    p.add_argument("--advertiser", help="tt-ccl 广告主名（adv_name）")
    p.add_argument("--period", default="30", choices=sorted(TT_PERIODS), help="tt-topads 周期（天）")
    p.add_argument("--preset-date", default="Last 30 days", choices=sorted(GG_DATE_PRESETS))
    p.add_argument("--format", choices=["pretty", "tsv", "json"], default="pretty")
    p.add_argument("--out", help="结果写入文件")
    p.add_argument("--selftest", action="store_true")
    return p.parse_args(argv)


def render(rows, fmt):
    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2)
    if fmt == "tsv":
        head = "surface\tmarket\tquery\tperiod\turl\tnote"
        body = ["\t".join(str(r.get(k, "")) for k in
                         ["surface", "market", "query", "period", "url", "note"]) for r in rows]
        return "\n".join([head] + body)
    lines = [f"[{i+1}] {r['surface']} | {r['market']} | {r['query']}\n    {r['url']}"
             + (f"\n    备注: {r['note']}" if r.get("note") else "") for i, r in enumerate(rows)]
    return f"共 {len(rows)} 条：\n" + "\n".join(lines)


def selftest():
    url, _ = gg_transparency_url("US", domain="replika.com")
    assert url == ("https://adstransparency.google.com/?region=US&domain=replika.com"
                   "&preset-date=Last+30+days"), url
    url, _ = tt_topads_url("ID", period="7", keyword="AI song")
    assert url == ("https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en"
                   "?region=ID&period=7&keyword=AI+song"), url
    url, _ = tt_ccl_url("DE", advertiser="Nike")
    assert url == ("https://library.tiktok.com/ads?region=DE&adv_name=Nike"
                   "&sort_type=last_shown_date%2Cdesc"), url
    # 非 DSA 法域必须报错而不是生成无效链接
    for bad_call in (lambda: tt_ccl_url("ID", "Nike"), lambda: apple_adrepo_url("ID")):
        try:
            bad_call()
            raise AssertionError("非 DSA 法域应报错")
        except ValueError:
            pass
    assert apple_adrepo_url("DE")[0] == "https://adrepository.apple.com/"
    url, _ = appstore_search_url("US", "AI chatbot")
    assert url == "https://apps.apple.com/us/search?term=AI+chatbot", url
    assert appstore_chart_url("GB")[0] == "https://apps.apple.com/gb/charts/iphone"
    url, _ = itunes_search_url("AI chat", "ID")
    assert url == "https://itunes.apple.com/search?term=AI+chat&country=ID&entity=software", url
    url, _ = gplay_search_url("AI chat", "ID")
    assert url == "https://play.google.com/store/search?q=AI+chat&c=apps&gl=ID", url
    url, _ = gg_suggest_url("US", "ai companion")
    assert url == "https://www.google.com/search?q=ai+companion&gl=US", url
    url, _ = gtrends_web_url(["AI song", "lagu ai"], "ID")
    assert url == ("https://trends.google.com/trends/explore?date=now+7-d&geo=ID"
                   "&q=AI+song%2Clagu+ai"), url
    plan = build_plan(["ID", "DE"], ["mureka.ai"], ["Mureka"], ["lagu AI"])
    surfaces = {r["surface"] for r in plan}
    # ID 非欧盟不应出现 ccl/adrepo，DE 欧盟应出现
    id_s = {r["surface"] for r in plan if r["market"] == "ID"}
    de_s = {r["surface"] for r in plan if r["market"] == "DE"}
    assert "tt-ccl" not in id_s and "apple-adrepo" not in id_s, id_s
    assert {"tt-ccl", "apple-adrepo"} <= de_s, de_s
    assert {"gg-transparency", "tt-topads", "appstore-search",
            "itunes-search", "gplay-search", "gg-suggest", "gtrends-web",
            "appstore-chart"} <= surfaces, surfaces
    # 零第三方：计划中不得出现任何第三方商业数据平台 source
    assert not (surfaces & {"similarweb", "sensortower", "crunchbase", "builtwith"}), surfaces
    # 去重：同 app 名同时在 apps 与 keyword 派生的 tt-topads 只保留一条/市场
    dup_plan = build_plan(["ID"], [], ["Mureka"], ["Mureka"])
    n = sum(1 for r in dup_plan if r["surface"] == "tt-topads")
    assert n == 1, n
    print("selftest OK：GG透明度/TT TopAds/TT CCL法域校验/Apple库/AppStore巡查/iTunes接口/"
          "搜索词/计划去重与DSA法域分流均通过，且零第三方商业数据源")


def main(argv=None):
    args = parse_args(argv)
    if args.selftest:
        selftest()
        return 0

    if args.plan:
        tokens = [t.strip() for t in args.markets.split(",") if t.strip()] or ["ALL"]
        markets = normalize_markets(tokens)
        rows = build_plan(markets, args.domain, args.app, args.keyword)
    else:
        if not args.source:
            raise ValueError("单入口模式需要 --source，或改用 --plan 批量生成")
        market = normalize_markets([args.market])[0]
        kw = args.keyword[0] if args.keyword else None
        app = args.app[0] if args.app else kw
        domain = args.domain[0] if args.domain else None
        s = args.source
        if s == "gg-transparency":
            url, note = gg_transparency_url(market, domain=domain, text=app, preset_date=args.preset_date)
        elif s == "tt-topads":
            url, note = tt_topads_url(market, period=args.period, keyword=kw)
        elif s == "tt-ccl":
            url, note = tt_ccl_url(market, advertiser=args.advertiser or app)
        elif s == "apple-adrepo":
            url, note = apple_adrepo_url(market)
        elif s == "appstore-search":
            url, note = appstore_search_url(market, kw)
        elif s == "appstore-chart":
            url, note = appstore_chart_url(market)
        elif s == "itunes-search":
            url, note = itunes_search_url(kw, market)
        elif s == "gplay-search":
            url, note = gplay_search_url(kw, market)
        elif s == "gg-suggest":
            url, note = gg_suggest_url(market, kw)
        else:  # gtrends-web
            url, note = gtrends_web_url(args.keyword or [kw], market)
        rows = [{"surface": s, "market": market, "query": kw or app or domain or "-",
                 "period": "7d/30d", "url": url, "note": note}]

    text = render(rows, args.format)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"已写入 {args.out}（{len(rows)} 条）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
