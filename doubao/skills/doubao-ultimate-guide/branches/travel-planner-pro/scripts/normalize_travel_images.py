#!/usr/bin/env python3
"""Normalize travel-guide images to consistent sizes before Lark insertion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Pillow is required for image normalization. Install it with:\n"
        "    pip install Pillow\n"
        "If you cannot install it, skip this script and resize images manually,\n"
        "or insert images into Feishu and adjust display width there.\n"
    )
    sys.exit(2)


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

PRESETS = {
    "cover": (1600, 900),
    "route": (1200, 900),
    "day-card": (1080, 1440),
    "gallery": (1024, 1024),
    "travel-doc": None,
}


def parse_size(value: str) -> tuple[int, int]:
    raw = value.lower().replace("*", "x").split("x")
    if len(raw) != 2:
        raise argparse.ArgumentTypeError("size must look like 1200x900")
    try:
        width, height = int(raw[0]), int(raw[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size must use integers") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size must be positive")
    return width, height


def iter_images(path: Path, recursive: bool) -> Iterable[Path]:
    if path.is_file():
        if path.suffix.lower() in IMAGE_EXTS:
            yield path
        return
    pattern = "**/*" if recursive else "*"
    for item in sorted(path.glob(pattern)):
        if item.is_file() and item.suffix.lower() in IMAGE_EXTS:
            yield item


def infer_travel_doc_size(path: Path) -> tuple[int, int]:
    name = path.stem.lower()
    if "cover" in name or name.startswith("01-"):
        return PRESETS["cover"]  # type: ignore[return-value]
    if "route" in name or "map" in name or "traffic" in name or "transport" in name:
        return PRESETS["route"]  # type: ignore[return-value]
    if "food" in name or "gallery" in name or "attraction" in name:
        return PRESETS["gallery"]  # type: ignore[return-value]
    return PRESETS["day-card"]  # type: ignore[return-value]


def normalize_image(src: Path, dst: Path, size: tuple[int, int], mode: str) -> None:
    with Image.open(src) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        if mode == "fit":
            image.thumbnail(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", size, "white")
            left = (size[0] - image.width) // 2
            top = (size[1] - image.height) // 2
            canvas.paste(image, (left, top))
            output = canvas
        else:
            output = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

        dst.parent.mkdir(parents=True, exist_ok=True)
        output.save(dst, quality=92, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize travel guide images to fixed dimensions.")
    parser.add_argument("input", type=Path, help="Image file or directory.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory.")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Named size preset.")
    parser.add_argument("--size", type=parse_size, help="Explicit output size, e.g. 1200x900.")
    parser.add_argument("--mode", choices=["cover", "fit"], default="cover", help="cover crops; fit pads with white.")
    parser.add_argument("--recursive", action="store_true", help="Read images recursively when input is a directory.")
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"input does not exist: {args.input}")
    if not args.preset and not args.size:
        parser.error("provide --preset or --size")
    if args.preset and args.size:
        parser.error("use only one of --preset or --size")

    images = list(iter_images(args.input, args.recursive))
    if not images:
        parser.error("no images found")

    for src in images:
        size = args.size
        if args.preset == "travel-doc":
            size = infer_travel_doc_size(src)
        elif args.preset:
            size = PRESETS[args.preset]
        assert size is not None

        rel = src.name if args.input.is_file() else src.relative_to(args.input)
        dst = args.out / rel
        if dst.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            dst = dst.with_suffix(".jpg")
        normalize_image(src, dst, size, args.mode)
        print(f"{src} -> {dst} ({size[0]}x{size[1]})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
