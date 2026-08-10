#!/usr/bin/env python3
"""Validate the mandatory Word geometry and typography of an audit report."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


TOLERANCE_PT = 0.6
MARKDOWN_RE = re.compile(r"(^|\s)(#{1,6}\s|\*\*|`{1,3}|>\s)", re.MULTILINE)


def near(actual: float | None, expected: float, tolerance: float = TOLERANCE_PT) -> bool:
    return actual is not None and abs(actual - expected) <= tolerance


def points(value) -> float | None:
    return value.pt if value is not None and hasattr(value, "pt") else None


def line_points(paragraph_format) -> float | None:
    value = paragraph_format.line_spacing
    return value.pt if value is not None and hasattr(value, "pt") else None


def font_pair(run) -> tuple[str | None, str | None]:
    if run._element.rPr is None or run._element.rPr.rFonts is None:
        return None, None
    fonts = run._element.rPr.rFonts
    latin = fonts.get(qn("w:ascii")) or fonts.get(qn("w:hAnsi"))
    east_asia = fonts.get(qn("w:eastAsia"))
    return latin, east_asia


def check_style(document, name: str, size: float, line: float, before: float,
                after: float, indent: float | None, alignment, errors: list[str]) -> None:
    style = document.styles[name]
    pf = style.paragraph_format
    if not near(points(style.font.size), size):
        errors.append(f"{name}字号应为{size}pt")
    if not near(line_points(pf), line):
        errors.append(f"{name}行距应为固定值{line}pt")
    if not near(points(pf.space_before) or 0.0, before):
        errors.append(f"{name}段前应为{before}pt")
    if not near(points(pf.space_after) or 0.0, after):
        errors.append(f"{name}段后应为{after}pt")
    if indent is not None and not near(points(pf.first_line_indent) or 0.0, indent):
        errors.append(f"{name}首行缩进应为{indent}pt")
    if pf.alignment != alignment:
        errors.append(f"{name}对齐方式不符合强制规范")


def validate(path: Path) -> tuple[list[str], list[str]]:
    document = Document(path)
    errors: list[str] = []
    warnings: list[str] = []

    if not document.sections:
        return ["文档没有节"], warnings

    for index, section in enumerate(document.sections, 1):
        if not near(section.page_width.cm, 21.0, 0.03) or not near(section.page_height.cm, 29.7, 0.03):
            errors.append(f"第{index}节纸张不是A4")
        expected = (2.54, 2.54, 3.17, 3.17)
        actual = (section.top_margin.cm, section.bottom_margin.cm,
                  section.left_margin.cm, section.right_margin.cm)
        if any(abs(a - e) > 0.03 for a, e in zip(actual, expected)):
            errors.append(f"第{index}节页边距不是上/下2.54cm、左/右3.17cm")

    check_style(document, "Normal", 12, 20, 6, 6, 24,
                WD_ALIGN_PARAGRAPH.JUSTIFY, errors)
    check_style(document, "Heading 1", 14, 24, 12, 6, 0,
                WD_ALIGN_PARAGRAPH.LEFT, errors)
    check_style(document, "Heading 2", 12, 23, 9, 4, 0,
                WD_ALIGN_PARAGRAPH.LEFT, errors)
    check_style(document, "Heading 3", 12, 22, 6, 3, 0,
                WD_ALIGN_PARAGRAPH.LEFT, errors)
    check_style(document, "Heading 4", 12, 22, 6, 3, 0,
                WD_ALIGN_PARAGRAPH.LEFT, errors)

    nonempty = [p for p in document.paragraphs if p.text.strip()]
    if not nonempty:
        errors.append("文档没有正文")
        return errors, warnings
    title = nonempty[0]
    title_run = title.runs[0] if title.runs else None
    if title.alignment != WD_ALIGN_PARAGRAPH.CENTER:
        errors.append("报告主标题未居中")
    if title_run is None or not near(points(title_run.font.size), 16):
        errors.append("报告主标题字号应为16pt")
    if not near(line_points(title.paragraph_format), 26):
        errors.append("报告主标题行距应为固定值26pt")
    if not near(points(title.paragraph_format.space_after) or 0.0, 18):
        errors.append("报告主标题段后应为18pt")

    for index, paragraph in enumerate(nonempty, 1):
        if MARKDOWN_RE.search(paragraph.text):
            errors.append(f"第{index}个非空段落含Markdown控制符")
        for run in paragraph.runs:
            latin, east_asia = font_pair(run)
            if latin and latin != "Times New Roman":
                warnings.append(f"第{index}个非空段落存在非Times New Roman西文字体：{latin}")
            if east_asia and east_asia != "宋体":
                warnings.append(f"第{index}个非空段落存在非宋体中文字体：{east_asia}")

    return errors, sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description="校验个人信息保护审计报告DOCX强制格式")
    parser.add_argument("docx", help="待校验DOCX文件")
    args = parser.parse_args()
    path = Path(args.docx)
    if not path.is_file():
        raise SystemExit(f"文件不存在：{path}")
    errors, warnings = validate(path)
    for item in errors:
        print("错误：" + item)
    for item in warnings:
        print("警告：" + item)
    if errors:
        print(f"DOCX格式校验未通过：{len(errors)}项错误，{len(warnings)}项警告")
        return 1
    print(f"DOCX格式校验通过：0项错误，{len(warnings)}项警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
