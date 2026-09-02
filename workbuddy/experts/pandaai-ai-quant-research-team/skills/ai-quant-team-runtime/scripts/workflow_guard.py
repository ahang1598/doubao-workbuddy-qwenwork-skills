#!/usr/bin/env python3
"""Fail-closed workflow guard for the AI quant research team.

The guard does not judge investment merit. It verifies that required commands were
actually launched, required evidence exists and is structurally usable, and sealed
artifacts have not changed before finalization.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from mode_profiles import ALL_STAGES, DEFAULT_MODE, MODE_PROFILES, active_stages, get_profile
except ModuleNotFoundError:  # Support importlib-based test and host loaders.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mode_profiles import ALL_STAGES, DEFAULT_MODE, MODE_PROFILES, active_stages, get_profile


SCHEMA_VERSION = 1
PACKAGE_VERSION = "0.4.2"
SKILLS = [
    "skill-report-replication",
    "skill-factor-mining-pandaai",
    "skill-pandaai-factor-online",
    "skill-backtest-overfit",
    "skill-strategy-tearsheet-report",
]

MEMBERS: dict[str, dict[str, Any]] = {
    "source-replication-researcher": {
        "skill": "skill-report-replication",
        "stages": ("01_source_replication",),
    },
    "factor-engineer": {
        "skill": "skill-factor-mining-pandaai",
        "stages": ("02_factor_candidates",),
    },
    "pandaai-experimenter": {
        "skill": "skill-pandaai-factor-online",
        "stages": ("03_platform_preflight", "04_platform_execution"),
    },
    "overfit-auditor": {
        "skill": "skill-backtest-overfit",
        "stages": ("05_statistical_audit",),
    },
    "performance-reporter": {
        "skill": "skill-strategy-tearsheet-report",
        "stages": ("06_tearsheet",),
    },
}

STAGE_MEMBER = {
    stage: member_id
    for member_id, spec in MEMBERS.items()
    for stage in spec["stages"]
}

LEGACY_PROFILE = {
    "active_stages": ALL_STAGES,
    "active_members": tuple(MEMBERS),
    "source_depth": None,
    "full_translation": True,
    "max_validation_charts": 19,
    "min_candidates": 4,
    "online_preflight": True,
    "paid_execution": True,
    "statistical_audit": True,
    "allowed_conclusions": ("PROMOTE_TO_OOS", "RESEARCH_REJECTED", "BLOCKED"),
}


class GuardError(RuntimeError):
    """A fail-closed validation or state error."""


@dataclass(frozen=True)
class StageSpec:
    required_files: tuple[str, ...]
    command_labels: tuple[str, ...]
    validator: Callable[[Path], dict[str, Any]]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuardError(f"invalid JSON {path}: {exc}") from exc


def inside(root: Path, path: Path) -> bool:
    try:
        return os.path.commonpath([str(root.resolve()), str(path.resolve())]) == str(root.resolve())
    except (OSError, ValueError):
        return False


def safe_path(run_dir: Path, relative: str) -> Path:
    candidate = run_dir / relative
    if not inside(run_dir, candidate):
        raise GuardError(f"path escapes run directory: {relative}")
    return candidate


def require_file(run_dir: Path, relative: str, min_bytes: int = 1) -> Path:
    path = safe_path(run_dir, relative)
    if not path.is_file():
        raise GuardError(f"missing required file: {relative}")
    size = path.stat().st_size
    if size < min_bytes:
        raise GuardError(f"required file too small: {relative} ({size} bytes)")
    return path


def as_bool(value: Any) -> bool:
    return value is True


def state_mode(state: dict[str, Any]) -> str:
    return str(state.get("mode") or "legacy")


def state_profile(state: dict[str, Any]) -> dict[str, Any]:
    mode = state_mode(state)
    return LEGACY_PROFILE if mode == "legacy" else get_profile(mode)


def workflow_stages(state: dict[str, Any]) -> tuple[str, ...]:
    return tuple(state_profile(state)["active_stages"])


def workflow_members(state: dict[str, Any]) -> tuple[str, ...]:
    return tuple(state_profile(state)["active_members"])


def validate_hashed_paths(run_dir: Path, records: Any, label: str) -> list[str]:
    if not isinstance(records, list) or not records:
        raise GuardError(f"{label} must be a non-empty list")
    paths: list[str] = []
    for index, item in enumerate(records, 1):
        if not isinstance(item, dict):
            raise GuardError(f"{label}[{index}] must be an object")
        relative = str(item.get("path", "")).strip()
        digest = str(item.get("sha256", "")).strip()
        if not relative or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise GuardError(f"{label}[{index}] has invalid path or SHA-256")
        path = require_file(run_dir, relative, 1)
        if sha256(path) != digest:
            raise GuardError(f"{label}[{index}] hash mismatch: {relative}")
        paths.append(relative)
    if len(paths) != len(set(paths)):
        raise GuardError(f"{label} contains duplicate paths")
    return paths


def validate_member_exchange(run_dir: Path, stage: str,
                             required_outputs: tuple[str, ...]) -> dict[str, Any]:
    member_id = STAGE_MEMBER.get(stage)
    if not member_id:
        raise GuardError(f"no member route declared for stage: {stage}")
    skill = str(MEMBERS[member_id]["skill"])
    packet = load_json(require_file(run_dir, f"{stage}/task_packet.json", 120))
    handoff = load_json(require_file(run_dir, f"{stage}/member_handoff.json", 160))

    if packet.get("schema_version") != 1:
        raise GuardError(f"{stage} task packet schema_version must be 1")
    if packet.get("member_id") != member_id or packet.get("stage") != stage:
        raise GuardError(f"{stage} task packet is routed to the wrong member or stage")
    if not str(packet.get("objective", "")).strip():
        raise GuardError(f"{stage} task packet missing objective")
    constraints = packet.get("constraints")
    if not isinstance(constraints, list) or not any(str(item).strip() for item in constraints):
        raise GuardError(f"{stage} task packet missing constraints")
    packet_outputs = packet.get("required_outputs")
    if not isinstance(packet_outputs, list):
        raise GuardError(f"{stage} task packet required_outputs must be a list")
    if not set(required_outputs).issubset({str(item) for item in packet_outputs}):
        raise GuardError(f"{stage} task packet does not request every required business output")
    validate_hashed_paths(run_dir, packet.get("input_evidence"), f"{stage} task input_evidence")

    if handoff.get("schema_version") != 1:
        raise GuardError(f"{stage} member handoff schema_version must be 1")
    if handoff.get("member_id") != member_id or handoff.get("skill") != skill:
        raise GuardError(f"{stage} member handoff identity or skill mismatch")
    if handoff.get("stage") != stage:
        raise GuardError(f"{stage} member handoff stage mismatch")
    if handoff.get("context_isolated") is not True:
        raise GuardError(f"{stage} member handoff does not confirm isolated context")
    invocation_id = str(handoff.get("invocation_id", "")).strip()
    if not invocation_id:
        raise GuardError(f"{stage} member handoff missing invocation_id")
    if str(handoff.get("status", "")).lower() != "completed":
        raise GuardError(f"{stage} member handoff is not completed")
    for field in ("conclusion", "reservations"):
        if not str(handoff.get(field, "")).strip():
            raise GuardError(f"{stage} member handoff missing {field}")
    evidence_paths = validate_hashed_paths(
        run_dir, handoff.get("evidence"), f"{stage} member handoff evidence"
    )
    if not set(required_outputs).issubset(set(evidence_paths)):
        raise GuardError(f"{stage} member handoff does not cover every required business output")
    return {
        "member_id": member_id,
        "skill": skill,
        "invocation_id": invocation_id,
        "input_evidence_count": len(packet["input_evidence"]),
        "handoff_evidence_count": len(evidence_paths),
    }


def normalize_date(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise GuardError(f"{field} must be YYYY-MM-DD or YYYYMMDD")


def validate_intake(run_dir: Path, *, enforce_preflight_freshness: bool = True) -> dict[str, Any]:
    state = load_state(run_dir)
    mode = state_mode(state)
    profile = state_profile(state)
    request = load_json(require_file(run_dir, "00_intake/request.json", 40))
    approval = load_json(require_file(run_dir, "00_intake/approval.json", 40))
    inventory = load_json(require_file(run_dir, "00_intake/skill_inventory.json", 100))
    if mode == "legacy":
        required = ("task", "source", "universe", "start_date", "end_date", "adjustment_cycle", "credit_budget")
        local_key = "universe"
    else:
        required = ("task", "source", "execution_mode", "local_replication_universe",
                    "start_date", "end_date", "adjustment_cycle")
        local_key = "local_replication_universe"
        if request.get("execution_mode") != mode:
            raise GuardError("request execution_mode differs from workflow mode")
        if profile["paid_execution"]:
            required += ("platform_universe", "credit_budget")
    missing = [key for key in required if request.get(key) in (None, "")]
    if missing:
        raise GuardError(f"request.json missing fields: {', '.join(missing)}")
    start = normalize_date(request["start_date"], "start_date")
    end = normalize_date(request["end_date"], "end_date")
    if start >= end:
        raise GuardError("start_date must be before end_date")
    cycle = int(request["adjustment_cycle"])
    budget = int(request.get("credit_budget", 0))
    if cycle not in range(1, 21):
        raise GuardError("adjustment_cycle must be 1-20")
    if profile["paid_execution"] and budget < 1:
        raise GuardError("credit_budget must be positive")
    if not as_bool(approval.get("approved")):
        raise GuardError("approval.json does not contain approved=true")
    if not str(approval.get("user_approval_text", "")).strip():
        raise GuardError("approval.json missing user_approval_text")
    approval_keys = (local_key, "adjustment_cycle")
    if mode != "legacy" and profile["paid_execution"]:
        if str(request.get("platform_universe")) != "沪深全A":
            raise GuardError("PandaAI platform_universe must be 沪深全A")
        approval_keys += ("platform_universe", "credit_budget")
    for key in approval_keys:
        if str(approval.get(key)) != str(request.get(key)):
            raise GuardError(f"approval parameter differs from request: {key}")
    for key in ("start_date", "end_date"):
        if normalize_date(approval.get(key), f"approval.{key}") != normalize_date(request.get(key), key):
            raise GuardError(f"approval parameter differs from request: {key}")
    if not str(request.get("oos_plan", "")).strip():
        raise GuardError("request.json missing oos_plan")
    if request.get("round_trip_cost") in (None, ""):
        raise GuardError("request.json missing round_trip_cost")
    if mode != "legacy":
        preflight = load_json(require_file(run_dir, "00_intake/environment_preflight.json", 120))
        if preflight.get("mode") != mode or preflight.get("success") is not True:
            raise GuardError("environment preflight does not prove this mode is ready")
        try:
            expires = dt.datetime.fromisoformat(str(preflight.get("expires_at", "")))
        except ValueError as exc:
            raise GuardError("environment preflight has invalid expires_at") from exc
        if expires.tzinfo is None:
            raise GuardError("environment preflight expires_at must include a timezone")
        if enforce_preflight_freshness and expires <= dt.datetime.now(dt.timezone.utc):
            raise GuardError("environment preflight expired before intake seal")
    if inventory.get("all_present") is not True or not isinstance(inventory.get("skills"), list):
        raise GuardError("skill_inventory.json does not confirm all dependencies")
    inventory_names = {str(item.get("name")) for item in inventory["skills"] if isinstance(item, dict)}
    if inventory_names != set(SKILLS):
        raise GuardError("skill_inventory.json does not contain exactly the five required skills")
    for item in inventory["skills"]:
        files = item.get("files")
        if not isinstance(files, list) or not files:
            raise GuardError(f"skill inventory has no file hashes for {item.get('name')}")
        root = Path(str(item.get("root", ""))).expanduser()
        if not root.is_dir():
            raise GuardError(f"inventoried skill root is no longer available: {item.get('name')}")
        for entry in files:
            if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))):
                raise GuardError(f"skill inventory has invalid hash for {item.get('name')}")
            current = root / str(entry.get("path", ""))
            if not current.is_file() or current.stat().st_size != entry.get("size") or sha256(current) != entry.get("sha256"):
                raise GuardError(f"inventoried skill file changed or disappeared: {item.get('name')}/{entry.get('path')}")
    return {"mode": mode, "window": [start, end], "cycle": cycle, "budget": budget,
            "local_replication_universe": request[local_key],
            "platform_universe": request.get("platform_universe"),
            "scope_approved": True, "skill_count": len(inventory["skills"])}


def validate_source(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    mode = state_mode(state)
    profile = state_profile(state)
    manifest = load_json(require_file(run_dir, "01_source_replication/manifest.json", 80))
    require_file(run_dir, "01_source_replication/final_delivery_summary.md", 300)
    require_file(run_dir, "01_source_replication/factor_formula.md", 100)
    if str(manifest.get("status", "")).lower() not in {"complete", "completed", "passed"}:
        raise GuardError("source replication manifest status is not completed")
    if not isinstance(manifest.get("data_sources"), list) or not manifest["data_sources"]:
        raise GuardError("source replication manifest has no data_sources")
    if not isinstance(manifest.get("run_history"), list) or not manifest["run_history"]:
        raise GuardError("source replication manifest has no run_history")
    if str(manifest.get("data_mode", "")).lower() in {"synthetic", "demo", "mock", "example"}:
        raise GuardError("synthetic/demo data cannot prove a research result")
    outputs = [
        "01_source_replication/manifest.json",
        "01_source_replication/final_delivery_summary.md",
        "01_source_replication/factor_formula.md",
    ]
    compact = None
    if mode != "legacy":
        if manifest.get("source_depth") != profile["source_depth"]:
            raise GuardError(f"source_depth must be {profile['source_depth']} in {mode} mode")
        if bool(manifest.get("full_translation")) != bool(profile["full_translation"]):
            raise GuardError("manifest.full_translation does not match execution mode")
    if mode in {"fast", "standard"}:
        receipt = load_json(require_file(run_dir, "01_source_replication/data_call_receipt.json", 120))
        backtest = load_json(require_file(run_dir, "01_source_replication/compact_backtest.json", 160))
        if str(receipt.get("status", "")).lower() not in {"success", "passed", "complete", "completed"}:
            raise GuardError("data_call_receipt does not show a successful real call")
        if int(receipt.get("rows", 0)) <= 0:
            raise GuardError("data_call_receipt has zero rows")
        for key in ("method", "actual_parameters", "date_range", "key_fields"):
            if receipt.get(key) in (None, "", []):
                raise GuardError(f"data_call_receipt missing {key}")
        if backtest.get("executed") is not True or int(backtest.get("n_periods", 0)) < 20:
            raise GuardError("compact_backtest does not prove an actual run with >=20 periods")
        if int(backtest.get("execution_lag_periods", 0)) < 1:
            raise GuardError("compact_backtest execution_lag_periods must be >=1")
        metrics = backtest.get("metrics")
        if not isinstance(metrics, dict) or not {
            "total_return", "annualized_return", "sharpe", "max_drawdown"
        }.issubset(metrics):
            raise GuardError("compact_backtest missing required metrics")
        if int(backtest.get("validation_chart_count", 0)) > int(profile["max_validation_charts"]):
            raise GuardError("compact_backtest exceeds the mode chart budget")
        outputs += [
            "01_source_replication/data_call_receipt.json",
            "01_source_replication/compact_backtest.json",
        ]
        compact = {"rows": int(receipt["rows"]), "periods": int(backtest["n_periods"])}
    member = validate_member_exchange(run_dir, "01_source_replication", tuple(outputs))
    return {"status": manifest.get("status"), "data_sources": len(manifest["data_sources"]),
            "source_depth": manifest.get("source_depth"), "compact": compact, "member": member}


def validate_candidates(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    minimum = int(state_profile(state)["min_candidates"])
    ledger = require_file(run_dir, "02_factor_candidates/candidates.jsonl", 80)
    require_file(run_dir, "02_factor_candidates/candidate_review.md", 200)
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(ledger.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GuardError(f"candidates.jsonl line {number} is invalid JSON: {exc}") from exc
        required = ("candidate_id", "formula", "direction", "hypothesis", "parameters", "source_anchor", "decision")
        missing = [key for key in required if item.get(key) in (None, "")]
        if missing:
            raise GuardError(f"candidate line {number} missing: {', '.join(missing)}")
        if str(item["direction"]) not in {"0", "1"}:
            raise GuardError(f"candidate line {number} direction must be 0 or 1")
        if not isinstance(item["parameters"], dict):
            raise GuardError(f"candidate line {number} parameters must be an object")
        rows.append(item)
    if len(rows) < minimum:
        raise GuardError(f"at least {minimum} factor candidates are required in {state_mode(state)} mode")
    ids = [str(item["candidate_id"]) for item in rows]
    if len(ids) != len(set(ids)):
        raise GuardError("candidate_id values must be unique")
    formulas = [re.sub(r"\s+", "", str(item["formula"]).lower()) for item in rows]
    if len(formulas) != len(set(formulas)):
        raise GuardError("duplicate candidate formulas found")
    member = validate_member_exchange(run_dir, "02_factor_candidates", (
        "02_factor_candidates/candidates.jsonl",
        "02_factor_candidates/candidate_review.md",
    ))
    return {"candidate_count": len(rows), "candidate_ids": ids, "member": member}


def checks_passed(payload: dict[str, Any], name: str) -> int:
    if not as_bool(payload.get("success")):
        raise GuardError(f"{name} success is not true")
    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        raise GuardError(f"{name} has no checks")
    for item in checks:
        if not isinstance(item, dict) or str(item.get("status", "")).lower() not in {"pass", "passed", "ok"}:
            raise GuardError(f"{name} contains a failed or malformed check")
    return len(checks)


def validate_preflight(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    mode = state_mode(state)
    preflight = load_json(require_file(run_dir, "03_platform_preflight/preflight.json", 60))
    balance = load_json(require_file(run_dir, "03_platform_preflight/balance.json", 2))
    approval = load_json(require_file(run_dir, "03_platform_preflight/approval_snapshot.json", 40))
    count = checks_passed(preflight, "preflight.json")
    if not as_bool(approval.get("costed_run_approved")):
        raise GuardError("approval_snapshot.json does not contain costed_run_approved=true")
    if not str(approval.get("user_approval_text", "")).strip():
        raise GuardError("approval_snapshot.json missing user_approval_text")
    try:
        approved_at = dt.datetime.fromisoformat(str(approval.get("approved_at", "")))
        sealed_at = dt.datetime.fromisoformat(str(load_state(run_dir)["stages"]["02_factor_candidates"]["sealed_at"]))
        if approved_at.tzinfo is None or sealed_at.tzinfo is None or approved_at < sealed_at:
            raise GuardError("cost approval predates the sealed candidate ledger")
    except ValueError as exc:
        raise GuardError("approval_snapshot.json has an invalid approved_at timestamp") from exc
    balance_text = json.dumps(balance, ensure_ascii=False).lower()
    if any(token in balance_text for token in ("login_required", "unauthorized", "not logged in")):
        raise GuardError("balance response indicates missing authentication")
    request = load_json(require_file(run_dir, "00_intake/request.json", 40))
    scope_keys = ("universe", "adjustment_cycle", "credit_budget") if mode == "legacy" else (
        "platform_universe", "adjustment_cycle", "credit_budget"
    )
    for key in scope_keys:
        if str(approval.get(key)) != str(request.get(key)):
            raise GuardError(f"preflight approval differs from intake request: {key}")
    for key in ("start_date", "end_date"):
        if normalize_date(approval.get(key), f"approval_snapshot.{key}") != normalize_date(request.get(key), key):
            raise GuardError(f"preflight approval differs from intake request: {key}")
    if float(approval.get("round_trip_cost", -1)) != float(request.get("round_trip_cost", -2)):
        raise GuardError("preflight approval differs from intake request: round_trip_cost")
    candidate_path = require_file(run_dir, "02_factor_candidates/candidates.jsonl", 80)
    if approval.get("candidates_sha256") != sha256(candidate_path):
        raise GuardError("cost approval is not bound to the current candidates.jsonl hash")
    candidate_ids = [json.loads(line)["candidate_id"] for line in noncomment_lines(candidate_path)]
    if set(map(str, approval.get("approved_candidate_ids", []))) != set(map(str, candidate_ids)):
        raise GuardError("approved_candidate_ids do not match the current candidate ledger")
    estimated = int(approval.get("estimated_credit_cost", -1))
    if estimated < 0 or estimated > int(request["credit_budget"]):
        raise GuardError("estimated_credit_cost exceeds or omits the approved budget")
    member = validate_member_exchange(run_dir, "03_platform_preflight", (
        "03_platform_preflight/preflight.json",
        "03_platform_preflight/balance.json",
        "03_platform_preflight/approval_snapshot.json",
    ))
    return {"checks": count, "balance_payload": type(balance).__name__,
            "approved_candidate_count": len(candidate_ids), "estimated_credit_cost": estimated,
            "member": member}


def noncomment_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def validate_execution(run_dir: Path) -> dict[str, Any]:
    request = load_json(require_file(run_dir, "00_intake/request.json", 40))
    candidates_path = require_file(run_dir, "02_factor_candidates/candidates.jsonl", 80)
    approved_hash = sha256(candidates_path)
    candidate_ids = [
        str(json.loads(line)["candidate_id"]) for line in noncomment_lines(candidates_path)
    ]
    execution_state = load_json(require_file(
        run_dir, "04_platform_execution/execution_state.json", 80
    ))
    if not isinstance(execution_state, dict) or set(execution_state) != set(candidate_ids):
        raise GuardError("execution_state.json does not match the approved candidate ledger")
    for candidate_id in candidate_ids:
        entry = execution_state.get(candidate_id)
        if not isinstance(entry, dict):
            raise GuardError(f"execution state is malformed for {candidate_id}")
        if entry.get("candidate_sha256") != approved_hash:
            raise GuardError(f"execution candidate hash mismatch for {candidate_id}")
        if int(entry.get("group_number", 0)) != 10:
            raise GuardError(f"execution group_number must be 10 for {candidate_id}")
        if int(entry.get("cycle", 0)) != int(request["adjustment_cycle"]):
            raise GuardError(f"execution cycle differs from intake for {candidate_id}")
        if float(entry.get("round_trip", -1)) != float(request["round_trip_cost"]):
            raise GuardError(f"execution cost differs from intake for {candidate_id}")
        if normalize_date(entry.get("start"), f"execution.{candidate_id}.start") != normalize_date(
            request["start_date"], "request.start_date"
        ) or normalize_date(entry.get("end"), f"execution.{candidate_id}.end") != normalize_date(
            request["end_date"], "request.end_date"
        ):
            raise GuardError(f"execution date range differs from intake for {candidate_id}")
    run_ids_path = require_file(run_dir, "04_platform_execution/run_ids.txt", 3)
    run_ids = [line.split()[0] for line in noncomment_lines(run_ids_path)]
    if len(run_ids) < 1 or len(run_ids) != len(set(run_ids)):
        raise GuardError("run_ids.txt must contain at least one unique run ID")
    summary_path = require_file(run_dir, "04_platform_execution/result-cache/summary.json", 30)
    summary = load_json(summary_path)
    results = summary.get("results") if isinstance(summary, dict) else None
    if not isinstance(results, list) or not results:
        raise GuardError("result-cache/summary.json has no results")
    failed = [item.get("run_id", "unknown") for item in results if not as_bool(item.get("success"))]
    if failed:
        raise GuardError(f"platform results contain failures: {', '.join(map(str, failed))}")
    result_ids = {str(item.get("run_id")) for item in results}
    missing = [run_id for run_id in run_ids if run_id not in result_ids]
    if missing:
        raise GuardError(f"summary missing run IDs: {', '.join(missing)}")
    cache = safe_path(run_dir, "04_platform_execution/result-cache")
    raw_ids = {path.stem for path in cache.glob("*.json") if path.name != "summary.json" and path.stat().st_size > 10}
    missing_raw = [run_id for run_id in run_ids if run_id not in raw_ids]
    if missing_raw:
        raise GuardError(f"raw result JSON missing for run IDs: {', '.join(missing_raw)}")
    report = require_file(run_dir, "04_platform_execution/candidates.report.csv", 20)
    rows, columns, _ = csv_profile(report)
    if rows < 1 or columns < 4:
        raise GuardError("candidates.report.csv has no usable result rows")
    member = validate_member_exchange(run_dir, "04_platform_execution", (
        "04_platform_execution/execution_state.json",
        "04_platform_execution/run_ids.txt",
        "04_platform_execution/result-cache/summary.json",
        "04_platform_execution/candidates.report.csv",
    ))
    return {"run_count": len(run_ids), "successful_results": len(results), "report_rows": rows,
            "member": member}


def csv_profile(path: Path) -> tuple[int, int, dict[str, str] | None]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if not header:
                return 0, 0, None
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise GuardError(f"invalid CSV {path}: {exc}") from exc
    dates: list[str] = []
    for row in rows:
        if not row:
            continue
        for value in row[:2]:
            raw = str(value).strip()[:10]
            try:
                dates.append(dt.date.fromisoformat(raw).isoformat())
                break
            except ValueError:
                pass
    date_range = {"start": min(dates), "end": max(dates)} if dates else None
    return len([row for row in rows if row]), len(header), date_range


def validate_statistical(run_dir: Path) -> dict[str, Any]:
    selected = require_file(run_dir, "05_statistical_audit/selected_returns.csv", 100)
    trials = require_file(run_dir, "05_statistical_audit/trials_matrix.csv", 200)
    report = load_json(require_file(run_dir, "05_statistical_audit/overfit_report.json", 80))
    with selected.open("r", encoding="utf-8-sig", newline="") as handle:
        selected_header = [str(value).strip().lower() for value in (next(csv.reader(handle), []) or [])]
    if selected_header != ["date", "return"]:
        raise GuardError(
            "selected_returns.csv must use the exact header date,return; plural returns is misread by tearsheet"
        )
    selected_rows, selected_columns, selected_dates = csv_profile(selected)
    trial_rows, trial_columns, trial_dates = csv_profile(trials)
    if selected_rows < 30:
        raise GuardError("selected_returns.csv requires at least 30 observations")
    if trial_rows < 30:
        raise GuardError("trials_matrix.csv requires at least 30 observations")
    if trial_columns < 10:
        raise GuardError("trials_matrix.csv requires at least 10 trial columns")
    if abs(selected_rows - trial_rows) > 1:
        raise GuardError("selected returns and trials matrix are not aligned in length")
    if report.get("pbo") is None:
        raise GuardError("overfit report has no PBO block; full trial matrix is required")
    if not isinstance(report.get("passed"), bool) or not str(report.get("verdict", "")).strip():
        raise GuardError("overfit report missing passed/verdict")
    if int(report.get("n_obs", 0)) < 30 or int(report.get("n_trials", 0)) < 10:
        raise GuardError("overfit report does not reflect the required sample/trial counts")
    member = validate_member_exchange(run_dir, "05_statistical_audit", (
        "05_statistical_audit/selected_returns.csv",
        "05_statistical_audit/trials_matrix.csv",
        "05_statistical_audit/overfit_report.json",
    ))
    return {
        "selected_rows": selected_rows,
        "selected_columns": selected_columns,
        "trial_rows": trial_rows,
        "trial_columns": trial_columns,
        "selected_date_range": selected_dates,
        "trial_date_range": trial_dates,
        "passed": report["passed"],
        "verdict": report["verdict"],
        "selected_header": selected_header,
        "member": member,
    }


def validate_tearsheet(run_dir: Path) -> dict[str, Any]:
    payload = load_json(require_file(run_dir, "06_tearsheet/tearsheet.json", 100))
    require_file(run_dir, "06_tearsheet/tearsheet.html", 500)
    for key in ("summary", "risk_adjusted", "n_periods", "periods_per_year"):
        if key not in payload:
            raise GuardError(f"tearsheet.json missing {key}")
    selected_rows, _, _ = csv_profile(require_file(run_dir, "05_statistical_audit/selected_returns.csv", 100))
    n_periods = int(payload.get("n_periods", 0))
    if n_periods < 30 or abs(n_periods - selected_rows) > 1:
        raise GuardError("tearsheet period count does not match selected_returns.csv")
    member = validate_member_exchange(run_dir, "06_tearsheet", (
        "06_tearsheet/tearsheet.json",
        "06_tearsheet/tearsheet.html",
    ))
    return {"n_periods": n_periods, "periods_per_year": payload["periods_per_year"],
            "member": member}


def validate_final(run_dir: Path) -> dict[str, Any]:
    state = load_state(run_dir)
    mode = state_mode(state)
    profile = state_profile(state)
    expected_members = set(workflow_members(state))
    active = set(workflow_stages(state))
    handoffs = load_json(require_file(run_dir, "07_final_review/expert_handoffs.json", 200))
    report_path = require_file(run_dir, "07_final_review/final_report.md", 500)
    if not isinstance(handoffs, dict) or not isinstance(handoffs.get("experts"), list):
        raise GuardError("expert_handoffs.json must contain an experts list")
    experts = handoffs["experts"]
    member_ids = [str(item.get("member_id", "")) for item in experts if isinstance(item, dict)]
    if len(experts) != len(expected_members) or set(member_ids) != expected_members:
        raise GuardError(f"expert handoff must contain exactly the {mode} mode member agents")
    for item in experts:
        member_id = str(item.get("member_id", ""))
        skill = str(item.get("skill", ""))
        if skill != MEMBERS[member_id]["skill"]:
            raise GuardError(f"expert handoff skill mismatch for {member_id}")
        invocation_ids = item.get("invocation_ids")
        if not isinstance(invocation_ids, list) or not invocation_ids:
            raise GuardError(f"expert handoff missing invocation_ids for {member_id}")
        expected_invocations = {
            str(load_json(require_file(run_dir, f"{stage}/member_handoff.json", 160)).get("invocation_id", ""))
            for stage in MEMBERS[member_id]["stages"] if stage in active
        }
        if set(map(str, invocation_ids)) != expected_invocations:
            raise GuardError(f"expert handoff invocation_ids do not match stage handoffs for {member_id}")
        if str(item.get("status", "")).lower() not in {"verified", "completed", "pass", "fail"}:
            raise GuardError(f"invalid expert status for {member_id}")
        for key in ("conclusion", "reservations"):
            if not str(item.get(key, "")).strip():
                raise GuardError(f"expert handoff missing {key} for {member_id}")
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise GuardError(f"expert handoff missing evidence for {member_id}")
        for relative in evidence:
            require_file(run_dir, str(relative), 1)
    conclusion = str(handoffs.get("unified_conclusion", ""))
    if conclusion not in set(profile["allowed_conclusions"]):
        raise GuardError(f"unified_conclusion is not allowed in {mode} mode")
    if "05_statistical_audit" in active:
        overfit = load_json(require_file(run_dir, "05_statistical_audit/overfit_report.json", 80))
        if conclusion == "PROMOTE_TO_OOS" and overfit.get("passed") is not True:
            raise GuardError("cannot promote when overfit audit did not pass")
    elif conclusion == "PROMOTE_TO_OOS":
        raise GuardError("fast mode cannot promote a result without statistical audit")
    text = report_path.read_text(encoding="utf-8-sig")
    expert_heading = "五位专家意见" if mode in {"legacy", "standard", "audit"} else "专家意见"
    for heading in (expert_heading, "统一结论", "证据回执", "风险与限制"):
        if heading not in text:
            raise GuardError(f"final_report.md missing section: {heading}")
    return {"mode": mode, "unified_conclusion": conclusion, "expert_count": len(experts),
            "member_ids": sorted(member_ids)}


STAGES: dict[str, StageSpec] = {
    "00_intake": StageSpec(
        ("00_intake/request.json", "00_intake/approval.json", "00_intake/skill_inventory.json"),
        ("skill_inventory",), validate_intake),
    "01_source_replication": StageSpec(
        ("01_source_replication/task_packet.json", "01_source_replication/manifest.json",
         "01_source_replication/final_delivery_summary.md", "01_source_replication/factor_formula.md",
         "01_source_replication/member_handoff.json"), ("source_quality_gate",), validate_source),
    "02_factor_candidates": StageSpec(
        ("02_factor_candidates/task_packet.json", "02_factor_candidates/candidates.jsonl",
         "02_factor_candidates/candidate_review.md", "02_factor_candidates/member_handoff.json"),
        (), validate_candidates),
    "03_platform_preflight": StageSpec(
        ("03_platform_preflight/task_packet.json", "03_platform_preflight/preflight.json",
         "03_platform_preflight/balance.json", "03_platform_preflight/approval_snapshot.json",
         "03_platform_preflight/member_handoff.json"),
        ("platform_bootstrap", "platform_balance"), validate_preflight),
    "04_platform_execution": StageSpec(
        ("04_platform_execution/task_packet.json", "04_platform_execution/execution_state.json",
         "04_platform_execution/run_ids.txt",
         "04_platform_execution/result-cache/summary.json",
         "04_platform_execution/candidates.report.csv", "04_platform_execution/member_handoff.json"),
        ("platform_factor_run", "platform_collect_results"), validate_execution),
    "05_statistical_audit": StageSpec(
        ("05_statistical_audit/task_packet.json", "05_statistical_audit/selected_returns.csv",
         "05_statistical_audit/trials_matrix.csv", "05_statistical_audit/overfit_report.json",
         "05_statistical_audit/member_handoff.json"), ("overfit_report",), validate_statistical),
    "06_tearsheet": StageSpec(
        ("06_tearsheet/task_packet.json", "06_tearsheet/tearsheet.json",
         "06_tearsheet/tearsheet.html", "06_tearsheet/member_handoff.json"),
        ("tearsheet",), validate_tearsheet),
    "07_final_review": StageSpec(
        ("07_final_review/expert_handoffs.json", "07_final_review/final_report.md"), (), validate_final),
}


ALLOWED_COMMANDS: dict[tuple[str, str], tuple[str, ...]] = {
    ("00_intake", "skill_inventory"): ("build_skill_inventory.py", "--out", "--skill"),
    ("01_source_replication", "source_quality_gate"): ("quality_gate",),
    ("03_platform_preflight", "platform_bootstrap"): ("bootstrap.py",),
    ("03_platform_preflight", "platform_balance"): ("pandaai-cli", "balance"),
    ("04_platform_execution", "platform_factor_run"): (
        "run_candidates.py", "--candidates-sha256", "--state-out", "--start", "--end",
        "--cycle", "--round-trip", "--group-number"
    ),
    ("04_platform_execution", "platform_collect_results"): ("collect_results.py", "--out-dir"),
    ("05_statistical_audit", "overfit_report"): ("overfit_report.py", "--returns", "--trials", "--out"),
    ("06_tearsheet", "tearsheet"): ("tearsheet.py", "--out", "--html"),
}


def stage_required_files(state: dict[str, Any], stage: str) -> tuple[str, ...]:
    files = list(STAGES[stage].required_files)
    mode = state_mode(state)
    if stage == "00_intake" and mode != "legacy":
        files.append("00_intake/environment_preflight.json")
    if stage == "01_source_replication" and mode in {"fast", "standard"}:
        files.extend(("01_source_replication/data_call_receipt.json",
                      "01_source_replication/compact_backtest.json"))
    return tuple(files)


def stage_command_labels(state: dict[str, Any], stage: str) -> tuple[str, ...]:
    return STAGES[stage].command_labels


def state_path(run_dir: Path) -> Path:
    return run_dir / "workflow_state.json"


def load_state(run_dir: Path) -> dict[str, Any]:
    path = state_path(run_dir)
    if not path.is_file():
        raise GuardError(f"workflow not initialized: {path}")
    state = load_json(path)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise GuardError("unsupported workflow_state schema")
    mode = state_mode(state)
    if mode != "legacy" and mode not in MODE_PROFILES:
        raise GuardError(f"unsupported workflow mode: {mode}")
    if list(state.get("stages", {}).keys()) != list(workflow_stages(state)):
        raise GuardError("workflow_state stage list is invalid")
    return state


def save_state(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    atomic_json(state_path(run_dir), state)


def previous_stages(state: dict[str, Any], stage: str) -> list[str]:
    names = list(workflow_stages(state))
    if stage not in names:
        raise GuardError(f"stage is not active in {state_mode(state)} mode: {stage}")
    return names[:names.index(stage)]


def require_previous_verified(state: dict[str, Any], stage: str, run_dir: Path | None = None) -> None:
    pending = [name for name in previous_stages(state, stage) if state["stages"][name]["status"] != "verified"]
    if pending:
        raise GuardError(f"previous stages are not verified: {', '.join(pending)}")
    if run_dir is not None:
        for name in previous_stages(state, stage):
            verify_sealed_stage(run_dir, state, name)


def redact(text: str) -> str:
    patterns = [
        (re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(access[_-]?token\s*[:=]\s*)[\"']?[^\s,\"']+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(password\s*[:=]\s*)[\"']?[^\s,\"']+"), r"\1[REDACTED]"),
    ]
    for pattern, replacement in patterns:
        text = pattern.sub(replacement, text)
    return text


def command_allowed(stage: str, label: str, argv: list[str]) -> None:
    required = ALLOWED_COMMANDS.get((stage, label))
    if not required:
        raise GuardError(f"command label is not allowed for stage: {stage}/{label}")
    joined = " ".join(argv).lower()
    if not all(token.lower() in joined for token in required):
        raise GuardError(f"command does not match allowlist for {stage}/{label}: requires {required}")
    if label == "skill_inventory":
        expected = Path(__file__).resolve().with_name("build_skill_inventory.py")
        resolved_args = []
        for value in argv:
            try:
                resolved_args.append(Path(value).resolve())
            except OSError:
                pass
        if expected not in resolved_args:
            raise GuardError("skill inventory must use this package's build_skill_inventory.py")
    if label == "tearsheet" and "--returns" not in argv and "--nav" not in argv:
        raise GuardError("tearsheet command must provide --returns or --nav")
    if label == "platform_factor_run":
        if "--create-only" in argv or "--report-only" in argv:
            raise GuardError("platform_factor_run must execute paid runs, not create-only/report-only")
    forbidden = (" login", " token", " password", "authorization")
    if any(token in f" {joined}" for token in forbidden):
        raise GuardError("credential-bearing/login commands must not be captured by the guard")


def command_receipts(run_dir: Path, stage: str, label: str | None = None) -> list[dict[str, Any]]:
    directory = run_dir / "command_receipts" / stage
    if not directory.is_dir():
        return []
    items = []
    for path in sorted(directory.glob("*.json")):
        payload = load_json(path)
        if label is None or payload.get("label") == label:
            payload["_path"] = path.relative_to(run_dir).as_posix()
            items.append(payload)
    return items


def successful_labels(run_dir: Path, stage: str) -> set[str]:
    return {str(item.get("label")) for item in command_receipts(run_dir, stage)
            if item.get("exit_code") == 0 and item.get("allowlist_passed") is True}


def artifact_profile(run_dir: Path, relative: str) -> dict[str, Any]:
    path = require_file(run_dir, relative, 1)
    profile: dict[str, Any] = {
        "path": relative.replace("\\", "/"),
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = load_json(path)
        profile["json_type"] = type(payload).__name__
    elif suffix == ".jsonl":
        profile["jsonl_records"] = len(noncomment_lines(path))
    elif suffix == ".csv":
        rows, columns, date_range = csv_profile(path)
        profile.update({"rows": rows, "columns": columns})
        if date_range:
            profile["date_range"] = date_range
    return profile


def stage_receipt_path(run_dir: Path, stage: str) -> Path:
    return run_dir / "stage_receipts" / f"{stage}.json"


def init_workflow(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    if state_path(run_dir).exists():
        raise GuardError(f"workflow already initialized: {run_dir}")
    mode = args.mode
    preflight = None
    if mode != "legacy":
        if not args.preflight_json:
            raise GuardError("fast/standard/audit init requires --preflight-json")
        preflight = load_json(args.preflight_json.resolve())
        if preflight.get("mode") != mode or preflight.get("success") is not True:
            raise GuardError("preflight mode or success status does not match init")
        if preflight.get("execution_ready") is not True:
            raise GuardError("preflight did not declare execution_ready=true")
        try:
            expires = dt.datetime.fromisoformat(str(preflight.get("expires_at", "")))
        except ValueError as exc:
            raise GuardError("preflight has invalid expires_at") from exc
        if expires.tzinfo is None or expires <= dt.datetime.now(dt.timezone.utc):
            raise GuardError("preflight has expired")
    stages = ALL_STAGES if mode == "legacy" else active_stages(mode)
    state = {
        "schema_version": SCHEMA_VERSION,
        "package_version": PACKAGE_VERSION,
        "task_id": args.task_id,
        "mode": mode,
        "run_id": f"{args.task_id}-{secrets.token_hex(4)}",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "status": "in_progress",
        "stages": {name: {"status": "pending", "sealed_at": None, "receipt": None} for name in stages},
    }
    if preflight is not None:
        atomic_json(run_dir / "00_intake" / "environment_preflight.json", preflight)
        state["environment_preflight"] = {
            "path": "00_intake/environment_preflight.json",
            "fingerprint": preflight.get("fingerprint"),
            "expires_at": preflight.get("expires_at"),
        }
    save_state(run_dir, state)
    print(json.dumps({"ok": True, "run_dir": str(run_dir), "run_id": state["run_id"]}, ensure_ascii=False))
    return 0


def exec_command(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state = load_state(run_dir)
    require_previous_verified(state, args.stage, run_dir)
    argv = list(args.command)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        raise GuardError("missing command after --")
    command_allowed(args.stage, args.label, argv)
    if args.stage == "01_source_replication" and args.label == "source_quality_gate":
        mode = state_mode(state)
        command_text = " ".join(argv).lower()
        expected = "compact_quality_gate.py" if mode in {"fast", "standard"} else "quality_gate_check.py"
        if expected not in command_text:
            raise GuardError(f"{mode} mode source gate must use {expected}")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    log_dir = run_dir / "command_logs" / args.stage
    receipt_dir = run_dir / "command_receipts" / args.stage
    log_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{stamp}-{args.label}.stdout.log"
    stderr_path = log_dir / f"{stamp}-{args.label}.stderr.log"
    started = utc_now()
    try:
        proc = subprocess.run(argv, cwd=run_dir, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=args.timeout, check=False)
        exit_code = proc.returncode
        stdout = redact(proc.stdout or "")
        stderr = redact(proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        exit_code = 124 if isinstance(exc, subprocess.TimeoutExpired) else 127
        stdout = redact(getattr(exc, "stdout", "") or "")
        stderr = redact(str(exc))
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    if args.stdout_file:
        destination = safe_path(run_dir, args.stdout_file)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(stdout, encoding="utf-8")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": args.stage,
        "label": args.label,
        "argv": argv,
        "started_at": started,
        "ended_at": utc_now(),
        "exit_code": exit_code,
        "allowlist_passed": True,
        "stdout_log": stdout_path.relative_to(run_dir).as_posix(),
        "stdout_sha256": sha256(stdout_path),
        "stderr_log": stderr_path.relative_to(run_dir).as_posix(),
        "stderr_sha256": sha256(stderr_path),
    }
    receipt_path = receipt_dir / f"{stamp}-{args.label}.json"
    atomic_json(receipt_path, receipt)
    state["stages"][args.stage]["status"] = "running" if exit_code == 0 else "blocked"
    save_state(run_dir, state)
    print(json.dumps({"ok": exit_code == 0, "exit_code": exit_code,
                      "receipt": receipt_path.relative_to(run_dir).as_posix()}, ensure_ascii=False))
    return exit_code


def seal_stage(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state = load_state(run_dir)
    require_previous_verified(state, args.stage, run_dir)
    spec = STAGES[args.stage]
    required_labels = stage_command_labels(state, args.stage)
    required_files = stage_required_files(state, args.stage)
    labels = successful_labels(run_dir, args.stage)
    missing_labels = [label for label in required_labels if label not in labels]
    if missing_labels:
        raise GuardError(f"missing successful command receipts: {', '.join(missing_labels)}")
    validation = spec.validator(run_dir)
    artifacts = [artifact_profile(run_dir, relative) for relative in required_files]
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": args.stage,
        "sealed_at": utc_now(),
        "validation": validation,
        "required_command_labels": list(required_labels),
        "successful_command_receipts": [
            item["_path"] for item in command_receipts(run_dir, args.stage)
            if item.get("exit_code") == 0 and item.get("allowlist_passed") is True
        ],
        "artifacts": artifacts,
    }
    receipt_path = stage_receipt_path(run_dir, args.stage)
    atomic_json(receipt_path, receipt)
    state["stages"][args.stage] = {
        "status": "verified",
        "sealed_at": receipt["sealed_at"],
        "receipt": receipt_path.relative_to(run_dir).as_posix(),
        "receipt_sha256": sha256(receipt_path),
    }
    # Resealing an earlier stage invalidates every downstream seal.
    active = list(workflow_stages(state))
    for downstream in active[active.index(args.stage) + 1:]:
        state["stages"][downstream] = {"status": "pending", "sealed_at": None, "receipt": None}
        old = stage_receipt_path(run_dir, downstream)
        if old.is_file():
            old.unlink()
    completion = run_dir / "completion_receipt.json"
    if completion.is_file():
        completion.unlink()
    state["status"] = "in_progress"
    save_state(run_dir, state)
    print(json.dumps({"ok": True, "stage": args.stage,
                      "receipt": receipt_path.relative_to(run_dir).as_posix()}, ensure_ascii=False))
    return 0


def verify_sealed_stage(run_dir: Path, state: dict[str, Any], stage: str) -> dict[str, Any]:
    if stage not in workflow_stages(state):
        raise GuardError(f"stage is not active in {state_mode(state)} mode: {stage}")
    info = state["stages"][stage]
    if info.get("status") != "verified" or not info.get("receipt"):
        raise GuardError(f"stage not verified: {stage}")
    receipt_path = safe_path(run_dir, str(info["receipt"]))
    if not receipt_path.is_file() or sha256(receipt_path) != info.get("receipt_sha256"):
        raise GuardError(f"stage receipt changed or missing: {stage}")
    receipt = load_json(receipt_path)
    # The environment preflight is a time-of-check gate for sealing intake. Once
    # intake is sealed, later stages rely on the receipt and artifact hashes.
    # Requiring the short-lived preflight to remain current would make a
    # 10–20 minute standard workflow impossible to complete.
    if stage == "00_intake":
        validate_intake(run_dir, enforce_preflight_freshness=False)
    else:
        STAGES[stage].validator(run_dir)
    for artifact in receipt.get("artifacts", []):
        path = require_file(run_dir, str(artifact.get("path")), 1)
        if path.stat().st_size != artifact.get("size") or sha256(path) != artifact.get("sha256"):
            raise GuardError(f"sealed artifact changed: {artifact.get('path')}")
    labels = successful_labels(run_dir, stage)
    missing = [label for label in stage_command_labels(state, stage) if label not in labels]
    if missing:
        raise GuardError(f"command receipts missing after seal for {stage}: {', '.join(missing)}")
    return receipt


def status_command(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state = load_state(run_dir)
    rows = []
    for stage in workflow_stages(state):
        info = state["stages"][stage]
        row = {"stage": stage, "status": info["status"]}
        if info["status"] == "verified":
            try:
                verify_sealed_stage(run_dir, state, stage)
                row["integrity"] = "ok"
            except GuardError as exc:
                row["integrity"] = "failed"
                row["error"] = str(exc)
        rows.append(row)
    print(json.dumps({"task_id": state["task_id"], "run_id": state["run_id"],
                      "mode": state_mode(state),
                      "workflow_status": state["status"], "stages": rows}, ensure_ascii=False, indent=2))
    return 0 if all(row.get("integrity", "ok") == "ok" for row in rows) else 1


def finalize(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    state = load_state(run_dir)
    active = workflow_stages(state)
    members = workflow_members(state)
    stage_receipts = {stage: verify_sealed_stage(run_dir, state, stage) for stage in active}
    final_validation = stage_receipts["07_final_review"]["validation"]
    overfit_validation = stage_receipts.get("05_statistical_audit", {}).get("validation")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "package_version": PACKAGE_VERSION,
        "task_id": state["task_id"],
        "run_id": state["run_id"],
        "mode": state_mode(state),
        "completed_at": utc_now(),
        "skills": SKILLS,
        "members": list(members),
        "member_invocations": {
            member_id: [
                load_json(require_file(run_dir, f"{stage}/member_handoff.json", 160))["invocation_id"]
                for stage in spec["stages"] if stage in active
            ]
            for member_id, spec in MEMBERS.items() if member_id in members
        },
        "unified_conclusion": final_validation["unified_conclusion"],
        "overfit_passed": overfit_validation["passed"] if overfit_validation else None,
        "stage_receipts": {
            stage: {
                "path": state["stages"][stage]["receipt"],
                "sha256": state["stages"][stage]["receipt_sha256"],
            } for stage in active
        },
        "disclaimer": "Workflow evidence verified; no guarantee of economic validity or future return.",
    }
    path = run_dir / "completion_receipt.json"
    atomic_json(path, receipt)
    state["status"] = "completed"
    state["completion_receipt"] = path.relative_to(run_dir).as_posix()
    state["completion_receipt_sha256"] = sha256(path)
    save_state(run_dir, state)
    print(json.dumps({"ok": True, "status": "completed",
                      "unified_conclusion": receipt["unified_conclusion"],
                      "receipt": path.relative_to(run_dir).as_posix(),
                      "sha256": sha256(path)}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    init_parser = sub.add_parser("init", help="initialize a new run directory")
    init_parser.add_argument("--run-dir", type=Path, required=True)
    init_parser.add_argument("--task-id", required=True)
    init_parser.add_argument("--mode", choices=(*MODE_PROFILES, "legacy"), default=DEFAULT_MODE,
                             help="execution profile; standard is the default")
    init_parser.add_argument("--preflight-json", type=Path,
                             help="fresh environment_preflight.py output (required except legacy)")
    init_parser.set_defaults(func=init_workflow)

    exec_parser = sub.add_parser("exec", help="run an allowlisted command and capture a receipt")
    exec_parser.add_argument("--run-dir", type=Path, required=True)
    exec_parser.add_argument("--stage", choices=STAGES, required=True)
    exec_parser.add_argument("--label", required=True)
    exec_parser.add_argument("--stdout-file", help="also write redacted stdout to this run-relative path")
    exec_parser.add_argument("--timeout", type=int, default=1800)
    exec_parser.add_argument("command", nargs=argparse.REMAINDER)
    exec_parser.set_defaults(func=exec_command)

    seal_parser = sub.add_parser("seal", help="validate and seal one stage")
    seal_parser.add_argument("--run-dir", type=Path, required=True)
    seal_parser.add_argument("--stage", choices=STAGES, required=True)
    seal_parser.set_defaults(func=seal_stage)

    status_parser = sub.add_parser("status", help="show workflow and integrity state")
    status_parser.add_argument("--run-dir", type=Path, required=True)
    status_parser.set_defaults(func=status_command)

    final_parser = sub.add_parser("finalize", help="verify every stage and issue completion receipt")
    final_parser.add_argument("--run-dir", type=Path, required=True)
    final_parser.set_defaults(func=finalize)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except GuardError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
