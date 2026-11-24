#!/usr/bin/env python3
"""Derive a business-deck colour set from one brand colour (pure python, no PIL).

    python3 brand_palette.py "#FFD100"                    # palette picked by hue
    python3 brand_palette.py "#E60012" --palette claret_oxford
    python3 brand_palette.py --palette exec_navy          # no brand: the palette's own colours, same keys
    python3 brand_palette.py "#0052D9" --format table

The named palette is the mood / structure reference (which accent family, warm or cool neutrals); every concrete value
is computed in OKLCH from the brand colour (a brand too light for text — yellow, gold — hands text, series and tints to
the palette main family and keeps the brand for logo / bars / small blocks) so tints stay clean (controlled chroma, no muddy 70 % / 88 % white mixes),
text colours meet 4.5:1 on white, and nothing is black / near-black except as tinted ink.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys

# palette -> (main, accent, second) — mirrors svg_lib/svg_palettes.py PALETTES[name]["exhibit"] (business-deck set)
PALETTES = {
    "exec_navy": ("#16283C", "#B4782D", "#4A5A6E"),
    "claret_oxford": ("#0F3E6E", "#990F3D", "#4C7AA6"),
    "sage_review": ("#3E5B4C", "#B84C3A", "#738A78"),
    "oxford_navy_gold": ("#101E38", "#B8862E", "#426291"),
    "forest_gold": ("#1E4D3A", "#B08A3E", "#5C8A73"),
    "bcg_green": ("#197048", "#D6861E", "#4A9A72"),
    "ember_orange": ("#C2561C", "#8F3A14", "#DE9A62"),
    "burgundy_coral": ("#8B1E3F", "#E05A47", "#C47A8A"),
    "kearney_purple": ("#4E3F69", "#9A73B0", "#7F6C9C"),
    "plum_mauve": ("#5E4473", "#A06DAE", "#8C7A99"),
    "lek_forest": ("#1F4238", "#3F8C68", "#5E7F72"),
    "rolandberger_grey": ("#3A4148", "#4C6D96", "#7F8182"),
}

TEXT_CONTRAST = 4.5


# ---------- colour math ----------
def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"not a hex colour: {h!r}")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_hex(rgb):
    return "#" + "".join("%02X" % round(min(1, max(0, c)) * 255) for c in rgb)


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rgb_oklch(rgb):
    r, g, b = (_lin(c) for c in rgb)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def _oklch_lin(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def oklch_rgb(L, C, H):
    """OKLCH -> sRGB, reducing chroma (not clipping channels) until the colour is in gamut."""
    lo, hi = 0.0, C
    rgb = _oklch_lin(L, C, H)
    if all(-1e-6 <= c <= 1 + 1e-6 for c in rgb):
        return tuple(_gam(min(1, max(0, c))) for c in rgb)
    for _ in range(30):
        mid = (lo + hi) / 2
        if all(-1e-6 <= c <= 1 + 1e-6 for c in _oklch_lin(L, mid, H)):
            lo = mid
        else:
            hi = mid
    return tuple(_gam(min(1, max(0, c))) for c in _oklch_lin(L, lo, H))


def luminance(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b=(1, 1, 1)):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _hsl(rgb):
    mx, mn = max(rgb), min(rgb)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    r, g, b = rgb
    h = ((g - b) / d % 6) if mx == r else ((b - r) / d + 2) if mx == g else ((r - g) / d + 4)
    return h * 60, s, l


QUIET_ACCENT = {"burgundy_coral": "#4F5B66"}   # in-palette cool grey used when every warm hue clashes with the brand


# ---------- derivation ----------
def default_palette(rgb):
    """Hue -> palette, same mapping as business-deck.md: blue claret_oxford, red burgundy_coral, orange ember_orange,
    gold / yellow exec_navy, green / teal bcg_green, purple / pink kearney_purple, grey rolandberger_grey."""
    h, s, l = _hsl(rgb)
    if s < 0.15 or l < 0.08:
        return "rolandberger_grey"
    for upper, name in ((12, "burgundy_coral"), (38, "ember_orange"), (68, "exec_navy"), (185, "bcg_green"),
                        (255, "claret_oxford"), (335, "kearney_purple"), (360, "burgundy_coral")):
        if h < upper:
            return name
    return "burgundy_coral"


def _text_safe(L, C, H, target=TEXT_CONTRAST):
    """Darken (keep hue; yellows lean toward amber so they don't turn olive) until contrast on white >= target."""
    if 80 <= H <= 115:
        H = 70 + (H - 80) * 0.3
    for _ in range(80):
        rgb = oklch_rgb(L, C, H)
        if contrast(rgb) >= target:
            return rgb
        L -= 0.01
        C = min(C, 0.16)
    return oklch_rgb(L, C, H)


def derive(brand=None, palette=None):
    if brand is None and palette is None:
        raise ValueError("give a brand colour, --palette, or both")
    pal_main, pal_accent, pal_second = PALETTES[palette] if palette else (None, None, None)
    src = brand or pal_main
    rgb = hex_rgb(src)
    palette = palette or default_palette(rgb)
    pal_main, pal_accent, pal_second = PALETTES[palette]
    L, C, H = rgb_oklch(rgb)
    warm = C >= 0.03 and (H < 110 or H > 330)
    flags = {}

    c_white = contrast(rgb)
    flags["brand_too_light_for_text"] = c_white < TEXT_CONTRAST
    flags["brand_too_saturated_for_text"] = not flags["brand_too_light_for_text"] and C > 0.21 and L > 0.52
    flags["brand_too_bright_for_large_fill"] = C > 0.17 and L > 0.55
    pL0, pC0, pH0 = rgb_oklch(hex_rgb(pal_main))
    # too light for text (yellow / gold / light orange / mint): darkening the brand gives mustard / brown, so the
    # palette's own main (navy, teal …) carries text and series; the brand stays on logo, bars and small blocks
    host = flags["brand_too_light_for_text"] and brand is not None
    if host:
        main_text = hex_rgb(pal_main) if contrast(hex_rgb(pal_main)) >= TEXT_CONTRAST else _text_safe(pL0, pC0, pH0)
    elif flags["brand_too_saturated_for_text"]:   # signal red / electric blue: calm it a notch for text and series
        main_text = oklch_rgb(L - 0.05, 0.19, H)
    else:
        main_text = rgb
    mL, mC, mH = rgb_oklch(main_text)

    # tints: hue of the brand, lightness fixed, chroma capped so they read clean, not muddy or candy
    tH, cb = (mH, max(min(mC, 0.10), 0.02)) if host else (H, max(C, 0.02))   # host: tints of the main family, not beige
    light = oklch_rgb(0.87, min(cb * 0.42, 0.075), tH)
    light2 = oklch_rgb(0.955, min(cb * 0.20, 0.03), tH)
    second = oklch_rgb((mL + 0.87) / 2 - 0.04, min(mC * 0.65, 0.11), mH)
    deep = oklch_rgb(max(0.20 if host else 0.28, mL - (0.06 if host else 0.13)), min(mC, 0.12), mH)

    # accent: the palette's accent family, toned; if its hue collides with the brand, the palette main's hue (lifted
    # off near-black); if that collides too, a deeper brand shade. Never black / near-black, never neon.
    aL, aC, aH = rgb_oklch(hex_rgb(pal_accent))
    pL, pC, pH = pL0, pC0, pH0
    def clash(h):
        return C >= 0.04 and hue_gap(h, H) < 35
    if host and not (C >= 0.04 and hue_gap(H, mH) < 35):   # main is the palette main; the brand itself (deepened
        accent, accent_from = _text_safe(L, C, H, 3.0), "brand_deep"   # to stay legible) is the one highlight
    elif host and aC >= 0.04 and hue_gap(aH, mH) >= 35:   # light blue brand on a navy main: same hue, use palette accent
        accent, accent_from = oklch_rgb(min(max(aL, 0.45), 0.62), min(aC, 0.14), aH), palette + ".accent"
    elif aC >= 0.04 and not clash(aH):
        accent, accent_from = oklch_rgb(min(max(aL, 0.45), 0.62), min(aC, 0.14), aH), palette + ".accent"
    elif pC >= 0.03 and not clash(pH):
        accent, accent_from = oklch_rgb(min(max(pL, 0.42), 0.50), min(max(pC, 0.06), 0.12), pH), palette + ".main"
    elif palette in QUIET_ACCENT:   # a warm palette whose accent and main both sit on the brand's hue (red brand on
        accent, accent_from = hex_rgb(QUIET_ACCENT[palette]), palette + ".quiet"   # wine + coral): its cool grey highlights
    else:
        accent, accent_from = oklch_rgb(max(0.40, mL - 0.12), min(max(mC, 0.10), 0.16), mH), "brand_deep"
    if host:   # neutrals follow the main family, so a yellow brand does not tint every grey beige
        warm = mC >= 0.03 and (mH < 110 or mH > 330)
    gh, gc = (65, 0.010) if warm else (250, 0.012)
    ink = oklch_rgb(0.25, min(0.02, max(mC if host else C, 0.01) * 0.2), mH if host else H)
    out = {
        "palette": palette,
        "brand": rgb_hex(rgb),
        "main_text": rgb_hex(main_text),
        "second": rgb_hex(second),
        "light": rgb_hex(light),
        "light2": rgb_hex(light2),
        "deep": rgb_hex(deep),
        "accent": rgb_hex(accent),
        "accent_from": accent_from,
        "grey": rgb_hex(oklch_rgb(0.70, gc, gh)),
        "grey_light": rgb_hex(oklch_rgb(0.90, gc * 0.6, gh)),
        "ink": rgb_hex(ink),
        "ink_muted": rgb_hex(oklch_rgb(0.52, gc * 1.2, gh)),
        "bg": "#FFFFFF",
        "on_brand": "#FFFFFF" if c_white >= TEXT_CONTRAST else rgb_hex(ink),
        "neutral_temperature": "warm" if warm else "cool",
        "flags": flags,
        "rgb": {},
        "contrast_on_white": {"brand": round(c_white, 2), "main_text": round(contrast(main_text), 2),
                              "accent": round(contrast(accent), 2)},
    }
    if brand is None:   # palette only: keep the palette's own main / accent / second
        out.update(brand=pal_main, main_text=pal_main, accent=pal_accent, second=pal_second, accent_from=palette)
    out["rgb"] = {k: "rgb(%d,%d,%d)" % tuple(round(c * 255) for c in hex_rgb(out[k])) for k, _ in ROLES}
    return out


ROLES = [
    ("brand", "品牌原色：logo、少量实心色块 / 竖条 / 编号底（亮色品牌只做小面积）"),
    ("main_text", "主色：主数据系列、关键数字、图表小标题、编号、图标、描边、关键词加粗（浅色品牌时取 palette main）"),
    ("second", "第二数据系列"),
    ("light", "第三及以后系列、描边、进度条底槽"),
    ("light2", "浅底格（表头底、提示条底）"),
    ("deep", "图表里需要压暗的那一个系列 / 负值"),
    ("accent", "每页最多 1 处强调"),
    ("grey", "对照系列（去年 / 竞品）"),
    ("grey_light", "分隔线、网格线、未选中状态"),
    ("ink", "标题、正文、表格文字、轴标签、0.5–1pt 细线"),
    ("ink_muted", "副标题、口径、脚注、来源、页码"),
    ("bg", "页面底色"),
    ("on_brand", "brand 实心块上的文字"),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("brand", nargs="?", help="brand colour, e.g. #FFD100")
    ap.add_argument("--palette", choices=sorted(PALETTES), help="mood reference (default: picked by brand hue)")
    ap.add_argument("--format", choices=("json", "table"), default="json")
    a = ap.parse_args(argv)
    if not a.brand and not a.palette:
        ap.error("give a brand colour, --palette, or both")
    try:
        out = derive(a.brand, a.palette)
    except ValueError as e:
        ap.error(str(e))
    if a.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        flags = ", ".join(k for k, v in out["flags"].items() if v) or "none"
        print(f"palette {out['palette']}  ·  neutrals {out['neutral_temperature']}  ·  flags {flags}")
        for k, role in ROLES:
            print(f"{k:<11} {out[k]}  {out['rgb'][k]:<17} {role}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
