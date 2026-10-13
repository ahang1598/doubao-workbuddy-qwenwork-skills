#!/usr/bin/env python3
"""Validate research facts and build reader-facing Markdown or Lark XML."""

import argparse
import html
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


FACT_RE = re.compile(r"\{fact:([^}]+)\}")
CLAIM_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
PLACEHOLDER_RE = re.compile(r"\b(?:TBD|TODO|FIXME)\b|待补(?:充|数据)?|\{\{[^}]+\}\}")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
DISCLAIMER = "免责声明：本内容仅供研究与信息参考，不构成投资建议。"
XML_DISCLAIMER_RE = re.compile(
    r"<p(?:\s+[^>]*)?>\s*" + re.escape(DISCLAIMER) + r"\s*</p>\s*$",
    re.S,
)

SOURCE_TYPES = {
    "regulator", "exchange", "official_filing", "government_statistics",
    "company_ir", "finance_database", "consensus_database", "broker",
    "industry_body", "media", "author_inference",
}
USAGE_TYPES = {
    "hard_fact", "company_statement", "management_guidance", "consensus",
    "news_event", "author_inference",
}
HARD_FACT_SOURCES = {
    "regulator", "exchange", "official_filing", "government_statistics",
    "company_ir", "finance_database",
}


def emit(message):
    sys.stderr.write(f"{message}\n")


def parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def load_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("facts.json 顶层必须是对象")
    return data


def validate_facts(data):
    errors = []
    warnings = []
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta 缺失或不是对象")
        meta = {}

    for field in ("research_object", "as_of"):
        if not meta.get(field):
            errors.append(f"meta.{field} 缺失")
    as_of = parse_date(meta.get("as_of"))
    if meta.get("as_of") and as_of is None:
        errors.append("meta.as_of 必须为 YYYY-MM-DD")

    claims = data.get("claims")
    if not isinstance(claims, list):
        errors.append("claims 必须是数组")
        claims = []

    known_ids = {
        item.get("claim_id") for item in claims
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }
    seen = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} 必须是对象")
            continue

        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            errors.append(f"{prefix}.claim_id 格式错误")
        elif claim_id in seen:
            errors.append(f"{prefix}.claim_id 重复: {claim_id}")
        else:
            seen.add(claim_id)

        for field in ("text", "source", "source_date", "source_type", "usage_type"):
            if not claim.get(field):
                errors.append(f"{prefix}.{field} 缺失")

        source_date = parse_date(claim.get("source_date"))
        if claim.get("source_date") and source_date is None:
            errors.append(f"{prefix}.source_date 必须为 YYYY-MM-DD")
        elif as_of and source_date and source_date > as_of:
            errors.append(f"{prefix}.source_date 晚于 meta.as_of")

        source_type = claim.get("source_type")
        usage_type = claim.get("usage_type")
        if source_type and source_type not in SOURCE_TYPES:
            errors.append(f"{prefix}.source_type 不在允许枚举内")
        if usage_type and usage_type not in USAGE_TYPES:
            errors.append(f"{prefix}.usage_type 不在允许枚举内")
        if usage_type == "hard_fact" and source_type not in HARD_FACT_SOURCES:
            errors.append(f"{prefix} 将非权威来源标为 hard_fact")

        if usage_type == "author_inference":
            evidence_ids = claim.get("evidence_ids")
            if source_type != "author_inference":
                errors.append(f"{prefix}.author_inference 的 source_type 必须匹配")
            if not isinstance(evidence_ids, list) or not evidence_ids:
                errors.append(f"{prefix}.author_inference 缺少 evidence_ids")
            else:
                unknown = sorted(set(evidence_ids) - known_ids)
                if unknown:
                    errors.append(f"{prefix}.author_inference 引用了未知 evidence_ids: {unknown}")
                if claim_id in evidence_ids:
                    errors.append(f"{prefix}.author_inference 不得自引用")
            if not isinstance(claim.get("alternatives"), list) or not claim.get("alternatives"):
                errors.append(f"{prefix}.author_inference 缺少 alternatives")
            if claim.get("confidence") not in {"high", "medium", "low"}:
                errors.append(f"{prefix}.author_inference 的 confidence 必须为 high/medium/low")

        value = claim.get("value")
        if "value" in claim and not claim.get("unit"):
            warnings.append(f"{prefix} 有 value 但 unit 缺失")
        if isinstance(value, (int, float)) and not math.isfinite(value):
            errors.append(f"{prefix}.value 必须为有限数")
        if not claim.get("url"):
            warnings.append(f"{prefix}.url 缺失；确认来源确无公开链接")

    return errors, warnings


def claim_map(data):
    return {
        item["claim_id"]: item
        for item in data.get("claims", [])
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }


def fact_ids(text):
    result = []
    for group in FACT_RE.findall(text):
        result.extend(item.strip() for item in group.split(",") if item.strip())
    return result


def validate_source(text, claims, output_format="markdown"):
    errors = []
    warnings = []
    lines = text.splitlines()
    if output_format == "markdown":
        if not lines or not lines[0].startswith("# "):
            errors.append("Markdown 正文必须以一级标题开始")
        if not lines or lines[-1].strip() != DISCLAIMER:
            errors.append("Markdown 最后一行必须是规定的免责声明")
    elif output_format == "lark-xml":
        stripped = text.strip()
        if not re.match(r"^<title(?:\s|>)", stripped):
            errors.append("飞书 XML 正文必须以 <title> 开始")
        if not XML_DISCLAIMER_RE.search(stripped):
            errors.append("飞书 XML 最后必须是包含规定免责声明的 <p>")
        try:
            ET.fromstring(f"<root>{text}</root>")
        except ET.ParseError as exc:
            errors.append(f"飞书 XML 不是合法的 XML 片段: {exc}")
    else:
        errors.append(f"未知输出格式: {output_format}")

    for number, line in enumerate(lines, start=1):
        if PLACEHOLDER_RE.search(line):
            errors.append(f"L{number} 存在占位符: {line.strip()[:80]}")
        for claim_id in fact_ids(line):
            if claim_id not in claims:
                errors.append(f"L{number} 引用了不存在的 claim_id: {claim_id}")

    used = set(fact_ids(text))
    unused = sorted(set(claims) - used)
    if unused:
        warnings.append(f"facts.json 中有未被正文引用的 claim_id: {unused}")
    if "信息截止日" not in text and "截至" not in text:
        warnings.append("正文未明确写出信息截止日")
    return errors, warnings


def replace_fact_markers(text):
    order = []
    numbers = {}

    def replace(match):
        markers = []
        for claim_id in fact_ids(match.group(0)):
            if claim_id not in numbers:
                numbers[claim_id] = len(order) + 1
                order.append(claim_id)
            markers.append(f"[{numbers[claim_id]}]")
        return "".join(markers)

    display = FACT_RE.sub(replace, text)
    display = COMMENT_RE.sub("", display).strip() + "\n"
    return display, order, numbers


def make_markdown_display(text, claims):
    display, order, numbers = replace_fact_markers(text)
    entries = []
    for claim_id in order:
        claim = claims[claim_id]
        number = numbers[claim_id]
        source = str(claim.get("source", "未注明来源"))
        source_date = str(claim.get("source_date", ""))
        url = str(claim.get("url", "")).strip()
        label = source + (f"（{source_date}）" if source_date else "")
        entries.append(f"[{number}] [{label}]({url})" if url else f"[{number}] {label}")

    lines = display.splitlines()
    source_index = next(
        (idx for idx, line in enumerate(lines) if line.strip() == "## 数据来源"), None
    )
    if source_index is not None:
        end = len(lines)
        for idx in range(source_index + 1, len(lines)):
            stripped = lines[idx].strip()
            if re.match(r"^#{2,3}\s+", stripped) or stripped == DISCLAIMER:
                end = idx
                break
        lines = lines[:source_index + 1] + [""] + entries + [""] + lines[end:]
    elif lines and lines[-1].strip() == DISCLAIMER:
        body = lines[:-1]
        while body and not body[-1].strip():
            body.pop()
        lines = body + ["", "## 数据来源", ""] + entries + ["", DISCLAIMER]
    else:
        lines.extend(["", "## 数据来源", ""] + entries)
    return "\n".join(lines).rstrip() + "\n"


def make_lark_xml_display(text, claims):
    display, order, numbers = replace_fact_markers(text)
    items = []
    for claim_id in order:
        claim = claims[claim_id]
        source = str(claim.get("source", "未注明来源"))
        source_date = str(claim.get("source_date", ""))
        label = source + (f"（{source_date}）" if source_date else "")
        safe_label = html.escape(label)
        url = str(claim.get("url", "")).strip()
        content = (
            f'<a href="{html.escape(url, quote=True)}">{safe_label}</a>'
            if url else safe_label
        )
        items.append(f'  <li seq="auto">{content}</li>')

    source_section = "<h2>数据来源</h2>\n<ol>\n" + "\n".join(items) + "\n</ol>\n\n"
    disclaimer_match = XML_DISCLAIMER_RE.search(display.strip())
    if disclaimer_match is None:
        raise ValueError("飞书 XML 缺少末尾免责声明")

    disclaimer_start = disclaimer_match.start()
    before_disclaimer = display.strip()[:disclaimer_start].rstrip()
    old_sources = re.search(
        r"<h[1-9](?:\s+[^>]*)?>\s*数据来源\s*</h[1-9]>",
        before_disclaimer,
        re.S,
    )
    if old_sources is not None:
        before_disclaimer = before_disclaimer[:old_sources.start()].rstrip()

    disclaimer = display.strip()[disclaimer_match.start():disclaimer_match.end()].strip()
    return f"{before_disclaimer}\n\n{source_section}{disclaimer}\n"


def make_display(text, claims, output_format="markdown"):
    if output_format == "markdown":
        return make_markdown_display(text, claims)
    if output_format == "lark-xml":
        return make_lark_xml_display(text, claims)
    raise ValueError(f"未知输出格式: {output_format}")


def self_test():
    data = {
        "meta": {"research_object": "示例公司", "as_of": "2026-07-20"},
        "claims": [{
            "claim_id": "revenue_q1", "text": "一季度收入为 100",
            "source": "公司公告", "source_date": "2026-04-30",
            "url": "https://example.com", "source_type": "official_filing",
            "usage_type": "hard_fact", "value": 100, "unit": "CNY mn",
        }],
    }
    source = (
        "# 示例报告\n\n信息截止日：2026-07-20\n\n## 结论\n\n"
        "一季度收入为 100。{fact:revenue_q1}\n\n" + DISCLAIMER
    )
    errors, _ = validate_facts(data)
    if errors:
        raise AssertionError(errors)
    errors, _ = validate_source(source, claim_map(data), "markdown")
    if errors:
        raise AssertionError(errors)
    output = make_display(source, claim_map(data))
    if ("{fact:" in output or "## 数据来源" not in output or "[1]" not in output
            or not output.rstrip().endswith(DISCLAIMER)):
        raise AssertionError(output)
    source_with_old_section = source.replace(
        "\n\n" + DISCLAIMER,
        "\n\n## 数据来源\n\n旧来源。\n\n" + DISCLAIMER,
    )
    replaced = make_display(source_with_old_section, claim_map(data))
    if "旧来源" in replaced or not replaced.rstrip().endswith(DISCLAIMER):
        raise AssertionError(replaced)

    xml_source = (
        "<title>示例报告</title>\n\n"
        "<p>信息截止日：2026-07-20</p>\n\n"
        "<h1>结论</h1>\n\n"
        "<p>一季度收入为 100。{fact:revenue_q1}</p>\n\n"
        f"<p>{DISCLAIMER}</p>"
    )
    errors, _ = validate_source(xml_source, claim_map(data), "lark-xml")
    if errors:
        raise AssertionError(errors)
    xml_output = make_display(xml_source, claim_map(data), "lark-xml")
    if ("{fact:" in xml_output or "<h2>数据来源</h2>" not in xml_output
            or "[1]" not in xml_output
            or not XML_DISCLAIMER_RE.search(xml_output.strip())):
        raise AssertionError(xml_output)
    xml_with_old_section = xml_source.replace(
        f"\n\n<p>{DISCLAIMER}</p>",
        f"\n\n<h2>数据来源</h2>\n<p>旧来源。</p>\n\n<p>{DISCLAIMER}</p>",
    )
    xml_replaced = make_display(xml_with_old_section, claim_map(data), "lark-xml")
    if "旧来源" in xml_replaced:
        raise AssertionError(xml_replaced)
    emit("SELF_TEST_PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验研究事实与引用，并生成读者版 Markdown 或飞书 XML。")
    parser.add_argument("source_file", nargs="?")
    parser.add_argument("facts_json", nargs="?")
    parser.add_argument("--format", choices=("markdown", "lark-xml"), default="markdown")
    parser.add_argument("--output", help="读者版输出路径")
    parser.add_argument("--check-only", action="store_true", help="只校验，不生成输出")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0
    if not args.source_file or not args.facts_json:
        parser.error("需要 source_file 和 facts_json，或使用 --self-test")
    if not args.check_only and not args.output:
        parser.error("生成读者版时必须提供 --output")

    try:
        source = Path(args.source_file).read_text(encoding="utf-8")
        data = load_json(args.facts_json)
    except Exception as exc:
        emit(f"[错误] 无法读取输入: {exc}")
        return 1

    facts_errors, facts_warnings = validate_facts(data)
    claims = claim_map(data)
    source_errors, source_warnings = validate_source(source, claims, args.format)
    for item in facts_warnings + source_warnings:
        emit(f"[警告] {item}")
    for item in facts_errors + source_errors:
        emit(f"[错误] {item}")
    if facts_errors or source_errors:
        return 1
    if args.check_only:
        emit("校验通过")
        return 0

    try:
        output_path = Path(args.output).resolve()
        if output_path in {Path(args.source_file).resolve(), Path(args.facts_json).resolve()}:
            raise ValueError("输出路径不能覆盖输入文件")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(make_display(source, claims, args.format), encoding="utf-8")
    except Exception as exc:
        emit(f"[错误] 生成失败: {exc}")
        return 1
    emit(f"已生成: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
