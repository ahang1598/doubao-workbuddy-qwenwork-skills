"""row_table: shared-row chart table — the default block for comparing many objects on several measures.

Columns:
  Label     text label; level=0 group header (once per group), level=1 row label
  Text      computed text / number per row
  Bar       horizontal bar with grey track; value inside / after / before; cumulative=True steps bars along (exa12)
  Dumbbell  2+ points per row on one scale (current→future, group A vs B, gross→net); connector bar|line|arrow
  Range     interval per row (lo, hi, optional point): gantt, CI / forest, min–max
  Heat      one coloured cell per row (heat-map column) with the value printed inside
  Diverge   back-to-back bars around a centre (population pyramid, gain vs loss)
  Box       box-and-whisker per row from (min, q1, median, q3, max) fields — distributions across groups
  Note      multi-line so-what text per row (optional bold lead); rows grow to fit the tallest note
  Rank      rank change prev → now as ▲3 / ▼1 / — (up = rank number fell)
  Scen      IBCS bar: AC solid + reference (PL hollow outline / PY grey) offset behind it, value at the end
  Variance  IBCS variance: ac − ref as good/bad bar (pct=False) or (ac/ref − 1) as pin (pct=True) from a zero axis
Table extras: total=row dict (dark band), brackets=[(i0, i1, text, col_idx)], focus=callable(row) (others dimmed),
per-column focus=, zebra=True|'track', legend_items=[(label, color, kind)].
"""
from __future__ import annotations

import math
import re

from ._axes import nice_ticks
from ._marks import legend, vbracket
from ._text import fmt, has_cjk, tw, wrap


def _dfmt(v):
    """Default cell formatter (replaced per column by _shared_fmt: one decimal count for the whole column)."""
    return fmt(v)


def _decimals(v):
    """Decimals one value needs (0 for integers and |v| ≥ 100, at most 2)."""
    v = float(v)
    if v.is_integer() or abs(v) >= 100:
        return 0
    return 1 if abs(round(v, 1) - v) < 1e-9 else 2


def _shared_fmt(values):
    """One formatter for a column: every cell with the same decimals (4.95 next to 53.6 → 4.95 / 53.60, never a
    rounded '5'); an all-integer column prints 358 / 1,182 / 80, never '358.0'."""
    vs = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not vs:
        return _dfmt
    nd = max(_decimals(v) for v in vs)
    if max(abs(v) for v in vs) >= 1000:
        nd = min(nd, 1)
    if nd == 0 or any(0 < abs(v) < 0.01 for v in vs):   # integers / ≥100: fmt() already prints no ".0"
        return _dfmt

    def f_(v):
        if not isinstance(v, (int, float)):
            return fmt(v)
        t = f"{float(v):,.{nd}f}"
        return "0" if t.lstrip("-").strip("0.,") == "" else t
    return f_


class Col:
    width = None
    header = ""
    header_align = "start"
    header_bold = False
    sep = False
    focus = None
    ticks = None
    ticks_pos = "top"

    def __init__(self, **kw):
        self.__dict__.update(kw)


class Label(Col):
    """Text label. field: key or callable. level=0 group header; valign='middle' centres it across its group."""

    def __init__(self, field="label", width=None, header="", level=1, size=11, weight=400, align="start", wrap_w=None,
                 color=None, valign="top"):
        super().__init__(field=field, width=width, header=header, level=level, size=size, weight=weight, align=align,
                         wrap_w=wrap_w, color=color, header_align=align, valign=valign)


class Text(Col):
    """Computed text: fmt(row) -> str. color: str | callable(row)."""

    def __init__(self, fmt, width=56, header="", size=11, weight=400, align="end", color=None):
        self._key = fmt if isinstance(fmt, str) and "{" not in fmt else None
        if isinstance(fmt, str):   # Text("note") / Text("{x}%"): a field name or a format string over the row
            key = fmt
            fmt = (lambda r: key.format(**r)) if "{" in key else (lambda r: "" if r.get(key) is None else str(r.get(key)))
        super().__init__(fmt=fmt, width=width, header=header, size=size, weight=weight, align=align, color=color,
                         header_align=align)


class Bar(Col):
    """Horizontal bar. color: str | callable(row). value_pos: auto | inside_end | end | before | none.
    Every row (focus or not) prints its value; values=False (or value_pos="none") turns all of them off."""

    def __init__(self, field, width=None, header="", domain=None, color=None, value_pos="auto", fmt=_dfmt,
                 track=True, bar_h=0.62, ticks=None, tick_fmt=lambda v: fmt(v), size=10.5, cumulative=False, focus=None,
                 values=True, vmax=None, vmin=None):
        if domain is None and vmax is not None:
            domain = (vmin or 0, vmax)
        if values is False:
            value_pos = "none"
        super().__init__(field=field, width=width, header=header, domain=domain, color=color, value_pos=value_pos,
                         fmt=fmt, track=track, bar_h=bar_h, ticks=ticks, tick_fmt=tick_fmt, size=size,
                         cumulative=cumulative, focus=focus)


class Dumbbell(Col):
    """Points on one scale. series=[(field, name, color, style)], style dot|ring|pale.
    connector bar|line|arrow (arrow: base period → current, i.e. first→last, or last→first when the names say the
    first series is the current one, e.g. ("今年", "去年")). base=True shades axis start→first value. labels='values'.
    delta=True writes actual − reference ("+15", via value_fmt; last − first series unless the names say the first is
    the actual and the last the reference, e.g. ("now", "2025H1") then ("ly", "2024H1")) on the connector, or right of the dumbbell when the
    gap is too short; delta=callable(d) -> str formats it yourself (e.g. lambda d: f"{d:+.1f}pt").
    unit: the values' unit (or a METRICS dict); a rate unit (%, pt, pp) writes delta=True in pt ("+6.3pt").
    A domain= that leaves values outside is widened to cover them (ticks recomputed)."""

    def __init__(self, series, width=None, header="", domain=None, ticks=None, tick_fmt=lambda v: fmt(v),
                 connector="bar", labels="none", r=6, ticks_pos="top", value_fmt=lambda v: fmt(v), zero_line=False,
                 focus=None, base=False, delta=False, unit=None):
        super().__init__(series=series, width=width, header=header, domain=domain, ticks=ticks, tick_fmt=tick_fmt,
                         connector=connector, labels=labels, r=r, ticks_pos=ticks_pos, value_fmt=value_fmt,
                         zero_line=zero_line, focus=focus, base=base, delta=delta, unit=unit)

    def delta_of(self, first, last):
        """Signed gap shown by delta=True: actual − reference. last − first, unless the series names / fields say the
        first series is the actual ("now"/"AC"/"实际"/the later period) and the last the reference (去年/PY/预算)."""
        from ._kpi import ac_minus_ref_order
        s0, s1 = self.series[0], self.series[-1]
        o = ac_minus_ref_order((str(s0[1]), str(s0[0]) if not callable(s0[0]) else ""),
                               (str(s1[1]), str(s1[0]) if not callable(s1[0]) else ""))
        return first - last if o < 0 else last - first

    def delta_text(self, d, zh=True):
        if callable(self.delta):
            return self.delta(d)
        from ._kpi import is_rate_unit, pt_text
        if is_rate_unit(self.unit):
            if self.labels == "values" and d != 0 and round(abs(d), 1) == 0:
                for digits in range(2, 7):
                    if round(abs(d), digits):
                        body = f"{abs(d):.{digits}f}".rstrip("0").rstrip(".")
                        return ("+" if d > 0 else "−") + body + "pt"
            return pt_text(d, zh=zh)
        return ("+" if d > 0 else ("−" if d < 0 else "±")) + self.value_fmt(abs(d))


class Range(Col):
    """Interval per row: lo/hi fields (+ optional point field). Gantt (time), CI/forest (estimate), min–max.
    ref=value draws a reference line (e.g. 1 for HR, 0 for effects). color: str | callable(row).
    A value range (football field, scenarios, valuation band) is unreadable without numbers: by default it gets a
    numeric axis (ticks) and each bar its endpoint values (labels="auto" → "values" unless the ranges are years, i.e.
    a Gantt); ticks=False / labels="none" turn them off."""

    def __init__(self, lo, hi, point=None, width=None, header="", domain=None, ticks=None, tick_fmt=lambda v: fmt(v),
                 ticks_pos="top", color=None, ref=None, labels="auto", value_fmt=lambda v: fmt(v), bar_h=0.42,
                 focus=None):
        super().__init__(lo=lo, hi=hi, point=point, width=width, header=header, domain=domain, ticks=ticks,
                         tick_fmt=tick_fmt, ticks_pos=ticks_pos, color=color, ref=ref, labels=labels,
                         value_fmt=value_fmt, bar_h=bar_h, focus=focus)


class Heat(Col):
    """One coloured cell per row; colour interpolates light→main over domain (or diverging if `mid` given: above mid
    → main, below → `below` role — "context" grey by default, "neg" for attainment / vs-target matrices)."""

    def __init__(self, field, width=52, header="", domain=None, mid=None, fmt=_dfmt, size=10.5,
                 header_align="middle", below="context"):
        super().__init__(field=field, width=width, header=header, domain=domain, mid=mid, fmt=fmt, size=size,
                         header_align=header_align, below=below)


class Status(Col):
    """Traffic-light dot + short word per row from a status field ("green" / "amber" / "red", e.g. metric_rows()):
    met = main, close = pale tint of the "bad" colour, missed = bad (neg). words overrides the labels."""

    def __init__(self, field="status", width=64, header="状态", words=None, size=10.5):
        super().__init__(field=field, width=width, header=header, words=words, size=size)


class Spark(Col):
    """Sparkline per row from a list field (oldest → latest): thin line, last point dotted and labelled. kind="bar"
    draws mini columns instead (last one in accent). Scale is per row (shape, not level) unless shared=True.
    A KPI table with a Spark column reads trend + level + gap in one line (sparkline table)."""

    def __init__(self, field, width=110, header="趋势", kind="line", shared=False, label=True, fmt=_dfmt,
                 size=10.5, color=None, focus=None):
        super().__init__(field=field, width=width, header=header, kind=kind, shared=shared, label=label, fmt=fmt,
                         size=size, color=color, focus=focus, header_align="start")


class Harvey(Col):
    """Harvey ball per row (0–4 quarters filled) — qualitative scores read at a glance instead of digits.
    field: numeric score; scale=(lo, hi) maps to 0…4 quarters (e.g. 1–5 scores → (1, 5)). Optional label next to it."""

    def __init__(self, field, width=52, header="", scale=(0, 4), r=9, label=None, header_align="middle"):
        super().__init__(field=field, width=width, header=header, scale=scale, r=r, label=label,
                         header_align=header_align)


_LEVEL_WORDS = {"低": 1, "较低": 1.5, "中低": 1.5, "中": 2, "中等": 2, "中高": 3, "较高": 3, "高": 4, "极高": 4,
                "low": 1, "medium-low": 1.5, "medium": 2, "med": 2, "medium-high": 3, "high": 4, "very high": 4}


class Level(Harvey):
    """Qualitative level per row (可能性 / 影响 / 把握度): a Harvey ball read from a word — 低 / 中低 / 中 / 中高 / 高
    (Low / Medium / High) — or a 1–4 grade. No 1–5 scores or decimals on the page: a judgement shown as a level, not
    as a measured number. label=True prints the word next to the ball."""

    def __init__(self, field, width=56, header="", label=False, r=8):
        def grade(row, _f=field):
            v = row.get(_f) if isinstance(row, dict) else None
            if isinstance(v, str):
                key = v.strip().lower()
                if key not in _LEVEL_WORDS:
                    raise ValueError(f"Level('{_f}')：{v!r} 不是档位——写 低 / 中低 / 中 / 中高 / 高（或 Low / Medium / High）")
                return _LEVEL_WORDS[key]
            return v
        super().__init__(field=grade, width=width, header=header, scale=(0, 4), r=r,
                         label=(lambda row, _f=field: str(row.get(_f, ""))) if label else None)


class Diverge(Col):
    """Back-to-back bars: left field grows leftwards, right field rightwards from a shared centre."""

    def __init__(self, left, right, width=None, header="", domain=None, left_color=None, right_color=None,
                 fmt=lambda v: fmt(v), left_name="", right_name="", bar_h=0.62, focus=None):
        super().__init__(left=left, right=right, width=width, header=header, domain=domain, left_color=left_color,
                         right_color=right_color, fmt=fmt, left_name=left_name, right_name=right_name, bar_h=bar_h,
                         focus=focus, header_align="middle")


class Box(Col):
    """Box plot per row. fields: (min, q1, median, q3, max) keys; optional mean. color: str | callable(row)."""

    def __init__(self, fields, width=None, header="", domain=None, ticks=None, tick_fmt=lambda v: fmt(v),
                 ticks_pos="top", color=None, labels="median", value_fmt=lambda v: fmt(v), focus=None):
        super().__init__(fields=fields, width=width, header=header, domain=domain, ticks=ticks, tick_fmt=tick_fmt,
                         ticks_pos=ticks_pos, color=color, labels=labels, value_fmt=value_fmt, focus=focus)


class Note(Col):
    """Multi-line so-what text per row (implication / action), wrapped within width. field: key or callable(row)
    returning a str or a (lead, text) tuple — lead is drawn bold (lead=True) and the text runs on after it.
    The table's row height grows to fit the tallest note (raises if the box is too short: widen the Note,
    shorten the text or raise Exhibit(h=)). Integrated text, not an annotation."""

    def __init__(self, field, width=220, header="含义", size=12, lead=True, color=None):
        super().__init__(field=field, width=width, header=header, size=size, lead=lead, color=color)

    def parts(self, row):
        v = _val(row, self.field)
        if v in (None, ""):
            return "", ""
        if isinstance(v, (tuple, list)):
            ld, tx = (str(v[0] or ""), str(v[1] or "")) if len(v) > 1 else (str(v[0] or ""), "")
            return ld, tx
        return "", str(v)

    def layout(self, row):
        """[(line, n_lead_chars)] after wrapping lead + text inside the column width."""
        ld, tx = self.parts(row)
        full = (ld + " " + tx).strip() if ld and tx else (ld or tx)
        if not full:
            return []
        out, ptr = [], 0
        nl = len(ld) if self.lead else 0
        # one character of slack: CJK punctuation may hang past the wrap width (it never starts a line)
        for ln in wrap(full, self.size, self.width - self.size, bold=bool(ld and self.lead)):
            st = full.find(ln, ptr)
            st = ptr if st < 0 else st
            ptr = st + len(ln)
            out.append((ln, max(0, min(len(ln), nl - st))))
        return out

    def height(self, row):
        n = len(self.layout(row))
        return 0 if not n else self.size * 1.3 * (n - 1) + self.size * 1.02 + getattr(self, "_pad", 10)


class Rank(Col):
    """Rank change per row from prev_key → now_key (rank numbers, 1 = top): ▲3 (moved up, positive colour),
    ▼1 (down, neg colour), — (unchanged); a missing previous rank prints 新 / new.
    kind="value": prev_key / now_key are values (sales last year → this year): arrow and colour follow
    sign(now − prev), ▲ when the value grew; fmt formats |Δ|. kind="auto" (default) treats the fields as values when
    any of them is not a small positive integer (a rank ≤ max(3 × rows, 30)) — passing deliveries as "ranks" would
    print ▼ for a value that grew."""

    def __init__(self, prev_key, now_key, width=60, header="排名变化", size=11, align="middle", kind="auto",
                 fmt=lambda v: fmt(v)):
        if kind not in ("auto", "rank", "value"):
            raise ValueError(f"Rank: kind={kind!r} 只能是 'auto' / 'rank'（名次，1=第一）/ 'value'（数值，按 now − prev 定方向）")
        super().__init__(prev_key=prev_key, now_key=now_key, width=width, header=header, size=size, align=align,
                         header_align=align, kind=kind, fmt=fmt)

    def resolve(self, rows):
        """'rank' or 'value' for these rows."""
        if self.kind != "auto":
            return self.kind
        cap = max(3 * len(rows), 30)
        for r in rows:
            for k in (self.prev_key, self.now_key):
                v = _val(r, k)
                if v is None:
                    continue
                try:
                    f_ = float(v)
                except (TypeError, ValueError):
                    continue
                if f_ != int(f_) or not 1 <= f_ <= cap:
                    return "value"
        return "rank"

    def cell(self, p_, n_, C, zh=True):
        """(text, colour) of one row: direction and colour always from the sign of the change."""
        if p_ is None:
            return ("新" if zh else "new"), C["sub"]
        if getattr(self, "_mode", "rank") == "value":
            d = float(n_) - float(p_)
            body = str(self.fmt(abs(d))).lstrip("+−-± ")
        else:
            d = int(round(p_ - n_))
            body = str(abs(d))
        if d > 0:
            return f"▲{body}", C.get("pos", C["accent"])
        if d < 0:
            return f"▼{body}", C["neg"]
        return "—", C["sub"]


class Scen(Col):
    """IBCS structure bar: AC solid (main) with its reference drawn behind, offset — ref_kind="PL" hollow outline
    (below), "PY" grey bar (above); scen="FC" draws the row's main bar hatched. Value label after the longer bar.
    ac / ref: key or callable(row). color: str | callable(row) for the AC bar."""

    def __init__(self, ac, ref=None, ref_kind="PL", width=None, header="", domain=None, scen="AC", color=None,
                 fmt=lambda v: fmt(v), size=10.5, bar_h=0.46, focus=None):
        if str(ref_kind).upper() not in ("PL", "BU", "PY", "FC"):
            raise ValueError(f"Scen: ref_kind={ref_kind!r} 只能是 'PL'（预算，空心框）或 'PY'（去年，灰条）")
        super().__init__(ac=ac, ref=ref, ref_kind=str(ref_kind).upper(), width=width, header=header, domain=domain,
                         scen=scen, color=color, fmt=fmt, size=size, bar_h=bar_h, focus=focus)


class Variance(Col):
    """IBCS variance column, one shared scale across rows with a zero axis: pct=False → absolute ac − ref as a
    good/bad bar labelled "+12"; pct=True → relative ac / ref − 1 as a pin (line + round head) labelled "+8%".
    favorable="down" for cost-type measures (an overrun is bad); callable(row) -> "up"/"down" for mixed tables (P&L:
    cost rows "down"). A row carrying "higher_better" (metric_rows() rows do) colours by it: higher_better=False → an
    increase is bad; a favorable that contradicts a row's explicit higher_better raises. Rows whose "unit" is a rate
    (%, pt, pp) show the change in pt (actual − ref), never as a relative % of a percentage.
    Header defaults to ΔPL / ΔPL% (ref_name="PY" → ΔPY); on a Chinese table 对目标 / 对目标% (对去年 for PY).
    fmt formats the signed value (default +x / −x; pct: +8% / −3.5%). width=None shares the free table width with
    the other flexible columns (pass e.g. width=100 to fix it). Counts as an on-chart annotation."""

    def __init__(self, ac, ref, pct=False, favorable=None, width=None, header=None, ref_name=None, domain=None,
                 fmt=None, size=10.5, focus=None):
        if not callable(favorable) and favorable not in ("up", "down", None):
            raise ValueError(f"Variance: favorable={favorable!r} 只能是 'up'（越高越好）、'down'（越低越好，成本/费用）"
                             "或 callable(row) -> 'up'/'down'（损益表里费用行取 'down'）")
        rn = ref_name or (str(ref).upper() if isinstance(ref, str) and str(ref).upper() in ("PL", "PY", "BU", "FC")
                          else "PL")
        auto = header is None
        if header is None:
            header = f"Δ{rn}%" if pct else f"Δ{rn}"
        super().__init__(ac=ac, ref=ref, pct=pct, favorable=favorable, width=width, header=header, domain=domain,
                         fmt=fmt, size=size, focus=focus, header_align="middle", _auto_header=auto, _rn=rn)

    def zh_header(self):
        """Default header on a Chinese table: 对目标 / 对去年 (+ %), never raw ΔPL / ΔPY."""
        word = _ZH_REF.get(self._rn, "对目标")
        return word + ("%" if self.pct else "")

    @staticmethod
    def _rate(row):
        from ._kpi import RATE_UNITS
        return isinstance(row, dict) and str(row.get("unit", "")).strip() in RATE_UNITS

    def value(self, row):
        a, r = _val(row, self.ac), _val(row, self.ref)
        if a is None or r is None:
            return None
        if self.pct:
            if self._rate(row):   # a rate's change is in pt: drawn on the % scale as (a − r) / 100, labelled "pt"
                return (a - r) / 100
            return (a / r - 1) if r else None
        return a - r

    def label(self, row, v=None):
        """Text of row's variance (pt for rate rows)."""
        v = self.value(row) if v is None else v
        if v is None:
            return ""
        if self._rate(row) and not self.fmt:
            d = v * 100 if self.pct else v
            s_ = f"{abs(d):.1f}".rstrip("0").rstrip(".") if abs(d) < 10 else f"{abs(d):.0f}"
            return ("+" if d > 0 else ("−" if d < 0 else "±")) + (s_ or "0") + "pt"
        return self.text(v)

    def fav(self, row):
        given = self.favorable(row) if callable(self.favorable) else self.favorable
        hb = row.get("higher_better") if isinstance(row, dict) else None
        if hb is not None:
            want = "up" if hb else "down"
            if given is not None and given != want and not callable(self.favorable):
                raise ValueError(f"Variance：行 {row.get('label', row.get('key', ''))!r} 的 higher_better={bool(hb)}（"
                                 f"{'越高越好' if hb else '越低越好'}；METRICS 没写时默认越高越好，status/达标也按它算），favorable 却给了 "
                                 f"{given!r}——颜色会画反。删掉 favorable 让 Variance 按行的 higher_better 上色；确实越低越好的指标"
                                 "（成本、费用率、不良率）在 METRICS 里写 higher_better=False")
            return want
        return given or "up"

    def text(self, v):
        if self.fmt:
            t = str(self.fmt(v))
            return re.sub(r"^([+−\-±])\s*[+−\-±]+", r"\1", t)   # "−+6.1%" / "++3.3%" from a fmt that signs twice
        if self.pct:
            from ._ibcs import pct_text
            return pct_text(v)
        return ("+" if v > 0 else ("−" if v < 0 else "±")) + fmt(abs(v))


def _column_formats(rows, columns):
    """Bar / Heat columns left on the default fmt share one decimal count; a Spark's end label reuses the string a
    value column of the same row prints for that number (sparkline "5" next to a cell "4.95")."""
    for c in columns:
        if isinstance(c, (Bar, Heat)):
            if getattr(c, "_fmt0", None) is None:
                c._fmt0 = c.fmt
            if c._fmt0 is _dfmt:
                c.fmt = _shared_fmt([_val(r, c.field) for r in rows if isinstance(r, dict)])
        elif isinstance(c, Spark):
            if getattr(c, "_fmt0", None) is None:
                c._fmt0 = c.fmt
            if c._fmt0 is not _dfmt:
                continue
            lasts = [next((v for v in reversed(_val(r, c.field) or []) if v is not None), None) for r in rows
                     if isinstance(r, dict)]
            base = _shared_fmt(lasts)
            peers = [x for x in columns if isinstance(x, (Bar, Heat))]

            def sp(v, base=base, peers=peers):
                for x in peers:   # same number in a value column → same text
                    vals = [_val(r, x.field) for r in rows if isinstance(r, dict)]
                    if any(isinstance(u, (int, float)) and abs(float(u) - float(v)) < 1e-9 for u in vals):
                        return x.fmt(v)
                return base(v)
            c.fmt = sp


_ZH_REF = {"PL": "对目标", "BU": "对预算", "PY": "对去年", "FC": "对预测"}


def _zh_table(ex, rows, columns):
    """A Chinese table: the exhibit is in Chinese or a row label has CJK."""
    from ._text import has_cjk
    if ex.body_lang:
        return True
    lab = next((c for c in columns if isinstance(c, Label)), None)
    return bool(lab) and any(has_cjk(str(_val(r, lab.field) or "")) for r in rows)


def _record_facts(ex, rows, columns):
    """What the table showed, for the title-vs-data check at publish: status counts, per-row variance (kept on the
    exhibit and in _page.FACTS for pages whose fragments are passed by hand)."""
    from ._page import FACTS as _G

    class _Both(list):
        def append(self, x):
            _G.append(x)
            ex.__dict__.setdefault("facts", []).append(x)
    FACTS = _Both()
    lab = next((c for c in columns if isinstance(c, Label)), None)
    name = lambda r: str(_val(r, lab.field) if lab else r.get("label", ""))
    bars = [(i, c) for i, c in enumerate(columns) if isinstance(c, Bar) and isinstance(c.field, str)]
    FACTS.append({"kind": "chart", "fn": "row_table", "cats": [name(r) for r in rows if not r.get("_style")],
                  "series": [(str(c.header or c.field), [_val(r, c.field) for r in rows if not r.get("_style")])
                             for _, c in bars], "col": [i for i, _ in bars],
                  "headers": [str(c.header or getattr(c, "field", "") or "") for c in columns]})
    for c in columns:
        if isinstance(c, Status):
            vals = [_val(r, c.field) for r in rows if not r.get("_style")]
            FACTS.append({"kind": "status", "counts": {k: sum(1 for v in vals if v == k) for k in ("green", "amber", "red")},
                          "n": sum(1 for v in vals if v is not None)})
            break
    var = [c for c in columns if isinstance(c, Variance)]
    var = [c for c in var if not c.pct] or var
    units = {str(r.get("unit", "")).strip() for r in rows if isinstance(r, dict)}
    if var and len(units) <= 1:   # KPI tables mixing 亿元 and % rows: magnitudes are not comparable
        items = [(name(r), var[0].value(r)) for r in rows if not r.get("_style")]
        FACTS.append({"kind": "variance", "items": [(k, v) for k, v in items if v is not None]})


def _val(row, field):
    return field(row) if callable(field) else row.get(field)


_AC_KEYS = ("ac", "actual", "now", "cur", "current")
_REF_KEYS = ("py", "ly", "pl", "bu", "fc", "ref", "prev", "target", "budget", "plan")
_SIGNED = re.compile(r"^\s*([+\-−])\s*\d")


def _ac_ref_fields(rows, columns):
    """(ac_field, ref_field) of the table's two-scenario comparison: a Variance column's ac/ref, a Dumbbell whose series
    names tell actual from reference, or row keys ac/actual/now + py/ly/pl/target/…; None when unclear."""
    from ._kpi import ac_minus_ref_order
    for c in columns:
        if isinstance(c, Variance) and isinstance(c.ac, str) and isinstance(c.ref, str):
            return c.ac, c.ref
    for c in columns:
        if isinstance(c, Dumbbell) and len(c.series) >= 2:
            s0, s1 = c.series[0], c.series[-1]
            if isinstance(s0[0], str) and isinstance(s1[0], str):
                o = ac_minus_ref_order((str(s0[1]), s0[0]), (str(s1[1]), s1[0]))
                if o:
                    return (s1[0], s0[0]) if o > 0 else (s0[0], s1[0])
    keys = set().union(*[set(r) for r in rows if isinstance(r, dict)]) if rows else set()
    ac = next((k for k in _AC_KEYS if k in keys), None)
    ref = next((k for k in _REF_KEYS if k in keys), None)
    return (ac, ref) if ac and ref else None


def _check_delta_sign(rows, columns):
    """A Text column headed Δ… whose signed values contradict AC − reference on every row (a delta precomputed as
    PY − AC) raises — the reader would see a decline as growth."""
    texts = [c for c in columns if isinstance(c, Text) and "Δ" in str(c.header or "")]
    if not texts:
        return
    pair = _ac_ref_fields(rows, columns)
    if not pair:
        return
    body = [r for r in rows if isinstance(r, dict) and not r.get("_style")]
    for c in texts:
        n = bad = 0
        for r in body:
            a, b = r.get(pair[0]), r.get(pair[1])
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or abs(a - b) < 1e-9:
                continue
            try:
                t = str(c.fmt(r))
            except Exception:  # noqa: BLE001 — a fmt that cannot run here fails later with its own error
                return
            m = _SIGNED.match(t)
            if not m or not re.search(r"[1-9]", t):
                continue
            n += 1
            bad += (m.group(1) == "+") != (a - b > 0)
        if n and bad == n and (n >= 2 or len(body) == 1):
            raise ValueError(f"差异符号与 AC−对照相反：列 {c.header!r} 每行的正负号都与 {pair[0]} − {pair[1]} 相反"
                             f"（如 {pair[0]}={body[0].get(pair[0])}、{pair[1]}={body[0].get(pair[1])} 却写成 "
                             f"{c.fmt(body[0])}）——差异一律按 实际 − 对照（去年/预算）算：把 Text 里的 r[ref] − r[ac] 改成 "
                             "r[ac] − r[ref]，或直接用 Variance(ac, ref) 列让库来算")


RISK_LEVELS = {"高", "中", "低", "high", "medium", "low"}
_LEVELISH = re.compile(r"^\s*(?:极?[高中低](?:[高中低])?(?:风险|等级|级)?|[中高低]-[中高低]|(?:very |medium[- ])?(?:high|medium|low)"
                       r"(?:[- ](?:high|medium|low))?|mid(?:dle)?)\s*$", re.I)


def check_risk_levels(values, where="等级"):
    """Level words in a Status / Heat column or a risk_matrix: only 高/中/低 (High/Medium/Low). 中高 / 中低 /
    Medium-High blur the ranking the matrix exists for — raise. Non-level strings and numbers are left alone."""
    bad = []
    for v in values:
        if not isinstance(v, str):
            continue
        s = v.strip()
        if _LEVELISH.match(s) and re.sub(r"(?:风险|等级|级)$", "", s).strip().lower() not in RISK_LEVELS:
            bad.append(s)
    if bad:
        raise ValueError(f"{where}：{sorted(set(bad))[:4]}——风险等级只用高/中/低（High/Medium/Low），"
                         "介于两档之间就归到更接近的一档，差别写进应对说明")


def _range_defaults(col, rows):
    """Range columns: a value range gets endpoint labels and a numeric axis unless switched off; a time range (Gantt,
    years 1900–2100) keeps bare bars. Idempotent (resolved values are stored on the column)."""
    vals = [v for r in rows for v in (_val(r, col.lo), _val(r, col.hi)) if isinstance(v, (int, float))]
    gantt = bool(vals) and all(1900 <= v <= 2101 for v in vals)
    if col.labels == "auto":
        col.labels = "none" if gantt else "values"
    if col.ticks is None and not gantt and vals:
        lo, hi = col.domain or _domain(col, rows)
        col.ticks = [t for t in nice_ticks(hi, 4, lo if lo else 0) if lo - 1e-9 <= t <= hi + 1e-9]
    elif col.ticks is False:
        col.ticks = None


def _fit_dumbbell_domain(col, rows):
    """A caller-given Dumbbell domain that leaves points outside (axis to 60, values 64 / 70.3) is widened to cover every
    value; caller ticks are recomputed on the new domain. Returns the new domain or None (unchanged)."""
    if not col.domain:
        return None
    vals = [v for r in rows for f, *_ in col.series for v in [_val(r, f)] if isinstance(v, (int, float))]
    if not vals:
        return None
    lo, hi = col.domain
    if min(vals) >= lo and max(vals) <= hi:
        return None
    nlo, nhi = min(lo, min(vals)), max(hi, max(vals))
    t = nice_ticks(nhi, 4, nlo)
    col.domain = (min(t[0], nlo), max(t[-1], nhi))
    if col.ticks:
        col.ticks = [x for x in t if col.domain[0] - 1e-9 <= x <= col.domain[1] + 1e-9]
    print(f"Dumbbell：domain=({lo:g}, {hi:g}) 装不下数据（{min(vals):g}–{max(vals):g}），已放宽到 "
          f"({col.domain[0]:g}, {col.domain[1]:g})")
    return col.domain


INVISIBLE_SHARE = 0.03   # a gap below 3 % of the axis span: the two points overlap and the change cannot be seen
INVISIBLE_DUMBBELL = "两期差异小于轴长 3%，点重合看不出变化：改差异条（Variance）或缩小轴域"


def add_issue(ex, msg):
    """Record a chart problem in ex.extra_issues (ex.check() reports it; Frame.publish holds the page)."""
    if ex is not None:
        ex.extra_issues = list(dict.fromkeys(list(getattr(ex, "extra_issues", None) or []) + [msg]))


def _invisible_dumbbell(ex, col, rows):
    """Every row's first↔last gap < INVISIBLE_SHARE of the Dumbbell axis span (e.g. 0.5pt on a 0–40 % axis)."""
    if len(col.series) < 2 or not getattr(col, "_dom", None):
        return False
    span = col._dom[1] - col._dom[0]
    f0, f1 = col.series[0][0], col.series[-1][0]
    gaps = [abs(b - a) for r in rows if not r.get("_style")
            for a, b in [(_val(r, f0), _val(r, f1))] if isinstance(a, (int, float)) and isinstance(b, (int, float))]
    if span <= 0 or len(gaps) < 2 or max(gaps) >= INVISIBLE_SHARE * span:
        return False
    add_issue(ex, f"{INVISIBLE_DUMBBELL}（最大差 {fmt(max(gaps))}，轴长 {fmt(span)}）")
    return True


def _domain(col, rows):
    if col.domain:
        return col.domain
    vals = []
    for r in rows:
        if isinstance(col, Bar):
            vals.append(_val(r, col.field))
        elif isinstance(col, Dumbbell):
            vals += [_val(r, f) for f, *_ in col.series]
        elif isinstance(col, Range):
            vals += [_val(r, col.lo), _val(r, col.hi)] + ([_val(r, col.point)] if col.point else [])
        elif isinstance(col, Diverge):
            vals += [_val(r, col.left), _val(r, col.right)]
        elif isinstance(col, Heat):
            vals.append(_val(r, col.field))
        elif isinstance(col, Box):
            vals += [_val(r, f) for f in col.fields]
        elif isinstance(col, Scen):
            vals += [_val(r, col.ac)] + ([_val(r, col.ref)] if col.ref is not None else [])
        elif isinstance(col, Variance):
            vals.append(col.value(r))
    vals = [v for v in vals if v is not None]
    if isinstance(col, (Scen, Variance)):   # no ticks: bars use the full width, zero always on the scale
        lo, hi = min(vals + [0]), max(vals + [0])
        return (lo, hi) if hi > lo else (-1, 1)
    if isinstance(col, Bar) and col.cumulative:
        return (0, sum(v for v in vals if v > 0))
    if isinstance(col, Heat):
        return (min(vals), max(vals))
    if isinstance(col, Diverge):
        return (0, max(vals))
    lo, hi = min(vals + [0]), max(vals)
    pos = sorted((v for v in vals if v > 0), reverse=True)
    if isinstance(col, Bar) and len(pos) >= 3 and pos[0] > 4 * pos[1] and pos[1] > 0:
        hi = pos[1] * 1.3   # one outlier (494.7x next to 20–40x) would squeeze every other bar: break its bar instead
        col._broken = True
    if isinstance(col, (Dumbbell, Range, Box)) and min(vals) > 0 and min(vals) > 0.45 * hi:
        # points/intervals far from zero: zoom the scale so the gap the title talks about is visible
        lo = min(vals) - (hi - min(vals)) * 0.25
    t = nice_ticks(hi, 4, lo if lo != 0 else 0)
    return (t[0], t[-1])


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x + (y - x) * t):02X}" for x, y in zip(a, b))


def _luma(c):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b


def _min_width(c, rows, total=None):
    """Narrowest a fixed-width column may be squeezed to when row_table scales widths down to fit its box."""
    w = c.width or 0
    if isinstance(c, Label):
        pool = rows + ([total] if total else [])
        words = [p for r in pool for p in re.split(r"[\s/·、，,]+", str(_val(r, c.field) or "")) if p]
        filled_ = getattr(c, "_fill", False)
        longest = max([tw(p if not has_cjk(p) else p[:4], c.size, c.weight >= 600 or filled_) for p in words] + [0])
        return min(w, max(40.0, longest + 6 + (max(2 * getattr(c, "_pad", LABEL_PAD) - 6, 0) if filled_ else 0), 0.55 * w))
    if isinstance(c, Text):
        head = max([tw(h, 10.5) for h in str(c.header or "").split("\n")] + [0])
        return min(w, max(28.0, head, 0.6 * w))
    if isinstance(c, Note):
        return min(w, max(120.0, 0.7 * w))
    return min(w, max(24.0, 0.75 * w))   # Heat / Status / Harvey / Rank / Spark / fixed-width scaled columns


ROW_MAX = 110   # canvas px (≈137 on the slide): a 2–3 row table fills its box with roomy rows


def _bracket_candidates(rows, i0, i1, total=None):
    """Values a bracket label over rows i0..i1 may state: per numeric field the sum / mean of the bracketed rows and
    their share of all rows (or of the total row), and the mean / sum of differences between two numeric fields."""
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    sel = [r for r in rows[i0:i1 + 1] if isinstance(r, dict)]
    fields = sorted({k for r in sel for k, v in r.items() if num(v) and not str(k).startswith("_")})
    out = []
    for k in fields:
        vs = [r[k] for r in sel if num(r.get(k))]
        if not vs:
            continue
        S = sum(vs)
        out += [S, S / len(vs)]
        allv = sum(r[k] for r in rows if isinstance(r, dict) and num(r.get(k)))
        for base in (allv, (total or {}).get(k) if num((total or {}).get(k)) else None):
            if base:
                out += [S / base, 1 - S / base]
    for a in fields:
        for b in fields:
            if a < b:
                d = [r[b] - r[a] for r in sel if num(r.get(a)) and num(r.get(b))]
                if d:
                    out += [sum(d), sum(d) / len(d)]
    return out


def _check_brackets(rows, brackets, total=None):
    """A bracket label's numbers ("其余 9 家合计 30.1%") must be what the bracketed rows add up to (程序算)."""
    from ._marks import check_label_numbers
    for b in brackets or ():
        i0, i1, text = b[0], b[1], b[2]
        if not (0 <= i0 <= i1 < len(rows)):
            raise ValueError(f"row_table brackets=({i0}, {i1}, …)：行号越界（共 {len(rows)} 行，从 0 数）")
        check_label_numbers(text, _bracket_candidates(rows, i0, i1, total), f"row_table brackets=({i0}, {i1}, {text!r})",
                            what=f"第 {i0}–{i1} 行的合计/均值/占比")


_DRAWN_COLS = (Label, Text, Note, Rank, Bar, Scen, Variance, Dumbbell, Range, Heat, Spark, Status, Harvey, Box, Diverge)


def _check_column_kinds(columns):
    """Every column must be a class row_table draws: a bare Col(...) or a foreign object would be skipped silently
    (the page shows only the other columns)."""
    names = " / ".join(k.__name__ for k in _DRAWN_COLS) + " / Level"
    for i, c in enumerate(columns):
        if not isinstance(c, _DRAWN_COLS):
            raise ValueError(f"row_table：第 {i + 1} 列是 {type(c).__name__}，row_table 不会画它（整列会消失）——"
                             f"换成具体列类：{names}（文字用 Text(\"字段\") / Note，数值用 Bar / Heat，评分用 Harvey / Level）")


def _check_empty_text_columns(rows, columns):
    """A text column whose every cell is empty is almost always a misspelt field name (Text("assump") on rows that
    carry "assumption")."""
    body = [r for r in rows if isinstance(r, dict) and not r.get("_style")]
    if not body:
        return
    for c in columns:
        if isinstance(c, Label):
            cells = [_val(r, c.field) for r in body]
        elif isinstance(c, Text):
            try:
                cells = [c.fmt(r) for r in body]
            except (KeyError, TypeError, IndexError):
                continue
        elif isinstance(c, Note):
            cells = [(c.parts(r)[0] + c.parts(r)[1]) for r in body]
        else:
            continue
        if all(v is None or str(v).strip() == "" for v in cells):
            key = getattr(c, "_key", None) or getattr(c, "field", None)
            have = sorted({k for r in body for k in r if not str(k).startswith("_")})
            raise ValueError(f"row_table：{type(c).__name__} 列 {c.header or key!r} 每行都是空的——字段名可能写错"
                             f"（列取的是 {key!r}，行里的字段有 {have[:12]}）；改成行里真实的字段名，或删掉这一列")


def _check_time_rows(rows, columns):
    """Time runs left to right: a table whose rows are ≥3 consecutive periods (2022 / 2023 / 2024, 24Q1…) drawn as a
    Bar / Dumbbell / Variance column reads like a ranking with a 'top' row — print a non-blocking nudge toward
    columns(..., rows=); the author may ignore it when the layout is deliberate."""
    from ._page import is_period
    lab = next((c for c in columns if isinstance(c, Label) and getattr(c, "level", 1) == 1), None)
    if lab is None:
        return
    body = [r for r in rows if isinstance(r, dict) and not r.get("_style")]
    cats = [str(_val(r, lab.field) or "").strip() for r in body]
    if len(cats) < 3 or not all(c and is_period(c) for c in cats):
        return
    bars = [c for c in columns if isinstance(c, (Bar, Dumbbell, Variance, Diverge, Scen))]
    if not bars:
        return
    names = "、".join(str(c.header or getattr(c, "_key", "") or type(c).__name__) for c in bars[:3])
    print(f"提醒（不阻塞）：row_table 的行是时间（{cats[0]}…{cats[-1]}），{names} 画成了横条——时间通常从左往右排，竖排容易读成有'最大值'的排名。"
          "一般改用 columns(ex, box, 年份, [(指标, 值, 色)], rows=[(第二指标, 值, fmt)])：年份做横轴，主指标画柱，同比 / 利润率 / 份额放轴下数据行；"
          "多个指标的时间序列用 lines 或 small_multiples。如果是有意为之（如期数很多、横向放不下），忽略本提醒即可")


def _check_total_row(ex, rows, columns, total):
    """The total row of a table: each numeric field must equal the sum of the rows (or their mean, for rates / per-unit
    fields) within 2 % — "合计 7,437" over segments that add to 7,518 is a typo the reader catches at once."""
    if not isinstance(total, dict):
        return
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    bad = []
    for c in columns:
        f_ = getattr(c, "field", None)
        if not isinstance(f_, str) or isinstance(c, Label):
            continue
        tv = total.get(f_)
        vals = [r.get(f_) for r in rows if isinstance(r, dict) and not r.get("_style")]
        if not num(tv) or len(vals) < 2 or not all(num(v) for v in vals):
            continue
        sm, mean = sum(vals), sum(vals) / len(vals)
        tol = lambda x: abs(tv - x) <= max(0.02 * abs(x), 0.51)
        if min(vals) >= 0 and tv < sm and not (tol(sm) or tol(mean) or min(vals) <= tv <= max(vals)):
            bad.append(f"{c.header or f_}：合计 {tv:g} 小于各行之和 {sm:g}")   # rows may list only the top N: a bigger total is fine
    if bad:
        add_issue(ex, "合计行与各行对不上——" + "；".join(bad[:3]) + "：合计用程序 sum(各行) 算，或在表头写明口径（如'含其他'）")


def row_table(ex, box, rows, columns, total=None, brackets=(), focus=None, header_size=10.5, zebra=False, rules=True,
              row_h=None, gap=14, group_rules=True, legend_items=None, max_row_h=None, head_rules=True,
              first_col="auto"):
    """Draw a shared-row chart table in box. Returns {"y": {label: cy}, "cols": [(x0, x1)] in column order,
    "col": {header or field: (x0, x1)}, "row_h": h, "top": y, "bottom": y of the last row's bottom}. Annotate a column
    by name — r["col"]["规模，亿元"] — not by index (cols[0] is the Label column).

    rows: list of dicts; a row may set "_style": "muted" (grey, e.g. 'Rest of') and "_bold": True.
    first_col="auto" (default): "plain" — bold label text, no block (a column of solid blocks reads like a bar chart).
    first_col="fill" (McKinsey): when the first column is a row Label (level=1), each of its cells is a solid
    dark block (palette main / deep; focus rows in the darkened accent, muted rows grey) with white bold text, white
    gaps between blocks; the head cell stays a plain bold head + rule and row hairlines start at the second column.
    first_col="plain": the label is ordinary text.
    """
    from ._page import check_box as _cb
    _cb(box, "row_table")
    _col_types = tuple(v for v in (globals().get(n) for n in ("Label", "Text", "Bar", "Range", "Heat", "Note", "Spark",
                                                               "Variance", "Dumbbell", "Scen", "Status", "Harvey", "Rank"))
                       if isinstance(v, type))
    for r_ in rows:
        bad_ = [k for k, v in (r_.items() if isinstance(r_, dict) else []) if isinstance(v, _col_types)]
        if bad_:
            raise ValueError(f"row_table：rows 里放的是列对象（{bad_[0]}={type(r_[bad_[0]]).__name__}(...)）——rows 每行是"
                             "普通值 dict(方法='PE', lo=364, hi=505, 假设='18–25x')，列类型写在 columns=[Label('方法'), "
                             "Range('lo', 'hi'), Text('假设')]；只要文字表就用 text_table(x, y, w, 表头, 行列表)")
    C = ex.C
    from ._page import chart_box as _cbx
    box = _cbx(ex, box)
    dim = C["dim"]
    if focus is not None and not callable(focus):   # focus=2 / "宁德时代" / [0, 1]: row index(es) or label(s)
        keys = set(focus) if isinstance(focus, (list, tuple, set)) else {focus}
        idx = {id(r) for i, r in enumerate(rows) if i in keys or str(r.get("label")) in {str(k) for k in keys}}
        focus = lambda r: id(r) in idx   # noqa: E731
    from ._page import check_box
    x0, y0, x1, y1 = check_box(box, "row_table")
    _check_column_kinds(columns)
    _check_brackets(rows, brackets, total)
    from ._page import TABLES
    TABLES.append((len(rows), len(columns)))
    if legend_items is None:   # dumbbell end points carry the period identity: name them unless the header already does
        for c in columns:
            if isinstance(c, Dumbbell) and len(c.series) >= 2 and not all(str(s_[1]) in str(c.header) for s_ in c.series):
                legend_items = [(str(s_[1]), s_[2] or ex.C["main"], "dot") for s_ in c.series]
                break
    if len(rows) == 1 and total is None and any(isinstance(c, (Bar, Dumbbell, Range)) for c in columns):
        raise ValueError("row_table 只有 1 行：一根条 / 一对点看不出比较——单个指标的实际 vs 目标用 target_columns 或 big_number + 差值一句话；"
                         "或把同类的几个指标合成多行（每行一个指标）")
    if len(rows) >= 2 and not any(isinstance(c, Label) for c in columns):
        first = columns[0] if columns else None
        if isinstance(first, Text) and getattr(first, "_key", None):   # Text("year") first: it is the row label
            columns = [Label(first._key, header=first.header, weight=700)] + list(columns[1:])
        else:
            key = next((k for k in ("label", "name", "名称", "公司", "company", "year", "年份") if all(k in r for r in rows)), None)
            if key is None:
                raise ValueError("row_table 没有 Label 列：每行看不出是谁——第一列加 Label(\"label\")（对象名/年份/部件）")
            columns = [Label(key, weight=700)] + list(columns)
    _check_time_rows(rows, columns)
    for c in columns:   # a data column that is mostly "未披露" is an empty chart, not evidence
        if isinstance(c, Range):
            _range_defaults(c, rows)
        if isinstance(c, Dumbbell):
            if hasattr(c, "_diff_original_header"):
                c.header, c.ticks = c._diff_original_header, c._diff_original_ticks
            _fit_dumbbell_domain(c, rows)
        if isinstance(c, (Status, Heat)):
            check_risk_levels([_val(r, c.field) for r in rows], c.header or c.field)
        elif isinstance(c, (Text, Label)) and re.search(r"等级|级别|level|rating", str(c.header or ""), re.I):
            vals = [c.fmt(r) if isinstance(c, Text) else _val(r, c.field) for r in rows if not r.get("_style")]
            check_risk_levels(vals, c.header)
        if isinstance(c, (Bar, Range)) and len(rows) >= 3:
            keys = [c.field] if isinstance(c, Bar) else [c.lo, c.hi]
            miss = sum(1 for r in rows if any(_val(r, k) is None for k in keys))
            if miss / len(rows) > 0.4:
                raise ValueError(f"row_table：列 {c.header or keys[0]!r} 有 {miss}/{len(rows)} 行缺数据——去掉这一列（或改成 Text "
                                 "列写'未披露'），或只保留有数据的行；不要画一列空条")
            if isinstance(c, Range):   # a range whose ends coincide on most rows is a column of dots without meaning
                flat = sum(1 for r in rows if _val(r, c.lo) is not None and _val(r, c.lo) == _val(r, c.hi))
                if flat / len(rows) > 0.5:
                    raise ValueError(f"row_table：Range 列 {c.header or c.lo!r} 有 {flat}/{len(rows)} 行起止相同（只有一个值）——"
                                     "单值用 Bar 或 Text 列；区间要真有上下限")
                lo_s = [_val(r, c.lo) for r in rows]
                hi_s = [_val(r, c.hi) for r in rows]
                if None not in lo_s + hi_s and len(set(lo_s)) == 1 and len(set(hi_s)) == 1 and c.domain \
                        and (hi_s[0] - lo_s[0]) >= 0.6 * (c.domain[1] - c.domain[0]):
                    raise ValueError(f"row_table：Range 列 {c.header or c.lo!r} 每行起止都一样（{lo_s[0]}–{hi_s[0]}），"
                                     "条形全等，读不出任何差别——一个季度内的措施改用 exhibit_help('action_plan')（每条补回多少、累加到缺口），"
                                     "或换成 Dumbbell 列画'当前值 → 目标值'；时间写进 Text 列")
    _check_empty_text_columns(rows, columns)
    _check_delta_sign(rows, columns)
    _check_total_row(ex, rows, columns, total)
    _column_formats(rows + ([total] if total else []), columns)
    if any(isinstance(c, Variance) and c._auto_header for c in columns) and _zh_table(ex, rows, columns):
        for c in columns:
            if isinstance(c, Variance) and c._auto_header:
                c.header = c.zh_header()
    flex = [c for c in columns if c.width is None]
    units = {str(r.get("unit", "")).strip() for r in rows if isinstance(r, dict)} - {""}
    for c in columns:   # 亿元 / 万单 / pt rows on one absolute scale: bar lengths compare nothing — numbers only
        if isinstance(c, Variance):
            c.text_only = (not c.pct) and len(units) >= 2
    from ._page import first_col_mode
    _labels0 = ([_val(r, columns[0].field) for r in rows if not r.get("_style")]
                if columns and isinstance(columns[0], Label) else [])
    mode1 = first_col_mode(first_col, _labels0)
    fill1 = (mode1 in ("fill", "light") and columns and isinstance(columns[0], Label) and columns[0].level == 1
             and len(columns) >= 2)
    if columns and isinstance(columns[0], Label):   # set every call: a Label object reused with first_col="plain"
        columns[0]._fill = bool(fill1)
        columns[0]._light = bool(fill1) and mode1 == "light"
        columns[0]._pad = LABEL_PAD
        if fill1 and columns[0].width is None and not any(c.width is None for c in columns[1:]):
            # every other column has a fixed width: the block inset widens the table, so keep it tight unless the box
            # has room to spare (hand-drawn brackets / notes often use the margin right of the last column)
            others = sum(c.width for c in columns[1:]) + gap * (len(columns) - 1)
            pool_ = rows + ([total] if total else [])
            lw_ = max(tw(str(_val(r, columns[0].field) or ""), columns[0].size, True) for r in pool_) * 1.08 + 6
            if others + lw_ + 2 * LABEL_PAD + 72 > x1 - x0:
                columns[0]._pad = 4
    for c in list(flex):
        if isinstance(c, Label):
            pool = rows + ([total] if total else [])
            filled_ = getattr(c, "_fill", False) and c is columns[0]
            ins = 2 * c._pad - 6 if filled_ else 0   # the plain label already has 6px of slack
            # the server measures bold CJK a little wider than tw(): 8 % slack keeps the text inside its block
            c.width = min(max(tw(str(_val(r, c.field) or ""), c.size, c.weight >= 600 or filled_) for r in pool)
                          * (1.08 if filled_ else 1) + 6 + max(ins, 0), (c.wrap_w + max(ins, 0)) if c.wrap_w else 10 ** 6)
            if filled_:
                c.width = float(math.ceil(c.width))
            flex.remove(c)
    extra = {}
    for i0, i1, text, ci in brackets:
        extra[ci] = max(extra.get(ci, 0), 18 + tw(text, 11.5, True) + 4)
    def _need(c):   # label room a scaled column needs besides its bars (variance / scenario value labels)
        if isinstance(c, Variance):
            vs = [(c.value(r), r) for r in rows]
            head = 7.4 if c.pct else 3
            pos = max([tw(c.label(r, v), c.size) for v, r in vs if v is not None and v > 0] + [0])
            neg = max([tw(c.label(r, v), c.size) for v, r in vs if v is not None and v < 0] + [0])
            return pos + neg + 2 * head + 8 + 16
        if isinstance(c, Scen):
            return max([tw(c.fmt(_val(r, c.ac)), c.size) for r in rows if _val(r, c.ac) is not None] + [0]) + 8 + 30
        return 40
    need = {id(c): _need(c) for c in flex}
    fixed = sum(c.width for c in columns if c.width is not None) + gap * (len(columns) - 1) + sum(extra.values())
    free = (x1 - x0) - fixed
    if sum(need.values()) > free:
        # fixed widths (Label / Text / Heat / Note …) wider than the chart area: scale them down proportionally to
        # each column's minimum instead of failing — only raise when even the minimums cannot fit
        fixed_cols = [c for c in columns if c not in flex]
        mins = {id(c): _min_width(c, rows, total) for c in fixed_cols}
        deficit = sum(need.values()) - free
        room = sum(max(0.0, c.width - mins[id(c)]) for c in fixed_cols)
        if room + 1e-6 < deficit:
            gap_need = sum(need.values()) + sum(mins.values()) + gap * (len(columns) - 1) + sum(extra.values())
            sug = "、".join(f"{type(c).__name__}({(c.header or getattr(c, 'field', '') or '')!r}) width={mins[id(c)]:.0f}"
                           for c in fixed_cols if not isinstance(c, Label))
            raise ValueError(f"row_table 列放不下：即使每列缩到最小也需约 {gap_need:.0f}px，图区只有 {x1 - x0:.0f}px（画布单位）"
                             f"。建议：去掉一列（或把句子并进 Note 列）、加大 Exhibit(w=)，或 gap= 调小"
                             + (f"；最小可用宽度参考 {sug}" if sug else "")
                             + ("；差异/情景列数值标签另需 %.0fpx" % sum(need.values()) if any(
                                 isinstance(c, (Variance, Scen)) for c in flex) else ""))
        for c in fixed_cols:
            c.width -= max(0.0, c.width - mins[id(c)]) * deficit / room
        fixed = sum(c.width for c in columns if c.width is not None) + gap * (len(columns) - 1) + sum(extra.values())
        free = (x1 - x0) - fixed
    spare = free - sum(need.values())
    for c in flex:   # every flexible column gets its label room, the rest is shared equally
        c.width = need[id(c)] + spare / len(flex)
    for c in flex:   # a time bar squeezed into a sliver reads as a dot: borrow width from the widest text columns
        want = 110 if isinstance(c, Range) else (170 if isinstance(c, Bar) and c.cumulative else
                                                 (100 if isinstance(c, (Bar, Dumbbell)) else 0))
        if want and c.width < want:
            floor_ = 120 if not isinstance(c, (Bar, Dumbbell)) or getattr(c, "cumulative", False) else 64   # short value columns can give
            donors = [d for d in columns if isinstance(d, (Text, Note)) and d.width > floor_]
            need = want - c.width
            room = sum(d.width - floor_ for d in donors)
            if room > 0:
                take = min(need, room)
                for d in donors:
                    d.width -= take * (d.width - floor_) / room
                c.width += take
    xs, cx = [], x0
    for i, c in enumerate(columns):
        xs.append((cx, cx + c.width))
        cx += c.width + gap + extra.get(i, 0)
    scaled = (Bar, Dumbbell, Range, Diverge, Box, Scen, Variance)
    if any(isinstance(c, (Variance, Spark)) or (isinstance(c, Bar) and c.cumulative) for c in columns):
        ex.notes += 1   # variance bars / pins are the argument annotation of an IBCS table
    has_header = any(c.header for c in columns) or any(isinstance(c, scaled) and c.ticks for c in columns)
    top_both = any(isinstance(c, scaled) and c.ticks and c.ticks_pos == "top" and c.header for c in columns)
    for c, (a_, b_) in zip(columns, xs):   # a header wider than its column wraps inside it (never into the neighbour)
        if c.header and "\n" not in str(c.header) and tw(str(c.header), header_size, bold=True) > (b_ - a_) + 2:
            from ._text import wrap as _wrp
            c.header = "\n".join(_wrp(str(c.header), header_size, max(b_ - a_, 20), bold=True)[:3])
    head_lines = max([len(str(c.header).split("\n")) for c in columns if c.header] + [1])
    head_h = ((40 if top_both else 22) + 12.5 * max(head_lines - 1, 0) * (0 if top_both else 1)) if has_header else 0
    bottom_ticks = any(isinstance(c, scaled) and c.ticks and c.ticks_pos == "bottom" for c in columns)
    leg_h = 24 if legend_items else 0
    n = len(rows) + (1 if total else 0)
    # Rows share the box height: few rows grow taller (up to ROW_MAX) so the table fills its box instead of sitting on
    # the top half of the page; max_row_h is only honoured while the table still fills most of the box. What a cap
    # leaves over is split evenly above and below (the table is centred in its box), never all at the bottom.
    extra_h = head_h + leg_h + (6 if total else 0) + (22 if bottom_ticks else 0)
    avail = (y1 - y0 - extra_h) / n
    if row_h is None:
        cap = ROW_MAX
        if max_row_h and (max_row_h * n + extra_h) >= 0.85 * (y1 - y0):
            cap = max_row_h
        row_h = min(avail, cap)
    from ._layouts import SQUEEZE_MAX, _squeezed, split_hint
    fit = (y1 - y0 - extra_h) / n   # the most a row may take inside the box
    notes = [c for c in columns if isinstance(c, Note)]
    if notes:   # rows grow to the tallest note cell; the box must hold them
        need = max(c.height(r) for c in notes for r in rows)
        if need > row_h:
            if need > fit + 0.5 and need <= fit * (1 + SQUEEZE_MAX):   # small overflow: note cell padding 10 → 4px
                for c in notes:
                    c._pad = 4
                tight = max(c.height(r) for c in notes for r in rows)
                if tight <= fit + 0.5:
                    _squeezed(f"row_table Note 列超出 {need - fit:.0f}px/行（{need / fit - 1:.0%}）：已压缩行内留白，字号不变")
                    need = tight
                else:
                    for c in notes:
                        c._pad = 10
            if need > fit + 0.5:
                raise ValueError(f"row_table：Note 列最高需 {need:.0f}px/行，图区只够 {fit:.0f}px/行（{len(rows)} 行，超出 "
                                 f"{need / fit - 1:.0%}）——加宽 Note(width=)、缩短文字，或加大 Exhibit(h=)；"
                                 + split_hint("row_table", len(rows), (y1 - y0 - extra_h) / need))
            row_h = need
    text_need, text_tight = 0.0, 0.0   # wrapped Text cells: grow rows inside the box, ≤15 % over → tighter line spacing
    if fill1:   # a long label wraps inside its block (≤3 lines): rows grow so the wrapped lines stay inside it
        c0, (a0, b0) = columns[0], xs[0]
        lab_need = 0.0
        for r in rows:
            k_ = len(wrap(str(_val(r, c0.field) or ""), c0.size, (b0 - a0 - 2 * c0._pad) / 1.08, True))
            if k_ >= 2:
                lab_need = max(lab_need, k_ * c0.size * 1.18 + 10)
        if lab_need > fit + 0.5 or lab_need > 3 * c0.size * 1.18 + 10:   # would not fit / >3 lines: plain labels
            fill1, c0._fill = False, False
        else:
            text_need = max(text_need, lab_need)
    for c, (a, b) in zip(columns, xs):
        if isinstance(c, Text):
            for r in rows:
                s_ = c.fmt(r)
                bold_ = bool(r.get("_bold")) or c.weight >= 600
                if s_ in (None, "") or tw(str(s_), c.size, bold_) <= (b - a) + 2:
                    continue
                k_ = len(wrap(str(s_), c.size, b - a, bold_))
                text_need = max(text_need, k_ * c.size * 1.2 + 2)
                text_tight = max(text_tight, k_ * c.size * 1.05 + 2)
    tight_text = False
    if text_need > row_h:
        if text_need <= fit + 0.5:
            row_h = text_need
        elif text_tight <= fit + 0.5 and text_need <= fit * (1 + SQUEEZE_MAX):
            row_h, tight_text = fit, True
            _squeezed(f"row_table Text 列换行超出 {text_need - fit:.0f}px/行（{text_need / fit - 1:.0%}）：已收紧行距，字号不变")
        else:
            raise ValueError(f"row_table：Text 列换行后每行需 {text_need:.0f}px，图区只够 {fit:.0f}px/行（{len(rows)} 行，超出 "
                             f"{text_need / fit - 1:.0%}）——句子放 Note 列、加宽该列 width= 或缩短成关键词；"
                             + split_hint("row_table", len(rows), (y1 - y0 - extra_h) / text_need))
    if fill1 and row_h < columns[0].size * 1.18 + 9:   # rows too thin for a block around the text: plain labels
        fill1, columns[0]._fill = False, False
    used = row_h * n + extra_h
    y0 = y0 + max(0.0, (y1 - y0 - used) / 2)   # leftover height (a capped table) splits above and below
    top = y0 + head_h
    body_bottom = top + row_h * len(rows)
    # ---- headers, scales, ticks
    for ci, (c, (a, b)) in enumerate(zip(columns, xs)):
        if c.sep and ci > 0:
            ex.line(a - gap / 2, top - head_h, a - gap / 2, body_bottom + (22 if bottom_ticks else 0), stroke=C["context"],
                    width=0.9, tag="grid")
        if isinstance(c, scaled):
            c._dom = _domain(c, rows)
            if isinstance(c, Dumbbell):
                _invisible_dumbbell(ex, c, rows)
            if isinstance(c, Diverge):
                mid = (a + b) / 2
                room = max(tw(c.fmt(_val(r, f) or 0), 10) for r in rows for f in (c.left, c.right)) + 6
                c._sl = (lambda m, w, d, rm: (lambda v: m - v / d[1] * (w / 2 - rm)))(mid, b - a, c._dom, room)
                c._sr = (lambda m, w, d, rm: (lambda v: m + v / d[1] * (w / 2 - rm)))(mid, b - a, c._dom, room)
            else:
                pad_l = pad_r = 0.0
                if getattr(c, "ticks", None):
                    pad_l = tw(c.tick_fmt(c.ticks[0]), 10.5) / 2 + 2
                    pad_r = tw(c.tick_fmt(c.ticks[-1]), 10.5) / 2 + 2
                if isinstance(c, Range) and c.labels == "values":
                    pad_r = max(pad_r, max(tw((c.value_fmt(_val(r, c.point)) + f" ({c.value_fmt(_val(r, c.lo))}–{c.value_fmt(_val(r, c.hi))})")
                                              if c.point and _val(r, c.point) is not None else
                                              f"{c.value_fmt(_val(r, c.lo) or 0)}–{c.value_fmt(_val(r, c.hi) or 0)}", 10)
                                           for r in rows) + 8)
                if isinstance(c, Dumbbell) and c.labels == "values":
                    pad_r = max(pad_r, 10)
                if isinstance(c, Dumbbell) and c.delta:
                    pad_r = max(pad_r, _delta_pad(c, rows, a + pad_l, b - pad_r, zh=bool(ex.body_lang)))
                if isinstance(c, Scen):
                    labs = [c.fmt(_val(r, c.ac)) for r in rows if _val(r, c.ac) is not None]
                    pad_r = max(pad_r, max([tw(t, c.size) for t in labs] + [0]) + 8)
                    if c._dom[0] < 0:
                        pad_l = max(pad_l, max([tw(c.fmt(_val(r, c.ac)), c.size) for r in rows
                                                if (_val(r, c.ac) or 0) < 0] + [0]) + 8)
                if isinstance(c, Variance):
                    vs_r = [(c.value(r), r) for r in rows]
                    vs = [v for v, _ in vs_r]
                    head = 7.4 if c.pct else 3
                    pos = [tw(c.label(r, v), c.size) for v, r in vs_r if v is not None and v > 0]
                    neg = [tw(c.label(r, v), c.size) for v, r in vs_r if v is not None and v < 0]
                    pad_r = max(pos) + head + 4 if pos else (head + 2 if neg else 2)
                    pad_l = max(neg) + head + 4 if neg else (head + 2 if pos else 2)
                    if any(v == 0 for v in vs):
                        pad_r = max(pad_r, tw(c.text(0), c.size) + 6)
                if isinstance(c, Box) and c.labels == "median":
                    pad_r = max(pad_r, max(tw(c.value_fmt(_val(r, c.fields[2]) or 0), 10) for r in rows) + 8)
                aa, bb = a + pad_l, b - pad_r
                c._sx = (lambda a_, b_, d: (lambda v: a_ + (v - d[0]) / (d[1] - d[0]) * (b_ - a_)))(aa, bb, c._dom)
                if isinstance(c, Dumbbell):
                    _dumbbell_to_diff(ex, c, rows, a, b)
            if getattr(c, "ticks", None) and not isinstance(c, Diverge):
                ty = top - 8 if c.ticks_pos == "top" else body_bottom + 16
                for t in c.ticks:
                    ex.text(c._sx(t), ty, c.tick_fmt(t), size=10.5, fill=C["axis"], anchor="middle")
                    ex.line(c._sx(t), top, c._sx(t), body_bottom, stroke=C["grid"], width=0.7, tag="grid")
            if isinstance(c, Bar) and c._dom[0] < 0 < c._dom[1]:
                ex.line(c._sx(0), top, c._sx(0), body_bottom, stroke=C["axis"], width=0.9, tag="grid")
            if isinstance(c, Variance) and not getattr(c, "text_only", False):
                ex.line(c._sx(0), top - 2, c._sx(0), body_bottom, stroke=C["axis"], width=0.9, tag="grid")
            if isinstance(c, Variance):
                c._tx = b - 2   # text-only variance: right-aligned numbers
            if isinstance(c, Dumbbell) and getattr(c, "_diff", False):
                ex.line(c._sx(0), top - 2, c._sx(0), body_bottom, stroke=C["axis"], width=0.9, tag="grid")
            elif isinstance(c, Dumbbell) and c.zero_line and c._dom[0] < 0 < c._dom[1]:
                ex.line(c._sx(0), top, c._sx(0), body_bottom, stroke=C["context"], width=0.8, tag="grid")
            if isinstance(c, Range) and c.ref is not None:
                ex.line(c._sx(c.ref), top, c._sx(c.ref), body_bottom, stroke=C["context"], width=0.8, dash="3,3",
                        tag="grid")
            if isinstance(c, Diverge):
                ex.line((a + b) / 2, top, (a + b) / 2, body_bottom, stroke=C["axis"], width=0.8, tag="grid")
                if c.left_name:
                    ex.text((a + b) / 2 - 6, top - 8, c.left_name, size=header_size, weight=700, fill=C["ink"], anchor="end")
                if c.right_name:
                    ex.text((a + b) / 2 + 6, top - 8, c.right_name, size=header_size, weight=700, fill=C["ink"])
        if isinstance(c, Heat):
            c._dom = _domain(c, rows)
        if c.header == "含义" and isinstance(c, Note) and not ex.body_lang:
            c.header = "So what"
        if c.header:
            hx = a if c.header_align == "start" else (b if c.header_align == "end" else (a + b) / 2)
            anchor = {"start": "start", "end": "end"}.get(c.header_align, "middle")
            base = top - 8 - (18 if (isinstance(c, scaled) and c.ticks and c.ticks_pos == "top") else 0)
            hl = str(c.header).split("\n")
            for i, hr in enumerate(hl[::-1]):   # McKinsey: every column head bold, ink
                ex.text(hx, base - i * 12.5, hr, size=header_size, weight=700, fill=C["ink"], anchor=anchor)
            if head_rules:   # one main-colour rule under each column head (gap between columns = column separation)
                ex.line(a, top - 3, b, top - 3, stroke=C["main"], width=1.4, tag="grid")
    for c in columns:
        if isinstance(c, Bar):
            c._run = 0.0
        if isinstance(c, Rank):
            c._mode = c.resolve([r for r in rows if not r.get("_style")])
        c._noted = False
    # ---- rows
    out_y, last_group = {}, {}
    row_label_col = next((c for c in columns if isinstance(c, Label) and c.level == 1), None)
    for i, r in enumerate(rows):
        ry = top + i * row_h
        cy = ry + row_h / 2
        muted = r.get("_style") == "muted"
        fo_table = True if focus is None else bool(focus(r))
        if zebra is True and i % 2 == 0:
            ex.rect(x0, ry, x1 - x0, row_h, "#F7F7F7", register=False)
        if focus is not None and fo_table and not muted and not any(isinstance(c_, (Heat, Status, Spark)) for c_ in columns):
            # the row the claim is about: a pale main-colour band (tables of filled cells mark it by dimming the rest)
            from ._palette import _mix as _mx
            bx1 = max(b_ for _, b_ in xs) + 4   # the band covers the columns, not the bracket / note margin beyond them
            bx0 = (xs[1][0] - 6) if fill1 else x0   # a filled first column carries its own focus colour
            ex.rect(bx0, ry + 1, min(x1, bx1) - bx0, row_h - 2, _mx(C["main"], "#FFFFFF", 0.9), register=False)
        for c, (a, b) in zip(columns, xs):
            fo = fo_table if c.focus is None else bool(c.focus(r))
            if isinstance(c, Label):
                v = str(_val(r, c.field) or "")
                gcy = cy
                if c.level == 0:
                    if last_group.get(id(c)) == v:
                        continue
                    last_group[id(c)] = v
                    if group_rules and i > 0:
                        ex.line(a, ry, x1, ry, stroke=C["context"], width=0.8, tag="grid")
                    n_in = 1
                    while i + n_in < len(rows) and str(_val(rows[i + n_in], c.field) or "") == v:
                        n_in += 1
                    if c.valign == "middle":
                        gcy = ry + n_in * row_h / 2
                if not v:
                    continue
                if getattr(c, "_fill", False) and c is columns[0]:
                    _label_block(ex, c, r, v, a, b, ry, row_h, muted, focus is not None and fo_table, focus is not None,
                                 tight_text)
                    continue
                lines = wrap(v, c.size, c.wrap_w or c.width + 4, c.weight >= 600)
                lh = c.size * 1.18
                yf = gcy + c.size * 0.36 - (len(lines) - 1) * lh / 2
                hx = a if c.align == "start" else (b if c.align == "end" else (a + b) / 2)
                for j, ln in enumerate(lines):
                    ex.text(hx, yf + j * lh, ln, size=c.size, weight=700 if r.get("_bold") else c.weight,
                            fill=(c.color(r) if callable(c.color) else c.color) or (C["sub"] if muted else C["text"]),
                            anchor={"start": "start", "end": "end"}.get(c.align, "middle"))
            elif isinstance(c, Text):
                s = c.fmt(r)
                if s in (None, ""):
                    continue
                col = c.color(r) if callable(c.color) else c.color
                if not fo:   # non-focus rows recede, but their words must stay readable (context grey is ~2:1)
                    col = C["sub"]
                bold = bool(r.get("_bold")) or c.weight >= 600
                lines_ = [str(s)]
                lh = c.size * (1.05 if tight_text else 1.2)
                if tw(str(s), c.size, bold) > (b - a) + 2:   # a phrase wider than its column wraps inside it
                    lines_ = wrap(str(s), c.size, b - a, bold)
                    if len(lines_) * lh > row_h - 2 + 0.5:
                        raise ValueError(f"row_table：Text 列 {c.header or ''!r} 的 '{str(s)[:16]}…' 在 {b - a:.0f} 宽的列里放不下"
                                         "——句子放 Note 列（自动换行、行高随文字），或加大该列 width=，或缩短成 ≤6 字的关键词")
                align = c.align if len(lines_) == 1 else "start"
                hx = a if align == "start" else (b if align == "end" else (a + b) / 2)
                y0_ = cy + c.size * 0.36 - (len(lines_) - 1) * lh / 2
                for j_, ln_ in enumerate(lines_):
                    ex.text(hx, y0_ + j_ * lh, ln_, size=c.size, weight=700 if r.get("_bold") else c.weight,
                            fill=col or (C["sub"] if muted else C["text"]),
                            anchor={"start": "start", "end": "end"}.get(align, "middle"))
            elif isinstance(c, Note):
                lay = c.layout(r)
                lh = c.size * 1.3
                yf = cy + c.size * 0.36 - (len(lay) - 1) * lh / 2
                tcol = (c.color(r) if callable(c.color) else c.color) or (C["sub"] if muted or not fo else C["text"])
                for j, (ln, k) in enumerate(lay):
                    spans = ([(ln[:k], 700, C["ink"] if fo else tcol)] if k else []) + \
                            ([(ln[k:], 400, tcol)] if ln[k:] else [])
                    ex.text(a, yf + j * lh, "", size=c.size, spans=spans)
            elif isinstance(c, Rank):
                p_, n_ = _val(r, c.prev_key), _val(r, c.now_key)
                if n_ is None:
                    continue
                s_, col = c.cell(p_, n_, C, bool(ex.body_lang))
                if not fo:
                    col = C["context"]
                hx = a if c.align == "start" else (b if c.align == "end" else (a + b) / 2)
                ex.text(hx, cy + c.size * 0.36, s_, size=c.size, weight=700 if s_[0] in "▲▼" else 400, fill=col,
                        anchor={"start": "start", "end": "end"}.get(c.align, "middle"))
            elif isinstance(c, Bar):
                _draw_bar(ex, c, r, a, b, cy, row_h, muted, fo, dim)
            elif isinstance(c, Scen):
                _draw_scen(ex, c, r, cy, row_h, muted, fo, dim)
            elif isinstance(c, Variance):
                _draw_variance(ex, c, r, cy, row_h, muted, fo, dim)
            elif isinstance(c, Dumbbell):
                _draw_dumbbell(ex, c, r, a, b, cy, row_h, fo, dim, zebra)
            elif isinstance(c, Range):
                lo, hi = _val(r, c.lo), _val(r, c.hi)
                if lo is None or hi is None:
                    ex.text(a + 4, cy + 4, "未披露" if ex.body_lang else "n/d", size=10, italic=not ex.body_lang, fill=C["sub"])
                    continue
                col = (c.color(r) if callable(c.color) else c.color) or C["main"]
                if muted:
                    col = C["context"]
                if not fo:
                    col = dim
                bh = min(row_h * c.bar_h, 18)
                if c.point is None:
                    ex.rect(c._sx(lo), cy - bh / 2, max(c._sx(hi) - c._sx(lo), 2), bh, col)
                else:
                    ex.line(c._sx(lo), cy, c._sx(hi), cy, stroke=col, width=1.6, tag="series", whole=True)
                    for e in (lo, hi):
                        ex.line(c._sx(e), cy - 4, c._sx(e), cy + 4, stroke=col, width=1.2, tag="grid")
                    pv = _val(r, c.point)
                    if pv is not None:
                        ex.rect(c._sx(pv) - 4.5, cy - 4.5, 9, 9, col)
                if c.labels == "values":
                    same = c.value_fmt(lo) == c.value_fmt(hi)   # degenerate range: show one value, not "17 (17–17)"
                    pv_ = _val(r, c.point) if c.point else None
                    lab = (c.value_fmt(lo) if same else
                           (c.value_fmt(pv_) + f" ({c.value_fmt(lo)}–{c.value_fmt(hi)})" if pv_ is not None
                            else f"{c.value_fmt(lo)}–{c.value_fmt(hi)}"))
                    ex.text(c._sx(hi) + 6, cy + 4, lab, size=10, fill=C["sub"])
            elif isinstance(c, Heat):
                v = _val(r, c.field)
                if v is None:
                    hh = min(row_h - 2, 34)
                    ex.rect(a + 1, cy - hh / 2, b - a - 2, hh, C["band"], register=False)
                    ex.text((a + b) / 2, cy + 4, "–", size=10.5, fill=C["sub"], anchor="middle")
                    continue
                d0, d1 = c._dom
                if c.mid is not None:
                    t = (v - c.mid) / (max(abs(d0 - c.mid), abs(d1 - c.mid)) or 1)
                    col = _mix("#F4F6F8", C["main"], 0.15 + 0.85 * min(abs(t), 1)) if t > 0 else (
                        _mix("#F4F6F8", C.get(c.below, c.below) if str(c.below).startswith("#") is False else c.below,
                             (0.2 if c.below == "context" else 0.12) + (0.8 if c.below == "context" else 0.7) * min(-t, 1))
                        if t < 0 else "#F4F6F8")
                else:
                    t = (v - d0) / ((d1 - d0) or 1)
                    col = _mix("#EEF1F8", C["main"], 0.12 + 0.88 * t)
                if not fo:
                    col = _mix("#FFFFFF", col, 0.35)
                hh = min(row_h - 2, 34)
                ex.rect(a + 1, cy - hh / 2, b - a - 2, hh, col, register=False)
                ex.occupy((a + 1, cy - hh / 2, b - 1, cy + hh / 2), "mark", "panel-bg")
                ex.text((a + b) / 2, cy + c.size * 0.36, c.fmt(v), size=c.size,
                        fill="#FFFFFF" if _luma(col) < 140 else C["ink"], anchor="middle")
            elif isinstance(c, Spark):
                ys = [v for v in (_val(r, c.field) or []) if v is not None]
                if len(ys) < 2:
                    continue
                lab = c.fmt(ys[-1]) if c.label else ""
                lw = tw(lab, c.size) + 6 if lab else 0
                if c.shared:
                    allv = [v for rr in rows for v in (_val(rr, c.field) or []) if v is not None]
                    lo_, hi_ = min(allv + [0]), max(allv)
                else:
                    lo_, hi_ = (min(ys), max(ys)) if c.kind == "line" else (min(ys + [0]), max(ys))
                span = (hi_ - lo_) or 1
                sh = min(row_h * 0.62, 30)
                ax_, bx_ = a + 2, b - lw - 4
                sx_ = lambda k: ax_ + k * (bx_ - ax_) / (len(ys) - 1 if c.kind == "line" else len(ys))
                sy_ = lambda v: cy + sh / 2 - (v - lo_) / span * sh
                col = (c.color(r) if callable(c.color) else c.color) or C["main"]
                if not fo:
                    col = C["context"]
                hi_col = C["accent"] if fo else C["context"]
                if c.kind == "line":
                    pts = [(sx_(k), sy_(v)) for k, v in enumerate(ys)]
                    for start, end in zip(pts, pts[1:]):
                        ex.line(*start, *end, stroke=col, width=1.4, tag="series", whole=True, register=False)
                    ex.circle(pts[-1][0], pts[-1][1], 2.8, hi_col, register=False)
                    ex.occupy((ax_, cy - sh / 2, bx_, cy + sh / 2), "mark", "panel-bg")
                    lx, ly = pts[-1][0] + 5, cy + c.size * 0.36
                else:
                    bw = (bx_ - ax_) / len(ys) * 0.68
                    for k, v in enumerate(ys):
                        x_ = sx_(k) + ((bx_ - ax_) / len(ys) - bw) / 2
                        y_ = sy_(max(v, 0))
                        ex.rect(x_, y_, bw, max(abs(sy_(v) - sy_(0)), 1), hi_col if k == len(ys) - 1 else col,
                                register=False)
                    ex.occupy((ax_, cy - sh / 2, bx_, cy + sh / 2), "mark", "panel-bg")
                    lx, ly = bx_ + 5, cy + c.size * 0.36
                if lab:
                    ex.text(lx, ly, lab, size=c.size, weight=700 if fo else 400, fill=C["ink"] if fo else C["sub"])
            elif isinstance(c, Status):
                v = _val(r, c.field)
                if v is None:
                    continue
                zh_ = ex.body_lang
                words = c.words or ({"green": "达标", "amber": "接近", "red": "未达标"} if zh_ else
                                    {"green": "Met", "amber": "Close", "red": "Missed"})
                miss = C.get("bad") or C["neg"]   # one hue for "off target": close = pale tint, missed = solid
                col = {"green": C["main"], "amber": _mix(miss, "#FFFFFF", 0.45), "red": miss}.get(v, C["context"])
                if v == "red" and not getattr(c, "_counted", False):   # a red light is the page's argument mark
                    ex.notes += 1
                    c._counted = True
                ex.circle(a + 7, cy, 5.5, col)
                ex.text(a + 17, cy + c.size * 0.36, words.get(v, str(v)), size=c.size, weight=700 if v == "red" else 400,
                        fill=col if v == "red" else C["text"])
            elif isinstance(c, Harvey):
                v = _val(r, c.field)
                cx_ = (a + b) / 2 if not c.label else a + c.r + 2
                if v is None:
                    ex.text(cx_, cy + 4, "–", size=10.5, fill=C["sub"], anchor="middle")
                    continue
                lo_, hi_ = c.scale
                if not (lo_ - 1e-9 <= v <= hi_ + 1e-9):
                    raise ValueError(f"Harvey('{c.field}'): 值 {v} 超出 scale={c.scale}——按数据范围传 scale（如 0–100 分传 scale=(0, 100)）")
                q = max(0, min(4, round((v - lo_) / ((hi_ - lo_) or 1) * 4)))
                col = C["main"] if fo else dim
                ex.circle(cx_, cy, c.r, "#FFFFFF", stroke=col, width=1.4)
                if q == 4:
                    ex.circle(cx_, cy, c.r, col, register=False)
                elif q > 0:
                    import math as _m
                    ang = q * 90
                    x2 = cx_ + c.r * _m.sin(_m.radians(ang))
                    y2 = cy - c.r * _m.cos(_m.radians(ang))
                    large = 1 if ang > 180 else 0
                    ex.path(f"M{cx_:.1f},{cy:.1f} L{cx_:.1f},{cy - c.r:.1f} A{c.r},{c.r} 0 {large} 1 {x2:.1f},{y2:.1f} Z",
                            fill=col, register=False)
                if c.label:
                    ex.text(cx_ + c.r + 6, cy + 4, c.label(r) if callable(c.label) else str(c.label), size=10.5,
                            fill=C["text"])
            elif isinstance(c, Box):
                mn, q1, md, q3, mx = (_val(r, f) for f in c.fields)
                if None in (mn, q1, md, q3, mx):
                    ex.text(a + 4, cy + 4, "未披露" if ex.body_lang else "n/d", size=10, italic=not ex.body_lang, fill=C["sub"])
                    continue
                col = (c.color(r) if callable(c.color) else c.color) or C["main"]
                if not fo:
                    col = dim
                bh = min(row_h * 0.5, 16)
                ex.line(c._sx(mn), cy, c._sx(q1), cy, stroke=C["context"], width=1, tag="series", whole=True)
                ex.line(c._sx(q3), cy, c._sx(mx), cy, stroke=C["context"], width=1, tag="series", whole=True)
                for e in (mn, mx):
                    ex.line(c._sx(e), cy - bh / 3, c._sx(e), cy + bh / 3, stroke=C["context"], width=1, tag="grid")
                ex.rect(c._sx(q1), cy - bh / 2, c._sx(q3) - c._sx(q1), bh, col)
                ex.line(c._sx(md), cy - bh / 2, c._sx(md), cy + bh / 2, stroke="#FFFFFF", width=2, tag="grid")
                if c.labels == "median" and fo:
                    ex.text(c._sx(mx) + 6, cy + 4, c.value_fmt(md), size=10, fill=C["sub"])
            elif isinstance(c, Diverge):
                lv, rv = _val(r, c.left), _val(r, c.right)
                bh = min(row_h * c.bar_h, 26)
                lc = c.left_color or C["main"]
                rc = c.right_color or C["accent"]
                if not fo:
                    lc = rc = dim
                mid = (a + b) / 2
                if lv is not None:
                    ex.rect(c._sl(lv), cy - bh / 2, mid - c._sl(lv), bh, lc)
                    ex.text(c._sl(lv) - 4, cy + 4, c.fmt(lv), size=10, anchor="end")
                if rv is not None:
                    ex.rect(mid, cy - bh / 2, c._sr(rv) - mid, bh, rc)
                    ex.text(c._sr(rv) + 4, cy + 4, c.fmt(rv), size=10)
        filled = focus is not None or any(isinstance(c_, (Heat, Status)) for c_ in columns)
        if rules and i < len(rows) - 1:   # hairline between rows: dashed (McKinsey "floating columns") on plain tables,
            lx = xs[1][0] if (len(xs) > 1 and isinstance(columns[0], Label) and (columns[0].level == 0 or fill1)) else x0
            ex.line(lx, ry + row_h, x1, ry + row_h, stroke="#BFBFBF" if not filled else "#D9D9D9", width=0.6,
                    dash=None if filled else "3,3", tag="grid")   # solid where cells are filled (a dash would cross them)
        elif rules:   # the table closes with a solid hairline
            ex.line(x0, ry + row_h, x1, ry + row_h, stroke="#BFBFBF", width=0.8, tag="grid")
        if row_label_col is not None:
            out_y[str(_val(r, row_label_col.field))] = cy
    # ---- total row
    if total:
        ry = body_bottom + 6
        cy = ry + row_h / 2
        for c, (a, b) in zip(columns, xs):
            if isinstance(c, Label) and c.level == 1:
                ex.text(b if c.align == "end" else a, cy + 4, "" if _val(total, c.field) is None else str(_val(total, c.field)),
                        size=c.size, weight=700,
                        fill=C["ink"], anchor="end" if c.align == "end" else "start")
            elif isinstance(c, Bar):
                v = _val(total, c.field)
                bh_ = min(row_h * c.bar_h, 26)
                if c.cumulative and v is not None:   # running total vs the full scale (e.g. the gap): bar + remainder
                    xe = c._sx(min(v, c._dom[1]))
                    ex.rect(a, cy - bh_ / 2, b - a, bh_, C["track"], register=False)
                    ex.rect(a, cy - bh_ / 2, max(xe - a, 1.5), bh_, C["deep"], register=False)
                    rest = c._dom[1] - v
                    lab = c.fmt(v) + (f"（差 {fmt(rest)}）" if rest > 0.005 * c._dom[1] else "")
                    if xe - a > tw(lab, 11, True) + 12:
                        ex.text(xe - 5, cy + 4, lab, size=11, weight=700, fill="#FFFFFF", anchor="end", register=False)
                    else:
                        ex.text(a + 4, cy - bh_ / 2 - 4, lab, size=11, weight=700, fill=C["ink"], register=False)
                elif v is not None:
                    ex.rect(a, cy - bh_ / 2, b - a, bh_, C["deep"], register=False)
                    ex.text((a + b) / 2, cy + 4, c.fmt(v), size=11, fill="#FFFFFF", anchor="middle", register=False)
            elif isinstance(c, Scen):
                v = _val(total, c.ac)
                if v is not None:
                    ex.text(c._sx(0) + (4 if v >= 0 else -4), cy + 4, c.fmt(v), size=c.size, weight=700, fill=C["ink"],
                            anchor="start" if v >= 0 else "end")
            elif isinstance(c, Variance):
                v = c.value(total)
                if v is not None:
                    from ._ibcs import var_color
                    to = getattr(c, "text_only", False)
                    ex.text(c._tx if to else c._sx(0) + (5 if v >= 0 else -5), cy + 4, c.label(total, v), size=c.size,
                            weight=700, fill=var_color(ex, v, c.fav(total)),
                            anchor="end" if to else ("start" if v >= 0 else "end"))
            elif isinstance(c, Text):
                try:
                    s = c.fmt(total)
                except (KeyError, TypeError):
                    s = None
                if s and str(s).strip() not in ("None", "nan", "None%"):
                    hx = a if c.align == "start" else (b if c.align == "end" else (a + b) / 2)
                    ex.text(hx, cy + 4, s, size=c.size, weight=700,
                            anchor={"start": "start", "end": "end"}.get(c.align, "middle"))
    for i0, i1, text, ci in brackets:
        vbracket(ex, xs[ci][1] + 6, top + i0 * row_h + 4, top + (i1 + 1) * row_h - 4, text)
    if legend_items:
        ly = body_bottom + (6 + row_h if total else 0) + (22 if bottom_ticks else 0) + 20
        legend(ex, x0, min(ly, y1 - 4), legend_items, size=10.5)
    by_col = {}
    for c, span in zip(columns, xs):   # cols by header / field too: index arithmetic picked the wrong column
        for k in (getattr(c, "header", None), getattr(c, "field", None) if isinstance(getattr(c, "field", None), str) else None):
            if k and k not in by_col:
                by_col[k] = span
    _record_facts(ex, rows, columns)
    return {"y": out_y, "cols": xs, "col": by_col, "row_h": row_h, "top": top, "bottom": body_bottom}


LABEL_PAD = 8   # text inset inside a filled first-column block


def _label_colors(C):
    """(normal, focus, muted) block colours for a filled first column — all carry white text at ≥ 4.5:1 and stay in
    the palette: main (deep when main is light), the accent darkened until it reads, and the palette's grey."""
    from ._palette import contrast, _mix as _mx
    base = C["main"] if contrast(C["main"]) >= 4.5 else C["deep"]
    if contrast(base) < 4.5:   # dark-page palettes: main and ink are light — darken the main until white reads
        base = C["main"]
        for _ in range(30):
            if contrast(base) >= 4.5:
                break
            base = _mx(base, "#000000", 0.06)
    acc = C["accent"]
    for _ in range(20):
        if contrast(acc) >= 4.5:
            break
        acc = _mx(acc, "#000000", 0.06)
    if abs(contrast(acc) - contrast(base)) < 2:   # accent ≈ main: focus = the deep ink instead
        acc = C["deep"] if contrast(C["deep"]) > contrast(base) + 2 else _mx(base, "#000000", 0.45)
    if contrast(acc) < 4.5:
        acc = _mx(base, "#000000", 0.45)
    return base, acc, C["sub"]


def _light_block(C):
    """Pale tint of the palette main for the 'light' first column (dark text reads at ≥ 7:1 on it)."""
    from ._palette import _mix as _mx
    return _mx(C["main"], "#FFFFFF", 0.86)


def _label_block(ex, c, r, v, a, b, ry, row_h, muted, is_focus, has_focus, tight):
    """One filled first-column cell: solid block with 3px white gap above / below, white bold text inset, ≤3 lines."""
    C = ex.C
    base, acc, grey = _label_colors(C)
    col = grey if muted else (acc if is_focus else base)
    ink = "#FFFFFF"
    if getattr(c, "_light", False):   # pale tint of the main colour, dark bold text; focus row keeps the solid accent
        light = _light_block(C)
        col, ink = (acc, "#FFFFFF") if is_focus else (light, C["sub"] if muted else C["deep"])
    ex.rect(a, ry + 3, b - a, row_h - 6, col, register=False)
    ex.occupy((a, ry + 3, b, ry + row_h - 3), "mark", "panel-bg")
    pad = getattr(c, "_pad", LABEL_PAD)
    lines = wrap(v, c.size, (b - a - 2 * pad) / 1.08, True)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:-1] + "…"
    lh = c.size * (1.05 if tight else 1.18)
    cy = ry + row_h / 2
    yf = cy + c.size * 0.36 - (len(lines) - 1) * lh / 2
    for j, ln in enumerate(lines):
        ex.text(a + pad, yf + j * lh, ln, size=c.size, weight=700, fill=ink, anchor="start")


def _draw_bar(ex, c, r, a, b, cy, row_h, muted, fo, dim):
    C = ex.C
    v = _val(r, c.field)
    bh = min(row_h * c.bar_h, 26)
    from ._layouts import PROFILE as _PRO
    if c.track and not (c.track is True and _PRO.get("research")):   # research: a grey rail reads as an undefined capacity
        ex.rect(a, cy - bh / 2, b - a, bh, C["track"], register=False)
    if v is None:
        ex.text(a + 4, cy + 4, "未披露" if ex.body_lang else "n/d", size=10, italic=not ex.body_lang, fill=C["sub"])
        return
    col = (c.color(r) if callable(c.color) else c.color) or C["main"]
    if muted:
        col = C["context"]
    if not fo:
        col = dim
    if c.cumulative:
        x_a, x_b = c._sx(c._run), c._sx(c._run + v)
        c._run += v
    else:
        x_a, x_b = sorted((c._sx(0 if c._dom[0] <= 0 <= c._dom[1] else c._dom[0]), c._sx(min(v, c._dom[1]))))
    ex.rect(x_a, cy - bh / 2, max(x_b - x_a, 1.5), bh, col, register=False)
    if getattr(c, "_broken", False) and v > c._dom[1]:   # broken outlier bar: a white double slash across its end
        bx = x_b - 14
        for dx in (0, 5):
            ex.line(bx + dx - 3, cy + bh / 2 + 2, bx + dx + 3, cy - bh / 2 - 2, stroke="#FFFFFF", width=2.2, tag="grid")
    ex.occupy((x_a, cy - bh / 2, x_a + max(x_b - x_a, 1.5), cy + bh / 2), "mark", "bar")
    txt = c.fmt(v)
    if v < 0 and not any(ch in txt for ch in "-−–("):
        txt = "−" + txt  # a custom fmt that drops the sign must not turn a loss into a gain
    w_ = tw(txt, c.size)
    pos = c.value_pos
    if pos == "auto":
        if (x_b - x_a) > w_ + 14:
            pos = "inside_end"
        elif c.cumulative and x_a - a > w_ + 8:
            pos = "before"
        elif b - x_b > w_ + 8:
            pos = "end"
        else:
            pos = "before"
    if pos == "inside_end":
        ex.text(x_b - 5, cy + c.size * 0.36, txt, size=c.size, fill="#FFFFFF" if _luma(col) < 150 else C["ink"],
                anchor="end")
    elif pos == "end":
        ex.text(x_b + 5, cy + c.size * 0.36, txt, size=c.size)
    elif pos == "before":
        ex.text(x_a - 5, cy + c.size * 0.36, txt, size=c.size, anchor="end")


def _draw_scen(ex, c, r, cy, row_h, muted, fo, dim):
    """Reference bar behind, shifted up by `off`; AC bar in front, shifted down (IBCS overlapped bars)."""
    from ._ibcs import scen_bar
    C = ex.C
    v = _val(r, c.ac)
    rv = _val(r, c.ref) if c.ref is not None else None
    bh = min(row_h * c.bar_h, 18)
    off = bh * 0.34 if rv is not None else 0
    col = (c.color(r) if callable(c.color) else c.color) or C["main"]
    if muted:
        col = C["context"]
    elif not fo:   # de-focused rows keep the AC notation (solid), never a pale tone that reads as PY:
        col = C.get("ac_dim", col) if (c.ref_kind == "PY" and rv is not None) else _mix("#FFFFFF", col, 0.55)
    z = c._sx(0)
    if rv is not None:
        rcol = None if c.ref_kind == "PY" else col
        scen_bar(ex, min(z, c._sx(rv)), cy - bh / 2 - off / 2, max(abs(c._sx(rv) - z), 1.2), bh, c.ref_kind,
                 color=rcol)
    if v is None:
        ex.text(z + 4, cy + 4, "未披露" if ex.body_lang else "n/d", size=10, italic=not ex.body_lang, fill=C["sub"])
        return
    scen_bar(ex, min(z, c._sx(v)), cy - bh / 2 + off / 2, max(abs(c._sx(v) - z), 1.2), bh, c.scen, color=col)
    ends = [c._sx(v)] + ([c._sx(rv)] if rv is not None else [])
    end = max(ends) if v >= 0 else min(ends)
    ex.text(end + (5 if v >= 0 else -5), cy + c.size * 0.36, c.fmt(v), size=c.size,
            weight=700 if r.get("_bold") else 400, fill=C["ink"] if fo else C["sub"],
            anchor="start" if v >= 0 else "end")


def _draw_variance(ex, c, r, cy, row_h, muted, fo, dim):
    from ._ibcs import var_color
    C = ex.C
    v = c.value(r)
    if v is None:
        return
    col = var_color(ex, v, c.fav(r))
    if muted:
        col = C["context"]
    elif not fo:   # IBCS: a variance keeps its good/bad meaning even on de-focused rows — only paler
        col = _mix("#FFFFFF", col, 0.45)
    if getattr(c, "text_only", False):   # mixed units: coloured number, no bar on a shared scale
        ex.text(c._tx, cy + c.size * 0.36, c.label(r, v), size=c.size, weight=700 if r.get("_bold") else 400,
                fill=col, anchor="end")
        return
    z, xv = c._sx(0), c._sx(v)
    if c.pct:
        ex.line(z, cy, xv, cy, stroke=col, width=1.6, tag="series", whole=True)
        ex.circle(xv, cy, 3.4, col)
        tx = xv + (7.4 if v >= 0 else -7.4)
    else:
        bh = min(row_h * 0.46, 16)
        ex.rect(min(z, xv), cy - bh / 2, max(abs(xv - z), 1.2), bh, col)
        tx = xv + (4 if v >= 0 else -4)
    ex.text(tx, cy + c.size * 0.36, c.label(r, v), size=c.size, weight=700 if r.get("_bold") else 400,
            fill=C["text"] if fo else C["sub"], anchor="start" if v >= 0 else "end")


DIFF_NOTE = "差值"


def _dumbbell_to_diff(ex, c, rows, a, b):
    """Every row's two points closer than 2 × the point diameter (e.g. 128 → 96 on a 0–1000 axis): the
    dumbbell cannot show the change, so the column draws a signed difference bar from 0 (variance style, label at the
    bar end) beside named comparator values. Missing endpoints retain their available comparator, without a delta."""
    c._diff = False
    if hasattr(c, "_diff_original_header"):
        c.header = c._diff_original_header
    if len(c.series) < 2:
        return False
    f0, f1 = c.series[0][0], c.series[-1][0]
    pairs = [(v0, v1) for r in rows if not r.get("_style")
             for v0, v1 in [(_val(r, f0), _val(r, f1))] if isinstance(v0, (int, float)) and isinstance(v1, (int, float))]
    if not pairs or any(abs(c._sx(v1) - c._sx(v0)) >= 4 * c.r for v0, v1 in pairs):
        return False
    ds = [c.delta_of(v0, v1) for v0, v1 in pairs]
    m = max(abs(d) for d in ds) or 1.0
    lab_w = max(tw(c.delta_text(d, zh=bool(ex.body_lang)), 10, True) for d in ds) + 6
    comparison_slots = []
    cursor = a
    for field, name, color, style in c.series:
        value_width = max(tw(_comparison_text(c, r, field, name), 11) for r in rows) + 12
        comparison_slots.append((cursor, field, name, color))
        cursor += value_width
    neg, pos = any(d < 0 for d in ds), any(d > 0 for d in ds)
    aa = cursor + (lab_w if neg else 2)
    bb = b - (lab_w if pos or not neg else 2)
    if bb - aa < 40:
        raise ValueError("Dumbbell 差值布局放不下比较两期的数值和差异条：加宽该列或 Exhibit(w=)，"
                         "或改用 Text 列分别列出比较值；不能省略比较值")
    lo, hi = (-m if neg else 0.0), (m if pos or not neg else 0.0)
    c._dom = (lo, hi)
    c._sx = (lambda a_, b_, d: (lambda v: a_ + (v - d[0]) / ((d[1] - d[0]) or 1) * (b_ - a_)))(aa, bb, c._dom)
    c._diff_original_ticks = c.ticks
    c._diff, c.ticks, c._comparison_slots = True, None, comparison_slots
    c._diff_original_header = c.header
    difference_note = DIFF_NOTE if ex.body_lang else "Difference"
    if difference_note not in str(c.header or ""):
        c.header = (f"{c.header}（{difference_note}）" if ex.body_lang else f"{c.header} ({difference_note})") \
            if c.header else difference_note
    if getattr(ex, "extra_issues", None):
        ex.extra_issues = [i for i in ex.extra_issues if not str(i).startswith(INVISIBLE_DUMBBELL)]
    return True


def _comparison_text(column, row, field, name):
    value = _val(row, field)
    return f"{name} {column.value_fmt(value) if value is not None else '—'}"


def _draw_diff(ex, c, r, cy, row_h, fo, dim):
    for position, field, name, color in c._comparison_slots:
        ex.text(position, cy + 3.96, _comparison_text(c, r, field, name), size=11,
                fill=ex.C["text"] if fo else ex.C["sub"])
    v0, v1 = _val(r, c.series[0][0]), _val(r, c.series[-1][0])
    if v0 is None or v1 is None:
        return
    if not getattr(c, "_noted", False):
        ex.notes += 1
        c._noted = True
    d = c.delta_of(v0, v1)
    x0_, x1_ = sorted((c._sx(0), c._sx(d)))
    h = min(row_h, 44) * 0.42
    col = c.series[-1][2] if fo else dim
    if x1_ - x0_ >= 0.5:
        ex.rect(x0_, cy - h / 2, x1_ - x0_, h, col)
    lab = c.delta_text(d, zh=bool(ex.body_lang))
    if d < 0:
        ex.text(x0_ - 4, cy + 3.6, lab, size=10, weight=700, fill=ex.C["ink"], anchor="end")
    else:
        ex.text(x1_ + 4, cy + 3.6, lab, size=10, weight=700, fill=ex.C["ink"])


def _draw_dumbbell(ex, c, r, a, b, cy, row_h, fo, dim, zebra):
    C = ex.C
    if getattr(c, "_diff", False):
        return _draw_diff(ex, c, r, cy, row_h, fo, dim)
    row_h = min(row_h, 44)  # tall rows keep a slim connector
    pts = [(_val(r, f), nm, colr, st) for f, nm, colr, st in c.series]
    vals = [p[0] for p in pts if p[0] is not None]
    if zebra == "track":
        ex.rect(a, cy - row_h * 0.34, b - a, row_h * 0.68, C["band"], register=False)
    if c.base and pts[0][0] is not None:
        ex.rect(c._sx(c._dom[0]), cy - row_h * 0.14, c._sx(pts[0][0]) - c._sx(c._dom[0]), row_h * 0.28,
                "#B3B3B3" if fo else C["track"], register=False)
        if len(vals) >= 2:
            ex.rect(c._sx(min(vals)), cy - row_h * 0.14, c._sx(max(vals)) - c._sx(min(vals)), row_h * 0.28, "#E9E9E9",
                    register=False)
    if len(vals) >= 2:
        conn = "#C8C8C8" if fo else C["track"]
        if c.connector == "bar":
            ex.rect(c._sx(min(vals)), cy - row_h * 0.17, c._sx(max(vals)) - c._sx(min(vals)), row_h * 0.34, conn,
                    register=False)
        else:
            x_s, x_e = c._sx(pts[0][0]), c._sx(pts[-1][0])
            if c.connector == "arrow" and c.delta_of(0, 1) < 0:   # series given as (今年, 去年): arrow base → current
                x_s, x_e = x_e, x_s
            dirn = 1 if x_e >= x_s else -1
            if c.connector == "arrow" and abs(x_e - x_s) > 2 * c.r + 6:
                ex.line(x_s + dirn * (c.r + 2), cy, x_e - dirn * (c.r + 3), cy, stroke=C["text"] if fo else conn, width=1,
                        marker="arr", tag="series", whole=True)
            else:
                ex.line(x_s, cy, x_e, cy, stroke=(pts[-1][2] if fo else conn), width=1.6, tag="series", whole=True)
    # series colours name the ends (国产 vs 外资, legend): a de-focused row keeps them and only fades
    keyed = len({str(colr).upper() for _, _, colr, _ in pts if colr}) >= 2
    from ._marks import FOCUS_FADE
    for v, nm, colr, st in pts:
        if v is None:
            continue
        pc = colr if (fo or keyed) else dim
        op = FOCUS_FADE if (keyed and not fo) else None
        if st == "ring":
            ex.circle(c._sx(v), cy, c.r - 0.7, "#FFFFFF", stroke=pc, width=1.5, opacity=op)
        elif st == "pale":
            ex.circle(c._sx(v), cy, c.r, pc, stroke=C["ink"] if fo else None, width=0.9, opacity=op)
        else:
            ex.circle(c._sx(v), cy, c.r, pc, opacity=op)
    if c.labels == "values":   # every row keeps its numbers, not only the focus row
        for v, nm, colr, st in pts:
            if v is not None:
                ex.text(c._sx(v), cy - c.r - 4, c.value_fmt(v), size=10, fill=colr if fo else C["sub"], anchor="middle")
    if c.delta and fo and pts[0][0] is not None and pts[-1][0] is not None:
        if not getattr(c, "_noted", False):
            ex.notes += 1
            c._noted = True
        d = c.delta_of(pts[0][0], pts[-1][0])
        lab = c.delta_text(d, zh=bool(ex.body_lang))
        w_ = tw(lab, 10, True)
        xa, xb = sorted((c._sx(pts[0][0]), c._sx(pts[-1][0])))
        if xb - xa >= w_ + 2 * c.r + 8:
            on_bar = c.connector == "bar" and row_h * 0.34 >= 11
            ex.text((xa + xb) / 2, cy + 3.6 if on_bar else cy - 4, lab, size=10, weight=700, fill=C["ink"],
                    anchor="middle")
        else:
            xm = max(c._sx(v) for v in vals)
            ex.text(xm + c.r + 5, cy + 3.6, lab, size=10, weight=700, fill=C["ink"])


def _delta_pad(c, rows, a, b, zh=True):
    """Right padding a Dumbbell needs so delta labels that fall right of a short dumbbell stay inside the column."""
    dom = _domain(c, rows)
    sx = lambda v: a + (v - dom[0]) / ((dom[1] - dom[0]) or 1) * (b - a)  # noqa: E731
    need = 0.0
    for r in rows:
        v0, v1 = _val(r, c.series[0][0]), _val(r, c.series[-1][0])
        if v0 is None or v1 is None:
            continue
        w_ = tw(c.delta_text(c.delta_of(v0, v1), zh=zh), 10, True)
        if abs(sx(v1) - sx(v0)) < w_ + 2 * c.r + 8:
            vm = max(_val(r, f) for f, *_ in c.series if _val(r, f) is not None)
            need = max(need, sx(vm) + c.r + 5 + w_ + 2 - b)
    return max(need, 0) * 1.25 + (8 if need > 0 else 0)


def score_options(options, criteria, scale=(1, 5), lang=None):
    """Score options from their raw numbers with stated rules, so every 1–5 cell and the weighted total are computed.

    options: [dict(label=..., <field>=value, ...)]; criteria: [(header, field, weight, rule)], weights sum to 1;
    rule = "high" (more is better) | "low" (less is better) → linear between the worst and best option, or
    a list of ascending cut points [c1, c2, c3, c4] → 1 below c1 … 5 at or above c4 (reverse with ("low", [..])).
    Values that are already scores on the scale (every value of the criterion within lo–hi, e.g. 1–5 judgements)
    are kept as given ("low" reflects them: hi + lo − v) — never stretched min–max, which would reorder the totals.
    Adds s_<field>, score (weighted, 2 dp) and rank to each option; returns (options sorted by score, footnote text).
    Ties keep the input order; an input "rank" that disagrees with the computed one is printed (rank_in keeps it).
    """
    lo, hi = scale
    from ._text import has_cjk
    zh = (lang == "zh") if lang else any(has_cjk(c[0]) for c in criteria)
    if abs(sum(c[2] for c in criteria) - 1) > 1e-6:
        raise ValueError("criteria weights must sum to 1")
    notes = []
    for head, field, w, rule in criteria:
        vals = [o[field] for o in options if o.get(field) is not None]
        rev = isinstance(rule, tuple) and rule[0] == "low"
        cuts = rule[1] if isinstance(rule, tuple) else rule
        on_scale = not isinstance(cuts, (list, tuple)) and bool(vals) and all(
            isinstance(v, (int, float)) and lo - 1e-9 <= v <= hi + 1e-9 for v in vals)
        for o in options:
            v = o.get(field)
            if v is None:
                o["s_" + field] = None
                continue
            if isinstance(cuts, (list, tuple)):
                k = sum(v >= c for c in cuts)
                s = lo + k if not rev else hi - k
            elif on_scale:   # already a score on the scale: as given (reflected for "low")
                s = v if cuts == "high" else hi + lo - v
            else:
                a, b = min(vals), max(vals)
                t = 0.5 if b == a else (v - a) / (b - a)
                s = lo + (hi - lo) * (t if cuts == "high" else 1 - t)
            o["s_" + field] = round(min(max(s, lo), hi), 1)
        cut_txt = f"{'≥' if not rev else '≤'}{'/'.join(str(c) for c in cuts)}" if isinstance(cuts, (list, tuple)) else ""
        if zh:
            notes.append(f"{head}（权重 {w:.0%}）：" + (f"{cut_txt} 依次 {'+1' if not rev else '−1'} 分" if cut_txt
                         else (f"{lo}–{hi} 分{'原样采用' if cuts == 'high' else '反向计分'}" if on_scale
                               else f"按{'高' if cuts == 'high' else '低'}者为优线性映射到 {lo}–{hi}")))
        else:
            notes.append(f"{head} ({w:.0%}): " + (f"{cut_txt} steps {'+1' if not rev else '−1'}" if cut_txt
                         else (f"{lo}–{hi} score {'as given' if cuts == 'high' else 'reversed'}" if on_scale
                               else f"{'higher' if cuts == 'high' else 'lower'} is better, scaled {lo}–{hi}")))
    for o in options:  # computed from the displayed (1-dp) cell values so readers can re-add the table
        o["score"] = round(sum((o["s_" + f] or 0) * w for _, f, w, _ in criteria), 1)
    ranked = sorted(options, key=lambda o: -o["score"])   # stable: ties keep the input order
    moved = []
    for i, o in enumerate(ranked, 1):
        if "rank" in o and "rank_in" not in o:
            o["rank_in"] = o["rank"]
        if o.get("rank_in") is not None and o["rank_in"] != i:
            moved.append(f"{o.get('label', o.get('name', i))}: {o['rank_in']}→{i}")
        o["rank"] = i
    if moved:
        print("score_options：按加权总分算出的名次与输入的 rank 不一致（" + "；".join(str(m) for m in moved[:5])
              + "）——标题/要点/推荐标记按返回的 rank 写，或核对权重与分数")
    if len(ranked) >= 2 and ranked[0]["score"] == ranked[1]["score"]:
        print(f"score_options：第 1、2 名总分相同（{ranked[0]['score']}），按输入顺序排前——不要写'领先'，"
              "或调整权重/分数拉开差距")
    return ranked, ("评分规则：" + "；".join(notes)) if zh else ("Scoring: " + "; ".join(notes))


def top_n(rows, key, n=6, other=None, keep=None, sum_fields=None):
    """Dense data → the rows a page can carry: sort by `key` (desc), keep the first n (plus any row where keep(row) is
    true, e.g. "我方"), and fold the rest into one muted "其他（k 家）" / "Others (k)" row whose numeric fields are
    summed (sum_fields; default every numeric field present in all folded rows) and whose other fields are blank.
    Returns (rows, share_of_top) where share_of_top = sum of key over the kept top-n / total (for a bracket label)."""
    from ._text import has_cjk
    ranked = sorted(rows, key=lambda r: -(r.get(key) or 0))
    kept = ranked[:n] + [r for r in ranked[n:] if keep and keep(r)]
    rest = [r for r in ranked if r not in kept]
    total = sum(r.get(key) or 0 for r in rows) or 1
    share = sum(r.get(key) or 0 for r in ranked[:n]) / total
    if not rest:
        return kept, share
    zh = any(has_cjk(str(r.get("label", ""))) for r in rows)
    fields = sum_fields or [k for k in rest[0] if all(isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool)
                                                       for r in rest)]
    o = {k: None for k in rest[0]}
    o.update({k: sum(r[k] for r in rest) for k in fields})
    o["label"] = other or (f"其他（{len(rest)} 家）" if zh else f"Others ({len(rest)})")
    o["_style"] = "muted"
    return kept + [o], share
