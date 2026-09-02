#!/usr/bin/env python3
"""WorkBuddy-safe PandaAI CLI status and interactive-login entry point."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


MIN_VERSION = (0, 1, 6)
CONFIG_PATH = Path.home() / ".pandaai" / "config.yaml"
BASE_CONFIG = (
    "gateway_url: https://www.pandaaiquant.com/pandaApi\n"
    "country_code: '86'\n"
)


def run_capture(command: list[str], timeout: int = 60) -> dict:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "exit_code": 124 if isinstance(exc, subprocess.TimeoutExpired) else 127,
            "stdout": "",
            "stderr": type(exc).__name__,
        }


def parse_json(result: dict) -> dict | None:
    if result["exit_code"] != 0:
        return None
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def version_tuple(value: str | None) -> tuple[int, int, int] | None:
    match = re.search(r"([0-9]+)\.([0-9]+)\.([0-9]+)", str(value or ""))
    return tuple(map(int, match.groups())) if match else None


def detect_version() -> str | None:
    uv = shutil.which("uv")
    if not uv:
        return None
    result = run_capture([uv, "tool", "list"])
    match = re.search(r"pandaai-cli\s+v([0-9]+(?:\.[0-9]+){2})", result["stdout"])
    return match.group(1) if match else None


def seed_base_config() -> bool:
    if CONFIG_PATH.exists():
        return False
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(BASE_CONFIG, encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
    return True


def safe_account_snapshot(executable: str) -> tuple[dict | None, str | None]:
    balance_payload = parse_json(run_capture([executable, "--json", "balance"], timeout=60))
    if not balance_payload or balance_payload.get("success") is not True:
        return None, "LOGIN_REQUIRED"
    raw_balance = balance_payload.get("balance")
    if not isinstance(raw_balance, dict):
        return None, "BALANCE_RESPONSE_INVALID"
    balance = {
        key: raw_balance[key]
        for key in ("computingPower", "bamboo", "status", "version")
        if key in raw_balance
    }
    factor_payload = parse_json(
        run_capture(
            [executable, "--json", "factor_list", "--limit", "1", "--no-detail"],
            timeout=60,
        )
    )
    if not factor_payload or factor_payload.get("success") is not True:
        return None, "FACTOR_LIST_RESPONSE_INVALID"
    computing_power = balance.get("computingPower")
    affordable_runs = None
    if isinstance(computing_power, (int, float)):
        affordable_runs = int(max(0, computing_power) // 2)
    return {
        "balance": balance,
        "approx_affordable_runs": affordable_runs,
        "factor_count": factor_payload.get("total"),
    }, None


def status_payload(executable: str | None, *, after_login: bool = False, seeded: bool = False) -> dict:
    base = {
        "ok": False,
        "status": "CLI_MISSING",
        "python_version": sys.version.split()[0],
        "minimum_cli_version": "0.1.6",
        "config_present": CONFIG_PATH.is_file(),
        "config_seeded": seeded,
        "credential_policy": "interactive CLI only; never accept credentials in chat or logs",
        "privacy": {
            "raw_cli_json_retained": False,
            "account_identifiers_retained": False,
            "config_content_retained": False,
        },
    }
    if sys.version_info < (3, 9):
        base["status"] = "PYTHON_UNSUPPORTED"
        return base
    if not executable:
        base["next_action"] = "Install pandaai-cli >=0.1.6 in a user-visible terminal"
        return base
    cli_version = detect_version()
    base["cli_present"] = True
    base["cli_version"] = cli_version
    if version_tuple(cli_version) is None or version_tuple(cli_version) < MIN_VERSION:
        base["status"] = "CLI_VERSION_UNSUPPORTED"
        base["next_action"] = "Install or upgrade with uv tool install --upgrade pandaai-cli"
        return base
    help_result = run_capture([executable, "factor_create", "--help"])
    if help_result["exit_code"] != 0 or "--group-number" not in help_result["stdout"]:
        base["status"] = "CLI_CONTRACT_UNSUPPORTED"
        return base
    snapshot, error = safe_account_snapshot(executable)
    if error:
        base["status"] = error
        base["next_action"] = "Run python scripts/bootstrap.py --login in a user-visible terminal"
        return base
    base.update(snapshot or {})
    base["ok"] = True
    base["status"] = "READY_AFTER_LOGIN" if after_login else "READY"
    base["authenticated"] = True
    return base


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="read-only login and account check")
    parser.add_argument("--login", action="store_true", help="start credential-safe interactive login")
    args = parser.parse_args()
    if args.status and args.login:
        parser.error("choose only one operation")
    executable = shutil.which("pandaai-cli")
    if not args.login:
        payload = status_payload(executable)
        emit(payload)
        return 0 if payload["ok"] else 2

    preliminary = status_payload(executable)
    if preliminary["ok"]:
        emit(preliminary)
        return 0
    if preliminary["status"] not in {"LOGIN_REQUIRED", "BALANCE_RESPONSE_INVALID"}:
        emit(preliminary)
        return 2
    seeded = seed_base_config()
    if not (sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()):
        payload = status_payload(executable, seeded=seeded)
        payload["ok"] = False
        payload["status"] = "LOGIN_REQUIRES_INTERACTIVE_TERMINAL"
        payload["next_action"] = "Open a user-visible terminal and run: python scripts/bootstrap.py --login"
        emit(payload)
        return 3
    print(
        "PandaAI CLI will now request login information directly. "
        "Do not paste it into WorkBuddy chat.",
        file=sys.stderr,
    )
    login = subprocess.run([executable, "login"], check=False)
    if login.returncode != 0:
        emit({
            "ok": False,
            "status": "LOGIN_FAILED",
            "exit_code": login.returncode,
            "credential_policy": "no credentials were captured by this wrapper",
        })
        return 2
    payload = status_payload(executable, after_login=True, seeded=seeded)
    emit(payload)
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
