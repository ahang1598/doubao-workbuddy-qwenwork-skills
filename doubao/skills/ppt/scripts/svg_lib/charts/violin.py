"""Consistent sample statistics and measured layout for violin charts."""

from __future__ import annotations

from collections.abc import Sequence

from ._distribution import render_distribution

VARIANTS = ("boxplot_inner_flat", "quartile_outlined", "points_inner_flat", "half_gradient", "kde_only", "overlay")


def draw_violin(
    data: dict,
    variant: str = "boxplot_inner_flat",
    palette="archive_ink",
    width: float = 900,
    height: float = 540,
    title=None,
    subtitle=None,
    y_axis_label=None,
    figure_label=None,
    note=None,
    source=None,
    *,
    academic=False,
    pairwise_p=None,
    auto_test=None,
    pairs=None,
    y_min=None,
    y_max=None,
    orientation="vertical",
    paired=False,
    conditions=None,
    bandwidth=None,
    show_boxplot=True,
    show_mean=True,
    show_outliers=True,
    show_legend=True,
    per_group_n=None,
    font_family=None,
    multi_mode=None,
) -> str:
    """Render every violin variant from raw observations with shared axes."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown violin variant {variant!r}; expected {VARIANTS}")
    if multi_mode not in (None, "auto", "single", "off", "with_condition_facets", "with_effect_size"):
        raise ValueError(f"unsupported multi_mode {multi_mode!r}")
    if multi_mode == "with_condition_facets" and conditions is None:
        raise ValueError("with_condition_facets requires conditions")
    from ._distribution import render_distribution

    return render_distribution(
        data.get("groups"),
        kind="violin",
        variant=variant,
        orientation=orientation,
        paired=paired,
        conditions=conditions,
        academic=academic,
        pairwise_p=pairwise_p,
        auto_test=auto_test,
        pairs=pairs,
        y_min=y_min,
        y_max=y_max,
        y_unit=data.get("unit", ""),
        y_title=y_axis_label,
        bandwidth=bandwidth,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
        show_points=(variant == "points_inner_flat" or paired),
        show_boxplot=show_boxplot,
        show_mean=show_mean,
        show_outliers=show_outliers,
        show_legend=show_legend,
        per_group_n=per_group_n,
        highlight_group=data.get("highlight_name"),
        effect_size=multi_mode == "with_effect_size",
    )


def make_violin(
    groups: Sequence[Sequence] | None = None,
    y_unit: str = "",
    highlight_group: str | None = None,
    bandwidth: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    figure_note: str | None = None,
    y_axis_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    width: float = 1200.0,
    height: float | None = None,
    show_boxplot: bool = True,
    show_mean: bool = True,
    show_outliers: bool = True,
    show_legend: bool = True,
    per_group_n: list[int] | None = None,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    *,
    academic: bool = False,
    pairwise_p=None,
    auto_test: str | None = None,
    pairs=None,
    multi_mode: str | None = None,
    conditions=None,
    y_title: str | None = None,
    orientation: str = "vertical",
    paired: bool = False,
) -> str:
    """Violin distributions with raw observations, pairing, facets and effects.

    ``variant='overlay'`` overlays exactly two periods using filled solid and
    dashed contours. Numeric observations and ``{value, subject_id}`` records
    share the boxplot schema. ``orientation='mirrored'`` uses exactly two
    named ``conditions`` as independent numeric variables, with a reversed
    left axis and a single aligned central category column. ``per_group_n`` is a display-count override in
    either orientation; raw observations still determine the density/statistics.
    Effect-size inference requires explicit multi_mode="with_effect_size";
    automatic layout and academic styling do not assume independent samples.
    """
    if variant not in (None, "classic", *VARIANTS):
        raise ValueError(f"unknown violin variant {variant!r}")
    if multi_mode not in (None, "auto", "single", "off", "with_condition_facets", "with_effect_size"):
        raise ValueError(f"unsupported violin multi_mode {multi_mode!r}")
    if multi_mode == "with_condition_facets" and conditions is None:
        raise ValueError("with_condition_facets requires conditions")
    return render_distribution(
        groups,
        kind="violin",
        variant=variant,
        orientation=orientation,
        paired=paired,
        conditions=conditions,
        academic=academic,
        pairwise_p=pairwise_p,
        auto_test=auto_test,
        pairs=pairs,
        y_min=y_min,
        y_max=y_max,
        y_unit=y_unit,
        y_title=y_axis_label or y_title,
        bandwidth=bandwidth,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=" · ".join(str(value) for value in (figure_note, note) if value) or None,
        source=source,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
        show_points=(variant == "points_inner_flat" or paired),
        show_boxplot=show_boxplot,
        show_mean=show_mean,
        show_outliers=show_outliers,
        show_legend=show_legend,
        per_group_n=per_group_n,
        highlight_group=highlight_group,
        effect_size=multi_mode == "with_effect_size",
    )
