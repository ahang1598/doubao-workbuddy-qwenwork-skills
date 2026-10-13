#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证据时间线 HTML 生成脚本

两种输出模式（通过 --mode 参数切换，默认 timeline）：
  timeline  — 纵向 A4 可打印时间轴（默认，本技能主输出）
  mindmap   — 横向 A4 思维导图（根节点→年份→月份→事件卡片，SVG 贝塞尔连线）

使用方法：
    python3 generate_timeline_print.py \\
        --case-name "案件名称" \\
        --output "outputs/案件名称_时间线.html" \\
        --data-file "scripts/example_data.json" \\
        --mode timeline

依赖：Python 3.7+，无需额外安装包
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path


# ──────────────────────────────────────────────
# 事件类型自动识别关键词
# ──────────────────────────────────────────────
TYPE_RULES = [
    ("contract",   "合同签署", "type-contract",   ["合同", "协议", "签署", "签订", "签字", "盖章", "合作协议", "补充协议"]),
    ("payment",    "付款/资金", "type-payment",    ["付款", "支付", "缴纳", "转账", "回款", "保证金", "押金", "定金", "佣金", "货款", "工程款", "结算", "万元", "万$"]),
    ("breach",     "违约/逾期", "type-breach",     ["违约", "逾期", "未履行", "拒绝", "拒付", "未支付", "未取得", "逾期付款", "逾期未", "未按时"]),
    ("notice",     "通知/函件", "type-notice",     ["函", "通知", "律师函", "法务函", "催款", "催告", "告知", "发函", "函件", "律师信", "函发"]),
    ("deadline",   "约定节点", "type-deadline",   ["截止", "到期", "届满", "期限", "节点", "前", "之前", "约定", "期满"]),
    ("litigation", "诉讼准备", "type-litigation",  ["律师费", "诉讼费", "保险费", "诉讼", "保全", "仲裁", "立案", "起诉", "开庭", "判决", "申请"]),
    ("preparation","前期准备", "type-preparation", ["决议", "股东会", "尽职", "调查", "意向", "洽谈", "备忘录", "可行性"]),
]

DEFAULT_TYPE = ("default", "其他", "type-default")

# 类型 css class → 十六进制颜色（与模板保持一致）
TYPE_COLOR_HEX = {
    "type-preparation": "#4a6fa5",
    "type-contract":    "#2b6cb0",
    "type-payment":     "#276749",
    "type-breach":      "#c53030",
    "type-notice":      "#c05621",
    "type-litigation":  "#553c9a",
    "type-deadline":    "#975a16",
    "type-default":     "#4a5568",
}

# 年份节点颜色（按索引轮转）
YEAR_COLORS = [
    "#2b6cb0",  # 蓝
    "#276749",  # 绿
    "#553c9a",  # 紫
    "#975a16",  # 黄褐
    "#c53030",  # 红
    "#4a6fa5",  # 蓝灰
]


def detect_type(event_text: str):
    """根据事件描述文本自动检测类型"""
    for type_key, label, css_class, keywords in TYPE_RULES:
        for kw in keywords:
            if kw.rstrip("$") in event_text:
                return type_key, label, css_class
    return DEFAULT_TYPE


def _esc(s: str) -> str:
    """HTML 转义"""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ══════════════════════════════════════════════
#  MODE: mindmap — 横向 A4 思维导图
# ══════════════════════════════════════════════

def _parse_timeline_to_tree(timeline: list) -> tuple:
    """
    将 timeline 解析成有序树：
    返回 (year_order, years_data)
      year_order: [年份字符串, ...]（按升序）
      years_data: { year: { month_int: [event, ...] } }
    """
    years_data = {}   # { "2019": { 3: [ev,...], 8: [ev,...] } }
    year_order = []

    def add_event(year_str, month_int, ev):
        if year_str not in years_data:
            years_data[year_str] = {}
            year_order.append(year_str)
        if month_int not in years_data[year_str]:
            years_data[year_str][month_int] = []
        years_data[year_str][month_int].append(ev)

    for item in timeline:
        if "month" in item:
            # 分组格式：{"month": "2019年3月", "events": [...]}
            m = re.search(r"(\d{4})\D+(\d{1,2})", item.get("month", ""))
            if m:
                year_str  = m.group(1)
                month_int = int(m.group(2))
                for ev in item.get("events", []):
                    add_event(year_str, month_int, ev)
        else:
            # 平铺格式：{"date": "2019年3月1日", ...}
            m = re.search(r"(\d{4})\D+(\d{1,2})", item.get("date", ""))
            if m:
                year_str  = m.group(1)
                month_int = int(m.group(2))
                add_event(year_str, month_int, item)

    # 按年份升序排列
    year_order.sort()
    return year_order, years_data


def build_mindmap_html(timeline: list, case_name: str) -> tuple:
    """
    构建 CSS Grid 思维导图 HTML 节点 + SVG 连接线数据。

    返回 (nodes_html, connections_json, total_events)

    节点使用 grid-row / grid-column 定位（3 列）：
      col 1: 根节点（贯穿全部行）
      col 2: 具体日期节点（如 2019年3月29日）
      col 3: 事件卡片
    """
    year_order, years_data = _parse_timeline_to_tree(timeline)

    nodes_html  = []
    connections = []   # [[from_id, to_id, color, stroke_width], ...]
    total       = 0
    event_row   = 1    # 当前 grid-row（事件行从 1 开始递增）
    event_idx   = 0    # 全局事件序号

    date_node_defs  = []
    event_node_defs = []

    for yi, year in enumerate(year_order):
        months = years_data[year]
        for month in sorted(months.keys()):
            events = months[month]
            for ev in events:
                ev_id     = f"node-e-{event_idx}"
                event_idx += 1
                total     += 1

                # 构建日期节点标签：年份 + 日期字段
                ev_date_raw = ev.get("date", "")
                if re.search(r"\d{4}", ev_date_raw):
                    date_label = ev_date_raw        # 已含年份
                else:
                    date_label = f"{year}年{ev_date_raw}"  # 拼接年份

                date_id = f"node-d-{event_idx}"  # 每个事件独立日期节点

                # 日期节点 HTML（中灰）
                date_node_defs.append(
                    f'  <div class="mm-node mm-date" id="{date_id}"\n'
                    f'       style="grid-column:2;grid-row:{event_row}">\n'
                    f'    {_esc(date_label)}\n'
                    f'  </div>'
                )

                # 事件卡片 HTML
                ev_name     = _esc(ev.get("event",    ""))
                ev_summary  = _esc(ev.get("summary",  ""))
                ev_evidence = _esc(ev.get("evidence", ""))
                ev_page     = _esc(ev.get("page",     ""))
                ev_amount   = _esc(ev.get("amount",   ""))
                ev_note     = _esc(ev.get("note",     ""))

                # 摘要
                summary_html = (
                    f'<div class="mm-event-summary">{ev_summary}</div>'
                    if ev_summary else ""
                )

                # 元数据（纯文字，无图标）
                meta_parts = []
                if ev_evidence:
                    meta_parts.append(f'<span class="mm-event-badge">证据：{ev_evidence}</span>')
                if ev_page:
                    meta_parts.append(f'<span class="mm-event-badge">页码：{ev_page}</span>')
                meta_html = (
                    f'<div class="mm-event-meta">{"" .join(meta_parts)}</div>'
                    if meta_parts else ""
                )
                amount_html = (
                    f'<div class="mm-event-amount">{ev_amount}</div>'
                    if ev_amount else ""
                )
                note_html = (
                    f'<div class="mm-event-note">{ev_note}</div>'
                    if ev_note else ""
                )

                event_node_defs.append(
                    f'  <div class="mm-node mm-event" id="{ev_id}"\n'
                    f'       style="grid-column:3;grid-row:{event_row}">\n'
                    f'    <div class="mm-event-name">{ev_name}</div>\n'
                    f'    {summary_html}\n'
                    f'    {meta_html}\n'
                    f'    {amount_html}\n'
                    f'    {note_html}\n'
                    f'  </div>'
                )

                # 连接：根→日期，日期→事件
                connections.append(["node-root", date_id, "#888", 1.8])
                connections.append([date_id, ev_id, "#aaa", 1.0])
                event_row += 1

    # 根节点（贯穿全部行）
    root_span = max(event_row - 1, 1)
    root_html = (
        f'  <div class="mm-node mm-root" id="node-root"\n'
        f'       style="grid-column:1;grid-row:1/span {root_span}">\n'
        f'    {_esc(case_name)}\n'
        f'  </div>'
    )

    all_nodes = [root_html] + date_node_defs + event_node_defs

    nodes_html_str   = "\n".join(all_nodes)
    connections_json = json.dumps(connections, ensure_ascii=False)

    return nodes_html_str, connections_json, total


# ══════════════════════════════════════════════
#  MODE: timeline — 纵向 A4 时间轴（原版保留）
# ══════════════════════════════════════════════

def build_event_html(event: dict) -> str:
    """构建单条事件的 HTML（纵向时间轴模式）"""
    date_str   = event.get("date", "")
    event_name = event.get("event", "")
    summary    = event.get("summary", "")
    evidence   = event.get("evidence", "")
    page       = event.get("page", "")
    amount     = event.get("amount", "")
    note       = event.get("note", "")

    type_key, type_label, css_class = detect_type(event_name)

    summary_html = (
        f'<div class="event-summary {css_class}">{_esc(summary)}</div>'
        if summary else ""
    )

    meta_parts = []
    if evidence:
        meta_parts.append(
            f'<span class="event-badge"><span class="event-badge-label">证据：</span>{_esc(evidence)}</span>'
        )
    if page:
        meta_parts.append(
            f'<span class="event-badge"><span class="event-badge-label">页码：</span>{_esc(page)}</span>'
        )
    meta_html   = f'<div class="event-meta">{"".join(meta_parts)}</div>' if meta_parts else ""
    amount_html = f'<div class="event-amount">💰 {_esc(amount)}</div>' if amount else ""
    note_html   = f'<div class="event-note">📌 {_esc(note)}</div>'     if note   else ""

    return f"""    <div class="timeline-event">
      <div class="event-date {css_class}">{_esc(date_str)}</div>
      <div class="event-dot-col">
        <div class="event-dot {css_class}"></div>
      </div>
      <div class="event-card {css_class}">
        <div class="event-name">{_esc(event_name)}</div>
        {summary_html}
        {meta_html}
        {amount_html}
        {note_html}
      </div>
    </div>"""


def build_timeline_html(timeline: list) -> tuple:
    """
    构建完整时间线 HTML（纵向时间轴模式）。
    支持分组格式和平铺格式。
    """
    html_parts = []
    total = 0

    is_grouped = timeline and "month" in timeline[0]

    if is_grouped:
        for group in timeline:
            month  = group.get("month", "")
            events = group.get("events", [])
            if not events:
                continue
            month_html = (
                f'  <div class="month-group">\n'
                f'    <div class="month-label">{_esc(month)}</div>\n'
            )
            event_rows = []
            for ev in events:
                event_rows.append(build_event_html(ev))
                total += 1
            month_html += "\n".join(event_rows) + "\n  </div>\n"
            html_parts.append(month_html)
    else:
        current_month  = None
        current_events = []

        def flush_group(month_key, evs):
            if not evs:
                return ""
            rows = "\n".join(build_event_html(e) for e in evs)
            return (
                f'  <div class="month-group">\n'
                f'    <div class="month-label">{_esc(month_key)}</div>\n'
                f'{rows}\n  </div>\n'
            )

        for ev in timeline:
            date_str = ev.get("date", "")
            m = re.match(r"(\d{4})[年\-](\d{1,2})", date_str)
            if m:
                month_key = f"{m.group(1)}年{int(m.group(2))}月"
            else:
                month_key = date_str[:7] if len(date_str) >= 7 else "日期不详"

            if month_key != current_month:
                if current_month is not None:
                    html_parts.append(flush_group(current_month, current_events))
                current_month  = month_key
                current_events = []
            current_events.append(ev)
            total += 1

        if current_month and current_events:
            html_parts.append(flush_group(current_month, current_events))

    return "".join(html_parts), total


# ──────────────────────────────────────────────
# 模板加载
# ──────────────────────────────────────────────

def _load_template_file(name: str, custom_path=None) -> str:
    if custom_path:
        path = Path(custom_path)
    else:
        path = Path(__file__).parent.parent / "references" / name
    if not path.exists():
        print(f"错误：模板文件不存在：{path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def load_mindmap_template(custom_path=None) -> str:
    return _load_template_file("mindmap-template.html", custom_path)


def load_timeline_template(custom_path=None) -> str:
    return _load_template_file("timeline-print-template.html", custom_path)


# ──────────────────────────────────────────────
# 主生成函数
# ──────────────────────────────────────────────

def generate_html(case_name: str, data, output_path: str,
                  template_path=None, mode: str = "timeline"):
    """
    生成 HTML 文件。

    参数：
        case_name     案件名称
        data          dict 或 JSON 字符串（含 timeline 字段）
        output_path   输出 .html 文件路径
        template_path 可选，自定义模板路径
        mode          输出模式："timeline"（默认）或 "mindmap"
    """
    if isinstance(data, str):
        data_dict = json.loads(data)
    else:
        data_dict = data

    timeline = data_dict.get("timeline", [])
    if not timeline:
        print("警告：timeline 字段为空，将生成空内容", file=sys.stderr)

    generated_date = date.today().strftime("%Y年%m月%d日")

    if mode == "timeline":
        # ── 纵向时间轴模式（原版）──
        template = load_timeline_template(template_path)
        timeline_html, total_events = build_timeline_html(timeline)

        html = template
        html = html.replace("{CASE_NAME}",      case_name)
        html = html.replace("{GENERATED_DATE}", generated_date)
        html = html.replace("{TIMELINE_HTML}",  timeline_html)
        html = html.replace("{TOTAL_EVENTS}",   str(total_events))

    else:
        # ── 思维导图模式（默认）──
        template = load_mindmap_template(template_path)
        mindmap_html, connections_json, total_events = build_mindmap_html(
            timeline, case_name
        )

        html = template
        html = html.replace("{CASE_NAME}",        case_name)
        html = html.replace("{GENERATED_DATE}",   generated_date)
        html = html.replace("{MINDMAP_HTML}",     mindmap_html)
        html = html.replace("{CONNECTIONS_JSON}", connections_json)
        html = html.replace("{TOTAL_EVENTS}",     str(total_events))

    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    mode_label = "思维导图" if mode != "timeline" else "纵向时间轴"
    print(f"✓ {mode_label} HTML 已生成：{output_path}")
    print(f"  模式：{mode}  共 {total_events} 项事件")
    return output_path


# ──────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="生成证据时间线 HTML（思维导图 / 纵向时间轴）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例（思维导图，默认）：
  python3 generate_timeline_print.py \\
      --case-name "锦溪颐景御府项目" \\
      --output "outputs/锦溪颐景御府项目_思维导图.html" \\
      --data-file "scripts/example_data.json"

示例（纵向时间轴）：
  python3 generate_timeline_print.py \\
      --case-name "锦溪颐景御府项目" \\
      --output "outputs/锦溪颐景御府项目_时间线.html" \\
      --data-file "scripts/example_data.json" \\
      --mode timeline
        """,
    )
    parser.add_argument("--case-name",  required=True, help="案件名称")
    parser.add_argument("--output",     required=True, help="输出 HTML 文件路径")
    parser.add_argument("--data",       help="JSON 数据字符串")
    parser.add_argument("--data-file",  help="JSON 数据文件路径")
    parser.add_argument("--template",   help="自定义 HTML 模板路径")
    parser.add_argument(
        "--mode",
        choices=["mindmap", "timeline"],
        default="timeline",
        help="输出模式：timeline（纵向时间轴，默认）或 mindmap（思维导图）",
    )

    args = parser.parse_args()

    if not args.data and not args.data_file:
        parser.error("必须指定 --data 或 --data-file")

    if args.data_file:
        if not os.path.exists(args.data_file):
            print(f"错误：文件不存在：{args.data_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.data_file, "r", encoding="utf-8") as f:
            data = f.read()
    else:
        data = args.data

    try:
        generate_html(
            case_name=args.case_name,
            data=data,
            output_path=args.output,
            template_path=args.template,
            mode=args.mode,
        )
    except Exception as e:
        print(f"错误：生成失败：{e}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
