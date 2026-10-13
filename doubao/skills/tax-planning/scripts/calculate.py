"""Tax planning: progressive brackets, effective vs marginal rate, timing benefit."""
from __future__ import annotations


def progressive_tax(income: float, brackets: list[tuple[float, float]]) -> float:
    """brackets: (upper_bound, rate) ascending; last bound may be float('inf')."""
    tax, lower = 0.0, 0.0
    for upper, rate in brackets:
        if income <= lower:
            break
        tax += (min(income, upper) - lower) * rate
        lower = upper
    return tax


def effective_rate(tax: float, income: float) -> float:
    return tax / income


def marginal_rate(income: float, brackets: list[tuple[float, float]]) -> float:
    for upper, rate in brackets:
        if income <= upper:
            return rate
    return brackets[-1][1]


def deferral_benefit(tax_amount: float, years_deferred: float, discount_rate: float) -> float:
    """PV saving from postponing a tax payment."""
    return tax_amount * (1 - (1 + discount_rate) ** -years_deferred)


if __name__ == "__main__":
    brackets = [(300_000, 0.07), (600_000, 0.11), (1_100_000, 0.15),
                (1_600_000, 0.19), (3_200_000, 0.21), (float("inf"), 0.24)]
    t = progressive_tax(2_000_000, brackets)
    expected = 300_000*0.07 + 300_000*0.11 + 500_000*0.15 + 500_000*0.19 + 400_000*0.21
    assert abs(t - expected) < 1e-9
    assert abs(effective_rate(t, 2_000_000) - expected / 2_000_000) < 1e-12
    assert marginal_rate(2_000_000, brackets) == 0.21
    db = deferral_benefit(100_000, 3, 0.10)
    assert abs(db - 100_000 * (1 - 1.1 ** -3)) < 1e-9
    print(f"tax {t:,.0f} | eff {effective_rate(t, 2_000_000):.1%} | marginal 21% | OK")
