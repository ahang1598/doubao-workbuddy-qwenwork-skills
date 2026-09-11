"""svg_lib/charts/matrix_heat.py

Matrix heatmap (correlation-plot style) with 5 cell rendering methods:
  square_flat_full / circle_full / ellipse_upper / pie_full / annotated_number

Data schema
-----------
data = {
    "matrix": [[num, ...], ...],   # N x N (usually symmetric) or M x N
    "labels": [str],               # row+col labels for symmetric, else col labels
    "row_labels"?: [str],          # for non-square matrix
    "diverging"?: bool,            # if True (and matrix contains 0/negative), color spans - / +
                                    # "-1" in the matrix always means "skip cell"
}

All 5 variants use the *same* data and labels; only cell rendering differs.
Layout: title/subtitle at top, row labels left, column labels rotated top, cells inside,
color bar on right.
"""
from __future__ import annotations
import math
import uuid
from ._shared import (

    resolve_palette, is_dark_palette, xesc, auto_font_size,
    rgb_tuple, _rgba_with_alpha,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgb_tuple, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib, _estimate_label_width_px)
_VARIANTS = {
    "square_flat_full",
    "circle_full",
    "ellipse_upper",
    "pie_full",
    "annotated_number",
}


def draw_matrix_heat(
    data: dict,
    variant: str = "square_flat_full",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 720,
    title: str = None,
    subtitle: str = None,
) -> str:
    """Render a matrix heatmap SVG."""
    if variant not in _VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {sorted(_VARIANTS)}")

    M = data.get("matrix")
    if not M or not M[0]:
        raise ValueError("matrix_heat: data['matrix'] required and non-empty")

    labels = data.get("labels")
    row_labels = data.get("row_labels", labels)
    col_labels = data.get("col_labels", labels)
    if row_labels is None:
        row_labels = [str(i + 1) for i in range(len(M))]
    if col_labels is None:
        col_labels = [str(i + 1) for i in range(len(M[0]))]

    n_rows = len(M)
    n_cols = len(M[0])

    # Compute value range (excluding sentinel -1 which means "skip cell")
    flat = [v for row in M for v in row if v is not None and v != -1]
    if not flat:
        raise ValueError("matrix_heat: no valid values")
    vmin = min(flat)
    vmax = max(flat)
    # Detect diverging
    diverging = data.get("diverging")
    if diverging is None:
        diverging = (vmin < 0 and vmax > 0)

    pal = resolve_palette(palette)
    ink = pal["ink"]
    accent = pal["accent"]
    secondary = pal["secondary"]
    bg = pal["bg"]
    muted = pal["muted"]
    ink6 = pal["ink6"]
    ink4 = pal["ink4"]
    ink2 = pal["ink2"]
    dark = is_dark_palette(pal)

    # Layout
    W = float(width)
    H = float(height)
    mt = 70.0 if title else 40.0
    if title and subtitle:
        mt = 100.0
    mr = 130.0   # room for color bar
    mb = 70.0    # room for column labels rotated up? actually cols on top; leave room for legend note

    # font size for labels — 先算出来，供 ml 自适应用
    label_fs = auto_font_size(max(n_rows, n_cols), base=12, min_size=8, max_size=14)

    # Adaptive left margin: row labels 用 text-anchor="end"，从 x = ml - 8 向左延伸。
    # 用 embed_svg_validator 相同的字符宽度模型估算最长 row label 渲染宽度，避免长文本被左裁
    # （ridge R6.5 已用同样思路修 "UDE 3.5 SONNET" 类问题；matrix 同样修）。
    _row_label_strs = [str(l) for l in row_labels]
    _max_row_label_px = max(
        (_estimate_label_width_px(lbl, label_fs, 0.0, bold=True,
                                   font_family="Inter, sans-serif") for lbl in _row_label_strs),
        default=0.0,
    )
    _min_ml = _max_row_label_px + 8 + 4  # 8 = anchor 偏移；4 = 2px OUT_OF_BOUNDS_MARGIN + 渲染余量
    _base_ml = 100.0 if max(len(str(l)) for l in row_labels) <= 8 else 130.0
    ml = max(_base_ml, _min_ml)

    plot_w = W - ml - mr
    plot_h = H - mt - mb
    cell = min(plot_w / n_cols, plot_h / n_rows)

    # Center grid horizontally in available plot area (approx)
    ml_grid = ml
    mt_grid = mt + 40  # leave room for rotated col labels

    def cx(i): return ml_grid + i * cell + cell / 2
    def cy(j): return mt_grid + j * cell + cell / 2

    # ---- Color function ----
    # cold/warm endpoints
    if diverging:
        # For dark bg, use lighter cold/warm so cells "pop"
        if dark:
            cold_rgb = (90, 130, 170)
            warm_rgb = rgb_tuple(accent)
        else:
            # cool-toned slate → warm accent
            cold_rgb = _cold_endpoint_for(pal)
            warm_rgb = rgb_tuple(accent)
        vspan_min = min(vmin, -abs(vmax))
        vspan_max = max(vmax, abs(vmin))
        if vspan_min == vspan_max:
            vspan_min, vspan_max = -1.0, 1.0
    else:
        # sequential: paper → accent
        cold_rgb = None
        warm_rgb = rgb_tuple(accent)
        if vmax == vmin:
            vmax = vmin + 1.0

    paper_rgb = rgb_tuple(bg)

    def val_to_color(v):
        if diverging:
            # symmetric around 0
            if v >= 0:
                t = min(1.0, v / vspan_max) if vspan_max > 0 else 0.0
                r = paper_rgb[0] + (warm_rgb[0] - paper_rgb[0]) * t
                g = paper_rgb[1] + (warm_rgb[1] - paper_rgb[1]) * t
                b = paper_rgb[2] + (warm_rgb[2] - paper_rgb[2]) * t
            else:
                t = min(1.0, v / vspan_min) if vspan_min < 0 else 0.0
                r = paper_rgb[0] + (cold_rgb[0] - paper_rgb[0]) * t
                g = paper_rgb[1] + (cold_rgb[1] - paper_rgb[1]) * t
                b = paper_rgb[2] + (cold_rgb[2] - paper_rgb[2]) * t
        else:
            t = 0.0 if vmax == vmin else (v - vmin) / (vmax - vmin)
            t = max(0.0, min(1.0, t))
            r = paper_rgb[0] + (warm_rgb[0] - paper_rgb[0]) * t
            g = paper_rgb[1] + (warm_rgb[1] - paper_rgb[1]) * t
            b = paper_rgb[2] + (warm_rgb[2] - paper_rgb[2]) * t
        return f"rgb({int(r)},{int(g)},{int(b)})"

    def text_color_for(v):
        # decide contrast against cell fill luminance
        col = val_to_color(v)
        # parse rgb
        try:
            body = col[col.index("(") + 1: col.rindex(")")]
            rr, gg, bb = [int(float(x)) for x in body.split(",")[:3]]
        except Exception:
            rr, gg, bb = 128, 128, 128
        luma = 0.299 * rr + 0.587 * gg + 0.114 * bb
        return "rgba(20,20,20,1)" if luma > 145 else "rgba(245,245,240,1)"

    # title font size (label_fs 已在 layout 计算阶段算过，供 ml 自适应用)
    title_fs = 22 if n_rows <= 10 else 20

    # ---- Build SVG ----
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>')

    # Title
    if title:
        parts.append(
            f'<text x="{ml_grid:.1f}" y="{40:.1f}" font-family="Georgia, serif" '
            f'font-size="{title_fs}" font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
    if subtitle:
        parts.append(
            f'<text x="{ml_grid:.1f}" y="{60:.1f}" font-family="Inter, sans-serif" '
            f'font-size="12" fill="{muted}" letter-spacing="0.06em">{xesc(subtitle)}</text>'
        )

    # column labels (rotated)
    for i, lab in enumerate(col_labels):
        x = cx(i)
        y = mt_grid - 6
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate(-40 {x:.1f} {y:.1f})" '
            f'text-anchor="start" font-family="Inter, sans-serif" '
            f'font-size="{label_fs}" font-weight="600" fill="{ink}">{xesc(lab)}</text>'
        )
    # row labels (left)
    for j, lab in enumerate(row_labels):
        parts.append(
            f'<text x="{ml_grid - 8:.1f}" y="{cy(j) + 4:.1f}" text-anchor="end" '
            f'font-family="Inter, sans-serif" font-size="{label_fs}" font-weight="600" '
            f'fill="{ink}">{xesc(lab)}</text>'
        )

    # cells
    upper_only = (variant == "ellipse_upper")

    for j in range(n_rows):
        for i in range(n_cols):
            if upper_only and j > i:
                continue
            v = M[j][i]
            if v == -1 or v is None:
                # skipped cell
                x0 = ml_grid + i * cell
                y0 = mt_grid + j * cell
                parts.append(
                    f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" width="{cell - 1:.1f}" '
                    f'height="{cell - 1:.1f}" fill="none" stroke="{ink2}" stroke-width="0.5"/>'
                )
                parts.append(
                    f'<text x="{cx(i):.1f}" y="{cy(j) + 3:.1f}" text-anchor="middle" '
                    f'font-family="Inter, sans-serif" font-size="{label_fs}" fill="{muted}">—</text>'
                )
                continue

            parts.append(_render_cell(
                variant, ml_grid + i * cell, mt_grid + j * cell, cell,
                v, val_to_color(v), text_color_for(v),
                ink, ink2, vspan_min if diverging else vmin, vspan_max if diverging else vmax,
                diverging, label_fs,
            ))

    # grid outline
    grid_w = n_cols * cell
    grid_h = n_rows * cell
    if upper_only:
        # only outline the triangle
        pts = [
            (ml_grid, mt_grid),
            (ml_grid + grid_w, mt_grid),
            (ml_grid + grid_w, mt_grid + grid_h),
        ]
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
        parts.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="0.8"/>')
    else:
        parts.append(
            f'<rect x="{ml_grid:.1f}" y="{mt_grid:.1f}" width="{grid_w:.1f}" '
            f'height="{grid_h:.1f}" fill="none" stroke="{ink}" stroke-width="0.8"/>'
        )

    # ---- Colorbar (right side) ----
    cb_x = ml_grid + grid_w + 24
    cb_y = mt_grid + 10
    cb_w = 14.0
    cb_h = min(240.0, grid_h - 20)
    # Suffix with a random hex so two slides using the same palette in one deck
    # don't produce duplicate <linearGradient> IDs (duplicate_element_id lint hit).
    # Same pattern as _boxplot_skin.apply_skin (uuid4 hex[:6]).
    grad_id = f"mh_cb_{uuid.uuid4().hex[:6]}"
    if diverging:
        parts.append(
            f'<defs><linearGradient id="{grad_id}" x1="0" y1="1" x2="0" y2="0">'
            f'<stop offset="0%" stop-color="rgb({cold_rgb[0]},{cold_rgb[1]},{cold_rgb[2]})"/>'
            f'<stop offset="50%" stop-color="rgb({paper_rgb[0]},{paper_rgb[1]},{paper_rgb[2]})"/>'
            f'<stop offset="100%" stop-color="rgb({warm_rgb[0]},{warm_rgb[1]},{warm_rgb[2]})"/>'
            f'</linearGradient></defs>'
        )
    else:
        parts.append(
            f'<defs><linearGradient id="{grad_id}" x1="0" y1="1" x2="0" y2="0">'
            f'<stop offset="0%" stop-color="rgb({paper_rgb[0]},{paper_rgb[1]},{paper_rgb[2]})"/>'
            f'<stop offset="100%" stop-color="rgb({warm_rgb[0]},{warm_rgb[1]},{warm_rgb[2]})"/>'
            f'</linearGradient></defs>'
        )
    parts.append(
        f'<rect x="{cb_x:.1f}" y="{cb_y:.1f}" width="{cb_w:.1f}" height="{cb_h:.1f}" '
        f'fill="url(#{grad_id})" stroke="{muted}" stroke-width="0.5"/>'
    )
    if diverging:
        ticks = [(vspan_min, f"{vspan_min:.1f}"),
                 (0, "0"),
                 (vspan_max, f"+{vspan_max:.1f}")]
        for tv, tl in ticks:
            frac = (tv - vspan_min) / (vspan_max - vspan_min) if vspan_max > vspan_min else 0.5
            yy = cb_y + cb_h * (1 - frac)
            parts.append(
                f'<line x1="{cb_x + cb_w:.1f}" y1="{yy:.1f}" x2="{cb_x + cb_w + 4:.1f}" y2="{yy:.1f}" '
                f'stroke="{muted}"/>'
            )
            parts.append(
                f'<text x="{cb_x + cb_w + 8:.1f}" y="{yy + 3.5:.1f}" '
                f'font-family="Inter, sans-serif" font-size="10" fill="{muted}">{tl}</text>'
            )
    else:
        for frac, tv in [(0.0, vmin), (0.5, (vmin + vmax) / 2), (1.0, vmax)]:
            yy = cb_y + cb_h * (1 - frac)
            parts.append(
                f'<line x1="{cb_x + cb_w:.1f}" y1="{yy:.1f}" x2="{cb_x + cb_w + 4:.1f}" y2="{yy:.1f}" '
                f'stroke="{muted}"/>'
            )
            parts.append(
                f'<text x="{cb_x + cb_w + 8:.1f}" y="{yy + 3.5:.1f}" '
                f'font-family="Inter, sans-serif" font-size="10" fill="{muted}">{tv:.2f}</text>'
            )

    parts.append('</svg>')
    return "".join(parts)


def _cold_endpoint_for(pal):
    """Pick a cool-toned cold endpoint that contrasts with warm accent."""
    # Simple heuristic: if secondary looks bluish/cool, use it; else default slate.
    sec = rgb_tuple(pal.get("secondary", "rgba(94,80,62,1)"))
    r, g, b = sec
    # cool test: b > r and g > r*0.9
    if b > r * 1.05:
        return sec
    # default slate/steel blue
    return (70, 95, 130)


def _render_cell(variant, x0, y0, cell, v, cell_col, txt_col,
                 ink, ink2, vlow, vhigh, diverging, label_fs):
    """Return SVG fragment for one cell using the chosen variant."""
    cxp = x0 + cell / 2
    cyp = y0 + cell / 2
    if variant == "square_flat_full":
        # Just filled square
        return (
            f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" width="{cell - 1:.1f}" '
            f'height="{cell - 1:.1f}" fill="{cell_col}"/>'
        )

    if variant == "circle_full":
        # size ∝ sqrt(|v|) fraction of max magnitude
        vmax_abs = max(abs(vlow), abs(vhigh), 1e-9)
        frac = (abs(v) / vmax_abs) if diverging else ((v - vlow) / (vhigh - vlow) if vhigh > vlow else 0.5)
        frac = max(0.0, min(1.0, frac))
        radius = (frac ** 0.5) * (cell / 2) * 0.9
        s = (
            f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" width="{cell - 1:.1f}" '
            f'height="{cell - 1:.1f}" fill="none" stroke="{ink2}" stroke-width="0.4"/>'
        )
        s += (
            f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{radius:.1f}" fill="{cell_col}"/>'
        )
        return s

    if variant == "ellipse_upper":
        # eccentricity ∝ |v|/vmax_abs; tilt by sign of v
        vmax_abs = max(abs(vlow), abs(vhigh), 1e-9)
        frac = (abs(v) / vmax_abs) if diverging else ((v - vlow) / (vhigh - vlow) if vhigh > vlow else 0.5)
        frac = max(0.0, min(1.0, frac))
        r_avail = (cell / 2) * 0.88
        rx = r_avail
        ry = r_avail * max(0.06, 1 - frac * 0.9)
        angle = -45 if v >= 0 else 45
        s = (
            f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" width="{cell - 1:.1f}" '
            f'height="{cell - 1:.1f}" fill="none" stroke="{ink2}" stroke-width="0.4"/>'
        )
        s += (
            f'<ellipse cx="{cxp:.1f}" cy="{cyp:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'transform="rotate({angle} {cxp:.1f} {cyp:.1f})" fill="{cell_col}" '
            f'stroke="{ink2}" stroke-width="0.5"/>'
        )
        return s

    if variant == "pie_full":
        # filled fraction ∝ |v|/vmax_abs; direction by sign
        vmax_abs = max(abs(vlow), abs(vhigh), 1e-9)
        frac = (abs(v) / vmax_abs) if diverging else ((v - vlow) / (vhigh - vlow) if vhigh > vlow else 0.5)
        frac = max(0.0, min(1.0, frac))
        r = (cell / 2) * 0.85
        s = (
            f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" width="{cell - 1:.1f}" '
            f'height="{cell - 1:.1f}" fill="none" stroke="{ink2}" stroke-width="0.4"/>'
        )
        # For a fully-filled cell the outline circle would sit at the exact same
        # cx/cy/r as the fill circle, producing a duplicate-bbox lint hit. Emit a
        # single fill+stroke circle in that case; otherwise draw the faint outline
        # (as a track) and stamp the pie wedge on top.
        if frac >= 0.999:
            s += (
                f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{r:.1f}" '
                f'fill="{cell_col}" stroke="{ink}" stroke-width="0.5"/>'
            )
            return s
        # outline circle (empty track)
        s += (
            f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{r:.1f}" fill="rgba(0,0,0,0.04)" '
            f'stroke="{ink}" stroke-width="0.5"/>'
        )
        if frac < 0.01:
            return s
        angle_deg = frac * 360.0
        # start at 12 o'clock
        if v >= 0:
            a_from, a_to = 0.0, angle_deg
            sweep = 1
        else:
            a_from, a_to = 0.0, -angle_deg
            sweep = 0

        def polar(ang):
            rad = math.radians(ang - 90)
            return cxp + r * math.cos(rad), cyp + r * math.sin(rad)

        x1, y1 = polar(a_from)
        x2, y2 = polar(a_to)
        large = 1 if abs(angle_deg) > 180 else 0
        s += (
            f'<path d="M {cxp:.1f} {cyp:.1f} L {x1:.1f} {y1:.1f} '
            f'A {r:.1f} {r:.1f} 0 {large} {sweep} {x2:.1f} {y2:.1f} Z" fill="{cell_col}"/>'
        )
        return s

    if variant == "annotated_number":
        s = (
            f'<rect x="{x0 + 0.5:.1f}" y="{y0 + 0.5:.1f}" width="{cell - 1:.1f}" '
            f'height="{cell - 1:.1f}" fill="{cell_col}"/>'
        )
        num_fs = max(9.0, cell * 0.28)
        # format: signed for diverging, plain else
        if diverging:
            txt = f"{v:+.2f}"
        else:
            txt = f"{v:.2f}"
        s += (
            f'<text x="{cxp:.1f}" y="{cyp + num_fs * 0.35:.1f}" text-anchor="middle" '
            f'font-family="Inter, sans-serif" font-size="{num_fs:.1f}" font-weight="500" '
            f'fill="{txt_col}">{txt}</text>'
        )
        return s

    return ""


def make_matrix_heat(matrix: Sequence[Sequence[float]],
                     labels: Sequence[str] = None,
                     row_labels: Sequence[str] = None,
                     col_labels: Sequence[str] = None,
                     row_sub_labels: Sequence[str] = None,
                     domain_groups: Sequence = None,
                     colormap: str = "auto",
                     midpoint: float = None,
                     vmin: float = None,
                     vmax: float = None,
                     show_row_mean: bool = True,
                     show_col_mean: bool = True,
                     show_colorbar: bool = True,
                     colorbar_label: str = "SCORE",
                     colorbar_sub: str = None,
                     value_fmt: str = ".1f",
                     title: str = None,
                     subtitle: str = None,
                     figure_label: str = None,
                     note: str = None,
                     source: str = None,
                     highlight_pair: tuple = None,   # 老 API 兼容（当 labels 传入时可用）
                     font_family: str = None,
                     palette=None,
                variant: str = None) -> str:
    """
    矩阵热力图（Dandelion academic 风格）。

    输入两种模式：
      A) 老 API（对称关系矩阵）：
         matrix = N×N；labels = N 个节点名；
         对角线可以传实际值（会正常上色）；也可以传 -1 或 None 表示"跳过该格"（渲染为灰色空白 + —）——
         常用于"节点跟自己无关系"的语义场景（相关矩阵、协作强度、A→B 依赖等）。
         highlight_pair=(i,j) 高亮某对
      B) 新 API（任意矩阵）：
         matrix = M×N，row_labels 长度 M，col_labels 长度 N
         每格显示数值 + 按 colormap 上色

    colormap:
      - "auto" (默认): 若数值有正负跨度或有 midpoint 参数 → diverging，否则 sequential
      - "diverging": 冷→中→暖，midpoint 处色中性
      - "sequential": 浅→深单色渐变（用 palette.accent 派生）
    midpoint: diverging colormap 的中点（默认取所有值中位数）
    vmin/vmax: 色标范围，缺省用 matrix min/max

    row_sub_labels: M 个行副描述（斜体小字），学术风惯例
    domain_groups: [(row_start, row_end, name), ...] 行分组左侧竖排大写标签
    show_row_mean / show_col_mean: 右/下均值 mini bar / 数字
    show_colorbar: 右侧竖色条

    title/subtitle/figure_label/note/source: 学术风顶/底文字
    """
    if not _variant_is_classic('matrix_heat', variant):
        _data = {"matrix": [list(r) for r in matrix], "labels": list(labels), "highlight_pair": highlight_pair}
        return _dispatch_to_svg_lib(
            'matrix_heat', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    if not matrix or not matrix[0]:
        raise ValueError("matrix_heat: empty matrix")

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.6))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(250,248,242,1)"

    # ---------- 老 API 兼容 ----------
    n_rows_raw = len(matrix)
    n_cols_raw = len(matrix[0])
    is_legacy = (labels is not None and row_labels is None and col_labels is None
                 and n_rows_raw == n_cols_raw and any(v == -1 for row in matrix for v in row))

    # 数据归一化：把 -1 视为 None（不渲染）
    def _val(v):
        if v is None or v == -1:
            return None
        return float(v)
    data = [[_val(v) for v in row] for row in matrix]

    if labels is not None and row_labels is None and col_labels is None:
        row_labels = list(labels)
        col_labels = list(labels)
    if row_labels is None:
        row_labels = [str(i+1) for i in range(n_rows_raw)]
    if col_labels is None:
        col_labels = [str(i+1) for i in range(n_cols_raw)]
    if len(row_labels) != n_rows_raw:
        raise ValueError(f"matrix_heat: row_labels len {len(row_labels)} != rows {n_rows_raw}")
    if len(col_labels) != n_cols_raw:
        raise ValueError(f"matrix_heat: col_labels len {len(col_labels)} != cols {n_cols_raw}")

    # 展平有效值
    flat = [v for row in data for v in row if v is not None]
    if not flat:
        raise ValueError("matrix_heat: no valid cell values")
    d_min = min(flat); d_max = max(flat)
    if vmin is None: vmin = d_min
    if vmax is None: vmax = d_max
    if vmax <= vmin:
        vmax = vmin + 1e-6

    # 决定 colormap 模式
    if colormap == "auto":
        # 若跨越 0 (含负值)、或用户显式给了 midpoint、或矩阵是 diverging（有明显正负段），走 diverging
        if midpoint is not None:
            cmap_mode = "diverging"
        elif d_min < 0 and d_max > 0:
            cmap_mode = "diverging"
            if midpoint is None:
                midpoint = 0
        else:
            cmap_mode = "sequential"
    else:
        cmap_mode = colormap
    if cmap_mode == "diverging" and midpoint is None:
        # 用中位数
        srt = sorted(flat)
        midpoint = srt[len(srt) // 2]

    # ---------- colormap ----------
    # 派生调色板：sequential = ink@1 到 accent（浅底：accent 深端；深底：accent 亮端）
    # diverging = ink→muted→accent 或从 palette accent + secondary 派生冷暖两侧
    def _lerp(a, b, t):
        return a + (b - a) * t

    def _rgb_to_hex(r, g, b):
        return (int(r), int(g), int(b))

    if cmap_mode == "diverging":
        # 冷端: palette secondary (若不存在则从 ink 派生冷色); 暖端: accent
        cold = _rgb_tuple(c_secondary)
        neutral = _rgb_tuple(PAPER)
        warm = _rgb_tuple(_ACC)
        stops = [
            (vmin, cold),
            (vmin + (midpoint - vmin) * 0.7, tuple(int(_lerp(cold[k], neutral[k], 0.6)) for k in range(3))),
            (midpoint, neutral),
            (midpoint + (vmax - midpoint) * 0.3, tuple(int(_lerp(neutral[k], warm[k], 0.6)) for k in range(3))),
            (vmax, warm),
        ]
    else:  # sequential
        # 浅→深：paper → accent
        light = _rgb_tuple(PAPER)
        deep = _rgb_tuple(_ACC)
        # 若 light 是深底 palette 的深色，则反转：deep = accent（亮）
        light_luma = 0.299 * light[0] + 0.587 * light[1] + 0.114 * light[2]
        if light_luma < 100:
            # 深底：从 深底 → accent（亮）
            stops = [(vmin, light), (vmax, deep)]
        else:
            # 浅底：paper → deep accent
            stops = [(vmin, light), (vmax, deep)]

    def value_to_color(v, alpha=1.0):
        if v is None:
            return "rgba(0,0,0,0)"
        v = max(vmin, min(vmax, v))
        for i in range(len(stops) - 1):
            v1, c1 = stops[i]
            v2, c2 = stops[i+1]
            if v1 <= v <= v2:
                t = (v - v1) / max(v2 - v1, 1e-9)
                r = _lerp(c1[0], c2[0], t)
                g = _lerp(c1[1], c2[1], t)
                b = _lerp(c1[2], c2[2], t)
                return f"rgba({int(r)},{int(g)},{int(b)},{alpha})"
        return "rgba(0,0,0,1)"

    def text_color_for_value(v):
        """选择格子上文字的颜色，保证与格子色对比充足。
        规则：格子亮 → 用深字；格子暗 → 用亮字。
        深底 / 浅底 palette 都能正确处理。
        """
        if v is None:
            return c_muted
        v_c = max(vmin, min(vmax, v))
        # 计算格子亮度
        cell_br = 200  # 默认
        for i in range(len(stops) - 1):
            v1, c1 = stops[i]
            v2, c2 = stops[i+1]
            if v1 <= v_c <= v2:
                t = (v_c - v1) / max(v2 - v1, 1e-9)
                r = _lerp(c1[0], c2[0], t)
                g = _lerp(c1[1], c2[1], t)
                b = _lerp(c1[2], c2[2], t)
                cell_br = 0.299*r + 0.587*g + 0.114*b
                break
        # 独立于 palette 的判断：格子亮就用深字（近黑），暗就用亮字（近白）
        DARK_TEXT = "rgba(24,26,34,1)"
        LIGHT_TEXT = "rgba(250,248,242,1)"
        return DARK_TEXT if cell_br > 145 else LIGHT_TEXT

    n_rows = n_rows_raw
    n_cols = n_cols_raw

    # ---------- 画布 ----------
    W = 1300
    H = 820
    MARGIN_T = 155 if title else 70
    MARGIN_B = 130 if (note or source) else 60
    plot_h = H - MARGIN_T - MARGIN_B
    cell_h = plot_h / n_rows

    # ---------- 字号自适应基准（cell_h 已知，可算 row_label_font；cell_w 需等 MARGIN_L 定后再算） ----------
    # 双重自适应：viewBox 尺寸 + 数据规模 (n = 矩阵边长)。
    # 目的：slide 里排 3 张 SVG 缩到 ~400px 宽时字也读得清。
    # base_fs = min(viewBox_w, viewBox_h) * 0.02  →  W=1300,H=820 → 16.4
    # 数据规模系数按 n = max(rows, cols) 分档。
    _n_mat = max(n_rows_raw, n_cols_raw)
    _base_fs = min(W, H) * 0.02
    if _n_mat <= 4:
        _fs_data = _base_fs * 1.4
    elif _n_mat <= 8:
        _fs_data = _base_fs * 1.0
    elif _n_mat <= 15:
        _fs_data = _base_fs * 0.8
    else:
        _fs_data = max(_base_fs * 0.6, 10)

    # 行标签字号：依赖 cell_h（此时已确定），不依赖 MARGIN_L。
    row_label_font = max(10.0, min(22.0, _fs_data * 1.05, cell_h / 2.6))

    # ---------- 自适应 MARGIN_L：根据最长 row_label 实际渲染宽度 ----------
    # 行标签以 text-anchor="end" 从 x = MARGIN_L - 12 向左延伸。
    # 用 embed_svg_validator 相同的字符宽度模型估算，保证 label 不被 viewBox 左侧裁掉
    # （ridge R6.5 已用同样思路修 "UDE 3.5 SONNET" 类问题）。
    # font-weight="600" → bold=True；无 letter-spacing。
    # CJK 字符（0x2E80-0x9FFF 等）在 _estimate_label_width_px 里落入 punct 分类（~0.5em），
    # 但实际渲染约 1em 宽（validator 侧用 unicodedata.east_asian_width 走 F/W 分支）。
    # 用同样的判定给 CJK 每字补足 (1 - 0.5) = 0.5em × bold_mul，避免 MARGIN_L 不足导致
    # "用户体验设计部门" 类 6+ 字 CJK label 溢 viewBox（R13 learn 报的 bug）。
    def _cjk_extra_px(_s, _fs, _bold):
        _mul = 1.05 if _bold else 1.0
        _extra = 0.0
        for _ch in _s:
            _code = ord(_ch)
            if (0x2E80 <= _code <= 0x9FFF or 0x3000 <= _code <= 0xD7AF
                    or 0xF900 <= _code <= 0xFAFF or 0xFE30 <= _code <= 0xFE4F
                    or 0xFF01 <= _code <= 0xFF60 or 0xFFE0 <= _code <= 0xFFE6):
                # 估算器把 CJK 当 punct(~0.5em)；实际约 1em → 每字补 ~0.5em
                _extra += _fs * 0.5 * _mul
        return _extra

    _row_label_strs = [str(l) for l in row_labels]
    _max_row_label_px = max(
        (_estimate_label_width_px(lbl, row_label_font, 0.0, bold=True,
                                   font_family=_body_font)
         + _cjk_extra_px(lbl, row_label_font, True) for lbl in _row_label_strs),
        default=0.0,
    )
    # 12 = anchor 偏移量（见下文行标签绘制）；+8 = 2px OUT_OF_BOUNDS_MARGIN + 渲染余量
    _min_margin_l = int(math.ceil(_max_row_label_px + 12 + 8))
    _base_margin_l = 200 if (domain_groups or row_sub_labels) else 150
    MARGIN_L = max(_base_margin_l, _min_margin_l)

    # ---------- 自适应 MARGIN_R：为 row-mean 数字与 colorbar 各自留出宽度 ----------
    # 右侧组成：row-mean bar(60) + gap(18) + row-mean 数字宽度 + gap + colorbar(14) + colorbar tick 文字 + 边距
    # 若不自适应，MARGIN_R 固定 250 时 row-mean 数字会撞进 colorbar rect（text_shape_overlap）。
    if show_colorbar or show_row_mean:
        # 估算 row-mean 数字最大宽度：按 fmt 格式化所有 row means 拿最长串。
        _fmt = "{:" + value_fmt + "}"
        _row_means_est = []
        for row in data:
            _vs = [v for v in row if v is not None]
            _row_means_est.append(sum(_vs) / len(_vs) if _vs else 0)
        # row-mean 数字字号 = max(11.0, cell_font_size*0.95)。此时 cell_font_size 未定，先用上界 min(28, cell_h*0.55) 保守估算。
        _rm_fs_upper = min(28.0, max(11.0, cell_h * 0.55 * 0.95))
        _rm_max_txt_w = max(
            (_estimate_label_width_px(_fmt.format(rm), _rm_fs_upper, 0.0, bold=False,
                                       font_family=_body_font) for rm in _row_means_est),
            default=0.0,
        )
        # 保存给下游 colorbar 位置计算用。
        _rm_max_txt_w_cache = _rm_max_txt_w
        _rm_fs_cache = _rm_fs_upper
        # ---- 估算 colorbar 右侧文字最大宽度（tick label + "SCORE" label + sub 描述） ----
        # fs_bar 尚未定义，用 min(14, max(10, _base_fs*0.7)) 一致公式。
        _fs_bar_est = round(min(14.0, max(10.0, _base_fs * 0.7)), 1)
        # tick label 用 vmin/vmax 生成的候选字符串保守估算。
        _tick_candidates = [f"{vmin:g}", f"{vmax:g}", f"{(vmin+vmax)/2:g}"]
        _tick_max_w = max(
            (_estimate_label_width_px(t, min(14.0, 12 * max(0.7, min(1.8, 1.0))), 0.0,
                                       bold=False, font_family=_body_font) for t in _tick_candidates),
            default=0.0,
        )
        # sub_txt: 若外部传入 colorbar_sub 使用之；否则用默认 "Sequential · min-max" / "Diverging · midpoint m"
        _sub_default = (f"Diverging · midpoint {vmin:g}"
                        if (vmin < 0 and vmax > 0) or (midpoint is not None)
                        else f"Sequential · {vmin:g}-{vmax:g}")
        _sub_est = colorbar_sub or _sub_default
        _sub_w = _estimate_label_width_px(_sub_est, _fs_bar_est, 0.05, bold=False,
                                           font_family=_body_font)
        _label_w = _estimate_label_width_px(colorbar_label or "", _fs_bar_est * 1.15,
                                             0.14, bold=True, font_family=_body_font)
        # cb_x 右侧最大文字宽度：tick label（从 cb_x + cb_w + 10 起）VS sub/label（从 cb_x - 4 起）。
        # 换算成"从 cb_x 开始需要的右侧宽度":
        #   tick 需要 cb_w(14) + 10 + tick_max_w + ~8 padding
        #   sub/label 需要 max(sub_w, label_w) - 4 + ~8 padding
        _cb_right_txt = max(14 + 10 + _tick_max_w, max(_sub_w, _label_w) - 4) + 8
        # 空间需求：12 (bar_x 起点 = plot_w 后 12) + 60 (bar) + 6 (bar → text 间距)
        #         + text + 10 (safety gap 到 cb) + cb_right_txt
        _needed_right = 12 + 60 + 6 + _rm_max_txt_w + 10 + _cb_right_txt
        MARGIN_R = max(250, int(math.ceil(_needed_right)))
    else:
        MARGIN_R = 60
        _rm_max_txt_w_cache = 0.0
        _rm_fs_cache = 11.0

    plot_w = W - MARGIN_L - MARGIN_R
    cell_w = plot_w / n_cols

    # 参考基准：cell 几何均值 vs 8×8 默认 (~86) → scale
    _cell_geo = math.sqrt(max(1.0, cell_w) * max(1.0, cell_h))
    _scale = max(0.7, min(1.8, _cell_geo / 86.0))

    # ---------- 动态字号 ----------
    # 单元格中数字标签：cell 尺寸独立控制 —— cell 大字号也大
    # cell_fs = min(cell_w, cell_h) * 0.25，保证格子够大时数字够大。
    # 仍受"单字符宽度"约束以免长数值溢出。
    sample_val = None
    for row in data:
        for v in row:
            if v is not None:
                sample_val = v; break
        if sample_val is not None:
            break
    sample_str = ("{:" + value_fmt + "}").format(sample_val) if sample_val is not None else "00.0"
    max_by_w = cell_w * 0.85 / max(1, len(sample_str) * 0.55)
    max_by_h = cell_h * 0.55
    _cell_num_target = min(cell_w, cell_h) * 0.25
    cell_font_size = max(9.0, min(28.0, _cell_num_target, max_by_w, max_by_h))
    # 列标签：用 _fs_data 作为期望字号，同样受 cell 尺寸约束防溢出
    col_label_font = max(9.0, min(20.0, _fs_data, cell_w / 5.5))

    # 辅助文字字号（title/subtitle/figure_label/colorbar 等）
    # base_fs = 16.4 → title 想要 ~1.6×，subtitle ~0.7×
    fs_title    = round(min(34.0, max(20.0, _base_fs * 1.6)), 1)
    fs_subtitle = round(min(16.0, max(10.0, _base_fs * 0.75)), 1)
    fs_figure   = round(min(13.0, max(9.0,  _base_fs * 0.62)), 1)
    fs_bar      = round(min(14.0, max(10.0, _base_fs * 0.7)), 1)   # colorbar / footer note

    def cell_x(mi): return MARGIN_L + mi * cell_w
    def cell_y(bi): return MARGIN_T + bi * cell_h

    parts = []

    # 深底 palette 加背景
    if c_bg:
        parts.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')

    # ---------- 顶部 ----------
    # 顶部三行 y 位置根据 fs 联动（避免大字号时行距不够）
    _y_title = 20 + fs_title  # baseline
    _y_subtitle = _y_title + fs_title * 0.55 + fs_subtitle
    _y_line = _y_subtitle + 12
    _y_figure = _y_line + 14 + fs_figure * 0.5
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_title:.1f}" '
                     f'font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_subtitle:.1f}" '
                     f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
        parts.append(f'<line x1="{MARGIN_L}" y1="{_y_line:.1f}" x2="{W-40}" y2="{_y_line:.1f}" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        label_w = max(72, len(figure_label) * 8 + 20)
        note_txt = f"Heatmap · {n_rows} rows × {n_cols} cols"
        parts.append(f'<text x="{MARGIN_L+label_w}" y="{_y_figure:.1f}" font-family="{_body_font}" font-size="{fs_figure}" '
                     f'fill="{c_muted}" letter-spacing=".04em">{_xesc(note_txt)}</text>')

    # ---------- 列标签（旋转 -35°）----------
    for mi, cname in enumerate(col_labels):
        x = cell_x(mi) + cell_w / 2
        y = MARGIN_T - 8
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" '
                     f'transform="rotate(-35 {x:.1f} {y:.1f})" '
                     f'text-anchor="start" font-family="{_body_font}" '
                     f'font-size="{col_label_font:.1f}" font-weight="600" fill="{_INK}">{_xesc(str(cname))}</text>')

    # ---------- 行标签 + 副描述 ----------
    for bi, bname in enumerate(row_labels):
        y = cell_y(bi) + cell_h / 2
        sub = row_sub_labels[bi] if row_sub_labels and bi < len(row_sub_labels) else None
        sub_fs = max(7.0, row_label_font - 2)
        parts.append(f'<text x="{MARGIN_L - 12}" y="{y - (3 if sub else -3):.1f}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{row_label_font:.1f}" font-weight="600" '
                     f'fill="{_INK}">{_xesc(str(bname))}</text>')
        if sub:
            parts.append(f'<text x="{MARGIN_L - 12}" y="{y + 10:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{sub_fs:.1f}" '
                         f'fill="{c_muted}" font-style="italic">{_xesc(str(sub))}</text>')

    # ---------- 每个格子 ----------
    for bi in range(n_rows):
        for mi in range(n_cols):
            v = data[bi][mi]
            x = cell_x(mi)
            y = cell_y(bi)
            if v is None:
                # 空格：淡灰底 + "—"
                parts.append(f'<rect x="{x+0.5:.1f}" y="{y+0.5:.1f}" '
                             f'width="{cell_w-1:.1f}" height="{cell_h-1:.1f}" '
                             f'fill="{_rgba_with_alpha(_INK, 0.04)}"/>')
                parts.append(f'<text x="{x + cell_w/2:.1f}" y="{y + cell_h/2 + 3.5:.1f}" '
                             f'text-anchor="middle" font-family="{_body_font}" '
                             f'font-size="{cell_font_size:.1f}" fill="{c_muted}">—</text>')
                continue
            fill = value_to_color(v)
            txt = text_color_for_value(v)
            # highlight_pair (老 API 兼容)：以往用 fill + 独立 outline rect 两个 element，
            # 在完全相同 bbox 上叠加会触发 duplicate_element_id / bbox_overlap（R13 brand/learn 报的 bug）。
            # 参照 R6.5 gantt 的修法，合并为 fill+stroke 的单一 rect。
            _is_highlight = (
                is_legacy and highlight_pair
                and (bi, mi) in [tuple(highlight_pair), (highlight_pair[1], highlight_pair[0])]
            )
            if _is_highlight:
                parts.append(f'<rect x="{x+0.5:.1f}" y="{y+0.5:.1f}" '
                             f'width="{cell_w-1:.1f}" height="{cell_h-1:.1f}" '
                             f'fill="{fill}" stroke="{_ACC}" stroke-width="2"/>')
            else:
                parts.append(f'<rect x="{x+0.5:.1f}" y="{y+0.5:.1f}" '
                             f'width="{cell_w-1:.1f}" height="{cell_h-1:.1f}" '
                             f'fill="{fill}"/>')
            # 数值
            fmt_str = "{:" + value_fmt + "}"
            parts.append(f'<text x="{x + cell_w/2:.1f}" y="{y + cell_h/2 + cell_font_size*0.32:.1f}" '
                         f'text-anchor="middle" font-family="{_body_font}" '
                         f'font-size="{cell_font_size:.1f}" font-weight="500" fill="{txt}">{_xesc(fmt_str.format(v))}</text>')

    # ---------- domain 分组：左侧竖标签 + 白色横线分隔 ----------
    if domain_groups:
        for dg in domain_groups:
            if len(dg) < 3:
                continue
            rs, re_, dl = dg[0], dg[1], dg[2]
            if rs > 0:
                y = MARGIN_T + rs * cell_h
                parts.append(f'<line x1="{MARGIN_L - 4}" y1="{y:.1f}" '
                             f'x2="{MARGIN_L + plot_w:.1f}" y2="{y:.1f}" '
                             f'stroke="{PAPER}" stroke-width="2"/>')
            # 左侧竖排大写标签
            domain_x = MARGIN_L - 148
            y_mid = MARGIN_T + (rs + re_) / 2 * cell_h
            parts.append(f'<text x="{domain_x}" y="{y_mid + 3:.1f}" '
                         f'transform="rotate(-90 {domain_x} {y_mid:.1f})" '
                         f'text-anchor="middle" font-family="{_body_font}" '
                         f'font-size="{fs_bar}" fill="{c_muted}" font-weight="600" letter-spacing=".18em">'
                         f'{_xesc(str(dl).upper())}</text>')

    # ---------- 右侧 ROW MEAN mini bar ----------
    bar_x = MARGIN_L + plot_w + 12
    bar_maxw = 60
    if show_row_mean:
        row_means = []
        for row in data:
            vs = [v for v in row if v is not None]
            row_means.append(sum(vs) / len(vs) if vs else 0)
        max_mean = max(row_means) if row_means else 1
        parts.append(f'<text x="{bar_x}" y="{MARGIN_T - 8}" font-family="{_body_font}" '
                     f'font-size="{fs_bar}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">ROW MEAN</text>')
        for bi, avg in enumerate(row_means):
            y = cell_y(bi) + cell_h / 2
            bar_len = (avg / max_mean) * bar_maxw if max_mean > 0 else 0
            parts.append(f'<rect x="{bar_x}" y="{y-4:.1f}" width="{max(0.5, bar_len):.1f}" height="8" '
                         f'fill="{value_to_color(avg, 0.55)}" stroke="{value_to_color(avg, 1)}" '
                         f'stroke-width="0.6"/>')
            fmt_str = "{:" + value_fmt + "}"
            # row-mean 数字是 secondary label，floor 11pt 保证 embed 后可读
            parts.append(f'<text x="{bar_x + bar_maxw + 6}" y="{y + 3:.1f}" text-anchor="start" '
                         f'font-family="{_body_font}" font-size="{round(max(11.0, cell_font_size * 0.95), 1)}" fill="{c_muted}" '
                         f'font-weight="500">{_xesc(fmt_str.format(avg))}</text>')

    # ---------- 底部 COL MEAN ----------
    if show_col_mean:
        col_means = []
        for mi in range(n_cols):
            vs = [data[bi][mi] for bi in range(n_rows) if data[bi][mi] is not None]
            col_means.append(sum(vs) / len(vs) if vs else 0)
        fmt_str = "{:" + value_fmt + "}"
        # col-mean 数字宽度不得超过 cell_w，否则会溢到相邻 cell 上方形成 text_shape_overlap。
        # 用 embed_svg_validator 的字符宽度模型算出：当 fs = _fs_upper 时最长值需要多少 px，
        # 若 > cell_w * 0.92 就按比例回退 fs（floor 保持 9pt，比原 11pt 略低但仅在极窄 cell 下触发）。
        _fs_col_mean_upper = max(11.0, cell_font_size * 0.95)
        _col_max_txt_upper = max(
            (_estimate_label_width_px(fmt_str.format(a), _fs_col_mean_upper, 0.0,
                                       bold=True, font_family=_body_font) for a in col_means),
            default=0.0,
        )
        _col_target_w = cell_w * 0.92
        if _col_max_txt_upper > _col_target_w and _col_max_txt_upper > 0:
            _fs_col_mean = max(9.0, _fs_col_mean_upper * (_col_target_w / _col_max_txt_upper))
        else:
            _fs_col_mean = _fs_col_mean_upper
        # y_bot 需在 grid 底边下方留出足够 clearance：文字 bbox top = y_bot - fs*0.8，
        # 必须 > grid 底边 (MARGIN_T + plot_h) 才能避免 text_shape_overlap（Bug 1 in classic 3x3）。
        # 取 max(20, _fs_col_mean * 0.85 + 3) 让大 fs 时 gap 自动变大。
        _col_gap = max(20.0, _fs_col_mean * 0.85 + 3)
        y_bot = MARGIN_T + plot_h + _col_gap
        parts.append(f'<text x="{MARGIN_L - 12}" y="{y_bot:.1f}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{fs_bar}" fill="{c_muted}" '
                     f'font-weight="600" letter-spacing=".14em">COL MEAN</text>')
        for mi, avg in enumerate(col_means):
            x = cell_x(mi) + cell_w / 2
            parts.append(f'<text x="{x:.1f}" y="{y_bot:.1f}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="{_fs_col_mean:.1f}" font-weight="600" '
                         f'fill="{value_to_color(avg, 1)}">{_xesc(fmt_str.format(avg))}</text>')

    # ---------- 右侧 colorbar ----------
    if show_colorbar:
        # cb_x 需在 row-mean 数字末端右侧再留 gap，避免 text_shape_overlap（Bug 1）。
        # bar_x = MARGIN_L + plot_w + 12；row-mean 数字左端 = bar_x + 60 + 6；右端 = 左端 + max_txt_w。
        # cb_x 从原固定 W - MARGIN_R + 110 改为 dynamic：max(旧值, row-mean 数字右端 + 10)。
        _cb_x_min = MARGIN_L + plot_w + 12 + 60 + 6 + _rm_max_txt_w_cache + 10
        cb_x = max(W - MARGIN_R + 110, _cb_x_min)
        cb_y = MARGIN_T + 130
        cb_w = 14
        cb_h = 300
        # 渐变
        grad_stops = []
        for v, c in stops:
            offset = (v - vmin) / max(vmax - vmin, 1e-9) * 100
            grad_stops.append(f'<stop offset="{offset:.1f}%" stop-color="rgb({c[0]},{c[1]},{c[2]})"/>')
        parts.append(f'<defs><linearGradient id="cbGrad_{id(matrix) & 0xffff}" x1="0" y1="1" x2="0" y2="0">'
                     f'{"".join(grad_stops)}'
                     f'</linearGradient></defs>')
        parts.append(f'<rect x="{cb_x}" y="{cb_y}" width="{cb_w}" height="{cb_h}" '
                     f'fill="url(#cbGrad_{id(matrix) & 0xffff})" stroke="{_INK4}" stroke-width="0.6"/>')
        # 刻度：4-6 档 nice-number
        def _nice_ticks(vmin, vmax, target=5):
            span = vmax - vmin
            if span <= 0:
                return [vmin]
            raw = span / target
            mag = 10 ** math.floor(math.log10(max(raw, 1e-9)))
            for nice in (1, 2, 2.5, 5, 10):
                if raw / mag <= nice:
                    step = nice * mag
                    break
            else:
                step = 10 * mag
            t = math.ceil(vmin / step) * step
            ticks = []
            while t <= vmax + 1e-9:
                ticks.append(t); t += step
            return ticks
        cb_ticks = _nice_ticks(vmin, vmax)
        # 若 diverging 且 midpoint 不在 ticks 中，加进去
        if cmap_mode == "diverging" and midpoint not in cb_ticks:
            cb_ticks = sorted(set(cb_ticks + [midpoint]))
        for tv in cb_ticks:
            if tv < vmin - 1e-9 or tv > vmax + 1e-9:
                continue
            ty = cb_y + cb_h * (1 - (tv - vmin) / max(vmax - vmin, 1e-9))
            parts.append(f'<line x1="{cb_x + cb_w}" y1="{ty:.1f}" x2="{cb_x + cb_w + 4}" y2="{ty:.1f}" '
                         f'stroke="{c_muted}" stroke-width="0.8"/>')
            is_mid = (cmap_mode == "diverging" and abs(tv - midpoint) < 1e-6)
            label = f"{tv:g}" + (" ←" if is_mid else "")
            weight = "700" if is_mid else "500"
            parts.append(f'<text x="{cb_x + cb_w + 10}" y="{ty + 3.5:.1f}" text-anchor="start" '
                         f'font-family="{_body_font}" font-size="{round(min(14.0, 12 * _scale), 1)}" fill="{c_muted}" '
                         f'font-weight="{weight}">{_xesc(label)}</text>')
        # 标题
        # colorbar 上方三行文字的间距也跟 scale 联动，避免大 scale 时重叠
        _gap = 20 * _scale
        _fs_cb_label  = round(min(15.0, 13 * _scale), 1)   # 'Value'
        _fs_cb_arrow  = round(min(12.0, 10 * _scale), 1)   # '↑ Above midpoint'
        _fs_cb_tick   = round(min(14.0, 12 * _scale), 1)   # colorbar 刻度数字
        _y_value = cb_y - _gap
        _y_sub   = _y_value - _gap
        _y_arrow = _y_sub - _gap
        # 若同时显示 row-mean mini bar：三行 header (arrow / sub / value) 需夹在
        # ROW MEAN 表头底边 与 row-mean 首行数字顶边 之间，否则 sub/value 会与首行数字重叠。
        # 大 _scale 时空间往往不足，此时把 header 整体上移到 ROW MEAN 表头之上。
        if show_row_mean:
            _rm_header_top = (MARGIN_T - 8) - fs_bar * 0.8
            _rm_first_top = (MARGIN_T + cell_h / 2 + 3) - (10 * _scale) * 0.8
            _y_value_bottom = _y_value + _fs_cb_label * 0.2
            if _y_value_bottom > _rm_first_top - 4:
                # 空间不够：把 header 三行整体挪到 ROW MEAN 表头之上（y=cb_y 无关，改以 rm_header_top 为锚）
                _tight_gap = min(_gap, _fs_cb_label + 6)
                _y_value = _rm_header_top - 8
                _y_sub   = _y_value - _tight_gap
                _y_arrow = _y_sub - _tight_gap
        # 若上方存在 subtitle divider line（y=_y_line），确保 ↑ Above midpoint 的字形顶
        # 与 divider 至少留 4px 间隙，防止 divider 从 caption 中间穿过（embed_svg_line_through_text）。
        # 若 arrow 字形顶低于 divider+4，则把三行 header 整体下移；value 允许下探至 row-mean 首行数字上方。
        if subtitle:
            _divider_clear = _y_line + 4 + _fs_cb_arrow  # 要求 _y_arrow >= 该值
            if _y_arrow < _divider_clear:
                _shift = _divider_clear - _y_arrow
                # 三行同步下移；先按 shift 后再夹到 row-mean 首行数字顶之上
                _y_arrow += _shift
                _y_sub   += _shift
                _y_value += _shift
                if show_row_mean:
                    _rm_first_top = (MARGIN_T + cell_h / 2 + 3) - (10 * _scale) * 0.8
                    _value_bottom_cap = _rm_first_top - 4
                    if _y_value + _fs_cb_label * 0.2 > _value_bottom_cap:
                        # 空间被上下夹紧，压缩行距（丢掉 sub 与 arrow 之间的额外间距）
                        _shrink = (_y_value + _fs_cb_label * 0.2) - _value_bottom_cap
                        _y_value -= _shrink
                        # arrow 仍需守住 divider 底部间隙，仅压 sub/value 之间距
                        _y_sub = min(_y_sub, _y_value - (_fs_cb_label + 4))
                        # sub 与 arrow 若被压反，直接把 sub 放到 arrow 下方一行
                        if _y_sub <= _y_arrow:
                            _y_sub = _y_arrow + _fs_cb_arrow + 4
        parts.append(f'<text x="{cb_x - 4}" y="{_y_value:.1f}" font-family="{_body_font}" '
                     f'font-size="{_fs_cb_label}" fill="{_INK}" font-weight="600" letter-spacing=".14em">'
                     f'{_xesc(colorbar_label)}</text>')
        sub_txt = colorbar_sub
        if sub_txt is None:
            if cmap_mode == "diverging":
                sub_txt = f"Diverging · midpoint {midpoint:g}"
            else:
                sub_txt = f"Sequential · {vmin:g}-{vmax:g}"
        parts.append(f'<text x="{cb_x - 4}" y="{_y_sub:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_bar}" fill="{c_muted}" letter-spacing=".05em">'
                     f'{_xesc(sub_txt)}</text>')
        # ↑↓ 副注
        parts.append(f'<text x="{cb_x + cb_w/2:.1f}" y="{_y_arrow:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{_fs_cb_arrow}" fill="{c_muted}" '
                     f'letter-spacing=".03em">↑ Above midpoint</text>')
        parts.append(f'<text x="{cb_x + cb_w/2:.1f}" y="{cb_y + cb_h + _gap * 1.5:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{_fs_cb_arrow}" fill="{c_muted}" '
                     f'letter-spacing=".03em">↓ Below midpoint</text>')

    # ---------- 底部脚注 ----------
    if note or source:
        foot_y = H - 45
        parts.append(f'<line x1="{MARGIN_L}" y1="{foot_y-14}" x2="{W-40}" y2="{foot_y-14}" '
                     f'stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y}" font-family="{_body_font}" '
                         f'font-size="{round(9.5 * _scale, 1)}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            parts.append(f'<text x="{MARGIN_L}" y="{foot_y+14}" font-family="{_body_font}" '
                         f'font-size="{round(9.5 * _scale, 1)}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')
        if figure_label:
            parts.append(f'<text x="{W-40}" y="{foot_y+14}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_bar}" fill="{c_muted}" '
                         f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 16) 2×2 Positioning 象限图
# ==============================================================
