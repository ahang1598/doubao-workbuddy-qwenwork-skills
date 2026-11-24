"""Marks and argument annotations. Colours come from ex.C roles; everything registers for placement / check."""

from __future__ import annotations

import re

import math

from ._axes import Axes
from ._place import place_label
from ._text import fmt, tw, wrap

# ===================================================================================== annotations


def _clear_whole_lines(ex, cx, cy, half_w, half_h, kind, skip=None):
    from ._page import _seg_hits_box
    series = [entry for entry in ex.reg if entry["kind"] == "line" and entry is not skip
              and (entry.get("whole") or entry["tag"] == "series")]

    def touches(box):
        return any(_seg_hits_box(*entry["box"], box, pad=2 + entry.get("width", 1) / 2) for entry in series)

    if touches((cx - half_w, cy - half_h, cx + half_w, cy + half_h)):
        target = (cx, cy)
        bounds = ex._panel or (0, 0, ex.w, ex.h)
        choices = []
        for step in range(1, 9):
            for direction_x, direction_y in ((0, -1), (0, 1), (1, 0), (-1, 0),
                                               (1, -1), (-1, -1), (1, 1), (-1, 1)):
                candidate_x = cx + direction_x * step * (half_w + 10)
                candidate_y = cy + direction_y * step * (half_h + 10)
                box = (candidate_x - half_w, candidate_y - half_h,
                       candidate_x + half_w, candidate_y + half_h)
                if (box[0] < bounds[0] or box[1] < bounds[1] or box[2] > bounds[2] or box[3] > bounds[3]
                        or touches(box)):
                    continue
                choices.append((ex.cost(box, bounds=bounds) + math.dist(target, (candidate_x, candidate_y)),
                                candidate_x, candidate_y))
        if not choices:
            raise ValueError(f"{kind}: no room clear of the complete data series; move the annotation outside the chart")
        _, cx, cy = min(choices)
    return cx, cy


def _clear_marks_and_text(ex, cx, cy, half_w, half_h):
    """A badge put on a dot / Harvey ball / label (e.g. "推荐" next to a row name that wrapped) hides it: slide the
    badge sideways (then up / down) to the nearest spot clear of registered dots and text. Keeps the spot when
    nothing nearby is free."""
    from ._page import _ov
    blockers = [e["box"] for e in ex.reg if (e["kind"] == "text") or (e["kind"] == "mark" and e.get("circle"))]

    def hit(x, y):   # series lines are handled after this by _clear_whole_lines (with a leader)
        box = (x - half_w, y - half_h, x + half_w, y + half_h)
        return any(_ov(box, b, pad=1) for b in blockers)
    if not hit(cx, cy):
        return cx, cy
    bounds = ex._panel or (0, 0, ex.w, ex.h)
    best = None
    for step in range(1, 41):
        for dx, dy in ((step * 4, 0), (-step * 4, 0), (0, -step * 3), (0, step * 3)):
            x, y = cx + dx, cy + dy
            if x - half_w < bounds[0] or x + half_w > bounds[2] or y - half_h < bounds[1] or y + half_h > bounds[3]:
                continue
            if not hit(x, y):
                d = math.hypot(dx, dy * 1.6)   # same row first: a vertical move lands on the neighbour row
                if best is None or d < best[0]:
                    best = (d, x, y)
        if best is not None:
            break
    return (best[1], best[2]) if best else (cx, cy)


def badge(ex, cx, cy, text, fill=None, size=11.5, color="#FFFFFF"):
    """Round badge with a multiple / delta ('5.3×', '+9%'). Returns radius. A badge that would cover a dot, a Harvey
    ball or a label slides to the nearest free spot beside it."""
    ex.notes += 1
    from ._page import lint_w
    w = lint_w(text, size, True)
    r = max(w / 2 + 6, size * 1.25)
    half_w, half_h = (w / 2 + 9, size * 0.95) if w > size * 3.2 else (r, r)
    cx, cy = _clear_marks_and_text(ex, cx, cy, half_w, half_h)
    target = (cx, cy)
    cx, cy = _clear_whole_lines(ex, cx, cy, half_w, half_h, "badge")
    if (cx, cy) != target:
        delta_x, delta_y = target[0] - cx, target[1] - cy
        fraction = (min(half_w / abs(delta_x) if delta_x else math.inf,
                        half_h / abs(delta_y) if delta_y else math.inf)
                    if w > size * 3.2 else r / math.hypot(delta_x, delta_y))
        ex.line(*target, cx + delta_x * fraction, cy + delta_y * fraction,
                stroke=ex.C["context"], width=0.8, tag="leader")
    if w > size * 3.2:   # long text: a pill, not a giant disc
        h = size * 1.9
        x0, x1, y0, y1, q = cx - w / 2 - 9, cx + w / 2 + 9, cy - h / 2, cy + h / 2, h / 2
        ex.cut_lines(box=(x0, y0, x1, y1))   # a slope / ref line under the badge reads as a line through its text
        ex.path(f"M{x0 + q:.1f},{y0:.1f} H{x1 - q:.1f} Q{x1:.1f},{y0:.1f} {x1:.1f},{cy:.1f} Q{x1:.1f},{y1:.1f} {x1 - q:.1f},{y1:.1f} "
                f"H{x0 + q:.1f} Q{x0:.1f},{y1:.1f} {x0:.1f},{cy:.1f} Q{x0:.1f},{y0:.1f} {x0 + q:.1f},{y0:.1f} Z",
                fill=fill or ex.C["main"], register=False)
        ex.occupy((x0, y0, x1, y1), "mark", "badge")
        ex.text(cx, cy + size * 0.36, text, size=size, weight=700, fill=color, anchor="middle")
        return h / 2
    ex.cut_lines(circle=(cx, cy, r))
    ex.circle(cx, cy, r, fill or ex.C["main"])
    ex.text(cx, cy + size * 0.36, text, size=size, weight=700, fill=color, anchor="middle")
    return r


def num_dot(ex, cx, cy, n=None, fill=None, r=8):
    """Small filled circle with a number, to pair a chart location with numbered takeaways in the page XML.
    Place it by data instead of pixels: num_dot(ex, columns结果, "2025", 1) (above that bar), num_dot(ex, row_table结果,
    "宁德时代", 2) (that row, right of its bar), num_dot(ex, lines/NAxes 结果, (2024, 1.83), 3) (that point)."""
    if n is None and isinstance(cy, int) and not isinstance(cx, (int, float)):
        raise ValueError("num_dot(ex, 图结果, 类目/行名/(x, y), n)：四个参数，最后一个是编号")
    if isinstance(cx, dict) and "tops" in cx:   # columns() result + category
        cats = [str(c) for c in cx["cats"]]
        k = cats.index(str(cy)) if str(cy) in cats else int(cy) if isinstance(cy, int) and 0 <= cy < len(cats) else None
        if k is None:
            raise ValueError(f"num_dot：{cy!r} 不是这张柱图的类目（{cats[:8]}）")
        b = cx["bands"][k]
        row_vals = [vs[k] for _, vs in (cx.get("rows") or []) if k < len(vs) and vs[k] is not None]
        cx, cy = b[0] + b[1] / 2, cx["tops"][cats[k]] - 30
    elif isinstance(cx, dict) and "y" in cx and "cols" in cx:   # row_table() result + row label
        ys = {str(key): v for key, v in cx["y"].items()}
        if str(cy) not in ys:
            raise ValueError(f"num_dot：{cy!r} 不是这张表的行（{list(ys)[:8]}）")
        x_end = cx["cols"][-1][1] if cx["cols"] else ex.w - 12
        cy, cx = ys[str(cy)], min(x_end + 12, ex.w - r - 2)
    elif hasattr(cx, "sx") and hasattr(cx, "sy") and isinstance(cy, (tuple, list)):   # NAxes + (x, y) data point
        ax_, (xv, yv) = cx, cy
        cx, cy = ax_.sx(xv), ax_.sy(yv) - 16
    elif isinstance(cy, str) and not isinstance(cx, (int, float)):   # any chart + a category name: find its label
        ex._flush()
        bands = getattr(ex, "pareto_bands", None) or {}
        hits = [e["box"] for e in ex.reg if e["kind"] == "text" and str(e["tag"]).strip() == cy.strip()]
        if cy in bands:
            x0_, x1_, top_ = bands[cy][:3]
            cx, cy = (x0_ + x1_) / 2, top_ - 30
        elif hits:
            b = hits[0]
            cx, cy = (b[0] + b[2]) / 2, b[1] - 14
        else:
            raise ValueError(f"num_dot：图上找不到类目 {cy!r}——写图上显示的类目名，或传像素坐标 num_dot(ex, x, y, n)")
    if any(f_.get("kind") == "bubble_numbers" for f_ in getattr(ex, "facts", None) or []):
        raise ValueError("这张气泡图已经用 numbered 编号（气泡里的 1、2、3），不要再叠 num_dot——右栏要点直接用同样的编号")
    ex.notes += 1
    ex.num_dots = getattr(ex, "num_dots", 0) + 1   # Frame.publish: the side points() should carry mark=n
    ex._flush()
    target = (cx, cy)
    box = (cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1)
    if ex.cost(box) > 0:   # on a line / label / bar edge: nearest clear spot around the target, with a short leader
        best = None
        for step in (1, 1.6, 2.3, 3.2):
            for dx, dy in ((0, -1), (1, -1), (-1, -1), (1, 0), (-1, 0), (0, 1), (1, 1), (-1, 1)):
                x, y = cx + dx * step * (r + 5), cy + dy * step * (r + 5)
                c = ex.cost((x - r - 1, y - r - 1, x + r + 1, y + r + 1)) + math.dist(target, (x, y))
                if best is None or c < best[0]:
                    best = (c, x, y)
            if best[0] < 60:
                break
        _, cx, cy = best
        if math.dist(target, (cx, cy)) > r + 2:
            f = r / math.dist(target, (cx, cy))
            ex.line(*target, cx - (cx - target[0]) * f, cy - (cy - target[1]) * f,
                    stroke=ex.C["context"], width=0.8, tag="leader")
    near = list(locals().get("row_vals") or [])   # readings at the spot this dot marks (incl. its column's data rows):
    # publish matches takeaway n against them
    for e in ex.reg:
        if e["kind"] == "text" and e.get("fill") not in (ex.C["axis"], "#FFFFFF"):
            bx = e["box"]
            if math.dist(target, ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)) <= 60:
                near += [float(v.replace(",", "")) for v in re.findall(r"\d[\d,]*(?:\.\d+)?", str(e["tag"]))]
    ex.__dict__.setdefault("dot_values", {})[n] = near
    ex.cut_lines(circle=(cx, cy, r))
    ex.circle(cx, cy, r, fill or ex.C["main"])
    ex.text(cx, cy + 3.8, str(n), size=10.5, weight=700, fill="#FFFFFF", anchor="middle")
    return r


def dim_arrow(ex, x, y_top, y_bot, from_top=None, from_bot=None, label=None, fill=None):
    """Vertical double arrow between two values; optional leader ticks back to the values and a badge."""
    t = ex.C["text"]
    if from_top is not None:
        ex.line(from_top, y_top, x + 4, y_top, stroke=t, width=0.8, tag="dim")
    if from_bot is not None:
        ex.line(from_bot, y_bot, x + 4, y_bot, stroke=t, width=0.8, tag="dim")
    ex.line(x, y_top + 2, x, y_bot - 2, stroke=t, width=1, marker="arr_s", marker_start="arr_s", tag="dim", whole=True)
    if label:
        cy = (y_top + y_bot) / 2
        badge(ex, x, cy, label, fill=fill)


def _bracket_lines(ex, pts, stroke):
    start = len(ex.el)
    for index, (first, last) in enumerate(zip(pts, pts[1:])):
        ex.line(*first, *last, stroke=stroke, width=0.9, tag="path", whole=index == 1)
    ex.el[start:] = ["".join(ex.el[start:])]


def span_bracket(ex, x0, x1, y, text, up=True, size=11, color=None, weight=700):
    """Horizontal bracket over / under a span (e.g. '5.1% CAGR' over forecast years)."""
    ex.notes += 1
    d = -6 if up else 6
    pts = [(x0, y), (x0, y + d), (x1, y + d), (x1, y)]
    _bracket_lines(ex, pts, ex.C["text"])
    ty = y + d - 5 if up else y + d + size + 2
    ex.text((x0 + x1) / 2, ty, text, size=size, weight=weight, anchor="middle", fill=color or ex.C["ink"])


def vbracket(ex, x, y0, y1, text=None, size=11.5, weight=700, depth=6, color=None):
    """Right-facing vertical bracket spanning y0..y1 with a total label ('71%')."""
    ex.notes += 1
    pts = [(x, y0), (x + depth, y0), (x + depth, y1), (x, y1)]
    _bracket_lines(ex, pts, ex.C["context"])
    if text:
        ex.text(x + depth + 6, (y0 + y1) / 2 + size * 0.36, text, size=size, weight=weight, fill=color or ex.C["ink"])


def big_number(ex, x, y, big, unit="", sub="", anchor="start", size=30, inline=True, color=None):
    """Serif headline number. inline=True: unit on the same baseline ('+309 亿元'), grey sub below.
    inline=False: unit bold + sub italic stacked below (use anchor='middle'). Returns bottom y."""
    ex.notes += 1
    from ._page import SERIF
    ex.text(x, y, big, size=size, family=SERIF, fill=color or ex.C["ink"], anchor=anchor)
    bw = tw(big, size, serif=True)
    yy = y
    if unit and inline:
        ux = x + bw + 6 if anchor == "start" else (x + bw / 2 + 6 if anchor == "middle" else x + 6)
        ex.text(ux, y, unit, size=13, weight=700, fill=ex.C["ink"])
    elif unit:
        yy += 15
        ex.text(x, yy, unit, size=12.5, weight=700, fill=ex.C["ink"], anchor=anchor)
    if sub:
        yy += 18 if inline else 15
        ex.text(x, yy, sub, size=11 if inline else 12.5, fill=ex.C["sub"] if inline else ex.C["ink"], anchor=anchor,
                italic=not inline)
    return yy


def leader_label(ex, x, y_from, y_to, text, size=11, width=None):
    """Thin vertical leader from a mark up to a diamond + label (stair-step labels over ranked bars)."""
    ex.line(x, y_from, x, y_to + 5, stroke=ex.C["context"], width=0.9, tag="leader")
    diamond(ex, x, y_to, 4)
    rows = wrap(text, size, width) if width else [text]
    ex.lines(x + 8, y_to + size * 0.36, rows, size=size, lh=1.2)


def diamond(ex, cx, cy, r, fill=None):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    ex.path("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + " Z", fill=fill or ex.C["ink"], pts=pts)


def legend(ex, x, y, items, size=11, gap=16):
    """items: (label, color, kind), kind in square | dot | ring | pale | line | dash | bar. Returns end x.
    Every swatch colour must be drawn on the chart (to_slide checks it)."""
    ex.legend_drawn = True
    ex.legend_log = list(getattr(ex, "legend_log", None) or []) + [(str(lab), col) for lab, col, _ in items]
    need = sum(size * 0.84 + (9 if k_ in ("line", "dash") else 5) + 3 + tw(str(lab), max(size, 10)) + gap for lab, _, k_ in items) - gap
    if x + need > ex.w - 2 and need <= ex.w - 4:   # a row running off the canvas: slide it back inside (same row)
        x = ex.w - 2 - need
    if y - max(size, 10) * 0.8 < 0:   # baseline too close to the top edge: the glyphs would leave the canvas
        y = max(size, 10) * 0.8 + 0.5
    x0_ = x
    n0 = len(ex.el)
    x = _legend_items(ex, x, y, items, size, gap)
    ex.occupy((x0_, y - size, x - gap, y + size * 0.25), "mark", "legend")   # size_legend(ax=) / labels keep clear
    ex._legend_els = set(getattr(ex, "_legend_els", set())) | {s for s in ex.el[n0:] if not s.startswith("<text")}
    return x


def _legend_items(ex, x, y, items, size, gap):
    for label, color, kind in items:
        k = size * 0.42
        cx, cy = x + k, y - size * 0.33
        if kind == "dot":
            ex.circle(cx, cy, k, color, register=False)
        elif kind in ("ring", "hollow"):
            ex.circle(cx, cy, k - 0.6, "#FFFFFF", stroke=color, width=1.4, register=False)
        elif kind == "pale":
            ex.circle(cx, cy, k, color, stroke=ex.C["ink"], width=0.9, register=False)
        elif kind in ("line", "dash"):
            ex.line(x, cy, x + 2 * k + 6, cy, stroke=color, width=2, dash="4,3" if kind == "dash" else None,
                    register=False)
        elif kind == "bar":
            ex.rect(cx - 2.5, cy - k * 1.1, 5, k * 2.2, color, register=False)
        else:
            ex.rect(x, cy - k, 2 * k, 2 * k, color, register=False)
        lx = x + 2 * k + (9 if kind in ("line", "dash") else 5) + 3
        ex.text(lx, y, label, size=size)
        x = lx + tw(label, size) + gap
    return x


def size_legend(ex, x, y, values, to_r, label_lines=(), fmt_v=lambda v: fmt(v), size=10.5, ax=None):
    """Nested-circle area legend for bubble charts; to_r is the chart's value→radius function.
    ax=<the bubble axes>: a compact one-line legend in the header row above the plot (left of any colour legend) —
    "气泡=…：○ 1,200  ○ 200" with small circles — so nothing sits inside the plot. x / y are then ignored."""
    ex.size_legend_drawn = True
    if ax is not None:
        lab = " ".join(label_lines) if label_lines else ""
        left_end = ax.x + (tw(getattr(ax, "_ytitle", "") or "", size) + 24 if getattr(ax, "_ytitle", "") else 0)
        used = [e["box"] for e in ex.reg if e.get("tag") == "legend" and e["box"][1] < ax.y]
        right_lim = min([b[0] for b in used] + [ax.x + ax.w]) - 16
        rs = [min(to_r(v), 9.0) for v in sorted(values, reverse=True)]
        need = (tw(lab, size) + 8 if lab else 0) + sum(2 * r + 6 + tw(fmt_v(v), size) + 12 for r, v in zip(rs, sorted(values, reverse=True)))
        cx = max(left_end, right_lim - need)
        cy = ax.y - 10 - size * 0.33
        base_y = ax.y - 10
        if right_lim - need < left_end:   # header row taken (y title + colour legend): a free plot corner instead
            from ._page import _ov
            busy = [e["box"] for e in ex.reg if e.get("kind") in ("mark", "text") and e.get("tag") not in ("grid", "band")
                    and e.get("box") and len(e["box"]) == 4]
            busy += [(min(e["box"][0][0], e["box"][1][0]) - 1, min(e["box"][0][1], e["box"][1][1]) - 1,
                      max(e["box"][0][0], e["box"][1][0]) + 1, max(e["box"][0][1], e["box"][1][1]) + 1)
                     for e in ex.reg if e.get("kind") == "line" and e.get("tag") not in ("grid", "leader")]
            for x0_, y0_ in ((ax.x + ax.w - need - 4, ax.y + 4), (ax.x + 6, ax.y + 4),
                             (ax.x + ax.w - need - 4, ax.y + ax.h - 20), (ax.x + 6, ax.y + ax.h - 20)):
                if x0_ >= ax.x and not any(_ov((x0_ - 2, y0_ - 2, x0_ + need + 2, y0_ + 18), b) for b in busy):
                    cx, base_y = x0_, y0_ + 13
                    cy = base_y - size * 0.33
                    break
        if lab:
            ex.text(cx, base_y, lab, size=size, fill=ex.C["sub"])
            cx += tw(lab, size) + 8
        x_start = cx
        for r, v in zip(rs, sorted(values, reverse=True)):
            ex.circle(cx + r, cy, r, "none", stroke=ex.C["context"], width=0.8, register=False)
            ex.text(cx + 2 * r + 4, base_y, fmt_v(v), size=size, fill=ex.C["sub"])
            cx += 2 * r + 6 + tw(fmt_v(v), size) + 12
        ex.occupy((x_start - (tw(lab, size) + 8 if lab else 0), base_y - 14, cx, base_y + 8), "mark", "legend")
        return cx, base_y + 8
    for i, ln in enumerate(label_lines):
        ex.text(x, y + i * 13, ln, size=size)
    lx = x + (max((tw(l, size) for l in label_lines), default=0) + 16 if label_lines else 0)
    rmax = max(to_r(v) for v in values)
    base = y - size * 0.8 + 2 * rmax + 2
    cx, vx = lx + rmax, lx + 2 * rmax + 14
    for v in sorted(values, reverse=True):
        r = to_r(v)
        ex.circle(cx, base - r, r, "none", stroke=ex.C["context"], width=0.8, register=False)
        ty = base - 2 * r
        ex.line(cx, ty, vx - 3, ty, stroke=ex.C["context"], width=0.6, tag="leader")
        ex.text(vx, ty + 4, fmt_v(v), size=size, fill=ex.C["sub"])
    right = vx + max(tw(fmt_v(v), size) for v in values)
    ex.occupy((x, y - size, right, base), "mark", "legend")
    return right, base


def axis_arrow_title(ex, x, y_top, y_bot, lines, size=11):
    """Left axis title as a stacked block with a long double arrow beside it. lines: [(text, weight)]."""
    ex.line(x, y_top, x, y_bot, stroke=ex.C["text"], width=0.8, marker="arr_s", marker_start="arr_s", tag="axis-arrow")
    mid = (y_top + y_bot) / 2 - (len(lines) - 1) * size * 0.6
    for i, (t, wgt) in enumerate(lines):
        ex.text(x - 8, mid + i * size * 1.2, t, size=size, weight=wgt, fill=ex.C["ink"], anchor="end")


# ===================================================================================== xy marks


FOCUS_FADE = 0.35   # fill-opacity of de-focused marks whose colour names a category / series (legend colour kept)


def _bubble_colours_are_categories(pts, default, accent=None):
    """True when bubble colours encode categories: ≥ 2 distinct colours (accent / grey / orange included). The one
    exception is a single focus bubble — one point in accent (or highlight=True), every other point sharing one colour."""
    if not any(p.get("color") for p in pts):
        return False
    cols = [p.get("color") or default for p in pts]
    counts = {c: cols.count(c) for c in cols}
    if len(counts) < 2:
        return False
    if len(counts) == 2 and len(pts) >= 3:
        odd = [p for p, c in zip(pts, cols) if counts[c] == 1]
        if len(odd) == 1 and (odd[0].get("highlight") or (accent and (odd[0].get("color") == accent))):
            return False   # one focus bubble against the rest: emphasis, not a category
    return True


def _quadrant_keyed(ax, pts):
    """The colours are keyed by quadrants(): exactly two colours, one a grey (dim / context), and every coloured point
    sits in the shaded quadrant whose name is written on the chart."""
    q = getattr(ax, "_quad", None)
    if not q or not q[2]:
        return False
    C = ax.s.C
    greys = {C.get(k) for k in ("dim", "context", "sub")} - {None}
    cols = {p.get("color") or C["main"] for p in pts}
    if len(cols) != 2 or not (cols & greys):
        return False
    xv, yv, shade = q
    inside = lambda p: ((p["x"] > xv) == shade.endswith("R")) and ((p["y"] > yv) == shade.startswith("T"))
    keyed = all(inside(p) for p in pts if (p.get("color") or C["main"]) not in greys)
    if keyed:
        grey_in = [i + 1 for i, p in enumerate(pts) if (p.get("color") or C["main"]) in greys and inside(p)]
        if grey_in:
            raise ValueError(f"第 {grey_in} 个点落在高亮象限却是灰色：象限着色要一致——高亮象限里的点都用强调色"
                             "（color=ex.C['accent'] if 在该象限 else ex.C['context']，按坐标算，不手挑）")
    return keyed


def _qualitative_axes(pts):
    """"横轴/纵轴" whose values are a few integer levels (≤ 4 distinct, span ≤ 3, e.g. 1–3), "" otherwise. Both axes
    must look like levels — a 1–5 score on one axis against a real number on the other is a real scatter."""
    def levels(key):
        vs = [p.get(key) for p in pts if isinstance(p.get(key), (int, float))]
        return bool(vs) and all(float(v).is_integer() for v in vs) and len(set(vs)) <= 4 and max(vs) - min(vs) <= 3
    return "横轴和纵轴" if levels("x") and levels("y") else ""


def bubbles(ax, pts, size_max=None, r_max=None, r_min=4, label_size=11, prefer=None, focus=None, label_weight=700,
            numbered=None, groups=None, key=None):
    """Scatter / bubble plot with automatic labels (queued; largest bubble first; never left of the y axis).

    pts: dicts with x, y and optional size (area-proportional), color, label, sub, hollow, highlight, prefer, group.
    groups=True (or {group: colour}): colour bubbles by p["group"] with a legend — use it to show clusters; the
    colours drawn are kept in ex.group_colors {group: colour} for points(..., [(lead, text, ex.group_colors[g])]).
    focus: callable(pt) -> bool; others drawn in dim grey. Returns [(px, py, r)].
    numbered=True: draw 1, 2, 3… inside/next to each bubble instead of text labels (for crowded matrices such as risk
    maps); list "① name — response" in the XML side column with points(). Points sharing a position are nudged apart.
    numbered=None (default): numbered automatically when there are ≥ 4 bubbles and none carries a label (a risk
    matrix explained in a side list); numbered=False forces plain unlabelled bubbles.
    key=None (default): when ≥ 6 labelled bubbles crowd together (labels would stack with long leaders), every bubble
    gets its own palette colour and the names go in a colour key right of the plot (needs NAxes.fit(..., key_w=120));
    key=True forces it, key=False keeps per-bubble labels.
    Radius ∝ √size (area-proportional) up to r_max (default: 12 % of the plot's short side, at most 34); every bubble
    is kept fully inside the plot area.
    """
    if len(pts) < 3:
        def _k(p_, *ks):
            return next((p_[k] for k in ks if isinstance(p_, dict) and k in p_), None)
        rows_ = ", ".join(f"dict(label={_k(p_, 'label', 'name')!r}, x={_k(p_, 'x')!r}, y={_k(p_, 'y')!r})" for p_ in pts[:2])
        if len(pts) < 2:
            raise ValueError("bubbles 只有 1 个点，看不出分布/象限——用 big_number + 一句结论（或补齐同类对象再画）")
        raise ValueError(f"bubbles 少于 3 个点（收到 {len(pts)} 个），看不出分布/象限——改用 row_table（对象 × 两个指标），直接可用：\n"
                         f"  row_table(ex, ex.body, [{rows_}], [Label('label'), Bar('x', header='指标1'), Bar('y', header='指标2')])")
    if any("level" in p for p in pts):   # risk_matrix points may carry a level word
        from ._table import check_risk_levels
        check_risk_levels([p.get("level") for p in pts], "bubbles/risk_matrix level")
    ex = ax.s
    if groups:  # colour by p["group"] and add a one-line legend at the top-right of the plot
        cols = groups if isinstance(groups, dict) else {}
        pal = [ex.C["main"], ex.C["accent"], ex.C["third"], ex.C["second"], ex.C["context"]]
        names = list(dict.fromkeys(p.get("group") for p in pts if p.get("group")))
        for i, g in enumerate(names):
            cols.setdefault(g, pal[i % len(pal)])
        for p in pts:
            if p.get("group") and not p.get("color"):
                p["color"] = cols[p["group"]]
        shown = {g: cols[g] for g in names}   # focus= fades the other bubbles but keeps their group colour
        ex.group_colors = dict(getattr(ex, "group_colors", None) or {}, **shown)   # points(mark=ex.group_colors[g])
        items = [(g, shown[g], "dot") for g in names]
        lw = sum(tw(g, 10.5) + 30 for g in names)
        legend(ex, ax.x + ax.w - lw, ax.y - 10, items, size=10.5)   # header row, right of the y title — not in the plot
        ex.occupy((ax.x + ax.w - lw, ax.y - 22, ax.x + ax.w, ax.y - 2), "mark", "legend")
    sizes = [p.get("size") for p in pts if p.get("size") is not None]
    smax = size_max or (max(sizes) if sizes else None)
    if r_max is None:
        r_max = min(34.0, max(r_min + 4.0, 0.12 * min(ax.w, ax.h)))
    if numbered is None:
        numbered = len(pts) >= 4 and not any(p.get("label") for p in pts)
    skipped = [p.get("label", "?") for p in pts if p.get("x") is None or p.get("y") is None]
    if skipped:  # an undisclosed value must not be drawn at an invented position; list it in a note instead
        print(f"bubbles: 未画坐标缺失的点 {skipped}（在脚注写'未披露'）")
    pts = [p for p in pts if p.get("x") is not None and p.get("y") is not None]
    outside = [p.get("label", f"({p['x']}, {p['y']})") for p in pts
               if not (ax.xmin <= p["x"] <= ax.xmax and ax.ymin <= p["y"] <= ax.ymax)]
    if outside:
        raise ValueError(f"bubbles: {outside} 落在坐标轴范围外——把 NAxes.fit 的 xlim/ylim（及 xticks/yticks）放宽到包含全部点")
    # colours that encode categories (groups= or ≥ 2 colours shown in a legend) survive focus=: others only fade
    keyed = bool(groups) or _bubble_colours_are_categories(pts, ex.C["main"], ex.C.get("accent"))
    out, seen = [None] * len(pts), {}
    big_first = sorted(range(len(pts)), key=lambda i: -(pts[i].get("size") or 0))  # small bubbles stay on top
    for i in big_first:
        p = pts[i]
        px, py = ax.sx(p["x"]), ax.sy(p["y"])
        k = (round(px / 14), round(py / 14))
        r = r_min if (smax is None or p.get("size") is None) else max(r_max * math.sqrt(p["size"] / smax), r_min)
        if k in seen:  # identical / near-identical scores: fan out so every bubble stays visible
            n = seen[k] = seen[k] + 1
            inside = lambda q: (ax.x + r < q[0] < ax.x + ax.w - r) and (ax.y + r < q[1] < ax.y + ax.h - r)
            cands = [(px + 15 * math.cos(n * 2.1 + j * 0.8), py + 15 * math.sin(n * 2.1 + j * 0.8)) for j in range(8)]
            px, py = next((q for q in cands if inside(q)), cands[0])   # a direction that stays inside the plot
        else:
            seen[k] = 0
        out[i] = [px, py, r]
    if numbered:   # a number hidden under a neighbour is useless: push overlapping bubbles apart (positions ≈ scores)
        for _ in range(40):
            moved = False
            for a in range(len(out)):
                for b in range(a + 1, len(out)):
                    (x1, y1, r1), (x2, y2, r2) = out[a][:3], out[b][:3]
                    need = (r1 + r2) * 0.92
                    d = math.hypot(x2 - x1, y2 - y1)
                    if d < need:
                        ux, uy = ((x2 - x1) / d, (y2 - y1) / d) if d > 0.1 else (0.8, -0.6)
                        k = (need - d) / 2 + 0.5
                        out[a][0] -= ux * k; out[a][1] -= uy * k
                        out[b][0] += ux * k; out[b][1] += uy * k
                        moved = True
            for q in out:
                q[0] = min(max(q[0], ax.x + q[2]), ax.x + ax.w - q[2])
                q[1] = min(max(q[1], ax.y + q[2]), ax.y + ax.h - q[2])
            if not moved:
                break
    crowded = not numbered and not groups and _bubbles_crowded(ax, pts, out)
    room = getattr(ax, "key_w", 0) >= 80 or key is True
    key_mode = key is True or (key is None and crowded and room)
    if crowded and key is None and not room:
        print("bubbles 提醒：气泡拥挤、标签会挤在一起——NAxes.fit(..., key_w=120) 给图右侧留出颜色图例位，"
              "bubbles 会自动给每个气泡不同颜色并在右侧列名称（不再逐个贴标签）")
    if key_mode:   # labels would pile up: one colour per bubble, names listed in a colour key right of the plot
        _bubble_key_colors(ex, pts, out)
        keyed = True
    for i in big_first:
        p = pts[i]
        px, py, r = out[i]
        px = min(max(px, ax.x + r + 1), ax.x + ax.w - r - 1) if ax.w > 2 * r + 2 else ax.x + ax.w / 2   # inside the plot
        py = min(max(py, ax.y + r + 1), ax.y + ax.h - r - 1) if ax.h > 2 * r + 2 else ax.y + ax.h / 2
        px = min(max(px, r + 1), ex.w - r - 1)  # never let a bubble spill off the canvas
        col = p.get("color") or ex.C["main"]
        faded, bold = None, False
        if focus is not None:
            if not focus(p) and keyed:
                faded = FOCUS_FADE   # colours name categories (legend): keep the hue, only fade
            elif not focus(p):
                col = ex.C["dim"]
            elif keyed:
                bold = True          # focus bubble of a colour-keyed chart: dark rim, same colour
        rim, rim_w = (ex.C["ink"], 2) if bold else ("#FFFFFF", 1)
        if p.get("hollow"):
            ex.circle(px, py, r, "#FFFFFF", stroke=col, width=2.2 if bold else 1.4, opacity=faded)
        elif r > 18:  # large bubbles: translucent with a white rim so overlapped neighbours stay readable
            ex.add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="{col}" fill-opacity="{faded or 0.82}" '
                   f'stroke="{rim}" stroke-width="{1.2 if not bold else rim_w}"/>')
            ex._add("mark", (px - r, py - r, px + r, py + r), "circle", circle=(px, py, r), fill=col)
        else:
            ex.circle(px, py, r, col, stroke=rim, width=rim_w, opacity=faded)
        out[i] = (px, py, r)
    _bubble_overlaps(ex, pts, out)
    if len({p.get("size") for p in pts if p.get("size") is not None}) >= 2:
        ex.sized_bubbles = True   # to_slide refuses when no size_legend() explains what the area means
        ex.bubble_to_r = lambda v, _m=r_max, _s=smax, _n=r_min: max(_m * math.sqrt(v / _s), _n)   # for size_legend
    if not groups and _bubble_colours_are_categories(pts, ex.C["main"], ex.C.get("accent")) \
            and not _quadrant_keyed(ax, pts):   # to_slide refuses without a legend
        ex.legend_needed = list(getattr(ex, "legend_needed", None) or []) + ["bubbles 点的颜色"]
        ax._bubble_pts = pts   # quadrants() drawn afterwards may still key the colours
    level_axes = _qualitative_axes(pts)
    if level_axes:   # print-only: positions on 1–3 levels read as false precision on a continuous axis
        print(f"bubbles 提醒：{level_axes} 只有几档整数等级（如 1–3 的高/中/低），画成连续坐标会被读成精确数值——"
              "改用 risk_register（row_table + Level 档位列）；确是连续数值就忽略")
    xt = getattr(ax, "_xtitle", "") or ""
    yt = getattr(ax, "_ytitle", "") or ""
    if re.search(r"可能性|概率|likelihood|probability", xt + yt, re.I) and re.search(r"影响|impact|严重", xt + yt, re.I) \
            and all(0 <= p.get("x", -1) <= 5 and 0 <= p.get("y", -1) <= 5 for p in pts) and not any(p.get("size") for p in pts):
        raise ValueError("bubbles：'可能性 × 影响' 是 0–5 的团队打分——定性判断画成坐标点会被读成精确数值。改用 risk_register："
                         "row_table(ex, box, rows, [Label('label'), Level('p', header='可能性'), Level('i', header='影响'), "
                         "Note('sig', header='触发信号'), Note('act', header='应对')])，档位写 低 / 中 / 中高 / 高（exhibit_help('risk_register')）；"
                         "只有真实概率 % 与影响金额时才用坐标")
    if numbered:
        from ._page import add_fact
        add_fact(ex, {"kind": "bubble_numbers", "n": len(out)})   # Frame.publish checks the side list names them all
        ex.num_dots = getattr(ex, "num_dots", 0) + len(out)   # numbered bubbles are the dots a numbered rail points at
        for i, (p, (px, py, r)) in enumerate(zip(pts, out), 1):
            if r >= 8:
                ex.text(px, py + 4, str(i), size=10.5, weight=700, anchor="middle", register=False,
                        fill="#FFFFFF" if not p.get("hollow") else ex.C["ink"])
            else:
                place_label(ex, px, py, [str(i)], size=10.5, r=r, weights=[700], fills=[ex.C["ink"]], priority=2,
                            _circle=(px, py, r), bounds=ax.label_bounds())
        return out
    if key_mode:
        _bubble_key_column(ax, pts, out)
    for p, (px, py, r) in zip(pts, out):
        if not p.get("label") or p.get("_keyed"):
            continue
        rows, w = [p["label"]], [label_weight]
        f = [p.get("label_color") or (p.get("color") if p.get("highlight") else ex.C["ink"])]
        if p.get("sub"):
            rows.append(p["sub"])
            w.append(400)
            f.append(ex.C["sub"])
        place_label(ex, px, py, rows, size=label_size, r=r, weights=w, fills=f, priority=2,
                    prefer=p.get("prefer") or prefer or ("E", "W", "NE", "NW", "N", "S", "SE", "SW"),
                    _circle=(px, py, r), bounds=ax.label_bounds())
    return out


def _crowded_set(pts, circles, near=46):
    """Labelled bubbles that sit within `near` px of another labelled bubble (their labels would stack)."""
    lab = [i for i, p in enumerate(pts) if p.get("label")]
    out = set()
    for i in lab:
        x, y, r = circles[i]
        for j in lab:
            if j != i and math.hypot(circles[j][0] - x, circles[j][1] - y) < near + 0.3 * max(r, circles[j][2]):
                out.add(i)
                break
    return out


def _bubbles_crowded(ax, pts, circles, near=46):
    """≥ 3 labelled bubbles packed together: those get a colour key instead of stacked labels."""
    return len(_crowded_set(pts, circles, near)) >= 3


def _key_palette(C, n):
    """n colours that read apart, staying inside the palette: its distinct hues (main / accent / neg / third), each
    at three lightness steps (base, light, dark), interleaved so neighbours differ in hue and lightness."""
    from ._palette import _mix as _mx
    from ._palette import contrast as _ct
    hues = []
    for c in (C["main"], C["accent"], C.get("neg", C["third"]), C["third"], C["second"]):
        if all(_hue_gap(c, h) > 25 or abs(_ct(c) - _ct(h)) > 3 for h in hues):
            hues.append(c)
    steps = (lambda c: c, lambda c: _mx(c, "#FFFFFF", 0.5), lambda c: _mx(c, "#000000", 0.35))
    out = []
    for st in steps:
        for h in hues:
            col = st(h)
            if col not in out:
                out.append(col)
    k = 0
    while len(out) < n:   # more objects than steps: lighter still
        out.append(_mx(hues[k % len(hues)], "#FFFFFF", 0.72))
        k += 1
    return out[:n]


def _hue_gap(a, b):
    import colorsys
    def h(c):
        c = c.lstrip("#")
        return colorsys.rgb_to_hls(*(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)))[0] * 360
    d = abs(h(a) - h(b)) % 360
    return min(d, 360 - d)


def _bubble_key_colors(ex, pts, circles):
    """The crowded bubbles get one distinct colour each (top-to-bottom, so the key reads in the same order); the
    others keep their colour and their direct label."""
    crowd = _crowded_set(pts, circles)
    order = sorted(crowd, key=lambda i: circles[i][1])
    cols = _key_palette(ex.C, len(order))
    for k, i in enumerate(order):
        pts[i]["color"] = cols[k]
        pts[i]["_keyed"] = True
    ex._key_order = order


def _bubble_key_column(ax, pts, circles):
    """'● name' rows in a column right of the plot for the keyed (crowded) bubbles, in their top-to-bottom order."""
    ex = ax.s
    order = getattr(ex, "_key_order", None) or []
    kx = ax.x + ax.w + 16
    step = min(20.0, max(14.0, (ax.h - 8) / max(1, len(order))))
    ky = max(ax.y + 8, min(ax.y + ax.h - step * len(order),   # the key sits level with the crowd it explains
                           sum(circles[i][1] for i in order) / max(1, len(order)) - step * len(order) / 2))
    for i in order:
        ex.circle(kx + 5, ky - 4, 5, pts[i]["color"], register=False)
        ex.text(kx + 14, ky, str(pts[i]["label"]), size=10.5, weight=600, fill=ex.C["ink"])
        ky += step
    ex.legend_drawn = True
    ex.legend_log = list(getattr(ex, "legend_log", None) or []) + [(str(pts[i]["label"]), pts[i]["color"]) for i in order]
    ex.legend_needed = [x for x in (getattr(ex, "legend_needed", None) or []) if "bubbles" not in x]


def _circle_overlap(c1, c2):
    """Intersection area of two circles (x, y, r)."""
    (x1, y1, r1), (x2, y2, r2) = c1, c2
    d = math.hypot(x2 - x1, y2 - y1)
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = r1 * r1 * math.acos(max(-1.0, min(1.0, (d * d + r1 * r1 - r2 * r2) / (2 * d * r1))))
    a2 = r2 * r2 * math.acos(max(-1.0, min(1.0, (d * d + r2 * r2 - r1 * r1) / (2 * d * r2))))
    k = 0.5 * math.sqrt(max(0.0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)))
    return a1 + a2 - k


BUBBLE_OVERLAP = 0.40   # share of the smaller bubble's area covered by another one: the two read as one blob


def _bubble_overlaps(ex, pts, circles, share=BUBBLE_OVERLAP, min_r=8):
    """Record "气泡 A 与 B 几乎重合" in ex.extra_issues (reported by ex.check()) for every pair of bubbles (both
    r ≥ min_r, i.e. sized ones) where one covers > share of the smaller one's area."""
    found = []
    for a in range(len(circles)):
        for b in range(a + 1, len(circles)):
            ca, cb = circles[a], circles[b]
            if min(ca[2], cb[2]) < min_r:
                continue
            if _circle_overlap(ca, cb) > share * math.pi * min(ca[2], cb[2]) ** 2:
                la = pts[a].get("label") or f"#{a + 1}"
                lb = pts[b].get("label") or f"#{b + 1}"
                found.append(f"气泡 {la} 与 {lb} 几乎重合：改用 row_table 或缩小 size 映射（bubbles(r_max=)）")
    if found:
        ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + found))
    return found


def vertex_dots(ex, pts, color, r=3, width=1.4, register=True):
    """Hollow markers on a polyline's vertices: the series is drawn as separate native line pieces, and without a
    marker each joint reads as a break. Skipped when the points are too close to tell apart."""
    if len(pts) < 2 or min(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(pts, pts[1:])) < 3.2 * r:
        return
    for a, b in pts:
        ex.circle(a, b, r, "#FFFFFF", stroke=color, width=width, register=register)


def runs(xs, ys):
    """Consecutive (x, y) runs between missing values: a None breaks the line — no segment bridges the gap."""
    out, cur = [], []
    for x, y in zip(xs, ys):
        if y is None:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append((x, y))
    return out + ([cur] if cur else [])


def gap_marks(ex, xs, ys, sx, y_base, zh=True):
    """'缺' under every interior missing value of a series (first / last non-None bound it): the break in the line is
    data, not a drawing fault. Returns the x values marked."""
    have = [i for i, y in enumerate(ys) if y is not None]
    if len(have) < 2:
        return []
    miss = [xs[i] for i in range(have[0], have[-1]) if ys[i] is None]
    done = getattr(ex, "_gap_marked", None)
    if done is None:
        done = ex._gap_marked = set()
    for x in miss:
        if x in done:
            continue
        done.add(x)
        ex.text(sx(x), y_base, "缺" if zh else "n/a", size=10, fill=ex.C["sub"], anchor="middle")
    return miss


def polyline(ax, xs, ys, color, width=2, dash=None, dots=True, r=3):
    """Series line; a None value breaks it (no segment, no dot across the gap). Returns the drawn points."""
    ex = ax.s
    parts = [[(ax.sx(x), ax.sy(y)) for x, y in run] for run in runs(xs, ys)]
    pts = [p for part in parts for p in part]
    el0 = len(ex.el)   # native line pieces, one ex.el entry (a stroked path becomes a custom shape the server reads
    for part in parts:   # as a filled box: labels inside it "overflow" it)
        for p, q in zip(part, part[1:]):
            ex.line(*p, *q, stroke=color, width=width, dash=dash, register=False, whole=True)
    ex.el[el0:] = ["".join(ex.el[el0:])]
    for part in parts:
        for p, q in zip(part, part[1:]):
            ex._add("line", (p, q), "series", stroke=color, width=width, whole=True)
    if dots:
        for part in parts:
            if len(part) == 1 and len(parts) > 1:   # an isolated point between gaps: still visible
                ex.circle(*part[0], r, "#FFFFFF", stroke=color, width=1.4, register=False)
            else:
                vertex_dots(ex, part, color, r=r)
    return pts


def _flow_bands(ex, ax, bands, categories, series, flow, C):
    """Bands joining each stacked segment to the same segment of the next column (see columns(flow=))."""
    from ._palette import _mix as _pmix
    n = len(categories)
    if flow is False:
        return
    if flow is None:   # auto: periods on the axis, a readable number of columns and layers
        from ._page import is_period
        if not (3 <= n <= 8 and len(series) <= 5 and all(is_period(c) for c in categories)):
            return
    pick = None
    if isinstance(flow, str):
        pick = {flow}
    elif isinstance(flow, (list, tuple, set)):
        pick = {str(x) for x in flow}
    names = {str(nm) for nm, _, _ in series}
    if pick is not None and not pick & names:
        raise ValueError(f"columns(flow=)：{sorted(pick)} 不是系列名（可选：{sorted(names)}）")
    base0 = 0.0 if ax.ymin <= 0 else ax.ymin
    edges = []   # per column: {series: (y_top, y_bottom)} in slide coordinates
    for i in range(n):
        acc, d = base0, {}
        for nm, vals, _ in series:
            v = vals[i] or 0
            d[str(nm)] = (ax.sy(acc + v), ax.sy(acc))
            acc += v
        edges.append(d)
    for nm, vals, col in series:
        if pick is not None and str(nm) not in pick:
            continue
        try:
            fill = _pmix(col, "#FFFFFF", 0.8)   # pale: the band reads as a link, the bars stay the data
        except (ValueError, TypeError, IndexError):
            fill = C["track"]
        for i in range(n - 1):
            if not (vals[i] and vals[i + 1]):
                continue
            (bx0, bw0), (bx1, _) = bands[i], bands[i + 1]
            x0, x1 = bx0 + bw0, bx1
            (t0, b0), (t1, b1) = edges[i][str(nm)], edges[i + 1][str(nm)]
            # one closed shape (pale fill + thin outline in the series colour): a single editable element per gap; its
            # vertical sides sit on the bars' edges of the same colour, so only the two slanted edges show
            ex.path(f"M{x0:.1f},{t0:.1f} L{x1:.1f},{t1:.1f} L{x1:.1f},{b1:.1f} L{x0:.1f},{b0:.1f} Z", fill=fill,
                    stroke=col, width=0.6, register=False)


def area_stack(ax, xs, series):
    """Stacked areas. series: [(name, values, color)] bottom-up. Returns cumulative tops per series."""
    ex = ax.s
    cum = [0.0] * len(xs)
    tops = []
    for _, vals, color in series:
        nxt = [c + (v or 0) for c, v in zip(cum, vals)]
        up = [(ax.sx(x), ax.sy(v)) for x, v in zip(xs, nxt)]
        dn = [(ax.sx(x), ax.sy(v)) for x, v in reversed(list(zip(xs, cum)))]
        ex.path("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in up + dn) + " Z", fill=color, register=False)
        cum = nxt
        tops.append(nxt)
    top = [(ax.sx(x), ax.sy(v)) for x, v in zip(xs, cum)]
    for (a, b), (c, d) in zip(top, top[1:]):
        ex._add("mark", (a, min(b, d), c, ax.sy(ax.ymin)), "area")
    return tops


def gap_fill(ax, xs, a, b, color_a_above, color_b_above, opacity=1.0):
    """Fill between two series; colour switches at each crossing (who is ahead)."""
    ex = ax.s
    segs = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        d0, d1 = a[i] - b[i], a[i + 1] - b[i + 1]
        if d0 * d1 < 0:
            t = d0 / (d0 - d1)
            xm, ym = x0 + t * (x1 - x0), a[i] + t * (a[i + 1] - a[i])
            segs += [([(x0, a[i]), (xm, ym)], [(x0, b[i]), (xm, ym)], d0),
                     ([(xm, ym), (x1, a[i + 1])], [(xm, ym), (x1, b[i + 1])], d1)]
        else:
            segs.append(([(x0, a[i]), (x1, a[i + 1])], [(x0, b[i]), (x1, b[i + 1])], d0 if d0 != 0 else d1))
    for top, bot, d in segs:
        pts = top + list(reversed(bot))
        col = color_a_above if d > 0 else color_b_above
        ex.path("M" + " L".join(f"{ax.sx(px):.1f},{ax.sy(py):.1f}" for px, py in pts) + " Z", fill=col,
                stroke=col, width=0.6, opacity=opacity, register=False)


# ===================================================================================== column family


def stacked_bar(ax, x, w, segs):
    """Absolute stacked column: segs [(value, color)] bottom-up. Returns top pixel y."""
    base = 0.0 if ax.ymin <= 0 else ax.ymin
    for v, color in segs:
        if not v:
            continue
        y0, y1 = ax.sy(base), ax.sy(base + v)
        ax.s.rect(x, min(y0, y1), w, abs(y0 - y1), color)
        base += v
    return ax.sy(base)


FLAT_SHARES_PT = 3   # 100 % stacked bars whose every segment moves < 3pt look identical (e.g. 95 % vs 90 %)
FLAT_SHARES = "各期构成差异都小于 3pt，100% 堆叠条看起来一样：改 slope / dumbbell_table（聚焦轴域）只画变化的那一段"

_RATE_WORDS = re.compile(r"率|占比|份额|市占|渗透|比重|比例|%|％|margin|share|ratio|rate|penetration", re.I)
# a count / amount by its own name (会员数, 门店, 收入, 亿元 …): never a rate, whatever the slot title says
_QTY_WORDS = re.compile(r"(?<!比)数(?!率)|人数|会员|用户|门店|店数|收入|营收|销量|销售额|金额|规模|GMV|订单|"
                        r"(?<![千万亿])元|[亿万千]|家数|客流|revenue|sales|users|members|stores|count|volume", re.I)


def _rate_by_name(names, values, slot_title=""):
    """'%' when the series is a rate (margin / share / 占比) by its own name — or, for a series named generically,
    by its chart slot title — and every value lies in −100…100; else None. A series whose own name says it is a
    count or amount (活跃会员, 门店数, 收入) is never a rate: its change is a difference, not "pt"."""
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals or not all(-100 <= v <= 100 for v in vals):
        return None
    own = " ".join(str(n) for n in names)
    if _RATE_WORDS.search(own):
        return "%"
    if _QTY_WORDS.search(own):
        return None
    return "%" if slot_title and _RATE_WORDS.search(str(slot_title)) and not _QTY_WORDS.search(str(slot_title)) else None


def _flat_shares(ex, series, n):
    """Record FLAT_SHARES in ex.extra_issues when ≥ 2 percent-stacked columns differ by < FLAT_SHARES_PT in every
    segment (shares already in 0–100)."""
    if n < 2 or len(series) < 2:
        return False
    spread = max(max(s[1]) - min(s[1]) for s in series)
    if spread >= FLAT_SHARES_PT:
        return False
    ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or [])
                                         + [f"{FLAT_SHARES}（最大变化 {spread:.1f}pt）"]))
    return True


SIGNAL_SINGLE_PCT: list = []   # one 100% column drawn on this page: f.publish suggests icon_grid once


def columns(ex, box, categories, series, stack=None, ymax=None, ticks=None, focus=None, values=True,
            value_fmt=lambda v: fmt(v), label_width=None, totals=None, forecast_from=None, pad=0.32, group_gap=0.12,
            show_grid=True, legend_items=True, cagr=None, yoy=None, diff=None, target=None, order="heavy", delta=None,
            delta_fmt=None, note=None, unit=None, share_y=None, diff_series=None, ymin=None, rows=None, flow=None):
    """Vertical column chart in box: grouped (stack=None), absolute stacked ('stack') or 100% ('percent').

    rows=[(name, values), …] or [(name, values, fmt)]: 1–2 data rows under the category axis, one number under each
    column (L.E.K. / Bain "chart + data row"): a second metric of the same objects and periods (margin, deal count,
    share, avg size) without a second chart or a second y axis. Row name sits left of the axis; each row gets a
    light band; values must be one per category (None prints "—"). A rate row (name or fmt with %) prints pt-free
    values as given — no arithmetic is done on rows.

    unit: the values' unit (or a METRICS dict). A rate unit (%, pt, pp) labels delta= / diff= / yoy= changes in pt
    (b − a), never as a % of a percentage; unknown unit = unchanged.

    series: [(name, values, color)]; None values are skipped. focus: callable(category, series_name) -> bool (others
    dimmed), or a category index / name / series name, or a tuple of them. forecast_from: index of the first forecast category — those columns use each series' light tone and a
    dashed divider with 实绩/预测 labels. totals=True prints the stack total above stacked columns.
    Argument notes (think-cell style, % computed from the data): cagr=(i, j) or [(i, j), (j, k)] CAGR arrow(s) — a
    yearly amount series gets them automatically, not rates or percentages; yoy=k or [k, …] change
    arrow between column k and k+1; diff=(i, j) total-difference arrow (leave ~60px right of the box); target=(value,
    "label") target line; on grouped columns (≥2 series, no stack) diff= needs diff_series="<series name>" (which
    series' two bars are compared — the same object in two periods is delta=, not diff=). diff/yoy/cagr compare categories; delta=(a, b) compares the two series a → b inside each
    category of a grouped chart: a small bracket over the pair with "series b − series a" (delta=(a, b, [cat idx…])
    for chosen categories only; delta_fmt=callable(d) -> str, default "+x" via value_fmt). Use the one that proves
    the page title.
    flow=True (stacked columns over periods): between neighbouring columns each segment is joined to the same segment of
    the next column by a light band (two edges + a pale fill of the series colour, one editable shape per gap) — the
    reader follows one category's growth / decline. flow="<series name>" (or a list) draws only those series' bands.
    Default (flow=None): on for stacked period columns with 3–8 columns and ≤5 series, off otherwise.
    Stacks are ordered heavy → light: the series with the largest total sits at the bottom and takes the darkest
    colour (colours are re-assigned dark → light in that order, so pass them in any order); order="given" keeps
    the series order and colours as passed (e.g. a fixed category order shared across pages).
    note=(category or index, "what this bar means") or a list of them: a speech bubble pointing at that bar's top
    (works together with cagr/yoy/diff; ≤2 per chart). Numbers written in a note (8.7%, 26.3) must match a value the
    program computes for that bar (its values, change vs neighbours, CAGR to/from it, share) — else ValueError.
    show_grid=False hides grid lines, not value-axis ticks; values=False hides only labels on the columns.
    share_y: side-by-side panels (ex.panel) with the same unit= share the value axis automatically (magnitudes stay
    comparable); share_y=False keeps an independent axis — then state the multiple on the chart.
    Returns dict(ax=Axes, centers=[...], tops={cat: y}).
    """
    from ._page import check_box as _cb
    _cb(box, "columns")
    C = ex.C
    from ._page import chart_box as _cbx
    box = _cbx(ex, box)
    from ._page import check_box, focus_fn
    check_box(box, "columns")
    focus = focus_fn(focus, categories)
    _start, _notes0 = len(ex.el), ex.notes
    from ._kpi import is_rate_unit, pt_text
    from . import _semantics as _sem
    from ._layouts import PROFILE as _PRO
    if not stack and len(categories) >= 2:   # bars of one axis in different units (亿元 / 亿港元 / %)
        _sem.mixed_units(list(categories) + [s_[0] for s_ in series] + [unit if isinstance(unit, str) else None],
                         "columns", "第二个单位（%、倍、个数）的指标放轴下数据行 rows=[(名, 值列表, fmt)]；不同币种先换算成同一单位，或分成两张小图（各自纵轴）")
    for s__ in series:   # 4+ identical bars: a placeholder series, not data
        nm_, vv_ = s__[0], [v for v in s__[1] if v is not None]
        if len(vv_) >= 4 and len(set(vv_)) == 1 and _PRO.get("research"):
            raise ValueError(f"columns：系列 {nm_!r} 的 {len(vv_)} 个值全是 {vv_[0]:g}——像占位数，不是数据；"
                             "换成真实序列，缺的写 None（图上标'缺'）")
    if len(categories) == 1 and stack == "percent" and 2 <= len(series) <= 4 and _PRO.get("research"):
        print("columns：一根 100% 堆叠柱 = 一个整体的构成——研究稿用整页版式 icon_grid(f, [(名称, 占比), …], icon=…)"
              "（10×10 图标网格，份额/渠道/收入/用户结构都适用），或把对比年份/对象补成多根柱")
        SIGNAL_SINGLE_PCT.append(True)
    if len(categories) < 2 and not stack and len(series) < 2 and _PRO.get("research"):
        raise ValueError("columns 只有 1 根柱：一个数不成图（读者没有比较对象）——写成 KPI 数字 / kv 行，"
                         "或补上可比对象（上年、同业、目标）画成 2 根以上")
    if unit is None and stack != "percent":   # value_fmt prints "%" (14.1%) → a rate series: changes in pt, no CAGR
        sample = next((v for s_ in series for v in s_[1] if v is not None), None)
        try:
            if sample is not None and str(value_fmt(sample)).rstrip().endswith("%") \
                    and not str(value_fmt(sample)).lstrip().startswith(("+", "−", "-")):
                unit = "%"
        except Exception:  # noqa: BLE001
            pass
    if unit is None and stack != "percent":   # a margin / share / rate series by its name: changes in pt
        unit = _rate_by_name([s_[0] for s_ in series], [v for s_ in series for v in s_[1] if v is not None],
                             getattr(ex, "_slot_title", "") or "")
    rate_ = is_rate_unit(unit) and stack != "percent"
    if (is_rate_unit(unit) or stack == "percent") and cagr:
        raise ValueError("CAGR 不用于比率/增速/百分比序列；传 unit= 并用 diff= 或 yoy= 表达百分点变化")
    if cagr and _sem.is_multiple(unit, *[s_[0] for s_ in series]):
        raise ValueError("CAGR 不用于估值倍数/比率（PE、PB、EV/EBITDA、x、倍）：倍数的复合增速没有经营含义；"
                         "改用 diff= 写变化（如 '28x → 22x'），或对盈利/收入本身算 CAGR")
    if stack and len(series) >= 2:
        _sem.periods_as_segments([s_[0] for s_ in series], f"columns(stack={stack!r})")
        _range_stack_hint(ex, [s_[0] for s_ in series])
    if diff is not None and not stack and len(series) >= 2:
        names_ = [str(s_[0]) for s_ in series]
        if diff_series is None:
            raise ValueError(f"columns：分组柱（{len(series)} 个系列 {names_[:4]}）用 diff= 必须写 diff_series='<系列名>'——"
                             f"不写就拿第一个系列「{names_[0]}」的两根柱相减，常常比错对象（两家公司同一年 ≠ 标题说的变化）。"
                             "同一对象两期（如 A 公司 2014→2023）用 delta=(0, 1)（每组内系列间的差）；"
                             f"同一系列里两个类别之差才用 diff=(i, j), diff_series='{names_[-1]}'")
        if str(diff_series) not in names_:
            raise ValueError(f"columns(diff_series={diff_series!r})：不是系列名，可选 {names_}")
    if len(series) >= 2 and not legend_items and not stack:
        raise ValueError("columns：多系列却关掉了图例（legend_items=False）——颜色无从对应系列；保留图例，或在同页另画 legend()")
    _fixed_sum_guard(categories, series, stack, yoy, diff, cagr)
    _sem.uneven_time(ex, categories, "columns")
    n = len(categories)
    vals_all = [v for s_ in series for v in s_[1]]
    if len(vals_all) >= 4 and sum(v is None for v in vals_all) / len(vals_all) > 0.4:
        raise ValueError("columns：超过 40% 的柱没有数据（None）——只画有数据的类别/年份，或改用 Text 写'未披露'；"
                         "不要画一排空柱")
    if n <= 2 and len(series) == 1 and not stack:   # two bars = one difference; counted for the page precheck
        ex.two_bar = getattr(ex, "two_bar", 0) + 1
    default = [C["main"], C["second"], C["light"], C["third"], C["context"]]
    series = [(s_[0], s_[1], (s_[2] if len(s_) > 2 and s_[2] else default[k % len(default)])) for k, s_ in enumerate(series)]
    series, py_names = _py_series_grey(ex, series) if not stack else (series, set())
    if stack and order == "heavy" and len(series) > 1:
        tot_s = [sum(v or 0 for v in s_[1]) for s_ in series]
        idx = sorted(range(len(series)), key=lambda k: -tot_s[k])
        lum = lambda c: (0.299 * int(c[1:3], 16) + 0.587 * int(c[3:5], 16) + 0.114 * int(c[5:7], 16)) \
            if isinstance(c, str) and c.startswith("#") and len(c) == 7 else 128
        cols = sorted((s_[2] for s_ in series), key=lum)
        accent = [s_[2] for s_ in series if s_[2] in (C["accent"], C["neg"])]
        if accent:   # a highlighted series keeps its colour; the others go dark → light by weight
            rest = iter(c for c in cols if c not in accent)
            series = [(series[k][0], series[k][1], series[k][2] if series[k][2] in accent else next(rest)) for k in idx]
        else:
            series = [(series[k][0], series[k][1], cols[r_]) for r_, k in enumerate(idx)]
    if stack == "percent":
        tot = [sum((s[1][i] or 0) for s in series) or 1 for i in range(n)]
        series = [(nm, [((v or 0) / tot[i] * 100) for i, v in enumerate(vals)], col) for nm, vals, col in series]
        _flat_shares(ex, series, n)
    if stack:
        top_v = max(sum((s[1][i] or 0) for s in series) for i in range(n))
        if stack != "percent" and ymax is None and 96 <= top_v <= 101 and all(
                96 <= sum((s[1][i] or 0) for s in series) <= 101 for i in range(n) if any(s[1][i] for s in series)):
            ymax = 100   # shares that already sum to 100: no empty band above
    else:
        top_v = max(v for s in series for v in s[1] if v is not None)
    min_v = 0 if stack else min([0] + [v for s in series for v in s[1] if v is not None])
    if ymax is None and stack != "percent":
        ymax = _sem.share_scale(ex, unit, top_v * 1.08, share_y, stack)
    data_rows = _check_rows(rows, categories, "columns")
    longest = max(len(str(c)) for c in categories)
    rows = 2 if (label_width and any(tw(c, 10.5) > label_width for c in categories)) else 1
    rows_h = ROW_H * len(data_rows) + (6 if data_rows else 0)
    if data_rows:   # the strip under the axis is taken from the box bottom (the bars keep the rest)
        box = (box[0], box[1], box[2], box[3] - rows_h)
    leg_h = 22 if (legend_items and len(series) > 1) else 0
    from ._axes import bar_ticks as _nt
    from ._page import frame_w
    _tk = ticks or _nt(ymax or (100 if stack == "percent" else top_v * 1.08), 4, min_v)
    _tfmt = (lambda v: f"{v:.0f}%") if stack == "percent" else (lambda v: fmt(v))
    left_ = max(34, max(frame_w(_tfmt(t), 10.5) for t in _tk) + 10)   # tick labels must fit left of the axis
    if data_rows:   # the row names sit in the same left margin: widen it if a name is wider than the tick labels
        left_ = max(left_, max(tw(n_, 10, True) for n_, _, _ in data_rows) + 10)
    fit = lambda tp: Axes.fit(ex, (box[0], box[1] + leg_h, box[2], box[3]),  # noqa: E731
                              ymax or (100 if stack == "percent" else top_v * 1.08), ymin=min_v, ticks=ticks,
                              label_rows=rows, top_pad=tp, left=left_)
    ax = fit(24)
    if delta is not None and not stack:   # the series-delta bracket + label sit ~36px above the tallest bar
        short = (box[1] + leg_h + 2) - (ax.sy(top_v) - (16 if values else 4) - 8 - 12)
        if short > 0:
            ax = fit(24 + short)
    if stack != "percent":   # stacked layers above the tallest bar: value label → yoy oval → CAGR line → bubble.
        # Each gets its own band so they never compete for the same strip (three notes over one bar overlapped).
        will_cagr = bool(cagr) or (cagr is None and _auto_cagr(categories, series, stack, forecast_from, yoy, diff,
                                                               target, delta, ex, unit=unit))
        layers = (16 if values else 4) + (30 if yoy is not None else 0) + (26 if will_cagr else 0)
        layers += (34 * min(len(_note_list(note)), 2) + 10) if note else 0
        if (yoy is not None) + bool(will_cagr) + bool(note) >= 2:
            want = 24 + layers
            short = (box[1] + leg_h + want) - ax.sy(top_v)
            if short > 0 and (box[3] - box[1]) > 140:
                ax = fit(24 + min(short, (box[3] - box[1]) * 0.42))
    ax.grid(fmt_tick=_tfmt, lines=show_grid)
    bands = ax.bands(n, pad=pad)
    lab_boxes, dropped_vals = [], []   # grouped value labels placed / left out (wider than their bar)
    centers, tops, seg_y = [], {}, {}
    sub_geo = {}   # grouped columns: (category index, series name) -> (x, width, top y) of each bar
    light = {C["main"]: C["light"], C["accent"]: C["light2"]}
    focus_colors = [set() for _ in series]
    from ._palette import _mix as _pmix
    multi = len(series) > 1
    used_cols = {str(col).lower() for _, _, col in series if col}
    for k_, v_ in list(light.items()):   # forecast tint must not equal another series' colour (legend identity)
        if str(v_).lower() in used_cols:
            light[k_] = _pmix(k_, "#FFFFFF", 0.5)
    greys = {str(C.get(k_, "")).lower() for k_ in ("py", "context", "dim", "sub", "ac_dim", "track")}
    for _, _, col in series:
        if col and col not in light and str(col).lower() not in greys:
            try:
                light[col] = _pmix(col, "#FFFFFF", 0.5)
            except (ValueError, TypeError, IndexError):
                pass

    def _dim_col(col):   # multi-series: dimming keeps the series hue (lighter), so legend identity survives
        try:
            return _pmix(col, "#FFFFFF", 0.62) if multi else C["dim"]
        except (ValueError, TypeError, IndexError):
            return C["dim"]
    dimmed_cols = set()
    # stacked columns: a focus that picks whole columns (focus="2025") must not fade the other columns' segments —
    # light segments faded again turn near-white and stop matching the legend; only a focus on some segments inside
    # a column (a series) fades the rest of that column
    col_focus, f_cache = set(), {}   # col_focus: columns with no focused segment (drawn as is, not faded)
    if stack and focus is not None:
        for i, cat in enumerate(categories):   # focus called once per (category, series), in drawing order
            for k, (nm, vals, _) in enumerate(series):
                f_cache[(i, k)] = bool(focus(cat, nm))
        hits = [[f_cache[(i, k)] for k, s_ in enumerate(series) if s_[1][i]] for i in range(n)]
        if any(any(h) for h in hits):
            col_focus = {i for i, h in enumerate(hits) if h and not any(h)}
    # a focus on single segments (one country's one channel) is outlined; a whole-series focus fades the other series
    # in every column and in the legend alike
    seg_focus = stack and focus is not None and multi and any(
        len({f_cache[(i, k)] for i in range(n) if series[k][1][i]}) > 1 for k in range(len(series)))
    if stack and not values and len(series) >= 2:
        print("columns：堆叠柱的段内数值是读数本身，已忽略 values=False（放不下的窄段自动不标）——"
              "要更少数字就减少分段（合并成'其他'）")
        values = True
    if stack:
        _flow_bands(ex, ax, bands, categories, series, flow, C)
    for i, ((bx, bw), cat) in enumerate(zip(bands, categories)):
        # several series: forecast bars keep each series' colour (the dashed 实绩/预测 divider marks the forecast) —
        # a lighter forecast tone stops matching the legend; a single series has no legend and keeps the light tone
        fc = forecast_from is not None and i >= forecast_from and not multi
        if stack:
            segs = []
            for series_index, (nm, vals, col) in enumerate(series):
                c = light.get(col, col) if fc else col
                # stacked: a focused segment is outlined (below); its column-mates keep the legend colours
                dimmed = focus is not None and i not in col_focus and not f_cache.get((i, series_index), True) and not seg_focus
                if dimmed:
                    c = _dim_col(col)
                    dimmed_cols.add(c)
                if vals[i]:
                    focus_colors[series_index].add(c if dimmed else None)
                segs.append((vals[i], c))
            ty = stacked_bar(ax, bx, bw, segs)
            if focus is not None and i not in col_focus and any(c_ not in dimmed_cols for _, c_ in segs):   # a focused column: its labels are marked
                ex.focus_marks = list(getattr(ex, "focus_marks", None) or []) + [(bx, ty, bx + bw, ax.sy(max(ax.ymin, 0)))]
            tops[cat] = tops[str(cat)] = ty
            acc = 0.0 if ax.ymin <= 0 else ax.ymin
            for (nm, vals, _), (v, _) in zip(series, segs):
                seg_y.setdefault(str(cat), {})[nm] = (ax.sy(acc + (v or 0)), ax.sy(acc))
                acc += v or 0
            if seg_focus and i not in col_focus:   # focused segment(s): dashed outline, colours kept
                for k_, (nm, vals, _) in enumerate(series):
                    if vals[i] and f_cache.get((i, k_)):
                        y_top, y_bot = seg_y[str(cat)][nm]
                        dashed_box(ex, bx - 2, y_top - 2, bx + bw + 2, y_bot + 2)
                        ex.focus_marks = list(getattr(ex, "focus_marks", None) or []) + [(bx, y_top, bx + bw, y_bot)]
            if values:
                base = 0.0
                for (nm, vals, col), (v, c) in zip(series, segs):
                    if v:
                        y0, y1 = ax.sy(base), ax.sy(base + v)
                        lab_ = f"{v:.0f}%" if stack == "percent" else value_fmt(v)
                        if abs(y0 - y1) > 13 and bw > frame_w(lab_, 10) + 1:   # the native frame must fit the segment
                            dark = c not in (C["light"], C["light2"], C["dim"], C["track"], C["context"]) and c not in dimmed_cols
                            ex.text(bx + bw / 2, (y0 + y1) / 2 + 3.6, (f"{v:.0f}%" if stack == "percent" else value_fmt(v)),
                                    size=10, fill="#FFFFFF" if dark else C["ink"], anchor="middle")
                        base += v
            if totals:   # with a column focus, the focused column's total is the bold one
                off = i in col_focus
                ex.text(bx + bw / 2, ty - 5, value_fmt(sum(s[1][i] or 0 for s in series)), size=10.5,
                        weight=400 if off else 700, fill=C["sub"] if off else C["ink"], anchor="middle")
        else:
            k = len(series)
            sub_w = bw / k
            ty = ax.sy(0)
            drawn = []
            for j, (nm, vals, col) in enumerate(series):   # all bars of the group first, then their labels: a bar
                v = vals[i]                                  # painted after a label covers it (server: shape covers text)
                if v is None:
                    continue
                c = light.get(col, col) if fc else col
                dimmed = focus is not None and not focus(cat, nm) and nm not in py_names
                if dimmed:
                    c = C.get("ac_dim", C["sub"]) if py_names else _dim_col(col)   # next to a light-grey PY: dark grey
                if v:
                    focus_colors[j].add(c if dimmed else None)
                sx0 = bx + j * sub_w + sub_w * group_gap / 2
                ww = sub_w * (1 - group_gap)
                y0, y1 = ax.sy(0), ax.sy(v)
                ax.s.rect(sx0, min(y0, y1), ww, abs(y0 - y1), c)
                if focus is not None and not dimmed:   # the highlighted bar(s): their labels count as marked
                    ex.focus_marks = list(getattr(ex, "focus_marks", None) or []) + [(sx0, min(y0, y1), sx0 + ww, max(y0, y1))]
                sub_geo[(i, str(nm))] = (sx0, ww, y1)
                drawn.append((sx0, ww, y1, v))
                ty = min(ty, y1)
            if values:
                fs = 10 if k > 1 else 10.5
                # tallest bars first; a label that would sit on a neighbour bar (its frame is wider than its own bar)
                # or on a label already placed is left out — the server reports both, and lifting labels over the
                # neighbours turns the group into an unreadable staircase
                for sx0, ww, y1, v in sorted(drawn, key=lambda d: d[2]):
                    lab_ = value_fmt(v)
                    cx_ = sx0 + ww / 2
                    half = frame_w(lab_, fs) / 2
                    # a negative bar's label goes below the bar — unless that runs into the category labels under a
                    # tight axis (small negatives), then it sits just above the zero line
                    y_ = (y1 - 5) if v >= 0 else (y1 + 13 if y1 + 13 + 4 < ax.sy(ax.ymin) else ax.sy(0) - 5)
                    box_ = (cx_ - half, y_ - 0.85 * fs, cx_ + half, y_ + 0.15 * fs)
                    on_bar = v >= 0 and any(sx1 < box_[2] and box_[0] < sx1 + ww1 and yt < box_[3]
                                            for sx1, ww1, yt, _ in drawn if sx1 != sx0)
                    on_lab = any(box_[0] < b_[2] and b_[0] < box_[2] and box_[1] < b_[3] and b_[1] < box_[3]
                                 for b_ in lab_boxes)
                    if on_bar or on_lab:
                        dropped_vals.append(lab_)
                        continue
                    lab_boxes.append(box_)
                    ex.text(cx_, y_, lab_, size=fs, fill=C["sub"] if fc else C["text"], anchor="middle")
            tops[cat] = tops[str(cat)] = ty
        centers.append(bx + bw / 2)
    if focus is not None and all(None not in fc and fc for fc in focus_colors if fc):   # focus= matched nothing
        raise ValueError("columns(focus=)：没有一根柱被选中，全部被淡化成灰——focus 写类目名（focus='2025'）、类目序号"
                         "（focus=5）、系列名，或 lambda c, s: c == '2025'；要突出的就是标题里的那根柱")
    ax.xlabels(centers, [str(c) for c in categories], width=label_width or (ax.w / n - 4), size=10.5)
    if data_rows:
        _draw_rows(ex, ax, centers, data_rows, box[3] + 6, left=box[0])
    if dropped_vals:
        print(f"columns：{len(dropped_vals)} 个数值标签比柱宽、会压到相邻柱/标签，已省略（如 {dropped_vals[:3]}）——"
              "要全部显示就加宽 Exhibit、减少系列，或 value_fmt 写短（如 1.9k）")
    split_at = None
    if forecast_from is None and _mixed_periods(categories):   # years then halves / quarters: partition the axis
        kinds_ = [_period_kind(c) == "Y" and not _SUB_YEAR.search(str(c)) for c in categories]
        if kinds_[0] and not kinds_[-1] and kinds_ == sorted(kinds_, reverse=True):
            split_at = kinds_.index(False)
    if split_at:
        dx = (bands[split_at - 1][0] + bands[split_at - 1][1] + bands[split_at][0]) / 2
        ex.line(dx, ax.y - 2, dx, ax.sy(ax.ymin), stroke=C["context"], width=0.8, dash="3,3", tag="ref")
        cjk = any(ord(ch) > 0x2E80 for ch in "".join(str(c) for c in categories) + ex.body_lang)
        sub = "半年" if any(_period_kind(c) == "H" for c in categories[split_at:]) else ("季度" if any(
            _period_kind(c) == "Q" for c in categories[split_at:]) else "年内累计")
        ex.text(dx - 6, ax.y + 10, "全年" if cjk else "Full year", size=10, fill=C["sub"], anchor="end")
        ex.text(dx + 6, ax.y + 10, sub if cjk else "Partial", size=10, fill=C["sub"])
    if forecast_from is not None and 0 < forecast_from < n:
        dx = (bands[forecast_from - 1][0] + bands[forecast_from - 1][1] + bands[forecast_from][0]) / 2
        ex.line(dx, ax.y - 2, dx, ax.sy(ax.ymin), stroke=C["context"], width=0.8, dash="3,3", tag="ref")
        cjk = any(ord(ch) > 0x2E80 for nm, _, _ in series for ch in nm) or any(ord(ch) > 0x2E80 for ch in ex.body_lang)
        ytd = all(re.search(r"YTD|1[-–~]\d+月|H1|1H|Q[1-3]|年初至今|前\d+月", str(c), re.I) for c in categories[forecast_from:])
        ex.text(dx - 6, ax.y + 10, "实绩" if cjk else "Actual", size=10, fill=C["sub"], anchor="end")
        ex.text(dx + 6, ax.y + 10, ("年内累计" if cjk else "YTD") if ytd else ("预测" if cjk else "Forecast"), size=10,
                fill=C["sub"])
        divider = dx
    else:
        divider = None
    if legend_items and len(series) > 1:
        items = [(nm, next(iter(colors)) if len(colors) == 1 and None not in colors else col, "square")
                 for (nm, _, col), colors in zip(series, focus_colors)]
        legend(ex, box[0], box[1] + 10, items, size=10.5)
    vals = [sum((s[1][i] or 0) for s in series) if stack else series[0][1][i] for i in range(n)]
    share_total = stack == "percent" or (stack and len(series) > 1 and all(abs(v - 100) <= 1.5 for v in vals if v))
    r = dict(ax=ax, centers=centers, tops=tops, bands=bands, values=vals, cats=[str(c) for c in categories],
             rows=[(nm_, list(vs_)) for nm_, vs_, _ in data_rows],
             divider=divider, segs=seg_y, rate_unit=is_rate_unit(unit) or stack == "percent", share_total=share_total,
             multiple=_sem.is_multiple(unit, *[s_[0] for s_ in series]),
             series_names=[] if stack else [str(s_[0]) for s_ in series],
             first_bars=({i_: sub_geo[(i_, str(series[0][0]))] for i_ in range(n) if (i_, str(series[0][0])) in sub_geo}
                         if not stack and len(series) > 1 else {}),   # grouped: CAGR is computed on series 0 — draw it there
             forecast=[forecast_from is not None and k >= forecast_from or _sem.is_forecast(c)
                       for k, c in enumerate(categories)])
    if _mixed_periods(categories) and not split_at:
        ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + [
            "年度与半年/季度混在同一根轴：读者会当成连续时间——年度与半年分成两个面板（或两组并留空隙），CAGR 只算完整年度"]))
    if target is not None:
        ax.ref_y(*target) if isinstance(target, (tuple, list)) else ax.ref_y(target)
        ex.notes += 1
    _cg = [cagr] if (isinstance(cagr, tuple)) else ([tuple(cagr)] if (isinstance(cagr, list) and cagr and isinstance(cagr[0], int)) else
                                                    [c_ for c_ in (cagr or []) if isinstance(c_, tuple)] if isinstance(cagr, list) else [])
    for k in ([yoy] if isinstance(yoy, int) else (yoy or [])):
        kk = min(k % n, n - 2) if n >= 2 else k   # yoy=last / -1 → the change into the last column
        if (kk, kk + 1) in _cg:   # the same span already carries a CAGR arrow: a second label on it only clutters
            continue
        if rate_ and vals[kk] is not None and vals[kk + 1] is not None:
            level_diff(ex, r, kk, text=pt_text(vals[kk + 1] - vals[kk], zh=bool(ex.body_lang)))
        else:
            level_diff(ex, r, kk)
    if cagr is False or cagr == []:   # turned off — unless the title states the rate, or nothing else annotates the chart
        from . import _frame as _fr
        if getattr(ex, "_panel", None) is None and all(x is None for x in (yoy, diff, target, delta)) and not flow \
                and not getattr(ex, "_no_auto_combo", 0) and ex.w >= 500 and not getattr(ex, "_auto", None):   # one full-width chart, not a panel of a multi-chart page
            cagr = None   # a bare yearly total with the arrow switched off shows no argument: draw it anyway
        elif re.search(_GROWTH_WORDS, (getattr(_fr, "LAST_TITLE", "") or "") + " " + (getattr(_fr, "LAST_SUBTITLE", "") or ""), re.I) and getattr(ex, "_panel", None) is None:
            cagr = None
    if cagr is None and not share_total and _auto_cagr(categories, series, stack, forecast_from, yoy, diff, target, delta, ex, unit=unit):
        nz = [i for i, v in enumerate(vals) if v]
        # the rates the title states pick the spans (e.g. "13.8% 2019–24, 16.0% to 2029" → two arrows); else first → last
        cagr = _title_spans(r) or [(nz[0], nz[-1])]
    if cagr is True:
        nz = [i for i, v in enumerate(vals) if v]
        cagr = _title_spans(r) or [(nz[0], nz[-1])]
    if cagr and isinstance(cagr[0], int):
        cagr = [tuple(cagr)]
    if cagr:
        if divider is not None:   # the arrow runs across the top: the 实绩 / 预测 tags go (light bars + divider remain)
            labs = {"实绩", "预测", "Actual", "Forecast"}
            ex.el = [e for e in ex.el if not (e.startswith("<text") and re.sub(r"<[^>]+>", "", e) in labs)]
            ex.reg = [g for g in ex.reg if not (g["kind"] == "text" and g["tag"] in labs)]
        for c_ in cagr:
            cagr_arrow(ex, r, *c_)
        r["_cagr_spans"] = [tuple(sorted((c_[0] % n, c_[1] % n))) for c_ in cagr]   # a later cagr_arrow on them: skipped
    if diff is not None and (n < 2 or diff[0] % n == diff[1] % n):
        print("diff 已忽略：只有一个类别或两端相同，没有可比较的差值")
        diff = None
    if diff is not None and len(diff) < 3 and tuple(sorted((diff[0] % n, diff[1] % n))) in (r.get("_cagr_spans") or []):
        # cagr and diff over the same two bars: the two brackets stack over the same span and say the same thing
        print("diff 已忽略：与 cagr= 是同一对柱（同一跨度画两个标注会叠在一起）——只留 CAGR；要强调倍数就写进标题或要点")
        diff = None
    if diff is not None:
        rd = r
        if diff_series is not None and not stack and len(series) >= 2:   # the named series' own bars and values
            k_s = [str(s_[0]) for s_ in series].index(str(diff_series))
            sv = list(series[k_s][1])
            g_ = {i_: sub_geo.get((i_, str(diff_series))) for i_ in range(n)}
            rd = dict(r, values=sv, bands=[(g_[i_][0], g_[i_][1]) if g_[i_] else r["bands"][i_] for i_ in range(n)],
                      tops={**r["tops"], **{r["cats"][i_]: g_[i_][2] for i_ in range(n) if g_[i_]}})
        dv = rd["values"]
        if rate_ and None not in (dv[diff[0] % n], dv[diff[1] % n]) and len(diff) < 3:
            i_, j_ = sorted((diff[0] % n, diff[1] % n))
            total_diff(ex, rd, i_, j_, text=pt_text(dv[j_] - dv[i_], zh=bool(ex.body_lang)))
        elif len(diff) < 3 and None not in (dv[diff[0] % n], dv[diff[1] % n]) and dv[diff[0] % n] \
                and all(_period_kind(r["cats"][k_]) is None and _year_of(r["cats"][k_]) is None for k_ in diff[:2]):
            # two objects, not two periods: a gap between them ("B 比 A 低 53%"), not a growth arrow
            a_, b_ = diff[0] % n, diff[1] % n
            g_ = dv[b_] / dv[a_] - 1
            zh_ = bool(ex.body_lang) or any(ord(ch) > 0x2E80 for ch in "".join(r["cats"]))
            word = ("高" if g_ > 0 else "低") if zh_ else ("above" if g_ > 0 else "below")
            lab_ = (f"{r['cats'][b_]}比{r['cats'][a_]}{word} {abs(g_) * 100:.0f}%" if zh_
                    else f"{r['cats'][b_]} {abs(g_) * 100:.0f}% {word} {r['cats'][a_]}")
            total_diff(ex, rd, *sorted((a_, b_)), text=lab_)
        else:
            total_diff(ex, rd, *diff)
    if delta is not None:
        r["deltas"] = series_delta(ex, r, series, *delta, fmt_=delta_fmt or (
            (lambda change: pt_text(change, zh=bool(ex.body_lang))) if rate_ else (
                lambda change: ("+" if change > 0 else ("−" if change < 0 else "±")) + value_fmt(abs(change)))),
            group_gap=group_gap, values=values)
    for nt in _note_list(note):
        cs = [str(c) for c in categories]
        if str(nt[0]) in cs:
            k = cs.index(str(nt[0]))
        elif isinstance(nt[0], int) and -n <= nt[0] < n:
            k = nt[0] % n
        else:
            raise ValueError(f"columns(note=)：{nt[0]!r} 既不是类目（{cs[:6]}…）也不是有效序号——写类目名，如 note=({cs[-1]!r}, '一句含义')")
        check_label_numbers(nt[1], _note_candidates(r, series, k, stack), f"columns(note=({nt[0]!r}, …))",
                            what=f"{categories[k]} 这根柱")
        from ._composite import speech_note
        ty = tops[str(categories[k])]
        if stack == "percent" or ty - (box[1] + leg_h) < 30:
            raise ValueError("columns(note=)：100% 堆叠/顶满的柱上方没有地方放说话框——改用 Note 列/右侧要点讲含义，"
                             "或给 Exhibit 留出上方空间（ymax=）")
        px_ = centers[k]
        ends = {c_[1] for c_ in (cagr or []) if isinstance(c_, tuple)} | ({k_ + 1 for k_ in ([yoy] if isinstance(yoy, int)
                                                                                    else (yoy or []))} if yoy is not None else set())
        starts = {c_[0] for c_ in (cagr or []) if isinstance(c_, tuple)}
        bw_ = bands[k][1]
        if k in ends or k in starts:   # an arrow already lands on the bar centre: point at the bar's free side,
            px_ += bw_ * (0.3 if k in ends else -0.3)   # above its value label (the tail must not run through it)
            for e in ex.reg:
                if e["kind"] == "text" and e["box"][0] - 2 <= centers[k] <= e["box"][2] + 2 and e["box"][3] <= ty + 2 \
                        and e["box"][1] >= ty - 24:
                    ty = min(ty, e["box"][1] - 3)
        speech_note(ex, (px_, ty), nt[1])
    if stack != "percent" and min_v >= 0 and not data_rows:   # plain columns may become an editable chart on a multi-chart page
        from ._autonative import record
        orig = {nm: vals for nm, vals, _ in series}
        record(ex, "columns", box, _start, _notes0, categories, [(nm, list(orig[nm])) for nm, _, _ in series],
               [col for _, _, col in series], focus=focus, forecast_from=forecast_from, stack=stack, values=values,
               grid=show_grid)
    if stack != "percent":
        _columns_facts(ex, categories, series)
        seqs = [list(vals)] + [list(s_[1]) for s_ in series] if stack else [list(s_[1]) for s_ in series]
        ex._cagr_charts = list(getattr(ex, "_cagr_charts", None) or []) + [([str(c) for c in categories], seqs)]
    from ._page import add_fact
    add_fact(ex, {"kind": "chart", "fn": "columns", "cats": [str(c) for c in categories], "stack": stack,
                  "series": [(str(nm), list(vs)) for nm, vs, *_ in series]})   # for the "no annotation" refusal's suggestion
    return r


ROW_H = 20   # canvas units per data row under a chart axis


def _check_rows(rows, categories, where):
    """Normalise rows= for a data strip under a category axis: [(name, values, fmt)], one value per category."""
    if not rows:
        return []
    if isinstance(rows, tuple) and len(rows) in (2, 3) and isinstance(rows[0], str):
        rows = [rows]
    out = []
    for r in rows:
        if not isinstance(r, (tuple, list)) or len(r) not in (2, 3) or not isinstance(r[0], str):
            raise ValueError(f"{where}(rows=)：每行写 (行名, [每个类目一个值]) 或 (行名, 值列表, fmt)，如 "
                             "rows=[('利润率', [12.1, 13.4, 15.0], lambda v: f'{v:.1f}%')]")
        vals = list(r[1])
        if len(vals) != len(categories):
            raise ValueError(f"{where}(rows=)：行 {r[0]!r} 有 {len(vals)} 个值，类目有 {len(categories)} 个——一个类目一个值，缺的写 None")
        f_ = r[2] if len(r) > 2 and callable(r[2]) else (lambda v: fmt(v))
        out.append((r[0], vals, f_))
    if len(out) > 2:
        raise ValueError(f"{where}(rows=)：最多 2 行（第三个指标另起一张图或写进右栏）")
    return out


def _draw_rows(ex, ax, centers, data_rows, y0, left=None):
    """1–2 rows of numbers aligned under the category centres: light band, row name left of the plot area."""
    from ._page import add_fact
    C = ex.C
    x_l = ax.x if left is None else left
    for k, (name, vals, f_) in enumerate(data_rows):
        ry = y0 + k * ROW_H
        ex.rect(x_l, ry, ax.x + ax.w - x_l, ROW_H - 3, C.get("band", "#F2F2F2"), register=False)
        ex.text(x_l + 3, ry + ROW_H / 2 + 2.6, name, size=10, weight=700, fill=C["ink"])
        for cx, v in zip(centers, vals):
            ex.text(cx, ry + ROW_H / 2 + 2.6, "—" if v is None else f_(v), size=10, fill=C["text"], anchor="middle")
        add_fact(ex, {"kind": "row", "name": str(name), "values": list(vals)})
    ex.data_rows = getattr(ex, "data_rows", 0) + len(data_rows)


def _fixed_sum_guard(categories, series, stack, yoy, diff, cagr):
    """A 100 % stack, or a stack whose per-period totals are constant (shares that sum to 100, a fixed pool): the
    total never changes, so yoy= / diff= / cagr= on it print "+0%" — raise with the per-series pt change instead."""
    if not stack or len(series) < 2 or all(x in (None, False, []) for x in (yoy, diff, cagr)):
        return
    n = len(categories)
    tots = [sum((s_[1][i] or 0) for s_ in series) for i in range(n)]
    nz = [t for t in tots if t]
    fixed = stack == "percent" or (len(nz) >= 2 and max(nz) - min(nz) <= 0.005 * max(abs(t) for t in nz))
    if not fixed:
        return
    shares = [[((s_[1][i] or 0) / tots[i] * 100 if tots[i] else None) for i in range(n)] for s_ in series]
    i0, i1 = 0, n - 1
    moves = [(abs((sh[i1] or 0) - (sh[i0] or 0)), k) for k, sh in enumerate(shares)
             if sh[i0] is not None and sh[i1] is not None]
    k = max(moves, key=lambda m: (round(m[0], 6), -m[1]))[1] if moves else 0   # largest move; first series on a tie
    d = (shares[k][i1] or 0) - (shares[k][i0] or 0)
    what = "yoy=" if yoy not in (None, False, []) else ("diff=" if diff is not None else "cagr=")
    raise ValueError(f"columns(stack={stack!r})：各期合计固定（{'100%' if stack == 'percent' else fmt(nz[0])}），{what} 对合计算出来恒为 "
                     f"+0%——构成图只讲某一个系列的百分点变化（±x pt on a single series）：如「{series[k][0]}」"
                     f"{categories[i0]}→{categories[i1]} {('+' if d >= 0 else '−') + f'{abs(d):.1f}'}pt，写成 columns(ex, box, cats, [('{series[k][0]}', 占比)], unit='%', "
                     "diff=(i, j))，或堆叠图上不加 yoy/diff/cagr、在小标题里写这句")


def _columns_facts(ex, categories, series):
    """What the title check needs from a column chart: growth per category (two period series, e.g. 2024 vs 2025)
    or per series (period categories, several series), and each series over period categories."""
    from ._page import add_fact, growth_items, is_period, _PERIOD_NAME_RE
    cats = [str(c) for c in categories]
    periods = len(cats) >= 2 and all(is_period(c) for c in cats)
    if len(series) == 2 and len(cats) >= 2 and not periods and all(_PERIOD_NAME_RE.search(str(s_[0])) for s_ in series):
        from ._kpi import ac_minus_ref_order
        s0, s1 = (series[1], series[0]) if ac_minus_ref_order(str(series[0][0]), str(series[1][0])) < 0 else series
        g = growth_items(cats, s0[1], s1[1])   # reference → actual, whichever order the series came in
        if len(g) >= 2:
            add_fact(ex, {"kind": "growth", "items": g})
    if periods and len(series) >= 2:
        firsts = [next((v for v in s_[1] if v is not None), None) for s_ in series]
        lasts = [next((v for v in reversed(s_[1]) if v is not None), None) for s_ in series]
        g = growth_items([s_[0] for s_ in series], firsts, lasts)
        if len(g) >= 2:
            add_fact(ex, {"kind": "growth", "items": g})
    if periods and len(cats) >= 3:
        for s_ in series:
            add_fact(ex, {"kind": "series", "name": str(s_[0]), "values": list(s_[1]), "periods": cats})


_LABEL_NUM = re.compile(r"(?<![\w.])([+\-−]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(%|％|pt|pp|个百分点|x|×|倍)?", re.I)


def label_numbers(text):
    """Numbers in a hand-written label that claim a computed value: decimals (26.3) and rates / multiples (8%, 5pt,
    2.1x). Plain integers (counts like "9 家", "前 5", ranges like 2019–25) and years are not claims."""
    out = []
    for m in _LABEL_NUM.finditer(str(text or "")):
        raw, unit = m.group(1).replace(",", "").replace("−", "-"), (m.group(2) or "")
        if not unit and "." not in raw:
            continue
        if re.fullmatch(r"-?(?:19|20)\d{2}", raw.lstrip("+")):
            continue
        dec = len(raw.split(".")[1]) if "." in raw else 0
        out.append((abs(float(raw)), dec, unit, m.group(0).strip()))
    return out


def check_label_numbers(text, candidates, where, what="所标对象"):
    """ValueError when a number in `text` matches none of the program-computed `candidates` within its own rounding
    (a share may be given as a fraction: 0.268 ↔ 26.8%). The message shows the computed values to write instead."""
    cands = [abs(c) for c in candidates if isinstance(c, (int, float)) and c == c]
    if not cands:
        return
    for v, dec, unit, shown in label_numbers(text):
        tol = 0.5 * 10 ** -dec + 1e-9
        pool = cands + ([c * 100 for c in cands] if unit in ("%", "％", "pt", "pp", "个百分点") or dec else [])
        if any(abs(c - v) <= tol for c in pool):
            continue
        near = sorted(pool, key=lambda c: abs(c - v))[:3]
        raise ValueError(f"{where}：标签里的「{shown}」和数据算出来的对不上——{what}按数据是 "
                         f"{'、'.join(fmt(round(c, max(dec, 1))) for c in near)}。数字由程序算出再写进标签"
                         "（f-string 从数据拼），或删掉这个数；分母/对象不同就改指向")


def _note_candidates(r, series, k, stack):
    """Values a note on column k may cite: its bar values and stack total, change vs neighbours (absolute / %),
    CAGR from / to it, its share of the stack and of the series total."""
    n = len(r["values"])
    out = []
    for s_ in series:
        vs = list(s_[1])
        v = vs[k]
        if v is None:
            continue
        out.append(v)
        for j in (k - 1, k + 1):
            if 0 <= j < n and vs[j] is not None:
                out += [v - vs[j]] + ([v / vs[j] - 1, v / vs[j]] if vs[j] else [])
        tot = sum(x for x in vs if x is not None)
        if tot:
            out.append(v / tot)
        if stack:
            st = sum((s2[1][k] or 0) for s2 in series)
            if st:
                out.append(v / st)
        for i_ in range(n):   # CAGR / change over any span that ends or starts at k
            if i_ == k or vs[i_] is None:
                continue
            a, b = sorted((i_, k))
            rr = dict(r, values=vs)
            g, _ = _cagr_of(rr, a, b)
            if g is not None:
                out.append(g)
            if vs[a]:
                out += [vs[b] / vs[a] - 1, vs[b] - vs[a]]
    tv = r["values"][k]
    if tv is not None:
        out.append(tv)
    return out


_RANGE_SEG = re.compile(r"区间|上限|下限|低限|高限|上沿|下沿|\b(?:low|high|lower|upper|min|max|range|bound)s?\b", re.I)


def _range_stack_hint(ex, names):
    """Stack segments named like bounds (低限 + 区间, low / high): a stacked column reads as 0 → top, not lo → hi."""
    hit = [str(n_) for n_ in names if _RANGE_SEG.search(str(n_))]
    if not hit:
        return
    msg = (f"堆叠分段 {hit} 像区间上下限：堆叠柱读成 0→顶的总量，区间色会被读成整根柱——区间（低值–高值）改用 "
           "row_table 的 Range(lo, hi, point=) 列或 dot_range(rows=[dict(label, value, lo, hi)])，或画两根并列柱")
    print(f"columns 提醒：{msg}")
    ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + [msg]))


def _sign_fix(t):
    return re.sub(r"^\+\s*[-−]", "−", re.sub(r"^\+\+", "+", str(t)))


def _note_list(note):
    if not note:
        return []
    return [note] if isinstance(note, tuple) and len(note) == 2 and isinstance(note[1], str) else list(note)


_GROWTH_WORDS = r"CAGR|年均|复合|年化|annual(?:ly)?|a year|per year|/yr|p\.a\.|per annum|yoy growth"


def _auto_cagr(categories, series, stack, forecast_from, yoy, diff, target, delta, ex, unit=None):
    """columns() without cagr=: draw one when the chart is a yearly series (≥4 periods like 2021 / FY24 / 2026E) of a
    single total (one series, or an absolute stack), first and last values present and positive, and no other
    annotation was asked for. cagr=False turns it off."""
    from . import _frame
    from ._kpi import is_rate_unit
    from ._semantics import is_multiple
    if is_rate_unit(unit) or is_multiple(unit, *[s_[0] for s_ in series]):
        return False
    names = " ".join([str(unit or "")] + [str(s_[0]) for s_ in series])
    if re.search(r"天|日\b|days?\b|周转|turnover|DSO|DIO|DPO|月数|months?\b|率|ratio|倍数|multiple|score|评分|指数|index", names, re.I):
        return False   # durations, ratios and scores: a compound growth rate of them means nothing
    title = (getattr(_frame, "LAST_TITLE", "") or "") + " " + (getattr(_frame, "LAST_SUBTITLE", "") or "")
    said = bool(re.search(_GROWTH_WORDS, title, re.I))   # the title states a growth rate
    # other annotations only stand in for the arrow when the title does not itself state the growth rate
    if stack == "percent" or (not said and any(x is not None for x in (yoy, diff, target, delta))):
        return False
    if len(categories) < (2 if said else 4) or not all(
            re.fullmatch(r"(?:FY|CY)?'?(?:19|20)?\d{2}[EFAPB]?(?:年[EF]?|E年)?", str(c).strip()) for c in categories):
        return False
    if len(series) > 1 and not stack:
        return False
    tot = [sum((s_[1][i] or 0) for s_ in series) if stack else series[0][1][i] for i in range(len(categories))]
    nz = [i for i, v in enumerate(tot) if v]
    if not (len(nz) >= (2 if said else 4) and tot[nz[0]] > 0 and tot[nz[-1]] > 0):
        return False
    # a series that peaked and turned down ("利润掉头向下") gets no automatic CAGR arrow: the title's growth word is
    # usually about a sibling panel; pass cagr=(i, j) explicitly when the arrow is really meant
    peak = max(tot[i] for i in nz)
    turned = tot[nz[-1]] < 0.98 * peak and peak > tot[nz[0]] * 1.02   # rose to a peak, then fell back
    return not turned


def series_delta(ex, r, series, a, b, cats=None, fmt_=None, group_gap=0.12, values=True):
    """(Via columns(..., delta=(a, b[, cats]))) In a grouped column chart, bracket bars a and b of each category and
    write the difference above the pair (computed): always actual − reference — series b − series a unless the series
    names say a is the actual and b the reference (AC / 实际 / 本期 vs 去年 / 预算 / PY / an earlier period), then a − b.
    Returns {category: difference}."""
    if r.get("segs"):
        raise ValueError("delta= 只用于分组柱（stack=None）；堆积柱请用 diff=/yoy= 比较类别")
    k = len(series)
    if not (0 <= a < k and 0 <= b < k) or a == b:
        raise ValueError(f"delta=({a}, {b})：需两个不同的系列下标（共 {k} 个系列）")
    from ._semantics import noncomparable_guard
    noncomparable_guard(ex, "系列差值（delta=）")
    ex.notes += 1
    ax = r["ax"]
    fmt_ = fmt_ or (lambda d: f"{d:+.1f}")
    out = {}
    from ._kpi import ac_minus_ref_order
    ya, yb = (re.search(r"(?:19|20)\d{2}", str(series[x][0])) for x in (a, b))
    if ya and yb and ya.group(0) != yb.group(0):   # "2025 实际" vs "2026 目标": a change over time — later − earlier
        flip = int(ya.group(0)) > int(yb.group(0))
    else:
        flip = ac_minus_ref_order(str(series[a][0]), str(series[b][0])) < 0   # ("AC", "去年") passed as (0, 1): AC − PY
    idx = range(len(r["cats"])) if cats is None else ([cats] if isinstance(cats, int) else cats)
    for i in idx:
        va, vb = series[a][1][i], series[b][1][i]
        if va is None or vb is None:
            continue
        bx, bw = r["bands"][i]
        sub = bw / k
        xa = bx + a * sub + sub / 2
        xb = bx + b * sub + sub / 2
        top = min(ax.sy(max(va, 0)), ax.sy(max(vb, 0))) - (16 if values else 4)
        y = top - 4
        lo, hi = min(xa, xb), max(xa, xb)
        pts = [(lo, y + 4), (lo, y), (hi, y), (hi, y + 4)]
        ex.path("M" + " L".join(f"{p:.1f},{q:.1f}" for p, q in pts), stroke=ex.C["text"], width=0.9, pts=pts)
        d = (va - vb) if flip else (vb - va)
        out[r["cats"][i]] = d
        ex.text((lo + hi) / 2, y - 4, _sign_fix(fmt_(d)), size=10.5, weight=700,
                fill=ex.C["neg"] if d < 0 else ex.C["accent"], anchor="middle")
    return out


_BRIDGE_RESIDUAL = re.compile(r"^\s*(?:其他|其它|other|others|轧差|残差|差额)(?:\s*[（(][^）)]*[）)])?\s*$", re.I)
RESIDUAL_SHARE = 0.30   # a residual step above this share of the largest named step hides a driver


def _bridge_residual(ex, deltas, value_fmt=lambda v: fmt(v)):
    """Record "轧差项'其他'过大" in ex.extra_issues (ex.check() reports it, publish holds the page) when a residual step
    (其他 / 其它 / other / 轧差 / 残差, incl. '其他（轧差）') exceeds RESIDUAL_SHARE of the largest named step."""
    named = [abs(v) for lab, v in deltas if v and not _BRIDGE_RESIDUAL.match(lab)]
    if not named:
        return []
    top = max(named)
    found = []
    for lab, v in deltas:
        if v and _BRIDGE_RESIDUAL.match(lab) and abs(v) > RESIDUAL_SHARE * top:
            vv = ("+" if v > 0 else "−") + str(value_fmt(abs(v))).lstrip("+−-± ")
            found.append(f"轧差项'{lab.strip()}'过大（{vv}）：拆出主要构成（如非经常性损益）或标'其他（轧差）'")
    if found:
        ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + found))
    return found


def _bridge_plug(ex, steps, value_fmt=lambda v: fmt(v)):
    """Record "两步金额正负相等" in ex.extra_issues when two delta steps have exactly equal absolute values with opposite
    signs and |value| ≥ 1 % of the start (e.g. +618 vs −618 — a plug that forces the bridge
    to close). Values with a single significant digit (3 / −3 bp, 10 / −10) coincide too often to mean anything and
    are skipped."""
    def sig(v):
        return len(f"{abs(v):.6g}".replace(".", "").replace("e", "").strip("0").split("+")[0])
    totals = [abs(st[2]) for st in steps if st[0] == "total"]
    base = totals[0] if totals else max([abs(st[2]) for st in steps] + [0])
    ds = [float(st[2]) for st in steps if st[0] == "delta"]
    found = []
    for i, a in enumerate(ds):
        for b in ds[i + 1:]:
            if a * b < 0 and abs(abs(a) - abs(b)) <= 1e-9 * max(abs(a), 1) and abs(a) >= 0.01 * base and abs(a) > 0 \
                    and sig(a) >= 2:
                found.append(f"两步金额正负相等（±{str(value_fmt(abs(a))).lstrip('+−-± ')}）：疑似凑平项，核对口径")
    if found:
        ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + found))
    return found


def _bridge_colors(steps, focus):
    """Per-step own colours (4th item) are honoured only when every delta step has one, or for the focus step(s);
    a partial mix (one red decline, the next grey) falls back to the up / down role colours."""
    deltas = [st for st in steps if st[0] == "delta"]
    if deltas and all(st[3] for st in deltas):
        up = [str(st[3]).upper() for st in deltas if st[2] >= 0]
        dn = [str(st[3]).upper() for st in deltas if st[2] < 0]

        def grey(c):
            try:
                r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
            except (ValueError, IndexError):
                return False
            return max(r, g, b) - min(r, g, b) < 18
        # a grey next to a coloured step of the same direction (研发 grey, 毛利 red) is a half-highlight, not a scheme
        half = any(len(set(cs)) > 1 and any(grey(c) for c in cs) for cs in (up, dn))
        if not half and (len(set(up) | set(dn)) == len(deltas) or not (set(up) & set(dn))):
            return steps   # one colour per initiative, or one colour per direction
    keys = set() if focus is None else ({focus} if isinstance(focus, str) else set(focus))
    return [st if (st[0] != "delta" or str(st[1]) in keys) else st[:3] + (None,) for st in steps]


_PY_NAME = re.compile(r"去年|上年|同期|前一?年|\b(?:PY|LY|prior year|last year|previous year)\b", re.I)
_GREY_PY_TEXT = re.compile(r"(?:浅灰|灰色?)[^，,。；;]{0,4}(?:为|是|=|：|:)?\s*(?:去年|上年|同期|PY)|(?:去年|上年|同期|PY)[^，,。；;]{0,4}(?:为|用|=|：|:)?\s*(?:浅灰|灰)"
                           r"|grey\s*(?:=|is|for)?\s*(?:PY|prior|last year)", re.I)


def _is_py_name(nm):
    """A previous-year series by its name (去年 / 同期 / PY / last year) — not 预算 / 目标 (those are PL)."""
    from ._kpi import _AC_WORDS
    t = str(nm or "")
    return bool(_PY_NAME.search(t)) and not _AC_WORDS.search(t) and not re.search(r"预算|目标|计划|budget|target|plan", t, re.I)


def _py_series_grey(ex, series):
    """IBCS: a previous-year series is light grey. Series named 去年 / 同期 / PY whose colour is not a light neutral
    (lightness < 80 % or tinted) — or any PY series on a page whose subtitle says "浅灰为去年" — are drawn in the
    palette's py grey (otherwise the subtitle says light grey = last year over green bars).
    Returns (series, names of the PY series)."""
    import colorsys
    from . import _frame
    C = ex.C
    said = bool(_GREY_PY_TEXT.search((getattr(_frame, "LAST_SUBTITLE", "") or "") + " " + (getattr(_frame, "LAST_TITLE", "") or "")))
    out, names = [], set()
    for nm, vals, col in series:
        if len(series) >= 2 and _is_py_name(nm):
            names.add(nm)
            try:
                r_, g_, b_ = (int(col[i:i + 2], 16) / 255 for i in (1, 3, 5))
                _, l_, s_ = colorsys.rgb_to_hls(r_, g_, b_)
                light_neutral = l_ >= 0.8 and (s_ <= 0.15 or max(r_, g_, b_) - min(r_, g_, b_) < 0.08)
            except (ValueError, TypeError, IndexError):
                light_neutral = False
            if said or not light_neutral:
                col = C["py"]
        out.append((nm, vals, col))
    return out, names


def _bridge_value(value, value_fmt):
    body = str(value_fmt(abs(value))).lstrip("+−-±＋－﹢﹣ ")
    body = re.sub(r"^(\D*?)(?:[+−\-±＋－﹢﹣]\s*)+(?=\d|\.\d)", r"\1", body)
    return ("+" if value >= 0 else "−") + body


def waterfall(ax, centers, bw, steps, colors=None, values=True, value_fmt=lambda v: fmt(v), share=False,
              truncated_ok=False, focus=None):
    """Bridge: steps [("total"|"delta", label, value[, color])]; increases use the "up" colour, declines the contrast
    colour neg — the same colour for every step of one direction. A 4th item colours a delta bar only when every delta
    step has one (e.g. one colour per initiative) or the step is named in focus= (label or labels); a partial mix of own
    colours is dropped. Totals must equal start + deltas (raises otherwise); two steps of exactly equal size and
    opposite sign are reported by check() as a likely plug. Dashed connectors. share=True adds each delta's share of the
    net change under its value ("占 42%"). Returns top y per step."""
    C = ax.s.C
    colors = colors or {"total": C["main"], "up": C["accent"], "down": C["neg"]}
    run, tops, prev = 0.0, [], None
    steps = [tuple(st) + (None,) * (4 - len(st)) for st in steps]
    steps = _bridge_colors(steps, focus)
    _bridge_plug(ax.s, steps, value_fmt)
    net = sum(st[2] for st in steps if st[0] == "delta") or None
    ds = [st[2] for st in steps if st[0] == "delta"]
    if share and ds and min(ds) < 0 < max(ds):   # mixed signs: "占 324% / −249%" of the net change reads as nonsense
        share = "gross"
    zh = any(ord(ch) > 0x2E80 for st in steps for ch in str(st[1]))   # follow the step labels
    from ._page import FACTS
    fact = {"kind": "bridge", "items": [(str(st[1]), float(st[2])) for st in steps if st[0] == "delta"]}
    FACTS.append(fact)
    ax.s.__dict__.setdefault("facts", []).append(fact)   # f.publish(ex=…) reads the exhibit's own facts
    _bridge_residual(ax.s, [(str(st[1]), st[2]) for st in steps if st[0] == "delta"], value_fmt)
    for i, ((kind, lab, v, own), cx) in enumerate(zip(steps, centers)):
        if kind == "total":
            if i > 0 and abs(v - run) > 0.005 * max(abs(v), 1):
                raise ValueError(f"waterfall: '{lab}' = {v} 但起点加各项 = {run:.4g}；桥不闭合，补上缺的项或改数")
            if ax.ymin > 0 and i == 0 and not truncated_ok:   # truncated axis (ibcs_bridge marks it: allowed there): a total drawn from ymin exaggerates every step
                raise ValueError(f"waterfall: 纵轴从 {ax.ymin:g} 起（截断）——总量柱默认从 0 起，Axes 的 ymin 改为 0；"
                                 "增量只有总量几个百分点时用 ibcs_bridge（自动标截断），或按 variance_bridge 配方传 "
                                 "truncated_ok=True 并用 scale_marker 标出底线")
            base0 = min(max(0.0, ax.ymin), ax.ymax)
            lo, hi, run = (base0, v, v) if v >= base0 else (v, base0, v)   # totals start at 0 (negative ones hang below)
            color = colors["total"]
        else:
            lo, hi = (run, run + v) if v >= 0 else (run + v, run)
            run += v
            color = colors["up"] if v >= 0 else colors["down"]
        color = own or color
        ax.s.rect(cx - bw / 2, ax.sy(hi), bw, ax.sy(lo) - ax.sy(hi), color)
        if prev is not None:
            px, level = prev
            ax.s.line(px, ax.sy(level), cx - bw / 2, ax.sy(level), stroke=C["context"], width=0.7, dash="2,2", tag="grid")
        prev = (cx + bw / 2, run)
        tops.append(ax.sy(hi))
        if values:
            txt = value_fmt(v) if kind == "total" else _bridge_value(v, value_fmt)
            ax.s.text(cx, ax.sy(hi) - 5, txt, size=10.5, weight=700 if kind == "delta" else 400, anchor="middle",
                      fill=C["ink"])
            if share and kind == "delta" and net:
                same = [d for d in ds if (d >= 0) == (v >= 0)]
                base = sum(same) if share == "gross" else net   # mixed: share among same-direction drivers
                lab_ = (f"占增量 {v / base:.0%}" if v >= 0 else f"占减量 {v / base:.0%}") if share == "gross" else f"占 {v / net:.0%}"
                ax.s.text(cx, ax.sy(hi) - 19, (lab_ if zh else f"{v / base:.0%}"), size=10,
                          fill=C["sub"], anchor="middle")
    if share and net:
        ax.s.notes += 1
    return tops


# ===================================================================================== composition


def hstack100(ex, x, y, w, h, segs, label_size=10.5, min_inside=34):
    """100% horizontal composition bar. segs [(label, share, color, text_color)]; narrow segments get tiered external
    labels. Returns x-ranges of segments."""
    total = sum(s[1] for s in segs)
    if all(0 <= s[1] <= 100 for s in segs) and 102 < total < 300:
        raise ValueError(f"hstack100：各段合计 {total:g}%（>100%）——构成的各部分要互斥、同一分母、加总 100%；"
                         "不是同一分母的占比（各自占不同总体）改用条形图逐项比较")
    cx, spans, last_out, tier = x, [], -1e9, 0
    for lab, v, color, tc in segs:
        sw = v / total * w
        ex.rect(cx, y, sw, h, color, stroke="#FFFFFF", stroke_width=1, register=False)
        ex.occupy((cx, y, cx + sw, y + h), "mark", "panel-bg")
        val = f"{v:.0f}%" if v >= 10 else f"{v:.1f}%"
        has_pct = "%" in str(lab)   # label already carries the share: don't print it twice
        if sw >= min_inside:
            if has_pct:
                ex.text(cx + sw / 2, y + h / 2 + label_size / 2 - 1, lab, size=label_size + 1, weight=700, fill=tc, anchor="middle")
            else:
                ex.text(cx + sw / 2, y + h / 2 - 1, val, size=label_size + 1, weight=700, fill=tc, anchor="middle")
                ex.text(cx + sw / 2, y + h / 2 + label_size + 1, lab, size=label_size - 1, fill=tc, anchor="middle")
        else:
            txt = lab if has_pct else f"{lab} {val}"
            ls = max(label_size - 1, 10)
            tw_ = tw(txt, ls) + 1
            mid = cx + sw / 2
            lx0 = min(max(mid - tw_ / 2, x), x + w - tw_)   # keep the label over the bar, never past its ends
            tier = tier + 1 if lx0 < last_out + 6 else 0
            ly = y - 10 - tier * (ls + 3)
            ex.line(mid, y, mid, ly + 3, stroke=ex.C["context"], width=0.7, tag="leader")
            ex.text(lx0, ly, txt, size=ls, anchor="start")
            last_out = lx0 + tw_
        spans.append((cx, cx + sw))
        cx += sw
    return spans


def vstack100(ex, x, y, w, h, segs, size=10.5, title=None):
    """Vertical 100% composition column (sidebar). segs bottom-up [(label, share, color, text_color)];
    title: str or [(text, weight)] (wrapped to the panel width)."""
    if title:
        limit = (ex._panel[2] if ex._panel else ex.w - ex.m) - x
        rows = title if isinstance(title, list) else [(title, 700)]
        lines = []
        for t, wgt in rows:
            lines += [(ln, wgt) for ln in wrap(t, 11, limit, wgt >= 600)]
        for i, (t, wgt) in enumerate(lines):
            ex.text(x, y + 11 + i * 13.5, t, size=11, weight=wgt, fill=ex.C["ink"])
        y += len(lines) * 13.5 + 14
        h -= len(lines) * 13.5 + 14
    total = sum(s[1] for s in segs)
    cy = y + h
    for lab, v, col, tc in segs:
        sh = v / total * h
        ex.rect(x, cy - sh, w, sh, col, register=False)
        ex.occupy((x, cy - sh, x + w, cy), "mark", "panel-bg")
        ex.text(x + w / 2, cy - sh / 2 + 4, f"{v:g}", size=size + 0.5, weight=700, fill=tc, anchor="middle")
        ex.line(x + w + 2, cy - sh / 2, x + w + 12, cy - sh / 2, stroke=ex.C["context"], width=0.6, tag="leader")
        for j, ln in enumerate(lab.split("\n")):
            ex.text(x + w + 16, cy - sh / 2 + 4 + j * 13, ln, size=size)
        cy -= sh


def dot_waffle(ex, x, y, w, value, n_cols=10, n_rows=10, on=None, off=None, gap_ratio=0.22):
    """10×10 dot waffle filled bottom-up (percent of a group). Returns (x, y, w, h)."""
    step = w / n_cols
    r = step * (1 - gap_ratio) / 2
    k = round(value)
    for i in range(n_cols * n_rows):
        row, col = divmod(i, n_cols)
        cy = y + (n_rows - 1 - row) * step + step / 2
        ex.circle(x + col * step + step / 2, cy, r, (on or ex.C["accent"]) if i < k else (off or "#CCCCCC"),
                  register=False)
    ex.occupy((x, y, x + w, y + step * n_rows), "mark", "panel-bg")
    return x, y, w, step * n_rows


def venn3(ex, cx0, cy0, areas, total, colors, labels=True, R=None):
    """Area-proportional 3-set Venn inside a universe circle. areas: exclusive regions A,B,C,AB,AC,BC,ABC.
    colors: dict A,B,C,AB,AC,BC,ABC. Returns (P centres, r radii, R_all)."""
    import itertools  # noqa: F401
    R_all = R or 150
    scale = math.pi * R_all * R_all / total
    ex.circle(cx0, cy0, R_all, "#EBEBEB", register=False)
    A = areas["A"] + areas["AB"] + areas["AC"] + areas["ABC"]
    B = areas["B"] + areas["AB"] + areas["BC"] + areas["ABC"]
    Cc = areas["C"] + areas["AC"] + areas["BC"] + areas["ABC"]
    r = {k: math.sqrt(v * scale / math.pi) for k, v in (("A", A), ("B", B), ("C", Cc))}

    def lens(r1, r2, d):
        if d >= r1 + r2:
            return 0.0
        if d <= abs(r1 - r2):
            return math.pi * min(r1, r2) ** 2
        a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
        a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
        return a1 + a2 - 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))

    def solve(r1, r2, target):
        lo, hi = abs(r1 - r2) + 1e-6, r1 + r2
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if lens(r1, r2, mid) > target else (lo, mid)
        return (lo + hi) / 2

    dAB = solve(r["A"], r["B"], (areas["AB"] + areas["ABC"]) * scale)
    dAC = solve(r["A"], r["C"], (areas["AC"] + areas["ABC"]) * scale)
    dBC = solve(r["B"], r["C"], (areas["BC"] + areas["ABC"]) * scale)
    ang = math.radians(48)
    Bp = (dAB * math.cos(ang), dAB * math.sin(ang))
    a = (dAC ** 2 - dBC ** 2 + dAB ** 2) / (2 * dAB)
    h = math.sqrt(max(dAC ** 2 - a ** 2, 0))
    mx, my = a * Bp[0] / dAB, a * Bp[1] / dAB
    cands = [(mx + h * Bp[1] / dAB, my - h * Bp[0] / dAB), (mx - h * Bp[1] / dAB, my + h * Bp[0] / dAB)]
    Cp = min(cands, key=lambda p: p[0] - p[1])
    raw = {"A": (0.0, 0.0), "B": Bp, "C": Cp}
    xs = [raw[k][0] - r[k] for k in "ABC"] + [raw[k][0] + r[k] for k in "ABC"]
    ys = [raw[k][1] - r[k] for k in "ABC"] + [raw[k][1] + r[k] for k in "ABC"]
    ox, oy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    P = {k: (cx0 + v[0] - ox, cy0 + v[1] - oy) for k, v in raw.items()}
    for k in "ABC":
        ex.circle(*P[k], r[k], colors[k], register=False)
    uid = f"v{len(ex.el)}"
    ex.add("<defs>" + "".join(f'<clipPath id="{uid}{k}"><circle cx="{P[k][0]:.1f}" cy="{P[k][1]:.1f}" r="{r[k]:.1f}"/>'
                              f'</clipPath>' for k in "ABC") + "</defs>")
    for a_, b_ in (("A", "B"), ("A", "C"), ("B", "C")):
        ex.add(f'<g clip-path="url(#{uid}{a_})"><circle cx="{P[b_][0]:.1f}" cy="{P[b_][1]:.1f}" r="{r[b_]:.1f}" '
               f'fill="{colors[a_ + b_]}"/></g>')
    ex.add(f'<g clip-path="url(#{uid}A)"><g clip-path="url(#{uid}B)"><circle cx="{P["C"][0]:.1f}" cy="{P["C"][1]:.1f}" '
           f'r="{r["C"]:.1f}" fill="{colors["ABC"]}"/></g></g>')
    for k in "ABC":
        ex.occupy((P[k][0] - r[k], P[k][1] - r[k], P[k][0] + r[k], P[k][1] + r[k]), "mark", "panel-bg")
    if labels:
        acc = {}
        x0_, x1_ = min(P[k][0] - r[k] for k in "ABC"), max(P[k][0] + r[k] for k in "ABC")
        y0_, y1_ = min(P[k][1] - r[k] for k in "ABC"), max(P[k][1] + r[k] for k in "ABC")
        yy = y0_
        while yy < y1_:
            xx = x0_
            while xx < x1_:
                key = "".join(k for k in "ABC" if (xx - P[k][0]) ** 2 + (yy - P[k][1]) ** 2 <= r[k] ** 2)
                if key:
                    s = acc.setdefault(key, [0, 0, 0])
                    s[0] += xx
                    s[1] += yy
                    s[2] += 1
                xx += 2.5
            yy += 2.5
        for key, val in areas.items():
            if key in acc:
                sx, sy, n = acc[key]
                dark = len(key) > 1
                ex.text(sx / n, sy / n + 4, fmt(val), size=11.5 if val > 50 else 10.5, weight=700 if dark else 400,
                        fill="#FFFFFF" if dark else ex.C["ink"], anchor="middle")
    return P, r, R_all


def missing_band(ex, ax, items, label=None, size=10.5):
    """Grey strip under a numeric-x axis for objects missing y (reserve room with NAxes.fit(band_rows=)).

    items: [{"x": value or None, "label": str, "marker": "diamond"|"hollow"|None, "r": radius}].
    """
    import itertools
    C = ex.C
    label = label or ("未披露" if ex.body_lang else "Not disclosed")
    top = ax.below + 6
    pts = sorted([it for it in items if it.get("x") is not None], key=lambda it: it["x"])
    geo = [(it, ax.sx(it["x"]), it.get("r", 4.5), tw(it["label"], size) + it.get("r", 4.5) + 8) for it in pts]

    def rows_needed(spans):
        rows, idx = [], []
        for sp in spans:
            for ri, row in enumerate(rows):
                if all(sp[1] + 8 < a or sp[0] - 8 > b for a, b in row):
                    row.append(sp)
                    idx.append(ri)
                    break
            else:
                rows.append([sp])
                idx.append(len(rows) - 1)
        return len(rows), idx

    best = None
    for sides in itertools.product("RL", repeat=min(len(geo), 8)):
        sides = list(sides) + ["R"] * (len(geo) - len(sides))
        sp = [((px - rr - 2, px + wl) if sd == "R" else (px - wl, px + rr + 2)) for (it, px, rr, wl), sd in zip(geo, sides)]
        out_of = sum(1 for a, b in sp if a < ax.x or b > ax.x + ax.w)
        n, idx = rows_needed(sp)
        score = out_of * 100 + n * 10 + sides.count("L")
        if best is None or score < best[0]:
            best = (score, sides, idx)
    placed = [(it, px, rr, ri, sd) for (it, px, rr, wl), sd, ri in zip(geo, best[1], best[2])] if geo else []
    n_rows = max([p[3] for p in placed], default=0) + 1
    h = max(26, 18 * n_rows + 8)
    if ax.band_h and h > ax.band_h + 1:
        print(f"missing_band: 需要 {n_rows} 行，请用 NAxes.fit(..., band_rows={n_rows}) 预留空间")
    ex.rect(ax.x, top, ax.w, h, C["band"], register=False)
    ex.occupy((ax.x, top, ax.x + ax.w, top + h), "mark", "band")
    lab_rows = label.split("\n")
    lw = max(tw(rw, size) for rw in lab_rows)
    left_edge = (ex._panel or ex.body)[0]
    lx, anchor = (ax.x - 8, "end") if ax.x - 8 - lw >= left_edge - 1 else (ax.x + 8, "start")
    for i, row in enumerate(lab_rows):
        ex.text(lx, top + h / 2 + 4 + (i - (len(lab_rows) - 1) / 2) * 13, row, size=size, fill=C["sub"], anchor=anchor)
    for it, px, rr, ri, side in placed:
        py = top + 13 + ri * 18
        m = it.get("marker", "diamond")
        if m == "diamond":
            diamond(ex, px, py, rr, fill=C["context"])
        elif m == "hollow":
            ex.circle(px, py, rr, "#FFFFFF", stroke=C["context"], width=1.3, register=False)
        ex.text(px + rr + 5 if side == "R" else px - rr - 5, py + 4, it["label"], size=size,
                anchor="start" if side == "R" else "end")
    for it in items:
        if it.get("x") is None:
            ex.text(ax.x + ax.w - 8, top + h / 2 + 4, it["label"], size=size, fill=C["sub"], anchor="end", italic=True)
    return top, top + h


# ===================================================================================== reference annotations


def _zh_ex(ex, *t):
    return bool(ex.body_lang) or any(any(ord(ch) > 0x2E80 for ch in str(s)) for s in t if s)


def _pct(v):
    s = f"{abs(v) * 100:.0f}"
    return f"{'+' if v >= 0 or s == '0' else '−'}{s}%"


def _pct_cagr(v):
    """CAGR labels keep one decimal under 10% (+1.3%), else whole percent."""
    s = f"{abs(v) * 100:.1f}" if abs(v) < 0.095 else f"{abs(v) * 100:.0f}"
    return f"{'+' if v >= 0 or float(s) == 0 else '−'}{s}%"


def dashed_box(ex, x0, y0, x1, y1, label=None, color=None, width=1.1, size=10):
    """McKinsey-style region mark: a dashed outline (no fill) around the bars / points / years a claim is about, the
    label in the gap of the top edge. Four native dashed lines, not a shape: the server must not take the box for a
    text container (labels inside it are not 'overflowing' it)."""
    ex.notes += 1
    col = color or ex.C["accent"]
    from ._page import frame_w
    if label:
        lw_ = frame_w(label, size) + 8
        if lw_ > x1 - x0:   # widen the box to its label, shifted inward at the canvas edges
            pad = (lw_ - (x1 - x0)) / 2
            x0, x1 = x0 - pad, x1 + pad
            if x1 > ex.w - 1:
                x0, x1 = x0 - (x1 - ex.w + 1), ex.w - 1
            if x0 < 1:
                x0, x1 = 1, x1 + (1 - x0)
        cx = (x0 + x1) / 2
        ex.line(x0, y0, cx - lw_ / 2, y0, stroke=col, width=width, dash="4,3", tag="box")
        ex.line(cx + lw_ / 2, y0, x1, y0, stroke=col, width=width, dash="4,3", tag="box")
        ex.text(cx, y0 + size * 0.36, label, size=size, weight=700, fill=col, anchor="middle")
    else:
        ex.line(x0, y0, x1, y0, stroke=col, width=width, dash="4,3", tag="box")
    ex.line(x0, y1, x1, y1, stroke=col, width=width, dash="4,3", tag="box")
    ex.line(x0, y0, x0, y1, stroke=col, width=width, dash="4,3", tag="box")
    ex.line(x1, y0, x1, y1, stroke=col, width=width, dash="4,3", tag="box")
    ex.dashed_boxes = list(getattr(ex, "dashed_boxes", None) or []) + [(x0, y0, x1, y1, label or "")]
    return (x0, y0, x1, y1)


def band(ax, lo, hi, label=None, axis="x", color=None, opacity=None):
    """Region mark: axis="x" frames a period (NAxes: x values; column charts: category indices lo..hi inclusive),
    axis="y" a value range (target zone, valuation band). A dashed outline with the label in its top edge (McKinsey
    style), never a filled block over the data. opacity: ignored (old calls)."""
    ex, C = ax.s, ax.s.C
    from ._page import frame_w
    if axis == "x":
        if ax.xmin is None:
            b = ax.cat_bands
            step = (b[1][0] - b[0][0]) if len(b) > 1 else b[0][1]
            gap = (step - b[0][1]) / 2
            x0, x1 = b[lo][0] - gap * 0.6, b[hi][0] + b[hi][1] + gap * 0.6
        else:
            x0, x1 = ax.sx(lo), ax.sx(hi)
        ex._flush()
        # the box hugs what it frames: its top edge sits just above the tallest mark / label inside its columns,
        # then moves up (never above the plot top − 6) until its label is clear of other labels and notes
        inside = [e["box"][1] for e in ex.reg if e["kind"] in ("mark", "text") and e["box"][0] >= x0 - 1
                  and e["box"][2] <= x1 + 1 and e["box"][3] <= ax.y + ax.h + 1 and e["box"][1] >= ax.y - 30]
        y_hi = min(inside) - 8 if inside else ax.y - 6
        lw_ = frame_w(label, 10) + 8 if label else 0
        cx = (x0 + x1) / 2
        best, y = None, y_hi
        while True:
            c = ex.cost((cx - lw_ / 2, y - 7, cx + lw_ / 2, y + 5), bounds=(0, 0, ex.w, ex.h)) if label else 0
            if best is None or c < best[0]:
                best = (c, y)
            if c < 1 or y - 6 < min(ax.y - 6, y_hi):
                break
            y -= 6
        dashed_box(ex, x0, max(best[1], 9 if label else 1), x1, ax.y + ax.h - 1, label=label, color=color)
    else:
        y0, y1 = ax.sy(hi), ax.sy(lo)
        dashed_box(ex, ax.x + 1, y0, ax.x + ax.w - 1, y1, label=label, color=color)


def quadrants(ax, xv, yv, labels=None, shade="TR", color=None):
    """Four-quadrant split at (xv, yv): dashed threshold lines, one shaded quadrant (TR/TL/BR/BL or None) and quadrant
    names in the outer corners. labels: dict(TR=..., TL=..., BR=..., BL=...) — T/B = y above/below yv, R/L = x
    right/left of xv (TR = high x & high y; BR = HIGH x & low y). Call after ax.frame()."""
    ax.s.notes += 1
    ex, C = ax.s, ax.s.C
    ax._quad = (xv, yv, shade)
    if getattr(ax, "_bubble_pts", None) and _quadrant_keyed(ax, ax._bubble_pts):   # bubbles drawn first
        ex.legend_needed = [x for x in (getattr(ex, "legend_needed", None) or []) if x != "bubbles 点的颜色"]
    cx, cy = ax.sx(xv), ax.sy(yv)
    L, R, T, B = ax.x, ax.x + ax.w, ax.y, ax.y + ax.h
    boxes = dict(TL=(L, T, cx, cy), TR=(cx, T, R, cy), BL=(L, cy, cx, B), BR=(cx, cy, R, B))
    if shade:   # the quadrant that matters: a dashed outline, not a tint over the points
        a, b, c, d = boxes[shade]
        dashed_box(ex, a + 2, b + 2, c - 2, d - 2, color=color)
        ex.notes -= 1   # counted once below
    ex.line(cx, T, cx, B, stroke=C["context"], width=0.8, dash="3,3", tag="ref")
    ex.line(L, cy, R, cy, stroke=C["context"], width=0.8, dash="3,3", tag="ref")
    def put(k, t):
        a, b, c, d = boxes[k]
        w, h = tw(t, 10.5, True), 10.5
        outer = (k.endswith("R"), k[0] == "T")
        corners = sorted([(r_, t_) for r_ in (True, False) for t_ in (True, False)], key=lambda q: q != outer)
        best = None
        for r_, t_ in corners:
            x0 = c - 6 - w if r_ else a + 6
            y0 = b + 4 if t_ else d - 6 - h
            cost = ex.cost((x0, y0, x0 + w, y0 + h), bounds=(a, b, c, d))
            if best is None or cost < best[0] - 1e-6:
                best = (cost, x0, y0)
        ex.text(best[1], best[2] + h * 0.86, t, size=10.5, weight=700, fill=C["ink"] if k == shade else C["sub"])

    for k, t in (labels or {}).items():
        ex.queue.append(dict(priority=0, panel=ex._panel, fn=lambda k=k, t=t: put(k, t)))


def trend(ax, xs, ys, label=None, color=None, extend=None):
    """Least-squares trend line over (xs, ys) (NAxes), dashed; label (default 'R² 0.xx') at the right end.
    extend=(x_from, x_to) draws it over a wider x range. Returns (slope, intercept, r2)."""
    ax.s.notes += 1
    ex, C = ax.s, ax.s.C
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pts)
    mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts) or 1
    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    a = my - b * mx
    sst = sum((p[1] - my) ** 2 for p in pts) or 1
    r2 = 1 - sum((p[1] - a - b * p[0]) ** 2 for p in pts) / sst
    xa, xb = extend or (min(p[0] for p in pts), max(p[0] for p in pts))
    clamp = lambda y: min(max(y, ax.ymin), ax.ymax)  # noqa: E731
    col = color or C["accent"]
    ex.line(ax.sx(xa), ax.sy(clamp(a + b * xa)), ax.sx(xb), ax.sy(clamp(a + b * xb)), stroke=col, width=1.4,
            dash="5,3", tag="series", whole=True)
    place_label(ex, ax.sx(xb), ax.sy(clamp(a + b * xb)), label or f"R² {r2:.2f}", size=10, r=0, gap=4,
                prefer=("NW", "SW", "W", "N"), fills=[col], priority=3)
    return b, a, r2


# ===================================================================================== think-cell arrows on columns()


def _chg(a, b):
    """% change label from a to b; None when not meaningful (missing value, zero or negative base)."""
    if a is None or b is None or a <= 0:
        return None
    return b / a - 1


def _chg_lab(a, b, zh):
    d = _chg(a, b)
    if d is not None:
        return d, _pct(d)
    if a is not None and b is not None and a < 0 <= b:
        return None, "扭亏" if zh else "turnaround"
    return None, "n.m."


def _col(r, i):
    b = r["bands"][i]
    return b[0], b[0] + b[1], r["tops"][r["cats"][i]], r["values"][i]


def _oval(ex, cx, cy, text, size=10.5, color=None, own=None):
    from ._page import lint_w
    w = max(tw(text, size, True), lint_w(text, size, True)) + 14
    h = size + 9
    target = (cx, cy)
    cx, cy = _clear_whole_lines(ex, cx, cy, w / 2, h / 2, "oval", skip=own)
    if (cx, cy) != target:
        delta_x, delta_y = target[0] - cx, target[1] - cy
        fraction = 1 / math.hypot(delta_x / (w / 2), delta_y / (h / 2))
        ex.line(*target, cx + delta_x * fraction, cy + delta_y * fraction,
                stroke=ex.C["context"], width=0.8, tag="leader")
    ex.cut_lines(box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), pad=1)   # lines it hides: not under the label
    ex.add(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" fill="#FFFFFF" '
           f'stroke="{color or ex.C["ink"]}" stroke-width="1"/>')
    ex._add("mark", (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), "oval")
    ex.text(cx, cy + size * 0.36, text, size=size, weight=700, fill=color or ex.C["ink"], anchor="middle",
            register=False)


def _quarter_period(category):
    category = str(category).strip()
    year_first = re.fullmatch(r"(?:FY\s*)?['’]?(\d{4}|\d{2})\s*[-/]?\s*Q([1-4])[AEF]?", category, re.I)
    if year_first:
        year, quarter = year_first.groups()
    else:
        quarter_first = re.fullmatch(
            r"(?:Q([1-4])|([1-4])Q)\s*[-/]?\s*(?:FY\s*)?['’]?(\d{4}|\d{2})[AEF]?", category, re.I
        )
        if not quarter_first:
            return None
        quarter = quarter_first.group(1) or quarter_first.group(2)
        year = quarter_first.group(3)
    return int(year) * 4 + int(quarter) - 1, len(year)


def _half_period(category):
    """(year * 2 + half, year digits) for half-year labels (2025H1, H2 2025, 1H25, 2025年上半年), else None."""
    c = str(category).strip()
    m = re.fullmatch(r"(?:FY\s*)?['’]?(\d{4}|\d{2})\s*[-/]?\s*(?:H([12])|([12])H|年?([上下])半年)[AEF]?", c, re.I) or \
        re.fullmatch(r"(?:H([12])|([12])H)\s*[-/]?\s*(?:FY\s*)?['’]?(\d{4}|\d{2})[AEF]?", c, re.I)
    if not m:
        return None
    g = m.groups()
    if len(g) == 4:
        year, half = g[0], g[1] or g[2] or ("1" if g[3] == "上" else "2")
    else:
        half, year = g[0] or g[1], g[2]
    return int(year) * 2 + int(half) - 1, len(year)


_SUB_YEAR = re.compile(r"Q[1-4]|[1-4]Q|H[12]|[12]H|半年|\d{1,2}月|YTD|M\d|月", re.I)
_YEAR_LABEL = re.compile(r"(?:FY|CY)?\s*'?(?:(?:19|20)\d{2}|\d{2})\s*(?:年度?)?\s*[AEFPB]?(?:年[EF]?|E年)?")


def _year_of(category):
    """Calendar / fiscal year of a whole-year label (2023, FY24, 2026E, 2025年), else None."""
    c = str(category).strip()
    if _SUB_YEAR.search(c) or not _YEAR_LABEL.fullmatch(c):
        return None
    m = re.search(r"((?:19|20)\d{2})", c) or re.search(r"'?(\d{2})(?!\d)", c)
    if not m:
        return None
    y = int(m.group(1))
    return y if y >= 100 else 2000 + y


def _cagr_of(r, i, j):
    """(growth per year, elapsed years) between columns i and j from their real period labels: whole years count year
    intervals (2023 → 2025 = 2 years, not 3 points), quarters / halves count elapsed quarters / halves (annualised).
    (None, 0) when an endpoint is ≤ 0, the labels carry no period, or the two ends are of a different kind (a whole
    year vs a half-year / quarter, e.g. FY2024 → 2025H1)."""
    vi, vj = r["values"][i], r["values"][j]
    if not (vi and vj and vi > 0 < vj) or i == j:
        return None, 0
    ci, cj = r["cats"][i], r["cats"][j]
    for parse, per_year in ((_quarter_period, 4), (_half_period, 2)):
        start_period, end_period = parse(ci), parse(cj)
        if start_period is not None and end_period is not None:
            if start_period[1] != end_period[1]:
                return None, 0
            elapsed_years = (end_period[0] - start_period[0]) / per_year
            return (vj / vi) ** (1 / elapsed_years) - 1 if elapsed_years else None, elapsed_years
    yi, yj = _year_of(ci), _year_of(cj)
    if yi is None or yj is None or yi == yj:
        return None, 0
    n = yj - yi
    return (vj / vi) ** (1 / n) - 1, n


def _period_kind(category):
    """'Y' whole year, 'H' half-year, 'Q' quarter, None for other labels."""
    if _quarter_period(category) is not None:
        return "Q"
    if _half_period(category) is not None:
        return "H"
    return "Y" if _year_of(category) is not None else None


def _mixed_periods(categories):
    """True when one axis mixes whole years with half-years / quarters / YTD (FY2024, FY2025, 2025H1 …)."""
    kinds = {_period_kind(c) for c in categories}
    sub = any(_SUB_YEAR.search(str(c)) for c in categories)
    return "Y" in kinds and (bool(kinds & {"H", "Q"}) or sub)


def _title_rates():
    """Growth rates the page title / subtitle states next to CAGR / 年均 / 复合: [(value %, text as written)]."""
    from . import _frame
    t = (getattr(_frame, "LAST_TITLE", "") or "") + " " + (getattr(_frame, "LAST_SUBTITLE", "") or "")
    if not re.search(_GROWTH_WORDS, t, re.I):
        return []
    out = []
    for m in re.finditer(r"([+−-]?\d+(?:\.\d+)?)\s*%", t):
        before = t[max(0, m.start() - 10):m.start()]
        if re.search(r"份额|占比|市占|渗透|毛利|利润率|费用率|比例|share|penetration|margin|of (?:total|sales|revenue)",
                     before + t[m.end():m.end() + 8], re.I) and not re.search(_GROWTH_WORDS, before, re.I):
            continue   # a share / margin %, not a growth rate
        v = float(m.group(1).replace("−", "-"))
        if v > 0 and re.search(r"下滑|下降|萎缩|decline|fell|shrink", t[max(0, m.start() - 8):m.start()], re.I):
            v = -v
        out.append((v, m.group(1).lstrip("+")))
    return out


def _rate_text(g):
    """The title's own spelling of this rate when it states one within rounding (13.8% stays 13.8%), else None."""
    for v, txt in _title_rates():
        if abs(g * 100 - v) <= max(0.35, abs(v) * 0.03):
            num = txt.lstrip("+-−")
            return ("−" if v < 0 else "+") + num + "%"
    return None


def _title_spans(r):
    """Column spans whose CAGR matches each rate the title states (longest span first among near-equal matches)."""
    out = []
    k = len(r["values"])
    nz = [i for i, v in enumerate(r["values"]) if v]
    rates = _title_rates()
    if len(rates) == 1 and len(nz) >= 2:   # one stated rate that the whole visible span rounds to: the whole span
        g, _n = _cagr_of(r, nz[0], nz[-1])
        if g is not None and abs(g * 100 - rates[0][0]) <= 0.55:
            return [(nz[0], nz[-1])]
    for v, _ in rates:
        best = None
        for i in range(k):
            for j in range(i + 1, k):
                g, _n = _cagr_of(r, i, j)
                if g is None or (_n < 2 and k > 2):   # a one-year change is a YoY, not a CAGR span
                    continue
                err = abs(g * 100 - v)
                if err <= max(0.35, abs(v) * 0.03) and (best is None or (err + 0.05 * -(j - i)) < best[0]):
                    best = (err + 0.05 * -(j - i), i, j)
        if best and (best[1], best[2]) not in out:
            out.append((best[1], best[2]))
    if not out and len(rates) == 1 and len(nz) >= 2:   # a rounded / differently-based rate: the whole visible span
        g, _n = _cagr_of(r, nz[0], nz[-1])
        if g is not None and abs(g * 100 - rates[0][0]) <= max(1.5, abs(rates[0][0]) * 0.12):
            return [(nz[0], nz[-1])]
    return sorted(out)


def cagr_arrow(ex, r, i, j, text=None, lift=22):
    """(Also via columns(..., cagr=(i, j)).) Consulting-style CAGR arrow over columns() result r from column i to j: one
    diagonal arrow rising (or falling) from just above column i's value to just above column j's, clear of every bar in
    between, with an oval 'CAGR +x%' (computed) sitting on the line. Returns the CAGR."""
    if r.get("rate_unit"):
        raise ValueError("CAGR 不用于比率/增速/百分比序列；用 diff= 或 yoy= 表达百分点变化")
    if r.get("multiple"):
        raise ValueError("CAGR 不用于估值倍数/比率（PE、PB、x、倍）；改用 diff= 写变化，或对盈利/收入本身算 CAGR")
    names = r.get("series_names") or []
    if text is not None and len(names) > 1 and not any(nm in str(text) for nm in names):
        raise ValueError(f"cagr text={text!r}：图上有 {len(names)} 个系列，CAGR 须写明属于哪个（如 '{names[0]} CAGR +x%'）；"
                         "CAGR 按第一个系列计算——要算别的系列，把它放在第一位")
    fc, (lo_, hi_) = r.get("forecast") or [], sorted((i, j))
    # actual → forecast beyond the base year (2023A → 2028E with 2024A, 2025A in between) mixes regimes; the forecast
    # segment proper starts at the last actual (2025A → 2028E) and needs no tag
    mixed_fc = len(fc) > hi_ and fc[hi_] and not fc[lo_] and not fc[lo_ + 1]
    xi0, xi1, ti, vi = _col(r, i)
    xj0, xj1, tj, vj = _col(r, j)
    if not (vi and vj and vi > 0 < vj):
        raise ValueError(f"cagr=({i}, {j})：起止值须为正数（{vi} → {vj}），起点为零/负值或跨正负时 CAGR 无意义；"
                         "改用 diff=（绝对差额，如'亏损收窄 X'）或 yoy=")
    if r.get("share_total"):
        raise ValueError(f"cagr=({i}, {j})：各柱合计都是 100%（构成），总和的 CAGR 恒为 0、说明不了结构变化；"
                         "改写论点系列的百分点变化（unit='%' + diff= / delta=，如'推理占比 +10pt'）")
    g, n = _cagr_of(r, i, j)
    if g is None:
        ci, cj = r["cats"][i], r["cats"][j]
        kinds = {_period_kind(ci), _period_kind(cj)}
        if None not in kinds and len(kinds) > 1:
            why = "起止期间长度不同（整年 vs 半年/季度），不能算年复合"
        elif "Q" in kinds:
            why = "季度期间无法确定；CAGR 需要非零期间，且季度起止年份位数一致"
        elif None in kinds:
            why = "类别不是真实期间（年份 / 季度 / 半年），年数无从计算——CAGR 只用于按年排列的同一指标"
        else:
            why = "期间无法确定；CAGR 需要非零期间"
        raise ValueError(f"cagr=({i}, {j})：{why}（{ci} → {cj}）；改用 diff= 写差额/增幅，或只取完整年度做 CAGR")
    if mixed_fc and text is not None and not re.search(r"含预测|预测|incl\.? ?f|forecast|[EF]\b", str(text), re.I):
        raise ValueError(f"cagr=({i}, {j})：起止跨实际与预测（{r['cats'][i]} → {r['cats'][j]}），text 须注明'（含预测）'，"
                         "或拆成实际段 + 预测段（从最后一个实际年起）两个 CAGR")
    # one year apart, or a chart of only two columns: a compound rate over one step is just the change — the arrow
    # keeps its place but says 同比 / "N 年 +x%" instead of "CAGR"; a hand-written "CAGR …" text is refused
    sub_year = {_period_kind(r["cats"][i]), _period_kind(r["cats"][j])} & {"Q", "H"}
    two_point = not sub_year and (len(r["values"]) == 2 or n <= 1 + 1e-9)   # sub-year ends: labelled 年化 below
    if two_point and text is not None and re.search(r"CAGR|复合|年均|annual", str(text), re.I):
        raise ValueError(f"cagr=({i}, {j})：{r['cats'][i]} → {r['cats'][j]} 只有两个点/相隔 {n:g} 年，不是复合增速——"
                         "相邻两期用 yoy=（同比），不相邻用 diff=（差额/增幅）；或补齐中间年份再算 CAGR")
    lo0, hi0 = sorted((i % len(r["values"]), j % len(r["values"])))
    dup = next(((a_, b_) for a_, b_ in r.get("_cagr_spans", []) if a_ < hi0 and lo0 < b_), None)
    if dup is not None:   # the title already drew this arrow (columns auto CAGR): one arrow per span, not two
        print(f"cagr_arrow({i}, {j})：这张柱图已有 CAGR 箭头（{r['cats'][dup[0]]}→{r['cats'][dup[1]]}，标题/cagr= 自动画的），"
              "未再画第二条——要换区间就在 columns(cagr=(i, j)) 里改，不要另调 cagr_arrow")
        return _cagr_of(r, lo0, hi0)[0]
    from ._semantics import caliber_change_warn, noncomparable_guard
    noncomparable_guard(ex, "CAGR")
    caliber_change_warn(ex, f"CAGR {r['cats'][i]}→{r['cats'][j]}")
    ex.notes += 1
    if not two_point:
        ex.cagr_drawn = True
    fb = r.get("first_bars") or {}
    if i in fb and j in fb:   # grouped columns: the rate belongs to the first series — the arrow runs over its bars
        (xi0, wi_, ti), (xj0, wj_, tj) = fb[i], fb[j]
        xi1, xj1 = xi0 + wi_, xj0 + wj_
        # still clear every taller bar of the groups it crosses (the loop below lifts the line over r["tops"])
    a, b = (xi0 + xi1) / 2, (xj0 + xj1) / 2
    ya, yb = ti - lift, tj - lift
    # lift the whole line until every bar top (and its value label) between i and j sits below it
    lo, hi = min(i, j), max(i, j)
    for k in range(lo, hi + 1):
        c = r["cats"][k]
        xk = r["bands"][k][0] + r["bands"][k][1] / 2
        t = (xk - a) / (b - a) if b != a else 0
        yk = ya + (yb - ya) * t
        need = r["tops"][c] - (lift if k in (i, j) else lift + 14)   # clear the value labels of bars in between
        half_w = r["bands"][k][1] / 2
        for xe in (xk - half_w, xk + half_w):   # the line must clear the whole label width, not just its centre
            te = (xe - a) / (b - a) if b != a else 0
            yk = max(yk, ya + (yb - ya) * min(max(te, 0), 1))
        if yk > need:
            ya -= yk - need
            yb -= yk - need
    # ...and every yoy oval / level arrow already drawn between i and j (they sit just above the bar tops)
    for e in ex.reg:
        if e.get("tag") != "oval" and not (e["kind"] == "line" and e.get("tag") == "dim"):
            continue
        if e["kind"] == "line":
            (p0, p1) = e["box"]
            ex0, ey0, ex1, ey1 = min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1])
        else:
            ex0, ey0, ex1, ey1 = e["box"]
        if ex1 < min(a, b) or ex0 > max(a, b):
            continue
        for xe in (ex0, ex1):
            te = (xe - a) / (b - a) if b != a else 0
            yk = ya + (yb - ya) * min(max(te, 0), 1)
            need = ey0 - 8
            if yk > need:
                ya -= yk - need
                yb -= yk - need
    ya, yb = max(ya, 4), max(yb, 4)
    col = ex.C["text"]
    if text is None and two_point:   # one step: the plain change, named as such (never "CAGR")
        zh_ = _zh_ex(ex, *r["cats"])
        lo_i, hi_i = sorted((i, j))
        chg = r["values"][hi_i] / r["values"][lo_i] - 1
        if abs(n - 1) < 1e-9:
            lab = f"{'同比' if zh_ else 'YoY'} {_pct(chg)}"
        else:
            lab = f"{n:g} 年 {_pct(chg)}" if zh_ else f"{_pct(chg)} over {n:g} yrs"
    elif text is None and sub_year:   # quarterly / half-year endpoints: an annualised rate, not an annual CAGR
        zh_ = _zh_ex(ex, *r["cats"])
        lab = f"{'年化' if zh_ else 'Annualised'} {_rate_text(g) or _pct_cagr(g)}"
    else:
        lab = text or f"CAGR {_rate_text(g) or _pct_cagr(g)}"
    if text is None:
        zh_ = _zh_ex(ex, *r["cats"])
        if len(names) > 1:   # several series: say which one the rate belongs to (it is computed on the first)
            lab = f"{names[0]} {lab}"
        if mixed_fc:   # actual → forecast: the reader must see the end point is an estimate
            lab += "（含预测）" if zh_ else " (incl. fcst)"
    from ._page import lint_w
    half = (max(tw(lab, 10.5, True), lint_w(lab, 10.5, True)) + 14) / 2
    cx = (a + b) / 2
    div = r.get("divider")
    if div is not None and abs(cx - div) < half + 4 and b - a > 4 * half:  # keep the oval off the 实绩|预测 divider
        cx = div + half + 6 if b > div else div - half - 6
    from ._page import _ov
    oh = 19.5

    def at(c):
        return c, ya + (yb - ya) * ((c - a) / (b - a) if b != a else 0)

    def busy(c):
        x_, y_ = at(c)
        box = (x_ - half - 2, y_ - oh / 2 - 2, x_ + half + 2, y_ + oh / 2 + 2)
        return any((e["kind"] == "text" or e.get("tag") == "oval") and _ov(box, e["box"]) for e in ex.reg)
    if busy(cx) and b - a > 2 * half:   # slide the oval along its own line off value labels / other ovals
        span = b - a
        for t in (0.35, 0.65, 0.25, 0.75, 0.15, 0.85):
            c = a + span * t
            if min(c, a + span - half) >= a + half - 2 and not busy(c):
                cx = c
                break
    # the label sits just above its arrow (consulting style). The server judges a line by its bounding box, so the
    # oval clears the arrow's top end; it slides toward the high end, where the line comes closest to it
    lo_x, hi_x = sorted((a, b))
    rise = yb < ya
    oy = min(ya, yb) - oh / 2 - 3
    if oy - oh / 2 < 1:   # arrow lifted to the top edge: lower it as far as the labels / bars under it allow
        def line_y(x_):
            return ya + (yb - ya) * (min(max((x_ - a) / (b - a), 0), 1) if b != a else 0)
        slack = min([e["box"][1] - 4 - max(line_y(e["box"][0]), line_y(e["box"][2])) for e in ex.reg
                     if e["kind"] in ("text", "mark") and e.get("tag") not in ("grid", "oval")
                     and e["box"][2] > lo_x and e["box"][0] < hi_x and e["box"][1] > min(ya, yb)] or [0])
        drop = min(max(slack, 0), 1 - (oy - oh / 2))
        ya, yb, oy = ya + drop, yb + drop, oy + drop
    if oy - oh / 2 >= 1:
        def sit(c_):   # the oval rests on the line: its lower edge just above the line's highest point under it
            return max(min(at(c_ - half)[1], at(c_ + half)[1]) - oh / 2 - 3, oh / 2 + 1)
        c = (a + b) / 2
        for t in ((0.5, 0.62, 0.38, 0.75, 0.25) if rise else (0.5, 0.38, 0.62, 0.25, 0.75)):
            c = min(max(a + (b - a) * t, lo_x + half), hi_x - half) if hi_x - lo_x > 2 * half else (a + b) / 2
            box = (c - half - 2, sit(c) - oh / 2 - 2, c + half + 2, sit(c) + oh / 2 + 2)
            if not any((e["kind"] == "text" or e.get("tag") == "oval") and _ov(box, e["box"]) for e in ex.reg):
                break
        ex.line(a, ya, b, yb, stroke=col, width=1.1, marker="arr", tag="dim", whole=True)
        _oval(ex, c, sit(c), lab, own=ex.reg[-1])
        return g
    if abs(b - a) < 2 * half + 60:   # no room above the arrow: the oval rides on the middle of the line
        cx = (a + b) / 2
    cx, cy = at(cx)
    ex.line(a, ya, b, yb, stroke=col, width=1.1, marker="arr", tag="dim", whole=True)
    _oval(ex, cx, cy, lab)
    return g


def title_rate_orphans(ex):
    """Growth rates the title states next to CAGR / 年均 that no column series on this exhibit compounds to (any span
    of any series, total or segment): e.g. "利润 CAGR 4.03%" over a revenue-only chart. [] when nothing to compare."""
    charts = getattr(ex, "_cagr_charts", None) or []
    rates = _title_rates()
    if not charts or not rates:
        return []
    out = []
    for v, txt in rates:
        hit = False
        for cats, seqs in charts:
            for vals in seqs:
                rr = {"values": vals, "cats": cats}
                k = len(vals)
                hit = hit or any((g := _cagr_of(rr, a, b)[0]) is not None and abs(g * 100 - v) <= max(0.6, abs(v) * 0.05)
                                 for a in range(k) for b in range(a + 1, k))
        if not hit:
            out.append(txt + "%")
    return out


def _arrow(ex, r, i, j, x):
    xi0, xi1, ti, vi = _col(r, i)
    xj0, xj1, tj, vj = _col(r, j)
    for a, b, ty in ((xi0, xi1, ti), (xj0, xj1, tj)):
        lo, hi = (b, x + 4) if x > b + 2 else ((x - 4, a) if x < a - 2 else (None, None))
        if lo is None:
            continue
        for k, c in enumerate(r["cats"]):  # stop the level line before a taller column (and its value label)
            ca, cb = r["bands"][k][0], r["bands"][k][0] + r["bands"][k][1]
            if ca > lo and cb < hi and r["tops"][c] - 16 < ty:
                lo, hi = (lo, hi) if x < ca else (max(lo, cb), hi)
                if x > cb:
                    lo = max(lo, cb)
                else:
                    hi = min(hi, ca)
        ex.line(lo, ty, hi, ty, stroke=ex.C["context"], width=0.8, dash="2,2", tag="dim")
    up = tj < ti
    ex.line(x, ti - (1 if up else -1), x, tj + (3 if up else -3), stroke=ex.C["text"], width=1.1,
            marker="arr", tag="dim", whole=True)
    return ti, tj, _chg_lab(vi, vj, bool(ex.body_lang) or any(ord(c) > 0x2E80 for c in "".join(r["cats"])))


def total_diff(ex, r, i, j, text=None, color=None):
    """think-cell total-difference arrow: level lines from the tops of columns i and j run right of the last column,
    a vertical arrow joins them and an oval on the arrow shows the % difference (computed; grouped/stacked columns
    use the first series / the stack total). Without ~60px free right of the box it goes into the gap left of j.
    Returns the difference ratio (None when not meaningful: negative/zero base → "扭亏"/"n.m.")."""
    from ._semantics import noncomparable_guard
    noncomparable_guard(ex, "差值箭头（diff=）")
    ex.notes += 1
    n_ = len(r["values"])
    i, j = i % n_, j % n_
    if i > j:   # a difference reads earlier → later: diff=(1, 0) on 22.1 → 40.5 must not print −45%
        i, j = j, i
    vi, vj = r["values"][i], r["values"][j]
    if vi is None or vj is None:
        raise ValueError(f"diff=({i}, {j})：有缺失值，换一对有数据的柱")
    if text:
        cands = [vj - vi, vi - vj] + ([vj / vi - 1, vj / vi] if vi else [])
        check_label_numbers(text, cands, f"diff=({i}, {j}, 文本)", what=f"{r['cats'][i]}→{r['cats'][j]} 的差")
    lab = text or _chg_lab(vi, vj, True)[1]
    ow = tw(lab, 10.5, True) + 14
    x = max(_col(r, k)[1] for k in range(min(i, j), max(i, j) + 1)) + ow / 2 + 6
    from . import _layouts as _ly
    if j < n_ - 1:   # other columns stand right of j: an arrow pushed right of j lands on column j+1 and reads as its own
        if j - i == 1:
            ex.notes -= 1   # level_diff counts the mark itself
            return level_diff(ex, r, i, text=text or None, color=color)
        return _span_bracket(ex, r, i, j, text, color)
    if j - i >= 2 and (_ly.PROFILE.get("speech") or x + ow / 2 > ex.w):
        # non-adjacent pair: an arrow in the gap left of j reads as "(j-1) → j"; bracket both bars and name the periods
        return _span_bracket(ex, r, i, j, text, color)
    if x + ow / 2 > ex.w:  # no room right of the last column: put the arrow in the gap left of column j instead
        x = (_col(r, j - 1)[1] + _col(r, j)[0]) / 2 if j else _col(r, j)[0] - 6
    ti, tj, (d, auto) = _arrow(ex, r, i, j, x)
    _oval(ex, x, (ti + tj) / 2, text or auto, color=color or (ex.C["neg"] if d is not None and d < 0 else ex.C["accent"]))
    return d


def _span_bracket(ex, r, i, j, text=None, color=None):
    """Bracket over non-adjacent columns i < j: a tick above each compared bar, a line joining them above every bar in
    between, and an oval naming both periods with the change ("24Q1→25Q3 +54%"). Returns the change ratio."""
    xi0, xi1, ti, vi = _col(r, i)
    xj0, xj1, tj, vj = _col(r, j)
    d, auto = _chg_lab(vi, vj, bool(ex.body_lang) or any(ord(c) > 0x2E80 for c in "".join(map(str, r["cats"]))))
    top = min(r["tops"][r["cats"][k]] for k in range(i, j + 1))
    y = max(top - 30, 14.0)
    ci, cj = (xi0 + xi1) / 2, (xj0 + xj1) / 2
    col = color or (ex.C["neg"] if d is not None and d < 0 else ex.C["accent"])
    ex.line(ci, y, cj, y, stroke=ex.C["text"], width=1, tag="dim")
    for cx, ty in ((ci, ti), (cj, tj)):
        ex.line(cx, y, cx, max(y + 4, ty - 16), stroke=ex.C["text"], width=1, tag="dim")
    named = text and str(r["cats"][i]) in text and str(r["cats"][j]) in text   # the label already names both ends
    _oval(ex, (ci + cj) / 2, y, text if named else f"{r['cats'][i]}→{r['cats'][j]} {text or auto}", color=col)
    return d


def level_diff(ex, r, i, text=None, color=None):
    """think-cell level-difference arrow between neighbouring columns i and i+1 (YoY): arrow in the gap between the
    two bar tops, oval label with the % change (computed) just above it. Returns the change ratio."""
    from ._semantics import noncomparable_guard
    noncomparable_guard(ex, "同比箭头（yoy=）")
    ex.notes += 1
    if r["values"][i] is None or r["values"][i + 1] is None:
        raise ValueError(f"yoy={i}：第 {i} 或 {i + 1} 根柱缺值，换一个有数据的位置")
    x = (_col(r, i)[1] + _col(r, i + 1)[0]) / 2
    ti, tj, (d, auto) = _arrow(ex, r, i, i + 1, x)
    oy = min(ti, tj) - 30
    lab = text or auto
    ow, oh = tw(lab, 10.5, True) + 14, 19.5
    from ._page import _ov

    def hit(cx, cy):
        box = (cx - ow / 2 - 2, cy - oh / 2 - 2, cx + ow / 2 + 2, cy + oh / 2 + 2)
        return any(e["kind"] == "text" and _ov(box, e["box"]) for e in ex.reg)
    ox = x
    if hit(ox, oy):   # value labels / 实绩|预测 tags in the way: sit the oval beside the arrow, level with its middle
        mid = (ti + tj) / 2
        for cx in (x + ow / 2 + 6, x - ow / 2 - 6):
            if not hit(cx, mid):
                ox, oy = cx, mid
                break
    if ox == x:
        ex.line(x, oy + 9, x, min(ti, tj) - 2, stroke=ex.C["context"], width=0.8, tag="dim")
    _oval(ex, ox, oy, lab, color=color or (ex.C["neg"] if d is not None and d < 0 else ex.C["accent"]))
    return d


def relate(ex, A, B, kind="arrow", text=None, src=None, op="×", color=None):
    """Show HOW two panels (ex.cols boxes A → B) relate instead of just placing them side by side / stacked.
    kind="drill": src (a box (x0, y0, x1, y1) in A, or (columns_result, k) for bar k) gets an outline and two dashed
    lines fan out from it to B's near edge — "this bar / segment is broken down on the right"; put B's breakdown
    of exactly that value in B. kind="arrow": a chevron in the gap with a 2–4 character relation word above it
    (text="导致"/"拆解为"/"因此"/"drives"). kind="op": an operator circle in the gap (op="×", "+", "=", "−") for
    A × B = result style pages. Needs a gap of ≥48 canvas units between the panels (ex.cols(2, gap=56)).
    Returns the connector's box."""
    ex.notes += 1
    ex.related = True
    C = ex.C
    col = color or C["accent"]
    ax0, ay0, ax1, ay1 = A
    bx0, by0, bx1, by1 = B
    horiz = bx0 >= ax1 - 1   # B right of A; otherwise B below A
    if kind == "drill":
        if isinstance(src, tuple) and len(src) == 2 and isinstance(src[0], dict):
            r, k = src
            x0, w = r["bands"][k]
            src = (x0 - 3, r["tops"][r["cats"][k]] - 3, x0 + w + 3, r["ax"].sy(r["ax"].ymin) + 1)
        sx0, sy0, sx1, sy1 = src
        ex.add(f'<rect x="{sx0:.1f}" y="{sy0:.1f}" width="{sx1 - sx0:.1f}" height="{sy1 - sy0:.1f}" fill="none" '
               f'stroke="{col}" stroke-width="1.4"/>')
        if horiz:
            pairs = (((sx1, sy0), (bx0, by0 + 10)), ((sx1, sy1), (bx0, by1 - 24)))   # ≈ B's plot top / x axis
        else:
            pairs = (((sx0, sy1), (bx0, by0)), ((sx1, sy1), (bx1, by0)))
        for p, q in pairs:
            ex.line(*p, *q, stroke=col, width=1, dash="4,3", tag="dim")
        return (min(sx0, bx0), min(sy0, by0), max(sx1, bx0), max(sy1, by1))
    if horiz:
        cx, cy = (ax1 + bx0) / 2, (max(ay0, by0) + min(ay1, by1)) / 2
    else:
        cx, cy = (max(ax0, bx0) + min(ax1, bx1)) / 2, (ay1 + by0) / 2
    gap = (bx0 - ax1) if horiz else (by0 - ay1)
    if gap < 40:
        raise ValueError(f"relate：两个面板间隙只有 {gap:.0f}，放不下连接符；用 ex.cols(2, gap=56)（上下排列用 vgap=56）")
    if kind == "op":
        rr = min(gap / 2 - 4, 18)
        ex.circle(cx, cy, rr, col)
        ex.text(cx, cy + 7, op, size=20, weight=700, fill="#FFFFFF", anchor="middle", register=False)
        return (cx - rr, cy - rr, cx + rr, cy + rr)
    s = min(gap / 2 - 6, 16)   # chevron half-size
    if horiz:
        d = f"M{cx - s * 0.6:.1f},{cy - s:.1f} L{cx + s * 0.6:.1f},{cy:.1f} L{cx - s * 0.6:.1f},{cy + s:.1f} " \
            f"L{cx - s * 0.1:.1f},{cy:.1f} Z"
    else:
        d = f"M{cx - s:.1f},{cy - s * 0.6:.1f} L{cx:.1f},{cy + s * 0.6:.1f} L{cx + s:.1f},{cy - s * 0.6:.1f} " \
            f"L{cx:.1f},{cy - s * 0.1:.1f} Z"
    ex.path(d, fill=col, pts=[(cx - s, cy - s), (cx + s, cy + s)])
    if text:
        if horiz:
            for n_, ln in enumerate(text if isinstance(text, list) else [text]):
                ex.text(cx, cy - s - 8 - 14 * n_, ln, size=11, weight=700, fill=col, anchor="middle", register=False)
        else:
            ex.text(cx + s + 6, cy + 4, text, size=11, weight=700, fill=col, register=False)
    return (cx - s, cy - s, cx + s, cy + s)
