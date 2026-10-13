#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_case(name: str, command: list[str], *, stdin: str | None = None, expected: int = 0, require_json: bool = True) -> dict:
    proc = subprocess.run(command, input=stdin, text=True, capture_output=True)
    parsed = None
    json_ok = False
    if require_json:
        try:
            parsed = json.loads(proc.stdout)
            json_ok = isinstance(parsed, dict)
        except json.JSONDecodeError:
            json_ok = False
    else:
        json_ok = True
    return {
        "name": name,
        "command": " ".join(command),
        "expected_returncode": expected,
        "actual_returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "json_ok": json_ok,
        "passed": proc.returncode == expected and json_ok and not proc.stderr,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    validate = root / "scripts" / "validate_request.py"
    sample = root / "sample_request.json"
    fixtures = root / "tests" / "fixtures"
    checks = [
        run_case("help_contract", [sys.executable, str(validate), "--help"], expected=0),
        run_case("sample_request", [sys.executable, str(validate)], stdin=sample.read_text(encoding="utf-8"), expected=0),
        run_case("missing_required", [sys.executable, str(validate)], stdin=(fixtures / "missing_request.json").read_text(encoding="utf-8"), expected=2),
        run_case("malformed_json", [sys.executable, str(validate)], stdin=(fixtures / "malformed_request.txt").read_text(encoding="utf-8"), expected=2),
    ]
    routing = root / "tests" / "actionhub_routing_cases.jsonl"
    routing_cases = [line for line in routing.read_text(encoding="utf-8").splitlines() if line.strip()] if routing.exists() else []
    checks.append({
        "name": "routing_cases_present",
        "expected_returncode": 0,
        "actual_returncode": 0 if routing_cases else 1,
        "stdout": f"routing_cases={len(routing_cases)}",
        "stderr": "",
        "json_ok": True,
        "passed": bool(routing_cases),
    })
    summary = {
        "skill": "speech-campaign-intro-coach",
        "ok": all(check["passed"] for check in checks),
        "checks": checks,
        "total": len(checks),
        "passed": sum(1 for check in checks if check["passed"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
