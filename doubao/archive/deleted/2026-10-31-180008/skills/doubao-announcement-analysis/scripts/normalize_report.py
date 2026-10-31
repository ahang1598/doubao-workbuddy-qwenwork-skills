#!/usr/bin/env python3
"""规范化最终报告 Markdown 的排版（finalize_report.py 的内部 helper）。

草稿阶段允许用「」『』直角引号（模型更容易和 ASCII 引号区分开）。这个脚本把它们
转换成标准中文弯引号，供最终交付使用。

同时自动修复模型常见笔误：用英文直引号 `"..."` 包裹含中文的词句时，先转成「」，
再进入弯引号转换——避免门禁 2 因引号格式报 ERROR，迫使模型逐条手改。

代码块（围栏）与行内代码内的内容原样保留，不做转换。

不做的事：不检查手写角标、不做来源校验——那些是 lint_report.py 的职责。这个脚本
只管排版层面的引号规范化，职责边界要清晰，不要把两件事混在一个脚本里。

用法（一般不单独调用，由 finalize_report.py 编排）：
  python3 normalize_report.py <文件路径> [<文件路径> ...] [--check]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

QUOTE_TRANSLATION = str.maketrans({
    "「": "\u201c",
    "」": "\u201d",
    "『": "\u2018",
    "』": "\u2019",
})

# 与 lint_report.py 的 ASCII_QUOTED_HAN_RE 对齐：英文直引号包裹且内容含汉字
ASCII_QUOTED_HAN_RE = re.compile(r'"([^"\n]*[\u4e00-\u9fff][^"\n]*)"')
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _protect_inline_code(line: str) -> tuple[str, list[str]]:
    parts: list[str] = []

    def repl(match: re.Match[str]) -> str:
        parts.append(match.group(0))
        return f"\x00INLINE{len(parts) - 1}\x00"

    return INLINE_CODE_RE.sub(repl, line), parts


def _restore_inline_code(line: str, parts: list[str]) -> str:
    for idx, part in enumerate(parts):
        line = line.replace(f"\x00INLINE{idx}\x00", part)
    return line


def convert_ascii_quoted_han(line: str) -> str:
    """把 `"中文短语"` 转成「中文短语」，供后续弯引号转换。跳过行内代码。"""
    protected, parts = _protect_inline_code(line)
    converted = ASCII_QUOTED_HAN_RE.sub(r"「\1」", protected)
    return _restore_inline_code(converted, parts)


def normalize_markdown(text: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if is_fence(line):
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
        else:
            fixed = convert_ascii_quoted_han(line)
            out.append(fixed.translate(QUOTE_TRANSLATION))
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把草稿直角引号「」『』及英文直引号包裹的中文短语转换成最终中文弯引号"
    )
    parser.add_argument("paths", nargs="+", help="要规范化的 Markdown 文件（原地修改）")
    parser.add_argument("--check", action="store_true", help="只检查是否需要规范化，不写回文件")
    args = parser.parse_args()

    changed: list[Path] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        text = path.read_text(encoding="utf-8")
        normalized = normalize_markdown(text)
        if normalized != text:
            changed.append(path)
            if not args.check:
                path.write_text(normalized, encoding="utf-8")

    for path in changed:
        print(f"{'需要规范化' if args.check else '已规范化'}: {path}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
