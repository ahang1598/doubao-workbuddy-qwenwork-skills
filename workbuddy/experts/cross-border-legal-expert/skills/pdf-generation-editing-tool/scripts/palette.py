#!/usr/bin/env python3
"""
palette.py — Infer design tokens from document metadata.

Usage:
    python3 palette.py --title "AI Trends 2025" --type report --out tokens.json
    python3 palette.py --title "John Doe Resume" --type resume --out tokens.json
    python3 palette.py --meta meta.json --out tokens.json

Outputs tokens.json consumed by all downstream scripts.
Cover fonts are loaded via Google Fonts @import in the cover HTML (no local caching).
Body fonts use ReportLab system fonts (Times-Bold / Helvetica) for Latin text,
and STSong-Light CID font for CJK (Chinese/Japanese/Korean) text — auto-detected.
Exit codes: 0 success, 1 bad args, 3 write error
"""

import argparse
import json
import sys

# ── Palette library ────────────────────────────────────────────────────────────
# Each entry: cover colors + cover_pattern + mood
PALETTES = {
    # Each type has a distinctive accent hue from across the colour spectrum,
    # and a cover_bg that creates a unique mood.  No two share the same identity.
    "richee": {
        # ── Richee 品牌色（参考 course-guideline.md）──
        # 浅色底色 + 卡片化结构 + 绿色系强调
        "cover_bg":   "#F6F7F9",
        "accent":     "#029856",       # 深绿——主强调
        "accent_lt":  "#D1FAE5",       # 极浅绿——背景装饰
        "text_light": "#FFFFFF",       # 白字（用于深色色块）
        "page_bg":    "#F6F7F9",       # 页面统一底色
        "card_bg":    "#FFFFFF",       # 卡片背景
        "card_border":"#E5E7EB",       # 卡片边框
        "card_radius": 8,              # 卡片圆角（对应 8px）
        "dark":       "#0A0D12",       # 深色点缀（非纯黑）
        "body_text":  "#0A0D12",       # 主文字
        "muted":      "#9CA3AF",       # 次级文字
        "tertiary":   "#6B7280",       # 三级文字
        "divider":    "#E5E7EB",       # 分割线
        "cover_pattern": "grid",
        "mood": "professional",
        # Richee 排版——字号体系（参考 course-guideline §3）
        "scale": {
            "size_display": 54,
            "size_h1":      26,
            "size_h2":      18,
            "size_h3":      14.5,
            "size_body":    14,
            "size_caption": 11,
            "size_meta":    9,
            "line_gap":     23,        # 1.65 × 14pt ≈ 23pt
            "section_gap":  28,
            "para_gap":     10,
        },
        # Richee 布局——留白规范（参考 course-guideline §4）
        "layout": {
            "margin":       48,        # ≥ 48px
            "card_pad":     28,        # 卡片内边距 24-32px
        },
    },
    "report": {
        # Deep charcoal + warm bronze-gold accent — authoritative with warmth
        "cover_bg":   "#1E232B",
        "accent":     "#C4964A",
        "accent_lt":  "#F5EFE2",
        "text_light": "#EDE9E2",
        "page_bg":    "#FAFAF8",
        "dark":       "#0D1117",       # was #1A1E24 — too close to cover_bg
        "body_text":  "#2C2C30",
        "muted":      "#A0A0AA",       # was #7A7A84 — WCAG AA on #1E232B
        "cover_pattern": "fullbleed",
        "mood": "authoritative",
    },
    "proposal": {
        # Dark charcoal + deep teal accent — confident, fresh
        "cover_bg":   "#1F272C",
        "accent":     "#2D8B7A",
        "accent_lt":  "#E2F0EC",
        "text_light": "#EDE9E2",
        "page_bg":    "#FAFAF7",
        "dark":       "#0D1217",       # was #18191E
        "body_text":  "#28282E",
        "muted":      "#9CA8A4",       # was #7A7870
        "cover_pattern": "split",
        "mood": "confident",
    },
    "resume": {
        # White + classic navy accent — clean, professional
        "cover_bg":   "#FFFFFF",
        "accent":     "#1A2B4C",
        "accent_lt":  "#E8EEF5",
        "text_light": "#FFFFFF",
        "page_bg":    "#FFFFFF",
        "dark":       "#111111",
        "body_text":  "#222222",
        "muted":      "#888888",
        "cover_pattern": "typographic",
        "mood": "clean",
    },
    "portfolio": {
        # Near-black + vibrant plum accent — expressive, creative
        "cover_bg":   "#181820",
        "accent":     "#8B5A9E",
        "accent_lt":  "#F2E8F6",
        "text_light": "#EDE9E4",
        "page_bg":    "#F8F8F8",
        "dark":       "#080810",       # was #101018
        "body_text":  "#28282E",
        "muted":      "#9A9AB0",       # was #8A8A96
        "cover_pattern": "atmospheric",
        "mood": "expressive",
    },
    "academic": {
        # Warm ivory + burgundy accent — scholarly tradition
        "cover_bg":   "#F5F2EB",
        "accent":     "#8B2500",
        "accent_lt":  "#F0E4DE",
        "text_light": "#FFFFFF",
        "page_bg":    "#F5F2EB",
        "dark":       "#1A1A28",
        "body_text":  "#1E1E2A",
        "muted":      "#8A7A6A",       # was #7A7068 — more contrast on ivory
        "cover_pattern": "typographic",
        "mood": "scholarly",
    },
    "general": {
        # Warm charcoal + amber accent — modern neutral with warmth
        "cover_bg":   "#21242B",
        "accent":     "#D4893A",
        "accent_lt":  "#F5ECE0",
        "text_light": "#EEEBE5",
        "page_bg":    "#F8F6F2",
        "dark":       "#0B0E14",       # was #1A1A1A
        "body_text":  "#2C2C2C",
        "muted":      "#AAAAB0",       # was #888888
        "cover_pattern": "fullbleed",
        "mood": "neutral",
    },
    # ── Extended types — each with a distinct accent identity ─────────────────
    "minimal": {
        # Warm off-white + near-black accent — pure restraint
        "cover_bg":   "#F7F6F4",
        "accent":     "#1A1A1A",
        "accent_lt":  "#E8E8E7",
        "text_light": "#F7F6F4",
        "page_bg":    "#F7F6F4",
        "dark":       "#111111",
        "body_text":  "#222222",
        "muted":      "#999999",
        "cover_pattern": "minimal",
        "mood": "restrained",
    },
    "stripe": {
        # Near-black + rust terracotta accent — bold, warm
        "cover_bg":   "#1E222A",
        "accent":     "#D4793A",
        "accent_lt":  "#F2E6DB",
        "text_light": "#FFFFFF",
        "page_bg":    "#F8F8F7",
        "dark":       "#0E1117",
        "body_text":  "#262630",
        "muted":      "#888898",
        "cover_pattern": "stripe",
        "mood": "bold",
    },
    "diagonal": {
        # Deep navy + emerald green accent — dynamic, elegant
        "cover_bg":   "#18282E",
        "accent":     "#2E8B6B",
        "accent_lt":  "#E2F0E9",
        "text_light": "#EEF0F5",
        "page_bg":    "#F8FAFC",
        "dark":       "#0F1A20",
        "body_text":  "#1E2C3A",
        "muted":      "#7A8A96",
        "cover_pattern": "diagonal",
        "mood": "dynamic",
    },
    "frame": {
        # Warm parchment + amber-gold accent — classical, elegant
        "cover_bg":   "#F5F2EC",
        "accent":     "#B8935A",
        "accent_lt":  "#EDE6D8",
        "text_light": "#F5F2EC",
        "page_bg":    "#F5F2EC",
        "dark":       "#2A1E14",
        "body_text":  "#2C2018",
        "muted":      "#9A8A78",
        "cover_pattern": "frame",
        "mood": "classical",
    },
    "editorial": {
        # White + crimson accent — editorial impact
        "cover_bg":   "#FFFFFF",
        "accent":     "#C41E3A",
        "accent_lt":  "#F0DFE2",
        "text_light": "#FFFFFF",
        "page_bg":    "#FFFFFF",
        "dark":       "#0A0A0A",
        "body_text":  "#1A1A1A",
        "muted":      "#777777",
        "cover_pattern": "editorial",
        "mood": "editorial",
    },
    # ── New patterns (v2) — distinct color identities ────────────────────────
    "magazine": {
        # Warm linen + forest pine accent — sophisticated publication
        "cover_bg":   "#F0EEE6",
        "accent":     "#2D4A3E",
        "accent_lt":  "#E2EBE6",
        "text_light": "#FFFFFF",
        "page_bg":    "#F0EEE6",
        "dark":       "#0D1A2B",
        "body_text":  "#2A2A2A",
        "muted":      "#7A8A80",
        "cover_pattern": "magazine",
        "mood": "magazine",
    },
    "darkroom": {
        # Midnight purple + soft violet accent — moody, cinematic
        "cover_bg":   "#16122A",
        "accent":     "#7B6AAF",
        "accent_lt":  "#E8E4F5",
        "text_light": "#EDE9E2",
        "page_bg":    "#F7F7F5",
        "dark":       "#040218",       # was #0A0818
        "body_text":  "#2C2C2C",
        "muted":      "#A8A8D0",       # was #8A8AB0
        "cover_pattern": "darkroom",
        "mood": "darkroom",
    },
    "terminal": {
        # True black + terminal green accent — technical, iconic
        "cover_bg":   "#0D1117",
        "accent":     "#3DAA6B",
        "accent_lt":  "#E2F0E8",
        "text_light": "#C9D1D9",
        "page_bg":    "#F8F8F6",
        "dark":       "#000000",       # was #010409
        "body_text":  "#2C2C2C",
        "muted":      "#8CBB9E",       # was #5A9A7A — too dark on dark bg
        "cover_pattern": "terminal",
        "mood": "terminal",
    },
    "poster": {
        # White + pure black accent — stark, bold
        "cover_bg":   "#FFFFFF",
        "accent":     "#0A0A0A",
        "accent_lt":  "#EBEBEA",
        "text_light": "#FFFFFF",
        "page_bg":    "#FFFFFF",
        "dark":       "#0A0A0A",
        "body_text":  "#1A1A1A",
        "muted":      "#888888",
        "cover_pattern": "poster",
        "mood": "poster",
    },
}

# ── Font pairs — CSS names for cover HTML, ReportLab names for body ─────────────
# cover uses Google Fonts via @import (no local disk caching needed)
# body always uses system fonts via ReportLab
FONT_PAIRS = {
    "authoritative": {
        "display_css":  "Playfair Display",
        "body_css":     "IBM Plex Sans",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "confident": {
        "display_css":  "Syne",
        "body_css":     "Nunito Sans",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Syne:wght@600;800&family=Nunito+Sans:wght@400;600;700&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "clean": {
        "display_css":  "DM Serif Display",
        "body_css":     "DM Sans",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "expressive": {
        "display_css":  "Fraunces",
        "body_css":     "Inter",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,700;0,900;1,900&family=Inter:wght@300;400;500&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "scholarly": {
        "display_css":  "EB Garamond",
        "body_css":     "Source Sans 3",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@400;600&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "neutral": {
        "display_css":  "Outfit",
        "body_css":     "Outfit",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "restrained": {
        "display_css":  "Cormorant Garamond",
        "body_css":     "Jost",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&family=Jost:wght@300;400;500&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "bold": {
        "display_css":  "Barlow Condensed",
        "body_css":     "Barlow",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;900&family=Barlow:wght@400;500;600&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "dynamic": {
        "display_css":  "Montserrat",
        "body_css":     "Montserrat",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,700;0,900;1,400&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "classical": {
        "display_css":  "Cormorant",
        "body_css":     "Crimson Pro",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Cormorant:ital,wght@0,400;0,700;1,400&family=Crimson+Pro:wght@400;600&display=swap",
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "editorial": {
        "display_css":  "Bebas Neue",
        "body_css":     "Libre Franklin",
        "gfonts_import": (
            "https://fonts.googleapis.com/css2?family=Bebas+Neue"
            "&family=Libre+Franklin:ital,wght@0,400;0,700;1,400&display=swap"
        ),
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    # ── New moods (v2) ───────────────────────────────────────────────────────────
    "magazine": {
        "display_css":  "Playfair Display",
        "body_css":     "EB Garamond",
        "gfonts_import": (
            "https://fonts.googleapis.com/css2?family=Playfair+Display"
            ":ital,wght@0,700;0,900;1,700"
            "&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap"
        ),
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "darkroom": {
        "display_css":  "Playfair Display",
        "body_css":     "EB Garamond",
        "gfonts_import": (
            "https://fonts.googleapis.com/css2?family=Playfair+Display"
            ":ital,wght@0,700;0,900;1,700"
            "&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap"
        ),
        "display_rl":   "Times-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
    "terminal": {
        "display_css":  "Space Mono",
        "body_css":     "Space Mono",
        "gfonts_import": (
            "https://fonts.googleapis.com/css2?family=Space+Mono"
            ":ital,wght@0,400;0,700;1,400&display=swap"
        ),
        "display_rl":   "Courier-Bold",
        "body_rl":      "Courier",
        "body_b_rl":    "Courier-Bold",
    },
    "poster": {
        "display_css":  "Barlow Condensed",
        "body_css":     "Courier Prime",
        "gfonts_import": (
            "https://fonts.googleapis.com/css2?family=Barlow+Condensed"
            ":wght@700;900"
            "&family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap"
        ),
        "display_rl":   "Times-Bold",
        "body_rl":      "Courier",
        "body_b_rl":    "Courier-Bold",
    },
    "professional": {
        # Richee brand: Inter (sans-serif, clean) for cover, fallback to system
        "display_css":  "Inter",
        "body_css":     "Inter",
        "gfonts_import": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap",
        "display_rl":   "Helvetica-Bold",
        "body_rl":      "Helvetica",
        "body_b_rl":    "Helvetica-Bold",
    },
}

SYSTEM_FALLBACK = {
    "display_css":  "Georgia",
    "body_css":     "Arial",
    "gfonts_import": "",
    "display_rl":   "Times-Bold",
    "body_rl":      "Helvetica",
    "body_b_rl":    "Helvetica-Bold",
}


# ── Colour helpers ──────────────────────────────────────────────────────────────
def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lighten(hex_color: str, factor: float = 0.09) -> str:
    """Blend hex_color toward white (factor = accent weight, 0=white, 1=full color)."""
    r, g, b = _hex_to_rgb(hex_color)
    return "#{:02X}{:02X}{:02X}".format(
        round(r * factor + 255 * (1 - factor)),
        round(g * factor + 255 * (1 - factor)),
        round(b * factor + 255 * (1 - factor)),
    )


# ── Token assembly ─────────────────────────────────────────────────────────────
def build_tokens(
    title: str,
    doc_type: str,
    author: str = "",
    date: str = "",
    accent_override: str = "",
    cover_bg_override: str = "",
    pattern: str = "",
    layout_params: dict | None = None,
) -> dict:
    palette   = PALETTES.get(doc_type, PALETTES["general"]).copy()
    mood      = palette["mood"]
    font_pair = FONT_PAIRS.get(mood, SYSTEM_FALLBACK)

    # Apply caller-supplied overrides before token assembly
    if accent_override:
        palette["accent"]    = accent_override
        palette["accent_lt"] = _lighten(accent_override, 0.09)
    if cover_bg_override:
        palette["cover_bg"] = cover_bg_override

    # ── Layout selection: AI-driven > explicit pattern > type default ──
    if layout_params:
        cover_pattern = "custom"
    elif pattern:
        cover_pattern = pattern
    else:
        cover_pattern = palette.get("cover_pattern", "fullbleed")

    # ── Per-type scale & layout overrides ──
    type_scale  = palette.pop("scale", {})
    type_layout = palette.pop("layout", {})

    tokens = {
        # Identity
        "title":    title,
        "author":   author,
        "date":     date,
        "doc_type": doc_type,

        # Palette — base colours
        "cover_bg":      palette["cover_bg"],
        "accent":        palette["accent"],
        "accent_lt":     palette["accent_lt"],
        "text_light":    palette["text_light"],
        "page_bg":       palette["page_bg"],
        "dark":          palette["dark"],
        "body_text":     palette["body_text"],
        "muted":         palette["muted"],

        # Palette — extended (optional)
        "card_bg":       palette.get("card_bg", ""),
        "card_border":   palette.get("card_border", ""),
        "card_radius":   palette.get("card_radius", 0),
        "tertiary":      palette.get("tertiary", palette["muted"]),
        "divider":       palette.get("divider", palette["accent"]),

        "cover_pattern": cover_pattern,
        "layout_params": layout_params,
        "mood":          mood,

        # Typography — CSS names for cover HTML (loaded via Google Fonts @import)
        "font_display":     font_pair["display_css"],
        "font_body":        font_pair["body_css"],
        "gfonts_import":    font_pair["gfonts_import"],

        # Typography — ReportLab system font names for body pages (Latin)
        "font_display_rl":  font_pair["display_rl"],
        "font_body_rl":     font_pair["body_rl"],
        "font_body_b_rl":   font_pair["body_b_rl"],

        # Typography — CJK font names for body pages (auto-used when content has CJK chars)
        "font_cjk_rl":      "STSong-Light",
        "font_cjk_b_rl":    "STSong-Light",

        # Legacy keys (kept so render_body.py's register_fonts is a no-op)
        "font_heading":  font_pair["display_rl"],
        "font_body_b":   font_pair["body_b_rl"],
        "font_paths":    {},

        # Type scale (pt) — overridable per-type
        "size_display":  type_scale.get("size_display", 54),
        "size_h1":       type_scale.get("size_h1", 22),
        "size_h2":       type_scale.get("size_h2", 15),
        "size_h3":       type_scale.get("size_h3", 11.5),
        "size_body":     type_scale.get("size_body", 10.5),
        "size_caption":  type_scale.get("size_caption", 8.5),
        "size_meta":     type_scale.get("size_meta", 8),

        # Layout (pt, 1cm ≈ 28.35pt) — overridable per-type
        "margin_left":   type_layout.get("margin", 79),
        "margin_right":  type_layout.get("margin", 79),
        "margin_top":    type_layout.get("margin", 79),
        "margin_bottom": type_layout.get("margin", 71),
        "card_pad":      type_layout.get("card_pad", 0),
        "section_gap":   type_scale.get("section_gap", 26),
        "para_gap":      type_scale.get("para_gap", 8),
        "line_gap":      type_scale.get("line_gap", 17),
    }
    return tokens


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate design tokens from document metadata")
    parser.add_argument("--title",  default="Untitled Document")
    parser.add_argument("--type",   default="general",
                        choices=list(PALETTES.keys()),
                        help="Document type: " + ", ".join(PALETTES.keys()))
    parser.add_argument("--author", default="")
    parser.add_argument("--date",   default="")
    parser.add_argument("--meta",     help="JSON file with title/type/author/date keys")
    parser.add_argument("--accent",   default="",
                        help="Override accent colour (hex, e.g. #2D6A8F). "
                             "accent_lt is auto-derived by lightening toward white.")
    parser.add_argument("--cover-bg", default="",
                        help="Override cover background colour (hex).")
    parser.add_argument("--pattern", default="",
                        choices=list(PALETTES.keys()),
                        help="Explicit cover pattern (overrides type default): "
                             + ", ".join(PALETTES.keys()))
    parser.add_argument("--layout-params", default="",
                        help="Path to layout_params.json for AI-generated custom cover layout.")
    parser.add_argument("--out",    default="tokens.json")
    args = parser.parse_args()

    if args.meta:
        try:
            with open(args.meta) as f:
                meta = json.load(f)
            args.title  = meta.get("title",  args.title)
            args.type   = meta.get("type",   args.type)
            args.author = meta.get("author", args.author)
            args.date   = meta.get("date",   args.date)
            if not args.pattern:
                args.pattern = meta.get("pattern", "")
        except Exception as e:
            print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
            sys.exit(1)

    # Load AI-generated layout params if specified
    lp = None
    if args.layout_params:
        try:
            with open(args.layout_params, encoding="utf-8") as f:
                lp = json.load(f)
        except Exception as e:
            print(json.dumps({"status": "error", "error": f"layout-params load failed: {e}"}),
                  file=sys.stderr)
            sys.exit(1)

    tokens = build_tokens(
        args.title, args.type, args.author, args.date,
        accent_override=args.accent,
        cover_bg_override=getattr(args, "cover_bg", ""),
        pattern=args.pattern,
        layout_params=lp,
    )

    try:
        with open(args.out, "w") as f:
            json.dump(tokens, f, indent=2)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}), file=sys.stderr)
        sys.exit(3)

    print(json.dumps({
        "status":  "ok",
        "out":     args.out,
        "mood":    tokens["mood"],
        "pattern": tokens["cover_pattern"],
        "fonts":   f'{tokens["font_display"]} / {tokens["font_body"]}',
    }))


if __name__ == "__main__":
    main()
