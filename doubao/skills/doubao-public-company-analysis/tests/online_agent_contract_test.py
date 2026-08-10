#!/usr/bin/env python3
"""Generic contract checks for the online Agent execution profile."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    online = (
        ROOT / "references/online-agent-execution-contract.md"
    ).read_text(encoding="utf-8")
    quality = (ROOT / "references/quality-gates.md").read_text(encoding="utf-8")
    runtime = json.loads(
        (ROOT / "config/runtime.json").read_text(encoding="utf-8")
    )
    loading = json.loads(
        (ROOT / "config/loading-profile.json").read_text(encoding="utf-8")
    )

    assert "`full_runtime`" in skill
    assert "`hybrid_runtime`" in skill
    assert "`agent_only`" in skill
    assert "不得声称运行过脚本" in skill
    assert "不得拼成区间、排名或倍数" in skill
    assert "代理指标" in skill

    required_online_rules = [
        "工具顺序不是为了各调用一次而固定",
        "每条查询写成一个可回答的问题",
        "工具调用成功但没有返回有效文档或字段时",
        "不得拼成数值区间",
        "不得跨口径排名或计算倍数",
        "替代解释",
        "无脚本内联自检",
        "不得把模型摘要标成“工具原始输出”",
        "多家二手来源重复同一说法不会自动升级",
        "精确阈值必须来自历史分布",
        "raw_trace_unavailable",
        "运行 `--help`",
        "5 次是硬上限",
        "每个外部数字、精确比例、日期",
        "不得用 ROE 代替 ROIC",
    ]
    for rule in required_online_rules:
        assert rule in online, rule

    forbidden_case_terms = [
        "泡泡" + "玛特",
        "LAB" + "UBU",
        "会员贡献93.7",
        "52" + "TOYS",
        "TOP" + " TOY",
    ]
    for term in forbidden_case_terms:
        assert term not in online, term

    contract = runtime["search_contract"]
    assert contract["routing_policy"] == "claim_driven"
    assert contract["empty_result_is_covered"] is False
    assert contract["cross_scope_range_or_ranking_allowed"] is False
    assert contract["secondary_only_critical_claim_allowed"] is False
    assert contract["secondary_only_critical_claim_status"] == "provisional"
    assert contract["inference_policy"][
        "cross_scope_profit_cashflow_subtraction_allowed"
    ] is False
    assert contract["trace_policy"]["model_summary_is_raw_trace"] is False
    assert contract["script_execution_evidence"][
        "help_or_import_is_task_execution"
    ] is False
    assert contract["output_claim_policy"][
        "provisional_may_be_called_verified_fact"
    ] is False
    assert contract["inference_policy"]["roe_may_substitute_for_roic"] is False
    assert contract["runtime_profiles"]["agent_only"].endswith(
        "online-agent-execution-contract.md"
    )

    assert loading["runtime_profiles"]["hybrid_runtime"][
        "may_claim_unexecuted_scripts_ran"
    ] is False
    assert loading["runtime_profiles"]["full_runtime"][
        "help_or_import_counts_as_execution"
    ] is False
    assert loading["runtime_profiles"]["agent_only"][
        "may_claim_scripts_ran"
    ] is False
    assert loading["runtime_profiles"]["agent_only"][
        "global_degrade_because_scripts_unavailable"
    ] is False
    assert loading["search"]["tool_order"] == [
        "seed_finance_search",
        "general_search",
    ]
    assert loading["search"][
        "authoritative_financial_database_standard_fields_may_be_supported"
    ] is True
    assert "不同年份、地域、品类、分母或指标类型" in quality

    print("PASS company-analysis online Agent generic contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
