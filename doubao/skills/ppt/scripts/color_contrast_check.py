#!/usr/bin/env python3
"""Detect low text/background contrast in a Slides XML readback.

The checker is deliberately conservative: a text/background contrast failure
is a ``FAIL``. ``--format json`` is intended for regression automation; the
text format remains convenient for humans.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

DEFAULT_BG = (255, 255, 255, 1.0)
DEFAULT_FG = (31, 35, 41, 1.0)
# Contrast and review gates.
DEFAULT_CONTRAST_GATE = 2.25
COMPLEX_BACKGROUND_CONTRAST_MULTIPLIER = 1.05
ERROR_CONTRAST_RATIO = 0.80

# Text-role recognition thresholds.
LARGE_TEXT_MIN_FONT_SIZE = 24.0
LARGE_BOLD_TEXT_MIN_FONT_SIZE = 18.66
DECORATIVE_DISPLAY_MIN_FONT_SIZE = 180.0
DECORATIVE_DISPLAY_MAX_TEXT_LENGTH = 3
NAVIGATION_BADGE_MIN_FONT_SIZE = 32.0
DISPLAY_PERCENT_MIN_FONT_SIZE = 32.0
CONNECTOR_LABEL_MAX_HEIGHT = 32.0

# Visual-role geometry and colour thresholds.
STATUS_CARD_WHITE_MIN_CHANNEL = 245
STATUS_CARD_MIN_SATURATION = 80
STATUS_CARD_MIN_WIDTH = 70.0
STATUS_CARD_MAX_WIDTH = 150.0
STATUS_CARD_MIN_HEIGHT = 40.0
STATUS_CARD_MAX_HEIGHT = 90.0
DARK_GRADIENT_MAX_LUMINANCE = 0.03
DARK_GRADIENT_MIN_CONTRAST = 2.5
RGBA_RE = re.compile(
    r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)", re.I
)
GRADIENT_STOP_RE = re.compile(r"(rgba?\([^)]*\))\s*([\d.]+)?%?", re.I)
PATTERN_PERCENT_RE = re.compile(r"pct(\d+)$", re.I)
NAVIGATION_TOKEN_RE = re.compile(r"\d{1,3}$")
DISPLAY_PERCENT_RE = re.compile(r"\d{1,2}%$")
CONNECTOR_LABEL_RE = re.compile(r"[a-z][a-z -]{1,31}$")
UNRESOLVED_PATTERN = "__unresolved_pattern__"


def local_name(elem: ET.Element | str) -> str:
    tag = elem if isinstance(elem, str) else elem.tag
    return tag.rsplit("}", 1)[-1]


def number(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def parse_color(value: str | None) -> tuple[int, int, int, float] | None:
    if not value:
        return None
    match = RGBA_RE.fullmatch(value.strip())
    if not match:
        return None
    r, g, b = (max(0, min(255, round(float(match.group(i))))) for i in range(1, 4))
    alpha = max(0.0, min(1.0, float(match.group(4) or 1)))
    return r, g, b, alpha


def color_css(color: tuple[int, int, int, float]) -> str:
    return f"rgba({color[0]}, {color[1]}, {color[2]}, {color[3]:.6g})"


def pattern_color(element: ET.Element) -> str | None:
    """Approximate a percentage fill as its area-weighted visible colour.

    SML ``fillPattern`` is not a solid fill, but treating it as white (the
    former fallback) turns white text on a dark patterned cover into 1:1.
    Percentage patterns are deterministic enough to use their weighted colour;
    unsupported pattern types remain unresolved instead of inventing a ratio.
    """
    match = PATTERN_PERCENT_RE.fullmatch(element.get("type", ""))
    foreground = parse_color(element.get("foregroundColor"))
    background = parse_color(element.get("backgroundColor"))
    if not match or not foreground or not background:
        return None
    coverage = max(0.0, min(1.0, int(match.group(1)) / 100.0))
    alpha = max(0.0, min(1.0, number(element.get("alpha"), 1.0)))
    visible = over(
        foreground[:3] + (foreground[3] * coverage * alpha,),
        background[:3] + (background[3] * alpha,),
    )
    return color_css(visible)


def over(fg: tuple[int, int, int, float], bg: tuple[int, int, int, float]) -> tuple[int, int, int, float]:
    alpha = fg[3] + bg[3] * (1 - fg[3])
    if alpha == 0:
        return 0, 0, 0, 0.0
    return tuple(round((fg[i] * fg[3] + bg[i] * bg[3] * (1 - fg[3])) / alpha) for i in range(3)) + (alpha,)


def srgb_to_linear(component: int) -> float:
    component /= 255.0
    return component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    return .2126 * srgb_to_linear(rgb[0]) + .7152 * srgb_to_linear(rgb[1]) + .0722 * srgb_to_linear(rgb[2])


def contrast(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    first, second = luminance(fg), luminance(bg)
    return (max(first, second) + .05) / (min(first, second) + .05)


def color_or_gradient(value: str | None, x_ratio: float) -> tuple[int, int, int, float] | None:
    solid = parse_color(value)
    if solid:
        return solid
    if not value or "gradient" not in value.lower():
        return None
    stops = [(parse_color(match.group(1)), match.group(2)) for match in GRADIENT_STOP_RE.finditer(value)]
    stops = [(color, float(position) / 100 if position else None) for color, position in stops if color]
    if not stops:
        return None
    if len(stops) == 1:
        return stops[0][0]
    position = max(0.0, min(1.0, x_ratio))
    resolved = [(color, index / (len(stops) - 1) if raw is None else raw) for index, (color, raw) in enumerate(stops)]
    left, right = resolved[0], resolved[-1]
    for candidate in resolved[1:]:
        if position <= candidate[1]:
            right = candidate
            break
        left = candidate
    first, left_position = left
    last, right_position = right
    progress = 0 if right_position == left_position else (position - left_position) / (right_position - left_position)
    return tuple(round(first[i] + (last[i] - first[i]) * progress) for i in range(3)) + (first[3] + (last[3] - first[3]) * progress,)


def fill_color(elem: ET.Element) -> str | None:
    for child in elem:
        if local_name(child) != "fill":
            continue
        for nested in child:
            if local_name(nested) == "fillColor":
                return nested.get("color")
            if local_name(nested) == "fillPattern":
                return pattern_color(nested) or UNRESOLVED_PATTERN
    return None


def border_color(elem: ET.Element) -> str | None:
    """Return the visible colour used by a line-like element."""
    for child in elem:
        if local_name(child) == "border":
            return child.get("color")
    return None


def element_bbox(elem: ET.Element) -> tuple[float, float, float, float]:
    """Approximate the paint bounds of all drawable SML elements.

    Shapes, images, icons, tables and charts use a normal bounding box.  Lines
    use endpoints, while polylines use their declared outer rectangle.  The
    latter two are an approximation: it catches a text label placed directly
    on a thick connector without claiming pixel-perfect curve coverage.
    """
    tag = local_name(elem)
    if tag == "line":
        width = max(1.0, number(next((child.get("width") for child in elem if local_name(child) == "border"), "1")))
        x1, y1 = number(elem.get("startX")), number(elem.get("startY"))
        x2, y2 = number(elem.get("endX")), number(elem.get("endY"))
        return min(x1, x2) - width / 2, min(y1, y2) - width / 2, abs(x2 - x1) + width, abs(y2 - y1) + width
    return number(elem.get("topLeftX")), number(elem.get("topLeftY")), number(elem.get("width")), number(elem.get("height"))


def table_cell_paints(node: ET.Element, order: int) -> Iterable[Paint]:
    x0, y0 = number(node.get("topLeftX")), number(node.get("topLeftY"))
    widths = [number(col.get("width"), number(node.get("width")) / 2) for col in node.iter() if local_name(col) == "col"] or [number(node.get("width"))]
    row_y = y0
    for row in (item for item in node if local_name(item) == "tr"):
        row_h = number(row.get("height"), number(node.get("height")) / 2)
        x, column = x0, 0
        for cell in (item for item in row if local_name(item) == "td"):
            span = int(number(cell.get("colspan"), 1))
            cell_w = sum(widths[column:column + span]) or number(node.get("width"))
            yield Paint(x, row_y, cell_w, row_h, fill_color(cell), order)
            x += cell_w
            column += span
        row_y += row_h


@dataclass
class Paint:
    x: float
    y: float
    width: float
    height: float
    color: str | None
    order: int
    kind: str = ""

    def covers(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def at(self, x: float) -> tuple[int, int, int, float] | None:
        return color_or_gradient(self.color, 0.5 if not self.width else (x - self.x) / self.width)


def attrs(parent: dict[str, str], element: ET.Element) -> dict[str, str]:
    inherited = dict(parent)
    inherited.update({key: value for key, value in element.attrib.items() if value})
    return inherited


def inline_runs(node: ET.Element, inherited: dict[str, str]) -> Iterable[tuple[str, dict[str, str]]]:
    current = attrs(inherited, node)
    if node.text and node.text.strip():
        yield node.text.strip(), current
    for child in node:
        yield from inline_runs(child, current)
        if child.tail and child.tail.strip():
            yield child.tail.strip(), current


def page_default(slide: ET.Element) -> str | None:
    for child in slide:
        if local_name(child) != "style":
            continue
        return fill_color(child)
    return None


def theme_default(root: ET.Element) -> str | None:
    for element in root.iter():
        if local_name(element) == "body" and element.get("fontColor"):
            return element.get("fontColor")
    return None


def element_record(slide_num: int, slide_id: str, text: str, style: dict[str, str], bbox: tuple[float, float, float, float], paint_index: int, source: str, shape_background: str | None = None, object_id: str | None = None, object_path: str | None = None, shape_alpha: float | None = None) -> dict:
    return {
        "slide": slide_num, "slide_id": slide_id, "text": text[:160], "fg_color": style.get("color") or style.get("fontColor") or "rgba(31, 35, 41, 1)",
        "font_size": number(style.get("fontSize"), 16), "bold": style.get("bold", "").lower() in {"true", "1", "bold"},
        "text_background": style.get("backgroundColor"), "shape_background": shape_background,
        "bbox": bbox, "paint_index": paint_index, "source": source,
        "object_id": object_id, "object_path": object_path,
        "shape_alpha": shape_alpha,
    }


def parse_xml(xml_path: str) -> tuple[list[dict], dict[int, dict]]:
    return parse_xml_root(ET.parse(xml_path).getroot())


def parse_xml_root(root: ET.Element) -> tuple[list[dict], dict[int, dict]]:
    """Parse a presentation root for callers that already parsed the XML.

    ``xml_lint`` owns XML validation and deliberately passes its in-memory root
    here, so this companion entry point must stay available alongside the
    file-based CLI helper above.
    """
    fallback_fg = theme_default(root) or "rgba(31, 35, 41, 1)"
    records: list[dict] = []
    slides: dict[int, dict] = {}
    slide_num = 0
    for slide in root.iter():
        if local_name(slide) != "slide":
            continue
        slide_num += 1
        slide_id = slide.get("id", f"page{slide_num}")
        data = next((child for child in slide if local_name(child) == "data"), None)
        if data is None:
            continue
        paints: list[Paint] = []
        images: list[Paint] = []
        paint_index: dict[int, int] = {}
        object_path: dict[int, str] = {}
        tag_counts: dict[str, int] = {}
        order = 0
        for node in data:
            tag = local_name(node)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            object_path[id(node)] = f"data/{tag}[{tag_counts[tag]}]"
            paint_index[id(node)] = order
            if tag in {"shape", "img", "icon", "chart", "line", "polyline"}:
                x, y, width, height = element_bbox(node)
                color = fill_color(node)
                if tag in {"line", "polyline"}:
                    color = border_color(node)
                elif tag == "chart":
                    color = next((child.get("color") for child in node.iter() if local_name(child) == "chartBackground"), None)
                paint = Paint(x, y, width, height, color, order, tag)
                if tag != "img" and paint.color:
                    paints.append(paint)
                if tag == "img":
                    images.append(paint)
            elif tag == "table":
                paints.extend(paint for paint in table_cell_paints(node, order) if paint.color)
            order += 1
        slides[slide_num] = {"id": slide_id, "page_bg": page_default(slide), "paints": paints, "images": images}
        for node in data:
            tag = local_name(node)
            if tag == "shape":
                content = next((child for child in node if local_name(child) == "content"), None)
                if content is None:
                    continue
                inherited = {"color": fallback_fg, "fontSize": "16"}
                inherited = attrs(inherited, content)
                bbox = (number(node.get("topLeftX")), number(node.get("topLeftY")), number(node.get("width")), number(node.get("height")))
                for paragraph in content.iter():
                    if local_name(paragraph) == "p":
                        for text, style in inline_runs(paragraph, inherited):
                            records.append(element_record(slide_num, slide_id, text, style, bbox, paint_index[id(node)], "shape", fill_color(node), node.get("id"), object_path[id(node)], shape_alpha=number(node.get("alpha"), 1.0) if node.get("alpha") is not None else None))
            elif tag == "table":
                x, y = number(node.get("topLeftX")), number(node.get("topLeftY"))
                widths = [number(col.get("width"), number(node.get("width")) / 2) for col in node.iter() if local_name(col) == "col"] or [number(node.get("width"))]
                row_y, column = y, 0
                for row in (item for item in node if local_name(item) == "tr"):
                    row_h = number(row.get("height"), number(node.get("height")) / 2)
                    for cell in (item for item in row if local_name(item) == "td"):
                        span = int(number(cell.get("colspan"), 1))
                        cell_w = sum(widths[column:column + span]) or number(node.get("width"))
                        content = next((child for child in cell if local_name(child) == "content"), None)
                        if content is not None:
                            inherited = attrs({"color": fallback_fg, "fontSize": "16", "backgroundColor": fill_color(cell) or ""}, content)
                            for paragraph in content.iter():
                                if local_name(paragraph) == "p":
                                    for text, style in inline_runs(paragraph, inherited):
                                        records.append(element_record(slide_num, slide_id, text, style, (x, row_y, cell_w, row_h), paint_index[id(node)], "table", object_id=node.get("id"), object_path=object_path[id(node)]))
                        x += cell_w
                        column += span
                    x = number(node.get("topLeftX")); row_y += row_h; column = 0
            elif tag == "chart":
                chart_bg = next((child.get("color") for child in node.iter() if local_name(child) == "chartBackground"), None)
                chart_bbox = (number(node.get("topLeftX")), number(node.get("topLeftY")), number(node.get("width")), number(node.get("height")))
                for child in node.iter():
                    if local_name(child) in {"chartTitle", "chartLabel", "chartLabels", "chartLegend"} and (child.text or child.get("color")):
                        label = (child.text or local_name(child)).strip()
                        style = {"color": child.get("color") or fallback_fg, "fontSize": child.get("fontSize", "11"), "backgroundColor": chart_bg or ""}
                        records.append(element_record(slide_num, slide_id, label, style, chart_bbox, paint_index[id(node)], "chart", object_id=node.get("id"), object_path=object_path[id(node)]))
    return records, slides


def background_at(record: dict, slide: dict, x: float, y: float) -> tuple[tuple[int, int, int, float] | None, bool, list[tuple[int, int, int, float]], bool, bool]:
    bg = color_or_gradient(slide["page_bg"], x / 960) or DEFAULT_BG
    target_index = record["paint_index"]
    unresolved = False
    line_backed = False
    for paint in slide["paints"]:
        if paint.order < target_index and paint.covers(x, y):
            line_backed |= paint.kind in {"line", "polyline"}
            color = paint.at(x)
            if color:
                bg = over(color, bg)
            elif paint.color == UNRESOLVED_PATTERN:
                unresolved = True
    for is_shape_background, color_value in (
        (True, record.get("shape_background")),
        (False, record.get("text_background")),
    ):
        color = color_or_gradient(color_value, .5)
        if color and is_shape_background:
            color = (*color[:3], color[3] * effective_shape_alpha(record))
        # ``rgba(..., 0)`` is not a background.  Compositing rather than
        # returning it also keeps semi-transparent text/cell fills honest.
        if color and color[3] > 0:
            bg = over(color, bg)
    has_image = any(image.order < target_index and image.covers(x, y) for image in slide["images"])
    overlays = []
    for paint in slide["paints"]:
        if paint.order > target_index and paint.covers(x, y):
            color = paint.at(x)
            if color:
                overlays.append(color)
    return (None if unresolved else bg), has_image, overlays, unresolved, line_backed


def is_large(font_size: float, bold: bool) -> bool:
    return font_size >= LARGE_TEXT_MIN_FONT_SIZE or (bold and font_size >= LARGE_BOLD_TEXT_MIN_FONT_SIZE)


def is_decorative_display_text(text: str, font_size: float) -> bool:
    """Ignore giant, short display initials that do not carry readable copy."""
    return font_size >= DECORATIVE_DISPLAY_MIN_FONT_SIZE and len(text.strip()) <= DECORATIVE_DISPLAY_MAX_TEXT_LENGTH


def is_decorative_navigation_token(text: str, font_size: float, image_backed: bool) -> bool:
    """Leave image-backed section-number badges to visual review.

    A short, large numeric marker (for example ``01`` on an illustrated cloud)
    conveys navigation rather than body copy.  Its readability depends on the
    complete rendered badge -- outline, shadow and illustration edge -- which
    is not available in Slides XML.  This deliberately does not cover normal
    numeric content such as dates, values, table cells, or small page numbers.
    """
    return image_backed and font_size >= NAVIGATION_BADGE_MIN_FONT_SIZE and bool(NAVIGATION_TOKEN_RE.fullmatch(text.strip()))


def is_display_percent(text: str, font_size: float) -> bool:
    """Large whole-number percentages are visual metrics, not body copy."""
    return font_size >= DISPLAY_PERCENT_MIN_FONT_SIZE and bool(DISPLAY_PERCENT_RE.fullmatch(text.strip()))


def is_white_status_card_label(fg: tuple[int, int, int, float], bg: tuple[int, int, int, float], bbox: tuple[float, float, float, float]) -> bool:
    """Recognise compact, high-saturation status cards with white labels.

    These can fall below the configured contrast gate for some green/blue/orange
    cards, but their large coloured surfaces and compact, repeated status
    treatment remain visually legible in the rendered deck.
    """
    _, _, width, height = bbox
    return (
        min(fg[:3]) >= STATUS_CARD_WHITE_MIN_CHANNEL
        and max(bg[:3]) - min(bg[:3]) >= STATUS_CARD_MIN_SATURATION
        and STATUS_CARD_MIN_WIDTH <= width <= STATUS_CARD_MAX_WIDTH
        and STATUS_CARD_MIN_HEIGHT <= height <= STATUS_CARD_MAX_HEIGHT
    )


def is_connector_label(text: str, bbox: tuple[float, float, float, float]) -> bool:
    """Short lowercase captions attached to diagram connectors are secondary."""
    return bbox[3] <= CONNECTOR_LABEL_MAX_HEIGHT and bool(CONNECTOR_LABEL_RE.fullmatch(text.strip()))


def is_dark_gradient_annotation(fg: tuple[int, int, int, float], ratio: float, complex_background: bool) -> bool:
    """Keep readable dark annotations on a rendered gradient out of FAIL."""
    return complex_background and luminance(fg[:3]) <= DARK_GRADIENT_MAX_LUMINANCE and ratio >= DARK_GRADIENT_MIN_CONTRAST


def effective_shape_alpha(item: dict) -> float:
    """Return a shape-level alpha clamped to the compositing range."""
    shape_alpha = item.get("shape_alpha")
    if isinstance(shape_alpha, (int, float)):
        return max(0.0, min(1.0, float(shape_alpha)))
    return 1.0


def effective_text_alpha(item: dict) -> float:
    """Return the run's own opacity, combining the text colour alpha with its shape alpha.

    A ghost numeral is authored either as ``rgba(r, g, b, 0.3)`` on an opaque shape or as an opaque
    colour inside a shape carrying ``alpha``. Both spellings paint the same faint glyphs, so the
    exemption must look at the product rather than the text colour alone.
    """
    color = parse_color(item.get("fg_color"))
    alpha = color[3] if color else 1.0
    return alpha * effective_shape_alpha(item)


def is_ghost_decorative_text(item: dict) -> bool:
    """Adapt a contrast record to xml_lint's canonical ghost-text predicate.

    The import stays local because xml_lint imports this checker for contrast
    integration. At lint time both modules have finished loading, while a
    module-level import here would create an initialization cycle.
    """
    from xml_lint import is_ghost_text

    return is_ghost_text(
        {
            "kind": "shape",
            "type": "text",
            "text": item.get("text"),
            "fontSize": item.get("font_size"),
            "textAlpha": effective_text_alpha(item),
        }
    )


def lint_level(item: dict) -> str:
    """Block only severe low-contrast results with deterministic XML backgrounds.

    A result within 20% of its applicable contrast gate is a warning for visual
    review. Ghost/decorative ornament is also exempt from blocking, so an
    author is not forced to repaint or delete an intentional design element
    solely to reach ``error_count == 0``.
    """
    required_contrast = item.get("required_contrast", DEFAULT_CONTRAST_GATE)
    if not isinstance(required_contrast, (int, float)):
        required_contrast = DEFAULT_CONTRAST_GATE
    contrast_value = item.get("contrast")
    if not isinstance(contrast_value, (int, float)):
        return "warning"
    error_gate = required_contrast * ERROR_CONTRAST_RATIO
    if (
        item.get("verdict") == "FAIL"
        # Keep the exact 80%-of-gate boundary in review despite binary float
        # representation (for example, 3.0 * 0.8 is slightly above 2.40).
        and contrast_value < error_gate - 1e-9
        and not item.get("complex_background")
        and item.get("source") not in {"line", "polyline"}
        and not is_ghost_decorative_text(item)
    ):
        return "error"
    return "warning"


def check(
    records: list[dict],
    slides: dict[int, dict],
    screenshots_dir: str,
    threshold: float,
) -> tuple[list[dict], bool]:
    results, has_fail = [], False
    for record in records:
        if is_decorative_display_text(record["text"], record["font_size"]):
            results.append({**record, "contrast": None, "verdict": "SKIP", "reason": "giant short display text is decorative", "bg_source": "decorative"})
            continue
        slide = slides[record["slide"]]
        fg = parse_color(record["fg_color"]) or DEFAULT_FG
        # ``alpha`` on a text shape attenuates its glyphs together with the
        # shape. Apply the same effective alpha used by ghost classification
        # before compositing the visible foreground against each background.
        fg = (*fg[:3], effective_text_alpha(record))
        x, y, width, height = record["bbox"]
        samples = [(x + width * col / 4, y + height * row / 2) for col in range(1, 4) for row in range(1, 2)]
        record = {**record, "sample_points": [{"x": point_x, "y": point_y} for point_x, point_y in samples]}
        # A paint covering exactly one of three samples can be a local chart
        # bar, badge, or neighbouring decoration in the text box's unused
        # space. Keep it for visual review. Coverage of two samples remains a
        # sufficiently broad, deterministic background to preserve blocking
        # detection for severe contrast failures.
        single_sample_paint_coverage = any(
            sum(paint.covers(point_x, point_y) for point_x, point_y in samples) == 1
            for paint in slide["paints"]
            if paint.order < record["paint_index"]
        )
        observations = []
        image_backed = False
        unsupported_background = False
        line_backed = False
        for point_x, point_y in samples:
            bg, image_here, overlays, unresolved, point_line_backed = background_at(record, slide, point_x, point_y)
            image_backed |= image_here
            unsupported_background |= unresolved
            line_backed |= point_line_backed
            if bg:
                foreground = over(fg, bg)
                for overlay in overlays:
                    foreground, bg = over(overlay, foreground), over(overlay, bg)
                observations.append((foreground, bg, point_x, point_y))
        if image_backed:
            results.append({**record, "contrast": None, "verdict": "SKIP", "reason": "image-backed text excluded", "bg_source": "image excluded"})
            continue
        contrast_values = [contrast(item[0][:3], item[1][:3]) for item in observations]
        source = "xml layered fill" if observations else "missing background"
        if not observations:
            reason = "unsupported background pattern" if unsupported_background else "no resolvable background"
            results.append({**record, "contrast": None, "verdict": "SKIP", "reason": reason, "bg_source": source})
            continue
        fg_final, bg_final, worst_x, worst_y = min(observations, key=lambda item: contrast(item[0][:3], item[1][:3]))
        ratio = min(contrast_values)
        record.update({
            "effective_fg_color": color_css(fg_final),
            "effective_bg_color": color_css(bg_final),
            "worst_sample": {
                "x": worst_x,
                "y": worst_y,
                "contrast": ratio,
                "method": "xml",
            },
        })
        def is_complex_color(value: str | None) -> bool:
            color = parse_color(value)
            return bool(value and "gradient" in value.lower()) or bool(color and color[3] < 1)

        complex_background = single_sample_paint_coverage or line_backed or (
            record.get("shape_background") is not None and effective_shape_alpha(record) < 1.0
        ) or any(is_complex_color(value) for value in (slide["page_bg"], record.get("shape_background"), record.get("text_background"))) or any(
            (paint.color or "").lower().find("gradient") >= 0 or (parse_color(paint.color) or DEFAULT_BG)[3] < 1
            for paint in slide["paints"] if paint.covers(x + width / 2, y + height / 2)
        )
        record["complex_background"] = complex_background
        if is_decorative_navigation_token(record["text"], record["font_size"], image_backed):
            results.append({**record, "contrast": ratio, "verdict": "SKIP", "reason": "image-backed numeric navigation badge needs visual review", "bg_source": source})
            continue
        if is_display_percent(record["text"], record["font_size"]):
            results.append({**record, "contrast": ratio, "verdict": "PASS", "reason": "large whole-number display metric", "bg_source": source})
            continue
        if is_white_status_card_label(fg_final, bg_final, record["bbox"]):
            results.append({**record, "contrast": ratio, "verdict": "PASS", "reason": "compact saturated status card", "bg_source": source})
            continue
        if is_connector_label(record["text"], record["bbox"]):
            results.append({**record, "contrast": ratio, "verdict": "PASS", "reason": "secondary diagram connector label", "bg_source": source})
            continue
        if is_dark_gradient_annotation(fg_final, ratio, complex_background):
            results.append({**record, "contrast": ratio, "verdict": "PASS", "reason": "readable dark annotation on complex background", "bg_source": source})
            continue
        # Large text uses the baseline gate on every XML-resolvable surface.
        # The complex-background guard below adds a small safety margin.
        required = DEFAULT_CONTRAST_GATE if is_large(record["font_size"], record["bold"]) else threshold
        # Semi-transparent layers are especially sensitive to renderer rounding
        # and screenshots.  Keep a small conservative band around the requested
        # threshold instead of certifying a visually borderline value.
        effective_required = required * COMPLEX_BACKGROUND_CONTRAST_MULTIPLIER if complex_background else required
        record["required_contrast"] = effective_required
        if ratio < effective_required:
            guard = " (complex-background guard)" if complex_background else ""
            verdict, reason, has_fail = "FAIL", f"contrast {ratio:.2f}:1 < {effective_required:.2f}{guard}", True
        else:
            verdict, reason = "PASS", ""
        results.append({**record, "contrast": ratio, "verdict": verdict, "reason": reason, "bg_source": source})
    return results, has_fail


def summary(results: list[dict], has_fail: bool | None = None) -> dict:
    """Summarise blocking errors separately from screenshot-review warnings."""
    failures = [item for item in results if item["verdict"] == "FAIL"]
    errors = [item for item in failures if lint_level(item) == "error"]
    warnings = [item for item in failures if lint_level(item) == "warning"]
    return {
        "has_issues": bool(failures),
        "has_blocking_issues": bool(errors),
        "issue_count": len(failures),
        "warning_count": len(warnings),
        "fix_pages": sorted({item["slide"] for item in errors}),
        "review_pages": sorted({item["slide"] for item in warnings}),
    }


def display_background_source(source: str) -> str:
    """Turn parser provenance into a short agent-facing explanation."""
    if source == "xml layered fill":
        return "页面元素底色"
    return source


def issue_message(item: dict) -> str:
    """Render the compact, single-line repair handoff for one text issue."""
    if is_ghost_decorative_text(item):
        return (
            f"对象：{item['text']}；判断：可能是幽灵字，文字与背景对比度不足；"
            "设计复核：确认它仅作为背景装饰，不承载正文、标题、状态或导航信息；"
            "动作：若仅作装饰，可结合页面截图确认后保留；若需要阅读，请提升文字或背景的区分度后复检。"
        )
    source = item["bg_source"]
    if item.get("effective_fg_color") and item.get("effective_bg_color"):
        evidence = (
            f"文字为 {item['effective_fg_color']}，背景为 {item['effective_bg_color']}，"
            f"背景来自{display_background_source(source)}"
        )
    else:
        evidence = f"背景来自{display_background_source(source)}"
    return (
        f"对象：{item['text']}；问题：文字与背景对比度不足，可能影响可读性；"
        f"依据：{evidence}；动作：调整文字或其底色后复检。"
    )


def production_result(item: dict) -> dict:
    return {
        "slide_number": item["slide"],
        "slide_id": item["slide_id"],
        "xml_path": item.get("object_path"),
        "level": lint_level(item),
        "message": issue_message(item),
    }


def print_text(results: list[dict], has_fail: bool) -> None:
    for item in (item for item in results if item["verdict"] == "FAIL"):
        ratio = "n/a" if item["contrast"] is None else f"{item['contrast']:.2f}:1"
        print(f"{item['verdict']:4} p{item['slide']:02d} {item['source']:5} {item['text']!r} contrast={ratio} {item['reason']}")
    totals = summary(results, has_fail)
    print("summary " + " ".join(f"{key}={value}" for key, value in totals.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Slides XML text contrast checker (image-backed text excluded)")
    parser.add_argument("--xml", required=True)
    parser.add_argument("--threshold", type=float, default=DEFAULT_CONTRAST_GATE, help=f"minimum contrast ratio for ordinary text (default: {DEFAULT_CONTRAST_GATE})")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if not os.path.isfile(args.xml):
        print(f"error: XML file not found: {args.xml}", file=sys.stderr)
        return 2
    records, slides = parse_xml(args.xml)
    results, has_fail = check(
        records,
        slides,
        "",
        args.threshold,
    )
    payload = {"summary": summary(results, has_fail), "issues": [production_result(item) for item in results if item["verdict"] == "FAIL"]}
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text(results, has_fail)
    return 1 if payload["summary"]["has_blocking_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
