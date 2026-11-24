"""Plain panels of a multi-chart page become editable Feishu charts.

columns() / lines() record each chart they draw in ex._auto. ex.to_slide() keeps the full SVG result and, beside it,
an alternative where every *plain* chart (no annotation drawn by the call — cagr / diff / target / yoy / delta — and
nothing else drawn over its box: callout, badge, band, bracket, ref line, drill outline…) is replaced by a native
<chart> with the same data, colours and box. Frame.publish() picks the alternative only when the page holds two or more
charts and at least one of them stays SVG (annotated), so a page is never only native charts and annotations never sit
on a native chart (Feishu clients lay native charts out differently; overlays would drift). Small multiples, shared
time axes, IBCS charts, tables and anything not plain column / stacked / line data are never converted.
"""

from __future__ import annotations

import re

from ..atomize_svg_to_slide._font_metrics import text_advance
from ._native import NativeChart

ALT = {}   # to_slide() result -> dict(n=charts, plain=convertible charts, alt=fragment with native charts)


def record(ex, kind, box, start, notes_before, categories, series, colors, focus=None, forecast_from=None,
           stack=None, values=True, ymax=None, grid=True):
    """Remember a chart drawn into ex (elements ex.el[start:]) — called at the end of columns() / lines()."""
    if getattr(ex, "_no_auto", 0):
        return
    ex._auto.append(dict(kind=kind, box=tuple(box), start=start, end=len(ex.el), cats=[str(c) for c in categories],
                         series=series, colors=colors, focus=focus, forecast_from=forecast_from, stack=stack,
                         values=values, ymax=ymax, grid=grid, own_notes=ex.notes > notes_before))


_NUM = r"(-?[\d.]+)"


def _bbox(e):
    """Rough bounding box of one SVG element string (rect / circle / line / text / path)."""
    a = dict(re.findall(r'\s([\w-]+)="([^"]*)"', e.split(">", 1)[0]))
    try:
        if e.startswith("<rect"):
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
            return (x, y, x + float(a.get("width", 0)), y + float(a.get("height", 0)))
        if e.startswith("<circle"):
            cx, cy, r = float(a["cx"]), float(a["cy"]), float(a.get("r", 0))
            return (cx - r, cy - r, cx + r, cy + r)
        if e.startswith("<line"):   # one entry may hold several pieces (a diagonal / polyline drawn as lines)
            v = [(float(a_), float(b_), float(c_), float(d_)) for a_, b_, c_, d_ in re.findall(
                r'x1="(-?[\d.]+)" y1="(-?[\d.]+)" x2="(-?[\d.]+)" y2="(-?[\d.]+)"', e)]
            return (min(min(p[0], p[2]) for p in v), min(min(p[1], p[3]) for p in v),
                    max(max(p[0], p[2]) for p in v), max(max(p[1], p[3]) for p in v))
        if e.startswith("<text"):
            x, y, sz = float(a["x"]), float(a["y"]), float(a.get("font-size", 11))
            n = len(re.sub(r"<[^>]+>", "", e)) * sz * 0.6
            anc = a.get("text-anchor", "start")
            x0 = x - n if anc == "end" else (x - n / 2 if anc == "middle" else x)
            return (x0, y - sz, x0 + n, y + sz * 0.25)
        if e.startswith("<path"):
            v = [float(t) for t in re.findall(_NUM, a.get("d", ""))]
            if len(v) >= 2:
                xs, ys = v[0::2], v[1::2]
                return (min(xs), min(ys), max(xs), max(ys))
    except (KeyError, ValueError):
        return None
    return None


def _hits(b, box, pad=2):
    return b is not None and not (b[2] < box[0] + pad or b[0] > box[2] - pad or b[3] < box[1] + pad or b[1] > box[3] - pad)


def analyse(ex, x0, y0, s):
    """Return (n charts, plain charts, alternative element list, native xml list) for this exhibit."""
    autos = list(getattr(ex, "_auto", []))
    if not autos:
        return 0, 0, None, []
    owned = set()
    for a in autos:
        owned.update(range(a["start"], a["end"]))
    others = [(i, _bbox(e)) for i, e in enumerate(ex.el) if i not in owned]
    natives, drop = [], set()
    for a in autos:
        if a["own_notes"] or any(_hits(b, a["box"]) for _, b in others):
            continue
        bx0, by0, bx1, by1 = a["box"]
        box = (x0 + bx0 * s, y0 + by0 * s, (bx1 - bx0) * s, (by1 - by0) * s)
        if box[2] < 180 or box[3] < 120:   # too small for Feishu's own axes / labels
            continue
        kind = a["kind"]
        if kind == "columns":
            kind = {"percent": "stacked100"}.get(a["stack"], "stacked" if a["stack"] else "column")
        vals = [v for _, vs in a["series"] for v in vs if v is not None]
        if not vals:
            continue
        dec = any(abs(v - round(v)) > 1e-9 for v in vals)
        vfmt = ("#,##0.0" if max(abs(v) for v in vals) >= 1000 else "0.0") if dec else \
            ("#,##0" if max(abs(v) for v in vals) >= 1000 else "0")
        n_marks = len(a["cats"]) * (1 if kind in ("stacked", "stacked100") else len(a["series"]))
        per = box[2] / max(n_marks, 1)   # Feishu does not de-collide value labels: keep them only where they fit
        size = 10.5 * s
        label_size = (10 if kind in ("stacked", "stacked100") or len(a["series"]) > 1 else 10.5) * s
        label_spec = f'{"," if "#,##" in vfmt else ""}.{1 if dec else 0}f'
        widest = max(text_advance(format(value, label_spec), ex.font, label_size) for value in vals)
        show = a["values"] and kind != "line" and per >= widest + 4 * s
        try:
            nc = NativeChart(kind, a["cats"], a["series"], box=box, palette=None, colors=a["colors"],
                             forecast_from=a["forecast_from"], focus=a["focus"], value_labels=show,
                             legend=len(a["series"]) > 1, font=ex.font, size=size, value_fmt=vfmt,
                             label_size=label_size, tick_size=size, legend_size=size, grid=a["grid"])
            nc.C = ex.C
            natives.append(nc.xml())
        except Exception:  # noqa: BLE001  anything the native chart cannot express stays SVG
            continue
        drop.update(range(a["start"], a["end"]))
    if not natives:
        return len(autos), 0, None, []
    return len(autos), len(natives), [e for i, e in enumerate(ex.el) if i not in drop], natives


def swap(frags):
    """Frame.publish: frags with the plain charts made native, when the page has ≥2 charts and ≥1 stays SVG."""
    import os
    if os.environ.get("EXHIBIT_NATIVE", "").strip().lower() not in ("1", "true", "on", "yes"):
        return list(frags), 0   # exhibit charts stay SVG by default (native conversion is parked: feat/ppt-native-charts)
    info = [ALT.get(f) for f in frags]
    n = sum(i["n"] for i in info if i) + sum(1 for f, i in zip(frags, info) if not i and _is_chart_frag(f))
    plain = sum(i["plain"] for i in info if i)
    if n < 2 or not plain or plain >= n:
        return list(frags), 0
    return [i["alt"] if i else f for f, i in zip(frags, info)], plain


def _is_chart_frag(f):   # a chart fragment drawn without columns()/lines() (row_table, bubbles, ibcs…): stays SVG
    return str(f).count("<shape") >= 6
