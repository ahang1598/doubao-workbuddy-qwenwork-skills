"""Shared discovery and invocation policy for PPTX cloud capabilities."""

from __future__ import annotations

import json
import os
import platform as platform_module
import re
import shutil
import subprocess
import sys
from pathlib import Path


_CLI_SEGMENT = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_CLI_EXECUTABLE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_DEFAULT_CLI_NAMES = ("qwenwork", "qwenwork-cli")
_HTTP_STATUS = re.compile(r"\bHTTP\s+(\d{3})\b", re.IGNORECASE)
_OPERATION_ERROR = re.compile(r"\(([A-Z][A-Z0-9_]{2,63})\)")
_MAX_CLI_OUTPUT_BYTES = 256 << 10
_CLI_HEALTH_TIMEOUT_SECONDS = 5
_CLI_VERSION = re.compile(r"\bqwenwork\s+\S+\s+\(client-integration\)", re.IGNORECASE)
_CLI_CORE_MISSING = re.compile(
    r"(?:no such file|cannot execute|not recognized|系统找不到指定的文件)",
    re.IGNORECASE,
)
_TERMINAL_OPERATION_ERRORS = {
    "CANCELLED",
    "INVALID_ARGUMENT",
    "OPERATION_CANCELLED",
    "PARAMETER_INVALID",
    "PPTX_INVALID",
    "REQUEST_INVALID",
}


class CloudRuntimeError(RuntimeError):
    def __init__(self, code: str, *, fallback_allowed: bool, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.fallback_allowed = fallback_allowed
        self.detail = detail


def _classify_cli_failure(detail: str) -> CloudRuntimeError:
    match = _HTTP_STATUS.search(detail)
    status = int(match.group(1)) if match else 0
    if status in {401, 403}:
        return CloudRuntimeError("CLOUD_AUTH_REJECTED", fallback_allowed=True, detail=detail)
    if status == 404:
        return CloudRuntimeError("CLOUD_TOOL_UNAVAILABLE", fallback_allowed=True, detail=detail)
    if status in {408, 409, 413, 425, 429} or status >= 500:
        return CloudRuntimeError("CLOUD_TRANSIENT_FAILURE", fallback_allowed=True, detail=detail)
    if status in {400, 415, 422}:
        return CloudRuntimeError("CLOUD_REQUEST_INVALID", fallback_allowed=False, detail=detail)
    operation_error = _OPERATION_ERROR.search(detail)
    if operation_error is not None:
        code = operation_error.group(1)
        fallback_allowed = code not in _TERMINAL_OPERATION_ERRORS
        return CloudRuntimeError(code, fallback_allowed=fallback_allowed, detail=detail)
    # CLI/network implementations do not share one stable error string. In auto
    # mode an unclassified cloud failure is infrastructure-shaped and must not
    # suppress the validated local implementation.
    return CloudRuntimeError("CLOUD_OPERATION_FAILED", fallback_allowed=True, detail=detail)


def cloud_runtime_configured() -> bool:
    return bool(
        os.environ.get("QWENWORK_BASE_URL", "").strip()
        and os.environ.get("QWENWORK_TOKEN", "").strip()
    )


def _candidate_executable(candidate: Path, platform_name: str) -> bool:
    return candidate.is_file() and (
        platform_name.startswith("win") or os.access(candidate, os.X_OK)
    )


def _resource_cli_candidates(platform_name: str) -> list[Path]:
    configured = os.environ.get("QWENWORK_RESOURCES_BIN", "").strip()
    if not configured:
        return []
    root = Path(configured).expanduser()
    machine = platform_module.machine().lower()
    if platform_name.startswith("darwin"):
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        names = (f"qwenwork-darwin-{arch}", "qwenwork")
    elif platform_name.startswith("win"):
        processor = os.environ.get("PROCESSOR_ARCHITECTURE", "").lower()
        arch = "arm64" if "arm64" in {machine, processor} else "x64"
        names = (f"qwenwork-win32-{arch}.exe", "qwenwork.exe", "qwenwork-cli.exe")
    else:
        names = ()
    return [root / name for name in names]


def _qwenwork_cli_healthy(candidate: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [candidate, "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=_CLI_HEALTH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, "CLOUD_CLI_CORE_MISSING"
    detail = " ".join(((result.stderr or "") + " " + (result.stdout or "")).split())
    if result.returncode == 0 and _CLI_VERSION.search(detail):
        return True, ""
    if _CLI_CORE_MISSING.search(detail):
        return False, "CLOUD_CLI_CORE_MISSING"
    return False, "CLOUD_CLI_UNHEALTHY"


def resolve_qwenwork_cli(
    script_path: Path | None = None,
    platform_name: str | None = None,
    *,
    required: bool = False,
) -> str | None:
    effective_platform = platform_name or sys.platform
    failures: list[str] = []
    configured = os.environ.get("QWENWORK_CLI_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        resolved: str | None = None
        if _candidate_executable(candidate, effective_platform):
            resolved = str(candidate)
        if (
            "/" not in configured
            and "\\" not in configured
            and _CLI_EXECUTABLE_NAME.fullmatch(configured) is not None
        ):
            resolved = shutil.which(configured)
        if resolved:
            healthy, code = _qwenwork_cli_healthy(resolved)
            if healthy:
                return resolved
            failures.append(code)
        if required:
            raise CloudRuntimeError(
                failures[-1] if failures else "CLOUD_CLI_UNAVAILABLE",
                fallback_allowed=True,
            )
        return None

    candidates: list[str] = []
    if effective_platform.startswith("linux"):
        source = (script_path or Path(__file__)).resolve()
        roots: list[Path] = []
        if len(source.parents) > 3:
            roots.append(source.parents[3] / "bin" / "linux")
        roots.append(Path.home() / ".qwenworkcn" / "bin" / "linux")
        for root in roots:
            for name in _DEFAULT_CLI_NAMES:
                candidate = root / name
                if _candidate_executable(candidate, effective_platform):
                    candidates.append(str(candidate))

    for name in _DEFAULT_CLI_NAMES:
        discovered = shutil.which(name)
        if discovered:
            candidates.append(discovered)
    for candidate in _resource_cli_candidates(effective_platform):
        if _candidate_executable(candidate, effective_platform):
            candidates.append(str(candidate))

    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(Path(candidate).resolve())
        if normalized in seen:
            continue
        seen.add(normalized)
        healthy, code = _qwenwork_cli_healthy(candidate)
        if healthy:
            return candidate
        failures.append(code)
    if required:
        code = (
            "CLOUD_CLI_CORE_MISSING"
            if "CLOUD_CLI_CORE_MISSING" in failures
            else "CLOUD_CLI_UNHEALTHY"
            if "CLOUD_CLI_UNHEALTHY" in failures
            else "CLOUD_CLI_UNAVAILABLE"
        )
        raise CloudRuntimeError(
            code,
            fallback_allowed=True,
        )
    return None


def cloud_runtime_ready() -> bool:
    return cloud_runtime_configured() and resolve_qwenwork_cli() is not None


def document_convert_target_supported(target: str) -> bool:
    """通过服务端 Catalog 判断 document.convert 是否支持目标格式。"""

    if _CLI_SEGMENT.fullmatch(target) is None or not cloud_runtime_ready():
        return False
    cli = resolve_qwenwork_cli()
    if cli is None:
        return False
    try:
        result = subprocess.run(
            [cli, "tools", "describe", "document.convert", "-o", "json"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    stdout = result.stdout or ""
    if result.returncode != 0 or len(stdout.encode("utf-8")) > _MAX_CLI_OUTPUT_BYTES:
        return False
    try:
        descriptor = json.loads(stdout)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(descriptor, dict) or descriptor.get("id") != "document.convert":
        return False
    schema = descriptor.get("parameter_schema")
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            return False
    output = descriptor.get("output")
    if not isinstance(schema, dict) or not isinstance(output, dict):
        return False
    properties = schema.get("properties")
    target_property = properties.get("target_format") if isinstance(properties, dict) else None
    enum = target_property.get("enum") if isinstance(target_property, dict) else None
    extensions = output.get("extensions")
    return (
        isinstance(enum, list)
        and target in enum
        and isinstance(extensions, list)
        and f".{target}" in extensions
    )


def extract_document_tool_metadata(payload: dict) -> dict:
    """Return FC metadata from the stable Runtime/CLI success envelope."""

    output = payload.get("output") if isinstance(payload, dict) else None
    if not isinstance(output, dict) or output.get("status") != "success":
        raise CloudRuntimeError("CLOUD_RESPONSE_INVALID", fallback_allowed=True)
    metadata = output.get("result")
    if not isinstance(metadata, dict):
        raise CloudRuntimeError("CLOUD_RESPONSE_INVALID", fallback_allowed=True)
    return metadata


def run_document_tool(
    cli_path: tuple[str, ...],
    input_path: Path,
    *,
    save_path: Path | None = None,
    flags: tuple[tuple[str, str | None], ...] = (),
    deadline: str = "10m",
    timeout_seconds: int = 620,
) -> dict:
    if not cli_path or any(_CLI_SEGMENT.fullmatch(value) is None for value in cli_path):
        raise ValueError("qwenwork capability path is invalid")
    if not input_path.is_file():
        raise ValueError("qwenwork capability input is unavailable")
    cli = resolve_qwenwork_cli(required=True)
    command = [cli, "tools", *cli_path, str(input_path.resolve())]
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["--save", str(save_path.resolve())])
    seen: set[str] = set()
    for name, value in flags:
        if _CLI_SEGMENT.fullmatch(name) is None or name in seen:
            raise ValueError("qwenwork capability flag is invalid")
        seen.add(name)
        command.append("--" + name)
        if value is not None:
            if not isinstance(value, str) or len(value.encode("utf-8")) > 4096 or "\x00" in value:
                raise ValueError("qwenwork capability flag value is invalid")
            command.append(value)
    command.extend(["--deadline", deadline, "-o", "json"])
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CloudRuntimeError("CLOUD_TRANSIENT_FAILURE", fallback_allowed=True) from exc
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if len(stdout.encode("utf-8")) > _MAX_CLI_OUTPUT_BYTES or len(stderr.encode("utf-8")) > _MAX_CLI_OUTPUT_BYTES:
        raise CloudRuntimeError("CLOUD_RESPONSE_TOO_LARGE", fallback_allowed=True)
    if result.returncode != 0:
        detail = " ".join((stderr or stdout).split())[:500]
        raise _classify_cli_failure(detail)
    try:
        payload = json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CloudRuntimeError("CLOUD_RESPONSE_INVALID", fallback_allowed=True) from exc
    if not isinstance(payload, dict) or payload.get("state") != "completed":
        raise CloudRuntimeError("CLOUD_OPERATION_INCOMPLETE", fallback_allowed=True)
    return payload
