#!/usr/bin/env python3
"""Offline arithmetic and eligibility checks on explicitly supplied inputs."""

import argparse
from collections import deque
from datetime import date, datetime
from decimal import Decimal, localcontext
from functools import wraps
from pathlib import Path

import input_guards as guards
from input_guards import Budget, LocalResourceLimit, number, within

ZERO = Decimal(0)
MAX_INPUT_BYTES = guards.MAX_INPUT_BYTES
MAX_ROWS = guards.MAX_ROWS
MAX_INPUT_NODES = guards.MAX_INPUT_NODES
MAX_ACTIVE_FUNDS = guards.MAX_ACTIVE_FUNDS
MAX_ACTIVE_PAYMENTS = guards.MAX_ACTIVE_PAYMENTS
MAX_MATCH_PAIRS = guards.MAX_MATCH_PAIRS
MAX_WORK_UNITS = guards.MAX_WORK_UNITS


def input_shape(data):
    guards.input_shape(data, max_bytes=MAX_INPUT_BYTES, max_rows=MAX_ROWS, max_nodes=MAX_INPUT_NODES)


def precise(function):
    @wraps(function)
    def invoke(*args, **kwargs):
        # Preserve small balances alongside large amounts, independent of the caller's context.
        with localcontext() as context:
            context.prec = 512
            return function(*args, **kwargs)
    return invoke


def checked_input(function):
    @wraps(function)
    @precise
    def invoke(data):
        input_shape(data)
        return function(data)
    return invoke


def fields(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError(f"expected fields {sorted(allowed)}; required {sorted(required)}")


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty text required")
    return value


def day(value):
    text(value, "date")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("dates must use YYYY-MM-DD")
    return parsed


def instant(value):
    text(value, "time")
    if len(value) == 10:
        return day(value)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamps require an explicit UTC offset")
    return parsed


def temporal_compare(left, right):
    a, b = instant(left), instant(right)
    if isinstance(a, datetime) == isinstance(b, datetime):
        return (a > b) - (a < b)
    ad = a.date() if isinstance(a, datetime) else a
    bd = b.date() if isinstance(b, datetime) else b
    # A date-only record on an intraday cutoff cannot prove event ordering.
    return ((ad > bd) - (ad < bd)) if ad != bd else None


def admission(evidence_reasons, business_reasons=(), missing_reasons=(), temporal_reasons=None):
    """Keep independent disqualifications; a summary never replaces its causes."""
    groups = {
        "evidence_reasons": list(dict.fromkeys(evidence_reasons)),
        "business_reasons": list(dict.fromkeys(business_reasons)),
        "missing_reasons": list(dict.fromkeys(missing_reasons)),
        "temporal_reasons": list(dict.fromkeys(temporal_reasons or ())),
    }
    reasons = list(dict.fromkeys(reason for values in groups.values() for reason in values))
    return {
        **groups, "evidence_status": next(iter(groups["evidence_reasons"]), "eligible"),
        "temporal_status": "not_evaluated" if temporal_reasons is None else "evaluated",
        "ineligibility_reasons": reasons, "eligibility_status": next(iter(reasons), "eligible"),
    }


def evidence_reasons(value, as_of):
    fields(value, {"source", "known_at", "effective_at", "status"})
    instant(as_of)
    for key in ("known_at", "effective_at"):
        if value.get(key) is not None:
            instant(value[key])
    if value.get("status") not in ("effective", "draft", "revoked", "unknown", None):
        raise ValueError("unsupported evidence status")
    reasons = []
    if not value.get("source"):
        reasons.append("unknown_source")
    else:
        text(value["source"], "source")
    if value.get("status") != "effective":
        reasons.append("not_effective")
    for key in ("known_at", "effective_at"):
        if value.get(key) is None:
            reasons.append(f"unknown_{key}")
            continue
        order = temporal_compare(value[key], as_of)
        if order is None:
            reasons.append(f"unknown_intraday_{key}")
        elif order > 0:
            reasons.append(f"post_cutoff_{key}")
    return reasons


def evidence(value, as_of):
    return next(iter(evidence_reasons(value, as_of)), "eligible")


def aggregate_admission(value, as_of):
    if value is None:
        return admission(["missing_evidence"])
    fields(value, {"source", "known_at", "effective_at", "status", "kind"})
    reasons = evidence_reasons({k: v for k, v in value.items() if k != "kind"}, as_of)
    if value.get("kind") != "fact":
        reasons.append("not_confirmed_fact")
    return admission(reasons)


def aggregate_evidence(value, as_of):
    return aggregate_admission(value, as_of)["evidence_status"]


def unique(rows):
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each row must be an object")
        key = text(row.get("id"), "id")
        if key in result:
            raise ValueError(f"duplicate record id: {key}")
        result[key] = row
    return result


def metadata(value):
    fields(value, {"scope", "currency", "unit"}, {"scope", "currency", "unit"})
    for key, item in value.items():
        text(item, key)
    return value


def window(value):
    required = {"start", "end", "include_start", "include_end"}
    fields(value, required, required)
    start, end = day(value["start"]), day(value["end"])
    if end <= start or any(type(value[k]) is not bool for k in ("include_start", "include_end")):
        raise ValueError("invalid explicit window")
    return start, end


def inside(value, interval):
    start, end = window(interval)
    when = day(value)
    return (when > start or (when == start and interval["include_start"])) and (
        when < end or (when == end and interval["include_end"]))


@checked_input
def cash(data):
    required = {"principal", "annual_rate", "rate_kind", "interest_days", "year_days",
                "fee_rate", "fixed_fee", "availability"}
    fields(data, required | {"occupancy"}, required)
    principal = number(data["principal"], "principal", positive=True)
    rate = number(data["annual_rate"], "annual_rate", signed=True)
    interest_days = number(data["interest_days"], "interest_days")
    year_days = number(data["year_days"], "year_days", positive=True)
    fee = principal * number(data["fee_rate"], "fee_rate") + number(data["fixed_fee"], "fixed_fee")
    if data["rate_kind"] not in ("gross", "net"):
        raise ValueError("rate_kind must be gross or net")
    if data["rate_kind"] == "net" and fee != 0:
        raise ValueError("net rate with additional fees is ambiguous; normalize the fee basis first")
    quoted_interest = principal * rate * interest_days / year_days
    net = quoted_interest - fee
    fields(data["availability"], {"trading_day", "withdrawal_day"},
           {"trading_day", "withdrawal_day"})
    availability = {k: number(v, k) if v is not None else None
                    for k, v in data["availability"].items()}
    trading, withdrawal = availability["trading_day"], availability["withdrawal_day"]
    if trading is not None and withdrawal is not None and withdrawal < trading:
        raise ValueError("withdrawal before trading availability requires a separate product model")
    result = {
        "quoted_interest": quoted_interest, "rate_kind": data["rate_kind"], "fee": fee,
        "net_interest": net, "interest_days": interest_days, "interest_year_days": year_days,
        "availability": availability, "occupancy_days": None, "net_simple_annual_rate": None,
        "unknowns": [], "formula": "net = principal * annual_rate * interest_days / year_days - fee",
    }
    occupancy = data.get("occupancy")
    if occupancy is None:
        result["unknowns"].append("occupancy purpose/start/end/capital/year basis not provided")
        return result
    keys = {"purpose", "start_day", "end_day", "capital_base", "year_days", "basis_note"}
    fields(occupancy, keys, keys)
    if occupancy["purpose"] not in ("withdrawal", "trading", "custom"):
        raise ValueError("unknown occupancy purpose")
    text(occupancy["basis_note"], "occupancy basis_note")
    result["occupancy_basis"] = occupancy
    parsed = {k: None if occupancy[k] is None else number(
        occupancy[k], "occupancy/" + k, signed=k in ("start_day", "end_day"),
        positive=k in ("capital_base", "year_days"))
        for k in ("start_day", "end_day", "capital_base", "year_days")}
    if any(v is None for v in parsed.values()):
        result["unknowns"].append("incomplete occupancy basis; never substitute interest_days")
        return result
    start, end = parsed["start_day"], parsed["end_day"]
    elapsed = end - start
    if elapsed <= 0:
        raise ValueError("occupancy must be positive")
    if occupancy["purpose"] != "custom":
        endpoint = availability[occupancy["purpose"] + "_day"]
        if endpoint is None:
            result["unknowns"].append("selected availability endpoint is unknown")
            return result
        if endpoint != end:
            raise ValueError("occupancy end disagrees with selected availability; same origin required")
    capital, annual_days = parsed["capital_base"], parsed["year_days"]
    result.update(occupancy_days=elapsed, net_simple_annual_rate=net * annual_days / (capital * elapsed))
    return result


@checked_input
def debt_window(data):
    required = {"as_of", "meta", "window", "debts", "ledger_complete"}
    fields(data, required | {"reported", "ledger_complete_evidence"}, required)
    instant(data["as_of"])
    meta = metadata(data["meta"])
    window(data["window"])
    if type(data["ledger_complete"]) is not bool:
        raise ValueError("ledger_complete must be explicit boolean")
    completeness_proof = data.get("ledger_complete_evidence")
    completeness_reason = aggregate_evidence(completeness_proof, data["as_of"])
    confirmed_complete = data["ledger_complete"] and completeness_reason == "eligible"
    selected, excluded, unresolved, diagnostics = [], [], [], []
    total = ZERO
    keys = {"id", "meta", "amount", "maturity_date", "evidence"}
    for key, row in unique(data["debts"]).items():
        fields(row, keys, keys)
        amount = None if row["amount"] is None else number(row["amount"], "debts/" + key + "/amount")
        if row["maturity_date"] is not None:
            day(row["maturity_date"])
        row_meta = metadata(row["meta"])
        proof_reasons = evidence_reasons(row["evidence"], data["as_of"])
        reason = next(iter(proof_reasons), "eligible")
        business = ["different_scope"] if row_meta["scope"] != meta["scope"] else []
        missing = (["unknown_maturity_or_amount"]
                   if row["maturity_date"] is None or row["amount"] is None else [])
        temporal = None
        if not proof_reasons and not business and row["maturity_date"] is not None:
            temporal = [] if inside(row["maturity_date"], data["window"]) else ["outside_window"]
        diagnostics.append({"id": key, "evidence": row["evidence"],
                            "supplied_maturity_date": row["maturity_date"],
                            "admission": admission(proof_reasons, business, missing, temporal)})
        if row_meta["scope"] != meta["scope"]:
            excluded.append({"id": key, "reason": "different_scope"})
            continue
        if row_meta != meta:
            raise ValueError("currency/unit mismatch in the selected scope; no silent conversion")
        if reason != "eligible":
            unresolved.append({"id": key, "reason": reason})
            continue
        if row["maturity_date"] is None or row["amount"] is None:
            unresolved.append({"id": key, "reason": "unknown_maturity_or_amount"})
            continue
        if not inside(row["maturity_date"], data["window"]):
            excluded.append({"id": key, "reason": "outside_window"})
            continue
        total += amount
        selected.append({"id": key, "amount": amount, "maturity_date": row["maturity_date"],
                         "source": row["evidence"]["source"]})
    result = {"meta": meta, "window": data["window"], "included": selected, "excluded": excluded,
              "admission_diagnostics": diagnostics,
              "unresolved": unresolved, "known_legal_principal": total,
              "reconciliation_difference_ledger_minus_report": None,
              "reconciliation_status": "not_requested",
              "ledger_complete_confirmed": confirmed_complete,
              "aggregate_evidence": {"ledger_complete": completeness_proof},
              "aggregate_evidence_status": {"ledger_complete": completeness_reason},
              "aggregate_evidence_diagnostics": {
                  "ledger_complete": aggregate_admission(completeness_proof, data["as_of"])},
              "limitation": "Legal principal only; put scenarios and dated interest are separate."}
    reported = data.get("reported")
    if reported is not None:
        fields(reported, {"as_of", "meta", "window", "basis", "amount", "evidence"},
               {"as_of", "meta", "window", "basis", "amount"})
        reported_amount = None if reported["amount"] is None else number(reported["amount"], "reported/amount")
        report_proof = reported.get("evidence")
        report_reason = aggregate_evidence(report_proof, data["as_of"])
        result["aggregate_evidence"]["reported"] = report_proof
        result["aggregate_evidence_status"]["reported"] = report_reason
        result["aggregate_evidence_diagnostics"]["reported"] = aggregate_admission(report_proof, data["as_of"])
        metadata(reported["meta"])
        window(reported["window"])
        compatible = (temporal_compare(reported["as_of"], data["as_of"]) == 0
                      and reported["meta"] == meta and reported["window"] == data["window"]
                      and reported["basis"] == "legal_principal")
        if not compatible:
            result["reconciliation_status"] = "incompatible_basis"
        elif (unresolved or not confirmed_complete or reported["amount"] is None
              or report_reason != "eligible"):
            result["reconciliation_status"] = "incomplete"
        else:
            result["reconciliation_status"] = "comparable_not_accounting_proof"
            result["reconciliation_difference_ledger_minus_report"] = total - reported_amount
    return result


@precise
def max_cover(funds, demands, eligible, work=None):
    """Bipartite maximum flow; a balance can be spent only once across all dates."""
    if not isinstance(funds, dict) or not isinstance(demands, dict):
        raise ValueError("funds and demands must be registered objects")
    within(len(funds), MAX_ACTIVE_FUNDS, "active funds")
    within(len(demands), MAX_ACTIVE_PAYMENTS, "active payments")
    within(len(funds) * len(demands), MAX_MATCH_PAIRS, "fund/payment match pairs")
    input_shape([funds, demands])
    if not isinstance(eligible, (list, tuple)):
        raise ValueError("eligible links must be an explicit sequence")
    within(len(eligible), MAX_MATCH_PAIRS, "eligible pairs")
    work = work if work is not None else Budget(MAX_WORK_UNITS, "allocation work")
    work.spend(len(funds) + len(demands) + len(eligible))
    amounts = {}
    for kind, rows in (("fund", funds), ("demand", demands)):
        for key, row in rows.items():
            text(key, kind + " id")
            if not isinstance(row, dict) or "amount" not in row:
                raise ValueError("each graph record requires an amount")
            amounts[kind, key] = number(row["amount"], kind + " amount")
    links, seen = [], set()
    for pair in eligible:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("eligible link must contain fund and demand ids")
        fid, did = pair
        text(fid, "fund id")
        text(did, "demand id")
        if fid not in funds or did not in demands or (fid, did) in seen:
            raise ValueError("duplicate or dangling eligible link")
        seen.add((fid, did))
        links.append((fid, did))
    residual, original, adjacency = {}, {}, {}

    def edge(a, b, capacity):
        work.spend(1)
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)
        residual[a, b], residual[b, a] = capacity, ZERO
        original[a, b] = capacity

    source, sink = ("source",), ("sink",)
    adjacency[source], adjacency[sink] = [], []
    for fid in funds:
        edge(source, ("fund", fid), amounts["fund", fid])
    for did in demands:
        edge(("demand", did), sink, amounts["demand", did])
    for fid, did in links:
        edge(("fund", fid), ("demand", did), min(amounts["fund", fid], amounts["demand", did]))
    while True:
        parents = {source: None}
        queue = deque([source])
        while queue and sink not in parents:
            node = queue.popleft()
            work.spend(len(adjacency[node]))
            for nxt in adjacency[node]:
                if nxt not in parents and residual[node, nxt] > 0:
                    parents[nxt] = node
                    queue.append(nxt)
        if sink not in parents:
            break
        path, node = [], sink
        while parents[node] is not None:
            work.spend(1)
            previous = parents[node]
            path.append((previous, node))
            node = previous
        amount = min(residual[link] for link in path)
        work.spend(len(path) * 2)
        for a, b in path:
            residual[a, b] -= amount
            residual[b, a] += amount
    allocations = []
    work.spend(len(links))
    for fid, did in links:
        link = (("fund", fid), ("demand", did))
        amount = original[link] - residual[link]
        if amount:
            allocations.append({"fund_id": fid, "demand_id": did, "amount": amount})
    return allocations


@checked_input
def funding(data):
    required = {"as_of", "meta", "funds", "demands", "demand_schedule_complete"}
    fields(data, required | {"demand_schedule_complete_evidence", "registered_debt_ids"}, required)
    registered = (guards.string_set(data["registered_debt_ids"], "registered_debt_ids")
                  if "registered_debt_ids" in data else None)
    work = Budget(MAX_WORK_UNITS, "funding work")
    cutoff = instant(data["as_of"])
    cutoff_day = cutoff.date() if isinstance(cutoff, datetime) else cutoff
    meta = metadata(data["meta"])
    if type(data["demand_schedule_complete"]) is not bool:
        raise ValueError("demand_schedule_complete must be explicit boolean")
    completeness_proof = data.get("demand_schedule_complete_evidence")
    completeness_reason = aggregate_evidence(completeness_proof, data["as_of"])
    confirmed_complete = data["demand_schedule_complete"] and completeness_reason == "eligible"
    funds, demands, exclusions, diagnostics = {}, {}, [], []
    balances, payments = set(), set()
    fund_keys = {"id", "balance_id", "owner", "amount", "meta", "balance_at", "available_from",
                 "expires_on", "status", "restriction", "debt_ids", "purposes", "evidence"}
    demand_keys = {"id", "payment_id", "debt_id", "obligor", "amount", "meta", "due",
                   "purpose", "evidence"}
    for kind, rows, keys, target in (
        ("fund", data["funds"], fund_keys, funds), ("demand", data["demands"], demand_keys, demands),
    ):
        records = unique(rows)
        within(len(records), MAX_ACTIVE_FUNDS if kind == "fund" else MAX_ACTIVE_PAYMENTS,
               kind + " records")
        work.spend(len(records))
        for key, row in records.items():
            fields(row, keys, keys)
            date_fields = ("balance_at", "available_from", "expires_on") if kind == "fund" else ("due",)
            for name in date_fields:
                if row[name] is not None:
                    (instant if name == "balance_at" else day)(row[name])
            if (kind == "fund" and row["available_from"] is not None and row["expires_on"] is not None
                    and day(row["expires_on"]) < day(row["available_from"])):
                raise ValueError("fund expiry before availability")
            if metadata(row["meta"]) != meta:
                raise ValueError("fund/demand scope, currency and unit must match")
            dedup_key = text(row["balance_id" if kind == "fund" else "payment_id"], "economic id")
            seen = balances if kind == "fund" else payments
            if dedup_key in seen:
                raise ValueError("duplicate economic balance/payment across rows or periods")
            seen.add(dedup_key)
            proof_reasons = evidence_reasons(row["evidence"], data["as_of"])
            business, missing = [], []
            temporal = None if proof_reasons else []
            if row["amount"] is None:
                missing.append("unknown_amount")
            else:
                amount = number(row["amount"], "amount")
            if kind == "fund":
                text(row["owner"], "owner")
                if row["status"] not in ("available", "conditional", "planned", "frozen", "unknown"):
                    raise ValueError("unsupported funds status")
                guards.restrictions(row, registered, "funds/" + key)
                if row["status"] != "available":
                    business.append("not_available_at_cutoff")
                if row["restriction"] == "unknown":
                    business.append("unknown_restrictions")
                if row["balance_at"] is None:
                    missing.append("unconfirmed_cutoff_balance")
                if row["available_from"] is None:
                    missing.append("availability_not_confirmed_at_cutoff")
                if temporal is not None:
                    if row["balance_at"] is not None and temporal_compare(row["balance_at"], data["as_of"]) != 0:
                        temporal.append("unconfirmed_cutoff_balance")
                    if (row["available_from"] is not None
                            and temporal_compare(row["available_from"], data["as_of"]) not in (-1, 0)):
                        temporal.append("availability_not_confirmed_at_cutoff")
                    if row["expires_on"] is not None and day(row["expires_on"]) < cutoff_day:
                        temporal.append("expired_at_cutoff")
            else:
                for name in ("obligor", "debt_id", "purpose"):
                    text(row[name], name)
                if row["purpose"] not in guards.PURPOSES:
                    raise ValueError("demand.purpose: use only principal, put, interest")
                if registered is not None and row["debt_id"] not in registered:
                    raise ValueError("demand.debt_id: references unregistered debt")
                if row["due"] is None:
                    missing.append("unknown_payment_date")
                elif temporal is not None and temporal_compare(row["due"], data["as_of"]) != 1:
                    temporal.append("not_strictly_after_cutoff")
            state = admission(proof_reasons, business, missing, temporal)
            reason = state["eligibility_status"]
            diagnostics.append({
                "kind": kind, "id": key, "evidence": row["evidence"],
                "supplied_dates": {name: row[name] for name in date_fields}, "admission": state})
            if reason != "eligible":
                exclusions.append({"kind": kind, "id": key, "reason": reason})
            else:
                target[key] = {**row, "amount": amount}
    eligible, mismatches = [], []
    within(len(funds) * len(demands), MAX_MATCH_PAIRS, "fund/payment match pairs")
    work.spend(len(funds) * len(demands))
    work.spend(sum(len(f["debt_ids"]) + len(f["purposes"]) for f in funds.values()))
    allowed = {fid: (set(f["debt_ids"]), set(f["purposes"])) for fid, f in funds.items()}
    for fid, fund in funds.items():
        for did, demand in demands.items():
            reason = None
            if fund["owner"] != demand["obligor"]:
                reason = "different_obligor_no_transfer_evidence"
            elif fund["expires_on"] and day(demand["due"]) > day(fund["expires_on"]):
                reason = "fund_expired_before_payment"
            elif day(demand["due"]) < day(fund["available_from"]):
                reason = "payment_before_availability"
            elif fund["restriction"] == "dedicated" and (
                demand["debt_id"] not in allowed[fid][0] or demand["purpose"] not in allowed[fid][1]
            ):
                reason = "restricted_debt_or_purpose_mismatch"
            if reason:
                mismatches.append({"fund_id": fid, "demand_id": did, "reason": reason})
            else:
                eligible.append((fid, did))
    allocations = max_cover(funds, demands, eligible, work)
    work.spend(len(allocations) + len(funds) + len(demands))
    used = {fid: ZERO for fid in funds}
    paid = {did: ZERO for did in demands}
    for row in allocations:
        used[row["fund_id"]] += row["amount"]
        paid[row["demand_id"]] += row["amount"]
    uncovered = {did: row["amount"] - paid[did] for did, row in demands.items()}
    known_gap = sum(uncovered.values(), ZERO)
    complete = confirmed_complete and not any(e["kind"] == "demand" for e in exclusions)
    return {
        "meta": meta, "allocations": allocations, "uncovered_by_payment": uncovered,
        "unused_by_balance": {fid: row["amount"] - used[fid] for fid, row in funds.items()},
        "excluded": exclusions, "ineligible_matches": mismatches,
        "admission_diagnostics": diagnostics,
        "known_schedule_uncovered": known_gap,
        "demand_schedule_complete_confirmed": confirmed_complete,
        "aggregate_evidence": {"demand_schedule_complete": completeness_proof},
        "aggregate_evidence_status": {"demand_schedule_complete": completeness_reason},
        "aggregate_evidence_diagnostics": {
            "demand_schedule_complete": aggregate_admission(completeness_proof, data["as_of"])},
        "full_schedule_gap_against_confirmed_supplied_sources": known_gap if complete else None,
        "source_ids": {
            "funds": {key: row["evidence"]["source"] for key, row in funds.items()},
            "demands": {key: row["evidence"]["source"] for key, row in demands.items()},
        },
        "limitations": [
            "Conditional/planned sources are excluded, not proved nonexistent.",
            "Maximum coverage of supplied dated payments, not an execution instruction or priority optimum.",
            "No interest, put exercise, refinancing, intra-group transfers or future receipts are invented.",
            "Use one combined schedule across periods; do not restart the same opening balances.",
        ],
    }


def run(mode, data):
    return {"cash": cash, "debt-window": debt_window, "funding": funding}[mode](data)


def encode(value):
    return guards.encode(value, max_bytes=MAX_INPUT_BYTES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("cash", "debt-window", "funding"))
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        value = guards.read_json(args.input, max_bytes=MAX_INPUT_BYTES)
        result = guards.dumps(run(args.mode, value), max_bytes=MAX_INPUT_BYTES)
        print(result, end="")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Input not evaluated: {exc}\n")


if __name__ == "__main__":
    main()
