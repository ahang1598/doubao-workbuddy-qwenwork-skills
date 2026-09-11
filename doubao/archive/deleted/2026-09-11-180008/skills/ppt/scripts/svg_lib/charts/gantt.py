"""charts/gantt.py

统一 API 的甘特图。

data schema:
    {
      "tasks": [(name, start, end, stream?), ...],
      # start/end 支持:
      #   - ISO date string "YYYY-MM-DD"
      #   - 数值（相对位置，任何单位）
      #   - datetime.date 对象
      "milestones"?: [(pos, label), ...],   # pos 与 tasks 的时间同类型
      "today"?: pos,
      "critical_indices"?: [int],
      "progress_map"?: {name: 0..1 (or 0..100)},
    }

variants:
  - default_flat
  - progress_split     # 描边框 + 内部填充完成部分
  - critical_path      # 关键任务用 accent 上色，slack 虚线连接
  - gradient_bars      # 柱条渐变
  - dot_range          # 起终点圆点 + 连线
"""
from __future__ import annotations
import datetime as _dt
import math
import random
from ._shared import (

    resolve_palette, xesc, auto_font_size, viewbox_fs, _rgba_with_alpha,
    is_dark_palette,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
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
        # ISO date
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
        except Exception:
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
    # numeric mode
    nums = [_to_num(p) for p in all_pts]
    return min(nums), max(nums), False


def draw_gantt(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 1100,
    height: float = None,
    title: str = None,
    subtitle: str = None,
    figure_label: str = None,
    note: str = None,
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

    # 自动补 progress_map（progress_split 需要）
    if variant == "progress_split" and not progress_map:
        rng = random.Random(0x6A)
        progress_map = {t["name"]: rng.randint(15, 90) / 100 for t in tasks}

    # 归一化 progress: 0..1
    def _prog(name):
        v = progress_map.get(name, 0.6)
        if v > 1:
            v = v / 100
        return max(0.0, min(1.0, v))

    lo, hi, use_dates = _infer_bounds(tasks, milestones, today)

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

    # 分配 stream -> series color idx
    stream_names = []
    for t in tasks:
        s = t.get("stream")
        if s and s not in stream_names:
            stream_names.append(s)
    def _task_color(t, i):
        s = t.get("stream")
        if s and s in stream_names:
            return series[stream_names.index(s) % len(series)]
        return series[i % len(series)]

    n = len(tasks)
    W = float(width)
    if height is None:
        row_target = 40 if n <= 8 else (34 if n <= 15 else 28)
        H = max(400.0, 200 + n * row_target)
    else:
        H = float(height)

    ML = 90.0
    MR = 60.0
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
    fs_task = max(11.0, viewbox_fs(W, H, n, role_mult=1.0, floor=11))
    fs_owner = max(11.0, viewbox_fs(W, H, n, role_mult=0.85, floor=11))
    fs_axis = 10

    body_font = "Inter, sans-serif"
    head_font = "Georgia, serif"

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{BG}"/>')

    # header
    y_pos = 46
    if title:
        parts.append(f'<text x="{ML:.1f}" y="{y_pos}" font-family="{head_font}" font-size="24" '
                     f'font-weight="600" fill="{label_col}" letter-spacing="0.06em">{xesc(title)}</text>')
        y_pos += 24
    if subtitle:
        parts.append(f'<text x="{ML:.1f}" y="{y_pos}" font-family="{body_font}" font-size="12" '
                     f'fill="{MUT}" letter-spacing="0.15em">{xesc(subtitle)}</text>')
        y_pos += 12
    if title or subtitle:
        parts.append(f'<line x1="{ML:.1f}" y1="{y_pos + 6:.1f}" x2="{W - MR:.1f}" '
                     f'y2="{y_pos + 6:.1f}" stroke="{INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{ML:.1f}" y="{y_pos + 24:.1f}" font-family="{body_font}" font-size="10" '
                     f'font-weight="600" fill="{MUT}" letter-spacing="0.15em">{xesc(figure_label)}</text>')

    # x-axis: ticks
    if use_dates:
        _draw_date_axis(parts, lo, hi, plot_left, plot_right, plot_top, plot_bot,
                        pal, body_font, fs_axis, dark, hide_weekend=(variant == "dot_range"))
    else:
        _draw_numeric_axis(parts, lo, hi, plot_left, plot_right, plot_top, plot_bot,
                           pal, body_font, fs_axis)

    # today line
    if today is not None:
        tx = x_of(today, plot_left, plot_right)
        parts.append(f'<line x1="{tx:.1f}" y1="{plot_top - 12:.1f}" x2="{tx:.1f}" y2="{plot_bot + 6:.1f}" '
                     f'stroke="{ACC}" stroke-width="1.6" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{tx:.1f}" y="{plot_top - 32:.1f}" text-anchor="middle" '
                     f'font-family="{body_font}" font-size="10" font-weight="700" '
                     f'fill="{ACC}">TODAY</text>')

    # tasks
    for i, t in enumerate(tasks):
        y_row = plot_top + i * row_h
        y_bar_h = row_h * 0.55
        y_bar = y_row + (row_h - y_bar_h) / 2
        col = _task_color(t, i)

        xL = x_of(t["start"], plot_left, plot_right)
        xR = x_of(t["end"], plot_left, plot_right)
        w = max(2.0, xR - xL)

        # task name label
        name = t["name"]
        # truncate long names
        max_chars = int((plot_left - ML - 10) / (fs_task * 0.6))
        display_name = name if len(name) <= max_chars else name[:max(3, max_chars - 1)] + "…"
        parts.append(f'<text x="{ML + 8:.1f}" y="{y_row + row_h/2 + 4:.1f}" '
                     f'font-family="{body_font}" font-size="{fs_task}" font-weight="600" '
                     f'fill="{label_col}">{xesc(display_name)}</text>')
        if t.get("stream") and row_h > 26:
            parts.append(f'<text x="{ML + 8:.1f}" y="{y_row + row_h/2 + 15:.1f}" '
                         f'font-family="{body_font}" font-size="{fs_owner}" fill="{MUT}">'
                         f'{xesc(str(t["stream"]))}</text>')

        # milestone diamond
        if t["is_milestone"]:
            cx = xL
            cy = y_row + row_h / 2
            parts.append(f'<polygon points="{cx:.1f},{cy - 8:.1f} {cx + 8:.1f},{cy:.1f} '
                         f'{cx:.1f},{cy + 8:.1f} {cx - 8:.1f},{cy:.1f}" '
                         f'fill="{ACC}" stroke="{INK}" stroke-width="1.2"/>')
            continue

        if variant == "default_flat":
            parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" '
                         f'height="{y_bar_h:.1f}" fill="{col}"/>')
        elif variant == "progress_split":
            prog = _prog(t["name"])
            done_w = w * prog
            parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" '
                         f'height="{y_bar_h:.1f}" fill="{_rgba_with_alpha(col, 0.18)}" '
                         f'stroke="{col}" stroke-width="1.3"/>')
            if done_w > 0:
                parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{done_w:.1f}" '
                             f'height="{y_bar_h:.1f}" fill="{col}"/>')
                if done_w > 26:
                    parts.append(f'<text x="{xL + done_w - 4:.1f}" y="{y_bar + y_bar_h/2 + 3:.1f}" '
                                 f'text-anchor="end" font-family="{body_font}" font-size="9" '
                                 f'font-weight="700" fill="{BG}">{int(prog * 100)}%</text>')
        elif variant == "critical_path":
            is_crit = i in critical
            fill = ACC if is_crit else col
            parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" '
                         f'height="{y_bar_h:.1f}" fill="{fill}"/>')
            if not is_crit and i < n - 1:
                nxt = tasks[i + 1]
                nxt_x = x_of(nxt["start"], plot_left, plot_right)
                if nxt_x > xR:
                    cy = y_row + row_h / 2
                    parts.append(f'<line x1="{xR:.1f}" y1="{cy:.1f}" x2="{nxt_x:.1f}" y2="{cy:.1f}" '
                                 f'stroke="{pal["ink4"]}" stroke-width="0.8" stroke-dasharray="3 2"/>')
            if is_crit:
                parts.append(f'<text x="{xR + 6:.1f}" y="{y_bar + y_bar_h/2 + 3:.1f}" '
                             f'font-family="{body_font}" font-size="9" font-weight="700" '
                             f'fill="{ACC}">CP</text>')
        elif variant == "gradient_bars":
            gid = f"gantt_g_{i}"
            top = _rgba_with_alpha(col, 1.0)
            bot = _rgba_with_alpha(col, 0.4)
            parts.append(f'<defs><linearGradient id="{gid}" x1="{xL:.1f}" y1="0" '
                         f'x2="{xR:.1f}" y2="0" gradientUnits="userSpaceOnUse">'
                         f'<stop offset="0%" stop-color="{top}"/>'
                         f'<stop offset="100%" stop-color="{bot}"/></linearGradient></defs>')
            parts.append(f'<rect x="{xL:.1f}" y="{y_bar:.1f}" width="{w:.1f}" '
                         f'height="{y_bar_h:.1f}" fill="url(#{gid})"/>')
        elif variant == "dot_range":
            cy = y_row + row_h / 2
            parts.append(f'<line x1="{xL:.1f}" y1="{cy:.1f}" x2="{xR:.1f}" y2="{cy:.1f}" '
                         f'stroke="{col}" stroke-width="2.4" stroke-linecap="round"/>')
            parts.append(f'<circle cx="{xL:.1f}" cy="{cy:.1f}" r="5.5" fill="{BG}" '
                         f'stroke="{col}" stroke-width="2"/>')
            parts.append(f'<circle cx="{xR:.1f}" cy="{cy:.1f}" r="5.5" fill="{col}" '
                         f'stroke="{col}" stroke-width="2"/>')
            # date/pos labels
            slbl = _fmt_pos(t["start"], use_dates)
            elbl = _fmt_pos(t["end"], use_dates)
            parts.append(f'<text x="{xL - 6:.1f}" y="{cy - 8:.1f}" text-anchor="end" '
                         f'font-family="{body_font}" font-size="8.5" fill="{MUT}">{xesc(slbl)}</text>')
            parts.append(f'<text x="{xR + 6:.1f}" y="{cy - 8:.1f}" text-anchor="start" '
                         f'font-family="{body_font}" font-size="8.5" fill="{MUT}">{xesc(elbl)}</text>')

    # user-provided milestones (outside of tasks)
    # 把 milestone 抬高到轴上方独立层：label 在 plot_top-38, diamond 在 plot_top-32~-20
    # 与 axis tick label (plot_top - 8) 分层，且与 TODAY (plot_top - 32) 保持一致但可能碰撞
    for m in milestones:
        pos, lbl = m[0], m[1]
        mx = x_of(pos, plot_left, plot_right)
        # 若和 today 位置太近，则把 milestone 再抬高 12px 以避免叠 TODAY 字
        label_y = plot_top - 44
        diamond_top = plot_top - 36
        diamond_mid = plot_top - 28
        diamond_bot = plot_top - 20
        if today is not None:
            try:
                tx_check = x_of(today, plot_left, plot_right)
                if abs(mx - tx_check) < 30:
                    label_y = plot_top - 60
                    diamond_top -= 16
                    diamond_mid -= 16
                    diamond_bot -= 16
            except Exception:
                pass
        parts.append(
            f'<polygon points="{mx:.1f},{diamond_top:.1f} {mx + 6:.1f},{diamond_mid:.1f} '
            f'{mx:.1f},{diamond_bot:.1f} {mx - 6:.1f},{diamond_mid:.1f}" '
            f'fill="{ACC}" stroke="{BG}" stroke-width="1.2"/>'
        )
        # 不再画 diamond→plot_top 的虚连接线：diamond_bot (plot_top-20) 到 plot_top 的线段
        # 会穿过位于 plot_top-8 的 tick label（如 "6"、"8"）中央，视觉上像"红线切数字"。
        # 菱形本身的下顶点已经指向 x 位置，无需额外连接线。
        # 白色 halo 描边 + accent 前景，避免与轴 tick 数字视觉粘连
        parts.append(
            f'<text x="{mx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'font-family="{body_font}" font-size="9.5" font-weight="700" '
            f'stroke="{BG}" stroke-width="3" stroke-linejoin="round" paint-order="stroke" '
            f'fill="{ACC}">{xesc(str(lbl))}</text>'
        )

    # legend for critical_path
    if variant == "critical_path" and critical:
        lx = plot_right - 260
        ly = H - 40
        # Non-critical 用 series[1]，如仍等于 accent 则退回中性 ink4
        non_crit_col = series[1] if len(series) > 1 else pal["ink4"]
        if non_crit_col == ACC:
            non_crit_col = pal["ink4"]
        parts.append(f'<rect x="{lx:.1f}" y="{ly:.1f}" width="12" height="10" fill="{ACC}"/>')
        parts.append(f'<text x="{lx + 18:.1f}" y="{ly + 9:.1f}" font-family="{body_font}" '
                     f'font-size="10" fill="{label_col}">Critical path</text>')
        parts.append(f'<rect x="{lx + 130:.1f}" y="{ly:.1f}" width="12" height="10" fill="{non_crit_col}"/>')
        parts.append(f'<text x="{lx + 148:.1f}" y="{ly + 9:.1f}" font-family="{body_font}" '
                     f'font-size="10" fill="{label_col}">Non-critical + slack</text>')

    # note
    if note:
        parts.append(f'<text x="{ML:.1f}" y="{H - 20:.1f}" font-family="{body_font}" font-size="9.5" '
                     f'fill="{MUT}"><tspan font-weight="600">Note.</tspan> {xesc(note)}</text>')

    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------
# axis helpers
# ------------------------------------------------------------

def _draw_date_axis(parts, lo, hi, plot_left, plot_right, plot_top, plot_bot,
                    pal, body_font, fs, dark, hide_weekend=False):
    total = max(1, (hi - lo).days)
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
                gx2 = plot_left + ((d - lo).days + 1) / total * (plot_right - plot_left)
                parts.append(f'<rect x="{gx:.1f}" y="{plot_top:.1f}" width="{max(0.1, gx2 - gx):.1f}" '
                             f'height="{plot_bot - plot_top:.1f}" fill="{weekend_fill}"/>')
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
    keep_labels = set(label_positions[::label_stride]) if label_stride > 1 else set(label_positions)

    d = lo
    idx = 0
    while d <= hi:
        gx = plot_left + ((d - lo).days / total) * (plot_right - plot_left)
        parts.append(f'<line x1="{gx:.1f}" y1="{plot_top:.1f}" x2="{gx:.1f}" y2="{plot_bot:.1f}" '
                     f'stroke="{pal["ink1"]}" stroke-width="0.6"/>')
        if (d.weekday() == 0 or step >= 7) and idx in keep_labels:
            parts.append(f'<text x="{gx:.1f}" y="{plot_top - 8:.1f}" text-anchor="middle" '
                         f'font-family="{body_font}" font-size="{fs}" fill="{pal["muted"]}">'
                         f'{d.strftime("%b %d")}</text>')
        d = d + _dt.timedelta(days=step)
        idx += 1


def _draw_numeric_axis(parts, lo, hi, plot_left, plot_right, plot_top, plot_bot,
                       pal, body_font, fs):
    ticks = _nice_ticks_num(lo, hi, 6)
    span = hi - lo or 1
    for t in ticks:
        gx = plot_left + ((t - lo) / span) * (plot_right - plot_left)
        parts.append(f'<line x1="{gx:.1f}" y1="{plot_top:.1f}" x2="{gx:.1f}" y2="{plot_bot:.1f}" '
                     f'stroke="{pal["ink1"]}" stroke-width="0.6"/>')
        parts.append(f'<text x="{gx:.1f}" y="{plot_top - 8:.1f}" text-anchor="middle" '
                     f'font-family="{body_font}" font-size="{fs}" fill="{pal["muted"]}">'
                     f'{_num_fmt(t)}</text>')


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
    # start
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
        return f"{int(round(v))}"
    return f"{v:g}"


def _fmt_pos(v, use_dates):
    if use_dates:
        d = _parse_date(v)
        if d:
            return d.strftime("%b %d")
    return _num_fmt(float(v)) if isinstance(v, (int, float)) else str(v)


def make_gantt(tasks,
               weeks: int = None,
               critical_index=None,
               milestones=None,
               project_start=None,
               project_end=None,
               today=None,
               title: str = None,
               subtitle: str = None,
               figure_label: str = None,
               note: str = None,
               source: str = None,
               show_kpi: bool = True,
               show_legend: bool = True,
               width: float = 1620,
               height: float = None,
               font_family: str = None,
               palette=None,
                variant: str = None) -> str:
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
       - progress: 0-100 完成度（可选，缺省 0）
       - status: "done"/"on-track"/"at-risk"/"delayed"（可选，缺省 "on-track"）
       - milestone: True/False（可选，milestone=True 时用菱形代替条）
    B) **老格式（兼容）**：list of tuple `(name, start_week, end_week)`
       + weeks=int 项目总周数
       + critical_index=int 关键路径任务索引（高亮）
       + milestones=[(week, label), ...]

    project_start / project_end: 项目起止日期（新格式时自动从 tasks 推断）
    today: 今日日期，用于红色 TODAY 竖虚线；缺省用 datetime.date.today()

    title/subtitle/figure_label/note/source: 学术风顶/底文字
    show_kpi: 顶部 4 张 KPI 卡片（OVERALL PROGRESS / COMPLETED / ON TRACK / AT RISK）
    show_legend: 底部图例条

    palette 支持 stream_colors/status_colors 覆盖。
    """
    if not _variant_is_classic('gantt', variant):
        _data = {"tasks": list(tasks), "milestones": milestones or [], "critical_indices": ([critical_index] if isinstance(critical_index, int) else list(critical_index or []))}
        return _dispatch_to_svg_lib(
            'gantt', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    import datetime as _dt

    if not tasks:
        raise ValueError("gantt: at least one task required")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.5))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(247,240,226,1)"
    PANEL = _pal.get("panel", _rgba_with_alpha(_INK, 0.04) if not c_bg else _rgba_with_alpha(_INK, 0.08))

    # 状态色（保持金融印刷风固定色，独立于 palette）
    STATUS_COLORS = {
        "done":     _pal.get("gantt_done_color",     "rgba(16,106,82,1)"),
        "on-track": _pal.get("gantt_ontrack_color",  "rgba(60,105,148,1)"),
        "at-risk":  _pal.get("gantt_atrisk_color",   "rgba(194,145,60,1)"),
        "delayed":  _pal.get("gantt_delayed_color",  "rgba(170,60,70,1)"),
    }

    # ---------- 输入归一化 ----------
    def _to_date(v):
        if isinstance(v, _dt.date):
            return v
        if isinstance(v, str):
            return _dt.datetime.strptime(v, "%Y-%m-%d").date()
        raise ValueError(f"gantt: date must be str 'YYYY-MM-DD' or date, got {v!r}")

    is_legacy = (isinstance(tasks[0], (list, tuple))
                 and len(tasks[0]) >= 3
                 and isinstance(tasks[0][1], (int, float))
                 and isinstance(tasks[0][2], (int, float)))

    if is_legacy:
        # 老 API：(name, start_week, end_week)
        if weeks is None:
            weeks = max(t[2] for t in tasks) + 1
        # 用虚拟日期：Jan 1 起，每周 7 天
        base = _dt.date(2025, 1, 6)  # Monday
        norm_tasks = []
        for i, t in enumerate(tasks):
            name = str(t[0])
            sw = int(t[1]); ew = int(t[2])
            start_d = base + _dt.timedelta(weeks=sw)
            end_d = base + _dt.timedelta(weeks=ew) - _dt.timedelta(days=1)
            is_critical = (critical_index is not None and i == critical_index)
            norm_tasks.append(dict(
                stream="Tasks",
                name=name,
                owner=None,
                start=start_d, end=end_d,
                progress=100 if is_critical else 0,
                status="on-track",
                milestone=False,
                _highlight=is_critical,
            ))
        # 里程碑作为独立任务
        if milestones:
            for m_ in milestones:
                if len(m_) < 2:
                    continue
                wk, lbl = m_[0], m_[1]
                ms_date = base + _dt.timedelta(weeks=wk)
                norm_tasks.append(dict(
                    stream="Milestones",
                    name=str(lbl),
                    owner=None,
                    start=ms_date, end=ms_date,
                    progress=0, status="on-track",
                    milestone=True, _highlight=False,
                ))
        proj_start = base
        proj_end = base + _dt.timedelta(weeks=weeks) - _dt.timedelta(days=1)
    else:
        norm_tasks = []
        for t in tasks:
            if not isinstance(t, dict):
                raise ValueError(f"gantt: new API expects dict tasks, got {type(t)}")
            norm_tasks.append(dict(
                stream=t.get("stream", "Tasks"),
                name=str(t.get("name", "")),
                owner=t.get("owner"),
                start=_to_date(t["start"]),
                end=_to_date(t["end"]),
                progress=int(t.get("progress", 0)),
                status=t.get("status", "on-track"),
                milestone=bool(t.get("milestone", False)),
                _highlight=False,
            ))
        proj_start = project_start and _to_date(project_start) or min(t["start"] for t in norm_tasks)
        proj_end = project_end and _to_date(project_end) or max(t["end"] for t in norm_tasks)

    if today is None:
        today = _dt.date.today()
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
        # 补齐缺失的 stream
        for i, name in enumerate(stream_names):
            if name not in STREAM_COLORS:
                STREAM_COLORS[name] = stream_series[i]

    # ---------- 统计 ----------
    n_tasks = len(norm_tasks)
    overall_progress = sum(t["progress"] for t in norm_tasks) / n_tasks if n_tasks else 0
    n_done = sum(1 for t in norm_tasks if t["status"] == "done")
    n_on_track = sum(1 for t in norm_tasks if t["status"] == "on-track")
    n_at_risk = sum(1 for t in norm_tasks if t["status"] == "at-risk")
    n_delayed = sum(1 for t in norm_tasks if t["status"] == "delayed")
    total_days = (proj_end - proj_start).days + 1
    days_elapsed = max(0, min(total_days, (today - proj_start).days))
    schedule_pct = days_elapsed / total_days * 100

    # ---------- 布局 ----------
    MARGIN_L = 90
    MARGIN_R = 90
    MARGIN_T = 265 if show_kpi else 160
    MARGIN_B = 130 if (note or source or show_legend) else 60

    LEFT_COL_W = 380
    RIGHT_COL_W = 140
    plot_x = MARGIN_L + LEFT_COL_W

    # ---------- 字号 ----------
    # 双重自适应：viewBox 尺寸 + 数据规模（n = tasks 数）。
    # gantt 高度由 tasks 决定（下方 height 计算），所以 base_fs 只按宽度算一档基准；
    # 之后先按 tasks 数分档，再乘各类目倍数。
    # slide 里排 3 张 SVG 缩到 400px 宽也要读得清。
    _n_tasks_fs = n_tasks
    # 高度在下面按 tasks 算；这里用 width + 800 做保守下界当"最小视口"估算 base_fs
    _base_fs = min(float(width), 820.0) * 0.02   # width=1620 → 16.4
    if _n_tasks_fs <= 4:
        _fs_data = _base_fs * 1.4
    elif _n_tasks_fs <= 8:
        _fs_data = _base_fs * 1.0
    elif _n_tasks_fs <= 15:
        _fs_data = _base_fs * 0.8
    else:
        _fs_data = max(_base_fs * 0.6, 10)

    fs_title    = round(min(34.0, max(20.0, _base_fs * 1.6)), 1)
    fs_subtitle = round(min(16.0, max(10.0, _base_fs * 0.75)), 1)
    fs_figure   = round(min(13.0, max(9.0,  _base_fs * 0.62)), 1)
    # KPI 大数字：base_fs * 3.0（原来就是大数字，保持）
    fs_kpi_hdr  = round(min(14.0, max(10.0, _base_fs * 0.65)), 1)
    fs_kpi_big  = round(min(50.0, max(24.0, _base_fs * 3.0)), 1)
    fs_kpi_sub  = round(min(14.0, max(10.0, _base_fs * 0.65)), 1)
    fs_head     = round(min(14.0, max(10.0, _base_fs * 0.7)),  1)   # 表头
    fs_group    = round(min(17.0, max(11.0, _fs_data * 0.95)), 1)   # group header
    fs_group_sub = round(min(14.0, max(10.0, _fs_data * 0.8)), 1)
    fs_task     = round(min(19.0, max(11.0, _fs_data * 1.05)), 1)   # 任务名
    fs_task_sub = round(min(14.0, max(10.0, _fs_data * 0.8)),  1)   # 任务日期/owner
    fs_bar_txt  = round(min(13.0, max(9.0,  _fs_data * 0.7)),  1)
    fs_bar_lbl  = round(min(14.0, max(10.0, _fs_data * 0.8)),  1)
    fs_status   = round(min(14.0, max(10.0, _fs_data * 0.8)),  1)
    # milestone label 略小（base_fs * 0.85）
    fs_ms_lbl   = round(min(15.0, max(10.0, _base_fs * 0.85)), 1)
    fs_x_tick   = round(min(13.0, max(9.0,  _base_fs * 0.65)), 1)
    fs_legend   = round(min(14.0, max(10.0, _base_fs * 0.7)),  1)
    fs_foot     = round(min(14.0, max(10.0, _base_fs * 0.7)),  1)
    plot_y = MARGIN_T
    plot_w = width - MARGIN_L - MARGIN_R - LEFT_COL_W - RIGHT_COL_W
    ROW_H = 40
    GROUP_HEADER_H = 32

    # 计算每个 task 的 y offset
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

    # 顶部标题
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="52" '
                     f'font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="76" '
                     f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
        parts.append(f'<line x1="{MARGIN_L}" y1="92" x2="{width-MARGIN_R}" y2="92" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="112" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        lbl_w = max(72, len(figure_label) * 8 + 20)
        parts.append(f'<text x="{MARGIN_L+lbl_w}" y="112" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" letter-spacing=".04em">'
                     f'{_xesc(f"Gantt · {n_tasks} tasks · {proj_start.isoformat()} → {proj_end.isoformat()}")}</text>')

    # KPI 卡片
    if show_kpi:
        kpis = [
            ("OVERALL PROGRESS", f"{overall_progress:.0f}%", f"schedule at {schedule_pct:.0f}% elapsed", STATUS_COLORS["on-track"]),
            ("COMPLETED", f"{n_done}", f"of {n_tasks} tasks", STATUS_COLORS["done"]),
            ("ON TRACK", f"{n_on_track}", "tasks progressing to plan", STATUS_COLORS["on-track"]),
            ("AT RISK", f"{n_at_risk}", "needs attention this week", STATUS_COLORS["at-risk"]),
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
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y}" width="{kpi_w:.1f}" height="{_kpi_h:.1f}" fill="{PANEL}" '
                         f'stroke="{_INK4}" stroke-width="0.8"/>')
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y}" width="4" height="{_kpi_h:.1f}" fill="{col}"/>')
            parts.append(f'<text x="{kx+18:.1f}" y="{kpi_y+_hdr_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_kpi_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">'
                         f'{_xesc(label)}</text>')
            parts.append(f'<text x="{kx+18:.1f}" y="{kpi_y+_big_baseline:.1f}" font-family="{_head_font}" '
                         f'font-size="{fs_kpi_big}" fill="{_INK}" font-weight="700">{_xesc(big)}</text>')
            parts.append(f'<text x="{kx+18:.1f}" y="{kpi_y+_sub_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_kpi_sub}" fill="{c_muted}">{_xesc(sub)}</text>')
            # 第一张卡片带进度条
            if i == 0:
                bx = kx + 150
                by = kpi_y + _big_baseline - fs_kpi_big * 0.3
                bw = kpi_w - 170
                bh = 10
                if bw > 30:
                    parts.append(f'<rect x="{bx:.1f}" y="{by}" width="{bw:.1f}" height="{bh}" '
                                 f'fill="{PANEL}" stroke="{_INK4}" stroke-width="0.4"/>')
                    parts.append(f'<rect x="{bx:.1f}" y="{by}" width="{bw*overall_progress/100:.1f}" '
                                 f'height="{bh}" fill="{col}"/>')
                    plan_x = bx + bw * schedule_pct / 100
                    parts.append(f'<line x1="{plan_x:.1f}" y1="{by-3}" x2="{plan_x:.1f}" y2="{by+bh+3}" '
                                 f'stroke="{_INK}" stroke-width="1.2"/>')
                    parts.append(f'<text x="{plan_x:.1f}" y="{by-6}" text-anchor="middle" '
                                 f'font-family="{_body_font}" font-size="{fs_x_tick}" fill="{_INK}" '
                                 f'font-weight="600">PLAN</text>')

    # 表头
    head_y = MARGIN_T - 12
    parts.append(f'<text x="{MARGIN_L}" y="{head_y}" font-family="{_body_font}" '
                 f'font-size="{fs_head}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">'
                 f'WORKSTREAM · TASK</text>')
    parts.append(f'<text x="{MARGIN_L + LEFT_COL_W - 10}" y="{head_y}" text-anchor="end" '
                 f'font-family="{_body_font}" font-size="{fs_head}" fill="{c_muted}" '
                 f'font-weight="600" letter-spacing=".15em">OWNER</text>')
    parts.append(f'<text x="{width - MARGIN_R}" y="{head_y}" text-anchor="end" '
                 f'font-family="{_body_font}" font-size="{fs_head}" fill="{c_muted}" '
                 f'font-weight="600" letter-spacing=".15em">STATUS · %</text>')
    parts.append(f'<line x1="{MARGIN_L}" y1="{head_y+6}" x2="{width-MARGIN_R}" y2="{head_y+6}" '
                 f'stroke="{_INK}" stroke-width="0.6"/>')

    # 月份 header + 周刻度
    axis_y = plot_y - 40
    month_starts = []
    d0 = proj_start.replace(day=1)
    while d0 <= proj_end:
        month_starts.append(d0)
        if d0.month == 12:
            d0 = d0.replace(year=d0.year+1, month=1)
        else:
            d0 = d0.replace(month=d0.month+1)

    for i, ms in enumerate(month_starts):
        x_start = max(date_to_x(ms), plot_x)
        if i + 1 < len(month_starts):
            x_end = date_to_x(month_starts[i+1])
        else:
            x_end = date_to_x(proj_end + _dt.timedelta(days=1))
        x_end = min(x_end, plot_x + plot_w)
        col_w = x_end - x_start
        if i % 2 == 0:
            parts.append(f'<rect x="{x_start:.1f}" y="{axis_y-2}" width="{col_w:.1f}" '
                         f'height="20" fill="{PANEL}" opacity="0.6"/>')
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
            parts.append(f'<text x="{(x_start+x_end)/2:.1f}" y="{axis_y+12}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="{_month_fs}" font-weight="700" '
                         f'fill="{_INK}" letter-spacing=".05em">{_xesc(_month_label)}</text>')
        if i > 0:
            parts.append(f'<line x1="{x_start:.1f}" y1="{axis_y+18}" '
                         f'x2="{x_start:.1f}" y2="{plot_y+plot_h+8}" '
                         f'stroke="{_INK4}" stroke-width="0.5"/>')

    # 周刻度
    d_iter = proj_start
    week_i = 0
    while d_iter <= proj_end:
        x = date_to_x(d_iter)
        if week_i % 2 == 0:
            parts.append(f'<line x1="{x:.1f}" y1="{plot_y - 8}" x2="{x:.1f}" y2="{plot_y - 4}" '
                         f'stroke="{c_muted}" stroke-width="0.5"/>')
            if week_i % 4 == 0:
                parts.append(f'<text x="{x:.1f}" y="{plot_y - 11}" text-anchor="middle" '
                             f'font-family="{_body_font}" font-size="{fs_x_tick-1}" fill="{c_muted}">'
                             f'{d_iter.strftime("%d")}</text>')
        d_iter += _dt.timedelta(days=7)
        week_i += 1

    # 绘图区底 + 分组 header + 斑马
    # 背景填色 + 边框合并为一个 rect，避免 bbox 完全重合触发 embed 校验告警。
    parts.append(f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" '
                 f'fill="{PAPER}" stroke="{_INK}" stroke-width="0.8"/>')

    prev_stream = None
    for i, t in enumerate(norm_tasks):
        if t["stream"] != prev_stream:
            prev_stream = t["stream"]
            hy = plot_y + task_y_offset[i] - GROUP_HEADER_H
            col = STREAM_COLORS[t["stream"]]
            r, g, b = _rgb_tuple(col)
            parts.append(f'<rect x="{MARGIN_L}" y="{hy}" width="{width-MARGIN_L-MARGIN_R}" '
                         f'height="{GROUP_HEADER_H}" fill="rgba({r},{g},{b},0.10)"/>')
            parts.append(f'<rect x="{MARGIN_L}" y="{hy}" width="4" height="{GROUP_HEADER_H}" '
                         f'fill="{col}"/>')
            parts.append(f'<text x="{MARGIN_L + 14}" y="{hy + GROUP_HEADER_H - 8}" '
                         f'font-family="{_body_font}" font-size="{fs_group}" font-weight="700" '
                         f'fill="{col}" letter-spacing=".14em">{_xesc(t["stream"].upper())}</text>')
            # 组内统计
            gt = [x for x in norm_tasks if x["stream"] == t["stream"]]
            gdone = sum(1 for x in gt if x["status"] == "done")
            gprog = sum(x["progress"] for x in gt) / len(gt) if gt else 0
            parts.append(f'<text x="{plot_x - 10}" y="{hy + GROUP_HEADER_H - 8}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_group_sub}" fill="{c_muted}" '
                         f'letter-spacing=".05em">{gdone}/{len(gt)} done · {gprog:.0f}% avg</text>')

        y = plot_y + task_y_offset[i]
        if i % 2 == 1:
            parts.append(f'<rect x="{plot_x}" y="{y}" width="{plot_w}" height="{ROW_H}" '
                         f'fill="{PANEL}" opacity="0.55"/>')

    # 绘图区边框已合并到上方 PAPER 底色 rect；此处不再叠加以免 bbox 冲突。

    # 任务名 + owner
    for i, t in enumerate(norm_tasks):
        y = plot_y + task_y_offset[i]
        ty = y + ROW_H / 2 + 4
        parts.append(f'<text x="{MARGIN_L + 22}" y="{ty:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_task}" fill="{_INK}">{_xesc(t["name"])}</text>')
        if t["owner"]:
            parts.append(f'<text x="{MARGIN_L + LEFT_COL_W - 10}" y="{ty:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_task_sub}" fill="{c_muted}" '
                         f'font-style="italic">{_xesc(str(t["owner"]))}</text>')

    # 甘特条
    BAR_H = 22
    for i, t in enumerate(norm_tasks):
        y = plot_y + task_y_offset[i] + (ROW_H - BAR_H) / 2
        x0 = date_to_x(t["start"])
        x1 = date_to_x(t["end"] + _dt.timedelta(days=1))
        w = max(x1 - x0, 6)
        col = STREAM_COLORS[t["stream"]]
        r, g, b = _rgb_tuple(col)

        if t["milestone"]:
            cx = x1
            cy = y + BAR_H / 2
            sz = 9
            # 计划区间底条
            parts.append(f'<rect x="{x0:.1f}" y="{y+BAR_H/2-2:.1f}" width="{w:.1f}" height="4" '
                         f'rx="1.5" fill="rgba({r},{g},{b},0.35)"/>')
            pts = f"{cx:.1f},{cy-sz:.1f} {cx+sz:.1f},{cy:.1f} {cx:.1f},{cy+sz:.1f} {cx-sz:.1f},{cy:.1f}"
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
                # 放左侧、右对齐、baseline 与行中线对齐
                parts.append(f'<text x="{_ms_x_end:.1f}" y="{cy + 3.5:.1f}" text-anchor="end" '
                             f'font-family="{_body_font}" font-size="{_ms_fs}" fill="{_INK}" '
                             f'font-weight="600">{_xesc(_ms_txt)}</text>')
            else:
                # 空间不够（菱形贴左边），改放右侧、左对齐
                parts.append(f'<text x="{cx + sz + 4:.1f}" y="{cy + 3.5:.1f}" text-anchor="start" '
                             f'font-family="{_body_font}" font-size="{_ms_fs}" fill="{_INK}" '
                             f'font-weight="600">{_xesc(_ms_txt)}</text>')
        else:
            # 计划底条
            parts.append(f'<rect x="{x0:.1f}" y="{y:.1f}" width="{w:.1f}" height="{BAR_H}" '
                         f'rx="2.5" fill="rgba({r},{g},{b},0.22)" '
                         f'stroke="rgba({r},{g},{b},0.55)" stroke-width="0.6"/>')
            # 进度条：略微内缩以避免与计划底条 bbox 完全重合（100% 完成时）。
            pw = w * t["progress"] / 100
            if pw > 1:
                # 内缩 0.5px 让两个 rect 的 bbox 不完全一致，同时视觉上不明显变化。
                pw_draw = min(pw, w - 0.5) if t["progress"] >= 100 else pw
                parts.append(f'<rect x="{x0 + 0.3:.1f}" y="{y + 0.3:.1f}" width="{pw_draw:.1f}" '
                             f'height="{BAR_H - 0.6}" '
                             f'rx="2.5" fill="rgba({r},{g},{b},0.9)"/>')
            # 百分比
            pct_txt = f'{t["progress"]}%'
            if t["progress"] >= 25 and pw > 34:
                parts.append(f'<text x="{x0 + pw - 5:.1f}" y="{y + BAR_H/2 + 3.5:.1f}" '
                             f'text-anchor="end" font-family="{_body_font}" '
                             f'font-size="{fs_bar_txt}" font-weight="700" fill="{PAPER}">{pct_txt}</text>')
            elif t["progress"] > 0:
                parts.append(f'<text x="{x0 + w + 4:.1f}" y="{y + BAR_H/2 + 3.5:.1f}" '
                             f'font-family="{_body_font}" font-size="{fs_bar_lbl}" '
                             f'font-weight="600" fill="{c_muted}">{pct_txt}</text>')

        # 状态 badge
        sc = STATUS_COLORS.get(t["status"], STATUS_COLORS["on-track"])
        bx = width - MARGIN_R - RIGHT_COL_W + 10
        by = y + BAR_H / 2
        parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="4" fill="{sc}"/>')
        parts.append(f'<text x="{bx + 10:.1f}" y="{by + 3.5:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_status}" fill="{_INK}" font-weight="600">{_xesc(t["status"])}</text>')
        parts.append(f'<text x="{width - MARGIN_R:.1f}" y="{by + 3.5:.1f}" text-anchor="end" '
                     f'font-family="{_head_font}" font-size="{fs_ms_lbl}" fill="{_INK}" '
                     f'font-weight="700">{t["progress"]}%</text>')

    # TODAY 竖线
    if proj_start <= today <= proj_end:
        today_x = date_to_x(today)
        red_col = STATUS_COLORS["delayed"]
        parts.append(f'<line x1="{today_x:.1f}" y1="{axis_y - 4}" '
                     f'x2="{today_x:.1f}" y2="{plot_y + plot_h + 6}" '
                     f'stroke="{red_col}" stroke-width="1.4" stroke-dasharray="4 3"/>')
        # 顶部小旗
        flag_w = 62
        flag_h = 16
        fx = today_x - flag_w / 2
        fy = axis_y - 4 - flag_h - 4
        parts.append(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{flag_w}" height="{flag_h}" '
                     f'rx="2" fill="{red_col}"/>')
        parts.append(f'<polygon points="{today_x-5:.1f},{fy+flag_h:.1f} '
                     f'{today_x+5:.1f},{fy+flag_h:.1f} '
                     f'{today_x:.1f},{fy+flag_h+5:.1f}" fill="{red_col}"/>')
        parts.append(f'<text x="{today_x:.1f}" y="{fy + 11:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_bar_lbl}" font-weight="700" '
                     f'fill="{PAPER}" letter-spacing=".1em">TODAY · {_xesc(today.strftime("%b %d").upper())}</text>')

    # 底部图例
    if show_legend:
        lg_y = plot_y + plot_h + 55
        parts.append(f'<line x1="{MARGIN_L}" y1="{lg_y - 20}" x2="{width-MARGIN_R}" y2="{lg_y - 20}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        parts.append(f'<text x="{MARGIN_L}" y="{lg_y - 5}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{c_muted}" font-weight="600" letter-spacing=".15em">LEGEND</text>')

        # 用第一个 stream 的色
        demo_col = stream_series[0] if stream_series else _ACC
        r_, g_, b_ = _rgb_tuple(demo_col)
        lx = MARGIN_L + 80
        ly = lg_y - 15
        parts.append(f'<rect x="{lx}" y="{ly}" width="60" height="12" rx="2" '
                     f'fill="rgba({r_},{g_},{b_},0.22)" stroke="rgba({r_},{g_},{b_},0.55)" stroke-width="0.6"/>')
        parts.append(f'<text x="{lx + 68}" y="{ly + 10}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{_INK}">Planned duration</text>')

        lx += 200
        parts.append(f'<rect x="{lx}" y="{ly}" width="60" height="12" rx="2" '
                     f'fill="rgba({r_},{g_},{b_},0.22)" stroke="rgba({r_},{g_},{b_},0.55)" stroke-width="0.6"/>')
        parts.append(f'<rect x="{lx}" y="{ly}" width="42" height="12" rx="2" fill="{demo_col}"/>')
        parts.append(f'<text x="{lx + 68}" y="{ly + 10}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{_INK}">Actual progress</text>')

        # milestone
        lx += 200
        cx_ = lx + 8; cy_ = ly + 6; sz_ = 7
        pts_ = f"{cx_},{cy_-sz_} {cx_+sz_},{cy_} {cx_},{cy_+sz_} {cx_-sz_},{cy_}"
        parts.append(f'<polygon points="{pts_}" fill="{demo_col}" stroke="{PAPER}" stroke-width="1.2"/>')
        parts.append(f'<text x="{lx + 22}" y="{ly + 10}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{_INK}">Milestone</text>')

        # TODAY
        lx += 130
        parts.append(f'<line x1="{lx}" y1="{ly - 1}" x2="{lx}" y2="{ly + 13}" '
                     f'stroke="{STATUS_COLORS["delayed"]}" stroke-width="1.4" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{lx + 10}" y="{ly + 10}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{_INK}">Today marker</text>')

        # 状态 badges
        lx += 130
        for k, col in [("done", STATUS_COLORS["done"]),
                       ("on-track", STATUS_COLORS["on-track"]),
                       ("at-risk", STATUS_COLORS["at-risk"]),
                       ("delayed", STATUS_COLORS["delayed"])]:
            parts.append(f'<circle cx="{lx + 4}" cy="{ly + 6}" r="4" fill="{col}"/>')
            parts.append(f'<text x="{lx + 12}" y="{ly + 10}" font-family="{_body_font}" '
                         f'font-size="{fs_legend}" fill="{c_muted}">{k}</text>')
            lx += 78

    # 底部脚注
    if note or source:
        foot_y = height - 45
        parts.append(f'<line x1="{MARGIN_L}" y1="{foot_y-14}" x2="{width-MARGIN_R}" y2="{foot_y-14}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y+14}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')
        if figure_label:
            parts.append(f'<text x="{width-MARGIN_R}" y="{foot_y+14}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_figure}" fill="{c_muted}" '
                         f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 12) Population Pyramid 人口金字塔
# ==============================================================
