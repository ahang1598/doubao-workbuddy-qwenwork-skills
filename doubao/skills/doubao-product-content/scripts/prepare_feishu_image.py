#!/usr/bin/env python3
"""Export display-safe images for Feishu/Lark documents.

The output is flattened to RGB, optionally trimmed, and resized to a bounded
display image while preserving aspect ratio. Use --preset body for image
blocks/cards and --preset table for compact table thumbnails.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    if image.mode != "RGBA":
        return None
    alpha = image.getchannel("A")
    return alpha.point(lambda p: 255 if p > 8 else 0).getbbox()


def corner_background(rgb: Image.Image) -> tuple[int, int, int]:
    w, h = rgb.size
    samples = [
        rgb.getpixel((0, 0)),
        rgb.getpixel((w - 1, 0)),
        rgb.getpixel((0, h - 1)),
        rgb.getpixel((w - 1, h - 1)),
    ]
    return tuple(int(sum(px[i] for px in samples) / len(samples)) for i in range(3))


def background_bbox(rgb: Image.Image, fuzz: int) -> tuple[int, int, int, int] | None:
    bg = Image.new("RGB", rgb.size, corner_background(rgb))
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > fuzz else 0)
    return mask.getbbox()


def expand_box(box: tuple[int, int, int, int], size: tuple[int, int], padding: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    w, h = size
    return (
        max(0, left - padding),
        max(0, top - padding),
        min(w, right + padding),
        min(h, bottom + padding),
    )


def trim_image(image: Image.Image, trim_white: bool, fuzz: int, padding: int) -> Image.Image:
    bbox = alpha_bbox(image)
    rgb = Image.new("RGB", image.size, "white")
    if image.mode == "RGBA":
        rgb.paste(image, mask=image.getchannel("A"))
    else:
        rgb.paste(image.convert("RGB"))

    if bbox is None and trim_white:
        bbox = background_bbox(rgb, fuzz)

    if bbox:
        bbox = expand_box(bbox, rgb.size, padding)
        return rgb.crop(bbox)
    return rgb


def resize_for_display(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    w, h = image.size
    scale = min(max_width / w, max_height / h, 1.0)
    if scale >= 1.0:
        return image
    return image.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)


def is_mostly_blank(image: Image.Image) -> bool:
    stat = ImageStat.Stat(image.convert("L"))
    return stat.stddev[0] < 1.5


def process_one(src: Path, out_dir: Path, args: argparse.Namespace) -> Path:
    image = Image.open(src)
    display = trim_image(image, args.trim_white, args.fuzz, args.padding)
    display = resize_for_display(display, args.max_width, args.max_height)
    if is_mostly_blank(display):
        raise ValueError(f"Output looks blank after trimming: {src}")

    suffix = ".jpg" if args.format == "jpeg" else ".png"
    out = out_dir / f"{src.stem}_feishu{suffix}"
    if args.format == "jpeg":
        display.save(out, quality=args.quality, optimize=True)
    else:
        display.save(out, optimize=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", help="Source image paths")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--preset",
        choices=["body", "table"],
        default="body",
        help="body: medium images for document image blocks/cards; table: compact thumbnails for table cells",
    )
    parser.add_argument("--max-width", type=int)
    parser.add_argument("--max-height", type=int)
    parser.add_argument("--padding", type=int, default=12)
    parser.add_argument("--trim-white", action="store_true")
    parser.add_argument("--fuzz", type=int, default=10)
    parser.add_argument("--format", choices=["png", "jpeg"], default="jpeg")
    parser.add_argument("--quality", type=int, default=92)
    args = parser.parse_args()
    if args.max_width is None:
        args.max_width = 720 if args.preset == "body" else 220
    if args.max_height is None:
        args.max_height = 960 if args.preset == "body" else 320

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in args.images:
        out = process_one(Path(item), out_dir, args)
        print(out)


if __name__ == "__main__":
    main()
