"""Bloom pyramid v2 layout · hero canvas 1400×720 · stepped pyramid.

Redesigned for hero canvas 1400×720 · matches step1 reference (`bloom_hero_reference.svg`):
    - **stepped horizontal band pyramid** · bottom widest, top narrowest
    - each tier: hue-tinted rect + left hue bar + Ln id + CN name (serif) + EN name +
      italic verbs + right-aligned example + optional progress bar + %
    - left rotated axis rail "HIGHER-ORDER COGNITIVE DEMAND" with arrow at top
    - optional right sidebar (TIER MASTERY / ACTION VERBS / HOW TO READ)
    - optional MASTERY CLIFF callout pinned to a specific tier (auto-computed
      as max-drop tier if not provided)

Elasticity:
    * n_tiers ∈ [3, 7]  · tier_h and stepped indent adapt via _LEVELS
    * CN name / EN name / verbs / example / mastery_pct all optional per tier
    * sidebar toggles on/off via has_sidebar flag → pyramid_right shifts to consume space
    * KPI band toggles on/off (rendered by preset)
    * callout auto-picks max-drop tier when data.callout is None

Output kinds:
    tier_rect      · one tier band · x/y/w/h + hue + index + tier_num
    tier_shadow    · drop-shadow rect (0.05 alpha · 2px offset)
    tier_hue_bar   · left 6px hue bar
    tier_id        · "L1..Ln" small caps · hue-colored
    tier_cn        · CN name (serif 24) · aligned bottom-left
    tier_en        · EN caps (Inter bold 13) · hue-colored
    tier_verbs     · italic verbs · slate
    tier_example   · right-aligned example · dark ink
    tier_bar_bg    · progress bar background (hue @ 0.22)
    tier_bar_fill  · progress bar fill (hue @ 0.92)
    tier_pct       · "%" text · hue-colored serif
    axis_line      · left rotated axis · line + arrow + end dot
    axis_arrow     · small triangle at top
    axis_dot       · circle at bottom
    axis_label     · rotated "HIGHER-ORDER COGNITIVE DEMAND"
    axis_top_tag   · "CREATE" small label near top
    axis_bot_tag   · "REMEMBER" small label near bottom
    callout_rect   · MASTERY CLIFF box
    callout_kicker · MASTERY CLIFF kicker
    callout_line   · italic "L4 → L5 drops 13pt"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["bloom_v2_layout", "LayoutOverflow", "BloomParams"]


class LayoutOverflow(RuntimeError):
    pass


# ─── density levels · pick by n_tiers ───
# (max_n_tiers, tier_h, tier_gap, step_indent)
# tier_h calibrated so vertical content (id top / EN mid / verbs+bar bottom)
# stays roughly 6-10px shy of tier bottom · no more "empty 30px vertical slack".
# ref: n=6 uses tier_h=60 → content y_top+18..y_top+52 · 8px trail padding
_LEVELS: List[Tuple[int, float, float, float]] = [
    (3, 72.0, 8.0, 84.0),
    (4, 68.0, 7.0, 72.0),
    (5, 64.0, 6.0, 62.0),
    (6, 60.0, 5.0, 56.0),
    (7, 50.0, 3.0, 48.0),
]


@dataclass
class BloomParams:
    # canvas · hero 1400×720
    canvas_w: float = 1400.0
    canvas_h: float = 720.0

    # pyramid geometry
    # pyramid_x_right = 1040 matches step1 reference exactly. The callout lives
    # in the right gutter x=1046..1196 (150w × 48h) which visually overlaps the
    # sidebar's LABEL column (sidebar_x=1140) — this matches the reference
    # layout where the callout sits BESIDE a sidebar row rather than in a
    # completely disjoint gutter. Sidebar bars start at x=1210 so callout
    # doesn't touch them.
    pyramid_x_right: float = 1040.0       # right edge of every tier (shared)
    # no-sidebar mode: consume the space normally reserved for the right
    # sidebar. The default renderer subtracts the sidebar in compact slide
    # decks, so the pyramid itself must extend close to the right chrome.
    pyramid_x_right_no_sidebar: float = 1280.0
    pyramid_bot_y: float = 574.0         # bottom row y1 (L1 bottom)
    pyramid_top_y_min: float = 180.0     # top row y0 hard floor
    # when KPI band is absent (minimal), pyramid may start higher
    pyramid_top_y_min_no_kpi: float = 130.0
    hue_bar_w: float = 6.0
    tier_shadow_dx: float = 2.0
    tier_shadow_dy: float = 2.0

    # left axis
    axis_x: float = 76.0
    axis_arrow_dy: float = 8.0
    axis_bot_dot_r: float = 3.0
    axis_top_tag_dy: float = 6.0       # arrow tip → tag baseline
    axis_bot_tag_dy: float = 4.0

    # tier text pads (relative to tier x = tier_right - tier_w)
    #
    # LAYOUT COLUMN MODEL (fix 2026-09-13 bl_bloom TIER label overlap bug):
    #   [hue_bar 0..6] [ID_COL 22..22+tier_id_col_w] [gap] [CN_COL] [EN_COL 102+]
    # tier_id lives in ID_COL (independent left column · reserved regardless of
    # its text content). CN name starts at (id_pad_x + tier_id_col_w + gap) so
    # it can NEVER overlap tier_id horizontally · no matter what CJK glyphs
    # the caller passes.
    #
    # Sizing rationale:
    #   tier_id_col_w default 60 accommodates up to ~7 chars ("TIER · 05")
    #   at 15pt sans + 0.18em letter-spacing (7 * 15 * 1.18 ≈ 124px BUT most
    #   callers use short "L1..L5" ≈ 35px). 60 gives room for medium labels
    #   like "T-01 CORE" (8 chars slimmer glyphs). Callers wanting long ids
    #   ("TIER MASTERY 05") should pass tier_id_col_w=90 explicitly.
    id_pad_x: float = 22.0
    id_pad_y_top: float = 18.0         # from tier y_top
    tier_id_col_w: float = 60.0        # reserved column width for tier_id
    tier_id_col_gap: float = 6.0       # gap between id column and CN column
    cn_pad_x: float = 22.0             # CN name (serif) · legacy · overridden
                                       # when id column would collide (see below)
    cn_pad_y_bot: float = 14.0         # from tier y_bot (so cn hugs bottom baseline)
    en_pad_x: float = 102.0
    en_pad_y_top_ratio: float = 0.56   # en baseline y in tier
    verbs_pad_y_top_ratio: float = 0.86
    tier_subtitle_gap: float = 18.0    # fixed gap between tier title and subtitle
    tier_guide_gap: float = 18.0       # subtitle end -> pale guide line
    tier_guide_right_pad: float = 20.0
    tier_guide_min_w: float = 46.0

    # progress bar (only when mastery_pct given)
    bar_w: float = 130.0
    bar_h: float = 8.0
    bar_right_pad: float = 44.0        # bar right edge relative to tier right
    example_right_pad: float = 16.0    # example right edge relative to tier right
    pct_right_pad: float = 16.0        # pct right edge

    # sidebar (when has_sidebar)
    sidebar_x: float = 1140.0
    sidebar_w: float = 190.0
    # sidebar TIER MASTERY panel geometry (used for callout Y-collision check):
    # panel title at panel_y=200; first tier row at panel_y+22=222; each row +24.
    # The text label at each row baseline y sits at (sidebar_row_y-8, sidebar_row_y+4)
    # visually (font-size=10 · sits above y baseline). Rows are indexed top-tier
    # (Ln) first descending to L1 in sidebar.
    sidebar_panel_y: float = 200.0
    sidebar_row_dy: float = 24.0
    sidebar_row_first_offset: float = 22.0  # first row y = panel_y + 22

    # callout · positioned in right gutter beyond pyramid_x_right (matches ref)
    # geometry: callout_x=1046 (=pyramid_x_right+6), right=1196
    # The right gutter overlaps sidebar_x=1140 label column · we DO NOT want
    # the callout rect to visually cover a sidebar text label. Y-collision
    # check below shrinks callout_w when necessary.
    callout_x: float = 1046.0
    callout_w: float = 150.0
    callout_h: float = 48.0
    # sidebar collision guards
    #   callout_sidebar_gap : horizontal net-space required between callout
    #                        right edge and sidebar_x when Y-collision detected.
    #   callout_bar_x       : sidebar BAR column start x (hard collision line
    #                        even without Y-overlap · used as absolute right cap).
    callout_sidebar_gap: float = 4.0
    callout_bar_x: float = 1210.0        # sidebar bar start x — hard collision line
    # minimum width required for callout to render in right-gutter position
    callout_min_gutter_w: float = 150.0
    # minimum vertical gap required to place callout in KPI→pyramid top space
    callout_top_gap_min: float = 60.0
    # when placing callout in top_gap, sit it just above pyramid top by this
    # much (visually "attaches" the callout to the pyramid rather than
    # floating in the gap center).
    callout_top_gap_attach_offset: float = 12.0

    # CN name (serif) horizontal padding
    # cn_pad_x (=22px) is the LEGACY value. The runtime path computes an
    # effective cn_x that respects the tier_id reserved column:
    #   cn_x = max(cn_pad_x, id_pad_x + tier_id_col_w + tier_id_col_gap)
    # so CN name never collides with tier_id regardless of what CJK text
    # the caller passes.
    # When tier bars grow very short (n=7, tier_h=50), tier_id (top) and CN (bottom)
    # end up vertically close. We also shrink CN font size and push it further
    # right so it reads as a distinct name-plate.
    cn_dynamic_tier_h_threshold: float = 55.0
    cn_font_size: float = 24.0
    cn_squeeze_font_size: float = 20.0
    cn_squeeze_pad_x: float = 44.0
    # legacy fields kept for backward compat (unused in new logic)
    cn_dynamic_min: float = 80.0
    cn_dynamic_ratio: float = 0.08

    min_tiers: int = 3
    max_tiers: int = 7


def _iter_tiers(tree: Any) -> List[Any]:
    root = getattr(tree, "root", None)
    if root is None:
        return []
    out: List[Any] = []
    cur = root
    while True:
        kids = list(getattr(cur, "children", []) or [])
        if not kids:
            break
        out.append(kids[0])
        cur = kids[0]
    return out


def _pick_level(n: int) -> Tuple[float, float, float]:
    for max_n, th, tg, si in _LEVELS:
        if n <= max_n:
            return th, tg, si
    raise LayoutOverflow(f"n_tiers={n} > {_LEVELS[-1][0]}")


def _estimate_text_width(text: str, font_size: float, *, letter_spacing_em: float = 0.0) -> float:
    """Estimate SVG text width using the atomizer's conservative glyph model."""
    width = 0.0
    for ch in text:
        if ord(ch) > 0x2E80:
            width += font_size * 1.05
        elif ch.isspace():
            width += font_size * 0.35
        elif ch in "·×→↑↓←◆◈§":
            width += font_size * 0.70
        elif ch.isupper():
            width += font_size * 0.72
        elif ch.isdigit():
            width += font_size * 0.55
        else:
            width += font_size * 0.58
    if len(text) > 1 and letter_spacing_em:
        width += (len(text) - 1) * font_size * letter_spacing_em
    return width


def bloom_v2_layout(
    tree: Any,
    *,
    params: Optional[BloomParams] = None,
    has_sidebar: bool = True,
    has_kpi_band: bool = True,
) -> List[Dict[str, Any]]:
    """Bloom hero pyramid layout · returns positions list.

    Parameters
    ----------
    tree : Tree schema; root → L1 → L2 → ... → Ln (single chain).
        tiers[0] = L1 (bottom, widest); tiers[-1] = Ln (top, narrowest).
        Each tier TreeNode carries:
          label       = CN name (e.g. "记忆")
          sublabel    = EN name (e.g. "REMEMBER")
          detail      = verbs italic text
          group       = hue key
          extra["example"] = right-side example
          extra["mastery_pct"] = 0..100 (optional)
        Tree.extra["callout"] = {"tier_num": int, "text": str, "kicker": str}
            or None to auto-detect max-drop tier
        Tree.extra["axis_label"] = axis text (default HIGHER-ORDER COGNITIVE DEMAND)
        Tree.extra["axis_top_tag"] / ["axis_bot_tag"] = short caps
    has_sidebar : bool · when False, pyramid extends to pyramid_x_right_no_sidebar

    Returns
    -------
    List[dict] · kinds enumerated in module docstring.
    """
    p = params or BloomParams()
    tiers = _iter_tiers(tree)
    n = len(tiers)
    if n < p.min_tiers:
        raise LayoutOverflow(f"n_tiers={n} < min {p.min_tiers}")
    if n > p.max_tiers:
        raise LayoutOverflow(f"n_tiers={n} > max {p.max_tiers}")

    tier_h, tier_gap, step_indent = _pick_level(n)

    x_right = p.pyramid_x_right if has_sidebar else p.pyramid_x_right_no_sidebar
    step = tier_h + tier_gap
    # when KPI band is absent, shift the whole pyramid up ~40px so the KPI
    # dead-zone (y=110..190) doesn't yawn as empty space above the tiers
    y_bot = p.pyramid_bot_y if has_kpi_band else (p.pyramid_bot_y - 30.0)

    # when KPI band is absent, allow pyramid to reach higher (frees ~50px)
    top_floor = p.pyramid_top_y_min if has_kpi_band else p.pyramid_top_y_min_no_kpi

    # ── content-density adaptive width ──
    # scan tiers · if NO tier has an example AND no tier has mastery_pct,
    # tiers have no right-column content · shrink pyramid width so we don't
    # end up with a huge empty right band (test3 minimal mode).
    _has_any_example = False
    _has_any_pct = False
    for _t in tiers:
        _extra = getattr(_t, "extra", {}) or {}
        if str(_extra.get("example", "") or "").strip():
            _has_any_example = True
        if _extra.get("mastery_pct") is not None:
            _has_any_pct = True
    if not _has_any_example and not _has_any_pct:
        # In minimal mode (no example / no pct), the pyramid has no right-column
        # content so it can safely extend further right without crowding. The
        # baseline cap (1040 for sidebar, 1120 no-sidebar) leaves a large empty
        # band (940..1140 = 200px void in test3) which reads as visual noise.
        # Step-3e flagged this as "test3 空场 · 200px 空". Extend the pyramid
        # right edge closer to the sidebar column:
        #   - has_sidebar: extend to 1100 (sidebar_x=1140 − 40 gutter), so
        #     tier bars fill more canvas. Only expands (never shrinks) since
        #     minimal content already occupies < 1040.
        #   - no sidebar: 1220 (canvas_right 1330 − 110 margin) so pyramid
        #     spans much of the canvas.
        _minimal_target = 1100.0 if has_sidebar else 1220.0
        # Only apply if it EXTENDS x_right (never shrink the pyramid below its
        # normal footprint · a data-driven pyramid still wants normal width).
        x_right = max(x_right, _minimal_target)

    # widest tier (L1, i=0) width so its left edge ≥ axis + a margin
    # widest_left = 138 in reference (76+62). Use axis_x + 62 as left minimum.
    widest_left_min = p.axis_x + 62.0
    max_tier_w = x_right - widest_left_min

    # narrowest tier (Ln) still needs enough px to hold "L{n} · CN · EN · verbs"
    # In minimal mode (no example / no pct, often no CN) 260px is enough.
    _minimal_mode = not _has_any_example and not _has_any_pct
    min_tier_w = 260.0 if _minimal_mode else 360.0
    if max_tier_w - (n - 1) * step_indent < min_tier_w:
        # 挤到底: compress step_indent
        step_indent = max(20.0, (max_tier_w - min_tier_w) / max(n - 1, 1))

    # compute tier y_top ranges (i=0 is bottom)
    top_y_ln = y_bot - tier_h - (n - 1) * step
    if top_y_ln < top_floor:
        raise LayoutOverflow(
            f"pyramid too tall for n={n} · top_y={top_y_ln:.0f} < min {top_floor}"
        )

    out: List[Dict[str, Any]] = []

    # ── LEFT AXIS ──
    tree_extra = getattr(tree, "extra", None) or {}
    if not isinstance(tree_extra, dict):
        tree_extra = {}
    axis_label = tree_extra.get("axis_label", "HIGHER-ORDER  COGNITIVE  DEMAND")
    axis_top_tag = tree_extra.get("axis_top_tag", "CREATE")
    axis_bot_tag = tree_extra.get("axis_bot_tag", "REMEMBER")

    axis_y_top = top_y_ln + 8.0       # slightly below top tier top
    axis_y_bot = y_bot + 6.0
    out.append({
        "kind": "axis_line",
        "x": p.axis_x,
        "y1": axis_y_top,
        "y2": axis_y_bot,
    })
    out.append({
        "kind": "axis_arrow",
        "x": p.axis_x,
        "y": axis_y_top,
        "dy": p.axis_arrow_dy,
    })
    out.append({
        "kind": "axis_dot",
        "cx": p.axis_x,
        "cy": axis_y_bot,
        "r": p.axis_bot_dot_r,
    })
    out.append({
        "kind": "axis_label",
        "cx": p.axis_x - 16.0,
        "cy": (axis_y_top + axis_y_bot) / 2,
        "text": axis_label,
        "rotate": -90,
    })
    out.append({
        "kind": "axis_top_tag",
        "x": p.axis_x + 10.0,
        "y": axis_y_top + p.axis_top_tag_dy,
        "text": axis_top_tag,
    })
    out.append({
        "kind": "axis_bot_tag",
        "x": p.axis_x + 10.0,
        "y": axis_y_bot + p.axis_bot_tag_dy,
        "text": axis_bot_tag,
    })

    # ── TIERS ──
    tier_positions: List[Dict[str, Any]] = []
    for i, tier in enumerate(tiers):
        w = max_tier_w - i * step_indent
        w = max(w, min_tier_w)
        # y_top for tier index i (i=0 is bottom):
        y_top = y_bot - tier_h - i * step
        x_left = x_right - w
        cy = y_top + tier_h / 2

        hue = str(getattr(tier, "group", "") or "rust")
        cn_name = str(getattr(tier, "label", "") or "")
        en_name = str(getattr(tier, "sublabel", "") or "")
        verbs = str(getattr(tier, "detail", "") or "")
        extra = getattr(tier, "extra", {}) or {}
        example = str(extra.get("example", "") or "")
        pct_raw = extra.get("mastery_pct")
        try:
            pct = float(pct_raw) if pct_raw is not None else None
        except (TypeError, ValueError):
            pct = None

        tier_num = i + 1

        # drop shadow (very subtle)
        out.append({
            "kind": "tier_shadow",
            "x": x_left + p.tier_shadow_dx,
            "y": y_top + p.tier_shadow_dy,
            "w": w,
            "h": tier_h,
        })
        # main rect
        out.append({
            "kind": "tier_rect",
            "x": x_left, "y": y_top, "w": w, "h": tier_h,
            "hue": hue, "index": i, "tier_num": tier_num,
        })
        # left hue bar
        out.append({
            "kind": "tier_hue_bar",
            "x": x_left, "y": y_top,
            "w": p.hue_bar_w, "h": tier_h,
            "hue": hue,
        })
        # tier id (L1..Ln) small caps
        out.append({
            "kind": "tier_id",
            "x": x_left + p.id_pad_x,
            "y": y_top + p.id_pad_y_top,
            "text": f"L{tier_num}",
            "hue": hue,
        })
        # CN name bottom-left
        # ROOT-CAUSE FIX (2026-09-13): tier_id lives in a reserved ID_COL
        # [id_pad_x .. id_pad_x + tier_id_col_w]. CN name MUST start at
        # least `tier_id_col_gap` past ID_COL right edge so it never
        # collides with tier_id horizontally regardless of caller's CN
        # text length or the id text length ("L1" vs "TIER · 05").
        # Vertical stacking (tier_id top, CN bottom) still leaves them in
        # the same visual "left-plate" band, but the reserved horizontal
        # gutter guarantees each glyph column is legible.
        #
        # Squeezed mode (tier_h < threshold, e.g. n=7):
        #   - shrink CN font size (still ≥ hard red line 15pt SVG-space)
        #   - push CN further right (cn_squeeze_pad_x) for extra breathing
        # In both modes the ID_COL reservation is enforced as a floor.
        cn_squeezed = tier_h < p.cn_dynamic_tier_h_threshold
        cn_fs = p.cn_squeeze_font_size if cn_squeezed else p.cn_font_size
        cn_dx_requested = p.cn_squeeze_pad_x if cn_squeezed else p.cn_pad_x
        # enforce ID column reservation floor
        cn_dx_floor = p.id_pad_x + p.tier_id_col_w + p.tier_id_col_gap
        cn_dx = max(cn_dx_requested, cn_dx_floor)
        if cn_name:
            out.append({
                "kind": "tier_cn",
                "x": x_left + cn_dx,
                "y": y_top + tier_h - p.cn_pad_y_bot,
                "text": cn_name,
                "hue": hue,
                "font_size": cn_fs,
            })
        # EN / verbs column · starts at a measured fixed gap after CN.
        # The older len()*font-size heuristic made the visual gap between
        # tier titles and subtitles drift by tier/content. Use the same
        # conservative glyph model as atomize_svg_to_slide so the online
        # slide-native text boxes keep a stable title -> subtitle rhythm.
        cn_est_w = _estimate_text_width(cn_name, cn_fs) if cn_name else 0.0
        en_dx_floor = cn_dx + cn_est_w + p.tier_subtitle_gap if cn_name else 0.0
        en_dx = max(p.en_pad_x, en_dx_floor)
        en_x = x_left + en_dx
        # EN name (Inter caps, colored)
        if en_name:
            out.append({
                "kind": "tier_en",
                "x": en_x,
                "y": y_top + tier_h * p.en_pad_y_top_ratio,
                "text": en_name,
                "hue": hue,
            })
        # verbs italic
        if verbs:
            out.append({
                "kind": "tier_verbs",
                "x": en_x,
                "y": y_top + tier_h * p.verbs_pad_y_top_ratio,
                "text": verbs,
            })
        guide_text = en_name or verbs
        if guide_text:
            guide_font = 16.0 if en_name else 15.0
            guide_tracking = 0.18 if en_name else 0.0
            guide_y_ratio = p.en_pad_y_top_ratio if en_name else p.verbs_pad_y_top_ratio
            guide_x1 = (
                en_x
                + _estimate_text_width(
                    guide_text,
                    guide_font,
                    letter_spacing_em=guide_tracking,
                )
                + p.tier_guide_gap
            )
            guide_x2 = x_right - p.tier_guide_right_pad
            if guide_x2 - guide_x1 >= p.tier_guide_min_w:
                out.append({
                    "kind": "tier_guide_line",
                    "x1": guide_x1,
                    "y1": y_top + tier_h * guide_y_ratio,
                    "x2": guide_x2,
                    "y2": y_top + tier_h * guide_y_ratio,
                    "hue": hue,
                })
        # progress bar & example
        # · bar placed above example baseline · bar right = x_right - bar_right_pad
        bar_right = x_right - p.bar_right_pad
        bar_left = bar_right - p.bar_w
        # example baseline (roughly at tier upper-third → tier_h*0.45)
        example_y = y_top + tier_h * 0.45
        pct_y = y_top + tier_h * 0.87
        bar_y = y_top + tier_h * 0.72

        if example:
            out.append({
                "kind": "tier_example",
                "x": x_right - p.example_right_pad,
                "y": example_y,
                "text": example,
                "hue": hue,
            })
        if pct is not None:
            pct_c = max(0.0, min(1.0, pct / 100.0))
            out.append({
                "kind": "tier_bar_bg",
                "x": bar_left, "y": bar_y,
                "w": p.bar_w, "h": p.bar_h,
                "hue": hue,
            })
            out.append({
                "kind": "tier_bar_fill",
                "x": bar_left, "y": bar_y,
                "w": p.bar_w * pct_c, "h": p.bar_h,
                "hue": hue,
            })
            out.append({
                "kind": "tier_pct",
                "x": x_right - p.pct_right_pad,
                "y": pct_y,
                "text": f"{int(round(pct))}%",
                "hue": hue,
            })

        tier_positions.append({
            "index": i, "tier_num": tier_num,
            "x_left": x_left, "y_top": y_top, "w": w, "h": tier_h,
            "cx": x_left + w / 2, "cy": cy,
            "hue": hue, "pct": pct,
            "cn": cn_name, "en": en_name,
        })

    # ── CALLOUT (MASTERY CLIFF or user-supplied) ──
    # Data protocol:
    #   tree.extra["callout"] = {"tier_num": int, "kicker": str, "text": str, "hue": str, "enabled": bool}
    #     if None or missing: auto-pick max-drop tier from pct sequence (bottom-up)
    #     if enabled=False: skip callout
    callout_cfg = None
    if isinstance(tree_extra, dict):
        callout_cfg = tree_extra.get("callout")
    if callout_cfg is None:
        # auto: compute max-drop tier (max Δpct between adjacent tiers, i vs i-1 where i-1 is below)
        drops: List[Tuple[int, float]] = []  # (upper tier_num, drop_pct)
        for i in range(1, len(tier_positions)):
            lower = tier_positions[i - 1]
            upper = tier_positions[i]
            if lower.get("pct") is not None and upper.get("pct") is not None:
                d = float(lower["pct"]) - float(upper["pct"])
                if d > 0:
                    drops.append((upper["tier_num"], d))
        if drops:
            drops.sort(key=lambda t: t[1], reverse=True)
            top_num, drop_pt = drops[0]
            # find lower's tier_num
            for pos in tier_positions:
                if pos["tier_num"] == top_num - 1:
                    below_num = top_num - 1
                    below_hue = pos["hue"]
                    break
            else:
                below_num, below_hue = top_num - 1, "rust"
            callout_cfg = {
                "tier_num": top_num - 1,  # cliff pinned to the LOWER of the pair
                "kicker": "CLIFF",
                "text": f"drops {int(round(drop_pt))}pt",
                "hue": below_hue,
                "enabled": True,
            }

    if callout_cfg and callout_cfg.get("enabled", True):
        pin_tier = callout_cfg.get("tier_num")
        pin_pos: Optional[Dict[str, Any]] = None
        for pos in tier_positions:
            if pos["tier_num"] == pin_tier:
                pin_pos = pos
                break
        if pin_pos is None and tier_positions:
            # fall back to middle tier
            pin_pos = tier_positions[len(tier_positions) // 2]
        if pin_pos is not None:
            # ─── callout placement · sidebar-collision-safe ───
            # Default anchor: right of pyramid (x_right + 6), centered on pin tier.
            # HARD CONSTRAINT (has_sidebar): callout.right ≤ sidebar_x - callout_sidebar_gap.
            # If the right-gutter cannot fit the requested callout width, relocate:
            #   1) if the KPI→pyramid-top vertical gap is ≥ callout_h + top_gap_min:
            #      → place callout centered horizontally in the pyramid, in that gap
            #        (works well for n≤4 where pyramid is short and gap is large).
            #   2) else if right-gutter is at least 88px wide:
            #      → shrink callout_w to fit the gutter (keep in gutter, no overlap).
            #   3) else (extreme squeeze): place callout inside pin tier's LEFT half
            #      above the EN/verbs column · half-transparent-safe fallback.
            callout_w_default = p.callout_w
            callout_h_default = p.callout_h
            kicker_txt = str(callout_cfg.get("kicker") or "MASTERY CLIFF")
            line_txt = str(callout_cfg.get("text") or "")
            hue = callout_cfg.get("hue") or pin_pos["hue"]

            # 1) baseline right-gutter position
            default_cx = p.callout_x
            default_cy = pin_pos["y_top"] + pin_pos["h"] / 2
            default_cy_top = default_cy - callout_h_default / 2

            # sidebar collision check (only when has_sidebar).
            # TWO collision types to guard against:
            #  A) HARD collision with sidebar BAR column (x ≥ callout_bar_x=1210).
            #     The right gutter naturally ends at callout_bar_x - gap, so the
            #     hard cap is max_hard_right = callout_bar_x - gap (≈ 1206).
            #  B) VISUAL collision with sidebar TEXT LABEL column (x ≥ sidebar_x=1140).
            #     Only matters when the callout's Y-range overlaps a sidebar row
            #     text baseline. Text labels sit at y = panel_y + row_offset +
            #     i * row_dy, where i indexes top-tier (Ln) first. Label glyph
            #     roughly occupies (y-10, y+2). If the callout rect covers this
            #     band, the label becomes unreadable — shrink callout width so
            #     right edge ≤ sidebar_x - callout_sidebar_gap.
            if has_sidebar:
                # A) hard right cap (bar column)
                max_hard_right = p.callout_bar_x - p.callout_sidebar_gap
                available_gutter_w_hard = max_hard_right - default_cx

                # B) label column: compute sidebar row Y positions (top→bottom)
                # rows displayed rev-order (Ln first) starting at
                # panel_y + row_first_offset. Rendered n rows.
                _sb_rows_y: List[float] = []
                for _ri in range(n):
                    _sb_rows_y.append(
                        p.sidebar_panel_y
                        + p.sidebar_row_first_offset
                        + _ri * p.sidebar_row_dy
                    )
                # detect whether default callout y-range covers ANY sidebar row
                # baseline. Label glyphs span y-10..y+2 (font 10pt). Add a
                # small buffer so we err on the side of collision.
                _cy_top = default_cy_top
                _cy_bot = default_cy_top + callout_h_default
                _label_glyph_top = 10.0  # px above baseline occupied by glyph
                _label_glyph_bot = 3.0   # px below baseline (descenders)
                _y_overlap_row = None
                for _ry in _sb_rows_y:
                    _lt = _ry - _label_glyph_top
                    _lb = _ry + _label_glyph_bot
                    # overlap if intervals [cy_top,cy_bot] and [lt,lb] intersect
                    if _cy_top < _lb and _cy_bot > _lt:
                        _y_overlap_row = _ry
                        break

                if _y_overlap_row is not None:
                    # Y-collision with sidebar label: gutter is capped at
                    # sidebar_x (label column start) - gap.
                    max_soft_right = p.sidebar_x - p.callout_sidebar_gap
                    available_gutter_w = min(
                        available_gutter_w_hard,
                        max_soft_right - default_cx,
                    )
                else:
                    # No Y-overlap · use the wider hard cap (bar column only)
                    available_gutter_w = available_gutter_w_hard
            else:
                available_gutter_w = callout_w_default  # unconstrained

            callout_placement = None  # "gutter" / "top_gap" / "pyramid_top_inside"

            # KPI band bottom is roughly y=158 (kpi_y=124 + kpi_h=34).
            # (also used further below in fallback branches)
            kpi_bottom = 158.0 if has_kpi_band else 110.0
            top_gap = top_y_ln - kpi_bottom

            # Small-n (3-4 tier) + sidebar: the sidebar's TIER MASTERY table
            # and ACTION VERBS panel occupy y=200..~500 for 4 rows, so the
            # right-gutter callout y (mid pin tier) visually collides with
            # sidebar text. Prefer top_gap placement in that case if it fits.
            small_n_prefer_top_gap = (
                has_sidebar and n <= 4 and top_gap >= callout_h_default + 20.0
            )

            # gutter_shrunk minimum width required to hold the callout.
            # We keep gutter placement when width ≥ _gutter_shrunk_min_w (=90);
            # font stays at 10.5pt (body ≥ 10pt hard red line) but letter-
            # spacing is reduced automatically when width < 130 so "MASTERY
            # CLIFF" fits (see letter_spacing_kicker field below).
            _gutter_shrunk_min_w = 90.0

            if not small_n_prefer_top_gap and available_gutter_w >= callout_w_default:
                # fits comfortably in right gutter · use default position
                callout_placement = "gutter"
                cx = default_cx
                cy_top = default_cy_top
                cw = callout_w_default
                ch = callout_h_default
            else:
                # right-gutter is too narrow or small-n prefers top_gap
                # placement · try KPI→pyramid-top space
                if top_gap >= callout_h_default + 12.0:
                    # place callout centered horizontally in the pyramid width,
                    # inside the KPI→pyramid-top vertical gap.
                    callout_placement = "top_gap"
                    # pyramid horizontal center: use pin tier's cx (already
                    # centered on the mastery cliff tier · reads as a natural anchor)
                    cx = pin_pos["cx"] - callout_w_default / 2
                    # Bias toward pyramid top (attach visually) rather than
                    # floating in gap center. Bottom of callout sits
                    # `callout_top_gap_attach_offset` (default 12px) above
                    # pyramid top edge. Fall back to gap-center if the gap is
                    # too tight for the attach position.
                    _attach_cy_top = (
                        top_y_ln
                        - p.callout_top_gap_attach_offset
                        - callout_h_default
                    )
                    _gap_center_cy_top = (
                        (kpi_bottom + top_y_ln) / 2 - callout_h_default / 2
                    )
                    if _attach_cy_top >= kpi_bottom + 6.0:
                        cy_top = _attach_cy_top
                    else:
                        cy_top = _gap_center_cy_top
                    cw = callout_w_default
                    ch = callout_h_default
                elif has_sidebar and available_gutter_w >= _gutter_shrunk_min_w:
                    # shrink callout_w to fit right gutter while keeping it in
                    # the same vertical position (aligned with cliff tier).
                    # Only takes this branch when we still have enough width
                    # for 10.5pt kicker · below that we'd be forced to drop
                    # kicker to 9pt (violates body ≥ 10pt hard red line), so
                    # we fall through to pyramid_top_inside instead.
                    callout_placement = "gutter_shrunk"
                    cw = min(callout_w_default, available_gutter_w)
                    ch = callout_h_default
                    cx = default_cx
                    cy_top = default_cy_top
                else:
                    # last-resort: overlap the pin tier · position hugging the
                    # top-right corner of the pin tier band so the callout sits
                    # above the EN/verbs row (which lives at tier_h*0.56 → ~34px
                    # from top for tier_h=60) rather than covering the tier body.
                    # Force cw ≥ _gutter_shrunk_min_w (130) so kicker stays at
                    # 10.5pt (body ≥ 10pt hard red line).
                    callout_placement = "pyramid_top_inside"
                    cw = max(_gutter_shrunk_min_w, min(callout_w_default, pin_pos["w"] * 0.55))
                    ch = callout_h_default
                    # Anchor callout so its BOTTOM sits at pin_pos.y_top + tier_h*0.50
                    # (just above EN row baseline). Callout top pushes UP into the
                    # tier_gap notch above pin tier. If that exceeds top_floor,
                    # we accept an EN-row overlap on the callout right half only.
                    _callout_bot = pin_pos["y_top"] + max(24.0, tier_h * 0.45)
                    _callout_top = _callout_bot - ch
                    if _callout_top < top_floor + 4.0:
                        _callout_top = top_floor + 4.0
                    cy_top = _callout_top
                    # x: sit callout at pin tier's RIGHT edge so the LEFT
                    # side of the tier (tier_id + CN + EN + verbs) stays visible
                    cx = pin_pos["x_left"] + pin_pos["w"] - cw - 6.0

            out.append({
                "kind": "callout_rect",
                "x": cx, "y": cy_top,
                "w": cw, "h": ch,
                "hue": hue,
                "placement": callout_placement,
            })
            # font sizes · body ≥ 10pt hard red line applies to callout kicker
            # (kicker counts as body text per Step-3e review). Floor at 10.5pt
            # for kicker (never drop to 9pt). When width < 130, reduce
            # letter-spacing so "MASTERY CLIFF" fits in the shrunk callout
            # without falling below 10pt.
            kicker_fs = 10.5
            line_fs = 13.0 if cw >= 130 else 11.0
            # letter-spacing (em) for kicker · matches width-headroom.
            # Full-width (cw ≥ 140) uses 0.22em tracking (baseline reference
            # aesthetic). Narrow gutter (cw < 130) drops to 0.06em so the
            # 13-char "MASTERY CLIFF" fits without triggering fs shrink.
            kicker_ls = 0.22 if cw >= 130 else 0.06
            # when in shrunk gutter, apply textLength ONLY when natural width
            # would overflow inner_w (=cw-16). Estimate natural width:
            #   kicker (Inter 10.5pt bold, ls=0.06em) ≈ 7.0px/char
            #   line   (Georgia 11pt italic)          ≈ 6.5px/char
            # Short strings ("CLIFF" 5c ≈ 35px, "drops 13pt" 10c ≈ 65px) fit
            # naturally inside inner_w=74 at cw=90 without shrink → no
            # textLength → renders at true glyph width, no tail overflow.
            if callout_placement == "gutter_shrunk":
                inner_w = cw - 16.0
                _kicker_est_w = len(kicker_txt) * 7.0
                _line_est_w = len(line_txt) * 6.5
                kicker_tl = inner_w if _kicker_est_w > inner_w else None
                line_tl = inner_w if _line_est_w > inner_w else None
            else:
                kicker_tl = None
                line_tl = None
            out.append({
                "kind": "callout_kicker",
                "cx": cx + cw / 2,
                "cy": cy_top + ch * 0.48,
                "text": kicker_txt,
                "hue": hue,
                "font_size": kicker_fs,
                "text_length": kicker_tl,
                "letter_spacing": kicker_ls,
            })
            out.append({
                "kind": "callout_line",
                "cx": cx + cw / 2,
                "cy": cy_top + ch * 0.84,
                "text": line_txt,
                "hue": hue,
                "font_size": line_fs,
                "text_length": line_tl,
            })

    # attach summary for preset (sidebar sizing, tier hue list)
    out.append({
        "kind": "layout_meta",
        "n_tiers": n,
        "tier_h": tier_h,
        "tier_gap": tier_gap,
        "step_indent": step_indent,
        "x_right": x_right,
        "has_sidebar": has_sidebar,
        "sidebar_x": p.sidebar_x,
        "sidebar_w": p.sidebar_w,
        "pyramid_top_y": top_y_ln,
        "pyramid_bot_y": y_bot,
        "tiers": tier_positions,       # ordered bottom→top
    })

    return out
