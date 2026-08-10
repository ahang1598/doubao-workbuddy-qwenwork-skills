#!/usr/bin/env python3
"""Generic P2 regressions. Uses fictional entities and no evaluation oracle."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run(
        [sys.executable, *map(str, args)], capture_output=True, text=True
    )


def evidence_slots():
    core = [
        "latest_annual_report",
        "latest_interim_report",
        "cashflow_statement",
    ]
    slots = []
    for index, kind in enumerate(core, 1):
        slots.append({
            "id": f"core-{index}",
            "slot_kind": kind,
            "fact_needed": kind,
            "allowed_source_types": ["company_ir"],
            "period": "latest before as-of",
            "affected_claim_ids": ["filing-claim"],
            "status": "covered",
            "availability": "available",
            "source_type": "company_ir",
            "source_url": f"https://example.com/{kind}",
        })
    for index in range(4, 9):
        slots.append({
            "id": f"other-{index}",
            "fact_needed": f"generic evidence {index}",
            "allowed_source_types": ["company_ir"],
            "period": "current",
            "affected_claim_ids": ["filing-claim"],
            "status": "blocked",
        })
    return slots


def ledger():
    return {
        "contract_version": "P2",
        "as_of": "2026-06-30T16:00:00+08:00",
        "analysis_ready": True,
        "freeze_point": {
            "latest_fy": "FY2025",
            "latest_reported_period": "2026H1",
            "checked_at": "2026-06-30T15:00:00+08:00",
            "ir_or_exchange_checked": True,
            "newer_filing_exists": False,
        },
        "evidence_slots": evidence_slots(),
        "claims": [{
            "id": "filing-claim",
            "claim": "The latest filing set is identified.",
            "critical": True,
            "source_url": "https://example.com/filing",
            "source_type": "company_ir",
            "published_at": "2026-06-01T08:00:00+08:00",
            "supported": True,
        }],
    }


def p2_report():
    capabilities = {
        name: {"allowed": True, "missing": []}
        for name in (
            "can_assess_business",
            "can_assess_competition",
            "can_assess_financial_quality",
            "can_compare_peers",
            "can_value",
            "can_state_investment_view",
        )
    }
    return {
        "contract_version": "P2",
        "identity": {
            "company": "虚构远岚设备",
            "ticker": "TEST",
            "exchange": "示例交易所",
            "as_of": "2026-06-30",
            "latest_fy": "FY2025",
            "latest_reported_period": "2026H1",
            "freeze_point_checked": True,
        },
        "answer": {
            "core_judgment": "证据支持条件式判断。",
            "confidence": "medium",
            "largest_uncertainty": "市场输入",
        },
        "capabilities": capabilities,
        "evidence_slots": evidence_slots(),
        "claims": [
            {
                "id": "cfo",
                "type": "fact",
                "critical": True,
                "financial_or_official": True,
                "period": "FY2025",
                "source_ids": ["primary"],
            },
            {
                "id": "capex",
                "type": "fact",
                "critical": True,
                "financial_or_official": True,
                "period": "FY2025",
                "source_ids": ["primary"],
            },
        ],
        "calculations": [],
        "company_type": {
            "type": "manufacturing",
            "required_metrics": ["volume"],
            "covered_metrics": ["volume"],
            "blocked_metrics": [],
        },
        "competition": {
            "named_peers": ["虚构同口径可比企业"],
            "comparability_notes": ["按同一分母比较"],
            "blocked_reason": "",
        },
        "financial_quality": {
            "bridge": ["statutory CFO -> cash CapEx -> conventional FCF"],
            "conclusion": "口径可对账。",
            "cashflow_basis": {
                "statement_cfo_claim_id": "cfo",
                "cash_capex_claim_ids": ["capex"],
                "conventional_fcf_definition": "statutory CFO - cash CapEx",
                "company_adjusted_fcf_name": None,
                "adjusted_to_statutory_bridge": [],
                "customer_financing_scope": "not applicable",
                "unreconciled_difference": None,
            },
        },
        "valuation": {
            "mode": "full",
            "as_of": "2026-06-30",
            "method": "comparable multiple",
            "implied_assumptions": ["same denominator"],
            "blocked_inputs": [],
            "input_as_of_consistent": True,
            "market_inputs": [
                {"name": "price", "as_of": "2026-06-30", "value": 10},
                {"name": "shares", "as_of": "2026-06-29", "value": 100},
            ],
        },
        "bear_case": {
            "strongest_counterargument": "现金改善可能只是时点效应。",
            "falsification_signals": [
                {"metric": "cash conversion", "direction": "down", "period": "next report", "source_entry": "filing"},
                {"metric": "inventory", "direction": "up", "period": "next report", "source_entry": "filing"},
                {"metric": "capex", "direction": "up", "period": "next report", "source_entry": "filing"},
            ],
        },
        "unknowns": [],
        "sources": [{"id": "primary", "type": "company_ir", "url": "https://example.com/filing"}],
    }


def write_cashflow_fixture(directory):
    metrics = {
        "net_profit": 100,
        "depreciation_amortization": 20,
        "share_based_compensation": 5,
        "disposal_gain": -2,
        "inventory_write_down": 1,
        "accounts_receivable_change": -15,
        "inventory_change": -8,
        "accounts_payable_change": 10,
        "contract_liabilities_change": 4,
        "other_operating_items_change": 5,
        "operating_cash_flow": 120,
        "capex": 30,
        "free_cash_flow": 90,
        "adjusted_free_cash_flow": 80,
        "net_change_in_cash": 15,
    }
    lines = ["entity,period,metric,value,currency,unit,source_locator"]
    lines.extend(
        f"FictionalCo,FY2025,{metric},{value},CNY,million,formal-filing"
        for metric, value in metrics.items()
    )
    (directory / "financials.csv").write_text("\n".join(lines), encoding="utf-8")
    supplemental = {
        "fcf_definition": {
            "name": "analyst conventional free cash flow",
            "kind": "analyst_conventional",
            "formula": "operating_cash_flow - cash_capex",
            "source": "formal filing",
        },
        "adjusted_fcf_definition": {
            "name": "company adjusted free cash flow",
            "reported_metric": "adjusted_free_cash_flow",
            "starting_metric": "operating_cash_flow",
            "statutory_total_cash_metric": "net_change_in_cash",
            "source": "company definition",
            "customer_financing_scope": "after customer financing",
            "adjustments": [
                {"name": "cash capex", "amount": -30, "cash_or_non_cash": "cash", "source": "formal filing"},
                {"name": "customer financing", "amount": -10, "cash_or_non_cash": "cash", "source": "company definition"},
            ],
        },
    }
    (directory / "cashflow_facts.json").write_text(
        json.dumps(supplemental), encoding="utf-8"
    )


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)

        evidence = ledger()
        evidence["evidence_slots"][0]["status"] = "blocked"
        evidence_path = temp / "evidence.json"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        assert run(ROOT / "scripts/search_evidence_validator.py", evidence_path).returncode != 0
        evidence["evidence_slots"][0]["status"] = "covered"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        assert run(ROOT / "scripts/search_evidence_validator.py", evidence_path).returncode == 0

        cashflow_dir = temp / "cashflow"
        cashflow_dir.mkdir()
        write_cashflow_fixture(cashflow_dir)
        cashflow_result = run(ROOT / "scripts/company_cashflow_bridge.py", cashflow_dir)
        assert cashflow_result.returncode == 0, cashflow_result.stderr
        cashflow = json.loads(cashflow_result.stdout)
        bridge = cashflow["bridges"]["FY2025"]
        assert bridge["calculated_fcf"] == 90
        assert bridge["adjusted_fcf_bridge"]["reconciles"] is True
        assert bridge["fcf_basis"]["profit_bridge_may_define_fcf"] is False

        response = temp / "response.md"
        response.write_text(
            "核心判断：仅形成条件结论。\n来源：https://example.com/filing",
            encoding="utf-8",
        )
        contract = temp / "contract.json"
        contract.write_text(json.dumps({"min_chars": 1}), encoding="utf-8")
        report_path = temp / "report.json"
        report = p2_report()
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        assert run(
            ROOT / "scripts/validate_deliverable.py",
            response,
            contract,
            "--report-json",
            report_path,
        ).returncode != 0
        report["valuation"].update({
            "mode": "degraded",
            "input_as_of_consistent": False,
            "market_inputs": [],
            "blocked_inputs": ["same-as-of market price"],
        })
        report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        assert run(
            ROOT / "scripts/validate_deliverable.py",
            response,
            contract,
            "--report-json",
            report_path,
        ).returncode == 0

        bad_text = temp / "bad.md"
        bad_text.write_text(
            "核心判断：FCF等于经营利润加非现金项目再减资本开支；版权费是固定成本，可随规模摊薄。\n"
            "本内容不构成投资建议。",
            encoding="utf-8",
        )
        assert run(ROOT / "scripts/lint_direct_response.py", bad_text).returncode != 0

    print("PASS company-analysis P2 generic regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
