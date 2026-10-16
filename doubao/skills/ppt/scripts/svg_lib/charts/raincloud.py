"""Raincloud plots: a half KDE, Tukey box and actual observations per group."""

from ._distribution import render_distribution


def make_raincloud(
    groups,
    *,
    orientation="horizontal",
    paired=False,
    conditions=None,
    y_unit="",
    y_title=None,
    y_min=None,
    y_max=None,
    bandwidth=None,
    academic=False,
    pairwise_p=None,
    auto_test=None,
    pairs=None,
    multi_mode=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    width=1200,
    height=None,
    palette=None,
    font_family=None,
):
    """Return SVG; observations may be numbers or ``{value, subject_id}`` records.

    ``paired=True`` connects matching subject IDs across adjacent groups.
    ``conditions=[(facet_name, groups), ...]`` uses a common numeric domain.
    Precomputed P values may be a list, or a mapping from facet name to list.
    """
    if multi_mode not in (None, "auto", "single", "off", "with_condition_facets", "with_effect_size"):
        raise ValueError(f"unsupported raincloud multi_mode {multi_mode!r}")
    if multi_mode == "with_condition_facets" and conditions is None:
        raise ValueError("with_condition_facets requires conditions")
    return render_distribution(
        groups,
        kind="raincloud",
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
        effect_size=multi_mode == "with_effect_size",
    )
