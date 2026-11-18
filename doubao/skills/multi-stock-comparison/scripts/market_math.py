"""Optional market arithmetic. Schema: references/calculations.md.
Imports shared JSON/Decimal helpers from the bundled financial_math.py.
"""
import sys
from decimal import Decimal
from financial_math import cli, number, positive


def calculate(v):
    op = v["operation"]
    if op == "returns":
        start, end = positive(v["start"]), positive(v["end"])
        bs, be = positive(v["benchmark_start"]), positive(v["benchmark_end"])
        r, b = end / start - 1, be / bs - 1
        return {"return_percent": r * 100, "benchmark_return_percent": b * 100,
                "excess_percentage_points": (r - b) * 100,
                "relative_wealth_excess_percent": ((1 + r) / (1 + b) - 1) * 100}
    if op == "risk":
        values = v["prices"]
        if not isinstance(values, list) or len(values) < 3 or v["frequency"] != "daily":
            raise ValueError("at least three daily prices required")
        n = positive(v["periods_per_year"])
        if n != n.to_integral_value():
            raise ValueError("integer annualization factor required")
        prices = [positive(x) for x in values]
        returns = [b / a - 1 for a, b in zip(prices, prices[1:])]
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        peak, drawdown = prices[0], Decimal(0)
        for price in prices:
            peak = max(peak, price)
            drawdown = max(drawdown, (peak - price) / peak)
        return {"annualized_sample_volatility_percent": (variance * n).sqrt() * 100,
                "max_drawdown_percent": drawdown * 100,
                "return_observations": len(returns)}
    if op == "premium":
        left, right = positive(v["left_price"]), positive(v["right_price"])
        converted = right * positive(v["fx_right_to_left"]) * positive(v["entitlement_ratio"])
        return {"right_equivalent_in_left_currency": converted,
                "left_premium_percent": (left / converted - 1) * 100,
                "right_premium_percent": (converted / left - 1) * 100}
    raise ValueError("unknown operation")


if __name__ == "__main__":
    sys.exit(cli(calculate))
