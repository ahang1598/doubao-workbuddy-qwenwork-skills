"""Automatic placement of labels and callouts (queued, placed at output time, largest anchors first)."""

from __future__ import annotations

import math

from ._page import _seg_hits_box
from ._text import tw, wrap

_DIRS = {
    "E": (1, 0, "start"), "W": (-1, 0, "end"), "N": (0, -1, "middle"), "S": (0, 1, "middle"),
    "NE": (1, -1, "start"), "NW": (-1, -1, "end"), "SE": (1, 1, "start"), "SW": (-1, 1, "end"),
}
_ALL = ("E", "W", "NE", "NW", "N", "S", "SE", "SW")


def _place_now(ex, x, y, rows, size, r, gap, prefer, weights, fills, lh, ignore_circle, bounds=None):
    from ._page import lint_w
    widths = [lint_w(t, size, bold=w >= 600) for t, w in zip(rows, weights)]
    W, H = max(widths), size * lh * (len(rows) - 1) + size * 1.02
    best = None
    for k, extra in enumerate((0, 8, 18, 32, 50, 75, 105, 140)):
        for i, d in enumerate(prefer):
            dx, dy, anchor = _DIRS[d]
            shifts = (0, -1, 1, -2, 2, -3, 3) if dy == 0 else (0,)
            for si, sh in enumerate(shifts):
                dist = r + gap + extra
                ax_ = x + dx * (dist if dy == 0 else dist * 0.75)
                if dy < 0:
                    top = y - dist - H if dx == 0 else y - dist * 0.75 - H * 0.6
                elif dy > 0:
                    top = y + dist if dx == 0 else y + dist * 0.75 - H * 0.4
                else:
                    top = y - H / 2 + sh * (H + 3)
                x0 = ax_ - W if anchor == "end" else (ax_ - W / 2 if anchor == "middle" else ax_)
                box = (x0, top, x0 + W, top + H)
                bb = None
                if bounds is not None:
                    pb = ex._panel or (ex.m, 0, ex.w - ex.m, ex.h)
                    bb = (max(bounds[0], pb[0]), max(bounds[1], pb[1]), min(bounds[2], pb[2]), min(bounds[3], pb[3]))
                c = ex.cost(box, bounds=bb, ignore_circle=ignore_circle) + i * 2 + k * 18 + si * 6
                if c >= 1e6:
                    continue
                c += _ambiguous(ex, box, x, y, r, ignore_circle)
                tx, ty = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
                if math.hypot(tx - x, ty - y) - r > 12:  # leader would be drawn: it must not cross texts / marks
                    for e in ex.reg:
                        if e["kind"] == "text" and _seg_hits_box((x, y), (tx, ty), e["box"], pad=1):
                            c += 70
                        elif e["kind"] == "line" and e["tag"] == "leader":
                            p, q = e["box"]
                            if _segs_cross((x, y), (tx, ty), p, q):
                                c += 70
                        elif e["kind"] == "mark" and e["circle"] is not None and e["circle"] != ignore_circle:
                            cx_, cy_, rr = e["circle"]
                            if _seg_circle((x, y), (tx, ty), cx_, cy_, rr):
                                c += 40
                if best is None or c < best[0]:
                    best = (c, box, anchor, ax_, top)
        if best is not None and best[0] < 40 + k * 18:
            break
    if best is not None and best[0] >= 300:
        if bounds is not None:
            alt = _probe_cost(ex, x, y, W, H, r, gap, prefer, ignore_circle, left=bounds[0])
            if alt is not None and alt[0] < best[0]:
                best = alt
        if best[0] >= 300:  # still crowded: free-space grid search within 170px, leader drawn automatically
            alt = _grid_search(ex, x, y, W, H, r, ignore_circle, bounds)
            if alt is not None and alt[0] < best[0]:
                best = alt
    if best is None and bounds is not None:   # nothing fits inside the plot: relax to the panel (still right of y axis)
        best = _probe_cost(ex, x, y, W, H, r, gap, prefer, ignore_circle, left=bounds[0])
    if best is None:
        best = (0, (x + r + gap, y - H / 2, x + r + gap + W, y + H / 2), "start", x + r + gap, y - H / 2)
    _, box, anchor, ax_, top = best
    for i, (t, w, f) in enumerate(zip(rows, weights, fills)):
        ex.text(ax_, top + size * 0.80 + i * size * lh, t, size=size, weight=w, fill=f, anchor=anchor)
    tx, ty = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
    if math.hypot(tx - x, ty - y) - r > 12:
        ang = math.atan2(ty - y, tx - x)
        ex.line(x + math.cos(ang) * (r + 1.5), y + math.sin(ang) * (r + 1.5), tx - math.cos(ang) * 2,
                ty - math.sin(ang) * 2, stroke=ex.C["context"], width=0.7, tag="leader")
    return box


def _probe_cost(ex, x, y, W, H, r, gap, prefer, ignore_circle, left=None):
    """Cheapest panel-wide candidate (no drawing); same geometry as _place_now."""
    best = None
    for k, extra in enumerate((0, 8, 18, 32, 50, 75, 105, 140)):
        for i, d in enumerate(prefer):
            dx, dy, anchor = _DIRS[d]
            for si, sh in enumerate((0, -1, 1, -2, 2, -3, 3) if dy == 0 else (0,)):
                dist = r + gap + extra
                ax_ = x + dx * (dist if dy == 0 else dist * 0.75)
                if dy < 0:
                    top = y - dist - H if dx == 0 else y - dist * 0.75 - H * 0.6
                elif dy > 0:
                    top = y + dist if dx == 0 else y + dist * 0.75 - H * 0.4
                else:
                    top = y - H / 2 + sh * (H + 3)
                x0 = ax_ - W if anchor == "end" else (ax_ - W / 2 if anchor == "middle" else ax_)
                box = (x0, top, x0 + W, top + H)
                pb = ex._panel or (ex.m, 0, ex.w - ex.m, ex.h)
                bb = (max(pb[0], left if left is not None else pb[0]), pb[1], pb[2], pb[3])
                c = ex.cost(box, bounds=bb, ignore_circle=ignore_circle) + i * 2 + k * 18 + si * 6 + 60
                c += _ambiguous(ex, box, x, y, r, ignore_circle)
                if best is None or c < best[0]:
                    best = (c, box, anchor, ax_, top)
    return best


def _grid_search(ex, x, y, W, H, r, ignore_circle, bounds, radius=170, step=8):
    pb = ex._panel or (ex.m, 0, ex.w - ex.m, ex.h)
    bb = pb if bounds is None else (max(bounds[0], pb[0]), pb[1], pb[2], pb[3])
    best = None
    for dy in range(-radius, radius + 1, step):
        for dx in range(-radius, radius + 1, step):
            d = math.hypot(dx, dy)
            if d > radius or d < r:
                continue
            for anchor in ("start", "end"):
                ax_ = x + dx
                x0 = ax_ if anchor == "start" else ax_ - W
                top = y + dy - H / 2
                box = (x0, top, x0 + W, top + H)
                c = ex.cost(box, bounds=bb, ignore_circle=ignore_circle)
                if c >= 1e6:
                    continue
                tx, ty = min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3])
                for e in ex.reg:
                    if e["kind"] == "text" and _seg_hits_box((x, y), (tx, ty), e["box"], pad=1):
                        c += 70
                    elif e["kind"] == "line" and e["tag"] == "leader" and _segs_cross((x, y), (tx, ty), *e["box"]):
                        c += 70
                c += 1.2 * math.hypot(tx - x, ty - y) + 80 + _ambiguous(ex, box, x, y, r, ignore_circle)
                if best is None or c < best[0]:
                    best = (c, box, anchor, ax_, top)
    return best


def _ambiguous(ex, box, x, y, r, ignore_circle):
    """A label sitting nearer another bubble than its own reads as that bubble's label."""
    def gap(cx, cy, rr):
        dx = max(box[0] - cx, 0, cx - box[2])
        dy = max(box[1] - cy, 0, cy - box[3])
        return math.hypot(dx, dy) - rr
    own = gap(x, y, r)
    if own < 6:
        return 0
    for e in ex.reg:
        if e["kind"] == "mark" and e["circle"] is not None and e["circle"] != ignore_circle:
            cx_, cy_, rr = e["circle"]
            if rr >= 3 and gap(cx_, cy_, rr) + 4 < own:
                return 90
    return 0


def _segs_cross(p1, p2, q1, q2):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(q1, q2, p1), orient(q1, q2, p2)
    d3, d4 = orient(p1, p2, q1), orient(p1, p2, q2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _seg_circle(p, q, cx, cy, r):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = dx * dx + dy * dy or 1
    t = max(0, min(1, ((cx - p[0]) * dx + (cy - p[1]) * dy) / L))
    nx, ny = p[0] + t * dx, p[1] + t * dy
    return (nx - cx) ** 2 + (ny - cy) ** 2 < (r - 1) ** 2


def place_label(ex, x, y, rows, size=11, r=0.0, gap=5, prefer=_ALL, weights=None, fills=None, lh=1.22,
                priority=1, _circle=None, bounds=None):
    """Queue a (multi-line) label for anchor (x, y) with radius r. Placed at save() inside the current panel."""
    rows = [rows] if isinstance(rows, str) else list(rows)
    weights = weights or [400] * len(rows)
    fills = fills or [None] * len(rows)
    ex.queue.append(dict(priority=priority, r=r, panel=ex._panel,
                         fn=lambda: _place_now(ex, x, y, rows, size, r, gap, prefer, weights, fills, lh, _circle, bounds)))



def _callout_now(ex, target, rows, size, prefer, dist, italic, target_r, style):
    """style:
      'leader' (default) – plain text box beside the target, joined by a thin straight elbow leader (no arrowhead):
                           horizontal from the box edge, then straight to the target (McKinsey-style callout).
      'tag'              – the note sits right next to the target with no line at all (short labels on bars/points).
      'arrow'            – curved arrow (only for "this movement / this jump" annotations).
    """
    from ._page import lint_w
    W = max(lint_w(r, size) for r in rows)   # the server's width: a leader starting inside it "crosses the text"
    H = size * 1.22 * (len(rows) - 1) + size * 1.02
    tx, ty = target
    best = None
    dists = [4, 8, 14] if style == "tag" else [dist, dist * 1.35, dist * 1.8, dist * 2.4, dist * 3.0]
    order = prefer if style != "leader" else tuple(k for k in prefer if k in ("E", "W", "NE", "NW", "SE", "SW")) or prefer
    for k, d in enumerate(dists):
        for i, key in enumerate(order):
            dx, dy, _ = _DIRS[key]
            n = math.hypot(dx, dy)
            gap = d + target_r
            cx = tx + dx / n * gap + dx * W / 2
            cy = ty + dy / n * gap + dy * H / 2
            box = (cx - W / 2, cy - H / 2, cx + W / 2, cy + H / 2)
            frm = (min(max(tx, box[0]), box[2]), min(max(ty, box[1]), box[3]))
            c = ex.cost(box) + i * 3 + k * 26
            if style != "tag":
                for e in ex.reg:
                    if e["kind"] == "text" and _seg_hits_box(frm, (tx, ty), e["box"], pad=1):
                        c += 80
            if best is None or c < best[0]:
                best = (c, box, key)
        if best[0] < 70:
            break
    _, box, key = best
    fill = ex.C["text"] if not italic else ex.C["sub"]
    for i, r in enumerate(rows):
        ex.text(box[0], box[1] + size * 0.80 + i * size * 1.22, r, size=size, italic=italic, fill=fill)
    if style == "tag":
        return
    if style == "leader":
        # attach at the vertical middle of the first line, on the side facing the target
        ay = box[1] + size * 0.45
        ax_ = box[0] - 4 if tx < box[0] else (box[2] + 4 if tx > box[2] else (box[0] + box[2]) / 2)
        if box[0] <= tx <= box[2]:          # target straight above/below: short vertical leader
            ay = box[3] + 3 if ty > box[3] else box[1] - 3
            pts = [(tx, ay), (tx, ty - (target_r + 2) * (1 if ty > ay else -1))]
        else:
            elbow_x = tx + (target_r + 6) * (1 if ax_ > tx else -1)
            ang = math.atan2(ty - ay, elbow_x - ax_)
            end = (tx + (target_r + 2) * (1 if ax_ > tx else -1), ty)
            pts = [(ax_, ay), (elbow_x, ay), end] if abs(ty - ay) > 3 else [(ax_, ay), end]
        ex.path("M" + " L".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts), stroke=ex.C["context"], width=0.8, register=False)
        ex.circle(pts[-1][0], pts[-1][1], 1.8, ex.C["text"], register=False)
        for p, q in zip(pts, pts[1:]):
            ex._add("line", (p, q), "callout")
        return
    sx_, sy_ = min(max(tx, box[0]), box[2]), min(max(ty, box[1]), box[3])
    if box[0] <= tx <= box[2]:
        sy_ = box[3] + 3 if ty > box[3] else box[1] - 3
    elif box[1] <= ty <= box[3]:
        sx_ = box[2] + 3 if tx > box[2] else box[0] - 3
    else:
        sy_ += 3 if ty > box[3] else -3
    ang = math.atan2(ty - sy_, tx - sx_)
    ex_, ey_ = tx - math.cos(ang) * (target_r + 3), ty - math.sin(ang) * (target_r + 3)
    mx, my = (sx_ + ex_) / 2, (sy_ + ey_) / 2
    bcx, bcy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    nx, ny = -(ey_ - sy_), (ex_ - sx_)
    nlen = math.hypot(nx, ny) or 1
    sign = 1 if (nx * (mx - bcx) + ny * (my - bcy)) > 0 else -1
    bow = 0.18 * math.hypot(ex_ - sx_, ey_ - sy_)
    qx, qy = mx + sign * nx / nlen * bow, my + sign * ny / nlen * bow
    ex.path(f"M{sx_:.1f},{sy_:.1f} Q{qx:.1f},{qy:.1f} {ex_:.1f},{ey_:.1f}", stroke=ex.C["text"], width=0.9, marker="arr",
            register=False)
    ex._add("line", ((sx_, sy_), (ex_, ey_)), "callout")


def callout(ex, target, text, width=150, size=10.5, prefer=("E", "W", "NE", "NW", "SE", "SW", "N", "S"), dist=22,
            italic=False, target_r=0, style="leader"):
    """Queue a note for target=(px, py); placed at output after point labels.

    style='leader' (default): text beside the target + thin straight elbow leader ending in a small dot.
    style='tag': short note right next to the target, no line. style='arrow': curved arrow — use sparingly, only
    for a movement/jump; most chart notes should be leader or tag. Prefer stating the insight in the page XML
    (side text / numbered takeaways) over many in-chart notes; ≤2 callouts per chart.
    """
    rows = wrap(text, size, width)
    ex.notes += 1   # a callout on the data point is an argument annotation
    ex.queue.append(dict(priority=1, panel=ex._panel,
                         fn=lambda: _callout_now(ex, target, rows, size, prefer, dist, italic, target_r, style)))
