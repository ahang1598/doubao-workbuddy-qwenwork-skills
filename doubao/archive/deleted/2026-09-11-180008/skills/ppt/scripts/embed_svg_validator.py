#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
"""Validate self-contained SVG content embedded in Slides XML."""

from __future__ import annotations

import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any


SVG_NS = "{http://www.w3.org/2000/svg}"
EMBED_SVG_CAPABILITIES: dict[str, Any] = {
    "allowed_elements": [
        "svg",
        "defs",
        "g",
        "path",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "use",
        "linearGradient",
        "radialGradient",
        "stop",
        "clipPath",
        "mask",
        "filter",
        "feGaussianBlur",
        "feColorMatrix",
        "feOffset",
        "feMerge",
        "feMergeNode",
        "animate",
        "animateTransform",
        "animateMotion",
        "mpath",
    ],
    "visual_review_elements": [
        "filter",
        "mask",
        "clipPath",
        "feGaussianBlur",
        "feColorMatrix",
        "feOffset",
        "feMerge",
        "feMergeNode",
        "animate",
        "animateTransform",
        "animateMotion",
    ],
    "forbidden_elements": [
        "script",
        "style",
        "foreignObject",
        "iframe",
        "object",
        "image",
    ],
    "forbidden_attributes": ["style", "class"],
    "reference_attributes": ["href", "xlink:href"],
    "allowed_reference_prefixes": ["#"],
    "required_svg_attributes": ["xmlns", "viewBox"],
    "animation": {
        "allowed_elements": ["animate", "animateTransform", "animateMotion"],
        "duration_pattern": r"^(?:\d+(?:\.\d+)?|\.\d+)s$",
        "begin_pattern": r"^(?:\d+(?:\.\d+)?|\.\d+)s$",
        "repeat_count": "indefinite",
    },
}


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def xml_namespace(tag: str) -> str | None:
    return tag.split("}", 1)[0] + "}" if tag.startswith("{") else None


def load_embed_svg_capabilities() -> dict[str, Any]:
    return EMBED_SVG_CAPABILITIES


def validate_embedded_svgs(
    slide_root: ET.Element,
) -> list[dict[str, Any]]:
    capabilities = load_embed_svg_capabilities()
    allowed_elements = set(capabilities["allowed_elements"])
    review_elements = set(capabilities["visual_review_elements"])
    forbidden_elements = set(capabilities["forbidden_elements"])
    forbidden_attributes = set(capabilities["forbidden_attributes"])
    reference_attributes = set(capabilities["reference_attributes"])
    allowed_reference_prefixes = tuple(capabilities["allowed_reference_prefixes"])
    required_svg_attributes = set(capabilities["required_svg_attributes"])
    animation = capabilities.get("animation", {})
    animation_elements = set(animation.get("allowed_elements", [])) - {"mpath"}
    duration_pattern = re.compile(animation.get("duration_pattern", r"^$"))
    begin_pattern = re.compile(animation.get("begin_pattern", r"^$"))
    issues: list[dict[str, Any]] = []

    def append_issue(
        level: str,
        code: str,
        path: str,
        message: str,
        hint: str,
        *,
        embed_id: str,
        tag: str | None = None,
        attr: str | None = None,
        actual: Any = None,
    ) -> None:
        issue: dict[str, Any] = {
            "level": level,
            "code": code,
            "path": path,
            "message": message,
            "hint": hint,
            "elements": [embed_id],
        }
        if tag is not None:
            issue["tag"] = tag
        if attr is not None:
            issue["attr"] = attr
        if actual is not None:
            issue["actual"] = actual
        issues.append(issue)

    slide_namespace = xml_namespace(slide_root.tag)
    embeds = [
        element
        for element in slide_root.iter()
        if xml_local_name(element.tag) == "embed"
        and xml_namespace(element.tag) == slide_namespace
    ]
    for embed_index, embed in enumerate(embeds, start=1):
        embed_id = embed.attrib.get("id") or f"embed-{embed_index}"
        embed_path = f"slide/data/embed[{embed_index}]"
        children = list(embed)
        if len(children) != 1 or xml_namespace(children[0].tag) != SVG_NS or xml_local_name(children[0].tag) != "svg":
            append_issue(
                "error",
                "embed_svg_invalid_root",
                embed_path,
                f"embed {embed_id} must contain exactly one SVG namespace <svg> root",
                'Put one <svg xmlns="http://www.w3.org/2000/svg" viewBox="..."> child inside <embed>.',
                embed_id=embed_id,
                tag="embed",
            )
            continue

        svg_root = children[0]
        svg_path = f"{embed_path}/svg"
        missing_root_attrs = sorted(
            attr_name
            for attr_name in required_svg_attributes
            if attr_name not in svg_root.attrib
            and not (attr_name == "xmlns" and xml_namespace(svg_root.tag) == SVG_NS)
        )
        for attr_name in missing_root_attrs:
            append_issue(
                "error",
                "embed_svg_missing_required_attr",
                svg_path,
                f"embedded SVG {embed_id} is missing required attribute {attr_name!r}",
                f'Add {attr_name}="0 0 <width> <height>" to the SVG root.',
                embed_id=embed_id,
                tag="svg",
                attr=attr_name,
            )

        view_box = svg_root.attrib.get("viewBox")
        if view_box is not None:
            try:
                values = [float(value) for value in re.split(r"[\s,]+", view_box.strip()) if value]
                valid_view_box = (
                    len(values) == 4
                    and all(math.isfinite(value) for value in values)
                    and values[2] > 0
                    and values[3] > 0
                )
            except ValueError:
                valid_view_box = False
            if not valid_view_box:
                append_issue(
                    "error",
                    "embed_svg_invalid_viewbox",
                    svg_path,
                    f"embedded SVG {embed_id} has invalid viewBox {view_box!r}",
                    'Use four finite numbers with positive width and height, for example viewBox="0 0 440 280".',
                    embed_id=embed_id,
                    tag="svg",
                    attr="viewBox",
                    actual=view_box,
                )

        ids: set[str] = set()
        references: list[tuple[str, str, str]] = []
        used_review_elements: set[str] = set()
        svg_has_animation = any(
            xml_local_name(descendant.tag) in animation_elements for descendant in svg_root.iter()
        )
        for node in svg_root.iter():
            node_name = xml_local_name(node.tag)
            node_path = f"{svg_path}/{node_name}"
            if xml_namespace(node.tag) != SVG_NS:
                append_issue(
                    "error",
                    "embed_svg_invalid_namespace",
                    node_path,
                    f"embedded SVG element <{node_name}> is outside the SVG namespace",
                    'Keep every SVG descendant in xmlns="http://www.w3.org/2000/svg".',
                    embed_id=embed_id,
                    tag=node_name,
                )
                continue
            if node_name in forbidden_elements:
                append_issue(
                    "error",
                    "embed_svg_forbidden_element",
                    node_path,
                    f"embedded SVG uses forbidden element <{node_name}>",
                    "Use only the elements listed in EMBED_SVG_CAPABILITIES.",
                    embed_id=embed_id,
                    tag=node_name,
                )
            elif node_name not in allowed_elements:
                append_issue(
                    "error",
                    "embed_svg_unsupported_element",
                    node_path,
                    f"embedded SVG uses unsupported element <{node_name}>",
                    "Replace it with an allowed SVG primitive or extend the capability registry after online verification.",
                    embed_id=embed_id,
                    tag=node_name,
                )
            if node_name in review_elements:
                used_review_elements.add(node_name)

            if node_name == "filter" and svg_has_animation:
                region_attrs = ("x", "y", "width", "height")
                explicit_numeric_region = node.attrib.get("filterUnits") == "userSpaceOnUse"
                if explicit_numeric_region:
                    for region_attr in region_attrs:
                        raw_value = node.attrib.get(region_attr)
                        try:
                            numeric_value = float(raw_value) if raw_value is not None else math.nan
                        except ValueError:
                            numeric_value = math.nan
                        if not math.isfinite(numeric_value):
                            explicit_numeric_region = False
                            break
                if not explicit_numeric_region:
                    append_issue(
                        "error",
                        "embed_svg_unbounded_filter_region",
                        node_path,
                        f"animated embedded SVG {embed_id} uses a filter without a fixed user-space region",
                        'Set filterUnits="userSpaceOnUse" and numeric x, y, width, height values large enough for the full effect.',
                        embed_id=embed_id,
                        tag=node_name,
                    )

            if (
                node.attrib.get("filter")
                and node.attrib.get("clip-path")
                and any(xml_local_name(descendant.tag) in animation_elements for descendant in node.iter())
            ):
                append_issue(
                    "error",
                    "embed_svg_filter_clip_animation_conflict",
                    node_path,
                    f"embedded SVG {embed_id} combines filter, clip-path, and animation in one render subtree",
                    "Split static glow, body, and animated sheen into separate layers; keep filters off the clipped animated element.",
                    embed_id=embed_id,
                    tag=node_name,
                )

            node_id = node.attrib.get("id")
            if node_id:
                if node_id in ids:
                    append_issue(
                        "error",
                        "embed_svg_duplicate_id",
                        node_path,
                        f"embedded SVG {embed_id} contains duplicate id {node_id!r}",
                        "Give every SVG id a unique value inside the embed.",
                        embed_id=embed_id,
                        tag=node_name,
                        attr="id",
                        actual=node_id,
                    )
                ids.add(node_id)

            for raw_attr_name, value in node.attrib.items():
                attr_name = xml_local_name(raw_attr_name)
                if attr_name in forbidden_attributes or attr_name.lower().startswith("on"):
                    append_issue(
                        "error",
                        "embed_svg_forbidden_attribute",
                        node_path,
                        f"embedded SVG uses forbidden attribute {attr_name!r} on <{node_name}>",
                        "Use presentation attributes and SMIL allowlisted elements; do not use CSS or event handlers.",
                        embed_id=embed_id,
                        tag=node_name,
                        attr=attr_name,
                    )
                if attr_name in reference_attributes and value:
                    if value.startswith(allowed_reference_prefixes):
                        references.append((node_path, attr_name, value[1:]))
                    else:
                        append_issue(
                            "error",
                            "embed_svg_external_reference",
                            node_path,
                            f"embedded SVG reference {attr_name}={value!r} is not self-contained",
                            'Use only local fragment references such as href="#path-id".',
                            embed_id=embed_id,
                            tag=node_name,
                            attr=attr_name,
                            actual=value,
                        )
                for url_value in re.findall(r"url\(([^)]+)\)", value):
                    normalized = url_value.strip().strip("'\"")
                    if normalized.startswith("#"):
                        references.append((node_path, attr_name, normalized[1:]))
                    else:
                        append_issue(
                            "error",
                            "embed_svg_external_reference",
                            node_path,
                            f"embedded SVG url() reference {normalized!r} is not self-contained",
                            "Use only url(#local-id) references.",
                            embed_id=embed_id,
                            tag=node_name,
                            attr=attr_name,
                            actual=normalized,
                        )

            if node_name in animation_elements:
                duration = node.attrib.get("dur", "")
                begin = node.attrib.get("begin", "0s")
                repeat_count = node.attrib.get("repeatCount")
                if not duration_pattern.fullmatch(duration):
                    append_issue(
                        "error",
                        "embed_svg_invalid_animation",
                        node_path,
                        f"<{node_name}> requires a numeric seconds duration, got {duration!r}",
                        'Use dur like "2.8s".',
                        embed_id=embed_id,
                        tag=node_name,
                        attr="dur",
                        actual=duration,
                    )
                if not begin_pattern.fullmatch(begin):
                    append_issue(
                        "error",
                        "embed_svg_invalid_animation",
                        node_path,
                        f"<{node_name}> uses unsupported begin value {begin!r}",
                        'Use a numeric offset such as begin="0s" or begin=".4s"; event triggers are forbidden.',
                        embed_id=embed_id,
                        tag=node_name,
                        attr="begin",
                        actual=begin,
                    )
                if repeat_count != animation.get("repeat_count"):
                    append_issue(
                        "error",
                        "embed_svg_invalid_animation",
                        node_path,
                        f"<{node_name}> must use repeatCount={animation.get('repeat_count')!r}",
                        f'Use repeatCount="{animation.get("repeat_count")}".',
                        embed_id=embed_id,
                        tag=node_name,
                        attr="repeatCount",
                        actual=repeat_count,
                    )

        for reference_path, attr_name, target_id in references:
            if target_id and target_id not in ids:
                append_issue(
                    "error",
                    "embed_svg_missing_reference",
                    reference_path,
                    f"embedded SVG reference #{target_id} does not resolve inside {embed_id}",
                    "Add the referenced id inside the same SVG or remove the reference.",
                    embed_id=embed_id,
                    attr=attr_name,
                    actual=target_id,
                )

        if used_review_elements:
            append_issue(
                "warning",
                "embed_svg_visual_review_required",
                svg_path,
                f"embedded SVG {embed_id} uses renderer-sensitive elements: {', '.join(sorted(used_review_elements))}",
                "After writing the slide, verify the real Slides screenshot; readback alone does not prove filter or mask rendering.",
                embed_id=embed_id,
                tag="svg",
            )

    return issues


def _svg_number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


# Text width is estimated with a per-glyph advance model ported from xml_lint's
# estimate_text_width so SVG label geometry matches the layout linter's measurements.
# The coefficients below are advance ratios (em fractions) tuned against real Slides
# renders; every override may only raise an estimate, never lower it, so a slightly high
# advance is a benign false positive while a low one risks a missed collision/overflow.
#
# "%" is Unicode half-width (Na) but advances ~0.85em in common UI fonts; measuring it at
# the generic punct coefficient under-reports every percentage metric.
_SVG_PERCENT_SIGN_WIDTH_RATIO = 0.85
# Common marks that fall through to the punct branch yet render much wider than 0.50em.
_SVG_WIDE_SYMBOL_WIDTH_RATIOS: dict[str, float] = {
    "@": 1.0,
    "&": 0.67,
    "$": 0.56,
    "¥": 0.56,
    "£": 0.56,
    "¢": 0.56,
    "#": 0.56,
    "~": 0.58,
    "+": 0.58,
    "=": 0.58,
    "<": 0.58,
    ">": 0.58,
}
# The widest Latin letters advance far beyond the per-category average (lowercase "m"
# ~0.87em, "W" ~0.95em), so they carry a per-glyph advance applied before the category branch.
_SVG_WIDE_LETTER_WIDTH_RATIOS: dict[str, float] = {
    "m": 0.90,
    "w": 0.78,
    "M": 0.90,
    "W": 0.98,
    "G": 0.78,
    "O": 0.78,
    "Q": 0.78,
    "A": 0.72,
    "B": 0.66,
    "C": 0.72,
    "D": 0.72,
    "H": 0.72,
    "K": 0.66,
    "N": 0.72,
    "P": 0.66,
    "R": 0.72,
    "U": 0.72,
    "X": 0.66,
    "Z": 0.62,
}
_SVG_SERIF_FONT_PATTERNS = {
    "song", "songti", "simsun", "ming", "mincho",
    "georgia", "times", "caslon", "garamond", "sourcehan-serif",
    "source han serif", "思源宋体", "宋体", "明体",
}
_SVG_SANS_EXPLICIT_MARKERS = {
    "sans", "sans-serif", "sans serif", "sourcehan-sans", "source han sans", "思源黑体", "黑体",
    "helvetica", "arial", "inter", "roboto", "verdana", "tahoma", "calibri", "open sans",
}
# Geometric/wide sans families (Montserrat/Poppins/Futura) advance ~0.62-0.66em per glyph,
# noticeably wider than the humanist sans baseline; they get their own tier.
_SVG_WIDE_SANS_FONT_MARKERS = {
    "montserrat", "poppins", "futura", "century gothic", "gotham", "raleway",
    "nunito", "quicksand", "josefin", "comfortaa",
}
_SVG_FONT_CATEGORY_MULTIPLIERS: dict[str, dict[str, float]] = {
    "sans": {"upper": 0.57, "lower": 0.51, "digit": 0.58, "punct": 0.50},
    "serif": {"upper": 0.57, "lower": 0.53, "digit": 0.58, "punct": 0.50},
    "wide-sans": {"upper": 0.62, "lower": 0.58, "digit": 0.63, "punct": 0.53},
}


def _svg_is_cjk_char(character: str) -> bool:
    """CJK-like characters may wrap between any two adjacent glyphs."""
    code = ord(character)
    return (
        0x2E80 <= code <= 0x9FFF
        or 0x3000 <= code <= 0xD7AF
        or 0xF900 <= code <= 0xFAFF
        or 0xFE30 <= code <= 0xFE4F
        or 0xFF01 <= code <= 0xFF60
        or 0xFFE0 <= code <= 0xFFE6
    )


def _svg_classify_font_family(font_family: str | None) -> str:
    if not font_family:
        return "sans"
    family_lower = font_family.lower()
    for marker in _SVG_WIDE_SANS_FONT_MARKERS:
        if marker in family_lower:
            return "wide-sans"
    for marker in _SVG_SANS_EXPLICIT_MARKERS:
        if marker in family_lower:
            return "sans"
    for pattern in _SVG_SERIF_FONT_PATTERNS | {"serif"}:
        if pattern in family_lower:
            return "serif"
    return "sans"


def _svg_estimate_character_width(
    character: str,
    font_size: float,
    bold: bool = False,
    font_family: str | None = None,
    east_asian_context: bool = False,
) -> float:
    bold_multiplier = 1.05 if bold else 1.0
    if character.isspace():
        return font_size * 0.33 * bold_multiplier
    ea_width = unicodedata.east_asian_width(character)
    # Ambiguous-width glyphs (dashes, middle-dot, ellipsis) render full-width in a CJK run and
    # half-width in a Latin run (UAX #11); only promote them when the run has East Asian context.
    if ea_width in {"F", "W"} or (ea_width == "A" and east_asian_context):
        return font_size * bold_multiplier
    if character == "%":
        return font_size * _SVG_PERCENT_SIGN_WIDTH_RATIO * bold_multiplier
    wide_ratio = _SVG_WIDE_SYMBOL_WIDTH_RATIOS.get(character)
    if wide_ratio is not None:
        return font_size * wide_ratio * bold_multiplier
    coeffs = _SVG_FONT_CATEGORY_MULTIPLIERS[_svg_classify_font_family(font_family)]
    wide_letter_ratio = _SVG_WIDE_LETTER_WIDTH_RATIOS.get(character)
    if wide_letter_ratio is not None:
        category_ratio = coeffs["upper"] if character.isupper() else coeffs["lower"]
        return font_size * max(wide_letter_ratio, category_ratio) * bold_multiplier
    if character.isupper():
        return font_size * coeffs["upper"] * bold_multiplier
    if character.islower():
        return font_size * coeffs["lower"] * bold_multiplier
    if character.isdigit():
        return font_size * coeffs["digit"] * bold_multiplier
    return font_size * coeffs["punct"] * bold_multiplier


# Baseline-relative text box: ascent reaches the cap/ascender top, descent covers glyphs that
# hang below the baseline. Text without any descender glyph leaves the descent band empty, so we
# drop it to avoid a phantom band that inflates the vertical bbox (e.g. a large "8.8%" grazing a
# small axis label beneath it).
_SVG_TEXT_ASCENT_RATIO = 0.8
_SVG_TEXT_DESCENT_RATIO = 0.2
# Latin lowercase glyphs and punctuation that render below the baseline; any CJK glyph also fills
# the descent band, so those are detected separately via _svg_is_cjk_char.
_SVG_DESCENDER_CHARS = frozenset("gjpqy" + ",;()[]{}")


def _svg_text_has_descender(text: str) -> bool:
    return any(
        character in _SVG_DESCENDER_CHARS or _svg_is_cjk_char(character)
        for character in text
    )


def _svg_text_width(
    text: str,
    font_size: float,
    letter_spacing: float,
    bold: bool = False,
    font_family: str | None = None,
) -> float:
    east_asian_context = any(_svg_is_cjk_char(character) for character in text)
    width = sum(
        _svg_estimate_character_width(character, font_size, bold, font_family, east_asian_context)
        for character in text
    )
    if text:
        width += letter_spacing * max(len(text) - 1, 0)
    return max(width, 0.0)


def _svg_letter_spacing(value: str | None, font_size: float) -> float:
    """Resolve an SVG letter-spacing attribute to pixels, supporting em/px units."""
    if value is None:
        return 0.0
    text = value.strip().lower()
    if text.endswith("em"):
        return _svg_number(text[:-2]) * font_size
    if text.endswith("px"):
        return _svg_number(text[:-2])
    return _svg_number(text)


def _svg_is_bold(font_weight: str | None) -> bool:
    if font_weight is None:
        return False
    text = font_weight.strip().lower()
    if text in {"bold", "bolder"}:
        return True
    return _svg_number(text) >= 600


def _svg_visual_bbox(node: ET.Element, path: str) -> dict[str, Any] | None:
    node_name = xml_local_name(node.tag)
    if node.attrib.get("transform"):
        # A transformed primitive needs a renderer-grade transform matrix to produce a reliable
        # axis-aligned box. Leave it to screenshot review instead of inventing coordinates.
        return None

    if node_name == "text":
        text = "".join(node.itertext()).strip()
        if not text:
            return None
        font_size = _svg_number(node.attrib.get("font-size"), 16.0)
        letter_spacing = _svg_letter_spacing(node.attrib.get("letter-spacing"), font_size)
        bold = _svg_is_bold(node.attrib.get("font-weight"))
        font_family = node.attrib.get("font-family")
        width = _svg_text_width(text, font_size, letter_spacing, bold, font_family)
        x = _svg_number(node.attrib.get("x"))
        anchor = node.attrib.get("text-anchor", "start")
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        baseline_y = _svg_number(node.attrib.get("y"))
        descent = _SVG_TEXT_DESCENT_RATIO if _svg_text_has_descender(text) else 0.0
        return {
            "kind": "text",
            "path": path,
            "x": x,
            "y": baseline_y - font_size * _SVG_TEXT_ASCENT_RATIO,
            "width": width,
            "height": font_size * (_SVG_TEXT_ASCENT_RATIO + descent),
            "text": text,
        }

    if node_name == "rect":
        return {
            "kind": "rect",
            "path": path,
            "x": _svg_number(node.attrib.get("x")),
            "y": _svg_number(node.attrib.get("y")),
            "width": max(_svg_number(node.attrib.get("width")), 0.0),
            "height": max(_svg_number(node.attrib.get("height")), 0.0),
        }

    if node_name == "circle":
        radius = max(_svg_number(node.attrib.get("r")), 0.0)
        return {
            "kind": "circle",
            "path": path,
            "x": _svg_number(node.attrib.get("cx")) - radius,
            "y": _svg_number(node.attrib.get("cy")) - radius,
            "width": radius * 2,
            "height": radius * 2,
        }

    if node_name == "ellipse":
        radius_x = max(_svg_number(node.attrib.get("rx")), 0.0)
        radius_y = max(_svg_number(node.attrib.get("ry")), 0.0)
        return {
            "kind": "ellipse",
            "path": path,
            "x": _svg_number(node.attrib.get("cx")) - radius_x,
            "y": _svg_number(node.attrib.get("cy")) - radius_y,
            "width": radius_x * 2,
            "height": radius_y * 2,
        }

    return None


# A text or shape must leave the viewBox by more than this margin to count as out-of-canvas;
# it absorbs the small width error from estimating CJK glyph advance in _svg_text_width.
OUT_OF_BOUNDS_MARGIN_PX = 2.0
# A text may exceed its container path width by this much before it is treated as overflowing.
TEXT_CONTAINER_OVERFLOW_TOLERANCE_PX = 1.0


def _svg_viewbox(svg_root: ET.Element) -> tuple[float, float, float, float] | None:
    raw = svg_root.attrib.get("viewBox")
    if not raw:
        return None
    parts = re.findall(r"-?\d+(?:\.\d+)?", raw)
    if len(parts) != 4:
        return None
    vx, vy, vw, vh = (float(value) for value in parts)
    if vw <= 0 or vh <= 0:
        return None
    return vx, vy, vw, vh


def _svg_line_segment(node: ET.Element, path: str) -> dict[str, Any] | None:
    if xml_local_name(node.tag) != "line" or node.attrib.get("transform"):
        return None
    return {
        "kind": "line",
        "path": path,
        "x1": _svg_number(node.attrib.get("x1")),
        "y1": _svg_number(node.attrib.get("y1")),
        "x2": _svg_number(node.attrib.get("x2")),
        "y2": _svg_number(node.attrib.get("y2")),
    }


def _svg_polyline_container_bbox(node: ET.Element, path: str) -> dict[str, Any] | None:
    name = xml_local_name(node.tag)
    if node.attrib.get("transform"):
        return None
    xs: list[float] = []
    ys: list[float] = []
    if name == "path":
        d = node.attrib.get("d") or ""
        # Only straight, absolute outlines yield a tight box without a real renderer; bail on
        # curves (C/Q/A/S/T) and any relative command to avoid inventing a wrong container.
        if re.search(r"[CcQqAaSsTtmlhvz]", d):
            return None
        tokens = re.findall(r"[MLHVZ]|-?\d+(?:\.\d+)?", d)
        index = 0
        while index < len(tokens):
            command = tokens[index]
            if command in {"M", "L"} and index + 2 < len(tokens):
                xs.append(float(tokens[index + 1]))
                ys.append(float(tokens[index + 2]))
                index += 3
            elif command == "H" and index + 1 < len(tokens):
                xs.append(float(tokens[index + 1]))
                index += 2
            elif command == "V" and index + 1 < len(tokens):
                ys.append(float(tokens[index + 1]))
                index += 2
            else:
                index += 1
    elif name in {"polygon", "polyline"}:
        coords = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", node.attrib.get("points") or "")]
        xs = coords[0::2]
        ys = coords[1::2]
    else:
        return None
    if not xs or not ys:
        return None
    return {
        "kind": name,
        "path": path,
        "x": min(xs),
        "y": min(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


def _svg_segment_clip(
    segment: dict[str, Any], xmin: float, ymin: float, xmax: float, ymax: float
) -> tuple[float, float, float, float] | None:
    """Clip a line segment to a box (Liang-Barsky); return the clipped endpoints or None."""
    x0, y0 = segment["x1"], segment["y1"]
    dx, dy = segment["x2"] - x0, segment["y2"] - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - xmin, xmax - x0, y0 - ymin, ymax - y0)
    u1, u2 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
        else:
            t = qi / pi
            if pi < 0:
                u1 = max(u1, t)
            else:
                u2 = min(u2, t)
    if u1 > u2:
        return None
    return (x0 + u1 * dx, y0 + u1 * dy, x0 + u2 * dx, y0 + u2 * dy)


def _svg_bbox_overlap(left: dict[str, Any], right: dict[str, Any]) -> float:
    overlap_width = min(
        left["x"] + left["width"], right["x"] + right["width"]
    ) - max(left["x"], right["x"])
    overlap_height = min(
        left["y"] + left["height"], right["y"] + right["height"]
    ) - max(left["y"], right["y"])
    if overlap_width <= 0 or overlap_height <= 0:
        return 0.0
    return overlap_width * overlap_height


def detect_embedded_svg_overlaps(slide_root: ET.Element) -> list[dict[str, Any]]:
    """Report visible text collisions and duplicate SVG primitives inside each embed.

    The Slides layout linter sees an embed as one outer rectangle and cannot inspect its SVG
    children. This intentionally conservative check catches the common failure mode where several
    generated labels are written to the same coordinate, while avoiding connector lines crossing
    nodes and nested shapes that are often deliberate.
    """

    issues: list[dict[str, Any]] = []
    slide_namespace = xml_namespace(slide_root.tag)
    embeds = [
        element
        for element in slide_root.iter()
        if xml_local_name(element.tag) == "embed"
        and xml_namespace(element.tag) == slide_namespace
    ]
    for embed_index, embed in enumerate(embeds, start=1):
        embed_id = embed.attrib.get("id") or f"embed-{embed_index}"
        children = list(embed)
        if len(children) != 1 or xml_namespace(children[0].tag) != SVG_NS:
            continue
        svg_root = children[0]
        svg_path = f"slide/data/embed[{embed_index}]/svg"
        primitives: list[dict[str, Any]] = []
        lines: list[dict[str, Any]] = []
        containers: list[dict[str, Any]] = []
        tag_counts: dict[str, int] = {}

        def visit(node: ET.Element, parent_hidden: bool = False, parent_animated: bool = False) -> None:
            node_name = xml_local_name(node.tag)
            tag_counts[node_name] = tag_counts.get(node_name, 0) + 1
            node_path = (
                svg_path
                if node is svg_root
                else f"{svg_path}/{node_name}[{tag_counts[node_name]}]"
            )
            hidden = parent_hidden or node_name in {"defs", "clipPath", "mask", "filter"}
            # Animated elements move at render time, so their static coordinates cannot prove a
            # geometric defect; the new layout checks below skip them.
            animated = parent_animated or any(
                xml_local_name(child.tag) in {"animate", "animateMotion", "animateTransform", "set"}
                for child in node
            )
            if not hidden:
                primitive = _svg_visual_bbox(node, node_path)
                if primitive is not None and primitive["width"] > 0 and primitive["height"] > 0:
                    primitive["animated"] = animated
                    primitives.append(primitive)
                if node_name == "line":
                    segment = _svg_line_segment(node, node_path)
                    if segment is not None:
                        segment["animated"] = animated
                        lines.append(segment)
                elif node_name in {"path", "polygon", "polyline"}:
                    container = _svg_polyline_container_bbox(node, node_path)
                    if container is not None and container["width"] > 0 and container["height"] > 0:
                        containers.append(container)
                elif node_name in {"circle", "ellipse"} and primitive is not None:
                    # A circle/ellipse holding a centered label is a text container too: at the
                    # vertical center the available horizontal chord is the full bbox width (the
                    # diameter / 2*rx), so its bbox is the usable inner width for a label sitting
                    # on the center line (slides p12: "WorkBuddy" truncated inside an r=24 circle).
                    containers.append(
                        {
                            "kind": node_name,
                            "path": node_path,
                            "x": primitive["x"],
                            "y": primitive["y"],
                            "width": primitive["width"],
                            "height": primitive["height"],
                        }
                    )
            for child in node:
                visit(child, hidden, animated)

        visit(svg_root)
        texts = [
            primitive
            for primitive in primitives
            if primitive["kind"] == "text" and not primitive.get("animated")
        ]
        shapes = [
            primitive
            for primitive in primitives
            if primitive["kind"] in {"rect", "circle", "ellipse"} and not primitive.get("animated")
        ]
        static_lines = [line for line in lines if not line.get("animated")]

        # Text collisions are geometric. For filled primitives only exact duplicate boxes are
        # considered defects, which avoids flagging intentional nested rings and backgrounds.
        parent = list(range(len(primitives)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left_index: int, right_index: int) -> None:
            left_root, right_root = find(left_index), find(right_index)
            if left_root != right_root:
                parent[right_root] = left_root

        for left_index, left in enumerate(primitives):
            for right_index in range(left_index + 1, len(primitives)):
                right = primitives[right_index]
                if left["kind"] == "text" and right["kind"] == "text":
                    if _svg_bbox_overlap(left, right) > 1.0:
                        union(left_index, right_index)
                elif (
                    left["kind"] == right["kind"]
                    and left["kind"] in {"rect", "circle", "ellipse"}
                    and all(
                        abs(left[key] - right[key]) < 0.001
                        for key in ("x", "y", "width", "height")
                    )
                ):
                    union(left_index, right_index)

        components: dict[int, list[dict[str, Any]]] = {}
        for index, primitive in enumerate(primitives):
            components.setdefault(find(index), []).append(primitive)
        for component in components.values():
            if len(component) < 2:
                continue
            kind = component[0]["kind"]
            issues.append(
                {
                    "level": "error",
                    "code": "embed_svg_bbox_overlap",
                    "path": component[0]["path"],
                    "message": (
                        f"embedded SVG {embed_id} has {len(component)} overlapping "
                        f"{kind} elements"
                    ),
                    "hint": (
                        "Move the SVG elements to distinct coordinates, or remove duplicated "
                        "generated elements before writing the slide."
                    ),
                    "elements": [embed_id],
                    "overlaps": [
                        {
                            "path": primitive["path"],
                            "bbox": {
                                key: round(primitive[key], 3)
                                for key in ("x", "y", "width", "height")
                            },
                            **({"text": primitive["text"]} if "text" in primitive else {}),
                        }
                        for primitive in component
                    ],
                    "measurement": {
                        "overlap_element_count": len(component),
                        "primitive_kind": kind,
                    },
                }
            )

        def _text_bbox(primitive: dict[str, Any]) -> dict[str, float]:
            return {
                key: round(primitive[key], 3)
                for key in ("x", "y", "width", "height")
            }

        # Out-of-canvas: a text or shape whose box leaves the viewBox by more than the CJK
        # width-estimate margin is clipped by the embed frame and cannot be intentional.
        viewbox = _svg_viewbox(svg_root)
        if viewbox is not None:
            vx, vy, vw, vh = viewbox
            for primitive in texts + shapes:
                overflow_right = primitive["x"] + primitive["width"] - (vx + vw)
                overflow_bottom = primitive["y"] + primitive["height"] - (vy + vh)
                overflow_left = vx - primitive["x"]
                overflow_top = vy - primitive["y"]
                overflow = max(overflow_right, overflow_bottom, overflow_left, overflow_top)
                if overflow <= OUT_OF_BOUNDS_MARGIN_PX:
                    continue
                label = primitive.get("text", primitive["kind"])
                issues.append(
                    {
                        "level": "error",
                        "code": "embed_svg_out_of_bounds",
                        "path": primitive["path"],
                        "message": (
                            f"embedded SVG {embed_id} {primitive['kind']} '{label}' extends "
                            f"{round(overflow, 1)}px beyond the {round(vw)}x{round(vh)} viewBox"
                        ),
                        "hint": (
                            "Move the element inside the viewBox, shrink its font-size, or enlarge "
                            "the viewBox so the content is not clipped by the embed frame."
                        ),
                        "elements": [embed_id],
                        "overlaps": [
                            {
                                "path": primitive["path"],
                                "bbox": _text_bbox(primitive),
                                **({"text": primitive["text"]} if "text" in primitive else {}),
                            }
                        ],
                        "measurement": {
                            "overflow_px": round(overflow, 3),
                            "viewbox": {"width": vw, "height": vh},
                        },
                    }
                )

        # Cross-type collision: a text whose box overlaps a shape but whose center falls outside
        # that shape is grazing it, not labeling it. Labels centered inside a shape are skipped so
        # normal in-shape captions do not flag.
        for text in texts:
            center_x = text["x"] + text["width"] / 2
            center_y = text["y"] + text["height"] / 2
            for shape in shapes:
                if _svg_bbox_overlap(text, shape) <= 1.0:
                    continue
                inside = (
                    shape["x"] <= center_x <= shape["x"] + shape["width"]
                    and shape["y"] <= center_y <= shape["y"] + shape["height"]
                )
                if inside:
                    continue
                issues.append(
                    {
                        "level": "error",
                        "code": "embed_svg_text_shape_overlap",
                        "path": text["path"],
                        "message": (
                            f"embedded SVG {embed_id} text '{text['text']}' overlaps a "
                            f"{shape['kind']} it does not label"
                        ),
                        "hint": (
                            "Reposition the text clear of the shape, or move the shape, so the "
                            "label does not collide with unrelated geometry."
                        ),
                        "elements": [embed_id],
                        "overlaps": [
                            {"path": text["path"], "bbox": _text_bbox(text), "text": text["text"]},
                            {"path": shape["path"], "bbox": _text_bbox(shape)},
                        ],
                        "measurement": {"primitive_kind": shape["kind"]},
                    }
                )

        # Line through text: a line that crosses the glyph band of a text box horizontally strikes
        # through the glyphs. The band spans 15%-70% of the box height: the raised top edge catches a
        # line pressed against the cap, while stopping short of the baseline (~80%) so labels sitting
        # on an axis are not flagged. Requiring a horizontal-dominant span of at least half the text
        # width skips vertical dividers and axis ticks that merely touch a label edge.
        for text in texts:
            band_top = text["y"] + text["height"] * 0.15
            band_bottom = text["y"] + text["height"] * 0.7
            for line in static_lines:
                clipped = _svg_segment_clip(
                    line, text["x"], band_top, text["x"] + text["width"], band_bottom
                )
                if clipped is None:
                    continue
                horizontal_span = abs(clipped[2] - clipped[0])
                vertical_span = abs(clipped[3] - clipped[1])
                if horizontal_span < 0.5 * text["width"] or horizontal_span < vertical_span:
                    continue
                issues.append(
                    {
                        "level": "error",
                        "code": "embed_svg_line_through_text",
                        "path": text["path"],
                        "message": (
                            f"embedded SVG {embed_id} line strikes through text '{text['text']}'"
                        ),
                        "hint": (
                            "Move the line or the text apart so the connector or axis does not "
                            "cross the label."
                        ),
                        "elements": [embed_id],
                        "overlaps": [
                            {"path": text["path"], "bbox": _text_bbox(text), "text": text["text"]},
                            {
                                "path": line["path"],
                                "bbox": {
                                    "x": round(min(line["x1"], line["x2"]), 3),
                                    "y": round(min(line["y1"], line["y2"]), 3),
                                    "width": round(abs(line["x2"] - line["x1"]), 3),
                                    "height": round(abs(line["y2"] - line["y1"]), 3),
                                },
                            },
                        ],
                        "measurement": {"horizontal_span_px": round(horizontal_span, 3)},
                    }
                )
                break

        # Text overflowing its container: a label centered inside a straight-edged path/polygon but
        # wider than that container is truncated or spills past the shape it belongs to.
        for text in texts:
            center_x = text["x"] + text["width"] / 2
            center_y = text["y"] + text["height"] / 2
            enclosing = None
            for container in containers:
                if (
                    container["x"] <= center_x <= container["x"] + container["width"]
                    and container["y"] <= center_y <= container["y"] + container["height"]
                ):
                    if enclosing is None or (
                        container["width"] * container["height"]
                        < enclosing["width"] * enclosing["height"]
                    ):
                        enclosing = container
            if enclosing is None:
                continue
            if text["width"] <= enclosing["width"] + TEXT_CONTAINER_OVERFLOW_TOLERANCE_PX:
                continue
            issues.append(
                {
                    "level": "error",
                    "code": "embed_svg_text_container_overflow",
                    "path": text["path"],
                    "message": (
                        f"embedded SVG {embed_id} text '{text['text']}' is "
                        f"{round(text['width'] - enclosing['width'], 1)}px wider than its "
                        f"{enclosing['kind']} container and is truncated"
                    ),
                    "hint": (
                        "Shorten the text, reduce its font-size, or widen the container so the "
                        "label fits inside the shape."
                    ),
                    "elements": [embed_id],
                    "overlaps": [
                        {"path": text["path"], "bbox": _text_bbox(text), "text": text["text"]},
                        {"path": enclosing["path"], "bbox": _text_bbox(enclosing)},
                    ],
                    "measurement": {
                        "text_width_px": round(text["width"], 3),
                        "container_width_px": round(enclosing["width"], 3),
                    },
                }
            )

    return issues
