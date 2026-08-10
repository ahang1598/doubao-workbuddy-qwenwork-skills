#!/usr/bin/env python3
"""
渲染上市公司公告解读报告中用到的图表（折线图/柱状图/事件时间线图），
供 Markdown 以相对路径引用，或由 render_html_report.py 内嵌进 HTML。

输入 JSON 结构：
{
  "charts": [
    {
      "id": "revenue-trend",                # 必填，作为输出文件名（<id>.png）
      "type": "line" | "bar" | "event_timeline",  # 必填
      "title": "近5期营业收入与净利润（示例）", # 必填，写具体指标名，不要写"趋势图"这种空标题
      "x_label": "报告期",                   # 必填
      "y_label": "金额（亿元）",              # 必填，含单位
      "x": ["2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3"],  # line/bar 必填
      "series": [                            # line/bar 必填，至少一条
        {"name": "营业收入", "values": [12.1, 13.4, 12.8, 14.0, 15.2]},
        {"name": "净利润",  "values": [1.1, 1.4, 1.0, 1.6, 2.0]}
      ],
      "source_caption": "来源：公司定期报告（示例数据）"  # 必填，标注来源和口径
    }
  ]
}

event_timeline 类型（用于 linked-signals.md 第四节触发的"关联动态时间线"）用另一套字段，
不需要 x/series，改用 price_series + events：
{
  "id": "price-event-timeline",
  "type": "event_timeline",
  "title": "XX公司股价表现与关联事件时间线（示例）",
  "x_label": "日期",
  "y_label": "股价（元）",
  "price_series": {                          # 必填
    "dates": ["2026-06-20", "2026-06-23", "..."],   # 交易日序列，升序
    "values": [12.3, 12.5, 12.1, "..."]
  },
  "events": [                                # 必填，至少一条
    {"date": "2026-07-10", "label": "本次业绩预告", "category": "本公告"},
    {"date": "2026-06-20", "label": "股东减持公告", "category": "联动公告"},
    {"date": "2026-07-05", "label": "互动平台回复：解释产能问题", "category": "互动平台回复"}
  ],
  "source_caption": "来源：seed_finance_search 行情数据 + 公告/互动平台检索（示例数据）"
}
分类标签（category）用什么名字，图例就显示什么名字，不需要预先在脚本里注册；
event 的 date 如果不在 price_series.dates 里，会自动标到最近的交易日上。

用法：
  python3 render_charts.py --input chart-spec.json --output-dir charts
"""
import argparse
import json
import os
import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.lines as mlines
import matplotlib.pyplot as plt

COMMON_REQUIRED_FIELDS = ["id", "type", "title", "x_label", "y_label", "source_caption"]
LINE_BAR_REQUIRED_FIELDS = ["x", "series"]
EVENT_TIMELINE_REQUIRED_FIELDS = ["price_series", "events"]
SUPPORTED_CHART_TYPES = ("line", "bar", "event_timeline")

EVENT_CATEGORY_PALETTE = ["#C0392B", "#2980B9", "#8E44AD", "#16A085", "#D35400", "#7F8C8D"]

CJK_FONT_CANDIDATES = [
    "PingFang SC",
    "Heiti SC",
    "STHeiti",
    "Songti SC",
    "Arial Unicode MS",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "SimHei",
    "Microsoft YaHei",
    "WenQuanYi Zen Hei",
]


def configure_cjk_font():
    """尽量选一个系统里已装的中文字体，否则中文标题/坐标轴文字会渲染成方块。"""
    available = {f.name for f in fm.fontManager.ttflist}
    for name in CJK_FONT_CANDIDATES:
        if name in available:
            matplotlib.rcParams["font.sans-serif"] = [name] + list(
                matplotlib.rcParams.get("font.sans-serif", [])
            )
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name
    print(
        "警告：系统里没有找到可用的中文字体，图表中的中文可能显示为方块。"
        "如需正确显示，请安装一个中文字体（如 Noto Sans CJK）。",
        file=sys.stderr,
    )
    return None


def validate_chart(chart):
    chart_id = chart.get("id", "<unknown>")
    missing = [f for f in COMMON_REQUIRED_FIELDS if f not in chart]
    if missing:
        raise ValueError(f"图表 {chart_id} 缺少必填字段: {missing}")
    if chart["type"] not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"图表 {chart_id} 的 type 不支持: {chart['type']}（仅支持 line / bar / event_timeline）")

    if chart["type"] in ("line", "bar"):
        missing = [f for f in LINE_BAR_REQUIRED_FIELDS if f not in chart]
        if missing:
            raise ValueError(f"图表 {chart_id} 缺少必填字段: {missing}")
        if not chart["series"]:
            raise ValueError(f"图表 {chart_id} 的 series 不能为空")
        for s in chart["series"]:
            if len(s["values"]) != len(chart["x"]):
                raise ValueError(f"图表 {chart_id} 的系列 {s['name']} 数据点数量与 x 轴数量不一致")
    else:
        missing = [f for f in EVENT_TIMELINE_REQUIRED_FIELDS if f not in chart]
        if missing:
            raise ValueError(f"图表 {chart_id} 缺少必填字段: {missing}")
        price_series = chart["price_series"]
        if "dates" not in price_series or "values" not in price_series:
            raise ValueError(f"图表 {chart_id} 的 price_series 需要包含 dates 和 values")
        if len(price_series["dates"]) != len(price_series["values"]):
            raise ValueError(f"图表 {chart_id} 的 price_series 里 dates 和 values 数量不一致")
        if not price_series["dates"]:
            raise ValueError(f"图表 {chart_id} 的 price_series 不能为空")
        if not chart["events"]:
            raise ValueError(f"图表 {chart_id} 的 events 不能为空")
        for e in chart["events"]:
            for f in ("date", "label"):
                if f not in e:
                    raise ValueError(f"图表 {chart_id} 的 events 里有一项缺少字段: {f}")


def render_line(ax, chart):
    for s in chart["series"]:
        ax.plot(chart["x"], s["values"], marker="o", linewidth=1.8, label=s["name"])


def render_bar(ax, chart):
    series = chart["series"]
    n = len(series)
    x_positions = list(range(len(chart["x"])))
    width = 0.8 / max(n, 1)
    for i, s in enumerate(series):
        offsets = [p + (i - (n - 1) / 2) * width for p in x_positions]
        ax.bar(offsets, s["values"], width=width, label=s["name"])
    ax.set_xticks(x_positions)
    ax.set_xticklabels(chart["x"])


def _parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def _nearest_date_index(target_date, dates, date_index):
    """事件日期若不在交易日序列里（如非交易日发生的互动平台回复），标到最近的交易日上。"""
    if target_date in date_index:
        return date_index[target_date]
    target = _parse_date(target_date)
    diffs = [(abs((_parse_date(d) - target).days), i) for i, d in enumerate(dates)]
    return min(diffs)[1]


def render_event_timeline(ax, chart):
    dates = chart["price_series"]["dates"]
    values = chart["price_series"]["values"]
    x_positions = list(range(len(dates)))

    ax.plot(x_positions, values, color="#333333", linewidth=1.6, zorder=2)

    tick_step = max(1, len(dates) // 10)
    ax.set_xticks(x_positions[::tick_step])
    ax.set_xticklabels([dates[i] for i in x_positions[::tick_step]], rotation=45, ha="right", fontsize=8)

    date_index = {d: i for i, d in enumerate(dates)}
    y_min, y_max = min(values), max(values)
    y_span = (y_max - y_min) or max(abs(y_max), 1) * 0.1
    label_y = y_max + y_span * 0.08

    category_color = {}
    for event in chart["events"]:
        idx = _nearest_date_index(event["date"], dates, date_index)
        category = event.get("category", "事件")
        if category not in category_color:
            category_color[category] = EVENT_CATEGORY_PALETTE[len(category_color) % len(EVENT_CATEGORY_PALETTE)]
        color = category_color[category]
        ax.axvline(idx, color=color, linestyle="--", linewidth=1, alpha=0.75, zorder=1)
        ax.annotate(
            event["label"],
            xy=(idx, label_y),
            rotation=90,
            fontsize=7,
            color=color,
            ha="center",
            va="bottom",
        )

    ax.set_ylim(y_min - y_span * 0.15, y_max + y_span * 0.55)

    if category_color:
        handles = [
            mlines.Line2D([0], [0], color=color, linestyle="--", label=category)
            for category, color in category_color.items()
        ]
        ax.legend(handles=handles, fontsize=8, frameon=False, loc="upper left")


def render_chart(chart, output_dir):
    figsize = (9.5, 4.8) if chart["type"] == "event_timeline" else (7, 4.2)
    fig, ax = plt.subplots(figsize=figsize, dpi=160)

    if chart["type"] == "line":
        render_line(ax, chart)
    elif chart["type"] == "bar":
        render_bar(ax, chart)
    else:
        render_event_timeline(ax, chart)

    ax.set_title(chart["title"], fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel(chart["x_label"], fontsize=10)
    ax.set_ylabel(chart["y_label"], fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if chart["type"] in ("line", "bar") and len(chart["series"]) > 1:
        ax.legend(fontsize=9, frameon=False)

    fig.text(0.01, 0.01, chart["source_caption"], fontsize=8, color="#666666")
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    output_path = os.path.join(output_dir, f"{chart['id']}.png")
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="渲染公告解读报告用的图表")
    parser.add_argument("--input", required=True, help="图表规格 JSON 文件路径")
    parser.add_argument("--output-dir", required=True, help="输出 PNG 文件的目录")
    args = parser.parse_args()

    configure_cjk_font()

    with open(args.input, "r", encoding="utf-8") as f:
        spec = json.load(f)

    charts = spec.get("charts", [])
    if not charts:
        print("输入文件里没有 charts 字段或为空", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    manifest = {}
    for chart in charts:
        validate_chart(chart)
        path = render_chart(chart, args.output_dir)
        manifest[chart["id"]] = path
        print(f"生成图表: {chart['id']} -> {path}")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
