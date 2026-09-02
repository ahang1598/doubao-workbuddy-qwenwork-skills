#!/usr/bin/env python3
"""Split or resize oversized OCR inputs without changing the source file."""

import argparse
import json
from pathlib import Path


DEFAULT_MAX_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg"}


def _save_under_limit(image, output_stem, max_bytes):
    from PIL import Image

    png_path = output_stem.with_suffix(".png")
    image.save(png_path, format="PNG", optimize=True)
    if png_path.stat().st_size <= max_bytes:
        return png_path

    rgb = image.convert("RGB")
    jpg_path = output_stem.with_suffix(".jpg")
    for quality in (90, 80, 70, 60, 50):
        rgb.save(jpg_path, format="JPEG", quality=quality, optimize=True)
        if jpg_path.stat().st_size <= max_bytes:
            png_path.unlink(missing_ok=True)
            return jpg_path

    resized = rgb
    while min(resized.size) > 320:
        resized = resized.resize(
            (max(1, int(resized.width * 0.8)), max(1, int(resized.height * 0.8))),
            Image.Resampling.LANCZOS,
        )
        resized.save(jpg_path, format="JPEG", quality=50, optimize=True)
        if jpg_path.stat().st_size <= max_bytes:
            png_path.unlink(missing_ok=True)
            return jpg_path

    png_path.unlink(missing_ok=True)
    jpg_path.unlink(missing_ok=True)
    raise ValueError(f"页面压缩后仍超过 {max_bytes} 字节")


def _part(path, page_number):
    return {
        "page_number": page_number,
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
    }


def split_ocr_input(input_path, output_dir, max_bytes=DEFAULT_MAX_BYTES, dpi=150):
    source = Path(input_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    if not source.is_file():
        return {"status": "BLOCKED_INPUT", "message": f"文件不存在：{source}", "parts": []}
    if max_bytes <= 0:
        return {"status": "BLOCKED_INPUT", "message": "max_bytes 必须大于 0", "parts": []}

    source_bytes = source.stat().st_size
    if source_bytes <= max_bytes:
        return {
            "status": "PASS",
            "source": str(source),
            "source_bytes": source_bytes,
            "max_bytes": max_bytes,
            "split_required": False,
            "parts": [_part(source, 1)],
        }

    destination.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()
    parts = []
    try:
        if suffix == ".pdf":
            import fitz
            from PIL import Image

            with fitz.open(source) as document:
                for index, page in enumerate(document, start=1):
                    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    output = _save_under_limit(
                        image,
                        destination / f"page-{index:04d}",
                        max_bytes,
                    )
                    parts.append(_part(output, index))
        elif suffix in SUPPORTED_IMAGES:
            from PIL import Image, ImageOps

            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened).copy()
            output = _save_under_limit(image, destination / "page-0001", max_bytes)
            parts.append(_part(output, 1))
        else:
            return {
                "status": "BLOCKED_INPUT",
                "message": f"不支持的大文件类型：{suffix or '无扩展名'}",
                "parts": [],
            }
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        return {"status": "BLOCKED_INPUT", "message": str(exc), "parts": []}

    if not parts or any(item["bytes"] > max_bytes for item in parts):
        return {"status": "BLOCKED_INPUT", "message": "拆分结果仍超过 OCR 单文件限制", "parts": parts}
    return {
        "status": "PASS",
        "source": str(source),
        "source_bytes": source_bytes,
        "max_bytes": max_bytes,
        "split_required": True,
        "parts": parts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    result = split_ocr_input(args.input, args.output_dir, args.max_bytes, args.dpi)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
