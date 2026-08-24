"""Structural validator for .pptx files.

Runs ~12 OOXML-level checks and emits findings as JSON to stdout.
Real defects + defensible heuristics + a WCAG-correct contrast check.

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
import math
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import defusedxml.ElementTree as ET

NSMAP = {
    "p":  "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a":  "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r":  "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rs": "http://schemas.openxmlformats.org/package/2006/relationships",
    "c":  "http://schemas.openxmlformats.org/drawingml/2006/chart",
}

EMU_PER_CM = 360000
EMU_PER_PT = 12700
EMU_PER_INCH = 914400


@dataclass
class Finding:
    check: str
    severity: str          # "error" | "warning" | "info"
    slide: int | None      # 1-based slide number; None if package-level
    shape: str | None      # shape name if applicable
    message: str
    details: dict = field(default_factory=dict)


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
    findings += check_overlap(deck)
    findings += check_text_overflow(deck)
    findings += check_font_hierarchy(deck)
    findings += check_low_contrast(deck)
    if template:
        findings += check_palette_adherence(deck, template)
    if require_notes:
        findings += check_speaker_notes_presence(deck)
    return findings


# ---------- deck loading ----------------------------------------------------


@dataclass
class _Deck:
    path: Path
    zf: zipfile.ZipFile
    parts: dict[str, bytes]
    rels: dict[str, list[dict]]            # part_path -> list of {Id, Type, Target}
    slide_paths: list[str]                  # ordered ppt/slides/slideN.xml
    slide_w_emu: int
    slide_h_emu: int
    media_paths: set[str]                   # ppt/media/*
    media_referenced: set[str]              # subset actually referenced


def _load_deck(path: Path) -> _Deck:
    zf = zipfile.ZipFile(path)
    parts: dict[str, bytes] = {}
    for name in zf.namelist():
        parts[name] = zf.read(name)

    # parse rels files
    rels: dict[str, list[dict]] = {}
    for name in parts:
        if name.endswith(".rels"):
            owner = _rels_owner(name)
            root = ET.fromstring(parts[name])
            rels[owner] = [
                {
                    "Id": r.get("Id"),
                    "Type": r.get("Type"),
                    "Target": r.get("Target"),
                    "TargetMode": r.get("TargetMode", "Internal"),
                }
                for r in root
            ]

    # slide order
    pres_xml = ET.fromstring(parts["ppt/presentation.xml"])
    sld_id_list = pres_xml.find("p:sldIdLst", NSMAP)
    pres_rels = rels.get("ppt/presentation.xml", [])
    rid_to_target = {r["Id"]: r["Target"] for r in pres_rels}
    slide_paths: list[str] = []
    if sld_id_list is not None:
        for sld_id in sld_id_list.findall("p:sldId", NSMAP):
            rid = sld_id.get(f"{{{NSMAP['r']}}}id")
            target = rid_to_target.get(rid)
            if target:
                slide_paths.append(_resolve_target("ppt/presentation.xml", target))

    # canvas dimensions
    sld_sz = pres_xml.find("p:sldSz", NSMAP)
    slide_w = int(sld_sz.get("cx")) if sld_sz is not None else 9144000
    slide_h = int(sld_sz.get("cy")) if sld_sz is not None else 6858000

    # media
    media_paths = {p for p in parts if p.startswith("ppt/media/") and not p.endswith("/")}
    media_referenced: set[str] = set()
    for owner, rs in rels.items():
        for r in rs:
            if r["TargetMode"] == "External":
                continue
            target_abs = _resolve_target(owner, r["Target"])
            if target_abs.startswith("ppt/media/"):
                media_referenced.add(target_abs)

    return _Deck(
        path=path,
        zf=zf,
        parts=parts,
        rels=rels,
        slide_paths=slide_paths,
        slide_w_emu=slide_w,
        slide_h_emu=slide_h,
        media_paths=media_paths,
        media_referenced=media_referenced,
    )


def _rels_owner(rels_name: str) -> str:
    """ppt/slides/_rels/slide1.xml.rels -> ppt/slides/slide1.xml"""
    parts = rels_name.split("/")
    # remove the trailing .rels
    last = parts[-1][:-len(".rels")]
    base = parts[:-2] + [last] if parts[-2] == "_rels" else parts[:-1] + [last]
    return "/".join(base)


def _resolve_target(owner: str, target: str) -> str:
    """Resolve a relationship Target relative to its owner part."""
    if target.startswith("/"):
        return target.lstrip("/")
    owner_dir = "/".join(owner.split("/")[:-1])
    parts = owner_dir.split("/") if owner_dir else []
    for seg in target.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg == ".":
            continue
        else:
            parts.append(seg)
    return "/".join(parts)


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

    Tolerance: 0.5cm. Only flag text-bearing shapes (placeholder, autoshape
    with text, textbox). Decorative geometry off-canvas is sometimes
    intentional.
    """
    out: list[Finding] = []
    tol = EMU_PER_CM // 2
    w, h = deck.slide_w_emu, deck.slide_h_emu
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_shapes(deck.parts[slide_path]):
            if not sp["has_text"]:
                continue
            x, y, sw, sh = sp["x"], sp["y"], sp["w"], sp["h"]
            if x + sw < -tol or x > w + tol or y + sh < -tol or y > h + tol:
                out.append(Finding(
                    check="off_slide_geometry",
                    severity="warning",
                    slide=idx,
                    shape=sp["name"],
                    message=f"text-bearing shape '{sp['name']}' is outside the slide canvas",
                    details={"x": x, "y": y, "w": sw, "h": sh, "canvas": [w, h]},
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
        rects = list(_iter_geometry(deck.parts[slide_path]))
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


def _rect_intersect(a: dict, b: dict) -> int:
    dx = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    dy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return dx * dy


def _iter_geometry(slide_xml: bytes) -> Iterable[dict]:
    """Yield bbox + content flag for every sp/pic on the slide."""
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError:
        return

    def _bbox(elem) -> tuple[int, int, int, int] | None:
        x_frm = elem.find(".//a:xfrm", NSMAP)
        if x_frm is None:
            return None
        off = x_frm.find("a:off", NSMAP)
        ext = x_frm.find("a:ext", NSMAP)
        if off is None or ext is None:
            return None
        return (
            int(off.get("x", "0")),
            int(off.get("y", "0")),
            int(ext.get("cx", "0")),
            int(ext.get("cy", "0")),
        )

    # autoshape / textbox
    for sp in root.iter(f"{{{NSMAP['p']}}}sp"):
        bbox = _bbox(sp)
        if not bbox:
            continue
        nv = sp.find("p:nvSpPr/p:cNvPr", NSMAP)
        name = nv.get("name") if nv is not None else "shape"
        text_runs = sp.findall(".//a:r", NSMAP)
        has_text = any(
            (r.findtext("a:t", default="", namespaces=NSMAP) or "").strip()
            for r in text_runs
        )
        x, y, w, h = bbox
        yield {
            "kind": "sp", "name": name,
            "x": x, "y": y, "w": w, "h": h,
            "content": has_text,
        }

    # picture
    for pic in root.iter(f"{{{NSMAP['p']}}}pic"):
        bbox = _bbox(pic)
        if not bbox:
            continue
        nv = pic.find("p:nvPicPr/p:cNvPr", NSMAP)
        name = nv.get("name") if nv is not None else "picture"
        x, y, w, h = bbox
        yield {
            "kind": "pic", "name": name,
            "x": x, "y": y, "w": w, "h": h,
            "content": True,
        }


def check_text_overflow(deck: _Deck) -> list[Finding]:
    """Port of OfficeCLI PowerPointHandler.ShapeProperties.cs:3819-3839.

    Flat 0.55em latin / 1.0em CJK width. 5% tolerance. Skip shapes with
    autoFit=normal or autoFit=shape (PowerPoint auto-resizes those at render).
    """
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_shapes(deck.parts[slide_path]):
            if not sp["has_text"]:
                continue
            if sp["auto_fit"] in ("normAutofit", "spAutoFit"):
                continue
            est_h = _estimate_text_height_emu(sp)
            usable_h = max(sp["h"] - sp["margin_t"] - sp["margin_b"], 1)
            if est_h > usable_h * 1.05:
                out.append(Finding(
                    check="text_overflow",
                    severity="warning",
                    slide=idx,
                    shape=sp["name"],
                    message=f"text in '{sp['name']}' likely overflows (est {est_h} EMU vs usable {usable_h} EMU)",
                    details={"est_height_emu": est_h, "usable_height_emu": usable_h},
                ))
    return out


def check_font_hierarchy(deck: _Deck) -> list[Finding]:
    """Detect title runs <36pt and body runs outside 11-18pt."""
    out: list[Finding] = []
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        for sp in _iter_shapes(deck.parts[slide_path]):
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
        for sp in _iter_shapes(deck.parts[slide_path]):
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
        for sp in _iter_shapes(deck.parts[slide_path]):
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


# ---------- shape iteration -------------------------------------------------


def _iter_shapes(slide_xml: bytes) -> Iterable[dict]:
    """Yield a dict per shape with the bits the checks need."""
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError:
        return
    for sp in root.iter(f"{{{NSMAP['p']}}}sp"):
        nv = sp.find("p:nvSpPr/p:cNvPr", NSMAP)
        ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NSMAP)
        x_frm = sp.find("p:spPr/a:xfrm", NSMAP)
        if x_frm is None:
            continue
        off = x_frm.find("a:off", NSMAP)
        ext = x_frm.find("a:ext", NSMAP)
        if off is None or ext is None:
            continue
        body_pr = sp.find("p:txBody/a:bodyPr", NSMAP)
        margins = _body_margins(body_pr)
        auto_fit = None
        if body_pr is not None:
            for tag in ("normAutofit", "spAutoFit", "noAutofit"):
                if body_pr.find(f"a:{tag}", NSMAP) is not None:
                    auto_fit = tag
                    break

        # text runs / colors / sizes
        text_runs = sp.findall(".//a:r", NSMAP)
        has_text = any((r.findtext("a:t", default="", namespaces=NSMAP) or "").strip() for r in text_runs)
        text_sizes_emu: list[int] = []
        text_colors: list[tuple[int, int, int]] = []
        explicit_colors: list[tuple[int, int, int]] = []
        for r in text_runs:
            rpr = r.find("a:rPr", NSMAP)
            if rpr is not None and rpr.get("sz"):
                text_sizes_emu.append(int(rpr.get("sz")))
            # color: a:rPr/a:solidFill/a:srgbClr
            srgb = r.find("a:rPr/a:solidFill/a:srgbClr", NSMAP)
            if srgb is not None and srgb.get("val"):
                text_colors.append(_hex_to_rgb(srgb.get("val")))
                explicit_colors.append(_hex_to_rgb(srgb.get("val")))

        # shape fill
        sf = sp.find("p:spPr/a:solidFill/a:srgbClr", NSMAP)
        solid_fill = _hex_to_rgb(sf.get("val")) if sf is not None and sf.get("val") else None
        if solid_fill:
            explicit_colors.append(solid_fill)

        # gather text widths (simplified: total chars)
        text = "".join(
            (r.findtext("a:t", default="", namespaces=NSMAP) or "")
            for r in text_runs
        )

        yield {
            "name": (nv.get("name") if nv is not None else "shape"),
            "x": int(off.get("x", "0")),
            "y": int(off.get("y", "0")),
            "w": int(ext.get("cx", "0")),
            "h": int(ext.get("cy", "0")),
            "has_text": has_text,
            "text": text,
            "text_sizes_emu": text_sizes_emu,
            "text_colors": text_colors,
            "explicit_colors": explicit_colors,
            "solid_fill": solid_fill,
            "margin_l": margins[0],
            "margin_t": margins[1],
            "margin_r": margins[2],
            "margin_b": margins[3],
            "auto_fit": auto_fit,
            "placeholder_type": ph.get("type") if ph is not None else None,
        }


def _body_margins(body_pr) -> tuple[int, int, int, int]:
    # bodyPr attrs: lIns/tIns/rIns/bIns in EMU; defaults from spec
    if body_pr is None:
        return (91440, 45720, 91440, 45720)
    return (
        int(body_pr.get("lIns") or 91440),
        int(body_pr.get("tIns") or 45720),
        int(body_pr.get("rIns") or 91440),
        int(body_pr.get("bIns") or 45720),
    )


def _slide_solid_bg(slide_xml: bytes) -> tuple[int, int, int] | None:
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError:
        return None
    sf = root.find(".//p:cSld/p:bg/p:bgPr/a:solidFill/a:srgbClr", NSMAP)
    if sf is not None and sf.get("val"):
        return _hex_to_rgb(sf.get("val"))
    return None


# ---------- text overflow estimation ---------------------------------------


def _estimate_text_height_emu(sp: dict) -> int:
    """Port OfficeCLI's char-width heuristic.

    Latin = 0.55em, CJK/fullwidth = 1.0em. Line height = font size pt * 1.2,
    converted to EMU. We don't have <a:bodyPr> line-spacing exposed here in
    enough detail; default to lnSpc=1.2.
    """
    usable_w = max(sp["w"] - sp["margin_l"] - sp["margin_r"], 1)
    text = sp["text"] or ""
    if not text:
        return 0
    sizes = sp["text_sizes_emu"] or [1800]  # default 18pt → 1800 (hundredths-of-pt)
    avg_size_pt = sum(sizes) / len(sizes) / 100
    font_emu = int(avg_size_pt * EMU_PER_PT)
    cjk_emu = font_emu          # 1.0em
    latin_emu = int(font_emu * 0.55)

    lines = 1
    cur = 0
    for ch in text:
        if ch == "\n":
            lines += 1
            cur = 0
            continue
        cw = cjk_emu if _is_cjk_or_fullwidth(ch) else latin_emu
        if cur + cw > usable_w and cur > 0:
            lines += 1
            cur = cw
        else:
            cur += cw

    line_h_emu = int(font_emu * 1.2)
    return lines * line_h_emu


def _is_cjk_or_fullwidth(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x3040 <= cp <= 0x30FF        # Hiragana, Katakana
        or 0x3400 <= cp <= 0x4DBF     # CJK Ext A
        or 0x4E00 <= cp <= 0x9FFF     # CJK Unified
        or 0xAC00 <= cp <= 0xD7AF     # Hangul
        or 0xFF00 <= cp <= 0xFF60     # Fullwidth Latin
        or 0xFFE0 <= cp <= 0xFFE6
    )


# ---------- contrast --------------------------------------------------------


def _wcag_contrast(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1 = _relative_luminance(c1)
    l2 = _relative_luminance(c2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(rgb[0]), lin(rgb[1]), lin(rgb[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------- palette / theme -------------------------------------------------


def _theme_palette_hex(theme_xml: bytes) -> set[str]:
    try:
        root = ET.fromstring(theme_xml)
    except ET.ParseError:
        return set()
    palette: set[str] = set()
    for srgb in root.iter(f"{{{NSMAP['a']}}}srgbClr"):
        v = srgb.get("val")
        if v:
            palette.add(v.upper())
    return palette


# ---------- misc helpers ----------------------------------------------------


def _slide_index_of_part(deck: _Deck, part_path: str) -> int | None:
    if part_path in deck.slide_paths:
        return deck.slide_paths.index(part_path) + 1
    # walk rels: chart, etc., are owned by a slide
    for idx, sp in enumerate(deck.slide_paths, start=1):
        for r in deck.rels.get(sp, []):
            if _resolve_target(sp, r["Target"]) == part_path:
                return idx
    return None


def _hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _print_pretty(findings: list[Finding]) -> None:
    if not findings:
        print("no issues")
        return
    sev_order = {"error": 0, "warning": 1, "info": 2}
    for f in sorted(findings, key=lambda x: (x.slide or 0, sev_order.get(x.severity, 9), x.check)):
        slide = f"slide {f.slide}" if f.slide else "deck"
        shape = f" ({f.shape})" if f.shape else ""
        print(f"[{f.severity.upper():7}] {slide}{shape}  {f.check}: {f.message}")


if __name__ == "__main__":
    sys.exit(main())
