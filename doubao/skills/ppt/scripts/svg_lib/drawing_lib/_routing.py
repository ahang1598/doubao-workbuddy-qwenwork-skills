"""Caller-controlled waypoints and bounded rectilinear obstacle routing."""

from __future__ import annotations

import heapq
import math
from functools import lru_cache
from ..atomize_svg_to_slide._geometry import fmt
from ._geometry import _unit


def inside(point, box):
    return box.x < point[0] < box.x + box.width and box.y < point[1] < box.y + box.height


def crosses(a, b, box):
    """Whether a segment crosses an open rectangle; touching its rim is allowed."""
    low, high = 0.0, 1.0
    for av, bv, lo, hi in ((a[0], b[0], box.x, box.x + box.width), (a[1], b[1], box.y, box.y + box.height)):
        delta = bv - av
        if abs(delta) < 1e-12:
            if not lo < av < hi:
                return False
        else:
            enter, leave = sorted(((lo - av) / delta, (hi - av) / delta))
            low, high = max(low, enter), min(high, leave)
            if high - low <= 1e-12:
                return False
    return high > 0 and low < 1 and high - low > 1e-12


def _simplify(points):
    result = []
    for point in points:
        if result and point == result[-1]:
            continue
        while len(result) > 1:
            a, b = result[-2:]
            u = (b[0] - a[0], b[1] - a[1])
            v = (point[0] - b[0], point[1] - b[1])
            if abs(u[0] * v[1] - u[1] * v[0]) < 1e-9 and u[0] * v[0] + u[1] * v[1] > 0:
                result.pop()
            else:
                break
        result.append(point)
    return result


def _orthogonal(start, end, obstacles, bend_penalty):
    if any(inside(p, b) for p in (start, end) for b in obstacles):
        raise ValueError(
            "Endpoint or waypoint lies inside an avoidance area; exclude endpoint objects or change lead/clearance"
        )
    if start == end:
        return [start]
    xs = sorted({start[0], end[0], *(v for b in obstacles for v in (b.x, b.x + b.width))})
    ys = sorted({start[1], end[1], *(v for b in obstacles for v in (b.y, b.y + b.height))})
    si, sj = xs.index(start[0]), ys.index(start[1])
    ei, ej = xs.index(end[0]), ys.index(end[1])

    @lru_cache(maxsize=None)
    def allowed(i, j):
        return not any(inside((xs[i], ys[j]), b) for b in obstacles)

    @lru_cache(maxsize=None)
    def visible(i, j, k, l):
        return not any(crosses((xs[i], ys[j]), (xs[k], ys[l]), b) for b in obstacles)

    state = (si, sj, 0)
    costs = {state: 0.0}
    parents = {}
    queue = [(0.0, state)]
    goal = None
    while queue:
        cost, current = heapq.heappop(queue)
        if cost != costs[current]:
            continue
        i, j, axis = current
        if (i, j) == (ei, ej):
            goal = current
            break
        for k, l, new_axis in ((i - 1, j, 1), (i + 1, j, 1), (i, j - 1, 2), (i, j + 1, 2)):
            if not (0 <= k < len(xs) and 0 <= l < len(ys)) or not allowed(k, l) or not visible(i, j, k, l):
                continue
            candidate = (k, l, new_axis)
            distance = abs(xs[k] - xs[i]) + abs(ys[l] - ys[j])
            new_cost = cost + distance + (bend_penalty if axis and axis != new_axis else 0)
            if new_cost < costs.get(candidate, math.inf):
                costs[candidate] = new_cost
                parents[candidate] = current
                heapq.heappush(queue, (new_cost, candidate))
    if goal is None:
        raise ValueError("No orthogonal route satisfies the supplied avoidance regions")
    result = []
    while True:
        i, j, _ = goal
        result.append((xs[i], ys[j]))
        if goal == state:
            break
        goal = parents[goal]
    return _simplify(result[::-1])


def routed_path(a, b, waypoints, start_normal, end_normal, lead, route, obstacles, clearance):
    if route == "bezier":
        points = [a] + list(waypoints) + [b]
        if any(math.dist(p, q) <= 1e-12 for p, q in zip(points, points[1:])):
            raise ValueError("Bezier waypoints must be distinct from adjacent points")
        tangents = []
        for i, p in enumerate(points):
            if i == 0:
                t = start_normal or _unit((points[1][0] - p[0], points[1][1] - p[1]))
            elif i == len(points) - 1:
                t = (
                    tuple(-v for v in end_normal)
                    if end_normal
                    else _unit((p[0] - points[i - 1][0], p[1] - points[i - 1][1]))
                )
            else:
                delta = (points[i + 1][0] - points[i - 1][0], points[i + 1][1] - points[i - 1][1])
                t = _unit(delta if math.hypot(*delta) > 1e-12 else (points[i + 1][0] - p[0], points[i + 1][1] - p[1]))
            tangents.append(t)
        commands = [f"M {fmt(a[0])} {fmt(a[1])}"]
        for i, (p, q) in enumerate(zip(points, points[1:])):
            h = min(lead, math.dist(p, q) / 3)
            c = tuple(p[k] + h * tangents[i][k] for k in (0, 1))
            e = tuple(q[k] - h * tangents[i + 1][k] for k in (0, 1))
            commands.append("C " + " ".join(fmt(v) for point in (c, e, q) for v in point))
        return " ".join(commands)
    start = tuple(a[k] + lead * start_normal[k] for k in (0, 1)) if start_normal else a
    end = tuple(b[k] + lead * end_normal[k] for k in (0, 1)) if end_normal else b
    stops = [start] + list(waypoints) + [end]
    if route == "orthogonal":
        padded = [box.padded(clearance) for box in obstacles]
        if any(crosses(p, q, box) for p, q in ((a, start), (end, b)) for box in padded):
            raise ValueError("Port lead crosses an avoidance area; change the direction or lead distance")
        points = [a]
        for p, q in zip(stops, stops[1:]):
            points.extend(_orthogonal(p, q, padded, max(1, clearance * 0.1)))
        points.append(b)
    else:
        points = [a] + stops + [b]
    points = _simplify(points)
    if len(points) < 2:
        raise ValueError("Connector endpoints define no length")
    return "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in points)
