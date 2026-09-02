"""Emoji-to-text sanitisation shared by the DOCX writers.

DOCX deliverables must not contain emoji (WPS compatibility, D3-S2).
Model-authored content (report.json sections, operation comments) may carry
the workflow's status markers; map the known ones to bracket labels per the
skill's format baseline and strip anything else in the emoji ranges.

Contract text (old_text/new_text) is never passed through here — original
wording must not be silently altered.
"""

from __future__ import annotations

import re

EMOJI_MAP = {
    "🔴": "【高风险】",
    "🟡": "【中风险】",
    "🟢": "【低风险】",
    "✅": "【符合】",
    "❌": "【缺失】",
    "⚠️": "【关注】",
    "⚠": "【关注】",
    "🔄": "【反转】",
}

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "☀-➿"
    "⬀-⯿"
    "️"
    "]"
)


def sanitize_text(text: str) -> str:
    if not text:
        return text
    for emoji, label in EMOJI_MAP.items():
        text = text.replace(emoji, label)
    return _EMOJI_RE.sub("", text)


def sanitize_data(value):
    """Recursively sanitise every string in a JSON-like structure."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_data(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_data(item) for key, item in value.items()}
    return value
