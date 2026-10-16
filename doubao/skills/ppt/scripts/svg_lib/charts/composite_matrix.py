"""Matrix plot adapter and one-call heatmap compositions."""

from __future__ import annotations

import math
from copy import deepcopy
from xml.sax.saxutils import quoteattr

from .._common import _resolve_palette
from .._typography import chart_font_sizes
from ._academic_rigor import BBox, sig_marker
from ._chart_layout import finite, wrap_lines
from ._composition import (
    adjacent,
    attrs,
    color_key,
    footer,
    group_start,
    heading,
    numeric_axis,
    scale_from,
    serialize_layout,
    size_key,
)
from ._matrix_core import ColorScale, MatrixContext, _cell_shape, aligned_matrix, masked, mean, numeric_matrix
from ._xy import _marker
from .clustered_heatmap import _apply_user_order, _dendrogram_segments


class MatrixPlot:
    """Validated matrix state rendered into any explicit plot box."""

    def __init__(self, data, palette, font_family, color_options=None):
        self.data = deepcopy(data)
        raw = numeric_matrix(data["matrix"])
        self.nr, self.nc = len(raw), len(raw[0])
        shape = (self.nr, self.nc)
        self.matrix = masked(raw, data.get("mask"))
        self.row_labels = list(map(str, data.get("row_labels", range(1, self.nr + 1))))
        self.col_labels = list(map(str, data.get("col_labels", range(1, self.nc + 1))))
        if len(self.row_labels) != self.nr or len(self.col_labels) != self.nc:
            raise ValueError("row_labels and col_labels must match matrix dimensions")
        if len(set(self.row_labels)) != self.nr or len(set(self.col_labels)) != self.nc:
            raise ValueError("composition matrix labels act as ids and must be unique")
        self.upper = (
            masked(numeric_matrix(data["upper_matrix"], shape=shape), data.get("mask"))
            if data.get("upper_matrix") is not None
            else None
        )
        if self.upper is not None and self.nr != self.nc:
            raise ValueError("upper_matrix requires a square matrix")
        self.text = aligned_matrix(data.get("cell_text"), shape, "cell_text")
        self.pvalues = aligned_matrix(data.get("pvalues"), shape, "pvalues")
        if self.pvalues:
            for row in self.pvalues:
                for p in row:
                    if p is not None and not 0 <= finite(p, "pvalue") <= 1:
                        raise ValueError("pvalues must be in [0, 1]")
        self.sizes = (
            masked(numeric_matrix(data["size_matrix"], shape=shape, nonnegative=True), data.get("mask"))
            if data.get("size_matrix") is not None
            else None
        )
        self.size_max = max((v for row in self.sizes for v in row if v is not None), default=0) if self.sizes else 0
        if data.get("size_max") is not None:
            supplied = finite(data["size_max"], "size_max", minimum=0)
            if supplied < self.size_max:
                raise ValueError("size_max must include all observed sizes")
            self.size_max = supplied
        self.variant = data.get("variant", "square_flat_full")
        if self.variant not in ("square_flat_full", "circle_full", "annotated_number"):
            raise ValueError("composition matrix variant must be square_flat_full, circle_full or annotated_number")
        self.palette, self.font = palette, font_family
        self.row_order = list(data.get("row_order", range(self.nr)))
        self.col_order = list(data.get("col_order", range(self.nc)))
        self.trees = {}
        for side, n in (("top", self.nc), ("bottom", self.nc), ("left", self.nr)):
            tree = data.get(side + "_tree")
            if tree:
                order, linkage = _apply_user_order(tree, n)
                if side in ("top", "bottom"):
                    if "col_order" not in data and "top" not in self.trees and "bottom" not in self.trees:
                        self.col_order = order
                    elif order != self.col_order:
                        _apply_user_order({"order": self.col_order, "linkage": linkage}, n)
                else:
                    if "row_order" not in data:
                        self.row_order = order
                    elif order != self.row_order:
                        _apply_user_order({"order": self.row_order, "linkage": linkage}, n)
                self.trees[side] = linkage
        if self.upper is not None:
            if "row_order" not in data and "left" not in self.trees:
                self.row_order = list(self.col_order)
            if self.row_order != self.col_order:
                raise ValueError("split matrices require one shared row/column order")
        for order, n in ((self.row_order, self.nr), (self.col_order, self.nc)):
            _apply_user_order({"order": order}, n)
        base_values = [
            self.matrix[i][j]
            for ri, i in enumerate(self.row_order)
            for cj, j in enumerate(self.col_order)
            if self.upper is None or ri >= cj
        ]
        self.scale = ColorScale.from_values(base_values, palette, **(color_options or data.get("color_scale") or {}))
        upper_options = dict(data.get("upper_scale", {}))
        upper_palette = _resolve_palette(upper_options.pop("palette", palette))
        self.upper_scale = (
            ColorScale.from_values(
                [
                    self.upper[i][j]
                    for ri, i in enumerate(self.row_order)
                    for cj, j in enumerate(self.col_order)
                    if ri < cj
                ],
                upper_palette,
                **upper_options,
            )
            if self.upper is not None
            else None
        )
        self.positions = None
        if data.get("col_positions") is not None:
            if len(data["col_positions"]) != self.nc:
                raise ValueError("col_positions must match matrix columns")
            self.positions = [finite(data["col_positions"][j], "col_positions") for j in self.col_order]
            if any(self.positions[i] >= self.positions[i + 1] for i in range(self.nc - 1)):
                raise ValueError("numeric column positions must be strictly increasing in display order")

    def geometry(self, bbox, row_order=None, col_order=None):
        box = BBox(*bbox)
        rows = self.row_order if row_order is None else list(row_order)
        cols = self.col_order if col_order is None else list(col_order)
        if self.positions is not None:
            vals = [self.data["col_positions"][j] for j in cols]
            if len(vals) == 1:
                edges = [vals[0] - 0.5, vals[0] + 0.5]
            else:
                edges = (
                    [vals[0] - (vals[1] - vals[0]) / 2]
                    + [(a / 2 + b / 2) for a, b in adjacent(vals)]
                    + [vals[-1] + (vals[-1] - vals[-2]) / 2]
                )
            start, span = edges[0], edges[-1] - edges[0]
            xedges = [box.x0 + (v - start) / span * (box.x1 - box.x0) for v in edges]
            centers = [box.x0 + (v - start) / span * (box.x1 - box.x0) for v in vals]
        else:
            xedges = [box.x0 + j / len(cols) * (box.x1 - box.x0) for j in range(len(cols) + 1)]
            centers = [(a + b) / 2 for a, b in adjacent(xedges)]
        yedges = [box.y0 + i / len(rows) * (box.y1 - box.y0) for i in range(len(rows) + 1)]
        ycenters = [(a + b) / 2 for a, b in adjacent(yedges)]
        return rows, cols, xedges, yedges, centers, ycenters

    def render(self, layout, bbox, *, row_order=None, col_order=None, radius_max=None, role="matrix-plot"):
        rows, cols, xedges, yedges, xc, yc = self.geometry(bbox, row_order, col_order)
        display = []
        layout.parts.append(group_start(role))
        for i, original_i in enumerate(rows):
            values = []
            for j, original_j in enumerate(cols):
                # Triangle is selected in display order; values remain indexed
                # by original variable identities in their respective datasets.
                upper = self.upper is not None and self.row_order.index(original_i) < self.col_order.index(original_j)
                value = self.upper[original_i][original_j] if upper else self.matrix[original_i][original_j]
                scale = self.upper_scale if upper else self.scale
                values.append(value)
                x0, x1, y0, y1 = xedges[j], xedges[j + 1], yedges[i], yedges[i + 1]
                layout.parts.append(
                    group_start(
                        "matrix-cell",
                        row_id=self.row_labels[original_i],
                        column=self.col_labels[original_j],
                        value="missing" if value is None else value,
                        triangle="upper" if upper else "lower",
                    )
                )
                if value is None:
                    layout.parts.append(
                        f'<rect x="{x0 + 0.3:.3f}" y="{y0 + 0.3:.3f}" width="{x1 - x0 - 0.6:.3f}" height="{y1 - y0 - 0.6:.3f}" fill={quoteattr(self.palette["ink1"])}/>'
                    )
                elif self.sizes is not None:
                    size = self.sizes[original_i][original_j]
                    max_radius = radius_max if radius_max is not None else min(x1 - x0, y1 - y0) * 0.4
                    radius = max_radius * math.sqrt(size / self.size_max) if size is not None and self.size_max else 0
                    layout.parts.append(
                        _marker(
                            xc[j],
                            yc[i],
                            radius,
                            "circle",
                            scale.color(value),
                            opacity=1,
                            role="matrix-dot",
                            attrs=attrs(size=size),
                        )
                    )
                else:
                    layout.parts.append(_cell_shape(self.variant, x0, y0, x1 - x0, y1 - y0, value, scale))
                text = self.text[original_i][original_j] if self.text else None
                if (
                    text is None
                    and self.data.get("show_values", self.variant == "annotated_number")
                    and value is not None
                ):
                    text = f"{value:.3g}"
                if self.pvalues and self.pvalues[original_i][original_j] is not None:
                    text = (str(text) + " " if text is not None else "") + sig_marker(
                        self.pvalues[original_i][original_j]
                    )
                if text is not None:
                    lines = wrap_lines(text, x1 - x0 - 8, layout.font_sizes["foot"], layout.font)
                    if len(lines) * layout.font_sizes["foot"] * 1.35 > y1 - y0 - 4:
                        raise ValueError("matrix cell text needs a larger height")
                    for k, line in enumerate(lines):
                        layout.text(
                            line,
                            xc[j],
                            yc[i]
                            - len(lines) * layout.font_sizes["foot"] * 0.675
                            + k * layout.font_sizes["foot"] * 1.35,
                            fs=layout.font_sizes["foot"],
                            anchor="middle",
                            color=scale.contrast(value) if value is not None and self.sizes is None else layout.ink,
                        )
                layout.parts.append("</g>")
            display.append(values)
        layout.parts.append(
            f'<rect x="{bbox.x0:.3f}" y="{bbox.y0:.3f}" width="{bbox.x1 - bbox.x0:.3f}" height="{bbox.y1 - bbox.y0:.3f}" fill="none" stroke={quoteattr(layout.pal["ink4"])} stroke-width=".7"/>'
        )
        layout.parts.append("</g>")
        return MatrixContext(
            plot_bbox=tuple(bbox),
            column_centers=tuple(xc),
            row_centers=tuple(yc),
            row_labels=tuple(self.row_labels[i] for i in rows),
            col_labels=tuple(self.col_labels[j] for j in cols),
            scales=tuple(s for s in (self.scale, self.upper_scale) if s is not None),
            palette=dict(self.palette),
            matrix=tuple(tuple(row) for row in display),
            row_order=tuple(rows),
            col_order=tuple(cols),
            font_family=self.font,
        )


def _tree(layout, state, side, box, centers):
    order = state.row_order if side == "left" else state.col_order
    segments, highest = _dendrogram_segments(order, state.trees[side], len(order))

    def leaf(value):
        low = math.floor(value)
        high = min(len(centers) - 1, low + 1)
        return centers[low] + (centers[high] - centers[low]) * (value - low)

    def depth(value):
        if side == "left":
            return box.x1 - value / highest * (box.x1 - box.x0)
        return (
            box.y1 - value / highest * (box.y1 - box.y0)
            if side == "top"
            else box.y0 + value / highest * (box.y1 - box.y0)
        )

    layout.parts.append(group_start("dendrogram", side=side))
    for a, ha, b, hb, _ in segments:
        x0, y0, x1, y1 = (
            (depth(ha), leaf(a), depth(hb), leaf(b)) if side == "left" else (leaf(a), depth(ha), leaf(b), depth(hb))
        )
        layout.parts.append(
            f'<path d="M{x0:.3f},{y0:.3f} L{x1:.3f},{y1:.3f}" fill="none" stroke={quoteattr(layout.pal["ink6"])} stroke-width="1"/>'
        )
    layout.parts.append("</g>")


def _track_specs(data, state):
    tracks = deepcopy(data.get("tracks", []))
    for track in tracks:
        side = track.get("side", "right")
        if side not in ("left", "right", "top", "bottom"):
            raise ValueError("matrix track side must be left, right, top or bottom")
        track["side"] = side
        track["kind"] = track.get("kind", "bar")
        if track["kind"] not in ("bar", "point", "color"):
            raise ValueError("matrix track kind must be bar, point or color")
        labels = state.row_labels if side in ("left", "right") else state.col_labels
        values = track.get("values")
        if not isinstance(values, dict) or any(str(key) not in labels for key in values):
            raise ValueError("matrix track values must map existing row or column ids to observations")
        track["values"] = {str(k): v for k, v in values.items()}
        if track["kind"] != "color":
            if not values:
                raise ValueError("numeric matrix tracks need at least one observation")
            track["scale"] = scale_from(
                list(values.values()),
                domain=track.get("domain"),
                transform=track.get("transform", "linear"),
                zero=track["kind"] == "bar",
            )
        elif any(value not in track.get("colors", {}) for value in values.values()):
            raise ValueError("categorical track colors must map every observed category")
    return tracks


def _matrix_track(layout, track, box, labels, centers, cell_sizes):
    horizontal = track["side"] in ("left", "right")
    values, kind = track["values"], track["kind"]
    layout.parts.append(group_start("matrix-track", name=track.get("name", ""), side=track["side"]))
    for label, center, cell_size in zip(labels, centers, cell_sizes):
        if label not in values:
            continue
        value = values[label]
        color = track.get("colors", {}).get(value) if kind == "color" else track.get("color", layout.pal["accent"])
        if kind == "color":
            x, y, w, h = (
                (box.x0, center - cell_size / 2, box.x1 - box.x0, cell_size)
                if horizontal
                else (center - cell_size / 2, box.y0, cell_size, box.y1 - box.y0)
            )
            layout.parts.append(
                f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill={quoteattr(color)} {attrs(role="annotation-cell", id=label, value=value)}/>'
            )
        else:
            scale = track["scale"]
            end = scale.map(value, box.x0, box.x1) if horizontal else scale.map(value, box.y1, box.y0)
            if kind == "bar":
                zero = scale.map(0, box.x0, box.x1) if horizontal else scale.map(0, box.y1, box.y0)
                x, y, w, h = (
                    (min(zero, end), center - cell_size * 0.26, abs(end - zero), cell_size * 0.52)
                    if horizontal
                    else (center - cell_size * 0.26, min(zero, end), cell_size * 0.52, abs(end - zero))
                )
                layout.parts.append(
                    f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill={quoteattr(color)} {attrs(role="track-bar", id=label, value=value)}/>'
                )
            else:
                x, y = (end, center) if horizontal else (center, end)
                layout.parts.append(
                    _marker(
                        x,
                        y,
                        min(4, cell_size * 0.25),
                        "circle",
                        color,
                        opacity=1,
                        role="track-point",
                        attrs=attrs(id=label, value=value),
                    )
                )
    if kind != "color":
        numeric_axis(
            layout,
            box,
            track["scale"],
            orientation="x" if horizontal else "y",
            side="bottom" if horizontal else "right",
        )
    layout.parts.append("</g>")


def _line_data(state, spec):
    columns = [state.col_labels[j] for j in state.col_order]
    if "values" in spec:
        values = spec["values"]
        if not isinstance(values, dict) or any(k not in state.col_labels for k in values):
            raise ValueError("line values must map existing column ids to values")
        result = [
            finite(values[label], "line value") if label in values and values[label] is not None else None
            for label in columns
        ]
    elif spec.get("statistic", "mean") == "mean":
        source = spec.get("source", "lower")
        if source not in ("lower", "upper", "display") or (source == "upper" and state.upper is None):
            raise ValueError("line source must be lower, upper or display with the requested matrix present")
        matrix = [
            [
                (
                    state.upper
                    if source == "upper" or (source == "display" and state.upper is not None and ri < cj)
                    else state.matrix
                )[i][j]
                for cj, j in enumerate(state.col_order)
            ]
            for ri, i in enumerate(state.row_order)
        ]
        result = [mean([row[j] for row in matrix]) for j in range(state.nc)]
    else:
        raise ValueError("line statistic must be mean, or supply values")
    return result, scale_from([v for v in result if v is not None], domain=spec.get("domain"))


def make_matrix_composition(data, *, layout, color_scale=None, size_label="Size", **common):
    """Heatmap + real aligned line, local inset, trees and four-side tracks."""
    state = MatrixPlot(data, layout.pal, layout.font, color_scale)
    layout.font_sizes = chart_font_sizes(layout.width, layout.height, max(state.nr, state.nc))
    tracks = _track_specs(data, state)
    top = layout.header(common.get("title"), common.get("subtitle"), common.get("figure_label"))
    top = color_key(layout, state.scale, top)
    if state.upper_scale:
        top = color_key(layout, state.upper_scale, top)
    if state.sizes:
        top = size_key(layout, state.size_max, top, label=size_label)
    for track in tracks:
        if track["kind"] == "color":
            for label, color in track["colors"].items():
                top += (
                    layout.text(
                        f"{track.get('name', 'Annotation')} · {label}",
                        45,
                        top,
                        fs=layout.font_sizes["foot"],
                        width=layout.width - 73,
                    )
                    + 4
                )
                layout.parts.append(f'<rect x="28" y="{top - 17:.3f}" width="9" height="9" fill={quoteattr(color)}/>')
    by_side = {side: [t for t in tracks if t["side"] == side] for side in ("left", "right", "top", "bottom")}
    row_labels = [state.row_labels[i] for i in state.row_order]
    col_labels = [state.col_labels[j] for j in state.col_order]
    row_room = min(220, max(layout.measure(v, layout.font_sizes["label"]) for v in row_labels) + 15)
    row_axis_text = (common.get("y_title") or "") + (f" ({common['y_unit']})" if common.get("y_unit") else "")
    if row_axis_text:
        row_room = max(row_room, min(220, layout.measure(row_axis_text, layout.font_sizes["label"]) + 15))
    side_room = {side: sum(34 if t["kind"] == "color" else 116 for t in by_side[side]) for side in ("left", "right")}
    top_room = sum(38 if t["kind"] == "color" else 116 for t in by_side["top"]) + (90 if "top" in state.trees else 0)
    bottom_room = sum(38 if t["kind"] == "color" else 116 for t in by_side["bottom"]) + (
        90 if "bottom" in state.trees else 0
    )
    line_spec = data.get("line")
    inset = data.get("inset")
    inset_room = max(330, layout.width * 0.31) if inset else 0
    line_room = 90 if line_spec else 0
    left_room = 85 if "left" in state.trees else 0
    layout.width = max(
        layout.width,
        56
        + row_room
        + side_room["left"]
        + left_room
        + max(340, state.nc * 24)
        + side_room["right"]
        + line_room
        + inset_room,
    )
    if inset:
        selected_column_count = len(inset.get("columns", []))
        if not selected_column_count:
            raise ValueError("inset needs columns")
        selected_row_labels = [str(v) for v in inset.get("rows", [])]
        if not selected_row_labels:
            raise ValueError("inset needs rows")
        crop_labels = min(170, max(layout.measure(v, layout.font_sizes["foot"]) for v in selected_row_labels) + 15)
        usable = layout.width - 56 - row_room - side_room["left"] - side_room["right"] - left_room - line_room
        ratio = 1.4 * selected_column_count / state.nc
        main_width = max(340, state.nc * 24, (usable - crop_labels - 60) / (1 + ratio))
        inset_room = main_width * ratio + crop_labels + 60
        layout.width = max(
            layout.width,
            56 + row_room + side_room["left"] + side_room["right"] + left_room + line_room + main_width + inset_room,
        )
    x0 = 28 + row_room + side_room["left"] + left_room
    x1 = layout.width - 28 - side_room["right"] - line_room - inset_room
    col_width = (x1 - x0) / state.nc
    col_lines = [wrap_lines(v, col_width - 5, layout.font_sizes["foot"], layout.font) for v in col_labels]
    column_title = (common.get("x_title") or "") + (f" ({common['x_unit']})" if common.get("x_unit") else "")
    row_title = (common.get("y_title") or "") + (f" ({common['y_unit']})" if common.get("y_unit") else "")
    column_title_h = (
        len(wrap_lines(column_title, x1 - x0, layout.font_sizes["label"], layout.font))
        * layout.font_sizes["label"]
        * 1.35
        + 8
        if column_title
        else 0
    )
    row_title_h = (
        len(wrap_lines(row_title, max(80, row_room), layout.font_sizes["label"], layout.font))
        * layout.font_sizes["label"]
        * 1.35
        + 8
        if row_title
        else 0
    )
    col_room = max(len(v) for v in col_lines) * layout.font_sizes["foot"] * 1.35 + 18 + column_title_h
    row_lines = [wrap_lines(v, row_room - 10, layout.font_sizes["label"], layout.font) for v in row_labels]
    cell_h = max(25, max(len(v) for v in row_lines) * layout.font_sizes["label"] * 1.35 + 7)
    if state.text:
        cell_h = max(
            cell_h,
            max(
                len(wrap_lines(v or "", col_width - 8, layout.font_sizes["foot"], layout.font))
                for row in state.text
                for v in row
            )
            * layout.font_sizes["foot"]
            * 1.35
            + 8,
        )
    # Track titles occupy a common row above the matrix, outside their glyphs.
    side_title_h = max(
        [0]
        + [
            len(
                wrap_lines(
                    heading(t.get("name", ""), t["scale"]) if t["kind"] != "color" else t.get("name", ""),
                    88 if t["kind"] != "color" else 20,
                    11,
                    layout.font,
                )
            )
            * layout.font_sizes["foot"]
            * 1.35
            + 9
            for t in by_side["left"] + by_side["right"]
        ]
    )
    line_values, line_scale = _line_data(state, line_spec) if line_spec else (None, None)
    line_title = (
        heading(line_spec.get("label", "Column mean"), line_scale, line_spec.get("unit", "")) if line_spec else ""
    )
    line_title_h = (
        len(wrap_lines(line_title, line_room - 9, layout.font_sizes["foot"], layout.font))
        * layout.font_sizes["foot"]
        * 1.35
        + 8
        if line_spec
        else 0
    )
    guide_room = 26 if inset and (line_spec or by_side["right"]) else 0
    y0 = top + top_room + max(side_title_h, line_title_h, row_title_h) + guide_room
    plot_h = max(300, state.nr * cell_h, layout.height - y0 - col_room - bottom_room - 70)
    y1 = y0 + plot_h
    foot_lines = sum(
        len(wrap_lines(v, layout.width - 56, layout.font_sizes["foot"], layout.font))
        for v in (common.get("note"), common.get("source"))
        if v
    )
    layout.height = max(
        layout.height, y1 + col_room + bottom_room + 72 + foot_lines * layout.font_sizes["label"] * 1.35
    )
    box = BBox(x0, y0, x1, y1)
    context = state.render(layout, box)
    if row_title:
        layout.text(
            row_title, 28, y0 - row_title_h - guide_room + 2, fs=layout.font_sizes["label"], width=max(80, row_room)
        )
    if column_title:
        layout.text(
            column_title,
            (x0 + x1) / 2,
            y1 + col_room - column_title_h,
            fs=layout.font_sizes["label"],
            anchor="middle",
            width=x1 - x0,
        )
    for label, lines, center in zip(row_labels, row_lines, context.row_centers):
        for j, text in enumerate(lines):
            layout.text(
                text,
                28 + row_room - 10,
                center - len(lines) * layout.font_sizes["label"] * 0.675 + j * layout.font_sizes["label"] * 1.35,
                fs=layout.font_sizes["label"],
                anchor="end",
            )
    for lines, center in zip(col_lines, context.column_centers):
        for j, text in enumerate(lines):
            layout.text(
                text,
                center,
                y1 + 10 + j * layout.font_sizes["foot"] * 1.35,
                fs=layout.font_sizes["foot"],
                anchor="middle",
            )
    geo = state.geometry(box)
    widths = [geo[2][i + 1] - geo[2][i] for i in range(state.nc)]
    heights = [plot_h / state.nr] * state.nr
    for side in ("left", "right"):
        cursor = x0 - left_room - side_room["left"] if side == "left" else x1 + line_room + 16
        for track in by_side[side]:
            tw = 20 if track["kind"] == "color" else 88
            tbox = BBox(cursor, y0, cursor + tw, y1)
            title = (
                heading(track.get("name", ""), track["scale"]) if track["kind"] != "color" else track.get("name", "")
            )
            layout.text(title, cursor, y0 - side_title_h - guide_room + 2, fs=layout.font_sizes["foot"], width=tw)
            _matrix_track(layout, track, tbox, row_labels, context.row_centers, heights)
            cursor += 34 if track["kind"] == "color" else 116
    for side in ("top", "bottom"):
        cursor = top if side == "top" else y1 + col_room
        if side in state.trees:
            tbox = BBox(x0, cursor, x1, cursor + 80)
            _tree(layout, state, side, tbox, context.column_centers)
            cursor += 90
        for track in by_side[side]:
            th = 18 if track["kind"] == "color" else 70
            label = (
                heading(track.get("name", ""), track["scale"]) if track["kind"] != "color" else track.get("name", "")
            )
            layout.text(label, 28, cursor + 5, fs=layout.font_sizes["foot"], width=max(80, x0 - 40))
            tbox = BBox(x0, cursor, x1, cursor + th)
            _matrix_track(layout, track, tbox, col_labels, context.column_centers, widths)
            cursor += 38 if track["kind"] == "color" else 116
    if "left" in state.trees:
        _tree(layout, state, "left", BBox(x0 - 80, y0, x0 - 7, y1), context.row_centers)
    if line_spec:
        scale = line_scale
        line_color = line_spec.get("color", layout.ink)
        coords = [
            (x, scale.map(v, y1, y0)) if v is not None else None for x, v in zip(context.column_centers, line_values)
        ]
        layout.parts.append(group_start("matrix-line"))
        for i in range(1, len(coords)):
            if coords[i - 1] is not None and coords[i] is not None:
                a, b = coords[i - 1], coords[i]
                path = f"M{a[0]:.3f},{a[1]:.3f} L{b[0]:.3f},{b[1]:.3f}"
                layout.parts.append(
                    f'<path d="{path}" fill="none" stroke={quoteattr(layout.pal.get("bg") or "#FFFFFF")} stroke-width="5"/><path d="{path}" fill="none" stroke={quoteattr(line_color)} stroke-width="2"/>'
                )
        for label, value, point in zip(col_labels, line_values, coords):
            if point:
                layout.parts.append(
                    _marker(
                        *point,
                        3.5,
                        "circle",
                        line_color,
                        opacity=1,
                        role="matrix-line-point",
                        attrs=attrs(column=label, value=value),
                    )
                )
        layout.parts.append("</g>")
        numeric_axis(layout, box, scale, orientation="y", side="right")
        layout.text(
            line_title, x1 + 9, y0 - line_title_h - guide_room + 2, fs=layout.font_sizes["foot"], width=line_room - 9
        )
    inset_box = None
    if inset:
        selected_rows = [state.row_labels.index(str(v)) for v in inset["rows"]]
        selected_cols = [state.col_labels.index(str(v)) for v in inset["columns"]]
        for selected, order in ((selected_rows, state.row_order), (selected_cols, state.col_order)):
            indices = sorted(order.index(v) for v in selected)
            if (
                not selected
                or len(set(selected)) != len(selected)
                or indices != list(range(min(indices), max(indices) + 1))
            ):
                raise ValueError("inset rows and columns must select one nonempty contiguous display region")
        selected_rows.sort(key=state.row_order.index)
        selected_cols.sort(key=state.col_order.index)
        ix0 = layout.width - inset_room + 30
        iw = inset_room - 66
        inset_row_room = min(
            iw * 0.35, max(layout.measure(state.row_labels[i], layout.font_sizes["foot"]) for i in selected_rows) + 12
        )
        inset_box = BBox(
            ix0 + inset_row_room, y0 + 44, ix0 + iw, y0 + 44 + max(180, len(selected_rows) * plot_h / state.nr * 1.4)
        )
        layout.text(inset.get("title", "Selected region"), ix0, y0, fs=layout.font_sizes["group"], bold=True, width=iw)
        layout.height = max(layout.height, inset_box.y1 + 110 + foot_lines * layout.font_sizes["label"] * 1.35)
        ctx = state.render(layout, inset_box, row_order=selected_rows, col_order=selected_cols, role="matrix-inset")
        for label, center in zip(ctx.row_labels, ctx.row_centers):
            lines = wrap_lines(label, inset_row_room - 10, layout.font_sizes["foot"], layout.font)
            for i, line in enumerate(lines):
                layout.text(
                    line,
                    inset_box.x0 - 10,
                    center - len(lines) * layout.font_sizes["foot"] * 0.675 + i * layout.font_sizes["foot"] * 1.35,
                    fs=layout.font_sizes["foot"],
                    anchor="end",
                )
        for label, center in zip(ctx.col_labels, ctx.column_centers):
            layout.text(
                label,
                center,
                inset_box.y1 + 10,
                fs=layout.font_sizes["foot"],
                anchor="middle",
                width=(inset_box.x1 - inset_box.x0) / len(selected_cols) - 5,
            )
        ri = [state.row_order.index(i) for i in selected_rows]
        ci = [state.col_order.index(j) for j in selected_cols]
        select = BBox(geo[2][min(ci)], geo[3][min(ri)], geo[2][max(ci) + 1], geo[3][max(ri) + 1])
        layout.parts.append(
            f'<rect x="{select.x0:.3f}" y="{select.y0:.3f}" width="{select.x1 - select.x0:.3f}" height="{select.y1 - select.y0:.3f}" fill="none" stroke={quoteattr(layout.pal["ink"])} stroke-width="2" stroke-dasharray="5 3" data-role="inset-selection"/>'
        )
        # Guide lines stop before inset labels; labels remain completely readable.
        gutter = x1 + line_room + side_room["right"] + 10
        for start_y, end_y in ((select.y0, inset_box.y0), (select.y1, inset_box.y1)):
            route = (
                f"M{select.x1:.3f},{start_y:.3f} H{x1:.3f} V{y0 - 12:.3f} H{gutter:.3f} V{end_y:.3f} H{ix0 - 8:.3f}"
                if guide_room
                else f"M{select.x1:.3f},{start_y:.3f} H{gutter:.3f} V{end_y:.3f} H{ix0 - 8:.3f}"
            )
            layout.parts.append(
                f'<path d="{route}" fill="none" stroke={quoteattr(layout.pal["ink6"])} stroke-width=".8" stroke-dasharray="3 4" data-role="inset-guide"/>'
            )
    footer(layout, common.get("note"), common.get("source"))
    serialize_layout(
        layout,
        "matrix-composition-layout",
        [
            {
                "bbox": list(box),
                "row_centers": context.row_centers,
                "column_centers": context.column_centers,
                "row_order": state.row_order,
                "col_order": state.col_order,
                "color_domain": [state.scale.low, state.scale.high],
                "line_values": line_values,
                "inset_bbox": list(inset_box) if inset_box else None,
            }
        ],
    )
    return layout.svg("Heatmap with shared-coordinate scientific overlays and aligned tracks")
