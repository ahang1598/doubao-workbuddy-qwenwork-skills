"""Shared internals of the composite parts (the public parts live in the ``_*_parts`` modules)."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from ..atomize_svg_to_slide._geometry import fmt
from ._geometry import Geometry, _attrs

_STYLES = ("rich", "flat")
_INK = "#26313D"
_PORT_SIDES = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _with_edges(geometry, **extra):
    b = geometry.bounds
    edges = {
        "top": (b.x + b.width / 2, b.y),
        "bottom": (b.x + b.width / 2, b.y + b.height),
        "left": (b.x, b.y + b.height / 2),
        "right": (b.x + b.width, b.y + b.height / 2),
        "center": (b.x + b.width / 2, b.y + b.height / 2),
    }
    edges.update(extra)
    g = geometry.with_ports(**edges)
    dirs = dict(g.port_directions)
    dirs.update({k: v for k, v in _PORT_SIDES.items()})
    g = Geometry(g.element, g.bounds, g.ports, dirs, g.port_tangents)
    cx, cy = b.x + b.width / 2, b.y + b.height / 2
    return g.moved(-cx, -cy) if abs(cx) > 1e-9 or abs(cy) > 1e-9 else g


def _el(tag, **attrs):
    return ET.Element(tag, _attrs(attrs))


def _style(style):
    if style not in _STYLES:
        raise ValueError('style must be "rich" or "flat"')
    return style == "rich"


def _start(rich=None):  # ``rich`` accepted for call-site symmetry; the holder is the same
    holder = _el("g")
    defs = _el("defs")
    holder.append(defs)
    return holder, defs


def _finish(holder, defs, bounds, **ports):
    if defs is not None and not len(defs):
        holder.remove(defs)
    return _with_edges(Geometry(holder, bounds), **ports)


def _circ(cx, cy, r):
    """Circle as a subpath (same winding everywhere so merged circles union under nonzero fill)."""
    return (
        f"M{fmt(cx + r)} {fmt(cy)} A{fmt(r)} {fmt(r)} 0 1 0 {fmt(cx - r)} {fmt(cy)} "
        f"A{fmt(r)} {fmt(r)} 0 1 0 {fmt(cx + r)} {fmt(cy)} Z"
    )


def _head(x, y, dx, dy, size, color):
    """Filled arrowhead with its tip at (x, y) pointing along (dx, dy)."""
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    bx, by = x - ux * size, y - uy * size
    w = size * 0.45
    return _el(
        "path",
        d=f"M{fmt(x)} {fmt(y)} L{fmt(bx - uy * w)} {fmt(by + ux * w)} L{fmt(bx + uy * w)} {fmt(by - ux * w)} Z",
        fill=color,
        stroke="none",
    )


def _linear(gid, stops, *, x2=0, y2=1):
    g = _el("linearGradient", id=gid, x1=0, y1=0, x2=x2, y2=y2)
    for off, color, op in stops:
        g.append(_el("stop", offset=off, stop_color=color, stop_opacity=op if op < 1 else None))
    return g
