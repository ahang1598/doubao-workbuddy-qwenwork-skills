#!/usr/bin/env python3
"""交付阶段读回校验（英文侧）：检查飞书文档回读 XML 是否合格。

纯读回校验：标题存在、有 References、英文文内引用可见、禁用花哨块、无坏占位、
无验真中间痕迹。供 Makefile 的 deliver 目标在 lark-cli 读回后调用。

exit code: 0 通过 / 1 阻断 / 2 环境或参数错误。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import check_draft
from revision_guard import protected_anchor_counts


RICH_BLOCK_BANNED = ("<callout", "<grid", "<button", "<card", "<admonition")
VERIFICATION_ARTIFACTS = ("scout_handoff", "code_trace", "authority_signal", "quality_basis", "reverification")
REFERENCE_HEADINGS = {"references", "works cited", "bibliography", "reference list"}


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def load_citation_style(meta_path: str) -> str:
    try:
        data = json.loads(Path(meta_path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        emit({"status": "error", "stage": "deliver", "failures": [f"无法读取meta.json：{exc}"]}, 2)
    return str(data.get("citation_style") or "apa7").strip().lower()


def has_english_citation(xml: str, citation_style: str) -> bool:
    return bool(citation_keys(visible_xml_text(xml), citation_style))


def normalized_content(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[#*_`>|$\\\[\](){}-]+", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def visible_markdown(value: str) -> str:
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)


def visible_xml_text(value: str) -> str:
    value = re.sub(
        r"</(?:p|h[1-6]|heading|li|tr|div|blockquote|table|sheet)>",
        "\n",
        value,
        flags=re.I,
    )
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value)


def split_reference_section(value: str) -> tuple[str, list[str]]:
    lines = value.splitlines()
    for index, line in enumerate(lines):
        heading = re.sub(r"^\s*#{1,6}\s*", "", line).strip().casefold()
        if heading in REFERENCE_HEADINGS:
            entries = [
                candidate.strip()
                for candidate in lines[index + 1:]
                if candidate.strip()
            ]
            return "\n".join(lines[:index]), entries
    return value, []


def citation_keys(value: str, citation_style: str) -> set[str]:
    keys: set[str] = set()
    if citation_style in {"apa7", "chicago18_author_date"}:
        for author, year, _ in check_draft.extract_author_year_citations(value, citation_style):
            author = re.sub(r"\s*\[[^\]]+\]", "", author)
            author = re.sub(r"\bet\s+al\.?", "", author, flags=re.I)
            author_key = check_draft.normalize_bibliographic_text(author)
            year_key = check_draft.normalize_year(year)
            if author_key and year_key:
                keys.add(f"{author_key}|{year_key}")
    elif citation_style == "mla9":
        for key, _ in check_draft.extract_mla_citations(value):
            normalized = check_draft.normalize_bibliographic_text(key)
            if normalized:
                keys.add(normalized)
    return keys


def reference_keys(entries: list[str]) -> set[str]:
    return {
        normalized
        for entry in entries
        if (normalized := normalized_content(entry))
    }


def content_anchors(source: str) -> list[str]:
    body, _ = split_reference_section(visible_markdown(source))
    candidates: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("|")
            or re.fullmatch(r"\|?[\s:|-]+\|?", stripped)
        ):
            continue
        normalized = normalized_content(stripped)
        if normalized:
            candidates.append(normalized)
    return candidates


def missing_ordered_anchors(anchors: list[str], content: str) -> list[str]:
    missing: list[str] = []
    cursor = 0
    for anchor in anchors:
        position = content.find(anchor, cursor)
        if position < 0:
            missing.append(anchor)
            continue
        cursor = position + len(anchor)
    return missing


def source_expectations(source: str) -> dict[str, Any]:
    headings = [
        re.sub(r"[*_`]", "", match.group(1)).strip()
        for match in re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", source)
    ]
    return {
        "has_references": bool(
            re.search(
                r"(?im)^#{1,3}\s*(references|works cited|bibliography|reference list)\s*$",
                source,
            )
        ),
        "has_table": bool(
            re.search(r"(?m)^\|.+\|\s*$", source)
            and re.search(r"(?m)^\|?\s*[-:]+", source)
        ),
        "headings": headings,
        "normalized_length": len(normalized_content(visible_markdown(source))),
        "anchors": content_anchors(source),
    }


def check_doc(
    xml: str,
    source: str,
    citation_style: str,
    require_tables: bool,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    metrics: dict[str, Any] = {}

    xml_text = visible_xml_text(xml)
    xml_body, xml_references = split_reference_section(xml_text)
    source_visible = visible_markdown(source)
    source_body, source_references = split_reference_section(source_visible)
    title_values = [
        normalized_content(match.group(2))
        for match in re.finditer(
            r"<(title|h1)\b[^>]*>(.*?)</\1>",
            xml,
            flags=re.I | re.S,
        )
    ]
    metrics["has_title"] = any(title_values)
    metrics["has_references"] = bool(xml_references)
    metrics["has_table"] = "<table" in xml or "<sheet" in xml
    metrics["citation_style"] = citation_style
    metrics["has_citation"] = has_english_citation(xml, citation_style)
    metrics["banned_blocks"] = [t for t in RICH_BLOCK_BANNED if t in xml]
    metrics["bad_placeholders"] = [
        label for pattern, label in check_draft.PLACEHOLDER_PATTERNS
        if re.search(pattern, xml, flags=re.I)
    ]
    metrics["verification_artifacts"] = [t for t in VERIFICATION_ARTIFACTS if t in xml.lower()]
    expected = source_expectations(source)
    xml_norm = normalized_content(xml_text)
    metrics["expected_references"] = expected["has_references"]
    metrics["expected_table"] = expected["has_table"]
    metrics["content_length_ratio"] = round(
        len(xml_norm) / max(expected["normalized_length"], 1),
        3,
    )
    metrics["source_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    expected_citation_keys = citation_keys(source_body, citation_style)
    actual_citation_keys = citation_keys(xml_body, citation_style)
    expected_reference_keys = reference_keys(source_references)
    actual_reference_keys = reference_keys(xml_references)
    expected_reference_sequence = [
        normalized_content(entry)
        for entry in source_references
        if normalized_content(entry)
    ]
    actual_reference_sequence = [
        normalized_content(entry)
        for entry in xml_references
        if normalized_content(entry)
    ]
    metrics["expected_citation_keys"] = sorted(expected_citation_keys)
    metrics["citation_keys"] = sorted(actual_citation_keys)
    metrics["expected_body_citation_keys"] = sorted(expected_citation_keys)
    metrics["body_citation_keys"] = sorted(actual_citation_keys)
    metrics["expected_reference_keys"] = sorted(expected_reference_keys)
    metrics["reference_keys"] = sorted(actual_reference_keys)
    metrics["expected_anchor_count"] = len(expected["anchors"])
    expected_literal_counts = protected_anchor_counts(source_visible)
    actual_literal_counts = protected_anchor_counts(xml_text)

    if not metrics["has_title"]:
        failures.append("飞书文档未检测到标题或一级标题。")
    if expected_literal_counts != actual_literal_counts:
        failures.append("飞书读回的数字、单位或引用原始token与终稿不一致。")
    if normalized_content(source_body) != normalized_content(xml_body):
        failures.append("飞书读回正文规范化文本与终稿不一致，存在新增、删除、重排或改写。")
    if metrics["has_references"] and not metrics["has_citation"]:
        failures.append("飞书文档有 References，但未检测到文内引用（作者-年份或编号）。")
    if expected["has_references"] and not metrics["has_references"]:
        failures.append("终稿含 References，但飞书读回未检测到参考文献章节。")
    if (require_tables or expected["has_table"]) and not metrics["has_table"]:
        failures.append("本次要求验收表格，但飞书文档未检测到表格。")
    if expected["normalized_length"] >= 80 and metrics["content_length_ratio"] < 0.6:
        failures.append(
            f"飞书读回正文长度不足终稿的60%（当前比例 {metrics['content_length_ratio']}），可能发生截断或内容丢失。"
        )
    missing_headings = [
        heading for heading in expected["headings"]
        if normalized_content(heading)
        and normalized_content(heading) not in xml_norm
    ]
    if missing_headings:
        failures.append(f"飞书读回缺少终稿标题：{missing_headings[:8]}")
    missing_anchors = missing_ordered_anchors(expected["anchors"], xml_norm)
    if missing_anchors:
        failures.append(
            "飞书读回缺少终稿正文锚点，或段落顺序/重复次数发生变化："
            f"{missing_anchors[:8]}"
        )
    anchor_count_mismatches = [
        anchor
        for anchor, count in Counter(expected["anchors"]).items()
        if xml_norm.count(anchor) != count
    ]
    if anchor_count_mismatches:
        failures.append(
            "飞书读回正文锚点重复次数与终稿不一致："
            f"{anchor_count_mismatches[:8]}"
        )
    if expected_citation_keys != actual_citation_keys:
        failures.append(
            "飞书读回正文引用键集合与终稿不一致："
            f"缺少 {sorted(expected_citation_keys - actual_citation_keys)[:8]}，"
            f"多出 {sorted(actual_citation_keys - expected_citation_keys)[:8]}"
        )
    if expected_reference_keys != actual_reference_keys:
        failures.append(
            "飞书读回参考文献键集合与终稿不一致："
            f"缺少 {sorted(expected_reference_keys - actual_reference_keys)[:5]}，"
            f"多出 {sorted(actual_reference_keys - expected_reference_keys)[:5]}"
        )
    if expected_reference_sequence != actual_reference_sequence:
        failures.append("飞书读回参考文献条目内容、顺序或重复次数与终稿不一致。")
    if metrics["banned_blocks"]:
        failures.append(f"飞书文档存在禁用花哨布局：{metrics['banned_blocks']}")
    if metrics["bad_placeholders"]:
        failures.append(f"飞书文档存在占位或未完成标记：{metrics['bad_placeholders']}")
    if metrics["verification_artifacts"]:
        failures.append(f"飞书文档残留验真中间痕迹：{metrics['verification_artifacts']}")

    return failures, metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, help="读回的飞书文档 XML 文件")
    parser.add_argument("--source", required=True, help="本次交付的 paper_final.md")
    parser.add_argument("--meta", required=True, help="与正文检查共用的 meta.json")
    parser.add_argument("--require-tables", action="store_true")
    parser.add_argument("--write-report", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    xml = Path(args.xml).read_text(encoding="utf-8-sig")
    source = Path(args.source).read_text(encoding="utf-8-sig")
    citation_style = load_citation_style(args.meta)
    failures, metrics = check_doc(xml, source, citation_style, args.require_tables)
    meta_text = Path(args.meta).read_text(encoding="utf-8-sig")
    metrics["meta_sha256"] = hashlib.sha256(meta_text.encode("utf-8")).hexdigest()
    payload = {
        "status": "pass" if not failures else "fail",
        "stage": "deliver",
        "failures": failures,
        "result": metrics,
    }
    if failures:
        payload["fix"] = "修复飞书文档内容后重新读回校验；花哨块、占位与验真痕迹必须清除。"
    if args.write_report:
        report = Path(args.write_report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit(payload, 0 if payload["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
