#!/usr/bin/env python3
"""Run a read-only, cacheable environment preflight before a research run starts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from mode_profiles import DEFAULT_MODE, MODE_PROFILES, get_profile


SCHEMA_VERSION = 1
PLATFORM_UNIVERSE = "沪深全A"
EXPECTED_SKILLS = {
    "skill-report-replication",
    "skill-factor-mining-pandaai",
    "skill-pandaai-factor-online",
    "skill-backtest-overfit",
    "skill-strategy-tearsheet-report",
}
MIN_CLI_VERSION = (0, 1, 6)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    return value.isoformat(timespec="seconds")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command(cli: Path, *args: str) -> list[str]:
    if cli.suffix.lower() == ".py":
        return [sys.executable, str(cli), *args]
    return [str(cli), *args]


def run(argv: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
        return {"exit_code": proc.returncode, "stdout": proc.stdout or "", "stderr": proc.stderr or ""}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": 124 if isinstance(exc, subprocess.TimeoutExpired) else 127,
                "stdout": "", "stderr": str(exc)}


def parse_uv_version() -> str | None:
    uv = shutil.which("uv")
    if not uv:
        return None
    result = run([uv, "tool", "list"])
    match = re.search(r"pandaai-cli\s+v([0-9]+(?:\.[0-9]+){2})", result["stdout"])
    return match.group(1) if match else None


def version_tuple(value: str | None) -> tuple[int, int, int] | None:
    match = re.search(r"([0-9]+)\.([0-9]+)\.([0-9]+)", str(value or ""))
    return tuple(map(int, match.groups())) if match else None


def parse_skills(items: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for item in items:
        if "=" not in item:
            errors.append(f"invalid --skill value: {item}")
            continue
        name, raw_root = item.split("=", 1)
        root = Path(raw_root).expanduser().resolve()
        declaration = root / "SKILL.md"
        if not declaration.is_file():
            errors.append(f"missing SKILL.md: {name}")
            continue
        stat = declaration.stat()
        records.append({
            "name": name,
            "root": str(root),
            "declaration": str(declaration),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256(declaration),
        })
    return records, errors


def snapshot_fingerprint(mode: str, cli: Path | None, skills: list[dict[str, Any]],
                         request_sha: str | None) -> str:
    cli_stat = None
    if cli and cli.is_file():
        stat = cli.stat()
        cli_stat = {"path": str(cli), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    raw = json.dumps({"mode": mode, "cli": cli_stat, "skills": skills,
                      "request_sha256": request_sha}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_request(path: Path | None) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    if path is None:
        return None, None, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, [f"invalid request JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, None, ["request JSON must be an object"]
    return payload, sha256(path), []


def request_scope(request: dict[str, Any] | None, mode: str) -> dict[str, Any]:
    if request is None:
        return {"status": "not_provided", "compatible": True}
    local_universe = str(request.get("local_replication_universe") or request.get("universe") or "").strip()
    platform_universe = str(request.get("platform_universe") or "").strip()
    legacy = "local_replication_universe" not in request and "universe" in request
    platform_required = bool(get_profile(mode)["paid_execution"])
    issues: list[str] = []
    if not local_universe:
        issues.append("local_replication_universe is missing")
    if platform_required:
        if legacy and str(request.get("universe", "")).strip() != PLATFORM_UNIVERSE:
            issues.append("legacy universe is a local sample but the paid platform is fixed to 沪深全A")
        if not legacy and platform_universe != PLATFORM_UNIVERSE:
            issues.append("platform_universe must be 沪深全A for PandaAI paid execution")
    return {
        "status": "passed" if not issues else "blocked",
        "compatible": not issues,
        "legacy_request": legacy,
        "local_replication_universe": local_universe,
        "platform_universe": platform_universe or (str(request.get("universe", "")).strip() if legacy else ""),
        "actual_platform_universe": PLATFORM_UNIVERSE,
        "issues": issues,
    }


def sanitized_balance(cli: Path) -> tuple[dict[str, Any] | None, str | None]:
    result = run(command(cli, "--json", "balance"), timeout=45)
    if result["exit_code"] != 0:
        return None, f"balance exit {result['exit_code']}: {result['stderr'].strip()}"
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError as exc:
        return None, f"balance returned invalid JSON: {exc}"
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return None, "balance did not return success=true"
    raw_balance = payload.get("balance") if isinstance(payload.get("balance"), dict) else {}
    allowed = {key: raw_balance[key] for key in ("computingPower", "bamboo", "status", "version")
               if key in raw_balance}
    return {"success": True, "balance": allowed, "privacy_sanitized": True}, None


def try_cache(cache_path: Path, fingerprint: str, output: Path) -> bool:
    if not cache_path.is_file():
        return False
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8-sig"))
        expires = dt.datetime.fromisoformat(str(payload.get("expires_at", "")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False
    if payload.get("fingerprint") != fingerprint or expires <= now_utc():
        return False
    payload["cache_hit"] = True
    payload["cache_source"] = str(cache_path)
    atomic_json(output, payload)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODE_PROFILES, default=DEFAULT_MODE)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--cli-version")
    parser.add_argument("--skip-online", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    profile = get_profile(args.mode)
    output = args.out.resolve()
    request, request_sha, request_errors = read_request(args.request.resolve() if args.request else None)
    skills, skill_errors = parse_skills(args.skill)
    cli_raw = args.cli or (Path(shutil.which("pandaai-cli")) if shutil.which("pandaai-cli") else None)
    cli = cli_raw.expanduser().resolve() if cli_raw else None
    fingerprint = snapshot_fingerprint(args.mode, cli, skills, request_sha)
    cache_dir = (args.cache_dir or (output.parent / ".preflight-cache")).resolve()
    cache_path = cache_dir / f"{args.mode}-{fingerprint}.json"
    if not args.force and try_cache(cache_path, fingerprint, output):
        print(json.dumps({"ok": True, "cache_hit": True, "out": str(output)}, ensure_ascii=False))
        return 0

    checks: list[dict[str, Any]] = []
    errors = request_errors + skill_errors
    python_ok = sys.version_info >= (3, 9)
    checks.append({"id": "python", "status": "pass" if python_ok else "fail",
                   "detail": sys.version.split()[0]})
    if not python_ok:
        errors.append("Python 3.9 or newer is required")
    skill_names = {str(item["name"]) for item in skills}
    skills_ok = skill_names == EXPECTED_SKILLS and not skill_errors
    checks.append({"id": "skill_declarations", "status": "pass" if skills_ok else "fail",
                   "detail": f"{len(skills)} declaration(s) hashed"})
    if not skills_ok:
        errors.append("preflight requires exactly the five declared team skills")

    cli_exists = cli is not None and cli.is_file()
    help_result = run(command(cli, "factor_create", "--help")) if cli_exists else {
        "exit_code": 127, "stdout": "", "stderr": "pandaai-cli not found"
    }
    group_supported = help_result["exit_code"] == 0 and "--group-number" in help_result["stdout"]
    cli_version = args.cli_version or parse_uv_version()
    if cli_exists and not cli_version:
        version_result = run(command(cli, "--version"))
        cli_version = version_result["stdout"].strip() or version_result["stderr"].strip() or None
    cli_required = bool(profile["paid_execution"])
    checks.append({"id": "cli", "status": "pass" if cli_exists else ("fail" if cli_required else "warning"),
                   "detail": str(cli) if cli else "not installed"})
    checks.append({"id": "group_number_contract",
                   "status": "pass" if group_supported else ("fail" if cli_required else "warning"),
                   "detail": "factor_create supports --group-number" if group_supported else "unsupported or CLI absent"})
    if cli_required and (not cli_exists or not group_supported):
        errors.append("paid mode requires a PandaAI CLI that supports --group-number")
    version_ok = version_tuple(cli_version) is not None and version_tuple(cli_version) >= MIN_CLI_VERSION
    checks.append({"id": "cli_version", "status": "pass" if version_ok else ("fail" if cli_required else "warning"),
                   "detail": str(cli_version or "unknown")})
    if cli_required and not version_ok:
        errors.append("paid mode requires pandaai-cli >=0.1.6")

    scope = request_scope(request, args.mode)
    checks.append({"id": "request_scope", "status": "pass" if scope["compatible"] else "fail",
                   "detail": "; ".join(scope.get("issues", [])) or "local and platform universes are separated"})
    errors.extend(scope.get("issues", []))

    balance = None
    online_error = None
    online_requested = bool(profile["online_preflight"]) and not args.skip_online
    if online_requested and cli_exists:
        balance, online_error = sanitized_balance(cli)
        checks.append({"id": "authentication_and_balance", "status": "pass" if balance else "fail",
                       "detail": "authenticated read-only balance query" if balance else online_error})
        if online_error:
            errors.append(online_error)
    elif profile["online_preflight"]:
        checks.append({"id": "authentication_and_balance", "status": "warning",
                       "detail": "online check intentionally skipped"})

    generated = now_utc()
    expires = generated + dt.timedelta(minutes=int(profile["environment_cache_ttl_minutes"]))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "mode_label": profile["label_zh"],
        "success": not errors,
        "execution_ready": not errors and (not profile["online_preflight"] or balance is not None),
        "generated_at": iso(generated),
        "expires_at": iso(expires),
        "cache_hit": False,
        "fingerprint": fingerprint,
        "checks": checks,
        "errors": errors,
        "environment": {
            "python_version": sys.version.split()[0],
            "cli_path": str(cli) if cli else None,
            "cli_version": cli_version,
            "factor_create_group_number_supported": group_supported,
            "skills": skills,
        },
        "platform_capability": {
            "stock_pool": PLATFORM_UNIVERSE,
            "stock_pool_user_selectable": False,
            "online_preflight_requested": online_requested,
            "balance": balance,
        },
        "request_scope": scope,
        "privacy": {
            "credential_files_read": False,
            "account_identifiers_retained": False,
            "balance_allowlist": ["computingPower", "bamboo", "status", "version"],
        },
    }
    atomic_json(cache_path, payload)
    atomic_json(output, payload)
    print(json.dumps({"ok": payload["success"], "cache_hit": False, "out": str(output),
                      "cache": str(cache_path), "mode": args.mode}, ensure_ascii=False))
    return 0 if payload["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
