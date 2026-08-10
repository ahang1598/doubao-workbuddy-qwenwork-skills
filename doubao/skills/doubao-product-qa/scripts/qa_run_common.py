#!/usr/bin/env python3
"""qa-run.json 的共享常量、派生统计与轻量语义校验。"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


BASE_FILES = {
    "00-input-notes.md",
    "01-test-plan.md",
    "02-traceability.csv",
    "03-test-cases.csv",
    "04-acceptance-checklist.md",
    "05-risks.md",
    "06-bugs.md",
    "07-test-report.md",
}

PROFILE_FILES = {
    "smoke": {"07-test-report.md"},
    "plan": {
        "01-test-plan.md",
        "02-traceability.csv",
        "03-test-cases.csv",
        "05-risks.md",
    },
    "execution": {"03-test-cases.csv", "06-bugs.md", "07-test-report.md"},
    "full": set(BASE_FILES),
    "bug": {"06-bugs.md"},
    "hotfix": {
        "00-input-notes.md",
        "03-test-cases.csv",
        "04-acceptance-checklist.md",
        "05-risks.md",
        "06-bugs.md",
        "07-test-report.md",
    },
}
PROFILE_FILES["mobile"] = set(BASE_FILES) | {
    "08-device-matrix.json",
    "09-automation-summary.json",
}

EXECUTION_STATUSES = {
    "passed", "failed", "pending_confirmation", "blocked", "skipped", "infra_error"
}
EXECUTION_LEVELS = {"full_automation", "partial_validation", "exploratory", "blocked"}
EXECUTION_MODES = {"automated", "manual", "hybrid"}
MANUAL_HANDOFF_STATUSES = {"not_required", "pending", "in_progress", "completed", "blocked"}
TEST_INTENTS = {"one_off_ui", "repeatable_ui", "non_ui_validation"}
RELEASE_DECISIONS = {"go", "conditional_go", "no_go", "undetermined"}
SEVERITIES = {"S1", "S2", "S3", "S4"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
RISK_MECHANISM_STATUSES = {
    "identified", "designed", "verified", "failed", "blocked", "accepted", "not_applicable"
}
CHANGE_ACTIONS = {"ADD", "MODIFY", "REMOVE", "RESTORE", "REPLACE", "NARROW"}
CHANGE_OBJECT_TYPES = {
    "run", "requirement", "risk_mechanism", "case", "acceptance",
    "execution", "evidence", "bug", "delivery"
}
SAFE_HTTP_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
REPRODUCIBILITY = {"always", "intermittent", "once", "not_reproduced"}
BUG_STATUSES = {"open", "in_progress", "fixed", "pending_retest", "closed", "rejected", "deferred"}
ANALYSIS_CONFIDENCE = {"high", "medium", "low", "unknown"}
EVIDENCE_LEVELS = {"L0_claim", "L1_document", "L2_observation", "L3_reproducible", "L4_formal"}
VALIDATION_SCOPES = {"precheck", "exploratory", "formal"}
TASK_MODES = {
    "lightweight_answer", "plan", "execution_review", "web_execution",
    "api_execution", "bug", "hotfix", "multi_round",
}
DELIVERY_FORMATS = {
    "inline_markdown", "markdown", "csv", "json", "docx", "xlsx", "pptx", "pdf",
    "lark_doc", "lark_sheets", "lark_base", "lark_ppt", "multi",
}
DELIVERY_CARRIERS = {
    "inline", "local", "office_file", "lark_doc", "lark_sheets", "lark_base", "lark_ppt", "multi"
}
FORMAT_CARRIER = {
    "markdown": "local", "csv": "local", "json": "local",
    "docx": "office_file", "xlsx": "office_file", "pptx": "office_file", "pdf": "office_file",
    "lark_doc": "lark_doc", "lark_sheets": "lark_sheets",
    "lark_base": "lark_base", "lark_ppt": "lark_ppt",
}
INPUT_ACCESS_STATUSES = {"read", "blocked", "not_applicable"}
INPUT_TYPES_WITH_ITEMS = {"spreadsheet", "archive"}
ACCEPTANCE_TYPES = {
    "core_flow", "exception", "permission_security", "compatibility",
    "data_consistency", "analytics", "performance", "defect_blocker", "release_config",
}
OPEN_BUG_CANDIDATE_STATUSES = {"pending_reproduction", "reproduced", "retest_passed_needs_triage", "needs_triage"}
VAGUE_TEST_DATA = re.compile(r"^(样例为准|正常数据|合理值|同上|默认值|适当数据|任意值)$")
VAGUE_EXPECTED = re.compile(r"^(功能正常|显示正常|结果正确|符合预期|无异常|可用)$")
NUMBER_TOKEN = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(%)?")
BOUNDARY_QUESTION_MARKERS = (
    "是否包含", "是否含", "边界是否", "含不含", "包含边界",
    "≥还是>", ">还是≥", "≤还是<", "<还是≤",
    "大于还是大于等于", "小于还是小于等于",
)
CONDITIONAL_ORACLE_MARKERS = (
    "待确认", "待定", "若", "如果", "分别验证", "双轨", "两种口径",
    "按确认口径", "以确认结果为准", "pending", "tbd",
)


def index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item.get(key, "")): item for item in items if item.get(key)}


def executions_for_case(run: dict[str, Any], case_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in run.get("executions", [])
        if str(item.get("case_id", "")) == case_id
    ]


def case_status(run: dict[str, Any], case_id: str) -> str:
    statuses = [str(item.get("status", "")) for item in executions_for_case(run, case_id)]
    if not statuses:
        return "未执行"
    latest = statuses[-1]
    if latest == "failed":
        return "失败"
    if latest == "pending_confirmation":
        return "待确认"
    if latest in {"blocked", "infra_error"}:
        return "阻塞"
    if latest == "skipped":
        return "不适用"
    if latest == "passed":
        return "通过"
    return "阻塞"


def acceptance_status(run: dict[str, Any], check: dict[str, Any]) -> str:
    statuses = [case_status(run, str(case_id)) for case_id in check.get("case_ids", [])]
    if not statuses:
        return "待验证"
    if "失败" in statuses:
        return "未通过"
    if "阻塞" in statuses:
        return "阻塞"
    if "未执行" in statuses or "待确认" in statuses:
        return "待验证"
    if all(status == "不适用" for status in statuses):
        return "不适用"
    if all(status in {"通过", "不适用"} for status in statuses) and "通过" in statuses:
        return "通过"
    return "待验证"


def coverage_snapshot(run: dict[str, Any]) -> dict[str, Any]:
    requirements = run.get("requirements", [])
    cases = run.get("cases", [])
    req_ids = {str(item.get("id", "")) for item in requirements}
    linked_req_ids: set[str] = set()
    status_counts: Counter[str] = Counter()
    for case in cases:
        case_id = str(case.get("id", ""))
        status_counts[case_status(run, case_id)] += 1
        linked_req_ids.update(
            str(req_id) for req_id in case.get("requirement_ids", []) if str(req_id) in req_ids
        )
    p0_ids = {
        str(item.get("id", ""))
        for item in requirements
        if str(item.get("risk", "")).upper() == "P0"
    }
    acceptance_counts = Counter(
        acceptance_status(run, item) for item in run.get("acceptance_checks", [])
    )
    return {
        "requirement_total": len(requirements),
        "requirement_linked": len(linked_req_ids),
        "requirement_unlinked": len(req_ids - linked_req_ids),
        "p0_requirement_total": len(p0_ids),
        "p0_requirement_linked": len(p0_ids & linked_req_ids),
        "case_total": len(cases),
        "case_status_counts": dict(sorted(status_counts.items())),
        "acceptance_total": len(run.get("acceptance_checks", [])),
        "acceptance_status_counts": dict(sorted(acceptance_counts.items())),
    }


def unresolved_p0(run: dict[str, Any]) -> list[str]:
    p0_ids = {
        str(item.get("id", ""))
        for item in run.get("requirements", [])
        if str(item.get("risk", "")).upper() == "P0"
    }
    affected: list[str] = []
    for req_id in sorted(p0_ids):
        linked = [
            case
            for case in run.get("cases", [])
            if req_id in [str(value) for value in case.get("requirement_ids", [])]
        ]
        if not linked or any(case_status(run, str(case.get("id", ""))) != "通过" for case in linked):
            affected.append(req_id)
    return affected


def requested_delivery(run: dict[str, Any]) -> dict[str, Any]:
    contract = run.get("request_contract")
    if not isinstance(contract, dict):
        return {}
    delivery = contract.get("delivery")
    return delivery if isinstance(delivery, dict) else {}


def canonical_fingerprint(run: dict[str, Any]) -> str:
    ignored = {"phase_receipts", "delivery_manifest", "coverage", "updated_at"}
    payload = {key: value for key, value in run.items() if key not in ignored}
    if isinstance(payload.get("change_ledger"), list):
        payload["change_ledger"] = [
            item for item in payload["change_ledger"]
            if not isinstance(item, dict) or item.get("object_type") != "delivery"
        ]
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def resolve_local_locator(locator: str, artifact_root: Path | None) -> Path | None:
    if not locator or locator.startswith(("http://", "https://")):
        return None
    candidate = Path(locator).expanduser()
    if not candidate.is_absolute():
        if artifact_root is None:
            return None
        candidate = artifact_root / candidate
    return candidate.resolve()


def boundary_values(text: str) -> set[tuple[float, bool]]:
    """抽取可比较的数值边界；30% 与 30.00% 视为同一边界。"""
    return {
        (float(match.group(1)), bool(match.group(2)))
        for match in NUMBER_TOKEN.finditer(text)
    }


def unresolved_boundary_oracle_findings(run: dict[str, Any]) -> list[tuple[str, str]]:
    """找出把未决边界口径写成无条件规则/oracle 的位置。"""
    candidates: list[tuple[str, Any]] = []
    for index, requirement in enumerate(run.get("requirements", [])):
        candidates.extend((
            (f"requirements[{index}].summary", requirement.get("summary")),
            (f"requirements[{index}].behavior", requirement.get("behavior")),
        ))
    for index, mechanism in enumerate(run.get("risk_mechanisms", [])):
        candidates.append((f"risk_mechanisms[{index}].oracle", mechanism.get("oracle")))
    for index, case in enumerate(run.get("cases", [])):
        candidates.extend((
            (f"cases[{index}].expected_result", case.get("expected_result")),
            (f"cases[{index}].state_oracle", case.get("state_oracle")),
        ))

    findings: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for question in run.get("open_questions", []):
        if question.get("status") != "open":
            continue
        question_text = str(question.get("question", ""))
        lowered_question = question_text.lower()
        if not any(marker in lowered_question for marker in BOUNDARY_QUESTION_MARKERS):
            continue
        values = boundary_values(question_text)
        if not values:
            continue
        question_id = str(question.get("id", "开放问题"))
        for path, value in candidates:
            text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")
            lowered = text.lower()
            if not text or not values.intersection(boundary_values(text)):
                continue
            if any(marker in lowered for marker in CONDITIONAL_ORACLE_MARKERS):
                continue
            finding = (
                path,
                f"{question_id} 的边界口径仍为 open，却被写成无条件规则/oracle；"
                "FIX: 改为双轨/条件预期，或先把问题解决并记录依据",
            )
            if finding not in seen:
                findings.append(finding)
                seen.add(finding)
    return findings


def semantic_findings(run: dict[str, Any], artifact_root: Path | None = None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(level: str, path: str, message: str) -> None:
        findings.append({"level": level, "path": path, "message": message})

    required_types = {
        "schema_version": int,
        "run_id": str,
        "revision": int,
        "profile": str,
        "test_intent": str,
        "execution_level": str,
        "input": dict,
        "environment": dict,
        "requirements": list,
        "risk_mechanisms": list,
        "open_questions": list,
        "change_ledger": list,
        "observed_surfaces": list,
        "cases": list,
        "acceptance_checks": list,
        "executions": list,
        "evidence": list,
        "bugs": list,
        "risks": list,
        "coverage": dict,
        "release_decision": dict,
        "delivery_manifest": dict,
        "test_data": dict,
    }
    for field, expected in required_types.items():
        value = run.get(field)
        if not isinstance(value, expected):
            add("error", field, f"必须是 {expected.__name__}")
    if run.get("schema_version") == 2:
        for field, expected in {"request_contract": dict, "phase_receipts": list}.items():
            if not isinstance(run.get(field), expected):
                add("error", field, f"schema_version=2 时必须是 {expected.__name__}")

    if findings:
        return findings

    if run["profile"] not in PROFILE_FILES:
        add("error", "profile", f"未知 profile：{run['profile']}")
    if run["test_intent"] not in TEST_INTENTS:
        add("error", "test_intent", f"非法 test_intent：{run['test_intent']}")
    if run["execution_level"] not in EXECUTION_LEVELS:
        add("error", "execution_level", f"非法 execution_level：{run['execution_level']}")
    if run["revision"] < 1:
        add("error", "revision", "必须是大于等于 1 的整数")
    if run["schema_version"] not in {1, 2}:
        add("error", "schema_version", "仅支持 1 或 2")

    contract = run.get("request_contract", {})
    if contract:
        if not isinstance(contract, dict):
            add("error", "request_contract", "必须是对象")
            contract = {}
        else:
            if contract.get("task_mode") not in TASK_MODES:
                add("error", "request_contract.task_mode", "必须使用受支持的任务模式")
            if not contract.get("request_summary"):
                add("error", "request_contract.request_summary", "必须保留用户目标摘要")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(contract.get("request_hash", ""))):
                add("error", "request_contract.request_hash", "必须是规范化请求摘要的 sha256")
            scope = contract.get("scope")
            if not isinstance(scope, dict):
                add("error", "request_contract.scope", "必须是对象")
            else:
                for field in (
                    "included_source_ids", "excluded_source_ids",
                    "included_rounds", "excluded_rounds",
                ):
                    if not isinstance(scope.get(field), list):
                        add("error", f"request_contract.scope.{field}", "必须是数组")
            evidence_policy = contract.get("evidence_policy")
            if not isinstance(evidence_policy, dict):
                add("error", "request_contract.evidence_policy", "必须是对象")
            else:
                if not isinstance(evidence_policy.get("allow_new_execution"), bool):
                    add("error", "request_contract.evidence_policy.allow_new_execution", "必须是布尔值")
                if evidence_policy.get("allow_precheck_bug_promotion") is not False:
                    add(
                        "error",
                        "request_contract.evidence_policy.allow_precheck_bug_promotion",
                        "性能预跑不得直接提升为正式 Bug",
                    )
            delivery = contract.get("delivery")
            if not isinstance(delivery, dict):
                add("error", "request_contract.delivery", "必须是对象")
            else:
                if delivery.get("format") not in DELIVERY_FORMATS:
                    add("error", "request_contract.delivery.format", "非法交付格式")
                if delivery.get("carrier") not in DELIVERY_CARRIERS:
                    add("error", "request_contract.delivery.carrier", "非法交付载体")
                if not isinstance(delivery.get("artifact_required"), bool):
                    add("error", "request_contract.delivery.artifact_required", "必须是布尔值")
                for field in ("filenames", "required_sections", "section_order"):
                    if not isinstance(delivery.get(field), list):
                        add("error", f"request_contract.delivery.{field}", "必须是数组")
                artifacts = delivery.get("artifacts", [])
                if not isinstance(artifacts, list):
                    add("error", "request_contract.delivery.artifacts", "必须是数组")
                    artifacts = []
                artifact_names: list[str] = []
                for index, artifact in enumerate(artifacts):
                    artifact_format = artifact.get("format")
                    artifact_carrier = artifact.get("carrier")
                    if artifact_format not in DELIVERY_FORMATS - {"inline_markdown", "multi"}:
                        add("error", f"request_contract.delivery.artifacts[{index}].format", "非法实体格式")
                    if artifact_carrier not in DELIVERY_CARRIERS - {"inline", "multi"}:
                        add("error", f"request_contract.delivery.artifacts[{index}].carrier", "非法实体载体")
                    if artifact_format in FORMAT_CARRIER and artifact_carrier != FORMAT_CARRIER[artifact_format]:
                        add("error", f"request_contract.delivery.artifacts[{index}].carrier", "载体与格式不匹配")
                    filename = str(artifact.get("filename", ""))
                    if not filename:
                        add("error", f"request_contract.delivery.artifacts[{index}].filename", "不能为空")
                    suffix = {
                        "markdown": ".md", "csv": ".csv", "json": ".json", "docx": ".docx",
                        "xlsx": ".xlsx", "pptx": ".pptx", "pdf": ".pdf",
                    }.get(str(artifact_format))
                    if suffix and not filename.lower().endswith(suffix):
                        add("error", f"request_contract.delivery.artifacts[{index}].filename", f"{artifact_format} 必须使用 {suffix} 扩展名")
                    artifact_names.append(filename)
                if delivery.get("artifact_required") and not lines_like(delivery.get("filenames")):
                    add("error", "request_contract.delivery.filenames", "要求实体交付时必须声明文件名")
                if delivery.get("artifact_required") and not artifacts:
                    add("error", "request_contract.delivery.artifacts", "实体交付必须逐项声明格式、载体和文件名")
                if artifacts and artifact_names != lines_like(delivery.get("filenames")):
                    add("error", "request_contract.delivery.artifacts", "artifacts 与 filenames 必须逐项同序")
                artifact_formats = {str(item.get("format")) for item in artifacts}
                artifact_carriers = {str(item.get("carrier")) for item in artifacts}
                if delivery.get("format") != "multi" and artifact_formats and artifact_formats != {delivery.get("format")}:
                    add("error", "request_contract.delivery.format", "顶层格式与 artifacts 不一致")
                if delivery.get("carrier") != "multi" and artifact_carriers and artifact_carriers != {delivery.get("carrier")}:
                    add("error", "request_contract.delivery.carrier", "顶层载体与 artifacts 不一致")
                if delivery.get("format") == "markdown":
                    filenames = lines_like(delivery.get("filenames"))
                    if any(not value.lower().endswith(".md") for value in filenames):
                        add("error", "request_contract.delivery.filenames", "Markdown 交付文件必须使用 .md 扩展名")

    input_info = run["input"]
    for field, expected in {
        "summary": str,
        "sources": list,
        "assumptions": list,
        "conflicts": list,
        "artifacts": list,
    }.items():
        if not isinstance(input_info.get(field), expected):
            add("error", f"input.{field}", f"必须是 {expected.__name__}")

    artifact_ids: set[str] = set()
    input_artifacts = input_info.get("artifacts", [])
    if not isinstance(input_artifacts, list):
        input_artifacts = []
    for index, artifact in enumerate(input_artifacts):
        artifact_id = str(artifact.get("id", ""))
        if not re.fullmatch(r"SRC-\d{3,}", artifact_id):
            add("error", f"input.artifacts[{index}].id", "应为 SRC-NNN")
        if artifact_id in artifact_ids:
            add("error", f"input.artifacts[{index}].id", "输入材料 ID 重复")
        artifact_ids.add(artifact_id)
        for field in ("type", "locator", "access_status", "completeness_checked"):
            if field not in artifact:
                add("error", f"input.artifacts[{index}].{field}", "缺少字段")
        access_status = str(artifact.get("access_status", ""))
        if access_status not in INPUT_ACCESS_STATUSES:
            add("error", f"input.artifacts[{index}].access_status", "必须是 read/blocked/not_applicable")
        if access_status == "read":
            if artifact.get("completeness_checked") is not True:
                add("error", f"input.artifacts[{index}].completeness_checked", "已读材料必须完成完整性核对")
            if not artifact.get("coverage_note"):
                add("error", f"input.artifacts[{index}].coverage_note", "已读材料必须说明实际核对范围")
        if access_status == "blocked":
            if not artifact.get("blocked_reason"):
                add("error", f"input.artifacts[{index}].blocked_reason", "受阻材料必须说明原因")
            if not artifact.get("minimal_unblock_action"):
                add("error", f"input.artifacts[{index}].minimal_unblock_action", "受阻材料必须给出最小解锁动作")
        if str(artifact.get("type", "")) in INPUT_TYPES_WITH_ITEMS:
            item_count = artifact.get("item_count")
            reviewed_count = artifact.get("reviewed_item_count")
            if not isinstance(item_count, int) or item_count < 1:
                add("error", f"input.artifacts[{index}].item_count", "表格/压缩包必须记录大于等于 1 的项目总数")
            if not isinstance(reviewed_count, int) or reviewed_count < 0:
                add("error", f"input.artifacts[{index}].reviewed_item_count", "必须记录已核对项目数")
            elif isinstance(item_count, int) and reviewed_count > item_count:
                add("error", f"input.artifacts[{index}].reviewed_item_count", "不能大于项目总数")
            if access_status == "read" and isinstance(item_count, int) and reviewed_count != item_count:
                add("error", f"input.artifacts[{index}]", "标记 read 的表格/压缩包必须核对全部 Sheet/成员")

    scope = contract.get("scope", {}) if isinstance(contract, dict) else {}
    if isinstance(scope, dict):
        included_sources = {str(value) for value in scope.get("included_source_ids", [])}
        excluded_sources = {str(value) for value in scope.get("excluded_source_ids", [])}
        included_rounds = {str(value) for value in scope.get("included_rounds", [])}
        excluded_rounds = {str(value) for value in scope.get("excluded_rounds", [])}
        for index, artifact in enumerate(input_artifacts):
            if artifact.get("access_status") != "read":
                continue
            artifact_id = str(artifact.get("id", ""))
            round_id = str(artifact.get("round", ""))
            if included_sources and artifact_id not in included_sources:
                add("error", f"input.artifacts[{index}]", "读取了 request_contract 范围外的来源")
            if artifact_id in excluded_sources:
                add("error", f"input.artifacts[{index}]", "读取了 request_contract 明确排除的来源")
            if included_rounds and round_id not in included_rounds:
                add("error", f"input.artifacts[{index}].round", "读取了本轮请求范围外的轮次")
            if round_id and round_id in excluded_rounds:
                add("error", f"input.artifacts[{index}].round", "读取了 request_contract 明确排除的轮次")

    requirement_index = index_by(run["requirements"], "id")
    risk_mechanism_index = index_by(run["risk_mechanisms"], "id")
    case_index = index_by(run["cases"], "id")
    evidence_index = index_by(run["evidence"], "id")
    if len(requirement_index) != len(run["requirements"]):
        add("error", "requirements", "需求 ID 缺失或重复")
    if len(risk_mechanism_index) != len(run["risk_mechanisms"]):
        add("error", "risk_mechanisms", "风险机制 ID 缺失或重复")
    if len(case_index) != len(run["cases"]):
        add("error", "cases", "用例 ID 缺失或重复")
    if len(evidence_index) != len(run["evidence"]):
        add("error", "evidence", "证据 ID 缺失或重复")

    for index, requirement in enumerate(run["requirements"]):
        req_id = str(requirement.get("id", ""))
        if not re.fullmatch(r"REQ-[A-Z0-9_-]+-\d{3}", req_id, flags=re.IGNORECASE):
            add("error", f"requirements[{index}].id", "应为 REQ-<模块>-NNN")
        for field in ("summary", "source", "risk"):
            if not requirement.get(field):
                add("error", f"requirements[{index}].{field}", "不能为空")
        if requirement.get("risk") not in PRIORITIES:
            add("error", f"requirements[{index}].risk", "必须是 P0/P1/P2/P3")
        if requirement.get("risk") in {"P0", "P1"}:
            behavior = requirement.get("behavior")
            if not isinstance(behavior, dict):
                add("error", f"requirements[{index}].behavior", "P0/P1 必须结构化拆解业务行为")
            else:
                for field in (
                    "actor", "precondition", "trigger", "rule", "state_change",
                    "observable_result", "failure_behavior",
                ):
                    if not behavior.get(field):
                        add("error", f"requirements[{index}].behavior.{field}", "P0/P1 行为字段不能为空")
            if not lines_like(requirement.get("impact_scope")):
                add("error", f"requirements[{index}].impact_scope", "P0/P1 必须列出影响范围")

    for index, question in enumerate(run["open_questions"]):
        question_id = str(question.get("id", ""))
        if not re.fullmatch(r"Q-[A-Z0-9_-]+-\d{3}", question_id, flags=re.IGNORECASE):
            add("error", f"open_questions[{index}].id", "应为 Q-<模块>-NNN")
        for field in ("question", "impact", "status"):
            if not question.get(field):
                add("error", f"open_questions[{index}].{field}", "不能为空")
        if question.get("status") not in {"open", "resolved", "deferred", "not_applicable"}:
            add("error", f"open_questions[{index}].status", "必须是 open/resolved/deferred/not_applicable")
        if question.get("status") == "open" and not question.get("next_action"):
            add("error", f"open_questions[{index}].next_action", "开放问题必须给出最小确认动作")
    for path, message in unresolved_boundary_oracle_findings(run):
        add("error", path, message)

    for index, mechanism in enumerate(run["risk_mechanisms"]):
        mechanism_id = str(mechanism.get("id", ""))
        if not re.fullmatch(r"RM-[A-Z0-9_-]+-\d{3}", mechanism_id, flags=re.IGNORECASE):
            add("error", f"risk_mechanisms[{index}].id", "应为 RM-<模块>-NNN")
        for field in (
            "title", "failure_mode", "business_impact", "oracle",
            "requirement_ids", "case_ids", "priority", "status",
        ):
            if field not in mechanism:
                add("error", f"risk_mechanisms[{index}].{field}", "缺少字段")
        if not lines_like(mechanism.get("oracle")):
            add("error", f"risk_mechanisms[{index}].oracle", "必须包含可观察 oracle")
        if mechanism.get("priority") not in PRIORITIES:
            add("error", f"risk_mechanisms[{index}].priority", "必须是 P0/P1/P2/P3")
        status = str(mechanism.get("status", ""))
        if status not in RISK_MECHANISM_STATUSES:
            add("error", f"risk_mechanisms[{index}].status", f"非法状态 {status}")
        for req_id in mechanism.get("requirement_ids", []):
            if str(req_id) not in requirement_index:
                add("error", f"risk_mechanisms[{index}].requirement_ids", f"引用不存在的需求 {req_id}")
        mechanism_case_ids = [str(value) for value in mechanism.get("case_ids", [])]
        if status in {"designed", "verified", "failed", "blocked"} and not mechanism_case_ids:
            add("error", f"risk_mechanisms[{index}].case_ids", f"{status} 状态必须关联用例")
        for case_id in mechanism_case_ids:
            if case_id not in case_index:
                add("error", f"risk_mechanisms[{index}].case_ids", f"引用不存在的用例 {case_id}")

    for index, surface in enumerate(run["observed_surfaces"]):
        for field in ("surface_id", "page", "control_or_claim", "functional_check", "source"):
            if not surface.get(field):
                add("error", f"observed_surfaces[{index}].{field}", "不能为空")

    for index, case in enumerate(run["cases"]):
        case_id = str(case.get("id", ""))
        if not re.fullmatch(r"TC-[A-Z0-9_-]+-\d{3}", case_id, flags=re.IGNORECASE):
            add("error", f"cases[{index}].id", "应为 TC-<模块>-NNN")
        for field in ("module", "title", "priority", "type", "steps", "expected_result", "requirement_ids"):
            if not case.get(field):
                add("error", f"cases[{index}].{field}", "不能为空")
        priority = str(case.get("priority", ""))
        if priority not in PRIORITIES:
            add("error", f"cases[{index}].priority", "必须是 P0/P1/P2/P3")
        test_data = str(case.get("test_data", "")).strip()
        expected_result = str(case.get("expected_result", "")).strip()
        if priority in {"P0", "P1"}:
            if not test_data:
                add("error", f"cases[{index}].test_data", "P0/P1 必须提供固定值、构造式或 fixture")
            elif VAGUE_TEST_DATA.fullmatch(test_data):
                add("error", f"cases[{index}].test_data", f"P0/P1 测试数据过于模糊：{test_data}")
            if not lines_like(case.get("risk_mechanism_ids")):
                add("error", f"cases[{index}].risk_mechanism_ids", "P0/P1 必须关联风险机制")
        if priority == "P0" and not case.get("release_blocking_reason"):
            add("error", f"cases[{index}].release_blocking_reason", "P0 必须说明不过为何阻断发布")
        if VAGUE_EXPECTED.fullmatch(expected_result):
            add("error", f"cases[{index}].expected_result", f"预期结果不可观察：{expected_result}")
        state_oracle = case.get("state_oracle")
        if state_oracle is not None:
            if not isinstance(state_oracle, dict):
                add("error", f"cases[{index}].state_oracle", "必须是对象")
            else:
                if not state_oracle.get("intermediate") or not state_oracle.get("terminal"):
                    add("error", f"cases[{index}].state_oracle", "必须分开写中间业务状态与最终业务状态")
                if not state_oracle.get("technical_outcome"):
                    add("error", f"cases[{index}].state_oracle.technical_outcome", "必须单列技术执行结果")
                if (
                    state_oracle.get("intermediate")
                    and state_oracle.get("technical_outcome")
                    and state_oracle.get("intermediate") == state_oracle.get("technical_outcome")
                ):
                    add("error", f"cases[{index}].state_oracle", "业务状态与技术执行结果不能复用同一值")
        execution_mode = str(case.get("execution_mode", "automated"))
        if execution_mode not in EXECUTION_MODES:
            add("error", f"cases[{index}].execution_mode", f"非法执行方式 {execution_mode}")
        if "status" in case:
            add("error", f"cases[{index}].status", "用例状态必须由 executions 派生，不能重复维护")
        for req_id in case.get("requirement_ids", []):
            if str(req_id).startswith("RISK-"):
                continue
            if str(req_id) not in requirement_index:
                add("error", f"cases[{index}].requirement_ids", f"引用不存在的需求 {req_id}")
        for mechanism_id in case.get("risk_mechanism_ids", []):
            mechanism_id = str(mechanism_id)
            mechanism = risk_mechanism_index.get(mechanism_id)
            if not mechanism:
                add("error", f"cases[{index}].risk_mechanism_ids", f"引用不存在的风险机制 {mechanism_id}")
            elif case_id not in [str(value) for value in mechanism.get("case_ids", [])]:
                add("error", f"cases[{index}].risk_mechanism_ids", f"{mechanism_id} 未反向引用 {case_id}")

    acceptance_ids: set[str] = set()
    accepted_case_ids: set[str] = set()
    for index, check in enumerate(run["acceptance_checks"]):
        check_id = str(check.get("id", ""))
        if not re.fullmatch(r"AC-[A-Z0-9_-]+-\d{3}", check_id, flags=re.IGNORECASE):
            add("error", f"acceptance_checks[{index}].id", "应为 AC-<模块>-NNN")
        if check_id in acceptance_ids:
            add("error", f"acceptance_checks[{index}].id", "验收项 ID 重复")
        acceptance_ids.add(check_id)
        for field in ("title", "type", "case_ids", "blocking", "notes"):
            if field not in check:
                add("error", f"acceptance_checks[{index}].{field}", "缺少字段")
        if not check.get("title"):
            add("error", f"acceptance_checks[{index}].title", "不能为空")
        if check.get("type") not in ACCEPTANCE_TYPES:
            add("error", f"acceptance_checks[{index}].type", "非法验收类型")
        if not isinstance(check.get("blocking"), bool):
            add("error", f"acceptance_checks[{index}].blocking", "必须是布尔值")
        case_ids = [str(value) for value in check.get("case_ids", [])]
        if not case_ids:
            add("error", f"acceptance_checks[{index}].case_ids", "验收项必须关联至少一条用例")
        for case_id in case_ids:
            if case_id not in case_index:
                add("error", f"acceptance_checks[{index}].case_ids", f"引用不存在的用例 {case_id}")
            accepted_case_ids.add(case_id)
        if "status" in check:
            add("error", f"acceptance_checks[{index}].status", "验收状态必须从 executions 派生，不能重复维护")
    if len(run["acceptance_checks"]) > 30:
        add("warning", "acceptance_checks", "验收项超过 30 条，检查是否误把用例逐条复制为验收清单")
    for case in run["cases"]:
        case_id = str(case.get("id", ""))
        if case.get("priority") == "P0" and case_id not in accepted_case_ids and run["profile"] in {"full", "hotfix", "mobile"}:
            add("error", f"cases[{case_id}]", "完整提测/热修复的 P0 用例必须进入决策级验收清单")

    execution_ids: set[str] = set()
    for index, execution in enumerate(run["executions"]):
        execution_id = str(execution.get("id", ""))
        if not execution_id or execution_id in execution_ids:
            add("error", f"executions[{index}].id", "执行 ID 缺失或重复")
        elif not re.fullmatch(r"EXE-[A-Z0-9_-]+", execution_id, flags=re.IGNORECASE):
            add("error", f"executions[{index}].id", "执行 ID 必须使用 EXE-* 命名空间")
        execution_ids.add(execution_id)
        case_id = str(execution.get("case_id", ""))
        if case_id not in case_index:
            add("error", f"executions[{index}].case_id", f"引用不存在的用例 {case_id}")
        status = str(execution.get("status", ""))
        if status not in EXECUTION_STATUSES:
            add("error", f"executions[{index}].status", f"非法执行状态 {status}")
        level = str(execution.get("execution_level", ""))
        if level not in EXECUTION_LEVELS:
            add("error", f"executions[{index}].execution_level", f"非法执行等级 {level}")
        validation_scope = str(execution.get("validation_scope", "formal"))
        if validation_scope not in VALIDATION_SCOPES:
            add("error", f"executions[{index}].validation_scope", "必须是 precheck/exploratory/formal")
        if run.get("schema_version") == 2 and "validation_scope" not in execution:
            add("error", f"executions[{index}].validation_scope", "schema_version=2 必须显式声明证据适用范围")
        execution_method = str(execution.get("execution_method", "automated"))
        if execution_method not in {"automated", "manual"}:
            add("error", f"executions[{index}].execution_method", f"非法执行方法 {execution_method}")
        if execution_method == "manual" and not execution.get("operator"):
            add("error", f"executions[{index}].operator", "人工执行必须记录操作人或角色")
        if execution_method == "manual":
            for field in ("actual_result", "started_at", "finished_at"):
                if not execution.get(field):
                    add("error", f"executions[{index}].{field}", f"人工执行必须记录 {field}")
            attempt = execution.get("attempt")
            if not isinstance(attempt, int) or attempt < 1:
                add("error", f"executions[{index}].attempt", "人工执行 attempt 必须是大于等于 1 的整数")
            retest_of = execution.get("retest_of")
            if retest_of:
                previous = next((item for item in run["executions"] if item.get("id") == retest_of), None)
                if not previous:
                    add("error", f"executions[{index}].retest_of", f"引用不存在的执行 {retest_of}")
                elif previous.get("case_id") != case_id:
                    add("error", f"executions[{index}].retest_of", "复测只能引用同一用例的历史执行")
        evidence_ids = [str(value) for value in execution.get("evidence_ids", [])]
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_index:
                add("error", f"executions[{index}].evidence_ids", f"引用不存在的证据 {evidence_id}")
        if status == "passed" and not evidence_ids and not execution.get("assertions"):
            add("error", f"executions[{index}]", "通过执行必须包含断言或证据")
        if status == "pending_confirmation" and not execution.get("confirmation_needed"):
            add("error", f"executions[{index}].confirmation_needed", "待确认记录必须说明需要确认什么")
        if validation_scope == "precheck" and execution.get("formal_conclusion") is True:
            add("error", f"executions[{index}].formal_conclusion", "预跑结果不能声明为正式结论")
        method = str(execution.get("http_method", "")).upper()
        if method and method not in SAFE_HTTP_METHODS:
            writes_allowed = bool(run.get("test_data", {}).get("writes_allowed", False))
            if not writes_allowed:
                add("error", f"executions[{index}].http_method", "写请求默认关闭，未获得 writes_allowed 授权")

    for index, evidence in enumerate(run["evidence"]):
        evidence_id = str(evidence.get("id", ""))
        if not re.fullmatch(r"EVD-[A-Z0-9_-]+", evidence_id, flags=re.IGNORECASE):
            add("error", f"evidence[{index}].id", "证据 ID 必须使用 EVD-* 命名空间")
        path_value = str(evidence.get("path", ""))
        evidence_type = str(evidence.get("type", ""))
        evidence_level = str(evidence.get("level", ""))
        if evidence_level and evidence_level not in EVIDENCE_LEVELS:
            add("error", f"evidence[{index}].level", "必须是 L0_claim..L4_formal")
        if run.get("schema_version") == 2 and not evidence_level:
            add("error", f"evidence[{index}].level", "schema_version=2 必须标记证据等级")
        validation_scope = str(evidence.get("validation_scope", "formal"))
        if validation_scope not in VALIDATION_SCOPES:
            add("error", f"evidence[{index}].validation_scope", "必须是 precheck/exploratory/formal")
        if evidence_type not in {"assertions", "manual_observation"} and not path_value:
            add("error", f"evidence[{index}].path", "文件型证据必须提供路径")
        if artifact_root and path_value and not path_value.startswith(("http://", "https://")):
            if not (artifact_root / path_value).exists():
                add("warning", f"evidence[{index}].path", f"证据文件不存在：{path_value}")

    precheck_execution_ids = {
        str(item.get("id", ""))
        for item in run["executions"]
        if item.get("validation_scope") == "precheck"
    }
    precheck_evidence_ids = {
        str(value)
        for item in run["executions"]
        if item.get("validation_scope") == "precheck"
        for value in item.get("evidence_ids", [])
    } | {
        str(item.get("id", ""))
        for item in run["evidence"]
        if item.get("validation_scope") == "precheck"
    }
    formal_evidence_ids = {
        str(value)
        for item in run["executions"]
        if item.get("validation_scope", "formal") == "formal"
        for value in item.get("evidence_ids", [])
    } | {
        str(item.get("id", ""))
        for item in run["evidence"]
        if item.get("validation_scope", "formal") == "formal"
    }

    bug_ids: set[str] = set()
    active_bug_claims_by_execution: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, bug in enumerate(run["bugs"]):
        bug_id = str(bug.get("id", ""))
        if not bug_id or bug_id in bug_ids:
            add("error", f"bugs[{index}].id", "Bug ID 缺失或重复")
        elif not re.fullmatch(r"BUG-[A-Z0-9_-]+-\d{3}", bug_id, flags=re.IGNORECASE):
            add("error", f"bugs[{index}].id", "应为 BUG-<模块>-NNN")
        bug_ids.add(bug_id)
        severity = str(bug.get("severity", "")).upper()
        priority = str(bug.get("priority", "")).upper()
        if severity not in SEVERITIES:
            add("error", f"bugs[{index}].severity", "严重程度必须是 S1/S2/S3/S4")
        if priority not in PRIORITIES:
            add("error", f"bugs[{index}].priority", "优先级必须是 P0/P1/P2/P3")
        for field in (
            "module", "status", "severity_basis", "environment", "preconditions", "steps",
            "actual_result", "expected_result", "impact", "analysis", "workaround", "related_ids",
        ):
            if bug.get(field) in (None, "", []):
                add("error", f"bugs[{index}].{field}", "正式 Bug 字段不能为空；未知时明确写待补充及下一步")
        if bug.get("status") not in BUG_STATUSES:
            add("error", f"bugs[{index}].status", "非法 Bug 状态")
        analysis = bug.get("analysis")
        if not isinstance(analysis, dict):
            add("error", f"bugs[{index}].analysis", "必须是结构化对象")
        else:
            for field in (
                "classification", "trigger_hypothesis", "change_correlation",
                "blast_radius", "confidence",
            ):
                if not analysis.get(field):
                    add("error", f"bugs[{index}].analysis.{field}", "不能为空")
            if analysis.get("confidence") not in ANALYSIS_CONFIDENCE:
                add("error", f"bugs[{index}].analysis.confidence", "必须是 high/medium/low/unknown")
        reproducibility = str(bug.get("reproducibility", ""))
        if reproducibility not in REPRODUCIBILITY:
            add("error", f"bugs[{index}].reproducibility", "缺少或非法 reproducibility")
        attempts = bug.get("repro_attempts")
        if not isinstance(attempts, int) or attempts < 1:
            add("error", f"bugs[{index}].repro_attempts", "必须是大于等于 1 的整数")
        if not isinstance(bug.get("first_failure_preserved"), bool):
            add("error", f"bugs[{index}].first_failure_preserved", "必须明确是否保留首次失败")
        if not bug.get("evidence_grade"):
            add("error", f"bugs[{index}].evidence_grade", "必须记录 evidence_grade")
        if not bug.get("evidence_ids"):
            add("warning", f"bugs[{index}].evidence_ids", "正式 Bug 没有关联证据；若仅为用户口述需明确证据等级")
        category = str(bug.get("category", ""))
        if category not in {"static_ui", "interaction", "state", "timing", "api", "crash", "flaky", "other"}:
            add("error", f"bugs[{index}].category", "必须记录合法 Bug 证据类别")
        for evidence_id in bug.get("evidence_ids", []):
            if str(evidence_id) not in evidence_index:
                add("error", f"bugs[{index}].evidence_ids", f"引用不存在的证据 {evidence_id}")
        related_ids = {str(value) for value in bug.get("related_ids", [])}
        if bug.get("status") not in {"closed", "rejected"}:
            for execution_id in sorted(related_ids & execution_ids):
                active_bug_claims_by_execution.setdefault(execution_id, []).append((index, bug))
        bug_evidence_ids = {str(value) for value in bug.get("evidence_ids", [])}
        if related_ids & precheck_execution_ids:
            add("error", f"bugs[{index}].related_ids", "性能预跑执行不能直接提升为正式 Bug；先完成正式复测")
        if bug_evidence_ids & precheck_evidence_ids and not bug_evidence_ids & formal_evidence_ids:
            add("error", f"bugs[{index}].evidence_ids", "Bug 仅由预跑证据支持；必须补正式复现证据或降级为待确认")
        bug_evidence_types = {
            str(evidence_index.get(str(value), {}).get("type", ""))
            for value in bug.get("evidence_ids", [])
        }
        evidence_rank = {
            "L0_claim": 0, "L1_document": 1, "L2_observation": 2,
            "L3_reproducible": 3, "L4_formal": 4,
        }
        bug_evidence_levels = [
            evidence_rank.get(str(evidence_index.get(str(value), {}).get("level", "")), -1)
            for value in bug.get("evidence_ids", [])
        ]
        if run.get("schema_version") == 2 and (
            not bug_evidence_levels or max(bug_evidence_levels) < evidence_rank["L2_observation"]
        ):
            add("error", f"bugs[{index}].evidence_ids", "正式 Bug 至少需要 L2_observation 证据；否则保留为缺陷候选或待确认")
        if category == "static_ui" and "screenshot" not in bug_evidence_types:
            add("warning", f"bugs[{index}].evidence_ids", "静态 UI Bug 应提供截图")
        if category in {"interaction", "state", "timing"} and not bug_evidence_types.intersection({"video", "trace", "screenshot", "log"}):
            add("warning", f"bugs[{index}].evidence_ids", "交互/状态/时序 Bug 应提供步骤截图、视频、trace 或日志")
        if category == "api" and not bug_evidence_types.intersection({"request_response", "network", "trace"}):
            add("warning", f"bugs[{index}].evidence_ids", "API Bug 应提供请求、响应或 trace")
        if category == "crash" and not bug_evidence_types.intersection({"crash", "crash_check", "log"}):
            add("warning", f"bugs[{index}].evidence_ids", "Crash Bug 应提供日志或 crash 文件")
        if reproducibility == "intermittent" and attempts < 2:
            add("error", f"bugs[{index}].repro_attempts", "偶现 Bug 至少记录两次尝试")
        if reproducibility in {"once", "intermittent", "not_reproduced"} and bug.get("first_failure_preserved") is not True:
            add("error", f"bugs[{index}].first_failure_preserved", "非必现问题必须保留首次失败")

    for execution_id, claims in active_bug_claims_by_execution.items():
        if len(claims) < 2:
            continue
        signatures = [
            str(bug.get("independent_failure_signature", "")).strip()
            for _, bug in claims
        ]
        if all(signatures) and len(set(signatures)) == len(signatures):
            continue
        paths = ", ".join(f"bugs[{index}]" for index, _ in claims)
        add(
            "error",
            paths,
            f"同一次执行 {execution_id} 被拆成 {len(claims)} 个开放 Bug；"
            "FIX: 合并为一个 Bug，或为每个独立失败填写唯一 independent_failure_signature",
        )

    candidate_ids: set[str] = set()
    for index, candidate in enumerate(run.get("bug_candidates", [])):
        candidate_id = str(candidate.get("id", ""))
        if not candidate_id or candidate_id in candidate_ids:
            add("error", f"bug_candidates[{index}].id", "缺陷候选 ID 缺失或重复")
        candidate_ids.add(candidate_id)
        for field in ("case_id", "title", "status", "first_execution_id", "first_failure_preserved"):
            if candidate.get(field) in (None, ""):
                add("error", f"bug_candidates[{index}].{field}", "不能为空")
        if candidate.get("case_id") not in case_index:
            add("error", f"bug_candidates[{index}].case_id", "引用不存在的用例")
        if not any(item.get("id") == candidate.get("first_execution_id") for item in run["executions"]):
            add("error", f"bug_candidates[{index}].first_execution_id", "引用不存在的首次失败执行")
        if candidate.get("first_failure_preserved") is not True:
            add("error", f"bug_candidates[{index}].first_failure_preserved", "缺陷候选必须保留首次失败")

    for index, blocker in enumerate(run.get("blockers", [])):
        actions = blocker.get("minimal_unblock_actions", [])
        if not isinstance(actions, list) or not actions:
            add("error", f"blockers[{index}]", "阻塞项必须包含最小补齐动作")

    manual_handoff = run.get("manual_handoff", {})
    if manual_handoff and not isinstance(manual_handoff, dict):
        add("error", "manual_handoff", "必须是对象")
        manual_handoff = {}
    if manual_handoff.get("required"):
        status = str(manual_handoff.get("status", ""))
        if status not in MANUAL_HANDOFF_STATUSES - {"not_required"}:
            add("error", "manual_handoff.status", "人工交接状态必须是 pending/in_progress/completed/blocked")
        if run.get("selected_path") != "manual_handoff":
            add("error", "selected_path", "需要人工交接时 selected_path 必须是 manual_handoff")
        if not manual_handoff.get("reason"):
            add("error", "manual_handoff.reason", "必须说明自动化不可用和转人工的原因")
        manual_case_ids = [str(value) for value in manual_handoff.get("case_ids", [])]
        if not manual_case_ids:
            add("error", "manual_handoff.case_ids", "人工交接必须至少关联一个用例")
        for case_id in manual_case_ids:
            case = case_index.get(case_id)
            if not case:
                add("error", "manual_handoff.case_ids", f"引用不存在的用例 {case_id}")
                continue
            if case.get("execution_mode") not in {"manual", "hybrid"}:
                add("error", f"cases[{case_id}].execution_mode", "人工交接用例必须标为 manual 或 hybrid")
            if not case.get("assigned_to"):
                add("error", f"cases[{case_id}].assigned_to", "人工交接用例必须指定执行人或角色")
            if not case.get("manual_reason"):
                add("error", f"cases[{case_id}].manual_reason", "人工交接用例必须说明人工原因")
            if not lines_like(case.get("evidence_expected")):
                add("error", f"cases[{case_id}].evidence_expected", "人工交接用例必须说明应回传的证据")
        if not lines_like(manual_handoff.get("prerequisites")):
            add("error", "manual_handoff.prerequisites", "人工交接必须包含执行前准备")
        if not lines_like(manual_handoff.get("result_submission")):
            add("error", "manual_handoff.result_submission", "人工交接必须说明结果回传方式")

    host_os = str(run.get("environment", {}).get("host_os") or run.get("environment", {}).get("system") or "")
    target_type = str(run.get("target", {}).get("type", "")).lower()
    remote_macos = bool(run.get("environment", {}).get("remote_macos_runner"))
    if host_os in {"Windows", "Linux"} and target_type in {"ios", "ios_app", "iphone", "ipad"} and not remote_macos:
        ios_blockers = [
            item
            for item in run.get("blockers", [])
            if item.get("code") == "IOS_REQUIRES_MACOS" or str(item.get("platform", "")).lower() == "ios"
        ]
        manual_executions = [
            item for item in run.get("executions", []) if item.get("execution_method") == "manual"
        ]
        if not manual_executions and run.get("execution_level") != "blocked":
            add("error", "execution_level", f"{host_os} 本机 iOS 自动化必须 blocked，除非声明 remote_macos_runner")
        if manual_executions and run.get("execution_level") not in {"exploratory", "partial_validation", "blocked"}:
            add("error", "execution_level", f"{host_os} 回传的 iOS 人工结果只能记为 exploratory/partial_validation")
        if not ios_blockers:
            add("error", "blockers", f"{host_os} 本机 iOS 测试必须包含 IOS_REQUIRES_MACOS blocker")
        if any(item.get("execution_level") == "full_automation" for item in run.get("executions", [])):
            add("error", "executions", f"{host_os} 本机不能产生 iOS full_automation")
        if not manual_handoff.get("required"):
            add("error", "manual_handoff", f"{host_os} 本机 iOS 自动化不可用时必须生成可执行的人工测试交接")

    for index, risk in enumerate(run["risks"]):
        for field in ("id", "title", "priority", "description"):
            if not risk.get(field):
                add("error", f"risks[{index}].{field}", "不能为空")

    change_ids: set[str] = set()
    last_count_by_type: dict[str, int] = {}
    last_revision = 0
    for index, change in enumerate(run["change_ledger"]):
        change_id = str(change.get("id", ""))
        if not re.fullmatch(r"CHG-\d{3,}", change_id):
            add("error", f"change_ledger[{index}].id", "应为 CHG-NNN")
        if change_id in change_ids:
            add("error", f"change_ledger[{index}].id", "变更 ID 重复")
        change_ids.add(change_id)
        revision = change.get("revision")
        if not isinstance(revision, int) or revision < 1 or revision > run["revision"]:
            add("error", f"change_ledger[{index}].revision", "必须在 1..run.revision 范围内")
        elif revision < last_revision:
            add("error", f"change_ledger[{index}].revision", "revision 不得倒序")
        else:
            last_revision = revision
        action = str(change.get("action", "")).upper()
        object_type = str(change.get("object_type", ""))
        if action not in CHANGE_ACTIONS:
            add("error", f"change_ledger[{index}].action", f"非法 action {action}")
        if object_type not in CHANGE_OBJECT_TYPES:
            add("error", f"change_ledger[{index}].object_type", f"非法 object_type {object_type}")
        for field in ("source", "summary"):
            if not change.get(field):
                add("error", f"change_ledger[{index}].{field}", "不能为空")
        before = change.get("before_count")
        after = change.get("after_count")
        delta = change.get("delta_count")
        if not all(isinstance(value, int) and value >= 0 for value in (before, after)):
            add("error", f"change_ledger[{index}]", "before_count/after_count 必须是非负整数")
        elif not isinstance(delta, int) or after - before != delta:
            add("error", f"change_ledger[{index}].delta_count", "必须等于 after_count - before_count")
        if object_type in last_count_by_type and before != last_count_by_type[object_type]:
            add("error", f"change_ledger[{index}].before_count", f"必须承接上一条 {object_type} 的 after_count")
        if isinstance(after, int):
            last_count_by_type[object_type] = after
        if action in {"ADD", "RESTORE"} and isinstance(delta, int) and delta <= 0:
            add("error", f"change_ledger[{index}].delta_count", f"{action} 的 delta 必须为正")
        if action == "MODIFY" and delta != 0:
            add("error", f"change_ledger[{index}].delta_count", "MODIFY 的 delta 必须为 0")
        if action in {"REMOVE", "NARROW"} and isinstance(delta, int) and delta > 0:
            add("error", f"change_ledger[{index}].delta_count", f"{action} 的 delta 不得为正")
        if action == "REPLACE":
            if not lines_like(change.get("removed_ids")) or not lines_like(change.get("added_ids")):
                add("error", f"change_ledger[{index}]", "REPLACE 必须同时列出 removed_ids 和 added_ids")

    if not run["change_ledger"]:
        add("error", "change_ledger", "必须至少包含初始化变更")
    elif last_revision != run["revision"]:
        add("error", "revision", "必须等于 change_ledger 的最大 revision")

    current_counts = {
        "run": 1,
        "requirement": len(run["requirements"]),
        "risk_mechanism": len(run["risk_mechanisms"]),
        "case": len(run["cases"]),
        "acceptance": len(run["acceptance_checks"]),
        "execution": len(run["executions"]),
        "evidence": len(run["evidence"]),
        "bug": len(run["bugs"]),
        "delivery": len(run["delivery_manifest"].get("outputs", [])),
    }
    for object_type, count in current_counts.items():
        if count and object_type not in last_count_by_type:
            add("error", "change_ledger", f"{object_type} 当前有 {count} 项，但没有变更记录")
        elif object_type in last_count_by_type and last_count_by_type[object_type] != count:
            add("error", "change_ledger", f"{object_type} 台账末值 {last_count_by_type[object_type]} 与当前 {count} 不一致")

    delivery_manifest = run["delivery_manifest"]
    if delivery_manifest.get("source_revision") != run["revision"]:
        add("error", "delivery_manifest.source_revision", "必须与 run.revision 一致")
    outputs = delivery_manifest.get("outputs", [])
    if not isinstance(outputs, list):
        add("error", "delivery_manifest.outputs", "必须是数组")
        outputs = []
    for index, output in enumerate(outputs):
        carrier = str(output.get("carrier", ""))
        status = str(output.get("status", ""))
        output_format = str(output.get("format", ""))
        if carrier not in DELIVERY_CARRIERS:
            add("error", f"delivery_manifest.outputs[{index}].carrier", f"非法载体 {carrier}")
        if output_format and output_format not in DELIVERY_FORMATS:
            add("error", f"delivery_manifest.outputs[{index}].format", f"非法格式 {output_format}")
        if status not in {"planned", "created", "validated", "failed", "local_fallback", "stale"}:
            add("error", f"delivery_manifest.outputs[{index}].status", f"非法状态 {status}")
        if output.get("source_revision") != run["revision"] and status not in {"stale", "failed"}:
            add("error", f"delivery_manifest.outputs[{index}].source_revision", "非 stale/failed 产物必须匹配当前 revision")
        if status in {"created", "validated"} and not output.get("locator"):
            add("error", f"delivery_manifest.outputs[{index}].locator", "已创建产物必须记录真实 URL/token/路径")
        if status == "validated" and output.get("validated") is not True:
            add("error", f"delivery_manifest.outputs[{index}].validated", "validated 状态必须有回读成功标记")
        if status == "validated" and not output.get("readback_receipt"):
            add("error", f"delivery_manifest.outputs[{index}].readback_receipt", "validated 状态必须记录回读回执")
        locator = str(output.get("locator", ""))
        if carrier in {"local", "office_file"} and status == "validated":
            resolved = resolve_local_locator(locator, artifact_root)
            if resolved is None or not resolved.is_file():
                add("error", f"delivery_manifest.outputs[{index}].locator", "本地交付物不存在或不是文件")
            elif resolved.stat().st_size == 0:
                add("error", f"delivery_manifest.outputs[{index}].locator", "本地交付物为空文件")
            elif output_format == "markdown" and resolved.suffix.lower() != ".md":
                add("error", f"delivery_manifest.outputs[{index}].locator", "Markdown 交付物必须使用 .md 扩展名")

    phase_receipts = run.get("phase_receipts", [])
    if phase_receipts and not isinstance(phase_receipts, list):
        add("error", "phase_receipts", "必须是数组")
    elif isinstance(phase_receipts, list):
        seen_receipts: set[tuple[str, int]] = set()
        for index, receipt in enumerate(phase_receipts):
            receipt_revision = receipt.get("revision", 0)
            if not isinstance(receipt_revision, int):
                add("error", f"phase_receipts[{index}].revision", "必须是整数")
                receipt_revision = 0
            key = (str(receipt.get("stage", "")), receipt_revision)
            if key in seen_receipts:
                add("error", f"phase_receipts[{index}]", "同一 revision 的阶段回执重复")
            seen_receipts.add(key)
            if receipt.get("state") not in {"CLOSED", "DISCLOSE"}:
                add("error", f"phase_receipts[{index}].state", "只允许记录已通过的 CLOSED/DISCLOSE 回执")

    test_data = run["test_data"]
    for field in ("writes_allowed", "accounts", "created_records", "cleanup"):
        if field not in test_data:
            add("error", f"test_data.{field}", "缺少字段")

    expected_coverage = coverage_snapshot(run)
    if run["coverage"] != expected_coverage:
        add(
            "error",
            "coverage",
            f"与 canonical 执行数据不一致；FIX: 运行 qa_flow.py normalize，期望 {expected_coverage!r}",
        )

    decision = str(run["release_decision"].get("decision", ""))
    if decision not in RELEASE_DECISIONS:
        add("error", "release_decision.decision", f"非法发布结论 {decision}")
    if not run["executions"] and decision != "undetermined":
        add("error", "release_decision.decision", "零执行证据时只能是 undetermined，禁止建议或否定终审")
    p0_open = unresolved_p0(run)
    if decision == "go" and p0_open:
        add("error", "release_decision.decision", f"仍有未通过 P0：{', '.join(p0_open)}")
    open_p0_mechanisms = [
        str(item.get("id", ""))
        for item in run["risk_mechanisms"]
        if item.get("priority") == "P0" and item.get("status") != "verified"
    ]
    if decision == "go" and open_p0_mechanisms:
        add("error", "release_decision.decision", f"仍有未验证 P0 风险机制：{', '.join(open_p0_mechanisms)}")
    open_blocking_acceptance = [
        str(item.get("id", ""))
        for item in run["acceptance_checks"]
        if item.get("blocking") is True and acceptance_status(run, item) != "通过"
    ]
    if decision == "go" and open_blocking_acceptance:
        add(
            "error",
            "release_decision.decision",
            f"仍有未通过的阻断验收项：{', '.join(open_blocking_acceptance)}",
        )
    if decision == "no_go":
        supported = any(
            str(item.get("status", "")) in {"failed", "blocked", "infra_error"}
            for item in run["executions"]
        ) or any(
            str(item.get("severity", "")).upper() in {"S1", "S2"}
            and str(item.get("status", "open")) not in {"closed", "rejected"}
            for item in run["bugs"]
        )
        if not supported:
            add("error", "release_decision.decision", "no_go 必须由失败/阻塞执行或开放 S1/S2 证据支持")
    if decision in {"go", "conditional_go"} and any(
        str(item.get("severity", "")).upper() in {"S1", "S2"}
        and str(item.get("status", "open")) not in {"closed", "rejected"}
        for item in run["bugs"]
    ):
        add("error", "release_decision.decision", "存在未关闭 S1/S2，不能给出上线结论")
    if decision == "go" and any(
        str(item.get("status", "")) in OPEN_BUG_CANDIDATE_STATUSES
        for item in run.get("bug_candidates", [])
    ):
        add("error", "release_decision.decision", "存在未完成归因或复现的人工失败，不能给出无条件上线结论")

    findings.extend(p0_blocking_identity(run))
    findings.extend(unverified_consistency(run))
    findings.extend(open_oracle_discipline(run))

    cleanup = run.get("test_data", {}).get("cleanup", {})
    if cleanup and cleanup.get("required") and cleanup.get("status") not in {
        "completed",
        "failed",
        "blocked",
    }:
        add("error", "test_data.cleanup.status", "需要清理时必须记录 completed/failed/blocked")
    if cleanup.get("required") and cleanup.get("status") in {"failed", "blocked"} and decision == "go":
        add("error", "release_decision.decision", "测试数据未恢复，不能给出无条件上线结论")

    return findings


OPEN_BUG_STATUSES = {"open", "in_progress", "pending_retest"}


def p0_blocking_identity(run: dict[str, Any]) -> list[dict[str, str]]:
    """P0 ⟺ 阻断本次发布。

    金标准的真实规则不是"哪一类问题算 P0"，而是"P0 就是这次不修就不能发的那些"。
    四份金标准 4/4 满足该恒等式（组合优化只有 BUG-01 阻断且只有它是 P0；
    企业知识库前两条阻断灰度且只有它们是 P0；药品 R04/R08/R11 三条 P0 全部阻断）。
    这条恒等式静态可查，且能同时治两种病：把 P1 抬成 P0（膨胀），
    以及标了 P0 却不敢写进阻塞项（口惠而实不至）。
    """
    findings: list[dict[str, str]] = []
    bugs = [item for item in run.get("bugs", []) or [] if isinstance(item, dict)]
    open_p0 = {
        str(item.get("id"))
        for item in bugs
        if str(item.get("priority", "")).upper() == "P0"
        and str(item.get("status", "open")) in OPEN_BUG_STATUSES
    }
    if not bugs:
        return findings
    decision = run.get("release_decision", {}) or {}
    if "blocking_bug_ids" not in decision:
        if open_p0:
            findings.append({
                "level": "error",
                "path": "release_decision.blocking_bug_ids",
                "message": f"有 {len(open_p0)} 个开放 P0，必须在发布结论里逐个列为阻塞项",
                "fix": f'在 release_decision 增加 "blocking_bug_ids": {sorted(open_p0)}',
            })
        return findings
    declared = {str(item) for item in decision.get("blocking_bug_ids") or []}
    inflated = sorted(open_p0 - declared)
    understated = sorted(declared - open_p0)
    if inflated:
        findings.append({
            "level": "error",
            "path": "release_decision.blocking_bug_ids",
            "message": f"这些 Bug 标了 P0 却没有阻断发布：{', '.join(inflated)}",
            "fix": "要么把它们写进 blocking_bug_ids，要么按金标准口径降到 P1（本期修复但不阻断）",
        })
    if understated:
        findings.append({
            "level": "error",
            "path": "release_decision.blocking_bug_ids",
            "message": f"这些 Bug 阻断了发布却不是开放 P0：{', '.join(understated)}",
            "fix": "把它们的 priority 改成 P0，或从 blocking_bug_ids 移除",
        })
    return findings


def unverified_consistency(run: dict[str, Any]) -> list[dict[str, str]]:
    """有未执行用例就必须有未验证范围。

    实测事故：成品同时写着「未验证范围：无」和 21 条「未执行」。
    `unverified` 是手填字段，没有任何东西把未执行推导进去。
    """
    counts = (run.get("coverage") or {}).get("case_status_counts") or {}
    not_run = int(counts.get("未执行", 0)) + int(counts.get("阻塞", 0))
    if not not_run:
        return []
    unverified = run.get("unverified")
    if isinstance(unverified, str):
        unverified = [unverified] if unverified.strip() else []
    if unverified:
        return []
    if not run.get("executions"):
        # 纯方案任务：所有用例天然未执行，要写的是"已知未覆盖的能力"。
        # 金标准在只有 PRD 的题目里同样单列了这一项（平台券真实到账为已知范围外）。
        return [{
            "level": "error",
            "path": "unverified",
            "message": "本轮无执行证据，必须写明已知未覆盖范围",
            "fix": '在 unverified 列出本轮明确不覆盖的能力，例如 ["平台券真实到账依赖下游未联调接口，本轮不覆盖"]',
        }]
    return [{
        "level": "error",
        "path": "unverified",
        "message": f"有 {not_run} 条用例未执行，未验证范围不能为空",
        "fix": "在 unverified 写清哪些能力/组合本轮没有被验证，以及它对发布判断的影响",
    }]


AMBIGUITY_MARKERS = ("≥", "≤", ">", "<", "边界", "含", "计算顺序", "自然日", "整数", "封顶", "到账")


def open_oracle_discipline(run: dict[str, Any]) -> list[dict[str, str]]:
    """未决口径不得写成唯一预期。

    开放问题里凡涉及边界符号、计算顺序、时间口径或外部依赖到账的，
    受影响用例的预期必须是双轨（写出两种口径各自的结果）或明确标阻塞。
    判据取自实测：知贝把 7 天写死成 168 小时、把 50% 封顶顺序写死、
    把平台券到账写进期望结果——三条都是在 PRD 明说"待确认"的情况下发生的。
    """
    findings: list[dict[str, str]] = []
    open_questions = [
        item for item in run.get("open_questions", []) or []
        if isinstance(item, dict) and str(item.get("status", "open")) in {"open", "待确认", "pending"}
    ]
    risky = [
        item for item in open_questions
        if any(marker in str(item.get("question", "")) for marker in AMBIGUITY_MARKERS)
    ]
    if not risky:
        return findings
    cases = {str(item.get("id")): item for item in run.get("cases", []) or [] if isinstance(item, dict)}
    for question in risky:
        affected = [str(cid) for cid in question.get("affected_case_ids") or []]
        if not affected:
            continue
        rigid = []
        for case_id in affected:
            case = cases.get(case_id)
            if not case:
                continue
            expected = " ".join(lines_like(case.get("expected_result")))
            dual = any(token in expected for token in ("若", "如果", "两种", "双轨", "口径 A", "待确认", "阻塞"))
            if expected and not dual:
                rigid.append(case_id)
        if rigid:
            findings.append({
                "level": "error",
                "path": "open_questions[].oracle_discipline",
                "message": f"{question.get('id')} 未决，但 {', '.join(rigid)} 已写成唯一预期",
                "fix": "改成双轨预期（写出两种口径各自的结果），或把用例标为阻塞待澄清",
            })
    return findings


def lines_like(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]
