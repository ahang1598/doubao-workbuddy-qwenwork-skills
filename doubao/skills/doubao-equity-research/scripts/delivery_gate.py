#!/usr/bin/env python3
"""Validate the planned and final delivery state for equity research."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


TEXT_CHECKS = (
    "single_decision_question",
    "core_conclusion_within_three_sentences",
    "no_structured_comparison_or_navigation",
    "no_advanced_component_needed_or_generated",
)
QUALITY_CHECKS = (
    "conclusion_first",
    "every_section_changes_decision",
    "evidence_traceable_and_current",
    "low_quality_information_removed",
    "redundant_content_removed",
    "styles_serve_content",
    "required_structure_preserved",
    "logic_chain_explicit",
    "reader_navigation_clear",
    "accounting_bases_unambiguous",
)
VISUAL_CHECKS = (
    "unique_decision_question",
    "source_units_labeled",
    "no_duplicate_encoding",
    "rendering_verified",
)
HTML_BLOCK_CHECKS = (
    "embedded_in_lark_document",
    "source_file_not_delivered",
)
KLINE_STATUSES = {"included", "not_applicable", "not_price_analysis"}
KLINE_EXCEPTIONS = {
    "user_declined_visual",
    "single_point_question",
    "reliable_ohlc_unavailable",
    "multi_asset_comparison",
    "corporate_action_or_data_break",
    "price_path_not_relevant",
}
DELIVERY_MODES = {"TEXT", "LARK_DOC"}
CORE_FINANCIAL_DATA_STATUSES = {
    "planned",
    "included",
    "included_with_gaps",
    "not_relevant",
}


def is_visual_component(name):
    markers = (
        "html_block", "kline", "trend", "waterfall", "heatmap",
        "timeline", "quadrant", "flow",
    )
    return isinstance(name, str) and any(marker in name for marker in markers)


def emit(message):
    sys.stderr.write(f"{message}\n")


def load_manifest(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("交付清单顶层必须是 JSON 对象")
    return data


def valid_doc_url(value):
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return any(part in {"docx", "wiki"} for part in parts)


def validate_string_list(data, field, errors, minimum=0, maximum=None):
    value = data.get(field)
    if not isinstance(value, list):
        errors.append(f"{field} 必须是数组")
        return []
    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field}[{index}] 必须是非空字符串")
        else:
            normalized.append(item.strip())
    if len(normalized) != len(set(normalized)):
        errors.append(f"{field} 不得重复")
    if len(normalized) < minimum:
        errors.append(f"{field} 至少需要 {minimum} 项")
    if maximum is not None and len(normalized) > maximum:
        errors.append(f"{field} 最多允许 {maximum} 项")
    return normalized


def validate_manifest(data, phase):
    errors = []
    mode = data.get("delivery_mode")
    if mode not in DELIVERY_MODES:
        errors.append("delivery_mode 必须是 TEXT 或 LARK_DOC")

    reason = data.get("mode_reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("mode_reason 必须是非空字符串")

    components = validate_string_list(data, "advanced_components", errors)

    if phase == "final" and data.get("data_consistency_verified") is not True:
        errors.append("完成态要求 data_consistency_verified=true")

    core_status = data.get("core_financial_data_status")
    if core_status not in CORE_FINANCIAL_DATA_STATUSES:
        errors.append(
            "core_financial_data_status 必须是 planned、included、"
            "included_with_gaps 或 not_relevant"
        )
    if phase == "plan" and core_status not in {"planned", "not_relevant"}:
        errors.append(
            "计划态 core_financial_data_status 必须是 planned 或 not_relevant"
        )
    if phase == "final" and core_status not in {
        "included",
        "included_with_gaps",
        "not_relevant",
    }:
        errors.append(
            "完成态 core_financial_data_status 必须是 included、"
            "included_with_gaps 或 not_relevant，不能停留在 planned"
        )
    if core_status in {"planned", "included", "included_with_gaps"}:
        validate_string_list(
            data, "core_financial_data_fields", errors, minimum=1
        )
    if core_status == "not_relevant":
        core_reason = data.get("core_financial_data_reason")
        if not isinstance(core_reason, str) or not core_reason.strip():
            errors.append(
                "核心金融数据不相关时必须提供 core_financial_data_reason"
            )
    if core_status == "included_with_gaps":
        validate_string_list(
            data, "core_financial_data_gaps", errors, minimum=1
        )

    required_sections = []
    if mode == "LARK_DOC":
        required_sections = validate_string_list(
            data, "required_sections", errors, minimum=2, maximum=12
        )
        if phase == "final":
            actual_sections = validate_string_list(
                data, "actual_sections", errors, minimum=2
            )
            actual_set = set(actual_sections)
            for section in required_sections:
                if section not in actual_set:
                    errors.append(
                        f"actual_sections 缺少必需章节：{section}"
                    )

    visual_components = [
        component for component in components if is_visual_component(component)
    ]
    html_block_components = [
        component for component in components if "html_block" in component
    ]
    if visual_components:
        if mode != "LARK_DOC":
            errors.append("存在 HTML 视觉时 delivery_mode 必须是 LARK_DOC")
        visual_purposes = data.get("visual_purposes")
        purposes = []
        if not isinstance(visual_purposes, dict):
            errors.append("存在高级视觉时必须提供 visual_purposes 对象")
        else:
            for component in visual_components:
                purpose = visual_purposes.get(component)
                if not isinstance(purpose, str) or not purpose.strip():
                    errors.append(
                        f"visual_purposes.{component} 必须是非空的独立决策问题"
                    )
                else:
                    purposes.append(purpose.strip())
            normalized = [" ".join(purpose.lower().split()) for purpose in purposes]
            if len(normalized) != len(set(normalized)):
                errors.append("不同高级视觉不得使用相同 visual_purposes")

    scripted_price_components = [
        component
        for component in components
        if component in {"price_chart_html_block", "kline_html_block"}
    ]
    if scripted_price_components:
        generation_modes = data.get("chart_generation_modes")
        if not isinstance(generation_modes, dict):
            errors.append("股价图或 K 线必须提供 chart_generation_modes 对象")
        else:
            for component in scripted_price_components:
                mode_value = generation_modes.get(component)
                if mode_value != "script":
                    errors.append(
                        f"chart_generation_modes.{component} 必须是 script；"
                        "不得手写或手工兜底生成 HTML"
                    )

    price_analysis = data.get("price_analysis")
    kline_status = data.get("kline_status")
    if not isinstance(price_analysis, bool):
        errors.append("price_analysis 必须是布尔值")
    if kline_status not in KLINE_STATUSES:
        errors.append(
            "kline_status 必须是 included、not_applicable 或 not_price_analysis"
        )
    if price_analysis is False and kline_status != "not_price_analysis":
        errors.append("非股价分析必须设置 kline_status=not_price_analysis")
    if price_analysis is False and "kline_html_block" in components:
        errors.append("包含 kline_html_block 时 price_analysis 必须为 true")
    if price_analysis is False and "price_chart_html_block" in components:
        errors.append("包含 price_chart_html_block 时 price_analysis 必须为 true")
    if price_analysis is True:
        if kline_status == "not_price_analysis":
            errors.append("股价分析不得设置 kline_status=not_price_analysis")
        elif kline_status == "included":
            if mode != "LARK_DOC":
                errors.append("包含 K 线时 delivery_mode 必须是 LARK_DOC")
            if "kline_html_block" not in components:
                errors.append(
                    "包含 K 线时 advanced_components 必须列出 kline_html_block"
                )
        elif kline_status == "not_applicable":
            exception = data.get("kline_exception")
            if exception not in KLINE_EXCEPTIONS:
                errors.append(
                    "K 线不适用时必须提供允许的 kline_exception 枚举值"
                )

    if mode == "TEXT":
        checks = data.get("text_checks")
        if not isinstance(checks, dict):
            errors.append("TEXT 模式必须提供 text_checks 对象")
        else:
            for name in TEXT_CHECKS:
                if checks.get(name) is not True:
                    errors.append(f"TEXT 模式要求 text_checks.{name}=true")
        if components:
            errors.append("TEXT 模式不得包含任何 advanced_components；必须升级为 LARK_DOC")

    if phase == "final" and mode == "LARK_DOC":
        if data.get("doc_created") is not True:
            errors.append("LARK_DOC 完成态要求 doc_created=true")
        if not valid_doc_url(data.get("doc_url")):
            errors.append("LARK_DOC 完成态要求可访问的 /docx/ 或 /wiki/ URL")
        if data.get("fetch_verified") is not True:
            errors.append("LARK_DOC 完成态要求 fetch_verified=true")
        quality_checks = data.get("quality_checks")
        if not isinstance(quality_checks, dict):
            errors.append("LARK_DOC 完成态必须提供 quality_checks 对象")
        else:
            for name in QUALITY_CHECKS:
                if quality_checks.get(name) is not True:
                    errors.append(f"LARK_DOC 完成态要求 quality_checks.{name}=true")
        if visual_components:
            visual_checks = data.get("visual_checks")
            if not isinstance(visual_checks, dict):
                errors.append("含高级视觉的完成态必须提供 visual_checks 对象")
            else:
                for name in VISUAL_CHECKS:
                    if visual_checks.get(name) is not True:
                        errors.append(
                            f"含高级视觉的完成态要求 visual_checks.{name}=true"
                        )
        if html_block_components:
            html_block_checks = data.get("html_block_checks")
            if not isinstance(html_block_checks, dict):
                errors.append(
                    "含 HTML block 的完成态必须提供 html_block_checks 对象"
                )
            else:
                for name in HTML_BLOCK_CHECKS:
                    if html_block_checks.get(name) is not True:
                        errors.append(
                            f"含 HTML block 的完成态要求 "
                            f"html_block_checks.{name}=true"
                        )

    return errors


def run_self_test():
    text_manifest = {
        "delivery_mode": "TEXT",
        "mode_reason": "单一事实问题",
        "text_checks": {name: True for name in TEXT_CHECKS},
        "advanced_components": [],
        "data_consistency_verified": True,
        "core_financial_data_status": "not_relevant",
        "core_financial_data_reason": "单一事实问题不需金融与财务基线",
        "price_analysis": False,
        "kline_status": "not_price_analysis",
        "doc_created": False,
        "doc_url": "",
        "fetch_verified": False,
    }
    lark_plan = {
        "delivery_mode": "LARK_DOC",
        "mode_reason": "需要多章节和情景表",
        "text_checks": {},
        "advanced_components": ["rich_table"],
        "core_financial_data_status": "planned",
        "core_financial_data_fields": [
            "price",
            "market_cap",
            "revenue",
            "net_profit",
            "valuation",
        ],
        "required_sections": [
            "核心结论",
            "核心金融与财务快照",
            "主体分析",
            "风险与验证",
        ],
        "price_analysis": False,
        "kline_status": "not_price_analysis",
        "doc_created": False,
        "doc_url": "",
        "fetch_verified": False,
    }
    lark_final = dict(lark_plan)
    lark_final.update(
        core_financial_data_status="included",
        data_consistency_verified=True,
        actual_sections=list(lark_plan["required_sections"]),
        doc_created=True,
        doc_url="https://example.feishu.cn/docx/test_token",
        fetch_verified=True,
        quality_checks={name: True for name in QUALITY_CHECKS},
    )

    assert not validate_manifest(text_manifest, "plan")
    assert not validate_manifest(text_manifest, "final")
    assert not validate_manifest(lark_plan, "plan")
    assert validate_manifest(lark_plan, "final")
    assert not validate_manifest(lark_final, "final")

    bad_text = dict(text_manifest)
    bad_text["advanced_components"] = ["html_block"]
    assert validate_manifest(bad_text, "plan")

    bad_checks = dict(text_manifest)
    bad_checks["text_checks"] = dict(text_manifest["text_checks"])
    bad_checks["text_checks"]["single_decision_question"] = False
    assert validate_manifest(bad_checks, "plan")

    expanded_text = dict(text_manifest)
    expanded_text["text_checks"] = dict(text_manifest["text_checks"])
    expanded_text["text_checks"].pop("core_conclusion_within_three_sentences")
    expanded_text["text_checks"]["answer_within_three_short_paragraphs"] = True
    assert validate_manifest(expanded_text, "plan")

    bad_url = dict(lark_final)
    bad_url["doc_url"] = "https://example.feishu.cn/drive/folder"
    assert validate_manifest(bad_url, "final")

    bad_quality = dict(lark_final)
    bad_quality["quality_checks"] = dict(lark_final["quality_checks"])
    bad_quality["quality_checks"]["low_quality_information_removed"] = False
    assert validate_manifest(bad_quality, "final")

    inconsistent_final = dict(lark_final)
    inconsistent_final["data_consistency_verified"] = False
    assert validate_manifest(inconsistent_final, "final")

    missing_core_reason = dict(text_manifest)
    missing_core_reason.pop("core_financial_data_reason")
    assert validate_manifest(missing_core_reason, "plan")

    unfinished_core = dict(lark_final)
    unfinished_core["core_financial_data_status"] = "planned"
    assert validate_manifest(unfinished_core, "final")

    missing_core_gaps = dict(lark_final)
    missing_core_gaps["core_financial_data_status"] = "included_with_gaps"
    assert validate_manifest(missing_core_gaps, "final")

    missing_required_section = dict(lark_final)
    missing_required_section["actual_sections"] = [
        section
        for section in lark_final["actual_sections"]
        if section != "风险与验证"
    ]
    assert validate_manifest(missing_required_section, "final")

    price_plan = dict(lark_plan)
    price_plan.update(
        price_analysis=True,
        kline_status="included",
        advanced_components=["kline_html_block"],
        visual_purposes={"kline_html_block": "事件前后价格路径是否异常"},
        chart_generation_modes={"kline_html_block": "script"},
    )
    assert not validate_manifest(price_plan, "plan")

    missing_kline_component = dict(price_plan)
    missing_kline_component["advanced_components"] = []
    assert validate_manifest(missing_kline_component, "plan")

    valid_exception = dict(text_manifest)
    valid_exception.update(
        price_analysis=True,
        kline_status="not_applicable",
        kline_exception="user_declined_visual",
    )
    assert not validate_manifest(valid_exception, "plan")

    invalid_exception = dict(valid_exception)
    invalid_exception["kline_exception"] = "too_much_work"
    assert validate_manifest(invalid_exception, "plan")

    price_line_plan = dict(lark_plan)
    price_line_plan.update(
        price_analysis=True,
        kline_status="not_applicable",
        kline_exception="reliable_ohlc_unavailable",
        advanced_components=["price_chart_html_block"],
        visual_purposes={"price_chart_html_block": "收盘价路径是否存在结构性拐点"},
        chart_generation_modes={"price_chart_html_block": "script"},
    )
    assert not validate_manifest(price_line_plan, "plan")

    non_script_price_line = dict(price_line_plan)
    non_script_price_line["chart_generation_modes"] = {
        "price_chart_html_block": "manual"
    }
    assert validate_manifest(non_script_price_line, "plan")

    mislabeled_component = dict(lark_plan)
    mislabeled_component["advanced_components"] = ["kline_html_block"]
    assert validate_manifest(mislabeled_component, "plan")

    visual_final = dict(lark_final)
    visual_final.update(
        advanced_components=["trend_html_block", "heatmap_html_block"],
        visual_purposes={
            "trend_html_block": "盈利预期是否持续上修",
            "heatmap_html_block": "估值对 WACC 与永续增长有多敏感",
        },
        visual_checks={name: True for name in VISUAL_CHECKS},
        html_block_checks={name: True for name in HTML_BLOCK_CHECKS},
    )
    assert not validate_manifest(visual_final, "final")

    duplicate_visual_purpose = dict(visual_final)
    duplicate_visual_purpose["visual_purposes"] = {
        "trend_html_block": "同一个问题",
        "heatmap_html_block": "同一个问题",
    }
    assert validate_manifest(duplicate_visual_purpose, "plan")

    missing_visual_check = dict(visual_final)
    missing_visual_check.pop("visual_checks")
    assert validate_manifest(missing_visual_check, "final")

    missing_html_block_check = dict(visual_final)
    missing_html_block_check.pop("html_block_checks")
    assert validate_manifest(missing_html_block_check, "final")

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "manifest.json"
        path.write_text(json.dumps(lark_final, ensure_ascii=False), encoding="utf-8")
        assert not validate_manifest(load_manifest(path), "final")

    print("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(
        description="校验股票研究的 delivery_mode 计划态或最终完成态"
    )
    parser.add_argument("manifest", nargs="?", help="交付清单 JSON 路径")
    parser.add_argument("--phase", choices=("plan", "final"), default="final")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    if args.self_test:
        run_self_test()
        return 0
    if not args.manifest:
        emit("错误: 必须提供交付清单 JSON 路径")
        return 2
    try:
        errors = validate_manifest(load_manifest(args.manifest), args.phase)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        emit(f"错误: {exc}")
        return 2
    if errors:
        for error in errors:
            emit(f"门禁失败: {error}")
        return 1
    print(f"DELIVERY_GATE_PASS phase={args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
