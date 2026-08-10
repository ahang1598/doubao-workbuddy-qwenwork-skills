#!/usr/bin/env python3
"""Validate section admission and compression checks for research reports."""

import argparse
import json
import sys
import tempfile
from pathlib import Path


PROFILE_LIMITS = {"one_pager": 5, "standard": 8, "deep_dive": 12}
VISUAL_BUDGETS = {"one_pager": 1, "standard": 3, "deep_dive": 5}
ROLES = {"core_conclusion", "analysis", "risk", "validation", "appendix"}
VISUAL_FORMATS = {"html5_block", "svg_whiteboard", "mermaid_whiteboard"}
FINANCIAL_CATEGORIES = {
    "market_data",
    "valuation",
    "financial_scale",
    "growth",
    "profitability",
    "cash_flow",
    "balance_sheet",
    "capital_efficiency",
}
OPERATING_FINANCIAL_CATEGORIES = {
    "financial_scale",
    "growth",
    "profitability",
    "cash_flow",
    "balance_sheet",
    "capital_efficiency",
}
FINANCIAL_NOT_RELEVANT_CODES = {
    "single_fact_query",
    "narrow_nonfinancial_scope",
    "user_explicitly_excluded",
    "other_material_reason",
}
EVIDENCE_QUALITY = {
    "primary",
    "standardized_data",
    "consensus",
    "derived",
    "authoritative_media",
    "supported_inference",
    "mixed",
}
FINAL_CHECKS = (
    "conclusion_first",
    "answers_core_question_directly",
    "no_generic_background",
    "no_unranked_news_dump",
    "no_repeated_claims",
    "tables_answer_one_question",
    "visuals_have_information_job",
    "visuals_rendered_and_legible",
    "visuals_nonredundant",
    "visual_sources_units_complete",
    "visual_text_fallbacks_present",
    "only_material_data_gaps",
    "low_quality_content_removed",
    "compression_pass_completed",
)
KLINE_EXCEPTION_CODES = {
    "missing_complete_ohlc",
    "no_continuous_trading_series",
    "universe_too_large_for_readable_kline",
    "incompatible_windows_or_frequency",
    "user_explicitly_declined",
    "single_price_point_only",
    "other_material_reason",
}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def load_manifest(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("质量清单顶层必须是 JSON 对象")
    return data


def validate_manifest(data, phase):
    errors = []
    if not nonempty(data.get("core_question")):
        errors.append("core_question 必须是非空字符串")

    profile = data.get("document_profile")
    if profile not in PROFILE_LIMITS:
        errors.append("document_profile 必须是 one_pager、standard 或 deep_dive")
    if profile == "deep_dive" and not nonempty(data.get("deep_dive_reason")):
        errors.append("deep_dive 必须提供不可压缩的 deep_dive_reason")

    snapshot = data.get("core_financial_snapshot")
    if not isinstance(snapshot, dict):
        errors.append("core_financial_snapshot 必须是对象")
        snapshot = {}
    snapshot_status = snapshot.get("status")
    if snapshot_status == "included":
        companies = snapshot.get("companies")
        if not isinstance(companies, list) or len(companies) < 2:
            errors.append("核心财务金融快照 included 时 companies 至少包含 2 家公司")
        elif any(not nonempty(company) for company in companies):
            errors.append("核心财务金融快照 companies 只能包含非空字符串")
        elif len({company.strip() for company in companies}) != len(companies):
            errors.append("核心财务金融快照 companies 不得重复")

        metrics = snapshot.get("metrics")
        if not isinstance(metrics, list) or len(metrics) < 5:
            errors.append("核心财务金融快照 included 时 metrics 至少包含 5 个指标")
        elif any(not nonempty(metric) for metric in metrics):
            errors.append("核心财务金融快照 metrics 只能包含非空字符串")
        elif len({metric.strip() for metric in metrics}) != len(metrics):
            errors.append("核心财务金融快照 metrics 不得重复")

        categories = snapshot.get("metric_categories")
        if not isinstance(categories, list):
            errors.append("核心财务金融快照 metric_categories 必须是数组")
            categories = []
        else:
            unknown_categories = [
                category for category in categories
                if category not in FINANCIAL_CATEGORIES
            ]
            if unknown_categories:
                errors.append(
                    "核心财务金融快照包含未知 metric_categories: "
                    + ", ".join(str(item) for item in unknown_categories)
                )
            if len(categories) != len(set(categories)):
                errors.append("核心财务金融快照 metric_categories 不得重复")
        if "market_data" not in categories:
            errors.append("核心财务金融快照必须覆盖 market_data")
        if "valuation" not in categories:
            errors.append("核心财务金融快照必须覆盖 valuation")
        if len(set(categories) & OPERATING_FINANCIAL_CATEGORIES) < 2:
            errors.append("核心财务金融快照至少覆盖两个经营财务类别")

        if snapshot.get("presentation") != "compact_comparison_table":
            errors.append(
                "核心财务金融快照 presentation 必须是 compact_comparison_table"
            )
        if not nonempty(snapshot.get("coverage")):
            errors.append("核心财务金融快照 included 时必须说明 coverage")
        snapshot_evidence = snapshot.get("evidence_ids")
        if not isinstance(snapshot_evidence, list) or not snapshot_evidence:
            errors.append("核心财务金融快照 evidence_ids 必须是非空数组")
        elif any(not nonempty(item) for item in snapshot_evidence):
            errors.append("核心财务金融快照 evidence_ids 只能包含非空字符串")
        if phase == "final":
            for field in (
                "valuation_date_verified",
                "periods_aligned_or_labeled",
                "currency_units_complete",
                "missing_values_not_fabricated",
            ):
                if snapshot.get(field) is not True:
                    errors.append(f"核心财务金融快照 final 阶段要求 {field}=true")
    elif snapshot_status == "not_relevant":
        if snapshot.get("reason_code") not in FINANCIAL_NOT_RELEVANT_CODES:
            errors.append("核心财务金融快照不相关时 reason_code 不在允许枚举内")
        if not nonempty(snapshot.get("reason")):
            errors.append("核心财务金融快照不相关时必须提供具体 reason")
        if not nonempty(snapshot.get("decision_impact")):
            errors.append("核心财务金融快照不相关时必须说明 decision_impact")
    else:
        errors.append(
            "core_financial_snapshot.status 必须是 included 或 not_relevant"
        )

    price_analysis = data.get("price_analysis")
    if not isinstance(price_analysis, bool):
        errors.append("price_analysis 必须是布尔值")
    kline_plan = data.get("kline_plan")
    if not isinstance(kline_plan, dict):
        errors.append("kline_plan 必须是对象")
        kline_plan = {}
    status = kline_plan.get("status")
    if price_analysis is True:
        if status == "included":
            if not nonempty(kline_plan.get("coverage")):
                errors.append("K 线 included 时必须说明 coverage")
            kline_evidence = kline_plan.get("evidence_ids")
            if not isinstance(kline_evidence, list) or not kline_evidence:
                errors.append("K 线 included 时 evidence_ids 必须是非空数组")
            elif any(not nonempty(item) for item in kline_evidence):
                errors.append("K 线 evidence_ids 只能包含非空字符串")
            if phase == "final":
                if kline_plan.get("rendering_verified") is not True:
                    errors.append("K 线 included 的 final 阶段要求 rendering_verified=true")
                if kline_plan.get("same_window_frequency_adjustment_verified") is not True:
                    errors.append(
                        "K 线 included 的 final 阶段要求 same_window_frequency_adjustment_verified=true"
                    )
        elif status == "not_applicable":
            if kline_plan.get("reason_code") not in KLINE_EXCEPTION_CODES:
                errors.append("K 线不适用时 reason_code 不在允许枚举内")
            if not nonempty(kline_plan.get("reason")):
                errors.append("K 线不适用时必须给出具体 reason")
        else:
            errors.append("price_analysis=true 时 K 线 status 必须是 included 或 not_applicable")
    elif price_analysis is False and status != "not_needed":
        errors.append("price_analysis=false 时 K 线 status 必须是 not_needed")

    visual_plan = data.get("visual_plan")
    if not isinstance(visual_plan, list):
        errors.append("visual_plan 必须是数组；没有图表时使用空数组")
        visual_plan = []
    visual_ids = set()
    redundancy_groups = set()
    included_visuals = []
    for index, visual in enumerate(visual_plan):
        prefix = f"visual_plan[{index}]"
        if not isinstance(visual, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        visual_id = visual.get("id")
        if not nonempty(visual_id):
            errors.append(f"{prefix}.id 必须是非空字符串")
        elif visual_id.strip() in visual_ids:
            errors.append(f"图表 id 重复: {visual_id.strip()}")
        else:
            visual_ids.add(visual_id.strip())
        include = visual.get("include")
        if not isinstance(include, bool):
            errors.append(f"{prefix}.include 必须是布尔值")
            continue
        if not include:
            if not nonempty(visual.get("exclusion_reason")):
                errors.append(f"{prefix} 排除时必须说明 exclusion_reason")
            continue

        included_visuals.append(visual)
        for field, label in (
            ("title", "title"),
            ("chart_type", "chart_type"),
            ("information_job", "information_job"),
            ("decision_relevance", "decision_relevance"),
            ("reader_takeaway", "reader_takeaway"),
            ("why_visual_beats_text_or_table", "why_visual_beats_text_or_table"),
            ("redundancy_group", "redundancy_group"),
        ):
            if not nonempty(visual.get(field)):
                errors.append(f"{prefix}.{label} 必须是非空字符串")
        if visual.get("format") not in VISUAL_FORMATS:
            errors.append(
                f"{prefix}.format 必须是 html5_block、svg_whiteboard 或 mermaid_whiteboard"
            )
        if visual.get("new_information") is not True:
            errors.append(f"{prefix}.new_information 必须为 true")
        evidence_ids = visual.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            errors.append(f"{prefix}.evidence_ids 必须是非空数组")
        elif any(not nonempty(item) for item in evidence_ids):
            errors.append(f"{prefix}.evidence_ids 只能包含非空字符串")
        group = visual.get("redundancy_group")
        if nonempty(group):
            normalized_group = group.strip()
            if normalized_group in redundancy_groups:
                errors.append(
                    f"图表 redundancy_group 重复: {normalized_group}；同一信息任务只能保留一个视觉家族"
                )
            else:
                redundancy_groups.add(normalized_group)
        if phase == "final":
            for field in (
                "rendering_verified",
                "source_and_units_verified",
                "text_summary_present",
            ):
                if visual.get(field) is not True:
                    errors.append(f"{prefix} final 阶段要求 {field}=true")

    if profile in VISUAL_BUDGETS and len(included_visuals) > VISUAL_BUDGETS[profile]:
        if not nonempty(data.get("visual_budget_reason")):
            errors.append(
                f"{profile} 默认最多 {VISUAL_BUDGETS[profile]} 个视觉家族；超出时必须提供 visual_budget_reason"
            )

    if price_analysis is True and status == "included":
        kline_visuals = [
            visual for visual in included_visuals
            if visual.get("chart_type") == "kline"
            and visual.get("format") == "html5_block"
        ]
        if len(kline_visuals) != 1:
            errors.append(
                "K 线 included 时 visual_plan 必须且只能有一个 chart_type=kline、format=html5_block 的视觉家族"
            )

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections 必须是非空数组")
        sections = []

    seen_titles = set()
    included = []
    for index, section in enumerate(sections):
        prefix = f"sections[{index}]"
        if not isinstance(section, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        title = section.get("title")
        if not nonempty(title):
            errors.append(f"{prefix}.title 必须是非空字符串")
        elif title.strip() in seen_titles:
            errors.append(f"章节标题重复: {title.strip()}")
        else:
            seen_titles.add(title.strip())

        include = section.get("include")
        if not isinstance(include, bool):
            errors.append(f"{prefix}.include 必须是布尔值")
            continue
        if not include:
            if not nonempty(section.get("exclusion_reason")):
                errors.append(f"{prefix} 排除时必须说明 exclusion_reason")
            continue

        included.append(section)
        role = section.get("role")
        if role not in ROLES:
            errors.append(f"{prefix}.role 不在允许枚举内")
        if not nonempty(section.get("decision_relevance")):
            errors.append(f"{prefix}.decision_relevance 必须说明如何改变判断")
        if section.get("new_information") is not True:
            errors.append(f"{prefix}.new_information 必须为 true")
        if not nonempty(section.get("reader_takeaway")):
            errors.append(f"{prefix}.reader_takeaway 必须是非空字符串")
        if section.get("evidence_quality") not in EVIDENCE_QUALITY:
            errors.append(f"{prefix}.evidence_quality 不在允许枚举内")
        evidence_ids = section.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            errors.append(f"{prefix}.evidence_ids 必须是非空数组")
        elif any(not nonempty(item) for item in evidence_ids):
            errors.append(f"{prefix}.evidence_ids 只能包含非空字符串")

    if profile in PROFILE_LIMITS and len(included) > PROFILE_LIMITS[profile]:
        errors.append(
            f"{profile} 最多包含 {PROFILE_LIMITS[profile]} 个分析章节，当前为 {len(included)}"
        )
    core_positions = [i for i, section in enumerate(included) if section.get("role") == "core_conclusion"]
    if len(core_positions) != 1:
        errors.append("必须且只能有一个 include=true 的 core_conclusion")
    elif core_positions[0] != 0:
        errors.append("core_conclusion 必须是第一个保留章节")

    if phase == "final":
        checks = data.get("document_checks")
        if not isinstance(checks, dict):
            errors.append("final 阶段必须提供 document_checks 对象")
        else:
            for name in FINAL_CHECKS:
                if checks.get(name) is not True:
                    errors.append(f"final 阶段要求 document_checks.{name}=true")
    return errors


def run_self_test():
    valid = {
        "core_question": "A 与 B 谁的盈利兑现更强？",
        "document_profile": "standard",
        "deep_dive_reason": "",
        "core_financial_snapshot": {
            "status": "included",
            "companies": ["公司 A", "公司 B"],
            "metrics": [
                "price",
                "market_cap",
                "revenue_ttm",
                "operating_margin_ttm",
                "free_cash_flow_ttm",
                "forward_pe",
            ],
            "metric_categories": [
                "market_data",
                "valuation",
                "financial_scale",
                "profitability",
                "cash_flow",
            ],
            "presentation": "compact_comparison_table",
            "coverage": "同一估值日与共同 TTM",
            "evidence_ids": ["snapshot-a", "snapshot-b"],
            "valuation_date_verified": True,
            "periods_aligned_or_labeled": True,
            "currency_units_complete": True,
            "missing_values_not_fabricated": True,
        },
        "price_analysis": False,
        "kline_plan": {"status": "not_needed"},
        "visual_plan": [],
        "visual_budget_reason": "",
        "sections": [
            {
                "title": "核心结论",
                "include": True,
                "role": "core_conclusion",
                "decision_relevance": "直接回答选择问题",
                "new_information": True,
                "reader_takeaway": "A 当前兑现更强，但订单放缓会翻转判断",
                "evidence_quality": "mixed",
                "evidence_ids": ["claim-a-margin", "claim-a-orders"],
            },
            {
                "title": "普通公司简介",
                "include": False,
                "exclusion_reason": "不改变比较结论且属于常识背景",
            },
        ],
        "document_checks": {name: True for name in FINAL_CHECKS},
    }
    assert not validate_manifest(valid, "plan")
    assert not validate_manifest(valid, "final")

    bad_order = json.loads(json.dumps(valid))
    bad_order["sections"].insert(
        0,
        {
            "title": "先写背景",
            "include": True,
            "role": "analysis",
            "decision_relevance": "提供上下文",
            "new_information": True,
            "reader_takeaway": "背景",
            "evidence_quality": "primary",
            "evidence_ids": ["claim-bg"],
        },
    )
    assert validate_manifest(bad_order, "plan")

    bad_checks = json.loads(json.dumps(valid))
    bad_checks["document_checks"]["compression_pass_completed"] = False
    assert validate_manifest(bad_checks, "final")

    too_long = json.loads(json.dumps(valid))
    too_long["document_profile"] = "one_pager"
    template = {
        "include": True,
        "role": "analysis",
        "decision_relevance": "改变排序",
        "new_information": True,
        "reader_takeaway": "新增判断",
        "evidence_quality": "primary",
        "evidence_ids": ["claim-x"],
    }
    for index in range(5):
        section = dict(template)
        section["title"] = f"分析 {index}"
        too_long["sections"].append(section)
    assert validate_manifest(too_long, "plan")

    price_valid = json.loads(json.dumps(valid))
    price_valid["price_analysis"] = True
    price_valid["kline_plan"] = {
        "status": "included",
        "coverage": "全部两只比较标的，同窗口日线",
        "evidence_ids": ["ohlc-a", "ohlc-b"],
        "rendering_verified": True,
        "same_window_frequency_adjustment_verified": True,
    }
    price_valid["visual_plan"] = [
        {
            "id": "price-kline-family",
            "include": True,
            "title": "A/B 同窗口价格路径",
            "chart_type": "kline",
            "format": "html5_block",
            "information_job": "核对价格路径、波动与事件窗口",
            "decision_relevance": "区分端点收益相同但路径风险不同的标的",
            "new_information": True,
            "reader_takeaway": "A 的事件后波动收敛快于 B",
            "why_visual_beats_text_or_table": "路径、影线和波动聚集无法由端点表格完整表达",
            "evidence_ids": ["ohlc-a", "ohlc-b"],
            "redundancy_group": "price-path",
            "rendering_verified": True,
            "source_and_units_verified": True,
            "text_summary_present": True,
        }
    ]
    assert not validate_manifest(price_valid, "plan")
    assert not validate_manifest(price_valid, "final")

    bad_price = json.loads(json.dumps(valid))
    bad_price["price_analysis"] = True
    bad_price["kline_plan"] = {"status": "not_needed"}
    assert validate_manifest(bad_price, "plan")

    price_exception = json.loads(json.dumps(valid))
    price_exception["price_analysis"] = True
    price_exception["kline_plan"] = {
        "status": "not_applicable",
        "reason_code": "missing_complete_ohlc",
        "reason": "仅取得收盘价，不能补造开高低",
    }
    assert not validate_manifest(price_exception, "final")

    duplicate_visual = json.loads(json.dumps(price_valid))
    second_visual = json.loads(json.dumps(duplicate_visual["visual_plan"][0]))
    second_visual["id"] = "duplicate-price-chart"
    duplicate_visual["visual_plan"].append(second_visual)
    assert validate_manifest(duplicate_visual, "final")

    missing_render_check = json.loads(json.dumps(price_valid))
    missing_render_check["visual_plan"][0]["rendering_verified"] = False
    assert validate_manifest(missing_render_check, "final")

    snapshot_not_relevant = json.loads(json.dumps(valid))
    snapshot_not_relevant["core_financial_snapshot"] = {
        "status": "not_relevant",
        "reason_code": "single_fact_query",
        "reason": "只核对同口径毛利率定义",
        "decision_impact": "其他财务数据不会改变该定义性答案",
    }
    assert not validate_manifest(snapshot_not_relevant, "final")

    missing_snapshot = json.loads(json.dumps(valid))
    missing_snapshot.pop("core_financial_snapshot")
    assert validate_manifest(missing_snapshot, "plan")

    weak_snapshot = json.loads(json.dumps(valid))
    weak_snapshot["core_financial_snapshot"]["metric_categories"] = [
        "market_data",
        "valuation",
        "profitability",
    ]
    assert validate_manifest(weak_snapshot, "plan")

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "quality.json"
        path.write_text(json.dumps(valid, ensure_ascii=False), encoding="utf-8")
        assert not validate_manifest(load_manifest(path), "final")
    print("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(description="校验报告章节准入与最终压缩状态")
    parser.add_argument("manifest", nargs="?", help="质量清单 JSON 路径")
    parser.add_argument("--phase", choices=("plan", "final"), default="final")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    if args.self_test:
        run_self_test()
        return 0
    if not args.manifest:
        sys.stderr.write("错误: 必须提供质量清单 JSON 路径\n")
        return 2
    try:
        errors = validate_manifest(load_manifest(args.manifest), args.phase)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(f"错误: {exc}\n")
        return 2
    if errors:
        for error in errors:
            sys.stderr.write(f"质量门禁失败: {error}\n")
        return 1
    manifest = load_manifest(args.manifest)
    included = sum(1 for section in manifest["sections"] if section.get("include"))
    included_visuals = sum(
        1 for visual in manifest.get("visual_plan", []) if visual.get("include")
    )
    print(
        f"EDITORIAL_GATE_PASS phase={args.phase} "
        f"core_financial_snapshot={manifest['core_financial_snapshot']['status']} "
        f"included_sections={included} included_visual_families={included_visuals}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
