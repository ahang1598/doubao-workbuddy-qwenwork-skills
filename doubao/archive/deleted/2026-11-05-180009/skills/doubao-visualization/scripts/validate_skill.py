#!/usr/bin/env python3
"""Validate structure, routing invariants, and runtime loading budgets."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"

# 地图委派给独立入口，不进入根计划或通用组合协议。
PLAN_MODES = {
    "text_only",
    "echarts",
    "static_image_overlay",
    "html_svg",
    "generated_illustration",
}

REQUIRED = [
    "agents/openai.yaml",
    "references/routing.md",
    "map-create/SKILL.md",
    "map-create/agents/openai.yaml",
    "map-create/scripts/create-map.mjs",
    "map-create/scripts/telemetry-task.mjs",
    "map-create/assets/engine/engine.json.gz",
    "map-create/vendor.lock.json",
    "references/shared-quality.md",
    "references/mode-echarts.md",
    "references/mode-image-overlay.md",
    "references/mode-html-svg.md",
    "references/mode-generated-illustration.md",
    "references/generated-prompt-rules.md",
    "references/generated-style-guide.md",
    "references/generated-tool-contracts.md",
    "references/composition.md",
    "references/tool-contracts.md",
    "references/renderer-trigger-design.md",
    "references/renderer-stability-math.md",
    "references/renderer-interaction-geometry.md",
    "references/renderer-output-mobile.md",
    "references/echarts-option-spec.md",
    "references/echarts-web-pc-spec.md",
    "references/echarts-web-pc-sunburst-reference.md",
    "references/echarts-web-pc-gauge-reference.md",
    "references/echarts-source.md",
    "references/image-overlay-process-spec.md",
    "references/image-overlay-authoring-spec.md",
    "examples/routing-cases.md",
    "examples/generated-worked-example.md",
    "examples/image-overlay-gold-process.md",
    "examples/image-overlay-gold-reply.md",
    "schemas/visualization-plan.schema.json",
]

FORBIDDEN_FILES = [
    "references/mode-interactive.md",
]

BASE_ROUTES = {
    "echarts": ["SKILL.md", "references/mode-echarts.md"],
    "static_image_overlay": [
        "SKILL.md",
        "references/mode-image-overlay.md",
    ],
    "static_image_overlay_complex": [
        "SKILL.md",
        "references/mode-image-overlay.md",
        "references/image-overlay-process-spec.md",
        "references/image-overlay-authoring-spec.md",
    ],
    "html_svg_static": ["SKILL.md", "references/mode-html-svg.md"],
    "html_svg_interactive": [
        "SKILL.md",
        "references/mode-html-svg.md",
        "references/renderer-stability-math.md",
        "references/renderer-interaction-geometry.md",
    ],
    "generated_illustration": [
        "SKILL.md",
        "references/mode-generated-illustration.md",
        "references/generated-prompt-rules.md",
        "references/generated-style-guide.md",
        "references/generated-tool-contracts.md",
        "references/shared-quality.md",
    ],
    "echarts_web_pc": [
        "SKILL.md",
        "references/mode-echarts.md",
        "references/echarts-web-pc-spec.md",
    ],
    "echarts_web_pc_sunburst": [
        "SKILL.md",
        "references/mode-echarts.md",
        "references/echarts-web-pc-spec.md",
        "references/echarts-web-pc-sunburst-reference.md",
    ],
    "echarts_web_pc_gauge": [
        "SKILL.md",
        "references/mode-echarts.md",
        "references/echarts-web-pc-spec.md",
        "references/echarts-web-pc-gauge-reference.md",
    ],
}

BASE_ROUTE_BUDGETS = {
    "echarts": 18_000,
    "static_image_overlay": 18_000,
    "static_image_overlay_complex": 48_000,
    "html_svg_static": 20_000,
    "html_svg_interactive": 34_000,
    "generated_illustration": 38_000,
    "echarts_web_pc": 40_000,
    "echarts_web_pc_sunburst": 52_000,
    "echarts_web_pc_gauge": 46_000,
}

# 只记录委派入口的加载量；后续依赖由子入口决定，不套用普通模式预算。
DELEGATED_ROUTES = {
    "map-create": ["SKILL.md", "map-create/SKILL.md"],
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_agent_metadata(skill_dir: Path, expected_name: str) -> list[str]:
    errors: list[str] = []
    skill_path = skill_dir / "SKILL.md"
    agent_path = skill_dir / "agents/openai.yaml"
    if not skill_path.is_file() or not agent_path.is_file():
        return errors  # REQUIRED 已报告缺失文件。
    skill_text = skill_path.read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\n(.*?)\n---\n", skill_text, re.S)
    name = re.search(r"^name:\s*(.+)$", frontmatter.group(1), re.M) if frontmatter else None
    if not name or name.group(1).strip().strip("\"'") != expected_name:
        errors.append(f"{skill_path.relative_to(ROOT)} 的 name 应为 {expected_name}")
    agent_text = agent_path.read_text(encoding="utf-8")
    prompt = re.search(r"^\s*default_prompt:\s*(.+)$", agent_text, re.M)
    invocations = re.findall(r"\$([a-z0-9-]+)", prompt.group(1)) if prompt else []
    if invocations != [expected_name]:
        errors.append(f"{agent_path.relative_to(ROOT)} 的 default_prompt 应调用 ${expected_name}")
    return errors


def validate_delegated_routes(text: str) -> tuple[dict[str, int], list[str]]:
    errors: list[str] = []
    entry_sizes: dict[str, int] = {}
    section = re.search(r"^## 按需加载\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in (section.group(1).splitlines() if section else [])
        if line.lstrip().startswith("|")
    ]
    for route, paths in DELEGATED_ROUTES.items():
        entry = f"{route}/SKILL.md"
        route_rows = [row for row in rows if row and f"`{route}`" in row[0]]
        if len(route_rows) != 1 or len(route_rows[0]) < 2 or entry not in route_rows[0][1]:
            errors.append(f"按需加载表应有唯一 {route} 分支，基础必读指向 {entry}")
        if all((ROOT / path).is_file() for path in paths):
            entry_sizes[route] = sum((ROOT / path).stat().st_size for path in paths)

        skill_dir = ROOT / route
        errors.extend(validate_agent_metadata(skill_dir, route))
        markdown_files = [skill_dir / "SKILL.md", *skill_dir.glob("references/*.md")]
        for markdown_file in markdown_files:
            if not markdown_file.is_file():
                continue
            markdown = markdown_file.read_text(encoding="utf-8")
            relative_source = markdown_file.relative_to(ROOT)
            # Markdown 链接相对文档解析，含配对 JSON；外部链接不发起网络检查。
            for reference in set(re.findall(r"\[[^\]\n]*\]\(([^)\s]+)\)", markdown)):
                target = urlsplit(reference)
                if target.scheme or target.netloc or not target.path:
                    continue
                if not (markdown_file.parent / unquote(target.path)).is_file():
                    errors.append(f"{relative_source} 链接不存在: {reference}")
            # 子包内的代码路径相对 SKILL_DIR；不把任务产物当作随包文件。
            for reference in set(re.findall(
                r"`((?:references|contracts|assets|themes)/[^`\n]+\.(?:md|json)(?:#[^`\n]+)?)`",
                markdown,
            )):
                if not (skill_dir / reference.split("#", 1)[0]).is_file():
                    errors.append(f"{relative_source} 引用不存在: {reference}")
    return entry_sizes, errors


def validate_plan(plan: dict) -> list[str]:
    errors: list[str] = []
    mode = plan.get("mode")
    behavior = plan.get("behavior")
    source = plan.get("source")
    secondary = plan.get("secondary")
    sources = {
        "user_content",
        "user_image",
        "verified",
        "example",
        "insufficient",
    }

    if set(plan) != {"mode", "behavior", "source", "secondary"}:
        errors.append("plan 必须且只能包含四个最小字段")
    if mode not in PLAN_MODES:
        errors.append("mode 非法")
    if behavior not in {"not_applicable", "static", "interactive"}:
        errors.append("behavior 非法")
    if source not in sources:
        errors.append("source 非法")
    if mode == "html_svg" and behavior not in {"static", "interactive"}:
        errors.append("html_svg 必须指定 static 或 interactive")
    if mode != "html_svg" and behavior != "not_applicable":
        errors.append("非 html_svg 的 behavior 必须为 not_applicable")
    if mode == "static_image_overlay" and source != "user_image":
        errors.append("原图叠加必须使用 user_image")
    if source == "insufficient" and mode != "text_only":
        errors.append("素材不足时必须回退 text_only")
    if secondary is not None and secondary not in PLAN_MODES - {"text_only"}:
        errors.append("secondary 非法")
    if secondary == mode:
        errors.append("secondary 不得与 mode 重复")
    if mode == "text_only" and secondary is not None:
        errors.append("text_only 不得组合第二模式")
    return errors


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    text = SKILL.read_text(encoding="utf-8")

    frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not frontmatter:
        errors.append("SKILL.md 缺少合法 frontmatter")
    else:
        front = frontmatter.group(1)
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        description = re.search(r"^description:\s*(.+)$", front, re.M)
        if not name or name.group(1).strip() != "doubao-visualization":
            errors.append("frontmatter name 必须为 doubao-visualization")
        if not description:
            errors.append("缺少 description")
        elif len(description.group(1).strip()) > 260:
            warnings.append("description 超过 260 字符")

    for relative_path in REQUIRED:
        if not (ROOT / relative_path).is_file():
            errors.append(f"缺少必需文件: {relative_path}")
    for relative_path in FORBIDDEN_FILES:
        if (ROOT / relative_path).exists():
            errors.append(f"仍包含禁用文件: {relative_path}")

    errors.extend(validate_agent_metadata(ROOT, "doubao-visualization"))
    delegated_entry_sizes, delegated_errors = validate_delegated_routes(text)
    errors.extend(delegated_errors)

    markdown_files = [
        SKILL,
        *ROOT.glob("references/*.md"),
        *ROOT.glob("examples/*.md"),
    ]
    for markdown_file in markdown_files:
        markdown = markdown_file.read_text(encoding="utf-8")
        for reference in re.findall(r"`([^`\n]+\.md)`", markdown):
            candidates = [
                ROOT / reference,
                markdown_file.parent / reference,
                ROOT / "references" / reference,
                ROOT / "examples" / reference,
            ]
            if not any(candidate.is_file() for candidate in candidates):
                relative_source = markdown_file.relative_to(ROOT)
                errors.append(
                    f"{relative_source} 引用不存在: {reference}"
                )

    if len(text.splitlines()) > 140:
        errors.append("SKILL.md 超过 140 行")
    for term in [
        "ECharts",
        "原图",
        "HTML/SVG",
        "静态默认",
        "地图路由",
        "按需加载",
        "附件交付",
    ]:
        if term not in text:
            errors.append(f"SKILL.md 缺少核心契约: {term}")

    for obsolete in [
        "required_files_loaded",
        "先完整读取 `references/routing.md`",
        "每次使用必读",
    ]:
        if obsolete in text:
            errors.append(f"入口仍包含旧加载机制: {obsolete}")

    for mode_file in [
        "references/mode-echarts.md",
        "references/mode-image-overlay.md",
        "references/mode-html-svg.md",
    ]:
        mode_text = read(mode_file)
        if "完整运行契约" not in mode_text:
            errors.append(f"{mode_file} 未声明常规任务自包含")
        if "shared-quality.md" in mode_text:
            errors.append(f"{mode_file} 仍默认依赖 shared-quality.md")

    overlay_mode = read("references/mode-image-overlay.md")
    for term in [
        "总 coord 数不超过 2",
        "总 coord 数不少于 3",
        "steps 不少于 2",
        "必须同时读取",
        "image-overlay-process-spec.md",
        "image-overlay-authoring-spec.md",
    ]:
        if term not in overlay_mode:
            errors.append(f"原图叠加缺少结构阈值或加载契约: {term}")

    pc_spec = read("references/echarts-web-pc-spec.md")
    for term in [
        "Device platform",
        "电脑端",
        "网页端",
        "986 × 420",
    ]:
        if term not in pc_spec:
            errors.append(f"Web/PC ECharts 规范缺少条件或画布契约: {term}")
    if "不是本分支默认依赖" not in pc_spec:
        errors.append("Web/PC ECharts 规范重新引入了默认多文件加载")
    for stale in [
        "移动端继续遵循 `echarts-option-spec.md`",
        "保留 `echarts-option-spec.md` 的 ES5 callback",
    ]:
        if stale in pc_spec:
            errors.append(f"Web/PC ECharts 规范仍含默认加载残留: {stale}")
    if "echarts-web-pc-sunburst-reference.md" not in text:
        errors.append("SKILL.md 未接入 Web/PC Sunburst 参考")
    if "echarts-web-pc-gauge-reference.md" not in text:
        errors.append("SKILL.md 未接入 Web/PC Gauge 参考")

    route_sizes = {}
    for route, paths in BASE_ROUTES.items():
        size = sum((ROOT / path).stat().st_size for path in paths)
        route_sizes[route] = size
        if size > BASE_ROUTE_BUDGETS[route]:
            errors.append(
                f"{route} 基础加载 {size} 字节，超过预算 "
                f"{BASE_ROUTE_BUDGETS[route]}"
            )

    schema_path = ROOT / "schemas/visualization-plan.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if set(schema["required"]) != {
            "mode",
            "behavior",
            "source",
            "secondary",
        }:
            errors.append("schema 未使用四字段最小计划")
        if "required_files" in schema.get("properties", {}):
            errors.append("schema 不应包含文件加载 bookkeeping")
        if set(schema["properties"]["mode"]["enum"]) != PLAN_MODES:
            errors.append("schema mode 与计划校验器不一致")
        if set(schema["properties"]["secondary"]["enum"]) != (
            PLAN_MODES - {"text_only"}
        ) | {None}:
            errors.append("schema secondary 与计划校验器不一致")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        errors.append(f"schema JSON 无法解析或结构错误: {exc}")

    plan_cases = [
        {
            "mode": "echarts",
            "behavior": "not_applicable",
            "source": "user_content",
            "secondary": None,
        },
        {
            "mode": "static_image_overlay",
            "behavior": "not_applicable",
            "source": "user_image",
            "secondary": None,
        },
        {
            "mode": "html_svg",
            "behavior": "interactive",
            "source": "verified",
            "secondary": "echarts",
        },
        {
            "mode": "generated_illustration",
            "behavior": "not_applicable",
            "source": "verified",
            "secondary": None,
        },
        {
            "mode": "generated_illustration",
            "behavior": "not_applicable",
            "source": "user_image",
            "secondary": "html_svg",
        },
        {
            "mode": "echarts",
            "behavior": "not_applicable",
            "source": "user_content",
            "secondary": "generated_illustration",
        },
    ]
    for index, plan in enumerate(plan_cases):
        for message in validate_plan(plan):
            errors.append(f"plan case {index}: {message}")

    generated_plan = {
        "mode": "generated_illustration",
        "behavior": "not_applicable",
        "source": "verified",
        "secondary": None,
    }
    invalid_plan_cases = [
        {**generated_plan, "mode": "map-create"},
        {**generated_plan, "secondary": "map-create"},
        {**generated_plan, "behavior": "interactive"},
        {**generated_plan, "source": "insufficient"},
        {**generated_plan, "secondary": "text_only"},
        {**generated_plan, "secondary": "generated_illustration"},
        {**generated_plan, "mode": "text_only", "secondary": "generated_illustration"},
    ]
    for index, plan in enumerate(invalid_plan_cases):
        if not validate_plan(plan):
            errors.append(f"invalid plan case {index}: 未拒绝非法计划")

    junk = [
        path
        for path in ROOT.rglob("*")
        if path.name == ".DS_Store"
        or path.name.startswith("._")
        or "__MACOSX" in path.parts
        or path.name == "__pycache__"
    ]
    if junk:
        errors.append("目录包含缓存或 macOS 元数据文件")

    result = {
        "skill": str(ROOT),
        "skill_lines": len(text.splitlines()),
        "route_bytes": route_sizes,
        "delegated_entry_bytes": delegated_entry_sizes,
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
