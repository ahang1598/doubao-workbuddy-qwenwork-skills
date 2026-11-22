#!/usr/bin/env python3
"""Prepare text capacity in a full template slide copy, changing only padding.

prepare --source slide-06.xml --ids bcq bcU bci --output prepared.xml
prepare --source slide-06.xml --ids bcq --output prepared.xml --allow-resize

Only text, rect and ellipse shapes are supported. An ellipse is measured in its
axis-aligned inscribed rectangle. Schema padding defaults are applied explicitly
to measurement probes: 0px for text shapes and 5px for other shapes. Original
padding is retained when the text fits; otherwise a zero-padding copy is tried.
No text, font, geometry or connection is changed. All selected containers must
fit the heuristic before any deliverable XML is returned. --allow-resize adds
an outer-frame suggestion to a failure report; it never resizes a shape.

Measurements use xml_lint's glyph-category widths and authored paragraph/run
sizes, spacing and wrapping. Font files are not loaded. Reported fit is an
estimated layout capacity, not a pixel-exact rendering guarantee. Rendered
review remains necessary, especially for font substitution and tight circles.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from xml.parsers import expat

from lxml import etree as ET

try:
    from .. import xml_lint as _lint
except ImportError:  # direct CLI or file-based helper loading
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import xml_lint as _lint  # noqa: E402

PADDING = ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft")
TEXT_TAGS = {"content", "p", "span", "t", "strong", "b", "em", "i", "u", "del", "a", "br"}
UNMEASURED_ATTRIBUTES = {"list", "listStyle", "baseline", "tabStopPos", "defaultTabSize", "indent", "hanging"}
MEASUREMENT = {
    "method": "xml_lint glyph-category heuristic with strict wrapping at available width",
    "font_source": "declared fontFamily profiles or estimator default; font files not loaded",
    "rich_text_basis": "largest declared size and letter spacing, and widest declared font profile per paragraph",
    "pixel_exact": False,
    "requires_rendered_review": True,
    "height_basis": "authored line spacing; first line uses font size, following lines use line height",
    "ellipse_text_area": "axis-aligned inscribed rectangle: width/sqrt(2), height/sqrt(2)",
    "schema_padding_defaults": {"text": 0, "rect": 5, "ellipse": 5},
}


def _local(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else ""


def _number(value, label, *, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Cannot measure {label}: {value!r}") from error
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"Invalid {label}: {value!r}")
    return number


def _bbox(shape):
    return {"x": _number(shape.get("topLeftX"), "topLeftX"),
            "y": _number(shape.get("topLeftY"), "topLeftY"),
            "width": _number(shape.get("width"), "width", positive=True),
            "height": _number(shape.get("height"), "height", positive=True)}


def _probe(shape, content, bbox, padding):
    """Normalize namespaces only in a detached measurement tree."""
    probe = copy.deepcopy(shape)
    for child in list(probe):
        if _local(child) != "content":
            probe.remove(child)
    for child in probe.iter():
        if isinstance(child.tag, str):
            child.tag = _local(child)
            if child.tag == "p" and child.text is None:
                # The shared regex extractor needs explicit closing tags to
                # retain blank paragraphs. Only the analysis probe changes.
                child.text = ""
    probe.set("type", "text")
    factor = math.sqrt(2) if shape.get("type") == "ellipse" else 1
    probe.set("width", str(bbox["width"] / factor))
    probe.set("height", str(bbox["height"] / factor))
    probe_content = next(child for child in probe if _local(child) == "content")
    for key, value in padding.items():
        probe_content.set(key, str(value))
    element = _lint.extract_elements(ET.tostring(probe, encoding="unicode"))[0]
    # The shared extractor uses the largest span size. Include paragraph-level
    # sizes too, so a large paragraph cannot be measured at the content default.
    paragraphs = [child for child in content if _local(child) == "p"]
    if paragraphs and len(paragraphs) != len(element["paragraphs"]):
        raise ValueError("Paragraph layout could not be measured")
    for paragraph, meta in zip(paragraphs, element["paragraphs"]):
        meta["fontSize"] = max(
            [_number(content.get("fontSize", shape.get("fontSize", "16")), "fontSize", positive=True)]
            + [_number(n.get("fontSize"), "fontSize", positive=True)
               for n in paragraph.iter() if n.get("fontSize") is not None]
        )
        meta["explicit_paragraph"] = True
        meta["letterSpacing"] = max(
            [element.get("letterSpacing") or 0]
            + [_number(n.get("letterSpacing"), "letterSpacing")
               for n in paragraph.iter() if n.get("letterSpacing") is not None]
        )
        meta["fontFamilies"] = list(dict.fromkeys(
            [element["fontFamily"]] + [n.get("fontFamily") for n in paragraph.iter() if n.get("fontFamily")]
        ))
    element["bold"] = element["bold"] or any(n.get("bold") in {"true", "1"} for n in content.iter())
    return element, factor


def _measure(element, bbox, factor):
    width = max(element["width"] - element["paddingLeft"] - element["paddingRight"], 0)
    height = max(element["height"] - element["paddingTop"] - element["paddingBottom"], 0)
    available = {"x": bbox["x"] + (bbox["width"] - element["width"]) / 2 + element["paddingLeft"],
                 "y": bbox["y"] + (bbox["height"] - element["height"]) / 2 + element["paddingTop"],
                 "width": width, "height": height}
    paragraphs = element.get("paragraphs") or [{"text": element.get("text", ""), "fontSize": element["fontSize"]}]
    line_count = 0
    estimated_height = 0.0
    first_leading = 0.0
    unwrapped_width = 0.0
    required_width = 0.0
    for paragraph in paragraphs:
        text = paragraph["text"]
        if not text and not paragraph.get("explicit_paragraph"):
            continue
        families = paragraph.get("fontFamilies") or [element["fontFamily"]]
        size = _lint.resolve_font_size(element, paragraph.get("fontSize"))
        letter_spacing = _lint.resolve_letter_spacing(element, paragraph)
        spacing = paragraph.get("lineSpacing") or element.get("lineSpacing")
        line_height = _lint.estimate_text_line_height(element, spacing, size)
        before = _lint.estimate_text_line_height(element, paragraph.get("beforeLineSpacing") or element.get("beforeLineSpacing") or "fixed:0", size)
        after = _lint.estimate_text_line_height(element, paragraph.get("afterLineSpacing") or element.get("afterLineSpacing") or "fixed:0", size)
        if any(value is None for value in (line_height, before, after)):
            raise ValueError("Line spacing could not be measured")
        count = 0
        for hard_line in text.split("\n"):
            logical_width = max(_lint.estimate_text_width(hard_line.rstrip(), size, letter_spacing, element["bold"], family) for family in families)
            unwrapped_width = max(unwrapped_width, logical_width)
            if element.get("wrap") in {"false", "0"}:
                count += 1
                required_width = max(required_width, logical_width)
            else:
                count += max(_lint.count_wrapped_lines(hard_line, size, letter_spacing, element["bold"], family, max(width, 1)) for family in families)
                east_asian = any(_lint.is_cjk_char(char) for char in hard_line)
                required_width = max(required_width, max(
                    [_lint.estimate_character_width(char, size, element["bold"], family, east_asian)
                     for char in hard_line if not char.isspace() for family in families] or [0]))
        if line_count == 0:
            first_leading = max(line_height - size, 0)
        estimated_height += before + (size if line_count == 0 else line_height) + max(count - 1, 0) * line_height + after
        line_count += count
    return {"available_bbox": available, "line_count": line_count,
            "estimated_height": estimated_height,
            "estimated_height_with_first_line_leading": estimated_height + first_leading,
            "estimated_unwrapped_width": unwrapped_width,
            "minimum_glyph_width": required_width,
            "fits": width + 1e-9 >= required_width and height + 1e-9 >= estimated_height}


def _content_spans(raw):
    """Locate real content start tags using XML byte offsets, never regex text."""
    parser = expat.ParserCreate(namespace_separator="}")
    stack = []
    spans = {}

    def start(name, attrs):
        kind = name.rsplit("}", 1)[-1]
        if kind == "content" and len(stack) >= 2 and stack[-1][0] == "shape" and stack[-2][0] == "data":
            start_byte = parser.CurrentByteIndex
            end_byte = start_byte
            quote = None
            while end_byte < len(raw):
                char = raw[end_byte]
                if quote:
                    if char == quote:
                        quote = None
                elif char in (34, 39):
                    quote = char
                elif char == 62:
                    spans[stack[-1][1].get("id")] = (start_byte, end_byte + 1)
                    break
                end_byte += 1
        stack.append((kind, attrs))

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: stack.pop()
    parser.Parse(raw, True)
    return spans


def _zero_padding(head):
    # Consume complete quoted attributes so text inside an unrelated value can
    # never be mistaken for a real padding attribute.
    pattern = rb"(\s+)([^\s=<>/'\"]+)(\s*=\s*)(['\"])(.*?)\4"
    present = set()
    replacements = []
    for match in re.finditer(pattern, head, flags=re.S):
        key = match.group(2).decode("utf-8")
        if key in PADDING:
            present.add(key)
            replacements.append((match.start(5), match.end(5)))
    for start, end in reversed(replacements):
        head = head[:start] + b"0" + head[end:]
    missing = [b" " + key.encode() + b'="0"' for key in PADDING if key not in present]
    offset = -2 if head.endswith(b"/>") else -1
    return head[:offset] + b"".join(missing) + head[offset:]


def prepare_text_containers(source, ids, *, allow_resize=False) -> dict:
    """Return full copy XML only when every selected container estimates to fit.

    ``source`` is a single-slide SML file. ``ids`` selects top-level real shape
    IDs. ``needed_bbox`` on failure describes text-area capacity at its reported
    width, in px. Outer-frame dimensions are suggested only with allow_resize.
    The original file and all output bytes except selected padding values stay
    unchanged. Invalid selection raises ValueError; unmeasurable layout returns
    needs_action without XML.
    """
    path = Path(source)
    raw = path.read_bytes()
    ids = list(ids) if not isinstance(ids, str) else [ids]
    if not ids or any(not isinstance(value, str) or not value for value in ids):
        raise ValueError("Select at least one nonempty shape ID")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate selected IDs")
    root = ET.fromstring(raw, ET.XMLParser(resolve_entities=False, no_network=True))
    if root.getroottree().docinfo.doctype:
        raise ValueError("DOCTYPE is not supported in template text preparation")
    if _local(root) != "slide":
        raise ValueError("Expected a single slide XML")
    data = next((child for child in root if _local(child) == "data"), None)
    if data is None:
        raise ValueError("Slide has no data")
    members = [child for child in data if isinstance(child.tag, str) and child.get("id")]
    if len(members) != len({child.get("id") for child in members}):
        raise ValueError("Duplicate top-level member IDs in source")
    lookup = {child.get("id"): child for child in members}
    if set(ids) - set(lookup):
        raise ValueError("Missing top-level member IDs: " + ", ".join(sorted(set(ids) - set(lookup))))
    if any(_local(lookup[value]) != "shape" for value in ids):
        raise ValueError("Text preparation requires selected shape IDs")
    selected = [child for child in members if child.get("id") in ids]
    result = {"schema_version": 1, "ok": True, "status": "prepared", "source": str(path),
              "source_sha256": hashlib.sha256(raw).hexdigest(),
              "selected_ids": [child.get("id") for child in selected],
              "measurement": copy.deepcopy(MEASUREMENT), "containers": []}
    changes = []
    for shape in selected:
        row = {"id": shape.get("id"), "type": shape.get("type")}
        result["containers"].append(row)
        try:
            if shape.get("type") not in {"text", "rect", "ellipse"}:
                raise ValueError("Supported shape types: text, rect, ellipse")
            if shape.get("vert", "horz") != "horz":
                raise ValueError("Vertical text requires rendered layout review")
            contents = [child for child in shape if _local(child) == "content"]
            if len(contents) != 1:
                raise ValueError("Expected exactly one shape content element")
            content = contents[0]
            if any(_local(n) not in TEXT_TAGS or UNMEASURED_ATTRIBUTES.intersection(n.attrib) for n in content.iter() if isinstance(n.tag, str)):
                raise ValueError("Text lists, fields, tabs or special offsets require rendered layout review")
            bbox = _bbox(shape)
            row["outer_bbox"] = bbox
            default = 0 if shape.get("type") == "text" else 5
            padding = {key: _number(content.get(key, str(default)), key) for key in PADDING}
            if any(value < 0 for value in padding.values()):
                raise ValueError("Padding must be nonnegative")
            row["effective_padding_before"] = padding
            row["declared_font_families"] = sorted({n.get("fontFamily") for n in shape.iter() if n.get("fontFamily")})
            element, factor = _probe(shape, content, bbox, padding)
            before = _measure(element, bbox, factor)
            row["before"] = before
            row["padding_after"] = dict(padding)
            row["after"] = before
            row["status"] = "fits"
            if before["fits"]:
                continue
            zero = dict.fromkeys(PADDING, 0)
            element, factor = _probe(shape, content, bbox, zero)
            after = _measure(element, bbox, factor)
            row.update(padding_after=zero, after=after, status="padding_reduced")
            if after["fits"]:
                changes.append(shape.get("id"))
                continue
            row["status"] = "needs_action"
            needed_width = max(after["available_bbox"]["width"], after["minimum_glyph_width"])
            needed_element = copy.deepcopy(element)
            needed_element["width"] = needed_width
            needed = _measure(needed_element, bbox, factor)
            row["needed_bbox"] = {"coordinate_space": "text_area", "width": needed_width,
                                  "height": needed["estimated_height"], "measured_at_width": needed_width}
            row["suggestions"] = [{"action": "use_external_text_frame", "needed_bbox": row["needed_bbox"],
                                   "message": "Place all original text and styles in a separate text frame; review layout and connections."}]
            if allow_resize:
                row["suggestions"].append({"action": "resize_outer_frame", "bbox": {
                    "x": bbox["x"], "y": bbox["y"],
                    "width": math.ceil(max(bbox["width"], needed_width * factor) * 10) / 10,
                    "height": math.ceil(max(bbox["height"], needed["estimated_height"] * factor) * 10) / 10},
                    "padding": zero, "review_connections": True,
                    "message": "Suggested dimensions only; review neighboring objects and connections before resizing."})
        except ValueError as error:
            row.update(status="unsupported", reason=str(error), suggestions=[{
                "action": "review_rendered_layout", "message": "Preserve the original text and styles; resolve this layout before preparation."}])
        result["ok"] = False
    if path.read_bytes() != raw:
        raise ValueError("Source changed during text-container preparation")
    if not result["ok"]:
        result["status"] = "needs_action"
        return result
    spans = _content_spans(raw)
    output = raw
    for shape_id in sorted(changes, key=lambda value: spans[value][0], reverse=True):
        start, end = spans[shape_id]
        output = output[:start] + _zero_padding(output[start:end]) + output[end:]
    result["xml"] = output.decode("utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Prepare selected containers in a full slide copy")
    prepare.add_argument("--source", required=True)
    prepare.add_argument("--ids", nargs="+", required=True)
    prepare.add_argument("--output", required=True, help="New XML path; report is written beside it as .text-fit.json")
    prepare.add_argument("--allow-resize", action="store_true", help="Permit outer-frame suggestions only")
    args = parser.parse_args(argv)
    output = Path(args.output)
    manifest = output.with_suffix(".text-fit.json")
    try:
        if output.resolve() == Path(args.source).resolve() or manifest.resolve() == Path(args.source).resolve():
            raise ValueError("Output paths must differ from the source")
        if output == manifest or output.exists() or manifest.exists():
            raise ValueError("Output or report already exists")
        result = prepare_text_containers(args.source, args.ids, allow_resize=args.allow_resize)
        if not result["ok"]:
            print(json.dumps(result, ensure_ascii=False))
            return 2
        xml = result.pop("xml")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(xml.encode("utf-8"))
        result["xml_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
        with manifest.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    except (ValueError, OSError, ET.XMLSyntaxError, expat.ExpatError, UnicodeError) as error:
        parser.error(str(error))
    print(json.dumps({"ok": True, "output": str(output), "report": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
