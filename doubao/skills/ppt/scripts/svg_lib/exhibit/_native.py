"""Native (data-bound, editable) Feishu charts for single-chart pages.

A native <chart> keeps its data table: the user edits numbers in Feishu and bars / lines / slices follow. Feishu's
clients lay out native charts slightly differently from each other (web, desktop, PPTX export), so nothing is drawn
on top of a native chart — overlaid arrows / ovals / bands would land in different places on different screens.
Emphasis uses only what the chart itself carries: per-bar colour (focus=, forecast_from=, bar_colors=), data labels,
legend. The argument (CAGR, gap, change) goes in the page title, the chart title or the side points. Pages that need
annotations drawn on the chart, or several charts aligned on one axis, use the exhibit (SVG) charts.

    nc = NativeChart("column", cats, [("装机", vals)], box=(40, f.top, 580, f.bottom - f.top), forecast_from=6,
                     focus=lambda c, s: c == "我方", palette=PAL)
    f.publish(nc.xml(), side=points(...)[0], deck=DECK, page=N, cwd=CWD, who=...)

Kinds: column, bar (horizontal, negatives grow left of zero), line, area, stacked, stacked100, combo (columns + a
line on a hidden right axis, kept above the bars), pie, donut.
"""

from __future__ import annotations

from html import escape

from ._palette import roles


def _rgb(c):
    c = str(c)
    if c.startswith("#") and len(c) == 7:
        return "rgb(%d,%d,%d)" % tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return c


class NativeChart:
    KINDS = ("column", "bar", "line", "area", "stacked", "stacked100", "combo", "pie", "donut")

    def __init__(self, kind, categories, series, box, ymax=None, ymin=0, palette=None, focus=None,
                 forecast_from=None, value_labels=True, value_fmt=None, y2max=None, font="思源黑体", size=12,
                 cat_axis=True, value_axis=True, grid=True, legend=None, track=False, colors=None, bar_colors=None,
                 label_pos=None, gap=0.6, points=True, label_size=None, tick_size=None, legend_size=None):
        """Font sizes are logical points matching adjacent slide text. label_size defaults to size; tick_size and
        legend_size default to size - 1. Service fontSize is two-thirds of logical points; PPTX delivery normalizes
        chart fonts separately.
        kind: see KINDS. categories: list of labels. series: [(name, values)] (combo: first = columns, second =
        line on the right axis). box: (x, y, w, h) on the slide — leave ~40 px above it for annotations.
        ymax/ymin: fixed value axis (computed from the data when omitted, rounded up). focus(cat, series_name) → bool:
        those bars in accent, others main. forecast_from: index of the first forecast category (lighter colour +
        actual|forecast divider). value_fmt: Excel number format for the data labels, e.g. '0.0', '0%'."""
        if kind not in self.KINDS:
            raise ValueError(f"NativeChart kind={kind!r}：只支持 {', '.join(self.KINDS)}；其他图种用 exhibit 画")
        self.kind, self.cats, self.series = kind, [str(c) for c in categories], [(n, list(v)) for n, v in series]
        self.x, self.y, self.w, self.h = box
        self.C = roles(palette)
        self.focus, self.forecast_from, self.value_labels, self.value_fmt = focus, forecast_from, value_labels, value_fmt
        self.font, self.size = font, size
        self.label_size = size if label_size is None else label_size
        self.tick_size = size - 1 if tick_size is None else tick_size
        self.legend_size = size - 1 if legend_size is None else legend_size
        vals = [v for _, vs in self.series[:1 if kind == "combo" else None] for v in vs if v is not None]
        if kind in ("stacked",):
            vals = [sum(vs[i] or 0 for _, vs in self.series) for i in range(len(self.cats))]
        top = max(vals) if vals else 1
        self.ymin = ymin
        head = 1.7 if kind == "combo" else 1.08   # combo: bars fill the lower ~60 %, the line runs above them
        self.ymax = ymax if ymax is not None else (100 if kind == "stacked100" else _nice_up(top * head))
        y2 = [v for v in (self.series[1][1] if kind == "combo" and len(self.series) > 1 else []) if v is not None]
        self.y2max = y2max if y2max is not None else (_nice_up(max(y2) * 1.15) if y2 else None)
        # combo: keep the line in the upper band above the bars (line labels never collide with bar labels)
        self.y2min = 0
        if y2:
            lo, hi = min(y2), max(y2)
            span = max(hi - lo, abs(hi) * 0.1, 1)
            self.y2min = lo - span * 3.2            # line sits in the band above the bars (labels carry the values)
            self.y2min = int(self.y2min) if self.y2min == int(self.y2min) else int(self.y2min) - 1
            self.y2max = y2max if y2max is not None else int(hi + span * 0.5) + 1
        self.cat_axis, self.value_axis, self.grid, self.legend_on = cat_axis, value_axis, grid, legend
        self.track, self.series_colors, self.bar_colors, self.label_pos, self.gap = track, colors, bar_colors, label_pos, gap
        self.points = points   # line / area / combo line: a marker on every data point (like the exhibit lines)
        if kind == "bar" and ymin == 0 and any(v is not None and v < 0 for _, vs in self.series for v in vs):
            lo = min(v for _, vs in self.series for v in vs if v is not None)
            self.ymin = -_nice_up(-lo * 1.08)

    # ------------------------------------------------------------------ colours
    def _colors(self):
        C = self.C
        if self.series_colors:
            return list(self.series_colors) + [C["third"], C["context"]]
        if self.kind in ("pie", "donut"):
            return [C["main"], C["second"], C["light"], C["third"], C["light2"], C["context"]]
        if self.kind in ("stacked", "stacked100"):
            return [C["main"], C["second"], C["light"], C["light2"], C["third"], C["context"]]
        if self.series_colors:
            return list(self.series_colors) + [C["third"], C["context"]]
        if self.kind == "combo":
            return [C["main"], C["accent"]]
        return [C["main"], C["second"], C["accent"], C["third"]]

    def _bar_color(self, i, k=0):
        C = self.C
        if self.bar_colors is not None:   # callable(i, k) -> colour or None (default)
            c = self.bar_colors(i, k)
            if c:
                return c
        if self.forecast_from is not None and i >= self.forecast_from and k == 0:
            return C["light"]
        if self.focus is not None:
            return C["accent"] if self.focus(self.cats[i], self.series[k][0]) else C["main"]
        return self._colors()[k]

    # ------------------------------------------------------------------ XML
    def xml(self):
        """Editable chart XML: service fontSize is two-thirds of logical point size."""
        kind, C = self.kind, self.C
        category_size, label_size, tick_size, legend_size = (
            font_size * 2 / 3 for font_size in (self.size, self.label_size, self.tick_size, self.legend_size)
        )
        ptype = {"stacked": "column", "stacked100": "column", "donut": "pie"}.get(kind, kind)
        extra = ""
        if kind in ("stacked", "stacked100"):
            pct100 = ' percentage="true"' if kind == "stacked100" else ""
            extra = f'<chartExtra><chartStack{pct100}/></chartExtra>'
        else:
            extra = "<chartExtra/>"
        fmt_attr = f' format="{escape(self.value_fmt)}"' if self.value_fmt else ""
        labels = ""
        if self.value_labels:
            pos = self.label_pos or {"column": "outside", "bar": "outside", "line": "top", "area": "top", "stacked": "center",
                                     "stacked100": "center", "combo": "outside", "pie": "outside", "donut": "outside"}[kind]
            lc = "rgb(255,255,255)" if kind in ("stacked", "stacked100") else _rgb(C["ink"])
            pct = ' percentage="true" value="false"' if kind in ("pie", "donut") else ' value="true"'
            labels = (f'<chartLabels position="{pos}"{pct} fontSize="{label_size}" color="{lc}"{fmt_attr}/>'
                      if kind not in ("combo", "line", "area") else "")   # lines: markers only, no per-point values
        series_xml = []
        for k, (name, vs) in enumerate(self.series):
            attrs = ""
            if kind == "combo":
                attrs = ' comboType="column"' if k == 0 else ' comboType="line" yAxisPosition="right"'
            inner = ""
            if kind in ("column", "bar", "combo", "stacked", "stacked100") and (k == 0 or kind in ("stacked", "stacked100")):
                per = "".join(f'<chartBar index="{i + 1}" color="{_rgb(self._bar_color(i, k))}"/>'
                              for i in range(len(self.cats)) if self._bar_color(i, k) != self._colors()[k])
                bg = f' backgroundColor="{_rgb(C["track"])}"' if self.track else ""
                inner = f'<chartBars color="{_rgb(self._colors()[k])}" gapWidth="{round(self.gap * 100)}"{bg}>{per}</chartBars>'
            if kind in ("pie", "donut"):
                hole = ' innerRadius="0.58"' if kind == "donut" else ""
                inner = (f'<chartSectors{hole} borderColor="rgb(255,255,255)">'
                         + "".join(f'<chartSector index="{i + 1}" color="{_rgb(c)}"/>'
                                   for i, c in zip(range(len(self.cats)), self._colors())) + "</chartSectors>")
            if kind == "combo" and self.value_labels and k == 0:   # the bars carry values; the line only markers
                inner += f'<chartLabels position="outside" value="true" fontSize="{label_size}" color="{_rgb(C["ink"])}"/>'
            is_line = kind in ("line", "area") or (kind == "combo" and k == 1)
            if is_line and self.points:   # filled marker in the series colour on every point
                inner += f'<chartPoints color="{_rgb(self._colors()[k])}" shape="circle" size="7"/>'
            series_xml.append(f'<chartSeries index="{k + 1}"{attrs}>{inner}</chartSeries>')
        lines = ("" if kind not in ("line", "area") else
                 '<chartLines width="2"/>' + ("" if self.points else '<chartPoints size="0"/>'))
        plot = (f'<chartPlot type="{ptype}">{extra}{lines}{labels}'
                f'<chartSeriesList>{"".join(series_xml)}</chartSeriesList></chartPlot>')
        axes = ""
        if kind not in ("pie", "donut"):
            hide = '<chartLabel fontSize="1" color="rgba(255,255,255,0)"/>'
            lab = f'<chartLabel fontSize="{category_size}" color="{_rgb(C["ink"])}"/>' if self.cat_axis else hide
            pfmt = ' format="0%"' if kind == "stacked100" else (
                ' format="#,##0"' if self.value_fmt and "#,##" in self.value_fmt else "")
            vlab = f'<chartLabel fontSize="{tick_size}" color="{_rgb(C["axis"])}"{pfmt}/>' if self.value_axis else hide
            grid = f'<chartGridLine color="{_rgb(C["grid"])}"/>' if self.grid else ""
            import math as _m   # the server takes integer axis bounds only (max="0.8" is rejected): round outward
            ints = float(self.ymin).is_integer() and float(self.ymax).is_integer() or abs(self.ymax - self.ymin) >= 4
            vmin = (f' min="{_m.floor(self.ymin)}"' if ints else "") if kind != "stacked100" else ""
            axl = "<chartAxisLine/>" if self.cat_axis or kind != "bar" else ""
            vmax = (f' max="{_m.ceil(self.ymax)}"' if ints else "") if kind != "stacked100" else ""
            if kind == "bar":
                axes = (f'<chartAxes><chartAxis type="y" position="left">{lab}{axl}</chartAxis>'
                        f'<chartAxis type="x"{vmin}{vmax}>{grid}{vlab}</chartAxis></chartAxes>')
            else:
                y2 = ""
                if kind == "combo" and self.y2max is not None:
                    y2 = (f'<chartAxis type="y" position="right" min="{self.y2min}" max="{int(self.y2max)}">'
                          f'<chartLabel fontSize="1" color="rgb(255,255,255)"/></chartAxis>')   # scale only, no ticks
                axes = (f'<chartAxes><chartAxis type="x">{lab}<chartAxisLine/></chartAxis>'
                        f'<chartAxis type="y" position="left"{vmin}{vmax}>{grid}{vlab}</chartAxis>{y2}</chartAxes>')
        show_leg = self.legend_on if self.legend_on is not None else (len(self.series) > 1 or kind in ("pie", "donut"))
        legend = f'<chartLegend position="top" fontSize="{legend_size}"/>' if show_leg else ""
        theme = "".join(f'<color value="{_rgb(c)}"/>' for c in self._colors())
        data = "".join(f'<chartField name="{escape(n)}">{",".join("" if v is None else str(v) for v in vs)}</chartField>'
                       for n, vs in self.series)
        xml = (f'<chart topLeftX="{self.x:.0f}" topLeftY="{self.y:.0f}" width="{self.w:.0f}" height="{self.h:.0f}">'
                f'<chartPlotArea>{plot}{axes}</chartPlotArea>{legend}'
                f'<chartStyle><chartBackground color="rgba(0, 0, 0, 0)"/><chartBorder color="rgba(0, 0, 0, 0)" width="0"/>'
                f'<chartColorTheme>{theme}</chartColorTheme></chartStyle>'
                f'<chartData><dim1><chartField name="类别">{",".join(escape(c) for c in self.cats)}</chartField></dim1>'
                f'<dim2>{data}</dim2></chartData></chart>')
        import hashlib
        identity = hashlib.sha256(xml.encode("utf-8")).hexdigest()[:20]
        return xml.replace("<chart ", f'<chart id="exhibit-native-{identity}" ', 1)

    def _val(self, i, k=0):
        if self.kind == "stacked":
            return sum(vs[i] or 0 for _, vs in self.series)
        return self.series[k][1][i]


def _nice_up(v):
    import math
    if v <= 0:
        return 1
    p = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * p >= v - 1e-12:
            top = m * p
            return int(math.ceil(top)) if top >= 10 else round(top, 6)   # small values keep a fractional axis
    return int(math.ceil(v))
