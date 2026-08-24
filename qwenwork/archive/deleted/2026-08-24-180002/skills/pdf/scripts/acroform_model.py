"""Shared AcroForm widget model.

Walks a PDF's interactive form (AcroForm) and produces a normalized,
JSON-friendly description of every terminal widget: text inputs,
checkboxes, radio groups and choice lists. Both the export CLI and the
value-writer CLI build on top of this module so the widget contract stays
in exactly one place.
"""

from typing import Any, Dict, List, Optional

from pypdf import PdfReader

# Field-type tokens as they appear in the PDF's /FT entry.
_TYPE_TEXT = "/Tx"
_TYPE_BUTTON = "/Btn"
_TYPE_CHOICE = "/Ch"

_OFF_STATE = "/Off"


def _qualified_name(widget: Any) -> Optional[str]:
    """Build a dotted, fully-qualified field name by climbing /Parent links."""
    segments: List[str] = []
    node = widget
    while node:
        partial = node.get("/T")
        if partial:
            segments.append(partial)
        node = node.get("/Parent")
    if not segments:
        return None
    return ".".join(reversed(segments))


def _classify_terminal(field: Any, name: str) -> Dict[str, Any]:
    """Turn a single terminal field object into its normalized descriptor."""
    descriptor: Dict[str, Any] = {"field_id": name}
    kind = field.get("/FT")

    if kind == _TYPE_TEXT:
        descriptor["type"] = "text"
        return descriptor

    if kind == _TYPE_BUTTON:
        descriptor["type"] = "checkbox"
        states = field.get("/_States_", [])
        if len(states) == 2:
            if _OFF_STATE in states:
                on_state = states[0] if states[0] != _OFF_STATE else states[1]
                descriptor["checked_value"] = on_state
                descriptor["unchecked_value"] = _OFF_STATE
            else:
                print(
                    f"Unexpected state values for checkbox `${name}`. Its checked "
                    "and unchecked values may not be correct; if you're trying to "
                    "check it, visually verify the results."
                )
                descriptor["checked_value"] = states[0]
                descriptor["unchecked_value"] = states[1]
        return descriptor

    if kind == _TYPE_CHOICE:
        descriptor["type"] = "choice"
        descriptor["choice_options"] = [
            {"value": state[0], "text": state[1]}
            for state in field.get("/_States_", [])
        ]
        return descriptor

    descriptor["type"] = f"unknown ({kind})"
    return descriptor


class AcroFormInspector:
    """Enumerates and geo-locates every fillable widget in a PDF."""

    def __init__(self, reader: PdfReader):
        self._reader = reader
        self._terminals: Dict[str, Dict[str, Any]] = {}
        self._radio_group_names: set = set()
        self._radio_groups: Dict[str, Dict[str, Any]] = {}

    def _collect_terminals(self) -> None:
        """First pass: split fields into terminals and radio-group parents."""
        for name, field in self._reader.get_fields().items():
            if field.get("/Kids"):
                if field.get("/FT") == _TYPE_BUTTON:
                    self._radio_group_names.add(name)
                continue
            self._terminals[name] = _classify_terminal(field, name)

    def _attach_geometry(self) -> None:
        """Second pass: walk page annotations to place widgets on the page."""
        for page_offset, page in enumerate(self._reader.pages):
            for annotation in page.get("/Annots", []):
                name = _qualified_name(annotation)
                if name in self._terminals:
                    self._terminals[name]["page"] = page_offset + 1
                    self._terminals[name]["rect"] = annotation.get("/Rect")
                elif name in self._radio_group_names:
                    self._register_radio_option(name, annotation, page_offset + 1)

    def _register_radio_option(self, name: str, annotation: Any, page: int) -> None:
        """Record one radio button (an appearance state other than /Off)."""
        try:
            live_states = [s for s in annotation["/AP"]["/N"] if s != _OFF_STATE]
        except KeyError:
            return
        if len(live_states) != 1:
            return
        group = self._radio_groups.setdefault(
            name,
            {
                "field_id": name,
                "type": "radio_group",
                "page": page,
                "radio_options": [],
            },
        )
        group["radio_options"].append(
            {"value": live_states[0], "rect": annotation.get("/Rect")}
        )

    @staticmethod
    def _reading_order(entry: Dict[str, Any]) -> list:
        """Sort widgets top-to-bottom then left-to-right within each page."""
        if "radio_options" in entry:
            rect = entry["radio_options"][0]["rect"] or [0, 0, 0, 0]
        else:
            rect = entry.get("rect") or [0, 0, 0, 0]
        return [entry.get("page"), [-rect[1], rect[0]]]

    def inspect(self) -> List[Dict[str, Any]]:
        """Run both passes and return placed widgets in reading order."""
        self._collect_terminals()
        self._attach_geometry()

        placed = []
        for descriptor in self._terminals.values():
            if "page" in descriptor:
                placed.append(descriptor)
            else:
                print(
                    "Unable to determine location for field id: "
                    f"{descriptor.get('field_id')}, ignoring"
                )

        combined = placed + list(self._radio_groups.values())
        combined.sort(key=self._reading_order)
        return combined


def enumerate_widgets(reader: PdfReader) -> List[Dict[str, Any]]:
    """Convenience wrapper: inspect a reader and return the widget list."""
    return AcroFormInspector(reader).inspect()
