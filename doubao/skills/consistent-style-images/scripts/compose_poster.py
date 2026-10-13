#!/usr/bin/env python3
"""Compose an approved layout using actual brand assets/fonts. Never calls image APIs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

from profile_utils import asset_file, load_profile


def resolve(value, base):
    return (base / value).resolve()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compose(config_path):
    spec = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent
    width, height = spec["width"], spec["height"]
    if any(type(n) is not int or n <= 0 for n in (width, height)):
        raise ValueError("width and height must be positive integers")
    output = resolve(spec["output"], base)
    report_path = output.with_suffix(".render.json")
    if output.suffix.lower() != ".png":
        raise ValueError("output must be PNG")
    if output.exists() or report_path.exists():
        raise ValueError("output or render record already exists; choose a versioned filename")
    if not spec.get("brand_profile"):
        raise ValueError("brand_profile required; no default brand")
    profile_path = resolve(spec["brand_profile"], base)
    profile, fingerprint = load_profile(profile_path, spec.get("rule_overrides", []))
    if spec.get("brand_id") != profile["id"] or spec.get("profile_fingerprint") != fingerprint:
        raise ValueError("brand mismatch or stale profile fingerprint")
    constraints = profile.get("constraints", {})
    palette = spec.get("palette", {})
    if not isinstance(palette, dict) or any(not isinstance(c, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in palette.values()):
        raise ValueError("palette values must be six-digit colors chosen for this brand/task")
    if spec.get("base_image"):
        with Image.open(resolve(spec["base_image"], base)) as source:
            if source.size != (width, height):
                raise ValueError("base image dimensions differ; this script will not crop/stretch it")
            canvas = source.convert("RGBA")
    else:
        canvas = Image.new("RGBA", (width, height), spec.get("background", "#FFFFFF"))
    draw = ImageDraw.Draw(canvas)
    levels = spec.get("levels", {})
    if not isinstance(levels, dict):
        raise ValueError("levels must be a named object")
    fonts, font_records = {}, {}
    def read_font(key, size, axes=None):
        path, digest, _ = asset_file(profile, profile_path, "fonts", key)
        font = ImageFont.truetype(str(path), size)
        if axes:
            available = font.get_variation_axes()
            names = [a["name"].decode() if isinstance(a["name"], bytes) else a["name"] for a in available]
            if set(axes) - set(names):
                raise ValueError("unknown variable font axis")
            font.set_variation_by_axes([axes.get(name, a["default"]) for name, a in zip(names, available)])
        font_records[key] = {"path": str(path), "sha256": digest}
        return font
    for name, level in levels.items():
        size = level["size"]
        if type(size) is not int or size <= 0:
            raise ValueError("font sizes must be positive integers")
        primary_font = read_font(level["font"], size, level.get("axes"))
        latin_font = read_font(level["latin_font"], size, level.get("latin_axes")) if level.get("latin_font") else primary_font
        fonts[name] = (primary_font, latin_font)
    used_colors, used_levels, boxes, drawn = set(), set(), [], []

    def check_box(box, label):
        x0, y0, x1, y1 = box
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height or x1 <= x0 or y1 <= y0:
            raise ValueError(f"{label}: invalid or out-of-canvas bounds")
        for other, other_label in boxes:
            if max(x0, other[0]) < min(x1, other[2]) and max(y0, other[1]) < min(y1, other[3]):
                raise ValueError(f"{label}: overlaps {other_label}")
        boxes.append((box, label))

    def render_line(line, label, inside=None):
        level = line["level"]
        chinese, latin = fonts[level]
        used_levels.add(level)
        align = line.get("align", "left")
        if align not in ("left", "center", "right"):
            raise ValueError("renderer supports left/center/right; use another tool for other layouts")
        allowed = constraints.get("allowed_alignments")
        if allowed is not None and align not in allowed:
            raise ValueError("alignment violates selected profile/task rules")
        segments = []
        for run in line["runs"]:
            color = run["color"]
            if color not in palette:
                raise ValueError(f"{label}: text color role not in selected palette")
            if not isinstance(run["text"], str) or "\n" in run["text"]:
                raise ValueError(f"{label}: each line must be an explicit single-line string")
            used_colors.add(color)
            # Split scripts using the selected brand font pair; no fallback to another brand.
            for text in re.findall(r"[\x00-\u024f]+|[^\x00-\u024f]+", run["text"]):
                font = latin if ord(text[0]) <= 0x024F else chinese
                segments.append((text, font, palette[color]))
        text_width = sum(font.getlength(text) for text, font, _ in segments)
        if text_width <= 0 or text_width > line["max_width"]:
            raise ValueError(f"{label}: empty/overflowing text; edit layout, do not squeeze or shrink it")
        x = line["x"] - (text_width / 2 if align == "center" else text_width if align == "right" else 0)
        y = line["baseline_y"]
        bounds = []
        cursor = x
        for text, font, color in segments:
            b = draw.textbbox((cursor, y), text, font=font, anchor="ls")
            bounds.append(b)
            cursor += font.getlength(text)
        box = (min(b[0] for b in bounds), min(b[1] for b in bounds),
               max(b[2] for b in bounds), max(b[3] for b in bounds))
        if inside is not None:
            if box[0] < inside[0] or box[1] < inside[1] or box[2] > inside[2] or box[3] > inside[3]:
                raise ValueError(f"{label}: text does not fit button padding")
        else:
            check_box(box, label)
        cursor = x
        for text, font, color in segments:
            draw.text((cursor, y), text, font=font, fill=color, anchor="ls")
            cursor += font.getlength(text)
        drawn.append({"label": label, "text": "".join(r["text"] for r in line["runs"]),
                      "level": level, "bbox": list(box)})

    logo_record = None
    logo_spec = spec.get("logo")
    if logo_spec:
        logo_path, logo_digest, asset = asset_file(profile, profile_path, "assets", logo_spec["asset"])
        with Image.open(logo_path) as original:
            logo = original.convert("RGBA")
        logo_width = logo_spec["width"]
        if type(logo_width) is not int or logo_width <= 0:
            raise ValueError("logo width must be positive integer")
        logo_height = round(logo_width * logo.height / logo.width)
        if logo_height < asset.get("min_height_px", 1):
            raise ValueError("logo height below selected asset minimum")
        x, y = logo_spec["x"], logo_spec["y"]
        margin = logo_spec["clear_space"]
        if not isinstance(margin, (int, float)) or margin < 0:
            raise ValueError("clear_space must be nonnegative")
        check_box((x-margin, y-margin, x+logo_width+margin, y+logo_height+margin), "logo clear space")
        canvas.alpha_composite(logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS), (x, y))
        logo_record = {"asset": logo_spec["asset"], "path": str(logo_path), "sha256": logo_digest}
    for i, line in enumerate(spec.get("lines", [])):
        render_line(line, f"line-{i+1}")
    ctas = spec.get("ctas", [])
    if not isinstance(ctas, list):
        raise ValueError("ctas must be a list, empty for no CTA")
    if constraints.get("cta_required") and not ctas:
        raise ValueError("selected profile/task requires CTA")
    for i, cta in enumerate(ctas):
        x, y, w, h = cta["box"]
        check_box((x, y, x+w, y+h), f"CTA-{i+1}")
        padding = cta["padding"]
        if padding < 0 or padding*2 >= min(w,h):
            raise ValueError("CTA padding must leave a positive inner rectangle")
        shape = cta.get("shape", "rectangle")
        allowed = constraints.get("allowed_button_shapes")
        if allowed is not None and shape not in allowed:
            raise ValueError("button shape violates selected profile/task rules")
        if shape == "rectangle":
            draw.rectangle((x,y,x+w-1,y+h-1), fill=cta["fill"])
        elif shape == "rounded_rectangle":
            radius = cta["radius"]
            if not 0 <= radius <= min(w,h)/2:
                raise ValueError("invalid corner radius")
            draw.rounded_rectangle((x,y,x+w-1,y+h-1), radius=radius, fill=cta["fill"])
        else:
            raise ValueError("renderer only supports rectangular buttons; choose another tool for this shape")
        align = cta.get("align", "center")
        anchor_x = x+w/2 if align == "center" else x+padding if align == "left" else x+w-padding
        line = {"level": cta["level"], "align": align, "x": anchor_x, "baseline_y": cta["baseline_y"],
                "max_width": w-2*padding, "runs": cta["runs"]}
        render_line(line, f"CTA-{i+1} text", (x+padding,y+padding,x+w-padding,y+h-padding))
    maximum = constraints.get("max_text_levels")
    if maximum is not None and len(used_levels) > maximum:
        raise ValueError("text hierarchy exceeds selected profile/task limit")
    options = constraints.get("palette_options")
    if used_colors and options is not None:
        exact = constraints.get("require_all_palette_colors", False)
        if not any(used_colors == set(o) if exact else used_colors <= set(o) for o in options):
            raise ValueError("copy colors violate selected profile/task palette")
        if exact and len({palette[k].lower() for k in used_colors}) != len(used_colors):
            raise ValueError("required distinct text colors cannot share one color value")
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG")
    payload = buf.getvalue()
    record = {"output": str(output), "size": [width, height], "sha256": hashlib.sha256(payload).hexdigest(),
              "brand_id": profile["id"], "profile_fingerprint": fingerprint, "copy_palette": palette,
              "logo": logo_record, "fonts": font_records,
              "text": drawn, "review_status": "pending", "layout_source": str(config_path),
              "note": "Deterministic rendering evidence only; visual inspection and project confirmation still required."}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as f:
        f.write(payload)
    with report_path.open("x", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compose(args.layout.resolve()), ensure_ascii=False, indent=2))
    except Exception as exc:
        parser.exit(1, f"Composition failed: {exc}\n")
