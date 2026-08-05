# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///

"""
从 Word 文档中提取文本内容，保留表格结构信息。

用法：
    uv run scripts/extract_docx.py document.docx
    uv run scripts/extract_docx.py document.docx --output extracted.txt
    uv run scripts/extract_docx.py document.docx --format json
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _tag(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def extract_elements(docx_path: Path) -> list[dict]:
    """从 .docx 中提取结构化元素列表。"""
    with zipfile.ZipFile(docx_path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            print("错误：DOCX 中未找到 word/document.xml", file=sys.stderr)
            return []
        with zf.open("word/document.xml") as f:
            tree = ET.parse(f)

    root = tree.getroot()
    body = root.find(f".//{_tag('body')}")
    if body is None:
        return []

    elements = []
    t = _tag

    for child in body:
        if child.tag == t("p"):
            text = _para_text(child)
            if not text:
                continue

            el: dict = {"type": "paragraph", "text": text}

            pPr = child.find(t("pPr"))
            if pPr is not None:
                pStyle = pPr.find(t("pStyle"))
                if pStyle is not None:
                    style = pStyle.get(f"{{{W_NS}}}val", "")
                    if style:
                        el["style"] = style

            runs = child.findall(t("r"))
            if runs and all(
                r.find(t("rPr")) is not None and r.find(t("rPr")).find(t("b")) is not None
                for r in runs
                if _run_text(r).strip()
            ):
                el["bold"] = True

            has_placeholder = "____" in text or "☐" in text or "☑" in text
            if has_placeholder:
                el["has_field"] = True

            elements.append(el)

        elif child.tag == t("tbl"):
            rows_data = []
            for tr in child.findall(f".//{t('tr')}"):
                cells = []
                for tc in tr.findall(t("tc")):
                    cell_paras = []
                    for p in tc.findall(f".//{t('p')}"):
                        pt = _para_text(p)
                        if pt:
                            cell_paras.append(pt)
                    cells.append(" / ".join(cell_paras) if cell_paras else "")
                if any(cells):
                    rows_data.append(cells)
            if rows_data:
                has_fields = any(
                    "____" in cell or "☐" in cell or "☑" in cell or cell == ""
                    for row in rows_data for cell in row
                )
                el = {"type": "table", "rows": rows_data}
                if has_fields:
                    el["has_fields"] = True
                elements.append(el)

    return elements


def _para_text(p_elem) -> str:
    return "".join(
        t_elem.text for t_elem in p_elem.findall(f".//{_tag('t')}") if t_elem.text
    )


def _run_text(r_elem) -> str:
    return "".join(
        t_elem.text for t_elem in r_elem.findall(_tag("t")) if t_elem.text
    )


def elements_to_text(elements: list[dict]) -> str:
    """将结构化元素转为带表格标注的可读文本。"""
    lines = []
    tbl_idx = 0

    for el in elements:
        if el["type"] == "table":
            tbl_idx += 1
            lines.append(f"\n--- 表格 {tbl_idx} ---")
            for r_idx, row in enumerate(el["rows"], 1):
                lines.append(f"  行{r_idx}: " + " | ".join(c if c else "(空)" for c in row))
            lines.append("")
        else:
            text = el["text"]
            if el.get("bold"):
                text = f"**{text}**"
            lines.append(text)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="从 Word 文档中提取文本")
    parser.add_argument("docx_path", type=Path, help="DOCX 文件路径")
    parser.add_argument("-o", "--output", type=Path, help="输出文件路径（默认输出到终端）")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式：text（带表格标注的可读文本）、json（结构化数据）",
    )

    args = parser.parse_args()

    if not args.docx_path.exists():
        print(f"错误：文件不存在：{args.docx_path}", file=sys.stderr)
        sys.exit(1)

    elements = extract_elements(args.docx_path)

    if args.format == "json":
        output = json.dumps(elements, indent=2, ensure_ascii=False)
    else:
        output = elements_to_text(elements)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"已写入：{args.output}（共 {len(elements)} 个元素）", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
