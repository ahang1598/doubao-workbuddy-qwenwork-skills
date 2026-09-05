"""Shared OOXML plumbing for the .pptx analysis scripts.

Deck loading, relationship resolution, placeholder-inheritance resolution,
shape/geometry iteration, text-extent estimation, and colour maths. No
checks live here — only the machinery the checks are written against.

Two entry points build on this:

    view_issues.py   correctness — "is this file broken?"
    deck_style.py    style + capacity — "is this deck monotonous?",
                     "can this template carry N pages?"

Neither imports the other.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
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

# How far a no-wrap shape's text may poke into a neighbour before it counts as
# a collision. ~0.35cm — wide enough to absorb the default text insets and the
# error in the flat char-width metric, narrow enough that a real word-art
# collision (typically >1cm deep) still fires.
SPILL_TOL_EMU = 126000


@dataclass
class Finding:
    check: str
    severity: str          # "error" | "warning" | "info"
    slide: int | None      # 1-based slide number; None if package-level
    shape: str | None      # shape name if applicable
    message: str
    details: dict = field(default_factory=dict)


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
    ph_inherit_cache: dict = field(default_factory=dict)


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


def _rect_intersect(a: dict, b: dict) -> int:
    dx = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    dy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return dx * dy


def _iter_geometry(slide_xml: bytes, inherited: dict | None = None) -> Iterable[dict]:
    """Yield visible geometry for shapes, pictures, and graphic frames.

    ``inherited`` supplies geometry for placeholders that carry no ``<a:xfrm>``
    of their own (see :func:`_ph_inherit_map`).
    """
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError:
        return

    def _bbox(
        elem, xfrm_path: str = ".//a:xfrm"
    ) -> tuple[int, int, int, int] | None:
        x_frm = elem.find(xfrm_path, NSMAP)
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
        ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NSMAP)
        entry = (inherited or {}).get(_ph_key(ph)) or {}
        bbox = _bbox(sp) or entry.get("bbox")
        if not bbox:
            continue
        nv = sp.find("p:nvSpPr/p:cNvPr", NSMAP)
        name = nv.get("name") if nv is not None else "shape"
        text_runs = sp.findall(".//a:r", NSMAP)
        has_text = any(
            (r.findtext("a:t", default="", namespaces=NSMAP) or "").strip()
            for r in text_runs
        )
        # Anything that puts pixels on the slide: ink, a fill, or an outline.
        # A bare <a:noFill/> rect is a spacer and leaves no mark.
        has_visual_style = any(
            sp.find(f"p:spPr/a:{f}", NSMAP) is not None
            for f in ("solidFill", "gradFill", "blipFill", "pattFill")
        ) or sp.find("p:spPr/a:ln/a:solidFill", NSMAP) is not None
        painted = has_text or has_visual_style
        x, y, w, h = bbox
        # An unfilled, unstroked text box has no visible edges — only its ink
        # collides. Top-anchored boxes are routinely taller than their single
        # line of text (a stacked TOC is the canonical case), so comparing box
        # rectangles invents overlaps that nobody can see. Shrink such boxes to
        # the estimated ink height before the pairwise test.
        if (
            has_text
            and sp.find("p:spPr/a:solidFill", NSMAP) is None
            and sp.find("p:spPr/a:ln/a:solidFill", NSMAP) is None
        ):
            body_pr = sp.find("p:txBody/a:bodyPr", NSMAP)
            anchor = body_pr.get("anchor") if body_pr is not None else None
            ink_h = _ink_height_emu(sp, bbox[2], entry.get("size"), entry.get("wrap"))
            if ink_h and ink_h < h:
                if anchor in (None, "t"):
                    h = ink_h
                elif anchor == "b":
                    y, h = y + (h - ink_h), ink_h
                else:  # ctr
                    y, h = y + (h - ink_h) // 2, ink_h
        yield {
            "kind": "sp", "name": name,
            "x": x, "y": y, "w": w, "h": h,
            "content": has_text,
            "has_text": has_text,
            "painted": painted,
            "has_visual_style": has_visual_style,
            "is_placeholder": ph is not None,
            "can_bleed": not has_text,
            # The declared box, before any ink shrink. Edge-clipping is a
            # property of the box the renderer draws, not of the glyph band.
            "box": bbox,
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
            "has_text": False,
            "painted": True,
            "has_visual_style": True,
            "is_placeholder": False,
            "can_bleed": True,
            "box": bbox,
        }

    # table / chart / SmartArt / embedded object. Unlike sp and pic, a
    # graphicFrame stores its transform directly as p:xfrm.
    for frame in root.iter(f"{{{NSMAP['p']}}}graphicFrame"):
        bbox = _bbox(frame, "p:xfrm")
        if not bbox:
            continue
        nv = frame.find("p:nvGraphicFramePr/p:cNvPr", NSMAP)
        name = nv.get("name") if nv is not None else "graphic frame"
        x, y, w, h = bbox
        has_text = any(
            (node.text or "").strip()
            for node in frame.iter(f"{{{NSMAP['a']}}}t")
        )
        yield {
            "kind": "graphicFrame", "name": name,
            "x": x, "y": y, "w": w, "h": h,
            "content": True,
            "has_text": has_text,
            "painted": True,
            "has_visual_style": True,
            "is_placeholder": False,
            "can_bleed": False,
            "box": bbox,
        }


def _ph_key(ph) -> tuple[str, str] | None:
    """Identity of a placeholder for inheritance matching: (type, idx).

    OOXML default type is "body" when the attribute is absent. ``idx`` defaults
    to "0". Title-family types are interchangeable across the slide/layout
    boundary (a slide's ``title`` inherits from a layout's ``ctrTitle``), so
    they are normalised to a single bucket.
    """
    if ph is None:
        return None
    t = ph.get("type") or "body"
    if t in ("title", "ctrTitle"):
        return ("title", "")
    return (t, ph.get("idx") or "0")


def _ph_inherit_map(deck: _Deck, slide_path: str) -> dict[tuple[str, str], dict]:
    """Placeholder properties a slide inherits from its layout, then master.

    A slide shape with no ``<a:xfrm>`` is not position-less: PowerPoint walks
    slide -> slideLayout -> slideMaster and uses the first matching
    placeholder. Without this, whole slides (a TOC built entirely from layout
    placeholders) are invisible to the overlap and overflow checks — and
    ``wrap``/font-size defined only on the layout get misread as absent, which
    turns a correctly-designed no-wrap placeholder into a fake overflow.

    Each entry carries ``bbox``, ``wrap`` and ``size`` (hundredths of a point,
    from ``a:defRPr``/``a:rPr``). Layout entries win over master entries.
    """
    cached = deck.ph_inherit_cache.get(slide_path)
    if cached is not None:
        return cached

    chain: list[str] = []
    layout = _rel_target(deck, slide_path, "slideLayout")
    if layout:
        chain.append(layout)
        master = _rel_target(deck, layout, "slideMaster")
        if master:
            chain.append(master)

    inherited: dict[tuple[str, str], dict] = {}
    for part in reversed(chain):  # master first so the layout overwrites it
        xml = deck.parts.get(part)
        if xml is None:
            continue
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        for sp in root.iter(f"{{{NSMAP['p']}}}sp"):
            key = _ph_key(sp.find("p:nvSpPr/p:nvPr/p:ph", NSMAP))
            if key is None:
                continue
            entry = inherited.setdefault(key, {"bbox": None, "wrap": None, "size": None})
            x_frm = sp.find("p:spPr/a:xfrm", NSMAP)
            if x_frm is not None:
                off = x_frm.find("a:off", NSMAP)
                ext = x_frm.find("a:ext", NSMAP)
                if off is not None and ext is not None:
                    entry["bbox"] = (
                        int(off.get("x", "0")), int(off.get("y", "0")),
                        int(ext.get("cx", "0")), int(ext.get("cy", "0")),
                    )
            body_pr = sp.find("p:txBody/a:bodyPr", NSMAP)
            if body_pr is not None and body_pr.get("wrap"):
                entry["wrap"] = body_pr.get("wrap")
            for pr in sp.iter():
                if pr.tag in (f"{{{NSMAP['a']}}}defRPr", f"{{{NSMAP['a']}}}rPr") and pr.get("sz"):
                    entry["size"] = int(pr.get("sz"))
                    break

    deck.ph_inherit_cache[slide_path] = inherited
    return inherited


def _rel_target(deck: _Deck, owner: str, rel_suffix: str) -> str | None:
    for r in deck.rels.get(owner, []):
        if r["TargetMode"] == "External":
            continue
        if (r["Type"] or "").endswith("/" + rel_suffix):
            return _resolve_target(owner, r["Target"])
    return None


def _iter_layout_visuals(deck: _Deck, slide_path: str) -> Iterable[dict]:
    """返回幻灯片从版式继承的显式视觉元素。

    纯文字占位提示不会作为页面内容渲染，因此不纳入结果。母版级品牌元素仍交给
    渲染 QA 判断，因为 logo、页码和页脚通常是有意设计，通用碰撞检测会产生噪声。
    """
    layout = _rel_target(deck, slide_path, "slideLayout")
    if not layout:
        return
    xml = deck.parts.get(layout)
    if xml is None:
        return
    for geometry in _iter_geometry(xml):
        if geometry.get("has_visual_style"):
            yield {**geometry, "source_part": layout}


def _iter_shapes(slide_xml: bytes, inherited: dict | None = None) -> Iterable[dict]:
    """Yield a dict per shape with the bits the checks need.

    ``inherited`` maps ``_ph_key`` -> {bbox, wrap, size} for placeholders that
    take those from the layout/master (see :func:`_ph_inherit_map`).
    """
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError:
        return
    for sp in root.iter(f"{{{NSMAP['p']}}}sp"):
        nv = sp.find("p:nvSpPr/p:cNvPr", NSMAP)
        ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NSMAP)
        inh = (inherited or {}).get(_ph_key(ph)) or {}
        x_frm = sp.find("p:spPr/a:xfrm", NSMAP)
        bbox = None
        if x_frm is not None:
            off = x_frm.find("a:off", NSMAP)
            ext = x_frm.find("a:ext", NSMAP)
            if off is not None and ext is not None:
                bbox = (
                    int(off.get("x", "0")), int(off.get("y", "0")),
                    int(ext.get("cx", "0")), int(ext.get("cy", "0")),
                )
        if bbox is None:
            bbox = inh.get("bbox")
        if bbox is None:
            continue
        body_pr = sp.find("p:txBody/a:bodyPr", NSMAP)
        margins = _body_margins(body_pr)
        vertical_anchor = body_pr.get("anchor") if body_pr is not None else None
        auto_fit = None
        auto_fit_computed = False
        wrap = inh.get("wrap")
        if body_pr is not None:
            wrap = body_pr.get("wrap") or wrap
            for tag in ("normAutofit", "spAutoFit", "noAutofit"):
                node = body_pr.find(f"a:{tag}", NSMAP)
                if node is not None:
                    auto_fit = tag
                    # Neither flavour is self-certifying.
                    #
                    # <a:normAutofit/> bare is a *request*: no renderer has
                    # computed a shrink factor yet, and non-PowerPoint
                    # renderers ignore the element entirely. Only a populated
                    # fontScale/lnSpcReduction proves the fit was resolved.
                    #
                    # <a:spAutoFit/> means "grow the box to the text", but the
                    # growing is the *author's* job — the box only actually
                    # fits if cy was recomputed. python-pptx hardcodes
                    # spAutoFit into its textbox template and never touches cy,
                    # so on generated decks it marks nothing. Trusting it blind
                    # exempted 178/204 shapes on a deck whose cards visibly
                    # overflowed. The caller re-checks cy against the estimate.
                    auto_fit_computed = bool(
                        node.get("fontScale") or node.get("lnSpcReduction")
                    )
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
        # Does this shape have a visible edge of its own? An unfilled,
        # unstroked box is invisible, so text crossing its boundary crosses
        # nothing.
        has_edge = any(
            sp.find(f"p:spPr/a:{f}", NSMAP) is not None
            for f in ("solidFill", "gradFill", "blipFill", "pattFill")
        ) or sp.find("p:spPr/a:ln/a:solidFill", NSMAP) is not None

        # gather text widths (simplified: total chars)
        text = "".join(
            (r.findtext("a:t", default="", namespaces=NSMAP) or "")
            for r in text_runs
        )

        yield {
            "name": (nv.get("name") if nv is not None else "shape"),
            "x": bbox[0],
            "y": bbox[1],
            "w": bbox[2],
            "h": bbox[3],
            "has_text": has_text,
            "text": text,
            "paragraphs": _paragraphs_of(sp),
            "text_sizes_emu": text_sizes_emu,
            "inherited_size_emu": inh.get("size"),
            "text_colors": text_colors,
            "explicit_colors": explicit_colors,
            "solid_fill": solid_fill,
            "has_edge": has_edge,
            "painted": has_text or has_edge,
            "margin_l": margins[0],
            "margin_t": margins[1],
            "margin_r": margins[2],
            "margin_b": margins[3],
            "vertical_anchor": vertical_anchor,
            "auto_fit": auto_fit,
            "auto_fit_computed": auto_fit_computed,
            "wrap": wrap,
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


def _paragraphs_of(sp_elem) -> list[dict]:
    """Per-paragraph text and run sizes for a shape.

    Paragraph boundaries matter: ``<a:p>`` is a hard line break, and each
    paragraph carries its own run sizes. Flattening a shape to one string and
    one average size understates height whenever paragraphs differ in size —
    a 11.5pt label stacked on an 8.5pt caption averages to 10pt on a single
    line, which is how a two-line block fit inside a one-line box.
    """
    out: list[dict] = []
    for para in sp_elem.findall("p:txBody/a:p", NSMAP):
        runs = para.findall(".//a:r", NSMAP)
        text = "".join((r.findtext("a:t", default="", namespaces=NSMAP) or "") for r in runs)
        sizes = [
            int(r.find("a:rPr", NSMAP).get("sz"))
            for r in runs
            if r.find("a:rPr", NSMAP) is not None and r.find("a:rPr", NSMAP).get("sz")
        ]
        # a:br is an explicit line break inside one paragraph
        breaks = len(para.findall("a:br", NSMAP))
        out.append({"text": text, "sizes": sizes, "breaks": breaks})
    return out


def _estimate_text_height_emu(sp: dict) -> int:
    """Port OfficeCLI's char-width heuristic.

    Latin = 0.55em, CJK/fullwidth = 1.0em. Line height = font size pt * 1.2.

    Measured per paragraph and summed: each ``<a:p>`` starts a new line and
    sets its own line height from its own runs. Averaging sizes across the
    whole shape hid real overflow in generated decks, where a label/caption
    pair in one box is the standard idiom.
    """
    paragraphs = sp.get("paragraphs")
    if not paragraphs:
        text = sp.get("text") or ""
        if not text:
            return 0
        paragraphs = [{
            "text": text,
            "sizes": sp.get("text_sizes_emu") or [],
            "breaks": 0,
        }]

    usable_w = max(sp["w"] - sp["margin_l"] - sp["margin_r"], 1)
    default = sp.get("inherited_size_emu") or 1800
    total = 0
    for para in paragraphs:
        sizes = para.get("sizes") or [default]
        # A line's height is set by its tallest run, not the average.
        size_pt = max(sizes) / 100
        font_emu = int(size_pt * EMU_PER_PT)
        latin_emu = int(font_emu * 0.55)
        text = para.get("text") or ""

        lines = 1 + para.get("breaks", 0)
        cur = 0
        for ch in text:
            if ch == "\n":
                lines += 1
                cur = 0
                continue
            cw = font_emu if _is_cjk_or_fullwidth(ch) else latin_emu
            if cur + cw > usable_w and cur > 0:
                lines += 1
                cur = cw
            else:
                cur += cw
        total += lines * int(font_emu * 1.2)
    return total


def _spill_collision(spill: dict, source: dict, shapes: list[dict], canvas_w: int) -> str | None:
    """What the horizontal spill of a no-wrap shape actually hits.

    Returns a human-readable target ("the slide edge", or a shape name), or
    ``None`` when the spill lands in empty canvas — which is a legitimate
    design choice for oversized display type, not a bug.

    Only the portion *past* the source box counts, and it has to bite deeper
    than ``SPILL_TOL_EMU`` into the neighbour. Designers routinely size a
    no-wrap box tight to the glyphs and let the default 0.1" text insets
    nominally poke a few points into the next box; the flat char-width metric
    is not precise enough to call that a defect.
    """
    if spill["x"] + spill["w"] > canvas_w + SPILL_TOL_EMU:
        return "the slide edge"
    for other in shapes:
        if other is source or not other["has_text"]:
            continue
        depth = min(spill["x"] + spill["w"], other["x"] + other["w"]) - max(
            source["x"] + source["w"], other["x"]
        )
        overlap_y = min(spill["y"] + spill["h"], other["y"] + other["h"]) - max(
            spill["y"], other["y"]
        )
        if depth > SPILL_TOL_EMU and overlap_y > 0:
            return f"onto text in '{other['name']}'"
    return None


def _vertical_spill_collision(
    sp: dict, est_h: int, shapes: list[dict], canvas_h: int
) -> str | None:
    """What the downward spill of an overflowing text box actually hits.

    The vertical mirror of :func:`_spill_collision`, and it exists for the same
    reason: an unfilled, unstroked text box whose glyphs run past its declared
    ``cy`` into empty canvas looks *identical* to one sized correctly. Nobody
    can see the box, so nothing is wrong. python-pptx stamps every textbox with
    ``spAutoFit`` and never recomputes ``cy``, so this is the normal state of a
    generated deck, not a defect — flagging it produced ten warnings on an
    agenda slide that renders perfectly.

    What *is* visible: glyphs crossing the shape's own painted edge, glyphs
    running off the canvas, and glyphs landing on a neighbour.

    Returns a human-readable target, or ``None`` when the spill is invisible.
    """
    bottom = sp["y"] + sp["h"]
    spill_top = bottom
    spill_bottom = sp["y"] + sp["margin_t"] + est_h
    if spill_bottom <= spill_top + SPILL_TOL_EMU:
        return None
    if spill_bottom > canvas_h + SPILL_TOL_EMU:
        return "the slide edge"
    for other in shapes:
        if other is sp or not other.get("painted"):
            continue
        # A container the source sits inside (a card behind its own label) is
        # intentional layering, and spilling into its padding is invisible —
        # but only while the glyphs stay inside it. Text that runs out the
        # bottom of its own card is exactly the defect we are looking for.
        encloses = (
            other["x"] <= sp["x"] and other["y"] <= sp["y"]
            and other["x"] + other["w"] >= sp["x"] + sp["w"]
            and other["y"] + other["h"] >= bottom
        )
        if encloses:
            if spill_bottom > other["y"] + other["h"] + SPILL_TOL_EMU:
                return f"past the bottom of '{other['name']}'"
            continue
        depth = min(spill_bottom, other["y"] + other["h"]) - max(spill_top, other["y"])
        overlap_x = min(sp["x"] + sp["w"], other["x"] + other["w"]) - max(sp["x"], other["x"])
        if depth > SPILL_TOL_EMU and overlap_x > 0:
            if other.get("has_text"):
                return f"onto text in '{other['name']}'"
            return f"onto '{other['name']}'"
    return None


def _ink_height_emu(sp_elem, box_w: int, inherited_size: int | None, wrap: str | None) -> int:
    """Height the glyphs in a shape actually paint.

    Deliberately *not* the line-box height used by the overflow estimator:
    that includes 1.2em leading plus the top/bottom text insets, which for a
    single line is nearly the whole box and so shrinks nothing. What collides
    visually is the glyph band — roughly 1.0em per line, ascender to descender.
    Returns 0 when there is nothing to measure.
    """
    runs = sp_elem.findall(".//a:r", NSMAP)
    text = "".join((r.findtext("a:t", default="", namespaces=NSMAP) or "") for r in runs)
    if not text.strip():
        return 0
    body_pr = sp_elem.find("p:txBody/a:bodyPr", NSMAP)
    margins = _body_margins(body_pr)
    paragraphs = _paragraphs_of(sp_elem)
    sizes = [int(r.find("a:rPr", NSMAP).get("sz"))
             for r in runs
             if r.find("a:rPr", NSMAP) is not None and r.find("a:rPr", NSMAP).get("sz")]
    if (body_pr is not None and body_pr.get("wrap") == "none") or wrap == "none":
        # No wrapping: line count is literal, regardless of how far the glyphs
        # run past the box width. Feeding this to the wrapping estimator would
        # invent lines and defeat the shrink.
        band = 0
        for para in paragraphs:
            size = (max(para["sizes"]) if para["sizes"] else inherited_size or 1800) / 100
            lines = 1 + para.get("breaks", 0) + para["text"].count("\n")
            band += int(size * EMU_PER_PT * lines)
        return band
    line_box = _estimate_text_height_emu({
        "w": box_w, "text": text, "text_sizes_emu": sizes,
        "paragraphs": paragraphs,
        "inherited_size_emu": inherited_size,
        "margin_l": margins[0], "margin_r": margins[2],
    })
    if not line_box:
        return 0
    return int(line_box / 1.2)  # strip the leading; keep the glyph band


def _estimate_text_width_emu(sp: dict) -> int:
    """Widest single line, for shapes that never wrap (``wrap="none"``).

    Same 0.55em latin / 1.0em CJK metric as the height estimate. Measured per
    paragraph, since each ``<a:p>`` is its own line and carries its own run
    sizes; within a paragraph the largest run drives the width, because with
    no wrapping one oversized run is what breaks out of the box.
    """
    paragraphs = sp.get("paragraphs")
    if not paragraphs:
        text = sp.get("text") or ""
        if not text:
            return 0
        paragraphs = [{"text": text, "sizes": sp.get("text_sizes_emu") or []}]
    default = sp.get("inherited_size_emu") or 1800
    widest = 0
    for para in paragraphs:
        sizes = para.get("sizes") or [default]
        font_emu = int(max(sizes) / 100 * EMU_PER_PT)
        latin_emu = int(font_emu * 0.55)
        for line in (para.get("text") or "").split("\n"):
            w = sum(font_emu if _is_cjk_or_fullwidth(ch) else latin_emu for ch in line)
            widest = max(widest, w)
    return widest


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
