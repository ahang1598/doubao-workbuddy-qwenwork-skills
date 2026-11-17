#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_docx_format.py — 合同文档格式标准化

作用:
    统一 .docx 合同文件的字体、字号、标题层级,避免因来源不同(扫描件转Word、
    .doc 旧格式转换、不同模板导出)导致的字体大小不一、样式混乱问题。

设计原则:
    - 只改格式,不改内容: 不增删任何文字,仅调整 run 的字体属性
    - 安全无破坏: 对 Track Changes 修订标记、批注等结构保持不动
    - 可配置: 字体、字号、标题识别规则均可通过参数调整
    - 幂等: 重复执行结果一致

标题识别规则 (中文合同常见模式):
    - 主标题: 文档首段,内容为"XX协议/XX合同/保密协议"等
    - 一级标题: "第X条"、"第一条"、"序言"、"附则"、"其他约定"等
    - 其余为正文

用法:
    python3 normalize_docx_format.py <input.docx> [--output output.docx]
    python3 normalize_docx_format.py contract.docx --body-font 宋体 --body-size 12

退出码:
    0  成功
    1  输入错误
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt
    from docx.oxml.ns import qn
except ImportError:
    print("[ERROR] python-docx 未安装,请先执行: pip install python-docx", file=sys.stderr)
    sys.exit(1)


# ── 默认配置 ──────────────────────────────────────────────
DEFAULT_BODY_FONT = "宋体"
DEFAULT_BODY_SIZE = 12.0  # pt (小四)
DEFAULT_TITLE_FONT = "黑体"
DEFAULT_TITLE_SIZE = 16.0  # pt (三号)
DEFAULT_H1_FONT = "黑体"
DEFAULT_H1_SIZE = 14.0  # pt (四号)

# 一级标题正则: 匹配多种中文合同标题格式
# 1. 第X条 / 第一章 / 第X章
# 2. 冒号开头 (如 "：保密信息"、"：义务") — 部分合同模板的特殊格式
# 3. 序言 / 前言 / 总则 / 附则 / 其他约定 / 争议解决 / 违约责任 等独立标题
H1_PATTERN = re.compile(
    r"^(第[一二三四五六七八九十百千零\d]+[条章节]"
    r"|：[^：]{2,15}$"
    r"|序言|前言|总则|附则|结尾|其他|其他约定|争议解决|违约责任"
    r"|附件[一二三四五六七八九十\d]+.*)$"
)

# 主标题关键词: 出现在文档开头且含"协议/合同/合约/备忘录"等
MAIN_TITLE_KEYWORDS = ("协议", "合同", "合约", "备忘录", "保密协议", "合作协议")


def is_main_title(text: str, para_idx: int) -> bool:
    """判断是否为文档主标题(首段 + 含协议/合同关键词 + 较短)"""
    stripped = text.strip()
    if para_idx > 3:  # 只看前几段
        return False
    if len(stripped) > 30 or len(stripped) < 2:
        return False
    return any(kw in stripped for kw in MAIN_TITLE_KEYWORDS)


def is_h1_heading(text: str) -> bool:
    """判断是否为一级条款标题"""
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > 25:
        return False
    return bool(H1_PATTERN.match(stripped))


def set_run_font(run, font_name: str, font_size_pt: float, bold: bool | None = None):
    """设置单个 run 的中英文字体和字号。"""
    run.font.name = font_name
    run.font.size = Pt(font_size_pt)
    # 中文字体需要单独设置 eastAsia
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        from docx.oxml import OxmlElement
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), font_name)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)

    if bold is not None:
        run.font.bold = bold


def normalize_document(
    doc,
    body_font: str = DEFAULT_BODY_FONT,
    body_size: float = DEFAULT_BODY_SIZE,
    title_font: str = DEFAULT_TITLE_FONT,
    title_size: float = DEFAULT_TITLE_SIZE,
    h1_font: str = DEFAULT_H1_FONT,
    h1_size: float = DEFAULT_H1_SIZE,
) -> dict:
    """
    标准化整个文档的字体格式。

    返回统计信息 dict。
    """
    stats = {
        "total_paragraphs": 0,
        "body_paragraphs": 0,
        "main_title_paragraphs": 0,
        "h1_paragraphs": 0,
        "body_font": body_font,
        "body_size_pt": body_size,
    }

    for idx, para in enumerate(doc.paragraphs):
        stats["total_paragraphs"] += 1
        text = para.text

        if not text.strip():
            continue  # 空段落跳过

        # 判断层级
        if is_main_title(text, idx):
            level = "title"
            stats["main_title_paragraphs"] += 1
        elif is_h1_heading(text):
            level = "h1"
            stats["h1_paragraphs"] += 1
        else:
            level = "body"
            stats["body_paragraphs"] += 1

        # 应用格式
        for run in para.runs:
            if level == "title":
                set_run_font(run, title_font, title_size, bold=True)
                para.alignment = 1  # 居中
            elif level == "h1":
                set_run_font(run, h1_font, h1_size, bold=True)
            else:
                set_run_font(run, body_font, body_size)

    return stats


def main():
    parser = argparse.ArgumentParser(description="合同 docx 格式标准化 — 统一字体字号")
    parser.add_argument("input", help="输入 .docx 文件路径")
    parser.add_argument("--output", "-o", default=None,
                        help="输出路径(默认覆盖原文件,建议指定新路径)")
    parser.add_argument("--body-font", default=DEFAULT_BODY_FONT,
                        help=f"正文字体(默认 {DEFAULT_BODY_FONT})")
    parser.add_argument("--body-size", type=float, default=DEFAULT_BODY_SIZE,
                        help=f"正文字号 pt(默认 {DEFAULT_BODY_SIZE})")
    parser.add_argument("--title-font", default=DEFAULT_TITLE_FONT,
                        help=f"主标题字体(默认 {DEFAULT_TITLE_FONT})")
    parser.add_argument("--title-size", type=float, default=DEFAULT_TITLE_SIZE,
                        help=f"主标题字号 pt(默认 {DEFAULT_TITLE_SIZE})")
    parser.add_argument("--h1-font", default=DEFAULT_H1_FONT,
                        help=f"一级标题字体(默认 {DEFAULT_H1_FONT})")
    parser.add_argument("--h1-size", type=float, default=DEFAULT_H1_SIZE,
                        help=f"一级标题字号 pt(默认 {DEFAULT_H1_SIZE})")
    parser.add_argument("--inplace", action="store_true",
                        help="直接覆盖原文件(默认生成新文件)")
    args = parser.parse_args()

    in_path = os.path.abspath(args.input)
    if not os.path.isfile(in_path):
        print(f"[ERROR] 文件不存在: {in_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(in_path)[1].lower()
    if ext != ".docx":
        print(f"[ERROR] 仅支持 .docx 文件,当前: {ext}", file=sys.stderr)
        sys.exit(1)

    # 输出路径
    if args.output:
        out_path = os.path.abspath(args.output)
    elif args.inplace:
        out_path = in_path
    else:
        base = os.path.splitext(in_path)[0]
        out_path = f"{base}_normalized.docx"

    # 执行标准化
    doc = Document(in_path)
    stats = normalize_document(
        doc,
        body_font=args.body_font,
        body_size=args.body_size,
        title_font=args.title_font,
        title_size=args.title_size,
        h1_font=args.h1_font,
        h1_size=args.h1_size,
    )

    doc.save(out_path)

    # 输出结果 JSON (供 pipeline 解析)
    result = {
        "success": True,
        "input_path": in_path,
        "output_path": out_path,
        "stats": stats,
        "notes": (
            f"已统一格式: 正文 {args.body_font} {args.body_size}pt, "
            f"一级标题 {args.h1_font} {args.h1_size}pt 加粗, "
            f"主标题 {args.title_font} {args.title_size}pt 加粗居中。"
        ),
    }
    print(__import__("json").dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
