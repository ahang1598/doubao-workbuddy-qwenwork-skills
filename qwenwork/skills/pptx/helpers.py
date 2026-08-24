"""Helpers for python-pptx authoring.

Small utilities for text-run formatting, smart-quotes, palette/font
token application. Used by ``components.py`` and the agent directly
from ``from_scratch.md`` workflows.

Keep this module *small*. Anything more elaborate than a single
shape transformation belongs in a component, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.shapes.autoshape import Shape
from pptx.text.text import _Run, _Paragraph, TextFrame
from pptx.util import Emu, Pt

__all__ = [
    "Palette",
    "FontPair",
    "Style",
    "smart_quotes",
    "set_text",
    "add_paragraph",
    "apply_palette",
    "apply_font_pair",
    "fill_solid",
    "no_border",
    "set_border",
    "no_fill",
    "no_shadow",
    "set_fill_alpha",
    "save_pptx",
]


# ---------- style tokens -----------------------------------------------------


@dataclass
class Palette:
    """Six-slot palette tokens passed to components and primitives."""

    primary: RGBColor
    secondary: RGBColor
    accent: RGBColor
    muted: RGBColor = field(default_factory=lambda: RGBColor(0x6B, 0x72, 0x80))
    bg: RGBColor = field(default_factory=lambda: RGBColor(0xF7, 0xF8, 0xFA))
    on_bg: RGBColor = field(default_factory=lambda: RGBColor(0x11, 0x18, 0x27))


@dataclass
class FontPair:
    header: str = "Calibri"
    body: str = "Calibri"


@dataclass
class Style:
    palette: Palette
    fonts: FontPair = field(default_factory=FontPair)


def save_pptx(prs, path) -> None:
    """Save a deck without python-pptx's blank placeholder thumbnail.

    Keeping that inherited thumbnail makes product preview cards render a
    white image instead of the first slide. Centralize the fix so every
    python-pptx authoring path gets the same package-safe behavior.
    """
    from scripts.strip_thumbnail import strip_thumbnail

    prs.save(path)
    strip_thumbnail(str(path))


# ---------- smart-quote handling --------------------------------------------


_SMART_MAP = {
    '"': "\u201c",   # left double; PowerPoint auto-pairs with U+201D inside paragraphs
    "'": "\u2018",
}


def smart_quotes(text: str) -> str:
    """Convert straight quotes to typographic curly quotes (deterministic).

    Pairs `"..."` as `“...”` and `'...'` as `‘...’`. Apostrophes
    inside words are treated as right-single quotes. This is best-effort
    — for nuanced typography, write the Unicode codepoints directly.
    """
    if not text:
        return text

    out: list[str] = []
    in_double = False
    in_single = False
    prev_is_alpha = False

    for ch in text:
        if ch == '"':
            out.append("\u201d" if in_double else "\u201c")
            in_double = not in_double
        elif ch == "'":
            if prev_is_alpha:
                out.append("\u2019")          # apostrophe / closing
            else:
                out.append("\u2019" if in_single else "\u2018")
                in_single = not in_single
        else:
            out.append(ch)
        prev_is_alpha = ch.isalpha()
    return "".join(out)


# ---------- text application -------------------------------------------------


def set_text(
    target,
    text: str,
    *,
    size: int | float | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    color: RGBColor | None = None,
    font: str | None = None,
    align: PP_ALIGN | None = None,
    smart: bool = True,
) -> _Run:
    """Set a shape/text-frame/paragraph's text content to a single run.

    Clears any existing runs. For multi-paragraph or mixed-run content,
    use ``add_paragraph()`` repeatedly.
    """
    text = smart_quotes(text) if smart else text

    if isinstance(target, Shape):
        tf = target.text_frame
    elif isinstance(target, TextFrame):
        tf = target
    else:
        raise TypeError(f"set_text target must be Shape or TextFrame, not {type(target)!r}")

    tf.clear()
    p = tf.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run()
    run.text = text
    _style_run(run, size=size, bold=bold, italic=italic, color=color, font=font)
    return run


def add_paragraph(
    tf: TextFrame,
    text: str,
    *,
    size: int | float | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    color: RGBColor | None = None,
    font: str | None = None,
    align: PP_ALIGN | None = None,
    space_before: int | float | None = None,
    space_after: int | float | None = None,
    smart: bool = True,
) -> _Paragraph:
    """Append a paragraph to a text-frame as a single run."""
    text = smart_quotes(text) if smart else text
    p = tf.add_paragraph()
    if align is not None:
        p.alignment = align
    if space_before is not None:
        p.space_before = Pt(space_before)
    if space_after is not None:
        p.space_after = Pt(space_after)
    run = p.add_run()
    run.text = text
    _style_run(run, size=size, bold=bold, italic=italic, color=color, font=font)
    return p


def _style_run(
    run: _Run,
    *,
    size,
    bold,
    italic,
    color,
    font,
) -> None:
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = color
    if font is not None:
        _set_run_font(run, font)


def _set_run_font(run: _Run, font: str) -> None:
    """Set Latin and East Asian typefaces on one run.

    python-pptx writes only ``a:latin`` for ``font.name``. Explicit ``a:ea``
    keeps CJK runs on the same intended family across PowerPoint, LibreOffice,
    and macOS instead of letting each renderer choose a different fallback.
    """
    run.font.name = font
    properties = run._r.get_or_add_rPr()
    east_asian = properties.find(qn("a:ea"))
    if east_asian is None:
        east_asian = OxmlElement("a:ea")
        latin = properties.find(qn("a:latin"))
        index = properties.index(latin) + 1 if latin is not None else 0
        properties.insert(index, east_asian)
    east_asian.set("typeface", font)


# ---------- palette / font token application --------------------------------


def apply_palette(shape: Shape, role: str, palette: Palette) -> None:
    """Fill a shape with a palette role.

    Roles: ``primary``, ``secondary``, ``accent``, ``muted``, ``bg``.
    """
    color = getattr(palette, role, None)
    if color is None:
        raise ValueError(f"unknown palette role {role!r}")
    fill_solid(shape, color)


def apply_font_pair(tf: TextFrame, fonts: FontPair, *, header_paragraphs: Iterable[int] = (0,)) -> None:
    """Apply header font to selected paragraphs, body font to the rest."""
    header_idx = set(header_paragraphs)
    for i, p in enumerate(tf.paragraphs):
        font = fonts.header if i in header_idx else fonts.body
        for run in p.runs:
            if run.font.name is None:
                _set_run_font(run, font)


# ---------- fill / line shortcuts -------------------------------------------


def fill_solid(shape: Shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def no_fill(shape: Shape) -> None:
    shape.fill.background()


def no_border(shape: Shape) -> None:
    shape.line.fill.background()


def set_border(shape: Shape, color: RGBColor, width_pt: float = 1.0) -> None:
    shape.line.color.rgb = color
    shape.line.width = Pt(width_pt)


def no_shadow(shape: Shape) -> None:
    """Kill any inherited theme outer-shadow on an autoshape.

    python-pptx ``add_shape`` shapes inherit the presentation theme's
    default shape style, which on most templates carries an outer shadow.
    There is no high-level toggle for this, so we inject an **empty**
    ``<a:effectLst/>`` into the shape's ``<p:spPr>``. An explicit empty
    effect list overrides the inherited one — the shape renders flat.

    Idempotent: replaces any existing effectLst with an empty one.
    """
    spPr = shape._element.spPr
    existing = spPr.find(qn("a:effectLst"))
    if existing is not None:
        spPr.remove(existing)
    spPr.append(spPr.makeelement(qn("a:effectLst"), {}))


def set_fill_alpha(shape: Shape, pct: float) -> None:
    """Make a shape's *solid* fill semi-transparent (true alpha, not a tint).

    ``pct`` is the **opacity** percentage 0..100 (100 = fully opaque,
    30 = mostly see-through). Call this AFTER ``fill_solid(shape, color)`` —
    it finds the ``<a:solidFill>/<a:srgbClr>`` and injects ``<a:alpha val=…>``
    (``val`` in thousandths of a percent, per OOXML). Used for area fills
    like the radar data polygon, where the grid/labels should show through.
    Does NOT add a shadow.

    Raises if the shape has no solid fill yet.
    """
    pct = max(0.0, min(100.0, float(pct)))
    spPr = shape._element.spPr
    solid = spPr.find(qn("a:solidFill"))
    srgb = solid.find(qn("a:srgbClr")) if solid is not None else None
    if srgb is None:
        raise ValueError("set_fill_alpha requires a solid fill — call fill_solid() first")
    existing = srgb.find(qn("a:alpha"))
    if existing is not None:
        srgb.remove(existing)
    srgb.append(srgb.makeelement(qn("a:alpha"), {"val": str(int(pct * 1000))}))


# ---------- geometry helpers (internal use; kept lightweight) ---------------


def emu_grid(origin_emu: tuple[int, int], size_emu: tuple[int, int], cols: int, rows: int):
    """Yield (col, row, x, y, w, h) for a uniform grid.

    Coordinates and sizes are in EMU. Use in components when you need
    consistent cell geometry; one helper here avoids re-deriving the math
    in every component.
    """
    ox, oy = origin_emu
    w, h = size_emu
    cw = w // cols
    rh = h // rows
    for r in range(rows):
        for c in range(cols):
            yield c, r, ox + c * cw, oy + r * rh, cw, rh
