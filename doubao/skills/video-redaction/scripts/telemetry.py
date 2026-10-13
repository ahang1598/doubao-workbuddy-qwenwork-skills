#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

UNKNOWN_VALUE = "unknown"

CN_TEA_ENDPOINT = "https://mcs.zijieapi.com/list"
SG_TEA_ENDPOINT = "https://sgali-mcs.byteoversea.com/list"
TEA_EVENT_NAME = "cli_command_executed"
CN_PRODUCTION_APP_ID = 1045459
SG_PRODUCTION_APP_ID = 1047954
TEST_APP_ID = 1046114
REQUEST_TIMEOUT_SECONDS = 1.0
MAX_ENVELOPE_BYTES = 1024 * 1024

MAX_KEY_LENGTH = 64
MAX_SCALAR_LENGTH = 255
MAX_RECORD_LENGTH = 1024
MAX_MEMBERS = 300
MAX_COMMAND_LENGTH = 128
MAX_ACCOUNT_ID_LENGTH = 128
MAX_USER_AGENT_LENGTH = 512
MAX_NAME_LENGTH = 128
MAX_VERSION_LENGTH = 32
MAX_SKILL_ID_LENGTH = MAX_NAME_LENGTH + 1 + MAX_VERSION_LENGTH
MAX_CALLER_SEGMENTS = 2
MASKED_VALUE = "*"
MAX_DEVICE_ID_FILE_BYTES = 128
DIRECTORY_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

SAFE_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
STABLE_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CALLER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMAND_PATTERN = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
PRODUCT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MAJOR_MINOR_VERSION_PATTERN = re.compile(r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

BUILT_IN_SENSITIVE_KEY_PARTS = [
    "accountid",
    "accesskey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "passwd",
    "privatekey",
    "secret",
    "token",
]


def _code_point_length(value: str) -> int:
    return len(value)


def _truncate_code_points(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max(0, max_length - 1)]}…"


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _has_non_empty_value(env: dict[str, str], key: str) -> bool:
    value = env.get(key)
    return isinstance(value, str) and value.strip() != ""


def _has_env_key(env: dict[str, str], key: str) -> bool:
    return key in env


def _has_env_key_prefix(env: dict[str, str], prefix: str) -> bool:
    return any(key.startswith(prefix) for key in env)


def _has_non_empty_prefix(env: dict[str, str], prefix: str) -> bool:
    return any(key.startswith(prefix) and str(value).strip() != "" for key, value in env.items())


def _has_any_non_empty_value(env: dict[str, str], keys: list[str]) -> bool:
    return any(_has_non_empty_value(env, key) for key in keys)


def _has_trimmed_value_ignore_case(env: dict[str, str], key: str, expected: str) -> bool:
    value = env.get(key)
    return isinstance(value, str) and value.strip().lower() == expected.lower()


def _has_trimmed_value_containing_ignore_case(env: dict[str, str], key: str, expected: str) -> bool:
    value = env.get(key)
    return isinstance(value, str) and expected.lower() in value.strip().lower()


def _normalize_stable_name(value: str | None) -> str | None:
    if not value or len(value) > MAX_NAME_LENGTH:
        return None
    return value if STABLE_NAME_PATTERN.fullmatch(value) else None


def _normalize_ai_agent_name(value: str | None) -> str | None:
    trimmed = value.strip() if isinstance(value, str) else ""
    if not trimmed or len(trimmed) > MAX_NAME_LENGTH:
        return None
    return trimmed if CALLER_NAME_PATTERN.fullmatch(trimmed) else None


@dataclass(frozen=True)
class SkillIdentity:
    name: str | None = None
    version: str | None = None


def _is_valid_semver(value: str | None) -> bool:
    return isinstance(value, str) and len(value) <= MAX_VERSION_LENGTH and SEMVER_PATTERN.fullmatch(value) is not None


def _normalize_skill_id(value: str | None) -> SkillIdentity:
    if not value or len(value) > MAX_SKILL_ID_LENGTH:
        return SkillIdentity()
    segments = value.split("/")
    if len(segments) > 2:
        return SkillIdentity()
    name = _normalize_stable_name(segments[0])
    if not name:
        return SkillIdentity()
    version = segments[1] if len(segments) == 2 else None
    if version and (
        _is_valid_semver(version) or MAJOR_MINOR_VERSION_PATTERN.fullmatch(version)
    ):
        return SkillIdentity(name=name, version=version)
    return SkillIdentity(name=name)


def _normalize_ide_client_name(value: str | None) -> str | None:
    return _normalize_stable_name(value.strip() if isinstance(value, str) else None)


def _detect_outer_runtime(env: dict[str, str]) -> str | None:
    if _has_non_empty_prefix(env, "OPENCLAW_"):
        return "openclaw"
    if _has_non_empty_prefix(env, "ARKCLAW_") or _has_trimmed_value_containing_ignore_case(
        env, "IDENTITY_NAME", "arkclaw"
    ):
        return "arkclaw"
    if _has_non_empty_prefix(env, "HERMES_"):
        return "hermes"
    if _has_env_key(env, "COZE_CLAW_AGENT_ID"):
        return "coze-claw"
    return None


def _detect_inner_ai_client(env: dict[str, str]) -> str | None:
    if _has_trimmed_value_ignore_case(env, "AI_AGENT", "trae"):
        return "trae"
    custom = _normalize_ai_agent_name(env.get("AI_AGENT"))
    if custom:
        return custom
    if _has_env_key_prefix(env, "DOUBAO_OFFICE_"):
        return "doubao-office"
    has_claude_code = _has_any_non_empty_value(env, ["CLAUDECODE", "CLAUDE_CODE"])
    if has_claude_code and _has_non_empty_value(env, "CLAUDE_CODE_IS_COWORK"):
        return "claude-cowork"
    if has_claude_code:
        return "claude-code"
    if _has_non_empty_value(env, "VELO_ENV"):
        return "velo"
    if _has_non_empty_prefix(env, "CODEX_"):
        return "codex"
    if _has_non_empty_prefix(env, "CURSOR_"):
        return "cursor"
    if (
        _has_non_empty_prefix(env, "TRAE_")
        or _has_non_empty_value(env, "COCO_PLUGIN_ROOT")
        or _has_trimmed_value_ignore_case(env, "ICUBE_PRODUCT_BRAND_NAME", "trae")
    ):
        return "trae"
    if _has_non_empty_value(env, "GEMINI_CLI"):
        return "gemini-cli"
    if _has_any_non_empty_value(env, ["KIRO_SESSION_ID", "KIRO_AGENT_PATH"]):
        return "kiro"
    if _has_any_non_empty_value(env, ["OPENCODE", "OPENCODE_CLIENT"]):
        return "opencode"
    if _has_non_empty_value(env, "ANTIGRAVITY_AGENT"):
        return "antigravity"
    if _has_any_non_empty_value(env, ["COPILOT_CLI", "COPILOT_MODEL", "COPILOT_ALLOW_ALL"]):
        return "github-copilot"
    if _has_non_empty_value(env, "CLINE_ACTIVE"):
        return "cline"
    if _has_non_empty_value(env, "AMP_CURRENT_THREAD_ID"):
        return "amp"
    if env.get("PI_CODING_AGENT") == "true":
        return "pi"
    if _has_non_empty_value(env, "REPL_ID"):
        return "replit"
    if _has_non_empty_value(env, "AUGMENT_AGENT"):
        return "augment"
    if _has_non_empty_value(env, "QWEN_CODE"):
        return "qwen-code"
    if _has_non_empty_value(env, "COPILOT_GITHUB_TOKEN"):
        return "github-copilot"
    return None


def _resolve_ai_caller(env: dict[str, str]) -> str | None:
    segments = []
    for value in (_detect_outer_runtime(env), _detect_inner_ai_client(env)):
        if value and value not in segments:
            segments.append(value)
    if segments:
        return ",".join(segments)
    return _normalize_stable_name((env.get("IDENTITY_NAME") or "").strip())


@dataclass(frozen=True)
class InvocationContext:
    cli_name: str
    cli_version: str
    invocation_id: str
    invocation_type: str
    caller_name: str
    skill_name: str
    skill_version: str


def resolve_invocation_context(cli_name: str, cli_version: str, env: dict[str, str] | None = None) -> InvocationContext:
    env = dict(os.environ if env is None else env)
    skill = _normalize_skill_id(env.get("VE_SKILL_ID"))
    ide_client_name = _normalize_ide_client_name(env.get("IDE_CLIENT_NAME"))
    ai_caller = _resolve_ai_caller(env)
    stdin_is_tty = sys.stdin.isatty()
    stdout_is_tty = sys.stdout.isatty()

    caller_name = UNKNOWN_VALUE
    if skill.name:
        invocation_type = "skill"
        caller_name = ai_caller or UNKNOWN_VALUE
    elif ide_client_name:
        invocation_type = "ide-plugin"
        caller_name = ide_client_name
    elif ai_caller:
        invocation_type = "direct"
        caller_name = ai_caller
    elif stdin_is_tty and stdout_is_tty:
        invocation_type = "manual"
    else:
        invocation_type = "unknown"

    return InvocationContext(
        cli_name=cli_name,
        cli_version=cli_version if _is_valid_semver(cli_version) else UNKNOWN_VALUE,
        invocation_id=str(uuid.uuid4()),
        invocation_type=invocation_type,
        caller_name=caller_name,
        skill_name=skill.name or UNKNOWN_VALUE,
        skill_version=skill.version or UNKNOWN_VALUE,
    )


def _is_valid_caller_chain(value: str) -> bool:
    parts = value.split(",")
    return len(parts) <= MAX_CALLER_SEGMENTS and all(
        CALLER_NAME_PATTERN.fullmatch(part) for part in parts
    )


def _fits_user_agent_limit(value: str) -> bool:
    try:
        return len(value.encode("ascii")) <= MAX_USER_AGENT_LENGTH
    except UnicodeEncodeError:
        return False


def build_invocation_user_agent(context: InvocationContext) -> str | None:
    if (
        not PRODUCT_PATTERN.fullmatch(context.cli_name)
        or not _is_valid_semver(context.cli_version)
        or not UUID_PATTERN.fullmatch(context.invocation_id)
        or context.invocation_type not in {"skill", "direct", "ide-plugin", "manual", "unknown"}
    ):
        return None

    required_start = [
        f"{context.cli_name}/{context.cli_version}",
        f"invocation/{context.invocation_type}",
    ]
    invocation_id_token = f"invocation-id/{context.invocation_id}"
    caller_token = None
    if context.caller_name != UNKNOWN_VALUE and _is_valid_caller_chain(context.caller_name):
        caller_token = f"caller/{context.caller_name.replace(',', '+')}"
    skill_token = None
    if (
        context.skill_name != UNKNOWN_VALUE
        and _normalize_stable_name(context.skill_name)
        and (
            context.skill_version == UNKNOWN_VALUE
            or _is_valid_semver(context.skill_version)
            or MAJOR_MINOR_VERSION_PATTERN.fullmatch(context.skill_version)
        )
    ):
        skill_token = (
            f"skill/{context.skill_name}"
            if context.skill_version == UNKNOWN_VALUE
            else f"skill/{context.skill_name}#{context.skill_version}"
        )

    for candidate in (
        " ".join(required_start + ([caller_token] if caller_token else []) + ([skill_token] if skill_token else []) + [invocation_id_token]),
        " ".join(required_start + ([skill_token] if skill_token else []) + [invocation_id_token]),
        " ".join(required_start + [invocation_id_token]),
    ):
        if _fits_user_agent_limit(candidate):
            return candidate
    return None


def _canonical_sensitive_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _is_sensitive_key(key: str, configured: set[str]) -> bool:
    canonical = _canonical_sensitive_key(key)
    return canonical in configured or any(part in canonical for part in BUILT_IN_SENSITIVE_KEY_PARTS)


def _normalize_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, str):
        cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", value)
        return _truncate_code_points(cleaned, MAX_SCALAR_LENGTH)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    return None


def _normalize_value(value: Any) -> Any:
    if not isinstance(value, list):
        return _normalize_scalar(value)
    result = []
    for item in value:
        normalized = _normalize_scalar(item)
        if normalized is not None:
            result.append(normalized)
    return result or None


def _normalize_record(
    input_record: dict[str, Any] | None,
    configured_redactions: set[str],
    max_members: int,
) -> tuple[dict[str, Any], int]:
    values: dict[str, Any] = {}
    members = 0
    for key in sorted((input_record or {}).keys()):
        if _code_point_length(key) > MAX_KEY_LENGTH or SAFE_KEY_PATTERN.fullmatch(key) is None:
            continue
        raw_value = input_record.get(key)
        if raw_value is None:
            continue
        value = MASKED_VALUE if _is_sensitive_key(key, configured_redactions) else _normalize_value(raw_value)
        if value is None:
            continue
        value_members = len(value) + 1 if isinstance(value, list) else 1
        if members + value_members > max_members:
            if not isinstance(value, list):
                continue
            remaining = max(0, max_members - members - 1)
            if remaining == 0:
                continue
            values[key] = value[:remaining]
            members += remaining + 1
            continue
        values[key] = value
        members += value_members
    return values, members


def _serialize_record(values: dict[str, Any]) -> str | None:
    accepted: dict[str, Any] = {}
    for key in sorted(values.keys()):
        value = values[key]
        candidate_value = value
        candidate = _serialize_json({**accepted, key: candidate_value})
        if _code_point_length(candidate) > MAX_RECORD_LENGTH and isinstance(value, list):
            prefix = []
            for item in value:
                next_value = prefix + [item]
                candidate = _serialize_json({**accepted, key: next_value})
                if _code_point_length(candidate) > MAX_RECORD_LENGTH:
                    break
                prefix.append(item)
            if not prefix:
                continue
            candidate_value = prefix
            candidate = _serialize_json({**accepted, key: candidate_value})
        if _code_point_length(candidate) <= MAX_RECORD_LENGTH:
            accepted[key] = candidate_value
    return _serialize_json(accepted) if accepted else None


def serialize_safe_fields(
    params: dict[str, Any] | None,
    extra: dict[str, Any] | None,
    sensitive_param_names: list[str],
) -> tuple[str | None, str | None]:
    sensitive_params = {
        _canonical_sensitive_key(name) for name in sensitive_param_names if _canonical_sensitive_key(name)
    }
    normalized_params, param_members = _normalize_record(params, sensitive_params, MAX_MEMBERS)
    normalized_extra, _ = _normalize_record(
        extra,
        set(),
        max(0, MAX_MEMBERS - param_members),
    )
    return _serialize_record(normalized_params), _serialize_record(normalized_extra)


def _canonical_option_name(value: str) -> str | None:
    parts = [part for part in re.split(r"[-_]+", value) if part]
    if not parts or not re.match(r"^[A-Za-z]", parts[0]):
        return None
    key = "".join(
        f"{part[0].lower()}{part[1:]}" if index == 0 else f"{part[0].upper()}{part[1:]}"
        for index, part in enumerate(parts)
    )
    return key if SAFE_KEY_PATTERN.fullmatch(key) else None


def _add_param(params: dict[str, Any], key: str, value: Any) -> None:
    current = params.get(key)
    if current is None:
        params[key] = value
    elif isinstance(current, list):
        current.append(value)
    else:
        params[key] = [current, value]


def _last_value(value: Any) -> Any:
    return value[-1] if isinstance(value, list) else value


def _resolve_output_format(params: dict[str, Any]) -> str | None:
    json_flag = _last_value(params.get("json"))
    format_flag = _last_value(params.get("format"))
    params.pop("json", None)
    params.pop("format", None)
    if json_flag is True:
        return "json"
    if isinstance(format_flag, str):
        normalized = format_flag.strip().lower()
        if normalized in {"json", "human"}:
            return normalized
    if json_flag is False:
        return "human"
    return None


def parse_script_arguments(argv: list[str]) -> tuple[dict[str, Any] | None, str | None]:
    params: dict[str, Any] = {}
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == "--":
            break
        if not token.startswith("--") or token == "--":
            index += 1
            continue
        equals_index = token.find("=")
        raw_option = token[2:] if equals_index < 0 else token[2:equals_index]
        if equals_index < 0 and raw_option.startswith("no-") and len(raw_option) > 3:
            key = _canonical_option_name(raw_option[3:])
            if key:
                _add_param(params, key, False)
            index += 1
            continue
        key = _canonical_option_name(raw_option)
        if not key:
            index += 1
            continue
        if equals_index >= 0:
            _add_param(params, key, token[equals_index + 1 :])
            index += 1
            continue
        next_token = argv[index + 1] if index + 1 < len(argv) else None
        if next_token is not None and next_token != "--" and not next_token.startswith("--"):
            _add_param(params, key, next_token)
            index += 2
            continue
        _add_param(params, key, True)
        index += 1
    output_format = _resolve_output_format(params)
    return (params or None), output_format


def infer_script_command(entry_file: str) -> str:
    basename = Path(entry_file).name
    stem = Path(basename).stem
    normalized = re.sub(r"[^a-z0-9.-]+", "-", stem.strip().lower()).strip("-")
    return normalized or "script"


def _limit_error_message(error_message: str | None) -> str:
    raw = error_message or "Unknown error"
    return _truncate_code_points(raw, 500)


def _read_tool_version() -> str:
    try:
        pyproject = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text("utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
        if match:
            return match.group(1)
    except OSError:
        pass
    return "0.1.0"


def _normalize_device_id_directory(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if DIRECTORY_SEGMENT_PATTERN.fullmatch(normalized) else None


def _resolve_device_id_path(device_id_directory: str) -> Path | None:
    directory_name = _normalize_device_id_directory(device_id_directory)
    if not directory_name:
        return None
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / directory_name / "device-id"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / directory_name / "device-id"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = xdg if xdg and os.path.isabs(xdg) else str(Path.home() / ".config")
    return Path(base) / directory_name / "device-id"


def _read_device_id(device_id_path: Path) -> str | None:
    try:
        if not device_id_path.is_file() or device_id_path.stat().st_size > MAX_DEVICE_ID_FILE_BYTES:
            return None
        stored = device_id_path.read_text("utf-8").strip().lower()
    except OSError:
        return None
    return stored if UUID_PATTERN.fullmatch(stored) else None


def _load_or_create_device_id(device_id_directory: str) -> str | None:
    device_id_path = _resolve_device_id_path(device_id_directory)
    if device_id_path is None:
        return None
    existing = _read_device_id(device_id_path)
    if existing:
        return existing
    new_id = str(uuid.uuid4())
    try:
        device_id_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp_path = device_id_path.with_name(
            f".{device_id_path.name}.{os.getpid()}.{uuid.uuid4()}.tmp"
        )
        try:
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(fd, f"{new_id}\n".encode("utf-8"))
            finally:
                os.close(fd)
            os.link(tmp_path, device_id_path)
            return new_id
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except OSError:
        return _read_device_id(device_id_path)


class ToolTelemetry:
    def __init__(
        self,
        tool_name: str,
        tool_version: str,
        region: str = "cn",
        disabled: bool = False,
        debug: bool = False,
        sensitive_param_names: list[str] | None = None,
        device_id_directory: str | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.tool_version = tool_version
        self.region = "sg" if region == "sg" else "cn"
        self.disabled = disabled
        self.debug = debug
        self.sensitive_param_names = list(sensitive_param_names or [])
        self.device_id_directory = device_id_directory or tool_name
        self.context = resolve_invocation_context(tool_name, tool_version)
        self.account_id: str | None = None
        self.extra: dict[str, Any] = {}
        self.device_id = _load_or_create_device_id(self.device_id_directory)

    def add_extra(self, extra: dict[str, Any]) -> None:
        if self.disabled:
            return
        self.extra.update(extra)

    def set_account_id(self, account_id: str | None) -> None:
        if not isinstance(account_id, str):
            return
        normalized = account_id.strip()
        if (
            not normalized
            or len(normalized) > MAX_ACCOUNT_ID_LENGTH
            or re.search(r"[\x00-\x1f\x7f]", normalized)
        ):
            return
        self.account_id = normalized

    def get_user_agent(self) -> str | None:
        return build_invocation_user_agent(self.context)

    def _report(self, event: dict[str, Any]) -> None:
        params = {key: value for key, value in event.items() if value is not None}
        app_id = TEST_APP_ID if self.debug else (SG_PRODUCTION_APP_ID if self.region == "sg" else CN_PRODUCTION_APP_ID)
        endpoint = SG_TEA_ENDPOINT if self.region == "sg" else CN_TEA_ENDPOINT
        now_ms = int(time.time() * 1000)
        payload = [
            {
                "events": [
                    {
                        "event": TEA_EVENT_NAME,
                        "params": _serialize_json(params),
                        "local_time_ms": now_ms,
                    }
                ],
                "user": {"user_unique_id": str(uuid.uuid4())},
                "local_time": now_ms // 1000,
                "header": {"app_id": app_id},
                "verbose": 1,
            }
        ]
        body = _serialize_json(payload).encode("utf-8")
        if len(body) > MAX_ENVELOPE_BYTES:
            return
        req = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS):
                pass
        except Exception:
            pass

    def report_script_completion(
        self,
        *,
        command: str,
        argv: list[str],
        result: str,
        duration_ms: int,
        error_message: str | None = None,
    ) -> None:
        if self.disabled:
            return
        if len(command) > MAX_COMMAND_LENGTH or COMMAND_PATTERN.fullmatch(command) is None:
            return
        params, output_format = parse_script_arguments(argv)
        safe_params, safe_extra = serialize_safe_fields(params, self.extra, self.sensitive_param_names)
        event = {
            "cli_name": self.context.cli_name,
            "cli_version": self.context.cli_version,
            "invocation_id": self.context.invocation_id,
            "device_id": self.device_id,
            "command": command,
            "params": safe_params,
            "result": result,
            "error_message": _limit_error_message(error_message) if result == "failure" else None,
            "duration_ms": max(0, duration_ms),
            "output_format": output_format,
            "python_major": platform.python_version_tuple()[0],
            "os": sys.platform,
            "arch": platform.machine(),
            "interaction_mode": "interactive" if sys.stdin.isatty() and sys.stdout.isatty() else "non-interactive",
            "invocation_type": self.context.invocation_type,
            "caller_name": None if self.context.caller_name == UNKNOWN_VALUE else self.context.caller_name,
            "skill_name": None if self.context.skill_name == UNKNOWN_VALUE else self.context.skill_name,
            "skill_version": None if self.context.skill_version == UNKNOWN_VALUE else self.context.skill_version,
            "account_id": self.account_id,
            "extra": safe_extra,
        }
        self._report(event)


def create_default_telemetry() -> ToolTelemetry:
    return ToolTelemetry(
        tool_name="byte-mediakit-video-redaction",
        tool_version=os.environ.get("VIDEO_REDACTION_TELEMETRY_VERSION", _read_tool_version()),
        region=os.environ.get("VIDEO_REDACTION_TELEMETRY_REGION", "cn"),
        disabled=os.environ.get("VIDEO_REDACTION_TELEMETRY_DISABLED") == "1",
        debug=os.environ.get("VIDEO_REDACTION_TELEMETRY_DEBUG") == "1",
        sensitive_param_names=[
            "input",
            "output",
            "audioFile",
            "videoUrl",
            "videoUrls",
            "stateFile",
        ],
        device_id_directory="velo-cli",
    )
