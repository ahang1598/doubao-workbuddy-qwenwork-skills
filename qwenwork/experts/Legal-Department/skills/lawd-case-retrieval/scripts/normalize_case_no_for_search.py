#!/usr/bin/env python3
"""
裁判文书网搜索框用案号：去除全部空白与常见粘贴噪声字符。

与 references/detail-query-case-no-examples.md「步骤 1.1」第 7 条（删除全部空白字符）对齐，
作为模式B 步骤 B4 键入前的可重复闸门；不替代步骤 B1 的年份括号、全角数字等完整标准化。
"""

from __future__ import annotations

import argparse
import sys

# 常见复制/OCR 噪声（isspace() 为 False）
_EXTRA_REMOVE = frozenset(
    {
        "\u200b",  # ZERO WIDTH SPACE
        "\u200c",  # ZERO WIDTH NON-JOINER
        "\u200d",  # ZERO WIDTH JOINER
        "\ufeff",  # ZERO WIDTH NO-BREAK SPACE / BOM
    }
)


def normalize_for_search(s: str) -> str:
    """删除所有 Unicode 空白（str.isspace）及 _EXTRA_REMOVE 中的字符。"""
    return "".join(ch for ch in s if not ch.isspace() and ch not in _EXTRA_REMOVE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="输出去除全部空白后的案号串，供裁判文书网搜索框粘贴。"
    )
    parser.add_argument(
        "case_string",
        nargs="?",
        default=None,
        help="原始案号；省略则从 stdin 读取全文",
    )
    args = parser.parse_args()

    raw = args.case_string
    if raw is None:
        raw = sys.stdin.read()

    out = normalize_for_search(raw)
    if not out:
        print("错误：去除空白后为空，请检查输入。", file=sys.stderr)
        return 1

    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
