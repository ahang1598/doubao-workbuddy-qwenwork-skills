#!/usr/bin/env python3
"""Validation and audit checks for normalized and calculated DCF files."""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

from calculate_dcf import calculate


SCENARIO_ZH = {"bear": "悲观", "base": "基准", "bull": "乐观"}


def scenario_zh(name: str) -> str:
    return SCENARIO_ZH.get(name.lower(), name)


def check(name: str, actual: Any, expected: Any, difference: Any, tolerance: Any, status: str, notes: str) -> dict[str, Any]:
    return {"check": name, "actual": actual, "expected": expected, "difference": difference, "tolerance": tolerance, "status": status, "notes": notes}


def validate(payload: dict[str, Any], calculated: dict[str, Any] | None = None) -> dict[str, Any]:
    expected_calc = calculate(payload)
    calculated = calculated or expected_calc
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    incomplete: list[str] = []
    warnings: list[str] = list(calculated.get("warnings", []))
    meta = payload.get("meta", {})
    formal_model = meta.get("model_purpose", "formal") != "illustrative"

    for key in ("company", "ticker", "valuation_date", "currency", "units"):
        present = bool(meta.get(key))
        checks.append(check(f"meta.{key}", present, True, 0 if present else 1, 0, "通过" if present else "错误", "必填模型元数据"))
        if not present:
            errors.append(f"缺少必填模型元数据：meta.{key}")

    sources = payload.get("sources", [])
    field_sources = payload.get("field_sources", {})
    source_ok = isinstance(sources, list) and len(sources) > 0
    mapping_ok = isinstance(field_sources, dict) and len(field_sources) > 0
    source_status = "通过" if source_ok else ("错误" if formal_model else "警告")
    mapping_status = "通过" if mapping_ok else ("错误" if formal_model else "警告")
    checks.append(check("来源台账", len(sources) if isinstance(sources, list) else 0, ">0", None, None, source_status, "正式估值必须填充权威来源"))
    checks.append(check("字段来源映射", len(field_sources) if isinstance(field_sources, dict) else 0, ">0", None, None, mapping_status, "关键 R/E/A/H 字段需要映射至真实来源或假设依据"))
    if not source_ok:
        message = "来源台账为空；正式估值必须补充权威来源"
        (errors if formal_model else warnings).append(message)
    if not mapping_ok:
        message = "字段来源映射为空；关键报告值、调整值、预测值和市场数据必须映射至来源"
        (errors if formal_model else warnings).append(message)

    source_ids: set[str] = set()
    source_by_id: dict[str, dict[str, Any]] = {}
    duplicate_source_ids: set[str] = set()
    invalid_source_rows: list[int] = []
    if isinstance(sources, list):
        for index, item in enumerate(sources):
            source_id = item.get("source_id") if isinstance(item, dict) else None
            if not isinstance(source_id, str) or not source_id.strip():
                invalid_source_rows.append(index)
                continue
            source_id = source_id.strip()
            if source_id in source_ids:
                duplicate_source_ids.add(source_id)
            source_ids.add(source_id)
            source_by_id[source_id] = item
    source_integrity_ok = not invalid_source_rows and not duplicate_source_ids
    checks.append(check("来源ID唯一性", {"invalid_rows": invalid_source_rows, "duplicates": sorted(duplicate_source_ids)}, "无空值且唯一", len(invalid_source_rows) + len(duplicate_source_ids), 0, "通过" if source_integrity_ok else "错误", "来源台账的source_id必须非空且唯一"))
    if not source_integrity_ok:
        errors.append("来源台账存在空来源ID或重复来源ID")

    def mapped_source_ids(value: Any) -> list[str]:
        found: list[str] = []
        if isinstance(value, dict):
            if isinstance(value.get("source_id"), str):
                found.append(value["source_id"])
            for child in value.values():
                found.extend(mapped_source_ids(child))
        elif isinstance(value, list):
            for child in value:
                found.extend(mapped_source_ids(child))
        return found

    dangling = sorted({source_id for source_id in mapped_source_ids(field_sources) if source_id not in source_ids})
    checks.append(check("来源ID引用完整性", len(dangling), 0, len(dangling), 0, "通过" if not dangling else "错误", "字段来源映射引用的来源ID必须存在于来源台账"))
    if dangling:
        errors.append("字段来源映射引用不存在的来源ID：" + ", ".join(dangling))

    required_mappings = meta.get(
        "required_source_mappings",
        ["forecast", "wacc", "equity_bridge", "corporate_actions", "market_cap_cross_check"],
    )
    if formal_model and isinstance(required_mappings, list):
        invalid_mappings: list[str] = []
        for key in required_mappings:
            mapped_ids = mapped_source_ids(field_sources.get(key)) if isinstance(field_sources, dict) else []
            if not mapped_ids or any(source_id not in source_ids for source_id in mapped_ids):
                invalid_mappings.append(str(key))
        checks.append(check("关键字段来源覆盖", len(invalid_mappings), 0, len(invalid_mappings), 0, "通过" if not invalid_mappings else "错误", "每个关键字段组必须引用至少一个真实来源ID"))
        if invalid_mappings:
            errors.append("关键字段来源映射为空或无效：" + ", ".join(invalid_mappings))

    scenarios_input = payload.get("scenarios", {})
    if formal_model and isinstance(scenarios_input, dict):
        for name, scenario in scenarios_input.items():
            evidence = scenario.get("scenario_evidence") if isinstance(scenario, dict) else None
            valid = (
                isinstance(evidence, dict)
                and bool(evidence.get("rationale"))
                and isinstance(evidence.get("changed_drivers"), list)
                and len(evidence.get("changed_drivers")) > 0
                and all(isinstance(item, str) and item.strip() for item in evidence.get("changed_drivers"))
                and isinstance(evidence.get("source_ids"), list)
                and len(evidence.get("source_ids")) > 0
                and all(isinstance(source_id, str) and source_id in source_ids for source_id in evidence.get("source_ids"))
                and isinstance(evidence.get("invalidation_conditions"), list)
                and len(evidence.get("invalidation_conditions")) > 0
                and all(isinstance(item, str) and item.strip() for item in evidence.get("invalidation_conditions"))
            )
            status = "通过" if valid else "未完成"
            checks.append(check(f"{scenario_zh(name)}情景依据", valid, True, 0 if valid else 1, 0, status, "情景必须说明变化驱动、依据和失效条件"))
            if not valid:
                incomplete.append(f"{scenario_zh(name)}情景缺少可审计依据、变化驱动或失效条件")

    equity_bridge = payload.get("equity_bridge", {})
    share_classes = equity_bridge.get("share_classes") if isinstance(equity_bridge, dict) else None
    if formal_model:
        invalid_classes: list[str] = []
        valuation_date = meta.get("valuation_date")
        for index, item in enumerate(share_classes if isinstance(share_classes, list) else []):
            if not isinstance(item, dict):
                invalid_classes.append(str(index))
                continue
            required = (
                "security_id",
                "exchange",
                "shares",
                "shares_date",
                "price",
                "price_date",
                "price_basis",
                "currency",
                "fx_to_valuation_currency",
                "source_id",
                "reference_market_cap",
                "market_cap_date",
                "market_cap_source_id",
            )
            if any(item.get(field) in (None, "") for field in required):
                invalid_classes.append(str(index))
                continue
            if item.get("source_id") not in source_ids or item.get("market_cap_source_id") not in source_ids:
                invalid_classes.append(str(index))
                continue
            try:
                parsed_valuation = date.fromisoformat(str(valuation_date))
                for source_id in (item.get("source_id"), item.get("market_cap_source_id")):
                    if date.fromisoformat(str(source_by_id[source_id].get("public_date"))) > parsed_valuation:
                        raise ValueError
                parsed_price = date.fromisoformat(str(item["price_date"]))
                parsed_shares = date.fromisoformat(str(item["shares_date"]))
                parsed_market_cap = date.fromisoformat(str(item["market_cap_date"]))
                if (
                    parsed_price > parsed_valuation
                    or (parsed_valuation - parsed_price).days > 7
                    or parsed_shares != parsed_valuation
                    or parsed_market_cap != parsed_price
                    or item.get("price_basis") != "unadjusted_close"
                ):
                    invalid_classes.append(str(index))
            except ValueError:
                invalid_classes.append(str(index))
        classes_ok = isinstance(share_classes, list) and bool(share_classes) and not invalid_classes
        checks.append(check("分证券股价—股数—市值口径", invalid_classes, [], len(invalid_classes), 0, "通过" if classes_ok else "错误", "每个证券必须使用估值日股数、不复权近端收盘价，并以同日独立市值反向核验"))
        if not classes_ok:
            errors.append("分证券股本与市值桥缺少估值日股数、不复权近端价格、独立市值或真实来源")

        review = equity_bridge.get("corporate_action_review") if isinstance(equity_bridge, dict) else None
        review_errors: list[str] = []
        if not isinstance(review, dict):
            review_errors.append("缺少公司行动检索记录")
        else:
            try:
                baseline_date = date.fromisoformat(str(review.get("baseline_share_date")))
                search_start = date.fromisoformat(str(review.get("search_start_date")))
                reviewed_through = date.fromisoformat(str(review.get("reviewed_through_date")))
                parsed_valuation = date.fromisoformat(str(valuation_date))
                if search_start > baseline_date:
                    review_errors.append("检索起始日晚于基准股本日")
                if reviewed_through != parsed_valuation:
                    review_errors.append("检索截止日必须等于估值日")
            except ValueError:
                review_errors.append("公司行动检索日期无效")
            review_source_ids = review.get("source_ids")
            if not isinstance(review_source_ids, list) or not review_source_ids or any(source_id not in source_ids for source_id in review_source_ids):
                review_errors.append("公司行动检索未引用真实来源")
            elif isinstance(review_source_ids, list):
                for source_id in review_source_ids:
                    try:
                        if date.fromisoformat(str(source_by_id[source_id].get("public_date"))) > date.fromisoformat(str(valuation_date)):
                            review_errors.append(f"公司行动来源{source_id}在估值日后才公开")
                    except ValueError:
                        review_errors.append(f"公司行动来源{source_id}缺少有效公开日")
            if review.get("no_unrecorded_actions_confirmed") is not True:
                review_errors.append("未确认估值日前公司行动已完整覆盖")
            actions = review.get("actions")
            if not isinstance(actions, list):
                review_errors.append("公司行动清单缺失")
            else:
                for index, action in enumerate(actions):
                    if not isinstance(action, dict) or action.get("source_id") not in source_ids:
                        review_errors.append(f"公司行动{index}缺少真实来源")
                        continue
                    try:
                        effective_date = date.fromisoformat(str(action.get("effective_date")))
                        parsed_valuation = date.fromisoformat(str(valuation_date))
                    except ValueError:
                        review_errors.append(f"公司行动{index}生效日无效")
                        continue
                    if effective_date <= parsed_valuation and action.get("applied_to_share_count") is not True:
                        review_errors.append(f"公司行动{index}已生效但未计入股数")
        review_ok = not review_errors
        checks.append(check("估值日前公司行动完整性", review_errors, [], len(review_errors), 0, "通过" if review_ok else "错误", "必须从基准股本日至估值日检索送股、转增、拆合股、增发、回购、转换、ADR/H股变化并滚存股数"))
        if not review_ok:
            errors.append("估值日前公司行动检索或股数滚存不完整：" + "；".join(review_errors))

    wacc_components = payload.get("wacc_components")
    if formal_model and not isinstance(wacc_components, dict):
        checks.append(check("WACC计算方式", "直接WACC或缺失", "完整组成项", 1, 0, "错误", "正式模型必须由WACC组成项计算，直接WACC只允许示例模型"))
        errors.append("正式模型缺少WACC组成项；不得直接硬编码最终WACC")
    if formal_model and isinstance(wacc_components, dict):
        basis_ok = wacc_components.get("capital_structure_basis") in {"current_actual", "target", "hybrid"}
        rationale_ok = bool(wacc_components.get("capital_structure_rationale"))
        checks.append(check("资本结构口径", basis_ok and rationale_ok, True, 0 if basis_ok and rationale_ok else 1, 0, "通过" if basis_ok and rationale_ok else "未完成", "必须区分公司实际资本结构与估值采用结构并解释差异"))
        if not (basis_ok and rationale_ok):
            incomplete.append("WACC未说明公司实际资本结构与估值采用资本结构的关系")

    if formal_model and meta.get("consolidated_fcff_includes_non_wholly_owned_subsidiaries") is True:
        minority = payload.get("equity_bridge", {}).get("minority_interest")
        reason = payload.get("equity_bridge", {}).get("minority_interest_not_applicable_reason")
        minority_ok = (isinstance(minority, (int, float)) and minority > 0) or bool(reason)
        checks.append(check("少数股东权益桥接", minority_ok, True, 0 if minority_ok else 1, 0, "通过" if minority_ok else "错误", "合并FCFF包含非全资子公司时必须扣除少数股东权益或解释不适用"))
        if not minority_ok:
            errors.append("企业价值到股权价值桥遗漏少数股东权益")

    tolerance = 1e-8
    for name, result in calculated.get("scenarios", {}).items():
        display_name = scenario_zh(name)
        for row in result.get("forecast", []):
            expected_fcff = row["nopat"] + row["da"] - row["capex"] - row["delta_nwc"] + row["other_noncash"] - row["other_investment"]
            delta = row["fcff"] - expected_fcff
            status = "通过" if abs(delta) <= tolerance else "错误"
            checks.append(check(f"{display_name} {row['period']} 企业自由现金流（FCFF）勾稽", row["fcff"], expected_fcff, delta, tolerance, status, "税后经营利润 + 折旧摊销 - 资本开支 - 经营性净营运资本增加 ± 其他调整"))
            if status == "错误":
                errors.append(f"{display_name} {row['period']}：企业自由现金流（FCFF）未通过勾稽")
        spread = result["wacc"] - result["terminal_growth"]
        status = "通过" if spread >= 0.005 else "警告"
        checks.append(check(f"{display_name} 加权平均资本成本（WACC）与永续增长率安全垫", spread, ">=0.005", None, 0.005, status, "至少保留50个基点"))
        tv_share = result.get("terminal_value_share_of_ev")
        if tv_share is None:
            status = "错误"
            errors.append(f"{display_name}：无法计算终值占比")
        elif tv_share > 0.90 and formal_model:
            status = "错误"
            errors.append(f"{display_name}：终值占比超过90%，必须重建显性期后才能输出点估值")
        elif tv_share > 0.85 and formal_model:
            status = "未完成"
            incomplete.append(f"{display_name}：终值占比超过85%，需要延长显性期或补充稳态过渡证据")
        elif tv_share > 0.75:
            status = "警告"
        else:
            status = "通过"
        checks.append(check(f"{display_name} 终值占比", tv_share, "<=0.75；>0.85未完成；>0.90失败", None, 0.75, status, "终值占比较高时必须延长预测期、解释稳态并扩大敏感性"))
        factors = [row["discount_factor"] for row in result.get("forecast", [])]
        monotonic = all(0 < factor < 1 for factor in factors) and all(factors[i] > factors[i + 1] for i in range(len(factors) - 1))
        checks.append(check(f"{display_name} 折现因子", monotonic, True, 0 if monotonic else 1, 0, "通过" if monotonic else "错误", "折现因子必须位于0与1之间并逐期下降"))
        if not monotonic:
            errors.append(f"{display_name}：折现因子无效")

    calc_base = calculated["scenarios"][calculated["base_scenario"]]["per_share_value"]
    expected_base = expected_calc["scenarios"][expected_calc["base_scenario"]]["per_share_value"]
    delta = calc_base - expected_base
    status = "通过" if math.isclose(calc_base, expected_base, rel_tol=1e-10, abs_tol=1e-8) else "错误"
    checks.append(check("计算文件一致性", calc_base, expected_base, delta, 1e-8, status, "根据标准化输入重新计算"))
    if status == "错误":
        errors.append("计算结果与标准化输入重新计算的结果不一致")

    sens = calculated.get("sensitivity", {})
    sens_rows = sens.get("rows", [])
    direction_ok = True
    for row in sens_rows:
        values = [value for value in row.get("per_share_values", []) if value is not None]
        if any(values[i] < values[i + 1] for i in range(len(values) - 1)):
            direction_ok = False
    checks.append(check("敏感性方向", direction_ok, True, 0 if direction_ok else 1, 0, "通过" if direction_ok else "错误", "其他条件不变时，每股价值不应随WACC上升而提高"))
    if not direction_ok:
        errors.append("敏感性方向无效：其他条件不变时，每股价值不应随加权平均资本成本（WACC）上升而提高")

    status_code = "FAIL" if errors else ("INCOMPLETE" if incomplete else "PASS")
    status_zh = {"PASS": "通过", "INCOMPLETE": "未完成", "FAIL": "失败"}[status_code]
    return {"model_status": status_zh, "model_status_code": status_code, "errors": errors, "incomplete_reasons": sorted(set(incomplete)), "warnings": sorted(set(warnings)), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="校验标准化DCF输入与计算结果")
    parser.add_argument("input", type=Path)
    parser.add_argument("--calculated", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    calculated = json.loads(args.calculated.read_text(encoding="utf-8")) if args.calculated else None
    result = validate(payload, calculated)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["model_status_code"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
