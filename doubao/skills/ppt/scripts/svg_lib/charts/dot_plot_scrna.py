"""General size/color dot matrices and a compatible scRNA-seq wrapper."""

from __future__ import annotations

from ._matrix_core import numeric_matrix, render_matrix
from ._shared import tr


def make_dot_matrix(
    size_matrix,
    color_matrix,
    row_labels,
    col_labels,
    *,
    size_label="Size",
    colorbar_label="Value",
    size_max=None,
    size_legend_values=None,
    colormap="auto",
    midpoint=None,
    vmin=None,
    vmax=None,
    log_color=False,
    cell_text=None,
    pvalues=None,
    mask=None,
    row_annotation=None,
    col_annotation=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    width=1300,
    height=820,
    font_family=None,
    palette=None,
    variant=None,
):
    """Dot area is directly proportional to nonnegative size; color is independent.

    A zero size draws no dot; missing size or color draws a missing-cell marker.
    ``size_max`` defaults to the observed maximum and cannot clip observations.
    Either annotation argument accepts one sequence or named tracks in a dict.
    For categorical color_matrix values, pass colormap={category: color};
    categories receive a key instead of a continuous numeric colorbar.
    """
    if variant not in {None, "classic", "default", "academic", "circle_full"}:
        raise ValueError("dot_matrix supports the circle_full variant")
    return render_matrix(
        color_matrix,
        row_labels,
        col_labels,
        variant="circle_full",
        size_matrix=size_matrix,
        size_max=size_max,
        size_label=size_label,
        size_legend_values=size_legend_values,
        scale_options={
            "colormap": colormap,
            "midpoint": midpoint,
            "vmin": vmin,
            "vmax": vmax,
            "log": log_color,
            "label": colorbar_label,
        },
        cell_text=cell_text,
        pvalues=pvalues,
        mask=mask,
        row_annotation=row_annotation,
        col_annotation=col_annotation,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        font_family=font_family,
        palette=palette,
        metadata={"chart": "dot_matrix", "resolved_mode": "single", "fallback_reason": None},
    )


def make_dot_plot_scrna(
    genes,
    clusters,
    pct_expr,
    mean_expr,
    *,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    expr_unit="",
    pct_legend_values=(25, 50, 75, 100),
    cluster_annotation=None,
    log_color=False,
    width=1300,
    height=820,
    font_family=None,
    palette=None,
    variant=None,
    multi_mode="auto",
    cell_text=None,
    pvalues=None,
    mask=None,
    row_annotation=None,
    colormap="auto",
    midpoint=None,
    vmin=None,
    vmax=None,
):
    """scRNA-seq matrix: percent expressing controls area; mean expression color.

    The old signature and the supplied annotation colors are preserved.
    Percentages outside [0,100] raise instead of being silently clipped.
    with_marker_summary shows the observed cross-cluster mean per gene,
    aligned to the same gene rows, and retains the size and color legends.
    """
    pct = numeric_matrix(pct_expr, "pct_expr", (len(genes), len(clusters)), nonnegative=True)
    if any(v > 100 for row in pct for v in row if v is not None):
        raise ValueError("pct_expr values must lie between 0 and 100")
    if variant not in {None, "classic", "default", "academic", "circle_full"}:
        raise ValueError("dot_plot_scrna supports the circle_full variant")
    if multi_mode not in {None, "auto", "single", "none", "with_marker_summary"}:
        raise ValueError(f"Unknown dot_plot_scrna multi_mode {multi_mode!r}")
    summary = multi_mode == "with_marker_summary" or (multi_mode == "auto" and len(clusters) >= 4)
    if summary and len(clusters) < 4:
        raise ValueError("with_marker_summary requires at least four clusters")
    return render_matrix(
        mean_expr,
        genes,
        clusters,
        variant="circle_full",
        size_matrix=pct,
        size_max=100,
        size_label=tr("% expressing"),
        size_legend_values=pct_legend_values,
        size_suffix="%",
        italic_rows=True,
        show_row_mean=summary,
        row_mean_label=tr("Mean expression"),
        scale_options={
            "colormap": colormap,
            "midpoint": midpoint,
            "vmin": vmin,
            "vmax": vmax,
            "log": log_color,
            "label": tr("Mean expression ({unit})", unit=expr_unit) if expr_unit else tr("Mean expression"),
        },
        cell_text=cell_text,
        pvalues=pvalues,
        mask=mask,
        row_annotation=row_annotation,
        col_annotation=cluster_annotation,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        font_family=font_family,
        palette=palette,
        metadata={
            "chart": "dot_plot_scrna",
            "resolved_mode": "with_marker_summary" if summary else "single",
            "fallback_reason": None,
        },
    )
