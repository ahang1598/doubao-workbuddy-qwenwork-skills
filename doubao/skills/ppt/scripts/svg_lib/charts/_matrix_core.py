"""Shared matrix validation, scales and measured layout (stdlib only)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from html import escape as _attr

from .._common import _estimate_label_width_px, _fmt_axis, _resolve_font, _resolve_palette, _rgb_tuple, _xesc
from .._typography import chart_font_sizes
from . import _academic_rigor as rigor
from ._matrix_math import stable_fraction, stable_lerp
from ._shared import tr

VARIANTS = {"square_flat_full", "circle_full", "ellipse_upper", "pie_full", "annotated_number"}


def numeric_matrix(matrix, name="matrix", shape=None, nonnegative=False):
    if matrix is None or len(matrix) == 0 or len(matrix[0]) == 0:
        raise ValueError(f"{name} must be a non-empty rectangular matrix")
    nr, nc = len(matrix), len(matrix[0])
    if shape is not None and (nr, nc) != shape:
        raise ValueError(f"{name} must have shape {shape}, got {(nr, nc)}")
    result = []
    for i, row in enumerate(matrix):
        if len(row) != nc:
            raise ValueError(f"{name} row {i} has {len(row)} columns; expected {nc}")
        out = []
        for j, value in enumerate(row):
            if value is None:
                out.append(None)
                continue
            if isinstance(value, bool):
                raise TypeError(f"{name}[{i}][{j}] must be numeric, None or NaN")
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError(f"{name}[{i}][{j}] must be numeric, None or NaN") from None
            if math.isnan(value):
                value = None
            elif not math.isfinite(value) or (nonnegative and value < 0):
                raise ValueError(f"{name}[{i}][{j}] must be finite" + (" and nonnegative" if nonnegative else ""))
            out.append(value)
        result.append(out)
    return result


def aligned_matrix(value, shape, name):
    if value is None:
        return None
    if len(value) != shape[0] or any(len(row) != shape[1] for row in value):
        raise ValueError(f"{name} must have shape {shape}")
    return [list(row) for row in value]


def masked(matrix, mask):
    if mask is None:
        return matrix
    mask = aligned_matrix(mask, (len(matrix), len(matrix[0])), "mask")
    if any(not isinstance(v, bool) for row in mask for v in row):
        raise ValueError("mask must contain booleans (True hides a cell)")
    return [[None if mask[i][j] else v for j, v in enumerate(row)] for i, row in enumerate(matrix)]


def mean(values):
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    try:
        return math.fsum(valid) / len(valid)
    except OverflowError:
        scale = max(abs(v) for v in valid)
        return (math.fsum(v / scale for v in valid) / len(valid)) * scale


def format_value(value, value_fmt=None, span=None):
    """Use shared numeric precision by default; preserve explicit formatting."""
    if value is None:
        return "\u2014"
    if value_fmt is not None:
        return format(value, value_fmt)
    if value == 0:
        return "0"
    if span is None or not math.isfinite(span):
        span = abs(value)
    label = _fmt_axis(value, span)
    if float(label.replace(",", "")) == 0:
        return format(value, ".3g")
    return label


def number_labels(values, value_fmt=None):
    """Choose enough shared precision to distinguish every displayed value."""
    ordered = sorted({v for v in values if v is not None})
    steps = [ordered[i + 1] - ordered[i] for i in range(len(ordered) - 1)]
    span = min(steps) if steps else abs(ordered[0]) if ordered else 1
    labels = [format_value(value, value_fmt, span) for value in values]
    if value_fmt is None and len(set(labels)) < len(set(values)):
        for significant in range(3, 18):
            labels = [
                "\u2014" if value is None else format(value, f".{significant}g") if value else "0" for value in values
            ]
            if len(set(labels)) == len(set(values)):
                break
    return labels


def text_width(text, fs, font):
    return _estimate_label_width_px(str(text), fs, font_family=font)


def wrap(text, max_width, fs, font):
    lines = []
    for paragraph in str(text).split("\n"):
        line = ""
        for char in paragraph:
            if line and text_width(line + char, fs, font) > max_width:
                # Prefer a word boundary while still supporting CJK and long IDs.
                split = line.rfind(" ")
                if split > 0:
                    lines.append(line[:split])
                    line = line[split + 1 :] + char
                else:
                    lines.append(line.rstrip())
                    line = char.lstrip()
            else:
                line += char
        lines.append(line.rstrip())
    return lines or [""]


def text_svg(x, y, lines, fs, color, font, anchor="start", weight=400, italic=False, rotate=None):
    if isinstance(lines, str):
        lines = [lines]
    transform = f' transform="rotate({rotate} {x:.2f} {y:.2f})"' if rotate else ""
    if len(lines) > 1:
        # Emit real lines as independent primitives. Preserve the rounded SVG
        # baseline/step and the common rotation pivot used by the former tspans.
        baseline = float(f"{y:.2f}")
        step = float(f"{fs * 1.3:.2f}")
        style = (
            f'font-family="{_attr(font, quote=True)}" font-size="{fs:.2f}" '
            f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}"'
            + (' font-style="italic"' if italic else "")
            + transform
        )
        return "".join(
            f'<text x="{x:.2f}" y="{baseline + i * step:.2f}" {style}>{_xesc(str(line))}</text>'
            for i, line in enumerate(lines)
        )
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="{_attr(font, quote=True)}" font-size="{fs:.2f}" '
        f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}"'
        + (' font-style="italic"' if italic else "")
        + transform
        + ">"
        + "".join(
            f'<tspan x="{x:.2f}" dy="{0 if i == 0 else fs * 1.3:.2f}">{_xesc(str(s))}</tspan>'
            for i, s in enumerate(lines)
        )
        + "</text>"
    )


def numeric_tick_layout(values, positions, x, width, fs, font, roles=None, value_fmt=None):
    """Retain all semantic ticks and place colliding labels on separate rows."""
    labels = number_labels(values, value_fmt)
    roles = roles or [tr("Value")] * len(values)
    lanes = []
    result = []
    for value, position, label, role in zip(values, positions, labels, roles):
        lane = 0
        while True:
            content = label if lane == 0 else f"{role}: {label}"
            label_fs = min(fs, width / max(1, text_width(content, 1, font)))
            label_width = text_width(content, label_fs, font)
            left = min(max(position - label_width / 2, x), x + width - label_width)
            right = left + label_width
            if lane == len(lanes):
                lanes.append([])
            if all(right + 8 <= lo or left >= hi + 8 for lo, hi in lanes[lane]):
                lanes[lane].append((left, right))
                result.append(
                    {
                        "value": value,
                        "text": content,
                        "x": left,
                        "lane": lane,
                        "dy": lane * fs * 1.5,
                        "fs": label_fs,
                        "width": label_width,
                    }
                )
                break
            lane += 1
    return result, len(lanes) * fs * 1.5


def numeric_tick_svg(layout, y, color, font):
    fragments = []
    for tick in layout:
        fragments.append(f'<g data-scale-tick="{tick["value"]}" data-tick-lane="{tick["lane"]}">')
        fragments.append(text_svg(tick["x"], y + tick["dy"], tick["text"], tick["fs"], color, font))
        fragments.append("</g>")
    return "".join(fragments)


@dataclass
class ColorScale:
    low: float
    high: float
    midpoint: float | None
    palette: dict
    log: bool = False
    label: str = "Value"

    @classmethod
    def from_values(
        cls, values, palette, *, vmin=None, vmax=None, midpoint=None, colormap="auto", log=False, label="Value"
    ):
        vals = [v for v in values if v is not None]
        if not vals and (vmin is None or vmax is None):
            raise ValueError("No observed cell values; supply an explicit vmin/vmax to render an empty matrix")
        lo = min(vals) if vmin is None else float(vmin)
        hi = max(vals) if vmax is None else float(vmax)
        if not math.isfinite(lo) or not math.isfinite(hi) or hi < lo:
            raise ValueError("Color scale requires finite vmin <= vmax")
        if colormap not in {"auto", "sequential", "diverging"}:
            raise ValueError("colormap must be auto, sequential or diverging")
        if colormap == "sequential" and midpoint is not None:
            raise ValueError("midpoint requires a diverging color scale")
        if hi == lo and vals and any(v != lo for v in vals):
            raise ValueError("Equal color limits require constant observed values")
        if log and (lo <= 0 or any(v <= 0 for v in vals)):
            raise ValueError("log_color requires strictly positive observed values and limits")
        if log and (colormap == "diverging" or midpoint is not None):
            raise ValueError("log_color cannot be combined with a diverging midpoint")
        diverging = colormap == "diverging" or (colormap == "auto" and (midpoint is not None or lo < 0 < hi))
        if diverging:
            mid = float(midpoint) if midpoint is not None else (0.0 if lo < 0 < hi else stable_lerp(lo, hi, 0.5))
            if not math.isfinite(mid) or not lo <= mid <= hi:
                raise ValueError("midpoint must lie inside the color scale limits")
        else:
            mid = None
        return cls(lo, hi, mid, palette, log, tr(str(label)))

    def fraction(self, value):
        if self.high == self.low:
            return 0.5
        if self.log:
            return rigor._log_lin(value, self.low, self.high, 0.0, 1.0)
        return stable_fraction(value, self.low, self.high)

    def value_at(self, fraction):
        if fraction <= 0:
            return self.low
        if fraction >= 1:
            return self.high
        if self.log:
            return 10.0 ** (math.log10(self.low) * (1 - fraction) + math.log10(self.high) * fraction)
        return stable_lerp(self.low, self.high, fraction)

    def color(self, value):
        paper = self.palette.get("bg") or "rgb(255,255,255)"
        accent = self.palette["accent"]
        if self.midpoint is None:
            return rigor.value_to_color(0.08 + 0.92 * self.fraction(value), 0, 1, stops=[paper, accent])
        cold = self.palette["secondary"]
        if value <= self.midpoint:
            f = stable_fraction(value, self.low, self.midpoint) if self.midpoint > self.low else 1.0
            return rigor.value_to_color(f, 0, 1, stops=[cold, paper])
        f = stable_fraction(value, self.midpoint, self.high) if self.high > self.midpoint else 1.0
        return rigor.value_to_color(f, 0, 1, stops=[paper, accent])

    def contrast(self, value):
        r, g, b = _rgb_tuple(self.color(value))
        return "rgb(24,26,34)" if 0.299 * r + 0.587 * g + 0.114 * b > 145 else "rgb(250,250,248)"


@dataclass
class CategoryScale:
    colors: dict
    palette: dict
    label: str

    def color(self, value):
        return self.colors[value]


def prepare_tracks(annotation, n, name, pal):
    if annotation is None:
        return []
    tracks = annotation if isinstance(annotation, dict) else {name: annotation}
    out = []
    colors = [pal["secondary"], pal["accent"], "#719B87", "#A58BB2", "#B7A469", "#7CA7B2", "#AA7C80", "#8E9299"]
    for title, values in tracks.items():
        if len(values) != n:
            raise ValueError(f"annotation track {title!r} must have {n} values")
        present = [v for v in values if v is not None]
        numeric = bool(present) and all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in present)
        if numeric:
            vals = numeric_matrix([values], f"annotation {title}")[0]
            if any(v is not None for v in vals):
                scale = ColorScale.from_values(vals, pal, label=str(title))
                out.append((str(title), [None if v is None else scale.color(v) for v in vals], scale))
            else:
                out.append((str(title), [None] * n, [(tr("Missing"), pal["ink1"])]))
        else:
            keys, fills, legend = {}, [], []
            names = sorted(
                {str(v[0] if isinstance(v, (tuple, list)) and len(v) == 2 else v) for v in values if v is not None}
            )
            defaults = {label: colors[i % len(colors)] for i, label in enumerate(names)}
            for value in values:
                if value is None:
                    fills.append(None)
                    continue
                label, explicit = value if isinstance(value, (tuple, list)) and len(value) == 2 else (str(value), None)
                label = str(label)
                if label not in keys:
                    keys[label] = explicit or defaults[label]
                    legend.append((label, keys[label]))
                elif explicit and keys[label] != explicit:
                    raise ValueError(f"annotation {title!r} assigns multiple colors to {label!r}")
                fills.append(keys[label])
            out.append((str(title), fills, legend))
    return out


def reorder_annotation(annotation, order):
    if annotation is None:
        return None
    if isinstance(annotation, dict):
        return {name: [values[i] for i in order] for name, values in annotation.items()}
    return [annotation[i] for i in order]


def _cell_shape(variant, x, y, w, h, value, scale):
    fill = scale.color(value)
    cx, cy = x + w / 2, y + h / 2
    r = min(w, h) * 0.43
    if variant in {"square_flat_full", "annotated_number"}:
        return (
            f'<rect x="{x + 0.35:.2f}" y="{y + 0.35:.2f}" width="{w - 0.7:.2f}" height="{h - 0.7:.2f}" fill="{fill}"/>'
        )
    if scale.midpoint is not None:
        midpoint_fraction = scale.fraction(scale.midpoint)
        span = max(midpoint_fraction, 1 - midpoint_fraction)
        magnitude = abs(scale.fraction(value) - midpoint_fraction) / span if scale.high != scale.low else 0.0
    else:
        span = max(abs(scale.low), abs(scale.high))
        magnitude = abs(value) / span if span else 0.0
    magnitude = min(1.0, max(0.0, magnitude))
    if variant == "circle_full":
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r * math.sqrt(magnitude):.6g}" fill="{fill}" stroke="{scale.palette["ink4"]}" stroke-width=".6"/>'
    if variant == "ellipse_upper":
        rx = r * math.sqrt((1 + magnitude) / 2)
        ry = max(0.4, r * math.sqrt((1 - magnitude) / 2))
        angle = -45 if value >= (scale.midpoint or 0) else 45
        return f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" transform="rotate({angle} {cx:.2f} {cy:.2f})" fill="{fill}" stroke="{scale.palette["ink4"]}" stroke-width=".6"/>'
    if magnitude >= 0.999999:
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}"/>'
    outline = f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="none" stroke="{scale.palette["ink4"]}" stroke-width=".6"/>'
    if magnitude <= 0:
        return outline
    direction = 1 if value >= (scale.midpoint if scale.midpoint is not None else 0) else -1
    angle = -math.pi / 2 + direction * magnitude * math.tau
    ex, ey = cx + r * math.cos(angle), cy + r * math.sin(angle)
    return outline + (
        f'<path d="M {cx:.2f} {cy:.2f} L {cx:.2f} {cy - r:.2f} A {r:.2f} {r:.2f} 0 '
        f'{int(magnitude > 0.5)} {int(direction > 0)} {ex:.2f} {ey:.2f} Z" fill="{fill}"/>'
    )


@dataclass(frozen=True)
class MatrixContext:
    """Measured plot geometry for internal shared-axis composition callbacks."""

    plot_bbox: tuple
    column_centers: tuple
    row_centers: tuple
    row_labels: tuple
    col_labels: tuple
    scales: tuple
    palette: dict
    matrix: tuple
    row_order: tuple
    col_order: tuple
    font_family: str

    @property
    def color_domains(self):
        return tuple((scale.low, scale.high) for scale in self.scales)


def table_values(matrix, columns):
    """Keep text/category observations as literal values, never fake numbers."""
    if matrix is None or not len(matrix) or not columns:
        raise ValueError("columns requires a non-empty table and schema")
    n = len(columns)
    allowed = {"name", "type", "vmin", "vmax", "midpoint", "colormap", "log", "palette", "colors", "label"}
    for column in columns:
        if not isinstance(column, dict) or set(column) - allowed:
            raise ValueError("Each column schema must contain name/type and supported scale options")
        if column.get("type", "number") not in {"number", "text", "category"}:
            raise ValueError("Column type must be number, text or category")
    raw = aligned_matrix(matrix, (len(matrix), n), "table")
    raw = [[None if isinstance(v, float) and math.isnan(v) else v for v in row] for row in raw]
    numeric = []
    for row in raw:
        numeric.append([v if columns[j].get("type", "number") == "number" else None for j, v in enumerate(row)])
    return raw, numeric


def table_scales(raw, numeric, columns, pal, defaults):
    scales, categories = [], []
    for j, column in enumerate(columns):
        kind = column.get("type", "number")
        local_pal = _resolve_palette(column["palette"]) if "palette" in column else pal
        if kind == "number":
            opts = {k: v for k, v in defaults.items() if k != "label"}
            opts.update({k: column[k] for k in ("vmin", "vmax", "midpoint", "colormap", "log", "label") if k in column})
            opts.setdefault("label", column.get("name", str(j + 1)))
            scales.append(ColorScale.from_values([row[j] for row in numeric], local_pal, **opts))
            categories.append([])
        elif kind == "category":
            color_map = column.get("colors", {})
            vals = [None if row[j] is None else (str(row[j]), color_map.get(str(row[j]))) for row in raw]
            _, _, key = prepare_tracks({column.get("name", str(j + 1)): vals}, len(raw), tr("Column"), local_pal)[0]
            scales.append(None)
            categories.append(key)
        else:
            scales.append(None)
            categories.append([])
    return scales, categories


_COMPACT_RETRY = (
    "Canvas too small",
    "Canvas height is too small",
    "Cell text needs more space",
    "Column mean text needs",
)


def render_matrix(*args, **kwargs):
    """Render at the shared density policy; on a caller-fixed small canvas retry compactly."""
    try:
        return _render_matrix(*args, **kwargs)
    except ValueError as error:
        if not str(error).startswith(_COMPACT_RETRY):
            raise
        first = error
    for options in [{"rmax": cap} for cap in (None, 30.0, 22.0, 16.0, 12.0, 9.0)] + [{"rmax": None, "below": True}]:
        try:
            return _render_matrix(*args, _compact=options, **kwargs)
        except ValueError as error:
            if not str(error).startswith(_COMPACT_RETRY):
                raise
    raise first


def _render_matrix(
    matrix,
    row_labels,
    col_labels,
    *,
    variant="annotated_number",
    scale_options=None,
    cell_text=None,
    cell_label_position="center",
    pvalues=None,
    mask=None,
    upper_matrix=None,
    upper_scale=None,
    row_annotation=None,
    col_annotation=None,
    row_sub_labels=None,
    domain_groups=None,
    show_values=False,
    show_row_mean=False,
    show_col_mean=False,
    show_colorbar=True,
    colorbar_sub=None,
    value_fmt=None,
    highlight_pair=None,
    compare_cols=None,
    size_matrix=None,
    size_max=None,
    size_label="Size",
    size_legend_values=None,
    size_suffix="",
    italic_rows=False,
    row_mean_label="Row mean",
    summary=None,
    columns=None,
    dendrograms=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    width=1300,
    height=820,
    font_family=None,
    palette=None,
    metadata=None,
    _overlays=None,
    _compact=None,
):
    compact = _compact is not None
    size_label, row_mean_label = tr(size_label), tr(row_mean_label)
    table_raw = None
    categorical_colors = (scale_options or {}).get("colormap")
    categorical_colors = categorical_colors if isinstance(categorical_colors, dict) else None
    if columns is not None:
        table_raw, matrix = table_values(matrix, columns)
    if categorical_colors is not None:
        if size_matrix is None or upper_matrix is not None or columns is not None:
            raise ValueError("A categorical colormap is supported for a size/color dot matrix")
        if any((scale_options or {}).get(k) is not None for k in ("vmin", "vmax", "midpoint")) or (
            scale_options or {}
        ).get("log"):
            raise ValueError("Categorical colors cannot use numeric limits, a midpoint or logarithmic scaling")
        if not matrix or not matrix[0]:
            raise ValueError("color_matrix must be non-empty")
        matrix = aligned_matrix(matrix, (len(matrix), len(matrix[0])), "color_matrix")
        matrix = [
            [None if v is None or (isinstance(v, float) and math.isnan(v)) else str(v) for v in row] for row in matrix
        ]
        matrix = masked(matrix, mask)
        if any(v not in categorical_colors for row in matrix for v in row if v is not None):
            raise ValueError("Categorical colormap must map every observed color_matrix category")
        if show_row_mean or show_col_mean:
            raise ValueError("Category colors do not have numeric means")
        matrix = masked(matrix, mask)
    else:
        matrix = masked(numeric_matrix(matrix), mask)
    nr, nc = len(matrix), len(matrix[0])
    shape = (nr, nc)
    if variant not in VARIANTS:
        raise ValueError(f"Unknown matrix variant {variant!r}; available: {sorted(VARIANTS)}")
    if cell_label_position not in {"center", "below"}:
        raise ValueError("cell_label_position must be center or below")
    if cell_label_position == "below" and variant not in {"circle_full", "pie_full"}:
        raise ValueError("below-cell labels require circle_full or pie_full")
    if variant == "ellipse_upper" and upper_matrix is None:
        # Visibility is part of the observation contract, not a paint-only
        # filter: every scale, summary, comparison and overlay uses this mask.
        mask = [[i > j or (mask is not None and mask[i][j]) for j in range(nc)] for i in range(nr)]
        matrix = masked(matrix, mask)
    if len(row_labels) != nr or len(col_labels) != nc:
        raise ValueError("row_labels / col_labels must match the matrix shape")
    row_labels, col_labels = list(map(str, row_labels)), list(map(str, col_labels))
    cell_text = aligned_matrix(cell_text, shape, "cell_text")
    if cell_text is not None:
        cell_text = masked(cell_text, mask)
    if table_raw is not None:
        table_raw = masked(table_raw, mask)
    if pvalues is not None:
        pvalues = numeric_matrix(pvalues, "pvalues", shape, nonnegative=True)
        if any(p > 1 for row in pvalues for p in row if p is not None):
            raise ValueError("pvalues must lie between 0 and 1")
    if row_sub_labels is not None and len(row_sub_labels) != nr:
        raise ValueError("row_sub_labels must match rows")
    if upper_matrix is not None:
        if nr != nc:
            raise ValueError("upper_matrix requires a square matrix with a shared row / column order")
        upper_matrix = masked(numeric_matrix(upper_matrix, "upper_matrix", shape), mask)
    elif upper_scale is not None:
        raise ValueError("upper_scale requires upper_matrix")
    if size_matrix is not None:
        if variant not in {"circle_full", "square_flat_full", "annotated_number"}:
            raise ValueError("Independent size_matrix supports circle_full, square_flat_full or annotated_number")
        size_matrix = masked(numeric_matrix(size_matrix, "size_matrix", shape, nonnegative=True), mask)
        # A missing size or color means no observed dot. Exclude it from scales.
        matrix = [
            [v if size_matrix[i][j] is not None else None for j, v in enumerate(row)] for i, row in enumerate(matrix)
        ]
        if upper_matrix is not None:
            upper_matrix = [
                [v if size_matrix[i][j] is not None else None for j, v in enumerate(row)]
                for i, row in enumerate(upper_matrix)
            ]
    visible_matrix = [
        [upper_matrix[i][j] if upper_matrix is not None and i < j else v for j, v in enumerate(row)]
        for i, row in enumerate(matrix)
    ]
    if highlight_pair is not None and (
        len(highlight_pair) != 2
        or any(not isinstance(v, int) or isinstance(v, bool) for v in highlight_pair)
        or not (0 <= highlight_pair[0] < nr and 0 <= highlight_pair[1] < nc)
    ):
        raise ValueError("highlight_pair must contain valid row and column indices")
    if compare_cols is not None:
        if columns is not None or categorical_colors is not None:
            raise ValueError(
                "compare_cols requires numeric observations in one common unit, not a heterogeneous columns schema"
            )
        if (
            len(compare_cols) != 2
            or any(not isinstance(c, int) or isinstance(c, bool) or c < 0 or c >= nc for c in compare_cols)
            or compare_cols[0] == compare_cols[1]
        ):
            raise ValueError("compare_cols requires two distinct valid column indices")
    pal = _resolve_palette("archive_ink" if palette is None else palette)
    body_font, head_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    if not all(math.isfinite(v) and v > 0 for v in (W, H)):
        raise ValueError("width and height must be positive finite values")
    fonts = chart_font_sizes(W, H, max(nr, nc))
    fs, legend_fs, title_fs = fonts["label"], fonts["legend"], fonts["title"]
    base_values = [
        v for i, row in enumerate(visible_matrix) for j, v in enumerate(row) if upper_matrix is None or i >= j
    ]
    if columns is not None:
        if upper_matrix is not None or size_matrix is not None:
            raise ValueError("columns schema cannot be combined with upper_matrix or size_matrix")
        if show_row_mean or show_col_mean:
            raise ValueError("Mixed table columns have independent units; disable row and column means")
        column_scales, column_categories = table_scales(table_raw, matrix, columns, pal, scale_options or {})
        scale = next((s for s in column_scales if s is not None), ColorScale(0, 1, None, pal))
        scales = [s for s in column_scales if s is not None]
    else:
        column_scales, column_categories = None, []
        if categorical_colors is not None:
            scale = CategoryScale(categorical_colors, pal, (scale_options or {}).get("label", tr("Category")))
            scales = []
        else:
            scale = ColorScale.from_values(base_values, pal, **(scale_options or {}))
            scales = [scale]
    upper_size_options = {}
    if upper_matrix is not None:
        opts = dict(upper_scale or {})
        upper_size_options = {
            key: opts.pop(key) for key in ("size_max", "size_label", "size_legend_values") if key in opts
        }
        upper_palette = _resolve_palette(opts.pop("palette")) if "palette" in opts else pal
        if "colorbar_label" in opts:
            opts["label"] = opts.pop("colorbar_label")
        opts.setdefault("label", tr("Upper triangle"))
        scales.append(
            ColorScale.from_values(
                [v for i, row in enumerate(upper_matrix) for j, v in enumerate(row) if i < j], upper_palette, **opts
            )
        )
    r_tracks = prepare_tracks(row_annotation, nr, tr("Row annotation"), pal)
    c_tracks = prepare_tracks(col_annotation, nc, tr("Column annotation"), pal)
    table_keys = [(columns[j].get("name", col_labels[j]), None, key) for j, key in enumerate(column_categories) if key]
    if categorical_colors is not None:
        observed_categories = {v for row in matrix for v in row if v is not None}
        table_keys.append(
            (
                scale.label,
                None,
                [(key, color) for key, color in categorical_colors.items() if key in observed_categories],
            )
        )
    parts = []
    if pal.get("bg"):
        parts.append(f'<rect x="0" y="0" width="{W:.2f}" height="{H:.2f}" fill="{pal["bg"]}"/>')
    top = 16.0 if compact else 24.0
    for content, size, color, weight, font in [
        (title, title_fs, pal["ink"], 600, head_font),
        (subtitle, legend_fs, pal["ink6"], 400, body_font),
        (figure_label, legend_fs, pal["ink6"], 500, body_font),
    ]:
        if content:
            lines = wrap(content, W - 56, size, font)
            parts.append(text_svg(28, top + size, lines, size, color, font, weight=weight))
            top += len(lines) * size * 1.3 + 7
    top += 6 if compact else 14
    footer = []
    for label, content in [("", note), (tr("Source: "), source)]:
        if content:
            footer += wrap(label + str(content), W - 56, legend_fs, body_font)
    footer_h = len(footer) * legend_fs * 1.3 + (20 if footer else 0)
    # Start with the shared density policy, then fit the actual full label
    # blocks. Dense matrices need room for every row, including wrapped labels.
    min_fs = 10.0 if compact else 8.0
    side = 16.0 if compact else 28.0
    cell_unit_w = 0.0
    if compact and columns is None and categorical_colors is None and (show_values or variant == "annotated_number"):
        cell_unit_w = max(
            (
                text_width(format_value(v, value_fmt, scale.high - scale.low), 1, body_font)
                for row in visible_matrix
                for v in row
                if v is not None
            ),
            default=0.0,
        )
    col_mean_unit_w = 0.0
    if compact and show_col_mean:
        col_means = number_labels([mean([row[j] for row in visible_matrix]) for j in range(nc)], value_fmt)
        col_mean_unit_w = max(text_width(label, 1, body_font) for label in col_means)
    for _font_attempt in range(40):
        row_room = min(
            W * 0.25, max(55.0, (1.1 if W >= 700 else 1.0) * max(text_width(s, fs, body_font) for s in row_labels))
        )
        if show_col_mean:
            row_room = max(row_room, text_width(tr("Col mean"), legend_fs, body_font) + 10)
        row_lines = [wrap(s, row_room, fs, body_font) for s in row_labels]
        if row_sub_labels is not None:
            for i, sub in enumerate(row_sub_labels):
                row_lines[i] += wrap(sub, row_room, fs, body_font) if sub else []
        track_size, track_gap = 12.0, 4.0
        dendrow = 72.0 if dendrograms and dendrograms[0] else 0.0
        dendcol = 72.0 if dendrograms and dendrograms[1] else 0.0
        group_room = max(28.0, fs * 1.5 + 16) if domain_groups else 0.0
        x0 = side + group_room + row_room + 12 + dendrow + len(r_tracks) * (track_size + track_gap)
        legend_needed = show_colorbar or size_matrix is not None or r_tracks or c_tracks or summary or table_keys
        # Colorbar-only legends may move under the matrix on a narrow caller-sized canvas.
        legend_below = (
            compact
            and _compact.get("below")
            and show_colorbar
            and bool(scales)
            and size_matrix is None
            and not (r_tracks or c_tracks or summary or table_keys)
        )
        below_w = min(240.0, (W - 56 - 24 * (len(scales) - 1)) / max(1, len(scales)))
        below_h = (
            max(
                len(wrap(sc.label, below_w, legend_fs, body_font)) * legend_fs * 1.3
                + 8
                + (
                    len(wrap(colorbar_sub, below_w, legend_fs * 0.9, body_font)) * legend_fs * 1.2 + 6
                    if colorbar_sub and k == 0
                    else 0
                )
                + 12
                + legend_fs * 1.5
                + 8
                for k, sc in enumerate(scales)
            )
            if legend_below
            else 0.0
        )
        legend_titles = (
            [scale.label for scale in scales]
            + [t[0] for t in r_tracks + c_tracks + table_keys]
            + ([summary["title"]] if summary else [])
            + ([size_label] if size_matrix is not None else [])
        )
        legend_room = (
            min(
                W * 0.3,
                max(
                    96.0 if compact else 172.0,
                    legend_fs * (6 if compact else 10),
                    max((text_width(label, legend_fs, body_font) + 34 for label in legend_titles), default=0),
                ),
            )
            if legend_needed and not legend_below
            else 0.0
        )
        row_means = [mean(row) for row in visible_matrix] if show_row_mean else []
        mean_bar = 24.0 if compact else 50.0
        row_mean_texts = number_labels(row_means, value_fmt)
        means_room = (
            max(102.0, 89 + max((text_width(label, fs, body_font) for label in row_mean_texts), default=0))
            if not compact
            else 8 + mean_bar + 5 + max((text_width(label, fs, body_font) for label in row_mean_texts), default=0) + 2
            if show_row_mean
            else 0.0
        )
        compare_room = 190.0 if compare_cols is not None else 0.0
        x1 = W - side - legend_room - means_room - compare_room
        cw = (x1 - x0) / nc
        max_col_width = max(text_width(s, fs, body_font) for s in col_labels)
        angle = 0 if max_col_width <= cw - 8 else -90
        # With vertical labels, character height determines horizontal spacing and
        # full string width determines bottom clearance. No label is dropped.
        col_space = fs * 1.4 + 10 if angle == 0 else max_col_width + 14
        comparison_tick_layout = None
        if compare_cols is not None:
            a, b = compare_cols
            comparison_values = [row[c] for row in visible_matrix for c in (a, b) if row[c] is not None]
            comparison_min, comparison_max = min(comparison_values, default=0), max(comparison_values, default=1)
            compare_x = x1 + means_room + 20
            compare_width = compare_room - 35
            comparison_ticks = (
                [comparison_min, comparison_max] if comparison_min != comparison_max else [comparison_min]
            )
            comparison_positions = (
                [compare_x, compare_x + compare_width]
                if len(comparison_ticks) == 2
                else [compare_x + compare_width / 2]
            )
            if not comparison_values:
                comparison_ticks, comparison_positions = [], []
            comparison_tick_layout, comparison_tick_h = numeric_tick_layout(
                comparison_ticks,
                comparison_positions,
                compare_x,
                compare_width,
                fs,
                body_font,
                ["Min", "Max"],
                value_fmt,
            )
            col_space = max(col_space, comparison_tick_h + 15)
        table_headers = [wrap(label, cw - 12, fs, body_font) for label in col_labels] if columns is not None else None
        header_h = max(len(lines) * fs * 1.3 for lines in table_headers) + 12 if table_headers else 0
        if table_headers:
            col_space = 0
        means_h = fs * 1.6 + 14 if show_col_mean else 0.0
        side_heading_h = 0
        if show_row_mean:
            side_heading_h = len(wrap(row_mean_label, means_room - 10, legend_fs, body_font)) * legend_fs * 1.3 + 10
        if compare_cols is not None:
            a, b = compare_cols
            comparison_lines = [wrap(col_labels[index], compare_room - 55, legend_fs, body_font) for index in (a, b)]
            comparison_header_h = (1 + sum(len(lines) for lines in comparison_lines)) * legend_fs * 1.3 + 22
            side_heading_h = max(side_heading_h, comparison_header_h)
        y0 = top + max(dendcol + len(c_tracks) * (track_size + track_gap) + header_h, side_heading_h)
        y1 = H - 28 - footer_h - col_space - means_h - below_h
        ch = (y1 - y0) / nr
        required_h = max((len(lines) * fs * 1.3 for lines in row_lines), default=fs * 1.3)
        if cell_label_position == "below":
            required_h = max(required_h, fs * 3 + 8)
        cells_fit = (not cell_unit_w or (cw - 8) / cell_unit_w >= min_fs) and (
            not col_mean_unit_w or (cw - 6) / col_mean_unit_w >= min_fs
        )
        if cw >= max(10, fs * 1.15) and ch >= required_h + 3 and y1 > y0 and cells_fit:
            break
        if fs <= min_fs:
            break
        fs = max(min_fs, fs * 0.94)
    if cw < max(10, fs * 1.15) or ch < required_h + 3 or y1 <= y0 or not cells_fit:
        raise ValueError(
            f"Canvas too small for all matrix labels without overlap; increase width / height (current {W:g} x {H:g}, cell {cw:.1f} x {ch:.1f})"
        )
    if domain_groups:
        for start, end, label in domain_groups:
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= nr:
                raise ValueError("domain_groups ranges must satisfy 0 <= start < end <= rows")
            group_fs = min(fs, ((end - start) * ch - 8) / max(1, text_width(str(label), 1, body_font)))
            if group_fs < 8:
                raise ValueError("domain group label needs more vertical space")
            gy = y0 + (start + end) * ch / 2
            parts.append(text_svg(side + fs, gy, str(label), group_fs, pal["ink6"], body_font, "middle", rotate=-90))
            parts.append(
                f'<path d="M {x0 - 4:.2f} {y0 + start * ch:.2f} H {x0 - 8:.2f} V {y0 + end * ch:.2f} H {x0 - 4:.2f}" fill="none" stroke="{pal["ink4"]}"/>'
            )
    if dendrow:
        parts.append(dendrograms[0](x0 - len(r_tracks) * 16 - dendrow, x0 - len(r_tracks) * 16 - 6, y0, y1, pal))
    if dendcol:
        parts.append(dendrograms[1](x0, x1, top, top + dendcol - 6, pal))
    for t, (_, fills, _) in enumerate(r_tracks):
        for i, color in enumerate(fills):
            if color:
                parts.append(
                    f'<rect x="{x0 - (len(r_tracks) - t) * 16:.2f}" y="{y0 + i * ch:.2f}" width="12" height="{ch:.2f}" fill="{color}"/>'
                )
    for t, (_, fills, _) in enumerate(c_tracks):
        for j, color in enumerate(fills):
            if color:
                parts.append(
                    f'<rect x="{x0 + j * cw:.2f}" y="{top + dendcol + t * 16:.2f}" width="{cw:.2f}" height="12" fill="{color}"/>'
                )
    for i, lines in enumerate(row_lines):
        yy = y0 + (i + 0.5) * ch - (len(lines) - 1) * fs * 0.65 + fs * 0.33
        parts.append(
            text_svg(side + group_room + row_room, yy, lines, fs, pal["ink"], body_font, "end", italic=italic_rows)
        )
    col_y = y1 + means_h + 10
    for j, label in enumerate(col_labels):
        if table_headers:
            parts.append(
                text_svg(
                    x0 + (j + 0.5) * cw,
                    y0 - header_h + fs,
                    table_headers[j],
                    fs,
                    pal["ink"],
                    body_font,
                    "middle",
                    weight=600,
                )
            )
        else:
            parts.append(
                text_svg(
                    x0 + (j + 0.5) * cw,
                    col_y + (fs if angle == 0 else 0),
                    label,
                    fs,
                    pal["ink"],
                    body_font,
                    "middle" if angle == 0 else "end",
                    rotate=angle,
                )
            )
    glyph_h = ch - (fs * 1.6 + 8 if cell_label_position == "below" else 0)
    rmax = min(45.0, min(cw, glyph_h) * 0.40)
    if compact and _compact.get("rmax") is not None:
        rmax = min(rmax, _compact["rmax"])
    if size_matrix is not None:
        size_limits = []
        size_legend_specs = []
        for triangle in range(2 if upper_matrix is not None else 1):
            source_matrix = visible_matrix
            observed_sizes = [
                size_matrix[i][j]
                for i, row in enumerate(source_matrix)
                for j, v in enumerate(row)
                if v is not None
                and size_matrix[i][j] is not None
                and (upper_matrix is None or ((i < j) if triangle else (i >= j)))
            ]
            actual_max = max(observed_sizes, default=0)
            limit = upper_size_options.get("size_max") if triangle else size_max
            limit = actual_max if limit is None else float(limit)
            if not math.isfinite(limit) or limit < actual_max or limit < 0:
                raise ValueError("size_max must be finite and at least the largest observed size")
            size_limits.append(limit)
            label = upper_size_options.get("size_label", tr("Upper size")) if triangle else size_label
            reps = upper_size_options.get("size_legend_values") if triangle else size_legend_values
            size_legend_specs.append((label, limit, reps))
        key_labels = []
        for _, limit, requested in size_legend_specs:
            reps = list(requested) if requested is not None else ([limit * 0.25, limit * 0.5, limit] if limit else [0])
            key_labels.extend(label + size_suffix for label in number_labels(reps))
        key_width = max((text_width(label, legend_fs, body_font) for label in key_labels), default=0)
        rmax = min(rmax, max(5, (legend_room - 40 - key_width) / 2))

        def radius(value, triangle=0):
            limit = size_limits[triangle]
            return rmax * math.sqrt(value / limit) if limit > 0 else 0.0

    if size_matrix is not None:
        for i in range(nr):
            if i % 2:
                parts.append(
                    f'<rect x="{x0:.2f}" y="{y0 + i * ch:.2f}" width="{x1 - x0:.2f}" height="{ch:.2f}" fill="{pal["ink1"]}" opacity=".22"/>'
                )
    for i, row in enumerate(visible_matrix):
        for j, value in enumerate(row):
            if variant == "ellipse_upper" and upper_matrix is None and i > j:
                continue
            this_scale = scales[1] if upper_matrix is not None and i < j else scale
            if column_scales is not None and column_scales[j] is not None:
                this_scale = column_scales[j]
            x, y = x0 + j * cw, y0 + i * ch
            nonnumeric = table_raw is not None and columns[j].get("type", "number") != "number"
            literal = table_raw[i][j] if nonnumeric and not (mask is not None and mask[i][j]) else None
            semantic_value = str(literal) if literal is not None else (value if value is not None else "missing")
            parts.append(f'<g data-row="{i}" data-col="{j}" data-value="{_attr(str(semantic_value), quote=True)}">')
            if literal is not None:
                fill = dict(column_categories[j]).get(str(literal), pal.get("bg") or "white")
                parts.append(
                    f'<rect x="{x + 0.35:.2f}" y="{y + 0.35:.2f}" width="{cw - 0.7:.2f}" height="{ch - 0.7:.2f}" fill="{fill}" stroke="{pal["ink1"]}" stroke-width=".5"/>'
                )
                content = (
                    str(cell_text[i][j]) if cell_text is not None and cell_text[i][j] is not None else str(literal)
                )
                lines = wrap(content, cw - 12, fs, body_font)
                if len(lines) * fs * 1.3 > ch - 8:
                    raise ValueError("Table cell text needs more space; increase height / width")
                rr, gg, bb = _rgb_tuple(fill)
                color = "rgb(24,26,34)" if 0.299 * rr + 0.587 * gg + 0.114 * bb > 145 else "rgb(250,250,248)"
                parts.append(
                    text_svg(
                        x + cw / 2,
                        y + ch / 2 - (len(lines) - 1) * fs * 0.65 + fs * 0.33,
                        lines,
                        fs,
                        color,
                        body_font,
                        "middle",
                    )
                )
            elif value is None:
                parts.append(
                    f'<rect x="{x + 0.35:.2f}" y="{y + 0.35:.2f}" width="{cw - 0.7:.2f}" height="{ch - 0.7:.2f}" fill="{pal["ink1"]}"/>'
                )
                missing_label = (
                    str(cell_text[i][j]) if cell_text is not None and cell_text[i][j] is not None else "\u2014"
                )
                missing_lines = wrap(missing_label, cw - 12, fs, body_font)
                if len(missing_lines) * fs * 1.3 > ch - 8:
                    raise ValueError("Cell text needs more space")
                parts.append(
                    text_svg(
                        x + cw / 2,
                        y + ch / 2 - (len(missing_lines) - 1) * fs * 0.65 + fs * 0.33,
                        missing_lines,
                        fs,
                        pal["ink6"],
                        body_font,
                        "middle",
                    )
                )
            elif size_matrix is not None:
                rr = (
                    radius(size_matrix[i][j], int(upper_matrix is not None and i < j))
                    if size_matrix[i][j] is not None
                    else 0
                )
                if rr > 0:
                    if variant == "square_flat_full":
                        parts.append(
                            f'<rect x="{x + cw / 2 - rr:.2f}" y="{y + glyph_h / 2 - rr:.2f}" width="{2 * rr:.4f}" height="{2 * rr:.4f}" fill="{this_scale.color(value)}" stroke="{pal["ink4"]}" stroke-width=".5"/>'
                        )
                    else:
                        parts.append(
                            f'<circle cx="{x + cw / 2:.2f}" cy="{y + glyph_h / 2:.2f}" r="{rr:.4f}" fill="{this_scale.color(value)}" stroke="{pal["ink4"]}" stroke-width=".5"/>'
                        )
            else:
                parts.append(_cell_shape(variant, x, y, cw, glyph_h, value, this_scale))
            if value is not None:
                label = (
                    str(cell_text[i][j])
                    if cell_text is not None and cell_text[i][j] is not None
                    else (
                        format_value(value, value_fmt, this_scale.high - this_scale.low)
                        if show_values or variant == "annotated_number"
                        else ""
                    )
                )
                p = pvalues[i][j] if pvalues is not None else None
                sig = (
                    "***"
                    if p is not None and p < 0.001
                    else "**"
                    if p is not None and p < 0.01
                    else "*"
                    if p is not None and p < 0.05
                    else ""
                )
                label_lines = (
                    wrap(label, cw - 12, fs, body_font)
                    if label and cell_text is not None
                    else ([label] if label else [])
                )
                labels = label_lines + ([sig] if sig else [])
                if labels:
                    text_fs = min(
                        fs,
                        ch / (len(labels) * 1.7),
                        (cw - 8) / max(1, max(text_width(s, 1, body_font) for s in labels)),
                    )
                    if text_fs < min_fs:
                        raise ValueError(
                            "Cell text needs more space; increase the canvas or shorten cell_text / value_fmt"
                        )
                    color = (
                        this_scale.contrast(value)
                        if variant in {"square_flat_full", "annotated_number"} and size_matrix is None
                        else pal["ink"]
                    )
                    if cell_label_position == "below":
                        available_h = ch - glyph_h - 5
                        text_fs = min(text_fs, available_h / (len(labels) * 1.3))
                        if text_fs < 8:
                            raise ValueError("Below-cell labels need more height")
                        yy = y + glyph_h + 3 + text_fs + (available_h - len(labels) * text_fs * 1.3) / 2
                    else:
                        yy = y + ch / 2 - (len(labels) - 1) * text_fs * 0.65 + text_fs * 0.33
                    parts.append(text_svg(x + cw / 2, yy, labels, text_fs, color, body_font, "middle", 500))
            if highlight_pair is not None and (i, j) in {tuple(highlight_pair), tuple(reversed(highlight_pair))}:
                parts.append(
                    f'<rect x="{x + 1:.2f}" y="{y + 1:.2f}" width="{cw - 2:.2f}" height="{ch - 2:.2f}" fill="none" stroke="{pal["ink"]}" stroke-width="2"/>'
                )
            parts.append("</g>")
    if _overlays:
        context = MatrixContext(
            plot_bbox=(x0, y0, x1, y1),
            column_centers=tuple(x0 + (j + 0.5) * cw for j in range(nc)),
            row_centers=tuple(y0 + (i + 0.5) * ch for i in range(nr)),
            row_labels=tuple(row_labels),
            col_labels=tuple(col_labels),
            scales=tuple(scales),
            palette=dict(pal),
            matrix=tuple(tuple(row) for row in visible_matrix),
            row_order=tuple((metadata or {}).get("row_order", range(nr))),
            col_order=tuple((metadata or {}).get("col_order", range(nc))),
            font_family=body_font,
        )
        for callback in _overlays:
            fragment = callback(context)
            if not isinstance(fragment, str):
                raise TypeError("A matrix overlay callback must return an SVG fragment")
            parts.append(fragment)
    parts.append(
        f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" fill="none" stroke="{pal["ink4"]}" stroke-width=".7"/>'
    )

    if show_row_mean:
        mx = x1 + (8 if compact else 16)
        mean_heading = wrap(row_mean_label, means_room - 10, legend_fs, body_font)
        parts.append(
            text_svg(
                mx, y0 - 10 - (len(mean_heading) - 1) * legend_fs * 1.3, mean_heading, legend_fs, pal["ink6"], body_font
            )
        )
        observed = [v for v in row_means if v is not None]
        lo, hi = min([0] + observed), max([0] + observed)
        zero = mx + stable_fraction(0, lo, hi) * mean_bar
        for i, value in enumerate(row_means):
            yy = y0 + (i + 0.5) * ch
            if value is not None:
                end = mx + stable_fraction(value, lo, hi) * mean_bar
                parts.append(
                    f'<rect x="{min(zero, end):.2f}" y="{yy - 4:.2f}" width="{abs(end - zero):.2f}" height="8" fill="{scale.color(value)}"/>'
                )
            parts.append(
                text_svg(
                    mx + mean_bar + (5 if compact else 7), yy + fs * 0.33, row_mean_texts[i], fs, pal["ink6"], body_font
                )
            )
        parts.append(f'<line x1="{zero:.2f}" y1="{y0:.2f}" x2="{zero:.2f}" y2="{y1:.2f}" stroke="{pal["ink2"]}"/>')
    if show_col_mean:
        parts.append(text_svg(x0 - 10, y1 + fs + 10, tr("Col mean"), legend_fs, pal["ink6"], body_font, "end"))
        column_mean_texts = number_labels([mean([row[j] for row in visible_matrix]) for j in range(nc)], value_fmt)
        for j in range(nc):
            label = column_mean_texts[j]
            f = min(fs, (cw - 6) / max(1, text_width(label, 1, body_font)))
            if f < min_fs:
                raise ValueError("Column mean text needs more width")
            parts.append(text_svg(x0 + (j + 0.5) * cw, y1 + fs + 10, label, f, pal["ink6"], body_font, "middle"))
    if compare_cols is not None:
        a, b = compare_cols
        px = x1 + means_room + 20
        pw = compare_room - 35
        header_y = y0 - comparison_header_h + legend_fs
        parts.append(text_svg(px, header_y, tr("Displayed values"), legend_fs, pal["ink"], body_font, weight=600))
        header_y += legend_fs * 1.3 + 6
        for index, lines, color in [
            (a, comparison_lines[0], pal["secondary"]),
            (b, comparison_lines[1], pal["accent"]),
        ]:
            parts.append(
                f'<circle data-comparison-key="{index}" cx="{px + 4:.2f}" cy="{header_y - legend_fs * 0.3:.2f}" r="3.5" fill="{color}"/>'
            )
            parts.append(text_svg(px + 14, header_y, lines, legend_fs, pal["ink6"], body_font))
            header_y += len(lines) * legend_fs * 1.3 + 4
        vals = [row[c] for row in visible_matrix for c in (a, b) if row[c] is not None]
        lo, hi = min(vals, default=0), max(vals, default=1)

        def X(v):
            if hi == lo:
                return px + pw / 2
            return px + 4 + stable_fraction(v, lo, hi) * (pw - 8)

        marker_radius = min(4.0, (ch - 2) / 4)
        for i, row in enumerate(visible_matrix):
            yy = y0 + (i + 0.5) * ch
            parts.append(f'<g data-comparison-row="{i}">')
            marker_y = {a: yy, b: yy}
            if row[a] is not None and row[b] is not None:
                if abs(X(row[a]) - X(row[b])) < 2 * marker_radius + 1:
                    # Categorical-row offsets separate glyphs without moving
                    # either observation away from its exact numeric X value.
                    offset = marker_radius + 0.5
                    marker_y = {a: yy - offset, b: yy + offset}
                parts.append(
                    f'<line x1="{X(row[a]):.2f}" y1="{marker_y[a]:.2f}" x2="{X(row[b]):.2f}" y2="{marker_y[b]:.2f}" stroke="{pal["ink4"]}"/>'
                )
            for index, value, color in [(a, row[a], pal["secondary"]), (b, row[b], pal["accent"])]:
                if value is not None:
                    parts.append(
                        f'<circle data-comparison-col="{index}" data-value="{value}" cx="{X(value):.6g}" cy="{marker_y[index]:.6g}" r="{marker_radius:.4f}" fill="{color}"/>'
                    )
            parts.append("</g>")
        parts.append(numeric_tick_svg(comparison_tick_layout, y1 + fs + 10, pal["ink6"], body_font))
    # Legends occupy one measured column, with no fixed minimum colorbar height
    # that could force the last legend off the canvas.
    lx = W - side - legend_room + (12 if compact else 24)
    ly = top
    lw = legend_room - (16 if compact else 30)
    if legend_below:
        lx, lw = side, below_w
        ly = H - 28 - footer_h - below_h + 4

    def heading(label):
        nonlocal ly
        lines = wrap(label, lw, legend_fs, body_font)
        parts.append(text_svg(lx, ly + legend_fs, lines, legend_fs, pal["ink"], body_font, weight=600))
        ly += len(lines) * legend_fs * 1.3 + 8

    def colorbar(current, subtitle=None):
        nonlocal ly
        heading(current.label)
        if subtitle:
            lines = wrap(subtitle, lw, legend_fs * 0.9, body_font)
            parts.append(text_svg(lx, ly + legend_fs * 0.9, lines, legend_fs * 0.9, pal["ink6"], body_font))
            ly += len(lines) * legend_fs * 1.2 + 6
        bh = 12
        for band in range(48):
            t = (band + 0.5) / 48
            parts.append(
                f'<rect x="{lx + lw * band / 48:.2f}" y="{ly:.2f}" width="{lw / 48 + 0.5:.2f}" height="{bh}" fill="{current.color(current.value_at(t))}"/>'
            )
        ticks = [current.low] if current.low == current.high else [current.low, current.high]
        if current.midpoint is not None and current.low < current.midpoint < current.high:
            ticks.insert(1, current.midpoint)
        positions = [lx + current.fraction(tick) * lw for tick in ticks]
        roles = [
            tr("Midpoint") if tick == current.midpoint else tr("Min") if tick == current.low else tr("Max")
            for tick in ticks
        ]
        tick_layout, tick_height = numeric_tick_layout(ticks, positions, lx, lw, legend_fs, body_font, roles)
        for tx in positions:
            parts.append(
                f'<line x1="{tx:.4f}" y1="{ly + bh:.2f}" x2="{tx:.4f}" y2="{ly + bh + 3:.2f}" stroke="{pal["ink4"]}" stroke-width=".7"/>'
            )
        parts.append(numeric_tick_svg(tick_layout, ly + bh + legend_fs + 4, pal["ink6"], body_font))
        ly += bh + tick_height + 20

    if size_matrix is not None:
        for triangle, (legend_label, limit, requested) in enumerate(size_legend_specs):
            heading(legend_label)
            reps = list(requested) if requested is not None else ([limit * 0.25, limit * 0.5, limit] if limit else [0])
            if not reps or any(not math.isfinite(float(v)) or v < 0 or v > limit for v in reps):
                raise ValueError("size_legend_values must lie inside 0..size_max")
            size_values = sorted(set(reps))
            size_texts = [label + size_suffix for label in number_labels(size_values)]
            size_text_width = lw - 2 * rmax - 10
            for value, label in zip(size_values, size_texts):
                rr = radius(value, triangle)
                label_fs = min(legend_fs, size_text_width / max(1, text_width(label, 1, body_font)))
                row_h = max(label_fs * 1.5, rr * 2 + 4)
                cy = ly + row_h / 2
                if variant == "square_flat_full":
                    parts.append(
                        f'<rect x="{lx + rmax - rr:.2f}" y="{cy - rr:.2f}" width="{2 * rr:.4f}" height="{2 * rr:.4f}" fill="none" stroke="{pal["ink6"]}"/>'
                    )
                else:
                    parts.append(
                        f'<circle cx="{lx + rmax:.2f}" cy="{cy:.2f}" r="{rr:.4f}" fill="none" stroke="{pal["ink6"]}"/>'
                    )
                parts.append(
                    text_svg(lx + 2 * rmax + 10, cy + label_fs * 0.33, label, label_fs, pal["ink6"], body_font)
                )
                ly += row_h + 4
            ly += 10
    if show_colorbar and legend_below:
        band_top, band_bottom = ly, ly
        for index, current in enumerate(scales):
            lx, ly = side + index * (below_w + 24), band_top
            colorbar(current, colorbar_sub if index == 0 else None)
            band_bottom = max(band_bottom, ly - 20)
        ly = band_bottom
    elif show_colorbar:
        for index, current in enumerate(scales):
            colorbar(current, colorbar_sub if index == 0 else None)
    for name, _, key in r_tracks + c_tracks + table_keys:
        if isinstance(key, ColorScale):
            colorbar(key)
        else:
            heading(name)
            for label, color in key:
                lines = wrap(label, lw - 22, legend_fs, body_font)
                parts.append(f'<rect x="{lx:.2f}" y="{ly + 2:.2f}" width="10" height="10" fill="{color}"/>')
                parts.append(text_svg(lx + 18, ly + legend_fs, lines, legend_fs, pal["ink6"], body_font))
                ly += max(16, len(lines) * legend_fs * 1.3) + 3
            ly += 10
    if summary:
        heading(summary["title"])
        items = summary["items"]
        maxv = max((v for _, v, _ in items), default=1) or 1
        for label, value, detail in items:
            lines = wrap(f"{label} ({value:g})", lw, legend_fs, body_font)
            parts.append(text_svg(lx, ly + legend_fs, lines, legend_fs, pal["ink6"], body_font))
            ly += len(lines) * legend_fs * 1.3 + 5
            parts.append(
                f'<rect x="{lx:.2f}" y="{ly:.2f}" width="{lw * value / maxv:.2f}" height="6" fill="{pal["secondary"]}"/>'
            )
            ly += 12
            if detail:
                lines = wrap(", ".join(detail), lw, legend_fs * 0.9, body_font)
                parts.append(text_svg(lx, ly + legend_fs * 0.9, lines, legend_fs * 0.9, pal["ink6"], body_font))
                ly += len(lines) * legend_fs * 1.2 + 7
    if ly > H - 28 - footer_h:
        raise ValueError(
            "Canvas height is too small for all legends / annotation keys; increase height or reduce tracks"
        )
    if footer:
        parts.append(
            text_svg(28, H - 28 - (len(footer) - 1) * legend_fs * 1.3, footer, legend_fs, pal["ink6"], body_font)
        )
    meta = {
        "rows": nr,
        "cols": nc,
        "variant": variant,
        "cell_label_position": cell_label_position,
        "plot_bbox": [x0, y0, x1, y1],
        "column_centers": [x0 + (j + 0.5) * cw for j in range(nc)],
        "row_centers": [y0 + (i + 0.5) * ch for i in range(nr)],
        "row_labels": row_labels,
        "col_labels": col_labels,
        **(metadata or {}),
    }
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" font-family="{_attr(body_font, quote=True)}" data-matrix-layout="{_attr(json.dumps(meta, ensure_ascii=False), quote=True)}">'
        + "".join(parts)
        + "</svg>"
    )
