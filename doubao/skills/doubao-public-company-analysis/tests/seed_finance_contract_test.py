#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_router():
    path = ROOT / "scripts/search_router.py"
    spec = importlib.util.spec_from_file_location("company_seed_router", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    runtime = json.loads((ROOT / "config/runtime.json").read_text(encoding="utf-8"))
    loading = json.loads(
        (ROOT / "config/loading-profile.json").read_text(encoding="utf-8")
    )
    assert "name: company-analysis-seed-finance" in skill
    assert runtime["case_type"] == "company-analysis-seed-finance"
    contract = runtime["search_contract"]
    assert contract["primary_tool"] == "seed_finance_search"
    assert contract["fallback"] == "general_search"
    assert contract["off_means_zero_calls"] is True
    assert contract["database_numbers_are_company_disclosure"] is False
    assert contract[
        "authoritative_financial_database_may_support_standard_fields"
    ] is True
    assert contract["internal_estimates_are_company_disclosure"] is False
    assert contract["routing_policy"] == "claim_driven"
    assert contract["first_party_anchor_tool"] == "general_search"
    assert contract["financial_data_tool"] == "seed_finance_search"
    assert contract["empty_result_is_covered"] is False
    assert contract["cross_scope_range_or_ranking_allowed"] is False
    assert contract["supported_requires_sufficient_source_role"] is True
    assert contract["secondary_only_critical_claim_status"] == "provisional"
    assert contract["trace_policy"]["model_summary_is_raw_trace"] is False
    assert contract["max_calls_is_hard_limit"] is True
    assert contract["supported_required_for_verified_fact_label"] is True
    assert contract["all_critical_provisional_blocks_definitive_conclusion"] is True
    assert contract["script_execution_evidence"][
        "help_or_import_is_task_execution"
    ] is False
    assert contract["output_claim_policy"][
        "all_external_numbers_must_exist_in_claim_ledger"
    ] is True
    assert set(contract["required_artifacts"]) == {
        "query_log",
        "evidence_atoms",
        "coverage_gaps",
        "claim_ledger",
    }
    assert all(
        "seed-finance-search-routing.md" in refs
        for refs in loading["mode_references"].values()
    )
    assert all(
        "online-agent-execution-contract.md" in refs
        for refs in loading["mode_references"].values()
    )

    router = load_router()
    required = router.plan(
        router.infer_signals(
            "company-analysis-seed-finance",
            "分析示例公司 TEST 在美国市场 FY2025 收入与年报，截至2026-06-30。",
            {"object_frozen": True, "jurisdiction_frozen": True, "as_of": "2026-06-30"},
        )
    )
    assert required["mode"] == "required"
    assert required["tool_order"] == ["seed_finance_search", "general_search"]
    assert required["fallback_tool_order"] == ["general_search"]
    assert required["max_calls"] == 5
    assert "as_of" in required["query_required_dimensions"]
    assert required["first_external_call"] == (
        "claim_driven:highest_priority_evidence_slot"
    )
    assert required["repair_calls_reserved_min"] == 1
    assert required["max_calls_is_hard_limit"] is True

    natural = router.plan(
        router.infer_signals(
            "company-analysis-seed-finance",
            "示例科技股份有限公司的竞争优势是否持久？",
            {"object_frozen": True, "as_of": "2026-06-30"},
        )
    )
    assert natural["mode"] == "required"

    off = router.plan(
        router.infer_signals(
            "company-analysis-seed-finance",
            "仅使用封闭材料计算。",
            {"closed_fixture": True, "object_frozen": True},
        )
    )
    assert off["mode"] == "off"
    assert off["max_calls"] == 0
    print("PASS company-analysis seed finance contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
