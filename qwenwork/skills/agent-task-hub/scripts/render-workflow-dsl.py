#!/usr/bin/env python3
"""Render agent-task-hub workflow DSL templates safely.

This helper is intentionally local-only: it renders JSON files and validates
that no placeholders remain. It does not call dws and does not mutate tables.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_RE = re.compile(r"<[^>]+>")


def load_template(name: str) -> str:
    return (ROOT / "templates" / name).read_text(encoding="utf-8")


def render(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    leftovers = PLACEHOLDER_RE.findall(rendered)
    if leftovers:
        raise SystemExit(f"unreplaced placeholders: {', '.join(sorted(set(leftovers)))}")
    json.loads(rendered)
    return rendered


def write_output(rendered: str, out: Path) -> None:
    data = json.loads(rendered)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-id", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--notice-field-id", required=True)
    parser.add_argument("--out", required=True, type=Path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render agent-task-hub workflow DSL")
    sub = parser.add_subparsers(dest="kind", required=True)

    handoff = sub.add_parser("handoff", help="Render direct handoff notification workflow")
    add_common(handoff)
    handoff.add_argument("--assignee-field-id", required=True)

    claim = sub.add_parser("claim", help="Render pending-claim group notification workflow")
    add_common(claim)
    claim.add_argument("--status-field-id", required=True)
    claim.add_argument("--pending-option-id", required=True)
    claim.add_argument("--group-cid", required=True)

    args = parser.parse_args()

    if args.kind == "handoff":
        template = load_template("handoff-notify-workflow.json")
        replacements = {
            "<任务台账tableId>": args.table_id,
            "<任务交接对象fieldId>": args.assignee_field_id,
            "<通知文案fieldId>": args.notice_field_id,
        }
    else:
        template = load_template("claim-notify-workflow.json")
        replacements = {
            "<任务台账tableId>": args.table_id,
            "<通知文案fieldId>": args.notice_field_id,
            "<交接状态fieldId>": args.status_field_id,
            "<待认领optionId>": args.pending_option_id,
            "<团队群cid>": args.group_cid,
        }

    write_output(render(template, replacements), args.out)


if __name__ == "__main__":
    main()
