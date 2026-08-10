#!/usr/bin/env python3
"""按 JSON 清单运行设备测试矩阵并聚合命令级结果。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from platform_process import prepare_command, process_group_options, stop_process_tree


TARGET_LOCKS: dict[str, threading.Lock] = {}
TARGET_LOCKS_GUARD = threading.Lock()


def get_target_lock(target: str) -> threading.Lock:
    with TARGET_LOCKS_GUARD:
        if target not in TARGET_LOCKS:
            TARGET_LOCKS[target] = threading.Lock()
        return TARGET_LOCKS[target]


def safe_run_id(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    cleaned = "".join(char if char in allowed else "-" for char in value).strip("-")
    return cleaned or "run"


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取矩阵 JSON：{exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        raise ValueError("矩阵必须是包含 runs 数组的 JSON 对象")
    ids = set()
    for index, item in enumerate(payload["runs"]):
        if not isinstance(item, dict):
            raise ValueError(f"runs[{index}] 必须是对象")
        for field in ("id", "platform", "target", "command"):
            if field not in item:
                raise ValueError(f"runs[{index}] 缺少字段 {field}")
        if not isinstance(item["command"], list) or not item["command"]:
            raise ValueError(f"runs[{index}].command 必须是非空参数数组")
        if not all(isinstance(arg, str) and arg for arg in item["command"]):
            raise ValueError(f"runs[{index}].command 每个参数必须是非空字符串")
        if item["id"] in ids:
            raise ValueError(f"重复 run id：{item['id']}")
        ids.add(item["id"])
        if "env" in item and not isinstance(item["env"], dict):
            raise ValueError(f"runs[{index}].env 必须是对象")
        if "timeout_seconds" in item and int(item["timeout_seconds"]) <= 0:
            raise ValueError(f"runs[{index}].timeout_seconds 必须大于 0")
    return payload


def execute_run(item: dict[str, Any], manifest_dir: Path, out_root: Path) -> dict[str, Any]:
    run_id = safe_run_id(str(item["id"]))
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(exist_ok=True)

    command = item["command"]
    executable = command[0]
    if "/" not in executable and shutil.which(executable) is None:
        result = {
            "id": item["id"],
            "platform": item["platform"],
            "target": item["target"],
            "status": "infra_error",
            "exit_code": None,
            "duration_seconds": 0.0,
            "message": f"找不到命令：{executable}",
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "artifact_dir": str(artifact_dir),
        }
        stderr_path.write_text(result["message"] + "\n", encoding="utf-8")
        return result

    cwd_value = item.get("cwd")
    cwd = (manifest_dir / cwd_value).resolve() if cwd_value else manifest_dir
    if not cwd.is_dir():
        message = f"工作目录不存在：{cwd}"
        stderr_path.write_text(message + "\n", encoding="utf-8")
        return {
            "id": item["id"],
            "platform": item["platform"],
            "target": item["target"],
            "status": "infra_error",
            "exit_code": None,
            "duration_seconds": 0.0,
            "message": message,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "artifact_dir": str(artifact_dir),
        }

    env = os.environ.copy()
    for key, value in item.get("env", {}).items():
        if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"run {item['id']} 的 env 必须是标量字符串映射")
        env[key] = str(value)
    env.update(
        {
            "QA_RUN_ID": str(item["id"]),
            "QA_PLATFORM": str(item["platform"]),
            "QA_TARGET_ID": str(item["target"]),
            "QA_ARTIFACT_DIR": str(artifact_dir),
        }
    )
    timeout_seconds = int(item.get("timeout_seconds", 1800))
    expected = {int(code) for code in item.get("expected_exit_codes", [0])}
    target_key = f"{item['platform']}::{item['target']}"
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    with get_target_lock(target_key):
        try:
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                process = subprocess.Popen(
                    prepare_command(command),
                    cwd=str(cwd),
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    shell=False,
                    **process_group_options(),
                )
                try:
                    exit_code = process.wait(timeout=timeout_seconds)
                    status = "passed" if exit_code in expected else "failed"
                    message = "命令执行完成"
                except subprocess.TimeoutExpired:
                    cleanup = stop_process_tree(process)
                    exit_code = None
                    status = "timeout"
                    message = f"超过 {timeout_seconds}s；cleanup={cleanup.get('method', 'unknown')}"
        except (OSError, ValueError) as exc:
            exit_code = None
            status = "infra_error"
            message = str(exc)
            stderr_path.write_text(message + "\n", encoding="utf-8")

    return {
        "id": item["id"],
        "platform": item["platform"],
        "target": item["target"],
        "status": status,
        "exit_code": exit_code,
        "started_at": started_at,
        "duration_seconds": round(time.monotonic() - started, 3),
        "message": message,
        "command": command,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "artifact_dir": str(artifact_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行 iOS、Android 和小程序设备测试矩阵")
    parser.add_argument("manifest", type=Path, help="矩阵 JSON")
    parser.add_argument("--out", type=Path, default=Path("device-runs"), help="结果目录")
    parser.add_argument("--max-workers", type=int, default=1, help="最大并发数")
    parser.add_argument("--only-platform", action="append", help="只运行指定平台，可重复")
    parser.add_argument("--dry-run", action="store_true", help="只验证并打印执行计划")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="显式允许空矩阵或筛选后无目标；默认将其视为配置错误或阻塞",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_workers < 1:
        print("--max-workers 必须大于 0", file=sys.stderr)
        return 2
    manifest_path = args.manifest.expanduser().resolve()
    try:
        manifest = load_manifest(manifest_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    source_runs = manifest["runs"]
    if not source_runs and not args.allow_empty:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "configuration_error",
                    "reason": "empty_matrix",
                    "run_count": 0,
                    "runs": [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    runs = source_runs
    if args.only_platform:
        allowed = set(args.only_platform)
        runs = [item for item in runs if item["platform"] in allowed]

    if not runs:
        if args.allow_empty:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "status": "empty_allowed",
                        "reason": "explicit_allow_empty",
                        "run_count": 0,
                        "runs": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "blocked",
                    "reason": "no_matching_target",
                    "requested_platforms": args.only_platform or [],
                    "available_platforms": sorted(
                        {str(item.get("platform", "")) for item in source_runs}
                    ),
                    "run_count": 0,
                    "runs": [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "run_count": len(runs),
                    "runs": [
                        {
                            "id": item["id"],
                            "platform": item["platform"],
                            "target": item["target"],
                            "command": item["command"],
                        }
                        for item in runs
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    out_root = args.out.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(execute_run, item, manifest_path.parent, out_root): item
            for item in runs
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 - 需要把单个 worker 异常写入总报告
                item = futures[future]
                results.append(
                    {
                        "id": item["id"],
                        "platform": item["platform"],
                        "target": item["target"],
                        "status": "infra_error",
                        "exit_code": None,
                        "duration_seconds": 0.0,
                        "message": f"runner 异常：{exc}",
                    }
                )

    results.sort(key=lambda item: str(item["id"]))
    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "counts": counts,
        "runs": results,
    }
    summary_path = out_root / "matrix-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if results and all(item["status"] == "passed" for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
