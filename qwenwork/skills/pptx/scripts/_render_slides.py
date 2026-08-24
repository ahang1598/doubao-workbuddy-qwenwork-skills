"""Cloud-first PPTX slide rendering with one local LibreOffice fallback."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from PIL import Image, UnidentifiedImageError

from _cloud_runtime import CloudRuntimeError, cloud_runtime_ready, run_document_tool
from _execution_route import BackendFailure, execute_with_fallback, execution_mode


def _images_valid(paths: list[Path], expected_page_counts: frozenset[int] | None) -> bool:
    if not paths:
        return False
    if expected_page_counts is not None and len(paths) not in expected_page_counts:
        return False
    for path in paths:
        if not path.is_file() or path.stat().st_size < 8:
            return False
        with path.open("rb") as source:
            header = source.read(8)
        if header != b"\x89PNG\r\n\x1a\n" and not header.startswith(b"\xff\xd8\xff"):
            return False
        try:
            with Image.open(path) as image:
                image.verify()
                if image.width < 1 or image.height < 1:
                    return False
        except (OSError, SyntaxError, UnidentifiedImageError):
            return False
    return True


def _cloud_render(pptx_path: Path, temp_dir: Path, dpi: int) -> list[Path]:
    cloud_root = temp_dir / "cloud-render"
    pdf_path = cloud_root / "source.pdf"
    pages_dir = cloud_root / "pages"
    try:
        run_document_tool(
            ("document", "convert"),
            pptx_path,
            save_path=pdf_path,
            flags=(("to", "pdf"),),
        )
        run_document_tool(
            ("document", "pdf", "render-pages"),
            pdf_path,
            save_path=pages_dir,
            flags=(("dpi", str(dpi)), ("max-side", "2400")),
        )
    except CloudRuntimeError as exc:
        raise BackendFailure(exc.code, fallback_allowed=exc.fallback_allowed) from exc
    return sorted(path for path in pages_dir.glob("page_*.png") if path.is_file())


def render_pages_with_fallback(
    pptx_path: Path,
    temp_dir: Path,
    *,
    dpi: int,
    local_renderer: Callable[[Path, Path], list[Path]],
    expected_page_counts: frozenset[int] | None = None,
) -> list[Path]:
    result, report = execute_with_fallback(
        mode=execution_mode(),
        local_ready=lambda: shutil.which("soffice") is not None and shutil.which("pdftoppm") is not None,
        cloud_ready=cloud_runtime_ready,
        run_local=lambda: local_renderer(pptx_path, temp_dir),
        run_cloud=lambda: _cloud_render(pptx_path, temp_dir, dpi),
        validate=lambda paths: _images_valid(paths, expected_page_counts),
    )
    report.emit()
    return result
