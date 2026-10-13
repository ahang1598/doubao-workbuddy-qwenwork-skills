#!/usr/bin/env python3
"""Mandatory Feishu document output check.

The writing skill should call a real Feishu/Lark document tool first, then save
its returned result as JSON and run this script before declaring completion.

Usage:
    python3 scripts/require_feishu_output.py output/feishu-output.json

Expected JSON example:
{
  "title": "文章标题",
  "document_url": "https://example.feishu.cn/docx/xxxxxxxxxxxxxxxx",
  "content_written": true
}

Exit code 0 = valid Feishu document delivery.
Any non-zero exit code = delivery is incomplete and MUST NOT be reported as done.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

FEISHU_DOC_RE = re.compile(
    r"^https://[A-Za-z0-9.-]+\.(?:feishu\.cn|larksuite\.com)/(?:docx|docs)/[A-Za-z0-9_-]{8,}(?:[/?#].*)?$",
    re.IGNORECASE,
)


def fail(message: str) -> int:
    print(f"FEISHU_OUTPUT_CHECK=FAIL: {message}", file=sys.stderr)
    return 2


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"result file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def validate(data: dict[str, Any]) -> None:
    title = data.get("title")
    url = data.get("document_url")
    content_written = data.get("content_written")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing title")
    if not isinstance(url, str) or not FEISHU_DOC_RE.match(url.strip()):
        raise ValueError("missing or invalid Feishu/Lark document_url")
    if content_written is not True:
        raise ValueError("content_written must be true; empty documents do not count")


def main() -> int:
    if len(sys.argv) != 2:
        return fail("usage: require_feishu_output.py <feishu-output.json>")

    try:
        data = load_json(Path(sys.argv[1]))
        validate(data)
    except ValueError as exc:
        return fail(str(exc))

    print(f"FEISHU_OUTPUT_CHECK=PASS: {data['document_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
