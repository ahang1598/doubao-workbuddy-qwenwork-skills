"""pptx — PowerPoint slide-deck inspection (read-only).

4 subcommands
-------------
list-slides    Index, title (best-effort), shape kinds, image/chart/table flags per slide.
slide-text     Extract all text from one slide (--slide N) or all slides (--all).
find-slide     First slide whose title or any text matches --regex.
count-images   Total picture/chart shape count (optionally per-slide breakdown).

Why no separate ``slide-shape`` command: the same {n_slides, has_picture_total,
has_chart_total} answers can already be assembled from list-slides + count-images
without proliferating subcommands.  Keep the surface small.
"""
from __future__ import annotations

import argparse
import re
from typing import Any

from . import _common as C

_PPTX_EXTS = (".pptx", ".pptm")


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("list-slides",
                       help="Index/title/shape kinds per slide; flags has_picture/has_chart/has_table.")
    p.add_argument("file")

    p = sub.add_parser("slide-text",
                       help="Extract all text from one slide (--slide N) or every slide (--all).")
    p.add_argument("file")
    p.add_argument("--slide", type=int, default=None,
                   help="1-based slide number; mutually exclusive with --all")
    p.add_argument("--all", action="store_true",
                   help="dump text of every slide as a list")
    p.add_argument("--max-chars", type=int, default=20000)

    p = sub.add_parser("find-slide",
                       help="Return first slide whose title or any text frame matches --regex.")
    p.add_argument("file")
    p.add_argument("--regex", required=True)
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--title-only", action="store_true",
                   help="search only the slide title (first text frame), not body text")

    p = sub.add_parser("count-images",
                       help="Total picture/chart shape count (optionally per-slide).")
    p.add_argument("file")
    p.add_argument("--per-slide", action="store_true",
                   help="also emit a per-slide list of {slide, n_pictures, n_charts}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open(path: str):
    pptx = C.lazy_import("pptx")
    abs_path = C.require_file(path, _PPTX_EXTS)
    try:
        return pptx.Presentation(abs_path), abs_path
    except Exception as e:
        raise C.VerifierError(C.ErrCode.PARSE_ERROR,
                              f"pptx.Presentation({abs_path}) failed: {e}") from e


# python-pptx shape type enum values we care about. We import lazily (inside
# helper) so that the module file itself stays import-error-free when the
# dependency is missing — `cmd_*` will surface DEP_MISSING on first call.
def _shape_kinds(slide) -> dict:
    """Return a dict of shape-kind counts and a best-effort title string."""
    pptx_enum = C.lazy_import("pptx.enum.shapes")
    MSO = pptx_enum.MSO_SHAPE_TYPE  # noqa: N806

    n_picture = 0
    n_chart = 0
    n_table = 0
    n_text = 0
    n_other = 0
    title = None

    for shape in slide.shapes:
        try:
            stype = shape.shape_type
        except Exception:
            stype = None
        if stype == MSO.PICTURE:
            n_picture += 1
        elif getattr(shape, "has_chart", False):
            n_chart += 1
        elif getattr(shape, "has_table", False):
            n_table += 1
        elif getattr(shape, "has_text_frame", False):
            n_text += 1
        else:
            n_other += 1

    # Best-effort title detection: prefer the explicit title placeholder, then
    # fall back to the first text frame on the slide.
    try:
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            t = slide.shapes.title.text_frame.text or ""
            if t.strip():
                title = t.strip()
    except Exception:
        pass
    if title is None:
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                t = shape.text_frame.text or ""
                if t.strip():
                    title = t.strip().splitlines()[0]
                    break

    return {
        "title": title,
        "n_shapes": len(slide.shapes),
        "n_pictures": n_picture,
        "n_charts": n_chart,
        "n_tables": n_table,
        "n_text_frames": n_text,
        "n_other": n_other,
        "has_picture": n_picture > 0,
        "has_chart": n_chart > 0,
        "has_table": n_table > 0,
    }


def _slide_text(slide) -> str:
    """Concatenate all text-frame text on a slide, plus any table cell text."""
    parts: list[str] = []
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            t = shape.text_frame.text
            if t:
                parts.append(t)
        if getattr(shape, "has_table", False):
            for row in shape.table.rows:
                cells_text = []
                for cell in row.cells:
                    cells_text.append(cell.text_frame.text if cell.text_frame else "")
                parts.append("\t".join(cells_text))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# list-slides
# ---------------------------------------------------------------------------

def cmd_list_slides(args: argparse.Namespace) -> dict:
    pres, abs_path = _open(args.file)
    slides: list[dict] = []
    for i, slide in enumerate(pres.slides):
        meta = _shape_kinds(slide)
        meta["index"] = i + 1
        slides.append(meta)
    return {
        "file": abs_path,
        "slide_count": len(slides),
        "slides": slides,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{len(slides)} slides; "
                                + ", ".join(f"#{s['index']}({(s['title'] or '<no-title>')[:30]!r})"
                                            for s in slides[:6])
                                + (" ..." if len(slides) > 6 else "")),
    }


# ---------------------------------------------------------------------------
# slide-text
# ---------------------------------------------------------------------------

def cmd_slide_text(args: argparse.Namespace) -> dict:
    if args.slide is None and not args.all:
        raise C.VerifierError(C.ErrCode.BAD_ARGS,
                              "either --slide N or --all is required")
    if args.slide is not None and args.all:
        raise C.VerifierError(C.ErrCode.BAD_ARGS,
                              "--slide and --all are mutually exclusive")

    pres, abs_path = _open(args.file)
    n = len(pres.slides)

    if args.slide is not None:
        if args.slide < 1 or args.slide > n:
            raise C.VerifierError(C.ErrCode.NOT_FOUND,
                                  f"slide {args.slide} out of range (deck has {n} slides)")
        text = _slide_text(pres.slides[args.slide - 1])
        truncated = len(text) > args.max_chars
        if truncated:
            text = text[: args.max_chars]
        return {
            "file": abs_path, "slide": args.slide, "slide_count": n,
            "char_count": len(text), "truncated": truncated, "text": text,
            "_evidence": C.evidence(file=abs_path,
                                    locator={"slide": args.slide},
                                    quote=f"slide {args.slide}/{n}: {len(text)} chars"
                                    + (" (truncated)" if truncated else "")),
        }

    # --all: emit a list (still respect max-chars budget)
    items: list[dict] = []
    used = 0
    truncated = False
    for i, slide in enumerate(pres.slides):
        t = _slide_text(slide)
        items.append({"slide": i + 1, "char_count": len(t), "text": t})
        used += len(t)
        if used > args.max_chars:
            truncated = True
            # crop trailing item to fit budget
            overflow = used - args.max_chars
            items[-1]["text"] = items[-1]["text"][: max(0, len(items[-1]["text"]) - overflow)]
            items[-1]["char_count"] = len(items[-1]["text"])
            items[-1]["truncated"] = True
            break
    return {
        "file": abs_path, "slide_count": n,
        "slides": items, "truncated": truncated,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"{n} slides; total {sum(i['char_count'] for i in items)} chars"
                                + (" (truncated)" if truncated else "")),
    }


# ---------------------------------------------------------------------------
# find-slide
# ---------------------------------------------------------------------------

def cmd_find_slide(args: argparse.Namespace) -> dict:
    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        rx = re.compile(args.regex, flags)
    except re.error as e:
        raise C.VerifierError(C.ErrCode.BAD_ARGS, f"invalid regex: {e}") from e

    pres, abs_path = _open(args.file)
    for i, slide in enumerate(pres.slides):
        meta = _shape_kinds(slide)
        if args.title_only:
            haystack = meta["title"] or ""
        else:
            haystack = (meta["title"] or "") + "\n" + _slide_text(slide)
        m = rx.search(haystack)
        if m:
            return {
                "file": abs_path, "regex": args.regex,
                "found": True, "slide": i + 1, "title": meta["title"],
                "matched_text": m.group(0)[:120],
                "_evidence": C.evidence(file=abs_path,
                                        locator={"slide": i + 1},
                                        quote=f"slide {i + 1} matches: {m.group(0)[:80]!r} "
                                        f"(title={meta['title']!r})"),
            }
    return {
        "file": abs_path, "regex": args.regex,
        "found": False, "slide_count": len(pres.slides),
        "_evidence": C.evidence(file=abs_path,
                                locator={"regex": args.regex},
                                quote=f"no slide matches /{args.regex}/ across {len(pres.slides)} slides"),
    }


# ---------------------------------------------------------------------------
# count-images
# ---------------------------------------------------------------------------

def cmd_count_images(args: argparse.Namespace) -> dict:
    pres, abs_path = _open(args.file)
    total_pic = 0
    total_chart = 0
    per_slide: list[dict] = []
    for i, slide in enumerate(pres.slides):
        meta = _shape_kinds(slide)
        total_pic += meta["n_pictures"]
        total_chart += meta["n_charts"]
        if args.per_slide:
            per_slide.append({
                "slide": i + 1,
                "n_pictures": meta["n_pictures"],
                "n_charts": meta["n_charts"],
            })
    out = {
        "file": abs_path, "slide_count": len(pres.slides),
        "n_pictures": total_pic, "n_charts": total_chart,
        "_evidence": C.evidence(file=abs_path,
                                quote=f"pictures={total_pic}, charts={total_chart} "
                                f"across {len(pres.slides)} slides"),
    }
    if args.per_slide:
        out["per_slide"] = per_slide
    return out
