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
