"""统一 API: draw_candle(data, variant, palette, ...) -> str (SVG)"""

from __future__ import annotations

import math

from .._common import (
    _legacy_inks,
    _dispatch_to_svg_lib,
    _estimate_label_width_px,
    _prepend_bg_if_dark,
    _resolve_font,
    _resolve_palette,
    _rgba_with_alpha,
    _variant_is_classic,
    _xesc,
)
from .._typography import chart_font_sizes
from . import _academic_rigor as rigor
from ._shared import (
    notes_source_footer,
    _header,
    tr,
    resolve_palette,
    svg_close,
    svg_open,
    viewbox_fs,
    xesc,
)

BODY_FONT = "Inter, sans-serif"


# Multi-mode whitelist for ``make_candle``.
#   with_volume : top_bottom_2to1 (main 2/3 K-line, sub 1/3 volume bars).
#                 Trigger: ohlc + volume both provided, equal length, n >= 20.
#                 Validator: raw_values non-empty, equal lengths, n >= 20.
# Dict insertion order defines priority under multi_mode="auto".
def _candle_count_rows(signals):
    return int(signals.get("n", 0))


def _validate_with_volume(signals):
    n = int(signals.get("n", 0))
    nv = int(signals.get("n_vol", 0))
    if n < 20:
        return (False, f"need n>=20 (got {n})")
    if nv != n:
        return (False, f"volume length {nv} != ohlc length {n}")
    return (True, "")


_CANDLE_MULTI_WHITELIST = {
    "with_volume": (
        "top_bottom_2to1",
        lambda s: _candle_count_rows(s) >= 20 and int(s.get("n_vol", 0)) == _candle_count_rows(s),
        lambda s: _validate_with_volume(s),
    ),
}


def draw_candle(
    data: dict,
    variant: str = "candle_american_filled",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str | None = None,
    subtitle: str | None = None,
) -> str:
    ohlc = data.get("ohlc") or []
    if len(ohlc) < 2:
        raise ValueError("draw_candle: need at least 2 ohlc rows")
    date_labels = data.get("date_labels") or [""] * len(ohlc)
    if len(date_labels) != len(ohlc):
        raise ValueError("draw_candle: date_labels length != ohlc length")
    unit = data.get("unit") or ""

    pal = resolve_palette(palette)

    if variant == "heikin_ashi":
        ohlc = _make_heikin_ashi(ohlc)

    ctx = _Ctx(ohlc, date_labels, unit, pal, float(width), float(height), title, subtitle, variant)

    if variant in ("candle_american_filled", "heikin_ashi"):
        body = _draw_candle_filled(ctx)
    elif variant == "candle_japanese_hollow":
        body = _draw_candle_hollow(ctx)
    elif variant == "ohlc_american":
        body = _draw_ohlc_american(ctx)
    elif variant == "line_close":
        body = _draw_line_close(ctx)
    else:
        raise ValueError(
            f"unknown variant {variant!r}. Supported: candle_american_filled, "
            "candle_japanese_hollow, ohlc_american, heikin_ashi, line_close"
        )

    header = _header(ctx)
    axes = _axes(ctx)
    return svg_open(0, 0, ctx.W, ctx.H, bg=pal["bg"]) + header + axes + body + svg_close()


class _Ctx:
    def __init__(self, ohlc, date_labels, unit, pal, W, H, title, subtitle, variant):
        self.ohlc = ohlc
        self.date_labels = date_labels
        self.unit = unit
        self.pal = pal
        self.W = W
        self.H = H
        self.title = title
        self.subtitle = subtitle
        self.variant = variant
        self.n = len(ohlc)

        self.ML = 60
        self.MR = 30
        self.header_h = 20
        if title:
            self.header_h = 44
        if subtitle:
            self.header_h += 18
        self.plot_top = self.header_h + 14
        self.plot_bot = H - 34
        self.plot_w = W - self.ML - self.MR
        self.plot_h = self.plot_bot - self.plot_top

        highs = [row[1] for row in ohlc]
        lows = [row[2] for row in ohlc]
        pmax = max(highs)
        pmin = min(lows)
        pad = (pmax - pmin) * 0.08 or 1.0
        self.pmax = pmax + pad
        self.pmin = pmin - pad

        # up/down colors
        # UP = accent (常为红/暖色)，DOWN = secondary
        self.up_col = pal.get("accent", "rgba(163,88,50,1)")
        self.down_col = pal.get("secondary", "rgba(94,80,62,1)")

        self.fs_axis = viewbox_fs(W, H, self.n, role_mult=0.95)
        self.fs_label = viewbox_fs(W, H, self.n, role_mult=0.85)

    def x_of(self, i):
        if self.n == 1:
            return self.ML + self.plot_w / 2
        return self.ML + (i + 0.5) * (self.plot_w / self.n)

    def y_of(self, p):
        span = self.pmax - self.pmin
        if span <= 0:
            return self.plot_top + self.plot_h / 2
        return self.plot_bot - (p - self.pmin) / span * self.plot_h

    def bar_w(self):
        step = self.plot_w / max(1, self.n)
        return max(1.5, step * 0.62)


def _fmt_tick(v: float) -> str:
    """Y 轴刻度格式：|v| >= 100 → 整数；10 <= |v| < 100 → 1 位小数；|v| < 10 → 2 位小数。"""
    av = abs(v)
    if av >= 100:
        return f"{round(v)}"
    if av >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def _axes(ctx: _Ctx) -> str:
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []

    # y ticks (5 ticks)
    # Bug 1 修复：当 pmax-pmin > 50（|v| 大范围）时，把步长强制为整数，
    # 避免 tick 出现 .5（此时 _fmt_tick 会 round 到 int，丢精度）。
    span = ctx.pmax - ctx.pmin
    if span > 50:
        raw_step = span / 4.0
        y_step = max(1, math.ceil(raw_step))
        y_start = math.ceil(ctx.pmin / y_step) * y_step
    else:
        y_step = None  # fall back to even division
    for i in range(5):
        t = i / 4
        y = ctx.plot_bot - t * ctx.plot_h
        if y_step is not None:
            p = y_start + i * y_step
            y = ctx.y_of(p)
        else:
            p = ctx.pmin + t * (ctx.pmax - ctx.pmin)
        # Bug 1 fix: y_step 模式下 y_start + 4*y_step 可能 > pmax_padded，
        # 导致最顶 tick 的 y 坐标 < plot_top（甚至越过 viewBox 上边）。
        # 只保留落在绘图区内的 tick，其它跳过。
        if y < ctx.plot_top or y > ctx.plot_bot:
            continue
        parts.append(
            f'<line x1="{ctx.ML}" y1="{y:.1f}" x2="{ctx.W - ctx.MR}" y2="{y:.1f}" '
            f'stroke="{ink}" stroke-width="0.4" opacity="0.12"/>'
        )
        parts.append(
            f'<text x="{ctx.ML - 6}" y="{y + 3:.1f}" text-anchor="end" font-family="{BODY_FONT}" '
            f'font-size="{ctx.fs_axis}" fill="{mut}">{_fmt_tick(p)}{xesc(ctx.unit)}</text>'
        )

    parts.append(
        f'<line x1="{ctx.ML}" y1="{ctx.plot_bot}" x2="{ctx.W - ctx.MR}" y2="{ctx.plot_bot}" '
        f'stroke="{ink}" stroke-width="0.6"/>'
    )
    # date labels (only 5-8 evenly spaced)
    n = ctx.n
    n_show = min(8, n)
    step = max(1, n // n_show)
    for i in range(0, n, step):
        x = ctx.x_of(i)
        parts.append(
            f'<text x="{x:.1f}" y="{ctx.plot_bot + 16:.1f}" text-anchor="middle" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_label}" fill="{mut}">'
            f"{xesc(ctx.date_labels[i])}</text>"
        )
    return "".join(parts)


def _draw_candle_filled(ctx: _Ctx) -> str:
    parts = []
    bw = ctx.bar_w()
    for i, row in enumerate(ctx.ohlc):
        o, h, l, c = row[0], row[1], row[2], row[3]
        x = ctx.x_of(i)
        y_o = ctx.y_of(o)
        y_h = ctx.y_of(h)
        y_l = ctx.y_of(l)
        y_c = ctx.y_of(c)
        is_up = c >= o
        col = ctx.up_col if is_up else ctx.down_col
        parts.append(f'<line x1="{x:.1f}" y1="{y_h:.1f}" x2="{x:.1f}" y2="{y_l:.1f}" stroke="{col}" stroke-width="1"/>')
        y_top = min(y_o, y_c)
        y_bot = max(y_o, y_c)
        h_body = max(1.0, y_bot - y_top)
        parts.append(
            f'<rect x="{x - bw / 2:.1f}" y="{y_top:.1f}" width="{bw:.1f}" height="{h_body:.1f}" '
            f'fill="{_rgba_with_alpha(col, 0.92)}"/>'
        )
    return "".join(parts)


def _draw_candle_hollow(ctx: _Ctx) -> str:
    parts = []
    bw = ctx.bar_w()
    paper = ctx.pal["bg"]
    for i, row in enumerate(ctx.ohlc):
        o, h, l, c = row[0], row[1], row[2], row[3]
        x = ctx.x_of(i)
        y_o = ctx.y_of(o)
        y_h = ctx.y_of(h)
        y_l = ctx.y_of(l)
        y_c = ctx.y_of(c)
        is_up = c >= o
        col = ctx.up_col if is_up else ctx.down_col
        parts.append(f'<line x1="{x:.1f}" y1="{y_h:.1f}" x2="{x:.1f}" y2="{y_l:.1f}" stroke="{col}" stroke-width="1"/>')
        y_top = min(y_o, y_c)
        y_bot = max(y_o, y_c)
        h_body = max(1.0, y_bot - y_top)
        if is_up:
            parts.append(
                f'<rect x="{x - bw / 2:.1f}" y="{y_top:.1f}" width="{bw:.1f}" height="{h_body:.1f}" '
                f'fill="{paper}" stroke="{col}" stroke-width="1.2"/>'
            )
        else:
            parts.append(
                f'<rect x="{x - bw / 2:.1f}" y="{y_top:.1f}" width="{bw:.1f}" height="{h_body:.1f}" '
                f'fill="{_rgba_with_alpha(col, 0.92)}"/>'
            )
    return "".join(parts)


def _draw_ohlc_american(ctx: _Ctx) -> str:
    parts = []
    bw = ctx.bar_w()
    tick = max(2.5, bw * 0.55)
    for i, row in enumerate(ctx.ohlc):
        o, h, l, c = row[0], row[1], row[2], row[3]
        x = ctx.x_of(i)
        y_o = ctx.y_of(o)
        y_h = ctx.y_of(h)
        y_l = ctx.y_of(l)
        y_c = ctx.y_of(c)
        is_up = c >= o
        col = ctx.up_col if is_up else ctx.down_col
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_h:.1f}" x2="{x:.1f}" y2="{y_l:.1f}" stroke="{col}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<line x1="{x - tick:.1f}" y1="{y_o:.1f}" x2="{x:.1f}" y2="{y_o:.1f}" stroke="{col}" stroke-width="1.4"/>'
        )
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_c:.1f}" x2="{x + tick:.1f}" y2="{y_c:.1f}" stroke="{col}" stroke-width="1.4"/>'
        )
    return "".join(parts)


def _draw_line_close(ctx: _Ctx) -> str:
    parts = []
    accent = ctx.pal["accent"]
    accent_soft = _rgba_with_alpha(accent, 0.16)
    pts = [(ctx.x_of(i), ctx.y_of(row[3])) for i, row in enumerate(ctx.ohlc)]
    area = f"M {pts[0][0]:.1f} {ctx.plot_bot:.1f} "
    area += " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts)
    area += f" L {pts[-1][0]:.1f} {ctx.plot_bot:.1f} Z"
    parts.append(f'<path d="{area}" fill="{accent_soft}"/>')
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    parts.append(f'<polyline points="{line}" fill="none" stroke="{accent}" stroke-width="2" stroke-linejoin="round"/>')
    if ctx.n <= 30:
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{accent}"/>')
    return "".join(parts)


def _make_heikin_ashi(ohlc):
    """Heikin-Ashi transform."""
    out = []
    for i, row in enumerate(ohlc):
        o, h, l, c = row[0], row[1], row[2], row[3]
        ha_c = (o + h + l + c) / 4.0
        if i == 0:
            ha_o = (o + c) / 2.0
        else:
            ha_o = (out[-1][0] + out[-1][3]) / 2.0
        ha_h = max(h, ha_o, ha_c)
        ha_l = min(l, ha_o, ha_c)
        out.append((ha_o, ha_h, ha_l, ha_c))
    return out


def make_candle(
    ohlc,
    date_labels=None,
    events=None,
    volumes=None,
    volume=None,
    y_unit: str = "$",
    show_ma=True,
    ma_windows=(20, 60),
    show_bollinger=True,
    bollinger_window=20,
    bollinger_k=2,
    show_volume=True,
    show_side_panel=True,
    show_kpi=False,
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source: str | None = None,
    width=1500,
    height=None,
    color_convention: str = "cn",
    font_family: str | None = None,
    palette=None,
    variant: str | None = None,
    multi_mode: str = "auto",
) -> str:
    """
    K 线图 · dandelion academic 风格。

    ohlc: 列表，每项 (open, high, low, close) 或含 volume 的 5 元组
    date_labels: N 个日期标签（可选，自动按等距切月份刻度）
    events: [(idx, title, kind), ...] kind ∈ {"positive","warning","neutral"}
            在指定 bar 上加竖虚线 + 顶部标签
    volumes: N 个成交量（可选；若 ohlc 已含第 5 项 volume，此参数忽略）
    y_unit: 价格前缀（"$", "¥" 等）

    show_ma / ma_windows: 是否叠加移动均线（可传 (20, 60) 两条）
    show_bollinger / bollinger_window / bollinger_k: 布林带
    show_volume: 底部成交量子图
    show_side_panel: 右侧 LEGEND + KEY EVENTS 面板
    show_kpi: 顶部 4 个 KPI 卡片（LAST PRICE / CHANGE / RANGE / VOLUME）；默认关闭——
              RANGE 与 Y 轴重复，学术/汇报页需要时显式 show_kpi=True

    title/subtitle/figure_label/note: 学术风顶/底文字
    palette: 用 accent → up 色 · secondary → down 色，或用户在 palette 指定 up_color/down_color
    """
    if not _variant_is_classic("candle", variant):
        _data = {"ohlc": list(ohlc), "date_labels": date_labels or []}
        return _dispatch_to_svg_lib(
            "candle",
            variant,
            _data,
            title=title,
            subtitle=subtitle,
            figure_label=figure_label,
            palette=palette,
            font_family=font_family,
        )
    if not ohlc:
        raise ValueError("candle: ohlc empty")
    N = len(ohlc)
    # ``volume`` is a canonical alias of ``volumes`` (kept for multi_mode api
    # consistency across charts). If both are provided we prefer ``volume``.
    if volume is not None and volumes is None:
        volumes = volume
    _mm_signals = {
        "n": N,
        "n_vol": len(volumes) if volumes is not None else 0,
    }
    # Build a sentinel BBox from (width x expected plot H ≈ height-240) so we
    # size-gate against the real plot area, not the raw canvas.
    _probe_W = float(width)
    _probe_H = float(height) if height is not None else (820.0 if volumes else 620.0)
    _probe_plot = rigor.bbox_from_edges(
        0.0,
        _probe_W - 60.0,
        110.0,
        _probe_H - 60.0,
    )
    _mm_mode, _mm_template, _mm_reason = rigor.resolve_multi_mode_v2(
        multi_mode,
        _CANDLE_MULTI_WHITELIST,
        _mm_signals,
        _probe_plot,
    )
    # Multi-mode drives the show_volume gate: when the explicit ``with_volume`` requirement is not satisfied we
    # silent-fall-back to single (no volume strip), matching the Phase-2 contract.
    if multi_mode in (None, "single", "off"):
        pass  # leave show_volume as caller specified
    elif _mm_mode == "with_volume":
        show_volume = True  # force sub-panel on
    else:
        # multi_mode="auto" that didn't match → treat as single; keep the
        # historical default (show volume only when volumes exist).
        if multi_mode != "auto":
            show_volume = False
    # Normalize ohlc → 5-tuple with volume
    norm = []
    for i, row in enumerate(ohlc):
        if len(row) < 4:
            raise ValueError(f"candle: ohlc[{i}] must have (o,h,l,c[,v]): {row}")
        o, h, l, c = float(row[0]), float(row[1]), float(row[2]), float(row[3])
        if h < max(o, c) - 1e-6 or l > min(o, c) + 1e-6:
            raise ValueError(f"candle: ohlc[{i}] high/low invalid: h={h} l={l} o={o} c={c}")
        v = None
        if len(row) >= 5 and row[4] is not None:
            v = float(row[4])
        elif volumes is not None and i < len(volumes):
            v = float(volumes[i])
        norm.append((o, h, l, c, v))

    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = _legacy_inks(_pal)
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_secondary = _pal.get("secondary", _rgba_with_alpha(_INK, 0.5))
    c_bg = _pal.get("bg")
    PAPER = c_bg if c_bg else "rgba(247,240,226,1)"
    PANEL = _pal.get("panel", _rgba_with_alpha(_INK, 0.04) if not c_bg else _rgba_with_alpha(_INK, 0.08))

    # up/down 颜色：由 color_convention 决定
    #   "cn"（中国大陆惯例，默认）：红涨 · 绿跌（红火吉利）
    #   "us"（欧美惯例）：绿涨 · 红跌（红色警示）
    # 用户在 palette 里显式指定 up_color / down_color 时以 palette 为准
    _RED_COL = "rgba(152,42,55,1)"  # 波尔多酒红（印刷体）
    _GREEN_COL = "rgba(16,106,82,1)"  # 祖母绿（印刷体）
    if color_convention == "us":
        _default_up, _default_down = _GREEN_COL, _RED_COL
    else:
        _default_up, _default_down = _RED_COL, _GREEN_COL
    UP_COL = _pal.get("up_color", _default_up)
    DOWN_COL = _pal.get("down_color", _default_down)
    MA_SHORT_COL = _pal.get("ma_short_color", _ACC)
    MA_LONG_COL = _pal.get("ma_long_color", c_secondary)
    BOLL_COL = _pal.get("bollinger_color", c_secondary)

    closes = [c[3] for c in norm]

    def sma(series, n):
        """动态窗口 SMA：不足 n 时用截至当前的所有数据。"""
        out = []
        for i in range(len(series)):
            w = min(i + 1, n)
            out.append(sum(series[i - w + 1 : i + 1]) / w)
        return out

    ma_series = [sma(closes, w) for w in ma_windows] if show_ma else []

    boll_up = boll_dn = None
    if show_bollinger and N >= 2:
        bu = [None] * N
        bd = [None] * N
        # 从第一根开始就有值：不足 bollinger_window 时用截至当前的所有数据（动态窗口）
        for i in range(N):
            w = min(i + 1, bollinger_window)
            if w < 2:
                # 只有一个点，无法算 std；用一个极小对称范围避免视觉跳跃
                bu[i] = closes[i]
                bd[i] = closes[i]
                continue
            window = closes[i - w + 1 : i + 1]
            m_ = sum(window) / w
            var = sum((x - m_) ** 2 for x in window) / w
            sd = math.sqrt(var)
            bu[i] = m_ + bollinger_k * sd
            bd[i] = m_ - bollinger_k * sd
        boll_up, boll_dn = bu, bd

    first = norm[0][0]
    last = norm[-1][3]
    chg = last - first
    chg_pct = chg / first * 100 if first != 0 else 0
    period_high = max(c[1] for c in norm)
    period_low = min(c[2] for c in norm)
    all_vols = [c[4] for c in norm if c[4] is not None]
    avg_vol = sum(all_vols) / len(all_vols) if all_vols else None

    # 若用户开了 show_volume 但没提供 volumes 数据，自动关闭（避免底部大片留白）
    if show_volume and not all_vols:
        show_volume = False

    MARGIN_L = 90
    MARGIN_R = 260 if show_side_panel else 60
    # MARGIN_T：title 存在时留 title/subtitle/figure/KPI 区（KPI 高约 70）；无 title 时压缩
    MARGIN_T = 210 if (title and show_kpi) else (160 if title else (110 if show_kpi else 40))
    MARGIN_B = 90 if note else 40
    if source:
        MARGIN_B += 16

    # height 自适应：有 volume 时 820（含底部成交量子图）；无 volume 时 620（只有价格区）
    if height is None:
        height = 820 if show_volume else 620

    fonts = chart_font_sizes(width, height, N)
    price_label_width = max(
        _estimate_label_width_px(f"{y_unit}{value:g}", fonts["ytick"], font_family=_body_font)
        for row in norm
        for value in row[:4]
    )
    MARGIN_L = max(MARGIN_L, price_label_width + 28)
    # Narrow embeds: legend/events flow above the plot instead of a 260px side column.
    side_compact = bool(show_side_panel) and float(width) - MARGIN_L - MARGIN_R < float(width) * 0.6
    if side_compact:
        MARGIN_L = price_label_width + 22
        MARGIN_R = 20
    if not show_side_panel:
        MARGIN_R = max(MARGIN_R, price_label_width + 24)
    MARGIN_B = max(MARGIN_B, fonts["xtick"] * 1.4 + 24 + (32 if note or source else 0))
    plot_x = MARGIN_L
    plot_w = width - MARGIN_L - MARGIN_R
    _fs_scale = max(0.85, min(1.5, max(1, (plot_w - min(4, plot_w / N * 0.15) * (N - 1)) / N) / 17.0))
    fs_kpi_hdr = round(min(11.0, max(10.0, 9 * _fs_scale)), 1)
    fs_kpi_big = round(min(20.0, 15 * _fs_scale), 1)
    fs_kpi_sub = round(min(12.0, max(10.0, 10 * _fs_scale)), 1)
    fs_side_hdr = 11
    fs_side_lg = 12
    kpi_y = 128 if title else 28
    kpi_cols = kpi_rows = 0
    kpi_cell_h = 0
    if side_compact:
        fs_side_lg = 11
        kpi_y = 128 if title else 12
    if show_kpi and side_compact:
        kpi_cols, kpi_rows = 2, math.ceil((4 if all_vols else 3) / 2)
        kpi_cell_h = round(fs_kpi_hdr + fs_side_lg + 12)
        MARGIN_T = kpi_y + kpi_rows * kpi_cell_h + 10
    elif show_kpi:
        n_kpi = 4 if all_vols else 3
        kpi_cell_h = round(22 + fs_kpi_hdr + fs_kpi_big + fs_kpi_sub)
        kpi_need_w = (
            12
            + 8
            + max(
                _estimate_label_width_px(t, fs_kpi_hdr, letter_spacing_em=0.14, bold=True, font_family=_body_font)
                for t in (tr("PERIOD CHANGE"), tr("AVG VOLUME"))
            )
        )
        kpi_need_w = max(
            kpi_need_w,
            20
            + _estimate_label_width_px(
                f"{y_unit}{period_low:.2f} — {y_unit}{period_high:.2f}", fs_kpi_big, bold=True, font_family=_head_font
            ),
        )
        kpi_avail = width - MARGIN_R - MARGIN_L
        kpi_cols = max(1, min(n_kpi, int((kpi_avail + 22) // (kpi_need_w + 22))))
        if kpi_cols < n_kpi and kpi_cols >= 2:
            kpi_cols = 2 if n_kpi == 4 else kpi_cols
        kpi_rows = math.ceil(n_kpi / kpi_cols)
        if kpi_rows > 1 or side_compact:
            MARGIN_T = kpi_y + kpi_rows * kpi_cell_h + (kpi_rows - 1) * 10 + 30
    compact_items = []
    if side_compact:
        compact_items.append(("candle", UP_COL, tr("Up day (close ≥ open)")))
        compact_items.append(("candle", DOWN_COL, tr("Down day (close < open)")))
        if show_ma:
            for mi, w in enumerate(ma_windows):
                compact_items.append(
                    (
                        "line",
                        [MA_SHORT_COL, MA_LONG_COL, _ACC][min(mi, 2)],
                        tr("MA {w} (short-term)" if mi == 0 else "MA {w} (long-term)", w=w),
                    )
                )
        if show_bollinger:
            compact_items.append(("dash", BOLL_COL, tr("Bollinger ({w}, {k}σ)", w=bollinger_window, k=bollinger_k)))
        for ev in events or []:
            if len(ev) >= 2 and 0 <= ev[0] < N:
                kind = ev[2] if len(ev) > 2 else "neutral"
                col = UP_COL if kind == "positive" else (DOWN_COL if kind == "warning" else _ACC)
                o_i, c_i = norm[ev[0]][0], norm[ev[0]][3]
                date_str = (
                    date_labels[ev[0]] if (date_labels and ev[0] < len(date_labels)) else tr("bar {i}", i=ev[0] + 1)
                )
                compact_items.append(
                    ("dot", col, f"{date_str} · {ev[1]} {((c_i - o_i) / o_i * 100 if o_i else 0):+.1f}%")
                )
        flow_x0, flow_x1 = 12, width - 12
        fx, row = flow_x0, 0
        compact_pos = []
        for kind, col, text in compact_items:
            iw = 24 + _estimate_label_width_px(text, fs_side_lg, bold=True, font_family=_body_font)
            if fx > flow_x0 and fx + iw > flow_x1:
                fx, row = flow_x0, row + 1
            compact_pos.append((fx, row))
            fx += iw + 12
        compact_rows = row + 1 if compact_items else 0
        compact_top = MARGIN_T if show_kpi else kpi_y
        MARGIN_T = compact_top + compact_rows * (fs_side_lg + 8) + 14
    GAP_MID = 22
    plot_h_total = height - MARGIN_T - MARGIN_B
    if show_volume:
        price_h = int(plot_h_total * 0.72)
        vol_h = plot_h_total - price_h - GAP_MID
    else:
        price_h = plot_h_total
        vol_h = 0
    price_y = MARGIN_T
    vol_y = price_y + price_h + GAP_MID

    cand_gap = max(1, min(4, plot_w / N * 0.15))
    cand_w = max(1, (plot_w - cand_gap * (N - 1)) / N)

    def x_of(i):
        return plot_x + i * (cand_w + cand_gap) + cand_w / 2

    # 基准：默认 N=60 天、plot_w ≈ 1150 → cand_w ≈ 17px
    # N 少（10-20）时 cand_w 变大 → 字号放大；N 多（100+）时收缩
    _fs_scale = max(0.85, min(1.5, cand_w / 17.0))
    fs_title = round(min(30.0, 26 * _fs_scale), 1)
    fs_subtitle = round(min(14.0, 12 * _fs_scale), 1)
    fs_figure = round(min(12.0, max(10.0, 10 * _fs_scale)), 1)
    fs_yaxis = round(fonts["ytick"], 1)
    fs_xaxis = round(fonts["xtick"], 1)
    fs_vol_hdr = round(min(11.0, max(10.0, 9.5 * _fs_scale)), 1)
    fs_evline = round(min(11.0, max(10.0, 9.5 * _fs_scale)), 1)
    fs_ev_date = 10
    fs_ev_ttl = 12

    # 价格 Y 范围（含 MA、Boll 影响的 padding）
    all_hi = max(c[1] for c in norm)
    all_lo = min(c[2] for c in norm)
    if boll_up:
        vals = [v for v in boll_up if v is not None]
        if vals:
            all_hi = max(all_hi, max(vals))
    if boll_dn:
        vals = [v for v in boll_dn if v is not None]
        if vals:
            all_lo = min(all_lo, min(vals))
    padding = (all_hi - all_lo) * 0.08
    Y_MAX = all_hi + padding
    Y_MIN = all_lo - padding

    def py_of(v):
        return price_y + (Y_MAX - v) / max(Y_MAX - Y_MIN, 1e-6) * price_h

    max_vol = max(all_vols) if all_vols else 1

    def vy_of(v):
        return vol_y + (1 - v / max_vol) * vol_h if vol_h > 0 else vol_y

    parts = []
    if c_bg:
        parts.append(f'<rect width="{width}" height="{height}" fill="{PAPER}"/>')

    if title:
        parts.append(
            f'<text x="{MARGIN_L}" y="52" '
            f'font-family="{_head_font}" '
            f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
            f"{_xesc(title)}</text>"
        )
    if subtitle:
        parts.append(
            f'<text x="{MARGIN_L}" y="76" '
            f'font-family="{_body_font}" font-size="{fs_subtitle}" fill="{c_muted}" '
            f'letter-spacing=".16em">{_xesc(subtitle)}</text>'
        )
        parts.append(f'<line x1="{MARGIN_L}" y1="92" x2="{width - 40}" y2="92" stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(
            f'<text x="{MARGIN_L}" y="112" font-family="{_body_font}" font-size="{fs_figure}" '
            f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>'
        )
        lbl_w = max(72, len(figure_label) * 8 + 20)
        parts.append(
            f'<text x="{MARGIN_L + lbl_w}" y="112" font-family="{_body_font}" font-size="{fs_figure}" '
            f'fill="{c_muted}" letter-spacing=".04em">{_xesc(tr("Candlestick · {n} bars · OHLC + volume", n=N))}</text>'
        )

    if show_kpi:
        chg_color = UP_COL if chg > 0 else DOWN_COL
        chg_arrow = "▲" if chg > 0 else "▼"
        kpis = [
            (tr("LAST PRICE"), f"{y_unit}{last:.2f}", tr("period end")),
            (tr("PERIOD CHANGE"), f"{chg_arrow} {chg_pct:+.1f}%", tr("{value} absolute", value=f"{y_unit}{chg:+.2f}")),
            (
                tr("RANGE"),
                f"{y_unit}{period_low:.2f} — {y_unit}{period_high:.2f}",
                tr("span {value}", value=f"{y_unit}{period_high - period_low:.2f}"),
            ),
        ]
        if avg_vol is not None:
            if avg_vol >= 1e6:
                kpis.append((tr("AVG VOLUME"), f"{avg_vol / 1e6:.2f}M", tr("per bar")))
            elif avg_vol >= 1e3:
                kpis.append((tr("AVG VOLUME"), f"{avg_vol / 1e3:.1f}K", tr("per bar")))
            else:
                kpis.append((tr("AVG VOLUME"), f"{avg_vol:,.0f}", tr("per bar")))
        # 4 卡片均分可用宽
        n_kpi = len(kpis)
        avail_w = width - MARGIN_R - MARGIN_L
        kpi_gap = 22
        kpi_w = (
            min(220, (avail_w - kpi_gap * (kpi_cols - 1)) / kpi_cols)
            if kpi_rows > 1
            else min(220, (avail_w - 22 * (n_kpi - 1)) / n_kpi)
        )
        # rect 高度跟字号联动：header + big + sub + padding
        _pad_top = 8
        _pad_mid = 6
        _pad_bot = 8
        _kpi_h = _pad_top + fs_kpi_hdr + _pad_mid + fs_kpi_big + _pad_mid + fs_kpi_sub + _pad_bot
        _kpi_h = round(_kpi_h)
        kpi_y0 = kpi_y
        col0_w = (
            max(
                [
                    _estimate_label_width_px(f"{b} · {sb}", fs_side_lg, bold=True, font_family=_body_font)
                    for _, b, sb in kpis[::2]
                ]
                + [
                    _estimate_label_width_px(lb, fs_kpi_hdr, letter_spacing_em=0.08, bold=True, font_family=_body_font)
                    for lb, _, _ in kpis[::2]
                ]
            )
            + 24
        )
        for i, (label, big, sub) in enumerate(kpis if side_compact else []):
            kx = 12 + (i % 2) * max((width - 24) / 2, col0_w)
            ky = kpi_y0 + (i // 2) * kpi_cell_h
            parts.append(
                f'<rect x="{kx:.1f}" y="{ky + 2:.1f}" width="3" height="{kpi_cell_h - 6:.1f}" fill="{chg_color if i == 1 else _ACC}"/>'
            )
            parts.append(
                f'<text x="{kx + 9:.1f}" y="{ky + 2 + fs_kpi_hdr * 0.85:.1f}" font-family="{_body_font}" '
                f'font-size="{fs_kpi_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".08em">{_xesc(label)}</text>'
            )
            parts.append(
                f'<text x="{kx + 9:.1f}" y="{ky + 6 + fs_kpi_hdr + fs_side_lg * 0.85:.1f}" font-family="{_body_font}" '
                f'font-size="{fs_side_lg}" font-weight="700" fill="{chg_color if i == 1 else _INK}">{_xesc(big)}'
                f'<tspan font-weight="400" fill="{c_muted}">\u00a0· {_xesc(sub)}</tspan></text>'
            )
        for i, (label, big, sub) in enumerate([] if side_compact else kpis):
            kx = MARGIN_L + (i % kpi_cols) * (kpi_w + kpi_gap)
            kpi_y = kpi_y0 + (i // kpi_cols) * (_kpi_h + 10)
            _y_hdr = kpi_y + _pad_top + fs_kpi_hdr
            _y_big = _y_hdr + _pad_mid + fs_kpi_big
            _y_sub = _y_big + _pad_mid + fs_kpi_sub
            accent_c = chg_color if i == 1 else _ACC
            parts.append(
                f'<rect x="{kx:.1f}" y="{kpi_y}" width="{kpi_w:.1f}" height="{_kpi_h}" fill="{PANEL}" '
                f'stroke="{_INK4}" stroke-width="0.6"/>'
            )
            parts.append(f'<rect x="{kx:.1f}" y="{kpi_y}" width="4" height="{_kpi_h}" fill="{accent_c}"/>')
            parts.append(
                f'<text x="{kx + 12:.1f}" y="{_y_hdr:.1f}" font-family="{_body_font}" '
                f'font-size="{fs_kpi_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">{_xesc(label)}</text>'
            )
            big_col = chg_color if i == 1 else _INK
            parts.append(
                f'<text x="{kx + 12:.1f}" y="{_y_big:.1f}" font-family="{_head_font}" '
                f'font-size="{fs_kpi_big}" fill="{big_col}" font-weight="700">{_xesc(big)}</text>'
            )
            # sub 放在 big 下方（原来是跟 big 同一行右对齐会跟大数字重叠）
            parts.append(
                f'<text x="{kx + 12:.1f}" y="{_y_sub:.1f}" '
                f'font-family="{_body_font}" font-size="{fs_kpi_sub}" fill="{c_muted}">{_xesc(sub)}</text>'
            )

    def _nice_step(span, target=8):
        raw = span / target
        mag = 10 ** math.floor(math.log10(max(raw, 1e-9)))
        for nice in (1, 2, 2.5, 5, 10):
            if raw / mag <= nice:
                return nice * mag
        return 10 * mag

    step = _nice_step(Y_MAX - Y_MIN, target=max(2, min(8, int(price_h / (fs_yaxis * 2.2)))))
    # Bug 1 修复：当价格跨度 > 50 时，step 必须是整数（避免出现 .5 刻度）；
    # 当 step >= 1 时也上取整为整数，防止 nice=2.5 与 mag=1 相乘出现 .5。
    if (Y_MAX - Y_MIN) > 50 or step >= 1:
        step = max(1, math.ceil(step))
    y_ticks = []
    t = math.ceil(Y_MIN / step) * step
    while t <= Y_MAX + 1e-9:
        y_ticks.append(t)
        t += step

    for yv in y_ticks:
        py = py_of(yv)
        parts.append(
            f'<line x1="{plot_x}" y1="{py:.1f}" x2="{plot_x + plot_w}" y2="{py:.1f}" '
            f'stroke="{_rgba_with_alpha(_INK, 0.08)}" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{plot_x - 8}" y="{py + 3.5:.1f}" text-anchor="end" '
            f'font-family="{_body_font}" font-size="{fs_yaxis}" fill="{_INK}">'
            f"{_xesc(f'{y_unit}{yv:g}')}</text>"
        )
        if not show_side_panel:
            parts.append(
                f'<text x="{plot_x + plot_w + 6}" y="{py + 3.5:.1f}" text-anchor="start" '
                f'font-family="{_body_font}" font-size="{fs_yaxis}" fill="{_INK}">{yv:g}</text>'
            )

    if boll_up and boll_dn:
        band_up = [(x_of(i), py_of(boll_up[i])) for i in range(N) if boll_up[i] is not None]
        band_dn = [(x_of(i), py_of(boll_dn[i])) for i in range(N) if boll_dn[i] is not None]
        if band_up and band_dn:
            up_path = " ".join(f"{'L' if k else 'M'} {x:.1f} {y:.1f}" for k, (x, y) in enumerate(band_up))
            dn_path_rev = " ".join(f"L {x:.1f} {y:.1f}" for x, y in reversed(band_dn))
            parts.append(f'<path d="{up_path} {dn_path_rev} Z" fill="{_rgba_with_alpha(BOLL_COL, 0.06)}"/>')
            parts.append(
                f'<path d="{up_path}" fill="none" stroke="{_rgba_with_alpha(BOLL_COL, 0.35)}" '
                f'stroke-width="0.8" stroke-dasharray="2 2"/>'
            )
            dn_path = " ".join(f"{'L' if k else 'M'} {x:.1f} {y:.1f}" for k, (x, y) in enumerate(band_dn))
            parts.append(
                f'<path d="{dn_path}" fill="none" stroke="{_rgba_with_alpha(BOLL_COL, 0.35)}" '
                f'stroke-width="0.8" stroke-dasharray="2 2"/>'
            )

    for i, (o, h, l, c, v) in enumerate(norm):
        cx = x_of(i)
        is_up = c >= o
        col = UP_COL if is_up else DOWN_COL
        parts.append(
            f'<line x1="{cx:.1f}" y1="{py_of(h):.1f}" '
            f'x2="{cx:.1f}" y2="{py_of(l):.1f}" '
            f'stroke="{col}" stroke-width="1"/>'
        )
        top_v = max(o, c)
        bot_v = min(o, c)
        body_h = max(1.2, py_of(bot_v) - py_of(top_v))
        parts.append(
            f'<rect x="{cx - cand_w / 2:.1f}" y="{py_of(top_v):.1f}" '
            f'width="{cand_w:.1f}" height="{body_h:.1f}" '
            f'fill="{_rgba_with_alpha(col, 0.92)}"/>'
        )

    ma_cols = [MA_SHORT_COL, MA_LONG_COL]
    for mi, ma in enumerate(ma_series):
        pts = [(x_of(i), py_of(v)) for i, v in enumerate(ma) if v is not None]
        if not pts:
            continue
        d = " ".join(f"{'L' if k else 'M'} {x:.1f} {y:.1f}" for k, (x, y) in enumerate(pts))
        col = ma_cols[mi] if mi < len(ma_cols) else _ACC
        alpha = 1.0 if mi == 0 else 0.9
        parts.append(f'<path d="{d}" fill="none" stroke="{_rgba_with_alpha(col, alpha)}" stroke-width="1.6"/>')

    if events:
        for ev in events:
            if len(ev) < 2:
                continue
            idx = ev[0]
            ev_title = ev[1]
            kind = ev[2] if len(ev) > 2 else "neutral"
            if idx < 0 or idx >= N:
                continue
            ex = x_of(idx)
            bottom_y = (vol_y + vol_h) if show_volume else (price_y + price_h)
            parts.append(
                f'<line x1="{ex:.1f}" y1="{price_y + 8}" x2="{ex:.1f}" y2="{bottom_y:.1f}" '
                f'stroke="{c_muted}" stroke-width="0.6" stroke-dasharray="3 3"/>'
            )
            ann_col = UP_COL if kind == "positive" else (DOWN_COL if kind == "warning" else _ACC)
            lab_w = max(90, len(str(ev_title)) * 6 + 30)
            parts.append(
                f'<rect x="{ex - lab_w / 2:.1f}" y="{price_y + 2}" width="{lab_w:.1f}" height="18" rx="2" '
                f'fill="{PANEL}" stroke="{_rgba_with_alpha(ann_col, 0.6)}" stroke-width="0.8"/>'
            )
            parts.append(f'<circle cx="{ex - lab_w / 2 + 12:.1f}" cy="{price_y + 11}" r="2.5" fill="{ann_col}"/>')
            parts.append(
                f'<text x="{ex - lab_w / 2 + 20:.1f}" y="{price_y + 15}" font-family="{_body_font}" '
                f'font-size="{fs_evline}" fill="{_INK}" font-weight="600">{_xesc(str(ev_title))}</text>'
            )

    if show_volume and all_vols:
        for f in [0.5, 1.0] if vol_h >= fs_yaxis * 2.4 else [1.0]:
            yv = max_vol * f
            py = vy_of(yv)
            parts.append(
                f'<line x1="{plot_x}" y1="{py:.1f}" x2="{plot_x + plot_w}" y2="{py:.1f}" '
                f'stroke="{_rgba_with_alpha(_INK, 0.05)}" stroke-width="0.5"/>'
            )
            if yv >= 1e6:
                lbl = f"{yv / 1e6:.1f}M"
            elif yv >= 1e3:
                lbl = f"{yv / 1e3:.0f}K"
            else:
                lbl = f"{yv:.0f}"
            parts.append(
                f'<text x="{plot_x - 8}" y="{py + 3.5:.1f}" text-anchor="end" '
                f'font-family="{_body_font}" font-size="{max(10, fs_yaxis - 1)}" fill="{c_muted}">{_xesc(lbl)}</text>'
            )
        for i, (o, h, l, c, v) in enumerate(norm):
            if v is None:
                continue
            cx = x_of(i)
            col = UP_COL if c >= o else DOWN_COL
            top = vy_of(v)
            bot = vy_of(0)
            parts.append(
                f'<rect x="{cx - cand_w / 2:.1f}" y="{top:.1f}" '
                f'width="{cand_w:.1f}" height="{bot - top:.1f}" '
                f'fill="{_rgba_with_alpha(col, 0.55)}"/>'
            )
        parts.append(
            f'<text x="{plot_x}" y="{vol_y - 6}" font-family="{_body_font}" '
            f'font-size="{fs_vol_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">{_xesc(tr("VOLUME"))}</text>'
        )

    bottom_axis_y = (vol_y + vol_h) if show_volume else (price_y + price_h)
    # 若 date_labels 存在：等距抽 6-10 个 tick
    if date_labels:
        widest_date = max(
            _estimate_label_width_px(str(label), fs_xaxis, bold=True, font_family=_body_font) for label in date_labels
        )
        n_show = max(1, min(len(date_labels), 10, int(plot_w / (widest_date + fs_xaxis))))
        tick_positions = (
            [round(i * (len(date_labels) - 1) / (n_show - 1)) for i in range(n_show)] if n_show > 1 else [0]
        )
        for pi in tick_positions:
            xv = x_of(pi)
            lbl = str(date_labels[pi])
            parts.append(
                f'<line x1="{xv:.1f}" y1="{bottom_axis_y}" x2="{xv:.1f}" y2="{bottom_axis_y + 4}" '
                f'stroke="{c_muted}" stroke-width="0.8"/>'
            )
            parts.append(
                f'<text x="{xv:.1f}" y="{bottom_axis_y + fs_xaxis + 9}" text-anchor="middle" '
                f'font-family="{_body_font}" font-size="{fs_xaxis}" font-weight="600" '
                f'fill="{_INK}">{_xesc(lbl)}</text>'
            )
    else:
        # 默认在 5 等分位置
        for i in sorted({int(k * (N - 1) / 5) if N > 1 else 0 for k in range(6)}):
            xv = x_of(i)
            parts.append(
                f'<line x1="{xv:.1f}" y1="{bottom_axis_y}" x2="{xv:.1f}" y2="{bottom_axis_y + 4}" '
                f'stroke="{c_muted}" stroke-width="0.8"/>'
            )
            parts.append(
                f'<text x="{xv:.1f}" y="{bottom_axis_y + fs_xaxis + 9}" text-anchor="middle" '
                f'font-family="{_body_font}" font-size="{fs_xaxis}" font-weight="600" '
                f'fill="{_INK}">{i + 1}</text>'
            )

    parts.append(
        f'<line x1="{plot_x}" y1="{bottom_axis_y}" x2="{plot_x + plot_w}" y2="{bottom_axis_y}" '
        f'stroke="{_INK}" stroke-width="0.9"/>'
    )

    if side_compact:
        for (kind, col, text), (fx, row) in zip(compact_items, compact_pos):
            cy = compact_top + row * (fs_side_lg + 8) + fs_side_lg * 0.6
            if kind == "candle":
                parts.append(
                    f'<line x1="{fx + 8:.1f}" y1="{cy - 8:.1f}" x2="{fx + 8:.1f}" y2="{cy + 8:.1f}" stroke="{col}" stroke-width="1"/>'
                )
                parts.append(
                    f'<rect x="{fx + 5:.1f}" y="{cy - 5:.1f}" width="6" height="10" fill="{_rgba_with_alpha(col, 0.92)}"/>'
                )
            elif kind == "dot":
                parts.append(f'<circle cx="{fx + 8:.1f}" cy="{cy:.1f}" r="3" fill="{col}"/>')
            else:
                dash = ' stroke-dasharray="2 2"' if kind == "dash" else ""
                parts.append(
                    f'<line x1="{fx:.1f}" y1="{cy:.1f}" x2="{fx + 16:.1f}" y2="{cy:.1f}" stroke="{col}" stroke-width="1.8"{dash}/>'
                )
            parts.append(
                f'<text x="{fx + 24:.1f}" y="{cy + fs_side_lg * 0.35:.1f}" font-family="{_body_font}" '
                f'font-size="{fs_side_lg}" font-weight="600" fill="{_INK}">{_xesc(text)}</text>'
            )
    elif show_side_panel:
        side_x = width - MARGIN_R + 30
        side_w = MARGIN_R - 30 - 30

        parts.append(
            f'<text x="{side_x}" y="{MARGIN_T + 10}" font-family="{_body_font}" '
            f'font-size="{fs_side_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">{_xesc(tr("LEGEND"))}</text>'
        )
        parts.append(
            f'<line x1="{side_x}" y1="{MARGIN_T + 18}" x2="{side_x + side_w}" y2="{MARGIN_T + 18}" '
            f'stroke="{_INK}" stroke-width="0.6"/>'
        )

        lg_y = MARGIN_T + 40

        def _sample_candle(sx, sy, color):
            parts.append(f'<line x1="{sx}" y1="{sy - 14}" x2="{sx}" y2="{sy + 14}" stroke="{color}" stroke-width="1"/>')
            parts.append(
                f'<rect x="{sx - 4}" y="{sy - 8}" width="8" height="16" fill="{_rgba_with_alpha(color, 0.92)}"/>'
            )

        _sample_candle(side_x + 8, lg_y, UP_COL)
        parts.append(
            f'<text x="{side_x + 24}" y="{lg_y + 4}" font-family="{_body_font}" '
            f'font-size="{fs_side_lg}" font-weight="600" fill="{_INK}">{_xesc(tr("Up day (close ≥ open)"))}</text>'
        )

        _sample_candle(side_x + 8, lg_y + 32, DOWN_COL)
        parts.append(
            f'<text x="{side_x + 24}" y="{lg_y + 36}" font-family="{_body_font}" '
            f'font-size="{fs_side_lg}" font-weight="600" fill="{_INK}">{_xesc(tr("Down day (close < open)"))}</text>'
        )

        row_i = 2
        if show_ma:
            for mi, w in enumerate(ma_windows):
                col = ma_cols[mi] if mi < len(ma_cols) else _ACC
                y_line = lg_y + 62 + mi * 20
                parts.append(
                    f'<line x1="{side_x + 2}" y1="{y_line}" x2="{side_x + 18}" y2="{y_line}" '
                    f'stroke="{col}" stroke-width="1.8"/>'
                )
                parts.append(
                    f'<text x="{side_x + 24}" y="{y_line + 4}" font-family="{_body_font}" '
                    f'font-size="{fs_side_lg}" font-weight="600" fill="{_INK}">{_xesc(tr("MA {w} (short-term)" if mi == 0 else "MA {w} (long-term)", w=w))}</text>'
                )
            row_i += len(ma_windows)
        if show_bollinger:
            y_line = lg_y + 62 + (len(ma_windows) if show_ma else 0) * 20
            parts.append(
                f'<line x1="{side_x + 2}" y1="{y_line}" x2="{side_x + 18}" y2="{y_line}" '
                f'stroke="{_rgba_with_alpha(BOLL_COL, 0.5)}" stroke-width="0.8" stroke-dasharray="2 2"/>'
            )
            parts.append(
                f'<text x="{side_x + 24}" y="{y_line + 4}" font-family="{_body_font}" '
                f'font-size="{fs_side_lg}" font-weight="600" fill="{_INK}">{_xesc(tr("Bollinger ({w}, {k}σ)", w=bollinger_window, k=bollinger_k))}</text>'
            )

        if events:
            ev_start = lg_y + 62 + ((len(ma_windows) if show_ma else 0) + (1 if show_bollinger else 0)) * 20 + 30
            parts.append(
                f'<text x="{side_x}" y="{ev_start}" font-family="{_body_font}" '
                f'font-size="{fs_side_hdr}" fill="{c_muted}" font-weight="600" letter-spacing=".14em">{_xesc(tr("KEY EVENTS"))}</text>'
            )
            parts.append(
                f'<line x1="{side_x}" y1="{ev_start + 8}" x2="{side_x + side_w}" y2="{ev_start + 8}" '
                f'stroke="{_INK4}" stroke-width="0.5"/>'
            )
            for i, ev in enumerate(events):
                if len(ev) < 2:
                    continue
                idx = ev[0]
                ev_title = ev[1]
                kind = ev[2] if len(ev) > 2 else "neutral"
                col = UP_COL if kind == "positive" else (DOWN_COL if kind == "warning" else _ACC)
                ey = ev_start + 28 + i * 42
                if idx < 0 or idx >= N:
                    continue
                o_i = norm[idx][0]
                c_i = norm[idx][3]
                day_ret = (c_i - o_i) / o_i * 100 if o_i else 0
                parts.append(
                    f'<rect x="{side_x}" y="{ey}" width="{side_w}" height="32" fill="{PANEL}" '
                    f'stroke="{_INK4}" stroke-width="0.5"/>'
                )
                parts.append(f'<rect x="{side_x}" y="{ey}" width="3" height="32" fill="{col}"/>')
                date_str = date_labels[idx] if (date_labels and idx < len(date_labels)) else f"bar {idx + 1}"
                parts.append(
                    f'<text x="{side_x + 10}" y="{ey + 12}" font-family="{_body_font}" '
                    f'font-size="{fs_ev_date}" fill="{c_muted}" font-weight="600" letter-spacing=".1em">'
                    f"{_xesc(str(date_str))}</text>"
                )
                parts.append(
                    f'<text x="{side_x + 10}" y="{ey + 25}" font-family="{_body_font}" '
                    f'font-size="{fs_ev_ttl}" fill="{_INK}" font-weight="700">{_xesc(str(ev_title))}</text>'
                )
                parts.append(
                    f'<text x="{side_x + side_w - 10}" y="{ey + 25}" text-anchor="end" '
                    f'font-family="{_head_font}" font-size="{fs_ev_ttl + 2}" font-weight="700" '
                    f'fill="{col}">{day_ret:+.1f}%</text>'
                )

    parts.append(
        notes_source_footer(
            note,
            source,
            x=MARGIN_L,
            x_right=width - 40,
            y=height - 32,
            rule=_INK4,
            font=_body_font,
            fs="10",
            color=c_muted,
            stack_source=True,
        )
    )

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# 6) Boxplot 箱线图（多组四分位分布）
