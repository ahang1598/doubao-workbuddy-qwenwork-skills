"""Consistent sample statistics and measured layout for boxplot charts."""

from __future__ import annotations

from ._distribution import render_distribution

VARIANTS = ("default_flat", "beeswarm", "notched_outlined", "variable_width_gradient", "strip_flat")


def draw_boxplot(
    data: dict,
    variant: str = "default_flat",
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
    show_jitter=True,
    show_mean=True,
    show_legend=True,
    font_family=None,
    multi_mode=None,
) -> str:
    """Render a boxplot variant using the same sample and axis semantics."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown boxplot variant {variant!r}; expected {VARIANTS}")
    if multi_mode not in (None, "auto", "single", "off", "with_condition_facets", "with_effect_size"):
        raise ValueError(f"unsupported multi_mode {multi_mode!r}")
    if multi_mode == "with_condition_facets" and conditions is None:
        raise ValueError("with_condition_facets requires conditions")
    from ._distribution import render_distribution

    return render_distribution(
        data.get("groups"),
        kind="boxplot",
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
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
        show_points=show_jitter,
        show_mean=show_mean,
        show_legend=show_legend,
        highlight_group=data.get("highlight_name"),
        effect_size=multi_mode == "with_effect_size",
    )


def make_boxplot(
    groups,
    y_unit: str = "",
    highlight_group: str | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    y_title: str | None = None,
    note: str | None = None,
    source: str | None = None,
    show_legend: bool = True,
    show_jitter: bool = True,
    show_mean: bool = True,
    multi_mode: str = "auto",
    width: float = 1200,
    height: float | None = None,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    *,
    academic: bool = False,
    pairwise_p=None,
    auto_test: str | None = None,
    pairs=None,
    orientation: str = "vertical",
    paired: bool = False,
    conditions=None,
) -> str:
    """Sample boxplots with Tukey whiskers, optional ID pairing and facets.

    ``groups=[(name, observations), ...]`` accepts finite numbers or records
    ``{value, subject_id}``. ``paired=True`` connects matching IDs, whereas
    ``pairs`` selects statistical tests. ``conditions=[(name, groups), ...]``
    preserves a common numeric scale; P values may be keyed by condition.
    ``multi_mode='with_effect_size'`` explicitly requests the effect panel.
    Academic styling and automatic layout never request inferential statistics.
    Pairing requires actual subject IDs; unlabelled arrays do not establish independence.
    """
    if variant not in (None, "classic", *VARIANTS):
        raise ValueError(f"unknown boxplot variant {variant!r}")
    if multi_mode not in (None, "auto", "single", "off", "with_condition_facets", "with_effect_size"):
        raise ValueError(f"unsupported boxplot multi_mode {multi_mode!r}")
    if multi_mode == "with_condition_facets" and conditions is None:
        raise ValueError("with_condition_facets requires conditions")
    return render_distribution(
        groups,
        kind="boxplot",
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
        y_title=y_title,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
        show_points=show_jitter,
        show_mean=show_mean,
        show_legend=show_legend,
        highlight_group=highlight_group,
        effect_size=multi_mode == "with_effect_size",
    )
