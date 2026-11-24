"""Exhibit chart-area canvas: occupancy registry, automatic placement, self-check, atomized output."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from ._palette import roles
from ._text import fmt, has_cjk, tw, wrap  # noqa: F401

USED: set = set()     # exhibit functions called since the last publish (page scripts are one process per run)
SLID: list = []     # Exhibits placed with to_slide() since the last publish
BLOCKS: list = []   # boxed page blocks (kpi_strip / table_block …) built for the current frame()
LAYOUTS_USED: set = set()   # page-layout functions (columns_page, kpi_charts_page …) called by this page script
SIGNALS: list = []   # risk signals of the page being built (to_slide / publish); Frame.publish records + clears them
FACTS: list = []     # data the page's charts drew (bridge steps, status counts) — publish checks the title against it
TABLES: list = []    # (rows, cols) of tables drawn since the last publish — speech decks flag big ones


def _atomize_exhibit(svg_path):
    from ..atomize_svg_to_slide import atomize_svg_to_slide, convert_line, serialize_slide
    from ..atomize_svg_to_slide._config import _CFG
    from ..atomize_svg_to_slide._serialize import _parse

    source = ET.fromstring(Path(svg_path).read_text(encoding="utf-8"))
    whole = {element.get("id"): ET.tostring(element, encoding="unicode") for element in source.iter()
             if element.tag.rsplit("}", 1)[-1] == "line"
             and (element.get("id") or "").startswith("exhibit-series-")}
    diagnostics = {}
    fragment = atomize_svg_to_slide(svg_path, diagnostics=diagnostics)
    root = _parse(fragment)
    data = root.find("{https://www.larkoffice.com/sml/2.0}data")
    # Current SML requires a positive border width. An omitted zero-width
    # border preserves the appearance of the source SVG's unoutlined shapes.
    for shape in data.findall("{https://www.larkoffice.com/sml/2.0}shape"):
        for border in shape.findall("{https://www.larkoffice.com/sml/2.0}border"):
            if float(border.get("width", "1")) == 0:
                shape.remove(border)
    if not whole:
        return serialize_slide(root)
    outputs = {identifier: [] for identifier in whole}
    scope = "-".join(f"{_CFG[key]:g}" for key in ("slide_x0", "slide_y0", "slide_w", "slide_h"))
    for record in diagnostics["objects"]:
        identifiers = [identifier for identifier in record["source_ids"] if identifier in whole]
        if not identifiers:
            continue
        if (len(identifiers) != 1 or not record["outputs"] or record["decision"] != "native"
                or record["source_tag"] not in ("line", "path")):
            raise ValueError("A whole series interval must map to one independent native line")
        outputs[identifiers[0]].extend(output["index"] for output in record["outputs"])
    if any(not indices for indices in outputs.values()):
        raise ValueError("A whole series interval was lost during atomization")
    for identifier, indices in sorted(outputs.items(), key=lambda item: min(item[1]), reverse=True):
        if indices != list(range(min(indices), max(indices) + 1)):
            raise ValueError("A whole series interval must have an independent paint range")
        native = ET.fromstring(convert_line.__wrapped__(whole[identifier]))
        if native.tag != "line":
            raise ValueError("A whole series interval requires a solid-color native line")
        native.set("id", f"{identifier}-{scope}")
        data[min(indices):max(indices) + 1] = [native]
    return serialize_slide(root)


def chart_box(ex, box):
    """Inside `with ex.panel(…, claim=…) as b:` a chart drawn into the whole ex.body (or the panel box before its head)
    would run over the claim / unit lines: such a box is clipped to the panel's chart area b."""
    p = getattr(ex, "_panel", None) if ex is not None else None
    if p is None or not getattr(ex, "claims", None):
        return box
    try:
        x0, y0, x1, y1 = (float(v) for v in box)
    except (TypeError, ValueError):
        return box
    px0, py0, px1, py1 = p
    if y0 < py0 - 0.5 and x0 <= px0 + 1 and x1 >= px1 - 1:   # starts above the chart area of this panel
        return Box((max(x0, px0), py0, min(x1, px1), min(y1, py1)))
    return box


def check_box(box, where="box"):
    """Endpoint box (x0, y0, x1, y1): a width/height of 0 or less means (x, y, w, h) was passed — say so."""
    try:
        x0, y0, x1, y1 = (float(v) for v in box)
    except (TypeError, ValueError):
        raise ValueError(f"{where}：box 是 (x0, y0, x1, y1) 四个数（收到 {box!r}）") from None
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        raise ValueError(f"{where}：box 是 (x0, y0, x1, y1)，不是 (x, y, w, h)——收到 {tuple(box)!r}，宽 {x1 - x0:g}、"
                         f"高 {y1 - y0:g} ≤0。右下角写 (x0 + w, y0 + h)，或用 ex.body / ex.cols() / ex.split() 给的框")
    return box


def add_fact(ex, fact):
    """Record what a chart drew (FACTS for hand-passed fragments + ex.facts for f.publish(ex=…))."""
    FACTS.append(fact)
    if ex is not None:
        ex.__dict__.setdefault("facts", []).append(fact)


_PERIOD_RE = re.compile(r"^(?:(?:FY|CY)?'?(?:19|20)?\d{2}(?:[EFAPB]|年[EF]?|E年)?|.*?(?:Q[1-4]|[1-4]Q|H[12]|[12]H|W\d{1,2}|"
                        r"第?\d{1,2}周|\d{1,2}月|[一二三四]季度?).*)$", re.I)
_PERIOD_NAME_RE = re.compile(r"(?:19|20)\d{2}|FY\d|Q[1-4]|H[12]|去年|今年|上年|本年|同期|上期|本期|^PY$|^AC$", re.I)


APPENDIX_PAGE = False   # set by frame(): the page being built is an appendix page


def first_col_mode(mode, labels=None):
    """Table first-column style: 'plain' (bold ink text, no block — default: solid blocks in a column read like a bar
    chart that is not one) / 'fill' (dark block, white bold) / 'light' (pale main tint, dark bold), only when asked."""
    if mode in (None, "auto"):
        return "plain"
    return mode


def is_period(c):
    """A period label: 2024 / FY24 / 2026E / 24Q3 / H1 / W42 / 9月 / 三季度."""
    return bool(_PERIOD_RE.match(str(c).strip()))


def growth_items(names, firsts, lasts):
    """[(name, rate or None, delta)] from first / last values (rate None when the first value is ≤ 0)."""
    out = []
    for nm, a, b in zip(names, firsts, lasts):
        if a is None or b is None:
            continue
        out.append((str(nm), (b / a - 1) if a > 0 else None, b - a))
    return out

SANS = "思源黑体"  # same family as the page XML text, so chart and page read as one typeface
SERIF = "Georgia, 思源宋体, serif"
MIN_PT = 10  # atomize lifts smaller text to 10pt; author at >= 10 so layout matches the slide


_LINT_W = None


def lint_w(t, size, bold=False):
    """Glyph width the Slides server lint estimates for ``t`` (canvas units; the estimator is linear in size).
    It runs ~10% wider than the font metrics for digits / Latin, so a label that fits by ``tw`` can still be
    reported as touching its neighbour."""
    global _LINT_W
    if _LINT_W is None:
        try:
            import sys
            scripts = str(Path(__file__).resolve().parents[2])
            if scripts not in sys.path:
                sys.path.append(scripts)
            from _exhibit_xml_lint import estimate_text_width
            _LINT_W = estimate_text_width
        except Exception:  # noqa: BLE001
            _LINT_W = False
    est = _LINT_W(str(t), size, 0, bold) if _LINT_W else 0.0
    return max(est, tw(t, size, bold=bold))


def frame_w(t, size, bold=False):
    """Width of the native text frame atomize writes for a one-line label (canvas units): the server's
    text_overflows_container test uses this frame, not the glyphs."""
    return max(tw(t, size, bold=bold) + 0.5 * size, lint_w(t, size, bold) + 0.1 * size) + 2.0   # + real-font overhang


class _Cat(str):
    """A category label that also compares equal to its index (focus lambdas written as c == 1 or c == "2025")."""
    def __new__(cls, label, index):
        o = str.__new__(cls, label)
        o.index_ = index
        return o

    def __eq__(self, other):
        if isinstance(other, int) and not isinstance(other, bool):
            return self.index_ == other
        return str.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    __hash__ = str.__hash__


def check_panel_note(claim, note, where):
    """A panel's explanation under its claim says WHY / so-what, not the claim's numbers again (≤40 chars)."""
    n_ = str(note or "").strip()
    if len(re.sub(r"\s", "", n_)) > 44:
        raise ValueError(f"{where}：诠释 {len(n_)} 字（≤40）——只写判断句没说的原因或含义，细节放讲稿 note=")
    nums = lambda t: {x for x in re.findall(r"\d+(?:\.\d+)?", str(t)) if not (len(x) == 4 and x.startswith(("19", "20")))}   # noqa: E731
    dup = nums(n_) & nums(claim)
    if dup:
        raise ValueError(f"{where}：诠释重复了判断句里的数字 {sorted(dup)[:3]}——诠释写原因 / 含义（为什么会这样、对结论意味着什么），"
                         "不复述数字")


def _focus_parallel_hint(cats):
    """focus= on a chart whose page title names ≥ 3 of its categories: the page compares them side by side, so
    greying all but one misreads it. A printed hint only — the author decides."""
    import re as _re
    from . import _frame
    title = getattr(_frame, "LAST_TITLE", "") or ""
    named = [c for c in dict.fromkeys(cats)
             if not _re.fullmatch(r"[\d\s.,%’'QHEFY年月季度上下半-]+", c) and len(c) >= 2 and c in title]
    if len(named) >= 3:
        print(f"提示：标题同时点名了 {len(named)} 个类目（{'、'.join(named[:5])}），这页像是几个对象并列比较——"
              "并列比较不用 focus=（其余不置灰）；只有标题说的是'某一个 vs 其他'时才 focus 它")


def focus_fn(focus, categories):
    """focus= of columns / plain_bars as callable(category, series_name) -> bool: a callable passes through (one- or
    two-argument); an int is a category index, a str a category or series name, a tuple / list / set any of those."""
    if focus is None:
        return None
    cats = [str(c) for c in categories]
    _focus_parallel_hint(cats)
    if callable(focus):
        import inspect
        try:
            n = len([p for p in inspect.signature(focus).parameters.values()
                     if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        except (TypeError, ValueError):
            n = 2
        # a lambda written against the index (focus=lambda c, s: c == 1) gets a category that equals both its name
        # and its position, so either spelling picks the bar the author meant
        def _cat(c):
            k = cats.index(str(c)) if str(c) in cats else None
            return _Cat(str(c), k) if k is not None else c
        return (lambda c, s: focus(_cat(c))) if n == 1 else (lambda c, s: focus(_cat(c), s))
    keys = focus if isinstance(focus, (tuple, list, set, frozenset)) else (focus,)
    idx = {cats[k] for k in keys if isinstance(k, int) and not isinstance(k, bool) and -len(cats) <= k < len(cats)}
    names = {str(k) for k in keys if not isinstance(k, int) or isinstance(k, bool)}
    return lambda c, s: str(c) in idx or str(c) in names or (s is not None and str(s) in names)


KEYNOTE_SCALE = 2.0   # keynote decks: canvas fonts (≥ MIN_PT 10) land at ≥ 20pt on the slide (keynote font floor)


def _keynote_deck():
    """True when this task's deck is a business-keynote deck (.lark-slides/decks/<deck>/style == keynote): the deck of
    the last frame() / the live task, else every styled deck in the task folder is keynote."""
    try:
        from ._frame import _resolve_deck, _task_root, LAST_DECK
        from ..atomize_svg_to_slide._exhibit_publish import deck_dir
        root = _task_root(None)
        deck = _resolve_deck(None, None) or LAST_DECK[0]
        if deck:
            f = deck_dir(root, deck) / "style"
            return f.is_file() and f.read_text(encoding="utf-8").strip() == "keynote"
        styles = {p.read_text(encoding="utf-8").strip() for p in root.glob(".lark-slides/decks/*/style")}
        return styles == {"keynote"}
    except Exception:  # noqa: BLE001
        return False


def _box_text(x, y, t, size, anchor, weight, italic=False, serif=False):
    s = max(size, MIN_PT)
    w = tw(t, s, bold=weight >= 600, italic=italic, serif=serif)
    x0 = x - w if anchor == "end" else (x - w / 2 if anchor == "middle" else x)
    return (x0, y - s * 0.80, x0 + w, y + s * 0.22)


def _glyph_box(x, y, t, size, anchor, weight):
    """The box the server lint compares for text-vs-text / line-vs-text: its own width estimate, 1.2em tall,
    centred on the atomized frame (frame centre = baseline − 0.35em)."""
    s = max(size, MIN_PT)
    w = lint_w(t, s, weight >= 600)
    x0 = x - w if anchor == "end" else (x - w / 2 if anchor == "middle" else x)
    cy = y - 0.35 * s
    return (x0, cy - 0.5 * s, x0 + w, cy + 0.5 * s)


def _frame_box(x, y, t, size, anchor, weight):
    """The native text frame atomize writes (what text_overflows_container compares with the shape below)."""
    s = max(size, MIN_PT)
    w = frame_w(t, s, weight >= 600)
    x0 = x - w if anchor == "end" else (x - w / 2 if anchor == "middle" else x)
    cy = y - 0.35 * s
    return (x0, cy - 0.5 * s, x0 + w, cy + 0.5 * s)


def _straight_poly(d):
    """Vertices of an open path made only of absolute M/L/H/V commands (one subpath), else None."""
    toks = re.findall(r"[MLHVZmlhvzCcQqAaSsTt]|-?\d*\.?\d+(?:e-?\d+)?", str(d))
    pts, cmd, i = [], None, 0
    try:
        while i < len(toks):
            t = toks[i]
            if t.isalpha():
                if t not in "MLHV" or (t == "M" and pts):
                    return None
                cmd, i = t, i + 1
                continue
            if cmd in ("M", "L"):
                pts.append((float(toks[i]), float(toks[i + 1])))
                i += 2
                cmd = "L" if cmd == "M" else cmd
            elif cmd == "H":
                pts.append((float(t), pts[-1][1]))
                i += 1
            elif cmd == "V":
                pts.append((pts[-1][0], float(t)))
                i += 1
            else:
                return None
    except (IndexError, ValueError):
        return None
    return pts if len(pts) >= 2 else None


def _ov(a, b, pad=0.0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def _area(a, b):
    return max(min(a[2], b[2]) - max(a[0], b[0]), 0) * max(min(a[3], b[3]) - max(a[1], b[1]), 0)


def _inside(inner, outer, tol=1.0):
    return (inner[0] >= outer[0] - tol and inner[1] >= outer[1] - tol and inner[2] <= outer[2] + tol
            and inner[3] <= outer[3] + tol)


def _seg_hits_box(p, q, b, pad=1.0):
    x0, y0, x1, y1 = b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _circle_box_overlap(cx, cy, r, b):
    nx, ny = min(max(cx, b[0]), b[2]), min(max(cy, b[1]), b[3])
    return (nx - cx) ** 2 + (ny - cy) ** 2 < r * r


_SIGNS2 = re.compile(r"(?<![\w.])([+\u2212\-\u00b1])\s*[+\u2212\-\u00b1]+(?=\s*[\d.])")


def _one_sign(t):
    """"++28.4" / "−+25.1" (a caller's fmt that already signs, plus the library's sign) → one sign, the first."""
    s_ = str(t)
    return _SIGNS2.sub(r"\1", s_) if any(c in s_ for c in "+\u2212-\u00b1") else t


class _PanelCtx:
    def __init__(self, ex, box):
        self.ex, self.box, self.prev = ex, box, None

    def __enter__(self):
        self.prev, self.ex._panel = self.ex._panel, self.box
        return self.box

    def __exit__(self, *a):
        self.ex._panel = self.prev


class Box(tuple):
    """(x0, y0, x1, y1) that also reads as .x / .y / .w / .h (box.w = x1 − x0)."""
    x = property(lambda b: b[0])
    y = property(lambda b: b[1])
    w = property(lambda b: b[2] - b[0])
    h = property(lambda b: b[3] - b[1])


class _Roles(dict):
    """ex.C: colour roles; a common name that is not a role (grey, gray, red, green, primary…) maps to the nearest role."""
    _ALIAS = {"grey": "context", "gray": "context", "light_grey": "track", "lightgray": "track", "red": "neg",
              "negative": "neg", "green": "good", "positive": "good", "primary": "main", "secondary": "second",
              "highlight": "accent", "black": "ink", "muted": "dim", "pos": "good", "bad": "neg", "warn": "neg"}

    def __missing__(self, key):
        alt = self._ALIAS.get(str(key).lower())
        if alt and alt in self:
            return self[alt]
        if alt == "good" or str(key).lower() in ("good",):
            return self.get("accent")
        raise KeyError(f"ex.C 没有 {key!r}：可用 {sorted(self)[:16]}")


class Exhibit:
    """Chart-area canvas for one slide (only the chart: axes, marks, data labels, argument annotations).

    Title, subtitle, side text, KPI cards, footnotes, source and page number are written as native slide XML
    by the author; the exhibit is placed into the box that XML leaves free:

        ex = Exhibit(w=880, h=340, palette="mckinsey_blue")   # size of the box on the slide (slide px)
        ...draw in ex.body (canvas units; fonts are enlarged 1.25x on the slide)...
        frag = ex.to_slide(x=40, y=120)                         # top-left of the box on the slide
        publish_slide(page_xml, frag, presentation=deck, page=N, cwd=CWD)

    ex.C -> colour roles (main / accent / second / light / light2 / third / deep / context / dim / ink / text / sub /
            axis / grid / track / band). dark=True (or a palette whose bg is dark) -> light text / grid for a dark page (non-focus grey ≥ 3:1 on it).
            keynote deck (auto, or keynote=True): scale 2.0 so every in-chart label is ≥ 20pt. lang="zh"|"en" picks automatic labels (实绩/预测 vs Actual/Forecast).
    """

    def __init__(self, w=880, h=340, palette=None, lang=None, scale=1.25, font=None, dark=None, keynote=None,
                 deck=None, cwd=None):   # deck / cwd: accepted for symmetry with frame(); the palette comes from palette=
        # The canvas is drawn at (w/scale, h/scale) and enlarged by `scale` on the slide, so every in-chart font
        # (ticks, labels, values, notes) reads >= 12.5pt without hand-tuning sizes. Use ex.w / ex.h / ex.body for
        # coordinates inside the chart; never hard-code slide pixels.
        if not (isinstance(w, (int, float)) and isinstance(h, (int, float))) or w <= 0 or h <= 0:
            raise ValueError(f"Exhibit(w={w!r}, h={h!r})：宽高必须 >0——是框的尺寸（框宽 = x1 − x0、框高 = y1 − y0）；"
                             "子框 box 是 (x0, y0, x1, y1)")
        from ._layouts import SLOT_TITLES
        self._slot_title = SLOT_TITLES.get((round(w), round(h)), "")
        if scale < 1.2:  # smaller scale shrinks every in-chart font below the 12.5pt floor
            print(f"Exhibit: scale={scale} 会让图内文字小于 12.5pt，已改回 1.25；空间不够请加大 w/h 或删标签")
            scale = 1.25
        if keynote is None:
            keynote = _keynote_deck()
        if keynote and scale < KEYNOTE_SCALE:   # keynote: ticks / labels ≥ 20pt — draw fewer, bigger labels
            scale = KEYNOTE_SCALE
        self.slide_w, self.slide_h, self.scale = w, h, scale
        self.font = font or SANS  # pass the page XML fontFamily if it is not 思源黑体
        w, h = w / scale, h / scale
        self.w, self.h, self.m = w, h, 0
        self.el, self.reg, self.queue, self.panels = [], [], [], []
        self._series_count = 0
        self.fills = set()   # colours the chart actually paints (rect / circle / path fills): side-point marks must match one
        self._panel = None
        self._notes, self._note_at = 0, []   # argument annotations drawn (badge, diff arrows, ref lines, callouts…)
        self._auto = []  # plain charts that may become editable Feishu charts (see _autonative)
        from ._palette import set_default
        from . import _layouts as _ly
        if not palette or _ly.PROFILE.get("speech"):   # the deck's palette (set_palette); business-deck: always it
            from ._frame import deck_palette
            try:
                palette = deck_palette() or palette
            except Exception:  # noqa: BLE001 — no task folder / deck: keep the process default
                pass
        set_default(palette)
        self.C = _Roles(roles(palette, dark))   # dark page bg (dark=True, or a palette with dark bg): light text / grid
        if lang is None:   # follow the language of the last frame() title (English deck → Actual/Forecast labels)
            from . import _frame
            lang = _frame.LAST_LANG
        self.body_lang = "中" if lang == "zh" else ""
        self.body = Box((0, 0, w, h))

    @property
    def notes(self):
        return self._notes

    @notes.setter
    def notes(self, v):   # every annotation remembers where it was drawn (panel, element index) — see _autonative
        if v > self._notes:
            self._note_at.append((self._panel, len(self.el)))
        self._notes = v

    # ------------------------------------------------------------------ panels / registry
    def panel(self, box, claim=None, unit=None, note=None):
        """`with ex.panel(box) as b:` — labels queued inside stay inside `box`; check() flags text spilling out.
        claim="判断句", unit="指标，单位 · 期间": on a multi-chart page every panel gets one bold judgement (what this chart
        proves; the panels' claims read in order restate the page title) over a grey metric line and a rule; the box
        yielded by `with` is what is left below them — draw the chart in it.
        note="一两句诠释": optional ≤2 lines under the claim (the reason / implication the claim does not say — no
        repeated numbers); the chart keeps the rest of the height."""
        check_box(box, "ex.panel")
        if unit:   # per-panel unit: panels on different units (GWh vs US$) are independent metrics, not one story
            self.panel_units = list(getattr(self, "panel_units", None) or []) + [str(unit)]
        if claim:
            box = self._panel_head(box, claim, unit, note)
        elif note:
            raise ValueError("ex.panel(note=)：诠释写在判断句下面——先写 claim=")
        self.panels.append(tuple(box))
        return _PanelCtx(self, Box(box))

    def _panel_head(self, box, claim, unit, note=None):
        from ._text import wrap as _wrap
        x0, y0, x1, y1 = box
        C = self.C
        rows_ = _wrap(str(claim), 12, x1 - x0, bold=True)
        if len(rows_) > 2:
            raise ValueError(f"ex.panel(claim=)：判断句 {claim!r} 超过两行——缩到约 {int((x1 - x0) / 12 * 2)} 字，细节放图上标注")
        y = y0 + 11
        for ln in rows_:
            self.text(x0, y, ln, size=12, weight=700, fill=C["ink"])
            y += 15
        if note:
            check_panel_note(claim, note, "ex.panel(note=)")
            n_rows = _wrap(str(note), 10.5, x1 - x0)
            if len(n_rows) > 2:
                raise ValueError(f"ex.panel(note=)：诠释 {note!r} 超过两行——缩到约 {int((x1 - x0) / 10.5 * 2)} 字")
            for ln in n_rows:
                self.text(x0, y, ln, size=10.5, fill=C["text"])
                y += 13.5
        # fixed head height (claim 2 lines + note 2 lines when given): panels side by side start their charts level
        y = max(y, y0 + 11 + 30 + (27 + 2 if note else 0))
        if unit:
            self.text(x0, y + 1, str(unit), size=10, fill=C["sub"])
            y += 14
        self.line(x0, y - 4, x1, y - 4, stroke=C["ink"], width=0.8, tag="grid")
        self.claims = list(getattr(self, "claims", None) or []) + [str(claim)]
        return (x0, y + 4, x1, y1)

    def cols(self, n=2, gap=28, rows=1, vgap=24):
        """Split ex.body into an n-column (× rows) grid of equal panel boxes, in canvas units — use these instead of
        computing boxes from slide pixels (the canvas is the slide box ÷ scale)."""
        x0, y0, x1, y1 = self.body
        w, h = (x1 - x0 - gap * (n - 1)) / n, (y1 - y0 - vgap * (rows - 1)) / rows
        return [(x0 + c * (w + gap), y0 + r * (h + vgap), x0 + c * (w + gap) + w, y0 + r * (h + vgap) + h)
                for r in range(rows) for c in range(n)]

    def split(self, frac=0.32, gap=36, side="right"):
        """Split ex.body into (main, side) boxes."""
        x0, y0, x1, y1 = self.body
        sw = (x1 - x0) * frac
        if side == "right":
            return (x0, y0, x1 - sw - gap, y1), (x1 - sw, y0, x1, y1)
        return (x0 + sw + gap, y0, x1, y1), (x0, y0, x0 + sw, y1)

    def _add(self, kind, box, tag, circle=None, **extra):
        self.reg.append(dict(kind=kind, box=box, tag=tag, panel=self._panel, circle=circle, z=len(self.el), **extra))

    def occupy(self, box, kind="mark", tag="manual"):
        """Reserve an area (e.g. a hand-drawn shape) so auto-placement avoids it."""
        self._add(kind, box, tag)

    # ------------------------------------------------------------------ primitives (all registered)
    _FILL_RE = re.compile(r'<(?:rect|circle|ellipse|path|polygon)\b[^>]*?\bfill="([^"]+)"([^>]*)')

    def add(self, s):
        if s[:1] == "<" and '="' in s:   # fill="neg" / stroke="accent": a palette role name typed as the colour
            s = re.sub(r'\b(fill|stroke)="([a-z][a-z0-9_]*)"',
                       lambda m: f'{m.group(1)}="{self.C[m.group(2)]}"' if m.group(2) in self.C
                       and str(self.C[m.group(2)]).startswith(("#", "rgb")) else m.group(0), s)
        self.el.append(s)
        if s[:1] == "<" and "fill=" in s:   # colours the reader sees on the chart (faint fills < 0.3 opacity excluded)
            for col, rest in self._FILL_RE.findall(s):
                op = re.search(r'fill-opacity="([\d.]+)"', rest)
                if col != "none" and not col.startswith("url(") and (op is None or float(op.group(1)) >= 0.3):
                    self.fills.add(col)

    def text(self, x, y, t, size=11, fill=None, weight=400, anchor="start", italic=False, family=None, spans=None,
             register=True, color=None, bold=None):
        fill = fill or color
        weight = 700 if bold else weight
        """Single-line text at baseline y. spans=[(text, weight, color), ...] lays runs left→right; returns end x."""
        fill = fill or self.C["text"]
        family = family or self.font
        if spans is not None:
            cx = x
            for st, sw, sf in spans:
                lead = len(st) - len(st.lstrip(" "))
                cx += tw(" " * lead, size)
                core = st.strip(" ")
                if core:
                    self.text(cx, y, core, size=size, fill=sf or fill, weight=sw, italic=italic, family=family,
                              register=register)
                    cx += tw(core, size, bold=sw >= 600)
                cx += tw(" " * (len(st) - lead - len(core)), size) if core else 0
            return cx
        size = max(size, MIN_PT)
        t = _one_sign(t)
        if italic and has_cjk(str(t)):   # CJK fonts have no italic face: the renderer falls back to a script font
            italic = False
        style = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{fill}" text-anchor="{anchor}"{style}>{escape(str(t))}</text>')
        if register and str(t).strip():
            self._add("text", _box_text(x, y, str(t), size, anchor, weight, italic, family == SERIF), str(t),
                      frame=_frame_box(x, y, str(t), size, anchor, weight),
                      glyph=_glyph_box(x, y, str(t), size, anchor, weight), fill=fill)
        return x + tw(t, size, bold=weight >= 600)

    def lines(self, x, y, rows, size=11, lh=1.22, **kw):
        for i, r in enumerate(rows):
            self.text(x, y + i * size * lh, r, size=size, **kw)
        return y + len(rows) * size * lh

    def under(self, fn, *a, **k):
        """Draw with ``fn`` (self.rect / self.path …) but paint the result beneath everything drawn so far: shaded
        periods / zones are backgrounds — the server reports a fill painted AFTER a label as covering it, however
        transparent it looks. Element indices recorded by charts (autonative ranges) are shifted to match."""
        n0 = len(self.el)
        out = fn(*a, **k)
        new = self.el[n0:]
        if new:
            self.el = new + self.el[:n0]
            for c in getattr(self, "_auto", []):
                c["start"] += len(new)
                c["end"] += len(new)
            self._note_at = [(p, i + len(new)) for p, i in self._note_at]
        return out

    def rect(self, x, y, w, h, fill, register=True, stroke=None, stroke_width=None, opacity=None):
        fill = fill or self.C["main"]   # a missing colour must not make the mark invisible
        extra = (f' stroke="{stroke}" stroke-width="{stroke_width or 1}"' if stroke else "") + \
                (f' fill-opacity="{opacity}"' if opacity is not None else "")
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{fill}"{extra}/>')
        if register and w > 0 and h > 0:
            self._add("mark", (x, y, x + w, y + h), "rect", fill=fill, opacity=opacity)
        elif w > 8 and h > 8 and (opacity is None or float(opacity) >= 0.08):
            self._add("area", (x, y, x + w, y + h), "rect")   # unregistered background: still a server "container"

    def circle(self, cx, cy, r, fill, stroke=None, width=1, register=True, opacity=None):
        """opacity: a de-focused mark of a colour-keyed chart keeps its legend hue and only fades."""
        fill = fill or self.C["main"]
        s = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        if opacity is not None:
            s += f' fill-opacity="{opacity}"' + (f' stroke-opacity="{opacity}"' if stroke else "")
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{s}/>')
        if register:
            self._add("mark", (cx - r, cy - r, cx + r, cy + r), "circle", circle=(cx, cy, r), fill=fill)

    def line(self, x1, y1, x2=None, y2=None, stroke=None, width=1, dash=None, marker=None, marker_start=None, register=True,
             tag="line", whole=False, color=None):
        if isinstance(x1, (tuple, list)) and isinstance(y1, (tuple, list)):   # line((x1, y1), (x2, y2), ...)
            (x1, y1), (x2, y2) = x1, y1
        stroke = stroke or color
        # A diagonal native <line> is judged by the server through its bounding box (text_color_contrast samples
        # the paint under a label; a CAGR arrow's box covers every value label below it). A solid diagonal is drawn
        # as collinear pieces whose boxes stay within PIECE units of the line itself — it looks the same. All pieces
        # are one ex.el entry, so element indices (autonative chart ranges) do not move.
        dx, dy = x2 - x1, y2 - y1
        # whole=True (data series): one native line per interval, so the reader can select / edit it as one piece
        n = 1 if (dash or whole) else max(1, math.ceil(min(abs(dx), abs(dy)) / self.PIECE))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        cap = ' stroke-linecap="round"' if whole else ""   # joints between intervals stay closed
        identifier = ""
        if whole:
            self._series_count += 1
            identifier = f' id="exhibit-series-{self._series_count}"'
        # touching pieces with round caps show a faint joint every PIECE units on Feishu (anti-aliased cap ends meet
        # edge to edge): overlap neighbours by ~1.5 units with butt caps instead — renders as one continuous stroke
        ov = 1.5 / (math.hypot(dx, dy) or 1) if n > 1 else 0
        segs = [(max(0.0, k / n - ov), min(1.0, (k + 1) / n + ov)) for k in range(n)]
        if dash and not whole and min(abs(dx), abs(dy)) > self.PIECE:
            # a dashed diagonal becomes one custom shape whose bounding box the server takes for a text container:
            # draw every dash as its own short solid line instead
            pat = [float(v) for v in re.findall(r"[\d.]+", str(dash))] or [4.0, 3.0]
            pat = pat * (2 if len(pat) % 2 else 1)
            L, pos, k, segs = math.hypot(dx, dy), 0.0, 0, []
            while pos < L - 0.01:
                on = pat[k % len(pat)]
                if k % 2 == 0:
                    segs.append((pos / L, min(pos + on, L) / L))
                pos += on
                k += 1
            d = ""
            if marker and segs:
                segs[-1] = (segs[-1][0], 1.0)
        parts = []
        for k, (a, b) in enumerate(segs):
            m = (f' marker-end="url(#{marker})"' if marker and k == len(segs) - 1 else "") + \
                (f' marker-start="url(#{marker_start})"' if marker_start and k == 0 else "")
            parts.append(f'<line x1="{x1 + dx * a:.2f}" y1="{y1 + dy * a:.2f}" x2="{x1 + dx * b:.2f}" '
                         f'y2="{y1 + dy * b:.2f}" stroke="{stroke or self.C["axis"]}" stroke-width="{width}"{d}{m}{cap}{identifier}/>')
        self.add("".join(parts))
        if register:
            self._add("line", ((x1, y1), (x2, y2)), tag, stroke=stroke or self.C["axis"], width=width, whole=whole)

    PIECE = 6.0   # canvas units: max bounding-box thickness of one piece of a diagonal line

    _LINE_RE = re.compile(r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"([^>]*?)/>')

    def cut_lines(self, box=None, circle=None, pad=1.5):
        """Remove the part of every solid line already drawn that lies under ``box`` (x0, y0, x1, y1) or ``circle``
        (cx, cy, r) — the badge / oval / note drawn on top hides it anyway, but the server does not see occlusion and
        reads a line under the label as a line through the text. Returns the number of lines cut."""
        def inside(px, py):
            if circle is not None:
                return math.hypot(px - circle[0], py - circle[1]) < circle[2] + pad
            return box[0] - pad < px < box[2] + pad and box[1] - pad < py < box[3] + pad

        cut = 0

        def one(m):
            nonlocal cut
            x1, y1, x2, y2 = (float(v) for v in m.groups()[:4])
            rest = m.group(5)
            if "stroke-dasharray" in rest or ' id="exhibit-series-' in rest:
                return m.group(0)
            steps = max(2, int(math.hypot(x2 - x1, y2 - y1)))
            flags = [inside(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps) for i in range(steps + 1)]
            if not any(flags):
                return m.group(0)
            cut += 1
            out, start = [], None
            for i, f in enumerate(flags + [True]):
                if not f and start is None:
                    start = i
                elif f and start is not None:
                    if i - 1 - start >= 2:
                        a, b = start / steps, (i - 1) / steps
                        r_ = rest if b >= 1 else re.sub(r' marker-end="[^"]*"', "", rest)
                        r_ = r_ if a <= 0 else re.sub(r' marker-start="[^"]*"', "", r_)
                        out.append(f'<line x1="{x1 + (x2 - x1) * a:.2f}" y1="{y1 + (y2 - y1) * a:.2f}" '
                                   f'x2="{x1 + (x2 - x1) * b:.2f}" y2="{y1 + (y2 - y1) * b:.2f}"{r_}/>')
                    start = None
            return "".join(out)

        self.el = [self._LINE_RE.sub(one, e) if e.startswith("<line") else e for e in self.el]
        return cut

    def path(self, d, fill="none", stroke=None, width=1, marker=None, opacity=None, pts=None, register=True):
        """pts: optional vertices for registration (filled → bbox mark, stroked → segments)."""
        poly = _straight_poly(d) if (fill == "none" and stroke) else None
        if poly is not None:
            # An open stroked polyline atomizes to one custom shape: the server treats its bounding box as a filled
            # container (labels inside it "overflow" it, the box covers labels drawn before it). Native line pieces
            # look the same and are judged by their real geometry.
            el0 = len(self.el)
            for i, (p, q) in enumerate(zip(poly, poly[1:])):
                self.line(*p, *q, stroke=stroke, width=width, register=False,
                          marker=marker if i == len(poly) - 2 else None)
            self.el[el0:] = ["".join(self.el[el0:])]
            if register and pts:
                for p, q in zip(pts, pts[1:]):
                    self._add("line", (p, q), "path", stroke=stroke, width=width)
            return
        m = f' marker-end="url(#{marker})"' if marker else ""
        o = f' fill-opacity="{opacity}"' if opacity is not None else ""
        s = f' stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"' if stroke else ""
        self.add(f'<path d="{d}" fill="{fill}"{s}{m}{o}/>')
        if fill != "none" and (opacity is None or float(opacity) >= 0.08):
            v = [float(t) for t in re.findall(r"-?\d*\.?\d+", re.sub(r"[AaQqCc][^MLHVZmlhvz]*", " ", d))]
            if len(v) >= 4 and not (register and pts):
                xs, ys = v[0::2], v[1::2]
                if max(xs) - min(xs) > 8 and max(ys) - min(ys) > 8:
                    self._add("area", (min(xs), min(ys), max(xs), max(ys)), "path")
        if register and pts:
            if fill != "none":
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                self._add("mark", (min(xs), min(ys), max(xs), max(ys)), "path")
            else:
                for p, q in zip(pts, pts[1:]):
                    self._add("line", (p, q), "path", stroke=stroke, width=width)

    # ------------------------------------------------------------------ placement cost
    def cost(self, box, bounds=None, ignore_circle=None):
        b = bounds or self._panel or (0, 0, self.w, self.h)
        if not _inside(box, b, tol=0.5):
            return 1e6
        c = 0.0
        for e in self.reg:
            k = e["kind"]
            if k == "line":
                if e["tag"] == "grid":
                    continue
                if _seg_hits_box(e["box"][0], e["box"][1], box, pad=3):
                    # a label on a data line would cut the line (the server blocks a line through text)
                    c += 400 if e["tag"] in ("axis-arrow", "axis", "box") else (900 if e["tag"] == "series" else 120)
            elif e["circle"] is not None:
                if e["circle"] == ignore_circle:
                    continue
                cx, cy, r = e["circle"]
                if _circle_box_overlap(cx, cy, r + 2, box):
                    c += 3.0 * (_area(box, e["box"]) + 40)
            elif k == "area":   # a filled background the server reads as the label's container: in or out, not across
                if _ov(box, e["box"], pad=1) and not _inside(box, e["box"], tol=-3):
                    c += 150
            elif _ov(box, e["box"], pad=1.5):
                c += (6.0 if k == "text" else 3.0) * (_area(box, e["box"]) + 30)
        return c

    def _flush(self):
        while self.queue:
            q, self.queue = self.queue, []
            q.sort(key=lambda it: (-it["priority"], -it.get("r", 0)))
            for it in q:
                prev, self._panel = self._panel, it["panel"]
                it["fn"]()
                self._panel = prev

    # ------------------------------------------------------------------ self-check
    def check(self, verbose=True):
        """Text-on-text, text-on-mark, line-through-text, text outside its panel, anything off the canvas."""
        self._flush()
        issues = []
        texts = [e for e in self.reg if e["kind"] == "text" and e["tag"] not in ("axis-band",)]
        marks = [e for e in self.reg if e["kind"] == "mark" and e["tag"] not in ("band", "panel-bg", "manual", "legend")]
        lines = [e for e in self.reg if e["kind"] == "line" and e["tag"] not in ("leader", "grid")]
        for i, e in enumerate(texts):
            b, t = e["box"], e["tag"]
            if b[0] < 0 or b[2] > self.w or b[1] < 0 or b[3] > self.h:
                issues.append(f"出界: '{t[:24]}'")
            if e["panel"] is not None and not _inside(b, e["panel"], tol=2):
                issues.append(f"超出所在面板: '{t[:24]}'")
            for f in texts[i + 1:]:
                if _area(b, f["box"]) > 4 or (_ov(b, f["box"], pad=-0.5) and abs(b[1] - f["box"][1]) < 2
                                              and min(b[2], f["box"][2]) - max(b[0], f["box"][0]) > -2 and t != f["tag"]):
                    issues.append(f"文字重叠: '{t[:18]}' × '{f['tag'][:18]}'")
            for m in marks:
                if m["circle"] is not None:
                    cx, cy, r = m["circle"]
                    if _inside(b, (cx - r, cy - r, cx + r, cy + r), tol=0):
                        continue
                    if _circle_box_overlap(cx, cy, r - 1.5, b):
                        issues.append(f"文字压图形: '{t[:20]}' × 圆")
                        break
                else:
                    if _inside(b, m["box"], tol=1.0):
                        continue
                    if _area(b, m["box"]) > 0.2 * (b[2] - b[0]) * (b[3] - b[1]):
                        issues.append(f"文字压图形: '{t[:20]}' × 矩形")
                        break
            for ln in lines:
                if _seg_hits_box(ln["box"][0], ln["box"][1], b, pad=-1.5):
                    issues.append(f"线穿过文字: '{t[:20]}' ({ln['tag']})")
                    break
        for m in marks:
            b = m["box"]
            if b[0] < -1 or b[2] > self.w + 1 or b[1] < -1 or b[3] > self.h + 1:
                issues.append("图形出界")
        boxes = [e["box"] for e in self.reg if e["kind"] in ("text", "mark")]
        boxes += [(min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
                  for p, q in (e["box"] for e in self.reg if e["kind"] == "line")]
        if boxes:
            used_w = (max(b[2] for b in boxes) - min(b[0] for b in boxes)) / self.w
            used_h = (max(b[3] for b in boxes) - min(b[1] for b in boxes)) / self.h
            if used_w < 0.6 or used_h < 0.6:
                issues.append(f"图区留白：内容只占框宽 {used_w:.0%}、框高 {used_h:.0%}——缩小 Exhibit(w,h) 让 XML 补位，"
                              "或加大数据区（Axes/row_table 的 box 用满 ex.body）")
        issues += [s_ for s_ in (getattr(self, "extra_issues", None) or []) if s_ not in issues]   # e.g. bubbles overlap
        if verbose:
            print("check:", "OK" if not issues else f"{len(issues)} 个问题")
            for s in issues[:25]:
                print("  -", s)
        return issues

    # ------------------------------------------------------------------ output
    def tostring(self, background=False):
        self._flush()
        t = self.C["text"]
        defs = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto"><path d="M0,1 L9,5 L0,9 z" fill="{t}"/></marker>'
                '<marker id="arr_s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
                f'orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="{t}"/></marker></defs>')
        bg = (f'<rect width="{self.w}" height="{self.h}" fill="{self.C.get("page_bg") or "#FFFFFF"}"/>'
              if background else "")
        body = "".join(self.el)
        if self.C.get("page_bg"):   # dark page: white halos / ovals / separators take the page colour, text stays
            body = re.sub(r'<(?!text|tspan)[a-z]+\b[^>]*>', lambda m: re.sub(
                r'((?:fill|stroke)=")#FFFFFF"', r'\g<1>' + self.C["page_bg"] + '"', m.group(0), flags=re.I), body)
        if background:   # preview only: draw native hatches (data-sml-pattern) as SVG patterns in their colour
            cols = sorted(set(re.findall(r'fill="(#[0-9A-Fa-f]{6})"[^>]*data-sml-pattern=', body)))
            pats = "".join(f'<pattern id="h{c[1:]}" width="5" height="5" patternUnits="userSpaceOnUse" '
                           f'patternTransform="rotate(45)"><rect width="5" height="5" fill="#FFFFFF"/>'
                           f'<rect width="2.2" height="5" fill="{c}"/></pattern>' for c in cols)
            defs = defs.replace("</defs>", pats + "</defs>")
            body = re.sub(r'fill="#([0-9A-Fa-f]{6})"([^>]*data-sml-pattern=)', r'fill="url(#h\1)"\2', body)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">{bg}{defs}{body}</svg>')

    def save(self, path):
        """Write the SVG (after placement + check). Returns check issues."""
        self._flush()
        issues = self.check()
        Path(path).write_text(self.tostring(), encoding="utf-8")
        return issues

    def preview(self, path, width=None):
        """Render the chart area to PNG for one visual look (rsvg-convert / cairosvg / qlmanage, whichever exists).
        The whole page (with the XML title / footnotes) is seen in publish_slide's screenshot."""
        self._flush()
        out = Path(path)
        width = width or int(self.slide_w * 2)
        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "exhibit.svg"
            svg.write_text(self.tostring(background=True), encoding="utf-8")
            if shutil.which("rsvg-convert"):
                subprocess.run(["rsvg-convert", "-w", str(width), "-b", "white", str(svg), "-o", str(out)], check=True)
                return str(out)
            try:
                import cairosvg

                cairosvg.svg2png(url=str(svg), write_to=str(out), output_width=width, background_color="white")
                return str(out)
            except Exception:  # noqa: BLE001
                pass
            if shutil.which("qlmanage"):
                subprocess.run(["qlmanage", "-t", "-s", str(width), "-o", tmp, str(svg)], check=True, capture_output=True)
                shutil.move(str(Path(tmp) / "exhibit.svg.png"), out)
                return str(out)
        print("preview: 无可用渲染器；写入后用 publish_slide(..., screenshot=True) 看截图")
        return ""

    def to_slide(self, x=40, y=120, width=None, check=True):
        """Place labels, run check(), atomize into native Slides elements at slide box (x, y, w, h).

        width defaults to the canvas width (1:1, so font sizes are real pt). Pass the result to publish_slide
        together with the page XML that holds title / subtitle / text / footnotes / <note>.
        """
        width = width or self.slide_w
        self._at = (x, y)
        if self not in SLID:
            SLID.append(self)   # Frame.publish reads the num_dots / dot readings of charts passed as frags
        from ..atomize_svg_to_slide._config import _CFG

        self._slid = True
        self._flush()
        if check:
            issues = self.check()
            self._issues = issues
            if issues:
                SIGNALS.append(f"check {len(issues)} 个问题")
            tags = {e["tag"] for e in self.reg}
            if len(self.panels) >= 2 and not getattr(self, "related", False):
                SIGNALS.append("多图无关系")
                print("关系提醒：图区有 %d 个面板但没有画出它们之间的关系——左图一行/一根柱/一段在右图展开用 expand_panels + "
                      "expand，同一时间轴用 shared_time，同一组对象用 shared_rows，或 brace + takeaway 把两图合成一句结论；"
                      "确实是独立并列就忽略" % len(self.panels))
            if getattr(self, "sized_bubbles", False) and not getattr(self, "size_legend_drawn", False):
                raise ValueError("气泡大小不同却没有大小图例：size_legend(ex, x, y, [代表值…], ex.bubble_to_r, label_lines=['气泡=…，单位']) "
                                 "写明面积代表什么；"
                                 "没有第三个数值就不传 size=，画等大点")
            if getattr(self, "legend_needed", None) and not getattr(self, "legend_drawn", False):
                raise ValueError(f"{self.legend_needed[0]}区分了多个系列/类别却没有图例：legend(ex, x, y, [(名称, 颜色, 'dot'), …])"
                                 "，或改用直接标签（lines 的 end_labels=True、bubbles 的 groups=）")
            ghost = legend_ghosts(self)
            if ghost:
                raise ValueError(f"图例颜色在图上找不到：{'、'.join(f'{n}（{c}）' for n, c in ghost[:4])}——图例色块必须等于实际画出的"
                                 "柱/点/线颜色。focus= 只降低非焦点透明度或加粗焦点，不把按类别/系列着色的图形改成灰色；"
                                 "图例改用实际颜色，或去掉 focus=")
            annotated = bool(self.notes or tags & {"dim", "ref", "leader", "oval", "path"})
            SIGNALS.append("有标注图" if annotated else "图上无标注")   # page level: publish keeps "无标注" only if no chart has one
            if not annotated:
                print("注释提醒：图上还没有论证标注——标题里的倍数/增速/差距/阈值请画在图上（cagr_arrow、total_diff、"
                      "level_diff、badge、dim_arrow、ax.ref_y、band、callout、span_bracket、num_dot），数值由程序算。")
        keys = ("svg_w", "svg_h", "slide_x0", "slide_y0", "slide_w", "slide_h")
        saved = {k: _CFG[k] for k in keys}
        from . import _autonative
        from ._uncross import uncross

        def atomize(elements):
            el, self.el = self.el, elements
            try:
                _CFG.update(svg_w=self.w, svg_h=self.h, slide_x0=x, slide_y0=y, slide_w=width,
                            slide_h=width * self.h / self.w)
                with tempfile.TemporaryDirectory() as tmp:
                    p = Path(tmp) / "exhibit.svg"
                    p.write_text(self.tostring(), encoding="utf-8")
                    # the server blocks a native line crossing a native shape (gridline through a column, baseline
                    # along a bar's bottom edge, divider through a Gantt bar) although the SVG paints the bar over
                    # it: split / nudge those lines so what the server sees equals what the reader sees
                    return uncross(_atomize_exhibit(str(p)))
            finally:
                _CFG.update(saved)
                self.el = el
        frag = atomize(self.el)
        if check:
            srv = lint_fragment(self, frag, x, y, width / self.w)
            if srv:
                self._issues = list(self._issues) + srv
                self.server_issues = srv
                SIGNALS[:] = [s_ for s_ in SIGNALS if not s_.startswith("check ")] + [f"check {len(self._issues)} 个问题"]
                print(f"服务端规则预检：{len(srv)} 处会被写入时拦下（本地已按同一 lint 复算）")
                for s_ in srv[:12]:
                    print("  -", s_)
        n, plain, kept, natives = _autonative.analyse(self, x, y, width / self.w)
        if n:   # Frame.publish may swap in the variant where this exhibit's plain charts are native
            alt = frag
            if plain:
                alt = atomize(kept)
                alt = alt.replace("</data>", "".join(natives) + "</data>", 1) if "</data>" in alt else \
                    alt.replace("</slide>", "<data>" + "".join(natives) + "</data></slide>", 1)
            _autonative.ALT[frag] = dict(n=n, plain=plain, alt=alt)
        self._frag = frag   # Frame.publish(ex=ex, frags=[…]) adds it back when the author left it out of frags
        return frag


def legend_ghosts(ex):
    """[(legend label, colour)] for legend swatches whose colour no drawn mark carries (fill of a rect / circle /
    path, or the stroke of a series line): a legend must name the colours the reader sees."""
    items = getattr(ex, "legend_log", None) or []
    if not items:
        return []
    own = getattr(ex, "_legend_els", set())
    drawn = {str(e.get("fill")).upper() for e in ex.reg if e["kind"] == "mark" and e.get("fill")}
    drawn |= {str(e.get("stroke")).upper() for e in ex.reg if e["kind"] == "line" and e.get("stroke")}
    for s in ex.el:
        if s in own or s.startswith("<text"):
            continue
        drawn |= {m.upper() for m in re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{6})"', s)}
    return [(lab, col) for lab, col in items
            if isinstance(col, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", col) and col.upper() not in drawn]


# ---------------------------------------------------------------------- server-lint mirror
_KIND_ZH = {"grid": "网格线", "axis": "坐标轴", "series": "折线", "path": "连线", "dim": "CAGR/差值箭头",
            "ref": "参考线", "box": "虚线框", "leader": "引线", "callout": "callout 引线", "zero": "零线", "rect": "柱/色块",
            "speech": "说话框", "oval": "CAGR 椭圆", "badge": "徽章", "circle": "圆点", "line": "线"}


def _nearest(ex, kind, p, q=None, box=None):
    """Registry entry closest to a lint object (canvas coordinates)."""
    best = None
    for e in ex.reg:
        if e["kind"] != kind:
            continue
        if kind == "line":
            a, b = e["box"]
            d = min(math.dist(p, a) + math.dist(q, b), math.dist(p, b) + math.dist(q, a))
            # a line drawn in pieces / cut by an oval: the lint object is part of the registered segment
            for u in (p, q):
                t = _seg_dist(u, a, b)
                d = min(d, 2 * t + 0.0 if t < 1.5 and _seg_dist(p if u is q else q, a, b) < 1.5 else d)
        else:
            d = sum(abs(u - v) for u, v in zip(box, e["box"]))
        if best is None or d < best[0]:
            best = (d, e)
    return best[1] if best and best[0] < 12 else None


def _seg_dist(p, a, b):
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def lint_fragment(ex, frag, x0, y0, s):
    """Run the Slides server lint (local mirror: xml_lint + publish's own triage) on an exhibit fragment and
    return one line per finding the server would block, naming the chart element and the fix. Empty when the
    lint is unavailable. These are exactly the findings publish reports as "第 N 个片段…相压"."""
    try:
        import sys
        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.append(scripts)
        import _exhibit_xml_lint as xml_lint
        from ..atomize_svg_to_slide._exhibit_publish import _classify, _children, _describe
        res = xml_lint.lint_xml(frag)
        # page placement (out of canvas) depends on where the page puts the box; check() already flags labels
        # outside the canvas, and a fragment alone is never a blank page
        errs = [e for sl in res.get("slides", []) for e in sl.get("errors", [])
                if not str(e.get("code", "")).endswith("out_of_canvas") and e.get("code") != "blank_slide"]
        # publish's triage files line-vs-shape crossings inside generated output as conversion noise, but the server
        # blocks every one of them (bbox_overlap: line … crosses shape) — to_slide() removes them via uncross();
        # any that survive are reported here so the page is fixed before upload, not after 8 rejected writes
        crossed = [e for e in errs if "crosses shape" in str(e.get("message", ""))]
        # same for a line through a label's glyphs (server: line … crosses text): triage may file a light gridline
        # over generated text as noise, the server does not; to_slide() splits such lines, survivors are named here
        crossed_t = [e for e in errs if "crosses text" in str(e.get("message", ""))]
        if not errs:
            return []
        gen = set(range(len(_children(frag))))
        _, report = _classify(frag, gen, errs)
        items = [_describe(frag, e, gen, {i: "fragment[0]" for i in gen}) for e in report]
    except Exception:  # noqa: BLE001 — the mirror is a convenience; the server still decides
        return []

    def canvas(o):
        if o.get("xml_line"):
            a, b, c, d = o["xml_line"]
            return ("line", ((a - x0) / s, (b - y0) / s), ((c - x0) / s, (d - y0) / s))
        if o.get("xml_box"):
            a, b, w, h = o["xml_box"]
            return ("box", ((a - x0) / s, (b - y0) / s, (a + w - x0) / s, (b + h - y0) / s))
        return (None,)

    out = [f"服务端·线穿色块：{len(crossed)} 条原生线（网格线/基线/参考线/分隔线）穿过柱或色块——服务端会拦下；"
           "参考线/分隔线改到柱外侧，或 show_grid=False"] if crossed else []
    if crossed_t:
        kids = _children(frag)

        def _txt(path):
            m = re.search(r"shape\[(\d+)\]", str(path))
            shapes = [k for k in kids if k.tag.split("}")[-1] == "shape"]
            if m and int(m.group(1)) <= len(shapes):
                return " ".join("".join(shapes[int(m.group(1)) - 1].itertext()).split())[:20]
            return ""
        labs = list(dict.fromkeys(t for t in (_txt((e.get("elements") or ["", ""])[-1]) for e in crossed_t) if t))
        out.append(f"服务端·线穿文字：{len(crossed_t)} 条原生线穿过标签" + (f"（{'、'.join(labs[:4])}）" if labs else "")
                   + "——服务端会拦下；标签挪到线的一侧（prefer=/dy=），或删掉这个标签/这条参考线")
    for d in items:
        objs = d.get("objects") or []
        if "crosses text" in str(d.get("message", "")) and crossed_t:
            continue   # already named in the 线穿文字 line above
        texts = [o for o in objs if o.get("element", "").endswith('"text"]')]
        other = [o for o in objs if o not in texts]
        code = d.get("code")
        lab = "、".join(f"「{o.get('text', '')}」" for o in texts) or "文字"
        what = ""
        if other:
            c = canvas(other[0])
            e = (_nearest(ex, "line", c[1], c[2]) if c[0] == "line" else
                 _nearest(ex, "mark", None, box=c[1]) if c[0] == "box" else None)
            tag = (e or {}).get("tag") or ("line" if c[0] == "line" else "")
            what = _KIND_ZH.get(tag, "图形" if c[0] == "box" else "线")
        if code == "bbox_overlap" and len(texts) == 2:
            out.append(f"服务端·文字重叠：{lab} 两个标签按服务端字宽估算相压——删掉其中一个（或只留首尾值 values=False）、"
                       "减少类别，或加大 Exhibit 宽度")
        elif code == "bbox_overlap" and other and other[0].get("element") == "line":
            fix = {"CAGR/差值箭头": "CAGR/差值箭头压到柱顶数值：传 values=False 或只留首尾值（箭头保留）",
                   "折线": "折线穿过标签：callout/note 换方向（prefer=）或删掉这个标签",
                   "callout 引线": "引线穿过别的文字：callout 换方向（prefer=）、缩短文字，或删掉它",
                   "引线": "引线穿过别的文字：删掉这个标签或换位置",
                   "参考线": "参考线压到标签：参考线文字改短，或删掉被压的数值标签",
                   "坐标轴": "标签压在坐标轴上：标签放到轴外侧或删掉"}.get(what, f"{what}穿过标签：标签挪离这条线，或删掉标签")
            out.append(f"服务端·线压文字：{what} × {lab}——{fix}")
        elif code == "bbox_overlap":
            out.append(f"服务端·图形盖住文字：{what or '色块'}（后画）盖住 {lab}——"
                       + ("说话框/徽章换位置或缩短文字（note= 写短一点）" if what in ("说话框", "徽章", "CAGR 椭圆")
                          else "该标签放到色块外，或删掉这个标签"))
        elif code == "text_overflows_container":
            ov = d.get("overflow") or {}
            side = "、".join(f"{k} {v:.1f}px" for k, v in ov.items() if v)
            fix = ("柱内数值标签比这一段宽/高：values=False，或只给够高的段标数" if what == "柱/色块" else
                   "文字落在折线/形状的外接框里：标签换位置（prefer=）或删掉" if what in ("连线", "折线", "图形") else
                   f"文字超出{what}：放大该底框或缩短文字")
            out.append(f"服务端·文字超出底框：{lab} 超出 {what or '底框'}（{side}）——{fix}")
        elif code == "text_color_contrast":
            out.append(f"服务端·对比度：{lab} 与下方元素对比不足——标签挪离深色线/色块，或深色底上改白字")
        elif code and code.endswith("out_of_canvas"):
            out.append(f"服务端·出界：{lab if texts else what or '元素'} 超出页面——把图框放进 960×540 内（减小 x/y 或 Exhibit 宽高）")
        else:
            out.append(f"服务端·{code}：{d.get('fix') or d.get('message') or ''}"[:160])
    return list(dict.fromkeys(out))
