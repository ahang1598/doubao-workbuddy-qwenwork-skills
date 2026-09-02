#!/usr/bin/env python3
"""Offline structural validator for this portable QuantSkills agent."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "README.en.md",
    "LICENSE",
    "CLAUDE.md",
    "agents/openai.yaml",
    "agents/portable-loader.md",
    "agents/team.json",
    "agents/execution_modes.json",
    ".cursor/rules/quantskills-agent.mdc",
    "references/sop.md",
    "references/evidence-contract.md",
    "references/member-handoff-schema.md",
    "references/source-boundary.md",
    "scripts/workflow_guard.py",
    "scripts/mode_profiles.py",
    "scripts/environment_preflight.py",
    "scripts/compact_quality_gate.py",
    "scripts/collect_results.py",
    "scripts/run_candidates.py",
    "scripts/build_skill_inventory.py",
    "scripts/smoke_test.py",
    "scripts/package_platform_variants.py",
    "tests/test_workflow_guard.py",
    "tests/test_execution_modes.py",
    "tests/test_collect_results.py",
    "tests/test_run_candidates.py",
    "tests/test_portable_adapters.py",
    "adapters/host-capability-contract.json",
    "adapters/README.md",
    "adapters/common/portable_team.py",
    "adapters/common/cli.py",
    "adapters/common/local_bootstrap.py",
    "adapters/codex/adapter.json",
    "adapters/codex/README.md",
    "adapters/claude_code/adapter.json",
    "adapters/claude_code/materialize.py",
    "adapters/claude_code/README.md",
    "adapters/openai_agents/adapter.json",
    "adapters/openai_agents/adapter.py",
    "adapters/openai_agents/README.md",
    "adapters/langgraph/adapter.json",
    "adapters/langgraph/graph.py",
    "adapters/langgraph/README.md",
    "adapters/workbuddy/adapter.json",
    "adapters/workbuddy/build_package.py",
    "adapters/workbuddy/README.md",
]

SKILLS = [
    "skill-report-replication",
    "skill-factor-mining-pandaai",
    "skill-pandaai-factor-online",
    "skill-backtest-overfit",
    "skill-strategy-tearsheet-report",
]

MEMBERS = {
    "source-replication-researcher": {
        "skill": "skill-report-replication",
        "stages": ["01_source_replication"],
    },
    "factor-engineer": {
        "skill": "skill-factor-mining-pandaai",
        "stages": ["02_factor_candidates"],
    },
    "pandaai-experimenter": {
        "skill": "skill-pandaai-factor-online",
        "stages": ["03_platform_preflight", "04_platform_execution"],
    },
    "overfit-auditor": {
        "skill": "skill-backtest-overfit",
        "stages": ["05_statistical_audit"],
    },
    "performance-reporter": {
        "skill": "skill-strategy-tearsheet-report",
        "stages": ["06_tearsheet"],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty: {relative}")
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8-sig")
        for token in (
            "name: agent-ai-quant-research-team",
            "schema_version: 2.0.0",
            "project_type: agent",
            "license: GPL-3.0-only",
            "validation_level: listed",
            "interface: {mode: natural-language}",
            "```json qsh-form",
            "AgentTool",
            "agents/team.json",
            "member_handoff.json",
            "workflow_guard.py finalize",
            "standard",
            "environment_preflight.py",
            "local_replication_universe",
            "platform_universe",
        ):
            if token not in text:
                errors.append(f"AGENTS.md missing declaration/policy token: {token}")
        match = re.search(r"requires:\s*\[([^\]]+)\]", text)
        if not match:
            errors.append("AGENTS.md missing requires list")
        else:
            actual = {item.strip() for item in match.group(1).split(",")}
            if actual != set(SKILLS):
                errors.append(f"requires mismatch: {sorted(actual)}")
    openai = root / "agents" / "openai.yaml"
    if openai.is_file():
        text = openai.read_text(encoding="utf-8-sig")
        if "entrypoint: AGENTS.md" not in text or "canonical_root: AGENTS.md" not in text:
            errors.append("agents/openai.yaml does not point to AGENTS.md")
    team_path = root / "agents" / "team.json"
    if team_path.is_file():
        try:
            team = json.loads(team_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid agents/team.json: {exc}")
        else:
            if team.get("team_id") != "agent-ai-quant-research-team":
                errors.append("agents/team.json team_id mismatch")
            if team.get("lead") != {
                "id": "agent-ai-quant-research-team", "declaration": "AGENTS.md"
            }:
                errors.append("agents/team.json lead mismatch")
            invocation = team.get("invocation", {})
            if invocation.get("mechanism") != "AgentTool" or invocation.get("context_policy") != "isolated":
                errors.append("agents/team.json must require isolated AgentTool invocation")
            if team.get("package_version") != "0.4.2":
                errors.append("agents/team.json package_version must be 0.4.2")
            if team.get("default_execution_mode") != "standard":
                errors.append("agents/team.json default execution mode must be standard")
            if team.get("execution_modes") != "agents/execution_modes.json":
                errors.append("agents/team.json execution_modes path mismatch")
            members = team.get("members")
            if not isinstance(members, list) or len(members) != len(MEMBERS):
                errors.append("agents/team.json must contain exactly five members")
            else:
                seen: set[str] = set()
                for member in members:
                    member_id = str(member.get("id", ""))
                    seen.add(member_id)
                    expected = MEMBERS.get(member_id)
                    if expected is None:
                        errors.append(f"unexpected member ID: {member_id}")
                        continue
                    if member.get("skills") != [expected["skill"]]:
                        errors.append(f"member skill mismatch: {member_id}")
                    if member.get("stages") != expected["stages"]:
                        errors.append(f"member stage route mismatch: {member_id}")
                    declaration = str(member.get("declaration", ""))
                    path = root / declaration
                    if declaration != f"agents/members/{member_id}.md" or not path.is_file():
                        errors.append(f"missing or invalid member declaration: {member_id}")
                        continue
                    member_text = path.read_text(encoding="utf-8-sig")
                    for token in (
                        f"name: {member_id}",
                        f"  - {expected['skill']}",
                        "不调用其他 Agent",
                        "member_handoff.json",
                        "references/member-handoff-schema.md",
                    ):
                        if token not in member_text:
                            errors.append(f"member declaration {member_id} missing token: {token}")
                if seen != set(MEMBERS):
                    errors.append("agents/team.json member IDs mismatch")
    modes_path = root / "agents" / "execution_modes.json"
    if modes_path.is_file():
        try:
            modes = json.loads(modes_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid agents/execution_modes.json: {exc}")
        else:
            if modes.get("default_mode") != "standard":
                errors.append("execution_modes default_mode must be standard")
            profiles = modes.get("modes")
            if not isinstance(profiles, dict) or set(profiles) != {"fast", "standard", "audit"}:
                errors.append("execution_modes must declare fast, standard, and audit")
            elif profiles["fast"].get("active_stages") != [
                "00_intake", "01_source_replication", "07_final_review"
            ]:
                errors.append("fast execution mode stage route mismatch")
    for directory in (root / "scripts", root / "tests"):
        for script in directory.glob("*.py"):
            try:
                ast.parse(script.read_text(encoding="utf-8-sig"), filename=str(script))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                errors.append(f"Python syntax validation failed for {script.name}: {exc}")
    result = {"ok": not errors, "root": str(root), "errors": errors}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PASS" if result["ok"] else "FAIL")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
