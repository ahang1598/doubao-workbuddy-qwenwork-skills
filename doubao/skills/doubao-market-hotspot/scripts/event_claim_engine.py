#!/usr/bin/env python3
"""Deterministic event evidence timing, transmission graph, and domain arithmetic engine."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 1_048_576
MAX_ITEMS_PER_LIST = 500

EVENT_STATUSES = {
    "rumor",
    "proposed",
    "announced",
    "adopted",
    "effective",
    "superseded",
    "repealed",
}
PRE_EFFECTIVE_STATUSES = {"rumor", "proposed", "announced", "adopted"}
INACTIVE_STATUSES = {"superseded", "repealed"}
CONFIRMING_LEGAL_STATUSES = {"announced", "adopted", "effective"}
CONFLICTING_LEGAL_STATUSES = {"superseded", "repealed"}


class InputError(ValueError):
    """Raised when the JSON input is structurally or numerically invalid."""


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise InputError(f"{name} must be an array")
    if len(value) > MAX_ITEMS_PER_LIST:
        raise InputError(f"{name} exceeds max length {MAX_ITEMS_PER_LIST}")
    return value


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InputError(f"{name} must be a finite number")
    return numeric


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InputError(f"{field} must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise InputError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _optional_time(value: Any, field: str) -> datetime | None:
    return None if value is None else _parse_time(value, field)


def _evidence_time(source: Any, field: str) -> datetime | None:
    if source is None or isinstance(source, str):
        return None
    if not isinstance(source, dict):
        raise InputError(f"{field} must be a string or object when provided")
    for key in ("published_at", "observed_at", "as_of", "timestamp"):
        if source.get(key) is not None:
            return _parse_time(source[key], f"{field}.{key}")
    return None


def _event_gate(status: str) -> dict[str, Any]:
    return {
        "status": status,
        "event_is_confirmed": status in {"announced", "adopted", "effective"},
        "event_is_currently_effective": status == "effective",
        "event_is_inactive": status in INACTIVE_STATUSES,
        "may_describe_as_fact": status in {"announced", "adopted", "effective"},
        "may_model_proposal_conditionally": status in PRE_EFFECTIVE_STATUSES,
        "may_quantify_current_event": status == "effective",
        "reason": {
            "rumor": "rumor_requires_confirmation",
            "proposed": "proposal_is_not_adopted_or_effective",
            "announced": "announcement_is_not_yet_effective",
            "adopted": "adopted_event_is_not_yet_effective",
            "effective": "event_is_effective",
            "superseded": "event_has_been_superseded",
            "repealed": "event_has_been_repealed",
        }[status],
    }


def _claim_effect_at_freeze(
    claim: dict[str, Any], event_status: str, freeze: datetime
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    source = claim.get("source")
    source_time = _evidence_time(source, "claim.source")
    if source_time is not None and source_time > freeze:
        return "unknown", ["source_after_as_of"]
    if isinstance(source, dict) and source.get("coverage_end") is not None and source_time is None:
        return "unknown", ["coverage_period_without_published_at"]

    effective_from = _optional_time(
        claim.get("effective_from"), "claim.effective_from"
    )
    if effective_from is not None and effective_from > freeze:
        return "unknown", ["effective_from_after_as_of"]

    supported = claim.get("supported")
    if supported not in (True, False, None):
        raise InputError("claim.supported must be true, false, or null")
    if supported is not True:
        return "unknown", ["unsupported" if supported is False else "support_unknown"]

    legal_status = claim.get("legal_status")
    if legal_status is not None:
        if not isinstance(legal_status, str) or legal_status not in EVENT_STATUSES:
            raise InputError(
                "claim.legal_status must be one of the supported event statuses"
            )
        if legal_status in CONFLICTING_LEGAL_STATUSES and event_status not in INACTIVE_STATUSES:
            return "conflict", [f"claim_legal_status_{legal_status}"]
        if event_status == "effective" and legal_status in PRE_EFFECTIVE_STATUSES:
            return "conflict", [f"claim_legal_status_{legal_status}"]
        if event_status in INACTIVE_STATUSES and legal_status in CONFIRMING_LEGAL_STATUSES:
            return "conflict", [f"event_is_{event_status}"]

    return "valid", reasons


def _evaluate_claims(
    raw_claims: list[Any], event_status: str, freeze: datetime
) -> dict[str, Any]:
    seen: set[str] = set()
    buckets: dict[str, list[dict[str, Any]]] = {
        "valid": [],
        "unknown": [],
        "conflict": [],
    }
    for index, raw in enumerate(raw_claims):
        claim = _require_object(raw, f"claims[{index}]")
        claim_id = claim.get("id")
        claim_type = claim.get("claim_type")
        if not isinstance(claim_id, str) or not claim_id:
            raise InputError(f"claims[{index}].id must be a non-empty string")
        if claim_id in seen:
            raise InputError(f"duplicate claim id: {claim_id}")
        seen.add(claim_id)
        if not isinstance(claim_type, str) or not claim_type:
            raise InputError(
                f"claims[{index}].claim_type must be a non-empty string"
            )
        if claim.get("critical", False) not in (True, False):
            raise InputError(f"claims[{index}].critical must be boolean")
        source_role = claim.get("source_role")
        if source_role is not None and not isinstance(source_role, str):
            raise InputError(f"claims[{index}].source_role must be a string")

        state, reasons = _claim_effect_at_freeze(claim, event_status, freeze)
        buckets[state].append(
            {
                "id": claim_id,
                "claim_type": claim_type,
                "critical": claim.get("critical", False),
                "source_role": source_role,
                "reasons": reasons,
            }
        )
    return {
        "valid_claims": buckets["valid"],
        "unknown_claims": buckets["unknown"],
        "conflicting_claims": buckets["conflict"],
    }


def _validate_transmission(raw: Any) -> dict[str, Any]:
    transmission = _require_object(raw, "transmission")
    raw_nodes = _require_list(transmission.get("nodes", []), "transmission.nodes")
    raw_edges = _require_list(transmission.get("edges", []), "transmission.edges")
    node_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, raw_node in enumerate(raw_nodes):
        node = _require_object(raw_node, f"transmission.nodes[{index}]")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise InputError(
                f"transmission.nodes[{index}].id must be a non-empty string"
            )
        if node_id in node_ids:
            raise InputError(f"duplicate transmission node id: {node_id}")
        node_ids.add(node_id)
        nodes.append(node)

    normalized_edges: list[dict[str, Any]] = []
    adjacency = {node_id: set() for node_id in node_ids}
    indegree = {node_id: 0 for node_id in node_ids}
    for index, raw_edge in enumerate(raw_edges):
        edge = _require_object(raw_edge, f"transmission.edges[{index}]")
        source = edge.get("from", edge.get("source"))
        target = edge.get("to", edge.get("target"))
        if not isinstance(source, str) or not isinstance(target, str):
            raise InputError(
                f"transmission.edges[{index}] requires string from/to endpoints"
            )
        edge_result: dict[str, Any] = {"index": index, "from": source, "to": target}
        missing = [
            endpoint
            for endpoint in (source, target)
            if endpoint not in node_ids
        ]
        if missing:
            errors.append(
                {
                    **edge_result,
                    "code": "UNKNOWN_EDGE_ENDPOINT",
                    "missing_node_ids": sorted(set(missing)),
                }
            )
            edge_result["valid"] = False
        else:
            edge_result["valid"] = True
            if target not in adjacency[source]:
                adjacency[source].add(target)
                indegree[target] += 1
        normalized_edges.append(edge_result)

    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if bool(node_ids) and visited != len(node_ids):
        errors.append({"code": "TRANSMISSION_CYCLE"})

    connected: set[str] = set()
    if node_ids:
        undirected = {node_id: set() for node_id in node_ids}
        for source, targets in adjacency.items():
            for target in targets:
                undirected[source].add(target)
                undirected[target].add(source)
        pending = [next(iter(node_ids))]
        while pending:
            current = pending.pop()
            if current in connected:
                continue
            connected.add(current)
            pending.extend(undirected[current] - connected)
    disconnected = sorted(node_ids - connected)
    if disconnected:
        errors.append(
            {
                "code": "DISCONNECTED_TRANSMISSION_NODES",
                "node_ids": disconnected,
            }
        )

    return {
        "valid": not errors,
        "node_count": len(nodes),
        "edge_count": len(normalized_edges),
        "nodes": nodes,
        "edges": normalized_edges,
        "errors": errors,
    }


def _market_kind(item: dict[str, Any]) -> str | None:
    raw = item.get("evidence_type", item.get("type", item.get("role")))
    if raw is None and item.get("pre_event_expectation") is True:
        return "pre_event_expectation"
    if raw is None and (
        item.get("comparable") is True or item.get("is_comparable") is True
    ):
        return "comparable_market_evidence"
    if not isinstance(raw, str):
        return None
    normalized = raw.casefold().replace("-", "_").replace(" ", "_")
    if normalized in {
        "pre_event_expectation",
        "event_expectation",
        "expectation",
        "consensus",
    }:
        return "pre_event_expectation"
    if normalized in {
        "comparable_market",
        "comparable_market_evidence",
        "market_comparable",
        "comparable",
    }:
        return "comparable_market_evidence"
    return normalized


def _evaluate_market(raw_market: list[Any], freeze: datetime) -> dict[str, Any]:
    usable: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_market):
        item = _require_object(raw, f"market_evidence[{index}]")
        item_id = item.get("id", f"market_evidence[{index}]")
        source_time = _evidence_time(
            item.get("source", item), f"market_evidence[{index}]"
        )
        reason = None
        if source_time is not None and source_time > freeze:
            reason = "source_after_as_of"
        elif item.get("supported", True) is not True:
            reason = "unsupported"
        kind = _market_kind(item)
        if kind == "comparable_market_evidence" and (
            item.get("comparable") is False or item.get("is_comparable") is False
        ):
            reason = "not_comparable"
        normalized: dict[str, Any] = {"id": item_id, "evidence_type": kind}
        if reason:
            normalized["reason"] = reason
            excluded.append(normalized)
        else:
            usable.append(normalized)

    has_expectation = any(
        item["evidence_type"] == "pre_event_expectation" for item in usable
    )
    has_comparable = any(
        item["evidence_type"] == "comparable_market_evidence" for item in usable
    )
    missing = []
    if not has_expectation:
        missing.append("pre_event_expectation")
    if not has_comparable:
        missing.append("comparable_market_evidence")
    return {
        "usable_evidence": usable,
        "excluded_evidence": excluded,
        "has_pre_event_expectation": has_expectation,
        "has_comparable_market_evidence": has_comparable,
        "can_assess_priced_in": not missing,
        "missing_requirements": missing,
    }


def evaluate_event_claims(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one generic event package at its evidence freeze point."""
    payload = _require_object(payload, "input")
    event = _require_object(payload.get("event"), "event")
    status = event.get("status")
    if status not in EVENT_STATUSES:
        raise InputError(
            "event.status must be one of: " + ", ".join(sorted(EVENT_STATUSES))
        )
    freeze = _parse_time(event.get("as_of"), "event.as_of")
    jurisdiction = event.get("jurisdiction")
    if not isinstance(jurisdiction, str) or not jurisdiction:
        raise InputError("event.jurisdiction must be a non-empty string")
    if event.get("source") is not None and not isinstance(
        event["source"], (str, dict)
    ):
        raise InputError("event.source must be a string or object")
    event_source_time = _evidence_time(event.get("source"), "event.source")
    event_source_after_freeze = (
        event_source_time is not None and event_source_time > freeze
    )

    claims = _evaluate_claims(
        _require_list(payload.get("claims", []), "claims"), status, freeze
    )
    transmission = _validate_transmission(payload.get("transmission", {}))
    market = _evaluate_market(
        _require_list(payload.get("market_evidence", []), "market_evidence"),
        freeze,
    )
    gate = _event_gate(status)
    unresolved_critical = [
        claim
        for key in ("unknown_claims", "conflicting_claims")
        for claim in claims[key]
        if claim["critical"]
    ]
    can_quantify = (
        gate["may_quantify_current_event"]
        and not event_source_after_freeze
        and not unresolved_critical
        and transmission["valid"]
        and transmission["node_count"] > 0
    )
    unknowns: list[dict[str, Any]] = [
        {
            "code": "CLAIM_UNRESOLVED",
            "claim_id": claim["id"],
            "critical": claim["critical"],
            "reasons": claim["reasons"],
        }
        for claim in claims["unknown_claims"]
    ]
    if event_source_after_freeze:
        unknowns.append({"code": "EVENT_SOURCE_AFTER_AS_OF"})
    if not market["can_assess_priced_in"]:
        unknowns.append(
            {
                "code": "PRICED_IN_EVIDENCE_INCOMPLETE",
                "missing": market["missing_requirements"],
            }
        )
    if not transmission["node_count"]:
        unknowns.append({"code": "TRANSMISSION_GRAPH_EMPTY"})

    errors = list(transmission["errors"])
    errors.extend(
        {
            "code": "CLAIM_CONFLICT",
            "claim_id": claim["id"],
            "reasons": claim["reasons"],
        }
        for claim in claims["conflicting_claims"]
    )
    return {
        "event": {
            "status": status,
            "as_of": event["as_of"],
            "jurisdiction": jurisdiction,
            "source": event.get("source"),
        },
        "event_capability_gate": gate,
        **claims,
        "can_quantify_event": can_quantify,
        "can_assess_priced_in": market["can_assess_priced_in"],
        "priced_in_evidence": market,
        "transmission_validation": transmission,
        "unknowns": unknowns,
        "errors": errors,
    }


def evaluate_calculations(payload: dict[str, Any]) -> dict[str, Any]:
    """Perform deterministic financial, unit, FX, reconciliation, and scenario math."""
    payload = _require_object(payload, "input")
    errors: list[dict[str, Any]] = []
    changes_out: list[dict[str, Any]] = []
    shares_out: list[dict[str, Any]] = []
    reconciliations_out: list[dict[str, Any]] = []
    fx_out: list[dict[str, Any]] = []
    scenario_out: dict[str, Any] | None = None

    for idx, raw in enumerate(_require_list(payload.get("changes", []), "changes")):
        item = _require_object(raw, f"changes[{idx}]")
        item_id = str(item.get("id") or f"change_{idx}")
        start = _require_number(item.get("start"), f"changes[{idx}].start")
        end = _require_number(item.get("end"), f"changes[{idx}].end")
        diff = end - start
        direction = "up" if diff > 1e-12 else "down" if diff < -1e-12 else "flat"
        pct = None if abs(start) < 1e-12 else round(diff / abs(start) * 100.0, 4)
        row: dict[str, Any] = {
            "id": item_id,
            "start": start,
            "end": end,
            "abs_change": round(diff, 6),
            "pct_change": pct,
            "direction": direction,
            "unit": item.get("unit", ""),
        }
        if item.get("is_rate_pct") is True:
            row["bps_change"] = round(diff * 100.0, 2)
        changes_out.append(row)

    for idx, raw in enumerate(_require_list(payload.get("shares", []), "shares")):
        item = _require_object(raw, f"shares[{idx}]")
        item_id = str(item.get("id") or f"share_{idx}")
        part = _require_number(item.get("part"), f"shares[{idx}].part")
        whole = _require_number(item.get("whole"), f"shares[{idx}].whole")
        if whole <= 0:
            raise InputError(f"shares[{idx}].whole must be positive")
        strict_subset = bool(item.get("strict_subset", True))
        exceeds = strict_subset and (part < 0 or part > whole + 1e-9)
        if exceeds:
            errors.append(
                {
                    "code": "SUBSET_EXCEEDS_WHOLE",
                    "id": item_id,
                    "part": part,
                    "whole": whole,
                }
            )
        shares_out.append(
            {
                "id": item_id,
                "part": part,
                "whole": whole,
                "share_pct": round(part / whole * 100.0, 4),
                "valid_subset": not exceeds,
                "unit": item.get("unit", ""),
            }
        )

    for idx, raw in enumerate(
        _require_list(payload.get("reconciliations", []), "reconciliations")
    ):
        item = _require_object(raw, f"reconciliations[{idx}]")
        item_id = str(item.get("id") or f"reconcile_{idx}")
        total = _require_number(item.get("total"), f"reconciliations[{idx}].total")
        raw_parts = _require_list(item.get("parts", []), f"reconciliations[{idx}].parts")
        if not raw_parts:
            raise InputError(f"reconciliations[{idx}].parts must be non-empty")
        parts = [
            _require_number(val, f"reconciliations[{idx}].parts[{p_idx}]")
            for p_idx, val in enumerate(raw_parts)
        ]
        tolerance = _require_number(
            item.get("tolerance", 1e-6), f"reconciliations[{idx}].tolerance"
        )
        if tolerance < 0:
            raise InputError(f"reconciliations[{idx}].tolerance must be non-negative")
        summed = sum(parts)
        diff = summed - total
        matched = abs(diff) <= tolerance
        if not matched:
            errors.append(
                {
                    "code": "SUM_MISMATCH",
                    "id": item_id,
                    "expected_total": total,
                    "computed_sum": round(summed, 6),
                    "diff": round(diff, 6),
                }
            )
        reconciliations_out.append(
            {
                "id": item_id,
                "expected_total": total,
                "computed_sum": round(summed, 6),
                "diff": round(diff, 6),
                "reconciled": matched,
            }
        )

    for idx, raw in enumerate(
        _require_list(payload.get("fx_conversions", []), "fx_conversions")
    ):
        item = _require_object(raw, f"fx_conversions[{idx}]")
        item_id = str(item.get("id") or f"fx_{idx}")
        amount = _require_number(item.get("amount"), f"fx_conversions[{idx}].amount")
        fx_rate = _require_number(item.get("fx_rate"), f"fx_conversions[{idx}].fx_rate")
        if fx_rate <= 0:
            raise InputError(f"fx_conversions[{idx}].fx_rate must be positive")
        from_ccy = str(item.get("from_currency") or "").strip()
        to_ccy = str(item.get("to_currency") or "").strip()
        if not from_ccy or not to_ccy:
            raise InputError(
                f"fx_conversions[{idx}] requires non-empty from_currency and to_currency"
            )
        per_unit = str(item.get("per_unit") or "").strip()
        converted = amount * fx_rate
        fx_out.append(
            {
                "id": item_id,
                "amount": amount,
                "from_currency": from_ccy,
                "to_currency": to_ccy,
                "fx_rate": fx_rate,
                "converted_amount": round(converted, 6),
                "unit_label": f"{to_ccy}/{per_unit}" if per_unit else to_ccy,
            }
        )

    if payload.get("scenarios") is not None:
        scen_block = _require_object(payload["scenarios"], "scenarios")
        status = str(scen_block.get("event_status", "")).strip().lower()
        raw_rows = _require_list(scen_block.get("scenarios", []), "scenarios.scenarios")
        if status in {"rumor", "unconfirmed", "传闻", "未确认"}:
            scenario_out = {
                "can_quantify_event": False,
                "event_status": status,
                "reason": "unconfirmed events cannot enter probability-weighted return calculations",
                "scenario_names": [
                    row.get("name") for row in raw_rows if isinstance(row, dict)
                ],
            }
        elif status in {"confirmed", "official", "effective", "announced", "adopted", "已确认", "正式"}:
            current_val = _require_number(
                scen_block.get("current_value"), "scenarios.current_value"
            )
            if current_val <= 0 or not raw_rows:
                raise InputError(
                    "scenarios requires positive current_value and non-empty scenarios list"
                )
            rows = []
            prob_sum = 0.0
            expected_terminal = 0.0
            horizons: set[float] = set()
            for s_idx, s_raw in enumerate(raw_rows):
                s_obj = _require_object(s_raw, f"scenarios.scenarios[{s_idx}]")
                prob = _require_number(
                    s_obj.get("probability"), f"scenarios.scenarios[{s_idx}].probability"
                )
                term = _require_number(
                    s_obj.get("terminal_value"),
                    f"scenarios.scenarios[{s_idx}].terminal_value",
                )
                years = _require_number(
                    s_obj.get("years"), f"scenarios.scenarios[{s_idx}].years"
                )
                if not 0.0 <= prob <= 1.0 or term < 0.0 or years <= 0.0:
                    raise InputError(
                        f"scenarios.scenarios[{s_idx}] requires probability in [0,1], non-negative terminal_value, positive years"
                    )
                hpr = term / current_val - 1.0
                ann = (term / current_val) ** (1.0 / years) - 1.0 if term > 0 else -1.0
                rows.append(
                    {
                        "name": str(s_obj.get("name") or f"scenario_{s_idx}"),
                        "probability": prob,
                        "years": years,
                        "terminal_value": term,
                        "holding_period_return": round(hpr, 6),
                        "annualized_return": round(ann, 6),
                    }
                )
                prob_sum += prob
                expected_terminal += prob * term
                horizons.add(years)
            if abs(prob_sum - 1.0) > 1e-6:
                raise InputError("scenario probabilities must sum to 1.0 (+/- 1e-6)")
            scenario_out = {
                "can_quantify_event": True,
                "event_status": status,
                "probability_sum": round(prob_sum, 6),
                "expected_terminal_value": round(expected_terminal, 6),
                "expected_holding_period_return": (
                    round(expected_terminal / current_val - 1.0, 6)
                    if len(horizons) == 1
                    else None
                ),
                "aggregation_note": (
                    "uniform_horizon"
                    if len(horizons) == 1
                    else "returns_not_aggregated_across_different_horizons"
                ),
                "scenarios": rows,
            }
        else:
            raise InputError(
                "scenarios.event_status must be confirmed/effective or rumor/unconfirmed"
            )

    return {
        "mode": "calc",
        "valid": not errors,
        "changes": changes_out,
        "shares": shares_out,
        "reconciliations": reconciliations_out,
        "fx_conversions": fx_out,
        "scenarios": scenario_out,
        "errors": errors,
    }


def _read_raw_input(source: str) -> str:
    if source == "-":
        raw = sys.stdin.read()
    elif source.lstrip().startswith(("{", "[")):
        raw = source
    else:
        path = Path(source)
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise InputError(f"input file exceeds {MAX_INPUT_BYTES} bytes")
        raw = path.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > MAX_INPUT_BYTES:
        raise InputError(f"input payload exceeds {MAX_INPUT_BYTES} bytes")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate event evidence timing/transmission or perform deterministic domain calculations."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input JSON file path, inline JSON string, or - for stdin (default).",
    )
    parser.add_argument(
        "--mode",
        choices=("claims", "calc"),
        default="claims",
        help="Evaluation mode: 'claims' (default) or 'calc' for domain arithmetic.",
    )
    parser.add_argument("--output", help="Optional output JSON file path.")
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print emitted JSON."
    )
    args = parser.parse_args(argv)
    try:
        raw = _read_raw_input(args.input)
        payload = json.loads(raw)
        result = (
            evaluate_calculations(payload)
            if args.mode == "calc"
            else evaluate_event_claims(payload)
        )
        text = (
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2 if args.pretty else None,
                sort_keys=args.pretty,
            )
            + "\n"
        )
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    except (OSError, json.JSONDecodeError, InputError) as error:
        print(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
