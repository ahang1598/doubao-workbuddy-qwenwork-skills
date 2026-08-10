#!/usr/bin/env python3
"""Deterministic local checks for the unified visualization skill."""
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
    "references/mode-interactive.md",
    "references/mode-generated-illustration.md",
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
    "references/generated-prompt-rules.md",
    "references/generated-style-guide.md",
    "references/generated-tool-contracts.md",
    "references/migration-coverage.md",
    "examples/routing-cases.md",
    "examples/image-overlay-gold-process.md",
    "examples/image-overlay-gold-reply.md",
    "examples/generated-worked-example.md",
    "schemas/visualization-plan.schema.json",
]


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    text = SKILL.read_text(encoding="utf-8")

    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not fm:
        fail("SKILL.md 缺少合法 frontmatter", errors)
    else:
        front = fm.group(1)
        name = re.search(r"^name:\s*(.+)$", front, re.M)
        desc = re.search(r"^description:\s*(.+)$", front, re.M)
        if not name or name.group(1).strip() != ROOT.name:
            fail("目录名与 frontmatter name 不一致", errors)
        if not desc:
            fail("缺少 description", errors)
        elif len(desc.group(1).strip()) > 260:
            warnings.append("description 超过 260 字符，需结合平台限制复核")

    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"缺少必需文件: {rel}", errors)

    links = re.findall(r"`((?:references|examples|schemas|scripts)/[^`]+)`", text)
    for rel in links:
        if not (ROOT / rel).exists():
            fail(f"SKILL.md 引用不存在: {rel}", errors)

    body_lines = len(text.splitlines())
    if body_lines > 500:
        fail(f"SKILL.md 共 {body_lines} 行，超过 500 行", errors)

    required_terms = ["ECharts", "原图", "交互", "生成式知识配图", "地图禁用", "附件另行处理"]
    for term in required_terms:
        if term not in text:
            fail(f"缺少核心路由/边界关键词: {term}", errors)

    all_md = "\n".join(p.read_text(encoding="utf-8") for p in ROOT.rglob("*.md"))

    loading_gate_terms = ["强制渐进加载门", "必须完整读取", "required_files_loaded"]
    for term in loading_gate_terms:
        if term not in text and term not in all_md:
            fail(f"缺少 reference 加载门关键词: {term}", errors)

    mode_loading_groups = {
        "references/mode-echarts.md": [
            "echarts-option-spec.md", "shared-quality.md", "必须完整读取"
        ],
        "references/mode-image-overlay.md": [
            "image-overlay-process-spec.md", "image-overlay-authoring-spec.md",
            "shared-quality.md", "必须完整读取"
        ],
        "references/mode-interactive.md": [
            "renderer-trigger-design.md", "renderer-stability-math.md",
            "renderer-interaction-geometry.md", "renderer-output-mobile.md",
            "shared-quality.md", "必须完整读取"
        ],
        "references/mode-generated-illustration.md": [
            "generated-prompt-rules.md", "generated-style-guide.md",
            "generated-tool-contracts.md", "shared-quality.md", "必须完整读取"
        ],
    }
    for rel, terms in mode_loading_groups.items():
        mode_text = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        for term in terms:
            if term not in mode_text:
                fail(f"{rel} 缺少加载门要求: {term}", errors)

    conflict_patterns = {
        "强制临时 process 文件": r"必须.*svp_process\.json|先.*写入.*svp_process\.json",
        "强制未知固定模型": r"必须.*seedream_5\.0_pro|固定使用 Seedream 5\.0 Pro",
        "普通 ECharts 强制 HTML": r"(?:普通|常规|原生)?数据图表.{0,30}(?:必须|一律).{0,20}html type=|ECharts.{0,30}(?:必须|一律).{0,20}html type=",
        "证据允许生成替代": r"原图.*证据.*(?:可以|允许|应当|使用|改用).*生成.*替代",
    }
    for label, pattern in conflict_patterns.items():
        if re.search(pattern, all_md, re.I):
            fail(f"发现已知冲突: {label}", errors)

    schema_path = ROOT / "schemas/visualization-plan.schema.json"
    if schema_path.exists():
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"schema JSON 无法解析: {exc}", errors)

    junk = [p for p in ROOT.rglob("*") if p.name == ".DS_Store" or p.name.startswith("._") or "__MACOSX" in p.parts]
    if junk:
        fail("目录包含 macOS 元数据文件", errors)

    print(json.dumps({
        "skill": str(ROOT),
        "skill_lines": body_lines,
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL"
    }, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
