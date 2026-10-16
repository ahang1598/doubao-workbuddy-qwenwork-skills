"""Nested Donut · 5 variant 统一 API：
- donut_flat: 双层 donut，内 domain 深色 / 外 sub 浅色（同色系）
"""

from __future__ import annotations

import math

from .._common import (
    _INK,
    _derive_series_colors,
    _dispatch_to_svg_lib,
    _estimate_label_width_px,
    _pick_series_colors,
    _prepend_bg_if_dark,
    _render_title_block,
    _resolve_font,
    _resolve_palette,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from ._shared import (
    tr,
    auto_font_size,
    resolve_palette,
    rgb_tuple,
    svg_close,
    svg_open,
    xesc,
)


def _abbrev_number(n):
    """Abbreviate a numeric value to a compact 3-4 char label."""
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    absv = abs(v)
    sign = "-" if v < 0 else ""
    if absv >= 1e12:
        s = f"{absv / 1e12:.2f}T"
    elif absv >= 1e9:
        s = f"{absv / 1e9:.2f}B"
    elif absv >= 1e6:
        s = f"{absv / 1e6:.2f}M"
    elif absv >= 1e3:
        s = f"{absv / 1e3:.1f}K"
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
    """Fit a center total-value label into `max_width_px`."""
    if max_width_px <= 0 or not text:
        return text, fs
    s = str(text)
    if _estimate_label_width_px(s, fs, bold=bold, font_family=body_font) <= max_width_px:
        return s, fs
    stripped = s.lstrip("-").replace(".", "")
    is_numeric = stripped.isdigit()
    if is_numeric and len(s) >= 7:
        abbr = _abbrev_number(s)
        if _estimate_label_width_px(abbr, fs, bold=bold, font_family=body_font) <= max_width_px:
            return abbr, fs
        s = abbr  # keep shrinking on the abbreviated form
    cur_fs = fs
    while cur_fs - 1.0 >= fs_floor:
        cur_fs -= 1.0
        if _estimate_label_width_px(s, cur_fs, bold=bold, font_family=body_font) <= max_width_px:
            return s, cur_fs
    return s, max(fs_floor, cur_fs)


VARIANTS = (
    "donut_flat",
    "donut_gradient",
    "sunburst_flat",
    "polar_area_outlined",
    "donut_layered",
)


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
    if ang_to - ang_from >= 360 - 1e-9:
        # Two half-arcs represent an exact full circle; one 360° SVG arc has
        # coincident endpoints and disappears.
        x1, y1 = _polar(cx, cy, r_out, ang_from)
        x2, y2 = _polar(cx, cy, r_out, ang_from + 180)
        outer = f"M {x1:.2f} {y1:.2f} A {r_out:.2f} {r_out:.2f} 0 1 1 {x2:.2f} {y2:.2f} A {r_out:.2f} {r_out:.2f} 0 1 1 {x1:.2f} {y1:.2f} Z"
        if r_in <= 0.01:
            return outer
        x3, y3 = _polar(cx, cy, r_in, ang_from)
        x4, y4 = _polar(cx, cy, r_in, ang_from + 180)
        return (
            outer
            + f" M {x3:.2f} {y3:.2f} A {r_in:.2f} {r_in:.2f} 0 1 0 {x4:.2f} {y4:.2f} A {r_in:.2f} {r_in:.2f} 0 1 0 {x3:.2f} {y3:.2f} Z"
        )
    large = 1 if (ang_to - ang_from) > 180 else 0
    x1, y1 = _polar(cx, cy, r_out, ang_from)
    x2, y2 = _polar(cx, cy, r_out, ang_to)
    x3, y3 = _polar(cx, cy, r_in, ang_to)
    x4, y4 = _polar(cx, cy, r_in, ang_from)
    if r_in <= 0.01:
        return f"M {cx:.2f} {cy:.2f} L {x1:.2f} {y1:.2f} A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} Z"
    return (
        f"M {x1:.2f} {y1:.2f} "
        f"A {r_out:.2f} {r_out:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} "
        f"L {x3:.2f} {y3:.2f} "
        f"A {r_in:.2f} {r_in:.2f} 0 {large} 0 {x4:.2f} {y4:.2f} Z"
    )


def _sector_ink(color):
    r, g, b = rgb_tuple(color)
    return "rgba(28,28,26,1)" if 0.299 * r + 0.587 * g + 0.114 * b > 165 else "rgba(255,255,255,1)"


def _wrap_complete(text, width, fs, font):
    """Wrap without eliding category names or numerical values."""
    out = []
    rest = str(text)
    while rest:
        end = len(rest)
        while end > 1 and _estimate_label_width_px(rest[:end], fs, bold=True, font_family=font) > width:
            end -= 1
        if end < len(rest):
            space = rest.rfind(" ", 0, end + 1)
            if space > 0:
                end = space
        out.append(rest[:end].rstrip())
        rest = rest[end:].lstrip()
    return out or [""]


def _sector_label_layout(name, value, cx, cy, r_in, r_out, start, end, fs, font):
    """Fit all corners of a centered text block inside the actual annular sector."""
    mid = (start + end) / 2
    while fs >= 12:
        names = _wrap_complete(name, max(95.0, (r_out - r_in) * 1.55), fs, font)
        rows = [(line, fs) for line in names] + ([(value, max(11.0, fs * 0.82))] if value is not None else [])
        height = sum(size * 1.25 for _, size in rows)
        half_w = max(_estimate_label_width_px(line, size, bold=True, font_family=font) for line, size in rows) / 2 + 3
        half_h = height / 2 + 3
        for step in range(41):
            r = r_in + (r_out - r_in) * (0.25 + step * 0.0125)
            tx, ty = _polar(cx, cy, r, mid)
            dx, dy = tx - cx, ty - cy
            near = math.hypot(max(0, abs(dx) - half_w), max(0, abs(dy) - half_h))
            if near < r_in + 3:
                continue
            corners = [(dx + sx * half_w, dy + sy * half_h) for sx in (-1, 1) for sy in (-1, 1)]
            if any(math.hypot(x, y) > r_out - 3 for x, y in corners):
                continue
            if end - start < 359.99 and any(
                (math.degrees(math.atan2(y, x)) + 90 - start) % 360 > end - start for x, y in corners
            ):
                continue
            baseline = ty - height / 2
            placed = []
            for line, size in rows:
                baseline += size
                placed.append((tx, baseline, line, size))
                baseline += size * 0.25
            return placed
        fs -= 0.5
    return None


def _complete_leaders(entries, cx, cy, radius, font, ink, fs=14.0, wrap=220):
    """Place complete labels on exterior tracks, preserving real sector anchors."""
    parts, bounds = [], [cx - radius, cy - radius, cx + radius, cy + radius]
    for side in (-1, 1):
        records = []
        for label, start, end, anchor_r in entries:
            mid = (start + end) / 2
            if (1 if math.sin(math.radians(mid)) >= 0 else -1) != side:
                continue
            ax, ay = _polar(cx, cy, anchor_r, mid)
            rx, ry = _polar(cx, cy, radius + 10, mid)
            lines = _wrap_complete(label, wrap / 1.1, fs, font)
            records.append([ry, ax, ay, rx, ry, lines])
        records.sort(key=lambda rec: rec[0])
        total_h = sum(len(rec[-1]) * fs * 1.4 + 10 for rec in records)
        cursor = min(cy - radius, cy - total_h / 2)
        label_x = cx + side * (radius + 46)
        for desired, ax, ay, rx, ry, lines in records:
            block_h = len(lines) * fs * 1.4
            top = max(cursor, desired - block_h / 2)
            center = top + block_h / 2
            elbow = cx + side * (radius + 26)
            end_x = label_x - side * 8
            parts.append(
                f'<polyline points="{ax:.1f},{ay:.1f} {rx:.1f},{ry:.1f} {elbow:.1f},{center:.1f} {end_x:.1f},{center:.1f}" '
                f'fill="none" stroke="{_rgba_with_alpha(ink, 0.45)}" stroke-width="0.9"/>'
            )
            for i, line in enumerate(lines):
                y = top + fs + i * fs * 1.4
                parts.append(
                    f'<text x="{label_x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{fs}" '
                    f'font-weight="600" fill="{ink}" text-anchor="{"start" if side > 0 else "end"}">{_xesc(line)}</text>'
                )
                tw = _estimate_label_width_px(line, fs, bold=True, font_family=font) * 1.1 + fs * 0.3
                bounds[0] = min(bounds[0], label_x - (tw if side < 0 else 0))
                bounds[2] = max(bounds[2], label_x + (tw if side > 0 else 0))
            bounds[1] = min(bounds[1], top)
            bounds[3] = max(bounds[3], top + block_h)
            cursor = top + block_h + 10
    return parts, bounds


def _render_leader_labels(
    cx,
    cy,
    R_ref,
    entries,
    ink,
    body_font,
    fs=10.0,
    min_span=1.5,
    viewbox_x=0.0,
    viewbox_w=None,
    margin=2.0,
    *,
    bounds_out=None,
    extra_entries=(),
):
    """Place all labels, including tiny sectors, on complete exterior tracks."""
    # Preserve the private calling convention used by the existing variants.
    from html import unescape

    leaders = [(unescape(entry[0]), entry[1], entry[2], entry[3] if len(entry) > 3 else R_ref) for entry in entries]
    fragments, bounds = _complete_leaders(leaders + list(extra_entries), cx, cy, R_ref, body_font, ink, max(12.0, fs))
    if bounds_out is not None:
        bounds_out[0] = min(bounds_out[0], bounds[0])
        bounds_out[1] = min(bounds_out[1], bounds[1])
        bounds_out[2] = max(bounds_out[2], bounds[2])
        bounds_out[3] = max(bounds_out[3], bounds[3])
    return fragments


def draw_nested_donut(
    data: dict,
    variant: str = "donut_flat",
    palette="archive_ink",
    width: float = 720,
    height: float = 720,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {VARIANTS}")

    segments = data.get("segments") or []
    if not segments:
        raise ValueError("nested_donut: at least one segment required")
    total_label = data.get("total_label", tr("TOTAL"))
    total_value = data.get("total_value")

    pal = resolve_palette(palette)
    ink, _ink6 = pal["ink"], pal["ink6"]
    bg = pal["bg"]
    series = _pick_series_colors(pal, max(6, len(segments)))

    body_font = "Inter, sans-serif"
    head_font = "Georgia, serif"

    dom_total = sum(v for _, v, _ in segments) or 1.0
    if total_value is None:
        total_value = dom_total

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
    _use_layered_shadow = variant == "donut_layered"

    if variant == "donut_gradient":
        for i, col in enumerate(series[: len(segments)]):
            r, g, b = rgb_tuple(col)
            defs_parts.append(
                f'<radialGradient id="ndg_{i}" cx="50%" cy="50%" r="65%">'
                f'<stop offset="0%" stop-color="rgba({min(255, r + 40)},{min(255, g + 40)},{min(255, b + 40)},1)"/>'
                f'<stop offset="100%" stop-color="rgba({max(0, r - 30)},{max(0, g - 30)},{max(0, b - 30)},1)"/>'
                f"</radialGradient>"
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

    leader_bounds = [0.0, 0.0, float(width), 0.0]
    domain_layouts = []
    external_domains = []
    if variant != "polar_area_outlined":
        r_in, r_out = (R_l1_in, R_l1_out) if variant == "sunburst_flat" else (R_center, R_inner)
        angle = 0.0
        for dom, value, subs in segments:
            end = angle + value / dom_total * 360
            suffix = None if variant == "sunburst_flat" else f"{value / dom_total * 100:.1f}%"
            placed = _sector_label_layout(dom, suffix, cx, cy, r_in, r_out, angle, end, 14, body_font)
            domain_layouts.append(placed)
            if placed is None:
                external_domains.append((str(dom) + (f" · {suffix}" if suffix else ""), angle, end, (r_in + r_out) / 2))
            outer_band = R_l2_out - R_l1_out if variant == "sunburst_flat" else R_outer - R_inner
            if any(
                _estimate_label_width_px(f"{name} {val:g}", 12, bold=True, font_family=body_font) > outer_band - 10
                for name, val in subs
            ):
                _needs_leader = True
            if any(val / (sum(v for _, v in subs) or 1) * (end - angle) < 5 for _, val in subs):
                _needs_leader = True
            angle = end
        _needs_leader = _needs_leader or bool(external_domains)

    filter_attr = ""  # 已改用 shadow_dup pattern（下方 translate 副本），不再走 SVG filter

    if variant == "sunburst_flat":
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{R_center}" fill="{ink}"/>')
        _fs_center_val = max(14, R_center * 0.42)
        parts.append(
            f'<text x="{cx}" y="{cy - 2:.1f}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{_fs_center_val:.0f}" font-weight="800" fill="{bg}">'
            f"{total_value:g}</text>"
        )
        parts.append(
            f'<text x="{cx}" y="{cy + _fs_center_val * 0.75:.1f}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{max(9, R_center * 0.22):.0f}" font-weight="700" fill="{bg}" '
            f'letter-spacing=".18em">'
            f"{xesc(total_label)}</text>"
        )
        ang = 0.0
        _sunburst_leader_entries = []  # collect (label_text, s_from, s_to) for leader-line pass
        for i, (dom, dpct, subs) in enumerate(segments):
            d_from = ang
            d_to = ang + dpct / dom_total * 360
            base = series[i % len(series)]
            parts.append(
                f'<path d="{_arc_path(cx, cy, R_l1_in, R_l1_out, d_from, d_to)}" '
                f'fill="{base}" stroke="{bg}" stroke-width="1.5"/>'
            )
            if domain_layouts[i] is not None:
                for tx, ty, label, label_fs in domain_layouts[i]:
                    parts.append(
                        f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-family="{body_font}" '
                        f'font-size="{label_fs}" font-weight="700" fill="{_sector_ink(base)}">{xesc(label)}</text>'
                    )
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
                    _sunburst_leader_entries.append((xesc(sname), s_from, s_to))
                    sa = s_to
                    continue
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
                    f'fill="{_sector_ink(lc)}" dominant-baseline="middle" '
                    f'transform="rotate({rot:.1f} {tx2:.1f} {ty2:.1f})">{xesc(sname)}</text>'
                )
                sa = s_to
            ang = d_to

        if _needs_leader and _sunburst_leader_entries:
            parts.extend(
                _render_leader_labels(
                    cx,
                    cy,
                    R_l2_out,
                    _sunburst_leader_entries,
                    ink=ink,
                    body_font=body_font,
                    fs=10.0,
                    viewbox_x=0.0,
                    viewbox_w=width,
                    bounds_out=leader_bounds,
                    extra_entries=external_domains,
                )
            )

    elif variant == "polar_area_outlined":
        subs_flat = []
        for i, (dom, dpct, subs) in enumerate(segments):
            for j, (sname, sval) in enumerate(subs):
                subs_flat.append((sname, sval, i))
        if not subs_flat:
            subs_flat = [(d[0], d[1], i) for i, d in enumerate(segments)]
        n_wedges = len(subs_flat)
        _needs_leader = _needs_leader or any(
            _estimate_label_width_px(f"{name} {val:g}", 12, bold=True, font_family=body_font) > 90
            for name, val, _ in subs_flat
        )
        R_max = R - 30
        max_val = max(s[1] for s in subs_flat) or 1
        ang_step = 360.0 / n_wedges
        for k in (0.25, 0.5, 0.75, 1.0):
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{R_max * k:.1f}" fill="none" '
                f'stroke="{_rgba_with_alpha(ink, 0.15)}" stroke-width="0.6" stroke-dasharray="3 3"/>'
            )
        for k, (sname, sval, di) in enumerate(subs_flat):
            a_from = k * ang_step
            a_to = a_from + ang_step * 0.9
            r_out = math.sqrt(4**2 + (R_max**2 - 4**2) * sval / max_val)
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
        if _needs_leader:
            # 走 leader-line：两侧竖排 label，避免切向文字挤压
            _entries = []
            for k, (sname, sval, di) in enumerate(subs_flat):
                a_from = k * ang_step
                a_to = a_from + ang_step * 0.9
                _entries.append(
                    (f"{xesc(sname)} {sval:g}", a_from, a_to, math.sqrt(4**2 + (R_max**2 - 4**2) * sval / max_val))
                )
            parts.extend(
                _render_leader_labels(
                    cx,
                    cy,
                    R_max,
                    _entries,
                    ink=ink,
                    body_font=body_font,
                    fs=float(fs),
                    viewbox_x=0.0,
                    viewbox_w=width,
                    bounds_out=leader_bounds,
                    extra_entries=external_domains,
                )
            )
        else:
            for k, (sname, sval, di) in enumerate(subs_flat):
                a_from = k * ang_step
                a_to = a_from + ang_step * 0.9
                r_out = math.sqrt(4**2 + (R_max**2 - 4**2) * sval / max_val)
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
        # Keep the total outside the radial data, whose sectors meet at the
        # origin. Covering their centre also hides their quantitative area.
        parts.append(
            f'<text x="{width - 40:.1f}" y="82" text-anchor="end" font-family="{body_font}" '
            f'font-size="14" font-weight="600" fill="{ink}">{xesc(total_label)} · {total_value:g}</text>'
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
            for i, dom, iw in row:
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
        ang = 0.0
        outer_labels = []
        for i, (dom, dpct, subs) in enumerate(segments):
            d_from, d_to = ang, ang + dpct / dom_total * 360
            base = series[i % len(series)]
            inner_fill = f"url(#ndg_{i})" if variant == "donut_gradient" else base
            outer_fill = _lighten(base, 0.5)
            inner_d = _arc_path(cx, cy, R_center, R_inner, d_from, d_to)
            if _use_layered_shadow:
                parts.append(
                    f'<path d="{inner_d}" transform="translate(3,5)" fill="{ink}" fill-opacity="0.25" stroke="none"/>'
                )
            parts.append(f'<path d="{inner_d}" fill="{inner_fill}" stroke="{bg}" stroke-width="1.5"{filter_attr}/>')
            if domain_layouts[i] is not None:
                for tx, ty, label, label_fs in domain_layouts[i]:
                    parts.append(
                        f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-family="{body_font}" '
                        f'font-size="{label_fs}" font-weight="700" fill="{_sector_ink(base)}">{xesc(label)}</text>'
                    )
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
                parts.append(f'<path d="{outer_d}" fill="{outer_fill}" stroke="{bg}" stroke-width="1"{filter_attr}/>')
                outer_labels.append((sname, sval, s_from, s_to, i))
                sub_ang = s_to
            ang = d_to

        # 外环标签 —— 走 leader-line（>8 sub 或 wide）或径向 rotate
        if _needs_leader:
            _entries = [(f"{xesc(sname)} {sval:g}", s_from, s_to) for (sname, sval, s_from, s_to, di) in outer_labels]
            parts.extend(
                _render_leader_labels(
                    cx,
                    cy,
                    R_outer,
                    _entries,
                    ink=ink,
                    body_font=body_font,
                    fs=10.0,
                    viewbox_x=0.0,
                    viewbox_w=width,
                    bounds_out=leader_bounds,
                    extra_entries=external_domains,
                )
            )
        else:
            # 极小 slice（span<5°）省略 label；相邻 label 角度差过小时交替径向偏移防压叠
            prev_visible_mid = None
            prev_offset = 0
            for sname, sval, s_from, s_to, di in outer_labels:
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
                    f'fill="{_sector_ink(_lighten(series[di % len(series)], 0.5))}" dominant-baseline="middle" '
                    f'transform="rotate({rot:.1f} {tx:.1f} {ty:.1f})">'
                    f"{xesc(sname)} {sval:g}</text>"
                )

        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{R_center}" fill="{bg}" '
            f'stroke="{_rgba_with_alpha(ink, 0.15)}" stroke-width="0.8"/>'
        )
        fs_total_val = max(16, R_center * 0.35)
        parts.append(
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="{fs_total_val:.0f}" font-weight="700" fill="{ink}">'
            f"{total_value:g}</text>"
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-family="{body_font}" '
            f'font-size="10" font-weight="700" fill="{pal["muted"]}" '
            f'letter-spacing=".18em">{xesc(total_label)}</text>'
        )

    if defs_parts:
        defs_str = "<defs>" + "".join(defs_parts) + "</defs>"
        parts.insert(1, defs_str)

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
    vb_x = min(0.0, leader_bounds[0] - 8)
    vb_y = min(0.0, leader_bounds[1] - 8)
    vb_right = max(float(width), leader_bounds[2] + 8)
    vb_bottom = max(min(height, max(_content_bot, cy + 20)), leader_bounds[3] + 8)
    parts[0] = svg_open(vb_x, vb_y, vb_right - vb_x, vb_bottom - vb_y, bg=bg)

    parts.append(svg_close())
    return "".join(parts)


def make_nested_donut(
    data,
    total_label: str = "TOTAL",
    total_value=None,
    width: float = 720.0,
    height: float = 720.0,
    domain_colors: dict | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    font_family: str | None = None,
    palette: dict | None = None,
    variant: str | None = None,
) -> str:
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
    if not _variant_is_classic("nested_donut", variant):
        _data = {"segments": list(data), "total_label": total_label}
        if total_value is not None:
            _data["total_value"] = total_value
        return _dispatch_to_svg_lib(
            "nested_donut",
            variant,
            _data,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            palette=palette,
            font_family=font_family,
            width=width,
            height=height,
        )

    if not data:
        raise ValueError("nested_donut: at least one domain required")
    for i, d in enumerate(data):
        if len(d) < 3:
            raise ValueError(f"nested_donut: data[{i}] must be (domain, pct, subs), got {d}")

    from ._shared import _rgba_with_alpha  # regex form (not _common's); shadows the module import here

    def _rgb_tuple(rgba_str):
        import re as _re

        m = _re.match(r"\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", rgba_str)
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
    c_ink = _pal.get("ink", _INK)
    c_muted = _pal.get("muted", _rgba_with_alpha(c_ink, 0.5))
    # 从 palette 派生系列色（先看 palette["series"]，否则从 accent 做 hue-shift 派生 n 色）
    # nested_donut 需要至少 8 个系列色（domain 轮转）
    _default_colors = _pal.get("domain_default_colors") or _derive_series_colors(_pal, max(8, len(data)))

    dc = dict(domain_colors) if domain_colors else {}
    inner_colors = []
    outer_lighten = []
    for i, (dom, _pct, _subs) in enumerate(data):
        base = dc.get(dom) or _default_colors[i % len(_default_colors)]
        inner_colors.append(base)
        outer_lighten.append(_lighten(base, 0.5))

    # Wide aspect (w/h > 1.5): 缩小 donut 半径（用 height 主导），donut 靠左 30% 位置，
    # 留右侧较大宽度做外部 leader label；左侧也留够 label reserve，避免左半 wedge label 无处放。
    # Tall aspect / 方形: 居中；若 sub-slice 数 > 8 也要外部 label，此时收缩半径为标签让位
    _aspect = float(width) / float(height) if height else 1.0
    _wide = _aspect > 1.5
    _n_subs_total = sum(len(d[2]) for d in data)
    _needs_leader = (_n_subs_total > 8) or _wide
    _label_reserve = 90.0 if _needs_leader else 0.0
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
    _fs_dom_wide = max(14.0, _fs_base * 1.2 * _fs_dom_mult)  # domain wide arcs
    _fs_sub_wide = max(13.0, _fs_base * 1.15 * _fs_sub_mult)
    _fs_center_val = max(30.0, _fs_base * 2.6)
    _fs_center_lbl = max(12.0, _fs_base * 1.0)

    for _fit_pass in range(10):
        R_inner = R_outer * 0.72  # 内环拓宽，为两行 label 让空间
        R_center = R_outer * 0.30
        parts = []
        defs_parts = []  # textPath 需要的隐藏 path 定义

        ang = 0.0
        external_domains = []
        leader_bounds = [cx - R_outer, cy - R_outer, cx + R_outer, cy + R_outer]
        _outer_labels = []  # 收集外环 label 数据，后统一绘制（避免 defs 与 fill 顺序问题）
        for i, (dom, dpct, subs) in enumerate(data):
            d_from, d_to = ang, ang + dpct * 3.6
            parts.append(
                f'<path d="{_arc_path(cx, cy, R_center, R_inner, d_from, d_to)}" '
                f'fill="{inner_colors[i]}" stroke="rgba(255,255,255,1)" stroke-width="1.5"/>'
            )
            r, g, b = _rgb_tuple(inner_colors[i])
            inner_ink = "rgba(28,28,26,1)" if 0.299 * r + 0.587 * g + 0.114 * b > 165 else "rgba(255,255,255,1)"
            placed = _sector_label_layout(
                dom, f"{dpct:.1f}%", cx, cy, R_center, R_inner, d_from, d_to, _fs_dom_wide, _body_font
            )
            if placed is None:
                external_domains.append((f"{dom} · {dpct:.1f}%", d_from, d_to, (R_center + R_inner) / 2))
            else:
                for tx, ty, label, label_fs in placed:
                    parts.append(
                        f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty:.1f}" font-size="{label_fs}" '
                        f'font-weight="700" fill="{inner_ink}" text-anchor="middle">{_xesc(label)}</text>'
                    )

            sub_ang = d_from
            for j, (sname, spct) in enumerate(subs):
                s_from, s_to = sub_ang, sub_ang + spct * 3.6
                # Sibling sub-slices step through lighter tints of their domain color so they stay distinguishable.
                tint = (
                    outer_lighten[i] if len(subs) == 1 else _lighten(inner_colors[i], 0.28 + 0.44 * j / (len(subs) - 1))
                )
                parts.append(
                    f'<path d="{_arc_path(cx, cy, R_inner, R_outer, s_from, s_to)}" '
                    f'fill="{tint}" stroke="rgba(255,255,255,1)" stroke-width="1"/>'
                )
                _outer_labels.append((sname, spct, s_from, s_to, i))
                sub_ang = s_to
            ang = d_to

        # A radial outer label needs room both along the annulus and across its
        # wedge. If any label needs a rail, put all outer labels on shared tracks.
        outer_layout = []
        use_leaders = _needs_leader or bool(external_domains)
        for sname, spct, start, end, dom_idx in _outer_labels:
            value = f"{spct:g}%"
            label = f"{sname} {value}"
            fs = _fs_sub_wide
            while (
                fs > 12
                and _estimate_label_width_px(label, fs, bold=True, font_family=_body_font) > R_outer - R_inner - 12
            ):
                fs -= 0.5
            mid_r = (R_inner + R_outer) / 2
            if (
                _estimate_label_width_px(label, fs, bold=True, font_family=_body_font) > R_outer - R_inner - 12
                or math.radians(end - start) * R_inner < fs * 1.5
            ):
                use_leaders = True
            outer_layout.append((label, start, end, fs, mid_r))
        if use_leaders:
            entries = external_domains + [(label, start, end, R_outer) for label, start, end, _, _ in outer_layout]
            fragments, leader_bounds = _complete_leaders(
                entries, cx, cy, R_outer, _body_font, c_ink, wrap=220 if width >= 700 else max(60.0, width * 0.2)
            )
            parts.extend(fragments)
        else:
            for label, start, end, fs, text_r in outer_layout:
                mid = (start + end) / 2
                tx, ty = _polar(cx, cy, text_r, mid)
                rot = mid - 90 if 0 <= mid < 180 else mid + 90
                parts.append(
                    f'<text font-family="{_body_font}" x="{tx:.1f}" y="{ty:.1f}" font-size="{fs}" '
                    f'fill="rgba(40,40,40,0.95)" font-weight="600" text-anchor="middle" dominant-baseline="middle" '
                    f'transform="rotate({rot:.1f} {tx:.1f} {ty:.1f})">{_xesc(label)}</text>'
                )

        # 之前中心圆硬编码 fill=白，深底 palette 上 c_ink 是浅色 → 浅色文字盖在白圆上直接消失。
        # 改用 palette.bg 让"中心空心"和页面同色（视觉上真正"挖洞"），c_ink 文字在 bg 上一定对比。
        _center_fill = _pal.get("bg") or "rgba(255,255,255,1)"
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R_center:.1f}" fill="{_center_fill}"/>')
        if total_value is None:
            total_value = round(sum(d[1] for d in data))
        # Fit the total value inside the center circle: long numbers (e.g. 1289456789) would otherwise punch through the
        # circle AABB and trip the OOB / text-shape overlap detector.
        _center_avail_w = 2 * R_center * 0.9
        _total_str = _xesc(total_value)
        _total_str, _fs_center_val_fit = _fit_center_label(
            _total_str,
            _center_avail_w,
            _fs_center_val,
            _body_font,
            bold=True,
            fs_floor=max(12.0, _fs_center_val * 0.5),
        )
        parts.append(
            f'<text font-family="{_body_font}" x="{cx:.1f}" y="{cy - 3:.1f}" font-size="{_fs_center_val_fit}" font-weight="800" '
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
            fs_floor=11.0,
        )
        parts.append(
            f'<text font-family="{_body_font}" x="{cx:.1f}" y="{cy + _fs_center_val_fit * 0.75:.1f}" font-size="{_fs_center_lbl_fit}" font-weight="700" '
            f'fill="{c_ink}" fill-opacity="0.72" text-anchor="middle" letter-spacing=".2em">{_label_str}</text>'
        )

        defs_str = f"<defs>{''.join(defs_parts)}</defs>" if defs_parts else ""
        # 顶部标题栏（可选，向 y 负方向扩）
        c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
        _title_block, _title_h = _render_title_block(
            x_left=0,
            anchor_y=-6,
            width=width,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            subtitle_font_size=11,
            figure_font_size=11,
            # 用 palette 解析的 c_ink（深底时是浅色），不是模块级 _INK（恒为深）
            ink=c_ink,
            muted=c_muted,
            body_font=_body_font,
            heading_font=_head_font,
        )
        body = defs_str + _title_block + "".join(parts)
        pad = 10.0
        vb_y = min(-pad - _title_h if _title_block else cy - R_outer - pad, leader_bounds[1] - pad)
        # viewBox 底部按实际内容收敛：donut 只用到 cy±R_outer；height 参数只是给
        # cx/cy/R_outer 的坐标基准，如果照原来的 vb_h=height+2*pad 会在 donut 下方
        # 留出 height/2 - (cy + R_outer) + pad 的空白（medium 4 domain + leader 布局
        # 下 R_outer=240，height=720，就是 ~130px 底部空白）。改用 cy + R_outer +
        # 少量 margin 作为内容底界，收窄 viewBox。
        _content_bot = max(cy + R_outer, leader_bounds[3]) + pad
        vb_h = _content_bot - vb_y
        _x0 = min(0.0, leader_bounds[0])
        vb_x, vb_w = _x0 - pad, max(leader_bounds[2], _x0 + width) - _x0 + 2 * pad
        _over = max(vb_w - width - 2 * pad, vb_h - height - 2 * pad)
        if _over <= 1 or R_outer <= 40:
            break
        R_outer = max(40.0, R_outer - _over / 2 - 0.5)
    _svg_result = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}">{body}</svg>'
    )
    return _prepend_bg_if_dark(_svg_result, _pal)
