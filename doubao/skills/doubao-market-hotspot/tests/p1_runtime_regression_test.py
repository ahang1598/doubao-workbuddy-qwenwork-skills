#!/usr/bin/env python3
"""Generic regressions for event search, evidence, and fail-close delivery."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from event_runtime_guard import guard  # noqa: E402
from search_router import infer_signals, plan  # noqa: E402


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        capture_output=True,
        text=True,
    )


def supported_claim(claim_id, claim_type, **extra):
    return {
        "id": claim_id,
        "claim_type": claim_type,
        "critical": extra.pop("critical", False),
        "supported": True,
        "source_ids": ["official-document"],
        **extra,
    }


def base_package():
    return {
        "status": "completed",
        "gates": {
            "primary_source_gate_passed": True,
            "semantic_gate_passed": True,
        },
        "search": {"mode": "optional"},
        "claims": [
            supported_claim("identity", "event_identity", critical=True),
            supported_claim("status", "event_status", critical=True),
            supported_claim("scope", "scope_parameter", critical=True),
        ],
        "market_evidence": [],
    }


def test_event_type_search_plans():
    company = infer_signals(
        "event-impact-analysis",
        "一家上市公司宣布资产收购，分析交易状态和影响。",
        {"object_frozen": True},
    )
    company_plan = plan(company)
    assert company_plan["event_type"] == "company"
    assert company_plan["source_order"][:2] == ["company_ir", "exchange_filing"]
    assert company_plan["query_stages"] == [
        "event_identity_and_status",
        "scope_and_parameters",
        "impact_and_pre_event_market_baseline",
    ]
    assert company_plan["stage_contract"]["advance_requires_previous_stage_pass"]

    rule = infer_signals(
        "event-impact-analysis",
        "某发布机关拟调整行业准入规则，分析对相关公司的适用范围。",
        {"object_frozen": True, "jurisdiction_frozen": True},
    )
    rule_plan = plan(rule)
    assert rule_plan["event_type"] == "regulatory"
    assert rule_plan["source_order"][0] == "issuing_authority"
    optional_plan = plan(
        {
            "skill": "event-impact-analysis",
            "object_frozen": True,
            "event_type": "generic",
        }
    )
    assert len(optional_plan["query_stages"]) == 3


def test_claim_guard_and_market_baseline():
    payload = base_package()
    payload["claims"].append(
        supported_claim(
            "borrowed-threshold",
            "numeric_parameter",
            parameter_origin="other_jurisdiction",
        )
    )
    result = guard(payload)
    borrowed = next(
        item for item in result["claim_results"]
        if item["id"] == "borrowed-threshold"
    )
    assert borrowed["disposition"] == "conditional_scenario_only"
    assert result["can_assess_priced_in"] is False
    assert result["query_stage_gate"]["may_enter_impact_and_market_baseline"]


def test_search_off_numeric_review():
    payload = base_package()
    payload["search"] = {"mode": "off", "can_upgrade": True}
    payload["claims"].append(
        {
            "id": "experience-range",
            "claim_type": "numeric_parameter",
            "critical": False,
            "supported": False,
            "source_ids": [],
            "claim_kind": "numeric",
            "parameter_origin": "industry_experience",
        }
    )
    upgraded = guard(payload)
    assert upgraded["search"]["effective_mode"] == "required"

    payload["search"] = {
        "mode": "off",
        "can_upgrade": False,
        "user_forbids_search": True,
    }
    downgraded = guard(payload)
    claim = next(
        item for item in downgraded["claim_results"]
        if item["id"] == "experience-range"
    )
    assert claim["disposition"] == "remove_or_preserve_as_unknown"


def test_hard_gates_remain_failed():
    for gate in ("primary_source_gate_passed", "semantic_gate_passed"):
        payload = base_package()
        payload["gates"][gate] = False
        result = guard(payload)
        assert result["status"] == "failed"
        assert result["may_deliver"] is False
        assert gate in result["hard_gate_failures"]

    payload = base_package()
    payload["status"] = "failed"
    assert guard(payload)["status"] == "failed"


def test_evidence_validator_and_finalizer_fail_close():
    with tempfile.TemporaryDirectory() as raw_temp:
        temp = Path(raw_temp)
        ledger = {
            "as_of": "2026-07-01T00:00:00Z",
            "claims": [
                {
                    "id": "unsupported-status",
                    "claim": "事件已经生效",
                    "claim_kind": "status",
                    "critical": True,
                    "supported": False,
                    "source_type": "issuing_authority",
                    "source_url": "https://authority.invalid/notice",
                }
            ],
        }
        ledger_path = temp / "ledger.json"
        ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
        assert run("search_evidence_validator.py", ledger_path).returncode == 1

        facts = ROOT / "schemas" / "facts.example.json"
        config = json.loads((ROOT / "config" / "runtime.json").read_text())
        data = json.loads(facts.read_text())
        sections = config["modes"][data["meta"]["mode"]]["required_sections"]
        body = ["# 通用事件分析"]
        for spec in sections:
            body += [
                "",
                f"## {spec['aliases'][0]}",
                "",
                "这是用于验证交付门禁的通用内容，包含机制、来源和局限。 "
                "{fact:example_fact}",
            ]
        body += ["", "本报告仅供研究参考，不构成投资建议。"]
        report = temp / "report.md"
        report.write_text("\n".join(body), encoding="utf-8")
        quality = temp / "quality.json"
        quality.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "may_deliver": False,
                    "hard_gate_failures": ["semantic_gate_passed"],
                }
            ),
            encoding="utf-8",
        )
        finalized = run(
            "finalize_report.py",
            report,
            facts,
            "--quality-gates",
            quality,
        )
        assert finalized.returncode == 1
        manifest = json.loads(
            report.with_name("report-manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["status"] == "FAILED"


def main():
    test_event_type_search_plans()
    test_claim_guard_and_market_baseline()
    test_search_off_numeric_review()
    test_hard_gates_remain_failed()
    test_evidence_validator_and_finalizer_fail_close()
    print("PASS event-impact-analysis P1 generic runtime regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
