"""Keep native <line>s of an atomized exhibit from crossing native shape bodies or text glyphs (server lint
``bbox_overlap: line … crosses shape`` / ``line … crosses text``).

The server judges a line by its geometric segment against every visible filled shape: a gridline / baseline /
target line / divider running through a column, a Gantt bar or a dot is blocked, even though in the SVG the bar is
painted over the gridline. The rule (mirrored in scripts/xml_lint.py ``line_crosses_shape``): the segment's chord
through the body is ≥ 6px, the shape is not a hairline / text / ≥40%-canvas backdrop, and the line does not thread a
small marker's centre. A line lying exactly on a bar edge (the baseline under columns, a gridline at a stack
boundary) counts too, since its chord runs along the edge.

``uncross(frag)`` rewrites the fragment so no line crosses: a line flush with shape edges is nudged off them by
< 2px (one direction for all of them); otherwise the line is split into the pieces between the bodies — the visible
result equals the SVG where the bar hides the gridline. Arrow heads stay on the true end pieces.

Text: the server's ``line_crosses_text`` tests the segment against the label's estimated glyph box (eroded by
max(0.12·fontSize, 2px)); a gridline / connector / leader through a value label or annotation is blocked. Such a line
is split around the (un-eroded) glyph box plus TEXT_GAP — the label reads as knocked out of the rule.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

EDGE_TOL = 1.6      # a line within this distance of a shape edge is "on the edge": nudge rather than cut
NUDGE_GAP = 0.15    # clearance left after a nudge (the 1px stroke still meets the bar edge visually)
CUT_GAP = 0.6       # clearance left around a cut
MIN_PIECE = 2.0     # pieces shorter than this are dropped
TEXT_GAP = 1.5      # clearance left around a text label's glyph box

_LINE = re.compile(r'<line\b([^>]*?)(/>|>(.*?)</line>)', re.S)


def xml_lint():
    """scripts/xml_lint.py (the local mirror of the server lint), or None when unavailable."""
    scripts = str(Path(__file__).resolve().parents[2])
    if scripts not in sys.path:
        sys.path.append(scripts)
    try:
        import _exhibit_xml_lint as m
        return m
    except Exception:  # noqa: BLE001
        return None


def _num(attrs, k):
    m = re.search(rf'\b{k}="(-?[\d.]+(?:e-?\d+)?)"', attrs)
    return float(m.group(1)) if m else None


def _interval(p, q, s):
    """Parameter range [t0, t1] of segment p→q inside shape s (rect or ellipse, rotation aware), or None."""
    cx, cy = s["x"] + s["width"] / 2, s["y"] + s["height"] / 2
    hw, hh = s["width"] / 2, s["height"] / 2
    if hw <= 0 or hh <= 0:
        return None
    r = math.radians(-(s.get("rotation") or 0))
    sn, cs = math.sin(r), math.cos(r)

    def loc(x, y):
        dx, dy = x - cx, y - cy
        return dx * cs - dy * sn, dx * sn + dy * cs

    (ax, ay), (bx, by) = loc(*p), loc(*q)
    dx, dy = bx - ax, by - ay
    if s.get("type") == "ellipse":
        A = dx * dx / (hw * hw) + dy * dy / (hh * hh)
        B = 2 * (ax * dx / (hw * hw) + ay * dy / (hh * hh))
        C = ax * ax / (hw * hw) + ay * ay / (hh * hh) - 1
        disc = B * B - 4 * A * C
        if A == 0 or disc < 0:
            return None
        t0, t1 = (-B - math.sqrt(disc)) / (2 * A), (-B + math.sqrt(disc)) / (2 * A)
    else:
        t0, t1 = -math.inf, math.inf
        for d, dist in ((-dx, ax + hw), (dx, hw - ax), (-dy, ay + hh), (dy, hh - ay)):
            if d == 0:
                if dist < 0:
                    return None
                continue
            t = dist / d
            if d < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
        if t0 > t1:
            return None
    return t0, t1


def _crossing(xl, line, shapes, texts=()):
    """Obstacles the line crosses: shape bodies (as themselves) and text labels (as their glyph rect)."""
    hit = [s for s in shapes if xl.line_crosses_shape(line, s, 960, 540)]
    return hit + [r for t, r in texts if xl.line_crosses_text(line, t)]


def _text_obstacles(xl, frag):
    """[(text element, glyph rect padded by TEXT_GAP)] for every text the server's line rule would test."""
    out = []
    for t in xl.extract_elements(frag):
        if not xl.is_text_element(t) or not xl.has_text_content(t):
            continue
        try:
            g = xl.estimate_text_crossing_bbox(t)
        except Exception:  # noqa: BLE001
            g = None
        if g:
            out.append((t, {"type": "rect", "rotation": 0, "text": True, "x": g["x"] - TEXT_GAP,
                            "y": g["y"] - TEXT_GAP, "width": g["width"] + 2 * TEXT_GAP,
                            "height": g["height"] + 2 * TEXT_GAP}))
    return out


def _as_line(p, q, alpha):
    return {"kind": "line", "type": "line", "startX": p[0], "startY": p[1], "endX": q[0], "endY": q[1],
            "x": min(p[0], q[0]), "y": min(p[1], q[1]), "width": abs(q[0] - p[0]), "height": abs(q[1] - p[1]),
            "rotation": 0, "alpha": alpha, "visible": True}


def _nudge(p, q, hits):
    """Axis-aligned line flush with the edges of every crossed shape: shift it off them (one direction), else None."""
    horiz, vert = abs(p[1] - q[1]) < 1e-6, abs(p[0] - q[0]) < 1e-6
    if not (horiz or vert) or any(s.get("rotation") for s in hits):
        return None
    c = p[1] if horiz else p[0]
    shift = None
    for s in hits:
        lo, hi = (s["y"], s["y"] + s["height"]) if horiz else (s["x"], s["x"] + s["width"])
        if abs(c - lo) <= EDGE_TOL and c - lo < hi - c:
            need = lo - NUDGE_GAP - c          # move before the low edge (negative)
        elif abs(c - hi) <= EDGE_TOL:
            need = hi + NUDGE_GAP - c          # move past the high edge (positive)
        else:
            return None
        if shift is not None and (shift > 0) != (need > 0):
            return None
        shift = need if shift is None else (max(shift, need) if need > 0 else min(shift, need))
    if shift is None or abs(shift) > 2.2:
        return None
    return ((p[0], p[1] + shift), (q[0], q[1] + shift)) if horiz else ((p[0] + shift, p[1]), (q[0] + shift, q[1]))


def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _rewrite(attrs, body, p, q, keep_start, keep_end):
    a = attrs
    for k, v in (("startX", p[0]), ("startY", p[1]), ("endX", q[0]), ("endY", q[1])):
        a = re.sub(rf'\b{k}="[^"]*"', f'{k}="{_fmt(v)}"', a)
    a = re.sub(r'\sid="[^"]*"', "", a) if not (keep_start and keep_end) else a
    b = body or ""
    if not keep_start:
        b = re.sub(r"<startArrow\b[^>]*?(/>|>.*?</startArrow>)", "", b, flags=re.S)
    if not keep_end:
        b = re.sub(r"<endArrow\b[^>]*?(/>|>.*?</endArrow>)", "", b, flags=re.S)
    return f"<line{a}>{b}</line>"


def uncross(frag):
    """Return frag with every native line nudged / split so that none crosses a native shape body or text glyphs."""
    xl = xml_lint()
    if xl is None or "<line" not in frag:
        return frag
    try:
        shapes = [e for e in xl.extract_elements(frag) if xl.is_line_crossing_shape_candidate(e)]
        texts = _text_obstacles(xl, frag)
        lines = xl.extract_line_elements(frag)
    except Exception:  # noqa: BLE001
        return frag
    if not (shapes or texts) or not lines:
        return frag
    lines_iter = iter(lines)

    def one(m):
        attrs, body = m.group(1), m.group(3)
        coords = [_num(attrs, k) for k in ("startX", "startY", "endX", "endY")]
        if any(v is None for v in coords):
            return m.group(0)
        info = next(lines_iter, None)
        alpha = info["alpha"] if info else 1
        if info and xl.is_whole_series_line(info):
            return m.group(0)
        p, q = (coords[0], coords[1]), (coords[2], coords[3])
        hits = _crossing(xl, _as_line(p, q, alpha), shapes, texts)
        if not hits:
            return m.group(0)
        moved = None if any(h.get("text") for h in hits) else _nudge(p, q, hits)
        if moved and not _crossing(xl, _as_line(*moved, alpha), shapes, texts):
            return _rewrite(attrs, body, *moved, True, True)
        # split: drop the parameter ranges inside each crossed body (plus a small clearance)
        L = math.dist(p, q)
        if L < MIN_PIECE:
            return ""
        pad = CUT_GAP / L
        pt = lambda t_: (p[0] + (q[0] - p[0]) * t_, p[1] + (q[1] - p[1]) * t_)  # noqa: E731
        cuts = []
        for _ in range(4):   # pieces may still cross another shape (contained-chord exemptions no longer apply)
            for s in hits:
                iv = _interval(p, q, s)
                if iv:
                    cuts.append((max(0.0, iv[0] - pad), min(1.0, iv[1] + pad)))
            cuts.sort()
            keep, t = [], 0.0
            for a, b in cuts:
                if a > t:
                    keep.append((t, a))
                t = max(t, b)
            if t < 1:
                keep.append((t, 1.0))
            keep = [(a, b) for a, b in keep if (b - a) * L >= MIN_PIECE]
            hits = [s for a, b in keep for s in _crossing(xl, _as_line(pt(a), pt(b), alpha), shapes, texts)]
            if not hits:
                break
        return "".join(_rewrite(attrs, body, pt(a), pt(b), a <= 0, b >= 1) for a, b in keep)

    return _LINE.sub(one, frag)


def crossings(frag):
    """[(line, shape)] pairs the server reports as ``line … crosses shape`` (local mirror)."""
    xl = xml_lint()
    if xl is None:
        return []
    try:
        return [tuple(i["elements"]) for i in xl.detect_line_shape_crossings(frag, xl.extract_elements(frag), 1)]
    except Exception:  # noqa: BLE001
        return []


def text_crossings(frag):
    """[(line, text)] pairs the server reports as ``line … crosses text`` (local mirror)."""
    xl = xml_lint()
    if xl is None:
        return []
    try:
        return [tuple(i["elements"]) for i in xl.detect_line_text_crossings(frag, xl.extract_elements(frag), 1)]
    except Exception:  # noqa: BLE001
        return []
