"""Debt-plan conservation, scenario compilation and dated liquidity rollforwards."""

from collections import deque
from datetime import timedelta
from decimal import Decimal

import fixed_income_checks as legacy
from input_guards import restrictions
from workflow_inputs import (ZERO, Budget, MAX_WORK_UNITS, boolean, day, fields, number,
                             nullable_amount, rows, text, simple_interest, within)

MAX_MATCH_PAIRS = 50000
MAX_ACTIVE_PAYMENTS = 512
MAX_ACTIVE_FUNDS = 512
MAX_RESULT_ROWS = 4096


def validate_plan(ctx, debt, plan):
    """Validate supplied structure and raw values, without activating a plan."""
    fields(plan, {"id", "kind", "evidence_id", "principal_payments", "interest_periods",
                  "interest_schedule_complete"},
           {"principal_schedule_complete_evidence_id", "interest_schedule_complete_evidence_id"})
    location = debt["id"] + "/" + text(plan["id"], "plan id")
    if plan["kind"] not in ("legal", "put"):
        raise ValueError(location + ": plan kind must be legal or put")
    boolean(plan["interest_schedule_complete"], "interest_schedule_complete")
    ctx.proof(debt["evidence_id"])
    ctx.proof(plan["evidence_id"])
    for field in ("principal_schedule_complete_evidence_id", "interest_schedule_complete_evidence_id"):
        if plan.get(field) is not None:
            ctx.proof(plan[field])
    principal = None if debt["principal"] is None else number(debt["principal"], debt["id"] + "/principal")
    payments, periods = rows(plan["principal_payments"]), rows(plan["interest_periods"])
    ctx.work.spend(len(payments) + len(periods) + len(periods) ** 2 + 1)
    known, amounts_complete, dates = ZERO, True, []
    for key, row in payments.items():
        fields(row, {"id", "due", "amount", "evidence_id"}, {"purpose"})
        purpose = row.get("purpose", "principal" if plan["kind"] == "legal" else None)
        if purpose not in ("principal", "put") or (plan["kind"] == "legal" and purpose != "principal"):
            raise ValueError(location + "/" + key + ": principal purpose must be explicit for put plans")
        ctx.proof(row["evidence_id"])
        dates.append(None if row["due"] is None else day(row["due"]))
        if row["amount"] is None:
            amounts_complete = False
        else:
            known += number(row["amount"], location + "/" + key + "/amount")
    if principal is not None:
        if known > principal:
            raise ValueError(location + ": principal double counted")
        if amounts_complete and known != principal:
            raise ValueError(location + ": schedule does not conserve principal; matching amounts required")
    intervals = []
    for key, row in periods.items():
        fields(row, {"id", "due", "start", "end", "annual_rate", "year_days",
                     "paid_amount", "evidence_id"}, {"accrued_before_start"})
        if key in payments:
            raise ValueError(location + ": principal and interest payment ids overlap")
        ctx.proof(row["evidence_id"])
        left, right = day(row["start"]), day(row["end"])
        due = None if row["due"] is None else day(row["due"])
        if left >= right or (due is not None and due < right):
            raise ValueError(location + "/" + key + ": invalid interest interval or payment date")
        if any(left < b and right > a for a, b in intervals):
            raise ValueError(location + ": duplicate or overlapping interest accrual intervals")
        intervals.append((left, right))
        if dates and all(d is not None for d in dates) and amounts_complete and right > max(dates):
            raise ValueError(location + ": interest accrual extends beyond full principal redemption")
        for field in ("annual_rate", "year_days", "paid_amount"):
            if row[field] is not None:
                number(row[field], location + "/" + key + "/" + field,
                       positive=field == "year_days", signed=field == "annual_rate")
        history = row.get("accrued_before_start")
        if history is not None:
            fields(history, {"amount", "through", "evidence_id"})
            ctx.proof(history["evidence_id"])
            day(history["through"])
            if history["amount"] is not None:
                number(history["amount"], location + "/" + key + "/accrued_before_start", signed=True)


def principal_dependency_unknown(payments, through, *, inclusive=False):
    """An unknown payment affects only balances on/after its possible payment day."""
    return bool(principal_dependencies(payments, through, inclusive=inclusive))


def principal_dependencies(payments, through, *, inclusive=False):
    missing = []
    for payment in payments:
        if payment["amount"] == ZERO:
            continue
        if payment["due"] is None:
            reason = "unknown_principal_payment_date"
        elif payment["amount"] is None and (
                day(payment["due"]) < through or (inclusive and day(payment["due"]) == through)):
            reason = "unknown_principal_payment_amount"
        else:
            continue
        missing.append({"location": payment["id"], "reason": reason,
                        "evidence_status": payment["evidence_status"]})
    return missing


def compile_plan(ctx, debt, plan, allow_assumptions, start, activation_reason="eligible",
                 activation_fact_reason="eligible"):
    validate_plan(ctx, debt, plan)
    fields(plan, {"id", "kind", "evidence_id", "principal_payments", "interest_periods",
                  "interest_schedule_complete"},
           {"principal_schedule_complete_evidence_id", "interest_schedule_complete_evidence_id"})
    if plan["kind"] not in ("legal", "put"):
        raise ValueError("plan kind must be legal or put")
    boolean(plan["interest_schedule_complete"], "interest_schedule_complete")
    unknowns, payments, factual_unknowns = [], [], []
    factual = {"principal": {}, "interest": {}}

    def proof(key, location, group):
        factual[group][location] = {"evidence_id": key,
                                   "status": ctx.fact_reason(key, debt["id"] + "/" + location,
                                                             factual_unknowns)}
        return ctx.proof(key, allow_assumptions)[1]

    completeness = {}
    for group in ("principal", "interest"):
        key = plan.get(group + "_schedule_complete_evidence_id")
        completeness[group] = {
            "evidence_id": key,
            "status": ctx.fact_reason(key, debt["id"] + "/" + group + "_completeness",
                                      factual_unknowns),
        }
    plan_reason = proof(plan["evidence_id"], "plan", "principal")
    debt_reason = proof(debt["evidence_id"], "debt", "principal")

    def payment_reason(key, location, group):
        row_reason = proof(key, location, group)
        return next((r for r in (activation_reason, debt_reason, plan_reason, row_reason)
                     if r != "eligible"), "eligible")

    def payment_date(value, reason, location):
        due = value if reason == "eligible" else None
        if due is None:
            unknowns.append({"location": location, "reason": (
                "unknown_payment_date" if reason == "eligible" else reason)})
        else:
            ctx.future(due)
            if day(due) < day(start):
                raise ValueError("payment precedes debt origination")
        return due

    principal_reason = debt_reason if activation_reason == "eligible" else activation_reason
    principal = nullable_amount(debt["principal"], principal_reason, unknowns, debt["id"] + "/principal")
    known_principal = ZERO
    principal_rows = rows(plan["principal_payments"])
    interest_rows = rows(plan["interest_periods"])
    ctx.work.spend(len(principal_rows) ** 2 * max(1, len(interest_rows))
                   + len(interest_rows) ** 2 + len(principal_rows) + len(interest_rows))
    for key, row in principal_rows.items():
        fields(row, {"id", "due", "amount", "evidence_id"}, {"purpose"})
        purpose = row.get("purpose", "principal" if plan["kind"] == "legal" else None)
        if purpose not in ("principal", "put") or (plan["kind"] == "legal" and purpose != "principal"):
            raise ValueError("principal purpose must be explicit for put plans; legal plans require principal")
        reason = payment_reason(row["evidence_id"], "principal/" + key, "principal")
        due = payment_date(row["due"], reason, debt["id"] + "/" + key)
        amount = nullable_amount(row["amount"], reason, unknowns, debt["id"] + "/" + key)
        if amount is not None:
            known_principal += amount
        payments.append({"id": debt["id"] + "/" + key, "debt_id": debt["id"],
                         "obligor": debt["obligor"], "due": due, "amount": amount,
                         "purpose": purpose,
                         "evidence_id": row["evidence_id"], "evidence_status": reason, "calculation": None})
    if plan_reason != "eligible":
        unknowns.append({"location": debt["id"] + "/" + plan["id"], "reason": plan_reason})
    if principal is not None and known_principal > principal:
        raise ValueError(f"principal double counted: {debt['id']}/{plan['id']}")
    principal_amounts_complete = all(p["amount"] is not None for p in payments)
    principal_complete = principal_amounts_complete and all(p["due"] is not None for p in payments)
    if principal is not None and principal_amounts_complete and known_principal != principal:
        raise ValueError(f"principal schedule does not conserve outstanding principal: {debt['id']}")
    if not principal_rows and principal != ZERO:
        unknowns.append({"location": debt["id"], "reason": "missing_principal_schedule"})
    if not plan["interest_schedule_complete"]:
        unknowns.append({"location": debt["id"], "reason": "interest_schedule_incomplete"})
    principal_payments = list(payments)
    interval_keys = set()
    for key, row in interest_rows.items():
        fields(row, {"id", "due", "start", "end", "annual_rate", "year_days",
                     "paid_amount", "evidence_id"}, {"accrued_before_start"})
        if key in principal_rows:
            raise ValueError("principal and interest payment ids overlap")
        reason = payment_reason(row["evidence_id"], "interest/" + key, "interest")
        due = payment_date(row["due"], reason, debt["id"] + "/" + key)
        start_day, end_day = day(row["start"]), day(row["end"])
        if start_day >= end_day or (due is not None and (
                day(due) < end_day or (activation_reason == "eligible" and day(due) < day(start)))):
            raise ValueError("invalid interest interval or payment date")
        if (start_day, end_day) in interval_keys:
            raise ValueError("duplicate interest accrual interval")
        if any(start_day < b and end_day > a for a, b in interval_keys):
            raise ValueError("overlapping interest accrual intervals")
        interval_keys.add((start_day, end_day))
        if reason == "eligible" and debt["origin"] == "draw" and start_day < day(start):
            raise ValueError("new borrowing accrues before the draw")
        if principal_rows and principal_complete and end_day > max(day(p["due"]) for p in principal_rows.values()):
            raise ValueError("interest accrual extends beyond full principal redemption")
        rate = nullable_amount(row["annual_rate"], reason, unknowns, key + "/rate", signed=True)
        basis = nullable_amount(row["year_days"], reason, unknowns, key + "/year_days", positive=True)
        paid = nullable_amount(row["paid_amount"], reason, unknowns, key + "/paid")
        accrued_before = ZERO
        history = row.get("accrued_before_start")
        if history is not None:
            fields(history, {"amount", "through", "evidence_id"})
            day(history["through"])
            history_amount = nullable_amount(
                history["amount"], proof(history["evidence_id"], "history/" + key, "interest"),
                unknowns, key + "/accrued_before_start", signed=True)
        opening = debt["origin"] == "opening"
        if reason == "eligible" and opening and (end_day - day(start)).days <= 1:
            raise ValueError("wholly historical accrual requires a separate model")
        if reason == "eligible" and opening and start_day <= day(start):
            if history is None:
                accrued_before = None
                unknowns.append({"location": debt["id"] + "/" + key,
                                 "reason": "pre_cutoff_accrued_interest_required"})
            else:
                if history["through"] != start:
                    raise ValueError("historical accrual must bridge exactly to the cutoff")
                accrued_before = history_amount
        elif history is not None and reason == "eligible":
            raise ValueError("historical accrual supplied for a wholly future period")
        if paid is not None and accrued_before is not None and paid > max(accrued_before, ZERO):
            raise ValueError("paid-at-cutoff exceeds sourced historical accrual")
        amount, credit, calculation = None, None, None
        if reason == "eligible":
            # Opening principal is the EOD balance; a new draw starts accruing on its draw day.
            anchor = day(start) + timedelta(days=1) if opening else day(start)
            accrual_start = max(start_day, anchor)
            boundaries = sorted({accrual_start, end_day} | {
                day(p["due"]) for p in principal_payments
                if p["due"] is not None and accrual_start < day(p["due"]) < end_day
            })
            segments, known_interests, missing = [], [], []
            for left, right in zip(boundaries, boundaries[1:]):
                dependencies = principal_dependencies(principal_payments, left, inclusive=True)
                if principal is None:
                    dependencies.append({"location": debt["id"] + "/principal", "reason": "unknown_principal"})
                base = None if dependencies else principal - sum(
                    (p["amount"] for p in principal_payments if p["due"] is not None
                     and day(p["due"]) <= left), ZERO)
                for field, value in (("rate", rate), ("year_days", basis)):
                    if value is None:
                        dependencies.append({"location": debt["id"] + "/" + key + "/" + field,
                                             "reason": "unknown_" + field})
                interest = None if dependencies else simple_interest(base, rate, (right-left).days, basis)
                if interest is not None:
                    known_interests.append(interest)
                missing.extend(dependencies)
                segments.append({"start": left.isoformat(), "end": right.isoformat(),
                                 "principal": base, "days": (right-left).days, "interest": interest,
                                 "status": "computed" if interest is not None else "unknown",
                                 "missing_dependencies": dependencies})
            known_future = sum(known_interests, ZERO) if known_interests else None
            future = known_future if len(known_interests) == len(segments) else None
            accrued = accrued_before + future if accrued_before is not None and future is not None else None
            remaining = accrued - paid if accrued is not None and paid is not None else None
            for field, value in (("accrued_before_start", accrued_before), ("paid_at_cutoff", paid)):
                if value is None:
                    missing.append({"location": debt["id"] + "/" + key + "/" + field,
                                    "reason": "unknown_" + field})
            if remaining is not None:
                amount, credit = max(remaining, ZERO), max(-remaining, ZERO)
            calculation = {"method": "simple_actual_on_remaining_principal",
                           "status": "computed" if remaining is not None else "partial",
                           "annual_rate": rate, "year_days": basis, "segments": segments,
                           "known_future_accrual": known_future, "future_accrued": future,
                           "missing_dependencies": missing,
                           "accrued_before_start": accrued_before,
                           "accrued": accrued, "paid_at_cutoff": paid, "remaining": remaining}
        if amount is None:
            unknowns.append({"location": debt["id"] + "/" + key, "reason": "interest_not_computable"})
        payments.append({"id": debt["id"] + "/" + key, "debt_id": debt["id"],
                         "obligor": debt["obligor"], "due": due, "amount": amount,
                         "purpose": "interest", "evidence_id": row["evidence_id"],
                         "evidence_status": reason, "interest_credit": credit, "calculation": calculation})
    if activation_reason != "eligible":
        unknowns.append({"location": debt["id"] + "/activation", "reason": activation_reason})
    if activation_fact_reason != "eligible":
        factual_unknowns.append({"location": debt["id"] + "/activation",
                                 "reason": activation_fact_reason})
    modeled_principal = (principal is not None and principal_complete
                         and plan_reason == debt_reason == activation_reason == "eligible")
    modeled_schedule = modeled_principal and not unknowns
    factual_principal = (modeled_principal and activation_fact_reason == "eligible"
                         and completeness["principal"]["status"] == "eligible"
                         and all(row["status"] == "eligible" for row in factual["principal"].values()))
    factual_interest = (factual_principal and modeled_schedule
                        and completeness["interest"]["status"] == "eligible"
                        and all(row["status"] == "eligible" for row in factual["interest"].values()))
    return {"debt_id": debt["id"], "plan_id": plan["id"], "kind": plan["kind"],
            "principal": principal, "payments": payments, "unknowns": unknowns,
            "principal_schedule_complete": modeled_principal,
            "scenario_schedule_complete": modeled_schedule,
            "factual_principal_schedule_complete": factual_principal,
            "factual_interest_schedule_complete": factual_interest,
            "completeness_evidence": completeness, "factual_dependencies": factual,
            "factual_unknowns": factual_unknowns}


def priority_cover(funds, payments, work=None):
    """Lexicographic earliest-date coverage; residual rerouting preserves earlier paid totals."""
    work = work if work is not None else Budget(MAX_WORK_UNITS, "allocation work")
    within(len(funds), MAX_ACTIVE_FUNDS, "active funds")
    within(len(payments), MAX_ACTIVE_PAYMENTS, "active payments")
    within(len(funds) * len(payments), MAX_MATCH_PAIRS, "fund/payment match pairs")
    work.spend(len(funds) * len(payments) + len(payments) ** 2)
    source, sink = ("source",), ("sink",)
    adj, capacity, initial = {source: [], sink: []}, {}, {}

    def edge(a, b, value):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
        capacity[a, b], capacity[b, a], initial[a, b] = value, ZERO, value

    for fid, fund in funds.items():
        edge(source, ("fund", fid), fund["amount"])
    matches = []
    for fid, fund in funds.items():
        for pid, payment in payments.items():
            if (fund["owner"] == payment["obligor"]
                    and day(fund["available_from"]) <= day(payment["due"])
                    and (fund["expires_on"] is None or day(payment["due"]) <= day(fund["expires_on"]))
                    and (fund["restriction"] == "unrestricted" or (
                        payment["debt_id"] in fund["debt_ids"] and payment["purpose"] in fund["purposes"]))):
                edge(("fund", fid), ("pay", pid), min(fund["amount"], payment["amount"]))
                matches.append((fid, pid))
    for due in sorted({p["due"] for p in payments.values()}):
        for pid, payment in payments.items():
            if payment["due"] == due:
                edge(("pay", pid), sink, payment["amount"])
        while True:
            parents, queue = {source: None}, deque([source])
            while queue and sink not in parents:
                current = queue.popleft()
                work.spend(len(adj[current]))
                for nxt in adj[current]:
                    if nxt not in parents and capacity[current, nxt] > 0:
                        parents[nxt] = current
                        queue.append(nxt)
            if sink not in parents:
                break
            links, current = [], sink
            while parents[current] is not None:
                work.spend(1)
                links.append((parents[current], current))
                current = parents[current]
            amount = min(capacity[link] for link in links)
            for a, b in links:
                capacity[a, b] -= amount
                capacity[b, a] += amount
    return [{"fund_id": f, "payment_id": p,
             "amount": initial[("fund", f), ("pay", p)] - capacity[("fund", f), ("pay", p)]}
            for f, p in matches if initial[("fund", f), ("pay", p)] != capacity[("fund", f), ("pay", p)]]


def pool(ctx, row, allow_assumptions, unknowns, registered, opening=False,
         activation_reason="eligible", activation_state=None):
    required = {"id", "balance_id", "owner", "meta", "amount", "available_from", "expires_on",
                "restriction", "debt_ids", "purposes", "evidence_id", "status"}
    fields(row, required | ({"balance_at"} if opening else set()))
    ctx.meta_check(row["meta"])
    text(row["owner"], "owner")
    text(row["balance_id"], "balance_id")
    date_fields = ("available_from", "expires_on") + (("balance_at",) if opening else ())
    for name in date_fields:
        if row[name] is not None:
            day(row[name])
    if (row["expires_on"] is not None and row["available_from"] is not None
            and day(row["expires_on"]) < day(row["available_from"])):
        raise ValueError("fund expiry before availability")
    if row["status"] not in ("confirmed", "conditional", "planned", "unknown"):
        raise ValueError("unsupported funds status")
    restrictions(row, registered, "funds/" + row["id"])
    proof_reasons = ctx.proof_details(row["evidence_id"], allow_assumptions)[1]["evidence_reasons"]
    business, missing = [], []
    if row["status"] != "confirmed" and not (
        allow_assumptions and ctx.evidence[row["evidence_id"]]["kind"] == "assumption"
    ):
        business.append("unconfirmed_source")
    if row["restriction"] == "unknown":
        business.append("unknown_restriction")
    if activation_state is not None:
        proof_reasons.extend(activation_state["evidence_reasons"])
        business.extend(activation_state["business_reasons"])
        missing.extend(activation_state["missing_reasons"])
    elif activation_reason != "eligible":
        business.append(activation_reason)
    if row["amount"] is None:
        missing.append("unknown_amount")
    if row["available_from"] is None:
        missing.append("unknown_available_from")
    if opening and row["balance_at"] is None:
        missing.append("unknown_cutoff_balance")
    temporal = None
    if not proof_reasons and activation_reason == "eligible":
        temporal = []
        if opening:
            if ((row["balance_at"] is not None and row["balance_at"] != ctx.as_of)
                    or (row["available_from"] is not None and day(row["available_from"]) > day(ctx.as_of))):
                raise ValueError("opening funds require a confirmed cutoff balance")
            if row["expires_on"] is not None and day(row["expires_on"]) < day(ctx.as_of):
                temporal.append("expired_at_cutoff")
        elif row["available_from"] is not None:
            ctx.future(row["available_from"])
    state = legacy.admission(proof_reasons, business, missing, temporal)
    reason = state["eligibility_status"]
    amount = nullable_amount(row["amount"], reason, unknowns, "fund/" + row["id"])
    unknowns.extend({"location": "fund/" + row["id"], "reason": item}
                    for item in state["ineligibility_reasons"][1:])
    return {**row, **{name: row[name] if temporal is not None else None for name in date_fields},
            "supplied_dates": {name: row[name] for name in date_fields},
            "amount": amount, "eligibility_status": reason, "admission": state,
            "evidence_kind": ctx.evidence[row["evidence_id"]]["kind"]}


def analyze(ctx, data):
    fields(data, {"ledger_complete", "window", "reported", "debts", "opening_funds",
                  "facilities", "scenarios"}, {"ledger_complete_evidence_id"})
    boolean(data["ledger_complete"], "ledger_complete")
    legacy.window(data["window"])
    aggregate_unknowns = []
    completeness_reason = ctx.fact_reason(data.get("ledger_complete_evidence_id"),
                                         "ledger_complete", aggregate_unknowns)
    ledger_complete = data["ledger_complete"] and completeness_reason == "eligible"
    if not data["ledger_complete"]:
        aggregate_unknowns.append({"location": "ledger_complete", "reason": "ledger_declared_incomplete"})
    reported, reported_reason = data["reported"], "not_requested"
    if reported is not None:
        fields(reported, {"as_of", "meta", "window", "basis", "amount"}, {"evidence_id"})
        if reported["amount"] is not None:
            number(reported["amount"], "reported/amount")
        reported_reason = ctx.fact_reason(reported.get("evidence_id"), "reported", aggregate_unknowns)
        reported = {**{k: v for k, v in reported.items() if k != "evidence_id"},
                    "evidence": ctx.aggregate_proof(reported.get("evidence_id"))}
        if reported_reason != "eligible":
            reported["amount"] = None
    debts, facilities = rows(data["debts"]), rows(data["facilities"])
    registered = set(debts)
    for key, debt in debts.items():
        fields(debt, {"id", "obligor", "meta", "principal", "origin", "evidence_id", "legal_plan", "plans"})
        ctx.meta_check(debt["meta"])
        text(debt["obligor"], "obligor")
        if debt["origin"] not in ("opening", "draw"):
            raise ValueError("debt origin must be opening or draw")
        plans = rows(debt["plans"])
        for plan in plans.values():
            validate_plan(ctx, debt, plan)
        if debt["legal_plan"] not in plans or plans[debt["legal_plan"]]["kind"] != "legal":
            raise ValueError("each debt needs one designated legal maturity plan")
    for key, f in facilities.items():
        fields(f, {"id", "owner", "meta", "undrawn_limit", "available_from", "expires_on",
                   "status", "evidence_id", "restriction", "debt_ids", "purposes"})
        restrictions(f, registered, "facilities/" + key)
        ctx.meta_check(f["meta"])
        text(f["owner"], "facility owner")
        day(f["available_from"])
        day(f["expires_on"])
        if day(f["expires_on"]) < day(f["available_from"]):
            raise ValueError("invalid facility availability")
        number(f["undrawn_limit"], "undrawn limit")
        ctx.proof(f["evidence_id"])
        if f["status"] not in ("confirmed", "conditional", "planned", "unknown"):
            raise ValueError("unsupported facility status")
    legal_rows, legal_unknowns = [], list(aggregate_unknowns)
    for debt in debts.values():
        if debt["origin"] != "opening":
            continue
        plan = rows(debt["plans"])[debt["legal_plan"]]
        compiled = compile_plan(ctx, debt, plan, False, ctx.as_of)
        if not compiled["factual_principal_schedule_complete"]:
            legal_unknowns.append({"location": debt["id"], "reason": "incomplete_legal_principal"})
        for payment in compiled["payments"]:
            if payment["purpose"] == "principal":
                proof = ctx.proof(payment["evidence_id"])[0]
                legal_rows.append({"id": payment["id"], "meta": ctx.meta, "amount": payment["amount"],
                                   "maturity_date": payment["due"], "evidence": proof})
    ledger = legacy.run("debt-window", {
        "as_of": ctx.as_of, "meta": ctx.meta, "window": data["window"], "debts": legal_rows,
        "ledger_complete": ledger_complete and not legal_unknowns,
        "ledger_complete_evidence": ctx.aggregate_proof(data.get("ledger_complete_evidence_id")),
        **({"reported": reported} if reported is not None else {}),
    })
    ledger.update(ledger_complete_confirmed=ledger_complete,
                  completeness_evidence_status=completeness_reason,
                  reported_evidence_status=reported_reason)
    scenarios = []
    scenario_rows = rows(data["scenarios"])
    within(len(scenario_rows), 16, "scenario count")
    for sid, scenario in scenario_rows.items():
        fields(scenario, {"id", "note", "allow_assumptions", "plans", "inflows", "draws"})
        text(scenario["note"], "scenario note")
        allow = boolean(scenario["allow_assumptions"], "allow_assumptions")
        if not isinstance(scenario["plans"], dict):
            raise ValueError("plans must select exactly one plan id per active debt")
        draws = rows(scenario["draws"])
        selected_draws, used_facilities, draw_dates, draw_rows = {}, {}, {}, []
        unknowns = [row for row in aggregate_unknowns if row["location"] == "ledger_complete"]
        pools = {}
        economic_ids = set()

        def add_pool(item, opening=False, activation_reason="eligible", activation_state=None):
            result = pool(ctx, item, allow, unknowns, registered, opening,
                          activation_reason, activation_state)
            if item["id"] in pools or item["balance_id"] in economic_ids:
                raise ValueError("duplicate economic funds across opening/inflows/draws")
            economic_ids.add(item["balance_id"])
            pools[item["id"]] = result

        for item in rows(data["opening_funds"]).values():
            add_pool(item, True)
        for item in rows(scenario["inflows"]).values():
            add_pool(item)
        within(len(pools) + len(draws), MAX_ACTIVE_FUNDS, "registered scenario funds")
        for draw_id, draw in draws.items():
            fields(draw, {"id", "facility_id", "debt_id", "date", "amount", "evidence_id"})
            day(draw["date"])
            if draw["facility_id"] not in facilities or draw["debt_id"] not in debts:
                raise ValueError("draw must bind a registered facility and new debt")
            facility, debt = facilities[draw["facility_id"]], debts[draw["debt_id"]]
            amount = number(draw["amount"], "draw amount", positive=True)
            if (debt["origin"] != "draw" or draw["debt_id"] in selected_draws
                    or debt["obligor"] != facility["owner"]
                    or number(debt["principal"], "new debt principal") != amount):
                raise ValueError("draw must create exactly one matching new principal liability")
            evidence_ids = {"facility": facility["evidence_id"], "draw": draw["evidence_id"],
                            "debt": debt["evidence_id"]}
            proof_states = {name: ctx.proof_details(key, allow)[1] for name, key in evidence_ids.items()}
            statuses = {name: state["evidence_status"] for name, state in proof_states.items()}
            proof_reasons = [name + ":" + item for name, state in proof_states.items()
                             for item in state["evidence_reasons"]]
            business = []
            if facility["status"] != "confirmed" and not (
                    allow and ctx.evidence[facility["evidence_id"]]["kind"] == "assumption"):
                business.append("facility:unconfirmed_facility")
            state = legacy.admission(proof_reasons, business,
                                     temporal_reasons=[] if not proof_reasons and not business else None)
            reason = state["eligibility_status"]
            factual = {name: ctx.proof_details(key)[1] for name, key in evidence_ids.items()}
            fact_statuses = {name: item["evidence_status"] for name, item in factual.items()}
            fact_reasons = [name + ":" + reason for name, item in factual.items()
                            for reason in item["evidence_reasons"]]
            fact_business = ["facility:unconfirmed_facility"] if facility["status"] != "confirmed" else []
            fact_state = legacy.admission(fact_reasons, fact_business,
                                         temporal_reasons=[] if not fact_reasons and not fact_business else None)
            fact_reason = fact_state["eligibility_status"]
            selected_draws[debt["id"]] = {
                "date": draw["date"], "reason": reason, "fact_reason": fact_reason}
            if reason == "eligible":
                ctx.future(draw["date"])
                if not day(facility["available_from"]) <= day(draw["date"]) <= day(facility["expires_on"]):
                    raise ValueError("draw outside facility availability")
                used_facilities[facility["id"]] = used_facilities.get(facility["id"], ZERO) + amount
                if used_facilities[facility["id"]] > number(facility["undrawn_limit"]):
                    raise ValueError("draws exceed undrawn limit; revolving restoration is not implicit")
                draw_dates[debt["id"]] = draw["date"]
            else:
                unknowns.extend({"location": "draw/" + draw_id, "reason": item}
                                for item in state["ineligibility_reasons"])
            assumed = any(ctx.evidence[key]["kind"] == "assumption" for key in evidence_ids.values())
            draw_rows.append({
                "id": draw_id, "debt_id": debt["id"], "facility_id": facility["id"],
                "date": draw["date"] if reason == "eligible" else None,
                "amount": amount if reason == "eligible" else None,
                "evidence_ids": evidence_ids, "evidence_status": statuses,
                "factual_evidence_status": fact_statuses,
                "supplied_date": draw["date"], "admission": state, "factual_admission": fact_state,
                "status": ("assumed" if assumed else "eligible") if reason == "eligible" else "unknown",
                "actual_execution_status": "unknown",
            })
            add_pool({
                "id": "draw/" + draw_id, "balance_id": "draw/" + draw_id, "owner": facility["owner"],
                "meta": facility["meta"], "amount": amount if reason == "eligible" else None,
                "available_from": draw["date"], "expires_on": None, "status": "confirmed",
                "restriction": facility["restriction"], "debt_ids": facility["debt_ids"],
                "purposes": facility["purposes"], "evidence_id": draw["evidence_id"],
            }, activation_reason=reason, activation_state=state)
            if reason != "eligible":
                pools["draw/" + draw_id]["available_from"] = None
            if assumed:
                pools["draw/" + draw_id]["evidence_kind"] = "assumption"
        active = {k for k, debt in debts.items() if debt["origin"] == "opening"} | set(selected_draws)
        if set(scenario["plans"]) != active:
            raise ValueError("scenario must select exactly one plan for every opening/drawn debt")
        compiled, payments = [], {}
        for key in sorted(active):
            debt = debts[key]
            plan_id = scenario["plans"][key]
            if not isinstance(plan_id, str) or plan_id not in rows(debt["plans"]):
                raise ValueError("one scenario cannot combine maturity and put alternatives")
            activation = selected_draws.get(key, {
                "date": ctx.as_of, "reason": "eligible", "fact_reason": "eligible"})
            plan = compile_plan(ctx, debt, rows(debt["plans"])[plan_id], allow,
                                activation["date"], activation["reason"], activation["fact_reason"])
            compiled.append(plan)
            unknowns.extend(plan["unknowns"])
            unknowns.extend(plan["factual_unknowns"])
            within(len(payments) + len(plan["payments"]), MAX_ACTIVE_PAYMENTS, "registered scenario payments")
            for payment in plan["payments"]:
                if payment["id"] in payments:
                    raise ValueError("duplicate economic payment")
                payments[payment["id"]] = payment
        known_pools = {k: p for k, p in pools.items() if p["amount"] is not None}
        known_payments = {k: p for k, p in payments.items() if p["amount"] is not None and p["due"] is not None}
        allocations = priority_cover(known_pools, known_payments, ctx.work)
        paid, used = dict.fromkeys(known_payments, ZERO), dict.fromkeys(known_pools, ZERO)
        for allocation in allocations:
            paid[allocation["payment_id"]] += allocation["amount"]
            used[allocation["fund_id"]] += allocation["amount"]
        payment_rows = [{**p, "covered": paid.get(pid),
                         "uncovered": p["amount"] - paid[pid] if pid in paid else None}
                        for pid, p in sorted(payments.items(), key=lambda item: (item[1]["due"] or "9999-12-31", item[0]))]
        events = {p["due"] for p in payments.values() if p["due"] is not None} | set(draw_dates.values()) | {
            p["available_from"] for p in known_pools.values() if day(p["available_from"]) > day(ctx.as_of)}
        horizon = max(events, default=ctx.as_of)
        events |= {(day(p["expires_on"]) + timedelta(days=1)).isoformat()
                   for p in known_pools.values() if p["expires_on"] and
                   day(ctx.as_of) <= day(p["expires_on"]) < day(horizon)}
        owners = sorted({p["owner"] for p in known_pools.values()} | {
            p["obligor"] for p in known_payments.values()})
        output_rows = (len(owners) + len(compiled)) * len(events)
        within(output_rows, MAX_RESULT_ROWS, "cashflow/liability rows")
        ctx.work.spend(output_rows + len(allocations) + len(payments) + len(pools)
                       + len(events) * len(payments))
        balances, incoming_by, due_by, covered_by, expired_by, principal_by = {}, {}, {}, {}, {}, {}

        def add(mapping, key, value):
            mapping[key] = mapping.get(key, ZERO) + value

        for fid, p in known_pools.items():
            if day(p["available_from"]) <= day(ctx.as_of) and (
                    p["expires_on"] is None or day(p["expires_on"]) >= day(ctx.as_of)):
                add(balances, p["owner"], p["amount"])
            add(incoming_by, (p["owner"], p["available_from"]), p["amount"])
            if p["expires_on"] is not None:
                when = (day(p["expires_on"]) + timedelta(days=1)).isoformat() if p["expires_on"] < horizon else None
                add(expired_by, (p["owner"], when), p["amount"] - used[fid])
        for pid, p in known_payments.items():
            add(due_by, (p["obligor"], p["due"]), p["amount"])
            add(covered_by, (p["obligor"], p["due"]), paid[pid])
            if p["purpose"] != "interest":
                add(principal_by, (p["debt_id"], p["due"]), p["amount"])
        cashflow, liabilities = [], []
        for owner in owners:
            balance = balances.get(owner, ZERO)
            uncovered_total = ZERO
            for when in sorted(events):
                incoming = incoming_by.get((owner, when), ZERO)
                due = due_by.get((owner, when), ZERO)
                covered = covered_by.get((owner, when), ZERO)
                expired = expired_by.get((owner, when), ZERO)
                closing = balance + incoming - covered - expired
                if closing < 0:
                    raise ValueError("internal cash conservation failure")
                uncovered_total += due - covered
                cashflow.append({"owner": owner, "date": when, "opening": balance, "inflows": incoming,
                                 "due": due, "covered": covered, "expired_unavailable": expired,
                                 "closing": closing, "cumulative_uncovered": uncovered_total,
                                 "basis": "conditional_coverage_of_supplied_sources_not_actual_payments"})
                balance = closing
        for plan in compiled:
            debt = debts[plan["debt_id"]]
            if debt["id"] in selected_draws and selected_draws[debt["id"]]["reason"] != "eligible":
                liabilities.append({
                    "debt_id": debt["id"], "date": None, "opening": None, "draw": None,
                    "principal_scheduled": None, "closing": None, "actual_closing": None,
                    "basis": "unconfirmed_draw_path", "reason": selected_draws[debt["id"]]["reason"],
                })
                continue
            remaining = plan["principal"] if debt["origin"] == "opening" else ZERO
            principal_payments = [p for p in plan["payments"] if p["purpose"] != "interest"]
            for when in sorted(events):
                draw_amount = plan["principal"] if draw_dates.get(debt["id"]) == when else ZERO
                before_draw = debt["origin"] == "draw" and when < draw_dates[debt["id"]]
                dependency_unknown = not before_draw and principal_dependency_unknown(
                    principal_payments, day(when), inclusive=True)
                principal_scheduled = (principal_by.get((debt["id"], when), ZERO)
                                       if not dependency_unknown else None)
                closing = (None if remaining is None or draw_amount is None or principal_scheduled is None
                           else remaining + draw_amount - principal_scheduled)
                liabilities.append({"debt_id": debt["id"], "date": when, "opening": remaining,
                                    "draw": draw_amount, "principal_scheduled": principal_scheduled,
                                    "closing": closing, "actual_closing": None,
                                    "basis": "selected_plan_performed_as_scheduled_not_observed"})
                remaining = closing
        known_gap = sum((p["uncovered"] for p in payment_rows if p["uncovered"] is not None), ZERO)
        scenario_complete = all(p["scenario_schedule_complete"] for p in compiled)
        demand_complete = ledger_complete and all(
            p["factual_principal_schedule_complete"] and p["factual_interest_schedule_complete"]
            for p in compiled)
        scenarios.append({
            "id": sid, "note": scenario["note"], "allow_assumptions": allow,
            "selected_plans": scenario["plans"], "payments": payment_rows, "funds": list(pools.values()),
            "draws": draw_rows,
            "facility_usage": used_facilities,
            "plan_completeness": [{k: v for k, v in p.items()
                                   if k not in ("principal", "payments", "unknowns")} for p in compiled],
            "allocations": allocations, "cashflow": cashflow, "liabilities": liabilities,
            "liability_basis": "selected_plan_performed_as_scheduled_not_observed",
            "actual_payment_status": "unknown",
            "known_gap_against_supplied_eligible_sources": known_gap,
            "scenario_payment_schedule_complete": scenario_complete,
            "scenario_schedule_scope": "selected_registered_debts_only_not_ledger_completeness",
            "scenario_status": "computed" if scenario_complete else "partial",
            "selected_schedule_gap_against_supplied_eligible_sources": known_gap if scenario_complete else None,
            "funding_basis": ("includes_explicit_assumptions" if any(
                p["evidence_kind"] == "assumption" for p in known_pools.values()) else "supplied_factual_sources"),
            "full_schedule_gap_against_supplied_eligible_sources": known_gap if demand_complete else None,
            "payment_schedule_complete": demand_complete, "unknowns": unknowns,
            "status": "partial" if unknowns or not demand_complete else "computed",
        })
    if not scenarios:
        raise ValueError("debt analysis needs at least one explicit scenario")
    return {"legal_window": ledger, "legal_unknowns": legal_unknowns, "scenarios": scenarios,
            "limitations": [
                "Coverage is against supplied eligible sources, not a default probability or execution.",
                "Date-only events use end-of-day availability; intraday ordering is not modeled.",
                "Uncovered means a conditional gap against supplied sources, never observed arrears or default.",
                "Liabilities and interest follow the selected scheduled-principal path, not the funded allocation.",
                "Actual repayment and actual remaining liabilities require separately sourced execution evidence.",
                "Signed interest credits are not available cash or principal offsets without separate evidence.",
                "Later cash is not silently used to erase earlier conditional coverage gaps.",
                "Internal transfers and revolving-credit restoration require separately reconciled inputs.",
            ]}
