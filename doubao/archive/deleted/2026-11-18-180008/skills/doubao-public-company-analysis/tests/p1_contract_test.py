#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def report():
    slots = [
        {
            "id": f"slot-{index}",
            "fact_needed": f"通用证据{index}",
            "allowed_source_types": ["company_ir"],
            "period": "FY2025",
            "affected_claim_ids": ["calc_growth"],
            "status": "covered",
        }
        for index in range(1, 9)
    ]
    capabilities = {
        name: {"allowed": name != "can_compare_peers", "missing": ["peer_data"] if name == "can_compare_peers" else []}
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
        "identity": {
            "company": "虚构示例公司",
            "ticker": "TEST",
            "exchange": "示例交易所",
            "as_of": "2026-06-30T16:00:00+08:00",
            "latest_fy": "FY2025",
            "latest_reported_period": "2026Q1",
            "freeze_point_checked": True,
        },
        "answer": {"core_judgment": "局部证据足以形成条件结论。", "confidence": "medium", "largest_uncertainty": "同行口径"},
        "capabilities": capabilities,
        "evidence_slots": slots,
        "claims": [
            {
                "id": "calc_growth",
                "type": "calculation",
                "critical": True,
                "financial_or_official": True,
                "period": "FY2025",
                "source_ids": ["primary-1"],
                "calculation_id": "growth-1",
            }
        ],
        "calculations": [
            {
                "id": "growth-1",
                "formula": "(current - prior) / prior",
                "inputs": [{"name": "current", "value": 120}, {"name": "prior", "value": 100}],
                "result": 0.2,
                "unit": "ratio",
                "period": "FY2025",
                "tolerance": 1e-9,
            }
        ],
        "company_type": {
            "type": "manufacturing",
            "required_metrics": ["volume", "unit_cost"],
            "covered_metrics": ["volume"],
            "blocked_metrics": ["unit_cost"],
        },
        "competition": {"named_peers": [], "comparability_notes": [], "blocked_reason": "缺同口径一手披露"},
        "financial_quality": {"bridge": ["profit -> working capital -> cash"], "conclusion": "现金转化需继续观察"},
        "valuation": {
            "mode": "degraded",
            "as_of": "2026-06-30",
            "method": "reverse DCF relationship",
            "implied_assumptions": ["价格不变时，更低利润率要求更高收入增长补偿"],
            "blocked_inputs": ["fully diluted shares"],
        },
        "bear_case": {
            "strongest_counterargument": "增长来自不可持续的渠道备货。",
            "falsification_signals": [
                {"metric": "inventory", "direction": "up", "period": "next quarter", "source_entry": "company filing"},
                {"metric": "cash conversion", "direction": "down", "period": "next quarter", "source_entry": "cash-flow statement"},
                {"metric": "volume", "direction": "down", "period": "next quarter", "source_entry": "operating update"},
            ],
        },
        "unknowns": [{"item": "peer metric", "affected_claim_ids": ["calc_growth"], "next_source": "peer exchange filing"}],
        "sources": [{"id": "primary-1", "type": "company_ir", "url": "https://example.com/filing"}],
    }


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        response = temp / "response.md"
        response.write_text("核心判断：局部证据足以形成条件结论。\n来源：https://example.com/filing\n", encoding="utf-8")
        contract = temp / "contract.json"
        contract.write_text(json.dumps({"min_chars": 1}), encoding="utf-8")
        structured = temp / "report.json"
        structured.write_text(json.dumps(report(), ensure_ascii=False), encoding="utf-8")
        result = run(ROOT / "scripts/validate_deliverable.py", response, contract, "--report-json", structured)
        assert result.returncode == 0, result.stdout + result.stderr

        bad = report()
        bad["valuation"] = {"mode": "degraded", "method": "", "implied_assumptions": [], "blocked_inputs": []}
        structured.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        assert run(ROOT / "scripts/validate_deliverable.py", response, contract, "--report-json", structured).returncode != 0

        refusal = temp / "refusal.md"
        refusal.write_text("由于缺少估值数据，无法完成分析，因此停止。", encoding="utf-8")
        assert run(ROOT / "scripts/lint_direct_response.py", refusal).returncode != 0

        router_input = temp / "router.json"
        router_input.write_text(json.dumps({"company_type": "manufacturing"}), encoding="utf-8")
        routed = run(ROOT / "scripts/company_type_router.py", router_input)
        assert routed.returncode == 0
        assert json.loads(routed.stdout)["type"] == "manufacturing"

        ledger = {
            "as_of": "2026-06-30T16:00:00+08:00",
            "freeze_point": {
                "latest_fy": "FY2025",
                "latest_reported_period": "2026Q1",
                "checked_at": "2026-06-30T15:00:00+08:00",
                "ir_or_exchange_checked": True,
                "newer_filing_exists": False,
            },
            "evidence_slots": report()["evidence_slots"],
            "claims": [
                {
                    "id": "filing-claim",
                    "claim": "最近披露期间已由一手页面确认",
                    "critical": True,
                    "source_url": "https://example.com/filing",
                    "source_type": "company_ir",
                    "published_at": "2026-04-30T08:00:00+08:00",
                    "supported": True,
                }
            ],
        }
        ledger_path = temp / "ledger.json"
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
        assert run(ROOT / "scripts/search_evidence_validator.py", ledger_path).returncode == 0
        ledger["freeze_point"]["newer_filing_exists"] = True
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
        assert run(ROOT / "scripts/search_evidence_validator.py", ledger_path).returncode != 0
    print("PASS company-analysis P1 contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
