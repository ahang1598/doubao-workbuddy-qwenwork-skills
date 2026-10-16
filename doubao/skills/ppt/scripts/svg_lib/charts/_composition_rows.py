"""Shared category-row geometry for adjacent heterogeneous Cartesian panels."""

from ._chart_layout import wrap_lines
from ._composition import heading
from ._xy import CategoryScale, _axis_format


class RowScale(CategoryScale):
    """Stable category order from top to bottom for either renderer convention."""

    def map(self, value, p0, p1):
        return super().map(value, min(p0, p1), max(p0, p1))


def _gutters(panel, canvas):
    data, width = panel["data"], panel["_width"]
    categories = panel["axes"]["y"].categories
    fonts = panel["_fonts"]
    fs = fonts["label"]
    if panel["kind"] == "bar":
        left = min(180, max(canvas.measure(c, fs) for c in categories) + 18)
        plot_width = width - left - 15
        label = heading(data.get("x_title", "Value"), panel["axes"]["x"], data.get("x_unit", ""))
        top = max(26, len(wrap_lines(label, plot_width, fs, canvas.font)) * fs * 1.35 + 9)
        bottom = 52
        label_width = left - 15
    else:
        ys = panel["axes"]["y"]
        fmt = _axis_format(ys)[0]
        left = max(55, min(180, max((canvas.measure(fmt(v), fs) for v in ys.ticks or []), default=20) + 20))
        right = 168 if any(p.get("label") for s in panel["series"] for p in s["points"]) else 18
        left, right = panel.get("_axis_gutters", (left, right))
        plot_width = width - left - right
        label = heading(data.get("y_title", "Y"), ys, data.get("y_unit", ""))
        top = len(wrap_lines(label, plot_width, fs, canvas.font)) * fs * 1.35 + 9
        label = heading(data.get("x_title", "X"), panel["axes"]["x"], data.get("x_unit", ""))
        bottom = len(wrap_lines(label, plot_width, fs, canvas.font)) * fs * 1.35 + 30
        if panel.get("inset"):
            bottom += panel["inset_height"] + 24
        label_width = max(30, left - 20)
    label_height = max(len(wrap_lines(c, label_width, fs, canvas.font)) for c in categories) * fs * 1.35 + 14
    return top, bottom, len(categories) * max(38, label_height)


def align_category_rows(panels, positions, canvas):
    """Align supported mixed-family members of explicit Y groups in one row."""
    groups = {}
    for panel, (row, _, _) in zip(panels, positions):
        if panel.get("y_group") and isinstance(panel["axes"].get("y"), CategoryScale):
            groups.setdefault((row, str(panel["y_group"])), []).append(panel)
    for members in groups.values():
        kinds = {p["kind"] for p in members}
        if kinds != {"bar", "xy"}:
            continue
        for panel in members:
            # ChartLayout.text applies this bold-width allowance before wrapping.
            # Reserve the same lines so a long title cannot reach its legend.
            fonts = panel["_fonts"]
            panel["title_h"] = (
                len(wrap_lines(panel["name"], panel["_width"] / 1.05, fonts["group"], canvas.heading))
                * fonts["group"]
                * 1.35
                + 10
            )
            panel["header_h"] = max(
                panel["header_h"],
                panel["title_h"] + panel["legend_h"] + len(panel["note_lines"]) * fonts["foot"] * 1.35 + 18,
            )
        scale = RowScale(members[0]["axes"]["y"].categories)
        specs = [_gutters(panel, canvas) for panel in members]
        top, bottom, content = (max(spec[i] for spec in specs) for i in range(3))
        header = max(p["header_h"] for p in members)
        for panel in members:
            panel["axes"]["y"] = scale
            panel["header_h"] = header
            panel["_row_gutters"] = (top, bottom)
            panel["min_height"] = max(panel["min_height"], top + content + bottom)
