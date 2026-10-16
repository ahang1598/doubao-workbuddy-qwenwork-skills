"""统一 API 的甘特图。"""

from __future__ import annotations

import datetime as _dt
import math

from .._common import (
    _derive_series_colors,
    _dispatch_to_svg_lib,
    _estimate_label_width_px,
    _prepend_bg_if_dark,
    _resolve_font,
    _resolve_palette,
    _rgb_tuple,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from .._typography import chart_font_sizes
from ._chart_layout import wrap_lines
from ._shared import (
    notes_source_footer,
    tr,
    is_dark_palette,
    resolve_palette,
    viewbox_fs,
    xesc,
)

VARIANTS = ("default_flat", "progress_split", "critical_path", "gradient_bars", "dot_range")


def _to_num(v, project_start=None):
    """把日期/字符串/数值统一转 float 天数（相对项目起点）。"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, _dt.date):
        if project_start is None:
            return 0.0
        return float((v - project_start).days)
    if isinstance(v, str):
        try:
            d = _dt.date.fromisoformat(v)
            if project_start is None:
                return 0.0
            return float((d - project_start).days)
        except ValueError:
            return float(v)
    raise TypeError(f"gantt: cannot convert {v!r} to number")


def _parse_date(v):
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, str):
        return _dt.date.fromisoformat(v)
    return None


def _normalize_tasks(tasks_in):
    """接受 tuple 或 dict，统一成 [{name, start, end, stream, is_milestone}]。"""
    out = []
    for t in tasks_in:
        if isinstance(t, dict):
            item = dict(t)
        elif isinstance(t, (list, tuple)):
            item = {"name": t[0], "start": t[1], "end": t[2]}
            if len(t) >= 4:
                item["stream"] = t[3]
        else:
            raise TypeError(f"gantt: task must be tuple/dict, got {type(t).__name__}")
        item.setdefault("stream", None)
        item["is_milestone"] = item.get("milestone", False) or item.get("start") == item.get("end")
        out.append(item)
    return out


def _infer_bounds(tasks_norm, milestones, today):
    """如果 tasks 里是 date 字符串，返回 (project_start_date, project_end_date)，否则数值区间。"""

    def _try_date(v):
        try:
            return _parse_date(v)
        except (TypeError, ValueError):
            return None

    all_pts = []
    for t in tasks_norm:
        all_pts.append(t["start"])
        all_pts.append(t["end"])
    for m in milestones or []:
        all_pts.append(m[0])
    if today is not None:
        all_pts.append(today)

    dates = [_try_date(p) for p in all_pts]
    if all(d is not None for d in dates):
        return min(dates), max(dates), True
    if any(d is not None for d in dates):
        raise ValueError("gantt: do not mix calendar dates and numeric positions")
    nums = [_to_num(p) for p in all_pts]
    if not all(math.isfinite(v) for v in nums):
        raise ValueError("gantt: task times must be finite")
    return min(nums), max(nums), False


def _milestone_rows(milestones, x_fn, fs, font, width):
    """Place milestone labels in stacked rows: [(mx, label_x, row, label)], row count."""
    import itertools

    items = sorted(((x_fn(m[0]), str(m[1])) for m in milestones), key=lambda t: t[0])
    if not items:
        return [], 0
    halves = [_estimate_label_width_px(label, fs, bold=True, font_family=font) * 0.55 + 4 for _, label in items]

    def span(mx, half, anchor):
        # centre / box ends just right of the diamond / box starts just left of it
        cx = mx if anchor == 0 else mx - half + 10 if anchor == 1 else mx + half - 10
        cx = min(width - half - 4, max(half + 4, cx))
        return cx, cx - half, cx + half

    def layout(anchors):
        placed, crossings = [], 0
        for (mx, label), half, anchor in zip(items, halves, anchors):
            cx, lo, hi = span(mx, half, anchor)
            row = 0
            while True:
                overlap = any(r == row and not (hi + 8 < plo or lo - 8 > phi) for _, _, r, _, plo, phi in placed)
                cuts_leader = any(r > row and lo - 3 <= pmx <= hi + 3 for pmx, _, r, _, _, _ in placed)
                crossed = row and any(r < row and plo - 3 <= mx <= phi + 3 for _, _, r, _, plo, phi in placed)
                if not overlap and not cuts_leader and not crossed:
                    break
                if row > len(items) + 1:  # nothing clean: accept the overlap-free spot, count it
                    if not overlap:
                        crossings += 1
                        break
                row += 1
            placed.append((mx, cx, row, label, lo, hi))
        rows = max(p[2] for p in placed) + 1
        return (crossings, rows, sum(a != 0 for a in anchors)), placed

    if len(items) <= 7:
        best = min((layout(a) for a in itertools.product((0, 1, 2), repeat=len(items))), key=lambda t: t[0])
    else:
        anchors = []
        for i in range(len(items)):
            anchors.append(min((0, 1, 2), key=lambda a: layout(anchors + [a] + [0] * (len(items) - i - 1))[0]))
        best = layout(anchors)
    placed = best[1]
    return [p[:4] for p in placed], max(p[2] for p in placed) + 1


def _marker_color(pal, used):
    """A saturated palette colour clearly different from every bar colour, so milestones / the today line"""
    import colorsys
    from .._common import _rgb_tuple

    def rgb(c):
        try:
            return _rgb_tuple(c)
        except (ValueError, TypeError):
            return None

    bars = [v for v in map(rgb, used) if v]

    def usable(c):
        v = rgb(c)
        if not v or "," in str(c) and str(c).rstrip(")").split(",")[-1].strip() not in ("1", "1.0", "255"):
            return False  # translucent greys read as gridlines
        h, l, sat = colorsys.rgb_to_hls(*(x / 255 for x in v))
        return sat > 0.35 and 0.2 < l < 0.7 and all(sum((a - b) ** 2 for a, b in zip(v, u)) ** 0.5 > 110 for u in bars)

    for c in [pal.get("accent"), pal.get("secondary"), *(pal.get("series") or [])]:
        if c and usable(c):
            return c
    base = rgb(pal.get("accent")) or (163, 88, 50)
    h, l, sat = colorsys.rgb_to_hls(*(x / 255 for x in base))
    r, g, b = colorsys.hls_to_rgb((h + 0.5) % 1, min(max(l, 0.35), 0.45), max(sat, 0.55))
    return f"rgba({round(r * 255)},{round(g * 255)},{round(b * 255)},1)"


def draw_gantt(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 1100,
    height: float | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    font_family: str | None = None,
) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"gantt: unknown variant {variant!r}. Available: {VARIANTS}")

    tasks_in = list(data.get("tasks", []))
    if not tasks_in:
        raise ValueError("gantt: at least one task required")

    tasks = _normalize_tasks(tasks_in)
    milestones = list(data.get("milestones") or [])
    today = data.get("today")
    critical = set(data.get("critical_indices") or [])
    progress_map = data.get("progress_map") or {}

    # Progress is measured input, never a decorative random split.
    if variant == "progress_split" and not progress_map:
        progress_map = {t["name"]: t["progress"] for t in tasks if "progress" in t}
    if variant == "progress_split" and any(t["name"] not in progress_map for t in tasks if not t["is_milestone"]):
        raise ValueError("gantt: progress_split requires progress for every task")

    # 归一化 progress: 0..1
    def _prog(name):
        v = float(progress_map[name])
        if not math.isfinite(v) or not 0 <= v <= 100:
            raise ValueError("gantt: progress must be in [0,1] or [0,100]")
        if v > 1:
            v = v / 100
        return v

    lo, hi, use_dates = _infer_bounds(tasks, milestones, None)
    convert = _parse_date if use_dates else _to_num
    if any(convert(t["end"]) < convert(t["start"]) for t in tasks):
        raise ValueError("gantt: task end must not precede start")
    if data.get("domain") is not None:
        lower, upper = (convert(v) for v in data["domain"])
        if lower > lo or upper < hi or lower >= upper:
            raise ValueError("gantt: domain must include every task and milestone")
        lo, hi = lower, upper
    if today is not None and not lo <= convert(today) <= hi:
        today = None

    if use_dates:
        total_days = max(1, (hi - lo).days)

        def x_of(v, plot_left, plot_right):
            d = _parse_date(v) if not isinstance(v, _dt.date) else v
            return plot_left + ((d - lo).days / total_days) * (plot_right - plot_left)
    else:
        span = hi - lo or 1

        def x_of(v, plot_left, plot_right):
            return plot_left + ((float(v) - lo) / span) * (plot_right - plot_left)

    pal = resolve_palette(palette)
    INK = pal["ink"]
    ACC = pal["accent"]
    MUT = pal["muted"]
    BG = pal["bg"]
    series = pal.get("series", [ACC, pal["secondary"], INK])
    dark = is_dark_palette(pal)
    label_col = "rgba(240,232,214,1)" if dark else INK

    stream_names = []
    for t in tasks:
        s = t.get("stream")
        if s is not None and s != "" and s not in stream_names:
            stream_names.append(s)

    def _task_color(t, i):
        s = t.get("stream")
        if s is not None and s != "" and s in stream_names:
            return series[stream_names.index(s) % len(series)]
        return series[i % len(series)]

    n = len(tasks)
    if variant == "critical_path":
        bar_colors = [ACC, pal["ink4"]]
    else:
        bar_colors = list(dict.fromkeys(_task_color(t, i) for i, t in enumerate(tasks)))
    MARK = _marker_color(pal, bar_colors)
    W = float(width)
    if height is None:
        row_target = 40 if n <= 8 else (34 if n <= 15 else 28)
        H = max(400.0, 200 + n * row_target)
    else:
        H = float(height)

    ML = min(90.0, max(24.0, W * 0.06))
    MR = min(60.0, max(20.0, W * 0.04))
    plot_left = ML + 200  # 左侧留给任务名
    plot_right = W - MR
    # 顶部预留：milestone label(24) + axis tick label(14) + gap + TODAY(14) 需要独立层级
    plot_top = 170.0 if (title or subtitle) else 100.0
    plot_bot = H - 70.0
    plot_h = plot_bot - plot_top
    row_h = plot_h / n

    # task name / owner 是每行的关键 secondary label，embed 宽 <450 时旧的
    # auto_font_size 会给出 9-11pt，缩到 embed 后不可读。改用 viewbox_fs 让字号
    # 随 viewBox 放大，同时锁 floor=11 保证 secondary 至少 11pt。
    body_font, head_font = _resolve_font(font_family)
    fs_cap = None
    plot_top0 = plot_top
    while True:
        compact = fs_cap is not None
        plot_top = 0.0 if compact else plot_top0
        fs_task = max(11.0, viewbox_fs(W, H, n, role_mult=1.0, floor=11))
        fs_owner = max(11.0, viewbox_fs(W, H, n, role_mult=0.85, floor=11))
        fs_axis = viewbox_fs(W, H, n)
        # Three-row regional plans are commonly placed in a ~490px column; an
        # explicit height must not silently force tiny labels when room exists.
        fs_owner = max(fs_owner, W / 45)
        fs_task = max(fs_task, fs_owner * 1.1)
        fs_axis = max(fs_axis, fs_owner)
        if height is None:
            # Automatic charts remain legible at a 600px column width. Preserve
            # type and allocate more space, rather than shrinking dense task rows.
            fs_owner = max(fs_owner, W / 50)
            fs_task = max(fs_task, fs_owner * 1.1)
            fs_axis = max(fs_axis, fs_owner)

        if fs_cap is not None:
            fs_owner = min(fs_owner, fs_cap)
            fs_task = min(fs_task, fs_cap * 1.1)
            fs_axis = min(fs_axis, fs_cap)
        name_width = max(
            _estimate_label_width_px(str(task["name"]), fs_task * 1.05, font_family=body_font) for task in tasks
        )
        plot_left = ML + min(W * 0.38, max(200.0, name_width + 32))
        header_lines = []
        header_top = 26.0
        for value, size, bold, font in (
            (title, max(24.0, fs_task * 1.3), True, head_font),
            (subtitle, max(12.0, fs_owner), False, body_font),
            (figure_label, max(10.0, fs_owner), True, body_font),
        ):
            if value:
                for line in wrap_lines(value, W - ML - MR, size * (1.05 if bold else 1), font):
                    header_lines.append((line, header_top + size * 0.84, size, bold, font))
                    header_top += size * 1.3
                header_top += 5
        if compact:
            plot_top = max(plot_top, fs_axis * 1.1 + 24)
        fs_today = max(10.0, fs_owner * 0.85)
        ms_rows, n_ms_rows = _milestone_rows(
            milestones, lambda v: x_of(v, plot_left, plot_right), fs_owner, body_font, W
        )
        # tick labels | today label row | diamonds | stacked milestone label rows
        annotation_band = (
            fs_axis * 1.1
            + 14
            + (fs_today * 1.25 + 6 if today is not None else 0)
            + (22 + n_ms_rows * fs_owner * 1.3 + 4 if milestones else 0)
            + 8
        )
        if header_lines:
            plot_top = max(plot_top, header_top + (annotation_band if milestones or today is not None else 38))
        elif milestones or today is not None:
            plot_top = max(plot_top, annotation_band)
        note_lines = wrap_lines("Note. " + str(note), W - ML - MR, fs_owner, body_font) if note else []
        has_legend = variant == "critical_path" and critical and data.get("show_legend", True)
        footer_space = max(
            40.0 if compact else 70.0,
            24 + (fs_owner * 1.3 + 10 if has_legend else 0) + len(note_lines) * fs_owner * 1.3 + 12,
        )
        plot_bot = H - footer_space
        row_h = (plot_bot - plot_top) / n
        task_label_blocks = []
        for task in tasks:
            names = wrap_lines(str(task["name"]), plot_left - ML - 24, fs_task * 1.05, body_font)
            streams = (
                wrap_lines(str(task["stream"]), plot_left - ML - 24, fs_owner, body_font)
                if task.get("stream") is not None and task.get("stream") != ""
                else []
            )
            name_h = (len(names) - 1) * fs_task * 1.25 + fs_task * 1.1
            stream_h = max(0, len(streams) - 1) * fs_owner * 1.25 + (fs_owner * 1.1 if streams else 0)
            text_h = name_h + (4 + stream_h if streams else 0)
            task_label_blocks.append((names, streams, name_h, text_h))
        if height is None:
            # Preserve the measured type size and grow the automatic canvas to fit
            # complete names and stream labels. Explicit heights remain a constraint.
            needed_row = max(block[3] for block in task_label_blocks) + 8
            H = max(H, math.ceil(plot_top + footer_space + n * needed_row))
            plot_bot = H - footer_space
            plot_h = plot_bot - plot_top
            row_h = plot_h / n

        fits = all(block[3] <= row_h - 4 for block in task_label_blocks)
        if height is None or fits or fs_owner <= 10:
            break
        # Explicit embed canvas: shrink type toward the 10px floor before giving up.
        fs_cap = max(10.0, round(fs_owner * 0.92, 1))

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{BG}"/>')

    # Measured header uses the same font sizes as its reserved space.
    for line, baseline, size, bold, font in header_lines:
        parts.append(
            f'<text x="{ML:.1f}" y="{baseline:.1f}" font-family="{font}" font-size="{size:.1f}" '
            f'font-weight="{600 if bold else 400}" fill="{label_col if bold else MUT}">{xesc(line)}</text>'
        )

    if use_dates:
        _draw_date_axis(
            parts,
            lo,
            hi,
            plot_left,
            plot_right,
            plot_top,
            plot_bot,
            pal,
            body_font,
            fs_axis,
            dark,
            hide_weekend=(variant == "dot_range"),
        )
    else:
        _draw_numeric_axis(
            parts,
            lo,
            hi,
            plot_left,
            plot_right,
            plot_top,
            plot_bot,
            pal,
            body_font,
            fs_axis,
            unit=data.get("time_unit") or "",
        )

    tick_top = plot_top - 8 - fs_axis * 1.1
    today_baseline = tick_top - 6
    diamond_bot = tick_top - 6 - (fs_today * 1.25 + 6 if today is not None else 0)
    if today is not None:
        tx = x_of(today, plot_left, plot_right)
        parts.append(
            f'<line x1="{tx:.1f}" y1="{plot_top:.1f}" x2="{tx:.1f}" y2="{plot_bot + 6:.1f}" '
            f'stroke="{MARK}" stroke-width="1.6" stroke-dasharray="4 3" data-role="today-marker" data-color="{MARK}"/>'
        )
        today_text = tr("TODAY")
        today_half = _estimate_label_width_px(today_text, fs_today, bold=True, font_family=body_font) / 2 + 2
        parts.append(
            f'<text x="{min(W - today_half, max(today_half, tx)):.1f}" y="{today_baseline:.1f}" text-anchor="middle" '
            f'font-family="{body_font}" font-size="{fs_today:.1f}" font-weight="700" '
            f'fill="{MARK}">{_xesc(today_text)}</text>'
        )

    for i, t in enumerate(tasks):
        y_row = plot_top + i * row_h
        y_bar_h = row_h * 0.55
        y_bar = y_row + (row_h - y_bar_h) / 2
        col = _task_color(t, i)

        xL = x_of(t["start"], plot_left, plot_right)
        xR = x_of(t["end"], plot_left, plot_right)
        w = max(2.0, xR - xL)

        # Measure the complete name and optional stream as one centered block.
        # Fixed baselines only 11px apart overlapped once task fonts grew.
        name = str(t["name"])
        name_lines, stream_lines, name_height, label_height = task_label_blocks[i]
        if label_height > row_h - 4:
            raise ValueError(f"gantt: full label for {name!r} needs a taller canvas")
        label_top = y_row + (row_h - label_height) / 2
        for line_index, line in enumerate(name_lines):
            parts.append(
                f'<text x="{ML + 8:.1f}" y="{label_top + fs_task * 0.84 + line_index * fs_task * 1.25:.1f}" '
                f'font-family="{body_font}" font-size="{fs_task}" font-weight="600" '
                f'fill="{label_col}">{xesc(line)}</text>'
            )
        for line_index, line in enumerate(stream_lines):
            parts.append(
                f'<text x="{ML + 8:.1f}" y="{label_top + name_height + 4 + fs_owner * 0.84 + line_index * fs_owner * 1.25:.1f}" '
                f'font-family="{body_font}" font-size="{fs_owner}" fill="{MUT}">{xesc(line)}</text>'
            )

        if t["is_milestone"]:
            cx = xL
            cy = y_row + row_h / 2
            parts.append(
                f'<polygon points="{cx:.1f},{cy - 8:.1f} {cx + 8:.1f},{cy:.1f} '
                f'{cx:.1f},{cy + 8:.1f} {cx - 8:.1f},{cy:.1f}" '
                f'fill="{MARK}" stroke="{INK}" stroke-width="1.2"/>'
            )
            continue

        if variant == "default_flat":
            parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" height="{y_bar_h:.1f}" fill="{col}"/>')
        elif variant == "progress_split":
            prog = _prog(t["name"])
            done_w = w * prog
            parts.append(
                f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" '
                f'height="{y_bar_h:.1f}" fill="{_rgba_with_alpha(col, 0.18)}" '
                f'stroke="{col}" stroke-width="1.3" data-role="task-progress" data-progress="{prog * 100:g}"/>'
            )
            if done_w > 0:
                parts.append(
                    f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{done_w:.1f}" height="{y_bar_h:.1f}" fill="{col}"/>'
                )
            progress_text = f"{prog * 100:g}%"
            text_width = _estimate_label_width_px(progress_text, fs_owner, bold=True, font_family=body_font)
            inside = done_w >= text_width + 12 and y_bar_h >= fs_owner + 6
            text_x = xL + done_w - 5 if inside else min(xR + 8, W - text_width - 8)
            text_color = (BG or "#FFFFFF") if inside else INK
            parts.append(
                f'<text x="{text_x:.1f}" y="{y_bar + y_bar_h / 2 + fs_owner * 0.3:.1f}" '
                f'text-anchor="{"end" if inside else "start"}" font-family="{body_font}" font-size="{fs_owner:.1f}" '
                f'font-weight="700" fill="{text_color}">{progress_text}</text>'
            )
        elif variant == "critical_path":
            is_crit = i in critical
            fill = ACC if is_crit else pal["ink4"]
            parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" height="{y_bar_h:.1f}" fill="{fill}"/>')
            if is_crit:
                parts.append(
                    f'<text x="{xR + 6:.1f}" y="{y_bar + y_bar_h / 2 + fs_owner * 0.3:.1f}" '
                    f'font-family="{body_font}" font-size="{fs_owner:.1f}" font-weight="700" '
                    f'fill="{ACC}">{_xesc(tr("CP"))}</text>'
                )
        elif variant == "gradient_bars":
            gid = f"gantt_g_{i}"
            top = _rgba_with_alpha(col, 1.0)
            bot = _rgba_with_alpha(col, 0.4)
            parts.append(
                f'<defs><linearGradient id="{gid}" x1="{xL:.1f}" y1="0" '
                f'x2="{xR:.1f}" y2="0" gradientUnits="userSpaceOnUse">'
                f'<stop offset="0%" stop-color="{top}"/>'
                f'<stop offset="100%" stop-color="{bot}"/></linearGradient></defs>'
            )
            parts.append(
                f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" height="{y_bar_h:.1f}" fill="url(#{gid})"/>'
            )
        elif variant == "dot_range":
            cy = y_row + row_h / 2
            parts.append(
                f'<line x1="{xL:.1f}" y1="{cy:.1f}" x2="{xR:.1f}" y2="{cy:.1f}" '
                f'stroke="{col}" stroke-width="2.4" stroke-linecap="round"/>'
            )
            parts.append(f'<circle cx="{xL:.1f}" cy="{cy:.1f}" r="5.5" fill="{BG}" stroke="{col}" stroke-width="2"/>')
            parts.append(f'<circle cx="{xR:.1f}" cy="{cy:.1f}" r="5.5" fill="{col}" stroke="{col}" stroke-width="2"/>')
            slbl = _fmt_pos(t["start"], use_dates)
            elbl = _fmt_pos(t["end"], use_dates)
            parts.append(
                f'<text x="{xL - 6:.1f}" y="{cy - 8 - fs_owner * 0.25:.1f}" text-anchor="end" '
                f'font-family="{body_font}" font-size="{fs_owner:.1f}" fill="{MUT}">{xesc(slbl)}</text>'
            )
            parts.append(
                f'<text x="{xR + 6:.1f}" y="{cy - 8 - fs_owner * 0.25:.1f}" text-anchor="start" '
                f'font-family="{body_font}" font-size="{fs_owner:.1f}" fill="{MUT}">{xesc(elbl)}</text>'
            )

    # user-provided milestones: diamonds in one row above the ticks / today label; labels stacked into
    # non-overlapping rows (_milestone_rows), lifted labels get a thin leader down to their diamond.
    diamond_top = diamond_bot - 14
    for mx, label_x, row, lbl in ms_rows:
        parts.append(
            f'<polygon points="{mx:.1f},{diamond_top:.1f} {mx + 6:.1f},{diamond_bot - 7:.1f} '
            f'{mx:.1f},{diamond_bot:.1f} {mx - 6:.1f},{diamond_bot - 7:.1f}" '
            f'fill="{MARK}" stroke="{BG}" stroke-width="1.2" data-role="milestone"/>'
        )
        if row:
            parts.append(
                f'<line x1="{mx:.1f}" y1="{diamond_top - 6 - row * fs_owner * 1.3 + 3:.1f}" x2="{mx:.1f}" '
                f'y2="{diamond_top - 1:.1f}" stroke="{MARK}" stroke-width="0.8"/>'
            )
    for mx, label_x, row, lbl in ms_rows:
        parts.append(
            f'<text x="{label_x:.1f}" y="{diamond_top - 6 - row * fs_owner * 1.3:.1f}" text-anchor="middle" '
            f'font-family="{body_font}" font-size="{fs_owner}" font-weight="700" '
            f'stroke="{BG}" stroke-width="3" stroke-linejoin="round" paint-order="stroke" '
            f'fill="{MARK}">{xesc(str(lbl))}</text>'
        )

    footer_y = plot_bot + 24
    if has_legend:
        legend = [(tr("Critical path"), ACC), (tr("Non-critical"), pal["ink4"])]
        symbol = fs_owner * 0.65
        widths = [symbol + 10 + _estimate_label_width_px(label, fs_owner, font_family=body_font) for label, _ in legend]
        lx = max(ML, plot_right - sum(widths) - 26)
        for (label, color), item_width in zip(legend, widths):
            parts.append(
                f'<rect x="{lx:.1f}" y="{footer_y:.1f}" width="{symbol:.1f}" height="{symbol:.1f}" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{lx + symbol + 10:.1f}" y="{footer_y + fs_owner * 0.75:.1f}" font-family="{body_font}" '
                f'font-size="{fs_owner:.1f}" fill="{label_col}">{label}</text>'
            )
            lx += item_width + 26
        footer_y += fs_owner * 1.3 + 10
    for line in note_lines:
        parts.append(
            f'<text x="{ML:.1f}" y="{footer_y + fs_owner * 0.84:.1f}" font-family="{body_font}" '
            f'font-size="{fs_owner:.1f}" fill="{MUT}">{xesc(line)}</text>'
        )
        footer_y += fs_owner * 1.3

    parts.append("</svg>")
    return "".join(parts)


def _draw_date_axis(
    parts, lo, hi, plot_left, plot_right, plot_top, plot_bot, pal, body_font, fs, dark, hide_weekend=False
):
    total = max(1, (hi - lo).days)
    if total > 180:
        # Long programmes: month or year ticks labelled with the year, not a weekly grid of "%b %d".
        months = 12 if total > 3 * 365 else 6 if total > 2 * 365 else 3 if total > 365 else 1
        label_w = _estimate_label_width_px("2026-08", fs, font_family=body_font) + fs
        while months < 12 and (plot_right - plot_left) / max(1, total / 30.4 / months) < label_w:
            months = {1: 3, 3: 6, 6: 12}[months]
        y, m = lo.year, lo.month
        if lo.day != 1:
            m += 1
        while (m - 1) % months:
            m += 1
        y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
        span_years = max(1, round(total / 365 / max(1, (plot_right - plot_left) / label_w)))
        while True:
            d = _dt.date(y, m, 1)
            if d > hi:
                break
            gx = plot_left + ((d - lo).days / total) * (plot_right - plot_left)
            parts.append(
                f'<line x1="{gx:.1f}" y1="{plot_top:.1f}" x2="{gx:.1f}" y2="{plot_bot:.1f}" '
                f'stroke="{pal["ink1"]}" stroke-width="0.6"/>'
            )
            if months < 12 or (y - lo.year) % span_years == 0:
                text = str(y) if months == 12 else f"{y}-{m:02d}"
                parts.append(
                    f'<text x="{gx:.1f}" y="{plot_top - 8:.1f}" text-anchor="middle" '
                    f'font-family="{body_font}" font-size="{fs}" fill="{pal["muted"]}">{text}</text>'
                )
            m += months
            y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
        return
    step = 1
    if total > 60:
        step = 7
    elif total > 30:
        step = 3

    # 先画 weekend 高亮：逐日扫描 Sat/Sun，与 tick step 无关
    # step==7 时（>60 天）跳过 weekend 带，视觉太密
    if not hide_weekend and step < 7:
        weekend_fill = _rgba_with_alpha(pal["ink"], 0.06)
        d = lo
        while d <= hi:
            if d.weekday() >= 5:
                gx = plot_left + ((d - lo).days / total) * (plot_right - plot_left)
                gx2 = min(plot_right, plot_left + ((d - lo).days + 1) / total * (plot_right - plot_left))
                if gx2 > gx:
                    parts.append(
                        f'<rect x="{gx:.1f}" y="{plot_top:.1f}" width="{gx2 - gx:.1f}" '
                        f'height="{plot_bot - plot_top:.1f}" fill="{weekend_fill}"/>'
                    )
            d = d + _dt.timedelta(days=1)

    # 先算出会被标注的 tick 总数，决定 label decimation。
    # 密度控制阈值（label 数量）：>20 → 每 4 个 tick 一个 label，>12 → 每 2 个，
    # 否则全画。避免 dot_range 长时段（>7 月 / >25 周）生成 30+ 个 %b %d bbox 撞在一起。
    label_positions = []
    d = lo
    idx = 0
    while d <= hi:
        if d.weekday() == 0 or step >= 7:
            label_positions.append(idx)
        d = d + _dt.timedelta(days=step)
        idx += 1
    n_labels = len(label_positions)
    if n_labels > 20:
        label_stride = 4
    elif n_labels > 12:
        label_stride = 2
    else:
        label_stride = 1
    date_width = _estimate_label_width_px("September 28", fs, font_family=body_font)
    max_labels = max(1, int((plot_right - plot_left) / (date_width + fs)))
    label_stride = max(label_stride, math.ceil(n_labels / max_labels))
    keep_labels = set(label_positions[::label_stride]) if label_stride > 1 else set(label_positions)

    d = lo
    idx = 0
    while d <= hi:
        gx = plot_left + ((d - lo).days / total) * (plot_right - plot_left)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_top:.1f}" x2="{gx:.1f}" y2="{plot_bot:.1f}" '
            f'stroke="{pal["ink1"]}" stroke-width="0.6"/>'
        )
        if (d.weekday() == 0 or step >= 7) and idx in keep_labels:
            parts.append(
                f'<text x="{gx:.1f}" y="{plot_top - 8:.1f}" text-anchor="middle" '
                f'font-family="{body_font}" font-size="{fs}" fill="{pal["muted"]}">'
                f"{d.strftime('%b %d')}</text>"
            )
        d = d + _dt.timedelta(days=step)
        idx += 1


def _draw_numeric_axis(parts, lo, hi, plot_left, plot_right, plot_top, plot_bot, pal, body_font, fs, unit=""):
    ticks = _nice_ticks_num(lo, hi, 6)
    span = hi - lo or 1
    for t in ticks:
        gx = plot_left + ((t - lo) / span) * (plot_right - plot_left)
        parts.append(
            f'<line x1="{gx:.1f}" y1="{plot_top:.1f}" x2="{gx:.1f}" y2="{plot_bot:.1f}" '
            f'stroke="{pal["ink1"]}" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{gx:.1f}" y="{plot_top - 8:.1f}" text-anchor="middle" '
            f'font-family="{body_font}" font-size="{fs}" fill="{pal["muted"]}">'
            f"{_num_fmt(t)}{(' ' + xesc(unit)) if unit and t == ticks[-1] else ''}</text>"
        )


def _nice_ticks_num(lo, hi, count):
    span = hi - lo
    if span <= 0:
        return [lo]
    step = span / count
    exp = 10 ** math.floor(math.log10(step))
    frac = step / exp
    if frac < 1.5:
        step = 1 * exp
    elif frac < 3:
        step = 2 * exp
    elif frac < 7:
        step = 5 * exp
    else:
        step = 10 * exp
    start = math.ceil(lo / step) * step
    out = []
    v = start
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


def _num_fmt(v):
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v - round(v)) < 1e-9:
        return f"{round(v)}"
    return f"{v:g}"


def _fmt_pos(v, use_dates):
    if use_dates:
        d = _parse_date(v)
        if d:
            return d.strftime("%b %d")
    return _num_fmt(float(v)) if isinstance(v, (int, float)) else str(v)


def make_gantt(
    tasks,
    weeks: int | None = None,
    critical_index=None,
    milestones=None,
    project_start=None,
    project_end=None,
    today=None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_kpi: bool = True,
    show_legend: bool = True,
    time_unit: str = "",
    width: float = 1620,
    height: float | None = None,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """
    甘特图 · dandelion academic 风格。

    tasks: 支持两种格式（自动识别）：
    A) **新格式（推荐）**：list of dict：
       {"stream": "Infrastructure", "name": "Cloud landing zone",
        "owner": "P. Rossi", "start": "2026-08-03", "end": "2026-08-28",
        "progress": 95, "status": "on-track", "milestone": False}
       字段：
       - stream: workstream 分组名（相同 stream 会分到同一组，可选，缺省全部一组）
       - name: 任务名（必需）
       - owner: 负责人（可选）
       - start / end: 日期字符串 "YYYY-MM-DD" 或 datetime.date（必需）
       - progress: 0-100 完成度（可选，缺省显示未报告）
       - status: "done"/"on-track"/"at-risk"/"delayed"（可选，缺省显示未报告）
       - milestone: True/False（可选，milestone=True 时用菱形代替条）
    B) **老格式（兼容）**：list of tuple `(name, start_week, end_week, stream?)`
       + 可选第 4 项仅是工作流/分组标签（含数字 0/1），不是关键路径布尔值；关键路径只由 critical_index 指定
       + weeks=int 项目总周数
       + critical_index=int 关键路径任务索引（高亮）
       + milestones=[(week, label), ...]

    project_start / project_end: 项目起止日期（新格式时自动从 tasks 推断）
    today: 今日日期，画 TODAY 竖虚线（tuple 格式用 palette accent 色，chart_slide 会提示实际颜色）；dict 格式缺省用 datetime.date.today()

    title/subtitle/figure_label/note/source: 学术风顶/底文字
    show_kpi: 顶部 4 张 KPI 卡片（OVERALL PROGRESS / COMPLETED / ON TRACK / AT RISK）
    show_legend: 底部图例条
    time_unit: 数值时间轴的单位（"h"、"d"、"周"），标在最后一个刻度后；阶段 / 检测窗口 / 时程区间用 tuple
       (名称, 起, 止, 分组) 即可，如 ("cTnI", 3, 240, "心肌损伤标志物")。

    palette 支持 stream_colors/status_colors 覆盖。
    """
    if not _variant_is_classic("gantt", variant):
        tasks = list(tasks)
        if not tasks:
            raise ValueError("gantt: at least one task required")
        norm = _normalize_tasks(tasks)
        lower, upper, use_dates = _infer_bounds(norm, milestones, None)
        _data = {
            "tasks": tasks,
            "milestones": milestones or [],
            "critical_indices": ([critical_index] if isinstance(critical_index, int) else list(critical_index or [])),
            "today": today,
            "show_legend": show_legend,
            "time_unit": time_unit,
        }
        if weeks is not None:
            if use_dates:
                raise ValueError("gantt: weeks requires numeric task positions")
            _data["domain"] = (0, weeks)
        if project_start is not None or project_end is not None:
            if not use_dates:
                raise ValueError("gantt: calendar bounds require calendar task dates")
            _data["domain"] = (
                lower if project_start is None else project_start,
                upper if project_end is None else project_end,
            )
        # Public task progress is always percentage units. The internal draw
        # adapter also accepts fractional maps, so convert explicitly once.
        progress_map = {}
        for t in norm:
            if t.get("progress") is not None:
                value = float(t["progress"])
                if not math.isfinite(value) or not 0 <= value <= 100:
                    raise ValueError("gantt: progress must be finite and in [0,100]")
                progress_map[t["name"]] = value / 100
        if progress_map:
            _data["progress_map"] = progress_map
        return _dispatch_to_svg_lib(
            "gantt",
            variant,
            _data,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            palette=palette,
            font_family=font_family,
            width=width,
            height=height,
            note=" · ".join(str(v) for v in (note, source) if v) or None,
        )

    import datetime as _dt

    if not tasks:
        raise ValueError("gantt: at least one task required")

    if milestones and all(
        isinstance(t, dict) and not any(t.get(k) is not None for k in ("progress", "status", "owner")) for t in tasks
    ):
        # A plain dict timeline with milestones (trial programmes, regulatory history) is a timeline, not a
        # status dashboard: draw it like the tuple form so milestones=, today= and multi-year axes are honoured.
        tasks = [(t["name"], t["start"], t["end"], t.get("stream") or "") for t in tasks]
    if isinstance(tasks[0], (list, tuple)):
        if (project_start is not None or project_end is not None) and not all(
            isinstance(t[1], (str, _dt.date)) for t in tasks
        ):
            raise ValueError("gantt: numeric weeks cannot be combined with calendar date bounds")
        data = {
            "tasks": list(tasks),
            "milestones": milestones or [],
            "today": today,
            "critical_indices": [critical_index] if critical_index is not None else [],
            "show_legend": show_legend,
            "time_unit": time_unit,
        }
        if weeks is not None:
            data["domain"] = (0, weeks)
        if project_start is not None or project_end is not None:
            lower, upper, _ = _infer_bounds(_normalize_tasks(tasks), milestones, None)
            data["domain"] = (
                lower if project_start is None else project_start,
                upper if project_end is None else project_end,
            )
        return draw_gantt(
            data,
            variant="critical_path" if critical_index is not None else "default_flat",
            palette=palette,
            width=width,
            height=height,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=" · ".join(str(v) for v in (note, source) if v) or None,
            font_family=font_family,
        )

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK4, _ACC = (
        _pal["ink"],
        _pal["ink4"],
        _pal["accent"],
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(247,240,226,1)"
    PANEL = _pal.get("panel", _rgba_with_alpha(_INK, 0.04) if not c_bg else _rgba_with_alpha(_INK, 0.08))

    # 状态色（保持金融印刷风固定色，独立于 palette）
    STATUS_COLORS = {
        "done": _pal.get("gantt_done_color", "rgba(16,106,82,1)"),
        "on-track": _pal.get("gantt_ontrack_color", "rgba(60,105,148,1)"),
        "at-risk": _pal.get("gantt_atrisk_color", "rgba(194,145,60,1)"),
        "delayed": _pal.get("gantt_delayed_color", "rgba(170,60,70,1)"),
    }

    def _to_date(v):
        if isinstance(v, _dt.date):
            return v
        if isinstance(v, str):
            return _dt.date.fromisoformat(v)
        raise ValueError(f"gantt: date must be str 'YYYY-MM-DD' or date, got {v!r}")

    norm_tasks = []
    for t in tasks:
        if not isinstance(t, dict):
            raise TypeError(f"gantt: new API expects dict tasks, got {type(t)}")
        progress = t.get("progress")
        if progress is not None:
            progress = float(progress)
            if not math.isfinite(progress) or not 0 <= progress <= 100:
                raise ValueError("gantt: progress must be finite and in [0,100]")
        if t.get("status") is not None and t["status"] not in STATUS_COLORS:
            raise ValueError("gantt: unknown reported status")
        norm_tasks.append(
            {
                "stream": t.get("stream", "Tasks"),
                "name": str(t.get("name", "")),
                "owner": t.get("owner"),
                "start": _to_date(t["start"]),
                "end": _to_date(t["end"]),
                "progress": progress,
                "status": t.get("status"),
                "milestone": bool(t.get("milestone", False)),
                "_highlight": False,
            }
        )
    proj_start = project_start and _to_date(project_start) or min(t["start"] for t in norm_tasks)
    proj_end = project_end and _to_date(project_end) or max(t["end"] for t in norm_tasks)
    if any(t["end"] < t["start"] for t in norm_tasks):
        raise ValueError("gantt: task end must not precede start")
    if proj_end < proj_start or any(t["start"] < proj_start or t["end"] > proj_end for t in norm_tasks):
        raise ValueError("gantt: project bounds must include all tasks")

    if today is None:
        today = _dt.datetime.now().astimezone().date()
    else:
        today = _to_date(today) if not isinstance(today, _dt.date) else today

    # 派生 workstream 色（按 palette.series 或 accent 派生）
    stream_names = []
    for t in norm_tasks:
        if t["stream"] not in stream_names:
            stream_names.append(t["stream"])
    stream_series = _derive_series_colors(_pal, len(stream_names), mode="distinct")
    STREAM_COLORS = _pal.get("gantt_stream_colors")
    if STREAM_COLORS is None:
        STREAM_COLORS = {name: stream_series[i] for i, name in enumerate(stream_names)}
    else:
        for i, name in enumerate(stream_names):
            if name not in STREAM_COLORS:
                STREAM_COLORS[name] = stream_series[i]

    n_tasks = len(norm_tasks)
    reported_progress = [t["progress"] for t in norm_tasks if t["progress"] is not None]
    overall_progress = sum(reported_progress) / len(reported_progress) if reported_progress else None
    reported_status = sum(t["status"] is not None for t in norm_tasks)
    n_done = sum(1 for t in norm_tasks if t["status"] == "done")
    n_on_track = sum(1 for t in norm_tasks if t["status"] == "on-track")
    n_at_risk = sum(1 for t in norm_tasks if t["status"] == "at-risk")
    total_days = (proj_end - proj_start).days + 1
    days_elapsed = max(0, min(total_days, (today - proj_start).days))
    schedule_pct = days_elapsed / total_days * 100

    MARGIN_L = 90
    MARGIN_R = 90
    MARGIN_T = 320 if show_kpi else 215
    MARGIN_B = 130 if (note or source or show_legend) else 60

    LEFT_COL_W = 380
    RIGHT_COL_W = 140
    plot_x = MARGIN_L + LEFT_COL_W

    # 双重自适应：viewBox 尺寸 + 数据规模（n = tasks 数）。
    # gantt 高度由 tasks 决定（下方 height 计算），所以 base_fs 只按宽度算一档基准；
    # 之后先按 tasks 数分档，再乘各类目倍数。
    # slide 里排 3 张 SVG 缩到 400px 宽也要读得清。
    _n_tasks_fs = n_tasks
    # 高度在下面按 tasks 算；这里用 width + 800 做保守下界当"最小视口"估算 base_fs
    _base_fs = min(float(width), 820.0) * 0.02  # width=1620 → 16.4
    if _n_tasks_fs <= 4:
        _fs_data = _base_fs * 1.4
    elif _n_tasks_fs <= 8:
        _fs_data = _base_fs * 1.0
    elif _n_tasks_fs <= 15:
        _fs_data = _base_fs * 0.8
    else:
        _fs_data = max(_base_fs * 0.6, 10)

    fs_title = round(min(34.0, max(20.0, _base_fs * 1.6)), 1)
    fs_subtitle = round(min(16.0, max(10.0, _base_fs * 0.75)), 1)
    fs_figure = round(min(13.0, max(9.0, _base_fs * 0.62)), 1)
    # KPI 大数字：base_fs * 3.0（原来就是大数字，保持）
    fs_kpi_hdr = round(min(14.0, max(10.0, _base_fs * 0.65)), 1)
    fs_kpi_big = round(min(50.0, max(24.0, _base_fs * 3.0)), 1)
    fs_kpi_sub = round(min(14.0, max(10.0, _base_fs * 0.65)), 1)
    fs_head = round(min(14.0, max(10.0, _base_fs * 0.7)), 1)  # 表头
    fs_group = round(min(17.0, max(11.0, _fs_data * 0.95)), 1)  # group header
    fs_group_sub = round(min(14.0, max(10.0, _fs_data * 0.8)), 1)
    fonts = chart_font_sizes(width, height or 800, n_tasks)
    fs_task = round(fonts["label"], 1)  # 任务名
    fs_task_sub = round(min(14.0, max(10.0, _fs_data * 0.8)), 1)  # 任务日期/owner
    fs_bar_txt = round(min(13.0, max(9.0, _fs_data * 0.7)), 1)
    fs_bar_lbl = round(min(14.0, max(10.0, _fs_data * 0.8)), 1)
    fs_status = round(min(14.0, max(10.0, _fs_data * 0.8)), 1)
    # milestone label 略小（base_fs * 0.85）
    fs_ms_lbl = round(min(15.0, max(10.0, _base_fs * 0.85)), 1)
    fs_x_tick = round(fonts["xtick"], 1)
    fs_legend = round(min(14.0, max(10.0, _base_fs * 0.7)), 1)
    fs_foot = round(min(14.0, max(10.0, _base_fs * 0.7)), 1)
    plot_y = MARGIN_T
    plot_w = width - MARGIN_L - MARGIN_R - LEFT_COL_W - RIGHT_COL_W
    ROW_H = max(40, fs_task * 1.4 + fs_task_sub * 1.4 + 14)
    GROUP_HEADER_H = 48

    prev_stream = None
    task_y_offset = []
    cur_y = 0
    for i, t in enumerate(norm_tasks):
        if t["stream"] != prev_stream:
            cur_y += GROUP_HEADER_H
            prev_stream = t["stream"]
        task_y_offset.append(cur_y)
        cur_y += ROW_H
    plot_h = cur_y

    # 画布高度自适应：任务少 → 画布矮，任务多 → 画布高
    # 用户显式传 height 时以用户为准，否则按 MARGIN_T + plot_h + MARGIN_B 算
    if height is None:
        height = MARGIN_T + plot_h + MARGIN_B

    def date_to_x(dt):
        frac = (dt - proj_start).days / max(total_days, 1)
        return plot_x + frac * plot_w

    parts = []
    if c_bg:
        parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')

    if title:
        parts.append(
            f'<text x="{MARGIN_L}" y="52" '
            f'font-family="{_head_font}" '
            f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
            f"{_xesc(title)}</text>"
        )
    if subtitle:
        parts.append(
            f'<text x="{MARGIN_L}" y="76" '
            f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
            f'letter-spacing=".16em">{_xesc(subtitle)}</text>'
        )
        parts.append(
            f'<line x1="{MARGIN_L}" y1="92" x2="{width - MARGIN_R}" y2="92" stroke="{_INK}" stroke-width="0.8"/>'
        )
    if figure_label:
        parts.append(
            f'<text x="{MARGIN_L}" y="112" font-family="{_body_font}" font-size="{fs_figure}" '
            f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>'
        )
        lbl_w = max(72, len(figure_label) * 8 + 20)
        parts.append(
            f'<text x="{MARGIN_L + lbl_w}" y="112" font-family="{_body_font}" font-size="{fs_figure}" '
            f'fill="{c_muted}" letter-spacing=".04em">'
            f"{_xesc(tr('Gantt · {n} tasks · {start} → {end}', n=n_tasks, start=proj_start.isoformat(), end=proj_end.isoformat()))}</text>"
        )

    if show_kpi:
        kpis = [
            (
                tr("REPORTED PROGRESS"),
                f"{overall_progress:g}%" if overall_progress is not None else "—",
                tr("{k}/{n} tasks reported", k=len(reported_progress), n=n_tasks),
                STATUS_COLORS["on-track"],
            ),
            (
                tr("COMPLETED"),
                str(n_done) if reported_status else "—",
                tr("{k}/{n} statuses reported", k=reported_status, n=n_tasks),
                STATUS_COLORS["done"],
            ),
            (
                tr("ON TRACK"),
                str(n_on_track) if reported_status else "—",
                tr("{k}/{n} statuses reported", k=reported_status, n=n_tasks),
                STATUS_COLORS["on-track"],
            ),
            (
                tr("AT RISK"),
                str(n_at_risk) if reported_status else "—",
                tr("{k}/{n} statuses reported", k=reported_status, n=n_tasks),
                STATUS_COLORS["at-risk"],
            ),
        ]
        kpi_y = 130
        # 三行 baseline 布局：hdr → big → sub，间距按字号自适应确保 bbox 不相交
        # （fs_kpi_big 可到 50pt，若沿用固定 y+20/y+46/y+64 会让 big bbox 覆盖 hdr/sub）。
        _kpi_pad_top = 18.0
        _kpi_gap_line = 4.0
        _hdr_baseline = _kpi_pad_top
        _big_baseline = _hdr_baseline + fs_kpi_hdr * 0.2 + fs_kpi_big * 0.8 + _kpi_gap_line
        _sub_baseline = _big_baseline + fs_kpi_big * 0.2 + fs_kpi_sub * 0.8 + _kpi_gap_line
        _kpi_h = max(68.0, _sub_baseline + fs_kpi_sub * 0.2 + 8.0)
        kpi_w = 340
        kpi_gap = 20
        avail = width - MARGIN_L - MARGIN_R
        n_kpi = len(kpis)
        kpi_w = min(340, (avail - kpi_gap * (n_kpi - 1)) / n_kpi)
        for i, (label, big, sub, col) in enumerate(kpis):
            kx = MARGIN_L + i * (kpi_w + kpi_gap)
            parts.append(
                f'<rect x="{kx:.1f}" y="{kpi_y}" width="{kpi_w:.1f}" height="{_kpi_h:.1f}" fill="{PANEL}" '
                f'stroke="{_INK4}" stroke-width="0.8"/>'
            )
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y}" width="4" height="{_kpi_h:.1f}" fill="{col}"/>')
            parts.append(
                f'<text x="{kx + 18:.1f}" y="{kpi_y + _hdr_baseline:.1f}" font-family="{_body_font}" '
                f'font-size="{fs_kpi_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">'
                f"{_xesc(label)}</text>"
            )
            parts.append(
                f'<text x="{kx + 18:.1f}" y="{kpi_y + _big_baseline:.1f}" font-family="{_head_font}" '
                f'font-size="{fs_kpi_big}" fill="{_INK}" font-weight="700">{_xesc(big)}</text>'
            )
            parts.append(
                f'<text x="{kx + 18:.1f}" y="{kpi_y + _sub_baseline:.1f}" font-family="{_body_font}" '
                f'font-size="{fs_kpi_sub}" fill="{c_muted}">{_xesc(sub)}</text>'
            )
            if i == 0 and overall_progress is not None:
                metric_width = _estimate_label_width_px(big, fs_kpi_big, bold=True, font_family=_head_font)
                bx = kx + 18 + metric_width + 16
                by = kpi_y + _big_baseline - fs_kpi_big * 0.3
                bw = kx + kpi_w - 18 - bx
                bh = 10
                if bw > 30:
                    parts.append(
                        f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}" height="{bh}" '
                        f'fill="{PANEL}" stroke="{_INK4}" stroke-width="0.4"/>'
                    )
                    parts.append(
                        f'<rect x="{bx:.1f}" y="{by}" width="{bw * overall_progress / 100:.1f}" '
                        f'height="{bh}" fill="{col}"/>'
                    )
                    plan_x = bx + bw * schedule_pct / 100
                    parts.append(
                        f'<line x1="{plan_x:.1f}" y1="{by - 3}" x2="{plan_x:.1f}" y2="{by + bh + 3}" '
                        f'stroke="{_INK}" stroke-width="1.2"/>'
                    )
                    parts.append(
                        f'<text x="{plan_x:.1f}" y="{by - 6}" text-anchor="middle" '
                        f'font-family="{_body_font}" font-size="{fs_kpi_sub}" fill="{_INK}" '
                        f'font-weight="600">{_xesc(tr("PLAN"))}</text>'
                    )

    head_y = MARGIN_T - 12
    parts.append(
        f'<text x="{MARGIN_L}" y="{head_y}" font-family="{_body_font}" '
        f'font-size="{fs_head}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">'
        f"WORKSTREAM · TASK</text>"
    )
    parts.append(
        f'<text x="{MARGIN_L + LEFT_COL_W - 10}" y="{head_y}" text-anchor="end" '
        f'font-family="{_body_font}" font-size="{fs_head}" fill="{c_muted}" '
        f'font-weight="600" letter-spacing=".15em">{_xesc(tr("OWNER"))}</text>'
    )
    parts.append(
        f'<text x="{width - MARGIN_R}" y="{head_y}" text-anchor="end" '
        f'font-family="{_body_font}" font-size="{fs_head}" fill="{c_muted}" '
        f'font-weight="600" letter-spacing=".15em">STATUS · %</text>'
    )
    parts.append(
        f'<line x1="{MARGIN_L}" y1="{head_y + 6}" x2="{width - MARGIN_R}" y2="{head_y + 6}" '
        f'stroke="{_INK}" stroke-width="0.6"/>'
    )

    axis_y = plot_y - 40
    month_starts = []
    d0 = proj_start.replace(day=1)
    while d0 <= proj_end:
        month_starts.append(d0)
        if d0.month == 12:
            d0 = d0.replace(year=d0.year + 1, month=1)
        else:
            d0 = d0.replace(month=d0.month + 1)

    for i, ms in enumerate(month_starts):
        x_start = max(date_to_x(ms), plot_x)
        if i + 1 < len(month_starts):
            x_end = date_to_x(month_starts[i + 1])
        else:
            x_end = date_to_x(proj_end + _dt.timedelta(days=1))
        x_end = min(x_end, plot_x + plot_w)
        col_w = x_end - x_start
        if i % 2 == 0:
            parts.append(
                f'<rect x="{x_start:.1f}" y="{axis_y - 2}" width="{col_w:.1f}" '
                f'height="20" fill="{PANEL}" opacity="0.6"/>'
            )
        # 月份 label 若宽度超过所在列宽（col_w），会溢出到相邻 rect（触发 text_shape_overlap）。
        # 逐档缩：完整 "OCT 2025" → 只显示 "OCT" → 不显示。
        _month_label = ms.strftime("%b %Y").upper()
        _month_fs = fs_x_tick + 1
        _est_w = len(_month_label) * _month_fs * 0.62
        if _est_w > col_w - 6:
            _month_label = ms.strftime("%b").upper()
            _est_w = len(_month_label) * _month_fs * 0.62
        if _est_w > col_w - 4:
            _month_label = None
        if _month_label:
            parts.append(
                f'<text x="{(x_start + x_end) / 2:.1f}" y="{axis_y + 12}" text-anchor="middle" '
                f'font-family="{_body_font}" font-size="{_month_fs}" font-weight="700" '
                f'fill="{_INK}" letter-spacing=".05em">{_xesc(_month_label)}</text>'
            )
        if i > 0:
            parts.append(
                f'<line x1="{x_start:.1f}" y1="{axis_y + 18}" '
                f'x2="{x_start:.1f}" y2="{plot_y + plot_h + 8}" '
                f'stroke="{_INK4}" stroke-width="0.5"/>'
            )

    d_iter = proj_start
    week_i = 0
    while d_iter <= proj_end:
        x = date_to_x(d_iter)
        if week_i % 2 == 0:
            parts.append(
                f'<line x1="{x:.1f}" y1="{plot_y - 8}" x2="{x:.1f}" y2="{plot_y - 4}" '
                f'stroke="{c_muted}" stroke-width="0.5"/>'
            )
            if week_i % 4 == 0:
                parts.append(
                    f'<text x="{x:.1f}" y="{plot_y - 11}" text-anchor="middle" '
                    f'font-family="{_body_font}" font-size="{fs_x_tick - 1}" fill="{c_muted}">'
                    f"{d_iter.strftime('%d')}</text>"
                )
        d_iter += _dt.timedelta(days=7)
        week_i += 1

    # 绘图区底 + 分组 header + 斑马
    # 背景填色 + 边框合并为一个 rect，避免 bbox 完全重合触发 embed 校验告警。
    parts.append(
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" '
        f'fill="{PAPER}" stroke="{_INK}" stroke-width="0.8"/>'
    )

    prev_stream = None
    for i, t in enumerate(norm_tasks):
        if t["stream"] != prev_stream:
            prev_stream = t["stream"]
            hy = plot_y + task_y_offset[i] - GROUP_HEADER_H
            col = STREAM_COLORS[t["stream"]]
            r, g, b = _rgb_tuple(col)
            parts.append(
                f'<rect x="{MARGIN_L}" y="{hy}" width="{width - MARGIN_L - MARGIN_R}" '
                f'height="{GROUP_HEADER_H}" fill="rgba({r},{g},{b},0.10)"/>'
            )
            parts.append(f'<rect x="{MARGIN_L}" y="{hy}" width="4" height="{GROUP_HEADER_H}" fill="{col}"/>')
            parts.append(
                f'<text x="{MARGIN_L + 14}" y="{hy + 18}" '
                f'font-family="{_body_font}" font-size="{fs_group}" font-weight="700" '
                f'fill="{col}" letter-spacing=".14em">{_xesc(t["stream"].upper())}</text>'
            )
            gt = [x for x in norm_tasks if x["stream"] == t["stream"]]
            gdone = sum(1 for x in gt if x["status"] == "done")
            gvalues = [x["progress"] for x in gt if x["progress"] is not None]
            gknown = sum(x["status"] is not None for x in gt)
            gprogress = f"{sum(gvalues) / len(gvalues):g}% reported avg" if gvalues else "progress —"
            gstatus = f"{gdone}/{gknown} reported done" if gknown else "status —"
            parts.append(
                f'<text x="{MARGIN_L + 14}" y="{hy + 38}" '
                f'font-family="{_body_font}" font-size="{fs_group_sub}" fill="{c_muted}" '
                f">{gstatus} · {gprogress}</text>"
            )

        y = plot_y + task_y_offset[i]
        if i % 2 == 1:
            parts.append(
                f'<rect x="{plot_x}" y="{y}" width="{plot_w}" height="{ROW_H}" fill="{PANEL}" opacity="0.55"/>'
            )

    # 绘图区边框已合并到上方 PAPER 底色 rect；此处不再叠加以免 bbox 冲突。

    for i, t in enumerate(norm_tasks):
        y = plot_y + task_y_offset[i]
        ty = y + ROW_H / 2 + 4
        parts.append(
            f'<text x="{MARGIN_L + 22}" y="{ty:.1f}" font-family="{_body_font}" '
            f'font-size="{fs_task}" fill="{_INK}">{_xesc(t["name"])}</text>'
        )
        if t["owner"]:
            parts.append(
                f'<text x="{MARGIN_L + LEFT_COL_W - 10}" y="{ty:.1f}" text-anchor="end" '
                f'font-family="{_body_font}" font-size="{fs_task_sub}" fill="{c_muted}" '
                f'font-style="italic">{_xesc(str(t["owner"]))}</text>'
            )

    BAR_H = 22
    for i, t in enumerate(norm_tasks):
        y = plot_y + task_y_offset[i] + (ROW_H - BAR_H) / 2
        x0 = date_to_x(t["start"])
        x1 = date_to_x(t["end"] + _dt.timedelta(days=1))
        w = max(x1 - x0, 6)
        col = STREAM_COLORS[t["stream"]]
        r, g, b = _rgb_tuple(col)

        if t["milestone"]:
            cx = date_to_x(t["end"])
            cy = y + BAR_H / 2
            sz = 9
            parts.append(
                f'<rect x="{x0:.1f}" y="{y + BAR_H / 2 - 2:.1f}" width="{w:.1f}" height="4" '
                f'rx="1.5" fill="rgba({r},{g},{b},0.35)"/>'
            )
            pts = f"{cx:.1f},{cy - sz:.1f} {cx + sz:.1f},{cy:.1f} {cx:.1f},{cy + sz:.1f} {cx - sz:.1f},{cy:.1f}"
            parts.append(f'<polygon points="{pts}" fill="{col}" stroke="{PAPER}" stroke-width="1.5"/>')
            label = t["end"].strftime("%b %d")
            # 标签放到菱形左侧、与行中线对齐：
            # 之前放在菱形上方（y=cy-sz-3）时，bbox 顶端会侵入上方 group header rect 或
            # 上一行 zebra rect，触发 embed_svg_text_shape_overlap。改为放在菱形左侧后，
            # 文本中心落在本行的 zebra rect 内（若有），lint 把 center-inside 视作合法 label，
            # 且不与上方 header rect 相交。当菱形靠近左边、放不下时降级为菱形上方一档更高位置。
            _ms_txt = f"◆ {label}"
            _ms_fs = fs_ms_lbl - 2
            _ms_est_w = len(_ms_txt) * _ms_fs * 0.62
            # 与菱形留 4px padding
            _ms_x_end = cx - sz - 4
            if _ms_x_end - _ms_est_w >= plot_x + 2:
                parts.append(
                    f'<text x="{_ms_x_end:.1f}" y="{cy + 3.5:.1f}" text-anchor="end" '
                    f'font-family="{_body_font}" font-size="{_ms_fs}" fill="{_INK}" '
                    f'font-weight="600">{_xesc(_ms_txt)}</text>'
                )
            else:
                parts.append(
                    f'<text x="{cx + sz + 4:.1f}" y="{cy + 3.5:.1f}" text-anchor="start" '
                    f'font-family="{_body_font}" font-size="{_ms_fs}" fill="{_INK}" '
                    f'font-weight="600">{_xesc(_ms_txt)}</text>'
                )
        else:
            parts.append(
                f'<rect x="{x0:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR_H}" '
                f'rx="2.5" fill="rgba({r},{g},{b},0.22)" '
                f'stroke="rgba({r},{g},{b},0.55)" stroke-width="0.6"/>'
            )
            # 进度条：略微内缩以避免与计划底条 bbox 完全重合（100% 完成时）。
            pw = w * (t["progress"] or 0) / 100
            if pw > 1:
                # 内缩 0.5px 让两个 rect 的 bbox 不完全一致，同时视觉上不明显变化。
                pw_draw = min(pw, w - 0.5) if t["progress"] >= 100 else pw
                parts.append(
                    f'<rect x="{x0 + 0.3:.1f}" y="{y + 0.3:.1f}" width="{pw_draw:.1f}" '
                    f'height="{BAR_H - 0.6}" '
                    f'rx="2.5" fill="rgba({r},{g},{b},0.9)"/>'
                )
            pct_txt = f"{t['progress']:g}%" if t["progress"] is not None else "—"
            pct_width = _estimate_label_width_px(pct_txt, fs_bar_txt, bold=True, font_family=_body_font)
            if pw > pct_width + 10:
                parts.append(
                    f'<text x="{x0 + pw - 5:.1f}" y="{y + BAR_H / 2 + 3.5:.1f}" '
                    f'text-anchor="end" font-family="{_body_font}" '
                    f'font-size="{fs_bar_txt}" font-weight="700" fill="{PAPER}">{pct_txt}</text>'
                )

        sc = STATUS_COLORS.get(t["status"], _INK4)
        pct_txt = f"{t['progress']:g}%" if t["progress"] is not None else "—"
        bx = width - MARGIN_R - RIGHT_COL_W + 10
        by = y + BAR_H / 2
        parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="{sc}"/>')
        parts.append(
            f'<text x="{bx + 10:.1f}" y="{by + 3.5:.1f}" font-family="{_body_font}" '
            f'font-size="{fs_status}" fill="{_INK}" font-weight="600">{_xesc(t["status"] or "—")}</text>'
        )
        parts.append(
            f'<text x="{width - MARGIN_R:.1f}" y="{by + 3.5:.1f}" text-anchor="end" '
            f'font-family="{_head_font}" font-size="{fs_ms_lbl}" fill="{_INK}" '
            f'font-weight="700">{pct_txt}</text>'
        )

    if proj_start <= today <= proj_end:
        today_x = date_to_x(today)
        red_col = STATUS_COLORS["delayed"]
        parts.append(
            f'<line x1="{today_x:.1f}" y1="{axis_y - 4}" '
            f'x2="{today_x:.1f}" y2="{plot_y + plot_h + 6}" '
            f'stroke="{red_col}" stroke-width="1.4" stroke-dasharray="4 3" data-role="today-marker" data-color="{red_col}"/>'
        )
        today_label = f"TODAY · {today.strftime('%b %d').upper()}"
        flag_w = _estimate_label_width_px(today_label, fs_bar_lbl, bold=True, font_family=_body_font) + 20
        flag_h = fs_bar_lbl * 1.4 + 8
        fx = today_x - flag_w / 2
        fy = axis_y - 4 - flag_h - 4
        parts.append(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{flag_w}" height="{flag_h}" rx="2" fill="{red_col}"/>')
        parts.append(
            f'<polygon points="{today_x - 5:.1f},{fy + flag_h:.1f} '
            f"{today_x + 5:.1f},{fy + flag_h:.1f} "
            f'{today_x:.1f},{fy + flag_h + 5:.1f}" fill="{red_col}"/>'
        )
        parts.append(
            f'<text x="{today_x:.1f}" y="{fy + flag_h / 2 + fs_bar_lbl * 0.35:.1f}" text-anchor="middle" '
            f'font-family="{_body_font}" font-size="{fs_bar_lbl}" font-weight="700" '
            f'fill="{PAPER}">{_xesc(today_label)}</text>'
        )

    if show_legend:
        lg_y = plot_y + plot_h + 55
        parts.append(
            f'<line x1="{MARGIN_L}" y1="{lg_y - 20}" x2="{width - MARGIN_R}" y2="{lg_y - 20}" '
            f'stroke="{_INK4}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{MARGIN_L}" y="{lg_y - 5}" font-family="{_body_font}" '
            f'font-size="{fs_legend}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(tr("LEGEND"))}</text>'
        )

        demo_col = stream_series[0] if stream_series else _ACC
        r_, g_, b_ = _rgb_tuple(demo_col)
        lx = MARGIN_L + 80
        ly = lg_y - 15
        parts.append(
            f'<rect x="{lx}" y="{ly}" width="60" height="12" rx="2" '
            f'fill="rgba({r_},{g_},{b_},0.22)" stroke="rgba({r_},{g_},{b_},0.55)" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{lx + 68}" y="{ly + 10}" font-family="{_body_font}" '
            f'font-size="{fs_legend}" fill="{_INK}">{_xesc(tr("Planned duration"))}</text>'
        )

        lx += 200
        parts.append(
            f'<rect x="{lx}" y="{ly}" width="60" height="12" rx="2" '
            f'fill="rgba({r_},{g_},{b_},0.22)" stroke="rgba({r_},{g_},{b_},0.55)" stroke-width="0.6"/>'
        )
        parts.append(f'<rect x="{lx}" y="{ly}" width="42" height="12" rx="2" fill="{demo_col}"/>')
        parts.append(
            f'<text x="{lx + 68}" y="{ly + 10}" font-family="{_body_font}" '
            f'font-size="{fs_legend}" fill="{_INK}">{_xesc(tr("Actual progress"))}</text>'
        )

        lx += 200
        cx_ = lx + 8
        cy_ = ly + 6
        sz_ = 7
        pts_ = f"{cx_},{cy_ - sz_} {cx_ + sz_},{cy_} {cx_},{cy_ + sz_} {cx_ - sz_},{cy_}"
        parts.append(f'<polygon points="{pts_}" fill="{demo_col}" stroke="{PAPER}" stroke-width="1.2"/>')
        parts.append(
            f'<text x="{lx + 22}" y="{ly + 10}" font-family="{_body_font}" '
            f'font-size="{fs_legend}" fill="{_INK}">{_xesc(tr("Milestone"))}</text>'
        )

        lx += 130
        parts.append(
            f'<line x1="{lx}" y1="{ly - 1}" x2="{lx}" y2="{ly + 13}" '
            f'stroke="{STATUS_COLORS["delayed"]}" stroke-width="1.4" stroke-dasharray="4 3"/>'
        )
        parts.append(
            f'<text x="{lx + 10}" y="{ly + 10}" font-family="{_body_font}" '
            f'font-size="{fs_legend}" fill="{_INK}">{_xesc(tr("Today marker"))}</text>'
        )

        lx += 130
        for k, col in [
            ("done", STATUS_COLORS["done"]),
            ("on-track", STATUS_COLORS["on-track"]),
            ("at-risk", STATUS_COLORS["at-risk"]),
            ("delayed", STATUS_COLORS["delayed"]),
        ]:
            parts.append(f'<circle cx="{lx + 4}" cy="{ly + 6}" r="4" fill="{col}"/>')
            parts.append(
                f'<text x="{lx + 12}" y="{ly + 10}" font-family="{_body_font}" '
                f'font-size="{fs_legend}" fill="{c_muted}">{k}</text>'
            )
            lx += 78

    parts.append(
        notes_source_footer(
            note,
            source,
            x=MARGIN_L,
            x_right=width - MARGIN_R,
            y=height - 45,
            rule=_INK4,
            font=_body_font,
            fs=fs_foot,
            color=c_muted,
            figure_label=figure_label,
            figure_fs=fs_figure,
        )
    )

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# 12) Population Pyramid 人口金字塔
