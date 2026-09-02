#!/usr/bin/env python3
"""
keyword_checker.py — Amazon Listing 关键词埋词检查 & 商标侵权扫描

用法：
  # 基础埋词检查（交互式输入）
  python3 keyword_checker.py

  # 从文件读取（listing_file: JSON, keywords_file: 每行一个关键词）
  python3 keyword_checker.py --listing listing.json --keywords keywords.txt

  # 仅做商标侵权扫描
  python3 keyword_checker.py --listing listing.json --mode trademark

  # 输出 JSON 结果（供 SKILL.md 解析）
  python3 keyword_checker.py --listing listing.json --keywords keywords.txt --json

JSON 输入格式（listing.json）：
{
  "title": "...",
  "bullets": ["...", "...", "...", "...", "..."],
  "description": "...",
  "search_terms": "..."
}
"""

import re
import sys
import json
import argparse
from typing import Dict, List, Tuple

# ──────────────────────────────────────────────
# 高风险商标词库（常见被侵权品牌）
# 铺货卖家应避免在文案中出现这些词（兼容声明除外）
# ──────────────────────────────────────────────
TRADEMARK_BRANDS = {
    # 电子/科技
    "apple", "iphone", "ipad", "ipod", "airpods", "macbook", "imac", "apple watch",
    "samsung", "galaxy", "sony", "beats", "bose", "jbl", "anker",
    "nintendo", "playstation", "xbox", "microsoft",
    "google", "pixel", "fitbit", "garmin",
    # 服装/运动
    "nike", "adidas", "puma", "reebok", "under armour", "new balance",
    "gucci", "louis vuitton", "lv", "chanel", "prada", "versace", "hermes",
    "north face", "columbia", "patagonia", "arc'teryx",
    # 家居/厨具
    "instant pot", "vitamix", "kitchenaid", "cuisinart", "ninja", "keurig",
    "dyson", "roomba", "irobot", "shark", "bissell",
    "yeti", "hydroflask", "hydro flask", "stanley", "nalgene",
    # 工具/汽车
    "dewalt", "milwaukee", "makita", "bosch", "craftsman",
    # 医疗/健康
    "advil", "tylenol", "bandaid", "band-aid",
    # 影视/IP
    "disney", "marvel", "dc comics", "star wars", "harry potter",
    "pokemon", "minecraft", "fortnite", "roblox",
    "nfl", "nba", "fifa", "mlb",
}

# ──────────────────────────────────────────────
# 极限词 / 违禁词列表
# ──────────────────────────────────────────────
BANNED_PHRASES = [
    # 排名类
    "#1", "number one", "number 1", "best seller", "bestseller", "top seller",
    "best in class", "best ever", "world's best", "world best",
    "top rated", "highest rated", "most popular", "unbeatable", "unmatched",
    # 促销/CTA 类
    "free shipping", "fast shipping", "ships fast", "same day", "express delivery",
    "order now", "buy now", "add to cart", "click here", "shop now",
    "limited time", "while supplies last", "today only", "flash sale",
    "on sale", "discount", "special price", "buy 2 get 1",
    # 评价诱导
    "leave a review", "5 star", "five star", "rate us",
    # 医疗/功效
    "cures", "treats", "heals", "prevents disease", "fda approved",
    "clinically proven", "doctor recommended", "medically proven",
    # 绝对保证
    "100% guaranteed", "lifetime guarantee", "never fails", "zero defects",
]


def normalize(text: str) -> str:
    """转小写，去除多余空格，便于匹配。"""
    return re.sub(r'\s+', ' ', text.lower().strip())


def build_listing_text(listing: Dict) -> Dict[str, str]:
    """将 listing dict 拆分为各字段文本。"""
    fields = {
        "title": listing.get("title", ""),
        "bullets": " ".join(listing.get("bullets", [])),
        "description": listing.get("description", ""),
        "search_terms": listing.get("search_terms", ""),
    }
    fields["full_text"] = " ".join(fields.values())
    return fields


def check_keyword_coverage(keywords: List[str], listing_fields: Dict[str, str]) -> List[Dict]:
    """
    检查每个关键词在哪些字段中出现。
    返回：[{keyword, used, locations: [title/bullets/description/search_terms], risk}]
    """
    results = []
    full_text_norm = normalize(listing_fields["full_text"])

    for kw in keywords:
        kw_norm = normalize(kw)
        if not kw_norm:
            continue

        locations = []
        for field in ["title", "bullets", "description", "search_terms"]:
            field_norm = normalize(listing_fields[field])
            if kw_norm in field_norm:
                locations.append(field)

        used = len(locations) > 0
        results.append({
            "keyword": kw,
            "used": used,
            "locations": locations,
        })

    return results


def check_trademark_risk(listing_fields: Dict[str, str]) -> List[Dict]:
    """
    扫描文案中是否出现商标品牌词。
    返回：[{brand, field, context, risk_level, suggestion}]
    """
    issues = []
    full_norm = normalize(listing_fields["full_text"])

    for brand in sorted(TRADEMARK_BRANDS):
        if brand in full_norm:
            # 找出在哪个字段
            for field in ["title", "bullets", "description", "search_terms"]:
                field_norm = normalize(listing_fields[field])
                if brand in field_norm:
                    # 提取上下文（前后20字符）
                    idx = field_norm.find(brand)
                    start = max(0, idx - 20)
                    end = min(len(field_norm), idx + len(brand) + 20)
                    context = "..." + field_norm[start:end] + "..."

                    # 判断是否为合规兼容声明
                    is_compatible = any(
                        phrase in field_norm[max(0, idx - 30):idx + len(brand) + 30]
                        for phrase in ["compatible with", "fits", "for use with", "designed for", "works with"]
                    )

                    risk_level = "LOW (兼容声明)" if is_compatible else "HIGH (直接引用)"
                    suggestion = (
                        "✅ 已使用兼容声明，确认格式：'Compatible with [品牌]' 且注明非官方出品"
                        if is_compatible
                        else f"⚠️ 建议改为：'Compatible with {brand.title()}' 或删除品牌名，改用通用描述"
                    )

                    issues.append({
                        "brand": brand,
                        "field": field,
                        "context": context,
                        "risk_level": risk_level,
                        "suggestion": suggestion,
                    })

    return issues


def check_banned_phrases(listing_fields: Dict[str, str]) -> List[Dict]:
    """
    扫描违禁词/极限词。
    返回：[{phrase, field, context}]
    """
    issues = []
    for phrase in BANNED_PHRASES:
        for field in ["title", "bullets", "description", "search_terms"]:
            field_norm = normalize(listing_fields[field])
            if phrase in field_norm:
                idx = field_norm.find(phrase)
                start = max(0, idx - 20)
                end = min(len(field_norm), idx + len(phrase) + 20)
                context = "..." + field_norm[start:end] + "..."
                issues.append({
                    "phrase": phrase,
                    "field": field,
                    "context": context,
                })

    return issues


def check_search_terms_bytes(search_terms: str) -> Dict:
    """检查后台搜索词字节数。"""
    byte_count = len(search_terms.encode("utf-8"))
    return {
        "byte_count": byte_count,
        "limit": 500,
        "passed": byte_count <= 500,
        "overflow": max(0, byte_count - 500),
    }


def check_title_length(title: str, category_type: str = "general") -> Dict:
    """检查标题字符数。"""
    limit = 125 if category_type == "apparel" else 200
    char_count = len(title)
    return {
        "char_count": char_count,
        "limit": limit,
        "passed": char_count <= limit,
        "overflow": max(0, char_count - limit),
    }


def check_description_length(description: str) -> Dict:
    """检查产品描述字符数 ≤ 2000。"""
    char_count = len(description)
    return {
        "char_count": char_count,
        "limit": 2000,
        "passed": char_count <= 2000,
        "overflow": max(0, char_count - 2000),
    }


def check_search_terms_dedup(search_terms: str, title: str, bullets_text: str) -> Dict:
    """检查后台搜索词是否与标题/五点重复（重复词浪费字节配额）。"""
    st_words = set(normalize(search_terms).split())
    title_words = set(normalize(title).split())
    bullets_words = set(normalize(bullets_text).split())
    front_words = title_words | bullets_words
    duplicates = sorted(st_words & front_words)
    return {
        "duplicate_words": duplicates,
        "duplicate_count": len(duplicates),
        "passed": len(duplicates) == 0,
    }


def print_coverage_report(results: List[Dict]) -> None:
    used = [r for r in results if r["used"]]
    unused = [r for r in results if not r["used"]]

    print("\n" + "═" * 60)
    print("📊 关键词埋词检查报告")
    print("═" * 60)
    print(f"总计：{len(results)} 个关键词 | ✅ 已埋：{len(used)} 个 | ❌ 未埋：{len(unused)} 个")
    print(f"覆盖率：{len(used)/len(results)*100:.1f}%" if results else "")

    if used:
        print("\n✅ 已埋词（Used Keywords）")
        print("-" * 40)
        for r in used:
            locs = " + ".join(r["locations"])
            print(f"  ✓ {r['keyword']:<35} [{locs}]")

    if unused:
        print("\n❌ 未埋词（Unused Keywords）— 建议补充")
        print("-" * 40)
        for r in unused:
            print(f"  ✗ {r['keyword']}")


def print_trademark_report(issues: List[Dict]) -> None:
    if not issues:
        print("\n✅ 商标侵权检查：未发现高风险品牌词")
        return

    print("\n" + "═" * 60)
    print("⚠️  商标侵权扫描报告")
    print("═" * 60)
    high_risk = [i for i in issues if "HIGH" in i["risk_level"]]
    low_risk = [i for i in issues if "LOW" in i["risk_level"]]

    if high_risk:
        print(f"\n🔴 高风险（需立即处理）— {len(high_risk)} 处")
        for issue in high_risk:
            print(f"\n  品牌词: {issue['brand'].upper()}")
            print(f"  字段:   {issue['field']}")
            print(f"  上下文: {issue['context']}")
            print(f"  建议:   {issue['suggestion']}")

    if low_risk:
        print(f"\n🟡 低风险（兼容声明，确认格式）— {len(low_risk)} 处")
        for issue in low_risk:
            print(f"\n  品牌词: {issue['brand'].upper()}")
            print(f"  字段:   {issue['field']}")
            print(f"  上下文: {issue['context']}")
            print(f"  建议:   {issue['suggestion']}")


def print_banned_report(issues: List[Dict]) -> None:
    if not issues:
        print("\n✅ 违禁词检查：未发现违规表述")
        return

    print("\n" + "═" * 60)
    print("🚫 违禁词 / 极限词扫描报告")
    print("═" * 60)
    for issue in issues:
        print(f"\n  违禁词: \"{issue['phrase']}\"")
        print(f"  字段:   {issue['field']}")
        print(f"  上下文: {issue['context']}")


def run_check(listing: Dict, keywords: List[str] = None, mode: str = "full",
              category_type: str = "general", output_json: bool = False) -> Dict:
    fields = build_listing_text(listing)

    result = {
        "coverage": [],
        "trademark_issues": [],
        "banned_issues": [],
        "title_length": {},
        "description_length": {},
        "search_terms_bytes": {},
        "search_terms_dedup": {},
        "summary": {},
    }

    # 1. 埋词覆盖检查
    if keywords and mode in ("full", "coverage"):
        result["coverage"] = check_keyword_coverage(keywords, fields)

    # 2. 商标侵权扫描
    if mode in ("full", "trademark"):
        result["trademark_issues"] = check_trademark_risk(fields)

    # 3. 违禁词扫描
    if mode in ("full", "banned"):
        result["banned_issues"] = check_banned_phrases(fields)

    # 4. 标题字符数
    if listing.get("title"):
        result["title_length"] = check_title_length(listing["title"], category_type)

    # 5. 后台搜索词字节数
    if listing.get("search_terms"):
        result["search_terms_bytes"] = check_search_terms_bytes(listing["search_terms"])

    # 6. 产品描述字符数
    if listing.get("description"):
        result["description_length"] = check_description_length(listing["description"])

    # 7. 后台搜索词去重
    if listing.get("search_terms") and (listing.get("title") or listing.get("bullets")):
        bullets_text = " ".join(listing.get("bullets", []))
        result["search_terms_dedup"] = check_search_terms_dedup(
            listing["search_terms"], listing.get("title", ""), bullets_text
        )

    # 8. 汇总
    used_count = sum(1 for r in result["coverage"] if r["used"])
    total_kw = len(result["coverage"])
    result["summary"] = {
        "keyword_coverage_rate": f"{used_count}/{total_kw} ({used_count/total_kw*100:.1f}%)" if total_kw else "N/A",
        "trademark_high_risk_count": sum(1 for i in result["trademark_issues"] if "HIGH" in i["risk_level"]),
        "banned_phrase_count": len(result["banned_issues"]),
        "title_ok": result["title_length"].get("passed", True),
        "description_ok": result["description_length"].get("passed", True),
        "search_terms_ok": result["search_terms_bytes"].get("passed", True),
        "search_terms_dedup_ok": result["search_terms_dedup"].get("passed", True),
        "overall_pass": (
            sum(1 for i in result["trademark_issues"] if "HIGH" in i["risk_level"]) == 0
            and len(result["banned_issues"]) == 0
            and result["title_length"].get("passed", True)
            and result["description_length"].get("passed", True)
            and result["search_terms_bytes"].get("passed", True)
        ),
    }

    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["coverage"]:
            print_coverage_report(result["coverage"])
        print_trademark_report(result["trademark_issues"])
        print_banned_report(result["banned_issues"])

        # 字符/字节汇总
        print("\n" + "═" * 60)
        print("📏 字符/字节限制检查")
        print("═" * 60)
        tl = result["title_length"]
        if tl:
            status = "✅" if tl["passed"] else f"❌ 超出 {tl['overflow']} 字符"
            print(f"  标题字符数：{tl['char_count']} / {tl['limit']}  {status}")
        dl = result["description_length"]
        if dl:
            status = "✅" if dl["passed"] else f"❌ 超出 {dl['overflow']} 字符"
            print(f"  描述字符数：{dl['char_count']} / {dl['limit']}  {status}")
        st = result["search_terms_bytes"]
        if st:
            status = "✅" if st["passed"] else f"❌ 超出 {st['overflow']} 字节"
            print(f"  后台搜索词：{st['byte_count']} / {st['limit']} 字节  {status}")
        sd = result["search_terms_dedup"]
        if sd:
            if sd["passed"]:
                print(f"  搜索词去重：✅ 无重复词")
            else:
                print(f"  搜索词去重：⚠️ {sd['duplicate_count']} 个词与标题/五点重复")
                print(f"    重复词：{', '.join(sd['duplicate_words'][:20])}")

        # 总体结论
        print("\n" + "═" * 60)
        s = result["summary"]
        if s["overall_pass"]:
            print("🎉 总体结论：合规检查通过，无高风险问题")
        else:
            print("⛔ 总体结论：发现违规项，请处理后再上架")
            if s["trademark_high_risk_count"] > 0:
                print(f"   - 商标高风险：{s['trademark_high_risk_count']} 处（必须修复）")
            if s["banned_phrase_count"] > 0:
                print(f"   - 违禁词：{s['banned_phrase_count']} 处（必须修复）")
            if not s["title_ok"]:
                print(f"   - 标题超长（必须截断）")
            if not s["description_ok"]:
                print(f"   - 产品描述超长（必须截断至 2000 字符）")
            if not s["search_terms_ok"]:
                print(f"   - 后台搜索词超字节（整个字段将作废）")
        if not s.get("search_terms_dedup_ok", True):
            print(f"   ⚠️ 后台搜索词有 {result['search_terms_dedup']['duplicate_count']} 个词与前端重复（建议删除以节省字节配额）")
        print("═" * 60 + "\n")

    return result


def load_listing_interactive() -> Dict:
    """交互式输入 listing 内容。"""
    print("请输入 Listing 内容（每项回车结束，五点描述逐条输入）：\n")
    title = input("标题 (Title): ").strip()
    bullets = []
    for i in range(1, 6):
        b = input(f"五点 {i} (Bullet {i}): ").strip()
        if b:
            bullets.append(b)
    description = input("产品描述 (Description): ").strip()
    search_terms = input("后台搜索词 (Search Terms): ").strip()
    return {
        "title": title,
        "bullets": bullets,
        "description": description,
        "search_terms": search_terms,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Amazon Listing 关键词埋词检查 & 商标侵权扫描"
    )
    parser.add_argument("--listing", help="Listing JSON 文件路径")
    parser.add_argument("--keywords", help="关键词文件路径（每行一个关键词）")
    parser.add_argument(
        "--mode",
        choices=["full", "coverage", "trademark", "banned"],
        default="full",
        help="检查模式：full=全部 | coverage=仅埋词 | trademark=仅商标 | banned=仅违禁词",
    )
    parser.add_argument(
        "--category",
        choices=["general", "apparel"],
        default="general",
        help="商品类目（影响标题字符限制）",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    args = parser.parse_args()

    # 加载 Listing
    if args.listing:
        with open(args.listing, "r", encoding="utf-8") as f:
            listing = json.load(f)
    else:
        listing = load_listing_interactive()

    # 加载关键词
    keywords = []
    if args.keywords:
        with open(args.keywords, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
    elif args.mode in ("full", "coverage") and not args.json:
        kw_input = input("\n请输入关键词（逗号或换行分隔，回车跳过）：\n").strip()
        if kw_input:
            keywords = [k.strip() for k in re.split(r"[,\n]", kw_input) if k.strip()]

    run_check(listing, keywords, args.mode, args.category, args.json)


if __name__ == "__main__":
    main()
