#!/usr/bin/env python3
"""
AI-Powered Title Analysis for Amazon Search Results

Uses linkfox-aigc-textgen (GEM_3_FLASH) to extract structured information
from product titles: brand, materials, features, use cases, cultural markers, specs.

Usage:
  python analyze_titles_ai.py <amazon_search_json> [--inline]
  python analyze_titles_ai.py <amazon_search_json> --model GEM_3_1_PRO

Output:
  - Always writes full JSON to <cwd>/linkfox/<YYYY-MM-DD>/<session>/data/
  - Prints summary to stdout
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from collections import Counter
from statistics import mean

SLUG = "cross-cultural-product-selection"
SMALL_THRESHOLD = 8000

# Path to the AIGC textgen script
AIGC_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "linkfox-aigc-textgen", "scripts", "aigc_textgen.py"
)


def resolve_data_path():
    cwd = os.getcwd()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    session_id = os.environ.get("SESSION_ID", "default")
    base = os.path.join(cwd, "linkfox", today, session_id, "data")
    os.makedirs(base, exist_ok=True)
    return base


def load_products(filepath):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("errcode") != 200:
        raise ValueError(f"API error: {data.get('errmsg')}")
    products = data.get("products", [])
    keyword = data.get("keyword", "unknown")
    return products, keyword


def build_prompt(titles, keyword):
    """Build AI extraction prompt."""
    title_list = "\n".join(f"{i+1}. \"{t}\"" for i, t in enumerate(titles))

    prompt = f"""你是一个亚马逊产品标题分析专家。请从以下"{keyword}"搜索结果的产品标题中提取结构化信息。

对于每个标题，提取以下字段（用中文标注）：
- brand: 品牌名（从标题语义判断哪个词是品牌，可能在任意位置；如果无法确定填 "Unknown"）
- materials: 材质列表（如 ["棉", "陶瓷", "不锈钢"]）
- features: 核心卖点列表（如 ["保温", "可折叠", "环保", "手工制作"]）
- useCases: 使用场景列表（如 ["下午茶", "室内晾衣", "圣诞聚餐"]）
- culturalMarkers: 文化标识列表（如 ["英式", "英格兰设计", "Union Jack"]）
- specs: 规格描述（如 "大号", "3件套", "6杯量"）

判断品牌名的规则：
1. 品牌名通常是专有名词（首字母大写），不是通用产品词或形容词
2. 如果标题以品牌名开头，直接取
3. 如果标题以描述词开头（如"Large"、"3-Tier"），品牌名可能在后面
4. "by [X]" 模式中 X 通常是品牌
5. 多词品牌要完整提取（如 "Ulster Weavers" 而非 "Ulster"）
6. 明显不是品牌的词：tea, cup, stand, large, small, pack, set 等

请以 JSON 数组格式返回，每个元素对应一个标题，按顺序排列：
[{{"brand": "...", "materials": [...], "features": [...], "useCases": [...], "culturalMarkers": [...], "specs": "..."}}, ...]

只返回 JSON 数组，不要其他文字。

产品标题列表：
{title_list}"""
    return prompt


def call_aigc(prompt, model="GEM_3_FLASH"):
    """Call linkfox-aigc-textgen script with the prompt."""
    params = {
        "prompt": prompt,
        "imageUrls": [],
        "model": model,
        "thinkingLevel": "medium",
    }

    # Write params to temp file to avoid shell escaping issues
    params_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_aigc_params.json")
    with open(params_file, "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False)

    try:
        # Call the AIGC script with --stdin --content-only
        with open(params_file, "r", encoding="utf-8") as stdin_f:
            result = subprocess.run(
                ["python3", AIGC_SCRIPT, "--stdin", "--content-only"],
                stdin=stdin_f,
                capture_output=True,
                text=True,
                timeout=600,
            )
    finally:
        if os.path.exists(params_file):
            os.remove(params_file)

    if result.returncode != 0:
        raise RuntimeError(f"AIGC script failed (exit {result.returncode}): {result.stderr[:500]}")

    content = result.stdout.strip()
    if not content:
        raise RuntimeError("AIGC script returned empty content")

    return content


def parse_ai_response(content, num_titles):
    """Parse AI response into structured data."""
    # The AIGC script replaces newlines with U+23CE, restore them
    content = content.replace("\u23ce", "\n").strip()
    # Strip markdown code blocks if present
    import re as _re
    _cb = _re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, _re.DOTALL)
    if _cb:
        content = _cb.group(1).strip()

    # Find the JSON array in the response
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"Cannot find JSON array in AI response. Content: {content[:200]}")

    json_str = content[start:end + 1]
    try:
        items = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI response as JSON: {e}. Content: {json_str[:200]}")

    # Ensure we have the right number of items
    if len(items) < num_titles:
        # Pad with empty items
        while len(items) < num_titles:
            items.append({"brand": "Unknown", "materials": [], "features": [], "useCases": [], "culturalMarkers": [], "specs": ""})
    elif len(items) > num_titles:
        items = items[:num_titles]

    return items


def aggregate_results(items):
    """Aggregate extracted data across all titles."""
    total = len(items) or 1

    # Brand concentration
    brands = [item.get("brand", "Unknown") for item in items]
    brand_counter = Counter(brands)
    top_brands = [
        {"brand": b, "count": c, "share_pct": round(c / total * 100, 1)}
        for b, c in brand_counter.most_common(10)
    ]

    # Materials distribution
    all_materials = []
    for item in items:
        all_materials.extend(item.get("materials", []))
    material_counter = Counter(all_materials)
    materials = [
        {"material": m, "count": c, "share_pct": round(c / total * 100, 1)}
        for m, c in material_counter.most_common(15)
    ]

    # Features distribution
    all_features = []
    for item in items:
        all_features.extend(item.get("features", []))
    feature_counter = Counter(all_features)
    features = [
        {"feature": f, "count": c, "share_pct": round(c / total * 100, 1)}
        for f, c in feature_counter.most_common(15)
    ]

    # Cultural markers
    all_cultural = []
    for item in items:
        all_cultural.extend(item.get("culturalMarkers", []))
    cultural_counter = Counter(all_cultural)
    cultural = [
        {"marker": m, "count": c, "share_pct": round(c / total * 100, 1)}
        for m, c in cultural_counter.most_common(10)
    ]

    # Use cases
    all_use_cases = []
    for item in items:
        all_use_cases.extend(item.get("useCases", []))
    use_case_counter = Counter(all_use_cases)
    use_cases = [
        {"scenario": u, "count": c}
        for u, c in use_case_counter.most_common(10)
    ]

    # Specs
    all_specs = [item.get("specs", "") for item in items if item.get("specs")]
    spec_counter = Counter(all_specs)
    specs = [
        {"spec": s, "count": c}
        for s, c in spec_counter.most_common(10)
    ]

    return {
        "totalTitles": total,
        "brands": top_brands,
        "materials": materials,
        "features": features,
        "culturalMarkers": cultural,
        "useCases": use_cases,
        "specs": specs,
        "extraction_method": "AI (GEM_3_FLASH/GEM_3_1_PRO) semantic analysis",
        "note": "品牌/材质/卖点/场景/文化标识由AI大模型语义提取，非关键词匹配",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_titles_ai.py <amazon_search_json> [--inline] [--model GEM_3_1_PRO]")
        sys.exit(1)

    inline = "--inline" in sys.argv
    model = "GEM_3_FLASH"
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]

    files = [f for f in sys.argv[1:] if not f.startswith("--")]
    if not files:
        print("Error: no input file specified")
        sys.exit(1)

    filepath = files[0]
    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}")
        sys.exit(1)

    # Load products
    products, keyword = load_products(filepath)
    titles = [p.get("title", "") for p in products]

    if not titles:
        print("Error: no titles found in input file")
        sys.exit(1)

    print(f"Analyzing {len(titles)} titles for keyword '{keyword}' using AI model {model}...", file=sys.stderr)

    # Build prompt and call AI
    prompt = build_prompt(titles, keyword)
    content = call_aigc(prompt, model)

    # Parse AI response
    items = parse_ai_response(content, len(titles))

    # Aggregate results
    aggregated = aggregate_results(items)

    output = {
        "analysis_type": "ai_title_analysis",
        "keyword": keyword,
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_titles": len(titles),
        "aggregated": aggregated,
        "per_title": items,
    }

    # Always write to data directory
    data_path = resolve_data_path()
    ts = int(time.time() * 1_000_000)
    out_file = os.path.join(data_path, f"ai-title-analysis-{ts}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    output_json = json.dumps(output, ensure_ascii=False, indent=2)
    output_bytes = len(output_json.encode("utf-8"))

    if inline or output_bytes <= SMALL_THRESHOLD:
        print(output_json)
    else:
        print(f"Saved full response: {out_file} ({output_bytes} bytes)")
        a = aggregated
        print(f"\nAI Title Analysis for '{keyword}' ({len(titles)} titles, model={model}):")
        print(f"\n  Brands: {', '.join(b['brand'] + '(' + str(b['count']) + ')' for b in a['brands'][:5])}")
        print(f"  Materials: {', '.join(m['material'] + '(' + str(m['count']) + ')' for m in a['materials'][:5])}")
        print(f"  Features: {', '.join(f['feature'] + '(' + str(f['count']) + ')' for f in a['features'][:5])}")
        print(f"  Cultural: {', '.join(c['marker'] + '(' + str(c['count']) + ')' for c in a['culturalMarkers'][:5])}")
        print(f"  Use cases: {', '.join(u['scenario'] + '(' + str(u['count']) + ')' for u in a['useCases'][:5])}")
        print(f"\nFull details saved to: {out_file}")
        print("Use --inline to see full JSON output.")


if __name__ == "__main__":
    main()
