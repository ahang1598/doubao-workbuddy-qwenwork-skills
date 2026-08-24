#!/usr/bin/env python3
"""
batch_ops.py — PDF Structural Editing

Handles merge, split, rotate, reorder, watermark, text-watermark, and split-by-bookmarks operations.
All operations are lossless (no re-rendering of page content).

Usage:
    # Merge multiple PDFs
    python scripts/batch_ops.py --action merge \
        --inputs a.pdf b.pdf c.pdf --output merged.pdf

    # Split into individual pages
    python scripts/batch_ops.py --action split \
        --input book.pdf --output-dir pages/

    # Split into chunks of N pages
    python scripts/batch_ops.py --action split \
        --input book.pdf --pages-per-chunk 10 --output-dir parts/

    # Extract specific pages into a single output PDF
    python scripts/batch_ops.py --action split \
        --input book.pdf --pages 3-5 --output extracted.pdf

    # Extract non-contiguous pages into a single output PDF
    python scripts/batch_ops.py --action split \
        --input book.pdf --pages 1,3,7-9 --output selected.pdf

    # Split by bookmarks (one PDF per top-level bookmark).
    # Pages before the first bookmark (cover/foreword/TOC) go into
    # 000_preamble.pdf so the split is lossless. Use --no-preamble to drop them.
    python scripts/batch_ops.py --action split-by-bookmarks \
        --input book.pdf --output-dir chapters/

    # Rotate specific pages (1-indexed, comma-separated or range)
    python scripts/batch_ops.py --action rotate \
        --input doc.pdf --pages 1,3,5-7 --degrees 90 --output rotated.pdf

    # Apply a watermark PDF overlay to all pages
    python scripts/batch_ops.py --action watermark \
        --input doc.pdf --watermark stamp.pdf --output watermarked.pdf

    # Add a text watermark (supports CJK characters)
    python scripts/batch_ops.py --action text-watermark \
        --input doc.pdf --text "机密" --output watermarked.pdf

    # Reorder pages
    python scripts/batch_ops.py --action reorder \
        --input doc.pdf --order 3,1,2,4 --output reordered.pdf
"""

import argparse
import sys
from pathlib import Path


def _parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """
    Parse a page specification string into a sorted list of 0-based indices.
    Supports: "1,3,5-7" (1-based, inclusive ranges).
    """
    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s.strip()), int(hi_s.strip())
            for p in range(lo, hi + 1):
                if 1 <= p <= total_pages:
                    indices.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                indices.add(p - 1)
    return sorted(indices)


def action_merge(inputs: list[Path], output: Path) -> None:
    from pypdf import PdfWriter, PdfReader

    composer = PdfWriter()
    total_pages = 0
    for src in inputs:
        reader = PdfReader(str(src))
        page_count = len(reader.pages)
        total_pages += page_count
        for page in reader.pages:
            composer.add_page(page)
    with open(output, "wb") as fh:
        composer.write(fh)
    print(f"Merged {len(inputs)} files ({total_pages} pages total) → {output}")


def action_split(
    input_pdf: Path,
    output_dir: Path,
    pages_per_chunk: int,
    page_spec=None,
    single_output=None,
) -> None:
    """
    Split a PDF into chunks, or extract specific pages.

    When `page_spec` is provided:
    - If `single_output` is also given, all matching pages are written to that
      single output file (useful for extracting a subset of pages).
    - Otherwise, each matching page is written to its own file in `output_dir`.

    When `page_spec` is not provided, the PDF is split into chunks of
    `pages_per_chunk` pages and written to `output_dir`.
    """
    from pypdf import PdfWriter, PdfReader

    reader = PdfReader(str(input_pdf))
    total = len(reader.pages)
    stem = input_pdf.stem

    if page_spec:
        target_indices = _parse_page_spec(page_spec, total)
        if not target_indices:
            print(f"Error: page spec '{page_spec}' matched no pages (total: {total})", file=sys.stderr)
            sys.exit(1)

        if single_output:
            # All selected pages → one output file
            extractor = PdfWriter()
            for idx in target_indices:
                extractor.add_page(reader.pages[idx])
            single_output.parent.mkdir(parents=True, exist_ok=True)
            with open(single_output, "wb") as fh:
                extractor.write(fh)
            print(f"Extracted pages {page_spec} ({len(target_indices)} page(s)) → {single_output}")
        else:
            # Each selected page → its own file in output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            for rank, idx in enumerate(target_indices, start=1):
                page_file = output_dir / f"{stem}_page{idx + 1:03d}.pdf"
                splitter = PdfWriter()
                splitter.add_page(reader.pages[idx])
                with open(page_file, "wb") as fh:
                    splitter.write(fh)
            print(f"Extracted {len(target_indices)} page(s) from '{page_spec}' → {output_dir}/")
        return

    # Default: chunk-based split
    output_dir.mkdir(parents=True, exist_ok=True)
    if pages_per_chunk <= 0:
        pages_per_chunk = 1

    chunk_idx = 1
    for start in range(0, total, pages_per_chunk):
        end = min(start + pages_per_chunk, total)
        splitter = PdfWriter()
        for page_idx in range(start, end):
            splitter.add_page(reader.pages[page_idx])
        chunk_name = output_dir / f"{stem}_part{chunk_idx:03d}.pdf"
        with open(chunk_name, "wb") as fh:
            splitter.write(fh)
        chunk_idx += 1

    print(f"Split {total} pages into {chunk_idx - 1} chunk(s) in {output_dir}/")


def _flatten_bookmarks(outline, reader) -> list[dict]:
    """
    Recursively flatten a nested PDF outline into a sorted list of
    {"title": str, "page": int (0-based)} dicts.
    """
    results: list[dict] = []
    for item in outline:
        if isinstance(item, list):
            results.extend(_flatten_bookmarks(item, reader))
        else:
            try:
                page_num = reader.get_destination_page_number(item)
                results.append({"title": item.title, "page": page_num})
            except Exception:
                continue
    results.sort(key=lambda x: x["page"])
    return results


def action_split_by_bookmarks(
    input_pdf: Path,
    output_dir: Path,
    level: int = 1,
    include_preamble: bool = True,
) -> None:
    """
    Split a PDF at top-level bookmark boundaries.

    Each bookmark defines the start of a section; the section runs until the
    next bookmark (or end of document). Output files are named using the
    bookmark title (sanitised for filesystem safety).

    Pages located *before* the first bookmark (typically cover, foreword,
    or table-of-contents pages) are NOT part of any chapter. By default
    they are written to a separate ``000_preamble.pdf`` so the split is
    lossless and the source PDF's total page count is preserved across
    the output set. Pass ``include_preamble=False`` to discard them
    (matches the legacy behaviour of strict by-chapter splitting).

    `level` controls which outline depth to split on:
      - 1 (default): split on top-level bookmarks only
      - 2: include second-level bookmarks as split points too
      - etc.
    """
    from pypdf import PdfWriter, PdfReader

    reader = PdfReader(str(input_pdf))
    total = len(reader.pages)
    outline = reader.outline

    if not outline:
        print("Error: PDF has no bookmarks/outline to split on.", file=sys.stderr)
        sys.exit(1)

    flat = _flatten_bookmarks(outline, reader)
    if not flat:
        print("Error: could not resolve any bookmark destinations.", file=sys.stderr)
        sys.exit(1)

    # Filter by level if the bookmarks carry nesting info.
    # _flatten_bookmarks flattens everything; for level filtering we re-walk.
    if level == 1:
        top_level: list[dict] = []
        for item in outline:
            if not isinstance(item, list):
                try:
                    page_num = reader.get_destination_page_number(item)
                    top_level.append({"title": item.title, "page": page_num})
                except Exception:
                    continue
        if top_level:
            flat = sorted(top_level, key=lambda x: x["page"])

    # Deduplicate bookmarks pointing to the same page (keep first)
    seen_pages: set[int] = set()
    deduped: list[dict] = []
    for entry in flat:
        if entry["page"] not in seen_pages:
            seen_pages.add(entry["page"])
            deduped.append(entry)
    flat = deduped

    output_dir.mkdir(parents=True, exist_ok=True)

    def _safe_filename(title: str, idx: int) -> str:
        sanitised = "".join(c if c.isalnum() or c in " _-" else "_" for c in title).strip()
        if not sanitised:
            sanitised = f"section_{idx}"
        return f"{idx:03d}_{sanitised}.pdf"

    written_files = 0
    pages_written = 0

    # Preamble: pages before the first bookmark (cover/foreword/TOC).
    # Without this, those pages would be silently dropped — a real
    # data-loss bug for users running "split by chapter" on annual
    # reports, books, or any PDF where chapter 1 doesn't start on page 1.
    first_chapter_start = flat[0]["page"]
    if include_preamble and first_chapter_start > 0:
        preamble_writer = PdfWriter()
        for page_idx in range(0, first_chapter_start):
            preamble_writer.add_page(reader.pages[page_idx])
        preamble_file = output_dir / "000_preamble.pdf"
        with open(preamble_file, "wb") as fh:
            preamble_writer.write(fh)
        written_files += 1
        pages_written += first_chapter_start
        print(
            f"  preamble: {first_chapter_start} page(s) before first chapter → "
            f"{preamble_file.name}"
        )

    for i, bookmark in enumerate(flat):
        start_page = bookmark["page"]
        end_page = flat[i + 1]["page"] if i + 1 < len(flat) else total

        if start_page >= end_page:
            # Empty section: malformed outline, two bookmarks pointing at the
            # same page after dedup, or a bookmark past EOF. Skip it but log
            # so users know which chapter was dropped.
            print(
                f"  warning: skipping empty section '{bookmark['title']}' "
                f"(start_page={start_page + 1}, end_page={end_page})",
                file=sys.stderr,
            )
            continue

        writer = PdfWriter()
        for page_idx in range(start_page, end_page):
            writer.add_page(reader.pages[page_idx])

        out_file = output_dir / _safe_filename(bookmark["title"], i + 1)
        with open(out_file, "wb") as fh:
            writer.write(fh)
        written_files += 1
        pages_written += end_page - start_page

    coverage_note = ""
    if pages_written < total:
        missing = total - pages_written
        if not include_preamble and first_chapter_start > 0:
            hint = " (drop --no-preamble to keep cover/foreword/TOC pages)"
        else:
            hint = " (likely caused by empty/duplicate bookmark sections)"
        coverage_note = f" (warning: {missing} page(s) not covered by any output file{hint})"
    print(
        f"Split into {written_files} file(s) by bookmarks "
        f"({pages_written}/{total} pages) → {output_dir}/{coverage_note}"
    )


def action_rotate(input_pdf: Path, page_spec: str, degrees: int, output: Path) -> None:
    from pypdf import PdfWriter, PdfReader

    reader = PdfReader(str(input_pdf))
    total = len(reader.pages)
    target_indices = _parse_page_spec(page_spec, total) if page_spec else list(range(total))

    rotator = PdfWriter()
    for idx, page in enumerate(reader.pages):
        if idx in target_indices:
            page.rotate(degrees)
        rotator.add_page(page)
    with open(output, "wb") as fh:
        rotator.write(fh)
    print(f"Rotated pages {page_spec or 'all'} by {degrees}° → {output}")


def action_watermark(input_pdf: Path, watermark_pdf: Path, output: Path) -> None:
    from pypdf import PdfWriter, PdfReader

    reader = PdfReader(str(input_pdf))
    stamp_reader = PdfReader(str(watermark_pdf))
    stamp_page = stamp_reader.pages[0]

    stamper = PdfWriter()
    for page in reader.pages:
        page.merge_page(stamp_page)
        stamper.add_page(page)
    with open(output, "wb") as fh:
        stamper.write(fh)
    print(f"Watermark applied → {output}")


def _resolve_watermark_font(text: str) -> str:
    """Pick the best available font for *text*, with CJK auto-detection.

    Returns a ReportLab font name.  Exits with a clear error message when
    CJK text is requested but no CJK font can be found — producing a PDF
    with blank-box watermarks is worse than stopping early.
    """
    # Lazy import: _fonts lives next to this script
    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from _fonts import contains_cjk, register_cjk_font

    if not contains_cjk(text):
        # Base-14 fonts are not embedded. Some independent renderers do not
        # substitute them, which leaves a valid text stream that renders as a
        # blank page. ReportLab ships Bitstream Vera, so use that deterministic
        # local asset and embed its subset in every watermark output.
        try:
            import reportlab
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError as exc:
            raise RuntimeError(
                "reportlab is required for text watermarks; install it with: pip install reportlab"
            ) from exc
        font_name = "QWWatermarkLatin"
        try:
            pdfmetrics.getFont(font_name)
        except KeyError:
            font_path = Path(reportlab.__file__).resolve().parent / "fonts" / "VeraBd.ttf"
            if not font_path.is_file():
                raise RuntimeError("reportlab's embedded Latin watermark font is unavailable")
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        return font_name

    result = register_cjk_font()
    if result.ok:
        return result.bold_family or result.family

    # CJK text but no font → fail fast with an actionable message.
    print(
        f"Error: watermark text contains CJK characters but no CJK font "
        f"was found on this system. {result.reason}\n"
        "Hint: set WUKONG_CJK_FONT=/path/to/font.ttf to override.",
        file=sys.stderr,
    )
    sys.exit(1)


def _build_text_watermark_page(
    text: str,
    page_width: float,
    page_height: float,
    font_name: str,
    font_size: float = 54,
    opacity: float = 0.15,
    angle: float = 45,
) -> bytes:
    """Generate a single-page PDF with repeated diagonal text watermarks.

    Uses ReportLab to draw semi-transparent rotated text across the entire
    page area.  The caller is responsible for resolving *font_name* via
    :func:`_resolve_watermark_font` so that CJK glyphs are covered.

    Returns raw PDF bytes suitable for ``io.BytesIO`` → pypdf merge.
    """
    import io
    import math

    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        print(
            "Error: reportlab is required for text watermarks but is not "
            "installed. Run: pip install reportlab",
            file=sys.stderr,
        )
        sys.exit(1)

    buf = io.BytesIO()
    watermark_canvas = canvas.Canvas(buf, pagesize=(page_width, page_height))
    watermark_canvas.saveState()

    watermark_canvas.setFillAlpha(opacity)
    watermark_canvas.setFillColorRGB(0.5, 0.5, 0.5)
    watermark_canvas.setFont(font_name, font_size)

    # Move origin to page centre, then rotate
    watermark_canvas.translate(page_width / 2, page_height / 2)
    watermark_canvas.rotate(angle)

    # Tile watermark text along the rotated axis to cover the full page.
    # The diagonal is the worst-case span we need to fill.
    diagonal = math.sqrt(page_width ** 2 + page_height ** 2)
    spacing = font_size * 4
    repetitions = int(diagonal / spacing) + 1
    for i in range(-repetitions, repetitions + 1):
        offset_y = i * spacing
        watermark_canvas.drawCentredString(0, offset_y - font_size / 3, text)

    watermark_canvas.restoreState()
    watermark_canvas.save()
    return buf.getvalue()


def _get_visual_page_size(page) -> tuple[float, float]:
    """Return the (width, height) a PDF viewer would actually display.

    Pages with a ``/Rotate`` attribute of 90 or 270 are visually swapped
    compared to their raw ``mediabox`` dimensions.  When we overlay a
    watermark we must match the *visual* orientation so the text appears
    at the correct angle.
    """
    media = page.mediabox
    raw_width = float(media.width)
    raw_height = float(media.height)
    rotation = int(page.get("/Rotate") or 0) % 360
    if rotation in (90, 270):
        return raw_height, raw_width
    return raw_width, raw_height


def action_text_watermark(
    input_pdf: Path,
    text: str,
    output: Path,
    font_size: float = 54,
    opacity: float = 0.15,
    angle: float = 45,
) -> None:
    """Add a text watermark to every page of a PDF.

    Generates a per-page watermark overlay (sized to match each page's
    visual dimensions, accounting for ``/Rotate``) and merges it onto
    every page.  CJK text is handled automatically via ``_fonts``.
    """
    import io

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(input_pdf))

    # Resolve font once — register_cjk_font is idempotent.
    font_name = _resolve_watermark_font(text)

    writer = PdfWriter()
    for page in reader.pages:
        visual_width, visual_height = _get_visual_page_size(page)

        watermark_bytes = _build_text_watermark_page(
            text, visual_width, visual_height, font_name,
            font_size, opacity, angle,
        )
        stamp_reader = PdfReader(io.BytesIO(watermark_bytes))
        stamp_page = stamp_reader.pages[0]

        # If the source page is rotated, counter-rotate the watermark
        # overlay so it renders upright in the viewer.
        rotation = int(page.get("/Rotate") or 0) % 360
        if rotation:
            stamp_page.rotate(rotation)

        page.merge_page(stamp_page)
        writer.add_page(page)

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as fh:
        writer.write(fh)
    print(f"Text watermark '{text}' applied to {len(reader.pages)} page(s) → {output}")


def action_reorder(input_pdf: Path, order_spec: str, output: Path) -> None:
    from pypdf import PdfWriter, PdfReader

    reader = PdfReader(str(input_pdf))
    total = len(reader.pages)
    new_order = [int(x.strip()) - 1 for x in order_spec.split(",")]

    invalid = [i for i in new_order if not (0 <= i < total)]
    if invalid:
        print(f"Error: page numbers out of range: {[i+1 for i in invalid]}", file=sys.stderr)
        sys.exit(1)

    arranger = PdfWriter()
    for idx in new_order:
        arranger.add_page(reader.pages[idx])
    with open(output, "wb") as fh:
        arranger.write(fh)
    print(f"Reordered {total} pages → {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lossless PDF structural editing.")
    parser.add_argument("--action", required=True,
                        choices=["merge", "split", "split-by-bookmarks", "rotate",
                                 "watermark", "text-watermark", "reorder"])

    # Shared
    parser.add_argument("--output", help="Output PDF file path")
    parser.add_argument("--output-dir", help="Output directory (used by split)")

    # Merge
    parser.add_argument("--inputs", nargs="+", help="Input PDFs for merge")

    # Split / common single-input
    parser.add_argument("--input", help="Input PDF file")
    parser.add_argument("--pages-per-chunk", type=int, default=1,
                        help="Pages per chunk when splitting (default: 1)")

    # Page-selection spec, shared by rotate and split-by-pages
    parser.add_argument("--pages",
                        help="Page spec, e.g. '1,3,5-7' or 'all'. "
                             "Used by --action rotate (pages to rotate) and "
                             "--action split (pages to extract; pair with "
                             "--output for single-file extraction).")
    parser.add_argument("--degrees", type=int, default=90, choices=[90, 180, 270],
                        help="Rotation degrees (default: 90)")

    # Watermark (PDF overlay)
    parser.add_argument("--watermark", help="Watermark PDF path")

    # Text watermark
    parser.add_argument("--text", help="Watermark text (supports CJK)")
    parser.add_argument("--font-size", type=float, default=54,
                        help="Watermark font size in points (default: 54)")
    parser.add_argument("--opacity", type=float, default=0.15,
                        help="Watermark opacity 0.0-1.0 (default: 0.15)")
    parser.add_argument("--angle", type=float, default=45,
                        help="Watermark rotation angle in degrees (default: 45)")

    # Split by bookmarks
    parser.add_argument("--bookmark-level", type=int, default=1,
                        help="Outline depth to split on (default: 1 = top-level bookmarks)")
    parser.add_argument("--no-preamble", action="store_true",
                        help="Drop pages before the first bookmark instead of "
                             "writing them to 000_preamble.pdf (default: keep)")

    # Reorder
    parser.add_argument("--order", help="New page order as comma-separated 1-based indices")

    args = parser.parse_args()

    try:
        if args.action == "merge":
            if not args.inputs or not args.output:
                parser.error("--inputs and --output required for merge")
            action_merge([Path(f) for f in args.inputs], Path(args.output))

        elif args.action == "split":
            if not args.input:
                parser.error("--input required for split")
            out_dir = Path(args.output_dir) if args.output_dir else Path(args.input).parent
            single_output = Path(args.output) if args.output else None
            action_split(Path(args.input), out_dir, args.pages_per_chunk, args.pages, single_output)

        elif args.action == "split-by-bookmarks":
            if not args.input:
                parser.error("--input required for split-by-bookmarks")
            out_dir = Path(args.output_dir) if args.output_dir else Path(args.input).parent
            action_split_by_bookmarks(
                Path(args.input), out_dir, args.bookmark_level,
                include_preamble=not args.no_preamble,
            )

        elif args.action == "rotate":
            if not args.input or not args.output:
                parser.error("--input and --output required for rotate")
            action_rotate(Path(args.input), args.pages, args.degrees, Path(args.output))

        elif args.action == "watermark":
            if not args.input or not args.watermark or not args.output:
                parser.error("--input, --watermark, and --output required")
            action_watermark(Path(args.input), Path(args.watermark), Path(args.output))

        elif args.action == "text-watermark":
            if not args.input or not args.text or not args.output:
                parser.error("--input, --text, and --output required for text-watermark")
            action_text_watermark(
                Path(args.input), args.text, Path(args.output),
                font_size=args.font_size, opacity=args.opacity, angle=args.angle,
            )

        elif args.action == "reorder":
            if not args.input or not args.order or not args.output:
                parser.error("--input, --order, and --output required for reorder")
            action_reorder(Path(args.input), args.order, Path(args.output))

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
