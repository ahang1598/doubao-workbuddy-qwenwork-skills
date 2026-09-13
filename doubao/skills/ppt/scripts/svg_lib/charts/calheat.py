"""svg_lib/charts/calheat.py

Calendar heat map with 5 layout variants:
  default_row_52x7 / monthly_grid_12x31 / small_multiples / radial_year / dot_grid

Data schema
-----------
data = {
    "values": [365 floats],   # daily values; if len < 365, padded with 0
    "year": int,              # calendar year (used for weekday alignment / month length)
    "kpis"?: [(header, big, sub)],   # optional 3 KPIs shown near the top
}

Values <= 0 are drawn as "empty" (very faint), positive values ramp toward accent color.
"""
from __future__ import annotations
import math
import calendar
from ._shared import (

    resolve_palette, is_dark_palette, xesc,
    rgb_tuple, _rgba_with_alpha,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _darken_rgba, _lighten_rgba, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
_VARIANTS = {
    "default_row_52x7",
    "monthly_grid_12x31",
    "small_multiples",
    "radial_year",
    "dot_grid",
}

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_LABELS_FULL = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def draw_calheat(
    data: dict,
    variant: str = "default_row_52x7",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = None,
    title: str = None,
    subtitle: str = None,
) -> str:
    """Render a calendar heat map SVG."""
    if variant not in _VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {sorted(_VARIANTS)}")

    values = list(data.get("values") or [])
    year = int(data.get("year") or 2025)
    # Pad or truncate to 365 (or 366 for leap year)
    n_days = 366 if calendar.isleap(year) else 365
    if len(values) < n_days:
        values = values + [0.0] * (n_days - len(values))
    values = values[:n_days]

    kpis = data.get("kpis")
    if kpis is None:
        total = int(sum(values))
        active = sum(1 for v in values if v > 0)
        peak = int(max(values)) if values else 0
        kpis = [
            ("TOTAL", f"{total:,}", "activity"),
            ("ACTIVE DAYS", f"{active}", f"of {n_days}"),
            ("PEAK", f"{peak}", "single day"),
        ]

    pal = resolve_palette(palette)
    ink = pal["ink"]; accent = pal["accent"]; bg = pal["bg"]
    muted = pal["muted"]
    ink4 = pal["ink4"]; ink2 = pal["ink2"]
    dark = is_dark_palette(pal)

    accent_rgb = rgb_tuple(accent)
    ink_rgb = rgb_tuple(ink)
    bg_rgb = rgb_tuple(bg)
    bg_luma = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]

    vmax = max(values) if any(v > 0 for v in values) else 1.0

    def val_color(v):
        """Map v to a color; v=0 → faint, v=vmax → accent."""
        if v <= 0:
            a = 0.10 if bg_luma > 100 else 0.14
            return _rgba_with_alpha(ink, a)
        t = min(1.0, v / vmax)
        # For light bg: blend from light-tint of accent → accent
        # For dark bg: blend from dark base (bg + ink) → accent
        ar, ag, ab = accent_rgb
        if bg_luma < 100:
            base_r, base_g, base_b = 40, 40, 44
        else:
            base_r = int(ar + (255 - ar) * 0.82)
            base_g = int(ag + (255 - ag) * 0.82)
            base_b = int(ab + (255 - ab) * 0.82)
        r = base_r + (ar - base_r) * t
        g = base_g + (ag - base_g) * t
        b = base_b + (ab - base_b) * t
        if t > 0.85:
            r *= 0.9; g *= 0.9; b *= 0.9
        return f"rgb({int(r)},{int(g)},{int(b)})"

    body_font = "Inter, 'PingFang SC', sans-serif"
    head_font = "Georgia, serif"

    W = float(width)

    if variant == "default_row_52x7":
        H = float(height) if height else 480.0
        return _render_row_52x7(W, H, values, year, title, subtitle, kpis,
                                ink, accent, bg, muted, ink4, ink2,
                                val_color, body_font, head_font, vmax, bg_luma)
    if variant == "dot_grid":
        H = float(height) if height else 480.0
        return _render_row_52x7(W, H, values, year, title, subtitle, kpis,
                                ink, accent, bg, muted, ink4, ink2,
                                val_color, body_font, head_font, vmax, bg_luma,
                                use_dot=True)
    if variant == "monthly_grid_12x31":
        H = float(height) if height else 680.0
        return _render_monthly_grid(W, H, values, year, title, subtitle, kpis,
                                    ink, accent, bg, muted, ink4, ink2,
                                    val_color, body_font, head_font, vmax, bg_luma)
    if variant == "small_multiples":
        H = float(height) if height else 700.0
        return _render_small_multiples(W, H, values, year, title, subtitle, kpis,
                                       ink, accent, bg, muted, ink4, ink2,
                                       val_color, body_font, head_font, vmax, bg_luma)
    if variant == "radial_year":
        H = float(height) if height else 900.0
        return _render_radial(W, H, values, year, title, subtitle, kpis,
                              ink, accent, bg, muted, ink4, ink2,
                              val_color, body_font, head_font, vmax, bg_luma)

    return ""


# ============================================================
# Helper: fill in date -> position maps
# ============================================================
def _doy_to_md(doy, year=2025):
    """doy: 0-based (0..364/365). Returns (month_idx 0..11, day-of-month 1..31)."""
    d = doy + 1
    for m in range(1, 13):
        dim = calendar.monthrange(year, m)[1]
        if d <= dim:
            return m - 1, d
        d -= dim
    return 11, calendar.monthrange(year, 12)[1]


def _title_block(x, y_top, w, title, subtitle, ink, muted,
                 body_font, head_font):
    parts = []
    if title:
        parts.append(
            f'<text x="{x:.1f}" y="{y_top:.1f}" font-family="{head_font}" '
            f'font-size="22" font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
    if subtitle:
        parts.append(
            f'<text x="{x:.1f}" y="{y_top + 20:.1f}" font-family="{body_font}" '
            f'font-size="12" fill="{muted}" letter-spacing="0.10em">{xesc(subtitle)}</text>'
        )
    if title or subtitle:
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_top + 32:.1f}" x2="{x + w:.1f}" y2="{y_top + 32:.1f}" '
            f'stroke="{ink}" stroke-width="0.7"/>'
        )
    return parts


def _kpi_row(x, y, avail_w, kpis, ink, muted, accent, bg, ink4,
             body_font, head_font, scale=1.0):
    parts = []
    if not kpis:
        return parts
    kpi_h = 54.0 * scale
    gap = 16.0
    n = len(kpis)
    kw = (avail_w - gap * (n - 1)) / n
    head_fs = 9.5 * scale
    big_fs = 20 * scale
    sub_fs = 9.5 * scale
    for i, (head, big, sub) in enumerate(kpis):
        kx = x + i * (kw + gap)
        parts.append(
            f'<rect x="{kx:.1f}" y="{y:.1f}" width="{kw:.1f}" height="{kpi_h:.1f}" '
            f'fill="{_rgba_with_alpha(ink, 0.02)}" stroke="{ink4}" stroke-width="0.7"/>'
        )
        parts.append(
            f'<rect x="{kx:.1f}" y="{y:.1f}" width="3" height="{kpi_h:.1f}" fill="{accent}"/>'
        )
        parts.append(
            f'<text x="{kx + 12:.1f}" y="{y + 16 * scale:.1f}" font-family="{body_font}" '
            f'font-size="{head_fs:.1f}" fill="{muted}" font-weight="600" letter-spacing="0.14em">'
            f'{xesc(head)}</text>'
        )
        parts.append(
            f'<text x="{kx + 12:.1f}" y="{y + 38 * scale:.1f}" font-family="{head_font}" '
            f'font-size="{big_fs:.1f}" fill="{ink}" font-weight="700">{xesc(big)}</text>'
        )
        parts.append(
            f'<text x="{kx + 12:.1f}" y="{y + 50 * scale:.1f}" font-family="{body_font}" '
            f'font-size="{sub_fs:.1f}" fill="{muted}">{xesc(sub)}</text>'
        )
    return parts


# ============================================================
# 52x7 row / dot_grid (unified renderer)
# ============================================================
def _render_row_52x7(W, H, values, year, title, subtitle, kpis,
                     ink, accent, bg, muted, ink4, ink2,
                     val_color, body_font, head_font, vmax, bg_luma,
                     use_dot=False):
    MARGIN_L = 80.0
    MARGIN_R = 40.0
    top_used = 40
    # Body content is built into `body` so we can compute the true content
    # bottom (legend area) and shrink the viewBox to eliminate the large
    # trailing empty band that came from cell being capped at 16px while
    # plot_h_target was oversized.
    body = []

    body.extend(_title_block(MARGIN_L, top_used, W - MARGIN_L - MARGIN_R,
                              title, subtitle, ink, muted, body_font, head_font))
    ycur = top_used + (44 if (title or subtitle) else 0)
    body.extend(_kpi_row(MARGIN_L, ycur, W - MARGIN_L - MARGIN_R,
                          kpis, ink, muted, accent, bg, ink4, body_font, head_font))
    ycur += 76

    # Grid: 53 columns x 7 rows (weekday)
    plot_w = W - MARGIN_L - MARGIN_R
    plot_h_target = H - ycur - 90
    CELL_GAP = 2.0
    cell = min((plot_w - 52 * CELL_GAP) / 53, (plot_h_target - 6 * CELL_GAP) / 7, 16.0)
    if cell < 6:
        cell = 6
    grid_w = 53 * cell + 52 * CELL_GAP
    grid_h = 7 * cell + 6 * CELL_GAP

    grid_x = MARGIN_L
    grid_y = ycur + 20

    # weekday labels
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for wi, wl in enumerate(weekdays):
        if wi % 2 == 0:
            wy = grid_y + wi * (cell + CELL_GAP) + cell * 0.7
            body.append(
                f'<text x="{grid_x - 8:.1f}" y="{wy:.1f}" text-anchor="end" '
                f'font-family="{body_font}" font-size="9" fill="{muted}">{wl}</text>'
            )

    # Which week does each doy fall in? week 0 starts on Jan 1 (aligned to weekday).
    jan1_wd = calendar.weekday(year, 1, 1)  # Mon=0..Sun=6
    seen_months = set()
    for doy, v in enumerate(values):
        cell_index = jan1_wd + doy
        week = cell_index // 7
        wday = cell_index % 7
        if week >= 53:
            break
        cx_ = grid_x + week * (cell + CELL_GAP)
        cy_ = grid_y + wday * (cell + CELL_GAP)

        m, d = _doy_to_md(doy, year)
        # month label at first day of month
        if d == 1 and m not in seen_months:
            seen_months.add(m)
            body.append(
                f'<text x="{cx_:.1f}" y="{grid_y - 6:.1f}" font-family="{body_font}" '
                f'font-size="9.5" fill="{muted}" font-weight="600">{MONTH_LABELS[m]}</text>'
            )

        col = val_color(v)
        if use_dot:
            # dot with radius ∝ value; base color from color scale
            frac = min(1.0, v / vmax) if vmax > 0 else 0
            r = 1.2 + (cell * 0.42) * (frac ** 0.5)
            body.append(
                f'<circle cx="{cx_ + cell / 2:.1f}" cy="{cy_ + cell / 2:.1f}" '
                f'r="{r:.1f}" fill="{col}"/>'
            )
        else:
            body.append(
                f'<rect x="{cx_:.1f}" y="{cy_:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
                f'rx="1.5" fill="{col}"/>'
            )

    # legend at bottom
    legend_y = grid_y + grid_h + 24
    _append_legend(body, grid_x, legend_y, val_color, vmax, muted, body_font,
                   use_dot=use_dot)

    # Shrink viewBox height to actual content bottom + padding so the SVG has
    # no large empty band below the legend (grid cell is capped at 16px, so
    # the caller-supplied H is usually way larger than what the grid consumes).
    # Legend swatch box=12 + text baseline+font descent ≈ 14 below legend_y.
    content_bottom = legend_y + 14
    H_fit = min(float(H), content_bottom + 20.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H_fit)}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H_fit:.1f}" fill="{bg}"/>')
    parts.extend(body)
    parts.append('</svg>')
    return "".join(parts)


def _append_legend(parts, x, y, val_color, vmax, muted, body_font, use_dot=False):
    parts.append(
        f'<text x="{x - 6:.1f}" y="{y + 10:.1f}" text-anchor="end" '
        f'font-family="{body_font}" font-size="10" fill="{muted}">Less</text>'
    )
    n_steps = 5
    box = 12
    gap = 3
    for i in range(n_steps):
        v = (i / (n_steps - 1)) * vmax
        if use_dot:
            # circle swatch matches dot_grid chart cells
            cx = x + i * (box + gap) + box / 2
            cy = y + box / 2
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{box / 2 - 1:.1f}" '
                f'fill="{val_color(v)}"/>'
            )
        else:
            parts.append(
                f'<rect x="{x + i * (box + gap):.1f}" y="{y:.1f}" width="{box}" height="{box}" '
                f'rx="2" fill="{val_color(v)}"/>'
            )
    parts.append(
        f'<text x="{x + n_steps * (box + gap) + 4:.1f}" y="{y + 10:.1f}" '
        f'font-family="{body_font}" font-size="10" fill="{muted}">More</text>'
    )


# ============================================================
# monthly_grid_12x31
# ============================================================
def _render_monthly_grid(W, H, values, year, title, subtitle, kpis,
                         ink, accent, bg, muted, ink4, ink2,
                         val_color, body_font, head_font, vmax, bg_luma):
    body = []

    grid = [[None] * 31 for _ in range(12)]
    for doy, v in enumerate(values):
        m, d = _doy_to_md(doy, year)
        grid[m][d - 1] = v

    MARGIN_L = 80.0
    MARGIN_R = 40.0
    body.extend(_title_block(MARGIN_L, 40, W - MARGIN_L - MARGIN_R,
                              title, subtitle, ink, muted, body_font, head_font))
    ycur = 40 + (44 if (title or subtitle) else 0)
    body.extend(_kpi_row(MARGIN_L, ycur, W - MARGIN_L - MARGIN_R,
                          kpis, ink, muted, accent, bg, ink4, body_font, head_font))
    ycur += 76

    plot_w = W - MARGIN_L - MARGIN_R
    plot_h_target = H - ycur - 100
    GAP = 2.0
    CELL_W = min((plot_w - 30 * GAP) / 31, 22.0)
    CELL_H = min((plot_h_target - 11 * GAP) / 12, 22.0)
    if CELL_W < 6: CELL_W = 6
    if CELL_H < 6: CELL_H = 6

    grid_x = MARGIN_L + 30
    grid_y = ycur + 30

    # day-of-month header
    for d in range(1, 32):
        if d == 1 or d % 5 == 0:
            cx_ = grid_x + (d - 1) * (CELL_W + GAP) + CELL_W / 2
            body.append(
                f'<text x="{cx_:.1f}" y="{grid_y - 6:.1f}" text-anchor="middle" '
                f'font-family="{body_font}" font-size="9" fill="{muted}">{d}</text>'
            )
    # month labels
    for m in range(12):
        cy_ = grid_y + m * (CELL_H + GAP) + CELL_H * 0.68
        body.append(
            f'<text x="{grid_x - 8:.1f}" y="{cy_:.1f}" text-anchor="end" '
            f'font-family="{body_font}" font-size="10" font-weight="600" '
            f'fill="{ink}">{MONTH_LABELS[m]}</text>'
        )

    for m in range(12):
        for d in range(31):
            x = grid_x + d * (CELL_W + GAP)
            y = grid_y + m * (CELL_H + GAP)
            v = grid[m][d]
            if v is None:
                body.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_W:.1f}" height="{CELL_H:.1f}" '
                    f'rx="2" fill="{_rgba_with_alpha(ink, 0.03)}" stroke="{_rgba_with_alpha(ink, 0.10)}" '
                    f'stroke-width="0.5" stroke-dasharray="1 2"/>'
                )
            else:
                body.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL_W:.1f}" height="{CELL_H:.1f}" '
                    f'rx="2" fill="{val_color(v)}"/>'
                )

    legend_y = grid_y + 12 * (CELL_H + GAP) + 20
    _append_legend(body, grid_x, legend_y, val_color, vmax, muted, body_font)

    # Shrink viewBox to fit the actual bottom of the legend swatches/text.
    content_bottom = legend_y + 14
    H_fit = min(float(H), content_bottom + 20.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H_fit)}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H_fit:.1f}" fill="{bg}"/>')
    parts.extend(body)
    parts.append('</svg>')
    return "".join(parts)


# ============================================================
# small_multiples: 3x4 mini calendars
# ============================================================
def _render_small_multiples(W, H, values, year, title, subtitle, kpis,
                            ink, accent, bg, muted, ink4, ink2,
                            val_color, body_font, head_font, vmax, bg_luma):
    body = []

    grid = [[None] * 31 for _ in range(12)]
    for doy, v in enumerate(values):
        m, d = _doy_to_md(doy, year)
        grid[m][d - 1] = v

    MARGIN_L = 60.0
    MARGIN_R = 40.0
    body.extend(_title_block(MARGIN_L, 40, W - MARGIN_L - MARGIN_R,
                              title, subtitle, ink, muted, body_font, head_font))
    ycur = 40 + (44 if (title or subtitle) else 0)
    body.extend(_kpi_row(MARGIN_L, ycur, W - MARGIN_L - MARGIN_R,
                          kpis, ink, muted, accent, bg, ink4, body_font, head_font))
    ycur += 90

    # 4 cols x 3 rows
    COLS = 4; ROWS = 3
    inter_gap = 16.0
    avail_w = W - MARGIN_L - MARGIN_R
    mini_full_w = (avail_w - (COLS - 1) * inter_gap) / COLS
    avail_h = H - ycur - 60
    mini_full_h = (avail_h - (ROWS - 1) * inter_gap) / ROWS

    header_h = 20.0
    weekday_h = 12.0
    mini_pad = 10.0

    weekdays = ["M", "T", "W", "T", "F", "S", "S"]

    for m in range(12):
        r = m // COLS
        c = m % COLS
        ox = MARGIN_L + c * (mini_full_w + inter_gap)
        oy = ycur + r * (mini_full_h + inter_gap)

        # available inside area
        inner_w = mini_full_w - 2 * mini_pad
        inner_h = mini_full_h - header_h - weekday_h - mini_pad
        cell_gap = 1.6
        cell = min((inner_w - 6 * cell_gap) / 7, (inner_h - 5 * cell_gap) / 6, 14.0)
        if cell < 5:
            cell = 5

        # frame
        body.append(
            f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{mini_full_w:.1f}" height="{mini_full_h:.1f}" '
            f'fill="{_rgba_with_alpha(ink, 0.02)}" stroke="{ink4}" stroke-width="0.6" rx="3"/>'
        )

        # month title
        body.append(
            f'<text x="{ox + mini_pad:.1f}" y="{oy + 14:.1f}" font-family="{body_font}" '
            f'font-size="10.5" font-weight="700" fill="{ink}" letter-spacing="0.12em">'
            f'{MONTH_LABELS_FULL[m]}</text>'
        )

        # weekday header
        wy = oy + header_h + 10
        for wi, wl in enumerate(weekdays):
            wx = ox + mini_pad + wi * (cell + cell_gap) + cell / 2
            body.append(
                f'<text x="{wx:.1f}" y="{wy:.1f}" text-anchor="middle" '
                f'font-family="{body_font}" font-size="7.5" fill="{muted}">{wl}</text>'
            )

        # days
        dim = calendar.monthrange(year, m + 1)[1]
        first_wd = calendar.weekday(year, m + 1, 1)  # Mon=0..Sun=6
        for d in range(1, dim + 1):
            idx = first_wd + (d - 1)
            row = idx // 7
            col = idx % 7
            cx_ = ox + mini_pad + col * (cell + cell_gap)
            cy_ = oy + header_h + weekday_h + row * (cell + cell_gap)
            v = grid[m][d - 1]
            color = val_color(v if v is not None else 0)
            body.append(
                f'<rect x="{cx_:.1f}" y="{cy_:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
                f'rx="1.2" fill="{color}"/>'
            )

    # Bottom of the mini-calendar grid (row-3 frame bottom).
    content_bottom = ycur + ROWS * mini_full_h + (ROWS - 1) * inter_gap
    H_fit = min(float(H), content_bottom + 20.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H_fit)}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H_fit:.1f}" fill="{bg}"/>')
    parts.extend(body)
    parts.append('</svg>')
    return "".join(parts)


# ============================================================
# radial_year
# ============================================================
def _render_radial(W, H, values, year, title, subtitle, kpis,
                   ink, accent, bg, muted, ink4, ink2,
                   val_color, body_font, head_font, vmax, bg_luma):
    body = []

    MARGIN_L = 60.0
    MARGIN_R = 40.0
    body.extend(_title_block(MARGIN_L, 40, W - MARGIN_L - MARGIN_R,
                              title, subtitle, ink, muted, body_font, head_font))
    ycur = 40 + (44 if (title or subtitle) else 0)
    # scale KPI row up so text stays legible against a large radial body
    kpi_scale = max(1.0, min(1.6, H / 620.0))
    body.extend(_kpi_row(MARGIN_L, ycur, W - MARGIN_L - MARGIN_R,
                          kpis, ink, muted, accent, bg, ink4, body_font, head_font,
                          scale=kpi_scale))
    ycur += 90 + (kpi_scale - 1.0) * 40

    per_month_days = [[] for _ in range(12)]
    for doy, v in enumerate(values):
        m, d = _doy_to_md(doy, year)
        per_month_days[m].append(v)
    monthly_totals = [sum(x) for x in per_month_days]

    # geometry
    ring_top = ycur + 20
    ring_bottom = H - 60
    ring_avail_h = ring_bottom - ring_top
    CX = W / 2
    CY = ring_top + ring_avail_h / 2
    R_OUT = min(W / 2 - 90, ring_avail_h / 2 - 60)
    if R_OUT < 60: R_OUT = 60
    R_IN = R_OUT * 0.40

    n_month = 12
    for m in range(n_month):
        dim = calendar.monthrange(year, m + 1)[1]
        seg = math.pi * 2 / n_month
        month_start = -math.pi / 2 + m * seg
        for d in range(31):
            a0 = month_start + (d / 31) * seg
            a1 = month_start + ((d + 1) / 31) * seg
            gap_rad = 0.001
            a0g = a0 + gap_rad
            a1g = a1 - gap_rad
            if d >= dim:
                fill = _rgba_with_alpha(ink, 0.05)
            else:
                v = per_month_days[m][d] if d < len(per_month_days[m]) else 0
                fill = val_color(v)
            p1x = CX + R_OUT * math.cos(a0g); p1y = CY + R_OUT * math.sin(a0g)
            p2x = CX + R_OUT * math.cos(a1g); p2y = CY + R_OUT * math.sin(a1g)
            p3x = CX + R_IN * math.cos(a1g); p3y = CY + R_IN * math.sin(a1g)
            p4x = CX + R_IN * math.cos(a0g); p4y = CY + R_IN * math.sin(a0g)
            path = (
                f'M {p1x:.2f} {p1y:.2f} '
                f'A {R_OUT:.2f} {R_OUT:.2f} 0 0 1 {p2x:.2f} {p2y:.2f} '
                f'L {p3x:.2f} {p3y:.2f} '
                f'A {R_IN:.2f} {R_IN:.2f} 0 0 0 {p4x:.2f} {p4y:.2f} Z'
            )
            body.append(f'<path d="{path}" fill="{fill}"/>')

    # month dividers + labels
    for m in range(n_month):
        seg = math.pi * 2 / n_month
        a = -math.pi / 2 + m * seg
        x1 = CX + (R_IN - 4) * math.cos(a); y1 = CY + (R_IN - 4) * math.sin(a)
        x2 = CX + (R_OUT + 4) * math.cos(a); y2 = CY + (R_OUT + 4) * math.sin(a)
        body.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{ink4}" stroke-width="0.5"/>'
        )
        a_mid = a + seg / 2
        # Push labels far enough outside the ring outline that a horizontal-axis label
        # (MAR/APR/SEP/OCT sit near ±cos≈1) does not overlap the circle's axis-aligned
        # bbox. Text half-width for a 3-letter label at font-size 12 is ~16px; the
        # outline circle radius = R_OUT+0.5, so we need r_lbl > (R_OUT + text_halfwidth)
        # / |cos(a_mid)|. Adding a small buffer keeps the validator happy.
        r_lbl = R_OUT + 34
        lx = CX + r_lbl * math.cos(a_mid); ly = CY + r_lbl * math.sin(a_mid)
        body.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-family="{body_font}" '
            f'font-size="12" font-weight="700" fill="{ink}" letter-spacing="0.10em">'
            f'{MONTH_LABELS_FULL[m]}</text>'
        )

    # rings outline
    body.append(
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="{R_OUT + 0.5:.1f}" fill="none" '
        f'stroke="{ink4}" stroke-width="0.5"/>'
    )
    body.append(
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="{R_IN - 0.5:.1f}" fill="none" '
        f'stroke="{ink4}" stroke-width="0.5"/>'
    )

    # center year label
    body.append(
        f'<text x="{CX:.1f}" y="{CY - 4:.1f}" text-anchor="middle" '
        f'font-family="{head_font}" font-size="42" font-weight="700" fill="{ink}" '
        f'letter-spacing="0.05em">{year}</text>'
    )
    total = int(sum(values))
    body.append(
        f'<text x="{CX:.1f}" y="{CY + 22:.1f}" text-anchor="middle" '
        f'font-family="{body_font}" font-size="12" fill="{muted}" '
        f'letter-spacing="0.10em">TOTAL {total:,}</text>'
    )

    # Bottom of content is the lower month label (a_mid = pi/2 → bottom of
    # the ring): y ≈ CY + (R_OUT + 34) + label font descent (~6). Also
    # account for the ring outline itself. Take the max.
    label_bottom = CY + (R_OUT + 34) + 8
    ring_outline_bottom = CY + R_OUT + 0.5
    content_bottom = max(label_bottom, ring_outline_bottom)
    H_fit = min(float(H), content_bottom + 20.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H_fit)}">']
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H_fit:.1f}" fill="{bg}"/>')
    parts.extend(body)
    parts.append('</svg>')
    return "".join(parts)


def make_calheat(values: Sequence[float] = None, matrix: Sequence[Sequence[float]] = None,
                 year: int = None,
                 first_dow: int = 0,
                 title: str = None,
                 subtitle: str = None,
                 figure_label: str = None,
                 figure_note: str = None,
                 note: str = None,
                 source: str = None,
                 unit_label: str = "activity",
                 kpis: "list[tuple]" = None,
                 show_month_bars: bool = True,
                 show_colorbar: bool = True,
                 highlight_monthly_peak: bool = True,
                 font_family: str = None,
                 palette=None,
                 variant: str = None) -> str:
    """
    日历热力图（GitHub-style academic print）：
      - 顶部标题 + subtitle + FIGURE caption
      - 上方 KPI 卡片（可选：TOTAL / ACTIVE DAYS / AVG / STREAK ...）
      - 主体：52 周 × 7 天，每格 = 一天；渐变颜色（从纸色到 accent）
      - 顶部月份 label + 每月首列虚线分隔
      - 左侧 Mon/Wed/Fri/Sun 标签
      - 每月最活跃日红色空心圆强调（可选）
      - 右侧 12 月 monthly total 柱状图
      - 底部 colorbar（离散 6 档）+ Notes / Source
      - 底部 Peak 图例说明

    参数：
      values / matrix: 传其一
        - values: 长度 ≤ 371（52×7=364 + 前置最多 6 天）的一维数组，按天顺序
        - matrix: 52×7 二维数组（列=周, 行=day-of-week）
      year: 年份显示（如 2025）
      first_dow: 一年第一天是周几（0=Mon..6=Sun）；只影响左侧 label 显示位置
      title / subtitle / figure_label / figure_note: 顶部标题
      note / source: 底部脚注
      unit_label: 数值语义（如 "commits", "hours", "requests"）
      kpis: [(header, big, sub), ...] 最多 4 张
      show_month_bars: 右侧 12 月柱状图
      show_colorbar: 底部 colorbar
      highlight_monthly_peak: 每月最活跃日画红色空心圆
      palette: 配色
    """
    if not _variant_is_classic("calheat", variant):
        # svg_lib 分派：把 values/matrix 转为 svg_lib 的 data
        _vals = list(values) if values is not None else [v for row in matrix for v in row]
        data = {"values": _vals}
        if year is not None:
            data["year"] = year
        # 用户显式传入的 kpis 必须透传给 svg_lib，否则 draw_calheat 会用自动计算的
        # TOTAL / ACTIVE DAYS / PEAK 覆盖用户值。只在 kpis is None 时才让下游自动生成。
        if kpis is not None:
            data["kpis"] = kpis
        return _dispatch_to_svg_lib(
            "calheat", variant, data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )
    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.5))
    paper = _pal.get("bg", "rgba(250,248,242,1)")

    if matrix is None:
        assert values is not None, "需要传 values 或 matrix"
        # 支持任意长度（≤ 371），不足补 0，多余截断
        arr = list(values)[:52 * 7]
        arr = arr + [0] * (52 * 7 - len(arr))
        matrix = [arr[w * 7:(w + 1) * 7] for w in range(52)]
    else:
        matrix = [list(row) for row in matrix]
        if len(matrix) != 52 or any(len(r) != 7 for r in matrix):
            raise ValueError(f"calheat: matrix must be 52×7, got {len(matrix)}×{len(matrix[0]) if matrix else 0}")

    flat = [v for row in matrix for v in row]
    vmax = max(flat) if flat else 1
    vmin = min(flat) if flat else 0
    if vmax == vmin:
        vmax = vmin + 1

    # ---- 颜色渐变：以 palette bg 为底，向 accent 深处渐变 ----
    def _rgb_of(rgba):
        return _rgb_tuple(rgba)
    accent_rgb = _rgb_of(_ACC)
    # 起点：稍深于 bg 一点点（用 muted lightened）；如果 bg 是深色，起点用 accent 淡化
    bg_rgb = _rgb_of(paper)
    bg_luma = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
    if bg_luma < 100:
        # 深底：起点是深底 → 渐变到 accent（保持 accent 亮度）
        empty_col = _rgba_with_alpha(_INK, 0.10)  # 微微亮的空格
    else:
        # 浅底：起点稍深于 bg
        empty_col = _rgba_with_alpha(_INK, 0.08)

    def _blend(c1_rgb, c2_rgb, t):
        r = c1_rgb[0] + (c2_rgb[0] - c1_rgb[0]) * t
        g = c1_rgb[1] + (c2_rgb[1] - c1_rgb[1]) * t
        b = c1_rgb[2] + (c2_rgb[2] - c1_rgb[2]) * t
        return f"rgb({int(r)},{int(g)},{int(b)})"

    # 起点是 muted 灰 blend bg
    start_rgb = _rgb_of(c_secondary)
    def value_to_color(v):
        if v == vmin or v == 0:
            return empty_col
        t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0
        t = max(0.0, min(1.0, t))
        # 使用 4 档级：淡→中→重→深(accent)
        # t 在 [0, 1] 内映射到 accent 亮度
        stops = [
            (0.0, _rgb_of(empty_col) if empty_col.startswith("rgb(") else start_rgb),
            (0.20, _lighten_rgba(_ACC, 0.7)),  # 淡 accent
            (0.50, _lighten_rgba(_ACC, 0.3)),
            (0.80, _ACC),
            (1.0, _darken_rgba(_ACC, 0.25)),
        ]
        # 转成 rgb tuple 列表
        stops2 = []
        for st, col in stops:
            if isinstance(col, tuple):
                stops2.append((st, col))
            else:
                stops2.append((st, _rgb_of(col)))
        for i in range(len(stops2) - 1):
            t1, c1 = stops2[i]; t2, c2 = stops2[i + 1]
            if t1 <= t <= t2:
                k = (t - t1) / (t2 - t1) if t2 > t1 else 0
                return _blend(c1, c2, k)
        return _blend(stops2[0][1], stops2[-1][1], 1)

    # ---- 画布 ----
    CELL = 14.0
    GAP = 3.0
    n_cols = 52
    plot_w = n_cols * (CELL + GAP) - GAP  # 883.0
    plot_h = 7 * (CELL + GAP) - GAP        # 116.0
    MARGIN_L = 100.0
    MARGIN_R = 260.0 if show_month_bars else 40.0
    # KPI 卡片顶部固定在 y=130；卡内三行 baseline 由字号动态决定，最终高度 kpi_h ≈
    # padding_top + fs_hdr + fs_big + fs_sub + gaps。base_fs 越大（大画布），kpi_h 越高。
    # 需要让 MARGIN_T 至少 = 130 + kpi_h + 20（KPI 卡到月份 label 的间距），否则月份 label
    # 会与 KPI sub 撞。这里先按 _fs_kpi_big=48 上限保守预留 100px 卡片高。
    if kpis:
        # 上限：24 (top padding + hdr) + 48 (big) + 12 (sub) + 8 (bottom padding) + 4*2 (gaps) ≈ 100
        _est_kpi_h = 24.0 + 48.0 + 12.0 + 12.0
        MARGIN_T = max(210.0, 130.0 + _est_kpi_h + 20.0)
    else:
        MARGIN_T = 210.0 if (title or subtitle) else 60.0
    MARGIN_B = 120.0 if (show_colorbar or note or source) else 60.0
    W = MARGIN_L + plot_w + MARGIN_R + 20
    H = MARGIN_T + plot_h + MARGIN_B + 20

    # ---------- 字号自适应 ----------
    # viewBox + 数据规模（n = active days）。W≈1243, H≈458.
    # calheat 是横向长条 (aspect ~2.7)，min(W,H) 会被 H 卡住偏小。
    # 用几何均值 sqrt(W*H) 更合适，避免 base_fs 在扁 SVG 里过小。
    _n_active = sum(1 for v in flat if v > 0)
    _base_fs = math.sqrt(W * H) * 0.02   # W=1243,H=458 → sqrt=755 → base=15.1
    if _n_active <= 4:
        _fs_data = _base_fs * 1.4
    elif _n_active <= 8:
        _fs_data = _base_fs * 1.0
    elif _n_active <= 15:
        _fs_data = _base_fs * 0.8
    else:
        _fs_data = max(_base_fs * 0.6, 10)

    # 各类字号：多数元素与 base_fs 联动；月份 label 与 KPI 大数字单独控制。
    # base_fs≈15，calheat 是横条 SVG → sqrt(W*H) 派生更合适。
    _fs_title    = round(min(34.0, max(22.0, _base_fs * 1.75)), 1)  # base*1.75 → ~26
    _fs_subtitle = round(min(16.0, max(11.0, _base_fs * 0.82)), 1)
    _fs_figure   = round(min(13.0, max(10.0, _base_fs * 0.7)),  1)
    _fs_month    = round(min(14.0, max(10.5, _base_fs * 0.73)), 1)   # 月份 label = base*1.1（相对 min(W,H) 版本）
    _fs_kpi_hdr  = round(min(12.0, max(9.5,  _base_fs * 0.65)), 1)
    _fs_kpi_big  = round(min(48.0, max(24.0, _base_fs * 2.5)),  1)  # KPI 大数字 base*2.5
    _fs_kpi_sub  = round(min(12.0, max(9.5,  _base_fs * 0.65)), 1)
    _fs_dow      = round(min(13.0, max(10.0, _base_fs * 0.7)),  1)   # Mon/Wed/Fri/Sun
    _fs_bar_hdr  = round(min(13.0, max(10.0, _base_fs * 0.72)), 1)   # MONTHLY TOTAL
    _fs_bar_lbl  = round(min(12.0, max(9.0,  _base_fs * 0.62)), 1)   # 月缩写
    _fs_bar_val  = round(min(12.0, max(9.5,  _base_fs * 0.68)), 1)
    _fs_cb       = round(min(13.0, max(11.0, _base_fs * 0.85)), 1)   # Less/More + tick
    _fs_foot     = round(min(14.0, max(11.0, _base_fs * 0.85)), 1)   # note/source 底线 11pt

    parts = []
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{paper}"/>')

    # ---- 标题 ----
    if title:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="52" font-family="{_head_font}" '
                     f'font-size="{_fs_title}" font-weight="600" fill="{_INK}" letter-spacing="0.1">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="76" font-family="{_body_font}" '
                     f'font-size="{_fs_subtitle}" fill="{c_muted}" letter-spacing="0.2">'
                     f'{_xesc(subtitle)}</text>')
    if title or subtitle:
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="92" x2="{W - 40:.1f}" y2="92" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="112" font-family="{_body_font}" '
                     f'font-size="{_fs_figure}" fill="{c_muted}" font-weight="600" letter-spacing="1.5">'
                     f'{_xesc(figure_label)}</text>')
    if figure_note:
        offset = 72 if figure_label else 0
        parts.append(f'<text x="{MARGIN_L + offset:.1f}" y="112" font-family="{_body_font}" '
                     f'font-size="{_fs_figure}" fill="{c_muted}" letter-spacing="0.4">'
                     f'{_xesc(figure_note)}</text>')

    # ---- KPI 卡片 ----
    if kpis:
        kpi_y = 130.0
        # 三行 baseline 布局：header (top) → big (middle) → sub (bottom)。
        # 需保证 header 底 (baseline + fs*0.2) < big 顶 (baseline - fs*0.8)，
        # 同理 big 底 < sub 顶，否则 detect_embedded_svg_overlaps 会报 bbox_overlap。
        _hdr_gap = 4.0   # baseline 之间的额外间距
        _pad_top = 16.0  # 卡内上边到 header baseline
        _hdr_baseline = _pad_top
        _big_baseline = _hdr_baseline + _fs_kpi_hdr * 0.2 + _fs_kpi_big * 0.8 + _hdr_gap
        _sub_baseline = _big_baseline + _fs_kpi_big * 0.2 + _fs_kpi_sub * 0.8 + _hdr_gap
        _kpi_content_h = _sub_baseline + _fs_kpi_sub * 0.2 + 8.0  # 8 = 底部内边距
        kpi_h = max(60.0, _kpi_content_h)
        n_k = len(kpis)
        gap = 20.0
        avail = (W - 40) - MARGIN_L
        kpi_w = (avail - gap * (n_k - 1)) / n_k
        for i, tup in enumerate(kpis):
            head, big, sub = tup[0], tup[1], tup[2] if len(tup) > 2 else ""
            kx = MARGIN_L + i * (kpi_w + gap)
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y:.1f}" width="{kpi_w:.1f}" '
                         f'height="{kpi_h:.1f}" fill="{paper}" stroke="{_INK4}" stroke-width="0.8"/>')
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y:.1f}" width="4" height="{kpi_h:.1f}" '
                         f'fill="{_ACC}"/>')
            parts.append(f'<text x="{kx + 16:.1f}" y="{kpi_y + _hdr_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{_fs_kpi_hdr}" fill="{c_muted}" font-weight="600" letter-spacing="1.4">'
                         f'{_xesc(head)}</text>')
            parts.append(f'<text x="{kx + 16:.1f}" y="{kpi_y + _big_baseline:.1f}" font-family="{_head_font}" '
                         f'font-size="{_fs_kpi_big}" fill="{_INK}" font-weight="700">{_xesc(big)}</text>')
            parts.append(f'<text x="{kx + 16:.1f}" y="{kpi_y + _sub_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{_fs_kpi_sub}" fill="{c_muted}">{_xesc(sub)}</text>')

    # ---- 月份 label（顶部）+ 分隔 ----
    # 12 个月，每月约 52/12 ≈ 4.33 周
    grid_x0 = MARGIN_L
    grid_y0 = MARGIN_T
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    for m in range(12):
        w_col = int(m * 52 / 12)
        mx = grid_x0 + w_col * (CELL + GAP)
        parts.append(f'<text x="{mx:.1f}" y="{grid_y0 - 8:.1f}" font-family="{_body_font}" '
                     f'font-size="{_fs_month}" font-weight="600" fill="{_INK}">'
                     f'{month_labels[m]}</text>')
        # 分隔虚线（除首月）
        if m > 0:
            div_x = mx - GAP / 2
            parts.append(f'<line x1="{div_x:.1f}" y1="{grid_y0 - 3:.1f}" x2="{div_x:.1f}" '
                         f'y2="{grid_y0 + plot_h + 3:.1f}" stroke="{_INK4}" stroke-width="0.4" '
                         f'stroke-dasharray="1 3"/>')

    # ---- 左侧 Mon/Wed/Fri/Sun 标签 ----
    for row, wname in [(0, "Mon"), (2, "Wed"), (4, "Fri"), (6, "Sun")]:
        y = grid_y0 + row * (CELL + GAP) + CELL - 3
        parts.append(f'<text x="{grid_x0 - 10:.1f}" y="{y:.1f}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{_fs_dow}" fill="{c_muted}">'
                     f'{wname}</text>')

    # ---- 绘制格子 ----
    # highlight_monthly_peak: 记录每个月的最大值 + 位置
    peak_pos = {}  # month_idx (0..11) → (col, row, val)
    for w in range(52):
        # month index 大致映射
        m_of_w = min(11, int(w * 12 / 52))
        for d in range(7):
            v = matrix[w][d]
            color = value_to_color(v)
            x = grid_x0 + w * (CELL + GAP)
            y = grid_y0 + d * (CELL + GAP)
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL:.1f}" height="{CELL:.1f}" '
                         f'rx="2" fill="{color}"/>')
            if highlight_monthly_peak:
                cur = peak_pos.get(m_of_w)
                if cur is None or v > cur[2]:
                    peak_pos[m_of_w] = (w, d, v)

    # ---- 每月最活跃日红圈 ----
    if highlight_monthly_peak:
        for m_idx, (w, d, v) in peak_pos.items():
            if v <= vmin:
                continue
            x = grid_x0 + w * (CELL + GAP) + CELL - 2
            y = grid_y0 + d * (CELL + GAP) + 2
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="none" '
                         f'stroke="{_ACC}" stroke-width="0.9"/>')

    # ---- 右侧月度总和柱状图 ----
    if show_month_bars:
        sum_x = grid_x0 + plot_w + 30
        sum_y = grid_y0
        sum_h = plot_h + 20
        sum_bar_w = 12.0
        sum_bar_gap = 4.0
        sum_w = 12 * (sum_bar_w + sum_bar_gap) - sum_bar_gap
        sum_bottom = sum_y + sum_h - 20
        sum_max_bar_h = sum_h - 40

        # 逐月总和 —— 用列范围估算
        monthly = [0.0] * 12
        for w in range(52):
            m_of_w = min(11, int(w * 12 / 52))
            for d in range(7):
                monthly[m_of_w] += matrix[w][d]
        month_max = max(monthly) if any(monthly) else 1

        parts.append(f'<text x="{sum_x:.1f}" y="{sum_y - 8:.1f}" font-family="{_body_font}" '
                     f'font-size="{_fs_bar_hdr}" font-weight="600" fill="{_INK}" letter-spacing="1.2">'
                     f'MONTHLY TOTAL</text>')
        parts.append(f'<line x1="{sum_x:.1f}" y1="{sum_bottom:.1f}" x2="{sum_x + sum_w:.1f}" '
                     f'y2="{sum_bottom:.1f}" stroke="{c_muted}" stroke-width="0.8"/>')

        for i, mv in enumerate(monthly):
            bx = sum_x + i * (sum_bar_w + sum_bar_gap)
            bh = (mv / month_max) * sum_max_bar_h if month_max > 0 else 0
            # 用 value_to_color 类似规则
            color = value_to_color(mv / max(1, month_max) * vmax) if mv > 0 else empty_col
            parts.append(f'<rect x="{bx:.1f}" y="{sum_bottom - bh:.1f}" width="{sum_bar_w:.1f}" '
                         f'height="{bh:.1f}" fill="{color}"/>')
            parts.append(f'<text x="{bx + sum_bar_w / 2:.1f}" y="{sum_bottom + 12:.1f}" '
                         f'text-anchor="middle" font-family="{_body_font}" '
                         f'font-size="{_fs_bar_lbl}" fill="{c_muted}">{month_labels[i][0]}</text>')
        # 最高月标注
        max_month_idx = monthly.index(month_max) if any(monthly) else 0
        bx = sum_x + max_month_idx * (sum_bar_w + sum_bar_gap) + sum_bar_w / 2
        bh = sum_max_bar_h
        if monthly and monthly[max_month_idx] > 0:
            parts.append(f'<text x="{bx:.1f}" y="{sum_bottom - bh - 4:.1f}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="{_fs_bar_val}" fill="{_INK}" '
                         f'font-weight="600">{int(round(month_max))}</text>')

    # ---- 底部 colorbar ----
    cb_bottom_y = grid_y0 + plot_h + 40
    if show_colorbar:
        cb_x = grid_x0 + 30
        cb_h = 12.0
        cb_w = 240.0
        parts.append(f'<text x="{cb_x - 12:.1f}" y="{cb_bottom_y + cb_h - 2:.1f}" '
                     f'text-anchor="end" font-family="{_body_font}" font-size="{_fs_cb}" '
                     f'fill="{c_muted}">Less</text>')
        levels = [0.0, 0.15, 0.35, 0.55, 0.75, 0.95]
        seg_w = cb_w / len(levels)
        for i, t in enumerate(levels):
            fill = value_to_color(t * vmax)
            cxseg = cb_x + i * seg_w
            parts.append(f'<rect x="{cxseg:.1f}" y="{cb_bottom_y:.1f}" width="{seg_w - 3:.1f}" '
                         f'height="{cb_h:.1f}" rx="2" fill="{fill}"/>')
        parts.append(f'<text x="{cb_x + cb_w + 10:.1f}" y="{cb_bottom_y + cb_h - 2:.1f}" '
                     f'text-anchor="start" font-family="{_body_font}" font-size="{_fs_cb}" '
                     f'fill="{c_muted}">More</text>')
        # 数值刻度
        for i in range(5):
            px = cb_x + (i / 4) * cb_w
            val = int(round(i / 4 * vmax))
            parts.append(f'<text x="{px:.1f}" y="{cb_bottom_y + cb_h + 14:.1f}" '
                         f'text-anchor="middle" font-family="{_body_font}" '
                         f'font-size="{_fs_cb}" fill="{c_muted}">{val}</text>')
        # peak circle 说明
        if highlight_monthly_peak:
            parts.append(f'<circle cx="{cb_x + cb_w + 130:.1f}" cy="{cb_bottom_y + cb_h / 2:.1f}" '
                         f'r="2" fill="none" stroke="{_ACC}" stroke-width="0.9"/>')
            parts.append(f'<text x="{cb_x + cb_w + 140:.1f}" y="{cb_bottom_y + cb_h - 2:.1f}" '
                         f'font-family="{_body_font}" font-size="{_fs_cb}" fill="{c_muted}">'
                         f'Monthly peak</text>')

    # ---- 脚注 ----
    if note or source:
        foot_y = H - 30
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{foot_y - 14:.1f}" x2="{W - 40:.1f}" '
                     f'y2="{foot_y - 14:.1f}" stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L:.1f}" y="{foot_y:.1f}" font-family="{_body_font}" '
                         f'font-size="{_fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            y_off = foot_y + (14 if note else 0)
            parts.append(f'<text x="{MARGIN_L:.1f}" y="{y_off:.1f}" font-family="{_body_font}" '
                         f'font-size="{_fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 3) Ridge Plot 山脊图
# ==============================================================
