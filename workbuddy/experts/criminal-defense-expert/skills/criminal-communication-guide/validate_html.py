#!/usr/bin/env python3
"""Validate a case-local HTML artifact and unresolved template controls."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag.lower())

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _inside(root: Path, path: Path) -> bool:
    return path == root or root in path.parents


def _blocked(path: Path, code: str, message: str) -> dict:
    return {
        "outcome": "BLOCKED",
        "document_path": str(path),
        "readable": False,
        "issues": [{"code": code, "message": message}],
        "warnings": [],
        "retryable": True,
    }


def validate_html(
    *,
    document_path: str | Path,
    matter_root: str | Path,
    doc_type: str = "",
    template_id: str = "",
    output_scene: str = "family_communication",
) -> dict:
    matter = _resolved(matter_root)
    path = _resolved(document_path)
    if not matter.is_dir() or not _inside(matter, path):
        return _blocked(path, "cross_matter_path", "HTML路径不属于当前案件")
    if not path.is_file():
        return _blocked(path, "file_missing", "HTML不存在")
    if path.suffix.lower() not in {".html", ".htm"}:
        return _blocked(path, "wrong_file_type", "文件不是HTML")
    try:
        html = path.read_text(encoding="utf-8")
        parser = StructureParser()
        parser.feed(html)
    except (OSError, UnicodeError, ValueError) as error:
        return _blocked(path, "file_unreadable", f"HTML无法解析: {error}")
    if "html" not in parser.tags or "body" not in parser.tags:
        return _blocked(path, "invalid_structure", "HTML缺少html或body结构")
    visible_text = "".join(parser.text)
    if len(re.sub(r"\s+", "", visible_text)) < 20:
        return _blocked(path, "empty_document", "HTML缺少实质可见内容")

    unresolved = re.findall(r"<!--\s*(?:CONTENT|MERMAID)_SLOT:[^>]+-->|\{\{[A-Za-z0-9_.-]+\}\}", html)
    warnings: list[dict] = []
    if unresolved:
        warnings.append({"code": "unresolved_placeholder", "message": f"HTML仍有{len(unresolved)}个模板占位"})
    internal_markers = ["resumeSubSessionId", "preloadedContexts", "submission_ready", "[INTERNAL"]
    found = [marker for marker in internal_markers if marker in visible_text]
    if found:
        return _blocked(path, "internal_marker", f"HTML含内部控制标记: {', '.join(found)}")
    if not template_id:
        warnings.append({"code": "missing_template_receipt", "message": "缺少模板ID回执"})
    return {
        "outcome": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "document_path": str(path),
        "readable": True,
        "doc_type": doc_type,
        "template_id": template_id,
        "output_scene": output_scene,
        "warnings": warnings,
        "retryable": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查刑事家属或沟通HTML")
    parser.add_argument("--document", required=True)
    parser.add_argument("--matter-root", required=True)
    parser.add_argument("--doc-type", default="")
    parser.add_argument("--template-id", default="")
    parser.add_argument("--output-scene", default="family_communication")
    args = parser.parse_args(argv)
    result = validate_html(
        document_path=args.document,
        matter_root=args.matter_root,
        doc_type=args.doc_type,
        template_id=args.template_id,
        output_scene=args.output_scene,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["outcome"] in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

