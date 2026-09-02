#!/usr/bin/env python3
"""Run deterministic offline package tests and write an auditable smoke artifact."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path, env: dict[str, str]) -> dict[str, object]:
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, check=False)
    return {
        "argv": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    checks = [
        run([sys.executable, "scripts/validate_agent.py", ".", "--json"], root, env),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], root, env),
        run([sys.executable, "scripts/workflow_guard.py", "--help"], root, env),
    ]
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version,
        "scope": "offline structure, three execution profiles, cached preflight, universe separation, isolated-member handoff, and evidence-gate fixtures; no live AgentTool or paid PandaAI calls",
        "passed": all(item["exit_code"] == 0 for item in checks),
        "checks": checks,
    }
    report = args.out / "smoke_results.json"
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report)
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
