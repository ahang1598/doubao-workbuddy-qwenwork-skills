#!/usr/bin/env python3
"""Execute an approved PandaAI candidate ledger with explicit, auditable parameters."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


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
    temp.replace(path)


def cli_command(cli: str, *args: str) -> list[str]:
    prefix = [sys.executable, cli] if Path(cli).suffix.lower() == ".py" else [cli]
    return [*prefix, "--json", *args]


def call(cli: str, args: list[str], timeout: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cli_command(cli, *args), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": {"message": str(exc)}}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": {
            "message": (proc.stdout + proc.stderr).strip()[:500] or f"exit {proc.returncode}"
        }}
    if not isinstance(payload, dict):
        return {"success": False, "error": {"message": "CLI JSON root is not an object"}}
    return payload


def parse_candidates(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON: {exc}") from exc
        candidate_id = str(item.get("candidate_id") or "").strip()
        formula = str(item.get("formula") or "").strip()
        direction = str(item.get("direction"))
        if not candidate_id or not formula or direction not in {"0", "1"}:
            raise ValueError(f"line {number}: candidate_id/formula/direction is invalid")
        if candidate_id in seen:
            raise ValueError(f"line {number}: duplicate candidate_id {candidate_id}")
        seen.add(candidate_id)
        rows.append({"candidate_id": candidate_id, "formula": formula, "direction": direction})
    if not rows:
        raise ValueError("candidate ledger is empty")
    return rows


def pct(value: Any) -> float:
    try:
        return float(str(value).rstrip("%"))
    except (TypeError, ValueError):
        return math.nan


def extract_metrics(payload: dict[str, Any], direction: str, cycle: int,
                    round_trip: float) -> dict[str, Any]:
    analysis = (payload.get("results") or {}).get("factor_analysis") or {}
    indicators = {
        row.get("indicator"): row.get("factor1")
        for row in analysis.get("query_factor_analysis_data", []) if isinstance(row, dict)
    }
    groups = {
        row.get("group"): row
        for row in analysis.get("query_group_return_analysis", []) if isinstance(row, dict)
    }
    long_side = groups.get("分组10" if direction == "1" else "分组1", {})
    short_side = groups.get("分组1" if direction == "1" else "分组10", {})
    turnover = pct(long_side.get("turnoverRate"))
    excess = pct(long_side.get("excessAnnualized"))
    cost = turnover * round_trip * (252.0 / cycle)
    return {
        "rank_ic": indicators.get("Rank_IC"),
        "ic_ir": indicators.get("IC_IR"),
        "p_value": indicators.get("p-value"),
        "monotonicity": indicators.get("单调性"),
        "long_excess": excess,
        "short_excess": pct(short_side.get("excessAnnualized")),
        "turnover": turnover,
        "cost": round(cost, 4),
        "net_excess": round(excess - cost, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--candidates-sha256", required=True)
    parser.add_argument("--state-out", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--round-trip", type=float, required=True)
    parser.add_argument("--group-number", type=int, required=True)
    parser.add_argument("--prefix", default="PD-MDD-")
    parser.add_argument("--cli", default="pandaai-cli")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    actual_hash = sha256(args.candidates)
    if actual_hash != args.candidates_sha256.lower():
        print(json.dumps({"ok": False, "error": "candidate ledger hash mismatch",
                          "actual_sha256": actual_hash}, ensure_ascii=False), file=sys.stderr)
        return 2
    if not 1 <= args.cycle <= 10 or not 2 <= args.group_number <= 10:
        print(json.dumps({"ok": False, "error": "cycle/group-number out of range"},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    try:
        candidates = parse_candidates(args.candidates)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if args.state_out.is_file():
        try:
            state = json.loads(args.state_out.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(json.dumps({"ok": False, "error": f"invalid state file: {exc}"},
                             ensure_ascii=False), file=sys.stderr)
            return 2
    else:
        state = {}
    if not isinstance(state, dict):
        print(json.dumps({"ok": False, "error": "state root is not an object"},
                         ensure_ascii=False), file=sys.stderr)
        return 2

    failures: list[str] = []
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        entry = state.setdefault(candidate_id, {})
        entry.update({
            "candidate_sha256": args.candidates_sha256.lower(),
            "formula": candidate["formula"],
            "direction": candidate["direction"],
            "start": args.start,
            "end": args.end,
            "cycle": args.cycle,
            "round_trip": args.round_trip,
            "group_number": args.group_number,
        })
        if entry.get("run_id") and entry.get("metrics"):
            continue
        if not entry.get("factor_id"):
            created = call(args.cli, [
                "factor_create", "--formula", candidate["formula"],
                "--name", args.prefix + candidate_id,
                "--start-date", args.start, "--end-date", args.end,
                "--adjustment-cycle", str(args.cycle),
                "--group-number", str(args.group_number),
                "--factor-direction", candidate["direction"],
            ], args.timeout)
            if created.get("success") is not True or not created.get("factor_id"):
                entry["error"] = {"phase": "factor_create", "detail": created.get("error", created)}
                failures.append(candidate_id)
                atomic_json(args.state_out, state)
                continue
            entry["factor_id"] = created["factor_id"]
            entry.pop("error", None)
            atomic_json(args.state_out, state)
        result = call(args.cli, ["factor_run", str(entry["factor_id"])], args.timeout)
        run_id = str(result.get("factor_run_id") or "").strip()
        if result.get("success") is not True or not run_id:
            entry["error"] = {"phase": "factor_run", "detail": result.get("error", result)}
            failures.append(candidate_id)
            atomic_json(args.state_out, state)
            continue
        entry["run_id"] = run_id
        entry["metrics"] = extract_metrics(result, candidate["direction"], args.cycle, args.round_trip)
        entry.pop("error", None)
        atomic_json(args.state_out, state)

    completed = [key for key, value in state.items() if isinstance(value, dict) and value.get("run_id")]
    print(json.dumps({"ok": not failures, "candidate_count": len(candidates),
                      "completed": completed, "failed": failures,
                      "state_out": str(args.state_out)}, ensure_ascii=False))
    return 0 if not failures and len(completed) == len(candidates) else 2


if __name__ == "__main__":
    raise SystemExit(main())
