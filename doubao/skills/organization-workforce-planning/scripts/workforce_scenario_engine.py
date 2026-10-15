#!/usr/bin/env python3
"""Decimal workforce scenario engine with validation, privacy, and source locking."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA = "workforce-1.1"
FULL_ARTIFACT = "organization-workforce-plan.full.json"
COMPACT_ARTIFACT = "organization-workforce-plan.compact.json"
STATES = {"ready", "degraded", "intake_required", "confirmation_required", "routed", "stopped"}
INTERNAL = re.compile(r"DETERMINISTIC TOOL OUTPUT|search-evidence\.json|system prompt", re.I)
USER_VISIBLE_INTERNAL = re.compile(
    r"SKILL\.md|scripts/[^\s]+\.py|artifact_state|delivery_tier|selected_skill|"
    r"compact_payload_sha256|organization-workforce-plan\.(?:full|compact)\.json",
    re.I,
)
PROCESS_LEAK = re.compile(
    r"(?:我先|我将|接下来(?:我)?|正在).{0,32}(?:读取|解压|运行脚本|调用工具|调试|修复报错)",
    re.I,
)
SENSITIVE_EXACT = {
    "employee_name", "candidate_name", "full_name", "email", "email_address", "phone",
    "phone_number", "mobile", "national_id", "id_card", "passport", "health_data",
    "medical_history", "protected_attribute", "gender", "sex", "age", "marital_status",
    "family_status", "family_burden", "pregnancy", "disability", "ethnicity", "race",
    "religion", "hukou", "household_registration",
}
SENSITIVE_CN = (
    "姓名", "邮箱", "电话", "手机号", "身份证", "护照", "健康", "病史", "性别", "年龄",
    "婚姻", "婚育", "家庭负担", "家庭状况", "怀孕", "残障", "民族", "宗教", "户籍",
)
SMALL_GROUP_COUNT_KEYS = ("group_count", "member_count", "sample_size", "population_count")
SMALL_GROUP_SAFE_KEYS = {
    "group_id", "group", "team", "role_id", "role", "department", "unit", "source_ids",
    "assumption_ids", "group_count", "member_count", "sample_size", "population_count",
    "suppressed", "suppression_reason",
}
ROUTE_KEYS = {"selected_skill", "intent", "route_status"}
INTAKE_KEYS = {"planning_period_and_org_scope", "business_goal_or_capability_demand", "current_org_role_reporting_baseline", "comparable_scenario_input"}
CAPABILITY_KEYS = {"allowed", "missing", "blocked_slots"}
SECTIONS = {
    "schema_version", "artifact_type", "artifact_state", "delivery_tier", "search_mode", "route", "intake", "capabilities", "frozen_scope",
    "claim_ledger", "baseline", "capability_demand", "currency", "period", "tolerance",
    "privacy_policy",
    "scenarios", "cost_bridge", "structure_options", "transition_route", "risks_and_counterpoints",
    "action_previews", "limitations", "next_steps", "artifact_index", "errors", "unknowns",
    "counts", "hard_gates", "formula_metadata",
}


def decimal(value: Any, field: str, non_negative: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if non_negative and result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def optional_decimal(value: Any, field: str, non_negative: bool = False) -> Decimal | None:
    if value is None or value == "":
        return None
    return decimal(value, field, non_negative)


def text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def dump(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    if normalized in SENSITIVE_EXACT:
        return True
    tokens = set(normalized.split("_"))
    if tokens & {"gender", "sex", "age", "pregnancy", "disability", "ethnicity", "race", "religion", "hukou"}:
        return True
    if "name" in tokens and tokens & {"employee", "candidate", "person", "staff", "worker", "manager"}:
        return True
    return any(token in key for token in SENSITIVE_CN)


def _small_group_count(value: dict[str, Any]) -> int | None:
    for key in SMALL_GROUP_COUNT_KEYS:
        if key not in value:
            continue
        try:
            parsed = int(value[key])
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be an integer")
        if parsed < 0:
            raise ValueError(f"{key} must be non-negative")
        return parsed
    return None


def privacy_scan(
    value: Any,
    minimum_group_size: int | None = None,
    path: tuple[str, ...] = (),
) -> tuple[Any, list[str]]:
    findings: list[str] = []
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            child_path = path + (str(key),)
            if _is_sensitive_key(key):
                findings.append("protected_field:" + ".".join(child_path))
                continue
            child, child_findings = privacy_scan(item, minimum_group_size, child_path)
            clean[key] = child
            findings.extend(child_findings)
        count = _small_group_count(clean)
        already_suppressed = clean.get("suppressed") is True and clean.get("suppression_reason") == "below_user_minimum_group_size"
        if minimum_group_size is not None and count is not None and count < minimum_group_size and already_suppressed:
            exposed = False
            for key, item in clean.items():
                if key in SMALL_GROUP_SAFE_KEYS:
                    continue
                if isinstance(item, dict):
                    exposed = exposed or any(metric is not None for metric in item.values())
                elif isinstance(item, (list, tuple)):
                    exposed = exposed or bool(item)
                else:
                    exposed = exposed or item is not None
            if exposed:
                findings.append("small_group_unsuppressed:" + (".".join(path) or "root"))
        elif minimum_group_size is not None and count is not None and count < minimum_group_size:
            for key in list(clean):
                if key in SMALL_GROUP_SAFE_KEYS:
                    continue
                item = clean[key]
                if isinstance(item, dict):
                    clean[key] = {metric: None for metric in item}
                elif not isinstance(item, (list, tuple)):
                    clean[key] = None
            clean["suppressed"] = True
            clean["suppression_reason"] = "below_user_minimum_group_size"
            findings.append("small_group:" + (".".join(path) or "root"))
        return clean, sorted(set(findings))
    if isinstance(value, list):
        clean = []
        for index, item in enumerate(value):
            child, child_findings = privacy_scan(item, minimum_group_size, path + (str(index),))
            clean.append(child)
            findings.extend(child_findings)
        return clean, sorted(set(findings))
    return value, findings


def _minimum_group_size(payload: dict[str, Any]) -> int | None:
    policy = payload.get("privacy_policy")
    if policy is None:
        return None
    if not isinstance(policy, dict):
        raise ValueError("privacy_policy must be an object")
    minimum = policy.get("minimum_group_size")
    if minimum is None:
        return None
    try:
        parsed = int(minimum)
    except (TypeError, ValueError) as exc:
        raise ValueError("minimum_group_size must be an integer") from exc
    if parsed <= 0:
        raise ValueError("minimum_group_size must be positive")
    return parsed


def _append_unknown(
    unknowns: list[dict[str, Any]],
    unknown_id: str,
    field: str,
    impact_slots: list[str],
    next_evidence: str,
    decision_change: str,
    **extra: Any,
) -> None:
    if any(item.get("unknown_id") == unknown_id for item in unknowns if isinstance(item, dict)):
        return
    unknowns.append({
        "unknown_id": unknown_id,
        "field": field,
        "state": "unknown",
        "impact_slots": impact_slots,
        "next_evidence": next_evidence,
        "decision_change": decision_change,
        **extra,
    })


def _derive_state(
    route: dict[str, Any],
    intake: dict[str, Any],
    capabilities: dict[str, Any],
    errors: list[Any],
    unknowns: list[Any],
    scenario_count: int,
) -> str:
    if route["selected_skill"] != "organization-workforce-planning" or route["route_status"] != "selected":
        return "routed"
    if not all(intake.get(key) for key in INTAKE_KEYS):
        return "intake_required"
    if capabilities["missing"] or [slot for slot in capabilities["blocked_slots"] if slot != "execution"]:
        return "degraded"
    if errors or unknowns or scenario_count == 0:
        return "degraded"
    return "ready"


def strict_mapping(value: Any, keys: set[str], name: str, list_values: bool = False, allow_none: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"malformed {name} schema")
    if list_values:
        if any(not isinstance(value[key], list) for key in keys):
            raise ValueError(f"malformed {name} schema")
    elif any(not isinstance(value[key], (str, dict)) and not (allow_none and value[key] is None) for key in keys):
        raise ValueError(f"malformed {name} schema")
    return value


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    route = strict_mapping(payload.get("route"), ROUTE_KEYS, "route")
    intake = strict_mapping(payload.get("intake"), INTAKE_KEYS, "intake", allow_none=True)
    capabilities = strict_mapping(payload.get("capabilities"), CAPABILITY_KEYS, "capabilities", True)
    currency, period = payload.get("currency"), payload.get("period")
    tolerance = decimal(payload.get("tolerance", "0.01"), "tolerance", True)
    errors: list[str] = []
    if not isinstance(payload.get("unknowns", []), list):
        raise ValueError("unknowns must be a list")
    unknowns: list[dict[str, Any]] = copy.deepcopy(payload.get("unknowns", []))
    for index, item in enumerate(unknowns):
        if not isinstance(item, dict):
            raise ValueError("unknown item must be an object")
        item.setdefault("unknown_id", f"unknown-input-{index + 1}")
        item.setdefault("field", "unspecified_input")
        item.setdefault("state", "unknown")
        item.setdefault("impact_slots", [])
        item.setdefault("next_evidence", "补充该未知项的来源、口径与负责人")
        item.setdefault("decision_change", "确认该未知项是否改变当前情景结论")
    missing_planning_inputs = {
        "capability_map": {
            "impact_slots": ["capability_demand", "structure_options"],
            "next_evidence": "细分能力项、当前覆盖与目标覆盖",
            "decision_change": "决定各情景能覆盖哪些能力及仍需补哪些岗位能力",
        },
        "workload_forecast": {
            "impact_slots": ["capability_demand", "structure_options"],
            "next_evidence": "按业务活动拆分的工作量、服务量或容量驱动",
            "decision_change": "把方向性能力需求升级为工作量—容量—岗位数量关系",
        },
        "structure_baseline": {
            "impact_slots": ["structure_options", "transition_route"],
            "next_evidence": "岗位序列、团队边界、接口与当前汇报线",
            "decision_change": "允许形成组织结构选项；补齐前只给情景支持选项，不推断汇报线",
        },
        "hc_flow_breakdown": {
            "impact_slots": ["cost_bridge", "scenarios"],
            "next_evidence": "招聘、离职、调入、调出分项及口径",
            "decision_change": "把净增量桥升级为完整期初—流量—期末 HC 桥",
        },
    }
    for field, detail in missing_planning_inputs.items():
        if not payload.get(field):
            _append_unknown(unknowns, f"unknown-{field}", field, **detail)
    raw_scenarios = payload.get("scenarios", [])
    if not isinstance(raw_scenarios, list):
        raise ValueError("scenarios must be a list")
    if not raw_scenarios:
        _append_unknown(
            unknowns,
            "unknown-scenarios",
            "scenarios",
            ["scenarios", "cost_bridge", "structure_options"],
            "至少一个带基线、角色净增、来源和假设的情景输入",
            "允许计算 HC 与成本桥；完整方案通常还需至少两个同口径可比较情景",
        )
    seen: set[str] = set()
    scenarios = []
    flow_inputs = payload.get("hc_flow_breakdown", {})
    if flow_inputs is not None and not isinstance(flow_inputs, dict):
        raise ValueError("hc_flow_breakdown must be an object keyed by scenario_id")
    for raw in raw_scenarios:
        if not isinstance(raw, dict):
            raise ValueError("scenario must be an object")
        scenario_id = raw.get("scenario_id")
        if not scenario_id:
            raise ValueError("scenario_id is required")
        if scenario_id in seen:
            raise ValueError(f"duplicate scenario_id: {scenario_id}")
        seen.add(scenario_id)
        baseline = decimal(raw.get("baseline_hc"), "baseline_hc", True)
        source_ids = raw.get("source_ids", [])
        assumption_ids = raw.get("assumption_ids", [])
        if not source_ids or not assumption_ids:
            raise ValueError("scenario source_ids and assumption_ids are required")
        delta_total = Decimal("0")
        recurring = Decimal("0")
        one_time = Decimal("0")
        recurring_unknown = not currency or not period
        one_time_unknown = not currency or not period
        role_rows = []
        role_deltas = raw.get("role_deltas", [])
        if not isinstance(role_deltas, list):
            raise ValueError("role_deltas must be a list")
        for item in role_deltas:
            if not isinstance(item, dict) or not item.get("role_id"):
                raise ValueError("role delta must be an object with role_id")
            delta = decimal(item.get("hc_delta"), "hc_delta")
            unit = optional_decimal(item.get("recurring_unit_cost"), "recurring_unit_cost", True)
            setup = optional_decimal(item.get("one_time_unit_cost"), "one_time_unit_cost", True)
            delta_total += delta
            if unit is None:
                recurring_unknown = True
            else:
                recurring += delta * unit
            if delta > 0 and setup is None:
                one_time_unknown = True
            elif setup is not None:
                one_time += max(delta, Decimal("0")) * setup
            role_rows.append({
                "role_id": item.get("role_id"), "hc_delta": text(delta),
                "recurring_unit_cost": None if unit is None else text(unit),
                "one_time_unit_cost": None if setup is None else text(setup),
                "source_ids": item.get("source_ids", source_ids), "assumption_ids": item.get("assumption_ids", assumption_ids),
            })
            role_sources = set(role_rows[-1]["source_ids"])
            role_assumptions = set(role_rows[-1]["assumption_ids"])
            if not role_sources or not role_assumptions or not role_sources <= set(source_ids) or not role_assumptions <= set(assumption_ids):
                raise ValueError("role source/assumption ids must be non-empty scenario subsets")
        ending = baseline + delta_total
        if ending < 0:
            raise ValueError(f"negative ending_hc: {scenario_id}")
        if recurring_unknown:
            _append_unknown(
                unknowns,
                f"unknown-{scenario_id}-recurring-cost",
                "recurring_unit_cost",
                ["cost_bridge", "scenarios", "structure_options"],
                "该情景所有角色的经常性单位成本、币种与期间口径",
                "允许复算并比较该情景的经常性成本；补齐前只保留 HC 结论",
                scenario_id=scenario_id,
            )
        if one_time_unknown:
            _append_unknown(
                unknowns,
                f"unknown-{scenario_id}-one-time-cost",
                "one_time_unit_cost",
                ["cost_bridge", "scenarios", "structure_options"],
                "该情景正向 HC 变动的一次性单位投入、币种与期间口径",
                "允许复算首期投入；补齐前不得把未知成本写成 0",
                scenario_id=scenario_id,
            )
        flow = flow_inputs.get(scenario_id) if flow_inputs else None
        if flow:
            required_flows = {"hires", "exits", "transfers_in", "transfers_out"}
            if not isinstance(flow, dict) or not required_flows <= set(flow):
                raise ValueError(f"malformed HC flow breakdown: {scenario_id}")
            flow_values = {key: decimal(flow[key], f"{scenario_id}.{key}", True) for key in required_flows}
            flow_net = flow_values["hires"] - flow_values["exits"] + flow_values["transfers_in"] - flow_values["transfers_out"]
            if abs(flow_net - delta_total) > tolerance:
                raise ValueError(f"HC flow does not reconcile to net delta: {scenario_id}")
            hc_bridge = {
                "opening_hc": text(baseline), "hires": text(flow_values["hires"]), "exits": text(flow_values["exits"]),
                "transfers_in": text(flow_values["transfers_in"]), "transfers_out": text(flow_values["transfers_out"]),
                "net_delta": text(flow_net), "ending_hc": text(ending), "complete_flow_bridge": True, "unknown_ids": [],
            }
        else:
            _append_unknown(
                unknowns,
                "unknown-hc_flow_breakdown",
                "hc_flow_breakdown",
                ["cost_bridge", "scenarios"],
                "招聘、离职、调入、调出分项及口径",
                "把净增量桥升级为完整期初—流量—期末 HC 桥",
            )
            hc_bridge = {
                "opening_hc": text(baseline), "hires": None, "exits": None,
                "transfers_in": None, "transfers_out": None,
                "net_delta": text(delta_total), "ending_hc": text(ending),
                "complete_flow_bridge": False, "unknown_ids": ["unknown-hc_flow_breakdown"],
            }
        scenarios.append({
            "scenario_id": scenario_id, "baseline_hc": text(baseline), "role_deltas": role_rows,
            "hc_delta": text(delta_total), "ending_hc": text(ending),
            "recurring_cost_delta": None if recurring_unknown else text(recurring),
            "one_time_cost": None if one_time_unknown else text(one_time),
            "currency": currency, "period": period, "source_ids": source_ids, "assumption_ids": assumption_ids,
            "hc_bridge": hc_bridge,
        })
    minimum_group_size = _minimum_group_size(payload)
    clean, privacy_findings = privacy_scan(payload, minimum_group_size)
    if privacy_findings:
        _append_unknown(
            unknowns,
            "unknown-privacy-redaction",
            "privacy_or_small_group_detail",
            ["baseline", "capability_demand", "structure_options"],
            "经授权的聚合字段、群组定义及最小群组阈值",
            "允许在不暴露受保护属性或小样本个体的前提下恢复聚合分析",
            finding_types=sorted({item.split(":", 1)[0] for item in privacy_findings}),
        )
    state = _derive_state(route, intake, capabilities, errors, unknowns, len(scenarios))
    role_ids = sorted({row["role_id"] for scenario in scenarios for row in scenario["role_deltas"] if row.get("role_id")})
    capability_map = clean.get("capability_map")
    workload = clean.get("workload_forecast")
    structure_baseline = clean.get("structure_baseline")
    capability_demand = [{
        "demand_anchor": intake["business_goal_or_capability_demand"],
        "capability_coverage": capability_map if capability_map else None,
        "workload": workload if workload else None,
        "role_dependencies": [{"role_id": role_id, "dependency": None, "state": "unknown"} for role_id in role_ids],
        "unknown_ids": [
            unknown_id for unknown_id in ("unknown-capability_map", "unknown-workload_forecast", "unknown-structure_baseline")
            if any(item.get("unknown_id") == unknown_id for item in unknowns)
        ],
    }]
    cost_bridge = [{
        "scenario_id": scenario["scenario_id"], "hc_bridge": scenario["hc_bridge"],
        "recurring_cost_delta": scenario["recurring_cost_delta"], "one_time_cost": scenario["one_time_cost"],
        "currency": currency, "period": period,
    } for scenario in scenarios]
    structure_options = []
    for scenario in scenarios:
        structure_options.append({
            "option_id": f"support-{scenario['scenario_id']}",
            "option_type": "scenario_support_option_not_org_chart",
            "basis_scenario_id": scenario["scenario_id"],
            "capability_coverage": capability_map if capability_map else {"state": "unknown", "unknown_id": "unknown-capability_map"},
            "workload_support": workload if workload else {"state": "unknown", "unknown_id": "unknown-workload_forecast"},
            "role_dependencies": [{"role_id": row["role_id"], "dependency": None, "state": "unknown"} for row in scenario["role_deltas"]],
            "hc_cost": {
                "opening_hc": scenario["baseline_hc"], "net_delta": scenario["hc_delta"], "ending_hc": scenario["ending_hc"],
                "recurring_cost_delta": scenario["recurring_cost_delta"], "one_time_cost": scenario["one_time_cost"],
                "currency": currency, "period": period,
            },
            "reversibility": "在形成不可逆人员或预算承诺前可重新选择；执行后须按正式人事与预算流程处理",
            "reporting_lines": structure_baseline.get("reporting_lines") if isinstance(structure_baseline, dict) and "reporting_lines" in structure_baseline else None,
            "risks": [
                "能力覆盖与工作量尚未闭合，HC/成本情景不能单独证明组织效果",
                "缺完整 HC 流量拆分时，净增量不等于招聘人数",
            ],
            "unknown_ids": sorted({
                item["unknown_id"] for item in unknowns
                if set(item.get("impact_slots", [])) & {"structure_options", "scenarios", "cost_bridge"}
            }),
        })
    transition_route = [
        {
            "stage": "evidence_closure", "condition": "能力地图、工作量、结构基线与 HC 流量拆分达到决策口径",
            "decision_gate": "evidence_gate", "pass_when": "关键 unknown 已关闭或被审批接受", "on_fail": "保持 degraded，不选择组织结构",
        },
        {
            "stage": "scenario_selection", "condition": "至少两套情景支持选项按同口径可比较",
            "decision_gate": "scenario_gate", "pass_when": "能力覆盖、工作量、HC 成本、可逆性与风险均有负责人确认", "on_fail": "保留并列选项",
        },
        {
            "stage": "approval_preview", "condition": "已选情景且人员、预算、合规审批输入齐全",
            "decision_gate": "approval_gate", "pass_when": "授权审批完成", "on_fail": "仅保留预览，不执行人员或预算动作",
        },
    ]
    maximum_counterpoint = {
        "type": "maximum_counterpoint",
        "statement": "现有证据只能证明 HC 与成本情景算术成立；在能力地图、工作量和结构基线缺失时，不能证明增加 HC 会改善交付，也不能推出任何汇报线方案。",
        "affected_slots": ["capability_demand", "structure_options", "transition_route"],
    }
    delivery_tier = "full" if route["intent"] == "full_package" else payload.get("delivery_tier", "direct")
    result = {
        "schema_version": SCHEMA, "artifact_type": "organization_workforce_plan_pack",
        "artifact_state": state, "delivery_tier": delivery_tier,
        "search_mode": payload.get("search_mode", "off"), "route": route, "intake": intake,
        "capabilities": capabilities, "frozen_scope": clean.get("frozen_scope", {}),
        "privacy_policy": {"minimum_group_size": minimum_group_size},
        "claim_ledger": clean.get("claim_ledger", []),
        "baseline": clean.get("baseline", {"planning_scope": intake["planning_period_and_org_scope"], "scenario_opening_hc": sorted({row["baseline_hc"] for row in scenarios})}),
        "capability_demand": capability_demand,
        "currency": currency, "period": period, "tolerance": text(tolerance),
        "scenarios": scenarios, "errors": errors, "unknowns": unknowns,
        "cost_bridge": cost_bridge, "structure_options": structure_options,
        "transition_route": transition_route,
        "risks_and_counterpoints": [maximum_counterpoint],
        "action_previews": clean.get("action_previews", []), "limitations": clean.get("limitations", []),
        "next_steps": [{
            "priority": index + 1,
            "unknown_id": item.get("unknown_id", f"unknown-input-{index + 1}"),
            "evidence": item.get("next_evidence", "补充该未知项的来源、口径与负责人"),
            "decision_change": item.get("decision_change", "确认该未知项是否改变当前情景结论"),
        } for index, item in enumerate(unknowns[:5]) if isinstance(item, dict)],
        "artifact_index": {
            "full": FULL_ARTIFACT, "compact": COMPACT_ARTIFACT,
            "artifact_type": "organization_workforce_plan_pack",
        },
        "counts": {"scenarios": len(scenarios), "unknowns": len(unknowns)},
        "hard_gates": {
            "non_negative_hc": True,
            "unique_scenario_ids": True,
            "scenarios_present": bool(scenarios),
            "privacy_minimized": not privacy_scan(clean, minimum_group_size)[1],
        },
        "formula_metadata": {
            "ending_hc": "baseline_hc + sum(role_deltas.hc_delta)",
            "hc_flow_net": "hires - exits + transfers_in - transfers_out; must equal net_delta when flow components are known",
            "recurring_cost_delta": "sum(hc_delta * recurring_unit_cost)",
            "one_time_cost": "sum(max(hc_delta,0) * one_time_unit_cost)",
            "unit": currency, "period": period, "tolerance": text(tolerance),
            "source_ids": sorted({sid for row in scenarios for sid in row["source_ids"]}),
            "assumption_ids": sorted({aid for row in scenarios for aid in row["assumption_ids"]}),
        },
    }
    return result


def compact_for(full: dict[str, Any], full_name: str, digest: str) -> dict[str, Any]:
    compact = {
        "schema_version": SCHEMA, "artifact_state": full["artifact_state"],
        "artifact_type": "organization_workforce_plan_pack",
        "delivery_tier": full["delivery_tier"], "search_mode": full["search_mode"], "capabilities": full["capabilities"],
        "privacy_policy": full["privacy_policy"],
        "scenario_summary": full["scenarios"], "exceptions": full["errors"], "unknowns": full["unknowns"],
        "counts": full["counts"], "hard_gates": full["hard_gates"], "formula_metadata": full["formula_metadata"],
        "source_index": full["formula_metadata"]["source_ids"],
        "core_slots": {
            "baseline": full["baseline"], "capability_demand": full["capability_demand"],
            "scenarios": full["scenarios"], "cost_bridge": full["cost_bridge"],
            "structure_options": full["structure_options"], "transition_route": full["transition_route"],
            "risks_and_counterpoints": full["risks_and_counterpoints"],
            "unknowns": full["unknowns"], "next_steps": full["next_steps"],
        },
        "artifact_index": full["artifact_index"],
        "full_artifact": FULL_ARTIFACT, "compact_artifact": COMPACT_ARTIFACT, "full_sha256": digest,
    }
    compact["compact_payload_sha256"] = hashlib.sha256(
        (json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ).hexdigest()
    return compact


def _recompute_scenario(row: dict[str, Any], tolerance: Decimal) -> dict[str, Any]:
    if not isinstance(row, dict) or not row.get("scenario_id"):
        raise ValueError("scenario row invalid")
    baseline = decimal(row.get("baseline_hc"), "baseline_hc", True)
    source_ids = row.get("source_ids")
    assumption_ids = row.get("assumption_ids")
    if (
        not isinstance(source_ids, list) or not source_ids
        or not isinstance(assumption_ids, list) or not assumption_ids
    ):
        raise ValueError("missing source/assumption ids")
    scenario_sources, scenario_assumptions = set(source_ids), set(assumption_ids)
    role_rows = row.get("role_deltas")
    if not isinstance(role_rows, list):
        raise ValueError("role_deltas must be a list")
    delta_total = Decimal("0")
    recurring_total = Decimal("0")
    one_time_total = Decimal("0")
    recurring_unknown = not row.get("currency") or not row.get("period")
    one_time_unknown = not row.get("currency") or not row.get("period")
    for role in role_rows:
        if not isinstance(role, dict) or not role.get("role_id"):
            raise ValueError("role delta must include role_id")
        delta = decimal(role.get("hc_delta"), "hc_delta")
        delta_total += delta
        unit = optional_decimal(role.get("recurring_unit_cost"), "recurring_unit_cost", True)
        setup = optional_decimal(role.get("one_time_unit_cost"), "one_time_unit_cost", True)
        if unit is None:
            recurring_unknown = True
        else:
            recurring_total += delta * unit
        if delta > 0 and setup is None:
            one_time_unknown = True
        elif setup is not None:
            one_time_total += max(delta, Decimal("0")) * setup
        role_sources = role.get("source_ids")
        role_assumptions = role.get("assumption_ids")
        if (
            not isinstance(role_sources, list) or not role_sources
            or not isinstance(role_assumptions, list) or not role_assumptions
            or not set(role_sources) <= scenario_sources
            or not set(role_assumptions) <= scenario_assumptions
        ):
            raise ValueError("role source/assumption ids must be non-empty scenario subsets")
    ending = baseline + delta_total
    if ending < 0:
        raise ValueError(f"negative ending_hc: {row['scenario_id']}")
    if row.get("hc_delta") != text(delta_total) or row.get("ending_hc") != text(ending):
        raise ValueError("scenario HC does not recompute from role_deltas")
    expected_recurring = None if recurring_unknown else text(recurring_total)
    expected_one_time = None if one_time_unknown else text(one_time_total)
    if row.get("recurring_cost_delta") != expected_recurring or row.get("one_time_cost") != expected_one_time:
        raise ValueError("scenario cost does not recompute from role_deltas")
    bridge = row.get("hc_bridge")
    if not isinstance(bridge, dict):
        raise ValueError("HC bridge missing")
    if (
        bridge.get("opening_hc") != text(baseline)
        or bridge.get("net_delta") != text(delta_total)
        or bridge.get("ending_hc") != text(ending)
    ):
        raise ValueError("HC bridge headline mismatch")
    if bridge.get("complete_flow_bridge") is True:
        flow_net = (
            decimal(bridge.get("hires"), "hires", True)
            - decimal(bridge.get("exits"), "exits", True)
            + decimal(bridge.get("transfers_in"), "transfers_in", True)
            - decimal(bridge.get("transfers_out"), "transfers_out", True)
        )
        if abs(flow_net - delta_total) > tolerance:
            raise ValueError("HC flow bridge mismatch")
    elif (
        bridge.get("complete_flow_bridge") is not False
        or any(bridge.get(key) is not None for key in ("hires", "exits", "transfers_in", "transfers_out"))
        or not bridge.get("unknown_ids")
    ):
        raise ValueError("incomplete HC flow must preserve unknown components")
    return {
        "scenario_id": row["scenario_id"],
        "hc_bridge": bridge,
        "recurring_cost_delta": expected_recurring,
        "one_time_cost": expected_one_time,
        "currency": row.get("currency"),
        "period": row.get("period"),
    }


def validate(full: dict[str, Any], compact: dict[str, Any] | None = None, full_bytes: bytes | None = None) -> None:
    missing = SECTIONS - full.keys()
    if missing:
        raise ValueError(f"missing sections: {sorted(missing)}")
    if full["schema_version"] != SCHEMA or full["artifact_state"] not in STATES:
        raise ValueError("schema or state invalid")
    if full["artifact_type"] != "organization_workforce_plan_pack":
        raise ValueError("artifact type invalid")
    if full["route"].get("intent") == "full_package" and full["delivery_tier"] != "full":
        raise ValueError("full_package must use full delivery tier")
    strict_mapping(full["route"], ROUTE_KEYS, "route")
    strict_mapping(full["intake"], INTAKE_KEYS, "intake", allow_none=True)
    strict_mapping(full["capabilities"], CAPABILITY_KEYS, "capabilities", True)
    if not isinstance(full["scenarios"], list) or not isinstance(full["unknowns"], list):
        raise ValueError("scenarios and unknowns must be lists")
    ids = [row.get("scenario_id") for row in full["scenarios"] if isinstance(row, dict)]
    if len(ids) != len(full["scenarios"]) or any(not scenario_id for scenario_id in ids):
        raise ValueError("scenario ids missing")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate scenario_id")
    unknown_ids = [item.get("unknown_id") for item in full["unknowns"] if isinstance(item, dict)]
    if len(unknown_ids) != len(full["unknowns"]) or any(not unknown_id for unknown_id in unknown_ids) or len(unknown_ids) != len(set(unknown_ids)):
        raise ValueError("unknown ids missing or duplicated")
    tolerance = decimal(full["tolerance"], "tolerance", True)
    expected_cost_bridge = []
    for row in full["scenarios"]:
        if row.get("currency") != full.get("currency") or row.get("period") != full.get("period"):
            raise ValueError("scenario cost unit or period mismatch")
        expected_cost_bridge.append(_recompute_scenario(row, tolerance))
    actual_cost_bridge = full.get("cost_bridge")
    if not isinstance(actual_cost_bridge, list) or len(actual_cost_bridge) != len(expected_cost_bridge):
        raise ValueError("cost bridge scenario coverage mismatch")
    actual_cost_ids = [item.get("scenario_id") for item in actual_cost_bridge if isinstance(item, dict)]
    if len(actual_cost_ids) != len(actual_cost_bridge) or len(actual_cost_ids) != len(set(actual_cost_ids)):
        raise ValueError("cost bridge scenario ids missing or duplicated")
    for expected in expected_cost_bridge:
        actual = next((item for item in actual_cost_bridge if item.get("scenario_id") == expected["scenario_id"]), None)
        if actual is None or any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError("cost bridge does not match recomputed scenario")
    if len(full["scenarios"]) >= 2 and len(full["structure_options"]) < 2:
        raise ValueError("two comparable scenario support options required")
    required_option_fields = {
        "option_id", "option_type", "basis_scenario_id", "capability_coverage", "workload_support",
        "role_dependencies", "hc_cost", "reversibility", "reporting_lines", "risks", "unknown_ids",
    }
    if any(not required_option_fields <= set(option) for option in full["structure_options"]):
        raise ValueError("scenario support option incomplete")
    scenario_by_id = {row["scenario_id"]: row for row in full["scenarios"]}
    for option in full["structure_options"]:
        scenario = scenario_by_id.get(option.get("basis_scenario_id"))
        if scenario is None:
            raise ValueError("structure option references unknown scenario")
        expected_hc_cost = {
            "opening_hc": scenario["baseline_hc"], "net_delta": scenario["hc_delta"],
            "ending_hc": scenario["ending_hc"], "recurring_cost_delta": scenario["recurring_cost_delta"],
            "one_time_cost": scenario["one_time_cost"], "currency": full.get("currency"), "period": full.get("period"),
        }
        if option.get("hc_cost") != expected_hc_cost:
            raise ValueError("structure option HC/cost does not match scenario")
    if any("date" in stage or "deadline" in stage for stage in full["transition_route"]):
        raise ValueError("transition route must use conditions, not invented dates")
    if not any(item.get("type") == "maximum_counterpoint" for item in full["risks_and_counterpoints"]):
        raise ValueError("maximum counterpoint missing")
    if full["counts"] != {"scenarios": len(full["scenarios"]), "unknowns": len(full["unknowns"])}:
        raise ValueError("count mismatch")
    minimum_group_size = _minimum_group_size(full)
    _, residual_privacy = privacy_scan(full, minimum_group_size)
    if residual_privacy:
        raise ValueError(f"private or protected fields remain: {residual_privacy}")
    expected_hard_gates = {
        "non_negative_hc": True,
        "unique_scenario_ids": True,
        "scenarios_present": bool(full["scenarios"]),
        "privacy_minimized": True,
    }
    if full.get("hard_gates") != expected_hard_gates:
        raise ValueError("hard gates do not match recomputed content")
    expected_state = _derive_state(
        full["route"], full["intake"], full["capabilities"], full["errors"], full["unknowns"], len(full["scenarios"])
    )
    if full["artifact_state"] in {"ready", "degraded", "intake_required", "routed"} and full["artifact_state"] != expected_state:
        raise ValueError("artifact state does not match recomputed content")
    expected_formula = {
        "ending_hc": "baseline_hc + sum(role_deltas.hc_delta)",
        "hc_flow_net": "hires - exits + transfers_in - transfers_out; must equal net_delta when flow components are known",
        "recurring_cost_delta": "sum(hc_delta * recurring_unit_cost)",
        "one_time_cost": "sum(max(hc_delta,0) * one_time_unit_cost)",
        "unit": full.get("currency"), "period": full.get("period"), "tolerance": text(tolerance),
        "source_ids": sorted({source_id for row in full["scenarios"] for source_id in row["source_ids"]}),
        "assumption_ids": sorted({assumption_id for row in full["scenarios"] for assumption_id in row["assumption_ids"]}),
    }
    if full.get("formula_metadata") != expected_formula:
        raise ValueError("formula metadata does not match recomputed content")
    if full["artifact_state"] == "ready" and not all(full["hard_gates"].values()):
        raise ValueError("ready with failed hard gate")
    if INTERNAL.search(json.dumps(full, ensure_ascii=False)):
        raise ValueError("internal protocol leakage")
    if compact is not None:
        if INTERNAL.search(json.dumps(compact, ensure_ascii=False)):
            raise ValueError("internal protocol leakage in compact")
        canonical = full_bytes or (json.dumps(full, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        expected = compact_for(full, FULL_ARTIFACT, hashlib.sha256(canonical).hexdigest())
        if compact != expected:
            raise ValueError("compact deep mismatch")
        if compact.get("artifact_state") != full["artifact_state"] or compact.get("counts") != full["counts"]:
            raise ValueError("compact/full mismatch")
        if compact.get("delivery_tier") != full["delivery_tier"] or compact.get("search_mode") != full["search_mode"] or compact.get("capabilities") != full["capabilities"]:
            raise ValueError("compact route context mismatch")
        if compact.get("source_index") != full["formula_metadata"]["source_ids"]:
            raise ValueError("source index mismatch")
        expected_core = {
            "baseline": full["baseline"], "capability_demand": full["capability_demand"],
            "scenarios": full["scenarios"], "cost_bridge": full["cost_bridge"],
            "structure_options": full["structure_options"], "transition_route": full["transition_route"],
            "risks_and_counterpoints": full["risks_and_counterpoints"],
            "unknowns": full["unknowns"], "next_steps": full["next_steps"],
        }
        if compact.get("core_slots") != expected_core or compact.get("hard_gates") != full["hard_gates"]:
            raise ValueError("compact core or hard-gate mirror mismatch")
        if full_bytes is not None and compact.get("full_sha256") != hashlib.sha256(full_bytes).hexdigest():
            raise ValueError("full hash mismatch")
        compact_payload = dict(compact)
        claimed_compact_hash = compact_payload.pop("compact_payload_sha256", None)
        actual_compact_hash = hashlib.sha256(
            (json.dumps(compact_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        ).hexdigest()
        if claimed_compact_hash != actual_compact_hash:
            raise ValueError("compact payload hash mismatch")


def _validated_claims(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    claims: dict[str, dict[str, Any]] = {}
    for claim in ledger.get("claims", []):
        claim_id, sources = claim.get("claim_id"), claim.get("source_ids")
        if (
            not isinstance(claim_id, str) or not claim_id or claim_id in claims
            or claim.get("validated") is not True
            or not isinstance(sources, list) or not sources or not all(isinstance(value, str) and value for value in sources)
            or not isinstance(claim.get("structured_value", {}), dict)
            or not isinstance(claim.get("allowed_slots", []), list)
        ):
            continue
        claims[claim_id] = claim
    return claims


def _canonical_bound_item(item: Any, claim: dict[str, Any], slot: str) -> dict[str, Any] | None:
    if not isinstance(item, dict) or item.get("claim_id") != claim["claim_id"]:
        return None
    sources = item.get("source_ids")
    if not isinstance(sources, list) or not sources or not set(sources) <= set(claim["source_ids"]):
        return None
    payload = {key: value for key, value in item.items() if key not in {"claim_id", "source_ids"}}
    structured = claim.get("structured_value", {}).get(slot)
    templates = structured if isinstance(structured, list) else ([] if structured is None else [structured])
    allowed_fields = set(claim.get("allowed_fields", {}).get(slot, []))
    for template in templates:
        if not isinstance(template, dict) or (allowed_fields and not set(template) <= allowed_fields):
            continue
        template_payload = {key: value for key, value in template.items() if key not in {"claim_id", "source_ids"}}
        if payload == template_payload:
            return {**copy.deepcopy(template_payload), "claim_id": claim["claim_id"], "source_ids": sorted(set(sources))}
    if claim.get("final_text") is not None and payload == {"text": claim["final_text"]}:
        return {"claim_id": claim["claim_id"], "source_ids": sorted(set(sources)), "text": claim["final_text"]}
    return None


def _ledger_slot(ledger: dict[str, Any], claims: dict[str, dict[str, Any]], slot: str, default: Any) -> Any:
    raw = ledger.get("structured_values", {}).get(slot, default)
    if not isinstance(raw, type(default)):
        raise ValueError(f"ledger structured_values.{slot} has wrong type")
    candidates = raw if isinstance(default, list) else ([] if not raw else [raw])
    rebuilt: list[dict[str, Any]] = []
    for item in candidates:
        claim = claims.get(item.get("claim_id")) if isinstance(item, dict) else None
        canonical = _canonical_bound_item(item, claim, slot) if claim else None
        if canonical is not None:
            rebuilt.append(canonical)
    for claim in sorted(claims.values(), key=lambda row: row["claim_id"]):
        if slot not in claim.get("allowed_slots", []):
            continue
        structured = claim.get("structured_value", {}).get(slot)
        templates = structured if isinstance(structured, list) else ([] if structured is None else [structured])
        for template in templates:
            candidate = {**copy.deepcopy(template), "claim_id": claim["claim_id"], "source_ids": sorted(set(claim["source_ids"]))}
            canonical = _canonical_bound_item(candidate, claim, slot)
            if canonical is not None and canonical not in rebuilt:
                rebuilt.append(canonical)
        if not templates and claim.get("final_text") is not None:
            candidate = {"claim_id": claim["claim_id"], "source_ids": sorted(set(claim["source_ids"])), "text": claim["final_text"]}
            if candidate not in rebuilt:
                rebuilt.append(candidate)
    if isinstance(default, list):
        return rebuilt
    return rebuilt[0] if rebuilt else {}


def _ledger_scalar(claims: dict[str, dict[str, Any]], slot: str) -> Any:
    values = [
        claim.get("structured_value", {}).get(slot)
        for claim in sorted(claims.values(), key=lambda row: row["claim_id"])
        if slot in claim.get("allowed_slots", []) and slot in claim.get("structured_value", {})
    ]
    return copy.deepcopy(values[0]) if values and all(value == values[0] for value in values) else None


def _validate_source_bindings(result: dict[str, Any], claims: dict[str, dict[str, Any]], slots: tuple[str, ...]) -> None:
    for slot in slots:
        value = result.get(slot, [])
        items = value if isinstance(value, list) else ([] if not value else [value])
        for item in items:
            claim = claims.get(item.get("claim_id")) if isinstance(item, dict) else None
            if claim is None or _canonical_bound_item(item, claim, slot) != item:
                raise ValueError(f"source binding invalid after finalize: {slot}")


def finalize(draft: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(draft)
    claims = _validated_claims(ledger)
    if not claims:
        raise ValueError("finalizer requires at least one validated source-locked claim")
    allowed_claim_fields = {
        "claim_id", "source_ids", "assumption_ids", "final_text", "structured_value",
        "allowed_slots", "allowed_fields",
    }
    result["claim_ledger"] = [
        {key: copy.deepcopy(value) for key, value in claim.items() if key in allowed_claim_fields}
        for claim in sorted(claims.values(), key=lambda row: row["claim_id"])
    ]
    factual_slots = {
        "frozen_scope", "baseline", "scenarios",
        "capability_demand", "cost_bridge", "structure_options", "transition_route",
        "risks_and_counterpoints", "action_previews", "limitations", "next_steps",
        "unknowns",
    }
    declared_structured = ledger.get("structured_values", {})
    if not isinstance(declared_structured, dict) or not set(declared_structured) <= factual_slots:
        raise ValueError("ledger structured_values contains unsupported slots")
    touched_slots = set(declared_structured)
    for claim in claims.values():
        claim_slots = claim.get("allowed_slots", [])
        if not set(claim_slots) <= (factual_slots | {"currency", "period"}):
            raise ValueError("claim contains unsupported allowed slot")
        touched_slots.update(set(claim_slots) & factual_slots)
    for slot in sorted(touched_slots):
        default = {} if isinstance(result.get(slot), dict) else []
        rebuilt = _ledger_slot(ledger, claims, slot, default)
        if result.get(slot) and not rebuilt:
            raise ValueError(f"finalizer cannot clear non-empty slot: {slot}")
        result[slot] = rebuilt
    for slot in ("currency", "period"):
        if any(slot in claim.get("allowed_slots", []) for claim in claims.values()):
            rebuilt_scalar = _ledger_scalar(claims, slot)
            if result.get(slot) is not None and rebuilt_scalar is None:
                raise ValueError(f"finalizer cannot clear or conflict on scalar: {slot}")
            result[slot] = rebuilt_scalar
    result["counts"]["scenarios"] = len(result["scenarios"])
    result["counts"]["unknowns"] = len(result["unknowns"])
    result["formula_metadata"]["source_ids"] = sorted({
        sid for scenario in result["scenarios"] for sid in scenario.get("source_ids", [])
    })
    result["formula_metadata"]["assumption_ids"] = sorted({
        aid for scenario in result["scenarios"] for aid in scenario.get("assumption_ids", [])
    })
    result["formula_metadata"]["unit"] = result["currency"]
    result["formula_metadata"]["period"] = result["period"]
    _, privacy_findings = privacy_scan(result, _minimum_group_size(result))
    result["hard_gates"] = {
        "non_negative_hc": True,
        "unique_scenario_ids": len({row.get("scenario_id") for row in result["scenarios"]}) == len(result["scenarios"]),
        "scenarios_present": bool(result["scenarios"]),
        "privacy_minimized": not privacy_findings,
    }
    if result["artifact_state"] in {"ready", "degraded", "intake_required", "routed"}:
        result["artifact_state"] = _derive_state(
            result["route"], result["intake"], result["capabilities"], result["errors"],
            result["unknowns"], len(result["scenarios"]),
        )
    before_numbers = set(re.findall(r"-?\d+(?:\.\d+)?", json.dumps(draft)))
    after_numbers = set(re.findall(r"-?\d+(?:\.\d+)?", json.dumps(result)))
    ledger_numbers = set(re.findall(r"-?\d+(?:\.\d+)?", json.dumps(ledger)))
    if not after_numbers <= (before_numbers | ledger_numbers):
        raise ValueError("finalizer attempted to add a number")
    _validate_source_bindings(result, claims, tuple(sorted(touched_slots)))
    validate(result)
    return result


def _user_visible_text(response: dict[str, Any], route_only: bool) -> str:
    body = response.get("body")
    parts = [body] if isinstance(body, str) else []
    questions = response.get("questions")
    if route_only and isinstance(questions, list):
        parts.extend(item for item in questions if isinstance(item, str))
    visible = "\n".join(parts)
    if not visible:
        raise AssertionError("user-visible body required")
    if USER_VISIBLE_INTERNAL.search(visible) or PROCESS_LEAK.search(visible):
        raise AssertionError("internal mechanism or work log leaked into user-visible body")
    return visible


def assert_eval(case: dict[str, Any], response: dict[str, Any]) -> None:
    if not isinstance(response, dict):
        raise AssertionError("structured response wrapper required")
    if response.get("artifact_state") != case.get("expected_state"):
        raise AssertionError("expected state mismatch")
    if response.get("delivery_tier") != case.get("expected_tier") or response.get("search_mode") != case.get("search_mode"):
        raise AssertionError("tier or Search mismatch")
    route = response.get("route", {})
    if response["artifact_state"] in {"routed", "intake_required"}:
        visible = _user_visible_text(response, True)
        strict_mapping(route, ROUTE_KEYS, "route")
        if response.get("full") is not None or response.get("compact") is not None:
            raise AssertionError("route-only response must not include full/compact")
        if response["artifact_state"] == "routed":
            if route["route_status"] != "routed" or route["selected_skill"] != case.get("expected_route"):
                raise AssertionError("adjacent route mismatch")
        else:
            questions = response.get("questions")
            if route["route_status"] != "intake_required" or route["selected_skill"] != "organization-workforce-planning":
                raise AssertionError("intake route mismatch")
            if not isinstance(questions, list) or not 1 <= len(questions) <= 3 or not all(isinstance(item, str) for item in questions):
                raise AssertionError("intake questions invalid")
        for token in case.get("must_include", []):
            if token not in visible:
                raise AssertionError(f"missing token: {token}")
        for token in case.get("must_not_include", []):
            if token in visible:
                raise AssertionError(f"forbidden token: {token}")
        return
    visible = _user_visible_text(response, False)
    strict_mapping(route, ROUTE_KEYS, "route")
    if route["selected_skill"] != "organization-workforce-planning":
        raise AssertionError("route mismatch")
    strict_mapping(response.get("capabilities"), CAPABILITY_KEYS, "capabilities", True)
    full, compact = response.get("full"), response.get("compact")
    if not isinstance(full, dict) or not isinstance(compact, dict):
        raise AssertionError("full/compact artifacts required")
    full_bytes = (json.dumps(full, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    expected_hash = hashlib.sha256(full_bytes).hexdigest()
    if response.get("full_sha256") != expected_hash or compact.get("full_sha256") != expected_hash:
        raise AssertionError("artifact hash mismatch")
    try:
        validate(full, compact, full_bytes)
    except ValueError as exc:
        raise AssertionError(f"artifact validation failed: {exc}") from exc
    if compact.get("counts") != full.get("counts") or compact.get("hard_gates") != full.get("hard_gates"):
        raise AssertionError("compact mirror mismatch")
    if (
        response["artifact_state"] != full.get("artifact_state") or response["artifact_state"] != compact.get("artifact_state")
        or response["delivery_tier"] != full.get("delivery_tier") or response["delivery_tier"] != compact.get("delivery_tier")
        or response["search_mode"] != full.get("search_mode") or response["search_mode"] != compact.get("search_mode")
        or response["capabilities"] != full.get("capabilities") or response["capabilities"] != compact.get("capabilities")
    ):
        raise AssertionError("state/tier/Search/capability mirror mismatch")
    expected_core = {
        "baseline": full.get("baseline"), "capability_demand": full.get("capability_demand"),
        "scenarios": full.get("scenarios"), "cost_bridge": full.get("cost_bridge"),
        "structure_options": full.get("structure_options"), "transition_route": full.get("transition_route"),
        "risks_and_counterpoints": full.get("risks_and_counterpoints"),
        "unknowns": full.get("unknowns"), "next_steps": full.get("next_steps"),
    }
    if compact.get("core_slots") != expected_core or compact.get("source_index") != full.get("formula_metadata", {}).get("source_ids"):
        raise AssertionError("core/source mirror mismatch")
    if route != full.get("route"):
        raise AssertionError("route mirror mismatch")
    if response["artifact_state"] == "ready" and not all(full.get("hard_gates", {}).values()):
        raise AssertionError("ready with failed Hard Gate")
    for token in case.get("must_include", []):
        if token not in visible:
            raise AssertionError(f"missing user-visible token: {token}")
    for token in case.get("must_not_include", []):
        if token in visible:
            raise AssertionError(f"forbidden user-visible token: {token}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compute"); c.add_argument("--input", required=True); c.add_argument("--full-out", required=True); c.add_argument("--compact-out", required=True)
    v = sub.add_parser("validate"); v.add_argument("--full", required=True); v.add_argument("--compact")
    p = sub.add_parser("privacy"); p.add_argument("--input", required=True); p.add_argument("--output", required=True)
    f = sub.add_parser("finalize"); f.add_argument("--input", required=True); f.add_argument("--claims", required=True); f.add_argument("--output", required=True)
    e = sub.add_parser("assert-eval"); e.add_argument("--evals", required=True); e.add_argument("--case-id", required=True); e.add_argument("--response", required=True)
    args = parser.parse_args()
    if args.command == "compute":
        full = calculate(json.loads(Path(args.input).read_text())); dump(args.full_out, full)
        data = Path(args.full_out).read_bytes(); compact = compact_for(full, Path(args.full_out).name, hashlib.sha256(data).hexdigest()); dump(args.compact_out, compact); validate(full, compact, data)
    elif args.command == "validate":
        data = Path(args.full).read_bytes(); validate(json.loads(data), json.loads(Path(args.compact).read_text()) if args.compact else None, data)
    elif args.command == "privacy":
        privacy_payload = json.loads(Path(args.input).read_text())
        clean, _ = privacy_scan(privacy_payload, _minimum_group_size(privacy_payload))
        dump(args.output, clean)
    elif args.command == "finalize":
        dump(args.output, finalize(json.loads(Path(args.input).read_text()), json.loads(Path(args.claims).read_text())))
    else:
        cases = json.loads(Path(args.evals).read_text())["evals"]; case = next(x for x in cases if x["id"] == args.case_id); assert_eval(case, json.loads(Path(args.response).read_text()))


if __name__ == "__main__":
    main()
