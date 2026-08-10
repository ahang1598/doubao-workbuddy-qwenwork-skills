#!/usr/bin/env python3
"""Validate final response completeness before user delivery."""

import argparse
import ast
import json
import re
from pathlib import Path


URL_RE = re.compile(r"https?://[^\s)\]>）】；，。]+")
INTERNAL_MARKERS = (
    "DETERMINISTIC TOOL OUTPUT",
    "VERIFIED COMPACT EVIDENCE",
    "evidence-validation.json",
    "_call",
)
PRIMARY_SOURCE_TYPES = {
    "regulator_filing",
    "exchange_filing",
    "company_ir",
    "official_transcript",
    "authoritative_market_database",
}
CAPABILITIES = {
    "can_assess_business",
    "can_assess_competition",
    "can_assess_financial_quality",
    "can_compare_peers",
    "can_value",
    "can_state_investment_view",
}


def recompute(calculation):
    values = {
        item["name"]: item["value"]
        for item in calculation.get("inputs", [])
        if isinstance(item, dict) and "name" in item and isinstance(item.get("value"), (int, float))
    }
    tree = ast.parse(calculation.get("formula", ""), mode="eval")
    allowed = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load,
        ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
        ast.USub, ast.UAdd,
    )
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError("unsupported formula")
    return eval(compile(tree, "<calculation>", "eval"), {"__builtins__": {}}, values)


def validate_report(report):
    """Validate the structured P1 minimum-deliverable contract."""
    failures = []
    identity = report.get("identity", {})
    for key in ("company", "ticker", "exchange", "as_of", "latest_fy", "latest_reported_period"):
        if not identity.get(key):
            failures.append(f"identity.{key} missing")
    if identity.get("freeze_point_checked") is not True:
        failures.append("freeze-point/latest-filing probe not completed")

    answer = report.get("answer", {})
    if not answer.get("core_judgment"):
        failures.append("direct core judgment missing")
    capabilities = report.get("capabilities", {})
    if not CAPABILITIES.issubset(capabilities):
        failures.append("local capability gates incomplete")

    slots = report.get("evidence_slots", [])
    if not 8 <= len(slots) <= 15:
        failures.append("required evidence slots must contain 8-15 items")
    for index, slot in enumerate(slots):
        for key in ("fact_needed", "allowed_source_types", "period", "affected_claim_ids", "status"):
            if not slot.get(key):
                failures.append(f"evidence_slots[{index}].{key} missing")

    claims = report.get("claims", [])
    sources = {source.get("id"): source for source in report.get("sources", [])}
    calculations = {calc.get("id"): calc for calc in report.get("calculations", [])}
    for calc_id, calc in calculations.items():
        for key in ("formula", "inputs", "result", "unit", "period", "tolerance"):
            value = calc.get(key)
            if value is None or value == "" or (key == "inputs" and not value):
                failures.append(f"{calc_id or 'calculation'}: {key} missing")
        try:
            if abs(recompute(calc) - calc["result"]) > calc["tolerance"]:
                failures.append(f"{calc_id or 'calculation'}: result is not reproducible")
        except (KeyError, TypeError, ValueError, SyntaxError, ZeroDivisionError) as error:
            failures.append(f"{calc_id or 'calculation'}: cannot recompute ({error})")
    for claim in claims:
        if claim.get("critical") and claim.get("type") in {"fact", "calculation"}:
            if not claim.get("period") or not claim.get("source_ids"):
                failures.append(f"{claim.get('id', 'claim')}: critical evidence incomplete")
        if claim.get("financial_or_official"):
            claim_sources = [sources.get(item, {}) for item in claim.get("source_ids", [])]
            if not any(source.get("type") in PRIMARY_SOURCE_TYPES for source in claim_sources):
                failures.append(f"{claim.get('id', 'claim')}: secondary-only support for critical company fact")
        if claim.get("calculation_id") and claim["calculation_id"] not in calculations:
            failures.append(f"{claim.get('id', 'claim')}: unknown calculation_id")

    company_type = report.get("company_type", {})
    required = set(company_type.get("required_metrics", []))
    covered = set(company_type.get("covered_metrics", []))
    blocked = set(company_type.get("blocked_metrics", []))
    if not company_type.get("type") or not required:
        failures.append("company-type route or required metrics missing")
    if not required.issubset(covered | blocked):
        failures.append("company-type required metrics neither covered nor blocked")

    competition = report.get("competition", {})
    if not competition.get("named_peers") and not competition.get("blocked_reason"):
        failures.append("named peer or explicit peer blocker required")
    if competition.get("named_peers") and not competition.get("comparability_notes"):
        failures.append("peer comparability notes missing")
    if not report.get("financial_quality", {}).get("bridge"):
        failures.append("financial bridge missing")
    if report.get("contract_version") == "P2":
        cashflow = report.get("financial_quality", {}).get("cashflow_basis", {})
        if not cashflow.get("statement_cfo_claim_id"):
            failures.append("P2 FCF requires cash-flow-statement CFO claim")
        if not cashflow.get("cash_capex_claim_ids"):
            failures.append("P2 FCF requires cash CapEx claims")
        if not cashflow.get("conventional_fcf_definition"):
            failures.append("P2 conventional FCF definition missing")
        if cashflow.get("company_adjusted_fcf_name") and not cashflow.get(
            "adjusted_to_statutory_bridge"
        ):
            failures.append("P2 adjusted FCF lacks statutory cash-flow bridge")
        if cashflow.get("company_adjusted_fcf_name") and not cashflow.get(
            "statutory_total_cash_claim_id"
        ):
            failures.append("P2 adjusted FCF lacks statutory total-cash-flow claim")
        if cashflow.get("company_adjusted_fcf_name") and not cashflow.get(
            "customer_financing_scope"
        ):
            failures.append("P2 adjusted FCF lacks customer-financing scope")

    valuation = report.get("valuation", {})
    mode = valuation.get("mode")
    if mode not in {"full", "degraded", "blocked"}:
        failures.append("valuation.mode invalid")
    elif mode == "full":
        if not valuation.get("as_of") or not valuation.get("method") or not valuation.get("implied_assumptions"):
            failures.append("full valuation inputs incomplete")
    elif mode == "degraded":
        if not valuation.get("method") or not valuation.get("implied_assumptions") or not valuation.get("blocked_inputs"):
            failures.append("degraded valuation requires method, implied assumptions and blocked inputs")
    elif not valuation.get("blocked_inputs"):
        failures.append("blocked valuation requires blocked_inputs")
    if report.get("contract_version") == "P2":
        market_inputs = valuation.get("market_inputs", [])
        valuation_as_of = valuation.get("as_of")
        input_dates = {
            str(item.get("as_of", ""))[:10]
            for item in market_inputs
            if isinstance(item, dict) and item.get("as_of")
        }
        if mode == "full":
            if valuation.get("input_as_of_consistent") is not True:
                failures.append("P2 full valuation inputs are not as-of consistent")
            if not market_inputs:
                failures.append("P2 full valuation market_inputs missing")
            if len(input_dates) != 1 or (
                valuation_as_of and input_dates != {str(valuation_as_of)[:10]}
            ):
                failures.append("P2 full valuation mixes input dates")
        elif len(input_dates) > 1 and not valuation.get("blocked_inputs"):
            failures.append("P2 degraded valuation with mixed dates must block precision")

        company_type_name = company_type.get("type")
        if company_type_name in {"content_platform", "brand_ip_licensing"}:
            mechanism = company_type.get("content_rights_cost_mechanism", {})
            if not mechanism.get("variable_components"):
                failures.append("P2 content business lacks variable rights-cost mechanism")
            if mechanism.get("assumes_fixed_cost_dilution") is True:
                failures.append("P2 content rights cost cannot default to fixed-cost dilution")

    bear = report.get("bear_case", {})
    if not bear.get("strongest_counterargument"):
        failures.append("strongest counterargument missing")
    if len(bear.get("falsification_signals", [])) < 3:
        failures.append("at least three observable falsification signals required")
    claim_ids = {claim.get("id") for claim in claims}
    for index, item in enumerate(report.get("unknowns", [])):
        affected = item.get("affected_claim_ids", [])
        if not affected or not item.get("next_source"):
            failures.append(f"unknowns[{index}] lacks local impact or next source")
        if any(claim_id not in claim_ids for claim_id in affected):
            failures.append(f"unknowns[{index}] references unknown claim")
    return failures


def validate(text, contract):
    failures = []
    warnings = []
    length = len(text)
    if length < contract.get("min_chars", 0):
        failures.append(f"response too short: {length}")
    if contract.get("target_chars") and length > contract["target_chars"]:
        warnings.append(
            f"response exceeds soft target: {length} > {contract['target_chars']}"
        )
    if contract.get("max_chars") and length > contract["max_chars"]:
        failures.append(f"response exceeds hard length limit: {length}")
    if contract.get("response_status") == "incomplete":
        failures.append("API response status is incomplete")
    if contract.get("finish_reason") in {"length", "max_tokens"}:
        failures.append(
            f"response stopped by token limit: {contract['finish_reason']}"
        )
    lowered = text.lower()
    missing = []
    for section in contract.get("required_any", []):
        aliases = section if isinstance(section, list) else [section]
        if not any(alias.lower() in lowered for alias in aliases):
            missing.append(" / ".join(aliases))
    if missing:
        failures.append("missing required sections: " + "; ".join(missing))
    urls = URL_RE.findall(text)
    if len(set(urls)) < contract.get("min_urls", 0):
        failures.append(
            f"insufficient source URLs: {len(set(urls))} < {contract['min_urls']}"
        )
    for marker in INTERNAL_MARKERS:
        if marker.lower() in lowered:
            failures.append(f"internal marker leaked: {marker}")
    for pattern in contract.get("forbidden_patterns", []):
        if re.search(pattern, text, flags=re.I):
            failures.append(f"forbidden pattern: {pattern}")
    for phrase in contract.get("required_phrases", []):
        if phrase.lower() not in lowered:
            failures.append(f"missing required phrase: {phrase}")
    if text.rstrip().endswith(("：", ":", "、", "-", "|")):
        failures.append("response appears truncated")
    if text.count("```") % 2:
        failures.append("unclosed code fence")
    last_lines = [
        line.strip() for line in text.rstrip().splitlines() if line.strip()
    ]
    if last_lines and re.match(r"^#{1,6}\s+", last_lines[-1]):
        failures.append("response ends with an empty heading")
    if contract.get("answer_first_any"):
        prefix = text[: contract.get("answer_first_chars", 250)].lower()
        aliases = contract["answer_first_any"]
        if not any(alias.lower() in prefix for alias in aliases):
            failures.append("direct answer missing from opening")
    return {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "stats": {
            "chars": length,
            "urls": len(set(urls)),
            "required_sections": len(contract.get("required_any", [])),
            "missing_sections": len(missing),
        },
        "repair_instructions": [
            "Use only facts and URLs already present in the evidence package.",
            "Do not add assumptions, thresholds, probabilities or new facts.",
            *failures,
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("response")
    parser.add_argument("contract")
    parser.add_argument("--output")
    parser.add_argument("--report-json")
    args = parser.parse_args()
    text = Path(args.response).read_text(encoding="utf-8")
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    result = validate(text, contract)
    if args.report_json:
        report = json.loads(Path(args.report_json).read_text(encoding="utf-8"))
        result["failures"].extend(validate_report(report))
        result["passed"] = not result["failures"]
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
