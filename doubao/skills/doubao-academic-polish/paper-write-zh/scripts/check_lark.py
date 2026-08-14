#!/usr/bin/env python3
"""交付阶段读回校验：检查飞书文档回读 XML 是否与终稿一致。

搬运自旧 check_lark_doc.py，去掉 handoff 生成，只做纯读回校验：标题存在、
参考文献与文内引用匹配、禁用花哨块、坏占位符，按需校验表格/图占位/公式。
供 Makefile 的 deliver 目标在 lark-cli 读回后调用。

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

from check_draft import citation_key_sets, split_references
from revision_guard import protected_anchor_counts


# 学术文档禁用的花哨布局块。
RICH_BLOCK_BANNED = ("<callout", "<grid", "<button", "<card", "<admonition")

# 不应出现在正式交付文档里的占位或过程文字。
BAD_PLACEHOLDERS = ("将在此处插入", "此处插图", "用户自行替换", "请用户", "TODO")


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def load_citation_style(meta_path: str) -> str:
    try:
        data = json.loads(Path(meta_path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        emit(
            {
                "status": "error",
                "stage": "deliver",
                "failures": [f"无法读取 meta.json 的 citation_style：{exc}"],
            },
            2,
        )
    return str(data.get("citation_style") or "gbt7714_numeric").strip().lower()


def has_table(xml: str) -> bool:
    return "<table" in xml or "<sheet" in xml


def has_citation(xml: str, citation_style: str) -> bool:
    patterns = [
        r"\[\d+(?:[-,，]\s*\d+)*\]",
        r"[①②③④⑤⑥⑦⑧⑨⑩]",
    ]
    if citation_style in {"author_year", "apa", "chicago", "mla", "template"}:
        patterns.extend(
            [
                r"（[^（）]{1,30}，?\s*(?:19|20)\d{2}[a-z]?）",
                r"\([^()]{1,40},?\s*(?:19|20)\d{2}[a-z]?\)",
            ]
        )
    if citation_style == "footnote":
        patterns.append(r"注释|脚注|[①②③④⑤⑥⑦⑧⑨⑩]|\[\^\d+\]")
    if citation_style == "mla":
        patterns.append(r"\([A-Z][A-Za-z'-]+(?:\s+\d+(?:-\d+)?)?\)")
    return any(re.search(pattern, xml) for pattern in patterns)


def has_formula_source(xml: str) -> bool:
    return "$$" in xml or "<equation" in xml or "<formula" in xml or "\\(" in xml or "\\[" in xml


def normalized_content(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[#*_`>|$\\\[\](){}-]+", " ", value)
    return re.sub(r"[^\u4e00-\u9fffa-z0-9]+", "", value.casefold())


def visible_markdown(value: str) -> str:
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return re.sub(r"https?://\S+", "", value)


def visible_xml_text(value: str) -> str:
    value = re.sub(
        r"</(?:p|h[1-6]|heading|li|tr|div|blockquote|table|sheet)>",
        "\n",
        value,
        flags=re.I,
    )
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", value))


def content_anchors(source: str) -> list[str]:
    candidates: list[str] = []
    paragraphs: list[str] = []
    for line in visible_markdown(source).splitlines() + [""]:
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or re.fullmatch(r"\|?[\s:|-]+\|?", stripped)
        ):
            if paragraphs:
                normalized = normalized_content(" ".join(paragraphs))
                if normalized:
                    candidates.append(normalized)
                paragraphs = []
            continue
        if stripped.startswith("|"):
            if paragraphs:
                normalized = normalized_content(" ".join(paragraphs))
                if normalized:
                    candidates.append(normalized)
                paragraphs = []
            normalized = normalized_content(stripped)
            if normalized:
                candidates.append(normalized)
            continue
        paragraphs.append(stripped)
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


def source_expectations(
    source: str,
    citation_style: str = "gbt7714_numeric",
) -> dict[str, Any]:
    headings = [
        re.sub(r"[*_`]", "", match.group(1)).strip()
        for match in re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", source)
    ]
    binding = citation_key_sets(source, citation_style)
    return {
        "has_references": bool(
            re.search(r"(?im)^#{1,3}\s*(参考文献|references|works cited|bibliography|注释|notes)\s*$", source)
        ),
        "has_table": bool(
            re.search(r"(?m)^\|.+\|\s*$", source)
            and re.search(r"(?m)^\|?\s*[-:]+", source)
        ),
        "headings": headings,
        "normalized_length": len(normalized_content(visible_markdown(source))),
        "anchors": content_anchors(source),
        "body_citation_keys": binding["body_keys"],
        "reference_keys": binding["reference_keys"],
    }


def check_doc(
    xml: str,
    source: str,
    citation_style: str,
    require_tables: bool,
    require_figures: bool,
    require_formula: bool,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    metrics: dict[str, Any] = {}

    title_values = [
        normalized_content(match.group(2))
        for match in re.finditer(
            r"<(title|h1)\b[^>]*>(.*?)</\1>",
            xml,
            flags=re.I | re.S,
        )
    ]
    metrics["has_title"] = any(title_values)
    metrics["has_references"] = any(
        title in xml for title in ("参考文献", "References", "Works Cited", "Bibliography", "注释", "Notes")
    )
    metrics["has_table"] = has_table(xml)
    metrics["has_citation"] = has_citation(xml, citation_style)
    metrics["has_formula_source"] = has_formula_source(xml)
    metrics["has_figure_placeholder"] = "待绘制" in xml and "内容要求" in xml
    metrics["banned_blocks"] = [token for token in RICH_BLOCK_BANNED if token in xml]
    metrics["bad_placeholders"] = [token for token in BAD_PLACEHOLDERS if token in xml]
    expected = source_expectations(source, citation_style)
    actual_binding = citation_key_sets(xml, citation_style)
    failures.extend(actual_binding["parse_errors"])
    xml_norm = normalized_content(xml)
    metrics["expected_references"] = expected["has_references"]
    metrics["expected_table"] = expected["has_table"]
    metrics["content_length_ratio"] = round(
        len(xml_norm) / max(expected["normalized_length"], 1),
        3,
    )
    metrics["source_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    metrics["expected_body_citation_keys"] = sorted(
        expected["body_citation_keys"]
    )
    metrics["actual_body_citation_keys"] = sorted(actual_binding["body_keys"])
    metrics["expected_reference_keys"] = sorted(expected["reference_keys"])
    metrics["actual_reference_keys"] = sorted(actual_binding["reference_keys"])
    metrics["substantive_anchor_count"] = len(expected["anchors"])
    source_visible = visible_markdown(source)
    xml_visible = visible_xml_text(xml)
    source_body, source_references = split_references(source_visible)
    xml_body, xml_references = split_references(xml_visible)
    expected_literal_counts = protected_anchor_counts(source_visible)
    actual_literal_counts = protected_anchor_counts(xml_visible)

    if not metrics["has_title"]:
        failures.append("飞书文档未检测到标题或一级标题。")
    if expected_literal_counts != actual_literal_counts:
        failures.append("飞书读回的数字、单位或引用原始token与终稿不一致。")
    if normalized_content(source_body) != normalized_content(xml_body):
        failures.append("飞书读回正文规范化文本与终稿不一致，存在新增、删除、重排或改写。")
    if normalized_content(source_references) != normalized_content(xml_references):
        failures.append("飞书读回参考文献内容、顺序或重复次数与终稿不一致。")
    if metrics["has_references"] and not metrics["has_citation"]:
        failures.append("飞书文档有参考文献，但未检测到文内引用标识。")
    if expected["has_references"] and not metrics["has_references"]:
        failures.append("终稿含参考文献，但飞书读回未检测到参考文献章节。")
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
            f"{missing_anchors[:3]}"
        )
    anchor_count_mismatches = [
        anchor
        for anchor, count in Counter(expected["anchors"]).items()
        if xml_norm.count(anchor) != count
    ]
    if anchor_count_mismatches:
        failures.append(
            "飞书读回正文锚点重复次数与终稿不一致："
            f"{anchor_count_mismatches[:3]}"
        )
    if actual_binding["body_keys"] != expected["body_citation_keys"]:
        failures.append(
            "飞书读回正文引用键集合与终稿不一致："
            f"终稿 {sorted(expected['body_citation_keys'])}，"
            f"读回 {sorted(actual_binding['body_keys'])}"
        )
    if actual_binding["reference_keys"] != expected["reference_keys"]:
        failures.append(
            "飞书读回参考条目键集合与终稿不一致："
            f"终稿 {sorted(expected['reference_keys'])}，"
            f"读回 {sorted(actual_binding['reference_keys'])}"
        )
    if require_figures and not metrics["has_figure_placeholder"]:
        failures.append("本次要求验收图占位，但飞书文档未检测到合格图占位（需含待绘制与内容要求）。")
    if require_formula and not metrics["has_formula_source"]:
        failures.append("本次要求验收公式，但飞书文档未检测到公式块或 LaTeX 源。")
    if metrics["banned_blocks"]:
        failures.append(f"飞书文档存在禁用花哨布局：{metrics['banned_blocks']}")
    if metrics["bad_placeholders"]:
        failures.append(f"飞书文档存在不合格占位或过程文字：{metrics['bad_placeholders']}")

    return failures, metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, help="读回的飞书文档 XML 文件")
    parser.add_argument("--source", required=True, help="本次交付的 paper_final.md")
    parser.add_argument("--meta", required=True, help="与正文检查共用的 meta.json")
    parser.add_argument("--require-tables", action="store_true")
    parser.add_argument("--require-figures", action="store_true")
    parser.add_argument("--require-formula", action="store_true")
    parser.add_argument("--write-report", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    xml = Path(args.xml).read_text(encoding="utf-8-sig")
    source = Path(args.source).read_text(encoding="utf-8-sig")
    citation_style = load_citation_style(args.meta)
    failures, metrics = check_doc(
        xml,
        source,
        citation_style,
        args.require_tables,
        args.require_figures,
        args.require_formula,
    )
    meta_text = Path(args.meta).read_text(encoding="utf-8-sig")
    metrics["meta_sha256"] = hashlib.sha256(meta_text.encode("utf-8")).hexdigest()
    payload = {
        "status": "pass" if not failures else "fail",
        "stage": "deliver",
        "failures": failures,
        "result": metrics,
    }
    if failures:
        payload["fix"] = "修复飞书文档内容后重新读回校验；花哨块与占位文字必须清除。"
    if args.write_report:
        report = Path(args.write_report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit(payload, 0 if payload["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
