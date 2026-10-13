#!/usr/bin/env python3
"""Redact sensitive values before emitting structured or text output."""

from __future__ import annotations

import re
from typing import Any


PATTERNS = (
    (re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[REDACTED_PHONE]"),
    (
        re.compile(r"(?i)(?:学号|student[ _-]?id)\s*[:：=]\s*[A-Z0-9_-]{5,32}"),
        "学号：[REDACTED_STUDENT_ID]",
    ),
    (
        re.compile(r"(?:姓名|联系人|申请人)\s*[:：=]\s*[\u4e00-\u9fff·]{2,16}"),
        "姓名：[REDACTED_NAME]",
    ),
    (
        re.compile(
            r"(?i)(?:api[ _-]?key|token|access[ _-]?token|secret|password|密码|验证码|支付口令)"
            r"\s*[:：=]\s*[^\s,;，；}\]]+"
        ),
        "credential=[REDACTED_CREDENTIAL]",
    ),
    (
        re.compile(r"(?<![\w.])(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?![\w.])"),
        "[REDACTED_PRIVATE_IP]",
    ),
    (
        re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+(?:internal|intranet|corp|lan|local)\b"),
        "[REDACTED_INTERNAL_DOMAIN]",
    ),
    (
        re.compile(r"(?:/Users|/home)/[^\s<>]+|[A-Za-z]:\\Users\\[^\s<>]+"),
        "[REDACTED_HOME_PATH]",
    ),
    (
        re.compile(r"(?:/private|/var/folders|/srv/internal)/[^\s<>]+"),
        "[REDACTED_PRIVATE_PATH]",
    ),
)


def redact_text(value: str) -> str:
    result = value
    for pattern, replacement in PATTERNS:
        result = pattern.sub(replacement, result)
    return result.replace("\x00", "[REDACTED_NUL]")


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize(item) for item in value)
    if isinstance(value, dict):
        return {redact_text(str(key)): sanitize(item) for key, item in value.items()}
    return value
