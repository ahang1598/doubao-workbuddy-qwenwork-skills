#!/usr/bin/env python3
"""Deterministic first-pass checks for Chinese university course choices."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


DEFAULT_WEIGHTS = {
    "difficulty_fit": 0.22,
    "grading": 0.16,
    "schedule_fit": 0.18,
    "future_utility": 0.28,
    "workload_fit": 0.16,
}

EVIDENCE_CONFIDENCE = {
    "official": 1.00,
    "university_aggregate": 1.00,
    "aggregated": 0.90,
    "syllabus": 0.80,
    "community": 0.45,
    "self_report": 0.35,
    "unknown": 0.00,
}

VALID_STATUS = {"considering", "enrolled", "locked", "waitlist", "dropped"}
VERIFICATION_STATUS = {"verified", "unverified", "conflict"}
FRESHNESS = {"current", "stale", "unknown"}
DYNAMIC_SUPPORTS = {"capacity", "addable", "deadline", "schedule", "instructor"}


def fail(message: str) -> None:
    raise ValueError(message)


def number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{field} 必须是数字")
    result = float(value)
    if not minimum <= result <= maximum:
        fail(f"{field} 必须在 {minimum:g}-{maximum:g} 之间")
    return result


def course_ids(values: Any, field: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
        fail(f"{field} 必须是课程号字符串数组")
    return [x.strip() for x in values if x.strip()]


def expand_weeks(meeting: dict[str, Any]) -> set[int]:
    weeks = meeting.get("weeks")
    if isinstance(weeks, list):
        result = {int(w) for w in weeks}
        if any(w < 1 or w > 30 for w in result):
            fail("meetings.weeks 周次必须在 1-30 之间")
        return result
    if weeks in {"all", "odd", "even"}:
        start, end, parity = 1, 30, weeks
    elif weeks is None:
        start = int(meeting.get("week_start", 1))
        end = int(meeting.get("week_end", 30))
        parity = meeting.get("parity", "all")
    else:
        fail("meetings.weeks 必须是数组、all、odd 或 even")
    if start < 1 or end > 30 or start > end:
        fail("week_start/week_end 必须满足 1 <= start <= end <= 30")
    if parity not in {"all", "odd", "even"}:
        fail("parity 必须是 all、odd 或 even")
    return {
        w for w in range(start, end + 1)
        if parity == "all" or (parity == "odd" and w % 2 == 1) or (parity == "even" and w % 2 == 0)
    }


def normalize_meeting(meeting: Any, field: str) -> dict[str, Any]:
    if not isinstance(meeting, dict):
        fail(f"{field} 必须是对象")
    day = int(number(meeting.get("day"), f"{field}.day", 1, 7))
    start = int(number(meeting.get("start_period"), f"{field}.start_period", 1, 30))
    end = int(number(meeting.get("end_period"), f"{field}.end_period", 1, 30))
    if start > end:
        fail(f"{field} 开始节次不得晚于结束节次")
    return {"day": day, "start": start, "end": end, "weeks": expand_weeks(meeting)}


def meetings_conflict(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a["day"] == b["day"]
        and max(a["start"], b["start"]) <= min(a["end"], b["end"])
        and bool(a["weeks"] & b["weeks"])
    )


def evidence_confidence(item: dict[str, Any]) -> float:
    level = str(item.get("evidence_level", "unknown"))
    confidence = EVIDENCE_CONFIDENCE.get(level, 0.0)
    sample = item.get("sample_size")
    if isinstance(sample, (int, float)):
        if sample < 10:
            confidence *= 0.50
        elif sample < 30:
            confidence *= 0.75
    age = item.get("source_age_semesters")
    if isinstance(age, (int, float)) and age > 2:
        confidence *= 0.70
    if item.get("instructor_match") is False:
        confidence *= 0.70
    return round(confidence, 3)


def workload_fit(course: dict[str, Any]) -> float | None:
    if "workload_rating" in course:
        return number(course["workload_rating"], "workload_rating", 1, 5)
    hours = course.get("workload_hours")
    if not isinstance(hours, (int, float)):
        return None
    if hours <= 4:
        return 5.0
    if hours <= 7:
        return 4.0
    if hours <= 10:
        return 3.0
    if hours <= 13:
        return 2.0
    return 1.0


def iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        fail(f"{field} 必须是 YYYY-MM-DD 日期")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        fail(f"{field} 必须是合法 YYYY-MM-DD 日期")


def validate_sources(raw: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        fail(f"{field} 必须是非空数组")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        prefix = f"{field}[{index}]"
        if not isinstance(item, dict):
            fail(f"{prefix} 必须是对象")
        for key in ("publisher", "source", "published_or_updated"):
            if not str(item.get(key, "")).strip():
                fail(f"{prefix}.{key} 不能为空")
        published = iso_date(item["published_or_updated"], f"{prefix}.published_or_updated")
        status = item.get("verification_status")
        freshness = item.get("freshness")
        if status not in VERIFICATION_STATUS:
            fail(f"{prefix}.verification_status 无效")
        if freshness not in FRESHNESS:
            fail(f"{prefix}.freshness 无效")
        supports = item.get("supports")
        if not isinstance(supports, list) or not supports or any(not isinstance(x, str) or not x.strip() for x in supports):
            fail(f"{prefix}.supports 必须是非空字符串数组")
        if published > date.today():
            fail(f"{prefix}.published_or_updated 不得晚于今天")
        result.append({**item, "_published": published, "_supports": set(supports)})
    return result


def validate_and_normalize(data: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(data, dict):
        fail("根节点必须是 JSON 对象")
    profile = data.get("profile")
    courses = data.get("courses")
    if not isinstance(profile, dict):
        fail("缺少 profile 对象")
    if not isinstance(courses, list) or not courses:
        fail("courses 必须是非空数组")
    for field in ("institution", "program", "target_term"):
        if not str(profile.get(field, "")).strip():
            fail(f"profile.{field} 不能为空")
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(courses):
        if not isinstance(raw, dict):
            fail(f"courses[{index}] 必须是对象")
        cid = str(raw.get("course_id", "")).strip()
        if not cid:
            fail(f"courses[{index}].course_id 不能为空")
        section_id = str(raw.get("section_id", "")).strip()
        option_key = (cid, section_id)
        option_id = f"{cid}:{section_id}" if section_id else cid
        if option_key in seen:
            fail(f"课程教学班重复: {option_id}")
        seen.add(option_key)
        name = str(raw.get("name", "")).strip()
        if not name:
            fail(f"{cid}.name 不能为空")
        credits = number(raw.get("credits"), f"{cid}.credits", 0, 50)
        status = str(raw.get("status", "considering"))
        if status not in VALID_STATUS:
            fail(f"{cid}.status 无效")
        meetings_raw = raw.get("meetings", [])
        if not isinstance(meetings_raw, list):
            fail(f"{cid}.meetings 必须是数组")
        meetings = [normalize_meeting(m, f"{cid}.meetings[{i}]") for i, m in enumerate(meetings_raw)]
        sources = validate_sources(raw.get("sources"), f"{cid}.sources")
        prerequisites = raw.get("prerequisites", {}) or {}
        if not isinstance(prerequisites, dict):
            fail(f"{cid}.prerequisites 必须是对象")
        any_groups = prerequisites.get("any_of_groups", []) or []
        if not isinstance(any_groups, list) or any(not isinstance(g, list) for g in any_groups):
            fail(f"{cid}.prerequisites.any_of_groups 必须是二维数组")
        normalized.append({
            **raw,
            "course_id": cid,
            "section_id": section_id,
            "option_id": option_id,
            "name": name,
            "credits": credits,
            "status": status,
            "_meetings": meetings,
            "_all_of": course_ids(prerequisites.get("all_of"), f"{cid}.prerequisites.all_of"),
            "_any_groups": [course_ids(g, f"{cid}.prerequisites.any_of_groups") for g in any_groups],
            "_corequisites": course_ids(prerequisites.get("corequisites"), f"{cid}.prerequisites.corequisites"),
            "_exclusions": course_ids(raw.get("exclusions"), f"{cid}.exclusions"),
            "_sources": sources,
        })
    return profile, normalized


def analyze(data: Any) -> dict[str, Any]:
    profile, courses = validate_and_normalize(data)
    completed = set(course_ids(profile.get("completed_courses"), "profile.completed_courses"))
    enrolled = set(course_ids(profile.get("enrolled_courses"), "profile.enrolled_courses"))
    proposed = set(course_ids(profile.get("proposed_courses"), "profile.proposed_courses"))
    active = completed | enrolled | proposed

    conflicts: list[dict[str, Any]] = []
    for i, left in enumerate(courses):
        for right in courses[i + 1:]:
            hits = []
            for lm in left["_meetings"]:
                for rm in right["_meetings"]:
                    if meetings_conflict(lm, rm):
                        hits.append({
                            "day": lm["day"],
                            "periods": [max(lm["start"], rm["start"]), min(lm["end"], rm["end"])],
                            "weeks": sorted(lm["weeks"] & rm["weeks"]),
                        })
            if hits:
                conflicts.append({"courses": [left["option_id"], right["option_id"]], "overlaps": hits})

    weights = dict(DEFAULT_WEIGHTS)
    supplied_weights = profile.get("weights", {})
    if supplied_weights:
        if not isinstance(supplied_weights, dict):
            fail("profile.weights 必须是对象")
        for key, value in supplied_weights.items():
            if key not in weights:
                fail(f"未知权重字段: {key}")
            weights[key] = number(value, f"profile.weights.{key}", 0, 1)
    if sum(weights.values()) <= 0:
        fail("评分权重之和必须大于 0")

    results = []
    gaps = []
    for course in courses:
        cid = course["course_id"]
        blockers: list[str] = []
        warnings: list[str] = []
        missing_all = [x for x in course["_all_of"] if x not in completed]
        if missing_all:
            blockers.append("缺少全部先修: " + ", ".join(missing_all))
        for group in course["_any_groups"]:
            if group and not completed.intersection(group):
                blockers.append("以下先修至少完成一门: " + ", ".join(group))
        missing_coreq = [x for x in course["_corequisites"] if x not in active]
        if missing_coreq:
            blockers.append("缺少共修/已修: " + ", ".join(missing_coreq))
        excluded = sorted(active.intersection(course["_exclusions"]))
        if excluded:
            blockers.append("与已修/已选课程互斥: " + ", ".join(excluded))
        capacity = str(course.get("capacity_status", "unknown"))
        dynamic_claims = set()
        if "capacity_status" in course:
            dynamic_claims.add("capacity")
        if "addable" in course:
            dynamic_claims.add("addable")
        for claim in sorted(dynamic_claims):
            supporting = [s for s in course["_sources"] if claim in s["_supports"]]
            if not any(s["verification_status"] == "verified" and s["freshness"] == "current" for s in supporting):
                blockers.append(f"{claim} 缺少已核验且当前有效的证据")
        dynamic_valid = not any("缺少已核验且当前有效的证据" in item for item in blockers)
        if dynamic_valid and course.get("addable") is False:
            blockers.append("当前不可补选")
        if dynamic_valid and capacity in {"closed", "full"}:
            blockers.append("容量已满或关闭")
        elif dynamic_valid and capacity in {"waitlist", "lottery"}:
            warnings.append("仅候补/抽签，不能视为已选上")
        if any(s["verification_status"] == "conflict" for s in course["_sources"]):
            blockers.append("来源存在冲突，需官方确认")
        if not course["_meetings"]:
            warnings.append("缺少上课时间，无法完整检查冲突")

        components: dict[str, float] = {}
        difficulty = course.get("difficulty")
        if isinstance(difficulty, dict) and "rating" in difficulty:
            rating = number(difficulty["rating"], f"{cid}.difficulty.rating", 1, 5)
            components["difficulty_fit"] = round(6 - rating, 3)
        grading = course.get("grading")
        grading_note = "unknown"
        if isinstance(grading, dict) and "friendliness" in grading:
            raw_grade = number(grading["friendliness"], f"{cid}.grading.friendliness", 1, 5)
            confidence = evidence_confidence(grading)
            if confidence > 0:
                components["grading"] = round(3 + (raw_grade - 3) * confidence, 3)
                grading_note = f"confidence={confidence:.3f}"
            else:
                warnings.append("给分证据未知，未计入总分")
        else:
            warnings.append("缺少给分证据，未计入总分")
        if "schedule_fit" in course:
            components["schedule_fit"] = number(course["schedule_fit"], f"{cid}.schedule_fit", 1, 5)
        utility = course.get("future_utility")
        if isinstance(utility, dict) and "rating" in utility:
            components["future_utility"] = number(utility["rating"], f"{cid}.future_utility.rating", 1, 5)
        work_fit = workload_fit(course)
        if work_fit is not None:
            components["workload_fit"] = work_fit

        used_weight = sum(weights[k] for k in components)
        total_weight = sum(weights.values())
        score = None
        if used_weight > 0:
            score = round(sum(components[k] * weights[k] for k in components) / used_weight, 3)
        coverage = round(used_weight / total_weight, 3)
        if coverage < 0.70:
            warnings.append("评分数据覆盖率低于 70%，排序仅作初筛")
        if score is None:
            gaps.append(f"{course['option_id']}: 缺少全部可评分字段")
        results.append({
            "course_id": cid,
            "section_id": course["section_id"],
            "option_id": course["option_id"],
            "name": course["name"],
            "eligible": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "score": score,
            "score_coverage": coverage,
            "component_scores": components,
            "grading_adjustment": grading_note,
        })

    order = [
        item["option_id"] for item in sorted(
            (x for x in results if x["eligible"]),
            key=lambda x: (x["score"] is not None, x["score"] if x["score"] is not None else -1, x["score_coverage"]),
            reverse=True,
        )
    ]
    return {
        "context": {
            "institution": profile["institution"],
            "program": profile["program"],
            "target_term": profile["target_term"],
        },
        "course_results": results,
        "schedule_conflicts": conflicts,
        "recommended_order_among_eligible": order,
        "data_gaps": gaps,
        "notice": "结果仅用于第一遍结构化校验；培养方案、开课、容量、截止日期与审批以目标学期官方信息为准。",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验并初排国内高校候选课程")
    parser.add_argument("input", type=Path, help="选课 JSON 文件")
    parser.add_argument("--output", type=Path, help="写入分析结果 JSON；省略则打印到标准输出")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = analyze(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    payload = json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
