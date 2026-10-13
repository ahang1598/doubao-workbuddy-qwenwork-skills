#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Meta Ad Library 检索链接生成器（无第三方依赖）。

为 global-ad-creative-advisor Skill 确定性地生成 Meta(Facebook) Ad Library 检索 URL，
支持「关键词 × 市场 × 媒体类型」批量生成，默认按总展示量(total_impressions)降序，
用于发现同类型产品的高展示优势素材。

示例:
  # 单个关键词，全球，全部媒体类型（与广告库前台默认排序一致）
  python3 build_adlibrary_url.py --keyword ChatGPT

  # 美国市场、仅视频、投放中、英语
  python3 build_adlibrary_url.py --keyword "AI chatbot" --markets US --media-types video --languages en

  # 批量：多个词 × 东南亚区域 × 视频，导出 tsv 供逐条采集
  python3 build_adlibrary_url.py --keyword ChatGPT --keyword Replika --region SEA \
      --media-types video --format tsv --out adlibrary_urls.tsv

  # 从文件读关键词（每行一个），指定多个市场
  python3 build_adlibrary_url.py --keywords-file words.txt --markets US,BR,JP --format json

  # 自检（回归校验默认 URL 与前台一致）
  python3 build_adlibrary_url.py --selftest
"""
import argparse
import json
import sys
import urllib.parse

BASE = "https://www.facebook.com/ads/library/"

ACTIVE_STATUS = {"active", "inactive", "all"}
MEDIA_TYPES = {"all", "image", "video", "meme", "none"}
SEARCH_TYPES = {"keyword_unordered", "keyword_exact_phrase", "page"}
SORT_MODES = {"total_impressions", "relevancy_monthly_grouped"}
DIRECTIONS = {"asc", "desc"}
PLATFORMS = {"facebook", "instagram", "messenger", "audience_network", "whatsapp"}

# 区域预设：市场分群与 references/02-market-competitors.md 保持一致
REGIONS = {
    "NA": ["US", "CA"],
    "EU5": ["GB", "DE", "FR", "IT", "ES"],
    "SEA": ["SG", "MY", "TH", "VN", "ID", "PH"],
    "LATAM": ["BR", "MX", "AR", "CO", "CL"],
    "NEASIA": ["JP", "KR", "TW", "HK"],
    "MENA": ["SA", "AE", "EG", "KW", "QA"],
    "OCEANIA": ["AU", "NZ"],
    "SOUTH_ASIA": ["IN", "PK", "BD"],
    "SSA": ["NG", "ZA", "KE"],
}

# 常见出海市场中文名 -> ISO 代码（代码本身也可直接传入）
COUNTRY_NAMES = {
    "全球": "ALL", "全部": "ALL",
    "美国": "US", "加拿大": "CA",
    "英国": "GB", "德国": "DE", "法国": "FR", "意大利": "IT", "西班牙": "ES",
    "新加坡": "SG", "马来西亚": "MY", "泰国": "TH", "越南": "VN",
    "印尼": "ID", "印度尼西亚": "ID", "菲律宾": "PH",
    "巴西": "BR", "墨西哥": "MX", "阿根廷": "AR", "哥伦比亚": "CO", "智利": "CL",
    "日本": "JP", "韩国": "KR", "台湾": "TW", "香港": "HK",
    "沙特": "SA", "阿联酋": "AE", "埃及": "EG", "科威特": "KW", "卡塔尔": "QA",
    "澳大利亚": "AU", "新西兰": "NZ",
    "印度": "IN", "巴基斯坦": "PK", "孟加拉": "BD",
    "尼日利亚": "NG", "南非": "ZA", "肯尼亚": "KE",
}


def build_url(keyword, country="ALL", media_type="all", active_status="active",
              search_type="keyword_unordered", sort_mode="total_impressions",
              sort_direction="desc", platforms=None, languages=None,
              is_targeted_country=False, ad_type="all"):
    """生成单个检索 URL。参数取值见模块头部常量与 Ad Library 前台。"""
    if active_status not in ACTIVE_STATUS:
        raise ValueError(f"active_status 仅支持 {sorted(ACTIVE_STATUS)}")
    if media_type not in MEDIA_TYPES:
        raise ValueError(f"media_type 仅支持 {sorted(MEDIA_TYPES)}")
    if search_type not in SEARCH_TYPES:
        raise ValueError(f"search_type 仅支持 {sorted(SEARCH_TYPES)}")
    if sort_mode not in SORT_MODES:
        raise ValueError(f"sort_mode 仅支持 {sorted(SORT_MODES)}")
    if sort_direction not in DIRECTIONS:
        raise ValueError(f"sort_direction 仅支持 {sorted(DIRECTIONS)}")
    platforms = [p.lower() for p in (platforms or [])]
    bad = [p for p in platforms if p not in PLATFORMS]
    if bad:
        raise ValueError(f"未知版位 {bad}，可选 {sorted(PLATFORMS)}")
    if not keyword or not str(keyword).strip():
        raise ValueError("keyword 不能为空")

    pairs = [
        ("active_status", active_status),
        ("ad_type", ad_type),
        ("country", country),
        ("is_targeted_country", str(bool(is_targeted_country)).lower()),
        ("media_type", media_type),
        ("q", str(keyword).strip()),
        ("search_type", search_type),
        ("sort_data[mode]", sort_mode),
        ("sort_data[direction]", sort_direction),
    ]
    for i, p in enumerate(platforms):
        pairs.append((f"publisher_platforms[{i}]", p))
    for i, lang in enumerate(languages or []):
        pairs.append((f"languages[{i}]", lang.lower()))
    return BASE + "?" + urllib.parse.urlencode(pairs)


def normalize_markets(tokens):
    """把市场 token（中文名/ISO 代码/区域预设）展开为去重的 ISO 代码列表。"""
    out = []
    for raw in tokens:
        t = raw.strip()
        if not t:
            continue
        if t.upper() in REGIONS:
            for code in REGIONS[t.upper()]:
                if code not in out:
                    out.append(code)
        elif t in COUNTRY_NAMES:
            code = COUNTRY_NAMES[t]
            if code not in out:
                out.append(code)
        else:
            code = t.upper()
            if code not in out:
                out.append(code)
    return out or ["ALL"]


def split_csv(value):
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Meta Ad Library 检索链接生成器")
    p.add_argument("--keyword", action="append", default=[], help="检索关键词，可重复传入多个")
    p.add_argument("--keywords-file", help="文本文件，每行一个关键词（# 开头为注释）")
    p.add_argument("--markets", default="", help="逗号分隔的市场：中文名/ISO 代码/ALL，默认 ALL")
    p.add_argument("--region", action="append", default=[], help="区域预设，可重复：NA/EU5/SEA/LATAM/NEASIA/MENA/OCEANIA/SOUTH_ASIA/SSA")
    p.add_argument("--media-types", default="all", help="逗号分隔：all/image/video/meme/none，默认 all")
    p.add_argument("--active-status", default="active", choices=sorted(ACTIVE_STATUS))
    p.add_argument("--search-type", default="keyword_unordered", choices=sorted(SEARCH_TYPES))
    p.add_argument("--platforms", default="", help="逗号分隔版位：facebook/instagram/messenger/audience_network/whatsapp")
    p.add_argument("--languages", default="", help="逗号分隔 ISO 639-1 语言码，如 en,es")
    p.add_argument("--targeted-country", action="store_true", help="仅看定向到所选国家的广告（is_targeted_country=true）")
    p.add_argument("--format", choices=["pretty", "tsv", "json"], default="pretty")
    p.add_argument("--out", help="把结果写入文件（pretty/tsv/json 原样写入）")
    p.add_argument("--selftest", action="store_true", help="运行自检后退出")
    return p.parse_args(argv)


def collect_rows(args):
    keywords = list(args.keyword)
    if args.keywords_file:
        with open(args.keywords_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    keywords.append(line)
    if not keywords:
        raise ValueError("至少需要一个 --keyword 或 --keywords-file")

    market_tokens = split_csv(args.markets) + args.region
    markets = normalize_markets(market_tokens)
    media_types = split_csv(args.media_types) or ["all"]
    for mt in media_types:
        if mt not in MEDIA_TYPES:
            raise ValueError(f"media_type '{mt}' 非法，可选 {sorted(MEDIA_TYPES)}")
    platforms = split_csv(args.platforms)
    languages = split_csv(args.languages)

    rows = []
    for kw in keywords:
        for market in markets:
            for mt in media_types:
                url = build_url(
                    kw, country=market, media_type=mt,
                    active_status=args.active_status, search_type=args.search_type,
                    platforms=platforms, languages=languages,
                    is_targeted_country=args.targeted_country,
                )
                rows.append({"keyword": kw, "country": market, "media_type": mt, "url": url})
    return rows


def render(rows, fmt):
    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2)
    if fmt == "tsv":
        lines = ["keyword\tcountry\tmedia_type\turl"]
        lines += [f"{r['keyword']}\t{r['country']}\t{r['media_type']}\t{r['url']}" for r in rows]
        return "\n".join(lines)
    lines = [f"[{i+1}] {r['keyword']} | {r['country']} | {r['media_type']}\n    {r['url']}"
             for i, r in enumerate(rows)]
    return f"共 {len(rows)} 条检索链接：\n" + "\n".join(lines)


def selftest():
    expected = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
                "&country=ALL&is_targeted_country=false&media_type=all&q=ChatGPT"
                "&search_type=keyword_unordered&sort_data%5Bmode%5D=total_impressions"
                "&sort_data%5Bdirection%5D=desc")
    got = build_url("ChatGPT")
    assert got == expected, f"默认 URL 与前台不一致:\n{got}\n{expected}"

    us_video = build_url("AI chat", country="US", media_type="video", languages=["en"])
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(us_video).query)
    assert parsed["country"] == ["US"] and parsed["media_type"] == ["video"]
    assert parsed["languages[0]"] == ["en"] and parsed["sort_data[mode]"] == ["total_impressions"]

    sea = normalize_markets(["SEA"])
    assert sea == ["SG", "MY", "TH", "VN", "ID", "PH"]
    assert normalize_markets(["美国", "US", "巴西"]) == ["US", "BR"]

    rows = collect_rows(parse_args(["--keyword", "a", "--keyword", "b", "--markets", "US,BR",
                                    "--media-types", "video,image"]))
    assert len(rows) == 8, len(rows)  # 2 词 × 2 国 × 2 媒体
    # docstring 内示例命令必须可被 argparse 解析（防止示例参数名与实现漂移）
    parse_args(["--keyword", "AI chatbot", "--markets", "US",
                "--media-types", "video", "--languages", "en"])
    parse_args(["--keyword", "ChatGPT", "--keyword", "Replika", "--region", "SEA",
                "--media-types", "video", "--format", "tsv"])
    print("selftest OK：默认链接、筛选参数、区域展开、批量笛卡尔积、docstring 示例解析均通过")


def main(argv=None):
    args = parse_args(argv)
    if args.selftest:
        selftest()
        return 0
    rows = collect_rows(args)
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
    except Exception as e:  # 生成器面向 Agent 调用，错误信息直接可读
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
