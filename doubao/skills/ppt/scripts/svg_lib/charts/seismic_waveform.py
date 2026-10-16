"""Academic chart: multi-trace seismic waveform display with event picks."""

from __future__ import annotations

import math

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _pick_series_colors,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr


# Multi-mode whitelist:
#   with_spectrogram: STFT of the first trace, rendered as a time-frequency
#   heatmap in a bottom sub-panel. Shares the X (time) domain with the main
#   waveform tracks via a ``top_bottom_2to1`` template.
def _validate_with_spectrogram(signals):
    traces = signals.get("traces") or []
    if not traces:
        return (False, "no traces")
    first = traces[0]
    n_samp = len(first.get("amplitude") or [])
    if n_samp < 128:
        return (False, "need >= 128 samples in first trace")
    return (True, "")


_SEISMIC_MULTI_WHITELIST = {
    "with_spectrogram": (
        "top_bottom_2to1",
        lambda s: len(s.get("traces") or []) >= 1 and len((s.get("traces") or [{}])[0].get("amplitude") or []) >= 128,
        lambda s: _validate_with_spectrogram(s),
    ),
}


def _stft_magnitudes(samples, window: int, hop: int):
    """Pure-stdlib short-time Fourier transform magnitude matrix."""
    n = len(samples)
    if window < 4 or hop < 1 or n < window:
        return ([], [], [])
    win = [0.5 * (1.0 - math.cos(2 * math.pi * i / (window - 1))) for i in range(window)]
    n_bins = window // 2
    times_idx = []
    mag = []
    # Pre-tabulate twiddles cos/sin to avoid recomputing per frame.
    # cos_tab[k][i] = cos(2*pi*k*i/window)
    cos_tab = [None] * n_bins
    sin_tab = [None] * n_bins
    for k in range(n_bins):
        cs = [math.cos(2 * math.pi * k * i / window) for i in range(window)]
        ss = [math.sin(2 * math.pi * k * i / window) for i in range(window)]
        cos_tab[k] = cs
        sin_tab[k] = ss
    t = 0
    while t + window <= n:
        times_idx.append(t + window / 2.0)  # frame center
        frame = [samples[t + i] * win[i] for i in range(window)]
        row = [0.0] * n_bins
        for k in range(n_bins):
            re = 0.0
            im = 0.0
            cs = cos_tab[k]
            ss = sin_tab[k]
            for i in range(window):
                v = frame[i]
                re += v * cs[i]
                im -= v * ss[i]
            row[k] = math.sqrt(re * re + im * im)
        mag.append(row)
        t += hop
    freqs_idx = list(range(n_bins))
    return (times_idx, freqs_idx, mag)


def _series_color(pal, i, n_series: int | None = None):
    """Per-trace color."""
    series_colors = pal.get("series")
    if series_colors and i < len(series_colors):
        return series_colors[i]
    if n_series and n_series > 0:
        cols = _pick_series_colors(pal, n_series)
        return cols[i % len(cols)]
    palette_order = [
        pal.get("ink", "rgba(28,28,26,1)"),
        pal.get("accent", "rgba(163,88,50,1)"),
        pal.get("secondary", "rgba(28,28,26,0.6)"),
    ]
    return palette_order[i % len(palette_order)]


def make_seismic_waveform(
    traces,
    events=None,
    *,
    time_unit: str = "s",
    amp_unit: str = "nm/s",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    stacked: bool = True,
    show_grid: bool = True,
    width: float = 1400,
    height: float = 760,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """Stacked seismic waveforms with event picks.

    Each entry in ``traces``:
        ``name``: str
        ``time``: list[float]
        ``amplitude``: list[float]
    Each entry in ``events`` (optional):
        ``time``: float
        ``label``: str (e.g. "P", "S")
        ``magnitude``: float optional
    Returns a complete ``<svg>...</svg>`` string.
    """
    _variant_is_classic("seismic_waveform", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    traces = [t for t in (traces or []) if t.get("time") and t.get("amplitude")]
    events = events or []
    n_tr = len(traces)
    fs = _dist_font_sizes(W, H, max(n_tr, 4))

    if not traces:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    all_t = []
    for t in traces:
        all_t.extend(t["time"])
    for ev in events:
        if "time" in ev:
            all_t.append(ev["time"])
    t_min, t_max = min(all_t), max(all_t)
    if t_max == t_min:
        t_max = t_min + 1
    t_ticks, _, _ = rigor.nice_axis(t_min, t_max, 8)

    trace_amp = []  # (lo, hi)
    for t in traces:
        amps = t["amplitude"]
        trace_amp.append((min(amps), max(amps)))

    # for shared y mapping (stacked), compute global span
    global_amp = max(abs(hi) + abs(lo) for lo, hi in trace_amp)
    if global_amp <= 0:
        global_amp = 1.0

    # Pre-scan events to estimate how many stacked label rows we'll need,
    # so we can push the plot area down and avoid chips invading the title.
    lbl_fs_pre = max(13.0, fs["label"])
    sorted_events_pre = sorted(
        [ev for ev in (events or []) if ev.get("time") is not None and t_min <= ev.get("time") <= t_max],
        key=lambda e: e["time"],
    )

    # width estimator mirrors the one used below
    def _ev_text(ev):
        lab = ev.get("label", "")
        mag = ev.get("magnitude")
        if mag is not None:
            return f"{lab} · M{mag:.1f}" if lab else f"M{mag:.1f}"
        return lab

    # tentative t range → tentative x-range for pre-layout
    # (we don't know plot_x_left/right yet; approximate via W)
    pre_left = 110
    pre_right = W - 70
    pre_span = max(1e-6, t_max - t_min)
    pre_rows = []
    for ev in sorted_events_pre:
        txt = _ev_text(ev)
        if not txt:
            continue
        w = _estimate_label_width_px(txt, lbl_fs_pre, font_family=body_font) + 10
        xx = pre_left + (ev["time"] - t_min) / pre_span * (pre_right - pre_left)
        xl, xr = xx - w * 0.5, xx + w * 0.5
        placed = None
        for ri, r_right in enumerate(pre_rows):
            if xl > r_right + 6:
                pre_rows[ri] = xr
                placed = ri
                break
        if placed is None:
            pre_rows.append(xr)
    n_rows_est = max(1, len(pre_rows))
    row_step_pre = lbl_fs_pre + 6
    chip_h_pre = lbl_fs_pre + 6
    # Compute the exact height of the title block so we can reserve a dedicated event-ribbon strip BELOW the title block
    # (not above it).
    _title_fs = fs["title"]
    _subtitle_fs = fs["subtitle"]
    _figure_fs = fs["figure"]
    _title_h = 0.0
    if subtitle:
        _title_h += _subtitle_fs + 6
    if title:
        _title_h += _title_fs + 8
    if figure_label:
        _title_h += _figure_fs + 4
    # Add 4px for the glyph-top safety padding the renderer adds, plus 2px.
    _title_h += 6.0
    # Reserve top margin for: title block + its 24 px below-baseline anchor offset + event ribbon rows + chip height +
    # 10 px breathing between the title block bottom and the top of the first ribbon row.
    ribbon_strip_h = n_rows_est * row_step_pre + chip_h_pre + 10
    margin_top = _title_h + 24 + ribbon_strip_h + 10
    margin_bot = 130
    # left margin: trace names now draw INLINE at trace start (not in the
    # Y-axis gutter), so we only need enough room for the rotated amplitude
    # axis title.
    margin_left = 90
    margin_right = 92  # +22 for optional spectrogram colorbar + "p95"/"p5" labels

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    _plot_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _signals = {"traces": traces, "n_traces": n_tr}
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _SEISMIC_MULTI_WHITELIST,
        _signals,
        _plot_bbox,
    )
    _sub_bbox = None
    _sub_title_h = 0.0
    if _mm_mode is not None and _mm_template is not None:
        _rects = rigor.allocate_main_sub(_plot_bbox, _mm_template)
        _main_bb = _rects["main"]
        _sub_bbox = _rects["sub"]
        plot_y_bot = _main_bb.y1  # shrink main vertically; share X domain
        # Reserve space for the sub-panel title INSIDE the sub-panel top
        # (not above the panel, which would collide with the last trace).
        _sub_title_h = 22.0

    def X(t):
        return rigor._lin(t, t_min, t_max, plot_x_left, plot_x_right)

    parts = rigor.draw_canvas_bg(pal, W, H)

    # title block — anchor it near the top of the viewBox (not just above the
    # plot) so the event-ribbon strip can live between the title bottom and
    # plot_y_top without colliding with either.
    title_anchor_y = _title_h + 24  # subtitle baseline sits here
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            title_anchor_y,
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
    # title_block_bottom is the baseline y of the subtitle (if present) or
    # the lowest text in the title block.
    title_block_bottom = title_anchor_y + 4  # include descender slack

    if show_grid:
        parts.append(
            rigor.draw_grid(
                plot_x_left,
                plot_x_right,
                plot_y_top,
                plot_y_bot,
                pal=pal,
                x_ticks=t_ticks,
                x_min=t_min,
                x_max=t_max,
                orient="vertical",
            )
        )

    plot_h = plot_y_bot - plot_y_top
    if stacked and n_tr > 0:
        row_h = plot_h / n_tr
    else:
        row_h = plot_h
    # amp -> screen y mapping scale (half row height is max deflection)
    half_h = row_h * 0.42

    ink6 = pal["ink6"]
    ink4 = pal["ink4"]

    for i, trace in enumerate(traces):
        baseline_y = plot_y_top + row_h * (i + 0.5)
        amps = trace["amplitude"]
        times = trace["time"]
        lo, hi = trace_amp[i]
        amp_span = max(abs(lo), abs(hi), 1e-12)
        c = _series_color(pal, i, n_tr)

        parts.append(
            f'<line x1="{plot_x_left:.1f}" y1="{baseline_y:.1f}" '
            f'x2="{plot_x_right:.1f}" y2="{baseline_y:.1f}" '
            f'stroke="{ink4}" stroke-width="0.8"/>'
        )

        # Use a small halo so the text stays readable even when a waveform swings through its position.
        name = trace.get("name", tr("Trace {i}", i=i + 1))
        name_fs = max(13.0, fs["ytick"])
        parts.append(
            rigor.draw_label_with_halo(
                plot_x_left + 6,
                baseline_y - half_h + name_fs,
                name,
                pal,
                fs=name_fs,
                anchor="start",
                color=pal["ink"],
                halo_alpha=0.85,
            )
        )

        d_parts = []
        for k, (tv, av) in enumerate(zip(times, amps)):
            if tv < t_min or tv > t_max:
                continue
            xs = X(tv)
            ys = baseline_y - (av / amp_span) * half_h
            d_parts.append(f"{'M' if k == 0 else 'L'} {xs:.1f} {ys:.1f}")
        if d_parts:
            parts.append(f'<path d="{" ".join(d_parts)}" fill="none" stroke="{c}" stroke-width="1.1"/>')

        amp_fs = max(13.0, fs["label"] * 0.85)
        amp_val = amp_span
        parts.append(
            f'<text x="{plot_x_right + 6:.1f}" y="{baseline_y - half_h + amp_fs:.1f}" '
            f'font-size="{amp_fs}" fill="{ink6}" font-style="italic">'
            f"±{amp_val:.2g}</text>"
        )

    # Label collision avoidance: when events crowd a short time window the top chips otherwise clip each other ("S" → "S
    # · M5." → "pP · M5").
    event_colors = {
        "P": pal.get("accent", "rgba(163,88,50,1)"),
        "S": pal.get("secondary", "rgba(42,86,122,1)"),
    }
    lbl_fs = max(13.0, fs["label"])
    sorted_events = sorted(
        [ev for ev in events if ev.get("time") is not None and t_min <= ev.get("time") <= t_max],
        key=lambda e: e["time"],
    )
    # Build label text + width per event, assign row index to minimise overlap.
    row_right_edges = []  # per row: rightmost x occupied so far (plus padding)
    event_rows = []  # same length as sorted_events: row index
    label_texts = []
    label_widths = []
    for ev in sorted_events:
        lab = ev.get("label", "")
        mag = ev.get("magnitude")
        if mag is not None:
            text_val = f"{lab} · M{mag:.1f}" if lab else f"M{mag:.1f}"
        else:
            text_val = lab
        label_texts.append(text_val)
        w = _estimate_label_width_px(text_val, lbl_fs, font_family=body_font) + 10
        label_widths.append(w)
        xx = X(ev["time"])
        xl = xx - w * 0.5
        xr = xx + w * 0.5
        pad = 6.0
        placed_row = None
        for ri, right in enumerate(row_right_edges):
            if xl > right + pad:
                row_right_edges[ri] = xr
                placed_row = ri
                break
        if placed_row is None:
            row_right_edges.append(xr)
            placed_row = len(row_right_edges) - 1
        event_rows.append(placed_row)

    row_step = lbl_fs + 6
    chip_h = lbl_fs + 6
    # Place event chips in a dedicated ribbon between the title block and the plot area.
    ribbon_top = title_block_bottom + 10
    # If we somehow computed too much slack (e.g. only 1 row), still cap the
    # bottom of the lowest row so it sits >= 10 px above plot_y_top.
    max_ribbon_bottom = plot_y_top - 10
    for ev, text_val, w, row in zip(sorted_events, label_texts, label_widths, event_rows):
        et = ev["time"]
        lab = ev.get("label", "")
        xx = X(et)
        c = event_colors.get(lab, pal["ink"])
        # vertical dashed line spans full plot area
        parts.append(
            f'<line x1="{xx:.1f}" y1="{plot_y_top:.1f}" x2="{xx:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{c}" stroke-width="1.3" stroke-dasharray="5 3"/>'
        )
        if text_val:
            lbl_y = ribbon_top + row * row_step
            # Hard clamp so no row ever dips into the plot area.
            if lbl_y + chip_h > max_ribbon_bottom:
                lbl_y = max_ribbon_bottom - chip_h
            parts.append(
                f'<rect x="{xx - w * 0.5:.1f}" y="{lbl_y:.1f}" width="{w:.1f}" '
                f'height="{chip_h:.1f}" fill="{pal.get("bg", "rgba(255,255,255,0.9)")}" '
                f'stroke="{c}" stroke-width="0.8"/>'
            )
            parts.append(
                f'<text x="{xx:.1f}" y="{lbl_y + lbl_fs:.1f}" font-size="{lbl_fs}" '
                f'fill="{c}" text-anchor="middle" font-weight="700">{_xesc(text_val)}</text>'
            )
            # short connector tick from chip bottom to plot_y_top so the chip
            # feels attached to its vertical dashed line.
            parts.append(
                f'<line x1="{xx:.1f}" y1="{lbl_y + chip_h:.1f}" '
                f'x2="{xx:.1f}" y2="{plot_y_top:.1f}" '
                f'stroke="{c}" stroke-width="0.6" stroke-dasharray="2 2"/>'
            )

    # X axis. When a sub-panel owns the shared X domain, the main plot's
    # bottom gets only a boundary line (no tick labels) and the real X axis
    # with ticks + title is drawn at the sub-panel bottom. Otherwise the X
    # axis sits at the main plot_y_bot as usual.
    if _sub_bbox is not None:
        parts.append(
            f'<line x1="{plot_x_left:.1f}" y1="{plot_y_bot:.1f}" '
            f'x2="{plot_x_right:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{pal["ink"]}" stroke-width="1.2" data-role="x-axis"/>'
        )
    else:
        parts.append(
            rigor.draw_x_axis(
                plot_x_left,
                plot_x_right,
                plot_y_bot,
                t_ticks,
                t_min,
                t_max,
                unit=time_unit,
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=tr("Time"),
            )
        )

    parts.append(
        f'<line x1="{plot_x_left:.1f}" y1="{plot_y_top:.1f}" '
        f'x2="{plot_x_left:.1f}" y2="{plot_y_bot:.1f}" '
        f'stroke="{pal["ink"]}" stroke-width="1.2" data-role="y-axis"/>'
    )
    amp_title = tr("Amplitude ({unit})", unit=amp_unit) if amp_unit else tr("Amplitude")
    cx = plot_x_left - margin_left * 0.65
    cy_mid = (plot_y_top + plot_y_bot) * 0.5
    parts.append(
        f'<text x="{cx:.1f}" y="{cy_mid:.1f}" font-size="{fs["yaxis"]}" '
        f'fill="{pal["ink"]}" text-anchor="middle" font-weight="600" '
        f'transform="rotate(-90 {cx:.1f} {cy_mid:.1f})">{_xesc(amp_title)}</text>'
    )

    counts_text = tr("n traces = {traces}, n events = {events}", traces=n_tr, events=len(events))
    parts.append(
        f'<text x="{plot_x_right - 10:.1f}" y="{title_block_bottom:.1f}" '
        f'font-size="{fs["label"]}" fill="{pal["ink6"]}" '
        f'text-anchor="end" font-style="italic">{counts_text}</text>'
    )

    if _sub_bbox is not None and _mm_mode == "with_spectrogram":
        first_trace = traces[0]
        samples = list(first_trace.get("amplitude") or [])
        tr_times = list(first_trace.get("time") or [])
        n_samp = len(samples)
        window = min(64, max(8, n_samp // 8))
        # Keep window even so (window // 2) bins are well-defined.
        if window % 2:
            window -= 1
        hop = max(1, window // 2)
        _t_idx, _f_idx, _mag = _stft_magnitudes(samples, window, hop)

        sx_left, sx_right, sy_top, sy_bot = rigor.bbox_to_edges(_sub_bbox)
        # Clamp sub-panel left to the main plot_x_left so the heatmap stays
        # aligned with the waveform X axis (strict shared-X).
        sx_left = plot_x_left
        sx_right = plot_x_right
        # Carve out an interior strip at the top of the sub-panel for the
        # title "Spectrogram (STFT, trace 1)" so the title lives INSIDE the
        # panel (not in the trace strip above where it collides with trace N).
        sy_heat_top = sy_top + _sub_title_h

        if _mag and _t_idx and _f_idx:
            # Map sample-index -> time for X mapping. Fall back to linear
            # interpolation across the trace's time array if provided.
            def _idx_to_time(idx):
                if tr_times:
                    i0 = math.floor(idx)
                    i1 = min(len(tr_times) - 1, i0 + 1)
                    frac = idx - i0
                    if i0 >= len(tr_times):
                        return tr_times[-1]
                    return tr_times[i0] + frac * (tr_times[i1] - tr_times[i0])
                return idx  # fallback: index as time

            frame_times = [_idx_to_time(ix) for ix in _t_idx]
            # Max bin value dominates the ramp when a single frame has a transient spike (e.g. the P-arrival), leaving
            # the rest of the grid as near-pure background.
            flat = sorted(v for row in _mag for v in row)
            if flat:

                def _pct(p):
                    if not flat:
                        return 0.0
                    k = (len(flat) - 1) * p
                    lo_i = math.floor(k)
                    hi_i = math.ceil(k)
                    if lo_i == hi_i:
                        return flat[lo_i]
                    return flat[lo_i] + (flat[hi_i] - flat[lo_i]) * (k - lo_i)

                m_min = _pct(0.05)
                m_max = _pct(0.95)
            else:
                m_min, m_max = 0.0, 1.0
            if abs(m_max - m_min) < 1e-12:
                m_max = m_min + 1.0

            n_frames = len(frame_times)
            n_bins = len(_mag[0])

            # Cell width: frame interval mapped to screen; cell height: freq
            # bin on the sub panel.
            def _SX(tv):
                return rigor._lin(tv, t_min, t_max, sx_left, sx_right)

            def _SY_bin(b):
                # low-frequency bin at bottom, high at top (invert y)
                return rigor._lin(b, 0, n_bins - 1, sy_bot, sy_heat_top)

            # Each cell: half-frame-width to each side, half-bin-height each side.
            if n_frames >= 2:
                frame_dt = (frame_times[-1] - frame_times[0]) / max(1, n_frames - 1)
            else:
                frame_dt = (t_max - t_min) * 0.1
            cell_w_px = max(1.5, _SX(frame_times[0] + frame_dt) - _SX(frame_times[0]))
            cell_h_px = max(1.5, abs(_SY_bin(1) - _SY_bin(0)))
            # +0.5 to kill 1-px gaps on rasterised backends
            cell_w_px += 0.5
            cell_h_px += 0.5

            for ti, tv in enumerate(frame_times):
                cx = _SX(tv) - cell_w_px * 0.5
                for bi in range(n_bins):
                    v = _mag[ti][bi]
                    # Clamp into [m_min, m_max] so percentile clipping bites.
                    vv = max(m_min, min(m_max, v))
                    col = rigor.value_to_color(vv, m_min, m_max, pal=pal)
                    cy = _SY_bin(bi) - cell_h_px * 0.5
                    parts.append(
                        f'<rect x="{cx:.2f}" y="{cy:.2f}" '
                        f'width="{cell_w_px:.2f}" height="{cell_h_px:.2f}" '
                        f'fill="{col}" stroke="none"/>'
                    )

            # Sub-panel border — full panel including title strip.
            parts.append(
                f'<rect x="{sx_left:.1f}" y="{sy_top:.1f}" '
                f'width="{(sx_right - sx_left):.1f}" '
                f'height="{(sy_bot - sy_top):.1f}" '
                f'fill="none" stroke="{pal["ink"]}" stroke-width="1.0"/>'
            )
            # Thin divider between title strip and heatmap.
            parts.append(
                f'<line x1="{sx_left:.1f}" y1="{sy_heat_top:.1f}" '
                f'x2="{sx_right:.1f}" y2="{sy_heat_top:.1f}" '
                f'stroke="{pal["ink4"]}" stroke-width="0.6"/>'
            )
            sub_fs = max(10.0, fs["label"] * 0.85)
            # Freq-bin labels: 0, mid, max. Nudge them further left so they clear the main-plot amplitude title and
            # never bleed into the waveform strip above.
            for b, lbl in [(0, "0"), (n_bins // 2, f"{n_bins // 2}"), (n_bins - 1, f"{n_bins - 1}")]:
                y = _SY_bin(b)
                # Keep label vertically bounded inside the heatmap region so
                # the top "max" label doesn't bleed up into the title strip.
                y_clamped = max(sy_heat_top + sub_fs * 0.6, min(sy_bot - 2, y + sub_fs * 0.35))
                parts.append(
                    f'<text x="{sx_left - 10:.1f}" y="{y_clamped:.1f}" '
                    f'font-size="{sub_fs:.1f}" fill="{pal["ink6"]}" '
                    f'text-anchor="end">{lbl}</text>'
                )
            # Rotated sub-axis title (freq bin) — anchor at the heatmap center.
            cy_sub = (sy_heat_top + sy_bot) * 0.5
            cx_sub = sx_left - margin_left * 0.55
            parts.append(
                f'<text x="{cx_sub:.1f}" y="{cy_sub:.1f}" '
                f'font-size="{sub_fs:.1f}" fill="{pal["ink"]}" '
                f'text-anchor="middle" font-weight="600" '
                f'transform="rotate(-90 {cx_sub:.1f} {cy_sub:.1f})">{_xesc(tr("Freq bin"))}</text>'
            )
            # Caption INSIDE the sub-panel's reserved title strip.
            cap_fs = max(11.0, fs["label"] * 0.92)
            cap_y = sy_top + _sub_title_h * 0.5 + cap_fs * 0.35
            parts.append(
                f'<text x="{sx_left + 8:.1f}" y="{cap_y:.1f}" '
                f'font-size="{cap_fs:.1f}" fill="{pal["ink"]}" '
                f'font-weight="700">Spectrogram (STFT, trace 1)</text>'
            )
            # Colorbar on the right edge of the sub-panel so viewers can tell that 5th/95th percentile clipping is
            # applied (annotate as ``p5``/``p95``).
            cbar_w = 10.0
            cbar_x = sx_right + 6
            cbar_y = sy_heat_top + 4
            cbar_h = max(20.0, (sy_bot - sy_heat_top) - 8)
            parts.append(
                rigor.draw_colorbar(
                    cbar_x,
                    cbar_y,
                    cbar_w,
                    cbar_h,
                    m_min,
                    m_max,
                    pal=pal,
                    orient="vertical",
                    fs_tick=max(9.5, sub_fs * 0.9),
                )
            )
            # Mark that the limits are percentile clips (not raw min/max).
            parts.append(
                f'<text x="{cbar_x + cbar_w + 4:.1f}" y="{cbar_y + 10:.1f}" '
                f'font-size="{sub_fs * 0.85:.1f}" fill="{pal["ink6"]}" '
                f'font-style="italic">p95</text>'
            )
            parts.append(
                f'<text x="{cbar_x + cbar_w + 4:.1f}" y="{cbar_y + cbar_h - 2:.1f}" '
                f'font-size="{sub_fs * 0.85:.1f}" fill="{pal["ink6"]}" '
                f'font-style="italic">p5</text>'
            )
            # Shared X axis lives at the sub-panel BOTTOM when a spectrogram
            # is drawn — the main plot gets only a boundary line.
            parts.append(
                rigor.draw_x_axis(
                    sx_left,
                    sx_right,
                    sy_bot,
                    t_ticks,
                    t_min,
                    t_max,
                    unit=time_unit,
                    pal=pal,
                    fs_tick=fs["ytick"],
                    fs_title=fs["yaxis"],
                    title=tr("Time"),
                )
            )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)
