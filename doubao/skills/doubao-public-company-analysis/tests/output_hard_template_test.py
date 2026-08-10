#!/usr/bin/env python3
"""断言线上输出硬模板机制存在于 SKILL、线上契约与 runtime 配置中。

只检查机制，不检查任何评测实体、公司名或答案。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKILL_PHRASES = (
    "线上最高优先级规则：输出硬模板",
    "规则1 身份与前提核验，与问题长短无关",
    "规则2 精确数字逐条带来源标记",
    "规则3 关键输入缺失时改写成分档表",
    "规则4 无一手来源的量级只能进假设卡",
    "规则5 开头固定为可审计摘要",
    "写作顺序在最后",
    "原样摘抄一句",
    "`[待核·…]` 的数字一律不进摘要",
    "`[阈值·分析设定]`",
    "摘要每一行只能来自一次摘抄",
    "这一步是前置判断，不是事后补救",
    "[一手·发布方·文件名·日期]",
    "[库·provider·as_of]",
    "[待核·模型记忆]",
    "[用户·自述]",
    "[推算·公式]",
    "存在证券代码、存在 IR 页面或能查到财报，都不能证明当前仍在上市",
    "必须先用可核验数据检验方向和幅度",
    "会计质量类断言",
    "不给买卖评级、目标价、仓位和止损",
    "摘要纪律（可执行判据）",
    "档内不得出现绝对金额",
    "复杂度路由只决定篇幅和槽位数量，不决定是否核验",
    "不要删掉数字",
    "不得用减少分析深度的方式满足本节",
    "本Skill补充（同等优先级）",
    "第一节固定为规则5的可审计摘要",
)

CONTRACT_PHRASES = (
    "输出硬模板执行细则",
    "补检索 → 补标记 → 改分档表 → 进假设卡",
    "不以\"数字是否被删除\"衡量",
)

FASTPATH_PHRASE = "快速路径只压缩产物和篇幅，不减少规则1的核验"


def main():
    skill = (ROOT / "SKILL.md").read_text()
    contract = (ROOT / "references/online-agent-execution-contract.md").read_text()
    runtime = json.loads((ROOT / "config/runtime.json").read_text())
    template = runtime["search_contract"]["output_hard_template"]

    for phrase in SKILL_PHRASES:
        assert phrase in skill, f"SKILL.md 缺少: {phrase}"
    for phrase in CONTRACT_PHRASES:
        assert phrase in contract, f"线上契约缺少: {phrase}"
    assert FASTPATH_PHRASE in skill, "快速路径未绑定身份核验义务"

    assert template["identity_verification_independent_of_complexity"] is True
    assert template["inline_source_tag_required_per_number"] is True
    assert template["blanket_source_statement_satisfies_tagging"] is False
    assert template["unsourced_number_action"] == "tag_as_pending_not_delete_and_not_vague"
    assert template["missing_input_action"] == "conditional_tier_table_not_assumption_not_refusal"
    assert template["unsourced_magnitude_container"] == "assumption_card"
    assert template["assumption_card_numbers_may_appear_in_conclusion"] is False
    assert template["peer_parameter_inheritance_allowed"] is False
    assert template["auditable_summary_first"] is True
    assert template["auditable_summary_max_lines"] == 5
    assert template["summary_written_last_placed_first"] is True
    assert template["summary_numbers_must_be_copied_from_body"] is True
    assert template["summary_strongest_evidence_is_verbatim_copy"] is True
    assert template["summary_may_contain_freshly_written_numbers"] is False
    assert template["summary_self_check_locate_original_sentence"] is True
    assert set(template["source_tag_vocabulary"]) == {
        "一手", "库", "用户", "推算", "待核", "阈值"}
    assert template["analyst_set_threshold_requires_explicit_tag"] is True
    assert template["threshold_must_state_it_is_set_not_observed"] is True
    assert template["summary_line_is_single_verbatim_copy"] is True
    assert template["summary_line_may_append_after_copy"] is False
    assert template["summary_fallback_is_precheck_result"] is True
    assert template["falsification_line_exempt_from_copy_rule"] is True
    assert template["falsification_threshold_requires_threshold_tag"] is True
    assert template["summary_may_downgrade_to_pending_evidence"] is False
    assert template["template_may_reduce_analysis_depth"] is False
    assert template["every_number_must_have_a_tag_class"] is True
    assert template["user_stated_facts_need_no_external_source"] is True
    assert template["derived_value_tag_requires_inputs_and_formula"] is True
    assert template["generic_default_ranges_must_be_tier_variables"] is True
    assert template["summary_allows_only_primary_db_or_user_tags"] is True
    listing = template["listing_status_evidence"]
    assert listing["ticker_or_ir_page_proves_current_listing"] is False
    assert template["user_premise_must_be_data_checked_before_answering"] is True
    assert template["accounting_claims_require_notes_or_segment_data"] is True
    assert template["rating_target_price_or_position_allowed"] is False
    assert template["absolute_amount_ban_applies_to_whole_response"] is True
    assert len(template["verify_before_conclusion"]) == 4

    # 硬模板不得内联任何具体实体、代码或行业结论
    for banned in ("泡泡玛特", "可灵", "Lawson", "FamilyMart", "2651.T"):
        assert banned not in skill, f"SKILL.md 出现评测实体: {banned}"

    print(f"PASS output hard template ({ROOT.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
