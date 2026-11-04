#!/usr/bin/env python3
"""Validate the planned and final delivery state for equity research."""

import argparse
import json
import sys
import tempfile
from pathlib import Path


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
    "embedded_in_html_report",
    "chart_source_embedded",
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
DELIVERY_MODES = {"TEXT", "HTML_REPORT"}
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


def valid_html_path(value):
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value.strip()).expanduser()
    if path.suffix.lower() != ".html" or not path.is_file():
        return False
    content = path.read_text(encoding="utf-8", errors="replace").lower()
    return "<!doctype html>" in content and "</html>" in content


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
        errors.append("delivery_mode 必须是 TEXT 或 HTML_REPORT")

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
    if mode == "HTML_REPORT":
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
        if mode != "HTML_REPORT":
            errors.append("存在 HTML 视觉时 delivery_mode 必须是 HTML_REPORT")
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
            if mode != "HTML_REPORT":
                errors.append("包含 K 线时 delivery_mode 必须是 HTML_REPORT")
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
            errors.append("TEXT 模式不得包含任何 advanced_components；必须升级为 HTML_REPORT")

    if phase == "final" and mode == "HTML_REPORT":
        if data.get("html_created") is not True:
            errors.append("HTML_REPORT 完成态要求 html_created=true")
        if not valid_html_path(data.get("html_path")):
            errors.append("HTML_REPORT 完成态要求实际存在且完整的 .html 文件")
        if data.get("file_verified") is not True:
            errors.append("HTML_REPORT 完成态要求 file_verified=true")
        quality_checks = data.get("quality_checks")
        if not isinstance(quality_checks, dict):
            errors.append("HTML_REPORT 完成态必须提供 quality_checks 对象")
        else:
            for name in QUALITY_CHECKS:
                if quality_checks.get(name) is not True:
                    errors.append(f"HTML_REPORT 完成态要求 quality_checks.{name}=true")
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
    with tempfile.TemporaryDirectory() as temp_dir:
        html_file = Path(temp_dir) / "report.html"
        html_file.write_text("<!doctype html><html><body>研究报告</body></html>", encoding="utf-8")
        text_manifest = {
            "delivery_mode": "TEXT", "mode_reason": "单一事实问题",
            "text_checks": {name: True for name in TEXT_CHECKS},
            "advanced_components": [], "data_consistency_verified": True,
            "core_financial_data_status": "not_relevant",
            "core_financial_data_reason": "单一事实问题不需金融与财务基线",
            "price_analysis": False, "kline_status": "not_price_analysis",
        }
        plan = {
            "delivery_mode": "HTML_REPORT", "mode_reason": "需要多章节和情景表",
            "advanced_components": ["rich_table"],
            "core_financial_data_status": "planned",
            "core_financial_data_fields": ["price", "revenue", "valuation"],
            "required_sections": ["核心结论", "主体分析"],
            "price_analysis": False, "kline_status": "not_price_analysis",
        }
        final = dict(plan)
        final.update(core_financial_data_status="included", data_consistency_verified=True,
                     actual_sections=list(plan["required_sections"]), html_created=True,
                     html_path=str(html_file), file_verified=True,
                     quality_checks={name: True for name in QUALITY_CHECKS})
        assert not validate_manifest(text_manifest, "final")
        assert not validate_manifest(plan, "plan")
        assert validate_manifest(plan, "final")
        assert not validate_manifest(final, "final")
        bad = dict(final); bad["html_path"] = str(Path(temp_dir) / "missing.html")
        assert validate_manifest(bad, "final")
        bad = dict(final); bad["data_consistency_verified"] = False
        assert validate_manifest(bad, "final")
        visual = dict(final)
        visual.update(advanced_components=["kline_html_block"], price_analysis=True,
                      kline_status="included", visual_purposes={"kline_html_block": "价格路径"},
                      chart_generation_modes={"kline_html_block": "script"},
                      visual_checks={name: True for name in VISUAL_CHECKS},
                      html_block_checks={name: True for name in HTML_BLOCK_CHECKS})
        assert not validate_manifest(visual, "final")
        visual["html_block_checks"]["embedded_in_html_report"] = False
        assert validate_manifest(visual, "final")
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
