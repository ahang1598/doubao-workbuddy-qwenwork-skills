#!/usr/bin/env python3
"""
ocr_pipeline.py — OCR scanned PDFs.

Converts a scanned (image-only) PDF to either:
  - a plain text file  (when --output ends with .txt or any non-pdf suffix), or
  - a searchable PDF   (when --output ends with .pdf) — original page images
    plus an invisible text layer positioned at each token's real bbox, so text
    can be copied/searched in any PDF viewer.

Zero system-level dependencies.

Usage:
    python scripts/ocr_pipeline.py scan.pdf --output result.txt
    python scripts/ocr_pipeline.py scan.pdf --output result.pdf
    python scripts/ocr_pipeline.py scan.pdf --output result.txt --pages 1-10
    python scripts/ocr_pipeline.py scan.pdf --output result.txt --dpi 150 --suppress-red

Requirements (all pure-Python wheels, no system installs):
    pip install rapidocr-onnxruntime pymupdf numpy reportlab pillow
    (optional) pip install deskew   # for rotated-scan auto-correction

Text output format:
    === Page 1 ===
    <page 1 OCR text>

    === Page 2 ===
    <page 2 OCR text>

    ...
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import os
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # The semantic route can still use the cloud backend.
    np = None


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import CloudRuntimeError, resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script

# Ensure every print flushes on newline, so an Agent viewing the bg shell_log
# sees progress in real time instead of a silent 15s-timeout window.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass  # Python <3.7 fallback — rely on explicit flush=True calls below.


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _suppress_red(arr: np.ndarray) -> np.ndarray:
    """Replace red-dominant pixels (stamps/seals) with white."""
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mask = (r > 150) & (r > g * 1.5) & (r > b * 1.5)
    out = arr.copy()
    out[mask] = [255, 255, 255]
    return out


def _deskew(arr: np.ndarray) -> np.ndarray:
    """Detect and correct skew angle. Returns original array if deskew unavailable."""
    try:
        from deskew import determine_skew
        from PIL import Image
        angle = determine_skew(arr)
        if angle is None or abs(angle) < 0.5:
            return arr
        img = Image.fromarray(arr)
        img = img.rotate(float(angle), resample=Image.BICUBIC,
                         expand=False, fillcolor=(255, 255, 255))
        return np.array(img)
    except ImportError:
        return arr


def preprocess(arr: np.ndarray, suppress_red: bool) -> np.ndarray:
    if suppress_red:
        arr = _suppress_red(arr)
    arr = _deskew(arr)
    return arr


# ---------------------------------------------------------------------------
# Page-range parsing (shared with extract_content.py / extract_tables.py)
# ---------------------------------------------------------------------------

def _parse_page_spec(spec: str, total: int) -> set[int]:
    """Parse '1-10' or '1,3,7-9' into a set of 0-based page indices.

    Raises ValueError with a human-readable message on malformed input.
    """
    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                lo, hi = part.split("-", 1)
                for p in range(int(lo), int(hi) + 1):
                    if 1 <= p <= total:
                        indices.add(p - 1)
            else:
                p = int(part)
                if 1 <= p <= total:
                    indices.add(p - 1)
        except ValueError:
            raise ValueError(
                f"Invalid page spec '{part}' in '{spec}'. "
                f"Expected format: '1-10' or '1,3,7-9' (1-indexed)."
            )
    return indices


# ---------------------------------------------------------------------------
# Streaming OCR pipeline (pymupdf + rapidocr-onnxruntime)
#
# Rasterise and OCR one page at a time, yielding (idx, arr, ocr_result). This
# keeps memory footprint at O(1 page + model) instead of O(n pages), which
# matters: DPI 200 A4 page ≈ 12 MB, so 500 pages would otherwise peak ~6 GB.
# ---------------------------------------------------------------------------

def ocr_pages_stream(pdf_path: Path, dpi: int, suppress_red: bool,
                     page_indices: set[int] | None = None):
    """Yield (page_idx, rgb_array, ocr_result) per page; arr is reclaimable
    after the consumer finishes with it (next iteration or list-append)."""
    import fitz
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    # Cap detector input to 960px long side. RapidOCR ships with
    # limit_type="min"/limit_side_len=736, which on high-DPI scans ends up
    # passing near-full-resolution images into the DB-detection ONNX model;
    # the intermediate feature maps then spike RSS to ~2.8 GB per inference.
    #
    # Empirical sweep at DPI 200 (A4 scans ~1654x2339):
    #   side=480:  peak 0.9 GB / time -70% / dense-ID-card quality -78% (too aggressive)
    #   side=640:  peak 1.3 GB / dense-ID-card quality -33%
    #   side=960:  peak 1.7 GB / dense-ID-card quality -4%, book quality ~0%   <- chosen
    #   side=1280: peak 1.9 GB / quality ~same as 960 but 10% more memory
    #
    # 960 is the knee of the curve — preserves quality on both dense small text
    # (licenses, forms) and normal print (books, reports) while cutting peak
    # RSS by ~40% vs RapidOCR default.
    #
    # This reaches into a private attribute that only exists on rapidocr-
    # onnxruntime 1.x. On 2.x (or any future refactor) we can't apply the
    # cap; warn loudly instead of silently regressing to ~2.8 GB/page.
    applied = False
    try:
        preprocess_op = engine.text_detector.preprocess_op
        for _op in preprocess_op:
            if hasattr(_op, "limit_side_len"):
                _op.limit_side_len = 960
                _op.limit_type = "max"
                applied = True
                break
    except AttributeError:
        pass
    if not applied:
        import rapidocr_onnxruntime as _ro
        ver = getattr(_ro, "__version__", "unknown")
        os.write(2, (
            f"[OCR-WARN] rapidocr-onnxruntime=={ver}: could not locate "
            f"text_detector.preprocess_op with limit_side_len — memory cap "
            f"not applied. Dense scans may spike RSS to ~2.8 GB/page. "
            f"Pin rapidocr-onnxruntime<2.0 to restore the cap.\n"
        ).encode("utf-8"))

    scale = dpi / 72
    mat = fitz.Matrix(scale, scale)

    with fitz.open(str(pdf_path)) as doc:
        for idx, page in enumerate(doc):
            if page_indices is not None and idx not in page_indices:
                continue
            pix = page.get_pixmap(matrix=mat, alpha=False)
            # .copy() detaches from pix.samples so pix can be released
            arr = np.frombuffer(pix.samples, dtype=np.uint8) \
                    .reshape(pix.h, pix.w, 3) \
                    .copy()
            arr = preprocess(arr, suppress_red)
            result, _ = engine(arr)
            yield idx, arr, (result or [])


def _page_text(ocr_result: list) -> str:
    return "\n".join(item[1] for item in ocr_result)


# ---------------------------------------------------------------------------
# Searchable PDF (invisible text layer at real bbox positions)
# ---------------------------------------------------------------------------

def build_searchable_pdf(page_stream, output_path: Path, dpi: int,
                         progress=None) -> int:
    """Emit a PDF where each page is the original image plus an invisible
    text layer positioned at each OCR token's real bbox. Text stays invisible
    regardless of the reader's fonts (PDF text-render-mode 3).

    Consumes an iterable of (page_idx, rgb_array, ocr_result) tuples one page
    at a time, writing each page to the canvas before releasing its `arr`.
    This keeps peak memory at O(1 page) regardless of document length.

    `progress`, if given, is called as progress(page_idx, char_count) per page
    so the caller can emit logs without re-scanning the ocr_result.

    Returns the number of pages written.
    """
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from PIL import Image

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:
        font_name = "Helvetica"

    px_to_pt = 72.0 / dpi
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = None
    pages_written = 0
    for page_idx, arr, ocr_result in page_stream:
        img_h_px, img_w_px = arr.shape[:2]
        pt_w = img_w_px * px_to_pt
        pt_h = img_h_px * px_to_pt

        if c is None:
            c = rl_canvas.Canvas(str(output_path), pagesize=(pt_w, pt_h))
        else:
            c.setPageSize((pt_w, pt_h))

        img_buf = io.BytesIO()
        Image.fromarray(arr).save(img_buf, format="PNG")
        img_buf.seek(0)
        c.drawImage(ImageReader(img_buf), 0, 0, width=pt_w, height=pt_h)

        for item in ocr_result:
            bbox, text = item[0], item[1]
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            box_w = (x_max - x_min) * px_to_pt
            box_h = (y_max - y_min) * px_to_pt
            if box_w <= 0 or box_h <= 0 or not text:
                continue

            pdf_x = x_min * px_to_pt
            pdf_y = (img_h_px - y_max) * px_to_pt  # PDF origin is bottom-left
            font_size = max(box_h * 0.85, 1.0)

            text_obj = c.beginText(pdf_x, pdf_y)
            text_obj.setTextRenderMode(3)  # 3 = invisible but selectable/searchable
            text_obj.setFont(font_name, font_size)

            raw_w = c.stringWidth(text, font_name, font_size)
            if raw_w > 0:
                text_obj.setHorizScale(box_w / raw_w * 100.0)

            text_obj.textOut(text)
            c.drawText(text_obj)

        c.showPage()
        pages_written += 1
        if progress is not None:
            progress(page_idx, len(_page_text(ocr_result)))

    if c is not None:
        c.save()
    return pages_written


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_ocr_pipeline(pdf_path: Path, output_path: Path,
                     dpi: int, suppress_red: bool,
                     page_indices: set[int] | None = None) -> dict:
    """Full OCR → searchable PDF or merged text file (decided by output suffix).

    Both output modes are streaming: pages are processed and emitted one at a
    time, so memory stays at O(1 page + OCR model) regardless of document
    length.

    If *page_indices* is given, only those 0-based page numbers are processed.
    """
    is_pdf_output = output_path.suffix.lower() == ".pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scope = f"pages {','.join(str(i+1) for i in sorted(page_indices))}" if page_indices else "all pages"
    print(f"  Rasterising {pdf_path.name} at {dpi} DPI and OCR-ing ({scope})…")

    stats = {"pages": 0, "total_chars": 0}

    if is_pdf_output:
        def tee(stream):
            # Report per-page progress while forwarding (idx, arr, result) through
            # to build_searchable_pdf, which consumes and releases each arr in turn.
            for idx, arr, ocr_result in stream:
                text_len = len(_page_text(ocr_result))
                stats["total_chars"] += text_len
                stats["pages"] += 1
                print(f"    Page {idx + 1}: {text_len} chars")
                yield idx, arr, ocr_result

        build_searchable_pdf(
            tee(ocr_pages_stream(pdf_path, dpi, suppress_red, page_indices)),
            output_path, dpi,
        )
    else:
        with output_path.open("w", encoding="utf-8") as fh:
            for idx, _arr, ocr_result in ocr_pages_stream(pdf_path, dpi, suppress_red, page_indices):
                text = _page_text(ocr_result)
                fh.write(f"=== Page {idx + 1} ===\n{text}\n\n")
                stats["total_chars"] += len(text)
                stats["pages"] += 1
                print(f"    Page {idx + 1}: {len(text)} chars")

    return {
        "source": str(pdf_path),
        "pages": stats["pages"],
        "dpi": dpi,
        "total_chars": stats["total_chars"],
        "output": str(output_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _local_runtime_ready() -> bool:
    return all(
        importlib.util.find_spec(module) is not None
        for module in ("numpy", "fitz", "rapidocr_onnxruntime", "reportlab", "PIL")
    )


def _cloud_runtime_ready() -> bool:
    try:
        return resolve_qwenwork_cli(required=False) is not None
    except RuntimeError:
        return False


def _valid_ocr_output(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1:
        return False
    if path.suffix.lower() == ".pdf":
        with path.open("rb") as source:
            return source.read(5) == b"%PDF-"
    return path.suffix.lower() == ".txt"


def _run_cloud_ocr(args: argparse.Namespace, pdf_path: Path, output_path: Path) -> Path:
    output_format = "pdf" if output_path.suffix.lower() == ".pdf" else "txt"
    flags: list[tuple[str, str | None]] = [
        ("dpi", str(args.dpi)),
        ("format", output_format),
    ]
    if args.pages:
        flags.append(("pages", args.pages))
    if args.suppress_red:
        flags.append(("suppress-red", None))
    try:
        run_document_tool(
            ("document", "pdf", "ocr"),
            pdf_path,
            save_path=output_path,
            flags=tuple(flags),
        )
    except CloudRuntimeError as exc:
        raise BackendFailure(exc.code, retryable=exc.retryable) from exc
    except RuntimeError as exc:
        raise BackendFailure("CLOUD_OPERATION_FAILED", retryable=True) from exc
    return output_path

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run OCR on a scanned PDF. Emits a searchable PDF "
                    "(if --output ends with .pdf) or a plain text file."
    )
    parser.add_argument("pdf_file", help="Input PDF path (scanned / image-only)")
    parser.add_argument("--output", "-o", required=True,
                        help="Output path. Suffix decides the mode. "
                             "RECOMMENDED DEFAULT: use a '.txt' suffix for plain text output "
                             "(fast, small, ideal for Agent / Q&A / extraction). "
                             "Only use '.pdf' when a searchable PDF is explicitly requested for "
                             "human reading or archiving — it is ~80%% slower per page and the "
                             "output file is ~1000x larger.")
    parser.add_argument("--lang", default="eng",
                        help="(IGNORED) RapidOCR auto-detects CN+EN; accepted for CLI compat only. "
                             "Do not bother choosing a value.")
    parser.add_argument("--dpi", type=int, default=150,
                        help="Rasterisation DPI (default: 150; higher = better quality but slower "
                             "and more memory). 150 is a sweet spot: detector resize caps input "
                             "at 960px long side anyway, so raising DPI past 150 mostly wastes "
                             "memory without improving OCR quality.")
    parser.add_argument("--psm", type=int, default=3,
                        help="(IGNORED) RapidOCR has no page-segmentation concept; accepted for CLI "
                             "compat only. Do not bother choosing a value.")
    parser.add_argument("--pages",
                        help="Page range spec, e.g. '1-10' or '1,3,7-9'. "
                             "Only the specified pages will be OCR-ed. "
                             "Recommended for large documents to avoid timeouts.")
    parser.add_argument("--suppress-red", action="store_true",
                        help="Suppress red pixels before OCR (reduces stamp/seal noise)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)

    try:
        handled = execute_semantic_script(
            argv=[str(Path(__file__).resolve()), *sys.argv[1:]],
            local_ready=_local_runtime_ready,
            cloud_ready=_cloud_runtime_ready,
            run_cloud=lambda: _run_cloud_ocr(args, pdf_path, output_path),
            local_result=lambda: output_path,
            validate=_valid_ocr_output,
            timeout_seconds=600,
        )
        if handled:
            return
    except BackendFailure as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Emit a page-count + ETA line to stderr IMMEDIATELY via os.write(2) — this
    # bypasses every layer of Python stdio buffering, so an Agent that started
    # this script in background sees it on the very first `view` of shell_log.
    # Fail-fast if the PDF cannot be opened: surface [OCR-FAILED] and exit.
    try:
        import fitz as _fitz
        with _fitz.open(str(pdf_path)) as _doc:
            _n = len(_doc)
    except Exception as exc:
        os.write(2, f"[OCR-FAILED] cannot open PDF: {exc}\n".encode("utf-8"))
        sys.exit(1)

    # Parse --pages into a set of 0-based indices (None = all pages).
    page_indices: set[int] | None = None
    if args.pages:
        try:
            page_indices = _parse_page_spec(args.pages, _n)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        if not page_indices:
            print(f"Error: --pages '{args.pages}' matched no valid pages "
                  f"(document has {_n} pages).", file=sys.stderr)
            sys.exit(1)

    # ~0.5-1s/page steady state + ~5s cold start for RapidOCR models.
    effective_pages = len(page_indices) if page_indices else _n
    _eta = max(15, int(effective_pages * 1.0) + 10)
    scope_label = f"{effective_pages} of {_n} pages" if page_indices else f"{_n} pages"
    os.write(2, f"[OCR-START] {pdf_path.name}: {scope_label}, "
                f"ETA ~{_eta}s. Recommended: `sleep {_eta}` then check output.\n"
                .encode("utf-8"))

    print(f"Starting OCR pipeline for {pdf_path.name}…")
    try:
        summary = run_ocr_pipeline(
            pdf_path, output_path,
            dpi=args.dpi,
            suppress_red=args.suppress_red,
            page_indices=page_indices,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        os.write(2, b"[OCR-FAILED]\n")
        sys.exit(1)

    print(f"\nDone. {summary['pages']} page(s), {summary['total_chars']} chars extracted.")
    if output_path.suffix.lower() == ".pdf":
        print(f"Searchable PDF → {summary['output']}")
    else:
        print(f"Text output → {summary['output']}")

    # Sentinel line: Agent watching the bg shell_log can grep for "OCR_DONE"
    # to know the pipeline finished successfully without polling exit code.
    os.write(2, b"[OCR-DONE]\n")


if __name__ == "__main__":
    main()
