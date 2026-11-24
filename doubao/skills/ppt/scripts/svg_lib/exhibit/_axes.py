"""Axes: categorical (bars) and numeric (scatter / lines), with reserved space for ticks, titles and a missing band."""

from __future__ import annotations

import math

from ._place import place_label
from ._text import fmt


def nice_ticks(vmax, n=4, vmin=0):
    span = (vmax - vmin) or abs(vmax) or 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=mag * 10)
    lo = math.floor(vmin / step + 1e-9) * step
    top = math.ceil(vmax / step - 1e-9) * step
    out, v = [], lo
    while v <= top + 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def tick_fmt(ticks):
    """Default tick formatter: as many decimals as the tick step needs (step 0.25 → 1.25, not 1.2), same on every tick."""
    vals = [float(t) for t in ticks]
    nd = 0
    while nd < 4 and any(abs(round(v, nd) - v) > 1e-9 for v in vals):
        nd += 1
    return (lambda v: f"{v:,.{nd}f}") if nd else fmt


def bar_ticks(vmax, n=4, vmin=0):
    """nice_ticks for bars: a small negative (|min| < 15% of the positive max) gets a finer step below zero
    (step/5 or step/4 of the positive tick step, e.g. -80 -> -100) instead of a full positive step, so the bars,
    the zero line and the category labels stay together."""
    if not (vmin < 0 < vmax and -vmin < 0.15 * vmax):
        return nice_ticks(vmax, n, vmin)
    pos = nice_ticks(vmax, n, 0)
    step = pos[1] - pos[0]
    lo = None
    for k in (5, 4, 2):
        sub = step / k
        cand = math.floor(vmin / sub + 1e-9) * sub
        if lo is None or cand > lo:
            lo = cand
    return [round(lo, 10)] + pos


def y_title(t):
    """A y-axis title is printed horizontally above the axis: its direction arrows point up/down, not right/left."""
    if not isinstance(t, str):
        return t
    return t.replace("→", "↑").replace("←", "↓").replace("->", "↑")


PLOTS: list = []   # plot-area heights (slide px) of the axes built for the current page: precheck flags squeezed ones


class Axes:
    """y-scale for bar/column charts. ax.sy(v), ax.bands(n) -> [(x, w)], ax.grid(), ax.xlabels(centers, labels)."""

    def __init__(self, ex, x, y, w, h, ymax, ymin=0, ticks=None, n_ticks=4):
        self.s, self.x, self.y, self.w, self.h = ex, x, y, w, h
        PLOTS.append(h * getattr(ex, "scale", 1))
        self.ticks = ticks or bar_ticks(ymax, n_ticks, ymin)
        if list(self.ticks) != sorted(self.ticks) or self.ticks[0] == self.ticks[-1]:
            raise ValueError(f"Axes: ticks 必须从小到大且不全相同（收到 {list(self.ticks)}）")
        self.ymin, self.ymax = self.ticks[0], self.ticks[-1]
        self.xmin = self.xmax = None
        self.below = y + h + 22
        self.band_h = 0

    @classmethod
    def fit(cls, ex, box, ymax, ymin=0, ticks=None, label_rows=1, left=34, top_pad=22):
        """Fit a column chart into box leaving room for y ticks (left), value labels (top) and x labels (bottom)."""
        from ._page import chart_box as _cbx
        x0, y0, x1, y1 = _cbx(ex, box)   # inside ex.panel(claim=…): never over the panel's claim / unit lines
        bottom = 10 + 14 * label_rows + 4
        return cls(ex, x0 + left, y0 + top_pad, x1 - x0 - left, y1 - y0 - top_pad - bottom, ymax, ymin, ticks)

    def sy(self, v):
        return self.y + self.h - (v - self.ymin) / (self.ymax - self.ymin) * self.h

    def sx(self, v):
        return self.x + (v - self.xmin) / (self.xmax - self.xmin) * self.w

    def grid(self, labels=True, size=10.5, fmt_tick=None, lines=True):
        """Draw ticks and the baseline; lines=False omits only horizontal grid lines."""
        C = self.s.C
        fmt_tick = fmt_tick or tick_fmt(self.ticks)
        for t in self.ticks:
            yy = self.sy(t)
            if lines and t != self.ymin:
                self.s.line(self.x, yy, self.x + self.w, yy, stroke=C["grid"], width=0.8, tag="grid")
            if labels:
                self.s.text(self.x - 6, yy + size * 0.35, fmt_tick(t), size=size, fill=C["axis"], anchor="end")
        base = self.sy(0) if self.ymin < 0 < self.ymax else self.sy(self.ymin)
        self.s.line(self.x, base, self.x + self.w, base, stroke=C["axis"], width=0.9, tag="axis")

    def ref_y(self, v, label=None):
        """Horizontal target / average line (bar and numeric axes); label placed automatically."""
        from ._page import add_fact
        add_fact(self.s, {"kind": "ref", "value": float(v), "label": str(label or "")})
        yy = self.sy(v)
        if label:  # tag sits on the line (left end, then right end), never pulled away on a leader
            from ._text import tw
            w = tw(label, 10) + 6
            for lx, ly, anc in ((self.x + 4, yy - 4, "start"), (self.x + self.w - 2, yy - 4, "end"),
                                (self.x + 4, yy + 13, "start"), (self.x + self.w - 2, yy + 13, "end")):
                bx = (lx, ly - 9, lx + w, ly + 2) if anc == "start" else (lx - w, ly - 9, lx, ly + 2)
                if self.s.cost(bx) < 1:
                    break
            self.s.text(lx, ly, label, size=10, fill=self.s.C["sub"], anchor=anc)
        self.s.line(self.x, yy, self.x + self.w, yy, stroke=self.s.C["context"], width=0.8, dash="3,3", tag="ref")

    def bands(self, n, pad=0.3):
        step = self.w / n
        self.cat_bands = [(self.x + i * step + step * pad / 2, step * (1 - pad)) for i in range(n)]
        return [(self.x + i * step + step * pad / 2, step * (1 - pad)) for i in range(n)]

    def xlabels(self, centers, labels, size=10.5, width=None, gap=15, fill=None, vertical=None):
        """Category labels under the axis. "\n" breaks a label; non-year labels wider than the band wrap to the band
        width (2 lines) automatically; long Chinese labels in very narrow bands are stacked vertically (vertical=True
        forces it — leave room with Axes.fit(label_rows=len(longest label))). Crowded year labels become '16 / '17…; still crowded → every k-th label."""
        from ._text import tw, wrap
        labels = [f"{l:.0f}" if isinstance(l, (int, float)) and float(l).is_integer() and 1900 <= l <= 2100 else str(l)
                  for l in labels]
        step = (centers[1] - centers[0]) if len(centers) > 1 else 1e9
        years = all(l.isdigit() and len(l) == 4 for l in labels)
        from ._text import has_cjk
        too_long = any("\n" not in l and tw(l, size) + 6 > step for l in labels)
        if vertical is None:  # long Chinese labels in narrow bands read better stacked vertically than wrapped/abbrev.
            vertical = too_long and not years and all(has_cjk(l) for l in labels) and step < size * 4.2
        if vertical:
            for cx, lab in zip(centers, labels):
                chars = [ch for ch in lab if ch.strip()]
                self.s.lines(cx, self.sy(self.ymin) + gap, chars, size=size, anchor="middle",
                             fill=fill or self.s.C["text"], lh=1.12)
            return
        if not width and not years and too_long:
            width = max(step - 6, size * 3)
        if not width and max(tw(l, size) for l in labels) + 6 > step:
            if all(l.isdigit() and len(l) == 4 for l in labels):
                labels = ["’" + l[2:] for l in labels]
            if max(tw(l, size) for l in labels) + 6 > step:
                k = int(max(tw(l, size) for l in labels) // step) + 1
                labels = [l if (i % k == 0 or i == len(labels) - 1) else "" for i, l in enumerate(labels)]
        for cx, lab in zip(centers, labels):
            if not lab:
                continue
            rows = [r for part in lab.split("\n") for r in (wrap(part, size, width) if width else [part])]
            self.s.lines(cx, self.sy(self.ymin) + gap, rows, size=size, anchor="middle", fill=fill or self.s.C["text"],
                         lh=1.2)


class NAxes(Axes):
    """Numeric x / y. Use NAxes.fit(ex, box, xlim, ylim, ...) — it reserves room for ticks, titles and band rows."""

    def __init__(self, ex, x, y, w, h, xlim, ylim, xticks=None, yticks=None, n=5):
        yt = yticks or nice_ticks(ylim[1], n, ylim[0])
        super().__init__(ex, x, y, w, h, yt[-1], ymin=yt[0], ticks=yt)
        self.xticks = xticks or nice_ticks(xlim[1], n, xlim[0])
        self.xmin, self.xmax = self.xticks[0], self.xticks[-1]

    @classmethod
    def fit(cls, ex, box, xlim, ylim, xticks=None, yticks=None, xtitle=True, ytitle=True, band_rows=0, left=36,
            key_w=0):
        """key_w: px kept free right of the plot for a colour key (bubbles(..., key=…) lists the names there)."""
        from ._page import chart_box as _cbx
        x0, y0, x1, y1 = _cbx(ex, box)
        top = y0 + (20 if ytitle else 6)
        bottom = 22 + (20 if xtitle else 0) + (0 if not band_rows else 6 + 18 * band_rows + 8)
        ax = cls(ex, x0 + left, top, x1 - x0 - left - 12 - key_w, y1 - top - bottom, xlim, ylim, xticks, yticks)
        ax.key_w = key_w
        ax.band_h = 0 if not band_rows else 18 * band_rows + 8
        return ax

    def frame(self, xfmt=None, yfmt=None, xtitle=None, ytitle=None, size=10.5, vgrid=False,
              zero_line=True):
        s, C = self.s, self.s.C
        self._xtitle, self._ytitle = str(xtitle or ""), str(ytitle or "")
        xfmt, yfmt = xfmt or tick_fmt(self.xticks), yfmt or tick_fmt(self.ticks)
        if self.xticks and all(1900 <= t <= 2100 for t in self.xticks):  # year axis (incl. 2026.7 = mid-year): no thousands sep
            xfmt = (lambda f: (lambda v: (f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}")
                               if f(v).replace(",", "").replace(".", "").isdigit() else f(v)))(xfmt)
        for t in self.ticks:
            yy = self.sy(t)
            if t != self.ymin:
                s.line(self.x, yy, self.x + self.w, yy, stroke=C["grid"], width=0.8, tag="grid")
            s.text(self.x - 6, yy + size * 0.35, yfmt(t), size=size, fill=C["axis"], anchor="end")
        for t in self.xticks:
            xx = self.sx(t)
            if vgrid and t != self.xmin:
                s.line(xx, self.y, xx, self.y + self.h, stroke=C["grid"], width=0.8, tag="grid")
            s.line(xx, self.y + self.h, xx, self.y + self.h + 4, stroke=C["axis"], width=0.8, tag="grid")
            lab = xfmt(t)
            if lab:
                s.text(xx, self.y + self.h + 16, lab, size=size, fill=C["axis"], anchor="middle")
        s.line(self.x, self.y + self.h, self.x + self.w, self.y + self.h, stroke=C["axis"], width=0.9, tag="axis")
        if zero_line and self.xmin < 0 < self.xmax:
            s.line(self.sx(0), self.y, self.sx(0), self.y + self.h, stroke=C["context"], width=0.8, dash="3,3", tag="zero")
        s.occupy((self.x - 30, self.y + self.h + 0.5, self.x + self.w + 14, self.y + self.h + 46), "text", "axis-band")
        self.below = self.y + self.h + 22
        if xtitle:
            s.text(self.x + self.w / 2, self.y + self.h + 36, xtitle, size=size + 0.5, weight=700, fill=C["ink"],
                   anchor="middle")
            self.below = self.y + self.h + 42
        if ytitle:
            ytitle = y_title(ytitle)
            s.text(self.x - 6, self.y - 10, ytitle, size=size, fill=C["axis"], anchor="start")

    def label_bounds(self):
        return (self.x + 2, self.y - 18, self.x + self.w + 60, self.y + self.h - 2)

    def ref_x(self, v, label=None, side="top"):
        """Vertical threshold / average line; its label is placed automatically."""
        from ._page import add_fact
        add_fact(self.s, {"kind": "ref", "value": float(v), "label": str(label or "")})
        xx = self.sx(v)
        self.s.line(xx, self.y, xx, self.y + self.h, stroke=self.s.C["context"], width=0.8, dash="3,3", tag="ref")
        if label:
            yy = self.y + 2 if side == "top" else self.y + self.h - 2
            place_label(self.s, xx, yy, label, size=10, r=0, gap=4,
                        prefer=("SE", "SW", "E", "W") if side == "top" else ("NE", "NW"), fills=[self.s.C["sub"]],
                        priority=3)
