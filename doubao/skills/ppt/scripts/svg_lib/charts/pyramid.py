"""charts/pyramid.py

统一 API 的人口金字塔（左右对称水平柱）。

data schema:
    {
      "categories":  [str, ...],     # N 个类别（例如年龄段）
      "left":        [num, ...],     # 左侧值
      "right":       [num, ...],     # 右侧值
      "left_label":  str,            # 左侧组标（默认 "MALE"）
      "right_label": str,            # 右侧组标（默认 "FEMALE"）
      "left_series"?:  [(name, [values]), ...],   # stacked_flat 可选
      "right_series"?: [(name, [values]), ...],   # stacked_flat 可选
    }

variants:
  - default_flat
  - filled_gradient
  - stacked_flat        # 若 data 未提供 series，自动 60/40 拆分
  - dot_flat            # Isotype 点阵
  - outlined_burgundy   # 描边 + 淡填
"""
from __future__ import annotations
import math
import re
from ._shared import (

    resolve_palette, xesc, auto_font_size, validate_svg,
    _rgba_with_alpha, is_dark_palette,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
VARIANTS = ("default_flat", "filled_gradient", "stacked_flat", "dot_flat", "outlined_burgundy")


def _autosplit(values, ratio=0.6):
    """把每格 value 拆成两个 series。"""
    a = [int(round(v * ratio)) for v in values]
    b = [v - x for v, x in zip(values, a)]
    return a, b


def _normalize_data(data, variant):
    """填充默认字段。"""
    cats = list(data["categories"])
    left = list(data["left"])
    right = list(data["right"])
    n = len(cats)
    if len(left) != n or len(right) != n:
        raise ValueError(f"pyramid: length mismatch categories={n} left={len(left)} right={len(right)}")
    for v in left + right:
        if v < 0:
            raise ValueError(f"pyramid: negative value not allowed: {v}")

    left_label = data.get("left_label", "MALE")
    right_label = data.get("right_label", "FEMALE")

    left_series = data.get("left_series")
    right_series = data.get("right_series")
    if variant == "stacked_flat":
        if not left_series:
            a, b = _autosplit(left, 0.6)
            left_series = [("Citizens", a), ("Migrants", b)]
        if not right_series:
            a, b = _autosplit(right, 0.6)
            right_series = [("Citizens", a), ("Migrants", b)]

    return {
        "categories": cats, "left": left, "right": right, "n": n,
        "left_label": left_label, "right_label": right_label,
        "left_series": left_series, "right_series": right_series,
    }


def draw_pyramid(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 1000,
    height: float = None,
    title: str = None,
    subtitle: str = None,
    figure_label: str = None,
    note: str = None,
) -> str:
    """Render a pyramid SVG.

    See module docstring for data schema.
    """
    if variant not in VARIANTS:
        raise ValueError(f"pyramid: unknown variant {variant!r}. Available: {VARIANTS}")

    pal = resolve_palette(palette)
    INK = pal["ink"]
    ACC = pal["accent"]
    MUT = pal["muted"]
    BG = pal["bg"]
    SEC = pal["secondary"]
    series = pal.get("series", [ACC, SEC, INK])
    dark = is_dark_palette(pal)

    # left color = secondary, right color = accent
    left_col = SEC if abs(_luma(SEC) - _luma(ACC)) > 40 else INK
    right_col = ACC

    d = _normalize_data(data, variant)
    cats = d["categories"]
    left_vals = d["left"]
    right_vals = d["right"]
    n = d["n"]

    # -- layout --
    W = float(width)
    slot_target = 30 if n <= 12 else (24 if n <= 20 else 18)
    plot_h_min = n * slot_target
    MARGIN_T = 130 if (title or subtitle) else 60
    MARGIN_B = 110
    if height is None:
        H = MARGIN_T + plot_h_min + MARGIN_B
        H = max(420.0, H)
    else:
        H = float(height)

    plot_top = MARGIN_T + 30
    plot_bot = H - MARGIN_B
    plot_h = plot_bot - plot_top
    row_h = plot_h / n

    ML = 90.0
    MR = 40.0
    center_x = W / 2
    # 中央 category 列宽度：既要考虑数量，也要考虑最长 category 文本的像素宽度
    # 否则短 label ok 但 "Working (25-60)" 类会被柱条盖住
    fs_cat_probe = 13 if n <= 5 else (12 if n <= 10 else (11 if n <= 20 else 10))
    longest_label_px = max((len(str(c)) for c in cats), default=0) * fs_cat_probe * 0.6
    center_gap = max(60, min(160, longest_label_px + 20))
    # n 极大时压缩一点，避免柱条过短
    if n > 12:
        center_gap = max(60, min(center_gap, 120))

    # 左右柱的绘制区间
    TOTAL_L_X = ML + 40   # 数值 anchored-end 位置
    TOTAL_R_X = W - MR - 40
    LABEL_PAD = 18
    bar_left_outer = TOTAL_L_X + LABEL_PAD
    bar_left_inner = center_x - center_gap / 2
    bar_right_inner = center_x + center_gap / 2
    bar_right_outer = TOTAL_R_X - LABEL_PAD

    half_w = min(bar_left_inner - bar_left_outer, bar_right_outer - bar_right_inner)
    max_v = max(max(left_vals), max(right_vals)) or 1
    scale = half_w / max_v * 0.94
    bar_h = row_h * (0.6 if n <= 15 else 0.7)

    # 字号自适应
    fs_cat = auto_font_size(n, base=11)
    fs_val = auto_font_size(n, base=10)
    fs_axis_hdr = auto_font_size(n, base=12)
    fs_title = 24
    fs_subtitle = 12

    body_font = "Inter, sans-serif"
    head_font = "Georgia, serif"
    title_col = "rgba(240,232,214,1)" if dark else INK
    label_col = "rgba(240,232,214,1)" if dark else INK

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{BG}"/>')

    # header
    y = 46
    if title:
        parts.append(f'<text x="{ML:.1f}" y="{y}" font-family="{head_font}" font-size="{fs_title}" '
                     f'font-weight="600" fill="{title_col}" letter-spacing="0.06em">{xesc(title)}</text>')
        y += 24
    if subtitle:
        parts.append(f'<text x="{ML:.1f}" y="{y}" font-family="{body_font}" font-size="{fs_subtitle}" '
                     f'fill="{MUT}" letter-spacing="0.16em">{xesc(subtitle)}</text>')
        y += 12
    if title or subtitle:
        parts.append(f'<line x1="{ML:.1f}" y1="{y + 6:.1f}" x2="{W - MR:.1f}" y2="{y + 6:.1f}" '
                     f'stroke="{INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{ML:.1f}" y="{y + 24:.1f}" font-family="{body_font}" font-size="10" '
                     f'font-weight="600" fill="{MUT}" letter-spacing="0.15em">{xesc(figure_label)}</text>')

    # side headers
    parts.append(
        f'<text x="{(bar_left_inner + bar_left_outer) / 2:.1f}" y="{plot_top - 14:.1f}" '
        f'text-anchor="middle" font-family="{body_font}" font-size="{fs_axis_hdr}" '
        f'font-weight="700" fill="{left_col}" letter-spacing="0.12em">'
        f'{xesc(d["left_label"])}</text>'
    )
    parts.append(
        f'<text x="{(bar_right_inner + bar_right_outer) / 2:.1f}" y="{plot_top - 14:.1f}" '
        f'text-anchor="middle" font-family="{body_font}" font-size="{fs_axis_hdr}" '
        f'font-weight="700" fill="{right_col}" letter-spacing="0.12em">'
        f'{xesc(d["right_label"])}</text>'
    )

    # subtle vertical guides at 4 ticks
    ticks = _nice_ticks(max_v, 4)
    for tick in ticks:
        dx = tick * scale
        for anchor_x in (bar_left_inner - dx, bar_right_inner + dx):
            parts.append(
                f'<line x1="{anchor_x:.1f}" y1="{plot_top:.1f}" x2="{anchor_x:.1f}" y2="{plot_bot:.1f}" '
                f'stroke="{pal["ink2"]}" stroke-width="0.4" stroke-dasharray="1 3"/>'
            )

    # variant dispatch
    if variant == "dot_flat":
        parts.extend(_render_dot(
            d, plot_top, row_h, bar_left_inner, bar_right_inner, half_w,
            center_x, left_col, right_col, MUT, INK, BG, fs_cat, fs_val, body_font
        ))
    elif variant == "stacked_flat":
        parts.extend(_render_stacked(
            d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
            center_x, series, INK, MUT, TOTAL_L_X, TOTAL_R_X, fs_cat, fs_val, body_font, label_col,
        ))
    elif variant == "filled_gradient":
        parts.extend(_render_gradient(
            d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
            center_x, left_col, right_col, INK, MUT, TOTAL_L_X, TOTAL_R_X,
            fs_cat, fs_val, body_font, label_col,
        ))
    elif variant == "outlined_burgundy":
        parts.extend(_render_outlined(
            d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
            center_x, left_col, right_col, ACC, INK, MUT, TOTAL_L_X, TOTAL_R_X,
            fs_cat, fs_val, body_font, label_col,
        ))
    else:  # default_flat
        parts.extend(_render_flat(
            d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
            center_x, left_col, right_col, INK, MUT, TOTAL_L_X, TOTAL_R_X,
            fs_cat, fs_val, body_font, label_col,
        ))

    # baselines
    parts.append(f'<line x1="{bar_left_outer - 6:.1f}" y1="{plot_bot:.1f}" '
                 f'x2="{bar_left_inner:.1f}" y2="{plot_bot:.1f}" stroke="{INK}" stroke-width="0.6"/>')
    parts.append(f'<line x1="{bar_right_inner:.1f}" y1="{plot_bot:.1f}" '
                 f'x2="{bar_right_outer + 6:.1f}" y2="{plot_bot:.1f}" stroke="{INK}" stroke-width="0.6"/>')

    # legend / note
    if note:
        parts.append(f'<text x="{ML:.1f}" y="{H - 20:.1f}" font-family="{body_font}" font-size="9.5" '
                     f'fill="{MUT}"><tspan font-weight="600">Note.</tspan> {xesc(note)}</text>')

    if variant == "stacked_flat" and d["left_series"]:
        _legend_stacked(parts, ML, H - 50, series, d, body_font, INK, label_col)

    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------
# variant renderers
# ------------------------------------------------------------

def _render_flat(d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
                 center_x, left_col, right_col, INK, MUT, TOTAL_L_X, TOTAL_R_X,
                 fs_cat, fs_val, body_font, label_col):
    out = []
    for i, cat in enumerate(d["categories"]):
        y_row = plot_top + i * row_h + (row_h - bar_h) / 2
        lv, rv = d["left"][i], d["right"][i]
        wL, wR = lv * scale, rv * scale
        out.append(f'<rect x="{bar_left_inner - wL:.1f}" y="{y_row:.1f}" width="{wL:.1f}" '
                   f'height="{bar_h:.1f}" fill="{left_col}"/>')
        out.append(f'<rect x="{bar_right_inner:.1f}" y="{y_row:.1f}" width="{wR:.1f}" '
                   f'height="{bar_h:.1f}" fill="{right_col}"/>')
        _mid_and_values(out, cat, lv, rv, center_x, TOTAL_L_X, TOTAL_R_X,
                        y_row + bar_h / 2 + 4, fs_cat, fs_val, body_font, label_col, MUT)
    return out


def _render_gradient(d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
                     center_x, left_col, right_col, INK, MUT, TOTAL_L_X, TOTAL_R_X,
                     fs_cat, fs_val, body_font, label_col):
    out = []
    # defs once
    def _grad_def(gid, col, x1, x2):
        top = _rgba_with_alpha(col, 1.0)
        bot = _rgba_with_alpha(col, 0.45)
        return (f'<linearGradient id="{gid}" x1="{x1:.1f}" y1="0" x2="{x2:.1f}" y2="0" '
                f'gradientUnits="userSpaceOnUse">'
                f'<stop offset="0%" stop-color="{top}"/>'
                f'<stop offset="100%" stop-color="{bot}"/></linearGradient>')

    defs = ['<defs>']
    for i in range(d["n"]):
        lv, rv = d["left"][i], d["right"][i]
        wL, wR = lv * scale, rv * scale
        defs.append(_grad_def(f"pyrL{i}", left_col, bar_left_inner - wL, bar_left_inner))
        defs.append(_grad_def(f"pyrR{i}", right_col, bar_right_inner + wR, bar_right_inner))
    defs.append('</defs>')
    out.extend(defs)

    for i, cat in enumerate(d["categories"]):
        y_row = plot_top + i * row_h + (row_h - bar_h) / 2
        lv, rv = d["left"][i], d["right"][i]
        wL, wR = lv * scale, rv * scale
        out.append(f'<rect x="{bar_left_inner - wL:.1f}" y="{y_row:.1f}" width="{wL:.1f}" '
                   f'height="{bar_h:.1f}" fill="url(#pyrL{i})"/>')
        out.append(f'<rect x="{bar_right_inner:.1f}" y="{y_row:.1f}" width="{wR:.1f}" '
                   f'height="{bar_h:.1f}" fill="url(#pyrR{i})"/>')
        _mid_and_values(out, cat, lv, rv, center_x, TOTAL_L_X, TOTAL_R_X,
                        y_row + bar_h / 2 + 4, fs_cat, fs_val, body_font, label_col, MUT)
    return out


def _render_outlined(d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
                     center_x, left_col, right_col, ACC, INK, MUT, TOTAL_L_X, TOTAL_R_X,
                     fs_cat, fs_val, body_font, label_col):
    # 使用 accent 家族的深浅
    LEFT_STROKE = _rgba_with_alpha(INK, 1.0)
    LEFT_FILL = _rgba_with_alpha(INK, 0.15)
    RIGHT_STROKE = ACC
    RIGHT_FILL = _rgba_with_alpha(ACC, 0.2)
    STROKE_W = 1.4

    out = []
    for i, cat in enumerate(d["categories"]):
        y_row = plot_top + i * row_h + (row_h - bar_h) / 2
        lv, rv = d["left"][i], d["right"][i]
        wL, wR = lv * scale, rv * scale
        out.append(f'<rect x="{bar_left_inner - wL:.1f}" y="{y_row:.1f}" width="{wL:.1f}" '
                   f'height="{bar_h:.1f}" fill="{LEFT_FILL}" stroke="{LEFT_STROKE}" '
                   f'stroke-width="{STROKE_W}"/>')
        out.append(f'<rect x="{bar_right_inner:.1f}" y="{y_row:.1f}" width="{wR:.1f}" '
                   f'height="{bar_h:.1f}" fill="{RIGHT_FILL}" stroke="{RIGHT_STROKE}" '
                   f'stroke-width="{STROKE_W}"/>')
        _mid_and_values(out, cat, lv, rv, center_x, TOTAL_L_X, TOTAL_R_X,
                        y_row + bar_h / 2 + 4, fs_cat, fs_val, body_font, label_col, MUT)
    return out


def _render_stacked(d, plot_top, row_h, bar_h, bar_left_inner, bar_right_inner, scale,
                    center_x, series, INK, MUT, TOTAL_L_X, TOTAL_R_X,
                    fs_cat, fs_val, body_font, label_col):
    out = []
    left_series = d["left_series"]
    right_series = d["right_series"]
    left_totals = [sum(s[1][i] for s in left_series) for i in range(d["n"])]
    right_totals = [sum(s[1][i] for s in right_series) for i in range(d["n"])]

    # 重新计算 scale 用 stacked 总和
    max_total = max(max(left_totals), max(right_totals)) or 1
    max_orig = max(max(d["left"]), max(d["right"])) or 1
    # 复用外部的 scale，前提是外部按 max_v 算出的；这里若 stacked 总数不同则重算
    stacked_scale = scale * (max_orig / max_total)

    for i, cat in enumerate(d["categories"]):
        y_row = plot_top + i * row_h + (row_h - bar_h) / 2
        # left stack (grow leftward)
        x_cursor = bar_left_inner
        for si, (sname, vals) in enumerate(left_series):
            w = vals[i] * stacked_scale
            col = series[si % len(series)]
            out.append(f'<rect x="{x_cursor - w:.1f}" y="{y_row:.1f}" width="{w:.1f}" '
                       f'height="{bar_h:.1f}" fill="{col}"/>')
            x_cursor -= w
        # right stack
        x_cursor = bar_right_inner
        for si, (sname, vals) in enumerate(right_series):
            w = vals[i] * stacked_scale
            col = series[(si + len(left_series)) % len(series)]
            out.append(f'<rect x="{x_cursor:.1f}" y="{y_row:.1f}" width="{w:.1f}" '
                       f'height="{bar_h:.1f}" fill="{col}"/>')
            x_cursor += w
        _mid_and_values(out, cat, left_totals[i], right_totals[i], center_x,
                        TOTAL_L_X, TOTAL_R_X, y_row + bar_h / 2 + 4,
                        fs_cat, fs_val, body_font, label_col, MUT)
    return out


def _render_dot(d, plot_top, row_h, bar_left_inner, bar_right_inner, half_w,
                center_x, left_col, right_col, MUT, INK, BG, fs_cat, fs_val, body_font):
    out = []
    left_vals = d["left"]
    right_vals = d["right"]
    max_v = max(max(left_vals), max(right_vals)) or 1

    dot_r = min(3.0, max(1.6, row_h * 0.1))
    dot_gap_x = dot_r * 3
    # 单行最多能画多少个 dot（保证不越过柱条左/右边界）
    dots_per_row = max(1, int((half_w - 10) / dot_gap_x))
    # unit_per_dot 需要保证 max_v 对应的 dot 数 <= dots_per_row（不换行）
    # 这样即便一行画满也不会 wrap 溢出到下方 category 槽
    unit_per_dot = max(1, math.ceil(max_v / dots_per_row))
    dot_gap_y = dot_r * 2.8

    for i, cat in enumerate(d["categories"]):
        y_mid = plot_top + i * row_h + row_h / 2
        lv, rv = left_vals[i], right_vals[i]
        n_l = min(dots_per_row, int(round(lv / unit_per_dot)))
        n_r = min(dots_per_row, int(round(rv / unit_per_dot)))
        # left dots (single row, aligned to inner edge)
        for k in range(n_l):
            col_i = k
            dx = bar_left_inner - 6 - (col_i + 1) * dot_gap_x
            dy = y_mid
            out.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="{dot_r:.1f}" fill="{left_col}"/>')
        # right dots
        for k in range(n_r):
            col_i = k
            dx = bar_right_inner + 6 + (col_i + 1) * dot_gap_x
            dy = y_mid
            out.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="{dot_r:.1f}" fill="{right_col}"/>')
        # center category
        out.append(f'<text x="{center_x:.1f}" y="{y_mid + 4:.1f}" text-anchor="middle" '
                   f'font-family="{body_font}" font-size="{fs_cat}" font-weight="600" fill="{INK}">'
                   f'{xesc(cat)}</text>')
        # values
        out.append(f'<text x="{bar_left_inner - half_w - 8:.1f}" y="{y_mid + 4:.1f}" '
                   f'text-anchor="end" font-family="{body_font}" font-size="{fs_val}" '
                   f'fill="{MUT}">{lv:,}</text>')
        out.append(f'<text x="{bar_right_inner + half_w + 8:.1f}" y="{y_mid + 4:.1f}" '
                   f'text-anchor="start" font-family="{body_font}" font-size="{fs_val}" '
                   f'fill="{MUT}">{rv:,}</text>')

    # unit legend at the bottom of the plot region
    lg_y = plot_top + d["n"] * row_h + 20
    out.append(f'<circle cx="{center_x - 100:.1f}" cy="{lg_y:.1f}" r="{dot_r}" fill="{left_col}"/>')
    out.append(f'<text x="{center_x - 88:.1f}" y="{lg_y + 4:.1f}" font-family="{body_font}" '
               f'font-size="10" fill="{INK}">1 dot = {unit_per_dot:,}</text>')
    return out


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

def _mid_and_values(out, cat, lv, rv, center_x, TOTAL_L_X, TOTAL_R_X, y_text,
                    fs_cat, fs_val, body_font, label_col, MUT):
    out.append(f'<text x="{center_x:.1f}" y="{y_text:.1f}" text-anchor="middle" '
               f'font-family="{body_font}" font-size="{fs_cat}" font-weight="600" '
               f'fill="{label_col}">{xesc(cat)}</text>')
    out.append(f'<text x="{TOTAL_L_X:.1f}" y="{y_text:.1f}" text-anchor="end" '
               f'font-family="{body_font}" font-size="{fs_val}" fill="{MUT}">{lv:,}</text>')
    out.append(f'<text x="{TOTAL_R_X:.1f}" y="{y_text:.1f}" text-anchor="start" '
               f'font-family="{body_font}" font-size="{fs_val}" fill="{MUT}">{rv:,}</text>')


def _legend_stacked(parts, x0, y0, series, d, body_font, INK, label_col):
    lx = x0
    ly = y0
    entries = []
    for i, (sname, _) in enumerate(d["left_series"]):
        entries.append((f'{d["left_label"]} · {sname}', series[i % len(series)]))
    off = len(d["left_series"])
    for i, (sname, _) in enumerate(d["right_series"]):
        entries.append((f'{d["right_label"]} · {sname}', series[(i + off) % len(series)]))
    for label, col in entries:
        parts.append(f'<rect x="{lx:.1f}" y="{ly:.1f}" width="14" height="10" fill="{col}"/>')
        parts.append(f'<text x="{lx + 20:.1f}" y="{ly + 9:.1f}" font-family="{body_font}" '
                     f'font-size="10" fill="{label_col}">{xesc(label)}</text>')
        lx += 20 + len(label) * 6.5 + 20


def _nice_ticks(vmax, count=4):
    """返回 ~count 个整数 tick，值 <= vmax。"""
    if vmax <= 0:
        return []
    step = vmax / count
    # 归一
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
    ticks = []
    v = step
    while v < vmax:
        ticks.append(v)
        v += step
    return ticks


def _luma(rgba_str):
    import re
    m = re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str or "")
    if not m:
        return 128
    r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
    return 0.299 * r + 0.587 * g + 0.114 * b


def make_population_pyramid(categories,
                            left_values,
                            right_values,
                            left_label: str = "MALE",
                            right_label: str = "FEMALE",
                            width: float = None,
                            height: float = None,
                            title: str = None,
                            subtitle: str = None,
                            figure_label: str = None,
                            figure_note: str = None,
                            note: str = None,
                            unit: str = "",
                            x_axis_label: str = None,
                            kpis: "list[tuple]" = None,
                            median_index: int = None,
                            median_label: str = None,
                            peak_index: int = None,
                            age_group_dividers: "list[tuple]" = None,
                            show_legend: bool = True,
                            font_family: str = None,
                            palette=None,
                variant: str = None) -> str:
    """
    人口金字塔（Financial-print academic style）：
      - 顶部标题 + 副标 + FIGURE caption
      - 上方 KPI 卡片区（可选，例：TOTAL POPULATION / MEDIAN AGE / SEX RATIO / DEPENDENCY / AGE COMPOSITION）
      - 主体：中轴 category label + 左右水平柱条 + 每条数值
      - 可选：median 虚线横穿（peak cohort 空心圆强调）
      - 可选：age-group 分组水平横线（0–14 / 15–64 / 65+ 分隔）
      - X 轴刻度对称 + POPULATION unit label
      - 底部图例 + Notes 脚注

    参数：
      categories:   N 个类目名（从上到下，例如 '95+', '90–94', ..., '0–4'）
      left_values:  N 个左侧数值 (>=0)
      right_values: N 个右侧数值 (>=0)
      left_label / right_label: 上方组别（"MALE" / "FEMALE" / "URBAN" ...）
      width / height: SVG 画布
      title / subtitle / figure_label / figure_note: 顶部标题区（可选）
      note: 底部脚注
      unit: X 轴刻度后缀（如 " k", "%"）
      x_axis_label: 轴下方总标签（例 "POPULATION (THOUSANDS)"）
      kpis: [(header, big_number, sub, kind), ...] 顶部 KPI 卡片；kind 可选:
            'left', 'right', 'muted'（决定左侧竖条颜色），最多 5 张
      median_index: (float) 中位数在 categories 中的分数位置（0..N-1，可 float），
                     渲染虚线横穿；配合 median_label 显示中间标签（如 "MEDIAN 36.7"）
      median_label: 中位数虚线上方文字
      peak_index:   最大柱条 index，画空心圆点标注
      age_group_dividers: [(index, label_above, label_below), ...]
                    在两个 index 之间画细分隔线并给侧栏加大写 label（如 [(3, "65+", None), (14, "WORKING", "0–14")]）
      show_legend: 显示底部 legend
      palette: 配色（None/str/dict）

    数据契约：
      - 2 ≤ N ≤ 30
      - 数值必须 >= 0
    """
    if not _variant_is_classic('population_pyramid', variant):
        _data = {"categories": list(categories), "left": list(left_values), "right": list(right_values), "left_label": left_label, "right_label": right_label}
        return _dispatch_to_svg_lib(
            'population_pyramid', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.6))
    paper = _pal.get("bg", "rgba(250,248,242,1)")

    # 派生左右两色（用 accent 做右侧、secondary/ink 做左侧；确保有色差）
    left_col = c_secondary
    right_col = _ACC
    # 若两个颜色 luminance 太接近，退回 ink vs accent
    def _luma(rgba):
        r, g, b = _rgb_tuple(rgba)
        return 0.299 * r + 0.587 * g + 0.114 * b
    if abs(_luma(left_col) - _luma(right_col)) < 40:
        left_col = _INK

    N = len(categories)
    if N < 2 or N > 30:
        raise ValueError(f"population_pyramid: N={N} out of [2, 30]")
    if len(left_values) != N or len(right_values) != N:
        raise ValueError("population_pyramid: categories / left / right length mismatch")
    for v in list(left_values) + list(right_values):
        if v < 0:
            raise ValueError(f"population_pyramid: negative value not allowed: {v}")
    max_v = max(list(left_values) + list(right_values)) or 1

    # ---- 画布布局 ----
    # width 自适应：让 plot_w = 数据实际 bar 长度 × 2 + axis_gap
    # 关键：nice_max 会凑整，bar 实际只占 axis 长度的 max_v/nice_max
    # 所以想让 bar 铺满 plot 区，就要按 nice_max 比例计算 plot_w
    MARGIN_L, MARGIN_R = 100.0, 40.0
    if width is None:
        _v = max_v or 1
        _e = 10 ** math.floor(math.log10(_v)) if _v > 0 else 1
        _nm = _e
        for _f in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
            if _f * _e >= _v:
                _nm = _f * _e; break
        _reach_ratio = _v / _nm
        # 每侧 bar 目标长度 300px，反推每侧 axis 长度 = 300/reach_ratio
        _target_bar_px = 300.0
        _target_half_axis = _target_bar_px / max(0.5, _reach_ratio)
        _axis_gap = 100.0
        width = MARGIN_L + MARGIN_R + 2 * _target_half_axis + _axis_gap
        width = max(880.0, min(1500.0, width))
    # height 自适应：每年龄段需要 slot_h ≈ 24px + 顶部标题/KPI + 底部图例/轴
    MARGIN_T = 220.0 if (kpis or title or subtitle) else 60.0
    MARGIN_B = 130.0 if show_legend else 90.0
    if height is None:
        # 每段 slot 目标 28px；N ≥ 14 时压到 24px
        _slot_target = 28 if N <= 12 else (24 if N <= 18 else 20)
        _plot_h_needed = N * _slot_target
        height = MARGIN_T + _plot_h_needed + MARGIN_B
    W, H = float(width), float(height)

    # ---- 字号自适应（viewBox + 数据规模双重）----
    _plot_h = H - MARGIN_T - MARGIN_B
    _slot_h_est = _plot_h / max(1, N)
    # slide 里 3 图并列 ≈ 400px，viewBox ~900 → 缩放 ~0.44x；字号需相应放大
    _fs_base = min(W, H) * 0.022
    # 数据规模乘数：N 少时放大更多
    if N <= 4:
        _n_mult = 1.5
    elif N <= 8:
        _n_mult = 1.2
    elif N <= 15:
        _n_mult = 0.95
    else:
        _n_mult = 0.75
    # slot 太窄时才收缩；否则不限制
    _slot_shrink = min(1.0, _slot_h_est / 22.0)
    fs_title    = round(max(24.0, min(40.0, _fs_base * 2.4)), 1)
    fs_subtitle = round(max(13.0, min(18.0, _fs_base * 1.2)), 1)
    fs_figure   = round(max(11.0, min(14.0, _fs_base * 0.95)), 1)
    fs_kpi_hdr  = round(max(11.0, min(14.0, _fs_base * 1.0)), 1)
    fs_kpi_big  = round(max(24.0, min(34.0, _fs_base * 2.4)), 1)
    fs_kpi_sub  = round(max(11.0, min(14.0, _fs_base * 1.0)), 1)
    fs_sex_lbl  = round(max(14.0, _fs_base * 1.4 * _n_mult), 1)                # MALE / FEMALE
    fs_cat      = round(max(12.0, _fs_base * 1.15 * _n_mult * _slot_shrink), 1) # 年龄段名字
    fs_val      = round(max(11.0, _fs_base * 0.95 * _n_mult * _slot_shrink), 1) # 左右数值
    fs_axis_end = round(max(11.0, _fs_base * 0.95 * _n_mult), 1)                # 轴末端 0/max 标签
    fs_axis_lbl = round(max(12.0, _fs_base * 1.05 * _n_mult), 1)                # POPULATION (THOUSANDS)
    fs_med      = round(max(11.0, _fs_base * 0.9 * _n_mult), 1)                 # median 标签
    fs_div      = round(max(11.0, _fs_base * 0.9 * _n_mult), 1)                 # 分组分隔线标签
    fs_legend   = round(max(12.0, _fs_base * 1.05 * _n_mult), 1)

    parts = []
    # 页面背景
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{paper}"/>')

    # ---- 标题区 ----
    if title:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="52" font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing="0.1">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="76" font-family="{_body_font}" '
                     f'font-size="{fs_subtitle}" fill="{c_muted}" letter-spacing="0.2">'
                     f'{_xesc(subtitle)}</text>')
    if title or subtitle:
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="92" x2="{W-MARGIN_R:.1f}" y2="92" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="112" font-family="{_body_font}" '
                     f'font-size="{fs_figure}" fill="{c_muted}" font-weight="600" letter-spacing="1.5">'
                     f'{_xesc(figure_label)}</text>')
    if figure_note:
        offset = 82 if figure_label else 0
        parts.append(f'<text x="{MARGIN_L + offset:.1f}" y="112" font-family="{_body_font}" '
                     f'font-size="{fs_figure}" fill="{c_muted}" letter-spacing="0.4">'
                     f'{_xesc(figure_note)}</text>')

    # ---- KPI 卡片行 ----
    if kpis:
        kpi_y = 130.0
        # 动态 baseline：保证 header/big/sub 三行 bbox 不相交。
        _hdr_gap = 4.0
        _pad_top = 16.0
        _hdr_baseline = _pad_top
        _big_baseline = _hdr_baseline + fs_kpi_hdr * 0.2 + fs_kpi_big * 0.8 + _hdr_gap
        _sub_baseline = _big_baseline + fs_kpi_big * 0.2 + fs_kpi_sub * 0.8 + _hdr_gap
        _kpi_content_h = _sub_baseline + fs_kpi_sub * 0.2 + 8.0
        kpi_h = max(60.0, _kpi_content_h)
        kpi_x = MARGIN_L
        avail = W - MARGIN_L - MARGIN_R
        n_kpi = len(kpis)
        gap = 20.0
        kpi_w = (avail - gap * (n_kpi - 1)) / n_kpi
        for i, tup in enumerate(kpis):
            head, big, sub = tup[0], tup[1], tup[2] if len(tup) > 2 else ""
            kind = tup[3] if len(tup) > 3 else "left"
            bar_col = {"left": left_col, "right": right_col, "muted": c_muted}.get(kind, left_col)
            kx = kpi_x + i * (kpi_w + gap)
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y:.1f}" width="{kpi_w:.1f}" height="{kpi_h:.1f}" '
                         f'fill="{paper}" stroke="{_INK4}" stroke-width="0.8"/>')
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y:.1f}" width="4" height="{kpi_h:.1f}" '
                         f'fill="{_rgba_with_alpha(bar_col, 1)}"/>')
            parts.append(f'<text x="{kx + 16:.1f}" y="{kpi_y + _hdr_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_kpi_hdr}" fill="{c_muted}" font-weight="600" letter-spacing="1.4">'
                         f'{_xesc(head)}</text>')
            parts.append(f'<text x="{kx + 16:.1f}" y="{kpi_y + _big_baseline:.1f}" font-family="{_head_font}" '
                         f'font-size="{fs_kpi_big}" fill="{_INK}" font-weight="700">{_xesc(big)}</text>')
            parts.append(f'<text x="{kx + 16:.1f}" y="{kpi_y + _sub_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_kpi_sub}" fill="{c_muted}">{_xesc(sub)}</text>')

    # ---- 主图区 ----
    plot_top = MARGIN_T
    plot_bot = H - MARGIN_B
    plot_h = plot_bot - plot_top
    plot_l = MARGIN_L
    plot_r = W - MARGIN_R
    plot_w = plot_r - plot_l
    axis_gap = 100.0  # 中轴左右各留 50px 给类目 label
    left_x0 = plot_l
    left_x1 = plot_l + (plot_w - axis_gap) / 2
    right_x0 = left_x1 + axis_gap
    right_x1 = plot_r
    label_center = (left_x1 + right_x0) / 2

    slot_h = plot_h / N
    bar_h = min(slot_h - 3, 20.0)
    if bar_h < 3:
        bar_h = max(3.0, slot_h - 1)
    row_pad = slot_h - bar_h

    # 上方组别标签
    parts.append(f'<text x="{(left_x0 + left_x1) / 2:.1f}" y="{plot_top - 8:.1f}" '
                 f'text-anchor="middle" font-family="{_body_font}" font-size="{fs_sex_lbl}" '
                 f'font-weight="700" fill="{_rgba_with_alpha(left_col, 1)}" letter-spacing="2.4">'
                 f'{_xesc(left_label)}</text>')
    parts.append(f'<text x="{(right_x0 + right_x1) / 2:.1f}" y="{plot_top - 8:.1f}" '
                 f'text-anchor="middle" font-family="{_body_font}" font-size="{fs_sex_lbl}" '
                 f'font-weight="700" fill="{_rgba_with_alpha(right_col, 1)}" letter-spacing="2.4">'
                 f'{_xesc(right_label)}</text>')

    # 计算 X 轴刻度（对称的 nice numbers）
    def _nice_max(v):
        if v <= 0: return 1
        e = 10 ** math.floor(math.log10(v))
        # 更细的档位，让 axis_max 更贴近 max_v，减少 bar 长度浪费
        for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
            if m * e >= v:
                return m * e
        return 10 * e
    axis_max = _nice_max(max_v)
    left_scale = (left_x1 - left_x0) / axis_max
    right_scale = (right_x1 - right_x0) / axis_max

    # X 轴刻度对（对称 5 段）
    n_ticks = 5
    x_ticks = [axis_max * i / n_ticks for i in range(n_ticks + 1)]
    # 竖直虚线（背景）
    for t in x_ticks:
        x_left = left_x1 - t * left_scale
        x_right = right_x0 + t * right_scale
        parts.append(f'<line x1="{x_left:.1f}" y1="{plot_top:.1f}" x2="{x_left:.1f}" y2="{plot_bot:.1f}" '
                     f'stroke="{_INK4}" stroke-width="0.4" stroke-dasharray="1 3"/>')
        parts.append(f'<line x1="{x_right:.1f}" y1="{plot_top:.1f}" x2="{x_right:.1f}" y2="{plot_bot:.1f}" '
                     f'stroke="{_INK4}" stroke-width="0.4" stroke-dasharray="1 3"/>')

    # 中轴 category 名（在中央柱条槽正中）
    for i, cat in enumerate(categories):
        y = plot_top + i * slot_h + slot_h / 2 + 3
        style = ' font-weight="700"' if (peak_index is not None and i == peak_index) else ''
        parts.append(f'<text x="{label_center:.1f}" y="{y:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_cat}" fill="{_INK}"{style}>'
                     f'{_xesc(cat)}</text>')

    # 数值格式化
    def _fmt(v):
        if isinstance(v, float) and abs(v) >= 1000:
            return f"{int(round(v)):,}"
        if isinstance(v, float):
            return f"{v:.1f}"
        return f"{v:,}" if isinstance(v, int) and abs(v) >= 1000 else str(v)

    # 柱条与数值
    for i in range(N):
        l = left_values[i]
        r = right_values[i]
        y = plot_top + i * slot_h + row_pad / 2
        is_peak = (peak_index is not None and i == peak_index)
        # 左侧
        w_l = l * left_scale
        parts.append(f'<rect x="{left_x1 - w_l:.1f}" y="{y:.1f}" width="{w_l:.1f}" height="{bar_h:.1f}" '
                     f'fill="{_rgba_with_alpha(left_col, 1)}"/>')
        parts.append(f'<text x="{left_x1 - w_l - 4:.1f}" y="{y + bar_h / 2 + 3:.1f}" '
                     f'text-anchor="end" font-family="{_body_font}" font-size="{fs_val}" '
                     f'fill="{"#{}#".format(_INK)[1:-1] if False else (_INK if is_peak else c_muted)}">'
                     f'{_fmt(l)}</text>')
        # 右侧
        w_r = r * right_scale
        parts.append(f'<rect x="{right_x0:.1f}" y="{y:.1f}" width="{w_r:.1f}" height="{bar_h:.1f}" '
                     f'fill="{_rgba_with_alpha(right_col, 1)}"/>')
        parts.append(f'<text x="{right_x0 + w_r + 4:.1f}" y="{y + bar_h / 2 + 3:.1f}" '
                     f'font-family="{_body_font}" font-size="{fs_val}" '
                     f'fill="{_INK if is_peak else c_muted}">{_fmt(r)}</text>')
        # peak cohort 空心圆
        if is_peak:
            parts.append(f'<circle cx="{left_x1 - w_l:.1f}" cy="{y + bar_h / 2 - 1:.1f}" r="2" '
                         f'fill="none" stroke="{_ACC}" stroke-width="0.9"/>')
            parts.append(f'<circle cx="{right_x0 + w_r - 2:.1f}" cy="{y + bar_h / 2 - 1:.1f}" r="2" '
                         f'fill="none" stroke="{_ACC}" stroke-width="0.9"/>')

    # median 虚线
    if median_index is not None:
        y_med = plot_top + (median_index + 0.5) * slot_h
        parts.append(f'<line x1="{left_x0:.1f}" y1="{y_med:.1f}" x2="{left_x1:.1f}" y2="{y_med:.1f}" '
                     f'stroke="{_ACC}" stroke-width="0.9" stroke-dasharray="4 3"/>')
        parts.append(f'<line x1="{right_x0:.1f}" y1="{y_med:.1f}" x2="{right_x1:.1f}" y2="{y_med:.1f}" '
                     f'stroke="{_ACC}" stroke-width="0.9" stroke-dasharray="4 3"/>')
        if median_label:
            # 标签放在 median 上方 slot 里，避免遮住 category name 和数值
            lab_w = max(60, len(median_label) * 6 + 12)
            lab_h = 14
            lab_y = y_med - slot_h * 0.55  # 上一格中
            # 若上一 slot 越顶，向下放
            if lab_y - lab_h / 2 < plot_top + 4:
                lab_y = y_med + slot_h * 0.55
            parts.append(f'<rect x="{label_center - lab_w / 2:.1f}" y="{lab_y - lab_h / 2:.1f}" '
                         f'width="{lab_w:.1f}" height="{lab_h:.1f}" fill="{paper}" '
                         f'stroke="{_ACC}" stroke-width="0.6"/>')
            parts.append(f'<text x="{label_center:.1f}" y="{lab_y + 3:.1f}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="{fs_med}" fill="{_ACC}" '
                         f'font-weight="700" letter-spacing="0.6">{_xesc(median_label)}</text>')

    # age-group dividers
    if age_group_dividers:
        for tup in age_group_dividers:
            idx, above, below = tup[0], tup[1] if len(tup) > 1 else None, tup[2] if len(tup) > 2 else None
            y_div = plot_top + idx * slot_h
            parts.append(f'<line x1="{plot_l:.1f}" y1="{y_div:.1f}" x2="{plot_r:.1f}" y2="{y_div:.1f}" '
                         f'stroke="{_rgba_with_alpha(_INK, 0.35)}" stroke-width="0.5" '
                         f'stroke-dasharray="2 4"/>')
            if above:
                parts.append(f'<text x="{plot_l - 10:.1f}" y="{y_div - 4:.1f}" text-anchor="end" '
                             f'font-family="{_body_font}" font-size="{fs_div}" fill="{c_muted}" '
                             f'letter-spacing="0.8" font-weight="600">{_xesc(above)}</text>')
            if below:
                parts.append(f'<text x="{plot_l - 10:.1f}" y="{y_div + 14:.1f}" text-anchor="end" '
                             f'font-family="{_body_font}" font-size="{fs_div}" fill="{c_muted}" '
                             f'letter-spacing="0.8" font-weight="600">{_xesc(below)}</text>')

    # X 轴基线 + 刻度数值
    parts.append(f'<line x1="{left_x0:.1f}" y1="{plot_bot:.1f}" x2="{left_x1:.1f}" y2="{plot_bot:.1f}" '
                 f'stroke="{_INK}" stroke-width="0.6"/>')
    parts.append(f'<line x1="{right_x0:.1f}" y1="{plot_bot:.1f}" x2="{right_x1:.1f}" y2="{plot_bot:.1f}" '
                 f'stroke="{_INK}" stroke-width="0.6"/>')
    for t in x_ticks:
        x_left = left_x1 - t * left_scale
        x_right = right_x0 + t * right_scale
        label = _fmt(t) + unit
        parts.append(f'<text x="{x_left:.1f}" y="{plot_bot + 16:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_axis_end}" fill="{c_muted}">{label}</text>')
        parts.append(f'<text x="{x_right:.1f}" y="{plot_bot + 16:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_axis_end}" fill="{c_muted}">{label}</text>')

    if x_axis_label:
        parts.append(f'<text x="{label_center:.1f}" y="{plot_bot + 34:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_axis_lbl}" fill="{c_muted}" '
                     f'letter-spacing="1.4">{_xesc(x_axis_label)}</text>')

    # ---- 图例 ----
    if show_legend:
        lg_y = plot_bot + 54
        lg_x = MARGIN_L + 30
        parts.append(f'<rect x="{lg_x:.1f}" y="{lg_y:.1f}" width="16" height="10" '
                     f'fill="{_rgba_with_alpha(left_col, 1)}"/>')
        parts.append(f'<text x="{lg_x + 22:.1f}" y="{lg_y + 9:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{c_muted}">{_xesc(left_label.title() if left_label.isupper() else left_label)}</text>')
        lg_x2 = lg_x + 90
        parts.append(f'<rect x="{lg_x2:.1f}" y="{lg_y:.1f}" width="16" height="10" '
                     f'fill="{_rgba_with_alpha(right_col, 1)}"/>')
        parts.append(f'<text x="{lg_x2 + 22:.1f}" y="{lg_y + 9:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{c_muted}">{_xesc(right_label.title() if right_label.isupper() else right_label)}</text>')
        if median_index is not None and median_label:
            lg_x3 = lg_x2 + 100
            parts.append(f'<line x1="{lg_x3:.1f}" y1="{lg_y + 5:.1f}" x2="{lg_x3 + 24:.1f}" '
                         f'y2="{lg_y + 5:.1f}" stroke="{_ACC}" stroke-width="0.9" stroke-dasharray="4 3"/>')
            parts.append(f'<text x="{lg_x3 + 30:.1f}" y="{lg_y + 9:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_legend}" fill="{c_muted}">Median</text>')
        if peak_index is not None:
            lg_x4 = lg_x2 + 100 + (100 if (median_index is not None and median_label) else 0)
            parts.append(f'<circle cx="{lg_x4 + 8:.1f}" cy="{lg_y + 5:.1f}" r="2" '
                         f'fill="none" stroke="{_ACC}" stroke-width="0.9"/>')
            parts.append(f'<text x="{lg_x4 + 18:.1f}" y="{lg_y + 9:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_legend}" fill="{c_muted}">Peak cohort</text>')

    # ---- 底部脚注 ----
    if note:
        foot_y = H - 20
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{foot_y - 14:.1f}" x2="{W - MARGIN_R:.1f}" '
                     f'y2="{foot_y - 14:.1f}" stroke="{_INK4}" stroke-width="0.5"/>')
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{foot_y:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_legend}" fill="{c_muted}">'
                     f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 13) Event Timeline 事件时间轴
# ==============================================================
