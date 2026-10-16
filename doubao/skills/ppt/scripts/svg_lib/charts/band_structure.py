"""Academic chart: electronic band structure (energy vs k-space with high-symmetry
points, Fermi level, and optional DOS side panel). Returns a complete
"""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _resolve_font,
    _resolve_palette,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from ._shared import tr

_BAND_MULTI_WHITELIST = {
    "with_dos": (
        "left_right_3to1",  # template used by can_fit_multi_v2
        lambda s: s.get("has_dos", False),
        lambda s: (
            s.get("has_dos", False) and len(s.get("dos_data", []) or []) >= 10,
            "dos_data missing or <10 points",
        ),
    ),
}


def _normalize_bands(bands):
    """Accept either the historical list-of-dicts form or a simpler list of energy arrays (``[[E,...], ...]``)."""
    norm = []
    for i, b in enumerate(bands or []):
        if isinstance(b, dict):
            norm.append(b)
            continue
        # Plain sequence of energies — synthesize uniform k_points in [0, 1].
        try:
            es = list(b)
        except TypeError:
            continue
        if not es:
            continue
        n = len(es)
        if n == 1:
            ks = [0.0]
        else:
            ks = [j / (n - 1) for j in range(n)]
        norm.append(
            {
                "name": tr("band {i}", i=i + 1),
                "k_points": ks,
                "energies": es,
                "is_valence": False,
            }
        )
    return norm


def make_band_structure(
    bands,
    *,
    high_symmetry_points=None,
    fermi_level: float = 0.0,
    energy_unit: str = "eV",
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_dos_panel: bool = False,
    dos_values=None,
    dos_data=None,
    multi_mode: str | None = None,
    width: float = 1300,
    height: float = 820,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """Band structure chart.

    Parameters
    ----------
    bands : list
        Either a list of dicts (``{name, k_points, energies, is_valence}``),
        or a plain list of energy arrays (``[[E,...], ...]``).
    high_symmetry_points : list of ``(k_coord, label)``, optional
        E.g. ``[(0.0, "Γ"), (0.5, "X"), (1.0, "M"), ...]``. Default is a
        placeholder ``Γ``–``X`` pair when omitted.
    fermi_level : float
        Energy value for the horizontal Fermi dashed line.
    show_dos_panel : bool
        Legacy flag: when True and ``dos_values`` is set, draw a DOS panel.
    dos_values, dos_data : list of ``(energy, dos)``
        DOS curve values. ``dos_data`` is the preferred modern name used by
        the ``multi_mode`` whitelist; ``dos_values`` is kept for back-compat.
    multi_mode : str, optional
        ``None`` / ``"off"`` / ``"single"`` — single-figure mode.
        ``"auto"`` — resolve via ``_BAND_MULTI_WHITELIST`` (silent fallback).
        ``"with_dos"`` — explicit DOS side panel; silent fallback if invalid.
    """
    _variant_is_classic("band_structure", variant)
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    bands = _normalize_bands(bands)
    n_bands = len(bands)
    fs = _dist_font_sizes(W, H, max(4, min(12, n_bands)))

    # Unified DOS source — ``dos_data`` takes precedence (new API).
    dos_curve = dos_data if dos_data is not None else dos_values

    margin_top = 110
    margin_bot = 130
    margin_left = 110
    margin_right = 60
    if H < rigor.COMPACT_HEIGHT:
        # Short slide canvases: size margins from the text actually drawn.
        margin_top, margin_bot, margin_left = rigor.compact_margins(
            fs, title=title, subtitle=subtitle, figure_label=figure_label, footer=bool(note or source)
        )
        margin_right = 28
    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    canvas_bbox = rigor.bbox_from_edges(
        plot_x_left,
        plot_x_right,
        plot_y_top,
        plot_y_bot,
    )
    data_signals = {
        "has_dos": bool(dos_curve),
        "dos_data": list(dos_curve) if dos_curve else [],
    }
    # Legacy ``show_dos_panel`` upgrades the request so old callers keep working.
    requested = multi_mode
    if requested is None and show_dos_panel and dos_curve:
        requested = "with_dos"

    mode, _template, _reason = rigor.resolve_multi_mode_v2(
        requested,
        _BAND_MULTI_WHITELIST,
        data_signals,
        canvas_bbox,
    )

    use_dos_panel = mode == "with_dos" and dos_curve and len(dos_curve) >= 10

    if use_dos_panel:
        tracks = rigor.allocate_tracks(
            canvas_bbox,
            weights=[3, 1],
            gutter=28.0,
            orient="h",
        )
        band_bbox, dos_bbox = tracks[0], tracks[1]
        band_x_left = band_bbox.x0
        band_x_right = band_bbox.x1
        dos_x_left = dos_bbox.x0
        dos_x_right = dos_bbox.x1
    else:
        band_x_left = plot_x_left
        band_x_right = plot_x_right
        dos_x_left = None
        dos_x_right = None

    all_e = []
    all_k = []
    for b in bands:
        all_e.extend(b.get("energies", []))
        all_k.extend(b.get("k_points", []))
    all_e.append(fermi_level)
    if dos_curve:
        for ev, _ in dos_curve:
            all_e.append(ev)
    if not all_e or not all_k:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No data"))}</text></svg>'
        )

    e_ticks, e_min, e_max = rigor.nice_axis(min(all_e), max(all_e), 6)
    k_min = min(all_k)
    k_max = max(all_k)
    if k_max == k_min:
        k_max = k_min + 1.0

    # Shared Y energy scale across both panels — identical pixel positions.
    y_scale = rigor.SharedScale(domain=(e_min, e_max), ticks=e_ticks)

    def X(v):
        return rigor._lin(v, k_min, k_max, band_x_left, band_x_right)

    def Y(v):
        # Pixel origin: top of plot box; shared across both panels.
        return y_scale.map(v, plot_y_bot, plot_y_top)

    # Default HSP when caller omits them (e.g. the new simpler API).
    if not high_symmetry_points:
        high_symmetry_points = [(k_min, "Γ"), (k_max, "X")]

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

    # background horizontal grid (energy ticks) — left panel only
    parts.append(
        rigor.draw_grid(
            band_x_left,
            band_x_right,
            plot_y_top,
            plot_y_bot,
            pal=pal,
            y_ticks=e_ticks,
            y_min=e_min,
            y_max=e_max,
            orient="horizontal",
        )
    )

    ink2 = pal["ink2"]
    for k_coord, _ in high_symmetry_points:
        if k_coord < k_min - 1e-9 or k_coord > k_max + 1e-9:
            continue
        xk = X(k_coord)
        parts.append(
            f'<line x1="{xk:.1f}" y1="{plot_y_top:.1f}" x2="{xk:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{ink2}" stroke-width="1"/>'
        )

    yf = Y(fermi_level)
    fermi_color = pal["accent"]
    if use_dos_panel:
        # Use the cross-panel source marker so the Fermi line visibly ties
        # the k-space panel to the DOS panel.
        parts.append(
            rigor.draw_source_marker(
                "hline",
                pal=pal,
                y=yf,
                x0=band_x_left,
                x1=dos_x_right,
            )
        )
    else:
        parts.append(
            f'<line x1="{band_x_left:.1f}" y1="{yf:.1f}" x2="{band_x_right:.1f}" y2="{yf:.1f}" '
            f'stroke="{fermi_color}" stroke-width="1.6" stroke-dasharray="6 4"/>'
        )
    f_label_x = dos_x_right if use_dos_panel else band_x_right
    parts.append(
        f'<text x="{f_label_x - 6:.1f}" y="{yf - 6:.1f}" font-size="{max(13.0, fs["label"]):.1f}" '
        f'fill="{fermi_color}" text-anchor="end" font-style="italic" '
        f'font-weight="600">E<tspan baseline-shift="sub" font-size="{max(10.0, fs["label"] * 0.7):.1f}">F</tspan></text>'
    )

    valence_color = pal.get("secondary", _rgba_with_alpha(pal["ink"], 0.75))
    conduction_color = pal["accent"]
    for b in bands:
        kp = b.get("k_points", [])
        ep = b.get("energies", [])
        if len(kp) < 2 or len(ep) < 2:
            continue
        is_valence = bool(b.get("is_valence", False))
        c = valence_color if is_valence else conduction_color
        d = " ".join(f"{'M' if i == 0 else 'L'} {X(k):.1f} {Y(e):.1f}" for i, (k, e) in enumerate(zip(kp, ep)))
        parts.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.0" stroke-linejoin="round"/>')

    parts.append(
        rigor.draw_y_axis(
            band_x_left,
            plot_y_top,
            plot_y_bot,
            e_ticks,
            e_min,
            e_max,
            unit=energy_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=tr("Energy ({unit})", unit=energy_unit) if energy_unit else tr("Energy"),
            side="left",
        )
    )

    ink = pal["ink"]
    ink6 = pal["ink6"]
    parts.append(
        f'<line x1="{band_x_left:.1f}" y1="{plot_y_bot:.1f}" '
        f'x2="{band_x_right:.1f}" y2="{plot_y_bot:.1f}" '
        f'stroke="{ink}" stroke-width="1.2" data-role="x-axis"/>'
    )
    tick_fs = max(13.0, fs["ytick"])
    for k_coord, label in high_symmetry_points:
        if k_coord < k_min - 1e-9 or k_coord > k_max + 1e-9:
            continue
        xk = X(k_coord)
        parts.append(
            f'<line x1="{xk:.1f}" y1="{plot_y_bot:.1f}" x2="{xk:.1f}" y2="{plot_y_bot + 5:.1f}" '
            f'stroke="{ink}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{xk:.1f}" y="{plot_y_bot + tick_fs + 10:.1f}" '
            f'font-size="{tick_fs}" text-anchor="middle" fill="{ink}" '
            f'font-weight="700">{_xesc(label)}</text>'
        )

    axis_title_fs = max(13.0, fs["yaxis"])
    parts.append(
        f'<text x="{(band_x_left + band_x_right) * 0.5:.1f}" '
        f'y="{plot_y_bot + tick_fs + axis_title_fs + 24:.1f}" '
        f'font-size="{axis_title_fs}" fill="{ink}" text-anchor="middle" '
        f'font-weight="600">{_xesc(tr("Wave vector k"))}</text>'
    )

    if use_dos_panel:
        # Filter DOS points to the shared energy domain.
        dos_in = [(ev, dv) for (ev, dv) in dos_curve if e_min - 1e-9 <= ev <= e_max + 1e-9]
        if dos_in:
            dos_min = min(dv for _, dv in dos_in)
            dos_max = max(dv for _, dv in dos_in)
            if dos_max == dos_min:
                dos_max = dos_min + 1.0
            # Give the baseline a visible offset from the panel edge.
            dos_min = min(0.0, dos_min)

            # DOS panel uses a secondary (fs × 0.88) font size budget.
            dos_fs_tick = tick_fs * 0.88
            dos_fs_title = axis_title_fs * 0.88

            def DX(v):
                return rigor._lin(v, dos_min, dos_max, dos_x_left, dos_x_right)

            # Panel border (axes box) — share Y with main panel implicitly.
            parts.append(
                f'<rect x="{dos_x_left:.1f}" y="{plot_y_top:.1f}" '
                f'width="{dos_x_right - dos_x_left:.1f}" '
                f'height="{plot_y_bot - plot_y_top:.1f}" fill="none" '
                f'stroke="{ink}" stroke-width="1.2"/>'
            )

            dos_fill = _rgba_with_alpha(pal["accent"], 0.22)
            x_base = DX(dos_min)
            poly = [f"{x_base:.1f},{Y(dos_in[0][0]):.1f}"]
            for ev, dv in dos_in:
                poly.append(f"{DX(dv):.1f},{Y(ev):.1f}")
            poly.append(f"{x_base:.1f},{Y(dos_in[-1][0]):.1f}")
            parts.append(f'<polygon points="{" ".join(poly)}" fill="{dos_fill}" stroke="none"/>')

            d = " ".join(f"{'M' if i == 0 else 'L'} {DX(dv):.1f} {Y(ev):.1f}" for i, (ev, dv) in enumerate(dos_in))
            parts.append(
                f'<path d="{d}" fill="none" stroke="{pal["accent"]}" stroke-width="2.0" stroke-linejoin="round"/>'
            )

            # DOS X-axis baseline (horizontal, at panel bottom).
            parts.append(
                f'<line x1="{dos_x_left:.1f}" y1="{plot_y_bot:.1f}" '
                f'x2="{dos_x_right:.1f}" y2="{plot_y_bot:.1f}" '
                f'stroke="{ink}" stroke-width="1.2"/>'
            )
            # A couple of X ticks on the DOS panel (0 and max).
            for dv in (dos_min, dos_max):
                xt = DX(dv)
                parts.append(
                    f'<line x1="{xt:.1f}" y1="{plot_y_bot:.1f}" '
                    f'x2="{xt:.1f}" y2="{plot_y_bot + 5:.1f}" '
                    f'stroke="{ink}" stroke-width="1"/>'
                )
                parts.append(
                    f'<text x="{xt:.1f}" y="{plot_y_bot + dos_fs_tick + 10:.1f}" '
                    f'font-size="{dos_fs_tick:.1f}" text-anchor="middle" '
                    f'fill="{ink}">{dv:.1f}</text>'
                )
            parts.append(
                f'<text x="{(dos_x_left + dos_x_right) * 0.5:.1f}" '
                f'y="{plot_y_bot + dos_fs_tick + dos_fs_title + 24:.1f}" '
                f'font-size="{dos_fs_title:.1f}" fill="{ink}" '
                f'text-anchor="middle" font-weight="600">DOS g(E)</text>'
            )
            # Panel header (small label at top of DOS panel).
            parts.append(
                f'<text x="{(dos_x_left + dos_x_right) * 0.5:.1f}" '
                f'y="{plot_y_top - 6:.1f}" font-size="{dos_fs_tick:.1f}" '
                f'fill="{ink6}" text-anchor="middle" '
                f'font-style="italic">{_xesc(tr("Density of States"))}</text>'
            )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 32))

    return rigor.wrap_svg(parts, W, H, body_font)
