"""Generated relation skin facades.

Most relation skins only differ by color, font, chrome tokens, and a small
mindmap hub motif. Keep those as data instead of one Python module per theme.
`registry.get_skin()` exposes each entry as a ModuleType-compatible facade so
existing `--skin <name>` usage remains unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Dict, Mapping, Optional, Sequence, Tuple

from ..engine import esc
from ..palettes import Palette
from .editorial_atelier import (
    CanvasProfile,
    EMBED_CANVAS as _EA_EMBED_CANVAS,
    HERO_CANVAS as _EA_HERO_CANVAS,
    TX_CANVAS as _EA_TX_CANVAS,
    _line,
    _rect,
    _txt,
)

HERO_CANVAS = _EA_HERO_CANVAS
EMBED_CANVAS = _EA_EMBED_CANVAS
TX_CANVAS = _EA_TX_CANVAS
HUE_ORDER: Tuple[str, ...] = ("rust", "orange", "magenta", "blue", "green", "olive", "cinnamon")

_FILTER_DEFS = """<filter id="ea-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceAlpha" stdDeviation="2"/><feOffset dx="0" dy="1.5"/><feComponentTransfer><feFuncA type="linear" slope="0.22"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="3.5"/><feOffset dx="0" dy="2.5"/><feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="ea-hub-halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur in="SourceGraphic" stdDeviation="5.5"/></filter>"""


@dataclass(frozen=True)
class GeneratedSkinSpec:
    class_name: str
    alias: str
    decor: str
    hue: Mapping[str, str]
    font_serif: str
    font_sans: str
    palette: Mapping[str, object]


def _type_scale(font_serif: str, font_sans: str) -> Dict[str, Tuple[int, str, int]]:
    return {
        "title": (26, font_serif, 700),
        "subtitle": (13, font_sans, 500),
        "section": (10, font_sans, 700),
        "column_header": (10, font_sans, 700),
        "hub_name": (19, font_serif, 800),
        "hub_name_xl": (26, font_serif, 800),
        "block_title": (17, font_serif, 700),
        "card_title": (13, font_sans, 800),
        "chip_kinase": (14, font_sans, 800),
        "chip_label": (11, font_sans, 700),
        "body_desc": (10, font_sans, 500),
        "micro_numeric": (10, font_serif, 700),
        "footer_read": (12, font_sans, 500),
        "footer_italic": (11, font_sans, 500),
        "kicker_mini": (9, font_sans, 700),
        "source_tag": (10, font_sans, 700),
    }


def _gradient_defs(hue: Mapping[str, str], hues: Sequence[str]) -> str:
    out = []
    for name in hues:
        c = hue.get(name, hue["rust"])
        out.append(
            f'<linearGradient id="ea-r-{name}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="0.75"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0.35"/>'
            f"</linearGradient>"
        )
    return "".join(out)


def _marker_defs(hue: Mapping[str, str], hues: Sequence[str], gray: str) -> str:
    out = []
    for name in hues:
        c = hue.get(name, hue["rust"])
        out.append(
            f'<marker id="ea-arr-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto">'
            f'<path d="M 0 0 L 9 5 L 0 10 Z" fill="{c}"/></marker>'
        )
    out.append(
        '<marker id="ea-tbar-gray" viewBox="0 0 10 10" refX="7" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto">'
        f'<line x1="7" y1="0" x2="7" y2="10" stroke="{gray}" stroke-width="2.6"/></marker>'
    )
    return "".join(out)


def _resolve_hue(hue: Mapping[str, str], hue_key_or_hex: str) -> str:
    if not hue_key_or_hex:
        return hue["rust"]
    if hue_key_or_hex.startswith("#") or hue_key_or_hex.startswith("rgba"):
        return hue_key_or_hex
    return hue.get(hue_key_or_hex, hue["rust"])


def _palette_from_spec(spec: GeneratedSkinSpec) -> Palette:
    return Palette(**dict(spec.palette))


def _draw_hub_motif(parts, module: ModuleType, cx: float, cy: float, r: float, pal: Palette) -> None:
    name = module.__skin_name__
    primary = _resolve_hue(module.HUE, "rust")
    accent = _resolve_hue(module.HUE, "gold_p")
    if any(token in name for token in ("bauhaus", "riso")):
        parts.append(f'<circle cx="{cx - r * 0.18:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{primary}" opacity="0.92"/>')
        parts.append(
            f'<circle cx="{cx + r * 0.22:.1f}" cy="{cy:.1f}" r="{r * 0.72:.1f}" fill="{accent}" opacity="0.72"/>'
        )
    elif any(token in name for token in ("terminal", "blueprint", "notebook", "chalkboard")):
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{pal.bg_alt}" stroke="{primary}" stroke-width="2" stroke-dasharray="7 5"/>'
        )
        parts.append(
            f'<line x1="{cx - r + 10:.1f}" y1="{cy:.1f}" x2="{cx + r - 10:.1f}" y2="{cy:.1f}" stroke="{accent}" stroke-width="1" opacity="0.65"/>'
        )
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy - r + 10:.1f}" x2="{cx:.1f}" y2="{cy + r - 10:.1f}" stroke="{accent}" stroke-width="1" opacity="0.65"/>'
        )
    elif any(token in name for token in ("arxiv", "swiss", "bain", "deloitte")):
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{pal.bg}" stroke="{primary}" stroke-width="1.2"/>')
        parts.append(
            f'<line x1="{cx - r + 10:.1f}" y1="{cy - r + 18:.1f}" x2="{cx + r - 10:.1f}" y2="{cy - r + 18:.1f}" stroke="{primary}" stroke-width="0.8"/>'
        )
        parts.append(
            f'<line x1="{cx - r + 10:.1f}" y1="{cy + r - 18:.1f}" x2="{cx + r - 10:.1f}" y2="{cy + r - 18:.1f}" stroke="{primary}" stroke-width="0.8"/>'
        )
    elif any(token in name for token in ("oxford", "symposium", "wabi")):
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{primary}" opacity="0.95"/>')
        parts.append(
            f'<rect x="{cx - r + 12:.1f}" y="{cy - r + 12:.1f}" width="24" height="24" fill="{accent}" opacity="0.82"/>'
        )
    else:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="none" stroke="{accent}" stroke-width="2" opacity="0.28"/>'
        )
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{primary}" opacity="0.96"/>')


class GeneratedTokenSkin:
    def __init__(self, module: ModuleType):
        self._module = module
        self.name = module.__skin_name__

    def draw_node(self, x, y, w, h, label, palette, kind="", **kwargs):
        if kind != "mindmap_hub":
            return None
        pal = palette or self._module.PALETTE
        return self._mindmap_hub(x, y, w, h, label, pal, **kwargs)

    def _mindmap_hub(self, x, y, w, h, name, pal, **kw):
        primary = _resolve_hue(self._module.HUE, "rust")
        accent = _resolve_hue(self._module.HUE, "gold_p")
        kicker = kw.get("kicker", "")
        stat = kw.get("stat", "")
        stat_note = kw.get("stat_note", "")
        cx = kw.get("hub_cx", x + w / 2)
        cy = kw.get("hub_cy", y + h / 2)
        r = kw.get("hub_r", w / 2)
        parts = []
        _draw_hub_motif(parts, self._module, cx, cy, r, pal)
        text_fill = pal.bg if primary != pal.bg else pal.ink
        if kicker:
            parts.append(
                f'<text x="{cx}" y="{cy - 28}" text-anchor="middle" font-family="{self._module.FONT_SANS}" font-size="8.5" font-weight="700" fill="{accent}" letter-spacing="0.28em">{esc(str(kicker).upper())}</text>'
            )
        if name:
            parts.append(
                f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-family="{self._module.FONT_SERIF}" font-size="22" font-weight="700" fill="{text_fill}">{esc(str(name))}</text>'
            )
        if stat:
            parts.append(
                f'<text x="{cx}" y="{cy + 30}" text-anchor="middle" font-family="{self._module.FONT_SERIF}" font-size="14" font-weight="700" font-style="italic" fill="{accent}">{esc(str(stat))}</text>'
            )
        if stat_note:
            parts.append(
                f'<text x="{cx}" y="{cy + 48}" text-anchor="middle" font-family="{self._module.FONT_SANS}" font-size="7" fill="{text_fill}" opacity="0.7" letter-spacing="0.14em">{esc(str(stat_note).upper())}</text>'
            )
        return "".join(parts)


def create_generated_skin_module(name: str) -> ModuleType:
    spec = GENERATED_SKIN_SPECS[name]
    mod = ModuleType(f"svg_lib.relation.skins.{name}")
    mod.__package__ = "svg_lib.relation.skins"
    mod.__skin_name__ = name
    mod.__doc__ = f"Generated relation skin facade for {name}. {spec.decor}"
    mod.HUE = dict(spec.hue)
    mod.HUE_ORDER = HUE_ORDER
    mod.FONT_SERIF = spec.font_serif
    mod.FONT_SANS = spec.font_sans
    mod.TYPE_SCALE = _type_scale(spec.font_serif, spec.font_sans)
    mod.CanvasProfile = CanvasProfile
    mod.HERO_CANVAS = HERO_CANVAS
    mod.EMBED_CANVAS = EMBED_CANVAS
    mod.TX_CANVAS = TX_CANVAS
    mod.PALETTE = _palette_from_spec(spec)
    setattr(mod, spec.alias, mod.PALETTE)

    def svg_defs(hues: Sequence[str] = HUE_ORDER, include_markers: bool = True, include_gradients: bool = True) -> str:
        inner = _FILTER_DEFS
        if include_gradients:
            inner += _gradient_defs(mod.HUE, hues)
        if include_markers:
            inner += _marker_defs(mod.HUE, hues, mod.PALETTE.gray)
        return f"<defs>{inner}</defs>"

    def hero_chrome(
        *,
        kicker: str = "",
        title: str = "",
        subtitle: str = "",
        column_headers: Optional[Sequence[Tuple[str, float]]] = None,
        encoding_note_right: str = "",
        palette: Optional[Palette] = None,
        canvas: Optional[CanvasProfile] = None,
        include_bg: bool = True,
    ) -> str:
        pal = palette or mod.PALETTE
        canvas = canvas or mod.HERO_CANVAS
        is_embed = canvas.w == 900 and canvas.h == 336
        title_sz = 17 if is_embed else 26
        subtitle_sz = 10 if is_embed else 13
        section_sz = 8 if is_embed else 10
        kicker_sz = 8 if is_embed else 10
        parts = []
        if include_bg:
            parts.append(_rect(0, 0, canvas.w, canvas.h, fill=pal.bg))
        if kicker:
            parts.append(
                _txt(
                    canvas.margin_x,
                    canvas.title_y - 20,
                    kicker,
                    size=kicker_sz,
                    family=mod.FONT_SANS,
                    weight=700,
                    fill=pal.primary,
                    letter_em=0.22,
                )
            )
        if title:
            parts.append(
                _txt(
                    canvas.margin_x,
                    canvas.title_y,
                    title,
                    size=title_sz,
                    family=mod.FONT_SERIF,
                    weight=700,
                    fill=pal.ink,
                    letter_em=0.01,
                )
            )
        if subtitle:
            parts.append(
                _txt(
                    canvas.margin_x,
                    canvas.subtitle_y,
                    subtitle,
                    size=subtitle_sz,
                    family=mod.FONT_SANS,
                    weight=500,
                    fill=pal.gray,
                    letter_em=0.04,
                )
            )
        parts.append(
            _line(
                canvas.margin_x,
                canvas.title_hair_y,
                canvas.w - canvas.margin_x,
                canvas.title_hair_y,
                stroke=pal.primary,
                sw=0.8,
                opacity=0.55,
            )
        )
        if column_headers:
            for lbl, col_x in column_headers:
                parts.append(
                    _txt(
                        col_x,
                        canvas.section_hdr_y,
                        lbl,
                        size=section_sz,
                        family=mod.FONT_SANS,
                        weight=700,
                        fill=pal.primary,
                        anchor="middle",
                        letter_em=0.26,
                    )
                )
        if encoding_note_right:
            parts.append(
                _txt(
                    canvas.w - canvas.margin_x,
                    canvas.subtitle_y,
                    encoding_note_right,
                    size=9 if is_embed else 11,
                    family=mod.FONT_SANS,
                    weight=500,
                    fill=pal.gray,
                    anchor="end",
                    italic=True,
                )
            )
        return "".join(parts)

    def hero_footer(
        *,
        caption: str = "",
        source: str = "",
        read_lines: Optional[Sequence[str]] = None,
        italic_last: bool = False,
        palette: Optional[Palette] = None,
        canvas: Optional[CanvasProfile] = None,
        min_read_chars: int = 40,
    ) -> str:
        _ = (caption, source, read_lines, italic_last, palette, canvas, min_read_chars)
        return ""

    def tspan(word: str, *, color: str = mod.HUE["rust"], weight: int = 700) -> str:
        c = _resolve_hue(mod.HUE, color) if not color.startswith("rgba") else color
        return f'<tspan font-weight="{weight}" fill="{c}">{esc(word)}</tspan>'

    mod.svg_defs = svg_defs
    mod.hero_chrome = hero_chrome
    mod.hero_footer = hero_footer
    mod.tspan = tspan
    mod.SKIN_INSTANCE = GeneratedTokenSkin(mod)
    setattr(mod, spec.class_name, GeneratedTokenSkin)
    mod.__all__ = [
        spec.alias,
        "PALETTE",
        spec.class_name,
        "SKIN_INSTANCE",
        "CanvasProfile",
        "HERO_CANVAS",
        "EMBED_CANVAS",
        "TX_CANVAS",
        "HUE",
        "HUE_ORDER",
        "TYPE_SCALE",
        "FONT_SERIF",
        "FONT_SANS",
        "svg_defs",
        "hero_chrome",
        "hero_footer",
        "tspan",
    ]
    return mod


GENERATED_SKIN_SPECS: Dict[str, GeneratedSkinSpec] = {
    "annual_report_ivory": GeneratedSkinSpec(
        class_name="AnnualReportIvorySkin",
        alias="ANNUAL_REPORT_IVORY",
        decor="chapter number rondel + deep forest.",
        hue={
            "blue": "#2C4370",
            "cinnamon": "#8B6E3C",
            "gold_p": "#C4A96B",
            "green": "#0A3D2E",
            "magenta": "#7A2E3A",
            "olive": "#6E6A4E",
            "orange": "#C4A96B",
            "rust": "#0A3D2E",
        },
        font_serif="Baskerville, EB Garamond, Georgia, serif",
        font_sans="Inter, sans-serif",
        palette={
            "accent": "#C4A96B",
            "accent_dim": "#8B6E3C",
            "bg": "#ECEEE9",
            "bg_alt": "#DFE3DC",
            "bg_dim": "#DFE3DC",
            "body_family": "Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(10,26,15,0.55)",
            "hair": "#0A1A0F",
            "head_family": "Baskerville, EB Garamond, Georgia, serif",
            "ink": "#0A1A0F",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Inter, sans-serif",
            "name": "Annual Report · Cool Ash + Deep Forest",
            "negative": "#7A2E3A",
            "positive": "#0A3D2E",
            "primary": "#0A3D2E",
            "primary_dim": "#C4A96B",
            "section_numbering": "arabic",
            "signature_note": "ANNUAL REPORT IVORY",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "arxiv_clean": GeneratedSkinSpec(
        class_name="ArxivCleanSkin",
        alias="ARXIV_CLEAN",
        decor="thin double ruler + Computer Modern.",
        hue={
            "blue": "#1E3A6E",
            "cinnamon": "#7A5A4A",
            "gold_p": "#8B7A3E",
            "green": "#3E6E4E",
            "magenta": "#B22222",
            "olive": "#5A5A4A",
            "orange": "#5A5A5A",
            "rust": "#0A0A0A",
        },
        font_serif="Latin Modern Roman, CMU Serif, EB Garamond, Georgia, serif",
        font_sans="Latin Modern Sans, Computer Modern, Inter, sans-serif",
        palette={
            "accent": "#8B7A3E",
            "accent_dim": "#7A5A4A",
            "bg": "#FFFFFF",
            "bg_alt": "#F5F5F5",
            "bg_dim": "#F5F5F5",
            "body_family": "Latin Modern Sans, Computer Modern, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(80,80,80,0.7)",
            "hair": "#0A0A0A",
            "head_family": "Latin Modern Roman, CMU Serif, EB Garamond, Georgia, serif",
            "ink": "#0A0A0A",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Latin Modern Sans, Computer Modern, Inter, sans-serif",
            "name": "Arxiv Clean · Latin Modern",
            "negative": "#B22222",
            "positive": "#3E6E4E",
            "primary": "#0A0A0A",
            "primary_dim": "#5A5A5A",
            "section_numbering": "arabic",
            "signature_note": "ARXIV CLEAN",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "arxiv_pastel": GeneratedSkinSpec(
        class_name="ArxivPastelSkin",
        alias="ARXIV_PASTEL",
        decor="arxiv tab-header + underline.",
        hue={
            "blue": "#3A5A7C",
            "cinnamon": "#8B7A5C",
            "gold_p": "#B8896B",
            "green": "#6E8A6E",
            "magenta": "#8B5A6E",
            "olive": "#8A8A6E",
            "orange": "#B8896B",
            "rust": "#5B7CBA",
        },
        font_serif="Charter, IBM Plex Serif, Georgia, serif",
        font_sans="IBM Plex Sans, Inter, sans-serif",
        palette={
            "accent": "#B8896B",
            "accent_dim": "#8B7A5C",
            "bg": "#FAFAFA",
            "bg_alt": "#EEF0F3",
            "bg_dim": "#EEF0F3",
            "body_family": "IBM Plex Sans, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(70,80,100,0.6)",
            "hair": "#1A2438",
            "head_family": "Charter, IBM Plex Serif, Georgia, serif",
            "ink": "#1A2438",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "IBM Plex Sans, Inter, sans-serif",
            "name": "Arxiv Pastel · Academic Cool White",
            "negative": "#8B5A6E",
            "positive": "#6E8A6E",
            "primary": "#5B7CBA",
            "primary_dim": "#B8896B",
            "section_numbering": "arabic",
            "signature_note": "ARXIV PASTEL",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "bain_scarlet": GeneratedSkinSpec(
        class_name="BainScarletSkin",
        alias="BAIN_SCARLET",
        decor="thick top+bottom rule bar hero.",
        hue={
            "blue": "#4A4A5A",
            "cinnamon": "#8B5A3C",
            "gold_p": "#B8783E",
            "green": "#5A6E4E",
            "magenta": "#8B1A1A",
            "olive": "#6E6E5E",
            "orange": "#E86A4F",
            "rust": "#CC0000",
        },
        font_serif="Georgia, serif",
        font_sans="Trade Gothic, Franklin Gothic, Inter, sans-serif",
        palette={
            "accent": "#B8783E",
            "accent_dim": "#8B5A3C",
            "bg": "#FFFFFF",
            "bg_alt": "#F8F5F5",
            "bg_dim": "#F8F5F5",
            "body_family": "Trade Gothic, Franklin Gothic, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(26,26,26,0.55)",
            "hair": "#1A1A1A",
            "head_family": "Georgia, serif",
            "ink": "#1A1A1A",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Trade Gothic, Franklin Gothic, Inter, sans-serif",
            "name": "Bain Scarlet · Trade Gothic",
            "negative": "#8B1A1A",
            "positive": "#5A6E4E",
            "primary": "#CC0000",
            "primary_dim": "#E86A4F",
            "section_numbering": "arabic",
            "signature_note": "BAIN SCARLET",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "bauhaus_primary": GeneratedSkinSpec(
        class_name="BauhausPrimarySkin",
        alias="BAUHAUS_PRIMARY",
        decor="red circle + blue square + yellow triangle triad.",
        hue={
            "blue": "#1B4EA8",
            "cinnamon": "#8B5A3C",
            "gold_p": "#F0C808",
            "green": "#3E7A4E",
            "magenta": "#8B1A1A",
            "olive": "#7A7A3E",
            "orange": "#F0C808",
            "rust": "#D8291C",
        },
        font_serif="Futura, Century Gothic, Georgia, serif",
        font_sans="Futura Bold, Futura, Century Gothic, Inter, sans-serif",
        palette={
            "accent": "#F0C808",
            "accent_dim": "#8B5A3C",
            "bg": "#FDE454",
            "bg_alt": "#F5D33A",
            "bg_dim": "#F5D33A",
            "body_family": "Futura Bold, Futura, Century Gothic, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(26,26,26,0.55)",
            "hair": "#1A1A1A",
            "head_family": "Futura, Century Gothic, Georgia, serif",
            "ink": "#1A1A1A",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Futura Bold, Futura, Century Gothic, Inter, sans-serif",
            "name": "Bauhaus Primary · Yellow",
            "negative": "#8B1A1A",
            "positive": "#3E7A4E",
            "primary": "#D8291C",
            "primary_dim": "#F0C808",
            "section_numbering": "arabic",
            "signature_note": "BAUHAUS PRIMARY",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "bcg_forest": GeneratedSkinSpec(
        class_name="BCGForestSkin",
        alias="BCG_FOREST",
        decor="MBB-style thin ring, forest green.",
        hue={
            "blue": "#3E5F7C",
            "cinnamon": "#8B6E4C",
            "gold_p": "#C4A96B",
            "green": "#0D5A2E",
            "magenta": "#7A3A3A",
            "olive": "#7A7A5C",
            "orange": "#C4A96B",
            "rust": "#106A38",
        },
        font_serif="Georgia, GT Sectra, serif",
        font_sans="Neue Haas Grotesk, Helvetica Neue, Inter, sans-serif",
        palette={
            "accent": "#C4A96B",
            "accent_dim": "#8B6E4C",
            "bg": "#F4F7F1",
            "bg_alt": "#E9EEE4",
            "bg_dim": "#E9EEE4",
            "body_family": "Neue Haas Grotesk, Helvetica Neue, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(13,51,32,0.55)",
            "hair": "#0D3320",
            "head_family": "Georgia, GT Sectra, serif",
            "ink": "#0D3320",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Neue Haas Grotesk, Helvetica Neue, Inter, sans-serif",
            "name": "BCG Forest · Sage White",
            "negative": "#7A3A3A",
            "positive": "#0D5A2E",
            "primary": "#106A38",
            "primary_dim": "#C4A96B",
            "section_numbering": "arabic",
            "signature_note": "BCG FOREST",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "bloomberg_amber": GeneratedSkinSpec(
        class_name="BloombergAmberSkin",
        alias="BLOOMBERG_AMBER",
        decor="terminal panel + tabular-num orange.",
        hue={
            "blue": "#00B4E4",
            "cinnamon": "#B87A4A",
            "gold_p": "#FFC800",
            "green": "#3ECE7B",
            "magenta": "#E85D5D",
            "olive": "#8A8478",
            "orange": "#FFA500",
            "rust": "#FF6B00",
        },
        font_serif="Georgia, serif",
        font_sans="IBM Plex Mono, JetBrains Mono, Menlo, monospace",
        palette={
            "accent": "#FFC800",
            "accent_dim": "#B87A4A",
            "bg": "#0B0F1A",
            "bg_alt": "#161C2E",
            "bg_dim": "#161C2E",
            "body_family": "IBM Plex Mono, JetBrains Mono, Menlo, monospace",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(180,180,180,0.6)",
            "hair": "#E8E8E8",
            "head_family": "Georgia, serif",
            "ink": "#E8E8E8",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "IBM Plex Mono, JetBrains Mono, Menlo, monospace",
            "name": "Bloomberg Amber · Terminal",
            "negative": "#E85D5D",
            "positive": "#3ECE7B",
            "primary": "#FF6B00",
            "primary_dim": "#FFA500",
            "section_numbering": "arabic",
            "signature_note": "BLOOMBERG AMBER",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "blueprint_grid": GeneratedSkinSpec(
        class_name="BlueprintGridSkin",
        alias="BLUEPRINT_GRID",
        decor="dimension arrows + measurement text.",
        hue={
            "blue": "#7CC4FA",
            "cinnamon": "#D4C8A8",
            "gold_p": "#F0D875",
            "green": "#8AF0B8",
            "magenta": "#E85D75",
            "olive": "#B0C4D8",
            "orange": "#7CC4FA",
            "rust": "#FFFFFF",
        },
        font_serif="Courier New, JetBrains Mono, monospace",
        font_sans="JetBrains Mono, Menlo, monospace",
        palette={
            "accent": "#F0D875",
            "accent_dim": "#D4C8A8",
            "bg": "#1E3A5F",
            "bg_alt": "#254670",
            "bg_dim": "#254670",
            "body_family": "JetBrains Mono, Menlo, monospace",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(245,249,255,0.55)",
            "hair": "#F5F9FF",
            "head_family": "Courier New, JetBrains Mono, monospace",
            "ink": "#F5F9FF",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "JetBrains Mono, Menlo, monospace",
            "name": "Blueprint Grid · CAD Cyan",
            "negative": "#E85D75",
            "positive": "#8AF0B8",
            "primary": "#FFFFFF",
            "primary_dim": "#7CC4FA",
            "section_numbering": "arabic",
            "signature_note": "BLUEPRINT GRID",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "chalkboard_slate": GeneratedSkinSpec(
        class_name="ChalkboardSlateSkin",
        alias="CHALKBOARD_SLATE",
        decor="chalk scribble double-circle + dashed.",
        hue={
            "blue": "#A5CEE8",
            "cinnamon": "#E8B08E",
            "gold_p": "#F0C060",
            "green": "#B8E88E",
            "magenta": "#F5A9A9",
            "olive": "#D4C89E",
            "orange": "#F0C060",
            "rust": "#FEFEF0",
        },
        font_serif="Chalkduster, Comic Sans MS, Kalam, cursive",
        font_sans="Chalkduster, Kalam, Comic Sans MS, cursive",
        palette={
            "accent": "#F0C060",
            "accent_dim": "#E8B08E",
            "bg": "#2B4A3A",
            "bg_alt": "#3A5A48",
            "bg_dim": "#3A5A48",
            "body_family": "Chalkduster, Kalam, Comic Sans MS, cursive",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(254,254,240,0.5)",
            "hair": "#FEFEF0",
            "head_family": "Chalkduster, Comic Sans MS, Kalam, cursive",
            "ink": "#FEFEF0",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Chalkduster, Kalam, Comic Sans MS, cursive",
            "name": "Chalkboard Slate · Classroom",
            "negative": "#F5A9A9",
            "positive": "#B8E88E",
            "primary": "#FEFEF0",
            "primary_dim": "#F0C060",
            "section_numbering": "arabic",
            "signature_note": "CHALKBOARD SLATE",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "coursera_indigo": GeneratedSkinSpec(
        class_name="CourseraIndigoSkin",
        alias="COURSERA_INDIGO",
        decor="rounded academic card + progress ring.",
        hue={
            "blue": "#0056D2",
            "cinnamon": "#8B6E4C",
            "gold_p": "#FFC33C",
            "green": "#4EA458",
            "magenta": "#DA5E5E",
            "olive": "#7A8A5E",
            "orange": "#FFC33C",
            "rust": "#0056D2",
        },
        font_serif="Georgia, serif",
        font_sans="Open Sans, Inter, sans-serif",
        palette={
            "accent": "#FFC33C",
            "accent_dim": "#8B6E4C",
            "bg": "#FFFFFF",
            "bg_alt": "#F4F6FB",
            "bg_dim": "#F4F6FB",
            "body_family": "Open Sans, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(15,27,71,0.55)",
            "hair": "#0F1B47",
            "head_family": "Georgia, serif",
            "ink": "#0F1B47",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Open Sans, Inter, sans-serif",
            "name": "Coursera Indigo · Academic Cards",
            "negative": "#DA5E5E",
            "positive": "#4EA458",
            "primary": "#0056D2",
            "primary_dim": "#FFC33C",
            "section_numbering": "arabic",
            "signature_note": "COURSERA INDIGO",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "deloitte_lime": GeneratedSkinSpec(
        class_name="DeloitteLimeSkin",
        alias="DELOITTE_LIME",
        decor="left vertical rule + minimalist.",
        hue={
            "blue": "#0076A8",
            "cinnamon": "#7A6E3C",
            "gold_p": "#EFA831",
            "green": "#009A44",
            "magenta": "#DA291C",
            "olive": "#7A8A3E",
            "orange": "#00B274",
            "rust": "#86BC25",
        },
        font_serif="Georgia, serif",
        font_sans="Open Sans, Inter, sans-serif",
        palette={
            "accent": "#EFA831",
            "accent_dim": "#7A6E3C",
            "bg": "#EEEFEA",
            "bg_alt": "#E2E4DD",
            "bg_dim": "#E2E4DD",
            "body_family": "Open Sans, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(30,30,30,0.55)",
            "hair": "#000000",
            "head_family": "Georgia, serif",
            "ink": "#000000",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Open Sans, Inter, sans-serif",
            "name": "Deloitte Lime · Slate",
            "negative": "#DA291C",
            "positive": "#009A44",
            "primary": "#86BC25",
            "primary_dim": "#00B274",
            "section_numbering": "arabic",
            "signature_note": "DELOITTE LIME",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "engineering_kraft": GeneratedSkinSpec(
        class_name="EngineeringKraftSkin",
        alias="ENGINEERING_KRAFT",
        decor="hand-drawn double stroke + blueprint dashes.",
        hue={
            "blue": "#1A3C6C",
            "cinnamon": "#8B5A3C",
            "gold_p": "#B87A4A",
            "green": "#3E6E5A",
            "magenta": "#7A2E3A",
            "olive": "#7A6E3E",
            "orange": "#8B3A1E",
            "rust": "#1A3C6C",
        },
        font_serif="Baskerville, Georgia, serif",
        font_sans="Architects Daughter, Kalam, Inter, sans-serif",
        palette={
            "accent": "#B87A4A",
            "accent_dim": "#8B5A3C",
            "bg": "#D6C7A8",
            "bg_alt": "#CCBE9F",
            "bg_dim": "#CCBE9F",
            "body_family": "Architects Daughter, Kalam, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(26,60,108,0.55)",
            "hair": "#1A3C6C",
            "head_family": "Baskerville, Georgia, serif",
            "ink": "#1A3C6C",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Architects Daughter, Kalam, Inter, sans-serif",
            "name": "Engineering Kraft · Sketch",
            "negative": "#7A2E3A",
            "positive": "#3E6E5A",
            "primary": "#1A3C6C",
            "primary_dim": "#8B3A1E",
            "section_numbering": "arabic",
            "signature_note": "ENGINEERING KRAFT",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "goldman_slate": GeneratedSkinSpec(
        class_name="GoldmanSlateSkin",
        alias="GOLDMAN_SLATE",
        decor="halo ring with GS deep blue + gold fig#.",
        hue={
            "blue": "#0F5EA5",
            "cinnamon": "#8B6E5C",
            "gold_p": "#C8AA6E",
            "green": "#3C6E50",
            "magenta": "#96322D",
            "olive": "#787882",
            "orange": "#2D5FA5",
            "rust": "#003A84",
        },
        font_serif="Chronicle Display, Söhne, Georgia, serif",
        font_sans="Söhne, Helvetica Neue, Inter, sans-serif",
        palette={
            "accent": "#C8AA6E",
            "accent_dim": "#8B6E5C",
            "bg": "#FAFAFB",
            "bg_alt": "#F0F0F5",
            "bg_dim": "#F0F0F5",
            "body_family": "Söhne, Helvetica Neue, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(120,120,130,1)",
            "hair": "#232328",
            "head_family": "Chronicle Display, Söhne, Georgia, serif",
            "ink": "#232328",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Söhne, Helvetica Neue, Inter, sans-serif",
            "name": "Goldman Slate · IB Analyst Note",
            "negative": "#96322D",
            "positive": "#3C6E50",
            "primary": "#003A84",
            "primary_dim": "#2D5FA5",
            "section_numbering": "arabic",
            "signature_note": "GOLDMAN SLATE",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "hermes_orange": GeneratedSkinSpec(
        class_name="HermesOrangeSkin",
        alias="HERMES_ORANGE",
        decor="saddle stitch double-line + Hermès orange.",
        hue={
            "blue": "#5A5A4E",
            "cinnamon": "#B8783E",
            "gold_p": "#D4A048",
            "green": "#5A6E4A",
            "magenta": "#8B3A2E",
            "olive": "#8B6E4A",
            "orange": "#F5943E",
            "rust": "#F37021",
        },
        font_serif="Serifa, Rockwell, Georgia, serif",
        font_sans="Univers, Helvetica Neue, Inter, sans-serif",
        palette={
            "accent": "#D4A048",
            "accent_dim": "#B8783E",
            "bg": "#F8DEB2",
            "bg_alt": "#EEC98A",
            "bg_dim": "#EEC98A",
            "body_family": "Univers, Helvetica Neue, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(61,31,15,0.55)",
            "hair": "#3D1F0F",
            "head_family": "Serifa, Rockwell, Georgia, serif",
            "ink": "#3D1F0F",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Univers, Helvetica Neue, Inter, sans-serif",
            "name": "Hermès Orange · Saddle Peach",
            "negative": "#8B3A2E",
            "positive": "#5A6E4A",
            "primary": "#F37021",
            "primary_dim": "#F5943E",
            "section_numbering": "arabic",
            "signature_note": "HERMES ORANGE",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "khan_teal": GeneratedSkinSpec(
        class_name="KhanTealSkin",
        alias="KHAN_TEAL",
        decor="rounded corners + progress dot + Lato.",
        hue={
            "blue": "#5AB8E8",
            "cinnamon": "#8B6E4C",
            "gold_p": "#F5A623",
            "green": "#14BF96",
            "magenta": "#DA5E5E",
            "olive": "#7A8A5E",
            "orange": "#F5A623",
            "rust": "#14BF96",
        },
        font_serif="Georgia, serif",
        font_sans="Lato, Open Sans, Inter, sans-serif",
        palette={
            "accent": "#F5A623",
            "accent_dim": "#8B6E4C",
            "bg": "#FFFFFF",
            "bg_alt": "#F0F9F8",
            "bg_dim": "#F0F9F8",
            "body_family": "Lato, Open Sans, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(31,46,58,0.55)",
            "hair": "#1F2E3A",
            "head_family": "Georgia, serif",
            "ink": "#1F2E3A",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Lato, Open Sans, Inter, sans-serif",
            "name": "Khan Teal · Rounded",
            "negative": "#DA5E5E",
            "positive": "#14BF96",
            "primary": "#14BF96",
            "primary_dim": "#F5A623",
            "section_numbering": "arabic",
            "signature_note": "KHAN TEAL",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "manuscript_sepia": GeneratedSkinSpec(
        class_name="ManuscriptSepiaSkin",
        alias="MANUSCRIPT_SEPIA",
        decor="illuminated capital + border flourish.",
        hue={
            "blue": "#4A5A7C",
            "cinnamon": "#8B5A3C",
            "gold_p": "#7A5E2E",
            "green": "#4E6E4E",
            "magenta": "#6E2A2E",
            "olive": "#7A6E3E",
            "orange": "#B87848",
            "rust": "#8B3A1E",
        },
        font_serif="IM Fell English, EB Garamond, Georgia, serif",
        font_sans="EB Garamond, Georgia, serif",
        palette={
            "accent": "#7A5E2E",
            "accent_dim": "#8B5A3C",
            "bg": "#F0E4C8",
            "bg_alt": "#E8DBB8",
            "bg_dim": "#E8DBB8",
            "body_family": "EB Garamond, Georgia, serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(61,40,23,0.5)",
            "hair": "#3D2817",
            "head_family": "IM Fell English, EB Garamond, Georgia, serif",
            "ink": "#3D2817",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "EB Garamond, Georgia, serif",
            "name": "Manuscript Sepia · Vellum + Ink",
            "negative": "#6E2A2E",
            "positive": "#4E6E4E",
            "primary": "#8B3A1E",
            "primary_dim": "#B87848",
            "section_numbering": "arabic",
            "signature_note": "MANUSCRIPT SEPIA",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "monocle_ecru": GeneratedSkinSpec(
        class_name="MonocleEcruSkin",
        alias="MONOCLE_ECRU",
        decor="editorial medallion + olive+tangerine.",
        hue={
            "blue": "#3E5A7C",
            "cinnamon": "#B8783E",
            "gold_p": "#C48E3C",
            "green": "#4E5E3A",
            "magenta": "#8B3A2E",
            "olive": "#7A8A5C",
            "orange": "#E88C50",
            "rust": "#4E5E3A",
        },
        font_serif="Plantin, Georgia, GT Sectra, serif",
        font_sans="Söhne, Inter, sans-serif",
        palette={
            "accent": "#C48E3C",
            "accent_dim": "#B8783E",
            "bg": "#EBDBAF",
            "bg_alt": "#DDCB94",
            "bg_dim": "#DDCB94",
            "body_family": "Söhne, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(30,46,26,0.55)",
            "hair": "#1E2E1A",
            "head_family": "Plantin, Georgia, GT Sectra, serif",
            "ink": "#1E2E1A",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Söhne, Inter, sans-serif",
            "name": "Monocle Ecru · Mustard",
            "negative": "#8B3A2E",
            "positive": "#4E5E3A",
            "primary": "#4E5E3A",
            "primary_dim": "#E88C50",
            "section_numbering": "arabic",
            "signature_note": "MONOCLE ECRU",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "notebook_grid": GeneratedSkinSpec(
        class_name="NotebookGridSkin",
        alias="NOTEBOOK_GRID",
        decor="hand-drawn circle + grid + notebook feel.",
        hue={
            "blue": "#3E5AA8",
            "cinnamon": "#8B6E4C",
            "gold_p": "#D4A017",
            "green": "#5A8A4A",
            "magenta": "#B84A5E",
            "olive": "#7A8A5E",
            "orange": "#D4A017",
            "rust": "#3E5AA8",
        },
        font_serif="Kalam, Architects Daughter, Comic Sans MS, cursive",
        font_sans="Kalam, Architects Daughter, Comic Sans MS, cursive",
        palette={
            "accent": "#D4A017",
            "accent_dim": "#8B6E4C",
            "bg": "#DBEAF6",
            "bg_alt": "#C5DBEC",
            "bg_dim": "#C5DBEC",
            "body_family": "Kalam, Architects Daughter, Comic Sans MS, cursive",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(42,58,63,0.55)",
            "hair": "#2A3A3F",
            "head_family": "Kalam, Architects Daughter, Comic Sans MS, cursive",
            "ink": "#2A3A3F",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Kalam, Architects Daughter, Comic Sans MS, cursive",
            "name": "Notebook Grid · Cyan Graph Paper",
            "negative": "#B84A5E",
            "positive": "#5A8A4A",
            "primary": "#3E5AA8",
            "primary_dim": "#D4A017",
            "section_numbering": "arabic",
            "signature_note": "NOTEBOOK GRID",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "oxford_indigo": GeneratedSkinSpec(
        class_name="OxfordIndigoSkin",
        alias="OXFORD_INDIGO",
        decor="crest badge + gothic frame.",
        hue={
            "blue": "#2C4370",
            "cinnamon": "#8B6E3C",
            "gold_p": "#B58A3E",
            "green": "#3D5A4E",
            "magenta": "#7A2E3E",
            "olive": "#7A6A3E",
            "orange": "#B58A3E",
            "rust": "#002147",
        },
        font_serif="Bodoni MT, Bodoni 72, Playfair Display, Georgia, serif",
        font_sans="Inter, Optima, sans-serif",
        palette={
            "accent": "#B58A3E",
            "accent_dim": "#8B6E3C",
            "bg": "#0F1B3D",
            "bg_alt": "#182548",
            "bg_dim": "#0A1330",
            "body_family": "Inter, Optima, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(245,240,220,0.55)",
            "hair": "#F5F0DC",
            "head_family": "Bodoni MT, Bodoni 72, Playfair Display, Georgia, serif",
            "ink": "#F5F0DC",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Inter, Optima, sans-serif",
            "name": "Oxford Indigo · Deep Crest",
            "negative": "#7A2E3E",
            "positive": "#3D5A4E",
            "primary": "#002147",
            "primary_dim": "#B58A3E",
            "section_numbering": "arabic",
            "signature_note": "OXFORD INDIGO",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "pitch_bauhaus": GeneratedSkinSpec(
        class_name="PitchBauhausSkin",
        alias="PITCH_BAUHAUS",
        decor="primary triangle+square+circle composition.",
        hue={
            "blue": "#1B4EA8",
            "cinnamon": "#8B5A3C",
            "gold_p": "#F0C808",
            "green": "#3E7A4E",
            "magenta": "#D8291C",
            "olive": "#6E7A3E",
            "orange": "#F0C808",
            "rust": "#D8291C",
        },
        font_serif="Futura, Century Gothic, Georgia, serif",
        font_sans="Futura Bold, Futura, Century Gothic, sans-serif",
        palette={
            "accent": "#F0C808",
            "accent_dim": "#8B5A3C",
            "bg": "#D62828",
            "bg_alt": "#B81E1E",
            "bg_dim": "#B81E1E",
            "body_family": "Futura Bold, Futura, Century Gothic, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(251,247,238,0.65)",
            "hair": "#FBF7EE",
            "head_family": "Futura, Century Gothic, Georgia, serif",
            "ink": "#FBF7EE",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Futura Bold, Futura, Century Gothic, sans-serif",
            "name": "Pitch Bauhaus · Primary Red",
            "negative": "#D8291C",
            "positive": "#3E7A4E",
            "primary": "#D8291C",
            "primary_dim": "#F0C808",
            "section_numbering": "arabic",
            "signature_note": "PITCH BAUHAUS",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "pitch_midnight": GeneratedSkinSpec(
        class_name="PitchMidnightSkin",
        alias="PITCH_MIDNIGHT",
        decor="dark midnight spotlight + champagne gold.",
        hue={
            "blue": "#5AB8E8",
            "cinnamon": "#D4A47C",
            "gold_p": "#F0D875",
            "green": "#7ADD9E",
            "magenta": "#D45D8A",
            "olive": "#C4B08E",
            "orange": "#FF6E50",
            "rust": "#E8C87A",
        },
        font_serif="Playfair Display, GT Sectra, Georgia, serif",
        font_sans="Inter Display, Inter, sans-serif",
        palette={
            "accent": "#F0D875",
            "accent_dim": "#D4A47C",
            "bg": "#0C1729",
            "bg_alt": "#1A2438",
            "bg_dim": "#1A2438",
            "body_family": "Inter Display, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(245,240,220,0.55)",
            "hair": "#F5F0DC",
            "head_family": "Playfair Display, GT Sectra, Georgia, serif",
            "ink": "#F5F0DC",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Inter Display, Inter, sans-serif",
            "name": "Pitch Midnight · TED Talk",
            "negative": "#D45D8A",
            "positive": "#7ADD9E",
            "primary": "#E8C87A",
            "primary_dim": "#FF6E50",
            "section_numbering": "arabic",
            "signature_note": "PITCH MIDNIGHT",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "pitch_sunset": GeneratedSkinSpec(
        class_name="PitchSunsetSkin",
        alias="PITCH_SUNSET",
        decor="warm gradient disc + fraunces round.",
        hue={
            "blue": "#5A6EA5",
            "cinnamon": "#D4906E",
            "gold_p": "#F0B85E",
            "green": "#7A9E6E",
            "magenta": "#B84A5E",
            "olive": "#B08E6E",
            "orange": "#F0906E",
            "rust": "#E85D8A",
        },
        font_serif="Fraunces, Playfair Display, Georgia, serif",
        font_sans="Fraunces, Inter, sans-serif",
        palette={
            "accent": "#F0B85E",
            "accent_dim": "#D4906E",
            "bg": "#FBC29B",
            "bg_alt": "#F5A97D",
            "bg_dim": "#F5A97D",
            "body_family": "Fraunces, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(58,31,44,0.55)",
            "hair": "#3A1F2C",
            "head_family": "Fraunces, Playfair Display, Georgia, serif",
            "ink": "#3A1F2C",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Fraunces, Inter, sans-serif",
            "name": "Pitch Sunset · Peach Coral",
            "negative": "#B84A5E",
            "positive": "#7A9E6E",
            "primary": "#E85D8A",
            "primary_dim": "#F0906E",
            "section_numbering": "arabic",
            "signature_note": "PITCH SUNSET",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "riso_duotone": GeneratedSkinSpec(
        class_name="RisoDuotoneSkin",
        alias="RISO_DUOTONE",
        decor="two overprinted circles + riso pink+cyan.",
        hue={
            "blue": "#3ECEDA",
            "cinnamon": "#D4906E",
            "gold_p": "#F0B85E",
            "green": "#7ADD9E",
            "magenta": "#B84A5E",
            "olive": "#B0A578",
            "orange": "#F0906E",
            "rust": "#E8628C",
        },
        font_serif="GT Alpina, Fraunces, Georgia, serif",
        font_sans="GT Alpina, Inter, sans-serif",
        palette={
            "accent": "#F0B85E",
            "accent_dim": "#D4906E",
            "bg": "#F4CFD1",
            "bg_alt": "#EBBABE",
            "bg_dim": "#EBBABE",
            "body_family": "GT Alpina, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(46,31,46,0.55)",
            "hair": "#2E1F2E",
            "head_family": "GT Alpina, Fraunces, Georgia, serif",
            "ink": "#2E1F2E",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "GT Alpina, Inter, sans-serif",
            "name": "Riso Duotone · Pink Overprint",
            "negative": "#B84A5E",
            "positive": "#7ADD9E",
            "primary": "#E8628C",
            "primary_dim": "#F0906E",
            "section_numbering": "arabic",
            "signature_note": "RISO DUOTONE",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "roland_terracotta": GeneratedSkinSpec(
        class_name="RolandTerracottaSkin",
        alias="ROLAND_TERRACOTTA",
        decor="hand-crafted thick frame + serif italic.",
        hue={
            "blue": "#5A5A4E",
            "cinnamon": "#8B5A3C",
            "gold_p": "#B8862F",
            "green": "#5A6E5A",
            "magenta": "#8B3A2E",
            "olive": "#8B6E4C",
            "orange": "#D48C6E",
            "rust": "#B2593D",
        },
        font_serif="Times New Roman, GT Sectra, Georgia, serif",
        font_sans="Inter, sans-serif",
        palette={
            "accent": "#B8862F",
            "accent_dim": "#8B5A3C",
            "bg": "#F5EFE6",
            "bg_alt": "#EDE5D6",
            "bg_dim": "#EDE5D6",
            "body_family": "Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(46,31,23,0.55)",
            "hair": "#2E1F17",
            "head_family": "Times New Roman, GT Sectra, Georgia, serif",
            "ink": "#2E1F17",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Inter, sans-serif",
            "name": "Roland Berger Terracotta · Craft",
            "negative": "#8B3A2E",
            "positive": "#5A6E5A",
            "primary": "#B2593D",
            "primary_dim": "#D48C6E",
            "section_numbering": "arabic",
            "signature_note": "ROLAND TERRACOTTA",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "swiss_grid": GeneratedSkinSpec(
        class_name="SwissGridSkin",
        alias="SWISS_GRID",
        decor="pure black type set on grid + accent stripe.",
        hue={
            "blue": "#3A3A3A",
            "cinnamon": "#7A7A7A",
            "gold_p": "#8A8A8A",
            "green": "#4A4A4A",
            "magenta": "#8B1A1A",
            "olive": "#6A6A6A",
            "orange": "#E30613",
            "rust": "#000000",
        },
        font_serif="Helvetica Neue, Helvetica, Arial, sans-serif",
        font_sans="Helvetica Neue, Helvetica, Arial, sans-serif",
        palette={
            "accent": "#8A8A8A",
            "accent_dim": "#7A7A7A",
            "bg": "#FFFFFF",
            "bg_alt": "#F5F5F5",
            "bg_dim": "#F5F5F5",
            "body_family": "Helvetica Neue, Helvetica, Arial, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(0,0,0,0.55)",
            "hair": "#000000",
            "head_family": "Helvetica Neue, Helvetica, Arial, sans-serif",
            "ink": "#000000",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Helvetica Neue, Helvetica, Arial, sans-serif",
            "name": "Swiss Grid · International Style",
            "negative": "#8B1A1A",
            "positive": "#4A4A4A",
            "primary": "#000000",
            "primary_dim": "#E30613",
            "section_numbering": "arabic",
            "signature_note": "SWISS GRID",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "symposium_ash": GeneratedSkinSpec(
        class_name="SymposiumAshSkin",
        alias="SYMPOSIUM_ASH",
        decor="square stamp seal + minimalist type.",
        hue={
            "blue": "#3E4A5A",
            "cinnamon": "#8B6E5C",
            "gold_p": "#8C6E3E",
            "green": "#4A5E4A",
            "magenta": "#6E2E3A",
            "olive": "#6A6A5A",
            "orange": "#8C6E3E",
            "rust": "#8C3A2E",
        },
        font_serif="Source Han Serif, Noto Serif CJK SC, EB Garamond, serif",
        font_sans="Source Han Sans, Inter, sans-serif",
        palette={
            "accent": "#8C6E3E",
            "accent_dim": "#8B6E5C",
            "bg": "#E7E8E5",
            "bg_alt": "#DDDEDA",
            "bg_dim": "#DDDEDA",
            "body_family": "Source Han Sans, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(31,31,31,0.55)",
            "hair": "#1F1F1F",
            "head_family": "Source Han Serif, Noto Serif CJK SC, EB Garamond, serif",
            "ink": "#1F1F1F",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Source Han Sans, Inter, sans-serif",
            "name": "Symposium Ash · Titanium + 朱印",
            "negative": "#6E2E3A",
            "positive": "#4A5E4A",
            "primary": "#8C3A2E",
            "primary_dim": "#8C6E3E",
            "section_numbering": "arabic",
            "signature_note": "SYMPOSIUM ASH",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "terminal_matrix": GeneratedSkinSpec(
        class_name="TerminalMatrixSkin",
        alias="TERMINAL_MATRIX",
        decor="[bracket] terminal frame + phosphor green.",
        hue={
            "blue": "#00E5FF",
            "cinnamon": "#B87A4A",
            "gold_p": "#FFC800",
            "green": "#39FF14",
            "magenta": "#FF3355",
            "olive": "#8AC748",
            "orange": "#FFC800",
            "rust": "#39FF14",
        },
        font_serif="JetBrains Mono, Menlo, monospace",
        font_sans="JetBrains Mono, IBM Plex Mono, monospace",
        palette={
            "accent": "#FFC800",
            "accent_dim": "#B87A4A",
            "bg": "#0A0F0A",
            "bg_alt": "#141A14",
            "bg_dim": "#141A14",
            "body_family": "JetBrains Mono, IBM Plex Mono, monospace",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(57,255,20,0.5)",
            "hair": "#39FF14",
            "head_family": "JetBrains Mono, Menlo, monospace",
            "ink": "#39FF14",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "JetBrains Mono, IBM Plex Mono, monospace",
            "name": "Terminal Matrix · Green Phosphor",
            "negative": "#FF3355",
            "positive": "#39FF14",
            "primary": "#39FF14",
            "primary_dim": "#FFC800",
            "section_numbering": "arabic",
            "signature_note": "TERMINAL MATRIX",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "wabi_sabi": GeneratedSkinSpec(
        class_name="WabiSabiSkin",
        alias="WABI_SABI",
        decor="ink brush circle + red hanko square seal.",
        hue={
            "blue": "#3A4A4E",
            "cinnamon": "#8B5A3C",
            "gold_p": "#B8862F",
            "green": "#4E5E3A",
            "magenta": "#8B1A1A",
            "olive": "#7A7052",
            "orange": "#B23A2E",
            "rust": "#1A1611",
        },
        font_serif="Noto Serif JP, Source Han Serif, EB Garamond, serif",
        font_sans="Noto Sans JP, Inter, sans-serif",
        palette={
            "accent": "#B8862F",
            "accent_dim": "#8B5A3C",
            "bg": "#F0E8D4",
            "bg_alt": "#E5DBC0",
            "bg_dim": "#E5DBC0",
            "body_family": "Noto Sans JP, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(26,22,17,0.55)",
            "hair": "#1A1611",
            "head_family": "Noto Serif JP, Source Han Serif, EB Garamond, serif",
            "ink": "#1A1611",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Noto Sans JP, Inter, sans-serif",
            "name": "Wabi Sabi · Kyoto Ink",
            "negative": "#8B1A1A",
            "positive": "#4E5E3A",
            "primary": "#1A1611",
            "primary_dim": "#B23A2E",
            "section_numbering": "arabic",
            "signature_note": "WABI SABI",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
    "wsj_broadsheet": GeneratedSkinSpec(
        class_name="WSJBroadsheetSkin",
        alias="WSJ_BROADSHEET",
        decor="broadsheet headline serif + kicker rule.",
        hue={
            "blue": "#3E5A7C",
            "cinnamon": "#8B5A3C",
            "gold_p": "#B8862F",
            "green": "#3B6B47",
            "magenta": "#7A2E3A",
            "olive": "#7A756A",
            "orange": "#B8465A",
            "rust": "#8B1728",
        },
        font_serif="GT Sectra, Playfair Display, Georgia, serif",
        font_sans="Söhne, Inter, sans-serif",
        palette={
            "accent": "#B8862F",
            "accent_dim": "#8B5A3C",
            "bg": "#F1EBD8",
            "bg_alt": "#E8E1CB",
            "bg_dim": "#E8E1CB",
            "body_family": "Söhne, Inter, sans-serif",
            "figure_caption_prefix": "Fig.",
            "folio_style": "hairline",
            "gray": "rgba(122,117,106,1)",
            "hair": "#141410",
            "head_family": "GT Sectra, Playfair Display, Georgia, serif",
            "ink": "#141410",
            "kicker_case": "upper",
            "kicker_letter_spacing": 2.5,
            "mono_family": "Söhne, Inter, sans-serif",
            "name": "WSJ Broadsheet · Newspaper Cream",
            "negative": "#7A2E3A",
            "positive": "#3B6B47",
            "primary": "#8B1728",
            "primary_dim": "#B8465A",
            "section_numbering": "arabic",
            "signature_note": "WSJ BROADSHEET",
            "subtitle_style": "sans_italic",
            "title_style": "serif_bold",
        },
    ),
}

__all__ = ["GeneratedSkinSpec", "GeneratedTokenSkin", "GENERATED_SKIN_SPECS", "create_generated_skin_module"]
