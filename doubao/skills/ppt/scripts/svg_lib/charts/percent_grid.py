"""svg_lib/charts/percent_grid.py

Percent Grid · 5 variant 统一 API：
- square_10x10: 10x10 方格 waffle，从左到右从上到下按类别填色
- dot_10x10: 100 圆点 waffle（Isotype 极简）
- person_10x10: 100 简笔小人（社会调查感）
- square_stacked_row: 单行 100 格长条（含刻度）
- dot_faceted: 每类一个独立 10x10 mini panel

data schema：
  {
    "options": [(label, count_of_100), ...],
  }
  - count_of_100: 每类占多少（0-100）
  - 所有 count 加起来应 ≤ 100；> 100 时截断到 100（并把多余的类丢弃并 warn）
  - < 100 时剩余用 muted 灰色填充
"""
from __future__ import annotations
import math
import warnings
from typing import Dict, Optional, List, Tuple

from ._shared import (

    resolve_palette, xesc, svg_open, svg_close, auto_font_size,
    _rgba_with_alpha, rgb_tuple,
)

from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
VARIANTS = (
    "square_10x10", "dot_10x10", "person_10x10",
    "square_stacked_row", "dot_faceted",
)


def _series_colors(pal, n):
    """5 variants 用的类别色。palette 优先级：
      1) pal["series"] 长度够 → 直接切前 n 个
      2) pal["series"] 不够 → 循环补齐（保持 palette 家族色）
      3) 无 series → 用 _derive_series_colors 做黄金角派生（也是从 pal.accent
         出发，跟 make_percent_grid 走同一套 palette-aware 逻辑）
    之前 case 3 硬编码 [accent, secondary, ink, muted] 循环，会把 ink（文本墨色）
    塞进去当类别色，跟 palette 语义不符；现在统一走 _derive_series_colors。
    """
    series = pal.get("series")
    if series and len(series) >= n:
        return list(series[:n])
    if series:
        return [series[i % len(series)] for i in range(n)]
    return _derive_series_colors(pal, n, mode="distinct")


def _resolve_options(options: List[Tuple[str, float]]):
    """归一化并截断到 100，返回 [(label, count)]"""
    total = sum(int(c) for _, c in options)
    resolved = []
    if total <= 100:
        for lbl, c in options:
            resolved.append((lbl, int(c)))
        return resolved
    warnings.warn(f"percent_grid: total counts {total} > 100, truncating")
    remaining = 100
    for lbl, c in options:
        c = int(c)
        if remaining <= 0:
            break
        take = min(c, remaining)
        resolved.append((lbl, take))
        remaining -= take
    return resolved


def draw_percent_grid(
    data: Dict,
    variant: str = "square_10x10",
    palette="archive_ink",
    width: Optional[float] = None,
    height: Optional[float] = None,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    figure_label: Optional[str] = None,
) -> str:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}. Available: {VARIANTS}")

    options = data.get("options") or []
    if not options:
        raise ValueError("percent_grid: at least one option required")
    options = _resolve_options(options)
    total_count = sum(c for _, c in options)
    remaining = 100 - total_count

    pal = resolve_palette(palette)
    ink, ink6 = pal["ink"], pal["ink6"]
    bg = pal["bg"]
    accent = pal["accent"]
    series = _series_colors(pal, max(4, len(options)))
    muted_fill = _rgba_with_alpha(ink, 0.12)

    body_font = "Inter, sans-serif"
    head_font = "Georgia, serif"

    ML = 60
    # ---- viewBox 按 variant 计算：把 legend 放在主体下方，压缩右侧和底部留白 ----
    # 主 10×10 grid 常量：cell 30/32 + gap 4，宽度 340~356，加左右 padding 40
    _n = len(options)
    _has_head = bool(title or subtitle or figure_label)
    _head_h = 100 if _has_head else 60  # title/subtitle 区高度（含 top_offset baseline）

    def _estimate_legend_rows(labels, counts, max_w, fs=13):
        """按 _draw_legend 的宽度估算（CJK-aware）计算实际会 wrap 到几行。
        必须与 _draw_legend 内部逻辑对齐：item_w = 20 + text_w + 20，
        text 是 "{lbl} {cnt}%"。"""
        x = 0.0
        rows = 1
        for lbl, cnt in zip(labels, counts):
            s = f"{lbl} {cnt}%"
            tw = sum((fs if ord(c) > 127 else fs * 0.55) for c in s)
            item_w = 20 + tw + 20
            if x + item_w > max_w and x > 0:
                rows += 1
                x = 0.0
            x += item_w
        return rows

    if variant in ("square_10x10", "dot_10x10"):
        _grid_w = 10 * 30 + 9 * 4  # 336
        _grid_h = _grid_w
        _labels = [l for l, _ in options]
        _counts = [c for _, c in options]
        _fs_lg = auto_font_size(_n, base=12, min_size=9, max_size=13)
        _legend_rows = _estimate_legend_rows(_labels, _counts, _grid_w, fs=_fs_lg)
        _row_h = max(22.0, _fs_lg * 1.8)
        _legend_h = _legend_rows * _row_h + 14  # +14 = swatch height
        width = ML + 40 + _grid_w + 40  # 476
        height = _head_h + _grid_h + 30 + _legend_h + 20
    elif variant == "person_10x10":
        _grid_w = 10 * 32 + 9 * 4  # 356
        _grid_h = _grid_w
        _labels = [l for l, _ in options]
        _counts = [c for _, c in options]
        _fs_lg = auto_font_size(_n, base=12, min_size=9, max_size=13)
        _legend_rows = _estimate_legend_rows(_labels, _counts, _grid_w, fs=_fs_lg)
        _row_h = max(22.0, _fs_lg * 1.8)
        _legend_h = _legend_rows * _row_h + 14
        width = ML + 40 + _grid_w + 40  # 496
        height = _head_h + _grid_h + 30 + _legend_h + 20
    elif variant == "square_stacked_row":
        # 保持宽度 900（bar 需要长度），但收紧高度
        width = 900
        _labels = [l for l, _ in options]
        _counts = [c for _, c in options]
        _fs_lg = auto_font_size(_n, base=12, min_size=9, max_size=13)
        _legend_max_w = width - (ML + 40) - 40
        _legend_rows = _estimate_legend_rows(_labels, _counts, _legend_max_w, fs=_fs_lg)
        _row_h = max(22.0, _fs_lg * 1.8)
        _legend_h = _legend_rows * _row_h + 14
        # top_offset(110) + 60(header gap) + cell_h(72) + ticks(30) + legend + bottom pad
        height = _head_h + 60 + 72 + 30 + 20 + _legend_h + 20
    elif variant == "dot_faceted":
        # 保持宽度但收紧高度：header + 40 + panel(title+val+grid) + 30 bottom
        width = 900
        # cell_size 受 panel_w 限制（panel_w 又受 N 限制），高 N 时 cell_size 远小于
        # 26 上限，若 viewBox 仍按 grid_size=258 算会在底部留大片空白。
        # 这里镜像 _draw_faceted 里的实际计算：
        #   grid_x = ML + 40，total_avail_w = width - grid_x - 40
        #   panel_w = (total_avail_w - (N-1)*panel_gap) / N
        #   cell_size = min((panel_w - 9*cell_gap) / 10, 26.0)
        #   grid_size = 10*cell_size + 9*cell_gap
        _grid_x_calc = ML + 40
        _total_avail_w = width - _grid_x_calc - 40
        _panel_gap_calc = 20.0
        _panel_w_calc = (_total_avail_w - (_n - 1) * _panel_gap_calc) / _n
        _cell_gap_calc = 1.2
        _cell_size_calc = min((_panel_w_calc - 9 * _cell_gap_calc) / 10, 26.0)
        _grid_size_calc = 10 * _cell_size_calc + 9 * _cell_gap_calc
        # 底部边框 = gy0 - 4 + grid_size + 6 = grid_size + 2 相对于 gy0
        # gy0 = grid_y + 26, grid_y = top_offset + 40, top_offset ≈ _head_h + 10
        # header + 40 = _head_h + 40（grid_y 位置）；再 + 26（到 gy0）+ grid_size + 2（border 底沿）+ 30 底 padding
        height = _head_h + 40 + 26 + _grid_size_calc + 2 + 30
    else:
        width = width or 900
        height = height or 620

    parts = [svg_open(0, 0, width, height, bg=bg)]

    # title / subtitle
    if figure_label:
        parts.append(
            f'<text x="{ML}" y="24" font-family="{body_font}" font-size="10" '
            f'font-weight="700" fill="{pal["muted"]}" letter-spacing=".18em">'
            f'{xesc(figure_label)}</text>'
        )
    if title:
        parts.append(
            f'<text x="{ML}" y="54" font-family="{head_font}" font-size="24" '
            f'font-weight="600" fill="{ink}">{xesc(title)}</text>'
        )
    if subtitle:
        # subtitle 与 title baseline 拉开：24pt title 下沿 ≈ 60，subtitle 落在 82
        # 让 title(黑) 与 subtitle(灰) 距离 ≥ fs*0.4（title 24 → 9.6px）
        parts.append(
            f'<text x="{ML}" y="82" font-family="{body_font}" font-size="11" '
            f'fill="{pal["muted"]}" letter-spacing=".08em">{xesc(subtitle)}</text>'
        )

    top_offset = 100 + (10 if title or subtitle else -40)

    # 构造 fill 序列（每格一个色）
    fills = []
    for lbl_idx, (lbl, cnt) in enumerate(options):
        col = series[lbl_idx % len(series)]
        fills.extend([col] * cnt)
    fills.extend([muted_fill] * remaining)
    # 确保总长 100
    fills = fills[:100]

    # 图元
    if variant == "square_10x10":
        _draw_10x10_squares(parts, fills, ML, top_offset, options, pal, width=width)
    elif variant == "dot_10x10":
        _draw_10x10_dots(parts, fills, ML, top_offset, options, pal, width=width)
    elif variant == "person_10x10":
        _draw_10x10_persons(parts, fills, ML, top_offset, options, pal, width=width)
    elif variant == "square_stacked_row":
        _draw_stacked_row(parts, fills, ML, top_offset, options, pal, width)
    elif variant == "dot_faceted":
        _draw_faceted(parts, options, remaining, ML, top_offset, pal, series, width, muted_fill)

    parts.append(svg_close())
    return "".join(parts)


def _draw_legend(parts, options, cx, cy, pal, orientation="horizontal", max_w=800):
    """绘制类别 legend。多行自动换行。"""
    body_font = "Inter, sans-serif"
    ink = pal["ink"]
    series = _series_colors(pal, max(4, len(options)))
    fs = auto_font_size(len(options), base=12, min_size=9, max_size=13)
    x = cx
    y = cy
    row_h = max(22.0, fs * 1.8)
    right = cx + max_w
    for i, (lbl, cnt) in enumerate(options):
        col = series[i % len(series)]
        # CJK-aware 宽度估算：ASCII/拉丁 ≈ fs * 0.55，CJK ≈ fs * 1.0（一个 em 宽）
        # 原按 ASCII 估算 (len(lbl) * fs * 0.55) 遇 CJK 会低估导致文字压色块
        lbl_str = f"{lbl} {cnt}%"
        _text_w = sum((fs if ord(c) > 127 else fs * 0.55) for c in lbl_str)
        item_w = 20 + _text_w + 20
        if x + item_w > right and x > cx:
            x = cx
            y += row_h
        parts.append(
            f'<rect x="{x}" y="{y}" width="14" height="14" fill="{col}" rx="2"/>'
        )
        parts.append(
            f'<text x="{x + 20}" y="{y + 11}" font-family="{body_font}" '
            f'font-size="{fs}" font-weight="600" fill="{ink}">'
            f'{xesc(lbl)} {cnt}%</text>'
        )
        x += item_w


def _draw_10x10_squares(parts, fills, ML, top_offset, options, pal, width=900):
    body_font = "Inter, sans-serif"
    cell = 30.0
    gap = 4.0
    grid_x = ML + 40
    grid_y = top_offset
    parts.append(
        f'<text x="{grid_x}" y="{grid_y - 14}" font-family="{body_font}" '
        f'font-size="10" fill="{pal["muted"]}" font-weight="600" '
        f'letter-spacing=".18em">ONE SQUARE = 1%</text>'
    )
    for i, fill in enumerate(fills):
        row = i // 10
        col = i % 10
        x = grid_x + col * (cell + gap)
        y = grid_y + row * (cell + gap)
        # shadow
        parts.append(
            f'<rect x="{x + 1:.1f}" y="{y + 1:.1f}" width="{cell}" height="{cell}" '
            f'fill="rgba(0,0,0,0.05)" rx="3"/>'
        )
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" '
            f'fill="{fill}" rx="3"/>'
        )
    # legend 放在主 grid 下方（横向多行），避免右侧巨量留白
    grid_bottom = grid_y + 10 * (cell + gap) - gap
    _draw_legend(parts, options, grid_x, grid_bottom + 30, pal,
                 max_w=10 * (cell + gap) - gap)


def _draw_10x10_dots(parts, fills, ML, top_offset, options, pal, width=900):
    body_font = "Inter, sans-serif"
    cell = 30.0
    gap = 4.0
    grid_x = ML + 40
    grid_y = top_offset
    parts.append(
        f'<text x="{grid_x}" y="{grid_y - 14}" font-family="{body_font}" '
        f'font-size="10" fill="{pal["muted"]}" font-weight="600" '
        f'letter-spacing=".18em">ONE DOT = 1%</text>'
    )
    r = 11.5
    for i, fill in enumerate(fills):
        row = i // 10
        col = i % 10
        cx = grid_x + col * (cell + gap) + cell / 2
        cy = grid_y + row * (cell + gap) + cell / 2
        parts.append(f'<circle cx="{cx + 1:.1f}" cy="{cy + 1:.1f}" r="{r}" fill="rgba(0,0,0,0.05)"/>')
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"/>')
    grid_bottom = grid_y + 10 * (cell + gap) - gap
    _draw_legend(parts, options, grid_x, grid_bottom + 30, pal,
                 max_w=10 * (cell + gap) - gap)


def _draw_10x10_persons(parts, fills, ML, top_offset, options, pal, width=900):
    body_font = "Inter, sans-serif"
    cell = 32.0
    gap = 4.0
    grid_x = ML + 40
    grid_y = top_offset
    parts.append(
        f'<text x="{grid_x}" y="{grid_y - 14}" font-family="{body_font}" '
        f'font-size="10" fill="{pal["muted"]}" font-weight="600" '
        f'letter-spacing=".18em">ONE PERSON = 1%</text>'
    )
    for i, fill in enumerate(fills):
        row = i // 10
        col = i % 10
        cx = grid_x + col * (cell + gap) + cell / 2
        cy = grid_y + row * (cell + gap) + cell / 2
        # 简笔小人
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy - 8.5:.1f}" r="4.2" fill="{fill}"/>'
            f'<path d="M {cx-6:.1f} {cy-3:.1f} '
            f'Q {cx-6:.1f} {cy-6:.1f} {cx-3:.1f} {cy-6:.1f} '
            f'L {cx+3:.1f} {cy-6:.1f} '
            f'Q {cx+6:.1f} {cy-6:.1f} {cx+6:.1f} {cy-3:.1f} '
            f'L {cx+5:.1f} {cy+5:.1f} '
            f'L {cx-5:.1f} {cy+5:.1f} Z" fill="{fill}"/>'
            f'<rect x="{cx-4:.1f}" y="{cy+5:.1f}" width="3" height="7" fill="{fill}"/>'
            f'<rect x="{cx+1:.1f}" y="{cy+5:.1f}" width="3" height="7" fill="{fill}"/>'
        )
    grid_bottom = grid_y + 10 * (cell + gap) - gap
    _draw_legend(parts, options, grid_x, grid_bottom + 30, pal,
                 max_w=10 * (cell + gap) - gap)


def _draw_stacked_row(parts, fills, ML, top_offset, options, pal, width):
    body_font = "Inter, sans-serif"
    grid_x = ML + 40
    grid_y = top_offset + 60
    total_w = width - grid_x - 40
    cell_gap = 0.4
    cell_w = (total_w - 99 * cell_gap) / 100
    # 加高 bar：原 48 → 72，让主体占更多 viewBox 垂直空间
    cell_h = 72.0
    parts.append(
        f'<text x="{grid_x}" y="{grid_y - 14}" font-family="{body_font}" '
        f'font-size="10" fill="{pal["muted"]}" font-weight="600" '
        f'letter-spacing=".18em">ONE UNIT = 1% · SINGLE ROW OF 100</text>'
    )
    for i, fill in enumerate(fills):
        x = grid_x + i * (cell_w + cell_gap)
        parts.append(
            f'<rect x="{x:.2f}" y="{grid_y:.1f}" width="{cell_w:.2f}" height="{cell_h}" '
            f'fill="{fill}" rx="1"/>'
        )
    # 刻度
    ink = pal["ink"]
    muted = pal["muted"]
    for j in range(0, 101, 10):
        x = grid_x + j * (cell_w + cell_gap) - cell_gap / 2
        parts.append(
            f'<line x1="{x:.1f}" y1="{grid_y + cell_h + 3:.1f}" '
            f'x2="{x:.1f}" y2="{grid_y + cell_h + 9:.1f}" '
            f'stroke="{_rgba_with_alpha(ink, 0.5)}" stroke-width="0.6"/>'
        )
        if j in (0, 25, 50, 75, 100):
            parts.append(
                f'<text x="{x:.1f}" y="{grid_y + cell_h + 22:.1f}" text-anchor="middle" '
                f'font-family="{body_font}" font-size="10" fill="{muted}">{j}%</text>'
            )
    # legend 放在刻度下方（灰刻度 baseline y+22，字号 10；下沿 y+24）
    # 与灰刻度字之间留 ≥ 10*0.4 + 视觉呼吸 ≈ 20px（黑体 legend 12pt → 12*0.4=4.8, 但视觉需更大）
    _draw_legend(parts, options, grid_x, grid_y + cell_h + 50, pal, max_w=width - grid_x - 40)


def _draw_faceted(parts, options, remaining, ML, top_offset, pal, series, width, muted_fill):
    body_font = "Inter, sans-serif"
    ink = pal["ink"]
    grid_x = ML + 40
    # 抬高 40 是为给顶部 "ONE DOT = 1% · ..." header 与每个 panel 的 label/百分比
    # 留出充分行高（避免 header text bbox 与 panel title 文字 bbox 相交）。
    grid_y = top_offset + 40
    N = len(options)
    total_avail_w = width - grid_x - 40
    panel_gap = 20.0
    panel_w = (total_avail_w - (N - 1) * panel_gap) / N
    cell_gap = 1.2
    # 上限从 20 → 26，让主体在纵向扩张，减少底部大片留白
    cell_size = min((panel_w - 9 * cell_gap) / 10, 26.0)
    grid_size = 10 * cell_size + 9 * cell_gap
    parts.append(
        f'<text x="{grid_x}" y="{grid_y - 24}" font-family="{body_font}" '
        f'font-size="10" fill="{pal["muted"]}" font-weight="600" '
        f'letter-spacing=".18em">ONE DOT = 1% · FACETED BY CATEGORY</text>'
    )
    for pi, (lbl, cnt) in enumerate(options):
        px0 = grid_x + pi * (panel_w + panel_gap)
        fill = series[pi % len(series)]
        # panel 标题（黑）落在 header（灰）下方 ≥ 12px，避免两者 bbox 相交
        fs_lbl = auto_font_size(N, base=11, min_size=9, max_size=13)
        parts.append(
            f'<text x="{px0:.1f}" y="{grid_y - 2:.1f}" font-family="{body_font}" '
            f'font-size="{fs_lbl}" font-weight="700" fill="{ink}">{xesc(lbl)}</text>'
        )
        parts.append(
            f'<text x="{px0 + panel_w - 4:.1f}" y="{grid_y + 14:.1f}" text-anchor="end" '
            f'font-family="{body_font}" font-size="14" font-weight="700" fill="{fill}">'
            f'{cnt}%</text>'
        )
        # 边框：严格包住 grid（gx0/gy0 起点），并向外扩 3px 视觉留白，
        # 避免 border 与 grid 因 panel 与 grid_size 不等宽而错位。
        gx0 = px0 + (panel_w - grid_size) / 2
        gy0 = grid_y + 26
        parts.append(
            f'<rect x="{gx0 - 3:.1f}" y="{gy0 - 4:.1f}" width="{grid_size + 6:.1f}" '
            f'height="{grid_size + 6:.1f}" fill="none" '
            f'stroke="{_rgba_with_alpha(ink, 0.2)}" stroke-width="0.6" rx="3"/>'
        )
        for i in range(100):
            row = i // 10
            col = i % 10
            cx = gx0 + col * (cell_size + cell_gap) + cell_size / 2
            cy = gy0 + row * (cell_size + cell_gap) + cell_size / 2
            r = cell_size * 0.4
            f = fill if i < cnt else muted_fill
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{f}"/>')


def make_percent_grid(options,
                      title: str = None,
                      subtitle: str = None,
                      figure_label: str = None,
                      figure_note: str = None,
                      footer: str = None,
                      note: str = None,
                      show_breakdown_band: bool = True,
                      show_kpi_row: bool = True,
                      positive_labels=None,
                      negative_labels=None,
                      neutral_label: str = None,
                      width: float = 800.0,
                      height: float = 700.0,
                      font_family: str = None,
                      palette=None,
                variant: str = None) -> str:
    """
    百人网格 / 100-dot infographic (Financial-print academic style).

    参数：
      options: [(label, count_out_of_100), ...] N 类 (2 ≤ N ≤ 8)，counts 求和必须 ≤ 100，
               若 <100 会自动补一个 "Other" 类填齐；>100 raise。
      title / subtitle / figure_label / figure_note: 顶部标题区（可选）
      footer / note: 底部脚注文字（footer 是老 API alias，note 优先）
      show_breakdown_band: 主 grid 底部的横向 100% 累计条（含每段百分比）
      show_kpi_row: 若 positive/negative 分组标签被指定，则显示 POSITIVE / NEUTRAL / NEGATIVE 三个大数字
      positive_labels / negative_labels / neutral_label: 指定按语义分组累计的类别；
        - positive_labels: 类别 label 列表，累计其百分比展示为 POSITIVE 大数字
        - negative_labels: 同上 → NEGATIVE
        - neutral_label:   单一类别 label，展示为 NEUTRAL
      palette: 配色（None/str/dict）

    数据契约：
      - 2 ≤ N ≤ 8
      - 每 count 必须是 [0, 100] 之间的整数；负数或非整数 raise
      - sum(counts) ∈ [0, 100]，>100 raise；< 100 自动补空白类 "—"
    """
    if not _variant_is_classic('percent_grid', variant):
        _data = {"options": list(options)}
        return _dispatch_to_svg_lib(
            'percent_grid', variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    # 页面背景（承接 palette.bg，若无则用白纸感）
    paper = _pal.get("bg", "rgba(250,248,242,1)")

    # ---- 数据规整 ----
    if not options or len(options) < 2:
        raise ValueError("percent_grid: need at least 2 options")
    if len(options) > 8:
        raise ValueError(f"percent_grid: too many options {len(options)} (max 8)")
    labels_norm = []
    counts_norm = []
    for lab, cnt in options:
        if not isinstance(cnt, (int, float)):
            raise ValueError(f"percent_grid: count '{cnt}' must be number")
        if cnt < 0 or cnt > 100:
            raise ValueError(f"percent_grid: count {cnt} out of [0,100] for '{lab}'")
        labels_norm.append(str(lab))
        counts_norm.append(int(round(cnt)))
    tot = sum(counts_norm)
    if tot > 100:
        raise ValueError(f"percent_grid: sum(counts)={tot} > 100")
    if tot < 100:
        labels_norm.append("—")
        counts_norm.append(100 - tot)
    N = len(labels_norm)

    # ---- 派生 N 个类别色（distinct 家族） ----
    series_cols = _derive_series_colors(_pal, N, mode="distinct")
    # 若最后一类是自动补的空白 "—"，用 muted 灰
    if labels_norm[-1] == "—" and sum(counts_norm[:-1]) < 100:
        series_cols[-1] = _rgba_with_alpha(_INK, 0.15)

    # 老 API alias
    if note is None and footer is not None:
        note = footer

    # ---- 画布 ----
    W, H = float(width), float(height)
    MARGIN_L, MARGIN_R = 90.0, 90.0
    MARGIN_T = 155.0 if title or subtitle else 60.0
    MARGIN_B = 90.0

    # ---------- 字号自适应（viewBox + 数据规模双重）----------
    # slide 里 3 图并列 ≈ 400px，viewBox=800 → 缩放 ~0.5x；字号需相应放大
    _n_opts_fs = N
    _fs_base = min(W, H) * 0.022
    if _n_opts_fs <= 4:
        _fs_mult = 1.5
    elif _n_opts_fs <= 8:
        _fs_mult = 1.15
    elif _n_opts_fs <= 15:
        _fs_mult = 0.9
    else:
        _fs_mult = 0.72
    _fs_title    = max(24.0, _fs_base * 2.2)
    _fs_subtitle = max(13.0, _fs_base * 1.1)
    _fs_figure   = max(11.0, _fs_base * 0.95)
    _fs_header   = max(12.0, _fs_base * 1.0)           # ONE SQUARE = 1% / BREAKDOWN
    _fs_breakdown_num = max(14.0, _fs_base * 1.2 * _fs_mult)
    _fs_breakdown_lbl = max(11.0, _fs_base * 0.95 * _fs_mult)
    _fs_kpi_hdr  = max(11.0, _fs_base * 0.9)
    _fs_kpi_big  = max(38.0, _fs_base * 3.4)
    _fs_kpi_sub  = max(11.0, _fs_base * 0.95)
    _fs_legend_hdr = max(12.0, _fs_base * 1.0)
    _fs_legend_lbl = max(12.0, _fs_base * 1.05 * _fs_mult)
    _fs_legend_pct = max(18.0, _fs_base * 1.6 * _fs_mult)
    _fs_note     = max(11.0, _fs_base * 0.95)

    parts = []
    # 页面背景（吃满整张 svg，避免 auto viewBox 因为它是 W/H 而漏掉）
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{paper}"/>')

    # ---- 标题区 ----
    if title:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="52" font-family="{_head_font}" '
                     f'font-size="{_fs_title}" font-weight="600" fill="{_INK}" letter-spacing="0.1">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="76" font-family="{_body_font}" '
                     f'font-size="{_fs_subtitle}" fill="{c_muted}" letter-spacing="0.2">'
                     f'{_xesc(subtitle)}</text>')
    if title or subtitle:
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="92" x2="{W-MARGIN_R:.1f}" y2="92" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="112" font-family="{_body_font}" '
                     f'font-size="{_fs_figure}" fill="{c_muted}" font-weight="600" letter-spacing="1.5">'
                     f'{_xesc(figure_label)}</text>')
    if figure_note:
        offset = 82 if figure_label else 0
        parts.append(f'<text x="{MARGIN_L + offset:.1f}" y="112" font-family="{_body_font}" '
                     f'font-size="{_fs_figure}" fill="{c_muted}" letter-spacing="0.4">'
                     f'{_xesc(figure_note)}</text>')

    # ---- 主 grid 10×10 ----
    GRID_N = 10
    main_cell = 30.0
    main_gap = 4.0
    main_size = GRID_N * main_cell + (GRID_N - 1) * main_gap  # 330
    main_x = MARGIN_L + 20
    main_y = MARGIN_T + 40

    # header 上小标签
    parts.append(f'<text x="{main_x:.1f}" y="{main_y - 12:.1f}" font-family="{_body_font}" '
                 f'font-size="{_fs_header}" fill="{c_muted}" font-weight="600" letter-spacing="1.8">'
                 f'ONE SQUARE = 1%</text>')

    # 填格：按类别顺序左→右、上→下逐个染色
    idx = 0
    for ci, cnt in enumerate(counts_norm):
        col_fill = series_cols[ci]
        for _ in range(cnt):
            row = idx // GRID_N
            col = idx % GRID_N
            x = main_x + col * (main_cell + main_gap)
            y = main_y + row * (main_cell + main_gap)
            # 阴影底
            parts.append(f'<rect x="{x+1:.1f}" y="{y+1:.1f}" width="{main_cell:.1f}" '
                         f'height="{main_cell:.1f}" fill="rgba(0,0,0,0.05)" rx="3"/>')
            # 主色块
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{main_cell:.1f}" '
                         f'height="{main_cell:.1f}" fill="{_rgba_with_alpha(col_fill, 0.92)}" rx="3"/>')
            idx += 1

    # ---- 底部累计条 ----
    if show_breakdown_band:
        band_y = main_y + main_size + 22
        band_h = 26.0
        parts.append(f'<text x="{main_x:.1f}" y="{band_y - 8:.1f}" font-family="{_body_font}" '
                     f'font-size="{_fs_header}" fill="{c_muted}" font-weight="600" letter-spacing="1.4">'
                     f'BREAKDOWN</text>')
        cur_x = main_x
        for ci, cnt in enumerate(counts_norm):
            col_fill = series_cols[ci]
            seg_w = cnt / 100.0 * main_size
            parts.append(f'<rect x="{cur_x:.1f}" y="{band_y:.1f}" width="{seg_w:.1f}" '
                         f'height="{band_h:.1f}" fill="{_rgba_with_alpha(col_fill, 0.92)}"/>')
            # 段内数字：按实际文本宽度判断是否放得下（否则会溢出到相邻段并触发 text_shape_overlap）
            num_str = f"{cnt}%"
            num_w = len(num_str) * _fs_breakdown_num * 0.55  # 数字近似 0.55em/char
            if seg_w >= max(30.0, num_w + 4):
                # 段内数字（用高对比色）
                parts.append(f'<text x="{cur_x + seg_w/2:.1f}" y="{band_y + band_h/2 + 4:.1f}" '
                             f'text-anchor="middle" font-family="{_head_font}" '
                             f'font-size="{_fs_breakdown_num}" font-weight="700" fill="{paper}">{cnt}%</text>')
            cur_x += seg_w
        # 段外描边
        parts.append(f'<rect x="{main_x:.1f}" y="{band_y:.1f}" width="{main_size:.1f}" '
                     f'height="{band_h:.1f}" fill="none" stroke="{_INK4}" stroke-width="0.5"/>')
        # 类别 label（横条下方）
        # 用 CJK-aware 宽度估算 + segment margin，避免窄段的 label 溢出到相邻段。
        cur_x = main_x
        for ci, cnt in enumerate(counts_norm):
            seg_w = cnt / 100.0 * main_size
            lab_str = labels_norm[ci]
            lab_w = sum((_fs_breakdown_lbl if ord(c) > 127 else _fs_breakdown_lbl * 0.55)
                        for c in lab_str)
            # 至少留 4px 左右 padding；宽度不够就不画（避免相邻 label 撞）
            if seg_w > 40 and lab_w + 8 <= seg_w:
                parts.append(f'<text x="{cur_x + seg_w/2:.1f}" y="{band_y + band_h + 15:.1f}" '
                             f'text-anchor="middle" font-family="{_body_font}" '
                             f'font-size="{_fs_breakdown_lbl}" fill="{_INK}" font-weight="600">'
                             f'{_xesc(lab_str)}</text>')
            cur_x += seg_w
    else:
        band_y = main_y + main_size
        band_h = 0.0

    # 用于底部 note 定位：跟踪当前 chart 内容的最低 baseline（含 fs*0.2 下沿）
    _content_bottom_y = band_y + band_h + (18 if show_breakdown_band else 0)

    # ---- POS/NEU/NEG 大数字 KPI 行 ----
    if show_kpi_row and (positive_labels or negative_labels or neutral_label):
        # kpi_y 到底部可用高度：给 header/big/sub 三行 + 两 gap 用。
        # 若 breakdown_band 打开，band label 已经占了 band_y + band_h + ~20，从那之后 20px 起画 kpi。
        # 若关闭 breakdown_band，从主 grid 底部再向下 30px 起画。
        kpi_top = band_y + band_h + (28 if show_breakdown_band else 30)
        kpi_bottom_max = H - MARGIN_B - 4
        avail_h = max(0.0, kpi_bottom_max - kpi_top)

        # 视觉留白（保守值，与 validator bbox 模型一致）
        gap_hb = 6.0
        gap_bs = 8.0

        # 优先用默认 _fs_kpi_big；若 avail_h 装不下 (hdr + gaps + big + sub) 则等比压缩 big 字号
        fs_hdr_used = _fs_kpi_hdr
        fs_sub_used = _fs_kpi_sub
        fs_big_used = _fs_kpi_big
        fixed_h = fs_hdr_used + gap_hb + gap_bs + fs_sub_used  # 非 big 部分
        max_fs_big = max(24.0, avail_h - fixed_h)
        if fs_big_used > max_fs_big:
            fs_big_used = max_fs_big

        kpi_y = kpi_top + fs_hdr_used * 0.8  # header baseline
        kpi_x = main_x
        kpi_slots = []
        label_to_idx = {lab: i for i, lab in enumerate(labels_norm)}
        # POS/NEU/NEG 语义色：优先从 palette 拿语义槽位（accent / muted / secondary），
        # 而不是按 label 在 options 里的 ordinal 位置取 series_cols[idx]。
        # 之前用 series_cols[label_idx]：
        #   1) label 顺序决定 KPI 大数字颜色，POS 可能是绿色、NEG 可能是橙色，反直觉；
        #   2) 若某类 label 不在 options 里，则 fallback 到 _ACC / _INK（模块级硬编码
        #      brown/black），完全无视传入的 palette，就是 issue 里说的
        #      "palette 参数被忽略，一直用内部色"。
        # 现在统一从 pal 语义槽位取，palette 换了 POS/NEU/NEG 就跟着换。
        _pos_col = _pal.get("accent", _ACC)
        _neu_col = c_muted
        _neg_col = _pal.get("secondary", _rgba_with_alpha(_pal["ink"], 0.6))
        if positive_labels:
            pos_sum = sum(counts_norm[label_to_idx[l]] for l in positive_labels if l in label_to_idx)
            pos_sub = " + ".join(positive_labels)
            kpi_slots.append(("POSITIVE", pos_sum, _pos_col, pos_sub))
        if neutral_label and neutral_label in label_to_idx:
            i = label_to_idx[neutral_label]
            kpi_slots.append(("NEUTRAL", counts_norm[i], _neu_col, "no strong opinion"))
        if negative_labels:
            neg_sum = sum(counts_norm[label_to_idx[l]] for l in negative_labels if l in label_to_idx)
            neg_sub = " + ".join(negative_labels)
            kpi_slots.append(("NEGATIVE", neg_sum, _neg_col, neg_sub))
        gap = 30.0
        slot_w = 160.0
        # 3 行 baseline 依据字号推导，避免大数字上下与 header/sub 撞：
        # validator 视 text bbox 为 [baseline - fs*0.8, baseline + fs*0.2]。
        # - header baseline @ kpi_y
        # - big baseline   @ kpi_y + fs_hdr*0.2 + gap_hb + fs_big*0.8
        # - sub  baseline  @ big_baseline + fs_big*0.2 + gap_bs + fs_sub*0.8
        y_hdr_baseline = kpi_y
        y_big_baseline = y_hdr_baseline + fs_hdr_used * 0.2 + gap_hb + fs_big_used * 0.8
        y_sub_baseline = y_big_baseline + fs_big_used * 0.2 + gap_bs + fs_sub_used * 0.8
        for i, (lab, val, col, sub) in enumerate(kpi_slots):
            kx = kpi_x + i * (slot_w + gap)
            parts.append(f'<text x="{kx:.1f}" y="{y_hdr_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_hdr_used}" fill="{c_muted}" font-weight="600" letter-spacing="1.4">'
                         f'{lab}</text>')
            parts.append(f'<text x="{kx:.1f}" y="{y_big_baseline:.1f}" font-family="{_head_font}" '
                         f'font-size="{fs_big_used}" fill="{_rgba_with_alpha(col, 1)}" font-weight="700">'
                         f'{val}%</text>')
            parts.append(f'<text x="{kx:.1f}" y="{y_sub_baseline:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_sub_used}" fill="{c_muted}">{_xesc(sub)}</text>')
        # KPI sub 是 KPI 行最后一行；它的字底沿 = baseline + fs*0.2
        _content_bottom_y = max(_content_bottom_y, y_sub_baseline + fs_sub_used * 0.2)

    # ---- 右侧图例：类别色卡 ----
    # 先估算 legend 宽度，再钳制 lg_x，使 legend 右边缘不越过 W - MARGIN_R。
    # 之前 lg_x = main_x + main_size + 60 硬编码 + _legend_total_w 里的
    # max(70.0, _fs_legend_pct*3.0) 高估百分数字宽度，配合 text-anchor="end"，
    # 在 W=800 时最多溢出 ~56px（slide 11: 856 vs 800）。
    lg_y = main_y + 4
    # 图例宽度：右侧留给 % 数字，label 区宽度按 CJK-aware 估算
    # 拉丁字符 = fs * 0.55；CJK 字符 = fs * 1.0（一个 em 宽）
    def _cjk_aware_w(s, fs, bold=False):
        # validator 对 bold 加 5% 系数（_svg_estimate_character_width bold_multiplier=1.05）；
        # 这里同步，否则 label bbox 与紧邻的 pct 大字 bbox 会相交（差 3-4px）。
        mul = 1.05 if bold else 1.0
        return sum((fs * mul if ord(c) > 127 else fs * 0.55 * mul) for c in s)

    # 若默认字号下 legend 塞不下（label 过长），按可用宽度反解字号
    _lg_x_min = main_x + main_size + 20  # 主 grid 右边至少留 20px gap
    _avail_lg_w = W - MARGIN_R - _lg_x_min
    def _compute_legend_w(fs_lbl, fs_pct):
        # label 走 font-weight="600" bold；pct 走 font-weight="700" bold。
        _mlbl = max((_cjk_aware_w(str(lab), fs_lbl, bold=True) for lab in labels_norm), default=0)
        _sw = max(16.0, fs_lbl * 1.1)
        _mpct_str = max((f"{c}%" for c in counts_norm), key=len, default="0%")
        _pnum = len(_mpct_str) * fs_pct * 0.55 * 1.05 + 4
        return _sw + 8 + _mlbl + 12 + _pnum, _sw, _mlbl, _pnum

    _fs_legend_lbl_used = _fs_legend_lbl
    _fs_legend_pct_used = _fs_legend_pct
    _legend_total_w, _swatch_w, _max_lbl_w, _pct_num_w = _compute_legend_w(
        _fs_legend_lbl_used, _fs_legend_pct_used)
    if _legend_total_w > _avail_lg_w:
        # 按比例整体缩小 legend 字号（保底不小于 9pt 和 12pt）
        shrink = _avail_lg_w / _legend_total_w
        _fs_legend_lbl_used = max(9.0, _fs_legend_lbl_used * shrink)
        _fs_legend_pct_used = max(12.0, _fs_legend_pct_used * shrink)
        _legend_total_w, _swatch_w, _max_lbl_w, _pct_num_w = _compute_legend_w(
            _fs_legend_lbl_used, _fs_legend_pct_used)

    _pct_col_offset = _swatch_w + 8 + _max_lbl_w + 12
    # 行高跟（缩后的）label 字号联动，避免 label 变大后互相压叠
    lg_row_h = max(30.0, _fs_legend_lbl_used * 2.2)

    # lg_x：优先保持 main_x + main_size + 60（右侧留白），
    # 但若 legend 会溢出 viewBox 右边，则回缩到刚好贴到 W - MARGIN_R；
    # 同时不能挤到主 grid（保底 main_x + main_size + 20 的间距）
    _lg_x_preferred = main_x + main_size + 60
    _lg_x_max = W - MARGIN_R - _legend_total_w
    lg_x = max(_lg_x_min, min(_lg_x_preferred, _lg_x_max))
    parts.append(f'<text x="{lg_x:.1f}" y="{lg_y - 12:.1f}" font-family="{_body_font}" '
                 f'font-size="{_fs_legend_hdr}" fill="{c_muted}" font-weight="600" letter-spacing="1.8">'
                 f'CATEGORIES</text>')
    parts.append(f'<line x1="{lg_x:.1f}" y1="{lg_y - 6:.1f}" x2="{lg_x + _legend_total_w:.1f}" '
                 f'y2="{lg_y - 6:.1f}" stroke="{_INK4}" stroke-width="0.6"/>')
    for i, (lab, cnt) in enumerate(zip(labels_norm, counts_norm)):
        row_y = lg_y + i * lg_row_h
        col = series_cols[i]
        parts.append(f'<rect x="{lg_x:.1f}" y="{row_y:.1f}" width="{_swatch_w:.1f}" height="{_swatch_w:.1f}" '
                     f'fill="{_rgba_with_alpha(col, 0.92)}" rx="2"/>')
        parts.append(f'<text x="{lg_x + _swatch_w + 8:.1f}" y="{row_y + _swatch_w*0.75:.1f}" font-family="{_body_font}" '
                     f'font-size="{_fs_legend_lbl_used}" font-weight="600" fill="{_INK}">{_xesc(lab)}</text>')
        # 百分比大字
        parts.append(f'<text x="{lg_x + _legend_total_w:.1f}" y="{row_y + _swatch_w*0.8:.1f}" font-family="{_head_font}" '
                     f'font-size="{_fs_legend_pct_used}" font-weight="700" fill="{_rgba_with_alpha(col, 1)}" '
                     f'text-anchor="end">{cnt}%</text>')
    # legend 最后一行底沿（用于 note 定位）
    _legend_last_row_bottom = lg_y + (len(labels_norm) - 1) * lg_row_h + max(_swatch_w, _fs_legend_pct_used)
    _content_bottom_y = max(_content_bottom_y, _legend_last_row_bottom)

    # ---- 底部脚注 ----
    if note:
        # note baseline 需要在最下方 chart 内容（KPI sub / legend 底沿）之下留出至少
        # max(fs_note * 1.4, 20)px 呼吸空间，否则会和 KPI sub 或 legend 最后一行文字撞。
        # 之前硬编码 H - 32，slide 5/9/11 上刚好和 KPI sub baseline 670.6 只差 2.6px。
        _note_baseline_min = _content_bottom_y + max(_fs_note * 1.4, 20.0)
        # 上限：baseline 加下沿 fs*0.2 不越过 viewBox 底
        _note_baseline_max = H - _fs_note * 0.2 - 2
        foot_y = min(max(H - 32, _note_baseline_min), _note_baseline_max)
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{foot_y - 14:.1f}" x2="{W - MARGIN_R:.1f}" '
                     f'y2="{foot_y - 14:.1f}" stroke="{_INK4}" stroke-width="0.5"/>')
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{foot_y:.1f}" font-family="{_body_font}" '
                     f'font-size="{_fs_note}" fill="{c_muted}">'
                     f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 10) Waterfall 瀑布图
# ==============================================================
