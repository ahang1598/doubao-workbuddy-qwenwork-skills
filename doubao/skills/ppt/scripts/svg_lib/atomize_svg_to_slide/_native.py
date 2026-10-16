"""Small, explicit SML constructors in Slides canvas pixels."""

from __future__ import annotations

from decimal import Decimal
import math
from numbers import Real
import re
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

from ._compose import _sml_literal_color
from ._gradient import _rgba
from ._serialize import _SML

if TYPE_CHECKING:
    from ..drawing_lib._geometry import Box


def _string(value, name, *, nonempty=False):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if nonempty and not value.strip():
        raise ValueError(f"{name} must not be empty")
    for character in value:
        code = ord(character)
        if not (
            code in (9, 10, 13) or 0x20 <= code <= 0xD7FF or 0xE000 <= code <= 0xFFFD or 0x10000 <= code <= 0x10FFFF
        ):
            raise ValueError(f"{name} contains a character not allowed in XML 1.0")
    return value


def _number(value, name, *, minimum=None, maximum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, not a boolean or string")
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if positive and number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return repr(number)


def _point(value, name):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise TypeError(f"{name} must be a two-number (x, y) point")
    # XType/YType bounds come from slides_xml_schema_definition.xml. They are
    # protocol limits, not a 960x540 page boundary or a clipping operation.
    return (
        _number(value[0], name + ".x", minimum=-8640, maximum=10560),
        _number(value[1], name + ".y", minimum=-4860, maximum=5940),
    )


def _color(value):
    _string(value, "color", nonempty=True)
    literal = _sml_literal_color(value.strip()).lower()
    try:
        red, green, blue, _ = _rgba(literal)
    except (ValueError, OverflowError) as error:
        raise ValueError("color must be a supported HEX/CSS named color or RGB(A) solid color") from error
    # Reuse existing color parsing, then emit native integer channels and a
    # decimal alpha (SML does not accept CSS shorthand ".5" or an exponent).
    if literal.startswith("rgba("):
        alpha = format(Decimal(literal.rsplit(",", 1)[1].rstrip(")").strip()), "f")
        return f"rgba({red},{green},{blue},{alpha})"
    return f"rgb({red},{green},{blue})"


def _alignment(value, name, choices):
    _string(value, name)
    if value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}")
    return value


def native_text(
    text: str,
    box: Box | tuple[float, float, float, float] | list[float],
    *,
    font_size: float,
    font_family: str = "思源黑体",
    color: str = "rgb(0,0,0)",
    bold: bool = False,
    text_align: str = "left",
    vertical_align: str = "top",
    wrap: bool = False,
) -> str:
    """Return one independent native ``<shape type="text">`` XML string.

    ``box`` is an (x, y, width, height) tuple/list or provides those four
    named attributes (for example, ``svg_drawing.Box``).
    Its values and ``font_size`` are already Slides canvas pixels; no SVG
    coordinate mapping is applied. Width/height must be positive, and the
    explicit font size must be within SML's [1, 4000] range. The caller owns
    the box, font choice and fit. Nothing is measured, clipped or resized.

    Plain text is XML-escaped and always placed inside ``<content><p>``.
    LF is represented by ``<br/>``; CRLF/CR are normalized to LF. Tabs use
    ``<tab/>``. Empty text and leading/trailing/blank lines are retained.
    Spaces remain in the XML; native SML whitespace/rendering rules apply.
    ``bold`` requires a bool, not a CSS font-weight value. Color accepts the
    existing HEX/CSS-name vocabulary or RGB(A), serialized as native RGB(A).

    Auto-fit is disabled; wrapping is off unless ``wrap=True`` (use it for body text and
    multi-sentence notes so long lines break inside the box instead of overflowing it). The result has its own SML
    namespace and may be passed directly to ``compose_slide(page, result)``.
    Rich markup passed as ``text`` is displayed literally, not interpreted.
    """
    _string(text, "text")
    if isinstance(box, (tuple, list)):
        if len(box) != 4:
            raise TypeError("box tuple/list must contain (x, y, width, height)")
        values = box
    else:
        try:
            values = (box.x, box.y, box.width, box.height)
        except AttributeError as error:
            raise TypeError("box must be an (x, y, width, height) tuple/list or provide those attributes") from error
    x, y = _point(values[:2], "box")
    width = _number(values[2], "box.width", positive=True)
    height = _number(values[3], "box.height", positive=True)
    size = _number(font_size, "font_size", minimum=1, maximum=4000)
    family = _string(font_family, "font_family", nonempty=True)
    if type(bold) is not bool:
        raise TypeError("bold must be a bool")
    if type(wrap) is not bool:
        raise TypeError("wrap must be a bool")
    align = _alignment(text_align, "text_align", ("left", "center", "right", "justify", "dist"))
    vertical = _alignment(vertical_align, "vertical_align", ("top", "middle", "bottom"))
    shape = ET.Element(
        "shape",
        {
            "xmlns": _SML,
            "type": "text",
            "topLeftX": x,
            "topLeftY": y,
            "width": width,
            "height": height,
        },
    )
    content = ET.SubElement(
        shape,
        "content",
        {
            "fontSize": size,
            "fontFamily": family,
            "color": _color(color),
            "bold": str(bold).lower(),
            "textAlign": align,
            "verticalAlign": vertical,
            "wrap": "true" if wrap else "false",
            "autoFit": "no-auto-fit",
        },
    )
    paragraph = ET.SubElement(content, "p")
    chunks = re.split(r"([\n\t])", text.replace("\r\n", "\n").replace("\r", "\n"))
    paragraph.text = chunks[0]
    for separator, tail in zip(chunks[1::2], chunks[2::2]):
        ET.SubElement(paragraph, "br" if separator == "\n" else "tab").tail = tail
    return ET.tostring(shape, encoding="unicode")


def native_line(start, end, *, color: str = "rgb(0,0,0)", width: int = 1) -> str:
    """Return one independent native straight ``<line>`` XML string.

    ``start``/``end`` are (x, y) points already in Slides canvas pixels.
    They become startX/startY/endX/endY, with a required ``<border>`` child.
    ``width`` is a nonnegative integer value in canvas pixels, as allowed by
    SML BorderType; 2.0 is accepted, 2.5 is rejected rather than rounded.
    Zero width and coincident endpoints are legal and are not made visible
    automatically. Supported solid colors are normalized just as for text.

    This is a plain line, with no arrows, dashes, layout, SVG mapping, IDs or
    side effects. Pass the returned string directly to ``compose_slide``.
    """
    start_x, start_y = _point(start, "start")
    end_x, end_y = _point(end, "end")
    if isinstance(width, bool) or not isinstance(width, Real):
        raise TypeError("width must be a nonnegative integer value")
    if isinstance(width, int):
        if width < 0:
            raise ValueError("width must be a nonnegative integer value")
        border_width = str(width)
    else:
        number = float(_number(width, "width", minimum=0))
        if not number.is_integer():
            raise ValueError("width must be a nonnegative integer value; fractional widths are not rounded")
        border_width = str(int(number))
    line = ET.Element(
        "line",
        {
            "xmlns": _SML,
            "type": "line",
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
        },
    )
    ET.SubElement(line, "border", {"color": _color(color), "width": border_width})
    return ET.tostring(line, encoding="unicode")


_NUM = re.compile(r"[-−+]?\d+(?:\.\d+)?")
_MATH = re.compile(r"\$([^$\n]+)\$")
_LEAD = re.compile(r"^(.{1,24}?[：:])\s*(.+)$", re.S)


def _box3(box):
    if isinstance(box, (tuple, list)):
        if len(box) not in (3, 4):
            raise TypeError("box must be (x, y, width) or (x, y, width, height)")
        return tuple(float(v) for v in box) + ((None,) if len(box) == 3 else ())
    return float(box.x), float(box.y), float(box.width), float(box.height)


def _inline(text):
    """Escaped run text; ``$\\mathrm{N_2O}$``-style spans (containing \\ ^ _ { }) become <formula>."""
    from xml.sax.saxutils import escape

    out, pos = [], 0
    for m in _MATH.finditer(text):
        if not re.search(r"[\\^_{}]", m.group(1)):
            continue  # "$5 and $10" stays text
        out.append(escape(text[pos : m.start()]))
        out.append(f"<formula><latex><![CDATA[{m.group(1)}]]></latex></formula>")
        pos = m.end()
    return "".join(out) + escape(text[pos:])


def _fit_height(content_xml, width, fallback):
    try:
        import sys
        from pathlib import Path

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from text_fit import text_height  # the lint's own estimator

        return text_height(content_xml, width=width, font_size=0)
    except Exception:  # noqa: BLE001 — a rough estimate still sizes the box
        return fallback


def native_bullets(
    items,
    box,
    *,
    font_size=14,
    color="rgb(40,40,40)",
    font_family="思源黑体",
    lead_bold=True,
    lead_color=None,
    bullet="•",
    sub_bullet="–",
    bullet_color=None,
    line_spacing=1.3,
    para_gap=6,
    text_align="left",
) -> str:
    """Bullet list as ONE native text shape: ``<ul><li><p>`` per item, bold "术语：" lead-ins, wrap on.

    ``items``: strings ("术语：说明" → bold "术语：" + normal text when ``lead_bold``; the lead is the
    text up to the first "：/:" within 24 characters), ``(lead, text)`` tuples, or a list right after
    an item for its sub-points (level 2, ``sub_bullet``). ``bullet=None`` gives plain paragraphs
    (still with bold leads). ``$...$`` containing LaTeX (\\ ^ _ { }) becomes an inline ``<formula>``.
    ``box`` is (x, y, width) or (x, y, width, height); the height is estimated with the lint's own
    text estimator and only ever grows the given height. ``para_gap`` is the px gap after each item.
    """
    x, y, w, h = _box3(box)
    size = _number(font_size, "font_size", minimum=1, maximum=4000)
    ink = _color(color)
    lead_ink = _color(lead_color) if lead_color else None
    if isinstance(items, str):
        items = [items]

    def para(item, level):
        if isinstance(item, tuple) and len(item) == 2:
            lead, body = (_string(s, "bullet item") for s in item)
            lead = lead if not lead or lead[-1] in "：:，,。." else lead + "："
        else:
            _string(item, "bullet item")
            m = _LEAD.match(item) if lead_bold else None
            lead, body = (m.group(1), m.group(2)) if m else ("", item)
        attrs = f' afterLineSpacing="fixed:{para_gap:g}"' if para_gap else ""
        if level > 1:
            attrs += f' level="{level}"' + (f' bulletChar="{sub_bullet}"' if bullet and sub_bullet else "")
        run = ""
        if lead:
            tint = f' color="{lead_ink}"' if lead_ink else ""
            run = f'<span bold="true"{tint}>{_inline(lead)}</span>'
        return f"<p{attrs}>{run}{_inline(body)}</p>"

    paras = []
    for item in items:
        if isinstance(item, list):
            paras += [para(sub, 2) for sub in item]
        else:
            paras.append(para(item, 1))
    if not paras:
        raise ValueError("items must not be empty")
    if bullet:
        head = f'<ul bulletChar="{bullet}"' + (f' bulletColor="{_color(bullet_color)}"' if bullet_color else "") + ">"
        body = head + "".join(f"<li>{p}</li>" for p in paras) + "</ul>"
    else:
        body = "".join(paras)
    from xml.sax.saxutils import quoteattr

    content = (
        f'<content fontSize="{float(size):g}" fontFamily={quoteattr(font_family)} color="{ink}" '
        f'textAlign="{_alignment(text_align, "text_align", ("left", "center", "right", "justify"))}" '
        f'verticalAlign="top" lineSpacing="multiple:{line_spacing:g}" wrap="true" autoFit="no-auto-fit">'
        f"{body}</content>"
    )
    rough = sum(1 + len(p) * float(size) // max(w, 1) for p in paras) * float(size) * line_spacing
    need = _fit_height(content, w, rough)
    if h is not None and need > h + 1:
        import warnings

        warnings.warn(
            f"native_bullets: text needs {need:.0f}px, box height {h:.0f}px — grown to fit; "
            "shorten items or widen the box if this pushes into other content",
            stacklevel=2,
        )
    height = max(need, h or 0)
    return (
        f'<shape xmlns="{_SML}" type="text" topLeftX="{x:g}" topLeftY="{y:g}" width="{w:g}" '
        f'height="{height:.0f}">{content}</shape>'
    )


def page_frame(
    title,
    *body,
    kicker=None,
    source=None,
    page_no=None,
    note=None,
    background=None,
    title_color="rgb(30,30,30)",
    accent="rgb(91,16,97)",
    muted="rgb(110,110,110)",
    font_family="思源黑体",
    title_size=26,
) -> str:
    """A complete ``<slide>``: standard title / kicker / source / page number on 960×540 plus ``body``.

    ``body`` are native element strings (``native_bullets``, ``native_table``, ``native_text`` …) laid
    out by the caller in the body area x 40–920, y 96–496 (y 104 when the title wraps to two lines).
    Layout: ``kicker`` (section label, 12px accent bold) at y 20; title (``title_size`` bold, wrap on)
    at y 38 (y 28 without kicker); ``source`` (10px muted, wraps upward) bottom-left ending at y 528;
    ``page_no`` bottom-right. ``note`` becomes the speaker notes (``\\n`` = new paragraph);
    ``background`` fills the page. Pass chart/drawing fragments to ``publish_slide`` as usual.
    """
    from xml.sax.saxutils import escape

    if any("<slide" in str(p) for p in body):
        raise TypeError(
            "page_frame body takes native elements; pass chart_slide()/to_slide() fragments to "
            "publish_slide(page_frame(...), fragment, ...) instead"
        )

    def fitted(text, box, **kw):
        """native_text with wrap on, its height grown to what the lint estimator needs."""
        xml = native_text(str(text), box, font_family=font_family, wrap=True, **kw)
        need = _fit_height(re.search(r"<content.*</content>", xml, re.S).group(0), box[2], box[3])
        return need, xml if need <= box[3] + 1 else native_text(
            str(text), (*box[:3], need), font_family=font_family, wrap=True, **kw
        )

    top, parts = 28, []
    if kicker:
        parts.append(
            native_text(str(kicker), (40, 20, 700, 18), font_size=12, color=accent, bold=True, font_family=font_family)
        )
        top = 38
    parts.append(
        fitted(title, (40, top, 880, round(title_size * 1.7)), font_size=title_size, color=title_color, bold=True)[1]
    )
    parts.extend(body)
    if source:
        sh, _ = fitted(source, (40, 510, 800, 18), font_size=10, color=muted)
        parts.append(fitted(source, (40, 528 - max(sh, 18), 800, max(sh, 18)), font_size=10, color=muted)[1])
    if page_no is not None:
        parts.append(
            native_text(
                str(page_no), (860, 510, 60, 18), font_size=10, color=muted, text_align="right", font_family=font_family
            )
        )
    style = f'<style><fill><fillColor color="{_color(background)}"/></fill></style>' if background else ""
    notes = ""
    if note:
        notes = "<note><content>" + "".join(f"<p>{escape(p)}</p>" for p in str(note).split("\n")) + "</content></note>"
    inner = "".join(re.sub(r'^(<\w+) xmlns="[^"]+"', r"\1", p) for p in parts)
    return f'<slide xmlns="{_SML}">{style}<data>{inner}</data>{notes}</slide>'


def _best_cells(rows, best, header, ncol):
    """(row, col) pairs holding the best value of each column named in ``best``."""
    if not best:
        return set()
    if isinstance(best, dict):
        names = [str(c) for c in rows[0]] if header else []
        spec = {}
        for col, how in best.items():
            j = col if isinstance(col, int) else names.index(str(col)) if str(col) in names else None
            if j is None:
                raise ValueError(f"best: column {col!r} is not a header name or index")
            spec[j] = how
    else:
        spec = dict(enumerate(best))
    out = set()
    for j, how in spec.items():
        how = {"↑": "max", "↓": "min", "max": "max", "min": "min"}.get(how or "")
        if how is None or j >= ncol:
            continue
        values = {}
        for i in range(1 if header else 0, len(rows)):
            m = _NUM.search(str(rows[i][j]) if j < len(rows[i]) else "")
            if m:
                values[i] = float(m.group(0).replace("−", "-"))
        if values:
            target = (max if how == "max" else min)(values.values())
            out |= {(i, j) for i, v in values.items() if v == target}
    return out


def native_table(
    rows,
    box,
    *,
    header=True,
    col_widths=None,
    font_size=11,
    header_size=None,
    font_family="思源黑体",
    color="rgb(40,40,40)",
    header_color=None,
    header_fill=None,
    rule_color="rgb(60,60,60)",
    zebra=None,
    align=None,
    best=None,
) -> str:
    """Academic three-line table (top rule, header rule, bottom rule) as one native ``<table>``.

    ``best`` bolds the best value per column (benchmark tables): one entry per column such as
    ``[None, '↑', '↓']`` ('↑'/'max' = higher is better, '↓'/'min' = lower), or a dict
    ``{'Acc': 'max', 3: 'min'}`` keyed by header name or column index; ties are all bolded and the
    first number in a cell is compared ("85.3±0.2" → 85.3).

    ``rows`` is a list of rows of cell strings (first row = header when ``header``); ``box`` is
    (x, y, width, height). ``col_widths`` are pixel widths (omit for an even split); ``align`` is one
    'left'/'center'/'right' per column (defaults: first column left, others center). Row heights are
    sized from ``font_size`` and the longest wrapped cell so text fits. ``zebra`` tints alternate rows.
    """
    from xml.sax.saxutils import escape

    if not rows or not all(isinstance(r, (list, tuple)) for r in rows):
        raise TypeError("rows must be a non-empty list of row lists")
    ncol = max(len(r) for r in rows)
    winners = _best_cells(rows, best, header, ncol)
    x, y, w, h = (float(v) for v in box)
    widths = list(col_widths) if col_widths else [w / ncol] * ncol
    if len(widths) != ncol:
        raise ValueError(f"col_widths needs {ncol} values")
    align = list(align) if align else ["left"] + ["center"] * (ncol - 1)
    header_size = header_size or font_size
    color, rule = _color(color), _color(rule_color)
    hcolor = _color(header_color) if header_color else color

    def lines(text, width, size):
        per_line = max(1.0, (width - 10) / (size * 0.98))  # CJK-width estimate
        return max(1, -(-sum(1 if ord(c) > 0x2E80 else 0.55 for c in str(text)) // per_line))

    heights = []
    for i, row in enumerate(rows):
        size = header_size if header and i == 0 else font_size
        n = max(lines(c, wd, size) for c, wd in zip(list(row) + [""] * (ncol - len(row)), widths))
        heights.append(max(size * 2.0, n * size * 1.45 + 10))
    scale = h / sum(heights) if sum(heights) < h else 1.0
    heights = [hh * scale for hh in heights]
    if sum(heights) > h + 1:
        import warnings

        warnings.warn(
            f"native_table: rows need ~{sum(heights):.0f}px but box height is {h:g}px — the table grows "
            f"downward to y≈{y + sum(heights):.0f} and may cover the footer; enlarge the box, cut rows, "
            "widen columns or lower font_size",
            stacklevel=2,
        )
    out = [
        f'<table xmlns="{_SML}" topLeftX="{x:g}" topLeftY="{y:g}" width="{w:g}" height="{sum(heights):.0f}">',
        "<colgroup>" + "".join(f'<col width="{wd:.0f}"/>' for wd in widths) + "</colgroup>",
    ]
    last = len(rows) - 1
    for i, row in enumerate(rows):
        is_head = header and i == 0
        out.append(f'<tr height="{heights[i]:.0f}">')
        for j in range(ncol):
            text = row[j] if j < len(row) else ""
            borders = ""
            if i == 0:
                borders += f'<borderTop color="{rule}" width="2"/>'
            if is_head:
                borders += f'<borderBottom color="{rule}" width="1"/>'
            if i == last:
                borders += f'<borderBottom color="{rule}" width="2"/>'
            fill = ""
            if is_head and header_fill:
                fill = f'<fill><fillColor color="{_color(header_fill)}"/></fill>'
            elif zebra and not is_head and i % 2 == 0:
                fill = f'<fill><fillColor color="{_color(zebra)}"/></fill>'
            size = header_size if is_head else font_size
            bold = ' bold="true"' if is_head or (i, j) in winners else ""
            body = escape(str(text)).replace("\n", "<br/>")
            out.append(
                f'<td>{borders}{fill}<content fontSize="{size:g}" fontFamily="{escape(font_family)}" '
                f'color="{hcolor if is_head else color}" textAlign="{align[j]}" verticalAlign="middle"'
                f"{bold}><p>{body}</p></content></td>"
            )
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)
