#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金买卖报告质量校验器

用途：
1. 对团队生成的 Markdown 报告做结构化质量校验
2. 将“最低篇幅 / 必需章节 / 三段式 / 模糊表述”从软约束变成硬检查
3. 对商品基金追加关键驱动因子校验，减少不同标的之间的内容深度波动

示例：
  python report_quality_validator.py "OutputReport/ETF买卖决策报告_518880_黄金ETF华安.md" --fund-type etf --variant gold
  python report_quality_validator.py "OutputReport/基金买卖决策报告_xxx.md" --fund-type qdii --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

MIN_CHARS = {
    "etf": 2000,
    "lof": 2000,
    "被动指数": 2000,
    "主动权益": 2500,
    "债券": 2000,
    "固收+": 2000,
    "qdii": 2500,
    "量化": 2500,
    "fof": 2500,
}

REQUIRED_HEADINGS = [
    "### 一、风险红线排查结果",
    "### 二、核心结论",
    "### 三、宏观与行业关联",
    "### 四、核心价值分析",
    "### 五、估值与择时分析",
    "### 六、分周期操作建议",
    "### 七、仓位管理方案",
    "### 八、跟踪与调整预案",
    "### 九、风险提示",
]

VAGUE_PHRASES = [
    "逢低布局",
    "长期持有",
    "谨慎关注",
    "有望上涨",
    "可适当关注",
    "值得关注",
    "建议关注",
]

FAILURE_MARKERS = [
    "采集失败",
    "无 fetch_all 函数",
    "数据不足",
    "获取失败",
]

VARIANT_RULES = {
    "gold": {
        "name": "黄金基金",
        "keywords": ["实际利率", "美元指数", "央行购金", "ETF持仓", "净多头"],
        "min_hits": 3,
    },
    "oil": {
        "name": "原油基金",
        "keywords": ["OPEC", "库存", "PMI", "地缘", "供需"],
        "min_hits": 3,
    },
    "theme": {
        "name": "行业/主题指数基金",
        "keywords": ["景气度", "跟踪指数", "重仓", "集中度", "估值", "价格位置"],
        "min_hits": 4,
    },
}


def normalize_fund_type(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in MIN_CHARS:
        return value
    if "etf" in value or "lof" in value or "被动" in value or "指数" in value:
        return "etf"
    if "主动" in value or "权益" in value:
        return "主动权益"
    if "债" in value:
        return "债券"
    if "固收" in value:
        return "固收+"
    if "qdii" in value:
        return "qdii"
    if "量化" in value:
        return "量化"
    if "fof" in value:
        return "fof"
    return "etf"


def compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def check_length(text: str, fund_type: str) -> Tuple[bool, str]:
    minimum = MIN_CHARS.get(fund_type, 2000)
    current = compact_len(text)
    return current >= minimum, f"字数/字符数 {current}，要求至少 {minimum}"


def check_headings(text: str) -> Tuple[bool, str, List[str]]:
    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    return not missing, f"缺失章节数 {len(missing)}", missing


def check_triads(text: str, fund_type: str) -> Tuple[bool, str, Dict[str, int]]:
    counts = {
        "📊": text.count("📊"),
        "🔍": text.count("🔍"),
        "📌": text.count("📌"),
    }
    threshold = 6 if fund_type == "etf" else 7
    passed = all(v >= threshold for v in counts.values())
    return passed, f"三段式标记计数 {counts}，阈值 {threshold}", counts


def check_vague_phrases(text: str) -> Tuple[bool, List[str]]:
    hits = [phrase for phrase in VAGUE_PHRASES if phrase in text]
    return not hits, hits


def check_failure_markers(text: str) -> Tuple[bool, List[str]]:
    hits = [marker for marker in FAILURE_MARKERS if marker in text]
    return not hits, hits


def check_variant(text: str, variant: str) -> Tuple[bool, str, Dict[str, bool]]:
    if not variant:
        return True, "未指定变体校验", {}
    rule = VARIANT_RULES.get(variant)
    if not rule:
        return True, f"未知变体 {variant}，跳过", {}

    hits = {kw: (kw in text) for kw in rule["keywords"]}
    passed_count = sum(1 for ok in hits.values() if ok)
    passed = passed_count >= rule["min_hits"]
    return passed, f"{rule['name']}关键因子命中 {passed_count}/{len(rule['keywords'])}，要求至少 {rule['min_hits']}", hits


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="基金买卖报告质量校验器")

    parser.add_argument("report_path", help="Markdown 报告路径")
    parser.add_argument("--fund-type", default="etf", help="基金类型：etf/主动权益/债券/固收+/qdii/量化/fof")
    parser.add_argument("--variant", default="", help="可选变体：gold/oil/theme")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    report_path = Path(args.report_path)
    if not report_path.exists():
        print(json.dumps({"passed": False, "error": f"文件不存在: {report_path}"}, ensure_ascii=False, indent=2))
        return 2

    text = report_path.read_text(encoding="utf-8")
    fund_type = normalize_fund_type(args.fund_type)

    checks: List[Dict] = []

    ok, detail = check_length(text, fund_type)
    checks.append({"name": "篇幅达标", "passed": ok, "detail": detail})

    ok, detail, missing = check_headings(text)
    checks.append({"name": "章节完整", "passed": ok, "detail": detail, "missing": missing})

    ok, detail, counts = check_triads(text, fund_type)
    checks.append({"name": "三段式覆盖", "passed": ok, "detail": detail, "counts": counts})

    ok, hits = check_vague_phrases(text)
    checks.append({"name": "模糊表述", "passed": ok, "detail": "未命中" if ok else f"命中: {hits}", "hits": hits})

    ok, hits = check_failure_markers(text)
    checks.append({"name": "失败标记", "passed": ok, "detail": "未命中" if ok else f"命中: {hits}", "hits": hits})

    ok, detail, hits = check_variant(text, args.variant.strip().lower())
    checks.append({"name": "变体关键因子", "passed": ok, "detail": detail, "hits": hits})

    passed = all(item["passed"] for item in checks)
    payload = {
        "passed": passed,
        "status": "PASSED" if passed else "FAILED",
        "report": str(report_path),
        "fund_type": fund_type,
        "variant": args.variant.strip().lower(),
        "checks": checks,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    else:
        print(f"状态: {payload['status']}")
        print(f"报告: {report_path}")
        print(f"基金类型: {fund_type}")
        if args.variant:
            print(f"变体: {args.variant.strip().lower()}")
        print("")
        for item in checks:
            flag = "✅" if item["passed"] else "❌"
            print(f"{flag} {item['name']}: {item['detail']}")
            if item.get("missing"):
                print(f"   - 缺失: {item['missing']}")
            if item.get("hits") and isinstance(item.get("hits"), list) and item["hits"]:
                print(f"   - 命中: {item['hits']}")
        if not passed:
            print("\n结论: 报告未通过质量闸门，请补齐后再输出。")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
