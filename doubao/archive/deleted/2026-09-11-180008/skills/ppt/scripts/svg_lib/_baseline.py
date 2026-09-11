"""svg_lib/_baseline.py

Baseline boxplot & violin generator, extracted from legacy
gen_svg_charts.py (v1) as a self-contained internal module.

Consumers:
  - svg_lib.charts.boxplot
  - svg_lib.charts.violin
"""
#!/usr/bin/env python3
"""
gen_svg_charts.py · 16 张 SVG 高级图表的生成器
按参数生成对应 SVG 字符串（不带 <embed> 外壳，方便模型直接嵌入）。

支持的 chart 类型：
  calheat            日历热力          参数：values（≤ 364 一维）或 matrix（52×7），可选 title/subtitle/kpis/note/source
  ridge              山脊图（多组分布）参数：distributions（N 组，每组是 pdf/hist 数值列表），可选 title/subtitle/highlight_index
  candle             K 线蜡烛图        参数：ohlc（[(open,high,low,close), ...] N 根）
  boxplot            箱线图            参数：groups（[(name, [values...])] N 组）
  sankey             桑基流            参数：left_nodes, right_nodes, flows（守恒自动校验）
  funnel_classic     经典梯形漏斗      参数：stages, stage_labels, stage_descriptions（每层一句描述）
  percent_grid       百人网格          参数：options（[(label, count_out_of_100), ...] 2..8 类），可选 title/subtitle/kpis 语义分组
  waterfall          瀑布图            参数：steps（[(name, value, kind), ...] kind='total'/'pos'/'neg'）
  gantt              甘特图            参数：tasks（[(name, start_week, end_week), ...]）, critical_index, milestones
  population_pyramid 人口金字塔        参数：categories, left_values, right_values，可选 title/kpis/median_index/peak_index/age_group_dividers
  event_timeline     事件时间轴        参数：years, events（[(index, side, title, sub, is_highlight), ...]）
  marimekko          马赛克图          参数：markets（[(name, width_share, [(sub, share), ...]), ...]）
  matrix_heat        矩阵热力          参数：matrix（N×N，传 -1 或 None 的格子会渲染为空白）, labels, highlight_pair
  quadrant_2x2       2×2 象限图        参数：items（[(name, x, y), ...]，x/y ∈ [0,1]）, x_axis, y_axis, x_title, y_title, highlight_index
  violin             小提琴分布        参数：groups（[(name, [values...])] N 组），可选 title/subtitle/y_axis_label/highlight_group/y_min/y_max

命令行用法：
  python3 gen_svg_charts.py --type calheat --matrix-file matrix.json
  python3 gen_svg_charts.py --type ridge --distributions-file dists.json
  python3 gen_svg_charts.py --type candle --ohlc-file ohlc.json --unit '$'
  python3 gen_svg_charts.py --type boxplot --groups-file groups.json --highlight Q3
  python3 gen_svg_charts.py --type sankey --sankey-file sankey.json
  python3 gen_svg_charts.py --type funnel_classic --stages '50,12,8,5,3,1' --labels '全市场,流动性,...' --descriptions '全球可交易品种;日均成交额...'
  python3 gen_svg_charts.py --type percent_grid --grid-file pg.json --footer 'ONE TICK = ONE RESPONDENT'
  python3 gen_svg_charts.py --type waterfall --waterfall-file wf.json
  python3 gen_svg_charts.py --type gantt --gantt-file gt.json
  python3 gen_svg_charts.py --type population_pyramid --pyramid-file pp.json
  python3 gen_svg_charts.py --type event_timeline --timeline-file et.json
  python3 gen_svg_charts.py --type marimekko --marimekko-file mk.json
  python3 gen_svg_charts.py --type matrix_heat --matheat-file mh.json
  python3 gen_svg_charts.py --type quadrant_2x2 --quadrant-file qd.json
  python3 gen_svg_charts.py --type violin --violin-file vl.json

Python 调用：
                              make_funnel_classic, make_percent_grid,
                              make_waterfall, make_gantt, make_population_pyramid,
                              make_event_timeline, make_marimekko,
                              make_matrix_heat, make_quadrant_2x2, make_violin)
  # 然后自己拼 <embed topLeftX=... topLeftY=... width=... height=...>{svg_str}</embed>

配色：所有 make_* 函数都接受统一 `palette` 参数（None / str / dict）。
      str 走 svg_palettes.PALETTES 查表（如 'archive_ink', 'nightlab', 'burgundy_analyst' ...），
      dict 直接传 {'ink', 'accent', 'secondary', 'bg', 'muted'} 五字段。
      None 时用中性默认色（rgba(28,28,26,x) 主色 + rgba(163,88,50,1) accent）。

embed 尺寸：SVG 内部 viewBox 由生成器决定（见 chart_help 里各图的具体尺寸）。
      slide 里 embed 的 topLeftX/Y/width/height 只要 aspect ratio 跟 viewBox 一致就不会裁；
      比例不同会自动从中心裁掉，若要保留某一侧用 <crop anchor="left|right|top|bottom">。
      想图占满整页 → embed 用大尺寸；想「左图右字」→ embed 用小尺寸（如 480×275、640×360）+ 旁边放 <shape type="text">。
"""
import math
import random
import json
import argparse
from typing import List, Sequence

# 默认配色（中性色，供 recolor 二次染色）
_INK  = "rgba(28,28,26,1.0)"
_INK6 = "rgba(28,28,26,0.6)"
_INK4 = "rgba(28,28,26,0.4)"
_INK2 = "rgba(28,28,26,0.2)"
_INK1 = "rgba(28,28,26,0.12)"
_ACC  = "rgba(163,88,50,1.0)"


# ============================================================
# 统一 palette 支持（所有 18 张图共用）
# ============================================================
# palette 参数接受：
#   - None: 用默认硬编码色（等价于 "archive_ink" 或未指定）
#   - str:  从 svg_palettes.PALETTES 查表（如 "burgundy_analyst"）
#   - dict: {"ink", "accent", "secondary", "bg", "muted"} 五字段自定义
# 派生字段（grid/connect/point_fill 等）由 chart 内部按需从 ink/accent 自动派生
def _rgb_prefix(rgba_str):
    """从 rgba(...) 提取 'rgba(r,g,b,' 前缀，方便与自定义 alpha 拼接。"""
    import re as _re
    m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str or "")
    if not m:
        return "rgba(28,28,26,"
    return f"rgba({int(float(m.group(1)))},{int(float(m.group(2)))},{int(float(m.group(3)))},"


def _rgba_with_alpha(rgba_str, alpha):
    """在给定 rgba 上覆盖 alpha 值。"""
    return f"{_rgb_prefix(rgba_str)}{alpha})"


def _resolve_palette(palette):
    """把 palette 参数（None/str/dict）解析为核心配色 dict。

    返回 dict 至少包含：ink, accent, secondary, bg, muted, ink6/4/2/1/12（派生）。
    """
    if palette is None:
        pl = {}
    elif isinstance(palette, dict):
        pl = dict(palette)
    elif isinstance(palette, str):
        try:
            from svg_palettes import PALETTES
        except ImportError:
            import os, sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from svg_palettes import PALETTES
        if palette not in PALETTES:
            raise ValueError(
                f"palette '{palette}' not found. Available: {sorted(PALETTES.keys())}"
            )
        pl = dict(PALETTES[palette])
    else:
        raise TypeError(f"palette must be None / str / dict, got {type(palette).__name__}")

    ink       = pl.get("ink",       _INK)
    accent    = pl.get("accent",    _ACC)
    secondary = pl.get("secondary", _rgba_with_alpha(ink, 0.6))
    bg        = pl.get("bg",        None)  # None = 不渲染背景
    muted     = pl.get("muted",     _rgba_with_alpha(ink, 0.6))

    out = {
        "ink":       ink,
        "accent":    accent,
        "secondary": secondary,
        "bg":        bg,
        "muted":     muted,
        # 派生（沿用旧命名，方便老函数不改逻辑）
        "ink6":      _rgba_with_alpha(ink, 0.6),
        "ink4":      _rgba_with_alpha(ink, 0.4),
        "ink2":      _rgba_with_alpha(ink, 0.2),
        "ink1":      _rgba_with_alpha(ink, 0.12),
        "grid":      pl.get("grid",    _rgba_with_alpha(ink, 0.12)),
        "connect":   pl.get("connect", _rgba_with_alpha(ink, 0.4)),
    }
    # 透传所有未处理的自定义字段（series / domain_default_colors / axis / tick / …）
    for k, v in pl.items():
        if k not in out:
            out[k] = v
    return out


def _prepend_bg_if_dark(svg_str, pal):
    """[已停用] chart SVG 保持透明，由 slide 层承接 palette.bg 作为整页背景。
    保留函数签名为兼容之前的 18 处 return _prepend_bg_if_dark(...) 调用。
    """
    return svg_str


def _rgb_tuple(rgba_str):
    """从 rgba(r,g,b,a) 提取 (r,g,b) 整数元组。"""
    import re as _re
    m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str or "")
    if not m:
        return (28, 28, 26)
    return (int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))))


def _rgb_to_hls(r, g, b):
    """RGB (0-255) → HLS (h in [0,1), l in [0,1], s in [0,1])。用于色相移动派生系列色。"""
    import colorsys
    return colorsys.rgb_to_hls(r/255, g/255, b/255)


def _hls_to_rgba(h, l, s, alpha=1.0):
    """HLS → rgba(...) 字符串。"""
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0, min(1, l)), max(0, min(1, s)))
    return f"rgba({int(r*255)},{int(g*255)},{int(b*255)},{alpha})"


def _derive_series_colors(pal, n, saturation_hint=None, lightness_hint=None, mode="distinct"):
    """基于 palette 的 accent/secondary/ink 派生 n 个系列色（同色系家族），
    可指定 saturation_hint / lightness_hint 让派生色适应深底/浅底 palette。

    优先级：
    1) 若 palette 定义了 `series`（list of rgba），且长度 ≥ n，直接取前 n 个
    2) 若定义了 `series` 但长度不够，循环补齐 + 用 accent 补 accent 位置
    3) 否则：从 accent 出发按 mode 派生 n 个色
       - mode="distinct"（默认）：黄金角 137.5° 大步 hue-shift，相邻互斥。
         用于 donut / sankey / marimekko 等类别图。
       - mode="gradient"：小步 hue-shift + 明度渐变，相邻色接近，
         从冷端渐变到暖端。用于 ridge 等**相邻组有次序**的图。
    """
    if not pal:
        pal = {}
    series = pal.get("series")
    if series and len(series) >= n:
        return list(series[:n])
    if series and len(series) < n:
        base_list = list(series)
        # 循环补齐
        while len(base_list) < n:
            base_list.append(series[len(base_list) % len(series)])
        return base_list

    # 从 accent 出发做 hue-shift
    accent = pal.get("accent", _ACC)
    ar, ag, ab = _rgb_tuple(accent)
    ah, al, asat = _rgb_to_hls(ar, ag, ab)
    if lightness_hint is not None:
        al = lightness_hint
    if saturation_hint is not None:
        asat = saturation_hint
    # 深底 palette（bg 深）时 series 更亮更饱和，浅底 palette 更沉稳
    if pal.get("bg"):
        bg_r, bg_g, bg_b = _rgb_tuple(pal["bg"])
        bg_luma = 0.299 * bg_r + 0.587 * bg_g + 0.114 * bg_b
        if bg_luma < 100 and lightness_hint is None:
            al = max(al, 0.55)  # 深底：颜色更亮
            asat = max(asat, 0.55)
        elif bg_luma > 220 and lightness_hint is None:
            al = min(al, 0.5)   # 浅底：颜色更深

    if mode == "gradient":
        # 渐变模式：色相从 accent 起点，向"补色方向"平滑推进（跨约 240° 色相环），
        # 明度做小幅波动（±0.08）避免完全同色。相邻色差 <30° hue，符合"ridge 邻组相似"直觉。
        if n <= 1:
            return [_hls_to_rgba(ah, al, asat, 1.0)]
        total_span = 0.65  # 覆盖 65% 色相环（约 234°），避免完全绕一圈回到起点
        out = []
        for i in range(n):
            t = i / max(1, n - 1)
            h_new = (ah + t * total_span) % 1.0
            # 明度沿 U 型：起止略暗、中段略亮（让"极端组"稍暗、"中段组"更饱和）
            l_shift = 0.08 * math.sin(t * math.pi)
            out.append(_hls_to_rgba(h_new, al + l_shift, asat, 1.0))
        return out

    # distinct 模式：黄金角，用于类别互斥
    step = 137.508 / 360
    out = [_hls_to_rgba(ah, al, asat, 1.0)]
    for i in range(1, n):
        h_new = (ah + i * step) % 1.0
        l_jitter = al + ((-1) ** i) * 0.05
        out.append(_hls_to_rgba(h_new, l_jitter, asat, 1.0))
    return out


def _xesc(s) -> str:
    """XML 转义所有用户传入的文本（含 & < > 会破坏 SVG）。安全用于 <text> 内容、属性值等。"""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _resolve_font(font_family: str = None) -> tuple[str, str]:
    """把 font_family 参数解析为 (body_font, heading_font) 二元组。

    - None（默认）：保留原设计——body 用 Inter（正文/标签），heading 用 Georgia（大标题/大数字）
    - str：body 与 heading 都用同一字体，全局统一
    """
    if font_family is None or font_family == "":
        return ("Inter, sans-serif", "Georgia, serif")
    return (font_family, font_family)


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
                 palette=None) -> str:
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
    """
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
        # 仅当数据真的落在问卷类 [0,100] 范围时才收敛到该区间（防止 y 轴外扩到 -110% / 200% 之类）。
        # 金融日收益率、变化率等百分比数据可以为负或大于 100，此时 clamp 会把有效数据点
        # 画到 viewBox 外，触发"数据点低于坐标轴最低值"或"高于坐标轴最高值"的视觉 bug。
        if d_min >= 0 and d_max <= 100:
            y_min = max(0, y_min); y_max = min(100, y_max)

    # 画布
    # height 缺省 None：按内容自适应（620 比原 720 少 100px 底部留白）
    if height is None:
        height = 620
    n_groups = len(groups)
    # ---- 字号自适应（先算，因为下方 MARGIN_B 需要 fs_group 决定底部 3 行 label 高度）----
    from ._common import _dist_font_sizes
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
    # 底部 3 行 label（name + n + Mdn）随字号动态放大 → MARGIN_B 也要跟着 fs_group 大。
    _labels_h = max(50.0, fs_group * 1.15 + fs_group * 1.15 + fs_group_n * 1.25 + fs_group_n)
    _footer_gap = max(20.0, fs_group_n)
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

    # 动态 footer 位置：随 labels 末行放，避免 "Mdn X.XXs" 与 "Notes." 横向重叠
    _labels_end_y = (plot_y + plot_h) + _labels_h
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

        # 7) X 标签（3 行）—— 行距按最大字号 * 1.15 预留，避免大字号下重叠
        _gap1 = max(14.0, fs_group * 1.05)      # name → n
        _gap2 = max(13.0, fs_group_n * 1.15)    # n → Mdn
        label_y = plot_y + plot_h + max(22, fs_group * 1.15)
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
            # 估算文字宽（按 fs_legend 缩放）—— 约 0.55 * fs_legend 每字符 + padding
            txt_w = len(label) * fs_legend * 0.55 + fs_legend * 0.8
            x_txt_right = x_cur
            x_txt_left = x_txt_right - txt_w
            # gap 也随字号放大，避免 symbol 与 label 挤到一起
            _sym_gap = max(6.0, fs_legend * 0.5)
            x_sym = x_txt_left - sym_w - _sym_gap
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
            x_cur = x_sym - max(16.0, fs_legend * 1.0)

    # 底部脚注
    if note or source:
        # 分割线与 note baseline 位置随 X 标签末行动态计算，避免 "Mdn X.XXs" 与 "Notes." 重叠
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


def _fmt_axis(v, span):
    """按数据 span 智能格式化数值：整数直接显示；否则按 span 大小选择合适小数位。
    span >= 100 → 整数；span >= 10 → 1 位；span >= 1 → 2 位；否则 3 位。带千分位分隔符。
    """
    if abs(v - round(v)) < 1e-9:
        try:
            return f"{int(round(v)):,}"
        except (OverflowError, ValueError):
            return str(int(round(v)))
    if span >= 100:
        return f"{int(round(v)):,}"
    if span >= 10:
        return f"{v:,.1f}"
    if span >= 1:
        return f"{v:,.2f}"
    return f"{v:,.3f}"


# ==============================================================
# 9) Funnel Classic 经典梯形漏斗
# ==============================================================


def make_violin(groups: Sequence[Sequence],
                y_unit: str = "",
                highlight_group: str = None,
                bandwidth: float = None,
                y_min: float = None,
                y_max: float = None,
                title: str = None,
                subtitle: str = None,
                figure_label: str = None,
                figure_note: str = None,
                y_axis_label: str = None,
                note: str = None,
                source: str = None,
                width: float = 1200.0,
                height: float = None,
                show_boxplot: bool = True,
                show_mean: bool = True,
                show_outliers: bool = True,
                show_legend: bool = True,
                per_group_n: "list[int]" = None,
                font_family: str = None,
                palette=None) -> str:
    """
    小提琴分布图（Academic / Publication Style）：
      - 米白纸底 + 稀疏虚线网格
      - KDE 密度轮廓 + 内嵌 mini boxplot（Q1-Q3 + 中位数 + whiskers）
      - 均值空心圆 + outlier 空心圆
      - 顶部 Title / Subtitle / FIGURE caption
      - 底部 legend（KDE / Q1-Q3 / mean / whiskers / outlier）+ Notes + Source
      - X 轴组名 + n / 中位数副标签

    参数：
      groups: [(name, [values...]), ...] N 组；每组建议 20-500 数值
      y_unit: Y 轴刻度后缀。若为 "%"，Y 轴 clamp 到 [0, 100]
      highlight_group: 组名，用 accent 高亮
      bandwidth: KDE 带宽；None 自动 Silverman
      y_min/y_max: Y 轴范围
      title / subtitle / figure_label / figure_note: 顶部标题
      y_axis_label: Y 轴标题（垂直排布）
      note / source: 底部脚注
      per_group_n: [(n1,n2,...)]，若不传按数据长度自动
      palette: 配色
    """
    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK, _INK6, _INK4, _INK2, _INK1, _ACC = (
        _pal["ink"], _pal["ink6"], _pal["ink4"], _pal["ink2"], _pal["ink1"], _pal["accent"]
    )
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    paper = _pal.get("bg", "rgba(250,248,242,1)")

    if not groups:
        raise ValueError("violin: at least one group required")
    for i, g in enumerate(groups):
        if len(g) < 2 or not g[1]:
            raise ValueError(f"violin: group[{i}] must be (name, [values]) with at least 1 value")

    N = len(groups)
    all_vals = [v for _, vs in groups for v in vs]
    v_min, v_max = min(all_vals), max(all_vals)
    step = max(1e-9, (v_max - v_min) / 5)
    magnitude = 10 ** max(0, int(math.log10(step)))
    tick_step = round(step / magnitude) * magnitude or magnitude
    v_min_floor = math.floor(v_min / tick_step) * tick_step
    v_max_ceil = math.ceil(v_max / tick_step) * tick_step
    v_min_a = v_min_floor
    v_max_a = v_max_ceil
    if v_max_a - v_min_a < tick_step * 0.5:
        v_min_a = v_min_floor - tick_step
        v_max_a = v_max_ceil + tick_step
    if y_unit.strip() == "%":
        # 仅当数据真的落在问卷类 [0,100] 范围时才收敛到该区间。
        # 金融日收益率、变化率等百分比数据可以为负或大于 100，此时 clamp 会把有效数据点
        # 画到 viewBox 外，触发"数据点低于坐标轴最低值"或"高于坐标轴最高值"的视觉 bug。
        if v_min >= 0 and v_max <= 100:
            v_min_a = max(0, v_min_a)
            v_max_a = min(100, v_max_a)
    if y_min is not None: v_min_a = y_min
    if y_max is not None: v_max_a = y_max
    span = v_max_a - v_min_a

    # 派生每组色（distinct 家族）
    series_cols = _derive_series_colors(_pal, N, mode="distinct")

    # ---- 画布布局 ----
    # height 缺省 None：按内容自适应（宽 1200 时约 620px 高，比原 720 省 100px 底部留白）
    if height is None:
        height = 620.0
    W, H = float(width), float(height)

    # ---- 字号自适应（先算：MARGIN_B 需要 fs_group 决定底部 3 行 label 高度）----
    # SVG 字号相对 viewBox。slide 400px embed 缩放后视觉字号会缩到 1/3，
    # 所以基准要拉到短边 2.4%（W=1200,H=620 → base ≈ 14.9pt），保证可读。
    from ._common import _dist_font_sizes
    _fs = _dist_font_sizes(W, H, N)
    fs_title    = _fs["title"]
    fs_subtitle = _fs["subtitle"]
    fs_figure   = _fs["figure"]
    fs_ytick    = _fs["ytick"]
    fs_yaxis    = _fs["yaxis"]
    fs_group    = _fs["group"]
    fs_group_n  = _fs["group_n"]
    fs_side_hdr = _fs["group_n"]
    fs_side_lg  = _fs["legend"]
    fs_ins_ttl  = _fs["group_n"]
    fs_foot     = _fs["foot"]

    MARGIN_L = 110.0
    MARGIN_R = 60.0
    MARGIN_T = 130.0 if (title or subtitle) else 60.0
    # 底部 3 行 X 标签（name + n + median）+ note/source
    _labels_h = max(50.0, fs_group * 1.15 + fs_group * 1.15 + fs_group_n * 1.25 + fs_group_n)
    _footer_gap = max(20.0, fs_group_n)
    _note_block_h = 0.0
    if note or source:
        _note_block_h = _footer_gap + 14.0
        _note_block_h += (fs_foot + 6.0) if note else 0.0
        _note_block_h += (fs_foot + 6.0) if source else 0.0
    MARGIN_B = max(100.0, _labels_h + _note_block_h + 8.0) if (note or source) else max(65.0, _labels_h + 8.0)

    plot_l = MARGIN_L
    plot_r = W - MARGIN_R
    plot_top = MARGIN_T
    plot_bot = H - MARGIN_B
    plot_w = plot_r - plot_l
    plot_h = plot_bot - plot_top

    # 动态 footer 位置（同 boxplot 修复）
    _labels_end_y = plot_bot + _labels_h
    _foot_divider_y = _labels_end_y + _footer_gap
    _foot_note_y = _foot_divider_y + max(14.0, fs_foot)
    _foot_source_y = _foot_note_y + (fs_foot + 6.0 if note else 0.0)

    slot_w = plot_w / N
    half_max_w = min(60.0, slot_w * 0.38)

    def yof(v):
        return plot_bot - (v - v_min_a) / span * plot_h

    parts = []
    # 页面背景
    parts.append(f'<rect x="0" y="0" width="{W:.1f}" height="{H:.1f}" fill="{paper}"/>')

    # ---- 标题 ----
    # 顶部标题 y 位置跟字号联动
    _y_title    = 20 + fs_title
    _y_subtitle = _y_title + fs_title * 0.55 + fs_subtitle
    _y_line     = _y_subtitle + 12
    _y_figure   = _y_line + 14 + fs_figure * 0.5
    if title:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{_y_title:.1f}" font-family="{_head_font}" '
                     f'font-size="{fs_title}" font-weight="600" fill="{_INK}" letter-spacing="0.1">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{_y_subtitle:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_subtitle}" fill="{c_muted}" letter-spacing="0.2">'
                     f'{_xesc(subtitle)}</text>')
    if title or subtitle:
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{_y_line:.1f}" x2="{W-MARGIN_R:.1f}" y2="{_y_line:.1f}" '
                     f'stroke="{_INK}" stroke-width="0.8"/>')
    if figure_label:
        parts.append(f'<text x="{MARGIN_L:.1f}" y="{_y_figure:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_figure}" fill="{c_muted}" font-weight="600" letter-spacing="1.5">'
                     f'{_xesc(figure_label)}</text>')
    if figure_note:
        offset = 70 if figure_label else 0
        parts.append(f'<text x="{MARGIN_L + offset:.1f}" y="{_y_figure:.1f}" font-family="{_body_font}" '
                     f'font-size="{fs_figure}" fill="{c_muted}" letter-spacing="0.4">'
                     f'{_xesc(figure_note)}</text>')

    # ---- Y 轴网格 & 刻度 ----
    tick = v_min_a
    while tick <= v_max_a + 1e-6:
        y = yof(tick)
        is_major = (round((tick - v_min_a) / tick_step) % 2 == 0)
        stroke = _rgba_with_alpha(_INK, 0.14 if is_major else 0.06)
        parts.append(f'<line x1="{plot_l:.1f}" y1="{y:.1f}" x2="{plot_r:.1f}" y2="{y:.1f}" '
                     f'stroke="{stroke}" stroke-width="1"/>')
        parts.append(f'<line x1="{plot_l - 4:.1f}" y1="{y:.1f}" x2="{plot_l:.1f}" y2="{y:.1f}" '
                     f'stroke="{c_muted}" stroke-width="0.8"/>')
        parts.append(f'<text x="{plot_l - 10:.1f}" y="{y + 3:.1f}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="{fs_ytick}" fill="{_INK}">'
                     f'{_fmt_axis(tick, span)}{y_unit}</text>')
        tick += tick_step

    # Y 轴标题（旋转）
    if y_axis_label:
        parts.append(f'<text x="{plot_l - 70:.1f}" y="{plot_top + plot_h / 2:.1f}" '
                     f'transform="rotate(-90 {plot_l - 70:.1f} {plot_top + plot_h / 2:.1f})" '
                     f'text-anchor="middle" font-family="{_body_font}" font-size="{fs_yaxis}" '
                     f'fill="{_INK}" font-weight="500">{_xesc(y_axis_label)}</text>')

    # ---- Gaussian KDE 工具 ----
    def gauss(u):
        return math.exp(-0.5 * u * u) / math.sqrt(2 * math.pi)

    def kde_density(vals, y_samples, bw):
        n = len(vals)
        return [sum(gauss((y - v) / bw) for v in vals) / (n * bw) for y in y_samples]

    def std(vs):
        m = sum(vs) / len(vs)
        return math.sqrt(sum((v - m) ** 2 for v in vs) / max(1, len(vs) - 1))

    def quantile(sorted_xs, q):
        n = len(sorted_xs)
        if n == 0: return 0
        pos = q * (n - 1)
        lo, hi = int(pos), min(int(pos) + 1, n - 1)
        frac = pos - lo
        return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac

    n_samples = 80

    # 先算全组的 max density，用于所有 violin 归一化到同一尺度
    group_stats = []
    global_dmax = 0.0
    for i, (name, vs) in enumerate(groups):
        vs_sorted = sorted(vs)
        n = len(vs_sorted)
        q1 = quantile(vs_sorted, 0.25); q2 = quantile(vs_sorted, 0.5); q3 = quantile(vs_sorted, 0.75)
        iqr = q3 - q1
        lo_w = max(v_min_a, q1 - 1.5 * iqr, min(vs_sorted))
        hi_w = min(v_max_a, q3 + 1.5 * iqr, max(vs_sorted))
        mean_v = sum(vs) / len(vs)
        outliers = [v for v in vs_sorted if v < lo_w or v > hi_w]

        if bandwidth is not None:
            bw = bandwidth
        else:
            sd = std(vs) if n >= 2 else max(1e-6, (v_max - v_min) / 4)
            iqr_scale = max(1e-6, iqr / 1.349) if iqr > 0 else sd
            bw = 0.9 * min(sd if sd > 0 else iqr_scale, iqr_scale) * (n ** (-1.0 / 5)) if n >= 2 else max(1e-6, span * 0.05)
            bw = max(bw, span * 0.015)

        y_lo = max(v_min_a, min(vs) - bw * 2)
        y_hi = min(v_max_a, max(vs) + bw * 2)
        y_samples = [y_lo + k / (n_samples - 1) * (y_hi - y_lo) for k in range(n_samples)]
        density = kde_density(vs, y_samples, bw)
        d_max = max(density) if density else 1e-9
        global_dmax = max(global_dmax, d_max)
        group_stats.append(dict(
            name=name, vs=vs_sorted, n=n, q1=q1, q2=q2, q3=q3,
            lo=lo_w, hi=hi_w, mean=mean_v, outliers=outliers,
            y_samples=y_samples, density=density, d_max=d_max, bw=bw))

    # ---- 每个 violin ----
    for i, s in enumerate(group_stats):
        cx = plot_l + (i + 0.5) * slot_w
        base_col = series_cols[i]
        is_hi = (highlight_group is not None and s["name"] == highlight_group)
        stroke_c = _ACC if is_hi else base_col
        fill_c = _rgba_with_alpha(_ACC, 0.25) if is_hi else _rgba_with_alpha(base_col, 0.2)

        widths = [(half_max_w * d / global_dmax) if (d / global_dmax) > 0.02 else 0.0
                  for d in s["density"]]
        pts_right = [(cx + widths[k], yof(s["y_samples"][k])) for k in range(n_samples)]
        pts_left = [(cx - widths[k], yof(s["y_samples"][k])) for k in range(n_samples - 1, -1, -1)]

        d = f"M {pts_right[0][0]:.2f} {pts_right[0][1]:.2f} "
        for (x, y) in pts_right[1:]:
            d += f"L {x:.2f} {y:.2f} "
        for (x, y) in pts_left:
            d += f"L {x:.2f} {y:.2f} "
        d += "Z"
        parts.append(f'<path d="{d}" fill="{fill_c}" stroke="{stroke_c}" stroke-width="1.1"/>')

        # 内嵌 boxplot
        if show_boxplot:
            y_hi = yof(s["hi"]); y_lo = yof(s["lo"])
            y_q3 = yof(s["q3"]); y_q1 = yof(s["q1"]); y_q2 = yof(s["q2"])
            parts.append(f'<line x1="{cx:.1f}" y1="{y_hi:.1f}" x2="{cx:.1f}" y2="{y_lo:.1f}" '
                         f'stroke="{_INK}" stroke-width="0.8"/>')
            cap_w = half_max_w * 0.28
            for wy in (y_hi, y_lo):
                parts.append(f'<line x1="{cx - cap_w / 2:.1f}" y1="{wy:.1f}" '
                             f'x2="{cx + cap_w / 2:.1f}" y2="{wy:.1f}" '
                             f'stroke="{_INK}" stroke-width="0.8"/>')
            bw2 = half_max_w * 0.22
            parts.append(f'<rect x="{cx - bw2:.1f}" y="{y_q3:.1f}" width="{2 * bw2:.1f}" '
                         f'height="{max(0.5, y_q1 - y_q3):.1f}" fill="{paper}" '
                         f'stroke="{stroke_c}" stroke-width="1"/>')
            parts.append(f'<line x1="{cx - bw2:.1f}" y1="{y_q2:.1f}" x2="{cx + bw2:.1f}" y2="{y_q2:.1f}" '
                         f'stroke="{stroke_c}" stroke-width="2" stroke-linecap="square"/>')

        # 均值
        if show_mean:
            y_mean = yof(s["mean"])
            parts.append(f'<circle cx="{cx:.1f}" cy="{y_mean:.1f}" r="3.2" fill="{paper}" '
                         f'stroke="{_INK}" stroke-width="1.2"/>')
            parts.append(f'<circle cx="{cx:.1f}" cy="{y_mean:.1f}" r="0.9" fill="{_INK}"/>')

        # outliers
        if show_outliers:
            import random as _rand
            _rand.seed(42 + i)
            for v in s["outliers"]:
                if v < v_min_a or v > v_max_a:
                    continue
                py = yof(v)
                jx = cx + (_rand.random() - 0.5) * 5
                parts.append(f'<circle cx="{jx:.1f}" cy="{py:.1f}" r="2.4" fill="none" '
                             f'stroke="{_INK}" stroke-width="1"/>')

        # X 轴组名 + n + 中位数
        # 行距按最大字号 * 1.15 预留，避免大字号下重叠
        _gap1 = max(22.0, fs_group * 1.15)      # name → n
        _gap2 = max(17.0, fs_group_n * 1.25)    # n → Mdn
        label_y = plot_bot + max(22.0, fs_group * 1.15)
        parts.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group}" font-weight="600" '
                     f'fill="{_INK}">{_xesc(s["name"])}</text>')
        n_disp = per_group_n[i] if per_group_n and i < len(per_group_n) else s["n"]
        parts.append(f'<text x="{cx:.1f}" y="{label_y + _gap1:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group_n}" fill="{c_muted}">'
                     f'n = {n_disp}</text>')
        med_fmt = _fmt_axis(s["q2"], span)
        parts.append(f'<text x="{cx:.1f}" y="{label_y + _gap1 + _gap2:.1f}" text-anchor="middle" '
                     f'font-family="{_body_font}" font-size="{fs_group_n}" fill="{c_muted}" '
                     f'font-style="italic">Mdn {med_fmt}{y_unit}</text>')

    # X 轴基线
    parts.append(f'<line x1="{plot_l:.1f}" y1="{plot_bot:.1f}" x2="{plot_r:.1f}" y2="{plot_bot:.1f}" '
                 f'stroke="{_INK}" stroke-width="1"/>')

    # ---- 图例 ----
    if show_legend:
        lg_y = 112
        lg_x = W - MARGIN_R
        # 右起：Outlier / whiskers / mean / Q1-Q3 median / KDE density
        items = []
        if show_outliers: items.append(("Outlier", "outlier"))
        items.append(("±1.5·IQR whiskers", "whisker"))
        if show_mean: items.append(("Mean", "mean"))
        if show_boxplot: items.append(("Q1–Q3 · median", "boxmed"))
        items.append(("KDE density", "kde"))
        x_cur = lg_x
        for lab, sym in items:
            # 估算文字宽度：按 validator 侧的每字符宽度上限估算（宽字符 ~0.9em、窄字符 ~0.55em），
            # 再留出足够 padding，避免 label bbox 与相邻 swatch rect 相交。
            wide_chars = set("QOWMmw–·—")
            est_char = sum(0.90 * fs_side_lg if ch in wide_chars else 0.55 * fs_side_lg for ch in lab)
            txt_w = est_char + fs_side_lg * 0.8
            parts.append(f'<text x="{x_cur:.1f}" y="{lg_y + 3:.1f}" text-anchor="end" '
                         f'font-family="{_body_font}" font-size="{fs_side_lg}" fill="{c_muted}">'
                         f'{_xesc(lab)}</text>')
            # 符号与文字之间保留 gap（随字号 scale）
            sym_x = x_cur - txt_w - max(14.0, fs_side_lg * 1.0)
            if sym == "outlier":
                parts.append(f'<circle cx="{sym_x:.1f}" cy="{lg_y:.1f}" r="2.4" fill="none" '
                             f'stroke="{_INK}" stroke-width="1"/>')
                sym_w = 10
            elif sym == "whisker":
                parts.append(f'<line x1="{sym_x:.1f}" y1="{lg_y - 6:.1f}" x2="{sym_x:.1f}" '
                             f'y2="{lg_y + 6:.1f}" stroke="{_INK}" stroke-width="0.9"/>')
                parts.append(f'<line x1="{sym_x - 4:.1f}" y1="{lg_y - 6:.1f}" x2="{sym_x + 4:.1f}" '
                             f'y2="{lg_y - 6:.1f}" stroke="{_INK}" stroke-width="0.9"/>')
                parts.append(f'<line x1="{sym_x - 4:.1f}" y1="{lg_y + 6:.1f}" x2="{sym_x + 4:.1f}" '
                             f'y2="{lg_y + 6:.1f}" stroke="{_INK}" stroke-width="0.9"/>')
                sym_w = 14
            elif sym == "mean":
                parts.append(f'<circle cx="{sym_x:.1f}" cy="{lg_y:.1f}" r="3.2" fill="{paper}" '
                             f'stroke="{_INK}" stroke-width="1.1"/>')
                parts.append(f'<circle cx="{sym_x:.1f}" cy="{lg_y:.1f}" r="0.8" fill="{_INK}"/>')
                sym_w = 10
            elif sym == "boxmed":
                sc = series_cols[0]
                parts.append(f'<rect x="{sym_x - 4:.1f}" y="{lg_y - 6:.1f}" width="8" height="12" '
                             f'fill="{paper}" stroke="{sc}" stroke-width="0.9"/>')
                parts.append(f'<line x1="{sym_x - 4:.1f}" y1="{lg_y:.1f}" x2="{sym_x + 4:.1f}" '
                             f'y2="{lg_y:.1f}" stroke="{sc}" stroke-width="1.6"/>')
                sym_w = 12
            else:  # kde
                sc = series_cols[0]
                # 迷你 violin
                pts_l, pts_r = [], []
                for k in range(15):
                    t = k / 14.0
                    yy = lg_y - 8 + t * 16
                    d_ = math.exp(-((t - 0.4) ** 2) / (2 * 0.16 ** 2))
                    w = d_ / 1.0 * 6
                    pts_l.append((sym_x - w, yy))
                    pts_r.append((sym_x + w, yy))
                d_str = f'M {pts_l[0][0]:.1f} {pts_l[0][1]:.1f} '
                for (x, y) in pts_l[1:]:
                    d_str += f'L {x:.1f} {y:.1f} '
                for (x, y) in reversed(pts_r):
                    d_str += f'L {x:.1f} {y:.1f} '
                d_str += 'Z'
                parts.append(f'<path d="{d_str}" fill="{_rgba_with_alpha(sc, 0.2)}" '
                             f'stroke="{sc}" stroke-width="0.9"/>')
                sym_w = 16
            x_cur = sym_x - sym_w - max(16.0, fs_side_lg * 1.1)

    # ---- 脚注 ----
    if note or source:
        # 分割线与 note baseline 位置随 X 标签末行动态计算，避免 "Mdn X.XXs" 与 "Notes." 重叠
        foot_y = _foot_note_y
        parts.append(f'<line x1="{MARGIN_L:.1f}" y1="{_foot_divider_y:.1f}" x2="{W - MARGIN_R:.1f}" '
                     f'y2="{_foot_divider_y:.1f}" stroke="{_INK4}" stroke-width="0.5"/>')
        if note:
            parts.append(f'<text x="{MARGIN_L:.1f}" y="{foot_y:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Notes.</tspan> {_xesc(note)}</text>')
        if source:
            y_off = _foot_source_y if note else foot_y
            parts.append(f'<text x="{MARGIN_L:.1f}" y="{y_off:.1f}" font-family="{_body_font}" '
                         f'font-size="{fs_foot}" fill="{c_muted}">'
                         f'<tspan font-weight="600">Source.</tspan> {_xesc(source)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(W)} {int(H)}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 18) Nested Donut 双层甜甜圈（sunburst 2-level）
# ==============================================================


