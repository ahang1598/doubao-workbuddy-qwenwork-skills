#!/usr/bin/env python3
"""
Deterministic safety-stock, reorder-point, and economic restock calculator for Amazon FBA.

Includes:
  - Classic safety stock (demand + lead-time variability)
  - Target-cover based order quantity
  - Holding cost H(Q)
  - Expected unsold / liquidation loss L(Q)
  - Simple expected net profit check

Usage examples:
  # Basic
  python calculate_restock.py --daily-sales 12.5 --std-demand 3.2 --lead-time 45 --std-lead 7 --service 0.95 --current 180 --inbound 50

  # With economics
  python calculate_restock.py --daily-sales 93 --std-demand 22 --lead-time 40 --std-lead 7 --service 0.95 \
      --current 1280 --inbound 900 --target-cover 70 \
      --unit-cost 18 --net-price 32 --holding-rate 0.28 \
      --sell-through 0.90 --promo-loss 10 --removal-loss 19.5 --promo-share 0.7

  # With FBA capacity / ASIN restock headroom caps
  python calculate_restock.py --daily-sales 25 --lead-time 35 --current 180 --inbound 120 \
      --target-cover 45 --capacity-headroom 500 --asin-restock-headroom 400 --defer-overflow-upstream
"""

from __future__ import annotations

import argparse
import math

Z_SCORES = {
    0.90: 1.28,
    0.95: 1.65,
    0.97: 1.88,
    0.98: 2.05,
    0.99: 2.33,
}


def get_z(service: float) -> float:
    if service in Z_SCORES:
        return Z_SCORES[service]
    keys = sorted(Z_SCORES.keys())
    for i, k in enumerate(keys):
        if service <= k:
            if i == 0:
                return Z_SCORES[k]
            prev = keys[i - 1]
            ratio = (service - prev) / (k - prev)
            return Z_SCORES[prev] + ratio * (Z_SCORES[k] - Z_SCORES[prev])
    return Z_SCORES[keys[-1]]


def safety_stock(
    daily_sales: float,
    std_demand: float,
    lead_time: float,
    std_lead: float,
    z: float,
) -> float:
    """Classic formula accounting for both demand and lead-time variability."""
    variance = (lead_time * std_demand ** 2) + (daily_sales ** 2 * std_lead ** 2)
    return z * math.sqrt(max(variance, 0))


def holding_cost(
    qty: float,
    unit_cost: float,
    holding_rate: float,
    avg_days_on_hand: float,
) -> float:
    """
    H(Q) ≈ unit_cost * Q * annual_holding_rate * (avg_days_on_hand / 365)
    """
    if qty <= 0 or unit_cost <= 0 or holding_rate <= 0:
        return 0.0
    return unit_cost * qty * holding_rate * (avg_days_on_hand / 365.0)


def expected_unsold_loss(
    qty: float,
    sell_through: float,
    promo_loss: float,
    removal_loss: float,
    promo_share: float,
) -> float:
    """
    L(Q) = Q_unsold * (promo_share * promo_loss + (1 - promo_share) * removal_loss)

    sell_through: expected fraction sold at normal / planned price (0-1)
    promo_loss:   $ loss per unit if cleared via promotion
    removal_loss: $ loss per unit if removed (cost + removal fee - residual)
    promo_share:  fraction of unsold units expected to go through promotion vs removal
    """
    if qty <= 0:
        return 0.0
    sell_through = max(0.0, min(1.0, sell_through))
    promo_share = max(0.0, min(1.0, promo_share))
    unsold = qty * (1.0 - sell_through)
    unit_loss = promo_share * promo_loss + (1.0 - promo_share) * removal_loss
    return unsold * unit_loss


def expected_net_profit(
    qty: float,
    net_price: float,
    unit_cost: float,
    sell_through: float,
    h_cost: float,
    l_cost: float,
) -> float:
    """
    π(Q) ≈ (net_price - unit_cost) * S(Q) - H(Q) - L(Q)
    where S(Q) = qty * sell_through
    """
    if qty <= 0:
        return 0.0
    sold = qty * max(0.0, min(1.0, sell_through))
    gross = (net_price - unit_cost) * sold
    return gross - h_cost - l_cost


def main():
    parser = argparse.ArgumentParser(
        description="FBA safety stock, reorder point & economic restock calculator"
    )
    # Core inventory inputs
    parser.add_argument("--daily-sales", type=float, required=True, help="Average daily unit sales")
    parser.add_argument("--std-demand", type=float, default=0.0, help="Std dev of daily demand")
    parser.add_argument("--lead-time", type=float, required=True, help="Average lead time in days")
    parser.add_argument("--std-lead", type=float, default=0.0, help="Std dev of lead time in days")
    parser.add_argument("--service", type=float, default=0.95, help="Target service level (0.90-0.99)")
    parser.add_argument("--current", type=float, default=0.0, help="Current sellable inventory")
    parser.add_argument("--inbound", type=float, default=0.0, help="Already inbound units")
    parser.add_argument(
        "--target-cover",
        type=float,
        default=None,
        help="Optional target days of cover (overrides pure ROP quantity)",
    )

    # Supplier constraints
    parser.add_argument("--moq", type=float, default=0.0, help="Minimum order quantity (0=ignore)")
    parser.add_argument(
        "--multiple",
        type=float,
        default=1.0,
        help="Order multiple / carton size (round up final qty)",
    )
    parser.add_argument("--max-qty", type=float, default=None, help="Optional maximum order quantity cap")
    parser.add_argument(
        "--raise-to-moq",
        action="store_true",
        help="If unconstrained qty > 0 but < MOQ, raise to MOQ (default: defer to 0 unless flag set)",
    )
    # Amazon capacity / restock headroom (IPI & restock limits)
    parser.add_argument(
        "--capacity-headroom",
        type=float,
        default=None,
        help="FBA account/size-tier capacity still available to send (units). Caps final FBA qty.",
    )
    parser.add_argument(
        "--asin-restock-headroom",
        type=float,
        default=None,
        help="ASIN-level restock limit remaining (units). Caps final FBA qty.",
    )
    parser.add_argument(
        "--defer-overflow-upstream",
        action="store_true",
        help="If capacity caps cut qty, print overflow as suggested upstream (AWD/hub) amount",
    )
    parser.add_argument(
        "--require-capacity",
        action="store_true",
        help="If neither --capacity-headroom nor --asin-restock-headroom is provided, "
        "force FBA qty to 0 (block uncapped send). Use for peak/strict policy runs.",
    )

    # Economic inputs (optional — if omitted, economics section is skipped)
    parser.add_argument("--unit-cost", type=float, default=None, help="Unit cost including inbound freight")
    parser.add_argument("--net-price", type=float, default=None, help="Net proceeds per unit after Amazon fees")
    parser.add_argument(
        "--holding-rate",
        type=float,
        default=0.28,
        help="Annualized holding cost rate (default 0.28 = 28%%)",
    )
    parser.add_argument(
        "--sell-through",
        type=float,
        default=0.95,
        help="Expected sell-through rate at planned price (0-1, default 0.95)",
    )
    parser.add_argument(
        "--promo-loss",
        type=float,
        default=0.0,
        help="Loss per unit if cleared via promotion",
    )
    parser.add_argument(
        "--removal-loss",
        type=float,
        default=0.0,
        help="Loss per unit if removed (cost + removal fee - residual)",
    )
    parser.add_argument(
        "--promo-share",
        type=float,
        default=0.7,
        help="Fraction of unsold units expected to be promoted vs removed (default 0.7)",
    )

    args = parser.parse_args()

    z = get_z(args.service)
    ss = safety_stock(args.daily_sales, args.std_demand, args.lead_time, args.std_lead, z)
    rop = (args.daily_sales * args.lead_time) + ss
    pipeline = args.current + args.inbound

    print("=" * 56)
    print("FBA RESTOCK CALCULATOR")
    print("=" * 56)
    print(f"Service level:          {args.service:.0%}  (Z = {z:.2f})")
    print(f"Safety stock:           {ss:,.1f} units")
    print(f"Reorder point:          {rop:,.1f} units")
    print(f"Current + inbound:      {pipeline:,.1f} units")

    if args.daily_sales > 0:
        print(f"Current days of cover:  {pipeline / args.daily_sales:,.1f} days")

    if args.target_cover is not None:
        target_units = args.daily_sales * args.target_cover
        qty = max(0.0, target_units - pipeline)
        avg_days = args.target_cover / 2.0  # approximate average on-hand if sold evenly
        print(f"Target cover:           {args.target_cover:.0f} days → {target_units:,.1f} units")
        print(f"Unconstrained qty:      {qty:,.1f} units")
    else:
        qty = max(0.0, rop - pipeline)
        avg_days = (args.lead_time + (ss / args.daily_sales if args.daily_sales > 0 else 0)) / 2.0
        print(f"Unconstrained qty:      {qty:,.1f} units (to reach ROP)")

    # ---- Supplier constraints (MOQ / multiple / max) ----
    qty_unconstrained = qty
    constraint_notes = []
    if qty > 0 and args.moq > 0 and qty < args.moq:
        if args.raise_to_moq:
            constraint_notes.append(f"raised to MOQ {args.moq:g}")
            qty = args.moq
        else:
            constraint_notes.append(f"deferred (qty {qty:g} < MOQ {args.moq:g}; pass --raise-to-moq to lift)")
            qty = 0.0
    if qty > 0 and args.multiple and args.multiple > 1:
        import math as _math
        rounded = _math.ceil(qty / args.multiple) * args.multiple
        if rounded != qty:
            constraint_notes.append(f"rounded to multiple {args.multiple:g}: {qty:g} → {rounded:g}")
            qty = rounded
    if qty > 0 and args.max_qty is not None and qty > args.max_qty:
        constraint_notes.append(f"capped at max-qty {args.max_qty:g}")
        qty = args.max_qty

    # Amazon FBA capacity / ASIN restock headroom (see references/ipi-capacity-limits.md)
    overflow_upstream = 0.0
    cap_ceiling = None
    has_capacity_input = (
        args.capacity_headroom is not None or args.asin_restock_headroom is not None
    )
    if args.require_capacity and not has_capacity_input and qty > 0:
        constraint_notes.append(
            "blocked by --require-capacity (no capacity-headroom or asin-restock-headroom)"
        )
        overflow_upstream = qty
        qty = 0.0
    if args.capacity_headroom is not None:
        cap_ceiling = args.capacity_headroom if cap_ceiling is None else min(cap_ceiling, args.capacity_headroom)
    if args.asin_restock_headroom is not None:
        cap_ceiling = (
            args.asin_restock_headroom
            if cap_ceiling is None
            else min(cap_ceiling, args.asin_restock_headroom)
        )
    if qty > 0 and cap_ceiling is not None:
        if cap_ceiling <= 0:
            constraint_notes.append(
                f"blocked by capacity/restock headroom ({cap_ceiling:g}); FBA qty → 0"
            )
            overflow_upstream = qty
            qty = 0.0
        elif qty > cap_ceiling:
            constraint_notes.append(
                f"capped by capacity/restock headroom {cap_ceiling:g} (was {qty:g})"
            )
            overflow_upstream = qty - cap_ceiling
            qty = cap_ceiling

    print(f"Final order qty:        {qty:,.1f} units")
    if constraint_notes:
        print(f"Constraints applied:    {'; '.join(constraint_notes)}")
    elif qty_unconstrained != qty:
        print("Constraints applied:    (adjusted)")
    if has_capacity_input:
        ch = "n/a" if args.capacity_headroom is None else f"{args.capacity_headroom:g}"
        ah = "n/a" if args.asin_restock_headroom is None else f"{args.asin_restock_headroom:g}"
        print(f"Capacity headroom:      {ch}  |  ASIN restock headroom: {ah}")
    elif qty_unconstrained > 0:
        if args.require_capacity:
            print("Capacity policy:        REQUIRE — blocked (no headroom inputs)")
        else:
            print(
                "Capacity policy:        UNCAPPED (no headroom inputs; "
                "pass --require-capacity to block)"
            )
    if overflow_upstream > 0:
        if args.defer_overflow_upstream:
            print(f"Overflow → upstream:    {overflow_upstream:,.1f} units (AWD/hub suggestion)")
        else:
            print(
                f"Overflow cut:           {overflow_upstream:,.1f} units "
                f"(pass --defer-overflow-upstream to surface hub/AWD suggestion)"
            )

    # ---- Economic section ----
    if args.unit_cost is not None and args.net_price is not None and qty > 0:
        h_cost = holding_cost(qty, args.unit_cost, args.holding_rate, avg_days)
        l_cost = expected_unsold_loss(
            qty,
            args.sell_through,
            args.promo_loss,
            args.removal_loss,
            args.promo_share,
        )
        profit = expected_net_profit(
            qty,
            args.net_price,
            args.unit_cost,
            args.sell_through,
            h_cost,
            l_cost,
        )

        print("-" * 56)
        print("ECONOMIC CHECK")
        print("-" * 56)
        print(f"Unit cost:              ${args.unit_cost:,.2f}")
        print(f"Net price (after fees): ${args.net_price:,.2f}")
        print(f"Unit margin:            ${args.net_price - args.unit_cost:,.2f}")
        print(f"Holding rate (annual):  {args.holding_rate:.0%}")
        print(f"Expected sell-through:  {args.sell_through:.0%}")
        print(f"Avg days on hand (est): {avg_days:,.1f}")
        print(f"H(Q) Holding cost:      ${h_cost:,.0f}")
        print(f"L(Q) Unsold/liq loss:   ${l_cost:,.0f}")
        print(f"Expected net profit:    ${profit:,.0f}")

        if profit < 0:
            print("\n⚠  Expected net profit is negative. Consider reducing qty, splitting inbound,")
            print("   improving sell-through, or revisiting price/promotion plan.")
        elif l_cost > h_cost * 2:
            print("\n⚠  Liquidation risk (L) dominates holding cost (H). Tightening qty or")
            print("   improving sell-through is recommended.")
        else:
            print("\n✓  Economics look acceptable under current assumptions.")
    elif qty > 0:
        print("-" * 56)
        print("(Pass --unit-cost and --net-price to enable H(Q) + L(Q) economic check)")

    print("=" * 56)


if __name__ == "__main__":
    main()
