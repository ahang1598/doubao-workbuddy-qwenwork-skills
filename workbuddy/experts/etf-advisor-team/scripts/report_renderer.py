#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ETF 报告 HTML 渲染引擎。

将 Markdown 报告渲染为带 ECharts 图表的专业 HTML 报告。

策略：Markdown → HTML 片段（保留全部内容） → 注入页面骨架 + 图表数据。
所有结论、数据、推导、信源以 Markdown 为权威中间产物，HTML 是可视化最终交付物。

用法:
  python report_renderer.py --markdown OutputReport/报告.md --intent full --output OutputReport/报告.html

注：v2 起已移除 --data / --scaffold 模式，Markdown 是唯一权威输入。
"""

from __future__ import annotations

# --- UTF-8 bootstrap (auto-injected, idempotent) ---
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
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from jinja2 import Environment, FileSystemLoader, Markup
except ImportError:
    try:
        from jinja2 import Environment, FileSystemLoader
        from markupsafe import Markup
    except ImportError:
        print("[错误] 需要安装 jinja2: pip install jinja2>=3.1.0", file=sys.stderr)
        sys.exit(1)


# ============================================================
# Paths
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = SKILL_DIR / "templates"


# ============================================================
# Markdown → HTML conversion (lightweight, no external deps)
# ============================================================

def _md_escape_html(text: str) -> str:
    """Escape HTML special chars in text content (not in already-processed tags)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _parse_inline(text: str) -> str:
    """Process inline Markdown: bold, code, links, images."""
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Links: [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # Emoji safe-pass (already unicode)
    return text


def _convert_md_table(lines: List[str]) -> str:
    """Convert Markdown table lines to HTML table."""
    if len(lines) < 2:
        return ""
    header_cells = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    # Skip separator line (lines[1])
    html_parts = ['<div class="table-wrapper"><table>']
    html_parts.append("<thead><tr>")
    for cell in header_cells:
        html_parts.append(f"<th>{_parse_inline(cell)}</th>")
    html_parts.append("</tr></thead>")
    html_parts.append("<tbody>")
    for row_line in lines[2:]:
        cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
        html_parts.append("<tr>")
        for i, cell in enumerate(cells):
            styled = _parse_inline(cell)
            # Color trends
            if "↑" in cell or cell.startswith("+"):
                styled = f'<span class="trend-up">{styled}</span>'
            elif "↓" in cell or (cell.startswith("-") and "%" in cell):
                styled = f'<span class="trend-down">{styled}</span>'
            html_parts.append(f"<td>{styled}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table></div>")
    return "\n".join(html_parts)


def markdown_to_html_sections(md_text: str) -> Tuple[Dict[str, str], List[Dict[str, str]], str]:
    """Parse Markdown report into structured sections.

    Returns:
        (meta_dict, sections_list, footer_html)
        meta_dict: {title, data_time, risk_preference, invest_horizon, ...}
        sections_list: [{id, title, nav_label, icon, content_html}, ...]
        footer_html: disclaimer text
    """
    lines = md_text.splitlines()
    meta: Dict[str, str] = {}
    sections: List[Dict[str, str]] = []
    footer = ""

    # Icons for section titles
    section_icons = {
        "全球宏观": "🌍", "国际市场": "🌍",
        "国内宏观": "🏛️",
        "大类资产": "📊", "资产配置": "📊",
        "行业赛道": "🏭", "行业配置": "🏭",
        "推荐标的": "🎯", "标的明细": "🎯",
        "操作执行": "📋", "操作计划": "📋",
        "风险提示": "⚠️",
        "附录": "📎",
    }

    # Extract title
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if title_match:
        meta["title"] = title_match.group(1).strip()

    # Extract meta line
    meta_line_match = re.search(r"\*\*数据采集时间\*\*:\s*(.+?)(?:\s*\||\s*$)", md_text, re.MULTILINE)
    if meta_line_match:
        meta["data_time"] = meta_line_match.group(1).strip()
    for key, pattern in [
        ("risk_preference", r"\*\*风险偏好\*\*:\s*(.+?)\s*\|"),
        ("invest_horizon", r"\*\*投资周期\*\*:\s*(.+?)(?:\s*\||$)"),
        ("fund_attribute", r"\*\*资金属性\*\*:\s*(.+?)(?:\s*\||$)"),
        ("product_type", r"\*\*产品形态\*\*:\s*(.+?)(?:\s*\||$)"),
    ]:
        m = re.search(pattern, md_text, re.MULTILINE)
        if m:
            meta[key] = m.group(1).strip()

    # Split into sections by ## headings
    section_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(section_pattern.finditer(md_text))

    sec_counter = 0
    for idx, match in enumerate(matches):
        sec_title = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md_text)
        sec_body = md_text[start:end].strip()

        # Skip appendix section — it will be rendered by the template's built-in appendix block
        if "附录" in sec_title:
            continue

        sec_counter += 1
        # Generate section id (no "section-" prefix; template adds "section-" via id="section-{{ sec.id }}")
        sec_id = str(sec_counter)
        # Determine nav label (short but not too short)
        nav_label = sec_title
        for cn_num in ["一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、"]:
            nav_label = nav_label.replace(cn_num, "")
        nav_label = nav_label.strip()[:12]

        # Determine icon
        icon = "📄"
        for keyword, ic in section_icons.items():
            if keyword in sec_title:
                icon = ic
                break

        # Convert section body to HTML
        content_html = _convert_section_body(sec_body)

        sections.append({
            "id": sec_id,
            "title": sec_title,
            "nav_label": nav_label,
            "icon": icon,
            "content_html": content_html,
        })

    # Footer (disclaimer)
    disclaimer_match = re.search(r"⚠️\s*(.+?)(?:\n---|$)", md_text, re.DOTALL)
    if disclaimer_match:
        footer = disclaimer_match.group(0).strip().rstrip("-").strip()

    return meta, sections, footer


def _convert_section_body(body: str) -> str:
    """Convert a section body (Markdown between ## headings) to HTML."""
    lines = body.splitlines()
    html_parts: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip horizontal rules
        if re.fullmatch(r"-{3,}", stripped):
            i += 1
            continue

        # H3: ### heading
        h3_match = re.match(r"^###\s+(.+)$", stripped)
        if h3_match:
            heading = _parse_inline(h3_match.group(1))
            html_parts.append(f'<h3 class="subsection-title">{heading}</h3>')
            i += 1
            continue

        # H4: #### heading
        h4_match = re.match(r"^####\s+(.+)$", stripped)
        if h4_match:
            heading = _parse_inline(h4_match.group(1))
            html_parts.append(f'<h4 class="detail-title">{heading}</h4>')
            i += 1
            continue

        # Three-stage labels: 📊 / 🔍 / 📌
        stage_match = re.match(r"^(📊|🔍|📌)\s+\*\*(.+?)\*\*(.*)$", stripped)
        if stage_match:
            emoji, label, rest = stage_match.groups()
            stage_class = {"📊": "stage-data", "🔍": "stage-analysis", "📌": "stage-conclusion"}.get(emoji, "")
            html_parts.append(f'<div class="card"><div class="card-title"><span class="emoji">{emoji}</span> {_parse_inline(label)}</div>')
            # Strip leading colons (：or :) from rest text
            rest_clean = re.sub(r"^[：:]+\s*", "", rest.strip())
            if rest_clean:
                html_parts.append(f'<p>{_parse_inline(rest_clean)}</p>')
            i += 1
            # Collect content until next stage/heading/table
            inner_html = []
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(r"^(📊|🔍|📌)\s+\*\*", next_line):
                    break
                if re.match(r"^#{2,4}\s+", next_line):
                    break
                if re.fullmatch(r"-{3,}", next_line):
                    break
                # Table inside a stage
                if next_line.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                    table_lines = []
                    while i < len(lines) and lines[i].strip().startswith("|"):
                        table_lines.append(lines[i])
                        i += 1
                    inner_html.append(_convert_md_table(table_lines))
                    continue
                # Ordered list
                if re.match(r"^\d+\.\s+", next_line):
                    ol_items = []
                    while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                        item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                        ol_items.append(f"<li>{_parse_inline(item_text)}</li>")
                        i += 1
                    inner_html.append('<ol class="analysis-list">' + "\n".join(ol_items) + "</ol>")
                    continue
                # Unordered list
                if next_line.startswith("- "):
                    ul_items = []
                    while i < len(lines) and (lines[i].strip().startswith("- ") or lines[i].strip().startswith("  ")):
                        item_line = lines[i].strip()
                        if item_line.startswith("- "):
                            ul_items.append(f"<li>{_parse_inline(item_line[2:])}</li>")
                        else:
                            # continuation of previous item
                            if ul_items:
                                ul_items[-1] = ul_items[-1].replace("</li>", f" {_parse_inline(item_line)}</li>")
                        i += 1
                    inner_html.append('<ul class="analysis-list">' + "\n".join(ul_items) + "</ul>")
                    continue
                # Blockquote
                if next_line.startswith("> "):
                    bq_lines = []
                    while i < len(lines) and lines[i].strip().startswith("> "):
                        bq_lines.append(_parse_inline(lines[i].strip()[2:]))
                        i += 1
                    inner_html.append('<blockquote class="conclusion-box">' + "<br>".join(bq_lines) + "</blockquote>")
                    continue
                # Conclusion box pattern: "- **XX**：YY"
                if next_line.startswith("- **") and "：" in next_line:
                    concl_items = []
                    while i < len(lines) and lines[i].strip().startswith("- **"):
                        concl_items.append(f"<li>{_parse_inline(lines[i].strip()[2:])}</li>")
                        i += 1
                    inner_html.append('<div class="conclusion-box"><ul style="list-style:none;padding:0;margin:0;">' + "\n".join(concl_items) + "</ul></div>")
                    continue
                # Empty line
                if not next_line:
                    i += 1
                    continue
                # Regular paragraph
                inner_html.append(f"<p>{_parse_inline(next_line)}</p>")
                i += 1

            html_parts.append("\n".join(inner_html))
            html_parts.append("</div>")  # close card
            continue

        # Standalone table (not inside a stage)
        if stripped.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            html_parts.append(f'<div class="card">{_convert_md_table(table_lines)}</div>')
            continue

        # Ordered list (standalone)
        if re.match(r"^\d+\.\s+", stripped):
            ol_items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                ol_items.append(f"<li>{_parse_inline(item_text)}</li>")
                i += 1
            html_parts.append(f'<div class="card"><ol class="analysis-list">{"".join(ol_items)}</ol></div>')
            continue

        # Unordered list (standalone)
        if stripped.startswith("- "):
            ul_items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or (lines[i].startswith("  ") and lines[i].strip())):
                item_line = lines[i].strip()
                if item_line.startswith("- "):
                    ul_items.append(f"<li>{_parse_inline(item_line[2:])}</li>")
                elif ul_items:
                    ul_items[-1] = ul_items[-1].replace("</li>", f" {_parse_inline(item_line)}</li>")
                i += 1
            html_parts.append(f'<div class="card"><ul class="analysis-list">{"".join(ul_items)}</ul></div>')
            continue

        # Blockquote
        if stripped.startswith("> "):
            bq_lines = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                bq_lines.append(_parse_inline(lines[i].strip()[2:]))
                i += 1
            html_parts.append(f'<blockquote class="conclusion-box">{"<br>".join(bq_lines)}</blockquote>')
            continue

        # Regular paragraph
        if stripped:
            html_parts.append(f"<p>{_parse_inline(stripped)}</p>")
        i += 1

    return "\n".join(html_parts)


# ============================================================
# Chart data extraction from Markdown tables
# ============================================================

def extract_chart_data_from_md(md_text: str) -> Dict[str, Any]:
    """Extract chart data from Markdown report tables for ECharts visualization.

    鲁棒性增强（v2）：
    1. 章节定位：支持多种标题关键词（"推荐标的"/"基金筛选"/"标的池"/"投资组合"等）
    2. 表头识别：配置/权重列通过正则模糊匹配，不依赖固定"配置比例"字面
    3. 列索引：通过表头关键词动态定位，不硬编码位置（解决列顺序不一致问题）
    4. 数据校验：提取结果为空时 key 不写入，避免渲染出空白图表容器
    """
    chart_data: Dict[str, Any] = {}

    # 1. Global macro data → KPI 备用数据（不直接绘图）
    global_section = _extract_section_between_any(
        md_text,
        start_keywords=["全球宏观", "国际市场"],
        end_keywords=["国内宏观", "大类资产"],
    )
    if global_section:
        kpis = _extract_table_data(global_section)
        if kpis:
            chart_data["_global_kpis"] = kpis

    # 2. Allocation pie → 从「大类资产配置」章节找配置/权重表
    alloc_section = _extract_section_between_any(
        md_text,
        start_keywords=["大类资产配置", "资产配置"],
        end_keywords=["行业赛道", "行业配置", "基金筛选", "标的池", "推荐标的"],
    )
    if alloc_section:
        pie_data = _extract_allocation_pie(alloc_section)
        if pie_data:
            chart_data["allocation_pie"] = {"data": pie_data}

    # 3. Sector bar 图已移除（行业数据通过表格+视觉标记呈现即可，图表信息密度低）

    # 4. Fund comparison bar → 从「推荐标的/投资组合/基金筛选」找最终配置表
    fund_section = _extract_section_between_any(
        md_text,
        start_keywords=["投资组合与操作", "推荐标的", "标的明细", "基金筛选与标的", "最终配置"],
        end_keywords=["风险提示", "附录", "补充说明"],
    )
    if fund_section:
        fund_comp = _extract_fund_comparison(fund_section)
        if fund_comp:
            chart_data["fund_comparison"] = fund_comp

    return chart_data


def _extract_section_between_any(
    text: str,
    start_keywords: List[str],
    end_keywords: List[str],
) -> Optional[str]:
    """在 ## 标题中，按多关键词查找起始/结束点，返回之间的正文。"""
    start_idx = -1
    for kw in start_keywords:
        m = re.search(rf"(?m)^##\s+.*{re.escape(kw)}.*$", text)
        if m and (start_idx < 0 or m.end() < start_idx):
            start_idx = m.end()
    if start_idx < 0:
        return None
    end_idx = len(text)
    for kw in end_keywords:
        m = re.search(rf"(?m)^##\s+.*{re.escape(kw)}.*$", text[start_idx:])
        if m:
            candidate = start_idx + m.start()
            if candidate < end_idx:
                end_idx = candidate
    return text[start_idx:end_idx]


def _find_col_index(header: List[str], keywords: List[str]) -> int:
    """在表头列表中查找第一个匹配任一关键词的列索引，返回 -1 表示未找到。"""
    for idx, cell in enumerate(header):
        for kw in keywords:
            if kw in cell:
                return idx
    return -1


def _extract_allocation_pie(section_text: str) -> List[Dict[str, Any]]:
    """从资产配置章节提取饼图数据。

    识别策略：
    - 表头必须至少包含"比例/权重/仓位/配置"之一
    - 首列识别为资产类别名，目标列识别为百分比
    - 过滤掉"合计/总计"等汇总行
    """
    colors = {
        "权益": "#dc2626", "股票": "#dc2626",
        "债券": "#3b82f6", "固收": "#3b82f6", "纯债": "#3b82f6",
        "商品": "#f59e0b", "黄金": "#f59e0b",
        "现金": "#6b7280", "货币": "#6b7280",
        "QDII": "#8b5cf6",
    }
    tables = _find_md_tables(section_text)
    for tbl in tables:
        header = tbl["header"]
        # 找百分比列
        pct_col = _find_col_index(header, ["配置比例", "比例", "权重", "仓位"])
        if pct_col < 0:
            continue
        # 首列作为名称
        pie_data = []
        for row in tbl["rows"]:
            if len(row) <= pct_col:
                continue
            name = row[0] if row else ""
            # 过滤合计行
            if re.search(r"合计|总计|小计|Total", name, re.IGNORECASE):
                continue
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", row[pct_col])
            if not pct_match:
                continue
            clean_name = re.sub(r"[（(].*?[）)]", "", name).strip()
            if not clean_name:
                continue
            pie_data.append({"name": clean_name[:12], "value": float(pct_match.group(1))})
        if pie_data and len(pie_data) >= 2:
            # 验证总和合理（80%-120%，避免用到了"单只基金配置"这种列）
            total = sum(item["value"] for item in pie_data)
            if 80 <= total <= 120:
                return pie_data
    return []


def _extract_sector_bar_DEPRECATED(section_text: str) -> Optional[Dict[str, Any]]:
    """[已废弃] 原行业赛道柱图提取逻辑。保留函数骨架供历史追溯，调用点已移除。

    移除原因：行业数据以「行业/赛道 | 景气度信号 | 近期涨跌 | 估值」表格形式
    呈现已足够清晰；景气度评分柱图信息密度低、易误导，故移除图表、保留表格。
    """
    return None





def _extract_fund_comparison(section_text: str) -> Optional[Dict[str, Any]]:
    """从推荐标的章节提取基金对比柱状图。

    识别策略：
    - 优先找同时包含"代码"和"比例/权重"的配置表
    - 用表头关键词动态定位 近1年/近3年/配置比例 列
    - 最多展示前10只
    """
    tables = _find_md_tables(section_text)
    for tbl in tables:
        header = tbl["header"]
        header_str = " ".join(header)
        # 必须同时有"代码"和（"比例"或"权重"）
        if "代码" not in header_str:
            continue
        if not re.search(r"比例|权重|配置", header_str):
            continue

        name_col = _find_col_index(header, ["简称", "名称", "基金名", "ETF"])
        if name_col < 0:
            # 降级：用"代码"的下一列
            code_col = _find_col_index(header, ["代码"])
            name_col = code_col + 1 if code_col >= 0 else 1
        r1y_col = _find_col_index(header, ["近1年", "1年收益", "近一年"])
        r3y_col = _find_col_index(header, ["近3年", "3年收益", "近三年"])
        weight_col = _find_col_index(header, ["配置比例", "比例", "权重", "仓位"])

        funds: List[str] = []
        r1y_vals: List[float] = []
        r3y_vals: List[float] = []
        weight_vals: List[float] = []

        for row in tbl["rows"]:
            if len(row) <= name_col:
                continue
            raw_name = row[name_col]
            # 过滤合计行、分隔行
            if not raw_name or re.search(r"合计|总计|小计", raw_name):
                continue
            # 清理 Markdown 强调符号
            short_name = re.sub(r"[*_`]", "", raw_name).strip()
            if len(short_name) > 12:
                short_name = short_name[:12]
            if not short_name:
                continue

            r1y = _extract_number(row[r1y_col]) if r1y_col >= 0 and r1y_col < len(row) else None
            r3y = _extract_number(row[r3y_col]) if r3y_col >= 0 and r3y_col < len(row) else None
            wt = _extract_number(row[weight_col]) if weight_col >= 0 and weight_col < len(row) else None

            funds.append(short_name)
            r1y_vals.append(r1y if r1y is not None else 0)
            r3y_vals.append(r3y if r3y is not None else 0)
            weight_vals.append(wt if wt is not None else 0)

        if len(funds) < 3:
            continue

        # 限制为前10只
        funds = funds[:10]
        r1y_vals = r1y_vals[:10]
        r3y_vals = r3y_vals[:10]
        weight_vals = weight_vals[:10]

        # 如果至少有一列有有效数据（>0），就生成图
        has_r1y = any(v != 0 for v in r1y_vals)
        has_r3y = any(v != 0 for v in r3y_vals)
        has_wt = any(v != 0 for v in weight_vals)

        if not (has_r1y or has_r3y or has_wt):
            continue

        series = []
        if has_r1y:
            series.append({"name": "近1年(%)", "type": "bar", "data": r1y_vals, "itemStyle": {"color": "#3b82f6"}})
        if has_r3y:
            series.append({"name": "近3年(%)", "type": "bar", "data": r3y_vals, "itemStyle": {"color": "#f59e0b"}})
        if has_wt and not (has_r1y or has_r3y):
            # 只有权重列可用时，画权重分布
            series.append({"name": "配置比例(%)", "type": "bar", "data": weight_vals, "itemStyle": {"color": "#059669"}})

        if series:
            return {"funds": funds, "series": series}
    return None


# 保留原 _extract_section_between 以兼容其他调用点
def _extract_section_between_legacy(text: str, start_keyword: str, end_keyword: str) -> Optional[str]:
    return _extract_section_between_any(text, [start_keyword], [end_keyword])


def _extract_section_between(text: str, start_keyword: str, end_keyword: str) -> Optional[str]:
    """向后兼容 wrapper，内部转发到 _extract_section_between_any。"""
    return _extract_section_between_any(text, [start_keyword], [end_keyword])


def _find_md_tables(text: str) -> List[Dict[str, Any]]:
    """Find all Markdown tables in text."""
    tables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and i + 1 < len(lines):
            header_cells = [c.strip() for c in line.strip("|").split("|")]
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if next_line.startswith("|") and all(
                re.fullmatch(r":?-{2,}:?", c.strip())
                for c in next_line.strip("|").split("|") if c.strip()
            ):
                rows = []
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    row_cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                    rows.append(row_cells)
                    j += 1
                tables.append({"header": header_cells, "rows": rows})
                i = j
                continue
        i += 1
    return tables


def _extract_table_data(text: str) -> List[Dict[str, str]]:
    """Extract first table in text as list of dicts with col0, col1, ... keys."""
    tables = _find_md_tables(text)
    if not tables:
        return []
    tbl = tables[0]
    result = []
    for row in tbl["rows"]:
        d = {}
        for j, cell in enumerate(row):
            d[f"col{j}"] = cell
        result.append(d)
    return result


def _extract_number(s: str) -> Optional[float]:
    """Extract first number from string."""
    m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", s.replace(",", ""))
    if m:
        try:
            return float(m.group().replace(",", ""))
        except ValueError:
            pass
    return None


# ============================================================
# Rendering
# ============================================================

def render_from_markdown(md_path: Path, intent: str, output_path: Path) -> str:
    """Main entry: Markdown → HTML report."""
    md_text = md_path.read_text(encoding="utf-8-sig")

    # Parse Markdown into sections
    meta, sections, footer = markdown_to_html_sections(md_text)

    # Extract chart data
    chart_data = extract_chart_data_from_md(md_text)

    # Extract appendix data sources
    data_sources = _extract_appendix_sources(md_text)

    # Load Jinja2 template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,  # We handle escaping manually in MD→HTML conversion
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("report_base.html")

    # Build template context - mark content as safe
    sections_for_tpl = []
    for sec in sections:
        sections_for_tpl.append({
            "id": sec["id"],
            "nav_label": sec["nav_label"],
            "icon": sec["icon"],
            "title": sec["title"],
            "content": Markup(sec["content_html"]),  # Mark as safe HTML
        })

    html = template.render(
        report=meta,
        sections=sections_for_tpl,
        chart_data=chart_data,
        chart_flags={
            "has_allocation_pie": bool(chart_data.get("allocation_pie")),
            "has_fund_comparison": bool(chart_data.get("fund_comparison")),
        },
        data_sources=data_sources,
        footer_text=footer,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    _print_utf8(f"[成功] HTML 报告已保存: {output_path}")
    return html


def render_from_json(data: Dict[str, Any], output_path: Path) -> str:
    """⚠️ 此入口已废弃。

    团队规范规定 Markdown 为唯一权威输入，强制走 Markdown → HTML 两步流程。
    保留此函数签名仅为向后兼容；直接调用会抛出 DeprecationWarning 并引导用户切换。
    """
    raise NotImplementedError(
        "render_from_json 已废弃。请先将结构化数据写成 Markdown 报告，再调用 "
        "`report_renderer.py --markdown <path>.md`。详见 references/output_pipeline.md。"
    )


def _extract_appendix_sources(md_text: str) -> List[Dict[str, str]]:
    """Extract data sources from appendix table.

    识别策略（v3 鲁棒性增强）：
    1. 优先匹配标准格式「## 附录：数据信源汇总表」
    2. 兜底匹配任何含「附录」和「信源」的 ## 标题
    3. 最后兜底匹配含「信源」的 ## 标题（如"第八章 数据信源汇总表"）
    """
    appendix: Optional[str] = None

    # 策略1: 标准格式「## 附录...信源...」
    match = re.search(r"(?m)^##\s+附录.*信源", md_text)
    if match:
        appendix = md_text[match.end():]

    # 策略2: 兜底 — 任何含「信源汇总」的 ## 标题（即使没写"附录"）
    if not appendix:
        match = re.search(r"(?m)^##\s+.*(?:数据信源|信源汇总)", md_text)
        if match:
            appendix = md_text[match.end():]

    if not appendix:
        return []
    tables = _find_md_tables(appendix)
    sources = []
    for tbl in tables:
        for row in tbl["rows"]:
            if len(row) >= 5:
                sources.append({
                    "id": row[0].strip(),
                    "name": row[1].strip(),
                    "type": row[2].strip(),
                    "url": row[3].strip(),
                    "date": row[4].strip(),
                })
    return sources


def generate_scaffold(intent: str = "full") -> Dict[str, Any]:
    """⚠️ 此入口已废弃。

    团队规范规定 Markdown 为唯一权威输入，不再提供 JSON scaffold 模板。
    Agent 请直接按 references/output_format.md 的模板写 Markdown 报告。
    """
    raise NotImplementedError(
        "generate_scaffold 已废弃。请参考 references/output_format.md 的 Markdown "
        "报告模板，直接撰写 .md 文件后调用 report_renderer.py --markdown。"
    )


def _print_utf8(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ETF 报告 HTML 渲染引擎（Markdown→HTML + ECharts 图表）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "注：--data / --scaffold 模式已废弃（v2）。"
            "Markdown 是团队的唯一权威输入，请用 --markdown 渲染。"
        ),
    )
    parser.add_argument("--markdown", required=True, help="已有 Markdown 报告路径")
    parser.add_argument("--intent", default="full", choices=["full", "sector", "compare", "mixed"], help="报告意图类型")
    parser.add_argument("--output", "-o", help="输出文件路径（默认同名 .html）")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    md_path = Path(args.markdown)
    if not md_path.exists():
        print(f"[错误] Markdown 文件不存在: {md_path}", file=sys.stderr)
        sys.exit(2)
    output_path = Path(args.output) if args.output else md_path.with_suffix(".html")
    render_from_markdown(md_path, args.intent, output_path)


if __name__ == "__main__":
    main()
