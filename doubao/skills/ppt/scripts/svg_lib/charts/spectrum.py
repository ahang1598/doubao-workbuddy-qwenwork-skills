"""Academic chart: 1-D spectrum — lab spectra (mass spec / NMR / IR / UV-Vis /
Raman) and observational spectra (transit / emission / absorption spectra).
"""

from __future__ import annotations

from .._common import (
    _dist_font_sizes,
    _estimate_label_width_px,
    _rgb_prefix,
    _resolve_font,
    _resolve_palette,
    _variant_is_classic,
    _xesc,
    auto_layout_labels,
)
from . import _academic_rigor as rigor
from ._chart_layout import axis_caption
from ._shared import ZH_CHROME, tr

for _key, _text in {"Data": "观测", "Model": "模型", "Spectrum": "谱线"}.items():
    ZH_CHROME.setdefault(_key, _text)


# Multi-mode whitelist (mode → (template, trigger, validator))
#   with_derivative : derivative sub-plot below main, shared X axis
#                     (classic NMR/IR/Raman presentation — surfaces fine
#                     structure obscured in the integrated spectrum).
def _validate_derivative(signals):
    xs = signals.get("xs") or []
    ys = signals.get("ys") or []
    if len(xs) < 10 or len(xs) != len(ys):
        return (False, "need matching xs/ys with len>=10")
    y_hi = max(ys)
    y_lo = min(ys)
    if y_hi - y_lo <= 1e-9 * (abs(y_hi) + 1.0):
        return (False, "flat spectrum (no variation to differentiate)")
    return (True, "")


_SPECTRUM_MULTI_WHITELIST = {
    "with_derivative": (
        "top_bottom_3to1",
        # Trigger: enough samples to compute a stable derivative AND some dynamic range.
        lambda s: len(s.get("xs") or []) >= 10 and s.get("has_variation", False),
        lambda s: _validate_derivative(s),
    ),
}


# Peak normalization (support dict + tuple format)
def _normalize_peak(p):
    """Normalize a peak to ``{"x", "label", "intensity"}`` dict."""
    if isinstance(p, dict):
        return {"x": p["x"], "label": p.get("label", ""), "intensity": p.get("intensity"), "width": p.get("width")}
    if isinstance(p, (tuple, list)):
        if len(p) == 1:
            return {"x": p[0], "label": "", "intensity": None, "width": None}
        if len(p) == 2:
            return {"x": p[0], "label": p[1], "intensity": None, "width": None}
        if len(p) >= 3:
            return {"x": p[0], "label": p[1], "intensity": p[2], "width": None}
    raise ValueError(f"peak must be dict or tuple/list, got {type(p).__name__}")


def _detect_peaks(x, y, top_k=5, min_dist_frac=0.02):
    """Simple local-maximum peak detector."""
    n = len(y)
    if n < 3:
        return []
    cands = []
    for i in range(1, n - 1):
        if y[i] > y[i - 1] and y[i] > y[i + 1]:
            cands.append((x[i], y[i]))
    cands.sort(key=lambda t: -t[1])
    x_range = max(x) - min(x) if x else 1.0
    min_dist = x_range * min_dist_frac
    picked = []
    for cx, cy in cands:
        if all(abs(cx - px) >= min_dist for px, _ in picked):
            picked.append((cx, cy))
            if len(picked) >= top_k:
                break
    return picked


# Observational spectra: binned points, model bands, absorption bands
def _num(value, name):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"spectrum {name} must be a number, got {value!r}") from None
    if out != out or out in (float("inf"), float("-inf")):
        raise ValueError(f"spectrum {name} must be finite")
    return out


def _err_pair(err, name):
    """``y_err`` as (below, above): a scalar is symmetric, a pair is (minus, plus)."""
    if err is None:
        return None
    if isinstance(err, (tuple, list)):
        if len(err) != 2:
            raise ValueError(f"spectrum {name} must be a number or a (minus, plus) pair")
        lo, hi = _num(err[0], name), _num(err[1], name)
    else:
        lo = hi = _num(err, name)
    if lo < 0 or hi < 0:
        raise ValueError(f"spectrum {name} must be non-negative")
    return lo, hi


def _normalize_points(points, x=None, y=None, y_err=None):
    """Binned observations as ``[{x, y, lo, hi, x_lo, x_hi}]`` (lo/hi = y − err / y + err)."""
    out = []
    if points is not None:
        for i, p in enumerate(points):
            if isinstance(p, (tuple, list)):
                p = dict(zip(("x", "y", "y_err"), p))
            if not isinstance(p, dict) or "x" not in p or "y" not in p:
                raise ValueError(f"spectrum points[{i}] needs x and y")
            px, py = _num(p["x"], "points.x"), _num(p["y"], "points.y")
            if p.get("y_lo") is not None or p.get("y_hi") is not None:
                lo, hi = _num(p.get("y_lo", py), "y_lo"), _num(p.get("y_hi", py), "y_hi")
            else:
                err = _err_pair(p.get("y_err", p.get("err")), "y_err")
                lo, hi = (py - err[0], py + err[1]) if err else (py, py)
            xe = _err_pair(p.get("x_err"), "x_err")
            out.append(
                {
                    "x": px,
                    "y": py,
                    "lo": min(lo, py),
                    "hi": max(hi, py),
                    "x_lo": px - xe[0] if xe else px,
                    "x_hi": px + xe[1] if xe else px,
                }
            )
        return out
    errs = y_err if isinstance(y_err, (list, tuple)) and len(y_err) == len(x) else [y_err] * len(x)
    for px, py, err in zip(x, y, errs):
        px, py = _num(px, "x"), _num(py, "y")
        e = _err_pair(err, "y_err")
        out.append(
            {"x": px, "y": py, "lo": py - e[0] if e else py, "hi": py + e[1] if e else py, "x_lo": px, "x_hi": px}
        )
    return out


def _normalize_models(models):
    out = []
    for i, m in enumerate(models or []):
        if not isinstance(m, dict) or not m.get("x") or not m.get("y") or len(m["x"]) != len(m["y"]):
            raise ValueError(f"spectrum models[{i}] needs matching x and y lists")
        mx = [_num(v, "models.x") for v in m["x"]]
        my = [_num(v, "models.y") for v in m["y"]]
        lo = hi = None
        if m.get("lo") is not None or m.get("hi") is not None:
            if m.get("lo") is None or m.get("hi") is None or not len(m["lo"]) == len(m["hi"]) == len(mx):
                raise ValueError(f"spectrum models[{i}] lo and hi must both match x in length")
            lo = [_num(v, "models.lo") for v in m["lo"]]
            hi = [_num(v, "models.hi") for v in m["hi"]]
        order = sorted(range(len(mx)), key=mx.__getitem__)
        pick = lambda seq: None if seq is None else [seq[k] for k in order]
        out.append(
            {
                "name": str(m.get("name") or ""),
                "x": pick(mx),
                "y": pick(my),
                "lo": pick(lo),
                "hi": pick(hi),
                "color": m.get("color"),
            }
        )
    return out


def _normalize_bands(bands):
    out = []
    for i, b in enumerate(bands or []):
        if isinstance(b, (tuple, list)):
            b = dict(zip(("start", "end", "label"), b))
        if not isinstance(b, dict) or b.get("start") is None or b.get("end") is None:
            raise ValueError(f"spectrum bands[{i}] needs start and end")
        a, z = sorted((_num(b["start"], "bands.start"), _num(b["end"], "bands.end")))
        out.append({"start": a, "end": z, "label": str(b.get("label") or ""), "color": b.get("color")})
    return out


# Light, distinguishable tints for molecule bands (journal style: pale fills, coloured labels).
_BAND_COLORS = (
    "rgba(70,120,180,1)",
    "rgba(200,120,40,1)",
    "rgba(80,150,90,1)",
    "rgba(150,90,160,1)",
    "rgba(180,70,70,1)",
    "rgba(110,110,110,1)",
)
_MODEL_COLORS = ("rgba(214,96,46,1)", "rgba(46,110,180,1)", "rgba(60,140,90,1)", "rgba(140,80,160,1)")


def _path(points, X, Y):
    return " ".join(f"{'M' if i == 0 else 'L'} {X(a):.2f} {Y(b):.2f}" for i, (a, b) in enumerate(points))


def make_spectrum(
    x=None,
    y=None,
    *,
    y_err=None,
    points=None,
    models=None,
    bands=None,
    peak_style: str = "stick",
    data_label: str | None = None,
    peaks=None,
    x_unit: str = "",
    y_unit: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    baseline_value: float = 0.0,
    show_baseline: bool | None = None,
    x_reversed: bool = False,
    auto_detect_peaks: bool = False,
    top_k_peaks: int = 5,
    show_stats: bool = False,
    multi_mode: str = "auto",
    width: float = 1400,
    height: float = 700,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
) -> str:
    """1-D spectrum: a lab trace with peaks, or an observational spectrum with error bars and models.

    Lab spectrum: ``x``/``y`` trace; ``peaks`` mark features as sticks
    (``peak_style="stick"``) or light shaded spans (``peak_style="band"``,
    width from the peak's ``width`` or 2% of the x range).

    Observational (transit / emission / absorption) spectrum — real binned data only:
      - ``points=[{"x": 4.30, "y": 2.21, "y_err": 0.012}]`` (``y_err`` may be a
        ``(minus, plus)`` pair; ``y_lo``/``y_hi`` and bin half-width ``x_err``
        also work), or ``x, y, y_err=`` (scalar or per-point list): grey error bars.
      - ``models=[{"name": "Best fit", "x": [...], "y": [...], "lo": [...], "hi": [...]}]``:
        coloured model line with its shaded 1σ band.
      - ``bands=[{"start": 4.2, "end": 4.4, "label": "CO₂"}]``: pale vertical spans
        for molecular absorption bands / spectral windows, labelled at the top.
      With ``points``, ``x``/``y`` (if also given) are drawn as a plain trace.
      The baseline is hidden by default for observational spectra.

    ``peaks`` accepts either format:
      - dict: ``{"x": 50.0, "label": "A", "intensity": 1.0}`` (intensity optional)
      - tuple/list: ``(x,)`` / ``(x, label)`` / ``(x, label, intensity)``

    ``show_stats=True`` opts in to a bookkeeping box (point count, x range);
    it is off by default because the axis already shows the x range and the
    sampling count carries no spectroscopic information on a slide.
    """
    _variant_is_classic("spectrum", variant)
    custom_palette = isinstance(palette, dict) and bool(palette.get("series"))
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)

    if peak_style not in ("stick", "band"):
        raise ValueError("peak_style must be 'stick' or 'band'")
    has_xy = bool(x) and bool(y) and len(x) == len(y)
    if x is not None and y is not None and len(x) != len(y):
        raise ValueError(f"spectrum x and y must have the same length ({len(x)} vs {len(y)})")
    if y_err is not None and points is None and not has_xy:
        raise ValueError("spectrum y_err needs x and y (or use points=[{x, y, y_err}])")
    obs = (
        _normalize_points(points)
        if points is not None
        else (_normalize_points(None, x, y, y_err) if y_err is not None and has_xy else [])
    )
    model_list = _normalize_models(models)
    band_list = _normalize_bands(bands)
    has_trace = has_xy and not (y_err is not None and points is None)
    observational = bool(obs or model_list)
    if show_baseline is None:
        show_baseline = not observational

    if not has_trace and not obs and not model_list:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
            f'<text x="{W / 2}" y="{H / 2}" text-anchor="middle" font-size="16" '
            f'fill="{pal["ink6"]}">{_xesc(tr("No spectrum data"))}</text></svg>'
        )

    xs = [float(v) for v in x] if has_trace else []
    ys = [float(v) for v in y] if has_trace else []
    n = len(xs)
    fs = _dist_font_sizes(W, H, 8)

    all_x = xs + [v for p in obs for v in (p["x_lo"], p["x_hi"])] + [v for m in model_list for v in m["x"]]
    all_y = (
        ys
        + [v for p in obs for v in (p["lo"], p["hi"])]
        + [v for m in model_list for v in (m["y"] + (m["lo"] or []) + (m["hi"] or []))]
    )
    stats_fmt = [("n", str(n or len(obs))), (tr("x min"), f"{min(all_x):.4g}"), (tr("x max"), f"{max(all_x):.4g}")]
    stats_w = 0.0
    if show_stats:
        _, stats_bounds = rigor.draw_stats_box(0, 0, stats_fmt, pal=pal, fs=fs["label"], font_family=body_font)
        stats_w = stats_bounds[2] - stats_bounds[0] + 42

    # layout — short slide boxes size margins from the text actually present so the plot stays usable
    margin_top = margin_bot = margin_left = 110
    if H < 600:
        heads = [
            f
            for v, f in ((title, fs["title"] + 8), (subtitle, fs["subtitle"] + 6), (figure_label, fs["figure"] + 4))
            if v
        ]
        margin_top = 26 + sum(heads) + fs["label"] * 1.6  # room for peak labels above the tallest peak
        margin_bot = fs["xtick"] + 22 + fs["xaxis"] * 1.5 + (fs["foot"] + 14 if note or source else 0)
        margin_left = 48 + fs["yaxis"] + fs["ytick"] * 2.6
    margin_right = max(60, stats_w)
    legend_entries = []
    if observational:
        if obs:
            legend_entries.append(("data", data_label or tr("Data"), None))
        named = pal.get("series_colors") or {}
        # A caller palette colours the models (by name, else in order); the built-in tints are only the default.
        model_colors = (
            _MODEL_COLORS
            if not custom_palette
            else [c for c in pal.get("series") or [] if c not in named.values()] or _MODEL_COLORS
        )
        for k, m in enumerate(model_list):
            color = m["color"] or named.get(m["name"]) or model_colors[k % len(model_colors)]
            m["color"] = color
            legend_entries.append(("model", m["name"] or tr("Model"), color))
        if has_trace:
            legend_entries.insert(0, ("trace", tr("Spectrum"), None))
    legend_fs = max(13.0, fs["legend"])
    legend_h = legend_fs * 1.9 if len(legend_entries) >= 2 else 0.0
    if observational and H < 600:
        # band / peak labels sit inside the plot top, so only the title block and legend need room above it
        heads = [
            f
            for v, f in ((title, fs["title"] + 8), (subtitle, fs["subtitle"] + 6), (figure_label, fs["figure"] + 4))
            if v
        ]
        margin_top = 18 + sum(heads) + (0 if legend_h else 8)
    margin_top += legend_h

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    # split the plot vertically so the derivative panel shares the X axis.
    y_hi_tmp = max(ys) if ys else 0.0
    y_lo_tmp = min(ys) if ys else 0.0
    _has_variation = (y_hi_tmp - y_lo_tmp) > 1e-9 * (abs(y_hi_tmp) + 1.0)
    if (observational or not has_trace) and multi_mode == "auto":
        multi_mode = "single"  # derivative panels only make sense for a sampled lab trace
    _plot_bbox = rigor.bbox_from_edges(plot_x_left, plot_x_right, plot_y_top, plot_y_bot)
    _mm_signals = {"xs": xs, "ys": ys, "has_variation": _has_variation}
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _SPECTRUM_MULTI_WHITELIST,
        _mm_signals,
        _plot_bbox,
    )

    if _mm_mode == "with_derivative":
        _rects = rigor.allocate_subplot_rects(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            plot_y_bot,
            _mm_template,
        )
        main_x_left, main_x_right, main_y_top, main_y_bot = _rects["main"]
        _sub_x_left, _sub_x_right, sub_y_top, sub_y_bot = _rects["sub"]
    else:
        main_x_left, main_x_right = plot_x_left, plot_x_right
        main_y_top, main_y_bot = plot_y_top, plot_y_bot
        sub_y_top = sub_y_bot = None

    x_min_data = min(all_x)
    x_max_data = max(all_x)
    label_fs = max(13.0, fs["label"])
    if observational:
        # Observational spectra hug the data (a transit depth of 2.1–2.3% must not start at 0);
        # the top keeps one label row for molecule bands / peak names.
        y_min_data = min(all_y + ([baseline_value] if show_baseline else []))
        y_max_data = max(all_y)
        span = (y_max_data - y_min_data) or abs(y_max_data) or 1.0
        top_frac = min(0.4, (label_fs * 2.2) / max(1.0, main_y_bot - main_y_top)) if (band_list or peaks) else 0.04
        y_ticks, y_min, y_max = rigor.nice_axis(
            y_min_data - span * 0.04, y_max_data + span * (0.04 + top_frac / (1 - top_frac)), 6
        )
        x_pad = (x_max_data - x_min_data) * 0.02
        x_ticks, x_min, x_max = rigor.nice_axis(x_min_data - x_pad, x_max_data + x_pad, 8)
        x_min = max(x_min, x_min_data - x_pad * 2.5) if x_ticks else x_min
        x_max = min(x_max, x_max_data + x_pad * 2.5) if x_ticks else x_max
        x_ticks = [t for t in x_ticks if x_min - 1e-9 <= t <= x_max + 1e-9]
    else:
        y_min_data = min(ys + [baseline_value])
        y_max_data = max(ys)
        x_ticks, x_min, x_max = rigor.nice_axis(x_min_data, x_max_data, 8)
        # pad y_max to leave room for peak labels (~15%)
        y_pad = (y_max_data - y_min_data) * 0.18
        # Intensity starts at 0: baseline noise a few % below zero must not open a negative tick (−20, −200).
        noise_floor = y_min_data < 0 <= baseline_value and -y_min_data <= 0.05 * max(y_max_data, 0)
        y_ticks, y_min, y_max = rigor.nice_axis(0.0 if noise_floor else y_min_data, y_max_data + y_pad, 6)
        if noise_floor:
            y_min = y_min_data

    def X(v):
        if x_reversed:
            return rigor._lin(v, x_min, x_max, main_x_right, main_x_left)
        return rigor._lin(v, x_min, x_max, main_x_left, main_x_right)

    def Y(v):
        return rigor._lin(v, y_min, y_max, main_y_bot, main_y_top)

    resolved_peaks = []
    if peaks:
        normalized = [_normalize_peak(p) for p in peaks]
        for p in normalized:
            px = float(p["x"])
            py = p.get("intensity")
            if py is None:
                # nearest sample of the trace, else of the data points / first model
                ref = (
                    list(zip(xs, ys))
                    or [(q["x"], q["y"]) for q in obs]
                    or list(zip(model_list[0]["x"], model_list[0]["y"]))
                )
                py = min(ref, key=lambda t: abs(t[0] - px))[1]
            py = float(py)
            lab = p.get("label", "")
            resolved_peaks.append((px, py, lab, p.get("width")))
    elif auto_detect_peaks and has_trace:
        auto = _detect_peaks(xs, ys, top_k=top_k_peaks)
        for px, py in auto:
            resolved_peaks.append((px, py, f"{px:.3g}", None))

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

    # Insert measured grid segments behind data after peak-label positions are known.
    grid_index = len(parts)
    parts.append("")

    ink = pal["ink"]
    ink6 = pal["ink6"]
    ink4 = pal["ink4"]
    accent = pal["accent"]

    if show_baseline:
        by = Y(baseline_value)
        parts.append(
            rigor.draw_reference_line(
                by,
                main_x_left,
                main_x_right,
                pal=pal,
                orient="horizontal",
                dash="4 4",
                color=ink4,
                label=None,
            )
        )

    label_items = []  # (lx, ly, text, anchor, fs, axis)
    label_colors = []
    band_fs = max(13.0, fs["label"] * 0.95)

    def _span(a, b):
        xa, xb = sorted((X(max(a, x_min)), X(min(b, x_max))))
        return xa, max(xb - xa, 1.2)

    # molecule absorption bands / spectral windows: pale spans behind everything, label at the top
    for k, band in enumerate(band_list):
        if band["end"] < x_min or band["start"] > x_max:
            continue
        color = band["color"] or _BAND_COLORS[k % len(_BAND_COLORS)]
        bx, bw = _span(band["start"], band["end"])
        parts.append(
            f'<rect x="{bx:.2f}" y="{main_y_top:.2f}" width="{bw:.2f}" height="{main_y_bot - main_y_top:.2f}" '
            f'fill="{_rgb_prefix(color)}0.13)" stroke="none" data-role="absorption-band"/>'
        )
        if band["label"]:
            label_items.append((bx + bw / 2, main_y_top + band_fs * 1.15, band["label"], "middle", band_fs, "x"))
            label_colors.append(color)

    # peak bands (peak_style="band"): light spans centred on each peak
    if peak_style == "band":
        default_w = (x_max - x_min) * 0.02
        for px, py, lab, pw in resolved_peaks:
            half = (float(pw) if pw else default_w) / 2
            bx, bw = _span(px - half, px + half)
            parts.append(
                f'<rect x="{bx:.2f}" y="{main_y_top:.2f}" width="{bw:.2f}" '
                f'height="{main_y_bot - main_y_top:.2f}" fill="{_rgb_prefix(accent)}0.12)" stroke="none" '
                f'data-role="peak-band"/>'
            )

    # model curves: shaded 1σ band under a coloured line
    for m in model_list:
        if m["lo"] is not None:
            upper = list(zip(m["x"], m["hi"]))
            lower = list(zip(m["x"], m["lo"]))[::-1]
            d = _path(upper + lower, X, Y) + " Z"
            parts.append(f'<path d="{d}" fill="{_rgb_prefix(m["color"])}0.22)" stroke="none" data-role="model-band"/>')
    if has_trace:
        parts.append(
            f'<path d="{_path(zip(xs, ys), X, Y)}" fill="none" stroke="{ink}" '
            f'stroke-width="{1.2 if observational else 1.4}"/>'
        )
    for m in model_list:
        parts.append(
            f'<path d="{_path(zip(m["x"], m["y"]), X, Y)}" fill="none" stroke="{m["color"]}" '
            f'stroke-width="2.2" stroke-linejoin="round" data-role="model"/>'
        )

    # binned observations: grey error bars with small caps + dark filled points
    err_color = "rgba(110,110,110,1)"
    cap = max(2.5, min(5.0, (main_x_right - main_x_left) / max(1, len(obs)) * 0.25))
    r = max(2.6, min(4.2, (main_x_right - main_x_left) / max(1, len(obs)) * 0.18))
    for q in obs:
        cx, cy = X(q["x"]), Y(q["y"])
        if q["hi"] > q["lo"]:
            y0, y1 = Y(q["lo"]), Y(q["hi"])
            parts.append(
                f'<line x1="{cx:.2f}" y1="{y0:.2f}" x2="{cx:.2f}" y2="{y1:.2f}" stroke="{err_color}" '
                f'stroke-width="1.1" data-role="error-bar"/>'
            )
            for yy in (y0, y1):
                parts.append(
                    f'<line x1="{cx - cap:.2f}" y1="{yy:.2f}" x2="{cx + cap:.2f}" y2="{yy:.2f}" '
                    f'stroke="{err_color}" stroke-width="1.1"/>'
                )
        if q["x_hi"] > q["x_lo"]:
            parts.append(
                f'<line x1="{X(q["x_lo"]):.2f}" y1="{cy:.2f}" x2="{X(q["x_hi"]):.2f}" y2="{cy:.2f}" '
                f'stroke="{err_color}" stroke-width="1.1"/>'
            )
    for q in obs:
        parts.append(
            f'<circle cx="{X(q["x"]):.2f}" cy="{Y(q["y"]):.2f}" r="{r:.2f}" fill="rgba(40,40,40,1)" '
            f'stroke="rgba(255,255,255,1)" stroke-width="0.6" data-role="point"/>'
        )
    # Minimum headroom above the baseline so satellite peaks (low intensity)
    # don't get their label stuck ON the baseline — reserve ``fs * 2`` px.
    min_label_y = Y(baseline_value) - label_fs * 2.0
    for px, py, lab, _pw in resolved_peaks:
        sx = X(px)
        sy_peak = Y(py)
        sy_base = Y(baseline_value)
        if peak_style == "stick":
            parts.append(
                f'<line x1="{sx:.1f}" y1="{sy_base:.1f}" x2="{sx:.1f}" y2="{sy_peak:.1f}" '
                f'stroke="{accent}" stroke-width="1.6"/>'
            )
            parts.append(
                f'<circle cx="{sx:.1f}" cy="{sy_peak:.1f}" r="3.0" fill="{accent}" stroke="{ink}" stroke-width="0.9"/>'
            )
        # label candidate (above peak). Pick anchor + x position based on
        # proximity to the right/left plot edge so the label stays inside the
        # viewBox. On small spectra fs grows large, which pushed labels
        # anchored "middle" past the right edge for peaks sitting close to
        # x_max.
        text = lab if lab else f"{px:.3g}"
        est_w = _estimate_label_width_px(text, label_fs, bold=True, font_family=body_font)
        margin = 6
        # Lift label at least ``fs * 2`` above baseline so satellite peaks
        # (short sticks) don't paint their label on the dashed baseline.
        raw_label_y = sy_peak - 10
        label_y = (
            main_y_top + label_fs * 1.15 if peak_style == "band" or observational else min(raw_label_y, min_label_y)
        )
        if sx + est_w * 0.5 + margin > main_x_right:
            # label would overflow right → anchor at end, place just inside
            label_items.append((main_x_right - margin, label_y, text, "end", label_fs, "x"))
        elif sx - est_w * 0.5 - margin < main_x_left:
            label_items.append((main_x_left + margin, label_y, text, "start", label_fs, "x"))
        else:
            label_items.append((sx, label_y, text, "middle", label_fs, "x"))
        label_colors.append(ink)

    peak_cutouts = []
    # layout peak labels to avoid overlap (allow x-direction only)
    if label_items:
        # Keep labels inside the plot, then nudge apart; labels sharing the top row that still collide drop a row.
        clamped = []
        for lx, ly, text, anchor, lfs, ax in label_items:
            tw = _estimate_label_width_px(text, lfs, font_family=body_font)
            if anchor == "middle":
                lx = min(max(lx, main_x_left + tw / 2 + 4), main_x_right - tw / 2 - 4)
            clamped.append((lx, ly, text, anchor, lfs, ax))
        label_items = clamped
        positions = auto_layout_labels(label_items, min_gap=4.0, iterations=30)
        placed = []
        for idx, ((lx, ly), item) in enumerate(zip(positions, label_items)):
            text = item[2]
            anchor = item[3]
            lfs = item[4]
            text_w = _estimate_label_width_px(text, lfs, font_family=body_font)
            text_left = lx - (text_w if anchor == "end" else text_w / 2 if anchor == "middle" else 0)
            text_left = min(max(text_left, main_x_left + 2), main_x_right - text_w - 2)
            lx = text_left + (text_w if anchor == "end" else text_w / 2 if anchor == "middle" else 0)
            box = [text_left - 3, ly - lfs * 0.85, text_left + text_w + 3, ly + lfs * 0.3]
            while any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in placed):
                ly += lfs * 1.25
                box[1] += lfs * 1.25
                box[3] += lfs * 1.25
            placed.append(box)
            label_fs_i, color_i = lfs, label_colors[idx] if idx < len(label_colors) else ink
            peak_cutouts.append((text_left - 7, ly - lfs * 0.85 - 3, text_left + text_w + 7, ly + lfs * 0.3 + 3))
            # Draw with halo so the label stays legible when the trace or the
            # baseline sits near it.
            parts.append(
                rigor.draw_label_with_halo(
                    lx,
                    ly,
                    text,
                    pal,
                    fs=label_fs_i,
                    anchor=anchor,
                    color=color_i,
                    halo_alpha=0.85,
                )
            )

    parts[grid_index] = rigor.draw_grid(
        main_x_left,
        main_x_right,
        main_y_top,
        main_y_bot,
        pal=pal,
        y_ticks=y_ticks,
        y_min=y_min,
        y_max=y_max,
        orient="horizontal",
        cutout_bboxes=peak_cutouts,
    )

    # X axis — if x_reversed, we need to invert tick positions. When the derivative panel is active, the X labels/title
    # live beneath the sub panel (shared axis), not under the main panel.
    _x_axis_y = sub_y_bot if _mm_mode == "with_derivative" else main_y_bot
    # One caption per axis: "Wavelength (μm)" — never a second, isolated unit line.
    x_title = axis_caption(x_title, x_unit, title) or None
    y_title = axis_caption(y_title, y_unit, title) or None
    x_unit = y_unit = ""
    if x_reversed:
        # draw manually: axis + ticks placed via X()
        parts.append(
            f'<line x1="{main_x_left:.1f}" y1="{_x_axis_y:.1f}" '
            f'x2="{main_x_right:.1f}" y2="{_x_axis_y:.1f}" stroke="{ink}" stroke-width="1.2"/>'
        )
        x_span = x_max - x_min
        _x_labels = rigor._tick_label_map(x_ticks, x_span)
        for v in x_ticks:
            if v < x_min - 1e-9 or v > x_max + 1e-9:
                continue
            xp = X(v)
            parts.append(
                f'<line x1="{xp:.1f}" y1="{_x_axis_y:.1f}" x2="{xp:.1f}" y2="{_x_axis_y + 5:.1f}" '
                f'stroke="{ink}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{xp:.1f}" y="{_x_axis_y + fs["ytick"] + 8:.1f}" '
                f'font-size="{fs["ytick"]}" text-anchor="middle" fill="{ink}">'
                f"{_xesc(_x_labels[v])}</text>"
            )
        if x_title:
            fs_t = max(13.0, fs["yaxis"])
            parts.append(
                f'<text x="{(main_x_left + main_x_right) / 2:.1f}" '
                f'y="{_x_axis_y + fs["ytick"] + fs_t + 18:.1f}" '
                f'font-size="{fs_t}" fill="{ink}" text-anchor="middle" font-weight="600">'
                f"{_xesc(x_title)}</text>"
            )
        if x_unit and not rigor._title_has_unit(x_title, x_unit):
            parts.append(
                f'<text x="{main_x_left:.1f}" y="{_x_axis_y + fs["ytick"] * 2.3 + 8:.1f}" '
                f'font-size="{max(13.0, fs["ytick"] * 0.95):.1f}" fill="{ink6}" '
                f'text-anchor="start" font-style="italic">{_xesc(x_unit)}</text>'
            )
        arrow_y = _x_axis_y + fs["ytick"] * 2.3 + 8
        parts.append(
            f'<text x="{main_x_right - 8:.1f}" y="{arrow_y:.1f}" '
            f'font-size="{max(13.0, fs["ytick"] * 0.95):.1f}" fill="{ink6}" '
            f'text-anchor="end" font-style="italic">← low</text>'
        )
    else:
        parts.append(
            rigor.draw_x_axis(
                main_x_left,
                main_x_right,
                _x_axis_y,
                x_ticks,
                x_min,
                x_max,
                unit="",
                pal=pal,
                fs_tick=fs["ytick"],
                fs_title=fs["yaxis"],
                title=x_title,
            )
        )

    parts.append(
        rigor.draw_y_axis(
            main_x_left,
            main_y_top,
            main_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit="",
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title,
            side="left",
        )
    )

    # legend (only when there is more than one kind of mark): one row above the plot, right-aligned
    if legend_h:
        items = []
        for kind, name, color in legend_entries:
            items.append((kind, name, color, _estimate_label_width_px(name, legend_fs, font_family=body_font)))
        total = sum(28 + w + 22 for *_, w in items) - 22
        lx = max(main_x_left, main_x_right - total)
        ly = main_y_top - legend_fs * 0.75
        for kind, name, color, w in items:
            if kind == "data":
                parts.append(
                    f'<line x1="{lx + 10:.1f}" y1="{ly - legend_fs * 0.55:.1f}" x2="{lx + 10:.1f}" '
                    f'y2="{ly + legend_fs * 0.55:.1f}" stroke="rgba(110,110,110,1)" stroke-width="1.1"/>'
                )
                parts.append(f'<circle cx="{lx + 10:.1f}" cy="{ly:.1f}" r="3.4" fill="rgba(40,40,40,1)"/>')
            elif kind == "model":
                parts.append(
                    f'<rect x="{lx:.1f}" y="{ly - legend_fs * 0.32:.1f}" width="22" height="{legend_fs * 0.64:.1f}" '
                    f'fill="{_rgb_prefix(color)}0.22)"/>'
                )
                parts.append(
                    f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{lx + 22:.1f}" y2="{ly:.1f}" stroke="{color}" '
                    f'stroke-width="2.2"/>'
                )
            else:
                parts.append(
                    f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{lx + 22:.1f}" y2="{ly:.1f}" stroke="{ink}" '
                    f'stroke-width="1.4"/>'
                )
            parts.append(
                f'<text x="{lx + 28:.1f}" y="{ly + legend_fs * 0.35:.1f}" font-size="{legend_fs:.1f}" '
                f'fill="{ink}" data-role="legend-label">{_xesc(name)}</text>'
            )
            lx += 28 + w + 22

    # stats box: n + x range (opt-in bookkeeping only)
    if show_stats:
        sb_svg, _ = rigor.draw_stats_box(
            W - 28,
            main_y_top + 6,
            stats_fmt,
            pal=pal,
            fs=fs["label"],
            anchor="end",
            font_family=body_font,
        )
        parts.append(sb_svg)

    if _mm_mode == "with_derivative" and n >= 3:
        # Compute 1st derivative via central differences; endpoints use fwd/bwd.
        _dy = [0.0] * n
        for _i in range(n):
            if _i == 0:
                _dx = xs[1] - xs[0]
                _dy[_i] = (ys[1] - ys[0]) / _dx if _dx != 0 else 0.0
            elif _i == n - 1:
                _dx = xs[-1] - xs[-2]
                _dy[_i] = (ys[-1] - ys[-2]) / _dx if _dx != 0 else 0.0
            else:
                _dx = xs[_i + 1] - xs[_i - 1]
                _dy[_i] = (ys[_i + 1] - ys[_i - 1]) / _dx if _dx != 0 else 0.0
        _d_lo = min(_dy)
        _d_hi = max(_dy)
        if _d_hi <= _d_lo:
            _d_hi = _d_lo + 1.0
        _d_pad = (_d_hi - _d_lo) * 0.08
        _d_lo -= _d_pad
        _d_hi += _d_pad
        _d_ticks, _d_min, _d_max = rigor.nice_axis(_d_lo, _d_hi, 3)

        def _SY(v):
            return rigor._lin(v, _d_min, _d_max, sub_y_bot, sub_y_top)

        parts.append(
            rigor.draw_grid(
                main_x_left,
                main_x_right,
                sub_y_top,
                sub_y_bot,
                pal=pal,
                y_ticks=_d_ticks,
                y_min=_d_min,
                y_max=_d_max,
                orient="horizontal",
            )
        )
        # Zero line (where derivative sign flips → spectral peak positions).
        if _d_min <= 0.0 <= _d_max:
            parts.append(
                rigor.draw_zero_line(
                    main_x_left,
                    main_x_right,
                    _SY(0.0),
                    pal=pal,
                    stroke_width=1.0,
                    dasharray="4 3",
                )
            )
        _der_d = " ".join(f"{'M' if i == 0 else 'L'} {X(xs[i]):.1f} {_SY(_dy[i]):.1f}" for i in range(n))
        parts.append(f'<path d="{_der_d}" fill="none" stroke="{accent}" stroke-width="1.3"/>')
        # Sub-panel Y axis (compact: only extreme ticks).
        _sub_fs_tick = max(10.0, fs["ytick"] * 0.85)
        _sub_fs_title = max(11.0, fs["yaxis"] * 0.85)
        parts.append(
            rigor.draw_y_axis(
                main_x_left,
                sub_y_top,
                sub_y_bot,
                _d_ticks,
                _d_min,
                _d_max,
                unit="",
                pal=pal,
                fs_tick=_sub_fs_tick,
                fs_title=_sub_fs_title,
                title=tr("dI/dx"),
                side="left",
            )
        )
        _cap_fs = max(10.0, fs["label"] * 0.85)
        parts.append(
            f'<text x="{main_x_right - 8:.1f}" y="{sub_y_top + _cap_fs + 2:.1f}" '
            f'font-size="{_cap_fs:.1f}" fill="{ink6}" text-anchor="end" '
            f'font-style="italic">1st derivative</text>'
        )

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 36))

    return rigor.wrap_svg(parts, W, H, body_font)
