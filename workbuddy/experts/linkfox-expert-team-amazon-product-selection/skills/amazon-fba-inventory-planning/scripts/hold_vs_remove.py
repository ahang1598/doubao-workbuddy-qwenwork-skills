#!/usr/bin/env python3
"""
Hold vs Remove decision helper for Amazon FBA inventory near aged thresholds.

Compares expected economic outcome of continuing to hold (with optional promo
sell-through) versus immediate removal.

Usage example:
  python hold_vs_remove.py \
    --qty 600 --daily-sales 8 --days-to-threshold 35 \
    --unit-cost 18 --net-price 32 \
    --removal-fee 1.5 --holding-rate 0.30 \
    --aged-fee-per-unit 4 \
    --promo-net-price 22 --promo-lift 0.5
"""

from __future__ import annotations

import argparse


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def decide(
    qty: float,
    daily_sales: float,
    days_to_threshold: float,
    unit_cost: float,
    net_price: float,
    removal_fee: float,
    residual: float,
    holding_rate: float,
    aged_fee_per_unit: float,
    promo_net_price: float | None,
    promo_lift: float,
) -> dict:
    """
    Returns a dict with both options' economics and a recommendation.
    """
    qty = max(0.0, qty)
    daily_sales = max(0.0, daily_sales)
    days_to_threshold = max(0.0, days_to_threshold)

    # --- Immediate removal ---
    removal_loss_per_unit = unit_cost + removal_fee - residual
    v_remove = -qty * removal_loss_per_unit

    # --- Continue holding ---
    # Effective sell rate if promo is used
    if promo_net_price is not None and promo_lift > 0:
        sell_rate = daily_sales * (1.0 + promo_lift)
        price_for_sold = promo_net_price
        using_promo = True
    else:
        sell_rate = daily_sales
        price_for_sold = net_price
        using_promo = False

    sold = min(qty, sell_rate * days_to_threshold) if days_to_threshold > 0 else 0.0
    unsold = qty - sold

    gross_on_sold = sold * (price_for_sold - unit_cost)
    holding_cost = qty * unit_cost * holding_rate * (days_to_threshold / 365.0)
    aged_cost = qty * max(0.0, aged_fee_per_unit)  # simplified expected aged burden over window
    unsold_removal_loss = unsold * removal_loss_per_unit

    v_hold = gross_on_sold - holding_cost - aged_cost - unsold_removal_loss

    # Recommendation
    if v_hold > v_remove:
        action = "HOLD"
        reason = "Expected outcome of holding is better (less negative / more positive) than immediate removal."
    elif v_hold < v_remove:
        action = "REMOVE"
        reason = "Immediate removal has a better expected outcome than continuing to hold."
    else:
        action = "INDIFFERENT"
        reason = "Expected outcomes are approximately equal; prefer promo clearance with removal as backup."

    return {
        "qty": qty,
        "days_to_threshold": days_to_threshold,
        "sell_rate": sell_rate,
        "using_promo": using_promo,
        "sold": sold,
        "unsold": unsold,
        "gross_on_sold": gross_on_sold,
        "holding_cost": holding_cost,
        "aged_cost": aged_cost,
        "unsold_removal_loss": unsold_removal_loss,
        "v_hold": v_hold,
        "v_remove": v_remove,
        "removal_loss_per_unit": removal_loss_per_unit,
        "action": action,
        "reason": reason,
    }


def main():
    p = argparse.ArgumentParser(description="FBA Hold vs Remove decision calculator")
    p.add_argument("--qty", type=float, required=True, help="Remaining sellable units")
    p.add_argument("--daily-sales", type=float, required=True, help="Current daily sales rate")
    p.add_argument(
        "--days-to-threshold",
        type=float,
        required=True,
        help="Days until next material aged-fee threshold (e.g. days until 181 on US)",
    )
    p.add_argument("--unit-cost", type=float, required=True, help="Unit cost incl. inbound freight")
    p.add_argument("--net-price", type=float, required=True, help="Normal net proceeds per unit after Amazon fees")
    p.add_argument("--removal-fee", type=float, default=1.5, help="Removal fee per unit (default 1.5)")
    p.add_argument("--residual", type=float, default=0.0, help="Expected residual value after removal (default 0)")
    p.add_argument(
        "--holding-rate",
        type=float,
        default=0.30,
        help="Annualized holding cost rate (default 0.30)",
    )
    p.add_argument(
        "--aged-fee-per-unit",
        type=float,
        default=0.0,
        help="Expected aged surcharge burden per unit over the remaining window (simplified)",
    )
    p.add_argument(
        "--promo-net-price",
        type=float,
        default=None,
        help="Net proceeds per unit under promo (optional)",
    )
    p.add_argument(
        "--promo-lift",
        type=float,
        default=0.0,
        help="Expected daily-sales lift under promo, e.g. 0.5 = +50%% (default 0)",
    )
    args = p.parse_args()

    r = decide(
        qty=args.qty,
        daily_sales=args.daily_sales,
        days_to_threshold=args.days_to_threshold,
        unit_cost=args.unit_cost,
        net_price=args.net_price,
        removal_fee=args.removal_fee,
        residual=args.residual,
        holding_rate=args.holding_rate,
        aged_fee_per_unit=args.aged_fee_per_unit,
        promo_net_price=args.promo_net_price,
        promo_lift=args.promo_lift,
    )

    print("=" * 58)
    print("FBA HOLD vs REMOVE DECISION")
    print("=" * 58)
    print(f"Quantity:              {r['qty']:,.0f}")
    print(f"Days to threshold:     {r['days_to_threshold']:,.0f}")
    print(f"Effective sell rate:   {r['sell_rate']:,.2f}/day"
          + (" (with promo)" if r["using_promo"] else ""))
    print(f"Expected sold:         {r['sold']:,.1f}")
    print(f"Expected unsold:       {r['unsold']:,.1f}")
    print("-" * 58)
    print("HOLD path")
    print(f"  Gross on sold:       ${r['gross_on_sold']:,.0f}")
    print(f"  Holding cost:        ${r['holding_cost']:,.0f}")
    print(f"  Aged fee burden:     ${r['aged_cost']:,.0f}")
    print(f"  Unsold→removal loss: ${r['unsold_removal_loss']:,.0f}")
    print(f"  Net outcome V_hold:  ${r['v_hold']:,.0f}")
    print("-" * 58)
    print("REMOVE path")
    print(f"  Loss per unit:       ${r['removal_loss_per_unit']:,.2f}")
    print(f"  Net outcome V_remove:${r['v_remove']:,.0f}")
    print("-" * 58)
    print(f"RECOMMENDATION:  {r['action']}")
    print(f"Reason: {r['reason']}")
    print("=" * 58)

    # Simple numeric edge
    edge = r["v_hold"] - r["v_remove"]
    if abs(edge) < 1:
        print("Edge ≈ $0 — decision is economically tight.")
    else:
        better = "HOLD" if edge > 0 else "REMOVE"
        print(f"Economic edge for {better}: ${abs(edge):,.0f}")


if __name__ == "__main__":
    main()
