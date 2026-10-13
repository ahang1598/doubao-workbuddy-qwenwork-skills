#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原生内容平台近 7 天「平台原生内容」热点探查链接生成器（无第三方依赖、免登录、零接管）。

设计口径（global-ad-creative-advisor Skill，P3）：
- YouTube / TikTok / Facebook / Instagram 的热点一律按**平台原生内容**搜索分析，不走广告后台口径，
  不依赖任何需要登录的广告产品，也不要求用户接管登录、不使用第三方镜像站。
- 时间窗固定「近 7 天」，目标是看目标市场用户这一周在刷什么、搜什么，转化成本周可落地的创意。

生成的入口：
  tt-search       TikTok 站内原生搜索（视频流；页内切「视频」、按「获赞最多」，按卡片日期筛近 7 天）
  tt-tag          TikTok 话题页（#hashtag 原生聚合流）
  yt-search       YouTube 原生搜索，已内置「本周上传 + 按播放量排序」的确定性筛选参数（2026-09 实测）
  yt-trending     YouTube 某地区 Trending 热门榜（自然内容风向，免登录）
  gtrends-yt      Google Trends 限定 YouTube 搜索、近 7 天、按地区（走势 + Rising 上升词）
  gtrends-web     Google Trends 网页搜索、近 7 天、按地区（需求风向 + Rising 上升词）
  fb-page         Facebook 公开主页视频/Reels 栏（FB 无公开热榜、不做 Watch 主动搜索，只靠已知账号直链）
  ig-profile      Instagram 公开账号主页（看近 7 天 Reels/帖子，登录墙频繁，能看多少看多少）
  ig-reel         Instagram 单条 Reel/帖子直链（接受完整链接或 shortcode）
  gg-transparency 【可选·同类型产品付费补充，非原生热点】Google Ads 透明度中心（P2 主载体在 build_openintel_urls.py）

注意：Facebook Watch 关键词搜索、Instagram Explore/标签页对未登录关闭，按 SKILL.md 与 references/06
红线「不做 Watch 主动搜索、不做标签/Explore 主动探查」，本脚本不提供 fb-watch / ig-tag 入口；
FB/IG 只接受已知公开主页或单条固定直链（fb-page / ig-profile / ig-reel）。

市场代码复用 build_adlibrary_url.py 的区域预设/中文名表。

示例:
  python3 build_trend_urls.py --source tt-search --market ID --keyword "lagu AI"
  python3 build_trend_urls.py --source yt-search --market ID --keyword "lagu AI"
  python3 build_trend_urls.py --source fb-page --account nike
  python3 build_trend_urls.py --source ig-profile --account nike
  # 一次性生成某市场全部原生热点侦察链接，导出 tsv
  python3 build_trend_urls.py --plan --markets ID \
      --keyword "lagu AI" --keyword "AI cover" --hashtag fyp --hashtag laguai \
      --fb-account lokalmedia --ig-account lokal.kreator \
      --domain suno.com --format tsv --out weekly_trend_plan.tsv

  python3 build_trend_urls.py --selftest
"""
import argparse
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_adlibrary_url import normalize_markets  # noqa: E402  复用市场表与区域预设

TT_SEARCH_BASE = "https://www.tiktok.com/search"
TT_TAG_BASE = "https://www.tiktok.com/tag"
YT_TRENDING_BASE = "https://www.youtube.com/feed/trending"
YT_SEARCH_BASE = "https://www.youtube.com/results"
GTRENDS_EXPLORE = "https://trends.google.com/trends/explore"
GG_TRANSPARENCY_BASE = "https://adstransparency.google.com/"
FB_BASE = "https://www.facebook.com"
IG_BASE = "https://www.instagram.com"

# YouTube「上传日期=本周(This week) + 排序=按播放量(View count)」组合筛选的确定性 sp 值。
# 2026-09 在 youtube.com 页面依次点选两级筛选后从最终 URL 实测得到（原始值末尾的 = 由 urlencode 编码为 %3D）。
YT_SP_WEEK_VIEWS = "CAMSBAgDEAE="
GG_DATE_PRESETS = {"Last 7 days", "Last 30 days", "Today", "Yesterday", "Any time"}

SOURCES = ["tt-search", "tt-tag", "yt-search", "yt-trending", "gtrends-yt", "gtrends-web",
           "fb-page", "ig-profile", "ig-reel", "gg-transparency"]
# 红线：fb-watch（FB Watch 主动搜索）、ig-tag（IG 标签/Explore 主动探查）对未登录关闭，
# 按 SKILL.md / references/06 不主动探查，禁止加入 SOURCES 或 build_plan 默认产出。
BLOCKED_PROBES = ["fb-watch", "ig-tag"]


def _region_or_none(market):
    """ALL/全球 -> None（不强制地区参数；TikTok/FB/IG 无地区 URL 参数，地区由本地语言关键词与网络环境决定）。"""
    return None if market == "ALL" else market


def tt_search_url(keyword):
    """TikTok 站内原生搜索。免登录可见视频卡片（作者/点赞/日期/话题标签）。"""
    if not keyword:
        raise ValueError("tt-search 需要 --keyword")
    url = TT_SEARCH_BASE + "?" + urllib.parse.urlencode([("q", keyword)])
    note = ("原生内容非广告：页内切「视频」Tab、排序选「获赞最多」；按卡片日期(M-D/X天前)人工筛近7天；"
            "TikTok 无地区URL参数，用本地语言关键词锁定目标市场内容")
    return url, note


def _hashtag_slug(tag):
    t = tag.lstrip("#").strip()
    # 话题不允许空格；保留各语言文字与数字，去掉空格和标点；ASCII 部分小写（话题本身不区分大小写）
    t = re.sub(r"[\s\-\._]+", "", t)
    return t.lower()


def tt_tag_url(hashtag):
    """TikTok 话题页原生聚合流。"""
    if not hashtag:
        raise ValueError("tt-tag 需要 --hashtag 或由 --keyword 派生")
    slug = _hashtag_slug(hashtag)
    if not slug:
        raise ValueError(f"话题无法从 {hashtag!r} 归一化，请显式传 --hashtag")
    url = TT_TAG_BASE + "/" + urllib.parse.quote(slug)
    note = "原生话题页：看话题总播放量、置顶与高赞视频形式/BGM；按视频发布日期筛近7天，免登录"
    return url, note


def yt_search_url(keyword, market):
    """YouTube 原生搜索，确定性带上「本周 + 按播放量」筛选。"""
    if not keyword:
        raise ValueError("yt-search 需要 --keyword")
    pairs = [("search_query", keyword), ("sp", YT_SP_WEEK_VIEWS)]
    region = _region_or_none(market)
    if region:
        pairs.append(("gl", region))
    url = YT_SEARCH_BASE + "?" + urllib.parse.urlencode(pairs)
    note = "已内置「本周上传+按播放量」；Shorts 内容在页内点「Shorts」Tab；播放量/发布时间为页面显示值，免登录"
    return url, note


def yt_trending_url(market, hl="en"):
    pairs = []
    region = _region_or_none(market)
    if region:
        pairs.append(("gl", region))
    pairs.append(("hl", hl))
    return YT_TRENDING_BASE + "?" + urllib.parse.urlencode(pairs)


def _gtrends_url(keywords, market, gprop=None):
    if not keywords:
        raise ValueError("Google Trends 至少需要一个关键词")
    pairs = [("date", "now 7-d")]
    region = _region_or_none(market)
    if region:
        pairs.append(("geo", region))
    if gprop:
        pairs.append(("gprop", gprop))
    pairs.append(("q", ",".join(keywords)))
    note = "看「近7天」走势曲线与「Rising/上升」相关查询词；脚本直连可能 429，用浏览器打开即可，免登录"
    return GTRENDS_EXPLORE + "?" + urllib.parse.urlencode(pairs), note


def gtrends_yt_url(keywords, market):
    return _gtrends_url(keywords, market, gprop="youtube")


def gtrends_web_url(keywords, market):
    url, _ = _gtrends_url(keywords, market, gprop=None)
    return url, "网页搜索需求风向（近7天）+ Rising 上升词；0-100 相对指数非搜索量，免登录"


def _account_slug(account):
    """把主页 URL / @handle / 纯 slug 归一化为账号路径段。"""
    if not account:
        raise ValueError("缺少账号")
    s = account.strip()
    s = re.sub(r"^https?://(www\.)?(facebook|instagram)\.com/", "", s)
    s = s.lstrip("@").strip("/")
    # 去掉 /reels /videos 等后缀与查询串，只保留账号主体
    s = re.split(r"[/?#]", s)[0]
    if not s:
        raise ValueError(f"账号无法从 {account!r} 归一化")
    return s


def fb_page_url(account):
    slug = _account_slug(account)
    url = f"{FB_BASE}/{urllib.parse.quote(slug)}/videos"
    note = ("FB原生(弱发现)：打开公开主页「视频/Reels」栏看近7天公开视频；FB无公开热榜；"
            "要求登录即停不登录，改跨平台外溢/通用搜索补证")
    return url, note


def ig_profile_url(account):
    slug = _account_slug(account)
    url = f"{IG_BASE}/{urllib.parse.quote(slug)}/"
    note = ("IG原生(弱发现)：公开主页看近7天 Reels/帖子的题材/封面/互动量级；Explore/搜索对未登录基本关闭，"
            "要求登录即停；不使用 Picuki 等第三方镜像")
    return url, note


def ig_reel_url(reel):
    if not reel:
        raise ValueError("ig-reel 需要单条链接或 shortcode")
    r = reel.strip()
    if r.startswith("http"):
        return r, "IG 单条公开 Reel/帖子直链（来自账号简介/全网搜索/P1已知材料），要求登录即停"
    code = r.strip("/")
    return f"{IG_BASE}/reel/{urllib.parse.quote(code)}/", "IG 单条 Reel（shortcode 生成），要求登录即停"


def gg_transparency_url(market, domain=None, text=None, preset_date="Last 7 days"):
    """【可选】同类型产品付费动作补充，不属于原生热点。"""
    if preset_date not in GG_DATE_PRESETS:
        raise ValueError(f"日期预设仅支持 {sorted(GG_DATE_PRESETS)}")
    if not domain and not text:
        raise ValueError("透明度中心必须提供 --domain（优先）或 --advertiser（广告主名）")
    pairs = [("region", market if market != "ALL" else "anywhere")]
    if domain:
        pairs.append(("domain", domain.strip()))
    if text:
        pairs.append(("text", text.strip()))
    pairs.append(("preset-date", preset_date))
    note = ("同类型产品付费补充(非原生热点)：页内选 Platform=YouTube、Format=Video；优先 domain 覆盖同域名全部广告账户；"
            "商业广告无曝光/花费数值，新广告延迟48-72h，免登录")
    return GG_TRANSPARENCY_BASE + "?" + urllib.parse.urlencode(pairs), note


def build_plan(markets, domains, texts, keywords, hashtags, fb_accounts=(), ig_accounts=()):
    """生成整周「原生热点」侦察计划：每市场 × 各原生入口；同类型产品域名走可选透明度中心补充。"""
    rows = []

    def add(surface, market, query, url, note, period="7d"):
        rows.append({"surface": surface, "market": market, "query": query,
                     "period": period, "url": url, "note": note})

    for market in markets:
        add("yt-trending", market, "-", yt_trending_url(market),
            "地区自然热门榜，免登录；若被同意页/首页重定向则改用 yt-search 补")
        if keywords:
            gt = gtrends_yt_url(keywords, market)
            add("gtrends-yt", market, ",".join(keywords), *gt)
            gw = gtrends_web_url(keywords, market)
            add("gtrends-web", market, ",".join(keywords), *gw)
        tags = list(hashtags)
        for kw in keywords:
            add("tt-search", market, kw, *tt_search_url(kw))
            tags.append(kw)  # 同时为每个关键词派生一个话题页
            add("yt-search", market, kw, *yt_search_url(kw, market))
            # FB 不做 Watch 主动搜索（红线），只通过下方 fb-account 已知公开主页直链采集
        for tag in dict.fromkeys(tags):  # 去重保序
            # TT 话题页允许开放发现；IG 标签/Explore 对未登录关闭、不主动探查（红线），不生成 ig-tag
            add("tt-tag", market, "#" + _hashtag_slug(tag), *tt_tag_url(tag))
        for acc in fb_accounts:
            add("fb-page", market, acc, *fb_page_url(acc))
        for acc in ig_accounts:
            add("ig-profile", market, acc, *ig_profile_url(acc))
        for domain in domains:
            add("gg-transparency", market, domain, *gg_transparency_url(market, domain=domain))
        for name in texts:
            add("gg-transparency", market, name, *gg_transparency_url(market, text=name))
    return rows


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="原生内容平台近一周平台原生内容热点探查链接生成器（免登录）")
    p.add_argument("--source", choices=SOURCES, help="单个入口；批量侦察用 --plan")
    p.add_argument("--plan", action="store_true", help="按市场一次性生成全部原生入口的侦察计划")
    p.add_argument("--market", default="ALL", help="单入口市场：ISO 代码/中文名/区域预设，默认 ALL")
    p.add_argument("--markets", default="", help="计划模式：逗号分隔多个市场")
    p.add_argument("--keyword", action="append", default=[], help="原生搜索关键词，可重复（英/本地语言）")
    p.add_argument("--keywords-file", help="每行一个关键词")
    p.add_argument("--hashtag", action="append", default=[], help="TikTok/IG 话题（不带#也可），可重复")
    p.add_argument("--fb-account", action="append", default=[], help="Facebook 公开主页（slug/@/URL），可重复")
    p.add_argument("--ig-account", action="append", default=[], help="Instagram 公开账号（slug/@/URL），可重复")
    p.add_argument("--account", help="单入口 fb-page/ig-profile 的账号")
    p.add_argument("--reel", help="ig-reel 的单条链接或 shortcode")
    p.add_argument("--domain", action="append", default=[], help="【可选】同类型产品域名，用于透明度中心付费补充")
    p.add_argument("--advertiser", action="append", default=[], help="【可选】同类型产品广告主名（无域名时）")
    p.add_argument("--format", choices=["pretty", "tsv", "json"], default="pretty")
    p.add_argument("--out", help="结果写入文件")
    p.add_argument("--selftest", action="store_true")
    return p.parse_args(argv)


def _read_keywords_file(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def render(rows, fmt):
    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2)
    if fmt == "tsv":
        head = "surface\tmarket\tquery\tperiod\turl\tnote"
        body = ["\t".join(str(r.get(k, "")) for k in
                         ["surface", "market", "query", "period", "url", "note"]) for r in rows]
        return "\n".join([head] + body)
    lines = [f"[{i+1}] {r['surface']} | {r['market']} | {r['query']} | {r['period']}\n    {r['url']}"
             + (f"\n    备注: {r['note']}" if r.get("note") else "") for i, r in enumerate(rows)]
    return f"共 {len(rows)} 条：\n" + "\n".join(lines)


def selftest():
    url, note = tt_search_url("lagu AI")
    assert url == "https://www.tiktok.com/search?q=lagu+AI", url
    assert "免登录" in note or "原生" in note
    url, _ = tt_tag_url("#Lagu AI")
    assert url == "https://www.tiktok.com/tag/laguai", url
    assert _hashtag_slug("FYP") == "fyp"
    url, _ = yt_search_url("lagu AI", "ID")
    assert url == ("https://www.youtube.com/results?search_query=lagu+AI"
                   "&sp=CAMSBAgDEAE%3D&gl=ID"), url
    assert yt_trending_url("US") == "https://www.youtube.com/feed/trending?gl=US&hl=en"
    url, _ = gtrends_yt_url(["AI chat", "chatgpt"], "US")
    assert url == ("https://trends.google.com/trends/explore?date=now+7-d&geo=US&gprop=youtube"
                   "&q=AI+chat%2Cchatgpt"), url
    url, _ = gtrends_web_url(["AI chat"], "US")
    assert url == ("https://trends.google.com/trends/explore?date=now+7-d&geo=US"
                   "&q=AI+chat"), url
    # Facebook / Instagram 仅已知公开固定直链（fb-page/ig-profile/ig-reel）
    assert fb_page_url("@nike")[0] == "https://www.facebook.com/nike/videos"
    assert fb_page_url("https://www.facebook.com/lokal.id/videos")[0] == \
        "https://www.facebook.com/lokal.id/videos"
    assert ig_profile_url("https://www.instagram.com/nike/")[0] == "https://www.instagram.com/nike/"
    assert ig_reel_url("Cabc123")[0] == "https://www.instagram.com/reel/Cabc123/"
    full = "https://www.instagram.com/reel/Cabc123/?igshid=xx"
    assert ig_reel_url(full)[0] == full
    assert _account_slug("@foo.bar/") == "foo.bar"
    url, _ = gg_transparency_url("US", domain="replika.com")
    assert url == ("https://adstransparency.google.com/?region=US&domain=replika.com"
                   "&preset-date=Last+7+days"), url
    assert gg_transparency_url("ALL", text="Acme Inc")[0].startswith(
        "https://adstransparency.google.com/?region=anywhere&text=Acme+Inc")
    plan = build_plan(["ID"], ["suno.com"], [], ["lagu AI"], ["fyp"],
                      fb_accounts=["lokalmedia"], ig_accounts=["lokal.kreator"])
    surfaces = {r["surface"] for r in plan}
    assert {"tt-search", "tt-tag", "yt-search", "yt-trending", "gtrends-yt", "gtrends-web",
            "fb-page", "ig-profile", "gg-transparency"} <= surfaces, surfaces
    # 红线反向断言：plan 默认产出与 SOURCES 均不得含 FB Watch 主动搜索 / IG 标签主动探查
    assert not (surfaces & set(BLOCKED_PROBES)), surfaces
    assert not (set(SOURCES) & set(BLOCKED_PROBES)), SOURCES
    # 关键词会派生同名话题，且显式 hashtag 去重
    tag_queries = [r["query"] for r in plan if r["surface"] == "tt-tag"]
    assert tag_queries.count("#laguai") == 1 and "#fyp" in tag_queries, tag_queries
    # 计划里不得再出现任何 Creative Center / Top Ads 广告后台链接（P3 只走原生）
    assert all("creativecenter" not in r["url"] and "topads" not in r["url"] for r in plan)
    # YT「本周+播放量」sp 常量必须保持 Base64URL 形态；YouTube 更换编码时按 references/06 第 2.1 节重取
    assert re.fullmatch(r"[A-Za-z0-9_\-]+={0,2}", YT_SP_WEEK_VIEWS), YT_SP_WEEK_VIEWS
    bad = False
    try:
        gg_transparency_url("US", preset_date="Last 999 days")
    except ValueError:
        bad = True
    assert bad
    print("selftest OK：TT/YT/FB/IG 原生入口(免登录,仅已知直链)、YT本周+播放量筛选、web/youtube Trends、"
          "话题派生去重、透明度中心可选补充、7天窗口、计划模式与参数校验均通过；"
          "fb-watch/ig-tag 红线反向断言通过（不主动探查封闭入口）")


def main(argv=None):
    args = parse_args(argv)
    if args.selftest:
        selftest()
        return 0

    if args.keywords_file:
        args.keyword += _read_keywords_file(args.keywords_file)

    if args.plan:
        tokens = [t.strip() for t in args.markets.split(",") if t.strip()] or ["ALL"]
        markets = normalize_markets(tokens)
        rows = build_plan(markets, args.domain, args.advertiser, args.keyword,
                          args.hashtag, args.fb_account, args.ig_account)
    else:
        if not args.source:
            raise ValueError("单入口模式需要 --source，或改用 --plan 批量生成")
        market = normalize_markets([args.market])[0]
        kw = args.keyword[0] if args.keyword else None
        s = args.source
        if s == "tt-search":
            url, note = tt_search_url(kw)
            rows = [{"surface": s, "market": market, "query": kw, "period": "7d",
                     "url": url, "note": note}]
        elif s == "tt-tag":
            tag = args.hashtag[0] if args.hashtag else kw
            url, note = tt_tag_url(tag)
            rows = [{"surface": s, "market": market, "query": "#" + _hashtag_slug(tag),
                     "period": "7d", "url": url, "note": note}]
        elif s == "yt-search":
            url, note = yt_search_url(kw, market)
            rows = [{"surface": s, "market": market, "query": kw, "period": "7d",
                     "url": url, "note": note}]
        elif s == "yt-trending":
            rows = [{"surface": s, "market": market, "query": "-", "period": "7d",
                     "url": yt_trending_url(market), "note": ""}]
        elif s == "gtrends-yt":
            if not args.keyword:
                raise ValueError("gtrends-yt 需要 --keyword（可多个）")
            url, note = gtrends_yt_url(args.keyword, market)
            rows = [{"surface": s, "market": market, "query": ",".join(args.keyword),
                     "period": "7d", "url": url, "note": note}]
        elif s == "gtrends-web":
            if not args.keyword:
                raise ValueError("gtrends-web 需要 --keyword（可多个）")
            url, note = gtrends_web_url(args.keyword, market)
            rows = [{"surface": s, "market": market, "query": ",".join(args.keyword),
                     "period": "7d", "url": url, "note": note}]
        elif s == "fb-page":
            url, note = fb_page_url(args.account)
            rows = [{"surface": s, "market": market, "query": args.account, "period": "7d",
                     "url": url, "note": note}]
        elif s == "ig-profile":
            url, note = ig_profile_url(args.account)
            rows = [{"surface": s, "market": market, "query": args.account, "period": "7d",
                     "url": url, "note": note}]
        elif s == "ig-reel":
            url, note = ig_reel_url(args.reel)
            rows = [{"surface": s, "market": market, "query": args.reel, "period": "7d",
                     "url": url, "note": note}]
        else:  # gg-transparency
            url, note = gg_transparency_url(market, domain=(args.domain[0] if args.domain else None),
                                            text=(args.advertiser[0] if args.advertiser else None))
            rows = [{"surface": s, "market": market,
                     "query": (args.domain or args.advertiser or ["-"])[0],
                     "period": "7d", "url": url, "note": note}]

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
