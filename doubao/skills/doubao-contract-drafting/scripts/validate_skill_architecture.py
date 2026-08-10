#!/usr/bin/env python3
"""Validate required V5.7 skill architecture and reference integrity."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md", "agents/openai.yaml", "references/deal-schema.md",
    "references/skeleton_families.md", "references/module_catalog.md",
    "references/skeleton_00_generic.md",
    "references/scenario-risk-map.md", "references/scenario-risk-checklist.md", "references/standard_policy.md",
    "references/scenario-risk-index.md",
    "references/default-commercial-parameters.md", "references/default-parameter-profiles.md",
    "references/draft-json-schema.md", "references/draft.schema.json",
    "references/drafting-conventions.md", "references/validation_rules.md",
    "references/legal-review-items.md", "evals/run_evals.py",
    "scripts/contract_model.py", "scripts/extract_deal.py", "scripts/preflight.py",
    "scripts/policy_gate.py", "scripts/consistency_check.py", "scripts/generate_docx.py",
    "scripts/font_check.py",
]


def fail(message: str) -> None:
    raise SystemExit("ARCHITECTURE ERROR: " + message)


def risk_targets(index_text: str) -> list[str]:
    targets = []
    for line in index_text.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "直接命中的风险地图标题" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        targets.extend(item.strip() for item in cells[1].split(" + ") if item.strip())
    return targets


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing " + ", ".join(missing))

    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for required_text in ("直接起草", "可填写空白", "无批注", "scenario-risk-map.md"):
        if required_text not in skill_text:
            fail(f"SKILL.md missing {required_text}")
    for relative_path in re.findall(r"`((?:references|scripts)/[^` ]+)`", skill_text):
        if not (ROOT / relative_path).is_file():
            fail(f"SKILL.md references missing file {relative_path}")
    bare_scripts = re.findall(r"(?<!\$\{CLAUDE_SKILL_DIR\}/)(scripts/[A-Za-z0-9_.-]+\.py)", skill_text)
    if bare_scripts:
        fail("SKILL.md uses cwd-relative script path: " + ", ".join(sorted(set(bare_scripts))))

    risk_map = (ROOT / "references/scenario-risk-map.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", risk_map, flags=re.MULTILINE)
    duplicates = sorted({heading for heading in headings if headings.count(heading) > 1})
    if duplicates:
        fail("duplicate risk-map headings: " + ", ".join(duplicates))
    index_text = (ROOT / "references/scenario-risk-index.md").read_text(encoding="utf-8")
    missing_targets = sorted({target for target in risk_targets(index_text) if target not in headings})
    if missing_targets:
        fail("risk index targets missing headings: " + ", ".join(missing_targets))
    print("Architecture validation passed.")


if __name__ == "__main__":
    main()
