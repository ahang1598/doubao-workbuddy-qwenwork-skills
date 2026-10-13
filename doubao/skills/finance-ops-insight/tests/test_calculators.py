#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def metadata(unit="CNY", period="2026-06", tolerance="0.01"):
    return {"unit": unit, "period": period, "tolerance": tolerance}


def run_py(script, args):
    cmd = [sys.executable, os.path.join(ROOT, "scripts", script)] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout) if r.stdout.strip() else {}


def assert_no_float(value):
    if isinstance(value, dict):
        for item in value.values():
            assert_no_float(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_float(item)
    else:
        assert not isinstance(value, float), value


def test_variance_example():
    code, out = run_py(
        "variance_decomp.py",
        [
            "--budget-volume",
            "10000",
            "--budget-price",
            "50",
            "--actual-volume",
            "11000",
            "--actual-price",
            "48",
            "--unit",
            "CNY",
            "--period",
            "2026-06",
            "--tolerance",
            "0",
        ],
    )
    assert code == 0
    assert out["status"] == "ok"
    assert out["total_variance"] == "28000"
    assert out["volume_effect"] == "50000"
    assert out["price_effect"] == "-22000"
    assert out["recon_ok"] is True
    assert_no_float(out)
    assert out["calculation"]["unit"] == "CNY"
    assert out["calculation"]["period"] == "2026-06"
    assert out["calculation"]["tolerance"] == "0"


def test_variance_tolerance_is_explicit():
    base = [
        "--budget-volume",
        "3",
        "--budget-price",
        "0.1",
        "--actual-volume",
        "4",
        "--actual-price",
        "0.2",
        "--unit",
        "USD",
        "--period",
        "2026-Q2",
    ]
    code, out = run_py("variance_decomp.py", base)
    assert code == 0
    assert out["status"] == "degraded"
    assert out["artifact_state"] == "degraded"
    assert out["recon_ok"] is None
    assert out["calculation"]["tolerance"] is None
    assert out["unknowns"][0]["missing"] == "tolerance"
    assert_no_float(out)

    code, out = run_py("variance_decomp.py", [*base, "--tolerance", "0"])
    assert code == 0
    assert out["status"] == "ok"
    assert out["recon_ok"] is True
    assert out["calculation"]["tolerance"] == "0"

    code, out = run_py("variance_decomp.py", [*base, "--tolerance", "-0.01"])
    assert code == 2
    assert out["status"] == "error"
    assert out["error_code"] == "negative_tolerance"


def test_margin_flags():
    payload = json.dumps(
        {
            "metadata": metadata(),
            "lines": [
            {"line": "A", "revenue": 100, "direct_cost": 120},
            {"line": "B", "revenue": 1000, "direct_cost": 900},
            {"line": "C", "revenue": 500, "direct_cost": 200},
            ],
        },
        ensure_ascii=False,
    )
    code, out = run_py("margin_calc.py", ["--input-json", payload])
    assert code == 0
    flags = {x["line"]: x["flag"] for x in out["lines"]}
    assert flags["A"] == "NEGATIVE"
    assert flags["B"] == "UNASSESSED_NO_POLICY"
    assert out["status"] == "ok"


def test_cash_shortfall():
    payload = {
        "metadata": metadata(),
        "opening_balance": 10000,
        "fixed_cost_weekly": 8000,
        "cushion_weeks": 2,
        "weeks": [
            {
                "week": "W1",
                "inflows": 1000,
                "outflows": 15000,
                "confirmed_inflows": 1000,
            }
        ],
        "payroll_events": [{"pay_date": "2026-06-05", "amount": 12000, "week_index": 0}],
    }
    code, out = run_py("cash_runway.py", ["--input-json", json.dumps(payload)])
    assert code == 0
    assert out["payroll"][0]["status"] == "SHORTFALL"
    assert out["weeks"][0]["end_balance"] == "-4000"
    assert out["confidence"] == "unknown"
    assert out["coverage"]["confirmation_tag_coverage"] == "1"
    assert out["calculation"]["numeric_serialization"] == "decimal_string"
    assert "HIGH" not in json.dumps(out)
    assert "MEDIUM" not in json.dumps(out)
    assert "LOW" not in json.dumps(out)


def test_business_metrics_perturbations():
    base = {
        "metadata": metadata(),
        "fixed_cost": 1000,
        "unit_price": 20,
        "unit_variable_cost": 10,
        "assumptions": ["single-product mix"],
    }
    code, first = run_py(
        "business_metrics.py",
        ["--operation", "break_even", "--input-json", json.dumps(base)],
    )
    assert code == 0
    perturbed = dict(base, fixed_cost=2000)
    _, second = run_py(
        "business_metrics.py",
        ["--operation", "break_even", "--input-json", json.dumps(perturbed)],
    )
    assert second["break_even_units"] == "200"
    assert first["break_even_units"] == "100"

    one_year = {
        "metadata": metadata(period="2025"),
        "periods": [{"year": 2025, "month": m, "value": m} for m in range(1, 13)],
    }
    _, observed = run_py(
        "business_metrics.py",
        ["--operation", "seasonal", "--input-json", json.dumps(one_year)],
    )
    assert observed["evidence_state"] == "observational_only"
    two_years = {
        "metadata": metadata(period="2025-2026"),
        "periods": one_year["periods"] + [{"year": 2026, "month": m, "value": m * 2} for m in range(1, 13)],
    }
    _, supported = run_py(
        "business_metrics.py",
        ["--operation", "seasonal", "--input-json", json.dumps(two_years)],
    )
    assert supported["evidence_state"] == "supported_for_seasonality"

    concentration = {
        "metadata": metadata(),
        "customers": [
            {"customer_id": "A", "revenue": 80},
            {"customer_id": "B", "revenue": 20},
        ],
        "top_n": 1,
    }
    _, concentrated = run_py(
        "business_metrics.py",
        ["--operation", "concentration", "--input-json", json.dumps(concentration)],
    )
    assert concentrated["top_n_share"] == "0.8"
    assert concentrated["risk_status"] == "unassessed"


def test_business_metrics_unknown_conservation():
    clients = {
        "metadata": metadata(),
        "clients": [
            {"client_id": "A", "revenue": 100, "direct_cost": 60}
        ]
    }
    code, result = run_py(
        "business_metrics.py",
        ["--operation", "client_profitability", "--input-json", json.dumps(clients)],
    )
    assert code == 0
    assert result["status"] == "degraded"
    assert result["clients"][0]["allocated_cost"] is None
    assert result["clients"][0]["profit"] is None
    assert result["clients"][0]["profit_margin"] is None
    assert result["unknowns"][0]["blocked_slots"] == ["profit", "profit_margin"]

    concentration = {
        "metadata": metadata(),
        "customers": [
            {"customer_id": "A", "revenue": 60},
            {"customer_id": "B", "revenue": 40},
        ]
    }
    _, result = run_py(
        "business_metrics.py",
        ["--operation", "concentration", "--input-json", json.dumps(concentration)],
    )
    assert result["top_n"] is None
    assert result["top_n_share"] is None
    assert result["unknowns"][0]["missing"] == "top_n"


def test_pricing_and_period_digest_perturbations():
    pricing = {
        "metadata": metadata(),
        "scenarios": [
            {
                "scenario_id": "base",
                "unit_price": 10,
                "volume": 100,
                "unit_variable_cost": 6,
            },
            {
                "scenario_id": "explicit_change",
                "unit_price": 12,
                "volume": 80,
                "unit_variable_cost": 6,
            },
        ]
    }
    _, result = run_py(
        "business_metrics.py",
        ["--operation", "pricing_sensitivity", "--input-json", json.dumps(pricing)],
    )
    assert result["no_volume_response_inferred"] is True
    assert result["scenarios"][0]["contribution"] == "400"
    assert result["scenarios"][1]["contribution"] == "480"

    digest = {
        "metadata": metadata(period="2025-2026"),
        "basis": "management",
        "periods": [
            {"period": "2025", "revenue": 100, "cost": 80},
            {"period": "2026", "revenue": 130, "cost": 90},
        ],
    }
    _, result = run_py(
        "business_metrics.py",
        ["--operation", "period_digest", "--input-json", json.dumps(digest)],
    )
    assert result["period_count"] == 2
    assert result["first_to_last_change"]["revenue"] == "30"
    assert result["statutory_report"] is False


def test_recurring_cost_review_does_not_cancel():
    payload = {
        "metadata": metadata(),
        "costs": [
            {"cost_id": "service", "amount": 20, "periods_per_year": 12}
        ]
    }
    _, result = run_py(
        "business_metrics.py",
        ["--operation", "recurring_costs", "--input-json", json.dumps(payload)],
    )
    assert result["costs"][0]["usage_status"] == "unknown"
    assert result["costs"][0]["action"] == "review"
    assert result["no_auto_cancel"] is True


def test_decimal_audit_serialization_and_metadata():
    payload = {
        "metadata": metadata(unit="USD", period="2026-Q2", tolerance="0.001"),
        "customers": [
            {"customer_id": "A", "revenue": "1.10"},
            {"customer_id": "B", "revenue": "2.20"},
        ],
        "top_n": 1,
    }
    _, result = run_py(
        "business_metrics.py",
        ["--operation", "concentration", "--input-json", json.dumps(payload)],
    )
    assert_no_float(result)
    assert result["calculation"] == {
        "unit": "USD",
        "period": "2026-Q2",
        "formula": "share_i = revenue_i / total_revenue; HHI = sum(share_i ^ 2)",
        "tolerance": "0.001",
        "numeric_serialization": "decimal_string",
    }
    assert isinstance(result["total_revenue"], str)
    assert isinstance(result["shares"][0]["share"], str)
    assert isinstance(result["hhi"], str)


if __name__ == "__main__":
    test_variance_example()
    test_variance_tolerance_is_explicit()
    test_margin_flags()
    test_cash_shortfall()
    test_business_metrics_perturbations()
    test_business_metrics_unknown_conservation()
    test_pricing_and_period_digest_perturbations()
    test_recurring_cost_review_does_not_cancel()
    test_decimal_audit_serialization_and_metadata()
    print("ok")
