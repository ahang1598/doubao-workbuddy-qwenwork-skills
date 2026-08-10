#!/usr/bin/env python3
"""Render a Feishu-friendly SVG overview board for a medical monitoring report.

The renderer intentionally uses only SVG primitives supported by Feishu
whiteboards: rect, line, text, tspan and g.  It has no third-party dependency.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


CANVAS_WIDTH = 1600
FRAME_X = 34
FRAME_Y = 28
CONTENT_X = 112
HEADER_Y = 96
FONT = "PingFang SC,Microsoft YaHei,Arial,sans-serif"
DELIVERABLE_SUPPORT_LEVELS = {"snippet", "abstract", "official_full"}
FORBIDDEN_EMPTY_MARKERS = (
    "仅题录，结果未核验",
    "本次仅取得题名与题录信息，研究对象、设计、结果和临床意义尚未核验",
)

CATEGORIES = (
    {
        "key": "news",
        "title": "最新医学资讯",
        "icon": "N",
        "fill": "#FFF8E8",
        "header": "#FDECC8",
        "stroke": "#E7C16B",
        "accent": "#A16207",
    },
    {
        "key": "guideline",
        "title": "共识、指南与监管",
        "icon": "G",
        "fill": "#F5F3FF",
        "header": "#EDE9FE",
        "stroke": "#C4B5FD",
        "accent": "#6D28D9",
    },
    {
        "key": "research",
        "title": "研究进展",
        "icon": "R",
        "fill": "#ECFDF5",
        "header": "#D1FAE5",
        "stroke": "#86D7B0",
        "accent": "#047857",
    },
)


def _repair_unescaped_value_quotes(raw_text: str) -> str:
    """Repair common prose quotes without trying to become a general JSON5 parser.

    This fallback runs only after strict JSON parsing fails. Inside a JSON string,
    a quote followed by ordinary prose cannot legally close the string, so it is
    safe to treat that quote as a literal character. Structural quotes before
    ``:``, ``,`` , ``]`` or ``}`` remain unchanged.
    """
    repaired: list[str] = []
    in_string = False
    escaped = False
    length = len(raw_text)

    for index, char in enumerate(raw_text):
        if not in_string:
            repaired.append(char)
            if char == '"':
                in_string = True
            continue

        if escaped:
            repaired.append(char)
            escaped = False
            continue
        if char == "\\":
            repaired.append(char)
            escaped = True
            continue
        if char != '"':
            repaired.append(char)
            continue

        next_index = index + 1
        while next_index < length and raw_text[next_index].isspace():
            next_index += 1
        next_char = raw_text[next_index] if next_index < length else ""
        if not next_char or next_char in ":,]}":
            repaired.append(char)
            in_string = False
        else:
            repaired.append('\\"')

    return "".join(repaired)


def load_payload(input_path: Path) -> tuple[dict[str, Any], bool]:
    """Load strict JSON, with one conservative repair for prose double quotes."""
    raw_text = input_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
        return payload, False
    except json.JSONDecodeError as original_error:
        repaired_text = _repair_unescaped_value_quotes(raw_text)
        if repaired_text == raw_text:
            raise original_error
        try:
            payload = json.loads(repaired_text)
        except json.JSONDecodeError:
            raise original_error
        return payload, True


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def normalize_display_id(value: Any, fallback: str = "") -> str:
    """Normalize common visual variants without making them an acceptance gate."""
    text = " ".join(str(value or "").split()).strip("【】[]").strip()
    match = re.fullmatch(r"([A-Za-z\u4e00-\u9fff]{1,12})\s*[-－—]\s*(\d{1,3})", text)
    if not match:
        return fallback
    return f"{match.group(1)}-{int(match.group(2)):02d}"


def display_width(text: str) -> float:
    width = 0.0
    for char in text:
        if char == "\t":
            width += 2
        elif unicodedata.east_asian_width(char) in {"W", "F", "A"}:
            width += 2
        else:
            width += 1
    return width


def wrap_text(value: Any, max_width: float) -> list[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return [""]

    tokens = re.findall(
        r"[A-Za-z0-9]+(?:[-–—/.'’:+][A-Za-z0-9]+)*|\s+|.",
        text,
    )
    lines: list[str] = []
    current = ""
    for token in tokens:
        if token.isspace():
            if current and not current.endswith(" "):
                current += " "
            continue
        candidate = current + token
        if current and display_width(candidate) > max_width:
            lines.append(current.rstrip())
            current = token
        else:
            current = candidate
        while display_width(current) > max_width:
            split_at = 1
            while (
                split_at < len(current)
                and display_width(current[: split_at + 1]) <= max_width
            ):
                split_at += 1
            lines.append(current[:split_at].rstrip())
            current = current[split_at:].lstrip()
    if current or not lines:
        lines.append(current.rstrip())
    return lines


def text_node(
    x: float,
    y: float,
    lines: list[str],
    *,
    size: int = 22,
    color: str = "#1F2937",
    weight: int = 400,
    line_height: int | None = None,
    anchor: str = "start",
) -> str:
    line_height = line_height or int(size * 1.45)
    tspans = []
    for index, line in enumerate(lines):
        dy = "0" if index == 0 else str(line_height)
        tspans.append(
            f'<tspan x="{x:.0f}" dy="{dy}">{esc(line)}</tspan>'
        )
    return (
        f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}">{"".join(tspans)}</text>'
    )


def category_key(value: Any) -> str:
    text = str(value or "").lower()
    if any(token in text for token in ("指南", "共识", "监管", "guideline", "consensus", "regulat")):
        return "guideline"
    if any(token in text for token in ("资讯", "新闻", "会议", "news", "brief")):
        return "news"
    if any(token in text for token in ("研究", "论文", "预印本", "research", "study", "preprint")):
        return "research"
    raise ValueError(
        f"unsupported item category: {value!r}; use news, guideline, or research, "
        "or provide a recognizable display_id/type"
    )


def display_type(raw: dict[str, Any], category: str) -> str:
    value = " ".join(
        str(raw.get("display_type") or raw.get("type") or "").split()
    )
    source_status = " ".join(str(raw.get("source_status") or "").split())
    combined = f"{value} {source_status}".lower()

    if category == "news":
        return "资讯"
    if category == "guideline":
        if any(token in combined for token in ("监管", "regulat", "approval", "safety")):
            return "监管"
        if any(token in combined for token in ("共识", "consensus")):
            return "共识"
        return "指南"
    if any(token in combined for token in ("预印本", "preprint")):
        return "预印本"
    return "研究"


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_items = payload.get("report_items")
    if not isinstance(raw_items, list):
        raise ValueError(
            "report_items must be a JSON array; legacy items input is forbidden"
        )

    items: list[dict[str, str]] = []
    seen_display_ids: set[str] = set()
    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index - 1}] must be an object")
        support_level = " ".join(
            str(raw.get("support_level") or "").split()
        )
        support_excerpt = " ".join(
            str(raw.get("support_excerpt") or "").split()
        )
        body_blocks = raw.get("body_blocks")
        if support_level not in DELIVERABLE_SUPPORT_LEVELS:
            raise ValueError(
                f"items[{index - 1}].support_level is not deliverable"
            )
        if not support_excerpt:
            raise ValueError(
                f"items[{index - 1}].support_excerpt is required"
            )
        if (
            not isinstance(body_blocks, list)
            or not any(str(block).strip() for block in body_blocks)
        ):
            raise ValueError(
                f"items[{index - 1}].body_blocks is required"
            )
        evidence_text = " ".join(
            (support_excerpt, *(str(block) for block in body_blocks))
        )
        if any(marker in evidence_text for marker in FORBIDDEN_EMPTY_MARKERS):
            raise ValueError(
                f"items[{index - 1}] contains an empty-item marker"
            )
        label = " ".join(
            str(raw.get("short_label") or raw.get("label") or "").split()
        )
        if not label:
            raise ValueError(f"items[{index - 1}].label is required")
        original_title = " ".join(
            str(
                raw.get("original_title")
                or raw.get("source_title")
                or raw.get("title")
                or ""
            ).split()
        )
        if not original_title:
            raise ValueError(f"items[{index - 1}].original_title is required")
        journal_name = " ".join(str(raw.get("journal_name") or "").split())
        preprint_platform = " ".join(
            str(raw.get("preprint_platform") or "").split()
        )
        source_name = " ".join(
            str(
                raw.get("source_name")
                or raw.get("source_organization")
                or raw.get("record_source")
                or raw.get("publisher")
                or ""
            ).split()
        )
        if journal_name:
            source_text = f"期刊：{journal_name}"
        elif preprint_platform:
            source_text = f"平台：{preprint_platform}"
        elif source_name:
            source_text = f"来源：{source_name}"
        else:
            raise ValueError(
                f"items[{index - 1}].source_name or source field is required"
            )
        source_date = " ".join(
            str(
                raw.get("delta_date")
                or raw.get("source_page_date")
                or raw.get("published_date")
                or ""
            ).split()
        )
        category_hint = raw.get("category")
        if category_hint is None or not str(category_hint).strip():
            category_hint = " ".join(
                str(
                    raw.get(field)
                    or ""
                )
                for field in ("display_id", "display_type", "type")
            )
        category = category_key(category_hint)
        item_type = display_type(raw, category)
        raw_display_id = str(raw.get("display_id") or "").strip()
        display_id = normalize_display_id(
            raw_display_id,
            fallback=f"{item_type}-{index:02d}",
        )
        if display_id in seen_display_ids:
            raise ValueError(f"duplicate display_id: {display_id}")
        seen_display_ids.add(display_id)
        source_url = str(raw.get("source_url") or raw.get("url") or "").strip()
        if not re.fullmatch(r"https?://[^\s<>]+", source_url, re.IGNORECASE):
            raise ValueError(f"items[{index - 1}].source_url is required")
        items.append(
            {
                "display_id": display_id,
                "category": category,
                "label": label,
                "original_title": original_title,
                "source_text": source_text,
                "source_date": source_date,
                "signal": " ".join(
                    str(raw.get("current_signal") or raw.get("signal") or "").split()
                ),
                "status": " ".join(str(raw.get("source_status") or "").split()),
                "url": source_url,
            }
        )

    summaries = payload.get("key_observations")
    if not isinstance(summaries, list):
        summaries = payload.get("summary_points")
    if not isinstance(summaries, list):
        summaries = []
    normalized_summaries: list[str] = []
    for raw in summaries:
        if isinstance(raw, dict):
            text = " ".join(str(raw.get("text") or "").split())
        else:
            text = " ".join(str(raw or "").split())
        if text:
            normalized_summaries.append(text)
    if not normalized_summaries:
        normalized_summaries = ["本期未提供可视化条目，具体状态见正文。"]

    empty_label = " ".join(str(payload.get("empty_label") or "本期暂无纳入条目").split())
    return {
        "topic": " ".join(str(payload.get("topic") or "医学主题").split()),
        "period": " ".join(str(payload.get("period") or "本期").split()),
        "summary": normalized_summaries[:4],
        "items": items,
        "empty_label": empty_label,
    }


def render(payload: dict[str, Any]) -> str:
    data = normalize_payload(payload)
    items = data["items"]
    inner_x = CONTENT_X
    inner_w = CANVAS_WIDTH - inner_x * 2
    parts: list[str] = []

    summary_lines: list[tuple[str, list[str]]] = []
    for summary in data["summary"]:
        summary_lines.append(("•", wrap_text(summary, 112)))
    summary_height = 54 + sum(max(1, len(lines)) * 31 + 7 for _, lines in summary_lines)

    header_y = HEADER_Y
    summary_y = 178
    cards_heading_y = summary_y + summary_height + 66
    cards_y = cards_heading_y + 40
    card_gap = 30
    card_w = (inner_w - card_gap * 2) / 3
    grouped: dict[str, list[dict[str, str]]] = {c["key"]: [] for c in CATEGORIES}
    for item in items:
        grouped[item["category"]].append(item)
    card_line_counts: dict[str, int] = {}
    for category in CATEGORIES:
        lines = 0
        category_items = grouped[category["key"]]
        if not category_items:
            lines = 1
        for item in category_items:
            lines += max(
                1,
                len(
                    wrap_text(
                        f'【{item["display_id"]}】 {item["label"]}',
                        34,
                    )
                ),
            )
        card_line_counts[category["key"]] = lines
    cards_h = max(226, 112 + max(card_line_counts.values(), default=1) * 31)

    matrix_heading_y = cards_y + cards_h + 66
    matrix_y = matrix_heading_y + 40
    matrix_header_h = 56
    col_gap = 24
    col_w = (inner_w - col_gap) / 2
    item_cells: list[dict[str, Any]] = []
    for item in items:
        title_lines = wrap_text(item["original_title"], 43)
        detail = " ｜ ".join(
            value for value in (item["source_text"], item["source_date"]) if value
        )
        detail_lines = wrap_text(detail, 46)
        cell_h = max(108, 32 + len(title_lines) * 27 + len(detail_lines) * 24)
        item_cells.append(
            {
                **item,
                "title_lines": title_lines,
                "detail_lines": detail_lines,
                "height": cell_h,
            }
        )
    row_heights: list[int] = []
    for start in range(0, len(item_cells), 2):
        row_heights.append(max(cell["height"] for cell in item_cells[start : start + 2]))
    matrix_body_h = sum(row_heights) if row_heights else 90
    footer_y = matrix_y + matrix_header_h + matrix_body_h + 62
    canvas_height = int(footer_y + 104)

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" '
        f'height="{canvas_height}" viewBox="0 0 {CANVAS_WIDTH} {canvas_height}">'
    )
    parts.append(f'<rect width="{CANVAS_WIDTH}" height="{canvas_height}" fill="#FFFFFF"/>')
    parts.append(
        f'<rect x="{FRAME_X}" y="{FRAME_Y}" '
        f'width="{CANVAS_WIDTH - FRAME_X * 2}" height="{canvas_height - FRAME_Y * 2}" '
        'rx="18" fill="#FFFFFF" stroke="#DDE3EA" stroke-width="2"/>'
    )

    parts.append(
        f'<rect x="{inner_x}" y="{header_y - 30}" width="42" height="42" '
        'rx="10" fill="#E8F7EF" stroke="#70C995"/>'
    )
    parts.append(text_node(inner_x + 21, header_y, ["M"], size=22, color="#16875B", weight=700, anchor="middle"))
    parts.append(
        text_node(
            inner_x + 58,
            header_y,
            [f'{data["topic"]}｜本期进展总览'],
            size=30,
            color="#111827",
            weight=700,
        )
    )
    parts.append(
        text_node(
            inner_x + inner_w,
            header_y,
            [data["period"]],
            size=18,
            color="#6B7280",
            weight=500,
            anchor="end",
        )
    )

    parts.append(
        f'<rect x="{inner_x}" y="{summary_y}" width="{inner_w}" height="{summary_height}" '
        'rx="12" fill="#F6F8FA"/>'
    )
    parts.append(text_node(inner_x + 28, summary_y + 39, ["核心观察"], size=21, color="#111827", weight=700))
    summary_text_y = summary_y + 76
    for bullet, lines in summary_lines:
        parts.append(text_node(inner_x + 34, summary_text_y, [bullet], size=20, color="#E7A21A", weight=700))
        parts.append(text_node(inner_x + 58, summary_text_y, lines, size=19, color="#374151", line_height=31))
        summary_text_y += max(1, len(lines)) * 31 + 7

    parts.append(text_node(inner_x, cards_heading_y, ["分类速览"], size=22, color="#111827", weight=700))
    for index, category in enumerate(CATEGORIES):
        x = inner_x + index * (card_w + card_gap)
        parts.append(
            f'<rect x="{x:.0f}" y="{cards_y}" width="{card_w:.0f}" height="{cards_h}" '
            f'rx="12" fill="{category["fill"]}" stroke="{category["stroke"]}" stroke-width="2"/>'
        )
        parts.append(
            f'<rect x="{x:.0f}" y="{cards_y}" width="{card_w:.0f}" height="58" '
            f'rx="12" fill="{category["header"]}"/>'
        )
        parts.append(
            f'<rect x="{x:.0f}" y="{cards_y + 46}" width="{card_w:.0f}" height="12" '
            f'fill="{category["header"]}"/>'
        )
        parts.append(
            f'<circle cx="{x + 30:.0f}" cy="{cards_y + 29}" r="14" '
            f'fill="{category["accent"]}"/>'
        )
        parts.append(
            text_node(x + 30, cards_y + 36, [category["icon"]], size=16, color="#FFFFFF", weight=700, anchor="middle")
        )
        count = len(grouped[category["key"]])
        parts.append(
            text_node(
                x + 54,
                cards_y + 37,
                [f'{category["title"]} · {count}'],
                size=20,
                color=category["accent"],
                weight=700,
            )
        )
        category_items = grouped[category["key"]]
        item_y = cards_y + 91
        if not category_items:
            parts.append(text_node(x + 26, item_y, [data["empty_label"]], size=18, color="#6B7280"))
        for item in category_items:
            lines = wrap_text(
                f'【{item["display_id"]}】 {item["label"]}',
                34,
            )
            parts.append(text_node(x + 25, item_y, ["•"], size=18, color=category["accent"], weight=700))
            parts.append(text_node(x + 46, item_y, lines, size=18, color="#26313F", line_height=31))
            item_y += len(lines) * 31

    parts.append(text_node(inner_x, matrix_heading_y, ["本期全部条目"], size=22, color="#111827", weight=700))
    parts.append(
        text_node(
            inner_x + inner_w,
            matrix_heading_y,
            ["逐条索引 · 编号对应正文"],
            size=16,
            color="#6B7280",
            weight=500,
            anchor="end",
        )
    )
    parts.append(
        f'<rect x="{inner_x}" y="{matrix_y}" width="{inner_w}" height="{matrix_header_h + matrix_body_h}" '
        'fill="#FFFFFF" stroke="#D8DEE7" stroke-width="2"/>'
    )
    parts.append(
        f'<rect x="{inner_x}" y="{matrix_y}" width="{inner_w}" height="{matrix_header_h}" fill="#F3F5F7"/>'
    )
    parts.append(text_node(inner_x + 24, matrix_y + 34, ["编号、原文标题与来源"], size=18, color="#374151", weight=700))

    current_y = matrix_y + matrix_header_h
    if not item_cells:
        parts.append(text_node(inner_x + 24, current_y + 54, [data["empty_label"]], size=19, color="#6B7280"))
    for row_index, row_h in enumerate(row_heights):
        if row_index % 2 == 1:
            parts.append(
                f'<rect x="{inner_x}" y="{current_y}" width="{inner_w}" height="{row_h}" fill="#FAFBFC"/>'
            )
        if row_index > 0:
            parts.append(
                f'<line x1="{inner_x}" y1="{current_y}" x2="{inner_x + inner_w}" y2="{current_y}" '
                'stroke="#E5E9EF" stroke-width="1"/>'
            )
        for col_index, cell in enumerate(item_cells[row_index * 2 : row_index * 2 + 2]):
            x = inner_x + col_index * (col_w + col_gap)
            palette = next(category for category in CATEGORIES if category["key"] == cell["category"])
            parts.append(
                f'<rect x="{x + 20:.0f}" y="{current_y + 20:.0f}" width="132" height="30" '
                f'rx="15" fill="{palette["header"]}"/>'
            )
            parts.append(
                text_node(
                    x + 86,
                    current_y + 41,
                    [f'【{cell["display_id"]}】'],
                    size=16,
                    color=palette["accent"],
                    weight=700,
                    anchor="middle",
                )
            )
            parts.append(
                text_node(
                    x + 166,
                    current_y + 42,
                    cell["title_lines"],
                    size=18,
                    color="#1F2937",
                    weight=600,
                    line_height=27,
                )
            )
            detail_y = current_y + 42 + len(cell["title_lines"]) * 27
            parts.append(
                text_node(
                    x + 166,
                    detail_y,
                    cell["detail_lines"],
                    size=16,
                    color="#6B7280",
                    line_height=24,
                )
            )
        current_y += row_h

    parts.append(
        f'<line x1="{inner_x + col_w + col_gap / 2:.0f}" y1="{matrix_y + matrix_header_h}" '
        f'x2="{inner_x + col_w + col_gap / 2:.0f}" y2="{matrix_y + matrix_header_h + matrix_body_h}" '
        'stroke="#E5E9EF" stroke-width="1"/>'
    )
    parts.append(
        text_node(
            inner_x,
            footer_y,
            ["编号与正文条目一一对应 · 证据成熟度与原始来源请见正文"],
            size=16,
            color="#8A94A3",
        )
    )
    parts.append(
        text_node(
            inner_x + inner_w,
            footer_y,
            ["内容由 AI 生成"],
            size=15,
            color="#A0A8B4",
            anchor="end",
        )
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_feishu_demo_document(payload: dict[str, Any], svg: str) -> str:
    """Wrap a rendered board in a small XML document for Feishu regression."""
    data = normalize_payload(payload)
    summary_items = "".join(
        f"<li><p>{esc(summary)}</p></li>" for summary in data["summary"]
    )
    return (
        f"<title>{esc(data['topic'])}｜总览画板视觉回归</title>\n"
        "<h1>本周总结</h1>\n"
        '<callout emoji="💡" background-color="light-blue" border-color="blue">\n'
        f"<ul>{summary_items}</ul>\n"
        "</callout>\n"
        "<h1>本期进展总览</h1>\n"
        '<whiteboard type="svg" path="@overview.svg"></whiteboard>\n'
        "<h1>灵感启发</h1>\n"
        '<callout emoji="💡" background-color="light-yellow" border-color="yellow">'
        "<p><b>验证实施条件。</b> 将外部验证结果与真实世界工作流放在同一研究框架中观察。</p>"
        "</callout>\n"
        '<callout emoji="🔎" background-color="light-blue" border-color="blue">'
        "<p><b>关注平台可迁移性。</b> 比较不同检测平台阈值及跨人群校准策略。</p>"
        "</callout>\n"
        "<p>本页仅用于验证画板与 callout 的飞书呈现。</p>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON payload path")
    parser.add_argument("--output", required=True, help="SVG output path")
    parser.add_argument(
        "--feishu-doc-output",
        help="Optional Feishu XML demo document path for visual regression",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload, input_repaired = load_payload(input_path)
    svg = render(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")
    if args.feishu_doc_output:
        doc_output = Path(args.feishu_doc_output)
        doc_output.parent.mkdir(parents=True, exist_ok=True)
        doc_output.write_text(
            render_feishu_demo_document(payload, svg),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output_path),
                "feishu_doc_output": args.feishu_doc_output,
                "items": len(normalize_payload(payload)["items"]),
                "input_repaired": input_repaired,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
