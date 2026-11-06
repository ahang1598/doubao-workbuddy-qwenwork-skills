#!/usr/bin/env python3
"""Monitor one PPT generation log using unambiguous terminal markers only.

``[DONE]`` is written by ``generate_ppt.py`` only after the generated PPTX has
been downloaded.  Progress messages such as "大纲生成完成" and "PPT 全部生成
完成" are deliberately not terminal states.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SUCCESS_MARKER = "[DONE]"
FAILURE_MARKER = "[ERROR]"
REQUEST_START_MARKER = "发送请求 path="
DEFAULT_TAIL_BYTES = 16 * 1024


def read_log_tail(log_path: Path, max_bytes: int = DEFAULT_TAIL_BYTES) -> str:
    """Read a bounded UTF-8 log tail without loading a growing log in full."""
    if not log_path.is_file():
        return ""
    with log_path.open("rb") as log_file:
        log_file.seek(0, 2)
        size = log_file.tell()
        log_file.seek(max(0, size - max_bytes))
        return log_file.read().decode("utf-8", errors="replace")


def current_attempt_log(log_tail: str) -> str:
    """Keep only the most recent generation attempt in an append-only log.

    A user may retry a failed generation with the same session ID.  Its log is
    deliberately retained for diagnosis, but an ``[ERROR]`` from that earlier
    attempt must not fail monitoring of the new request.
    """
    latest_start = log_tail.rfind(REQUEST_START_MARKER)
    return log_tail[latest_start:] if latest_start >= 0 else log_tail


def terminal_status(log_tail: str) -> str | None:
    """Return the current attempt's ``done``, ``failed``, or pending status."""
    attempt_log = current_attempt_log(log_tail)
    last_done = attempt_log.rfind(SUCCESS_MARKER)
    last_error = attempt_log.rfind(FAILURE_MARKER)
    if last_done < 0 and last_error < 0:
        return None
    return "done" if last_done > last_error else "failed"


def resolve_output_path(log_path: Path) -> Path:
    """Read and validate the result manifest written before ``[DONE]``."""
    result_path = log_path.parent / "generation_result.json"
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"生成结果清单不可用：{result_path}") from exc
    output_value = result.get("primary_pptx")
    if result.get("status") != "done" or not isinstance(output_value, str):
        raise ValueError("生成结果清单不包含可交付 PPTX")
    output_path = Path(output_value)
    if not output_path.is_file() or output_path.suffix.lower() != ".pptx":
        raise ValueError(f"生成结果中的 PPTX 不存在或格式不正确：{output_path}")
    return output_path.resolve()


def display_tail(log_tail: str, max_lines: int = 8) -> str:
    """Keep progress output compact while status detection uses the full window."""
    return "\n".join(log_tail.rstrip().splitlines()[-max_lines:])


def check_once(log_path: Path, poll_label: str = "") -> str:
    """Print one snapshot and return ``pending``, ``done``, or ``failed``.

    A single snapshot returns immediately, so the skill can report progress
    before scheduling the next check. A long foreground loop buffers stdout
    until the PPT task has already ended.
    """
    log_tail = read_log_tail(log_path)
    suffix = f" {poll_label}" if poll_label else ""
    print(f"=== PPT generation check{suffix} ===")
    if log_tail:
        print(display_tail(log_tail))
    else:
        print("[waiting for generate.log]")

    status = terminal_status(log_tail)
    if status == "done":
        try:
            output_path = resolve_output_path(log_path)
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            status = "failed"
        else:
            print(f"PPT_OUTPUT_PATH={output_path}")
    result = status or "pending"
    print(f"MONITOR_RESULT={result}")
    return result


def monitor(log_path: Path, interval_seconds: float, max_polls: int) -> str:
    """Backward-compatible blocking monitor for direct command-line callers."""
    for poll_count in range(1, max_polls + 1):
        status = check_once(log_path, f"{poll_count}/{max_polls}")
        if status != "pending":
            return status
        if poll_count < max_polls:
            time.sleep(interval_seconds)

    print("MONITOR_RESULT=timeout")
    return "timeout"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Monitor PPT generation until [DONE], [ERROR], or timeout."
    )
    parser.add_argument("log_file", help="Path to the session's generate.log")
    parser.add_argument(
        "--check-once",
        action="store_true",
        help="只检查并打印一轮日志；未结束时返回 MONITOR_RESULT=pending",
    )
    parser.add_argument("--interval-seconds", type=float, default=15.0)
    parser.add_argument("--max-polls", type=int, default=80)
    parser.add_argument(
        "--resolve-output",
        action="store_true",
        help="只读取并输出已完成任务的本地 PPTX 路径，不执行轮询",
    )
    args = parser.parse_args()

    if args.interval_seconds <= 0:
        parser.error("--interval-seconds 必须大于 0")
    if args.max_polls <= 0:
        parser.error("--max-polls 必须大于 0")

    log_path = Path(args.log_file)
    if args.resolve_output:
        try:
            print(resolve_output_path(log_path))
        except ValueError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        return 0

    if args.check_once:
        result = check_once(log_path)
        # ``pending`` is expected rather than a failed shell command. This
        # lets the skill report the snapshot and schedule the next check.
        return {"done": 0, "pending": 0, "failed": 1}[result]

    result = monitor(log_path, args.interval_seconds, args.max_polls)
    return {"done": 0, "failed": 1, "timeout": 2}[result]


if __name__ == "__main__":
    raise SystemExit(main())
