"""Consulting page layouts measured from an investment-committee deck (1440×810 scaled to 960×540, ×2/3).

Native XML page blocks that sit around (or replace) an exhibit chart area, so a page is not always "chart left +
three loose bullets right":

  key_takeaways   grey right rail: "关键要点 / KEY TAKEAWAYS" label, black rule, bold heads + body, grey dividers
  stat_stack      column of serif big numbers, each with a grey caption, grey dividers (next to a diagram / photo)
  section_head    bold block title + black rule over a column (chart, table, list)
  kv_rows         label | bold value rows between grey rules (a parameter table inside a column)
  note_box        light grey box with a 3px dark left bar (one framed sentence: what the chart above means)
  dot_bullets     small coloured dots + text (evidence lines under a chart)
  numbered_steps  ①②③④ circles + optional icon + bold head + body, grey dividers (a mechanism / chain)
  columns_page    3–4 parallel columns, each a stack of blocks (kicker+title, big number, text, kv rows, chart slot,
                  dots, note box), optional grey card background — the "three models compared" / "four sources" page
  table_block     multi-column table (icon + bold first column, numbers right, focus row shaded)
  mixed_columns_page  image/chart/table/explanation blocks in any column or vertical stack
  diagram_page    shortcut for image + optional stats + takeaways
  kpi_strip / kpi_charts_page  headline figures across the top + 1–2 charts below
  column_boxes    the (x, y, w, h) boxes of n columns over the body (for charts / tables placed by hand)

Every function takes slide coordinates (px = pt on the 960×540 canvas) and returns XML strings (plus geometry), to be
passed to f.publish(...). Body text >=14pt, heads 15pt bold, small-caps labels 12pt grey,
big numbers 28pt Georgia; superscript and step ordinals are separate annotations.
"""

from __future__ import annotations

import math
import re
from html import escape

from ._frame import W, X0, _box, _c, _icon_type, image_size
from ._palette import roles
from ._text import has_cjk, wrap

def _block(name):
    """Log one boxed page block for the research layout check (≥4 independent regions = no reading order)."""
    from ._page import BLOCKS
    BLOCKS.append(name)


SHORT: list = []   # layout warnings for the page being built; Frame.publish reports + clears them
SQUEEZE: list = []   # small overflows (≤ SQUEEZE_MAX) compressed instead of raised; Frame.publish prints + clears them
STRETCH_ROW_MAX = 10   # px a kv / table row may open up when a short column grows to its neighbour's height
NOTE_PIN_MAX = 80      # a column's closing note sits at the column foot only when that leaves ≤ this much air above it
SQUEEZE_MAX = 0.15   # overflow share a layout absorbs by shrinking chart height / row padding / gaps (never fonts)
CHART_MIN_SHARE, CHART_MIN_PX = 0.7, 60   # a compressed chart slot keeps ≥70 % of its requested height and ≥60px


def _squeezed(msg):
    """Record one compression note (the page still fits; the author sees it as a reminder, not a hold)."""
    if msg not in SQUEEZE:
        SQUEEZE.append(msg)


def split_hint(kind, n_items, fit_items, unit="行"):
    """Concrete a/b split advice for a block that overflows by more than SQUEEZE_MAX."""
    fit_items = max(1, min(int(fit_items), n_items - 1)) if n_items > 1 else 1
    return (f"拆成 a/b 两页：本页留前 {fit_items} {unit}，其余 {max(n_items - fit_items, 0)} {unit}放 b 页（同表头/同版式，"
            f"plan 加一行、交另一个 builder 并行做），或改成 Top {fit_items} + 其他；页数不设上限，不缩字号")
RAIL_W = 206  # right rail width (252/1440 of the page, widened so 14pt CJK fits ~13 chars a line)
RAIL_GAP = 13  # chart area → rail
RAIL_BG = "rgb(242,242,242)"
RULE_GREY = "rgb(204,204,204)"
RAIL_SHADOW = '<shadow color="rgba(0,0,0,0.12)" offset="3" blur="10" angle="90"/>'   # soft drop shadow under the white card
CAPTION = "rgb(102,102,102)"
BODY = "rgb(51,51,51)"
BODY_PT = 14  # every prose block (takeaways, steps, kv, notes, bullets, column text)
HEAD_PT = 15  # bold heads over prose
RESEARCH_PT = 12  # business-research reading decks: tables / rail evidence / kv / notes may pass size down to this
CHART_SLOTS: list = []  # chart slots reserved by page layouts since the last publish (publish: each needs a chart)
SLOT_TITLES: dict = {}  # (w, h) of a titled chart slot → its title ("储能毛利率，%"): the Exhibit drawn there reads its unit
RAIL_TEXT: list = []    # per rail: [(n, head + body)] of the numbered takeaways (publish finds their numbers on the chart)
RAIL_NUMS: list = []    # key_takeaways numbers per rail built since the last publish (publish matches them to num_dot)
KPI_LINKS: list = []    # kpi_charts_page [(value text, chart index)] since the last publish
CLAIMS: list = []       # judgement lines over the panels of the page being built (chart blocks / ex.panel(claim=))
PROFILE = {"research": False, "speech": False}   # set by frame() for the page being built (research = business-research,
#                                                  speech = business-deck)


def image_inset(src, source_path, box):
    """Native image XML centered in an (x, y, width, height) slot without cropping the source."""
    try:
        left, top, width, height = map(float, box)
    except (TypeError, ValueError):
        raise ValueError("image_inset 图窗为 (x,y,width,height)") from None
    if not all(math.isfinite(value) for value in (left, top, width, height)) or min(width, height) <= 0:
        raise ValueError("image_inset 图窗坐标须有限，宽高须为正")
    dimensions = image_size(source_path)
    if not dimensions or min(dimensions) <= 0:
        raise ValueError("image_inset 无法读取有效原图尺寸；使用原始 PNG/JPEG/GIF/WebP 文件")
    source_width, source_height = dimensions
    scale = min(width / source_width, height / source_height)
    image_width, image_height = source_width * scale, source_height * scale
    image_left = left + (width - image_width) / 2
    image_top = top + (height - image_height) / 2
    return (f'<img src="{escape(str(src), quote=True)}" topLeftX="{image_left:.6f}" '
            f'topLeftY="{image_top:.6f}" width="{image_width:.6f}" height="{image_height:.6f}"/>')


def _th(content_xml, width, size):
    """Height the server lint will measure for a <content> block (falls back to a wrap estimate)."""
    import sys as _s
    from pathlib import Path as _P

    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from _exhibit_text_fit import text_height

        return text_height(content_xml, width=round(width), font_size=size)
    except Exception:  # noqa: BLE001
        plain = re.sub(r"<[^>]+>", "", content_xml)
        return len(wrap(plain, size, width)) * size * 1.35 + 6
    finally:
        _s.path.pop(0)


def _label_width(text, size, font, bold=False):
    import sys as _s
    from pathlib import Path as _P

    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from _exhibit_text_fit import label_width

        return label_width(text, font_size=size, bold=bold, font_family=font)
    finally:
        _s.path.pop(0)


def _zh(*texts):
    return any(has_cjk(str(t or "")) for t in texts)


def _palette(palette, frame=None):
    return dict(frame.C) if palette is None and frame is not None else roles(palette)


def min_prose_pt():
    """Smallest prose size for the page being built: RESEARCH_PT on business-research decks, else BODY_PT."""
    return RESEARCH_PT if PROFILE.get("research") else BODY_PT


def _prose_size(size):
    floor = min_prose_pt()
    if size < floor:
        raise ValueError(f"正文至少 {floor:g}pt：删字、加宽或拆页，不缩字号")


def _rule(x, y, w, color, width=1):
    return (
        f'<line startX="{x:.0f}" startY="{y:.0f}" endX="{x + w:.0f}" endY="{y:.0f}">'
        f'<border color="{_c(color)}" width="{width}"/></line>'
    )


def _rect(x, y, w, h, fill):
    return (
        f'<shape type="rect" topLeftX="{x:.0f}" topLeftY="{y:.0f}" width="{w:.0f}" height="{h:.0f}">'
        f'<fill><fillColor color="{_c(fill)}"/></fill></shape>'
    )


def _head_body(head, body, size, head_size, ink, font, bullet=True, head_color=None, compact=False):
    """<content> paragraphs: '• head' (bold, head_size) on one paragraph, body (size, grey-black) below.
    compact: tighter line spacing (1.05 / 1.15) — the last step a crowded research rail takes before refusing."""
    hc = _c(head_color or ink)
    lh, lb = ("1.05", "1.15") if compact else ("1.15", "1.25")
    paras = ""
    if head:
        paras += (
            f'<p lineSpacing="multiple:{lh}"><span bold="true" fontSize="{head_size}" color="{hc}">'
            f"{'• ' if bullet else ''}{escape(head)}</span></p>"
        )
    if body:
        paras += f'<p lineSpacing="multiple:{lb}"><span fontSize="{size}" color="{BODY}">{escape(body)}</span></p>'
    return f'<content fontSize="{size}" fontFamily="{font}" color="{BODY}" textAlign="left" verticalAlign="top">{paras}</content>'


def rail_x(f=None):
    """Left x of the key-takeaways rail; the chart / body to its left ends at rail_x − RAIL_GAP."""
    return (f.right if f is not None else W - X0) - RAIL_W


def body_w(f=None, rail=None):
    """Width left for the chart / columns when the page carries a key_takeaways rail (rail=True) or not. rail=None:
    with a rail, except on business-deck (speech) pages, where charts take the full width unless rail=True."""
    left = f.left if f is not None else X0
    right = f.right if f is not None else W - X0
    if rail is None:
        rail = not PROFILE.get("speech")   # business-deck (speech): no takeaways rail by default
    return (rail_x(f) - RAIL_GAP - left) if rail else (right - left)


def key_takeaways(
    f,
    items,
    label=None,
    x=None,
    w=RAIL_W,
    top=None,
    bottom=None,
    palette=None,
    font="思源黑体",
    size=BODY_PT,
    head_size=HEAD_PT,
    accent_item=None,
    _compact=False,
):
    """Key-takeaways rail at the right of the chart (McKinsey style): a white card with a hairline border and a soft
    shadow, a bold "关键要点 / Key takeaways" head over a main-colour rule, then 2–4 items — bold head (one claim,
    ≤2 lines) + body (the evidence: numbers, source, 2–5 lines) — each behind the same small main-colour square, split
    by grey hairlines. One look for every item: no numbers, no accent-coloured head (a colour the chart does not use
    means nothing). Each takeaway ties to the chart by naming what it talks about (the year / object / segment) and
    quoting its reading; the chart marks that element (focus=, band / dashed_box, CAGR / diff label).
    business-deck (set_profile("deck")): no card, a 1px left rule.
    label: the card head — write one that names what the rail is about (≤10 字, e.g. "增长从哪来" / "盈利三点变化" /
    "对投资者的含义"); default "关键要点" / "Key takeaways" when omitted.
    items: [(head, body)] (a third field from older calls is ignored). accent_item: ignored (older calls).
    The rail spans f.top–f.bottom at the right edge (x defaults to rail_x()); place the chart in body_w(f) to its left.
    Returns xml. A research rail that overflows first drops to 12pt (the evidence floor), then tightens line spacing and
    item gaps; it raises only when the text still does not fit: cut the bodies, not the font. The card stays the same."""
    _block("key_takeaways")
    def _kt(it):   # (head, body): numbers / marks of older calls dropped; a str is one head, a dict its head/body values
        if isinstance(it, str):
            return (it, "")
        if isinstance(it, dict):
            vals = [it.get(k) for k in ("head", "title", "label", "claim", "结论") if it.get(k)] or list(it.values())[:1]
            body = [it.get(k) for k in ("body", "text", "evidence", "detail", "证据") if it.get(k)] or list(it.values())[1:2]
            return (str(vals[0]) if vals else "", str(body[0]) if body else "")
        return tuple((list(it) + [""])[:2])
    items = [_kt(it) for it in items]
    RAIL_NUMS.append([])
    RAIL_TEXT.append([(k + 1, f"{h} {b}") for k, (h, b) in enumerate(items)])
    _prose_size(size)
    head_size = max(size + 1, head_size)
    C = _palette(palette, f)
    top = f.top if top is None else top
    bottom = f.bottom if bottom is None else bottom
    x = rail_x(f) if x is None else x
    if w <= 24 or bottom <= top:
        raise ValueError("key_takeaways 需要正的可用宽高")
    if len(items) > 4:   # keep the first four (the ones the chart's dots 1–4 point at); the rest would not fit anyway
        print(f"key_takeaways：{len(items)} 条只保留前 4 条（其余并进证据或删掉）")
        items = list(items)[:4]
        RAIL_TEXT[-1] = RAIL_TEXT[-1][:4]
    if not 2 <= len(items) <= 4:
        raise ValueError("key_takeaways 写 2–4 条（每条 = 加粗结论 + 证据正文）")
    label = label or ("关键要点" if _zh(*[t for it in items for t in it]) else "Key takeaways")
    if len(str(label)) > 14:
        raise ValueError(f"key_takeaways(label=)：卡头 {label!r} 太长——≤10 字，写这栏讲什么（如'增长从哪来'），结论放进条目")
    pad = 12
    iw = w - 2 * pad
    speech = PROFILE.get("speech")   # business-deck: no panel — a 1px main-colour left rule (deck skeleton)
    out = [f'<line startX="{x:.0f}" startY="{top:.0f}" endX="{x:.0f}" endY="{bottom:.0f}">'
           f'<border color="{_c(C["main"])}" width="1"/></line>' if speech else
           f'<shape type="rect" topLeftX="{x:.0f}" topLeftY="{top:.0f}" width="{w:.0f}" height="{bottom - top:.0f}">'
           f'<fill><fillColor color="rgb(255,255,255)"/></fill><border color="{RULE_GREY}" width="1"/>{RAIL_SHADOW}</shape>']
    label_content = f'<content fontSize="{HEAD_PT}" fontFamily="{font}"><p>{escape(label)}</p></content>'
    label_height = _th(label_content, iw, HEAD_PT)
    out.append(_box(x + pad, top + 10, iw, label_height, f"<p>{escape(label)}</p>", HEAD_PT,
                    C["ink"] if speech else C["deep"], font, bold=True))
    start = top + 10 + label_height + 14
    if not speech:   # main-colour rule under the head (McKinsey "[Key takeaways]" + navy line)
        out.append(_rule(x + pad, start - 8, iw, C["main"], 2))
    avail = bottom - start - 8
    mark_w = 0 if speech else 16   # hanging main-colour square: every item's text on one left edge
    hs = [_th(_head_body(h, b, size, head_size, C["ink"], font, bullet=speech, compact=_compact), iw - mark_w, size) + 2
          for h, b in items]
    gap = (avail - sum(hs)) / len(items)
    if gap < 14:
        need = sum(hs) + 14 * len(items)
        if need <= avail * (1 + SQUEEZE_MAX) and gap >= (3 if _compact else 4):   # small overflow: tighter gaps, same font
            _squeezed(f"key_takeaways 超出 {need - avail:.0f}px（≤{SQUEEZE_MAX:.0%}）：已把条目间距压到 {gap:.0f}px；"
                      "想更松就删几字")
        elif PROFILE.get("research") and (size > 12 or not _compact):
            # research rail: drop to the 12pt evidence size, then tighten line spacing / gaps, before refusing (each
            # refusal cost the page a full rewrite); the card itself (white, border, shadow) never changes
            RAIL_NUMS.pop()
            RAIL_TEXT.pop()
            from ._page import BLOCKS
            BLOCKS.pop()
            if size > 12:
                print(f"key_takeaways 超出 {need - avail:.0f}px：已改用 12 号字（研究稿要点证据下限）")
                return key_takeaways(f, items, label=label, x=x, w=w, top=top, bottom=bottom, palette=palette,
                                     font=font, size=12, head_size=min(head_size, 13), accent_item=accent_item)
            print(f"key_takeaways 12 号字仍超出 {need - avail:.0f}px：已收紧行距和条目间距；想更松就删几字")
            return key_takeaways(f, items, label=label, x=x, w=w, top=top, bottom=bottom, palette=palette, font=font,
                                 size=12, head_size=12, accent_item=accent_item, _compact=True)
        else:
            chars = sum(len(str(a)) + len(str(b)) for a, b, *_ in [(list(it) + [""])[:2] for it in items])
            raise ValueError(
                f"key_takeaways 放不下：需要高 {need:.0f}px，只有 {avail:.0f}px（{len(items)} 条、{chars} 字，超出"
                f" {need / avail - 1:.0%}）——正文删到约 {int(chars * avail / need * 0.9)} 字，或减到 {max(2, len(items) - 1)} 条；"
                "证据多到删不动就拆成 a/b 两页（每页 2–3 条，plan 加一行交另一个 builder 并行）"
            )
    gap = min(gap, 40)
    cy = start + min(gap * 0.5, 14)
    for i, (head, body) in enumerate(items):
        tx = x + pad + mark_w
        if not speech:   # the same small main-colour square before every item
            out.append(f'<shape type="rect" topLeftX="{x + pad + 1:.0f}" topLeftY="{cy + 6:.0f}" width="7" height="7">'
                       f'<fill><fillColor color="{_c(C["main"])}"/></fill></shape>')
        out.append(
            f'<shape type="text" topLeftX="{tx:.0f}" topLeftY="{cy:.0f}" width="{iw - mark_w:.0f}" '
            f'height="{hs[i]:.0f}">{_head_body(head, body, size, head_size, C["ink"], font, bullet=speech, head_color=C["ink"], compact=_compact)}</shape>'
        )
        cy += hs[i]
        if i < len(items) - 1:
            out.append(_rule(x + pad, cy + gap / 2 - 1, iw, RULE_GREY, 1))
            cy += gap
    return "".join(out)


def section_head(x, y, w, text, palette=None, font="思源黑体", size=BODY_PT, rule=True, sup=None):
    """Bold block title over a column ("指标，单位" or a one-line claim) with a black rule under it.
    Returns (xml, y_below) — y_below is where the column's content starts."""
    C = roles(palette)
    s = (
        f'<p><span bold="true" color="{_c(C["deep"])}">{escape(text)}</span>'
        + (f'<span fontSize="9" color="{_c(C["deep"])}">{escape(str(sup))}</span>' if sup else "")
        + "</p>"
    )
    h = _th(f'<content fontSize="{size}" fontFamily="{font}">{s}</content>', w, size)
    out = _box(x, y, w, h, s, size, C["deep"], font)
    yb = y + h + 2
    if rule:
        out += _rule(x, yb, w, C["ink"], 1)
        yb += 6
    return out, yb


def stat_stack(x, y, w, items, h=None, palette=None, font="思源黑体", big=28, size=BODY_PT):
    """Column of 2–4 stats: serif big number (Georgia, value + unit) over a grey caption (what it is, basis,
    source), grey rules between — the column next to a diagram or photo. items: [(value, caption)] or
    [(value, unit, caption)]. h: column height to spread over. Returns (xml, bottom)."""
    _prose_size(size)
    C = roles(palette)
    rows = []
    for it in items:
        if isinstance(it, str):   # "26Q2 收入：968 亿（+10.1%）": big number = the first figure, caption = the sentence
            m = (re.search(r"[+\-−]?\d[\d,]*(?:\.\d+)?\s*(?:%|倍|x|亿|万|元|pt|个|家)", it)
                 or re.search(r"[+\-−]?\d[\d,]*(?:\.\d+)?(?![\dQH年月季E])", it))
            it = [m.group(0).strip(), "", it] if m else ["", "", it]
        elif isinstance(it, dict):
            it = [it.get("value", ""), it.get("unit", ""), it.get("label", it.get("caption", ""))]
        it = list(it)
        val, unit, cap = (it + [""])[:3] if len(it) >= 3 else (it[0], "", it[1] if len(it) > 1 else "")
        rows.append((str(val), str(unit), str(cap)))
    hs = []
    for val, unit, cap in rows:
        bs = big
        from ._text import tw

        while bs > 18 and tw(val, bs, bold=True) * 1.1 + tw(" " + unit, 16, bold=True) > w - 6:
            bs -= 2
        cap_h = (
            _th(
                f'<content fontSize="{size}" fontFamily="{font}"><p lineSpacing="multiple:1.25">{escape(cap)}</p></content>',
                w,
                size,
            )
            if cap
            else 0
        )
        number = (
            f'<p><span fontFamily="Georgia" fontSize="{bs}" bold="true">{escape(val)}</span>'
            + (f'<span fontSize="16" bold="true"> {escape(unit)}</span>' if unit else "")
            + "</p>"
        )
        number_h = _th(f'<content fontSize="{bs}" fontFamily="{font}">{number}</content>', w, bs) if val else 0
        hs.append((bs, number_h, cap_h))
    need = sum(b + c + 6 for _, b, c in hs)
    h = h or need + 28 * (len(rows) - 1)
    if need > h:
        raise ValueError(f"stat_stack 放不下：需要 {need:.0f}px，只有 {h:.0f}px——说明文字缩短或减少一项")
    gap = (h - need) / max(len(rows) - 1, 1) if len(rows) > 1 else 0
    gap = min(gap, 60)
    out, cy = [], y
    for i, ((val, unit, cap), (bs, bh, ch)) in enumerate(zip(rows, hs)):
        num = (
            f'<p><span fontFamily="Georgia" fontSize="{bs}" bold="true" color="{_c(C["deep"])}">{escape(val)}</span>'
            + (f'<span fontSize="16" bold="true" color="{_c(C["deep"])}"> {escape(unit)}</span>' if unit else "")
            + "</p>"
        )
        if val:
            out.append(_box(x, cy, w, bh, num, bs, C["deep"], font))
            cy += bh + 4
        if cap:
            out.append(_box(x, cy, w, ch, f'<p lineSpacing="multiple:1.25">{escape(cap)}</p>', size, CAPTION, font))
        cy += ch + 2
        if i < len(rows) - 1:
            out.append(_rule(x, cy + gap / 2, w, RULE_GREY, 1))
            cy += gap
    return "".join(out), cy


def kv_rows(x, y, w, rows, h=None, palette=None, font="思源黑体", size=BODY_PT, label_frac=None, header=None, focus=None,
            row_pad=12):
    """Parameter table inside a column: each row "label (grey-black) | value (bold, right)" between grey rules, a
    black rule on top. rows: [(label, value)]; header: optional (label_head, value_head) in grey caps.
    Labels and values share width according to their content; narrow narrative rows use full-width stacked cells.
    label_frac fixes the split explicitly. focus=k accents row k's value. Returns (xml, bottom)."""
    _prose_size(size)
    if w <= 32 or (label_frac is not None and not 0 < label_frac < 1):
        raise ValueError("kv_rows 需要足够宽度，label_frac 必须在 0 与 1 之间")
    C = roles(palette)
    stacked = False
    if label_frac is None:
        label_need = max((_label_width(label, size, font) for label, _ in rows), default=0)
        value_need = max((_label_width(value, size, font, bold=True) for _, value in rows), default=0)
        if header:
            label_need = max(label_need, _label_width(header[0], 12, font, bold=True))
            value_need = max(value_need, _label_width(header[1], 12, font, bold=True))
        stacked = label_need + value_need + 16 > w
        lw = max(label_need + 8, min(w / 2, w - value_need - 8))
    else:
        lw = w * label_frac
    vw = w - lw - 8
    out, cy = [], y
    if header:
        header_h = _th(
            f'<content fontSize="12" fontFamily="{font}" bold="true"><p>{escape(" / ".join(map(str, header)))}</p></content>',
            w - 8,
            12,
        ) if stacked else max(
            _th(
                f'<content fontSize="12" fontFamily="{font}" bold="true"><p>{escape(str(text))}</p></content>',
                width,
                12,
            )
            for text, width in zip(header, (lw - 8, vw))
        )
        if stacked:
            out.append(_box(x + 4, cy, w - 8, header_h, f'<p>{escape(" / ".join(map(str, header)))}</p>',
                            12, CAPTION, font, bold=True))
        else:
            out.append(_box(x + 4, cy, lw - 8, header_h, f"<p>{escape(header[0])}</p>", 12, CAPTION, font, bold=True))
            out.append(
                _box(x + lw, cy, vw, header_h, f"<p>{escape(header[1])}</p>", 12, CAPTION, font, bold=True, align="right")
            )
        cy += header_h + 4
    out.append(_rule(x, cy, w, C["ink"], 1))
    need = []
    for lab, val in rows:
        a = _th(f'<content fontSize="{size}" fontFamily="{font}"><p>{escape(str(lab))}</p></content>',
                w - 8 if stacked else lw - 8, size)
        b = _th(
            f'<content fontSize="{size}" fontFamily="{font}" bold="true"><p>{escape(str(val))}</p></content>',
            w - 8 if stacked else vw,
            size,
        )
        need.append((a + b + row_pad + 4, a, b) if stacked else (max(a, b) + row_pad, a, b))
    tot = cy - y + sum(row[0] for row in need)
    extra = max(0.0, ((h or tot) - tot) / max(len(rows), 1))
    extra = min(extra, 22)
    for i, ((lab, val), (nh, label_h, value_h)) in enumerate(zip(rows, need)):
        rh = nh + extra
        vc = C["accent"] if focus == i else C["deep"]
        if stacked:
            out.append(_box(x + 4, cy + 4, w - 8, label_h, f"<p>{escape(str(lab))}</p>", size, BODY, font))
            out.append(_box(x + 4, cy + label_h + 8, w - 8, value_h + extra,
                            f'<p><span bold="true" color="{_c(vc)}">{escape(str(val))}</span></p>',
                            size, vc, font))
            cy += rh
            out.append(_rule(x, cy, w, RULE_GREY if i < len(rows) - 1 else C["ink"], 1))
            continue
        out.append(_box(x + 4, cy + 4, lw - 8, rh - 6, f"<p>{escape(str(lab))}</p>", size, BODY, font, valign="middle"))
        out.append(
            _box(
                x + lw,
                cy + 4,
                vw,
                rh - 6,
                f'<p><span bold="true" color="{_c(vc)}">{escape(str(val))}</span></p>',
                size,
                vc,
                font,
                align="right",
                valign="middle",
            )
        )
        cy += rh
        out.append(_rule(x, cy, w, RULE_GREY if i < len(rows) - 1 else C["ink"], 1))
    if h and cy - y > h + 1:
        raise ValueError(f"kv_rows 超高 {cy - y - h:.0f}px：减少行数或缩短标签/数值")
    return "".join(out), cy


def note_box(x, y, w, text, lead=None, palette=None, font="思源黑体", size=BODY_PT, h=None):
    """Light grey box with a 3px dark left bar: one framed sentence under a chart or table (the arithmetic behind
    it, the comparable basis, "so the gap is …"). lead: optional bold opening words. Returns (xml, bottom)."""
    _block("note_box")
    _prose_size(size)
    C = roles(palette)
    body = (f'<span bold="true" color="{_c(C["deep"])}">{escape(lead)} </span>' if lead else "") + escape(text)
    content = f'<content fontSize="{size}" fontFamily="{font}" color="{BODY}"><p lineSpacing="multiple:1.3">{body}</p></content>'
    th = _th(content, w - 22, size)
    bh = max(h or 0, th + 12)
    out = _rect(x, y, w, bh, RAIL_BG) + _rect(x, y, 3, bh, C["deep"])
    out += (
        f'<shape type="text" topLeftX="{x + 11:.0f}" topLeftY="{y + 5:.0f}" width="{w - 20:.0f}" height="{bh - 8:.0f}">'
        f"{content.replace('<content ', '<content verticalAlign=' + chr(34) + 'middle' + chr(34) + ' ', 1)}</shape>"
    )
    return out, y + bh


def dot_bullets(x, y, w, items, palette=None, font="思源黑体", size=BODY_PT, gap=8, h=None):
    """Evidence lines with small coloured dots (5px): items [text] or [(text, colour_role)] — dot colour = the chart
    element it talks about (main / accent / context). Returns (xml, bottom)."""
    _prose_size(size)
    C = roles(palette)
    out, cy = [], y
    hs = []
    for it in items:
        t = it[0] if isinstance(it, (tuple, list)) else it
        hs.append(
            _th(
                f'<content fontSize="{size}" fontFamily="{font}"><p lineSpacing="multiple:1.25">{escape(str(t))}</p></content>',
                w - 12,
                size,
            )
        )
    if h:
        free = h - sum(hs) - gap * max(len(items) - 1, 0)
        if free < 0:
            raise ValueError(f"dot_bullets 放不下：需要 {sum(hs):.0f}px，只有 {h:.0f}px——删字或减少条数")
        gap = min(gap + free / max(len(items) - 1, 1), 28) if len(items) > 1 else gap
    for it, th in zip(items, hs):
        t, role = (it[0], it[1]) if isinstance(it, (tuple, list)) else (it, "main")
        col = C.get(role) or role
        out.append(
            f'<shape type="ellipse" topLeftX="{x:.0f}" topLeftY="{cy + size * 0.55:.0f}" width="6" height="6">'
            f'<fill><fillColor color="{_c(col)}"/></fill></shape>'
        )
        out.append(
            _box(x + 12, cy, w - 12, th, f'<p lineSpacing="multiple:1.25">{escape(str(t))}</p>', size, BODY, font)
        )
        cy += th + gap
    return "".join(out), cy - gap


def numbered_steps(x, y, w, items, h=None, palette=None, font="思源黑体", size=BODY_PT, head_size=HEAD_PT, rule=True):
    """Mechanism / chain list: per step a 16px dark numbered circle, an optional IconPark icon (27px), a bold head
    (the step's claim) and a body (the evidence), grey rules between. items: [(head, body)] or [(head, body, icon)]
    with icon an iconType from iconpark_tool.py search. Spread over h. Returns (xml, bottom)."""
    _prose_size(size)
    C = roles(palette)
    # a plain string step ("Solid-state 2027") is a head without body — not a sequence of characters
    items = [(it,) if isinstance(it, str) else tuple(it) for it in items]
    has_icon = any(len(it) > 2 and it[2] for it in items)
    tx = x + (64 if has_icon else 28)
    tw_ = w - (tx - x)
    contents = [
        _head_body(it[0], it[1] if len(it) > 1 else "", size, head_size, C["deep"], font, bullet=False) for it in items
    ]
    hs = [_th(c, tw_, size) + 2 for c in contents]
    need = sum(hs)
    h = h or need + 18 * len(items)
    if need > h:
        raise ValueError(f"numbered_steps 放不下：需要 {need:.0f}px，只有 {h:.0f}px——每步正文删到 2 行以内或减少步骤")
    gap = min((h - need) / max(len(items), 1), 40)
    out, cy = [], y + gap / 2
    for i, (it, c, hh) in enumerate(zip(items, contents, hs), 1):
        out.append(
            f'<shape type="ellipse" topLeftX="{x:.0f}" topLeftY="{cy + 2:.0f}" width="16" height="16">'
            f'<fill><fillColor color="{_c(C["deep"])}"/></fill></shape>'
        )
        digit_h = _th(f'<content fontSize="9" fontFamily="{font}" bold="true"><p>{i}</p></content>', 16, 9)
        out.append(
            _box(x, cy + 2, 16, digit_h, f"<p>{i}</p>", 9, "#FFFFFF", font, bold=True, align="center", valign="middle")
        )
        if has_icon and len(it) > 2 and it[2]:
            out.append(
                f'<icon iconType="{escape(_icon_type(it[2], "numbered_steps icon"))}" topLeftX="{x + 26:.0f}" '
                f'topLeftY="{cy:.0f}" width="26" height="26"><fill><fillColor color="{_c(C["deep"])}"/></fill></icon>'
            )
        out.append(
            f'<shape type="text" topLeftX="{tx:.0f}" topLeftY="{cy:.0f}" width="{tw_:.0f}" height="{hh:.0f}">{c}</shape>'
        )
        cy += hh
        if rule and i < len(items):
            out.append(_rule(x, cy + gap / 2, w, RULE_GREY, 1))
        cy += gap
    return "".join(out), cy - gap / 2


def column_boxes(n, x=None, y=None, w=None, h=None, gap=14):
    """[(x, y, w, h)] of 1–4 equal columns over the given band (default: full body width)."""
    x = X0 if x is None else x
    w = (W - 2 * X0) if w is None else w
    if not isinstance(n, int) or not 1 <= n <= 4 or gap < 0 or w <= gap * (n - 1) or (h is not None and h <= 0):
        raise ValueError("column_boxes 需要 1–4 栏、非负间距和正的可用宽高")
    cw = (w - gap * (n - 1)) / n
    return [(x + i * (cw + gap), y, cw, h) for i in range(n)]


def _icon_badge(x, y, icon, C, size=24):
    t = _icon_type(icon, "columns_page icon")
    return (
        f'<shape type="ellipse" topLeftX="{x:.0f}" topLeftY="{y:.0f}" width="{size}" height="{size}">'
        f'<fill><fillColor color="{_c(C["band_bg"])}"/></fill></shape>'
        f'<icon iconType="{escape(t)}" topLeftX="{x + 5:.0f}" topLeftY="{y + 5:.0f}" width="{size - 10}" '
        f'height="{size - 10}"><fill><fillColor color="{_c(C["deep"])}"/></fill></icon>'
    )


class _Overflow(Exception):
    def __init__(self, need, avail, heavy):
        super().__init__(f"{need:.0f}>{avail:.0f}")
        self.need, self.avail, self.heavy = need, avail, heavy


def columns_page(
    f, columns, top=None, bottom=None, gap=13, card=None, palette=None, font="思源黑体", x=None, w=None, focus=None
):
    """2–4 parallel columns: matching block stacks align their rows; different stacks only reserve their own blocks.
    columns: list of dicts with any of
      kicker  small grey caption over the title ("模式 ① · 自供" / "Gap source ①"); icon: IconPark iconType beside it
      title   bold 17pt column name ("比亚迪" / "制造代差")
      big     ("40–50%", "unit or None") serif 28pt headline number of the column
      text    2–4 lines of explanation (16pt minimum)
      kv      [(label, value)] parameter rows (kv_rows)
      chart   (height, "图表标题，单位") — reserves a slot; the box comes back in slots[i] for ex.to_slide(x, y)
      dots    [text | (text, role)] evidence bullets
      note    one framed sentence at the bottom (note_box)
    Matching stacks use each row's tallest height. Different stacks retain aligned heads and compact nonchart
    columns. card=True (default when any column has big / chart) draws grey card backgrounds; focus=k marks column k.
    Returns (xml, slots) — slots[i] = (x, y, w, h) of column i's chart slot or None."""
    C = _palette(palette, f)
    palette = {"exhibit": C}
    C.setdefault("band_bg", "rgb(227,236,244)")
    top = f.top if top is None else top
    bottom = f.bottom if bottom is None else bottom
    n = len(columns)
    if not 2 <= n <= 4:
        raise ValueError("columns_page 写 2–4 栏（同构对比：每栏同样的块、同样的顺序）")
    if PROFILE.get("research"):
        bare = [i + 1 for i, c in enumerate(columns) if not c.get("chart")]
        if n >= 4 and not bare:
            raise ValueError("columns_page 4 栏都放图，每张图只剩约 100px 宽，标签必然互压：减到 2–3 栏，"
                             "或把 4 个对象放进一张 row_table / small_multiples")
        if len(bare) == n:
            raise ValueError("columns_page 没有一栏有图（business-research 分栏页至少一栏要有小图）：给主栏加 "
                             "chart=(高度, \"图表标题，单位\") 并在返回的 slots[i] 里画同口径小图（≥4 个数据点：近 5 年或多个对象）；"
                             "只有文字和数字的对比改用 row_table（每行一个对象、带 Bar / Dumbbell 列）")
    card = any(c.get("big") or c.get("chart") for c in columns) if card is None else card
    x = f.left if x is None else x
    w = f.right - x if w is None else w
    boxes = column_boxes(n, x=x, y=top, w=w, h=bottom - top, gap=gap)
    pad = 12 if card else 0
    order = ("head", "big", "text", "kv", "chart", "dots", "note")
    present = [
        b for b in order if any((c.get(b) if b != "head" else (c.get("title") or c.get("kicker"))) for c in columns)
    ]
    iw = boxes[0][2] - 2 * pad
    sq = {"kv_pad": 12, "dot_gap": 8, "chart_cut": 0.0}   # compression knobs (small overflow only; fonts never change)

    def h_of(c, b):
        if b == "head":
            kicker_w = iw - (30 if c.get("icon") else 0)
            k = (
                _th(f'<content fontSize="12" fontFamily="{font}"><p>{escape(c["kicker"])}</p></content>', kicker_w, 12)
                + 6
                if c.get("kicker")
                else 0
            )
            t = (
                _th(
                    f'<content fontSize="{HEAD_PT}" fontFamily="{font}" bold="true"><p>{escape(c.get("title", ""))}</p></content>',
                    iw,
                    HEAD_PT,
                )
                if c.get("title")
                else 0
            )
            return k + 4 + t + 8
        if b == "big":
            if not c.get("big"):
                return 0
            value = c["big"] if isinstance(c["big"], (tuple, list)) else (c["big"], "")
            return stat_stack(0, 0, iw, [(value[0], value[1] or "", "")], palette=palette, font=font)[1] + 4
        if b == "text":
            return (
                _th(
                    f'<content fontSize="{BODY_PT}" fontFamily="{font}"><p lineSpacing="multiple:1.25">{escape(c.get("text", ""))}</p></content>',
                    iw,
                    14,
                )
                + 6
                if c.get("text")
                else 0
            )
        if b == "kv":
            rows = c.get("kv") or []
            return kv_rows(0, 0, iw, rows, palette=palette, font=font, row_pad=sq["kv_pad"])[1] + 6 if rows else 0
        if b == "chart":
            ch = c.get("chart")
            if not ch:
                return 0
            chart_h = ch[0] if isinstance(ch, (tuple, list)) else ch
            chart_h -= min(sq["chart_cut"], max(0.0, chart_h - max(CHART_MIN_PX, CHART_MIN_SHARE * chart_h)))
            title = ch[1] if isinstance(ch, (tuple, list)) and len(ch) > 1 else ""
            title_h = (
                _th(f'<content fontSize="{BODY_PT}" fontFamily="{font}" bold="true"><p>{escape(title)}</p></content>', iw, BODY_PT)
                + 6
                if title
                else 0
            )
            return chart_h + title_h + 4
        if b == "dots":
            return (
                sum(
                    _th(
                        f'<content fontSize="{BODY_PT}" fontFamily="{font}"><p lineSpacing="multiple:1.25">{escape(str(d[0] if isinstance(d, (tuple, list)) else d))}</p></content>',
                        iw - 12,
                        14,
                    )
                    + sq["dot_gap"]
                    for d in (c.get("dots") or [])
                )
                if c.get("dots")
                else 0
            )
        if b == "note":
            return note_box(0, 0, iw, c["note"], palette=palette, font=font)[1] + 8 if c.get("note") else 0
        return 0

    def fit_rows(block_heights, block_names, compact=False):
        need = sum(block_heights.values()) + 2 * pad + (4 if not card else 0)
        avail = bottom - top
        if need > avail + 1:
            raise _Overflow(need, avail, max(block_heights, key=block_heights.get))
        if compact and "chart" not in block_heights:
            return block_heights, top + need, 0
        layout_bottom = bottom
        spare = avail - need
        grow = [block for block in ("chart", "kv", "dots", "text") if block in block_heights]
        gap_between = min(spare / max(len(block_names), 1), 14) if not grow else 0
        if grow and "chart" not in block_heights:
            cap = {block: (len(max((column.get("kv") or [] for column in columns), key=len)) * 22
                           if block == "kv" else 0) for block in grow}
            cap["dots"] = 40 if "dots" in grow else 0
            for block in grow:
                take = min(cap.get(block, 0), spare)
                block_heights[block] += take
                spare -= take
            if spare > 0:
                gap_between = min(spare / max(len(block_names), 1), 14)
                spare -= gap_between * len(block_names)
            if spare > 0.12 * avail:
                layout_bottom -= spare
                SHORT.append(f"columns_page 内容只占栏高 {(avail - spare) / avail:.0%}，栏已缩到内容高度、下方空出 {spare:.0f}px："
                             "每栏补 2–3 行 text、4–6 行 kv 或 dots 证据，或让图表填满")
        elif grow:
            block_heights["chart"] += spare
        return block_heights, layout_bottom, gap_between

    def stretch(column, blocks, row, target):
        """A column shorter than the tallest one grows to its bottom (the card / rule spans the same height): kv rows
        open up by ≤ STRETCH_ROW_MAX each, blocks get even gaps (≤ 14px), a closing note sits at the column foot when
        that leaves ≤ NOTE_PIN_MAX above it. Dot lists keep their own spacing (spread dots read as unrelated lines).
        What is left stays as white at the column foot — content top-aligned, never spread into tall rows.
        Returns (heights, bottom, gap, air above the note, left)."""
        heights, col_bottom, gap_ = dict(row[0]), row[1], row[2]
        spare = target - col_bottom
        if spare <= 1:
            return heights, col_bottom, gap_, 0.0, 0.0
        if "kv" in heights:
            take = min(spare, len(column.get("kv") or []) * STRETCH_ROW_MAX)
            heights["kv"] += take
            spare -= take
        if spare > 0 and len(blocks) > 1:
            gap_ = min(spare / (len(blocks) - 1), 14)
            spare -= gap_ * (len(blocks) - 1)
        lift = 0.0
        if "note" in blocks and blocks.index("note") > 0 and 0 < spare <= NOTE_PIN_MAX:
            lift, spare = spare, 0.0   # the framed sentence sits at the column's foot, level with its neighbours
        # the blank-column note keeps its old measure (rows opened to 22px, dots to 20px, a note pinned to the foot):
        # leaving that air white instead of spreading it is a look, not a new reason to send the page back
        old_left = target - col_bottom - len(column.get("kv") or []) * 22 - max(len(column.get("dots") or []) - 1, 0) * 20
        if "note" in blocks and blocks.index("note") > 0:
            old_left = 0.0
        elif len(blocks) > 1:
            old_left -= min(max(old_left, 0.0) / (len(blocks) - 1), 14) * (len(blocks) - 1)
        return heights, target, gap_, lift, max(old_left, 0.0)

    def layout_rows():
        if any(blocks != present for blocks in column_blocks):
            head_height = max(h_of(column, "head") for column in columns) if "head" in present else 0
            rows_ = [
                fit_rows({block: head_height if block == "head" else h_of(column, block) for block in blocks},
                         blocks, compact=True)
                for column, blocks in zip(columns, column_blocks)
            ]
            tallest = max(r_[1] for r_ in rows_)
            rows_ = [stretch(column, blocks, r_, tallest) for column, blocks, r_ in zip(columns, column_blocks, rows_)]
            short_ = [i for i, r_ in enumerate(rows_) if r_[4] > 0.25 * (bottom - top)]
            if short_:   # stretched as far as its rows allow and still far shorter than the tallest column
                SHORT.append(f"columns_page 第 {[i + 1 for i in short_]} 栏内容比最高的一栏短 "
                             f"{max(rows_[i][4] for i in short_):.0f}px（行距已拉到上限），栏内大片空白：给短栏补 kv / dots / text 证据，"
                             "或每栏都给同类块（都放小图，或都不放图）")
            return [r_[:4] for r_ in rows_]
        return [fit_rows({block: max(h_of(column, block) for column in columns) for block in present}, present)
                + (0.0,)] * n

    column_blocks = [
        [block for block in present if (
            (column.get("title") or column.get("kicker")) if block == "head" else column.get(block)
        )]
        for column in columns
    ]
    try:
        row_layouts = layout_rows()
    except _Overflow as first:
        steps = []
        if first.need <= first.avail * (1 + SQUEEZE_MAX):   # small overflow: chart height → kv rows → dot gaps
            for knob, value, label in (("chart_cut", first.need - first.avail + 2, "图高"), ("kv_pad", 6, "kv 行高"),
                                       ("dot_gap", 3, "要点间距")):
                if knob == "chart_cut" and "chart" not in present or knob == "kv_pad" and "kv" not in present \
                        or knob == "dot_gap" and "dots" not in present:
                    continue
                sq[knob] = value
                steps.append(label)
                try:
                    row_layouts = layout_rows()
                    break
                except _Overflow:
                    continue
            else:
                steps = []
        if not steps:
            kv_n = max((len(c.get("kv") or []) for c in columns), default=0)
            dots_n = max((len(c.get("dots") or []) for c in columns), default=0)
            long_n, unit = max((kv_n, "行 kv"), (dots_n, "条要点"))
            hint = (split_hint("columns_page", long_n, long_n * first.avail / first.need, unit) if long_n >= 4 else
                    f"拆成 a/b 两页（每页 {max(2, n // 2)}–{n - max(2, n // 2) or 2} 栏，或图一页、文字证据一页；plan 加一行交另一个 builder 并行做）")
            raise ValueError(
                f"columns_page 放不下：需要高 {first.need:.0f}px，只有 {first.avail:.0f}px（超出 {first.need / first.avail - 1:.0%}，"
                f"最高的块是 {first.heavy}；>{SQUEEZE_MAX:.0%} 不自动压缩）——每栏 text 删到 2–3 行、kv 减到 3–4 行、chart 高度减小，"
                "或去掉 dots / note 之一；" + hint
            ) from None
        _squeezed(f"columns_page 超出 {first.need - first.avail:.0f}px（{first.need / first.avail - 1:.0%}）：已自动压缩"
                  f"{'、'.join(steps)}，字号不变")
    out, slots = [], []
    from ._page import BLOCKS as _BL
    for i, (c, (cx, cy0, cw, chh)) in enumerate(zip(columns, boxes)):
        if not c.get("chart") and not c.get("note"):   # each parallel column is a block of the page (charts count as charts)
            _BL.append("栏")
        row_h, column_bottom, gap_between, note_lift = row_layouts[i]
        chh = column_bottom - cy0
        if card:
            out.append(_rect(cx, cy0, cw, chh, RAIL_BG))
        if focus == i:
            out.append(_rect(cx, cy0, cw, 2, C["deep"]))
        elif not card:
            out.append(_rect(cx, cy0, cw, 2, "rgb(184,196,204)"))
        x0, cy = cx + pad, cy0 + pad + (4 if not card else 0)
        slot = None
        for b in column_blocks[i]:
            rh = row_h[b]
            if b == "head":
                kx = x0
                if c.get("icon"):
                    out.append(_icon_badge(x0, cy - 2, c["icon"], C))
                    kx = x0 + 30
                if c.get("kicker"):
                    kicker_h = _th(
                        f'<content fontSize="12" fontFamily="{font}"><p>{escape(c["kicker"])}</p></content>',
                        cw - (kx - cx) - pad,
                        12,
                    )
                    out.append(
                        _box(kx, cy, cw - (kx - cx) - pad, kicker_h, f"<p>{escape(c['kicker'])}</p>", 12, CAPTION, font)
                    )
                ty = cy + (kicker_h + 6 if c.get("kicker") else 2)
                if c.get("title"):
                    out.append(
                        _box(
                            x0,
                            ty,
                            iw,
                            rh - (ty - cy) - 6,
                            f'<p><span bold="true">{escape(c["title"])}</span></p>',
                            HEAD_PT,
                            C["deep"],
                            font,
                        )
                    )
                out.append(_rule(x0, cy + rh - 3, iw, C["ink"] if not card else RULE_GREY, 1))
            elif b == "big" and c.get("big"):
                bg = c["big"] if isinstance(c["big"], (tuple, list)) else (c["big"], None)
                xml, _ = stat_stack(x0, cy, iw, [(bg[0], bg[1] or "", "")], palette=palette, font=font)
                out.append(xml)
            elif b == "text" and c.get("text"):
                out.append(
                    _box(x0, cy, iw, rh - 4, f'<p lineSpacing="multiple:1.25">{escape(c["text"])}</p>', BODY_PT, BODY, font)
                )
            elif b == "kv" and c.get("kv"):
                xml, _ = kv_rows(x0, cy, iw, c["kv"], h=rh - 6, palette=palette, font=font, size=BODY_PT,
                                 row_pad=sq["kv_pad"])
                out.append(xml)
            elif b == "chart" and c.get("chart"):
                ch = c["chart"]
                ttl = ch[1] if isinstance(ch, (tuple, list)) and len(ch) > 1 else None
                sy = cy
                if ttl:
                    title_h = _th(
                        f'<content fontSize="{BODY_PT}" fontFamily="{font}"><p><span bold="true">{escape(ttl)}</span></p></content>',
                        iw,
                        14,
                    )
                    out.append(
                        _box(x0, cy, iw, title_h, f'<p><span bold="true">{escape(ttl)}</span></p>', BODY_PT, C["deep"], font)
                    )
                    sy = cy + title_h + 6
                slot = (x0, sy, iw, rh - (sy - cy) - 4)
                CHART_SLOTS.append(slot)
                if ttl:
                    SLOT_TITLES[(round(slot[2]), round(slot[3]))] = str(ttl)
            elif b == "dots" and c.get("dots"):
                xml, _ = dot_bullets(x0, cy, iw, c["dots"], palette=palette, font=font, size=BODY_PT, gap=sq["dot_gap"],
                                     h=rh - sq["dot_gap"])
                out.append(xml)
            elif b == "note" and c.get("note"):
                cy += note_lift
                xml, _ = note_box(x0, cy + 2, iw, c["note"], palette=palette, font=font, size=BODY_PT, h=rh - 6)
                out.append(xml)
            cy += rh + gap_between
        slots.append(slot)
    return "".join(out), slots


_NUM_CELL = re.compile(r"^[~≈<>≥≤]?\s*[+\-−]?[¥$€£]?\s*\d[\d,]*(\.\d+)?(/\d+)?\s*(%|pp|x|×|倍|亿|万|bp|bps|GWh|Ah|[A-Za-z/]{0,6})?"
                       r"(\s*[-–→]\s*[~≈]?\d[\d,.]*\s*(%|x|×|pp)?)?[¹²³⁴⁵*]*$")


def table_block(x, y, w, header, rows, widths=None, h=None, icons=None, focus=None, palette=None, font="思源黑体",
                size=BODY_PT, row_pad=12):
    """Compact multi-column table inside a column: grey-caps header, black rule, rows between grey rules; first
    column bold (optionally led by an IconPark icon per row), number columns right-aligned. focus=k shades row k
    (the spot value / our row) and accent-colours its numbers. Row heights stretch to fill h.
    header: [col names]; rows: [[cells]]; icons: [iconType or None] per row. Returns (xml, bottom)."""
    _block("table_block")
    _prose_size(size)
    odd = sorted({type(c).__name__ for r in rows for c in r if not isinstance(c, (str, int, float)) and c is not None})
    if odd:   # Bar(...) / Col objects are row_table columns: table_block prints text only (they showed as "<…object at 0x…>")
        raise ValueError(f"table_block 的单元格只能是文字或数字，收到 {odd}：Bar / Range / Heat 这类图形列只在 row_table 里用"
                         "（row_table(ex, box, rows=[dict(…)], columns=[Label(…), Bar('字段', header='…')])），"
                         "table_block / mixed_columns_page 的 table 块写文字（如 f\"{v:.0f}亿\"）")
    C = roles(palette)
    n = len(header)
    from ._page import TABLES
    TABLES.append((len(rows), n))
    if n < 2 or any(len(r) != n for r in rows) or not rows:
        raise ValueError("table_block 至少 2 列 1 行，且每行列数与表头一致")
    widths = list(widths) if widths else [1.6] + [1] * (n - 1)
    if len(widths) != n or any(v <= 0 for v in widths):
        raise ValueError("table_block widths 每列一个正权重")
    blank = {"", "—", "-", "–", "n/a", "N/A", "未披露", "Nascent", "新兴"}
    right = [j > 0 and 3 * sum(bool(_NUM_CELL.match(str(r[j]).strip())) or str(r[j]).strip() in blank for r in rows)
             >= 2 * len(rows) for j in range(n)]   # a mostly-numeric column; one worded cell does not flip it
    icon_w = 30 if icons and any(icons) else 0
    cw = [w * v / sum(widths) for v in widths]
    xs = [x + sum(cw[:j]) for j in range(n)]
    pad = 8

    def cell_w(j):
        return cw[j] - pad - (icon_w if j == 0 else 0)

    out, cy = [], y
    hh = max(_th(f'<content fontSize="12" fontFamily="{font}" bold="true"><p>{escape(str(t))}</p></content>',
                 cell_w(j), 12) for j, t in enumerate(header))
    for j, t in enumerate(header):
        hx = xs[j] + (icon_w if j == 0 else 0)
        out.append(_box(hx, cy, cell_w(j), hh, f"<p>{escape(str(t))}</p>", 12, CAPTION, font, bold=True,
                        align="right" if right[j] else "left"))
    cy += hh + 4
    out.append(_rule(x, cy, w, C["ink"], 1))
    need = []
    for r in rows:
        need.append(max(_th(f'<content fontSize="{size}" fontFamily="{font}" bold="{str(j == 0).lower()}">'
                            f'<p lineSpacing="multiple:1.15">{escape(str(t))}</p></content>', cell_w(j), size)
                        for j, t in enumerate(r)) + row_pad)
    tot = cy - y + sum(need)
    extra = min(max(0.0, ((h or tot) - tot) / len(rows)), 26)
    for i, (r, nh) in enumerate(zip(rows, need)):
        rh = nh + extra
        if focus == i:
            out.append(_rect(x, cy + 1, w, rh - 1, C.get("band_bg", "rgb(227,236,244)")))
        if icon_w and icons[i]:
            out.append(f'<icon iconType="{escape(_icon_type(icons[i], "table_block icon"))}" topLeftX="{x + 2:.0f}" '
                       f'topLeftY="{cy + rh / 2 - 11:.0f}" width="22" height="22"><fill><fillColor color="{_c(C["deep"])}"/>'
                       f'</fill></icon>')
        for j, t in enumerate(r):
            col = C["accent"] if (focus == i and j > 0) else (C["deep"] if j == 0 else BODY)
            bold = j == 0 or focus == i
            out.append(_box(xs[j] + (icon_w if j == 0 else 0) + (4 if j == 0 else 0), cy + 4, cell_w(j) - (4 if j == 0 else 0),
                            rh - 6, f'<p lineSpacing="multiple:1.15">{escape(str(t))}</p>', size, col, font, bold=bold,
                            align="right" if right[j] else "left", valign="middle"))
        cy += rh
        out.append(_rule(x, cy, w, RULE_GREY if i < len(rows) - 1 else C["ink"], 1))
    if h and cy - y > h + 1:
        fit = max(1, int(len(rows) * (h - (hh + 4)) / max(cy - y - hh - 4, 1)))
        raise ValueError(f"table_block 超高 {cy - y - h:.0f}px：减少行、缩短单元格文字或加宽这一栏（不缩字号）；"
                         + split_hint("table_block", len(rows), fit))
    return "".join(out), cy


def _layout_block(block, left, top, width, palette, font, height=None):
    kind = block.get("kind")
    raw = block.get("text", "")
    # text=[…] / (…): one line per item — str() of a list would print "['…', '…']" on the slide
    text = "\n".join(str(t) for t in raw) if isinstance(raw, (list, tuple)) else str(raw)
    colours = roles(palette)
    slot = None
    if kind == "head":
        xml, bottom = section_head(left, top, width, text, palette=palette, font=font, size=HEAD_PT)
    elif kind == "text":
        tsize = block.get("size", BODY_PT)
        _prose_size(tsize)
        paras = "".join(f'<p lineSpacing="multiple:1.25">{escape(ln)}</p>' for ln in (text.split("\n") if text else [""]))
        content = f'<content fontSize="{tsize}" fontFamily="{font}">{paras}</content>'
        measured = _th(content, width, tsize)
        xml = _box(left, top, width, measured, paras, tsize, BODY, font)
        bottom = top + measured
    elif kind == "big":
        xml, bottom = stat_stack(left, top, width, [block["value"]], palette=palette, font=font)
    elif kind == "stats":
        xml, bottom = stat_stack(left, top, width, block["items"], h=height, palette=palette, font=font,
                                 size=block.get("size", BODY_PT))
    elif kind == "kv":
        xml, bottom = kv_rows(
            left,
            top,
            width,
            block["rows"],
            h=height,
            palette=palette,
            font=font,
            header=block.get("header"),
            label_frac=block.get("label_frac", 0.5),
            size=block.get("size", BODY_PT),
            row_pad=block.get("row_pad", 12),
        )
    elif kind == "steps":
        xml, bottom = numbered_steps(left, top, width, block["items"], h=height, palette=palette, font=font)
    elif kind == "table":
        xml, bottom = table_block(left, top, width, block["header"], block["rows"], widths=block.get("widths"),
                                  h=height, icons=block.get("icons"), focus=block.get("focus"), palette=palette,
                                  font=font, size=block.get("size", BODY_PT), row_pad=block.get("row_pad", 12))
    elif kind == "dots":
        xml, bottom = dot_bullets(left, top, width, block["items"], palette=palette, font=font,
                                  size=block.get("size", BODY_PT), h=height)
    elif kind == "note":
        xml, bottom = note_box(left, top, width, text, lead=block.get("lead"), palette=palette, font=font,
                               size=block.get("size", BODY_PT))
    elif kind == "caption":   # one grey line under a picture (source / "示意"), not a framed sentence
        content = f'<content fontSize="12" fontFamily="{font}"><p>{escape(text)}</p></content>'
        measured = _th(content, width, 12)
        xml = _box(left, top + 4, width, measured, f"<p>{escape(text)}</p>", 12, CAPTION, font)
        bottom = top + 4 + measured
    elif kind in ("chart", "image"):
        requested = block.get("height", 140)
        if requested <= 0:
            raise ValueError(f"{kind} height 必须为正")
        xml, start = (
            section_head(left, top, width, str(block["title"]), palette=palette, font=font)
            if block.get("title")
            else ("", top)
        )
        if block.get("claim") and kind == "chart":   # judgement line over the metric title (multi-chart pages)
            cl = str(block["claim"])
            ch = _th(f'<content fontSize="{HEAD_PT}" fontFamily="{font}"><p>{escape(cl)}</p></content>', width, HEAD_PT)
            if ch > HEAD_PT * 1.4 * 2 + 6:
                raise ValueError(f"chart 块 claim {cl!r} 超过两行：缩到约 {int(width / HEAD_PT * 2)} 字")
            C_ = roles(palette)
            head_xml = _box(left, top, width, ch, f"<p>{escape(cl)}</p>", HEAD_PT, C_["ink"], font, bold=True)
            CLAIMS.append(cl)
            if block.get("note"):   # optional ≤2-line explanation under the claim
                from ._page import check_panel_note
                nt = str(block["note"])
                check_panel_note(cl, nt, "chart 块 note=")
                nh = _th(f'<content fontSize="{RESEARCH_PT + 1}" fontFamily="{font}"><p>{escape(nt)}</p></content>', width,
                         RESEARCH_PT + 1)
                if nh > (RESEARCH_PT + 1) * 1.4 * 2 + 6:
                    raise ValueError(f"chart 块 note {nt!r} 超过两行：缩到约 {int(width / 13 * 2)} 字")
                head_xml += _box(left, top + ch, width, nh, f"<p>{escape(nt)}</p>", RESEARCH_PT + 1, BODY, font)
                ch += nh
            if block.get("title"):
                t_xml, start = section_head(left, top + ch + 2, width, str(block["title"]), palette=palette, font=font)
                xml = head_xml + t_xml
            else:
                xml, start = head_xml + _rule(left, top + ch + 2, width, C_["ink"], 1), top + ch + 8
        caption = block.get("caption") if kind == "image" else None
        caption_height = (8 + _layout_block(dict(kind="caption", text=caption), 0, 0, width, palette, font)[1]
                          if caption else 0)
        total = height if height is not None else start - top + requested + caption_height
        available = total - (start - top) - caption_height
        if available <= 0:
            raise ValueError(f"{kind} 标题之后没有可用高度")
        slot = (left, start, width, available)
        if kind == "image":
            token = str(block.get("src", ""))
            ratio = block.get("ratio")
            if not token or token.startswith(("http:", "https:")):
                raise ValueError("image src 用已上传的 file_token 或 @本地路径，不用外链")
            if ratio is None or ratio <= 0:
                raise ValueError("image ratio 必须为原图的正宽高比")
            image_w = min(width, available * ratio)
            image_h = image_w / ratio
            image_x = left + (width - image_w) / 2
            image_y = start + (available - image_h) / 2
            xml += (
                f'<img src="{escape(token, quote=True)}" topLeftX="{image_x:.1f}" topLeftY="{image_y:.1f}" '
                f'width="{image_w:.1f}" height="{image_h:.1f}"/>'
            )
            content_bottom = image_y + image_h
            if block.get("callouts"):
                xml, content_bottom = _diagram_callouts(
                    xml, slot, ratio, block["callouts"], palette, font, block.get("focus")
                )
            if caption:
                xml += _layout_block(dict(kind="caption", text=caption), left, content_bottom + 8,
                                     width, palette, font)[0]
        bottom = top + total
    elif kind == "takeaways":
        if height is None:
            raise ValueError("takeaways 需要整栏高度")
        proxy = type("RailFrame", (), dict(top=top, bottom=top + height, left=left, right=left + width, C=colours))()
        xml = key_takeaways(
            proxy, block["items"], label=block.get("label"), x=left, w=width, palette=palette, font=font,
            size=block.get("size", BODY_PT),
        )
        bottom = top + height
    else:
        raise ValueError(f"未知 layout block kind: {kind!r}")
    return xml, bottom, slot


def _compress_column(blocks, avail, needed, gap, measure):
    """Shrink one stacked column by ≤ SQUEEZE_MAX: block gaps to 3px, table/kv row padding 12→6px, then chart/image
    heights (each keeps ≥ CHART_MIN_SHARE of its request and ≥ CHART_MIN_PX). Returns (blocks copy, steps taken)."""
    blocks = [dict(b) for b in blocks]
    steps = []
    if gap > 3 and len(blocks) > 1:
        steps.append("间距")
        needed = measure(blocks, 3)
        gap = 3
    if needed > avail:
        rowed = [b for b in blocks if b.get("kind") in ("table", "kv") and b.get("row_pad", 12) > 6]
        if rowed:
            for b in rowed:
                b["row_pad"] = 6
            steps.append("表格行高")
            needed = measure(blocks, gap)
    if needed > avail:
        charts = [b for b in blocks if b.get("kind") in ("chart", "image")]
        room = {id(b): max(0.0, b.get("height", 140) - max(CHART_MIN_PX, CHART_MIN_SHARE * b.get("height", 140)))
                for b in charts}
        total = sum(room.values())
        if total > 0:
            cut = min(total, needed - avail)
            for b in charts:
                b["height"] = b.get("height", 140) - cut * room[id(b)] / total
            steps.append("图高")
    return blocks, steps


def mixed_columns_page(
    f,
    columns,
    widths=None,
    gap=14,
    block_gap=8,
    top=None,
    bottom=None,
    x=None,
    w=None,
    card=False,
    palette=None,
    font="思源黑体",
):
    """Independent 1–4-column stacks: image, chart, table or explanation in any column and vertical order.

    Each column has blocks=[dict(kind=...)]; kinds: head, text, big(value=(number, unit, caption)), stats(items=),
    kv(rows=), steps(items=), table(header=, rows=, icons=, focus=), dots(items=), note(text=), chart(key=, height=, title=, claim=, note=), image(key=, src=, ratio=, height=), caption(text=), takeaways(items=).
    An image block can include callouts=[(label, fx, fy)], focus=label and caption=text; these stay with its image.
    text/stats/kv/table/dots/note/takeaways blocks take size= (default 14; business-research decks may go to 12).
    One column supports full-width vertical stacking; 2–4 columns support independent stacks or bounded regions.
    widths are positive relative weights. A takeaways block occupies an entire column by itself.
    Returns (native_xml, slots): slots[(column_index, key)] is a slide-coordinate box for a chart/image.
    Put an Exhibit into a chart slot with Exhibit(w=box[2], h=box[3]).to_slide(x=box[0], y=box[1]).
    """
    count = len(columns)
    if PROFILE.get("research") and count > 1:
        has = [any(b.get("kind") in ("chart", "image", "takeaways") for b in c.get("blocks", [])) for c in columns]
        if not any(has):   # one chart column carries the page; the others may be kv / table / text evidence
            raise ValueError("mixed_columns_page 没有一栏有图（business-research 分栏页至少一栏要有图）：给主栏加 "
                             "dict(kind=\"chart\", key=…, height=…, title=\"图表标题，单位\")；"
                             "纯文字对比改用 row_table，说明文字放进右栏 key_takeaways")
        if count >= 4 and all(has):   # 4 chart columns leave 80–120 px plots: overlaps, tiny plots, endless rework
            raise ValueError("mixed_columns_page 4 栏都放图，每张图只剩约 100px 宽，标签必然互压：减到 2–3 栏图，"
                             "其余对象放进一张 row_table / small_multiples，或只留一栏图、其他栏写 kv / text")
    top = f.top if top is None else top
    bottom = f.bottom if bottom is None else bottom
    left = f.left if x is None else x
    width = f.right - left if w is None else w
    column_boxes(count, x=left, y=top, w=width, h=bottom - top, gap=gap)
    weights = list(widths) if widths is not None else [1] * count
    if len(weights) != count or any(weight <= 0 for weight in weights) or block_gap < 0:
        raise ValueError("widths 必须每栏一个正权重，block_gap 必须非负")
    palette = {"exhibit": _palette(palette, f)}
    available_w = width - gap * (count - 1)
    output, slots = [], {}
    natural = []   # (column, content height before stretching, has a chart / image)
    for column_index, (column, weight) in enumerate(zip(columns, weights)):
        column_w = available_w * weight / sum(weights)
        padded = column.get("card", card)
        padding = 12 if padded else 0
        inner_w = column_w - 2 * padding
        inner_h = bottom - top - 2 * padding
        if inner_w <= 32 or inner_h <= 0:
            raise ValueError("mixed_columns_page 栏宽/高度不足：加宽这一栏或减少栏数")
        blocks = column.get("blocks", [])
        if not blocks:
            raise ValueError("mixed_columns_page 每栏至少一个 block")
        kinds = {block.get("kind") for block in blocks} - {"head", "caption", "chart", "image", "table", "note", "takeaways"}
        if kinds:   # a stack of text / stats / kv / steps / dots is one block (table / note / takeaways log themselves)
            from ._page import BLOCKS as _BL
            _BL.append("栏")
        if any(block.get("kind") == "takeaways" for block in blocks) and len(blocks) != 1:
            raise ValueError("takeaways 独占整栏，不与其他 block 堆叠")
        def measure(blocks_, gap_):
            sizes_ = []
            for block in blocks_:
                reserved = inner_h if block.get("kind") == "takeaways" else None
                sizes_.append(_layout_block(block, 0, 0, inner_w, palette, font, height=reserved)[1])
            return sizes_, sum(sizes_) + gap_ * (len(blocks_) - 1)

        col_gap = block_gap
        sizes, needed = measure(blocks, col_gap)
        if needed > inner_h:
            first_need = needed
            if needed <= inner_h * (1 + SQUEEZE_MAX):   # small overflow: gaps → row padding → chart height, never fonts
                blocks, steps = _compress_column(blocks, inner_h, needed, col_gap,
                                                 lambda b_, g_: measure(b_, g_)[1])
                col_gap = min(col_gap, 3) if "间距" in steps else col_gap
                sizes, needed = measure(blocks, col_gap)
                if needed <= inner_h:
                    _squeezed(f"mixed_columns_page 第 {column_index + 1} 栏超出 {first_need - inner_h:.0f}px"
                              f"（{first_need / inner_h - 1:.0%}）：已自动压缩{'、'.join(steps)}，字号不变")
            if needed > inner_h:
                tables = [b_ for b_ in blocks if b_.get("kind") in ("table", "kv")]
                big = max(tables, key=lambda b_: len(b_.get("rows") or []), default=None)
                n_rows = len(big.get("rows") or []) if big else 0
                hint = (split_hint(f"第 {column_index + 1} 栏的 {big.get('kind')}", n_rows,
                                   n_rows * inner_h / first_need) if n_rows >= 4 else
                        "拆成 a/b 两页（每页 ≤3 块，plan 加一行交另一个 builder 并行做；页数不设上限）")
                raise ValueError(
                    f"mixed_columns_page 第 {column_index + 1} 栏放不下：需要 {first_need:.0f}px，只有 {inner_h:.0f}px"
                    f"（超出 {first_need / inner_h - 1:.0%}，>{SQUEEZE_MAX:.0%} 不自动压缩）；删字、减少块、缩短图高或加宽，不缩正文；"
                    + hint
                )
        flexible = [index for index, block in enumerate(blocks) if block.get("kind") in ("chart", "image")]
        # a column that fills by spreading rows (kv / table / steps) is not empty when stretched; stats / text / dots
        # stay at their own height and leave the stretch as white space
        kinds_ = [block.get("kind") for block in blocks]
        note_foot = not flexible and len(blocks) > 1 and kinds_[-1] == "note"
        natural.append((column_index, needed, bool(flexible) or note_foot or any(
            k in ("kv", "table", "steps", "takeaways") for k in kinds_) or sum(
            len(block.get("items") or []) for block in blocks if block.get("kind") == "dots") >= 3))
        lead = {}   # extra air above a block (the closing note pinned to the column foot)
        if flexible:   # pictures take the column's spare height
            for index in flexible:
                sizes[index] += (inner_h - needed) / len(flexible)
        else:   # a column without a picture grows with the chart column beside it, within limits: rows open up by
            # ≤ STRETCH_ROW_MAX each, steps / stats a little; dot lists keep their spacing; the rest stays white at
            # the foot (content top-aligned) — spreading it all made 50px kv rows and dots floating mid-column
            spare = inner_h - needed
            for index, block in enumerate(blocks):
                n_ = len(block.get("rows") or block.get("items") or [])
                cap = {"kv": n_ * STRETCH_ROW_MAX, "table": n_ * STRETCH_ROW_MAX, "steps": n_ * 12,
                       "stats": n_ * 12}.get(block.get("kind"), 0)
                take = min(cap, max(spare, 0.0))
                sizes[index] += take
                spare -= take
            if note_foot and 0 < spare <= NOTE_PIN_MAX:   # the framed sentence sits at the column's foot
                lead[len(blocks) - 1] = spare
        if padded:
            output.append(_rect(left, top, column_w, bottom - top, RAIL_BG))
        cursor = top + padding
        for block_index, (block, height) in enumerate(zip(blocks, sizes)):
            cursor += lead.get(block_index, 0.0)
            xml, block_bottom, slot = _layout_block(
                block, left + padding, cursor, inner_w, palette, font, height=height
            )
            if block_bottom > cursor + height + 1:
                raise ValueError("mixed_columns_page 块高度超出保留区域")
            output.append(xml)
            if slot is not None:
                key = (column_index, block.get("key", block_index))
                if key in slots:
                    raise ValueError(f"图位 key 重复：{key}")
                slots[key] = slot
                if block.get("kind") == "chart":
                    CHART_SLOTS.append(slot)
                if block.get("title"):
                    SLOT_TITLES[(round(slot[2]), round(slot[3]))] = str(block["title"])
            cursor += height + col_gap
        left += column_w + gap
    has_chart = any(block.get("kind") in ("chart", "image") for column in columns for block in column.get("blocks", []))
    if count > 1 and has_chart and not all(c_ for _, _, c_ in natural):
        span_ = bottom - top
        short_ = [i for i, h_, c_ in natural if not c_ and span_ - h_ > 0.35 * span_]
        if short_:   # text / number columns beside a chart column: their content stops high, the rest is white
            SHORT.append(f"mixed_columns_page 第 {[i + 1 for i in short_]} 栏只有文字 / 大数字，内容只到栏高的 "
                         f"{max(h_ for i, h_, _ in natural if i in short_) / span_:.0%}，下方大片空白（旁边一栏有图撑满）："
                         "每栏都放一张小图（同口径序列），或都不放图、把这张图改成整页下方通栏 / 右栏，或给这些栏补 kv / dots 证据")
    return "".join(output), slots


def kpi_strip(x, y, w, items, palette=None, font="思源黑体", size=BODY_PT):
    """Row of 2–4 headline figures across the top of the body, thin grey separators between them: per item a grey
    12pt caption (metric · period), a serif 26pt number, and 1–2 grey 12pt context lines (YoY / basis). items:
    [(caption, value, context)] — context may be "" or "line 1\nline 2". Returns (xml, bottom)."""
    _block("kpi_strip")
    from ._text import tw

    C = roles(palette)
    n = len(items)
    if not 2 <= n <= 4:
        raise ValueError("kpi_strip 写 2–4 个数字（一行横排）")
    gap = 16
    cw = (w - gap * (n - 1)) / n
    rows = [(str(a), str(b), str(c or "")) for a, b, c in items]
    big = 26
    while big > 18 and any(tw(v, big, bold=True) * 1.12 > cw - 8 for _, v, _ in rows):
        big -= 2
    cap_h = max(_th(f'<content fontSize="12" fontFamily="{font}"><p>{escape(c)}</p></content>', cw - 8, 12) for c, _, _ in rows)
    ctx_h = max((_th(f'<content fontSize="12" fontFamily="{font}">' + "".join(
        f"<p>{escape(t)}</p>" for t in c.split("\n")) + "</content>", cw - 8, 12) if c else 0) for _, _, c in rows)
    if ctx_h > 40:
        raise ValueError("kpi_strip 每个数字的说明最多 2 行（同比 / 口径），细节放图注或 key_takeaways")
    num_h = big * 1.35
    out = []
    for i, (cap, val, ctx) in enumerate(rows):
        cx = x + i * (cw + gap)
        if i:
            out.append(f'<line startX="{cx - gap / 2:.0f}" startY="{y:.0f}" endX="{cx - gap / 2:.0f}" '
                       f'endY="{y + cap_h + num_h + ctx_h + 6:.0f}"><border color="{_c(RULE_GREY)}" width="1"/></line>')
        out.append(_box(cx, y, cw - 4, cap_h, f"<p>{escape(cap)}</p>", 12, CAPTION, font))
        out.append(_box(cx, y + cap_h + 2, cw - 4, num_h,
                        f'<p><span fontFamily="Georgia" bold="true">{escape(val)}</span></p>', big, C["deep"], font))
        if ctx:
            out.append(_box(cx, y + cap_h + num_h + 2, cw - 4, ctx_h,
                            "".join(f"<p>{escape(t)}</p>" for t in ctx.split("\n")), 12, CAPTION, font))
    bottom = y + cap_h + num_h + ctx_h + 8
    out.append(_rule(x, bottom, w, RULE_GREY, 1))
    return "".join(out), bottom + 1


def kpi_charts_page(f, kpis, charts, gap=28, palette=None, font="思源黑体"):
    """"Numbers on top, charts below": a kpi_strip of 2–4 headline figures, then 1–2 charts side by side filling the
    rest of the body (each under a bold section_head title). No conclusion strip: the title carries the so-what.
    kpis: [(caption, value, context, chart)] — chart = index of the chart below this figure is read from (0 / 1);
    business-research pages need it, and publish checks the value is drawn on that chart (same metric, same period —
    e.g. the last bar's label, the CAGR on the chart). charts: ["图题，单位", ...] (1–2).
    Returns (xml, slots) — slots[i] = (x, y, w, h) slide box of chart i: Exhibit(w=box[2], h=box[3]).to_slide(x=box[0], y=box[1])."""
    if not 1 <= len(charts) <= 2:
        raise ValueError("kpi_charts_page 下方放 1–2 张图；3 张以上用 columns_page(chart=…)")
    C = _palette(palette, f)
    pal = {"exhibit": C}
    links = []
    for k in kpis:
        ci = k[3] if len(k) > 3 else None
        if ci is not None and not (isinstance(ci, int) and 0 <= ci < len(charts)):
            raise ValueError(f"kpi_charts_page：KPI {k[0]!r} 的第 4 项 chart={ci!r} 要是下方图的序号 0–{len(charts) - 1}")
        links.append((str(k[1]), ci))
    KPI_LINKS.append(links)
    kpis = [tuple(k[:3]) for k in kpis]
    out, y = kpi_strip(f.left, f.top, f.right - f.left, kpis, palette=pal, font=font)
    out = [out]
    bottom = f.bottom
    y += 14
    n = len(charts)
    cw = (f.right - f.left - gap * (n - 1)) / n
    slots = []
    for i, title in enumerate(charts):
        cx = f.left + i * (cw + gap)
        xml, cy = section_head(cx, y, cw, str(title), palette=pal, font=font, rule=False)
        out.append(xml)
        if bottom - cy < 150:
            raise ValueError(f"kpi_charts_page 图区只剩 {bottom - cy:.0f}px：KPI 说明删到 1 行")
        slots.append((cx, cy + 2, cw, bottom - cy - 2))
    return "".join(out), slots


def _diagram_callouts(xml, slot, ratio, callouts, palette, font, focus=None):
    """Part labels outside the picture, joined to the part by a thin leader whose last leg is horizontal; labels on
    each side share one column. callouts: [(label, fx, fy)] with fx, fy = the part's position as a fraction (0–1) of
    the picture width / height; fx < 0.5 goes to the left column, else the right."""
    left, top, width, height = slot
    C = roles(palette)
    groups = {
        side: sorted((callout for callout in callouts if (callout[1] < 0.5) == (side == "L")),
                     key=lambda callout: callout[2])
        for side in ("L", "R")
    }
    label_limit = max(20, width * 0.2 - 12)
    label_widths = {
        side: min(max((_label_width(str(callout[0]), 11, font, bold=True) + 4 for callout in group), default=0),
                  label_limit)
        for side, group in groups.items()
    }
    left_rail = label_widths["L"] + 12 if groups["L"] else 0
    right_rail = label_widths["R"] + 12 if groups["R"] else 0
    picture_area = width - left_rail - right_rail
    pic_w = min(picture_area, height * ratio)
    pic_h = pic_w / ratio
    if pic_w <= 40:
        raise ValueError("image 图区太窄放不下部件标签：扩大图区或缩短部件名/减少 callouts")
    pic_x = left + left_rail + (picture_area - pic_w) / 2
    pic_y = top + (height - pic_h) / 2
    xml = re.sub(r'(<img [^>]*?)topLeftX="[\d.]+" topLeftY="[\d.]+" width="[\d.]+" height="[\d.]+"',
                 lambda m: f'{m.group(1)}topLeftX="{pic_x:.1f}" topLeftY="{pic_y:.1f}" width="{pic_w:.1f}" '
                           f'height="{pic_h:.1f}"', xml, count=1)
    out = [xml]
    content_bottom = pic_y + pic_h
    for side in ("L", "R"):
        group = groups[side]
        label_w = label_widths[side]
        label_heights = [max(18, _th(f'<content fontSize="11" fontFamily="{font}" bold="true">'
                                    f'<p>{escape(str(label))}</p></content>', label_w, 11))
                         for label, fx, fy in group]
        needed_height = sum(label_heights) + max(0, len(group) - 1) * 9
        if needed_height > height:
            raise ValueError(f"{'左' if side == 'L' else '右'}侧部件标签放不下：标签需 {needed_height:.0f}px，"
                             f"图槽只有 {height:.0f}px")
        ys, floor = [], top
        for (label, fx, fy), label_h in zip(group, label_heights):
            if not (0 <= fx <= 1 and 0 <= fy <= 1):
                raise ValueError(f"callout {label!r} 的位置用图内比例 0–1")
            y = max(pic_y + fy * pic_h, floor + label_h / 2)
            ys.append(y)
            floor = y + label_h / 2 + 9
        if ys and ys[-1] + label_heights[-1] / 2 > top + height:
            ceiling = top + height
            for label_index in range(len(ys) - 1, -1, -1):
                ys[label_index] = min(ys[label_index], ceiling - label_heights[label_index] / 2)
                ceiling = ys[label_index] - label_heights[label_index] / 2 - 9
        if ys:
            content_bottom = max(content_bottom, ys[-1] + label_heights[-1] / 2)
        lx = left if side == "L" else left + width - label_w
        elbow = pic_x - 8 if side == "L" else pic_x + pic_w + 8
        end = lx + label_w + 4 if side == "L" else lx - 4
        for (label, fx, fy), y, label_h in zip(group, ys, label_heights):
            px, py = pic_x + fx * pic_w, pic_y + fy * pic_h
            col = C["accent"] if focus is not None and label == focus else C["ink"]
            out.append(f'<line startX="{px:.0f}" startY="{py:.0f}" endX="{elbow:.0f}" endY="{y:.0f}">'
                       f'<border color="{_c(col)}" width="0.75"/></line>')
            out.append(f'<line startX="{elbow:.0f}" startY="{y:.0f}" endX="{end:.0f}" endY="{y:.0f}">'
                       f'<border color="{_c(col)}" width="0.75"/></line>')
            out.append(_box(lx, y - label_h / 2, label_w, label_h, f"<p>{escape(str(label))}</p>", 11, col, font, bold=True,
                            align="right" if side == "L" else "left", valign="middle"))
    return "".join(out), content_bottom


def diagram_page(
    f, image_token, image_ratio, items, stats=None, parameters=None, title=None, callouts=None, focus=None,
    caption=None, palette=None, font="思源黑体"
):
    """Image + optional stats + takeaways shortcut; use mixed_columns_page for freely positioned image blocks.

    image_token is an uploaded file_token (or @local path), image_ratio is the original width/height.
    stats=[(value, unit, caption)] or parameters=[(label, value)], never both. callouts=[(部件名, fx, fy)] puts
    part labels outside the picture with horizontal leaders (fx, fy = part position as 0–1 of the picture);
    focus=部件名 colours that technical label accent; omit callouts for images without component locations.
    caption is optional; engineering illustrations use "工程剖面示意图". Technical claims require separate evidence.
    Returns (xml, slots).
    """
    if stats is not None and parameters is not None:
        raise ValueError("参数栏选择 stats 或 parameters，不同时传")
    blocks = [dict(kind="image", key="diagram", src=image_token, ratio=image_ratio, title=title,
                   callouts=callouts, focus=focus)]
    if caption:
        blocks.append(dict(kind="caption", text=caption))
    diagram = dict(blocks=blocks)
    rail = dict(blocks=[dict(kind="takeaways", items=items)])
    middle = None
    if stats:
        middle = dict(blocks=[dict(kind="stats", items=stats)])
    elif parameters:
        middle = dict(blocks=[dict(kind="kv", rows=parameters)])
    width = f.right - f.left
    rail_weight = RAIL_W
    if middle is not None:
        remaining = width - 2 * RAIL_GAP - rail_weight
        columns = [diagram, middle, rail]
        weights = [remaining * 0.68, remaining * 0.32, rail_weight]
    else:
        columns = [diagram, rail]
        weights = [width - RAIL_GAP - rail_weight, rail_weight]
    xml, slots = mixed_columns_page(f, columns, widths=weights, gap=RAIL_GAP, palette=palette, font=font)
    return xml, slots


# Generated-image prompts for the diagram styles (fill {subject}, {ink} = page dark colour, {accent} = page accent,
# {part} = the part the title is about). The picture carries shapes only; every word is a native label.
DIAGRAM_PROMPTS = {
    "cutaway": (
        "a publication-quality engineering cutaway of {subject} explaining {part}, three-quarter view with a clean "
        "section through the casing revealing clearly separated internal layers; precise engineering line art, "
        "slightly heavier outer contours and fine internal lines in {ink}, light grey hatching for section surfaces, "
        "pure white background, mostly unfilled white surfaces, sparse {accent} emphasis near {part}; coherent "
        "perspective and legible component boundaries, one large focal object with modest side margins for native "
        "external labels and fine leaders added later; no gradients; absolutely no text, letters, numbers, labels, captions, arrows with words, logos or watermarks anywhere in the image"
    ),
}
DIAGRAM_PROMPTS_ZH = {
    "cutaway": "为解释{subject}中的{part}画专业出版级工程剖面线稿，三分之四视角，整齐剖开部分外壳露出彼此清楚分隔的内部层次；"
               "{ink}主描边，外轮廓略粗、内部细线，剖切面用浅灰排线，大部分表面留白，纯白背景，{part}附近少量{accent}强调；"
               "透视统一、部件边界清晰，单个大主体占主要图区，左右适度留位给后加的原生图外部件名称与细引线；无渐变；画面中不出现任何文字、字母、数字、标签、箭头注释、logo、水印",
}
LINE_ART_PROMPT = DIAGRAM_PROMPTS["cutaway"]
LINE_ART_PROMPT_ZH = DIAGRAM_PROMPTS_ZH["cutaway"]


def diagram_prompt(style, subject, part, ink, accent, zh=None):
    """Engineering cutaway prompt with page colours and reference-based principal structure."""
    if style != "cutaway":
        raise ValueError("style 只支持 cutaway")
    table = DIAGRAM_PROMPTS_ZH if (zh if zh is not None else has_cjk(subject)) else DIAGRAM_PROMPTS
    prompt = table["cutaway"].format(subject=subject, part=part, ink=_c(ink), accent=_c(accent))
    if table is DIAGRAM_PROMPTS_ZH:
        return prompt + ("；主要构造与作用据已提供的核实资料；无需完整参数、尺寸或 BOM，未知局部省略；"
                         "工程剖面示意图，不作为拆解或实测证据，不编参数、因果、数据或成效")
    return prompt + (
        "; show only the principal structure supported by supplied verified references; complete specifications "
        "are not required, omit unknown details rather than invent dimensions or a full BOM; engineering cutaway "
        "schematic, not an actual teardown or measured evidence; do not invent specifications, causal claims, data or outcomes"
    )


def icon_grid(f, items, icon="iconpark/Peoples/people.svg", rest="其他", per=1, box=None, n_cols=10, n_rows=10,
                colors=None, value_fmt=None, palette=None):
    """McKinsey-style 100-icon grid for the share of a whole: 10×10 IconPark icons (icon= any iconType or a bare name —
    people, cars, homes …; each icon is one native, editable element), filled row by row from the top-left in item
    order. items: [(name, share %)] of one whole (≤4 parts, sum ≤100); each part a palette shade, the rest light grey
    (`rest` names it in the key; None hides it). icon may also be a list, one per part. Key on the right: share in bold
    in the part's colour over its name, caption "每个图标 = 1%" at its foot. box: (x0, y0, x1, y1), default the body
    area. Returns body XML for f.publish(xml, …)."""
    _block("icon_grid")
    if not items:
        raise ValueError("icon_grid 需要 items=[(名称, 占比%)]")
    if len(items) > 4:
        raise ValueError(f"icon_grid 最多 4 个部分（收到 {len(items)}）：多出的并成'其他'，或改用 100% 堆叠条 / share_bars")
    total_n = n_cols * n_rows
    counts = [int(round(float(v) / per)) for _, v in items]
    if sum(counts) > total_n:
        raise ValueError(f"icon_grid 各部分合计 {sum(float(v) for _, v in items):g}% 超过 100%：items 是同一整体的构成")
    C = roles(palette)
    shades = colors or [C["main"], C["accent"], C["light"], C["second"]][:len(items)]
    icons = list(icon) if isinstance(icon, (list, tuple)) else [icon] * len(items)
    icons = [_icon_type(ic, "icon_grid icon") for ic in (icons + [icons[-1]] * len(items))[:len(items)]]
    off_icon = icons[-1] if len(set(icons)) == 1 else _icon_type("iconpark/Peoples/people.svg", "icon_grid icon")
    zh = has_cjk(" ".join(str(nm) for nm, _ in items) + str(rest or ""))
    vf = value_fmt or (lambda v: f"{float(v):g}%")
    x0, y0, x1, y1 = box or (f.left, f.top, f.right, f.bottom)
    key_w = min(260, (x1 - x0) * 0.36)
    step = min((x1 - x0 - key_w - 28) / n_cols, (y1 - y0) / n_rows)
    gw, gh = step * n_cols, step * n_rows
    gy = y0 + max(0, ((y1 - y0) - gh) / 2)
    cells = []
    for c, col, ic in zip(counts, shades, icons):
        cells += [(col, ic)] * c
    cells += [(C["track"], off_icon)] * (total_n - len(cells))
    sz = step * 0.82
    out = []
    for i, (col, ic) in enumerate(cells):
        r_, c_ = divmod(i, n_cols)
        x, y = x0 + c_ * step + (step - sz) / 2, gy + r_ * step + (step - sz) / 2
        out.append(f'<icon iconType="{escape(ic)}" topLeftX="{x:.1f}" topLeftY="{y:.1f}" width="{sz:.1f}" height="{sz:.1f}">'
                   f'<fill><fillColor color="{_c(col)}"/></fill></icon>')
    kx = x0 + gw + 28
    rows_ = [(nm, v, col) for (nm, v), col in zip(items, shades)]
    left = 100 * per - sum(float(v) for _, v in items)
    if rest and left >= per / 2:
        rows_.append((rest if zh or rest != "其他" else "Other", left, C["sub"]))
    gap = min(72, (gh - 24) / max(len(rows_), 1))
    ky = gy
    for nm, v, col in rows_:
        out.append(_box(kx, ky, key_w, 34, f'<p><span bold="true">{escape(vf(v))}</span></p>', 26, col, "思源黑体"))
        out.append(_box(kx, ky + 34, key_w, 20, f'<p>{escape(str(nm))}</p>', 12, C["text"], "思源黑体"))
        ky += gap
    cap = f"每个图标 = {per:g}%" if zh else f"Each icon = {per:g}%"
    out.append(_box(kx, gy + gh - 16, key_w, 16, f'<p>{escape(cap)}</p>', 10, C["sub"], "思源黑体"))
    return "".join(out)


person_grid = icon_grid   # earlier name
