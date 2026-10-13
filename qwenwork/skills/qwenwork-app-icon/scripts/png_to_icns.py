#!/usr/bin/env python3
"""
Convert a PNG / JPG / any Pillow-readable image to a macOS .icns file.

Usage:
    python3 png_to_icns.py <source_image> <output.icns>

Requirements:
    pip3 install --break-system-packages Pillow

Behaviour:
  * Auto-converts to RGBA (adds transparency channel if source is JPG/RGB).
  * Pads non-square input to square with transparent background.
  * Emits an .iconset folder with all 10 required sizes:
        16, 32, 128, 256, 512  (base)  +  @2x retina variants (32, 64, 256, 512, 1024)
  * Runs `iconutil -c icns` to produce the final .icns.
  * Cleans up the intermediate .iconset folder on success.
"""

import os
import shutil
import subprocess
import sys

from PIL import Image


def convert(source_image: str, output_icns: str) -> None:
    if not os.path.exists(source_image):
        print(f"Error: Source image not found: {source_image}")
        sys.exit(1)

    img = Image.open(source_image).convert("RGBA")
    w, h = img.size
    print(f"Source image: {w}x{h}")

    if w != h:
        size = max(w, h)
        square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        square.paste(img, ((size - w) // 2, (size - h) // 2))
        img = square
        print(f"Padded to square: {size}x{size}")

    if img.size[0] < 1024:
        print(f"Warning: source is only {img.size[0]}px; upscaling to 1024px via LANCZOS "
              f"(quality will degrade — recommend ≥1024x1024 source).")

    iconset_dir = output_icns.replace(".icns", ".iconset")
    if os.path.exists(iconset_dir):
        shutil.rmtree(iconset_dir)
    os.makedirs(iconset_dir)

    sizes = [
        (16,  "icon_16x16.png",     32,   "icon_16x16@2x.png"),
        (32,  "icon_32x32.png",     64,   "icon_32x32@2x.png"),
        (128, "icon_128x128.png",   256,  "icon_128x128@2x.png"),
        (256, "icon_256x256.png",   512,  "icon_256x256@2x.png"),
        (512, "icon_512x512.png",   1024, "icon_512x512@2x.png"),
    ]

    for base_size, base_name, retina_size, retina_name in sizes:
        img.resize((base_size, base_size), Image.LANCZOS).save(
            os.path.join(iconset_dir, base_name), "PNG")
        img.resize((retina_size, retina_size), Image.LANCZOS).save(
            os.path.join(iconset_dir, retina_name), "PNG")

    print(f"Created .iconset with {len(sizes) * 2} images")

    result = subprocess.run(
        ["iconutil", "-c", "icns", iconset_dir, "-o", output_icns],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"iconutil error: {result.stderr}")
        sys.exit(1)

    shutil.rmtree(iconset_dir)
    print(f"Generated .icns: {output_icns} ({os.path.getsize(output_icns)} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 png_to_icns.py <source_image> <output.icns>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
