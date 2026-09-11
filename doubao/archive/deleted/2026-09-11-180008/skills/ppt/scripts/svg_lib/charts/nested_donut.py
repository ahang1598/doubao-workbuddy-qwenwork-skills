"""svg_lib/charts/nested_donut.py

Nested Donut · 5 variant 统一 API：
- donut_flat: 双层 donut，内 domain 深色 / 外 sub 浅色（同色系）
- donut_gradient: 内环用 radial gradient（中亮外深）
- sunburst_flat: 三层放射：中心 ALL + 内 domain + 外 sub（无中空）
- polar_area_outlined: 极坐标玫瑰图，每 sub 一个 wedge，半径 = value，outlined 皮肤
- donut_layered: 双层 donut + drop shadow 效果

data schema：
  {
    "segments": [(name, value, [(sub, sub_value), ...]), ...],
    "total_label"?: str,
    "total_value"?: number,   # 若不提供则用 sum(value)
  }
  - value: domain 全局占比（推荐 sum=100 或与 total_value 一致，函数会按总和归一）
  - sub_value: sub 的全局占比（该 domain 所有 sub 加起来应 ≈ value；不强制）
"""
from __future__ import annotations
import math
from typing import Dict, Optional

from ._shared import (

    resolve_palette, xesc, svg_open, svg_close, auto_font_size,
    _rgba_with_alpha, rgb_tuple,
)

from .._common import (_INK, _derive_series_colors, _is_dark_palette, _prepend_bg_if_dark, _render_title_block, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, ridge_density_from_samples, _variant_is_classic, _dispatch_to_svg_lib, _estimate_label_width_px)


def _fit_leader_label(text, max_width_px, fs, body_font, bold=True, fs_floor=9.0):
    """Return (fitted_text, fitted_fs) so `_estimate_label_width_px` <= max_width_px.

    Strategy:
      1. If it already fits at `fs`, return as-is.
      2. Try shrinking font-size down to `fs_floor` in 0.5 steps.
      3. If still doesn't fit at `fs_floor`, truncate with a single-char ellipsis
         suffix ("Prefix…") until the estimated width fits at `fs_floor`.
         Preserve a trailing "X%"/"12" numeric tail if present so readers still
         see the value.
    Widths are computed with the same estimator used by the embed validator
    (`_estimate_label_width_px`), matching the OOB check byte-for-byte.
    """
    if max_width_px <= 0 or not text:
        return text, fs
    if _estimate_label_width_px(text, fs, bold=bold, font_family=body_font) <= max_width_px:
        return text, fs
    # 1) shrink fs down to floor
    cur_fs = fs
    while cur_fs - 0.5 >= fs_floor:
        cur_fs -= 0.5
        if _estimate_label_width_px(text, cur_fs, bold=bold, font_family=body_font) <= max_width_px:
            return text, cur_fs
    cur_fs = fs_floor
    if _estimate_label_width_px(text, cur_fs, bold=bold, font_family=body_font) <= max_width_px:
        return text, cur_fs
    # 2) truncate at fs_floor. Try to preserve the trailing " value" (last token) if any.
    parts = text.rsplit(" ", 1)
    if len(parts) == 2 and parts[1] and (parts[1][-1] in "%0123456789" or parts[1].replace(".", "").isdigit()):
        head, tail = parts[0], " " + parts[1]
    else:
        head, tail = text, ""
    # Iterative truncation with ellipsis suffix
    ellipsis = "…"  # U+2026 HORIZONTAL ELLIPSIS
    for keep in range(len(head), 0, -1):
        candidate = head[:keep].rstrip() + ellipsis + tail
        if _estimate_label_width_px(candidate, cur_fs, bold=bold, font_family=body_font) <= max_width_px:
            return candidate, cur_fs
    # 3) Last resort: single-char + ellipsis (drop tail)
    if head:
        candidate = head[0] + ellipsis
        return candidate, cur_fs
    return text, cur_fs


def _abbrev_number(n):
    """Abbreviate a numeric value to a compact 3-4 char label.

    Examples: 1289456789 -> '1.29B'; 12345 -> '12.3K'; 999 -> '999'.
    Falls back to str(n) for non-numeric input.
    """
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    absv = abs(v)
    sign = "-" if v < 0 else ""
    if absv >= 1e12:
        s = f"{absv/1e12:.2f}T"
    elif absv >= 1e9:
        s = f"{absv/1e9:.2f}B"
    elif absv >= 1e6:
        s = f"{absv/1e6:.2f}M"
    elif absv >= 1e3:
        s = f"{absv/1e3:.1f}K"
    else:
        # For small values keep original repr; if it's integer-valued show as int
        if isinstance(n, float) and float(n).is_integer():
            return f"{sign}{int(absv)}"
        return str(n)
    # Trim trailing zeros in decimal ("1.20K" -> "1.2K", "1.00B" -> "1B")
    if "." in s:
        head, unit = s[:-1], s[-1]
        head = head.rstrip("0").rstrip(".")
        s = head + unit
    return f"{sign}{s}"


def _fit_center_label(text, max_width_px, fs, body_font, bold=True, fs_floor=10.0):
    """Fit a center total-value label into `max_width_px`.

    Strategy:
      1. If it fits at fs, return as-is.
      2. If text is purely numeric and long (>=7 chars), try abbreviated form
         (1289456789 -> '1.29B').
      3. Shrink fs down to fs_floor in 1.0 steps.
      4. As a last resort, use the abbreviated form at fs_floor.
    """
    if max_width_px <= 0 or not text:
        return text, fs
    s = str(text)
    if _estimate_label_width_px(s, fs, bold=bold, font_family=body_font) <= max_width_px:
        return s, fs
    # Try abbrev first for numeric-looking strings
    stripped = s.lstrip("-").replace(".", "")
    is_numeric = stripped.isdigit()
    if is_numeric and len(s) >= 7:
        abbr = _abbrev_number(s)
        if _estimate_label_width_px(abbr, fs, bold=bold, font_family=body_font) <= max_width_px:
            return abbr, fs
        s = abbr  # keep shrinking on the abbreviated form
    # Shrink fs down to floor
    cur_fs = fs
    while cur_fs - 1.0 >= fs_floor:
        cur_fs -= 1.0
        if _estimate_label_width_px(s, cur_fs, bold=bold, font_family=body_font) <= max_width_px:
            return s, cur_fs
    return s, max(fs_floor, cur_fs)


VARIANTS = (
    "donut_flat", "donut_gradient", "sunburst_flat",
    "polar_area_outlined", "donut_layered",
)


def _series_colors(pal, n):
    series = pal.get("series")
    if series and len(series) >= n:
        return list(series[:n])
    if series:
        return [series[i % len(series)] for i in range(n)]
    acc, ink = pal["accent"], pal["ink"]
    return [acc, pal["secondary"], ink, pal["muted"]] * ((n // 4) + 1)


def _lighten(rgba_str, ratio=0.5):
    r, g, b = rgb_tuple(rgba_str)
    r2 = int(r + (255 - r) * ratio)
    g2 = int(g + (255 - g) * ratio)
    b2 = int(b + (255 - b) * ratio)
    return f"rgba({r2},{g2},{b2},1)"


def _polar(cx, cy, r, deg):
    """SVG 角度：起点 -90°（12 点方向），顺时针"""
    rad = math.radians(deg - 90)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def _arc_path(cx, cy, r_in, r_out, ang_from, ang_to):
    """扇形环 path（顺时针扫）"""
    if ang_to - ang_from >= 360:
        # 完整环
        ang_to = ang_from + 359.99
    large = 1 if (ang_to - ang_from) > 180 else 0
    x1, y1 = _polar(cx, cy, r_out, ang_from)
    x2, y2 = _polar(cx, cy, r_out, ang_to)
    x3, y3 = _polar(cx, cy, r_in, ang_to)
    x4, y4 = _polar(cx, cy, r_in, ang_from)
    if r_in <= 0.01:
        return (f"M {cx:.2f} {cy:.2f} "
                f"L {x1:.2f} {y1:.2f} "
                f"A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} Z")
    return (f"M {x1:.2f} {y1:.2f} "
            f"A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} "
            f"L {x3:.2f} {y3:.2f} "
            f"A {r_in:.2f} {r_in:.2f} 0 {large} 0 {x4:.2f} {y4:.2f} Z")


def _render_leader_labels(cx, cy, R_ref, entries, ink, body_font,
                          fs=10.0, min_span=1.5,
                          viewbox_x=0.0, viewbox_w=None, margin=2.0):
    """给 outer label 打外部 leader line（水平引线 + 两侧竖排 label）。

    entries: list of (label_text, s_from, s_to) —— 已按扇形角度排好；跨越 span<min_span 会被丢弃。
    返回 SVG 片段字符串 list（可直接加进 parts）。

    布局：
      - mid_ang < 180 -> 右侧 label
      - mid_ang >= 180 -> 左侧 label
      - 引线：anchor -> elbow_x -> label_x, 水平段共 y
      - tidy pass 强制最小行距 fs*1.25 防止重叠

    viewbox_x / viewbox_w: SVG viewBox 左边界 / 宽度，用来做单个 label 的
      OOB 预防：估算 label 宽度，超出 (viewbox_x + viewbox_w - margin) 时先
      缩字号，再截断加省略号。传 None 时跳过（向后兼容）。
    """
    fragments = []
    anchor_r = R_ref + 6
    line_h = fs * 1.25
    right_group = []
    left_group = []
    for label_text, s_from, s_to in entries:
        span = s_to - s_from
        if span < min_span:
            continue
        mid_ang = (s_from + s_to) / 2
        ax, ay = _polar(cx, cy, anchor_r, mid_ang)
        rec = {"name": label_text, "ax": ax, "ay": ay, "y": ay}
        if 0 <= mid_ang < 180:
            right_group.append(rec)
        else:
            left_group.append(rec)

    def _tidy(group, y_min, y_max):
        if not group:
            return
        group.sort(key=lambda r: r["ay"])
        for r in group:
            r["y"] = max(y_min, min(y_max, r["ay"]))
        for i in range(1, len(group)):
            if group[i]["y"] < group[i - 1]["y"] + line_h:
                group[i]["y"] = group[i - 1]["y"] + line_h
        if group and group[-1]["y"] > y_max:
            group[-1]["y"] = y_max
            for i in range(len(group) - 2, -1, -1):
                if group[i]["y"] > group[i + 1]["y"] - line_h:
                    group[i]["y"] = group[i + 1]["y"] - line_h

    y_min = cy - R_ref
    y_max = cy + R_ref
    _tidy(right_group, y_min, y_max)
    _tidy(left_group, y_min, y_max)

    right_elbow_x = cx + R_ref + 12
    left_elbow_x = cx - R_ref - 12
    right_label_x = cx + R_ref + 28
    left_label_x = cx - R_ref - 28

    def _emit(group, label_x, elbow_x, anchor_side):
        text_anchor = "start" if anchor_side == "right" else "end"
        for r in group:
            ax = r["ax"]
            ay = r["ay"]
            ly = r["y"]
            text_dx = 4 if anchor_side == "right" else -4
            # per-label fit: shrink fs / truncate to avoid OOB right/left
            label_text = r["name"]
            label_fs = fs
            if viewbox_w is not None:
                if anchor_side == "right":
                    avail = (viewbox_x + viewbox_w - margin) - (label_x + text_dx)
                else:
                    avail = (label_x + text_dx) - (viewbox_x + margin)
                if avail > 0:
                    label_text, label_fs = _fit_leader_label(
                        label_text, avail, fs, body_font, bold=True, fs_floor=9.0,
                    )
            fragments.append(
                f'<polyline points="{ax:.1f},{ay:.1f} {elbow_x:.1f},{ly:.1f} '
                f'{label_x + text_dx:.1f},{ly:.1f}" '
                f'fill="none" stroke="{_rgba_with_alpha(ink, 0.35)}" stroke-width="0.8"/>'
            )
            fragments.append(
                f'<text font-family="{body_font}" x="{label_x:.1f}" y="{ly + label_fs * 0.35:.1f}" '
                f'font-size="{label_fs}" fill="{_rgba_with_alpha(ink, 0.95)}" font-weight="600" '
                f'text-anchor="{text_anchor}" dominant-baseline="alphabetic">{label_text}</text>'
            )

    _emit(right_group, right_label_x, right_elbow_x, "right")
    _emit(left_group, left_label_x, left_elbow_x, "left")
    return fragments


def draw_nested_donut(
    data: Dict,
    variant: str = "donut_flat",
    palette="archive_ink",
    width: float = 720,
    height: float = 720,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    figure_label: Optional[str] = None,
) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {VARIANTS}")

    segments = data.get("segments") or []
    if not segments:
        raise ValueError("nested_donut: at least one segment required")
    total_label = data.get("total_label", "TOTAL")
    total_value = data.get("total_value")

    pal = resolve_palette(palette)
    ink, ink6 = pal["ink"], pal["ink6"]
    bg = pal["bg"]
    accent = pal["accent"]
    series = _series_colors(pal, max(6, len(segments)))

    body_font = "Inter, sans-serif"
    head_font = "Georgia, serif"

    # 归一化 domain
    dom_total = sum(v for _, v, _ in segments) or 1.0
    if total_value is None:
        total_value = dom_total

    # ---- leader-line 触发条件（与 make_nested_donut 保持一致）----
    # sub-slice 总数 > 8：径向 label 会挤压重叠；宽画布（w/h > 1.5）：右侧本来就有空间。
    _n_subs_total = sum(len(s[2]) for s in segments)
    _aspect = float(width) / float(height) if height else 1.0
    _wide = _aspect > 1.5
    _needs_leader = (_n_subs_total > 8) or _wide
    _label_reserve = 90.0 if _needs_leader else 0.0

    cx = width / 2
    cy = height / 2 + (10 if title else 0)
    R = min(width, height) / 2 - 40 - (30 if title else 0) - _label_reserve

    parts = [svg_open(0, 0, width, height, bg=bg)]
    defs_parts = []

    # title
    if figure_label:
        parts.append(
            f'<text x="{20}" y="24" font-family="{body_font}" font-size="10" '
            f'font-weight="700" fill="{pal["muted"]}" letter-spacing=".18em">{xesc(figure_label)}</text>'
        )
    if title:
        parts.append(
            f'<text x="{cx}" y="34" text-anchor="middle" font-family="{head_font}" '
            f'font-size="22" font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
    if subtitle:
        parts.append(
            f'<text x="{cx}" y="54" text-anchor="middle" font-family="{body_font}" '
            f'font-size="11" fill="{pal["muted"]}" letter-spacing=".08em">{xesc(subtitle)}</text>'
        )

    # Layered drop-shadow for donut_layered:
    # 用一份 translate(3,5) 的深色半透明副本叠在原 path 下方，模拟原 feGaussianBlur+feOffset+feFuncA(slope=0.35) 的效果
    # （不用 <filter>，validator 不支持 filter/feX）
    _use_layered_shadow = (variant == "donut_layered")

    # radial gradients for donut_gradient
    if variant == "donut_gradient":
        for i, col in enumerate(series[:len(segments)]):
            r, g, b = rgb_tuple(col)
            defs_parts.append(
                f'<radialGradient id="ndg_{i}" cx="50%" cy="50%" r="65%">'
                f'<stop offset="0%" stop-color="rgba({min(255,r+40)},{min(255,g+40)},{min(255,b+40)},1)"/>'
                f'<stop offset="100%" stop-color="rgba({max(0,r-30)},{max(0,g-30)},{max(0,b-30)},1)"/>'
                f'</radialGradient>'
            )

    # 几何
    # NOTE: 内环 domain 文字 = domain_name + pct% 两行，annulus 太窄时两行 label 无法
    # 完全塞进 R_center → R_inner 之间。原 R_inner=R*0.60 让 band width 只有 R*0.30，
    # 在 4 slice 45° corner angle 上两行文字 bbox 会往外/往内溢出（外触外环边缘，内
    # 触中心圆 AABB）→ 视觉上看外环覆盖了内环文字。改 R_inner=R*0.72 把内环 band
    # 拓宽到 R*0.42（+40%），配合下方 text_r 用 0.55 ratio（略偏外的 midpoint），
    # 让 label bbox 中心 shift 向圆心方向、并两侧都获得足够 clearance。
    if variant == "sunburst_flat":
        R_center = R * 0.15
        R_l1_in = R_center
        R_l1_out = R * 0.50
        R_l2_out = R * 0.95
    else:
        R_outer = R
        R_inner = R * 0.72
        R_center = R * 0.30

    filter_attr = ""  # 已改用 shadow_dup pattern（下方 translate 副本），不再走 SVG filter

    # 主图元
    if variant == "sunburst_flat":
        # 中心 ALL
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{R_center}" fill="{ink}"/>'
        )
        # 中心值（value 在上，label 在下）
        _fs_center_val = max(14, R_center * 0.42)
        parts.append(
            f'<text x="{cx}" y="{cy - 2:.1f}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{_fs_center_val:.0f}" font-weight="800" fill="{bg}">'
            f'{total_value:g}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + _fs_center_val * 0.75:.1f}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{max(9, R_center * 0.22):.0f}" font-weight="700" fill="{bg}" '
            f'letter-spacing=".18em">'
            f'{xesc(total_label)}</text>'
        )
        ang = 0.0
        _sunburst_leader_entries = []  # collect (label_text, s_from, s_to) for leader-line pass
        for i, (dom, dpct, subs) in enumerate(segments):
            d_from = ang
            d_to = ang + dpct / dom_total * 360
            base = series[i % len(series)]
            # 内层 domain
            parts.append(
                f'<path d="{_arc_path(cx, cy, R_l1_in, R_l1_out, d_from, d_to)}" '
                f'fill="{base}" stroke="{bg}" stroke-width="1.5"/>'
            )
            mid = (d_from + d_to) / 2
            span = d_to - d_from
            # 中心 domain 文字：从 midpoint (0.5) 略向内收到 0.48，避免宽 domain name
            # 的 bbox 触到 R_l1_out（视觉上被外环覆盖）。degenerate slice 跳过 label。
            tr = R_l1_in + (R_l1_out - R_l1_in) * 0.48
            tx, ty = _polar(cx, cy, tr, mid)
            fs_dom = auto_font_size(len(segments), base=13, min_size=9, max_size=15) if span >= 20 else 10
            if span >= 1.0:
                parts.append(
                    f'<text x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="middle" '
                    f'font-family="{body_font}" font-size="{fs_dom}" font-weight="700" '
                    f'fill="{bg}">{xesc(dom)}</text>'
                )
            # 外层 subs
            sa = d_from
            sub_total = sum(sh for _, sh in subs) or 1.0
            for j, (sname, sval) in enumerate(subs):
                s_from = sa
                s_to = sa + sval / sub_total * (d_to - d_from)
                lc = _lighten(base, 0.35 + 0.15 * (j % 3))
                parts.append(
                    f'<path d="{_arc_path(cx, cy, R_l1_out, R_l2_out, s_from, s_to)}" '
                    f'fill="{lc}" stroke="{bg}" stroke-width="1"/>'
                )
                if _needs_leader:
                    # 收集，稍后统一走 leader-line 布局
                    _sunburst_leader_entries.append((xesc(sname), s_from, s_to))
                    sa = s_to
                    continue
                # sub 标签
                smid = (s_from + s_to) / 2
                tr2 = (R_l1_out + R_l2_out) / 2
                tx2, ty2 = _polar(cx, cy, tr2, smid)
                s_span = s_to - s_from
                fs = 11 if s_span >= 15 else (9 if s_span >= 7 else 8)
                if s_span < 3:
                    sa = s_to
                    continue
                rot = smid - 90 if 0 <= smid < 180 else smid + 90
                parts.append(
                    f'<text x="{tx2:.1f}" y="{ty2:.1f}" text-anchor="middle" '
                    f'font-family="{body_font}" font-size="{fs}" font-weight="600" '
                    f'fill="{_rgba_with_alpha(ink, 0.85)}" dominant-baseline="middle" '
                    f'transform="rotate({rot:.1f} {tx2:.1f} {ty2:.1f})">{xesc(sname)}</text>'
                )
                sa = s_to
            ang = d_to

        if _needs_leader and _sunburst_leader_entries:
            parts.extend(_render_leader_labels(
                cx, cy, R_l2_out, _sunburst_leader_entries,
                ink=ink, body_font=body_font, fs=10.0,
                viewbox_x=0.0, viewbox_w=width,
            ))

    elif variant == "polar_area_outlined":
        # 展平 sub
        subs_flat = []
        for i, (dom, dpct, subs) in enumerate(segments):
            for j, (sname, sval) in enumerate(subs):
                subs_flat.append((sname, sval, i))
        if not subs_flat:
            # fallback: use domains directly
            subs_flat = [(d[0], d[1], i) for i, d in enumerate(segments)]
        n_wedges = len(subs_flat)
        R_max = R - 30
        max_val = max(s[1] for s in subs_flat) or 1
        ang_step = 360.0 / n_wedges
        # 参考圆
        for k in (0.25, 0.5, 0.75, 1.0):
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{R_max * k:.1f}" fill="none" '
                f'stroke="{_rgba_with_alpha(ink, 0.15)}" stroke-width="0.6" stroke-dasharray="3 3"/>'
            )
        # 首先画所有 wedge
        for k, (sname, sval, di) in enumerate(subs_flat):
            a_from = k * ang_step
            a_to = a_from + ang_step * 0.9
            r_out = R_max * sval / max_val
            col = series[di % len(series)]
            r, g, b = rgb_tuple(col)
            parts.append(
                f'<path d="{_arc_path(cx, cy, 4, r_out, a_from, a_to)}" '
                f'fill="rgba({r},{g},{b},0.20)" stroke="{col}" stroke-width="1.4"/>'
            )
        # 再画所有 label —— 切向排列（沿弧），锚点在 R_max+18 的外圈上。
        # 切向 = 文字基线垂直于半径（沿切线走），不会汇聚到圆心。
        # 当 wedge 特别多（>16）时对极小 wedge（sval/max_val < 0.15）省略 label 只留 legend。
        fs = auto_font_size(n_wedges, base=11, min_size=8, max_size=12)
        skip_tiny = n_wedges > 16
        if _needs_leader:
            # 走 leader-line：两侧竖排 label，避免切向文字挤压
            _entries = []
            for k, (sname, sval, di) in enumerate(subs_flat):
                a_from = k * ang_step
                a_to = a_from + ang_step * 0.9
                if skip_tiny and (sval / max_val) < 0.15:
                    continue
                _entries.append((f"{xesc(sname)} {sval:g}", a_from, a_to))
            parts.extend(_render_leader_labels(
                cx, cy, R_max, _entries,
                ink=ink, body_font=body_font, fs=float(fs),
                viewbox_x=0.0, viewbox_w=width,
            ))
        else:
            for k, (sname, sval, di) in enumerate(subs_flat):
                a_from = k * ang_step
                a_to = a_from + ang_step * 0.9
                r_out = R_max * sval / max_val
                if skip_tiny and (sval / max_val) < 0.15:
                    # 太小时省略标签
                    continue
                mid = (a_from + a_to) / 2
                r_label = R_max + 18
                tx, ty = _polar(cx, cy, r_label, mid)
                # 切向旋转：text baseline 沿切线方向。
                # 顶部/底部 (mid≈0 或 180) → 文字水平；左/右 (mid≈90 或 270) → 文字垂直。
                # 保证下半圆文字不倒立：mid ∈ (90,270) 时加 180 让文字翻正。
                if 90 < mid < 270:
                    rot = mid + 180
                else:
                    rot = mid
                # 引线（细）：从 wedge 外沿到 label 附近
                if r_label - r_out > 10:
                    lx1, ly1 = _polar(cx, cy, r_out, mid)
                    lx2, ly2 = _polar(cx, cy, r_label - 8, mid)
                    parts.append(
                        f'<line x1="{lx1:.1f}" y1="{ly1:.1f}" x2="{lx2:.1f}" y2="{ly2:.1f}" '
                        f'stroke="{_rgba_with_alpha(ink, 0.22)}" stroke-width="0.6"/>'
                    )
                parts.append(
                    f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                    f'font-family="{body_font}" font-size="{fs}" font-weight="600" '
                    f'fill="{ink}" dominant-baseline="middle" '
                    f'transform="rotate({rot:.1f} {tx:.1f} {ty:.1f})">{xesc(sname)} · {sval:g}</text>'
                )
        # 中心 total_value + total_label（放在参考圆中心，不遮挡 wedge 因为 wedge 从 r=4 开始）
        _fs_center_val = max(14, R_max * 0.12)
        parts.append(
            f'<text x="{cx}" y="{cy - 2:.1f}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{_fs_center_val:.0f}" font-weight="800" fill="{ink}">'
            f'{total_value:g}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + _fs_center_val * 0.85:.1f}" text-anchor="middle" '
            f'font-family="{body_font}" font-size="10" font-weight="700" '
            f'fill="{pal["muted"]}" letter-spacing=".18em">{xesc(total_label)}</text>'
        )
        # legend
        # 动态布局：估算每项宽度（swatch + text），必要时自动换行以适应画布宽度。
        body_fs = 12
        char_w = body_fs * 0.6
        swatch_w = 14 + 8  # swatch + gap
        pad = 24  # 每项之间的额外间距
        legend_left = 40
        legend_right = width - 20
        avail_w = max(legend_right - legend_left, 100)
        items = []
        for i, (dom, _pct, _subs) in enumerate(segments):
            item_w = swatch_w + len(dom) * char_w + pad
            items.append((i, dom, item_w))
        # 逐行装填
        rows = [[]]
        row_widths = [0.0]
        for it in items:
            _i, _dom, iw = it
            if row_widths[-1] + iw > avail_w and rows[-1]:
                rows.append([])
                row_widths.append(0.0)
            rows[-1].append(it)
            row_widths[-1] += iw
        row_h = 22
        # legend 顶行 y：让最后一行贴到 height-24 附近
        n_rows = len(rows)
        lg_y_top = height - 20 - (n_rows - 1) * row_h
        for ri, row in enumerate(rows):
            x_cur = legend_left
            y = lg_y_top + ri * row_h
            for (i, dom, iw) in row:
                col = series[i % len(series)]
                r, g, b = rgb_tuple(col)
                parts.append(
                    f'<rect x="{x_cur}" y="{y - 10}" width="14" height="14" '
                    f'fill="rgba({r},{g},{b},0.30)" stroke="{col}" stroke-width="1.2"/>'
                )
                parts.append(
                    f'<text x="{x_cur + 22}" y="{y + 1}" font-family="{body_font}" '
                    f'font-size="{body_fs}" font-weight="600" fill="{ink}">{xesc(dom)}</text>'
                )
                x_cur += iw

    else:
        # donut_flat / donut_gradient / donut_layered
        ang = 0.0
        outer_labels = []
        for i, (dom, dpct, subs) in enumerate(segments):
            d_from, d_to = ang, ang + dpct / dom_total * 360
            base = series[i % len(series)]
            inner_fill = f"url(#ndg_{i})" if variant == "donut_gradient" else base
            outer_fill = _lighten(base, 0.5)
            # 内环 domain
            inner_d = _arc_path(cx, cy, R_center, R_inner, d_from, d_to)
            if _use_layered_shadow:
                parts.append(
                    f'<path d="{inner_d}" transform="translate(3,5)" '
                    f'fill="{ink}" fill-opacity="0.25" stroke="none"/>'
                )
            parts.append(
                f'<path d="{inner_d}" '
                f'fill="{inner_fill}" stroke="{bg}" stroke-width="1.5"{filter_attr}/>'
            )
            mid_ang = (d_from + d_to) / 2
            span = d_to - d_from
            # Skip labels for degenerate / near-zero slices (avoid stacking labels at
            # the same point → embed_svg_bbox_overlap, and unreadable anyway).
            if span < 1.0:
                # 外环 sub
                sub_total = sum(sh for _, sh in subs) or 1.0
                sub_ang = d_from
                for j, (sname, sval) in enumerate(subs):
                    s_from = sub_ang
                    s_to = sub_ang + sval / sub_total * (d_to - d_from)
                    outer_d = _arc_path(cx, cy, R_inner, R_outer, s_from, s_to)
                    if _use_layered_shadow:
                        parts.append(
                            f'<path d="{outer_d}" transform="translate(3,5)" '
                            f'fill="{ink}" fill-opacity="0.22" stroke="none"/>'
                        )
                    parts.append(
                        f'<path d="{outer_d}" '
                        f'fill="{outer_fill}" stroke="{bg}" stroke-width="1"{filter_attr}/>'
                    )
                    outer_labels.append((sname, sval, s_from, s_to, i))
                    sub_ang = s_to
                ang = d_to
                continue
            # Place the two-line label (domain_name + pct%) near the RADIAL MIDPOINT
            # of the (now widened) inner ring band. Previous code used ratio 0.75 which
            # pushed the label bbox close to R_inner → visually the outer ring appeared
            # to cover the label's outer edge. With R_inner=0.72*R and ratio=0.55, the
            # bbox sits centered in the band with clearance from BOTH the outer edge
            # (R_inner) and the center-circle AABB (R_center).
            text_r = R_center + (R_inner - R_center) * 0.55
            tx, ty = _polar(cx, cy, text_r, mid_ang)
            fs_dom = 14 if span >= 30 else (12 if span >= 15 else 9)
            fs_pct = 12 if span >= 30 else (10 if span >= 15 else 8)
            # Shift the label pair up by half its own vertical extent so it's
            # geometrically CENTERED on (tx,ty). Two-line block has approx height
            # fs_dom + 2 + fs_pct; center-of-block should map to ty.
            _line_gap = 2.0
            _block_h = fs_dom + _line_gap + fs_pct
            _y_top = ty - _block_h * 0.5  # top of dom line (visual top)
            _y_dom = _y_top + fs_dom * 0.85  # baseline of dom
            _y_pct = _y_top + fs_dom + _line_gap + fs_pct * 0.85  # baseline of pct
            parts.append(
                f'<text x="{tx:.1f}" y="{_y_dom:.1f}" font-family="{body_font}" '
                f'font-size="{fs_dom}" font-weight="700" fill="{bg}" '
                f'text-anchor="middle">{xesc(dom)}</text>'
            )
            parts.append(
                f'<text x="{tx:.1f}" y="{_y_pct:.1f}" font-family="{body_font}" '
                f'font-size="{fs_pct}" font-weight="700" fill="{_rgba_with_alpha(bg, 0.9)}" '
                f'text-anchor="middle">{dpct / dom_total * 100:.1f}%</text>'
            )
            # 外环 sub
            sub_total = sum(sh for _, sh in subs) or 1.0
            sub_ang = d_from
            for j, (sname, sval) in enumerate(subs):
                s_from = sub_ang
                s_to = sub_ang + sval / sub_total * (d_to - d_from)
                outer_d = _arc_path(cx, cy, R_inner, R_outer, s_from, s_to)
                if _use_layered_shadow:
                    parts.append(
                        f'<path d="{outer_d}" transform="translate(3,5)" '
                        f'fill="{ink}" fill-opacity="0.22" stroke="none"/>'
                    )
                parts.append(
                    f'<path d="{outer_d}" '
                    f'fill="{outer_fill}" stroke="{bg}" stroke-width="1"{filter_attr}/>'
                )
                outer_labels.append((sname, sval, s_from, s_to, i))
                sub_ang = s_to
            ang = d_to

        # 外环标签 —— 走 leader-line（>8 sub 或 wide）或径向 rotate
        if _needs_leader:
            _entries = [
                (f"{xesc(sname)} {sval:g}", s_from, s_to)
                for (sname, sval, s_from, s_to, di) in outer_labels
            ]
            parts.extend(_render_leader_labels(
                cx, cy, R_outer, _entries,
                ink=ink, body_font=body_font, fs=10.0,
                viewbox_x=0.0, viewbox_w=width,
            ))
        else:
            # 极小 slice（span<5°）省略 label；相邻 label 角度差过小时交替径向偏移防压叠
            prev_visible_mid = None
            prev_offset = 0
            for (sname, sval, s_from, s_to, di) in outer_labels:
                span = s_to - s_from
                if span < 5:
                    continue
                mid_ang = (s_from + s_to) / 2
                # 邻近检测：与上一个可见 label 的角度差 <10° 且未跨过 180° 时，交替径向外推
                offset = 0
                if prev_visible_mid is not None:
                    delta = abs(mid_ang - prev_visible_mid)
                    if delta < 10:
                        offset = 10 if prev_offset == 0 else 0
                prev_visible_mid = mid_ang
                prev_offset = offset
                text_r = (R_inner + R_outer) / 2 + offset
                tx, ty = _polar(cx, cy, text_r, mid_ang)
                fs = 12 if span >= 20 else (10 if span >= 10 else 9)
                rot = mid_ang - 90 if 0 <= mid_ang < 180 else mid_ang + 90
                parts.append(
                    f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
                    f'font-family="{body_font}" font-size="{fs}" font-weight="600" '
                    f'fill="{ink}" dominant-baseline="middle" '
                    f'transform="rotate({rot:.1f} {tx:.1f} {ty:.1f})">'
                    f'{xesc(sname)} {sval:g}</text>'
                )

        # 中心圆 + total
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{R_center}" fill="{bg}" '
            f'stroke="{_rgba_with_alpha(ink, 0.15)}" stroke-width="0.8"/>'
        )
        fs_total_val = max(16, R_center * 0.35)
        parts.append(
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{fs_total_val:.0f}" font-weight="700" fill="{ink}">'
            f'{total_value:g}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="10" font-weight="700" fill="{pal["muted"]}" '
            f'letter-spacing=".18em">{xesc(total_label)}</text>'
        )

    # 组装 defs
    if defs_parts:
        defs_str = "<defs>" + "".join(defs_parts) + "</defs>"
        parts.insert(1, defs_str)

    # ---- 收窄 viewBox 底部空白 ----
    # svg_open 初始用的是 (0, 0, width, height)，但 donut/sunburst 只用到 cy±R_outer
    # 附近的垂直范围；height 只是坐标参考系。medium/large 触发 leader 后 R 减小到
    # ~200，donut 底 = cy + R ≈ 570 → viewBox=720 底部 ~150px 空白。改按实际内容
    # bottom 收窄。polar_area_outlined 例外 —— 它用整块画布 (R = R_max)，label ring
    # 在 R_max+18，几乎顶到底，且 leader 布局会把 label 竖排到 cy±R_max，收窄不安全，
    # 保持原始 height。
    _bg_pad = 10.0
    if variant == "sunburst_flat":
        _content_bot = cy + R_l2_out + _bg_pad
    elif variant == "polar_area_outlined":
        _content_bot = height  # 不收窄
    else:
        _content_bot = cy + R_outer + _bg_pad
    _new_vb_h = min(height, max(_content_bot, cy + 20))
    if _new_vb_h < height:
        # 只在能收窄时改写 parts[0]（svg_open 输出）以及 bg rect（如果有）。
        _new_h_str = f'{_new_vb_h:.1f}'
        # svg_open 生成：'<svg ... viewBox="0 0 width height">' 后可能跟 '<rect ... width="w" height="h" .../>'
        # 直接替换 parts[0]。
        _first = parts[0]
        _first = _first.replace(f'viewBox="0 0 {width} {height}"', f'viewBox="0 0 {width} {_new_h_str}"')
        _first = _first.replace(f'height="{height}"', f'height="{_new_h_str}"', 1)
        parts[0] = _first

    parts.append(svg_close())
    return "".join(parts)


def make_nested_donut(data,
                      total_label: str = "TOTAL",
                      total_value = None,
                      width: float = 720.0,
                      height: float = 720.0,
                      domain_colors: dict = None,
                      title: str = None,
                      subtitle: str = None,
                      figure_label: str = None,
                      font_family: str = None,
                      palette: dict = None,
                variant: str = None) -> str:
    """
    双层甜甜圈（内环 = 一级分类 domain / 外环 = 二级子类 sub-intent）：
    典型场景：任务/预算/流量按"领域 × 操作类型"双维度分解，父子扇形角度自然对齐。

    data: [(domain, domain_pct, [(sub_name, sub_pct), ...]), ...]
      - domain: 一级分类名
      - domain_pct: 该 domain 占全局的百分比（0-100，所有 domain 加起来应 ≈ 100）
      - subs: 二级子类列表，(sub_name, sub_pct)；sub_pct 是**全局百分比**（不是 domain 内百分比）
              所有 subs 的 sum 应 = domain_pct（函数不强制校验，只警告）
    total_label / total_value: 中心显示 "value / label" 两行（value 缺省时用 sum of domain_pct）
    domain_colors: 可选 {domain_name: base_color_rgba}，未传的 domain 从默认调色板轮转
                   外环 sub-slice 会用同色系 + 提亮/降饱和（自动派生）
    palette: 可选 {ink, muted, grid}；也支持 "domain_default_colors"（list）覆盖默认调色板

    视觉：
    - 内环 domain 扇形：主色实心，白色分隔线 1.5px
    - 外环 sub 扇形：domain 主色降饱和的浅变体，白色分隔线 1px
    - 内环文字：水平居中在扇形几何中心，两行（domain_name / pct%）
    - 外环文字：宽扇形（≥20°）沿弧线 textPath；窄扇形（<20°）径向从内向外 rotate
    - 中心空心圆：total_value + total_label
    """
    if not _variant_is_classic('nested_donut', variant):
        _data = {"segments": list(data), "total_label": total_label}
        if total_value is not None:
            _data["total_value"] = total_value
        return _dispatch_to_svg_lib(
            'nested_donut', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
            width=width, height=height,
        )

    if not data:
        raise ValueError("nested_donut: at least one domain required")
    for i, d in enumerate(data):
        if len(d) < 3:
            raise ValueError(f"nested_donut: data[{i}] must be (domain, pct, subs), got {d}")

    # ---- palette ----
    def _rgba_with_alpha(rgba_str, alpha):
        import re as _re
        m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str)
        if not m:
            return f"rgba(28,28,26,{alpha})"
        return f"rgba({int(float(m.group(1)))},{int(float(m.group(2)))},{int(float(m.group(3)))},{alpha})"
    def _rgb_tuple(rgba_str):
        import re as _re
        m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str)
        if not m:
            return (28, 28, 26)
        return (int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))))
    def _lighten(rgba_str, ratio=0.55):
        """把主色向白色靠 ratio 比例（0.55 = 深主色变淡主色）"""
        r, g, b = _rgb_tuple(rgba_str)
        r2 = int(r + (255 - r) * ratio)
        g2 = int(g + (255 - g) * ratio)
        b2 = int(b + (255 - b) * ratio)
        return f"rgba({r2},{g2},{b2},1)"

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    c_ink   = _pal.get("ink",   _INK)
    c_muted = _pal.get("muted", _rgba_with_alpha(c_ink, 0.5))
    # 从 palette 派生系列色（先看 palette["series"]，否则从 accent 做 hue-shift 派生 n 色）
    # nested_donut 需要至少 8 个系列色（domain 轮转）
    _default_colors = _pal.get("domain_default_colors") or _derive_series_colors(_pal, max(8, len(data)))

    # ---- 归一化 domain_colors + 派生外环色 ----
    dc = dict(domain_colors) if domain_colors else {}
    inner_colors = []
    outer_lighten = []
    for i, (dom, _pct, _subs) in enumerate(data):
        base = dc.get(dom) or _default_colors[i % len(_default_colors)]
        inner_colors.append(base)
        outer_lighten.append(_lighten(base, 0.5))

    # ---- 几何 ----
    # Wide aspect (w/h > 1.5): 缩小 donut 半径（用 height 主导），donut 靠左 30% 位置，
    # 留右侧较大宽度做外部 leader label；左侧也留够 label reserve，避免左半 wedge label 无处放。
    # Tall aspect / 方形: 居中；若 sub-slice 数 > 8 也要外部 label，此时收缩半径为标签让位
    _aspect = float(width) / float(height) if height else 1.0
    _wide = _aspect > 1.5
    _n_subs_total = sum(len(d[2]) for d in data)
    _needs_leader = (_n_subs_total > 8) or _wide
    _label_reserve = 90.0 if _needs_leader else 0.0
    import math as _m
    if _wide:
        # R 由 height 主导（不用 min(w,h) —— 那样 wide embed 里 R 太小很浪费竖向空间）
        R_outer = height / 2 - 30
        # cx：左侧留出 _label_reserve+padding，donut 中心固定在 R_outer + _label_reserve + 30
        # 这样左半 wedge label 有 _label_reserve 宽度可用，右半更宽（占用剩余画布）
        cx = R_outer + _label_reserve + 30
        cy = height / 2
    else:
        cx, cy = width / 2, height / 2
        # 外圈半径：为标签让空间。有 leader 时两侧各留 _label_reserve
        R_outer = min(width, height) / 2 - 30 - _label_reserve
    # NOTE: 内环 domain 文字（domain_name + pct% 两行）之前用 R_inner=0.60*R,
    # 让内环 band 只有 R*0.30，_text_r_default 落在 annulus midpoint 也常常让 label
    # bbox 向外挤到 R_inner 边缘 —— 视觉上外环覆盖了内环文字。与 draw_nested_donut
    # 骨架路径对齐：R_inner=0.72*R 拓宽内环 band 到 R*0.42，_text_r_default 用 0.55
    # 比例（略偏内的 midpoint），label bbox 中心留出对外环 (R_inner) 与中心圆 AABB
    # (R_center) 两侧 clearance。
    R_inner = R_outer * 0.72   # 内环拓宽，为两行 label 让空间
    R_center = R_outer * 0.30

    # ---------- 字号自适应（viewBox + 数据规模双重）----------
    _n_dom_fs = len(data)
    _fs_base = min(float(width), float(height)) * 0.022
    if _n_dom_fs <= 4:
        _fs_dom_mult = 1.55
    elif _n_dom_fs <= 8:
        _fs_dom_mult = 1.2
    elif _n_dom_fs <= 15:
        _fs_dom_mult = 0.9
    else:
        _fs_dom_mult = 0.72
    # 外圈标签更小些（fs * 0.85），因为空间紧
    _fs_sub_mult = _fs_dom_mult * 0.85
    _fs_dom_wide = max(14.0, _fs_base * 1.2 * _fs_dom_mult)   # domain wide arcs
    _fs_dom_mid  = max(12.0, _fs_base * 1.0 * _fs_dom_mult)   # domain medium arcs
    _fs_dom_narrow = max(10.0, _fs_base * 0.75 * _fs_dom_mult) # domain narrow arcs
    _fs_pct_wide = max(12.0, _fs_base * 1.0 * _fs_dom_mult)
    _fs_pct_mid  = max(10.0, _fs_base * 0.85 * _fs_dom_mult)
    _fs_pct_narrow = max(9.0, _fs_base * 0.7 * _fs_dom_mult)
    _fs_sub_wide = max(13.0, _fs_base * 1.15 * _fs_sub_mult)
    _fs_sub_mid  = max(11.0, _fs_base * 0.95 * _fs_sub_mult)
    _fs_sub_small = max(10.0, _fs_base * 0.8 * _fs_sub_mult)
    _fs_sub_tiny = max(10.0, _fs_base * 0.7 * _fs_sub_mult)
    _fs_center_val = max(30.0, _fs_base * 2.6)
    _fs_center_lbl = max(12.0, _fs_base * 1.0)

    def _polar(cx0, cy0, r, deg):
        """SVG 角度：起点 -90°（12 点方向），顺时针"""
        rad = _m.radians(deg - 90)
        return (cx0 + r * _m.cos(rad), cy0 + r * _m.sin(rad))

    def _arc_path(cx0, cy0, r_in, r_out, ang_from, ang_to):
        """扇形环 path（顺时针扫）"""
        large = 1 if (ang_to - ang_from) > 180 else 0
        x1, y1 = _polar(cx0, cy0, r_out, ang_from)
        x2, y2 = _polar(cx0, cy0, r_out, ang_to)
        x3, y3 = _polar(cx0, cy0, r_in, ang_to)
        x4, y4 = _polar(cx0, cy0, r_in, ang_from)
        return (f"M {x1:.2f} {y1:.2f} "
                f"A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} "
                f"L {x3:.2f} {y3:.2f} "
                f"A {r_in:.2f} {r_in:.2f} 0 {large} 0 {x4:.2f} {y4:.2f} Z")

    parts = []
    defs_parts = []  # textPath 需要的隐藏 path 定义

    # ---- 内环 + 外环扇形 ----
    ang = 0.0
    _outer_labels = []  # 收集外环 label 数据，后统一绘制（避免 defs 与 fill 顺序问题）
    for i, (dom, dpct, subs) in enumerate(data):
        d_from, d_to = ang, ang + dpct * 3.6
        # 内环 domain 扇形
        parts.append(
            f'<path d="{_arc_path(cx, cy, R_center, R_inner, d_from, d_to)}" '
            f'fill="{inner_colors[i]}" stroke="rgba(255,255,255,1)" stroke-width="1.5"/>'
        )
        # 内环文字：两行居中
        mid_ang = (d_from + d_to) / 2
        # 内环 domain 宽度判定：太窄就缩字号
        d_span = d_to - d_from
        if d_span >= 30:
            fs_domain = _fs_dom_wide
            fs_pct = _fs_pct_wide
        elif d_span >= 15:
            fs_domain = _fs_dom_mid
            fs_pct = _fs_pct_mid
        else:
            fs_domain = _fs_dom_narrow
            fs_pct = _fs_pct_narrow
        # 若名字触发两行拆分（&/空格 + 长），单行显示的是拆分后的更短片段；
        # 这里预取两行内容以正确估算最长行的半宽。
        _n_ascii = sum(1 for c in dom if ord(c) < 128)
        _n_cjk = len(dom) - _n_ascii
        _wt = _n_ascii + _n_cjk * 1.6
        _two_line = _wt > 12 and (' & ' in dom or ' ' in dom)
        if _two_line:
            _split_at = dom.rfind(' & ')
            if _split_at < 0:
                _mid = len(dom) // 2
                _left = dom.rfind(' ', 0, _mid + 3)
                _split_at = _left if _left > 0 else _mid
                _line1, _line2 = dom[:_split_at].strip(), dom[_split_at:].strip()
            else:
                _line1, _line2 = dom[:_split_at].strip(), dom[_split_at+3:].strip()
            _dom_widest = max(_line1, _line2, key=len)
        else:
            _line1, _line2 = dom, ""
            _dom_widest = dom
        # 迭代：如果按当前 fs_domain 找不到 text_r 让 label 既避开中心圆又不超 viewBox，
        # 就缩 fs_domain（步长 1.0）；下限 max(9, fs_pct)。
        _sn = abs(_m.sin(_m.radians(mid_ang)))
        _cs = abs(_m.cos(_m.radians(mid_ang)))
        # margin 需要能吸收 CJK 字宽估算误差（~5px 每几个字）+ baseline offset。
        # 之前用 3 → text bbox 与中心圆 AABB 常剩 1-2 像素 overlap 触发 embed_svg_text_shape_overlap。
        _margin = 8.0
        # text_r 落在 R_center → R_inner band 上，用 0.55 比例（偏内一点）：与
        # draw_nested_donut skeleton 一致，避免 label bbox 向外挤到 R_inner 边缘
        # 被视觉上覆盖。之前用 midpoint (0.5) 在 R_inner=0.60*R 上还行，但迁到
        # R_inner=0.72*R 后 midpoint 太靠内触中心圆；0.55 偏外一点点更稳。
        _text_r_default = R_center + (R_inner - R_center) * 0.55
        _vb_pad = 10.0  # 与 viewBox 生成用的 pad 保持一致
        _vb_left = -_vb_pad + 2.0
        _vb_right = width + _vb_pad - 2.0
        _vb_top = -_vb_pad + 2.0  # title 上方还有 _title_h 空间，这里保守只用 pad
        _vb_bot = height + _vb_pad - 2.0
        _fs_dom_floor = 9.0
        _fs_pct_ratio = fs_pct / max(1e-3, fs_domain)  # 保持 dom/pct 字号比例
        # 若两行拆分下最宽行仍太宽，允许收窄为一行 + 省略（保留 dom 关键前缀）。
        _dom_display = dom
        _dom_display_line1, _dom_display_line2 = _line1, _line2
        while True:
            _dom_half_w = 0.5 * _estimate_label_width_px(_dom_widest, fs_domain, bold=True, font_family=_body_font)
            _pct_half_w = 0.5 * _estimate_label_width_px(f"{dpct:.1f}%", fs_pct, bold=True, font_family=_body_font)
            _hw_est = max(_dom_half_w, _pct_half_w)
            # 垂直范围：ty 上方 = 最高一行到 ty 的距离 + 该行 fs*0.8；
            #         ty 下方 = 最低一行到 ty 的距离 + 该行 fs*0.3。
            if _two_line:
                _up_dist = fs_domain * 0.6 + fs_domain * 0.8  # line1 baseline 上方
                _down_dist = fs_domain * 0.55 + fs_pct + 2 + fs_pct * 0.3  # pct 行下方
            else:
                _up_dist = fs_domain * 0.8  # dom 行 baseline 之上
                _down_dist = fs_pct + 2 + fs_pct * 0.3  # pct 行下方
            _hh_est = max(_up_dist, _down_dist)
            # 需要的最小 text_r：让 x 或 y 至少一边跳出中心圆 AABB
            _cands = []
            if _sn > 1e-3:
                _cands.append((R_center + _hw_est + _margin) / _sn)
            if _cs > 1e-3:
                _cands.append((R_center + _hh_est + _margin) / _cs)
            _text_r_min = min(_cands) if _cands else (R_center + max(_hw_est, _hh_est) + _margin)
            # viewBox 上限：text_r 使得 tx±hw 和 ty±hh 都留在 viewBox 内。
            _r_cap = R_inner - fs_pct * 0.3  # 环带内
            # x 方向：cx + text_r*sin(a-90)*... 实际按 _polar，dx = r*cos(mid-90) = r*sin(mid)
            # sin(mid) 的符号决定 tx 相对 cx 的方向。用绝对值 + 两侧 padding 求上限。
            _dx_sign = _m.cos(_m.radians(mid_ang - 90))  # = sin(mid)
            _dy_sign = _m.sin(_m.radians(mid_ang - 90))  # = -cos(mid)
            if abs(_dx_sign) > 1e-3:
                if _dx_sign > 0:
                    _r_cap = min(_r_cap, (_vb_right - cx - _hw_est) / _dx_sign)
                else:
                    _r_cap = min(_r_cap, (cx - _vb_left - _hw_est) / (-_dx_sign))
            if abs(_dy_sign) > 1e-3:
                if _dy_sign > 0:
                    _r_cap = min(_r_cap, (_vb_bot - cy - _hh_est) / _dy_sign)
                else:
                    _r_cap = min(_r_cap, (cy - _vb_top - _hh_est) / (-_dy_sign))
            # 找 text_r：优先 default（annulus midpoint），若 default < min 就用 min，
            # 若 min > cap 说明当前 fs 装不下 → 缩字号重试。
            if _text_r_min <= max(_r_cap, _text_r_default):
                text_r = min(max(_r_cap, _text_r_default), max(_text_r_default, _text_r_min))
                break
            if fs_domain - 1.0 < _fs_dom_floor:
                # 已缩到下限；用 cap（保 viewBox 优先，允许中心圆轻微 overlap 也比 OOB 好）
                text_r = max(_r_cap, R_center + _margin)
                break
            fs_domain -= 1.0
            fs_pct = max(9.0, fs_domain * _fs_pct_ratio)
        tx, ty = _polar(cx, cy, text_r, mid_ang)
        # 渲染：两行拆分复用上面预算好的 _line1 / _line2，避免重复计算
        if _two_line:
            parts.append(
                f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty-fs_domain*0.6:.1f}" font-size="{fs_domain}" '
                f'font-weight="700" fill="rgba(255,255,255,1)" text-anchor="middle">{_xesc(_line1)}</text>'
            )
            parts.append(
                f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty+fs_domain*0.55:.1f}" font-size="{fs_domain}" '
                f'font-weight="700" fill="rgba(255,255,255,1)" text-anchor="middle">{_xesc(_line2)}</text>'
            )
            parts.append(
                f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty+fs_domain*0.55+fs_pct+2:.1f}" font-size="{fs_pct}" '
                f'font-weight="700" fill="rgba(255,255,255,0.9)" text-anchor="middle">{dpct:.1f}%</text>'
            )
        else:
            parts.append(
                f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty-1:.1f}" font-size="{fs_domain}" '
                f'font-weight="700" fill="rgba(255,255,255,1)" text-anchor="middle">{_xesc(dom)}</text>'
            )
            parts.append(
                f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty+fs_pct+2:.1f}" font-size="{fs_pct}" '
                f'font-weight="700" fill="rgba(255,255,255,0.9)" text-anchor="middle">{dpct:.1f}%</text>'
            )

        # 外环 sub-slices
        sub_ang = d_from
        for j, (sname, spct) in enumerate(subs):
            s_from, s_to = sub_ang, sub_ang + spct * 3.6
            parts.append(
                f'<path d="{_arc_path(cx, cy, R_inner, R_outer, s_from, s_to)}" '
                f'fill="{outer_lighten[i]}" stroke="rgba(255,255,255,1)" stroke-width="1"/>'
            )
            _outer_labels.append((sname, spct, s_from, s_to, i))
            sub_ang = s_to
        ang = d_to

    # ---- 外环文字：radial（少量 sub）或 leader line + 两侧竖排（多 sub / wide aspect）----
    # 触发外部 leader line 布局的条件：
    #   1) 总 sub-slice 数 > 8 —— 沿弧径向 label 会挤压
    #   2) wide aspect（w/h > 1.5）—— 右侧本来就有空间，顺手把 label 打到外面
    # 这两个条件在几何段已算好 _needs_leader / _leader_side_mode
    _use_leader = _needs_leader

    if not _use_leader:
        # 少量 sub-slice 且非 wide：走原径向 rotate 逻辑
        for k, (sname, spct, s_from, s_to, dom_idx) in enumerate(_outer_labels):
            span = s_to - s_from
            mid_ang = (s_from + s_to) / 2
            pct_str = f"{spct:.0f}%" if spct >= 1 else f"{spct:.1f}%"
            label_text = f"{_xesc(sname)} {pct_str}"

            if span >= 20:
                fs = _fs_sub_wide
            elif span >= 10:
                fs = _fs_sub_mid
            elif span >= 5:
                fs = _fs_sub_small
            else:
                fs = _fs_sub_tiny

            text_r = (R_inner + R_outer) / 2
            tx, ty = _polar(cx, cy, text_r, mid_ang)

            if 0 <= mid_ang < 180:
                rot = mid_ang - 90
            else:
                rot = mid_ang + 90

            parts.append(
                f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty:.1f}" font-size="{fs}" fill="rgba(40,40,40,0.9)" '
                f'font-weight="600" text-anchor="middle" dominant-baseline="middle" '
                f'transform="rotate({rot:.1f} {tx:.1f} {ty:.1f})">{label_text}</text>'
            )
    else:
        # ---- Leader-line 外部 label 布局 ----
        anchor_r = R_outer + 6  # 引线起点：外圈边缘外一点
        fs_leader = max(10.0, _fs_sub_small)
        line_h = fs_leader * 1.25

        # 按侧分组：mid_ang < 180 → 右侧 label；否则左侧
        right_group = []
        left_group  = []
        for k, (sname, spct, s_from, s_to, dom_idx) in enumerate(_outer_labels):
            span = s_to - s_from
            if span < 1.5:
                continue  # 极小 slice 省略
            mid_ang = (s_from + s_to) / 2
            ax, ay = _polar(cx, cy, anchor_r, mid_ang)
            pct_str = f"{spct:.0f}%" if spct >= 1 else f"{spct:.1f}%"
            label_text = f"{_xesc(sname)} {pct_str}"
            rec = {"name": label_text, "ax": ax, "ay": ay,
                   "mid": mid_ang, "dom_idx": dom_idx, "y": ay}
            if 0 <= mid_ang < 180:
                right_group.append(rec)
            else:
                left_group.append(rec)

        # tidy pass：按 y 排序后强制最小间距 line_h
        def _tidy(group, y_min, y_max):
            if not group:
                return
            group.sort(key=lambda r: r["ay"])
            for r in group:
                r["y"] = max(y_min, min(y_max, r["ay"]))
            for i in range(1, len(group)):
                if group[i]["y"] < group[i-1]["y"] + line_h:
                    group[i]["y"] = group[i-1]["y"] + line_h
            if group[-1]["y"] > y_max:
                group[-1]["y"] = y_max
                for i in range(len(group) - 2, -1, -1):
                    if group[i]["y"] > group[i+1]["y"] - line_h:
                        group[i]["y"] = group[i+1]["y"] - line_h

        y_min = cy - R_outer
        y_max = cy + R_outer
        _tidy(right_group, y_min, y_max)
        _tidy(left_group, y_min, y_max)

        # 引线转角 x（水平段起点）
        right_elbow_x = cx + R_outer + 12
        left_elbow_x  = cx - R_outer - 12
        # label 文字锚点 x
        right_label_x = cx + R_outer + 28
        left_label_x  = cx - R_outer - 28

        def _emit(group, label_x, elbow_x, anchor_side):
            text_anchor = "start" if anchor_side == "right" else "end"
            # Leader label 之前硬编码 fill="rgba(40,40,40,0.95)"（深灰），在深底 palette 上
            # 直接消失。改为跟 palette 挂钩：深底用 c_ink（palette 已为深底定义浅 ink），
            # 浅底沿用原深灰以保持对比。
            _leader_col = c_ink if _is_dark_palette(_pal) else "rgba(40,40,40,0.95)"
            # viewBox 右边界 = width + pad (pad=10, viewbox 起于 -pad)。
            # 每个 label 按可用宽度做 fit：先缩字号（floor 9），再截断加省略号，
            # 保证 x+width 不超过 viewBox 右边（左侧同理，从 -pad 起）。
            _vb_pad = 10.0
            _vb_right = width + _vb_pad
            _vb_left = -_vb_pad
            _margin = 2.0
            for r in group:
                ax = r["ax"]; ay = r["ay"]; ly = r["y"]
                text_dx = 4 if anchor_side == "right" else -4
                # 计算该 label 的可用宽度并 fit
                if anchor_side == "right":
                    avail = (_vb_right - _margin) - (label_x + text_dx)
                else:
                    avail = (label_x + text_dx) - (_vb_left + _margin)
                label_text = r["name"]
                label_fs = fs_leader
                if avail > 0:
                    label_text, label_fs = _fit_leader_label(
                        label_text, avail, fs_leader, _body_font,
                        bold=True, fs_floor=9.0,
                    )
                parts.append(
                    f'<polyline points="{ax:.1f},{ay:.1f} {elbow_x:.1f},{ly:.1f} '
                    f'{label_x + text_dx:.1f},{ly:.1f}" '
                    f'fill="none" stroke="{_rgba_with_alpha(c_ink, 0.35)}" stroke-width="0.8"/>'
                )
                parts.append(
                    f'<text font-family="{_body_font}" x="{label_x:.1f}" y="{ly + label_fs*0.35:.1f}" '
                    f'font-size="{label_fs}" fill="{_leader_col}" font-weight="600" '
                    f'text-anchor="{text_anchor}" dominant-baseline="alphabetic">{label_text}</text>'
                )

        _emit(right_group, right_label_x, right_elbow_x, "right")
        _emit(left_group, left_label_x, left_elbow_x, "left")

    # ---- 中心空心圆 + 总数 ----
    # 之前中心圆硬编码 fill=白，深底 palette 上 c_ink 是浅色 → 浅色文字盖在白圆上直接消失。
    # 改用 palette.bg 让"中心空心"和页面同色（视觉上真正"挖洞"），c_ink 文字在 bg 上一定对比。
    _center_fill = _pal.get("bg") or "rgba(255,255,255,1)"
    parts.append(
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R_center:.1f}" fill="{_center_fill}"/>'
    )
    if total_value is None:
        total_value = int(round(sum(d[1] for d in data)))
    # Fit the total value inside the center circle: long numbers (e.g. 1289456789)
    # would otherwise punch through the circle AABB and trip the OOB / text-shape
    # overlap detector. Use `_fit_center_label` for numeric-aware abbreviation
    # (1289456789 -> "1.29B") + fs shrink to fs_floor.
    # Available width: use the chord at ±fs*0.4 from cy (roughly the text's
    # vertical extent), which is slightly less than 2*R_center. Take 90% of the
    # inscribed diameter as a safety margin so the text stays clear of the ring.
    _center_avail_w = 2 * R_center * 0.9
    _total_str = _xesc(total_value)
    _total_str, _fs_center_val_fit = _fit_center_label(
        _total_str, _center_avail_w, _fs_center_val, _body_font,
        bold=True, fs_floor=max(12.0, _fs_center_val * 0.5),
    )
    parts.append(
        f'<text font-family="{_body_font}" x="{cx:.1f}" y="{cy-3:.1f}" font-size="{_fs_center_val_fit}" font-weight="800" '
        f'fill="{c_ink}" text-anchor="middle">{_total_str}</text>'
    )
    # total_label 单独拟合：letter-spacing .2em 会额外加宽 ~ (len-1) * 0.2 * fs。
    # _fit_center_label 与 _estimate_label_width_px 不认 letter-spacing，直接算出的宽度
    # 比 validator 用的 _svg_text_width 小一大截 → 通过 fit 但过不了 lint。
    # 修法：预先在 avail_w 里扣除 letter-spacing 的估算量，再调用 fit。
    _letter_spacing_em = 0.2
    _label_gaps = max(len(str(total_label)) - 1, 0)
    # 估算：假设收敛后的 fs ≈ _fs_center_lbl，先扣一次；不精确没关系，fit 内还会再缩。
    _ls_reserve = _label_gaps * _letter_spacing_em * _fs_center_lbl
    _center_label_avail_w = max(1.0, 2 * R_center * 0.85 - _ls_reserve)
    _label_str, _fs_center_lbl_fit = _fit_center_label(
        _xesc(total_label),
        _center_label_avail_w,
        _fs_center_lbl,
        _body_font,
        bold=True,
        fs_floor=8.0,
    )
    parts.append(
        f'<text font-family="{_body_font}" x="{cx:.1f}" y="{cy+_fs_center_val_fit*0.75:.1f}" font-size="{_fs_center_lbl_fit}" font-weight="700" '
        f'fill="{c_muted}" text-anchor="middle" letter-spacing=".2em">{_label_str}</text>'
    )

    defs_str = f"<defs>{''.join(defs_parts)}</defs>" if defs_parts else ""
    # 顶部标题栏（可选，向 y 负方向扩）
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    _title_block, _title_h = _render_title_block(
        x_left=0, anchor_y=-6, width=width,
        title=title, subtitle=subtitle, figure_label=figure_label,
        # 用 palette 解析的 c_ink（深底时是浅色），不是模块级 _INK（恒为深）
        ink=c_ink, muted=c_muted,
        body_font=_body_font, heading_font=_head_font,
    )
    body = defs_str + _title_block + "".join(parts)
    pad = 10.0
    vb_y = -pad - _title_h
    # viewBox 底部按实际内容收敛：donut 只用到 cy±R_outer；height 参数只是给
    # cx/cy/R_outer 的坐标基准，如果照原来的 vb_h=height+2*pad 会在 donut 下方
    # 留出 height/2 - (cy + R_outer) + pad 的空白（medium 4 domain + leader 布局
    # 下 R_outer=240，height=720，就是 ~130px 底部空白）。改用 cy + R_outer +
    # 少量 margin 作为内容底界，收窄 viewBox。
    _content_bot = cy + R_outer + pad
    vb_h = (_content_bot - vb_y)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.1f} {vb_y:.1f} {width + 2*pad:.1f} {vb_h:.1f}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)
