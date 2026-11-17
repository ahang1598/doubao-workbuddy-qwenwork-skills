#!/usr/bin/env python3
"""Validate the HTML-only Doubao Creative Design skill structure."""
from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "example/brief.md",
    "example/asset-manifest.md",
    "example/html-validation.html",
    "references/html/coding-rendering.md",
    "references/items/HTML.md",
    "references/style/coding/systems/diagram-visual-system.md",
    "references/style/coding/scenarios/flowchart-spec.md",
    "references/style/coding/scenarios/knowledge-graph-spec.md",
    "references/workflow/creation/pure-image.md",
    "references/workflow/creation/pure-coding.md",
    "references/workflow/creation/ai-coding.md",
    "references/workflow/editing/pure-image.md",
    "references/workflow/editing/pure-coding.md",
    "references/workflow/editing/ai-coding.md",
    "references/workflow/validation.md",
    "references/workflow/troubleshooting.md",
    "assets/templates/ref-bindings.json",
    "assets/svg/catalog.json",
    "scripts/maintenance/check-references.py",
    "scripts/maintenance/check-template-ref-bindings.py",
    "scripts/maintenance/render_html.py",
    "scripts/maintenance/capture_canvas.cjs",
    "scripts/maintenance/verify-html.cjs",
    "scripts/runtime/inline-svg-assets.py",
    "scripts/runtime/make-text-arc.py",
    "scripts/runtime/query-css-library.py",
    "scripts/runtime/resolve_font.py",
    "scripts/runtime/select_fonts.py",
    "scripts/runtime/validate_asset_manifest.py",
    "scripts/test/test_check_references.py",
    "scripts/test/test_asset_manifest_validator.py",
    "scripts/test/test_font_selection.py",
    "scripts/test/test_html_production_sequence.py",
    "scripts/test/test_query_css_library.py",
    "scripts/test/test_template_reference_boundaries.py",
    "scripts/test/test_verify_html.cjs",
)

FORBIDDEN_NAMES = ("canvas_renderer",)
FORBIDDEN_LEGACY_PATHS = ("references/xml", "examples")
FORBIDDEN_DESIGN_SOURCE_TERMS = (
    "多图层 XML",
    "XML Frame",
    "XML 兼容",
    "XML 输入",
    "XML 输出",
    "已有分层源",
    "既有分层源",
    "其他分层源",
)


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            errors.append(f"missing required path: {relative}")

    for path in ROOT.rglob("*"):
        lowered = path.name.lower()
        if any(term in lowered for term in FORBIDDEN_NAMES):
            errors.append(f"forbidden legacy path: {path.relative_to(ROOT)}")

    for relative in FORBIDDEN_LEGACY_PATHS:
        if (ROOT / relative).exists():
            errors.append(f"forbidden legacy design-source path: {relative}")

    for path in ROOT.rglob("*.xml"):
        relative = path.relative_to(ROOT).as_posix()
        # This sole XML fixture is the CLI envelope for an HTML asset, not a design source.
        if relative != "example/create-HTML.xml":
            errors.append(f"forbidden XML design source: {relative}")
            continue
        try:
            item = ET.parse(path).getroot()
            if (item.tag != "item" or item.get("type") != "HTML"
                    or [child.tag for child in item] != ["size", "asset"]
                    or not item.find("asset").get("url", "").startswith("https://")):
                errors.append("invalid HTML Item CLI fixture")
        except ET.ParseError:
            errors.append("malformed HTML Item CLI fixture")

    for path in (ROOT / "scripts").rglob("validate_*_plan.py"):
        errors.append(
            "forbidden natural-language Brief plan validator: "
            f"{path.relative_to(ROOT)}"
        )

    design_source_docs = [ROOT / "SKILL.md"]
    design_source_docs.extend((ROOT / "references" / "workflow").rglob("*.md"))
    design_source_docs.extend((ROOT / "references" / "style").rglob("*.md"))
    for source in design_source_docs:
        text = source.read_text(encoding="utf-8")
        for term in FORBIDDEN_DESIGN_SOURCE_TERMS:
            if term in text:
                errors.append(
                    "forbidden legacy design-source term: "
                    f"{source.relative_to(ROOT)} -> {term}"
                )

    for source in ROOT.rglob("*.md"):
        text = source.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            clean = target.split("#", 1)[0].strip()
            if not clean or clean.startswith("#") or "://" in clean:
                continue
            if not (source.parent / clean).resolve().exists():
                errors.append(f"broken link: {source.relative_to(ROOT)} -> {target}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: doubao-creative-design\n"):
        errors.append("SKILL.md name must be doubao-creative-design")

    if errors:
        for error in errors:
            print(error)
        return 1
    print("OK: HTML-only skill structure and local Markdown target paths are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
