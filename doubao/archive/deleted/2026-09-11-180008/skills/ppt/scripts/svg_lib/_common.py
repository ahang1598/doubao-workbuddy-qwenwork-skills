"""svg_lib/_common.py

共享 helper：palette 解析、字体解析、rgb/hls 颜色数学、SVG 骨架 helper（bbox/viewbox）、
标题渲染、label 避让排布。所有 make_* 与 draw_* 都可以复用。
"""
from __future__ import annotations
import math
import re
import colorsys
from typing import Sequence

__all__ = ['_INK', '_INK6', '_INK4', '_INK2', '_INK1', '_ACC', '_rgb_prefix', '_rgba_with_alpha', '_resolve_palette', '_bg_rect_svg', '_is_dark_bg', '_is_dark_palette', '_ink_on_bg', '_punchy_title_ink', '_prepend_bg_if_dark', '_rgb_tuple', '_rgb_to_hls', '_hls_to_rgba', '_lighten_rgba', '_darken_rgba', '_derive_series_colors', '_xesc', '_svg_open', '_svg_close', '_bbox_of_svg_body', '_wrap_with_auto_viewbox', '_resolve_font', '_render_title_block', 'auto_layout_labels', 'ridge_density_from_samples', '_fmt_num', '_fmt_axis', '_svg_close', 'auto_layout_labels', 'ridge_density_from_samples', '_fmt_axis', '_dist_font_sizes', '_SVG_LIB_VARIANTS', '_variant_is_classic', '_dispatch_to_svg_lib', '_estimate_label_width_px']



# ---- 默认色 ----
_INK  = "rgba(28,28,26,1.0)"
_INK6 = "rgba(28,28,26,0.6)"
_INK4 = "rgba(28,28,26,0.4)"
_INK2 = "rgba(28,28,26,0.2)"
_INK1 = "rgba(28,28,26,0.12)"
_ACC  = "rgba(163,88,50,1.0)"


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
            from svg_lib.svg_palettes import PALETTES
        except ImportError:
            import os, sys
            _svg_lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "svg_lib")
            if _svg_lib_dir not in sys.path:
                sys.path.insert(0, _svg_lib_dir)
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
    # 派生 ink_fg: 与 bg 保证对比的前景色。
    # 大部分 palette 已经把 ink 定义为与 bg 相反明度，因此直接沿用 ink；
    # 但少数场景（bg 未定义、ink 与 bg 明度差过小）需要 fallback 到硬编码对比色。
    # 参考 _ink_on_bg(pal_input, prefer_light=None)——但为了避免早期循环依赖，
    # 这里内联判断。
    if bg is not None:
        import re as _re
        _mbg = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', bg)
        _mink = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', ink or "")
        if _mbg and _mink:
            _bl = 0.299*float(_mbg.group(1))+0.587*float(_mbg.group(2))+0.114*float(_mbg.group(3))
            _il = 0.299*float(_mink.group(1))+0.587*float(_mink.group(2))+0.114*float(_mink.group(3))
            if abs(_bl - _il) < 80:  # ink 与 bg 亮度过近 → 用硬编码对比色
                out["ink_fg"] = "rgba(240,235,222,1)" if _bl < 128 else "rgba(28,28,26,1)"
            else:
                out["ink_fg"] = ink
        else:
            out["ink_fg"] = ink
    else:
        out["ink_fg"] = ink
    # 透传所有未处理的自定义字段（series / domain_default_colors / axis / tick / …）
    for k, v in pl.items():
        if k not in out:
            out[k] = v
    return out


def _bg_rect_svg(pal, width, height):
    """若 palette 定义了 bg，则返回一个全图背景 <rect>。"""
    if not pal.get("bg"):
        return ""
    return (f'<rect x="{-2}" y="{-2}" width="{width+4}" height="{height+4}" '
            f'fill="{pal["bg"]}"/>')


def _is_dark_bg(pal):
    """palette 是否需要 chart 自带背景色块（深底 palette 若不加，浅色 ink 文字会消失在白页面上）。"""
    bg = pal.get("bg")
    if not bg:
        return False
    import re as _re
    m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', bg)
    if not m:
        return False
    r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
    luma = 0.299 * r + 0.587 * g + 0.114 * b  # 0-255
    return luma < 180


def _is_dark_palette(pal):
    """Palette bg 是否深色（luma < 128）。用于选择前景对比色。

    与 `_is_dark_bg` 的区别：`_is_dark_bg` 阈值 180 用于判断"是否需要 chart 自绘背景块"；
    这里 128 用于纯粹的深/浅判定（前景色决策）。深浅之间任何模糊值，
    宁可当作浅色对待——因为浅色 chart 上再叠浅色文字只是低对比而不是隐形。
    """
    import re as _re
    m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)',
                  pal.get("bg", "rgba(250,248,242,1)") or "rgba(250,248,242,1)")
    if not m:
        return False
    r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


def _ink_on_bg(pal, prefer_light=None):
    """返回一个"保证与 pal.bg 对比"的前景色。

    - 深 bg：优先 pal.ink（大多数深 palette 已经把 ink 定义为浅色 → 直接用）；
      若 pal.ink 与 bg 同为深色（少见 misconfig），fallback 到硬编码浅色。
    - 浅 bg：同理。

    调用者通常直接用 pal["ink"]；只有当调用点原来硬编码了模块级 _INK（暗色）
    或 rgba(255,255,255,...) 之类的固定色，需要"跟 palette 挂钩"时才用本函数。
    """
    import re as _re
    def _luma(rgba_str):
        m = _re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str or "")
        if not m: return 128.0
        r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return 0.299*r + 0.587*g + 0.114*b
    bg = pal.get("bg", "rgba(250,248,242,1)") or "rgba(250,248,242,1)"
    bg_l = _luma(bg)
    ink = pal.get("ink", _INK)
    ink_l = _luma(ink)
    # 若 ink 与 bg 同"暗/亮"档（luma 差 < 80），说明 palette 配色异常——回退到硬编码对比色
    if abs(ink_l - bg_l) < 80:
        return "rgba(240,235,222,1)" if bg_l < 128 else "rgba(28,28,26,1)"
    return ink


def _prepend_bg_if_dark(svg_str, pal):
    """[已停用] chart SVG 保持透明，由 slide 层承接 palette.bg 作为整页背景。
    保留函数签名为兼容之前的 18 处 return _prepend_bg_if_dark(...) 调用。
    """
    return svg_str


def _punchy_title_ink(pal):
    """返回 chart title 用的"高对比"前景色。

    动机：多数深色 palette 的 ink 是"暖米色/象牙"（如 rgba(240,235,222,1) 之类），
    做正文/次要标签没问题，但用作 chart 大标题（Georgia serif · 20pt · 700）时
    对比不够 punchy——观感偏暗淡。Round 10 测试 8 个深底 palette 都反馈"title 偏暖
    米色不够 punchy"。

    策略：
    - 浅底 palette：直接返回 pal["ink"]（原设计视觉不变，硬规则要求）
    - 深底 palette：向白色靠 ratio，把暖米色拉成 crisp near-white。
      具体 ratio 由 ink 与纯白的距离决定：ink 越暖/越偏离白，ratio 越大。
      结果保持在 rgb 250+ 附近，视觉上是 crisp 白，但保留一丝 palette 暖调不至于冷硬。
    """
    if not _is_dark_palette(pal):
        return pal.get("ink", _INK)
    ink = pal.get("ink", _INK)
    r, g, b = _rgb_tuple(ink)
    # 把 ink 向 255 靠。ratio 0.7 保证结果 rgb 分量 >= ~245，
    # 且各通道差异被压到 <=6，视觉上是 crisp near-white 而非暖米色。
    ratio = 0.7
    r2 = int(r + (255 - r) * ratio)
    g2 = int(g + (255 - g) * ratio)
    b2 = int(b + (255 - b) * ratio)
    return f"rgba({r2},{g2},{b2},1)"


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


def _lighten_rgba(rgba_str, ratio=0.5):
    """rgba 向白色靠 ratio 比例（0.5 = 深主色变淡主色，参考 nested_donut 原逻辑）。"""
    r, g, b = _rgb_tuple(rgba_str)
    r2 = int(r + (255 - r) * ratio)
    g2 = int(g + (255 - g) * ratio)
    b2 = int(b + (255 - b) * ratio)
    return f"rgba({r2},{g2},{b2},1)"


def _darken_rgba(rgba_str, ratio=0.3):
    """rgba 向黑色靠 ratio 比例。"""
    r, g, b = _rgb_tuple(rgba_str)
    r2 = int(r * (1 - ratio))
    g2 = int(g * (1 - ratio))
    b2 = int(b * (1 - ratio))
    return f"rgba({r2},{g2},{b2},1)"


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


def _svg_open(vb_x=0, vb_y=0, vb_w=400, vb_h=300) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x} {vb_y} {vb_w} {vb_h}">'


def _svg_close() -> str:
    return "</svg>"


# ==============================================================
# 基础设施：自动 viewBox + 标签碰撞避让
# ==============================================================


def _dist_font_sizes(vb_w: float, vb_h: float, n_items: int) -> dict:
    """分布类图（boxplot / violin / ridge）的字号自适应。

    动机：SVG 字号相对 viewBox。当 slide 里把 viewBox=1200 宽的图缩到 ~400px
    宽时，viewBox 内 12pt 视觉上只剩 4pt——看不清。所以必须让字号：
      (1) 相对 viewBox 宽度显著放大（body ≥ vb_w/60），保证 embed 后仍可读
      (2) 按数据规模退让：少数据放大、多数据压小（但有底线 10pt）

    经验值（viewBox W=1200）：
      n ≤ 4:  body ≈ 22pt / title ≈ 30pt / group ≈ 23pt
      n ≤ 8:  body ≈ 17pt / title ≈ 23pt / group ≈ 18pt
      n ≤ 15: body ≈ 13pt / title ≈ 18pt / group ≈ 14pt
      n > 15: body ≈ 10pt / title ≈ 14pt / group ≈ 11pt

    对 viewBox W<1200 按 vb_w/60 线性收缩；ridge 的 H 通常远小于 W，用 W 作参考
    比 min(W,H) 更符合 embed 缩放物理（embed 通常按宽度对齐 slide 布局）。

    返回 dict：{title, subtitle, figure, ytick, yaxis, group, group_n, legend,
    foot, label, body}——各字段是相对 viewBox 的字号（浮点，1 位小数）。
    """
    base = float(vb_w) / 60.0  # W=1200 → 20, W=900 → 15
    if n_items <= 4:
        mult = 1.1
    elif n_items <= 8:
        mult = 0.85
    elif n_items <= 15:
        mult = 0.66
    else:
        mult = 0.5
    body = max(10.0, base * mult)  # 底线 10pt
    return {
        "title":    round(body * 1.35, 1),   # 大标题
        "subtitle": round(body * 0.9, 1),    # 副标题
        "figure":   round(body * 0.8, 1),    # figure_label / figure_note
        "ytick":    round(body * 0.9, 1),    # y 轴刻度
        "yaxis":    round(body * 0.95, 1),   # y 轴 label
        "group":    round(body * 1.05, 1),   # x 轴 组名主标签
        # boxplot/violin/ridge 的 "n = X" 与 "Mdn X" 是 secondary label，
        # 系数 0.95 + floor 11pt 保证 embed 到 slide 小窗口时仍可读
        "group_n":  round(max(11.0, body * 0.95), 1),
        # legend 里 4-5 项水平并排、每项 15-20 字符——若 fs 跟 body 一起拉到 22pt
        # 会把 lg_x 挤到左边，直接盖住标题或超出画布。所以给 legend 单独限一个较低上限。
        "legend":   round(min(15.0, body * 0.7), 1),
        "foot":     round(body * 0.8, 1),    # 底部脚注
        "label":    round(body * 1.0, 1),    # 通用文字标签（ridge 组名）
        "body":     round(body, 1),          # 兜底
    }


# ---- Per-glyph label width estimator ----
# Mirrors embed_svg_validator._svg_text_width so make_*/draw_* can reserve exactly
# the horizontal room the validator will later measure. Under-estimating margins
# was what let R6 academic ridge labels ("CLAUDE 3.5 SONNET", "GEMINI 2.5 PRO")
# overflow the viewBox by 40-113px even after the "0.62 * fs" heuristic.
#
# Coefficients are copied verbatim from embed_svg_validator so the two stay in
# lock-step. If validator gets re-tuned, update both sides.
_LABEL_WIDE_LETTER_RATIOS = {
    "m": 0.90, "w": 0.78, "M": 0.90, "W": 0.98,
    "G": 0.78, "O": 0.78, "Q": 0.78,
    "A": 0.72, "B": 0.66, "C": 0.72, "D": 0.72, "H": 0.72, "K": 0.66,
    "N": 0.72, "P": 0.66, "R": 0.72, "U": 0.72, "X": 0.66, "Z": 0.62,
}
_LABEL_WIDE_SYMBOL_RATIOS = {
    "@": 1.0, "&": 0.67, "$": 0.56, "¥": 0.56, "£": 0.56, "¢": 0.56,
    "#": 0.56, "~": 0.58, "+": 0.58, "=": 0.58, "<": 0.58, ">": 0.58,
}
_LABEL_FONT_CATEGORY = {
    "sans":       {"upper": 0.57, "lower": 0.51, "digit": 0.58, "punct": 0.50},
    "serif":      {"upper": 0.57, "lower": 0.53, "digit": 0.58, "punct": 0.50},
    "wide-sans":  {"upper": 0.62, "lower": 0.58, "digit": 0.63, "punct": 0.53},
}
_LABEL_WIDE_SANS_MARKERS = (
    "montserrat", "poppins", "futura", "century gothic", "gotham",
    "raleway", "nunito", "quicksand", "josefin", "comfortaa",
)
_LABEL_SERIF_MARKERS = (
    "song", "songti", "simsun", "ming", "mincho",
    "georgia", "times", "caslon", "garamond", "sourcehan-serif",
    "source han serif", "思源宋体", "宋体", "明体", "serif",
)


def _label_font_category(font_family):
    if not font_family:
        return "sans"
    fl = font_family.lower()
    for m in _LABEL_WIDE_SANS_MARKERS:
        if m in fl:
            return "wide-sans"
    for m in _LABEL_SERIF_MARKERS:
        if m in fl:
            return "serif"
    return "sans"


def _estimate_label_width_px(text, font_size, letter_spacing_em=0.0, bold=False, font_family=None):
    """Estimate rendered text width in px, matching embed_svg_validator._svg_text_width.

    text:              the label string (already upper()-cased if the caller
                       will render uppercase).
    font_size:         SVG font-size in user units.
    letter_spacing_em: e.g. 0.08 for `letter-spacing=".08em"`. 0 if none.
    bold:              True for font-weight >= 600.
    font_family:       used to pick the coefficient table.

    Return value is a **conservative** estimate — validator uses the same
    formula, so if the caller reserves at least this much room the label will
    not be flagged as out-of-bounds.
    """
    if not text:
        return 0.0
    bold_mul = 1.05 if bold else 1.0
    coeffs = _LABEL_FONT_CATEGORY[_label_font_category(font_family)]
    # Mirror embed_svg_validator._svg_is_cjk_char: CJK glyphs are full-width (fs * 1.0),
    # not punctuation-width. Without this, `能源供应` (4 CJK chars @ fs=22.8) is estimated at
    # ~48px while the validator sees ~96px — half the reserved space, causing the label to
    # collide with any shape whose bbox lies just outside where the caller placed it.
    def _is_cjk(code):
        return (
            0x2E80 <= code <= 0x9FFF
            or 0x3000 <= code <= 0xD7AF
            or 0xF900 <= code <= 0xFAFF
            or 0xFE30 <= code <= 0xFE4F
            or 0xFF01 <= code <= 0xFF60
            or 0xFFE0 <= code <= 0xFFE6
        )
    width = 0.0
    for ch in text:
        if ch.isspace():
            width += font_size * 0.33 * bold_mul
            continue
        if _is_cjk(ord(ch)):
            width += font_size * bold_mul
            continue
        if ch == "%":
            width += font_size * 0.85 * bold_mul
            continue
        sym_ratio = _LABEL_WIDE_SYMBOL_RATIOS.get(ch)
        if sym_ratio is not None:
            width += font_size * sym_ratio * bold_mul
            continue
        wide_letter = _LABEL_WIDE_LETTER_RATIOS.get(ch)
        if wide_letter is not None:
            cat_ratio = coeffs["upper"] if ch.isupper() else coeffs["lower"]
            width += font_size * max(wide_letter, cat_ratio) * bold_mul
            continue
        if ch.isupper():
            width += font_size * coeffs["upper"] * bold_mul
        elif ch.islower():
            width += font_size * coeffs["lower"] * bold_mul
        elif ch.isdigit():
            width += font_size * coeffs["digit"] * bold_mul
        else:
            width += font_size * coeffs["punct"] * bold_mul
    # letter-spacing is applied between glyphs (n-1 gaps)
    width += max(len(text) - 1, 0) * letter_spacing_em * font_size
    return width


def _bbox_of_svg_body(body: str) -> tuple:
    """扫描已经拼好的 SVG 内容（不含外层 <svg>），返回 (x_min, y_min, w, h) 真实包围盒。
    考虑：line/rect/circle/ellipse 坐标、path d 里的坐标、<text> 按 font-size × 字符数 × text-anchor × rotation 估位置。
    """
    import re as _re
    xs, ys = [], []
    for m in _re.finditer(r'\b(?:x1|x2|cx)="([-\d.]+)"', body):
        xs.append(float(m.group(1)))
    for m in _re.finditer(r'\b(?:y1|y2|cy)="([-\d.]+)"', body):
        ys.append(float(m.group(1)))
    # rect 加宽高
    for m in _re.finditer(r'<rect\b([^>]*)/?>', body):
        a = m.group(1)
        xm = _re.search(r'\bx="([-\d.]+)"', a)
        ym = _re.search(r'\by="([-\d.]+)"', a)
        wm = _re.search(r'\bwidth="([-\d.]+)"', a)
        hm = _re.search(r'\bheight="([-\d.]+)"', a)
        if xm and ym and wm and hm:
            x, y, w, h = float(xm.group(1)), float(ym.group(1)), float(wm.group(1)), float(hm.group(1))
            xs += [x, x + w]; ys += [y, y + h]
    # path d
    for m in _re.finditer(r'd="([^"]+)"', body):
        nums = list(map(float, _re.findall(r'-?\d+\.?\d*', m.group(1))))
        for i, v in enumerate(nums):
            (xs if i % 2 == 0 else ys).append(v)
    # circle 加半径
    for m in _re.finditer(r'<circle\b[^>]*cx="([-\d.]+)"[^>]*cy="([-\d.]+)"[^>]*r="([-\d.]+)"', body):
        cx, cy, rr = float(m.group(1)), float(m.group(2)), float(m.group(3))
        xs += [cx - rr, cx + rr]; ys += [cy - rr, cy + rr]
    # text 外扩：font-size × 字符数 × text-anchor × rotation
    for m in _re.finditer(r'<text\b([^>]*)>([^<]*)</text>', body):
        attrs, text = m.group(1), m.group(2)
        xm = _re.search(r'\bx="([-\d.]+)"', attrs)
        ym = _re.search(r'\by="([-\d.]+)"', attrs)
        fsm = _re.search(r'font-size="([-\d.]+)"', attrs)
        am = _re.search(r'text-anchor="(start|middle|end)"', attrs)
        wm = _re.search(r'font-weight="([-\d.]+|bold)"', attrs)
        lsm = _re.search(r'letter-spacing="([-\d.]+)(?:em|px|)?"', attrs)
        rotm = _re.search(r'transform="[^"]*rotate\(\s*(-?[\d.]+)(?:\s+(-?[\d.]+)\s+(-?[\d.]+))?\s*\)', attrs)
        if not (xm and ym):
            continue
        x, y = float(xm.group(1)), float(ym.group(1))
        fs = float(fsm.group(1)) if fsm else 12.0
        anchor = am.group(1) if am else "start"
        wt = wm.group(1) if wm else "400"
        wf = 1.15 if (wt == "bold" or (wt.isdigit() and int(wt) >= 600)) else 1.0
        ls_px = float(lsm.group(1)) * fs if lsm else 0.0
        n_ascii = sum(1 for c in text if ord(c) < 128)
        n_cjk = len(text) - n_ascii
        text_w = (n_ascii * fs * 0.7 + n_cjk * fs * 1.1) * wf
        text_w += max(0, len(text) - 1) * ls_px + max(3, fs * 0.2)
        if anchor == "start":  x1, x2 = -2, text_w
        elif anchor == "end":  x1, x2 = -text_w, 2
        else:                  x1, x2 = -text_w/2 - 2, text_w/2 + 2
        y1, y2 = -fs * 1.1, fs * 0.35
        corners = [(x + x1, y + y1), (x + x2, y + y1), (x + x2, y + y2), (x + x1, y + y2)]
        if rotm:
            deg = float(rotm.group(1))
            cx, cy = (float(rotm.group(2)), float(rotm.group(3))) if rotm.group(2) else (0.0, 0.0)
            rad = math.radians(deg)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            corners = [(cx + (px-cx)*cos_r - (py-cy)*sin_r, cy + (px-cx)*sin_r + (py-cy)*cos_r) for (px, py) in corners]
        for px, py in corners:
            xs.append(px); ys.append(py)
    if not xs or not ys:
        return (0.0, 0.0, 400.0, 300.0)
    x_min, y_min = min(xs), min(ys)
    return (x_min, y_min, max(xs) - x_min, max(ys) - y_min)


def _wrap_with_auto_viewbox(body: str, extra_pad: float = 8.0) -> str:
    """把 body 拼成完整 SVG，viewBox 按内容真实包围盒 + padding 计算。"""
    x_min, y_min, w, h = _bbox_of_svg_body(body)
    pad = max(extra_pad, min(w, h) * 0.03)
    vb = f"{x_min - pad:.1f} {y_min - pad:.1f} {w + 2*pad:.1f} {h + 2*pad:.1f}"
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{body}</svg>'


def _resolve_font(font_family: str = None) -> tuple[str, str]:
    """把 font_family 参数解析为 (body_font, heading_font) 二元组。

    - None（默认）：保留原设计——body 用 Inter（正文/标签），heading 用 Georgia（大标题/大数字）
    - str：body 与 heading 都用同一字体，全局统一
    """
    if font_family is None or font_family == "":
        return ("Inter, sans-serif", "Georgia, serif")
    return (font_family, font_family)
def _render_title_block(x_left: float, anchor_y: float, width: float,
                        title: str = None, subtitle: str = None,
                        figure_label: str = None,
                        ink: str = None, muted: str = None,
                        title_font_size: float = 22,
                        subtitle_font_size: float = 10,
                        figure_font_size: float = 9,
                        body_font: str = "Inter, sans-serif",
                        heading_font: str = "Inter, sans-serif") -> tuple[str, float]:
    """为"由 _wrap_with_auto_viewbox 自动算 viewBox 的图种"渲染顶部标题栏。

    风格对齐 make_ridge：默认无衬线字体、title 22pt/700/.02em、subtitle 10pt/600/.16em、
    figure_label 9pt/600/.15em；无分割线，简洁克制。

    body_font / heading_font: 字体分工。title 用 heading_font；subtitle & figure_label 用 body_font。
    默认都用无衬线（跟原 ridge 一样，无 font-family 时浏览器默认 sans）——外层函数会传入解析后的值。
    """
    ink = ink or _INK
    muted = muted or _rgba_with_alpha(ink, 0.6)
    parts_top: list[str] = []
    # 自底向上排：先算总高度
    lines = []
    if subtitle:
        lines.append(("subtitle", subtitle_font_size))
    if title:
        lines.append(("title", title_font_size))
    if figure_label:
        lines.append(("figure", figure_font_size))
    # 行距（gap）：subtitle→title 6, title→figure 8（对齐 ridge 的 34 vs 52，差 18 = 22 title-fs 减 4）
    gaps = {"subtitle": 6, "title": 8, "figure": 4}
    y_cursor = anchor_y - 2  # subtitle baseline 靠近 anchor_y
    y_subtitle = y_title = y_figure = None
    for name, fs in lines:
        if name == "subtitle":
            y_subtitle = y_cursor
            y_cursor -= fs + gaps["subtitle"]
        elif name == "title":
            y_title = y_cursor
            y_cursor -= fs + gaps["title"]
        elif name == "figure":
            y_figure = y_cursor
            y_cursor -= fs + gaps["figure"]
    top_y = y_cursor

    if figure_label and y_figure is not None:
        parts_top.append(
            f'<text x="{x_left:.1f}" y="{y_figure:.1f}" '
            f'font-family="{body_font}" font-size="{figure_font_size}" font-weight="600" '
            f'fill="{muted}" letter-spacing=".15em">'
            f'{_xesc(figure_label)}</text>'
        )
    if title and y_title is not None:
        parts_top.append(
            f'<text x="{x_left:.1f}" y="{y_title:.1f}" '
            f'font-family="{heading_font}" font-size="{title_font_size}" font-weight="700" '
            f'fill="{ink}" letter-spacing=".02em">{_xesc(title)}</text>'
        )
    if subtitle and y_subtitle is not None:
        parts_top.append(
            f'<text x="{x_left:.1f}" y="{y_subtitle:.1f}" '
            f'font-family="{body_font}" font-size="{subtitle_font_size}" font-weight="600" '
            f'fill="{muted}" letter-spacing=".16em">{_xesc(subtitle)}</text>'
        )
    total_h = anchor_y - top_y
    return "".join(parts_top), total_h


def auto_layout_labels(labels, min_gap: float = 4.0, iterations: int = 40) -> list:
    """
    通用标签避让：把 N 个标签的位置微调到互不重叠。
    labels: [(x, y, text, anchor, fontsize, axis)] —— axis 是 "x"/"y" 表示允许移动的方向
    返回 [(new_x, new_y), ...]
    算法：贪心迭代——每轮找出所有重叠对，按较小重叠方向微推靠后的一方，直到无重叠或达到 iterations。
    """
    def bbox(x, y, text, anchor, fs):
        n_ascii = sum(1 for c in text if ord(c) < 128)
        n_cjk = len(text) - n_ascii
        w = n_ascii * fs * 0.7 + n_cjk * fs * 1.1
        h = fs * 1.3
        if anchor == "start":   left = x
        elif anchor == "end":   left = x - w
        else:                   left = x - w / 2
        return left, y - fs * 1.1, w, h

    positions = [(L[0], L[1]) for L in labels]
    N = len(labels)
    for _ in range(iterations):
        moved = False
        boxes = [bbox(positions[i][0], positions[i][1], labels[i][2], labels[i][3], labels[i][4]) for i in range(N)]
        for i in range(N):
            for j in range(i + 1, N):
                bi, bj = boxes[i], boxes[j]
                ox = min(bi[0]+bi[2], bj[0]+bj[2]) - max(bi[0], bj[0])
                oy = min(bi[1]+bi[3], bj[1]+bj[3]) - max(bi[1], bj[1])
                if ox <= 0 or oy <= 0: continue
                axis_i = labels[i][5] if len(labels[i]) > 5 else "y"
                axis_j = labels[j][5] if len(labels[j]) > 5 else "y"
                if axis_i == "y" and axis_j == "y":
                    dy = oy + min_gap
                    if positions[i][1] < positions[j][1]: positions[j] = (positions[j][0], positions[j][1] + dy)
                    else: positions[i] = (positions[i][0], positions[i][1] + dy)
                elif axis_i == "x" and axis_j == "x":
                    dx = ox + min_gap
                    if positions[i][0] < positions[j][0]: positions[j] = (positions[j][0] + dx, positions[j][1])
                    else: positions[i] = (positions[i][0] + dx, positions[i][1])
                else:
                    if ox < oy:
                        dx = ox + min_gap
                        if positions[i][0] < positions[j][0]: positions[j] = (positions[j][0] + dx, positions[j][1])
                        else: positions[i] = (positions[i][0] + dx, positions[i][1])
                    else:
                        dy = oy + min_gap
                        if positions[i][1] < positions[j][1]: positions[j] = (positions[j][0], positions[j][1] + dy)
                        else: positions[i] = (positions[i][0], positions[i][1] + dy)
                moved = True
        if not moved:
            break
    return positions


# ==============================================================
# 1) Calendar Heat 日历热力（52 × 7 天）
# ==============================================================


def ridge_density_from_samples(samples: Sequence[float],
                               x_min: float,
                               x_max: float,
                               n: int = 60,
                               bandwidth: float = None) -> list:
    """把原始样本转成等距密度值，供 make_ridge 使用。

    samples:   原始样本
    x_min, x_max: X 轴范围（所有组共享），必须一致
    n:         输出的密度点数（默认 60）
    bandwidth: 高斯 KDE 带宽；缺省 Silverman 规则 = 1.06 * std * n^(-1/5)

    返回长度为 n 的密度值列表（严格 >= 0）。
    """
    if not samples:
        return [0.0] * n
    N = len(samples)
    mean = sum(samples) / N
    var = sum((s - mean) ** 2 for s in samples) / max(1, N - 1)
    std = math.sqrt(var) if var > 0 else max((x_max - x_min) * 0.01, 1e-6)
    if bandwidth is None:
        bandwidth = 1.06 * std * (N ** -0.2)
    bandwidth = max(bandwidth, (x_max - x_min) * 1e-4)
    step = (x_max - x_min) / (n - 1) if n > 1 else (x_max - x_min)
    inv_2h2 = 1.0 / (2.0 * bandwidth * bandwidth)
    coeff = 1.0 / (bandwidth * math.sqrt(2 * math.pi))
    result = []
    for i in range(n):
        x = x_min + i * step
        density = 0.0
        for s in samples:
            d = x - s
            density += math.exp(-d * d * inv_2h2)
        density = density * coeff / N
        result.append(density)
    return result



# ==============================================================
# 5) Candlestick 蜡烛图（OHLC）
# ==============================================================


def _fmt_num(v):
    """给节点旁边的总量标签用：整数直接显示；小数保留 1 位。"""
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.1f}"


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


def _svg_close() -> str:
    return "</svg>"


# ==============================================================
# 基础设施：自动 viewBox + 标签碰撞避让
# ==============================================================


def auto_layout_labels(labels, min_gap: float = 4.0, iterations: int = 40) -> list:
    """
    通用标签避让：把 N 个标签的位置微调到互不重叠。
    labels: [(x, y, text, anchor, fontsize, axis)] —— axis 是 "x"/"y" 表示允许移动的方向
    返回 [(new_x, new_y), ...]
    算法：贪心迭代——每轮找出所有重叠对，按较小重叠方向微推靠后的一方，直到无重叠或达到 iterations。
    """
    def bbox(x, y, text, anchor, fs):
        n_ascii = sum(1 for c in text if ord(c) < 128)
        n_cjk = len(text) - n_ascii
        w = n_ascii * fs * 0.7 + n_cjk * fs * 1.1
        h = fs * 1.3
        if anchor == "start":   left = x
        elif anchor == "end":   left = x - w
        else:                   left = x - w / 2
        return left, y - fs * 1.1, w, h

    positions = [(L[0], L[1]) for L in labels]
    N = len(labels)
    for _ in range(iterations):
        moved = False
        boxes = [bbox(positions[i][0], positions[i][1], labels[i][2], labels[i][3], labels[i][4]) for i in range(N)]
        for i in range(N):
            for j in range(i + 1, N):
                bi, bj = boxes[i], boxes[j]
                ox = min(bi[0]+bi[2], bj[0]+bj[2]) - max(bi[0], bj[0])
                oy = min(bi[1]+bi[3], bj[1]+bj[3]) - max(bi[1], bj[1])
                if ox <= 0 or oy <= 0: continue
                axis_i = labels[i][5] if len(labels[i]) > 5 else "y"
                axis_j = labels[j][5] if len(labels[j]) > 5 else "y"
                if axis_i == "y" and axis_j == "y":
                    dy = oy + min_gap
                    if positions[i][1] < positions[j][1]: positions[j] = (positions[j][0], positions[j][1] + dy)
                    else: positions[i] = (positions[i][0], positions[i][1] + dy)
                elif axis_i == "x" and axis_j == "x":
                    dx = ox + min_gap
                    if positions[i][0] < positions[j][0]: positions[j] = (positions[j][0] + dx, positions[j][1])
                    else: positions[i] = (positions[i][0] + dx, positions[i][1])
                else:
                    if ox < oy:
                        dx = ox + min_gap
                        if positions[i][0] < positions[j][0]: positions[j] = (positions[j][0] + dx, positions[j][1])
                        else: positions[i] = (positions[i][0] + dx, positions[i][1])
                    else:
                        dy = oy + min_gap
                        if positions[i][1] < positions[j][1]: positions[j] = (positions[j][0], positions[j][1] + dy)
                        else: positions[i] = (positions[i][0], positions[i][1] + dy)
                moved = True
        if not moved:
            break
    return positions


# ==============================================================
# 1) Calendar Heat 日历热力（52 × 7 天）
# ==============================================================


def ridge_density_from_samples(samples: Sequence[float],
                               x_min: float,
                               x_max: float,
                               n: int = 60,
                               bandwidth: float = None) -> list:
    """把原始样本转成等距密度值，供 make_ridge 使用。

    samples:   原始样本
    x_min, x_max: X 轴范围（所有组共享），必须一致
    n:         输出的密度点数（默认 60）
    bandwidth: 高斯 KDE 带宽；缺省 Silverman 规则 = 1.06 * std * n^(-1/5)

    返回长度为 n 的密度值列表（严格 >= 0）。
    """
    if not samples:
        return [0.0] * n
    N = len(samples)
    mean = sum(samples) / N
    var = sum((s - mean) ** 2 for s in samples) / max(1, N - 1)
    std = math.sqrt(var) if var > 0 else max((x_max - x_min) * 0.01, 1e-6)
    if bandwidth is None:
        bandwidth = 1.06 * std * (N ** -0.2)
    bandwidth = max(bandwidth, (x_max - x_min) * 1e-4)
    step = (x_max - x_min) / (n - 1) if n > 1 else (x_max - x_min)
    inv_2h2 = 1.0 / (2.0 * bandwidth * bandwidth)
    coeff = 1.0 / (bandwidth * math.sqrt(2 * math.pi))
    result = []
    for i in range(n):
        x = x_min + i * step
        density = 0.0
        for s in samples:
            d = x - s
            density += math.exp(-d * d * inv_2h2)
        density = density * coeff / N
        result.append(density)
    return result



# ==============================================================
# 5) Candlestick 蜡烛图（OHLC）
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




_SVG_LIB_VARIANTS = {
    "boxplot":            ("boxplot",       ["default_flat","beeswarm","notched_outlined","variable_width_gradient","strip_flat"], "default_flat"),
    "violin":             ("violin",        ["boxplot_inner_flat","quartile_outlined","points_inner_flat","half_gradient","kde_only"], "boxplot_inner_flat"),
    "ridge":              ("ridge",         ["default_flat","outlined_separated","gradient_overlap","joy_division","histogram_binned"], "default_flat"),
    "funnel_classic":     ("funnel",        ["default_flat","rectangle_flat","bar_lollipop","nested_arrow","pyramid_flat"], "default_flat"),
    "marimekko":          ("marimekko",     ["default_flat","mekko_gradient","mekko_outlined","shaded_residual","treemap_flat"], "default_flat"),
    "nested_donut":       ("nested_donut",  ["donut_flat","donut_gradient","sunburst_flat","polar_area_outlined","donut_layered"], "donut_flat"),
    "percent_grid":       ("percent_grid",  ["square_10x10","dot_10x10","person_10x10","square_stacked_row","dot_faceted"], "square_10x10"),
    "population_pyramid": ("pyramid",       ["default_flat","filled_gradient","stacked_flat","dot_flat","outlined_burgundy"], "default_flat"),
    "matrix_heat":        ("matrix_heat",   ["square_flat_full","circle_full","ellipse_upper","pie_full","annotated_number"], "square_flat_full"),
    "quadrant_2x2":       ("quadrant",      ["dot_cross","bubble_L","label_box_quadrant_bg","emoji_icon_cross","ring_arrow"], "dot_cross"),
    "gantt":              ("gantt",         ["default_flat","progress_split","critical_path","gradient_bars","dot_range"], "default_flat"),
    "candle":             ("candle",        ["candle_american_filled","candle_japanese_hollow","ohlc_american","heikin_ashi","line_close"], "candle_american_filled"),
    "event_timeline":     ("event_timeline",["horizontal_alt_dot","stepped_dot","vertical_alt_dot","horizontal_pin","circular_dot"], "horizontal_alt_dot"),
    "sankey":             ("sankey",        ["default_ribbon_flat","alluvial_sinusoidal","chord_circular","multi_layer_flat","gradient_layered"], "default_ribbon_flat"),
    "waterfall":          ("waterfall",     ["default_flat","subtotal_bridge","cross_axis","horizontal","stacked_gradient"], "default_flat"),
    "calheat":            ("calheat",       ["default_row_52x7","monthly_grid_12x31","small_multiples","radial_year","dot_grid"], "default_row_52x7"),
}





def _variant_is_classic(slug, variant):
    """是否走 baseline make_<slug>()：variant is None, "", "classic"。
    否则必须是 _SVG_LIB_VARIANTS[slug] 支持的骨架名，未支持则 raise。"""
    if variant is None or variant == "" or variant == "classic":
        return True
    if slug not in _SVG_LIB_VARIANTS:
        raise ValueError(
            f"chart '{slug}' has no skeleton variants; "
            f"pass variant=None or 'classic', or drop the variant argument."
        )
    _mod, supported, _def = _SVG_LIB_VARIANTS[slug]
    if variant not in supported:
        raise ValueError(
            f"chart '{slug}' variant '{variant}' not supported. "
            f"Available: {supported} (or None/'classic' for baseline)."
        )
    return False


def _dispatch_to_svg_lib(slug, variant, data, title=None, subtitle=None,
                           figure_label=None, palette=None, font_family=None,
                           width=None, height=None, **kwargs):
    """调用 svg_lib.charts.<mod>.draw_<mod>(data, variant, palette, ...) 并返回 SVG 字符串。

    slug: 原 skill 的 chart slug（例如 "boxplot"、"population_pyramid"）
    variant: svg_lib 里的变体名，必须在 _SVG_LIB_VARIANTS[slug][1] 里
    data: svg_lib 的 data dict（每个 chart 有自己的 schema，见 chart_help）
    其余参数尽量沿用 make_* 的通用参数
    """
    import importlib
    if slug not in _SVG_LIB_VARIANTS:
        raise ValueError(f"chart '{slug}' has no svg_lib variants")
    mod_name, supported, _def = _SVG_LIB_VARIANTS[slug]
    if variant not in supported:
        raise ValueError(
            f"chart '{slug}' variant '{variant}' not supported. "
            f"Choose one of: {supported}"
        )
    # 动态 import svg_lib 模块
    try:
        mod = importlib.import_module(f"svg_lib.charts.{mod_name}")
    except Exception:
        # scripts/ 下能直接 import
        import sys, os
        _scripts_root = os.path.dirname(os.path.abspath(__file__))
        if _scripts_root not in sys.path:
            sys.path.insert(0, _scripts_root)
        mod = importlib.import_module(f"svg_lib.charts.{mod_name}")

    draw_fn = getattr(mod, f"draw_{mod_name}")

    call_kwargs = {"data": data, "variant": variant}
    if palette is not None:
        # svg_lib 也接受 str 或 dict palette
        call_kwargs["palette"] = palette
    else:
        call_kwargs["palette"] = "archive_ink"
    if width is not None:
        call_kwargs["width"] = float(width)
    if height is not None:
        call_kwargs["height"] = float(height)
    if title is not None:
        call_kwargs["title"] = title
    if subtitle is not None:
        call_kwargs["subtitle"] = subtitle
    if figure_label is not None:
        # svg_lib 里少数 draw 接受 figure_label（如 boxplot）；其余忽略
        try:
            import inspect as _inspect
            if "figure_label" in _inspect.signature(draw_fn).parameters:
                call_kwargs["figure_label"] = figure_label
        except Exception:
            pass
    # font_family 处理（两步）：
    # 1. 显式替换 svg_lib 里常见的 Inter/Georgia 字体
    # 2. 兜底：直接在 <svg ...> 根元素上加 font-family="..."（SVG 子元素继承）
    #    不使用 <style>，因为 embed_svg_validator 把 <style> 列为 forbidden_elements。
    svg = draw_fn(**call_kwargs)
    if font_family:
        svg = svg.replace('font-family="Inter, sans-serif"', f'font-family="{font_family}"')
        svg = svg.replace("font-family='Inter, sans-serif'", f"font-family='{font_family}'")
        svg = svg.replace('font-family="Georgia, serif"', f'font-family="{font_family}"')
        svg = svg.replace("font-family='Georgia, serif'", f"font-family='{font_family}'")
        # 在 <svg ...> 根元素上注入 font-family 属性（若尚未存在）。
        # 双引号内可能包含内部单引号（例如 "PingFang SC, sans-serif"），需转义为 &quot;
        import re as _re
        m = _re.match(r'<svg\b([^>]*)>', svg)
        if m:
            attrs = m.group(1)
            if 'font-family=' not in attrs:
                _esc_ff = font_family.replace('&', '&amp;').replace('"', '&quot;')
                new_open = f'<svg{attrs} font-family="{_esc_ff}">'
                svg = new_open + svg[m.end():]
    return svg


