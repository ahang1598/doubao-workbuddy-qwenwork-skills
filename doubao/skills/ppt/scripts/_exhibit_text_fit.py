"""Size native text boxes with the same estimator the Slides lint uses."""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _exhibit_xml_lint as _lint  # noqa: E402

_SML = "https://www.larkoffice.com/sml/2.0"


def _measure(shape_xml):
    slide = f'<slide xmlns="{_SML}"><data>{shape_xml}</data></slide>'
    for element in _lint.extract_elements(slide):
        if _lint.is_text_element(element):
            block = _lint.estimate_text_block_height(element)
            if block:
                return block["estimated_height"] + element["paddingTop"] + element["paddingBottom"]
    return 0.0


def label_width(text, *, font_size, bold=False, font_family=None):
    """Width for an unbroken label, including the lint's Latin wrap-risk allowance."""
    widths = []
    for line in str(text).split("\n"):
        width = _lint.estimate_text_width(line.rstrip(), font_size, 0, bold, font_family or "")
        if re.search(r"[A-Za-z]", line):
            width /= _lint.TEXT_WIDTH_WRAP_RISK_RATIO
        widths.append(width)
    return round(max(widths or [0]) + 2, 1)


def text_height(text, *, width, font_size, line_spacing="multiple:1.2", bold=False, font_family=None, slack=1.06):
    """Height (px) a text box of ``width`` needs for ``text`` (plain str, '\\n' = new paragraph, or <content> XML)."""
    if text.lstrip().startswith("<content"):
        content = text
    else:
        paras = "".join(f"<p>{escape(p)}</p>" for p in str(text).split("\n"))
        attrs = f' fontSize="{font_size:g}" lineSpacing="{line_spacing}" wrap="true"'
        attrs += ' bold="true"' if bold else ""
        attrs += f' fontFamily="{escape(font_family)}"' if font_family else ""
        content = f"<content{attrs}>{paras}</content>"
    shape = f'<shape type="text" topLeftX="0" topLeftY="0" width="{width:g}" height="1">{content}</shape>'
    return round(_measure(shape) * slack + 2, 1)


def _boxes(slide_xml):
    """(offset, (x, y, w, h), text) of the elements a grown text box must not run into: text boxes with text, pictures,
    charts, tables, embeds (decorative fills / lines are not obstacles), in document order."""
    out = []
    for m in re.finditer(r"<(shape|img|table|chart|embed|whiteboard)\b([^>]*)>", slide_xml):
        vals = [re.search(rf'\b{k}="(-?[\d.]+)"', m.group(2)) for k in ("topLeftX", "topLeftY", "width", "height")]
        if not all(vals):
            continue
        end = m.end() if m.group(2).rstrip().endswith("/") else slide_xml.find(f"</{m.group(1)}>", m.end())
        text = re.sub(r"<[^>]+>|\s+", "", slide_xml[m.end():max(end, m.end())])
        if m.group(1) == "shape" and not ('type="text"' in m.group(2) and text):
            continue
        out.append((m.start(), tuple(float(v.group(1)) for v in vals), text))
    return out


def _hit(a, b, pad=1.0):
    return a[0] < b[0] + b[2] - pad and b[0] < a[0] + a[2] - pad and a[1] < b[1] + b[3] - pad and b[1] < a[1] + a[3] - pad


def fit_text_boxes(slide_xml, *, slack=1.06, max_bottom=530, pin_top=False):
    """Return ``slide_xml`` with overflowing native text boxes grown to fit (never shrunk).

    A box whose growth would reach an element it did not touch before is left as is, with a warning naming that
    element (growing would only move the overflow onto its neighbour). ``pin_top`` (business-deck): the grown box keeps
    its text where it was laid out — middle-aligned text gets verticalAlign="top", bottom-aligned text grows upward."""
    warnings = []
    others = _boxes(slide_xml)

    def grow(match):
        tag = match.group(0)
        head = re.match(r"<shape\b[^>]*>", tag).group(0)
        if 'type="text"' not in head or 'wrap="false"' in tag:
            return tag
        h = re.search(r'\bheight="([\d.]+)"', head)
        y = re.search(r'\btopLeftY="(-?[\d.]+)"', head)
        x = re.search(r'\btopLeftX="(-?[\d.]+)"', head)
        w = re.search(r'\bwidth="([\d.]+)"', head)
        if not h:
            return tag
        need = _measure(tag) * slack + 2
        if need <= float(h.group(1)):
            return tag
        text = " ".join(re.sub(r"<[^>]+>", "", tag).split())[:24]
        content = re.search(r"<content\b[^>]*>", tag)
        va = re.search(r'\bverticalAlign="(\w+)"', content.group(0)) if content else None
        va = va.group(1) if va else "middle"
        new_y = float(y.group(1)) if y else None
        if y and x and w:
            old = (float(x.group(1)), float(y.group(1)), float(w.group(1)), float(h.group(1)))
            new_y = old[1] - (need - old[3]) if pin_top and va == "bottom" else old[1]
            new = (old[0], new_y, old[2], need)
            hits = [(b, t) for off, b, t in others if off != match.start() and _hit(new, b) and not _hit(old, b)]
            if hits or new_y < 0:
                if hits:
                    b, t = hits[0]
                    warnings.append(
                        f"text box '{text}' needs {need:.0f}px (box {old[3]:g}) but growing it would reach "
                        f"'{t[:16] or 'an element'}' at y={b[1]:g}: not grown — shorten the text (a title: one line), "
                        f"widen the box, or move '{t[:16] or 'that element'}' and what sits under it down "
                        f"{max(1, round(new_y + need - b[1] + 2))}px"
                    )
                else:
                    warnings.append(f"text box '{text}' needs {need:.0f}px: growing it upward leaves the canvas, not grown")
                return tag
        if new_y is not None and new_y + need > max_bottom:
            warnings.append(
                f"text box '{text}' needs {need:.0f}px and would reach y={new_y + need:.0f}; shorten it or widen the box"
            )
        new_head = head.replace(h.group(0), f'height="{need:.1f}"', 1)
        if pin_top and va == "bottom" and y:
            new_head = new_head.replace(y.group(0), f'topLeftY="{new_y:.1f}"', 1)
        out = tag.replace(head, new_head, 1)
        if pin_top and va == "middle" and content:   # middle would re-centre the text lower in the taller box
            c = content.group(0)
            c2 = re.sub(r'\sverticalAlign="[^"]*"', "", c)
            c2 = c2[:-2] + ' verticalAlign="top"/>' if c2.endswith("/>") else c2[:-1] + ' verticalAlign="top">'
            out = out.replace(c, c2, 1)
        return out

    out = re.sub(r'<shape\b[^>]*type="text"[^>]*>.*?</shape>', grow, slide_xml, flags=re.S)
    return out, warnings


PIN_TOP_RATIO = 1.5   # box height ≥ this × the height its text needs: default middle alignment leaves a visible gap
PIN_MIN_GAP, PIN_BIG_GAP = 24.0, 40.0   # px of empty box height: below MIN the float is invisible; BIG floats anyway


def pin_tall_body_top(slide_xml, *, ratio=PIN_TOP_RATIO, slack=1.06):
    """business-deck: a body text box with ≥2 paragraphs and no verticalAlign that is visibly taller than its text (≥
    PIN_MIN_GAP px spare and either ``ratio`` × the text height or ≥ PIN_BIG_GAP px spare) gets verticalAlign="top", and
    so do the other such boxes of the same row (same top and height) — the default middle alignment floats the text
    away from the heading above it and leaves side-by-side columns of different length out of line. Only that attribute
    is added; boxes are not moved. Skipped when the text, moved to the
    top of its box, would reach an element (text, picture, chart, table, line) its centred lines did not touch.
    Returns (xml, notes)."""
    others = _boxes(slide_xml)
    for m in re.finditer(r"<line\b([^>]*)>", slide_xml):
        v = [re.search(rf'\b{k}="(-?[\d.]+)"', m.group(1)) for k in ("startX", "startY", "endX", "endY")]
        if all(v):
            x1, y1, x2, y2 = (float(t.group(1)) for t in v)
            others.append((m.start(), (min(x1, x2) - 1, min(y1, y2) - 1, abs(x2 - x1) + 2, abs(y2 - y1) + 2), "line"))
    cands = {}   # offset -> (box, need) of multi-paragraph body boxes left at the default middle alignment
    for m in re.finditer(r'<shape\b[^>]*type="text"[^>]*>.*?</shape>', slide_xml, flags=re.S):
        tag = m.group(0)
        head = re.match(r"<shape\b[^>]*>", tag).group(0)
        content = re.search(r"<content\b[^>]*>", tag)
        if not content or "verticalAlign" in content.group(0) or 'wrap="false"' in content.group(0) \
                or re.search(r'textType="(?:title|headline)"', content.group(0)):
            continue
        if sum(1 for p in re.findall(r"<p\b[^>]*>(.*?)</p>", tag, re.S) if re.sub(r"<[^>]+>|\s", "", p)) < 2:
            continue
        vals = [re.search(rf'\b{k}="(-?[\d.]+)"', head) for k in ("topLeftX", "topLeftY", "width", "height")]
        if all(vals):
            box = tuple(float(v.group(1)) for v in vals)
            need = _measure(tag) * slack + 2
            if 2 < need < box[3]:
                cands[m.start()] = (box, need)
    # visibly floating: ≥ PIN_MIN_GAP px of slack and either ratio × the text height or PIN_BIG_GAP px of slack
    loose = {off for off, (b, need) in cands.items()
             if b[3] - need >= PIN_MIN_GAP and (b[3] >= ratio * need or b[3] - need >= PIN_BIG_GAP)}
    rows = {(round(b[1]), round(b[3])) for off, (b, _) in cands.items() if off in loose}
    loose |= {off for off, (b, _) in cands.items() if (round(b[1]), round(b[3])) in rows}   # the row's other columns
    pinned = []

    def pin(match):
        tag = match.group(0)
        if match.start() not in loose:
            return tag
        (x, y, w, h), need = cands[match.start()]
        old, new = (x, y + (h - need) / 2, w, need), (x, y, w, need)
        if any(off != match.start() and _hit(new, b, 0) and not _hit(old, b, 0) for off, b, _ in others):
            return tag
        c = re.search(r"<content\b[^>]*>", tag).group(0)
        c2 = c[:-2] + ' verticalAlign="top"/>' if c.endswith("/>") else c[:-1] + ' verticalAlign="top">'
        pinned.append(" ".join(re.sub(r"<[^>]+>", " ", tag).split())[:16])
        return tag.replace(c, c2, 1)

    out = re.sub(r'<shape\b[^>]*type="text"[^>]*>.*?</shape>', pin, slide_xml, flags=re.S)
    notes = ([f"{len(pinned)} 个多段正文框比文字高很多、默认垂直居中会和上方小标题脱开：已补 verticalAlign=\"top\""
              f"（{'、'.join(repr(t) for t in pinned[:3])}），坐标未动"] if pinned else [])
    return out, notes
