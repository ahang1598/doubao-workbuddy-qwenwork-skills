"""Heatmaps, correlation glyphs and independently scaled triangular matrices."""

from __future__ import annotations

from ._matrix_core import VARIANTS, numeric_matrix, render_matrix, table_values

_VARIANTS = VARIANTS


def make_matrix_heat(
    matrix,
    labels=None,
    row_labels=None,
    col_labels=None,
    row_sub_labels=None,
    domain_groups=None,
    colormap="auto",
    midpoint=None,
    vmin=None,
    vmax=None,
    show_row_mean=None,
    show_col_mean=None,
    show_colorbar=True,
    colorbar_label="SCORE",
    colorbar_sub=None,
    value_fmt=None,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    highlight_pair=None,
    font_family=None,
    palette=None,
    variant=None,
    multi_mode="auto",
    compare_cols=None,
    width=1300,
    height=820,
    *,
    cell_text=None,
    cell_label_position="center",
    pvalues=None,
    mask=None,
    upper_matrix=None,
    upper_scale=None,
    row_annotation=None,
    col_annotation=None,
    columns=None,
    size_matrix=None,
    size_max=None,
    size_label="Size",
):
    """Render a complete SVG in one call.

    Variants: ``annotated_number`` shows filled cells with numbers;
    ``square_flat_full`` is the plain full matrix; ``circle_full`` uses circles
    with area proportional to magnitude; ``pie_full`` uses angular magnitude;
    ``ellipse_upper`` shows only the upper triangle and must not be used to
    hide observations in an ordinary category matrix. ``cell_label_position``
    is ``center`` by default; ``below`` reserves a separate label row inside
    each circle/pie cell so numbers remain readable on light or dark themes.

    ``labels`` applies to both axes of a square matrix, or to columns of a
    rectangular matrix. Explicit row_labels / col_labels take precedence.
    ``mask[i][j] is True`` excludes a cell, including from means and scales.
    ``cell_text`` and ``pvalues`` are aligned matrices; p-values < .05/.01/.001
    add *, **, *** without calculating an inferential test.
    ``upper_matrix`` supplies cells strictly above the diagonal. ``upper_scale``
    accepts vmin, vmax, midpoint, colormap, palette and label independently of
    the lower matrix. Optional size_matrix gives independent dot areas; upper
    size_max/size_label/size_legend_values belong to upper_scale. Means default
    off for independently scaled columns/triangles, which may have different units.
    ``columns`` is an optional schema of {name, type} entries, where type is
    number, category or text. Numeric entries accept scale options; categories
    accept a colors mapping. Original text/category observations stay literal. ``row_annotation`` / ``col_annotation`` accept one sequence or a
    dict mapping track names to sequences. Values may be categories, continuous
    numbers, or (category, color) pairs. The old API requires no additional step.
    ``compare_cols`` compares the actual displayed observations, including an
    upper matrix; all compared observations must share a numeric unit. It is
    unavailable for a heterogeneous columns schema. ``value_fmt=None`` uses
    adaptive precision; an explicit Python format string is respected.
    """
    if columns is not None:
        data, _ = table_values(matrix, columns)
    else:
        data = numeric_matrix(matrix)
    nr, nc = len(data), len(data[0])
    independent_units = columns is not None or upper_matrix is not None
    if independent_units and (show_row_mean is True or show_col_mean is True):
        raise ValueError("Means across independently scaled table columns / triangles are ambiguous; disable them")
    show_row_mean = not independent_units if show_row_mean is None else show_row_mean
    show_col_mean = not independent_units if show_col_mean is None else show_col_mean
    if row_labels is None:
        row_labels = labels if labels is not None and nr == nc else [str(i + 1) for i in range(nr)]
    if col_labels is None:
        col_labels = (
            labels
            if labels is not None
            else (
                [c.get("name", str(i + 1)) for i, c in enumerate(columns)]
                if columns is not None
                else [str(i + 1) for i in range(nc)]
            )
        )
    modes = {None, "auto", "single", "none", "with_selected_comparison"}
    if multi_mode not in modes:
        raise ValueError(f"Unknown matrix_heat multi_mode {multi_mode!r}")
    if multi_mode == "with_selected_comparison" and compare_cols is None:
        raise ValueError("with_selected_comparison requires compare_cols")
    selected = compare_cols if multi_mode not in {"single", "none"} else None
    resolved = "with_selected_comparison" if selected is not None else "single"
    selected_variant = (
        ("circle_full" if size_matrix is not None else "annotated_number")
        if variant in {None, "classic", "default", "academic"}
        else variant
    )
    return render_matrix(
        data,
        row_labels,
        col_labels,
        variant=selected_variant,
        scale_options={"colormap": colormap, "midpoint": midpoint, "vmin": vmin, "vmax": vmax, "label": colorbar_label},
        cell_text=cell_text,
        cell_label_position=cell_label_position,
        pvalues=pvalues,
        mask=mask,
        upper_matrix=upper_matrix,
        upper_scale=upper_scale,
        row_annotation=row_annotation,
        col_annotation=col_annotation,
        row_sub_labels=row_sub_labels,
        domain_groups=domain_groups,
        show_row_mean=show_row_mean,
        show_col_mean=show_col_mean,
        show_colorbar=show_colorbar,
        colorbar_sub=colorbar_sub,
        value_fmt=value_fmt,
        highlight_pair=highlight_pair,
        compare_cols=selected,
        columns=columns,
        size_matrix=size_matrix,
        size_max=size_max,
        size_label=size_label,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        note=note,
        source=source,
        width=width,
        height=height,
        font_family=font_family,
        palette=palette,
        metadata={"chart": "matrix_heat", "resolved_mode": resolved, "fallback_reason": None},
    )


def draw_matrix_heat(
    data, variant="square_flat_full", palette="archive_ink", width=900, height=720, title=None, subtitle=None, **kwargs
):
    """Data-dict variant API; forwards all supported matrix options unchanged."""
    options = dict(data)
    if "diverging" in options:
        diverging = options.pop("diverging")
        if diverging is not None:
            options.setdefault("colormap", "diverging" if diverging else "sequential")
    options.update(kwargs)
    options.update(variant=variant, palette=palette, width=width, height=height, title=title, subtitle=subtitle)
    options.setdefault("show_row_mean", False)
    options.setdefault("show_col_mean", False)
    return make_matrix_heat(**options)
