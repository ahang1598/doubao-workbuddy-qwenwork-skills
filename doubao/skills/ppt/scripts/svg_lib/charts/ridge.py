"""Consistent sample statistics and measured layout for ridge charts."""

from __future__ import annotations

from collections.abc import Sequence


def make_ridge(
    distributions: Sequence[Sequence[float]],
    group_labels: Sequence[str] | None = None,
    x_range: Sequence[float] | None = None,
    x_labels: Sequence[str] | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    highlight_index: int | None = None,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    *,
    academic: bool = False,
    x_unit: str | None = None,
    multi_mode: str = "auto",
    width: float | None = None,
    height: float | None = None,
    conditions=None,
) -> str:
    """Ridges from named raw samples or unnamed precomputed density matrices.

    ``conditions=[(facet_name, named_rows), ...]`` shares domains and row order.
    A named row can hold ``{series_name: observations}`` for grouped densities.
    ``with_counts`` shows true sample totals; ``with_median_trend`` shows group
    medians on a calibrated panel. Cosmetic variants retain the same statistics.
    """
    from ._ridge_distribution import render_ridge

    return render_ridge(
        distributions,
        group_labels,
        x_range,
        conditions=conditions,
        variant=variant,
        title=title,
        subtitle=subtitle,
        x_unit=x_unit,
        x_labels=x_labels,
        academic=academic,
        highlight_index=highlight_index,
        multi_mode=multi_mode,
        width=width,
        height=height,
        palette=palette,
        font_family=font_family,
    )
