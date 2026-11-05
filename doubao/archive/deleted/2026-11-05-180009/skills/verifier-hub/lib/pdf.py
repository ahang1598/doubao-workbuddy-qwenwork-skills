"""pdf — PDF inspection (read-only).

4 subcommands
-------------
pages          page_count, per-page width/height + orientation (landscape/portrait).
text-dump      extract text from all (or a page-range) pages.
cjk-check      whether the PDF embeds CJK-capable fonts; useful for "中文乱码" rubric.
count-images   count embedded image XObjects across the document (or per page).

All four go through ``lib/_pdf_backend.open_pdf``, which picks the first
available reader (pymupdf, then pdfplumber, then pypdf). Every result carries
a ``backend`` field so a surprising number can be traced to the reader that
produced it.
"""
from __future__ import annotations

import argparse

from . import _common as C
from . import _pdf_backend as B


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("pages", help="page count + per-page dimensions + orientation.")
    p.add_argument("file")
    p.add_argument("--expect-orientation", choices=("portrait", "landscape"), default=None,
                   help="if set, ALL pages must match this orientation to pass")
    p.add_argument("--min-pages", type=int, default=None)
    p.add_argument("--max-pages", type=int, default=None)

    p = sub.add_parser("text-dump", help="extract text from a page range.")
    p.add_argument("file")
    p.add_argument("--start", type=int, default=1, help="1-based, inclusive")
    p.add_argument("--end", type=int, default=None, help="1-based, inclusive (default: last page)")
    p.add_argument("--max-chars", type=int, default=20000)

    p = sub.add_parser("cjk-check",
                       help="check whether PDF embeds CJK-capable fonts (proxy for 中文渲染正确).")
    p.add_argument("file")
    p.add_argument("--sample-pages", type=int, default=3,
                   help="how many pages to sample for actual text inspection")

    p = sub.add_parser("count-images",
                       help="count embedded image XObjects across the document (or per page).")
    p.add_argument("file")
    p.add_argument("--per-page", action="store_true",
                   help="also emit a per-page count list (capped at 50 pages)")
    p.add_argument("--min", type=int, default=None,
                   help="optional lower bound to assert on")


_GEOMETRY_SAMPLE_CAP = 50


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

def cmd_pages(args: argparse.Namespace) -> dict:
    with B.open_pdf(args.file) as doc:
        abs_path = doc.path
        n = doc.page_count
        pages_info = []
        for i in range(min(n, _GEOMETRY_SAMPLE_CAP)):
            w, h = doc.page_size(i)
            pages_info.append({
                "page": i + 1,
                "width": w,
                "height": h,
                "orientation": "landscape" if w > h else "portrait",
            })

        checks: list[dict] = []
        if args.min_pages is not None:
            checks.append({"check": "min_pages", "expected": args.min_pages,
                           "actual": n, "passed": n >= args.min_pages})
        if args.max_pages is not None:
            checks.append({"check": "max_pages", "expected": args.max_pages,
                           "actual": n, "passed": n <= args.max_pages})
        if args.expect_orientation is not None:
            # Orientation must hold for EVERY page, so scan past the sample cap.
            all_orient = [p["orientation"] for p in pages_info]
            for i in range(len(pages_info), n):
                all_orient.append(doc.orientation(i))
            mismatched = [i + 1 for i, o in enumerate(all_orient)
                          if o != args.expect_orientation]
            checks.append({
                "check": "orientation",
                "expected": args.expect_orientation,
                "actual_unique": sorted(set(all_orient)),
                "mismatched_pages": mismatched[:10],
                "passed": not mismatched,
            })
        backend = doc.backend

    overall: bool | None = all(c["passed"] for c in checks) if checks else None
    return {
        "file": abs_path, "page_count": n,
        "pages_sample": pages_info,
        "checks": checks, "passed": overall,
        "backend": backend,
        "_evidence": C.evidence(
            file=abs_path,
            quote=f"page_count={n}"
            + (f"; first: {pages_info[0]['width']:.0f}×{pages_info[0]['height']:.0f} "
               f"({pages_info[0]['orientation']})" if pages_info else "")
            + ("; checks: " + ", ".join(f"{c['check']}={c['passed']}" for c in checks)
               if checks else ""),
        ),
    }


# ---------------------------------------------------------------------------
# text-dump
# ---------------------------------------------------------------------------

def cmd_text_dump(args: argparse.Namespace) -> dict:
    with B.open_pdf(args.file) as doc:
        abs_path = doc.path
        n = doc.page_count
        start = max(1, args.start)
        end = n if args.end is None else min(n, args.end)
        if start > end:
            raise C.VerifierError(C.ErrCode.BAD_ARGS,
                                  f"invalid range: start={start} > end={end} (pages={n})")
        parts: list[str] = []
        for i in range(start - 1, end):
            parts.append(f"# page {i + 1}")
            parts.append(doc.page_text(i))
            if sum(len(p) for p in parts) > args.max_chars:
                break
        backend = doc.backend

    text = "\n".join(parts)
    truncated = len(text) > args.max_chars
    if truncated:
        text = text[: args.max_chars]
    return {
        "file": abs_path, "page_count": n,
        "start": start, "end": end,
        "char_count": len(text), "truncated": truncated, "text": text,
        "backend": backend,
        "_evidence": C.evidence(file=abs_path,
                                locator={"pages": f"{start}-{end}"},
                                quote=f"{end - start + 1} pages, {len(text)} chars"
                                + (" (truncated)" if truncated else "")),
    }


# ---------------------------------------------------------------------------
# cjk-check
# ---------------------------------------------------------------------------

def cmd_cjk_check(args: argparse.Namespace) -> dict:
    """Two independent signals:

    1. Embedded fonts — any /BaseFont whose name matches a known CJK family.
    2. Sampled text — CJK codepoints actually extractable from the first N pages.

    A document that "should be Chinese" but yields almost no CJK characters
    usually shipped rasterised text or an incomplete font subset.
    """
    with B.open_pdf(args.file) as doc:
        abs_path = doc.path
        n = doc.page_count
        cjk_font_names: list[str] = []
        for i in range(n):
            for name in doc.page_fonts(i):
                if B.is_cjk_font(name):
                    cjk_font_names.append(name)

        sample_n = min(max(0, args.sample_pages), n)
        cjk_chars = 0
        sampled_chars = 0
        for i in range(sample_n):
            txt = doc.page_text(i)
            sampled_chars += len(txt)
            cjk_chars += sum(1 for c in txt if "\u4e00" <= c <= "\u9fff")
        backend = doc.backend

    has_cjk_text = cjk_chars > 0
    has_cjk_font = bool(cjk_font_names)
    return {
        "file": abs_path,
        "has_cjk_font": has_cjk_font,
        "cjk_font_names": sorted(set(cjk_font_names))[:10],
        "sampled_pages": sample_n,
        "sampled_total_chars": sampled_chars,
        "cjk_chars_in_sample": cjk_chars,
        "has_cjk_text": has_cjk_text,
        "backend": backend,
        "_evidence": C.evidence(
            file=abs_path,
            quote=f"cjk_font={has_cjk_font} ({len(set(cjk_font_names))} fonts), "
                  f"cjk_text={has_cjk_text} ({cjk_chars}/{sampled_chars} "
                  f"in {sample_n} pages)"),
    }


# ---------------------------------------------------------------------------
# count-images
# ---------------------------------------------------------------------------

def cmd_count_images(args: argparse.Namespace) -> dict:
    with B.open_pdf(args.file) as doc:
        abs_path = doc.path
        n = doc.page_count
        total = 0
        per_page: list[dict] = []
        for i in range(n):
            k = doc.page_image_count(i)
            total += k
            if args.per_page and i < 50:
                per_page.append({"page": i + 1, "n_images": k})
        backend = doc.backend

    passed: bool | None = None
    if args.min is not None:
        passed = total >= args.min

    out = {
        "file": abs_path,
        "page_count": n,
        "n_images": total,
        "passed": passed,
        "backend": backend,
        "_evidence": C.evidence(
            file=abs_path,
            quote=f"images={total} across {n} pages"
            + (f"; min={args.min}: {'OK' if passed else 'FAIL'}"
               if args.min is not None else ""),
        ),
    }
    if args.per_page:
        out["per_page"] = per_page
    return out
