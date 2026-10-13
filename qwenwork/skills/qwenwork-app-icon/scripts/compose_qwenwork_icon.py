#!/usr/bin/env python3
"""
Compose a macOS-style app icon that centers the QwenWork isometric logo on a
themed rounded-square background.

Usage:
    python3 compose_qwenwork_icon.py <output.png> [options]

Options:
    --logo <path>           Logo PNG or SVG to place. Default: assets/qwenwork-logo-3d.svg
    --bg-style <name>       One of: dark, brand-green, gradient-green, white, custom.
                            Default: dark
    --bg-color <hex>        Solid background color for --bg-style custom, e.g. #161616
    --bg-gradient <hex,hex> Two-stop gradient (top,bottom) for --bg-style custom,
                            e.g. #41D87E,#2DD370. Overrides --bg-color when given.
    --scale <float>         Logo width as fraction of canvas (0.4~0.8). Default: 0.62
    --size <int>            Output pixel size (square). Default: 2048
    --corner <float>        Rounded corner ratio (0~0.5). Default: 0.225 (Big Sur squircle)
    --no-shadow             Skip the soft drop shadow under the logo.

Requirements:
    pip3 install --break-system-packages Pillow

Notes:
  * SVG logos are rasterized via `qlmanage -t -s <size>` (macOS Quick Look),
    which understands complex SVG effects better than cairosvg/rsvg for this
    particular brand file. Falls back to cairosvg if qlmanage is unavailable.
  * The output PNG is intended as the source for png_to_icns.py, but is itself
    already macOS-compliant if used raw.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter

BRAND = {
    "green_500":  "#41D87E",
    "green_600":  "#2DD370",
    "green_300":  "#56E891",
    "gray_950":   "#161616",
    "gray_100":   "#EAEAEA",
    "white":      "#FFFFFF",
}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rasterize_svg(svg_path: str, size: int) -> Image.Image:
    """Render SVG to a size×size RGBA image. Prefer qlmanage (macOS) then cairosvg."""
    with tempfile.TemporaryDirectory() as td:
        # 1) qlmanage
        if shutil.which("qlmanage"):
            subprocess.run(
                ["qlmanage", "-t", "-s", str(size), "-o", td, svg_path],
                check=True, capture_output=True,
            )
            out = os.path.join(td, os.path.basename(svg_path) + ".png")
            if os.path.exists(out):
                return Image.open(out).convert("RGBA")
        # 2) cairosvg fallback
        try:
            import cairosvg  # type: ignore
            out = os.path.join(td, "out.png")
            cairosvg.svg2png(url=svg_path, write_to=out,
                             output_width=size, output_height=size)
            return Image.open(out).convert("RGBA")
        except Exception as e:  # pragma: no cover
            raise SystemExit(f"Failed to rasterize SVG: {e}. "
                             f"Install cairosvg or ensure qlmanage is available.")


def load_logo(logo_path: str, size: int) -> Image.Image:
    """Load a logo file (SVG or raster). Auto-crops surrounding empty space and
    returns an RGBA image."""
    if logo_path.lower().endswith(".svg"):
        img = rasterize_svg(logo_path, size)
    else:
        img = Image.open(logo_path).convert("RGBA")

    # Auto-crop: treat near-transparent OR near-background pixels as empty.
    # This handles the case where the "3d logo" SVG is drawn on solid #161616.
    import numpy as np
    arr = np.array(img)
    alpha = arr[:, :, 3]
    rgb_sum = arr[:, :, :3].sum(axis=2)
    # Content = non-transparent AND not near-black background
    mask = (alpha > 20) & (rgb_sum > 90)
    if mask.any():
        ys, xs = np.where(mask)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        img = img.crop((x0, y0, x1 + 1, y1 + 1))
        # Force transparency wherever we treated as background
        larr = np.array(img)
        lmask = larr[:, :, :3].sum(axis=2) < 90
        larr[lmask] = [0, 0, 0, 0]
        img = Image.fromarray(larr, "RGBA")
    return img


def make_background(size: int, corner: float, style: str,
                    bg_color: str | None, bg_gradient: str | None) -> tuple[Image.Image, Image.Image]:
    """Return (bg_rgba, rounded_mask_L)."""
    r = int(size * corner)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=255)

    style = style.lower()
    if style == "custom":
        if bg_gradient:
            top_hex, bot_hex = [c.strip() for c in bg_gradient.split(",")]
            top, bot = hex_to_rgb(top_hex), hex_to_rgb(bot_hex)
            grad = Image.new("RGB", (1, size))
            for y in range(size):
                t = y / (size - 1)
                grad.putpixel((0, y), tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
            bg = grad.resize((size, size)).convert("RGBA")
        else:
            color = hex_to_rgb(bg_color or BRAND["gray_950"])
            bg = Image.new("RGBA", (size, size), color + (255,))
    elif style == "soft-white":
        # White → very light green — matches the bundled default and gives Qianzai
        # (green mascot) maximum contrast without looking sterile.
        top, bot = (255, 255, 255), (232, 250, 240)
        grad = Image.new("RGB", (1, size))
        for y in range(size):
            t = y / (size - 1)
            grad.putpixel((0, y), tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
        bg = grad.resize((size, size)).convert("RGBA")
    elif style == "dark":
        # Subtle vertical gradient #1c1c1c -> #0a0a0a
        top, bot = (28, 28, 28), (8, 8, 8)
        grad = Image.new("RGB", (1, size))
        for y in range(size):
            t = y / (size - 1)
            grad.putpixel((0, y), tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
        bg = grad.resize((size, size)).convert("RGBA")
    elif style == "brand-green":
        bg = Image.new("RGBA", (size, size), hex_to_rgb(BRAND["green_500"]) + (255,))
    elif style == "gradient-green":
        top, bot = hex_to_rgb(BRAND["green_300"]), hex_to_rgb(BRAND["green_600"])
        grad = Image.new("RGB", (1, size))
        for y in range(size):
            t = y / (size - 1)
            grad.putpixel((0, y), tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
        bg = grad.resize((size, size)).convert("RGBA")
    elif style == "white":
        bg = Image.new("RGBA", (size, size), hex_to_rgb(BRAND["white"]) + (255,))
    else:
        raise SystemExit(f"Unknown --bg-style: {style}")

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(bg, (0, 0), mask)

    # Inner highlight for depth (skip on white / soft-white — looks noisy on light bg)
    if style not in ("white", "soft-white"):
        hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hl)
        for i in range(6):
            hd.rounded_rectangle((i, i, size - 1 - i, size - 1 - i),
                                 radius=r - i, outline=(255, 255, 255, 10 - i), width=1)
        canvas = Image.alpha_composite(canvas, hl)
    return canvas, mask


def compose(args) -> None:
    size = args.size
    canvas, mask = make_background(size, args.corner, args.bg_style,
                                   args.bg_color, args.bg_gradient)

    logo = load_logo(args.logo, size)
    # Fit logo into a square bounding box while preserving aspect
    lw, lh = logo.size
    scale = args.scale
    target_side = int(size * scale)
    r = max(lw, lh)
    ratio = target_side / r
    logo = logo.resize((int(lw * ratio), int(lh * ratio)), Image.LANCZOS)
    tw, th = logo.size

    if not args.no_shadow:
        shadow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        alpha = logo.split()[3]
        sh = Image.new("RGBA", logo.size, (0, 0, 0, 0))
        sh.putalpha(alpha.point(lambda a: int(a * 0.35)))
        sx = (size - tw) // 2
        sy = (size - th) // 2 + int(size * 0.02)
        shadow_layer.paste(sh, (sx, sy))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=size * 0.012))
        canvas = Image.alpha_composite(canvas, shadow_layer)

    canvas.paste(logo, ((size - tw) // 2, (size - th) // 2), logo)

    # Re-apply rounded mask so nothing bleeds outside squircle
    final = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    final.paste(canvas, (0, 0), mask)
    final.save(args.output, "PNG")
    print(f"Saved: {args.output} ({os.path.getsize(args.output)} bytes)")


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    default_logo = os.path.normpath(os.path.join(here, "..", "assets", "qianzai-mascot.svg"))

    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--logo", default=default_logo)
    ap.add_argument("--bg-style", default="soft-white",
                    choices=["soft-white", "dark", "brand-green", "gradient-green", "white", "custom"])
    ap.add_argument("--bg-color", default=None)
    ap.add_argument("--bg-gradient", default=None)
    ap.add_argument("--scale", type=float, default=0.62)
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--corner", type=float, default=0.225)
    ap.add_argument("--no-shadow", action="store_true")
    args = ap.parse_args()
    compose(args)


if __name__ == "__main__":
    main()
