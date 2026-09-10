"""svg_lib/_shared.py

通用工具，所有 draw_<chart>() 函数复用：
- palette 解析
- SVG XML 转义
- 图元自适应字号
- rsvg-convert 转 PNG 验证
"""
import os, sys, re, subprocess
from pathlib import Path

# svg_palettes.py 就在 svg_lib/ 下（scripts/svg_lib/svg_palettes.py）
SVG_LIB_ROOT = Path(__file__).resolve().parents[1]  # scripts/svg_lib/
if str(SVG_LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(SVG_LIB_ROOT))
from svg_palettes import PALETTES

# 常用色
_INK  = "rgba(28,28,26,1.0)"
_INK6 = "rgba(28,28,26,0.6)"
_INK4 = "rgba(28,28,26,0.4)"
_INK2 = "rgba(28,28,26,0.2)"
_INK1 = "rgba(28,28,26,0.12)"
_ACC  = "rgba(163,88,50,1.0)"


def resolve_palette(palette):
    """把 palette 参数（None/str/dict）解析为核心配色 dict。

    返回 dict 包含：ink, accent, secondary, bg, muted, ink6/4/2/1（派生）。
    """
    if palette is None:
        pl = {}
    elif isinstance(palette, dict):
        pl = dict(palette)
    elif isinstance(palette, str):
        if palette not in PALETTES:
            raise ValueError(f"unknown palette {palette!r}. Available: {sorted(PALETTES)}")
        pl = dict(PALETTES[palette])
    else:
        raise TypeError(f"palette must be None/str/dict, got {type(palette).__name__}")

    ink       = pl.get("ink",       _INK)
    accent    = pl.get("accent",    _ACC)
    secondary = pl.get("secondary", _rgba_with_alpha(ink, 0.6))
    bg        = pl.get("bg",        "rgba(250,248,242,1)")
    muted     = pl.get("muted",     _rgba_with_alpha(ink, 0.6))

    out = {
        "ink": ink, "accent": accent, "secondary": secondary,
        "bg": bg, "muted": muted,
        "ink6": _rgba_with_alpha(ink, 0.6),
        "ink4": _rgba_with_alpha(ink, 0.4),
        "ink2": _rgba_with_alpha(ink, 0.2),
        "ink1": _rgba_with_alpha(ink, 0.12),
    }
    # 透传其它字段（series/grid 等）
    for k, v in pl.items():
        if k not in out:
            out[k] = v
    return out


def _rgba_with_alpha(rgba_str, alpha):
    m = re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str or "")
    if not m:
        return f"rgba(28,28,26,{alpha})"
    r, g, b = int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
    return f"rgba({r},{g},{b},{alpha})"


def rgb_tuple(rgba_str):
    m = re.match(r'\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', rgba_str or "")
    if not m:
        return (28, 28, 26)
    return (int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))))


def is_dark_palette(pal):
    """判断 palette 的 bg 是否深色（用于决定文字颜色对比）。"""
    r, g, b = rgb_tuple(pal.get("bg", "rgba(250,248,242,1)"))
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return luma < 128


def xesc(s):
    """XML/SVG 文本转义。"""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def auto_font_size(n_items, base=12, min_size=8, max_size=16):
    """根据元素数量自适应字号：数量越多字号越小。

    n_items: 元素数量（比如箱线图组数、漏斗层数）
    """
    if n_items <= 5:
        return base + 2
    elif n_items <= 10:
        return base
    elif n_items <= 20:
        return max(min_size, base - 1)
    else:
        return max(min_size, base - 2)


def data_scale_factor(n):
    """按数据规模 n 返回字号缩放因子。

    分档：
      n <= 4  → 1.4  （超稀疏，字号放大）
      n <= 8  → 1.0  （常规）
      n <= 15 → 0.8  （中等密集）
      n > 15  → 0.6  （密集，还要额外 floor 保护）
    """
    if n <= 4:
        return 1.4
    if n <= 8:
        return 1.0
    if n <= 15:
        return 0.8
    return 0.6


def viewbox_fs(vb_w, vb_h, n, role_mult=1.0, floor=10.0):
    """按 viewBox 尺寸 + 数据规模 n 计算字号。

    公式：
        base_fs = min(vb_w, vb_h) * 0.02
        fs = base_fs * data_scale_factor(n) * role_mult
        n > 15 时 fs = max(fs, floor)

    role_mult: 角色字号系数（标题 > 值标签 > 轴刻度 …）
    floor: 大规模数据下的最小字号（默认 10）
    """
    base = min(float(vb_w), float(vb_h)) * 0.02
    fs = base * data_scale_factor(n) * float(role_mult)
    if n > 15:
        fs = max(fs, float(floor))
    # 保留一位小数即可，避免 fs="8.400000000000001" 这种冗长文本
    return round(fs, 1)


def svg_open(vb_x=0, vb_y=0, vb_w=900, vb_h=540, bg=None):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x} {vb_y} {vb_w} {vb_h}">']
    if bg:
        parts.append(f'<rect x="{vb_x}" y="{vb_y}" width="{vb_w}" height="{vb_h}" fill="{bg}"/>')
    return "".join(parts)


def svg_close():
    return "</svg>"


def render_to_png(svg_str, out_path, width=900):
    """把 SVG 字符串通过 rsvg-convert 转 PNG。返回是否成功。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open('/tmp/_render.svg', 'w') as f:
        f.write(svg_str)
    try:
        r = subprocess.run(['rsvg-convert', '/tmp/_render.svg', '-o', str(out_path), '-w', str(width)],
                          capture_output=True, text=True, timeout=30)
        return r.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:
        return False


def validate_svg(svg_str):
    """简单校验 SVG 语法。返回 (ok, reason)。"""
    if not svg_str.strip().startswith('<svg'):
        return False, "not starts with <svg"
    if '</svg>' not in svg_str:
        return False, "missing </svg>"
    # 基本括号平衡
    if svg_str.count('<') != svg_str.count('>'):
        return False, f"tag mismatch: {svg_str.count('<')} vs {svg_str.count('>')}"
    return True, "ok"


# =========================================================
# shape_variant 皮肤分发（跨 chart 复用）
# =========================================================

def flat_fill(pal, base_col, alpha=0.9):
    """flat 皮肤：半透明纯色。"""
    return _rgba_with_alpha(base_col, alpha)


def outlined_fill_stroke(pal, base_col, fill_alpha=0.22, stroke_alpha=0.85):
    """outlined 皮肤：淡填 + 深描边。返回 (fill, stroke)。"""
    return _rgba_with_alpha(base_col, fill_alpha), _rgba_with_alpha(base_col, stroke_alpha)


def gradient_def(gid, base_col, direction="vertical", x1=0, y1=0, x2=0, y2=100):
    """gradient 皮肤：linearGradient defs 字符串。返回 <defs> 内层片段。"""
    top = _rgba_with_alpha(base_col, 1.0)
    bot = _rgba_with_alpha(base_col, 0.55)
    if direction == "horizontal":
        x2, y2 = 100, 0
    return (
        f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop offset="0%" stop-color="{top}"/>'
        f'<stop offset="100%" stop-color="{bot}"/>'
        f'</linearGradient>'
    )


def layered_shapes(x, y, w, h, base_col, rx=0):
    """layered 皮肤：阴影 + 主体 + 高光。返回 SVG 片段字符串。"""
    shadow = _rgba_with_alpha(_INK, 0.28)
    rx_attr = f' rx="{rx}" ry="{rx}"' if rx > 0 else ''
    parts = [
        f'<rect x="{x:.1f}" y="{y+2:.1f}" width="{w:.1f}" height="{h:.1f}"{rx_attr} fill="{shadow}"/>',
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"{rx_attr} fill="{_rgba_with_alpha(base_col, 1.0)}"/>',
    ]
    if h > 6:
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="2.5"{rx_attr} fill="rgba(255,255,255,0.5)"/>')
    return "".join(parts)


def striped_pattern_def(pid, base_col, angle=45, spacing=6, line_width=1.6):
    """striped 皮肤：斜纹 pattern defs 片段。"""
    line_col = _rgba_with_alpha(base_col, 0.85)
    return (
        f'<pattern id="{pid}" patternUnits="userSpaceOnUse" '
        f'width="{spacing}" height="{spacing}" '
        f'patternTransform="rotate({angle})">'
        f'<line x1="0" y1="0" x2="0" y2="{spacing}" stroke="{line_col}" stroke-width="{line_width}"/>'
        f'</pattern>'
    )


# =========================================================
# 元素重叠检测（简单几何）
# =========================================================

def bbox_overlap(a, b):
    """检查两个 bbox {x, y, w, h} 是否重叠。"""
    return not (
        a['x'] + a['w'] < b['x'] or
        b['x'] + b['w'] < a['x'] or
        a['y'] + a['h'] < b['y'] or
        b['y'] + b['h'] < a['y']
    )


def check_text_overlaps(text_bboxes):
    """检查文本 bbox 列表里有几对重叠。返回重叠对数。"""
    overlaps = 0
    for i, a in enumerate(text_bboxes):
        for j in range(i + 1, len(text_bboxes)):
            if bbox_overlap(a, text_bboxes[j]):
                overlaps += 1
    return overlaps
