#!/usr/bin/env python3
"""Markdown → DOCX 标准转换流程。

流程：pandoc（律师规范模板 + Lua 过滤器）→ gridSpan 修复 → doc_styler.py 样式规范化 → 交付前自检。

用法：
    python md2docx.py input.md                        # 默认 word-report profile
    python md2docx.py input.md -o output.docx         # 指定输出路径
    python md2docx.py input.md --profile none          # 跳过样式化（仅 pandoc）
    python md2docx.py input.md --doc-name "报告标题"   # 自定义页脚名称

表格约定：
    统一使用 HTML <table> 语法编写表格（支持 colspan/rowspan 合并单元格）。
    Pandoc --from=html 解析 HTML 表格后，DOCX writer 不输出 w:gridSpan，
    本脚本通过 OOXML 后处理补全合并属性。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    from lxml import etree
except ImportError:
    etree = None

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REFERENCE = SCRIPT_DIR / "templates" / "template.docx"
DEFAULT_FILTER = SCRIPT_DIR / "markdown-to-docx.lua"

# 解析 HTML 单元格 colspan/rowspan 属性
_HTML_TABLE_RE = re.compile(r"<table\b.*?</table>", re.DOTALL | re.IGNORECASE)
_CELL_ATTR_RE = re.compile(r'<(td|th)\b([^>]*)>', re.IGNORECASE)
_COLSPAN_RE = re.compile(r'colspan\s*=\s*["\']?(\d+)["\']?', re.IGNORECASE)
_ROWSPAN_RE = re.compile(r'rowspan\s*=\s*["\']?(\d+)["\']?', re.IGNORECASE)

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
qn = lambda tag: f'{{{W_NS}}}{tag}'


def _parse_html_table_spans(markdown_text: str) -> list[list[list[tuple[int, int]]]]:
    """从 Markdown 文本中提取所有 HTML 表格的单元格 colspan/rowspan 信息。

    返回: [table_index][row_index][cell_index] = (colspan, rowspan)
    """
    tables_spans = []
    for match in _HTML_TABLE_RE.finditer(markdown_text):
        table_html = match.group(0)
        rows_html = re.findall(r'<tr\b[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)

        table_rows = []
        for row_html in rows_html:
            cells = _CELL_ATTR_RE.findall(row_html)
            row_spans = []
            for tag, attrs in cells:
                cs_m = _COLSPAN_RE.search(attrs)
                rs_m = _ROWSPAN_RE.search(attrs)
                colspan = int(cs_m.group(1)) if cs_m else 1
                rowspan = int(rs_m.group(1)) if rs_m else 1
                row_spans.append((colspan, rowspan))
            if row_spans:
                table_rows.append(row_spans)
        if table_rows:
            tables_spans.append(table_rows)
    return tables_spans


def fix_docx_gridspan(docx_path: Path, html_tables_info: list[list[list[tuple[int, int]]]]) -> int:
    """修复 DOCX 中 HTML 表格丢失的 gridSpan 属性。

    Pandoc --from=html 输出 DOCX 时，HTML 表格的 colspan/rowspan 属性不会写入 w:gridSpan。
    此函数通过对比原始 Markdown 中的表格结构，在 OOXML 中补全 gridSpan。

    返回修复的单元格数量。
    """
    if etree is None or not html_tables_info:
        return 0

    fixed_count = 0
    html_idx = 0

    with zipfile.ZipFile(docx_path, 'r') as z:
        xml_bytes = z.read('word/document.xml')

    root = etree.fromstring(xml_bytes)
    ooxml_tables = root.findall(f'.//{qn("tbl")}')

    for ooxml_tbl in ooxml_tables:
        if html_idx >= len(html_tables_info):
            break

        ooxml_rows = ooxml_tbl.findall(qn('tr'))
        if not ooxml_rows:
            continue

        # 检查此 OOXML 表格是否需要修复（某行单元格数 < tblGrid 列数）
        grid = ooxml_tbl.find(qn('tblGrid'))
        grid_cols = len(grid.findall(qn('gridCol'))) if grid is not None else 0

        needs_fix = False
        for row in ooxml_rows:
            if len(row.findall(qn('tc'))) < grid_cols:
                needs_fix = True
                break

        if not needs_fix and grid_cols > 0:
            continue

        # 取下一个有合并的 HTML 表格信息
        while html_idx < len(html_tables_info):
            spans_info = html_tables_info[html_idx]
            if any(cs > 1 or rs > 1 for row in spans_info for cs, rs in row):
                break
            html_idx += 1

        if html_idx >= len(html_tables_info):
            break

        spans_info = html_tables_info[html_idx]

        matched = True
        for ri, row_spans in enumerate(spans_info):
            if ri >= len(ooxml_rows):
                matched = False
                break

            ooxml_cells = ooxml_rows[ri].findall(qn('tc'))
            ci = 0
            for (colspan, rowspan) in row_spans:
                if ci >= len(ooxml_cells):
                    matched = False
                    break

                tc = ooxml_cells[ci]
                if colspan > 1:
                    tcPr = tc.find(qn('tcPr'))
                    if tcPr is None:
                        tcPr = etree.Element(qn('tcPr'))
                        tc.insert(0, tcPr)

                    old_gs = tcPr.find(qn('gridSpan'))
                    if old_gs is not None:
                        tcPr.remove(old_gs)

                    gs = etree.SubElement(tcPr, qn('gridSpan'))
                    gs.set(qn('val'), str(colspan))
                    fixed_count += 1

                ci += 1

            if not matched:
                break

        if matched:
            html_idx += 1

    if fixed_count > 0:
        xml_bytes = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        _replace_in_zip(docx_path, 'word/document.xml', xml_bytes)

    return fixed_count


def _replace_in_zip(zip_path: Path, member_name: str, new_content: bytes) -> None:
    """替换 ZIP 包中的指定文件（解决 append 模式无法覆盖的问题）。"""
    import io
    with zipfile.ZipFile(zip_path, 'r') as z_in:
        new_zip_buffer = io.BytesIO()
        with zipfile.ZipFile(new_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.infolist():
                if item.filename == member_name:
                    z_out.writestr(item, new_content)
                else:
                    z_out.writestr(item, z_in.read(item.filename))
        with open(zip_path, 'wb') as f:
            f.write(new_zip_buffer.getvalue())


def resolve_resource(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    for candidate in (path, SCRIPT_DIR / path_text, SCRIPT_DIR / "templates" / path_text):
        if candidate.exists():
            return candidate
    return path


def run_pandoc(input_path: Path, output_path: Path, reference: Path, lua_filter: Path) -> None:
    """pandoc 转换（默认 markdown 格式，Lua 过滤器处理 HTML 表格）。

    约定：表格统一使用 HTML <table> 语法（支持 colspan/rowspan）。
    Lua 过滤器 html-table-to-ast.lua 会把 RawBlock 中的 HTML 表格
    合并并转换为 Pandoc Table AST，同时保留 Markdown 其他语法（标题、列表等）。

    容错策略：Lua 过滤器出错时，自动降级为不带过滤器重试，
    保证基础转换（标题/段落/列表等）不受过滤器 bug 影响。
    """
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
        # Lua 过滤器出错：降级为不带过滤器重试，保证基础转换可用
        print(f"[警告] Lua 过滤器执行失败(exit={error.returncode})，降级为无过滤器重试...", file=sys.stderr)
        fallback_cmd = [
            "pandoc",
            str(input_path),
            "--reference-doc", str(reference),
            "-o", str(output_path),
        ]
        try:
            subprocess.run(fallback_cmd, check=True)
            print("[警告] 已降级完成转换（HTML 表格/合并单元格/对齐等 Lua 功能未生效）", file=sys.stderr)
        except subprocess.CalledProcessError as fb_error:
            print(f"[错误] 降级转换也失败(exit={fb_error.returncode})", file=sys.stderr)
            raise SystemExit(fb_error.returncode)


def apply_style(output_path: Path, profile: str, doc_name: str, footer_format: str = "page-of-total") -> list[str]:
    sys.path.insert(0, str(SCRIPT_DIR))
    from docx import Document
    from doc_styler import apply_doc_style

    doc = Document(str(output_path))
    violations = apply_doc_style(doc, profile=profile, doc_name=doc_name, footer_format=footer_format)
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
    parser.add_argument("--doc-name", default="", help="页脚文档名称（仅 name-page / name-page-of-total 页脚格式需要）")
    parser.add_argument(
        "--footer-format",
        default="page-of-total",
        choices=["page-only", "name-page", "page-of-total", "name-page-of-total", "none"],
        help="页脚格式：page-only（仅页码）/ name-page（名+页码，默认）/ page-of-total（页码/总数）/ name-page-of-total（名+页码/总数）/ none（无页脚）",
    )
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

    # 0. 读取原始 Markdown（用于 HTML 表格 span 提取）
    md_text = input_path.read_text(encoding='utf-8')

    # 1. pandoc 转换（--from=html + 模板 + Lua 过滤器）
    run_pandoc(input_path, output_path, reference_path, lua_filter_path)

    # 2. 修复 HTML 表格 gridSpan 丢失问题
    html_spans = _parse_html_table_spans(md_text)
    if html_spans:
        fixed = fix_docx_gridspan(output_path, html_spans)
        if fixed > 0:
            print(f'[gridSpan] 已修复 {fixed} 个合并单元格', file=sys.stderr)

    # 3. doc_styler 样式规范化 + 交付前自检
    if args.profile != "none":
        # doc_name 仅在 name-page 系页脚格式才需要，默认不取文件名
        doc_name = args.doc_name
        violations = apply_style(output_path, args.profile, doc_name, args.footer_format)
        if violations:
            print("校验失败:", violations, file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
