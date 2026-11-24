"""McKinsey "left chart → right expansion": the left panel's highlighted row / rows / bar / segment is opened up in
the right panel. A thin vertical divider separates the panels; a short grey line runs from the highlighted source
to a dot on the divider — no arrows, no dashed fans.

  L, R = expand_panels(ex, "左图标题", "单位", "右图标题", "单位")
  small_rows(ex, L, cats, [(name, values)], highlight=1)       left: one bar row per group (no y axis)
  plain_bars(ex, R, cats, values, focus=…)                       right: any chart, or small_rows / columns
  expand(ex, src)                                               src = small_rows(...) result, or (columns_r, k) / (r, k, series)
"""

from __future__ import annotations

from ._text import fmt, tw

TITLE_H = 48   # canvas units taken by panel title + rule + unit line


def _head(ex, x0, x1, title, unit):
    C = ex.C
    ex.text(x0, 14, title, size=12.5, weight=700, fill=C["ink"])
    ex.line(x0, 22, x1, 22, stroke=C["ink"], width=0.8, tag="grid")
    if unit:
        ex.text(x0, 39, unit, size=10.5, fill=C["text"])


def expand_panels(ex, left_title, left_unit, right_title, right_unit, split=0.5, gap=56):
    """Two panels with bold titles over a rule + unit line, and the divider between them. Returns (L, R) chart boxes
    (below the titles). split = left share of the width. Draw charts into L / R, then expand(ex, src)."""
    x0, y0, x1, y1 = ex.body
    lx1 = x0 + (x1 - x0 - gap) * split
    rx0 = lx1 + gap
    ex.divider_x = lx1 + gap / 2
    _head(ex, x0, lx1, left_title, left_unit)
    _head(ex, rx0, x1, right_title, right_unit)
    ex.line(ex.divider_x, y0 + 4, ex.divider_x, y1, stroke=ex.C["context"], width=0.8, tag="grid")
    ex.panels += [(x0, y0 + TITLE_H, lx1, y1), (rx0, y0 + TITLE_H, x1, y1)]
    return (x0, y0 + TITLE_H, lx1, y1), (rx0, y0 + TITLE_H, x1, y1)


def plain_bars(ex, box, cats, values, color=None, focus=None, value_fmt=lambda v: fmt(v), vmax=None, xlabels=True,
               pad=0.3):
    """Columns with no y axis or grid: baseline + value above each bar (the expansion panels' style).
    focus: callable(category) -> bool, or an index / name / tuple of them — those bars accent, others light. Returns dict(bands, tops, base, box)."""
    C = ex.C
    from ._page import focus_fn
    if focus is not None:
        two = focus_fn(focus, cats)
        focus = lambda c: two(c, None)   # noqa: E731
    x0, y0, x1, y1 = box
    base = y1 - (18 if xlabels else 2)
    vals = [v for v in values if v is not None]
    vmax = vmax or (max(vals) if vals else 1) or 1
    hh = base - y0 - 16
    step = (x1 - x0) / len(cats)
    bands, tops = [], []
    for i, (c, v) in enumerate(zip(cats, values)):
        bx, bw = x0 + i * step + step * pad / 2, step * (1 - pad)
        bands.append((bx, bw))
        if v is None:
            tops.append(base)
            continue
        col = color or C["main"]
        if focus is not None:
            col = C["accent"] if focus(c) else C["light"]
        top = base - max(v, 0) / vmax * hh
        ex.rect(bx, top, bw, max(base - top, 0.8), col)
        ex.text(bx + bw / 2, top - 5, value_fmt(v), size=10.5, fill=C["ink"], anchor="middle")
        if xlabels:
            ex.text(bx + bw / 2, base + 14, str(c), size=10.5, fill=C["ink"], anchor="middle")
        tops.append(top)
    ex.line(x0, base, x1, base, stroke=C["axis"], width=0.9, tag="axis")
    return dict(bands=bands, tops=tops, base=base, box=box)


def small_rows(ex, box, cats, rows, highlight=None, label_w=None, value_fmt=lambda v: fmt(v), color=None,
               shared_scale=True):
    """One bar row per group (all groups, then sub-groups), category labels only under the last row.
    rows: [(name, values)]. highlight: index or (first, last) of the row(s) expanded on the right — they get a grey
    band. Returns dict(rows=[(y0, y1)], src=(x0, y0, x1, y1) of the highlighted band or None)."""
    C = ex.C
    x0, y0, x1, y1 = box
    lw = label_w or (max(tw(n, 11, True) for n, _ in rows) + 16)
    rh = (y1 - y0) / len(rows)
    vmax = max(v for _, vs in rows for v in vs if v is not None) * 1.05 if shared_scale else None
    hl = (highlight, highlight) if isinstance(highlight, int) else highlight
    src = None
    if hl is not None:
        a, b = hl
        src = (x0, y0 + a * rh + 2, x1, y0 + (b + 1) * rh - 2)
        from ._marks import dashed_box
        dashed_box(ex, *src, color=C["accent"])
        ex.notes -= 1   # the expand() link is the annotation
    out = []
    for k, (nm, vs) in enumerate(rows):
        ry0, ry1 = y0 + k * rh, y0 + (k + 1) * rh
        ex.text(x0 + 6, (ry0 + ry1) / 2 + 4, nm, size=11, weight=700, fill=C["ink"])
        plain_bars(ex, (x0 + lw, ry0 + 6, x1 - 10, ry1 - 2), cats, vs, color=color, value_fmt=value_fmt,
                   vmax=vmax, xlabels=(k == len(rows) - 1))
        out.append((ry0, ry1))
    return dict(rows=out, src=src)


def expand(ex, src, color=None):
    """Connect the expanded source to the divider: src = small_rows() result (its grey band), a box (x0, y0, x1, y1),
    (columns_result, k) for bar k, or (columns_result, k, series_name) for one stacked segment (gets an outline).
    Call after expand_panels(). The right panel must show exactly that row / bar / segment broken down."""
    C = ex.C
    dx = getattr(ex, "divider_x", None)
    if dx is None:
        raise ValueError("expand：先用 expand_panels(...) 建左右面板（它画分隔线并记下位置）")
    outline = False
    if isinstance(src, dict) and "src" in src:
        box = src["src"]
        if box is None:
            raise ValueError("expand：small_rows 没有 highlight=，不知道展开哪一行")
    elif isinstance(src, tuple) and len(src) in (2, 3) and isinstance(src[0], dict):
        r, k = src[0], src[1]
        bx, bw = r["bands"][k]
        if len(src) == 3:
            seg = (r.get("segs") or {}).get(r["cats"][k], {}).get(src[2])
            if seg is None:
                raise ValueError(f"expand：第 {k} 根柱没有系列 {src[2]!r}（只有堆叠柱 stack='stack'/'percent' 能选色段）")
            top, bot = seg
        else:
            top, bot = r["tops"][r["cats"][k]], r["ax"].sy(r["ax"].ymin)
        box, outline = (bx - 3, top - 3, bx + bw + 3, bot + 3), True
    else:
        box, outline = src, True
    sx0, sy0, sx1, sy1 = box
    if outline:   # dashed outline around the expanded bar / segment (McKinsey)
        from ._marks import dashed_box
        dashed_box(ex, sx0, sy0, sx1, sy1, color=color or C["accent"])
        ex.notes -= 1
    y = (sy0 + sy1) / 2
    ex.line(sx1, y, dx, y, stroke=C["context"], width=0.9, tag="grid")
    ex.circle(dx, y, 3.2, C["context"], register=False)
    ex.notes += 1
    ex.related = True
    return box
