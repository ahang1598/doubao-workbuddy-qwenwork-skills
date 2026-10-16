"""Serialize a composed SML page with local, explicit SVG namespaces."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

_SML = "https://www.larkoffice.com/sml/2.0"
_SVG = "http://www.w3.org/2000/svg"
_XML = "http://www.w3.org/XML/1998/namespace"
_XLINK = "http://www.w3.org/1999/xlink"


def _parse(source):
    # Keep declarations too: prefixes may occur in attribute values or CSS.
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    pending = []
    events = ET.iterparse(io.StringIO(source), events=("start-ns", "start"), parser=parser)
    for event, item in events:
        if event == "start-ns":
            pending.append(item)
        else:
            for prefix, uri in pending:
                item.set("xmlns" + (":" + prefix if prefix else ""), uri)
            pending.clear()
    return events.root


def _name(value, scope, *, attribute=False):
    value = str(value) if isinstance(value, ET.QName) else value
    if not isinstance(value, str):
        raise TypeError("XML names must be strings or QName objects")
    if value.startswith("{"):
        uri, local = value[1:].split("}", 1)
        return uri, _local_name(local)
    if ":" in value:
        prefix, local = value.split(":", 1)
        _local_name(prefix)
        _local_name(local)
        if prefix not in scope or not scope[prefix]:
            raise ValueError(f"Unbound XML prefix: {prefix!r}")
        return scope[prefix], local
    return ("" if attribute else scope.get("", "")), _local_name(value)


def _local_name(value):
    # Check before rewriting: a malformed ET tag must not become valid XML
    # with a different namespace (e.g. v:v:rect or {urn:other}v:rect).
    if not value or ":" in value:
        raise ValueError(f"Invalid XML local name: {value!r}")
    try:
        parsed = ET.fromstring("<" + value + "/>")
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML local name: {value!r}") from exc
    if parsed.tag != value:
        raise ValueError(f"Invalid XML local name: {value!r}")
    return value


def _declarations(node):
    return {
        key[6:] if key.startswith("xmlns:") else "": value
        for key, value in node.attrib.items()
        if isinstance(key, str) and (key == "xmlns" or key.startswith("xmlns:"))
    }


def _text(value):
    return escape(value, {"\r": "&#13;"}) if value else ""


def _attribute(value):
    return '"' + escape(value, {'"': "&quot;", "\t": "&#9;", "\n": "&#10;", "\r": "&#13;"}) + '"'


def serialize_slide(slide: ET.Element | str) -> str:
    """Return one SML ``<slide>`` with literal ``<svg xmlns="…">`` roots."""
    root = _parse(slide) if isinstance(slide, str) else slide
    if not ET.iselement(root):
        raise TypeError("serialize_slide expects an Element or XML string")
    initial = {"xml": _XML}
    root_scope = {**initial, **_declarations(root)}
    if _name(root.tag, root_scope) != (_SML, "slide"):
        raise ValueError("Expected one <slide> in the SML 2.0 namespace")

    def emit(node, source_scope, output_scope):
        if node.tag is ET.Comment:
            return "<!--" + (node.text or "") + "-->" + _text(node.tail)
        if node.tag is ET.ProcessingInstruction:
            return "<?" + (node.text or "") + "?>" + _text(node.tail)

        declared = _declarations(node)
        source_scope = {**source_scope, **declared}
        uri, local = _name(node.tag, source_scope)
        is_svg = uri == _SVG and local == "svg"
        # Slides extracts each SVG from its SML ancestors. Keep the extracted
        # document self-contained, including attribute/CSS prefix bindings.
        scope = dict(initial if is_svg else output_scope)
        declarations = {}
        # Preserve explicit prefix bindings; default namespaces follow the
        # element's expanded name, including xmlns="" for foreign content.
        for prefix, target in (source_scope if is_svg else declared).items():
            if prefix and scope.get(prefix) != target:
                scope[prefix] = target
                declarations["xmlns:" + prefix] = target
        tag = "xml:" + local if uri == _XML else local
        if uri != _XML and (scope.get("", "") != uri or is_svg):
            scope[""] = uri
            declarations["xmlns"] = uri

        def attribute_name(value):
            namespace, name = _name(value, source_scope, attribute=True)
            if not namespace:
                return name
            prefix = next((p for p, target in scope.items() if p and target == namespace), None)
            if prefix is None:
                prefix = "xlink" if namespace == _XLINK and "xlink" not in scope else None
                if prefix is None:
                    index = 0
                    while f"ns{index}" in scope:
                        index += 1
                    prefix = f"ns{index}"
                scope[prefix] = namespace
                declarations["xmlns:" + prefix] = namespace
            return prefix + ":" + name

        attributes = []
        for key, value in node.attrib.items():
            if isinstance(key, str) and (key == "xmlns" or key.startswith("xmlns:")):
                continue
            name = attribute_name(key)
            if isinstance(value, ET.QName):
                value = attribute_name(value)
            attributes.append((name, value))
        attrs = "".join(" " + key + "=" + _attribute(value) for key, value in [*declarations.items(), *attributes])
        if len(node) or node.text:
            body = _text(node.text) + "".join(emit(child, source_scope, scope) for child in node)
            result = "<" + tag + attrs + ">" + body + "</" + tag + ">"
        else:
            result = "<" + tag + attrs + "/>"
        return result + _text(node.tail)

    result = emit(root, initial, initial)
    ET.fromstring(result)  # Reject invalid programmatically built trees too.
    return result
