#!/usr/bin/env python3
"""检测宿主 OS、架构、Shell 方言和本机可执行的平台能力。"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any


def shell_info(system: str) -> dict[str, Any]:
    candidates: list[tuple[str, str | None]] = []
    if system == "Windows":
        candidates.extend(
            [
                ("pwsh", shutil.which("pwsh")),
                ("powershell", shutil.which("powershell")),
                ("cmd", os.environ.get("COMSPEC") or shutil.which("cmd")),
            ]
        )
        preferred = next((name for name, path in candidates if path and name in {"pwsh", "powershell"}), "cmd")
        dialect = "powershell" if preferred in {"pwsh", "powershell"} else "cmd"
    else:
        configured = os.environ.get("SHELL")
        if configured:
            candidates.append((Path(configured).name, configured))
        for name in ("zsh", "bash", "sh"):
            path = shutil.which(name)
            if path and all(existing != path for _, existing in candidates):
                candidates.append((name, path))
        preferred = candidates[0][0] if candidates else "sh"
        dialect = "posix"
    return {
        "preferred": preferred,
        "dialect": dialect,
        "detected": [{"name": name, "path": path} for name, path in candidates if path],
    }


def detect_environment(system_override: str | None = None) -> dict[str, Any]:
    system = system_override or platform.system()
    shell = shell_info(system)
    local_ios = system == "Darwin"
    local_miniprogram = system in {"Darwin", "Windows"}
    blockers = []
    if not local_ios:
        blockers.append(
            {
                "platform": "ios",
                "code": "IOS_REQUIRES_MACOS",
                "execution_level": "blocked",
                "fallback_path": "manual_handoff",
                "manual_handoff_required": True,
                "reason": f"{system} 本机不能运行 Xcode、iOS Simulator 或 XCUITest",
                "minimal_unblock_actions": [
                    "连接可访问的 macOS 测试主机并提供标准 runner 地址",
                    "或配置远程 Appium + XCUITest",
                    "或使用支持 iOS 的设备云",
                ],
                "manual_prerequisites": [
                    "准备已安装待测版本的 iPhone/iPad，或提供 TestFlight/企业分发/MDM/Ad Hoc 安装入口",
                    "记录设备型号、iOS 版本和 App 构建版本",
                ],
            }
        )
    if not local_miniprogram:
        blockers.append(
            {
                "platform": "miniprogram",
                "code": "MINIPROGRAM_DEVTOOLS_HOST_UNSUPPORTED",
                "execution_level": "blocked",
                "fallback_path": "manual_handoff",
                "manual_handoff_required": True,
                "reason": f"{system} 不作为微信开发者工具本地标准宿主",
                "minimal_unblock_actions": ["使用 Windows/macOS 主机提供小程序工程入口", "或提供已授权 automator endpoint"],
                "manual_prerequisites": ["准备可打开目标小程序的手机和微信版本", "确认测试账号与测试数据"],
            }
        )
    return {
        "schema_version": 1,
        "host_os": system,
        "system": system,
        "release": platform.release(),
        "architecture": platform.machine(),
        "machine": platform.machine(),
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "shell": shell,
        "path": {
            "separator": os.sep if not system_override else ("\\" if system == "Windows" else "/"),
            "path_list_separator": os.pathsep if not system_override else (";" if system == "Windows" else ":"),
            "executable_suffixes": [".exe", ".cmd", ".bat"] if system == "Windows" else [""],
        },
        "capabilities": {
            "web_api_local": True,
            "android_local": True,
            "ios_local": local_ios,
            "miniprogram_devtools_local": local_miniprogram,
        },
        "command_policy": {
            "preferred_shell": shell["preferred"],
            "dialect": shell["dialect"],
            "render_only_detected_dialect": True,
            "prefer_argument_arrays": True,
            "inline_environment_assignment_supported": shell["dialect"] == "posix",
        },
        "platform_blockers": blockers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检测 QA 命令应使用的宿主 OS 与 Shell 方言")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--simulate-system", choices=["Windows", "Darwin", "Linux"], help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = detect_environment(args.simulate_system)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Host: {report['host_os']} / {report['architecture']}")
        print(f"Shell: {report['shell']['preferred']} ({report['shell']['dialect']})")
        print("Capabilities:")
        for name, available in report["capabilities"].items():
            print(f"  - {name}: {'available' if available else 'blocked'}")
        for blocker in report["platform_blockers"]:
            print(f"[BLOCKED] {blocker['platform']}: {blocker['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
