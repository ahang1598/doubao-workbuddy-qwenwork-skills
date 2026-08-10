#!/usr/bin/env python3
"""Validate high-impact recommendations before they enter a final answer.

The input is a JSON object with a non-empty ``actions`` list. This validator
checks evidence and experiment design, not domain-specific keywords or answers.
It exits 0 on PASS and 1 on FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from time_window_audit import audit_source


REDUCTION_ACTIONS = {
    "decrease",
    "reduce",
    "negative",
    "remove",
    "delete",
    "pause",
    "stop",
    "disable",
    "large_decrease",
}

ALLOWED_BASIS_TYPES = {
    "actual_config",
    "user_risk_budget",
    "historical_response",
    "platform_minimum_step",
    "prior_experiment",
}

RESPONSE_EVIDENCE_TYPES = {
    "none",
    "before_after_same_object",
    "controlled_test",
    "response_curve",
}
TIME_WINDOW_TYPES = {
    "point_events",
    "non_overlapping_periods",
    "overlapping_periods",
    "cumulative_snapshots",
    "unknown",
}
VERIFIED_REPLACEMENT_TYPES = {"observed_after_change", "controlled_test"}
REPLACEMENT_STATUSES = {"not_needed", "missing", "verified"}
PREDICTION_BASIS_TYPES = {"response_curve", "experiment", "scenario_formula"}
PREDICTION_KINDS = {"none", "direct_arithmetic", "behavioral_response"}
IMPACT_DIRECTIONS = {"none", "increase", "decrease", "remove"}
DIRECT_BLOCK_EXCEPTIONS = {"none", "legal", "safety", "fraud", "user_prohibited"}


def is_set(value) -> bool:
    return value is not None and value != "" and value != []


def derive_time_window_type(intervals: list[dict]) -> tuple[str, list[str]]:
    errors: list[str] = []
    parsed: list[tuple[date, date]] = []
    for idx, interval in enumerate(intervals, start=1):
        if not isinstance(interval, dict):
            errors.append(f"time_intervals[{idx}] 必须是对象")
            continue
        try:
            start = date.fromisoformat(str(interval.get("start") or ""))
            end = date.fromisoformat(str(interval.get("end") or ""))
        except ValueError:
            errors.append(f"time_intervals[{idx}] 的 start/end 必须是 ISO 日期")
            continue
        if start > end:
            errors.append(f"time_intervals[{idx}] 的 start 晚于 end")
            continue
        parsed.append((start, end))

    if errors or not parsed:
        return "unknown", errors

    unique = sorted(set(parsed))
    if all(start == end for start, end in unique):
        return "point_events", []

    overlaps = False
    for idx, left in enumerate(unique):
        for right in unique[idx + 1 :]:
            if max(left[0], right[0]) <= min(left[1], right[1]):
                overlaps = True
                break
        if overlaps:
            break

    if not overlaps:
        return "non_overlapping_periods", []

    starts = {start for start, _ in unique}
    nested = all(
        left[0] <= right[0] and left[1] >= right[1]
        or right[0] <= left[0] and right[1] >= left[1]
        for idx, left in enumerate(unique)
        for right in unique[idx + 1 :]
    )
    if len(starts) == 1 or nested:
        return "cumulative_snapshots", []
    return "overlapping_periods", []


def validate(plan: dict, base_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    base_dir = base_dir or Path.cwd()
    context = plan.get("context")
    if not isinstance(context, dict):
        return ["context 必须是对象"]

    actual_config_known = context.get("actual_config_known") is True
    post_change_data_available = context.get("post_change_data_available") is True
    objective_impaired = context.get("objective_impaired") is True
    primary_objectives = context.get("primary_objectives")
    if objective_impaired and (
        not isinstance(primary_objectives, list)
        or not primary_objectives
        or not all(isinstance(item, str) and item.strip() for item in primary_objectives)
    ):
        errors.append(
            "主目标受损时 context.primary_objectives 必须列出全部明确恢复目标"
        )
        primary_objectives = []
    response_evidence_type = str(
        context.get("response_evidence_type") or "none"
    ).strip().lower()
    time_window_type = str(
        context.get("time_window_type") or "unknown"
    ).strip().lower()
    if context.get("change_analysis") not in {True, False}:
        errors.append("context.change_analysis 必须明确填写 true/false，不能省略变化任务检查")
    if time_window_type not in TIME_WINDOW_TYPES:
        errors.append("context.time_window_type 非法")
    if response_evidence_type not in RESPONSE_EVIDENCE_TYPES:
        errors.append("context.response_evidence_type 非法")
    if context.get("change_analysis") is True:
        if context.get("time_fields_present") not in {True, False}:
            errors.append("变化任务必须明确填写 context.time_fields_present")
        time_fields_present = context.get("time_fields_present") is True
        if time_fields_present:
            source_audits = context.get("time_source_audits")
            if not isinstance(source_audits, list) or not source_audits:
                errors.append(
                    "变化任务存在时间字段时，必须提供 time_source_audits，"
                    "由脚本直接读取相关源表"
                )
            else:
                audited_intervals: list[dict] = []
                audit_types: list[str] = []
                for idx, spec in enumerate(source_audits, start=1):
                    if not isinstance(spec, dict):
                        errors.append(f"time_source_audits[{idx}] 必须是对象")
                        continue
                    try:
                        source = Path(str(spec.get("source_path") or ""))
                        if not source.is_absolute():
                            source = (base_dir / source).resolve()
                        result = audit_source(
                            source,
                            str(spec.get("sheet") or "Sheet1"),
                            int(spec.get("header_row") or 1),
                            str(spec.get("start_column") or ""),
                            str(spec.get("end_column") or ""),
                        )
                    except Exception as exc:
                        errors.append(f"time_source_audits[{idx}] 无法审计源表: {exc}")
                        continue
                    audited_intervals.extend(result["intervals"])
                    audit_types.append(result["derived_type"])
                if audited_intervals:
                    derived_type, interval_errors = derive_time_window_type(
                        audited_intervals
                    )
                    errors.extend(interval_errors)
                else:
                    derived_type = "unknown"
                record_count = context.get("time_record_count")
                if record_count != len(audited_intervals):
                    errors.append(
                        "time_record_count 必须等于脚本从源表读取的记录数，"
                        "不能手填或只提交方便归因的子集"
                    )
                if time_window_type != derived_type:
                    errors.append(
                        f"context.time_window_type={time_window_type} 与脚本判定"
                        f" {derived_type} 不一致"
                    )
        elif time_window_type != "unknown":
            errors.append("无时间字段时 time_window_type 必须为 unknown")
    if response_evidence_type != "none" and not is_set(
        context.get("response_evidence")
    ):
        errors.append("context 声称存在响应证据，但缺少 response_evidence")
    if response_evidence_type == "before_after_same_object":
        if time_window_type not in {"point_events", "non_overlapping_periods"}:
            errors.append(
                "前后响应证据要求点事件或互不重叠期间；"
                "重叠期间、累计快照或未知时间语义不能构造前后对比"
            )
        if context.get("action_change_verified") is not True or not is_set(
            context.get("action_change_evidence")
        ):
            errors.append(
                "前后响应证据缺少已验证动作及其参数变化；"
                "对象名称或创建时间不能替代变更记录"
            )

    actions = plan.get("actions")
    if not isinstance(actions, list) or not actions:
        return ["actions 必须是非空数组"]

    causal_families: dict[str, set[str]] = defaultdict(set)

    for idx, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            errors.append(f"action[{idx}] 必须是对象")
            continue

        label = action.get("name") or f"action[{idx}]"
        kind = str(action.get("action") or "").strip().lower()
        family = str(action.get("change_family") or "").strip().lower()
        phase = str(action.get("phase") or "").strip()

        execution_status = str(action.get("execution_status") or "").strip().lower()
        impact_direction = str(action.get("impact_direction") or "").strip().lower()
        if not label or not kind or not family or not phase or execution_status not in {
            "verify",
            "conditional",
            "immediate",
        }:
            errors.append(
                f"{label}: 缺少 name/action/change_family/phase，或 execution_status 非法"
            )
        if impact_direction not in IMPACT_DIRECTIONS:
            errors.append(f"{label}: impact_direction 必须是 none/increase/decrease/remove")

        is_reduction = impact_direction in {"decrease", "remove"}
        if kind in REDUCTION_ACTIONS and not is_reduction:
            errors.append(f"{label}: action 表示削减，但 impact_direction 未如实标为 decrease/remove")

        identity_known = action.get("object_identity_known") is True
        important_source = action.get("important_source") is True
        direct_block_exception = str(
            action.get("direct_block_exception") or "none"
        ).strip().lower()
        if direct_block_exception not in DIRECT_BLOCK_EXCEPTIONS:
            errors.append(f"{label}: direct_block_exception 非法")
            direct_block_exception = "none"
        if direct_block_exception != "none" and not is_set(
            action.get("direct_block_evidence")
        ):
            errors.append(f"{label}: 直接阻断例外缺少可追溯证据")

        if is_reduction and objective_impaired:
            contributions = action.get("objective_contributions")
            contribution_risk = False
            if not isinstance(contributions, dict):
                errors.append(
                    f"{label}: 主目标受损时，削减动作必须逐个填写"
                    " objective_contributions"
                )
                contribution_risk = True
            else:
                for objective in primary_objectives:
                    value = contributions.get(objective)
                    if value == "unknown":
                        contribution_risk = True
                    elif isinstance(value, (int, float)) and not isinstance(value, bool):
                        if value < 0:
                            errors.append(f"{label}: 目标贡献不能为负数")
                        elif value > 0:
                            contribution_risk = True
                    else:
                        errors.append(
                            f"{label}: objective_contributions[{objective!r}] "
                            "必须是非负数或 unknown"
                        )
                        contribution_risk = True
            if (
                contribution_risk
                and direct_block_exception == "none"
                and not important_source
            ):
                errors.append(
                    f"{label}: 对任一受损主目标仍有贡献或贡献未知，"
                    "important_source 必须为 true；不能用另一指标为零掩盖影响"
                )
                important_source = True
        replacement_type = str(
            action.get("replacement_evidence_type") or "none"
        ).strip().lower()
        replacement_status = str(
            action.get("replacement_status") or "not_needed"
        ).strip().lower()
        if replacement_status not in REPLACEMENT_STATUSES:
            errors.append(f"{label}: replacement_status 非法")

        if (
            execution_status == "immediate"
            and not actual_config_known
            and family not in {"observe", "verify"}
        ):
            errors.append(f"{label}: 实际配置未知，只能立即核验，执行动作须降级为 conditional")

        if is_set(action.get("absolute_target")) and not actual_config_known:
            errors.append(f"{label}: 实际配置未知，不能给 absolute_target")

        relative_change = action.get("relative_change")
        if is_set(relative_change) and relative_change != 0:
            basis_type = str(action.get("relative_basis_type") or "").strip().lower()
            if not actual_config_known:
                errors.append(
                    f"{label}: 实际配置未知，不能给数值化 relative_change；"
                    "先取得当前配置，再依据可追溯证据定幅"
                )
            if basis_type not in ALLOWED_BASIS_TYPES:
                errors.append(f"{label}: relative_change 缺少有效 relative_basis_type")
            if not is_set(action.get("relative_basis_evidence")):
                errors.append(f"{label}: relative_change 缺少 relative_basis_evidence")
            if basis_type == "actual_config" and not actual_config_known:
                errors.append(f"{label}: relative_basis_type=actual_config 但实际配置未知")
            if basis_type == "actual_config" and not is_set(
                context.get("actual_config_evidence")
            ):
                errors.append(f"{label}: actual_config 缺少配置证据")
            if basis_type in {"historical_response", "prior_experiment"} and (
                response_evidence_type
                not in {
                    "before_after_same_object",
                    "controlled_test",
                    "response_curve",
                }
                or not is_set(context.get("response_evidence"))
            ):
                errors.append(
                    f"{label}: 历史表现或跨对象差异不等于响应证据；"
                    "须有同一对象不同配置的前后数据、对照实验或响应曲线"
                )
            if basis_type == "user_risk_budget" and not is_set(
                context.get("user_risk_budget_evidence")
            ):
                errors.append(f"{label}: 缺少用户风险预算证据")
            if basis_type == "platform_minimum_step" and not is_set(
                context.get("platform_step_evidence")
            ):
                errors.append(f"{label}: 缺少平台最小调整步长证据")

        if is_reduction and not identity_known:
            if execution_status == "immediate" or not is_set(
                action.get("trigger_condition")
            ):
                errors.append(f"{label}: 削减动作前必须确认对象身份；条件式动作须写触发条件")

        if is_reduction and important_source and objective_impaired:
            if not is_set(action.get("net_effect_evidence")):
                errors.append(f"{label}: 重要贡献来源缺少主目标/护栏净影响证据")
            if execution_status == "immediate" and (
                replacement_status != "verified"
                or replacement_type not in VERIFIED_REPLACEMENT_TYPES
                or not post_change_data_available
                or not is_set(action.get("replacement_evidence"))
            ):
                errors.append(f"{label}: 主目标受损且替代能力未经调整后数据验证，不能立即削减")
            if execution_status == "conditional":
                if action.get("replacement_gate_required") is not True:
                    errors.append(f"{label}: 条件式削减重要来源必须把替代承接验证设为前置门")
                if not is_set(action.get("replacement_test_plan")):
                    errors.append(f"{label}: 缺少替代来源承接能力的验证方案")
                if action.get("replacement_test_timing") != "before_reduction":
                    errors.append(f"{label}: 替代承接验证必须发生在削减主要来源之前")
                if not is_set(action.get("trigger_condition")):
                    errors.append(f"{label}: 条件式削减重要来源必须写可验证触发条件")

        if is_set(action.get("predicted_result")):
            prediction_kind = str(
                action.get("prediction_kind") or ""
            ).strip().lower()
            prediction_type = str(
                action.get("prediction_basis_type") or ""
            ).strip().lower()
            if prediction_kind not in PREDICTION_KINDS - {"none"}:
                errors.append(f"{label}: predicted_result 缺少有效 prediction_kind")
            if prediction_type not in PREDICTION_BASIS_TYPES:
                errors.append(f"{label}: predicted_result 缺少有效 prediction_basis_type")
            if not is_set(action.get("prediction_basis_evidence")):
                errors.append(f"{label}: predicted_result 缺少证据或情景公式")
            if response_evidence_type == "none":
                errors.append(
                    f"{label}: 无响应证据时不得填写 predicted_result；"
                    "直接算术应写成历史分解或带输入变量的敏感性，不得写成未来结果"
                )
            if (
                prediction_kind == "behavioral_response"
                and prediction_type == "scenario_formula"
            ):
                errors.append(
                    f"{label}: 行为结果不能仅靠情景公式预测，须有响应曲线或实验"
                )
            if (
                prediction_type == "response_curve"
                and response_evidence_type != "response_curve"
            ):
                errors.append(f"{label}: 声称使用响应曲线，但上下文没有响应曲线证据")
            if (
                prediction_type == "experiment"
                and response_evidence_type != "controlled_test"
            ):
                errors.append(f"{label}: 声称使用实验，但上下文没有对照实验")

        if execution_status in {"immediate", "conditional"} and family:
            causal_families[phase].add(family)

    for phase, families in causal_families.items():
        if len(families) > 1:
            bundle_reason = (plan.get("phase_bundle_reasons") or {}).get(phase)
            attribution_limit = (plan.get("phase_bundle_attribution_limits") or {}).get(
                phase
            )
            if not is_set(bundle_reason) or not is_set(attribution_limit):
                errors.append(
                    f"phase={phase}: 同时改变多类变量 {sorted(families)}，"
                    "须拆分，或同时记录联合调整理由与不可单因归因的限制"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan_json", help="结构化建议计划 JSON 文件")
    args = parser.parse_args()

    try:
        plan = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL\n- 无法读取 JSON: {exc}")
        return 1

    errors = validate(plan, Path(args.plan_json).resolve().parent)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
