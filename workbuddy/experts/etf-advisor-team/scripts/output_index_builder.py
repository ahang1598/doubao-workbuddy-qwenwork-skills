#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OutputReport INDEX 自动生成器。

每次生成报告后可运行一次，扫描 OutputReport/ 下的所有 .md/.html/.pdf，
按日期倒序写入 INDEX.md，方便跨环境（Cowork/浏览器无显示等）的用户快速找到历史报告。

用法：
  python output_index_builder.py --dir c:/path/to/OutputReport

集成建议：agent 完成 Step 8 后调用一次。
"""

from __future__ import annotations

# --- UTF-8 bootstrap ---
import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_dir = _bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))
if _bootstrap_dir not in _bootstrap_sys.path:
    _bootstrap_sys.path.insert(0, _bootstrap_dir)
try:
    from _utf8_bootstrap import enable_utf8_io as _bootstrap_enable
    _bootstrap_enable()
except Exception:
    pass
# --- end UTF-8 bootstrap ---

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List


CATEGORY_RULES = [
    # (正则模式, 分类名称, emoji)
    (re.compile(r"基金投资组合推荐报告|基金组合推荐报告"), "完整组合推荐 (Full)", "📦"),
    (re.compile(r"(场内|场外|ETF).*基金.*推荐报告"), "单产品形态推荐 (Sector/Compare)", "🎯"),
    (re.compile(r"基金对比推荐报告"), "基金对比 (Compare)", "⚖️"),
    (re.compile(r"基金推荐报告"), "行业/主题推荐 (Sector)", "🏭"),
    (re.compile(r"A股推荐报告"), "A 股推荐报告", "📈"),
    (re.compile(r"ETF买卖决策报告"), "ETF 买卖决策报告", "💹"),
    (re.compile(r"交易决策报告"), "股票交易决策报告", "💼"),
    (re.compile(r"行业分析报告"), "行业分析报告", "🏗️"),
    (re.compile(r".*"), "其他", "📄"),
]


def categorize(name: str) -> tuple:
    for pat, cat, emoji in CATEGORY_RULES:
        if pat.search(name):
            return cat, emoji
    return "其他", "📄"


def main() -> int:
    parser = argparse.ArgumentParser(description="OutputReport 索引生成器")
    parser.add_argument("--dir", required=True, help="OutputReport 目录的绝对路径")
    parser.add_argument("--limit", type=int, default=0, help="每个分类最多列出多少条（0=全部）")
    args = parser.parse_args()

    report_dir = Path(args.dir).resolve()
    if not report_dir.is_dir():
        print(f"[错误] 目录不存在: {report_dir}", file=sys.stderr)
        return 2

    # 收集所有报告文件
    extensions = {".md", ".html", ".pdf", ".xlsx"}
    files: List[Path] = []
    for p in report_dir.iterdir():
        if p.is_file() and p.suffix.lower() in extensions and p.name != "INDEX.md":
            files.append(p)

    # 按文件名的"词干"（去掉扩展名和尾部的 _V2 之类）分组，同一报告的 md/html/pdf 合并一行
    stems: Dict[str, Dict[str, Path]] = defaultdict(dict)
    for p in files:
        stem = p.stem
        ext = p.suffix.lower().lstrip(".")
        stems[stem][ext] = p

    # 每个 stem 以最新 mtime 排序
    stem_list = sorted(stems.items(), key=lambda x: -max(p.stat().st_mtime for p in x[1].values()))

    # 按类别分组
    by_cat: Dict[str, List] = defaultdict(list)
    cat_emojis: Dict[str, str] = {}
    for stem, ext_map in stem_list:
        cat, emoji = categorize(stem)
        by_cat[cat].append((stem, ext_map))
        cat_emojis[cat] = emoji

    # 生成 Markdown
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# OutputReport 索引",
        "",
        f"> 自动生成于 {now} | 共 {len(stems)} 份报告 | "
        f"由 `scripts/output_index_builder.py` 维护",
        "",
        "## 使用说明",
        "",
        "- 本索引按类别分组展示工作区 `OutputReport/` 目录下所有报告",
        "- 每份报告优先链接 HTML（若存在），其次 MD、PDF、XLSX",
        "- 浏览器无显示的环境（Cowork/CI 等）：用 `preview_url` 工具打开 `.html` 链接，或直接阅读 `.md`",
        "- 重新生成：`python scripts/output_index_builder.py --dir {WS}/OutputReport`",
        "",
    ]

    # 固定顺序（完整组合优先）
    ordered_cats = [
        "完整组合推荐 (Full)",
        "单产品形态推荐 (Sector/Compare)",
        "基金对比 (Compare)",
        "行业/主题推荐 (Sector)",
        "A 股推荐报告",
        "ETF 买卖决策报告",
        "股票交易决策报告",
        "行业分析报告",
        "其他",
    ]
    for cat in ordered_cats:
        items = by_cat.get(cat, [])
        if not items:
            continue
        emoji = cat_emojis.get(cat, "📄")
        lines.append(f"## {emoji} {cat}（{len(items)} 份）")
        lines.append("")
        lines.append("| 报告名 | MD | HTML | PDF | XLSX | 最新修改时间 |")
        lines.append("|--------|----|----|-----|------|-------------|")

        display_items = items if args.limit == 0 else items[: args.limit]
        for stem, ext_map in display_items:
            mtime = max(p.stat().st_mtime for p in ext_map.values())
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

            def link(ext: str) -> str:
                p = ext_map.get(ext)
                if p is None:
                    return "—"
                return f"[{ext.upper()}]({p.name})"

            lines.append(
                f"| {stem} | {link('md')} | {link('html')} | "
                f"{link('pdf')} | {link('xlsx')} | {mtime_str} |"
            )
        if args.limit and len(items) > args.limit:
            lines.append(f"| ...（另有 {len(items) - args.limit} 份未列出，本分类共 {len(items)} 份） | | | | | |")
        lines.append("")

    index_path = report_dir / "INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[成功] 索引已生成: {index_path}（共 {len(stems)} 份报告，{len(by_cat)} 个类别）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
