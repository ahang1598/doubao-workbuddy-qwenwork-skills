#!/usr/bin/env python3
"""
convert_pdf_to_images.py — render PDF pages to PNG with pypdfium2.

Replaces the older pdf2image-based version. No system binary required;
the pypdfium2 wheel ships PDFium statically. Use this for the
"scanned PDF → vision" route and for the visual form-fill refinement.

Usage:
    python scripts/convert_pdf_to_images.py input.pdf --output images/
    python scripts/convert_pdf_to_images.py input.pdf --output images/ --pages 1-3,7
    python scripts/convert_pdf_to_images.py input.pdf --output images/ --dpi 200
    python scripts/convert_pdf_to_images.py input.pdf --output images/ --max-side 2000

Render guidance for the agent:
- Default DPI is 150 (~2x readable). Bump to 200–250 only after 150 was unreadable.
- Default max long-side cap is 1500 px; raising it costs memory.
- For posters / oversize pages, render once at low DPI for overview, then
  crop a region with Pillow and re-render that region at higher DPI.
- Render on demand by page index. Do not preemptively render all pages
  of a multi-page PDF.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import remote_runtime_required, resolve_qwenwork_cli
from _execution_route import (
    BackendFailure,
    execute_with_fallback,
    execution_mode,
)


def _parse_pages(spec: str, page_count: int) -> list[int]:
    """Parse a 1-based page spec like '1-3,7,9-11' into 0-based indices."""
    if not spec:
        return list(range(page_count))
    indices: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo = int(lo_s)
            hi = int(hi_s)
            if lo < 1 or hi < 1 or lo > hi:
                raise ValueError(f"Invalid range '{part}'")
            indices.extend(range(lo - 1, min(hi, page_count)))
        else:
            n = int(part)
            if n < 1 or n > page_count:
                raise ValueError(f"Page {n} out of range (1..{page_count})")
            indices.append(n - 1)
    seen: set[int] = set()
    out: list[int] = []
    for i in indices:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _parse_remote_pages(spec: str) -> list[int]:
    """Parse a bounded 1-based page spec without opening the PDF locally."""
    if not spec:
        return []
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo < 1 or hi < lo:
                raise ValueError(f"Invalid range '{part}'")
            pages.extend(range(lo, hi + 1))
        else:
            page = int(part)
            if page < 1:
                raise ValueError(f"Invalid page '{part}'")
            pages.append(page)
        if len(pages) > 100:
            raise ValueError("Remote rendering accepts at most 100 pages")
    unique: list[int] = []
    seen: set[int] = set()
    for page in pages:
        if page not in seen:
            seen.add(page)
            unique.append(page)
    return unique


def _remote_runtime_required() -> bool:
    return remote_runtime_required()


def _resolve_qwenwork_cli(
    script_path: Path | None = None,
    platform_name: str | None = None,
) -> str | None:
    return resolve_qwenwork_cli(
        script_path=script_path,
        platform_name=platform_name,
        required=False,
    )


def _local_runtime_ready() -> bool:
    return (
        importlib.util.find_spec("pypdfium2") is not None
        and importlib.util.find_spec("PIL") is not None
    )


def _cloud_runtime_ready() -> bool:
    try:
        return _resolve_qwenwork_cli() is not None
    except RuntimeError:
        return False


def _page_number(path: Path, fallback: int) -> int:
    value = path.stem.rsplit("_", 1)[-1]
    return int(value) if value.isdigit() else fallback


def _try_remote_render(
    pdf_path: Path,
    output_dir: Path,
    pages: str,
    dpi: int,
    max_side: int,
    fmt: str,
) -> list[dict] | None:
    """Render through qwenwork's capability tool, or return None if unavailable."""
    if fmt != "png":
        return None
    cli = _resolve_qwenwork_cli()
    if cli is None:
        return None
    requested_pages = _parse_remote_pages(pages)
    output_dir.mkdir(parents=True, exist_ok=True)
    before = {
        item.name: (item.stat().st_mtime_ns, item.stat().st_size)
        for item in output_dir.glob("page_*.png")
        if item.is_file()
    }
    command = [
        cli,
        "tools",
        "document",
        "pdf",
        "render-pages",
        str(pdf_path.resolve()),
        "--save",
        str(output_dir.resolve()),
        "--dpi",
        str(dpi),
        "--max-side",
        str(max_side),
        "--deadline",
        "10m",
        "-o",
        "json",
    ]
    if requested_pages:
        command.extend(["--pages", pages])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=620,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            "Warning: remote PDF rendering failed, falling back locally: "
            + str(exc),
            file=sys.stderr,
        )
        return None
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        print(
            "Warning: remote PDF rendering failed, falling back locally: "
            + (result.stderr or result.stdout).strip()[:1000],
            file=sys.stderr,
        )
        return None
    rendered = sorted(output_dir.glob("page_*.png"))
    changed = [
        item
        for item in rendered
        if before.get(item.name) != (item.stat().st_mtime_ns, item.stat().st_size)
    ]
    if not changed:
        print(
            "Warning: remote PDF rendering completed without new page artifacts",
            file=sys.stderr,
        )
        return None
    try:
        payload = json.loads(result.stdout)
        route = "qwenwork-cli"
    except json.JSONDecodeError:
        route = "remote"
    saved = [
        {"page": _page_number(path, index), "path": str(path), "runtime": route}
        for index, path in enumerate(changed, start=1)
    ]
    for item in saved:
        print(f"Saved page {item['page']} → {item['path']} (remote)")
    print(f"Converted {len(saved)} page(s) through qwenwork document runtime")
    return saved


def _convert_locally(
    pdf_path: Path,
    output_dir: Path,
    pages: str = "",
    dpi: int = 150,
    max_side: int = 1500,
    fmt: str = "png",
) -> list[dict]:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise BackendFailure("LOCAL_DEPENDENCY_MISSING", retryable=True) from exc
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise BackendFailure("LOCAL_DEPENDENCY_MISSING", retryable=True) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page_count = len(pdf)
        indices = _parse_pages(pages, page_count)
        scale = dpi / 72.0
        saved: list[dict] = []
        for idx in indices:
            page = pdf[idx]
            try:
                pil = page.render(scale=scale).to_pil()
            finally:
                page.close()
            w, h = pil.size
            long_side = max(w, h)
            if long_side > max_side:
                factor = max_side / long_side
                pil = pil.resize((int(w * factor), int(h * factor)))
            out_path = output_dir / f"page_{idx + 1:03d}.{fmt}"
            pil.save(out_path)
            saved.append({"page": idx + 1, "path": str(out_path), "size": list(pil.size)})
            print(f"Saved page {idx + 1} → {out_path} ({pil.size[0]}x{pil.size[1]})")
        print(f"Converted {len(saved)} page(s) at {dpi} DPI (max side {max_side} px)")
        return saved
    finally:
        pdf.close()


def convert(
    pdf_path: Path,
    output_dir: Path,
    pages: str = "",
    dpi: int = 150,
    max_side: int = 1500,
    fmt: str = "png",
) -> list[dict]:
    def run_local() -> list[dict]:
        try:
            return _convert_locally(pdf_path, output_dir, pages, dpi, max_side, fmt)
        except BackendFailure:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise BackendFailure("LOCAL_RENDER_FAILED", retryable=True) from exc

    def run_cloud() -> list[dict]:
        try:
            rendered = _try_remote_render(pdf_path, output_dir, pages, dpi, max_side, fmt)
        except (OSError, RuntimeError, ValueError) as exc:
            raise BackendFailure("CLOUD_RENDER_FAILED", retryable=True) from exc
        if rendered is None:
            raise BackendFailure("CLOUD_RENDER_UNAVAILABLE", retryable=True)
        return rendered

    def validate(rendered: list[dict]) -> bool:
        if not isinstance(rendered, list) or not rendered:
            return False
        for item in rendered:
            if not isinstance(item, dict):
                return False
            candidate = Path(str(item.get("path", "")))
            if not candidate.is_file() or candidate.stat().st_size < 1:
                return False
        return True

    result, report = execute_with_fallback(
        mode=execution_mode(),
        local_ready=_local_runtime_ready,
        cloud_ready=_cloud_runtime_ready,
        run_local=run_local,
        run_cloud=run_cloud,
        validate=validate,
    )
    report.emit()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path, help="Input PDF")
    ap.add_argument("--output", "-o", type=Path, required=True, help="Output directory")
    ap.add_argument("--pages", default="", help="Page spec like '1-3,7' (1-based). Default: all.")
    ap.add_argument("--dpi", type=int, default=150, help="Render DPI (default 150)")
    ap.add_argument("--max-side", type=int, default=1500, help="Max long-side pixels (default 1500)")
    ap.add_argument("--format", default="png", choices=("png", "jpg", "jpeg"), help="Output format")
    args = ap.parse_args()

    if not args.pdf.exists():
        print(f"Error: input PDF not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)
    convert(
        args.pdf,
        args.output,
        pages=args.pages,
        dpi=args.dpi,
        max_side=args.max_side,
        fmt=args.format,
    )


if __name__ == "__main__":
    main()
