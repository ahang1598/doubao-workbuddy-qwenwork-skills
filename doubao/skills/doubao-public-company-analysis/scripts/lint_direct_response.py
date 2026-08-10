#!/usr/bin/env python3
"""Lint user-facing direct responses before delivery. Stdlib only."""

import argparse
import re
from pathlib import Path


INTERNAL_MARKERS = [
    re.compile(r"\{fact:[^}]+\}"),
    re.compile(r"\b(?:facts\.json|analysis-plan|source-plan)\b", re.I),
]
TRADE_PATTERNS = [
    re.compile(r"建议(?:立即|马上)?(?:买入|卖出|加仓|减仓)"),
    re.compile(r"目标价\s*[:：]?\s*[￥$¥]?\d"),
    re.compile(r"仓位\s*[:：]?\s*\d+(?:\.\d+)?%"),
    re.compile(r"(?:保证收益|稳赚(?:不赔)?|必然?(?:上涨|下跌))"),
]
CRITICAL_NUMBER = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:%|个百分点|亿元|万元|万美元|倍|美元|人民币|港元)|"
    r"(?:PE|PB|PS|EV/EBITDA|IRR|MOIC)\s*[:：]?\s*\d)",
    re.I,
)
URL = re.compile(r"https?://\S+")
LOW_QUALITY = re.compile(
    r"(?:xueqiu\.com|caifuhao\.eastmoney\.com|book118\.com|renrendoc\.com|"
    r"wenku\.baidu\.com|docin\.com|fanwen|csdn\.net|cofool\.com)",
    re.I,
)
INVALID_REFUSAL = re.compile(
    r"(?:无法|不能|不足以)(?:完成|分析|判断|估值).{0,30}"
    r"(?:因此|所以)?(?:停止|不再|无法继续|仅列|只能列)",
    re.I,
)
GAP_LINE = re.compile(r"(?:缺少|缺失|未知|unknown|待获取|无法取得|待核对)", re.I)
ANSWER = re.compile(r"(?:核心判断|直接结论|结论是|总体判断|我的判断)", re.I)
FCF_PROXY = re.compile(
    r"(?:FCF|自由现金流).{0,40}(?:经营利润|operating\s+profit)"
    r".{0,80}(?:折旧|非现金|non[- ]cash).{0,80}(?:资本开支|CapEx)",
    re.I | re.S,
)
RIGHTS_FIXED_DILUTION = re.compile(
    r"(?:版权费|版权成本|内容分成|创作者分成|royalt(?:y|ies)|content\s+costs?)"
    r".{0,50}(?:固定成本|fixed\s+cost).{0,40}(?:摊薄|dilut|leverage)",
    re.I | re.S,
)


def paragraphs(text):
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("response")
    parser.add_argument("--route-only", action="store_true")
    parser.add_argument("--prompt", default="")
    args = parser.parse_args()
    text = Path(args.response).read_text(encoding="utf-8")
    errors = []
    warnings = []
    prompt_numbers = {
        match.group(0).replace(" ", "") for match in CRITICAL_NUMBER.finditer(args.prompt)
    }

    for pattern in INTERNAL_MARKERS:
        if pattern.search(text):
            errors.append(f"internal marker exposed: {pattern.pattern}")
    for pattern in TRADE_PATTERNS:
        if pattern.search(text):
            errors.append(f"unsafe action language: {pattern.pattern}")
    if FCF_PROXY.search(text):
        errors.append("FCF defined from operating-profit proxy instead of cash-flow statement")
    if RIGHTS_FIXED_DILUTION.search(text):
        errors.append("variable rights/content cost treated as fixed-cost dilution")
    parts = paragraphs(text)
    for index, paragraph in enumerate(parts, 1):
        nearby = "\n".join(parts[max(0, index - 2) : min(len(parts), index + 1)])
        paragraph_numbers = {
            match.group(0).replace(" ", "")
            for match in CRITICAL_NUMBER.finditer(paragraph)
        }
        user_supplied = bool(paragraph_numbers & prompt_numbers)
        if CRITICAL_NUMBER.search(paragraph) and not URL.search(nearby) and not user_supplied:
            errors.append(f"paragraph {index}: critical number has no inline URL")
        if CRITICAL_NUMBER.search(paragraph) and LOW_QUALITY.search(paragraph):
            warnings.append(f"paragraph {index}: critical number uses low-quality source")
    if args.route_only:
        if len(text) > 800:
            errors.append("route-only response exceeds 800 characters")
        if re.search(r"##\s+(?:财务|估值|候选|情景|投资观点)", text):
            errors.append("route-only response continued into domain analysis")
    else:
        if INVALID_REFUSAL.search(text):
            errors.append("invalid global refusal: use local capability/unknown")
        content_lines = [line.strip() for line in text.splitlines() if line.strip()]
        gap_lines = [line for line in content_lines if GAP_LINE.search(line)]
        if content_lines and len(gap_lines) / len(content_lines) > 0.6:
            errors.append("response is primarily a gap checklist")
        if len(text) >= 300 and not ANSWER.search(text[:300]):
            errors.append("direct conclusion missing from opening")
    if "不构成" not in text and not args.route_only:
        warnings.append("financial disclaimer missing")

    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)
    print(f"SUMMARY errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
