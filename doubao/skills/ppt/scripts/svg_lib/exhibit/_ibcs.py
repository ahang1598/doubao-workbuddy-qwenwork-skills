"""IBCS (International Business Communication Standards) charts for business reviews / management reports.

Notation (SUCCESS "unify"): AC actual = solid dark; PY previous year = solid light grey; PL/BU plan/budget = hollow
outline; FC forecast = hatched outline. Only variances are coloured: good (favourable) / bad (unfavourable) roles.
Time runs horizontally (ibcs_columns, wbr_trend), structure vertically (ibcs_bars / row_table Scen + Variance).

    scen_bar(ex, x, y, w, h, "FC")                 # one bar in scenario notation
    scen_legend(ex, x, y, ["AC", "PY", "PL"])      # swatches + 实际/去年/预算
    ibcs_columns(ex, box, periods, AC, PY=..., PL=..., FC=..., variance="PL")   # columns + ΔPL + ΔPL% panels
    ibcs_bars(ex, box, items, AC, PL=..., variance="PL")                       # rows + ΔPL bars + ΔPL% pins
    wbr_trend(ex, box, ...)                        # Amazon WBR: last 6 weeks | trailing 12 months, one y-scale
    chart_head(ex, x, y, entity, measure, period)  # IBCS title block
"""

from __future__ import annotations

from ._axes import nice_ticks
from ._text import fmt, tw

SCENS = ("AC", "PY", "PL", "BU", "FC")
_ZH = {"AC": "实际", "PY": "去年", "PL": "预算", "BU": "预算", "FC": "预测"}


def _zh(ex):
    return bool(ex.body_lang)


def scen_name(ex, scen):
    return _ZH[scen] if _zh(ex) else scen


def _signed(d, f):
    body = str(f(abs(d))).lstrip("+−-± ")   # a value_fmt that already signs ("+6.1%") must not give "++6.1%" / "−+6.1%"
    return ("+" if d > 0 else ("−" if d < 0 else "±")) + body


def pct_text(p):
    """Signed percentage: +8%, −3.5% (one decimal below 10%)."""
    a = abs(p) * 100
    s = f"{a:.1f}" if 0 < a < 9.95 else f"{a:.0f}"
    if s in ("0", "0.0"):
        return "持平"   # never "±0%" / "−0%"
    return ("+" if p > 0 else "−") + s + "%"


def var_color(ex, d, favorable="up"):
    """good / bad role for a variance d (favorable='down' for cost-type measures); 0 → context grey."""
    if favorable not in ("up", "down"):
        raise ValueError(f"favorable={favorable!r} 只能是 'up'（越高越好，收入/利润）或 'down'（越低越好，成本/费用/退货）")
    if not d:
        return ex.C["context"]
    return ex.C["good"] if (d > 0) == (favorable == "up") else ex.C["bad"]


def _hatch_path(x, y, w, h, step):
    """'/' hatch segments clipped to the rect (computed, no <pattern>/<clipPath>) as one multi-subpath d string."""
    x0, y0, x1, y1 = x + 0.7, y + 0.7, x + w - 0.7, y + h - 0.7
    if x1 - x0 < 1 or y1 - y0 < 1:
        return ""
    parts = []
    c = x0 + y0 + step * 0.6
    while c < x1 + y1:
        xa, xb = max(x0, c - y1), min(x1, c - y0)
        if xb - xa > 0.4:
            parts.append(f"M{xa:.1f},{c - xa:.1f} L{xb:.1f},{c - xb:.1f}")
        c += step
    return " ".join(parts)


def scen_bar(ex, x, y, w, h, scen="AC", color=None, register=True, hatch=None):
    """One bar (vertical or horizontal) in IBCS scenario notation. AC solid `color` (default main); PY solid py grey;
    PL/BU hollow (white fill, 1.4 outline); FC hatched outline (diagonal hatch, spacing `hatch` ≈ 4.5 canvas units,
    widened on big bars so a bar stays a few dozen strokes). Negative w/h are normalised. Returns the rect box."""
    scen = str(scen).upper()
    if scen not in SCENS:
        raise ValueError(f"scen_bar: scen={scen!r} 只能是 AC（实际）/PY（去年）/PL 或 BU（预算）/FC（预测）")
    if w < 0:
        x, w = x + w, -w
    if h < 0:
        y, h = y + h, -h
    C = ex.C
    col = color or C["main"]
    if scen == "AC":
        ex.rect(x, y, w, h, col, register=False)
    elif scen == "PY":
        ex.rect(x, y, w, h, color or C["py"], register=False)
    else:
        sw = 1.4 if scen in ("PL", "BU") else 1.1
        ex.rect(x + sw / 2, y + sw / 2, max(w - sw, 0.5), max(h - sw, 0.5), "#FFFFFF", register=False, stroke=col,
                stroke_width=sw)
        if scen == "FC":
            step = hatch or max(4.5, (w + h) / 36)
            d = _hatch_path(x, y, w, h, step)
            if d:
                ex.path(d, stroke=col, width=0.8, register=False)
    if register and w > 0 and h > 0:
        ex._add("mark", (x, y, x + w, y + h), "rect")
    return (x, y, x + w, y + h)


def scen_legend(ex, x, y, scens, size=10.5, gap=14, color=None):
    """Scenario swatches in the same notation: scens = ["AC", "PY", "PL", "FC"] or [("AC", "2026 实际"), ...].
    Labels default to 实际/去年/预算/预测 (zh deck) or AC/PY/PL/FC. y = text baseline. Returns end x."""
    k = size * 0.95
    for s in scens:
        sc, lab = (s if isinstance(s, (tuple, list)) else (s, None))
        lab = lab or scen_name(ex, str(sc).upper())
        scen_bar(ex, x, y - size * 0.78, k, k, sc, color=color, register=False, hatch=3)
        ex.text(x + k + 5, y, lab, size=size, fill=ex.C["text"])
        x += k + 5 + tw(lab, size) + gap
    return x


def _frame_subtitle():
    from . import _frame
    return getattr(_frame, "LAST_SUBTITLE", "") or ""


def _check_ref_vs_subtitle(fn, PY, PL):
    """Subtitle says year-on-year but only PL was passed: last year's numbers went in as the plan (header ΔPL%)."""
    sub = _frame_subtitle()
    import re
    if PL is not None and PY is None and re.search(r"去年|同比|上年|\bPY\b|YoY|prior year|last year", sub, re.I) \
            and not re.search(r"预算|计划|目标|\bPL\b|\bBU\b|budget|plan|target", sub, re.I):
        raise ValueError(f"{fn}：副标题说同比，但传的是 PL：去年数据用 PY=（表头随之变成 ΔPY / ΔPY%）")


def chart_head(ex, x, y, entity, measure, period, size=10.5):
    """IBCS title block (top-left of a chart): entity bold / measure + unit / period + scenarios
    (e.g. "华东区", "净收入，百万元", "2026 年 1–9 月 · AC vs PL"). y = top. Returns the bottom y.
    On a frame() page whose subtitle already names the measure / entity, nothing is drawn (the subtitle is the chart
    title; a second one inside the chart only repeats it) and y is returned unchanged."""
    sub = _frame_subtitle()
    head = lambda t: str(t or "").replace("**", "").split("，")[0].split(",")[0].strip()
    if sub and any(head(t) and head(t) in sub for t in (entity, measure)):
        return y
    lh = size * 1.32
    yy = y + size
    for t, w, c in ((entity, 700, ex.C["ink"]), (measure, 400, ex.C["text"]), (period, 400, ex.C["sub"])):
        if t:
            ex.text(x, yy, t, size=size, weight=w, fill=c)
            yy += lh
    return yy - lh + size * 0.3


def scale_marker(ex, x, y, text=None, size=10, color=None):
    """Scaling indicator for a page whose panels use different scales: a '//' break mark + "比例不同" note.
    y = text baseline. Returns end x."""
    C = ex.C
    col = color or C["sub"]
    for dx in (0, 4):
        ex.line(x + dx, y + 1, x + dx + 5, y - size * 0.8, stroke=col, width=1.1, register=False)
    ex.occupy((x, y - size * 0.8, x + 9, y + 1), "mark", "legend")
    t = text or ("比例不同" if _zh(ex) else "different scale")
    ex.notes += 1
    return ex.text(x + 13, y, t, size=size, fill=col)


# ===================================================================================== time series (columns)


def _seq(name, v, n):
    if v is None:
        return [None] * n
    if len(v) != n:
        raise ValueError(f"ibcs_columns: {name} 有 {len(v)} 个值，periods 有 {n} 个——逐期对齐（缺的期写 None）")
    return list(v)


def _var_panel(ex, x_a, x_b, top, bot, cents, w, vals, kind, favorable, label_f, head, bold=None, size=10):
    """One variance panel (no grid, no ticks): bars (kind='abs') or pins (kind='pct') from a zero line."""
    C = ex.C
    ds = [v for v in vals if v is not None]
    if not ds:
        return None
    hi, lo = max(ds + [0]), min(ds + [0])
    r = 3.4
    pad_t = (size + 5 + (r if kind == "pct" else 0)) if hi > 0 else 3
    pad_b = (size + 5 + (r if kind == "pct" else 0)) if lo < 0 else 3
    span = max(bot - top - pad_t - pad_b, 8)
    k = span / ((hi - lo) or 1)
    zy = top + pad_t + hi * k
    sy = lambda v: zy - v * k  # noqa: E731
    ex.line(x_a, zy, x_b, zy, stroke=C["axis"], width=0.9, tag="grid")
    ex.text(x_a - 8, zy + size * 0.36, head, size=10.5, weight=700, fill=C["ink"], anchor="end")
    for i, (cx, v) in enumerate(zip(cents, vals)):
        if v is None:
            continue
        col = var_color(ex, v, favorable)
        yv = sy(v)
        wt = 700 if bold and bold[i] else 400
        if kind == "abs":
            ex.rect(cx - w / 2, min(zy, yv), w, max(abs(yv - zy), 1.2), col)
            ty = yv - 4 if v >= 0 else yv + size + 1
        else:
            ex.line(cx, zy, cx, yv, stroke=col, width=1.6, tag="grid")
            ex.circle(cx, yv, r, col)
            ty = yv - r - 4 if v >= 0 else yv + r + size + 1
        ex.text(cx, ty, label_f(v), size=size, weight=wt, fill=C["text"], anchor="middle")
    return dict(zero=zy, sy=sy)


def ibcs_columns(ex, box, periods, AC, PY=None, PL=None, FC=None, variance="auto", pct=True, favorable="up",
                 value_fmt=lambda v: fmt(v), focus=None, legend=True, labels=None, size=10.5):
    """IBCS time-series chart: one column per period in scenario notation + variance panels above it.

    AC: actuals (None for future periods); FC: forecasts for those periods (hatched). PY drawn as a grey bar offset
    left behind AC; PL as a hollow bar offset right behind AC. variance="PY" | "PL" | None | "auto" (PL if given,
    else PY): absolute variance bars (ΔPL, good/bad colours from a zero line, labelled +x/−x) and, with pct=True, a
    relative variance pin panel (ΔPL%). Variance panels share the column x positions and have their own scale.
    favorable="down" for cost-type measures (an overrun is bad). focus: period label / index / callable → shaded
    period across all panels and bold labels. labels: {"AC": "2026 实际", ...} override legend names.
    Returns dict(centers, bw, sy, base, main_value, ref, deltas, pcts, panels).
    """
    C = ex.C
    n = len(periods)
    if n < 2:
        raise ValueError("ibcs_columns 少于 2 期——单期实际 vs 预算用 columns 成组柱（target_columns），多对象可用 ibcs_bars")
    if n == 2:   # two periods = one difference: counted like two-bar columns for the page precheck
        ex.two_bar = getattr(ex, "two_bar", 0) + 1
    AC, PY, PL, FC = (_seq(nm, v, n) for nm, v in (("AC", AC), ("PY", PY), ("PL", PL), ("FC", FC)))
    main = [a if a is not None else f for a, f in zip(AC, FC)]
    scen = ["AC" if a is not None else ("FC" if f is not None else None) for a, f in zip(AC, FC)]
    if sum(v is not None for v in main) < 2:
        raise ValueError("ibcs_columns：AC/FC 合计少于 2 期有值——至少两期实际或预测")
    if variance == "auto":
        variance = "PL" if any(v is not None for v in PL) else ("PY" if any(v is not None for v in PY) else None)
    if variance not in (None, "PY", "PL"):
        raise ValueError(f"ibcs_columns: variance={variance!r} 只能是 'PY' / 'PL' / None")
    ref = {"PY": PY, "PL": PL}.get(variance)
    if variance and not any(v is not None for v in ref):
        raise ValueError(f"ibcs_columns: variance='{variance}' 但没有传 {variance}=[...]——补上参照数据，或改 variance=None")
    var_color(ex, 0, favorable)   # validates favorable
    ex.notes += 1
    x0, y0, x1, y1 = box
    zh = _zh(ex)
    # ---- vertical layout
    leg_h = 20 if legend else 0
    gutter = (max(tw(f"Δ{variance}%", 10.5, True), tw(f"Δ{variance}", 10.5, True)) + 12) if variance else 0
    H = y1 - y0 - leg_h
    gap_v = 8
    h_pct = H * 0.2 if (variance and pct) else 0
    h_abs = H * (0.22 if pct else 0.27) if variance else 0
    lab_h = 20
    p_top = y0 + leg_h
    a_top = p_top + h_pct + (gap_v if h_pct else 0)
    m_top = a_top + h_abs + (gap_v if h_abs else 0)
    m_bot = y1 - lab_h
    if m_bot - m_top < 50:
        raise ValueError(f"ibcs_columns：主图只剩 {m_bot - m_top:.0f}px 高——加大 Exhibit(h=)（建议 ≥300）或 pct=False")
    xa, xb = x0 + gutter, x1
    step = (xb - xa) / n
    bw = min(step * 0.52, 46)
    has_py, has_pl = any(v is not None for v in PY), any(v is not None for v in PL)
    off = bw * 0.3
    # ---- focus band (behind everything)
    def is_focus(i):
        if focus is None:
            return False
        if callable(focus):
            return bool(focus(periods[i]))
        return focus == i if isinstance(focus, int) else str(focus) == str(periods[i])
    foc = [is_focus(i) for i in range(n)]
    for i in range(n):
        if foc[i]:
            ex.rect(xa + i * step + 1, p_top, step - 2, y1 - p_top, C["band"], register=False)
    # ---- main chart
    vals = [v for v in main + PY + PL if v is not None]
    hi, lo = max(vals + [0]), min(vals + [0])
    head = 16
    k = (m_bot - m_top - head - (14 if lo < 0 else 0)) / ((hi - lo) or 1)
    base = m_top + head + hi * k
    sy = lambda v: base - v * k  # noqa: E731
    cents, ac_c = [], []
    for i in range(n):
        cx = xa + (i + 0.5) * step
        cents.append(cx)
        n_ref = (1 if has_py else 0) + (1 if has_pl else 0)
        ax_ = cx - bw / 2 + (off / 2 if n_ref == 1 and has_py else (-off / 2 if n_ref == 1 else 0))
        if has_py and PY[i] is not None:
            scen_bar(ex, ax_ - off, sy(PY[i]), bw, sy(0) - sy(PY[i]), "PY")
        if has_pl and PL[i] is not None:
            scen_bar(ex, ax_ + off, sy(PL[i]), bw, sy(0) - sy(PL[i]), "PL")
        ac_c.append(ax_ + bw / 2)
        if main[i] is None:
            continue
        scen_bar(ex, ax_, sy(main[i]), bw, sy(0) - sy(main[i]), scen[i])
        top_v = max(v for v in (main[i], PY[i], PL[i]) if v is not None)
        if main[i] >= 0:
            ty = sy(max(top_v, 0)) - 5
        else:
            ty = sy(main[i]) + 13
        ex.text(ac_c[-1], ty, value_fmt(main[i]), size=size, weight=700 if foc[i] else 400,
                fill=C["ink"] if scen[i] == "AC" else C["sub"], anchor="middle")
    ex.line(xa, base, xb, base, stroke=C["axis"], width=0.9, tag="axis")
    for i, cx in enumerate(cents):
        ex.text(cx, m_bot + 14, str(periods[i]), size=size, weight=700 if foc[i] else 400,
                fill=C["ink"] if foc[i] else C["text"], anchor="middle")
    # ---- variance panels
    deltas = [(m - r) if (m is not None and r is not None) else None for m, r in zip(main, ref or [None] * n)]
    pcts = [(d / r) if (d is not None and r) else None for d, r in zip(deltas, ref or [None] * n)]
    panels = {}
    if variance:
        vw = bw * 0.72
        panels["abs"] = _var_panel(ex, xa, xb, a_top, a_top + h_abs, ac_c, vw, deltas, "abs", favorable,
                                   lambda d: _signed(d, value_fmt), f"Δ{variance}", bold=foc)
        if pct:
            panels["pct"] = _var_panel(ex, xa, xb, p_top, p_top + h_pct, ac_c, vw, pcts, "pct", favorable,
                                       pct_text, f"Δ{variance}%", bold=foc)
    if legend:
        items = [("AC", (labels or {}).get("AC"))]
        if any(s == "FC" for s in scen):
            items.append(("FC", (labels or {}).get("FC")))
        if has_py:
            items.append(("PY", (labels or {}).get("PY")))
        if has_pl:
            items.append(("PL", (labels or {}).get("PL")))
        scen_legend(ex, xa, y0 + 12, items, size=10.5)
    return dict(centers=ac_c, bw=bw, sy=sy, base=base, main_value=main, scen=scen, ref=ref, deltas=deltas, pcts=pcts,
                panels=panels, box_main=(xa, m_top, xb, m_bot), zh=zh)


# ===================================================================================== structure (rows)


def ibcs_bars(ex, box, items, AC, PY=None, PL=None, variance="auto", pct=True, favorable="up",
              value_fmt=lambda v: fmt(v), sort=True, total=None, focus=None, legend=True, label_header="",
              var_width=None, title=None):
    """IBCS structure chart (regions / products / channels): one row per item, AC bar with its reference (PL hollow
    outline offset below / PY grey offset above), then — aligned per row — an absolute variance column (good/bad bars
    from a centre axis) and a relative variance pin column. sort=True orders rows by AC descending. total=True (or a
    label such as "合计") adds a total row under a rule (values summed; variance as coloured text).
    focus: callable(label) -> bool (other rows dimmed). title=(entity, measure, period): an IBCS chart_head block
    above the chart — default None (on a frame page the subtitle is the chart title; it is skipped there anyway).
    Variance headers follow the reference used (ΔPY / ΔPY% vs last year, ΔPL / ΔPL% vs plan; 对去年 / 对目标 on a Chinese chart); a frame subtitle that
    says 同比 / 去年 with only PL= passed raises. Built on row_table(Label, Scen, Variance, Variance).
    Returns the row_table result plus "rows" and "columns"."""
    from ._table import Label, Scen, Variance, row_table
    n = len(items)
    if n < 2:
        raise ValueError("ibcs_bars 少于 2 行——单个对象的实际 vs 预算用 columns 成组柱（target_columns）或 big_number + 差异一句话")
    for nm, v in (("AC", AC), ("PY", PY), ("PL", PL)):
        if v is not None and len(v) != n:
            raise ValueError(f"ibcs_bars: {nm} 有 {len(v)} 个值，items 有 {n} 个——逐行对齐（缺的写 None）")
    _check_ref_vs_subtitle("ibcs_bars", PY, PL)
    if variance == "auto":
        variance = "PL" if PL is not None else ("PY" if PY is not None else None)
    if variance not in (None, "PY", "PL"):
        raise ValueError(f"ibcs_bars: variance={variance!r} 只能是 'PY' / 'PL' / None")
    if variance and {"PY": PY, "PL": PL}[variance] is None:
        raise ValueError(f"ibcs_bars: variance='{variance}' 但没有传 {variance}=[...]——补上参照数据，或改 variance=None")
    rows = [dict(label=str(it), ac=AC[i], py=PY[i] if PY else None, pl=PL[i] if PL else None)
            for i, it in enumerate(items)]
    if sort:
        rows.sort(key=lambda r: -(r["ac"] if r["ac"] is not None else float("-inf")))
    ref_kind = variance or ("PL" if PL is not None else ("PY" if PY is not None else None))
    ref_key = ref_kind.lower() if ref_kind else None
    x0, y0, x1, y1 = box
    vw = var_width or min(150, (x1 - x0) * 0.22)
    cols = [Label("label", header=label_header, align="end"),
            Scen("ac", ref=ref_key, ref_kind=ref_kind or "PL", fmt=value_fmt)]
    if variance:
        cols.append(Variance("ac", ref_key, favorable=favorable, fmt=lambda d: _signed(d, value_fmt), width=vw,
                             ref_name=variance))
        if pct:
            cols.append(Variance("ac", ref_key, pct=True, favorable=favorable, width=vw, ref_name=variance))
    tot = None
    if total:
        def s(k):
            vs = [r[k] for r in rows if r[k] is not None]
            return sum(vs) if vs else None
        tot = dict(label=total if isinstance(total, str) else ("合计" if _zh(ex) else "Total"), ac=s("ac"),
                   py=s("py"), pl=s("pl"))
    top = y0
    if title:
        top = chart_head(ex, x0, top, *(list(title) + [None, None, None])[:3]) + (8 if not _frame_subtitle() else 0)
    if legend:
        sc = ["AC"] + ([ref_kind] if ref_kind else [])
        scen_legend(ex, x0, top + 12, sc)
        top = top + 20
    t = row_table(ex, (x0, top, x1, y1), rows, cols, total=tot,
                  focus=(lambda r: focus(r["label"])) if focus else None)
    t.update(rows=rows, columns=cols)
    if variance:   # title check: "X 带动 / X 放量" vs the row with the largest growth vs the reference
        from ._page import add_fact, growth_items
        g = growth_items([r["label"] for r in rows], [r[ref_key] for r in rows], [r["ac"] for r in rows])
        if len(g) >= 2:
            add_fact(ex, {"kind": "growth", "items": g, "ref": variance})
    return t


# ===================================================================================== WBR trend


def wbr_trend(ex, box, recent_labels, recent_ac, recent_py, long_labels, long_ac, long_py, target=None,
              value_fmt=lambda v: fmt(v), name=None, heads=None, favorable="up", split=0.36, gap=30, size=10.5):
    """Amazon WBR chart: left = recent periods (≈6 weeks), right = trailing 12 months, ONE shared y-scale (ticks on
    the left only). AC solid line with dots + last value and YoY at each panel's end; PY thin grey line; target =
    dashed line with label (number or (value, "label")). heads=("近 6 周", "近 12 个月") override panel headers;
    name = legend name of AC (default 今年 / This year). Sets ex.related (shared scale) and counts one annotation.
    Returns dict(sy, left=xs, right=xs, ticks)."""
    C = ex.C
    zh = _zh(ex)
    for nm, labs, a, p, need in (("recent", recent_labels, recent_ac, recent_py, 3),
                                 ("long", long_labels, long_ac, long_py, 4)):
        if len(labs) != len(a) or (p is not None and len(p) != len(a)):
            raise ValueError(f"wbr_trend: {nm} 的 labels / AC / PY 个数不一致（{len(labs)} / {len(a)} / "
                             f"{len(p) if p is not None else '-'}）——逐期对齐，缺的写 None")
        if sum(v is not None for v in a) < need:
            raise ValueError(f"wbr_trend: {nm} 段少于 {need} 个实际值——左栏建议近 6 周、右栏近 12 个月")
    var_color(ex, 0, favorable)
    ex.related = True
    ex.notes += 1
    tv, tlab = (target if isinstance(target, (tuple, list)) else (target, None)) if target is not None else (None, None)
    vals = [v for s in (recent_ac, recent_py or [], long_ac, long_py or []) for v in s if v is not None]
    if tv is not None:
        vals.append(tv)
    lo, hi = min(vals), max(vals)
    vmin = lo - (hi - lo) * 0.2 if lo > 0.45 * hi else 0
    ticks = nice_ticks(hi, 4, max(vmin, 0) if lo >= 0 else vmin)
    x0, y0, x1, y1 = box
    ytw = max(tw(value_fmt(t), size) for t in ticks) + 8
    p_top, p_bot = y0 + 32, y1 - 20
    sy = lambda v: p_bot - (v - ticks[0]) / (ticks[-1] - ticks[0]) * (p_bot - p_top)  # noqa: E731
    W = x1 - x0 - ytw - gap
    lw = W * split
    panels = [(x0 + ytw, x0 + ytw + lw, recent_labels, recent_ac, recent_py),
              (x0 + ytw + lw + gap, x1, long_labels, long_ac, long_py)]
    hd = heads or (("近 %d 周" % len(recent_labels), "近 %d 个月" % len(long_labels)) if zh else
                   ("Last %d weeks" % len(recent_labels), "Trailing %d months" % len(long_labels)))

    def last_lab(ac, py):
        i = max(j for j, v in enumerate(ac) if v is not None)
        rows = [(value_fmt(ac[i]), 700, C["ink"])]
        if py is not None and py[i]:
            p = ac[i] / py[i] - 1
            rows.append(((("同比 " if zh else "") + pct_text(p) + ("" if zh else " YoY")), 700,
                         var_color(ex, p, favorable)))
        return i, rows

    for t in ticks:
        ex.text(x0 + ytw - 6, sy(t) + size * 0.35, value_fmt(t), size=size, fill=C["axis"], anchor="end")
    out = []
    tgt_segs = []
    for k, (a, b, labs, ac, py) in enumerate(panels):
        i_last, rows = last_lab(ac, py)
        pad_r = max(tw(t, 10.5, True) for t, _, _ in rows) + 10
        pa, pb = a + 6, b - pad_r
        n = len(labs)
        stp = (pb - pa) / max(n - 1, 1)
        xs = [pa + j * stp for j in range(n)]
        ex.text(a, y0 + 12, hd[k], size=11, weight=700, fill=C["ink"])
        for t in ticks:
            if t != ticks[0]:
                ex.line(a, sy(t), b, sy(t), stroke=C["grid"], width=0.7, tag="grid")
        ex.line(a, p_bot, b, p_bot, stroke=C["axis"], width=0.9, tag="axis")
        if tv is not None:
            ex.line(a, sy(tv), pb + 4, sy(tv), stroke=C["accent"], width=1.1, dash="4,3", tag="grid")
            tgt_segs.append((a, pb))
        if py is not None:
            pts = [(x, sy(v)) for x, v in zip(xs, py) if v is not None]
            for start, end in zip(pts, pts[1:]):
                ex.line(*start, *end, stroke=C["context"], width=1.3, tag="series", whole=True)
        pts = [(x, sy(v)) for x, v in zip(xs, ac) if v is not None]
        for start, end in zip(pts, pts[1:]):
            ex.line(*start, *end, stroke=C["main"], width=2.2, tag="series", whole=True)
        for p, q in pts:
            ex.circle(p, q, 2.6, C["main"])
        lx, ly = xs[i_last] + 7, sy(ac[i_last])
        ys = [ly + 3.6, ly + 3.6 + 12.5] if len(rows) > 1 else [ly + 3.6]
        if len(rows) > 1 and py[i_last] is not None and sy(py[i_last]) < ly:   # PY above: put YoY above the value
            ys = [ly + 3.6, ly + 3.6 - 12.5]
        for (t, w, c), yy in zip(rows, ys):
            ex.text(lx, yy, t, size=10.5 if w == 700 and c == C["ink"] else 10, weight=w, fill=c)
        # x labels, thinned when crowded
        wmax = max(tw(str(l), 10) for l in labs)
        every = 1 if wmax + 4 <= stp else int(wmax // max(stp, 1)) + 1
        for j, (x, l) in enumerate(zip(xs, labs)):
            if j % every == 0 or j == n - 1:
                if j != n - 1 and every > 1 and (n - 1 - j) < every:
                    continue
                ex.text(x, p_bot + 14, str(l), size=10, fill=C["axis"], anchor="middle")
        out.append(xs)
    if k == 1:
        ex.line(panels[1][0] - gap / 2, y0 + 2, panels[1][0] - gap / 2, p_bot, stroke=C["grid"], width=0.8, tag="grid")
    if tv is not None:
        lab = tlab or ((f"目标 {value_fmt(tv)}") if zh else f"Target {value_fmt(tv)}")
        w = tw(lab, 10) + 4
        yy = sy(tv)
        cands = []
        for a, pb in tgt_segs:
            cands += [(a + 2, yy - 4), (pb - w, yy - 4), (a + 2, yy + 12), (pb - w, yy + 12)]
        best = min(cands, key=lambda p: ex.cost((p[0], p[1] - 9, p[0] + w, p[1] + 2)))
        ex.text(best[0], best[1], lab, size=10, fill=C["accent"])
    leg = [(name or ("今年" if zh else "This year"), C["main"], "line"), (("去年" if zh else "Last year"),
                                                                          C["context"], "line")]
    if tv is not None:
        leg.append(((tlab or ("目标" if zh else "Target")).split(" ")[0], C["accent"], "dash"))
    from ._marks import legend as _legend
    lw_ = sum(tw(t, 10) + 12 + 9 + 16 for t, _, _ in leg)
    _legend(ex, x1 - lw_ + 16, y0 + 12, leg, size=10)
    return dict(sy=sy, left=out[0], right=out[1], ticks=ticks)


# ===================================================================================== variance bridge


def ibcs_bridge(ex, box, start, steps, end=None, start_scen="PL", end_scen="AC", favorable="up",
                value_fmt=lambda v: fmt(v), share="auto", focus=None, ymin=None, size=10.5):
    """IBCS variance bridge in one call: start bar (budget PL hollow / PY grey) → driver deltas (good / bad colours)
    → end bar (AC solid). start = ("预算", 1180); steps = [("销量", 38), ("价格", -14), ...]; end = ("实际", 1204)
    or None (= start + Σ steps; given ends are checked). favorable="down" for cost bridges (an increase is bad).
    share="auto" prints each driver's share of the net variance only when all drivers push the same way (mixed signs
    give shares like 173% / −15% that read wrong); focus = driver label(s) drawn bold with a badge.
    ymin: axis start (default: auto-truncated just below the lowest running level, with a scale_marker note so the
    truncation is declared). business-deck (set_profile("deck")): favourable deltas main, unfavourable grey.
    Returns dict(ax, centers, tops, net)."""
    from ._axes import Axes
    from ._marks import waterfall
    if len(steps) < 2:
        raise ValueError("ibcs_bridge 少于 2 个驱动因素——只有一项时直接写'实际比预算 +x，全部来自 X'，用 ibcs_columns 或 big_number")
    C = ex.C
    s_lab, s_val = start
    net = sum(v for _, v in steps)
    e_lab, e_val = end if end is not None else (("实际" if _zh(ex) else "Actual"), s_val + net)
    if abs(e_val - (s_val + net)) > 0.005 * max(abs(e_val), 1):
        raise ValueError(f"ibcs_bridge：{s_lab} {s_val} + 各项 {net:+.4g} ≠ {e_lab} {e_val}——补上缺的因素或加一项'其他'")
    if share == "auto":
        share = bool(net) and all((v >= 0) == (net >= 0) for _, v in steps)
    run, lows, highs = s_val, [s_val, e_val], [s_val, e_val]
    for _, v in steps:
        run += v
        lows.append(run)
        highs.append(run)
    hi = max(highs)
    lo_run = min(lows)
    if ymin is None:   # truncate only when the bars would otherwise be nearly equal heights
        span = hi - lo_run
        if lo_run <= 0 or span > 0.35 * hi:
            ymin = 0
        else:
            import math
            raw = max(lo_run - span * 1.2, 0)
            step = 10 ** math.floor(math.log10(max(span, 1e-9)))
            ymin = math.floor(raw / step) * step
    x0, y0, x1, y1 = box
    top_pad = 34 if share else 22
    ax = Axes.fit(ex, (x0, y0 + 6, x1, y1), hi * 1.02 if ymin == 0 else hi + (hi - ymin) * 0.04, ymin=ymin,
                  ticks=[ymin, hi], left=4, top_pad=top_pad)
    lab = [s_lab] + [l for l, _ in steps] + [e_lab]
    bands = ax.bands(len(lab), pad=0.42)
    cents = [b[0] + b[1] / 2 for b in bands]
    from . import _layouts as _ly
    good, bad = (C["main"], C["context"]) if _ly.PROFILE.get("speech") else (C["good"], C["bad"])   # deck: no red/green
    up, down = (good, bad) if favorable == "up" else (bad, good)
    wsteps = [("total", s_lab, s_val)] + [("delta", l, v) for l, v in steps] + [("total", e_lab, e_val)]
    tops = waterfall(ax, cents, bands[0][1], wsteps, colors={"total": C["main"], "up": up, "down": down}, truncated_ok=True,
                     value_fmt=value_fmt, share=share)
    if start_scen != "AC":
        ex.rect(bands[0][0], tops[0], bands[0][1], ax.sy(ax.ymin) - tops[0], "#FFFFFF", register=False)
        scen_bar(ex, bands[0][0], tops[0], bands[0][1], ax.sy(ax.ymin) - tops[0], start_scen, register=False)
    if end_scen != "AC":
        ex.rect(bands[-1][0], tops[-1], bands[-1][1], ax.sy(ax.ymin) - tops[-1], "#FFFFFF", register=False)
        scen_bar(ex, bands[-1][0], tops[-1], bands[-1][1], ax.sy(ax.ymin) - tops[-1], end_scen, register=False)
    ex.line(ax.x, ax.sy(ax.ymin), ax.x + ax.w, ax.sy(ax.ymin), stroke=C["axis"], width=0.9, tag="axis")
    ax.xlabels(cents, lab, size=size)
    if ymin:
        scale_marker(ex, x0, y0 + 10, text=(f"纵轴自 {value_fmt(ymin)} 起" if _zh(ex) else f"axis starts at {value_fmt(ymin)}"))
    if focus is not None:   # the driver the title names: outline its bar (no extra label to collide with)
        keys = {focus} if isinstance(focus, str) else set(focus)
        lv = s_val
        for k, (l, v) in enumerate(steps, 1):
            if l in keys:
                a_, b_ = sorted((ax.sy(lv), ax.sy(lv + v)))
                bx, bw = bands[k]
                ex.add(f'<rect x="{bx - 3:.1f}" y="{a_ - 3:.1f}" width="{bw + 6:.1f}" height="{b_ - a_ + 6:.1f}" '
                       f'fill="none" stroke="{C["ink"]}" stroke-width="1.3"/>')
            lv += v
    ex.notes += 1
    return {"ax": ax, "centers": cents, "tops": tops, "net": net}


def pace(ex, box, periods, AC, PL, PY=None, target=None, value_fmt=lambda v: fmt(v), unit="", size=10.5, base=None):
    """YTD pace: cumulative actual vs cumulative plan over the year, plus the cumulative gap as good/bad bars beneath.
    Top (≈70%): cumulative PL grey line, optional cumulative PY light grey, cumulative AC solid main line up to the
    last actual period; a dashed accent "required pace" line runs from the last actual to the full-year plan (or
    target=), labelled with the amount needed per remaining period. Bottom (≈30%): ΔPL cumulative (AC − PL) bars.
    periods: all period labels of the year. AC, PL and PY: per-period flows; difference already-YTD inputs first.
    AC: None / shorter list for future periods; target: full-year total, not a final-period flow; may differ from sum(PL).
    With annual guidance and no genuine phased plan, do not fabricate PL or budget variance;
    use actual vs annual goal and needed remainder instead.
    base=(label, ac, pl[, py]): an earlier period known only as a total (e.g. ("1–6月", 15820, 15600)) — becomes the
    first point, cumulation starts from it. Returns dict(ax, cum_ac, cum_pl, gap, need, goal)."""
    from ._more import lines
    from ._place import callout
    C = ex.C
    if base is not None:
        periods = [base[0]] + list(periods)
        AC = [base[1]] + list(AC)
        PL = [base[2]] + list(PL)
        if PY is not None:
            PY = [base[3] if len(base) > 3 else None] + list(PY)
    n = len(periods)
    AC = list(AC) + [None] * (n - len(AC))
    k = max(i for i, v in enumerate(AC) if v is not None)
    k0 = 1 if base is not None else 0      # the base point is a lump sum: average per period from the periods after it
    cum = lambda v: [None if v[i] is None else round(sum(x or 0 for x in v[:i + 1]), 6) for i in range(len(v))]
    ca, cp = cum(AC), cum(PL)
    goal = target if target is not None else cp[-1]
    X = list(range(1, n + 1))
    lab = {i + 1: p for i, p in enumerate(periods)}
    zh = any(ord(ch) > 0x2E80 for ch in "".join(periods)) or bool(ex.body_lang)
    x0, y0, x1, y1 = box
    split = y0 + (y1 - y0) * 0.70
    series = [{"name": "预算累计" if zh else "Plan YTD", "y": cp, "color": C["context"]}]
    if PY is not None:
        series.append({"name": "去年累计" if zh else "PY YTD", "y": cum(PY), "color": C["dim"]})
    series.append({"name": "实际累计" if zh else "Actual YTD", "y": ca[:k + 1] + [None] * (n - k - 1), "color": C["main"]})
    ymax = max([v for v in cp + ca if v is not None] + [goal])
    ax = lines(ex, (x0, y0, x1, split), X, series, ylim=(0, ymax * 1.08), xticks=X,
               xfmt=lambda v: lab.get(int(v), ""), yfmt=value_fmt, dots=False)
    gap = ca[k] - cp[k]
    rem = n - k - 1
    need = (goal - ca[k]) / rem if rem else 0.0
    if rem:
        ex.line(ax.sx(X[k]), ax.sy(ca[k]), ax.sx(X[-1]), ax.sy(goal), stroke=C["accent"], width=1.8, dash="5,3",
                tag="dim")
        ex.circle(ax.sx(X[-1]), ax.sy(goal), 3.4, "#FFFFFF", stroke=C["accent"], width=1.6)
    if zh:
        txt = f"{periods[k]}累计{'领先' if gap >= 0 else '落后'}预算 {value_fmt(abs(gap))}{unit}" + (
            f"；余下每期需 {value_fmt(need)}{unit}（{periods[k0]}–{periods[k]}均 {value_fmt((ca[k] - (ca[0] if k0 else 0)) / (k + 1 - k0))}）" if rem else "")
    else:
        txt = (f"YTD {'+' if gap >= 0 else '−'}{value_fmt(abs(gap))}{unit} vs plan" +
               (f"; need {value_fmt(need)}{unit}/period (avg so far {value_fmt((ca[k] - (ca[0] if k0 else 0)) / (k + 1 - k0))})" if rem else ""))
    callout(ex, (ax.sx(X[k]), ax.sy(ca[k])), txt, width=170)
    d = [None if ca[i] is None else ca[i] - cp[i] for i in range(n)]
    w = (ax.sx(2) - ax.sx(1)) * 0.5
    ex.text(ax.x, split + 26, "累计差（实际 − 预算）" if zh else "ΔPL YTD (AC − PL)", size=10.5, weight=700, fill=C["ink"])
    _var_panel(ex, ax.x, ax.x + ax.w, split + 34, y1 - 2, [ax.sx(x) for x in X], w, d, "abs", "up",
               lambda v: ("+" if v > 0 else ("−" if v < 0 else "±")) + value_fmt(abs(v)), "",
               bold=[i == k for i in range(n)], size=size)
    return dict(ax=ax, cum_ac=ca, cum_pl=cp, gap=gap, need=need, goal=goal)
