"""Structural validator for .pptx files.

Runs OOXML-level correctness checks and emits findings as JSON to stdout.
Real defects + defensible heuristics + a WCAG-correct contrast check.

Scope is deliberately **correctness only**: "is this file broken?" Every
check here has an objective answer that holds regardless of what stage
you're at — inspecting someone else's template, mid-build, or about to
deliver. Nothing here judges whether a deck is *good*.

Style and capacity questions live in `deck_style.py`:

    deck_style.py X.pptx --capacity --pages N   # can a template carry N pages?
    deck_style.py X.pptx --rhythm               # is a finished deck monotonous?

Keep that boundary. A clean report from this script says the file is
well-formed; it says nothing about whether a template's layouts can carry
your content. Conflating the two once caused an agent to repeat a
two-layout template across eight pages because the template scored
"no warnings".

Usage:
    python scripts/view_issues.py deck.pptx
    python scripts/view_issues.py deck.pptx --format pretty
    python scripts/view_issues.py deck.pptx --template brand.pptx  # palette adherence vs a reference deck

Exit code:
    0 — no issues
    1 — one or more findings
    2 — fatal (file unreadable, etc.)

Designed to be cheap and deterministic. Skip subjective design judgment
("the slide feels cramped"); that's what visual QA (subagent) is for.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

import defusedxml.ElementTree as ET

from pptx_core import (
    EMU_PER_CM,
    EMU_PER_INCH,
    NSMAP,
    Finding,
    _Deck,
    _estimate_text_height_emu,
    _estimate_text_width_emu,
    _hex,
    _iter_geometry,
    _iter_layout_visuals,
    _iter_shapes,
    _load_deck,
    _ph_inherit_map,
    _print_pretty,
    _rect_intersect,
    _resolve_target,
    _slide_index_of_part,
    _slide_solid_bg,
    _spill_collision,
    _theme_palette_hex,
    _vertical_spill_collision,
    _wcag_contrast,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Structural validator for .pptx")
    ap.add_argument("pptx")
    ap.add_argument("--format", choices=("json", "pretty"), default="json")
    ap.add_argument("--template", help="Reference template for palette-adherence check")
    ap.add_argument("--require-notes", action="store_true", help="Flag slides missing speaker notes")
    args = ap.parse_args()

    path = Path(args.pptx)
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2

    try:
        findings = run_all_checks(path, template=args.template, require_notes=args.require_notes)
    except Exception as e:
        print(f"fatal: {e}", file=sys.stderr)
        return 2

    if args.format == "pretty":
        _print_pretty(findings)
    else:
        json.dump([asdict(f) for f in findings], sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    return 1 if findings else 0


def run_all_checks(pptx_path: Path, *, template: str | None, require_notes: bool) -> list[Finding]:
    deck = _load_deck(pptx_path)
    findings: list[Finding] = []
    findings += check_broken_rels(deck)
    findings += check_unreferenced_media(deck)
    findings += check_duplicate_slide_ids(deck)
    findings += check_chart_series(deck)
    findings += check_table_dimensions(deck)
    findings += check_style_graph_cycles(deck)
    findings += check_off_slide_geometry(deck)
    findings += check_edge_clipping(deck)
    findings += check_inherited_layout_interference(deck)
    findings += check_overlap(deck)
    findings += check_text_overflow(deck)
    findings += check_font_hierarchy(deck)
    findings += check_low_contrast(deck)
    if template:
        findings += check_palette_adherence(deck, template)
    if require_notes:
        findings += check_speaker_notes_presence(deck)
    return findings

# ---------- checks ---------------------------------------------------------


def check_broken_rels(deck: _Deck) -> list[Finding]:
    out: list[Finding] = []
    for owner, rs in deck.rels.items():
        for r in rs:
            if r["TargetMode"] == "External":
                continue
            target = _resolve_target(owner, r["Target"])
            if target not in deck.parts:
                out.append(Finding(
                    check="broken_rels",
                    severity="error",
                    slide=_slide_index_of_part(deck, owner),
                    shape=None,
                    message=f"relationship {r['Id']} in {owner} points to missing part {target}",
                    details={"owner": owner, "id": r["Id"], "target": target},
                ))
    return out


def check_unreferenced_media(deck: _Deck) -> list[Finding]:
    out: list[Finding] = []
    orphans = sorted(deck.media_paths - deck.media_referenced)
    for m in orphans:
        out.append(Finding(
            check="unreferenced_media",
            severity="warning",
            slide=None,
            shape=None,
            message=f"media part not referenced by any relationship: {m}",
            details={"part": m},
        ))
    return out


def check_duplicate_slide_ids(deck: _Deck) -> list[Finding]:
    out: list[Finding] = []
    pres = ET.fromstring(deck.parts["ppt/presentation.xml"])
    seen: dict[str, int] = {}
    for idx, sld_id in enumerate(pres.findall(".//p:sldIdLst/p:sldId", NSMAP), start=1):
        sid = sld_id.get("id")
        if sid in seen:
            out.append(Finding(
                check="duplicate_slide_ids",
                severity="error",
                slide=idx,
                shape=None,
                message=f"duplicate slide id {sid} (also at position {seen[sid]})",
                details={"id": sid, "first_position": seen[sid], "duplicate_position": idx},
            ))
        else:
            seen[sid] = idx
    return out


def check_chart_series(deck: _Deck) -> list[Finding]:
    """Chart series referencing missing sheets / embeddings."""
    out: list[Finding] = []
    for name, data in deck.parts.items():
        if not name.startswith("ppt/charts/chart") or not name.endswith(".xml"):
            continue
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            continue
        # check externalData
        for ext in root.findall(".//c:externalData", NSMAP):
            rid = ext.get(f"{{{NSMAP['r']}}}id")
            owner_rels = deck.rels.get(name, [])
            r = next((x for x in owner_rels if x["Id"] == rid), None)
            if not r:
                out.append(Finding(
                    check="chart_series",
                    severity="error",
                    slide=_slide_index_of_part(deck, name),
                    shape=None,
                    message=f"chart {name} externalData references missing relationship {rid}",
                    details={"chart": name, "rid": rid},
                ))
                continue
            target = _resolve_target(name, r["Target"])
            if target not in deck.parts:
                out.append(Finding(
                    check="chart_series",
                    severity="error",
                    slide=_slide_index_of_part(deck, name),
                    shape=None,
                    message=f"chart {name} embeds missing sheet {target}",
                    details={"chart": name, "target": target},
                ))
    return out


def check_table_dimensions(deck: _Deck) -> list[Finding]:
    """For each <a:tbl>, count grid cols vs cells per row."""
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        try:
            root = ET.fromstring(deck.parts[slide_path])
        except (ET.ParseError, KeyError):
            continue
        for tbl in root.iter(f"{{{NSMAP['a']}}}tbl"):
            grid = tbl.find("a:tblGrid", NSMAP)
            if grid is None:
                continue
            n_cols = len(grid.findall("a:gridCol", NSMAP))
            for ri, tr in enumerate(tbl.findall("a:tr", NSMAP)):
                cells = tr.findall("a:tc", NSMAP)
                # account for hMerge / vMerge spans
                effective = 0
                for c in cells:
                    span = int(c.get("gridSpan", "1") or 1)
                    effective += span
                if effective != n_cols:
                    out.append(Finding(
                        check="table_dimensions",
                        severity="error",
                        slide=idx,
                        shape=None,
                        message=f"table row {ri} has {effective} cells but grid declares {n_cols} cols",
                        details={"row": ri, "cells": effective, "grid_cols": n_cols},
                    ))
    return out


def check_style_graph_cycles(deck: _Deck) -> list[Finding]:
    """Detect cycles in tableStyles / chartStyles / slideMaster basedOn chains."""
    out: list[Finding] = []
    # PPTX style cycles are rare. Walk slide masters: master -> layout -> slide chain
    # must terminate. Cycle would mean a layout points to itself transitively.
    layouts_to_master: dict[str, str] = {}
    for owner, rs in deck.rels.items():
        if "slideLayout" in owner and owner.endswith(".xml"):
            for r in rs:
                if "slideMaster" in (r["Type"] or ""):
                    layouts_to_master[owner] = _resolve_target(owner, r["Target"])
    # detect a layout that resolves to itself (would be a build error, almost
    # impossible in real files but cheap to check)
    for layout, master in layouts_to_master.items():
        if master == layout:
            out.append(Finding(
                check="style_graph_cycles",
                severity="error",
                slide=None,
                shape=None,
                message=f"slideLayout {layout} declares itself as slideMaster",
                details={"layout": layout},
            ))
    return out


def check_off_slide_geometry(deck: _Deck) -> list[Finding]:
    """Shapes whose bounding boxes lie outside the slide canvas.

    Tolerance: 0.5cm. Flag text-bearing shapes and semantic graphic frames
    (tables, charts, SmartArt, embedded objects). Decorative geometry
    off-canvas is sometimes intentional.
    """
    out: list[Finding] = []
    tol = EMU_PER_CM // 2
    w, h = deck.slide_w_emu, deck.slide_h_emu
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_geometry(
            deck.parts[slide_path], _ph_inherit_map(deck, slide_path)
        ):
            if not sp.get("has_text") and sp["kind"] != "graphicFrame":
                continue
            x, y, sw, sh = sp["x"], sp["y"], sp["w"], sp["h"]
            if x + sw < -tol or x > w + tol or y + sh < -tol or y > h + tol:
                out.append(Finding(
                    check="off_slide_geometry",
                    severity="warning",
                    slide=idx,
                    shape=sp["name"],
                    message=(
                        f"{sp['kind']} '{sp['name']}' is outside the slide canvas"
                    ),
                    details={
                        "x": x, "y": y, "w": sw, "h": sh,
                        "canvas": [w, h], "kind": sp["kind"],
                    },
                ))
    return out


def check_edge_clipping(deck: _Deck) -> list[Finding]:
    """Shapes that start on the canvas and run off it — partially clipped.

    Distinct from :func:`check_off_slide_geometry`, which only fires when a
    shape is *entirely* outside the canvas. A shape at x=9.05" w=1.45" on a
    10" slide is 30% off the right edge, fully visible to the author in the
    XML and fully broken in the render, yet it satisfies neither
    ``x > w + tol`` nor ``x + sw < -tol``. That gap shipped a table whose
    last column was cut in half and a bar chart whose track ran past the
    page.

    Two deliberate exemptions:

    - **Full-bleed pictures and background fills** — a hero image is
      *supposed* to bleed past the edge, and cropping it is the design.
      Recognised as any text-free shape spanning ≥90% of either axis.
    - **Unpainted spacers** — a ``<a:noFill/>`` rect with no outline and no
      text leaves no mark, so clipping it is invisible.

    Text-bearing shapes use a 0.05" tolerance, matching the usual internal text
    inset; other painted geometry retains the conservative 0.5cm tolerance.
    Text and semantic graphic-frame findings are deterministic ``error``
    findings; decorative geometry remains ``warning``.
    """
    out: list[Finding] = []
    w, h = deck.slide_w_emu, deck.slide_h_emu
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_geometry(deck.parts[slide_path], _ph_inherit_map(deck, slide_path)):
            if not sp.get("painted"):
                continue
            bx, by, bw, bh = sp.get("box") or (sp["x"], sp["y"], sp["w"], sp["h"])
            if bw <= 0 or bh <= 0:
                continue
            # entirely off-canvas is check_off_slide_geometry's finding
            if bx >= w or by >= h or bx + bw <= 0 or by + bh <= 0:
                continue
            over = {
                "left": max(0, -bx), "top": max(0, -by),
                "right": max(0, (bx + bw) - w), "bottom": max(0, (by + bh) - h),
            }
            is_text_shape = bool(sp.get("has_text"))
            is_semantic_frame = sp["kind"] == "graphicFrame"
            tol = EMU_PER_INCH // 20 if is_text_shape else EMU_PER_CM // 2
            clipped = {k: v for k, v in over.items() if v > tol}
            if not clipped:
                continue
            # A full-bleed pic/fill spanning most of an axis is bleeding by
            # design; text is never exempt.
            if sp.get("can_bleed") and (bw >= w * 0.9 or bh >= h * 0.9):
                continue
            worst = max(clipped.values())
            out.append(Finding(
                check="edge_clipping",
                severity=(
                    "error" if is_text_shape or is_semantic_frame else "warning"
                ),
                slide=idx,
                shape=sp["name"],
                message=(
                    f"'{sp['name']}' runs off the "
                    f"{'/'.join(sorted(clipped))} edge by "
                    f"{worst / EMU_PER_INCH:.2f}\" — it will render clipped"
                ),
                details={
                    "overflow_emu": clipped,
                    "box": {"x": bx, "y": by, "w": bw, "h": bh},
                    "canvas": [w, h],
                    "has_text": is_text_shape,
                    "kind": sp["kind"],
                    "tolerance_emu": tol,
                },
            ))
    return out


def check_inherited_layout_interference(deck: _Deck) -> list[Finding]:
    """报告新增文字与版式显式视觉元素之间的干扰。

    整页背景以及完整包住文字的版式视觉通常是有意的构图层。继承的小型装饰落入
    文字墨迹区域时不豁免，这正是本检查需要交给渲染审阅的失效模式。
    """
    out: list[Finding] = []
    slide_area = deck.slide_w_emu * deck.slide_h_emu
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        authored_text = [
            geometry
            for geometry in _iter_geometry(
                deck.parts[slide_path], _ph_inherit_map(deck, slide_path)
            )
            if geometry["kind"] == "sp"
            and geometry["content"]
            and not geometry.get("is_placeholder")
        ]
        layout_visuals = list(_iter_layout_visuals(deck, slide_path))
        for text_shape in authored_text:
            text_area = text_shape["w"] * text_shape["h"]
            if text_area <= 0:
                continue
            for visual in layout_visuals:
                visual_area = visual["w"] * visual["h"]
                if visual_area <= 0 or visual_area >= slide_area * 0.75:
                    continue
                intersection = _rect_intersect(text_shape, visual)
                if intersection <= 0:
                    continue
                # 布局视觉完整包住文字时，它通常是有意的卡片或底板。
                visual_contains_text = (
                    visual["x"] <= text_shape["x"]
                    and visual["y"] <= text_shape["y"]
                    and visual["x"] + visual["w"]
                    >= text_shape["x"] + text_shape["w"]
                    and visual["y"] + visual["h"]
                    >= text_shape["y"] + text_shape["h"]
                )
                if visual_contains_text:
                    continue
                ratio = intersection / min(text_area, visual_area)
                if ratio < 0.10:
                    continue
                layout_name = visual["source_part"].rsplit("/", 1)[-1]
                out.append(Finding(
                    check="inherited_layout_interference",
                    severity="warning",
                    slide=idx,
                    shape=f"{text_shape['name']} ∩ {visual['name']}",
                    message=(
                        f"authored text intersects visual inherited from {layout_name} "
                        f"by {100 * ratio:.0f}% of the smaller area; review the "
                        "full-resolution render"
                    ),
                    details={
                        "layout_part": visual["source_part"],
                        "text_shape": text_shape["name"],
                        "layout_shape": visual["name"],
                        "overlap_ratio": round(ratio, 3),
                    },
                ))
    return out


def check_overlap(deck: _Deck) -> list[Finding]:
    """Flag content-bearing shapes that overlap each other.

    Heuristic: walk every (sp or pic), compute bbox. For every unordered pair
    on the same slide where BOTH have content (text-bearing sp OR pic),
    compute intersection / smaller-area and bucket the severity:

    - ``ratio < 0.10`` → ``info`` (likely design-intent layering: drop caps,
      seal stamps, hero-image-with-floating-title, decorative bars under titles)
    - ``0.10 ≤ ratio < 0.40`` → ``warning`` (ambiguous — agent should look at
      the rendered slide to decide)
    - ``ratio ≥ 0.40`` → ``error`` (almost certainly a column-math bug — fix)

    Skips:
    - background fills (no text, no image): a full-bleed rect at z=0
    - shapes that fully contain another (parent ⊇ child = intentional layering)

    Real overlap (text-on-text, pic-over-card, big-pic-eats-the-card) is the
    most common visual bug we see — usually = wrong column math. The tiered
    severity keeps drop-cap / seal / hero-bg designs unflagged at ``info``
    while catching the actual bugs at ``error``.
    """
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        # Graphic frames are included in deterministic edge checks, but not in
        # this rectangle-overlap heuristic: labels and callouts intentionally
        # overlay charts often enough that adding them here would create noise.
        rects = [
            shape for shape in _iter_geometry(
                deck.parts[slide_path], _ph_inherit_map(deck, slide_path)
            )
            if shape["kind"] != "graphicFrame"
        ]
        for i, a in enumerate(rects):
            if not a["content"]:
                continue
            for b in rects[i + 1:]:
                if not b["content"]:
                    continue
                inter = _rect_intersect(a, b)
                if inter <= 0:
                    continue
                area_a = a["w"] * a["h"]
                area_b = b["w"] * b["h"]
                small = min(area_a, area_b)
                if small == 0:
                    continue
                # parent fully contains child → not a bug
                if inter >= 0.99 * small:
                    continue
                ratio = inter / small
                if ratio < 0.02:
                    continue  # noise (anti-aliasing margins)
                if ratio < 0.10:
                    severity = "info"
                elif ratio < 0.40:
                    severity = "warning"
                else:
                    severity = "error"
                out.append(Finding(
                    check="overlap",
                    severity=severity,
                    slide=idx,
                    shape=f"{a['name']} ∩ {b['name']}",
                    message=(
                        f"shapes overlap by {100*ratio:.0f}% of the smaller — "
                        f"{'likely a column-math bug' if severity == 'error' else 'review the rendered slide'}"
                    ),
                    details={
                        "a": {"name": a["name"], "x": a["x"], "y": a["y"], "w": a["w"], "h": a["h"], "kind": a["kind"]},
                        "b": {"name": b["name"], "x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"], "kind": b["kind"]},
                        "overlap_ratio": round(ratio, 3),
                    },
                ))
    return out


def check_text_overflow(deck: _Deck) -> list[Finding]:
    """Port of OfficeCLI PowerPointHandler.ShapeProperties.cs:3819-3839.

    Flat 0.55em latin / 1.0em CJK width. 5% tolerance.

    Two directions:

    - **Vertical** — estimated wrapped height vs usable box height.
    - **Horizontal** — ``wrap="none"`` shapes never wrap, so the text spills
      sideways out of its box. Spilling into empty canvas is a legitimate
      design (oversized display type in a deliberately narrow box), so this
      only fires when the spill leaves the canvas or lands on another
      content-bearing shape.

    Autofit is only honoured as an escape hatch on the **vertical** axis, and
    only when it has actually been *computed*. Neither flavour is
    self-certifying:

    - ``<a:normAutofit/>`` bare is a request that no renderer has resolved —
      python-pptx never fills in the scale, and non-PowerPoint renderers
      ignore the element entirely.
    - ``<a:spAutoFit/>`` says "the box grows to the text", but the growing is
      the author's job. python-pptx hardcodes it into every textbox it
      creates and never recomputes ``cy``, so on a generated deck it is
      noise: 178 of 204 text shapes carried it on a deck whose metric cards
      visibly overflowed their 0.16" boxes.

    So a ``fontScale``/``lnSpcReduction`` is trusted outright, and a bare
    ``spAutoFit`` is only trusted when the declared height actually agrees
    with the estimate — which is what the box-fits test below already asks.
    Horizontal spill is never exempt: neither flavour narrows text, and a
    stale ``spAutoFit`` box is itself the bug.
    """
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        shapes = list(_iter_shapes(deck.parts[slide_path], _ph_inherit_map(deck, slide_path)))
        for sp in shapes:
            if not sp["has_text"]:
                continue
            if sp["wrap"] == "none":
                est_w = _estimate_text_width_emu(sp)
                usable_w = max(sp["w"] - sp["margin_l"] - sp["margin_r"], 1)
                if est_w <= usable_w * 1.05:
                    continue
                spill = {
                    "x": sp["x"] + sp["margin_l"], "y": sp["y"],
                    "w": est_w, "h": sp["h"],
                }
                hit = _spill_collision(spill, sp, shapes, deck.slide_w_emu)
                if hit is None:
                    continue
                out.append(Finding(
                    check="text_overflow",
                    severity="warning",
                    slide=idx,
                    shape=sp["name"],
                    message=(
                        f"text in '{sp['name']}' has wrap=\"none\" and spills "
                        f"{est_w - usable_w} EMU past its box {hit}"
                    ),
                    details={
                        "axis": "horizontal",
                        "est_width_emu": est_w,
                        "usable_width_emu": usable_w,
                        "collides_with": hit,
                        "text": sp["text"][:60],
                    },
                ))
                continue
            if sp["auto_fit_computed"]:
                continue
            est_h = _estimate_text_height_emu(sp)
            usable_h = max(sp["h"] - sp["margin_t"] - sp["margin_b"], 1)
            if est_h <= usable_h * 1.05:
                continue
            # Overflowing the *declared* box is only a defect when something
            # shows it: the shape's own painted edge, the canvas edge, or a
            # neighbour the glyphs land on. An unfilled, unstroked box has no
            # visible boundary to cross.
            if sp["has_edge"]:
                hit = "its own painted edge"
            else:
                hit = _vertical_spill_collision(sp, est_h, shapes, deck.slide_h_emu)
                if hit is None:
                    continue
            out.append(Finding(
                check="text_overflow",
                severity="warning",
                slide=idx,
                shape=sp["name"],
                message=(
                    f"text in '{sp['name']}' overflows {hit} "
                    f"(est {est_h} EMU vs usable {usable_h} EMU)"
                ),
                details={
                    "axis": "vertical",
                    "est_height_emu": est_h,
                    "usable_height_emu": usable_h,
                    "collides_with": hit,
                    "auto_fit": sp["auto_fit"],
                },
            ))
    return out


def check_font_hierarchy(deck: _Deck) -> list[Finding]:
    """Detect title runs <36pt and body runs outside 11-18pt."""
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_shapes(deck.parts[slide_path], _ph_inherit_map(deck, slide_path)):
            if not sp["has_text"]:
                continue
            is_title = sp["placeholder_type"] in ("title", "ctrTitle")
            for size_emu in sp["text_sizes_emu"]:
                size_pt = size_emu / 100  # OOXML stores size as hundredths of pt
                if is_title and size_pt < 36:
                    out.append(Finding(
                        check="font_hierarchy",
                        severity="warning",
                        slide=idx,
                        shape=sp["name"],
                        message=f"title text at {size_pt:.0f}pt; recommend ≥36pt",
                        details={"size_pt": size_pt, "kind": "title"},
                    ))
                elif not is_title and (size_pt < 11 or size_pt > 18):
                    # Large text (>18pt) is usually intentional emphasis,
                    # not a "body" overshoot. Only flag very small text.
                    if size_pt < 8:
                        out.append(Finding(
                            check="font_hierarchy",
                            severity="error",
                            slide=idx,
                            shape=sp["name"],
                            message=f"text at {size_pt:.0f}pt is unreadable",
                            details={"size_pt": size_pt, "kind": "body"},
                        ))
    return out


def check_low_contrast(deck: _Deck) -> list[Finding]:
    """WCAG-correct contrast: linearized sRGB, then ratio against backdrop.

    Backdrop is the shape's own solid fill (if explicit) or slide bg
    (best-effort). Theme colors / lumMod/shade transforms are skipped.
    Reference: Ali's inherit_chrome.py:1270–1453 for the z-order walk
    (we use a simplified own-fill-or-slide-bg model here).
    """
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        slide_bg = _slide_solid_bg(deck.parts[slide_path])
        for sp in _iter_shapes(deck.parts[slide_path], _ph_inherit_map(deck, slide_path)):
            if not sp["has_text"] or not sp["text_colors"]:
                continue
            backdrop = sp["solid_fill"] or slide_bg
            if backdrop is None:
                continue
            for color in sp["text_colors"]:
                ratio = _wcag_contrast(color, backdrop)
                if ratio < 4.5:
                    out.append(Finding(
                        check="low_contrast",
                        severity="warning",
                        slide=idx,
                        shape=sp["name"],
                        message=f"text/backdrop contrast ratio {ratio:.2f} (<4.5)",
                        details={"text": _hex(color), "bg": _hex(backdrop), "ratio": round(ratio, 2)},
                    ))
                    break  # one finding per shape is enough
    return out


def check_palette_adherence(deck: _Deck, template_path: str) -> list[Finding]:
    """Flag explicit srgbClr values that don't match the template's theme palette."""
    out: list[Finding] = []
    try:
        with zipfile.ZipFile(template_path) as tzf:
            theme = tzf.read("ppt/theme/theme1.xml")
    except (FileNotFoundError, KeyError):
        return out
    palette = _theme_palette_hex(theme)
    if not palette:
        return out
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_shapes(deck.parts[slide_path], _ph_inherit_map(deck, slide_path)):
            for color in sp.get("explicit_colors", []):
                if _hex(color).upper() not in palette:
                    out.append(Finding(
                        check="palette_adherence",
                        severity="info",
                        slide=idx,
                        shape=sp["name"],
                        message=f"explicit color {_hex(color)} not in template palette",
                        details={"color": _hex(color), "palette": sorted(palette)},
                    ))
                    break
    return out


def check_speaker_notes_presence(deck: _Deck) -> list[Finding]:
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        owner_rels = deck.rels.get(slide_path, [])
        has_notes = False
        for r in owner_rels:
            if "notesSlide" in (r["Type"] or ""):
                target = _resolve_target(slide_path, r["Target"])
                if target in deck.parts:
                    # check the notes part has any text
                    try:
                        notes_root = ET.fromstring(deck.parts[target])
                        for t in notes_root.iter(f"{{{NSMAP['a']}}}t"):
                            if (t.text or "").strip():
                                has_notes = True
                                break
                    except ET.ParseError:
                        pass
        if not has_notes:
            out.append(Finding(
                check="speaker_notes_presence",
                severity="info",
                slide=idx,
                shape=None,
                message="slide has no speaker notes",
                details={},
            ))
    return out

if __name__ == "__main__":
    sys.exit(main())
