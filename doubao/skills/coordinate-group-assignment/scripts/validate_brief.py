#!/usr/bin/env python3
from __future__ import annotations
"""Validate the small, platform-independent AssignmentBrief contract."""

import argparse
import json
import sys
from pathlib import Path


MODES = {"plan", "assign", "merge"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an AssignmentBrief JSON file."
    )
    parser.add_argument("path", type=Path, help="path to AssignmentBrief JSON")
    args = parser.parse_args()

    try:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot read JSON: {exc}")
        return 1

    errors = []
    if not isinstance(payload, dict):
        errors.append("root must be an object")
        payload = {}

    mode = payload.get("mode")
    if mode not in MODES:
        errors.append(f"mode must be one of: {', '.join(sorted(MODES))}")

    assignment = payload.get("assignment")
    if not isinstance(assignment, dict):
        errors.append("assignment must be an object")
        assignment = {}
    for field in ("title", "objective", "deliverables"):
        value = assignment.get(field)
        if field == "deliverables":
            if not isinstance(value, list) or not value:
                errors.append("assignment.deliverables must be a non-empty list")
            else:
                for index, deliverable in enumerate(value, start=1):
                    if not isinstance(deliverable, dict):
                        errors.append(
                            f"assignment.deliverables[{index}] must be an object"
                        )
                        continue
                    for key in ("type", "format"):
                        if not isinstance(deliverable.get(key), str) or not deliverable[
                            key
                        ].strip():
                            errors.append(
                                f"assignment.deliverables[{index}].{key} must be a non-empty string"
                            )
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"assignment.{field} must be a non-empty string")

    team = payload.get("team", [])
    if not isinstance(team, list):
        errors.append("team must be a list")
    elif mode == "assign" and not team:
        errors.append("assign mode requires at least one team member")
    elif mode == "assign":
        required_member_fields = ("member_id", "availability", "strengths", "preferences", "constraints")
        member_ids = set()
        for index, member in enumerate(team, start=1):
            prefix = f"team[{index}]"
            if not isinstance(member, dict):
                errors.append(f"{prefix} must be an object")
                continue
            member_id = member.get("member_id")
            if not isinstance(member_id, str) or not member_id.strip():
                errors.append(f"{prefix}.member_id must be a non-empty string")
            elif member_id in member_ids:
                errors.append(f"duplicate team member_id: {member_id}")
            else:
                member_ids.add(member_id)
            for field in required_member_fields[1:]:
                value = member.get(field)
                if field == "availability":
                    valid = isinstance(value, str) and bool(value.strip())
                else:
                    valid = isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)
                if not valid:
                    errors.append(f"{prefix}.{field} must be explicitly provided")
            if "current_load" not in member:
                errors.append(f"{prefix}.current_load must be provided (use unknown when needed)")

    contributions = payload.get("contributions", [])
    if not isinstance(contributions, list):
        errors.append("contributions must be a list")
    elif mode == "merge" and not contributions:
        errors.append("merge mode requires at least one contribution")
    elif mode == "merge":
        for index, contribution in enumerate(contributions, start=1):
            prefix = f"contributions[{index}]"
            if not isinstance(contribution, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in ("member_id", "task_id", "draft_content", "claims", "evidence"):
                value = contribution.get(field)
                if field in {"claims", "evidence"}:
                    if not isinstance(value, list) or not value:
                        errors.append(f"{prefix}.{field} must be a non-empty list")
                elif not isinstance(value, str) or not value.strip():
                    errors.append(f"{prefix}.{field} must be a non-empty string")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(f"VALID brief: mode={mode}, deliverables={len(assignment['deliverables'])}, team={len(team)}, contributions={len(contributions)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
