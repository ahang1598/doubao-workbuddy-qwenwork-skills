#!/usr/bin/env python3
"""
optimize_pdf.py — PDF Size Optimizer

Reduces PDF file size by compressing images, removing duplicate objects,
stripping unnecessary metadata, and optionally linearizing for web delivery.

Usage:
    python scripts/optimize_pdf.py large.pdf small.pdf
    python scripts/optimize_pdf.py large.pdf small.pdf --image-quality 70
    python scripts/optimize_pdf.py large.pdf small.pdf --target-size 10240
    python scripts/optimize_pdf.py large.pdf small.pdf --target-size 10240 --rasterize-fallback
    python scripts/optimize_pdf.py large.pdf small.pdf --strip-metadata --linearize
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import resolve_qwenwork_cli, run_document_tool
from _execution_route import BackendFailure
from _semantic_route import execute_semantic_script


def _file_size_kb(path: Path) -> float:
    return path.stat().st_size / 1024


def _resolve_colorspace(cs_obj):
    """Resolve a PDF ColorSpace to (PIL mode, channels) or None."""
    if cs_obj is None:
        return None
    resolved = cs_obj.get_object() if hasattr(cs_obj, "get_object") else cs_obj

    if isinstance(resolved, list):
        # Array form: [/ICCBased, stream] or [/Indexed, base, hival, lookup]
        name = str(resolved[0]) if resolved else ""
        if "/ICCBased" in name and len(resolved) > 1:
            icc_stream = resolved[1]
            if hasattr(icc_stream, "get_object"):
                icc_stream = icc_stream.get_object()
            n = int(icc_stream.get("/N", 0)) if hasattr(icc_stream, "get") else 0
            if n == 3:
                return "RGB", 3
            elif n == 1:
                return "L", 1
            elif n == 4:
                return "CMYK", 4
        return None

    cs_str = str(resolved)
    if "DeviceRGB" in cs_str or "CalRGB" in cs_str:
        return "RGB", 3
    elif "DeviceGray" in cs_str or "CalGray" in cs_str:
        return "L", 1
    elif "DeviceCMYK" in cs_str:
        return "CMYK", 4
    return None


def _reconstruct_image(obj, data):
    """Rebuild a PIL Image from raw PDF image stream bytes (FlateDecode etc.)."""
    from PIL import Image
    try:
        width = int(obj.get("/Width", 0))
        height = int(obj.get("/Height", 0))
        if width <= 0 or height <= 0:
            return None

        bpc = int(obj.get("/BitsPerComponent", 8))
        if bpc != 8:
            return None

        result = _resolve_colorspace(obj.get("/ColorSpace"))
        if result is None:
            return None
        mode, channels = result

        expected = width * height * channels
        if len(data) < expected:
            return None

        return Image.frombytes(mode, (width, height), data[:expected])
    except Exception:
        return None


def compress_images_in_pdf(input_path: Path, output_path: Path, quality: int) -> int:
    """
    Re-compress images inside the PDF to the specified JPEG quality level.
    Handles DCTDecode (JPEG), PNG, and FlateDecode (raw pixel) images.
    Returns the count of images processed.
    """
    try:
        import pypdf
        from PIL import Image
        import io
    except ImportError:
        raise RuntimeError("pypdf and Pillow required. Run: pip install pypdf Pillow")

    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)
    img_count = 0

    for page in writer.pages:
        if "/Resources" not in page:
            continue
        resources = page.get("/Resources", {})
        xobjects = resources.get("/XObject", {})
        for key in list(xobjects.keys()):
            obj = xobjects[key]
            if hasattr(obj, "get_object"):
                obj = obj.get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            data = obj.get_data() if hasattr(obj, "get_data") else None
            if data is None:
                continue
            try:
                img = Image.open(io.BytesIO(data))
                if img.format not in ("JPEG", "PNG", None):
                    continue
            except Exception:
                img = _reconstruct_image(obj, data)
                if img is None:
                    continue
            try:
                if img.mode in ("RGBA", "P", "CMYK"):
                    img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                compressed = buf.getvalue()
                if len(compressed) < len(data):
                    obj.set_data(compressed)
                    obj[pypdf.generic.NameObject("/Filter")] = pypdf.generic.NameObject("/DCTDecode")
                    img_count += 1
            except Exception:
                continue

    with open(output_path, "wb") as fh:
        writer.write(fh)
    return img_count


def linearize_with_qpdf(input_path: Path, output_path: Path) -> bool:
    """Linearize PDF for fast web delivery using qpdf if available."""
    if not shutil.which("qpdf"):
        return False
    result = subprocess.run(
        ["qpdf", "--linearize", str(input_path), str(output_path)],
        capture_output=True
    )
    return result.returncode == 0


def _rasterize_compress(input_path: Path, output_path: Path, target_kb: float,
                        min_scale: float = 0.7, min_quality: int = 60):
    """Rasterize pages as JPEG images and rebuild the PDF.
    Searches from scale=1.0/quality=95 downward. Returns (scale, quality,
    size_kb, met_target) or None on error. When met_target is False, the
    output contains the smallest achievable result within quality bounds."""
    try:
        import pypdfium2 as pdfium
        from PIL import Image
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        import io, tempfile
    except ImportError:
        return None

    try:
        pdf = pdfium.PdfDocument(str(input_path))
    except Exception:
        return None

    page_count = len(pdf)
    if page_count == 0:
        return None

    page_sizes = []
    for page in pdf:
        w, h = page.get_size()
        page_sizes.append((w, h))

    scales = [round(s * 0.1, 1) for s in range(10, int(min_scale * 10) - 1, -1)]
    qualities = [q for q in range(95, min_quality - 1, -5)]

    # Quick calibration: render 1 page at min settings to measure overhead
    try:
        bm = pdf[0].render(scale=min_scale)
        cal_img = bm.to_pil()
        if cal_img.mode == "RGBA":
            cal_img = cal_img.convert("RGB")
        cal_buf = io.BytesIO()
        cal_img.save(cal_buf, format="JPEG", quality=min_quality, optimize=True)
        cal_jpg = cal_buf.getvalue()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            cal_path = tf.name
        c = canvas.Canvas(cal_path)
        c.setPageSize(page_sizes[0])
        c.drawImage(ImageReader(io.BytesIO(cal_jpg)),
                    0, 0, width=page_sizes[0][0], height=page_sizes[0][1])
        c.showPage()
        c.save()
        cal_pdf_size = Path(cal_path).stat().st_size
        Path(cal_path).unlink()
        overhead_ratio = cal_pdf_size / len(cal_jpg) if len(cal_jpg) > 0 else 1.3
    except Exception:
        overhead_ratio = 1.3

    best_result = None

    for scale in scales:
        pil_pages = []
        try:
            for page in pdf:
                bitmap = page.render(scale=scale)
                img = bitmap.to_pil()
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                pil_pages.append(img)
        except Exception:
            return best_result

        for quality in qualities:
            total_bytes = 0
            page_bufs = []
            for img in pil_pages:
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                page_bufs.append(buf.getvalue())
                total_bytes += len(page_bufs[-1])

            raw_kb = total_bytes / 1024
            estimated_kb = raw_kb * overhead_ratio
            if estimated_kb > target_kb:
                continue

            c = canvas.Canvas(str(output_path))
            for i, jpg_data in enumerate(page_bufs):
                w_pt, h_pt = page_sizes[i]
                c.setPageSize((w_pt, h_pt))
                c.drawImage(ImageReader(io.BytesIO(jpg_data)),
                            0, 0, width=w_pt, height=h_pt)
                c.showPage()
            c.save()
            actual_kb = output_path.stat().st_size / 1024
            overhead_ratio = actual_kb / raw_kb if raw_kb > 0 else overhead_ratio

            best_result = (scale, quality, actual_kb, actual_kb <= target_kb)
            if actual_kb <= target_kb:
                return best_result

    # If no combo met target, try the minimum settings as best effort
    if best_result is None:
        try:
            min_bufs = []
            min_pil = []
            for page in pdf:
                bitmap = page.render(scale=min_scale)
                img = bitmap.to_pil()
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                min_pil.append(img)
            for img in min_pil:
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=min_quality, optimize=True)
                min_bufs.append(buf.getvalue())
            c = canvas.Canvas(str(output_path))
            for i, jpg_data in enumerate(min_bufs):
                w_pt, h_pt = page_sizes[i]
                c.setPageSize((w_pt, h_pt))
                c.drawImage(ImageReader(io.BytesIO(jpg_data)),
                            0, 0, width=w_pt, height=h_pt)
                c.showPage()
            c.save()
            actual_kb = output_path.stat().st_size / 1024
            best_result = (min_scale, min_quality, actual_kb, actual_kb <= target_kb)
        except Exception:
            pass

    return best_result


def strip_metadata(input_path: Path, output_path: Path) -> None:
    try:
        import pypdf
    except ImportError:
        raise RuntimeError("pypdf required. Run: pip install pypdf")
    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)
    writer.add_metadata({})
    with open(output_path, "wb") as fh:
        writer.write(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize PDF file size.")
    parser.add_argument("input_pdf", help="Input PDF path")
    parser.add_argument("output_pdf", help="Output optimized PDF path")
    parser.add_argument("--image-quality", type=int, default=80, metavar="1-95",
                        help="JPEG compression quality for embedded images (default: 80)")
    parser.add_argument("--strip-metadata", action="store_true",
                        help="Remove document metadata")
    parser.add_argument("--linearize", action="store_true",
                        help="Linearize PDF for web delivery (requires qpdf)")
    parser.add_argument("--target-size", type=float, default=None, metavar="KB",
                        help="Target output size in KB. Iteratively lowers "
                             "image quality until the target is met.")
    parser.add_argument("--rasterize-fallback", action="store_true",
                        help="Allow page rasterization as last resort when "
                             "image compression cannot meet --target-size. "
                             "WARNING: text becomes non-searchable.")
    parser.add_argument("--min-scale", type=float, default=0.7,
                        help="Minimum render scale for rasterization (default: 0.7)")
    parser.add_argument("--min-quality", type=int, default=60,
                        help="Minimum JPEG quality for rasterization (default: 60)")
    parser.add_argument("--report", action="store_true",
                        help="Print compression report")
    args = parser.parse_args()

    input_path = Path(args.input_pdf)
    output_path = Path(args.output_pdf)

    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    def local_ready() -> bool:
        modules = ["pypdf", "PIL"]
        if args.rasterize_fallback:
            modules.extend(["pypdfium2", "reportlab"])
        return (
            all(importlib.util.find_spec(module) is not None for module in modules)
            and (not args.linearize or shutil.which("qpdf") is not None)
        )

    def cloud_ready() -> bool:
        try:
            return resolve_qwenwork_cli(required=False) is not None
        except RuntimeError:
            return False

    def run_cloud() -> Path:
        flags: list[tuple[str, str | None]] = [
            ("image-quality", str(args.image_quality)),
            ("min-scale", str(args.min_scale)),
            ("min-quality", str(args.min_quality)),
        ]
        if args.strip_metadata:
            flags.append(("strip-metadata", None))
        if args.linearize:
            flags.append(("linearize", None))
        if args.target_size is not None:
            flags.append(("target-size-kb", str(args.target_size)))
        if args.rasterize_fallback:
            flags.append(("rasterize-fallback", None))
        try:
            result = run_document_tool(
                ("document", "pdf", "optimize"),
                input_path,
                save_path=output_path,
                flags=tuple(flags),
            )
        except RuntimeError as exc:
            raise BackendFailure("CLOUD_PDF_OPTIMIZE_FAILED", retryable=True) from exc
        if args.report:
            print("Cloud optimization result: " + str(result.get("output", {}))[:1000])
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

    orig_kb = _file_size_kb(input_path)
    print(f"Input:  {input_path.name}  ({orig_kb:.1f} KB)")

    # Work on a temp copy, then apply passes
    import tempfile, shutil as sh
    with tempfile.TemporaryDirectory() as tmp:
        working = Path(tmp) / "working.pdf"
        sh.copy2(str(input_path), str(working))

        # Pass 1: compress images
        try:
            img_count = compress_images_in_pdf(working, output_path, args.image_quality)
            sh.copy2(str(output_path), str(working))
            print(f"  Images compressed: {img_count} re-encoded at quality {args.image_quality}")
        except RuntimeError as exc:
            print(f"  Image compression skipped: {exc}")

        # Pass 1b: adaptive quality search when --target-size is set
        # Always compress from input_path to avoid double-JPEG degradation
        if args.target_size and _file_size_kb(working) > args.target_size:
            met = False
            for q in range(min(args.image_quality - 5, 90), 45, -5):
                try:
                    cnt = compress_images_in_pdf(input_path, output_path, q)
                except RuntimeError:
                    break
                cur_kb = _file_size_kb(output_path)
                if cur_kb <= args.target_size:
                    sh.copy2(str(output_path), str(working))
                    print(f"  Target met at quality {q}: {cur_kb:.1f} KB "
                          f"({cnt} re-encoded)")
                    met = True
                    break
            if not met:
                # Use the best attempt if it's better than current working
                if output_path.exists() and _file_size_kb(output_path) < _file_size_kb(working):
                    sh.copy2(str(output_path), str(working))
                print(f"  Could not meet target {args.target_size:.0f} KB "
                      f"with image compression alone "
                      f"(best: {_file_size_kb(working):.1f} KB)")

        # Pass 1c: rasterization fallback (renders from original for best quality)
        if (args.target_size and args.rasterize_fallback
                and _file_size_kb(working) > args.target_size):
            print("  Trying rasterization fallback...")
            result = _rasterize_compress(
                input_path, output_path, args.target_size,
                min_scale=args.min_scale, min_quality=args.min_quality)
            if result:
                scale, quality, size_kb, met_target = result
                if size_kb < _file_size_kb(working):
                    sh.copy2(str(output_path), str(working))
                    print(f"  Rasterized: scale={scale}, quality={quality}, "
                          f"size={size_kb:.1f} KB"
                          f"{'' if met_target else ' (best effort, target not met)'}")
                    print(f"  WARNING: text is no longer searchable/selectable")
                elif not met_target:
                    print(f"  Rasterization did not improve over image compression")
            else:
                print(f"  Rasterization failed (missing deps or unreadable PDF)")

        # Pass 2: strip metadata
        if args.strip_metadata:
            strip_metadata(working, output_path)
            sh.copy2(str(output_path), str(working))
            print("  Metadata stripped")

        # Pass 3: linearize
        if args.linearize:
            success = linearize_with_qpdf(working, output_path)
            if success:
                sh.copy2(str(output_path), str(working))
                print("  Linearized for web delivery")
            else:
                print("  Linearization skipped (qpdf not found)")

        # Ensure output exists
        if not output_path.exists():
            sh.copy2(str(working), str(output_path))

    final_kb = _file_size_kb(output_path)
    saved_pct = (1 - final_kb / orig_kb) * 100 if orig_kb > 0 else 0

    print(f"Output: {output_path.name}  ({final_kb:.1f} KB)")
    print(f"Saved:  {orig_kb - final_kb:.1f} KB  ({saved_pct:.1f}% reduction)")

    if args.report:
        print("\nOptimization Report")
        print("-" * 40)
        print(f"  Source size:   {orig_kb:>8.1f} KB")
        print(f"  Output size:   {final_kb:>8.1f} KB")
        print(f"  Reduction:     {orig_kb - final_kb:>8.1f} KB  ({saved_pct:.1f}%)")
        print(f"  Image quality: {args.image_quality}")
        print(f"  Strip meta:    {args.strip_metadata}")
        print(f"  Linearized:    {args.linearize}")


if __name__ == "__main__":
    main()
