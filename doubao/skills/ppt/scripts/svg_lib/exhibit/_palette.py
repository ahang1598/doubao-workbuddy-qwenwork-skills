"""Colour roles for exhibits.

An exhibit never hard-codes hues. It asks the palette for roles:
  main      – the bulk series / subject bars           (McKinsey: deep blue #051E7B)
  accent    – the one highlighted object / argument    (McKinsey: cyan #00A9F4)
  second    – a minor second series                    (McKinsey: electric blue)
  light     – forecast / partial / pale companion of main
  light2    – pale companion of accent
  third     – an extra categorical hue (teal etc.)
  deep      – near-black structural fill (total rows, dark category)
  neg       – contrast warm colour for decline / risk / counter-example (red, or amber in red palettes)
  good/bad  – favourable / unfavourable variance (IBCS: only variances are coloured); muted green / red, or a
              blue / orange pair when the palette's main or accent is itself red or green
  py        – previous-year bars (light grey with a hint of main; lightness ≥ 80 %, enforced)
  ac_dim    – de-focused actual bars next to PY (dark grey, lightness ≤ 45 %)
  context   – grey for "everything else"
  dim       – very light grey for de-focused marks
  ink/text/sub/axis/grid – typography and structure greys
Consulting palettes in svg_palettes.py carry an explicit ``exhibit`` block; any other palette is mapped
from its ink / accent / secondary / series.
"""

from __future__ import annotations

import colorsys

from ..svg_palettes import PALETTES, resolve_palette

_NEUTRAL = {"ink": "#000000", "text": "#222222", "sub": "#555555", "axis": "#8C8C8C", "grid": "#E3E3E3",
            "context": "#B0B0B0", "dim": "#D6D6D6", "track": "#E6E6E6", "band": "#F2F2F2"}


def _hex(c: str) -> str:
    c = c.strip()
    if c.startswith("#"):
        return c.upper() if len(c) == 7 else c
    if c.startswith("rgba") or c.startswith("rgb"):
        parts = c[c.index("(") + 1:c.index(")")].split(",")
        r, g, b = (int(float(p)) for p in parts[:3])
        return f"#{r:02X}{g:02X}{b:02X}"
    return c


def _lighten(hexc: str, amount: float) -> str:
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l + (1 - l) * amount
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def _warm(accent: str, main: str = "#000000") -> str:
    """Colour for decline / risk / counter-example: a dark neutral grey — never a hue outside the palette (a red on a
    green or blue deck reads as an off-palette accent)."""
    return "#666666"


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _from_hls(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"


def _mix(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def _hue_class(c):
    """'red' | 'green' | None — used to keep variance colours from looking like the brand colour."""
    try:
        r, g, b = _rgb(_hex(c))
    except (ValueError, TypeError):
        return None
    if max(r, g, b) - min(r, g, b) < 18:   # grey: no hue
        return None
    h, l, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if l < 0.08 or l > 0.95:
        return None
    deg = h * 360
    if deg < 22 or deg >= 335:
        return "red"
    if 70 <= deg < 175:
        return "green"
    return None


def luminance(c):
    """WCAG relative luminance of #RRGGBB."""
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(_hex(c))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(c1, c2="#FFFFFF"):
    """WCAG contrast ratio between two colours (default: against white)."""
    a, b = sorted((luminance(c1), luminance(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _variance_roles(main, accent):
    """good / bad / py for a palette: muted green / red, or blue / orange when the brand itself is red or green."""
    brand = {_hue_class(main), _hue_class(accent)}
    good, bad = ("#3F6E9E", "#C47A3A") if brand & {"red", "green"} else ("#4C8A57", "#B8463A")
    return {"good": good, "bad": bad, "py": _mix(_hex(main), "#D4D4D4", 0.92)}


PY_MIN_L, AC_DIM_MAX_L = 0.80, 0.45   # IBCS: PY reads light grey, a de-focused AC dark grey — never two mid greys


def _lightness(c):
    r, g, b = (v / 255 for v in _rgb(_hex(c)))
    return colorsys.rgb_to_hls(r, g, b)[1]


def _ibcs_greys(out):
    """PY: near-neutral (saturation ≤ 0.12) with lightness ≥ PY_MIN_L; ac_dim (de-focused actuals): lightness ≤
    AC_DIM_MAX_L. A palette whose py is green / mid grey is pulled to light grey."""
    try:
        r, g, b = (v / 255 for v in _rgb(_hex(out.get("py", "#D9D9D9"))))
        h, l, s_ = colorsys.rgb_to_hls(r, g, b)
        out["py"] = _from_hls(h, max(l, PY_MIN_L + 0.02), min(s_, 0.12))
    except (ValueError, TypeError):
        out["py"] = "#D9D9D9"
    ac = out.get("ac_dim")
    if not ac or _lightness(ac) > AC_DIM_MAX_L:
        out["ac_dim"] = "#5A5A5A"
    return out


def _derive(brand, palette=None):
    """scripts/brand_palette.py derive(): the one brand → role mapping (business-deck.md 配色脚本)."""
    import sys
    from pathlib import Path
    scripts = str(Path(__file__).resolve().parents[2])
    if scripts not in sys.path:
        sys.path.append(scripts)
    import brand_palette as _bp
    return _bp.derive(brand, palette)


def brand_palette(primary, secondary=None, name=None, palette=None) -> dict:
    """Palette dict from a brand colour ("#E60012"), usable everywhere a palette name is (Exhibit(palette=...),
    frame(...), roles(...)). Same roles as scripts/brand_palette.py (one colour source for exhibit and hand-written
    XML): main = main_text (a brand too light for text hands it to the palette main; a signal colour is calmed),
    accent = the script's accent (a different hue from the brand), second / light / light2 / deep = its tints and
    shade; secondary overrides second. palette: the mood palette passed to the script (default by brand hue).
    good / bad variance colours avoid the brand hue (blue / orange pair for red or green brands)."""
    p = _hex(primary)
    if not (isinstance(p, str) and p.startswith("#") and len(p) == 7):
        raise ValueError(f"brand_palette: primary 要写成 #RRGGBB（收到 {primary!r}）")
    d = _derive(p, palette)
    main, accent = d["main_text"], d["accent"]
    sec = _hex(secondary) if secondary else d["second"]
    ex = {"main": main, "accent": accent, "second": sec, "light": d["light"], "light2": d["light2"],
          "third": _lighten(sec, 0.35), "deep": d["deep"]}
    ex.update(_variance_roles(main, accent))

    def rgba(c):
        r, g, b = _rgb(c)
        return f"rgba({r},{g},{b},1)"
    return {"name": name or f"brand_{p[1:].lower()}", "series_order": "fixed", "exhibit": ex, "brand": p,
            "ink": rgba(d["ink"]), "accent": rgba(accent), "secondary": rgba(sec), "bg": "rgba(255,255,255,1)",
            "muted": "rgba(118,118,118,0.65)",
            "series": [rgba(c) for c in (main, accent, sec, d["light"], "#B0B0B0", "#D6D6D6")]}


_DEFAULT = ["mckinsey_blue"]


def set_default(palette):
    """The palette last passed explicitly to frame()/Exhibit() becomes the default for every helper (points, kpis,
    takeaway, …) so one forgotten palette= argument cannot drop a page back to blue."""
    if palette:
        _DEFAULT[0] = palette


def roles(palette=None, dark=False) -> dict:
    """Resolve a palette name/dict into exhibit colour roles (all #RRGGBB); None = the current deck default.
    dark=True: chart sits on a dark page background -> light text / grid roles (None: from the palette's bg luminance;
    Exhibit passes None by default)."""
    palette = palette or _DEFAULT[0]
    p = resolve_palette(palette) if not isinstance(palette, dict) else palette
    if p is None:
        p = dict(PALETTES["mckinsey_blue"])
    out = _roles(p)
    bg = _hex(p.get("bg") or "#FFFFFF")
    if dark is None:
        try:
            dark = luminance(bg) < 0.18
        except (ValueError, TypeError):
            dark = False
    return dark_roles(out, bg if dark and _is_hex(bg) and luminance(bg) < 0.18 else "#111111") if dark else out


def _is_hex(c):
    return isinstance(c, str) and len(c) == 7 and c.startswith("#")


_DARK_NEUTRAL = {"ink": "#FFFFFF", "text": "#F2F2F2", "sub": "#C9CDD2", "axis": "#9AA0A6", "grid": "#3A3F47",
                 "context": "#80868E", "dim": "#4A5058", "track": "#2E333B", "band": "#22262D", "ac_dim": "#8C9096"}


def dark_roles(out, bg="#111111") -> dict:
    """Roles for a chart on a dark page: near-white text, dark-grey grid / track, and data colours (main / second /
    deep / light …) lightened until they read on bg (contrast ≥ 3)."""
    out = dict(out, **_DARK_NEUTRAL)
    out["page_bg"] = bg   # Exhibit.tostring paints white halos / label ovals in this colour instead of #FFFFFF
    for k in ("main", "accent", "second", "third", "deep", "light", "light2", "neg", "good", "bad"):
        c = out.get(k)
        if not _is_hex(c):
            continue
        for _ in range(12):
            if contrast(c, bg) >= 3:
                break
            c = _lighten(c, 0.15)
        out[k] = c
    for k in ("dim", "ac_dim"):   # non-focus bars / points still read on the dark page (≥ 3:1)
        c = out.get(k)
        for _ in range(12):
            if not _is_hex(c) or contrast(c, bg) >= 3:
                break
            c = _lighten(c, 0.12)
        out[k] = c
    return out


def _roles(p) -> dict:
    out = dict(_NEUTRAL)
    if "exhibit" in p:
        out.update({k: _hex(v) for k, v in p["exhibit"].items()})
        out.setdefault("neg", _warm(out["accent"], out["main"]))
        for k, v in _variance_roles(out["main"], out["accent"]).items():
            out.setdefault(k, v)
        return _ibcs_greys(out)
    series = [_hex(c) for c in p.get("series", [])]
    main = series[0] if series else _hex(p.get("ink", "#1F3A5F"))
    accent = _hex(p.get("accent", series[1] if len(series) > 1 else "#00A9F4"))
    second = _hex(p.get("secondary", series[2] if len(series) > 2 else main))
    out.update(main=main, accent=accent, second=second, light=_lighten(main, 0.62), light2=_lighten(accent, 0.6),
               third=series[3] if len(series) > 3 else _lighten(second, 0.35), deep=_hex(p.get("ink", "#051C2C")))
    out["neg"] = _warm(accent, main)
    out.update(_variance_roles(main, accent))
    return _ibcs_greys(out)
