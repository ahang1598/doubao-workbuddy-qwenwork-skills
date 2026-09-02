#!/usr/bin/env python3
"""Collect and normalize real PandaAI batch results into the team evidence contract."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def query(cli: str, run_id: str, timeout: int) -> dict[str, Any]:
    executable = [sys.executable, cli] if Path(cli).suffix.lower() == ".py" else [cli]
    try:
        proc = subprocess.run(
            [*executable, "--json", "factor_result", run_id], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "run_id": run_id, "error": {"message": str(exc)}}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"success": False, "run_id": run_id,
                "error": {"message": (proc.stdout + proc.stderr).strip()[:500]}}
    if not isinstance(payload, dict):
        return {"success": False, "run_id": run_id,
                "error": {"message": "factor_result JSON root is not an object"}}
    payload.setdefault("run_id", run_id)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_file", type=Path, help="execution_state.json from run_candidates.py")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-ids-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    parser.add_argument("--cli", default="pandaai-cli")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    try:
        state = json.loads(args.state_file.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": f"invalid state file: {exc}"}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    if not isinstance(state, dict) or not state:
        print(json.dumps({"ok": False, "error": "batch state is empty"}, ensure_ascii=False),
              file=sys.stderr)
        return 2

    entries: list[dict[str, Any]] = []
    for candidate_id, item in state.items():
        if not isinstance(item, dict):
            continue
        run_id = str(item.get("run_id") or "").strip()
        factor_id = str(item.get("factor_id") or "").strip()
        if run_id:
            entries.append({"candidate_id": str(candidate_id), "factor_id": factor_id,
                            "run_id": run_id, "metrics": item.get("metrics") or {}})
    if not entries:
        print(json.dumps({"ok": False, "error": "batch state contains no run IDs"}, ensure_ascii=False),
              file=sys.stderr)
        return 2
    run_ids = [entry["run_id"] for entry in entries]
    if len(run_ids) != len(set(run_ids)):
        print(json.dumps({"ok": False, "error": "duplicate run IDs in batch state"}, ensure_ascii=False),
              file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        payload = query(args.cli, entry["run_id"], args.timeout)
        atomic_json(args.out_dir / f"{entry['run_id']}.json", payload)
        success = payload.get("success") is True
        normalized.append({**entry, "success": success,
                           "status": payload.get("status"), "error": payload.get("error")})

    atomic_json(args.out_dir / "summary.json", {
        "schema_version": 1,
        "source": str(args.state_file.resolve()),
        "results": normalized,
        "success": all(item["success"] for item in normalized),
    })
    args.run_ids_out.parent.mkdir(parents=True, exist_ok=True)
    args.run_ids_out.write_text("\n".join(run_ids) + "\n", encoding="utf-8")
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    metric_fields = ["rank_ic", "ic_ir", "p_value", "monotonicity", "long_excess",
                     "short_excess", "turnover", "cost", "net_excess"]
    with args.report_out.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "candidate_id", "factor_id", "run_id", "success", *metric_fields
        ])
        writer.writeheader()
        for item in normalized:
            row = {key: item.get(key) for key in ("candidate_id", "factor_id", "run_id", "success")}
            row.update({key: item["metrics"].get(key) for key in metric_fields})
            writer.writerow(row)
    ok = all(item["success"] for item in normalized)
    print(json.dumps({"ok": ok, "run_count": len(normalized), "out_dir": str(args.out_dir),
                      "failed": [item["run_id"] for item in normalized if not item["success"]]},
                     ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
