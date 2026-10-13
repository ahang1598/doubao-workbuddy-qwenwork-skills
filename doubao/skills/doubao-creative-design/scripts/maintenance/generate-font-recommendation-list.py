#!/usr/bin/env python3
"""Generate the human font recommendation table from the curated JSON source."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


ROOT = Path(__file__).resolve().parents[2]
POOL_PATH = ROOT / "assets/fonts/font-curated-pool.json"
VALID_STATUSES = {"editorial_candidate", "registered_unclassified"}
VALID_ROLES = ("hero", "sub", "body", "meta")
LANGUAGE_ORDER = ("zh", "en", "ko", "ja")


def normalize(value: object) -> str:
    return "".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def cell(value: object) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = html.escape(text, quote=False)
    text = text.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")
    return text.replace("\n", "<br>")


def ordered(values: list[str], preferred: tuple[str, ...]) -> list[str]:
    priority = {value: index for index, value in enumerate(preferred)}
    return sorted(set(values), key=lambda value: (priority.get(value, len(priority)), value))


def validate(pool: dict) -> tuple[dict, list[dict]]:
    view = pool.get("recommendation_view")
    if not isinstance(view, dict) or view.get("schema_version") != 1:
        raise ValueError("recommendation_view.schema_version must be 1")
    if view.get("source_collection") != "fonts":
        raise ValueError("recommendation_view.source_collection must be fonts")
    if view.get("row_quota") is not None:
        raise ValueError("recommendation_view.row_quota must remain null")
    markers = view.get("generated_markers")
    if not isinstance(markers, list) or len(markers) != 2 or any(not isinstance(item, str) for item in markers):
        raise ValueError("recommendation_view.generated_markers must contain two strings")
    fonts = pool.get("fonts")
    if not isinstance(fonts, list):
        raise ValueError("fonts must be a list")
    seen: set[str] = set()
    for index, font in enumerate(fonts):
        if not isinstance(font, dict):
            raise ValueError(f"fonts[{index}] must be an object")
        key = font.get("key")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", key):
            raise ValueError(f"fonts[{index}].key is not a stable ASCII key")
        if key in seen:
            raise ValueError(f"duplicate font key: {key}")
        seen.add(key)
        status = font.get("recommendation_status")
        if status not in VALID_STATUSES:
            raise ValueError(f"{key}.recommendation_status is invalid: {status}")
        for field in ("display_name", "shape", "design_note"):
            if not isinstance(font.get(field), str) or not font[field].strip():
                raise ValueError(f"{key}.{field} must be a non-empty string")
        for field in ("recommendation_languages", "roles", "tags"):
            if not isinstance(font.get(field), list) or any(not isinstance(item, str) for item in font[field]):
                raise ValueError(f"{key}.{field} must be a string list")
        if status == "editorial_candidate":
            if not font["recommendation_languages"] or not font["roles"]:
                raise ValueError(f"{key} editorial candidate needs language and role")
            unknown_roles = set(font["roles"]) - set(VALID_ROLES)
            if unknown_roles:
                raise ValueError(f"{key} has unknown roles: {sorted(unknown_roles)}")
    return view, fonts


def generate(pool: dict) -> str:
    view, fonts = validate(pool)
    statuses = view.get("include_statuses")
    if statuses != ["editorial_candidate"]:
        raise ValueError("recommendation_view.include_statuses must be editorial_candidate only")
    blocked = {normalize(value) for value in pool.get("blocked_names", [])}
    rows = []
    for font in fonts:
        if font["recommendation_status"] not in statuses:
            continue
        identities = [
            font["key"],
            font["display_name"],
            font.get("catalog_id") or "",
            *font.get("aliases", []),
            *font.get("platform_families", []),
        ]
        if view.get("exclude_blocked_names") and blocked.intersection(normalize(value) for value in identities):
            continue
        languages = ordered(font["recommendation_languages"], LANGUAGE_ORDER)
        roles = ordered(font["roles"], VALID_ROLES)
        tags = sorted(set(font.get("tags", [])))
        rows.append((font["key"], font, languages, roles, tags))
    rows.sort(key=lambda item: item[0])

    lines = [
        f"<!-- generated-count: {len(rows)} -->",
        "| font_key | 推荐字体 | 语言 | 角色 | 形态 | 气质标签 | 设计说明 |",
        "|---|---|---|---|---|---|---|",
    ]
    for key, font, languages, roles, tags in rows:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                cell(key),
                cell(font["display_name"]),
                cell(" / ".join(languages)),
                cell(" / ".join(roles)),
                cell(font["shape"]),
                cell(" / ".join(tags) if tags else "—"),
                cell(font["design_note"]),
            )
        )
    return "\n".join(lines) + "\n"


def replace_generated(document: str, begin: str, end: str, generated: str) -> str:
    if document.count(begin) != 1 or document.count(end) != 1:
        raise ValueError("generated markers must each appear exactly once")
    before, rest = document.split(begin, 1)
    current, after = rest.split(end, 1)
    if begin in current or end in current:
        raise ValueError("generated markers cannot be nested")
    return before + begin + "\n" + generated + end + after


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when the generated region is stale")
    args = parser.parse_args()
    try:
        pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
        view, _ = validate(pool)
        document_path = ROOT / view["generated_document"]
        document = document_path.read_text(encoding="utf-8")
        begin, end = view["generated_markers"]
        expected = replace_generated(document, begin, end, generate(pool))
        if expected == document:
            return 0
        if args.check:
            print(f"stale generated font recommendation table: {document_path}", file=sys.stderr)
            return 1
        atomic_write(document_path, expected)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"font recommendation generation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
