"""
Skin protocol · Phase 3

每个 skin 实现下面几个方法 · 由未来的 render() 或用户直接调用。skin
只关心视觉外观：给出局部几何 + 语义 kind + palette · 返回 SVG 片段。
skin 不做布局、不做 chrome、不做数据变形。

    draw_node(x, y, w, h, label, palette, kind="task", **kwargs) -> svg_str
    draw_edge(x1, y1, x2, y2, label, palette, kind="assoc", **kwargs) -> svg_str
    draw_container(x, y, w, h, label, palette, kind="lane", **kwargs) -> svg_str
    defs(palette) -> svg_str          # 可选 · SVG <defs> 里的 filter / marker

palette 是外部参数 · skin 通过 palette 得到实际颜色。
返回的 SVG 片段只包含图元（无 <svg> 包裹），可以被拼进任何 canvas。

铁律：
    * 纯 stdlib · 不引外部依赖
    * 保持当前 11 个 relation preset 稳定 · 不改 svg_lib/
    * 不假设 canvas 尺寸 · 只按传入的 x/y/w/h 画
"""
from __future__ import annotations
from typing import Protocol
from ..palettes import Palette


class Skin(Protocol):
    """Skin 协议 · 6 通用 skin 都实现这个签名。

    实现方式统一：class 里定义 4 个方法 · 模块底部 export 单例（大写常量）。
    多余的 kwargs 用 `**_` 吞掉 · 避免上游传新字段时炸掉。
    """

    name: str

    def draw_node(self, x: float, y: float, w: float, h: float,
                  label: str, palette: Palette, **kwargs) -> str:
        ...

    def draw_edge(self, x1: float, y1: float, x2: float, y2: float,
                  label: str, palette: Palette, **kwargs) -> str:
        ...

    def draw_container(self, x: float, y: float, w: float, h: float,
                       label: str, palette: Palette, **kwargs) -> str:
        ...

    def defs(self, palette: Palette) -> str:
        ...


# ──────────────────────────────────────────────────────────────
# 通用辅助 · 供各 skin 复用
# ──────────────────────────────────────────────────────────────
def _mid(a: float, b: float) -> float:
    return (a + b) / 2.0


def _label_clip(label: str, max_chars: int = 22) -> str:
    """硬红线不允许 "…" · 返回完整 label (超长由上层控制)."""
    if not label:
        return ""
    return label


# 中日韩字符范围 (含 3040-30FF 假名 · 4E00-9FFF 中日韩统一表意)
def _is_cjk(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    return (0x3040 <= o <= 0x30FF) or (0x4E00 <= o <= 0x9FFF) or \
           (0x3400 <= o <= 0x4DBF) or (0xFF00 <= o <= 0xFFEF)


def _visual_width(text: str, char_w: float) -> float:
    """英文字符按 1 * char_w · CJK 按 1.8 * char_w · 数字/标点按 0.55.

    粗略估计 · 用于 wrap 分行判断 · 不需要精确."""
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        if _is_cjk(ch):
            total += char_w * 1.8
        elif ch in " .,;:!?)('\"":
            total += char_w * 0.4
        elif ch.isdigit():
            total += char_w * 0.75
        else:
            total += char_w
    return total


def _wrap_lines(text: str, max_width_px: float, char_w: float = 5.5,
                max_lines: int = 2) -> list[str]:
    """把 text 按 max_width_px 分成最多 max_lines 行 · 溢出末行加 …

    分行规则:
        1. 若整段 <= max_width, 单行返回
        2. 优先按 whitespace 分词 (英文 word)
        3. 遇 CJK 无 whitespace, 按字符切
        4. 单 word 超宽 · 强行切字符
        5. 超 max_lines · 最后一行加 …
    """
    if not text:
        return []
    if _visual_width(text, char_w) <= max_width_px:
        return [text]

    # tokens: whitespace-separated · CJK 每字符自成一 token
    tokens: list[str] = []
    buf = ""
    for ch in text:
        if _is_cjk(ch):
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        elif ch.isspace():
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(" ")
        else:
            buf += ch
    if buf:
        tokens.append(buf)

    lines: list[str] = []
    cur = ""
    for tok in tokens:
        if tok == " ":
            candidate = cur + " " if cur else cur
        else:
            candidate = cur + tok
        if _visual_width(candidate, char_w) <= max_width_px:
            cur = candidate
            continue
        # 溢出
        if cur.strip():
            lines.append(cur.rstrip())
            cur = ""
        if tok == " ":
            continue
        # 单 token 超宽 · 强切字符
        if _visual_width(tok, char_w) > max_width_px:
            for ch in tok:
                trial = cur + ch
                if _visual_width(trial, char_w) <= max_width_px:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = ch
                if len(lines) >= max_lines:
                    break
            if len(lines) >= max_lines:
                break
        else:
            cur = tok

    if cur.strip() and len(lines) < max_lines:
        lines.append(cur.rstrip())

    # 超 max_lines · 硬红线不允许 "…" · 直接截断保留字词完整
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    elif len(lines) == max_lines:
        # 已满 · 检查是否有 token 没塞进 (max_lines 提前退出) · 无 …
        pass

    return lines if lines else [text]


def _fit_font_size(text: str, max_width_px: float, base_size: float,
                   *, min_size: float = 7.0,
                   char_w_ratio: float = 0.55) -> tuple[float, str]:
    """字号自适应 · 保持单行.

    逻辑:
        1. 用 base_size 算 visual width
        2. 若 <= max_width, 返回 (base_size, text)
        3. 否则按比例缩到 min_size 之间
        4. 若 min_size 都还溢出, 返回 (min_size, clipped_text + "…")

    Returns:
        (font_size, text_to_render)
    """
    if not text:
        return base_size, ""
    base_w = _visual_width(text, base_size * char_w_ratio)
    if base_w <= max_width_px:
        return base_size, text
    # 缩字号
    scale = max_width_px / base_w
    new_size = max(base_size * scale, min_size)
    new_w = _visual_width(text, new_size * char_w_ratio)
    if new_w <= max_width_px:
        return new_size, text
    # min_size 都还溢出 · 硬红线不允许 "…" · 保留完整文本 · 让上层承担溢出
    # (调用方应给足 max_width_px · 或 text 精简)
    return new_size, text


def _text_multiline_svg(x: float, y: float, lines: list[str], *,
                         size: float, family: str, weight: int = 500,
                         fill: str = "#1C1914", anchor: str = "start",
                         italic: bool = False,
                         letter_em: float | None = None,
                         line_height: float | None = None) -> str:
    """把 lines 渲染成多行 SVG · y 为首行基线 · 每行 dy = line_height 或 size*1.15."""
    if not lines:
        return ""
    from ..engine import esc
    lh = line_height if line_height is not None else size * 1.15
    attrs = [
        f'x="{x}"', f'y="{y}"',
        f'font-family="{family}"', f'font-size="{size}"',
        f'fill="{fill}"', f'text-anchor="{anchor}"',
        f'font-weight="{weight}"',
    ]
    if italic:
        attrs.append('font-style="italic"')
    if letter_em is not None:
        attrs.append(f'letter-spacing="{letter_em}em"')
    tspans: list[str] = []
    for i, ln in enumerate(lines):
        if i == 0:
            tspans.append(f'<tspan x="{x}">{esc(ln)}</tspan>')
        else:
            tspans.append(f'<tspan x="{x}" dy="{lh}">{esc(ln)}</tspan>')
    return f'<text {" ".join(attrs)}>{"".join(tspans)}</text>'


# ═════════════════════════════════════════════════════════════════
# Color helpers · luminance & contrast auto ink picker
# ═════════════════════════════════════════════════════════════════

def _parse_color_to_rgb(c: str) -> tuple[int, int, int]:
    """Parse '#RGB' / '#RRGGBB' / 'rgba(r,g,b,a)' / 'rgb(r,g,b)' → (r,g,b)."""
    if not c:
        return (128, 128, 128)
    c = c.strip()
    if c.startswith("#"):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) >= 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    import re as _re
    m = _re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", c)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (128, 128, 128)


def _luminance(color: str) -> float:
    """WCAG relative luminance (0-255 scale, 未 gamma 校正的快速版).
    深底 < 140, 中亮 140-180, 浅底 > 180."""
    r, g, b = _parse_color_to_rgb(color)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _ink_on(bg_color: str,
            dark_ink: str = "rgba(20,20,26,0.95)",
            light_ink: str = "rgba(255,255,255,0.98)",
            threshold: float = 140.0) -> str:
    """给定底色返回可读的字色.
    bg 浅 (luminance >= threshold) → 深字; bg 深 → 白字.

    threshold=140 是经验值: 金/黄/淡青等中亮 hue (luminance 140-160) 判为浅色, 用深字.
    深蓝/深紫/勃艮第/黑 (luminance < 130) 判为深底, 用白字.
    """
    return dark_ink if _luminance(bg_color) >= threshold else light_ink


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """'#RRGGBB' 或 'rgba(...)' → 'rgba(r,g,b,alpha)' with 指定 alpha."""
    r, g, b = _parse_color_to_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha:.3f})"
