#!/usr/bin/env python3
"""Shared structural helpers for V5.7 contract draft JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

FACT_STATUSES = {
    "confirmed",
    "derived",
    "standard_term",
    "standard_parameter",
    "pending",
    "disputed",
}
REQUIRED_TOP_LEVEL = {
    "title",
    "placeholder",
    "use_comments",
    "use_colors",
    "allow_tables",
    "contract_form",
    "signature_ready",
    "facts",
    "sections",
    "appendices",
    "signature",
}


def load_contract(path: str | Path) -> dict[str, Any]:
    """Load a contract JSON object from disk."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("草案 JSON 顶层必须为对象")
    return data


def as_list(value: Any) -> list[Any]:
    """Return list values unchanged and treat malformed values as empty."""
    return value if isinstance(value, list) else []


def _iter_table_text(table: Any, path: str) -> Iterator[tuple[str, str]]:
    if not isinstance(table, list):
        return
    for row_index, row in enumerate(table):
        if not isinstance(row, list):
            continue
        for column_index, value in enumerate(row):
            yield f"{path}[{row_index}][{column_index}]", str(value)


def iter_contract_text(data: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield every text value that can appear in the generated contract."""
    yield "$.title", str(data.get("title", ""))
    for index, section in enumerate(as_list(data.get("sections"))):
        if isinstance(section, dict):
            yield f"$.sections[{index}].text", str(section.get("text", ""))
    for table_index, table in enumerate(as_list(data.get("tables"))):
        yield from _iter_table_text(table, f"$.tables[{table_index}]")
    for index, appendix in enumerate(as_list(data.get("appendices"))):
        if not isinstance(appendix, dict):
            continue
        yield f"$.appendices[{index}].number", str(appendix.get("number", ""))
        yield f"$.appendices[{index}].title", str(appendix.get("title", ""))
        for paragraph_index, paragraph in enumerate(as_list(appendix.get("content"))):
            yield f"$.appendices[{index}].content[{paragraph_index}]", str(paragraph)
        for table_index, table in enumerate(as_list(appendix.get("tables"))):
            yield from _iter_table_text(table, f"$.appendices[{index}].tables[{table_index}]")
    for index, party in enumerate(as_list(data.get("signature"))):
        yield f"$.signature[{index}]", str(party)


def contract_text(data: dict[str, Any]) -> str:
    """Join all generated contract text for substring checks."""
    return "\n".join(text for _, text in iter_contract_text(data))


def _validate_table(table: Any, path: str, errors: list[str]) -> None:
    if not isinstance(table, list):
        errors.append(f"{path} 必须为行数组")
        return
    for row_index, row in enumerate(table):
        if not isinstance(row, list):
            errors.append(f"{path}[{row_index}] 必须为单元格数组")
        elif not row:
            errors.append(f"{path}[{row_index}] 不得为空行")


def validate_schema(data: Any) -> list[str]:
    """Validate the documented V5.7 schema subset without third-party dependencies."""
    if not isinstance(data, dict):
        return ["$ 顶层必须为对象"]
    errors: list[str] = []
    for key in sorted(REQUIRED_TOP_LEVEL - set(data)):
        errors.append(f"$.{key} 为必填字段")
    if not isinstance(data.get("title"), str) or not data.get("title", "").strip():
        errors.append("$.title 必须为非空字符串")
    if data.get("placeholder") != "":
        errors.append("$.placeholder 必须为空字符串")
    for key in ("use_comments", "use_colors", "allow_tables", "signature_ready"):
        if key in data and not isinstance(data[key], bool):
            errors.append(f"$.{key} 必须为布尔值")
    if data.get("use_comments") is not False:
        errors.append("$.use_comments 必须为 false")
    if data.get("use_colors") is not False:
        errors.append("$.use_colors 必须为 false")
    if data.get("contract_form") not in {"single", "framework"}:
        errors.append("$.contract_form 必须为 single 或 framework")
    if "has_blanks" in data and not isinstance(data["has_blanks"], bool):
        errors.append("$.has_blanks 必须为布尔值")
    if "delivery_summary" in data and not isinstance(data["delivery_summary"], dict):
        errors.append("$.delivery_summary 必须为对象")

    profile = data.get("parameter_profile")
    if "parameter_profile" in data and not isinstance(profile, dict):
        errors.append("$.parameter_profile 必须为对象")
    if data.get("contract_form") == "single":
        if not isinstance(profile, dict):
            errors.append("$.parameter_profile 单项合同必须提供对象")
        else:
            for key in ("family", "role", "required"):
                if key not in profile:
                    errors.append(f"$.parameter_profile.{key} 为必填字段")
            if not isinstance(profile.get("family"), str) or not profile.get("family", "").strip():
                errors.append("$.parameter_profile.family 必须为非空字符串")
            if not isinstance(profile.get("role"), str) or not profile.get("role", "").strip():
                errors.append("$.parameter_profile.role 必须为非空字符串")
            if not isinstance(profile.get("required"), list) or not all(isinstance(item, str) for item in profile.get("required", [])):
                errors.append("$.parameter_profile.required 必须为字符串数组")
            if "not_applicable" in profile and not isinstance(profile["not_applicable"], dict):
                errors.append("$.parameter_profile.not_applicable 必须为对象")
            elif isinstance(profile.get("not_applicable"), dict) and not all(isinstance(value, str) for value in profile["not_applicable"].values()):
                errors.append("$.parameter_profile.not_applicable 的理由必须为字符串")

    facts = data.get("facts")
    if not isinstance(facts, list):
        errors.append("$.facts 必须为数组")
    else:
        for index, fact in enumerate(facts):
            path = f"$.facts[{index}]"
            if not isinstance(fact, dict):
                errors.append(f"{path} 必须为对象")
                continue
            for key in ("key", "value", "status"):
                if key not in fact:
                    errors.append(f"{path}.{key} 为必填字段")
            if "key" in fact and not isinstance(fact["key"], str):
                errors.append(f"{path}.key 必须为字符串")
            for key in ("source", "basis", "contract_slot", "note"):
                if key in fact and not isinstance(fact[key], str):
                    errors.append(f"{path}.{key} 必须为字符串")
            if fact.get("status") not in FACT_STATUSES:
                errors.append(f"{path}.status 不是允许的事实状态")
            for key in ("coverage_terms", "aliases", "forbidden_assertions"):
                if key in fact:
                    values = fact[key]
                    if not isinstance(values, list) or not values or not all(isinstance(item, str) and item for item in values):
                        errors.append(f"{path}.{key} 必须为非空字符串数组")
            if fact.get("status") == "standard_parameter":
                if not str(fact.get("basis", "")).strip():
                    errors.append(f"{path}.basis 标准参数必须提供适用依据")
                terms = fact.get("coverage_terms")
                if not isinstance(terms, list) or not terms or not all(isinstance(item, str) and item for item in terms):
                    errors.append(f"{path}.coverage_terms 标准参数必须提供非空字符串数组")
            if fact.get("status") == "pending":
                for key in ("aliases", "forbidden_assertions"):
                    values = fact.get(key)
                    if not isinstance(values, list) or not values or not all(isinstance(item, str) and item for item in values):
                        errors.append(f"{path}.{key} 待核查事实必须提供非空字符串数组")

    sections = data.get("sections")
    if not isinstance(sections, list):
        errors.append("$.sections 必须为数组")
    else:
        for index, section in enumerate(sections):
            path = f"$.sections[{index}]"
            if not isinstance(section, dict):
                errors.append(f"{path} 必须为对象")
            elif type(section.get("level")) is not int or section.get("level") not in {1, 2} or not isinstance(section.get("text"), str):
                errors.append(f"{path} 必须包含整数 level=1|2 和字符串 text")

    appendices = data.get("appendices")
    if not isinstance(appendices, list):
        errors.append("$.appendices 必须为数组")
    else:
        for index, appendix in enumerate(appendices):
            path = f"$.appendices[{index}]"
            if not isinstance(appendix, dict):
                errors.append(f"{path} 必须为对象")
                continue
            for key in ("number", "title"):
                if not isinstance(appendix.get(key), str) or not appendix.get(key, "").strip():
                    errors.append(f"{path}.{key} 必须为非空字符串")
            for key in ("source",):
                if key in appendix and not isinstance(appendix[key], str):
                    errors.append(f"{path}.{key} 必须为字符串")
            if "list_only" in appendix and not isinstance(appendix["list_only"], bool):
                errors.append(f"{path}.list_only 必须为布尔值")
            if "content" in appendix and (not isinstance(appendix["content"], list) or not all(isinstance(item, str) for item in appendix["content"])):
                errors.append(f"{path}.content 必须为字符串数组")
            if "tables" in appendix:
                if not isinstance(appendix["tables"], list):
                    errors.append(f"{path}.tables 必须为表格数组")
                else:
                    for table_index, table in enumerate(appendix["tables"]):
                        _validate_table(table, f"{path}.tables[{table_index}]", errors)

    signature = data.get("signature")
    if not isinstance(signature, list) or not all(isinstance(item, str) for item in signature):
        errors.append("$.signature 必须为字符串数组")
    elif data.get("contract_form") == "single" and not signature:
        errors.append("$.signature 单项合同必须提供签署主体以生成签署页")
    if "tables" in data:
        if not isinstance(data["tables"], list):
            errors.append("$.tables 必须为表格数组")
        else:
            for table_index, table in enumerate(data["tables"]):
                _validate_table(table, f"$.tables[{table_index}]", errors)
    return errors
