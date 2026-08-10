#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    skill = (ROOT / "SKILL.md").read_text()
    online = (ROOT / "references/online-agent-execution-contract.md").read_text()
    runtime = json.loads((ROOT / "config/runtime.json").read_text())
    loading = json.loads((ROOT / "config/loading-profile.json").read_text())
    contract = runtime["search_contract"]
    for term in ("full_runtime", "hybrid_runtime", "agent_only"):
        assert term in skill
    assert "线上最高优先级规则" in skill
    assert "事件状态：已发布（发布方·文件名·日期）" in skill
    assert "无法判断priced-in，需要以下基线" in skill
    assert "`--help`" in online and "raw_trace_unavailable" in online
    assert "online_direct_fast_path" in online
    assert "必须从用户正文删除" in online
    assert "Seed空结果不产生额外General额度" in online
    assert "provisional estimate" in online
    assert contract["max_calls_is_hard_limit"] is True
    assert contract["event_identity_status_requires_primary_general_search"] is True
    assert contract["authoritative_financial_database_may_support_market_and_standard_exposure_fields"] is True
    assert contract["seed_is_event_primary_source"] is False
    assert contract["transport_status_separate_from_evidence_status"] is True
    assert contract["trace_policy"]["model_summary_is_raw_trace"] is False
    assert contract["output_claim_policy"]["provisional_event_identity_blocks_quantification"] is True
    assert loading["runtime_profiles"]["agent_only"]["may_claim_scripts_ran"] is False
    assert all(any("online-agent-execution-contract.md" in ref for ref in refs)
               for refs in loading["mode_references"].values())
    print("PASS event-impact online Agent contract")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
