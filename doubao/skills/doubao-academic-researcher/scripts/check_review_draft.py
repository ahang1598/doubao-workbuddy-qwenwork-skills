#!/usr/bin/env python3
"""Validate the shape of the review-writing draft.

This script does not judge research quality. It only blocks the common failure
mode where the review draft turns into a full paper outline with abstract,
introduction, numbered sections, lists, or tables.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STRUCTURAL_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
    r"(?:摘要|引言|绪论|研究方法|方法|结果|讨论|结论|总结|参考文献)"
    r"(?:\*\*)?(?:\s*[:：]\s*.+)?\s*$"
)
NUMBERED_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:[一二三四五六七八九十]+[、.．]|第[一二三四五六七八九十]+[章节]|[0-9]+[、.．])\s*\S+"
)
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)")
TABLE_RE = re.compile(r"^\s*\|")
AUTHOR_YEAR_PATTERNS = (
    # 中文叙述式：张三（2021）/ 张三和李四（2021）/ 张三等（2021）
    re.compile(r"[\u4e00-\u9fff]{1,8}(?:[和与、][\u4e00-\u9fff]{1,8})?(?:等)?[（(]\d{4}[）)]"),
    # 英文叙述式：Smith（2020）/ Smith and Jones（2020）/ Smith & Jones（2020）/ Smith et al.（2020）
    re.compile(r"[A-Z][A-Za-z'’-]+(?:\s*(?:&|and)\s*[A-Z][A-Za-z'’-]+)?(?:\s+et al\.)?[（(]\d{4}[）)]"),
    # 括注式（中英通用）：（张三，2021）/（张三和李四，2021）/（Smith et al.，2020）
    re.compile(r"[（(][^（）()\n]{0,120}(?:等|et al\.|[\u4e00-\u9fff]|[A-Za-z])[^（）()\n]{0,20}[,，]\s*\d{4}[^（）()\n]{0,120}[）)]"),
)
# 负向校验：英文双作者错误使用中文“和”连接（如 “Smith 和 Jones（2020）”）。
# 英文姓氏之间应使用 and（叙述式）或 &（括注式），不得夹中文“和”。
# 用紧跟的年份约束把“引用”与普通英文术语并列（Python 和 Java）区分开，避免误伤。
EN_CONNECTOR_ERROR_RE = re.compile(
    r"[A-Z][A-Za-z'’\-]+\s*和\s*[A-Z][A-Za-z'’\-]+(?:\s+et al\.)?\s*[，,]?\s*[（(]?\s*\d{4}"
)
NUMBERED_CITATION_RE = re.compile(r"\[\d+(?:\s*[-,–]\s*\d+)?\]")
LINK_RE = re.compile(r"https?://|\[[^\]]+\]\([^)]+\)")
MAX_CITATIONS_PER_CLUSTER = 4
MAX_VISIBLE_LENGTH = 2000
LENGTH_FLOAT_TOLERANCE = 200
FORBIDDEN_PHRASES = (
    "本文",
    "本研究",
    "本论文",
    "为解决上述问题",
    "本文提出",
    "本文将",
    "本研究提出",
)


def visible_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def paragraphs(text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    return blocks


def has_author_year(text: str) -> bool:
    return any(pattern.search(text) for pattern in AUTHOR_YEAR_PATTERNS)


def en_connector_error_failures(text: str) -> list[str]:
    """英文双作者不得用中文“和”连接（应为 and / &）。"""
    failures: list[str] = []
    for match in EN_CONNECTOR_ERROR_RE.finditer(text):
        snippet = match.group(0).strip()
        failures.append(
            f"英文双作者引用误用中文“和”：“{snippet}”；英文叙述式用 and、括注式用 &"
        )
    return failures


def citation_cluster_failures(text: str) -> list[str]:
    failures: list[str] = []
    for match in re.finditer(r"[（(]([^（）()\n]{0,300}\d{4}[^（）()\n]{0,300})[）)]", text):
        if not has_author_year(match.group(0)):
            continue
        years = re.findall(r"\b(?:19|20)\d{2}\b", match.group(1))
        if len(years) > MAX_CITATIONS_PER_CLUSTER:
            failures.append(
                f"citation cluster contains {len(years)} citations; max is {MAX_CITATIONS_PER_CLUSTER}"
            )
    return failures


def validate(text: str) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    lines = [line.rstrip() for line in text.splitlines()]
    body = text.strip()
    para = paragraphs(body)
    length = visible_length(body)

    if not body:
        failures.append("draft is empty")

    if not 3 <= len(para) <= 6:
        failures.append(f"paragraph_count must be 3-6, got {len(para)}")

    if length > MAX_VISIBLE_LENGTH + LENGTH_FLOAT_TOLERANCE:
        failures.append(
            f"visible_length should stay around {MAX_VISIBLE_LENGTH} "
            f"(float {LENGTH_FLOAT_TOLERANCE}), got {length}"
        )

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            failures.append(f"line {lineno}: headings are not allowed in review draft")
        if STRUCTURAL_HEADING_RE.match(stripped):
            failures.append(f"line {lineno}: paper-structure heading is not allowed: {stripped}")
        if NUMBERED_HEADING_RE.match(stripped):
            failures.append(f"line {lineno}: numbered section heading is not allowed: {stripped}")
        if LIST_RE.match(stripped):
            failures.append(f"line {lineno}: lists are not allowed in review draft")
        if TABLE_RE.match(stripped):
            failures.append(f"line {lineno}: tables are not allowed in review draft")

    for phrase in FORBIDDEN_PHRASES:
        if phrase in body:
            failures.append(f"forbidden phrase found: {phrase}")

    numbered_count = len(NUMBERED_CITATION_RE.findall(body))
    if numbered_count:
        failures.append("draft contains numbered citations like [1]; use author-year citations")

    if not has_author_year(body):
        failures.append("draft must contain author-year citations")

    if LINK_RE.search(body):
        failures.append("draft body must not contain source hyperlinks; links belong in final references")

    failures.extend(citation_cluster_failures(body))
    failures.extend(en_connector_error_failures(body))

    result = {
        "paragraph_count": len(para),
        "visible_length": length,
        "numbered_citations": numbered_count,
        "author_year_citations": sum(len(pattern.findall(body)) for pattern in AUTHOR_YEAR_PATTERNS),
        "status": "pass" if not failures else "fail",
    }
    return result, failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check review-writing draft shape")
    parser.add_argument("--input", "-i", required=True, help="review draft markdown/text path")
    parser.add_argument("--write-report", help="optional JSON report output path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    text = Path(args.input).read_text(encoding="utf-8-sig")
    result, failures = validate(text)
    payload = {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "result": result,
    }
    if args.write_report:
        out = Path(args.write_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
