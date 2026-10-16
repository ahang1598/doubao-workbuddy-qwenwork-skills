"""Academic chart: electrochemical / frequency-response plot."""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import ZH_CHROME, tr

ZH_CHROME.setdefault("Measured", "实测")
ZH_CHROME.setdefault("Model", "模型")


def _format_freq(freq: float) -> str:
    """Short engineering notation for frequency labels (e.g. ``1 kHz``, ``10 mHz``)."""
    if freq <= 0:
        return "0"
    exp = math.floor(math.log10(freq))
    for mag, suffix in ((9, "G"), (6, "M"), (3, "k"), (0, ""), (-3, "m"), (-6, "u"), (-9, "n")):
        if exp >= mag:
            v = freq / (10**mag)
            if abs(v - round(v)) < 1e-6:
                return f"{round(v)} {suffix}Hz"
            return f"{v:.2g} {suffix}Hz"
    return f"{freq:.2g} Hz"


def _draw_nyquist(
    nyquist_points,
    *,
    pal,
    body_font,
    heading_font,
    fs,
    title,
    subtitle,
    figure_label,
    note,
    source,
    magnitude_unit,
    show_freq_labels,
    W,
    H,
    show_count=False,
    models=None,
):
    margin_top = 110
    margin_bot = 130
    margin_left = 120
    margin_right = 80
    if H < rigor.COMPACT_HEIGHT:
        margin_top, margin_bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source)
        )
        margin_right = min(margin_right, 40)
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    # Sort points by frequency so the polyline traces the EIS sweep in order (classic semicircle for RC/Randles-like
    # systems).
    def _freq_key(p):
        if len(p) >= 3 and p[2] is not None:
            return (0, float(p[2]))
        return (1, 0.0)

    nyquist_points = sorted(nyquist_points, key=_freq_key)

    zr = [p[0] for p in nyquist_points]
    zi = [p[1] for p in nyquist_points]  # already -Z''
    model_lines = []
    for m in models or []:
        pts = m.get("points") if isinstance(m, dict) else m
        if not pts or len(pts) < 2:
            raise ValueError("each nyquist model needs points=[(Z', -Z''), ...] (>= 2)")
        model_lines.append(
            (str(m.get("name") or "") if isinstance(m, dict) else "", [(float(p[0]), float(p[1])) for p in pts])
        )
    # Model curves (equivalent-circuit fit incl. a Warburg 45° tail) set the axis range too — never clipped.
    all_r = zr + [a for _, pts in model_lines for a, _ in pts]
    all_i = zi + [b for _, pts in model_lines for _, b in pts]
    x_ticks, x_min, x_max = rigor.nice_axis(min(0.0, min(all_r)), max(all_r), 6)
    y_ticks, y_min, y_max = rigor.nice_axis(min(0.0, min(all_i)), max(all_i), 5)

    def X(v):
        return rigor._lin(v, x_min, x_max, plot_x_left, plot_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    parts = rigor.draw_canvas_bg(pal, W, H)
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 24,
            plot_x_right - plot_x_left,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )

    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            plot_y_bot,
            pal=pal,
            y_ticks=y_ticks,
            y_min=y_min,
            y_max=y_max,
            x_ticks=x_ticks,
            x_min=x_min,
            x_max=x_max,
            orient="both",
        )
    )

    d = " ".join(f"{'M' if i == 0 else 'L'} {X(zr[i]):.1f} {Y(zi[i]):.1f}" for i in range(len(nyquist_points)))
    parts.append(f'<path d="{d}" fill="none" stroke="{pal["accent"]}" stroke-width="2.0"/>')
    for k, (name, pts) in enumerate(model_lines):
        md = " ".join(f"{'M' if i == 0 else 'L'} {X(a):.1f} {Y(b):.1f}" for i, (a, b) in enumerate(pts))
        parts.append(
            f'<path d="{md}" fill="none" stroke="{pal["ink"]}" stroke-width="1.6" '
            f'stroke-dasharray="{"6 4" if k == 0 else "2 3"}" data-role="nyquist-model"/>'
        )
    if model_lines:
        # Key in the plot's top-left corner: measured points vs each named model.
        key_fs = max(12.0, fs["label"] * 0.9)
        ky = plot_y_top + key_fs + 4
        x0 = plot_x_left + 12
        entries = [(tr("Measured"), None)] + [(name or tr("Model"), k) for k, (name, _) in enumerate(model_lines)]
        for label, k in entries:
            cy = ky - key_fs * 0.33
            if k is None:
                parts.append(f'<circle cx="{x0 + 9:.1f}" cy="{cy:.1f}" r="3.4" fill="{pal["accent"]}"/>')
            else:
                parts.append(
                    f'<line x1="{x0:.1f}" y1="{cy:.1f}" x2="{x0 + 18:.1f}" y2="{cy:.1f}" stroke="{pal["ink"]}" '
                    f'stroke-width="1.6" stroke-dasharray="{"6 4" if k == 0 else "2 3"}"/>'
                )
            parts.append(
                f'<text x="{x0 + 24:.1f}" y="{ky:.1f}" font-size="{key_fs:.1f}" fill="{pal["ink"]}" '
                f'data-role="legend-label">{_xesc(label)}</text>'
            )
            ky += key_fs * 1.4

    label_fs = max(13.0, fs["label"])
    N = len(nyquist_points)
    # Pick ~5 labels at well-spaced indices (first, last, and ~3 interior).
    # Hard-cap total labels to 5 to avoid pile-up at frequency extremes.
    if N <= 5:
        label_indices = sorted(set(range(N)))
    else:
        label_indices = {0, N - 1}
        for k in range(1, 4):
            label_indices.add(round(k * (N - 1) / 4))
        label_indices = sorted(label_indices)

    # Precompute scatter dot bboxes and horizontal grid y-coords so we can score candidate label positions and
    # drop/relocate labels that would trip the ``text_shape_overlap`` or ``line_through_text`` lint rules.
    _dot_r = 3.4
    _dot_bboxes = []
    for p in nyquist_points:
        _px = X(p[0])
        _py = Y(p[1])
        _dot_bboxes.append((_px - _dot_r, _py - _dot_r, _px + _dot_r, _py + _dot_r))
    _grid_ys = [Y(v) for v in y_ticks if y_min - 1e-9 <= v <= y_max + 1e-9]

    def _bbox_hits_dot(bbox):
        for d in _dot_bboxes:
            if not (bbox[2] < d[0] or bbox[0] > d[2] or bbox[3] < d[1] or bbox[1] > d[3]):
                return True
        return False

    def _bbox_hits_grid(bbox):
        # Mirror the lint band: text bbox height spans label_fs; band is 15%-70% of that height from the top.
        _h = max(1.0, bbox[3] - bbox[1])
        _band_top = bbox[1] + _h * 0.15 - 1.0
        _band_bot = bbox[1] + _h * 0.70 + 1.0
        for gy in _grid_ys:
            if _band_top <= gy <= _band_bot and (bbox[2] - bbox[0]) > 2.0:
                return True
        return False

    _placed_label_bbox = []
    _placed_halo_bbox = []

    for i, p in enumerate(nyquist_points):
        cx, cy = X(p[0]), Y(p[1])
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{_dot_r}" fill="{pal["accent"]}" '
            f'stroke="rgba(28,28,26,1)" stroke-width="0.8"/>'
        )
        if not (show_freq_labels and len(p) >= 3 and i in label_indices):
            continue
        text = _format_freq(p[2])
        from .._common import _estimate_label_width_px as _elw

        tw = _elw(text, label_fs, font_family=body_font)
        th = label_fs  # near full line height
        # Search candidate positions: 4 quadrants × 3 distances.
        placed = None
        for dy_mul in (-1, 1):  # above (-1) then below (+1)
            for dx_mul in (1, -1):  # right then left
                for dist in (16, 26, 40, 60):
                    _ldx = (_dot_r + 10 + (dist - 16) * 0.4) * dx_mul
                    _ldy = (_dot_r + label_fs * 0.9 + 2 + (dist - 16) * 0.5) * dy_mul
                    lx = cx + _ldx
                    ly = cy + _ldy
                    anc = "start" if dx_mul > 0 else "end"
                    if anc == "start":
                        bbox = (lx - 2, ly - th * 0.9, lx + tw + 4, ly + 2)
                    else:
                        bbox = (lx - tw - 4, ly - th * 0.9, lx + 2, ly + 2)
                    # keep inside plot bounds
                    if bbox[0] < plot_x_left or bbox[2] > plot_x_right:
                        continue
                    if bbox[1] < plot_y_top or bbox[3] > plot_y_bot:
                        continue
                    # avoid other placed labels (and their halo rects)
                    collided = False
                    for b in _placed_label_bbox + _placed_halo_bbox:
                        if not (bbox[2] < b[0] or bbox[0] > b[2] or bbox[3] < b[1] or bbox[1] > b[3]):
                            collided = True
                            break
                    if collided:
                        continue
                    if _bbox_hits_dot(bbox) or _bbox_hits_grid(bbox):
                        continue
                    # halo rect dimensions must also avoid other labels/dots.
                    _halo_pad_x = 4
                    _halo_pad_y = 2
                    if anc == "start":
                        _halo_bbox = (
                            lx - _halo_pad_x,
                            ly - label_fs * 0.82 - _halo_pad_y,
                            lx + tw + _halo_pad_x,
                            ly + _halo_pad_y + label_fs * 0.23,
                        )
                    else:
                        _halo_bbox = (
                            lx - tw - _halo_pad_x,
                            ly - label_fs * 0.82 - _halo_pad_y,
                            lx + _halo_pad_x,
                            ly + _halo_pad_y + label_fs * 0.23,
                        )
                    if _bbox_hits_dot(_halo_bbox):
                        continue
                    # The halo rect is itself a shape; if it would overlap a
                    # previously placed label's text bbox the lint flags
                    # ``text_shape_overlap`` against the earlier label.
                    _halo_vs_text_collision = False
                    for b in _placed_label_bbox:
                        if not (
                            _halo_bbox[2] < b[0] or _halo_bbox[0] > b[2] or _halo_bbox[3] < b[1] or _halo_bbox[1] > b[3]
                        ):
                            _halo_vs_text_collision = True
                            break
                    if _halo_vs_text_collision:
                        continue
                    placed = (lx, ly, anc, bbox, _halo_bbox)
                    break
                if placed:
                    break
            if placed:
                break
        if placed is None:
            # Could not find a clear slot — skip this label rather than emit an overlap the lint will flag. Journal
            # readers lose one out of five frequency annotations; better than a dirty page.
            continue
        lx, ly, anc, bbox, _halo_bbox = placed
        _placed_label_bbox.append(bbox)
        _placed_halo_bbox.append(_halo_bbox)
        parts.append(
            rigor.draw_label_with_halo(
                lx,
                ly,
                text,
                pal,
                fs=label_fs,
                anchor=anc,
                color=pal["ink6"],
                halo_alpha=0.85,
                italic=True,
            )
        )

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=magnitude_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=f"-Z'' ({magnitude_unit})" if magnitude_unit else "-Z''",
            side="left",
        )
    )
    parts.append(
        rigor.draw_x_axis(
            plot_x_left,
            plot_x_right,
            plot_y_bot,
            x_ticks,
            x_min,
            x_max,
            unit=magnitude_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Z' ({unit})", unit=magnitude_unit) if magnitude_unit else tr("Z'"),
        )
    )

    # top-right n points (opt-in bookkeeping)
    badge_fs = max(13.0, fs["label"])
    if show_count:
        parts.append(
            f'<text x="{plot_x_right - 6:.1f}" y="{plot_y_top + badge_fs + 6:.1f}" '
            f'font-size="{badge_fs:.1f}" fill="{pal["ink6"]}" text-anchor="end" '
            f'font-style="italic">{_xesc(tr("n points = {n}", n=N))}</text>'
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))
    return parts


def _draw_bode(
    *,
    bode_freq,
    bode_magnitude,
    bode_phase,
    pal,
    body_font,
    heading_font,
    fs,
    title,
    subtitle,
    figure_label,
    note,
    source,
    magnitude_unit,
    freq_unit,
    resonance_freq,
    log_freq,
    W,
    H,
    show_count=False,
):
    margin_top = 110
    margin_bot = 130
    margin_left = 120
    margin_right = 60
    if H < rigor.COMPACT_HEIGHT:
        margin_top, margin_bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source)
        )
        margin_right = min(margin_right, 40)
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    inner_gap = 50
    panel_h = (plot_y_bot - plot_y_top - inner_gap) * 0.5
    mag_top = plot_y_top
    mag_bot = plot_y_top + panel_h
    phi_top = mag_bot + inner_gap
    phi_bot = plot_y_bot

    f_min, f_max = min(bode_freq), max(bode_freq)
    if f_max == f_min:
        f_max = f_min * 10
    mag_min_data, mag_max_data = min(bode_magnitude), max(bode_magnitude)
    phi_min_data, phi_max_data = min(bode_phase), max(bode_phase)

    def Xf(v):
        if log_freq:
            return rigor._log_lin(v, f_min, f_max, plot_x_left, plot_x_right)
        return rigor._lin(v, f_min, f_max, plot_x_left, plot_x_right)

    if log_freq:
        mag_decades, mag_vmin_log, mag_vmax_log = rigor.log_axis(mag_min_data, mag_max_data)

        def Ym(v):
            return rigor._log_lin(v, mag_vmin_log, mag_vmax_log, mag_bot, mag_top)
    else:
        mag_ticks, mag_vmin, mag_vmax = rigor.nice_axis(mag_min_data, mag_max_data, 5)

        def Ym(v):
            return rigor._lin(v, mag_vmin, mag_vmax, mag_bot, mag_top)

    phi_ticks, phi_vmin, phi_vmax = rigor.nice_axis(phi_min_data, phi_max_data, 5)

    def Yp(v):
        return rigor._lin(v, phi_vmin, phi_vmax, phi_bot, phi_top)

    freq_decades, _, _ = rigor.log_axis(f_min, f_max) if log_freq else (None, None, None)

    parts = rigor.draw_canvas_bg(pal, W, H)
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            plot_y_top - 24,
            plot_x_right - plot_x_left,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )

    if log_freq:
        parts.append(
            rigor.draw_grid(
                plot_x_left,
                plot_x_right,
                mag_top,
                mag_bot,
                pal=pal,
                y_ticks=mag_decades,
                y_min=mag_vmin_log,
                y_max=mag_vmax_log,
                orient="horizontal",
                log_y=True,
            )
        )
    else:
        parts.append(
            rigor.draw_grid(
                plot_x_left,
                plot_x_right,
                mag_top,
                mag_bot,
                pal=pal,
                y_ticks=mag_ticks,
                y_min=mag_vmin,
                y_max=mag_vmax,
                orient="horizontal",
            )
        )
    d = " ".join(
        f"{'M' if i == 0 else 'L'} {Xf(f):.1f} {Ym(m):.1f}" for i, (f, m) in enumerate(zip(bode_freq, bode_magnitude))
    )
    parts.append(f'<path d="{d}" fill="none" stroke="{pal["accent"]}" stroke-width="2.0"/>')
    if log_freq:
        parts.append(
            rigor.draw_y_axis(
                plot_x_left,
                mag_top,
                mag_bot,
                mag_decades,
                mag_vmin_log,
                mag_vmax_log,
                unit=magnitude_unit,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=f"|Z| ({magnitude_unit})" if magnitude_unit else "|Z|",
                log=True,
                side="left",
            )
        )
    else:
        parts.append(
            rigor.draw_y_axis(
                plot_x_left,
                mag_top,
                mag_bot,
                mag_ticks,
                mag_vmin,
                mag_vmax,
                unit=magnitude_unit,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=f"|Z| ({magnitude_unit})" if magnitude_unit else "|Z|",
                side="left",
            )
        )
    # bottom border of mag panel (fake "x axis" line, no ticks on upper panel)
    parts.append(
        f'<line x1="{plot_x_left:.1f}" y1="{mag_bot:.1f}" '
        f'x2="{plot_x_right:.1f}" y2="{mag_bot:.1f}" '
        f'stroke="{pal["ink"]}" stroke-width="1.2"/>'
    )

    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            phi_top,
            phi_bot,
            pal=pal,
            y_ticks=phi_ticks,
            y_min=phi_vmin,
            y_max=phi_vmax,
            orient="horizontal",
        )
    )
    d = " ".join(
        f"{'M' if i == 0 else 'L'} {Xf(f):.1f} {Yp(p):.1f}" for i, (f, p) in enumerate(zip(bode_freq, bode_phase))
    )
    parts.append(f'<path d="{d}" fill="none" stroke="{pal.get("secondary", pal["ink"])}" stroke-width="2.0"/>')
    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            phi_top,
            phi_bot,
            phi_ticks,
            phi_vmin,
            phi_vmax,
            unit="°",
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Phase (°)"),
            side="left",
        )
    )
    # X axis under phase panel (log frequency)
    if log_freq:
        parts.append(
            rigor.draw_x_axis(
                plot_x_left,
                plot_x_right,
                phi_bot,
                freq_decades,
                f_min,
                f_max,
                unit=freq_unit,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=tr("Frequency ({unit})", unit=freq_unit) if freq_unit else tr("Frequency"),
                log=True,
            )
        )
    else:
        xt, _, _ = rigor.nice_axis(f_min, f_max, 6)
        parts.append(
            rigor.draw_x_axis(
                plot_x_left,
                plot_x_right,
                phi_bot,
                xt,
                f_min,
                f_max,
                unit=freq_unit,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=tr("Frequency ({unit})", unit=freq_unit) if freq_unit else tr("Frequency"),
            )
        )

    if resonance_freq is not None and f_min <= resonance_freq <= f_max:
        rx = Xf(resonance_freq)
        parts.append(
            f'<line x1="{rx:.1f}" y1="{mag_top:.1f}" x2="{rx:.1f}" y2="{phi_bot:.1f}" '
            f'stroke="{pal["accent"]}" stroke-width="1.4" stroke-dasharray="6 4"/>'
        )
        parts.append(
            f'<text x="{rx + 6:.1f}" y="{mag_top + fs["label"] + 4:.1f}" '
            f'font-size="{max(13.0, fs["label"]):.1f}" fill="{pal["accent"]}" '
            f'font-style="italic" font-weight="600">f_res = {_format_freq(resonance_freq)}</text>'
        )

    # top-right n points (opt-in bookkeeping)
    badge_fs = max(13.0, fs["label"])
    if show_count:
        parts.append(
            f'<text x="{plot_x_right - 6:.1f}" y="{plot_y_top + badge_fs + 6:.1f}" '
            f'font-size="{badge_fs:.1f}" fill="{pal["ink6"]}" text-anchor="end" '
            f'font-style="italic">{_xesc(tr("n points = {n}", n=len(bode_freq)))}</text>'
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))
    return parts


def make_nyquist_bode(
    *,
    mode: str = "nyquist",
    nyquist_points=None,
    bode_freq=None,
    bode_magnitude=None,
    bode_phase=None,
    magnitude_unit: str = "Ω",
    freq_unit: str = "Hz",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_freq_labels: bool = True,
    resonance_freq=None,
    log_freq: bool = True,
    show_count: bool = False,
    width: float = 1300,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    models=None,
) -> str:
    """Nyquist or Bode plot.

    ``mode="nyquist"``: pass ``nyquist_points`` as a list of
    ``(Z_real, -Z_imag, freq)`` triples (``freq`` may be omitted — then
    frequency labels are skipped). ``models=[{"name": "R(RQ)W 拟合", "points": [(Z', -Z''), ...]}]`` overlays
    equivalent-circuit fits (dashed); a Warburg tail in the model extends the axes instead of being clipped.
    ``magnitude_unit="Ω·cm²"`` goes into the axis titles (no separate unit labels).

    ``mode="bode"``: pass ``bode_freq``, ``bode_magnitude``, ``bode_phase``
    (parallel lists). ``log_freq`` toggles log-X for the shared frequency axis.
    ``show_count=True`` adds an "n points" badge (off by default: bookkeeping).
    """
    _variant_is_classic("nyquist_bode", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    if mode == "nyquist":
        if not nyquist_points:
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
                f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
                f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
            )
        n = len(nyquist_points)
        fs = _dist_font_sizes(W, H, max(4, n))
        parts = _draw_nyquist(
            nyquist_points,
            pal=pal,
            body_font=body_font,
            heading_font=heading_font,
            fs=fs,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            magnitude_unit=magnitude_unit,
            show_freq_labels=show_freq_labels,
            W=W,
            H=H,
            show_count=show_count,
            models=models,
        )
    elif mode == "bode":
        if not bode_freq or not bode_magnitude or not bode_phase:
            return (
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
                f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
                f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
            )
        n = len(bode_freq)
        fs = _dist_font_sizes(W, H, max(4, n))
        parts = _draw_bode(
            bode_freq=bode_freq,
            bode_magnitude=bode_magnitude,
            bode_phase=bode_phase,
            pal=pal,
            body_font=body_font,
            heading_font=heading_font,
            fs=fs,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            magnitude_unit=magnitude_unit,
            freq_unit=freq_unit,
            resonance_freq=resonance_freq,
            log_freq=log_freq,
            W=W,
            H=H,
            show_count=show_count,
        )
    else:
        raise ValueError(f"mode must be 'nyquist' or 'bode', got {mode!r}")

    return rigor.wrap_svg(parts, W, H, body_font)
