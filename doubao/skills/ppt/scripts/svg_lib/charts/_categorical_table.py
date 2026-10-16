"""Row-aligned statistical tables and forest rendering with measured gutters."""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

from ._academic_rigor import BBox
from ._chart_layout import (
    ChartLayout,
    finite,
    wrap_lines,
    forest_estimate_text,
    precise_number,
    forest_ci_context,
    forest_scale,
)
from ._composition import attrs, footer, heading, numeric_axis
from ._xy import _text
from ._shared import ZH_CHROME, tr

ZH_CHROME.setdefault("Events", "事件数")


def _cell_text(value):
    if value is None:
        return "—"
    if isinstance(value, float):
        return precise_number(value)
    return str(value)


def normalize_columns(columns):
    defaults = {"n": "N", "p": "P", "mean": "Mean", "sd": "SD", "events": tr("Events")}
    out = []
    for c in columns:
        c = dict(c) if isinstance(c, dict) else {"key": str(c), "label": defaults.get(str(c), str(c))}
        if not c.get("key"):
            raise ValueError("each table column needs a key")
        c.setdefault("label", c["key"])
        out.append(c)
    if len({c["key"] for c in out}) != len(out):
        raise ValueError("table column keys must be unique")
    return out


def render_table_plot(rows, bbox, *, columns, centers, layout, header_top=None):
    """Return a flat table fragment."""
    columns = normalize_columns(columns)
    fs = layout.font_sizes["label"]
    box = BBox(*bbox)
    if len(rows) != len(centers):
        raise ValueError("table centers must match rows")
    widths = [
        c.get(
            "width",
            max(
                layout.measure(c["label"], fs, True),
                max((layout.measure(_cell_text(r.get(c["key"])), fs) for r in rows), default=0),
            )
            + 22,
        )
        for c in columns
    ]
    if sum(widths) > box.x1 - box.x0 + 1e-6:
        raise ValueError("table columns do not fit the allocated width")
    parts, x = [], box.x0
    for c, width in zip(columns, widths):
        if header_top is not None:
            parts.append(
                _text(
                    c["label"],
                    x,
                    header_top + fs * 0.84,
                    layout.font,
                    layout.ink,
                    fs=fs,
                    weight=600,
                    role="table-header",
                )
            )
        for row, y in zip(rows, centers):
            if row.get("is_subgroup_header"):
                continue
            parts.append(
                f"<g {attrs(role='table-cell', row_id=row['row_id'], column=c['key'])}>{_text(_cell_text(row.get(c['key'])), x, y + fs * 0.3, layout.font, layout.ink, fs=fs)}</g>"
            )
        x += width
    return "".join(parts)


def normalize_forest_rows(rows, log_x=False):
    out = []
    for i, row in enumerate(rows):
        r = dict(row, row_id=str(row.get("row_id", i)))
        if not r.get("is_subgroup_header"):
            supplied = [r.get(k) is not None for k in ("estimate", "ci_lo", "ci_hi")]
            if supplied == [True, False, False]:
                # Estimate only: a point without whiskers (chart_slide suggests coef_plot / dot plot).
                est = finite(r["estimate"], "estimate")
                if log_x and est <= 0:
                    raise ValueError("log forest estimates must be positive")
                r.update(estimate=est, ci_lo=est, ci_hi=est, _point_only=True)
                supplied = [True, True, True]
            elif any(supplied) and not all(supplied):
                raise ValueError("forest estimate requires both confidence limits")
            if all(supplied):
                est, lo, hi = (finite(r[k], k) for k in ("estimate", "ci_lo", "ci_hi"))
                if not lo <= est <= hi:
                    raise ValueError("forest interval must satisfy ci_lo <= estimate <= ci_hi")
                if log_x and lo <= 0:
                    raise ValueError("log forest intervals must be positive")
                r.update(estimate=est, ci_lo=lo, ci_hi=hi)
            if isinstance(r.get("p"), str):
                r["_p_text"] = r.pop("p").strip()
            for key in ("n", "p", "mean", "sd"):
                if key in r and r[key] is not None:
                    r[key] = finite(r[key], key, minimum=0 if key in ("n", "p", "sd") else None)
            if r.get("n") is not None and not r["n"].is_integer():
                raise ValueError("forest N must be an integer")
            if r.get("n") is not None:
                r["n"] = int(r["n"])
            if r.get("p") is not None and r["p"] > 1:
                raise ValueError("forest P must be <= 1")
            if isinstance(r.get("events"), float) and r["events"].is_integer():
                r["events"] = int(r["events"])
        out.append(r)
    if not out or len({r["row_id"] for r in out}) != len(out):
        raise ValueError("forest rows must be non-empty with unique row_id")
    return out


def forest_p_text(row):
    """Journal P display: "<0.001", "0.003", "0.19"; a supplied string ("<0.001") is kept."""
    if row.get("_p_text"):
        return row["_p_text"]
    p = row.get("p")
    if p is None:
        return None
    return "<0.001" if p < 0.001 else f"{p:.2g}" if p < 0.1 else f"{p:.2f}"


def heterogeneity_text(het):
    """``{I2: 43, tau2: 0.02, Q: 12.1, df: 6, p: 0.03}`` → "I²=43%, τ²=0.02, Q=12.1 (df=6), P=0.03"; a string is kept."""
    if not het:
        return ""
    if isinstance(het, str):
        return het.strip()
    if not isinstance(het, dict):
        raise TypeError("heterogeneity must be a dict like {'I2': 43, 'tau2': 0.02, 'p': 0.03} or a string")
    h = {str(k).lower().replace("²", "2"): v for k, v in het.items()}
    unknown = set(h) - {"i2", "tau2", "q", "df", "p"}
    if unknown:
        raise ValueError(f"heterogeneity keys must be I2/tau2/Q/df/p, got {sorted(unknown)}")
    num = lambda v: v.strip() if isinstance(v, str) else precise_number(finite(v, "heterogeneity"))
    parts = []
    if h.get("i2") is not None:
        i2 = h["i2"]
        if not isinstance(i2, str):
            i2 = finite(i2, "I2")
            i2 = f"{i2 * 100 if 0 < i2 < 1 else i2:.0f}%"  # 0.43 or 43 → 43%
        parts.append(f"I²={i2}")
    if h.get("tau2") is not None:
        parts.append(f"τ²={num(h['tau2'])}")
    if h.get("q") is not None:
        parts.append(f"Q={num(h['q'])}" + (f" (df={num(h['df'])})" if h.get("df") is not None else ""))
    if h.get("p") is not None:
        p = h["p"]
        if isinstance(p, str):
            p = p.strip().lstrip("pP").strip()
            parts.append("P" + (p if p[:1] in "<>=≤≥" else "=" + p))
        else:
            parts.append("P=" + forest_p_text({"p": finite(p, "p")}))
    return ", ".join(parts)


ZH_CHROME.setdefault("Heterogeneity: ", "异质性：")


def insert_heterogeneity(rows, het):
    """A plain statistics line (no marker) directly under the pooled ``is_overall`` row."""
    text = heterogeneity_text(het)
    if not text:
        return list(rows)
    pooled = [i for i, r in enumerate(rows) if isinstance(r, dict) and r.get("is_overall")]
    if not pooled:
        raise ValueError("heterogeneity= needs a pooled row (is_overall=True) to sit under")
    out = list(rows)
    out.insert(
        pooled[-1] + 1,
        {"label": tr("Heterogeneity: ") + text, "is_subgroup_header": True, "_het": True, "row_id": "_heterogeneity"},
    )
    return out


def draw_favours(layout, favours, mid_x, y, fs, color=None):
    """``favours=(left, right)`` labels with arrows either side of the null line; returns used height."""
    if favours is None:
        return 0
    if len(favours) != 2:
        raise ValueError("favours must be a (left, right) pair of labels")
    left, right = (f"← {favours[0]}" if favours[0] else ""), (f"{favours[1]} →" if favours[1] else "")
    lw, rw = layout.measure(left, fs), layout.measure(right, fs)
    lx = max(28 + lw, mid_x - 8)
    rx = min(layout.width - 28 - rw, max(mid_x + 8, lx + 16))
    color = color or layout.pal["ink6"]
    for text, x, anchor, side in ((left, lx, "end", "left"), (right, rx, "start", "right")):
        if text:
            layout.parts.append(
                _text(text, x, y + fs * 0.84, layout.font, color, fs=fs, anchor=anchor, role=f"favours-{side}")
            )
    return fs * 1.35 + 6


def make_forest_table(
    rows,
    *,
    columns=None,
    row_order=None,
    x_title="Hazard ratio",
    x_unit="",
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    midline_value=1.0,
    log_x=False,
    value_domain=None,
    left_header="Subgroup",
    right_header_label="Estimate (CI)",
    width=1400,
    height=800,
    font_family=None,
    palette=None,
    favours=None,
    heterogeneity=None,
):
    rows = normalize_forest_rows(insert_heterogeneity(rows, heterogeneity), log_x)
    rows, right_header_label = forest_ci_context(rows, right_header_label)
    if row_order is not None:
        order = [str(v) for v in row_order]
        if len(order) != len(rows) or set(order) != {r["row_id"] for r in rows}:
            raise ValueError("row_order must contain every row_id exactly once")
        lookup = {r["row_id"]: r for r in rows}
        rows = [lookup[k] for k in order]
    columns = normalize_columns(
        columns
        if columns is not None
        else [
            k for k in ("n", "events", "mean", "sd", "p") if any(k in r or (k == "p" and "_p_text" in r) for r in rows)
        ]
    )
    for c in columns:
        if c["key"] == "p":
            c["key"] = "_p"
            for r in rows:
                r["_p"] = forest_p_text(r) if not r.get("is_subgroup_header") else None
    values = [v for r in rows if r.get("estimate") is not None for v in (r["ci_lo"], r["ci_hi"])]
    if not values:
        raise ValueError("forest needs at least one complete numeric estimate")
    midline_value = finite(midline_value, "midline_value")
    scale = forest_scale(values, midline_value, log_x=log_x, value_domain=value_domain)
    layout = ChartLayout(width, height, palette or "archive_ink", font_family, n_items=len(rows))
    fs = layout.font_sizes["label"]
    axis_fs = layout.font_sizes["xaxis"]
    line_h = fs * 1.35
    top = layout.header(title, subtitle, figure_label) + 8
    small_fs = max(10.0, fs * 0.85)
    favours_h = small_fs * 1.35 + 6 if favours else 0
    bottom = footer(layout, note, source) - fs * 1.35 - axis_fs * 1.35 - 25 - favours_h
    label_width = min(
        layout.width * 0.28,
        max(layout.measure(left_header, fs, True), max(layout.measure(r.get("label", ""), fs, True) for r in rows)),
    )
    label_width = max(65, label_width)
    for r in rows:
        r["_estimate"] = (
            ""
            if r.get("is_subgroup_header")
            else (forest_estimate_text(r, midline_value) if r.get("estimate") is not None else "—")
        )
    columns = [{"key": "_estimate", "label": right_header_label}, *columns]
    content = [
        max(layout.measure(c["label"], fs, True), max(layout.measure(_cell_text(r.get(c["key"])), fs) for r in rows))
        for c in columns
    ]
    # Slide panels: tighter column gutters before the canvas has to grow.
    for pad, gap, plot_min in ((23, 22, 180), (14, 14, 150)):
        for c, w in zip(columns, content):
            c["width"] = w + pad
        table_width = sum(c["width"] for c in columns)
        left, right = 28 + label_width + 24, layout.width - 28 - table_width - gap
        if right - left >= plot_min:
            break
    else:
        raise ValueError("canvas is too narrow for forest plot and measured statistics columns")
    header_height = max(len(wrap_lines(left_header, label_width, fs, layout.font)) * line_h, fs * 1.35)
    top += header_height + 16
    # The heterogeneity line has no marker or cells: it may run across the plot instead of wrapping.
    labels = [
        wrap_lines(r.get("label", ""), layout.width - 56 if r.get("_het") else label_width, fs, layout.font)
        for r in rows
    ]
    heights = [max(32, len(lines) * line_h + 12) for lines in labels]
    if sum(heights) > bottom - top:
        # Slide panels: rows tighten to the text line before the canvas has to grow.
        heights = [max(fs * 1.55, len(lines) * line_h + 4) for lines in labels]
    if sum(heights) > bottom - top:
        raise ValueError("canvas is too short for forest rows; increase height")
    extra = min(22, (bottom - top - sum(heights)) / len(rows))
    centers, cursor = [], top
    for h in heights:
        centers.append(cursor + (h + extra) / 2)
        cursor += h + extra
    box = BBox(left, top, right, cursor)
    layout.text(left_header, 28, top - header_height - 12, fs=fs, bold=True, width=label_width)
    layout.parts.append(
        render_table_plot(
            rows,
            BBox(right + gap, top, layout.width - 28, cursor),
            columns=columns,
            centers=centers,
            layout=layout,
            header_top=top - header_height - 12,
        )
    )
    X = lambda v: scale.map(v, left, right)
    layout.parts.append(
        f'<path d="M{X(midline_value)},{top} V{cursor}" stroke={quoteattr(layout.pal["ink6"])} stroke-dasharray="4 4" data-role="forest-reference"/>'
    )
    for i, (r, center, lines) in enumerate(zip(rows, centers, labels)):
        if i % 2 == 0:
            layout.parts.insert(
                0,
                f'<rect x="24" y="{center - (heights[i] + extra) / 2:.3f}" width="{layout.width - 48}" height="{heights[i] + extra:.3f}" fill={quoteattr(layout.pal["ink"])} fill-opacity=".025"/>',
            )
        layout.parts.append(f"<g {attrs(role='forest-row', row_id=r['row_id'], center=center)}>")
        layout.text(
            "\n".join(lines),
            28,
            center - len(lines) * line_h / 2,
            fs=fs,
            bold=(r.get("is_subgroup_header") and not r.get("_het")) or r.get("is_overall"),
            color=layout.pal["ink6"] if r.get("_het") else None,
        )
        if r.get("estimate") is not None:
            x, lo, hi = X(r["estimate"]), X(r["ci_lo"]), X(r["ci_hi"])
            if r.get("is_overall"):
                dh = min(6, (heights[i] + extra) * 0.3)
                path = f"M{lo},{center} L{x},{center - dh} L{hi},{center} L{x},{center + dh} Z"
                layout.parts.append(
                    f'<path d="{path}" fill={quoteattr(layout.pal["accent"])} data-role="forest-diamond"/>'
                )
            else:
                if not r.get("_point_only"):
                    layout.parts.append(
                        f'<path d="M{lo},{center} H{hi} M{lo},{center - 4} v8 M{hi},{center - 4} v8" fill="none" stroke={quoteattr(layout.pal["accent"])} stroke-width="1.5" data-role="forest-interval"/>'
                    )
                layout.parts.append(
                    f'<rect x="{x - 4}" y="{center - 4}" width="8" height="8" fill={quoteattr(layout.pal["accent"])} data-role="forest-estimate"/>'
                )
        layout.parts.append("</g>")
    numeric_axis(layout, box, scale)
    favours_h = draw_favours(layout, favours, X(midline_value), cursor + line_h + 10, small_fs)
    layout.text(
        heading(x_title, scale, x_unit),
        (left + right) / 2,
        cursor + line_h + 14 + favours_h,
        fs=axis_fs,
        anchor="middle",
        width=right - left,
    )
    numeric = [r for r in rows if not r.get("is_subgroup_header") and r.get("estimate") is not None]
    if numeric and all(r.get("_point_only") for r in numeric):
        layout.parts.append('<g data-role="forest-layout" data-forest-ci="none"></g>')
    return layout.svg(title or "Forest plot with statistics")
