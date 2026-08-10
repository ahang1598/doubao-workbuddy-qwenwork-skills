#!/usr/bin/env python3
"""把人工 QA 填写的 CSV 追加到 qa-run.json，并重新生成 Bug/报告与下一轮执行表。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qa_run_common import case_status, coverage_snapshot, semantic_findings


HEADERS = [
    "case_id", "module", "title", "priority", "preconditions", "steps", "test_data",
    "expected_result", "assigned_to", "evidence_expected", "previous_status", "attempt",
    "status", "operator", "actual_result", "started_at", "finished_at", "evidence_paths",
    "tester_notes", "retest_of",
]
STATUS_MAP = {
    "通过": "passed", "passed": "passed",
    "失败": "failed", "failed": "failed",
    "待确认": "pending_confirmation", "pending_confirmation": "pending_confirmation",
    "阻塞": "blocked", "blocked": "blocked",
    "不适用": "skipped", "skipped": "skipped",
    "未执行": "", "": "",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".m4v"}
LOG_SUFFIXES = {".log", ".txt", ".crash"}


def lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def canonical_fields(case: dict[str, Any], handoff: dict[str, Any]) -> dict[str, str]:
    return {
        "case_id": str(case.get("id", "")),
        "module": str(case.get("module", "")),
        "title": str(case.get("title", "")),
        "priority": str(case.get("priority", "")),
        "preconditions": "；".join(lines(case.get("preconditions"))),
        "steps": "\n".join(f"{index}. {item}" for index, item in enumerate(lines(case.get("steps")), start=1)),
        "test_data": str(case.get("test_data", "")),
        "expected_result": "；".join(lines(case.get("expected_result"))),
        "assigned_to": str(case.get("assigned_to") or handoff.get("operator") or "人工 QA"),
        "evidence_expected": "；".join(lines(case.get("evidence_expected"))),
    }


def parse_time(value: str, field: str, row_number: int, errors: list[str]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"第 {row_number} 行 {field} 不是 ISO 8601 时间：{value}")
        return None
    if parsed.tzinfo is None:
        errors.append(f"第 {row_number} 行 {field} 必须包含时区：{value}")
        return None
    return parsed


def split_paths(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;；\n]", value) if item.strip()]


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    used = {str(item.get("id", "")) for item in items}
    index = 1
    while f"{prefix}-{index:03d}" in used:
        index += 1
    return f"{prefix}-{index:03d}"


def evidence_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "screenshot"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix == ".crash":
        return "crash"
    if suffix in LOG_SUFFIXES:
        return "log"
    return "attachment"


def display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def update_bug_candidate(run: dict[str, Any], case: dict[str, Any], execution: dict[str, Any]) -> None:
    candidates = run.setdefault("bug_candidates", [])
    candidate = next(
        (
            item for item in candidates
            if item.get("case_id") == case.get("id")
            and item.get("status") not in {"closed", "rejected", "promoted"}
        ),
        None,
    )
    if execution["status"] == "failed":
        if candidate is None:
            candidates.append({
                "id": next_id(candidates, "CANDIDATE-MANUAL"),
                "case_id": case["id"],
                "title": f"人工执行失败：{case.get('title', case['id'])}",
                "status": "pending_reproduction",
                "first_execution_id": execution["id"],
                "latest_execution_id": execution["id"],
                "first_failure_preserved": True,
                "summary": execution.get("actual_result", ""),
            })
        else:
            candidate["status"] = "reproduced"
            candidate["latest_execution_id"] = execution["id"]
            candidate["summary"] = execution.get("actual_result", candidate.get("summary", ""))
    elif execution["status"] == "passed" and candidate is not None:
        candidate["status"] = "retest_passed_needs_triage"
        candidate["latest_execution_id"] = execution["id"]


def infer_qa_run(csv_path: Path) -> Path:
    if csv_path.parent.name == "manual-handoff":
        return csv_path.parent.parent / "qa-run.json"
    return csv_path.parent / "qa-run.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入人工 QA 执行结果并重新生成测试报告")
    parser.add_argument("results_csv", type=Path, help="人工填写后的 02-manual-test-cases.csv")
    parser.add_argument("--qa-run", type=Path, help="qa-run.json；默认从 CSV 相邻目录推断")
    parser.add_argument("--no-render", action="store_true", help="只更新 qa-run.json，不重新生成派生产物")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = args.results_csv.expanduser().resolve()
    qa_run_path = (args.qa_run.expanduser().resolve() if args.qa_run else infer_qa_run(csv_path).resolve())
    if not csv_path.is_file() or not qa_run_path.is_file():
        print(json.dumps({"ok": False, "error": "results_csv 或 qa-run.json 不存在"}, ensure_ascii=False), file=sys.stderr)
        return 2

    try:
        run = json.loads(qa_run_path.read_text(encoding="utf-8-sig"))
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [name for name in HEADERS if name not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"CSV 缺少字段：{', '.join(missing)}")
            rows = [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    working = deepcopy(run)
    before_execution_count = len(working.get("executions", []))
    before_evidence_count = len(working.get("evidence", []))
    cases = {str(item.get("id", "")): item for item in working.get("cases", [])}
    handoff = working.get("manual_handoff", {})
    existing_execution_ids = {str(item.get("id", "")) for item in working.get("executions", [])}
    errors: list[str] = []
    imported: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        raw_status = row.get("status", "")
        if raw_status not in STATUS_MAP:
            errors.append(f"第 {row_number} 行 status 非法：{raw_status}")
            continue
        status = STATUS_MAP[raw_status]
        if not status:
            continue
        case_id = row.get("case_id", "")
        case = cases.get(case_id)
        if not case:
            errors.append(f"第 {row_number} 行引用不存在的用例：{case_id}")
            continue
        if case.get("execution_mode") not in {"manual", "hybrid"}:
            errors.append(f"第 {row_number} 行 {case_id} 不是人工或混合用例")
            continue
        expected = canonical_fields(case, handoff)
        for field, value in expected.items():
            if row.get(field, "") != value:
                errors.append(f"第 {row_number} 行 {case_id} 的只读字段 {field} 已被修改")
        try:
            attempt = int(row.get("attempt", ""))
            if attempt < 1:
                raise ValueError
        except ValueError:
            errors.append(f"第 {row_number} 行 attempt 必须是大于等于 1 的整数")
            continue
        execution_id = f"EXE-MANUAL-{re.sub(r'[^A-Z0-9_-]', '-', case_id.upper())}-A{attempt}"
        if execution_id in existing_execution_ids:
            errors.append(f"第 {row_number} 行执行已存在，禁止覆盖：{execution_id}")
            continue
        operator = row.get("operator", "")
        actual_result = row.get("actual_result", "")
        if not operator or not actual_result:
            errors.append(f"第 {row_number} 行必须填写 operator 和 actual_result")
            continue
        started = parse_time(row.get("started_at", ""), "started_at", row_number, errors)
        finished = parse_time(row.get("finished_at", ""), "finished_at", row_number, errors)
        if started and finished and finished < started:
            errors.append(f"第 {row_number} 行 finished_at 早于 started_at")
            continue

        previous = [item for item in working.get("executions", []) if item.get("case_id") == case_id]
        retest_of = row.get("retest_of", "") or (str(previous[-1].get("id")) if previous else "")
        if retest_of:
            prior = next((item for item in previous if item.get("id") == retest_of), None)
            if prior is None:
                errors.append(f"第 {row_number} 行 retest_of 不属于该用例：{retest_of}")
                continue
        elif attempt > 1:
            errors.append(f"第 {row_number} 行 attempt>1 但没有可引用的历史执行")
            continue

        evidence_ids: list[str] = []
        observation_id = next_id(working.setdefault("evidence", []), "EVD-MANUAL")
        working["evidence"].append({
            "id": observation_id,
            "type": "manual_observation",
            "description": f"{operator}：{actual_result}",
            "created_at": row.get("finished_at", ""),
            "level": "L2_observation",
            "validation_scope": "exploratory",
        })
        evidence_ids.append(observation_id)
        for raw_path in split_paths(row.get("evidence_paths", "")):
            if raw_path.startswith(("http://", "https://")):
                resolved_path = raw_path
                kind = "attachment"
            else:
                candidate_path = Path(raw_path).expanduser()
                if not candidate_path.is_absolute():
                    candidate_path = csv_path.parent / candidate_path
                if not candidate_path.is_file():
                    errors.append(f"第 {row_number} 行证据文件不存在：{raw_path}")
                    continue
                kind = evidence_type(candidate_path)
                if kind in {"screenshot", "video"} and working.get("screenshot_policy") in {"off", "unconfirmed"}:
                    errors.append(f"第 {row_number} 行截图/录屏证据与 screenshot_policy={working.get('screenshot_policy')} 冲突")
                    continue
                resolved_path = display_path(candidate_path, qa_run_path.parent)
            evidence_id = next_id(working["evidence"], "EVD-MANUAL")
            working["evidence"].append({
                "id": evidence_id,
                "type": kind,
                "description": f"{case_id} 人工证据",
                "path": resolved_path,
                "level": "L2_observation",
                "validation_scope": "exploratory",
            })
            evidence_ids.append(evidence_id)

        execution = {
            "id": execution_id,
            "case_id": case_id,
            "status": status,
            "execution_level": "exploratory",
            "validation_scope": "exploratory",
            "execution_method": "manual",
            "operator": operator,
            "actual_result": actual_result,
            "started_at": row.get("started_at", ""),
            "finished_at": row.get("finished_at", ""),
            "tester_notes": row.get("tester_notes", ""),
            "attempt": attempt,
            "retest_of": retest_of or None,
            "evidence_ids": evidence_ids,
            "summary": actual_result,
        }
        if status == "pending_confirmation":
            execution["confirmation_needed"] = actual_result
        working.setdefault("executions", []).append(execution)
        existing_execution_ids.add(execution_id)
        update_bug_candidate(working, case, execution)
        imported.append(execution_id)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    if not imported:
        print(json.dumps({"ok": False, "error": "没有可导入的人工执行结果"}, ensure_ascii=False), file=sys.stderr)
        return 2

    working["revision"] = int(working.get("revision", 1)) + 1
    revision = working["revision"]
    ledger = working.setdefault("change_ledger", [])
    after_execution_count = len(working.get("executions", []))
    after_evidence_count = len(working.get("evidence", []))
    ledger.append({
        "id": next_id(ledger, "CHG"),
        "revision": revision,
        "action": "ADD",
        "object_type": "execution",
        "added_ids": imported,
        "removed_ids": [],
        "modified_ids": [],
        "before_count": before_execution_count,
        "after_count": after_execution_count,
        "delta_count": after_execution_count - before_execution_count,
        "source": str(csv_path),
        "summary": "导入人工执行结果",
    })
    added_evidence = [
        str(item.get("id", ""))
        for item in working.get("evidence", [])[before_evidence_count:]
    ]
    ledger.append({
        "id": next_id(ledger, "CHG"),
        "revision": revision,
        "action": "ADD",
        "object_type": "evidence",
        "added_ids": added_evidence,
        "removed_ids": [],
        "modified_ids": [],
        "before_count": before_evidence_count,
        "after_count": after_evidence_count,
        "delta_count": after_evidence_count - before_evidence_count,
        "source": str(csv_path),
        "summary": "归档人工观察与附件证据",
    })
    manifest = working.setdefault("delivery_manifest", {"source_revision": revision, "outputs": []})
    manifest["source_revision"] = revision
    for output in manifest.get("outputs", []):
        if output.get("status") not in {"failed", "local_fallback"}:
            output["status"] = "stale"
            output["validated"] = False

    working["execution_level"] = "exploratory"
    manual_ids = [str(value) for value in handoff.get("case_ids", [])]
    statuses = [case_status(working, case_id) for case_id in manual_ids]
    if statuses and all(value in {"通过", "失败", "不适用"} for value in statuses):
        working["manual_handoff"]["status"] = "completed"
    elif "阻塞" in statuses:
        working["manual_handoff"]["status"] = "blocked"
    else:
        working["manual_handoff"]["status"] = "in_progress"
    working["coverage"] = coverage_snapshot(working)
    working["release_decision"] = {
        "decision": "undetermined",
        "rationale": "人工结果已导入；仍需完成失败归因、缺陷分析和发布门禁复核。",
        "conditions": ["处理人工失败、阻塞和缺陷候选", "确认所有 P0/P1 人工用例最终状态"],
    }
    findings = semantic_findings(working, qa_run_path.parent)
    validation_errors = [item for item in findings if item["level"] == "error"]
    if validation_errors:
        print(json.dumps({"ok": False, "errors": validation_errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    submissions = qa_run_path.parent / "manual-handoff" / "submissions"
    submissions.mkdir(parents=True, exist_ok=True)
    archived = submissions / f"{stamp}-manual-results.csv"
    shutil.copy2(csv_path, archived)
    temp = qa_run_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(working, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(qa_run_path)

    render_result: dict[str, Any] | None = None
    if not args.no_render:
        renderer = Path(__file__).with_name("render_qa_artifacts.py")
        completed = subprocess.run(
            [sys.executable, str(renderer), str(qa_run_path), "--out", str(qa_run_path.parent)],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            print(completed.stderr, file=sys.stderr)
            return 1
        render_result = json.loads(completed.stdout)

    print(json.dumps({
        "ok": True,
        "qa_run": str(qa_run_path),
        "imported_executions": imported,
        "archived_submission": str(archived),
        "bug_candidates": [item.get("id") for item in working.get("bug_candidates", [])],
        "render": render_result,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
