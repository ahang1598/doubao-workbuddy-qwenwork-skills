"""More blocks: line chart with bands and end labels, donut, marimekko, timeline, sankey, distributions."""

from __future__ import annotations

import re

import math

from ._axes import NAxes
from ._marks import gap_marks, polyline
from ._place import place_label
from ._text import fmt, has_cjk, tw, wrap

# ===================================================================================== lines


def _DEFAULT_FMT(v):
    return fmt(v)


def lines(ex, box, x, series, xlim=None, ylim=None, xticks=None, yticks=None, xtitle=None, ytitle=None,
          xfmt=_DEFAULT_FMT, yfmt=lambda v: fmt(v), forecast_from=None, end_labels=True, focus=None, dots=True,
          band_rows=0, delta=None, delta_fmt=None, note=None, unit=None, xticklabels=None, rows=None):
    """Multi-line chart with optional uncertainty bands, forecast dashing and direct end labels (no legend).

    rows=[(name, values[, fmt])]: 1–2 data rows under the x axis, one value per x (a second metric of the same periods,
    e.g. 渗透率 under a volume line) — no second y axis.

    x: list of x values (numbers / years). series: [{"name", "y": [...], "color"?, "lo"?: [...], "hi"?: [...]}].
    forecast_from: x value where the forecast starts — later segments are dashed and a shaded region marks it.
    focus: callable(name) -> bool (others grey).
    delta=(name_a, name_b, x_value | [x values]): at each x a vertical bracket joins the two lines with the computed
    gap b − a — or a − b when the names say a is the actual and b the reference (实际 vs 目标 / AC vs PY) — ("+4.2", via yfmt; delta_fmt=callable(d) -> str for units, e.g. lambda d: f"{d:+.1f}pt").
    unit: the series unit (or a METRICS dict); a rate unit (%, pt, pp) labels the delta gap in pt automatically.
    note=(x value, "what this point means") — speech bubble on the first series' point (or (series name, x, text));
    a list for two. ≤2 per chart.
    Returns the NAxes (for annotations via ax.sx / ax.sy).
    """
    from ._page import check_box as _cb
    _cb(box, "lines")
    C = ex.C
    from ._page import chart_box as _cbx
    box = _cbx(ex, box)
    _start, _notes0 = len(ex.el), ex.notes
    if xticklabels is not None or any(isinstance(v, str) for v in x):   # period labels ("24Q1", "2025H1"): even steps
        if xticklabels is not None and xticks is not None and len(xticklabels) == len(xticks) != len(x) \
                and not any(isinstance(v, str) for v in xticks):   # labels for the ticks only: place each at its tick
            labels = [""] * len(x)
            for t_, l_ in zip(xticks, xticklabels):
                if 0 <= int(round(t_)) < len(x):
                    labels[int(round(t_))] = str(l_)
        else:
            labels = [str(v) for v in (xticklabels or x)]
        pos = {str(v): k for k, v in enumerate(x)}
        if forecast_from is not None:
            forecast_from = pos.get(str(forecast_from), forecast_from)
        if note is not None:
            nts = [note] if isinstance(note, tuple) and isinstance(note[-1], str) and len(note) in (2, 3) else list(note)
            nts = [tuple(nt[:-2]) + (pos.get(str(nt[-2]), nt[-2]), nt[-1]) for nt in nts]
            note = nts[0] if len(nts) == 1 else nts
        x = list(range(len(x)))
        xticks = xticks if xticks is not None and not any(isinstance(v, str) for v in xticks) else None
        xfmt = lambda v: labels[int(round(v))] if float(v).is_integer() and 0 <= int(round(v)) < len(labels) else ""   # noqa: E731
    from . import _semantics as _sem
    _sem.mixed_units([s.get("name") for s in series] + [ytitle, unit if isinstance(unit, str) else None],
                     "lines", "第二个单位的指标放轴下数据行 rows=[(名, 值列表, fmt)]，或分成上下两个面板（各自纵轴、各自单位）")
    if len(series) > 1 and not end_labels:
        ex.legend_needed = list(getattr(ex, "legend_needed", None) or []) + ["lines 多条线（end_labels=False）"]
    ys = [v for s in series for v in (s["y"] + (s.get("lo") or []) + (s.get("hi") or [])) if v is not None]
    xlim = xlim or (min(x), max(x))
    ylim = ylim or (min(0, min(ys)), max(ys) * 1.08)
    is_year = all(1900 <= v <= 2100 for v in x) and any(float(v).is_integer() for v in x)
    if is_year and xfmt is _DEFAULT_FMT:
        xfmt = lambda v: f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"
    xt = xticks or list(x)
    if xt[0] > xlim[0] or xt[-1] < xlim[1]:
        xt = sorted(set(xt) | {xlim[0], xlim[1]})
    right_pad = (max(tw(s["name"], 10.5, True) + 4 + tw(yfmt(next(v for v in reversed(s["y"]) if v is not None)), 10.5)
                     for s in series) + 14) if end_labels else 0
    x0, y0, x1, y1 = box
    from ._marks import _check_rows, ROW_H
    data_rows = _check_rows(rows, x, "lines")
    if data_rows:   # the strip under the x axis comes off the box bottom
        y1 -= ROW_H * len(data_rows) + 6
    from ._axes import nice_ticks as _nt
    _yt = yticks or _nt(ylim[1], 5, ylim[0])
    left = max(36, max(tw(yfmt(t), 10.5) for t in _yt) + 10)   # wide tick labels (40,000) must not spill left
    if data_rows:   # row names sit left of the first x value: the plot starts right of the widest name
        left = max(left, max(tw(n_, 10, True) for n_, _, _ in data_rows) + 6
                   + max(tw(f_(v_[0]) if v_[0] is not None else "—", 10) for _, v_, f_ in data_rows) / 2 + 8)
    ax = NAxes.fit(ex, (x0, y0, x1 - right_pad, y1), xlim, ylim, xticks=xt, yticks=yticks, xtitle=bool(xtitle),
                   ytitle=bool(ytitle), band_rows=band_rows, left=left)
    ax.xticks, ax.xmin, ax.xmax = xt, xlim[0], xlim[1]
    shown = set(xticks) if xticks else set(x)
    if forecast_from is not None:   # a dashed divider + 预测 tag (no grey block over the forecast years)
        fx = ax.sx(forecast_from)
        ex.line(fx, ax.y, fx, ax.y + ax.h, stroke=C["context"], width=0.8, dash="3,3", tag="ref")
        cjk = any(ord(ch) > 0x2E80 for ch in ex.body_lang)
        ex.text(fx + 6, ax.y + 12, "预测" if cjk else "Forecast", size=10, fill=C["sub"])
    ax.frame(xfmt=lambda v: xfmt(v) if v in shown else "", yfmt=yfmt, xtitle=xtitle, ytitle=ytitle, zero_line=False)
    palette = [C["main"], C["accent"], C["second"], C["third"], C["context"]]
    ends = []
    for i, s in enumerate(series):
        col = s.get("color") or palette[i % len(palette)]
        if focus is not None and not focus(s["name"]):
            col = C["dim"]
        if s.get("lo") and s.get("hi"):
            idx = [j for j in range(len(x)) if s["lo"][j] is not None and s["hi"][j] is not None]
            if forecast_from is not None and idx:   # start the band at the last actual point for continuity
                k0 = max([j for j in range(len(x)) if x[j] <= forecast_from], default=idx[0])
                if k0 not in idx:
                    idx = [k0] + idx
            hi = lambda j: s["hi"][j] if s["hi"][j] is not None else s["y"][j]
            lo = lambda j: s["lo"][j] if s["lo"][j] is not None else s["y"][j]
            up = [(ax.sx(x[j]), ax.sy(hi(j))) for j in idx]
            dn = [(ax.sx(x[j]), ax.sy(lo(j))) for j in reversed(idx)]
            ex.path("M" + " L".join(f"{p:.1f},{q:.1f}" for p, q in up + dn) + " Z", fill=col, opacity=0.14,
                    register=False)
        gap_ys = s["y"]
        if forecast_from is None:
            polyline(ax, x, s["y"], col, width=2.2, dots=dots)
        else:
            k = next((j for j, v in enumerate(x) if v >= forecast_from), len(x))
            polyline(ax, x[:k + 1], s["y"][:k + 1], col, width=2.2, dots=dots)
            if k < len(x) - 1:
                # forecast years not modelled (2026E … None … 2030E): one dashed line through the given points — a
                # forecast path is an estimate, not a series with missing observations, so no break and no '缺'
                fx = [xv for xv, yv in zip(x[k:], s["y"][k:]) if yv is not None]
                fy = [yv for yv in s["y"][k:] if yv is not None]
                if len(fx) >= 2:
                    polyline(ax, fx, fy, col, width=2.2, dash="5,3", dots=dots)
                gap_ys = list(s["y"][:k + 1]) + [0 if (yv is None and any(v is not None for v in s["y"][j + 1:])) else yv
                                                 for j, yv in enumerate(s["y"]) if j > k]
        # an interior missing value: the two known points are joined by a thin dashed line (the dash says "no data
        # here" — no '缺' text on the chart); leading / trailing None simply shorten the line
        known = [j for j, v in enumerate(gap_ys) if v is not None]
        for a_, b_ in zip(known, known[1:]):
            if b_ - a_ > 1 and s["y"][a_] is not None and s["y"][b_] is not None:
                ex.line(ax.sx(x[a_]), ax.sy(s["y"][a_]), ax.sx(x[b_]), ax.sy(s["y"][b_]), stroke=col, width=1.4,
                        dash="4,3", tag="gap")
        last = max(j for j, v in enumerate(s["y"]) if v is not None)
        px, py = ax.sx(x[last]), ax.sy(s["y"][last])
        ex.circle(px, py, 3, col)
        ends.append([py, s["name"], yfmt(s["y"][last]), col, px])
    if delta is not None:
        from ._kpi import is_rate_unit, pt_text
        _line_delta(ex, ax, x, series, delta, delta_fmt or (pt_text if is_rate_unit(unit) else (
            lambda d: ("+" if d > 0 else ("−" if d < 0 else "±")) + yfmt(abs(d)))))
    if note:
        from ._composite import speech_note
        nts = [note] if isinstance(note, tuple) and isinstance(note[-1], str) and len(note) in (2, 3) else list(note)
        by = {s["name"]: s for s in series}
        for nt in nts:
            s_ = by[nt[0]] if len(nt) == 3 else series[0]
            xv, txt = nt[-2], nt[-1]
            if xv not in x:
                raise ValueError(f"lines(note=)：x={xv} 不在 x 列表中")
            speech_note(ex, (ax.sx(xv), ax.sy(s_["y"][list(x).index(xv)])), txt)
    if end_labels:
        ends.sort()
        for j in range(1, len(ends)):  # de-overlap vertically
            if ends[j][0] - ends[j - 1][0] < 15:
                ends[j][0] = ends[j - 1][0] + 15
        for py, name, val, col, px in ends:
            # a line that stops before the last year gets its label at its own end (not floating at the far right)
            early = forecast_from is not None and px <= ax.sx(forecast_from) + 1 and px < ax.x + ax.w - 30
            lx = (px + 8) if early else max(px, ax.x + ax.w) + 8
            ex.text(lx, py + 4, name, size=10.5, weight=700, fill=C["sub"] if col in (C["dim"], C["context"]) else col)
            ex.text(lx + 4 + tw(name, 10.5, True), py + 4, val, size=10.5, fill=C["sub"])
    plain = (not any(s.get("lo") or s.get("hi") for s in series) and len(x) >= 3 and len(series) <= 4
             and all(float(v).is_integer() for v in x) and forecast_from is None and focus is None and not data_rows)
    if data_rows:
        from ._marks import _draw_rows
        _draw_rows(ex, ax, [ax.sx(v) for v in x], data_rows, y1 + 6, left=x0)
    if plain:   # plain lines may become an editable chart on a multi-chart page
        from ._autonative import record
        palette = [C["main"], C["accent"], C["second"], C["third"], C["context"]]
        record(ex, "line", box, _start, _notes0, [xfmt(v) for v in x], [(s["name"] or "值", list(s["y"])) for s in series],
               [s.get("color") or palette[i % len(palette)] for i, s in enumerate(series)], values=False)
    from ._marks import _mixed_periods
    xs_ = [v for v in x if isinstance(v, (int, float))]
    if (_mixed_periods([xfmt(v) for v in x]) or (xs_ and all(1990 <= v <= 2100 for v in xs_)
                                                  and any(float(v).is_integer() for v in xs_)
                                                  and any(not float(v).is_integer() for v in xs_))):
        ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + [
            "年度与半年/季度混在同一根轴：读者会当成连续时间——年度与半年分成两个面板（或两组并留空隙），CAGR 只算完整年度"]))
    from ._page import add_fact, growth_items
    add_fact(ex, {"kind": "chart", "fn": "lines", "cats": [xfmt(v) for v in x], "x": list(x),
                  "series": [(str(s.get("name") or ""), list(s["y"])) for s in series]})
    if len(x) >= 3:   # title check: "持续上行" needs a monotonic series; "X 带动" the fastest-growing line
        for s in series:
            add_fact(ex, {"kind": "series", "name": str(s.get("name") or ""), "values": list(s["y"]),
                          "periods": [xfmt(v) for v in x]})
        if len(series) >= 2:
            g = growth_items([s.get("name") or "" for s in series],
                             [next((v for v in s["y"] if v is not None), None) for s in series],
                             [next((v for v in reversed(s["y"]) if v is not None), None) for s in series])
            if len(g) >= 2:
                add_fact(ex, {"kind": "growth", "items": g})
    return ax


def _line_delta(ex, ax, x, series, delta, fmt_):
    na, nb, xs = delta
    by = {s["name"]: s for s in series}
    if na not in by or nb not in by:
        raise ValueError(f"lines(delta=)：找不到系列 {na!r}/{nb!r}（已有 {list(by)}）")
    xs = list(xs) if isinstance(xs, (list, tuple)) else [xs]
    from ._semantics import noncomparable_guard
    noncomparable_guard(ex, "两线差值（delta=）")
    ex.notes += 1
    C, out = ex.C, {}
    for xv in xs:
        if xv not in x:
            raise ValueError(f"lines(delta=)：x={xv} 不在 x 列表中")
        j = list(x).index(xv)
        va, vb = by[na]["y"][j], by[nb]["y"][j]
        if va is None or vb is None:
            continue
        from ._kpi import ac_minus_ref_order
        d = (va - vb) if ac_minus_ref_order(str(na), str(nb)) < 0 else (vb - va)   # always actual − reference
        out[xv] = d
        px, ya, yb = ax.sx(xv), ax.sy(va), ax.sy(vb)
        from ._marks import _sign_fix
        lab = _sign_fix(fmt_(d))
        w_ = tw(lab, 10.5, True)
        # bracket just right of the point (left of it at the right edge of the plot), label beside the bracket
        right = px + 8 + 6 + 4 + w_ <= ax.x + ax.w + 2
        bx = px + 6 if right else px - 6
        dep = 4 if right else -4
        top, bot = min(ya, yb) + 3, max(ya, yb) - 3
        if bot - top < 4:
            top, bot = (ya + yb) / 2 - 2, (ya + yb) / 2 + 2
        pts = [(bx, top), (bx + dep, top), (bx + dep, bot), (bx, bot)]
        ex.path("M" + " L".join(f"{p:.1f},{q:.1f}" for p, q in pts), stroke=C["text"], width=0.9, pts=pts)
        ty = (top + bot) / 2 + 10.5 * 0.36
        ex.text(bx + dep + (4 if right else -4), ty, lab, size=10.5, weight=700,
                fill=C["neg"] if d < 0 else C["ink"], anchor="start" if right else "end")
    ax.deltas = out
    return out


# ===================================================================================== donut


def donut(ex, cx, cy, r, segs, hole=0.62, center=None, center_sub=None, labels=True, focus=None, start=-90,
          inside=True):
    """Donut. segs [(label, value, color)]; labels go outside with short leaders (left/right columns, de-overlapped).
    center: big text in the hole (e.g. total); center_sub: small text under it."""
    from ._page import SERIF
    C = ex.C
    total = sum(v for _, v, _ in segs) or 1
    if all(0 <= v <= 100 for _, v, _ in segs) and 102 < total < 140 and len(segs) >= 2:   # shares that overshoot 100
        raise ValueError(f"donut：各扇区合计 {total:g}（像百分比却 >100%）——构成要互斥、同一分母、加总 100%；"
                         "不同总体的占比改用条形图逐项比较")
    a = math.radians(start)
    left, right = [], []
    for lab, v, col in segs:
        da = v / total * 2 * math.pi
        if focus is not None and not focus(lab):
            col = C["dim"]
        a2 = a + da
        large = 1 if da > math.pi else 0
        ri = r * hole
        p = [(cx + r * math.cos(a), cy + r * math.sin(a)), (cx + r * math.cos(a2), cy + r * math.sin(a2)),
             (cx + ri * math.cos(a2), cy + ri * math.sin(a2)), (cx + ri * math.cos(a), cy + ri * math.sin(a))]
        d = (f"M{p[0][0]:.1f},{p[0][1]:.1f} A{r:.1f},{r:.1f} 0 {large} 1 {p[1][0]:.1f},{p[1][1]:.1f} "
             f"L{p[2][0]:.1f},{p[2][1]:.1f} A{ri:.1f},{ri:.1f} 0 {large} 0 {p[3][0]:.1f},{p[3][1]:.1f} Z")
        ex.path(d, fill=col, stroke="#FFFFFF", width=1.2, register=False)
        mid = (a + a2) / 2
        (right if math.cos(mid) >= 0 else left).append([cy + (r + 14) * math.sin(mid), lab, v, mid, col])
        a = a2
    ex.occupy((cx - r, cy - r, cx + r, cy + r), "mark", "donut")
    if center:
        ex.text(cx, cy + (4 if not center_sub else -2), center, size=22, family=SERIF, fill=C["ink"], anchor="middle")
    if center_sub:
        ex.text(cx, cy + 16, center_sub, size=10.5, fill=C["sub"], anchor="middle")
    if labels and inside:  # think-cell style: % inside each big segment, name outside only for small ones
        a = math.radians(start)
        for lab, v, col in segs:
            da = v / total * 2 * math.pi
            mid = a + da / 2
            a += da
            rr = r * (1 + hole) / 2
            if da > 0.5:
                tx, ty = cx + rr * math.cos(mid), cy + rr * math.sin(mid)
                light = col in (C["light"], C["light2"], C["dim"], C["context"], C["track"])
                ex.text(tx, ty - 2, f"{v / total * 100:.0f}%", size=12, weight=700, anchor="middle",
                        fill=C["ink"] if light else "#FFFFFF", register=False)
                ex.text(tx, ty + 12, lab, size=10, anchor="middle", fill=C["ink"] if light else "#FFFFFF", register=False)
            else:
                ox, oy = cx + (r + 16) * math.cos(mid), cy + (r + 16) * math.sin(mid)
                ex.text(ox, oy + 4, f"{lab} {v / total * 100:.0f}%", size=10.5, weight=700,
                        anchor="start" if math.cos(mid) >= 0 else "end", fill=C["ink"])
        return
    if labels:
        for side, items in (("R", right), ("L", left)):
            items.sort()
            for j in range(1, len(items)):
                if items[j][0] - items[j - 1][0] < 26:
                    items[j][0] = items[j - 1][0] + 26
            for ly, lab, v, mid, col in items:
                sx, sy = cx + r * math.cos(mid), cy + r * math.sin(mid)
                ex_ = cx + (r + 18) * (1 if side == "R" else -1)
                ex.line(sx, sy, ex_, ly, stroke=C["context"], width=0.7, tag="leader")
                anchor = "start" if side == "R" else "end"
                tx = ex_ + (4 if side == "R" else -4)
                ex.text(tx, ly - 1, f"{v / total * 100:.0f}%", size=12, weight=700, fill=C["ink"], anchor=anchor)
                ex.text(tx, ly + 12, lab, size=10.5, fill=C["sub"], anchor=anchor)


# ===================================================================================== marimekko


def marimekko(ex, box, columns, seg_names, colors=None, value_fmt=lambda v: f"{v:.0f}%", width_fmt=lambda v: fmt(v),
              min_label=0.06):
    """Variable-width 100% columns: columns [(name, total, [share or value per segment])]. Column width ∝ total,
    segment height ∝ share within column. Segment labels print inside when big enough; legend on top.
    value_fmt receives the segment's SHARE OF ITS COLUMN in percent (0–100), not the raw value; width_fmt receives the
    column total. Returns {name: (x_left, x_right)} for every column plus "_bottom" (y of the column base), so
    annotations line up with the drawn columns: a, _ = r["中国"]; span_bracket(ex, a, b, r["_bottom"] + 6, ...)."""
    from ._marks import legend
    from ._semantics import periods_as_segments
    periods_as_segments(seg_names, "marimekko")
    try:   # value_fmt gets 0–100: a "{:.1%}"-style formatter prints 6170% — fall back to the plain percent label
        probe = re.findall(r"[\d.]+", str(value_fmt(61.7)).replace(",", ""))
        if probe and float(probe[0]) > 100:
            print("marimekko：value_fmt 收到的是 0–100 的占比（不是 0–1），'{:.1%}' 会再乘 100——已改用默认 f'{v:.0f}%'")
            value_fmt = lambda v: f"{v:.0f}%"
    except (TypeError, ValueError):
        pass
    C = ex.C
    if len(columns) < 2 or sum(1 for i in range(len(seg_names)) if any(c[2][i] for c in columns if i < len(c[2]))) < 2:
        raise ValueError("marimekko 需要 ≥2 列、≥2 个有值的分段（宽=规模、高=结构）；数据只有一列或一段时改用 hstack100 / row_table + Bar")
    colors = colors or [C["main"], C["second"], C["accent"], C["light"], C["third"], C["context"]]
    x0, y0, x1, y1 = box
    legend(ex, x0, y0 + 10, [(n, colors[i % len(colors)], "square") for i, n in enumerate(seg_names)], size=10.5)
    top, bottom = y0 + 30, y1 - 34
    T = sum(t for _, t, _ in columns)
    for name, tot, segs in columns:   # segments given as amounts (not shares) must add up to the column width
        s_ = sum(v for v in segs if v)
        if tot and not (95 <= s_ <= 105) and s_ and abs(s_ - tot) > 0.05 * abs(tot):
            raise ValueError(f"marimekko 列「{name}」：分段合计 {s_:g} ≠ 列总量 {tot:g}——分段给占比（合计 100）或给金额"
                             "（合计等于列总量），不要混口径；差额是'其他'就补一段")
    gap = 3
    W = (x1 - x0) - gap * (len(columns) - 1)
    cx = x0
    spans = {}
    for name, tot, segs in columns:
        w = W * tot / T
        spans[name] = (cx, cx + w)
        s = sum(v for v in segs if v)
        yy = bottom
        for i, v in enumerate(segs):
            if not v:
                continue
            h = (bottom - top) * v / s
            col = colors[i % len(colors)]
            ex.rect(cx, yy - h, w, h, col, stroke="#FFFFFF", stroke_width=1, register=False)
            ex.occupy((cx, yy - h, cx + w, yy), "mark", "panel-bg")
            share = v / s
            if share >= min_label and w > tw(value_fmt(share * 100), 10) + 6 and h > 14:
                dark = col not in (C["light"], C["light2"], C["dim"], C["context"])
                ex.text(cx + w / 2, yy - h / 2 + 3.6, value_fmt(share * 100), size=10, fill="#FFFFFF" if dark else C["ink"],
                        anchor="middle")
            yy -= h
        lines_ = wrap(name, 10.5, max(w, 30))
        ex.lines(cx + w / 2, bottom + 15, lines_[:2], size=10.5, anchor="middle")
        if w > tw(width_fmt(tot), 10) + 4:
            ex.text(cx + w / 2, top - 4, width_fmt(tot), size=10, fill=C["sub"], anchor="middle")
        cx += w + gap
    spans["_bottom"] = bottom + 15 + 13 * 2
    return spans


# ===================================================================================== timeline


def timeline(ex, box, events, start, end, ticks=None, tick_fmt=lambda v: f"{v:.0f}", phases=(), focus=None):
    """Horizontal event timeline. events [{"t", "label", "sub"?, "color"?}] alternate above / below the axis with
    stems; phases [(t0, t1, label)] are shaded bands under the axis. Returns x-mapping function."""
    C = ex.C
    x0, y0, x1, y1 = box
    ay = (y0 + y1) / 2 + 10
    pad = 40
    sx = lambda t: x0 + pad + (t - start) / (end - start) * (x1 - x0 - 2 * pad)
    for i, (t0, t1, lab) in enumerate(phases):
        ex.rect(sx(t0), ay - 6, sx(t1) - sx(t0), 12, [C["light"], C["light2"], C["track"]][i % 3], register=False)
        ex.text((sx(t0) + sx(t1)) / 2, ay + 26, lab, size=10.5, weight=700, fill=C["ink"], anchor="middle")
    ex.line(x0 + pad - 10, ay, x1 - pad + 10, ay, stroke=C["axis"], width=1.2, tag="axis", marker="arr")
    for t in (ticks or []):
        ex.line(sx(t), ay - 3, sx(t), ay + 3, stroke=C["axis"], width=0.9, tag="grid")
        ex.text(sx(t), ay + 42 if phases else ay + 16, tick_fmt(t), size=10, fill=C["axis"], anchor="middle")
    levels = [-1, 1, -2, 2]
    last_x = {}
    for i, e in enumerate(sorted(events, key=lambda e: e["t"])):
        px = sx(e["t"])
        col = e.get("color") or (C["accent"] if e.get("highlight") else C["main"])
        if focus is not None and not callable(focus):   # focus=<event dict> / label text
            _f = focus
            focus = lambda e_: e_ is _f or e_ == _f or (isinstance(_f, str) and _f in str(e_.get("label", "")))   # noqa: E731
        if focus is not None and not focus(e):
            col = C["dim"]
        wl = max(tw(e["label"], 11, True), tw(e.get("sub", ""), 10)) + 8
        lvl = next((l for l in levels if px - last_x.get(l, -1e9) > wl), levels[i % 2])
        last_x[lvl] = px
        stem = 34 * abs(lvl) + (0 if lvl < 0 else 14)
        ty = ay - stem if lvl < 0 else ay + stem + (16 if phases else 0)
        ex.line(px, ay, px, ty + (6 if lvl < 0 else -12), stroke=C["context"], width=0.8, tag="leader")
        ex.circle(px, ay, 4.5, col)
        ex.text(px, ty, e["label"], size=11, weight=700, fill=col if col != C["dim"] else C["sub"], anchor="middle")
        if e.get("sub"):
            ex.text(px, ty + 13, e["sub"], size=10, fill=C["sub"], anchor="middle")
    return sx


# ===================================================================================== sankey


def sankey(ex, box, nodes, links, node_w=12, gap=10, label_w=None, value_fmt=lambda v: fmt(v), focus=None):
    """Conserved flows between 2–4 stages. nodes: [{"id", "label", "stage" (0..n), "color"?}];
    links: [(src_id, dst_id, value)]. Node height ∝ throughput; links are smooth ribbons in the source colour
    (or dimmed if focus(link) is False). Labels: stage 0 on the left, last stage on the right, middle above."""
    C = ex.C
    x0, y0, x1, y1 = box
    stages = sorted({n["stage"] for n in nodes})
    by_id = {n["id"]: dict(n) for n in nodes}
    for n in by_id.values():
        n["in"] = sum(v for s, d, v in links if d == n["id"])
        n["out"] = sum(v for s, d, v in links if s == n["id"])
        n["val"] = max(n["in"], n["out"])
    lab_l = label_w or max([tw(n["label"], 10.5, True) for n in by_id.values() if n["stage"] == stages[0]] + [0]) + 10
    lab_r = label_w or max([tw(n["label"], 10.5, True) for n in by_id.values() if n["stage"] == stages[-1]] + [0]) + 10
    lab_r += max(tw(value_fmt(n["val"]), 10) for n in by_id.values()) + 6
    px0, px1 = x0 + lab_l, x1 - lab_r - node_w
    sx = {st: px0 + (px1 - px0) * i / max(len(stages) - 1, 1) for i, st in enumerate(stages)}
    H = y1 - y0 - 10
    scale = min((H - gap * (sum(1 for n in by_id.values() if n["stage"] == st) - 1)) /
                max(sum(n["val"] for n in by_id.values() if n["stage"] == st), 1e-9) for st in stages)
    palette = [C["main"], C["accent"], C["second"], C["third"], C["light"], C["context"]]
    for st in stages:
        col_nodes = [n for n in nodes if n["stage"] == st]
        tot = sum(by_id[n["id"]]["val"] for n in col_nodes) * scale + gap * (len(col_nodes) - 1)
        yy = y0 + 5 + (H - tot) / 2
        for i, n in enumerate(col_nodes):
            m = by_id[n["id"]]
            m["x"], m["y"], m["h"] = sx[st], yy, m["val"] * scale
            m["color"] = n.get("color") or palette[i % len(palette)]
            m["oy"], m["iy"] = yy, yy
            yy += m["h"] + gap
    for s_, d_, v in links:
        a, b = by_id[s_], by_id[d_]
        h = v * scale
        col = a["color"] if (focus is None or focus((s_, d_, v))) else C["dim"]
        xa, xb = a["x"] + node_w, b["x"]
        ya0, yb0 = a["oy"], b["iy"]
        a["oy"] += h
        b["iy"] += h
        mx = (xa + xb) / 2
        d = (f"M{xa:.1f},{ya0:.1f} C{mx:.1f},{ya0:.1f} {mx:.1f},{yb0:.1f} {xb:.1f},{yb0:.1f} "
             f"L{xb:.1f},{yb0 + h:.1f} C{mx:.1f},{yb0 + h:.1f} {mx:.1f},{ya0 + h:.1f} {xa:.1f},{ya0 + h:.1f} Z")
        ex.path(d, fill=col, opacity=0.32, register=False)
    for n in by_id.values():
        ex.rect(n["x"], n["y"], node_w, n["h"], n["color"])
        cy = n["y"] + n["h"] / 2
        if n["stage"] == stages[0]:
            ex.text(n["x"] - 6, cy + 1, n["label"], size=10.5, weight=700, fill=C["ink"], anchor="end")
            ex.text(n["x"] - 6, cy + 13, value_fmt(n["val"]), size=10, fill=C["sub"], anchor="end")
        elif n["stage"] == stages[-1]:
            ex.text(n["x"] + node_w + 6, cy + 4, n["label"], size=10.5, weight=700, fill=C["ink"])
            ex.text(n["x"] + node_w + 10 + tw(n["label"], 10.5, True), cy + 4, value_fmt(n["val"]), size=10,
                    fill=C["sub"])
        else:
            ex.text(n["x"] + node_w + 6, cy + 1, n["label"], size=10.5, weight=700, fill=C["ink"])
            ex.text(n["x"] + node_w + 6, cy + 13, value_fmt(n["val"]), size=10, fill=C["sub"])
    return by_id


# ===================================================================================== sensitivity (tornado)


def tornado(ex, box, base, rows, base_label=None, value_fmt=lambda v: fmt(v), low_color=None, high_color=None,
            threshold=None, threshold_label=None, label_w=None):
    """Sensitivity tornado: one bar per driver from the base outcome to the outcome at the driver's low / high case.

    rows: [(driver, low_case_text, outcome_at_low, high_case_text, outcome_at_high)], sorted widest first automatically;
    bars below the base use low_color (grey), above use high_color (main), whichever input case produced them.
    base: outcome under the base assumptions (vertical line). threshold: break-even / hurdle line (e.g. IRR 8%, NPV 0)
    — drivers whose bar crosses it are the ones that can flip the decision. Returns the x-scale function.
    """
    C = ex.C
    x0, y0, x1, y1 = box
    lc, hc = low_color or C["context"], high_color or C["main"]
    zh = any(has_cjk(r[0]) for r in rows)  # label language follows the driver names
    base_label = base_label if base_label is not None else ("基准" if zh else "Base")
    rows = sorted(rows, key=lambda r: -abs(r[4] - r[2]))
    spread = [v for r in rows for v in (r[2], r[4])] + [base]
    span = (max(spread) - min(spread)) or 1
    far = threshold is not None and (threshold < min(spread) - 0.35 * span or threshold > max(spread) + 0.35 * span)
    if far:  # hurdle far outside every case: say so instead of squeezing the bars to make room for the line
        hi_ = threshold < min(spread)
        t_ = threshold_label or value_fmt(threshold)
        note = (f"所有情景均{'高于' if hi_ else '低于'}{t_}" if zh else f"All cases {'above' if hi_ else 'below'} {t_}")
        threshold = None
    lw = label_w or min(max(tw(r[0], 11, True) for r in rows) + 10, (x1 - x0) * 0.3)
    vals = [base] + [v for r in rows for v in (r[2], r[4])] + ([threshold] if threshold is not None else [])
    lo, hi = min(vals), max(vals)
    lab = (lambda txt, v: (f"{value_fmt(v)}（{txt}）" if zh else f"{value_fmt(v)} ({txt})") if txt else value_fmt(v))  # noqa: E731
    room_l = max([tw(lab(r[1], r[2]), 10) for r in rows if r[2] < base] + [tw(lab(r[3], r[4]), 10) for r in rows if r[4] < base] + [0]) + 8
    room_r = max([tw(lab(r[1], r[2]), 10) for r in rows if r[2] >= base] + [tw(lab(r[3], r[4]), 10) for r in rows if r[4] >= base] + [0]) + 8
    head = 30
    ax0, ax1 = x0 + lw + room_l, x1 - room_r
    if hi - lo < 1e-9:
        hi = lo + 1
    sx = lambda v: ax0 + (v - lo) / (hi - lo) * (ax1 - ax0)  # noqa: E731
    rh = min((y1 - y0 - head - 20) / len(rows), 80)
    bh = min(rh * 0.56, 34)
    ex.text(sx(base), y0 + 12, f"{base_label} {value_fmt(base)}", size=10.5, weight=700, fill=C["ink"], anchor="middle")
    for i, (name, lt, lv, ht, hv) in enumerate(rows):
        cy = y0 + head + i * rh + rh / 2
        ex.text(x0 + lw - 8, cy + 4, name, size=11, weight=700, fill=C["ink"], anchor="end")
        for txt, v in ((lt, lv), (ht, hv)):
            col = hc if v >= base else lc
            a, b = sorted((sx(base), sx(v)))
            ex.rect(a, cy - bh / 2, max(b - a, 1.5), bh, col)
            right = v >= base
            label = lab(txt, v)
            lx = sx(v) + (5 if right else -5)
            if threshold is not None and right and v < threshold < v + 1e9 and sx(threshold) < lx + tw(label, 10) + 4:
                lx = max(lx, sx(threshold) + 5)
            if threshold is not None and not right and threshold < v and sx(threshold) > lx - tw(label, 10) - 4:
                lx = min(lx, sx(threshold) - 5)
            ex.text(lx, cy + 4, label, size=10, fill=C["sub"], anchor="start" if right else "end")
    bottom = y0 + head + len(rows) * rh
    ex.line(sx(base), y0 + 18, sx(base), bottom, stroke=C["ink"], width=1.1, tag="grid")
    if far:
        ex.text(sx(base), bottom + 14, note, size=10, weight=700, fill=C["accent"], anchor="middle")
    if threshold is not None:
        ex.line(sx(threshold), y0 + 18, sx(threshold), bottom, stroke=C["accent"], width=1.1, dash="4,3", tag="grid")
        if threshold_label:
            ex.text(sx(threshold), bottom + 14, threshold_label, size=10, weight=700, fill=C["accent"], anchor="middle")
    return sx
