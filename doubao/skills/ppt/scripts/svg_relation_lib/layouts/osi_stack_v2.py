"""OSI stack v2 layout · hero canvas 1400×720 · J1 reference SVG codified.

Layout for `hero_embed_04_J1_osi_v2` — replaces the embed-only v1 (900×336).
Codifies `final_svg_relation/04_J1_osi/step1_reference/osi_hero_reference.svg`:
  - 7 (flex 3-8) horizontal layer bars · each bar carries: accent bar +
    layer number + short label ("L7") + name ("Application") + purpose caption
    + PDU pill + protocols line + secondary description
  - Left USER-VISIBLE ↕ BITS & SIGNALS axis (with mini arrows)
  - Optional right TCP/IP mapping panel · groups of consecutive OSI layers
  - Optional bottom encapsulation strip (L7→L4→L3→L2 → payload → L2 trailer
    → L1 wire) with SEND↓ / RECEIVE↑ arrows

The layout only computes coordinates. All text styling / colors / marker
plumbing is delegated to the preset.

Data schema (Tree):
    root: TreeNode
      extra:
        axis_top_label:    str   (e.g. "USER-VISIBLE")
        axis_bot_label:    str   (e.g. "BITS & SIGNALS")
        axis_mid_label:    str   (e.g. "abstraction ↓ hardware")
        tcpip_title:       str   (right panel header, e.g. "TCP/IP MAPPING")
        tcpip_groups:      List[dict]  see below · empty list to hide panel
        encap_enabled:     bool
        encap_headline:    str
        encap_frames:      List[dict]  see below
    children: layer TreeNodes · top to bottom (L7 → L1 for OSI)
      label:    layer name (e.g. "Application")
      sublabel: short tag (e.g. "L7")
      group:    hue key (magenta / teal / green / gold / navy / brick / red)
      detail:   purpose (e.g. "User-facing services · what apps talk")
      extra:
        layer_no:  int  (badge number)
        pdu:       str  (e.g. "DATA" / "SEGMENT / DATAGRAM" / "PACKET")
        protocols: str  (e.g. "HTTP · SMTP · DNS · SSH · FTP")
        note:      str  (secondary italic caption)
        tcpip_key: str  (optional · matches tcpip_groups[i]["key"])

tcpip_groups entry:
    {"key": str,       # matches layer.extra["tcpip_key"]
     "label": str,     # panel header (e.g. "APPLICATION")
     "hue": str,       # hue key
     "note": str,      # italic sub (e.g. "TCP/IP · absorbs L5 · L6 · L7")
     "body": List[str] # up to 6 bullet-less lines
    }

encap_frames entry (bottom strip):
    {"kind": "header", "hue": str, "top": str, "mid": str, "bot": str}
    {"kind": "payload", "top": str, "note": str}
    {"kind": "trailer", "hue": str, "top": str, "mid": str, "bot": str}
    {"kind": "wire",   "hue": str, "text": str}
Layout computes x positions from left-to-right in listing order · wire is
special-cased and placed after a "serialize →" arrow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "osi_stack_v2_layout",
    "LayoutOverflow",
    "OSIStackParams",
]


# ─── hero canvas 1400×720 baseline (matches the reference SVG magic nums) ───
CANVAS_W = 1400
CANVAS_H = 720

# body region where the layer bars live
BODY_LEFT = 110       # bar x0
BODY_RIGHT = 900      # bar x1 (bar_w = 790)
BODY_TOP = 156        # first bar y0 (was 164 · shrink 8pt)
BODY_BOT = 500        # last bar y1 for 7 layers (was 552 · shrink 52pt) ·
                       # required to keep encap-strip below · 900×440 slide fit

# right TCP/IP mapping panel
TCPIP_LEFT = 920
TCPIP_RIGHT = 1370
TCPIP_W = TCPIP_RIGHT - TCPIP_LEFT   # 450

# left USER-VISIBLE axis
AXIS_X = 88
AXIS_TOP_Y = 144       # top label (was 150 · shift up)
AXIS_BOT_Y = 510       # bottom label (was 562)
AXIS_LINE_Y0 = 156     # (was 164)
AXIS_LINE_Y1 = 494     # (was 546)

# layer bar geometry
LAYER_H = 52
LAYER_GAP = 4          # row_h = LAYER_H + LAYER_GAP = 56
ACCENT_W = 5           # left colour bar

# per-layer inner columns (measured from the reference SVG)
LN_BADGE_X = 128       # "L7" serif number badge
NAME_X = 152           # layer name
PURPOSE_X = 152        # italic purpose (second line)
# R3-fix (2026-09-14 · atomize collision · round 2):
# 原 PDU_PILL_CX=395 让长 pill (SEGMENT/DATAGRAM w=139.4 → pill_x=325.6) 与
# label 尾字视觉粘连 (SVG-space 80pt gap 在 slide-space 折约 54pt · 用户仍报
# 咬字). 后移 PDU 中心到 445 · L4 pill_x=375.3 · slide-space 后 gap 越 100pt ·
# 与最长 label "Presentation" (12 chars * 10.5 = 126 · end=278) 也保 100pt SVG gap ·
# 保 protocols 从 pill_end+20 起 · 仍在 bar (110-980) 内 fit.
PDU_PILL_CX = 445      # PDU pill horizontal centre (was 395)
PDU_PILL_MIN_W = 58
PDU_PILL_H = 24        # pill height · fits 15pt bold text with breathing room
PROTOCOLS_X = 500      # protocols headline (may shift right if PDU pill wide · R3: 450→500 匹配 PDU_PILL_CX 后移)
PROTOCOLS_MIN_GAP = 20 # gap between right edge of PDU pill and protocols

# encapsulation strip · aggressively compressed (R2 · slide_h=440 safe) ·
# atomize to 900×440 slide (slide_y0=110, canvas 540) with max bottom ≤ 530.
ENCAP_STRIP_Y = 510    # top hairline
ENCAP_HEADLINE_Y = 522
# R3 fix (medium regression M1) · encap headline was overlapping axis_bot label
# on all 4 large slides. axis_bot label sits at SVG x≈72; the English
# "BITS & SIGNALS" at 15pt bold letter-spacing 1.5 extends to SVG x≈210. Encap
# headline used to start at SVG x=60 (= ENCAP_G_TX) which put its left edge
# right on top of the axis label. Shift the headline's SVG x to 232 (16pt
# breathing room past the English label · CN "比特与信号" gets a huge 45pt gap
# — encap frames themselves still start at tx=60 so the nested box row is
# unaffected.
ENCAP_HEADLINE_X = 232
ENCAP_G_TX = 60        # translate x
ENCAP_G_TY = 532       # translate y (top of nested boxes)
ENCAP_HEADER_W = 60    # standard header/trailer width
ENCAP_TRAILER_W = 70   # L2 trailer (FCS) slightly wider
ENCAP_H = 42           # inner box height (was 52 · shrink 10pt)
ENCAP_H_OUTER = 48     # L7 outer envelope height (was 62 · shrink 14pt)
ENCAP_PAYLOAD_W = 240
ENCAP_WIRE_W = 200
ENCAP_WIRE_H = 18      # wire pill height (was 22 · shrink 4pt)
ENCAP_ARROW_W = 70     # serialize arrow gap

# footer notes · baseline ≤ 596 so atomize (900×440 slide) bottom ≤ 530
FOOTER_HAIR_Y = 584
FOOTER_TEXT_Y = 596


class LayoutOverflow(RuntimeError):
    """Raised when the requested data will not fit the canvas."""


@dataclass
class OSIStackParams:
    """Tuneables for the hero OSI stack layout.

    Keep them close to the reference SVG · lifting them out lets the preset
    (or tests) trim the encapsulation strip or shrink the TCP/IP panel.
    """
    canvas_w: float = CANVAS_W
    canvas_h: float = CANVAS_H

    body_left: float = BODY_LEFT
    body_right: float = BODY_RIGHT
    body_top: float = BODY_TOP
    body_bot: float = BODY_BOT

    tcpip_left: float = TCPIP_LEFT
    tcpip_right: float = TCPIP_RIGHT

    axis_x: float = AXIS_X

    layer_h: float = LAYER_H
    layer_gap: float = LAYER_GAP
    accent_w: float = ACCENT_W

    ln_badge_x: float = LN_BADGE_X
    name_x: float = NAME_X
    pdu_pill_cx: float = PDU_PILL_CX
    pdu_pill_min_w: float = PDU_PILL_MIN_W
    pdu_pill_h: float = PDU_PILL_H
    protocols_min_gap: float = PROTOCOLS_MIN_GAP

    tcpip_body_font_size: float = 13.0
    tcpip_body_min_font_size: float = 12.0
    tcpip_body_line_h: float = 16.0

    encap_g_tx: float = ENCAP_G_TX
    encap_g_ty: float = ENCAP_G_TY

    max_layers: int = 8
    min_layers: int = 3


def _iter_layers(tree: Any) -> List[Any]:
    root = getattr(tree, "root", None)
    if root is None:
        return []
    return list(getattr(root, "children", []) or [])


def _root_extra(tree: Any) -> Dict[str, Any]:
    root = getattr(tree, "root", None)
    if root is None:
        return {}
    return dict(getattr(root, "extra", {}) or {})


def _pdu_pill_metrics(text: str, min_w: float) -> Tuple[float, float]:
    """Return compact pill width while keeping PDU/tag text at a uniform size."""
    if not text:
        return min_w, 15.0
    fs = 15.0
    width = _est_text_w(text, fs, bold=True, letter_spacing=0.5, pad=10.0)
    return max(min_w, width), fs


def _est_text_w(
    text: str,
    font_size: float,
    *,
    bold: bool = False,
    letter_spacing: float = 0.0,
    pad: float = 0.0,
) -> float:
    """Approximate SVG text width with the same character classes as atomizer."""
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        cp = ord(ch)
        if cp > 0x2E80:
            total += font_size * 1.05
        elif ch.isspace():
            total += font_size * 0.35
        elif ch in "·×→↑↓←◆◈§":
            total += font_size * 0.7
        elif ch.isupper():
            total += font_size * 0.72
        elif ch.isdigit():
            total += font_size * 0.55
        else:
            total += font_size * 0.58
    if bold:
        total *= 1.04
    if len(text) > 1 and letter_spacing:
        total += (len(text) - 1) * letter_spacing
    return total + pad


def _fit_text_size(
    text: str,
    max_w: float,
    base_size: float,
    min_size: float,
    *,
    bold: bool = False,
    letter_spacing: float = 0.0,
) -> float:
    """Return the largest font size that keeps a single line inside max_w."""
    if not text or max_w <= 0:
        return base_size
    width = _est_text_w(text, base_size, bold=bold, letter_spacing=letter_spacing)
    if width <= max_w:
        return base_size
    scale = max_w / width
    return max(min_size, base_size * scale)


def osi_stack_v2_layout(
    tree: Any,
    *,
    params: Optional[OSIStackParams] = None,
) -> List[Dict[str, Any]]:
    """Compute all positions for the J1 hero OSI stack.

    Returns a list of dicts, each with a ``kind`` discriminator:

        chrome_axis_top / chrome_axis_bot / chrome_axis_mid /
        chrome_axis_line / chrome_axis_arrow_top / chrome_axis_arrow_bot
        chrome_tcpip_hdr / chrome_tcpip_rule
        layer_bar / layer_accent / layer_num / layer_name / layer_purpose
        layer_pdu_pill / layer_pdu_text / layer_protocols / layer_note
        tcpip_group / tcpip_group_accent / tcpip_hdr / tcpip_sub /
        tcpip_body / tcpip_brace
        encap_hairline / encap_headline / encap_arrow_send /
        encap_arrow_recv / encap_serialize
        encap_outer / encap_header / encap_payload / encap_trailer /
        encap_wire / encap_wire_tick / encap_wire_caption
        footer_hair / footer_note
    """
    p = params or OSIStackParams()
    layers = _iter_layers(tree)
    n = len(layers)
    if n < p.min_layers:
        raise LayoutOverflow(
            f"osi_stack expects at least {p.min_layers} layers · got {n}"
        )
    if n > p.max_layers:
        raise LayoutOverflow(
            f"n_layers={n} exceeds max {p.max_layers} · reduce"
        )

    extra = _root_extra(tree)

    # ─── compact mode · triggered when there's neither TCP/IP panel nor encap
    # strip · shrinks the viewBox so a 3-4 layer minimal preset doesn't waste
    # 60% empty space. For TCP/IP or encap variants, keep the fixed layout so
    # atomize (900×440 slide) doesn't distort vertical aspect.
    tcpip_groups_early: List[Dict[str, Any]] = list(
        extra.get("tcpip_groups", []) or []
    )
    encap_enabled_early = bool(extra.get("encap_enabled", True))
    encap_frames_early: List[Dict[str, Any]] = list(
        extra.get("encap_frames", []) or []
    )
    compact = (not tcpip_groups_early) and (
        (not encap_enabled_early) or (not encap_frames_early)
    )

    # ─── vertical fit: compress row height if needed for n > 7 ───
    row_h = p.layer_h + p.layer_gap
    body_h = p.body_bot - p.body_top
    total_h = n * p.layer_h + (n - 1) * p.layer_gap
    if total_h > body_h + 1e-6:
        # shrink layer_h so n rows fit, keeping the same gap
        avail = body_h - (n - 1) * p.layer_gap
        if avail < 30:
            raise LayoutOverflow(
                f"cannot fit {n} layers in body height {body_h:.0f}"
            )
        layer_h = avail / n
        row_h = layer_h + p.layer_gap
    else:
        layer_h = p.layer_h

    body_bot_actual = p.body_top + n * layer_h + (n - 1) * p.layer_gap
    bar_w = p.body_right - p.body_left

    # ─── compact-mode geometry · footer moves up to sit just below axis
    # bottom label; viewBox shrinks so no 260px of dead space remains.
    if compact:
        footer_hair_y = body_bot_actual + 30
        footer_text_y = footer_hair_y + 14
        view_h_effective = footer_text_y + 16     # 16px bottom margin
    else:
        footer_hair_y = FOOTER_HAIR_Y
        footer_text_y = FOOTER_TEXT_Y
        view_h_effective = p.canvas_h

    out: List[Dict[str, Any]] = []

    # emit the effective viewBox height first · preset reads this to set
    # the outer <svg viewBox>. Falls back to canvas_h if absent.
    out.append({
        "kind": "chrome_viewbox",
        "w": p.canvas_w,
        "h": view_h_effective,
        "compact": compact,
    })

    # ═════════════════════════════════════════════════════════════════
    # Left USER-VISIBLE axis
    # ═════════════════════════════════════════════════════════════════
    axis_top_label = str(extra.get("axis_top_label", "USER-VISIBLE"))
    axis_bot_label = str(extra.get("axis_bot_label", "BITS & SIGNALS"))
    axis_mid_label = str(extra.get(
        "axis_mid_label", "abstraction ↓ hardware"
    ))

    out.append({
        "kind": "chrome_axis_top",
        "x": p.body_left - 40,
        "y": AXIS_TOP_Y,
        "text": axis_top_label,
    })
    out.append({
        "kind": "chrome_axis_bot",
        "x": p.body_left - 40,
        "y": body_bot_actual + 16,
        "text": axis_bot_label,
    })
    out.append({
        "kind": "chrome_axis_line",
        "x": p.axis_x,
        "y0": AXIS_LINE_Y0,
        "y1": body_bot_actual - 6,
    })
    out.append({
        "kind": "chrome_axis_arrow_top",
        "x": p.axis_x,
        "y": AXIS_LINE_Y0 + 4,
    })
    out.append({
        "kind": "chrome_axis_arrow_bot",
        "x": p.axis_x,
        "y": body_bot_actual - 10,
    })
    # Skip chrome_axis_mid · after atomize the `transform="rotate(...)"` is
    # stripped and the text lands horizontally on top of the L2/L3 layer bars.
    # The top / bot axis labels already convey the direction · axis mid is
    # ornamental. Keeping the key for backward-compat but not emitting.
    _ = axis_mid_label  # noqa: intentional drop after atomize regression

    # ═════════════════════════════════════════════════════════════════
    # Optional right TCP/IP mapping panel header
    # ═════════════════════════════════════════════════════════════════
    tcpip_groups: List[Dict[str, Any]] = list(extra.get("tcpip_groups", []) or [])
    tcpip_title = str(extra.get("tcpip_title", "TCP/IP MAPPING"))
    if tcpip_groups:
        out.append({
            "kind": "chrome_tcpip_hdr",
            "x": p.tcpip_left,
            "y": AXIS_TOP_Y,
            "text": tcpip_title,
        })
        out.append({
            "kind": "chrome_tcpip_rule",
            "x0": p.tcpip_left,
            "x1": p.tcpip_right,
            "y": AXIS_TOP_Y + 8,
        })

    # ═════════════════════════════════════════════════════════════════
    # 7 layer bars
    # ═════════════════════════════════════════════════════════════════
    bar_x1_for_tcpip = p.body_right if tcpip_groups else p.tcpip_right
    if tcpip_groups:
        # bar width stops before TCP/IP panel gap
        actual_bar_w = p.body_right - p.body_left
    else:
        # give layer bar all the way to right margin - 60
        actual_bar_w = (p.tcpip_right - 60) - p.body_left

    # index → y_top
    ys = [p.body_top + i * (layer_h + p.layer_gap) for i in range(n)]

    # Decide the PDU/tag column once for the whole stack. Short tags share a
    # centerline; if any tag is long, align every tag to the same left edge.
    max_pill_w = p.pdu_pill_min_w
    max_name_end = p.name_x
    for layer in layers:
        name_for_metric = str(getattr(layer, "label", "") or "")
        lex_for_metric = dict(getattr(layer, "extra", {}) or {})
        pdu_for_metric = str(lex_for_metric.get("pdu", "") or "")
        pill_w_for_metric, _ = _pdu_pill_metrics(
            pdu_for_metric, p.pdu_pill_min_w
        )
        name_end_for_metric = p.name_x + _est_text_w(
            name_for_metric, 18.0, bold=True
        )
        max_pill_w = max(max_pill_w, pill_w_for_metric)
        max_name_end = max(max_name_end, name_end_for_metric)

    has_long_pdu = max_pill_w > 132.0
    min_protocols_w = 130.0 if tcpip_groups else 180.0
    max_pdu_left = (
        p.body_right - max_pill_w - p.protocols_min_gap - min_protocols_w
    )
    preferred_left = p.pdu_pill_cx - max_pill_w / 2
    safe_left = max_name_end + 20.0
    if has_long_pdu:
        pdu_column_left = min(max(preferred_left, safe_left), max_pdu_left)
        pdu_column_left = max(p.name_x + 90.0, pdu_column_left)
        pdu_column_cx = pdu_column_left + max_pill_w / 2
    else:
        preferred_cx = max(p.pdu_pill_cx, safe_left + max_pill_w / 2)
        max_cx = max_pdu_left + max_pill_w / 2
        pdu_column_cx = min(preferred_cx, max_cx)
        pdu_column_left = pdu_column_cx - max_pill_w / 2

    # gather per-layer PDU widths so protocols x is consistent
    for i, layer in enumerate(layers):
        y = ys[i]
        hue = str(getattr(layer, "group", "") or "rust")
        name = str(getattr(layer, "label", "") or "")
        short = str(getattr(layer, "sublabel", "") or "")
        purpose = str(getattr(layer, "detail", "") or "")
        lex = dict(getattr(layer, "extra", {}) or {})
        layer_no = lex.get("layer_no", n - i)
        pdu = str(lex.get("pdu", "") or "")
        protocols = str(lex.get("protocols", "") or "")
        note = str(lex.get("note", "") or "")
        tcpip_key = str(lex.get("tcpip_key", "") or "")

        # bar body
        out.append({
            "kind": "layer_bar",
            "x": p.body_left,
            "y": y,
            "w": actual_bar_w,
            "h": layer_h,
            "hue": hue,
            "index": i,
        })
        # left accent slab
        out.append({
            "kind": "layer_accent",
            "x": p.body_left,
            "y": y,
            "w": p.accent_w,
            "h": layer_h,
            "hue": hue,
        })
        # number badge (serif "L7") — baseline y = layer top + 24
        # top-row baseline (name / badge / protocols / PDU text) sits at 24/52 ·
        # bottom-row baseline (purpose / note) at layer_h - 8/52.  Values bumped
        # from (20, 14) to (24, 8) so preset font-size ≥ 15 fits inside bar.
        if layer_h < 44:
            top_y = y + 24 * (layer_h / 52.0)
            bot_y = y + layer_h - layer_h * 0.155
        else:
            top_y = y + 24
            bot_y = y + layer_h - 8
        pill_top_y = y + max(6.0, layer_h * 0.23)
        pill_h = min(p.pdu_pill_h, layer_h - 12)

        out.append({
            "kind": "layer_num",
            "x": p.ln_badge_x,
            "y": top_y,
            "text": f"L{layer_no}",
            "hue": hue,
        })
        # name label
        out.append({
            "kind": "layer_name",
            "x": p.name_x,
            "y": top_y,
            "text": name,
            "hue": hue,
            "short": short,
        })
        # purpose (italic, second row)
        if purpose:
            out.append({
                "kind": "layer_purpose",
                "x": p.name_x,
                "y": bot_y,
                "text": purpose,
            })
        # PDU pill/tag column
        pill_w, pdu_fs = _pdu_pill_metrics(pdu, p.pdu_pill_min_w)
        if has_long_pdu:
            pill_x = pdu_column_left
        else:
            pill_x = pdu_column_cx - pill_w / 2
        pill_y = pill_top_y
        if pdu:
            out.append({
                "kind": "layer_pdu_pill",
                "x": pill_x,
                "y": pill_y,
                "w": pill_w,
                "h": pill_h,
                "hue": hue,
            })
            out.append({
                "kind": "layer_pdu_text",
                "cx": pill_x + pill_w / 2,   # R3-fix: 跟随 pill 实际位置 · 避免 shift 后 text 脱出 pill
                "x": pill_x + pill_w / 2,
                "cy": pill_y + pill_h / 2 + 3.5,
                "text": pdu,
                "hue": hue,
                "anchor": "middle",
                "font_size": pdu_fs,
            })
            protocols_x = max(
                PROTOCOLS_X,
                pill_x + pill_w + p.protocols_min_gap,
            )
        else:
            protocols_x = PROTOCOLS_X

        # protocols line
        if protocols:
            protocols_max_w = max(80.0, p.body_right - protocols_x - 14.0)
            protocols_fs = _fit_text_size(
                protocols, protocols_max_w, 17.0, 13.0, bold=True
            )
            out.append({
                "kind": "layer_protocols",
                "x": protocols_x,
                "y": top_y,
                "text": protocols,
                "font_size": protocols_fs,
                "max_w": protocols_max_w,
            })
        # note (italic caption)
        if note:
            out.append({
                "kind": "layer_note",
                "x": protocols_x,
                "y": bot_y,
                "text": note,
            })

    # ═════════════════════════════════════════════════════════════════
    # Optional TCP/IP mapping panel body (packs groups of consecutive layers)
    # ═════════════════════════════════════════════════════════════════
    if tcpip_groups:
        skip_kinds = {str(k) for k in (extra.get("skip_kinds", []) or [])}
        # build map: tcpip_key → indices of matching layers
        layer_indices_by_key: Dict[str, List[int]] = {}
        for i, layer in enumerate(layers):
            lex = dict(getattr(layer, "extra", {}) or {})
            k = str(lex.get("tcpip_key", "") or "")
            if not k:
                continue
            layer_indices_by_key.setdefault(k, []).append(i)

        for gi, grp in enumerate(tcpip_groups):
            key = str(grp.get("key", "") or "")
            label = str(grp.get("label", "") or "")
            g_hue = str(grp.get("hue", "") or "rust")
            g_note = str(grp.get("note", "") or "")
            g_body = list(grp.get("body", []) or [])

            idxs = layer_indices_by_key.get(key, [])
            if not idxs:
                # fall back: default to nth OSI layer
                continue

            y_top = ys[min(idxs)]
            y_bot = ys[max(idxs)] + layer_h
            grp_h = y_bot - y_top

            out.append({
                "kind": "tcpip_group",
                "x": p.tcpip_left,
                "y": y_top,
                "w": p.tcpip_right - p.tcpip_left,
                "h": grp_h,
                "hue": g_hue,
                "index": gi,
            })
            out.append({
                "kind": "tcpip_group_accent",
                "x": p.tcpip_left,
                "y": y_top,
                "w": p.accent_w,
                "h": grp_h,
                "hue": g_hue,
            })
            out.append({
                "kind": "tcpip_hdr",
                "x": p.tcpip_left + 18,
                "y": y_top + 20,
                "text": label,
                "hue": g_hue,
            })
            row_y = y_top + 36
            if g_note and "tcpip_sub" not in skip_kinds:
                out.append({
                    "kind": "tcpip_sub",
                    "x": p.tcpip_left + 18,
                    "y": row_y,
                    "text": g_note,
                })
                row_y += 18
            # body: up to 6 lines · fit per line inside the widened panel
            body_x = p.tcpip_left + 18
            body_max_w = max(80.0, p.tcpip_right - body_x - 16)
            for bi, bt in enumerate(g_body[:6]):
                body_text = str(bt)
                body_fs = _fit_text_size(
                    body_text,
                    body_max_w,
                    p.tcpip_body_font_size,
                    p.tcpip_body_min_font_size,
                    bold=(bi == 0),
                )
                out.append({
                    "kind": "tcpip_body",
                    "x": body_x,
                    "y": row_y + bi * p.tcpip_body_line_h,
                    "text": body_text,
                    "index": bi,
                    "font_size": body_fs,
                    "max_w": body_max_w,
                })
            # bracket from OSI right edge to panel accent (bridges group)
            out.append({
                "kind": "tcpip_brace",
                "x_from": p.body_right + 5,
                "x_to": p.tcpip_left - 2,
                "y_top": y_top + 26,
                "y_bot": y_bot - 26,
                "hue": g_hue,
            })

    # ═════════════════════════════════════════════════════════════════
    # Bottom encapsulation strip
    # ═════════════════════════════════════════════════════════════════
    encap_enabled = bool(extra.get("encap_enabled", True))
    encap_frames = list(extra.get("encap_frames", []) or [])
    if encap_enabled and encap_frames:
        _emit_encap(out, extra, p, encap_frames)

    # ═════════════════════════════════════════════════════════════════
    # Footer notes
    # ═════════════════════════════════════════════════════════════════
    footer_note = str(extra.get("footer_note", "") or "")
    if footer_note:
        out.append({
            "kind": "footer_hair",
            "x0": p.encap_g_tx,
            "x1": p.canvas_w - p.encap_g_tx,
            "y": footer_hair_y,
        })
        out.append({
            "kind": "footer_note",
            "x": p.encap_g_tx,
            "y": footer_text_y,
            "text": footer_note,
        })

    return out


def _emit_encap(out: List[Dict[str, Any]],
                extra: Dict[str, Any],
                p: OSIStackParams,
                frames: List[Dict[str, Any]]) -> None:
    """Emit encapsulation strip · left→right packed frames + arrows."""
    tx = p.encap_g_tx
    ty = p.encap_g_ty

    # hairline + headline
    out.append({
        "kind": "encap_hairline",
        "x0": tx,
        "x1": p.canvas_w - tx,
        "y": ENCAP_STRIP_Y,
    })
    headline = str(extra.get(
        "encap_headline",
        "ENCAPSULATION · a packet gains a header at each layer going "
        "down, sheds one going up",
    ))
    out.append({
        "kind": "encap_headline",
        "x": ENCAP_HEADLINE_X,
        "y": ENCAP_HEADLINE_Y,
        "text": headline,
    })

    # ── pack frames left → right ──
    # each frame becomes a positioned dict; wire has an extra serialize arrow
    # nested-box row occupies y ∈ [6, 66] (inner) with outer L7 at y ∈ [0, 72]
    slots: List[Dict[str, Any]] = []
    cur_x = 0.0
    for fi, fr in enumerate(frames):
        kind = fr.get("kind")
        if kind == "header" or kind == "trailer":
            w = (ENCAP_TRAILER_W if kind == "trailer" else ENCAP_HEADER_W)
            slots.append({
                "fi": fi, "kind": kind, "x": cur_x, "w": w,
                "hue": str(fr.get("hue", "") or "brick"),
                "top": fr.get("top", ""),
                "mid": fr.get("mid", ""),
                "bot": fr.get("bot", ""),
            })
            cur_x += w + 10
        elif kind == "payload":
            slots.append({
                "fi": fi, "kind": kind, "x": cur_x, "w": ENCAP_PAYLOAD_W,
                "top": fr.get("top", ""),
                "note": fr.get("note", ""),
            })
            cur_x += ENCAP_PAYLOAD_W + 10
        elif kind == "wire":
            # serialize arrow occupies 70px slot, then wire block
            arrow_x0 = cur_x
            arrow_x1 = cur_x + ENCAP_ARROW_W
            cur_x = arrow_x1 + 10
            slots.append({
                "fi": fi, "kind": "wire", "x": cur_x, "w": ENCAP_WIRE_W,
                "hue": str(fr.get("hue", "") or "red"),
                "text": fr.get("text", ""),
                "arrow_x0": arrow_x0,
                "arrow_x1": arrow_x1,
            })
            cur_x += ENCAP_WIRE_W + 10

    # ── outer L7 envelope covers headers + payload + trailer (pre-wire) ──
    pre_wire_slots = [s for s in slots if s["kind"] != "wire"]
    if pre_wire_slots:
        outer_x0 = pre_wire_slots[0]["x"]
        outer_x1 = max(s["x"] + s["w"] for s in pre_wire_slots)
        # use first header's hue for the outer envelope
        first_header = next((s for s in slots if s["kind"] == "header"), None)
        outer_hue = first_header["hue"] if first_header else "purple"
        out.append({
            "kind": "encap_outer",
            "x": tx + outer_x0,
            "y": ty,
            "w": outer_x1 - outer_x0,
            "h": ENCAP_H_OUTER,
            "hue": outer_hue,
        })

    # ── emit each slot ──
    first_header_emitted = False
    for s in slots:
        gx = tx + s["x"]
        if s["kind"] == "header":
            # first header sits inside outer L7 envelope (h=72) · rest at y+6
            if not first_header_emitted:
                y_top = ty
                h = ENCAP_H_OUTER
                first_header_emitted = True
            else:
                y_top = ty + 6
                h = ENCAP_H
            out.append({
                "kind": "encap_header",
                "x": gx, "y": y_top, "w": s["w"], "h": h,
                "hue": s["hue"],
                "top": s["top"], "mid": s["mid"], "bot": s["bot"],
            })
        elif s["kind"] == "trailer":
            out.append({
                "kind": "encap_trailer",
                "x": gx, "y": ty + 6, "w": s["w"], "h": ENCAP_H,
                "hue": s["hue"],
                "top": s["top"], "mid": s["mid"], "bot": s["bot"],
            })
        elif s["kind"] == "payload":
            out.append({
                "kind": "encap_payload",
                "x": gx, "y": ty + 6, "w": s["w"], "h": ENCAP_H,
                "top": s["top"], "note": s["note"],
            })
        elif s["kind"] == "wire":
            out.append({
                "kind": "encap_serialize",
                "x0": tx + s["arrow_x0"],
                "x1": tx + s["arrow_x1"],
                "y": ty + 36,
            })
            out.append({
                "kind": "encap_wire",
                "x": gx, "y": ty + 24, "w": s["w"], "h": ENCAP_WIRE_H,
                "hue": s["hue"], "text": s["text"],
            })
            # 11 evenly spaced ticks under wire
            for ti in range(11):
                tick_x = gx + 16 + ti * 16
                if tick_x < gx + s["w"] - 10:
                    out.append({
                        "kind": "encap_wire_tick",
                        "x": tick_x,
                        "y0": ty + 24 + ENCAP_WIRE_H + 4,
                        "y1": ty + 24 + ENCAP_WIRE_H + 4 + (
                            4 + (ti % 3) * 2
                        ),
                        "hue": s["hue"],
                    })

    # ── SEND / RECEIVE annotations to the right (legend chatter removed) ──
    if slots:
        right_edge = max(s["x"] + s["w"] for s in slots)
        arr_x0 = tx + right_edge + 20
        arr_x1 = tx + right_edge + 260
        send_text = str(extra.get(
            "encap_arrow_send_text",
            "SEND · encapsulate down · L7 → L1",
        ))
        recv_text = str(extra.get(
            "encap_arrow_recv_text",
            "RECEIVE · decapsulate up · L1 → L7",
        ))
        out.append({
            "kind": "encap_arrow_send",
            "x0": arr_x0, "x1": arr_x1, "y": ty - 2,
            "text": send_text,
        })
        out.append({
            "kind": "encap_arrow_recv",
            "x0": arr_x1, "x1": arr_x0,
            "y": ty + ENCAP_H_OUTER + 2,
            "text": recv_text,
        })
