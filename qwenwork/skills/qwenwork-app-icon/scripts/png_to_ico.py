#!/usr/bin/env python3
"""
Convert a PNG / JPG / any Pillow-readable image to a Windows .ico file.

Usage:
    python3 png_to_ico.py <source_image> <output.ico>

Requirements:
    pip3 install --break-system-packages Pillow

Behaviour:
  * Auto-converts to RGBA (adds transparency channel if source is JPG/RGB).
  * Pads non-square input to square with transparent background.
  * Emits a multi-resolution .ico containing every size Windows Explorer /
    File Explorer / taskbar consumes: 16, 24, 32, 48, 64, 128, 256.
    (Pillow's ICO writer uses the 256×256 PNG-encoded slot for the largest
    entry, which is what modern Windows expects.)

Reference: https://learn.microsoft.com/en-us/windows/win32/uxguide/vis-icons
"""

import os
import sys

from PIL import Image

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48),
             (64, 64), (128, 128), (256, 256)]


def convert(source_image: str, output_ico: str) -> None:
    if not os.path.exists(source_image):
        print(f"Error: Source image not found: {source_image}")
        sys.exit(1)

    img = Image.open(source_image).convert("RGBA")
    w, h = img.size
    print(f"Source image: {w}x{h}")

    if w != h:
        side = max(w, h)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(img, ((side - w) // 2, (side - h) // 2))
        img = square
        print(f"Padded to square: {side}x{side}")

    if img.size[0] < 256:
        print(f"Warning: source is only {img.size[0]}px; upscaling to 256px "
              f"via LANCZOS. Recommend ≥256×256 source for crisp taskbar icons.")

    img.save(output_ico, format="ICO", sizes=ICO_SIZES)
    print(f"Generated .ico: {output_ico} ({os.path.getsize(output_ico)} bytes) "
          f"with sizes {[s[0] for s in ICO_SIZES]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 png_to_ico.py <source_image> <output.ico>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
