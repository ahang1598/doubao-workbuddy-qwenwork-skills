"""Style and capacity analysis for .pptx files.

Separate from `view_issues.py` on purpose. That script answers "is this
file broken?" — a question with objective answers that apply to any pptx
at any stage. This one answers two *judgment* questions whose answers
depend on what stage you're at:

    capacity  (run on a TEMPLATE, before you author anything)
        Can this template's layouts carry the deck I've been asked for?
        A template with two content layouts cannot carry sixteen pages
        without visible repetition, no matter how clean its OOXML is.

    rhythm    (run on a FINISHED deck)
        Does the deck read as monotonous or leave data pages visually unfinished?

Conflating these with correctness caused a real regression: `editing.md`
used to decide "is this template weak?" by counting `view_issues.py`
warnings. Those warnings measure execution defects, not layout capacity,
so a well-built but structurally thin template scored as "strong" and the
agent dutifully repeated its two content layouts eight times.

Usage:
    python scripts/deck_style.py template.pptx --capacity --pages 16
    python scripts/deck_style.py output.pptx   --rhythm
    python scripts/deck_style.py deck.pptx                 # both
    python scripts/deck_style.py deck.pptx --format pretty

Exit code:
    0 — nothing to report
    1 — one or more findings (all findings here are advisory)
    2 — fatal (file unreadable, etc.)

Every finding is `info` severity. These are hints for a judgment call,
never a gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import defusedxml.ElementTree as ET

from pptx_core import (
    NSMAP,
    Finding,
    _Deck,
    _estimate_text_height_emu,
    _iter_geometry,
    _iter_layout_visuals,
    _iter_shapes,
    _load_deck,
    _ph_inherit_map,
    _print_pretty,
    _rel_target,
    _resolve_target,
)

# A layout is a *content* layout if it can hold a body of material. Layouts
# whose role is structural (cover, agenda, section divider, closing) repeat
# by design and must not count toward capacity.
_STRUCTURAL_HINTS = (
    "封面", "cover", "title slide",
    "目录", "agenda", "contents", "toc",
    "篇章", "章节", "section", "divider", "transition",
    "结尾", "结束", "closing", "thank", "end",
    "广告", "tagline", "statement",
)

_CONTENT_BODY_MIN_CHARS = 12
_CONTENT_BOUNDS_MAX_RATIO = 0.30
_CONTENT_SIDE_GAP_MIN_RATIO = 0.30
_CONTENT_INTERNAL_GAP_MIN_RATIO = 0.24
_SEMANTIC_VISUAL_MIN_AREA_RATIO = 0.08
_DISPLAY_STATEMENT_MIN_SIZE = 2400
_PHOTO_MIN_BYTES = 4096
_CHROME_MAX_AREA_RATIO = 0.06
_CHROME_POSITION_TOLERANCE = 0.025


def main() -> int:
    ap = argparse.ArgumentParser(description="Style + capacity analysis for .pptx")
    ap.add_argument("pptx")
    ap.add_argument("--format", choices=("json", "pretty"), default="json")
    ap.add_argument("--capacity", action="store_true",
                    help="Report layout capacity (run this on a template)")
    ap.add_argument("--rhythm", action="store_true",
                    help="Report finished-deck visual rhythm hints")
    ap.add_argument("--pages", type=int, default=None,
                    help="Total slides in the final outline, including structural slides")
    args = ap.parse_args()

    path = Path(args.pptx)
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2

    # Neither flag given → run both. Explicit flags select.
    want_capacity = args.capacity or not (args.capacity or args.rhythm)
    want_rhythm = args.rhythm or not (args.capacity or args.rhythm)

    try:
        deck = _load_deck(path)
        findings: list[Finding] = []
        if want_capacity:
            findings += check_layout_capacity(deck, requested_pages=args.pages)
        if want_rhythm:
            findings += check_visual_rhythm(deck)
    except Exception as e:
        print(f"fatal: {e}", file=sys.stderr)
        return 2

    if args.format == "pretty":
        _print_pretty(findings)
    else:
        json.dump([asdict(f) for f in findings], sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    return 1 if findings else 0


def check_layout_capacity(deck: _Deck, *, requested_pages: int | None = None) -> list[Finding]:
    """Can this template's layouts carry the requested page count?

    Counts *distinct* content layouts. Two properties make this cheap and
    hard to get wrong:

    - It reads the template's own declared structure (`p:cSld/@name` plus
      the placeholder inventory), not a rendering heuristic.
    - Near-duplicate layouts collapse. Chinese enterprise templates
      routinely ship `内文-2` and `1_内文-2` — the same geometry twice,
      an artifact of PowerPoint's layout duplication. Counting those as
      two would overstate capacity by 50%.

    The verdict maps onto the grading in ``editing.md § Step 0``:

    - ``strict``  — enough distinct content layouts to place every page
    - ``mixed``   — enough for most; a few pages need native composition
    - ``coarse``  — brand chrome is reusable, content geometry is not:
      keep the palette/fonts/logo, rebuild content pages as native
      compositions on the blank layout
    - ``none``    — no reusable content layouts exist at all (a generated
      deck, or a lone bare master); style reference only
    """
    layouts = _layout_inventory(deck)
    content = [l for l in layouts if l["role"] == "content"]

    # Collapse near-duplicates by geometric signature.
    by_sig: dict[tuple, list[dict]] = {}
    for l in content:
        by_sig.setdefault(l["signature"], []).append(l)
    distinct = len(by_sig)

    blank = [l for l in layouts if l["role"] == "blank"]

    details = {
        "rule": "layout_capacity",
        "distinct_content_layouts": distinct,
        "content_layouts": [
            {
                "name": group[0]["name"],
                "part": group[0]["part"],
                "body_placeholders": group[0]["body_count"],
                "duplicates": [g["name"] for g in group[1:]],
            }
            for group in by_sig.values()
        ],
        "structural_layouts": [
            {"name": l["name"], "role": l["role"]}
            for l in layouts if l["role"] not in ("content", "blank")
        ],
        "blank_layout_available": bool(blank),
        "blank_layout": blank[0]["name"] if blank else None,
        "source_slide_layouts": _source_slide_layouts(deck, layouts),
    }

    if requested_pages is None:
        msg = (
            f"template ships {distinct} distinct content-page layout(s). "
            "Re-run with --pages <N> to get a strict/mixed/coarse verdict."
        )
        return [Finding(check="layout_capacity", severity="info", slide=None,
                        shape=None, message=msg, details=details)]

    # Structural pages (cover, TOC, dividers, closing) don't consume content
    # layouts. Estimate them so `pages` is comparable to `distinct`.
    structural_est = _estimate_structural_pages(requested_pages, layouts)
    content_pages = max(requested_pages - structural_est, 1)

    # Each distinct layout can carry a couple of pages before repetition
    # reads as monotony — the same cap check_visual_rhythm's layout_reuse
    # rule enforces after the fact.
    per_layout_cap = 2
    capacity = distinct * per_layout_cap

    if distinct == 0:
        # No reusable content geometry at all — typically a generated deck
        # whose slides each carry their own shapes, or a single bare master.
        # Distinct from `coarse` (which has layouts, just too few).
        verdict = "none"
    elif capacity >= content_pages:
        verdict = "strict"
    elif capacity >= content_pages * 0.6:
        verdict = "mixed"
    else:
        verdict = "coarse"

    details.update({
        "requested_pages": requested_pages,
        "estimated_structural_pages": structural_est,
        "content_pages_needed": content_pages,
        "capacity_at_2_pages_per_layout": capacity,
        "verdict": verdict,
    })

    advice = {
        "strict": (
            "enough distinct content layouts to place every page — "
            "reuse the template's layouts and fill their placeholders"
        ),
        "mixed": (
            "enough for most pages, short for the rest — reuse layouts where the "
            "information architecture matches, and build the remainder as native "
            "compositions on the blank layout in the template's sampled style"
        ),
        "coarse": (
            "not enough content geometry to carry this deck — treat the template as "
            "COARSE-REFERENCE: keep brand (palette, fonts, logo, header/footer, master "
            "chrome) and rebuild content pages as native compositions on the blank "
            "layout. Refilling these layouts will produce visibly identical pages."
        ),
        "none": (
            "this file defines no reusable content layouts at all (its slides carry "
            "their own geometry, as a generated deck does). There is nothing to "
            "'strictly follow' structurally — sample its palette, fonts and logo as a "
            "style reference and compose every content page natively."
        ),
    }[verdict]

    msg = (
        f"{distinct} distinct content layout(s) for ~{content_pages} content pages "
        f"({requested_pages} requested − ~{structural_est} structural) → "
        f"{verdict.upper()}: {advice}"
    )
    return [Finding(check="layout_capacity", severity="info", slide=None,
                    shape=None, message=msg, details=details)]


def _layout_inventory(deck: _Deck) -> list[dict]:
    """One record per slideLayout: name, role, placeholder signature."""
    out: list[dict] = []
    layout_parts = sorted(
        (p for p in deck.parts if p.startswith("ppt/slideLayouts/slideLayout")
         and p.endswith(".xml")),
        key=_layout_sort_key,
    )
    for part in layout_parts:
        try:
            root = ET.fromstring(deck.parts[part])
        except ET.ParseError:
            continue
        c_sld = root.find("p:cSld", NSMAP)
        name = (c_sld.get("name") if c_sld is not None else "") or part.rsplit("/", 1)[-1]

        # Placeholder inventory. sldNum/dt/ftr are chrome, not content slots.
        body_boxes: list[tuple[int, int, int, int]] = []
        kinds: list[str] = []
        for sp in root.iter(f"{{{NSMAP['p']}}}sp"):
            ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NSMAP)
            if ph is None:
                continue
            ph_type = ph.get("type") or "body"
            if ph_type in ("sldNum", "dt", "ftr"):
                continue
            kinds.append(ph_type)
            x_frm = sp.find("p:spPr/a:xfrm", NSMAP)
            if x_frm is None:
                continue
            off = x_frm.find("a:off", NSMAP)
            ext = x_frm.find("a:ext", NSMAP)
            if off is None or ext is None:
                continue
            body_boxes.append((
                int(off.get("x", "0")), int(off.get("y", "0")),
                int(ext.get("cx", "0")), int(ext.get("cy", "0")),
            ))

        out.append({
            "part": part,
            "name": name,
            "body_count": len(kinds),
            "role": _layout_role(name, len(kinds)),
            "signature": _geometry_signature(body_boxes, deck),
        })
    return out


def _source_slide_layouts(deck: _Deck, layouts: list[dict]) -> list[dict]:
    """记录每张源幻灯片的实际版式及其继承视觉元素。"""
    layout_names = {layout["part"]: layout["name"] for layout in layouts}
    out: list[dict] = []
    for index, slide_path in enumerate(deck.slide_paths, start=1):
        layout_part = _rel_target(deck, slide_path, "slideLayout")
        if not layout_part:
            continue
        visual_names = Counter(
            geometry["name"] for geometry in _iter_layout_visuals(deck, slide_path)
        )
        out.append({
            "slide": index,
            "layout_name": layout_names.get(
                layout_part, layout_part.rsplit("/", 1)[-1]
            ),
            "layout_part": layout_part,
            "inherited_visual_shapes": dict(sorted(visual_names.items())),
        })
    return out


def _layout_sort_key(part: str) -> int:
    digits = "".join(ch for ch in part.rsplit("/", 1)[-1] if ch.isdigit())
    return int(digits) if digits else 0


def _layout_role(name: str, body_count: int) -> str:
    """Classify a layout by its declared name, falling back to slot count.

    The name is the template author's own statement of intent and is far more
    reliable than guessing from geometry. Only when it says nothing useful do
    we fall back on the slot count.
    """
    low = name.strip().lower()
    for hint in _STRUCTURAL_HINTS:
        if hint in low or hint in name:
            return "structural"
    if "空白" in name or "blank" in low:
        return "blank"
    if body_count == 0:
        return "blank"
    return "content"


def _geometry_signature(boxes: list[tuple[int, int, int, int]], deck: _Deck) -> tuple:
    """Coarse fingerprint of a layout's content-slot geometry.

    Quantised to a 20×20 grid so that layouts differing by rounding — or by
    PowerPoint's duplicate-and-nudge — collapse to one entry, while genuinely
    different compositions stay distinct.
    """
    if not boxes:
        return ()
    gx = max(deck.slide_w_emu // 20, 1)
    gy = max(deck.slide_h_emu // 20, 1)
    return tuple(sorted(
        (x // gx, y // gy, w // gx, h // gy) for x, y, w, h in boxes
    ))


def _estimate_structural_pages(requested: int, layouts: list[dict]) -> int:
    """How many of the requested pages are cover / TOC / divider / closing.

    Cover + closing are always present. A TOC appears if the template has one.
    Dividers scale with deck length: business decks run 4–6 sections, one
    divider each, and a template that ships a divider layout expects them.
    """
    names = " ".join(l["name"] for l in layouts)
    has_toc = any(h in names.lower() or h in names
                  for h in ("目录", "agenda", "contents", "toc"))
    has_divider = any(h in names.lower() or h in names
                      for h in ("篇章", "章节", "section", "divider", "transition"))

    est = 2  # cover + closing
    if has_toc:
        est += 1
    if has_divider:
        # ~1 divider per 4 pages, 2–6
        est += max(2, min(6, requested // 4))
    return min(est, max(requested - 1, 1))


def _picture_bbox(pic) -> tuple[int, int, int, int] | None:
    xfrm = pic.find("p:spPr/a:xfrm", NSMAP)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NSMAP)
    ext = xfrm.find("a:ext", NSMAP)
    if off is None or ext is None:
        return None
    return (
        int(off.get("x", "0")), int(off.get("y", "0")),
        int(ext.get("cx", "0")), int(ext.get("cy", "0")),
    )


def _picture_references(deck: _Deck) -> list[dict]:
    """Return slide-local image references with their rendered boxes."""
    out: list[dict] = []
    embed_attr = f"{{{NSMAP['r']}}}embed"
    for slide, slide_path in enumerate(deck.slide_paths, start=1):
        relationships = {
            rel["Id"]: _resolve_target(slide_path, rel["Target"])
            for rel in deck.rels.get(slide_path, [])
            if rel.get("TargetMode") != "External"
            and (rel.get("Type") or "").endswith("/image")
        }
        try:
            root = ET.fromstring(deck.parts[slide_path])
        except (ET.ParseError, KeyError):
            continue
        for pic in root.iter(f"{{{NSMAP['p']}}}pic"):
            blip = pic.find("p:blipFill/a:blip", NSMAP)
            target = relationships.get(blip.get(embed_attr)) if blip is not None else None
            bbox = _picture_bbox(pic)
            if not target or not bbox:
                continue
            data = deck.parts.get(target)
            if not data or len(data) < _PHOTO_MIN_BYTES:
                continue
            out.append({
                "slide": slide,
                "part": target,
                "bbox": bbox,
                "hash": hashlib.sha256(data).hexdigest()[:16],
            })
    return out


def _is_repeated_brand_chrome(references: list[dict], deck: _Deck) -> bool:
    """Recognize stable corner marks and full-slide template backgrounds."""
    if not references:
        return False
    width = max(deck.slide_w_emu, 1)
    height = max(deck.slide_h_emu, 1)
    normalized = [
        (
            x / width, y / height, w / width, h / height
        )
        for x, y, w, h in (reference["bbox"] for reference in references)
    ]
    clusters: list[list[int]] = []
    for index, box in enumerate(normalized):
        for cluster in clusters:
            baseline = normalized[cluster[0]]
            if max(
                abs(value - expected)
                for value, expected in zip(box, baseline)
            ) <= _CHROME_POSITION_TOLERANCE:
                cluster.append(index)
                break
        else:
            clusters.append([index])
    stable = max(clusters, key=len)
    if len(stable) < 3 or len(stable) / len(references) < 0.60:
        return False
    x, y, w, h = normalized[stable[0]]
    full_slide = w >= 0.90 and h >= 0.90
    compact_edge_mark = (
        w * h <= _CHROME_MAX_AREA_RATIO
        and (x <= 0.08 or y <= 0.08 or x + w >= 0.92 or y + h >= 0.92)
    )
    if not (full_slide or compact_edge_mark):
        return False
    # Cover and closing slides often enlarge the same brand mark. Treat those
    # structural variants as part of the stable chrome family, not as photos.
    outliers = [
        references[index]["slide"]
        for index in range(len(references))
        if index not in stable
    ]
    return all(slide in (1, len(deck.slide_paths)) for slide in outliers)


def _check_duplicate_photos(deck: _Deck) -> list[Finding]:
    """Find cross-slide photo reuse even when slides share one media part."""
    inherited_media = {
        _resolve_target(owner, rel["Target"])
        for owner, relationships in deck.rels.items()
        if owner.startswith(("ppt/slideLayouts/", "ppt/slideMasters/"))
        for rel in relationships
        if rel.get("TargetMode") != "External"
        and (rel.get("Type") or "").endswith("/image")
    }
    by_hash: dict[str, list[dict]] = {}
    for reference in _picture_references(deck):
        if reference["part"] in inherited_media:
            continue
        by_hash.setdefault(reference["hash"], []).append(reference)

    out: list[Finding] = []
    for digest, references in sorted(by_hash.items()):
        slides = sorted({reference["slide"] for reference in references})
        if len(slides) < 2 or _is_repeated_brand_chrome(references, deck):
            continue
        parts = sorted({reference["part"] for reference in references})
        out.append(Finding(
            check="visual_rhythm",
            severity="info",
            slide=None,
            shape=None,
            message=(
                f"the same photo is referenced on slides {slides}; review "
                "whether the reuse is intentional"
            ),
            details={
                "rule": "duplicate_photo",
                "slides": slides,
                "parts": parts,
                "hash": digest,
            },
        ))
    return out


def _check_content_obligation(deck: _Deck) -> list[Finding]:
    """Advisory signal when a content page lacks a visible payload."""
    out: list[Finding] = []
    canvas_area = deck.slide_w_emu * deck.slide_h_emu
    if canvas_area <= 0:
        return out

    layout_roles = {
        layout["part"]: layout["role"]
        for layout in _layout_inventory(deck)
    }
    for idx, slide_path in enumerate(deck.slide_paths, start=1):
        if idx in (1, len(deck.slide_paths)):
            continue
        try:
            root = ET.fromstring(deck.parts[slide_path])
        except (ET.ParseError, KeyError):
            continue

        layout_part = _rel_target(deck, slide_path, "slideLayout")
        if layout_part and layout_roles.get(layout_part) == "structural":
            continue

        inherited = _ph_inherit_map(deck, slide_path)
        shapes = [
            shape for shape in _iter_shapes(deck.parts[slide_path], inherited)
            if shape["has_text"]
            and shape["placeholder_type"] not in ("sldNum", "dt", "ftr")
            and not (
                shape["y"] >= deck.slide_h_emu * 0.85
                and max(
                    [
                        *(shape.get("text_sizes_emu") or []),
                        shape.get("inherited_size_emu") or 0,
                    ],
                    default=0,
                ) <= 1000
                and len(shape["text"].strip()) <= 80
            )
        ]
        paragraphs = [
            paragraph["text"]
            for shape in shapes
            for paragraph in shape.get("paragraphs", [])
            if paragraph.get("text", "").strip()
        ]
        combined_text = " ".join(paragraphs).lower()
        if any(hint in combined_text for hint in ("contents", "agenda", "目录")):
            continue

        geometries = list(_iter_geometry(
            deck.parts[slide_path], inherited
        ))
        body_shapes = [
            shape for shape in shapes
            if shape["placeholder_type"] not in ("title", "ctrTitle")
        ]
        meaningful_chars = len("".join(paragraphs).replace(" ", ""))
        body_chars = len("".join(
            shape["text"] for shape in body_shapes
        ).replace(" ", ""))

        visual_area = 0
        semantic_visuals = 0
        for geometry in geometries:
            area = geometry["w"] * geometry["h"]
            if area <= 0:
                continue
            if geometry["kind"] == "graphicFrame":
                semantic_visuals += 1
                visual_area += min(area, canvas_area)
            elif (
                geometry["kind"] == "pic"
                and area >= canvas_area * _SEMANTIC_VISUAL_MIN_AREA_RATIO
            ):
                semantic_visuals += 1
                visual_area += area
        visual_ratio = min(visual_area / canvas_area, 1.0)

        sizes = [
            size
            for shape in shapes
            for size in [
                *(shape.get("text_sizes_emu") or []),
                shape.get("inherited_size_emu"),
            ]
            if size is not None
        ]
        is_display_statement = (
            1 <= len(shapes) <= 2
            and 4 <= meaningful_chars
            and max(sizes, default=0) >= _DISPLAY_STATEMENT_MIN_SIZE
        )

        if (
            body_chars < _CONTENT_BODY_MIN_CHARS
            and semantic_visuals == 0
            and not is_display_statement
        ):
            out.append(Finding(
                check="visual_rhythm",
                severity="info",
                slide=idx,
                shape=None,
                message=(
                    "content page has no substantial body text, table, chart, "
                    "or image; verify that its planned message was authored. "
                    "Do not add decorative filler."
                ),
                details={
                    "rule": "content_obligation",
                    "reason": "missing_payload",
                    "meaningful_text_chars": meaningful_chars,
                    "body_text_chars": body_chars,
                    "semantic_visual_count": semantic_visuals,
                },
            ))
            continue

        body_paragraphs = sum(
            1
            for shape in body_shapes
            for paragraph in shape.get("paragraphs", [])
            if paragraph.get("text", "").strip()
        )
        if semantic_visuals or not body_shapes or body_paragraphs < 3:
            continue
        body_geometry: list[dict] = []
        for shape in body_shapes:
            ink_h = min(
                shape["h"],
                _estimate_text_height_emu(shape)
                + shape["margin_t"] + shape["margin_b"],
            )
            y = shape["y"]
            if shape.get("vertical_anchor") in ("ctr", "mid"):
                y += max((shape["h"] - ink_h) // 2, 0)
            elif shape.get("vertical_anchor") in ("b", "bottom"):
                y += max(shape["h"] - ink_h, 0)
            body_geometry.append({
                "x": shape["x"], "y": y,
                "w": shape["w"], "h": ink_h,
            })
        # Use estimated ink geometry rather than declared textbox height. A
        # top-anchored textbox may span most of the slide while painting only
        # two lines; using its declared box is what hid the original blank-band
        # failures from this review.
        min_x = min(shape["x"] for shape in body_geometry)
        min_y = min(shape["y"] for shape in body_geometry)
        max_x = max(shape["x"] + shape["w"] for shape in body_geometry)
        max_y = max(shape["y"] + shape["h"] for shape in body_geometry)
        bounds_ratio = (max_x - min_x) * (max_y - min_y) / canvas_area
        largest_side_gap = max(
            min_x / deck.slide_w_emu,
            (deck.slide_w_emu - max_x) / deck.slide_w_emu,
        )
        largest_vertical_gap = max(
            min_y / deck.slide_h_emu,
            (deck.slide_h_emu - max_y) / deck.slide_h_emu,
        )
        largest_edge_gap = max(largest_side_gap, largest_vertical_gap)
        edge_signal = (
            bounds_ratio <= _CONTENT_BOUNDS_MAX_RATIO
            and largest_edge_gap >= _CONTENT_SIDE_GAP_MIN_RATIO
        )

        intervals = sorted(
            (shape["y"], shape["y"] + shape["h"])
            for shape in body_geometry
            if shape["h"] > 0
        )
        merged: list[list[int]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        largest_internal_gap = max(
            (
                merged[index + 1][0] - merged[index][1]
                for index in range(len(merged) - 1)
            ),
            default=0,
        )
        internal_gap_ratio = largest_internal_gap / deck.slide_h_emu
        internal_gap_signal = (
            internal_gap_ratio >= _CONTENT_INTERNAL_GAP_MIN_RATIO
        )
        if not edge_signal and not internal_gap_signal:
            continue

        out.append(Finding(
            check="visual_rhythm",
            severity="info",
            slide=idx,
            shape=None,
            message=(
                f"{body_paragraphs} body paragraphs leave a substantial empty "
                "region in the visible composition; compare the render with "
                "the page's planned message and review whether the composition "
                "is complete. Do not add decorative filler."
            ),
            details={
                "rule": "content_obligation",
                "reason": "one_sided_payload",
                "body_paragraph_count": body_paragraphs,
                "content_bounds_ratio": round(bounds_ratio, 3),
                "largest_horizontal_gap_ratio": round(largest_side_gap, 3),
                "largest_vertical_gap_ratio": round(largest_vertical_gap, 3),
                "largest_internal_vertical_gap_ratio": round(
                    internal_gap_ratio, 3
                ),
                "edge_signal": edge_signal,
                "internal_gap_signal": internal_gap_signal,
                "semantic_visual_area_ratio": round(visual_ratio, 3),
            },
        ))
    return out


def check_visual_rhythm(deck: _Deck) -> list[Finding]:
    """Hints (info severity) for finished-deck rhythm and visual completeness.

    These are heuristics, not defects. The agent decides whether to act on each.

    Detectable review signals:

    - duplicate photo: the same image content referenced by two or more slides,
      excluding stable template/brand chrome
    - layout reuse: a template layout repeated across several content pages;
      structural pages and slides carrying their own composition are exempt
    - content obligation: a non-structural page has no substantial visible
      payload, or a multi-paragraph payload is confined to one side
    """

    # This check is a no-op for very small decks.
    if len(deck.slide_paths) < 3:
        return []

    out: list[Finding] = []

    out.extend(_check_duplicate_photos(deck))

    # -- 2. layout reuse (template-edit monotony) ---------------------------
    # Each slide has a rel to exactly one slideLayoutN.xml. Slides that share
    # the same layout target share a silhouette *when the slide itself is
    # just filling the layout's placeholders* — the template-edit case. A
    # from-scratch slide with hand-drawn non-placeholder shapes on the blank
    # layout does NOT share a silhouette with other blank-layout slides.
    #
    # The clean signal: count non-placeholder shapes on the slide (`sp`
    # without `<p:ph>`, plus `pic`, plus `grpSp`). If ≥3, the slide carries
    # its own composition and is exempt. If all shapes are placeholders,
    # the layout owns the silhouette and repeats matter.
    #
    # Cover / divider / closing layouts naturally repeat — cover/closing by
    # position, dividers by short visible text (<40 chars).
    if len(deck.slide_paths) >= 6:
        layout_by_slide: dict[int, str] = {}
        text_by_slide: dict[int, int] = {}
        author_shape_count: dict[int, int] = {}
        for idx, slide_path in enumerate(deck.slide_paths, start=1):
            slide_rels = deck.rels.get(slide_path, [])
            layout_target = None
            for r in slide_rels:
                if "slideLayout" in (r["Type"] or ""):
                    layout_target = _resolve_target(slide_path, r["Target"])
                    break
            if layout_target:
                layout_by_slide[idx] = layout_target
            try:
                root = ET.fromstring(deck.parts[slide_path])
                total = sum(
                    len((t.text or ""))
                    for t in root.iter(f"{{{NSMAP['a']}}}t")
                )
                text_by_slide[idx] = total
                p_ns = NSMAP["p"]
                # non-placeholder sp: has no <p:ph> under nvSpPr/nvPr
                authored = 0
                for sp in root.iter(f"{{{p_ns}}}sp"):
                    ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NSMAP)
                    if ph is None:
                        authored += 1
                authored += sum(1 for _ in root.iter(f"{{{p_ns}}}pic"))
                authored += sum(1 for _ in root.iter(f"{{{p_ns}}}grpSp"))
                author_shape_count[idx] = authored
            except (ET.ParseError, KeyError):
                text_by_slide[idx] = 0
                author_shape_count[idx] = 0

        by_layout: dict[str, list[int]] = {}
        for slide_idx, layout in layout_by_slide.items():
            if slide_idx == 1 or slide_idx == len(deck.slide_paths):
                continue
            if text_by_slide.get(slide_idx, 0) < 40:
                continue
            # slide carries its own composition — layout is just a chrome shell
            if author_shape_count.get(slide_idx, 0) >= 3:
                continue
            by_layout.setdefault(layout, []).append(slide_idx)

        # Use a conservative threshold to limit finding noise. It selects when
        # to ask for review; it is not an authoring quota.
        cap = max(2, len(deck.slide_paths) // 5)
        for layout, slides in by_layout.items():
            if len(slides) > cap:
                layout_name = layout.rsplit("/", 1)[-1]
                out.append(Finding(
                    check="visual_rhythm",
                    severity="info",
                    slide=None,
                    shape=None,
                    message=(
                        f"{len(slides)} content pages use the same layout "
                        f"({layout_name}); review whether the repetition is deliberate "
                        "and helps comparison. No change is needed when it does."
                    ),
                    details={
                        "rule": "layout_reuse",
                        "layout": layout_name,
                        "slides": slides,
                        "cap": cap,
                    },
                ))

    out.extend(_check_content_obligation(deck))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
