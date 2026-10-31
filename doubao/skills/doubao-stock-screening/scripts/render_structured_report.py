#!/usr/bin/env python3
"""Render one structured research report to native HTML and optional Markdown.

Usage: python3 scripts/render_structured_report.py report.json --output report.html

Add --markdown-output report.md only when a Markdown export is requested.

The HTML is built from semantic components. It is never parsed back from Markdown.
"""

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from native_charts import render_chart


DISCLAIMER = [
    '以上内容为 AI 自动生成或 AI 辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。',
    '以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误。历史数据、历史业绩、回测结果及情景假设均不代表未来表现。',
    '用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖本分析输出而作出的决策及其后果，由用户自行承担。',
]

COMPANY_PARTS = (
    ('role', '业务角色与主线相关性'),
    ('earnings', '业绩情况'),
    ('valuation', '估值与交易状态'),
    ('peers', '同行对比'),
    ('risk', '风险'),
)

CSS = """
:root{--navy:#10243b;--navy2:#1b3857;--ink:#172b41;--muted:#60758a;--line:#dce5ed;--canvas:#fff;--paper:#fff;--accent:#b48945;--teal:#13756e;--pale:#f6f8fa}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}.report-hero{background:linear-gradient(125deg,var(--navy),var(--navy2));color:#fff;padding:46px max(28px,calc((100vw - 1160px)/2));border-bottom:4px solid var(--accent)}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.18em;color:#d8c197}.report-hero h1{max-width:980px;font-size:34px;line-height:1.3;letter-spacing:-.02em;margin:13px 0 10px}.subtitle{max-width:850px;color:#d9e2eb;font-size:16px;margin:0 0 20px}.hero-meta{display:flex;gap:9px;flex-wrap:wrap}.hero-meta span{font-size:12px;border:1px solid #ffffff4d;border-radius:999px;padding:4px 12px;color:#ecf2f8}
.report-shell{max-width:1160px;margin:28px auto 72px;padding:0 24px}.toc{padding:0 0 18px;border-bottom:1px solid var(--line);margin-bottom:24px}.toc-title{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.1em;margin-bottom:8px}.toc-links{display:flex;flex-wrap:wrap;gap:6px 18px}.toc a{display:inline-block;padding:3px 0;font-size:13px;line-height:1.4}.summary-grid,.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.summary-grid{margin-bottom:16px}.card-grid{display:grid;grid-template-columns:1fr;gap:0;margin:20px 0;border-top:1px solid var(--line)}.summary-card,.metric-card{background:var(--pale);border:1px solid var(--line);border-radius:8px;padding:18px}.summary-card{border-top:3px solid var(--accent)}.summary-card .label,.metric-card .label{font-size:12px;color:var(--muted)}.summary-card .value,.metric-card .value{display:block;font-size:20px;font-weight:700;line-height:1.35;margin:5px 0;color:var(--navy)}.summary-card .detail,.metric-card .detail{font-size:12px;color:var(--muted);line-height:1.5}.opening-conclusion{background:#f2f7f6;border-left:4px solid var(--teal);padding:20px 24px;margin-bottom:34px}.opening-conclusion strong{display:block;font-size:13px;color:var(--teal);margin-bottom:6px}.opening-conclusion p{font-size:16px;line-height:1.75;margin:0;color:var(--navy)}.opening-conclusion p+p{margin-top:12px}
.report-section{padding:38px 0 44px;margin:0;border-top:1px solid var(--line);font-size:16px;line-height:1.75;color:var(--ink)}.report-section h2{font-size:22px;line-height:1.4;margin:0 0 17px;color:var(--ink)}.section-index{display:inline-block;font-size:16px;color:var(--teal);font-weight:700;vertical-align:baseline;min-width:36px;margin-right:10px}.report-section > h2 .section-index{font-size:inherit;color:inherit}.toc-index{color:var(--teal);font-weight:700;margin-right:5px}.report-section h3{font-size:18px;line-height:1.5;margin:31px 0 11px;color:var(--ink)}.section-conclusion{max-width:820px;font-size:16px;font-weight:600;line-height:1.75;color:var(--ink);margin:0 0 14px}.subsection-conclusion{max-width:820px;font-size:16px;font-weight:600;line-height:1.75;color:var(--ink);margin:0 0 17px}.report-section .section-intro{font-size:16px;color:var(--ink);max-width:820px;margin:0 0 22px}.report-section>p,.report-section .prose{max-width:820px;margin:0 0 17px}.report-section ul,.report-section ol{padding-left:1.4em;margin:6px 0 18px}.report-section li{padding-left:3px;margin:7px 0}.report-appendix{padding:28px 0;border-top:1px solid var(--line)}.report-appendix h2{font-size:18px;color:var(--navy);margin:0 0 14px}.block{margin:22px 0}.block:last-child{margin-bottom:0}.metric-grid{margin:17px 0}.metric-card{background:var(--pale)}
.flow{margin:20px 0}.flow-head{display:flex;justify-content:space-between;gap:18px;align-items:baseline;margin-bottom:10px}.flow-head strong{font-size:15px;color:var(--navy)}.flow-note,.table-note,.block-note{font-size:12px;color:var(--muted);margin-top:9px}.flow-steps{display:grid;gap:13px}.flow-step{display:grid;grid-template-columns:32px minmax(0,1fr) auto;gap:13px;align-items:start;background:#f8fafb;border:1px solid var(--line);border-left:3px solid var(--teal);border-radius:8px;padding:16px}.flow-step:not(:last-child){position:relative}.flow-step:not(:last-child):after{content:"↓";position:absolute;bottom:-19px;left:24px;color:var(--teal);font-size:20px;font-weight:700;z-index:1}.flow-index{display:grid;place-items:center;width:27px;height:27px;background:#dcece9;color:var(--teal);font-weight:700;border-radius:50%;font-size:12px}.flow-step-title{font-weight:700;color:var(--navy);line-height:1.4}.flow-step-detail{font-size:13px;color:var(--muted);margin-top:3px}.flow-count{background:#e8eff5;color:var(--navy);border-radius:5px;padding:3px 8px;font-size:12px;font-weight:700;white-space:nowrap}
.table-block{border:1px solid var(--line);border-radius:8px;overflow:hidden}.table-caption{background:#f7f9fb;font-weight:700;color:var(--navy);padding:12px 15px;border-bottom:1px solid var(--line)}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;min-width:540px}th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:#e9eff4;color:var(--navy);font-weight:700;white-space:nowrap}tbody tr:nth-child(even){background:#f9fbfc}tbody tr:last-child td{border-bottom:0}.table-note{padding:0 15px 12px;margin:0}
.candidate-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(180px,25%);gap:20px;padding:20px 2px;border-bottom:1px solid var(--line)}.candidate-card h3{font-size:17px;margin:0 0 4px}.candidate-subtitle{font-size:12px;color:var(--teal);margin-bottom:7px}.candidate-card p{font-size:14px;margin:0;max-width:720px}.candidate-stats{display:flex;flex-wrap:wrap;align-content:start;gap:7px}.candidate-stats span{font-size:12px;background:#e8eff5;padding:4px 8px;border-radius:4px}.company-analysis{display:grid;grid-template-columns:minmax(220px,28%) minmax(0,1fr);gap:32px;padding:32px 0;border-top:1px solid var(--line)}.company-heading h3{font-size:21px;margin:0 0 10px}.company-thesis{font-size:15px;line-height:1.65;color:var(--navy);font-weight:600;margin:0 0 16px}.company-stats{display:flex;flex-wrap:wrap;gap:7px}.company-stats span{font-size:12px;background:var(--pale);border:1px solid var(--line);border-radius:4px;padding:4px 7px}.company-body h4{font-size:16px;color:var(--navy);margin:0 0 6px}.company-part-conclusion{font-weight:700;color:var(--ink)}.company-body p{font-size:14px;line-height:1.8;margin:0 0 21px;max-width:740px}.company-body .company-argument:last-child p{margin-bottom:0}.timeline{border-left:2px solid #d6e3e7;margin-left:9px;padding-left:22px}.timeline-item{position:relative;padding:0 0 20px}.timeline-item:before{content:"";position:absolute;left:-29px;top:7px;width:10px;height:10px;background:var(--teal);border:2px solid #fff;border-radius:50%}.timeline-date{font-size:12px;color:var(--teal);font-weight:700}.timeline-title{font-weight:700;color:var(--navy)}.timeline-item p{font-size:13px;margin:3px 0 0;color:var(--muted)}.callout{border-left:4px solid var(--accent);background:#fbf8f1;padding:15px 18px;border-radius:0 8px 8px 0}.callout strong{display:block;margin-bottom:4px}.callout p{margin:0}.callout.risk{border-color:#aa4a48;background:#fdf6f5}.cite{font-size:.77em;vertical-align:super;white-space:nowrap;font-weight:700;padding-left:2px}
.report-chart{border:1px solid var(--line);border-radius:8px;padding:15px;background:#fff;margin:20px 0}.chart-scroll{overflow-x:auto}.report-chart svg{display:block;width:100%;height:auto}.report-chart figcaption{font-size:12px;color:var(--muted);margin:4px 4px 0}.report-chart figcaption strong{display:block;font-size:14px;color:var(--navy)}.chart-meta{display:block}.scroll-hint{display:none}.sources-list{list-style:none!important;padding:0!important}.sources-list li{padding:10px 0;border-bottom:1px solid var(--line);font-size:13px}.source-id{font-weight:700;color:var(--teal);margin-right:6px}.source-meta{display:block;color:var(--muted);font-size:12px}.disclaimer-list{font-size:12px;color:var(--muted)}
@media(max-width:900px){.report-hero{padding:34px 28px}.company-analysis{grid-template-columns:1fr;gap:15px}}
@media(max-width:600px){.report-hero{padding:30px 22px}.report-hero h1{font-size:27px}.report-shell{padding:0 16px;margin-top:12px}.toc-links{gap:4px 12px}.report-section{padding:27px 0 32px}.summary-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.summary-card{padding:12px}.summary-card .value{font-size:16px}.opening-conclusion{padding:17px}.opening-conclusion p{font-size:15px}.candidate-card{grid-template-columns:1fr;gap:10px}.company-analysis{padding:24px 0}.flow-step{grid-template-columns:27px minmax(0,1fr);padding:13px}.flow-count{grid-column:2;justify-self:start}.report-chart svg{min-width:650px}.scroll-hint{display:block;color:var(--teal);margin-top:5px}}
@media print{body{background:#fff}.report-hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}.report-shell{display:block;margin:0;max-width:none}.toc{display:none}.report-chart{break-inside:avoid}}

/* Narrative typography: three sizes and one text color; component styles stay independent. */
body{font-size:15.5px;line-height:1.75}
.report-hero h1{font-size:32px}
.report-section h3{margin:26px 0 10px}
.summary-card .label,.metric-card .label{font-size:13px;line-height:1.45}
.summary-card .detail,.metric-card .detail{font-size:13.5px;line-height:1.55}
.summary-card .value,.metric-card .value{font-size:20px;line-height:1.3;overflow-wrap:anywhere}
.summary-card .value-long,.metric-card .value-long{font-size:17px}
.flow-step-detail{font-size:14px;line-height:1.55}
.flow-note,.table-note,.block-note{font-size:13px;line-height:1.6}
.cite{font-size:.84em}
.scope-details{max-width:820px;margin:0 0 18px}
.scope-details p{margin:8px 0;font-size:16px;line-height:1.75;color:var(--ink)}
.scope-details strong,.theme-analysis strong{color:inherit}
.theme-analysis{max-width:820px}
.theme-analysis p{margin:0 0 14px;font-size:16px;line-height:1.75;color:var(--ink)}
.data-gap-list{max-width:820px;font-size:16px}
.report-section > p .cite,.report-section > h3 .cite,.report-section > .block.prose .cite,.report-section > .scope-details .cite,.report-section > .theme-analysis .cite,.report-section > ul .cite,.report-section > ol .cite{font-size:inherit;color:inherit;vertical-align:baseline}
@media(max-width:600px){.report-hero h1{font-size:26px}.metric-card{padding:15px}.metric-card .value{font-size:19px}.metric-card .value-long{font-size:17px}.summary-card .detail,.metric-card .detail{font-size:13px}}

"""


def esc(value):
    return html.escape(str(value), quote=True)


def text_with_citations(value):
    escaped = esc(value)
    return re.sub(r'\[(\d+)\]', lambda m: f'<a class="cite" href="#source-{m.group(1)}">[{m.group(1)}]</a>', escaped)


def render_paragraphs(value):
    """Preserve deliberate paragraph breaks in a report text field."""
    return ''.join(f'<p>{text_with_citations(part.strip())}</p>' for part in re.split(r'\n\s*\n+', value.strip()) if part.strip())


def required_string(obj, key, context):
    value = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{context} 缺少 {key}')
    return value


def display_heading(value):
    """Drop document-outline prefixes from web headings without changing the source."""
    title = str(value).strip()
    cleaned = re.sub(r'^\s*(?:[一二三四五六七八九十百]+[、．.]|\d+(?:\.\d+)+[、．.]?\s+|\d+[、．.]\s+|第[一二三四五六七八九十百\d]+(?:组|类|章|节|部分)[：:、\s]+)', '', title)
    return cleaned.strip() or title


def render_subheading(block, heading_index=None):
    """Keep narrative text out of heading typography when source data is verbose."""
    title = display_heading(required_string(block, 'text', 'heading'))
    conclusion = block.get('conclusion')
    lead = f'<p class="subsection-conclusion">{text_with_citations(conclusion)}</p>' if conclusion else ''
    number = f'{heading_index}）' if heading_index is not None else ''
    if len(title) <= 40 and '\n' not in title:
        return f'<h3>{number}{text_with_citations(title)}</h3>{lead}'
    prefix = re.match(r'^([^：:。；;]{2,12})[：:]\s*(.+)$', title, re.S)
    if prefix:
        return (f'<h3>{number}{text_with_citations(prefix.group(1))}</h3>{lead}'
                f'<p class="block prose">{text_with_citations(prefix.group(2))}</p>')
    return f'<p class="block prose">{text_with_citations(title)}</p>{lead}'


def render_block(block, heading_index=None):
    if not isinstance(block, dict):
        raise ValueError('报告 block 必须是对象')
    kind = block.get('type')
    if kind == 'paragraph':
        return f'<p class="block prose">{text_with_citations(required_string(block,"text","paragraph"))}</p>'
    if kind == 'heading':
        return render_subheading(block, heading_index)
    if kind == 'list':
        items = block.get('items')
        if not isinstance(items, list) or not items:
            raise ValueError('list 需要 items')
        tag = 'ol' if block.get('ordered') else 'ul'
        return f'<{tag} class="block">' + ''.join(f'<li>{text_with_citations(item)}</li>' for item in items) + f'</{tag}>'
    if kind == 'metrics':
        items = block.get('items')
        if not isinstance(items, list) or not items:
            raise ValueError('metrics 需要 items')
        cards = []
        for item in items:
            value = required_string(item, 'value', 'metric')
            value_class = 'value value-long' if len(value) > 16 else 'value'
            cards.append(f'<div class="metric-card"><span class="label">{esc(required_string(item,"label","metric"))}</span><span class="{value_class}">{text_with_citations(value)}</span><span class="detail">{text_with_citations(item.get("detail",""))}</span></div>')
        return '<div class="block metric-grid">' + ''.join(cards) + '</div>'
    if kind == 'flow':
        steps = block.get('steps')
        if not isinstance(steps, list) or not steps:
            raise ValueError('flow 需要 steps')
        title = block.get('title', '筛选流程')
        result = [f'<div class="block flow" aria-label="{esc(title)}"><div class="flow-head"><strong>{text_with_citations(title)}</strong></div><div class="flow-steps">']
        for index, step in enumerate(steps, 1):
            result.append(f'<div class="flow-step"><span class="flow-index">{index}</span><div><div class="flow-step-title">{text_with_citations(required_string(step,"title","flow step"))}</div><div class="flow-step-detail">{text_with_citations(step.get("detail",""))}</div></div>')
            if step.get('count') is not None:
                count = step['count']
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError('flow.count 必须是实际筛选所得的非负整数；估计数量写入 detail')
                result.append(f'<span class="flow-count">{count}{esc(step.get("count_unit", "只"))}</span>')
            result.append('</div>')
        result.append('</div>')
        if block.get('note'):
            result.append(f'<p class="flow-note">{text_with_citations(block["note"])}</p>')
        result.append('</div>')
        return ''.join(result)
    if kind == 'table':
        columns, rows = block.get('columns'), block.get('rows')
        if not isinstance(columns, list) or not columns or not isinstance(rows, list):
            raise ValueError('table 需要 columns 和 rows')
        if any(not isinstance(row, list) or len(row) != len(columns) for row in rows):
            raise ValueError('table 每行长度必须与 columns 一致')
        caption = f'<div class="table-caption">{text_with_citations(block["caption"])}</div>' if block.get('caption') else ''
        head = '<thead><tr>' + ''.join(f'<th scope="col">{text_with_citations(col)}</th>' for col in columns) + '</tr></thead>'
        body = '<tbody>' + ''.join('<tr>' + ''.join(f'<td>{text_with_citations(cell)}</td>' for cell in row) + '</tr>' for row in rows) + '</tbody>'
        note = f'<p class="table-note">{text_with_citations(block["note"])}</p>' if block.get('note') else ''
        return f'<div class="block table-block">{caption}<div class="table-scroll"><table>{head}{body}</table></div>{note}</div>'
    if kind == 'chart':
        return render_chart(block.get('spec'))
    if kind == 'cards':
        items = block.get('items')
        if not isinstance(items, list) or not items:
            raise ValueError('cards 需要 items')
        cards = []
        for item in items:
            stats = item.get('stats', [])
            if not isinstance(stats, list):
                raise ValueError('card.stats 必须是数组')
            stat_html = ''.join(f'<span>{esc(required_string(stat,"label","card stat"))}：{text_with_citations(required_string(stat,"value","card stat"))}</span>' for stat in stats)
            cards.append(f'<div class="candidate-card"><div><h3>{text_with_citations(display_heading(required_string(item,"title","card")))}</h3><p>{text_with_citations(item.get("summary",""))}</p><div class="candidate-subtitle">{text_with_citations(item.get("subtitle",""))}</div></div><div class="candidate-stats">{stat_html}</div></div>')
        return '<div class="block card-grid">' + ''.join(cards) + '</div>'
    if kind == 'company':
        title = display_heading(required_string(block, 'title', 'company'))
        parts = block.get('parts')
        analysis = block.get('analysis')
        if parts is not None:
            if not isinstance(parts, dict):
                raise ValueError('company.parts 必须是对象')
            thesis = required_string(block, 'thesis', 'company')
            body = ''.join(
                f'<div class="company-argument"><h4>{esc(label)}</h4>'
                f'<p><strong class="company-part-conclusion">{text_with_citations(required_string(parts.get(key),"conclusion",f"company.{key}"))}</strong> '
                f'{text_with_citations(required_string(parts.get(key),"text",f"company.{key}"))}</p></div>'
                for key, label in COMPANY_PARTS
            )
        elif analysis is not None:
            if not isinstance(analysis, list) or len(analysis) < 2:
                raise ValueError('company.analysis 至少需要两个独立论点')
            thesis = required_string(block, 'thesis', 'company')
            body = ''.join(f'<div class="company-argument"><h4>{text_with_citations(display_heading(required_string(item,"title","company analysis")))}</h4><p>{text_with_citations(required_string(item,"text","company analysis"))}</p></div>' for item in analysis)
        else:
            points = block.get('points')
            if not isinstance(points, list) or not points:
                raise ValueError('company 需要 analysis 或旧版 points 数组')
            thesis = block.get('thesis', '')
            body = ''.join(f'<div class="company-argument"><h4>{text_with_citations(display_heading(required_string(point,"label","company point")))}</h4><p>{text_with_citations(required_string(point,"text","company point"))}</p></div>' for point in points)
        stats = block.get('stats', [])
        if not isinstance(stats, list):
            raise ValueError('company.stats 必须是数组')
        stat_html = ''.join(f'<span>{esc(required_string(stat,"label","company stat"))}：{text_with_citations(required_string(stat,"value","company stat"))}</span>' for stat in stats)
        thesis_html = f'<p class="company-thesis">{text_with_citations(thesis)}</p>' if thesis else ''
        stats_html = f'<div class="company-stats">{stat_html}</div>' if stat_html else ''
        header = f'<div class="company-heading"><h3>{text_with_citations(title)}</h3>{thesis_html}{stats_html}</div>'
        return f'<article class="block company-analysis">{header}<div class="company-body">{body}</div></article>'
    if kind == 'timeline':
        items = block.get('items')
        if not isinstance(items, list) or not items:
            raise ValueError('timeline 需要 items')
        parts = []
        for item in items:
            parts.append(f'<div class="timeline-item"><div class="timeline-date">{esc(required_string(item,"date","timeline item"))}</div><div class="timeline-title">{text_with_citations(required_string(item,"title","timeline item"))}</div><p>{text_with_citations(item.get("detail",""))}</p></div>')
        return '<div class="block timeline">' + ''.join(parts) + '</div>'
    if kind == 'callout':
        tone = 'risk' if block.get('tone') == 'risk' else ''
        return f'<div class="block callout {tone}"><strong>{text_with_citations(required_string(block,"title","callout"))}</strong><p>{text_with_citations(required_string(block,"text","callout"))}</p></div>'
    raise ValueError(f'未知 block 类型：{kind}')


def validate_report(report):
    required_string(report, 'title', 'report')
    required_string(report, 'conclusion', 'report')
    version = report.get('schema_version', 1)
    if isinstance(version, bool) or version not in (1, 2):
        raise ValueError('schema_version 只支持 1 或 2')
    if not isinstance(report.get('summary', []), list):
        raise ValueError('summary 必须是数组')
    sections = report.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError('report 需要非空 sections')
    for section in sections:
        required_string(section, 'title', 'section')
        if not isinstance(section.get('blocks'), list):
            raise ValueError('section 需要 blocks 数组')
        if version == 2:
            required_string(section, 'conclusion', 'section')
            for block in section['blocks']:
                if not isinstance(block, dict):
                    raise ValueError('报告 block 必须是对象')
                if block.get('type') == 'heading':
                    required_string(block, 'conclusion', 'heading')
                if block.get('type') == 'cards':
                    for item in block.get('items', []):
                        required_string(item, 'summary', 'card')
                if block.get('type') == 'company':
                    required_string(block, 'thesis', 'company')
                    stats = block.get('stats')
                    if not isinstance(stats, list) or not stats:
                        raise ValueError('company 需要关键数字 stats')
                    for stat in stats:
                        required_string(stat, 'label', 'company stat')
                        required_string(stat, 'value', 'company stat')
                    parts = block.get('parts')
                    if not isinstance(parts, dict):
                        raise ValueError('company 需要五部分 parts 对象')
                    for key, _ in COMPANY_PARTS:
                        required_string(parts.get(key), 'conclusion', f'company.{key}')
                        required_string(parts.get(key), 'text', f'company.{key}')
    sources = report.get('sources', [])
    if not isinstance(sources, list) or not sources:
        raise ValueError('正式报告需要非空 sources 数组')
    ids = set()
    for source in sources:
        source_id = source.get('id') if isinstance(source, dict) else None
        if isinstance(source_id, bool) or not isinstance(source_id, int) or source_id < 1 or source_id in ids:
            raise ValueError('source.id 必须是唯一正整数')
        ids.add(source_id)
        required_string(source, 'title', 'source')
        if source.get('url'):
            if not isinstance(source['url'], str) or urlparse(source['url']).scheme not in {'http', 'https'}:
                raise ValueError('source.url 只支持 http 或 https')
    def citations(value):
        if isinstance(value, str):
            return {int(n) for n in re.findall(r'\[(\d+)\]', value)}
        if isinstance(value, list):
            return set().union(*(citations(item) for item in value)) if value else set()
        if isinstance(value, dict):
            return set().union(*(citations(item) for item in value.values())) if value else set()
        return set()
    missing = citations(report.get('sections', [])) | citations(report.get('summary', [])) | citations(report.get('conclusion', ''))
    missing -= ids
    if missing:
        raise ValueError(f'正文引用缺少来源：{sorted(missing)}')


def render_html(report):
    validate_report(report)
    title = report['title']
    subtitle = report.get('subtitle', '')
    meta = [('数据截至', report.get('as_of')), ('范围', report.get('scope'))]
    hero_meta = ''.join(f'<span>{esc(label)}：{esc(value)}</span>' for label, value in meta if value)
    hero = f'<header class="report-hero"><div class="eyebrow">EQUITY RESEARCH · 投资研究</div><h1>{esc(title)}</h1><p class="subtitle">{esc(subtitle)}</p><div class="hero-meta">{hero_meta}</div></header>'
    source_index = len(report['sections']) + 1
    disclaimer_index = source_index + 1
    navigation = '<nav class="toc" aria-label="报告目录"><div class="toc-title">报告目录</div><div class="toc-links">' + ''.join(f'<a href="#section-{i}"><span class="toc-index">{i:02d}</span>{esc(display_heading(s["title"]))}</a>' for i, s in enumerate(report['sections'], 1)) + f'<a href="#sources"><span class="toc-index">{source_index:02d}</span>数据来源</a><a href="#disclaimer"><span class="toc-index">{disclaimer_index:02d}</span>风险提示</a></div></nav>'
    summary = report.get('summary', [])
    summary_html = '<div class="summary-grid">' + ''.join(f'<div class="summary-card"><span class="label">{esc(required_string(item,"label","summary"))}</span><span class="value">{text_with_citations(required_string(item,"value","summary"))}</span><span class="detail">{text_with_citations(item.get("detail",""))}</span></div>' for item in summary) + '</div>' if summary else ''
    conclusion_html = f'<section class="opening-conclusion" aria-label="核心判断"><strong>核心判断</strong>{render_paragraphs(report["conclusion"])}</section>'
    sections_html = []
    for i, section in enumerate(report['sections'], 1):
        lead = f'<p class="section-conclusion">{text_with_citations(section["conclusion"])}</p>' if section.get('conclusion') else ''
        intro = f'<p class="section-intro">{text_with_citations(section["intro"])}</p>' if section.get('intro') else ''
        blocks_html = []
        heading_index = 0
        intro_after_first_heading = bool(intro and section['blocks'] and section['blocks'][0].get('type') == 'heading')
        for block in section['blocks']:
            if block.get('type') == 'heading':
                heading_index += 1
            blocks_html.append(render_block(block, heading_index if block.get('type') == 'heading' else None))
            if intro_after_first_heading and heading_index == 1 and block is section['blocks'][0]:
                blocks_html.append(intro)
        blocks = ''.join(blocks_html)
        sections_html.append(f'<section class="report-section" id="section-{i}"><h2><span class="section-index">{i:02d}</span>{esc(display_heading(section["title"]))}</h2>{lead}{"" if intro_after_first_heading else intro}{blocks}</section>')
    source_items = []
    for source in sorted(report.get('sources', []), key=lambda item:item['id']):
        url = source.get('url')
        link = f'<a href="{esc(url)}" rel="noopener noreferrer">查看来源</a>' if url else ''
        meta = ' · '.join(str(source.get(key, '')) for key in ('kind', 'date', 'usage') if source.get(key))
        source_items.append(f'<li id="source-{source["id"]}"><span class="source-id">[{source["id"]}]</span>{esc(source["title"])} {link}<span class="source-meta">{esc(meta)}</span></li>')
    sources_html = f'<section class="report-appendix" id="sources"><h2><span class="section-index">{source_index:02d}</span>数据来源</h2><ul class="sources-list">' + ''.join(source_items) + '</ul></section>'
    disclaimer_html = f'<section class="report-appendix" id="disclaimer"><h2><span class="section-index">{disclaimer_index:02d}</span>风险提示与免责声明</h2><ul class="disclaimer-list">' + ''.join(f'<li>{esc(item)}</li>' for item in DISCLAIMER) + '</ul></section>'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(title) + '</title><style>' + CSS + '</style></head><body>' + hero + '<main class="report-shell">' + navigation + summary_html + conclusion_html + ''.join(sections_html) + sources_html + disclaimer_html + '</main></body></html>'


def render_markdown(report):
    validate_report(report)
    lines = [f'# {report["title"]}', '']
    if report.get('subtitle'):
        lines += [report['subtitle'], '']
    if report.get('as_of'):
        lines += [f'数据截至：{report["as_of"]}', '']
    for item in report.get('summary', []):
        lines.append(f'- **{item["label"]}：** {item["value"]} {item.get("detail", "")}')
    if report.get('summary'):
        lines.append('')
    lines += ['## 核心判断', '', report['conclusion'], '']
    for i, section in enumerate(report['sections'], 1):
        lines += [f'## {i:02d} {display_heading(section["title"])}', '']
        if section.get('conclusion'):
            lines += [section['conclusion'], '']
        intro_after_first_heading = bool(section.get('intro') and section['blocks'] and section['blocks'][0].get('type') == 'heading')
        if section.get('intro') and not intro_after_first_heading:
            lines += [section['intro'], '']
        heading_index = 0
        for block_index, block in enumerate(section['blocks']):
            kind = block['type']
            if kind == 'paragraph': lines += [block['text'], '']
            elif kind == 'heading':
                heading_index += 1
                lines += [f'### {heading_index}）{display_heading(block["text"])}', '']
                if block.get('conclusion'): lines += [block['conclusion'], '']
                if intro_after_first_heading and block_index == 0: lines += [section['intro'], '']
            elif kind == 'list':
                lines += [f'{i}. {item}' if block.get('ordered') else f'- {item}' for i, item in enumerate(block['items'],1)] + ['']
            elif kind == 'metrics':
                lines += [f'- **{item["label"]}：** {item["value"]} {item.get("detail", "")}' for item in block['items']] + ['']
            elif kind == 'flow':
                lines += [f'**{block.get("title","筛选流程")}**', '']
                lines += [f'{i}. {step["title"]}：{step.get("detail", "")} ' + (f'{step["count"]}{step.get("count_unit", "只")}' if step.get('count') is not None else '') for i, step in enumerate(block['steps'],1)] + ['']
                if block.get('note'): lines += [block['note'], '']
            elif kind == 'table':
                lines += [f'**{block["caption"]}**', ''] if block.get('caption') else []
                lines += ['| ' + ' | '.join(str(c).replace('|','\\|') for c in block['columns']) + ' |', '| ' + ' | '.join('---' for _ in block['columns']) + ' |']
                lines += ['| ' + ' | '.join(str(c).replace('|','\\|') for c in row) + ' |' for row in block['rows']] + ['']
                if block.get('note'): lines += [block['note'], '']
            elif kind == 'chart':
                spec = block['spec']; lines += [f'**{spec["title"]}**（来源：{spec["source"]}）', '']
                columns = ['时间/对象'] + [s['name'] for s in spec['series']]
                lines += ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join('---' for _ in columns) + ' |']
                for i, label in enumerate(spec['x']):
                    lines.append('| ' + ' | '.join([label] + [str(s['values'][i]) if s['values'][i] is not None else '未披露' for s in spec['series']]) + ' |')
                lines.append('')
                if spec.get('note'): lines += [spec['note'], '']
            elif kind == 'cards':
                for card in block['items']:
                    lines += [f'### {display_heading(card["title"])}', '',card.get('summary',''),card.get('subtitle','')]
                    lines += [f'- {s["label"]}：{s["value"]}' for s in card.get('stats',[])] + ['']
            elif kind == 'company':
                lines += [f'### {display_heading(block["title"])}', '']
                if block.get('thesis'):
                    lines += [block['thesis'], '']
                lines += [f'- {stat["label"]}：{stat["value"]}' for stat in block.get('stats', [])] + [''] if block.get('stats') else []
                if block.get('parts'):
                    for key, label in COMPANY_PARTS:
                        part = block['parts'][key]
                        lines += [f'**{label}**', '', part['conclusion'], '', part['text'], '']
                else:
                    for item in block.get('analysis', block.get('points', [])):
                        lines += [f'**{display_heading(item.get("title", item.get("label", "分析")))}**', '', item['text'], '']
            elif kind == 'timeline':
                lines += [f'- **{item["date"]} · {item["title"]}：** {item.get("detail", "")}' for item in block['items']] + ['']
            elif kind == 'callout': lines += [f'> **{block["title"]}** {block["text"]}', '']
    lines += ['## 数据来源', '']
    for source in sorted(report.get('sources', []), key=lambda item:item['id']):
        parts = [f'[{source["id"]}] {source["title"]}']
        parts += [str(source[key]) for key in ('kind','date','usage','url') if source.get(key)]
        lines.append('- ' + '；'.join(parts))
    lines += ['', '## 风险提示与免责声明', ''] + [f'- {item}' for item in DISCLAIMER]
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description='从结构化数据生成原生 HTML 投研报告')
    parser.add_argument('report', type=Path, help='报告 JSON 文件')
    parser.add_argument('--output', type=Path, required=True, help='HTML 输出路径')
    parser.add_argument('--markdown-output', type=Path, help='可选的读者版 Markdown 输出路径')
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'))
    page = render_html(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding='utf-8')
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
