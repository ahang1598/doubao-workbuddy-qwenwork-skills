"""Grouped scientific scatter, independent prediction curves and exact OLS CI."""

import math

from .._common import _variant_is_classic
from ._xy import (
    _predict_model,
    add_frontier,
    fit_series,
    interpolate_curve,
    make_xy_chart,
    normalize_series,
    points_to_series,
)
from ._xy import (
    linreg as _linreg,
)
from ._xy import (
    loess as _loess_fit,
)

__all__ = ["_linreg", "_loess_fit", "make_scatter", "make_scatter_fit"]


def _residuals(series, *, y_transform=None):
    """Fitted residuals use the exact model."""
    result = []
    if y_transform is None:
        model_units = {s["_model"]["y_transform"] for s in series if s.get("_model")}
        if len(model_units) > 1:
            raise ValueError("mixed model transforms require an explicit common residual transform")
        y_transform = next(iter(model_units), "linear")
    for s in series:
        if not s["points"]:
            continue
        model = s.get("_model")
        transform = y_transform or (model["y_transform"] if model else "linear")
        if model:
            xs = [math.log10(p["x"]) if model["x_transform"] == "log10" else p["x"] for p in s["points"]]
            predicted = _predict_model(model, xs)
            if transform != model["y_transform"]:
                predicted = [10**v if model["y_transform"] == "log10" else math.log10(v) for v in predicted]
        else:
            predicted = [interpolate_curve(s["curve"], p["x"]) for p in s["points"]]
            if transform == "log10":
                if any(v <= 0 for v in predicted):
                    raise ValueError("log10 residuals require positive external predictions")
                predicted = [math.log10(v) for v in predicted]
        points = []
        for p, predicted_y in zip(s["points"], predicted):
            actual = math.log10(p["y"]) if transform == "log10" else p["y"]
            point = dict(p, y=actual - predicted_y, label="")
            if transform == "log10" and "y_err" in p:
                lo, hi = p["y_err"]
                if p["y"] - lo <= 0:
                    raise ValueError("log10 residual errors require positive error endpoints")
                point["y_err"] = (actual - math.log10(p["y"] - lo), math.log10(p["y"] + hi) - actual)
            points.append(point)
        result.append(
            {
                "name": s["name"],
                "marker": s.get("marker", "circle"),
                "points": points,
                "_residual_unit": "log10(y)" if transform == "log10" else "y",
            }
        )
    return normalize_series(result)


def make_scatter(
    points,
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
    highlight_mask=None,
    fit=None,
    show_ci=True,
    show_stats_box=False,
    multi_mode="single",
    x_transform="linear",
    y_transform="linear",
    reference_lines=None,
    phases=None,
    significance=None,
    annotations=None,
    summary=False,
    frontier=None,
    projected_from=None,
    reference_band=None,
    end_labels=True,
    width=1200,
    height=820,
    font_family=None,
    palette=None,
    variant=None,
):
    """One-call grouped scatter/curve chart.

    Accepts a flat x/y point list (dict points may contain ``group``) or canonical
    series ``{name, points, curve, fit, marker, color}``. Observation points may
    contain asymmetric error magnitudes, labels, sizes, and one categorical axis.
    ``summary=True`` adds the observed group mean and SEM on numerical axes.
    ``x_transform``/``y_transform`` are ``linear`` or ``log10``.

    Trend/curve mode (series with ``curve``, or ``phases``/``annotations``):
    axes hug the data and include reference values; ≤4 curves are labelled
    at their right end ("name  last value") instead of a legend; the last
    point is emphasised; ``end_labels=False`` turns those off (a legend names the curves instead).
    ``reference_lines=[{value, label, axis}]`` draws a
    dashed line labelled at its end; ``phases=[{start, end, label}]`` are light
    bands; ``significance=[{x, p}]`` (or ``label``; ``between=[name, name]``)
    draws a bracket between two curves at x; ``annotations=[{x, y, text}]``
    adds key-event labels with short leaders; ``y_err`` gives capped error bars.
    ``frontier=True`` joins the non-dominated points (lower x, higher y better — e.g. params vs accuracy)
    with a dashed Pareto-front line; ``"min"`` when lower y is better (materials: 强度–塑性权衡 strength vs
    elongation, ``frontier=True`` with x=strength, y=elongation). ``projected_from=2024`` draws every curve
    dashed from that x on (forecast / scenario segment); per series use ``dashed_from``.
    ``reference_band={'points': [(x, y), ...], 'label': '传统合金'}`` (or a list) shades the envelope of a
    reference population behind the points (e.g. conventional alloys on a strength–ductility map). Not for x = horizon after a shock:
    impulse responses use ``coef_plot(series=…, band=True)``.

    学术趋势图写法：单条曲线信息量不足。至少加一项：对比系列、带标注的参考/极限线、
    阶段 phases、关键事件 annotations、误差棒 y_err + 显著性 p，或报告区间（curve 的 lo/hi）。
    数值只用来源数据，不补造。示例：
        make_scatter([
            {"name": "对照", "points": [{"x": 0, "y": 100}, {"x": 500, "y": 78, "y_err": 3.1},
                {"x": 1000, "y": 52, "y_err": 4.4}],
             "curve": [{"x": 0, "y": 100}, {"x": 500, "y": 78}, {"x": 1000, "y": 52}]},
            {"name": "封装", "points": [{"x": 0, "y": 100}, {"x": 500, "y": 96, "y_err": 1.4},
                {"x": 1000, "y": 91, "y_err": 2.0}],
             "curve": [{"x": 0, "y": 100, "lo": 100, "hi": 100}, {"x": 500, "y": 96, "lo": 94, "hi": 98},
                {"x": 1000, "y": 91, "lo": 88, "hi": 94}]}],
            x_title="老化时间", x_unit="h", y_title="归一化 PCE", y_unit="%",
            reference_lines=[{"value": 80, "label": "T80", "axis": "y"}],
            significance=[{"x": 1000, "p": 0.0003}],
            annotations=[{"x": 500, "y": 78, "text": "湿热循环开始"}],
            width=880, height=420)
    """
    _variant_is_classic("scatter_fit", variant)
    series = points_to_series(points, fit=fit, highlight_mask=highlight_mask)
    if projected_from is not None:
        from ._chart_layout import finite as _finite

        projected_from = _finite(projected_from, "projected_from")
        series = [dict(s, dashed_from=s.get("dashed_from", projected_from)) for s in series]
    series = fit_series(series, show_ci=show_ci, x_transform=x_transform, y_transform=y_transform)
    series = add_frontier(series, frontier)
    n = sum(len(s["points"]) for s in series)
    if multi_mode not in (None, "single", "off", "auto", "with_residual", "with_marginal"):
        raise ValueError("multi_mode must be single, auto, with_residual or with_marginal")
    if multi_mode == "auto":
        multi_mode = (
            "with_residual"
            if n >= 30 and width >= 650 and height >= 570 and all(s.get("fit") == "linear" for s in series)
            else "with_marginal"
            if n >= 60 and width >= 650 and height >= 540
            else "single"
        )
    residual = _residuals(series, y_transform=y_transform) if multi_mode == "with_residual" else None
    trend = multi_mode in (None, "single", "off") and (
        any(s["curve"] and not s.get("_model") for s in series) or bool(phases) or bool(annotations)
    )
    return make_xy_chart(
        series,
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
        show_stats=show_stats_box,
        mode=multi_mode,
        residual_series=residual,
        summary=summary,
        trend=trend,
        annotations=annotations,
        reference_bands=reference_band,
        end_labels=end_labels,
    )


def make_scatter_fit(
    points,
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
    highlight_mask=None,
    fit="linear",
    show_ci=True,
    show_stats_box=True,
    multi_mode="auto",
    width=1200,
    height=820,
    font_family=None,
    palette=None,
    variant=None,
    reference_lines=None,
    x_transform="linear",
    y_transform="linear",
):
    """Compatible fitted-scatter entry; grouped inputs use the same shared core."""
    return make_scatter(
        points,
        x_unit=x_unit,
        y_unit=y_unit,
        x_title=x_title,
        y_title=y_title,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        highlight_mask=highlight_mask,
        fit=fit,
        show_ci=show_ci,
        show_stats_box=show_stats_box,
        multi_mode=multi_mode,
        width=width,
        height=height,
        font_family=font_family,
        palette=palette,
        variant=variant,
        reference_lines=reference_lines,
        x_transform=x_transform,
        y_transform=y_transform,
    )
