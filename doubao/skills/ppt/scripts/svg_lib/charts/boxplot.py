"""svg_lib/charts/boxplot.py

Productized boxplot with 5 variants:
  * default_flat            — baseline (make_boxplot)
  * beeswarm                — dots binned by y-position
  * notched_outlined        — notch polygon + outlined skin
  * variable_width_gradient — width ∝ √n + gradient skin
  * strip_flat              — pure vertical dot strip

All 5 variants consume the same `data` schema:
    data = {
        "groups": [(name, [values]), ...],
        "unit": str = "",
        "highlight_name": str | None,
    }
"""
from __future__ import annotations
import math
import re

from .._baseline import make_boxplot  # type: ignore
from .._boxplot_skin import _boxplot_skeleton_overlay, apply_skin  # type: ignore

from ._shared import (
    auto_font_size,
    resolve_palette,  # noqa: F401 (kept for parity / external re-use)
)
from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)


VARIANTS = (
    "default_flat",
    "beeswarm",
    "notched_outlined",
    "variable_width_gradient",
    "strip_flat",
)


# ------------------------------------------------------------------
# Overlap dedupe: the validator flags `embed_svg_bbox_overlap` when
# two <circle> primitives share the same visual bounding box (within
# 0.001, see embed_svg_validator.detect_embedded_svg_overlaps).
#
# For `strip_flat` (r=2.1 strip dots) and `notched_outlined` (r=2.4
# outlier rings inherited from the baseline) two samples can land on
# the same rounded coordinate. `notched_outlined` is a clean outline
# style — outlier duplication is a defect, not a design choice — so we
# drop the redundant circles here.
#
# beeswarm is intentionally exempt from this cleanup: dense bee-swarm
# stacks legitimately share coordinates by design.
# ------------------------------------------------------------------
_CIRCLE_RE = re.compile(r'<circle\b[^>]*/>')
_ATTR_RE = re.compile(r'(cx|cy|r)="([^"]+)"')


def _dedupe_svg_circles(svg: str, coord_epsilon: float = 0.05) -> str:
    """Remove <circle .../> tags whose (cx, cy, r) collide with an earlier
    circle within `coord_epsilon`. Only exact-coordinate duplicates trip the
    validator, but we bin at 0.05 to tolerate float formatting jitter."""
    seen = set()
    out = []
    last = 0
    for m in _CIRCLE_RE.finditer(svg):
        attrs = dict(_ATTR_RE.findall(m.group(0)))
        try:
            cx = float(attrs["cx"]); cy = float(attrs["cy"]); rr = float(attrs["r"])
        except (KeyError, ValueError):
            continue
        # Bin coordinates so tiny formatting differences still collide. Use
        # radius as an additional bucket key so we don't merge distinct dot
        # layers (halo r+4 vs fill r vs r=1.6 center pip on quadrant dots).
        key = (round(cx / coord_epsilon), round(cy / coord_epsilon), round(rr, 2))
        if key in seen:
            # skip this circle entirely
            out.append(svg[last:m.start()])
            last = m.end()
        else:
            seen.add(key)
    out.append(svg[last:])
    return "".join(out)


def _validate_data(data):
    if not isinstance(data, dict):
        raise TypeError(f"boxplot data must be dict, got {type(data).__name__}")
    groups = data.get("groups")
    if not groups:
        raise ValueError("boxplot data.groups is required and non-empty")
    normed = []
    for i, g in enumerate(groups):
        if not (isinstance(g, (tuple, list)) and len(g) >= 2):
            raise ValueError(f"boxplot group[{i}] must be (name, [values])")
        name, values = g[0], g[1]
        if not values:
            raise ValueError(f"boxplot group[{i}] '{name}' has empty values")
        # coerce numbers, strip NaN/inf
        vs = []
        for v in values:
            try:
                fv = float(v)
            except Exception:
                continue
            if fv != fv or fv in (float("inf"), -float("inf")):
                continue
            vs.append(fv)
        if not vs:
            raise ValueError(f"boxplot group[{i}] '{name}' has no valid numeric values")
        normed.append((str(name), vs))
    return normed


def draw_boxplot(
    data: dict,
    variant: str = "default_flat",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
    y_axis_label: str = None,
    figure_label: str = None,
    note: str = None,
    source: str = None,
) -> str:
    """Return a complete SVG string for a boxplot chart.

    variant ∈ VARIANTS. Falls back to `default_flat` for unknown variants
    with an assertion so tests catch typos.
    """
    if variant not in VARIANTS:
        raise ValueError(
            f"unknown boxplot variant {variant!r}; expected one of {VARIANTS}"
        )
    groups = _validate_data(data)
    unit = data.get("unit", "") or ""
    highlight = data.get("highlight_name")

    n_groups = len(groups)
    fs_base = auto_font_size(n_groups, base=12, min_size=8, max_size=16)

    baseline_kw = dict(
        y_unit=unit,
        title=title,
        subtitle=subtitle,
        figure_label=figure_label,
        y_title=y_axis_label,
        note=note,
        source=source,
        width=float(width),
        height=float(height),
        palette=palette,
        highlight_group=highlight,
    )
    # font_size auto-scales inside make_boxplot from plot_w/col_w; leave it be.

    # ------------------------------------------------------------------
    # 1. default_flat — baseline only.
    # ------------------------------------------------------------------
    if variant == "default_flat":
        return make_boxplot(groups=groups, **baseline_kw)

    # ------------------------------------------------------------------
    # 2-5. skeleton overlay variants. The overlay helper computes overlay
    # geometry using a fixed 1200x620 layout of make_boxplot; margins are
    # computed here to match make_boxplot's actual layout choices (they
    # depend on presence of title/note/source).
    # ------------------------------------------------------------------
    overlay_kw = dict(baseline_kw)
    overlay_kw["width"] = 1200.0
    overlay_kw["height"] = 620.0

    # Mirror make_boxplot's margin logic EXACTLY. MARGIN_B in the baseline
    # scales with fs_group / fs_group_n (3 label rows: name + n + Mdn), so
    # if we use the old hard-coded 65/100 here the overlay's y-scale will
    # extend beyond the baseline's actual plot region and the lowest
    # beeswarm/strip dots collide with the group name label
    # (embed_svg_text_shape_overlap).
    from .._common import _dist_font_sizes
    _fs_overlay = _dist_font_sizes(1200.0, 620.0, n_groups)
    _fs_group   = _fs_overlay["group"]
    _fs_group_n = _fs_overlay["group_n"]
    _labels_h = max(
        50.0,
        _fs_group * 1.15 + _fs_group * 1.15 + _fs_group_n * 1.25 + _fs_group_n,
    )
    margin_l = 110
    margin_r = 60
    margin_t = 130 if title else 60
    margin_b = (
        max(100.0, _labels_h + 30.0)
        if (note or source)
        else max(65.0, _labels_h + 8.0)
    )
    overlay_geo = dict(
        width=1200.0, height=620.0,
        margin_l=margin_l, margin_r=margin_r,
        margin_t=margin_t, margin_b=margin_b,
    )

    if variant == "beeswarm":
        svg = make_boxplot(groups=groups, **overlay_kw)
        return _boxplot_skeleton_overlay(svg, groups, palette, "beeswarm", **overlay_geo)

    if variant == "notched_outlined":
        svg = make_boxplot(groups=groups, **overlay_kw)
        svg = _boxplot_skeleton_overlay(svg, groups, palette, "notched", **overlay_geo)
        svg = apply_skin(svg, "outlined", "bp_notched")
        return _dedupe_svg_circles(svg)

    if variant == "variable_width_gradient":
        svg = make_boxplot(groups=groups, **overlay_kw)
        svg = _boxplot_skeleton_overlay(svg, groups, palette, "variable_width", **overlay_geo)
        svg = apply_skin(svg, "gradient", "bp_vw")
        return _dedupe_svg_circles(svg)

    if variant == "strip_flat":
        svg = make_boxplot(groups=groups, **overlay_kw)
        svg = _boxplot_skeleton_overlay(svg, groups, palette, "strip", **overlay_geo)
        return _dedupe_svg_circles(svg)

    # unreachable
    raise ValueError(f"unhandled variant {variant!r}")


def make_boxplot(groups,
                 y_unit: str = "",
                 highlight_group: str = None,
                 y_min: float = None,
                 y_max: float = None,
                 title: str = None,
                 subtitle: str = None,
                 figure_label: str = None,
                 y_title: str = None,
                 note: str = None,
                 source: str = None,
                 show_legend: bool = True,
                 show_jitter: bool = True,
                 show_mean: bool = True,
                 width: float = 1200,
                 height: float = None,
                 font_family: str = None,
                 palette=None,
                 variant: str = None) -> str:
    """
    箱线图（Dandelion academic 风格）。

    groups: [(name, [values...]), ...] N 组样本（每组建议 ≥ 5 个）
    y_unit: Y 轴刻度后缀（"%" / "ms" / "$" 等）
    highlight_group: 组名，该组箱体额外描边加粗
    y_min / y_max: 显式 Y 轴范围；缺省用数据 min/max 外扩 10%
    title/subtitle/figure_label: 顶部
    y_title: Y 轴竖排标题
    note/source: 底部脚注

    show_legend: 顶部右侧图例（Q1-Q3/Median/Mean/Whisker/Outlier 4 项）
    show_jitter: 抖动散点背景层
    show_mean: 均值空心圆

    variant: 若指定为 svg_lib 骨架变体（default_flat / beeswarm /
             notched_outlined / variable_width_gradient / strip_flat），
             改走 svg_lib.charts.boxplot.draw_boxplot；None/"classic" 走原本设计。
    """
    if not _variant_is_classic("boxplot", variant):
        data = {"groups": list(groups), "unit": y_unit or ""}
        if highlight_group is not None:
            data["highlight_name"] = highlight_group
        return _dispatch_to_svg_lib(
            "boxplot", variant, data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
            width=width, height=height,
        )

    if not groups:
        raise ValueError("boxplot: at least one group required")
    for i, g in enumerate(groups):
        if len(g) < 2 or not g[1]:
            raise ValueError(f"boxplot: group[{i}] needs (name, [values...]) with non-empty values")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(250,248,242,1)"
    GRID = _rgba_with_alpha(_INK, 0.06)
    GRIDMAJ = _rgba_with_alpha(_INK, 0.14)

    # 派生每组类别色（用 palette.series 或 accent 派生）
    series_colors = _derive_series_colors(_pal, len(groups), mode="distinct")

    # 计算 stats
    def quantile(sxs, q):
        n = len(sxs)
        if n == 0: return 0
        pos = q * (n - 1)
        lo = int(pos); hi = min(int(pos) + 1, n - 1)
        frac = pos - lo
        return sxs[lo] * (1 - frac) + sxs[hi] * frac

    stats = []
    all_values = []
    for name, values in groups:
        xs = sorted(float(v) for v in values)
        q1 = quantile(xs, 0.25)
        q2 = quantile(xs, 0.50)
        q3 = quantile(xs, 0.75)
        iqr = q3 - q1
        lo_w = max(min(xs), q1 - 1.5 * iqr)
        hi_w = min(max(xs), q3 + 1.5 * iqr)
        mean_v = sum(xs) / len(xs)
        outliers = [x for x in xs if x < lo_w - 1e-9 or x > hi_w + 1e-9]
        inliers = [x for x in xs if lo_w - 1e-9 <= x <= hi_w + 1e-9]
        stats.append(dict(name=str(name), xs=xs, q1=q1, q2=q2, q3=q3,
                          lo=lo_w, hi=hi_w, mean=mean_v,
                          outliers=outliers, inliers=inliers, n=len(xs)))
        all_values.extend(xs)

    # Y 范围
    d_min = min(all_values); d_max = max(all_values)
    span = d_max - d_min
    if y_min is None: y_min = d_min - span * 0.1
    if y_max is None: y_max = d_max + span * 0.1
    if y_unit == "%":
        # 仅当数据真的落在问卷类 [0,100] 范围时才收敛；金融日收益率、变化率等
        # 百分比数据可以为负或超过 100，clamp 会把有效数据点画到 viewBox 外。
        if d_min >= 0 and d_max <= 100:
            y_min = max(0, y_min); y_max = min(100, y_max)

    # 画布
    # height 缺省 None：按内容自适应（620 比原 720 少 100px 底部留白）
    if height is None:
        height = 620
    n_groups = len(groups)

    # ---- 字号自适应（先算：MARGIN_B 需要 fs_group 决定底部 3 行 label 高度）----
    # SVG 字号相对 viewBox；slide 400px embed 缩放后视觉字号缩到 1/3，
    # 所以基准要拉到短边 2.4%（W=1200,H=620 → base ≈ 14.9pt），保证可读。
    from .._common import _dist_font_sizes
    _fs = _dist_font_sizes(width, height, n_groups)
    fs_title    = _fs["title"]
    fs_subtitle = _fs["subtitle"]
    fs_figure   = _fs["figure"]
    fs_ytick    = _fs["ytick"]
    fs_yaxis    = _fs["yaxis"]
    fs_group    = _fs["group"]
    fs_group_n  = _fs["group_n"]
    fs_foot     = _fs["foot"]
    fs_legend   = _fs["legend"]

    MARGIN_L = 110
    MARGIN_R = 60
    MARGIN_T = 130 if title else 60
    # legend 在顶部（y=76 或 112），不影响 MARGIN_B。
    # 底部 3 行 label（name + n + Mdn）随字号动态放大 → MARGIN_B 也跟着大。
    _labels_h = max(50.0, fs_group * 1.15 + fs_group * 1.15 + fs_group_n * 1.25 + fs_group_n)
    # note/source 区（若存在）：divider gap + divider + note + source
    _footer_gap = max(20.0, fs_group_n)  # labels 末行到 note 分割线的安全间距
    _note_block_h = 0.0
    if note or source:
        _note_block_h = _footer_gap + 14.0
        _note_block_h += (fs_foot + 6.0) if note else 0.0
        _note_block_h += (fs_foot + 6.0) if source else 0.0
    MARGIN_B = max(100.0, _labels_h + _note_block_h + 8.0) if (note or source) else max(65.0, _labels_h + 8.0)
    plot_x = MARGIN_L
    plot_w = width - MARGIN_L - MARGIN_R
    plot_y = MARGIN_T
    plot_h = height - MARGIN_T - MARGIN_B

    # 底部 note/source 位置：随 labels 末行动态放，避免与 "Mdn X.XXs" 横向重叠
    _labels_end_y = (plot_y + plot_h) + _labels_h  # 最后一行 Mdn bbox 底部
    _foot_divider_y = _labels_end_y + _footer_gap
    _foot_note_y = _foot_divider_y + max(14.0, fs_foot)
    _foot_source_y = _foot_note_y + (fs_foot + 6.0 if note else 0.0)

    def y_to_px(v):
        return plot_y + (y_max - v) / max(y_max - y_min, 1e-9) * plot_h

    col_w = plot_w / n_groups
    box_w = col_w * 0.36

    def col_center(i):
        return plot_x + col_w * (i + 0.5)

    parts = []
    if c_bg:
        parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')

    # 顶部
    # 顶部标题 y 位置跟字号联动
    _y_title    = 20 + fs_title
    _y_subtitle = _y_title + fs_title * 0.55 + fs_subtitle
    _y_line     = _y_subtitle + 12
    _y_figure   = _y_line + 14 + fs_figure * 0.5
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_title:.1f}" '
                     f'font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_subtitle:.1f}" '
                     f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
        parts.append(f'<line x1="{MARGIN_L}" y1="{_y_line:.1f}" x2="{width-MARGIN_R}" y2="{_y_line:.1f}" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        lbl_w = max(72, len(figure_label) * 8 + 20)
        note_txt = f"Boxplot · {n_groups} groups"
        parts.append(f'<text x="{MARGIN_L+lbl_w}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" letter-spacing=".04em">{_xesc(note_txt)}</text>')

    # Y 网格 + 刻度（nice-number）
    def _nice_step(span, target=6):
        raw = span / target
        mag = 10 ** math.floor(math.log10(max(raw, 1e-9)))
        for nice in (1, 2, 2.5, 5, 10):
            if raw / mag <= nice:
                return nice * mag
        return 10 * mag
    step = _nice_step(y_max - y_min)
    y_ticks = []
    t = math.ceil(y_min / step) * step
    while t <= y_max + 1e-9:
        y_ticks.append(t); t += step

    for yv in y_ticks:
        py = y_to_px(yv)
        # major grid line at every 2 ticks
        is_major = ((yv / step) % 2) < 1e-6 if step > 0 else False
        stroke = GRIDMAJ if is_major else GRID
        parts.append(f'<line x1="{plot_x}" y1="{py:.1f}" x2="{plot_x+plot_w}" y2="{py:.1f}" '
                     f'stroke="{stroke}" stroke-width="1"/>')
        parts.append(f'<line x1="{plot_x-4}" y1="{py:.1f}" x2="{plot_x}" y2="{py:.1f}" '
                     f'stroke="{c_muted}" stroke-width="0.8"/>')
        label = f"{yv:g}{y_unit}" if y_unit else f"{yv:g}"
        parts.append(f'<text x="{plot_x-10}" y="{py+3.5:.1f}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{fs_ytick}" fill="{_INK}">'
                     f'{_xesc(label)}</text>')

    # Y 轴 title
    if y_title:
        ytx = plot_x - 70
        yty = plot_y + plot_h / 2
        parts.append(f'<text x="{ytx}" y="{yty}" transform="rotate(-90 {ytx} {yty})" '
                     f'text-anchor="middle" font-family="{_body_font}" font-size="{fs_yaxis}" '
                     f'fill="{_INK}" font-weight="500">{_xesc(y_title)}</text>')

    # 每个箱
    import random as _rand
    _rand_seed = _rand.Random(4)  # 稳定 jitter
    for i, s in enumerate(stats):
        cx = col_center(i)
        x_left = cx - box_w / 2
        x_right = cx + box_w / 2
        col = series_colors[i]
        # 半透明填色
        r, g, b = _rgb_tuple(col)
        col_fill = f"rgba({r},{g},{b},0.22)"

        # 1) 抖动散点
        if show_jitter:
            for v in s["inliers"]:
                jx = cx + _rand_seed.uniform(-box_w * 0.65, box_w * 0.65)
                py = y_to_px(v)
                parts.append(f'<circle cx="{jx:.1f}" cy="{py:.1f}" r="1.7" '
                             f'fill="rgba({r},{g},{b},0.35)" stroke="rgba({r},{g},{b},0.6)" stroke-width="0.4"/>')

        # 2) whiskers
        y_hi = y_to_px(s["hi"]); y_lo = y_to_px(s["lo"])
        y_q3 = y_to_px(s["q3"]); y_q1 = y_to_px(s["q1"])
        parts.append(f'<line x1="{cx}" y1="{y_hi:.1f}" x2="{cx}" y2="{y_q3:.1f}" '
                     f'stroke="{_INK}" stroke-width="1.1"/>')
        parts.append(f'<line x1="{cx}" y1="{y_q1:.1f}" x2="{cx}" y2="{y_lo:.1f}" '
                     f'stroke="{_INK}" stroke-width="1.1"/>')
        cap_w = box_w * 0.5
        for wy in (s["hi"], s["lo"]):
            py = y_to_px(wy)
            parts.append(f'<line x1="{cx-cap_w/2}" y1="{py:.1f}" x2="{cx+cap_w/2}" y2="{py:.1f}" '
                         f'stroke="{_INK}" stroke-width="1.1"/>')

        # 3) 箱体
        box_stroke_w = 1.8 if s["name"] == highlight_group else 1.2
        parts.append(f'<rect x="{x_left:.1f}" y="{y_q3:.1f}" width="{box_w:.1f}" height="{y_q1-y_q3:.1f}" '
                     f'fill="{col_fill}" stroke="{col}" stroke-width="{box_stroke_w}"/>')

        # 4) 中位线
        y_q2 = y_to_px(s["q2"])
        parts.append(f'<line x1="{x_left:.1f}" y1="{y_q2:.1f}" x2="{x_right:.1f}" y2="{y_q2:.1f}" '
                     f'stroke="{col}" stroke-width="2.2" stroke-linecap="square"/>')

        # 5) 均值：空心圆 + 内点
        if show_mean:
            y_mean = y_to_px(s["mean"])
            parts.append(f'<circle cx="{cx}" cy="{y_mean:.1f}" r="3.2" fill="{PAPER}" '
                         f'stroke="{_INK}" stroke-width="1.2"/>')
            parts.append(f'<circle cx="{cx}" cy="{y_mean:.1f}" r="0.9" fill="{_INK}"/>')

        # 6) outliers
        for v in s["outliers"]:
            py = y_to_px(v)
            parts.append(f'<circle cx="{cx:.1f}" cy="{py:.1f}" r="2.4" fill="none" '
                         f'stroke="{_INK}" stroke-width="1"/>')

        # 7) X 标签（3 行）—— 行距按最大字号 * 1.15 预留
        _gap1 = max(22.0, fs_group * 1.15)      # name → n
        _gap2 = max(17.0, fs_group_n * 1.25)    # n → Mdn
        label_y = plot_y + plot_h + max(22.0, fs_group * 1.15)
        parts.append(f'<text x="{cx:.1f}" y="{label_y}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group}" font-weight="600" '
                     f'fill="{_INK}">{_xesc(s["name"])}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{label_y+_gap1:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group_n}" fill="{c_muted}">'
                     f'n = {s["n"]}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{label_y+_gap1+_gap2:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group_n}" fill="{c_muted}" '
                     f'font-style="italic">Mdn {s["q2"]:.1f}</text>')

    # X 轴基线
    parts.append(f'<line x1="{plot_x}" y1="{plot_y+plot_h}" x2="{plot_x+plot_w}" y2="{plot_y+plot_h}" '
                 f'stroke="{_INK}" stroke-width="1"/>')

    # 图例（顶部右侧内联，"Q1-Q3 · median" 用 sample series[0] 色，其它用 _INK）
    if show_legend:
        if figure_label:
            lg_y = _y_figure
        elif subtitle:
            lg_y = _y_subtitle
        else:
            lg_y = _y_title if title else 40
        lg_x = width - MARGIN_R
        legend_col = series_colors[0]
        lr, lg, lb = _rgb_tuple(legend_col)

        # 4 个图例项从右到左布局
        # 每项：symbol(w px) + gap(6) + label
        items = [
            ("Outlier", 10, "outlier"),
            ("±1.5·IQR whiskers", 14, "whisker"),
            ("Mean", 10, "mean"),
            ("Q1–Q3 · median", 18, "box"),
        ]
        x_cur = lg_x
        for label, sym_w, kind in items:
            # 估算文字宽度：按 validator 侧的每字符宽度上限估算（宽字符 ~0.9em、窄字符 ~0.55em），
            # 再留出足够的 padding，避免 label bbox 与相邻 swatch rect 相交。
            # 之前 5.4px/char 对 'Q1–Q3 · median' 里的 'Q'/'m'/'–'/'·' 估算偏小，会让 swatch
            # rect 挤进 label 实际渲染框，触发 embed_svg_text_shape_overlap。
            wide_chars = set("QOWMmw–·—")
            est_char = sum(0.90 * fs_legend if ch in wide_chars else 0.55 * fs_legend for ch in label)
            txt_w = est_char + fs_legend * 0.8
            x_txt_right = x_cur
            x_txt_left = x_txt_right - txt_w
            # 符号与文字之间保留 gap，随字号 scale
            x_sym = x_txt_left - sym_w - max(10.0, fs_legend * 0.7)
            parts.append(f'<text x="{x_txt_right}" y="{lg_y+3}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_legend}" fill="{c_muted}">'
                         f'{_xesc(label)}</text>')
            sx = x_sym + sym_w / 2
            sy = lg_y
            if kind == "box":
                parts.append(f'<rect x="{sx-7}" y="{sy-4}" width="14" height="8" '
                             f'fill="rgba({lr},{lg},{lb},0.22)" stroke="{legend_col}" stroke-width="1"/>')
                parts.append(f'<line x1="{sx-7}" y1="{sy}" x2="{sx+7}" y2="{sy}" '
                             f'stroke="{legend_col}" stroke-width="1.5"/>')
            elif kind == "mean":
                parts.append(f'<circle cx="{sx}" cy="{sy}" r="3.2" fill="{PAPER}" '
                             f'stroke="{_INK}" stroke-width="1.1"/>')
                parts.append(f'<circle cx="{sx}" cy="{sy}" r="0.8" fill="{_INK}"/>')
            elif kind == "whisker":
                parts.append(f'<line x1="{sx}" y1="{sy-5}" x2="{sx}" y2="{sy+5}" '
                             f'stroke="{_INK}" stroke-width="1"/>')
                parts.append(f'<line x1="{sx-4}" y1="{sy-5}" x2="{sx+4}" y2="{sy-5}" '
                             f'stroke="{_INK}" stroke-width="1"/>')
                parts.append(f'<line x1="{sx-4}" y1="{sy+5}" x2="{sx+4}" y2="{sy+5}" '
                             f'stroke="{_INK}" stroke-width="1"/>')
            elif kind == "outlier":
                parts.append(f'<circle cx="{sx}" cy="{sy}" r="2.4" fill="none" '
                             f'stroke="{_INK}" stroke-width="1"/>')
            x_cur = x_sym - max(16.0, fs_legend * 1.1)

    # 底部脚注
    if note or source:
        # 分割线与 note baseline 位置随 X 标签末行动态计算（不再固定从 H 倒推），
        # 避免 secondary label（"Mdn X.XXs"）与 "Notes. …" 横向 bbox 相交。
        foot_y = _foot_note_y
        parts.append(f'<line x1="{MARGIN_L}" y1="{_foot_divider_y:.1f}" x2="{width-MARGIN_R}" y2="{_foot_divider_y:.1f}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y:.1f}" font-family="{_body_font}" '
                         f'font-size="9.5" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            y_src = _foot_source_y if note else foot_y
            parts.append(f'<text x="{MARGIN_L}" y="{y_src:.1f}" font-family="{_body_font}" '
                         f'font-size="9.5" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')
        if figure_label:
            y_fig = (_foot_source_y if note else _foot_note_y) + (fs_foot + 6.0 if source else 14.0)
            # 防止 y_fig 超出 viewBox 底部：clamp 到 H - 4（保留 4px 内边距）
            y_fig = min(y_fig, height - 4.0)
            parts.append(f'<text x="{width-MARGIN_R}" y="{y_fig:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="9" fill="{c_muted}" '
                         f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 7) Sankey 桑基流
# ==============================================================
