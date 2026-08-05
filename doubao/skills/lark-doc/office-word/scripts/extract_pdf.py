# /// script
# requires-python = ">=3.10"
# dependencies = ["pdfplumber"]
# ///

"""
从 PDF 简历中提取文本内容，支持多栏检测和表格提取。

用法：
    uv run scripts/extract_pdf.py resume.pdf
    uv run scripts/extract_pdf.py resume.pdf --output extracted.txt
    uv run scripts/extract_pdf.py resume.pdf --format structured
"""

import argparse
import json
import re
import sys
from pathlib import Path


def _detect_columns(page) -> int:
    """根据字符 x 坐标分布检测页面是否为多栏排版。"""
    chars = page.chars
    if not chars:
        return 1

    x_positions = sorted(set(round(c["x0"]) for c in chars))
    if len(x_positions) < 10:
        return 1

    page_width = page.width
    mid = page_width / 2
    gap_width = page_width * 0.05

    left_chars = sum(1 for c in chars if c["x0"] < mid - gap_width)
    right_chars = sum(1 for c in chars if c["x0"] > mid + gap_width)
    total = left_chars + right_chars

    if total == 0:
        return 1

    ratio = min(left_chars, right_chars) / total
    return 2 if ratio > 0.25 else 1


def _extract_two_column(page) -> str:
    """分别提取左右两栏的文本。"""
    mid = page.width / 2
    gap = page.width * 0.03

    left_box = (0, 0, mid - gap, page.height)
    right_box = (mid + gap, 0, page.width, page.height)

    left_crop = page.crop(left_box)
    right_crop = page.crop(right_box)

    left_text = left_crop.extract_text() or ""
    right_text = right_crop.extract_text() or ""

    parts = []
    if left_text.strip():
        parts.append(left_text.strip())
    if right_text.strip():
        parts.append(right_text.strip())

    return "\n\n".join(parts)


def _guess_element_type(line: str) -> str:
    """对提取的文本行做简单的结构类型推测。"""
    stripped = line.strip()
    if not stripped:
        return "empty"

    if re.match(r"^[\u2022\u25cf\u25cb\u2013\u2014\-•·●○◦▪►]\s", stripped):
        return "list_item"

    if len(stripped) < 40 and stripped.isupper():
        return "heading"

    common_headings = {
        "工作经历", "教育背景", "专业技能", "技能", "项目经历", "个人简介",
        "自我评价", "联系方式", "证书", "荣誉", "语言能力", "培训经历",
        "EXPERIENCE", "EDUCATION", "SKILLS", "PROJECTS", "SUMMARY",
        "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "CERTIFICATIONS",
        "CONTACT", "ACHIEVEMENTS", "AWARDS", "PUBLICATIONS",
    }
    if stripped.upper() in {h.upper() for h in common_headings}:
        return "heading"

    email_phone = re.search(r"[\w.-]+@[\w.-]+|[\d\-\(\)\+\s]{7,}", stripped)
    if email_phone and len(stripped) < 100:
        return "contact"

    return "paragraph"


def extract_pdf_elements(pdf_path: Path) -> list[dict]:
    """提取 PDF 为结构化元素列表。"""
    try:
        import pdfplumber
    except ImportError:
        print("错误：pdfplumber 不可用。请运行：uv sync", file=sys.stderr)
        sys.exit(1)

    elements = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    rows = []
                    for row in table:
                        cleaned = [cell.strip() if cell else "" for cell in row]
                        if any(cleaned):
                            rows.append(cleaned)
                    if rows:
                        elements.append({
                            "type": "table",
                            "page": page_num,
                            "rows": rows,
                        })

            num_cols = _detect_columns(page)
            if num_cols == 2:
                text = _extract_two_column(page)
            else:
                text = page.extract_text()

            if not text:
                continue

            for line in text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue

                etype = _guess_element_type(stripped)
                if etype == "empty":
                    continue

                el = {"type": etype, "text": stripped, "page": page_num}
                if num_cols == 2:
                    el["multi_column"] = True
                elements.append(el)

    return elements


def elements_to_text(elements: list[dict]) -> str:
    """将结构化元素转为 Markdown 风格可读文本。"""
    lines = []
    current_page = 0

    for el in elements:
        page = el.get("page", 0)
        if page != current_page:
            if current_page > 0:
                lines.append("")
            lines.append(f"--- 第 {page} 页 ---")
            current_page = page

        etype = el["type"]
        if etype == "heading":
            lines.append(f"\n## {el['text']}")
        elif etype == "list_item":
            lines.append(f"  - {el['text']}")
        elif etype == "table":
            for row in el["rows"]:
                lines.append(" | ".join(row))
            lines.append("")
        elif etype == "contact":
            lines.append(f"[联系信息] {el['text']}")
        else:
            lines.append(el["text"])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="从 PDF 简历中提取文本")
    parser.add_argument("pdf_path", type=Path, help="PDF 文件路径")
    parser.add_argument("-o", "--output", type=Path, help="输出文件路径（默认输出到终端）")
    parser.add_argument(
        "--format",
        choices=["text", "structured", "json"],
        default="text",
        help="输出格式：text（Markdown 风格可读文本）、structured/json（JSON 结构化数据）",
    )

    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"错误：文件不存在：{args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not args.pdf_path.suffix.lower() == ".pdf":
        print(f"错误：不是 PDF 文件：{args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    elements = extract_pdf_elements(args.pdf_path)

    if args.format in ("structured", "json"):
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
