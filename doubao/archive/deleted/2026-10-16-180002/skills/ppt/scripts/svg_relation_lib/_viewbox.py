"""svg_relation_lib._viewbox · 通用 SVG viewBox 收紧工具.

对 render 完的 SVG string 做 post-processing:
  1. 扫描所有 rect / circle / ellipse / line / text / path 元素的 bbox
  2. 计算实际内容 bbox (排除满版背景 rect)
  3. 用新 viewBox 替换 (给上下左右加 padding)
  4. 同步收缩满版 bg rect

支持从字符串输入 · 用正则解析 · 无需 XML parser 依赖.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

__all__ = [
    "shrink_viewbox",
    "compute_content_bbox",
    "embed_sizes",
    "extract_viewbox",
]


# ─── 基础解析 ────────────────────────────────────────────


_VIEWBOX_RE = re.compile(r'viewBox="([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)"')


def extract_viewbox(svg: str) -> Optional[Tuple[float, float, float, float]]:
    """从 SVG 里抽第一个 viewBox · 返回 (x, y, w, h) 或 None."""
    m = _VIEWBOX_RE.search(svg)
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)),
            float(m.group(3)), float(m.group(4)))


def _attr(elem: str, name: str) -> Optional[float]:
    """从元素字符串里抽属性值 (float)."""
    m = re.search(rf'\b{name}="([\d.\-]+)"', elem)
    return float(m.group(1)) if m else None


def _attrs_all(elem: str) -> Dict[str, str]:
    """把元素属性拆成 dict (只抽 key="value" · 字符串值)."""
    return dict(re.findall(r'\b([a-zA-Z_-]+)="([^"]*)"', elem))


# ─── 每种元素的 bbox 估算 ─────────────────────────────


def _rect_bbox(elem: str) -> Optional[Tuple[float, float, float, float]]:
    x = _attr(elem, "x") or 0.0
    y = _attr(elem, "y") or 0.0
    w = _attr(elem, "width")
    h = _attr(elem, "height")
    if w is None or h is None:
        return None
    return (x, y, x + w, y + h)


def _circle_bbox(elem: str) -> Optional[Tuple[float, float, float, float]]:
    cx = _attr(elem, "cx")
    cy = _attr(elem, "cy")
    r = _attr(elem, "r")
    if cx is None or cy is None or r is None:
        return None
    return (cx - r, cy - r, cx + r, cy + r)


def _ellipse_bbox(elem: str) -> Optional[Tuple[float, float, float, float]]:
    cx = _attr(elem, "cx")
    cy = _attr(elem, "cy")
    rx = _attr(elem, "rx")
    ry = _attr(elem, "ry")
    if cx is None or cy is None or rx is None or ry is None:
        return None
    return (cx - rx, cy - ry, cx + rx, cy + ry)


def _line_bbox(elem: str) -> Optional[Tuple[float, float, float, float]]:
    x1 = _attr(elem, "x1")
    y1 = _attr(elem, "y1")
    x2 = _attr(elem, "x2")
    y2 = _attr(elem, "y2")
    if None in (x1, y1, x2, y2):
        return None
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def _text_bbox(elem: str, content: str = "") -> Optional[Tuple[float, float, float, float]]:
    """text 的 bbox 粗估: x/y 是基线锚点 · 用字号估算宽高.
    默认 text-anchor=start · font-size=12 · 每字符 6px 宽.
    [FIX 2026-09-11 R2] CJK 全角字符按 fs × 1.0 · 数字/字母按 fs × 0.55 · 空格 0.35 ·
    与 atomize_svg_to_slide 的 _char_width 保持一致 · 避免 shrink_viewbox 因 CJK 宽度低估
    误裁 fishbone 顶侧长中文 sub-label."""
    x = _attr(elem, "x")
    y = _attr(elem, "y")
    if x is None or y is None:
        return None
    fs = _attr(elem, "font-size") or 12.0
    # 从内容估宽 (退化到 40px) · CJK-aware
    if content:
        text_w = 0.0
        for ch in content:
            if ord(ch) > 0x2E80:  # CJK 全角
                text_w += fs * 1.0
            elif ch.isspace():
                text_w += fs * 0.35
            elif ch.isupper():
                text_w += fs * 0.7
            else:
                text_w += fs * 0.55
    else:
        text_w = 8 * fs * 0.55
    # anchor 影响 x 起点
    m = re.search(r'text-anchor="([^"]+)"', elem)
    anchor = m.group(1) if m else "start"
    if anchor == "middle":
        x0, x1 = x - text_w / 2, x + text_w / 2
    elif anchor == "end":
        x0, x1 = x - text_w, x
    else:
        x0, x1 = x, x + text_w
    # y 是 baseline · 上 ~0.8*fs · 下 ~0.5*fs (matches atomize shape extent
    # `y + 6.75 for fs=15`; slight overestimate to keep post-atomize buffer)
    y0, y1 = y - fs * 0.8, y + fs * 0.5
    return (x0, y0, x1, y1)


def _path_bbox(elem: str) -> Optional[Tuple[float, float, float, float]]:
    """path 的 bbox 粗估: 扫描 d 里所有绝对坐标数字对."""
    m = re.search(r'\bd="([^"]+)"', elem)
    if not m:
        return None
    d = m.group(1)
    # 提取所有数字 (含负号 / 小数)
    nums = re.findall(r'-?\d+\.?\d*', d)
    if len(nums) < 2:
        return None
    xs = [float(n) for i, n in enumerate(nums) if i % 2 == 0]
    ys = [float(n) for i, n in enumerate(nums) if i % 2 == 1]
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


# ─── bbox 汇总 ────────────────────────────────────────


def compute_content_bbox(
    svg: str,
    viewbox: Tuple[float, float, float, float],
    exclude_full_bg: bool = True,
) -> Optional[Tuple[float, float, float, float]]:
    """扫描 svg 里所有可视元素 · 返回 (x0, y0, x1, y1) 或 None.

    viewbox: 用于识别满版 bg rect (与 viewBox 尺寸吻合的 rect 视为背景)
    exclude_full_bg: True 时忽略与 viewBox 完全对齐的 rect
    """
    vx, vy, vw, vh = viewbox
    xs: List[float] = []
    ys: List[float] = []

    # rect
    for m in re.finditer(r'<rect\s+([^/>]+)/?>', svg):
        elem = m.group(0)
        bbox = _rect_bbox(elem)
        if bbox is None:
            continue
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        # 排除满版 bg (尺寸 >= viewBox 90% 且落在 viewBox 顶角附近)
        if exclude_full_bg and w >= vw * 0.9 and h >= vh * 0.9:
            continue
        xs.extend([x0, x1])
        ys.extend([y0, y1])

    # circle
    for m in re.finditer(r'<circle\s+([^/>]+)/?>', svg):
        bbox = _circle_bbox(m.group(0))
        if bbox:
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])

    # ellipse
    for m in re.finditer(r'<ellipse\s+([^/>]+)/?>', svg):
        bbox = _ellipse_bbox(m.group(0))
        if bbox:
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])

    # line
    for m in re.finditer(r'<line\s+([^/>]+)/?>', svg):
        bbox = _line_bbox(m.group(0))
        if bbox:
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])

    # text · 需要抓 tag 和内容
    for m in re.finditer(r'<text\s+([^>]+)>([^<]*)(?:<[^>]+>[^<]*</[^>]+>)*[^<]*</text>', svg):
        content = m.group(2) or ""
        bbox = _text_bbox("<text " + m.group(1) + ">", content)
        if bbox:
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])

    # path · 只扫 d 里的坐标 (marker/filter 里的 path 忽略)
    for m in re.finditer(r'<path\s+([^/>]+)/?>', svg):
        elem = m.group(0)
        # 排除 defs 里的 arrow marker path (viewBox 0 0 10 10 · d 里最大 ≤ 10)
        bbox = _path_bbox(elem)
        if bbox and (bbox[2] - bbox[0] > 20 or bbox[3] - bbox[1] > 20):
            xs.extend([bbox[0], bbox[2]])
            ys.extend([bbox[1], bbox[3]])

    if not xs or not ys:
        return None
    # 与 viewBox 求交 (排除超出的 arrow marker viewbox)
    x_min = max(vx, min(xs))
    y_min = max(vy, min(ys))
    x_max = min(vx + vw, max(xs))
    y_max = min(vy + vh, max(ys))
    if x_max <= x_min or y_max <= y_min:
        return None
    return (x_min, y_min, x_max, y_max)


# ─── 主 API ──────────────────────────────────────────


def shrink_viewbox(
    svg: str,
    *,
    pad_x: float = 12.0,
    pad_y: float = 12.0,
    shrink_bg: bool = True,
) -> str:
    """把 SVG 的 viewBox 收紧到实际内容 bbox + padding.

    pad_x/pad_y: 收紧后四边保留的呼吸空间
    shrink_bg: 同步把第一个满版 bg rect 收缩到新 viewBox 尺寸

    幂等: 无内容 / 无法解析时返回原字符串.
    """
    vb = extract_viewbox(svg)
    if not vb:
        return svg
    bbox = compute_content_bbox(svg, vb)
    if not bbox:
        return svg
    vx, vy, vw, vh = vb
    x0, y0, x1, y1 = bbox
    new_x = max(vx, x0 - pad_x)
    new_y = max(vy, y0 - pad_y)
    new_w = min(vx + vw - new_x, (x1 - new_x) + pad_x)
    new_h = min(vy + vh - new_y, (y1 - new_y) + pad_y)
    if new_w <= 0 or new_h <= 0:
        return svg

    # 用 rounded ints (小数位过多会让 embed 尺寸难算)
    new_x_s = f"{new_x:.0f}"
    new_y_s = f"{new_y:.0f}"
    new_w_s = f"{new_w:.0f}"
    new_h_s = f"{new_h:.0f}"

    new_svg = _VIEWBOX_RE.sub(
        f'viewBox="{new_x_s} {new_y_s} {new_w_s} {new_h_s}"',
        svg, count=1,
    )

    if shrink_bg:
        # 找到第一个满版 bg rect · 尺寸接近原 viewBox
        # <rect x="0" y="0" width="1400" height="720" fill="..."/>
        def _replace_bg(m: re.Match) -> str:
            elem = m.group(0)
            w = _attr(elem, "width") or 0
            h = _attr(elem, "height") or 0
            # 只替换满版尺寸的 rect
            if w >= vw * 0.9 and h >= vh * 0.9:
                new_elem = re.sub(r'\bx="[\d.\-]+"',  f'x="{new_x_s}"',  elem)
                new_elem = re.sub(r'\by="[\d.\-]+"',  f'y="{new_y_s}"',  new_elem)
                new_elem = re.sub(r'\bwidth="[\d.\-]+"',
                                    f'width="{new_w_s}"', new_elem)
                new_elem = re.sub(r'\bheight="[\d.\-]+"',
                                    f'height="{new_h_s}"', new_elem)
                return new_elem
            return elem

        new_svg = re.sub(r'<rect\s+[^/>]+/?>', _replace_bg, new_svg)

    return new_svg


def embed_sizes(
    viewbox: Tuple[float, float, float, float],
    scales: Tuple[float, ...] = (1.0, 0.8, 0.7, 0.6),
) -> Dict[str, Tuple[int, int]]:
    """按 viewBox 宽高比返回多档 <embed width height> 推荐尺寸.

    Returns:
        {"1.0": (w, h), "0.8": (...), "0.7": (...), "0.6": (...)}
        取整 · 保持宽高比与 viewBox 严格等比 (embed 不会拉伸).
    """
    _, _, vw, vh = viewbox
    if vw <= 0 or vh <= 0:
        return {}
    out: Dict[str, Tuple[int, int]] = {}
    for s in scales:
        w = int(round(vw * s))
        h = int(round(vh * s))
        out[f"{s:.1f}"] = (w, h)
    return out
