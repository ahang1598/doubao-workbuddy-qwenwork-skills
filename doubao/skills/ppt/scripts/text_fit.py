"""Size native text boxes with the same estimator the Slides lint uses."""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import xml_lint as _lint  # noqa: E402

_SML = "https://www.larkoffice.com/sml/2.0"


def _measure(shape_xml):
    slide = f'<slide xmlns="{_SML}"><data>{shape_xml}</data></slide>'
    for element in _lint.extract_elements(slide):
        if _lint.is_text_element(element):
            block = _lint.estimate_text_block_height(element)
            if block:
                return block["estimated_height"] + element["paddingTop"] + element["paddingBottom"]
    return 0.0


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


def fit_text_boxes(slide_xml, *, slack=1.06, max_bottom=530):
    """Return ``slide_xml`` with overflowing native text boxes grown to fit (never shrunk)."""
    warnings = []

    def grow(match):
        tag = match.group(0)
        head = re.match(r"<shape\b[^>]*>", tag).group(0)
        if 'type="text"' not in head or 'wrap="false"' in tag:
            return tag
        h = re.search(r'\bheight="([\d.]+)"', head)
        y = re.search(r'\btopLeftY="([\d.]+)"', head)
        if not h:
            return tag
        need = _measure(tag) * slack + 2
        if need <= float(h.group(1)):
            return tag
        if y and float(y.group(1)) + need > max_bottom:
            text = re.sub(r"<[^>]+>", "", tag)[:24]
            warnings.append(
                f"text box '{text}' needs {need:.0f}px and would reach y={float(y.group(1)) + need:.0f}; shorten it or widen the box"
            )
        new_head = head.replace(h.group(0), f'height="{need:.1f}"', 1)
        return tag.replace(head, new_head, 1)

    out = re.sub(r'<shape\b[^>]*type="text"[^>]*>.*?</shape>', grow, slide_xml, flags=re.S)
    return out, warnings
