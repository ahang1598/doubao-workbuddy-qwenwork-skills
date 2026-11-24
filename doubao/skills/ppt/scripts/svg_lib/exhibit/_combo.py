"""Composite text–chart layouts for strategy pages (all fed to f.publish(*xml, frags=frags, ...)).

  period_notes   time series + short period takeaways above the matching years (no leader lines)
  panel_heads    2–3 panels side by side, each topped by a numbered one-line takeaway (key figure in accent)
  shared_time    two metrics stacked on ONE time axis (columns on top, lines below), one band through both
  (shared rows   = row_table with several data columns — see exhibit_help('shared_rows'))
"""

from __future__ import annotations

from html import escape

from ._frame import _box, _c
from ._palette import roles
from ._text import tw, wrap


def _rich(text, hl, C):
    t = escape(text)
    for h in ([hl] if isinstance(hl, str) else (hl or [])):
        t = t.replace(escape(h), f'<span color="{_c(C["accent"])}">{escape(h)}</span>')
    return t


def _panel_head(x, y, w, n, takeaway, chart_title, hl, C, font, numbered=True, note=None):
    """Numbered dot + bold takeaway (16pt, ≤2 lines) + optional ≤2-line explanation + grey chart title + rule.
    Returns (xml, bottom_y)."""
    tx = x + (34 if numbered else 0)
    lines = wrap(takeaway, 16, w - (tx - x) - 4, bold=True)
    if len(lines) > 2:
        raise ValueError(f"面板结论太长（{len(lines)} 行）：{takeaway!r} 缩到约 {int((w - 40) / 16 * 2)} 字以内，细节放图上标注")
    th = 24 * len(lines)
    out = []
    if numbered:
        out.append(f'<shape type="ellipse" topLeftX="{x:.0f}" topLeftY="{y:.0f}" width="24" height="24">'
                   f'<fill><fillColor color="{_c(C["main"])}"/></fill></shape>')
        out.append(_box(x, y, 24, 24, f"<p>{n}</p>", 12, "#FFFFFF", font, bold=True, align="center", valign="middle"))
    out.append(_box(tx, y - 1, w - (tx - x), th + 2, f'<p lineSpacing="multiple:1.15">{_rich(takeaway, hl, C)}</p>', 16,
                    C["ink"], font, bold=True))
    y2 = y + max(th, 24) + 6
    if note:
        from ._page import check_panel_note
        check_panel_note(takeaway, note, "panel_heads 诠释")
        nl = wrap(note, 13, w - (tx - x) - 4)
        if len(nl) > 2:
            raise ValueError(f"panel_heads 诠释 {note!r} 超过两行：缩到约 {int((w - 40) / 13 * 2)} 字")
        out.append(_box(tx, y2 - 2, w - (tx - x), 18 * len(nl) + 2, f'<p lineSpacing="multiple:1.2">{escape(note)}</p>', 13,
                        C["text"], font))
        y2 += 18 * len(nl) + 4
    if chart_title:
        y2 = max(y2, y + 24 * 2 + 6 + (18 * 2 + 4 if note else 0))   # fixed head height: charts start level
        out.append(_box(x, y2, w, 18, f"<p>{escape(chart_title)}</p>", 12, C["sub"], font))
        y2 += 20
    out.append(f'<line startX="{x:.0f}" startY="{y2 + 2:.0f}" endX="{x + w:.0f}" endY="{y2 + 2:.0f}">'
               f'<border color="{_c(C["grid"])}" width="1"/></line>')
    return "".join(out), y2 + 10


def panel_heads(f, panels, gap=36, numbered=True, palette=None, font="思源黑体", rules=True):
    """2–3 equal panels across the body of frame f, each with a numbered one-line takeaway on top.

    panels: [(takeaway, chart_title, highlight)] or [(takeaway, chart_title, highlight, note)] — highlight = the key
    figure(s) in the takeaway to colour accent; note = optional ≤2-line explanation under it (reason / implication, no
    repeated numbers).
    Each takeaway proves one step of the page title; read left → right they ARE the argument (no arrows needed).
    Returns (xml, boxes): boxes = [(x, y, w, h)] slide boxes for each panel's chart — build one Exhibit(w, h) per box
    and pass ex.to_slide(x=x, y=y) in frags. All panels get the same chart top (the tallest header)."""
    C = roles(palette)
    n = len(panels)
    W = f.right - f.left
    pw = (W - gap * (n - 1)) / n
    heads, bottoms = [], []
    from ._layouts import CLAIMS
    for i, p_ in enumerate(panels):
        tk, ct, hl = p_[:3]
        nt = p_[3] if len(p_) > 3 else None
        CLAIMS.append(str(tk))
        px = f.left + i * (pw + gap)
        xml, b = _panel_head(px, f.top, pw, i + 1, tk, ct, hl, C, font, numbered, note=nt)
        heads.append(xml)
        bottoms.append(b)
    top = max(bottoms)
    out = list(heads)
    if rules:
        for i in range(1, n):
            xl = f.left + i * (pw + gap) - gap / 2
            out.append(f'<line startX="{xl:.0f}" startY="{f.top:.0f}" endX="{xl:.0f}" endY="{f.bottom:.0f}">'
                       f'<border color="{_c(C["grid"])}" width="1"/></line>')
    return "".join(out), [(f.left + i * (pw + gap), top, pw, f.bottom - top) for i in range(n)]


def period_notes(f, periods, centers_x, band_w, top=None, focus=None, palette=None, font="思源黑体", height=64):
    """Short period takeaways ABOVE a time-series chart, each sitting over exactly the years it describes, with a
    thin colour bar marking the span — the reader sees "this sentence = these years" without leader lines.

    periods: [(i, j, lead, text)] category index range (inclusive) + bold lead + ≤14-char text. focus: index of the
    period that carries the page's argument (accent). centers_x: slide x of every category centre (see
    period_x(ex, r, x0)); band_w: slide width of one category band. Returns (xml, chart_top) — start the chart at
    chart_top (= top + height)."""
    C = roles(palette)
    top = f.top if top is None else top
    out = []
    for k, (i, j, lead, text) in enumerate(periods):
        xa, xb = centers_x[i] - band_w / 2, centers_x[j] + band_w / 2
        col = C["accent"] if k == focus else C["context"]
        out.append(f'<shape type="rect" topLeftX="{xa + 2:.0f}" topLeftY="{top:.0f}" width="{xb - xa - 4:.0f}" height="3">'
                   f'<fill><fillColor color="{_c(col)}"/></fill></shape>')
        w = xb - xa - 8
        if len(wrap(lead + text, 14, w - 4)) > 3:
            raise ValueError(f"时段说明太长：{lead}{text!r} 放不进 {w:.0f}px 宽（≤3 行），删字或合并时段")
        lc = C["accent"] if k == focus else C["ink"]
        out.append(_box(xa + 4, top + 8, w, height - 12,
                        f'<p lineSpacing="multiple:1.15"><span bold="true" color="{_c(lc)}">{escape(lead)}</span>'
                        f'{escape(text)}</p>', 14, C["text"], font))
    return "".join(out), top + height


def period_x(ex, r, x0):
    """Slide x of each category centre and the slide band width for a columns() result r drawn in ex placed at x0."""
    cs = r["centers"]
    step = (cs[1] - cs[0]) if len(cs) > 1 else r["bands"][0][1]
    return [x0 + c * ex.scale for c in cs], step * ex.scale


def shared_time(ex, cats, top, bottom, split=0.55, band=None, focus_label=None, gap=16, left=0,
                top_ticks=False, bottom_fmt=lambda v: f"{v:g}"):
    """Two metrics on ONE time axis inside ex: columns on top, lines below, years aligned; an optional band
    (i, j, "label") shades the same years through both panels — the reader sees cause and effect in one exhibit.

    top: (name, values, color?) for the columns. bottom: [(name, values, color?)] lines (first = protagonist,
    value labels on every point; others grey with an end label). left: canvas units reserved on the left (e.g. for
    the panels' row labels in XML). Returns dict(top=(y0, y1), bottom=(y0, y1), centers=[...]) in canvas units."""
    from ._axes import Axes
    from ._marks import columns
    C = ex.C
    names = [b[0] for b in bottom]
    x0, x1 = left, ex.w - max(tw(n, 10.5, True) for n in names) - 14   # room for the lines' end labels
    top_h = (ex.h - gap) * split
    nm, vals, *col = top
    ex._no_auto = getattr(ex, "_no_auto", 0) + 1   # a shared time axis is one chart: never split into native parts
    ex._no_auto_combo = 1
    try:
        r = columns(ex, (x0, 0, x1, top_h), cats, [(nm, vals, (col[0] if col else C["main"]))], show_grid=False,
                    legend_items=False, cagr=False)
    finally:
        ex._no_auto -= 1
        ex._no_auto_combo = 0
    centers, bw = r["centers"], r["bands"][0][1]
    yb0 = top_h + gap
    allv = [v for _, ys, *_ in bottom for v in ys if v is not None]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.2 or 1
    import math
    step = 10 ** math.floor(math.log10(max(hi - lo, 1e-9) / 2))
    step = next((m * step for m in (1, 2, 5, 10, 20, 50) if (hi - lo + 2 * pad) / (m * step) <= 4), step * 100)
    t0, t1 = math.floor((lo - pad) / step) * step, math.ceil((hi + pad) / step) * step
    ticks = [round(t0 + k * step, 6) for k in range(int(round((t1 - t0) / step)) + 1)]
    ax = Axes.fit(ex, (x0, yb0, x1, ex.h), t1, ymin=t0, ticks=ticks, top_pad=12, label_rows=0)
    ax.x, ax.w = r["ax"].x, r["ax"].w
    ax.grid(fmt_tick=bottom_fmt)
    from ._marks import gap_marks, runs
    for k, (bn, ys, *bc) in enumerate(bottom):
        colr = bc[0] if bc else (C["accent"] if k == 0 else C["context"])
        ys = list(ys) + [None] * (len(centers) - len(ys))
        pts = [(c, ax.sy(v)) for c, v in zip(centers, ys) if v is not None]
        for run in runs(centers, ys):   # a None breaks the line: no segment bridges the missing year
            for (c0, v0), (c1, v1) in zip(run, run[1:]):
                ex.line(c0, ax.sy(v0), c1, ax.sy(v1), stroke=colr, width=2.2 if k == 0 else 1.6, tag="series", whole=True)
        for a, b in pts:
            ex.circle(a, b, 3, "#FFFFFF", stroke=colr, width=1.4, register=False)
        known = [i for i, v in enumerate(ys) if v is not None]   # an interior gap: dashed bridge, no '缺' text
        for i0, i1 in zip(known, known[1:]):
            if i1 - i0 > 1:
                ex.line(centers[i0], ax.sy(ys[i0]), centers[i1], ax.sy(ys[i1]), stroke=colr, width=1.4, dash="4,3", tag="gap")
        if k == 0:   # value labels on the side away from the comparison line(s)
            others = [o[1] for o in bottom[1:]]
            idx_ = [i for i, v in enumerate(ys) if v is not None]
            for (a, b), v, idx in zip(pts, [v for v in ys if v is not None], idx_):
                ov = [o[idx] for o in others if idx < len(o) and o[idx] is not None]
                above = not ov or v >= max(ov)
                ex.text(a, b - 9 if above else b + 18, bottom_fmt(v), size=10.5, fill=colr, anchor="middle", weight=700)
        ex.text(pts[-1][0] + 9, pts[-1][1] + 4, bn, size=10.5, fill=colr if k == 0 else C["sub"], weight=700 if k == 0 else 400)
    if band:
        i, j, lab = band
        bx0 = r["bands"][i][0] - bw * 0.2
        bx1 = r["bands"][j][0] + bw * 1.2
        if j == len(centers) - 1:   # run to the edge: the series end labels sit inside the band, not across its edge
            bx1 = ex.w                # (a label half on the band is reported as overflowing it)
        from ._marks import dashed_box
        dashed_box(ex, bx0, 6, min(bx1, ex.w - 1), ex.h - 2, label=lab)   # the period through both panels
    ex.line(x0, top_h + gap / 2, x1, top_h + gap / 2, stroke=C["grid"], width=0.8, tag="grid")
    ex.related = True
    return dict(top=(0, top_h), bottom=(yb0, ex.h), centers=centers, ax_top=r["ax"], ax_bottom=ax, r=r)
