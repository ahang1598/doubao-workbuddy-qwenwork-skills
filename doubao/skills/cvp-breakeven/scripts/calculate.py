"""Cost-volume-profit: breakeven, target profit, margin of safety, operating leverage."""
from __future__ import annotations


def contribution_margin(price: float, variable_cost: float) -> float:
    return price - variable_cost


def breakeven_units(fixed_costs: float, price: float, variable_cost: float) -> float:
    cm = contribution_margin(price, variable_cost)
    if cm <= 0:
        raise ValueError("contribution margin must be positive")
    return fixed_costs / cm


def breakeven_sales(fixed_costs: float, cm_ratio: float) -> float:
    return fixed_costs / cm_ratio


def units_for_target_profit(fixed_costs: float, target: float, price: float, variable_cost: float) -> float:
    return (fixed_costs + target) / contribution_margin(price, variable_cost)


def margin_of_safety(actual_sales: float, breakeven_sales_value: float) -> float:
    """Returned as a ratio of actual sales."""
    return (actual_sales - breakeven_sales_value) / actual_sales


def degree_of_operating_leverage(total_cm: float, operating_income: float) -> float:
    return total_cm / operating_income


if __name__ == "__main__":
    be = breakeven_units(120_000, 50.0, 30.0)
    assert be == 6_000
    assert abs(breakeven_sales(120_000, 0.4) - 300_000) < 1e-9
    assert units_for_target_profit(120_000, 40_000, 50.0, 30.0) == 8_000
    assert abs(margin_of_safety(400_000, 300_000) - 0.25) < 1e-12
    assert abs(degree_of_operating_leverage(160_000, 40_000) - 4.0) < 1e-12
    print(f"breakeven: {be:,.0f} units | MOS 25% | DOL 4.0 | OK")
