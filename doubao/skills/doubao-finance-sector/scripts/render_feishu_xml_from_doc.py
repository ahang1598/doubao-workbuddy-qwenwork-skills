#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把结构化 doc.md 渲染成可写入飞书文档的 lark-doc XML。"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from generate_doc_markdown import GROUP_ORDER, load_doc_markdown

DISCLAIMER_LINES = [
    "以上内容为AI自动生成或AI辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。",
    "以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误，历史数据、历史业绩、回测结果及情景假设均不代表未来表现。",
    "用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖以上内容而作出的决策及其后果，由用户自行承担。",
]
RANK_WORDS = ["冷清", "温和", "活跃", "高热", "过热"]
GROUP_META = {
    "放量上攻": ("🟢", "量价齐升 · 参与充分"),
    "缩量上行": ("🟢", "量能不足 · 持续性存疑"),
    "缩量回调": ("🟢", "抛压衰竭 · 多近企稳"),
    "放量杀跌": ("🟢", "抛压沉重 · 资金出逃"),
}
DIMENSION_NAME_MAP = {
    "价格涨跌": "价格涨跌",
    "涨跌幅": "价格涨跌",
    "成交量能": "成交量能",
    "成交额": "成交量能",
    "代表股表现": "代表股表现",
    "情绪": "代表股表现",
    "估值位置": "估值位置",
    "估值": "估值位置",
}
DIMENSION_ORDER = ["价格涨跌", "成交量能", "代表股表现", "估值位置"]


def esc(text: Any) -> str:
    s = "" if text is None else str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace("\n", "<br/>")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace("%", "").replace("亿", "").replace("倍", "").replace("点", "").replace(",", "")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def with_direction(value: Any) -> str:
    num = _to_float(value)
    if num is None:
        return esc(value)
    if num > 0:
        return f'上涨 +{num:.2f}%'
    if num < 0:
        return f'下跌 {num:.2f}%'
    return "0.00%"


def colored_change(value: Any) -> str:
    num = _to_float(value)
    if num is None:
        return f"<b>{esc(value)}</b>"
    text = with_direction(num)
    if num > 0:
        return f'<b><span text-color="red">{esc(text)}</span></b>'
    if num < 0:
        return f'<b><span text-color="green">{esc(text)}</span></b>'
    return f"<b>{esc(text)}</b>"


def progress_bar(score: Any, color: str) -> str:
    try:
        s = int(round(float(score)))
    except (TypeError, ValueError):
        s = 0
    s = max(0, min(5, s))
    filled = s * 2
    return f'<span text-color="{color}">{"█" * filled}</span><span text-color="light-gray">{"█" * (10 - filled)}</span>'


def heat_scale(score: Any) -> str:
    try:
        s = int(round(float(score)))
    except (TypeError, ValueError):
        s = 0
    parts = []
    for idx, word in enumerate(RANK_WORDS, start=1):
        if idx == s:
            parts.append(f'<b><span text-color="red">[{word}]</span></b>')
        else:
            parts.append(word)
    return " ── ".join(parts)


def quadrant_pill(info_score: Any, market_score: Any) -> tuple[str, str]:
    try:
        info = int(round(float(info_score)))
        market = int(round(float(market_score)))
    except (TypeError, ValueError):
        return "双轨偏冷", "信息面与行情面均低迷，板块处于低关注状态"
    if info >= 3 and market >= 3:
        return "双轨偏热", "信息与行情共振，市场关注度高且资金参与积极"
    if info >= 3 and market < 3:
        return "信息领先", "政策/消息面热度领先于价格表现，预期走在行情前面"
    if info < 3 and market >= 3:
        return "行情领先", "价格/成交热度领先于信息面，可能存在纯资金驱动"
    return "双轨偏冷", "信息面与行情面均低迷，板块处于低关注状态"


def section_title(title: str) -> str:
    return f'<hr/>\n<h1 align="left"><span text-color="orange">{esc(title)}</span></h1>'


def render_key_chips(chips: list[dict[str, Any]]) -> str:
    chips = list(chips or [])
    while len(chips) < 4:
        chips.append({"label": "", "value": "", "unit": ""})
    col_pairs = ((chips[0], chips[2]), (chips[1], chips[3]))
    cols = []
    for pair in col_pairs:
        items = []
        for chip in pair:
            label = str(chip.get("label") or "")
            if "PE(TTM)" in label:
                label = label.replace("（代表股）", "").replace("当日 ", "").replace("当日", "").strip()
            value = str(chip.get("value") or "")
            if chip.get("metric_key") in {"daily_change", "change_7d"}:
                value = with_direction(value)
                unit = ""
            else:
                unit = str(chip.get("unit") or "")
                if value.endswith(unit):
                    unit = ""
                value = value.replace(" ", "")
                unit = unit.replace(" ", "")
            items.append(
                "<callout emoji=\"📊\" background-color=\"light-gray\" border-color=\"gray\">"
                f"<p><span text-color=\"gray\">{esc(label)}</span></p>"
                f"<p><b>{esc(value)}{esc(unit)}</b></p>"
                "</callout>"
            )
        cols.append('<column width-ratio="0.5">\n' + "\n".join(items) + "\n</column>")
    return "<grid>\n" + "\n".join(cols) + "\n</grid>"


def render_dimensions(dimensions: list[dict[str, Any]]) -> str:
    normalized = []
    for dim in dimensions or []:
        item = dict(dim)
        item["name"] = DIMENSION_NAME_MAP.get(str(item.get("name") or "").strip(), str(item.get("name") or "").strip())
        normalized.append(item)
    normalized.sort(key=lambda item: DIMENSION_ORDER.index(item.get("name")) if item.get("name") in DIMENSION_ORDER else 99)

    items = []
    for dim in normalized:
        items.append(
            "<callout emoji=\"🔴\" background-color=\"light-gray\" border-color=\"gray\">"
            f"<p><b>{esc(dim.get('name'))}  ·  {esc(dim.get('state'))}</b></p>"
            f"<p><b>关键数据：</b>{esc(dim.get('value'))}</p>"
            f"<p>{esc(dim.get('read'))}</p>"
            "</callout>"
        )
    while len(items) < 4:
        items.append(
            "<callout emoji=\"🔴\" background-color=\"light-gray\" border-color=\"gray\">"
            "<p><b>暂无  ·  暂无</b></p><p><b>关键数据：</b>暂无</p><p>暂无</p></callout>"
        )
    top = '<grid>\n<column width-ratio="0.5">\n' + items[0] + '\n</column>\n<column width-ratio="0.5">\n' + items[1] + "\n</column>\n</grid>"
    bottom = '<grid>\n<column width-ratio="0.5">\n' + items[2] + '\n</column>\n<column width-ratio="0.5">\n' + items[3] + "\n</column>\n</grid>"
    return top + "\n" + bottom


def render_catalysts(catalysts: list[dict[str, Any]]) -> str:
    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        m = re.search(r"(\d{1,2})月(\d{1,2})日", str(item.get("date") or ""))
        if not m:
            return (0, 0)
        return int(m.group(1)), int(m.group(2))
    blocks = []
    for item in sorted(catalysts or [], key=sort_key, reverse=True):
        category = str(item.get("category") or "")
        if category == "政策":
            category = "政策/产业"
        link = ""
        if str(item.get("url") or "").strip():
            link = f' <a href="{esc(item.get("url"))}">查看原文 ↗</a>'
        blocks.append(
            f'<h3 align="left"><span text-color="orange">{esc(item.get("tone"))} · {esc(item.get("date"))} · {esc(category)}</span></h3>\n'
            f'<p align="left"><b>{esc(item.get("title"))}</b>{link}</p>\n'
            f'<p align="left"><span text-color="gray">信息来源：{esc(item.get("source_name"))}</span></p>\n'
            f'<p align="left">{esc(item.get("fact"))}</p>\n'
            "<blockquote>\n"
            f"<p><b>为什么重要：</b>{esc(item.get('why'))}</p>\n"
            f"<p><b>后续验证：</b>{esc(item.get('verify'))}</p>\n"
            "</blockquote>"
        )
    return "\n".join(blocks)


def render_stocks_table(stocks: list[dict[str, Any]]) -> str:
    rows = []
    def stock_key(item: dict[str, Any]) -> float:
        try:
            return float(item.get("change") or 0)
        except (TypeError, ValueError):
            return 0.0
    for item in sorted(stocks or [], key=stock_key, reverse=True):
        turnover = "0.00"
        turnover_7d = "0.00"
        try:
            if str(item.get("turnover", "")).strip():
                turnover = f"{float(item.get('turnover') or 0):.2f}"
            if str(item.get("turnover_7d", "")).strip():
                turnover_7d = f"{float(item.get('turnover_7d') or 0):.2f}"
        except (TypeError, ValueError):
            pass
        rows.append(
            "<tr>"
            f"<td background-color=\"light-gray\" vertical-align=\"middle\"><p align=\"center\">{esc(item.get('name'))}</p></td>"
            f"<td vertical-align=\"middle\"><p align=\"center\">{esc(item.get('role'))}</p></td>"
            f"<td vertical-align=\"middle\"><p align=\"center\">{colored_change(item.get('change'))}</p></td>"
            f"<td vertical-align=\"middle\"><p align=\"center\"><b>{esc(turnover)}</b></p></td>"
            f"<td vertical-align=\"middle\"><p align=\"center\">{colored_change(item.get('change_7d'))}</p></td>"
            f"<td vertical-align=\"middle\"><p align=\"center\"><b>{esc(turnover_7d)}</b></p></td>"
            "</tr>"
        )
    return (
        '<h3 align="left"><span text-color="orange">10 只代表股行情</span></h3>\n'
        "<table>\n"
        "<colgroup><col width=\"120\"/><col width=\"100\"/><col width=\"130\"/><col width=\"130\"/><col width=\"150\"/><col width=\"170\"/></colgroup>\n"
        "<thead><tr>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">股票</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">角色</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">当日涨跌</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">当日成交(亿)</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">近7日涨跌</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">近7日均成交(亿)</span></b></p></th>"
        "</tr></thead>\n<tbody>\n"
        + "\n".join(rows)
        + "\n</tbody>\n</table>"
    )


def render_group_block(name: str, groups: dict[str, Any]) -> str:
    item = (groups or {}).get(name) or {}
    emoji, subtitle = GROUP_META[name]
    stocks = item.get("stocks") or []
    stock_line = "（无）" if not stocks else " ".join(f"<code>{esc(stock)}</code>" for stock in stocks)
    return (
        f'<callout emoji="{emoji}" background-color="light-gray" border-color="gray">'
        f"<p><b>{esc(name)}组</b> — {esc(subtitle)}</p>"
        f"<p>{stock_line}</p>"
        f"<p>{esc(item.get('feature') or '')}</p>"
        "</callout>"
    )


def render_groups(groups: dict[str, Any]) -> str:
    top = (
        '<h3 align="left"><span text-color="orange">四组行为分类</span></h3>\n'
        '<grid>\n<column width-ratio="0.5">\n'
        + render_group_block("放量上攻", groups)
        + '\n</column>\n<column width-ratio="0.5">\n'
        + render_group_block("缩量上行", groups)
        + "\n</column>\n</grid>"
    )
    bottom = (
        '<grid>\n<column width-ratio="0.5">\n'
        + render_group_block("缩量回调", groups)
        + '\n</column>\n<column width-ratio="0.5">\n'
        + render_group_block("放量杀跌", groups)
        + "\n</column>\n</grid>"
    )
    return top + "\n" + bottom


def render_watch_signals(items: list[dict[str, Any]]) -> str:
    out = []
    for idx, item in enumerate(items or [], start=1):
        tag = f" · {item.get('tag')}" if str(item.get("tag") or "").strip() else ""
        out.append(
            '<callout emoji="🔵" background-color="light-gray" border-color="gray">'
            f"<p><b>信号 {idx}{esc(tag)}：</b>{esc(item.get('signal'))}</p>"
            f"<p><b>盯：</b>{esc(item.get('watch'))}</p>"
            f"<p><b>改善：</b>{esc(item.get('improve'))}</p>"
            f"<p><b>恶化：</b>{esc(item.get('worsen'))}</p>"
            "</callout>"
        )
    return "\n".join(out)


def render_risks(items: list[dict[str, Any]]) -> str:
    out = []
    for item in items or []:
        out.append(
            '<callout emoji="⚠️" border-color="red">'
            f"<p><b>{esc(item.get('title'))}</b></p>"
            f"<p><b>触发：</b>{esc(item.get('trigger'))}</p>"
            f"<p>{esc(item.get('why'))}</p>"
            f"<p><b>证伪：</b>{esc(item.get('invalidate'))}</p>"
            "</callout>"
        )
    return "\n".join(out)


def render_sources(items: list[dict[str, Any]]) -> str:
    rows = []
    for idx, item in enumerate(items or [], start=1):
        if str(item.get("name") or "").strip() == "seed_finance_search":
            continue
        if str(item.get("url") or "").strip():
            name = f'<a href="{esc(item.get("url"))}">{esc(item.get("name"))}</a>'
        else:
            name = f"<b>{esc(item.get('name'))}</b>"
        suffix = " — ".join(part for part in [str(item.get("date") or "").strip(), str(item.get("title") or "").strip()] if part)
        rows.append((name, suffix))
    rendered = []
    for idx, (name, suffix) in enumerate(rows, start=1):
        rendered.append(f"<p align=\"left\">[{idx}] {name}{(' — ' + esc(suffix)) if suffix else ''}</p>")
    rendered.append("<p align=\"left\">[N] 同花顺数据库 — 行情、成交、估值与10股近7个交易日数据</p>")
    return "\n".join(rendered)


def render_doc(doc: dict[str, Any]) -> str:
    pill_label, pill_meaning = quadrant_pill(doc.get("info_score"), doc.get("market_score"))
    divergence = doc.get("divergence") or {}
    groups = doc.get("divergence_groups") or {}
    sec = doc.get("section_summaries") or {}
    answer = doc.get("answer") or {}

    parts = [
        f'<title>{esc(doc.get("sector"))}板块热度分析：{esc(doc.get("headline"))}</title>',
        f'<p align="left"><span text-color="gray">市场：{esc(doc.get("market"))} | 目标概念板块：{esc(doc.get("index_caliber"))} | 数据时点：{esc(doc.get("timestamp"))}</span></p>',
        '<callout emoji="⚠️" background-color="light-yellow" border-color="yellow"><p>本文仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。</p></callout>',
        section_title("综合热度仪表盘"),
        f'<p align="left"><b>综合热度：{esc(doc.get("composite_score"))}/5（{esc(doc.get("gauge_pill"))}）</b></p>',
        f'<p align="left"><b>{esc(doc.get("headline"))}</b></p>',
        f'<p align="left"><b>{esc(doc.get("summary"))}</b></p>',
        render_key_chips(doc.get("key_chips") or []),
        f'<p align="left"><span text-color="gray">本次选取的 10 只代表股：{esc("、".join(doc.get("selected_stocks") or []))}</span></p>',
        section_title("双轨热度 · 信息 vs 行情"),
        f'<p align="left"><b>{esc(divergence.get("pill") or pill_label)}</b>：{esc(pill_meaning)}</p>',
        "<table>"
        "<colgroup><col width=\"100\"/><col width=\"80\"/><col width=\"220\"/><col width=\"400\"/></colgroup>"
        "<thead><tr>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">轨道</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">分数</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">热度</span></b></p></th>"
        "<th background-color=\"light-gray\"><p align=\"center\"><b><span text-color=\"orange\">意味着</span></b></p></th>"
        "</tr></thead><tbody>"
        f"<tr><td background-color=\"light-gray\" vertical-align=\"middle\"><p align=\"center\">信息轨</p></td><td vertical-align=\"middle\"><p align=\"center\"><b>{esc(doc.get('info_score'))}/5</b></p></td><td vertical-align=\"middle\"><p align=\"center\">{progress_bar(doc.get('info_score'), 'blue')}</p></td><td vertical-align=\"middle\"><p align=\"center\">消息 / 催化 / 公开讨论的密度与强度</p></td></tr>"
        f"<tr><td background-color=\"light-gray\" vertical-align=\"middle\"><p align=\"center\">行情轨</p></td><td vertical-align=\"middle\"><p align=\"center\"><b>{esc(doc.get('market_score'))}/5</b></p></td><td vertical-align=\"middle\"><p align=\"center\">{progress_bar(doc.get('market_score'), 'red')}</p></td><td vertical-align=\"middle\"><p align=\"center\">价格 / 成交 / 代表股 / 估值的强度</p></td></tr>"
        "</tbody></table>",
        f'<p align="left"><b>判断：</b>{esc(divergence.get("verdict"))}</p>',
        f'<p align="left">{esc(divergence.get("meaning"))}</p>',
        section_title("📌 直接回答"),
        '<callout emoji="💡" background-color="light-gray" border-color="orange" text-color="gray">'
        f"<p><b>问题：</b>{esc(answer.get('restate'))}</p>"
        f"<p><b>结论：</b>{esc(answer.get('conclusion'))}</p>"
        f"<p><b>下一步：</b>{esc(answer.get('next'))}</p>"
        "</callout>",
        section_title("① 现在有多热"),
        f'<p align="left"><b>本段结论：</b>{esc(sec.get("heat"))}</p>',
        render_dimensions(doc.get("dimensions") or []),
        section_title("② 为什么涨 / 跌"),
        f'<p align="left"><b>本段结论：</b>{esc(sec.get("catalysts"))}</p>',
        render_catalysts(doc.get("catalysts") or []),
        section_title("③ 谁在动、谁没动"),
        f'<p align="left"><b>本段结论：</b>{esc(sec.get("divergence"))}</p>',
        render_stocks_table(doc.get("stocks") or []),
        render_groups(groups),
        section_title("④ 接下来盯什么"),
        f'<p align="left"><b>本段结论：</b>{esc(sec.get("watch"))}</p>',
        render_watch_signals(doc.get("watch_signals") or []),
        section_title("⑤ 风险提示"),
        f'<p align="left"><b>本段结论：</b>{esc(sec.get("risks"))}</p>',
        render_risks(doc.get("risks") or []),
        section_title("⑥ 信息来源"),
        render_sources(doc.get("sources") or []),
        section_title("免责声明"),
    ]
    parts.extend(f'<p align="left"><span text-color="gray">{esc(line)}</span></p>' for line in DISCLAIMER_LINES)
    return "\n".join(parts) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="把结构化 doc.md 渲染为 lark-doc XML。")
    ap.add_argument("doc_md", help="结构化 doc.md")
    ap.add_argument("-o", "--output", help="输出 XML 路径")
    args = ap.parse_args(argv)

    doc_path = Path(args.doc_md)
    if not doc_path.exists():
        print(f"[错误] 找不到 doc.md: {doc_path}")
        return 2
    out_path = Path(args.output) if args.output else doc_path.with_name(doc_path.stem.replace("_doc", "") + "_feishu.xml")
    doc = load_doc_markdown(doc_path)
    xml = render_doc(doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")
    print(f"[信息] 已生成飞书 XML: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
