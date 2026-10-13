#!/usr/bin/env python3
"""Deterministic pipeline rollup, movement, concentration, and local gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from artifact_receipts import file_sha256, validate_artifact_receipts, write_json


SCHEMA_VERSION = "sales.pipeline-forecast.v2"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACTS = set(
    json.loads((PACKAGE_ROOT / "config" / "runtime.json").read_text(encoding="utf-8"))
    ["claim_artifact_permission_gate"]["required_artifacts"]
)
CLAIM_FIELDS = {
    "claim_id", "claim", "claim_type", "critical", "object_id", "period",
    "unit", "source_ids", "source_tier", "confidence", "conflict_state",
}
CLAIM_TYPES = {"fact", "calculation", "inference", "assumption", "management_claim", "unknown"}
SOURCE_TIERS = {
    "primary", "customer_primary", "counterparty", "official", "crm_truth",
    "transaction_primary", "secondary", "lead_only",
}
CONFIDENCE = {"high", "medium", "low"}
CONFLICT_STATES = {"none", "open", "resolved"}
STRONG_SOURCE_TIERS = {"primary", "customer_primary", "official", "crm_truth", "transaction_primary"}
SAFE_ACTIONS = {"read", "analyze", "draft"}
CONFIRM_ACTIONS = {
    "send", "write", "write_crm", "create", "create_opportunity",
    "close_opportunity", "create_task", "publish", "update",
    "sequence_activate", "sequence_enroll",
}
DENY_ACTIONS = {"delete", "pay", "bribe", "bypass_control"}
USER_VISIBLE_FORBIDDEN_PATTERNS = (
    r"\bartifact_state\b", r"\bdelivery_tier\b", r"\bselected_skill\b",
    r"\broute_status\b", r"\bpermission_status\b", r"\bblocked_slots\b",
    r"\bclaim_(?:ledger|gate)\b", r"\bartifact_gate\b", r"\bpermission_gate\b",
    r"\bcrm_truth\b", r"\bschema(?:_version)?\b", r"\bpayload\b", r"\bsha256\b",
    r"(?:^|[^A-Za-z0-9_])scripts[\\/]", r"(?:^|[^A-Za-z0-9_])runtime[\\/]",
    r"\.full\.json", r"\.compact\.json", r"Hard Gate", r"主张台账",
    r"能力槽", r"工件索引", r"Traceback \(most recent call last\)",
    r"ModuleNotFoundError", r"\btool_call\b", r"\bclaim\s+ledger\b",
    r"\bSKILL\.md\b", r"\bCLI\b", r"\b(?:state|mode)\s*[=:]",
    r"(?:已|正在|将要)?(?:读取|调用|运行|执行).{0,12}(?:Skill|脚本|CLI|scripts[\\/])",
)
REFERENCE_ONLY_PATTERNS = (
    r"(?:完整|全部|详细|主工件|正文).{0,20}(?:请)?(?:见|查看|参见).{0,8}(?:附件|链接|文档)",
    r"文档已生成",
)
COMPLETION_TERMS = (
    "已发送", "已写回", "已创建", "已关闭", "已修改", "已加入序列", "已触达",
    "已完成", "已生成",
)
USER_SECTION_GROUPS = {
    "decision": ("结论", "判断", "建议"),
    "primary_artifact": ("账户", "外联", "管道", "预测", "漏斗", "预算", "行动清单", "QBR"),
    "evidence": ("依据", "来源", "证据", "CRM"),
    "uncertainty": ("待确认", "未知", "风险", "暂缓"),
    "next_action": ("下一步", "建议动作", "内部核验", "内部协调"),
}
CONSTRAINT_ORDER = (
    "account_identity", "owner", "suppression", "active_opportunity",
    "channel_capacity", "signal", "action",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def number(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    return int(integral) if value == integral else float(value)


def decimal_or_none(value: Any) -> Optional[Decimal]:
    if value is None or (isinstance(value, str) and value.strip().lower() in {"", "unknown", "null"}):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def lint_user_visible(payload: Any) -> dict:
    """Validate the business-facing response separately from internal artifacts."""
    if isinstance(payload, str):
        payload = {"text": payload}
    text = str((payload or {}).get("text") or "").strip()
    delivery_tier = (payload or {}).get("delivery_tier", "direct")
    max_chars = {"direct": 1800, "brief": 5200, "full": 11000}.get(delivery_tier, 11000)
    failures: List[str] = []
    if len(text) < 80:
        failures.append("user-visible response is not a minimum complete artifact")
    if len(text) > max_chars:
        failures.append(f"user-visible response exceeds {delivery_tier} character budget")
    for pattern in USER_VISIBLE_FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            failures.append(f"internal protocol leaked: {pattern}")
    for pattern in REFERENCE_ONLY_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            failures.append("external artifact is being used instead of an inline primary artifact")
            break
    required_sections = (payload or {}).get("required_sections") or list(USER_SECTION_GROUPS)
    missing_sections = []
    for section in required_sections:
        terms = USER_SECTION_GROUPS.get(section, (str(section),))
        if not any(term in text for term in terms):
            missing_sections.append(section)
    if missing_sections:
        failures.append(f"missing business sections: {','.join(missing_sections)}")
    completion_evidence = (payload or {}).get("completion_evidence") or []
    if not completion_evidence:
        used = [term for term in COMPLETION_TERMS if term in text]
        if used:
            failures.append(f"completion language lacks evidence: {','.join(used)}")
    return {
        "passed": not failures,
        "failures": failures,
        "character_count": len(text),
        "delivery_tier": delivery_tier,
    }


def validate_crm_actions(actions: Any) -> dict:
    """Keep proposed CRM/contact actions distinct from observed execution state."""
    failures: List[str] = []
    normalized = []
    if actions is None:
        return {"passed": True, "failures": [], "actions": []}
    if not isinstance(actions, list):
        return {"passed": False, "failures": ["actions must be a list"], "actions": []}
    for index, action in enumerate(actions):
        current_state = action.get("current_state", "unknown")
        proposed_action = action.get("proposed_action")
        approval_required = bool(action.get("approval_required", True))
        completion_evidence = action.get("completion_evidence") or []
        execution_state = action.get("execution_state", "proposed")
        if not proposed_action:
            failures.append(f"actions[{index}] missing proposed_action")
        if execution_state in {"executed", "completed"} and not completion_evidence:
            failures.append(f"actions[{index}] executed state lacks completion evidence")
        if proposed_action in {"send", "write_crm", "create_opportunity", "close_opportunity"}:
            if not approval_required and not completion_evidence:
                failures.append(f"actions[{index}] side effect lacks approval boundary")
        normalized.append({
            "object_id": action.get("object_id"),
            "current_state": current_state,
            "proposed_action": proposed_action,
            "approval_required": approval_required,
            "completion_evidence": completion_evidence,
            "execution_state": execution_state,
        })
    return {"passed": not failures, "failures": failures, "actions": normalized}


def prioritize_accounts(payload: dict) -> dict:
    """Apply hard constraints before signals and proposed outreach."""
    accounts = payload.get("accounts")
    if not isinstance(accounts, list):
        raise ValueError("accounts must be a list")
    capacities = payload.get("channel_capacities") or {}
    used = defaultdict(int)
    seen: set[str] = set()
    failures: List[str] = []
    decisions = []
    eligible = []
    for index, account in enumerate(accounts):
        account_id = account.get("account_id")
        checks = []
        if not account_id or account_id in seen:
            checks.append({"constraint": "account_identity", "passed": False})
            action, reason = "no_contact", "missing_or_duplicate_account_id"
            failures.append(f"accounts[{index}] missing or duplicate stable account_id")
        else:
            seen.add(account_id)
            checks.append({"constraint": "account_identity", "passed": True})
            owner = account.get("owner")
            owner_verified = account.get("owner_verified") is True
            owner_conflict = account.get("owner_conflict") is True
            checks.append({"constraint": "owner", "passed": bool(owner and owner_verified and not owner_conflict)})
            if not owner or not owner_verified:
                action, reason = "internal_verification", "owner_not_verified"
            elif owner_conflict:
                action, reason = "internal_coordination", "owner_conflict"
            elif not isinstance(account.get("suppressed"), bool):
                checks.append({"constraint": "suppression", "passed": False})
                action, reason = "internal_verification", "suppression_unknown"
            elif account.get("suppressed") is True:
                checks.append({"constraint": "suppression", "passed": False})
                action, reason = "no_contact", "suppressed"
            elif not isinstance(account.get("active_opportunity"), bool):
                checks.append({"constraint": "suppression", "passed": True})
                checks.append({"constraint": "active_opportunity", "passed": False})
                action, reason = "internal_verification", "active_opportunity_unknown"
            elif account.get("active_opportunity") is True:
                checks.append({"constraint": "suppression", "passed": True})
                checks.append({"constraint": "active_opportunity", "passed": False})
                action, reason = "internal_coordination", "active_opportunity"
            else:
                checks.append({"constraint": "suppression", "passed": True})
                checks.append({"constraint": "active_opportunity", "passed": True})
                channel = account.get("channel", "default")
                capacity = decimal_or_none(capacities.get(channel))
                if capacity is None or capacity < 0 or capacity != capacity.to_integral_value():
                    checks.append({"constraint": "channel_capacity", "passed": False})
                    action, reason = "internal_verification", "channel_capacity_unknown_or_invalid"
                elif used[channel] >= int(capacity):
                    checks.append({"constraint": "channel_capacity", "passed": False})
                    action, reason = "no_contact", "channel_capacity_exhausted"
                elif account.get("signal") in (None, "", "unknown"):
                    checks.append({"constraint": "channel_capacity", "passed": True})
                    checks.append({"constraint": "signal", "passed": False})
                    action, reason = "internal_verification", "signal_unknown"
                else:
                    checks.append({"constraint": "channel_capacity", "passed": True})
                    checks.append({"constraint": "signal", "passed": True})
                    action, reason = "outreach_draft", "constraints_passed"
                    used[channel] += 1
                    eligible.append(account_id)
        checks.append({"constraint": "action", "passed": action == "outreach_draft"})
        decisions.append({
            "account_id": account_id,
            "action": action,
            "reason": reason,
            "contact_allowed": action == "outreach_draft",
            "constraint_order": list(CONSTRAINT_ORDER),
            "checks": checks,
        })
    return {
        "passed": not failures,
        "failures": failures,
        "selected_for_outreach": eligible,
        "channel_usage": dict(used),
        "decisions": decisions,
    }


def validate_channel_plan(payload: dict) -> dict:
    account_rows = payload.get("accounts") or []
    constraints = {row.get("account_id"): row for row in account_rows if row.get("account_id")}
    channels = payload.get("channels") or []
    seen: set[str] = set()
    failures: List[str] = []
    output = []
    total_budget = Decimal("0")
    for index, channel in enumerate(channels):
        account_ids = channel.get("account_ids") or []
        unique_ids = []
        unavailable = []
        for account_id in account_ids:
            if account_id in seen:
                failures.append(f"channels[{index}] duplicate account_id {account_id}")
                continue
            seen.add(account_id)
            unique_ids.append(account_id)
            record = constraints.get(account_id, {})
            if (
                not record
                or not record.get("owner")
                or record.get("owner_verified") is not True
                or record.get("suppressed") is not False
                or record.get("active_opportunity") is not False
            ):
                unavailable.append(account_id)
        capacity = decimal_or_none(channel.get("capacity"))
        if capacity is None:
            failures.append(f"channels[{index}] missing capacity")
        elif capacity < 0 or capacity != capacity.to_integral_value():
            failures.append(f"channels[{index}] invalid capacity")
        elif len(unique_ids) > capacity:
            failures.append(f"channels[{index}] exceeds capacity")
        if unavailable:
            failures.append(f"channels[{index}] contains unavailable accounts")
        budget = decimal_or_none(channel.get("budget"))
        if budget is None:
            failures.append(f"channels[{index}] missing budget")
        else:
            total_budget += budget
        output.append({
            "channel": channel.get("channel"),
            "account_count": len(unique_ids),
            "unavailable_count": len(unavailable),
            "unavailable_account_ids": unavailable,
            "capacity": None if capacity is None else number(capacity),
            "budget": None if budget is None else number(budget),
        })
    expected_budget = decimal_or_none(payload.get("expected_total_budget"))
    if expected_budget is None:
        failures.append("missing expected total budget")
    elif total_budget != expected_budget:
        failures.append("channel budgets do not match expected total")
    return {
        "passed": not failures,
        "failures": failures,
        "channels": output,
        "total_budget": number(total_budget),
        "expected_total_budget": None if expected_budget is None else number(expected_budget),
        "final_plan_allowed": not failures,
    }


def calculate_funnel_metrics(payload: dict) -> dict:
    failures: List[str] = []

    def calculate_row(row: dict, label: str) -> dict:
        inquiries = decimal_or_none(row.get("inquiries"))
        valid_leads = decimal_or_none(row.get("valid_leads"))
        spend = decimal_or_none(row.get("spend"))
        target_valid_leads = decimal_or_none(row.get("target_valid_leads"))
        intent_grade_count = decimal_or_none(row.get("intent_grade_count"))
        if inquiries is None or inquiries <= 0:
            failures.append(f"{label} missing positive inquiries denominator")
        if valid_leads is None or valid_leads < 0:
            failures.append(f"{label} missing valid_leads")
        if inquiries is not None and valid_leads is not None and valid_leads > inquiries:
            failures.append(f"{label} valid_leads exceeds inquiries")
        valid_rate = None if inquiries in (None, 0) or valid_leads is None else valid_leads / inquiries
        cpl = None if spend is None or valid_leads in (None, 0) else spend / valid_leads
        target_cpl = None if spend is None or target_valid_leads in (None, 0) else spend / target_valid_leads
        return {
            "inquiries": None if inquiries is None else number(inquiries),
            "valid_leads": None if valid_leads is None else number(valid_leads),
            "intent_grade_count": None if intent_grade_count is None else number(intent_grade_count),
            "valid_rate": None if valid_rate is None else float(valid_rate),
            "valid_rate_percent": None if valid_rate is None else float(round(valid_rate * 100, 1)),
            "cpl": None if cpl is None else float(round(cpl, 2)),
            "target_cpl": None if target_cpl is None else float(round(target_cpl, 2)),
        }

    overall = calculate_row(payload.get("overall") or {}, "overall")
    channels = {
        str(row.get("channel") or index): calculate_row(row, f"channels[{index}]")
        for index, row in enumerate(payload.get("channels") or [])
    }
    if payload.get("multiply_clicks_by_visitor_conversion") is True:
        failures.append("click and visitor denominators are incompatible")
    if payload.get("ctr_as_current_valid_lead_cause") is True:
        failures.append("CTR may be a future experiment, not a proven current cause")
    return {
        "passed": not failures,
        "failures": failures,
        "overall": overall,
        "channels": channels,
        "intent_grade_is_valid_lead": False,
        "ctr_treatment": "future_experiment_only",
    }


def analyze_event_cutoffs(payload: dict) -> dict:
    failures: List[str] = []
    rows = []
    for index, event in enumerate(payload.get("events") or []):
        try:
            start = datetime.fromisoformat(event["start_at"])
            alert = datetime.fromisoformat(event["alert_at"])
            freeze = datetime.fromisoformat(event["freeze_at"])
        except (KeyError, TypeError, ValueError):
            failures.append(f"events[{index}] invalid event timestamps")
            continue
        try:
            ordered = start <= alert <= freeze
        except TypeError:
            ordered = False
        if not ordered:
            failures.append(f"events[{index}] timestamps must satisfy start_at <= alert_at <= freeze_at")
            continue
        rows.append({
            "record_id": event.get("record_id"),
            "start_at": event["start_at"],
            "hours_to_alert": (alert - start).total_seconds() / 3600,
            "hours_to_final_freeze": (freeze - start).total_seconds() / 3600,
            "alert_at": event["alert_at"],
            "freeze_at": event["freeze_at"],
        })
    sample_size = decimal_or_none(payload.get("sample_size"))
    population_size = decimal_or_none(payload.get("population_size"))
    population_conclusion_allowed = bool(
        sample_size is not None and population_size is not None
        and sample_size == population_size and not failures
    )
    return {
        "passed": not failures,
        "failures": failures,
        "events": rows,
        "population_conclusion_allowed": population_conclusion_allowed,
        "sample_conclusion": "current_sample_only" if not population_conclusion_allowed else "full_population",
    }


def stage_sensitivity(amount: Any, candidate_stages: List[str], probabilities: dict) -> dict:
    amount_value = decimal_or_none(amount)
    if amount_value is None or not candidate_stages:
        return {"passed": False, "adjacent_deltas": [], "endpoint_delta": None}
    values = []
    for stage in candidate_stages:
        probability = decimal_or_none(probabilities.get(stage))
        if probability is None or probability < 0 or probability > 1:
            return {"passed": False, "adjacent_deltas": [], "endpoint_delta": None}
        values.append((stage, amount_value * probability))
    adjacent = [
        {
            "from_stage": values[index][0],
            "to_stage": values[index + 1][0],
            "delta": number(abs(values[index + 1][1] - values[index][1])),
        }
        for index in range(len(values) - 1)
    ]
    return {
        "passed": True,
        "weighted_values": {stage: number(value) for stage, value in values},
        "adjacent_deltas": adjacent,
        "endpoint_delta": number(abs(values[-1][1] - values[0][1])) if len(values) > 1 else 0,
    }


def evaluate_claims(claims: Any) -> dict:
    failures: List[str] = []
    unknown_count = 0
    if not isinstance(claims, list) or not claims:
        return {"passed": False, "failures": ["claims must be a non-empty list"], "unknown_count": 0}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            failures.append(f"claims[{index}] must be an object")
            continue
        missing = sorted(CLAIM_FIELDS - set(claim))
        additional = sorted(set(claim) - CLAIM_FIELDS)
        if missing:
            failures.append(f"claims[{index}] missing {missing}")
            continue
        if additional:
            failures.append(f"claims[{index}] additional fields {additional}")
        if not all(isinstance(claim[field], str) and claim[field] for field in ("claim_id", "claim", "object_id", "period")):
            failures.append(f"claims[{index}] string fields invalid")
        if not isinstance(claim["critical"], bool):
            failures.append(f"claims[{index}].critical must be boolean")
        if claim["unit"] is not None and not isinstance(claim["unit"], str):
            failures.append(f"claims[{index}].unit must be string or null")
        if not isinstance(claim["source_ids"], list) or not all(isinstance(item, str) and item for item in claim["source_ids"]):
            failures.append(f"claims[{index}].source_ids must be a string list")
        if claim["claim_type"] not in CLAIM_TYPES:
            failures.append(f"claims[{index}].claim_type invalid")
        if claim["source_tier"] not in SOURCE_TIERS:
            failures.append(f"claims[{index}].source_tier invalid")
        if claim["confidence"] not in CONFIDENCE:
            failures.append(f"claims[{index}].confidence invalid")
        if claim["conflict_state"] not in CONFLICT_STATES:
            failures.append(f"claims[{index}].conflict_state invalid")
        elif claim.get("claim_type") == "unknown":
            unknown_count += 1
        elif claim.get("critical") and (
            not claim.get("source_ids") or claim.get("source_tier") not in STRONG_SOURCE_TIERS
        ):
            failures.append(f"claims[{index}] critical claim lacks strong source")
    return {"passed": not failures, "failures": failures, "unknown_count": unknown_count}


def evaluate_permissions(requests: Any) -> dict:
    failures: List[str] = []
    confirmation_required: List[str] = []
    denied: List[str] = []
    for request in requests or []:
        action = request.get("action")
        if action in DENY_ACTIONS:
            denied.append(action)
        elif action in CONFIRM_ACTIONS and not (
            request.get("preview") and request.get("permission_confirmed")
        ):
            confirmation_required.append(action)
        elif action not in SAFE_ACTIONS | CONFIRM_ACTIONS:
            failures.append(f"unsupported action: {action}")
    return {
        "passed": not failures and not confirmation_required and not denied,
        "failures": failures,
        "confirmation_required": confirmation_required,
        "denied": denied,
        "execution": "not_executed" if failures or confirmation_required or denied else "allowed",
    }


def run_gates(payload: dict, artifact_receipts: Any = None) -> dict:
    context = payload.get("gate_context") or {}
    receipts = artifact_receipts if artifact_receipts is not None else context.get("artifact_receipts")
    artifact_gate = validate_artifact_receipts(receipts, REQUIRED_ARTIFACTS)
    claim_gate = evaluate_claims(payload.get("claims"))
    permission_gate = evaluate_permissions(context.get("permission_requests"))
    action_gate = validate_crm_actions(context.get("proposed_actions"))
    account_gate = (
        prioritize_accounts(context["account_priority_input"])
        if context.get("account_priority_input") is not None
        else {"passed": True, "failures": [], "status": "not_supplied"}
    )
    channel_gate = (
        validate_channel_plan(context["channel_plan_input"])
        if context.get("channel_plan_input") is not None
        else {"passed": True, "failures": [], "status": "not_supplied"}
    )
    funnel_gate = (
        calculate_funnel_metrics(context["funnel_input"])
        if context.get("funnel_input") is not None
        else {"passed": True, "failures": [], "status": "not_supplied"}
    )
    event_gate = (
        analyze_event_cutoffs(context["event_input"])
        if context.get("event_input") is not None
        else {"passed": True, "failures": [], "status": "not_supplied"}
    )
    sensitivity_gate = validate_stage_sensitivity_bindings(payload)
    movement_gate = validate_movement_input(payload)
    user_output_gate = (
        lint_user_visible({
            "text": context.get("user_visible_text"),
            "delivery_tier": context.get("delivery_tier", "direct"),
            "completion_evidence": context.get("completion_evidence") or [],
        })
        if context.get("user_visible_text") is not None
        else {"passed": True, "failures": [], "status": "not_supplied"}
    )
    if permission_gate["denied"] or permission_gate["failures"]:
        state = "stopped"
    elif permission_gate["confirmation_required"]:
        state = "confirmation_required"
    elif (
        not claim_gate["passed"]
        or not permission_gate["passed"]
        or not artifact_gate["passed"]
        or not action_gate["passed"]
        or not account_gate["passed"]
        or not channel_gate["passed"]
        or not funnel_gate["passed"]
        or not event_gate["passed"]
        or not sensitivity_gate["passed"]
        or not movement_gate["passed"]
        or not user_output_gate["passed"]
        or claim_gate["unknown_count"]
    ):
        state = "degraded"
    else:
        state = "ready"
    return {
        "claim_gate": claim_gate,
        "artifact_gate": artifact_gate,
        "permission_gate": permission_gate,
        "action_gate": action_gate,
        "account_gate": account_gate,
        "channel_gate": channel_gate,
        "funnel_gate": funnel_gate,
        "event_gate": event_gate,
        "sensitivity_gate": sensitivity_gate,
        "movement_gate": movement_gate,
        "user_output_gate": user_output_gate,
        "artifact_state": state,
    }


def normalize_snapshot(rows: Any, currency: Any, label: str) -> Tuple[List[dict], List[dict], List[str]]:
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be a list")
    audit: List[dict] = []
    usable: List[dict] = []
    seen = set()
    duplicate_ids: List[str] = []
    for index, row in enumerate(rows):
        opportunity_id = row.get("opportunity_id")
        amount = decimal_or_none(row.get("amount"))
        stage = row.get("stage")
        row_currency = row.get("currency")
        reasons = []
        if not opportunity_id:
            reasons.append("missing_opportunity_id")
        if amount is None:
            reasons.append("missing_or_invalid_amount")
        if not stage:
            reasons.append("missing_stage")
        if currency is None or row_currency != currency:
            reasons.append("currency_mismatch_or_missing")
        duplicate = bool(opportunity_id and opportunity_id in seen)
        if duplicate:
            duplicate_ids.append(str(opportunity_id))
            reasons.append("duplicate_opportunity_id")
        if opportunity_id:
            seen.add(opportunity_id)
        normalized = {
            "row_index": index,
            "opportunity_id": opportunity_id,
            "stage": stage,
            "amount": None if amount is None else number(amount),
            "currency": row_currency,
            "status": "unknown" if reasons else "usable",
            "reasons": reasons,
        }
        audit.append(normalized)
        if not reasons:
            usable.append(normalized)
    return audit, usable, duplicate_ids


def validate_stage_sensitivity_bindings(payload: dict) -> dict:
    """Bind every sensitivity calculation to the authoritative current snapshot amount."""
    items = payload.get("stage_sensitivity")
    if not items:
        return {"passed": True, "failures": [], "results": {}, "status": "not_supplied"}
    if not isinstance(items, list):
        return {"passed": False, "failures": ["stage_sensitivity must be a list"], "results": {}}
    try:
        _, current, duplicate_ids = normalize_snapshot(
            payload.get("current_snapshot"), payload.get("currency"), "current_snapshot"
        )
    except ValueError as exc:
        return {"passed": False, "failures": [str(exc)], "results": {}}
    current_by_id = {row["opportunity_id"]: row for row in current}
    failures: List[str] = []
    results: Dict[str, dict] = {}
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            failures.append(f"stage_sensitivity[{index}] must be an object")
            continue
        opportunity_id = item.get("opportunity_id")
        if not opportunity_id or opportunity_id in seen:
            failures.append(f"stage_sensitivity[{index}] missing or duplicate opportunity_id")
            continue
        seen.add(opportunity_id)
        snapshot = current_by_id.get(opportunity_id)
        if snapshot is None or opportunity_id in duplicate_ids:
            failures.append(f"stage_sensitivity[{index}] opportunity is not a usable current-snapshot row")
            results[str(opportunity_id)] = {
                "passed": False,
                "failures": ["opportunity_not_in_usable_current_snapshot"],
            }
            continue
        snapshot_amount = Decimal(str(snapshot["amount"]))
        supplied_amount = decimal_or_none(item.get("amount"))
        row_failures = []
        if supplied_amount is not None and supplied_amount != snapshot_amount:
            row_failures.append("amount_does_not_match_current_snapshot")
        result = stage_sensitivity(
            snapshot_amount,
            item.get("candidate_stages") or [],
            payload.get("stage_probabilities") or {},
        )
        if not result["passed"]:
            row_failures.append("candidate_stages_or_probabilities_invalid")
        result.update({
            "snapshot_amount": number(snapshot_amount),
            "supplied_amount": None if supplied_amount is None else number(supplied_amount),
            "amount_source": "current_snapshot",
            "failures": row_failures,
            "passed": not row_failures,
        })
        if row_failures:
            failures.extend(f"stage_sensitivity[{index}] {failure}" for failure in row_failures)
        results[str(opportunity_id)] = result
    return {"passed": not failures, "failures": failures, "results": results}


def validate_movement_input(payload: dict) -> dict:
    prior = payload.get("prior_snapshot")
    if prior is None:
        return {"passed": True, "failures": [], "status": "not_supplied"}
    try:
        audit, _, _ = normalize_snapshot(prior, payload.get("currency"), "prior_snapshot")
    except ValueError as exc:
        return {"passed": False, "failures": [str(exc)], "status": "invalid"}
    invalid = [row for row in audit if row["status"] != "usable"]
    return {
        "passed": not invalid,
        "failures": ["prior_snapshot contains invalid or duplicate rows"] if invalid else [],
        "invalid_rows": invalid,
        "status": "valid" if not invalid else "invalid",
    }


def calculate(payload: dict, out_dir: Optional[Path] = None) -> Tuple[dict, dict]:
    currency = payload.get("currency")
    period = payload.get("period")
    amount_basis = payload.get("amount_basis")
    stage_probabilities = payload.get("stage_probabilities") or {}
    current_audit, current, duplicate_ids = normalize_snapshot(
        payload.get("current_snapshot"), currency, "current_snapshot"
    )
    prior_raw = payload.get("prior_snapshot")
    prior_audit: List[dict] = []
    prior: List[dict] = []
    if prior_raw is not None:
        prior_audit, prior, _ = normalize_snapshot(prior_raw, currency, "prior_snapshot")
    prior_input_valid = not any(row["status"] != "usable" for row in prior_audit)

    rollup: Dict[str, dict] = {}
    total = Decimal("0")
    weighted_total = Decimal("0")
    weighted_unknown_stages = []
    for row in current:
        stage = row["stage"]
        amount = Decimal(str(row["amount"]))
        bucket = rollup.setdefault(stage, {"deal_count": 0, "amount": Decimal("0"), "weighted_amount": Decimal("0"), "probability": None})
        bucket["deal_count"] += 1
        bucket["amount"] += amount
        total += amount
        probability = decimal_or_none(stage_probabilities.get(stage))
        if probability is None or probability < 0 or probability > 1:
            weighted_unknown_stages.append(stage)
        else:
            bucket["probability"] = number(probability)
            bucket["weighted_amount"] += amount * probability
            weighted_total += amount * probability

    rollup_output = {
        stage: {
            "deal_count": data["deal_count"],
            "amount": number(data["amount"]),
            "probability": data["probability"],
            "weighted_amount": None if data["probability"] is None else number(data["weighted_amount"]),
        }
        for stage, data in sorted(rollup.items())
    }
    weighted_known_total = weighted_total
    weighted_total_complete = None if weighted_unknown_stages else weighted_total
    sensitivity_gate = validate_stage_sensitivity_bindings(payload)
    sensitivity_output = sensitivity_gate["results"]

    quota = decimal_or_none(payload.get("quota"))
    forecast_metrics = {
        "known_mapped_forecast": number(weighted_known_total),
        "complete_forecast": None if weighted_total_complete is None else number(weighted_total_complete),
        "quota": None if quota is None else number(quota),
        "known_mapped_attainment": None
        if quota in (None, Decimal("0")) else float(weighted_known_total / quota),
        "known_mapped_attainment_percent": None
        if quota in (None, Decimal("0")) else float(round(weighted_known_total / quota * 100, 1)),
        "known_mapped_gap": None if quota is None else number(quota - weighted_known_total),
    }

    prior_by_id = {row["opportunity_id"]: row for row in prior}
    movement_rows = []
    if prior_raw is not None and prior_input_valid:
        for row in current:
            before = prior_by_id.get(row["opportunity_id"])
            if before is None:
                movement_rows.append({"opportunity_id": row["opportunity_id"], "movement": "new_in_current", "amount_delta": None, "stage_from": None, "stage_to": row["stage"]})
            else:
                movement_rows.append(
                    {
                        "opportunity_id": row["opportunity_id"],
                        "movement": "changed" if before["stage"] != row["stage"] or before["amount"] != row["amount"] else "unchanged",
                        "amount_delta": number(Decimal(str(row["amount"])) - Decimal(str(before["amount"]))),
                        "stage_from": before["stage"],
                        "stage_to": row["stage"],
                    }
                )
        current_ids = {row["opportunity_id"] for row in current}
        for row in prior:
            if row["opportunity_id"] not in current_ids:
                movement_rows.append({"opportunity_id": row["opportunity_id"], "movement": "missing_from_current", "amount_delta": None, "stage_from": row["stage"], "stage_to": None})

    sorted_current = sorted(current, key=lambda row: Decimal(str(row["amount"])), reverse=True)
    concentration_rows = [
        {
            "opportunity_id": row["opportunity_id"],
            "amount": row["amount"],
            "share": None if total == 0 else float(Decimal(str(row["amount"])) / total),
        }
        for row in sorted_current
    ]
    largest = Decimal(str(sorted_current[0]["amount"])) if sorted_current else Decimal("0")
    shares = [Decimal(str(row["share"])) for row in concentration_rows if row["share"] is not None]
    top1_share = shares[0] if shares else None
    top2_share = sum(shares[:2], Decimal("0")) if shares else None
    hhi = sum((share * share for share in shares), Decimal("0")) if shares else None
    conservation = {
        "input_count": len(payload.get("current_snapshot") or []),
        "row_audit_count": len(current_audit),
        "usable_count": len(current),
        "unknown_or_duplicate_count": sum(row["status"] != "usable" for row in current_audit),
        "passed": len(payload.get("current_snapshot") or []) == len(current_audit),
    }
    unknowns = [
        {"row_index": row["row_index"], "opportunity_id": row["opportunity_id"], "reasons": row["reasons"]}
        for row in current_audit
        if row["status"] != "usable"
    ]
    if prior_raw is None:
        unknowns.append({"field": "prior_snapshot", "reason": "movement_not_evaluated"})
    elif not prior_input_valid:
        unknowns.append({"field": "prior_snapshot", "reason": "movement_not_evaluated_invalid_prior_rows"})
    if not sensitivity_gate["passed"]:
        unknowns.append({
            "field": "stage_sensitivity",
            "reason": "sensitivity_not_bound_to_current_snapshot",
            "failures": sensitivity_gate["failures"],
        })
    if weighted_unknown_stages:
        unknowns.append({"field": "stage_probabilities", "reason": "probability_missing_or_out_of_range_0_1", "stages": sorted(set(weighted_unknown_stages))})
    if payload.get("derive_fiscal_quarter") and not payload.get("fiscal_calendar"):
        unknowns.append({"field": "fiscal_calendar", "reason": "quarter_assignment_not_evaluated"})
    for field, value in (("currency", currency), ("period", period), ("amount_basis", amount_basis)):
        if not value:
            unknowns.append({"field": field, "reason": "required_metadata_missing"})

    claim_gate = evaluate_claims(payload.get("claims"))
    action_gate = validate_crm_actions((payload.get("gate_context") or {}).get("proposed_actions"))
    permission_gate = evaluate_permissions(
        (payload.get("gate_context") or {}).get("permission_requests")
    )
    if permission_gate["denied"] or permission_gate["failures"]:
        base_state = "stopped"
    elif permission_gate["confirmation_required"]:
        base_state = "confirmation_required"
    elif not claim_gate["passed"] or not action_gate["passed"] or claim_gate["unknown_count"] or unknowns:
        base_state = "degraded"
    else:
        base_state = "ready"
    counts = {
        "records": len(current_audit),
        "claims": len(payload.get("claims") or []),
        "unknowns": len(unknowns),
    }
    manifest = {
        "artifact_state": base_state,
        "counts": counts,
        "required_artifacts": sorted(REQUIRED_ARTIFACTS),
    }
    paths = {
        "forecast_full_json": str(out_dir / "pipeline-forecast.full.json") if out_dir else None,
        "forecast_compact_json": str(out_dir / "pipeline-forecast.compact.json") if out_dir else None,
        "forecast_final_json": str(out_dir / "pipeline-forecast.final.json") if out_dir else None,
        "claim_ledger": str(out_dir / "claim-ledger.json") if out_dir else None,
    }
    full_file = {
        "artifact_name": "forecast_full_json",
        "manifest": manifest,
        "schema_version": SCHEMA_VERSION,
        "tool": "pipeline_forecast",
        "currency": currency,
        "period": period,
        "amount_basis": amount_basis,
        "formulas": {
            "stage_rollup": "sum(amount) grouped by stage",
            "weighted_amount": "sum(amount * user_or_org_stage_probability)",
            "concentration_share": "opportunity_amount / total_amount",
            "amount_ex_largest": "total_amount - largest_opportunity_amount",
            "hhi": "sum(opportunity_share ^ 2)",
            "known_mapped_attainment": "known_mapped_forecast / quota",
            "known_mapped_gap": "quota - known_mapped_forecast",
        },
        "current_row_audit": current_audit,
        "prior_row_audit": prior_audit,
        "rollup": rollup_output,
        "total_amount": number(total),
        "weighted_known_total": number(weighted_known_total),
        "weighted_total": None if weighted_total_complete is None else number(weighted_total_complete),
        "forecast_metrics": forecast_metrics,
        "stage_sensitivity": sensitivity_output,
        "movement": {
            "status": (
                "not_evaluated" if prior_raw is None
                else "not_evaluated_invalid_prior" if not prior_input_valid
                else "evaluated"
            ),
            "rows": movement_rows,
        },
        "concentration": {
            "rows": concentration_rows,
            "largest_amount": number(largest),
            "amount_ex_largest": number(total - largest),
            "top1_share": None if top1_share is None else float(top1_share),
            "top2_share": None if top2_share is None else float(top2_share),
            "hhi": None if hhi is None else float(hhi),
        },
        "set_conservation": conservation,
        "unknowns": unknowns,
        "claims": payload.get("claims") or [],
        "artifact_paths": paths,
    }
    compact_file = {
        "artifact_name": "forecast_compact_json",
        "manifest": manifest,
        "schema_version": SCHEMA_VERSION,
        "tool": "pipeline_forecast",
        "artifact_state": base_state,
        "core_results": {
            "total_amount": number(total),
            "weighted_known_total": number(weighted_known_total),
            "weighted_total": None if weighted_total_complete is None else number(weighted_total_complete),
            "forecast_metrics": forecast_metrics,
            "stage_sensitivity": sensitivity_output,
            "rollup": rollup_output,
            "movement_status": full_file["movement"]["status"],
            "largest_amount": number(largest),
            "amount_ex_largest": number(total - largest),
            "top1_share": full_file["concentration"]["top1_share"],
            "top2_share": full_file["concentration"]["top2_share"],
            "hhi": full_file["concentration"]["hhi"],
            "set_conservation": conservation,
        },
        "unknowns": unknowns,
        "source_index": sorted({source for claim in payload.get("claims") or [] for source in claim.get("source_ids", [])}),
        "full_artifact_path": paths["forecast_full_json"],
    }
    ledger_file = {
        "artifact_name": "claim_ledger",
        "manifest": manifest,
        "schema_version": SCHEMA_VERSION,
        "claims": payload.get("claims") or [],
    }

    def persist_artifacts() -> List[dict]:
        if not out_dir:
            return []
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json(Path(paths["forecast_full_json"]), full_file)
        full_hash = file_sha256(Path(paths["forecast_full_json"]))
        compact_file["full_sha256"] = full_hash
        write_json(Path(paths["forecast_compact_json"]), compact_file)
        compact_hash = file_sha256(Path(paths["forecast_compact_json"]))
        write_json(Path(paths["claim_ledger"]), ledger_file)
        ledger_hash = file_sha256(Path(paths["claim_ledger"]))
        final_file = {
            "artifact_name": "forecast_final_json",
            "manifest": manifest,
            "schema_version": SCHEMA_VERSION,
            "core_results": compact_file["core_results"],
            "input_artifact_hashes": {
                "forecast_full_json": full_hash,
                "forecast_compact_json": compact_hash,
                "claim_ledger": ledger_hash,
            },
        }
        write_json(Path(paths["forecast_final_json"]), final_file)
        persisted = []
        for name, path in paths.items():
            persisted.append({
                "artifact_name": name,
                "path": path,
                "expected_sha256": file_sha256(Path(path)),
            })
        return persisted

    receipts = persist_artifacts()
    gates = run_gates(payload, receipts)
    if unknowns and gates["artifact_state"] == "ready":
        gates["artifact_state"] = "degraded"
    final_state = gates["artifact_state"]
    manifest["artifact_state"] = final_state
    compact_file["artifact_state"] = final_state
    if out_dir:
        receipts = persist_artifacts()
        gates = run_gates(payload, receipts)
        if unknowns and gates["artifact_state"] == "ready":
            gates["artifact_state"] = "degraded"
        final_state = gates["artifact_state"]
        manifest["artifact_state"] = final_state
        compact_file["artifact_state"] = final_state
        receipts = persist_artifacts()
    full = dict(
        full_file,
        gates=gates,
        artifact_receipts=receipts,
        sha256=next((item["expected_sha256"] for item in receipts if item["artifact_name"] == "forecast_full_json"), None),
    )
    compact = dict(
        compact_file,
        hard_gates=gates,
        artifact_receipts=receipts,
        full_sha256=next((item["expected_sha256"] for item in receipts if item["artifact_name"] == "forecast_full_json"), None),
    )
    return full, compact


def _normalized_numeric_values(values: Any) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        parsed = decimal_or_none(value)
        if parsed is not None:
            normalized.add(str(parsed.normalize()))
    return normalized


def _numbers_in_text(text: str) -> set[str]:
    tokens = re.findall(r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d+)?%?", text or "")
    return _normalized_numeric_values(token.replace(",", "").rstrip("%") for token in tokens)


def finalize(payload: dict) -> dict:
    approved = payload.get("approved_context") or {}
    candidate = payload.get("candidate") or {}
    approved_claim_gate = evaluate_claims(approved.get("claims"))
    candidate_claim_gate = evaluate_claims(candidate.get("claims"))
    checks = {}
    for key in ("source_ids", "object_ids", "numeric_values"):
        allowed = set(approved.get(key) or [])
        used = set(candidate.get(key) or [])
        checks[key] = {"extra": sorted(used - allowed), "passed": used <= allowed}
    approved_claims = {
        claim["claim_id"]: claim for claim in approved.get("claims") or []
        if isinstance(claim, dict) and "claim_id" in claim
    }
    candidate_claims = {
        claim["claim_id"]: claim for claim in candidate.get("claims") or []
        if isinstance(claim, dict) and "claim_id" in claim
    }
    approved_claim_ids = set(approved_claims)
    candidate_claim_ids = set(candidate_claims)
    checks["claim_ids"] = {
        "extra": sorted(candidate_claim_ids - approved_claim_ids),
        "passed": candidate_claim_ids <= approved_claim_ids,
    }
    changed_claims = sorted(
        claim_id for claim_id in candidate_claim_ids & approved_claim_ids
        if canonical(candidate_claims[claim_id]) != canonical(approved_claims[claim_id])
    )
    checks["claim_content"] = {"changed": changed_claims, "passed": not changed_claims}
    user_visible_text = str(candidate.get("user_visible_text") or "")
    visible_numbers = _numbers_in_text(user_visible_text)
    declared_numbers = _normalized_numeric_values(candidate.get("numeric_values"))
    approved_numbers = _normalized_numeric_values(approved.get("numeric_values"))
    undeclared_numbers = sorted(visible_numbers - declared_numbers)
    unapproved_visible_numbers = sorted(visible_numbers - approved_numbers)
    checks["user_visible_numeric_values"] = {
        "undeclared": undeclared_numbers,
        "unapproved": unapproved_visible_numbers,
        "passed": not undeclared_numbers and not unapproved_visible_numbers,
    }
    user_output_gate = lint_user_visible({
        "text": user_visible_text,
        "delivery_tier": candidate.get("delivery_tier", "direct"),
        "completion_evidence": candidate.get("completion_evidence") or [],
    })
    action_gate = validate_crm_actions(candidate.get("actions"))
    accepted = (
        approved_claim_gate["passed"]
        and candidate_claim_gate["passed"]
        and all(item["passed"] for item in checks.values())
        and user_output_gate["passed"]
        and action_gate["passed"]
    )
    return {
        "status": "finalized" if accepted else "rejected_source_lock",
        "accepted": accepted,
        "schema_validation": {
            "approved_claims": approved_claim_gate,
            "candidate_claims": candidate_claim_gate,
        },
        "checks": checks,
        "user_output_gate": user_output_gate,
        "action_gate": action_gate,
        "candidate": candidate if accepted else None,
    }


def load_payload(args: argparse.Namespace) -> dict:
    if args.input_json:
        return json.loads(args.input_json)
    if args.input_file:
        return json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    raise ValueError("one of --input-json or --input-file is required")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--operation",
        choices=["calculate", "gate", "finalize", "lint", "prioritize", "channel-plan", "funnel", "events"],
        default="calculate",
    )
    parser.add_argument("--input-json")
    parser.add_argument("--input-file")
    parser.add_argument("--out-dir")
    args = parser.parse_args()
    try:
        payload = load_payload(args)
        if args.operation == "calculate":
            full, compact = calculate(payload, Path(args.out_dir) if args.out_dir else None)
            output = {"status": "ok", "full": full, "compact": compact}
        elif args.operation == "gate":
            output = {"status": "ok", "gates": run_gates(payload)}
        elif args.operation == "finalize":
            output = finalize(payload)
        elif args.operation == "lint":
            output = {"status": "ok", "user_output_gate": lint_user_visible(payload)}
        elif args.operation == "prioritize":
            output = {"status": "ok", "account_actions": prioritize_accounts(payload)}
        elif args.operation == "channel-plan":
            output = {"status": "ok", "channel_plan": validate_channel_plan(payload)}
        elif args.operation == "funnel":
            output = {"status": "ok", "funnel": calculate_funnel_metrics(payload)}
        else:
            output = {"status": "ok", "events": analyze_event_cutoffs(payload)}
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        output = {"status": "error", "error": str(exc)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("status") != "error" else 2


if __name__ == "__main__":
    sys.exit(main())
