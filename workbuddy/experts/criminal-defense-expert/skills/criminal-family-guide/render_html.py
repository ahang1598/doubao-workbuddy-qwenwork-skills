#!/usr/bin/env python3
"""Render an existing HTML template into a case-local HTML artifact."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


class HtmlRenderError(ValueError):
    """Raised when HTML rendering cannot safely continue."""


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _inside(root: Path, path: Path) -> bool:
    return path == root or root in path.parents


def _load_data(data_json: str | None, data_file: str | None) -> dict[str, object]:
    if data_json and data_file:
        raise HtmlRenderError("data-json和data-file只能选择一个")
    if data_file:
        value = json.loads(_resolved(data_file).read_text(encoding="utf-8"))
    elif data_json:
        value = json.loads(data_json)
    else:
        value = {}
    if not isinstance(value, dict):
        raise HtmlRenderError("填充数据必须是JSON对象")
    return value


def render_html(
    *,
    skill_root: str | Path,
    matter_root: str | Path,
    template_path: str | Path,
    output_path: str | Path,
    data_json: str | None = None,
    data_file: str | None = None,
    doc_type: str = "",
) -> dict:
    skill = _resolved(skill_root)
    matter = _resolved(matter_root)
    template = _resolved(template_path)
    output = _resolved(output_path)
    allowed_roots = [skill / "templates", skill / "assets"]
    if not any(_inside(root, template) for root in allowed_roots) or not template.is_file():
        raise HtmlRenderError("模板必须是当前Skill templates或assets目录中的现有文件")
    if not matter.is_dir() or not _inside(matter, output):
        raise HtmlRenderError("输出路径必须属于当前案件目录")
    data = _load_data(data_json, data_file)
    html = template.read_text(encoding="utf-8")
    for key, value in data.items():
        replacement = str(value)
        html = html.replace("{{" + key + "}}", replacement)
        html = re.sub(rf"<!--\s*CONTENT_SLOT:{re.escape(key)}\s*-->", lambda _: replacement, html)
        html = re.sub(rf"<!--\s*MERMAID_SLOT:{re.escape(key)}\s*-->", lambda _: replacement, html)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    template_root = next(root for root in allowed_roots if _inside(root, template))
    return {
        "outcome": "PASS",
        "document_path": str(output),
        "template_id": str(template.relative_to(template_root)),
        "doc_type": doc_type,
        "output_format": "html",
        "rendered": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="渲染刑事家属或沟通HTML")
    parser.add_argument("--skill-root", default=str(Path(__file__).parents[1]))
    parser.add_argument("--matter-root", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    data = parser.add_mutually_exclusive_group()
    data.add_argument("--data-json")
    data.add_argument("--data-file")
    parser.add_argument("--doc-type", default="")
    args = parser.parse_args(argv)
    try:
        result = render_html(
            skill_root=args.skill_root,
            matter_root=args.matter_root,
            template_path=args.template,
            output_path=args.output,
            data_json=args.data_json,
            data_file=args.data_file,
            doc_type=args.doc_type,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result = {"outcome": "BLOCKED", "rendered": False, "reason": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["outcome"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

