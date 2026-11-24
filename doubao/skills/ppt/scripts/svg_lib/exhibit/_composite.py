"""Composite charts: pie-of-pie, share circles with text rows, layered areas / ridgeline, speech-bubble note."""

from __future__ import annotations

import math

from ._text import fmt, tw, wrap


def _sector(cx, cy, r, a0, a1):
    large = 1 if a1 - a0 > math.pi else 0
    p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
    p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
    if a1 - a0 >= 2 * math.pi - 1e-6:
        return (f"M{cx - r:.1f},{cy:.1f} A{r:.1f},{r:.1f} 0 1 1 {cx + r:.1f},{cy:.1f} "
                f"A{r:.1f},{r:.1f} 0 1 1 {cx - r:.1f},{cy:.1f} Z")
    return (f"M{cx:.1f},{cy:.1f} L{p0[0]:.1f},{p0[1]:.1f} A{r:.1f},{r:.1f} 0 {large} 1 {p1[0]:.1f},{p1[1]:.1f} Z")


def _smooth(pts, t=0.18):
    """Catmull-Rom → cubic Bézier path body ('M… C…') through pts, clamped so it never overshoots between points."""
    if len(pts) < 3:
        return "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        lo, hi = min(p1[1], p2[1]), max(p1[1], p2[1])
        c1 = (p1[0] + (p2[0] - p0[0]) * t, min(max(p1[1] + (p2[1] - p0[1]) * t, lo), hi))
        c2 = (p2[0] - (p3[0] - p1[0]) * t, min(max(p2[1] - (p3[1] - p1[1]) * t, lo), hi))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def _light(C, col):
    if col in (C["light"], C.get("light2"), C["dim"], C["context"], C["track"], "#FFFFFF"):
        return True
    c = str(col).lstrip("#")
    if len(c) != 6:
        return False
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.62


HATCH = "wd-up-diag"   # native Slides fillPattern for slices that are not broken out


def _mix(col, t):
    """Blend a #RRGGBB colour toward white by t (0 = same, 1 = white)."""
    c = col.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % tuple(round(v + (255 - v) * t) for v in (r, g, b))


def _pie(ex, cx, cy, r, segs, start, fmt_, min_in=0.35, hatched=()):
    """Plain pie; returns [(a0, a1, label, value, color)]. % inside slices wide enough, else just outside.
    hatched: indices drawn with a diagonal hatch in their own colour (native fillPattern); their % sits on a white
    chip so it stays legible over the stripes."""
    C = ex.C
    tot = sum(v for _, v, _ in segs) or 1
    a, out = start, []
    for i, (lab, v, col) in enumerate(segs):
        da = v / tot * 2 * math.pi
        if i in hatched:
            ex.add(f'<path d="{_sector(cx, cy, r, a, a + da)}" fill="{col}" stroke="{col}" stroke-width="1" '
                   f'data-sml-pattern="{HATCH}"/>')
        else:
            ex.path(_sector(cx, cy, r, a, a + da), fill=col, stroke="#FFFFFF", width=1.2, register=False)
        out.append((a, a + da, lab, v, col))
        a += da
    ex.occupy((cx - r, cy - r, cx + r, cy + r), "mark", "pie")
    from ._page import frame_w

    def fits(a0, a1, rr, t):
        # the server compares the label's native text frame with the bounding box of the sector under it
        mid = (a0 + a1) / 2
        tx, ty = cx + rr * math.cos(mid), cy + rr * math.sin(mid)
        angs = [a0, a1] + [k * math.pi / 2 for k in range(-8, 9) if a0 < k * math.pi / 2 < a1]
        xs = [cx] + [cx + r * math.cos(a) for a in angs]
        ys = [cy] + [cy + r * math.sin(a) for a in angs]
        w, h = frame_w(t, 11.5, True) + 3, 11.5 + 3
        return min(xs) <= tx - w / 2 and tx + w / 2 <= max(xs) and min(ys) <= ty - h / 2 and ty + h / 2 <= max(ys)

    for i, (a0, a1, lab, v, col) in enumerate(out):
        mid = (a0 + a1) / 2
        rr = next((r * f for f in (0.62, 0.55, 0.7, 0.48, 0.76) if fits(a0, a1, r * f, fmt_(v / tot))), None)
        if rr is None:
            continue
        if a1 - a0 >= min_in and i not in hatched:
            fill = C["ink"] if _light(C, col) else "#FFFFFF"
            ex.text(cx + rr * math.cos(mid), cy + rr * math.sin(mid) + 4, fmt_(v / tot), size=11.5, weight=700,
                    anchor="middle", fill=fill, register=False)
        elif a1 - a0 >= min_in:
            t = fmt_(v / tot)
            tx, ty = cx + rr * math.cos(mid), cy + rr * math.sin(mid)
            w = tw(t, 11.5, True) + 8
            ex.rect(tx - w / 2, ty - 8.5, w, 17, "#FFFFFF", register=False)
            ex.text(tx, ty + 4, t, size=11.5, weight=700, anchor="middle", fill=C["ink"], register=False)
    return out, tot


_SHADES = (0, 0.28, 0.48, 0.64, 0.76, 0.86)


def _legend_rows(ex, x, y, items, tot, value_fmt, hatched=(), right=False):
    """Swatch + name + bold share per row from (x, y) (first baseline); right=True right-aligns the rows at x."""
    C = ex.C
    for i, (l, v, c) in enumerate(items):
        yy = y + i * 18
        t = value_fmt(v / tot)
        w = 14 + tw(l, 10.5) + 6 + tw(t, 10.5, True)
        lx = x - w if right else x
        if i in hatched:
            ex.add(f'<path d="M{lx:.1f},{yy - 9:.1f} L{lx + 9:.1f},{yy - 9:.1f} L{lx + 9:.1f},{yy:.1f} L{lx:.1f},{yy:.1f} Z" '
                   f'fill="{c}" stroke="{c}" stroke-width="0.8" data-sml-pattern="{HATCH}"/>')
        else:
            ex.rect(lx, yy - 9, 9, 9, c, register=False)
        ex.text(lx + 14, yy, l, size=10.5, fill=C["text"])
        ex.text(lx + 14 + tw(l, 10.5) + 6, yy, t, size=10.5, weight=700, fill=C["ink"])
    return max((14 + tw(l, 10.5) + 6 + tw(value_fmt(v / tot), 10.5, True) for l, v, _ in items), default=0)


def _funnel(ex, cx, cy, R, a0, a1, scx, scy, r, fill):
    """Grey-tinted funnel from slice edge points to the two points of the sub-pie facing the main pie; under all."""
    p0 = (cx + R * math.cos(a0), cy + R * math.sin(a0))
    p1 = (cx + R * math.cos(a1), cy + R * math.sin(a1))
    # end on the sub-pie's near side (±65° from the line between centres): a slimmer funnel whose bounding box
    # stays clear of the legends around it
    back = math.atan2(cy - scy, cx - scx)
    qa = (scx + r * math.cos(back + 1.13), scy + r * math.sin(back + 1.13))
    qb = (scx + r * math.cos(back - 1.13), scy + r * math.sin(back - 1.13))
    if math.dist(p0, qa) + math.dist(p1, qb) > math.dist(p0, qb) + math.dist(p1, qa):
        qa, qb = qb, qa
    ex.under(ex.path, f"M{p0[0]:.1f},{p0[1]:.1f} L{qa[0]:.1f},{qa[1]:.1f} L{qb[0]:.1f},{qb[1]:.1f} "
             f"L{p1[0]:.1f},{p1[1]:.1f} Z", fill=fill, opacity=0.75, register=False)
    xs, ys = [p0[0], p1[0], qa[0], qb[0]], [p0[1], p1[1], qa[1], qb[1]]
    return (min(xs), min(ys), max(xs), max(ys))


def pie_of_pie(ex, box, segs, explode, parts, value_fmt=lambda s: f"{s * 100:.0f}%", title_main=None,
               title_sub=None, colors=None):
    """Pie of pie. Main pie of segs [(label, value, color?)]; broken-out slices open into their own sub-pies, each
    joined to its slice by a funnel. Slices that are not broken out keep their colour as a diagonal hatch (native
    fillPattern), so the broken-out ones read first. Sub-pie slices are shades of their parent slice's colour.

    One slice:   explode="线上", parts=[(label, value), ...]  → main pie left, sub-pie right (title_sub names it).
    2–4 slices:  explode=["线上", "门店"] (or omit: the keys of parts), parts={"线上": [...], "门店": [...]}
                 → main pie centred, sub-pies around it (left / right columns), each titled "<slice> <share>" with
                 its legend on the outer side. Sub-pie radius grows with the slice's share.
    Labels: % inside wide slices; legend under the main pie names every main slice. Shares computed from the data.
    Returns dict(main=(cx, cy, r), sub=(cx, cy, r) of the first sub-pie, subs={label: (cx, cy, r)})."""
    C = ex.C
    if isinstance(parts, dict):
        keys = list(explode) if isinstance(explode, (list, tuple)) else ([explode] if explode is not None
                                                                           else list(parts))
    else:
        if isinstance(explode, (list, tuple)):
            raise ValueError("pie_of_pie：拆开多块时 parts 要写成 {扇区名: [(子项, 值), …]}")
        keys, parts = [explode], {explode: parts}
    if len(segs) < 2:
        raise ValueError("pie_of_pie：主饼需 ≥2 个扇区；只有一层构成用 donut / hstack100")
    names = [s[0] for s in segs]
    idx = []
    for k in keys:
        i = k if isinstance(k, int) else (names.index(k) if k in names else None)
        if i is None:
            raise ValueError(f"pie_of_pie：explode={k!r} 不在主饼扇区 {names} 里")
        idx.append(i)
    if not 1 <= len(idx) <= 4:
        raise ValueError("pie_of_pie：拆开 1–4 块；更多块改用 marimekko 或多个 donut")
    sub_of = {}
    for k, i in zip(keys, idx):
        p = parts.get(k, parts.get(names[i]))
        if not p or len(p) < 2:
            raise ValueError(f"pie_of_pie：{names[i]} 的展开饼需 ≥2 个子项")
        sub_of[i] = p
    x0, y0, x1, y1 = box
    pal = colors or [C["main"], C["accent"], C["second"], C["third"], C["deep"], C["context"]]   # no pale role: a hatch in it vanishes
    segs = [(s[0], s[1], s[2] if len(s) > 2 and s[2] else pal[k % len(pal)]) for k, s in enumerate(segs)]
    if len(idx) == 1 and not (len(segs[idx[0]]) > 2 and colors):
        segs = [(l, v, C["accent"] if i == idx[0] else c) for i, (l, v, c) in enumerate(segs)]
    hatched = {i for i in range(len(segs)) if i not in sub_of}
    tot = sum(v for _, v, _ in segs) or 1

    def shade(i):
        base = segs[i][2]
        return [(s[0], s[1], s[2] if len(s) > 2 and s[2] else
                 (_mix(base, _SHADES[j % len(_SHADES)]) if base.startswith("#") and len(base) == 7 else base))
                for j, s in enumerate(sub_of[i])]

    W, H = x1 - x0, y1 - y0
    top = y0 + (22 if title_main else 0)
    subs = {}
    if len(idx) == 1:
        k = idx[0]
        sp = shade(k)
        leg_h = 18 * max(len(segs), len(sp)) + 30
        R = min(W * 0.27, (H - leg_h - (22 if title_main else 0)) / 2)
        r = R * 0.62
        mcx, mcy = x0 + R + 6, top + R
        scx, scy = x1 - r - 6 - W * 0.06, mcy
        before = sum(v for _, v, _ in segs[:k]) / tot * 2 * math.pi
        da = segs[k][1] / tot * 2 * math.pi
        out, _ = _pie(ex, mcx, mcy, R, segs, -before - da / 2, value_fmt, hatched=hatched)
        _funnel(ex, mcx, mcy, R, out[k][0], out[k][1], scx, scy, r, C["track"])
        _pie(ex, scx, scy, r, sp, -math.pi / 2, value_fmt)
        ex.occupy((mcx + R * 0.5, scy - r, scx, scy + r), "mark", "funnel")
        ptot = sum(v for _, v, _ in sp) or 1
        for (cx, items, t, ttl, hz) in ((mcx, segs, tot, title_main, hatched), (scx, sp, ptot, title_sub, ())):
            if ttl:
                ex.text(cx, top - 8, ttl, size=11.5, weight=700, anchor="middle", fill=C["ink"])
            lw = max(tw(f"{l}  {value_fmt(v / t)}", 10.5) for l, v, _ in items)
            _legend_rows(ex, cx - lw / 2 - 7, mcy + R + 22, items, t, value_fmt, hatched=hz)
        subs[segs[k][0]] = (scx, scy, r)
        ex.notes += 1
        return dict(main=(mcx, mcy, R), sub=(scx, scy, r), subs=subs)

    # ---- several slices broken out: main pie centred, sub-pies in a left and a right column
    n = len(idx)
    slots = {2: [0.0, math.pi], 3: [0.0, math.pi * 5 / 6, math.pi * 7 / 6],
             4: [-math.pi / 5, math.pi / 5, math.pi * 4 / 5, math.pi * 6 / 5]}[n]

    def mids(start):
        a, m = start, {}
        for i, (_, v, _) in enumerate(segs):
            da = v / tot * 2 * math.pi
            m[i] = a + da / 2
            a += da
        return [m[i] for i in idx]

    def adiff(a, b):
        return abs((a - b + math.pi) % (2 * math.pi) - math.pi)

    best = None
    for step in range(180):   # rotate the pie (and match slices to slots) so each broken-out slice faces its sub-pie
        st = -math.pi + step * math.pi / 90
        ms = mids(st)
        for perm in _perms(n):
            cost = sum(adiff(ms[j], slots[perm[j]]) ** 2 for j in range(n))
            if best is None or cost < best[0]:
                best = (cost, st, perm)
    _, start, perm = best
    slot_of = {idx[j]: slots[perm[j]] for j in range(n)}
    side = {i: ("R" if math.cos(a) > 0 else "L") for i, a in slot_of.items()}
    sp_of = {i: shade(i) for i in idx}
    ptot_of = {i: sum(v for _, v, _ in sp_of[i]) or 1 for i in idx}
    leg_w = {i: max([tw(l, 10.5) + 20 + tw(value_fmt(v / ptot_of[i]), 10.5, True) for l, v, _ in sp_of[i]]
                    + [tw(f"{segs[i][0]} {value_fmt(segs[i][1] / tot)}", 11.5, True)]) for i in idx}
    col_n = {s_: sum(1 for i in idx if side[i] == s_) for s_ in "LR"}
    main_leg_h = 24
    R = min((H - (22 if title_main else 0) - main_leg_h - 8) / 2, W * 0.17)
    mcx = (x0 + x1) / 2
    mcy = top + R
    share_max = max(segs[i][1] for i in idx)
    out, _ = _pie(ex, mcx, mcy, R, segs, start, value_fmt, hatched=hatched)
    fboxes = []
    for s_ in "LR":
        mine = sorted((i for i in idx if side[i] == s_), key=lambda i: math.sin(slot_of[i]))
        if not mine:
            continue
        cell = (y1 - y0) / len(mine)
        lw = max(leg_w[i] for i in mine)
        room = (W / 2 - R - 24 - lw - 10) / 2
        rmax = max(min(room, cell / 2 - 10, R * 0.78), 18)
        for j, i in enumerate(mine):
            r = rmax * max(0.62, math.sqrt(segs[i][1] / share_max))
            cy = y0 + cell * (j + 0.5)
            cx = (x0 + lw + 10 + rmax) if s_ == "L" else (x1 - lw - 10 - rmax)
            a0, a1 = out[i][0], out[i][1]
            fboxes.append(_funnel(ex, mcx, mcy, R, a0, a1, cx, cy, r,
                                  _mix(segs[i][2], 0.82) if segs[i][2].startswith("#") else C["track"]))
            _pie(ex, cx, cy, r, sp_of[i], -math.pi / 2, value_fmt)
            # title heads the legend on the outer side: above the sub-pie it would sit inside the funnel's box
            ttl = f"{segs[i][0]} {value_fmt(segs[i][1] / tot)}"
            ly = cy - 18 * len(sp_of[i]) / 2 + 4
            if s_ == "L":
                ex.text(cx - r - 10, ly, ttl, size=11.5, weight=700, anchor="end", fill=C["ink"])
                _legend_rows(ex, cx - r - 10, ly + 20, sp_of[i], ptot_of[i], value_fmt, right=True)
            else:
                ex.text(cx + r + 10, ly, ttl, size=11.5, weight=700, fill=C["ink"])
                _legend_rows(ex, cx + r + 10, ly + 20, sp_of[i], ptot_of[i], value_fmt)
            subs[segs[i][0]] = (cx, cy, r)
    if title_main:
        ex.text(mcx, top - 8, title_main, size=11.5, weight=700, anchor="middle", fill=C["ink"])
    # one row under the main pie: a column would reach down into the funnels' bounding boxes
    ws = [14 + tw(l, 10.5) + 6 + tw(value_fmt(v / tot), 10.5, True) for l, v, _ in segs]
    span = sum(ws) + 16 * (len(ws) - 1)
    lx, ly = mcx - span / 2, mcy + R + 20
    for fx0, fy0, fx1, fy1 in fboxes:   # drop below any funnel box the row would sit in
        if fx0 < lx + span and fx1 > lx and fy1 > ly - 14:
            ly = max(ly, fy1 + 14)
    for k, (it, w) in enumerate(zip(segs, ws)):
        _legend_rows(ex, lx, ly, [it], tot, value_fmt, hatched={0} if k in hatched else ())
        lx += w + 16
    ex.notes += 1
    first = subs[segs[idx[0]][0]]
    return dict(main=(mcx, mcy, R), sub=first, subs=subs)


def _perms(n):
    from itertools import permutations
    return list(permutations(range(n)))


def layered_area(ex, box, x, series, line=None, ridge=False, overlap=0.55, xfmt=None, yfmt=lambda v: fmt(v),
                 ytitle=None, labels=True, smooth=True, unit=None, line_unit=None):
    """Overlapping (not stacked) areas, back → front light → dark, optional same-unit line on top.

    series: [(name, values, color?)] drawn in order (put the biggest first). line: (name, values, color?) drawn as a
    dark-cased line on the same axis. Names sit at the right end of each layer.
    unit / line_unit: unit strings or METRICS dicts; explicit metadata takes precedence over series-name suffixes.
    A known unit in ytitle must still agree. Incompatible units raise before drawing; unknown units remain compatible.
    Use separate panels or explicitly base-normalized source data for different units, never an automatic second
    axis or silent rescaling. CFO = capex + FCF is a decomposition: prefer bridge / stacked_columns.
    ridge=True: ridgeline — each series gets its own baseline row (first on top), rows overlap by `overlap` of a row
    height, every series scaled to the same max; names on the left of each baseline, y axis dropped. Use to compare
    the shape / timing of several series (seasonality, spikes by year or segment). Returns the NAxes (normal) or the
    list of baselines (ridge)."""
    import re
    from ._axes import NAxes

    def declared_unit(value):
        if isinstance(value, dict):
            value = value.get("unit")
        if value is None or not str(value).strip():
            return None
        value = str(value).strip()
        aliases = {"USD": "$", "USD B": "$B", "USD M": "$M", "USD K": "$K",
                   "US$": "$", "US$B": "$B", "US$M": "$M", "US$K": "$K", "％": "%", "pct": "%"}
        return aliases.get(value, value)

    def suffix_unit(value):
        if not isinstance(value, str):
            return None
        value = value.strip().rstrip(")]）").rstrip()
        symbol = re.search(r"(US\$[BMK]?|\$[BMK]?|[%％])$", value)
        if symbol:
            return declared_unit(symbol.group(1))
        known = re.search(r"(?:^|[\s(\[（])((?:USD|EUR|CNY|RMB)(?: [BMK])?|[kMGT]Wh|亿元|万元|元|bps?|pp|pt)$",
                          value)
        return declared_unit(known.group(1)) if known else None

    series = list(series)
    area_unit = declared_unit(unit)
    title_unit = suffix_unit(ytitle)
    axis_unit = area_unit or title_unit
    known_units = {area_unit or suffix_unit(item[0]) or axis_unit for item in series}
    known_units.add(axis_unit)
    known_units.add(title_unit)
    if line:
        known_units.add(declared_unit(line_unit) or suffix_unit(line[0]))
    known_units.discard(None)
    if len(known_units) > 1:
        raise ValueError(f"layered_area: incompatible same-axis units {sorted(known_units)}；"
                         "请分 panel 展示，或用明确基期正规化后的同单位数据；不自动加第二轴或缩放。")
    C = ex.C
    pal = [C["light"], C["second"], C["main"], C["accent"]]
    series = [(s[0], s[1], s[2] if len(s) > 2 and s[2] else pal[k % len(pal)]) for k, s in enumerate(series)]
    x0, y0, x1, y1 = box
    xf = xfmt or (lambda v: f"{v:.0f}" if float(v).is_integer() else f"{v:g}")
    shown = set(x[:: max(1, len(x) // 8)]) | {x[-1]}
    if ridge:
        if len(series) < 2:
            raise ValueError("layered_area(ridge=True)：山脊图要 ≥2 条序列（各年/各国/各品类一行）——只有一条就用 lines/columns，"
                             "或从 research 里补上其他年份/对象的同口径序列")
        n = len(series)
        lw = max(tw(s_[0], 10.5, True) for s_ in series) + 12
        ax = NAxes.fit(ex, (x0 + lw - 36, y0, x1, y1), (min(x), max(x)), (0, 1), xticks=list(x), ytitle=False)
        for xx in x:   # x labels only: the rows carry their own baselines, no y grid
            if xx in shown:
                ex.text(ax.sx(xx), ax.y + ax.h + 16, xf(xx), size=10.5, fill=C["axis"], anchor="middle")
        ex.occupy((ax.x - 30, ax.y + ax.h + 0.5, ax.x + ax.w + 14, ax.y + ax.h + 22), "text", "axis-band")
        rh = ax.h / (1 + (n - 1) * (1 - overlap))      # one row's full height
        step = rh * (1 - overlap)
        bases = []
        mx = max(v for _, vs, _ in series for v in vs if v is not None) or 1
        dark = [C["main"], C["second"], C["accent"], C["third"], C["context"]]
        for k, (name, vals, col) in enumerate(series):
            base = ax.y + rh + k * step
            col = series[k][2] if len(series[k]) > 2 and col not in pal else dark[k % len(dark)]
            pts = [(ax.sx(xx), base - (v / mx) * rh * 0.95) for xx, v in zip(x, vals) if v is not None]
            top = _smooth(pts) if smooth else "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
            ex.path(top + f" L{pts[-1][0]:.1f},{base:.1f} L{pts[0][0]:.1f},{base:.1f} Z", fill=col, opacity=0.88,
                    register=False)
            ex.path(top, stroke="#FFFFFF", width=1.2, register=False)
            ex.line(ax.x, base, ax.x + ax.w, base, stroke=C["axis"], width=0.6, tag="grid")
            for (a, b), (c, e) in zip(pts, pts[1:]):
                ex._add("mark", (a, min(b, e), c, base), "area")
            if labels:
                ex.text(ax.x - 8, base - 3, name, size=10.5, weight=700, anchor="end", fill=C["ink"])
            bases.append(base)
        ex._ridge = dict(x=list(x), bases=bases, mx=mx, rh=rh, ax=ax)
        return bases
    ys = [v for _, vs, _ in series for v in vs if v is not None] + ([v for v in line[1] if v is not None] if line else [])
    right = (max(tw(s_[0], 10.5, True) for s_ in series + ([line] if line else [])) + 14) if labels else 0
    ax = NAxes.fit(ex, (x0, y0, x1 - right, y1), (min(x), max(x)), (0, max(ys) * 1.06), xticks=list(x),
                   ytitle=bool(ytitle))
    ax.frame(xfmt=lambda v: xf(v) if v in shown else "", yfmt=yfmt, ytitle=ytitle, zero_line=False)
    base_y = ax.sy(0)
    ends = []
    for name, vals, col in series:
        pts = [(ax.sx(xx), ax.sy(v)) for xx, v in zip(x, vals) if v is not None]
        top = _smooth(pts) if smooth else "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
        ex.path(top + f" L{pts[-1][0]:.1f},{base_y:.1f} L{pts[0][0]:.1f},{base_y:.1f} Z", fill=col, register=False)
        for (a, b), (c, e) in zip(pts, pts[1:]):
            ex._add("mark", (a, min(b, e), c, base_y), "area")
        ends.append([pts[-1][1], name, col])
    if line:
        name, vals, col = line[0], line[1], (line[2] if len(line) > 2 and line[2] else "#FFFFFF")
        pts = [(ax.sx(xx), ax.sy(v)) for xx, v in zip(x, vals) if v is not None]
        if smooth and len(pts) > 2:
            d = _smooth(pts)
            if col == "#FFFFFF":
                ex.path(d, stroke=C["ink"], width=3.2, register=False)
            ex.path(d, stroke=col, width=1.6, pts=pts)
        else:
            col = C["accent"] if col == "#FFFFFF" else col
            for start, end in zip(pts, pts[1:]):
                ex.line(*start, *end, stroke=col, width=1.6, tag="series", whole=True)
        ends.append([pts[-1][1], name, C["ink"] if col == "#FFFFFF" else col])
    if labels:
        ends.sort()
        for k in range(1, len(ends)):
            ends[k][0] = max(ends[k][0], ends[k - 1][0] + 14)
        for yy, name, col in ends:
            ex.text(ax.x + ax.w + 6, yy + 4, name, size=10.5, weight=700, fill=C["ink"] if _light(C, col) else col)
    return ax


def ridge_point(ex, k, xv, v):
    """Slide-canvas point of value v at x=xv on ridgeline row k (from layered_area(ridge=True)) — target for notes."""
    r = ex._ridge
    return r["ax"].sx(xv), r["bases"][k] - (v / r["mx"]) * r["rh"] * 0.95


def speech_note(ex, target, text, width=None, size=10.5, prefer=("N", "NE", "NW", "E", "W", "S"), dist=26,
                color=None):
    """Speech-bubble note: a rounded box with a tail pointing at target=(x, y), saying what this data point means
    ("+17% mainly from data-center capex"). Placed clear of labels and marks; ≤2 per chart, short text.
    The box is drawn with the page's light accent tone and a thin outline, the tail touches the point."""
    from ._place import _DIRS
    C = ex.C
    if width is None:   # one line up to ~13 CJK chars, two balanced lines beyond — never a fixed box that overflows
        full = tw(text, size)
        width = min(max(full + 4, 60), max(full / 2 + size * 2, 150), ex.w * 0.4)
    rows = wrap(text, size, width)
    if len(rows) > 1 and tw(rows[-1], size) < size * 2.2:   # a dangling "11" / "%": widen instead of orphaning it
        rows = wrap(text, size, width + tw(rows[-1], size) + size)
    pad = 6
    from ._page import frame_w   # the native text frame (wider than the glyphs) must stay inside the box
    W = max(max(tw(r, size) + 2 * pad, frame_w(r, size) + pad + 1) for r in rows)
    H = size * 1.25 * len(rows) + 2 * pad - size * 0.25
    tx, ty = target
    for e in ex.reg:   # a value label sitting on the point: point at its top instead of through it
        if e["kind"] == "text" and e["box"][0] - 2 <= tx <= e["box"][2] + 2 and e["box"][1] - 2 <= ty - 6 <= e["box"][3] + 6:
            ty = min(ty, e["box"][1] - 2)
    from ._page import _seg_hits_box

    def tail_cost(box):
        """The tail is a filled triangle from the box edge to the point: the server takes its bounding box for a
        shape covering every label under it — it must not cross text / ovals and should stay short."""
        mx_ = min(max(tx, box[0] + 12), box[2] - 12)
        my_ = min(max(ty, box[1] + 8), box[3] - 8)
        base_ = (mx_, box[3] if ty > box[3] else box[1] if ty < box[1] else my_)
        tri = (min(base_[0] - 6, tx), min(base_[1], ty), max(base_[0] + 6, tx), max(base_[1], ty))
        c_ = 0.0
        from ._place import _segs_cross
        for e in ex.reg:
            if e["kind"] == "line" and e.get("tag") in ("dim", "leader", "callout") and _segs_cross(base_, (tx, ty), *e["box"]):
                c_ += 120   # the tail crossing a CAGR / yoy arrow reads as pointing at the arrow
            if (e["kind"] == "text" or e["tag"] in ("oval", "badge")) and _seg_hits_box(base_, (tx, ty), e["box"], pad=1):
                c_ += 120
            elif e["kind"] == "text" and (tri[2] - tri[0]) > 14 and (tri[3] - tri[1]) > 14 and \
                    not (tri[2] <= e["box"][0] or e["box"][2] <= tri[0] or tri[3] <= e["box"][1] or e["box"][3] <= tri[1]):
                c_ += 40   # inside the tail's bounding box
        return c_ + 0.15 * max(abs(base_[0] - tx), abs(base_[1] - ty))

    best = None
    for k, d in enumerate((dist, dist * 1.5, dist * 2.2, dist * 3)):
        for i, key in enumerate(prefer):
            dx, dy, _ = _DIRS[key]
            n = math.hypot(dx, dy) or 1
            for si, sh in enumerate((0, -0.5, 0.5, -1, 1) if dy else (0,)):   # above/below: also slide sideways
                cx = tx + dx / n * d + dx * W / 2 + sh * W
                cy = ty + dy / n * d + dy * H / 2
                box = (cx - W / 2, cy - H / 2, cx + W / 2, cy + H / 2)
                c = ex.cost(box) + i * 3 + k * 20 + si * 4 + tail_cost(box)
                if best is None or c < best[0]:
                    best = (c, box)
        if best[0] < 60:
            break
    if best[0] >= 60:   # every ring collides (a bubble over the CAGR arrow / value labels is what the server blocks):
        x_lo, y_lo = (ex._panel or (0, 0, ex.w, ex.h))[:2]   # free-space search over the whole panel
        x_hi, y_hi = (ex._panel or (0, 0, ex.w, ex.h))[2:]
        for yy in range(int(y_lo), int(y_hi - H), 6):
            for xx in range(int(x_lo), int(x_hi - W), 8):
                box = (xx, yy, xx + W, yy + H)
                far = math.hypot(xx + W / 2 - tx, yy + H / 2 - ty)
                c = ex.cost(box) + far * 0.25 + 30 + tail_cost(box)
                if c < best[0]:
                    best = (c, box)
    _, (bx0, by0, bx1, by1) = best
    edge = C["accent"] if color is None else color
    fill = "#FFFFFF"
    # tail base on the box side facing the target
    mx = min(max(tx, bx0 + 12), bx1 - 12)
    my = min(max(ty, by0 + 8), by1 - 8)
    if ty > by1:
        base = [(mx - 6, by1), (mx + 6, by1)]
    elif ty < by0:
        base = [(mx + 6, by0), (mx - 6, by0)]
    elif tx > bx1:
        base = [(bx1, my + 6), (bx1, my - 6)]
    else:
        base = [(bx0, my - 6), (bx0, my + 6)]
    tip = (tx + (0 if abs(tx - mx) < 2 else (2 if tx < mx else -2)), ty + (-3 if ty > by1 else 3 if ty < by0 else 0))
    rr = 5
    box_d = (f"M{bx0 + rr:.1f},{by0:.1f} H{bx1 - rr:.1f} Q{bx1:.1f},{by0:.1f} {bx1:.1f},{by0 + rr:.1f} "
             f"V{by1 - rr:.1f} Q{bx1:.1f},{by1:.1f} {bx1 - rr:.1f},{by1:.1f} H{bx0 + rr:.1f} "
             f"Q{bx0:.1f},{by1:.1f} {bx0:.1f},{by1 - rr:.1f} V{by0 + rr:.1f} Q{bx0:.1f},{by0:.1f} {bx0 + rr:.1f},{by0:.1f} Z")
    tail_d = f"M{base[0][0]:.1f},{base[0][1]:.1f} L{tip[0]:.1f},{tip[1]:.1f} L{base[1][0]:.1f},{base[1][1]:.1f} Z"
    ex.path(box_d, fill=fill, stroke=edge, width=1, register=False)
    ex.path(tail_d, fill=fill, stroke=edge, width=1, register=False)
    # hide the outline where the tail joins the box
    ex.line(base[0][0], base[0][1], base[1][0], base[1][1], stroke=fill, width=1.6, register=False)
    ex.occupy((bx0, by0, bx1, by1), "mark", "speech")
    for i, r in enumerate(rows):
        ex.text(bx0 + pad, by0 + pad + size * 0.85 + i * size * 1.25, r, size=size, fill=C["ink"], register=False)
    ex._add("text", (bx0, by0, bx1, by1), "speech")
    ex.notes += 1
    return (bx0, by0, bx1, by1)
