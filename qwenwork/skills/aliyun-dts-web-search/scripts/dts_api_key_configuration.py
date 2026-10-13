#!/usr/bin/env python3
"""Shared helpers for DTS_AI_API_KEY lookup and browser-based setup.

Each DTS-AI Skill includes an identical copy in its scripts/ directory so that
the Skill remains independently installable. Keep the copies identical;
tests/test_dts_api_key_configuration.py verifies this requirement.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import dts_api_key_browser_ui as browser_ui  # noqa: E402

ENV_VAR = "DTS_AI_API_KEY"
SCHEMA_VERSION = 1
SERVICE = "aliyun-dts-ai"
CREDENTIAL_FILE_MAX_BYTES = 16 * 1024
CREDENTIAL_KEYS = frozenset({"schema_version", "service", "api_key"})
SUPPORTED_LANGUAGES = browser_ui.SUPPORTED_LANGUAGES


class CredentialError(RuntimeError):
    """A local credential configuration failure that exposes no secret."""


class SetupError(CredentialError):
    """A local validation failure during interactive setup."""


def credential_directory() -> Path:
    """Return the shared DTS-AI credential directory."""
    return Path.home() / ".aliyun-dts" / "dts-ai"


def credential_file() -> Path:
    """Return the shared DTS-AI API-key JSON file."""
    return credential_directory() / "credentials.json"


def _owned_by_current_user(metadata: os.stat_result) -> bool:
    getuid = getattr(os, "getuid", None)
    return getuid is None or metadata.st_uid == getuid()


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag)


def _is_unsafe_link(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or _is_reparse_point(metadata)


def _require_private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise CredentialError(f"Credential directory is missing: {path}") from exc
    if _is_unsafe_link(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise CredentialError(f"Credential directory is not a regular directory: {path}")
    if not _owned_by_current_user(metadata):
        raise CredentialError(f"Credential directory is not owned by the current user: {path}")


def _ensure_private_directories() -> Path:
    root = Path.home() / ".aliyun-dts"
    child = root / "dts-ai"
    for path in (root, child):
        if path.exists() or path.is_symlink():
            metadata = path.lstat()
            if _is_unsafe_link(metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise SetupError(f"Credential directory is not a regular directory: {path}")
            if not _owned_by_current_user(metadata):
                raise SetupError(
                    f"Credential directory is not owned by the current user: {path}"
                )
        else:
            path.mkdir()
    return child


def _validate_api_key(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise CredentialError("DTS-AI API key must be a non-empty string")
    if value != value.strip():
        raise CredentialError("DTS-AI API key must not have surrounding whitespace")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise CredentialError("DTS-AI API key contains a control character")
    return value


def _encode_api_key(value: Any) -> str:
    api_key = _validate_api_key(value)
    return base64.b64encode(api_key.encode("utf-8")).decode("ascii")


def _decode_api_key(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise CredentialError("Credential file API key value is invalid")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CredentialError("Credential file API key value is invalid") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise CredentialError("Credential file API key value is invalid")
    try:
        api_key = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CredentialError("Credential file API key value is invalid") from exc
    return _validate_api_key(api_key)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CredentialError("Credential file contains a duplicate field")
        value[key] = item
    return value


def _decode_credentials(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CredentialError("Credential file must be UTF-8 without a BOM")
    try:
        text = raw.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
    except UnicodeDecodeError as exc:
        raise CredentialError("Credential file must be valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise CredentialError("Credential file must contain valid JSON") from exc
    if not isinstance(value, dict):
        raise CredentialError("Credential file JSON root must be an object")
    if set(value) != CREDENTIAL_KEYS:
        raise CredentialError(
            "Credential file fields must be schema_version, service, and api_key"
        )
    if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
        raise CredentialError("Credential file schema_version is unsupported")
    if value["service"] != SERVICE:
        raise CredentialError("Credential file service must be aliyun-dts-ai")
    return _decode_api_key(value["api_key"])


def load_api_key_file() -> str:
    """Load the API key from credentials.json, or return empty if absent."""
    path = credential_file()
    if not path.exists() and not path.is_symlink():
        return ""

    _require_private_directory(path.parent.parent)
    _require_private_directory(path.parent)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return ""
    if _is_unsafe_link(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise CredentialError(f"Credential file is not a regular file: {path}")
    if not _owned_by_current_user(metadata):
        raise CredentialError(f"Credential file is not owned by the current user: {path}")
    if metadata.st_size > CREDENTIAL_FILE_MAX_BYTES:
        raise CredentialError("Credential file exceeds the 16 KiB size limit")

    flags = os.O_RDONLY
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if no_follow:
        flags |= no_follow
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CredentialError(f"Credential file could not be opened safely: {path}") from exc
    try:
        opened_metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened_metadata.st_mode)
            or _is_reparse_point(opened_metadata)
            or not _owned_by_current_user(opened_metadata)
            or opened_metadata.st_dev != metadata.st_dev
            or opened_metadata.st_ino != metadata.st_ino
        ):
            raise CredentialError(f"Credential file changed while opening: {path}")
        chunks: list[bytes] = []
        remaining = CREDENTIAL_FILE_MAX_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(raw) > CREDENTIAL_FILE_MAX_BYTES:
        raise CredentialError("Credential file exceeds the 16 KiB size limit")
    return _decode_credentials(raw)


def _write_api_key_file(api_key: str) -> Path:
    directory = _ensure_private_directories()
    path = directory / "credentials.json"
    if path.exists() or path.is_symlink():
        metadata = path.lstat()
        if _is_unsafe_link(metadata) or not stat.S_ISREG(metadata.st_mode):
            raise SetupError(f"Credential file is not a regular file: {path}")
        if not _owned_by_current_user(metadata):
            raise SetupError(f"Credential file is not owned by the current user: {path}")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "service": SERVICE,
        "api_key": _encode_api_key(api_key),
    }
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(encoded) > CREDENTIAL_FILE_MAX_BYTES:
        raise SetupError("Credential file would exceed the 16 KiB size limit")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".credentials.", suffix=".tmp", dir=directory
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise SetupError(f"Credential file could not be written safely: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return path


def resolve_api_key() -> str:
    """Read DTS_AI_API_KEY from the current process, then credentials.json."""
    api_key = os.environ.get(ENV_VAR, "")
    if api_key:
        return _validate_api_key(api_key)
    return load_api_key_file()


def run_setup(*, language: str = "en") -> None:
    """Open the local browser interface and save the key to credentials.json."""
    existing = resolve_api_key()
    commit_error: list[str] = []

    def commit(api_key: str) -> bool:
        try:
            _write_api_key_file(api_key)
        except CredentialError as exc:
            commit_error.append(str(exc))
            return False
        return True

    def ready() -> None:
        if language == "zh-CN":
            print("系统浏览器已打开。请在 5 分钟内完成本地 API Key 配置。")
        else:
            print(
                "System browser opened. Complete the local API Key setup "
                "within 5 minutes."
            )

    try:
        browser_ui.run_browser_api_key_ui(
            commit,
            existing_configured=bool(existing),
            on_ready=ready,
            language=language,
        )
    except browser_ui.BrowserApiKeyUIError as exc:
        if exc.code == "UNAVAILABLE" and commit_error:
            raise SetupError(commit_error[-1]) from exc
        messages = {
            "OPEN_FAILED": (
                "OPEN_FAILED: the system browser could not be opened; "
                "no terminal secret-input fallback was used"
            ),
            "TIMEOUT": "TIMEOUT: the local browser setup was not completed within 5 minutes",
            "CANCELLED": "CANCELLED: no API Key was saved",
            "UNAVAILABLE": "UNAVAILABLE: the local browser setup could not be started",
            "INVALID_INPUT": "INVALID_INPUT: unsupported local browser setup parameters",
        }
        raise SetupError(messages.get(exc.code, "UNAVAILABLE")) from exc

    if language == "zh-CN":
        print("配置完成。")
    else:
        print("Configuration complete.")
