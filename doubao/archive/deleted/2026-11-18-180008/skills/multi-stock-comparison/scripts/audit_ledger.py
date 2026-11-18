#!/usr/bin/env python3
"""Audit a comparison evidence ledger for common finance research errors."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


LAYERS = {"group", "segment", "product"}
METRIC_TYPES = {"flow", "stock", "ratio", "other"}
EVIDENCE_TYPES = {
    "company_disclosure",
    "third_party_fact",
    "consensus",
    "single_institution",
    "calculation",
    "assumption",
    "inference",
    "to_verify",
}
EXTERNAL_EVIDENCE_TYPES = {
    "company_disclosure",
    "third_party_fact",
    "consensus",
    "single_institution",
}
REQUIRED_OBSERVATION_FIELDS = {
    "id",
    "company",
    "metric",
    "value",
    "period",
    "metric_type",
    "unit",
    "layer",
    "evidence",
    "source",
    "source_date",
}
BANNED_CALCULATION_SOURCE_RE = re.compile(
    r"author[ _-]?calculation|作者计算|脚本计算|script[ _-]?calculation|\.py\b",
    re.IGNORECASE,
)


def load_payload(path: str) -> dict[str, Any]:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def add(items: list[dict[str, str]], code: str, message: str) -> None:
    items.append({"code": code, "message": message})


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    as_of_value = payload.get("as_of")
    if not as_of_value:
        add(errors, "ROOT_AS_OF_MISSING", "Root field 'as_of' is required.")
    as_of = parse_date(as_of_value)
    if as_of_value and as_of is None:
        add(errors, "ROOT_AS_OF_INVALID", "Root field 'as_of' must use YYYY-MM-DD.")

    observations = payload.get("observations")
    comparisons = payload.get("comparisons", [])
    if not isinstance(observations, list) or not observations:
        add(errors, "OBSERVATIONS_MISSING", "'observations' must be a non-empty list.")
        observations = []
    if not isinstance(comparisons, list):
        add(errors, "COMPARISONS_INVALID", "'comparisons' must be a list.")
        comparisons = []

    by_id: dict[str, dict[str, Any]] = {}
    for index, obs in enumerate(observations):
        label = f"observation[{index}]"
        if not isinstance(obs, dict):
            add(errors, "OBSERVATION_INVALID", f"{label} must be an object.")
            continue
        missing = sorted(field for field in REQUIRED_OBSERVATION_FIELDS if obs.get(field) in (None, ""))
        if missing:
            add(errors, "OBSERVATION_FIELDS_MISSING", f"{label} missing: {', '.join(missing)}.")
        obs_id = obs.get("id")
        if obs_id in by_id:
            add(errors, "DUPLICATE_ID", f"Duplicate observation id: {obs_id}.")
        elif obs_id:
            by_id[str(obs_id)] = obs

        if obs.get("layer") not in LAYERS:
            add(errors, "LAYER_INVALID", f"{label} has invalid layer '{obs.get('layer')}'.")
        if obs.get("metric_type") not in METRIC_TYPES:
            add(errors, "METRIC_TYPE_INVALID", f"{label} has invalid metric_type '{obs.get('metric_type')}'.")
        if obs.get("evidence") not in EVIDENCE_TYPES:
            add(errors, "EVIDENCE_INVALID", f"{label} has invalid evidence '{obs.get('evidence')}'.")
        value = obs.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            add(errors, "VALUE_INVALID", f"{label} value must be numeric.")
        elif not math.isfinite(float(value)):
            add(errors, "VALUE_NOT_FINITE", f"{label} value must be finite.")
        source_date_value = obs.get("source_date")
        source_date = parse_date(source_date_value)
        if source_date_value and source_date is None:
            add(errors, "SOURCE_DATE_INVALID", f"{label} source_date must use YYYY-MM-DD.")
        elif as_of and source_date and source_date > as_of:
            add(errors, "SOURCE_DATE_AFTER_AS_OF", f"{label} source_date is later than root as_of.")
        if BANNED_CALCULATION_SOURCE_RE.search(str(obs.get("source", ""))):
            add(
                errors,
                "CALCULATION_AS_SOURCE",
                f"{label} uses an author calculation or script name as source; cite external inputs instead.",
            )
        if obs.get("evidence") == "calculation":
            if not obs.get("formula"):
                add(errors, "FORMULA_MISSING", f"{label} is a calculation but has no formula.")
            if not isinstance(obs.get("input_ids"), list) or not obs.get("input_ids"):
                add(errors, "CALCULATION_INPUTS_MISSING", f"{label} calculation requires non-empty input_ids.")
        if obs.get("evidence") == "consensus":
            for field in ("provider", "snapshot_date", "coverage_count"):
                if obs.get(field) in (None, ""):
                    add(errors, "CONSENSUS_METADATA_MISSING", f"{label} consensus missing '{field}'.")
        if obs.get("evidence") in {"single_institution", "assumption", "inference", "to_verify"}:
            add(warnings, "LOWER_CERTAINTY_EVIDENCE", f"{label} uses {obs.get('evidence')}; label it explicitly in output.")
        if obs.get("metric_type") in {"flow", "stock"} and not obs.get("currency"):
            add(warnings, "CURRENCY_MISSING", f"{label} has no currency; confirm the metric is non-monetary.")

    for index, obs in enumerate(observations):
        if not isinstance(obs, dict) or obs.get("evidence") != "calculation":
            continue
        label = f"observation[{index}]"
        input_ids = obs.get("input_ids")
        if not isinstance(input_ids, list):
            continue
        unknown_inputs = [str(item) for item in input_ids if str(item) not in by_id]
        if unknown_inputs:
            add(
                errors,
                "CALCULATION_INPUT_UNKNOWN",
                f"{label} references unknown input_ids: {', '.join(unknown_inputs)}.",
            )
        non_external_inputs = [
            str(item)
            for item in input_ids
            if str(item) in by_id and by_id[str(item)].get("evidence") not in EXTERNAL_EVIDENCE_TYPES
        ]
        if non_external_inputs:
            add(
                errors,
                "CALCULATION_INPUT_NOT_EXTERNAL",
                f"{label} input_ids must point to external evidence: {', '.join(non_external_inputs)}.",
            )
        self_id = str(obs.get("id", ""))
        if self_id and self_id in {str(item) for item in input_ids}:
            add(errors, "CALCULATION_SELF_REFERENCE", f"{label} must not reference itself.")

    comparison_ids: set[str] = set()
    for index, comparison in enumerate(comparisons):
        label = f"comparison[{index}]"
        if not isinstance(comparison, dict):
            add(errors, "COMPARISON_INVALID", f"{label} must be an object.")
            continue
        comparison_id = str(comparison.get("id", "")).strip()
        if not comparison_id:
            add(errors, "COMPARISON_ID_MISSING", f"{label} requires a non-empty id.")
        elif comparison_id in comparison_ids:
            add(errors, "COMPARISON_ID_DUPLICATE", f"Duplicate comparison id: {comparison_id}.")
        else:
            comparison_ids.add(comparison_id)
        ids = comparison.get("observation_ids")
        if not isinstance(ids, list) or len(ids) < 2:
            add(errors, "COMPARISON_IDS_MISSING", f"{label} needs at least two observation_ids.")
            continue
        missing_ids = [str(obs_id) for obs_id in ids if str(obs_id) not in by_id]
        if missing_ids:
            add(errors, "COMPARISON_ID_UNKNOWN", f"{label} references unknown ids: {', '.join(missing_ids)}.")
            continue

        selected = [by_id[str(obs_id)] for obs_id in ids]
        mismatches: list[str] = []
        for field in ("metric", "metric_type", "layer"):
            values = {str(obs.get(field)) for obs in selected}
            if len(values) > 1:
                mismatches.append(f"{field}={sorted(values)}")
        periods = {str(obs.get("period")) for obs in selected}
        if len(periods) > 1:
            mismatches.append(f"period={sorted(periods)}")
        units = {str(obs.get("unit")) for obs in selected}
        if len(units) > 1:
            mismatches.append(f"unit={sorted(units)}")

        currencies = {str(obs.get("currency")) for obs in selected if obs.get("currency")}
        if len(currencies) > 1 and not comparison.get("normalized_currency"):
            mismatches.append(f"currency={sorted(currencies)} without normalized_currency")

        if mismatches:
            mismatch_text = "; ".join(mismatches)
            if comparison.get("allow_mismatch"):
                if comparison.get("rationale"):
                    add(warnings, "COMPARISON_MISMATCH_ALLOWED", f"{label}: {mismatch_text}. Rationale supplied.")
                else:
                    add(errors, "MISMATCH_RATIONALE_MISSING", f"{label}: {mismatch_text}; allow_mismatch requires rationale.")
            else:
                add(errors, "COMPARISON_MISMATCH", f"{label}: {mismatch_text}.")

    return {
        "ok": not errors,
        "summary": {
            "observations": len(observations),
            "comparisons": len(comparisons),
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "errors": errors,
        "warnings": warnings,
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "PASS" if report["ok"] else "FAIL",
        (
            f"observations={summary['observations']} comparisons={summary['comparisons']} "
            f"errors={summary['errors']} warnings={summary['warnings']}"
        ),
    ]
    for severity in ("errors", "warnings"):
        for item in report[severity]:
            lines.append(f"{severity[:-1].upper()} [{item['code']}] {item['message']}")
    return "\n".join(lines)


def self_test() -> int:
    valid = {
        "as_of": "2026-07-22",
        "observations": [
            {
                "id": "a-revenue",
                "company": "公司 A",
                "metric": "revenue",
                "value": 100,
                "period": "2026Q2 TTM",
                "metric_type": "flow",
                "currency": "CNY",
                "unit": "bn",
                "layer": "group",
                "evidence": "company_disclosure",
                "source": "https://example.com/a",
                "source_date": "2026-07-20",
            },
            {
                "id": "a-margin",
                "company": "公司 A",
                "metric": "margin",
                "value": 0.2,
                "period": "2026Q2 TTM",
                "metric_type": "ratio",
                "unit": "%",
                "layer": "group",
                "evidence": "calculation",
                "source": "https://example.com/a",
                "source_date": "2026-07-20",
                "formula": "profit / revenue",
                "input_ids": ["a-revenue"],
            },
        ],
        "comparisons": [],
    }
    report = audit(valid)
    if not report["ok"]:
        raise AssertionError(report)
    invalid = json.loads(json.dumps(valid))
    invalid["observations"][1]["source"] = "audit_ledger.py 脚本计算"
    invalid["observations"][1].pop("input_ids")
    report = audit(invalid)
    codes = {item["code"] for item in report["errors"]}
    if not {"CALCULATION_AS_SOURCE", "CALCULATION_INPUTS_MISSING"}.issubset(codes):
        raise AssertionError(report)
    invalid_value = json.loads(json.dumps(valid))
    invalid_value["observations"][0]["value"] = "100"
    invalid_value["observations"][0]["source_date"] = "2026-07-23"
    report = audit(invalid_value)
    codes = {item["code"] for item in report["errors"]}
    if not {"VALUE_INVALID", "SOURCE_DATE_AFTER_AS_OF"}.issubset(codes):
        raise AssertionError(report)
    print("SELF_TEST_PASS", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", nargs="?", help="Path to ledger JSON, or '-' for stdin")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.ledger:
        parser.error("ledger is required unless --self-test is used")
    try:
        payload = load_payload(args.ledger)
        report = audit(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_text(report),
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
