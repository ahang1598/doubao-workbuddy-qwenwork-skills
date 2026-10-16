"""Adaptive nonnegative category/series comparison. The original grouped schema
selects Cartesian bar, matrix, distribution or interval views; explicit Cartesian
"""

from __future__ import annotations

import math

from .._common import (
    _derive_series_colors,
    _dist_font_sizes,
    _estimate_label_width_px,
    _fmt_axis,
    _resolve_font,
    _resolve_palette,
    _rgb_prefix,
    _variant_is_classic,
    _xesc,
)
from . import _academic_rigor as rigor
from .bar_academic import _err_halfwidth, _mean
from ._shared import tr


# Multi-mode whitelist: maps mode name → (template, trigger, validator).
def _validate_facet_by_series(s):
    n_s = s.get("n_series", 0)
    n_c = s.get("n_categories", 0)
    if n_s < 2:
        return (False, "need >= 2 series")
    if n_c < 3:
        return (False, "need >= 3 categories")
    # Also require each cell to have at least 1 value
    for si, rows in enumerate(s.get("series_values") or []):
        for ci, vals in enumerate(rows):
            if not vals:
                return (False, f"series[{si}] cat[{ci}] empty")
    return (True, "")


_GROUPED_BAR_MULTI_WHITELIST = {
    "with_facet_by_series": (
        None,  # layout handled by allocate_facet_grid, not allocate_main_sub
        lambda s: s.get("n_series", 0) >= 2 and s.get("n_categories", 0) >= 3,
        lambda s: _validate_facet_by_series(s),
    ),
}


def _wrap_label(text, width, fs, font_family, *, bold=False):
    """Wrap the complete label, including unspaced names, using measured widths."""
    lines = []
    remaining = str(text)
    while remaining:
        end = len(remaining)
        while end > 1 and _estimate_label_width_px(remaining[:end], fs, bold=bold, font_family=font_family) > width:
            end -= 1
        if end < len(remaining):
            space = remaining.rfind(" ", 0, end + 1)
            if space > 0:
                end = space
        lines.append(remaining[:end].rstrip())
        remaining = remaining[end:].lstrip()
    return lines or [""]


def make_grouped_bar(
    categories,
    series,
    *,
    y_unit: str = "",
    orientation: str = "vertical",
    stack: str | None = None,
    axis_break=None,
    line_series=None,
    right_y_unit: str = "",
    right_y_title: str | None = None,
    value_domain=None,
    x_title: str | None = None,
    y_title: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    figure_label: str | None = None,
    note: str | None = None,
    source: str | None = None,
    error_kind: str = "SEM",
    show_points: bool = True,
    pairwise_p=None,
    auto_test: str | None = None,
    pairs=None,
    highlight_series: str | None = None,
    width: float = 1300,
    height: float = 760,
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
    show_values: bool | None = None,
    value_scale: str = "auto",
    ci_level=None,
    reference_lines=None,
) -> str:
    """Adaptive grouped comparison from one unchanged category/series schema.

    ``multi_mode='auto'``（默认；single/off/None 也使用相同的数据选型）：
      - 非负汇总值：最多 24 格、12 类、4 系列用直角坐标分组柱图（共享数值轴，
        数值标在柱端）；更密集用 matrix_heat 的 circle_full 圆点矩阵，颜色与
        圆面积都表示原值。行列可交换以适配画布，类别/系列及数据对应关系不变。
        数字放在圆点下方；默认标各类别最高值及零值，show_values=True 显示全部，
        False 关闭数值。未给 value_domain 时色阶按实际范围拟合；显式范围原样保留。
      - 每格都有 >=5 个真实观测：按类别分组或分面，箱线图 + 原始样本点；每格
        >=20 个观测且 >=5 个不同值时用雨云图。阈值只控制显示，不保证统计充分。
      - 少量重复观测、均值及 SD/SEM/CI、混合/缺失样本或跨类别比较：分组
        区间图；保留原区间口径、实际样本、数值与已请求的 P 值。
      - stack='stacked'/'percent' 且各格只有完整汇总值时：Marimekko 图，
        列宽表示类别总量，区块面积表示组分数量，列内标注组分占比。
        其他显式堆叠、横向、断轴、双轴设置按原几何语义绘制。

    显式选型：``bars / heatmap / intervals / boxplot / raincloud / marimekko``（环形已移除）。
    不满足数据条件或会丢失误差/样本/比较的选择会报错，提示改用适合的模式。
    ``with_facet_by_series`` 保留原先按系列拆图的显式用法。

    负观测、负汇总值、负区间或负轴域会报错，提示改用支持正负数轴的
    原生柱状图/折线图；不能取绝对值、截零或平移来规避。正样本计算出的
    误差下界若为负且需要画出，也会触发此提示。

    汇总值用 ``{'value': 24.0}``；真实重复用 ``[22,24,26]``；已有均值与
    SD 用 ``{'mean':24,'sd':2,'n':3}``（error_kind='SD'）。SEM/CI95 同理；
    ``lo/hi`` 为已提供的绝对区间边界。单项数组不能估计 SEM。
    ``value_scale``：``'auto'``（默认）在单纯柱图（无堆叠/断轴/双轴）且全部数值
    > 0、最大/最小 > 30 倍时改用对数数值轴（轴标题注明“对数轴”），避免小值柱
    看不见；``'log'`` 强制对数轴，``'linear'`` 强制线性轴。
    ``ci_level=95``：``lo/hi`` 为置信区间时注明水平，图例显示“95% CI”，否则为“区间”。
    ``show_values=False`` 隐藏数值标签；True 要求显式数值，自动选型遇到
    样本数据会使用区间图；竖向柱数值标在柱顶，``orientation='horizontal'``
    标在柱端右侧。单系列柱图不画图例（系列名已在数值轴标题）。数值相差
    < 15% 时 chart_slide 会提示改用 dumbbell / 点图，柱基线始终从 0 开始。
    ``reference_lines=[{"value": 1, "label": "无富集 (=1)"}]`` 在数值轴上画带标签的虚线
    参照线（竖向/横向柱、对数轴、区间图均可）；分布/热图视图会报错提示改用 intervals。
    ``show_points`` 控制原始观测叠加，不编造观测。
    配色沿用 palette；每个视图保留类别、系列、单位、来源和注释。

    ``categories``: list of category label strings (X axis groups).
    ``series``: list of ``(series_name, [[values for cat1], [values for cat2], ...])``.
    ``pairwise_p``: list of ``(cat_idx, series_a_idx, series_b_idx, p)``, optional.
    Cross-category comparisons use ``{"a": [category, series],
    "b": [category, series], "p": value}``. This form also supports stacked
    and percent-stacked bars; the component name remains visible with its P value.
        直接提供预计算的 P 值。和 ``auto_test``/``pairs`` 互斥。
    ``auto_test``: str, optional
        自动在每个 category 内对 series 做 pairwise 统计检验。
        ``"welch"`` / ``"student"`` / ``"mann_whitney"``。
        必须和 ``pairs`` 一起传。
    ``pairs``: list of (i, j) tuples OR str, optional
        指定每个 category 内要测哪些 series 对。
          - list: 显式传 ``[(0, 1), (0, 2), ...]``
          - ``"all"``: 全组合 C(n_series, 2)
          - ``"sensible"``: 相邻 series + control vs 远（启发式）
        必须和 ``auto_test`` 一起传。
    """
    _variant_is_classic("grouped_bar", variant)
    from ._grouped_adaptive import coerce_series, render_adaptive, validate_nonnegative

    series = coerce_series(list(series))
    options = locals().copy()
    categories = list(categories)
    options.pop("coerce_series", None)
    options.pop("render_adaptive", None)
    options.pop("validate_nonnegative", None)

    cats, names, records = validate_nonnegative(
        categories, series, line_series=line_series, value_domain=value_domain, error_kind=error_kind
    )
    adaptive = render_adaptive(cats, names, records, options)
    if adaptive is not None:
        return adaptive
    from ._categorical import make_categorical, normalize_cell

    extended = (
        orientation != "vertical"
        or stack not in (None, "none")
        or axis_break is not None
        or line_series is not None
        or value_domain is not None
        or any(isinstance(comparison, dict) for comparison in pairwise_p or [])
    )
    extended = (
        extended
        or show_values is True
        or multi_mode in ("single", "off", None)
        or any(isinstance(s, dict) or any(isinstance(v, dict) or v is None for v in s[1]) for s in series)
    )
    if extended:
        if multi_mode not in ("auto", "single", "off", None):
            raise ValueError("extended categorical options require single mode")
        return make_categorical(
            categories,
            series,
            orientation=orientation,
            stack=stack,
            axis_break=axis_break,
            line_series=line_series,
            right_y_unit=right_y_unit,
            right_y_title=right_y_title,
            value_domain=value_domain,
            y_unit=y_unit,
            x_title=x_title,
            y_title=y_title,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            error_kind=error_kind,
            show_points=show_points,
            show_values=show_values,
            pairwise_p=pairwise_p,
            auto_test=auto_test,
            pairs=pairs,
            width=width,
            height=height,
            font_family=font_family,
            palette=palette,
            highlight=highlight_series,
            value_scale=value_scale,
            ci_level=ci_level,
            reference_lines=reference_lines,
        )
    if reference_lines:
        raise ValueError("reference_lines are drawn on bar and interval views; use multi_mode='auto' or 'intervals'")
    series = [(str(name), [normalize_cell(vals, error_kind)["replicates"] for vals in rows]) for name, rows in series]
    if not categories:
        raise ValueError("categories must be non-empty.")
    if not series:
        raise ValueError("series must be non-empty.")
    for i, s in enumerate(series):
        if not s or len(s) != 2:
            raise ValueError(f"series[{i}] must be (name, [[vals_cat1], ...]).")
        name, rows = s
        if len(rows) != len(categories):
            raise ValueError(f"series[{i}] ('{name}') has {len(rows)} rows but {len(categories)} categories.")
        for ci, vals in enumerate(rows):
            if not vals:
                raise ValueError(f"series '{name}' cat[{ci}] has no values.")
    if pairwise_p is not None and (auto_test is not None or pairs is not None):
        raise ValueError("Cannot specify pairwise_p together with auto_test/pairs. Use one API.")
    if auto_test is not None and pairs is None:
        raise ValueError("auto_test requires pairs. Pass pairs=[(i,j), ...] or pairs='all' / 'sensible'.")
    if pairs is not None and auto_test is None:
        raise ValueError("pairs requires auto_test. Pass auto_test='welch' / 'student' / 'mann_whitney'.")
    if auto_test is not None:
        from svg_lib.charts._academic_rigor import _PAIRWISE_TESTS, pairwise_test

        if not isinstance(pairs, (str, list, tuple)):
            raise ValueError("pairs must be list of (i, j) tuples, 'all', or 'sensible'")
        if isinstance(pairs, (list, tuple)) and auto_test not in _PAIRWISE_TESTS:
            raise ValueError(f"auto_test must be one of {list(_PAIRWISE_TESTS)}")
        pairwise_p = []
        for cat_idx in range(len(categories)):
            series_vals_at_cat = [s[1][cat_idx] for s in series]
            if isinstance(pairs, str):
                cat_pairs = pairwise_test(series_vals_at_cat, method=auto_test, pair_strategy=pairs)
            else:
                test_fn = _PAIRWISE_TESTS[auto_test]
                cat_pairs = [(i, j, test_fn(series_vals_at_cat[i], series_vals_at_cat[j])) for (i, j) in pairs]
            for i, j, p in cat_pairs:
                pairwise_p.append((cat_idx, i, j, p))
    if palette is None:
        palette = "archive_ink"
    pal = _resolve_palette(palette)
    body_font, heading_font = _resolve_font(font_family)
    W, H = float(width), float(height)
    n_cat = len(categories)
    n_ser = len(series)
    total_bars = n_cat * n_ser
    # Font sizes keyed to the larger of (categories, series) — the axis-label / legend count that users actually read —
    # not the multiplicative bar count, which shrinks fonts even when each dimension is small.
    fs = _dist_font_sizes(W, H, max(4, max(n_cat, n_ser)))

    ser_colors = _derive_series_colors(pal, n_ser)

    stats_grid = []  # [series_idx][cat_idx] = {mean, err, vals, n}
    for name, rows in series:
        row_stats = []
        for vals in rows:
            m = _mean(vals)
            e = _err_halfwidth(vals, error_kind) if len(vals) >= 2 else None
            row_stats.append({"mean": m, "err": e, "vals": vals, "n": len(vals)})
        stats_grid.append(row_stats)

    all_v = []
    for si in range(n_ser):
        for ci in range(n_cat):
            s = stats_grid[si][ci]
            all_v.extend(s["vals"])
            if s["err"] is not None:
                all_v.append(s["mean"] + s["err"])
                all_v.append(s["mean"] - s["err"])
    y_lo, y_hi = min(all_v), max(all_v)
    headroom = 0.25 if pairwise_p else 0.1
    y_hi = y_hi + (y_hi - y_lo) * headroom
    if y_lo >= 0:
        y_lo = 0.0
    y_ticks, y_min, y_max = rigor.nice_axis(y_lo, y_hi, 5)

    # ``with_facet_by_series`` short-circuits the historic draw path and delegates to the facet renderer.
    _mm_signals = {
        "n_series": n_ser,
        "n_categories": n_cat,
        "series_values": [[list(vals) for vals in rows] for (_, rows) in series],
    }
    _mm_bbox_full = rigor.bbox_from_edges(50, W - 50, 130, H - 150)
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _GROUPED_BAR_MULTI_WHITELIST,
        _mm_signals,
        _mm_bbox_full,
    )
    # Comparisons connect series within one category. Faceting separates those
    # anchors, so auto must retain the shared plot instead of dropping P values.
    if _mm_mode == "with_facet_by_series" and pairwise_p:
        if multi_mode == "with_facet_by_series":
            raise ValueError("pairwise comparisons require a shared grouped plot; use multi_mode='auto'")
        _mm_mode = None
    if _mm_mode == "with_facet_by_series":
        return _render_grouped_bar_facets(
            categories=categories,
            series=series,
            stats_grid=stats_grid,
            pal=pal,
            body_font=body_font,
            heading_font=heading_font,
            fs=fs,
            W=W,
            H=H,
            y_min=y_min,
            y_max=y_max,
            y_ticks=y_ticks,
            y_title=y_title,
            y_unit=y_unit,
            x_title=x_title,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            note=note,
            source=source,
            error_kind=error_kind,
            show_points=show_points,
            highlight_series=highlight_series,
        )

    max_tick_w = 0.0
    span_y = y_max - y_min
    for v in y_ticks:
        s_ = _fmt_axis(v, span_y if span_y > 0 else abs(v) or 1)
        max_tick_w = max(max_tick_w, _estimate_label_width_px(s_, fs["ytick"], font_family=body_font))

    margin_left = max_tick_w + 70
    margin_right = 50
    margin_bot = 150

    # Pre-compute legend wrap row count so margin_top can reserve space for a multi-row legend when many/long series
    # names would otherwise force the single-row legend off-canvas and collide with Y-axis unit chip / title.
    _lg_fs_pre = max(13.0, fs["legend"])
    _swatch_sz_pre = _lg_fs_pre * 1.1
    _unit_tag_pre = f" ({y_unit})" if y_unit else ""
    _item_widths = [
        (_swatch_sz_pre + 8 + _estimate_label_width_px(name + _unit_tag_pre, _lg_fs_pre, font_family=body_font) + 24)
        for (name, _rows) in series
    ]
    _avail_w_pre = (W - margin_right) - margin_left - 4
    _n_legend_rows = 1
    _cur = 0.0
    for _wi in _item_widths:
        if _cur > 0 and _cur + _wi > _avail_w_pre:
            _n_legend_rows += 1
            _cur = 0.0
        _cur += _wi
    _legend_row_h = max(_swatch_sz_pre + 6, _lg_fs_pre * 1.4)
    margin_top = 130 + max(0, _n_legend_rows - 1) * _legend_row_h  # extra: title + legend

    plot_x_left = margin_left
    plot_x_right = W - margin_right
    plot_y_top = margin_top
    plot_y_bot = H - margin_bot

    def Y(v):
        return rigor._lin(v, y_min, y_max, plot_y_bot, plot_y_top)

    plot_w = plot_x_right - plot_x_left
    cat_slot = plot_w / n_cat
    inner_pad = cat_slot * 0.15
    bar_slot = (cat_slot - 2 * inner_pad) / n_ser
    bar_w = bar_slot * 0.78

    cat_centers = [plot_x_left + cat_slot * (i + 0.5) for i in range(n_cat)]

    def bar_center(ci, si):
        left_edge = cat_centers[ci] - cat_slot * 0.5 + inner_pad + bar_slot * 0.5
        return left_edge + si * bar_slot

    parts = rigor.draw_canvas_bg(pal, W, H)

    _title_anchor_y = plot_y_top - 50 - max(0, _n_legend_rows - 1) * _legend_row_h
    parts.append(
        rigor.draw_title_block(
            plot_x_left,
            _title_anchor_y,
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

    # legend (top, right-aligned). Wrap to multiple rows when the one-row total
    # width would overflow the plot area width (otherwise the leftmost swatch /
    # label spills off the viewBox and lint flags text-text / text-shape overlap
    # with the Y-axis unit chip or title block).
    lg_fs = max(13.0, fs["legend"])
    swatch_sz = lg_fs * 1.1
    gap_item = 24
    gap_text = 8
    legend_items = []
    unit_tag = f" ({y_unit})" if y_unit else ""
    for i, (name, _rows) in enumerate(series):
        label_text = _xesc(name) + unit_tag
        tw = _estimate_label_width_px(name + unit_tag, lg_fs, font_family=body_font)
        legend_items.append((name, tw, label_text))
    _single_row_w = sum(swatch_sz + gap_text + tw + gap_item for _, tw, _ in legend_items) - gap_item
    _avail_w = plot_x_right - plot_x_left - 4
    # Pack right-to-left into rows that each fit in _avail_w.
    rows: list[list[tuple[int, str, float, str]]] = [[]]
    _cur_row_w = 0.0
    for i, (name, tw, label_text) in enumerate(legend_items):
        _slot_w = swatch_sz + gap_text + tw + gap_item
        if rows[-1] and _cur_row_w + _slot_w > _avail_w:
            rows.append([])
            _cur_row_w = 0.0
        rows[-1].append((i, name, tw, label_text))
        _cur_row_w += _slot_w
    # Row 0 is the topmost (nearest to title block). The last row sits closest
    # to the plot top. Draw each row right-aligned at plot_x_right.
    n_rows = len(rows)
    row_h = max(swatch_sz + 6, lg_fs * 1.4)
    # Bottom-most legend row baseline: plot_y_top - 25 (same as before when 1 row).
    _bottom_row_y = plot_y_top - 25
    for ri, row in enumerate(rows):
        row_tot_w = sum(swatch_sz + gap_text + tw + gap_item for _, _, tw, _ in row) - gap_item
        row_lg_x = plot_x_right - row_tot_w
        row_lg_y = _bottom_row_y - (n_rows - 1 - ri) * row_h
        cx = row_lg_x
        for i, name, tw, label_text in row:
            col = ser_colors[i]
            parts.append(
                f'<rect x="{cx:.1f}" y="{row_lg_y - swatch_sz:.1f}" '
                f'width="{swatch_sz:.1f}" height="{swatch_sz:.1f}" '
                f'fill="{_rgb_prefix(col)}0.55)" stroke="{col}" stroke-width="1.4"/>'
            )
            parts.append(
                f'<text x="{cx + swatch_sz + gap_text:.1f}" y="{row_lg_y - swatch_sz * 0.1:.1f}" '
                f'font-size="{lg_fs:.1f}" fill="{pal["ink"]}">{label_text}</text>'
            )
            cx += swatch_sz + gap_text + tw + gap_item

    parts.append(
        rigor.draw_grid(
            plot_x_left,
            plot_x_right,
            plot_y_top,
            plot_y_bot,
            pal=pal,
            y_ticks=y_ticks,
            y_min=y_min,
            y_max=y_max,
            orient="horizontal",
        )
    )

    y_zero = Y(max(0.0, y_min))
    for si in range(n_ser):
        is_hi = highlight_series is not None and series[si][0] == highlight_series
        col = ser_colors[si]
        for ci in range(n_cat):
            s = stats_grid[si][ci]
            bx = bar_center(ci, si)
            top_y = Y(s["mean"])
            bot_y = y_zero
            if top_y > bot_y:
                top_y, bot_y = bot_y, top_y
            alpha = 0.72 if is_hi else 0.52
            parts.append(
                f'<rect x="{bx - bar_w / 2:.2f}" y="{top_y:.2f}" '
                f'width="{bar_w:.2f}" height="{(bot_y - top_y):.2f}" '
                f'fill="{_rgb_prefix(col)}{alpha})" stroke="{col}" stroke-width="1.3"/>'
            )

    if show_points:
        for si in range(n_ser):
            col = ser_colors[si]
            for ci in range(n_cat):
                s = stats_grid[si][ci]
                bx = bar_center(ci, si)
                ys_px = [Y(v) for v in s["vals"]]
                parts.append(
                    rigor.draw_jittered_points(
                        bx,
                        ys_px,
                        bar_w,
                        pal=pal,
                        seed=si * 83 + ci * 29,
                        r=max(1.6, 2.4 - 0.01 * total_bars),
                        alpha=0.75,
                        color=pal["ink"],
                    )
                )

    for si in range(n_ser):
        for ci in range(n_cat):
            s = stats_grid[si][ci]
            if s["err"] is None:
                continue
            bx = bar_center(ci, si)
            cy = Y(s["mean"])
            err_up_px = abs(Y(s["mean"] + s["err"]) - cy)
            err_dn_px = abs(Y(s["mean"] - s["err"]) - cy)
            parts.append(
                rigor.draw_error_bar(
                    bx,
                    cy,
                    err_up_px,
                    err_dn_px,
                    pal=pal,
                    kind=error_kind,
                    width=min(bar_w * 0.6, 14),
                    color=pal["ink"],
                    stroke_w=1.4,
                )
            )

    parts.append(
        rigor.draw_y_axis(
            plot_x_left,
            plot_y_top,
            plot_y_bot,
            y_ticks,
            y_min,
            y_max,
            unit=y_unit,
            pal=pal,
            fs_tick=fs["ytick"],
            fs_title=fs["yaxis"],
            title=y_title,
            side="left",
        )
    )
    parts.append(
        f'<line x1="{plot_x_left:.1f}" y1="{plot_y_bot:.1f}" x2="{plot_x_right:.1f}" y2="{plot_y_bot:.1f}" '
        f'stroke="{pal["ink"]}" stroke-width="1.2"/>'
    )
    for ci, name in enumerate(categories):
        cx_ = cat_centers[ci]
        parts.append(
            f'<line x1="{cx_:.1f}" y1="{plot_y_bot:.1f}" x2="{cx_:.1f}" y2="{plot_y_bot + 5:.1f}" '
            f'stroke="{pal["ink"]}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{cx_:.1f}" y="{plot_y_bot + fs["group"] + 10:.1f}" '
            f'font-size="{fs["group"]:.1f}" fill="{pal["ink"]}" text-anchor="middle" '
            f'font-weight="600">{_xesc(name)}</text>'
        )
        # Replicate counts belong to each series, never to a pooled category.
        counts = [stats_grid[si][ci]["n"] for si in range(n_ser)]
        count_text = f"n = {counts[0]} each" if len(set(counts)) == 1 else "n = " + "/".join(map(str, counts))
        parts.append(
            f'<text x="{cx_:.1f}" y="{plot_y_bot + fs["group"] + fs["group_n"] + 18:.1f}" '
            f'font-size="{fs["group_n"]:.1f}" fill="{pal["ink"]}" text-anchor="middle">{_xesc(count_text)}</text>'
        )

    if x_title:
        xc = (plot_x_left + plot_x_right) * 0.5
        xt_y = plot_y_bot + fs["group"] + fs["group_n"] + 46
        parts.append(
            f'<text x="{xc:.1f}" y="{xt_y:.1f}" font-size="{fs["yaxis"]:.1f}" '
            f'fill="{pal["ink"]}" text-anchor="middle" font-weight="600">{_xesc(x_title)}</text>'
        )

    parts.append(
        f'<text x="{plot_x_left + 4:.1f}" y="{plot_y_top + fs["label"]:.1f}" '
        f'font-size="{fs["label"]:.1f}" fill="{pal["ink6"]}" font-style="italic">'
        f"{_xesc(_uncertainty_note(stats_grid, error_kind))}</text>"
    )

    if pairwise_p:
        # group by cat and sort by span
        sorted_sig = sorted(pairwise_p, key=lambda t: abs(t[1] - t[2]))
        used = {}  # ci -> list of (xa, xb, y_base)
        for cat_i, a, b, p in sorted_sig:
            if cat_i < 0 or cat_i >= n_cat:
                continue
            if a < 0 or b < 0 or a >= n_ser or b >= n_ser or a == b:
                continue
            ca = bar_center(cat_i, min(a, b))
            cb = bar_center(cat_i, max(a, b))
            sa = stats_grid[min(a, b)][cat_i]
            sb = stats_grid[max(a, b)][cat_i]
            top_a = Y(max(sa["mean"] + sa["err"], *sa["vals"]))
            top_b = Y(max(sb["mean"] + sb["err"], *sb["vals"]))
            base = min(top_a, top_b) - 18
            for u_xa, u_xb, u_y in used.get(cat_i, []):
                if not (cb < u_xa - 4 or ca > u_xb + 4):
                    base = min(base, u_y - 24)
            # Journal format: star + explicit P-value for scannable brackets.
            if isinstance(p, str):
                from ._chart_layout import parse_p

                p = parse_p(p)
            if p is None or math.isnan(p):  # NaN check
                label_text = "ns"
            else:
                from ._chart_layout import p_label

                text = p_label(p)
                stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                label_text = text if text == "ns" else f"ns ({text})" if stars == "ns" else f"{stars} {text}"
            parts.append(
                rigor.draw_sig_bracket(
                    ca,
                    cb,
                    base,
                    label_text,
                    pal=pal,
                    fs=fs["label"],
                    tick_h=5,
                    color=pal["ink"],
                )
            )
            used.setdefault(cat_i, []).append((ca, cb, base))

    parts.append(rigor.draw_footer(note, source, pal, fs, plot_x_left, plot_x_right, H - 20))

    return rigor.wrap_svg(parts, W, H, body_font)


# with_facet_by_series: one facet per series, shared Y, shared series colors
def _render_grouped_bar_facets(
    *,
    categories,
    series,
    stats_grid,
    pal,
    body_font,
    heading_font,
    fs,
    W,
    H,
    y_min,
    y_max,
    y_ticks,
    y_title,
    y_unit,
    x_title,
    title,
    subtitle,
    figure_label,
    note,
    source,
    error_kind,
    show_points,
    highlight_series,
):
    """Facet-grid renderer: one bar chart per series, cells arranged in a grid."""
    n_ser = len(series)
    n_cat = len(categories)

    shared_y = rigor.SharedScale(domain=(y_min, y_max), ticks=y_ticks, transform="linear")
    series_names = [name for name, _ in series]
    ctx = rigor.SeriesContext(ids=series_names, pal=pal)

    # Canvas margins (reserve for title block + legend + footer)
    margin_top = 130
    margin_bot = 110
    margin_left = 50
    margin_right = 50

    full_bbox = rigor.bbox_from_edges(
        margin_left,
        W - margin_right,
        margin_top,
        H - margin_bot,
    )
    # Choose cols for a roughly square grid rather than 1×n (which leaves wide
    # vertical whitespace) or n×1. 4 series must map to 2×2 (not 3+1).
    if n_ser <= 2:
        cols = n_ser
    elif n_ser <= 4:
        cols = 2
    elif n_ser <= 9:
        cols = 3
    else:
        cols = math.ceil(math.sqrt(n_ser))
    try:
        cells = rigor.allocate_facet_grid(full_bbox, n=n_ser, cols=cols, gutter=28.0)
    except rigor.LayoutError:
        cells = rigor.allocate_facet_grid(
            full_bbox,
            n=n_ser,
            cols=cols,
            gutter=20.0,
            min_cell=(140.0, 110.0),
        )

    ink = pal["ink"]
    ink6 = pal["ink6"]
    parts = rigor.draw_canvas_bg(pal, W, H)

    parts.append(
        rigor.draw_title_block(
            margin_left,
            margin_top - 50,
            W - margin_left - margin_right,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            pal=pal,
            fs=fs,
            body_font=body_font,
            heading_font=heading_font,
        )
    )

    facet_title_fs = max(12.0, fs["label"] * 1.1)
    tick_fs = max(10.0, fs["ytick"] * 0.9)
    cat_label_fs = max(9.0, fs["group"] * 0.85)

    for si, (sname, rows) in enumerate(series):
        cell = cells[si]
        c_x0, c_y0, c_x1, c_y1 = cell.x0, cell.y0, cell.x1, cell.y1
        # Facet local margins. The top margin must clear:
        #   (a) the facet title (baseline at c_y0 + facet_title_fs), and
        #   (b) the Y-axis unit chip, which sits above plot_y_top by about
        #       fs_tick*0.55 + unit_fs*0.8 + 4 px (chip baseline + ascent).
        # Previously f_margin_top was `facet_title_fs + 8` which left the
        # unit-chip bbox overlapping the facet title bbox when both were
        # emitted on leftmost-column facets. Reserve extra tick-space so the
        # chip's ascender clears the facet title descender.
        _unit_chip_fs = min(14.0, max(11.0, tick_fs * 0.7))
        _unit_clearance = tick_fs * 0.55 + _unit_chip_fs * 0.9 + 6
        title_lines = _wrap_label(sname, c_x1 - c_x0 - 12, facet_title_fs, body_font, bold=True)
        title_height = (
            max(len(_wrap_label(name, c_x1 - c_x0 - 12, facet_title_fs, body_font, bold=True)) for name, _ in series)
            * facet_title_fs
            * 1.25
        )
        # The highest tick projects above the plot even without a unit chip.
        f_margin_top = title_height + tick_fs + 12 + (_unit_clearance if y_unit else 0)
        category_lines = [
            _wrap_label(cname, (c_x1 - c_x0 - 54) / n_cat - 12, cat_label_fs, body_font) for cname in categories
        ]
        f_margin_bot = max(map(len, category_lines)) * cat_label_fs * 1.25 + 18
        f_margin_left = 44
        f_margin_right = 10
        plot_x_left = c_x0 + f_margin_left
        plot_x_right = c_x1 - f_margin_right
        plot_y_top = c_y0 + f_margin_top
        plot_y_bot = c_y1 - f_margin_bot

        for line_i, label in enumerate(title_lines):
            parts.append(
                f'<text x="{c_x0 + 4:.1f}" y="{c_y0 + facet_title_fs * (1 + line_i * 1.25):.1f}" '
                f'font-size="{facet_title_fs:.1f}" fill="{ink}" '
                f'font-weight="600">{_xesc(label)}</text>'
            )

        def Y(v, pt=plot_y_top, pb=plot_y_bot):
            return shared_y.map(v, pb, pt)

        parts.append(
            rigor.draw_grid(
                plot_x_left,
                plot_x_right,
                plot_y_top,
                plot_y_bot,
                pal=pal,
                y_ticks=y_ticks,
                y_min=y_min,
                y_max=y_max,
                orient="horizontal",
            )
        )

        plot_w = plot_x_right - plot_x_left
        slot_w = plot_w / n_cat
        bar_w = min(slot_w * 0.65, 60)
        cat_centers = [plot_x_left + slot_w * (ci + 0.5) for ci in range(n_cat)]

        col = ctx.color_of(sname)
        is_hi = highlight_series is not None and sname == highlight_series
        alpha = 0.72 if is_hi else 0.52

        y_zero = Y(max(0.0, y_min))

        for ci in range(n_cat):
            s = stats_grid[si][ci]
            bx = cat_centers[ci]
            top_y = Y(s["mean"])
            bot_y = y_zero
            if top_y > bot_y:
                top_y, bot_y = bot_y, top_y
            parts.append(
                f'<rect x="{bx - bar_w / 2:.2f}" y="{top_y:.2f}" '
                f'width="{bar_w:.2f}" height="{(bot_y - top_y):.2f}" '
                f'fill="{_rgb_prefix(col)}{alpha})" stroke="{col}" stroke-width="1.3"/>'
            )

        if show_points:
            for ci in range(n_cat):
                s = stats_grid[si][ci]
                bx = cat_centers[ci]
                ys_px = [Y(v) for v in s["vals"]]
                parts.append(
                    rigor.draw_jittered_points(
                        bx,
                        ys_px,
                        bar_w,
                        pal=pal,
                        seed=si * 83 + ci * 29,
                        r=1.8,
                        alpha=0.75,
                        color=pal["ink"],
                    )
                )

        for ci in range(n_cat):
            s = stats_grid[si][ci]
            if s["err"] is None:
                continue
            bx = cat_centers[ci]
            cy_px = Y(s["mean"])
            err_up_px = abs(Y(s["mean"] + s["err"]) - cy_px)
            err_dn_px = abs(Y(s["mean"] - s["err"]) - cy_px)
            parts.append(
                rigor.draw_error_bar(
                    bx,
                    cy_px,
                    err_up_px,
                    err_dn_px,
                    pal=pal,
                    kind=error_kind,
                    width=min(bar_w * 0.5, 10),
                    color=pal["ink"],
                    stroke_w=1.2,
                )
            )

        # Y axis (left side of facet, only show title on leftmost column facets)
        _show_y_title = si % cols == 0
        parts.append(
            rigor.draw_y_axis(
                plot_x_left,
                plot_y_top,
                plot_y_bot,
                y_ticks,
                y_min,
                y_max,
                unit=y_unit if _show_y_title else "",
                pal=pal,
                fs_tick=tick_fs,
                fs_title=tick_fs * 1.1,
                title=y_title if _show_y_title else None,
                side="left",
            )
        )
        parts.append(
            f'<line x1="{plot_x_left:.1f}" y1="{plot_y_bot:.1f}" x2="{plot_x_right:.1f}" y2="{plot_y_bot:.1f}" '
            f'stroke="{ink}" stroke-width="1.0"/>'
        )
        for ci, cname in enumerate(categories):
            cx_ = cat_centers[ci]
            parts.append(
                f'<line x1="{cx_:.1f}" y1="{plot_y_bot:.1f}" x2="{cx_:.1f}" y2="{plot_y_bot + 4:.1f}" '
                f'stroke="{ink}" stroke-width="0.8"/>'
            )
            for line_i, label in enumerate(category_lines[ci]):
                parts.append(
                    f'<text x="{cx_:.1f}" y="{plot_y_bot + cat_label_fs * (1 + line_i * 1.25) + 6:.1f}" '
                    f'font-size="{cat_label_fs:.1f}" fill="{ink}" text-anchor="middle" '
                    f'font-weight="500">{_xesc(label)}</text>'
                )

    # Shared x_title under the facet grid (centered)
    if x_title:
        xc = (margin_left + W - margin_right) * 0.5
        xt_y = H - margin_bot + 36
        parts.append(
            f'<text x="{xc:.1f}" y="{xt_y:.1f}" font-size="{fs["yaxis"]:.1f}" '
            f'fill="{ink}" text-anchor="middle" font-weight="600">{_xesc(x_title)}</text>'
        )

    parts.append(
        f'<text x="{margin_left + 4:.1f}" y="{margin_top - 8:.1f}" '
        f'font-size="{fs["label"]:.1f}" fill="{ink6}" font-style="italic">'
        f"{_xesc(_uncertainty_note(stats_grid, error_kind) + ' · faceted by series')}</text>"
    )

    foot_fs = max(13.0, fs["foot"])
    foot_y = H - 20
    parts.append(
        rigor.draw_note_source(
            note,
            source,
            x_left=margin_left,
            x_right=W - margin_right,
            y=foot_y,
            fs=foot_fs,
            color=ink6,
        )
    )

    return rigor.wrap_svg(parts, W, H, body_font)


def _uncertainty_note(stats_grid, error_kind):
    cells = [cell for series in stats_grid for cell in series]
    defined = sum(cell["err"] is not None for cell in cells)
    if not defined:
        return tr("Individual observations; uncertainty unavailable (n = 1 per series)")
    if defined < len(cells):
        return tr("Error bars: {kind} where n ≥ 2; unavailable for n = 1", kind=error_kind)
    return tr("Error bars: {kind} · n per series", kind=error_kind)
