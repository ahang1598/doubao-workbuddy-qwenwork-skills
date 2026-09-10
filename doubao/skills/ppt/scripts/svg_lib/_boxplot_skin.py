"""svg_lib/_boxplot_skin.py

Boxplot skeleton overlay + skin apply (extracted from the v23 skeleton experiment (boxplot group)).

Consumer:
  - svg_lib.charts.boxplot (notched_outlined / variable_width_gradient / beeswarm / strip variants)
"""
from __future__ import annotations

import math
import os
import re
import sys
import uuid

# svg_palettes.py 与本文件同目录（svg_lib/），确保它在 sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from svg_palettes import resolve_palette


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------

RGBA_RE = re.compile(r"rgba\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*([0-9.]+)\s*\)")


def _rgba_parts(s: str):
    m = RGBA_RE.match(s.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))


def _rgba(r, g, b, a=1.0):
    return f"rgba({int(r)},{int(g)},{int(b)},{a:g})"


def _with_alpha(rgba_str, alpha):
    p = _rgba_parts(rgba_str)
    if not p:
        return rgba_str
    return _rgba(p[0], p[1], p[2], alpha)


def _inject_defs(svg: str, defs_content: str) -> str:
    """Insert a <defs>...</defs> block right after the opening <svg ...> tag."""
    idx = svg.find(">")
    if idx == -1:
        return svg
    return svg[: idx + 1] + f"<defs>{defs_content}</defs>" + svg[idx + 1 :]


def _post_process_rects(svg: str, transform_rect) -> str:
    """Iterate over every <rect ...>/> tag; call transform_rect(attrs_dict) which
    can mutate the dict; re-emit the tag. `transform_rect` may also return a
    string that fully replaces the tag."""
    out = []
    i = 0
    while i < len(svg):
        j = svg.find("<rect", i)
        if j == -1:
            out.append(svg[i:])
            break
        out.append(svg[i:j])
        # find end of tag
        k = svg.find(">", j)
        if k == -1:
            out.append(svg[j:])
            break
        tag = svg[j : k + 1]
        # self-closing or not, we treat all <rect .../> as leaves here.
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        replacement = transform_rect(attrs)
        if replacement is None:
            # rebuild
            attr_str = " ".join(f'{k2}="{v2}"' for k2, v2 in attrs.items())
            self_close = tag.rstrip().endswith("/>")
            out.append(f"<rect {attr_str}" + ("/>" if self_close else ">"))
        else:
            out.append(replacement)
        i = k + 1
    return "".join(out)


# -----------------------------------------------------------------------------
# skin post-processors (work on any SVG produced by make_xxx)
# -----------------------------------------------------------------------------


def _skin_outlined(svg: str, box_selector_role: str = None) -> str:
    """Add / strengthen stroke on filled rects. For rects whose fill is not
    transparent, drop opacity to ~0.16 and add a 1.4-wide stroke of the same
    ink color."""

    def tx(attrs):
        if attrs.get("data-role-skip") == "1":
            return None
        if box_selector_role and attrs.get("data-role") not in (box_selector_role, box_selector_role + "-accent"):
            return None
        fill = attrs.get("fill", "")
        if not fill or fill in ("none", "transparent"):
            return None
        p = _rgba_parts(fill)
        if not p:
            return None
        # skip already tiny alpha (background grid etc)
        if p[3] < 0.1:
            return None
        r, g, b, a = p
        attrs["fill"] = _rgba(r, g, b, 0.15)
        attrs["stroke"] = _rgba(r, g, b, 0.85)
        attrs["stroke-width"] = "1.3"
        return None

    return _post_process_rects(svg, tx)


def _skin_gradient(svg: str, id_prefix: str) -> str:
    """Replace filled rects with vertical linear gradient references. Skips
    tiny rects (< 8px wide/tall) to avoid ruining thin decorations."""
    defs_chunks = []
    counter = {"n": 0}

    def tx(attrs):
        if attrs.get("data-role-skip") == "1":
            return None
        fill = attrs.get("fill", "")
        if not fill or fill.startswith("url(") or fill in ("none", "transparent"):
            return None
        p = _rgba_parts(fill)
        if not p:
            return None
        r, g, b, a = p
        if a < 0.35:
            return None
        try:
            w = float(attrs.get("width", "0"))
            h = float(attrs.get("height", "0"))
            y = float(attrs.get("y", "0"))
        except ValueError:
            return None
        if w < 6 or h < 6:
            return None
        gid = f"{id_prefix}_{counter['n']}"
        counter["n"] += 1
        defs_chunks.append(
            f'<linearGradient id="{gid}" x1="0" y1="{y:.1f}" x2="0" y2="{y + h:.1f}" '
            f'gradientUnits="userSpaceOnUse">'
            f'<stop offset="0%" stop-color="{_rgba(r, g, b, 1.0)}"/>'
            f'<stop offset="100%" stop-color="{_rgba(r, g, b, 0.45)}"/>'
            f"</linearGradient>"
        )
        attrs["fill"] = f"url(#{gid})"
        return None

    new_svg = _post_process_rects(svg, tx)
    if defs_chunks:
        new_svg = _inject_defs(new_svg, "".join(defs_chunks))
    return new_svg


def _skin_layered(svg: str, id_prefix: str) -> str:
    """Add a subtle bottom-inner shadow + top highlight strip on top of each
    "big" rect. Implemented by duplicating the rect with a shorter dark band and
    a thin top light band."""
    tag_re = re.compile(r"<rect\s+([^>]+?)/?>")

    out = []
    last = 0
    for m in tag_re.finditer(svg):
        out.append(svg[last : m.start()])
        tag = m.group(0)
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        last = m.end()
        fill = attrs.get("fill", "")
        p = _rgba_parts(fill)
        if not p or fill.startswith("url"):
            out.append(tag)
            continue
        try:
            x = float(attrs["x"])
            y = float(attrs["y"])
            w = float(attrs["width"])
            h = float(attrs["height"])
        except (KeyError, ValueError):
            out.append(tag)
            continue
        if w < 12 or h < 12 or p[3] < 0.35:
            out.append(tag)
            continue
        out.append(tag)
        r, g, b, a = p
        # dark band bottom third
        dh = min(h * 0.35, 22)
        out.append(
            f'<rect x="{x:.1f}" y="{y + h - dh:.1f}" width="{w:.1f}" height="{dh:.1f}" '
            f'fill="{_rgba(max(0, r - 30), max(0, g - 30), max(0, b - 30), 0.32)}"/>'
        )
        # thin bright band on top
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="2.4" '
            f'fill="{_rgba(min(255, r + 60), min(255, g + 60), min(255, b + 60), 0.55)}"/>'
        )
    out.append(svg[last:])
    return "".join(out)


def _skin_striped(svg: str, id_prefix: str) -> str:
    """Replace filled rects with a 45° stripe pattern of the same color."""
    defs_chunks = []
    counter = {"n": 0}
    used = {}

    def get_pat(color_rgba):
        p = _rgba_parts(color_rgba)
        if not p:
            return None
        key = (p[0], p[1], p[2])
        if key in used:
            return used[key]
        pid = f"{id_prefix}_pat_{counter['n']}"
        counter["n"] += 1
        r, g, b = key
        # base wash + dark stripe
        defs_chunks.append(
            f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="7" height="7" '
            f'patternTransform="rotate(45)">'
            f'<rect width="7" height="7" fill="{_rgba(r, g, b, 0.18)}"/>'
            f'<rect width="2.2" height="7" fill="{_rgba(r, g, b, 0.9)}"/>'
            f"</pattern>"
        )
        used[key] = pid
        return pid

    def tx(attrs):
        fill = attrs.get("fill", "")
        if not fill or fill.startswith("url(") or fill in ("none", "transparent"):
            return None
        p = _rgba_parts(fill)
        if not p or p[3] < 0.35:
            return None
        try:
            w = float(attrs.get("width", "0"))
            h = float(attrs.get("height", "0"))
        except ValueError:
            return None
        if w < 8 or h < 8:
            return None
        pid = get_pat(fill)
        if pid:
            attrs["fill"] = f"url(#{pid})"
        return None

    new_svg = _post_process_rects(svg, tx)
    if defs_chunks:
        new_svg = _inject_defs(new_svg, "".join(defs_chunks))
    return new_svg


def apply_skin(svg: str, variant: str, uid_prefix: str = "bp_skin") -> str:
    if variant in (None, "flat"):
        return svg
    if variant == "outlined":
        # outlined skin does not inject any <defs> IDs, so uid_prefix is unused
        # and no per-call uniqueness is needed.
        return _skin_outlined(svg)
    # For variants that inject <defs> elements with IDs, append a random suffix
    # so that using the same variant twice in one deck does not produce
    # duplicate IDs (which triggers duplicate_element_id lint errors).
    uniq_prefix = f"{uid_prefix}_{uuid.uuid4().hex[:6]}"
    if variant == "gradient":
        return _skin_gradient(svg, uniq_prefix + "_grad")
    if variant == "layered":
        return _skin_layered(svg, uniq_prefix + "_lay")
    if variant == "striped":
        return _skin_striped(svg, uniq_prefix + "_str")
    return svg


# -----------------------------------------------------------------------------
# skeleton overrides for boxplot: beeswarm, notched, variable_width, strip
# -----------------------------------------------------------------------------


def _strip_boxplot_body(svg: str) -> str:
    """Remove baseline box body elements from a make_boxplot() SVG.

    Strips:
      * box rects (fill alpha 0.22)
      * jitter dots (circle fill alpha 0.35)
      * whiskers + whisker caps (INK-colored lines with stroke-width 1.1)
      * median lines (colored lines with stroke-width 2.2 stroke-linecap=square)
      * mean marker (PAPER-filled r=3.2 circle + INK dot r=0.9)

    We deliberately keep the axis baseline (stroke-width=1) and gridlines
    (alpha 0.06/0.14) so the notched/variable_width overlays can align with
    y-ticks. Outlier open circles (fill="none") are also kept.
    """
    # box rects
    svg = re.sub(
        r'<rect[^>]*fill="rgba\(\d+,\d+,\d+,0\.22\)"[^>]*/>',
        "",
        svg,
    )
    # jitter dots
    svg = re.sub(
        r'<circle[^>]*fill="rgba\(\d+,\d+,\d+,0\.35\)"[^>]*/>',
        "",
        svg,
    )
    # median lines (fully-opaque colored line, stroke-width 2.2, square linecap)
    svg = re.sub(
        r'<line[^>]*stroke-width="2\.2"[^>]*stroke-linecap="square"[^>]*/>',
        "",
        svg,
    )
    # whiskers + whisker caps: stroke-width 1.1 with INK color (fully opaque
    # rgba with alpha 1). Grid lines share stroke-width 1 (not 1.1) so we
    # target 1.1 specifically. We match `stroke-width="1.1"` on <line>.
    svg = re.sub(
        r'<line[^>]*stroke-width="1\.1"[^>]*/>',
        "",
        svg,
    )
    # mean marker: outer PAPER-filled r=3.2 circle. PAPER is palette-dependent
    # so we match by `r="3.2"` with `fill=` other than "none".
    svg = re.sub(
        r'<circle[^>]*r="3\.2"[^>]*fill="rgba\([^"]*\)"[^>]*/>',
        "",
        svg,
    )
    # mean inner dot: r=0.9
    svg = re.sub(
        r'<circle[^>]*r="0\.9"[^>]*/>',
        "",
        svg,
    )
    return svg


def _boxplot_skeleton_overlay(
    svg: str,
    groups,
    palette_name,
    mode: str,
    width: float = 1200,
    height: float = 620,
    margin_l: float = 110,
    margin_r: float = 60,
    margin_t: float = 130,
    margin_b: float = 100,
) -> str:
    """Overlay geometry inside the plot area of an existing boxplot SVG.

    For "notched" and "variable_width" modes we FULLY REPLACE the underlying
    box geometry — the original rects, median lines, whiskers, whisker caps
    and mean markers are stripped from the input SVG before the overlay is
    appended, so the visual result is a single-layer box (no phantom stacked
    box or floating orange median).

    For "beeswarm" and "strip" modes the boxes + jitter dots are stripped
    but whiskers are kept as a subtle reference.

    Margin defaults match the previous hard-coded assumption (title + note).
    Callers should pass the actual `margin_t/margin_b` used by `make_boxplot`
    for the current invocation, otherwise the overlay geometry will be
    misaligned with the original whiskers/axis.
    """
    pal = resolve_palette(palette_name) or {}
    INK = pal.get("ink", "rgba(28,25,20,1)")
    ACC = pal.get("accent", "rgba(163,88,50,1)")
    series = pal.get("series", [ACC])

    W, H = float(width), float(height)
    ML, MR, MT, MB = float(margin_l), float(margin_r), float(margin_t), float(margin_b)
    plot_x, plot_w = ML, W - ML - MR
    plot_y, plot_h = MT, H - MT - MB
    n = len(groups)
    col_w = plot_w / n

    # compute per-group stats & y_min/y_max as make_boxplot does
    all_vals = []
    stats = []
    for name, values in groups:
        xs = sorted(float(v) for v in values)
        q1 = _quantile(xs, 0.25)
        q2 = _quantile(xs, 0.50)
        q3 = _quantile(xs, 0.75)
        iqr = q3 - q1
        lo = max(min(xs), q1 - 1.5 * iqr)
        hi = min(max(xs), q3 + 1.5 * iqr)
        stats.append(dict(name=name, xs=xs, q1=q1, q2=q2, q3=q3, lo=lo, hi=hi, n=len(xs)))
        all_vals.extend(xs)
    d_min, d_max = min(all_vals), max(all_vals)
    span = d_max - d_min
    y_min = d_min - span * 0.1
    y_max = d_max + span * 0.1

    def yof(v):
        return plot_y + (y_max - v) / max(y_max - y_min, 1e-9) * plot_h

    overlays = []

    if mode == "beeswarm":
        # Strip the base boxes (rects with 0.22 alpha fill) and jitter dots
        # (small circles with fill ...,0.35...). Whiskers/median stay visible
        # under our beeswarm dots so we get an academic feel.
        svg = re.sub(
            r'<rect[^>]*fill="rgba\(\d+,\d+,\d+,0\.22\)"[^>]*/>',
            "",
            svg,
        )
        # Also remove jitter dots (fill alpha 0.35 in a rgba(...) fill on circle)
        svg = re.sub(
            r'<circle[^>]*fill="rgba\(\d+,\d+,\d+,0\.35\)"[^>]*/>',
            "",
            svg,
        )
        # beeswarm: bin values, offset alternately along x
        for i, s in enumerate(stats):
            cx = plot_x + col_w * (i + 0.5)
            col = series[i % len(series)]
            # bin height 4px
            bin_h = 5
            # map each val to y; group by y-bucket
            buckets = {}
            for v in s["xs"]:
                py = yof(v)
                bkey = round(py / bin_h)
                buckets.setdefault(bkey, []).append(v)
            r_dot = 2.4
            gap = 5.5
            for bkey, vs in buckets.items():
                py = bkey * bin_h + bin_h / 2
                # alternate offset outwards
                for k, v in enumerate(vs):
                    side = (k // 2) + 1
                    if k == 0:
                        dx = 0
                    else:
                        dx = (gap * side) * (1 if k % 2 else -1)
                    overlays.append(
                        f'<circle cx="{cx + dx:.1f}" cy="{yof(v):.1f}" r="{r_dot}" '
                        f'fill="{_with_alpha(col, 0.72)}" stroke="{_with_alpha(INK, 0.35)}" stroke-width="0.4"/>'
                    )
            # median line
            y_med = yof(s["q2"])
            overlays.append(
                f'<line x1="{cx - 30}" y1="{y_med:.1f}" x2="{cx + 30}" y2="{y_med:.1f}" '
                f'stroke="{INK}" stroke-width="2.0"/>'
            )

    elif mode == "notched":
        # Full replacement: strip baseline box artifacts (rect, median line,
        # whiskers, caps, mean marker, jitter dots) so the notched polygon
        # stands alone. Leave outliers (open ink circles) as a subtle
        # reference.
        svg = _strip_boxplot_body(svg)
        # Redraw box with a notch: use a polygon that pinches at the median.
        for i, s in enumerate(stats):
            cx = plot_x + col_w * (i + 0.5)
            box_w = col_w * 0.36
            col = series[i % len(series)]
            y_q1 = yof(s["q1"])
            y_q2 = yof(s["q2"])
            y_q3 = yof(s["q3"])
            y_lo = yof(s["lo"])
            y_hi = yof(s["hi"])
            notch_dx = box_w * 0.22
            xL, xR = cx - box_w / 2, cx + box_w / 2
            # notch region ±6px around median
            notch_h = min(10, (y_q1 - y_q3) * 0.28)
            y_up = y_q2 - notch_h / 2
            y_dn = y_q2 + notch_h / 2
            # re-draw whiskers (thin) since baseline whiskers were stripped
            overlays.append(
                f'<line x1="{cx:.1f}" y1="{y_hi:.1f}" x2="{cx:.1f}" y2="{y_q3:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            overlays.append(
                f'<line x1="{cx:.1f}" y1="{y_q1:.1f}" x2="{cx:.1f}" y2="{y_lo:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            cap_w = box_w * 0.5
            overlays.append(
                f'<line x1="{cx - cap_w / 2:.1f}" y1="{y_hi:.1f}" '
                f'x2="{cx + cap_w / 2:.1f}" y2="{y_hi:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            overlays.append(
                f'<line x1="{cx - cap_w / 2:.1f}" y1="{y_lo:.1f}" '
                f'x2="{cx + cap_w / 2:.1f}" y2="{y_lo:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            path = (
                f"M {xL:.1f} {y_q3:.1f} L {xR:.1f} {y_q3:.1f} "
                f"L {xR:.1f} {y_up:.1f} L {xR - notch_dx:.1f} {y_q2:.1f} "
                f"L {xR:.1f} {y_dn:.1f} L {xR:.1f} {y_q1:.1f} "
                f"L {xL:.1f} {y_q1:.1f} L {xL:.1f} {y_dn:.1f} "
                f"L {xL + notch_dx:.1f} {y_q2:.1f} L {xL:.1f} {y_up:.1f} Z"
            )
            overlays.append(
                f'<path d="{path}" fill="{_with_alpha(col, 0.18)}" '
                f'stroke="{col}" stroke-width="1.4"/>'
            )
            # median mark inside notch
            overlays.append(
                f'<line x1="{xL + notch_dx:.1f}" y1="{y_q2:.1f}" x2="{xR - notch_dx:.1f}" y2="{y_q2:.1f}" '
                f'stroke="{col}" stroke-width="1.8"/>'
            )

    elif mode == "variable_width":
        # Full replacement: strip baseline box artifacts and re-draw a single
        # rect whose width ∝ √n.
        svg = _strip_boxplot_body(svg)
        ns = [s["n"] for s in stats]
        max_n = max(ns) or 1
        for i, s in enumerate(stats):
            cx = plot_x + col_w * (i + 0.5)
            col = series[i % len(series)]
            factor = math.sqrt(s["n"] / max_n)
            base_w = col_w * 0.44
            w = base_w * (0.35 + 0.65 * factor)
            xL = cx - w / 2
            y_q1 = yof(s["q1"])
            y_q3 = yof(s["q3"])
            y_q2 = yof(s["q2"])
            y_lo = yof(s["lo"])
            y_hi = yof(s["hi"])
            # re-draw whiskers (thin) since baseline whiskers were stripped
            overlays.append(
                f'<line x1="{cx:.1f}" y1="{y_hi:.1f}" x2="{cx:.1f}" y2="{y_q3:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            overlays.append(
                f'<line x1="{cx:.1f}" y1="{y_q1:.1f}" x2="{cx:.1f}" y2="{y_lo:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            cap_w = w * 0.5
            overlays.append(
                f'<line x1="{cx - cap_w / 2:.1f}" y1="{y_hi:.1f}" '
                f'x2="{cx + cap_w / 2:.1f}" y2="{y_hi:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            overlays.append(
                f'<line x1="{cx - cap_w / 2:.1f}" y1="{y_lo:.1f}" '
                f'x2="{cx + cap_w / 2:.1f}" y2="{y_lo:.1f}" '
                f'stroke="{INK}" stroke-width="1.0"/>'
            )
            overlays.append(
                f'<rect x="{xL:.1f}" y="{y_q3:.1f}" width="{w:.1f}" height="{y_q1 - y_q3:.1f}" '
                f'fill="{_with_alpha(col, 0.62)}" stroke="{col}" stroke-width="1.4"/>'
            )
            overlays.append(
                f'<line x1="{xL:.1f}" y1="{y_q2:.1f}" x2="{xL + w:.1f}" y2="{y_q2:.1f}" '
                f'stroke="{INK}" stroke-width="2.0"/>'
            )

    elif mode == "strip":
        # Kill existing boxes + jitter and draw a strip plot: pure vertical
        # dot column jittered ± a few px.
        svg = re.sub(
            r'<rect[^>]*fill="rgba\(\d+,\d+,\d+,0\.22\)"[^>]*/>',
            "",
            svg,
        )
        svg = re.sub(
            r'<circle[^>]*fill="rgba\(\d+,\d+,\d+,0\.35\)"[^>]*/>',
            "",
            svg,
        )
        # keep the whiskers/medians as reference
        import random

        rnd = random.Random(42)
        for i, s in enumerate(stats):
            cx = plot_x + col_w * (i + 0.5)
            col = series[i % len(series)]
            for v in s["xs"]:
                dx = (rnd.random() - 0.5) * col_w * 0.5
                py = yof(v)
                overlays.append(
                    f'<circle cx="{cx + dx:.1f}" cy="{py:.1f}" r="2.1" '
                    f'fill="{_with_alpha(col, 0.75)}" stroke="none"/>'
                )
            # median tick
            y_med = yof(s["q2"])
            overlays.append(
                f'<line x1="{cx - 32}" y1="{y_med:.1f}" x2="{cx + 32}" y2="{y_med:.1f}" '
                f'stroke="{INK}" stroke-width="2.0"/>'
            )

    # append overlays before </svg>
    close = svg.rfind("</svg>")
    return svg[:close] + "".join(overlays) + svg[close:]


def _quantile(sxs, q):
    n = len(sxs)
    if n == 0:
        return 0
    pos = q * (n - 1)
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sxs[lo] * (1 - frac) + sxs[hi] * frac


# -----------------------------------------------------------------------------
# funnel skeleton overrides: rectangle, pipeline_horizontal, stacked_bar, pyramid
# -----------------------------------------------------------------------------


