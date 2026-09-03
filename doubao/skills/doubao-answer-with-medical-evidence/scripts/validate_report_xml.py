#!/usr/bin/env python3
"""Run the minimal pre-create checks for a patient-facing Feishu XML report."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree


ANCHOR_RE = re.compile(
    r"<a\b[^>]*\bhref\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.I | re.S,
)
SUP_RE = re.compile(r"<\s*/?\s*sup\b|<\s*sup\b[^>]*/\s*>", re.I)
RAW_AMPERSAND_RE = re.compile(
    r"&(?!amp;|lt;|gt;|apos;|quot;|#\d+;|#x[0-9A-Fa-f]+;)"
)
DISPLAYED_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
DOMAIN_PATH_RE = re.compile(
    r"(?:[A-Z0-9-]+\.)+[A-Z]{2,}(?:[/#?][^\s]*)", re.I
)
BARE_DOMAIN_RE = re.compile(r"(?:[A-Z0-9-]+\.)+[A-Z]{2,}", re.I)
GENERIC_LINK_LABEL_PREFIX_RE = re.compile(
    r"^(?:(?:原文|链接|网址|来源|查看原文|点击查看|查看)\s*[:：]?\s*)+",
    re.I,
)
LINK_LABEL_EDGE_PUNCTUATION = " \t\r\n()（）[]【】<>《》“”\"'：:，,。.;；"


def _visible_text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _contains_sup(raw: str) -> bool:
    candidate = raw
    for _ in range(3):
        if SUP_RE.search(candidate):
            return True
        decoded = html.unescape(candidate)
        if decoded == candidate:
            break
        candidate = decoded
    return False


def _bare_url_candidate(visible: str) -> str:
    """Remove only generic wrappers before checking for an exposed bare domain."""

    candidate = visible.strip(LINK_LABEL_EDGE_PUNCTUATION)
    candidate = GENERIC_LINK_LABEL_PREFIX_RE.sub("", candidate)
    return candidate.strip(LINK_LABEL_EDGE_PUNCTUATION)


def _is_bare_url_label(label: str, href: str) -> bool:
    visible = _visible_text(label)
    decoded_href = html.unescape(href).strip()
    if not visible:
        return False
    candidate = _bare_url_candidate(visible)
    return bool(
        visible == decoded_href
        or DISPLAYED_URL_RE.search(visible)
        or DOMAIN_PATH_RE.search(candidate)
        or BARE_DOMAIN_RE.fullmatch(candidate)
    )


def _has_visible_raw_url(root: ElementTree.Element) -> bool:
    for element in root.iter():
        for candidate in (element.text, element.tail):
            visible = html.unescape(candidate or "").strip()
            bare_candidate = _bare_url_candidate(visible)
            if visible and (
                DISPLAYED_URL_RE.search(visible)
                or DOMAIN_PATH_RE.search(bare_candidate)
                or BARE_DOMAIN_RE.fullmatch(bare_candidate)
            ):
                return True
    return False


def _citation_links(raw: str) -> tuple[list[str], list[str]]:
    valid: list[str] = []
    invalid: list[str] = []
    for href, label in ANCHOR_RE.findall(raw):
        if (
            re.fullmatch(r"https?://[^\s]+", href)
            and _visible_text(label)
            and not _is_bare_url_label(label, href)
        ):
            valid.append(href)
        else:
            invalid.append(href)
    return valid, invalid


def validate_report(raw: str) -> list[str]:
    """Check XML usability, readable clickable references, and forbidden sup tags."""

    problems: list[str] = []
    stripped = raw.lstrip("\ufeff \t\r\n")
    if not stripped:
        return ["报告 XML 不能为空"]

    parsed_root: ElementTree.Element | None = None
    try:
        parsed_root = ElementTree.fromstring(f"<root>{stripped}</root>")
    except ElementTree.ParseError as exc:
        problems.append(f"报告 XML 不是良构片段：{exc}")
        if RAW_AMPERSAND_RE.search(stripped):
            problems.append(
                "XML 正文或属性值中的 & 是特殊字符，必须写成 &amp;；"
                "不要转义真实 XML 标签，也不要重复转义已经合法的 &amp;"
            )

    if _contains_sup(raw):
        problems.append("报告不得使用 <sup> 上标或脚注式引用；请直接使用可点击的来源名称")

    if parsed_root is not None and _has_visible_raw_url(parsed_root):
        problems.append(
            "文档可见文字不得直接显示 http(s) 或 www 裸链接；"
            "真实 URL 只写入 href，显示文字使用来源名称或说明性短语"
        )

    valid_links, invalid_links = _citation_links(raw)
    if not valid_links:
        problems.append("报告至少需要一个带 http(s) 协议且使用可读文字的可点击引用")
    if invalid_links:
        problems.append(
            "引用链接必须使用 http(s) 协议，并以来源名称或说明性短语作为链接文字；"
            "不得留空或把 URL 本身作为链接文字"
        )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="rendered report XML path, or - for stdin")
    args = parser.parse_args()

    try:
        raw = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"报告读取失败：{exc}", file=sys.stderr)
        return 2

    problems = validate_report(raw)
    if problems:
        print("患者版报告 XML 未通过校验：", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    links, _ = _citation_links(raw)
    print(
        json.dumps(
            {
                "valid": True,
                "citation_links": len(links),
                "forbidden_sup_tags": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
