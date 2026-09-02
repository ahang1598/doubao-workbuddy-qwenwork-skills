#!/usr/bin/env python3
"""标题预筛选脚本 — 在 AIGC 验证前过滤明显不相关的 1688 商品。

用法:
  python title_prefilter.py <1688_json_file> --category-word "<品类词>" --source <B1|B2>

输出: 过滤后的商品列表 JSON 到 stdout，被过滤的商品数到 stderr
"""
import argparse
import json
import sys


def prefilter(data, category_word, source):
    """过滤标题不含品类词的商品。

    Args:
        data: 1688 搜索结果 JSON（B1 或 B2 格式）
        category_word: 品类词（如 "化妆镜"、"便携显示器"）
        source: "B1" 或 "B2"

    Returns:
        (kept_products, filtered_count)
    """
    # B1 (linkfox-dld-product-search) 和 B2 (linkfox-1688-search-by-image) 都用 products 字段
    products = data.get("products", []) if isinstance(data, dict) else []

    if not products:
        print(f"[⚠️ 警告] {source} 结果中无商品", file=sys.stderr)
        return [], 0

    kept = []
    filtered = []

    for p in products:
        title = p.get("title", "") or ""
        if category_word.lower() in title.lower():
            kept.append(p)
        else:
            filtered.append({"offerId": p.get("offerId", ""), "title": title[:50], "reason": f"标题不含品类词'{category_word}'"})

    print(f"[预筛选] {source}: 共 {len(products)} 条, 保留 {len(kept)} 条, 过滤 {len(filtered)} 条", file=sys.stderr)
    for f in filtered:
        print(f"  [过滤] {f['offerId']} | {f['title']} | {f['reason']}", file=sys.stderr)

    return kept, len(filtered)


def main():
    parser = argparse.ArgumentParser(description="标题预筛选 — 过滤标题不含品类词的 1688 商品")
    parser.add_argument("json_file", help="1688 搜索结果 JSON 文件路径")
    parser.add_argument("--category-word", required=True, help="品类词（如 '化妆镜'、'便携显示器'）")
    parser.add_argument("--source", required=True, choices=["B1", "B2"], help="数据来源 B1 或 B2")
    args = parser.parse_args()

    with open(args.json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    kept, filtered_count = prefilter(data, args.category_word, args.source)

    # 输出过滤后的商品列表 JSON 到 stdout
    print(json.dumps(kept, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
