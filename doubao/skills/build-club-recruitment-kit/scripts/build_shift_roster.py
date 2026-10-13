#!/usr/bin/env python3
"""Build a deterministic, constraint-aware recruitment shift roster."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"文件不存在: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: 第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("输入顶层必须是 JSON object")
    staffing = data.get("staffing", data)
    if not isinstance(staffing, dict):
        raise ValueError("staffing 必须是 object")
    return staffing


def parse_minutes(value: Any, field: str) -> int:
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是 HH:MM")
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"{field} 必须是 HH:MM: {value!r}") from exc
    return parsed.hour * 60 + parsed.minute


def normalize(staffing: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    members = staffing.get("members")
    shifts = staffing.get("shifts")
    defaults = staffing.get("defaults", {})
    if not isinstance(members, list) or not members:
        raise ValueError("staffing.members 必须是非空数组")
    if not isinstance(shifts, list) or not shifts:
        raise ValueError("staffing.shifts 必须是非空数组")
    if not isinstance(defaults, dict):
        raise ValueError("staffing.defaults 必须是 object")

    default_max = defaults.get("max_shifts_per_person", 2)
    default_consecutive = defaults.get("max_consecutive_shifts", 1)
    if not isinstance(default_max, int) or isinstance(default_max, bool) or default_max < 1:
        raise ValueError("defaults.max_shifts_per_person 必须是正整数")
    if not isinstance(default_consecutive, int) or isinstance(default_consecutive, bool) or default_consecutive < 1:
        raise ValueError("defaults.max_consecutive_shifts 必须是正整数")

    normalized_members: list[dict[str, Any]] = []
    member_ids: set[str] = set()
    for index, raw in enumerate(members):
        if not isinstance(raw, dict):
            raise ValueError(f"members[{index}] 必须是 object")
        member_id = raw.get("id")
        if not isinstance(member_id, str) or not member_id.strip():
            raise ValueError(f"members[{index}].id 必须是非空字符串")
        if member_id in member_ids:
            raise ValueError(f"成员 id 重复: {member_id}")
        member_ids.add(member_id)
        available = raw.get("available_shift_ids", [])
        if not isinstance(available, list):
            raise ValueError(f"members[{index}].available_shift_ids 必须是数组")
        skills = raw.get("skills", [])
        preferred = raw.get("preferred_shift_ids", [])
        if not isinstance(skills, list) or not isinstance(preferred, list):
            raise ValueError(f"members[{index}] 的 skills/preferred_shift_ids 必须是数组")
        max_shifts = raw.get("max_shifts", default_max)
        max_consecutive = raw.get("max_consecutive_shifts", default_consecutive)
        if not isinstance(max_shifts, int) or isinstance(max_shifts, bool) or max_shifts < 1:
            raise ValueError(f"members[{index}].max_shifts 必须是正整数")
        if not isinstance(max_consecutive, int) or isinstance(max_consecutive, bool) or max_consecutive < 1:
            raise ValueError(f"members[{index}].max_consecutive_shifts 必须是正整数")
        normalized_members.append(
            {
                "id": member_id,
                "display_name": str(raw.get("display_name") or member_id),
                "skills": {str(item) for item in skills},
                "available_shift_ids": {str(item) for item in available},
                "preferred_shift_ids": {str(item) for item in preferred},
                "max_shifts": max_shifts,
                "max_consecutive_shifts": max_consecutive,
            }
        )

    normalized_shifts: list[dict[str, Any]] = []
    shift_ids: set[str] = set()
    for index, raw in enumerate(shifts):
        if not isinstance(raw, dict):
            raise ValueError(f"shifts[{index}] 必须是 object")
        shift_id = raw.get("id")
        if not isinstance(shift_id, str) or not shift_id.strip():
            raise ValueError(f"shifts[{index}].id 必须是非空字符串")
        if shift_id in shift_ids:
            raise ValueError(f"班次 id 重复: {shift_id}")
        shift_ids.add(shift_id)
        date = raw.get("date")
        if not isinstance(date, str) or not date.strip():
            raise ValueError(f"shifts[{index}].date 必须是非空字符串")
        start = parse_minutes(raw.get("start"), f"shifts[{index}].start")
        end = parse_minutes(raw.get("end"), f"shifts[{index}].end")
        if end <= start:
            raise ValueError(f"shifts[{index}] 的 end 必须晚于 start")
        roles = raw.get("roles")
        if not isinstance(roles, list) or not roles:
            raise ValueError(f"shifts[{index}].roles 必须是非空数组")
        normalized_roles: list[dict[str, Any]] = []
        role_names: set[str] = set()
        for role_index, role in enumerate(roles):
            if not isinstance(role, dict):
                raise ValueError(f"shifts[{index}].roles[{role_index}] 必须是 object")
            name = role.get("name")
            count = role.get("min_count")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"shifts[{index}].roles[{role_index}].name 必须是非空字符串")
            if name in role_names:
                raise ValueError(f"班次 {shift_id} 的岗位重复: {name}")
            role_names.add(name)
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise ValueError(f"班次 {shift_id} 岗位 {name} 的 min_count 必须是正整数")
            required = role.get("required_skills", [])
            preferred_skills = role.get("preferred_skills", [])
            if not isinstance(required, list) or not isinstance(preferred_skills, list):
                raise ValueError(f"班次 {shift_id} 岗位 {name} 的技能字段必须是数组")
            normalized_roles.append(
                {
                    "name": name,
                    "min_count": count,
                    "required_skills": {str(item) for item in required},
                    "preferred_skills": {str(item) for item in preferred_skills},
                }
            )
        normalized_shifts.append(
            {
                "id": shift_id,
                "label": str(raw.get("label") or shift_id),
                "date": date,
                "start": start,
                "end": end,
                "start_text": raw.get("start"),
                "end_text": raw.get("end"),
                "location": str(raw.get("location") or ""),
                "roles": normalized_roles,
            }
        )

    unknown_availability = sorted(
        {
            shift_id
            for member in normalized_members
            for shift_id in member["available_shift_ids"]
            if shift_id not in shift_ids
        }
    )
    if unknown_availability:
        raise ValueError(f"成员可用性引用未知班次: {', '.join(unknown_availability)}")

    normalized_shifts.sort(key=lambda item: (item["date"], item["start"], item["end"], item["id"]))
    return normalized_members, normalized_shifts, {
        "max_shifts_per_person": default_max,
        "max_consecutive_shifts": default_consecutive,
    }


def overlaps(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return (
        first["date"] == second["date"]
        and first["start"] < second["end"]
        and second["start"] < first["end"]
    )


def exceeds_consecutive(
    assigned_shift_ids: set[str],
    candidate_shift_id: str,
    shift_by_id: dict[str, dict[str, Any]],
    limit: int,
) -> bool:
    shifts = [shift_by_id[shift_id] for shift_id in assigned_shift_ids | {candidate_shift_id}]
    shifts.sort(key=lambda item: (item["date"], item["start"], item["end"], item["id"]))
    longest = 0
    current = 0
    previous: dict[str, Any] | None = None
    for shift in shifts:
        if previous and previous["date"] == shift["date"] and previous["end"] == shift["start"]:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        previous = shift
    return longest > limit


def build_roster(staffing: dict[str, Any]) -> dict[str, Any]:
    members, shifts, _defaults = normalize(staffing)
    member_by_id = {member["id"]: member for member in members}
    shift_by_id = {shift["id"]: shift for shift in shifts}

    seats: list[dict[str, Any]] = []
    for shift in shifts:
        for role in shift["roles"]:
            for seat_index in range(role["min_count"]):
                seats.append(
                    {
                        "shift_id": shift["id"],
                        "role": role["name"],
                        "seat_index": seat_index,
                        "required_skills": role["required_skills"],
                        "preferred_skills": role["preferred_skills"],
                    }
                )

    workloads: Counter[str] = Counter()
    member_shift_ids: dict[str, set[str]] = defaultdict(set)
    assignments: list[dict[str, Any]] = []
    unfilled_seats: list[dict[str, Any]] = []

    def eligible(member: dict[str, Any], seat: dict[str, Any]) -> bool:
        shift_id = seat["shift_id"]
        if shift_id not in member["available_shift_ids"]:
            return False
        if not seat["required_skills"].issubset(member["skills"]):
            return False
        if workloads[member["id"]] >= member["max_shifts"]:
            return False
        if shift_id in member_shift_ids[member["id"]]:
            return False
        candidate_shift = shift_by_id[shift_id]
        if any(overlaps(candidate_shift, shift_by_id[other]) for other in member_shift_ids[member["id"]]):
            return False
        if exceeds_consecutive(
            member_shift_ids[member["id"]],
            shift_id,
            shift_by_id,
            member["max_consecutive_shifts"],
        ):
            return False
        return True

    remaining = list(seats)
    while remaining:
        choices: list[tuple[int, str, str, int, dict[str, Any], list[dict[str, Any]]]] = []
        for seat in remaining:
            candidates = [member for member in members if eligible(member, seat)]
            choices.append(
                (
                    len(candidates),
                    seat["shift_id"],
                    seat["role"],
                    seat["seat_index"],
                    seat,
                    candidates,
                )
            )
        _count, _shift_id, _role, _seat_index, seat, candidates = min(
            choices,
            key=lambda item: (item[0], item[1], item[2], item[3]),
        )
        remaining.remove(seat)

        if not candidates:
            unfilled_seats.append(seat)
            continue

        def candidate_score(member: dict[str, Any]) -> tuple[float, int, int, int, str]:
            load_ratio = workloads[member["id"]] / member["max_shifts"]
            preferred_shift_penalty = 0 if seat["shift_id"] in member["preferred_shift_ids"] else 1
            preferred_skill_count = len(seat["preferred_skills"] & member["skills"])
            return (
                load_ratio,
                workloads[member["id"]],
                preferred_shift_penalty,
                -preferred_skill_count,
                member["id"],
            )

        selected = min(candidates, key=candidate_score)
        shift = shift_by_id[seat["shift_id"]]
        assignments.append(
            {
                "shift_id": shift["id"],
                "shift_label": shift["label"],
                "date": shift["date"],
                "start": shift["start_text"],
                "end": shift["end_text"],
                "location": shift["location"],
                "role": seat["role"],
                "member_id": selected["id"],
                "display_name": selected["display_name"],
            }
        )
        workloads[selected["id"]] += 1
        member_shift_ids[selected["id"]].add(seat["shift_id"])

    missing_counts: Counter[tuple[str, str]] = Counter(
        (seat["shift_id"], seat["role"]) for seat in unfilled_seats
    )
    unfilled: list[dict[str, Any]] = []
    for (shift_id, role), missing_count in sorted(missing_counts.items()):
        shift = shift_by_id[shift_id]
        role_spec = next(item for item in shift["roles"] if item["name"] == role)
        available = [member for member in members if shift_id in member["available_shift_ids"]]
        skilled = [member for member in available if role_spec["required_skills"].issubset(member["skills"])]
        if not available:
            reason = "no_available_member"
        elif not skilled:
            reason = "required_skill_gap"
        else:
            reason = "capacity_overlap_or_consecutive_limit"
        unfilled.append(
            {
                "shift_id": shift_id,
                "shift_label": shift["label"],
                "role": role,
                "missing_count": missing_count,
                "reason": reason,
            }
        )

    assignments.sort(key=lambda item: (item["date"], item["start"], item["shift_id"], item["role"], item["member_id"]))
    workload_rows = [
        {
            "member_id": member["id"],
            "display_name": member["display_name"],
            "assigned_shifts": workloads[member["id"]],
            "max_shifts": member["max_shifts"],
        }
        for member in sorted(members, key=lambda item: item["id"])
    ]

    if not unfilled:
        status = "feasible"
    elif assignments:
        status = "partial"
    else:
        status = "infeasible"

    return {
        "schema_version": "1.0",
        "status": status,
        "assignments": assignments,
        "unfilled": unfilled,
        "workloads": workload_rows,
        "summary": {
            "required_seats": len(seats),
            "filled_seats": len(assignments),
            "unfilled_seats": len(unfilled_seats),
        },
    }


def write_csv(path: Path, result: dict[str, Any]) -> None:
    fieldnames = [
        "date",
        "start",
        "end",
        "shift_id",
        "shift_label",
        "location",
        "role",
        "member_id",
        "display_name",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result["assignments"])


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# 招新排班表",
        "",
        f"状态：`{result['status']}`",
        "",
        "| 日期 | 时间 | 班次 | 地点 | 岗位 | 成员 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in result["assignments"]:
        lines.append(
            f"| {row['date']} | {row['start']}-{row['end']} | {row['shift_label']} | "
            f"{row['location'] or '-'} | {row['role']} | {row['display_name']} |"
        )
    if not result["assignments"]:
        lines.append("| - | - | - | - | - | 无可行分配 |")

    lines.extend(["", "## 缺岗", ""])
    if result["unfilled"]:
        lines.extend(["| 班次 | 岗位 | 缺口 | 原因 |", "| --- | --- | --- | --- |"])
        for row in result["unfilled"]:
            lines.append(
                f"| {row['shift_label']} | {row['role']} | {row['missing_count']} | {row['reason']} |"
            )
    else:
        lines.append("无。")

    lines.extend(["", "## 负载", "", "| 成员 | 已排班 | 上限 |", "| --- | --- | --- |"])
    for row in result["workloads"]:
        lines.append(f"| {row['display_name']} | {row['assigned_shifts']} | {row['max_shifts']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="RecruitmentBrief 或 staffing JSON")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()

    try:
        staffing = load_json(args.input)
        result = build_roster(staffing)
        if args.output_json:
            args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.output_csv:
            write_csv(args.output_csv, result)
        if args.markdown:
            write_markdown(args.markdown, result)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "ok": result["status"] == "feasible",
                "status": result["status"],
                "summary": result["summary"],
                "outputs": {
                    "json": str(args.output_json) if args.output_json else None,
                    "csv": str(args.output_csv) if args.output_csv else None,
                    "markdown": str(args.markdown) if args.markdown else None,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["status"] == "feasible" else 2


if __name__ == "__main__":
    sys.exit(main())
