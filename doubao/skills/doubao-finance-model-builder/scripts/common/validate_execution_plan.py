#!/usr/bin/env python3
"""Validate a public-company finance execution plan before model execution."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


WORKFLOWS = {"three_statements", "dcf", "lbo", "comps"}
STATUSES = ["PASS", "INCOMPLETE", "FAIL"]
VALUATION_WORKFLOWS = {"dcf", "comps"}


def parse_date(value: Any, field: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be YYYY-MM-DD")
        return None


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(item not in (None, "") for item in value)


def validate_scenario(name: str, scenario: Any, source_ids: set[str], errors: list[str]) -> None:
    prefix = f"module_plans.dcf.scenarios.{name}"
    if not isinstance(scenario, dict):
        errors.append(f"{prefix} is required")
        return
    for key in ("rationale", "changed_drivers", "source_ids", "invalidation_conditions"):
        value = scenario.get(key)
        if key == "rationale":
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{key} must be non-empty")
        elif not nonempty_list(value):
            errors.append(f"{prefix}.{key} must be a non-empty list")
    for source_id in scenario.get("source_ids", []) if isinstance(scenario.get("source_ids"), list) else []:
        if source_id not in source_ids:
            errors.append(f"{prefix}.source_ids references unknown source: {source_id}")


def validate(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if plan.get("schema_version") != "3.1":
        errors.append("schema_version must be 3.1")
    meta = plan.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta is required")
        meta = {}
    for key in ("task_id", "company", "currency", "units"):
        if not isinstance(meta.get(key), str) or not meta.get(key).strip():
            errors.append(f"meta.{key} must be non-empty")
    if meta.get("model_purpose") not in {"formal", "illustrative"}:
        errors.append("meta.model_purpose must be formal or illustrative")
    valuation_date = parse_date(meta.get("valuation_date"), "meta.valuation_date", errors)
    cutoff_date = parse_date(meta.get("information_cutoff_date"), "meta.information_cutoff_date", errors)
    if valuation_date and cutoff_date and cutoff_date > valuation_date:
        errors.append("information_cutoff_date cannot be later than valuation_date")

    workflows = plan.get("workflows")
    if not nonempty_list(workflows):
        errors.append("workflows must be a non-empty list")
        workflows = []
    elif len(set(workflows)) != len(workflows):
        errors.append("workflows must not contain duplicates")
    unknown = sorted(set(workflows) - WORKFLOWS)
    if unknown:
        errors.append("unsupported workflows: " + ", ".join(unknown))

    deliverables = plan.get("deliverables")
    if not isinstance(deliverables, dict) or not isinstance(deliverables.get("hero"), str) or not deliverables.get("hero"):
        errors.append("deliverables.hero is required")
    elif not isinstance(deliverables.get("support", []), list):
        errors.append("deliverables.support must be a list")
    if isinstance(deliverables, dict) and "artifact-audit.json" not in deliverables.get("support", []):
        errors.append("deliverables.support must include artifact-audit.json")

    evidence = plan.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence is required")
        evidence = {}
    ids = evidence.get("source_ids")
    if not nonempty_list(ids):
        errors.append("evidence.source_ids must be a non-empty list")
        ids = []
    elif len(set(ids)) != len(ids):
        errors.append("evidence.source_ids must be unique")
    source_ids = set(ids)
    if evidence.get("conflict_resolution_required") is not True:
        errors.append("evidence.conflict_resolution_required must be true")
    if not nonempty_list(evidence.get("required_topics")):
        errors.append("evidence.required_topics must be a non-empty list")
    elif meta.get("model_purpose") == "formal":
        if "latest_announcements" not in set(evidence["required_topics"]):
            errors.append("formal plan evidence.required_topics must include latest_announcements")

    quality_gates = set(plan.get("quality_gates", [])) if isinstance(plan.get("quality_gates"), list) else set()
    missing_artifact_gates = {"unified_model_audit", "direct_artifact_audit", "artifact_hash_lock"} - quality_gates
    if missing_artifact_gates:
        errors.append("quality_gates missing: " + ", ".join(sorted(missing_artifact_gates)))

    formal = meta.get("model_purpose") == "formal"
    if formal:
        support = deliverables.get("support", []) if isinstance(deliverables, dict) else []
        announcement_files = {
            "announcement-sweep.json",
            "announcement-sweep-validation.json",
            "model-contract.json",
            "model-audit.json",
        }
        missing = announcement_files - set(support if isinstance(support, list) else [])
        if missing:
            errors.append("formal deliverables.support missing: " + ", ".join(sorted(missing)))
    if formal and set(workflows) & VALUATION_WORKFLOWS:
        evidence_plan = plan.get("equity_evidence_plan")
        if not isinstance(evidence_plan, dict):
            errors.append("formal valuation requires equity_evidence_plan")
        else:
            expected = {
                "manifest_file": "equity-evidence.json",
                "validation_file": "equity-evidence-validation.json",
                "evidence_directory": "evidence",
                "validator": "scripts/common/validate_equity_evidence.py",
                "acquire_before_bridge": True,
                "must_pass_before_model": True,
                "local_primary_files_required": True,
                "official_search_result_required": True,
                "market_cap_reverse_check_required": True,
            }
            for key, value in expected.items():
                if evidence_plan.get(key) != value:
                    errors.append(f"equity_evidence_plan.{key} must equal {value!r}")
        support = deliverables.get("support", []) if isinstance(deliverables, dict) else []
        missing = {"equity-evidence.json", "equity-evidence-validation.json"} - set(support if isinstance(support, list) else [])
        if missing:
            errors.append("valuation deliverables.support missing: " + ", ".join(sorted(missing)))

    module_plans = plan.get("module_plans")
    if not isinstance(module_plans, dict):
        errors.append("module_plans is required")
        module_plans = {}
    for workflow in workflows:
        if not isinstance(module_plans.get(workflow), dict):
            errors.append(f"module_plans.{workflow} is required")

    if "dcf" in workflows and isinstance(module_plans.get("dcf"), dict):
        dcf = module_plans["dcf"]
        for key in ("input_file", "calculated_file", "workbook_file", "validation_file"):
            if not isinstance(dcf.get(key), str) or not dcf.get(key):
                errors.append(f"module_plans.dcf.{key} is required")
        if dcf.get("forecast_driver_level") not in {"segment", "volume_price", "operating_kpi", "total_growth_fallback"}:
            errors.append("module_plans.dcf.forecast_driver_level is invalid")
        threshold = dcf.get("material_driver_threshold")
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not 0 < threshold <= 1:
            errors.append("module_plans.dcf.material_driver_threshold must be in (0, 1]")
        scenarios = dcf.get("scenarios")
        if not isinstance(scenarios, dict):
            errors.append("module_plans.dcf.scenarios is required")
            scenarios = {}
        for name in ("bear", "base", "bull"):
            validate_scenario(name, scenarios.get(name), source_ids, errors)
        wacc = dcf.get("wacc")
        if not isinstance(wacc, dict):
            errors.append("module_plans.dcf.wacc is required")
        else:
            for key in ("current_actual_de_ratio", "adopted_de_ratio"):
                value = wacc.get(key)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
                    errors.append(f"module_plans.dcf.wacc.{key} must be in [0, 1]")
            if wacc.get("basis") not in {"current_actual", "target", "hybrid"}:
                errors.append("module_plans.dcf.wacc.basis is invalid")
            if wacc.get("basis") != "current_actual" and not str(wacc.get("rationale", "")).strip():
                errors.append("non-current WACC capital structure requires rationale")
        terminal = dcf.get("terminal_value")
        if not isinstance(terminal, dict):
            errors.append("module_plans.dcf.terminal_value is required")
        else:
            if terminal.get("method") not in {"perpetual_growth", "exit_multiple"}:
                errors.append("module_plans.dcf.terminal_value.method is invalid")
            limit = terminal.get("point_value_share_limit")
            if not isinstance(limit, (int, float)) or limit > 0.90:
                errors.append("DCF point-value terminal share limit cannot exceed 0.90")

    if "three_statements" in workflows and isinstance(module_plans.get("three_statements"), dict):
        three = module_plans["three_statements"]
        if three.get("revenue_driver_level") not in {"segment", "volume_price", "operating_kpi", "total_growth_fallback"}:
            errors.append("module_plans.three_statements.revenue_driver_level is invalid")
        required_checks = set(three.get("required_checks", []))
        missing = {"balance_sheet", "ending_cash", "retained_earnings"} - required_checks
        if missing:
            errors.append("three-statement plan missing checks: " + ", ".join(sorted(missing)))

    if "lbo" in workflows and isinstance(module_plans.get("lbo"), dict):
        lbo = module_plans["lbo"]
        assumptions = set(lbo.get("key_assumptions", []))
        required = {"ebitda_growth", "depreciation_amortization", "capex", "change_nwc", "tax_rate"}
        if not required <= assumptions:
            errors.append("LBO key assumptions missing: " + ", ".join(sorted(required - assumptions)))
        if not isinstance(lbo.get("operating_improvement_case"), dict):
            errors.append("LBO operating_improvement_case is required")
        if lbo.get("return_attribution_required") is not True:
            errors.append("LBO return_attribution_required must be true")

    if "comps" in workflows and isinstance(module_plans.get("comps"), dict):
        comps = module_plans["comps"]
        roles = set(comps.get("peer_roles", []))
        if not {"core", "secondary", "excluded"} <= roles:
            errors.append("comps peer_roles must include core, secondary and excluded")
        if comps.get("peer_rationale_required") is not True:
            errors.append("comps peer_rationale_required must be true")
        if comps.get("premium_discount_analysis_required") is not True:
            errors.append("comps premium_discount_analysis_required must be true")

    gates = set(plan.get("quality_gates", [])) if isinstance(plan.get("quality_gates"), list) else set()
    required_gates = {"source_mapping", "formula_errors", "cross_artifact_consistency"}
    if formal:
        required_gates.add("latest_announcement_sweep")
    if formal and set(workflows) & VALUATION_WORKFLOWS:
        required_gates |= {"local_primary_equity_evidence", "corporate_actions", "market_cap_reverse_check"}
    if not required_gates <= gates:
        errors.append("quality_gates missing: " + ", ".join(sorted(required_gates - gates)))

    policy = plan.get("result_policy")
    if not isinstance(policy, dict):
        errors.append("result_policy is required")
    else:
        if policy.get("allowed_statuses") != STATUSES:
            errors.append("result_policy.allowed_statuses must equal PASS, INCOMPLETE, FAIL")
        if policy.get("conclusion_requires_pass") is not True:
            errors.append("result_policy.conclusion_requires_pass must be true")
        limit = policy.get("point_value_terminal_share_limit")
        if "dcf" in workflows and (not isinstance(limit, (int, float)) or limit > 0.90):
            errors.append("result_policy.point_value_terminal_share_limit cannot exceed 0.90")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="验证上市公司财务建模执行计划")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(json.loads(args.plan.read_text(encoding="utf-8")))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
