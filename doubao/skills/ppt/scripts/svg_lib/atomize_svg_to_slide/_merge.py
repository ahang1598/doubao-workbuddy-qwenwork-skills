"""Append atomized SML data without reserializing the existing slide or SVGs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from xml.parsers import expat
from xml.sax.saxutils import escape

_SML_NS = "https://www.larkoffice.com/sml/2.0"
_SEPARATOR = "|"


@dataclass
class _DataSpan:
    raw: bytes
    start: int = -1
    open_end: int = -1
    close_start: int = -1
    self_closing: bool = False
    bindings: Dict[str, str] = field(default_factory=dict)
    children: List[Tuple[int, Dict[str, str]]] = field(default_factory=list)


def _tag_end(raw: bytes, start: int) -> int:
    """Find the end of a parsed start tag, respecting quoted '>' characters."""
    quote = 0
    for index in range(start, len(raw)):
        character = raw[index]
        if quote:
            if character == quote:
                quote = 0
        elif character in (34, 39):
            quote = character
        elif character == 62:
            return index + 1
    raise ValueError("Unclosed XML start tag")


def _scan_slide(xml: str, *, fragment: bool) -> _DataSpan:
    label = "atomized fragment" if fragment else "base slide"
    if not isinstance(xml, str):
        raise TypeError(f"{label} must be an XML string")
    span = _DataSpan(xml.encode("utf-8"))
    parser = expat.ParserCreate(namespace_separator=_SEPARATOR)
    parser.namespace_prefixes = True
    stack = []
    scopes = []
    pending_bindings = {}

    def namespace(prefix, uri):
        pending_bindings[prefix or ""] = uri or ""

    def start(name, attrs):
        parts = name.split(_SEPARATOR)
        uri, local = parts[:2] if len(parts) >= 2 else ("", name)
        prefix = parts[2] if len(parts) > 2 else ""
        if uri == _SML_NS and prefix:
            raise ValueError(
                f"{label} has prefixed SML <{prefix}:{local}>; pass the original unprefixed slide/atomize XML, without ElementTree serialization"
            )
        depth = len(stack)
        own_bindings = dict(pending_bindings)
        pending_bindings.clear()
        bindings = dict(scopes[-1]) if scopes else {}
        bindings.update(own_bindings)
        if depth == 0:
            if (uri, local) != (_SML_NS, "slide"):
                raise ValueError(f"{label} must have a <slide> root in the default SML 2.0 namespace")
            if fragment and attrs:
                raise ValueError("atomized fragment root must contain only namespace declarations and <data>")
        if depth == 1:
            if (uri, local) == (_SML_NS, "data"):
                if span.start >= 0:
                    raise ValueError(f"{label} must have exactly one direct <data> child")
                if fragment and attrs:
                    raise ValueError("atomized fragment <data> must not carry attributes that would be discarded")
                span.start = parser.CurrentByteIndex
                span.open_end = _tag_end(span.raw, span.start)
                span.self_closing = span.raw[span.start : span.open_end].rstrip().endswith(b"/>")
                span.bindings = bindings
            elif fragment:
                raise ValueError(
                    "atomized fragment may contain only a direct <data> child; a full slide would discard other content"
                )
        if depth == 2 and stack[-1] == (_SML_NS, "data"):
            if fragment and uri != _SML_NS:
                raise ValueError("atomized <data> children must be SML elements; keep SVG inside its <embed>")
            span.children.append((parser.CurrentByteIndex, own_bindings))
        stack.append((uri, local))
        scopes.append(bindings)

    def end(_name):
        if len(stack) == 2 and stack[-1] == (_SML_NS, "data"):
            span.close_start = span.open_end if span.self_closing else parser.CurrentByteIndex
        stack.pop()
        scopes.pop()

    def text(value):
        if fragment and len(stack) == 1 and value.strip():
            raise ValueError("atomized fragment must not contain loose text outside <data>")
        if fragment and len(stack) == 2 and stack[-1] == (_SML_NS, "data") and value.strip():
            raise ValueError("atomized <data> must contain elements, not loose text")

    def reject_doctype(*_args):
        raise ValueError(f"{label} must not contain DTD/entity declarations")

    parser.StartNamespaceDeclHandler = namespace
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.StartDoctypeDeclHandler = reject_doctype
    parser.EntityDeclHandler = reject_doctype
    try:
        parser.Parse(span.raw, True)
    except expat.ExpatError as exc:
        raise ValueError(f"Invalid {label} XML: {exc}") from exc
    if span.start < 0:
        raise ValueError(f"{label} must have exactly one direct SML <data> child")
    return span


def merge_atomized_slide(slide_xml: str, atomized_xml: str) -> str:
    """Append an atomize result to an existing complete SML slide."""
    base = _scan_slide(slide_xml, fragment=False)
    fragment = _scan_slide(atomized_xml, fragment=True)
    if fragment.self_closing:
        return slide_xml
    additions = fragment.raw[fragment.open_end : fragment.close_start]
    if not additions.strip():
        return slide_xml
    # A prefix declared on the fragment root/data would otherwise become
    # unbound (or acquire a different meaning) after moving its children.
    for offset, own_bindings in reversed(fragment.children):
        inherited = {
            prefix: uri
            for prefix, uri in fragment.bindings.items()
            if prefix not in ("", "xml") and prefix not in own_bindings and base.bindings.get(prefix) != uri
        }
        if not inherited:
            continue
        name_end = offset + 1
        while fragment.raw[name_end : name_end + 1] not in (b" ", b"\t", b"\r", b"\n", b"/", b">"):
            name_end += 1
        attributes = "".join(
            f' xmlns:{prefix}="{escape(uri, {chr(34): "&quot;"})}"' for prefix, uri in inherited.items()
        ).encode("utf-8")
        position = name_end - fragment.open_end
        additions = additions[:position] + attributes + additions[position:]
    if base.self_closing:
        result = base.raw[: base.open_end - 2] + b">" + additions + b"</data>" + base.raw[base.open_end :]
    else:
        result = base.raw[: base.close_start] + additions + base.raw[base.close_start :]
    merged = result.decode("utf-8")
    _scan_slide(merged, fragment=False)
    return merged
