"""
Skin · coursera_indigo · Coursera Indigo · Academic Cards

Auto-generated as part of the 40-skin mindmap sprint.
Hub decoration: rounded academic card + progress ring.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
from .editorial_atelier import (
    CanvasProfile,
    HERO_CANVAS as _EA_HERO_CANVAS,
    EMBED_CANVAS as _EA_EMBED_CANVAS,
    TX_CANVAS as _EA_TX_CANVAS,
    _txt,
    _rect,
    _line,
    _tint,
)


HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS


HUE = {
    'rust'        : '#0056D2',
    'orange'      : '#FFC33C',
    'magenta'     : '#DA5E5E',
    'blue'        : '#0056D2',
    'green'       : '#4EA458',
    'olive'       : '#7A8A5E',
    'cinnamon'    : '#8B6E4C',
    'gold_p'      : '#FFC33C',
}

HUE_ORDER: Tuple[str, ...] = (
    "rust", "orange", "magenta", "blue", "green", "olive", "cinnamon",
)


FONT_SERIF = 'Georgia, serif'
FONT_SANS = 'Open Sans, Inter, sans-serif'

TYPE_SCALE = {
    "title":         (26, FONT_SERIF, 700),
    "subtitle":      (13, FONT_SANS,  500),
    "section":       (10, FONT_SANS,  700),
    "column_header": (10, FONT_SANS,  700),
    "hub_name":      (19, FONT_SERIF, 800),
    "hub_name_xl":   (26, FONT_SERIF, 800),
    "block_title":   (17, FONT_SERIF, 700),
    "card_title":    (13, FONT_SANS,  800),
    "chip_kinase":   (14, FONT_SANS,  800),
    "chip_label":    (11, FONT_SANS,  700),
    "body_desc":     (10, FONT_SANS,  500),
    "micro_numeric": (10, FONT_SERIF, 700),
    "footer_read":   (12, FONT_SANS,  500),
    "footer_italic": (11, FONT_SANS,  500),
    "kicker_mini":   (9,  FONT_SANS,  700),
    "source_tag":    (10, FONT_SANS,  700),
}


PALETTE_OBJ = Palette(
    name='Coursera Indigo · Academic Cards',
    bg='#FFFFFF',
    bg_alt='#F4F6FB',
    bg_dim='#F4F6FB',
    ink='#0F1B47',
    gray='rgba(15,27,71,0.55)',
    hair='#0F1B47',
    primary=HUE["rust"],
    primary_dim=HUE["orange"],
    accent=HUE["gold_p"],
    accent_dim=HUE["cinnamon"],
    positive=HUE["green"],
    negative=HUE["magenta"],
    head_family=FONT_SERIF,
    body_family=FONT_SANS,
    mono_family=FONT_SANS,
    kicker_letter_spacing=2.5,
    kicker_case="upper",
    section_numbering="arabic",
    folio_style="hairline",
    title_style="serif_bold",
    subtitle_style="sans_italic",
    figure_caption_prefix="Fig.",
    signature_note="COURSERA INDIGO",
)

# alias for registry contract
COURSERA_INDIGO = PALETTE_OBJ
PALETTE = PALETTE_OBJ


_FILTER_DEFS = """<filter id="ea-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="0" dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope="0.22"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/><feOffset dx="0" dy="2.5"/><feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/></filter>"""


def _gradient_defs(hues: Sequence[str]) -> str:
    out: List[str] = []
    for name in hues:
        c = HUE.get(name, HUE["rust"])
        gid = f"ea-r-{name}"
        out.append(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="0.75"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0.35"/>'
            f'</linearGradient>'
        )
    return "".join(out)


def _marker_defs(hues: Sequence[str]) -> str:
    out: List[str] = []
    for name in hues:
        c = HUE.get(name, HUE["rust"])
        mid = f"ea-arr-{name}"
        out.append(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 9 5 L 0 10 Z" fill="{c}"/></marker>'
        )
    out.append(
        '<marker id="ea-tbar-gray" viewBox="0 0 10 10" refX="7" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto">'
        '<line x1="7" y1="0" x2="7" y2="10" '
        'stroke="rgba(94,80,62,0.85)" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


def _resolve_hue(hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return HUE["rust"]
    if hue_key_or_hex.startswith("#"):
        return hue_key_or_hex
    return HUE.get(hue_key_or_hex, HUE["rust"])


def svg_defs(hues: Sequence[str] = HUE_ORDER,
             include_markers: bool = True,
             include_gradients: bool = True) -> str:
    inner = _FILTER_DEFS
    if include_gradients:
        inner += _gradient_defs(hues)
    if include_markers:
        inner += _marker_defs(hues)
    return f"<defs>{inner}</defs>"


def hero_chrome(*, kicker: str = "",
                title: str = "",
                subtitle: str = "",
                column_headers: Optional[Sequence[Tuple[str, float]]] = None,
                encoding_note_right: str = "",
                palette: Palette = PALETTE_OBJ,
                canvas: CanvasProfile = HERO_CANVAS,
                include_bg: bool = True) -> str:
    is_embed = (canvas.w == 900 and canvas.h == 336)
    title_sz = 17 if is_embed else 26
    subtitle_sz = 10 if is_embed else 13
    parts: List[str] = []
    if include_bg:
        parts.append(_rect(0, 0, canvas.w, canvas.h, fill=palette.bg))
    if title:
        parts.append(_txt(canvas.margin_x, canvas.title_y, title,
                          size=title_sz, family=FONT_SERIF, weight=700,
                          fill=palette.ink, letter_em=0.01))
    if subtitle:
        parts.append(_txt(canvas.margin_x, canvas.subtitle_y, subtitle,
                          size=subtitle_sz, family=FONT_SANS, weight=500,
                          fill=palette.gray, letter_em=0.04))
    parts.append(_line(canvas.margin_x, canvas.title_hair_y,
                       canvas.w - canvas.margin_x, canvas.title_hair_y,
                       stroke=palette.primary, sw=0.8, opacity=0.55))
    return "".join(parts)


def hero_footer(*, caption: str = "",
                source: str = "",
                read_lines: Optional[Sequence[str]] = None,
                italic_last: bool = False,
                palette: Palette = PALETTE_OBJ,
                canvas: CanvasProfile = HERO_CANVAS,
                min_read_chars: int = 40) -> str:
    _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
    return ""


def tspan(word: str, *, color: str = HUE["rust"], weight: int = 700) -> str:
    c = _resolve_hue(color) if not color.startswith("rgba") else color
    return (f'<tspan font-weight="{weight}" fill="{c}">'
            f'{esc(word)}</tspan>')


class CourseraIndigoSkin:
    name = 'coursera_indigo'

    def draw_node(self, x, y, w, h, label, palette, kind="", **kwargs):
        pal = palette or PALETTE_OBJ
        if kind == "mindmap_hub":
            return self._mindmap_hub(x, y, w, h, label, pal, **kwargs)
        return None

    def _mindmap_hub(self, x, y, w, h, name, pal, **kw):
        primary = _resolve_hue("rust")
        accent = _resolve_hue("gold_p")
        kicker = kw.get("kicker", "")
        stat = kw.get("stat", "")
        stat_note = kw.get("stat_note", "")
        cx = kw.get("hub_cx", x + w / 2)
        cy = kw.get("hub_cy", y + h / 2)
        r = kw.get("hub_r", w / 2)
        parts = []

        # Coursera rounded card + progress ring
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{pal.bg}" stroke="{primary}" stroke-width="1.6"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r-4}" fill="none" stroke="{primary}" stroke-width="4" opacity="0.15" stroke-dasharray="{r*4} {r*2}"/>')
        if kicker:
            parts.append(f'<text x="{cx}" y="{cy-28}" text-anchor="middle" font-family="{FONT_SANS}" font-size="9" font-weight="700" fill="{primary}" letter-spacing="0.22em">{esc(kicker.upper())}</text>')
        if name:
            parts.append(f'<text x="{cx}" y="{cy+4}" text-anchor="middle" font-family="{FONT_SANS}" font-size="22" font-weight="700" fill="{pal.ink}">{esc(name)}</text>')
        if stat:
            parts.append(f'<text x="{cx}" y="{cy+28}" text-anchor="middle" font-family="{FONT_SANS}" font-size="15" font-weight="700" fill="{primary}">{esc(stat)}</text>')
        if stat_note:
            parts.append(f'<text x="{cx}" y="{cy+46}" text-anchor="middle" font-family="{FONT_SANS}" font-size="7.5" fill="{pal.gray}" letter-spacing="0.14em">{esc(stat_note.upper())}</text>')

        return "".join(parts)


SKIN_INSTANCE = CourseraIndigoSkin()


__all__ = [
    "COURSERA_INDIGO", "PALETTE",
    "CourseraIndigoSkin", "SKIN_INSTANCE",
    "CanvasProfile", "HERO_CANVAS", "EMBED_CANVAS", "TX_CANVAS",
    "HUE", "HUE_ORDER", "TYPE_SCALE", "FONT_SERIF", "FONT_SANS",
    "svg_defs", "hero_chrome", "hero_footer", "tspan",
]
