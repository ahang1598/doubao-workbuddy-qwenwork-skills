"""Linear coordinate maps and bounded, piecewise function sampling."""

from __future__ import annotations

from dataclasses import dataclass
import math
import xml.etree.ElementTree as ET
from ..atomize_svg_to_slide._geometry import fmt
from ._geometry import Box, Geometry, Point, Curve, _attrs, _box, _finite, _ink_box, _point, group
from ._help import _drawing_api


def _increasing_range(value):
    low, high = _point(value)
    if high <= low or not math.isfinite(high - low):
        raise ValueError("Range must have finite, increasing endpoints and span")
    return low, high


@_drawing_api(
    "math",
    purpose="将数据或数学坐标线性映射到 SVG 区域。",
    returns="CoordinateMap",
    semantics=(
        "x_range/y_range 为递增的 (min, max)，viewport 为正宽高 Box。",
        "默认 y_up=True，将数学向上的 y 轴映射为 SVG 向下的 y 轴；False 保持同向。",
        "映射返回普通坐标，不裁切、不绑定对象；viewport 不是自动裁切窗口。",
    ),
    example="coords = CoordinateMap(x_range, y_range, Box(left, top, width, height))",
    limits=("目前提供线性坐标；不自动生成坐标轴、刻度或求导。",),
    rank=0,
)
@dataclass(frozen=True, init=False)
class CoordinateMap:
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    viewport: Box
    y_up: bool = True

    def __init__(self, x_range, y_range, viewport, *, y_up=True):
        object.__setattr__(self, "x_range", _increasing_range(x_range))
        object.__setattr__(self, "y_range", _increasing_range(y_range))
        object.__setattr__(self, "viewport", viewport)
        object.__setattr__(self, "y_up", y_up)
        if not isinstance(self.viewport, Box):
            raise TypeError("viewport must be a Box")
        if not isinstance(self.y_up, bool):
            raise TypeError("y_up must be bool")
        v = self.viewport
        if min(v.width, v.height) <= 0:
            raise ValueError("Viewport dimensions must be positive")
        _finite(v.x + v.width, v.y + v.height, *self._scales)
        if any(s == 0 for s in self._scales):
            raise ValueError("Coordinate scale underflows; use a smaller range")

    @property
    def _scales(self):
        return (
            self.viewport.width / (self.x_range[1] - self.x_range[0]),
            self.viewport.height / (self.y_range[1] - self.y_range[0]),
        )

    @_drawing_api(
        "math",
        purpose="把一个数学坐标变成 SVG 坐标。",
        returns="Point 快照",
        semantics=(
            "x/y 为原始数据值；返回 viewport 所在坐标系中的点。",
            "用于曲线、刻度、投影线和端口的同一套坐标换算。",
        ),
        example="point = coords.point(x, f(x))",
        common=False,
    )
    def point(self, x, y):
        x, y = _point((x, y))
        sx, sy = self._scales
        v = self.viewport
        return _point(
            (
                v.x + (x - self.x_range[0]) * sx,
                v.y + ((self.y_range[1] - y) if self.y_up else (y - self.y_range[0])) * sy,
            )
        )

    @_drawing_api(
        "math",
        purpose="换算位移或切线方向，保留两轴比例与 y 轴方向。",
        returns="Point 向量",
        semantics=(
            "不包含 viewport 平移；输入 (1, slope) 可得到数学切线在 SVG 中的方向。",
            "结果未单位化；slope 由调用方计算或提供。",
        ),
        example="dx, dy = coords.vector(1, slope)",
        common=False,
    )
    def vector(self, dx, dy):
        dx, dy = _point((dx, dy))
        sx, sy = self._scales
        return _point((dx * sx, dy * sy * (-1 if self.y_up else 1)))

    @_drawing_api(
        "math",
        purpose="将 SVG 点换回原始数学坐标。",
        returns="Point 快照",
        semantics=("输入与 viewport 使用同一坐标系；不会自动撤销后续 Node 变换。",),
        example="x, y = coords.inverse(svg_x, svg_y)",
        common=False,
    )
    def inverse(self, x, y):
        x, y = _point((x, y))
        sx, sy = self._scales
        v = self.viewport
        return _point(
            (
                self.x_range[0] + (x - v.x) / sx,
                self.y_range[1] - (y - v.y) / sy if self.y_up else self.y_range[0] + (y - v.y) / sy,
            )
        )


@dataclass(frozen=True)
class FunctionSample:
    """A numeric snapshot; segments use output coordinates, gaps use input x."""

    segments: tuple[tuple[Point, ...], ...]
    gaps: tuple[tuple[float, float], ...]
    evaluations: int
    closed: bool = False

    @_drawing_api(
        "curves",
        purpose="将连续采样段分别转换为 Curve。",
        returns="tuple[Curve, ...]",
        semantics=("每个连续段单独返回，不跨 gaps 相连；可用于 ribbon、repeat 或轮廓端口。",),
        example="curves = samples.curves()",
        common=False,
    )
    def curves(self):
        from ._curves import _polyline

        return tuple(Curve(_polyline(segment, self.closed)) for segment in self.segments)

    @_drawing_api(
        "math",
        purpose="将采样结果转成可组合的 SVG 几何。",
        returns="Geometry",
        semantics=(
            '每个连续段分别以 M 开始，不跨越空缺连线；默认 fill="none"，描边由调用方提供。',
            "无可见段时返回空几何；可继续 with_ports/group/Drawing.add。",
            "已经包含映射后的坐标，Drawing.add 默认 at=(0, 0) 保持落点；额外 at 会再平移。",
        ),
        example="curve = samples.to_geometry(stroke=color, stroke_width=line_width)",
        style=True,
        rank=2,
    )
    def to_geometry(self, **style):
        if not self.segments:
            return group()
        paint = {"fill": "none", **style}
        d = " ".join(
            ("M" if i == 0 else "L") + f" {fmt(x)} {fmt(y)}"
            for segment in self.segments
            for i, (x, y) in enumerate(segment)
        )
        if self.closed:
            d += " Z"
        element = ET.Element("path", {"d": d, **_attrs(paint)})
        return Geometry(element, _ink_box(_box(p for s in self.segments for p in s), paint, True))


def _clip_sample_line(a, b, box):
    """Clip an accepted straight segment; never join across an invisible run."""
    low, high = 0.0, 1.0
    for av, bv, minimum, maximum in ((a[0], b[0], box.x, box.x + box.width), (a[1], b[1], box.y, box.y + box.height)):
        delta = bv - av
        if delta == 0:
            if not minimum <= av <= maximum:
                return None
        else:
            enter, leave = sorted(((minimum - av) / delta, (maximum - av) / delta))
            low, high = max(low, enter), min(high, leave)
            if low > high:
                return None

    def at(t):
        if t == 0:
            return a
        if t == 1:
            return b
        return tuple((1 - t) * av + t * bv for av, bv in zip(a, b))

    return at(low), at(high)


@_drawing_api(
    "math",
    purpose="按精度采样单变量实函数，并保留不连续段。",
    returns="FunctionSample",
    semantics=(
        "function 是纯 Python callable(x)，x_range 为递增区间；不接受表达式字符串。",
        "mapping 可传 CoordinateMap；tolerance 是输出坐标中的插值误差阈值，默认 0.5。",
        "max_step 是输入 x 的最大初始步长，默认区间跨度/64；各段再按四分点和中点误差细分。",
        "breaks 是已知断点的 x 值（可含端点），这些位置不求值且两侧永不相连。",
        "ValueError/ZeroDivisionError/OverflowError、非有限值及达到 max_depth 仍不满足精度的区间会断开。",
        "segments 保存输出坐标的连续折线；gaps 保存输入 x 上被跳过的区间/断点；evaluations 为调用次数。",
        "clip=True 且有 mapping 时裁到 viewport；clip=False 保留区外曲线。裁切不计入 gaps。",
    ),
    example="samples = sample_function(f, x_range, mapping=coords, breaks=known_breaks)\ncurve = samples.to_geometry(**paint)",
    limits=(
        "有限采样不能证明连续或捕捉任意窄峰/高频振荡；已知断点显式传 breaks，高频内容减小 max_step。",
        "max_points 限制函数求值总次数，超限报错且不返回截断结果；max_depth 为每个初始区间的细分深度。",
        "不自动求导；TypeError 等编程错误继续抛出。裁切按采样折线进行，描边可能伸出 viewport。",
    ),
    rank=1,
)
def sample_function(
    function,
    x_range,
    *,
    mapping=None,
    breaks=(),
    tolerance=0.5,
    max_step=None,
    max_depth=16,
    max_points=8192,
    clip=True,
):
    return _sample_curve(
        function,
        x_range,
        mapping=mapping,
        breaks=breaks,
        tolerance=tolerance,
        max_step=max_step,
        max_depth=max_depth,
        max_points=max_points,
        clip=clip,
    )


def _sample_curve(
    function,
    x_range,
    *,
    mapping=None,
    breaks=(),
    tolerance=0.5,
    max_step=None,
    max_depth=16,
    max_points=8192,
    clip=True,
    parametric=False,
):
    if not callable(function):
        raise TypeError("function must be callable, not an expression string")
    if mapping is not None and not isinstance(mapping, CoordinateMap):
        raise TypeError("mapping must be CoordinateMap or None")
    low, high = _increasing_range(x_range)
    tolerance = float(tolerance)
    step = (high - low) / 64 if max_step is None else float(max_step)
    _finite(tolerance, step)
    if min(tolerance, step) <= 0:
        raise ValueError("tolerance and max_step must be positive")
    if type(max_depth) is not int or not 0 <= max_depth <= 30:
        raise ValueError("max_depth must be an integer from 0 to 30")
    if type(max_points) is not int or max_points < 5:
        raise ValueError("max_points must be an integer of at least 5")
    if not isinstance(clip, bool):
        raise TypeError("clip must be bool")
    cuts = sorted(set(float(b) for b in breaks))
    _finite(*cuts)
    if any(b < low or b > high for b in cuts):
        raise ValueError("breaks must be inside x_range (including endpoints)")
    ratio = (high - low) / step
    if not math.isfinite(ratio) or ratio > max_points:
        raise ValueError("max_step exceeds the max_points sampling budget")
    viewport = mapping.viewport if clip and mapping else None
    cache = {}
    segments = []
    current = []
    gaps = [(b, b) for b in cuts]

    def evaluate(x):
        if x not in cache:
            if len(cache) >= max_points:
                raise ValueError("Function sampling exceeds max_points; relax tolerance/max_step or increase budget")
            try:
                value = function(x)
            except (ValueError, ZeroDivisionError, OverflowError):
                value = math.nan
            point = None
            if parametric:
                if isinstance(value, float) and math.isnan(value):
                    raw = (math.nan, math.nan)
                else:
                    if not isinstance(value, (tuple, list)) or len(value) != 2:
                        raise TypeError("Parametric function must return a numeric (x, y) pair")
                    raw = tuple(float(v) for v in value)
            else:
                raw = (x, float(value))  # Bad return types are programming errors.
            if all(math.isfinite(v) for v in raw):
                try:
                    point = mapping.point(*raw) if mapping else raw
                except (ValueError, OverflowError):
                    pass
            cache[x] = point
        return cache[x]

    def flush():
        if len(current) > 1:
            segments.append(tuple(current))
        current.clear()

    def accept(a, b):
        line = _clip_sample_line(a, b, viewport) if viewport else (a, b)
        if line is None:
            flush()
            return
        a, b = line
        if current and current[-1] != a:
            flush()
        if a != b:
            if not current:
                current.append(a)
            current.append(b)

    def gap(a, b):
        flush()
        gaps.append((a, b))

    def refine(a, b, depth):
        xs = [a + (b - a) * t for t in (0, 0.25, 0.5, 0.75, 1)]
        xs[0], xs[-1] = a, b
        points = [evaluate(x) for x in xs]
        valid = [p for p in points if p is not None]
        if not valid:
            gap(a, b)
            return
        if len(valid) == 5:
            # A wholly offscreen sampled interval need not refine toward an asymptote.
            if viewport and any(
                all(p[axis] < lo for p in points) or all(p[axis] > hi for p in points)
                for axis, lo, hi in (
                    (0, viewport.x, viewport.x + viewport.width),
                    (1, viewport.y, viewport.y + viewport.height),
                )
            ):
                flush()
                return
            error = max(
                math.dist(points[i], tuple((1 - t) * points[0][k] + t * points[-1][k] for k in (0, 1)))
                if parametric
                else abs(points[i][1] - ((1 - t) * points[0][1] + t * points[-1][1]))
                for i, t in ((1, 0.25), (2, 0.5), (3, 0.75))
            )
            if error <= tolerance:
                accept(points[0], points[-1])
                return
        mid = xs[2]
        if depth >= max_depth or mid in (a, b):
            gap(a, b)
            return
        refine(a, mid, depth + 1)
        refine(mid, b, depth + 1)

    boundaries = sorted({low, high, *cuts})
    for a, b in zip(boundaries, boundaries[1:]):
        start = math.nextafter(a, b) if a in cuts else a
        stop = math.nextafter(b, a) if b in cuts else b
        flush()
        if start >= stop:
            gap(a, b)
            continue
        count = max(1, math.ceil((stop - start) / step))
        for i in range(count):
            left = start + (stop - start) * (i / count)
            right = stop if i + 1 == count else start + (stop - start) * ((i + 1) / count)
            refine(left, right, 0)
    flush()
    merged = []
    for a, b in sorted(gaps):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return FunctionSample(tuple(segments), tuple(merged), len(cache))


@_drawing_api(
    "curves",
    purpose="按输出精度采样二维参数曲线。",
    returns="FunctionSample",
    semantics=(
        "function(t) 返回 (x, y)，t_range 递增；mapping 可将数学坐标映射到 SVG。",
        "tolerance 是二维插值距离阈值；max_step 是参数初始步长，默认跨度/64。",
        "breaks、gaps、max_depth、max_points 与 sample_function 含义一致；错误或未收敛处断开。",
        "closed=True 要求单一完整连续段且首尾相距不超过 tolerance；否则报错，不跨断点闭合。",
        "默认 clip=False 保留完整轮廓；指定 mapping 且 clip=True 时裁到 viewport。",
    ),
    example="samples = sample_parametric(position_at_t, t_range, closed=True)\npart = samples.to_geometry(**paint)",
    limits=("有限采样不能保证发现任意高频或窄细节；闭合和开闭端点含义由调用方确定。",),
)
def sample_parametric(
    function,
    t_range,
    *,
    mapping=None,
    breaks=(),
    tolerance=0.5,
    max_step=None,
    max_depth=16,
    max_points=8192,
    clip=False,
    closed=False,
):
    result = _sample_curve(
        function,
        t_range,
        mapping=mapping,
        breaks=breaks,
        tolerance=tolerance,
        max_step=max_step,
        max_depth=max_depth,
        max_points=max_points,
        clip=clip,
        parametric=True,
    )
    if closed:
        if (
            len(result.segments) != 1
            or result.gaps
            or math.dist(result.segments[0][0], result.segments[0][-1]) > tolerance
        ):
            raise ValueError("Closed sampling requires a complete continuous curve with matching endpoints")
        segment = result.segments[0]
        segment = segment[:-1] + (segment[0],)
        if len(set(segment)) < 3:
            raise ValueError("Closed sampling needs at least three distinct points")
        result = FunctionSample((segment,), result.gaps, result.evaluations, True)
    return result
