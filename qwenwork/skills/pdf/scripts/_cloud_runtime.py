"""Shared discovery policy for PDF Skill cloud Capability adapters."""

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
_SERVER_FAILURE = re.compile(r"\bfailed\s+\(([A-Z][A-Z0-9_]{2,63})\):")
_MAX_CLI_OUTPUT_BYTES = 256 << 10
_CLI_HEALTH_TIMEOUT_SECONDS = 5
_CLI_VERSION = re.compile(r"\bqwenwork\s+\S+\s+\(client-integration\)", re.IGNORECASE)
_CLI_CORE_MISSING = re.compile(
    r"(?:no such file|cannot execute|not recognized|系统找不到指定的文件)",
    re.IGNORECASE,
)
_RETRYABLE_SERVER_FAILURES = {
    "ARTIFACT_DOWNLOAD_FAILED",
    "ARTIFACT_UPLOAD_FAILED",
    "DOCUMENT_TOOL_TIMEOUT",
    "RESOURCE_EXHAUSTED",
}
_CLOUD_BACKEND_INELIGIBLE_FAILURES = {
    "CAPABILITY_NOT_FOUND",
    "CLOUD_AUTH_REJECTED",
    "CLOUD_TOOL_NOT_FOUND",
    "DOCUMENT_TOOL_NOT_FOUND",
    "TOOL_NOT_FOUND",
}


class CloudRuntimeError(RuntimeError):
    """A bounded cloud failure with stable routing semantics."""

    def __init__(self, code: str, *, retryable: bool, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.detail = detail


def _classify_cli_failure(detail: str) -> CloudRuntimeError:
    server_failure = _SERVER_FAILURE.search(detail)
    if server_failure:
        code = server_failure.group(1)
        return CloudRuntimeError(
            code,
            retryable=(
                code in _RETRYABLE_SERVER_FAILURES
                or code in _CLOUD_BACKEND_INELIGIBLE_FAILURES
            ),
            detail=detail,
        )
    match = _HTTP_STATUS.search(detail)
    status = int(match.group(1)) if match else 0
    if status in {401, 403}:
        return CloudRuntimeError("CLOUD_AUTH_REJECTED", retryable=True, detail=detail)
    if status == 404:
        return CloudRuntimeError("CLOUD_TOOL_NOT_FOUND", retryable=True, detail=detail)
    if status in {408, 425, 429} or status >= 500:
        return CloudRuntimeError("CLOUD_TRANSIENT_FAILURE", retryable=True, detail=detail)
    # 云端实现的错误文本并不完全统一。无法分类的失败在 auto 模式下
    # 不应压制已经过验证的本地实现；无效输入由语义脚本在调用前拦截。
    return CloudRuntimeError("CLOUD_OPERATION_FAILED", retryable=True, detail=detail)


def cloud_runtime_configured() -> bool:
    """Return whether Desktop injected the complete Gateway credential pair."""

    return bool(
        os.environ.get("QWENWORK_BASE_URL", "").strip()
        and os.environ.get("QWENWORK_TOKEN", "").strip()
    )


def remote_runtime_required() -> bool:
    """Return whether silently changing to a local engine is forbidden."""

    return (
        os.environ.get("QODER_WORK_VM", "").strip().lower() == "true"
        or os.environ.get("QWENWORK_DOCUMENT_RUNTIME_REQUIRED", "").strip().lower()
        in {"1", "true", "yes"}
        or cloud_runtime_configured()
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
    """Resolve a healthy CLI from an override, sandbox mount, PATH, or app resources."""

    effective_platform = platform_name or sys.platform
    failures: list[str] = []
    configured = os.environ.get("QWENWORK_CLI_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        resolved: str | None = None
        if _candidate_executable(candidate, effective_platform):
            resolved = str(candidate)
        if "/" not in configured and "\\" not in configured:
            if _CLI_EXECUTABLE_NAME.fullmatch(configured):
                resolved = shutil.which(configured)
        if resolved:
            healthy, code = _qwenwork_cli_healthy(resolved)
            if healthy:
                return resolved
            failures.append(code)
        if required:
            raise CloudRuntimeError(
                failures[-1] if failures else "CLOUD_CLI_UNAVAILABLE",
                retryable=True,
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
            retryable=True,
        )
    return None


def extract_document_tool_metadata(payload: dict) -> dict:
    """Return FC metadata from the stable Runtime/CLI success envelope."""

    output = payload.get("output") if isinstance(payload, dict) else None
    if not isinstance(output, dict) or output.get("status") != "success":
        raise RuntimeError("qwenwork capability returned invalid output metadata")
    metadata = output.get("result")
    if not isinstance(metadata, dict):
        raise RuntimeError("qwenwork capability returned invalid output metadata")
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
    """Execute exactly one typed Catalog command through qwenwork CLI."""

    if not cli_path or any(_CLI_SEGMENT.fullmatch(value) is None for value in cli_path):
        raise RuntimeError("qwenwork capability path is invalid")
    if not input_path.is_file():
        raise RuntimeError("qwenwork capability input is unavailable")
    cli = resolve_qwenwork_cli(required=True)
    command = [cli, "tools", *cli_path, str(input_path.resolve())]
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["--save", str(save_path.resolve())])
    seen: set[str] = set()
    for name, value in flags:
        if _CLI_SEGMENT.fullmatch(name) is None or name in seen:
            raise RuntimeError("qwenwork capability flag is invalid")
        seen.add(name)
        command.append("--" + name)
        if value is not None:
            if not isinstance(value, str) or len(value.encode("utf-8")) > 4096 or "\x00" in value:
                raise RuntimeError("qwenwork capability flag value is invalid")
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
        raise CloudRuntimeError("CLOUD_TRANSIENT_FAILURE", retryable=True) from exc
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if len(stdout.encode("utf-8")) > _MAX_CLI_OUTPUT_BYTES or len(stderr.encode("utf-8")) > _MAX_CLI_OUTPUT_BYTES:
        raise RuntimeError("qwenwork capability response exceeds its limit")
    if result.returncode != 0:
        detail = " ".join((stderr or stdout).split())[:500]
        raise _classify_cli_failure(detail)
    try:
        payload = json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("qwenwork capability returned invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("state") != "completed":
        raise RuntimeError("qwenwork capability did not complete")
    return payload
