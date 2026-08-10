#!/usr/bin/env python3
"""检测 Web、移动端与微信小程序自动化工具链和测试目标。"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from detect_host_environment import detect_environment

def run(args: list[str], cwd: Path | None = None, timeout: int = 10) -> dict[str, Any]:
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (FileNotFoundError, PermissionError) as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"命令超过 {timeout}s",
        }


def first_line(value: str) -> str:
    return value.splitlines()[0].strip() if value.strip() else ""


def detect_tool(name: str, version_args: list[str]) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"available": False, "path": None, "version": None}
    result = run([path, *version_args])
    version = first_line(result["stdout"] or result["stderr"])
    return {"available": result["ok"], "path": path, "version": version or None}


def detect_appium() -> dict[str, Any]:
    info = detect_tool("appium", ["--version"])
    info["drivers"] = []
    if not info["available"]:
        return info
    result = run([info["path"], "driver", "list", "--installed", "--json"], timeout=20)
    if result["ok"]:
        try:
            payload = json.loads(result["stdout"])
            if isinstance(payload, dict):
                info["drivers"] = sorted(payload.keys())
            elif isinstance(payload, list):
                info["drivers"] = payload
        except json.JSONDecodeError:
            info["drivers_raw"] = result["stdout"]
    else:
        info["driver_check_error"] = result["stderr"] or result["stdout"]
    return info


def adb_property(adb: str, serial: str, key: str) -> str | None:
    result = run([adb, "-s", serial, "shell", "getprop", key], timeout=5)
    return result["stdout"] or None if result["ok"] else None


def detect_android(adb_info: dict[str, Any]) -> list[dict[str, Any]]:
    if not adb_info["available"]:
        return []
    adb = adb_info["path"]
    result = run([adb, "devices", "-l"], timeout=10)
    devices: list[dict[str, Any]] = []
    if not result["ok"]:
        return devices
    for line in result["stdout"].splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        serial = parts[0]
        state = parts[1] if len(parts) > 1 else "unknown"
        attrs = {}
        for item in parts[2:]:
            if ":" in item:
                key, value = item.split(":", 1)
                attrs[key] = value
        device: dict[str, Any] = {
            "id": serial,
            "state": state,
            "kind": "emulator" if serial.startswith("emulator-") else "physical",
            "transport": attrs,
        }
        if state == "device":
            device.update(
                {
                    "manufacturer": adb_property(adb, serial, "ro.product.manufacturer"),
                    "model": adb_property(adb, serial, "ro.product.model"),
                    "os_version": adb_property(adb, serial, "ro.build.version.release"),
                    "api_level": adb_property(adb, serial, "ro.build.version.sdk"),
                }
            )
        devices.append(device)
    return devices


def detect_ios_simulators(xcrun_info: dict[str, Any]) -> list[dict[str, Any]]:
    if not xcrun_info["available"]:
        return []
    result = run([xcrun_info["path"], "simctl", "list", "devices", "--json"], timeout=15)
    if not result["ok"]:
        return []
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    simulators: list[dict[str, Any]] = []
    for runtime, devices in payload.get("devices", {}).items():
        os_version = runtime.rsplit("SimRuntime.", 1)[-1].replace("-", ".")
        for device in devices:
            simulators.append(
                {
                    "id": device.get("udid"),
                    "name": device.get("name"),
                    "os_version": os_version,
                    "state": device.get("state"),
                    "available": bool(device.get("isAvailable", True)),
                    "kind": "simulator",
                }
            )
    return simulators


def detect_ios_physical(xcrun_info: dict[str, Any]) -> list[dict[str, Any]]:
    if not xcrun_info["available"]:
        return []
    result = run([xcrun_info["path"], "xcdevice", "list", "--timeout", "5"], timeout=12)
    if not result["ok"]:
        return []
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    devices: list[dict[str, Any]] = []
    for item in payload:
        if item.get("simulator") is True:
            continue
        platform_name = str(item.get("platform", "")).lower()
        if "ios" not in platform_name and "iphone" not in platform_name and "ipad" not in platform_name:
            continue
        error = item.get("error")
        devices.append(
            {
                "id": item.get("identifier"),
                "name": item.get("name"),
                "os_version": item.get("operatingSystemVersion"),
                "available": error in (None, {}),
                "kind": "physical",
                "error": error,
            }
        )
    return devices


def detect_wechat_cli() -> dict[str, Any]:
    candidates = []
    if os.environ.get("WECHAT_DEVTOOLS_CLI"):
        candidates.append(Path(os.environ["WECHAT_DEVTOOLS_CLI"]).expanduser())
    candidates.extend([
        Path("/Applications/wechatwebdevtools.app/Contents/MacOS/cli"),
        Path("/Applications/微信开发者工具.app/Contents/MacOS/cli"),
    ])
    windows_roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    windows_relatives = [
        Path("Tencent/微信web开发者工具/cli.bat"),
        Path("Tencent/微信开发者工具/cli.bat"),
        Path("微信web开发者工具/cli.bat"),
        Path("微信开发者工具/cli.bat"),
        Path("Tencent/微信web开发者工具/cli.cmd"),
        Path("Tencent/微信开发者工具/cli.cmd"),
    ]
    for root in windows_roots:
        if root:
            candidates.extend(Path(root) / relative for relative in windows_relatives)
    candidates.extend([
        Path("C:/Program Files (x86)/Tencent/微信web开发者工具/cli.bat"),
        Path("C:/Program Files/Tencent/微信开发者工具/cli.bat"),
    ])
    for candidate in candidates:
        if candidate.is_file():
            return {"available": True, "path": str(candidate)}
    path = shutil.which("cli")
    return {"available": bool(path), "path": path}


def detect_miniprogram(project: Path, node_info: dict[str, Any]) -> dict[str, Any]:
    config_candidates = [project / "project.config.json", project / "app.json"]
    configs = [str(path) for path in config_candidates if path.is_file()]
    package_path = None
    if node_info["available"]:
        result = run(
            [
                node_info["path"],
                "-p",
                "require.resolve('miniprogram-automator/package.json')",
            ],
            cwd=project,
        )
        if result["ok"]:
            package_path = result["stdout"]
    return {
        "project": str(project),
        "project_configs": configs,
        "automator_available": bool(package_path),
        "automator_package": package_path,
        "ws_endpoint_configured": bool(os.environ.get("MINIPROGRAM_WS_ENDPOINT")),
    }


def build_report(project: Path) -> dict[str, Any]:
    host_environment = detect_environment()
    tools = {
        "node": detect_tool("node", ["--version"]),
        "npm": detect_tool("npm", ["--version"]),
        "appium": detect_appium(),
        "adb": detect_tool("adb", ["version"]),
        "xcodebuild": detect_tool("xcodebuild", ["-version"]),
        "xcrun": detect_tool("xcrun", ["--version"]),
        "wechat_devtools_cli": detect_wechat_cli(),
    }
    android = detect_android(tools["adb"])
    ios_simulators = detect_ios_simulators(tools["xcrun"])
    ios_physical = detect_ios_physical(tools["xcrun"])
    miniprogram = detect_miniprogram(project, tools["node"])

    drivers_text = " ".join(str(item).lower() for item in tools["appium"].get("drivers", []))
    ready = {
        "web": tools["node"]["available"] and tools["npm"]["available"],
        "android": tools["adb"]["available"] and any(item["state"] == "device" for item in android),
        "ios": host_environment["capabilities"]["ios_local"] and tools["xcodebuild"]["available"] and any(
            item.get("available") for item in [*ios_simulators, *ios_physical]
        ),
        "appium_android": tools["appium"]["available"] and "uiautomator2" in drivers_text,
        "appium_ios": host_environment["capabilities"]["ios_local"] and tools["appium"]["available"] and "xcuitest" in drivers_text,
        "miniprogram": miniprogram["automator_available"]
        and (
            miniprogram["ws_endpoint_configured"]
            or (
                tools["wechat_devtools_cli"]["available"]
                and bool(miniprogram["project_configs"])
            )
        ),
    }

    blockers = []
    if not tools["adb"]["available"]:
        blockers.append("Android：未找到 adb/Android SDK platform-tools")
    elif not ready["android"]:
        blockers.append("Android：未发现状态为 device 的模拟器或真机")
    if platform.system() != "Darwin":
        blockers.append("iOS：XCUITest/Appium XCUITest 需要 macOS host")
    elif not tools["xcodebuild"]["available"]:
        blockers.append("iOS：未找到完整 Xcode/xcodebuild")
    elif not ready["ios"]:
        blockers.append("iOS：未发现可用 Simulator 或真机")
    if not tools["appium"]["available"]:
        blockers.append("Appium：未安装 Appium core")
    else:
        if "uiautomator2" not in drivers_text:
            blockers.append("Appium：未检测到 uiautomator2 driver")
        if platform.system() == "Darwin" and "xcuitest" not in drivers_text:
            blockers.append("Appium：未检测到 xcuitest driver")
    if not miniprogram["ws_endpoint_configured"]:
        if not tools["wechat_devtools_cli"]["available"]:
            blockers.append("小程序：未找到微信开发者工具 CLI，且未设置 MINIPROGRAM_WS_ENDPOINT")
        if not miniprogram["project_configs"]:
            blockers.append("小程序：项目目录未发现 project.config.json 或 app.json，且未设置 MINIPROGRAM_WS_ENDPOINT")
    if not miniprogram["automator_available"]:
        blockers.append("小程序：项目无法解析 miniprogram-automator")

    return {
        "schema_version": 1,
        "host": host_environment,
        "project": str(project),
        "tools": tools,
        "targets": {
            "android": android,
            "ios_simulators": ios_simulators,
            "ios_physical": ios_physical,
        },
        "miniprogram": miniprogram,
        "ready": ready,
        "blockers": blockers,
        "platform_blockers": host_environment["platform_blockers"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检测 QA 自动化工具链、设备与小程序环境")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="被测项目目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    report = build_report(project)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"项目：{report['project']}")
        print("可执行能力：")
        for name, value in report["ready"].items():
            print(f"  - {name}: {'ready' if value else 'not ready'}")
        print("目标数量：")
        for name, values in report["targets"].items():
            print(f"  - {name}: {len(values)}")
        if report["blockers"]:
            print("阻塞项：")
            for item in report["blockers"]:
                print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
