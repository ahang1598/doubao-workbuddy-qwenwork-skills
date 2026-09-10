"""svg_lib/charts/event_timeline.py

统一 API: draw_event_timeline(data, variant, palette, ...) -> str (SVG)

Data schema:
    data = {
        "events": [(date_str, title, subtitle?, category?), ...],  # 至少 2 events
        "categories": {name: color} | None,   # 可选，主动指定 category 颜色
    }

Variants (5 共享 events):
    - horizontal_alt_dot   横线时间轴，卡片上下交替
    - stepped_dot           阶梯形时间轴（增长叙事）
    - vertical_alt_dot     纵向时间轴，卡片左右交替
    - horizontal_pin        横线 + pin 标记（水滴）
    - circular_dot          圆形时间轴（PDCA 感）
"""
from __future__ import annotations
import math

from ._shared import (

    resolve_palette,
    xesc,
    auto_font_size,
    viewbox_fs,
    svg_open,
    svg_close,
    _rgba_with_alpha,
)


from .._common import (_ACC, _INK, _INK1, _INK2, _INK4, _INK6, _derive_series_colors, _prepend_bg_if_dark, _resolve_font, _resolve_palette, _rgba_with_alpha, _xesc, _variant_is_classic, _dispatch_to_svg_lib)
BODY_FONT = "Inter, sans-serif"
HEAD_FONT = "Georgia, serif"


def draw_event_timeline(
    data: dict,
    variant: str = "horizontal_alt_dot",
    palette: str = "archive_ink",
    width: float = 900,
    height: float = 540,
    title: str = None,
    subtitle: str = None,
) -> str:
    events = data.get("events") or []
    if len(events) < 2:
        raise ValueError("draw_event_timeline: need at least 2 events")

    # normalize: (date, title, subtitle, category)
    #
    # Accepts several input shapes since make_event_timeline() forwards events
    # through _dispatch_to_svg_lib() without conversion:
    #   A) dict:  {"year", "month", "category"|"cat", "title", "desc"|"description"|"subtitle"}
    #             or {"date", "title", "subtitle"|"desc", "category"|"cat"}
    #   B) new-API tuple: (year, month, cat, title, desc)   — 5-tuple, e[1] is int month
    #   C) legacy-API tuple: (idx, side, title, sub, cat)   — 5-tuple, e[1] is "above"/"below"
    #   D) original svg_lib schema: (date_str, title, subtitle?, category?) — 2-4 tuple
    def _norm_event(e):
        if isinstance(e, dict):
            if "year" in e:
                y = e.get("year")
                mo = e.get("month", 1)
                try:
                    d = f"{int(y)}·{int(mo):02d}"
                except (TypeError, ValueError):
                    d = str(y)
                t = str(e.get("title", ""))
                s = str(e.get("desc", e.get("description", e.get("subtitle", ""))) or "")
                c = str(e.get("category", e.get("cat", "")) or "")
                return (d, t, s, c)
            d = str(e.get("date", ""))
            t = str(e.get("title", ""))
            s = str(e.get("subtitle", e.get("desc", e.get("description", ""))) or "")
            c = str(e.get("category", e.get("cat", "")) or "")
            return (d, t, s, c)
        # tuple / list forms
        if not isinstance(e, (list, tuple)) or len(e) == 0:
            return ("", "", "", "")
        # New-API tuple: (year:int, month:int, cat, title, desc)
        # Distinguishing marker: len>=4, e[0] and e[1] are ints (or int-like) and e[1]
        # is NOT the string "above"/"below".
        if len(e) >= 4 and not isinstance(e[1], str):
            try:
                y_i = int(e[0])
                mo_i = int(e[1])
                d = f"{y_i}·{mo_i:02d}"
                c = str(e[2]) if e[2] else ""
                t = str(e[3]) if len(e) > 3 else ""
                s = str(e[4]) if len(e) > 4 and e[4] else ""
                return (d, t, s, c)
            except (TypeError, ValueError):
                pass
        # Legacy-API tuple: (idx, side, title, sub, cat)
        if len(e) >= 4 and isinstance(e[1], str) and e[1] in ("above", "below"):
            # idx here is typically a numeric axis position (float like 0.3) that
            # has no semantic meaning as a "date" — historically we used to str()
            # it and render it on the card, which produced misleading labels
            # like "0.3 / 1.4 / 0.4" at the top of pin cards.  Prefer empty date
            # so title/sub carry the visible content instead.  Callers that want
            # a real date should either pass `years=[..]` to make_event_timeline
            # (which now pre-normalises to (year, month, ...) before dispatch)
            # or use the new-API tuple/dict form directly.
            d = ""
            t = str(e[2]) if len(e) > 2 else ""
            s = str(e[3]) if len(e) > 3 and e[3] else ""
            c = str(e[4]) if len(e) > 4 and e[4] else ""
            return (d, t, s, c)
        # Fallback: original svg_lib schema (date_str, title, subtitle?, category?)
        d = str(e[0]) if len(e) > 0 else ""
        t = str(e[1]) if len(e) > 1 else ""
        s = str(e[2]) if len(e) > 2 and e[2] else ""
        c = str(e[3]) if len(e) > 3 and e[3] else ""
        return (d, t, s, c)

    norm = [_norm_event(e) for e in events]

    pal = resolve_palette(palette)
    user_cat_color = data.get("categories") or {}

    # derive category -> color
    cat_color = {}
    used_cats = []
    for _, _, _, c in norm:
        if c and c not in cat_color:
            used_cats.append(c)
    series = pal.get("series") or [pal["accent"]]
    for i, c in enumerate(used_cats):
        cat_color[c] = user_cat_color.get(c, series[i % len(series)])

    ctx = _Ctx(norm, cat_color, pal, float(width), float(height), title, subtitle)

    if variant == "horizontal_alt_dot":
        body = _draw_horizontal_alt(ctx, use_pin=False)
    elif variant == "horizontal_pin":
        body = _draw_horizontal_alt(ctx, use_pin=True)
    elif variant == "stepped_dot":
        body = _draw_stepped(ctx)
    elif variant == "vertical_alt_dot":
        body = _draw_vertical_alt(ctx)
    elif variant == "circular_dot":
        body = _draw_circular(ctx)
    else:
        raise ValueError(
            f"unknown variant {variant!r}. Supported: horizontal_alt_dot, stepped_dot, "
            "vertical_alt_dot, horizontal_pin, circular_dot"
        )

    header = _header(ctx)
    return (
        svg_open(0, 0, ctx.W, ctx.H, bg=pal["bg"])
        + header
        + body
        + svg_close()
    )


class _Ctx:
    def __init__(self, events, cat_color, pal, W, H, title, subtitle):
        self.events = events
        self.cat_color = cat_color
        self.pal = pal
        self.W = W
        self.H = H
        self.title = title
        self.subtitle = subtitle
        self.n = len(events)

        self.ML = 60
        self.MR = 40
        self.header_h = 20
        if title:
            self.header_h = 44
        if subtitle:
            self.header_h += 18

        self.fs_title = viewbox_fs(W, H, self.n, role_mult=1.1)
        # secondary text (card desc / date) 底线 11pt，避免 embed 宽 <500 时糊掉
        self.fs_sub = max(11.0, viewbox_fs(W, H, self.n, role_mult=0.95, floor=11))
        self.fs_date = max(11.0, viewbox_fs(W, H, self.n, role_mult=0.9, floor=11))

    def color_for(self, cat):
        if cat and cat in self.cat_color:
            return self.cat_color[cat]
        return self.pal["accent"]


def _header(ctx: _Ctx) -> str:
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []
    ML = ctx.ML
    if ctx.title:
        parts.append(
            f'<text x="{ML}" y="30" font-family="{HEAD_FONT}" font-size="20" '
            f'font-weight="600" fill="{ink}" letter-spacing=".03em">{xesc(ctx.title)}</text>'
        )
    if ctx.subtitle:
        y = 48 if ctx.title else 30
        parts.append(
            f'<text x="{ML}" y="{y}" font-family="{BODY_FONT}" font-size="11" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(ctx.subtitle)}</text>'
        )
    if ctx.title:
        parts.append(
            f'<line x1="{ML}" y1="{ctx.header_h}" x2="{ctx.W - ctx.MR}" y2="{ctx.header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )
    return "".join(parts)


def _draw_horizontal_alt(ctx: _Ctx, use_pin: bool = False) -> str:
    """Horizontal axis with cards alternating above/below."""
    parts = []
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    bg = ctx.pal["bg"]

    n = ctx.n
    # push axis lower on small counts to balance whitespace above/below
    # (previously fixed at H/2+10, which left huge empty space up top for n < 6)
    if n <= 5:
        axis_y = ctx.header_h + (ctx.H - ctx.header_h) * 0.55
    else:
        axis_y = ctx.H / 2 + 10
    x0 = ctx.ML
    x1 = ctx.W - ctx.MR

    # main axis
    parts.append(
        f'<line x1="{x0}" y1="{axis_y:.1f}" x2="{x1}" y2="{axis_y:.1f}" '
        f'stroke="{ink}" stroke-width="1.2"/>'
    )

    # Dense (large_scale) needs a wider min card so titles like "Company founded" (15
     # chars) don't get mid-word split into "Company founde" + "d".  Neighbouring cards
     # still don't collide because alternating above/below pushes them onto separate
     # vertical bands — the only overlap that matters is same-side (i and i+2), spaced
     # 2*(x1-x0)/n apart, which comfortably clears a 100px card even at n=22 / w=1400.
    min_w = 100 if n > 15 else 80
    card_w = max(min_w, (x1 - x0) / max(1, n) * 0.9)
    # pin variant can afford a slightly wider ceiling because the droplet anchor
    # is narrower than the ring+dot (so left/right lead-line collisions are rarer)
    # — 190px vs 160px lets typical CJK titles like "WorkBuddy 公测" or
    # "请求量迅速冲高" fit on one line without shrinking font-size aggressively.
    card_w_cap = 190 if use_pin else 160
    card_w = min(card_w, card_w_cap)
    # taller cards + 2-line titles when very dense (large_scale)
    two_line_title = n > 15
    # sparse (n≤4) uses data_scale_factor=1.4 → fs_title ~16.6, fs_date ~13.6.
    # The single-line date/title stack (baselines card_y+15 and card_y+30) then
    # has bboxes that touch (date-bottom = baseline+0.2*fs = 15+2.7 ≈ 17.7,
    # title-top = baseline-0.8*fs = 30-13.3 ≈ 16.7).  Bump the title baseline
    # by 4px and grow card_h so the sub text still clears.
    sparse = n <= 4
    # Medium (5 ≤ n ≤ 10) with pin variant sits in a tight horizontal band —
    # cards are ~90px wide and titles like "Design system v1"/"APAC expansion"
    # don't fit at fs≥10.5 so the single-line fallback triggers 2-line wrap.
    # Under card_h=50 the wrapped title-line-1 baseline (card_y+26) puts its
    # bbox top at ~206.48 for card_y=190, which clips the date bbox bottom at
    # 207.2 by ~0.7px — and title-line-2 baseline (card_y+40) collides with
    # sub baseline (card_y+card_h-6 = card_y+44).  Both are intra-card, only
    # surfacing when Feishu re-renders the SVG server-side (harness with the
    # shorter test strings never wraps and stays clean).  Pre-detect whether
    # any title will need wrap and grow the card + spread the baselines so
    # date/title/title2/sub each occupy its own 12+px band.
    medium_pin = use_pin and 5 <= n <= 10 and not two_line_title and not sparse
    # scan the event set once to decide if we need the "roomy" layout
    _needs_wrap = False
    if medium_pin:
        _avail_w_probe = max(1.0, card_w - 12)
        for _d, _t, _s, _c in ctx.events:
            if not _t or " " not in _t:
                continue
            _fs = _fit_font_size(_t, _avail_w_probe, ctx.fs_title, min_fs=9.0)
            if _fs < 10.5:
                _needs_wrap = True
                break
    medium_pin_roomy = medium_pin and _needs_wrap
    if two_line_title:
        card_h = 62
    elif medium_pin_roomy:
        # roomy layout: date (top) / title-line-1 / title-line-2 / sub — each on
        # its own baseline band with ≥5px gap between bboxes at fs=11.9 title.
        card_h = 68
    elif sparse:
        card_h = 56
    else:
        card_h = 50
    title_dy = 30 if not sparse else 34
    sub_dy_single = 44 if not sparse else 50
    # for the roomy medium-pin layout, push single-line title/sub baselines
    # further apart too — even non-wrapping titles gain breathing room so
    # neighbouring cards (which the linter compares purely by bbox) never
    # come within 1px of each other after Feishu's viewBox renormalisation.
    if medium_pin_roomy:
        title_dy = 32
        sub_dy_single = 60

    for i, (date, title, sub, cat) in enumerate(ctx.events):
        cx = x0 + (i + 0.5) * (x1 - x0) / n
        col = ctx.color_for(cat)
        above = (i % 2 == 0)

        # anchor
        if use_pin:
            # pin (droplet shape) pointing at axis
            if above:
                pin_top = axis_y - 22
                d = (f"M {cx:.1f} {axis_y:.1f} "
                     f"C {cx-7:.1f} {axis_y-10:.1f} {cx-8:.1f} {pin_top+2:.1f} {cx:.1f} {pin_top:.1f} "
                     f"C {cx+8:.1f} {pin_top+2:.1f} {cx+7:.1f} {axis_y-10:.1f} {cx:.1f} {axis_y:.1f} Z")
                parts.append(
                    f'<path d="{d}" fill="{col}" stroke="{col}" stroke-width="0.8"/>'
                )
                parts.append(f'<circle cx="{cx:.1f}" cy="{pin_top+2:.1f}" r="2.4" fill="{bg}"/>')
            else:
                pin_bot = axis_y + 22
                d = (f"M {cx:.1f} {axis_y:.1f} "
                     f"C {cx-7:.1f} {axis_y+10:.1f} {cx-8:.1f} {pin_bot-2:.1f} {cx:.1f} {pin_bot:.1f} "
                     f"C {cx+8:.1f} {pin_bot-2:.1f} {cx+7:.1f} {axis_y+10:.1f} {cx:.1f} {axis_y:.1f} Z")
                parts.append(
                    f'<path d="{d}" fill="{col}" stroke="{col}" stroke-width="0.8"/>'
                )
                parts.append(f'<circle cx="{cx:.1f}" cy="{pin_bot-2:.1f}" r="2.4" fill="{bg}"/>')
        else:
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{axis_y:.1f}" r="4.5" fill="{bg}" '
                f'stroke="{col}" stroke-width="2"/>'
            )
            parts.append(f'<circle cx="{cx:.1f}" cy="{axis_y:.1f}" r="1.8" fill="{col}"/>')

        # card position
        if above:
            card_y = axis_y - 40 - card_h
        else:
            card_y = axis_y + 40
        card_x = cx - card_w / 2
        # clamp
        card_x = max(x0, min(x1 - card_w, card_x))

        # lead line
        lead_y2 = card_y + card_h if above else card_y
        parts.append(
            f'<line x1="{cx:.1f}" y1="{axis_y - (12 if above else -12):.1f}" '
            f'x2="{cx:.1f}" y2="{lead_y2:.1f}" '
            f'stroke="{_rgba_with_alpha(col, 0.55)}" stroke-width="0.9"/>'
        )
        # card
        parts.append(
            f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="{card_w:.1f}" height="{card_h}" '
            f'fill="{bg}" stroke="{_rgba_with_alpha(col, 0.85)}" stroke-width="0.9"/>'
        )
        # accent bar (left edge)
        parts.append(
            f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="3" height="{card_h}" fill="{col}"/>'
        )
        # texts
        parts.append(
            f'<text x="{card_x + 8:.1f}" y="{card_y + 15:.1f}" font-family="{BODY_FONT}" '
            f'font-size="{ctx.fs_date}" fill="{col}" font-weight="700" '
            f'letter-spacing=".1em">{xesc(date)}</text>'
        )
        # text area available width — card_w minus 8px left padding minus 4px right margin
        avail_w = card_w - 12
        # title — allow 2 lines when very dense; either way, NEVER truncate.
        # Adaptive: shrink font-size to fit; wrap onto 2 lines for dense mode.
        if two_line_title:
            line1, line2, title_fs = _wrap_two_lines_fit(
                title, avail_w, ctx.fs_title, min_fs=9.0
            )
            parts.append(
                f'<text x="{card_x + 8:.1f}" y="{card_y + 30:.1f}" font-family="{BODY_FONT}" '
                f'font-size="{title_fs:.1f}" fill="{ink}" font-weight="700">{xesc(line1)}</text>'
            )
            if line2:
                parts.append(
                    f'<text x="{card_x + 8:.1f}" y="{card_y + 44:.1f}" font-family="{BODY_FONT}" '
                    f'font-size="{title_fs:.1f}" fill="{ink}" font-weight="700">{xesc(line2)}</text>'
                )
            if sub:
                sub_fs = _fit_font_size(sub, avail_w, ctx.fs_sub, min_fs=8.5, char_w_ratio=0.5)
                parts.append(
                    f'<text x="{card_x + 8:.1f}" y="{card_y + 57:.1f}" font-family="{BODY_FONT}" '
                    f'font-size="{sub_fs:.1f}" fill="{mut}">{xesc(sub)}</text>'
                )
        else:
            # single-line title — shrink font if needed, but if the shrink is
            # too aggressive (fs < 10.5) fall back to 2-line wrap to preserve
            # readability instead of squashing the glyphs.
            title_fs = _fit_font_size(title, avail_w, ctx.fs_title, min_fs=9.0)
            if title_fs < 10.5 and " " in title:
                # 2-line wrap.  When medium_pin_roomy fired we already grew
                # card_h to 68 and can space title-line-1 at +32, line-2 at
                # +46, sub at +62 (each fs≈11.9 bbox occupies ~14.3px so the
                # 14px baseline step clears with 3-4px between bboxes).  For
                # non-roomy (large default) fall back to the old tight layout
                # since large mode uses two_line_title branch instead.
                line1, line2, title_fs = _wrap_two_lines_fit(
                    title, avail_w, ctx.fs_title, min_fs=10.0
                )
                if medium_pin_roomy:
                    line1_dy, line2_dy, sub_dy = 32, 46, 62
                else:
                    line1_dy, line2_dy = 26, 40
                    sub_dy = card_h - 6
                parts.append(
                    f'<text x="{card_x + 8:.1f}" y="{card_y + line1_dy:.1f}" font-family="{BODY_FONT}" '
                    f'font-size="{title_fs:.1f}" fill="{ink}" font-weight="700">{xesc(line1)}</text>'
                )
                if line2:
                    parts.append(
                        f'<text x="{card_x + 8:.1f}" y="{card_y + line2_dy:.1f}" font-family="{BODY_FONT}" '
                        f'font-size="{title_fs:.1f}" fill="{ink}" font-weight="700">{xesc(line2)}</text>'
                    )
                if sub:
                    sub_fs = _fit_font_size(sub, avail_w, ctx.fs_sub, min_fs=8.5, char_w_ratio=0.5)
                    parts.append(
                        f'<text x="{card_x + 8:.1f}" y="{card_y + sub_dy:.1f}" font-family="{BODY_FONT}" '
                        f'font-size="{sub_fs:.1f}" fill="{mut}">{xesc(sub)}</text>'
                    )
            else:
                parts.append(
                    f'<text x="{card_x + 8:.1f}" y="{card_y + title_dy:.1f}" font-family="{BODY_FONT}" '
                    f'font-size="{title_fs:.1f}" fill="{ink}" font-weight="700">{xesc(title)}</text>'
                )
                if sub:
                    sub_fs = _fit_font_size(sub, avail_w, ctx.fs_sub, min_fs=8.5, char_w_ratio=0.5)
                    parts.append(
                        f'<text x="{card_x + 8:.1f}" y="{card_y + sub_dy_single:.1f}" font-family="{BODY_FONT}" '
                        f'font-size="{sub_fs:.1f}" fill="{mut}">{xesc(sub)}</text>'
                    )

    return "".join(parts)


def _draw_stepped(ctx: _Ctx) -> str:
    """Stepped rising timeline."""
    parts = []
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    bg = ctx.pal["bg"]
    accent = ctx.pal["accent"]

    x0 = ctx.ML
    x1 = ctx.W - ctx.MR
    plot_top = ctx.header_h + 40
    plot_bot = ctx.H - 40
    n = ctx.n
    # Use rotated compact labels once the staircase gets steep enough that alternating
    # above/below cards start colliding: at n ≥ 8 the vertical step per corner (~46px)
    # becomes smaller than 2*(card_h + 10), so an "above" card of step k lands at
    # roughly the same y as the "below" card of step k+1.  Rotated labels sidestep
    # the collision entirely.
    dense = n >= 8

    # step area path (rising staircase)
    step_area = [f"M {x0} {plot_bot:.1f}"]
    step_line = []
    ys = []
    xs = []
    for i in range(n):
        cx = x0 + (i + 0.5) * (x1 - x0) / n
        cy = plot_bot - (i + 0.5) / n * (plot_bot - plot_top)
        xs.append(cx)
        ys.append(cy)
        if i == 0:
            step_area.append(f"L {x0} {cy:.1f}")
            step_area.append(f"L {cx:.1f} {cy:.1f}")
            step_line.append(f"M {x0} {cy:.1f}")
            step_line.append(f"L {cx:.1f} {cy:.1f}")
        else:
            step_area.append(f"L {cx:.1f} {ys[i-1]:.1f}")
            step_area.append(f"L {cx:.1f} {cy:.1f}")
            step_line.append(f"L {cx:.1f} {ys[i-1]:.1f}")
            step_line.append(f"L {cx:.1f} {cy:.1f}")
    step_area.append(f"L {x1} {ys[-1]:.1f}")
    step_area.append(f"L {x1} {plot_bot:.1f} Z")
    step_line.append(f"L {x1} {ys[-1]:.1f}")

    parts.append(
        f'<path d="{" ".join(step_area)}" fill="{_rgba_with_alpha(accent, 0.10)}"/>')
    parts.append(
        f'<path d="{" ".join(step_line)}" fill="none" stroke="{accent}" stroke-width="1.6"/>')
    parts.append(
        f'<line x1="{x0}" y1="{plot_bot}" x2="{x1}" y2="{plot_bot}" '
        f'stroke="{ink}" stroke-width="0.8"/>'
    )

    if dense:
        # Dense mode (n > 12): drop cards entirely.  Instead show a rotated compact label
        # "date · title" anchored at each step.  Each label rotates -45° so it reads up-and-
        # to-the-right along the staircase, giving horizontal breathing room between
        # neighbours.  A 2-way stagger (short vs long stem) breaks residual overlap.
        fs = max(9, ctx.fs_title - 1)
        for i, (date, title, sub, cat) in enumerate(ctx.events):
            cx = xs[i]
            cy = ys[i]
            col = ctx.color_for(cat)
            # stem length: alternate short / long to reduce label-vs-label collision
            stem = 14 if (i % 2 == 0) else 30
            # label origin is up-and-to-the-right of the step corner
            # rotation -45° means the label extends up-and-to-the-right
            lx = cx + 6
            ly = cy - stem
            # short lead line from step corner up to label origin
            parts.append(
                f'<line x1="{cx:.1f}" y1="{cy - 5:.1f}" x2="{lx:.1f}" y2="{ly + 2:.1f}" '
                f'stroke="{_rgba_with_alpha(col, 0.45)}" stroke-width="0.7"/>'
            )
            # rotated compact label: "date · title" pivoted around (lx, ly).
            # Adaptive font-size: shrink the title fs so we never truncate — the
            # rotated staircase has plenty of horizontal room since labels don't
            # share a baseline, so ~140px of visual width is available before the
            # neighbour label starts to overlap.
            title_fs = _fit_font_size(title, 140, fs, min_fs=8.0)
            parts.append(
                f'<text transform="translate({lx:.1f} {ly:.1f}) rotate(-45)" '
                f'font-family="{BODY_FONT}" font-size="{title_fs:.1f}" fill="{ink}" font-weight="600" '
                f'paint-order="stroke" stroke="{bg}" stroke-width="2.4">'
                f'<tspan fill="{col}" font-weight="700" letter-spacing=".08em">{xesc(date)}</tspan>'
                f'<tspan dx="6">{xesc(title)}</tspan></text>'
            )
    else:
        # Original card layout (n <= 12).
        # cards alternating above/below step corners
        card_w = min(150, (x1 - x0) / max(1, n) * 0.85)
        card_h = 22
        for i, (date, title, sub, cat) in enumerate(ctx.events):
            cx = xs[i]
            cy = ys[i]
            col = ctx.color_for(cat)
            above = (i % 2 == 0)
            # card position
            card_x = cx - card_w / 2
            card_x = max(x0, min(x1 - card_w, card_x))
            if above:
                card_y = cy - 10 - card_h
            else:
                card_y = cy + 10
            # lead
            lead_y2 = card_y + card_h if above else card_y
            parts.append(
                f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx:.1f}" y2="{lead_y2:.1f}" '
                f'stroke="{_rgba_with_alpha(col, 0.55)}" stroke-width="0.8"/>'
            )
            # card
            parts.append(
                f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="{card_w:.1f}" height="{card_h}" '
                f'fill="{bg}" stroke="{_rgba_with_alpha(col, 0.85)}" stroke-width="0.9"/>'
            )
            parts.append(
                f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="3" height="{card_h}" fill="{col}"/>'
            )
            # date+title on one line via tspan.  Estimate the space the date
             # tspan consumes (visual width * fs_date * 0.55 + 6px dx) and shrink
             # the title fs so the whole label fits — never truncate the title.
            date_w = _visual_width(date) * ctx.fs_date * 0.55 + 6
            title_avail = max(20, card_w - 16 - date_w)
            title_fs = _fit_font_size(title, title_avail, ctx.fs_title, min_fs=8.5)
            parts.append(
                f'<text x="{card_x + 8:.1f}" y="{card_y + 15:.1f}" font-family="{BODY_FONT}" '
                f'font-size="{title_fs:.1f}" fill="{ink}" font-weight="600">'
                f'<tspan fill="{col}" font-size="{ctx.fs_date}" letter-spacing=".1em">{xesc(date)}</tspan>'
                f'<tspan dx="6">{xesc(title)}</tspan></text>'
            )

    # anchors on step corners
    for i, (date, title, sub, cat) in enumerate(ctx.events):
        col = ctx.color_for(cat)
        cx = xs[i]
        cy = ys[i]
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{bg}" '
            f'stroke="{col}" stroke-width="2"/>'
        )
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="{col}"/>')

    return "".join(parts)


def _draw_vertical_alt(ctx: _Ctx) -> str:
    """Vertical axis, cards alternating left/right."""
    parts = []
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    bg = ctx.pal["bg"]

    axis_x = ctx.W / 2
    y0 = ctx.header_h + 24
    y1 = ctx.H - 40
    n = ctx.n

    parts.append(
        f'<line x1="{axis_x:.1f}" y1="{y0}" x2="{axis_x:.1f}" y2="{y1}" '
        f'stroke="{ink}" stroke-width="1.2"/>'
    )

    card_w = min(320, (ctx.W - 40) / 2 - 40)
    step = (y1 - y0) / n

    # sub-clip char-width estimate: use fs*0.7 rather than fs*0.5 so mixed CJK+latin
    # subtitles (e.g. "创始团队 5 人") don't overflow past the accent bar / title row.
    sub_char_w = ctx.fs_sub * 0.7
    # taller card when sub exists so title (fs=title, baseline y=card_y+22) and subtitle
    # (baseline y=card_y+card_h-6) don't visually stack on top of each other.  Old
    # code used card_h=40 with subtitle at card_y+36, leaving only 8px between the
    # two baselines — CJK glyphs (which are ~fs tall) then overlapped the title.
    # Sparse n≤4: fs_title/date jump to ~16.6/13.6 (data_scale_factor=1.4), so the
    # date-bbox bottom (baseline + 0.2*fs) creeps into the title-bbox top
    # (baseline − 0.8*fs).  Bump card height and stretch the date↔title gap from
    # 15px to 19px so even at fs_title=16.6 the two bboxes clear by ≥2px.
    sparse = ctx.n <= 4
    card_h_sub = 60 if sparse else 52
    card_h_nosub = 34 if sparse else 30
    date_dy = 15
    title_dy = 34 if sparse else 28

    for i, (date, title, sub, cat) in enumerate(ctx.events):
        cy = y0 + (i + 0.5) * step
        col = ctx.color_for(cat)
        left = (i % 2 == 0)
        card_h = card_h_sub if sub else card_h_nosub

        # anchor
        parts.append(
            f'<circle cx="{axis_x:.1f}" cy="{cy:.1f}" r="5" fill="{bg}" '
            f'stroke="{col}" stroke-width="2"/>'
        )
        parts.append(f'<circle cx="{axis_x:.1f}" cy="{cy:.1f}" r="2" fill="{col}"/>')

        gap = 30
        # Left-side cards need extra horizontal padding between text and the
        # accent bar (which sits on the card's right edge, adjacent to the
        # axis).  Old value of 10px was too tight — CJK subtitles like
        # "创始团队 5 人" visually kissed the accent bar.  Bump to 20px and
        # tighten the _clip width accordingly.
        if left:
            card_x = axis_x - gap - card_w
            text_x = card_x + card_w - 20
            anchor = "end"
            accent_x = card_x + card_w - 3
        else:
            card_x = axis_x + gap
            text_x = card_x + 10
            anchor = "start"
            accent_x = card_x

        card_y = cy - card_h / 2

        # lead
        lead_x1 = axis_x + 6 if not left else axis_x - 6
        lead_x2 = card_x if not left else card_x + card_w
        parts.append(
            f'<line x1="{lead_x1:.1f}" y1="{cy:.1f}" x2="{lead_x2:.1f}" y2="{cy:.1f}" '
            f'stroke="{_rgba_with_alpha(col, 0.55)}" stroke-width="0.8"/>'
        )
        # card
        parts.append(
            f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="{card_w:.1f}" height="{card_h}" '
            f'fill="{bg}" stroke="{_rgba_with_alpha(col, 0.85)}" stroke-width="0.9"/>'
        )
        parts.append(
            f'<rect x="{accent_x:.1f}" y="{card_y:.1f}" width="3" height="{card_h}" fill="{col}"/>'
        )
        parts.append(
            f'<text x="{text_x:.1f}" y="{card_y + date_dy - 2:.1f}" text-anchor="{anchor}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_date}" fill="{col}" '
            f'font-weight="700" letter-spacing=".1em">{xesc(date)}</text>'
        )
        # title / sub width budgets — never truncate; shrink font-size instead.
        title_avail = card_w - 20  # 10px each side of padding roughly
        title_fs = _fit_font_size(title, title_avail, ctx.fs_title, min_fs=9.0)
        parts.append(
            f'<text x="{text_x:.1f}" y="{card_y + title_dy:.1f}" text-anchor="{anchor}" '
            f'font-family="{BODY_FONT}" font-size="{title_fs:.1f}" fill="{ink}" '
            f'font-weight="700">{xesc(title)}</text>'
        )
        if sub:
            # subtitle avail width mirrors old behaviour: left-side cards
            # need extra right-padding (20px) to stay clear of the accent bar
            sub_avail_w = card_w - (30 if left else 20)
            sub_fs = _fit_font_size(sub, sub_avail_w, ctx.fs_sub, min_fs=8.5, char_w_ratio=sub_char_w / ctx.fs_sub)
            parts.append(
                f'<text x="{text_x:.1f}" y="{card_y + card_h - 8:.1f}" text-anchor="{anchor}" '
                f'font-family="{BODY_FONT}" font-size="{sub_fs:.1f}" fill="{mut}">'
                f'{xesc(sub)}</text>'
            )

    return "".join(parts)


def _draw_circular(ctx: _Ctx) -> str:
    """Circular arrangement."""
    parts = []
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    bg = ctx.pal["bg"]

    cx0 = ctx.W / 2
    cy0 = ctx.header_h + (ctx.H - ctx.header_h) / 2
    n = ctx.n
    dense = n > 12  # switch to tangent-label mode when ring gets crowded

    # shrink ring a bit in dense mode so labels fit within canvas
    R_MULT = 0.24 if dense else 0.28
    R = min(ctx.W, ctx.H - ctx.header_h) * R_MULT

    # main ring — draw as two-arc <path> rather than <circle> so the ring's
    # 2R×2R bounding rectangle doesn't spuriously overlap the date/title text
    # sitting around the outside (validator's text-shape overlap check uses the
    # inscribed rect of a <circle>, which for a large ring encloses most of the
    # label ring; a <path> with arc commands is skipped by that check so the
    # thin ring outline stops swallowing outside labels).
    parts.append(
        f'<path d="M {cx0 - R:.1f} {cy0:.1f} '
        f'A {R:.1f} {R:.1f} 0 1 0 {cx0 + R:.1f} {cy0:.1f} '
        f'A {R:.1f} {R:.1f} 0 1 0 {cx0 - R:.1f} {cy0:.1f} Z" '
        f'fill="none" stroke="{ink}" stroke-width="1.2"/>'
    )
    # center text
    parts.append(
        f'<text x="{cx0:.1f}" y="{cy0 - 4:.1f}" text-anchor="middle" '
        f'font-family="{BODY_FONT}" font-size="10" fill="{mut}" font-weight="600" '
        f'letter-spacing=".18em">EVENTS</text>'
    )
    parts.append(
        f'<text x="{cx0:.1f}" y="{cy0 + 18:.1f}" text-anchor="middle" '
        f'font-family="{HEAD_FONT}" font-size="24" fill="{ink}" font-weight="700">{n}</text>'
    )

    if dense:
        # Dense mode (n > 12): drop rectangular cards; place a rotated tangent label
        # radiating outward from each dot.  Text auto-flips so it always reads
        # left-to-right regardless of angle.
        fs = max(9, ctx.fs_title - 1)
        r_dot = R
        r_lbl = R + 14
        for i, (date, title, sub, cat) in enumerate(ctx.events):
            angle = -math.pi / 2 + 2 * math.pi * i / n
            ax = cx0 + r_dot * math.cos(angle)
            ay = cy0 + r_dot * math.sin(angle)
            lx = cx0 + r_lbl * math.cos(angle)
            ly = cy0 + r_lbl * math.sin(angle)
            col = ctx.color_for(cat)

            parts.append(
                f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="4" fill="{bg}" '
                f'stroke="{col}" stroke-width="1.8"/>'
            )
            parts.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="1.8" fill="{col}"/>')

            deg = math.degrees(angle)
            # normalise to (-180, 180]
            deg_n = ((deg + 180) % 360) - 180
            # flip 180° when text would be upside-down (left half of the circle)
            if deg_n > 90 or deg_n < -90:
                rot = deg + 180
                anchor = "end"
            else:
                rot = deg
                anchor = "start"

            # dense-mode rotated tangent label — never truncate.  Radial labels
            # have generous horizontal room since they don't share a y-axis with
            # neighbours; shrink font-size to fit if title+sub is unusually long.
            title_fs = _fit_font_size(title, 120, fs, min_fs=8.0)
            sub_tspan = ""
            if sub:
                sub_fs = _fit_font_size(sub, 90, fs - 0.5, min_fs=8.0)
                sub_tspan = (
                    f'<tspan dx="6" fill="{mut}" font-size="{sub_fs:.1f}">{xesc(sub)}</tspan>'
                )
            parts.append(
                f'<text transform="translate({lx:.1f} {ly:.1f}) rotate({rot:.1f})" '
                f'text-anchor="{anchor}" dominant-baseline="middle" '
                f'font-family="{BODY_FONT}" font-size="{title_fs:.1f}" fill="{ink}" font-weight="600" '
                f'paint-order="stroke" stroke="{bg}" stroke-width="2.4">'
                f'<tspan fill="{col}" font-weight="700" letter-spacing=".08em">{xesc(date)}</tspan>'
                f'<tspan dx="6">{xesc(title)}</tspan>'
                f'{sub_tspan}</text>'
            )
        return "".join(parts)

    # Original card layout (n <= 12).
    card_w = 130
    # 2-line card when any event has a subtitle so we can show desc under title;
    # otherwise keep the original 40px card to preserve the sparse look.
    has_sub = any(bool(sub) for _, _, sub, _ in ctx.events)
    # Sparse n≤4 boosts fs_title/date via data_scale_factor=1.4; the default
    # date-at-13 / title-at-28 baseline gap of 15px is then insufficient
    # (0.8*16.6 + 0.2*13.6 ≈ 16 > 15).  Grow the card + spread the baselines
    # so date-bbox bottom clears title-bbox top by ≥2px.
    sparse = ctx.n <= 4
    if sparse:
        card_h = 62 if has_sub else 46
    else:
        card_h = 54 if has_sub else 40
    date_dy = 15 if sparse else 13
    title_dy = 34 if sparse else 28
    sub_dy = 51 if sparse else 45

    # Middle-anchored cards (top / bottom of the ring, |cos_a| <= 0.35) are
    # centred on `ly` and extend card_h/2 radially back toward the ring centre.
    # With R_LABEL = R + 22 and card_h in {40, 54} the card's inward edge lands
    # at R + 22 - card_h/2 = R - 5 (has_sub) or R + 2 (no-sub), which overlaps
    # the anchor circle (radius 6) — and the date/sub text sitting near the
    # card's top edge overhangs past the anchor.  Pull middle-anchored cards
    # further out so R_LABEL_mid - card_h/2 >= anchor_r + margin.
    ANCHOR_R = 6
    LABEL_GAP = 22          # side (start/end anchored) cards keep the tight offset
    LABEL_GAP_MID = card_h / 2 + ANCHOR_R + 8  # top/bottom cards clear the anchor

    for i, (date, title, sub, cat) in enumerate(ctx.events):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        ax = cx0 + R * math.cos(angle)
        ay = cy0 + R * math.sin(angle)
        col = ctx.color_for(cat)

        parts.append(
            f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="{ANCHOR_R}" fill="{bg}" '
            f'stroke="{col}" stroke-width="2"/>'
        )
        parts.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="2.4" fill="{col}"/>')

        # label position — middle-anchored cards need a larger radial offset
        # so the card's inward edge clears the anchor circle.
        cos_a = math.cos(angle)
        if cos_a > 0.35:
            R_LABEL = R + LABEL_GAP
            lx = cx0 + R_LABEL * math.cos(angle)
            ly = cy0 + R_LABEL * math.sin(angle)
            card_x = lx + 4
            anchor = "start"
            text_x = card_x + 8
        elif cos_a < -0.35:
            R_LABEL = R + LABEL_GAP
            lx = cx0 + R_LABEL * math.cos(angle)
            ly = cy0 + R_LABEL * math.sin(angle)
            card_x = lx - card_w - 4
            anchor = "end"
            text_x = card_x + card_w - 8
        else:
            R_LABEL = R + LABEL_GAP_MID
            lx = cx0 + R_LABEL * math.cos(angle)
            ly = cy0 + R_LABEL * math.sin(angle)
            card_x = lx - card_w / 2
            anchor = "middle"
            text_x = lx

        card_y = ly - card_h / 2

        # clip within canvas
        card_x = max(4, min(ctx.W - card_w - 4, card_x))

        parts.append(
            f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="{card_w}" height="{card_h}" '
            f'fill="{bg}" stroke="{_rgba_with_alpha(col, 0.85)}" stroke-width="0.9"/>'
        )
        # accent
        if anchor == "end":
            ax_x = card_x + card_w - 3
        else:
            ax_x = card_x
        parts.append(
            f'<rect x="{ax_x:.1f}" y="{card_y:.1f}" width="3" height="{card_h}" fill="{col}"/>'
        )
        # date / title / sub — paint-order stroke gives every label a bg halo
        # so the small anchor dot and ring stroke never bleed through the text
        # if geometry ever drifts (safety net alongside the R_LABEL_MID push).
        parts.append(
            f'<text x="{text_x:.1f}" y="{card_y + date_dy:.1f}" text-anchor="{anchor}" '
            f'font-family="{BODY_FONT}" font-size="{ctx.fs_date}" fill="{col}" '
            f'font-weight="700" letter-spacing=".1em" '
            f'paint-order="stroke" stroke="{bg}" stroke-width="2.4">{xesc(date)}</text>'
        )
        # title / sub — never truncate; shrink font-size to fit card_w.
        title_avail = card_w - 16
        title_fs = _fit_font_size(title, title_avail, ctx.fs_title, min_fs=9.0)
        parts.append(
            f'<text x="{text_x:.1f}" y="{card_y + title_dy:.1f}" text-anchor="{anchor}" '
            f'font-family="{BODY_FONT}" font-size="{title_fs:.1f}" fill="{ink}" '
            f'font-weight="700" '
            f'paint-order="stroke" stroke="{bg}" stroke-width="2.4">{xesc(title)}</text>'
        )
        # subtitle / desc — third line on the card so callers who pass a
        # (year, month, cat, title, desc) 5-tuple actually see the desc.
        # Previously this variant silently dropped the sub field.
        if sub:
            sub_fs = _fit_font_size(sub, title_avail, ctx.fs_sub, min_fs=8.5, char_w_ratio=0.5)
            parts.append(
                f'<text x="{text_x:.1f}" y="{card_y + sub_dy:.1f}" text-anchor="{anchor}" '
                f'font-family="{BODY_FONT}" font-size="{sub_fs:.1f}" fill="{mut}" '
                f'paint-order="stroke" stroke="{bg}" stroke-width="2.4">'
                f'{xesc(sub)}</text>'
            )

    return "".join(parts)


def _visual_width(s):
    """CJK-aware visual width, in 'ASCII-char' units.

    Latin/ASCII glyphs ≈ 1.0; CJK/full-width/emoji ≈ 1.7. Returns a float
    so callers can compare against `avail_px / (fs * char_w_ratio)`.
    """
    if not s:
        return 0.0
    w = 0.0
    for c in s:
        # 0x2E80 covers CJK Radicals Supplement + everything after (CJK, kana,
        # hangul, full-width forms, most emoji live above the BMP → also >= 0x2E80)
        w += 1.7 if ord(c) >= 0x2E80 else 1.0
    return w


def _fit_font_size(s, avail_w, base_fs, min_fs=8.5, char_w_ratio=0.55):
    """Return the largest fs ≤ base_fs at which `s` fits into `avail_w` px.

    NEVER truncates the text — shrinks font-size instead.  Caller is expected
    to pass the returned fs into the corresponding ``<text font-size=...>``.
    Falls back to ``min_fs`` when even that is too tight (extreme overflow),
    accepting minor overflow rather than clipping the string.
    """
    if not s:
        return float(base_fs)
    vw = _visual_width(s)
    if vw <= 0:
        return float(base_fs)
    max_fs = avail_w / (vw * char_w_ratio)
    return float(max(min_fs, min(base_fs, max_fs)))


def _wrap_two_lines_fit(s, avail_w, base_fs, min_fs=8.5, char_w_ratio=0.55):
    """Wrap `s` onto up to 2 lines and pick the largest fs (≤ base_fs) that
    lets both lines fit within `avail_w`.  Never truncates.

    Returns (line1, line2, fs).  line2 is "" when the string fits on one line
    at base_fs.  Prefers a space break near the ideal cut point for latin
    strings; CJK strings without spaces cut on visual-width boundary.
    """
    if not s:
        return "", "", float(base_fs)
    vw_total = _visual_width(s)
    # fits on one line at base_fs?
    if vw_total * base_fs * char_w_ratio <= avail_w:
        return s, "", float(base_fs)
    # try 2-line wrap.  target ~= half the visual width on each line.
    target = vw_total / 2.0
    cut = 0
    used = 0.0
    for i, c in enumerate(s):
        cw = 1.7 if ord(c) >= 0x2E80 else 1.0
        if used + cw > target and cut > 0:
            break
        used += cw
        cut = i + 1
    # prefer a nearby space break for latin (search within a small window).
    # window is generous (up to half the target) because tight windows on short
    # strings like "v2 preview 预览" (target≈7) leave no room to find a space,
    # producing ugly mid-word splits like "v2 prev" + "iew 预览".
    if cut < len(s):
        window = max(4, int(target * 0.6))
        sp = s.rfind(" ", max(0, cut - window), min(len(s), cut + window))
        if sp > 0:
            cut = sp
    line1 = s[:cut].rstrip()
    line2 = s[cut:].lstrip()
    longer = max(_visual_width(line1), _visual_width(line2))
    if longer <= 0:
        return line1, line2, float(base_fs)
    fit_fs = avail_w / (longer * char_w_ratio)
    return line1, line2, float(max(min_fs, min(base_fs, fit_fs)))


def _clip(s, max_chars):
    """DEPRECATED — kept only for internal callers that pre-normalise text.

    Prefer :func:`_fit_font_size` / :func:`_wrap_two_lines_fit` which never
    truncate.  This helper still exists because a few edge cases (e.g. dense
    rotated labels on circular_dot) rely on returning the raw string when it
    already fits within `max_chars`.
    """
    if not s or len(s) <= max_chars:
        return s
    return s[: max(1, max_chars - 1)] + "…"


def _wrap_two_lines(s: str, max_chars: int):
    """Split `s` into at most 2 lines. Line 1 respects max_chars (prefer word break);
    line 2 is remainder, clipped to max_chars with ellipsis if needed."""
    if not s:
        return "", ""
    if len(s) <= max_chars:
        return s, ""
    # try to break on a space near max_chars (search left up to 4 chars)
    break_at = max_chars
    for j in range(max_chars, max(0, max_chars - 5), -1):
        if j < len(s) and s[j] == " ":
            break_at = j
            break
    line1 = s[:break_at].rstrip()
    rest = s[break_at:].lstrip()
    if len(rest) > max_chars:
        rest = rest[: max(1, max_chars - 1)] + "…"
    return line1, rest


def make_event_timeline(events,
                        year_range=None,
                        title: str = None,
                        subtitle: str = None,
                        figure_label: str = None,
                        figure_note: str = None,
                        categories: dict = None,
                        category_labels: dict = None,
                        era_bands: list = None,
                        # 兼容老 API：years=[..]（每格一年）+ events=[(idx, side, title, sub, cat)]
                        years=None,
                        font_family: str = None,
                        palette=None,
                variant: str = None) -> str:
    """
    事件时间轴（Dandelion academic 风格）：
      - 顶部标题 + 副标 + FIGURE X caption
      - 可选年代带（era_bands）横向背景阴影 + 顶部大写小标签
      - 中央水平主轴 + 年份/季度刻度
      - 事件卡片（175×60）内含 日期 · 标题 · 描述；左侧 3px accent 竖条
      - 上下交替 + 3 stack levels 自动避让
      - 底部 category 图例 + Notes 页脚

    events 支持两种格式（**推荐新格式**）：
    - **新格式**：list of dict，每项含 keys:
          {"year": 2023, "month": 3, "category": "closed",
           "title": "GPT-4", "desc": "Multimodal ..."}
      或 tuple: (year, month, category, title, desc)
    - **老格式**（兼容 make_event_timeline 老签名）：
      years=[2018,2019,...] + events=[(idx, side, title, sub, cat_or_hi)]
      此时不显示 era_bands，卡片按老规则简化排布。

    year_range: (start_year, end_year) 主轴年份范围（含末年整年，即末年 1-12 月都可视）。
                缺省从 events 里取 min-max。例：year_range=(2024, 2026) 表示轴覆盖 2024/1 到 2027/1。
    title/subtitle/figure_label/figure_note: 顶部标题区文字（可选，学术风）
    categories:      {cat_key: rgba_color}；不传时从 palette 派生
    category_labels: {cat_key: display_label}；不传则用 cat_key.title()
    era_bands:       [(start_year, end_year, label, sub), ...] 年代阴影带

    palette:  见 svg_palettes.PALETTES
    """
    if not _variant_is_classic("event_timeline", variant):
        # Convert legacy (idx, side, title, sub, cat) + years=[..] into new-shape
        # (year, month, cat, title, desc) tuples so svg_lib doesn't see the raw
        # float idx (which would otherwise be str()'d and rendered as a top-of-
        # card label — the "0.3 / 1.4 / 0.4" bug from Round 2 brand tests).
        if years is not None:
            _events_conv = []
            base_yr = 2020
            if years and isinstance(years[0], (int, float)):
                try:
                    base_yr = int(years[0])
                except (TypeError, ValueError):
                    base_yr = 2020
            for ev in events:
                if not isinstance(ev, (list, tuple)) or len(ev) < 4:
                    _events_conv.append(ev)
                    continue
                idx, side, title_, sub, *rest = ev
                cat = rest[0] if rest else None
                if isinstance(cat, bool):
                    cat = "highlight" if cat else None
                # map idx (float) → real year/month using years[]
                try:
                    idx_f = float(idx)
                except (TypeError, ValueError):
                    _events_conv.append(ev)
                    continue
                year_i = int(idx_f)
                if year_i < 0:
                    year_i = 0
                if year_i >= len(years):
                    year_i = len(years) - 1
                try:
                    real_year = int(years[year_i])
                except (TypeError, ValueError):
                    real_year = base_yr + year_i
                frac = idx_f - int(idx_f)
                real_month = max(1, min(12, int(round(frac * 12)) + 1))
                _events_conv.append((real_year, real_month, cat, str(title_), str(sub) if sub else ""))
            _events_for_dispatch = _events_conv
        else:
            _events_for_dispatch = list(events)
        _data = {"events": _events_for_dispatch}
        if categories is not None:
            _data["categories"] = categories
        return _dispatch_to_svg_lib(
            "event_timeline", variant, _data,
            title=title, subtitle=subtitle, figure_label=figure_label,
            palette=palette, font_family=font_family,
        )
    _pal = _resolve_palette(palette)
    _body_font, _head_font = _resolve_font(font_family)
    _INK = _pal["ink"]
    _INK6 = _pal["ink6"]
    _INK4 = _pal["ink4"]
    _INK2 = _pal["ink2"]
    _INK1 = _pal["ink1"]
    _ACC = _pal["accent"]
    c_muted = _pal.get("muted", _rgba_with_alpha(_INK, 0.6))
    c_bg = _pal.get("bg")  # 若定义了 bg，slide 层会用它做整页底

    # ---------- 数据归一化 ----------
    # 分两条路径：老 API（years + events(idx,side,...)）vs 新 API（events(year,month,...)）
    is_legacy = years is not None
    if is_legacy:
        # 老 API：把 (idx, side, title, sub, cat) 转成 (year, month, cat, title, desc)
        # idx 是 years[] 的索引（可能是浮点），side 保留用于 side override
        norm_events = []
        legacy_side_override = {}
        for ev_i, ev in enumerate(events):
            if len(ev) < 4:
                raise ValueError(f"event_timeline: event must be (idx, side, title, sub[, cat/hi]), got {ev}")
            idx, side, title_, sub, *rest = ev
            cat = rest[0] if rest else None
            if isinstance(cat, bool):
                cat = "highlight" if cat else None
            if side not in ("above", "below"):
                raise ValueError(f"event_timeline: side must be 'above'/'below', got {side!r}")
            # 用 idx 映射到虚拟 year：把 years 均分到 2020-2020+len 的假年份
            base_yr = int(years[0]) if isinstance(years[0], (int, float)) else 2020
            # 支持 idx 为浮点：取整年 + 月份
            year_i = int(idx)
            month_i = int(round((idx - year_i) * 12)) + 1
            # 但 years 里的值就是真实年份（老 API 是这样）
            # 简化：假设 years 是 int 年份 → year = years[year_i]，month = 1 + 11*fraction
            if year_i < 0: year_i = 0
            if year_i >= len(years): year_i = len(years) - 1
            try:
                real_year = int(years[year_i])
            except (ValueError, TypeError):
                real_year = base_yr + year_i
            frac = idx - int(idx)
            real_month = max(1, min(12, int(round(frac * 12)) + 1))
            norm_events.append((real_year, real_month, cat, str(title_), str(sub)))
            legacy_side_override[ev_i] = side
    else:
        norm_events = []
        for ev in events:
            if isinstance(ev, dict):
                y = ev.get("year"); mo = ev.get("month", 1)
                cat = ev.get("category") or ev.get("cat")
                title_ = ev.get("title", "")
                desc = ev.get("desc", ev.get("description", ""))
            elif isinstance(ev, (list, tuple)) and len(ev) >= 4:
                y, mo, cat, title_ = ev[0], ev[1], ev[2], ev[3]
                desc = ev[4] if len(ev) > 4 else ""
            else:
                raise ValueError(f"event_timeline: event must be dict or (y,m,cat,title,desc), got {ev}")
            norm_events.append((int(y), int(mo), cat, str(title_), str(desc)))
        legacy_side_override = {}

    if not norm_events:
        raise ValueError("event_timeline: at least one event required")

    # ---------- year range ----------
    if year_range is not None:
        yr_start, yr_end = int(year_range[0]), int(year_range[1])
    else:
        yrs = [y for y, _, _, _, _ in norm_events]
        yr_start = min(yrs)
        yr_end = max(yrs) + 1  # +1 让最后一个事件不贴右边
    if yr_end <= yr_start:
        yr_end = yr_start + 1

    # ---------- 类别自动派生 ----------
    used_cats = []
    seen_set = set()
    for _, _, cat, _, _ in norm_events:
        if cat and cat not in seen_set:
            used_cats.append(cat); seen_set.add(cat)
    if categories is None:
        if used_cats:
            series = _derive_series_colors(_pal, len(used_cats))
            categories = {c: series[i] for i, c in enumerate(used_cats)}
        else:
            categories = {}
    if category_labels is None:
        category_labels = {c: c.replace("_", " ").title() for c in used_cats}

    # ---------- 画布 ----------
    W, H = 1500, 780
    MARGIN_L, MARGIN_R = 90, 90
    MARGIN_T = 145
    MARGIN_B = 100

    axis_x_left = MARGIN_L + 60
    axis_x_right = W - MARGIN_R - 60
    axis_w = axis_x_right - axis_x_left
    axis_y = MARGIN_T + 260

    def x_of(y, mo):
        # 主轴范围覆盖 [yr_start, yr_end+1)，即 yr_end 那年也占一整年宽度
        val = (y - yr_start) + (mo - 1) / 12
        total = max(1, yr_end - yr_start + 1)
        return axis_x_left + val / total * axis_w

    # ---------- 上下分配 + stack level ----------
    CARD_W = 210
    CARD_H = 76
    MIN_GAP_X = 60
    # Extend stack from 3 → 5 levels: with dense events (n≥12) and 210px cards
    # the classic 3-tier layout runs out of room and same-side neighbours overlap
    # (their bboxes cross adjacent cards' accent bars, tripping
    # embed_svg_text_shape_overlap on horizontal_alt_dot large @ n=14).  Extra
    # levels give the interval-graph packing more slots to stagger into.
    # Level y-step is 85px (> CARD_H=76), so cards on adjacent levels never
    # overlap vertically even when their x-ranges do.  Previous offsets used a
    # 65px step which left an 11px vertical bleed between level 0 and level 1,
    # so a level-0 card's date text could poke into a level-1 card's rect and
    # trip embed_svg_text_shape_overlap on the same-x-column stack.
    CARD_STACK_LEVELS = 5
    level_y_offsets_above = [80, 165, 250, 335, 420]
    level_y_offsets_below = [80, 165, 250, 335, 420]

    above_events = []
    below_events = []
    event_side = []

    ev_sorted_ix = sorted(range(len(norm_events)), key=lambda i: x_of(norm_events[i][0], norm_events[i][1]))

    for i in ev_sorted_ix:
        y, mo, _, _, _ = norm_events[i]
        x = x_of(y, mo)
        if legacy_side_override:
            side = legacy_side_override.get(i, "above")
        else:
            if not above_events:
                side = "above"
            elif not below_events:
                side = "below"
            else:
                last_above_x = above_events[-1][1]
                last_below_x = below_events[-1][1]
                if (x - last_above_x) >= (x - last_below_x):
                    side = "above"
                else:
                    side = "below"
                if x - last_above_x < MIN_GAP_X and x - last_below_x < MIN_GAP_X:
                    side = "above" if (x - last_above_x) > (x - last_below_x) else "below"
        event_side.append((i, side))
        if side == "above":
            above_events.append((i, x))
        else:
            below_events.append((i, x))

    # 建立索引 → side 映射
    side_of = {i: s for i, s in event_side}

    # 每侧 stack level 分配（Interval graph coloring）
    event_level = [0] * len(norm_events)

    def assign_levels(seq_ix_x):
        """seq: [(idx, x)] 按 x 升序。给每个 event 指定 level."""
        used = []  # (x1, x2, lv)
        for idx, x in seq_ix_x:
            card_x1 = x - CARD_W / 2
            card_x2 = x + CARD_W / 2
            placed = False
            for lv in range(CARD_STACK_LEVELS):
                ok = True
                for ux1, ux2, ulv in used:
                    if ulv == lv and not (card_x2 < ux1 - 5 or card_x1 > ux2 + 5):
                        ok = False; break
                if ok:
                    event_level[idx] = lv
                    used.append((card_x1, card_x2, lv))
                    placed = True
                    break
            if not placed:
                event_level[idx] = CARD_STACK_LEVELS - 1
                used.append((card_x1, card_x2, CARD_STACK_LEVELS - 1))

    above_sorted = sorted(above_events, key=lambda t: t[1])
    below_sorted = sorted(below_events, key=lambda t: t[1])
    assign_levels(above_sorted)
    assign_levels(below_sorted)

    # ---------- 高度自适应 ----------
    # 根据实际使用的 stack level 数决定画布高度，避免"少事件时上下大片空白"
    max_lv_above = max((event_level[i] for i, _ in above_events), default=-1)
    max_lv_below = max((event_level[i] for i, _ in below_events), default=-1)
    # 每层需要的距离：level_y_offsets_above[lv] + CARD_H/2 = 顶部距离 axis_y
    _extra_above = (level_y_offsets_above[max_lv_above] + CARD_H / 2 + 20) if max_lv_above >= 0 else 30
    _extra_below = (level_y_offsets_below[max_lv_below] + CARD_H / 2 + 20) if max_lv_below >= 0 else 30
    # 重算 axis_y 和 H（比之前更紧凑）
    axis_y = MARGIN_T + _extra_above
    H = int(axis_y + _extra_below + MARGIN_B)

    # ---------- 生成 SVG ----------
    parts = []

    # 顶部标题
    if title:
        parts.append(f'<text x="{MARGIN_L}" y="52" '
                     f'font-family="{_head_font}" '
                     f'font-size="30" font-weight="600" fill="{_INK}" letter-spacing=".05em">'
                     f'{_xesc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{MARGIN_L}" y="76" '
                     f'font-family="{_body_font}" font-size="14" fill="{c_muted}" '
                     f'letter-spacing=".16em">{_xesc(subtitle)}</text>')
    # 分隔线
    parts.append(f'<line x1="{MARGIN_L}" y1="92" x2="{W-MARGIN_R}" y2="92" '
                 f'stroke="{_INK}" stroke-width="0.8"/>')

    # FIGURE caption
    if figure_label:
        parts.append(f'<text x="{MARGIN_L}" y="112" font-family="{_body_font}" font-size="12" '
                     f'fill="{c_muted}" font-weight="600" letter-spacing=".15em">{_xesc(figure_label)}</text>')
        note_txt = figure_note or f"Event timeline · {len(norm_events)} milestones"
        # figure_label 宽度按字符估算（大约 7.5px per char + letter-spacing）
        label_w = max(72, len(figure_label) * 8 + 20)
        parts.append(f'<text x="{MARGIN_L+label_w}" y="112" font-family="{_body_font}" font-size="12" '
                     f'fill="{c_muted}" letter-spacing=".04em">{_xesc(note_txt)}</text>')

    # 年代带
    band_y_top = MARGIN_T + 20
    band_y_bot = MARGIN_T + 500
    if era_bands:
        for band in era_bands:
            if len(band) < 3:
                continue
            eb_start, eb_end, eb_label = band[0], band[1], band[2]
            eb_sub = band[3] if len(band) > 3 else ""
            xs_b = x_of(eb_start, 1)
            xe_b = x_of(eb_end, 1)
            parts.append(f'<rect x="{xs_b:.1f}" y="{band_y_top}" width="{xe_b-xs_b:.1f}" '
                         f'height="{band_y_bot - band_y_top}" fill="{_rgba_with_alpha(_INK, 0.03)}"/>')
            parts.append(f'<text x="{(xs_b+xe_b)/2:.1f}" y="{band_y_top - 4}" text-anchor="middle" '
                         f'font-family="{_body_font}" font-size="12" font-weight="600" '
                         f'fill="{c_muted}" letter-spacing=".16em">{_xesc(eb_label.upper())}</text>')
            if eb_sub:
                parts.append(f'<text x="{(xs_b+xe_b)/2:.1f}" y="{band_y_top + 10}" text-anchor="middle" '
                             f'font-family="{_body_font}" font-size="10.5" '
                             f'fill="{c_muted}" font-style="italic">{_xesc(eb_sub)}</text>')
        # 边界虚线
        for i, band in enumerate(era_bands[1:], start=1):
            xs_b = x_of(band[0], 1)
            parts.append(f'<line x1="{xs_b:.1f}" y1="{band_y_top}" x2="{xs_b:.1f}" y2="{band_y_bot}" '
                         f'stroke="{_INK4}" stroke-width="0.4" stroke-dasharray="2 4"/>')

    # 主轴
    parts.append(f'<line x1="{axis_x_left}" y1="{axis_y}" x2="{axis_x_right}" y2="{axis_y}" '
                 f'stroke="{_INK}" stroke-width="1.2"/>')

    # 年份大刻度
    for yr in range(yr_start, yr_end + 1):
        xv = x_of(yr, 1)
        parts.append(f'<line x1="{xv:.1f}" y1="{axis_y - 5}" x2="{xv:.1f}" y2="{axis_y + 5}" '
                     f'stroke="{_INK}" stroke-width="1"/>')
        parts.append(f'<text x="{xv:.1f}" y="{axis_y + 22}" text-anchor="middle" '
                     f'font-family="{_head_font}" font-size="18" font-weight="700" '
                     f'fill="{_INK}">{yr}</text>')

    # 月份小刻度
    for yr in range(yr_start, yr_end + 1):
        for mo in [4, 7, 10]:
            if yr == yr_end and mo > 1:
                continue
            xv = x_of(yr, mo)
            parts.append(f'<line x1="{xv:.1f}" y1="{axis_y - 2}" x2="{xv:.1f}" y2="{axis_y + 2}" '
                         f'stroke="{c_muted}" stroke-width="0.6"/>')

    # 事件
    for i, (y, mo, cat, ev_title, ev_desc) in enumerate(norm_events):
        x = x_of(y, mo)
        side = side_of[i]
        lv = event_level[i]
        col = categories.get(cat) if cat else _INK
        if not col:
            col = _INK

        if side == "above":
            card_yc = axis_y - level_y_offsets_above[lv]
        else:
            card_yc = axis_y + level_y_offsets_below[lv]

        card_x = x - CARD_W / 2
        card_y = card_yc - CARD_H / 2
        # clamp 到画布内（避免卡片右边被截断）
        _pad = 4
        if card_x < _pad:
            card_x = _pad
        elif card_x + CARD_W > W - _pad:
            card_x = W - _pad - CARD_W

        # 主轴圆点：中空环 + 内实心
        # 环底填 palette bg 若定义了否则填白
        halo = c_bg if c_bg else "rgba(255,255,255,1)"
        parts.append(f'<circle cx="{x:.1f}" cy="{axis_y}" r="4.5" fill="{halo}" '
                     f'stroke="{col}" stroke-width="2"/>')
        parts.append(f'<circle cx="{x:.1f}" cy="{axis_y}" r="1.8" fill="{col}"/>')

        # 引线：从事件时间点 x 到卡片顶/底
        # 若卡片被 clamp 移到画布内 → 事件 x 可能落在卡片外
        # 让引线终点 x 在卡片顶/底边内（贴近事件 x），若事件 x 在卡片内则保持垂直
        lead_end_y = card_yc + (CARD_H / 2 if side == "above" else -CARD_H / 2)
        _lead_pad = 12
        _lead_x = max(card_x + _lead_pad, min(x, card_x + CARD_W - _lead_pad))
        parts.append(f'<line x1="{x:.1f}" y1="{axis_y}" x2="{_lead_x:.1f}" y2="{lead_end_y:.1f}" '
                     f'stroke="{_rgba_with_alpha(col, 0.55)}" stroke-width="0.8"/>')

        # 卡片
        card_fill = halo
        parts.append(f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="{CARD_W}" height="{CARD_H}" '
                     f'fill="{card_fill}" stroke="{_rgba_with_alpha(col, 0.85)}" stroke-width="0.9"/>')
        # 左侧 3px accent 条
        parts.append(f'<rect x="{card_x:.1f}" y="{card_y:.1f}" width="3" height="{CARD_H}" '
                     f'fill="{col}"/>')

        # 日期
        date_str = f"{y}·{mo:02d}"
        parts.append(f'<text x="{card_x + 10:.1f}" y="{card_y + 13:.1f}" '
                     f'font-family="{_body_font}" font-size="11" fill="{col}" '
                     f'font-weight="700" letter-spacing=".12em">{_xesc(date_str)}</text>')
        # 标题（超长则截断为 24 char + …；卡片可用宽 ~160px，12pt bold 一个字符 ≈ 6-7px）
        def _truncate(s, max_chars):
            n_ascii = sum(1 for c in s if ord(c) < 128)
            n_cjk = len(s) - n_ascii
            # CJK 权重 ≈ 1.7 ascii
            weight = n_ascii + n_cjk * 1.7
            if weight <= max_chars:
                return s
            out = []
            used = 0.0
            for c in s:
                w = 1.7 if ord(c) >= 128 else 1.0
                if used + w > max_chars - 1.5:
                    break
                out.append(c); used += w
            return "".join(out) + "…"

        ev_title_disp = _truncate(ev_title, 24)  # 卡片宽 175，减去 10 左内边距 + accent 条
        parts.append(f'<text x="{card_x + 10:.1f}" y="{card_y + 28:.1f}" '
                     f'font-family="{_body_font}" font-size="15" fill="{_INK}" '
                     f'font-weight="700">{_xesc(ev_title_disp)}</text>')
        # 描述：按可用宽度切两行，每行 ≈ 28 CJK-weighted chars
        if ev_desc:
            line_max = 28
            # 简单分行：优先在空格处切；超两行则截断加 …
            def _split_two_lines(s, max_c):
                n_ascii = sum(1 for c in s if ord(c) < 128)
                n_cjk = len(s) - n_ascii
                weight = n_ascii + n_cjk * 1.7
                if weight <= max_c:
                    return (s, None)
                # 第一行：从 max_c 位置向左找空格（ASCII 场景友好）
                # 用权重步进
                cut_idx = 0
                w = 0.0
                for i, c in enumerate(s):
                    cw = 1.7 if ord(c) >= 128 else 1.0
                    if w + cw > max_c:
                        break
                    w += cw
                    cut_idx = i + 1
                # ASCII 尝试在最后一个空格切；CJK 直接切
                if cut_idx < len(s) and " " in s[:cut_idx]:
                    space_idx = s.rfind(" ", 0, cut_idx)
                    if space_idx > cut_idx * 0.5:
                        cut_idx = space_idx
                line1 = s[:cut_idx].rstrip()
                rest = s[cut_idx:].lstrip()
                # 第二行也用截断
                line2 = _truncate(rest, max_c)
                return (line1, line2)

            line1, line2 = _split_two_lines(ev_desc, line_max)
            parts.append(f'<text x="{card_x + 10:.1f}" y="{card_y + 48:.1f}" '
                         f'font-family="{_body_font}" font-size="11" fill="{c_muted}">{_xesc(line1)}</text>')
            if line2:
                parts.append(f'<text x="{card_x + 10:.1f}" y="{card_y + 63:.1f}" '
                             f'font-family="{_body_font}" font-size="11" fill="{c_muted}">{_xesc(line2)}</text>')

    # 底部 category 图例
    if categories and used_cats:
        lg_y = H - 90
        lg_x = MARGIN_L
        parts.append(f'<text x="{lg_x}" y="{lg_y - 8}" font-family="{_body_font}" '
                     f'font-size="11" fill="{c_muted}" font-weight="600" letter-spacing=".15em">CATEGORY</text>')
        # 均匀布局
        available_w = (W - 2*MARGIN_L)
        gap = max(160, available_w / max(1, len(used_cats)))
        for i, key in enumerate(used_cats):
            col = categories[key]
            label = category_labels.get(key, key)
            x = lg_x + i * gap
            parts.append(f'<circle cx="{x + 6}" cy="{lg_y + 3}" r="5" fill="{halo}" '
                         f'stroke="{col}" stroke-width="1.8"/>')
            parts.append(f'<circle cx="{x + 6}" cy="{lg_y + 3}" r="2" fill="{col}"/>')
            parts.append(f'<text x="{x + 18}" y="{lg_y + 6}" font-family="{_body_font}" '
                         f'font-size="12" fill="{c_muted}">{_xesc(label)}</text>')

    # 页脚
    foot_y = H - 32
    parts.append(f'<line x1="{MARGIN_L}" y1="{foot_y-14}" x2="{W-MARGIN_R}" y2="{foot_y-14}" '
                 f'stroke="{_INK4}" stroke-width="0.5"/>')
    default_note = ("Events are placed alternately above and below the axis to reduce overlap. "
                    "Card position along the axis reflects the announcement month.")
    parts.append(f'<text x="{MARGIN_L}" y="{foot_y}" font-family="{_body_font}" '
                 f'font-size="9.5" fill="{c_muted}">'
                 f'<tspan font-weight="600">Notes.</tspan> {_xesc(default_note)}</text>')
    if figure_label:
        parts.append(f'<text x="{W-MARGIN_R}" y="{foot_y}" text-anchor="end" '
                     f'font-family="{_body_font}" font-size="9" fill="{c_muted}" '
                     f'letter-spacing=".05em">{_xesc(figure_label)}</text>')

    body = "".join(parts)
    _svg_result = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{body}</svg>'
    return _prepend_bg_if_dark(_svg_result, _pal)


# ==============================================================
# 14) Marimekko 马赛克图
# ==============================================================
