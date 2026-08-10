#!/usr/bin/env python3
"""跨 Windows/POSIX 的参数数组执行、进程组启动和进程树清理。"""

from __future__ import annotations

import os
import platform
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any


def prepare_command(command: list[str], system: str | None = None) -> list[str]:
    current = system or platform.system()
    if current != "Windows" or not command:
        return command
    executable = command[0]
    resolved = shutil.which(executable) if not Path(executable).is_file() else executable
    candidate = str(resolved or executable)
    if Path(candidate).suffix.lower() not in {".cmd", ".bat"}:
        return [candidate, *command[1:]]
    comspec = os.environ.get("COMSPEC", "cmd.exe")
    return [comspec, "/d", "/s", "/c", subprocess.list2cmdline([candidate, *command[1:]])]


def process_group_options(system: str | None = None) -> dict[str, Any]:
    current = system or platform.system()
    if current == "Windows":
        return {"creationflags": int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))}
    return {"start_new_session": True}


def stop_process_tree(process: subprocess.Popen[Any] | None, system: str | None = None) -> dict[str, Any]:
    if process is None:
        return {"started_by_runner": False, "stopped": False}
    if process.poll() is not None:
        return {"started_by_runner": True, "stopped": True, "exit_code": process.returncode}
    current = system or platform.system()
    method = ""
    if current == "Windows":
        try:
            ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
            if ctrl_break is not None:
                process.send_signal(ctrl_break)
                process.wait(timeout=5)
                method = "CTRL_BREAK_EVENT"
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            taskkill = shutil.which("taskkill")
            if taskkill:
                subprocess.run(
                    [taskkill, "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                method = "taskkill_tree"
            else:
                process.terminate()
                method = "terminate"
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
                method = "kill"
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=8)
            method = "SIGTERM_process_group"
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
            method = "SIGKILL_process_group"
    return {
        "started_by_runner": True,
        "stopped": process.poll() is not None,
        "exit_code": process.returncode,
        "method": method,
        "host_system": current,
    }
