#!/usr/bin/env python3
"""Validate planned and final delivery state for multi-stock comparison."""

import argparse
import json
import sys
import tempfile
from pathlib import Path


TEXT_CHECKS = (
    "single_decision_question",
    "answer_within_three_short_paragraphs",
    "no_structured_comparison_or_navigation",
    "no_advanced_component_needed_or_generated",
)
DELIVERY_MODES = {"TEXT", "HTML_REPORT"}


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


def validate_manifest(data, phase):
    errors = []
    mode = data.get("delivery_mode")
    if mode not in DELIVERY_MODES:
        errors.append("delivery_mode 必须是 TEXT 或 HTML_REPORT")

    reason = data.get("mode_reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("mode_reason 必须是非空字符串")

    components = data.get("advanced_components")
    if not isinstance(components, list):
        errors.append("advanced_components 必须是数组")
        components = []
    else:
        for index, component in enumerate(components):
            if not isinstance(component, str) or not component.strip():
                errors.append(f"advanced_components[{index}] 必须是非空字符串")

    visual_family_ids = data.get("visual_family_ids")
    if not isinstance(visual_family_ids, list):
        errors.append("visual_family_ids 必须是数组；没有图表时使用空数组")
        visual_family_ids = []
    else:
        normalized_ids = []
        for index, visual_id in enumerate(visual_family_ids):
            if not isinstance(visual_id, str) or not visual_id.strip():
                errors.append(f"visual_family_ids[{index}] 必须是非空字符串")
            else:
                normalized_ids.append(visual_id.strip())
        if len(normalized_ids) != len(set(normalized_ids)):
            errors.append("visual_family_ids 不得重复")
    if visual_family_ids and not components:
        errors.append("存在 visual_family_ids 时 advanced_components 不得为空")

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
        if visual_family_ids:
            errors.append("TEXT 模式不得包含 visual_family_ids；必须升级为 HTML_REPORT")

    if phase == "final" and mode == "HTML_REPORT":
        if data.get("editorial_gate_passed") is not True:
            errors.append("HTML_REPORT 完成态要求 editorial_gate_passed=true")
        if data.get("html_created") is not True:
            errors.append("HTML_REPORT 完成态要求 html_created=true")
        if not valid_html_path(data.get("html_path")):
            errors.append("HTML_REPORT 完成态要求实际存在且完整的 .html 文件")
        if data.get("file_verified") is not True:
            errors.append("HTML_REPORT 完成态要求 file_verified=true")

    return errors


def run_self_test():
    with tempfile.TemporaryDirectory() as temp_dir:
        html_file = Path(temp_dir) / "comparison.html"
        html_file.write_text("<!doctype html><html><body>比较报告</body></html>", encoding="utf-8")
        text_manifest = {
            "delivery_mode": "TEXT", "mode_reason": "单一事实问题",
            "text_checks": {name: True for name in TEXT_CHECKS},
            "advanced_components": [], "visual_family_ids": [],
        }
        plan = {
            "delivery_mode": "HTML_REPORT", "mode_reason": "多维比较",
            "advanced_components": ["rich_table"], "visual_family_ids": [],
        }
        final = dict(plan)
        final.update(editorial_gate_passed=True, html_created=True,
                     html_path=str(html_file), file_verified=True)
        assert not validate_manifest(text_manifest, "final")
        assert not validate_manifest(plan, "plan")
        assert validate_manifest(plan, "final")
        assert not validate_manifest(final, "final")
        bad = dict(final); bad["html_path"] = str(Path(temp_dir) / "missing.html")
        assert validate_manifest(bad, "final")
        visual = dict(final)
        visual.update(advanced_components=["timeseries_html5_block"],
                      visual_family_ids=["relative-path"])
        assert not validate_manifest(visual, "final")
    print("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(
        description="校验多股票比较的 delivery_mode 计划态或最终完成态"
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
