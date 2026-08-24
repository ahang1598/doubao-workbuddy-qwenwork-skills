#!/usr/bin/env python3
"""
crop_compose.py — PDF Content-Aware Crop & N-up Composition

Detects content boundaries on PDF pages, crops to the content region,
and composes multiple cropped regions onto new pages.

Uses PyMuPDF (fitz) for both content detection (structural analysis)
and composition (Form XObject with /BBox clipping — true PDF-level crop,
not viewer-hint cropbox).

Usage:
    # Auto-detect content, crop, and compose vertically on A4
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf --output merged.pdf

    # Horizontal layout
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf --output merged.pdf --layout horizontal

    # Grid layout (auto rows × cols)
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf d.pdf --output merged.pdf --layout grid

    # Manual crop box (skip auto-detection)
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf --output merged.pdf \\
        --crop 0,0,595,280

    # Specific pages from each input
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf --pages 1 1 1 --output merged.pdf

    # Multiple pages from a single file
    python scripts/crop_compose.py \\
        --input multi.pdf --pages 1-3 --output composed.pdf

    # Custom page size, margins, and gap
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf --output merged.pdf \\
        --page-size letter --margin 20 --gap 10

    # Per-page capacity (e.g. fit exactly 3 per page)
    python scripts/crop_compose.py \\
        --inputs a.pdf b.pdf c.pdf d.pdf e.pdf f.pdf \\
        --output merged.pdf --per-page 3
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    fitz = None


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


PAGE_SIZES = (
    {
        "a4": fitz.paper_rect("a4"),
        "a3": fitz.paper_rect("a3"),
        "letter": fitz.paper_rect("letter"),
        "legal": fitz.paper_rect("legal"),
    }
    if fitz is not None
    else {"a4": None, "a3": None, "letter": None, "legal": None}
)


def _is_background_rect(rect: fitz.Rect, page_rect: fitz.Rect,
                        threshold: float = 0.9) -> bool:
    """True if *rect* covers ≥ threshold of the page in both dimensions."""
    if page_rect.width <= 0 or page_rect.height <= 0:
        return False
    w_ratio = rect.width / page_rect.width
    h_ratio = rect.height / page_rect.height
    return w_ratio >= threshold and h_ratio >= threshold


def _render_content_bbox(page: fitz.Page, margin: float = 5.0) -> fitz.Rect | None:
    """Fallback: render page to bitmap and find non-white pixel bounds."""
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5), alpha=False)
        img_data = pix.samples
        w, h, n = pix.width, pix.height, pix.n

        min_x, min_y, max_x, max_y = w, h, 0, 0
        threshold = 250
        for y in range(h):
            row_start = y * w * n
            for x in range(w):
                offset = row_start + x * n
                if any(img_data[offset + c] < threshold for c in range(n)):
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x <= min_x or max_y <= min_y:
            return None

        scale = 0.5
        bbox = fitz.Rect(
            min_x / scale, min_y / scale,
            (max_x + 1) / scale, (max_y + 1) / scale,
        )
        bbox = bbox + (-margin, -margin, margin, margin)
        return bbox & page.rect
    except Exception:
        return None


def detect_content_bbox(page: fitz.Page, margin: float = 5.0) -> fitz.Rect:
    """Detect the bounding box of actual content on a page.

    Examines text blocks, vector drawings, and images to find the union
    of all visible content.  Filters out full-page background elements
    (drawings/images covering ≥90% of page area).

    Falls back to render-based detection for scanned pages, then to
    the full page rect if nothing else works.
    """
    page_rect = page.rect
    rects: list[fitz.Rect] = []

    for block in page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]:
        rects.append(fitz.Rect(block["bbox"]))

    for drawing in page.get_drawings():
        r = drawing["rect"]
        if not _is_background_rect(r, page_rect):
            rects.append(r)

    for img in page.get_image_info():
        r = fitz.Rect(img["bbox"])
        if not _is_background_rect(r, page_rect):
            rects.append(r)

    if not rects:
        rendered = _render_content_bbox(page, margin)
        if rendered is not None:
            return rendered
        return page_rect

    union = rects[0]
    for r in rects[1:]:
        union = union | r

    union = union + (-margin, -margin, margin, margin)
    result = union & page_rect

    if _is_background_rect(result, page_rect, threshold=0.95):
        rendered = _render_content_bbox(page, margin)
        if rendered is not None and not _is_background_rect(rendered, page_rect, 0.95):
            return rendered
        print(
            f"  warning: page {page.number + 1} — detected content covers "
            f"≥95% of page; auto-crop may be ineffective (consider --crop)",
            file=sys.stderr,
        )

    return result


def _parse_crop_spec(spec: str) -> fitz.Rect:
    """Parse 'left,top,right,bottom' into a fitz.Rect."""
    raw = spec.split(",")
    if len(raw) != 4:
        print(
            f"Error: --crop requires exactly 4 values (left,top,right,bottom), "
            f"got {len(raw)}",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        parts = [float(x.strip()) for x in raw]
    except ValueError:
        print(
            f"Error: --crop values must be numbers, got '{spec}'",
            file=sys.stderr,
        )
        sys.exit(1)
    rect = fitz.Rect(*parts)
    if rect.is_empty:
        print(
            f"Error: --crop rect is empty or inverted: {parts}",
            file=sys.stderr,
        )
        sys.exit(1)
    return rect


def _parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """Parse '1,3,5-7' into 0-based page indices."""
    indices: list[int] = []
    try:
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                lo_s, hi_s = part.split("-", 1)
                lo, hi = int(lo_s.strip()), int(hi_s.strip())
                for p in range(lo, hi + 1):
                    if 1 <= p <= total_pages:
                        indices.append(p - 1)
            else:
                p = int(part)
                if 1 <= p <= total_pages:
                    indices.append(p - 1)
    except ValueError:
        print(
            f"Error: invalid page spec '{spec}' — expected format like '1,3,5-7'",
            file=sys.stderr,
        )
        sys.exit(1)
    return indices


def _compute_layout(
    content_sizes: list[tuple[float, float]],
    layout: str,
    page_rect: fitz.Rect,
    margin: float,
    gap: float,
    per_page: int | None,
) -> list[list[tuple[int, fitz.Rect]]]:
    """Compute target rectangles for each content region.

    Returns a list of pages, each page being a list of (source_index, target_rect).
    """
    usable_w = page_rect.width - 2 * margin
    usable_h = page_rect.height - 2 * margin

    if usable_w <= 0 or usable_h <= 0:
        print(
            f"Error: margin ({margin} pt) is too large for page size "
            f"({page_rect.width:.0f}×{page_rect.height:.0f} pt)",
            file=sys.stderr,
        )
        sys.exit(1)

    if per_page is None:
        per_page = min(len(content_sizes), 20)

    pages: list[list[tuple[int, fitz.Rect]]] = []
    idx = 0
    total = len(content_sizes)

    while idx < total:
        batch_end = min(idx + per_page, total)
        batch = content_sizes[idx:batch_end]
        n = len(batch)
        page_items: list[tuple[int, fitz.Rect]] = []

        effective_gap = gap
        if layout == "vertical":
            max_gap = usable_h * 0.8 / max(n - 1, 1)
            effective_gap = min(gap, max_gap)

        if layout == "vertical":
            total_gap = effective_gap * (n - 1)
            available_h = usable_h - total_gap

            aspect_ratios = [w / h if h > 0 else 1.0 for w, h in batch]
            raw_heights = [available_h / n] * n

            # Refine: distribute height proportionally to content aspect ratio
            # so wider content gets less height and taller content gets more.
            inv_ratios = [1.0 / ar for ar in aspect_ratios]
            total_inv = sum(inv_ratios)
            if total_inv > 0:
                raw_heights = [(ir / total_inv) * available_h for ir in inv_ratios]

            y = margin
            for i, (cw, ch) in enumerate(batch):
                slot_h = raw_heights[i]
                scale = min(usable_w / cw, slot_h / ch) if cw > 0 and ch > 0 else 1.0
                rendered_w = cw * scale
                rendered_h = ch * scale
                x_offset = margin + (usable_w - rendered_w) / 2
                y_offset = y + (slot_h - rendered_h) / 2
                rect = fitz.Rect(
                    x_offset, y_offset,
                    x_offset + rendered_w, y_offset + rendered_h,
                )
                page_items.append((idx + i, rect))
                y += slot_h + effective_gap

        elif layout == "horizontal":
            max_gap_h = usable_w * 0.8 / max(n - 1, 1)
            effective_gap_h = min(gap, max_gap_h)
            total_gap = effective_gap_h * (n - 1)
            available_w = usable_w - total_gap

            aspect_ratios = [w / h if h > 0 else 1.0 for w, h in batch]
            total_ar = sum(aspect_ratios)
            if total_ar > 0:
                raw_widths = [(ar / total_ar) * available_w for ar in aspect_ratios]
            else:
                raw_widths = [available_w / n] * n

            x = margin
            for i, (cw, ch) in enumerate(batch):
                slot_w = raw_widths[i]
                scale = min(slot_w / cw, usable_h / ch) if cw > 0 and ch > 0 else 1.0
                rendered_w = cw * scale
                rendered_h = ch * scale
                x_offset = x + (slot_w - rendered_w) / 2
                y_offset = margin + (usable_h - rendered_h) / 2
                rect = fitz.Rect(
                    x_offset, y_offset,
                    x_offset + rendered_w, y_offset + rendered_h,
                )
                page_items.append((idx + i, rect))
                x += slot_w + effective_gap_h

        elif layout == "grid":
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)
            max_gap_gw = usable_w * 0.8 / max(cols - 1, 1)
            max_gap_gh = usable_h * 0.8 / max(rows - 1, 1)
            effective_gap_g = min(gap, max_gap_gw, max_gap_gh)
            cell_w = (usable_w - effective_gap_g * (cols - 1)) / cols
            cell_h = (usable_h - effective_gap_g * (rows - 1)) / rows

            for i, (cw, ch) in enumerate(batch):
                row, col = divmod(i, cols)
                scale = min(cell_w / cw, cell_h / ch) if cw > 0 and ch > 0 else 1.0
                rendered_w = cw * scale
                rendered_h = ch * scale
                cell_x = margin + col * (cell_w + effective_gap_g)
                cell_y = margin + row * (cell_h + effective_gap_g)
                x_offset = cell_x + (cell_w - rendered_w) / 2
                y_offset = cell_y + (cell_h - rendered_h) / 2
                rect = fitz.Rect(
                    x_offset, y_offset,
                    x_offset + rendered_w, y_offset + rendered_h,
                )
                page_items.append((idx + i, rect))
        else:
            print(f"Error: unknown layout '{layout}'", file=sys.stderr)
            sys.exit(1)

        pages.append(page_items)
        idx = batch_end

    return pages


def crop_and_compose(
    sources: list[tuple[str, int]],
    output_path: str,
    layout: str = "vertical",
    page_size: str = "a4",
    margin: float = 10.0,
    gap: float = 5.0,
    crop_spec: str | None = None,
    per_page: int | None = None,
) -> dict:
    """Main pipeline: detect → crop → compose.

    Args:
        sources: list of (pdf_path, page_index_0based)
        output_path: where to write the result
        layout: "vertical", "horizontal", or "grid"
        page_size: "a4", "letter", etc.
        margin: page margin in points
        gap: gap between content regions in points
        crop_spec: optional manual crop "left,top,right,bottom"
        per_page: max items per output page (None = fit all on one page)

    Returns:
        dict with stats for JSON output.
    """
    page_rect = PAGE_SIZES.get(page_size.lower())
    if page_rect is None:
        print(f"Error: unknown page size '{page_size}'", file=sys.stderr)
        sys.exit(1)

    manual_crop = _parse_crop_spec(crop_spec) if crop_spec else None

    # Phase 1: open sources and detect content bboxes
    regions: list[dict] = []
    opened: dict[str, fitz.Document] = {}

    try:
        for pdf_path, page_idx in sources:
            if pdf_path not in opened:
                try:
                    doc = fitz.open(pdf_path)
                except Exception as exc:
                    print(f"Error: cannot open '{pdf_path}': {exc}", file=sys.stderr)
                    sys.exit(1)
                if doc.is_encrypted:
                    print(
                        f"Error: '{pdf_path}' is encrypted/password-protected",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                opened[pdf_path] = doc
            doc = opened[pdf_path]
            if page_idx >= len(doc):
                print(
                    f"Error: '{pdf_path}' has {len(doc)} page(s), "
                    f"requested page {page_idx + 1}",
                    file=sys.stderr,
                )
                sys.exit(1)

            page = doc[page_idx]
            if manual_crop:
                bbox = manual_crop & page.rect
                if bbox.is_empty:
                    print(
                        f"Error: --crop region does not overlap with page {page_idx + 1} "
                        f"of '{pdf_path}' (page rect: {page.rect})",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            else:
                bbox = detect_content_bbox(page)

            regions.append({
                "doc": doc,
                "page_idx": page_idx,
                "bbox": bbox,
                "source": pdf_path,
            })

        content_sizes = [(r["bbox"].width, r["bbox"].height) for r in regions]

        # Phase 2: compute layout
        page_layouts = _compute_layout(
            content_sizes, layout, page_rect, margin, gap, per_page,
        )

        # Phase 3: compose output
        out_doc = fitz.open()
        for page_items in page_layouts:
            out_page = out_doc.new_page(
                width=page_rect.width, height=page_rect.height,
            )
            for src_idx, target_rect in page_items:
                region = regions[src_idx]
                out_page.show_pdf_page(
                    target_rect,
                    region["doc"],
                    region["page_idx"],
                    clip=region["bbox"],
                )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        out_doc.save(output_path, garbage=3, deflate=True)
        out_doc.close()

    finally:
        for doc in opened.values():
            doc.close()

    result = {
        "output": output_path,
        "input_count": len(sources),
        "output_pages": len(page_layouts),
        "layout": layout,
        "page_size": page_size,
        "detection": "manual" if manual_crop else "auto",
        "regions": [],
    }
    for r in regions:
        bbox = r["bbox"]
        result["regions"].append({
            "source": r["source"],
            "page": r["page_idx"] + 1,
            "content_bbox": [round(bbox.x0, 1), round(bbox.y0, 1),
                             round(bbox.x1, 1), round(bbox.y1, 1)],
            "content_size": f"{bbox.width:.0f}×{bbox.height:.0f} pt",
        })

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Content-aware PDF crop and N-up composition.",
        epilog=(
            "Examples:\n"
            "  # Auto-detect and compose 3 receipts vertically on A4\n"
            "  python scripts/crop_compose.py \\\n"
            "      --inputs a.pdf b.pdf c.pdf --output merged.pdf\n\n"
            "  # Pages from a single file, horizontal layout\n"
            "  python scripts/crop_compose.py \\\n"
            "      --input multi.pdf --pages 1-3 --output composed.pdf \\\n"
            "      --layout horizontal\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--inputs", nargs="+",
        help="Multiple input PDF files (one page each by default)",
    )
    input_group.add_argument(
        "--input",
        help="Single input PDF file (use with --pages to select pages)",
    )

    parser.add_argument("--output", required=True, help="Output PDF file path")
    parser.add_argument("--pages", nargs="*",
                        help="Page spec(s): one per input, or one range for --input")
    parser.add_argument("--layout", default="vertical",
                        choices=["vertical", "horizontal", "grid"],
                        help="Layout mode (default: vertical)")
    parser.add_argument("--page-size", default="a4",
                        choices=list(PAGE_SIZES.keys()),
                        help="Output page size (default: a4)")
    parser.add_argument("--margin", type=float, default=10.0,
                        help="Page margin in points (default: 10)")
    parser.add_argument("--gap", type=float, default=5.0,
                        help="Gap between regions in points (default: 5)")
    parser.add_argument("--crop",
                        help="Manual crop box: left,top,right,bottom in PDF points")
    parser.add_argument("--per-page", type=int,
                        help="Max regions per output page (default: all on one page)")
    parser.add_argument("--json", action="store_true",
                        help="Output result as JSON")

    args = parser.parse_args()

    output_path = Path(args.output)
    input_path = Path(args.input) if args.input else None

    def local_ready() -> bool:
        return importlib.util.find_spec("fitz") is not None

    def cloud_ready() -> bool:
        if input_path is None or not input_path.is_file() or args.page_size not in {"a4", "letter"}:
            return False
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path:
        flags: list[tuple[str, str | None]] = [
            ("layout", args.layout),
            ("page-size", args.page_size),
            ("margin-mm", str(args.margin * 25.4 / 72.0)),
            ("gap-mm", str(args.gap * 25.4 / 72.0)),
            ("per-page", str(args.per_page or 16)),
        ]
        if args.pages:
            flags.append(("pages", args.pages[0]))
        if args.crop:
            values = [value.strip() for value in args.crop.split(",")]
            if len(values) != 4:
                raise BackendFailure("CROP_ARGUMENT_INVALID", retryable=False)
            flags.append(("crop", "[" + ",".join(values) + "]"))
        try:
            run_document_tool(
                ("document", "pdf", "compose"),
                input_path,
                save_path=output_path,
                flags=tuple(flags),
            )
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_PDF_COMPOSE_FAILED", retryable=True) from exc
        return output_path

    def valid_pdf(path: Path) -> bool:
        if not path.is_file() or path.stat().st_size < 5:
            return False
        with path.open("rb") as source:
            return source.read(5) == b"%PDF-"

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=local_ready,
            cloud_ready=cloud_ready,
            run_cloud=run_cloud,
            local_result=lambda: output_path,
            validate=valid_pdf,
        )
        if handled:
            return
    except BackendFailure as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if fitz is None:
        print("Error: PyMuPDF (fitz) is required for local composition", file=sys.stderr)
        sys.exit(1)

    # Build source list: (path, 0-based page index)
    sources: list[tuple[str, int]] = []

    if args.input:
        doc = fitz.open(args.input)
        total = len(doc)
        doc.close()
        if args.pages:
            page_indices = _parse_page_spec(args.pages[0], total)
        else:
            page_indices = list(range(total))
        for idx in page_indices:
            sources.append((args.input, idx))
    else:
        if args.pages:
            if len(args.pages) != len(args.inputs):
                print(
                    f"Error: --pages count ({len(args.pages)}) must match "
                    f"--inputs count ({len(args.inputs)})",
                    file=sys.stderr,
                )
                sys.exit(1)
            for pdf_path, page_spec in zip(args.inputs, args.pages):
                doc = fitz.open(pdf_path)
                total = len(doc)
                doc.close()
                for idx in _parse_page_spec(page_spec, total):
                    sources.append((pdf_path, idx))
        else:
            for pdf_path in args.inputs:
                sources.append((pdf_path, 0))

    if not sources:
        print("Error: no source pages resolved", file=sys.stderr)
        sys.exit(1)

    result = crop_and_compose(
        sources=sources,
        output_path=args.output,
        layout=args.layout,
        page_size=args.page_size,
        margin=args.margin,
        gap=args.gap,
        crop_spec=args.crop,
        per_page=args.per_page,
    )

    if args.json:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Composed {result['input_count']} region(s) → "
              f"{result['output_pages']} page(s) → {result['output']}")
        for r in result["regions"]:
            print(f"  {r['source']} p{r['page']}: "
                  f"bbox={r['content_bbox']} ({r['content_size']})")


if __name__ == "__main__":
    main()
