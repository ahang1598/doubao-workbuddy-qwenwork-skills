#!/usr/bin/env python3
"""Markdown → DOCX 标准转换流程。

流程：pandoc（律师规范模板 + Lua 过滤器）→ doc_styler.py 样式规范化 → 交付前自检。

用法：
    python md2docx.py input.md                        # 默认 word-report profile
    python md2docx.py input.md -o output.docx         # 指定输出路径
    python md2docx.py input.md --profile none         # 跳过样式化（仅 pandoc）
    python md2docx.py input.md --doc-name "报告标题"   # 自定义页脚名称
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REFERENCE = SCRIPT_DIR / "template.docx"
DEFAULT_FILTER = SCRIPT_DIR / "markdown-to-docx.lua"


def resolve_resource(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    for candidate in (path, SCRIPT_DIR / path_text):
        if candidate.exists():
            return candidate
    return path


def run_pandoc(input_path: Path, output_path: Path, reference: Path, lua_filter: Path) -> None:
    cmd = [
        "pandoc",
        str(input_path),
        "--reference-doc", str(reference),
        "--lua-filter", str(lua_filter),
        "-o", str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("Pandoc 未找到，请安装或加入 PATH。", file=sys.stderr)
        raise SystemExit(127)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)


def apply_style(output_path: Path, profile: str, doc_name: str) -> list[str]:
    sys.path.insert(0, str(SCRIPT_DIR))
    from docx import Document
    from doc_styler import apply_doc_style

    doc = Document(str(output_path))
    violations = apply_doc_style(doc, profile=profile, doc_name=doc_name)
    doc.save(str(output_path))
    return violations


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Markdown → DOCX 标准转换（pandoc + doc_styler）",
    )
    parser.add_argument("input", help="输入 Markdown 文件")
    parser.add_argument("-o", "--output", help="输出 DOCX 路径，默认同输入文件名")
    parser.add_argument(
        "--profile",
        default="word-report",
        help="样式 profile：word-report（默认）/ word-revision / none（跳过样式化）",
    )
    parser.add_argument("--doc-name", default="", help="页脚文档名称，默认取输入文件名")
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE), help="参考模板 DOCX")
    parser.add_argument("--filter", dest="lua_filter", default=str(DEFAULT_FILTER), help="Lua 过滤器")
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        print(f"输入文件不存在: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser() if args.output else input_path.with_suffix(".docx")
    reference_path = resolve_resource(args.reference)
    lua_filter_path = resolve_resource(args.lua_filter)

    # 1. pandoc 转换（模板 + Lua 过滤器）
    run_pandoc(input_path, output_path, reference_path, lua_filter_path)

    # 2. doc_styler 样式规范化 + 交付前自检
    if args.profile != "none":
        doc_name = args.doc_name or input_path.stem
        violations = apply_style(output_path, args.profile, doc_name)
        if violations:
            print("校验失败:", violations, file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
