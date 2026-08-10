#!/usr/bin/env python3
"""Render designed text and graphic layers onto a generated product image.

Usage:
  python scripts/render_text_overlay.py --input base.png --output final.png --layers layers.json

layers.json:
[
  {
    "type": "rect",
    "box": [48, 48, 852, 178],
    "fill": "#FFFFFFD9",
    "radius": 24
  },
  {
    "type": "text",
    "text": "轻盈不闷",
    "box": [80, 70, 860, 190],
    "font_size": 72,
    "color": "#111111",
    "font_weight": "bold",
    "align": "center",
    "valign": "middle",
    "stroke_width": 0,
    "stroke_fill": "#ffffff"
  },
  {
    "type": "price",
    "box": [72, 482, 360, 558],
    "currency": "¥",
    "amount": "420",
    "suffix": "起",
    "color": "#D61F3C"
  }
]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = {
    "regular": [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ],
    "bold": [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ],
}


def parse_color(value: str | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if isinstance(value, tuple):
        return value
    raw = value.strip().lstrip("#")
    if len(raw) == 6:
        return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4)) + (255,)
    if len(raw) == 8:
        return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4, 6))
    raise ValueError(f"Unsupported color: {value}")


def iter_font_paths(extra: str | None, weight: str) -> Iterable[str]:
    if extra:
        yield extra
    yield from FONT_CANDIDATES.get(weight, FONT_CANDIDATES["regular"])
    yield from FONT_CANDIDATES["regular"]


def load_font(size: int, weight: str = "regular", font_path: str | None = None) -> ImageFont.FreeTypeFont:
    for candidate in iter_font_paths(font_path, weight):
        if candidate and os.path.exists(candidate):
            return ImageFont.truetype(candidate, size=size)
    raise FileNotFoundError("No usable font found. Provide --font or install a CJK-capable font.")


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, stroke_width: int) -> tuple[int, int]:
    left, top, right, bottom = draw.multiline_textbbox((0, 0), text, font=font, spacing=6, stroke_width=stroke_width)
    return right - left, bottom - top


def normalize_box(layer: dict) -> list[int]:
    box = layer.get("box")
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError(f"Layer requires box [left, top, right, bottom]: {layer}")
    return [int(v) for v in box]


def draw_rounded_box(draw: ImageDraw.ImageDraw, box: list[int], fill: str, radius: int = 0, outline: str | None = None, width: int = 1) -> None:
    kwargs = {"fill": parse_color(fill)}
    if outline:
        kwargs["outline"] = parse_color(outline)
        kwargs["width"] = width
    if radius:
        draw.rounded_rectangle(box, radius=radius, **kwargs)
    else:
        draw.rectangle(box, **kwargs)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, stroke_width: int) -> str:
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        current = ""
        for char in paragraph:
            candidate = current + char
            width, _ = text_bbox(draw, candidate, font, stroke_width)
            if current and width > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        lines.append(current)
    return "\n".join(lines)


def fit_font(draw: ImageDraw.ImageDraw, text: str, box: list[int], layer: dict) -> tuple[ImageFont.FreeTypeFont, str]:
    x1, y1, x2, y2 = box
    max_width = max(1, x2 - x1)
    max_height = max(1, y2 - y1)
    requested = int(layer.get("font_size", 56))
    min_size = int(layer.get("min_font_size", 18))
    weight = str(layer.get("font_weight", "regular")).lower()
    stroke_width = int(layer.get("stroke_width", 0))
    font_path = layer.get("font")

    for size in range(requested, min_size - 1, -2):
        font = load_font(size=size, weight=weight, font_path=font_path)
        wrapped = wrap_text(draw, text, font, max_width, stroke_width)
        width, height = text_bbox(draw, wrapped, font, stroke_width)
        if width <= max_width and height <= max_height:
            return font, wrapped
    font = load_font(size=min_size, weight=weight, font_path=font_path)
    return font, wrap_text(draw, text, font, max_width, stroke_width)


def render_shape(draw: ImageDraw.ImageDraw, layer: dict) -> None:
    kind = str(layer.get("type", "rect")).lower()
    box = normalize_box(layer)
    if kind in {"rect", "rounded_rect", "card", "pill"}:
        draw_rounded_box(
            draw,
            box,
            fill=layer.get("fill", "#FFFFFF"),
            radius=int(layer.get("radius", 0 if kind == "rect" else 18)),
            outline=layer.get("outline"),
            width=int(layer.get("width", 1)),
        )
        return
    if kind == "line":
        color = parse_color(layer.get("color", "#111111"))
        draw.line([(box[0], box[1]), (box[2], box[3])], fill=color, width=int(layer.get("width", 2)))
        return
    raise ValueError(f"Unsupported shape layer type: {kind}")


def render_text(draw: ImageDraw.ImageDraw, layer: dict) -> None:
    text = str(layer["text"])
    box = normalize_box(layer)
    padding = int(layer.get("padding", 0))
    if layer.get("background"):
        draw_rounded_box(
            draw,
            box,
            fill=layer["background"],
            radius=int(layer.get("radius", 0)),
            outline=layer.get("outline"),
            width=int(layer.get("outline_width", 1)),
        )
    if padding:
        box = [box[0] + padding, box[1] + padding, box[2] - padding, box[3] - padding]
    x1, y1, x2, y2 = box
    stroke_width = int(layer.get("stroke_width", 0))
    font, rendered_text = fit_font(draw, text, box, layer)
    width, height = text_bbox(draw, rendered_text, font, stroke_width)

    align = str(layer.get("align", "left")).lower()
    valign = str(layer.get("valign", "top")).lower()
    if align == "center":
        x = x1 + (x2 - x1 - width) / 2
    elif align == "right":
        x = x2 - width
    else:
        x = x1
    if valign == "middle":
        y = y1 + (y2 - y1 - height) / 2
    elif valign == "bottom":
        y = y2 - height
    else:
        y = y1

    if layer.get("shadow"):
        shadow = layer["shadow"]
        offset = shadow.get("offset", [0, 2])
        draw.multiline_text(
            (x + int(offset[0]), y + int(offset[1])),
            rendered_text,
            font=font,
            fill=parse_color(shadow.get("color", "#00000040")),
            spacing=int(layer.get("spacing", 6)),
            align=align,
        )

    draw.multiline_text(
        (x, y),
        rendered_text,
        font=font,
        fill=parse_color(layer.get("color", "#111111")),
        spacing=int(layer.get("spacing", 6)),
        align=align,
        stroke_width=stroke_width,
        stroke_fill=parse_color(layer.get("stroke_fill", "#ffffff")),
    )


def render_price(draw: ImageDraw.ImageDraw, layer: dict) -> None:
    box = normalize_box(layer)
    x1, y1, x2, y2 = box
    color = parse_color(layer.get("color", "#D61F3C"))
    currency = str(layer.get("currency", "¥"))
    amount = str(layer["amount"])
    suffix = str(layer.get("suffix", ""))
    currency_font = load_font(int(layer.get("currency_size", 28)), "bold", layer.get("font"))
    amount_font = load_font(int(layer.get("amount_size", 56)), "bold", layer.get("font"))
    suffix_font = load_font(int(layer.get("suffix_size", 24)), "regular", layer.get("font"))
    gap = int(layer.get("gap", 6))

    cy = y1 + int(layer.get("currency_offset_y", 20))
    ay = y1
    sy = y1 + int(layer.get("suffix_offset_y", 28))
    currency_w = draw.textbbox((0, 0), currency, font=currency_font)[2]
    amount_w = draw.textbbox((0, 0), amount, font=amount_font)[2]
    suffix_w = draw.textbbox((0, 0), suffix, font=suffix_font)[2] if suffix else 0
    total_w = currency_w + gap + amount_w + (gap + suffix_w if suffix else 0)

    align = str(layer.get("align", "left")).lower()
    if align == "center":
        x = x1 + (x2 - x1 - total_w) / 2
    elif align == "right":
        x = x2 - total_w
    else:
        x = x1

    draw.text((x, cy), currency, font=currency_font, fill=color)
    draw.text((x + currency_w + gap, ay), amount, font=amount_font, fill=color)
    if suffix:
        draw.text((x + currency_w + gap + amount_w + gap, sy), suffix, font=suffix_font, fill=color)


def render_layer(image: Image.Image, layer: dict) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    kind = str(layer.get("type", "text")).lower()
    if kind in {"rect", "rounded_rect", "card", "pill", "line"}:
        render_shape(draw, layer)
    elif kind == "price":
        render_price(draw, layer)
    elif kind == "text":
        render_text(draw, layer)
    else:
        raise ValueError(f"Unsupported layer type: {kind}")
    image.alpha_composite(overlay)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--layers", required=True)
    args = parser.parse_args()

    image = Image.open(args.input).convert("RGBA")
    layers = json.loads(Path(args.layers).read_text(encoding="utf-8"))
    for layer in layers:
        render_layer(image, layer)
    image.convert("RGB").save(args.output, quality=95)


if __name__ == "__main__":
    main()
