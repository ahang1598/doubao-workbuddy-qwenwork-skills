#!/usr/bin/env python3
"""Validate planned and final delivery state for multi-stock comparison."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


TEXT_CHECKS = (
    "single_decision_question",
    "answer_within_three_short_paragraphs",
    "no_structured_comparison_or_navigation",
    "no_advanced_component_needed_or_generated",
)
DELIVERY_MODES = {"TEXT", "LARK_DOC"}


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


def validate_manifest(data, phase):
    errors = []
    mode = data.get("delivery_mode")
    if mode not in DELIVERY_MODES:
        errors.append("delivery_mode 必须是 TEXT 或 LARK_DOC")

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
            errors.append("TEXT 模式不得包含任何 advanced_components；必须升级为 LARK_DOC")
        if visual_family_ids:
            errors.append("TEXT 模式不得包含 visual_family_ids；必须升级为 LARK_DOC")

    if phase == "final" and mode == "LARK_DOC":
        if data.get("editorial_gate_passed") is not True:
            errors.append("LARK_DOC 完成态要求 editorial_gate_passed=true")
        if data.get("doc_created") is not True:
            errors.append("LARK_DOC 完成态要求 doc_created=true")
        if not valid_doc_url(data.get("doc_url")):
            errors.append("LARK_DOC 完成态要求可访问的 /docx/ 或 /wiki/ URL")
        if data.get("fetch_verified") is not True:
            errors.append("LARK_DOC 完成态要求 fetch_verified=true")
        if visual_family_ids and data.get("visuals_fetch_verified") is not True:
            errors.append("包含图表的 LARK_DOC 完成态要求 visuals_fetch_verified=true")

    return errors


def run_self_test():
    text_manifest = {
        "delivery_mode": "TEXT",
        "mode_reason": "单一事实问题",
        "text_checks": {name: True for name in TEXT_CHECKS},
        "advanced_components": [],
        "visual_family_ids": [],
        "doc_created": False,
        "doc_url": "",
        "fetch_verified": False,
    }
    lark_plan = {
        "delivery_mode": "LARK_DOC",
        "mode_reason": "需要多章节和情景表",
        "text_checks": {},
        "advanced_components": ["rich_table"],
        "visual_family_ids": [],
        "editorial_gate_passed": False,
        "doc_created": False,
        "doc_url": "",
        "fetch_verified": False,
    }
    lark_final = dict(lark_plan)
    lark_final.update(
        editorial_gate_passed=True,
        doc_created=True,
        doc_url="https://example.feishu.cn/docx/test_token",
        fetch_verified=True,
    )

    assert not validate_manifest(text_manifest, "plan")
    assert not validate_manifest(text_manifest, "final")
    assert not validate_manifest(lark_plan, "plan")
    assert validate_manifest(lark_plan, "final")
    assert not validate_manifest(lark_final, "final")

    bad_text = dict(text_manifest)
    bad_text["advanced_components"] = ["html_block"]
    assert validate_manifest(bad_text, "plan")

    visual_plan = dict(lark_plan)
    visual_plan["advanced_components"] = ["timeseries_html5_block"]
    visual_plan["visual_family_ids"] = ["market-relative-path"]
    assert not validate_manifest(visual_plan, "plan")
    visual_final = dict(visual_plan)
    visual_final.update(
        editorial_gate_passed=True,
        doc_created=True,
        doc_url="https://example.feishu.cn/docx/visual_token",
        fetch_verified=True,
        visuals_fetch_verified=True,
    )
    assert not validate_manifest(visual_final, "final")
    visual_final["visuals_fetch_verified"] = False
    assert validate_manifest(visual_final, "final")

    bad_checks = dict(text_manifest)
    bad_checks["text_checks"] = dict(text_manifest["text_checks"])
    bad_checks["text_checks"]["single_decision_question"] = False
    assert validate_manifest(bad_checks, "plan")

    bad_url = dict(lark_final)
    bad_url["doc_url"] = "https://example.feishu.cn/drive/folder"
    assert validate_manifest(bad_url, "final")

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "manifest.json"
        path.write_text(json.dumps(lark_final, ensure_ascii=False), encoding="utf-8")
        assert not validate_manifest(load_manifest(path), "final")

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
