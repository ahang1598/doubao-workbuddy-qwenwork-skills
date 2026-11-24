"""More consulting charts: slope, bullet, pareto, small multiples, fan (scenario) forecast, treemap."""

from __future__ import annotations

import math
import re
from numbers import Real

from ._axes import Axes, NAxes, nice_ticks
from ._marks import polyline, vertex_dots
from ._text import fmt, has_cjk, tw, wrap


def _zh(ex, *texts):
    return bool(ex.body_lang) and any(has_cjk(t) for t in texts if t)


# ===================================================================================== slope


def slope(ex, box, items, left_label, right_label, value_fmt=lambda v: fmt(v), focus=None, rank=False, size=11):
    """Slope chart: each item is a line from its left value to its right value (two periods / two scenarios).

    items: [(name, left, right)]. rank=True plots rank positions (1 = top) instead of values. focus: callable(name)
    -> bool, highlighted lines in accent/main, others grey. Labels sit on both ends ("name  value"), de-overlapped.
    Returns (sy, x_left, x_right).
    """
    if len(items) < 3:
        if len(items) < 2:
            raise ValueError("slope 只有 1 个对象——用 big_number + 差值一句话（如 '2023→2025 +3.6pp'）")
        rows_ = ", ".join(f"dict(label={n!r}, a={a!r}, b={b!r})" for n, a, b in list(items)[:2])
        raise ValueError(f"slope 少于 3 个对象（收到 {len(items)} 个）——两期对比改用 dumbbell_table（每项一行、差值自动标），直接可用：\n"
                         f"  row_table(ex, ex.body, [{rows_}], [Label('label'), Dumbbell([('a', {left_label!r}, ex.C['context'], 'ring'), "
                         f"('b', {right_label!r}, ex.C['main'], 'dot')], delta=True)])\n"
                         "exhibit_help('dumbbell_table') 看完整方案")
    C = ex.C
    x0, y0, x1, y1 = box
    if rank:
        lo_r = {n: i + 1 for i, (n, a, b) in enumerate(sorted(items, key=lambda t: -t[1]))}
        hi_r = {n: i + 1 for i, (n, a, b) in enumerate(sorted(items, key=lambda t: -t[2]))}
        items = [(n, lo_r[n], hi_r[n]) for n, a, b in items]
        value_fmt = lambda v: f"#{v:.0f}"  # noqa: E731
    lw = max(tw(f"{n}  {value_fmt(a)}", size, True) for n, a, b in items) + 10
    rw = max(tw(f"{value_fmt(b)}  {n}", size, True) for n, a, b in items) + 10
    xl, xr = x0 + lw, x1 - rw
    head = 26
    vals = [v for _, a, b in items for v in (a, b)]
    lo, hi = min(vals), max(vals)
    if rank:
        lo, hi = hi + 0.5, lo - 0.5
    pad = (hi - lo) * 0.04 or 1
    sy = lambda v: y0 + head + (hi + pad - v) / ((hi - lo) + 2 * pad) * (y1 - y0 - head - 6)  # noqa: E731
    ex.text(xl, y0 + 14, left_label, size=size, weight=700, fill=C["ink"], anchor="middle")
    ex.text(xr, y0 + 14, right_label, size=size, weight=700, fill=C["ink"], anchor="middle")
    ex.line(xl, y0 + head - 4, xl, y1, stroke=C["grid"], width=0.8, tag="grid")
    ex.line(xr, y0 + head - 4, xr, y1, stroke=C["grid"], width=0.8, tag="grid")
    ends_l, ends_r = [], []
    hl = [C["accent"], C["main"], C["second"]]
    k = 0
    for n, a, b in items:
        on = focus(n) if focus else True
        col = (hl[k % len(hl)] if focus else C["main"]) if on else C["context"]
        k += 1 if (on and focus) else 0
        ex.line(xl, sy(a), xr, sy(b), stroke=col, width=2.2 if on else 1.2, tag="series", whole=True)
        ex.circle(xl, sy(a), 3.5, col)
        ex.circle(xr, sy(b), 3.5, col)
        ends_l.append([sy(a), f"{n}  {value_fmt(a)}", col, on])
        ends_r.append([sy(b), f"{value_fmt(b)}  {n}", col, on])
    for ends, x, anchor in ((ends_l, xl - 8, "end"), (ends_r, xr + 8, "start")):
        ends.sort()
        for j in range(1, len(ends)):
            if ends[j][0] - ends[j - 1][0] < size * 1.35:
                ends[j][0] = ends[j - 1][0] + size * 1.35
        for py, t, col, on in ends:
            ex.text(x, py + size * 0.36, t, size=size, weight=700 if on else 400, fill=col if on else C["sub"],
                    anchor=anchor)
    if focus and k:
        ex.notes += 1
    return sy, xl, xr


# ===================================================================================== bullet


def bullet(ex, box, rows, value_fmt=lambda v: fmt(v), domain=None, ranges_label=None, target_label=None, size=11):
    """Bullet chart: actual vs target against qualitative bands, one row per KPI / object.

    rows: [dict(label, actual, target, bands=(poor, ok, good))] — bands are upper bounds of grey zones (dark→light).
    Actual = thick bar (accent when it misses the target, main otherwise); target = vertical tick.
    Bands must be three strictly increasing, nonempty benchmark zones, not fabricated from the target.
    With only actual and target, use columns (exhibit_help('target_columns')).
    domain: shared scale (lo, hi) — otherwise per-row scale up to the last band. Returns row centres.
    """
    if len(rows) < 2:
        raise ValueError("bullet 只有 1 行——改用 big_number + 目标/差距的一句话，或把同口径的几个 KPI 放进同一张 bullet")
    import math
    from numbers import Real

    if domain is not None and (len(domain) != 2 or
                               not all(isinstance(value, Real) and math.isfinite(value) for value in domain) or
                               domain[0] >= domain[1]):
        raise ValueError("bullet domain 必须是有限数值 lo < hi")
    for row in rows:
        bands = row.get("bands")
        values = [row.get("actual"), row.get("target")]
        if not isinstance(bands, (tuple, list)) or len(bands) != 3 or not all(
                isinstance(value, Real) and math.isfinite(value) for value in values + list(bands)):
            raise ValueError("bullet：actual/target 必须为有限数值，bands 必须有三个有限的基准区间上界")
        lo, hi = domain or (0, max(bands[-1], *values))
        if not lo < bands[0] < bands[1] < bands[2] <= hi or any(value < lo or value > hi for value in values):
            raise ValueError("bullet：基准区间必须有三个非空且递增的区间，并容纳实绩与目标；"
                             "不要用 (0, target, target) 凑 bands。只有实绩＋目标用 exhibit_help('target_columns')")
    C = ex.C
    x0, y0, x1, y1 = box
    lw = max(tw(r["label"], size, True) for r in rows) + 12
    vw = max(tw(value_fmt(r["actual"]), size, True) for r in rows) + 12
    head = max(20, size + 8)
    rh = min((y1 - y0 - head) / len(rows), 56)
    greys = ["#D4D4D4", "#E3E3E3", "#F0F0F0"]
    out = []
    if ranges_label or target_label:
        ex.text(x0 + lw, y0 + 12, ranges_label or "", size=10, fill=C["sub"])
        if target_label:
            ex.text(x1 - vw, y0 + 12, f"| {target_label}", size=10, weight=700, fill=C["ink"], anchor="end")
    for i, r in enumerate(rows):
        cy = y0 + head + i * rh + rh / 2
        lo, hi = domain or (0, max(r["bands"][-1], r["actual"], r["target"]))
        a, b = x0 + lw, x1 - vw
        sx = lambda v: a + (v - lo) / ((hi - lo) or 1) * (b - a)  # noqa: E731
        bh = min(rh * 0.62, 26)
        prev = lo
        for g, ub in zip(greys, r["bands"]):
            ex.rect(sx(prev), cy - bh / 2, sx(ub) - sx(prev), bh, g, register=False)
            prev = ub
        miss = r["actual"] < r["target"]
        ex.rect(sx(lo), cy - bh * 0.18, sx(r["actual"]) - sx(lo), bh * 0.36, C["accent"] if miss else C["main"])
        tx = sx(r["target"])
        ex.line(tx, cy - bh * 0.42, tx, cy + bh * 0.42, stroke=C["ink"], width=2.4, tag="grid")
        target_text = value_fmt(r["target"])
        half_width = tw(target_text, size, True) / 2 + 2
        target_x = min(b - half_width, max(a + half_width, tx))
        ex.text(target_x, cy - bh / 2 - 4, target_text, size=size, weight=700, fill=C["ink"], anchor="middle")
        ex.text(x0 + lw - 8, cy + size * 0.36, r["label"], size=size, weight=700, fill=C["ink"], anchor="end")
        ex.text(b + 8, cy + size * 0.36, value_fmt(r["actual"]), size=size, weight=700,
                fill=C["accent"] if miss else C["ink"])
        out.append(cy)
    ex.notes += 1
    return out


# ===================================================================================== pareto


def pareto(ex, box, items, value_fmt=lambda v: fmt(v), cut=0.8, top_n=None, ylabel=None, size=10.5):
    """Pareto: bars sorted descending + cumulative share line (right scale, 0–100%) + a marker where the
    cumulative share crosses `cut` (e.g. "前 4 项 = 80%"; cut=0.67 etc. to match the title's CR-n). items: [(name, value)].
    Returns index of the cut item; ex.pareto_bands[name] = (x0, x1, bar_top) after sorting — anchor extra brackets /
    callouts on these, never on hand-typed coordinates."""
    C = ex.C
    import re as _re
    # "其他客户" / "其余 12 家" / "Others" / "长尾" are buckets: always last, never counted as a top item
    rest = lambda n: bool(_re.match(r"\s*(?:其他|其它|其余|剩余|长尾|others?\b|rest\b|other\b|remaining\b|long tail\b)",  # noqa: E731
                                    str(n), _re.I))
    items = sorted([t for t in items if not rest(t[0])], key=lambda t: -t[1]) + [t for t in items if rest(t[0])]
    total = sum(v for _, v in items) or 1
    x0, y0, x1, y1 = box
    ax = Axes.fit(ex, (x0, y0, x1 - 34, y1), max(v for _, v in items), label_rows=2)
    ax.grid(labels=True)
    bands = ax.bands(len(items), pad=0.28)
    cum, pts, k_cut = 0, [], None
    for i, ((n, v), (bx, bw)) in enumerate(zip(items, bands)):
        cum += v
        share = cum / total
        if k_cut is None and share >= cut - 1e-9 and not rest(n):   # "其他" is a bucket, never a top item
            k_cut = i
        on = (k_cut is None or i <= k_cut) and not rest(n)
        ex.rect(bx, ax.sy(v), bw, ax.sy(0) - ax.sy(v), C["main"] if on else C["context"])
        pts.append((bx + bw / 2, ax.y + ax.h * (1 - share)))
    ax.xlabels([b[0] + b[1] / 2 for b in bands], [n for n, _ in items], size=size)
    xr = ax.x + ax.w
    for t in (0, 0.5, 1.0):
        ex.text(xr + 6, ax.y + ax.h * (1 - t) + 4, f"{t:.0%}", size=10, fill=C["axis"])
    for start, end in zip(pts, pts[1:]):
        ex.line(*start, *end, stroke=C["accent"], width=2, tag="series", whole=True)
    for p, q in pts:
        ex.circle(p, q, 2.6, C["accent"])
    if k_cut is not None:
        cx = bands[k_cut][0] + bands[k_cut][1] + bands[0][1] * 0.14
        ex.line(cx, ax.y, cx, ax.y + ax.h, stroke=C["ink"], width=0.9, dash="4,3", tag="grid")
        zh = _zh(ex, items[0][0])
        lab = (f"前 {k_cut + 1} 项 = {sum(v for _, v in items[:k_cut + 1]) / total:.0%}" if zh else
               f"Top {k_cut + 1} = {sum(v for _, v in items[:k_cut + 1]) / total:.0%}")
        from ._marks import _clear_whole_lines
        from ._page import lint_w
        label_width = max(tw(lab, 11.5, True), lint_w(lab, 11.5, True))
        label_x, label_y = _clear_whole_lines(ex, cx + 6 + label_width / 2, ax.y + ax.h * 0.55 - 4,
                                             label_width / 2, 8, "pareto label")
        ex.text(label_x - label_width / 2, label_y + 4, lab, size=11.5, weight=700, fill=C["ink"])
        ex.notes += 1
    ex.pareto_bands = {n: (bx, bx + bw, ax.sy(v)) for (n, v), (bx, bw) in zip(items, bands)}   # name → (x0, x1, top)
    return k_cut


# ===================================================================================== small multiples


_PERIOD = re.compile(r"^\s*(?:(?:19|20)\d{2}(?:\s*(?:年|E|F|A|H[12]|Q[1-4]|年?[上下]半年|年?\d{1,2}月|年?Q[1-4]))?"
                     r"|FY\s*\d{2,4}|[1-4]Q\d{0,4}|Q[1-4](?:\s*\d{2,4})?|[12]H\d{0,4}|H[12](?:\s*\d{2,4})?"
                     r"|\d{1,2}月|W\d{1,2}|[上下]半年|去年|上年|今年|本年|同期|本期|上期|实际|目标|预算|计划"
                     r"|AC|PY|PL|BU|FC)\s*$", re.I)


def _is_periods(x):
    """True when the x values are periods / scenarios (years, quarters, months, AC/PY/PL…): adding them is meaningless."""
    return bool(x) and all(_PERIOD.match(f"{v:.0f}" if isinstance(v, (int, float)) and float(v).is_integer() else str(v))
                           for v in x)


def small_multiples(ex, box, panels, x, cols=None, value_fmt=lambda v: fmt(v), shared=None, highlight=None,
                    size=10.5, kind="line", focus_x=None, unit=None, base="prev", ref=None, kpi=None):
    """Grid of small charts (same x; same y when the series are of similar size, else each panel its own y —
    force with shared=True/False) — compare many series / objects at once.

    ref=(value, "label"): one baseline drawn through every panel at the same height (McKinsey "疫情前 = 100"): forces
    a shared scale on one row of panels, the label once at the left end. kpi="last" | "change" | [text per panel]:
    one big number per panel under its title (the reading the panel proves: last value, change vs base, or your
    own computed text) instead of the small header figure.

    panels: [(title, ys)] or [(title, ys, color)]. highlight: callable(title) -> bool (others in context grey).
    kind="line" (default): trend shape per panel, header shows last value and its change (needs ≥ 4 points).
    x: numeric values retain their distances; non-empty string labels use equal spacing and keep endpoint labels.
    base: what the header change compares the last value with — "prev" (default: the previous value, period over
    period, e.g. 2025H1 vs 2024H1 when x are half-years of successive years — match the subtitle's 同比/环比) or
    "first" (the first value of the series, i.e. change over the whole span).
    kind="column": vertical bars per period x (≥ 3), same header; kind="bar": horizontal bars per category x
    (category names on the left of each row's panel, values at bar ends), header shows the panel total — only for
    additive categories: no total when x are periods / scenarios (2024, Q1, AC/PY…) or unit is a rate (%, pt).
    Every panel with < 3 values raises (two periods: row_table / dumbbell_table).
    unit: the series unit; a rate unit (%, pt, pp) writes the header change in pt (last − base), not %.
    Line / column panels print their first and last values on the chart; with own scales (shared=False) every panel
    still starts its y axis at 0 and keeps the zero line at the same height, so baselines stay level.
    focus_x: callable(x_value) -> bool — column/bar kinds draw those periods/categories in accent (e.g. 我方).
    Returns list of panel boxes.
    """
    from ._kpi import FLAT, RATE_UNITS
    C = ex.C
    from ._page import chart_box as _cbx
    box = _cbx(ex, box)
    if kind not in ("line", "column", "bar"):
        raise ValueError(f"small_multiples: kind={kind!r} 只能是 'line' | 'column' | 'bar'")
    if base not in ("prev", "first"):
        raise ValueError(f"small_multiples: base={base!r} 只能是 'prev'（对上一期，默认）| 'first'（对首期）")
    if kind == "line":
        if not panels:
            raise ValueError("small_multiples: line 的 panels 不能为空")
        if x is None or len(x) == 0:
            raise ValueError("small_multiples: line 的 x 不能为空")
        if not (all(isinstance(value, str) and value.strip() for value in x)
                or all(isinstance(value, Real) for value in x)):
            raise ValueError("small_multiples: line 的 x 必须全部是数值或全部是非空字符串标签")
    n = len(panels)
    if panels and all(sum(v is not None for v in p[1]) < 3 for p in panels):
        raise ValueError("small_multiples: 每格少于 3 期读不出走势：改 row_table 或 dumbbell_table（两期对比每项一行，差值自动标）")
    rate = str(unit or "").strip() in RATE_UNITS
    flat = FLAT if ex.body_lang else "Flat"
    need = 4 if kind == "line" else 2
    short = [p[0] for p in panels if sum(v is not None for v in p[1]) < need]
    if short:
        raise ValueError(f"small_multiples: {short} 少于 4 个时点，看不出形状——改用 slope（两期）或 dumbbell_table"
                         if kind == "line" else f"small_multiples: {short} 少于 2 个值，改用 row_table")
    bad = [p[0] for p in panels if len(p[1]) != len(x)]
    if bad:
        raise ValueError(f"small_multiples: {bad} 的值个数与 x（{len(x)} 个）不一致")
    cols = cols or (n if n <= 4 else (3 if n <= 9 else 4))
    rows = (n + cols - 1) // cols
    x0, y0, x1, y1 = box
    gx, gy = 26, 22
    pw, ph = (x1 - x0 - gx * (cols - 1)) / cols, (y1 - y0 - gy * (rows - 1)) / rows
    allv = [v for p in panels for v in p[1] if v is not None]
    if ref is not None:
        if not (isinstance(ref, (tuple, list)) and len(ref) == 2 and isinstance(ref[0], (int, float))):
            raise ValueError("small_multiples(ref=)：写 (数值, '标签')，如 ref=(100, '疫情前=100')")
        if kind == "bar":
            raise ValueError("small_multiples(ref=)：基准线只用于 kind='line' / 'column'（同一时间轴）")
        allv = allv + [ref[0]]
        shared = True   # one line through every panel means one scale
    glo, ghi = min(0, min(allv)), max(allv) * (1.06 if ref is not None else 1)
    if shared is None:  # one scale only when panels are comparable in size; otherwise small series get flattened
        peaks = [max(v for v in p[1] if v is not None) for p in panels]
        shared = max(peaks) <= 4 * max(min(peaks), 1e-9)
    zero_f = 0.0   # own scales: the zero line sits at the same height in every panel (baselines level across a row)
    if not shared and kind != "bar":
        for p in panels:
            vs_ = [v for v in p[1] if v is not None]
            lo_, hi_ = min(0, min(vs_)), max(0, max(vs_))
            if hi_ > lo_:
                zero_f = max(zero_f, -lo_ / (hi_ - lo_))
        zero_f = min(zero_f, 0.95)
    kpis_ = None
    if kpi is not None:
        if isinstance(kpi, (list, tuple)):
            if len(kpi) != n:
                raise ValueError(f"small_multiples(kpi=)：{len(kpi)} 个文字，面板有 {n} 个")
            kpis_ = [str(k) for k in kpi]
        elif kpi in ("last", "change"):
            kpis_ = []
            for p in panels:
                ys_ = p[1]
                last_ = next(v for v in reversed(ys_) if v is not None)
                b_ = _sm_base(ys_, base)
                if kpi == "last" or b_ is None:
                    kpis_.append(value_fmt(last_))
                elif rate:
                    from ._kpi import pt_text
                    kpis_.append(pt_text(last_ - b_, zh=bool(ex.body_lang)))
                else:
                    c_ = (last_ / b_ - 1) if b_ else 0
                    kpis_.append(flat if abs(c_) < 0.005 else f"{'+' if c_ > 0 else '−'}{abs(c_):.0%}")
        else:
            raise ValueError("small_multiples(kpi=)：'last' | 'change' | [每格一个文字]")
    top_extra = 26 if kpis_ else 0
    xl = [f"{v:.0f}" if isinstance(v, (int, float)) and float(v).is_integer() else str(v) for v in x]
    cat_w = (max(tw(t, 10) for t in xl) + 6) if kind == "bar" else 0
    boxes = []
    for i, p in enumerate(panels):
        title, ys = p[0], p[1]
        r_, c_ = divmod(i, cols)
        bx0, by0 = x0 + c_ * (pw + gx), y0 + r_ * (ph + gy)
        lo, hi = (glo, ghi) if shared else (min(0, min(v for v in ys if v is not None)), max(v for v in ys if v is not None))
        if not shared and zero_f > 0 and kind != "bar":
            hi = max(hi, 0)
            if hi > 0:
                lo = min(lo, -zero_f * hi / (1 - zero_f))
                if lo < 0 and -lo / (hi - lo) < zero_f - 1e-9:
                    hi = -lo * (1 - zero_f) / zero_f
            elif lo < 0:
                hi = -lo * (1 - zero_f) / zero_f
        on = highlight(title) if highlight else True
        col = (p[2] if len(p) > 2 else C["main"]) if on else C["context"]
        ex.text(bx0, by0 + 12, title, size=size + 0.5, weight=700, fill=C["ink"] if on else C["sub"])
        last = next(v for v in reversed(ys) if v is not None)
        first = _sm_base(ys, base)
        if kind == "bar":   # a total only adds up additive categories — never two periods or a rate (客座率 161)
            head = "" if (rate or _is_periods(x)) else value_fmt(sum(v for v in ys if v is not None))
        elif first is None:
            head = value_fmt(last)
        elif rate:
            from ._kpi import pt_text
            head = f"{value_fmt(last)}  {pt_text(last - first, zh=bool(ex.body_lang))}"
        else:
            chg = (last / first - 1) if first else 0
            head = f"{value_fmt(last)}  " + (flat if abs(chg) < 0.005 else f"{'+' if chg > 0 else '−'}{abs(chg):.0%}")
        if kpis_:   # one big reading per panel (the panel's proof), replacing the small header figure
            from ._page import SERIF
            ex.text(bx0, by0 + 12 + 26, kpis_[i], size=20, weight=700, family=SERIF,
                    fill=(C["neg"] if kpis_[i].startswith(("−", "-")) else col) if on else C["sub"])
            ex.notes += 1
        elif head:
            ex.text(bx0 + pw, by0 + 12, head, size=size, weight=700, fill=col if on else C["sub"], anchor="end")
        if kind == "line":
            ay = _sm_line(ex, bx0, by0 + top_extra, pw, ph - top_extra, x, ys, lo, hi, col, value_fmt, on)
        elif kind == "column":
            ay = _sm_column(ex, bx0, by0 + top_extra, pw, ph - top_extra, x, xl, ys, lo, hi, col, on, focus_x, value_fmt)
        else:
            ay = _sm_bar(ex, bx0, by0, pw, ph, x, xl, ys, lo, hi, col, on, focus_x, value_fmt, cat_w)
        if ref is not None and ay:   # the same baseline height in every panel of the row (shared scale)
            a0, a1 = ay
            yr = a1 - (ref[0] - lo) / ((hi - lo) or 1) * (a1 - a0)
            ex.line(bx0, yr, bx0 + pw + (gx / 2 if c_ < cols - 1 else 0), yr, stroke=C["ink"], width=1.2,
                    dash="5,3", tag="ref")
            if c_ == cols - 1 and ref[1]:   # the label once, at the right end of the row
                ex.text(bx0 + pw, yr - 4, str(ref[1]), size=10, weight=700, fill=C["ink"], anchor="end")
            ex.notes += 1
        boxes.append((bx0, by0, bx0 + pw, by0 + ph))
    if kind != "bar":   # title check: growth per panel (base → last, same as the header) and each panel's series
        from ._page import add_fact, growth_items
        g = growth_items([p[0] for p in panels], [_sm_base(p[1], base) for p in panels],
                         [next((v for v in reversed(p[1]) if v is not None), None) for p in panels])
        if isinstance(kpi, (list, tuple)):
            # the big number per panel is the author's reading (年度 YoY, not first→last quarter): the title quotes it,
            # so growth is those rates when every panel's is a signed %, else nothing
            rates = [re.fullmatch(r"\s*([+\-−]?\d+(?:\.\d+)?)\s*%\s*", str(k)) for k in kpi]
            g = [(str(p[0]), float(m.group(1).replace("−", "-")) / 100, float(m.group(1).replace("−", "-")))
                 for p, m in zip(panels, rates)] if all(rates) else []
        if len(g) >= 2:
            add_fact(ex, {"kind": "growth", "items": g})
        if len(panels) == 1 and len(x) >= 3:
            add_fact(ex, {"kind": "series", "name": str(panels[0][0]), "values": list(panels[0][1]),
                          "periods": [str(v) for v in xl]})
    return boxes


def _sm_base(ys, base="prev"):
    """The value the header change compares the last value with: the previous non-empty value (base="prev") or the
    first one (base="first"); None when the series has no earlier value."""
    vals = [v for v in ys if v is not None]
    if len(vals) < 2:
        return None
    return vals[0] if base == "first" else vals[-2]


def _sm_line(ex, bx0, by0, pw, ph, x, ys, lo, hi, col, value_fmt=None, on=True):
    """Area line per panel; the first and last points carry their values (a small multiple without readings shows
    a shape the reader cannot quote)."""
    C = ex.C
    ay0, ay1 = by0 + 24, by0 + ph - 18
    positions = range(len(x)) if isinstance(x[0], str) else x
    sx = lambda v, a=bx0: a + (v - positions[0]) / ((positions[-1] - positions[0]) or 1) * pw  # noqa: E731
    syf = lambda v, a=ay0, b=ay1, l=lo, h=hi: b - (v - l) / ((h - l) or 1) * (b - a)  # noqa: E731
    base = syf(0) if lo < 0 <= hi else ay1   # the axis is the zero line (level across panels with own scales)
    ex.line(bx0, base, bx0 + pw, base, stroke=C["axis"], width=0.8, tag="axis")
    pts = [(sx(xv), syf(v)) for xv, v in zip(positions, ys) if v is not None]
    area = [(pts[0][0], base)] + pts + [(pts[-1][0], base)]
    ex.path("M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in area) + " Z", fill=col, opacity=0.12, register=False)
    for start, end in zip(pts, pts[1:]):
        ex.line(*start, *end, stroke=col, width=2, tag="series", whole=True)
    ex.occupy((bx0, ay0, bx0 + pw, ay1), "mark", "panel-bg")
    vertex_dots(ex, pts[:-1], col, r=2.4, width=1.2, register=False)
    ex.circle(pts[-1][0], pts[-1][1], 2.8, col, register=False)
    if value_fmt is not None:
        vals = [v for v in ys if v is not None]
        _sm_end_label(ex, pts[0], pts[1] if len(pts) > 1 else None, value_fmt(vals[0]), "start", by0, ay1, on)
        _sm_end_label(ex, pts[-1], pts[-2] if len(pts) > 1 else None, value_fmt(vals[-1]), "end", by0, ay1, on,
                      bold=True)
    ex.text(bx0, ay1 + 14, f"{x[0]:.0f}" if isinstance(x[0], (int, float)) else str(x[0]), size=10,
            fill=C["axis"])
    ex.text(bx0 + pw, ay1 + 14, f"{x[-1]:.0f}" if isinstance(x[-1], (int, float)) else str(x[-1]), size=10,
            fill=C["axis"], anchor="end")
    return ay0, ay1


def _sm_end_label(ex, pt, nb, text, anchor, by0, ay1, on, bold=False, size=10):
    """Value at an end point of a panel line: above the point when the line leaves it downwards (and the panel
    header leaves room), else below — never on the segment that runs from it."""
    C = ex.C
    x, y = pt
    rising = nb is not None and nb[1] < y   # neighbour higher on the page: the line climbs away above the point
    above_ok = y - 5 - size >= by0 + 16
    below_ok = y + 5 + size <= ay1 - 2
    above = (not rising and above_ok) or not below_ok
    ty = y - 5 if above else y + 5 + size * 0.8
    x += 3 if anchor == "start" else -3   # inside the panel's area shape: a label poking past its edge is blocked
    ex.text(x, ty, text, size=size, weight=700 if bold else 400, fill=(C["ink"] if bold else C["text"]) if on else C["sub"],
            anchor=anchor)


def _sm_column(ex, bx0, by0, pw, ph, x, xl, ys, lo, hi, col, on, focus_x, value_fmt):
    """Vertical bars per period on the panel's (shared) scale; first and last values labelled, first/last period under the axis
    (every period when the labels fit)."""
    C = ex.C
    ay0, ay1 = by0 + 24 + 13, by0 + ph - 18
    m = len(x)
    step = pw / m
    bw = step * 0.68
    syf = lambda v: ay1 - (v - lo) / ((hi - lo) or 1) * (ay1 - ay0)  # noqa: E731
    base = syf(0) if lo <= 0 <= hi else ay1
    fits = all(tw(t, 10) + 4 <= step for t in xl)
    for k, (xv, v) in enumerate(zip(x, ys)):
        cx = bx0 + step * k + step / 2
        if v is not None:
            c = C["accent"] if (on and focus_x and focus_x(xv)) else col
            yv = syf(v)
            ex.rect(cx - bw / 2, min(yv, base), bw, max(abs(base - yv), 1), c)
            if k in (0, m - 1) or (on and focus_x and focus_x(xv)):
                ex.text(cx, (yv - 4) if v >= 0 else (yv + 12), value_fmt(v), size=10, weight=700,
                        fill=C["ink"] if on else C["sub"], anchor="middle")
        if fits or k in (0, m - 1):
            anc = "middle" if fits else ("start" if k == 0 else "end")
            tx = cx if fits else (bx0 if k == 0 else bx0 + pw)
            ex.text(tx, ay1 + 14, xl[k], size=10, fill=C["axis"], anchor=anc)
    ex.line(bx0, base, bx0 + pw, base, stroke=C["axis"], width=0.8, tag="axis")
    return ay0, ay1


def _sm_bar(ex, bx0, by0, pw, ph, x, xl, ys, lo, hi, col, on, focus_x, value_fmt, cat_w):
    """Horizontal bars per category (same order in every panel) on the (shared) scale, values at bar ends."""
    C = ex.C
    ay0, ay1 = by0 + 22, by0 + ph
    m = len(x)
    rh = (ay1 - ay0) / m
    bh = min(rh * 0.62, 18)
    vw = max(tw(value_fmt(v), 10) for v in ys if v is not None) + 6
    a, b = bx0 + cat_w, bx0 + pw - vw
    sx = lambda v: a + (v - lo) / ((hi - lo) or 1) * (b - a)  # noqa: E731
    zero = sx(0) if lo <= 0 <= hi else a
    for k, (xv, v) in enumerate(zip(x, ys)):
        cy = ay0 + rh * k + rh / 2
        ex.text(a - 6, cy + 3.6, xl[k], size=10, fill=C["text"] if on else C["sub"], anchor="end")
        if v is None:
            continue
        c = C["accent"] if (on and focus_x and focus_x(xv)) else col
        xa, xb = sorted((zero, sx(v)))
        ex.rect(xa, cy - bh / 2, max(xb - xa, 1), bh, c)
        if v >= 0:
            ex.text(xb + 4, cy + 3.6, value_fmt(v), size=10, fill=C["ink"] if on else C["sub"])
        else:
            ex.text(xa - 4, cy + 3.6, value_fmt(v), size=10, fill=C["ink"] if on else C["sub"], anchor="end")
    ex.line(zero, ay0, zero, ay1, stroke=C["axis"], width=0.8, tag="axis")


# ===================================================================================== fan forecast


def fan(ex, box, x, actual, scenarios, forecast_from, value_fmt=lambda v: fmt(v), ytitle=None, size=10.5):
    """Scenario / fan forecast: actual line + base case continuing dashed + low/high band (shaded), with the three
    end values labelled ("乐观 / 基准 / 悲观"). scenarios: dict(low=[...], base=[...], high=[...]) aligned to x,
    None before forecast_from. Returns the NAxes."""
    C = ex.C
    vals = [v for v in actual if v is not None] + [v for s in scenarios.values() for v in s if v is not None]
    x0, y0, x1, y1 = box
    zh = _zh(ex, ytitle or "中")
    names = {"high": "乐观" if zh else "Upside", "base": "基准" if zh else "Base", "low": "悲观" if zh else "Downside"}
    rp = max(tw(f"{names[k]} {value_fmt(scenarios[k][-1])}", size, True) for k in names) + 14
    span_w = x1 - rp - x0 - 48
    step = int(max(1, -(-len(x) * (tw("2030", 10.5) + 10) // max(span_w, 1))))
    keep = {x[0], forecast_from, x[-1]}
    ticks = sorted(keep | {t for t in x[::step] if all(abs(t - k) >= step for k in keep)})
    ax = NAxes.fit(ex, (x0, y0, x1 - rp, y1), (x[0], x[-1]), (min(0, min(vals)), max(vals) * 1.08),
                   xticks=ticks, ytitle=bool(ytitle), xtitle=False)
    fx = ax.sx(forecast_from)
    ex.rect(fx, ax.y, ax.x + ax.w - fx, ax.h, "#F5F5F5", register=False)
    ex.text(fx + 6, ax.y + 12, "预测" if zh else "Forecast", size=10, fill=C["sub"])
    ax.frame(xfmt=lambda v: f"{v:.0f}", ytitle=ytitle, zero_line=False)
    if forecast_from not in x:
        raise ValueError(f"fan: forecast_from 要写 x 里的年份值（如 {x[len(x) // 2]}），不是下标")
    k = x.index(forecast_from)
    if actual[k] is None:
        raise ValueError(f"fan: actual 在 forecast_from={forecast_from} 必须有值（预测从最后一个实际值接续）")
    lo = [actual[k] if j == k else scenarios["low"][j] for j in range(k, len(x))]
    hi_ = [actual[k] if j == k else scenarios["high"][j] for j in range(k, len(x))]
    up = [(ax.sx(x[j]), ax.sy(hi_[j - k])) for j in range(k, len(x))]
    dn = [(ax.sx(x[j]), ax.sy(lo[j - k])) for j in reversed(range(k, len(x)))]
    ex.path("M" + " L".join(f"{p:.1f},{q:.1f}" for p, q in up + dn) + " Z", fill=C["second"], opacity=0.18,
            register=False)
    polyline(ax, x[:k + 1], actual[:k + 1], C["main"], width=2.4)
    base = [actual[k]] + list(scenarios["base"][k + 1:])
    polyline(ax, x[k:], base, C["accent"], width=2.2, dash="5,3")
    ends = sorted([[ax.sy(ys[-1]), key, ys, col] for key, ys, col in
                   (("high", hi_, C["second"]), ("base", base, C["accent"]), ("low", lo, C["second"]))])
    for j in range(1, 3):
        if ends[j][0] - ends[j - 1][0] < size * 1.4:
            ends[j][0] = ends[j - 1][0] + size * 1.4
    for py, key, ys, col in ends:
        ex.text(ax.x + ax.w + 8, py + 4, f"{names[key]} {value_fmt(ys[-1])}", size=size, weight=700 if key == "base" else 400,
                fill=col if key == "base" else C["sub"])
    return ax


# ===================================================================================== treemap


def treemap(ex, box, items, value_fmt=lambda v: fmt(v), colors=None, focus=None, size=11, min_label=2600):
    """Treemap (squarified): area = value; items [(name, value)] or [(name, value, color)]. Each tile shows name and
    value/share when it is big enough (area > min_label px²). focus: callable(name) -> bool (others muted).
    Returns {name: (x0, y0, x1, y1)}."""
    if len(items) < 3:
        raise ValueError(f"treemap 少于 3 块（收到 {len(items)} 块），面积对比没有意义——改用 hstack100（构成条，"
                         "exhibit_help('share_bars')）或 big_number + 一句结论")
    C = ex.C
    items = sorted(items, key=lambda t: -t[1])
    total = sum(t[1] for t in items) or 1
    x0, y0, x1, y1 = box
    y1 -= 18 if min(t[1] for t in items) / total < 0.03 else 0
    W, H = x1 - x0, y1 - y0
    scale = W * H / total
    pal = colors or [C["main"], C["second"], C["third"], C["light"], C["light2"], C["context"]]
    rects = {}

    def worst(row, w):
        s = sum(a for _, a, _ in row)
        return max(max(w * w * a / (s * s), (s * s) / (w * w * a)) for _, a, _ in row)

    def layout(seq, rx, ry, rw, rh):
        row = []
        while seq:
            w = min(rw, rh)
            cand = row + [seq[0]]
            if not row or worst(cand, w) <= worst(row, w):
                row = cand
                seq = seq[1:]
                continue
            rx, ry, rw, rh = place(row, rx, ry, rw, rh)
            row = []
        if row:
            place(row, rx, ry, rw, rh)

    def place(row, rx, ry, rw, rh):
        s = sum(a for _, a, _ in row)
        if rw >= rh:
            cw = s / rh
            yy = ry
            for name, a, c in row:
                hh = a / cw
                rects[name] = (rx, yy, rx + cw, yy + hh, c)
                yy += hh
            return rx + cw, ry, rw - cw, rh
        ch = s / rw
        xx = rx
        for name, a, c in row:
            ww = a / ch
            rects[name] = (xx, ry, xx + ww, ry + ch, c)
            xx += ww
        return rx, ry + ch, rw, rh - ch

    if focus is not None:  # focused tiles take the strong colours in size order, the rest stay muted grey
        strong = iter([C["main"], C["accent"], C["second"], C["third"]] * 4)
        cols = [t[2] if len(t) > 2 else (next(strong) if focus(t[0]) else C["context"]) for t in items]
    else:
        cols = [t[2] if len(t) > 2 else pal[min(i, len(pal) - 1)] for i, t in enumerate(items)]
    seq = [(t[0], t[1] * scale, c) for t, c in zip(items, cols)]
    small = []
    layout(seq, x0, y0, W, H)
    out = {}
    for name, v, *_ in items:
        a, b, c, d, col = rects[name]
        ex.rect(a, b, c - a, d - b, col, stroke="#FFFFFF", stroke_width=2, register=False)
        ex.occupy((a, b, c, d), "mark", "panel-bg")
        light = col in (C["light"], C["light2"], C["dim"], C["context"])
        fc = C["ink"] if light else "#FFFFFF"
        tw_, th_ = c - a, d - b
        val = f"{value_fmt(v)}  {v / total:.0%}"
        if tw_ > tw(name, size, True) + 10 and th_ > 2 * size + 14 and tw_ > tw(val, size - 0.5) + 10:
            ex.text(a + 6, b + size + 5, name, size=size, weight=700, fill=fc, register=False)
            ex.text(a + 6, b + 2 * size + 9, val, size=size - 0.5, fill=fc, register=False)
        elif tw_ > tw(f"{name} {v / total:.0%}", 10, True) + 8 and th_ > 10 + 8:
            ex.text(a + 4, b + (th_ + 10 * 0.7) / 2, f"{name} {v / total:.0%}", size=10, weight=700, fill=fc,
                    register=False)
        else:
            small.append(f"{name} {v / total:.0%}")
        out[name] = (a, b, c, d)
    if small:  # tiles too small for any label are listed under the map instead of overflowing
        ex.text(x0, y1 + 14, ("其他小项：" if _zh(ex, items[0][0]) else "Small: ") + "、".join(small), size=10,
                fill=C["sub"])
        print(f"treemap: {len(small)} 个小格放不下标签，已列在图下（给图区底部留 18px）")
    return out


# ===================================================================================== profit pool


def profit_pool(ex, box, segments, value_fmt=lambda v: f"{v:.0f}%", focus=None, avg=True, size=10.5):
    """Profit pool (variable-width columns): width = revenue share, height = margin, so area = profit pool.

    segments: [(name, revenue, margin_pct)], sorted by margin desc. Wide columns carry "name / margin" (inside, or
    on top when short); narrow ones keep the margin on top and list the name under the axis (stacked rows + leader;
    names that still do not fit go to an "另有/Also" line). avg=True: dashed revenue-weighted average margin.
    focus: callable(name) -> bool (accent; others grey). Returns {name: (x0, y0, x1, y1)}."""
    C = ex.C
    segs = sorted(segments, key=lambda t: -t[2])
    total = sum(s[1] for s in segs) or 1
    tiny = [s[0] for s in segs if s[1] / total < 0.03]
    if len(tiny) > 2:
        raise ValueError(f"profit_pool: {tiny} 收入占比都 <3%，柱宽看不见——合并成'其他'或改用 row_table")
    if len(segs) > 2 and max(s[2] for s in segs) - min(s[2] for s in segs) < 3:
        raise ValueError("profit_pool: 各环节利润率差异 <3 个百分点，利润池画不出差别——改用 share_bars 或 row_table")
    x0, y0, x1, y1 = box
    zh = _zh(ex, *[s[0] for s in segs])
    ticks = nice_ticks(max(s[2] for s in segs) * 1.04, 4, min(0, min(s[2] for s in segs) * 1.2))
    ax0 = x0 + max(tw(value_fmt(t), 10.5) for t in ticks) + 10
    sx = lambda s: ax0 + s * (x1 - 2 - ax0)  # noqa: E731
    cols, cum = [], 0
    for n, rev, m in segs:
        cols.append((n, m, sx(cum / total), sx((cum + rev) / total)))
        cum += rev
    _vf = value_fmt
    if any(b - a < tw(_vf(m), 10) - 2 for n, m, a, b in cols):   # "25.0%" too wide for a slim column: "25%" fits
        value_fmt = lambda v: re.sub(r"\.0+(?=\D*$)", "", _vf(v))  # noqa: E731
    narrow = [(n, m, (a + b) / 2, b - a >= tw(value_fmt(m), 10) - 2) for n, m, a, b in cols
              if b - a < tw(n, size, True) + 8]
    def stack(order):   # lowest free row, own leader clear, covering as few other leaders as possible
        below, under = [], {}
        for n, m, c, shown in order:
            t = n if shown else f"{n} {value_fmt(m)}"
            W, cands = tw(t, 10), []
            for r in range(max(2, min(5, int((y1 - y0) * 0.22 / 14)))):
                for k, lft in enumerate((c - W / 2, c - 3, c - W + 3)):
                    lft = min(max(lft, x0), x1 - W)
                    if all(not (lft < pr + 6 and pl < lft + W + 6) for rr, pl, pr, pc in below if rr == r) and \
                            all(not (pl - 3 <= c <= pr + 3) for rr, pl, pr, pc in below if rr < r) and \
                            all(not (lft - 3 <= pc <= lft + W + 3) for rr, pl, pr, pc in below if rr > r):
                        cover = sum(lft - 3 <= oc <= lft + W + 3 for o, _, oc, _ in narrow if o != n)
                        cands.append((r + 0.6 * cover, k, r, lft))
            if cands:
                _, _, r, lft = min(cands)
                below.append((r, lft, lft + W, c))
                under[n] = (r, lft, t)
        return below, under
    # margin order first; right-to-left (labels stair-step down to the left) when that places more names
    below, under = max((stack(narrow), stack(sorted(narrow, key=lambda q: -q[2]))),
                       key=lambda bu: (len(bu[1]), -max([r for r, *_ in bu[0]], default=0)))
    rest = [f"{n} {value_fmt(m)}" for n, m, *_ in narrow if n not in under]
    nrows = max([r for r, *_ in below], default=-1) + 1
    ax = Axes(ex, ax0, y0 + 24, x1 - 2 - ax0, y1 - y0 - 24 - (20 + 14 * nrows + (16 if rest else 0)), ticks[-1],
              ticks[0], ticks)
    ax.grid(fmt_tick=value_fmt)
    ex.text(x0, y0 + 10, "利润率（柱宽 = 收入占比）" if zh else "Margin (width = revenue share)", size=10, fill=C["sub"])
    av = sum(s[1] * s[2] for s in segs) / total
    ay, base, out = ax.sy(av), ax.sy(ax.ymin), {}
    for n, m, a, b in cols:
        on = focus(n) if focus else True
        col = (C["accent"] if focus else C["main"]) if on else C["context"]
        top, bot = sorted((ax.sy(m), ax.sy(0)))
        ex.rect(a, top, b - a, bot - top, col, stroke="#FFFFFF", stroke_width=1)
        out[n] = (a, top, b, bot)
        cx, hi, wide = (a + b) / 2, C["accent"] if focus and on else C["ink"], all(t[0] != n for t in narrow)
        if wide and bot - top > 2 * size + 14:  # name + margin inside, moved below the average line if it cuts
            ty = top + size + 5
            if avg and ty - size - 2 < ay < ty + size + 8 and bot - ay > 2 * size + 12:
                ty = ay + size + 5
            fc = "#FFFFFF" if on else C["ink"]
            ex.text(cx, ty, n, size=size, weight=700, fill=fc, anchor="middle")
            ex.text(cx, ty + size + 4, value_fmt(m), size=size, fill=fc, anchor="middle")
            continue
        t = f"{n} {value_fmt(m)}" if wide else value_fmt(m)
        sz = size if wide or b - a > tw(t, size, True) else 10
        if not wide and b - a < tw(t, 10) - 2:
            continue
        ty = top - 4 if m >= 0 else bot + size + 3
        if avg and m >= 0 and ty - size - 1 < ay < ty + 3:
            ty = ay - 3
        ex.text(cx, ty, t, size=sz, weight=700 if sz == size else 400, fill=hi, anchor="middle")
    for r, lft, rgt, c in below:
        ex.line(c, base + 3, c, base + 18 + 14 * r, stroke=C["context"], width=0.7, tag="leader")
    for n, (r, lft, t) in under.items():
        on = bool(focus and focus(n))
        ex.text(lft, base + 30 + 14 * r, t, size=10, weight=700 if on else 400, fill=C["accent"] if on else C["text"])
    for s in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        if not any(sx(s) - 18 <= c <= sx(s) + 18 for *_, c in below):
            ex.text(sx(s), base + 14, f"{s:.0%}", size=10, fill=C["axis"],
                    anchor="start" if s == 0 else ("end" if s == 1 else "middle"))
    if rest:
        ex.text(x0, y1 - 4, ("另有：" if zh else "Also: ") + "、".join(rest), size=10, fill=C["sub"])
    if avg:
        ax.ref_y(av, ("平均 " if zh else "Avg ") + value_fmt(av))
        ex.notes += 1
    return out


# ===================================================================================== bump


def bump(ex, box, periods, series, focus=None, top=None, size=10.5):
    """Bump chart: rank of each object over several periods (1 = top row). series: [(name, [rank per period])]
    (None = not ranked that period). Names at both ends ("name #r" right, "name" left), de-overlapped; period
    labels on top. focus: callable(name) -> bool (accent/main/second, thicker); others grey. top: only draw ranks
    <= top. Returns sy(rank)."""
    C = ex.C
    x0, y0, x1, y1 = box
    lim = top or max(r for _, rs in series for r in rs if r is not None)
    lw = max(tw(n, size, True) for n, _ in series) + 12
    rw = max(tw(f"#{lim} {n}", size, True) for n, _ in series) + 12
    xl, xr, head = x0 + lw, x1 - rw, 22
    step = (y1 - y0 - head - 8 - size) / max(lim - 1, 1)
    sy = lambda r: y0 + head + 8 + (r - 1) * step if lim > 1 else (y0 + y1 + head) / 2  # noqa: E731
    sx = lambda i: xl + i * (xr - xl) / max(len(periods) - 1, 1)  # noqa: E731
    for i, p in enumerate(periods):
        ex.text(sx(i), y0 + 12, str(p), size=size, weight=700, fill=C["ink"], anchor="middle")
        ex.line(sx(i), y0 + head - 2, sx(i), y1, stroke=C["grid"], width=0.8, tag="grid")
    hl, k, ends = [C["accent"], C["main"], C["second"]], 0, {"start": [], "end": []}
    order = sorted(series, key=lambda t: bool(focus and focus(t[0])))  # highlighted lines drawn last (on top)
    for n, rs in order:
        on = focus(n) if focus else True
        col = (hl[k % 3] if focus else C["main"]) if on else C["context"]
        k += 1 if on and focus else 0
        runs, cur = [], []  # one polyline per unbroken stretch (None / below `top` breaks the line)
        for i, r in enumerate(rs):
            if r is not None and r <= lim:
                cur.append((sx(i), sy(r)))
            elif cur:
                runs, cur = runs + [cur], []
        runs += [cur] if cur else []
        pts = [p for run in runs for p in run]
        if not pts:
            continue
        for run in runs:
            if len(run) > 1:
                for start, end in zip(run, run[1:]):
                    ex.line(*start, *end, stroke=col, width=2.6 if on else 1.4, tag="series", whole=True)
        for a, b in pts:
            ex.circle(a, b, 4 if on else 3, col)
        if rs[0] is not None and rs[0] <= lim:
            ends["start"].append([pts[0][1], n, col, on])
        if rs[-1] is not None and rs[-1] <= lim:
            ends["end"].append([pts[-1][1], f"#{rs[-1]:.0f} {n}", col, on])
    for key, x, anchor in (("start", xl - 8, "end"), ("end", xr + 8, "start")):
        e = sorted(ends[key])
        for j in range(1, len(e)):
            e[j][0] = max(e[j][0], e[j - 1][0] + size * 1.3)
        for py, t, col, on in e:
            ex.text(x, py + size * 0.36, t, size=size, weight=700 if on else 400, fill=col if on else C["sub"],
                    anchor=anchor)
    if focus and k:
        ex.notes += 1
    return sy


# ===================================================================================== dot range


def dot_range(ex, box, rows, value_fmt=lambda v: fmt(v), focus=None, ref=None, ref_label=None, mark_label=None,
              size=10.5):
    """Benchmark plot on endpoint box=(x0,y0,x1,y1), not width/height; both extents must be positive.
    rows: [dict(label, value, lo=None, hi=None, mark=None, unit=None)]; one axis = one unit (PB 'x' and yield '%'
    on one axis raise). Grey bar = peer range, dot = value, hollow diamond
    = median/target. Each row's peer range/median must share its metric definition, perimeter and period, not just
    unit; metrics may differ across rows. Shared x scale (zoomed to a local range when every value sits far from zero;
    dots carry no zero baseline); ref/ref_label draw a dashed reference, mark_label
    names the diamond. focus: callable(label) -> bool highlights rows (accent dot + bold label). Returns sx."""
    C = ex.C
    if ref is not None:
        from ._page import add_fact
        add_fact(ex, {"kind": "ref", "value": float(ref), "label": str(ref_label or "")})
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"dot_range: box=(x0,y0,x1,y1) requires x1 > x0 and y1 > y0; "
                         f"use endpoints, not width/height (received {box!r})")
    from ._semantics import mixed_units
    mixed_units([r.get("unit") or r["label"] for r in rows], "dot_range（各行共用一根横轴）",
                "分成两个 dot_range 面板（每个面板一种单位），或改 row_table 每列一个指标各自刻度")
    miss = [r["label"] for r in rows if r.get("value") is None]
    if miss:
        raise ValueError(f"dot_range: {miss} 没有 value——删掉这些行，在脚注写'未披露'")
    vals = [v for r in rows for v in (r["value"], r.get("lo"), r.get("hi"), r.get("mark")) if v is not None]
    lo_v, hi_v = min(vals + ([ref] if ref is not None else [])), max(vals + ([ref] if ref is not None else []))
    # dots and intervals encode position, not length: values clustered far from zero (71–75 % on a 0–80 axis) get a
    # local range so the gaps / interval widths are readable
    floor = lo_v - (hi_v - lo_v) * 0.25 if lo_v > 0 and lo_v > 0.45 * hi_v and hi_v > lo_v else min(0, lo_v)
    ticks = nice_ticks(hi_v, 4, floor)
    lw = max(tw(r["label"], size, True) for r in rows) + 12
    vw = max(tw(value_fmt(r["value"]), size, True) for r in rows) + 10
    a, b, head, foot = x0 + lw, x1 - vw, 34 if mark_label else 20, 18 if ref_label and ref is not None else 0
    sx = lambda v: a + (v - ticks[0]) / ((ticks[-1] - ticks[0]) or 1) * (b - a)  # noqa: E731
    rh = min((y1 - y0 - head - foot) / len(rows), 56)
    for t in ticks:
        ex.text(sx(t), y0 + 10, value_fmt(t), size=10, fill=C["axis"], anchor="middle")
        ex.line(sx(t), y0 + 14, sx(t), y0 + head + rh * len(rows), stroke=C["grid"], width=0.8, tag="grid")
    if mark_label:
        mx = b - tw(mark_label, 10)
        ex.path(f"M{mx - 10:.1f},{y0 + 20:.1f} l4.5,4.5 l-4.5,4.5 l-4.5,-4.5 Z", fill="#FFFFFF", stroke=C["ink"],
                width=1.2, register=False)
        ex.text(mx, y0 + 28, mark_label, size=10, fill=C["sub"])
    for i, r in enumerate(rows):
        cy = y0 + head + (i + 0.5) * rh
        on = focus(r["label"]) if focus else False
        col = C["accent"] if on else C["main"]
        if on:
            ex.rect(x0, cy - rh / 2 + 1, x1 - x0, rh - 2, C["band"], register=False)
        if r.get("lo") is not None and r.get("hi") is not None:
            ex.rect(sx(r["lo"]), cy - 4, sx(r["hi"]) - sx(r["lo"]), 8, C["dim"], register=False)
        if r.get("mark") is not None:
            mx, d = sx(r["mark"]), 5.5
            ex.path(f"M{mx:.1f},{cy - d:.1f} L{mx + d:.1f},{cy:.1f} L{mx:.1f},{cy + d:.1f} L{mx - d:.1f},{cy:.1f} Z",
                    fill="#FFFFFF", stroke=C["ink"], width=1.4, register=False)
        ex.circle(sx(r["value"]), cy, 6 if on else 5, col)
        ex.text(a - 10, cy + size * 0.36, r["label"], size=size, weight=700 if on else 400,
                fill=C["ink"] if on else C["text"], anchor="end")
        ext = [sx(v) for v in (r["value"], r.get("lo"), r.get("hi"), r.get("mark")) if v is not None]
        t, tx = value_fmt(r["value"]), max(sx(r["value"]) + 10, max(ext) + 8)
        tw_ = tw(t, size, True)
        if ref is not None and tx - 3 <= sx(ref) <= tx + tw_ + 3 and min(ext) - a > tw_ + 10:
            tx = min(ext) - 8 - tw_  # keep the value clear of the reference line
        ex.text(tx, cy + size * 0.36, t, size=size, weight=700, fill=col)
    if ref is not None:
        rx = sx(ref)
        yb = y0 + head + rh * len(rows)
        ex.line(rx, y0 + head - 4, rx, yb + 2, stroke=C["ink"], width=1, dash="4,3", tag="ref")
        if ref_label:
            w = tw(ref_label, 10)
            ex.text(min(max(rx, x0 + w / 2), x1 - w / 2), yb + 14, ref_label, size=10, fill=C["sub"], anchor="middle")
        ex.notes += 1
    return sx


# ===================================================================================== funnel


def funnel(ex, box, stages, value_fmt=lambda v: fmt(v), focus=None, size=10.5, targets=None):
    """Conversion funnel: centred horizontal bars shrinking with the value, stage name on the left, value inside
    (or beside a short bar; widths are √-compressed so late stages stay visible), and between consecutive stages the computed conversion "→ 38%". The step with the
    lowest conversion is marked in accent (the argument). stages: [(name, value)]. focus: callable(name) -> bool
    (accent bar; others main). targets: optional target conversion per step (n − 1 fractions, None to skip a step) —
    the "最大流失" mark then goes to the step furthest below its target, not the lowest raw rate (an exposure →
    inquiry step of 2.5 % is normal). The marked step is recorded for the title check ("最大流失在 X" must name it).
    Returns index of the weakest step (stage i -> i+1)."""
    C = ex.C
    x0, y0, x1, y1 = box
    n, top = len(stages), max(v for _, v in stages) or 1
    lw = max(tw(nm, size, True) for nm, _ in stages) + 14
    rates = [(stages[i + 1][1] / stages[i][1]) if stages[i][1] else 0 for i in range(n - 1)]
    worst = min(range(n - 1), key=lambda i: rates[i]) if rates else None
    if targets is not None:
        if len(targets) != n - 1:
            raise ValueError(f"funnel：targets 要给 {n - 1} 个（每一步转化的目标，缺的写 None），收到 {len(targets)} 个")
        gaps = [(rates[i] / targets[i] - 1, i) for i in range(n - 1) if targets[i]]
        if gaps:
            worst = min(gaps)[1]
    if worst is not None:
        from ._page import add_fact
        add_fact(ex, {"kind": "funnel", "worst": (str(stages[worst][0]), str(stages[worst + 1][0])),
                      "stages": [str(nm) for nm, _ in stages], "vs_target": bool(targets)})
    zh = _zh(ex, *[nm for nm, _ in stages])
    note = ("最大流失" if zh else "Biggest drop") if worst is not None else ""
    rw = tw(f"→ 100%  {note}", 10.5, True) + 8
    a, b = x0 + lw, x1 - rw
    cx, half = (a + b) / 2, (b - a) / 2
    bh = (y1 - y0) / (n + (n - 1) * 0.55)
    gap = bh * 0.55
    for i, (nm, v) in enumerate(stages):
        yt = y0 + i * (bh + gap)
        w = half * (0.18 + 0.82 * (v / top) ** 0.5) if v > 0 else 1.5  # √-compressed so tail stages stay visible
        on = focus(nm) if focus else False
        ex.rect(cx - w, yt, 2 * w, bh, C["accent"] if on else C["main"])
        ex.text(a - 14, yt + bh / 2 + size * 0.36, nm, size=size, weight=700 if on else 400, fill=C["ink"], anchor="end")
        t = value_fmt(v)
        if 2 * w > tw(t, size, True) + 12 and bh > size + 4:
            ex.text(cx, yt + bh / 2 + size * 0.36, t, size=size, weight=700, fill="#FFFFFF", anchor="middle")
        else:
            ex.text(cx + w + 6, yt + bh / 2 + size * 0.36, t, size=size, weight=700, fill=C["ink"])
        if i < n - 1:
            w2 = half * (0.18 + 0.82 * (stages[i + 1][1] / top) ** 0.5) if stages[i + 1][1] > 0 else 1.5
            yb, yn, bad = yt + bh, yt + bh + gap, i == worst and n > 2
            ex.path(f"M{cx - w:.1f},{yb:.1f} L{cx + w:.1f},{yb:.1f} L{cx + w2:.1f},{yn:.1f} L{cx - w2:.1f},{yn:.1f} Z",
                    fill=C["accent"] if bad else C["light2"], opacity=0.35 if bad else None, register=False)
            lab, ty = f"→ {rates[i]:.0%}", yb + gap / 2 + 10.5 * 0.36  # conversion column right of the funnel
            ex.text(b + 8, ty, lab, size=10.5, weight=700 if bad else 400, fill=C["accent"] if bad else C["sub"])
            if bad:
                ex.text(b + 14 + tw(lab, 10.5, True), ty, note, size=10.5, weight=700, fill=C["accent"])
    ex.notes += 1
    return worst
