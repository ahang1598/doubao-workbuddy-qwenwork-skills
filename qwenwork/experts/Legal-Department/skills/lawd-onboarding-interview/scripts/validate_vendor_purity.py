#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
供应商名纯净度门禁（办案画像 / 中枢输出文本）

三铁律要求"只写能力语义，绝不写死任何数据源供应商名、工具名或优先顺序"。
本脚本是交付前的机械防线：扫描文本，命中供应商名/工具名即拦截。
匹配前归一化（NFKC 全半角转换、去 markdown 标记与空白），防「天 眼 查」「**企查查**」等写法绕过。

用法：
    python3 scripts/validate_vendor_purity.py --file 办案画像.md
    python3 scripts/validate_vendor_purity.py --text "待检查的文本"

退出码：0 通过 / 1 拦截（逐条明细）/ 2 输入错误
"""
import argparse
import re
import sys
import unicodedata

VENDOR_PATTERNS = [
    ("天眼查", re.compile("天眼查")),
    ("企查查", re.compile("企查查")),
    ("启信宝", re.compile("启信宝")),
    ("爱企查", re.compile("爱企查")),
    ("tianyancha", re.compile(r"(?i)(?<![a-z0-9])tianyancha(?![a-z0-9])")),
    ("qichacha", re.compile(r"(?i)(?<![a-z0-9])qichacha(?![a-z0-9])")),
    ("tyc", re.compile(r"(?i)(?<![a-z0-9])tyc(?![a-z0-9])")),
    ("qcc", re.compile(r"(?i)(?<![a-z0-9])qcc(?![a-z0-9])")),
    ("北大法宝/pkulaw", re.compile(r"(?i)pkulaw|北大法宝")),
    ("fy-law-search-service", re.compile(r"(?i)fy[-_ ]?law[-_ ]?search")),
    ("TextIn/合合信息", re.compile(r"(?i)textin|合合信息")),
    ("qwenwork_mcp/mcp_tool", re.compile(r"(?i)qwenwork[_ ]?mcp|mcp[_ ]?tool")),
]

MD_STRIP_RE = re.compile(r"[*_`>#|]")


def normalize_line(line: str) -> str:
    line = unicodedata.normalize("NFKC", line)
    line = MD_STRIP_RE.sub("", line)
    return re.sub(r"\s+", "", line)


def scan(text: str):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        norm = normalize_line(line)
        if not norm:
            continue
        for label, pattern in VENDOR_PATTERNS:
            if pattern.search(norm):
                hits.append((lineno, label, line.strip()[:80]))
    return hits


def main():
    parser = argparse.ArgumentParser(description="供应商名纯净度门禁")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="待检查文件路径（如 办案画像.md）")
    group.add_argument("--text", help="直接传入的待检查文本（如中枢输出文本）")
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            print(f"输入错误：无法读取文件：{exc}", file=sys.stderr)
            return 2
    else:
        text = args.text

    if not text.strip():
        print("输入错误：待检查内容为空", file=sys.stderr)
        return 2

    hits = scan(text)
    if hits:
        print(f"❌ 拦截：发现 {len(hits)} 处供应商名/工具名，请改用能力语义表述后重跑。", file=sys.stderr)
        for lineno, label, snippet in hits:
            print(f"  第 {lineno} 行 [{label}]：{snippet}", file=sys.stderr)
        print("修正口径：写能力语义（如「企业工商信息查询连接器」「法规检索能力可用」），不写供应商名、工具名、server 名。", file=sys.stderr)
        return 1
    print("✅ 通过：未发现供应商名/工具名。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
