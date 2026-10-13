#!/usr/bin/env python3
"""Validate a structured RecruitmentPacket for consistency and safety."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


VALID_OUTPUTS = {
    "recruitment_flow",
    "poster_copy",
    "wechat_article",
    "speech",
    "interview_kit",
    "group_notices",
    "booth_script",
    "shift_roster",
}
VALID_PACKET_STATUSES = {"draft", "review", "publish_ready"}
VALID_FACT_STATUSES = {
    "confirmed_by_user",
    "verified_public",
    "assumption",
    "placeholder",
    "conflict",
}
PLACEHOLDER_RE = re.compile(r"\[待确认(?:[:：][^\]]+)?\]")
SENSITIVE_RE = re.compile(
    r"民族|宗教|政治面貌|政治观点|性取向|恋爱|婚姻|结婚|生育|家庭经济|父母职业|"
    r"家庭关系|疾病|病史|残障|残疾|MBTI|星座|身份证|宿舍|精确课表",
    re.IGNORECASE,
)
SELECTION_RE = re.compile(r"面试|试训|笔试|试演|作品集|录取")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"文件不存在: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}") from exc


def validate(data: Any, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["顶层必须是 JSON object"], warnings

    if data.get("schema_version") != "1.0":
        errors.append("schema_version 必须为 '1.0'")
    packet_status = data.get("packet_status")
    if packet_status not in VALID_PACKET_STATUSES:
        errors.append("packet_status 必须是 draft、review 或 publish_ready")
        packet_status = "draft"
    review_gate = strict or packet_status in {"review", "publish_ready"}
    publish_gate = strict or packet_status == "publish_ready"

    brief = data.get("brief_snapshot")
    materials = data.get("materials")
    if not isinstance(brief, dict):
        errors.append("brief_snapshot 必须是 object")
        brief = {}
    if not isinstance(materials, dict):
        errors.append("materials 必须是 object")
        materials = {}

    outputs = brief.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("brief_snapshot.outputs 必须是非空数组")
        outputs = []
    else:
        invalid = sorted({item for item in outputs if item not in VALID_OUTPUTS})
        if invalid:
            errors.append(f"brief_snapshot.outputs 包含未知值: {', '.join(map(str, invalid))}")

    unrequested_materials = sorted(set(materials) - set(outputs))
    if unrequested_materials:
        errors.append(
            "materials 含未请求物料: " + ", ".join(unrequested_materials)
        )

    fact_values = brief.get("fact_values", {})
    fact_statuses = brief.get("fact_statuses", {})
    forbidden_claims = brief.get("forbidden_claims", [])
    competency_ids = set(brief.get("competency_ids", [])) if isinstance(brief.get("competency_ids", []), list) else set()
    if not isinstance(fact_values, dict):
        errors.append("brief_snapshot.fact_values 必须是 object")
        fact_values = {}
    if not isinstance(fact_statuses, dict):
        errors.append("brief_snapshot.fact_statuses 必须是 object")
        fact_statuses = {}
    if not isinstance(forbidden_claims, list):
        errors.append("brief_snapshot.forbidden_claims 必须是数组")
        forbidden_claims = []

    if review_gate:
        missing_statuses = sorted(set(fact_values) - set(fact_statuses))
        missing_values = sorted(set(fact_statuses) - set(fact_values))
        if missing_statuses:
            errors.append(f"事实快照缺少状态: {', '.join(missing_statuses)}")
        if missing_values:
            errors.append(f"事实状态缺少对应值: {', '.join(missing_values)}")

    for field, status in fact_statuses.items():
        if status not in VALID_FACT_STATUSES:
            errors.append(f"事实状态非法 {field}: {status!r}")
        elif status in {"assumption", "placeholder", "conflict"}:
            message = f"未解决事实 {field}: {status}"
            (errors if review_gate else warnings).append(message)

    fact_placeholders = [
        field
        for field, value in fact_values.items()
        if isinstance(value, str) and PLACEHOLDER_RE.search(value)
    ]
    if fact_placeholders:
        message = f"事实快照含待确认占位符: {', '.join(sorted(fact_placeholders))}"
        (errors if review_gate else warnings).append(message)

    observed_values: dict[str, Any] = {}
    placeholder_count = 0
    for output in outputs:
        material = materials.get(output)
        if not isinstance(material, dict):
            errors.append(f"缺少物料或结构错误: {output}")
            continue
        status = material.get("status")
        if status not in VALID_PACKET_STATUSES:
            errors.append(f"materials.{output}.status 非法")
        elif publish_gate and status != "publish_ready":
            errors.append(f"定稿时 materials.{output}.status 必须为 publish_ready")

        content = material.get("content_markdown")
        if not isinstance(content, str) or not content.strip():
            message = f"materials.{output}.content_markdown 为空"
            (errors if review_gate else warnings).append(message)
            content = ""
        placeholders = PLACEHOLDER_RE.findall(content)
        placeholder_count += len(placeholders)
        for claim in forbidden_claims:
            if isinstance(claim, str) and claim.strip() and claim in content:
                errors.append(f"materials.{output} 命中禁用说法: {claim}")

        facts_used = material.get("facts_used", {})
        if not isinstance(facts_used, dict):
            errors.append(f"materials.{output}.facts_used 必须是 object")
            facts_used = {}
        for field, value in facts_used.items():
            if field in fact_values and fact_values[field] != value:
                errors.append(
                    f"{output} 的事实 {field} 与 brief_snapshot 不一致: {value!r} != {fact_values[field]!r}"
                )
            if field in observed_values and observed_values[field] != value:
                errors.append(f"跨物料事实冲突 {field}: {observed_values[field]!r} != {value!r}")
            else:
                observed_values[field] = value

        if output == "poster_copy" and "interview_kit" not in outputs and SELECTION_RE.search(content):
            selection_status = fact_statuses.get("selection.format")
            if selection_status not in {"confirmed_by_user", "verified_public"}:
                errors.append("poster_copy 含未确认的选拔流程或选拔形式")

    if placeholder_count:
        message = f"物料正文中发现 {placeholder_count} 个待确认占位符"
        (errors if review_gate else warnings).append(message)

    if "interview_kit" in outputs and isinstance(materials.get("interview_kit"), dict):
        structured = materials["interview_kit"].get("structured", {})
        if not isinstance(structured, dict):
            errors.append("interview_kit.structured 必须是 object")
            structured = {}
        questions = structured.get("questions", [])
        if not isinstance(questions, list):
            errors.append("interview_kit.structured.questions 必须是数组")
            questions = []
        if not questions:
            message = "interview_kit 没有结构化问题"
            (errors if review_gate else warnings).append(message)
        for index, question in enumerate(questions):
            prefix = f"interview_kit.questions[{index}]"
            if not isinstance(question, dict):
                errors.append(f"{prefix} 必须是 object")
                continue
            competency_id = question.get("competency_id")
            if not isinstance(competency_id, str) or not competency_id.strip():
                errors.append(f"{prefix}.competency_id 必须是非空字符串")
            elif competency_ids and competency_id not in competency_ids:
                errors.append(f"{prefix} 引用未知胜任力: {competency_id}")
            question_text = question.get("question")
            if not isinstance(question_text, str) or not question_text.strip():
                errors.append(f"{prefix}.question 必须是非空字符串")
                question_text = ""
            follow_ups = question.get("follow_ups", [])
            if not isinstance(follow_ups, list):
                errors.append(f"{prefix}.follow_ups 必须是数组")
                follow_ups = []
            combined = " ".join([question_text] + [str(item) for item in follow_ups])
            match = SENSITIVE_RE.search(combined)
            if match:
                errors.append(f"{prefix} 包含敏感或无关问题: {match.group(0)}")
            anchors = question.get("anchors")
            if review_gate and (not isinstance(anchors, dict) or not anchors):
                errors.append(f"{prefix}.anchors 在定稿时必须是非空 object")

    if "shift_roster" in outputs and isinstance(materials.get("shift_roster"), dict):
        structured = materials["shift_roster"].get("structured", {})
        if not isinstance(structured, dict):
            errors.append("shift_roster.structured 必须是 object")
        else:
            roster_status = structured.get("status")
            if roster_status not in {"feasible", "partial", "infeasible"}:
                errors.append("shift_roster.structured.status 必须是 feasible、partial 或 infeasible")
            unfilled = structured.get("unfilled", [])
            if not isinstance(unfilled, list):
                errors.append("shift_roster.structured.unfilled 必须是数组")
                unfilled = []
            if roster_status in {"partial", "infeasible"} and not unfilled:
                errors.append(f"{roster_status} 排班必须列出 unfilled")
            assignments = structured.get("assignments", [])
            if not isinstance(assignments, list):
                errors.append("shift_roster.structured.assignments 必须是数组")
                assignments = []
            if roster_status == "partial" and not assignments:
                errors.append("完全无可行分配时状态必须是 infeasible，不得使用 partial")
            if roster_status == "infeasible" and assignments:
                errors.append("存在可行分配时状态不得使用 infeasible")
            content = materials["shift_roster"].get("content_markdown", "")
            if roster_status in {"partial", "infeasible"} and isinstance(content, str) and re.search(r"全部(?:覆盖|排满)|无缺岗", content):
                errors.append(f"{roster_status} 排班正文不得声称全部覆盖或无缺岗")
            if review_gate and roster_status in {"partial", "infeasible"}:
                errors.append(f"排班状态为 {roster_status}，不得进入 review/publish_ready")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="RecruitmentPacket JSON")
    parser.add_argument("--strict", action="store_true", help="把定稿缺口视为错误")
    args = parser.parse_args()

    try:
        data = load_json(args.input)
    except ValueError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)], "warnings": []}, ensure_ascii=False, indent=2))
        return 1

    errors, warnings = validate(data, args.strict)
    print(
        json.dumps(
            {"valid": not errors, "errors": errors, "warnings": warnings},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
