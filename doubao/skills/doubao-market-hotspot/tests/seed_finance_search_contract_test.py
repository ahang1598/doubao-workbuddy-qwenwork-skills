#!/usr/bin/env python3
"""Generic fictional contract tests for event Seed Finance Search routing."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from event_runtime_guard import guard  # noqa: E402
from search_router import plan  # noqa: E402


LEDGER_FIELDS = [
    "tool",
    "query",
    "asof",
    "source",
    "period",
    "unit",
    "currency",
    "reported-vs-estimate",
]


def main():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.search(r"^---\n(.*?)\n---", skill, re.S).group(1)
    assert "name: doubao-market-hotspot" in frontmatter

    profile = json.loads((ROOT / "config/loading-profile.json").read_text())
    runtime = json.loads((ROOT / "config/runtime.json").read_text())
    contract = runtime["seed_finance_search"]

    assert profile["search"]["tool_order"] == [
        "general_search",
        "seed_finance_search",
    ]
    assert profile["search"]["official_general_first"] is True
    assert contract["schema_policy"] == "use_host_actual_schema_do_not_invent_parameters"
    assert contract["fallback"] == "general_search"
    assert contract["library_result_is_primary"] is False
    assert contract["ledger_fields"] == LEDGER_FIELDS
    routed = plan(
        {
            "skill": "event-impact-analysis",
            "object_frozen": True,
            "event_type": "regulatory",
            "needs_current_public_facts": True,
            "needs_public_rules": True,
        }
    )
    assert routed["tool_order"] == ["general_search", "seed_finance_search"]
    assert routed["source_order"][0] == "issuing_authority"
    assert routed["seed_finance_policy"][
        "missing_pre_event_baseline_can_assess_priced_in"
    ] is False

    fictional_event = {
        "status": "completed",
        "gates": {
            "primary_source_gate_passed": True,
            "semantic_gate_passed": True,
        },
        "search": {"mode": "optional"},
        "claims": [
            {
                "id": "fictional-event",
                "claim_type": "event_identity",
                "critical": True,
                "supported": True,
                "source_ids": ["fictional-official-document"],
            },
            {
                "id": "fictional-status",
                "claim_type": "event_status",
                "critical": True,
                "supported": True,
                "source_ids": ["fictional-official-document"],
            },
        ],
        "market_evidence": [],
    }
    guarded = guard(fictional_event)
    assert guarded["may_deliver"] is True
    assert guarded["can_assess_priced_in"] is False
    assert contract["missing_pre_event_baseline"]["can_assess_priced_in"] is False
    assert "事件原文、法规状态、辖区和生效日优先" in skill

    reference = (
        ROOT / "references/seed-finance-search-routing.md"
    ).read_text(encoding="utf-8")
    for field in LEDGER_FIELDS:
        assert f"`{field}`" in reference
    assert "不得发明工具名、字段或参数" in reference
    print("PASS event-impact Seed Finance Search fictional contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
