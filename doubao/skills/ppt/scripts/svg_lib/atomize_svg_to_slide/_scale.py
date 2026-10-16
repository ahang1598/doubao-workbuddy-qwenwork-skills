"""坐标 / 尺寸 / 字号 SVG → slide 缩放."""

from __future__ import annotations

import math

from ._config import _CFG


def _sx(x: float) -> float:
    return _CFG["slide_x0"] + x * _CFG["slide_w"] / _CFG["svg_w"]


def _sy(y: float) -> float:
    return _CFG["slide_y0"] + y * _CFG["slide_h"] / _CFG["svg_h"]


def _sw(w: float) -> float:
    return w * _CFG["slide_w"] / _CFG["svg_w"]


def _sh(h: float) -> float:
    return h * _CFG["slide_h"] / _CFG["svg_h"]


def _sf(font_size: float) -> float:
    """字号按 x 方向缩放比例调整. 用于老 caller 保底 (等比 / 轻微 anisotropic)."""
    scale = _CFG["slide_w"] / _CFG["svg_w"]
    return font_size * scale


def _font_scale_ratio() -> float:
    """字号 SVG→slide 的缩放比, 各向异性感知."""
    sx = _CFG["slide_w"] / max(1.0, _CFG["svg_w"])
    sy = _CFG["slide_h"] / max(1.0, _CFG["svg_h"])
    if sx < 1.0 and sy < 0.7 * sx:
        return math.sqrt(sx * sy)
    return sx


def s2l_x(x: float) -> float:
    return _sx(x)


def s2l_y(y: float) -> float:
    return _sy(y)
