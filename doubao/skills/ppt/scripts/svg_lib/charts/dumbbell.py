"""Two-endpoint comparisons with stable row ordering and truthful distances."""

from .._typography import chart_font_sizes
from ._chart_layout import precise_number
from ._xy import _spread_positions
from decimal import Decimal
import re
import math
from ._academic_rigor import nice_axis
from .._common import _fmt_axis
from ._distribution import (
    Canvas,
    _derive_series_colors,
    _resolve_palette,
    draw_header,
    finite,
    header_height,
    legend_layout,
    measure,
    wrap,
)
from ._shared import ZH_CHROME, tr

ZH_CHROME.setdefault("{a} to {b}", "{a} 至 {b}")


# Multi-mode whitelist: with_ranked_delta → ranked-by-delta sub-strip under the main dumbbell.
def _validate_ranked_delta(signals):
    n = int(signals.get("n_rows", 0))
    if n < 3:
        return (False, f"need >=3 rows for ranked-delta sub-panel (got {n})")
    return (True, "")


_DUMBBELL_MULTI_WHITELIST = {
    "with_ranked_delta": (
        None,  # layout handled inline below, not via allocate_main_sub
        lambda s: int(s.get("n_rows", 0)) >= 3,
        lambda s: _validate_ranked_delta(s),
    ),
}


_RANGE_LOW = {
    "min",
    "minimum",
    "lower",
    "lowerbound",
    "lowerlimit",
    "low",
    "lowend",
    "lo",
    "最小",
    "最小值",
    "最低",
    "最低值",
    "低值",
}
_RANGE_HIGH = {
    "max",
    "maximum",
    "upper",
    "upperbound",
    "upperlimit",
    "high",
    "highend",
    "hi",
    "最大",
    "最大值",
    "最高",
    "最高值",
    "高值",
}


_FOOT_LABEL = None


def _prefixed(prefix, content):
    """Prepend "注："/"来源：" unless the caller's text already starts with such a label (mirrors forest)."""
    import re

    global _FOOT_LABEL
    if _FOOT_LABEL is None:
        _FOOT_LABEL = re.compile(
            r"^(?:注|备注|说明|(?:数据|资料)?来源|出处|Notes?|Sources?|Data sources?)\s*[:：.。,，]|^(?:注|备注)\s|^(?:Notes?|Sources?)\s",
            re.I,
        )
    text = str(content).lstrip()
    return text if _FOOT_LABEL.match(text) else prefix + text


def _range_end(label):
    text = re.sub(r"[\s_\-()（）:：]", "", str(label)).lower()
    if any(k in text for k in ("下限", "下界")) or text in _RANGE_LOW:
        return "low"
    if any(k in text for k in ("上限", "上界")) or text in _RANGE_HIGH:
        return "high"
    return None


def _p_text(p, style="value"):
    """Compact P display: P=0.003 / P<0.001, or significance stars."""
    if isinstance(p, str):
        m = re.fullmatch(r"\s*(?:[Pp]\s*)?([<>=≤≥]?)\s*([0-9]*\.?[0-9]+(?:[eE]-?[0-9]+)?)\s*", p)
        if not m:
            return p.strip(), None
        op, value, raw = m.group(1).replace("≤", "<").replace("≥", ">") or "=", float(m.group(2)), m.group(2)
        raw = "0" + raw if raw.startswith(".") else raw
    else:
        op, value = "=", finite(p, "p")
        raw = "0.001" if value < 0.001 else f"{value:.2g}" if value < 0.1 else f"{value:.2f}"
    if not 0 <= value <= 1:
        raise ValueError("dumbbell p must lie between 0 and 1")
    if op == "=" and value < 0.001:
        op, raw = "<", "0.001"
    if style == "stars":
        significant = op != ">" and (value <= 0.05 if op == "<" else value < 0.05)
        level = value if op == "=" else value - 1e-12
        return ("***" if level < 0.001 else "**" if level < 0.01 else "*") if significant else "ns", value
    return f"P{op}{raw}", value


def make_dumbbell(
    rows,
    series_labels=("Before", "After"),
    *,
    x_unit="",
    x_title=None,
    x_min=None,
    x_max=None,
    title=None,
    subtitle=None,
    note=None,
    source=None,
    multi_mode="auto",
    width=1000,
    height=None,
    palette=None,
    font_family=None,
    show_values=None,
    show_delta=None,
    value_format=None,
    x_ticks=None,
    plot_height=None,
    note_font_size=None,
    delta_label=None,
    p_style="value",
):
    """Rows are ``{label, before, after}``; neither endpoint is an aggregate.

    The supplied row order is retained in the main plot. Values may be
    negative or equal. ``show_values`` and ``show_delta`` default to True
    for at most four rows; pass False to retain the minimal original layout.
    Values retain their data precision; delta is after minus before (percentage
    points when x_unit is %). Explicit dense annotations may need more space.
    Pass full-precision numbers; optional ``value_format=".1f"`` formats text
    only, after computing deltas from the original numbers. ``x_ticks`` supplies
    explicit tick values; otherwise ticks use readable steps inside the unchanged
    domain. ``plot_height`` optionally fixes the row area for aligned separate
    figures; supply equal overall height and enough room for all notes.
    ``note_font_size`` sets the note/source size explicitly. Full text is kept;
    an insufficient explicit height raises rather than truncating or shrinking.
    ``delta_label`` can replace the neutral Δ heading with a short, true metric
    description. It does not change the calculation (after minus before).
    ``palette.series[0]`` colors before and ``[1]`` after; the library never swaps
    them to choose which state is important. Marker radii are fixed per state
    and match the legend, independent of values or endpoint proximity.

    Optional row fields: ``before_lo/before_hi`` and ``after_lo/after_hi`` draw
    CI whiskers on each endpoint; ``n`` is printed under the row label;
    ``delta_ci=(lo, hi)`` prints "+1.73 (1.10–2.37)" in the Δ column;
    ``delta_unit`` suffixes that row's Δ; ``p`` (0.003 or "<0.001") adds a P
    column ("P=0.003"), or stars with ``p_style="stars"`` (legend in the note).
    Range-like series_labels (下限/上限, min/max, lower/upper) are rejected: a
    range is one estimate with lo/hi, i.e. coef_plot rows.

    ``multi_mode="with_ranked_delta"`` adds a ranked-by-delta sub-strip
    below the main dumbbell. The sub-strip shows the same rows sorted
    descending by (after - before), with signed bars and value labels, so
    readers can read both "what each row did" (main) and "who moved most"
    (sub) off one figure. Requires >=3 rows.
    """
    if not rows or len(series_labels) != 2:
        raise ValueError("dumbbell requires rows and exactly two series_labels")
    ends = [_range_end(label) for label in series_labels]
    if set(ends) == {"low", "high"}:
        raise ValueError(
            f"series_labels {tuple(series_labels)!r} are the two ends of a range, not two conditions; "
            "draw it as coef_plot rows=[{'label', 'estimate', 'lo', 'hi'}] instead of a dumbbell"
        )
    if p_style not in ("value", "stars"):
        raise ValueError("p_style must be 'value' or 'stars'")
    series_labels = [tr(label) for label in series_labels]
    normalized = [(str(row["label"]), finite(row["before"], "before"), finite(row["after"], "after")) for row in rows]

    def interval(row, key, value):
        lo, hi = row.get(f"{key}_lo"), row.get(f"{key}_hi")
        if lo is None and hi is None:
            return None
        if lo is None or hi is None:
            raise ValueError(f"{key}_lo and {key}_hi must be given together")
        lo, hi = sorted((finite(lo, f"{key}_lo"), finite(hi, f"{key}_hi")))
        if not lo - 1e-12 <= value <= hi + 1e-12:
            raise ValueError(f"{key} {value:g} lies outside its interval [{lo:g}, {hi:g}]")
        return lo, hi

    cis = [(interval(row, "before", b), interval(row, "after", a)) for row, (_, b, a) in zip(rows, normalized)]
    counts = []
    for row in rows:
        n = row.get("n")
        if n is not None and not isinstance(n, str):
            n = finite(n, "n")
            n = precise_number(n) if not float(n).is_integer() else str(int(n))
        counts.append(n)
    p_cells = [None if row.get("p") is None else _p_text(row["p"], p_style)[0] for row in rows]
    has_p = any(p is not None for p in p_cells)
    for name, value in (("show_values", show_values), ("show_delta", show_delta)):
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"{name} must be True, False or None")
    if delta_label is not None and (not isinstance(delta_label, str) or not delta_label.strip()):
        raise TypeError("delta_label must be a non-empty string or None")
    automatic_values, automatic_delta = show_values is None, show_delta is None and delta_label is None
    show_values = len(rows) <= 4 if show_values is None else show_values
    show_delta = (len(rows) <= 4 or delta_label is not None) if show_delta is None else show_delta
    deltas_decimal = [float(Decimal(str(after)) - Decimal(str(before))) for _, before, after in normalized]
    decimals = max(
        max(0, -Decimal(precise_number(value)).as_tuple().exponent)
        for _, before, after in normalized
        for value in (before, after)
    )
    decimals = decimals if decimals <= 4 else None
    if value_format is not None and not isinstance(value_format, str):
        raise TypeError("value_format must be a numeric format string or None")

    def display(value):
        return format(value, value_format) if value_format is not None else precise_number(value, decimals=decimals)

    width = finite(width, "width")
    if width < 400:
        raise ValueError("dumbbell width must be at least 400")
    if multi_mode not in (None, "single", "off", "auto", "with_ranked_delta"):
        raise ValueError("multi_mode must be single, auto or with_ranked_delta")
    want_ranked = multi_mode == "with_ranked_delta" or (multi_mode == "auto" and len(normalized) >= 6)
    if want_ranked and len(normalized) < 3:
        if multi_mode == "with_ranked_delta":
            raise ValueError("multi_mode 'with_ranked_delta': need >=3 rows (got {})".format(len(normalized)))
        want_ranked = False
    fonts = chart_font_sizes(width, height or width * 0.6, len(rows))
    fs, tick_fs, axis_fs = fonts["group"], fonts["xtick"], fonts["xaxis"]
    legend_fs, foot_fs = fonts["legend"], fonts["foot"]
    if note or source:
        foot_fs = max(foot_fs, width / 45)
    if note_font_size is not None:
        foot_fs = finite(note_font_size, "note_font_size")
        if foot_fs <= 0:
            raise ValueError("note_font_size must be positive")
    left = min(width * 0.35, max(100, max(measure(label, fs) for label, _, _ in normalized) + 50))
    labels = [wrap(label, left - 46, fs) for label, _, _ in normalized]
    value_fs = max(14.0, fs * 0.9)
    sub_fs = max(11.0, value_fs * 0.8)
    n_h = sub_fs * 1.3 if any(n is not None for n in counts) else 0
    row_h = max(44, max(len(lines) for lines in labels) * fs * 1.35 + n_h + 16)
    base_row_h = row_h
    if show_values:
        row_h = max(row_h, value_fs * 0.85 + 27)
    delta_strings = []
    for value, row in zip(deltas_decimal, rows):
        text = display(value)
        text = ("+" if value > 0 and not text.lstrip().startswith(("+", "-")) else "") + text
        delta_strings.append(text + (f" {row['delta_unit']}" if row.get("delta_unit") else ""))
    delta_cis = []
    for row, delta in zip(rows, deltas_decimal):
        ci = row.get("delta_ci")
        if ci is None:
            delta_cis.append(None)
            continue
        if len(ci) != 2:
            raise ValueError("delta_ci must be (lo, hi)")
        lo, hi = sorted(finite(v, "delta_ci") for v in ci)
        if not lo - 1e-9 <= delta <= hi + 1e-9:
            raise ValueError(f"delta {delta:g} lies outside its delta_ci [{lo:g}, {hi:g}]")
        a, b = (display(v).replace("-", "−") for v in (lo, hi))
        delta_cis.append("(" + tr("{a} to {b}", a=a, b=b) + ")" if lo < 0 else f"({a}–{b})")
    show_delta = show_delta or any(delta_cis)
    delta_unit = "pp" if x_unit == "%" else x_unit
    delta_header = delta_label if delta_label is not None else "Δ" + (f" ({delta_unit})" if delta_unit else "")
    p_header = "P"
    p_width = max([measure(p_header, value_fs)] + [measure(p, value_fs) for p in p_cells if p]) + 22 if has_p else 0

    def delta_width_for(stacked):
        cells = [
            measure(d, value_fs)
            if not ci
            else max(measure(d, value_fs), measure(ci, sub_fs))
            if stacked
            else measure(f"{d} {ci}", value_fs)
            for d, ci in zip(delta_strings, delta_cis)
        ]
        return max([measure(delta_header, value_fs), *cells]) + 26 if show_delta else 0

    stacked_ci = False
    delta_width = delta_width_for(False)
    values = [v for _, a, b in normalized for v in (a, b)] + [v for pair in cis for ci in pair if ci for v in ci]
    low, high = min(values), max(values)
    pad = (high - low or max(1, abs(high) * 0.1)) * 0.12
    low = low - pad if x_min is None else finite(x_min, "x_min")
    high = high + pad if x_max is None else finite(x_max, "x_max")
    if low > min(values) or high < max(values) or high <= low:
        raise ValueError("x_min/x_max must be increasing and contain all endpoints")
    tick_values, tick_labels, offset_label = _dumbbell_ticks(low, high, x_ticks)
    right = width - max(38, max(measure(label, tick_fs) for label in tick_labels) / 2 + 10) - delta_width - p_width
    if right - left < 180 and any(delta_cis):
        right += delta_width - delta_width_for(True)
        stacked_ci, delta_width = True, delta_width_for(True)
    if right - left < 180 and show_delta and automatic_delta and not any(delta_cis):
        right += delta_width
        show_delta, delta_width = False, 0
    if right - left < 180:
        raise ValueError("dumbbell annotations need a wider canvas")
    # A number is never split across lines ("0.775" → "0.77" / "5").
    tick_lines = [
        [label] if re.fullmatch(r"[-+−]?[0-9.,eE×^%]+", label) else wrap(label, (right - left) / 5 * 0.9, tick_fs)
        for label in tick_labels
    ]
    from ._chart_layout import axis_caption

    axis = axis_caption(x_title, x_unit, title)
    if offset_label:
        axis = f"{axis} · {offset_label}" if axis else offset_label
    axis_lines = wrap(axis, right - left, axis_fs) if axis else []
    axis_h = 34 + max(len(lines) for lines in tick_lines) * tick_fs * 1.35 + len(axis_lines) * axis_fs * 1.35
    colors = _derive_series_colors(_resolve_palette(palette), 2, mode="distinct")
    legend_rows, legend_h = legend_layout(list(zip(series_labels, colors)), width, legend_fs)
    top = header_height(width, title, subtitle, fonts=fonts) + legend_h + 18
    # Rank sub-strip space (one row per entry + caption + gutter).
    sub_row_h = max(22, fs * 1.4)
    sub_caption_h = legend_fs * 1.6 + 10
    sub_axis_h = tick_fs * 1.6 + 10
    sub_h = sub_caption_h + len(normalized) * sub_row_h + sub_axis_h + 24 if want_ranked else 0
    foot = []
    if has_p and p_style == "stars":
        stars_note = "* P<0.05, ** P<0.01, *** P<0.001; ns P≥0.05"
        note = f"{note}; {stars_note}" if note else stars_note
    for prefix, content in ((tr("Notes. "), note), (tr("Source. "), source)):
        if content:
            foot.extend(wrap(_prefixed(prefix, content), width - 64, foot_fs))
    requested_plot_height = None if plot_height is None else finite(plot_height, "plot_height")
    if requested_plot_height is not None and requested_plot_height <= 0:
        raise ValueError("plot_height must be positive")
    if requested_plot_height is not None and requested_plot_height < len(rows) * row_h:
        if show_values and automatic_values and requested_plot_height >= len(rows) * base_row_h:
            show_values, row_h = False, base_row_h
        else:
            raise ValueError("plot_height is too small for complete row labels and values")
    row_area = requested_plot_height if requested_plot_height is not None else len(rows) * row_h
    minimum = top + row_area + axis_h + sub_h + len(foot) * foot_fs * 1.35
    if height is not None and float(height) < minimum and show_values and automatic_values:
        show_values, row_h = False, base_row_h
        row_area = requested_plot_height if requested_plot_height is not None else len(rows) * row_h
        minimum = top + row_area + axis_h + sub_h + len(foot) * foot_fs * 1.35
    height = minimum if height is None else finite(height, "height")
    if height < minimum:
        raise ValueError(f"dumbbell height must be at least {minimum:g}")
    bottom = (
        top + requested_plot_height
        if requested_plot_height is not None
        else height - axis_h - sub_h - len(foot) * foot_fs * 1.35
    )
    scale = lambda value: left + (value - low) / (high - low) * (right - left)

    def row_center(index):
        height_per_row = (bottom - top) / len(rows)
        row_top = top + index * height_per_row
        center = row_top + height_per_row / 2
        if show_values:
            center = max(center, row_top + value_fs * 0.85 + 16)
        return center

    value_specs = []
    for index, (_, before, after) in enumerate(normalized):
        cy = row_center(index)
        if not show_values:
            value_specs.append([])
            continue
        entries = sorted([(scale(before), "before", before), (scale(after), "after", after)])
        strings = [display(value) for _, _, value in entries]
        widths = [measure(text, value_fs) for text in strings]
        positions = _spread_positions([x for x, _, _ in entries], widths, left + 3, right - 3, gap=8)
        baseline = cy - 13
        value_specs.append(
            [
                (x, source_x, endpoint, value, text, w, baseline)
                for x, (source_x, endpoint, value), text, w in zip(positions, entries, strings, widths)
            ]
        )
    c = Canvas(width, height, palette, font_family)
    draw_header(c, title, subtitle, fonts=fonts)
    for x, y, lines, color, extra in legend_rows:
        is_before = color == colors[0]
        c.circle(
            x + 4,
            top - legend_h + y - 10,
            6.2 if is_before else 4.6,
            "none" if is_before else color,
            f'stroke="{color}" stroke-width="1.8"' if is_before else "",
        )
        c.lines(x + 17, top - legend_h + y - 6, lines, legend_fs, color=c.muted)
    for value, lines in zip(tick_values, tick_lines):
        px = scale(value)
        # Grid segments stop at measured value labels rather than relying on a halo.
        blocked = sorted(
            (baseline - value_fs * 0.85 - 3, baseline + value_fs * 0.25 + 3)
            for specs in value_specs
            for x, _, _, _, _, w, baseline in specs
            if x - w / 2 - 3 <= px <= x + w / 2 + 3
        )
        cursor = top
        for lo, hi in blocked:
            if lo > cursor:
                c.line(px, cursor, px, min(lo, bottom), c.grid, 0.8)
            cursor = max(cursor, hi)
        if cursor < bottom:
            c.line(px, cursor, px, bottom, c.grid, 0.8)
        c.lines(px, bottom + tick_fs + 10, lines, tick_fs, "middle", c.muted)
    p_x, delta_x = width - 32, width - 32 - p_width
    if show_delta:
        c.text(delta_x, top - 12, delta_header, value_fs, "end", c.ink, 600)
    if has_p:
        c.text(p_x, top - 12, p_header, value_fs, "end", c.ink, 600, 'font-style="italic"')
    for index, ((label, before, after), lines) in enumerate(zip(normalized, labels)):
        cy = row_center(index)
        label_y = cy - (len(lines) - 1) * fs * 0.675 + fs * 0.33 - (n_h / 2 if counts[index] is not None else 0)
        c.lines(left - 18, label_y, lines, fs, "end")
        if counts[index] is not None:
            c.text(
                left - 18,
                label_y + (len(lines) - 1) * fs * 1.35 + sub_fs * 1.3,
                f"n = {counts[index]}",
                sub_fs,
                "end",
                c.muted,
                400,
                'data-role="row-n"',
            )
        c.line(
            scale(before),
            cy,
            scale(after),
            cy,
            c.muted,
            2.2,
            f'data-role="comparison" data-before="{before:g}" data-after="{after:g}"',
        )
        both = all(cis[index])
        for lo_hi, color, role, dy in (
            (cis[index][0], colors[0], "before-ci", -3.2 if both else 0),
            (cis[index][1], colors[1], "after-ci", 3.2 if both else 0),
        ):
            if lo_hi:
                x0, x1, y = scale(lo_hi[0]), scale(lo_hi[1]), cy + dy
                c.parts.append(
                    f'<path d="M{x0:.3f},{y:.3f} H{x1:.3f} M{x0:.3f},{y - 3.5:.3f} V{y + 3.5:.3f} '
                    f'M{x1:.3f},{y - 3.5:.3f} V{y + 3.5:.3f}" fill="none" stroke="{color}" stroke-width="1.5" '
                    f'data-role="{role}" data-lo="{lo_hi[0]:g}" data-hi="{lo_hi[1]:g}"/>'
                )
        # Distinct outline/fill identities remain visible even when unequal
        # endpoints project almost to the same pixel. Both centers stay exact.
        c.circle(
            scale(before),
            cy,
            6.2,
            "none",
            f'stroke="{colors[0]}" stroke-width="1.8" data-role="before" data-value="{before:g}"',
        )
        c.circle(scale(after), cy, 4.6, colors[1], f'data-role="after" data-value="{after:g}"')
        for x, source_x, endpoint, value, text, _, baseline in value_specs[index]:
            if abs(x - source_x) > 3:
                c.line(source_x, cy - 7, x, baseline + value_fs * 0.25 + 2, c.grid, 1.1)
            c.text(
                x,
                baseline,
                text,
                value_fs,
                "middle",
                c.ink,
                500,
                f'data-role="endpoint-value" data-endpoint="{endpoint}" data-value="{value:g}"',
            )
        if show_delta:
            ci_text = delta_cis[index]
            if ci_text and stacked_ci:
                c.text(
                    delta_x,
                    cy - 2,
                    delta_strings[index],
                    value_fs,
                    "end",
                    c.ink,
                    600,
                    f'data-role="row-delta" data-value="{deltas_decimal[index]:g}"',
                )
                c.text(delta_x, cy + sub_fs + 1, ci_text, sub_fs, "end", c.muted, 400, 'data-role="row-delta-ci"')
            else:
                text = f"{delta_strings[index]} {ci_text}" if ci_text else delta_strings[index]
                c.text(
                    delta_x,
                    cy + value_fs * 0.33,
                    text,
                    value_fs,
                    "end",
                    c.ink,
                    600,
                    f'data-role="row-delta" data-value="{deltas_decimal[index]:g}"',
                )
        if p_cells[index]:
            c.text(p_x, cy + value_fs * 0.33, p_cells[index], value_fs, "end", c.ink, 400, 'data-role="row-p"')
    if axis_lines:
        c.lines(
            (left + right) / 2,
            bottom + 10 + axis_fs + max(len(lines) for lines in tick_lines) * tick_fs * 1.35,
            axis_lines,
            axis_fs,
            "middle",
            c.muted,
        )
    if want_ranked:
        pal = _resolve_palette(palette)
        pos_color = colors[1]
        neg_color = pal.get("accent", colors[0]) if colors[1] != pal.get("accent") else colors[0]
        deltas = sorted(
            [(label, after - before, before, after) for label, before, after in normalized],
            key=lambda t: t[1],
            reverse=True,
        )
        max_abs = max((abs(d) for _, d, _, _ in deltas), default=1) or 1
        sub_top = bottom + axis_h + 12
        caption = tr("Ranked by Δ ({b} − {a})", b=series_labels[1], a=series_labels[0])
        if x_unit:
            caption += f", in {x_unit}"
        c.lines(32, sub_top + legend_fs * 0.9, [caption], legend_fs, color=c.muted)
        strip_top = sub_top + sub_caption_h
        strip_left = left
        strip_right = right
        strip_mid = (strip_left + strip_right) / 2
        half_width = (strip_right - strip_left) / 2 - 8
        c.line(strip_mid, strip_top, strip_mid, strip_top + len(deltas) * sub_row_h, c.grid, 1.0)
        for i, (label, delta, _before, _after) in enumerate(deltas):
            cy = strip_top + (i + 0.5) * sub_row_h
            bar_len = (abs(delta) / max_abs) * half_width
            bar_color = pos_color if delta >= 0 else neg_color
            if delta >= 0:
                bar_x, bar_w = strip_mid, bar_len
            else:
                bar_x, bar_w = strip_mid - bar_len, bar_len
            c.parts.append(
                f'<rect x="{bar_x:.3f}" y="{cy - sub_row_h * 0.32:.3f}" '
                f'width="{max(1.0, bar_w):.3f}" height="{sub_row_h * 0.64:.3f}" '
                f'fill="{bar_color}" fill-opacity="0.78" '
                f'data-role="ranked-delta" data-label="{label}" data-delta="{delta:g}"/>'
            )
            c.lines(strip_left - 10, cy + fs * 0.33, [label], fs, "end", c.muted)
            # Delta value next to end of bar
            value_text = f"{'+' if delta >= 0 else ''}{delta:.3g}"
            if delta >= 0:
                c.lines(bar_x + bar_w + 6, cy + fs * 0.33, [value_text], fs, "start", pos_color)
            else:
                c.lines(bar_x - 6, cy + fs * 0.33, [value_text], fs, "end", neg_color)
    if foot:
        c.lines(32, height - len(foot) * foot_fs * 1.35 + foot_fs * 0.84 + 2, foot, foot_fs, color=c.muted)
    c.parts.append(
        f'<g data-role="dumbbell-layout" data-domain-low="{low:.17g}" data-domain-high="{high:.17g}" data-plot-top="{top:.6f}" data-plot-bottom="{bottom:.6f}"/>'
    )
    return c.svg()


def _dumbbell_ticks(low, high, supplied=None):
    """Nice ticks inside explicit bounds; neither bounds nor data are changed."""
    span = high - low
    if supplied is not None:
        values = [finite(v, "x_ticks") for v in supplied]
        if len(values) < 2 or any(a >= b for a, b in zip(values, values[1:])) or values[0] < low or values[-1] > high:
            raise ValueError("x_ticks must be increasing distinct values inside x_min/x_max")
    else:
        values, _, _ = nice_axis(low, high, 6)
        values = [v for v in values if low <= v <= high]
        if len(values) < 2:
            values = [low, high]
    offset = 0.0
    if math.isfinite(span) and span > 0:
        center = low + span * 0.5
        if abs(center) / span > 1000:
            step = 10 ** (math.floor(math.log10(span)) + 1)
            offset = round(center / step) * step
    precision_span = abs(span) if math.isfinite(span) and span else max(abs(low), abs(high), 1)
    labels = [_fmt_axis(v - offset, precision_span) for v in values]
    if len(set(labels)) != len(labels):
        labels = [precise_number(v - offset) for v in values]
        if len(set(labels)) != len(labels):
            labels = [format(v - offset, ".17g") for v in values]
    return values, labels, tr("Offset {value}", value=f"{offset:+.17g}") if offset else ""
