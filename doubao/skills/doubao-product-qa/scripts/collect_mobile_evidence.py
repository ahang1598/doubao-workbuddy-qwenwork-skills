#!/usr/bin/env python3
"""采集 Android 或 iOS Simulator 的基础测试证据。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REDACTIONS = [
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<REDACTED>"),
    (re.compile(r"(?i)((?:token|session|cookie|password)[=:]\s*)[^\s,;]+"), r"\1<REDACTED>"),
    (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "<REDACTED_EMAIL>"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "<REDACTED_PHONE>"),
]


def redact(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def run_text(command: list[str], path: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        path.write_text(redact(stdout), encoding="utf-8")
        if stderr:
            path.with_suffix(path.suffix + ".stderr").write_text(redact(stderr), encoding="utf-8")
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "file": str(path),
            "command": command,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        path.with_suffix(path.suffix + ".stderr").write_text(str(exc) + "\n", encoding="utf-8")
        return {"ok": False, "returncode": None, "file": str(path), "error": str(exc)}


def run_binary(command: list[str], path: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        with path.open("wb") as handle:
            result = subprocess.run(
                command,
                stdout=handle,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        if result.stderr:
            path.with_suffix(path.suffix + ".stderr").write_text(
                redact(result.stderr.decode("utf-8", errors="replace")), encoding="utf-8"
            )
        return {
            "ok": result.returncode == 0 and path.stat().st_size > 0,
            "returncode": result.returncode,
            "file": str(path),
            "command": command,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "returncode": None, "file": str(path), "error": str(exc)}


def screenshot_enabled(args: argparse.Namespace) -> bool:
    return bool(args.screenshot and not args.no_screenshot)


def collect_android(args: argparse.Namespace, out: Path) -> list[dict[str, Any]]:
    adb = shutil.which("adb")
    if not adb:
        return [{"ok": False, "name": "tool", "error": "未找到 adb"}]
    serial = args.target
    results = []
    results.append(
        {
            "name": "device-state",
            **run_text([adb, "-s", serial, "get-state"], out / "device-state.txt", timeout=10),
        }
    )
    info_commands = [
        [adb, "-s", serial, "shell", "getprop"],
        [adb, "-s", serial, "shell", "wm", "size"],
        [adb, "-s", serial, "shell", "wm", "density"],
    ]
    info_path = out / "device-info.txt"
    info_parts = []
    info_ok = True
    for command in info_commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        info_parts.append(f"$ {' '.join(command)}\n{result.stdout}\n{result.stderr}\n")
        info_ok = info_ok and result.returncode == 0
    info_path.write_text(redact("\n".join(info_parts)), encoding="utf-8")
    results.append({"name": "device-info", "ok": info_ok, "file": str(info_path)})

    if args.package:
        results.append(
            {
                "name": "package-info",
                **run_text(
                    [adb, "-s", serial, "shell", "dumpsys", "package", args.package],
                    out / "package-info.txt",
                    timeout=30,
                ),
            }
        )
    if screenshot_enabled(args):
        results.append(
            {
                "name": "screenshot",
                **run_binary(
                    [adb, "-s", serial, "exec-out", "screencap", "-p"],
                    out / "screenshot.png",
                    timeout=30,
                ),
            }
        )
    if not args.no_logs:
        results.append(
            {
                "name": "logcat",
                **run_text(
                    [adb, "-s", serial, "logcat", "-d", "-v", "threadtime", "-t", args.log_lines],
                    out / "logcat.txt",
                    timeout=60,
                ),
            }
        )
        results.append(
            {
                "name": "crash-log",
                **run_text(
                    [adb, "-s", serial, "logcat", "-d", "-b", "crash", "-v", "threadtime"],
                    out / "crash-logcat.txt",
                    timeout=30,
                ),
            }
        )
    return results


def collect_ios_simulator(args: argparse.Namespace, out: Path) -> list[dict[str, Any]]:
    xcrun = shutil.which("xcrun")
    if not xcrun:
        return [{"ok": False, "name": "tool", "error": "未找到 xcrun"}]
    udid = args.target
    results = [
        {
            "name": "device-info",
            **run_text(
                [xcrun, "simctl", "list", "devices", "--json"],
                out / "simulator-devices.json",
                timeout=20,
            ),
        }
    ]
    if args.package:
        results.append(
            {
                "name": "app-container",
                **run_text(
                    [xcrun, "simctl", "get_app_container", udid, args.package],
                    out / "app-container.txt",
                    timeout=20,
                ),
            }
        )
    if screenshot_enabled(args):
        screenshot = out / "screenshot.png"
        result = subprocess.run(
            [xcrun, "simctl", "io", udid, "screenshot", str(screenshot)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        results.append(
            {
                "name": "screenshot",
                "ok": result.returncode == 0 and screenshot.is_file(),
                "returncode": result.returncode,
                "file": str(screenshot),
                "stderr": redact(result.stderr),
            }
        )
    if not args.no_logs:
        if args.process_name:
            predicate = f'process == "{args.process_name}"'
            results.append(
                {
                    "name": "unified-log",
                    **run_text(
                        [
                            xcrun,
                            "simctl",
                            "spawn",
                            udid,
                            "log",
                            "show",
                            "--last",
                            args.since,
                            "--style",
                            "compact",
                            "--predicate",
                            predicate,
                        ],
                        out / "unified-log.txt",
                        timeout=90,
                    ),
                }
            )
        else:
            results.append(
                {
                    "name": "unified-log",
                    "ok": True,
                    "skipped": True,
                    "message": "未提供 --process-name，为避免采集整个设备日志已跳过",
                }
            )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="采集移动端截图、设备信息、日志和崩溃证据")
    parser.add_argument("--platform", choices=["android", "ios-simulator"], required=True)
    parser.add_argument("--target", required=True, help="Android serial 或 iOS Simulator UDID")
    parser.add_argument("--out", type=Path, required=True, help="证据输出目录")
    parser.add_argument("--package", help="Android package 或 iOS bundle ID")
    parser.add_argument("--process-name", help="iOS Simulator 日志进程名")
    parser.add_argument("--since", default="5m", help="iOS unified log 时间范围")
    parser.add_argument("--log-lines", default="5000", help="Android logcat 最大行数")
    parser.add_argument("--screenshot", action="store_true", help="已获得用户确认后采集截图")
    parser.add_argument("--no-screenshot", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-logs", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.out.expanduser().resolve()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "platform": args.platform,
                    "target": args.target,
                    "out": str(out),
                    "package": args.package,
                    "process_name": args.process_name,
                    "screenshot": screenshot_enabled(args),
                    "logs": not args.no_logs,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    out.mkdir(parents=True, exist_ok=True)
    if args.platform == "android":
        results = collect_android(args, out)
    else:
        results = collect_ios_simulator(args, out)
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": args.platform,
        "target": args.target,
        "results": results,
    }
    (out / "evidence-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    required_failures = [
        item
        for item in results
        if not item.get("ok") and item.get("name") in {"tool", "device-state", "device-info", "screenshot"}
    ]
    return 1 if required_failures else 0


if __name__ == "__main__":
    sys.exit(main())
