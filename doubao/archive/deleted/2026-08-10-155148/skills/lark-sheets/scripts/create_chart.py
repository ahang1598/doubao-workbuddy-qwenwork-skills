#!/usr/bin/env python3
"""
在指定 sheet 的指定锚点单元格创建图表（bar/line/pie/scatter/area）。

用法：
  python scripts/create_chart.py file.xlsx Data A1:D10 bar G2 \
      --title "季度销售" --x-axis "季度" --y-axis "销售额" --show-data-labels
  # 跨 sheet 数据源
  python scripts/create_chart.py file.xlsx Dashboard "Raw!A1:D10" line B5
"""
import argparse

from openpyxl.chart import AreaChart, BarChart, LineChart, PieChart, Reference, ScatterChart, Series
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.legend import Legend

from _excel_utils import emit, emit_error, load_or_create_wb, parse_cell, parse_range, require_sheet

CHART_CLASSES = {
    "bar": BarChart,
    "line": LineChart,
    "pie": PieChart,
    "scatter": ScatterChart,
    "area": AreaChart,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("filepath")
    p.add_argument("sheet", help="图表落点所在 sheet")
    p.add_argument("data_range", help='数据范围，如 "A1:D10"，跨 sheet 写 "Raw!A1:D10"')
    p.add_argument("chart_type", choices=list(CHART_CLASSES.keys()))
    p.add_argument("target_cell", help='图表锚点单元格，如 "G2"（支持多字母列如 "AA15"）')
    p.add_argument("--title", default="")
    p.add_argument("--x-axis", default="")
    p.add_argument("--y-axis", default="")
    p.add_argument("--width", type=float, default=15.0, help="图表宽（cm）")
    p.add_argument("--height", type=float, default=7.5, help="图表高（cm）")
    p.add_argument("--no-legend", action="store_true")
    p.add_argument("--legend-position", choices=["r", "l", "t", "b", "tr"], default="r")
    p.add_argument("--show-data-labels", action="store_true")
    p.add_argument("--show-percent", action="store_true", help="饼图百分比")
    p.add_argument("--grid-lines", action="store_true")
    args = p.parse_args()

    if "!" in args.data_range:
        src_sheet, cell_range = args.data_range.split("!", 1)
    else:
        src_sheet, cell_range = args.sheet, args.data_range

    if ":" not in cell_range:
        emit_error("data_range must be a rectangular range like 'A1:D10'")

    wb = load_or_create_wb(args.filepath)
    try:
        chart_ws = require_sheet(wb, args.sheet)
        src_ws = require_sheet(wb, src_sheet)
    except ValueError as e:
        emit_error(str(e))

    try:
        sr, sc, er, ec = parse_range(cell_range)
        anchor_row, anchor_col = parse_cell(args.target_cell)
    except ValueError as e:
        emit_error(str(e))

    chart_cls = CHART_CLASSES[args.chart_type]
    chart = chart_cls()
    chart.title = args.title or None
    if hasattr(chart, "x_axis"):
        chart.x_axis.title = args.x_axis or None
    if hasattr(chart, "y_axis"):
        chart.y_axis.title = args.y_axis or None

    try:
        if args.chart_type == "scatter":
            for col in range(sc + 1, ec + 1):
                x_values = Reference(src_ws, min_row=sr + 1, max_row=er, min_col=sc)
                y_values = Reference(src_ws, min_row=sr + 1, max_row=er, min_col=col)
                series = Series(y_values, x_values, title_from_data=True)
                chart.series.append(series)
        else:
            data = Reference(src_ws, min_row=sr, max_row=er, min_col=sc + 1, max_col=ec)
            cats = Reference(src_ws, min_row=sr + 1, max_row=er, min_col=sc)
            chart.add_data(data, titles_from_data=True)
            chart.set_categories(cats)
    except Exception as e:
        emit_error(f"Failed to bind data references: {e}")

    if args.no_legend:
        chart.legend = None
    else:
        chart.legend = Legend()
        chart.legend.position = args.legend_position

    if args.show_data_labels or args.show_percent:
        labels = DataLabelList()
        labels.showVal = args.show_data_labels and not args.show_percent
        labels.showPercent = args.show_percent
        chart.dataLabels = labels

    if args.grid_lines:
        if hasattr(chart, "x_axis"):
            chart.x_axis.majorGridlines = ChartLines()
        if hasattr(chart, "y_axis"):
            chart.y_axis.majorGridlines = ChartLines()

    chart.width = args.width
    chart.height = args.height

    # openpyxl 的 add_chart 接收 "G2" 字符串锚点；我们已经做过 parse_cell 校验
    anchor_str = f"{args.target_cell.upper()}"
    try:
        chart_ws.add_chart(chart, anchor_str)
        wb.save(args.filepath)
    except Exception as e:
        emit_error(f"Failed to add chart: {e}")

    emit({
        "status": "success",
        "chart_type": args.chart_type,
        "anchor": anchor_str,
        "data_range": f"{src_sheet}!{cell_range}",
        "sheet": args.sheet,
    })


if __name__ == "__main__":
    main()
