#!/usr/bin/env python3
"""Deterministically typeset exact Chinese or English poster copy over a key visual."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont


FONT_CANDIDATES = {
    "sans": [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ],
    "serif": [
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    ],
    "latin-sans": [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
    "latin-serif": [
        "/System/Library/Fonts/NewYork.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    ],
    "latin-display": [
        "/System/Library/Fonts/Avenir Next Condensed.ttc",
        "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
}
ROLES = {
    "eyebrow",
    "headline",
    "support",
    "benefit",
    "badge",
    "cta",
    "closing_slogan",
    "footer",
    "legal",
}
DEFAULT_MAX_LINES = {
    "eyebrow": 1,
    "headline": 2,
    "support": 2,
    "benefit": 2,
    "badge": 2,
    "cta": 1,
    "closing_slogan": 2,
    "footer": 1,
    "legal": 3,
}

TEMPLATE = {
    "input": "/absolute/path/key-visual.png",
    "output": "/absolute/path/final-poster.png",
    "language": "zh-CN",
    "safe_margin_percent": 2,
    "regions": [
        {
            "role": "headline",
            "text": "精确主标题",
            "box_percent": [7, 8, 86, 18],
            "font": "serif",
            "max_font_size": 150,
            "min_font_size": 36,
            "color": "#FFF4E1",
            "align": "center",
            "valign": "center",
            "line_spacing": 0.12,
            "max_lines": 2,
            "stroke_width": 0,
            "stroke_fill": "#000000",
            "shadow": {"offset": [0, 4], "fill": "#00000080"},
            "background": None,
        },
        {
            "role": "cta",
            "text": "立即了解",
            "box_percent": [24, 82, 52, 8],
            "font": "sans",
            "max_font_size": 72,
            "min_font_size": 28,
            "color": "#111111",
            "align": "center",
            "valign": "center",
            "line_spacing": 0.1,
            "max_lines": 1,
            "stroke_width": 0,
            "stroke_fill": "#000000",
            "shadow": None,
            "background": {
                "fill": "#F7D994",
                "outline": "#FFF4D8",
                "width": 3,
                "radius_percent": 45,
            },
        },
    ],
}


def resolve_font(value: str) -> str:
    if value in FONT_CANDIDATES:
        for candidate in FONT_CANDIDATES[value]:
            if Path(candidate).is_file():
                return candidate
        raise FileNotFoundError(f"no installed font found for alias: {value}")
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(f"font not found: {value}")
    return str(path)


def rgba(value: str) -> tuple[int, int, int, int]:
    return ImageColor.getcolor(value, "RGBA")


def percent_box(values: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    if len(values) != 4:
        raise ValueError("box_percent must be [x, y, width, height]")
    x, y, w, h = values
    if not all(isinstance(item, (int, float)) for item in values):
        raise ValueError("box_percent values must be numeric")
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 100 or y + h > 100:
        raise ValueError("box_percent must stay inside 0–100")
    return (
        round(width * x / 100),
        round(height * y / 100),
        round(width * (x + w) / 100),
        round(height * (y + h) / 100),
    )


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, stroke: int) -> int:
    box = draw.textbbox((0, 0), text or " ", font=font, stroke_width=stroke)
    return box[2] - box[0]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    stroke: int,
) -> str:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if " " in paragraph and any("A" <= char.upper() <= "Z" for char in paragraph):
            words = paragraph.split()
            current = ""
            for word in words:
                trial = f"{current} {word}".strip()
                if current and text_width(draw, trial, font, stroke) > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = trial
            lines.append(current)
            continue
        current = ""
        for char in paragraph:
            trial = current + char
            if current and text_width(draw, trial, font, stroke) > max_width:
                lines.append(current)
                current = char
            else:
                current = trial
        lines.append(current)
    return "\n".join(lines)


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    max_size: int,
    min_size: int,
    box_width: int,
    box_height: int,
    spacing_ratio: float,
    stroke: int,
    max_lines: int,
) -> tuple[ImageFont.FreeTypeFont, str, int, tuple[int, int, int, int]]:
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size=size)
        wrapped = wrap_text(draw, text, font, box_width, stroke)
        if len(wrapped.splitlines()) > max_lines:
            continue
        spacing = max(0, round(size * spacing_ratio))
        bounds = draw.multiline_textbbox(
            (0, 0), wrapped, font=font, spacing=spacing, stroke_width=stroke, align="left"
        )
        if bounds[2] - bounds[0] <= box_width and bounds[3] - bounds[1] <= box_height:
            return font, wrapped, spacing, bounds
    raise ValueError(f"text does not fit region even at min_font_size={min_size}: {text}")


def validate_config(data: dict, require_files: bool) -> list[str]:
    errors: list[str] = []
    for key in ("input", "output"):
        value = data.get(key)
        if not isinstance(value, str) or not value.startswith("/"):
            errors.append(f"{key} must be an absolute path")
    if require_files and isinstance(data.get("input"), str) and not Path(data["input"]).is_file():
        errors.append(f"input does not exist: {data['input']}")

    language = data.get("language", "zh-CN")
    if language not in {"zh-CN", "en"}:
        errors.append("language must be zh-CN or en")

    margin = data.get("safe_margin_percent", 2)
    if not isinstance(margin, (int, float)) or not 0 <= margin <= 10:
        errors.append("safe_margin_percent must be 0–10")

    regions = data.get("regions")
    if not isinstance(regions, list) or not regions:
        errors.append("regions must be a non-empty array")
        return errors
    if len(regions) > 18:
        errors.append("regions may not exceed 18; simplify the information design")

    seen: set[tuple[str, str]] = set()
    for index, region in enumerate(regions):
        prefix = f"regions[{index}]"
        if not isinstance(region, dict):
            errors.append(f"{prefix} must be an object")
            continue
        role = region.get("role")
        if role not in ROLES:
            errors.append(f"{prefix}.role must be one of {sorted(ROLES)}")
        text = region.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{prefix}.text must be non-empty exact copy")
        key = (str(role), str(text))
        if key in seen:
            errors.append(f"{prefix} duplicates an identical role/text region")
        seen.add(key)
        try:
            box = region.get("box_percent")
            if not isinstance(box, list):
                raise ValueError("box_percent must be an array")
            percent_box(box, 100, 100)
            x, y, w, h = box
            if x < margin or x + w > 100 - margin:
                errors.append(f"{prefix} violates horizontal safe margin")
            if role == "cta" and y + h > 94:
                errors.append(f"{prefix} CTA must end at or above 94% height")
            if role == "legal" and y < 90:
                errors.append(f"{prefix} legal copy belongs in the bottom 10%")
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
        try:
            resolve_font(str(region.get("font", "sans")))
        except FileNotFoundError as exc:
            errors.append(f"{prefix}: {exc}")
        for key_name in ("max_font_size", "min_font_size"):
            if not isinstance(region.get(key_name), int) or region[key_name] <= 0:
                errors.append(f"{prefix}.{key_name} must be a positive integer")
        if (
            isinstance(region.get("max_font_size"), int)
            and isinstance(region.get("min_font_size"), int)
            and region["max_font_size"] < region["min_font_size"]
        ):
            errors.append(f"{prefix}.max_font_size must be >= min_font_size")
        max_lines = region.get("max_lines", DEFAULT_MAX_LINES.get(str(role), 2))
        if not isinstance(max_lines, int) or max_lines <= 0:
            errors.append(f"{prefix}.max_lines must be a positive integer")
        if region.get("align", "left") not in {"left", "center", "right"}:
            errors.append(f"{prefix}.align must be left, center, or right")
        if region.get("valign", "top") not in {"top", "center", "bottom"}:
            errors.append(f"{prefix}.valign must be top, center, or bottom")
        for color_key in ("color", "stroke_fill"):
            try:
                rgba(str(region.get(color_key, "#000000")))
            except ValueError:
                errors.append(f"{prefix}.{color_key} is not a valid color")
    return errors


def render(data: dict) -> None:
    image = Image.open(data["input"]).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for region in data["regions"]:
        left, top, right, bottom = percent_box(region["box_percent"], *image.size)
        box_width, box_height = right - left, bottom - top

        background = region.get("background")
        if background:
            radius = round(min(box_width, box_height) * background.get("radius_percent", 20) / 100)
            draw.rounded_rectangle(
                (left, top, right, bottom),
                radius=radius,
                fill=rgba(background.get("fill", "#00000000")),
                outline=rgba(background.get("outline", "#00000000")),
                width=int(background.get("width", 0)),
            )

        font_path = resolve_font(region.get("font", "sans"))
        stroke = int(region.get("stroke_width", 0))
        font, wrapped, spacing, bounds = fit_text(
            draw,
            region["text"],
            font_path,
            int(region["max_font_size"]),
            int(region["min_font_size"]),
            box_width,
            box_height,
            float(region.get("line_spacing", 0.1)),
            stroke,
            int(region.get("max_lines", DEFAULT_MAX_LINES[region["role"]])),
        )
        text_w, text_h = bounds[2] - bounds[0], bounds[3] - bounds[1]
        align = region.get("align", "left")
        valign = region.get("valign", "top")
        x = left if align == "left" else right - text_w if align == "right" else left + (box_width - text_w) / 2
        y = top if valign == "top" else bottom - text_h if valign == "bottom" else top + (box_height - text_h) / 2

        shadow = region.get("shadow")
        if shadow:
            dx, dy = shadow.get("offset", [0, 2])
            draw.multiline_text(
                (x + dx, y + dy),
                wrapped,
                font=font,
                fill=rgba(shadow.get("fill", "#00000080")),
                spacing=spacing,
                align=align,
                stroke_width=stroke,
                stroke_fill=rgba(region.get("stroke_fill", "#000000")),
            )
        draw.multiline_text(
            (x, y),
            wrapped,
            font=font,
            fill=rgba(region.get("color", "#FFFFFF")),
            spacing=spacing,
            align=align,
            stroke_width=stroke,
            stroke_fill=rgba(region.get("stroke_fill", "#000000")),
        )

    result = Image.alpha_composite(image, overlay)
    output = Path(data["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output)
    print(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", nargs="?")
    parser.add_argument("--write-template", metavar="PATH")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--skip-file-exists", action="store_true")
    args = parser.parse_args()

    if args.write_template:
        path = Path(args.write_template)
        path.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n")
        print(path)
        return 0
    if not args.config:
        parser.error("config is required unless --write-template is used")
    try:
        data = json.loads(Path(args.config).read_text())
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_config(data, not args.skip_file_exists)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAIL: {len(errors)} error(s)", file=sys.stderr)
        return 1
    if args.validate_only:
        print("PASS: typesetting config is valid")
        return 0
    try:
        render(data)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
