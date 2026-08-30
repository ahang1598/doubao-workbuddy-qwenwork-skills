#!/usr/bin/env python3
"""Classify content source type and recommend extraction method.

Given a URL or file path, determines the source type and outputs
the recommended extraction tool/method per content-sources.md.

Usage:
  python content_classifier.py --input "https://mp.weixin.qq.com/s/xxxxx"
  python content_classifier.py --input "/path/to/file.docx"
  python content_classifier.py --input "一段用户粘贴的文字..."

  # Batch mode: one input per line
  python content_classifier.py --batch inputs.txt

Output JSON:
  {
    "input": "...",
    "source_type": "wechat_article",
    "extraction_tool": "read_url",
    "extraction_command": "read_url(url='...')",
    "notes": "过滤文末广告和推荐阅读"
  }
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


def classify_single(input_str: str) -> dict:
    """Classify a single input string."""
    input_str = input_str.strip()
    if not input_str:
        return {"input": "", "source_type": "empty", "error": "输入为空"}

    # --- URL detection ---
    if re.match(r"https?://", input_str, re.IGNORECASE):
        return _classify_url(input_str)

    # --- File path detection ---
    if os.path.sep in input_str or input_str.startswith(".") or input_str.startswith("~"):
        return _classify_file(input_str)

    # Check if it looks like a filename with extension
    _, ext = os.path.splitext(input_str)
    if ext and len(ext) <= 6:
        return _classify_file(input_str)

    # --- Plain text fallback ---
    return {
        "input": input_str[:80] + ("..." if len(input_str) > 80 else ""),
        "source_type": "plain_text",
        "extraction_tool": "none",
        "extraction_command": "直接使用，保存为临时 .txt 文件供定量分析",
        "notes": "用户在对话中粘贴的文字，无需额外提取",
    }


def _classify_url(url: str) -> dict:
    """Classify a URL input."""
    base = {"input": url}

    # Xiaohongshu
    if re.search(r"xiaohongshu\.com|xhslink\.com", url, re.IGNORECASE):
        is_short = "xhslink.com" in url.lower()
        return {
            **base,
            "source_type": "xiaohongshu",
            "extraction_tool": "xhs-content-reader",
            "extraction_command": (
                "check-login → search-feeds → get-feed-detail → close-browser"
            ),
            "is_short_link": is_short,
            "notes": (
                "短链接需先 read_url 获取重定向后的完整URL" if is_short
                else "从URL中提取笔记ID，通过search获取xsec_token配对"
            ),
            "feed_id": _extract_xhs_id(url),
        }

    # WeChat article
    if re.search(r"mp\.weixin\.qq\.com", url, re.IGNORECASE):
        return {
            **base,
            "source_type": "wechat_article",
            "extraction_tool": "read_url",
            "extraction_command": f"read_url(url='{url}')",
            "notes": "过滤文末广告和推荐阅读，提取作者名用于标注来源",
        }

    # Generic URL
    return {
        **base,
        "source_type": "generic_url",
        "extraction_tool": "read_url",
        "extraction_command": f"read_url(url='{url}')",
        "notes": "通用URL，尝试 read_url 提取正文",
    }


def _classify_file(path: str) -> dict:
    """Classify a file path input."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    base = {"input": path, "file_exists": os.path.isfile(path)}

    if ext in (".docx",):
        return {
            **base,
            "source_type": "word_document",
            "extraction_tool": "parse_file",
            "extraction_command": f"parse_file(file_path='{path}', query='提取文档正文内容')",
            "notes": "跳过目录、页眉页脚、参考文献等非正文部分",
        }

    if ext in (".pdf",):
        return {
            **base,
            "source_type": "pdf_document",
            "extraction_tool": "parse_file",
            "extraction_command": f"parse_file(file_path='{path}', query='提取文档正文内容')",
            "notes": "跳过目录、页眉页脚、参考文献等非正文部分",
        }

    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        return {
            **base,
            "source_type": "image_ocr",
            "extraction_tool": "understand_media",
            "extraction_command": (
                f"understand_media(media_path='{path}', "
                f"question='请提取图片中的所有文字内容，保持原始排版格式')"
            ),
            "notes": "适用于截图的小红书笔记、公众号文章截图、手写笔记照片等",
        }

    if ext in (".txt", ".md"):
        return {
            **base,
            "source_type": "text_file",
            "extraction_tool": "read_file",
            "extraction_command": f"read_file(absolute_path='{path}')",
            "notes": "纯文本文件，直接读取",
        }

    return {
        **base,
        "source_type": "unknown_file",
        "extraction_tool": "unknown",
        "notes": f"不支持的文件格式: {ext}",
    }


def _extract_xhs_id(url: str) -> str | None:
    """Try to extract Xiaohongshu note ID from URL."""
    # Pattern: /explore/ID or /discovery/item/ID
    m = re.search(r"/(?:explore|discovery/item)/([a-zA-Z0-9]+)", url)
    return m.group(1) if m else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify content source type")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Single URL, file path, or text to classify")
    group.add_argument("--batch", help="File with one input per line for batch classification")
    args = parser.parse_args()

    if args.batch:
        batch_path = os.path.abspath(args.batch)
        with open(batch_path, "r", encoding="utf-8") as f:
            inputs = [line.strip() for line in f if line.strip()]
        results = [classify_single(inp) for inp in inputs]
    else:
        results = classify_single(args.input)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
