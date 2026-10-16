"""颜色 · gradient · 透明度 · 属性提取 helpers."""

from __future__ import annotations

import math
from html import unescape
import re
from typing import Optional

from ._gradient import native_linear_gradient


def _get_attr(tag: str, name: str) -> Optional[str]:
    # Converters receive canonical XML; match the complete attribute name so
    # opacity cannot accidentally read fill-opacity (nor x read cx/data-x).
    m = re.search(rf'(?:^|\s){re.escape(name)}="([^"]*)"', tag)
    return m.group(1) if m else None


def _get_num(tag: str, name: str, default: float = 0) -> float:
    v = _get_attr(tag, name)
    try:
        return float(v) if v else default
    except (TypeError, ValueError):
        return default


# 颜色识别


def _is_muted_gray(color: str) -> bool:
    """判断 rgba/rgb 颜色是否为中灰调 (R≈G≈B 且明度 80-200)."""
    if not color:
        return False
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color)
    if not m:
        return False
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    # 中灰: 三通道差 ≤ 25 且明度 80-200 (太黑=正文, 太白=底纹)
    max_diff = max(abs(r - g), abs(g - b), abs(r - b))
    avg = (r + g + b) / 3
    return max_diff <= 25 and 80 <= avg <= 200


def _is_transparent_fill(fill: Optional[str]) -> bool:
    """判断 fill 是否透明 (none / transparent / 空 / alpha=0 的 rgba)."""
    if fill is None:
        return False
    value = fill.strip().lower()
    if value in {"", "none", "transparent"}:
        return True
    rgba = re.match(r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)", value)
    return bool(rgba and float(rgba.group(1)) <= 0)


def _normalize_color(color: str) -> str:
    """Normalize SVG hex colors to Slides RGB/RGBA syntax, including hex alpha."""
    if not color:
        return "rgba(0,0,0,1)"
    c = color.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgb({r},{g},{b})"
        if len(h) == 8:
            r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{int(h[6:8], 16) / 255:.8g})"
    # Slides' color pattern rejects scientific alpha such as rgba(1,2,3,1e-1).
    m = re.fullmatch(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+[eE][-+]?\d+)\s*\)", c)
    if m:
        alpha = max(0.0, min(1.0, float(m.group(4))))
        return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha:.3f})"
    return c  # rgba(...) 直接用


def _apply_opacity(color: str, opacity: float) -> str:
    normalized = _normalize_color(color)
    if opacity < 1:
        rgb_m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", normalized)
        if rgb_m:
            return f"rgba({rgb_m.group(1)},{rgb_m.group(2)},{rgb_m.group(3)},{opacity:.2f})"
        rgba_m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.eE+-]+)\s*\)", normalized)
        if rgba_m:
            alpha = max(0.0, min(1.0, float(rgba_m.group(4)) * opacity))
            return f"rgba({rgba_m.group(1)},{rgba_m.group(2)},{rgba_m.group(3)},{alpha:.3f})"
    return normalized


def _offset_to_percent(offset: str) -> int:
    value = offset.strip()
    try:
        if value.endswith("%"):
            pct = float(value[:-1])
        else:
            pct = float(value) * 100
    except ValueError:
        pct = 0
    return int(max(0, min(100, round(pct))))


def _resolve_paint_color(paint: Optional[str], all_defs: str = "", opacity: float = 1.0) -> str:
    """解析 fill/stroke 颜色, 支持 url(#gradId) → CSS linear-gradient()."""
    if _is_transparent_fill(paint):
        return "rgba(0,0,0,0)"
    value = (paint or "").strip()
    url_m = re.fullmatch(r"url\(#([^)]+)\)", value)
    if not url_m:
        return _apply_opacity(value, opacity)

    # Reuse the exact subset for existing native fills too (rgba stops and
    # percentage directions). Leave legacy complex-paint routing unchanged.
    simple_gradient = native_linear_gradient(value, all_defs, opacity)
    if simple_gradient is not None:
        return simple_gradient

    if not all_defs:
        return "rgba(0,0,0,0)"
    gradient_id = re.escape(url_m.group(1))
    grad_m = re.search(
        rf'<linearGradient\b[^>]*id="{gradient_id}"[^>]*>(.*?)</linearGradient>',
        all_defs,
        flags=re.DOTALL,
    )
    if not grad_m:
        return "rgba(0,0,0,0)"
    grad_tag = grad_m.group(0)
    body = grad_m.group(1)
    x1 = _get_num(grad_tag, "x1", 0)
    y1 = _get_num(grad_tag, "y1", 0)
    x2 = _get_num(grad_tag, "x2", 1)
    y2 = _get_num(grad_tag, "y2", 0)
    angle = int(round((math.degrees(math.atan2(y2 - y1, x2 - x1)) + 90) % 360))
    stops = []
    for stop_m in re.finditer(r"<stop\b([^>]*)/?>", body):
        stop_tag = stop_m.group(1)
        stop_color = _get_attr(stop_tag, "stop-color") or "rgba(0,0,0,1)"
        stop_alpha = _get_num(stop_tag, "stop-opacity", 1.0) * opacity
        stop_offset = _offset_to_percent(_get_attr(stop_tag, "offset") or "0%")
        stops.append(f"{_apply_opacity(stop_color, stop_alpha)} {stop_offset}%")
    if len(stops) >= 2:
        return f"linear-gradient({angle}deg,{','.join(stops)})"
    if len(stops) == 1:
        return stops[0].rsplit(" ", 1)[0]
    return "rgba(0,0,0,0)"


# 常见 SVG 字体名 → slide 支持的字体名 (见 references/xml/fonts.md).
# key 都是小写单个 family (不带 fallback 链, 不带引号).
_SVG_FONT_FAMILY_MAP = {
    "georgia": "Georgia",
    "times new roman": "Times New Roman",
    "times": "Times New Roman",
    "eb garamond": "EB Garamond",
    "garamond": "Garamond",
    "playfair display": "Playfair Display",
    "playfair": "Playfair Display",
    "lora": "Lora",
    "merriweather": "Merriweather",
    "stix two text": "Georgia",  # 数学 / 符号 serif · 用 Georgia 兜底
    "stix": "Georgia",
    "serif": "Georgia",
    "inter": "Inter",
    "ibm plex sans": "IBM Plex Sans",
    "roboto": "Roboto",
    "montserrat": "Montserrat",
    "helvetica": "Arial",
    "arial": "Arial",
    "sans-serif": "Inter",
    "jetbrains mono": "Roboto Mono",
    "sarasa mono": "Roboto Mono",
    "ibm plex mono": "Roboto Mono",
    "roboto mono": "Roboto Mono",
    "source code pro": "Source Code Pro",
    "inconsolata": "Inconsolata",
    "courier": "Roboto Mono",
    "courier new": "Roboto Mono",
    "monospace": "Roboto Mono",
    "宋体": "宋体",
    "simsun": "宋体",
    "songti": "宋体",
    "思源宋体": "思源宋体",
    "寒蝉锦书宋": "寒蝉锦书宋",
    "source han serif": "思源宋体",
    "noto serif cjk": "思源宋体",
    "黑体": "黑体",
    "simhei": "黑体",
    "heiti": "黑体",
    "思源黑体": "思源黑体",
    "source han sans": "思源黑体",
    "noto sans cjk": "思源黑体",
    # 中文楷 / 圆 / 其他
    "楷体": "楷体",
    "kaiti": "楷体",
    "寒蝉正楷体": "寒蝉正楷体",
    "站酷小薇体": "站酷小薇体",
    "寒蝉团圆体": "寒蝉团圆体 圆体",
    "寒蝉团圆体 圆体": "寒蝉团圆体 圆体",
    "霞鹜 975 圆体": "霞鹜 975 圆体",
    "钟齐志莽行书": "钟齐志莽行书",
}


_GENERIC_SANS = {"sans-serif", "system-ui", "ui-sans-serif", "-apple-system", "blinkmacsystemfont"}


def _map_svg_font_family(raw: str) -> str:
    """Normalize known aliases."""
    from ._config import _CFG

    default = _CFG.get("default_font_family") or ""
    remaining = unescape(raw or "").strip()
    if not remaining:
        return default
    while remaining:
        remaining = remaining.lstrip(" ,\t\r\n")
        match = re.match(r"\"([^\"]*)\"|'([^']*)'|([^,]+)", remaining)
        if not match:
            return ""
        family = next(value for value in match.groups() if value is not None).strip()
        if family:
            if match.group(3) is not None and family.lower() in {
                "inherit",
                "initial",
                "unset",
                "revert",
                "revert-layer",
            }:
                return default
            if default and match.group(3) is not None and family.lower() in _GENERIC_SANS:
                return default
            return _SVG_FONT_FAMILY_MAP.get(family.lower(), family)
        remaining = remaining[match.end() :]
    return ""


# 文本 escape / unescape / 数值格式化


def _format_num(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _escape_xml(s: str) -> str:
    """转义为 XML-safe 字符 (原字符 → &amp; &lt; &gt;)."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
