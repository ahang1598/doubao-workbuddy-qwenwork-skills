#!/usr/bin/env python3
"""Validate a build-club-recruitment-kit RecruitmentBrief JSON file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
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
VALID_SELECTION_FORMATS = {
    "open_enrollment",
    "interview",
    "audition",
    "portfolio",
    "written_test",
    "mixed",
}
PLACEHOLDER_RE = re.compile(r"\[待确认(?:[:：][^\]]+)?\]")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"文件不存在: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}") from exc


def get_path(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def walk_strings(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((prefix, value))
    elif isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            found.extend(walk_strings(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk_strings(item, f"{prefix}[{index}]"))
    return found


def is_iso_date_or_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip() or PLACEHOLDER_RE.search(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


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

    for section in ("club", "campaign", "message", "selection", "staffing", "output_options"):
        if not isinstance(data.get(section), dict):
            errors.append(f"{section} 必须是 object")

    if is_missing(get_path(data, "club.name")):
        errors.append("club.name 是所有任务的必填字段")

    outputs = data.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("outputs 必须是非空数组")
        outputs = []
    else:
        invalid = sorted({item for item in outputs if item not in VALID_OUTPUTS})
        if invalid:
            errors.append(f"outputs 包含未知值: {', '.join(map(str, invalid))}")
        if len(outputs) != len(set(outputs)):
            errors.append("outputs 不得包含重复项")

    branch_requirements = {
        "recruitment_flow": ["campaign.goal", "campaign.audiences", "campaign.timeline"],
        "poster_copy": ["campaign.audiences", "message.core_values", "campaign.cta.action"],
        "wechat_article": ["campaign.audiences", "message.core_values", "campaign.cta.action"],
        "speech": ["campaign.audiences", "message.core_values", "campaign.cta.action"],
        "interview_kit": ["selection.format", "selection.competencies"],
        "booth_script": ["campaign.audiences", "message.core_values", "campaign.cta.action"],
        "shift_roster": ["staffing.members", "staffing.shifts"],
    }
    for output in outputs:
        for field in branch_requirements.get(output, []):
            if is_missing(get_path(data, field)):
                message = f"{output} 缺少最小输入 {field}"
                (errors if review_gate else warnings).append(message)

    selection_format = get_path(data, "selection.format")
    if "interview_kit" not in outputs:
        if selection_format in VALID_SELECTION_FORMATS:
            errors.append("未请求 interview_kit 时 selection.format 必须为空或待确认占位符")
    elif selection_format not in VALID_SELECTION_FORMATS:
        message = "interview_kit 需要明确 selection.format"
        (errors if review_gate else warnings).append(message)

    if "group_notices" in outputs:
        timeline = get_path(data, "campaign.timeline")
        scenarios = get_path(data, "output_options.notice_scenarios")
        if is_missing(timeline) and is_missing(scenarios):
            message = "group_notices 需要 campaign.timeline 或 output_options.notice_scenarios"
            (errors if review_gate else warnings).append(message)

    facts = data.get("facts")
    if not isinstance(facts, list):
        errors.append("facts 必须是数组")
        facts = []

    seen_fact_values: dict[str, Any] = {}
    for index, fact in enumerate(facts):
        prefix = f"facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{prefix} 必须是 object")
            continue
        field = fact.get("field")
        status = fact.get("status")
        if not isinstance(field, str) or not field.strip():
            errors.append(f"{prefix}.field 必须是非空字符串")
        if status not in VALID_FACT_STATUSES:
            errors.append(f"{prefix}.status 非法: {status!r}")
        if field in seen_fact_values and seen_fact_values[field] != fact.get("value"):
            errors.append(f"同一事实字段出现不同值: {field}")
        elif isinstance(field, str):
            seen_fact_values[field] = fact.get("value")
            structured_value = get_path(data, field)
            if structured_value is not None and structured_value != fact.get("value"):
                errors.append(
                    f"事实记录 {field} 与 Brief 字段不一致: {fact.get('value')!r} != {structured_value!r}"
                )

        unresolved = status in {"assumption", "placeholder", "conflict"}
        if unresolved and (fact.get("critical") or review_gate):
            message = f"未解决事实 {field}: {status}"
            (errors if review_gate else warnings).append(message)
        if status == "verified_public" and is_missing(fact.get("source")):
            errors.append(f"{prefix} 标为 verified_public 时必须填写 source")

    fact_fields = {
        fact.get("field")
        for fact in facts
        if isinstance(fact, dict) and isinstance(fact.get("field"), str)
    }
    required_fact_fields = {"club.name"}
    public_outputs = {
        "recruitment_flow",
        "poster_copy",
        "wechat_article",
        "speech",
        "group_notices",
        "booth_script",
    }
    if public_outputs.intersection(outputs):
        required_fact_fields.add("campaign.cta.action")
        if not is_missing(get_path(data, "campaign.cta.deadline")):
            required_fact_fields.add("campaign.cta.deadline")
        if not is_missing(get_path(data, "campaign.cta.link_or_placeholder")):
            required_fact_fields.add("campaign.cta.link_or_placeholder")
    if review_gate:
        missing_fact_records = sorted(required_fact_fields - fact_fields)
        if missing_fact_records:
            errors.append(f"review/publish_ready 缺少关键事实记录: {', '.join(missing_fact_records)}")

    placeholder_paths = [
        path for path, value in walk_strings(data) if PLACEHOLDER_RE.search(value)
    ]
    if placeholder_paths:
        message = f"发现 {len(placeholder_paths)} 个待确认占位符"
        (errors if review_gate else warnings).append(message)

    timeline = get_path(data, "campaign.timeline")
    if review_gate and isinstance(timeline, list):
        for index, item in enumerate(timeline):
            if not isinstance(item, dict):
                continue
            for field in ("id", "label", "start", "end", "location", "owner"):
                if is_missing(item.get(field)):
                    errors.append(f"campaign.timeline[{index}].{field} 在 review/publish_ready 时必填")
            for field in ("start", "end"):
                value = item.get(field)
                is_placeholder = isinstance(value, str) and bool(PLACEHOLDER_RE.search(value))
                if not is_missing(value) and not is_placeholder and not is_iso_date_or_datetime(value):
                    errors.append(f"campaign.timeline[{index}].{field} 必须使用 ISO 8601 日期或时间")
    deadline = get_path(data, "campaign.cta.deadline")
    deadline_is_placeholder = isinstance(deadline, str) and bool(PLACEHOLDER_RE.search(deadline))
    if review_gate and not is_missing(deadline) and not deadline_is_placeholder and not is_iso_date_or_datetime(deadline):
        errors.append("campaign.cta.deadline 必须使用 ISO 8601 日期或时间")

    competencies = get_path(data, "selection.competencies")
    if isinstance(competencies, list) and competencies:
        competency_ids: set[str] = set()
        weights: list[float] = []
        for index, competency in enumerate(competencies):
            if not isinstance(competency, dict):
                errors.append(f"selection.competencies[{index}] 必须是 object")
                continue
            comp_id = competency.get("id")
            if not isinstance(comp_id, str) or not comp_id.strip():
                errors.append(f"selection.competencies[{index}].id 必须是非空字符串")
            elif comp_id in competency_ids:
                errors.append(f"胜任力 id 重复: {comp_id}")
            else:
                competency_ids.add(comp_id)
            weight = competency.get("weight")
            if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0:
                errors.append(f"selection.competencies[{index}].weight 必须是非负数")
            else:
                weights.append(float(weight))
        if weights and abs(sum(weights) - 1.0) > 0.01:
            warnings.append(f"胜任力权重合计为 {sum(weights):.3f}，建议为 1")

    staffing = data.get("staffing")
    if isinstance(staffing, dict):
        members = staffing.get("members", [])
        shifts = staffing.get("shifts", [])
        if not isinstance(members, list):
            errors.append("staffing.members 必须是数组")
            members = []
        if not isinstance(shifts, list):
            errors.append("staffing.shifts 必须是数组")
            shifts = []
        member_ids = [m.get("id") for m in members if isinstance(m, dict)]
        shift_ids = [s.get("id") for s in shifts if isinstance(s, dict)]
        if len(member_ids) != len(set(member_ids)):
            errors.append("staffing.members 的 id 不得重复")
        if len(shift_ids) != len(set(shift_ids)):
            errors.append("staffing.shifts 的 id 不得重复")
        known_shifts = {sid for sid in shift_ids if isinstance(sid, str)}
        for index, member in enumerate(members):
            if not isinstance(member, dict):
                errors.append(f"staffing.members[{index}] 必须是 object")
                continue
            available = member.get("available_shift_ids", [])
            if not isinstance(available, list):
                errors.append(f"staffing.members[{index}].available_shift_ids 必须是数组")
            else:
                unknown = sorted({sid for sid in available if sid not in known_shifts})
                if unknown:
                    errors.append(
                        f"staffing.members[{index}] 引用未知班次: {', '.join(map(str, unknown))}"
                    )
        for index, shift in enumerate(shifts):
            if not isinstance(shift, dict):
                errors.append(f"staffing.shifts[{index}] 必须是 object")
                continue
            roles = shift.get("roles")
            if not isinstance(roles, list) or not roles:
                errors.append(f"staffing.shifts[{index}].roles 必须是非空数组")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="RecruitmentBrief JSON")
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
