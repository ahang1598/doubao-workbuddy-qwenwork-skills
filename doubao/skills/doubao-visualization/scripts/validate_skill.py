#!/usr/bin/env python3
"""Deterministic checks for the temporary deterministic-visualization skill."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"

REQUIRED = [
    "references/routing.md",
    "references/shared-quality.md",
    "references/mode-echarts.md",
    "references/mode-image-overlay.md",
    "references/mode-html-svg.md",
    "references/composition.md",
    "references/tool-contracts.md",
    "references/renderer-trigger-design.md",
    "references/renderer-stability-math.md",
    "references/renderer-interaction-geometry.md",
    "references/renderer-output-mobile.md",
    "references/echarts-option-spec.md",
    "references/echarts-source.md",
    "references/image-overlay-process-spec.md",
    "references/image-overlay-authoring-spec.md",
    "examples/routing-cases.md",
    "examples/image-overlay-gold-process.md",
    "examples/image-overlay-gold-reply.md",
    "schemas/visualization-plan.schema.json",
]

FORBIDDEN_FILES = [
    "references/mode-generated-illustration.md",
    "references/generated-prompt-rules.md",
    "references/generated-style-guide.md",
    "references/generated-tool-contracts.md",
    "references/migration-coverage.md",
    "examples/generated-worked-example.md",
    "references/mode-interactive.md",
]

FORBIDDEN_TERMS = [
    "generated" + "_illustration",
    "image" + "_gen",
    "generate" + "_image",
    "seed" + "ream_",
    "Seed" + "ream 5",
    "model" + "_version",
    "生成式知识" + "配图",
    "图片生成" + "工具",
    "生图" + "工具",
]


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def active_text() -> str:
    paths = [
        *ROOT.rglob("*.md"),
        *ROOT.rglob("*.yaml"),
        *ROOT.rglob("*.json"),
        *ROOT.rglob("*.py"),
    ]
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(set(paths))
        if path.is_file()
    )


def validate_plan_invariants(plan: dict) -> list[str]:
    """Validate the cross-field constraints used by the planning schema."""
    errors: list[str] = []
    assets = plan.get("assets") or []
    presentations = plan.get("presentations") or []
    required_files = set(plan.get("required_files") or [])
    policy = plan.get("user_image_policy")
    behavior = plan.get("html_svg_behavior")

    if plan.get("required_files_loaded") is not True:
        errors.append("required_files_loaded 必须为 true")

    if not assets:
        errors.append("assets 不能为空")
    if "none" in assets and len(assets) != 1:
        errors.append("assets 中的 none 不能与其他素材组合")
    if "user_image" not in assets and policy != "not_applicable":
        errors.append("没有 user_image 时 user_image_policy 必须为 not_applicable")
    if policy == "observe_for_schematic":
        if "user_image" not in assets:
            errors.append("observe_for_schematic 需要 user_image")
        if "html_svg" not in presentations:
            errors.append("observe_for_schematic 需要 html_svg")

    if plan.get("should_visualize") is False:
        if presentations != ["text_only"]:
            errors.append("should_visualize=false 时只能选择 text_only")

    if "text_only" in presentations and len(presentations) != 1:
        errors.append("text_only 不能与其他 presentation 组合")

    base_html = {
        "references/mode-html-svg.md",
        "references/renderer-trigger-design.md",
        "references/renderer-output-mobile.md",
        "references/shared-quality.md",
    }
    interactive_html = {
        "references/renderer-stability-math.md",
        "references/renderer-interaction-geometry.md",
    }
    echarts_files = {
        "references/mode-echarts.md",
        "references/echarts-option-spec.md",
        "references/shared-quality.md",
    }
    overlay_files = {
        "references/mode-image-overlay.md",
        "references/image-overlay-process-spec.md",
        "references/image-overlay-authoring-spec.md",
        "references/shared-quality.md",
    }

    if "html_svg" in presentations:
        if behavior not in {"static", "interactive"}:
            errors.append("html_svg 需要 static 或 interactive behavior")
        missing = base_html - required_files
        if missing:
            errors.append(f"html_svg 缺少必读文件: {sorted(missing)}")
        if behavior == "interactive":
            missing = interactive_html - required_files
            if missing:
                errors.append(f"interactive html_svg 缺少必读文件: {sorted(missing)}")
    elif behavior != "not_applicable":
        errors.append("未选择 html_svg 时 behavior 必须为 not_applicable")

    if "echarts" in presentations:
        missing = echarts_files - required_files
        if missing:
            errors.append(f"echarts 缺少必读文件: {sorted(missing)}")

    if "static_image_overlay" in presentations:
        if "user_image" not in assets or policy != "preserve":
            errors.append("原图叠加需要 user_image + preserve")
        missing = overlay_files - required_files
        if missing:
            errors.append(f"原图叠加缺少必读文件: {sorted(missing)}")

    if len(presentations) > 1 and "references/composition.md" not in required_files:
        errors.append("组合输出需要 references/composition.md")

    return errors


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    text = SKILL.read_text(encoding="utf-8")

    frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not frontmatter:
        fail("SKILL.md 缺少合法 frontmatter", errors)
    else:
        front = frontmatter.group(1)
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        description = re.search(r"^description:\s*(.+)$", front, re.M)
        if not name or name.group(1).strip() != ROOT.name:
            fail("目录名与 frontmatter name 不一致", errors)
        if not description:
            fail("缺少 description", errors)
        elif len(description.group(1).strip()) > 260:
            warnings.append("description 超过 260 字符，需结合平台限制复核")

    for relative_path in REQUIRED:
        if not (ROOT / relative_path).is_file():
            fail(f"缺少必需文件: {relative_path}", errors)

    for relative_path in FORBIDDEN_FILES:
        if (ROOT / relative_path).exists():
            fail(f"候选包仍包含禁用文件: {relative_path}", errors)

    links = re.findall(
        r"`((?:references|examples|schemas|scripts)/[^`]+)`",
        text,
    )
    for relative_path in links:
        if not (ROOT / relative_path).exists():
            fail(f"SKILL.md 引用不存在: {relative_path}", errors)

    body_lines = len(text.splitlines())
    if body_lines > 500:
        fail(f"SKILL.md 共 {body_lines} 行，超过 500 行", errors)

    required_terms = [
        "ECharts",
        "原图",
        "HTML/SVG",
        "静态",
        "交互",
        "地图禁用",
        "附件交付",
    ]
    for term in required_terms:
        if term not in text:
            fail(f"缺少核心路由或边界关键词: {term}", errors)

    corpus = active_text()
    for term in FORBIDDEN_TERMS:
        if re.search(re.escape(term), corpus, re.I):
            fail(f"候选包仍包含禁用能力标记: {term}", errors)

    loading_gate_terms = [
        "强制渐进加载门",
        "必须完整读取",
        "required_files_loaded",
    ]
    for term in loading_gate_terms:
        if term not in text and term not in corpus:
            fail(f"缺少 reference 加载门关键词: {term}", errors)

    mode_loading_groups = {
        "references/mode-echarts.md": [
            "echarts-option-spec.md",
            "shared-quality.md",
            "必须完整读取",
        ],
        "references/mode-image-overlay.md": [
            "image-overlay-process-spec.md",
            "image-overlay-authoring-spec.md",
            "shared-quality.md",
            "必须完整读取",
        ],
        "references/mode-html-svg.md": [
            "renderer-trigger-design.md",
            "renderer-output-mobile.md",
            "shared-quality.md",
            "必须完整读取",
        ],
    }
    for relative_path, terms in mode_loading_groups.items():
        path = ROOT / relative_path
        mode_text = path.read_text(encoding="utf-8") if path.exists() else ""
        for term in terms:
            if term not in mode_text:
                fail(f"{relative_path} 缺少加载门要求: {term}", errors)

    conflict_patterns = {
        "强制临时 process 文件": (
            r"必须.*svp_process\.json|先.*写入.*svp_process\.json"
        ),
        "普通 ECharts 强制 HTML": (
            r"(?:普通|常规|原生)?数据图表.{0,30}(?:必须|一律)"
            r".{0,20}html type=|ECharts.{0,30}(?:必须|一律)"
            r".{0,20}html type="
        ),
        "示意允许替代原图证据": (
            r"原图.*证据.*(?:可以|允许|应当|使用|改用)"
            r".*示意.*替代"
        ),
    }
    for label, pattern in conflict_patterns.items():
        if re.search(pattern, corpus, re.I):
            fail(f"发现已知冲突: {label}", errors)

    schema_path = ROOT / "schemas/visualization-plan.schema.json"
    if schema_path.exists():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            presentations = set(
                schema["properties"]["presentations"]["items"]["enum"]
            )
            expected = {
                "echarts",
                "static_image_overlay",
                "html_svg",
                "text_only",
            }
            if presentations != expected:
                fail("schema presentations 与临时路由不一致", errors)
            if schema["properties"]["required_files_loaded"] != {"const": True}:
                fail("schema 未强制 required_files_loaded=true", errors)
            schema_text = json.dumps(schema["allOf"], ensure_ascii=False)
            required_schema_files = [
                "references/mode-echarts.md",
                "references/echarts-option-spec.md",
                "references/mode-image-overlay.md",
                "references/image-overlay-process-spec.md",
                "references/image-overlay-authoring-spec.md",
                "references/mode-html-svg.md",
                "references/renderer-trigger-design.md",
                "references/renderer-output-mobile.md",
                "references/renderer-stability-math.md",
                "references/renderer-interaction-geometry.md",
                "references/shared-quality.md",
                "references/composition.md",
            ]
            for required_file in required_schema_files:
                if required_file not in schema_text:
                    fail(f"schema 缺少模式文件约束: {required_file}", errors)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            fail(f"schema JSON 无法解析或结构错误: {exc}", errors)

    junk = [
        path
        for path in ROOT.rglob("*")
        if path.name == ".DS_Store"
        or path.name.startswith("._")
        or "__MACOSX" in path.parts
        or path.name == "__pycache__"
    ]
    if junk:
        fail("目录包含缓存或 macOS 元数据文件", errors)

    result = {
        "skill": str(ROOT),
        "skill_lines": body_lines,
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
