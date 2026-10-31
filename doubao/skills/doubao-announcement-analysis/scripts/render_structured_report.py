#!/usr/bin/env python3
"""Validate a structured announcement report and render self-contained HTML.

The report JSON is the canonical content source. No full Markdown report is created.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import check_facts
import content_rules as rules


RISK_LINE = "回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。"
DISCLAIMER = [
    "以上内容为 AI 自动生成或 AI 辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。",
    "以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误。历史数据、历史业绩、回测结果及情景假设均不代表未来表现。",
    "用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖本分析输出而作出的决策及其后果，由用户自行承担。",
]
SINGLE_SECTIONS = {
    "announcement", "key_facts", "importance", "history", "linked_signals",
    "price_reaction", "perspectives", "watchlist",
}
BATCH_SECTIONS = {"coverage", "announcements", "highlights", "gaps"}
BLOCK_TYPES = {"paragraph", "callout", "list", "table", "chart"}
PERSPECTIVE_ANGLES = {
    "fundamentals": "基本面与估值影响",
    "management": "管理层与大股东视角",
    "counter_case": "反方与风险点",
}
PALETTE = ["#23466e", "#b48945", "#13756e", "#aa4a48"]
CSS = """
:root{--navy:#101f35;--navy2:#1a3554;--ink:#17283c;--muted:#607086;--line:#dbe3eb;--paper:#fff;--canvas:#f2f5f8;--accent:#b48945;--teal:#13756e}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1060px;margin:32px auto 64px;background:var(--paper);box-shadow:0 16px 48px #10243a13;border:1px solid var(--line)}
header{background:linear-gradient(125deg,var(--navy),var(--navy2));color:white;padding:34px 52px;border-bottom:4px solid var(--accent)}header small{color:#d5bc8e;letter-spacing:.14em}header h1{font-size:30px;line-height:1.35;margin:10px 0;color:#fff}header p{margin:0;color:#d8e2ee;font-size:13px}
article{padding:32px 52px 55px;min-width:0}h2{color:var(--navy);font-size:21px;margin:34px 0 15px;padding-bottom:9px;border-bottom:2px solid var(--accent)}h3{color:var(--navy);font-size:17px;margin:25px 0 10px}p{margin:0 0 14px}
.summary{background:#f7f9fb;border-left:4px solid var(--accent);padding:16px 20px;margin-bottom:28px}.summary h2{border:0;padding:0;margin:0 0 10px;font-size:18px}.summary ul{margin:0;padding-left:1.35em}.summary li{margin:8px 0}
.table-wrap{overflow-x:auto;margin:16px 0 8px;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:13px;min-width:480px}th{background:var(--navy);color:white;text-align:left}td,th{padding:9px 11px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:nth-child(even){background:#f6f8fa}.table-caption{font-size:12px;color:var(--muted);margin-bottom:22px}
.callout{border-left:4px solid var(--accent);background:#faf8f3;padding:13px 17px;margin:18px 0}.report-list{padding-left:1.4em}.report-list li{margin:8px 0}
figure.report-chart{max-width:860px;margin:20px auto 24px}figure.report-chart svg{display:block;width:100%;height:auto;border:1px solid var(--line);background:#fff}figcaption{font-size:12px;line-height:1.6;color:var(--muted);margin-top:8px}figcaption strong{display:block;font-size:14px;color:var(--ink)}.chart-events{font-size:12px;color:var(--muted);margin:8px 0 0;padding-left:1.5em}.chart-events li{margin:3px 0}
.sources{padding-left:1.6em}.sources li{margin:7px 0;overflow-wrap:anywhere}.disclaimer{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:18px;margin-top:30px}.disclaimer p{margin-bottom:9px}a{color:var(--teal)}sup{font-size:10px;white-space:nowrap}sup a{text-decoration:none;margin-left:2px}
@media(max-width:700px){main{margin:0;border:0}header{padding:24px}header h1{font-size:25px}article{padding:22px}figure.report-chart{margin-left:0;margin-right:0;overflow-x:auto}figure.report-chart svg{min-width:560px}}
@media print{body{background:white}main{margin:0;max-width:none;box-shadow:none;border:0}header{-webkit-print-color-adjust:exact;print-color-adjust:exact}figure.report-chart{break-inside:avoid}}
"""


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def numeric_text(text: str) -> bool:
    return bool(rules.NUMERIC_FACT_RE.search(text) or re.fullmatch(r"\s*[-+]?\d[\d,]*(?:\.\d+)?%?\s*", text))


def check_visible_text(text: Any, fact_ids: Any, label: str, facts: dict[str, Any], claims: dict[str, dict], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{label}.text 必须是非空文字")
        return
    if not isinstance(fact_ids, list) or any(not isinstance(x, str) for x in fact_ids):
        errors.append(f"{label}.fact_ids 必须是 claim_id 数组")
        return
    if numeric_text(text) and not fact_ids:
        errors.append(f"{label} 含关键数字但没有 fact_ids：{text[:70]}")
    for fact_id in fact_ids:
        if fact_id not in claims:
            errors.append(f"{label} 引用未知 claim_id：{fact_id}")
            continue
        claim = claims[fact_id]
        claim_period = rules.claim_periods(claim)
        text_period = rules.canonical_periods(text)
        if claim_period and text_period and claim_period.isdisjoint(text_period):
            warnings.append(f"{label} 与 {fact_id} 的期间口径可能不一致")
        rules.check_claim_wording(0, text, fact_id, claim, warnings)
    hard_checks = (
        (rules.JUDGMENT_RE, "自有判断表述"),
        (rules.UNNAMED_ANCHOR_RE, "无名锚表述"),
        (rules.PLACEHOLDER_RE, "残留占位符"),
        (rules.DRAFT_CORNER_QUOTE_RE, "草稿引号"),
        (rules.INLINE_FOOTNOTE_RE, "手写脚注角标"),
        (rules.GUESS_RE, "无算式推算措辞"),
        (rules.INTERNAL_RE, "内部流程词"),
        (rules.INTERNAL_LEVEL_RE, "内部分类词"),
        (rules.ASCII_QUOTED_HAN_RE, "中文被英文直引号包裹"),
    )
    for pattern, reason in hard_checks:
        match = pattern.search(text)
        if match:
            errors.append(f"{label} 出现{reason}：{match.group(0)}")
    if rules.RATING_RE.search(text) and not rules.ATTRIBUTION_RE.search(text):
        errors.append(f"{label} 疑似自有评级")
    if rules.UPSIDE_RE.search(text) and not rules.ATTRIBUTION_RE.search(text):
        warnings.append(f"{label} 出现上行/下行空间，缺少同行转引标注")
    if rules.BARE_WE_RE.search(text) and not rules.JUDGMENT_RE.search(text):
        warnings.append(f"{label} 出现“我们”，请确认不是自有判断")
    if rules.ASCII_DOUBLE_QUOTE_RE.search(text) and rules.HAN_RE.search(text):
        warnings.append(f"{label} 中文正文含英文直引号，请改用中文弯引号")
    if rules.US_FILING_RE.search(text) and (facts.get("meta") or {}).get("market") == "A股":
        errors.append(f"{label} A 股标的出现美股口径词")
    if rules.PROFIT_BEAT_RE.search(text) and rules.anchor_documented(facts, ("净利", "利润", "EPS", "每股收益")) is False:
        errors.append(f"{label} 利润超/低于预期却无预期锚")
    if rules.REVENUE_BEAT_RE.search(text) and rules.anchor_documented(facts, ("收入", "营收")) is False:
        errors.append(f"{label} 收入超/低于预期却无预期锚")


def validate_report(report: Any, facts: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(report, dict):
        return ["report.json 顶层必须是对象"], warnings
    claims = rules.collect_claims(facts)
    if not claims:
        errors.append("facts.json 必须有非空 claims；结构化报告不能绕过事实表")
    mode = report.get("mode")
    if mode not in {"single", "batch"}:
        errors.append("mode 必须是 single 或 batch")
    if not isinstance(report.get("title"), str) or not report["title"].strip():
        errors.append("title 必须是非空中文报告标题")
    summary = report.get("summary")
    if not isinstance(summary, list) or not 2 <= len(summary) <= 5:
        errors.append("summary 必须有 2–5 条重要结论")
    else:
        for i, item in enumerate(summary):
            if not isinstance(item, dict):
                errors.append(f"summary[{i}] 必须是对象")
                continue
            check_visible_text(item.get("text"), item.get("fact_ids", []), f"summary[{i}]", facts, claims, errors, warnings)
            if not item.get("fact_ids"):
                errors.append(f"summary[{i}] 的重要结论必须绑定事实表")
            if len(str(item.get("text", ""))) > 180:
                warnings.append(f"summary[{i}] 超过 180 字，建议压缩")
    sections = report.get("sections")
    if not isinstance(sections, list) or not sections:
        return errors + ["sections 必须是非空数组"], warnings
    keys: list[str] = []
    visible_text: list[str] = []
    for si, section in enumerate(sections):
        label = f"sections[{si}]"
        if not isinstance(section, dict):
            errors.append(f"{label} 必须是对象")
            continue
        key, title, blocks = section.get("key"), section.get("title"), section.get("blocks")
        if not isinstance(key, str) or not key:
            errors.append(f"{label}.key 缺失")
        else:
            keys.append(key)
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{label}.title 缺失")
        if not isinstance(blocks, list) or not blocks:
            errors.append(f"{label}.blocks 必须是非空数组")
            continue
        if key == "price_reaction" and mode == "single":
            if section.get("status") not in {"normal", "abnormal"}:
                errors.append(f"{label}.status 必须是 normal 或 abnormal")
            elif section["status"] == "abnormal" and not any(isinstance(b, dict) and b.get("type") == "chart" and b.get("events") for b in blocks):
                errors.append(f"{label} 股价显著异动时须有带事件标记的价格图")
        if key == "perspectives" and mode == "single":
            angles = {b.get("angle") for b in blocks if isinstance(b, dict)}
            missing_angles = set(PERSPECTIVE_ANGLES) - angles
            if missing_angles:
                errors.append(f"{label} 缺少多视角内容：{', '.join(sorted(missing_angles))}")
        for bi, block in enumerate(blocks):
            path = f"{label}.blocks[{bi}]"
            if not isinstance(block, dict):
                errors.append(f"{path} 必须是对象")
                continue
            kind = block.get("type")
            if kind not in BLOCK_TYPES:
                errors.append(f"{path}.type 不支持：{kind}")
                continue
            if kind in {"paragraph", "callout"}:
                check_visible_text(block.get("text"), block.get("fact_ids", []), path, facts, claims, errors, warnings)
                visible_text.append(str(block.get("text", "")))
            elif kind == "list":
                items = block.get("items")
                if not isinstance(items, list) or not items:
                    errors.append(f"{path}.items 必须是非空数组")
                else:
                    for ii, item in enumerate(items):
                        if not isinstance(item, dict):
                            errors.append(f"{path}.items[{ii}] 必须是对象")
                            continue
                        check_visible_text(item.get("text"), item.get("fact_ids", []), f"{path}.items[{ii}]", facts, claims, errors, warnings)
                        visible_text.append(str(item.get("text", "")))
            elif kind == "table":
                headers, rows = block.get("headers"), block.get("rows")
                if not isinstance(headers, list) or not headers or any(not isinstance(x, str) for x in headers):
                    errors.append(f"{path}.headers 必须是非空文字数组")
                    continue
                if not isinstance(rows, list) or not rows:
                    errors.append(f"{path}.rows 必须是非空数组")
                    continue
                for ri, row in enumerate(rows):
                    if not isinstance(row, list) or len(row) != len(headers):
                        errors.append(f"{path}.rows[{ri}] 的列数与 headers 不一致")
                        continue
                    for ci, cell in enumerate(row):
                        cell_path = f"{path}.rows[{ri}][{ci}]"
                        if isinstance(cell, dict):
                            check_visible_text(cell.get("text"), cell.get("fact_ids", []), cell_path, facts, claims, errors, warnings)
                            visible_text.append(str(cell.get("text", "")))
                        elif isinstance(cell, str):
                            if numeric_text(cell):
                                errors.append(f"{cell_path} 是数字，须写为含 fact_ids 的对象")
                        else:
                            errors.append(f"{cell_path} 必须是文字或含 text/fact_ids 的对象")
            elif kind == "chart":
                validate_chart(block, path, facts, claims, errors, warnings)
    if len(keys) != len(set(keys)):
        errors.append("sections[].key 不能重复")
    required = SINGLE_SECTIONS if mode == "single" else BATCH_SECTIONS
    missing = required - set(keys)
    if missing:
        errors.append(f"缺少必需章节：{', '.join(sorted(missing))}")
    if mode == "single" and not any(isinstance(s, dict) and s.get("key") == "history" and isinstance(s.get("blocks"), list) and any(isinstance(b, dict) and b.get("type") == "table" for b in s["blocks"]) for s in sections):
        errors.append("历史对比章节必须包含表格")
    if mode == "single" and not any("后续" in x and "关注" in x for x in visible_text):
        warnings.append("正文缺少「后续关注」文字；请检查 watchlist 章节")
    if not any(str(claim.get("url", "")).startswith(("http://", "https://")) for claim in claims.values()):
        warnings.append("事实表无可点击来源链接，请复核原公告和数据库链接")
    return errors, warnings


def validate_chart(chart: dict, path: str, facts: dict[str, Any], claims: dict[str, dict], errors: list[str], warnings: list[str]) -> None:
    if chart.get("chart_type") not in {"line", "bar"}:
        errors.append(f"{path}.chart_type 只支持 line 或 bar")
    for field in ("title", "unit", "caption", "market"):
        if not isinstance(chart.get(field), str) or not chart[field].strip():
            errors.append(f"{path}.{field} 必须是非空文字")
    if chart.get("market") not in {"A股", "港股", "美股"}:
        errors.append(f"{path}.market 必须是 A股、港股或美股")
    x_labels = chart.get("x_labels")
    if not isinstance(x_labels, list) or not 3 <= len(x_labels) <= 12 or any(not isinstance(x, str) or not x for x in x_labels):
        errors.append(f"{path}.x_labels 必须有 3–12 个非空标签")
        return
    series = chart.get("series")
    if not isinstance(series, list) or not 1 <= len(series) <= 4:
        errors.append(f"{path}.series 必须有 1–4 条序列")
        return
    for si, item in enumerate(series):
        sp = f"{path}.series[{si}]"
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            errors.append(f"{sp}.name 缺失")
            continue
        values = item.get("values")
        if not isinstance(values, list) or len(values) != len(x_labels):
            errors.append(f"{sp}.values 数量须与 x_labels 一致")
            continue
        for vi, point in enumerate(values):
            pp = f"{sp}.values[{vi}]"
            if not isinstance(point, dict) or not isinstance(point.get("value"), (int, float)) or isinstance(point.get("value"), bool) or not math.isfinite(point["value"]):
                errors.append(f"{pp}.value 必须是有限数值")
                continue
            ids = point.get("fact_ids")
            if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in claims for x in ids):
                errors.append(f"{pp}.fact_ids 必须引用已登记事实")
                continue
            if not any(isinstance(claims[fid].get("value"), (int, float)) and not isinstance(claims[fid].get("value"), bool) and math.isclose(float(claims[fid]["value"]), float(point["value"]), rel_tol=1e-9, abs_tol=1e-9) and claims[fid].get("unit") == chart.get("unit") for fid in ids):
                errors.append(f"{pp} 的数值和单位必须与至少一条 fact 的 value/unit 完全一致")
    if chart.get("chart_type") == "bar" and any(isinstance(p, dict) and isinstance(p.get("value"), (int, float)) and p["value"] < 0 for s in series if isinstance(s, dict) and isinstance(s.get("values"), list) for p in s["values"]):
        warnings.append(f"{path} 柱状图含负值，请复核基线")
    events = chart.get("events", [])
    if not isinstance(events, list):
        errors.append(f"{path}.events 必须是数组")
        return
    for ei, event in enumerate(events):
        ep = f"{path}.events[{ei}]"
        if not isinstance(event, dict):
            errors.append(f"{ep} 必须是对象")
            continue
        if not isinstance(event.get("x_index"), int) or isinstance(event.get("x_index"), bool) or not 0 <= event["x_index"] < len(x_labels):
            errors.append(f"{ep}.x_index 超出 x_labels 范围")
        elif event.get("date") != x_labels[event["x_index"]]:
            errors.append(f"{ep}.date 必须与 x_labels[x_index] 完全一致")
        if event.get("phase") not in {"发生", "披露", "可交易"}:
            errors.append(f"{ep}.phase 必须是发生、披露或可交易")
        if not isinstance(event.get("label"), str) or not event["label"].strip():
            errors.append(f"{ep}.label 缺失")
        ids = event.get("fact_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in claims for x in ids):
            errors.append(f"{ep}.fact_ids 必须引用已登记事实")
        else:
            check_visible_text(event.get("label"), ids, ep, facts, claims, errors, warnings)
        if not isinstance(event.get("market"), str) or not event["market"].strip():
            errors.append(f"{ep}.market 缺失")
        elif event["market"] != chart.get("market") and not event.get("cross_market_note"):
            errors.append(f"{ep} 与图表市场不同，须填写 cross_market_note")
    if chart.get("market") != (facts.get("meta") or {}).get("market") and not chart.get("market_note"):
        errors.append(f"{path} 与报告主市场不同，须填写 market_note")
    if isinstance(chart.get("caption"), str):
        all_ids = [fid for item in series if isinstance(item, dict) and isinstance(item.get("values"), list) for point in item["values"] if isinstance(point, dict) for fid in point.get("fact_ids", []) if isinstance(fid, str) and fid in claims]
        check_visible_text(chart["caption"], all_ids, f"{path}.caption", facts, claims, errors, warnings)


class Citations:
    def __init__(self, claims: dict[str, dict]):
        self.claims = claims
        self.number_by_source: dict[tuple[str, str], int] = {}
        self.sources: list[tuple[str, str]] = []

    def numbers(self, ids: list[str]) -> list[int]:
        numbers: list[int] = []
        for fact_id in ids:
            claim = self.claims[fact_id]
            key = (str(claim["source"]), str(claim.get("url", "")))
            if key not in self.number_by_source:
                self.sources.append(key)
                self.number_by_source[key] = len(self.sources)
            number = self.number_by_source[key]
            if number not in numbers:
                numbers.append(number)
        return sorted(numbers)

    def marker(self, ids: list[str]) -> str:
        numbers = self.numbers(ids)
        if not numbers:
            return ""
        return '<sup>' + ''.join(f'<a href="#src-{n}">[{n}]</a>' for n in numbers) + '</sup>'

    def source_list(self) -> str:
        rows = []
        for number, (source, url) in enumerate(self.sources, 1):
            link = f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(source)}</a>' if url.startswith(("http://", "https://")) else esc(source)
            rows.append(f'<li id="src-{number}">{link}</li>')
        return '<ol class="sources">' + ''.join(rows) + '</ol>'


def chart_svg(chart: dict) -> str:
    labels = chart["x_labels"]
    series = chart["series"]
    n = len(labels)
    width, height = 860, 390
    left, right, top, bottom = 72, 24, 44, 318
    plot_w, plot_h = width - left - right, bottom - top
    values = [p["value"] for s in series for p in s["values"]]
    low = min(values)
    high = max(values)
    if chart["chart_type"] == "bar":
        low = min(0, low)
        high = max(0, high)
    else:
        padding = max((high - low) * 0.12, abs(high) * 0.02, 0.01)
        low -= padding
        high += padding
    if high == low:
        high += 1
        low -= 1
    scale_y = lambda v: bottom - (v - low) / (high - low) * plot_h
    if chart["chart_type"] == "bar":
        step = plot_w / n
        scale_x = lambda i: left + (i + 0.5) * step
    else:
        scale_x = lambda i: left + i * plot_w / (n - 1)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(chart["title"])}" xmlns="http://www.w3.org/2000/svg">',
             '<rect width="860" height="390" fill="#fff"/>',
             f'<text x="{left}" y="24" font-size="13" fill="#607086">单位：{esc(chart["unit"])}</text>']
    for tick in range(5):
        value = low + (high - low) * tick / 4
        y = scale_y(value)
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e4e9ef"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#607086">{value:,.1f}</text>')
    for i, label in enumerate(labels):
        x = scale_x(i)
        parts.append(f'<text x="{x:.1f}" y="{bottom+24}" text-anchor="middle" font-size="12" fill="#607086">{esc(label)}</text>')
    for si, item in enumerate(series):
        color = PALETTE[si]
        if chart["chart_type"] == "line":
            coords = ' '.join(f'{scale_x(i):.1f},{scale_y(p["value"]):.1f}' for i, p in enumerate(item["values"]))
            parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
            for i, point in enumerate(item["values"]):
                parts.append(f'<circle cx="{scale_x(i):.1f}" cy="{scale_y(point["value"]):.1f}" r="4" fill="{color}"><title>{esc(item["name"])} · {esc(labels[i])}: {point["value"]} {esc(chart["unit"])}</title></circle>')
        else:
            bar_w = min(48, plot_w / n / (len(series) + 0.6))
            for i, point in enumerate(item["values"]):
                x = scale_x(i) + (si - (len(series)-1)/2) * bar_w
                base = scale_y(0)
                y = min(base, scale_y(point["value"]))
                h = max(abs(base-scale_y(point["value"])), 1)
                parts.append(f'<rect x="{x-bar_w*0.45:.1f}" y="{y:.1f}" width="{bar_w*0.9:.1f}" height="{h:.1f}" fill="{color}"><title>{esc(item["name"])} · {esc(labels[i])}: {point["value"]} {esc(chart["unit"])}</title></rect>')
    for ei, event in enumerate(chart.get("events", []), 1):
        x = scale_x(event["x_index"])
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{bottom}" stroke="#aa4a48" stroke-width="1" stroke-dasharray="4 4"/>')
        parts.append(f'<circle cx="{x:.1f}" cy="{top+7}" r="11" fill="#aa4a48"/><text x="{x:.1f}" y="{top+11}" text-anchor="middle" font-size="11" fill="white">{ei}</text>')
    legend_x = left
    for si, item in enumerate(series):
        parts.append(f'<rect x="{legend_x}" y="{height-20}" width="14" height="4" fill="{PALETTE[si]}"/><text x="{legend_x+20}" y="{height-14}" font-size="12" fill="#17283c">{esc(item["name"])}</text>')
        legend_x += min(220, 40 + len(item["name"]) * 15)
    parts.append('</svg>')
    return ''.join(parts)


def render_block(block: dict, citations: Citations) -> str:
    kind = block["type"]
    if kind == "paragraph":
        return f'<p>{esc(block["text"])}{citations.marker(block.get("fact_ids", []))}</p>'
    if kind == "callout":
        return f'<aside class="callout">{esc(block["text"])}{citations.marker(block.get("fact_ids", []))}</aside>'
    if kind == "list":
        return '<ul class="report-list">' + ''.join(f'<li>{esc(x["text"])}{citations.marker(x.get("fact_ids", []))}</li>' for x in block["items"]) + '</ul>'
    if kind == "table":
        head = ''.join(f'<th>{esc(x)}</th>' for x in block["headers"])
        rows = []
        for row in block["rows"]:
            cells = []
            for cell in row:
                if isinstance(cell, dict):
                    cells.append(f'<td>{esc(cell["text"])}{citations.marker(cell.get("fact_ids", []))}</td>')
                else:
                    cells.append(f'<td>{esc(cell)}</td>')
            rows.append('<tr>' + ''.join(cells) + '</tr>')
        caption = f'<p class="table-caption">{esc(block["caption"])}</p>' if block.get("caption") else ''
        return '<div class="table-wrap"><table><thead><tr>' + head + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>' + caption
    chart_ids = [fact_id for series in block["series"] for point in series["values"] for fact_id in point["fact_ids"]]
    event_rows = []
    for i, event in enumerate(block.get("events", []), 1):
        chart_ids.extend(event["fact_ids"])
        note = f'；跨市场说明：{esc(event["cross_market_note"])}' if event.get("cross_market_note") else ''
        event_rows.append(f'<li>{esc(event["date"])} · {esc(event["phase"])} · {esc(event["market"])} · {esc(event["label"])}{note}{citations.marker(event["fact_ids"])}</li>')
    market_note = f'；{esc(block["market_note"])}' if block.get("market_note") else ''
    caption = f'<figcaption><strong>{esc(block["title"])}</strong>{esc(block["caption"])}；市场：{esc(block["market"])}{market_note}{citations.marker(chart_ids)}</figcaption>'
    events = '<ol class="chart-events">' + ''.join(event_rows) + '</ol>' if event_rows else ''
    return f'<figure class="report-chart">{chart_svg(block)}{caption}{events}</figure>'


def render_html(report: dict, facts: dict) -> str:
    claims = rules.collect_claims(facts)
    citations = Citations(claims)
    summary = '<section class="summary"><h2>重点结论</h2><ul>' + ''.join(f'<li>{esc(item["text"])}{citations.marker(item.get("fact_ids", []))}</li>' for item in report["summary"]) + '</ul></section>'
    sections = []
    for section in report["sections"]:
        rendered_blocks = []
        seen_angles = set()
        for block in section["blocks"]:
            angle = block.get("angle")
            if section["key"] == "perspectives" and angle in PERSPECTIVE_ANGLES and angle not in seen_angles:
                rendered_blocks.append(f'<h3>{esc(PERSPECTIVE_ANGLES[angle])}</h3>')
                seen_angles.add(angle)
            rendered_blocks.append(render_block(block, citations))
        blocks = ''.join(rendered_blocks)
        sections.append(f'<section id="{esc(section["key"])}"><h2>{esc(section["title"])}</h2>{blocks}</section>')
    sources = '<section><h2>数据来源</h2>' + citations.source_list() + '</section>'
    disclaimer = '<section class="disclaimer"><h2>风险提示与免责声明</h2>' + ''.join(f'<p>{esc(p)}</p>' for p in DISCLAIMER) + '</section>'
    meta = facts["meta"]
    byline = f'{esc(meta["company"])} · {esc(meta["market"])} · {esc(meta["today"])}'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(report["title"]) + '</title><style>' + CSS + '</style></head><body><main><header><small>EQUITY RESEARCH · 公告解读</small><h1>' + esc(report["title"]) + '</h1><p>' + byline + '</p></header><article>' + summary + ''.join(sections) + sources + disclaimer + '</article></main></body></html>'


def render_summary(report: dict, html_output: Path) -> str:
    return RISK_LINE + '\n\n' + '## 重点结论\n\n' + '\n'.join(f'- {item["text"]}' for item in report["summary"]) + f'\n\nHTML 报告：[查看完整报告](<{html_output.resolve()}>)\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验结构化报告并直接生成 HTML 与对话摘要")
    parser.add_argument("report", type=Path, help="report.json 路径")
    parser.add_argument("facts", type=Path, help="facts.json 路径")
    parser.add_argument("--html-output", required=True, type=Path)
    parser.add_argument("--summary-output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        facts = check_facts.load_json(args.facts)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[错误] 无法读取输入：{exc}", file=sys.stderr)
        return 1
    facts_result = check_facts.validate(facts)
    errors, warnings = validate_report(report, facts)
    facts_result.emit()
    for warning in warnings:
        print(f"[警告] {warning}")
    for error in errors:
        print(f"[错误] {error}")
    if facts_result.errors or errors:
        return 1
    if args.html_output.resolve() == args.summary_output.resolve() or args.html_output.resolve() in {args.report.resolve(), args.facts.resolve()} or args.summary_output.resolve() in {args.report.resolve(), args.facts.resolve()}:
        print("[错误] 输出路径不能覆盖输入或彼此重合", file=sys.stderr)
        return 1
    if args.html_output.suffix.lower() != ".html":
        print("[错误] --html-output 必须以 .html 结尾", file=sys.stderr)
        return 1
    page = render_html(report, facts)
    summary = render_summary(report, args.html_output)
    args.html_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    html_tmp = args.html_output.with_suffix(args.html_output.suffix + ".tmp")
    summary_tmp = args.summary_output.with_suffix(args.summary_output.suffix + ".tmp")
    html_tmp.write_text(page, encoding="utf-8")
    summary_tmp.write_text(summary, encoding="utf-8")
    html_tmp.replace(args.html_output)
    summary_tmp.replace(args.summary_output)
    print(f"HTML 报告：{args.html_output}")
    print(f"对话摘要：{args.summary_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
