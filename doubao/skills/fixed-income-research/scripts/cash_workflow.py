"""Finite-lot research feasibility, with every withdrawal tested on its date."""

from decimal import Decimal
from itertools import product

from workflow_inputs import (ZERO, LocalResourceLimit, day, fields, integer, number,
                             nullable_amount, rows, simple_interest)


def analyze(ctx, data):
    fields(data, {"capital", "capital_evidence_id", "investment_date", "products",
                  "withdrawals", "proposed_lots", "search_limit", "allow_assumptions"})
    if type(data["allow_assumptions"]) is not bool:
        raise ValueError("allow_assumptions must be explicit boolean")
    allow = data["allow_assumptions"]
    invest = ctx.future(data["investment_date"])
    limit = integer(data["search_limit"], "search_limit", 1)
    if limit > 100000:
        raise ValueError("local enumeration safety limit is 100000 allocations")
    unknowns = []

    def amount(value, evidence_id, name, **kwargs):
        reason = ctx.proof(evidence_id, allow)[1]
        return nullable_amount(value, reason, unknowns, name, **kwargs)

    ctx.work.spend(1)
    capital = amount(data["capital"], data["capital_evidence_id"], "capital")
    products = []
    for key, item in rows(data["products"]).items():
        ctx.work.spend(16)
        fields(item, {"id", "meta", "evidence_id", "lot_size", "min_lots", "max_lots",
                      "annual_rate", "rate_kind", "interest_days", "year_days",
                      "fee_rate", "fixed_fee", "minimum_fee", "fee_timing",
                      "principal_available", "interest_available"})
        ctx.meta_check(item["meta"])
        lo = integer(item["min_lots"], "min_lots", 1)
        hi = integer(item["max_lots"], "max_lots")
        if hi < lo:
            raise ValueError("max_lots must be at least min_lots; zero allocation is separately allowed")
        if item["rate_kind"] not in ("gross", "net"):
            raise ValueError("rate_kind must be gross or net")
        if item["fee_timing"] not in ("upfront", "redemption"):
            raise ValueError("fee_timing must be upfront or redemption")
        values = {}
        for field in ("lot_size", "annual_rate", "interest_days", "year_days",
                      "fee_rate", "fixed_fee", "minimum_fee"):
            values[field] = amount(
                item[field], item["evidence_id"], key + "/" + field,
                positive=field in ("lot_size", "year_days"), signed=field == "annual_rate")
        if item["rate_kind"] == "net" and any(
                item[f] is not None and number(item[f], key + "/" + f) != ZERO for f in (
                "fee_rate", "fixed_fee", "minimum_fee")):
            raise ValueError("net quote cannot be charged additional fees")
        for field in ("principal_available", "interest_available"):
            if item[field] is None:
                unknowns.append({"location": key + "/" + field, "reason": "unknown_availability"})
            elif day(item[field]) < day(invest):
                raise ValueError("product proceeds precede investment")
        products.append({**item, **values})
    if not products:
        raise ValueError("cash analysis requires at least one product")
    withdrawals = []
    for key, item in rows(data["withdrawals"]).items():
        ctx.work.spend(4)
        fields(item, {"id", "date", "amount", "evidence_id"})
        if item["date"] is None:
            unknowns.append({"location": "withdrawals/" + key + "/date",
                             "reason": "unknown_withdrawal_date"})
        elif day(item["date"]) < day(invest):
            raise ValueError("withdrawal before investment requires a separate opening rollforward")
        withdrawals.append({**item, "amount": amount(item["amount"], item["evidence_id"], key)})
    proposed = data["proposed_lots"]
    if proposed is not None:
        if not isinstance(proposed, dict) or set(proposed) != {p["id"] for p in products}:
            raise ValueError("proposed_lots must specify every product exactly once")
        for p in products:
            ctx.work.spend(1)
            n = integer(proposed[p["id"]], "proposed_lots")
            if n != 0 and not p["min_lots"] <= n <= p["max_lots"]:
                raise ValueError("proposed allocation violates lot bounds")
    result = {"unknowns": unknowns, "allow_assumptions": allow,
              "proposed": None, "search_status": "unknown_inputs",
              "feasible_count": None, "feasible_lot_bounds": None, "witness": None,
              "search_space_size": None, "search_space_size_exact": False,
              "search_space_lower_bound": None, "evaluated_allocations": 0,
              "observed_feasible_count": 0,
              "limitations": [
                  "Finite-lot, one-purchase simple-interest research model, not a trading instruction.",
                  "No automatic reinvestment, early redemption, tax or settlement-calendar inference.",
                  "Proceeds are end-of-day withdrawable amounts; intraday ordering is not certified.",
                  "Bounds concern supplied products and constraints only, not all available investments.",
              ]}
    if unknowns:
        return result

    def evaluate(counts):
        # Precharge product arithmetic, event building/sorting and rollforwards.
        event_bound = 2 * len(products) + len(withdrawals) + 1
        ctx.work.spend(16 * len(products) + 4 * len(withdrawals)
                       + event_bound * (6 + event_bound.bit_length()))
        invested, upfront, future_fee, net_interest = ZERO, ZERO, ZERO, ZERO
        events, allocations = {}, []

        def event(when):
            return events.setdefault(when, {"principal": ZERO, "interest": ZERO,
                                            "fees": ZERO, "withdrawal": ZERO})

        for p, count in zip(products, counts):
            principal = p["lot_size"] * count
            interest = simple_interest(principal, p["annual_rate"], p["interest_days"], p["year_days"])
            fee = max(principal * p["fee_rate"] + p["fixed_fee"], p["minimum_fee"]) if count else ZERO
            invested += principal
            net_interest += interest - fee
            upfront += fee if p["fee_timing"] == "upfront" else ZERO
            future_fee += fee if p["fee_timing"] == "redemption" else ZERO
            event(p["principal_available"])["principal"] += principal
            event(p["interest_available"])["interest"] += interest
            if p["fee_timing"] == "redemption":
                event(p["principal_available"])["fees"] += fee
            allocations.append({"id": p["id"], "lots": count, "principal": principal,
                                "quoted_interest": interest, "fee": fee, "net_interest": interest-fee,
                                "principal_available": p["principal_available"],
                                "interest_available": p["interest_available"]})
        for w in withdrawals:
            event(w["date"])["withdrawal"] += w["amount"]
        cash = capital - invested - upfront
        timeline = [{"date": invest, "phase": "investment", "opening": capital,
                     "principal": -invested, "interest": ZERO, "fees": upfront,
                     "withdrawal": ZERO, "closing": cash, "shortfall": max(-cash, ZERO)}]
        feasible = cash >= 0
        for when, entry in sorted(events.items()):
            closing = cash + entry["principal"] + entry["interest"] - entry["fees"] - entry["withdrawal"]
            timeline.append({"date": when, "phase": "proceeds_then_withdrawal",
                             "opening": cash, **entry, "closing": closing, "shortfall": max(-closing, ZERO)})
            feasible = feasible and closing >= 0
            cash = closing
        expected = capital + net_interest - sum((w["amount"] for w in withdrawals), ZERO)
        if cash != expected:
            raise ValueError("cash reconciliation failure")
        return {"lots": {p["id"]: n for p, n in zip(products, counts)}, "feasible": feasible,
                "allocations": allocations, "cashflow": timeline, "net_interest": net_interest,
                "closing_cash": cash, "capital": capital, "upfront_fees": upfront,
                "redemption_fees": future_fee}

    if proposed is not None:
        result["proposed"] = evaluate(tuple(proposed[p["id"]] for p in products))
    bounds, feasible_count, witness = {}, 0, None
    try:
        choices, states = [], 1
        for p in products:
            ctx.work.spend(4)
            # Nonnegative fees make capital/lot a safe upper bound.
            upper = min(p["max_lots"], int(capital // p["lot_size"]))
            size = (upper - p["min_lots"] + 2) if upper >= p["min_lots"] else 1
            choices.append(size)
            # Never construct an enormous exact product just to compare it.
            states = limit + 1 if states > limit // size else states * size
        result["search_space_lower_bound"] = states
        if states > limit:
            result["search_status"] = "not_exhausted_safety_limit"
            return result
        result.update(search_space_size=states, search_space_size_exact=True)
        ctx.work.spend(sum(choices) + len(products))
        domains = [(0, *range(p["min_lots"], p["min_lots"] + size - 1))
                   for p, size in zip(products, choices)]
        for counts in product(*domains):
            trial = evaluate(counts)
            result["evaluated_allocations"] += 1
            if not trial["feasible"]:
                continue
            feasible_count += 1
            if witness is None:
                witness = trial
            for key, count in trial["lots"].items():
                low, high = bounds.get(key, (count, count))
                bounds[key] = (min(low, count), max(high, count))
    except LocalResourceLimit as exc:
        result.update(search_status="not_exhausted_work_limit", search_stop_reason=str(exc),
                      observed_feasible_count=feasible_count, witness=witness)
        return result
    result.update(search_status="exhausted_feasible" if feasible_count else "exhausted_infeasible",
                  feasible_count=feasible_count, observed_feasible_count=feasible_count, witness=witness,
                  feasible_lot_bounds={k: {"minimum": lo, "maximum": hi} for k, (lo, hi) in bounds.items()})
    return result
