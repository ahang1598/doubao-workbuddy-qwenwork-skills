#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from telemetry import create_default_telemetry, infer_script_command


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def parse_args(argv: list[str]) -> dict[str, object]:
    options: dict[str, object] = {
        "command": None,
        "entry_file": None,
        "runtime": None,
        "account_id": None,
        "child_args": [],
    }
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            options["child_args"] = argv[index + 1 :]
            break
        if token in {"--command", "--entry-file", "--runtime", "--account-id"}:
            if index + 1 >= len(argv):
                fail(f"{token} requires a value")
            key = token[2:].replace("-", "_")
            options[key] = argv[index + 1]
            index += 2
            continue
        fail(f"Unknown telemetry-runner option: {token}")

    if not options["entry_file"]:
        fail("--entry-file is required")
    if not options["child_args"]:
        fail("telemetry-runner requires a child command after --")
    if not options["command"]:
        options["command"] = infer_script_command(str(options["entry_file"]))
    return options


def extract_script_argv(entry_file: str, child_args: list[str]) -> list[str]:
    entry_path = str(Path(entry_file))
    for index, token in enumerate(child_args):
        if token == entry_path:
            return [entry_path, *child_args[index + 1 :]]
    for index, token in enumerate(child_args[:-1]):
        if token.lower() == "-file" and child_args[index + 1] == entry_path:
            return [entry_path, *child_args[index + 2 :]]
    return [entry_path]


def normalize_exit_code(returncode: int) -> int:
    if returncode >= 0:
        return returncode
    return 128 + abs(returncode)


def main() -> None:
    options = parse_args(sys.argv[1:])
    child_args = list(options["child_args"])
    telemetry = create_default_telemetry()
    if options["account_id"]:
        telemetry.set_account_id(str(options["account_id"]))
    if options["runtime"]:
        telemetry.add_extra({"scriptRuntime": str(options["runtime"])})

    env = os.environ.copy()
    env["VIDEO_REDACTION_TELEMETRY_ACTIVE"] = "1"
    started_at = time.perf_counter()
    result = "success"
    error_message = None
    exit_code = 0

    try:
        completed = subprocess.run(child_args, env=env, check=False)
        exit_code = normalize_exit_code(completed.returncode)
        if completed.returncode < 0:
            result = "cancelled"
            error_message = f"child exited with signal {abs(completed.returncode)}"
        elif completed.returncode != 0:
            result = "failure"
            error_message = f"child exited with code {completed.returncode}"
    except KeyboardInterrupt:
        result = "cancelled"
        error_message = "child interrupted"
        exit_code = 130
    except OSError as error:
        result = "failure"
        error_message = str(error)
        exit_code = 1
    finally:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        try:
            telemetry.report_script_completion(
                command=str(options["command"]),
                argv=extract_script_argv(str(options["entry_file"]), child_args),
                result=result,
                duration_ms=duration_ms,
                error_message=error_message,
            )
        except Exception:
            pass

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
