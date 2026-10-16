"""Identity-aware glyph obstacles and leader routing in screen coordinates."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from ._academic_rigor import BBox


def _point_segment_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    squared = dx * dx + dy * dy
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / squared)) if squared else 0
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _segment_distance(a, b, c, d):
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    ab0, ab1, cd0, cd1 = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
    if ab0 * ab1 < 0 and cd0 * cd1 < 0:
        return 0.0
    return min(
        _point_segment_distance(a, c, d),
        _point_segment_distance(b, c, d),
        _point_segment_distance(c, a, b),
        _point_segment_distance(d, a, b),
    )


def _in_polygon(point, vertices):
    x, y = point
    inside = False
    for index, a in enumerate(vertices):
        b = vertices[(index + 1) % len(vertices)]
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


@dataclass(frozen=True)
class Obstacle:
    owner: object
    kind: str
    vertices: tuple
    radius: float = 0.0
    padding: float = 1.2

    @property
    def box(self):
        xs, ys = zip(*self.vertices)
        pad = self.radius + self.padding
        return BBox(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def intersects(self, a, b):
        if self.kind == "circle":
            return _point_segment_distance(self.vertices[0], a, b) < self.radius + self.padding
        if self.kind == "segment":
            return _segment_distance(a, b, *self.vertices) < self.radius + self.padding
        if _in_polygon(a, self.vertices) or _in_polygon(b, self.vertices):
            return True
        return any(
            _segment_distance(a, b, p, self.vertices[(i + 1) % len(self.vertices)]) < self.padding
            for i, p in enumerate(self.vertices)
        )

    def contains(self, point):
        return self.intersects(point, point)


def marker_obstacle(owner, x, y, r, shape):
    if shape == "none" or r <= 0:
        return None
    if shape == "circle":
        return Obstacle(owner, "circle", ((x, y),), r)
    if shape == "square":
        vertices = ((x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r))
    elif shape == "diamond":
        vertices = ((x, y - r * 1.3), (x + r * 1.3, y), (x, y + r * 1.3), (x - r * 1.3, y))
    else:
        vertices = ((x, y - r * 1.4), (x + r * 1.2, y + r * 0.7), (x - r * 1.2, y + r * 0.7))
    return Obstacle(owner, "polygon", vertices)


def segment_obstacle(owner, a, b, width=1.2):
    return Obstacle(owner, "segment", (a, b), width / 2)


def obstacle_box(obstacle):
    return obstacle.box if isinstance(obstacle, Obstacle) else BBox(*obstacle)


def _coerce(obstacles):
    result = []
    for i, obstacle in enumerate(obstacles):
        if isinstance(obstacle, Obstacle):
            result.append(obstacle)
        else:
            x0, y0, x1, y1 = obstacle
            result.append(Obstacle(("anonymous", i), "polygon", ((x0, y0), (x1, y0), (x1, y1), (x0, y1)), padding=0))
    return result


def _route(start, end, obstacles, bounds):
    # Short A* edges only need local glyphs. A spatial index preserves exact
    # shape tests without scanning hundreds of distant points at every step.
    cell_size = 32.0
    buckets = {}
    for index, obstacle in enumerate(obstacles):
        box = obstacle.box
        for ix in range(math.floor(box.x0 / cell_size), math.floor(box.x1 / cell_size) + 1):
            for iy in range(math.floor(box.y0 / cell_size), math.floor(box.y1 / cell_size) + 1):
                buckets.setdefault((ix, iy), []).append(index)

    def clear(a, b):
        candidates = set()
        for ix in range(math.floor(min(a[0], b[0]) / cell_size), math.floor(max(a[0], b[0]) / cell_size) + 1):
            for iy in range(math.floor(min(a[1], b[1]) / cell_size), math.floor(max(a[1], b[1]) / cell_size) + 1):
                candidates.update(buckets.get((ix, iy), ()))
        return not any(obstacles[index].intersects(a, b) for index in candidates)

    if clear(start, end):
        return [start, end]
    step = 4.0
    x0 = min(start[0], min((o.box.x0 for o in obstacles), default=start[0])) - 12
    y0, y1 = bounds.y0 - 10, bounds.y1 + 10
    nx, ny = math.ceil((end[0] - x0) / step), math.ceil((y1 - y0) / step)

    def point(node):
        return (x0 + node[0] * step, y0 + node[1] * step)

    blocked = set()
    for obstacle in obstacles:
        box = obstacle.box
        for ix in range(max(0, math.floor((box.x0 - x0) / step) - 1), min(nx, math.ceil((box.x1 - x0) / step) + 1) + 1):
            for iy in range(
                max(0, math.floor((box.y0 - y0) / step) - 1), min(ny, math.ceil((box.y1 - y0) / step) + 1) + 1
            ):
                if obstacle.contains(point((ix, iy))):
                    blocked.add((ix, iy))
    costs = {}
    parents = {}
    queue = []
    sx, sy = round((start[0] - x0) / step), round((start[1] - y0) / step)
    for ix in range(max(0, sx - 3), min(nx, sx + 3) + 1):
        for iy in range(max(0, sy - 3), min(ny, sy + 3) + 1):
            node = (ix, iy)
            location = point(node)
            if node in blocked or not clear(start, location):
                continue
            cost = math.dist(start, location)
            costs[node] = cost
            parents[node] = None
            heapq.heappush(queue, (cost + math.dist(location, end), cost, node))
    found = None
    while queue:
        _, cost, node = heapq.heappop(queue)
        if cost != costs[node]:
            continue
        location = point(node)
        if abs(location[0] - end[0]) < step * 3 and clear(location, end):
            found = node
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nxt = node[0] + dx, node[1] + dy
            if not (0 <= nxt[0] <= nx and 0 <= nxt[1] <= ny) or nxt in blocked:
                continue
            destination = point(nxt)
            if not clear(location, destination):
                continue
            next_cost = cost + math.dist(location, destination)
            if next_cost < costs.get(nxt, math.inf):
                costs[nxt] = next_cost
                parents[nxt] = node
                heapq.heappush(queue, (next_cost + math.dist(destination, end), next_cost, nxt))
    if found is None:
        return None
    route = [end]
    while found is not None:
        route.append(point(found))
        found = parents[found]
    route.append(start)
    route.reverse()
    simplified = [route[0]]
    i = 0
    while i < len(route) - 1:
        j = len(route) - 1
        while j > i + 1 and not clear(route[i], route[j]):
            j -= 1
        simplified.append(route[j])
        i = j
    return simplified


def route_leader(start, end, occupied, bounds, source_owner=None):
    """Only source-owned shapes may be crossed."""
    all_obstacles = _coerce(occupied)
    others = [o for o in all_obstacles if o.owner != source_owner]
    if not any(o.contains(start) for o in others):
        route = _route(start, end, others, bounds)
        if route:
            return route
    source = next((o for o in all_obstacles if o.owner == source_owner and o.kind in ("circle", "polygon")), None)
    if source is not None:
        if source.kind == "circle":
            radius = source.radius + source.padding + 1
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            candidates = [
                (
                    start[0] + radius * math.cos(angle + i * math.tau / 48),
                    start[1] + radius * math.sin(angle + i * math.tau / 48),
                )
                for i in range(48)
            ]
        else:
            candidates = []
            for vertex in source.vertices:
                dx, dy = vertex[0] - start[0], vertex[1] - start[1]
                factor = 1 + (source.padding + 1) / max(1, math.hypot(dx, dy))
                candidates.append((start[0] + dx * factor, start[1] + dy * factor))
        for candidate in sorted(candidates, key=lambda p: math.dist(p, end)):
            if any(o.contains(candidate) for o in all_obstacles):
                continue
            route = _route(candidate, end, all_obstacles, bounds)
            if route:
                return route
    raise ValueError("point label has no unobstructed visible attachment; increase space between observations")
