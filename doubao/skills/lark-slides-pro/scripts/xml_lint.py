#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
"""Validate Slides XML structure and page layout through one release gate."""

from __future__ import annotations

import copy
import json
import math
import re
import sys
import unicodedata
import xml.parsers.expat as expat
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
from typing import Any

import sxsd_validator


XS_NS = "{http://www.w3.org/2001/XMLSchema}"
XML_NS = "{http://www.w3.org/XML/1998/namespace}"
SVG_NS = "{http://www.w3.org/2000/svg}"
SML_NAMESPACE = "https://www.larkoffice.com/sml/2.0"
SXSD_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "references" / "xml" / "slides_xml_schema_definition.xml"
ICONPARK_INDEX_PATH = Path(__file__).resolve().parents[1] / "references" / "xml" / "iconpark-index.json"
SXSD_TAG_ALIASES = {
    "textbox": "<shape type=\"text\">",
    "textBox": "<shape type=\"text\">",
    "image": "<img>",
    "picture": "<img>",
}
SXSD_ATTR_ALIASES = {
    "x": "topLeftX",
    "left": "topLeftX",
    "y": "topLeftY",
    "top": "topLeftY",
    "w": "width",
    "h": "height",
    "fontColor": "color",
}
SERVER_FILLED_SXSD_ATTRS = {"id"}
ROUNDTRIP_SXSD_ATTRS = {
    ("chart", "updated"),
    ("chartData", "isStaticData"),
}
# Slides readback echoes each chartField's CSV text as per-value <chartParsedValues> children;
# it is server-emitted and absent from the write schema, so it must not block page linting.
ROUNDTRIP_SXSD_TAGS = {("chartField", "chartParsedValues")}
DEFAULT_TABLE_COLUMN_WIDTH = 110
DEFAULT_TABLE_ROW_HEIGHT = 37
DEFAULT_TEXT_LINE_SPACING_MULTIPLE = 1.5
TEXT_WRAP_WIDTH_TOLERANCE_PX = 1.0
TEXT_HEIGHT_OVERFLOW_TOLERANCE_PX = 0.5
CENTERED_SHORT_LABEL_WIDTH_RATIO = 1.12
HEADLINE_NEAR_FIT_WIDTH_RATIO = 1.04
# A single-hard-line text run whose estimated visual width reaches this fraction of its content box
# is at risk of wrapping on the real (Skia) renderer. The width estimator can under-report by ~10%
# for short bold/latin runs, so we flag well below 100% to guarantee no real wrap escapes -- the
# team's release gate for these decks prefers false positives over any missed wrap.
TEXT_WIDTH_WRAP_RISK_RATIO = 0.85
# Only short single-line labels/metrics are candidates for the width-wrap rule; longer runs are
# prose meant to wrap.
SHORT_LABEL_WRAP_MAX_CHARS = 16
# "%" is classified half-width by Unicode (Na) but its glyph advance is close to an em in common UI
# fonts (Arial 0.889, PingFang ~0.85). Measuring it at the generic punct coefficient under-reports
# every percentage metric and hides real wraps/overflows (slides p3: bhU).
PERCENT_SIGN_WIDTH_RATIO = 0.85
# The generic punct coefficient (0.50em) fits narrow marks (. , : ; ! etc.) but a handful of common
# symbols render much wider, so measuring them at 0.50 under-reports the line and hides real wraps --
# the same defect "%" had before its own coefficient. These are all Unicode Na/ambiguous marks that
# fall through to the punct branch, so a per-glyph advance table (nearest common sans/PingFang values)
# is the physically correct fix, rather than teaching a shape classifier one more layout. We only
# raise coefficients here, never lower them (e.g. "*" "/" render narrower than 0.50): a slightly high
# estimate at worst yields a benign false positive, while lowering one risks a missed wrap, and this
# gate prefers false positives over any missed overflow.
WIDE_SYMBOL_WIDTH_RATIOS: dict[str, float] = {
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
# The category coefficients below are a per-category average, so the widest Latin letters (m w M W)
# get measured far too narrow: a lowercase "m" advances ~0.87em and "W" ~0.95em in common fonts, not
# the 0.51-0.62em the lower/upper averages assume. Averaging them in under-reports any run built from
# these glyphs, so a big-type run like "70mm" fits the estimate yet wraps on the real renderer (slides
# I9dd p27: bLN "70mm" in a 200px box). Same fix and same guardrails as WIDE_SYMBOL_WIDTH_RATIOS: a
# per-glyph advance (wide end of common sans/serif metrics) applied before the category branch, only
# ever raising the estimate -- a slightly high advance is a benign false positive, while the category
# average risks a missed wrap, and this gate prefers false positives over any missed overflow.
WIDE_LETTER_WIDTH_RATIOS: dict[str, float] = {
    "m": 0.90,
    "w": 0.78,
    "M": 0.90,
    "W": 0.98,
    "G": 0.78,
    "O": 0.78,
    "Q": 0.78,
    "C": 0.72,
    "D": 0.72,
    "H": 0.72,
    "N": 0.72,
    "R": 0.72,
    "U": 0.72,
}
# A repeated-text pair is only treated as an intentional shadow/duplicate overlay (and suppressed)
# when their glyph boxes are at least this coincident. Below it, two separately-placed labels that
# merely share the same text are a genuine collision and must still be reported.
SIMILAR_OVERLAY_COINCIDENCE_RATIO = 0.85
# A text glyph box that pokes past its background container by more than this many pixels has
# outgrown the box the author sized for it. A few pixels of slack absorbs glyph-width estimation
# jitter so tightly-fitted text is not falsely reported.
CONTAINER_OVERFLOW_MIN_PX = 4.0
# Minimum overlapped glyph-box area for a text-text collision. Text visual boxes are eroded to the
# estimated ink extent, so any overlap above float jitter is a real collision. ~60px^2 is roughly one
# CJK glyph's footprint at body size, above estimation noise yet below a genuine crossing.
NON_PARALLEL_TEXT_OVERLAP_MIN_AREA = 60.0
# A shape whose shorter side is at most this many pixels is a rule/divider/hairline, not a box that
# can contain text (real cards/pills on these decks are >= 40px on their short side). Used to keep the
# container-overflow check from adopting a divider as a text's background (slides p9).
LINE_LIKE_SHAPE_MAX_THICKNESS_PX = 8.0
# An image covering at least this fraction of the canvas is a full-bleed backdrop. When it also sits
# behind the text in z-order it cannot occlude that text, so it is exempt from image_covers_text
# (slides p9: bBo fills 960x540 at the bottom of the stack). A partial-bleed photo stays in scope.
FULL_CANVAS_BACKGROUND_COVERAGE_RATIO = 0.95
# A partial-bleed image that sits behind a text run and encloses essentially all of that run's glyph
# box is a local background for it -- the glyphs paint on top of the image, so it cannot occlude them
# (slides LuwIs0LQXlmCm0d2XTHcHxeCnfd: the 852x380 backdrop tucks fully under each card's copy). We
# require near-total enclosure so an image that only clips part of a run (a genuine occlusion, glyphs
# spilling past the image edge) is still reported.
BACKGROUND_IMAGE_TEXT_ENCLOSURE_RATIO = 0.98
DENSE_BODY_LINE_SPACING_MAX_MULTIPLE = 1.6
# Renderers tighten dense multi-paragraph bodies below their authored line spacing, but only by a
# bounded fraction -- they do not collapse a 2x-spaced body to the 1.6x floor. Model the realised
# spacing as 90% of the authored multiple (never below the 1.6x floor) so a body authored at
# multiple:2 in a box that only fits ~1.6x is still flagged (slides p12: bqL's 10 lines at
# multiple:2 render past its 200px box), while genuinely slack bodies stay benign.
DENSE_BODY_LINE_SPACING_COMPRESSION = 0.9
GHOST_TEXT_MIN_FONT_SIZE = 96
GHOST_TEXT_MAX_ALPHA = 0.5
GHOST_TEXT_FAINT_MIN_FONT_SIZE = 36
GHOST_TEXT_FAINT_MAX_ALPHA = 0.35
# A caption laid flush against a container's border shares its edge (0px gap), so their boxes touch
# with exactly 0 intersection area and area-based ownership would orphan it. Treat a text box within
# this many pixels of a container edge as owned by it so a caption spilling just past the border is
# still checked for overflow (slides p12: the labels sit on bgq's bottom edge and hang below it).
CONTAINER_EDGE_ADJACENCY_TOLERANCE = 2.0
# A <line> crossing text glyphs is a legibility defect (see line_crosses_text_glyphs). We erode the
# glyph box by this margin before testing intersection so a line that only skims a glyph edge or the
# padding-only text frame -- but does not actually cut through the letterforms -- is not flagged.
LINE_TEXT_GRAZE_MIN_PX = 2.0
LINE_TEXT_GRAZE_FONT_RATIO = 0.12
# A line whose effective stroke alpha is below this is not visibly rendered, so it cannot occlude text.
LINE_MIN_VISIBLE_ALPHA = 0.08
# A filled shape below this effective fill alpha is not visibly occluding text.
SHAPE_FILL_MIN_VISIBLE_ALPHA = 0.08
# Ignore sub-pixel/edge noise when a filled shape barely touches a text glyph box.
SHAPE_TEXT_OCCLUSION_MIN_AREA = 4.0
# Ignore sub-pixel/edge noise when two card-like background shapes barely touch.
SHAPE_CONTAINER_OVERLAP_MIN_AREA = 4.0
# Sub-pixel canvas overflow is floating-point rounding noise (e.g. rotated-bbox math), not a
# visible defect; keep this well under 1px so real overflow is still always caught.
CANVAS_OVERFLOW_TOLERANCE = 0.5
XML_PATH_HINT_PREFIX = "Locate via related_objects[].xml_path."
_SXSD_TAG_ATTRIBUTES_CACHE: dict[str, set[str]] | None = None
_ICONPARK_ICON_TYPES_CACHE: set[str] | None = None


class XmlLayoutLintError(Exception):
    pass


def fail(message: str) -> None:
    raise XmlLayoutLintError(message)


def read_file(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def parse_args(argv: list[str]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if not token.startswith("--"):
            fail(f"unexpected argument: {token}, need --input")
        key = token[2:]
        next_token = argv[index + 1] if index + 1 < len(argv) else None
        if next_token is None or next_token.startswith("--"):
            options[key] = True
            index += 1
            continue
        options[key] = next_token
        index += 2
    return options


def extract_attribute(tag_source: str, name: str) -> str | None:
    match = re.search(
        fr"(?:^|\s){re.escape(name)}\s*=\s*(?:\"([^\"]+)\"|'([^']+)')", tag_source
    )
    if not match:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)


def extract_numeric_attribute(tag_source: str, name: str) -> int | float | None:
    raw = extract_attribute(tag_source, name)
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return int(value) if value.is_integer() else value


def extract_bool_attribute(tag_source: str, name: str) -> bool:
    value = extract_attribute(tag_source, name)
    return value in {"true", "1", "yes"}


def extract_color_alpha(color: str | None) -> int | float | None:
    if color is None:
        return None
    normalized = re.sub(r"\s+", "", color).lower()
    if normalized == "transparent":
        return 0
    rgba_match = re.fullmatch(
        r"rgba\([^,]+,[^,]+,[^,]+,([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\)",
        normalized,
    )
    if rgba_match is None:
        return None
    try:
        alpha = float(rgba_match.group(1))
    except ValueError:
        return None
    return int(alpha) if alpha.is_integer() else alpha


def effective_text_alpha(shape_alpha: int | float | None, text_color: str | None) -> int | float:
    base_alpha = shape_alpha if isinstance(shape_alpha, (int, float)) else 1
    color_alpha = extract_color_alpha(text_color)
    if not isinstance(color_alpha, (int, float)):
        return base_alpha
    return base_alpha * color_alpha


def has_tag(value: str, tag: str) -> bool:
    return re.search(fr"<{re.escape(tag)}\b", value) is not None


def extract_optional_alpha(attrs: str) -> int | float:
    alpha = extract_numeric_attribute(attrs, "alpha")
    return alpha if isinstance(alpha, (int, float)) else 1


def default_fill_alpha(shape_type: str | None) -> int:
    return 0 if shape_type == "text" else 1


def extract_fill_alpha(value: str, shape_type: str | None = None) -> int | float | None:
    if not has_tag(value, "fill"):
        return None
    fill_img_attrs = extract_tag_attributes(value, "fillImg")
    if has_tag(value, "fillImg"):
        return extract_optional_alpha(fill_img_attrs)
    fill_pattern_attrs = extract_tag_attributes(value, "fillPattern")
    if has_tag(value, "fillPattern"):
        return extract_optional_alpha(fill_pattern_attrs)
    fill_color_attrs = extract_tag_attributes(value, "fillColor")
    if not has_tag(value, "fillColor"):
        return default_fill_alpha(shape_type)
    color = extract_attribute(fill_color_attrs, "color")
    if color is None:
        return default_fill_alpha(shape_type)
    alpha = extract_color_alpha(color)
    if isinstance(alpha, (int, float)):
        return alpha
    gradient_alphas = [
        float(raw_alpha)
        for raw_alpha in re.findall(
            r"rgba\([^,]+,[^,]+,[^,]+,([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))\)",
            color,
            flags=re.IGNORECASE,
        )
    ]
    if gradient_alphas:
        return max(gradient_alphas)
    # rgb()/hex/named colors without an explicit alpha are opaque.
    return 1


def detect_inline_style_presence(content_xml: str, style_tags: set[str]) -> bool:
    for tag_name in style_tags:
        if re.search(fr"<{re.escape(tag_name)}\b[\s>]", content_xml) is not None:
            return True
    return False


def detect_any_span_bool_attribute(content_xml: str, attr_name: str) -> bool:
    for attrs in re.findall(r"<span\b([^>]*)>", content_xml):
        if extract_bool_attribute(attrs, attr_name):
            return True
    return False


def sum_sizes(sizes: list[int | float]) -> int | float:
    return sum(sizes)


def is_filled_size(size: int | float | None) -> bool:
    return isinstance(size, (int, float)) and math.isfinite(size) and size > 0


def fill_last_size_gap(sizes: list[int | float], target_size: int | float) -> list[int | float]:
    if not sizes:
        return sizes
    final_sizes = [
        size if index == len(sizes) - 1 else max(1, math.floor(size + 0.5))
        for index, size in enumerate(sizes)
    ]
    remaining_size = target_size - sum_sizes(final_sizes[:-1])
    if remaining_size >= 1:
        final_sizes[-1] = remaining_size
        return final_sizes

    size_to_redistribute = 1 - remaining_size
    for index in range(len(final_sizes) - 2, -1, -1):
        reduction = min(final_sizes[index] - 1, size_to_redistribute)
        final_sizes[index] -= reduction
        size_to_redistribute -= reduction
        if size_to_redistribute == 0:
            final_sizes[-1] = 1
            return final_sizes

    final_sizes[-1] = 1
    return final_sizes


def solve_weighted_min_layout(
    input_sizes: list[int | float | None], default_size: int | float, target_min_size: int | float | None
) -> dict[str, Any]:
    filled_indexes: list[int] = []
    empty_indexes: list[int] = []
    base_sizes: list[int | float] = []
    for index, size in enumerate(input_sizes):
        if is_filled_size(size):
            filled_indexes.append(index)
            base_sizes.append(size)
        else:
            empty_indexes.append(index)
            base_sizes.append(0)
    filled_sum = sum_sizes(base_sizes)

    if target_min_size is None:
        final_sizes = [default_size if index in empty_indexes else size for index, size in enumerate(base_sizes)]
        return {"final_sizes": final_sizes, "actual_size": sum_sizes(final_sizes), "ratio": 1}

    if not filled_indexes:
        average_size = target_min_size / len(input_sizes)
        final_sizes = fill_last_size_gap([average_size] * len(input_sizes), target_min_size)
        return {"final_sizes": final_sizes, "actual_size": sum_sizes(final_sizes), "ratio": 1}

    if empty_indexes:
        remaining_size = target_min_size - filled_sum
        final_sizes = [*base_sizes]
        if remaining_size > 0:
            average_size = remaining_size / len(empty_indexes)
            empty_sizes = fill_last_size_gap([average_size] * len(empty_indexes), remaining_size)
            for index, empty_size in zip(empty_indexes, empty_sizes):
                final_sizes[index] = empty_size
        else:
            for index in empty_indexes:
                final_sizes[index] = default_size
        return {"final_sizes": final_sizes, "actual_size": sum_sizes(final_sizes), "ratio": 1}

    ratio = max(1, target_min_size / filled_sum)
    actual_size = max(target_min_size, filled_sum)
    if ratio == 1:
        return {"final_sizes": [*base_sizes], "actual_size": actual_size, "ratio": ratio}
    final_sizes = fill_last_size_gap([size * ratio for size in base_sizes], actual_size)
    return {"final_sizes": final_sizes, "actual_size": sum_sizes(final_sizes), "ratio": ratio}


def strip_xml(value: str, preserve_line_breaks: bool = False) -> str:
    stripped = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", value)
    if preserve_line_breaks:
        stripped = re.sub(r"<br\b[^>]*>", "\n", stripped)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    stripped = stripped.replace("&nbsp;", " ")
    stripped = stripped.replace("&amp;", "&")
    stripped = stripped.replace("&lt;", "<")
    stripped = stripped.replace("&gt;", ">")
    stripped = stripped.replace("&quot;", '"')
    stripped = stripped.replace("&#39;", "'")
    if preserve_line_breaks:
        return "\n".join(re.sub(r"\s+", " ", line).strip() for line in stripped.split("\n"))
    return re.sub(r"\s+", " ", stripped).strip()


def strip_xml_paragraphs(value: str) -> str:
    paragraphs = re.findall(r"<p\b[^>]*>([\s\S]*?)</p\s*>", value)
    if paragraphs:
        return "\n".join(strip_xml(paragraph, preserve_line_breaks=True) for paragraph in paragraphs)
    return strip_xml(value, preserve_line_breaks=True)


def strip_xml_paragraphs_preserving_spaces(value: str) -> str:
    """Like strip_xml_paragraphs but keeps runs of internal spaces intact.

    Slides readback echoes multi-space runs verbatim (e.g. "autofix      87%") and Skia
    renders them at full width, but strip_xml collapses whitespace, hiding real wraps from
    width estimation. Used only by detect_text_may_wrap_shapes to avoid under-measuring.
    """
    def strip_line_tags(fragment: str) -> str:
        stripped = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", fragment)
        stripped = re.sub(r"<br\b[^>]*>", "\n", stripped)
        stripped = re.sub(r"<[^>]+>", "", stripped)
        stripped = stripped.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
        stripped = stripped.replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
        return stripped

    paragraphs = re.findall(r"<p\b[^>]*>([\s\S]*?)</p\s*>", value)
    fragments = paragraphs if paragraphs else [value]
    return "\n".join(strip_line_tags(fragment) for fragment in fragments)


def extract_text_paragraphs(value: str, default_font_size: int | float) -> list[dict[str, Any]]:
    paragraphs = []
    for attrs, body in re.findall(r"<p\b([^>]*)>([\s\S]*?)</p\s*>", value):
        paragraphs.append(
            {
                "text": strip_xml(body, preserve_line_breaks=True),
                "fontSize": extract_max_span_font_size(body, default_font_size),
                "textAlign": extract_attribute(attrs, "textAlign"),
                "lineSpacing": extract_attribute(attrs, "lineSpacing"),
                "beforeLineSpacing": extract_attribute(attrs, "beforeLineSpacing"),
                "afterLineSpacing": extract_attribute(attrs, "afterLineSpacing"),
                "letterSpacing": extract_numeric_attribute(attrs, "letterSpacing"),
            }
        )
    return paragraphs


def extract_max_span_font_size(value: str, default_font_size: int | float) -> int | float:
    font_sizes = [
        font_size
        for attrs in re.findall(r"<span\b([^>]*)>", value)
        if (font_size := extract_numeric_attribute(attrs, "fontSize")) is not None
    ]
    return max([default_font_size, *font_sizes])


def extract_tag_attributes(value: str, tag: str) -> str:
    match = re.search(fr"<{re.escape(tag)}\b([^>]*)>", value)
    return match.group(1) if match else ""


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def xml_namespace(tag: str) -> str | None:
    return tag.split("}", 1)[0] + "}" if tag.startswith("{") else None


def load_sxsd_tag_attributes() -> dict[str, set[str]]:
    global _SXSD_TAG_ATTRIBUTES_CACHE
    if _SXSD_TAG_ATTRIBUTES_CACHE is not None:
        return _SXSD_TAG_ATTRIBUTES_CACHE

    _SXSD_TAG_ATTRIBUTES_CACHE = sxsd_validator.load_tag_attributes(SXSD_SCHEMA_PATH)
    return _SXSD_TAG_ATTRIBUTES_CACHE


def load_iconpark_icon_types() -> set[str]:
    global _ICONPARK_ICON_TYPES_CACHE
    if _ICONPARK_ICON_TYPES_CACHE is not None:
        return _ICONPARK_ICON_TYPES_CACHE

    try:
        index_data = json.loads(ICONPARK_INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"invalid iconpark index JSON: {error}")
    icons = index_data.get("icons")
    if not isinstance(icons, list):
        fail("iconpark index must contain an icons array")

    icon_types = {
        icon["iconType"]
        for icon in icons
        if isinstance(icon, dict) and isinstance(icon.get("iconType"), str) and icon["iconType"]
    }
    _ICONPARK_ICON_TYPES_CACHE = icon_types
    return icon_types


def build_sxsd_tag_hint(tag_name: str, supported_tags: set[str]) -> str:
    alias = SXSD_TAG_ALIASES.get(tag_name)
    if alias:
        return f"Use {alias} instead of <{tag_name}>."
    if tag_name == "svg":
        return 'Inside <embed> or <whiteboard>, write SVG as <svg xmlns="http://www.w3.org/2000/svg">...</svg>.'
    close_matches = get_close_matches(tag_name, sorted(supported_tags), n=3, cutoff=0.72)
    if close_matches:
        return "Unsupported SXSD tag. Did you mean " + ", ".join(f"<{match}>" for match in close_matches) + "?"
    return "Unsupported SXSD tag. Use only tags defined in slides_xml_schema_definition.xml."


def suggest_sxsd_attrs(attr_name: str, allowed_attrs: set[str]) -> list[str]:
    alias = SXSD_ATTR_ALIASES.get(attr_name)
    if alias and alias in allowed_attrs:
        return [alias]
    return get_close_matches(attr_name, sorted(allowed_attrs), n=3, cutoff=0.68)


def build_sxsd_attr_hint(tag_name: str, attr_name: str, allowed_attrs: set[str]) -> str:
    suggestions = suggest_sxsd_attrs(attr_name, allowed_attrs)
    if suggestions:
        if SXSD_ATTR_ALIASES.get(attr_name) == suggestions[0]:
            return f'Use "{suggestions[0]}" on <{tag_name}> instead of "{attr_name}".'
        return "Unsupported SXSD attribute. Did you mean " + ", ".join(f'"{match}"' for match in suggestions) + "?"
    allowed_summary = ", ".join(sorted(allowed_attrs)[:8])
    if len(allowed_attrs) > 8:
        allowed_summary += ", ..."
    return f"Unsupported SXSD attribute for <{tag_name}>. Allowed attributes include: {allowed_summary}."


def should_skip_sxsd_subtree(element: ET.Element, ancestors: list[str]) -> bool:
    return ("whiteboard" in ancestors or "embed" in ancestors) and xml_namespace(element.tag) == SVG_NS


def should_skip_sxsd_attribute(tag_name: str, attr_name: str) -> bool:
    return attr_name in SERVER_FILLED_SXSD_ATTRS or (tag_name, attr_name) in ROUNDTRIP_SXSD_ATTRS


def should_skip_sxsd_tag(parent_name: str | None, tag_name: str) -> bool:
    return (parent_name, tag_name) in ROUNDTRIP_SXSD_TAGS


def without_server_filled_sxsd_fields(root: ET.Element) -> ET.Element:
    sanitized_root = copy.deepcopy(root)

    def sanitize(element: ET.Element) -> None:
        tag_name = xml_local_name(element.tag)
        for raw_attr_name in list(element.attrib):
            if should_skip_sxsd_attribute(tag_name, xml_local_name(raw_attr_name)):
                del element.attrib[raw_attr_name]
        for child in list(element):
            if should_skip_sxsd_tag(tag_name, xml_local_name(child.tag)):
                element.remove(child)
                continue
            sanitize(child)

    sanitize(sanitized_root)
    return sanitized_root


def validate_sxsd_document(xml: str, root: ET.Element) -> list[dict[str, Any]]:
    tag_attributes = load_sxsd_tag_attributes()
    supported_tags = set(tag_attributes)
    issues: list[dict[str, Any]] = []
    suggested_attr_candidates: dict[tuple[str, str], list[set[str]]] = {}

    def visit(element: ET.Element, ancestors: list[str], path: str) -> None:
        if should_skip_sxsd_subtree(element, ancestors):
            return

        tag_name = xml_local_name(element.tag)
        current_path = f"{path}/{tag_name}" if path else tag_name
        parent_name = ancestors[-1] if ancestors else None
        if should_skip_sxsd_tag(parent_name, tag_name):
            return
        if tag_name not in supported_tags:
            issues.append(
                {
                    "level": "error",
                    "code": "sxsd_unsupported_tag",
                    "tag": tag_name,
                    "path": current_path,
                    "message": f"unsupported SXSD tag <{tag_name}> at {current_path}",
                    "hint": build_sxsd_tag_hint(tag_name, supported_tags),
                }
            )
            return
        else:
            allowed_attrs = tag_attributes[tag_name]
            for raw_attr_name in element.attrib:
                if raw_attr_name.startswith(XML_NS):
                    continue
                attr_name = xml_local_name(raw_attr_name)
                if should_skip_sxsd_attribute(tag_name, attr_name):
                    continue
                if attr_name in allowed_attrs:
                    continue
                suggestions = suggest_sxsd_attrs(attr_name, allowed_attrs)
                if suggestions:
                    suggested_attr_candidates.setdefault((current_path, tag_name), []).append(
                        set(suggestions)
                    )
                issues.append(
                    {
                        "level": "error",
                        "code": "sxsd_unsupported_attr",
                        "tag": tag_name,
                        "attr": attr_name,
                        "path": current_path,
                        "message": f'unsupported SXSD attribute "{attr_name}" on <{tag_name}> at {current_path}',
                        "hint": build_sxsd_attr_hint(tag_name, attr_name, allowed_attrs),
                    }
                )

        for child in element:
            visit(child, [*ancestors, tag_name], current_path)

    visit(root, [], "")
    existing = {
        (issue.get("code"), issue.get("path"), issue.get("tag"), issue.get("attr"))
        for issue in issues
    }
    unsupported_tag_locations = {
        (issue.get("path"), issue.get("tag"))
        for issue in issues
        if issue.get("code") == "sxsd_unsupported_tag"
    }
    schema_issues = _validate_sxsd_schema_constraints(xml, root)
    missing_attrs_by_location: dict[tuple[str, str], set[str]] = {}
    for schema_issue in schema_issues:
        if schema_issue.get("code") != "sxsd_missing_required_attr":
            continue
        location = (schema_issue.get("path"), schema_issue.get("tag"))
        missing_attrs_by_location.setdefault(location, set()).add(schema_issue.get("attr"))

    suggested_attrs: set[tuple[str, str, str]] = set()
    for location, candidate_groups in suggested_attr_candidates.items():
        missing_attrs = missing_attrs_by_location.get(location, set())
        for candidates in candidate_groups:
            matching_missing_attrs = candidates & missing_attrs
            if len(matching_missing_attrs) == 1:
                suggested_attrs.add((*location, next(iter(matching_missing_attrs))))

    for schema_issue in schema_issues:
        if schema_issue.get("code") == "sxsd_unexpected_child" and (
            schema_issue.get("path"),
            schema_issue.get("tag"),
        ) in unsupported_tag_locations:
            continue
        if schema_issue.get("code") == "sxsd_missing_required_attr" and (
            schema_issue.get("path"),
            schema_issue.get("tag"),
            schema_issue.get("attr"),
        ) in suggested_attrs:
            continue
        key = (
            schema_issue.get("code"),
            schema_issue.get("path"),
            schema_issue.get("tag"),
            schema_issue.get("attr"),
        )
        if key not in existing:
            issues.append(schema_issue)
    return issues


def _validate_sxsd_schema_constraints(xml: str, root: ET.Element) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if re.match(r"^\s*<\?xml\b", xml):
        issues.append(
            {
                "level": "error",
                "code": "sxsd_unsupported_declaration",
                "path": xml_local_name(root.tag),
                "tag": xml_local_name(root.tag),
                "expected": "SXSD document without an XML declaration",
                "actual": "<?xml ...?>",
                "message": "XML declarations are not supported by the Slides SXSD write format",
                "hint": "Remove the <?xml ...?> declaration and keep the SXSD root element.",
            }
        )

    issues.extend(
        sxsd_validator.validate_sxsd(
            without_server_filled_sxsd_fields(root),
            SXSD_SCHEMA_PATH,
        )
    )
    issues.extend(validate_embed_svg_roots(root))
    return issues


def validate_embed_svg_roots(root: ET.Element) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    document_namespace = sxsd_validator.element_namespace(root.tag)
    is_bare_slide_fragment = (
        xml_local_name(root.tag) == "slide" and document_namespace is None
    )
    if (
        document_namespace not in sxsd_validator.ACCEPTED_SML_NAMESPACES
        and not is_bare_slide_fragment
    ):
        return issues

    def visit(element: ET.Element, ancestors: list[str], parent_path: str) -> None:
        if should_skip_sxsd_subtree(element, ancestors):
            return

        tag_name = xml_local_name(element.tag)
        path = f"{parent_path}/{tag_name}" if parent_path else tag_name
        if (
            tag_name == "embed"
            and sxsd_validator.element_namespace(element.tag) == document_namespace
        ):
            for child in element:
                if xml_namespace(child.tag) != SVG_NS or xml_local_name(child.tag) == "svg":
                    continue
                child_name = xml_local_name(child.tag)
                child_path = f"{path}/{child_name}"
                issues.append(
                    {
                        "level": "error",
                        "code": "sxsd_unexpected_child",
                        "path": child_path,
                        "tag": child_name,
                        "expected": '<svg xmlns="http://www.w3.org/2000/svg">',
                        "actual": child_name,
                        "message": f"embedded SVG content must use an <svg> root at {child_path}",
                        "hint": 'Wrap the SVG content in <svg xmlns="http://www.w3.org/2000/svg">...</svg>.',
                    }
                )
        for child in element:
            visit(child, [*ancestors, tag_name], path)

    visit(root, [], "")
    return issues


def build_iconpark_icon_type_hint(icon_type: str, supported_icon_types: set[str]) -> str:
    close_matches = get_close_matches(icon_type, sorted(supported_icon_types), n=3, cutoff=0.58)
    if close_matches:
        return (
            "iconType must exist in iconpark-index.json. Did you mean "
            + ", ".join(f'"{match}"' for match in close_matches)
            + "?"
        )
    return "iconType must exist in iconpark-index.json. Use scripts/iconpark_tool.py to search supported icons."


def validate_iconpark_icon_types(root: ET.Element) -> list[dict[str, Any]]:
    supported_icon_types: set[str] | None = None
    issues: list[dict[str, Any]] = []

    def direct_child(element: ET.Element, local_name: str) -> ET.Element | None:
        return next((child for child in element if xml_local_name(child.tag) == local_name), None)

    def is_transparent_color(color: str) -> bool:
        normalized = re.sub(r"\s+", "", color).lower()
        if normalized == "transparent":
            return True
        rgba_match = re.fullmatch(r"rgba\([^,]+,[^,]+,[^,]+,([0-9.]+)\)", normalized)
        if not rgba_match:
            return False
        try:
            return float(rgba_match.group(1)) <= 0
        except ValueError:
            return False

    def append_missing_fill_color_issue(current_path: str) -> None:
        issues.append(
            {
                "level": "error",
                "code": "icon_missing_fill_color",
                "tag": "icon",
                "path": current_path,
                "message": f"<icon> must set explicit non-transparent fillColor for visual visibility at {current_path}",
                "hint": 'Add <fill><fillColor color="rgba(R, G, B, 1)"/></fill> inside <icon>. This is a visual lint rule, not an SXSD required field.',
            }
        )

    def visit(element: ET.Element, ancestors: list[str], path: str) -> None:
        nonlocal supported_icon_types
        if should_skip_sxsd_subtree(element, ancestors):
            return

        tag_name = xml_local_name(element.tag)
        current_path = f"{path}/{tag_name}" if path else tag_name
        if tag_name == "icon":
            icon_type = element.attrib.get("iconType")
            if icon_type is not None:
                if supported_icon_types is None:
                    supported_icon_types = load_iconpark_icon_types()
                if icon_type not in supported_icon_types:
                    issues.append(
                        {
                            "level": "error",
                            "code": "iconpark_unsupported_icon_type",
                            "tag": "icon",
                            "attr": "iconType",
                            "iconType": icon_type,
                            "path": current_path,
                            "message": f'unsupported iconpark iconType "{icon_type}" at {current_path}',
                            "hint": build_iconpark_icon_type_hint(icon_type, supported_icon_types),
                        }
                    )
            fill = direct_child(element, "fill")
            fill_color = direct_child(fill, "fillColor") if fill is not None else None
            color = fill_color.attrib.get("color") if fill_color is not None else None
            if not color:
                append_missing_fill_color_issue(current_path)
            elif is_transparent_color(color):
                issues.append(
                    {
                        "level": "error",
                        "code": "icon_transparent_fill_color",
                        "tag": "icon",
                        "attr": "fillColor",
                        "path": current_path,
                        "color": color,
                        "message": f'<icon> fillColor must not be transparent for visual visibility at {current_path}: "{color}"',
                        "hint": 'Use an opaque visible color, for example <fillColor color="rgba(37, 99, 235, 1)"/>.',
                    }
                )
        for child in element:
            visit(child, [*ancestors, tag_name], current_path)

    visit(root, [], "")
    return issues


def field_declares_numeric_value(field: ET.Element) -> bool:
    """True when a <chartField> supplies a series that can drive the value (vertical) axis.

    Prefer the author's declared valueType="number" (schema slides_xml_schema_definition.xml): that is
    the field's stated contract, so trust it even if the sample text is empty or unusual. Fall back to
    inspecting the text as a numeric CSV when valueType is absent (older/hand-authored markup). ET.text
    is the author's original run and excludes the server-readback <chartParsedValues> child echoes.
    """
    value_type = (field.attrib.get("valueType") or "").strip().lower()
    if value_type == "number":
        return True
    if value_type == "string":
        return False
    return is_numeric_value_csv(field.text or "")


def validate_chart_value_semantics(root: ET.Element) -> list[dict[str, Any]]:
    """Flag chart nodes whose value rendering will break: no numeric series for the value axis,
    a data label with nothing to show, or a number-format code that uses template placeholders
    instead of a real format code.

    Three checks share one AST walk over the chart subtree:

    - <chartData> whose dim1/dim2 carry no numeric series. The value (vertical) axis scales
      numbers, so at least one <chartField> across <dim1>/<dim2> must supply a numeric series
      (valueType="number", or a pure number+comma CSV like "52,48,55,68"). A category-only
      chartData leaves the axis with nothing to plot and renders abnormally.
    - a <chartLabels> whose category, value and percentage toggles are all false. At least one
      must be on (value defaults to true) or the data label renders empty.
    - a `format` attribute (on chartLabels/chartTooltip/chartLabel) that contains "{" or "}".
      `format` is an Excel-style number-format code (e.g. 0%, #,##0.00, 0万); template
      placeholders like "{value}bp" borrowed from other chart libraries are emitted verbatim.

    Mirrors validate_iconpark_icon_types' AST walk, and mirrors extract_source_id_elements' indexed
    xml_path scheme (slide[N]/data/chart[k]/...) plus the chart id so a fix agent can locate the
    exact node -- top-level issues carry no slide_number from the caller, so we embed the locators in
    the issue's own target/path here.
    """
    root_name = xml_local_name(root.tag)
    if root_name == "slide":
        numbered_slides = [(1, root)]
    elif root_name == "presentation":
        numbered_slides = list(
            enumerate(
                (child for child in root if xml_local_name(child.tag) == "slide"), start=1
            )
        )
    else:
        return []

    issues: list[dict[str, Any]] = []

    def visit(
        element: ET.Element,
        ancestors: list[str],
        path: str,
        chart: ET.Element | None,
        chart_path: str | None,
    ) -> None:
        if should_skip_sxsd_subtree(element, ancestors):
            return
        tag_name = xml_local_name(element.tag)
        owner_chart = element if tag_name == "chart" else chart
        owner_chart_path = path if tag_name == "chart" else chart_path
        if tag_name == "chartData":
            fields = [
                field
                for child in element
                if xml_local_name(child.tag) in {"dim1", "dim2"}
                for field in child
                if xml_local_name(field.tag) == "chartField"
            ]
            if fields and not any(field_declares_numeric_value(field) for field in fields):
                chart_id = owner_chart.attrib.get("id") if owner_chart is not None else None
                chart_path_value = owner_chart_path or path
                locator = chart_id or chart_path_value
                issues.append(
                    {
                        "level": "error",
                        "code": "chart_missing_numeric_dimension",
                        "tag": "chartData",
                        "path": path,
                        "target": {
                            **({"chart_id": chart_id} if chart_id else {}),
                            "chart_xml_path": chart_path_value,
                            "chartData_xml_path": path,
                        },
                        "message": (
                            f"chart {locator} has no numeric dimension: neither dim1 nor dim2 supplies "
                            "a numeric series (valueType=\"number\" or a pure number+comma CSV) to "
                            "render the value axis"
                        ),
                        "hint": (
                            f"Locate the chart via target.chart_xml_path ({chart_path_value}). Give dim1 "
                            'or dim2 a <chartField valueType="number"> whose value is digits joined by '
                            'English commas (e.g. "52,48,55,68"). A category-only chartData leaves the '
                            "value axis with nothing to scale and it renders abnormally."
                        ),
                    }
                )
        if tag_name == "chartLabels" and owner_chart is not None:
            # category/value/percentage are the three "what to show" toggles; at least one must be
            # on or the label renders empty. Defaults per schema: value=true, other two false, so an
            # untouched <chartLabels> is fine -- only an explicit value="false" without turning on
            # category/percentage produces a blank label.
            def label_toggle(name: str, default: bool) -> bool:
                raw = element.attrib.get(name)
                return default if raw is None else raw in {"true", "1", "yes"}

            if not (
                label_toggle("value", True)
                or label_toggle("category", False)
                or label_toggle("percentage", False)
            ):
                chart_id = owner_chart.attrib.get("id")
                chart_path_value = owner_chart_path or path
                locator = chart_id or chart_path_value
                issues.append(
                    {
                        "level": "error",
                        "code": "chart_labels_nothing_to_show",
                        "tag": "chartLabels",
                        "path": path,
                        "target": {
                            **({"chart_id": chart_id} if chart_id else {}),
                            "chart_xml_path": chart_path_value,
                            "element_xml_path": path,
                        },
                        "message": (
                            f"chart {locator} has a <chartLabels> with category, value and percentage "
                            "all false, so the data label renders empty"
                        ),
                        "hint": (
                            f"Locate the element via target.element_xml_path ({path}). Set at least one "
                            'of value="true", category="true" or percentage="true" (value defaults to '
                            "true, so usually just drop the explicit value=\"false\")."
                        ),
                    }
                )
        if owner_chart is not None and "format" in element.attrib:
            fmt = element.attrib.get("format", "")
            if "{" in fmt or "}" in fmt:
                chart_id = owner_chart.attrib.get("id")
                chart_path_value = owner_chart_path or path
                locator = chart_id or chart_path_value
                issues.append(
                    {
                        "level": "error",
                        "code": "chart_invalid_format_code",
                        "tag": tag_name,
                        "path": path,
                        "target": {
                            **({"chart_id": chart_id} if chart_id else {}),
                            "chart_xml_path": chart_path_value,
                            "element_xml_path": path,
                            "format": fmt,
                        },
                        "message": (
                            f'chart {locator} has an invalid format="{fmt}" on <{tag_name}>: `format` '
                            "is an Excel-style number-format code and does not expand template "
                            'placeholders like "{value}", so the braces render verbatim'
                        ),
                        "hint": (
                            f"Locate the element via target.element_xml_path ({path}). Replace the "
                            "placeholder with a real number-format code such as 0, 0.00, 0%, #,##0.00, "
                            'or 0万. Unit suffixes belong in the code itself (append literal text), not '
                            'as a "{value}" placeholder.'
                        ),
                    }
                )
        child_counts: dict[str, int] = {}
        for child in element:
            kind = xml_local_name(child.tag)
            child_counts[kind] = child_counts.get(kind, 0) + 1
            child_path = (
                f"{path}/data"
                if tag_name == "slide" and kind == "data"
                else f"{path}/{kind}[{child_counts[kind]}]"
            )
            visit(child, [*ancestors, tag_name], child_path, owner_chart, owner_chart_path)

    for slide_number, slide_root in numbered_slides:
        visit(slide_root, [], f"slide[{slide_number}]", None, None)

    return issues


def extract_error_context(xml: str, line: int | None, column: int | None, radius: int = 40) -> str | None:
    if line is None or column is None:
        return None
    lines = xml.splitlines()
    if line < 1 or line > len(lines):
        return None
    source_line = lines[line - 1]
    start = max(column - radius, 0)
    end = min(column + radius, len(source_line))
    return source_line[start:end].strip()


def build_xml_error_issue(error: ET.ParseError, xml: str) -> dict[str, Any]:
    line, column = getattr(error, "position", (None, None))
    return {
        "level": "error",
        "code": "xml_not_well_formed",
        "message": f"XML is not well-formed: {error}",
        "line": line,
        "column": column,
        "context": extract_error_context(xml, line, column),
        "hint": (
            "Escape raw user text before placing it in XML. In text nodes and attribute values, bare & must be "
            "written as &amp;. In text nodes, write < as &lt; and > as &gt;. For attribute URLs, use a=1&amp;b=2."
        ),
    }


def validate_sml_tag_prefixes(xml: str) -> list[dict[str, Any]]:
    namespace_map: dict[str, str] = {}
    pending_declarations: list[tuple[str, str | None]] = []
    declarations_by_element: list[list[tuple[str, str | None]]] = []
    element_stack: list[str] = []
    issues: list[dict[str, Any]] = []

    parser = expat.ParserCreate(namespace_separator="|")
    parser.namespace_prefixes = True

    def handle_namespace_decl(prefix: str | None, namespace: str) -> None:
        normalized_prefix = prefix or ""
        previous_namespace = namespace_map.get(normalized_prefix)
        namespace_map[normalized_prefix] = namespace
        pending_declarations.append((normalized_prefix, previous_namespace))

    def handle_start_element(name: str, _attrs: dict[str, str]) -> None:
        declarations_by_element.append(pending_declarations.copy())
        pending_declarations.clear()
        name_parts = name.rsplit("|", 2)
        if len(name_parts) == 3:
            _namespace, local_name, prefix = name_parts
            element_name = f"{prefix}:{local_name}"
        else:
            prefix = ""
            local_name = name_parts[-1]
            element_name = local_name
        element_stack.append(element_name)
        if not prefix:
            return

        actual_namespace = namespace_map.get(prefix)
        if actual_namespace not in sxsd_validator.ACCEPTED_SML_NAMESPACES:
            return
        path = "/".join(element_stack)
        issues.append(
            {
                "level": "error",
                "code": "sml_prefixed_tag",
                "tag": element_name,
                "namespace": actual_namespace,
                "path": path,
                "line": parser.CurrentLineNumber,
                "column": parser.CurrentColumnNumber,
                "message": f"SML tag <{element_name}> must not use a namespace prefix at {path}",
                "hint": (
                    f'Use <{local_name}> under the default namespace '
                    f'<{local_name} xmlns="{SML_NAMESPACE}">, or use an unprefixed SML tag.'
                ),
            }
        )

    def handle_end_element(_name: str) -> None:
        for prefix, previous_namespace in reversed(declarations_by_element.pop()):
            if previous_namespace is None:
                namespace_map.pop(prefix, None)
            else:
                namespace_map[prefix] = previous_namespace
        element_stack.pop()

    parser.StartNamespaceDeclHandler = handle_namespace_decl
    parser.StartElementHandler = handle_start_element
    parser.EndElementHandler = handle_end_element
    parser.Parse(xml, True)
    return issues


def parse_xml_root(xml: str) -> tuple[ET.Element | None, dict[str, Any] | None]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        return None, build_xml_error_issue(error, xml)

    root_name = xml_local_name(root.tag)
    if root_name not in {"presentation", "slide"}:
        fail("input must contain a <presentation> or <slide> root")
    return root, None


def validate_xml_well_formed(xml: str) -> dict[str, Any] | None:
    _, xml_error = parse_xml_root(xml)
    return xml_error


def serialize_slide_for_layout(slide_root: ET.Element) -> str:
    slide_copy = copy.deepcopy(slide_root)
    for element in slide_copy.iter():
        if not isinstance(element.tag, str):
            continue
        element.tag = xml_local_name(element.tag)
        attributes = {
            xml_local_name(attribute_name): value
            for attribute_name, value in element.attrib.items()
        }
        element.attrib.clear()
        element.attrib.update(attributes)
    return ET.tostring(slide_copy, encoding="unicode")


def parse_presentation(root: ET.Element) -> dict[str, Any]:
    root_name = xml_local_name(root.tag)
    if root_name == "slide":
        slide_roots = [root]
        width = 960
        height = 540
    elif root_name == "presentation":
        slide_roots = [child for child in root if xml_local_name(child.tag) == "slide"]
        width = int(float(root.attrib.get("width", 960)))
        height = int(float(root.attrib.get("height", 540)))
    else:
        fail("input must contain a <presentation> or <slide> root")
    return {
        "width": width,
        "height": height,
        "slides": [serialize_slide_for_layout(slide_root) for slide_root in slide_roots],
        "slide_roots": slide_roots,
    }


def build_source_xml_paths(slide_xml: str, slide_number: int) -> dict[str, list[str]]:
    root = ET.fromstring(slide_xml)
    data = next((child for child in root if xml_local_name(child.tag) == "data"), None)
    paths: dict[str, list[str]] = {}
    if data is None:
        return paths
    counts: dict[str, int] = {}
    for child in data:
        kind = xml_local_name(child.tag)
        counts[kind] = counts.get(kind, 0) + 1
        paths.setdefault(kind, []).append(
            f"slide[{slide_number}]/data/{kind}[{counts[kind]}]"
        )
    return paths


def attach_source_xml_paths(
    elements: list[dict[str, Any]], source_paths: dict[str, list[str]]
) -> None:
    offsets: dict[str, int] = {}
    for element in elements:
        kind = element["kind"]
        source_kind_index = element.get("_source_kind_index")
        offset = (
            source_kind_index - 1
            if isinstance(source_kind_index, int) and source_kind_index > 0
            else offsets.get(kind, 0)
        )
        kind_paths = source_paths.get(kind, [])
        if offset < len(kind_paths):
            element["xml_path"] = kind_paths[offset]
            element["_ref"] = kind_paths[offset]
        offsets[kind] = max(offsets.get(kind, 0), offset + 1)


def extract_source_id_elements(slide_xml: str, slide_number: int) -> list[dict[str, Any]]:
    root = ET.fromstring(slide_xml)
    elements: list[dict[str, Any]] = []
    root_path = f"slide[{slide_number}]"

    def walk(parent: ET.Element, parent_path: str) -> None:
        child_counts: dict[str, int] = {}
        for child in parent:
            kind = xml_local_name(child.tag)
            child_counts[kind] = child_counts.get(kind, 0) + 1
            xml_path = (
                f"{parent_path}/data"
                if parent is root and kind == "data"
                else f"{parent_path}/{kind}[{child_counts[kind]}]"
            )
            source_id = extract_attribute(
                ET.tostring(child, encoding="unicode").split(">", 1)[0], "id"
            )
            if source_id:
                elements.append(
                    {
                        "id": source_id,
                        "_source_id": source_id,
                        "kind": kind,
                        "type": child.attrib.get("type") or kind,
                        "xml_path": xml_path,
                        "_ref": xml_path,
                        "_slide_number": slide_number,
                    }
                )
            walk(child, xml_path)

    walk(root, root_path)
    return elements


def element_ref(element: dict[str, Any]) -> str:
    ref = element.get("_ref") or element.get("xml_path")
    if isinstance(ref, str) and ref:
        return ref
    # Low-level detector tests and external callers may pass already-extracted objects.
    # The lint_xml pipeline always attaches the source path before issue detection.
    fallback = element.get("id")
    if isinstance(fallback, str) and fallback:
        return fallback
    raise AssertionError("lint element must have a source xml path or fallback id")


def source_element_id(element: dict[str, Any]) -> str | None:
    value = element.get("_source_id")
    return value if isinstance(value, str) and value else None


def element_label(element: dict[str, Any]) -> str:
    return source_element_id(element) or element_ref(element)


def extract_elements(slide_xml: str) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    source_kind_counts: dict[str, int] = {}

    for match in re.finditer(r"<(shape|img|table|chart|whiteboard|embed)\b([^>]*)>", slide_xml):
        kind, attrs = match.group(1), match.group(2)
        source_kind_counts[kind] = source_kind_counts.get(kind, 0) + 1
        source_kind_index = source_kind_counts[kind]
        is_self_closing = attrs.rstrip().endswith("/")
        content = ""
        if kind in {"shape", "table", "chart"} and not is_self_closing:
            close_index = slide_xml.find(f"</{kind}>", match.end())
            if close_index != -1:
                content = slide_xml[match.end() : close_index]

        source_id = extract_attribute(attrs, "id") or None
        element_id = source_id or f"{kind}-{len(elements) + 1}"
        x = extract_numeric_attribute(attrs, "topLeftX")
        y = extract_numeric_attribute(attrs, "topLeftY")
        width = extract_numeric_attribute(attrs, "width")
        height = extract_numeric_attribute(attrs, "height")
        rotation = extract_numeric_attribute(attrs, "rotation") or 0
        alpha = extract_numeric_attribute(attrs, "alpha")
        table_layouts: dict[str, dict[str, Any] | None] = {}
        if kind == "table":
            width, table_layouts["width"] = resolve_table_dimension(
                content, width, extract_table_column_sizes, DEFAULT_TABLE_COLUMN_WIDTH
            )
            height, table_layouts["height"] = resolve_table_dimension(
                content, height, extract_table_row_sizes, DEFAULT_TABLE_ROW_HEIGHT
            )
        if all(value is not None for value in [x, y, width, height]):
            element = {
                "id": element_id,
                "_source_id": source_id,
                "kind": kind,
                "type": extract_attribute(attrs, "type") or kind,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotation": rotation,
                "alpha": alpha if alpha is not None else 1,
                "order": len(elements),
                "_source_kind_index": source_kind_index,
            }
            if kind == "table":
                element.update(
                    {
                        "declared_width": extract_numeric_attribute(attrs, "width"),
                        "declared_height": extract_numeric_attribute(attrs, "height"),
                        "table_layouts": table_layouts,
                    }
                )
            if kind == "chart":
                element["donut_hole"] = compute_donut_center_hole(element, content)
            if kind == "shape":
                content_attrs = extract_tag_attributes(content, "content")
                font_size = extract_numeric_attribute(content_attrs, "fontSize")
                if font_size is None:
                    font_size = extract_numeric_attribute(attrs, "fontSize")
                font_family = extract_attribute(content_attrs, "fontFamily") or extract_attribute(attrs, "fontFamily")
                text_color = extract_attribute(content_attrs, "color") or extract_attribute(attrs, "color")
                bold = (
                    extract_bool_attribute(content_attrs, "bold")
                    or extract_bool_attribute(attrs, "bold")
                    or detect_inline_style_presence(content, {"strong", "b"})
                    or detect_any_span_bool_attribute(content, "bold")
                )
                italic = (
                    extract_bool_attribute(content_attrs, "italic")
                    or extract_bool_attribute(attrs, "italic")
                    or detect_inline_style_presence(content, {"i", "em"})
                    or detect_any_span_bool_attribute(content, "italic")
                )
                element.update(
                    {
                        "textType": extract_attribute(content_attrs, "textType"),
                        "textAlign": extract_attribute(content_attrs, "textAlign"),
                        "verticalAlign": extract_attribute(content_attrs, "verticalAlign") or "middle",
                        "vert": extract_attribute(attrs, "vert") or "horz",
                        "autoFit": extract_attribute(content_attrs, "autoFit"),
                        "wrap": extract_attribute(content_attrs, "wrap"),
                        "lineSpacing": extract_attribute(content_attrs, "lineSpacing"),
                        "beforeLineSpacing": extract_attribute(content_attrs, "beforeLineSpacing"),
                        "afterLineSpacing": extract_attribute(content_attrs, "afterLineSpacing"),
                        "letterSpacing": extract_numeric_attribute(content_attrs, "letterSpacing"),
                        "paddingTop": extract_numeric_attribute(content_attrs, "paddingTop") or 0,
                        "paddingRight": extract_numeric_attribute(content_attrs, "paddingRight") or 0,
                        "paddingBottom": extract_numeric_attribute(content_attrs, "paddingBottom") or 0,
                        "paddingLeft": extract_numeric_attribute(content_attrs, "paddingLeft") or 0,
                        "fontSize": font_size if font_size is not None else 16,
                        "fontFamily": font_family or "",
                        "color": text_color,
                        "fillAlpha": extract_fill_alpha(content, element["type"]),
                        "textAlpha": effective_text_alpha(alpha, text_color),
                        "bold": bold,
                        "italic": italic,
                        "text": strip_xml_paragraphs(content),
                        "text_raw": strip_xml_paragraphs_preserving_spaces(content),
                        "paragraphs": extract_text_paragraphs(content, font_size if font_size is not None else 16),
                    }
                )
            elements.append(element)
    return elements


def intersects(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["x"] < right["x"] + right["width"]
        and left["x"] + left["width"] > right["x"]
        and left["y"] < right["y"] + right["height"]
        and left["y"] + left["height"] > right["y"]
    )


def is_text_element(element: dict[str, Any]) -> bool:
    return element["kind"] == "shape" and element["type"] == "text"


def is_whiteboard_element(element: dict[str, Any]) -> bool:
    return element["kind"] == "whiteboard"


def has_text_content(element: dict[str, Any]) -> bool:
    return bool(element.get("text"))


def is_vertical_text(element: dict[str, Any]) -> bool:
    return element.get("vert") in {"vert", "vert270", "word-art-vert", "word-art-vert-rtl", "ea-vert"}


def detect_table_text_occlusions(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag text glyphs that land on top of (or under) a table's cell grid.

    Mirrors detect_image_text_occlusions but for <table>. A free-floating text run whose glyph box
    intersects a sibling table is almost always an accidental overlay -- the table already renders its
    own cell text, so an unrelated shape sitting over the grid occludes it (slides p4). Text that is a
    table cell child is part of the table's own layout and never extracted as a standalone element, so
    this only ever sees sibling shapes. z-order is intentionally ignored: whether the text sits above
    or below the grid, the two sets of glyphs collide in the same pixels.
    """
    issues: list[dict[str, Any]] = []
    text_elements = [
        element
        for element in elements
        if is_text_element(element) and has_text_content(element) and not is_ghost_text(element)
    ]
    tables = [element for element in elements if element["kind"] == "table" and element["alpha"] > 0]
    for text_element in text_elements:
        if is_decorative_text(text_element):
            continue
        glyph_bbox = estimate_text_visual_bbox(text_element)
        if glyph_bbox is None:
            continue
        for table in tables:
            if not intersects(table, glyph_bbox):
                continue
            issues.append({
                "level": "error",
                "code": "table_covers_text",
                "elements": [element_ref(table), element_ref(text_element)],
                "message": f"text shape {element_label(text_element)} overlaps table {element_label(table)}",
                "hint": "Move the text shape off the table grid or into a table cell; a free shape on top of the grid occludes the cell contents.",
            })
    return issues


def compute_donut_center_hole(element: dict[str, Any], content: str) -> dict[str, Any] | None:
    """Return the empty center-hole circle of a donut chart, or None if the chart is not a donut.

    A donut is a `<chartPlot type="pie">` whose `<chartSectors>` carries an `innerRadius` fraction
    (0..1) of the pie radius that is punched out as an empty hole -- the classic ring chart with a
    headline like "70%+ / API收入占比" sitting in its middle. That center is genuinely blank pixels,
    so a text shape placed there occludes nothing. We model the hole conservatively: the pie is a
    circle centered on the chart bbox with radius min(w, h)/2, and the hole radius is innerRadius of
    that. Legends/labels shrink and can offset the real pie, so callers must require full containment
    (not mere intersection) before suppressing -- text grazing the ring itself must still be flagged.
    """
    plot_attrs = extract_tag_attributes(content, "chartPlot")
    if extract_attribute(plot_attrs, "type") != "pie":
        return None
    sectors_attrs = extract_tag_attributes(content, "chartSectors")
    inner_radius = extract_numeric_attribute(sectors_attrs, "innerRadius")
    if inner_radius is None or inner_radius <= 0:
        return None
    if inner_radius > 1:
        return None
    pie_radius = min(element["width"], element["height"]) / 2
    return {
        "cx": element["x"] + element["width"] / 2,
        "cy": element["y"] + element["height"] / 2,
        "radius": inner_radius * pie_radius,
    }


def bbox_within_circle(bbox: dict[str, Any], circle: dict[str, Any]) -> bool:
    """True when every corner of bbox lies inside the circle (full containment, not intersection)."""
    corners = (
        (bbox["x"], bbox["y"]),
        (bbox["x"] + bbox["width"], bbox["y"]),
        (bbox["x"], bbox["y"] + bbox["height"]),
        (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
    )
    return all(math.hypot(px - circle["cx"], py - circle["cy"]) <= circle["radius"] for px, py in corners)


def detect_chart_text_occlusions(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag text glyphs that land on top of (or under) a chart's plot area.

    Mirrors detect_table_text_occlusions but for <chart> (slides p5: a pie/donut chart bqP with the
    headline "abc 99%" and a caption "图表遮挡" dropped onto its ring). A chart draws its own axis
    labels, legend and data labels, so an unrelated text shape sitting over the plot box collides with
    that generated content. z-order is intentionally ignored -- whether the text is above or below the
    chart, the glyphs share the same pixels. Text that is chart-internal (titles, data labels) lives
    inside the <chart> node and is never extracted as a standalone element, so this only ever sees
    sibling shapes.
    """
    issues: list[dict[str, Any]] = []
    # A text run over the chart can be authored either as a standalone <shape type="text"> or as text
    # carried on a non-text shape (slides p6: a rect "shape遮挡" dropped onto the ring). Both paint
    # glyphs onto the plot area, so own the collision to the estimated glyph box of whichever shape
    # carries the text -- estimate_text_visual_bbox for a text shape, own_text_visual_bbox for a
    # text-bearing container shape.
    text_elements = [
        element
        for element in elements
        if element["kind"] == "shape"
        and has_text_content(element)
        and not is_ghost_text(element)
        and not is_line_like_shape(element)
    ]
    charts = [element for element in elements if element["kind"] == "chart" and element["alpha"] > 0]
    for text_element in text_elements:
        if is_decorative_text(text_element):
            continue
        glyph_bbox = (
            estimate_text_visual_bbox(text_element)
            if is_text_element(text_element)
            else own_text_visual_bbox(text_element)
        )
        if glyph_bbox is None:
            continue
        for chart in charts:
            if not intersects(chart, glyph_bbox):
                continue
            hole = chart.get("donut_hole")
            if hole is not None and bbox_within_circle(glyph_bbox, hole):
                # A headline sitting inside a ring chart's empty center occludes nothing.
                continue
            issues.append({
                "level": "error",
                "code": "chart_covers_text",
                "elements": [element_ref(chart), element_ref(text_element)],
                "message": f"text shape {element_label(text_element)} overlaps chart {element_label(chart)}",
                "hint": "Move the text shape off the chart plot area; a free shape on top of the chart occludes its axis labels, legend, and data labels.",
            })
    return issues


def is_numeric_value_csv(text: str) -> bool:
    """True when text is a pure numeric CSV -- the axis series that renders the value (vertical) axis.

    A value axis scales numbers, so the driving dimension must be digits joined by English commas
    (e.g. "52,48,55,68" or "0.55,0.42"). Category labels like "Q1,Q2" or "1月,2月" are not numeric and
    cannot drive the axis. Every comma-separated cell must parse as a number for the field to qualify.
    """
    stripped = text.strip()
    if not stripped:
        return False
    cells = [cell.strip() for cell in stripped.split(",")]
    if any(cell == "" for cell in cells):
        return False
    for cell in cells:
        try:
            float(cell)
        except ValueError:
            return False
    return True


def is_line_like_shape(element: dict[str, Any]) -> bool:
    """True for divider rules and hairlines -- shapes too thin on one axis to contain text.

    A background container encloses its text; a horizontal/vertical rule merely underlines or
    separates it. Owning text to a 3px-tall rule and then reporting it as an overflowing container
    is a false positive (slides p9, where a title's grown glyph box grazes the section divider).
    """
    return min(element["width"], element["height"]) <= LINE_LIKE_SHAPE_MAX_THICKNESS_PX


def detect_auto_fit_growth_collisions(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag shape-auto-fit text that grew past its authored box into content below it.

    shape-auto-fit grows a text box downward to fit wrapped lines, so growth by itself is benign --
    but only when the space below is empty. When a title wraps to more lines than the author sized
    for and the grown-below region lands on the text following it, the two collide on the rendered
    slide (slides p9: the section title wraps and overlaps the body beneath it). The plain text-text
    overlap check misses this because the collision covers well under 30% of the tall body box; here
    we measure only the grown region against each sibling text run, so any real intrusion is caught.
    We compare against text only: a title growing over a background image or panel is what auto-fit is
    for, whereas growing onto neighbouring copy is the layout break.
    """
    issues: list[dict[str, Any]] = []
    for element in elements:
        if not is_text_element(element) or not has_text_content(element):
            continue
        if element.get("autoFit") != "shape-auto-fit":
            continue
        if is_ghost_text(element) or is_decorative_text(element):
            continue
        glyph = estimate_text_visual_bbox(element)
        if glyph is None:
            continue
        authored_bottom = element["y"] + element["height"]
        grown_bottom = glyph["y"] + glyph["height"]
        growth = grown_bottom - authored_bottom
        if growth <= CONTAINER_OVERFLOW_MIN_PX:
            continue
        grown_region = {"x": glyph["x"], "y": authored_bottom, "width": glyph["width"], "height": growth}
        for other in elements:
            if other is element:
                continue
            if not is_text_element(other) or not has_text_content(other):
                continue
            if is_ghost_text(other) or is_decorative_text(other):
                continue
            other_bbox = estimate_text_visual_bbox(other)
            if other_bbox is None:
                continue
            if intersection_area(grown_region, other_bbox) <= CONTAINER_OVERFLOW_MIN_PX:
                continue
            issues.append({
                "level": "error",
                "code": "bbox_overlap",
                "elements": [element_ref(element), element_ref(other)],
                "message": (
                    f'auto-fit text {element_label(element)} grew {growth:g}px past its box and overlaps {element_label(other)}'
                ),
                "hint": "The shape-auto-fit text wrapped to more lines than its box allows; widen the box, shorten the text, or move the element below it down.",
            })
    return issues


def is_canvas_sized_background_shape(
    element: dict[str, Any], slide_width: int | float, slide_height: int | float
) -> bool:
    """True for a shape that effectively covers the whole slide canvas."""
    canvas_area = slide_width * slide_height
    if canvas_area <= 0:
        return False
    canvas = {"x": 0, "y": 0, "width": slide_width, "height": slide_height}
    return intersection_area(element, canvas) / canvas_area >= FULL_CANVAS_BACKGROUND_COVERAGE_RATIO


def choose_text_container_owner(
    candidates: list[dict[str, Any]],
    text_element: dict[str, Any],
    slide_width: int | float,
    slide_height: int | float,
    adjacency_tolerance: int | float = 0,
) -> dict[str, Any] | None:
    # A caption laid flush against a card's border shares an edge with it: the boxes touch but their
    # intersection area is exactly 0, so raw area ownership would orphan it (slides p12: the labels
    # "路由专家/每token激活/潜空间维度" sit on bgq's bottom edge and spill below). Expanding the
    # candidate box by adjacency_tolerance before scoring lets an edge-flush text still find its owner
    # so the downstream overflow check can fire. The default 0 keeps exact-overlap callers unchanged.
    def contact_score(candidate: dict[str, Any]) -> int | float:
        if adjacency_tolerance <= 0:
            return intersection_area(candidate, text_element)
        # Only expand candidates that genuinely touch (0px gap) the text -- when the real intersection
        # is already positive the tolerance just pads an established owner. A candidate that shares an
        # edge but is smaller than the text along the touching axis is a neighbour (a decorative icon or
        # rule sitting beside the text), not a container the text spills out of: a card that owns a
        # caption is at least as deep as the caption in the direction it hangs past (slides p12). Require
        # that before letting adjacency promote it, or an arrow flush against a title's left edge gets
        # mistaken for the title's container (slides Rejusj: right:492px false positive).
        if intersection_area(candidate, text_element) <= 0:
            overlap_x = min(candidate["x"] + candidate["width"], text_element["x"] + text_element["width"]) - max(
                candidate["x"], text_element["x"]
            )
            overlap_y = min(candidate["y"] + candidate["height"], text_element["y"] + text_element["height"]) - max(
                candidate["y"], text_element["y"]
            )
            if overlap_x <= 0 and candidate["width"] < text_element["width"]:
                return 0
            if overlap_y <= 0 and candidate["height"] < text_element["height"]:
                return 0
        expanded = {
            "x": candidate["x"] - adjacency_tolerance,
            "y": candidate["y"] - adjacency_tolerance,
            "width": candidate["width"] + 2 * adjacency_tolerance,
            "height": candidate["height"] + 2 * adjacency_tolerance,
        }
        return intersection_area(expanded, text_element)

    overlapping = [candidate for candidate in candidates if contact_score(candidate) > 0]
    if not overlapping:
        return None
    specific = [
        candidate
        for candidate in overlapping
        if not is_canvas_sized_background_shape(candidate, slide_width, slide_height)
    ]
    pool = specific or overlapping
    # When containers nest (a card sits inside a panel), the outer shape overlaps the text at least as
    # much as the inner one, so raw max-area ownership would pick the panel and miss the card the text
    # actually sits in. Drop any candidate that fully contains another candidate so only the innermost
    # containers remain, then fall back to max intersection area to break ties between siblings.
    innermost = [
        candidate
        for candidate in pool
        if not any(other is not candidate and contains(candidate, other) for other in pool)
    ]
    pool = innermost or pool
    return max(pool, key=contact_score)


def detect_text_container_overflow(
    elements: list[dict[str, Any]], slide_width: int | float = 960, slide_height: int | float = 540
) -> list[dict[str, Any]]:
    """Flag text whose authored box crosses the background shape acting as its container.

    A non-text shape drawn behind a text run (lower z-order) that overlaps it is a candidate
    background container -- a card, pill, or panel. Each text is owned by the candidate its authored
    text box overlaps most; when sibling cards partially overlap, this picks the card the text
    actually sits in rather than a neighbour that merely clips its tail. We report when that text box
    intersects but is not fully contained by the owning container. Ghost/decorative text is ignored,
    and text whose authored box fits entirely inside its owner produces nothing.
    """
    issues: list[dict[str, Any]] = []
    containers = [
        element
        for element in elements
        if element["kind"] == "shape"
        and not is_text_element(element)
        and is_visually_rendered(element)
        and not is_line_like_shape(element)
    ]
    for text_element in elements:
        if not is_text_element(text_element) or not has_text_content(text_element):
            continue
        if is_ghost_text(text_element) or is_decorative_text(text_element):
            continue
        # Own the text to the most specific behind-in-z-order shape its authored box overlaps. This
        # deliberately uses the text frame instead of the estimated glyph box: when a vertically-centered
        # single line sits at the bottom of a card, the glyph box can fall entirely outside the card even
        # though the frame still crosses the card border.
        candidates = [c for c in containers if is_drawn_behind(c, text_element)]
        owner = choose_text_container_owner(
            candidates,
            text_element,
            slide_width,
            slide_height,
            adjacency_tolerance=CONTAINER_EDGE_ADJACENCY_TOLERANCE,
        )
        if owner is None:
            continue
        overflow = {
            "left": round(max(owner["x"] - text_element["x"], 0), 3),
            "top": round(max(owner["y"] - text_element["y"], 0), 3),
            "right": round(
                max((text_element["x"] + text_element["width"]) - (owner["x"] + owner["width"]), 0), 3
            ),
            "bottom": round(
                max((text_element["y"] + text_element["height"]) - (owner["y"] + owner["height"]), 0), 3
            ),
        }
        if not any(value > 0 for value in overflow.values()):
            continue
        issues.append({
            "level": "error",
            "code": "text_overflows_container",
            "elements": [element_ref(text_element), element_ref(owner)],
            "overflow": overflow,
            "message": (
                f"text shape {element_label(text_element)} overflows its background container "
                f"{element_label(owner)}"
            ),
            "hint": "Enlarge the container shape, shrink the text, or reduce the text so the glyphs stay inside the box.",
        })
    return issues


def detect_shape_text_occlusions(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag a visible filled shape painted over a sibling text glyph box.

    A background container is harmless when it is behind the text it owns. A filled shape that
    paints after a text run is different: it can cover a foreign label, even when both shapes are
    otherwise valid cards. Report this as bbox_overlap on the occluding shape/text pair rather than
    the rectangle-rectangle intersection, so intentional card stacking remains allowed.
    """
    issues: list[dict[str, Any]] = []
    covering_shapes = [
        element
        for element in elements
        if element["kind"] == "shape"
        and not is_text_element(element)
        and not is_line_like_shape(element)
        and is_visually_rendered(element)
        and isinstance(element.get("fillAlpha"), (int, float))
        and element["alpha"] * element["fillAlpha"] >= SHAPE_FILL_MIN_VISIBLE_ALPHA
    ]
    text_elements = [
        element
        for element in elements
        if is_text_element(element)
        and has_text_content(element)
        and not is_ghost_text(element)
        and not is_decorative_text(element)
    ]
    for shape in covering_shapes:
        for text_element in text_elements:
            if not is_drawn_in_front_of(shape, text_element):
                continue
            glyph = estimate_text_visual_bbox(text_element)
            if glyph is None:
                continue
            # The glyph box is already rotated into canvas space, so the covering shape must be too:
            # a shape authored beside the text but rotated 90 sweeps its footprint across the glyphs,
            # and comparing its unrotated bbox would miss that occlusion entirely.
            shape_bbox = rotate_bbox_around_element_center(
                {key: shape[key] for key in ("x", "y", "width", "height")}, shape
            )
            overlap_area = intersection_area(shape_bbox, glyph)
            if overlap_area < SHAPE_TEXT_OCCLUSION_MIN_AREA:
                continue
            issues.append({
                "level": "error",
                "code": "bbox_overlap",
                "elements": [element_ref(shape), element_ref(text_element)],
                "measurement": {
                    "intersection_area": round(overlap_area, 3),
                    "fill_alpha": round(shape["alpha"] * shape["fillAlpha"], 3),
                },
                "message": f"shape {element_label(shape)} covers text {element_label(text_element)}",
                "hint": "Move the filled shape behind the text or move the text outside the shape's visual area.",
            })
    return issues


def detect_shape_container_overlaps(
    elements: list[dict[str, Any]], slide_width: int | float = 960, slide_height: int | float = 540
) -> list[dict[str, Any]]:
    """Flag neighboring card backgrounds that overlap each other.

    This is narrower than generic shape-shape geometry: a shape participates only when it is a
    visible filled non-text card, and at least one side is the inferred background owner of a text
    shape. If the front card already covers the back card's text, detect_shape_text_occlusions reports
    that more actionable text occlusion, so this rule skips that duplicate.
    """
    containers = [
        element
        for element in elements
        if element["kind"] == "shape"
        and not is_text_element(element)
        and not is_line_like_shape(element)
        and is_visually_rendered(element)
        and isinstance(element.get("fillAlpha"), (int, float))
    ]
    owned_texts: dict[str, list[dict[str, Any]]] = {
        element_ref(container): [] for container in containers
    }
    text_elements = [
        element
        for element in elements
        if is_text_element(element)
        and has_text_content(element)
        and not is_ghost_text(element)
        and not is_decorative_text(element)
    ]
    for text_element in text_elements:
        candidates = [container for container in containers if is_drawn_behind(container, text_element)]
        owner = choose_text_container_owner(candidates, text_element, slide_width, slide_height)
        if owner is not None:
            owned_texts[element_ref(owner)].append(text_element)

    issues: list[dict[str, Any]] = []
    for index, left in enumerate(containers):
        for right in containers[index + 1 :]:
            overlap_area = intersection_area(left, right)
            if overlap_area < SHAPE_CONTAINER_OVERLAP_MIN_AREA:
                continue
            if contains(left, right) or contains(right, left):
                continue
            if not owned_texts[element_ref(left)] and not owned_texts[element_ref(right)]:
                continue
            front, back = (right, left) if is_drawn_in_front_of(right, left) else (left, right)
            front_covers_back_text = any(
                intersection_area(front, text_element) >= SHAPE_TEXT_OCCLUSION_MIN_AREA
                for text_element in owned_texts[element_ref(back)]
            )
            if front_covers_back_text:
                continue
            issues.append({
                "level": "error",
                "code": "bbox_overlap",
                "elements": [element_ref(left), element_ref(right)],
                "measurement": {
                    "intersection_area": round(overlap_area, 3),
                    "left_fill_alpha": round(left["alpha"] * left["fillAlpha"], 3),
                    "right_fill_alpha": round(right["alpha"] * right["fillAlpha"], 3),
                },
                "message": f"shape {element_label(left)} overlaps shape {element_label(right)}",
                "hint": "Move or resize the card background shapes so adjacent cards no longer overlap.",
            })
    return issues


def is_full_canvas_background_image(
    image: dict[str, Any], slide_width: int | float, slide_height: int | float
) -> bool:
    """True for a full-bleed image drawn behind the content as the slide backdrop.

    A background photo/gradient that fills the canvas sits under every text run by design, so text
    rendered on top of it is never occluded (slides p9: bBo covers 0,0..960,540 at the bottom of the
    z-order). We treat an image as a backdrop when it covers essentially the whole canvas; z-order is
    checked per text pair at the call site so a full-canvas image sitting *above* a text run is still
    reported.
    """
    canvas_area = slide_width * slide_height
    if canvas_area <= 0:
        return False
    canvas = {"x": 0, "y": 0, "width": slide_width, "height": slide_height}
    covered = intersection_area(image, canvas)
    return covered / canvas_area >= FULL_CANVAS_BACKGROUND_COVERAGE_RATIO


def image_encloses_text_glyphs(image: dict[str, Any], glyph_bbox: dict[str, Any]) -> bool:
    """True when the image contains essentially all of the text's glyph box.

    A partial-bleed image drawn behind a text run acts as that run's local background when it tucks
    nearly the whole glyph box underneath it -- the glyphs paint on top, so the image cannot occlude
    them. We measure the glyph box against the image (not the canvas) so a local backdrop is exempt
    while an image that merely clips part of a run stays reported (glyphs spilling past the image edge
    drop the enclosed fraction below the threshold).
    """
    glyph_area = element_area(glyph_bbox)
    if glyph_area <= 0:
        return False
    return intersection_area(image, glyph_bbox) / glyph_area >= BACKGROUND_IMAGE_TEXT_ENCLOSURE_RATIO


def detect_image_text_occlusions(
    elements: list[dict[str, Any]], slide_width: int | float = 960, slide_height: int | float = 540
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    text_elements = [
        element
        for element in elements
        if is_text_element(element) and has_text_content(element) and not is_ghost_text(element)
    ]
    image_elements = [element for element in elements if element["kind"] == "img" and element["alpha"] > 0]
    for text_element in text_elements:
        for image_element in image_elements:
            # A full-canvas image drawn behind the text is the slide backdrop, not an occluder; text on
            # top of it renders cleanly (slides p9). An image that fills the canvas but sits *above* the
            # text still occludes, so this only exempts the behind-in-z-order case.
            if is_drawn_behind(image_element, text_element) and is_full_canvas_background_image(
                image_element, slide_width, slide_height
            ):
                continue
            if is_vertical_text(text_element):
                if intersects(image_element, text_element):
                    issues.append({
                        "level": "info",
                        "code": "image_may_cover_vertical_text",
                        "elements": [element_ref(image_element), element_ref(text_element)],
                        "message": (
                            f"image {element_label(image_element)} may cover vertical text shape "
                            f"{element_label(text_element)}"
                        ),
                        "hint": "Inspect the rendered slide because vertical text layout is not statically modeled.",
                    })
                continue
            text_visual_bbox = estimate_text_visual_bbox(text_element)
            if text_visual_bbox is not None and intersects(image_element, text_visual_bbox):
                # An image behind the text that encloses nearly all of its glyph box is that run's local
                # background, not an occluder -- the glyphs paint on top of it (slides
                # LuwIs0LQXlmCm0d2XTHcHxeCnfd). An image drawn *above* the text, or one that only clips
                # part of the glyph box, is not exempt.
                if is_drawn_behind(image_element, text_element) and image_encloses_text_glyphs(
                    image_element, text_visual_bbox
                ):
                    continue
                issues.append({
                    "level": "error",
                    "code": "image_covers_text",
                    "elements": [element_ref(image_element), element_ref(text_element)],
                    "message": (
                        f"image {element_label(image_element)} covers text shape "
                        f"{element_label(text_element)}"
                    ),
                    "hint": "Adjust the image and text shape coordinates or dimensions so the image no longer overlaps the text glyph area.",
                })
    return issues


def is_decorative_text(element: dict[str, Any]) -> bool:
    text = element.get("text") or ""
    return bool(text) and re.search(r"[A-Za-z0-9\u4e00-\u9fff]", text) is None


def normalize_text_for_overlap(text: str) -> str:
    return re.sub(r"\s+", "", text)


SERIF_FONT_PATTERNS = {
    "song", "songti", "simsun", "ming", "mincho",
    "georgia", "times", "caslon", "garamond", "sourcehan-serif",
    "source han serif", "思源宋体", "宋体", "明体",
}

SANS_EXPLICIT_MARKERS = {"sans", "sans-serif", "sans serif", "sourcehan-sans", "source han sans", "思源黑体", "黑体",
                         "helvetica", "arial", "inter", "roboto", "verdana", "tahoma", "calibri", "open sans"}

# Geometric/wide sans-serif families advance noticeably wider than the humanist sans baseline: a digit or
# lowercase glyph in Montserrat/Poppins/Futura is ~0.62-0.66em, not the ~0.51-0.58em the generic sans
# coefficients assume. Measuring them with the narrow baseline under-reports a run's ink extent, so a
# big-type token can collide with its neighbour while the estimated glyph boxes still show a gap (slides
# p19: the 60px bold Montserrat "48h" ink reaches x179 and touches "即做即售"/"当日鲜制", but the narrow
# estimate stops at x165 and the overlap is scored as 0). Give these families their own wider tier.
WIDE_SANS_FONT_MARKERS = {"montserrat", "poppins", "futura", "century gothic", "gotham", "raleway",
                          "nunito", "quicksand", "josefin", "comfortaa"}


def classify_font_family(font_family: str | None) -> str:
    if not font_family:
        return "sans"
    family_lower = font_family.lower()
    for marker in WIDE_SANS_FONT_MARKERS:
        if marker in family_lower:
            return "wide-sans"
    for marker in SANS_EXPLICIT_MARKERS:
        if marker in family_lower:
            return "sans"
    serif_keywords = SERIF_FONT_PATTERNS | {"serif"}
    for pattern in serif_keywords:
        if pattern in family_lower:
            return "serif"
    return "sans"


_FONT_CATEGORY_MULTIPLIERS: dict[str, dict[str, float]] = {
    "sans": {"upper": 0.57, "lower": 0.51, "digit": 0.58, "punct": 0.50},
    "serif": {"upper": 0.57, "lower": 0.53, "digit": 0.58, "punct": 0.50},
    "wide-sans": {"upper": 0.62, "lower": 0.58, "digit": 0.63, "punct": 0.53},
}


def estimate_character_width(
    character: str,
    font_size: int | float,
    bold: bool = False,
    font_family: str | None = None,
    east_asian_context: bool = False,
) -> int | float:
    bold_multiplier = 1.05 if bold else 1.0
    if character.isspace():
        return font_size * 0.33 * bold_multiplier
    ea_width = unicodedata.east_asian_width(character)
    # Ambiguous-width glyphs (em/en-dash, middle-dot, ellipsis) render full-width inside a CJK run and
    # half-width in a Latin run (UAX #11). Measuring "—— 李白" with narrow dashes under-reports the line
    # and hides a real wrap in a tight author-credit box (slides p1: bMW). Promote them to full-width
    # only when the surrounding run has East Asian context so "2020–2023" stays narrow.
    if ea_width in {"F", "W"} or (ea_width == "A" and east_asian_context):
        return font_size * bold_multiplier
    # "%" is half-width by Unicode class (Na) but renders nearly full-width (~0.85em in Arial/PingFang):
    # the generic punct coefficient under-measures every percentage metric, so a "Docs 99%Docs 99%..."
    # run wraps to more lines than estimated and its overflow is missed (slides p3: bhU). A handful of
    # other common symbols (@ & $ ¥ £ # + = < > ~) share this under-measurement, so they carry their own
    # per-glyph advance instead of the generic punct coefficient (see WIDE_SYMBOL_WIDTH_RATIOS).
    if character == "%":
        return font_size * PERCENT_SIGN_WIDTH_RATIO * bold_multiplier
    wide_ratio = WIDE_SYMBOL_WIDTH_RATIOS.get(character)
    if wide_ratio is not None:
        return font_size * wide_ratio * bold_multiplier
    category = classify_font_family(font_family)
    coeffs = _FONT_CATEGORY_MULTIPLIERS[category]
    # The widest Latin letters take a per-glyph advance instead of the category average, but only when
    # it is wider (the wide-sans tier already advances its glyphs generously), so this override can only
    # raise the estimate -- see WIDE_LETTER_WIDTH_RATIOS.
    wide_letter_ratio = WIDE_LETTER_WIDTH_RATIOS.get(character)
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


def estimate_text_width(
    text: str,
    font_size: int | float,
    letter_spacing: int | float = 0,
    bold: bool = False,
    font_family: str | None = None,
    east_asian_context: bool | None = None,
) -> int | float:
    # A run counts as East Asian context when it contains any CJK-like glyph; in that setting ambiguous
    # dashes/dots render full-width. Callers measuring a single wrap token (count_wrapped_lines) pass the
    # whole-line context explicitly so a lone dash token is still measured as full-width.
    if east_asian_context is None:
        east_asian_context = any(is_cjk_char(character) for character in text)
    base = sum(
        estimate_character_width(character, font_size, bold, font_family, east_asian_context)
        for character in text
    )
    return base + max(len(text) - 1, 0) * letter_spacing


def is_cjk_char(character: str) -> bool:
    """CJK-like characters may wrap between any two adjacent glyphs.

    Mirrors the isCJKLike ranges used by ee/slide text-measure-module so that
    line-count estimation matches DOM/Skia wrapping: CJK breaks per glyph while
    latin words stay atomic.
    """
    code = ord(character)
    return (
        0x2E80 <= code <= 0x9FFF
        or 0x3000 <= code <= 0xD7AF
        or 0xF900 <= code <= 0xFAFF
        or 0xFE30 <= code <= 0xFE4F
        or 0xFF01 <= code <= 0xFF60
        or 0xFFE0 <= code <= 0xFFE6
    )


def tokenize_for_wrap(text: str) -> list[tuple[str, str]]:
    """Split a hard line into wrap tokens: latin words are atomic, CJK glyphs
    are individually breakable, whitespace runs are collapse points."""
    tokens: list[tuple[str, str]] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character.isspace():
            start = index
            while index < length and text[index].isspace():
                index += 1
            tokens.append(("space", text[start:index]))
        elif is_cjk_char(character):
            tokens.append(("cjk", character))
            index += 1
        else:
            start = index
            while index < length and not text[index].isspace() and not is_cjk_char(text[index]):
                index += 1
            tokens.append(("word", text[start:index]))
    return tokens


def count_wrapped_lines(
    text: str,
    font_size: int | float,
    letter_spacing: int | float,
    bold: bool,
    font_family: str | None,
    available_width: int | float,
) -> int:
    """Greedy word-aware wrapped line count.

    Unlike ceil(width / available), latin words are never split mid-word (unless
    a single word is wider than the line, in which case it breaks like DOM
    overflow-wrap:break-word). This avoids under-counting lines for word-heavy
    text and matches how ee/slide reconciles Skia wrapping with the DOM.
    """
    tokens = tokenize_for_wrap(text)
    if not tokens:
        return 1
    lines = 1
    current = 0.0
    # Ambiguous glyphs render full-width in a CJK line; decide context from the whole line, not the lone
    # token, so a dash token split off from "—— 李白" is still measured full-width (matches Skia wrapping).
    east_asian_context = any(is_cjk_char(character) for character in text)

    def token_width(token: str) -> int | float:
        return estimate_text_width(token, font_size, letter_spacing, bold, font_family, east_asian_context)

    for kind, token in tokens:
        width = token_width(token)
        # letter-spacing applies at every glyph boundary, including the seam
        # between two tokens on the same line; add it back so a packed line
        # matches estimate_text_width of the concatenated run.
        junction = letter_spacing if current > 0 else 0
        if kind == "space":
            if current > 0:
                current += junction + width
            continue
        if current > 0 and current + junction + width <= available_width:
            current += junction + width
            continue
        if current > 0:
            lines += 1
        if kind == "word" and width > available_width:
            extra = math.ceil(width / available_width) - 1
            lines += extra
            current = width - extra * available_width
        else:
            current = width
    return lines


def resolve_letter_spacing(element: dict[str, Any], paragraph: dict[str, Any] | None = None) -> int | float:
    if paragraph is not None:
        value = paragraph.get("letterSpacing")
        if isinstance(value, (int, float)):
            return value
    value = element.get("letterSpacing")
    return value if isinstance(value, (int, float)) else 0


def text_wrap_width_tolerance() -> int | float:
    return TEXT_WRAP_WIDTH_TOLERANCE_PX


def text_height_overflow_tolerance() -> int | float:
    return TEXT_HEIGHT_OVERFLOW_TOLERANCE_PX


def has_explicit_height_auto_fit(element: dict[str, Any]) -> bool:
    return element.get("autoFit") in {"normal-auto-fit", "shape-auto-fit"}


def is_single_line_visual_candidate(
    element: dict[str, Any],
    paragraph: dict[str, Any] | None,
    text: str,
    logical_width: int | float,
    effective_width: int | float,
) -> bool:
    if "\n" in text or logical_width <= effective_width:
        return False
    text_align = (paragraph or {}).get("textAlign") or element.get("textAlign")
    compact_len = len(re.sub(r"\s+", "", text))
    if text_align == "center" and compact_len <= 32:
        return logical_width <= effective_width * CENTERED_SHORT_LABEL_WIDTH_RATIO

    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    if element.get("textType") in {"headline", "title"} and font_size <= 30 and compact_len <= 40:
        return logical_width <= effective_width * HEADLINE_NEAR_FIT_WIDTH_RATIO
    return False


def estimate_text_max_line_width(element: dict[str, Any]) -> int | float:
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    bold = element.get("bold", False)
    font_family = element.get("fontFamily", "")
    letter_spacing = resolve_letter_spacing(element)
    # Visual width ignores trailing whitespace: like Skia (which trims line-end
    # spaces), a run's rightmost visible glyph bounds the box. Counting trailing
    # spaces inflates the right edge and manufactures overlap false positives.
    paragraphs = [
        stripped for paragraph in re.split(r"\n+", element["text"]) if (stripped := paragraph.rstrip())
    ]
    return max(
        [estimate_text_width(paragraph, font_size, letter_spacing, bold, font_family) for paragraph in paragraphs]
        or [1]
    )


def is_similar_text_overlay(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """True for a shadow/duplicate text stack that is meant to sit on top of itself.

    Repeated text is only an intentional overlay when the two runs are nearly coincident -- e.g. a
    drop-shadow copy offset by a pixel or two. Two distinct labels that happen to carry the same text
    but sit at different positions (slides p6: identical "文字碰撞" runs collided by rotation) are a
    real overlap, so we require both a text match AND near-coincident glyph boxes before suppressing.
    """
    left_text = normalize_text_for_overlap(left.get("text") or "")
    right_text = normalize_text_for_overlap(right.get("text") or "")
    if not left_text or not right_text:
        return False
    text_matches = (
        left_text == right_text
        or left_text in right_text
        or right_text in left_text
        or SequenceMatcher(None, left_text, right_text).ratio() >= 0.75
    )
    if not text_matches:
        return False
    left_visual = estimate_text_visual_bbox(left)
    right_visual = estimate_text_visual_bbox(right)
    if left_visual is None or right_visual is None:
        return True
    overlap = intersection_area(left_visual, right_visual)
    smaller_area = min(
        left_visual["width"] * left_visual["height"],
        right_visual["width"] * right_visual["height"],
    )
    # A genuine shadow/duplicate overlay is almost fully coincident; a mere text coincidence between
    # two separately-placed labels leaves a large non-overlapping remainder and must not be suppressed.
    return smaller_area > 0 and overlap / smaller_area >= SIMILAR_OVERLAY_COINCIDENCE_RATIO


def estimate_text_line_count_for_text(
    element: dict[str, Any], text: str, paragraph: dict[str, Any] | None = None
) -> int:
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    bold = element.get("bold", False)
    font_family = element.get("fontFamily", "")
    letter_spacing = resolve_letter_spacing(element, paragraph)
    available_width = max(element["width"] - element.get("paddingLeft", 0) - element.get("paddingRight", 0), 1)
    hard_lines = text.split("\n")
    if not text:
        return 0
    line_count = 0
    for hard_line in hard_lines:
        if element.get("wrap") in {"false", "0"}:
            line_count += 1
            continue
        logical_width = max(estimate_text_width(hard_line, font_size, letter_spacing, bold, font_family), 1)
        effective_width = available_width + text_wrap_width_tolerance()
        if is_single_line_visual_candidate(element, paragraph, hard_line, logical_width, effective_width):
            line_count += 1
            continue
        line_count += count_wrapped_lines(
            hard_line, font_size, letter_spacing, bold, font_family, effective_width
        )
    return line_count


def estimate_text_line_count(element: dict[str, Any]) -> int:
    return max(estimate_text_line_count_for_text(element, element["text"]), 1)


def estimate_text_line_height(element: dict[str, Any], line_spacing: str | None = None) -> int | float | None:
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    if line_spacing is None:
        return font_size * DEFAULT_TEXT_LINE_SPACING_MULTIPLE
    match = re.fullmatch(r"(multiple|fixed):([0-9]+(?:\.[0-9]+)?)", line_spacing)
    if match is None:
        return None
    spacing_type, value = match.groups()
    return font_size * float(value) if spacing_type == "multiple" else float(value)


def adjust_dense_body_line_height(
    element: dict[str, Any],
    line_spacing: str | None,
    line_height: int | float,
    paragraph_count: int,
) -> int | float:
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    if paragraph_count < 4 or font_size > 14 or not line_spacing:
        return line_height
    match = re.fullmatch(r"multiple:([0-9]+(?:\.[0-9]+)?)", line_spacing)
    if match is None:
        return line_height
    authored_multiple = float(match.group(1))
    realised_multiple = max(
        authored_multiple * DENSE_BODY_LINE_SPACING_COMPRESSION, DENSE_BODY_LINE_SPACING_MAX_MULTIPLE
    )
    return min(line_height, font_size * min(realised_multiple, authored_multiple))


def estimate_text_block_height(element: dict[str, Any]) -> dict[str, Any] | None:
    """Estimate the rendered height of a text run using its real line spacing.

    Returns ``{"line_count", "estimated_height", "line_heights"}`` or ``None`` when the
    line spacing cannot be parsed. Shared by the height-overflow check and the visual
    glyph-box estimator so both honour ``lineSpacing`` (multiple/fixed, per-paragraph
    overrides) instead of a flat ``font_size * 1.2`` -- the latter under-reports multi-line
    poems and let <line> crossings escape (slides p8/p10).
    """
    if not is_text_element(element) or not has_text_content(element):
        return None
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    paragraphs = element.get("paragraphs") or [
        {
            "text": element["text"],
            "lineSpacing": None,
            "beforeLineSpacing": None,
            "afterLineSpacing": None,
        }
    ]
    line_count = 0
    estimated_height = 0.0
    line_heights: list[int | float] = []
    for paragraph in paragraphs:
        paragraph_line_count = estimate_text_line_count_for_text(element, paragraph["text"], paragraph)
        if paragraph_line_count == 0:
            continue
        resolved_line_spacing = paragraph["lineSpacing"] or element["lineSpacing"]
        line_height = estimate_text_line_height(element, resolved_line_spacing)
        before_spacing = estimate_text_line_height(
            element, paragraph["beforeLineSpacing"] or element["beforeLineSpacing"] or "fixed:0"
        )
        after_spacing = estimate_text_line_height(
            element, paragraph["afterLineSpacing"] or element["afterLineSpacing"] or "fixed:0"
        )
        if line_height is None or before_spacing is None or after_spacing is None:
            return None
        line_height = adjust_dense_body_line_height(element, resolved_line_spacing, line_height, len(paragraphs))
        first_line_height = font_size if line_count == 0 else line_height
        line_count += paragraph_line_count
        line_heights.append(line_height)
        estimated_height += (
            before_spacing + first_line_height + max(paragraph_line_count - 1, 0) * line_height + after_spacing
        )
    if line_count == 0:
        return None
    return {
        "line_count": line_count,
        "estimated_height": estimated_height,
        "line_heights": line_heights,
    }


def short_line_passive_wrap_width(
    element: dict[str, Any], block: dict[str, Any]
) -> dict[str, int | float] | None:
    """Return width metrics when a short single-line label overflows vertically only because it is
    too wide to fit on one line and was passively wrapped.

    A big-number/label run like "60%+" has no hard line break and is meant to stay on one line. When
    its box is narrower than the line, the renderer wraps it (wrap defaults to true), which inflates
    the block height and trips the vertical check. The real defect is width, not height: raising
    shape.height or setting wrap="true" (already the default) will not un-wrap it -- only widening the
    box or shrinking the font restores the single line. Return None for genuine height overflows
    (multi-paragraph prose, or a single line that already fits the width) so they keep the height hint.
    """
    # Vertical text stacks glyphs down a column, so horizontal advance width says nothing about
    # whether it fits -- its overflow is genuinely on the height axis. Mirror the guard in
    # detect_text_may_wrap_shapes so a vertical run is never reclassified to overflow_axis "width"
    # or handed a shape-width remediation hint.
    if is_vertical_text(element):
        return None
    if element.get("wrap") in {"false", "0"}:
        return None
    # Multi-hard-line text is authored to occupy several lines; its height overflow is genuine.
    if "\n" in element["text"]:
        return None
    # Prose is expected to wrap; this reclassification only targets short labels/metrics that were
    # meant to stay on one line, mirroring detect_text_may_wrap_shapes' SHORT_LABEL_WRAP_MAX_CHARS gate.
    # Titles/headlines are authored for one line regardless of length, so their passive wrap is a width
    # defect too: raising shape.height just leaves two overlapping lines, and the fix is to widen the
    # box or shrink the font. They therefore bypass the short-label char cap (slides: a long section
    # title wrapped and was wrongly told to increase its height).
    is_title_like = element.get("textType") in {"title", "headline", "sub-headline"}
    if not is_title_like and len(re.sub(r"\s+", "", element["text"])) > SHORT_LABEL_WRAP_MAX_CHARS:
        return None
    # It only counts as passive wrapping if the single logical line actually wrapped.
    if block["line_count"] < 2:
        return None
    raw_line = (element.get("text_raw") or element["text"]).rstrip()
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    # A passive-wrap candidate has no hard break, so it is a single paragraph; honour that paragraph's
    # letterSpacing (it may be set on the <p>, not the <content>) so per-paragraph spacing still counts.
    paragraphs = element.get("paragraphs") or []
    paragraph = paragraphs[0] if len(paragraphs) == 1 else None
    visual_width = max(
        estimate_text_width(
            raw_line, font_size, resolve_letter_spacing(element, paragraph), element.get("bold", False),
            element.get("fontFamily", ""),
        ),
        1,
    )
    available_width = max(element["width"] - element.get("paddingLeft", 0) - element.get("paddingRight", 0), 1)
    # The line must genuinely exceed the box (beyond the sub-pixel tolerance) for width to be the cause;
    # otherwise it wrapped for some other reason and the height hint still applies.
    if visual_width <= available_width + text_wrap_width_tolerance():
        return None
    return {
        "estimated_width": visual_width,
        "available_width": available_width,
        "width_ratio": visual_width / available_width,
    }


def detect_text_may_overflow_shapes(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for element in elements:
        if not is_text_element(element) or not has_text_content(element):
            continue
        if has_explicit_height_auto_fit(element):
            continue

        block = estimate_text_block_height(element)
        if block is None:
            continue
        line_count = block["line_count"]
        estimated_height = block["estimated_height"]
        line_heights = block["line_heights"]
        available_height = max(element["height"] - element["paddingTop"] - element["paddingBottom"], 0)
        overflow = estimated_height - available_height
        if overflow <= text_height_overflow_tolerance():
            continue

        is_background = is_background_decorative_text(element, elements)
        # Any real vertical overflow past the sub-pixel tolerance is an error, matching the
        # width-axis check (detect_text_may_wrap_shapes reports errors unconditionally). The old
        # <=10px "warning" band under-reported genuine half-line overflows (e.g. fixed:20 x3 lines
        # in a 50px box); the 0.5px tolerance above already absorbs rotated-bbox rounding noise.
        if is_background:
            level = "info"
        else:
            level = "error"

        # A short single-line label ("60%+") only overflows vertically because it was too wide to fit
        # one line and got passively wrapped. wrap defaults to true, so "set wrap=true" is a no-op and
        # raising height just leaves the ugly wrap in place -- the fix is to widen the box or shrink the
        # font. Report this as a width defect (not height) so the hint is actionable. Background
        # decoration keeps the height path, which already downgrades it to info.
        passive_wrap = None if is_background else short_line_passive_wrap_width(element, block)
        if passive_wrap is not None:
            visual_width = passive_wrap["estimated_width"]
            available_width = passive_wrap["available_width"]
            issues.append(
                {
                    "level": "error",
                    "code": "text_may_overflow_shape",
                    "overflow_axis": "width",
                    "elements": [element_ref(element)],
                    "estimated_width": visual_width,
                    "available_width": available_width,
                    "width_ratio": passive_wrap["width_ratio"],
                    "message": (
                        f"text shape {element_label(element)} may overflow its own content box "
                        f'(estimated line {visual_width:g}px, available {available_width:g}px); the single '
                        'line is too wide and wrapped, inflating its height -- widen the shape or reduce the '
                        'font size to keep it on one line'
                    ),
                    "hint": (
                        "The run has no hard line break and is meant to stay on one line, but its box is "
                        "too narrow so it wrapped. wrap defaults to true, so setting wrap=\"true\" or raising "
                        "shape.height will not un-wrap it; widen shape.width or reduce the font size instead. "
                        "This is an estimate based on font size, weight, and glyph widths."
                    ),
                }
            )
            continue

        message = (
            f"text shape {element_label(element)} may overflow its own content box "
            f'(estimated {estimated_height:g}px, available {available_height:g}px); '
            'consider setting content wrap="true" autoFit="normal-auto-fit"'
        )
        if is_background:
            message += " (likely background decoration: large font, low alpha, underneath other text)"
        issues.append(
            {
                "level": level,
                "code": "text_may_overflow_shape",
                "elements": [element_ref(element)],
                "overflow_axis": "height",
                "line_count": line_count,
                "line_height": max(line_heights),
                "estimated_height": estimated_height,
                "available_height": available_height,
                "overflow": overflow,
                "message": message,
                "hint": (
                    "Increase shape.height, reduce the text, or set content wrap=\"true\" "
                    "autoFit=\"normal-auto-fit\" (autoFit shrinks the font to fit; wrap is already "
                    "the default). This is an estimate based on font size, line spacing, and wrapped "
                    "line count."
                ),
            }
        )
    return issues


def detect_wrap_false_width_overflow(
    element: dict[str, Any], elements: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Report a wrap="false" text run whose widest hard line overruns its content box.

    wrap="false" text cannot reflow, so it does not "wrap" -- it is clipped or spills past the box
    edge. That is a definite overflow, so unlike detect_text_may_wrap_shapes (which guards against
    unexpected wrapping with label/metric heuristics), this measures the exact widest hard line and
    flags any excess beyond a sub-pixel tolerance, for any script or text length.
    """
    raw_text = element.get("text_raw") or element["text"]
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    letter_spacing = resolve_letter_spacing(element)
    bold = element.get("bold", False)
    font_family = element.get("fontFamily", "")
    # Trailing spaces are trimmed by the renderer (like Skia); measure each hard line's visible width
    # and keep the widest, since wrap="false" leaves every hard line on its own single physical line.
    visual_width = max(
        [
            estimate_text_width(hard_line.rstrip(), font_size, letter_spacing, bold, font_family)
            for hard_line in raw_text.split("\n")
        ]
        or [1]
    )
    visual_width = max(visual_width, 1)
    available_width = max(element["width"] - element.get("paddingLeft", 0) - element.get("paddingRight", 0), 1)
    effective_width = available_width + text_wrap_width_tolerance()
    if visual_width <= effective_width:
        return None

    ratio = visual_width / available_width
    # Large low-alpha text sitting behind other content is intentional background decoration; the
    # height-axis check downgrades it to info via is_background_decorative_text, and the width axis
    # mirrors that so a decorative ghost number is not reported as an error on either axis.
    is_background = is_background_decorative_text(element, elements)
    message = (
        f"text shape {element_label(element)} may overflow its own content box "
        f'(estimated line {visual_width:g}px, available {available_width:g}px); '
        'the run has wrap="false" and cannot reflow, so widen the shape or shorten the text'
    )
    if is_background:
        message += " (likely background decoration: large font, low alpha, underneath other text)"
    return {
        "level": "info" if is_background else "error",
        # Shares the text_may_overflow_shape code with the vertical/wrap checks: to the user this is
        # one concept ("text may overflow its box"). overflow_axis distinguishes them for tooling.
        "code": "text_may_overflow_shape",
        "overflow_axis": "width",
        "elements": [element_ref(element)],
        "estimated_width": visual_width,
        "available_width": available_width,
        "width_ratio": ratio,
        "message": message,
        "hint": (
            "Increase shape.width or shorten the text. wrap=\"false\" text cannot reflow, so a line "
            "wider than the box is clipped or spills past its edge. This is an estimate based on font "
            "size, weight, and glyph widths."
        ),
    }


def detect_text_may_wrap_shapes(
    elements: list[dict[str, Any]], already_flagged_refs: set[str] | None = None
) -> list[dict[str, Any]]:
    """Flag single-line text runs whose width is likely to wrap inside their own box.

    Complements detect_text_may_overflow_shapes, which only measures the vertical axis.
    A run can fit vertically (or carry autoFit) yet still wrap because the box is too
    narrow -- the exact false-negative these slides hit. Width estimation is independent
    of autoFit (shape-auto-fit only grows height, not width), so this check ignores it.
    already_flagged_refs are elements the vertical check already reported, identified by the same
    element_ref locator the issues carry; we skip them so a single wrapping shape is not
    double-reported under the shared text_may_overflow_shape code.
    """
    already_flagged_refs = already_flagged_refs or set()
    issues: list[dict[str, Any]] = []
    for element in elements:
        if not is_text_element(element) or not has_text_content(element):
            continue
        if element_ref(element) in already_flagged_refs:
            continue
        # Vertical text stacks glyphs down a column, so horizontal advance width says nothing about
        # whether it fits -- that axis is the box height, already measured by
        # detect_text_may_overflow_shapes. Guard before the wrap="false" branch too, otherwise a
        # vertical run with wrap="false" would be measured on the wrong axis and falsely flagged.
        if is_vertical_text(element):
            continue
        if element.get("wrap") in {"false", "0"}:
            # wrap="false" text cannot reflow, so any hard line wider than the box overflows/clips
            # its container -- an exact overflow, not a heuristic wrap risk. The short-label/metric
            # thresholds below exist to guard against unexpected wrapping and do not apply here, so
            # this run takes a dedicated exact-width path instead of being skipped outright.
            wrap_false_issue = detect_wrap_false_width_overflow(element, elements)
            if wrap_false_issue is not None:
                issues.append(wrap_false_issue)
            continue
        # Multi-hard-line text already wraps by author intent; only single logical lines
        # that were meant to stay on one line are at risk of an unexpected wrap.
        if "\n" in element["text"]:
            continue
        # Long prose is expected to wrap; this rule targets short labels/metrics
        # (e.g. "Slides 87%", "autofix 87%") that were meant to stay on one line.
        # Titles/headlines are the exception: they are authored for a single line regardless of length,
        # so a long one that passively wraps is still a defect and must be admitted past the short-label
        # cap. We scope this to {title, headline} to match the near-fit whitelist in
        # is_single_line_visual_candidate: the long-title path below relies on that near-fit calibration
        # to avoid false positives, so admitting a textType it does not protect (sub-headline) would let
        # a near-fit sub-headline that renders on one line be flagged. Short title-like runs stay on the
        # shared metric/latin/cjk threshold path below; only the newly admitted long titles take the
        # wrap-simulation path.
        is_title_like = element.get("textType") in {"title", "headline"}
        compact_len = len(re.sub(r"\s+", "", element["text"]))
        is_long_title = is_title_like and compact_len > SHORT_LABEL_WRAP_MAX_CHARS
        if not is_title_like and compact_len > SHORT_LABEL_WRAP_MAX_CHARS:
            continue

        # Measure with internal spaces preserved: Skia renders "autofix      87%" at full
        # width, but element["text"] has collapsed them, which would hide the wrap.
        raw_line = (element.get("text_raw") or element["text"]).rstrip()
        font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
        visual_width = max(
            estimate_text_width(
                raw_line, font_size, resolve_letter_spacing(element), element.get("bold", False),
                element.get("fontFamily", ""),
            ),
            1,
        )
        available_width = max(element["width"] - element.get("paddingLeft", 0) - element.get("paddingRight", 0), 1)
        effective_width = available_width + text_wrap_width_tolerance()
        if is_long_title:
            # Decide by the real wrap simulation (estimate_text_block_height), not a width-ratio band.
            # estimate_text_line_count_for_text applies is_single_line_visual_candidate first, so a title
            # whose estimated width lands within HEADLINE_NEAR_FIT_WIDTH_RATIO (~1.04) of the box is
            # treated as one line and NOT flagged -- that band absorbs the estimator's known over-report
            # on titles, so those render on one line and are not defects. Only a title that reflows to
            # >=2 lines past that near-fit band is flagged. This catches a passive title wrap regardless
            # of whether the box is tall enough to absorb the extra line (slides I9dd p25); the vertical
            # check alone would miss the tall-box case.
            block = estimate_text_block_height(element)
            if block is None or block["line_count"] < 2:
                continue
        else:
            # Latin/labeled runs ("Docs 99%", "Slides 87%") are where the width estimator under-reports,
            # so flag them from the aggressive risk band. Pure CJK breaks per glyph and is estimated
            # accurately, so it only wraps once it genuinely exceeds the box.
            if re.search(r"[A-Za-z]", raw_line):
                threshold = available_width * TEXT_WIDTH_WRAP_RISK_RATIO
            else:
                threshold = effective_width
            if visual_width <= threshold:
                continue

        ratio = visual_width / available_width
        message = (
            f"text shape {element_label(element)} may wrap inside its own content box "
            f'(estimated line {visual_width:g}px, available {available_width:g}px); '
            'widen the shape (pair with content wrap="false" to keep it on one line), or reduce the text'
        )
        issues.append(
            {
                "level": "error",
                # Shares the text_may_overflow_shape code with the vertical check: to the user this is
                # one concept ("text may overflow its box"), while the two axes stay in separate
                # functions. The overflow_axis field distinguishes them for tooling.
                "code": "text_may_overflow_shape",
                "overflow_axis": "width",
                "elements": [element_ref(element)],
                "estimated_width": visual_width,
                "available_width": available_width,
                "width_ratio": ratio,
                "message": message,
                "hint": (
                    "Increase shape.width so the whole line fits, then set content wrap=\"false\" if the "
                    "run must stay on one line -- wrap=\"false\" alone clips or spills text past a box that "
                    "is still too narrow. Alternatively shorten the text. This is an estimate based on "
                    "font size, weight, and glyph widths."
                ),
            }
        )
    return issues


def is_background_decorative_text(
    element: dict[str, Any], elements: list[dict[str, Any]]
) -> bool:
    if not is_ghost_text(element):
        return False
    for other in elements:
        if other is element:
            continue
        if not is_text_element(other) or not has_text_content(other):
            continue
        foreground_alpha = other.get("textAlpha", other.get("alpha", 1))
        if not isinstance(foreground_alpha, (int, float)) or foreground_alpha <= 0:
            continue
        if not is_drawn_in_front_of(other, element):
            continue
        if intersects(element, other):
            return True
    return False


def is_ghost_text(element: dict[str, Any]) -> bool:
    if not is_text_element(element) or not has_text_content(element):
        return False
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    text_alpha = element.get("textAlpha", element.get("alpha", 1))
    if not isinstance(text_alpha, (int, float)):
        return False
    if font_size > GHOST_TEXT_MIN_FONT_SIZE and text_alpha < GHOST_TEXT_MAX_ALPHA:
        return True
    return font_size >= GHOST_TEXT_FAINT_MIN_FONT_SIZE and text_alpha < GHOST_TEXT_FAINT_MAX_ALPHA


def estimate_text_visual_bbox(element: dict[str, Any]) -> dict[str, int | float] | None:
    if not is_text_element(element) or not has_text_content(element) or is_decorative_text(element):
        return None

    padding_left = element.get("paddingLeft", 0)
    padding_right = element.get("paddingRight", 0)
    padding_top = element.get("paddingTop", 0)
    padding_bottom = element.get("paddingBottom", 0)
    content_width = max(element["width"] - padding_left - padding_right, 0)
    content_height = max(element["height"] - padding_top - padding_bottom, 0)
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    line_count = estimate_text_line_count(element)
    estimated_width = max(1, estimate_text_max_line_width(element))
    visual_width = estimated_width if element.get("wrap") in {"false", "0"} else min(content_width, estimated_width)
    # Honour the run's real line spacing (default 1.5x) via the shared block-height estimator instead of
    # a flat font_size * 1.2. The flat factor under-reported multi-line runs by ~25%, shrinking the glyph
    # box so a genuinely touching run was pushed into a phantom vertical gap and the collision was missed
    # (slides p7). estimate_text_block_height drops the top line's leading (first_line_height = font_size),
    # which is the right conservative bias for the overflow detector but undercounts the rendered extent of
    # a vertically-centred multi-line block: the top line still carries half-leading above it, so a
    # centred block sits ~one leading taller than the tight baseline stack. Add that leading back for
    # multi-line runs, and take the larger of the block estimate and the old flat 1.2x baseline so a
    # single-line box never shrinks below the previous ink height.
    block = estimate_text_block_height(element)
    flat_height = line_count * font_size * 1.2
    if block:
        raw_height = block["estimated_height"]
        line_heights = block["line_heights"]
        if block["line_count"] > 1 and line_heights:
            raw_height += max(max(line_heights) - font_size, 0)
        raw_height = max(1, raw_height, flat_height)
    else:
        raw_height = max(1, flat_height)
    # shape-auto-fit grows the box downward to fit its text, so the rendered glyphs occupy the full
    # estimated block height even when it exceeds the authored box. Clamping to content_height here
    # would hide a grown title colliding with whatever sits below it (slides p9). Every other autoFit
    # mode keeps the authored box, so the estimate stays clamped.
    if element.get("autoFit") == "shape-auto-fit":
        visual_height = raw_height
    else:
        visual_height = min(content_height, raw_height)
    x = element["x"] + padding_left
    if element.get("textAlign") == "center":
        x += (content_width - visual_width) / 2
    elif element.get("textAlign") == "right":
        x += content_width - visual_width
    y = element["y"] + padding_top
    if element.get("verticalAlign") == "middle":
        y += (content_height - visual_height) / 2
    elif element.get("verticalAlign") == "bottom":
        y += content_height - visual_height
    return rotate_bbox_around_element_center(
        {"x": x, "y": y, "width": visual_width, "height": visual_height}, element
    )


def rotate_bbox_around_element_center(
    bbox: dict[str, int | float], element: dict[str, Any]
) -> dict[str, int | float]:
    """Return the axis-aligned bounds of bbox after the element's rotation is applied.

    Rotation spins the whole shape about its own centre, so a glyph box computed in the shape's local
    (unrotated) frame must be rotated with it before any axis-aligned overlap test. Without this, a
    text run rotated 90/270 keeps its horizontal footprint and its true vertical footprint is missed
    entirely (slides p6). We rotate the four corners about the element centre and take their AABB:
    exact for right-angle rotations and a conservative super-set for arbitrary angles, which suits the
    zero-false-negative gate.
    """
    rotation = element.get("rotation", 0)
    if not isinstance(rotation, (int, float)) or not math.isfinite(rotation):
        return bbox
    rotation %= 360
    if math.isclose(rotation, 0, abs_tol=1e-9):
        return bbox
    cx = element["x"] + element["width"] / 2
    cy = element["y"] + element["height"] / 2
    radians = math.radians(rotation)
    sine, cosine = math.sin(radians), math.cos(radians)
    corners = [
        (bbox["x"], bbox["y"]),
        (bbox["x"] + bbox["width"], bbox["y"]),
        (bbox["x"], bbox["y"] + bbox["height"]),
        (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
    ]
    rotated = [
        (
            cx + (px - cx) * cosine - (py - cy) * sine,
            cy + (px - cx) * sine + (py - cy) * cosine,
        )
        for px, py in corners
    ]
    xs = [point[0] for point in rotated]
    ys = [point[1] for point in rotated]
    return {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}


def intersection_area(left: dict[str, Any], right: dict[str, Any]) -> int | float:
    width = min(left["x"] + left["width"], right["x"] + right["width"]) - max(left["x"], right["x"])
    height = min(left["y"] + left["height"], right["y"] + right["height"]) - max(left["y"], right["y"])
    if width <= 0 or height <= 0:
        return 0
    return width * height


def intersection_height(left: dict[str, Any], right: dict[str, Any]) -> int | float:
    height = min(left["y"] + left["height"], right["y"] + right["height"]) - max(left["y"], right["y"])
    return max(height, 0)


def intersection_width(left: dict[str, Any], right: dict[str, Any]) -> int | float:
    width = min(left["x"] + left["width"], right["x"] + right["width"]) - max(left["x"], right["x"])
    return max(width, 0)


def element_area(element: dict[str, Any]) -> int | float:
    return max(element["width"], 0) * max(element["height"], 0)


def contains(outer: dict[str, Any], inner: dict[str, Any], tolerance: int | float = 2) -> bool:
    return (
        inner["x"] >= outer["x"] - tolerance
        and inner["y"] >= outer["y"] - tolerance
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + tolerance
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + tolerance
    )


def is_drawn_behind(element: dict[str, Any], reference: dict[str, Any]) -> bool:
    """True when ``element`` sits lower in the stacking order than ``reference``.

    ``order`` is the paint sequence assigned in extract_elements: lower paints first, so a lower
    ``order`` renders underneath. Every stacking test funnels through this helper (and its inverse
    is_drawn_in_front_of) so "behind" vs "in front" is decided in one place -- raw ``order`` compares
    at each call site drifted between ``<`` and ``<=`` and inverted the meaning by accident.
    """
    return element["order"] < reference["order"]


def is_drawn_in_front_of(element: dict[str, Any], reference: dict[str, Any]) -> bool:
    """True when ``element`` paints on top of ``reference`` (strictly higher stacking order)."""
    return element["order"] > reference["order"]


def is_bottom_layer_full_slide_whiteboard(
    whiteboard: dict[str, Any], other: dict[str, Any], slide_width: int | float, slide_height: int | float
) -> bool:
    return (
        is_drawn_behind(whiteboard, other)
        and whiteboard["x"] <= 2
        and whiteboard["y"] <= 2
        and whiteboard["width"] >= slide_width - 4
        and whiteboard["height"] >= slide_height - 4
    )


def is_background_container_for_whiteboard(container: dict[str, Any], whiteboard: dict[str, Any]) -> bool:
    if is_drawn_in_front_of(container, whiteboard):
        return False
    if is_text_element(container):
        return False
    return contains(container, whiteboard)


def is_template_text_stack(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if not (is_text_element(left) and is_text_element(right)):
        return False
    if not (has_text_content(left) and has_text_content(right)):
        return True
    top, bottom = sorted([left, right], key=lambda element: element["y"])
    top_type = top.get("textType")
    bottom_type = bottom.get("textType")
    allowed_pairs = {
        ("title", "sub-headline"),
        ("title", None),
        ("headline", "headline"),
        ("headline", None),
    }
    if (top_type, bottom_type) not in allowed_pairs:
        return False
    same_column = abs(top["x"] - bottom["x"]) <= 4
    vertical_offset = bottom["y"] - top["y"]
    top_font_size = float(top.get("fontSize", 16))
    if not (same_column and vertical_offset >= top_font_size * 0.75):
        return False
    # The authored-box vertical offset only proves the boxes were *laid out* as a stack. A title sized
    # for one line but wrapping to several grows its glyphs down onto the subtitle even though the boxes
    # were stacked (slides p17: the 72px title "全系列巡礼" wraps and its ink lands on the subtitle
    # below). Treat the stack as benign only when the estimated glyph boxes do not actually collide.
    top_glyph = estimate_text_visual_bbox(top)
    bottom_glyph = estimate_text_visual_bbox(bottom)
    if top_glyph is None or bottom_glyph is None:
        return True
    return intersection_area(top_glyph, bottom_glyph) < NON_PARALLEL_TEXT_OVERLAP_MIN_AREA


def should_flag_horizontal_text_overflow(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if not (is_text_element(left) and is_text_element(right)):
        return False
    if not (has_text_content(left) and has_text_content(right)):
        return False
    if is_ghost_text(left) or is_ghost_text(right):
        return False
    if is_template_text_stack(left, right) or is_similar_text_overlay(left, right):
        return False

    source, target = sorted([left, right], key=lambda element: element["x"])
    if source["x"] == target["x"]:
        return False
    wrap_enabled = source.get("wrap") not in {"false", "0"}
    has_horizontal_gap = source["x"] + source["width"] <= target["x"]
    if wrap_enabled and has_horizontal_gap:
        return False
    if source.get("autoFit") == "normal-auto-fit":
        return False
    if source.get("textAlign") in {"center", "right"}:
        return False

    font_size = source["fontSize"] if isinstance(source["fontSize"], (int, float)) else 16
    padding_left = source.get("paddingLeft", 0)
    padding_right = source.get("paddingRight", 0)
    available_width = max(source["width"] - padding_left - padding_right, 1)
    visual_width = estimate_text_max_line_width(source)
    overflow_width = visual_width - available_width
    min_overflow = max(font_size * 1.5, available_width * 0.08)
    if overflow_width < min_overflow:
        return False

    intrusion_width = source["x"] + padding_left + visual_width - target["x"]
    min_intrusion = max(font_size * 1.5, target["width"] * 0.08)
    if intrusion_width < min_intrusion:
        return False

    vertical_overlap = intersection_height(source, target)
    min_vertical_overlap = min(source["height"], target["height"]) * 0.40
    return vertical_overlap >= min_vertical_overlap


def horizontal_text_overflow_measurement(left: dict[str, Any], right: dict[str, Any]) -> dict[str, int | float]:
    source, target = sorted([left, right], key=lambda element: element["x"])
    padding_left = source.get("paddingLeft", 0)
    visual_width = estimate_text_max_line_width(source)
    source_visual_bbox = {"x": source["x"] + padding_left, "y": source["y"], "width": visual_width, "height": source["height"]}
    width = intersection_width(source_visual_bbox, target)
    height = intersection_height(source_visual_bbox, target)
    return {
        "intersection_width": round(width, 3),
        "intersection_height": round(height, 3),
        "intersection_area": round(width * height, 3),
    }


def should_flag_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if is_text_element(left) and not has_text_content(left):
        return False
    if is_text_element(right) and not has_text_content(right):
        return False
    if is_ghost_text(left) or is_ghost_text(right):
        return False
    if is_template_text_stack(left, right):
        return False
    if is_text_element(left) and is_text_element(right):
        if is_similar_text_overlay(left, right):
            return False
        left_visual = estimate_text_visual_bbox(left)
        right_visual = estimate_text_visual_bbox(right)
        if left_visual is None or right_visual is None:
            return False
        overlap_area = intersection_area(left_visual, right_visual)
        if overlap_area <= 0:
            return False
        # Any non-trivial glyph-box intersection is a genuine collision, whether the runs are parallel or
        # not. Text visual boxes are already eroded to the estimated ink extent, so a real overlap here
        # means glyphs actually touch; gate only on an absolute minimum area to absorb sub-pixel estimation
        # noise. The former 30%-of-smaller-box ratio for parallel runs masked real collisions where a short
        # run clipped the edge of a taller one (slides p7: "/11??@@a" vs "文字碰撞3", ~17% of the smaller box).
        return overlap_area >= NON_PARALLEL_TEXT_OVERLAP_MIN_AREA
    return False


def build_whiteboard_external_overlap_issue(
    whiteboard: dict[str, Any], overlap_details: list[dict[str, Any]]
) -> dict[str, Any]:
    element_refs = [detail["element"] for detail in overlap_details]
    return {
        "level": "warning",
        "code": "whiteboard_external_overlap",
        "elements": [element_ref(whiteboard), *element_refs],
        "message": (
            f"whiteboard {element_label(whiteboard)} overlaps {len(element_refs)} "
            "sibling elements across its boundary"
        ),
        "hint": (
            "Treat this as a static whiteboard container-bbox risk, not final visual proof. "
            "After moving or accepting the overlap, use screenshot QA or equivalent rendered visual inspection as "
            "the final authority because XML readback does not include whiteboard SVG/Mermaid internals."
        ),
        "overlaps": overlap_details,
    }


def should_report_whiteboard_overlap(
    whiteboard: dict[str, Any],
    other: dict[str, Any],
    slide_width: int | float,
    slide_height: int | float,
) -> dict[str, Any] | None:
    if other is whiteboard or not intersects(whiteboard, other):
        return None
    if is_ghost_text(other):
        return None
    if contains(whiteboard, other):
        return None
    if is_bottom_layer_full_slide_whiteboard(whiteboard, other, slide_width, slide_height):
        return None
    if is_background_container_for_whiteboard(other, whiteboard):
        return None

    overlap_width = intersection_width(whiteboard, other)
    overlap_height = intersection_height(whiteboard, other)
    if overlap_width < 8 or overlap_height < 8:
        return None

    other_area = element_area(other)
    if other_area <= 0:
        return None
    overlap_area = overlap_width * overlap_height
    overlap_ratio = overlap_area / other_area
    if overlap_ratio < 0.15:
        return None

    return {
        "element": element_ref(other),
        "kind": other["kind"],
        "type": other.get("type"),
        "overlap_width": overlap_width,
        "overlap_height": overlap_height,
        "target_overlap_ratio": round(overlap_ratio, 3),
    }


def prune_contained_text_overlap_details(
    overlap_details: list[dict[str, Any]], elements_by_ref: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    pruned: list[dict[str, Any]] = []
    for detail in overlap_details:
        element = elements_by_ref[detail["element"]]
        if is_text_element(element):
            has_reported_container = any(
                detail["element"] != other_detail["element"]
                and not is_text_element(elements_by_ref[other_detail["element"]])
                and contains(elements_by_ref[other_detail["element"]], element)
                for other_detail in overlap_details
            )
            if has_reported_container:
                continue
        pruned.append(detail)
    return pruned


def detect_whiteboard_external_overlaps(
    elements: list[dict[str, Any]], slide_width: int | float, slide_height: int | float
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    elements_by_ref = {element_ref(element): element for element in elements}
    for whiteboard in [element for element in elements if is_whiteboard_element(element)]:
        overlap_details = [
            detail
            for element in elements
            if (
                detail := should_report_whiteboard_overlap(
                    whiteboard,
                    element,
                    slide_width,
                    slide_height,
                )
            )
            is not None
        ]
        overlap_details = prune_contained_text_overlap_details(overlap_details, elements_by_ref)
        if overlap_details:
            issues.append(build_whiteboard_external_overlap_issue(whiteboard, overlap_details))
    return issues


def element_canvas_bbox(element: dict[str, Any]) -> dict[str, int | float]:
    bbox = {key: element[key] for key in ("x", "y", "width", "height")}
    if element["kind"] != "chart" and not (element["kind"] == "shape" and element["type"] == "text"):
        return bbox
    rotation = element["rotation"]
    if not isinstance(rotation, (int, float)) or not math.isfinite(rotation):
        rotation = 0
    rotation %= 360
    if math.isclose(rotation, 0, abs_tol=1e-9):
        return _union_text_glyph_extent(element, bbox)
    radians = math.radians(rotation)
    sine = abs(math.sin(radians))
    cosine = abs(math.cos(radians))
    sine = 0 if math.isclose(sine, 0, abs_tol=1e-12) else sine
    cosine = 0 if math.isclose(cosine, 0, abs_tol=1e-12) else cosine
    rotated_width = element["width"] * cosine + element["height"] * sine
    rotated_height = element["width"] * sine + element["height"] * cosine
    return {
        "x": element["x"] - (rotated_width - element["width"]) / 2,
        "y": element["y"] - (rotated_height - element["height"]) / 2,
        "width": rotated_width,
        "height": rotated_height,
    }


def _union_text_glyph_extent(
    element: dict[str, Any], bbox: dict[str, int | float]
) -> dict[str, int | float]:
    """Grow an axis-aligned text element's canvas box to cover glyphs painted past its authored box.

    A wrap="false" run keeps its full unwrapped line width even when that exceeds the authored box, and
    shape-auto-fit grows the box downward -- both paint glyphs outside the declared bounds. When those
    glyphs run off the canvas the overflow is real but invisible to the authored box (slides p16: the
    300px ghost "CONTENTS" sits in a 400px box yet its ink extends ~1476px, well past the 960 canvas).
    estimate_text_visual_bbox already reports the rendered ink extent in canvas space, so union it in.
    """
    if not (element["kind"] == "shape" and element["type"] == "text"):
        return bbox
    glyph = estimate_text_visual_bbox(element)
    if glyph is None:
        return bbox
    left = min(bbox["x"], glyph["x"])
    top = min(bbox["y"], glyph["y"])
    right = max(bbox["x"] + bbox["width"], glyph["x"] + glyph["width"])
    bottom = max(bbox["y"] + bbox["height"], glyph["y"] + glyph["height"])
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def detect_elements_out_of_canvas(
    elements: list[dict[str, Any]], slide_width: int | float, slide_height: int | float
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    # Every drawable element has a canvas-space bbox at this point. Keep this
    # deny-list-free so newly supported element kinds cannot silently escape
    # the page-boundary check.
    for element in elements:
        bbox = element_canvas_bbox(element)
        overflow = {
            "left": max(-bbox["x"], 0),
            "top": max(-bbox["y"], 0),
            "right": max(bbox["x"] + bbox["width"] - slide_width, 0),
            "bottom": max(bbox["y"] + bbox["height"] - slide_height, 0),
        }
        overflow_details = [
            f"{side} by {amount:g}px"
            for side, amount in overflow.items()
            if amount > CANVAS_OVERFLOW_TOLERANCE
        ]
        if not overflow_details:
            continue
        issues.append(
            {
                "level": "error",
                "code": f'{element["kind"]}_out_of_canvas',
                "elements": [element_ref(element)],
                "canvas": {"width": slide_width, "height": slide_height},
                "bbox": bbox,
                "overflow": overflow,
                "message": (
                    f'{element["kind"]} {element_label(element)} exceeds the {slide_width:g}x{slide_height:g} canvas '
                    f'({", ".join(overflow_details)})'
                ),
                "hint": (
                    "Move the table inside the canvas, reduce table.width/table.height, or split the table across "
                    "slides."
                    if element["kind"] == "table"
                    else f'Move the {element["kind"]} inside the canvas or reduce its width/height.'
                ),
            }
        )
    return issues


def extract_table_column_sizes(table_xml: str) -> list[int | float | None]:
    sizes: list[int | float | None] = []
    for match in re.finditer(r"<col\b([^>]*)/?>", table_xml):
        attrs = match.group(1)
        span = extract_numeric_attribute(attrs, "span") or 1
        span_count = int(span) if math.isfinite(span) and span > 0 and float(span).is_integer() else 1
        sizes.extend([extract_numeric_attribute(attrs, "width")] * span_count)
    return sizes


def extract_table_row_sizes(table_xml: str) -> list[int | float | None]:
    return [extract_numeric_attribute(match.group(1), "height") for match in re.finditer(r"<tr\b([^>]*)>", table_xml)]


def resolve_table_dimension(
    table_xml: str,
    declared_size: int | float | None,
    extract_sizes: Any,
    default_size: int | float,
) -> tuple[int | float | None, dict[str, Any] | None]:
    input_sizes = extract_sizes(table_xml)
    if not input_sizes:
        return declared_size, None
    layout = solve_weighted_min_layout(
        input_sizes, default_size, declared_size if is_filled_size(declared_size) else None
    )
    return layout["actual_size"], layout


def format_size(size: int | float) -> str:
    return f"{size:g}"


def detect_table_layout_size_mismatches(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    dimensions = {
        "width": ("col", "column widths"),
        "height": ("tr", "row heights"),
    }
    for table in (element for element in elements if element["kind"] == "table"):
        for dimension, (child_tag, child_description) in dimensions.items():
            target_size = table[f"declared_{dimension}"]
            if not is_filled_size(target_size):
                continue
            layout = table["table_layouts"][dimension]
            if layout is None:
                continue
            actual_size = layout["actual_size"]
            if math.isclose(actual_size, target_size, rel_tol=1e-9, abs_tol=1e-9):
                continue
            issues.append(
                {
                    "level": "info",
                    "code": "table_resolved_size_mismatch",
                    "elements": [element_ref(table)],
                    "dimension": dimension,
                    "declared_size": target_size,
                    "resolved_size": actual_size,
                    "resolved_sizes": layout["final_sizes"],
                    "message": (
                        f'table {element_label(table)} declares {dimension}={format_size(target_size)}px, but its '
                        f"{child_description} resolve to {format_size(actual_size)}px"
                    ),
                    "hint": (
                        f"Set table.{dimension} to {format_size(actual_size)}px, or adjust <{child_tag}> sizes "
                        f"so their resolved total matches {format_size(target_size)}px."
                    ),
                }
            )
    return issues


def segment_intersects_rect(
    x1: float, y1: float, x2: float, y2: float, rect: dict[str, int | float]
) -> bool:
    """True when segment (x1,y1)-(x2,y2) enters the axis-aligned rect (Liang-Barsky clip)."""
    left = rect["x"]
    top = rect["y"]
    right = rect["x"] + rect["width"]
    bottom = rect["y"] + rect["height"]
    if right <= left or bottom <= top:
        return False
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return left <= x1 <= right and top <= y1 <= bottom
    t_enter, t_exit = 0.0, 1.0
    for delta, distance in ((-dx, x1 - left), (dx, right - x1), (-dy, y1 - top), (dy, bottom - y1)):
        if delta == 0:
            if distance < 0:
                return False
            continue
        t = distance / delta
        if delta < 0:
            t_enter = max(t_enter, t)
        else:
            t_exit = min(t_exit, t)
        if t_enter > t_exit:
            return False
    return True


def line_text_graze_margin(text_element: dict[str, Any]) -> float:
    font_size = text_element["fontSize"] if isinstance(text_element.get("fontSize"), (int, float)) else 16
    return max(font_size * LINE_TEXT_GRAZE_FONT_RATIO, LINE_TEXT_GRAZE_MIN_PX)


def erode_rect(rect: dict[str, int | float], margin: float) -> dict[str, int | float] | None:
    width = rect["width"] - 2 * margin
    height = rect["height"] - 2 * margin
    if width <= 0 or height <= 0:
        return None
    return {"x": rect["x"] + margin, "y": rect["y"] + margin, "width": width, "height": height}


def estimate_text_crossing_bbox(element: dict[str, Any]) -> dict[str, int | float] | None:
    """Glyph box for <line> crossing tests, using the real line-spacing vertical span.

    estimate_text_visual_bbox approximates the vertical extent as line_count * font_size * 1.2,
    which under-reports multi-line runs with lineSpacing > 1.2 (e.g. poems at multiple:1.6). A
    horizontal separator sitting between two such lines then fell outside the box and the crossing
    escaped (slides p8/p10). Here we widen only the height to the real leading span so the line-
    crossing rule sees where glyphs actually sit; width/anchoring stay identical to the shared box.
    """
    glyph_bbox = estimate_text_visual_bbox(element)
    if glyph_bbox is None:
        return None
    block = estimate_text_block_height(element)
    if block is None:
        return glyph_bbox
    padding_top = element.get("paddingTop", 0)
    padding_bottom = element.get("paddingBottom", 0)
    content_height = max(element["height"] - padding_top - padding_bottom, 0)
    spacing_height = min(content_height, max(1, block["estimated_height"]))
    if spacing_height <= glyph_bbox["height"]:
        return glyph_bbox
    updated = dict(glyph_bbox)
    # Re-anchor vertically the same way estimate_text_visual_bbox does, using the taller span.
    y = element["y"] + padding_top
    if element.get("verticalAlign") == "middle":
        y += (content_height - spacing_height) / 2
    elif element.get("verticalAlign") == "bottom":
        y += content_height - spacing_height
    updated["y"] = y
    updated["height"] = spacing_height
    return updated


def line_crosses_text(line: dict[str, Any], text_element: dict[str, Any]) -> bool:
    if not is_visually_rendered(line) or line.get("alpha", 1) < LINE_MIN_VISIBLE_ALPHA:
        return False
    if not is_text_element(text_element) or not has_text_content(text_element):
        return False
    if is_ghost_text(text_element) or is_decorative_text(text_element):
        return False
    glyph_bbox = estimate_text_crossing_bbox(text_element)
    if glyph_bbox is None:
        return False
    # Erode the glyph box so a line skimming the letter edge or only clipping the padding-only text
    # frame is exempt; only a line that actually cuts through the letterforms is a crossing.
    target = erode_rect(glyph_bbox, line_text_graze_margin(text_element))
    if target is None:
        return False
    return segment_intersects_rect(
        line["startX"], line["startY"], line["endX"], line["endY"], target
    )


def detect_line_text_crossings(
    slide_xml: str, elements: list[dict[str, Any]], slide_number: int
) -> list[dict[str, Any]]:
    lines = extract_line_elements(slide_xml)
    if not lines:
        return []
    attach_source_xml_paths(lines, build_source_xml_paths(slide_xml, slide_number))
    text_elements = [element for element in elements if is_text_element(element)]
    issues: list[dict[str, Any]] = []
    for line in lines:
        for text_element in text_elements:
            if not line_crosses_text(line, text_element):
                continue
            issues.append(
                {
                    "level": "error",
                    "code": "bbox_overlap",
                    "elements": [element_ref(line), element_ref(text_element)],
                    "message": (
                        f"line {element_label(line)} crosses text {element_label(text_element)}"
                    ),
                    "hint": "Move the line off the text glyphs so it no longer cuts through the letterforms.",
                }
            )
    return issues


def lint_slide(
    slide_xml: str, slide_number: int, slide_width: int | float = 960, slide_height: int | float = 540
) -> dict[str, Any]:
    elements = extract_elements(slide_xml)
    attach_source_xml_paths(elements, build_source_xml_paths(slide_xml, slide_number))
    height_overflow_issues = detect_text_may_overflow_shapes(elements)
    # An error-level height overflow suppresses the width-wrap error for the same element (one run,
    # one "text overflows its box" defect). Only error-level counts: info-level background decoration
    # (large low-alpha text under other content) must not mask a genuine width overflow on the run.
    height_overflow_refs = {
        element_locator
        for issue in height_overflow_issues
        if issue["level"] == "error"
        for element_locator in issue["elements"]
    }
    issues: list[dict[str, Any]] = [
        *detect_whiteboard_external_overlaps(elements, slide_width, slide_height),
        *detect_elements_out_of_canvas(elements, slide_width, slide_height),
        *detect_table_layout_size_mismatches(elements),
        *height_overflow_issues,
        *detect_text_may_wrap_shapes(elements, height_overflow_refs),
        *detect_image_text_occlusions(elements, slide_width, slide_height),
        *detect_table_text_occlusions(elements),
        *detect_chart_text_occlusions(elements),
        *detect_text_container_overflow(elements, slide_width, slide_height),
        *detect_shape_container_overlaps(elements, slide_width, slide_height),
        *detect_shape_text_occlusions(elements),
        *detect_auto_fit_growth_collisions(elements),
        *detect_line_text_crossings(slide_xml, elements, slide_number),
    ]

    for index, left in enumerate(elements):
        for right in elements[index + 1 :]:
            horizontal_overflow = should_flag_horizontal_text_overflow(left, right)
            # should_flag_overlap already returns False for non-text pairs and for glyph boxes that do
            # not overlap, so the earlier raw-bbox intersects() guard was redundant for axis-aligned
            # text (the glyph box is inside the element box) and wrong for rotated text (rotation
            # expands the glyph box past a raw box that no longer intersects -- slides p6). Rely on
            # should_flag_overlap's rotation-aware glyph geometry as the sole authority.
            if not horizontal_overflow and not should_flag_overlap(left, right):
                continue
            issues.append(
                {
                    "level": "error",
                    "code": "bbox_overlap",
                    "elements": [element_ref(left), element_ref(right)],
                    "message": f"{element_label(left)} overlaps {element_label(right)}",
                    "hint": "Move or resize the elements so their visual bounds no longer intersect.",
                    **(
                        {"measurement": horizontal_text_overflow_measurement(left, right)}
                        if horizontal_overflow
                        else {}
                    ),
                }
            )

    return {
        "slide_number": slide_number,
        "element_count": len(elements),
        "elements": elements,
        "issues": dedupe_bbox_overlap_issues(issues),
    }


def dedupe_bbox_overlap_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate bbox_overlap issues that name the same element pair.

    The generic text-text loop and the specialised detectors (auto-fit growth, line crossings) can
    each surface the same colliding pair. To an agent that is one defect, so we keep the first issue
    for a given unordered {code, element-pair} and drop later repeats. Non-overlap codes are untouched.

    text_may_overflow_shape is shared by the vertical (height) and horizontal (width) detectors: a run
    can overflow on both axes (slides p3: bMP wraps two lines *and* is too wide), which to the user is
    still one "text overflows its box" defect. We keep a single issue per element -- the highest
    severity, so an info-level background-decoration height issue never hides the width error for the run.
    """
    _severity_rank = {"error": 2, "warning": 1, "info": 0}
    best_overflow_level: dict[str, str] = {}
    for issue in issues:
        if issue.get("code") == "text_may_overflow_shape" and len(issue["elements"]) == 1:
            element_locator = issue["elements"][0]
            current = best_overflow_level.get(element_locator)
            if current is None or _severity_rank[issue["level"]] > _severity_rank[current]:
                best_overflow_level[element_locator] = issue["level"]

    seen: set[tuple[str, frozenset[str]]] = set()
    kept_overflow: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for issue in issues:
        if issue.get("code") == "bbox_overlap":
            key = (issue["code"], frozenset(issue["elements"]))
            if key in seen:
                continue
            seen.add(key)
        elif issue.get("code") == "text_may_overflow_shape" and len(issue["elements"]) == 1:
            element_locator = issue["elements"][0]
            if (
                element_locator in kept_overflow
                or issue["level"] != best_overflow_level[element_locator]
            ):
                continue
            kept_overflow.add(element_locator)
        deduped.append(issue)
    return deduped



MIN_CONTAINER_WIDTH = 140
MIN_CONTAINER_HEIGHT = 160
MIN_SHORT_CARD_HEIGHT = 80
MIN_CONTAINER_AREA = 20_000
MIN_CONTENT_COVERAGE_RATIO = 0.15
MIN_SLIDE_CONTENT_COVERAGE_RATIO = 0.035
MIN_SLIDE_CONTENT_ELEMENT_COUNT = 4
SHORT_CARD_SIZE_TOLERANCE_RATIO = 0.10
MIN_SIMILAR_SHORT_CARD_COUNT = 2
LARGE_VISUAL_CHILD_RATIO = 0.35
LAYOUT_PANEL_SPAN_RATIO = 0.90
IMAGE_OVERLAY_MATCH_RATIO = 0.90
DENSITY_CONTAINMENT_TOLERANCE = 8


def clipped_bbox(element: dict[str, Any], container: dict[str, Any]) -> dict[str, int | float] | None:
    left = max(element["x"], container["x"])
    top = max(element["y"], container["y"])
    right = min(element["x"] + element["width"], container["x"] + container["width"])
    bottom = min(element["y"] + element["height"], container["y"] + container["height"])
    if right <= left or bottom <= top:
        return None
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def rectangle_union_area(rectangles: list[dict[str, int | float]]) -> int | float:
    x_coordinates = sorted({coordinate for rect in rectangles for coordinate in (rect["x"], rect["x"] + rect["width"])})
    area = 0
    for left, right in zip(x_coordinates, x_coordinates[1:]):
        intervals = sorted(
            (rect["y"], rect["y"] + rect["height"])
            for rect in rectangles
            if rect["x"] < right and rect["x"] + rect["width"] > left
        )
        covered_height = 0
        interval_end: int | float | None = None
        for top, bottom in intervals:
            if interval_end is None:
                covered_height += bottom - top
                interval_end = bottom
            elif bottom > interval_end:
                covered_height += bottom - max(top, interval_end)
                interval_end = bottom
        area += (right - left) * covered_height
    return area


def has_similar_short_card_peer(element: dict[str, Any], elements: list[dict[str, Any]]) -> bool:
    return sum(
        other is not element
        and is_visually_rendered(other)
        and other["kind"] == "shape"
        and other["type"] == "rect"
        and other["width"] >= MIN_CONTAINER_WIDTH
        and other["height"] >= MIN_SHORT_CARD_HEIGHT
        and element_area(other) >= MIN_CONTAINER_AREA
        and abs(other["width"] - element["width"]) / max(other["width"], element["width"])
        <= SHORT_CARD_SIZE_TOLERANCE_RATIO
        and abs(other["height"] - element["height"]) / max(other["height"], element["height"])
        <= SHORT_CARD_SIZE_TOLERANCE_RATIO
        for other in elements
    ) >= MIN_SIMILAR_SHORT_CARD_COUNT


def is_layout_container(
    element: dict[str, Any],
    slide_width: int | float,
    slide_height: int | float,
    elements: list[dict[str, Any]] | None = None,
) -> bool:
    has_supported_height = element["height"] >= MIN_CONTAINER_HEIGHT or (
        elements is not None
        and element["height"] >= MIN_SHORT_CARD_HEIGHT
        and has_similar_short_card_peer(element, elements)
    )
    return (
        element["kind"] == "shape"
        and element["type"] == "rect"
        and is_visually_rendered(element)
        and element["width"] >= MIN_CONTAINER_WIDTH
        and has_supported_height
        and element_area(element) >= MIN_CONTAINER_AREA
        and not (
            element["x"] <= 2
            and element["y"] <= 2
            and element["width"] >= slide_width - 4
            and element["height"] >= slide_height - 4
        )
    )


def is_edge_spanning_layout_panel(
    element: dict[str, Any], slide_width: int | float, slide_height: int | float
) -> bool:
    touches_horizontal_edge = element["x"] <= 2 or element["x"] + element["width"] >= slide_width - 2
    touches_vertical_edge = element["y"] <= 2 or element["y"] + element["height"] >= slide_height - 2
    return (touches_horizontal_edge and element["height"] >= slide_height * LAYOUT_PANEL_SPAN_RATIO) or (
        touches_vertical_edge and element["width"] >= slide_width * LAYOUT_PANEL_SPAN_RATIO
    )


def has_matching_image_overlay(container: dict[str, Any], elements: list[dict[str, Any]]) -> bool:
    container_area = element_area(container)
    return any(
        element["kind"] == "img"
        and is_visually_rendered(element)
        and intersection_area(container, element) / max(1, container_area) >= IMAGE_OVERLAY_MATCH_RATIO
        for element in elements
    )


def is_nested_in_layout_panel(
    container: dict[str, Any], elements: list[dict[str, Any]], slide_width: int | float, slide_height: int | float
) -> bool:
    return any(
        element is not container
        and element["kind"] == "shape"
        and element["type"] == "rect"
        and is_visually_rendered(element)
        and is_edge_spanning_layout_panel(element, slide_width, slide_height)
        and contains(element, container, tolerance=DENSITY_CONTAINMENT_TOLERANCE)
        for element in elements
    )


def extract_density_elements(slide_xml: str, slide_number: int = 1) -> list[dict[str, Any]]:
    elements = extract_elements(slide_xml)
    source_paths = build_source_xml_paths(slide_xml, slide_number)
    attach_source_xml_paths(elements, source_paths)
    shape_elements_by_index = {
        element["_source_kind_index"]: element
        for element in elements
        if element["kind"] == "shape"
    }
    root = ET.fromstring(slide_xml)
    shape_index = 0
    for node in root.iter():
        if xml_local_name(node.tag) != "shape":
            continue
        shape_index += 1
        element = shape_elements_by_index.get(shape_index)
        if element is None:
            continue
        content_node = next(
            (child for child in node if xml_local_name(child.tag) == "content"),
            None,
        )
        paragraphs = (
            [
                " ".join("".join(paragraph.itertext()).split())
                for paragraph in content_node.iter()
                if xml_local_name(paragraph.tag) == "p"
            ]
            if content_node is not None
            else []
        )
        raw_font_size = (
            content_node.attrib.get("fontSize") if content_node is not None else None
        ) or node.attrib.get("fontSize")
        try:
            base_font_size = float(raw_font_size or 16)
        except ValueError:
            base_font_size = 16.0
        element.update(
            {
                "textType": content_node.attrib.get("textType") if content_node is not None else None,
                "textAlign": content_node.attrib.get("textAlign") if content_node is not None else None,
                "autoFit": content_node.attrib.get("autoFit") if content_node is not None else None,
                "fontSize": base_font_size,
                "text": "\n".join(paragraph for paragraph in paragraphs if paragraph),
            }
        )
        if not has_text_content(element):
            continue
        declared_font_sizes = []
        for descendant in node.iter():
            raw_declared_font_size = descendant.attrib.get("fontSize")
            if raw_declared_font_size is None:
                continue
            try:
                declared_font_sizes.append(float(raw_declared_font_size))
            except ValueError:
                continue
        if declared_font_sizes:
            element["fontSize"] = max(declared_font_sizes)
    for source_kind_index, match in enumerate(
        re.finditer(r"<icon\b([^>]*)>", slide_xml), start=1
    ):
        attrs = match.group(1)
        source_id = extract_attribute(attrs, "id") or None
        x = extract_numeric_attribute(attrs, "topLeftX")
        y = extract_numeric_attribute(attrs, "topLeftY")
        width = extract_numeric_attribute(attrs, "width")
        height = extract_numeric_attribute(attrs, "height")
        if any(value is None for value in (x, y, width, height)):
            continue
        icon_alpha = extract_numeric_attribute(attrs, "alpha")
        elements.append(
            {
                "id": source_id or f"icon-{len(elements) + 1}",
                "_source_id": source_id,
                "kind": "icon",
                "type": "icon",
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotation": extract_numeric_attribute(attrs, "rotation") or 0,
                "alpha": icon_alpha if icon_alpha is not None else 1,
                "order": len(elements),
                "_source_kind_index": source_kind_index,
            }
        )
    for source_kind_index, match in enumerate(
        re.finditer(r"<polyline\b([^>]*)>", slide_xml), start=1
    ):
        attrs = match.group(1)
        x = extract_numeric_attribute(attrs, "topLeftX")
        y = extract_numeric_attribute(attrs, "topLeftY")
        width = extract_numeric_attribute(attrs, "width")
        height = extract_numeric_attribute(attrs, "height")
        if any(value is None for value in (x, y, width, height)):
            continue
        polyline_alpha = extract_numeric_attribute(attrs, "alpha")
        source_id = extract_attribute(attrs, "id") or None
        elements.append(
            {
                "id": source_id or f"polyline-{len(elements) + 1}",
                "_source_id": source_id,
                "kind": "polyline",
                "type": "polyline",
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotation": extract_numeric_attribute(attrs, "rotation") or 0,
                "alpha": polyline_alpha if polyline_alpha is not None else 1,
                "order": len(elements),
                "_source_kind_index": source_kind_index,
            }
        )
    for line_element in extract_line_elements(slide_xml):
        line_element["order"] = len(elements)
        elements.append(line_element)
    attach_source_xml_paths(elements, source_paths)
    for element in elements:
        element["_slide_number"] = slide_number
    return elements


def is_visually_rendered(element: dict[str, Any]) -> bool:
    return element.get("alpha", 1) > 0


def visual_bbox(element: dict[str, Any], container: dict[str, Any]) -> dict[str, int | float] | None:
    if not is_visually_rendered(element):
        return None
    if is_text_element(element):
        estimated = estimate_text_visual_bbox(element)
        return clipped_bbox(estimated, container) if estimated else None
    return clipped_bbox(element, container)


def own_text_visual_bbox(container: dict[str, Any]) -> dict[str, int | float] | None:
    if container["kind"] != "shape" or not has_text_content(container):
        return None
    text_proxy = {**container, "type": "text"}
    estimated = estimate_text_visual_bbox(text_proxy)
    return clipped_bbox(estimated, container) if estimated else None


def slide_content_visual_bbox(
    element: dict[str, Any], slide_bbox: dict[str, int | float]
) -> dict[str, int | float] | None:
    if not is_visually_rendered(element):
        return None
    if is_text_element(element):
        estimated = estimate_text_visual_bbox(element)
        return clipped_bbox(estimated, slide_bbox) if estimated else None
    if element["kind"] == "shape" and has_text_content(element):
        estimated = own_text_visual_bbox(element)
        return clipped_bbox(estimated, slide_bbox) if estimated else None
    if element["kind"] == "line":
        # a straight horizontal/vertical line has zero width or height in one axis; clipped_bbox
        # treats zero-area rects as invisible, so pad to its rendered stroke thickness instead.
        return clipped_bbox(line_stroke_bbox(element), slide_bbox)
    if element["kind"] in {"img", "chart", "table", "whiteboard", "embed", "icon", "polyline"}:
        return clipped_bbox(element, slide_bbox)
    return None


def line_stroke_bbox(element: dict[str, Any]) -> dict[str, Any]:
    return {**element, "width": max(element["width"], 1), "height": max(element["height"], 1)}


def is_slide_content_present(
    element: dict[str, Any], slide_bbox: dict[str, int | float]
) -> bool:
    # Deliberately permissive, unlike slide_content_visual_bbox: blank_slide is asking "is
    # *anything* rendered here", not the richer "counts toward meaningful content density" bar
    # that sparse_slide_content/sparse_container_content apply. A plain shape with no text (a
    # decorative rect/ellipse/etc.), <undefined>, or any future SXSD data element should all
    # count here — deny-list only what's actually invisible (alpha<=0 or zero on-canvas area)
    # instead of maintaining an allow-list that silently treats unlisted kinds as blank.
    if not is_visually_rendered(element):
        return False
    if (
        element["kind"] == "shape"
        and element["type"] == "rect"
        and not has_text_content(element)
        and element["x"] <= 2
        and element["y"] <= 2
        and element["width"] >= slide_bbox["width"] - 4
        and element["height"] >= slide_bbox["height"] - 4
    ):
        # A full-canvas plain rect is a background panel, not content -- same reasoning as
        # is_layout_container's existing background exclusion. A slide with nothing else on it
        # is still effectively blank.
        return False
    bbox = line_stroke_bbox(element) if element["kind"] == "line" else element
    return clipped_bbox(bbox, slide_bbox) is not None


def is_large_visual_child(element: dict[str, Any], container: dict[str, Any]) -> bool:
    if element["kind"] not in {"img", "chart", "table", "whiteboard", "embed"}:
        return False
    if not is_visually_rendered(element):
        return False
    return element_area(element) / element_area(container) >= LARGE_VISUAL_CHILD_RATIO


def detect_sparse_container_content(
    elements: list[dict[str, Any]], slide_number: int, slide_width: int | float, slide_height: int | float
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for container in (
        element for element in elements if is_layout_container(element, slide_width, slide_height, elements)
    ):
        if (
            is_edge_spanning_layout_panel(container, slide_width, slide_height)
            or is_nested_in_layout_panel(container, elements, slide_width, slide_height)
            or has_matching_image_overlay(container, elements)
        ):
            continue
        children = [
            element
            for element in elements
            if element is not container
            and contains(container, element, tolerance=DENSITY_CONTAINMENT_TOLERANCE)
        ]
        if any(is_large_visual_child(child, container) for child in children):
            continue
        own_text_bbox = own_text_visual_bbox(container)
        rectangles = ([own_text_bbox] if own_text_bbox else []) + [
            bbox for child in children if (bbox := visual_bbox(child, container)) is not None
        ]
        content_area = rectangle_union_area(rectangles) if rectangles else 0
        coverage_ratio = content_area / element_area(container)
        if coverage_ratio >= MIN_CONTENT_COVERAGE_RATIO:
            continue
        issues.append(
            {
                "level": "warning",
                "code": "sparse_container_content",
                "target": {
                    "slide_number": slide_number,
                    **(
                        {"container_id": source_element_id(container)}
                        if source_element_id(container) is not None
                        else {}
                    ),
                    "container_xml_path": element_ref(container),
                    "container_type": container["type"],
                    "bbox": {key: container[key] for key in ("x", "y", "width", "height")},
                },
                "rule": {
                    "name": "large_container_visible_content_coverage",
                    "threshold": MIN_CONTENT_COVERAGE_RATIO,
                    "comparison": "content_coverage_ratio < threshold",
                },
                "measurement": {
                    "container_area": element_area(container),
                    "visible_content_area": round(content_area, 3),
                    "content_coverage_ratio": round(coverage_ratio, 3),
                    "content_element_count": len(children) + (1 if own_text_bbox else 0),
                },
                "elements": [
                    element_ref(container),
                    *[element_ref(child) for child in children],
                ],
            }
        )
    return issues


def detect_sparse_slide_content(
    elements: list[dict[str, Any]], slide_number: int, slide_width: int | float, slide_height: int | float
) -> list[dict[str, Any]]:
    slide_bbox = {"x": 0, "y": 0, "width": slide_width, "height": slide_height}
    content = [
        (element, bbox)
        for element in elements
        if (bbox := slide_content_visual_bbox(element, slide_bbox)) is not None
    ]
    if len(content) < MIN_SLIDE_CONTENT_ELEMENT_COUNT:
        return []
    content_area = rectangle_union_area([bbox for _, bbox in content])
    slide_area = slide_width * slide_height
    coverage_ratio = content_area / slide_area
    if coverage_ratio >= MIN_SLIDE_CONTENT_COVERAGE_RATIO:
        return []
    return [
        {
            "level": "warning",
            "code": "sparse_slide_content",
            "target": {
                "slide_number": slide_number,
                "bbox": slide_bbox,
            },
            "rule": {
                "name": "slide_visible_content_coverage",
                "threshold": MIN_SLIDE_CONTENT_COVERAGE_RATIO,
                "comparison": "content_coverage_ratio < threshold",
            },
            "measurement": {
                "slide_area": slide_area,
                "visible_content_area": round(content_area, 3),
                "content_coverage_ratio": round(coverage_ratio, 3),
                "content_element_count": len(content),
            },
            "elements": [element_ref(element) for element, _ in content],
        }
    ]


def detect_blank_slide(
    elements: list[dict[str, Any]],
    slide_number: int,
    slide_width: int | float,
    slide_height: int | float,
) -> list[dict[str, Any]]:
    slide_bbox = {"x": 0, "y": 0, "width": slide_width, "height": slide_height}
    visible_elements = [
        element for element in elements if is_slide_content_present(element, slide_bbox)
    ]
    if visible_elements:
        return []
    return [
        {
            "level": "error",
            "code": "blank_slide",
            "schema_version": "2.0",
            "target": {"slide_number": slide_number},
            "rule": {
                "name": "slide_has_visible_content",
                "comparison": "visible_element_count == 0",
            },
            "measurement": {
                "visible_element_count": 0,
                "declared_element_count": len(elements),
            },
            "elements": [element_ref(element) for element in elements],
            "message": "slide has no visible content beyond empty layout shapes",
            "hint": "Add visible text, an image, a chart, a table, a whiteboard, or an icon before creating the slide.",
        }
    ]


def detect_duplicate_element_ids(
    elements: list[dict[str, Any]], *, cross_slide_only: bool = False
) -> list[dict[str, Any]]:
    elements_by_source_id: dict[str, list[dict[str, Any]]] = {}
    for element in elements:
        source_id = source_element_id(element)
        if source_id is not None:
            elements_by_source_id.setdefault(source_id, []).append(element)
    return [
        {
            "level": "error",
            "code": "duplicate_element_id",
            "elements": [element_ref(element) for element in duplicates],
            "measurement": {
                "element_id": source_id,
                "duplicate_count": len(duplicates),
            },
            "message": f'element id "{source_id}" is used by {len(duplicates)} elements',
            "hint": (
                "Do not invent replacement IDs. For newly authored elements, remove the id attribute. "
                "When updating read-back XML, keep the server ID on the original element only and remove it "
                "from copied or new elements."
            ),
        }
        for source_id, duplicates in elements_by_source_id.items()
        if len(duplicates) > 1
        and (
            not cross_slide_only
            or len({element.get("_slide_number") for element in duplicates}) > 1
        )
    ]


RULE_METADATA: dict[str, dict[str, Any]] = {
    "xml_not_well_formed": {
        "name": "xml_is_well_formed",
        "comparison": "xml_parse_error == false",
    },
    "sml_prefixed_tag": {
        "name": "sml_uses_default_namespace",
        "comparison": "prefixed_sml_tag_count == 0",
    },
    "sxsd_unsupported_tag": {
        "name": "tag_is_supported_by_slides_xml_schema",
        "comparison": "unsupported_tag_count == 0",
    },
    "sxsd_unsupported_attr": {
        "name": "attribute_is_supported_by_slides_xml_schema",
        "comparison": "unsupported_attribute_count == 0",
    },
    "icon_missing_fill_color": {
        "name": "icon_has_visible_fill_color",
        "comparison": "fill_color_present == true",
    },
    "icon_transparent_fill_color": {
        "name": "icon_has_visible_fill_color",
        "comparison": "fill_alpha > 0",
    },
    "iconpark_unsupported_icon_type": {
        "name": "iconpark_type_is_supported",
        "comparison": "icon_type in iconpark_index",
    },
    "bbox_overlap": {
        "name": "text_visual_bounds_do_not_overlap",
        "comparison": "intersection_area == 0",
    },
    "text_may_overflow_shape": {
        "name": "estimated_text_fits_declared_shape",
        "comparison": "estimated_height <= available_height",
    },
    "whiteboard_external_overlap": {
        "name": "whiteboard_does_not_cross_sibling_content",
        "comparison": "external_overlap_count == 0",
    },
    "image_covers_text": {
        "name": "image_does_not_cover_text",
        "comparison": "intersection_area == 0",
    },
    "image_may_cover_vertical_text": {
        "name": "image_vertical_text_occlusion_requires_review",
        "comparison": "intersection_area == 0",
    },
    "table_resolved_size_mismatch": {
        "name": "table_declared_size_matches_resolved_grid",
        "comparison": "declared_size == resolved_size",
    },
    "blank_slide": {
        "name": "slide_has_visible_content",
        "comparison": "visible_element_count > 0",
    },
    "duplicate_element_id": {
        "name": "element_ids_are_unique",
        "comparison": "duplicate_count == 0",
    },
    "chart_missing_numeric_dimension": {
        "name": "chart_data_has_numeric_value_dimension",
        "comparison": "numeric_dimension_count >= 1",
    },
}


def issue_rule(issue: dict[str, Any]) -> dict[str, Any]:
    if issue.get("rule"):
        return {**issue["rule"], "id": issue["code"]}
    if issue["code"].endswith("_out_of_canvas"):
        return {
            "id": issue["code"],
            "name": "element_stays_within_slide_canvas",
            "comparison": "max(left, top, right, bottom overflow) == 0",
        }
    return {
        "id": issue["code"],
        **RULE_METADATA.get(
            issue["code"],
            {"name": issue["code"], "comparison": "violation_count == 0"},
        ),
    }


def issue_measurement(
    issue: dict[str, Any], elements_by_ref: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if issue.get("measurement") is not None:
        return issue["measurement"]
    if issue["code"] == "bbox_overlap" and len(issue.get("elements", [])) == 2:
        left = elements_by_ref.get(issue["elements"][0])
        right = elements_by_ref.get(issue["elements"][1])
        if left and right:
            left_box = (estimate_text_visual_bbox(left) if is_text_element(left) else None) or left
            right_box = (estimate_text_visual_bbox(right) if is_text_element(right) else None) or right
            width = intersection_width(left_box, right_box)
            height = intersection_height(left_box, right_box)
            return {
                "intersection_width": round(width, 3),
                "intersection_height": round(height, 3),
                "intersection_area": round(width * height, 3),
            }
    if issue["code"].endswith("_out_of_canvas"):
        return {
            "canvas": issue.get("canvas"),
            "bbox": issue.get("bbox"),
            "overflow": issue.get("overflow"),
        }
    measurement_keys = (
        "line",
        "column",
        "tag",
        "attr",
        "iconType",
        "line_count",
        "line_height",
        "estimated_height",
        "available_height",
        "overflow",
        "dimension",
        "declared_size",
        "resolved_size",
        "resolved_sizes",
        "overlaps",
    )
    measured = {key: issue[key] for key in measurement_keys if key in issue}
    return measured or {"violation_count": 1}


def related_object(element: dict[str, Any]) -> dict[str, Any]:
    related = {
        "kind": element["kind"],
        "type": element["type"],
    }
    bbox_keys = ("x", "y", "width", "height")
    if all(key in element for key in bbox_keys):
        related["bbox"] = {key: element[key] for key in bbox_keys}
    if source_element_id(element) is not None:
        related["element_id"] = source_element_id(element)
    if element.get("xml_path"):
        related["xml_path"] = element["xml_path"]
    return related


def extract_line_elements(slide_xml: str) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for source_kind_index, match in enumerate(
        re.finditer(r"<line\b([^>]*?)(/?)>", slide_xml), start=1
    ):
        attrs = match.group(1)
        source_id = extract_attribute(attrs, "id") or None
        start_x = extract_numeric_attribute(attrs, "startX")
        start_y = extract_numeric_attribute(attrs, "startY")
        end_x = extract_numeric_attribute(attrs, "endX")
        end_y = extract_numeric_attribute(attrs, "endY")
        if any(value is None for value in (start_x, start_y, end_x, end_y)):
            continue
        line_alpha = extract_numeric_attribute(attrs, "alpha")
        base_alpha = line_alpha if line_alpha is not None else 1
        border_alpha = 1
        if match.group(2) != "/":
            close_index = slide_xml.find("</line>", match.end())
            body = slide_xml[match.end() : close_index] if close_index != -1 else ""
            border_attrs = extract_tag_attributes(body, "border")
            color_alpha = extract_color_alpha(extract_attribute(border_attrs, "color"))
            if isinstance(color_alpha, (int, float)):
                border_alpha = color_alpha
        elements.append(
            {
                "id": source_id or f"line-{len(elements) + 1}",
                "_source_id": source_id,
                "kind": "line",
                "type": "line",
                "x": min(start_x, end_x),
                "y": min(start_y, end_y),
                "width": abs(end_x - start_x),
                "height": abs(end_y - start_y),
                "startX": start_x,
                "startY": start_y,
                "endX": end_x,
                "endY": end_y,
                "rotation": 0,
                "alpha": base_alpha * border_alpha,
                "order": len(elements),
                "_source_kind_index": source_kind_index,
            }
        )
    return elements


def normalize_issue(
    issue: dict[str, Any],
    slide_number: int | None,
    elements_by_ref: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(issue)
    element_refs = list(dict.fromkeys(normalized.get("elements", [])))
    resolved_elements = [
        elements_by_ref[element_ref]
        for element_ref in element_refs
        if element_ref in elements_by_ref
    ]
    element_locators = [
        source_element_id(elements_by_ref[element_ref]) or element_ref
        if element_ref in elements_by_ref
        else element_ref
        for element_ref in element_refs
    ]
    element_ids = [
        source_id
        for element in resolved_elements
        if (source_id := source_element_id(element)) is not None
    ]
    normalized["schema_version"] = "2.0"
    normalized["elements"] = element_locators
    normalized["element_ids"] = element_ids
    normalized["target"] = {
        **({"slide_number": slide_number} if slide_number is not None else {}),
        **normalized.get("target", {}),
    }
    normalized["rule"] = issue_rule(normalized)
    normalized["measurement"] = issue_measurement(issue, elements_by_ref)
    normalized["related_objects"] = [related_object(element) for element in resolved_elements]
    if normalized["code"] == "sparse_container_content":
        ratio = normalized["measurement"]["content_coverage_ratio"]
        threshold = normalized["rule"]["threshold"]
        container_locator = (
            normalized["target"].get("container_id")
            or normalized["target"].get("container_xml_path")
            or "unknown"
        )
        normalized.setdefault(
            "message",
            f"large card {container_locator} content coverage {ratio:.1%} is below {threshold:.1%}",
        )
        normalized.setdefault(
            "hint",
            "Review the rendered screenshot; add or enlarge meaningful content if the whitespace is not intentional.",
        )
    elif normalized["code"] == "sparse_slide_content":
        ratio = normalized["measurement"]["content_coverage_ratio"]
        threshold = normalized["rule"]["threshold"]
        normalized.setdefault(
            "message",
            f"slide visible content coverage {ratio:.1%} is below {threshold:.1%}",
        )
        normalized.setdefault(
            "hint",
            "Review the rendered screenshot to decide whether the page is intentionally sparse.",
        )
    else:
        normalized.setdefault("message", normalized["code"].replace("_", " "))
    normalized.setdefault(
        "hint", "Inspect the reported elements and adjust them to satisfy the rule comparison."
    )
    if any(related.get("xml_path") for related in normalized["related_objects"]):
        hint = normalized["hint"]
        if not hint.startswith(XML_PATH_HINT_PREFIX):
            normalized["hint"] = f"{XML_PATH_HINT_PREFIX} {hint}"
    return normalized


def slide_status(errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if errors:
        return "blocked"
    if warnings:
        return "needs_screenshot_review"
    return "passed"


def is_slide_scoped_sxsd_issue(issue: dict[str, Any], root_name: str) -> bool:
    if issue.get("code") == "sxsd_unsupported_declaration":
        return False
    if root_name == "slide":
        return True
    path = issue.get("path")
    if not isinstance(path, str):
        return False
    if path.startswith("presentation/slide/"):
        return True
    return path == "presentation/slide" and (
        issue.get("attr") is not None or issue.get("code") == "sxsd_invalid_namespace"
    )


def build_result(
    source_path: str | None,
    slide_size: dict[str, int | float],
    top_level_issues: list[dict[str, Any]],
    slides: list[dict[str, Any]],
) -> dict[str, Any]:
    document_errors = [issue for issue in top_level_issues if issue["level"] == "error"]
    document_warnings = [issue for issue in top_level_issues if issue["level"] == "warning"]
    document_infos = [issue for issue in top_level_issues if issue["level"] == "info"]
    error_count = len(document_errors) + sum(len(slide["errors"]) for slide in slides)
    warning_count = len(document_warnings) + sum(len(slide["warnings"]) for slide in slides)
    info_count = len(document_infos) + sum(len(slide["infos"]) for slide in slides)
    all_errors = document_errors + [issue for slide in slides for issue in slide["errors"]]
    all_warnings = document_warnings + [issue for slide in slides for issue in slide["warnings"]]
    status = slide_status(all_errors, all_warnings)
    result: dict[str, Any] = {
        "schema_version": "2.0",
        "tool": "xml_lint",
        "file": source_path,
        "slide_size": slide_size,
        "summary": {
            "slide_count": len(slides),
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "status": status,
            "release_ready": error_count == 0,
            "screenshot_review_required": warning_count > 0,
        },
        "document": {
            "errors": document_errors,
            "warnings": document_warnings,
            "infos": document_infos,
        },
        "slides": slides,
    }
    if top_level_issues:
        result["issues"] = top_level_issues
    return result


def lint_xml(xml: str, source_path: str | None = None) -> dict[str, Any]:
    root, xml_error = parse_xml_root(xml)
    if xml_error:
        issue = normalize_issue(xml_error, None, {})
        return build_result(
            source_path,
            {"width": 960, "height": 540},
            [issue],
            [],
        )
    if root is None:
        raise AssertionError("parse_xml_root must return a root or error")

    namespace_issues = validate_sml_tag_prefixes(xml)
    root_name = xml_local_name(root.tag)
    sxsd_issues = validate_sxsd_document(xml, root)
    iconpark_issues = validate_iconpark_icon_types(root)
    chart_dimension_issues = validate_chart_value_semantics(root)
    top_level_issues = [
        normalize_issue(issue, None, {})
        for issue in [
            *namespace_issues,
            *[
                issue
                for issue in sxsd_issues
                if not is_slide_scoped_sxsd_issue(issue, root_name)
            ],
            *iconpark_issues,
            *chart_dimension_issues,
        ]
    ]
    if any(issue["level"] == "error" for issue in top_level_issues):
        return build_result(
            source_path,
            {"width": 960, "height": 540},
            top_level_issues,
            [],
        )

    presentation = parse_presentation(root)
    slide_roots = presentation["slide_roots"]
    slides: list[dict[str, Any]] = []
    presentation_id_elements: list[dict[str, Any]] = []
    presentation_elements_by_ref: dict[str, dict[str, Any]] = {}
    for index, slide_xml in enumerate(presentation["slides"]):
        slide_number = index + 1
        slide_root = slide_roots[index]
        slide_sxsd_issues = [
            normalize_issue(issue, slide_number, {})
            for issue in validate_sxsd_document(slide_xml, slide_root)
        ]
        slide_sxsd_errors = [
            issue for issue in slide_sxsd_issues if issue["level"] == "error"
        ]
        if slide_sxsd_errors:
            slide_sxsd_warnings = [
                issue for issue in slide_sxsd_issues if issue["level"] == "warning"
            ]
            slides.append(
                {
                    "slide_number": slide_number,
                    "status": slide_status(slide_sxsd_errors, slide_sxsd_warnings),
                    "element_count": 0,
                    "errors": slide_sxsd_errors,
                    "warnings": slide_sxsd_warnings,
                    "infos": [],
                    "issues": slide_sxsd_issues,
                }
            )
            continue

        geometry = lint_slide(
            slide_xml,
            slide_number,
            presentation["width"],
            presentation["height"],
        )
        density_elements = extract_density_elements(slide_xml, slide_number)
        id_elements = extract_source_id_elements(slide_xml, slide_number)
        presentation_id_elements.extend(id_elements)
        extra_elements = [
            element for element in density_elements if element["kind"] in {"icon", "polyline", "line"}
        ]
        elements_by_ref = {
            element_ref(element): element for element in density_elements
        }
        visible_element_count = len(elements_by_ref)
        for element in id_elements:
            elements_by_ref.setdefault(element_ref(element), element)
        # geometry["elements"] are the exact objects should_flag_overlap/detect_elements_out_of_canvas
        # selected inside lint_slide; prefer them so measurement/related_objects stay consistent
        # with whatever actually triggered the issue, instead of density_elements' separate re-parse.
        elements_by_ref.update(
            {element_ref(element): element for element in geometry["elements"]}
        )
        presentation_elements_by_ref.update(
            {
                element_ref(element): elements_by_ref[element_ref(element)]
                for element in id_elements
            }
        )
        extra_overflow_issues = detect_elements_out_of_canvas(
            extra_elements,
            presentation["width"],
            presentation["height"],
        )
        raw_issues = [
            *geometry["issues"],
            *extra_overflow_issues,
            *detect_duplicate_element_ids(id_elements),
            *detect_blank_slide(
                density_elements,
                slide_number,
                presentation["width"],
                presentation["height"],
            ),
            *detect_sparse_container_content(
                density_elements,
                slide_number,
                presentation["width"],
                presentation["height"],
            ),
            *detect_sparse_slide_content(
                density_elements,
                slide_number,
                presentation["width"],
                presentation["height"],
            ),
        ]
        issues = [
            *slide_sxsd_issues,
            *[
                normalize_issue(issue, slide_number, elements_by_ref)
                for issue in raw_issues
            ],
        ]
        errors = [issue for issue in issues if issue["level"] == "error"]
        warnings = [issue for issue in issues if issue["level"] == "warning"]
        infos = [issue for issue in issues if issue["level"] == "info"]
        slides.append(
            {
                "slide_number": slide_number,
                "status": slide_status(errors, warnings),
                "element_count": visible_element_count,
                "errors": errors,
                "warnings": warnings,
                "infos": infos,
                "issues": issues,
            }
        )

    top_level_issues.extend(
        normalize_issue(issue, None, presentation_elements_by_ref)
        for issue in detect_duplicate_element_ids(
            presentation_id_elements, cross_slide_only=True
        )
    )

    return build_result(
        source_path,
        {"width": presentation["width"], "height": presentation["height"]},
        top_level_issues,
        slides,
    )


def print_usage() -> None:
    print("Usage:\n  python3 xml_lint.py --input <xml_file.xml>", file=sys.stderr)


def run_cli(argv: list[str] | None = None) -> None:
    options = parse_args(argv or sys.argv[1:])
    if options.get("help") or options.get("--help"):
        print_usage()
        raise SystemExit(0)
    if not options.get("input"):
        print_usage()
        fail("--input is required")
    requested_path = options["input"]
    resolved_path = Path(requested_path).resolve()
    result = lint_xml(read_file(resolved_path), requested_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["summary"]["error_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        run_cli()
    except XmlLayoutLintError as error:
        print(f"xml-lint error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
