#!/usr/bin/env python3
"""Heuristic checker for fetched Feishu/Lark Doc content.

Save fetched document content as text, Markdown, or XML, then run:
    python scripts/check_lark_doc.py --doc-file .workflow/fetched_doc.xml --doc-url <url> --write-handoff .workflow/doc_handoff.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PLACEHOLDERS = ("图片待插入", "稍后补图", "这里放图", "待补充", "TODO", "占位")
BANNED_INTERNAL = ("内部质量门禁", "一票否决项", "自检清单", "检查清单", "workflow.py", "validate_run.py")
REQUIRED_ONE_OF = ("可复制正文", "可复制方案")
IMAGE_OR_MEDIA_MARKERS = ("<image", "<img", "image_token", "file_token", "media", "![", "![](", "image:", "图片 token")


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "\n", text)


def has_image_or_media(raw: str) -> bool:
    lowered = raw.lower()
    return any(token.lower() in lowered for token in IMAGE_OR_MEDIA_MARKERS)


def validate_doc(raw: str) -> tuple[dict[str, Any], list[str]]:
    plain = strip_tags(raw)
    failures: list[str] = []
    has_image = has_image_or_media(raw)
    has_core = any(section in plain for section in REQUIRED_ONE_OF)
    has_placeholder = any(token in plain for token in PLACEHOLDERS)
    has_internal = any(token in plain for token in BANNED_INTERNAL)
    if not has_core:
        failures.append("document missing 可复制正文 or 可复制方案 section")
    if not has_image:
        failures.append("document missing actual image/media block")
    if has_placeholder:
        failures.append("document contains unfinished placeholder text")
    if has_internal:
        failures.append("document exposes internal workflow/check text")
    if "可复制使用版" in plain:
        failures.append("document contains banned section 可复制使用版")
    if "核心设定与人物关系" in plain:
        failures.append("document contains banned section 核心设定与人物关系")
    result = {
        "core_section_checked": "pass" if has_core else "fail",
        "image_in_doc": "yes" if has_image else "no",
        "placeholder_removed": "yes" if not has_placeholder else "no",
        "internal_checks_hidden": "yes" if not has_internal else "no",
    }
    return result, failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check fetched Doubao Novel Writing Feishu document")
    parser.add_argument("--doc-file", required=True)
    parser.add_argument("--doc-id", default="")
    parser.add_argument("--doc-url", required=True)
    parser.add_argument("--doc-title", default="")
    parser.add_argument("--write-handoff")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raw = Path(args.doc_file).read_text(encoding="utf-8-sig")
    result, failures = validate_doc(raw)
    payload: dict[str, Any] = {"status": "pass" if not failures else "fail", "failures": failures, "result": result}
    if args.write_handoff:
        handoff = {
            "doc_created": "yes",
            "doc_id": args.doc_id,
            "doc_url": args.doc_url,
            "doc_title": args.doc_title,
            "fetched_back": "pass" if not failures else "fail",
            "image_in_doc": result["image_in_doc"],
            "ready_for_final": "yes" if not failures else "no",
            "chat_fulltext_output": "no",
            **result,
        }
        out = Path(args.write_handoff)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["handoff"] = str(out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
