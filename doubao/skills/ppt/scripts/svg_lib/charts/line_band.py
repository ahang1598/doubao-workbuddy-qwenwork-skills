"""Scientific response curves with independent observations, errors and bands."""

from .._common import _variant_is_classic
from ._chart_layout import finite
from ._xy import fit_series, make_xy_chart, normalize_series


def _line_series(series):
    result = []
    for i, raw in enumerate(series):
        s = dict(raw)
        if "x" in s or "y_mean" in s:
            if "points" in s or "curve" in s:
                raise ValueError("use canonical points/curve or legacy x/y_mean, not both")
            xs, ys = s.get("x", []), s.get("y_mean", [])
            if not xs or len(xs) != len(ys):
                raise ValueError("x / y_mean must be nonempty with matching lengths")
            for key in ("y_ci_up", "y_ci_dn", "x_err", "y_err", "n_per_point"):
                if key in s and len(s[key]) != len(xs):
                    raise ValueError(f"{key} length must match x")
            if ("y_ci_up" in s) != ("y_ci_dn" in s):
                raise ValueError("both y_ci_up and y_ci_dn are required")
            s["points"] = [{"x": x, "y": y} for x, y in zip(xs, ys)]
            s["curve"] = [{"x": x, "y": y} for x, y in zip(xs, ys)]
            for j, p in enumerate(s["points"]):
                for key in ("x_err", "y_err"):
                    if key in s:
                        p[key] = s[key][j]
            if "y_ci_up" in s:
                for j, p in enumerate(s["curve"]):
                    p.update(lo=s["y_ci_dn"][j], hi=s["y_ci_up"][j])
        result.append(s)
    return normalize_series(result)


def make_line_band(
    series,
    *,
    x_unit="",
    y_unit="",
    x_title=None,
    y_title=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    reference_lines=None,
    highlight_series=None,
    show_n_per_point=False,
    sample_sizes=None,
    width=1300,
    height=760,
    font_family=None,
    palette=None,
    variant=None,
    multi_mode="auto",
    phases=None,
    significance=None,
    x_transform="linear",
    y_transform="linear",
):
    """Draw supplied curves and observation points without conflating their grids.

    **When to use**: 已有时序观测/曲线及有效的不确定性区间，明确 SD/SEM/CI
    的含义。普通趋势、训练损失等无区间曲线用 ``make_scatter`` 的 ``curve``
    输入连接实际 x/y；无拟合任务时 ``fit=None``，无区间时 ``show_ci=False``。
    ROC/PR 用 ``roc_pr``；有起终值和可加增减项的贡献分解用 ``waterfall``。

    Legacy ``{name,x,y_mean,y_ci_up,y_ci_dn}`` remains supported. Canonical series
    use ``points`` for measured samples and ``curve`` for independently sampled
    predictions; ``marker='none'`` suppresses observation glyphs, not error bars.
    Optional ``fit='loess'`` derives a curve from the observations. ``phases`` is
    a list of {start,end,label}; significance entries are {x,p} or {x,label}.
    """
    _variant_is_classic("line_band", variant)
    resolved = _line_series(series)
    if highlight_series is not None and highlight_series not in [s["name"] for s in resolved]:
        raise ValueError("highlight_series must name an existing series")
    if highlight_series:
        for s in resolved:
            s["_emphasis"] = s["name"] == highlight_series
    resolved = fit_series(resolved, x_transform=x_transform, y_transform=y_transform)
    if multi_mode not in (None, "single", "off", "auto", "with_sample_size"):
        raise ValueError("multi_mode must be single, auto or with_sample_size")
    sample_tracks = []
    if sample_sizes is not None:
        sample_tracks.append(
            {"name": resolved[0]["name"], "positions": [p["x"] for p in resolved[0]["points"]], "counts": sample_sizes}
        )
    elif show_n_per_point:
        for s in resolved:
            if s.get("n_per_point") is not None:
                sample_tracks.append(
                    {"name": s["name"], "positions": [p["x"] for p in s["points"]], "counts": s["n_per_point"]}
                )
        if not sample_tracks:
            raise ValueError("show_n_per_point requires n_per_point data")
    for track in sample_tracks:
        if len(track["positions"]) != len(track["counts"]):
            raise ValueError("sample sizes must match their source-series observations")
        for n in track["counts"]:
            if finite(n, "sample size", minimum=0) % 1:
                raise ValueError("sample sizes must be integers")
    use_samples = bool(sample_tracks) and (multi_mode in ("auto", "with_sample_size") or show_n_per_point)
    if multi_mode == "with_sample_size" and not sample_tracks:
        raise ValueError("with_sample_size requires sample_sizes")
    return make_xy_chart(
        resolved,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        x_title=x_title,
        y_title=y_title,
        x_unit=x_unit,
        y_unit=y_unit,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
        x_transform=x_transform,
        y_transform=y_transform,
        reference_lines=reference_lines,
        phases=phases,
        significance=significance,
        sample_sizes=sample_tracks if use_samples else None,
    )
