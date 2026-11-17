#!/usr/bin/env python3
"""Look up Canvas command and XML documentation."""

import argparse
import io
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = ROOT / "references" / "protocol"
MANIFEST = PROTOCOL_ROOT / "manifest.json"
SPLIT_RE = re.compile(r"[\s,]+")


class ProtocolLookupError(ValueError):
    """Raised when a requested keyword cannot be resolved safely."""


def load_manifest() -> "tuple[list[dict[str, object]], dict[str, dict[str, object]]]":
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProtocolLookupError("manifest root must be an object")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ProtocolLookupError("manifest entries must be a list")

    by_keyword: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ProtocolLookupError("manifest contains an invalid entry")
        for field in ("keyword", "function", "file"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ProtocolLookupError(
                    f"manifest entry has invalid {field}: {entry.get('keyword')}"
                )
        dependencies = entry.get("depends_on")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) and item for item in dependencies
        ):
            raise ProtocolLookupError(
                f"invalid dependencies for {entry.get('keyword')}"
            )
        keyword = str(entry["keyword"])
        if keyword in by_keyword:
            raise ProtocolLookupError(f"duplicate keyword in manifest: {keyword}")
        by_keyword[keyword] = entry

    for keyword, entry in by_keyword.items():
        for dependency in entry["depends_on"]:
            if dependency not in by_keyword:
                raise ProtocolLookupError(
                    f"unknown dependency for {keyword}: {dependency}"
                )
        source_path(entry)
    return entries, by_keyword


def parse_keywords(values: "list[str]", keywords_file: "str | None") -> "list[str]":
    chunks = list(values)
    if keywords_file:
        if keywords_file == "-":
            text = sys.stdin.read()
            chunks.append(text[1:] if text.startswith("\ufeff") else text)
        else:
            chunks.append(Path(keywords_file).read_text(encoding="utf-8-sig"))

    return list(dict.fromkeys(
        keyword
        for chunk in chunks
        for keyword in SPLIT_RE.split(chunk.strip())
        if keyword
    ))


def resolve_keywords(
    requested: "list[str]",
    by_keyword: "dict[str, dict[str, object]]",
) -> "list[str]":
    unknown = [keyword for keyword in requested if keyword not in by_keyword]
    if unknown:
        raise ProtocolLookupError(
            "unknown protocol keyword(s): " + ", ".join(unknown)
            + "\nUse --list to show supported keywords."
        )
    return list(dict.fromkeys(requested))


def source_path(entry: "dict[str, object]") -> "Path":
    relative = entry["file"]
    path = (PROTOCOL_ROOT / relative).resolve()
    try:
        path.relative_to(PROTOCOL_ROOT.resolve())
    except ValueError as exc:
        raise ProtocolLookupError(f"unsafe protocol path: {relative}") from exc
    if not path.is_file():
        raise ProtocolLookupError(f"protocol file not found: {relative}")
    return path


def render_markdown(
    resolved: "list[str]",
    by_keyword: "dict[str, dict[str, object]]",
) -> "str":
    lines = [
        "===== 协议包开始 =====",
        "",
        "# Canvas 说明",
        "",
        "、".join(f"`{keyword}`" for keyword in resolved),
    ]
    for keyword in resolved:
        entry = by_keyword[keyword]
        path = source_path(entry)
        lines.extend(
            [
                "",
                "---",
                "",
                f"<!-- protocol-keyword: {keyword}; source: {entry['file']} -->",
                path.read_text(encoding="utf-8").rstrip(),
            ]
        )
    lines.extend(["", "===== 协议包结束 ====="])
    return "\n".join(lines) + "\n"


def build_parser() -> "argparse.ArgumentParser":
    parser = argparse.ArgumentParser(description="查 Canvas 命令和 XML 写法。")
    parser.add_argument("keywords", nargs="*", help="命令名或 XML 关键词，例如 str_replace xml:p")
    parser.add_argument("--keywords-file", metavar="PATH|-", help="从 UTF-8 文件或标准输入读关键词")
    parser.add_argument("--list", action="store_true", help="列出所有关键词")
    parser.add_argument("--output", metavar="PATH", help="将结果保存到 UTF-8 文件")
    return parser


def main(argv: "list[str] | None" = None) -> "int":
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors=stream.errors)
        elif isinstance(stream, io.TextIOWrapper) and stream.encoding.lower() != "utf-8":
            stream.flush()
            setattr(sys, name, io.TextIOWrapper(
                stream.detach(), encoding="utf-8", errors=stream.errors,
                line_buffering=stream.line_buffering,
            ))
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        entries, by_keyword = load_manifest()
        if args.list:
            if args.keywords or args.keywords_file:
                parser.error("--list cannot be combined with keyword input")
            output = "\n".join(
                f"{entry['keyword']}\t{entry['function']}" for entry in entries
            ) + "\n"
        else:
            requested = parse_keywords(args.keywords, args.keywords_file)
            if not requested:
                parser.error("provide at least one keyword or use --list")
            resolved = resolve_keywords(requested, by_keyword)
            output = render_markdown(resolved, by_keyword)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (OSError, json.JSONDecodeError, ProtocolLookupError) as exc:
        print(f"protocol lookup failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
