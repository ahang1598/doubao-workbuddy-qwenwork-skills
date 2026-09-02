#!/usr/bin/env python3
"""Build a deterministic inventory of the five local QuantSkills dependencies."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path


EXPECTED = {
    "skill-report-replication": ["SKILL.md", "scripts/quality_gate_check.py"],
    "skill-factor-mining-pandaai": ["SKILL.md"],
    "skill-pandaai-factor-online": [
        "SKILL.md", "scripts/bootstrap.py", "scripts/batch.py"
    ],
    "skill-backtest-overfit": ["SKILL.md", "scripts/overfit_report.py"],
    "skill-strategy-tearsheet-report": ["SKILL.md", "scripts/tearsheet.py"],
}

DECLARED_NAMES = {
    "skill-report-replication": {"skill-report-replication", "report-replication"},
    "skill-factor-mining-pandaai": {"skill-factor-mining-pandaai", "factor-mining-pandaai"},
    "skill-pandaai-factor-online": {"skill-pandaai-factor-online", "pandaai-factor-online"},
    "skill-backtest-overfit": {"skill-backtest-overfit"},
    "skill-strategy-tearsheet-report": {"skill-strategy-tearsheet-report"},
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def parse_mapping(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    name, raw = value.split("=", 1)
    if name not in EXPECTED:
        raise argparse.ArgumentTypeError(f"unexpected skill name: {name}")
    return name, Path(raw).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skill", action="append", type=parse_mapping, required=True)
    args = parser.parse_args()
    supplied = dict(args.skill)
    if set(supplied) != set(EXPECTED) or len(args.skill) != len(EXPECTED):
        missing = sorted(set(EXPECTED) - set(supplied))
        extra_or_duplicate = len(args.skill) - len(supplied)
        print(json.dumps({"ok": False, "error": "exactly five unique skills are required",
                          "missing": missing, "duplicates": max(0, extra_or_duplicate)}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    records = []
    errors = []
    for name, root in supplied.items():
        files = []
        declaration = root / "SKILL.md"
        if not root.is_dir():
            errors.append(f"{name}: directory not found: {root}")
            continue
        if declaration.is_file():
            text = declaration.read_text(encoding="utf-8-sig", errors="replace")
            match = re.search(r"(?m)^name:\s*['\"]?([^'\"\r\n]+)", text)
            declared = match.group(1).strip() if match else None
            if declared not in DECLARED_NAMES[name]:
                errors.append(
                    f"{name}: SKILL.md declares {declared!r}; expected one of {sorted(DECLARED_NAMES[name])}"
                )
        for relative in EXPECTED[name]:
            path = root / relative
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"{name}: missing {relative}")
                continue
            files.append({"path": relative, "size": path.stat().st_size, "sha256": digest(path)})
        records.append({"name": name, "root": str(root), "files": files})
    payload = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "all_present": not errors and len(records) == len(EXPECTED),
        "skills": records,
        "errors": errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["all_present"], "out": str(args.out), "errors": errors}, ensure_ascii=False))
    return 0 if payload["all_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
