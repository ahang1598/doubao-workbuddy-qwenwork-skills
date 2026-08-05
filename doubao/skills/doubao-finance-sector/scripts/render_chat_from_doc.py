#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把结构化 doc.md 渲染成对话框展示用 chat_raw.md，并可校验加粗后的 chat.md。"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from generate_doc_markdown import GROUP_ORDER, load_doc_markdown

FIXED_RISK_NOTICE = "回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。"
FIXED_ENDING = '下一步是否为您生成飞书文档版？如果需要，请回复"生成飞书文档"。'
DIMENSION_ORDER = ["价格涨跌", "成交量能", "代表股表现", "估值位置"]
TABLE_SEPARATOR_RE = re.compile(r"^\|[:\-| ]+\|$")
MANDATORY_SECTION_HEADERS = [
    "## 现在有多热",
    "## 为什么涨 / 跌",
    "## 接下来盯什么",
    "## 风险提示",
]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _gap(lines: int = 2) -> list[str]:
    return [""] * lines


def _display_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else text


def _display_as_of(doc: dict[str, Any]) -> str:
    for item in doc.get("key_chips") or []:
        source = item.get("source") if isinstance(item, dict) else {}
        as_of = _display_timestamp((source or {}).get("as_of"))
        if as_of:
            return as_of
    return _display_timestamp(doc.get("timestamp"))


def _render_key_chips_table(chips: list[dict[str, Any]]) -> list[str]:
    """把核心展示值渲染成四列两行表格（指标 | 数值 | 指标 | 数值）。"""
    pairs = []
    for item in chips or []:
        label = _clean_text(item.get("label"))
        value = _clean_text(item.get("value"))
        if not label or not value:
            continue
        pairs.append((label, value))
    lines = [
        "| 指标 | 数值 | 指标 | 数值 |",
        "|:---:|:---:|:---:|:---:|",
    ]
    for i in range(0, len(pairs), 2):
        row = pairs[i : i + 2]
        cells = []
        for label, value in row:
            cells.extend([label, value])
        while len(cells) < 4:
            cells.append("")
        lines.append(f"| {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    return lines


def _opening_line(doc: dict[str, Any]) -> str:
    sector = _clean_text(doc.get("index_caliber") or doc.get("sector"))
    display_as_of = _display_as_of(doc)
    composite = _clean_text(doc.get("composite_score"))
    gauge = _clean_text(doc.get("gauge_pill"))
    return (
        f"目标概念板块：**{sector}**，数据截至 **{display_as_of}** 收盘；\n\n"
        f"本次以该板块成分中市值最大的 10 只代表股为样本观察短期热度，"
        f"综合热度 **{composite}/5（{gauge}）**。"
    )


def _render_dimensions_table(dimensions: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| 维度 | 数值 | 状态 | 解读 |",
        "|---|---|---|---|",
    ]
    for item in dimensions:
        lines.append(
            f"| {_clean_text(item.get('name'))} | {_clean_text(item.get('value'))} | {_clean_text(item.get('state'))} | {_clean_text(item.get('read'))} |"
        )
    return lines


def _render_catalyst(item: dict[str, Any]) -> list[str]:
    return [
        f"### {_clean_text(item.get('date'))}｜信息来源：{_clean_text(item.get('source_name'))}｜{_clean_text(item.get('title'))}",
        *_gap(),
        f"  📌 **事实**：{_clean_text(item.get('fact'))}",
        f"  🔗 **为什么重要**：{_clean_text(item.get('why'))}",
        f"  🔍 **后续验证**：{_clean_text(item.get('verify'))}",
    ]


def _group_line(name: str, groups: dict[str, Any]) -> str:
    raw = (groups or {}).get(name) or {}
    feature = _clean_text(raw.get("feature"))
    stocks = [str(stock).strip() for stock in (raw.get("stocks") or []) if str(stock).strip()]
    if not stocks:
        return f"- **{name}** ：无。"
    prefix = f"（{'、'.join(stocks)}）"
    if not feature or feature == "无。":
        return f"- **{name}** ：{prefix}。"
    return f"- **{name}** ：{prefix}{feature}"


def _format_sources(items: list[dict[str, Any]], max_sources: int) -> list[str]:
    lines: list[str] = []
    public_sources = []
    has_seed = False
    for item in items or []:
        name = _clean_text(item.get("name"))
        title = _clean_text(item.get("title"))
        date = _clean_text(item.get("date"))
        url = _clean_text(item.get("url"))
        if name == "seed_finance_search":
            has_seed = True
            continue
        if not name:
            continue
        label = name
        if title:
            label += f"：{title}"
        if date:
            label += f"，{date}"
        text = f"- [{label}]({url})" if url else f"- {label}"
        public_sources.append(text)
    lines.extend(public_sources[:max_sources])
    if has_seed or True:
        lines.append("- 同花顺数据库：板块与代表股行情、成交、估值及近7个交易日数据。")
    return lines


def render_chat(
    doc: dict[str, Any],
    *,
    max_catalysts: int,
    max_signals: int,
    max_risks: int,
    max_sources: int,
) -> str:
    answer = doc.get("answer") or {}
    summaries = doc.get("section_summaries") or {}
    dimensions = list(doc.get("dimensions") or [])
    dimensions.sort(key=lambda item: DIMENSION_ORDER.index(item.get("name")) if item.get("name") in DIMENSION_ORDER else 99)
    catalysts = list(doc.get("catalysts") or [])
    watch_signals = list(doc.get("watch_signals") or [])
    risks = list(doc.get("risks") or [])
    groups = doc.get("divergence_groups") or {}
    selected_stocks = [str(stock).strip() for stock in (doc.get("selected_stocks") or []) if str(stock).strip()]

    lines = [
        FIXED_RISK_NOTICE,
        *_gap(),
        f"**结论**：{_clean_text(answer.get('conclusion'))}",
        *_gap(),
        f"**下一步**：{_clean_text(answer.get('next'))}",
        *_gap(),
        "---",
        *_gap(),
        _opening_line(doc),
        *_gap(),
    ]
    lines.extend(_render_key_chips_table(doc.get("key_chips") or []))
    lines.extend([
        *_gap(),
        f"本次选取的 10 只代表股：{'、'.join(selected_stocks)}。",
        *_gap(),
        "---",
        *_gap(),
        "## 现在有多热",
        *_gap(),
        _clean_text(summaries.get('heat')),
        *_gap(),
    ])
    lines.extend(_render_dimensions_table(dimensions))

    lines.extend([
        *_gap(),
        "## 为什么涨 / 跌",
        *_gap(),
        _clean_text(summaries.get('catalysts')),
        *_gap(),
    ])
    for item in catalysts[:max_catalysts]:
        lines.extend(_render_catalyst(item))
        lines.extend(_gap())

    lines.extend([
        "## 谁在动、谁没动",
        *_gap(),
        _clean_text(summaries.get('divergence')),
        *_gap(),
    ])
    for group_name in GROUP_ORDER:
        lines.append(_group_line(group_name, groups))

    lines.extend([
        *_gap(),
        "## 接下来盯什么",
        *_gap(),
        _clean_text(summaries.get('watch')),
        *_gap(),
    ])
    for idx, item in enumerate(watch_signals[:max_signals], start=1):
        tag = _clean_text(item.get("tag"))
        if tag:
            header = f"- **信号{idx} · {tag}**：{_clean_text(item.get('signal'))}"
        else:
            header = f"- **信号{idx}**：{_clean_text(item.get('signal'))}"
        lines.extend([
            header,
            f"  👀 **盯：** {_clean_text(item.get('watch'))}",
            f"  🟢 **改善：** {_clean_text(item.get('improve'))}",
            f"  ⚠️ **恶化：** {_clean_text(item.get('worsen'))}",
        ])

    lines.extend([
        *_gap(),
        "## 风险提示",
        *_gap(),
        _clean_text(summaries.get('risks')),
        *_gap(),
    ])
    for item in risks[:max_risks]:
        lines.extend([
            f"- **{_clean_text(item.get('title'))}**",
            f"  触发：{_clean_text(item.get('trigger'))}",
            f"  证伪：{_clean_text(item.get('invalidate'))}",
        ])

    lines.extend([
        *_gap(),
        "## 信息来源",
        *_gap(),
    ])
    lines.extend(_format_sources(doc.get("sources") or [], max_sources))
    lines.extend([
        *_gap(),
        FIXED_ENDING,
        *_gap(1),
    ])
    return "\n".join(lines)


def infer_final_output_path(doc_path: Path) -> Path:
    stem = doc_path.stem
    if stem.endswith("_doc"):
        stem = stem[: -len("_doc")]
    return doc_path.with_name(stem + "_chat.md")


def infer_raw_output_path(doc_path: Path) -> Path:
    stem = doc_path.stem
    if stem.endswith("_doc"):
        stem = stem[: -len("_doc")]
    return doc_path.with_name(stem + "_chat_raw.md")


def build_emphasis_prompt(chat_raw: str) -> str:
    return (
        "你将收到一份 Markdown 文本。\n"
        "你的任务：只对重点内容添加 Markdown 加粗标记 **。\n"
        "硬性要求：\n"
        "1. 只能插入 **，不能增加、删除、改写任何其他字符。\n"
        "2. 不能修改任何汉字、数字、标点、空格、换行。\n"
        "3. 不能调整标题、表格、列表、链接、段落顺序。\n"
        "4. 第一行固定风险提示必须原样保留。\n"
        "5. 最后一行固定引导语必须原样保留。\n"
        "6. 输出必须是完整 Markdown 全文，不要解释，不要代码块，不要前后缀说明。\n"
        "7. 优先加粗：结论词、动作词、关键数字、时间点、风险触发词、催化核心事实。\n"
        "8. 避免过度加粗，每行最多 1-3 处。\n\n"
        "9. 必须满足最低覆盖：`结论` 行正文至少 1 处、`下一步` 行正文至少 1 处；"
        "`现在有多热`、`为什么涨 / 跌`、`接下来盯什么`、`风险提示` 四个模块正文各至少 1 处；"
        "每条催化正文、每条信号、每条风险各至少 1 处。\n\n"
        "以下是待处理的 Markdown 全文：\n\n"
        f"{chat_raw}"
    )


def _non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _collect_inserted_star_segments(raw: str, emphasized: str) -> list[str] | None:
    segments: list[str] = []
    current: list[str] = []
    i = 0
    j = 0
    while i < len(raw) and j < len(emphasized):
        if raw[i] == emphasized[j]:
            if current:
                segments.append("".join(current))
                current = []
            i += 1
            j += 1
            continue
        if emphasized[j] == "*":
            current.append("*")
            j += 1
            continue
        return None
    if current:
        segments.append("".join(current))
    if i != len(raw):
        return None
    tail = emphasized[j:]
    if tail:
        if any(ch != "*" for ch in tail):
            return None
        segments.append(tail)
    return segments


def validate_emphasized_chat(raw: str, emphasized: str) -> list[str]:
    errors: list[str] = []
    if "```" in emphasized:
        errors.append("候选 chat.md 不得包含代码块。")
    raw_lines = raw.splitlines()
    emphasized_lines = emphasized.splitlines()
    inserted_segments = _collect_inserted_star_segments(raw, emphasized)
    if inserted_segments is None:
        errors.append("候选 chat.md 除插入 `**` 外还改动了其他字符。")
    else:
        invalid = [seg for seg in inserted_segments if len(seg) % 2 != 0]
        if invalid:
            errors.append("候选 chat.md 新增的星号必须成对出现，只允许插入 `**`。")
    if not raw_lines or not emphasized_lines:
        errors.append("chat 内容为空。")
        return errors
    if emphasized_lines[0] != FIXED_RISK_NOTICE:
        errors.append("候选 chat.md 第一行固定风险提示被改动。")
    raw_tail = _non_empty_lines(raw)
    emphasized_tail = _non_empty_lines(emphasized)
    if not raw_tail or not emphasized_tail or emphasized_tail[-1] != FIXED_ENDING:
        errors.append("候选 chat.md 最后一行固定引导语被改动。")
    if len(raw_lines) != len(emphasized_lines):
        errors.append("候选 chat.md 行数被改动；只允许插入 `**`。")
        return errors
    for idx, (raw_line, emph_line) in enumerate(zip(raw_lines, emphasized_lines), start=1):
        if raw_line.startswith("## ") and raw_line != emph_line:
            errors.append(f"第 {idx} 行标题被改动：`##` 标题必须逐字保留。")
        if TABLE_SEPARATOR_RE.match(raw_line) and raw_line != emph_line:
            errors.append(f"第 {idx} 行表格分隔线被改动。")
    raw_urls = re.findall(r"\]\(([^)]+)\)", raw)
    emph_urls = re.findall(r"\]\(([^)]+)\)", emphasized)
    if raw_urls != emph_urls:
        errors.append("候选 chat.md 的链接 URL 被改动。")
    return errors


def _find_line_index(lines: list[str], prefix: str) -> int | None:
    for idx, line in enumerate(lines):
        if line.startswith(prefix):
            return idx
    return None


def _find_section_range(lines: list[str], header: str) -> tuple[int, int] | None:
    start = _find_line_index(lines, header)
    if start is None:
        return None
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return start + 1, end


def _has_line_level_emphasis(raw_lines: list[str], emphasized_lines: list[str], start: int, end: int) -> bool:
    for idx in range(start, end):
        if raw_lines[idx].strip() and raw_lines[idx] != emphasized_lines[idx]:
            return True
    return False


def _collect_blocks(lines: list[str], start: int, end: int, prefix: str) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    idx = start
    while idx < end:
        if lines[idx].startswith(prefix):
            block_start = idx
            idx += 1
            while idx < end and not lines[idx].startswith(prefix):
                idx += 1
            blocks.append((block_start, idx))
            continue
        idx += 1
    return blocks


def validate_effective_emphasis(raw: str, emphasized: str) -> list[str]:
    errors: list[str] = []
    if raw == emphasized:
        return ["候选 chat.md 与 chat_raw.md 完全一致，未执行重点加粗。"]
    raw_lines = raw.splitlines()
    emphasized_lines = emphasized.splitlines()
    if len(raw_lines) != len(emphasized_lines):
        return []

    for prefix, label in [("**结论**：", "结论"), ("**下一步**：", "下一步")]:
        idx = _find_line_index(raw_lines, prefix)
        if idx is None:
            errors.append(f"找不到“{label}”行，无法检查有效强调。")
            continue
        if raw_lines[idx] == emphasized_lines[idx]:
            errors.append(f"“{label}”行缺少新增重点加粗。")

    for header in MANDATORY_SECTION_HEADERS:
        section_range = _find_section_range(raw_lines, header)
        if section_range is None:
            errors.append(f"找不到模块“{header}”，无法检查有效强调。")
            continue
        start, end = section_range
        if not _has_line_level_emphasis(raw_lines, emphasized_lines, start, end):
            errors.append(f"模块“{header}”正文缺少新增重点加粗。")

    catalyst_range = _find_section_range(raw_lines, "## 为什么涨 / 跌")
    if catalyst_range is not None:
        for idx, (block_start, block_end) in enumerate(_collect_blocks(raw_lines, *catalyst_range, "### "), start=1):
            if not _has_line_level_emphasis(raw_lines, emphasized_lines, block_start + 1, block_end):
                errors.append(f"第 {idx} 条催化正文缺少新增重点加粗。")

    signal_range = _find_section_range(raw_lines, "## 接下来盯什么")
    if signal_range is not None:
        for idx, (block_start, block_end) in enumerate(_collect_blocks(raw_lines, *signal_range, "- **信号"), start=1):
            if not _has_line_level_emphasis(raw_lines, emphasized_lines, block_start, block_end):
                errors.append(f"第 {idx} 条信号缺少新增重点加粗。")

    risk_range = _find_section_range(raw_lines, "## 风险提示")
    if risk_range is not None:
        for idx, (block_start, block_end) in enumerate(_collect_blocks(raw_lines, *risk_range, "- **"), start=1):
            if not _has_line_level_emphasis(raw_lines, emphasized_lines, block_start, block_end):
                errors.append(f"第 {idx} 条风险缺少新增重点加粗。")

    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="把结构化 doc.md 渲染为 chat_raw.md，并校验候选 chat.md。")
    ap.add_argument("doc_md", help="结构化 doc.md")
    ap.add_argument("-o", "--output", help="输出最终 chat.md 路径；未传 `--emphasized-input` 时兼容旧行为，直接写当前渲染结果")
    ap.add_argument("--raw-output", help="输出稳定底稿 chat_raw.md 路径")
    ap.add_argument("--emphasized-input", help="候选 chat.md 路径；应只在 chat_raw.md 基础上插入 `**`")
    ap.add_argument("--prompt-output", help="把给大模型/agent 的强调提示词写入文件")
    ap.add_argument("--style", default="default", choices=["default"], help="展示模板样式")
    ap.add_argument("--max-catalysts", type=int, default=3, help="最多展示多少条催化")
    ap.add_argument("--max-signals", type=int, default=3, help="最多展示多少条观察信号")
    ap.add_argument("--max-risks", type=int, default=3, help="最多展示多少条风险")
    ap.add_argument("--max-sources", type=int, default=4, help="最多展示多少条公开来源")
    args = ap.parse_args(argv)

    doc_path = Path(args.doc_md)
    if not doc_path.exists():
        print(f"[错误] 找不到 doc.md: {doc_path}")
        return 2
    doc = load_doc_markdown(doc_path)
    chat_raw = render_chat(
        doc,
        max_catalysts=max(1, args.max_catalysts),
        max_signals=max(1, args.max_signals),
        max_risks=max(1, args.max_risks),
        max_sources=max(1, args.max_sources),
    )
    if args.prompt_output:
        prompt_path = Path(args.prompt_output)
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(build_emphasis_prompt(chat_raw), encoding="utf-8")
        print(f"[信息] 已生成强调提示词: {prompt_path}")
    raw_path = Path(args.raw_output) if args.raw_output else None
    if raw_path:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(chat_raw, encoding="utf-8")
        print(f"[信息] 已生成 chat_raw.md: {raw_path}")
    if args.emphasized_input:
        emph_path = Path(args.emphasized_input)
        if not emph_path.exists():
            print(f"[错误] 找不到候选 chat.md: {emph_path}")
            return 2
        emphasized = emph_path.read_text(encoding="utf-8")
        errors = validate_emphasized_chat(chat_raw, emphasized)
        errors.extend(validate_effective_emphasis(chat_raw, emphasized))
        for msg in errors:
            print(f"[错误] {msg}")
        if errors:
            print(f"汇总: {len(errors)} 错误。候选 chat.md 未通过展示层校验。")
            return 1
        out_path = Path(args.output) if args.output else infer_final_output_path(doc_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(emphasized, encoding="utf-8")
        print(f"[信息] 候选 chat.md 校验通过，已生成最终 chat.md: {out_path}")
        return 0
    out_path = Path(args.output) if args.output else (raw_path or infer_final_output_path(doc_path))
    if args.output:
        print("[错误] 未提供 --emphasized-input 时，只允许通过 --raw-output 生成 chat_raw.md；禁止用 --output 直接落展示稿。")
        return 2
    if out_path.name.endswith("_chat.md") and not out_path.name.endswith("_chat_raw.md"):
        print("[错误] 生成最终 chat.md 必须提供 --emphasized-input；未校验的 chat_raw.md 不能直接作为最终输出。")
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(chat_raw, encoding="utf-8")
    print(f"[信息] 已生成当前渲染结果: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
