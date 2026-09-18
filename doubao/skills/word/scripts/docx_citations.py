#!/usr/bin/env python3
"""Inspect, validate, and edit Word citations: footnotes, endnotes, and REF bibliography.

The tool patches OOXML directly because python-docx does not expose a stable
high-level API for native notes. Mutations are transactional: the input is read
fully, all operations are applied in memory, note-specific validation runs, and
only then is an output DOCX atomically published.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import posixpath
import re
import stat
import sys
import tempfile
import urllib.parse
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_NS = "http://www.w3.org/XML/1998/namespace"

W = f"{{{W_NS}}}"
PKG_REL = f"{{{PKG_REL_NS}}}"
CT = f"{{{CT_NS}}}"
XML_SPACE = f"{{{XML_NS}}}space"
NS = {"w": W_NS, "r": R_NS, "rel": PKG_REL_NS, "ct": CT_NS}

REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_BASE = "application/vnd.openxmlformats-officedocument.wordprocessingml"

STYLE_CT = f"{CT_BASE}.styles+xml"
SETTINGS_CT = f"{CT_BASE}.settings+xml"

SAFE_NUMBER_FORMATS = {
    "decimal",
    "upperRoman",
    "lowerRoman",
    "upperLetter",
    "lowerLetter",
    "ordinal",
    "cardinalText",
    "ordinalText",
    "hex",
    "chicago",
    "ideographDigital",
    "japaneseCounting",
    "aiueo",
    "iroha",
    "decimalFullWidth",
    "decimalHalfWidth",
    "japaneseLegal",
    "japaneseDigitalTenThousand",
    "decimalEnclosedCircle",
    "decimalFullWidth2",
    "aiueoFullWidth",
    "irohaFullWidth",
    "decimalZero",
    "bullet",
    "ganada",
    "chosung",
    "decimalEnclosedFullstop",
    "decimalEnclosedParen",
    "decimalEnclosedCircleChinese",
    "ideographEnclosedCircle",
    "ideographTraditional",
    "ideographZodiac",
    "ideographZodiacTraditional",
    "taiwaneseCounting",
    "ideographLegalTraditional",
    "taiwaneseCountingThousand",
    "taiwaneseDigital",
    "chineseCounting",
    "chineseLegalSimplified",
    "chineseCountingThousand",
    "application",
    "russianLower",
    "russianUpper",
    "none",
    "numberInDash",
    "hebrew1",
    "hebrew2",
    "arabicAlpha",
    "arabicAbjad",
    "hindiVowels",
    "hindiConsonants",
    "hindiNumbers",
    "hindiCounting",
    "thaiLetters",
    "thaiNumbers",
    "thaiCounting",
    "vietnameseCounting",
}
RESTART_VALUES = {"continuous", "eachSect", "eachPage"}

SETTINGS_ORDER = [
    "writeProtection", "view", "zoom", "removePersonalInformation",
    "removeDateAndTime", "doNotDisplayPageBoundaries", "displayBackgroundShape",
    "printPostScriptOverText", "printFractionalCharacterWidth", "printFormsData",
    "embedTrueTypeFonts", "embedSystemFonts", "saveSubsetFonts", "saveFormsData",
    "mirrorMargins", "alignBordersAndEdges", "bordersDoNotSurroundHeader",
    "bordersDoNotSurroundFooter", "gutterAtTop", "hideSpellingErrors",
    "hideGrammaticalErrors", "activeWritingStyle", "proofState", "formsDesign",
    "attachedTemplate", "linkStyles", "stylePaneFormatFilter",
    "stylePaneSortMethod", "documentType", "mailMerge", "revisionView",
    "trackRevisions", "doNotTrackMoves", "doNotTrackFormatting",
    "documentProtection", "autoFormatOverride", "styleLockTheme", "styleLockQFSet",
    "defaultTabStop", "autoHyphenation", "consecutiveHyphenLimit",
    "hyphenationZone", "doNotHyphenateCaps", "showEnvelope", "summaryLength",
    "clickAndTypeStyle", "defaultTableStyle", "evenAndOddHeaders",
    "bookFoldRevPrinting", "bookFoldPrinting", "bookFoldPrintingSheets",
    "drawingGridHorizontalSpacing", "drawingGridVerticalSpacing",
    "displayHorizontalDrawingGridEvery", "displayVerticalDrawingGridEvery",
    "doNotUseMarginsForDrawingGridOrigin", "drawingGridHorizontalOrigin",
    "drawingGridVerticalOrigin", "doNotShadeFormData", "noPunctuationKerning",
    "characterSpacingControl", "printTwoOnOne", "strictFirstAndLastChars",
    "noLineBreaksAfter", "noLineBreaksBefore", "savePreviewPicture",
    "doNotValidateAgainstSchema", "saveInvalidXml", "ignoreMixedContent",
    "alwaysShowPlaceholderText", "doNotDemarcateInvalidXml", "saveXmlDataOnly",
    "useXSLTWhenSaving", "saveThroughXslt", "showXMLTags",
    "alwaysMergeEmptyNamespace", "updateFields", "hdrShapeDefaults",
    "footnotePr", "endnotePr", "compat", "docVars", "rsids", "mathPr",
    "attachedSchema", "themeFontLang", "clrSchemeMapping",
    "doNotIncludeSubdocsInStats", "doNotAutoCompressPictures", "forceUpgrade",
    "captions", "readModeInkLockDown", "schemaLibrary", "shapeDefaults",
    "doNotEmbedSmartTags", "decimalSymbol", "listSeparator",
]
SECTPR_ORDER = [
    "headerReference", "footerReference", "footnotePr", "endnotePr", "type",
    "pgSz", "pgMar", "paperSrc", "pgBorders", "lnNumType", "pgNumType",
    "cols", "formProt", "vAlign", "noEndnote", "titlePg", "textDirection",
    "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange",
]
NOTE_PR_ORDER = ["pos", "numFmt", "numStart", "numRestart", "footnote", "endnote"]


class CitationError(RuntimeError):
    """A fail-closed note operation error."""


@dataclass(frozen=True)
class KindInfo:
    kind: str
    plural: str
    singular: str
    part: str
    ref: str
    mark: str
    paragraph_style: str
    reference_style: str
    relationship_type: str
    content_type: str
    property_name: str
    positions: frozenset[str]
    default_position: str


KINDS = {
    "footnote": KindInfo(
        "footnote", "footnotes", "footnote", "word/footnotes.xml",
        "footnoteReference", "footnoteRef", "FootnoteText", "FootnoteReference",
        f"{REL_BASE}/footnotes", f"{CT_BASE}.footnotes+xml", "footnotePr",
        frozenset({"pageBottom", "beneathText", "sectEnd", "docEnd"}),
        "pageBottom",
    ),
    "endnote": KindInfo(
        "endnote", "endnotes", "endnote", "word/endnotes.xml",
        "endnoteReference", "endnoteRef", "EndnoteText", "EndnoteReference",
        f"{REL_BASE}/endnotes", f"{CT_BASE}.endnotes+xml", "endnotePr",
        frozenset({"sectEnd", "docEnd"}), "docEnd",
    ),
}


def _local(element: etree._Element) -> str:
    return etree.QName(element).localname


def _xml(data: bytes, name: str) -> etree._ElementTree:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False)
    try:
        return etree.ElementTree(etree.fromstring(data, parser=parser))
    except etree.XMLSyntaxError as exc:
        raise CitationError(f"invalid XML in {name}: {exc}") from exc


def _serialize(tree: etree._ElementTree) -> bytes:
    return etree.tostring(
        tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes"
    )


def _safe_member(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    candidate = name[:-1] if name.endswith("/") else name
    if not candidate:
        return False
    normalized = posixpath.normpath(candidate)
    return normalized == candidate and normalized != ".." and not normalized.startswith("../")


class DocxPackage:
    def __init__(self, source: Path):
        self.source = source
        self.infos: list[zipfile.ZipInfo] = []
        self.payloads: dict[str, bytes] = {}
        self.overrides: dict[str, bytes] = {}
        self.removed: set[str] = set()
        try:
            with zipfile.ZipFile(source, "r") as archive:
                seen: set[str] = set()
                for info in archive.infolist():
                    if info.filename in seen:
                        raise CitationError(f"duplicate ZIP member: {info.filename}")
                    seen.add(info.filename)
                    if not _safe_member(info.filename):
                        raise CitationError(f"unsafe ZIP member: {info.filename}")
                    mode = (info.external_attr >> 16) & 0xFFFF
                    if stat.S_ISLNK(mode):
                        raise CitationError(f"symlink ZIP member is not allowed: {info.filename}")
                    self.infos.append(info)
                    self.payloads[info.filename] = archive.read(info)
        except (OSError, zipfile.BadZipFile) as exc:
            raise CitationError(f"invalid DOCX package: {source}: {exc}") from exc
        for required in ("[Content_Types].xml", "word/document.xml"):
            if required not in self.payloads:
                raise CitationError(f"required DOCX part is missing: {required}")

    def names(self) -> set[str]:
        return (set(self.payloads) | set(self.overrides)) - self.removed

    def has(self, name: str) -> bool:
        return name in self.names()

    def read(self, name: str) -> bytes:
        if name in self.removed or (name not in self.overrides and name not in self.payloads):
            raise CitationError(f"DOCX part is missing: {name}")
        if name in self.overrides:
            return self.overrides[name]
        return self.payloads[name]

    def tree(self, name: str) -> etree._ElementTree:
        return _xml(self.read(name), name)

    def put_tree(self, name: str, tree: etree._ElementTree) -> None:
        self.overrides[name] = _serialize(tree)
        self.removed.discard(name)

    def write(self, destination: Path, *, force: bool = False) -> None:
        destination = destination.resolve()
        if destination.exists() and not force and destination != self.source.resolve():
            raise CitationError(f"output already exists (use --force): {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(temp_fd)
        temp_path = Path(temp_name)
        try:
            original_names = {info.filename for info in self.infos}
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as output:
                for info in self.infos:
                    name = info.filename
                    if name in self.removed:
                        continue
                    output.writestr(info, self.overrides.get(name, self.payloads[name]))
                for name in sorted(set(self.overrides) - original_names - self.removed):
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o600 << 16
                    output.writestr(info, self.overrides[name])
            os.replace(temp_path, destination)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise


def _insert_ordered(parent: etree._Element, child: etree._Element, order: list[str]) -> None:
    target = _local(child)
    try:
        target_index = order.index(target)
    except ValueError:
        parent.append(child)
        return
    for index, existing in enumerate(parent):
        try:
            existing_index = order.index(_local(existing))
        except ValueError:
            continue
        if existing_index > target_index:
            parent.insert(index, child)
            return
    parent.append(child)


def _set_text(node: etree._Element, value: str) -> None:
    node.text = value
    if value[:1].isspace() or value[-1:].isspace():
        node.set(XML_SPACE, "preserve")
    else:
        node.attrib.pop(XML_SPACE, None)


def _content_types(pkg: DocxPackage) -> etree._ElementTree:
    tree = pkg.tree("[Content_Types].xml")
    if tree.getroot().tag != CT + "Types":
        raise CitationError("[Content_Types].xml has an unexpected root")
    return tree


def _ensure_content_type(pkg: DocxPackage, part: str, content_type: str) -> None:
    tree = _content_types(pkg)
    root = tree.getroot()
    part_name = "/" + part.lstrip("/")
    matches = [
        node for node in root.findall(CT + "Override")
        if urllib.parse.unquote(node.get("PartName") or "") == part_name
    ]
    if len(matches) > 1:
        raise CitationError(f"duplicate Content Type overrides for {part_name}")
    if matches:
        if matches[0].get("ContentType") != content_type:
            raise CitationError(f"conflicting Content Type for {part_name}")
        return
    node = etree.SubElement(root, CT + "Override")
    node.set("PartName", part_name)
    node.set("ContentType", content_type)
    pkg.put_tree("[Content_Types].xml", tree)


def _relationships(pkg: DocxPackage) -> etree._ElementTree:
    name = "word/_rels/document.xml.rels"
    if pkg.has(name):
        tree = pkg.tree(name)
        if tree.getroot().tag != PKG_REL + "Relationships":
            raise CitationError(f"{name} has an unexpected root")
        return tree
    return etree.ElementTree(etree.Element(PKG_REL + "Relationships", nsmap={None: PKG_REL_NS}))


def _canonical_relationship_target(raw: str) -> str | None:
    parsed = urllib.parse.urlsplit(urllib.parse.unquote(raw))
    if (
        not parsed.path or parsed.scheme or parsed.netloc or parsed.query
        or parsed.fragment or "\\" in parsed.path
    ):
        return None
    return posixpath.normpath(
        parsed.path.lstrip("/")
        if parsed.path.startswith("/")
        else posixpath.join("word", parsed.path)
    )


def _ensure_relationship(pkg: DocxPackage, rel_type: str, target_part: str) -> None:
    tree = _relationships(pkg)
    root = tree.getroot()
    relationships = root.findall(PKG_REL + "Relationship")
    ids = [node.get("Id") for node in relationships]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise CitationError("document relationships contain empty or duplicate IDs")
    matches = [node for node in relationships if node.get("Type") == rel_type]
    if len(matches) > 1:
        raise CitationError(f"duplicate relationship type: {rel_type}")
    if matches:
        node = matches[0]
        if (
            node.get("TargetMode", "Internal") != "Internal"
            or _canonical_relationship_target(node.get("Target") or "") != target_part
        ):
            raise CitationError(f"conflicting relationship for {target_part}")
        return
    for node in relationships:
        if (
            node.get("TargetMode", "Internal") == "Internal"
            and _canonical_relationship_target(node.get("Target") or "") == target_part
        ):
            raise CitationError(f"{target_part} is mounted with the wrong relationship type")
    used = set(ids)
    index = 1
    while f"rId{index}" in used:
        index += 1
    node = etree.SubElement(root, PKG_REL + "Relationship")
    node.set("Id", f"rId{index}")
    node.set("Type", rel_type)
    node.set("Target", posixpath.basename(target_part))
    pkg.put_tree("word/_rels/document.xml.rels", tree)


def _separator(info: KindInfo, note_id: int, note_type: str, marker: str) -> etree._Element:
    note = etree.Element(W + info.singular)
    note.set(W + "type", note_type)
    note.set(W + "id", str(note_id))
    paragraph = etree.SubElement(note, W + "p")
    run = etree.SubElement(paragraph, W + "r")
    etree.SubElement(run, W + marker)
    return note


def _ensure_notes_part(pkg: DocxPackage, info: KindInfo) -> etree._ElementTree:
    if pkg.has(info.part):
        tree = pkg.tree(info.part)
        root = tree.getroot()
        if root.tag != W + info.plural:
            raise CitationError(f"{info.part} has an unexpected root")
    else:
        root = etree.Element(W + info.plural, nsmap={"w": W_NS})
        tree = etree.ElementTree(root)

    expected = {
        -1: ("separator", "separator"),
        0: ("continuationSeparator", "continuationSeparator"),
    }
    notes_by_id: dict[int, list[etree._Element]] = {}
    for note in root.findall(W + info.singular):
        try:
            note_id = int(note.get(W + "id", ""))
        except ValueError as exc:
            raise CitationError(f"{info.part} contains an invalid note ID") from exc
        notes_by_id.setdefault(note_id, []).append(note)
    for note_id, entries in notes_by_id.items():
        if len(entries) > 1:
            raise CitationError(f"{info.part} contains duplicate note ID {note_id}")
    insert_at = 0
    for note_id in (-1, 0):
        note_type, marker = expected[note_id]
        entries = notes_by_id.get(note_id, [])
        if entries:
            node = entries[0]
            if node.get(W + "type") != note_type or node.find(f".//{W}{marker}") is None:
                raise CitationError(f"{info.part} has a conflicting reserved note ID {note_id}")
            if root.index(node) != insert_at:
                raise CitationError(f"{info.part} reserved note ID {note_id} is out of order")
        else:
            root.insert(insert_at, _separator(info, note_id, note_type, marker))
        insert_at += 1

    pkg.put_tree(info.part, tree)
    _ensure_content_type(pkg, info.part, info.content_type)
    _ensure_relationship(pkg, info.relationship_type, info.part)
    return tree


def _ensure_styles(pkg: DocxPackage, info: KindInfo) -> None:
    part = "word/styles.xml"
    if pkg.has(part):
        tree = pkg.tree(part)
        root = tree.getroot()
        if root.tag != W + "styles":
            raise CitationError("word/styles.xml has an unexpected root")
    else:
        root = etree.Element(W + "styles", nsmap={"w": W_NS})
        tree = etree.ElementTree(root)
    styles = root.findall(W + "style")

    def find_style(style_id: str, style_type: str) -> etree._Element | None:
        matches = [node for node in styles if node.get(W + "styleId") == style_id]
        if len(matches) > 1:
            raise CitationError(f"duplicate style ID: {style_id}")
        if matches and matches[0].get(W + "type") != style_type:
            raise CitationError(f"style {style_id} has conflicting type")
        return matches[0] if matches else None

    changed = False
    if find_style(info.paragraph_style, "paragraph") is None:
        style = etree.Element(W + "style")
        style.set(W + "type", "paragraph")
        style.set(W + "styleId", info.paragraph_style)
        etree.SubElement(style, W + "name").set(W + "val", info.paragraph_style.lower())
        if find_style("Normal", "paragraph") is not None:
            etree.SubElement(style, W + "basedOn").set(W + "val", "Normal")
        etree.SubElement(style, W + "next").set(W + "val", info.paragraph_style)
        etree.SubElement(style, W + "uiPriority").set(W + "val", "99")
        etree.SubElement(style, W + "semiHidden")
        etree.SubElement(style, W + "unhideWhenUsed")
        rpr = etree.SubElement(style, W + "rPr")
        etree.SubElement(rpr, W + "sz").set(W + "val", "18")
        etree.SubElement(rpr, W + "szCs").set(W + "val", "18")
        root.append(style)
        styles.append(style)
        changed = True
    if find_style(info.reference_style, "character") is None:
        style = etree.Element(W + "style")
        style.set(W + "type", "character")
        style.set(W + "styleId", info.reference_style)
        etree.SubElement(style, W + "name").set(W + "val", info.reference_style.lower())
        if find_style("DefaultParagraphFont", "character") is not None:
            etree.SubElement(style, W + "basedOn").set(W + "val", "DefaultParagraphFont")
        etree.SubElement(style, W + "uiPriority").set(W + "val", "99")
        etree.SubElement(style, W + "semiHidden")
        etree.SubElement(style, W + "unhideWhenUsed")
        rpr = etree.SubElement(style, W + "rPr")
        etree.SubElement(rpr, W + "vertAlign").set(W + "val", "superscript")
        root.append(style)
        changed = True
    if changed or not pkg.has(part):
        pkg.put_tree(part, tree)
    _ensure_content_type(pkg, part, STYLE_CT)
    _ensure_relationship(pkg, f"{REL_BASE}/styles", part)


def _reference_run(info: KindInfo, note_id: int) -> etree._Element:
    run = etree.Element(W + "r")
    rpr = etree.SubElement(run, W + "rPr")
    etree.SubElement(rpr, W + "rStyle").set(W + "val", info.reference_style)
    etree.SubElement(rpr, W + "vertAlign").set(W + "val", "superscript")
    etree.SubElement(run, W + info.ref).set(W + "id", str(note_id))
    return run


def _text_run(text: str) -> etree._Element:
    run = etree.Element(W + "r")
    node = etree.SubElement(run, W + "t")
    _set_text(node, text)
    return run


def _note_node(info: KindInfo, note_id: int, paragraphs: list[str]) -> etree._Element:
    note = etree.Element(W + info.singular)
    note.set(W + "id", str(note_id))
    for index, text in enumerate(paragraphs):
        paragraph = etree.SubElement(note, W + "p")
        ppr = etree.SubElement(paragraph, W + "pPr")
        etree.SubElement(ppr, W + "pStyle").set(W + "val", info.paragraph_style)
        if index == 0:
            marker_run = etree.SubElement(paragraph, W + "r")
            marker_rpr = etree.SubElement(marker_run, W + "rPr")
            etree.SubElement(marker_rpr, W + "rStyle").set(W + "val", info.reference_style)
            etree.SubElement(marker_rpr, W + "vertAlign").set(W + "val", "superscript")
            etree.SubElement(marker_run, W + info.mark)
            run = etree.SubElement(paragraph, W + "r")
            etree.SubElement(run, W + "tab")
            node = etree.SubElement(run, W + "t")
            _set_text(node, text)
        else:
            paragraph.append(_text_run(text))
    return note


def _note_paragraphs(note: etree._Element) -> list[str]:
    values = []
    for paragraph in note.findall(W + "p"):
        values.append("".join(node.text or "" for node in paragraph.iter(W + "t")))
    return values


def _supported_note(note: etree._Element, info: KindInfo) -> bool:
    allowed = {
        info.singular, "p", "pPr", "pStyle", "r", "rPr", "rStyle",
        "vertAlign", "t", "tab", info.mark,
    }
    return all(_local(node) in allowed for node in note.iter())


@dataclass
class TextSegment:
    start: int
    end: int
    text_node: etree._Element | None
    run: etree._Element | None
    safe: bool


def _paragraph_map(
    paragraph: etree._Element, field_runs: set[etree._Element],
) -> tuple[str, list[TextSegment]]:
    text = ""
    segments: list[TextSegment] = []
    for child in paragraph:
        if child.tag == W + "pPr":
            continue
        nodes = list(child.iter(W + "t"))
        child_text = "".join(node.text or "" for node in nodes)
        safe = (
            child.tag == W + "r"
            and child not in field_runs
            and len(nodes) == 1
            and all(node.tag in {W + "rPr", W + "t"} for node in child)
        )
        start = len(text)
        text += child_text
        if child_text:
            segments.append(
                TextSegment(start, len(text), nodes[0] if safe else None, child if safe else None, safe)
            )
        elif child.tag != W + "r" or any(node.tag != W + "rPr" for node in child):
            # A semantic object between text runs is a barrier even if it has no text.
            text += "\u0000"
            segments.append(TextSegment(start, len(text), None, None, False))
    return text, segments


def _find_all(value: str, needle: str) -> Iterable[int]:
    start = 0
    while True:
        index = value.find(needle, start)
        if index < 0:
            return
        yield index
        start = index + 1


def _locate_anchor(
    document: etree._ElementTree, anchor: dict[str, Any]
) -> tuple[etree._Element, list[TextSegment], int, int]:
    needle = anchor.get("text")
    if not isinstance(needle, str) or not needle or "\u0000" in needle:
        raise CitationError("anchor.text must be a non-empty string")
    occurrence = anchor.get("occurrence")
    if occurrence is not None and (not isinstance(occurrence, int) or occurrence < 1):
        raise CitationError("anchor.occurrence must be a positive 1-based integer")
    position = anchor.get("position", "after")
    if position not in {"before", "after"}:
        raise CitationError("anchor.position must be 'before' or 'after'")

    body = document.getroot().find("w:body", namespaces=NS)
    if body is None:
        raise CitationError("word/document.xml has no w:body")
    # Complex fields use sibling runs; their result text looks like ordinary
    # text. Track nesting across paragraphs as fields can span paragraphs.
    field_runs: set[etree._Element] = set()
    field_depth = 0
    for node in body.iter():
        if node.tag == W + "r" and field_depth:
            field_runs.add(node)
        elif node.tag == W + "fldChar":
            kind = node.get(W + "fldCharType")
            if kind == "begin":
                field_depth += 1
            elif kind == "end":
                field_depth = max(0, field_depth - 1)
    matches: list[tuple[etree._Element, list[TextSegment], int, int]] = []
    for paragraph in body.iter(W + "p"):
        text, segments = _paragraph_map(paragraph, field_runs)
        for start in _find_all(text, needle):
            end = start + len(needle)
            ancestor = paragraph.getparent()
            while ancestor is not None and ancestor is not body:
                if _local(ancestor) in {
                    "sdt", "sdtContent", "ins", "del", "moveFrom", "moveTo",
                    "customXml", "smartTag",
                }:
                    raise CitationError(
                        f"anchor {needle!r} is inside an SDT, revision, or complex container"
                    )
                ancestor = ancestor.getparent()
            touched = [seg for seg in segments if seg.start < end and seg.end > start]
            if not touched or any(not seg.safe for seg in touched):
                raise CitationError(
                    f"anchor {needle!r} crosses a field, hyperlink, revision, SDT, or complex run"
                )
            matches.append((paragraph, segments, start, end))
    if not matches:
        raise CitationError(f"anchor not found: {needle!r}")
    if occurrence is None:
        if len(matches) != 1:
            raise CitationError(
                f"anchor is ambiguous ({len(matches)} matches); set anchor.occurrence"
            )
        return matches[0]
    if occurrence > len(matches):
        raise CitationError(
            f"anchor.occurrence {occurrence} exceeds {len(matches)} matches for {needle!r}"
        )
    return matches[occurrence - 1]


def _insert_at_boundary(
    paragraph: etree._Element,
    segments: list[TextSegment],
    boundary: int,
    reference: etree._Element,
) -> None:
    for segment in segments:
        if segment.start <= boundary <= segment.end and segment.safe:
            run = segment.run
            node = segment.text_node
            assert run is not None and node is not None
            offset = boundary - segment.start
            value = node.text or ""
            parent = run.getparent()
            if parent is not paragraph:
                raise CitationError("anchor run is not a direct paragraph child")
            index = parent.index(run)
            if offset == 0:
                parent.insert(index, reference)
            elif offset == len(value):
                parent.insert(index + 1, reference)
            else:
                left, right = value[:offset], value[offset:]
                _set_text(node, left)
                right_run = copy.deepcopy(run)
                right_nodes = list(right_run.iter(W + "t"))
                if len(right_nodes) != 1:
                    raise CitationError("cannot safely split anchor run")
                _set_text(right_nodes[0], right)
                parent.insert(index + 1, reference)
                parent.insert(index + 2, right_run)
            return
    raise CitationError("cannot resolve anchor boundary")


def _document_tree(pkg: DocxPackage) -> etree._ElementTree:
    tree = pkg.tree("word/document.xml")
    if tree.getroot().tag != W + "document":
        raise CitationError("word/document.xml has an unexpected root")
    return tree


def _user_notes(root: etree._Element, info: KindInfo) -> list[etree._Element]:
    result = []
    for note in root.findall(W + info.singular):
        try:
            note_id = int(note.get(W + "id", ""))
        except ValueError:
            continue
        if note_id > 0 and not note.get(W + "type"):
            result.append(note)
    return result


def _existing_note_state(pkg: DocxPackage, info: KindInfo) -> bool:
    if pkg.has(info.part):
        tree = pkg.tree(info.part)
        if _user_notes(tree.getroot(), info):
            return True
    document = _document_tree(pkg)
    return any(document.getroot().iter(W + info.ref))


def _has_note_configuration(pkg: DocxPackage, info: KindInfo) -> bool:
    if pkg.has("word/settings.xml"):
        settings = pkg.tree("word/settings.xml").getroot()
        if settings.find(W + info.property_name) is not None:
            return True
    document = _document_tree(pkg)
    return any(
        section.find(W + info.property_name) is not None
        for section in document.getroot().iter(W + "sectPr")
    )


def _next_note_id(root: etree._Element, info: KindInfo) -> int:
    values = []
    for note in root.findall(W + info.singular):
        try:
            value = int(note.get(W + "id", ""))
        except ValueError as exc:
            raise CitationError(f"{info.part} contains an invalid note ID") from exc
        if value > 0:
            values.append(value)
    return max(values, default=0) + 1


def _settings_tree(pkg: DocxPackage) -> etree._ElementTree:
    part = "word/settings.xml"
    if pkg.has(part):
        tree = pkg.tree(part)
        if tree.getroot().tag != W + "settings":
            raise CitationError("word/settings.xml has an unexpected root")
    else:
        tree = etree.ElementTree(etree.Element(W + "settings", nsmap={"w": W_NS}))
    _ensure_content_type(pkg, part, SETTINGS_CT)
    _ensure_relationship(pkg, f"{REL_BASE}/settings", part)
    return tree


def _ensure_property_container(
    parent: etree._Element, info: KindInfo, order: list[str]
) -> etree._Element:
    matches = parent.findall(W + info.property_name)
    if len(matches) > 1:
        raise CitationError(f"duplicate {info.property_name}")
    if matches:
        return matches[0]
    node = etree.Element(W + info.property_name)
    _insert_ordered(parent, node, order)
    return node


def _set_property(container: etree._Element, name: str, value: str) -> None:
    matches = container.findall(W + name)
    if len(matches) > 1:
        raise CitationError(f"duplicate note property: {name}")
    node = matches[0] if matches else etree.Element(W + name)
    node.set(W + "val", value)
    if not matches:
        _insert_ordered(container, node, NOTE_PR_ORDER)


def _set_property_if_missing(container: etree._Element, name: str, value: str) -> bool:
    matches = container.findall(W + name)
    if len(matches) > 1:
        raise CitationError(f"duplicate note property: {name}")
    if matches:
        return False
    node = etree.Element(W + name)
    node.set(W + "val", value)
    _insert_ordered(container, node, NOTE_PR_ORDER)
    return True


def _ensure_reserved_property_refs(container: etree._Element, info: KindInfo) -> None:
    existing = [node.get(W + "id") for node in container.findall(W + info.singular)]
    for value in ("-1", "0"):
        if value not in existing:
            node = etree.Element(W + info.singular)
            node.set(W + "id", value)
            _insert_ordered(container, node, NOTE_PR_ORDER)


def _configure(pkg: DocxPackage, operation: dict[str, Any]) -> dict[str, Any]:
    info = _kind(operation)
    scope = operation.get("scope", {"type": "document"})
    if not isinstance(scope, dict) or scope.get("type") not in {"document", "section"}:
        raise CitationError("configure.scope.type must be 'document' or 'section'")
    values = {
        "pos": operation.get("position"),
        "numFmt": operation.get("number_format"),
        "numStart": operation.get("start"),
        "numRestart": operation.get("restart"),
    }
    if all(value is None for value in values.values()):
        raise CitationError("configure requires at least one property")
    if values["pos"] is not None and values["pos"] not in info.positions:
        raise CitationError(f"invalid {info.kind} position: {values['pos']!r}")
    if values["numFmt"] is not None and values["numFmt"] not in SAFE_NUMBER_FORMATS:
        raise CitationError(f"unsupported number_format: {values['numFmt']!r}")
    if values["numStart"] is not None and (
        not isinstance(values["numStart"], int) or values["numStart"] < 1
    ):
        raise CitationError("configure.start must be a positive integer")
    if values["numRestart"] is not None and values["numRestart"] not in RESTART_VALUES:
        raise CitationError(f"invalid restart value: {values['numRestart']!r}")

    if scope["type"] == "document":
        tree = _settings_tree(pkg)
        container = _ensure_property_container(tree.getroot(), info, SETTINGS_ORDER)
        _ensure_reserved_property_refs(container, info)
        part = "word/settings.xml"
    else:
        index = scope.get("index")
        if not isinstance(index, int) or index < 1:
            raise CitationError("section scope requires a positive 1-based index")
        tree = _document_tree(pkg)
        sections = list(tree.getroot().iter(W + "sectPr"))
        if index > len(sections):
            raise CitationError(f"section index {index} exceeds {len(sections)} sections")
        container = _ensure_property_container(sections[index - 1], info, SECTPR_ORDER)
        part = "word/document.xml"

    for name, value in values.items():
        if value is not None:
            _set_property(container, name, str(value))
    pkg.put_tree(part, tree)
    mirrored_sections = 0
    if scope["type"] == "document":
        # LibreOffice ignores some settings-level note properties (notably the
        # endnote number format). Mirroring the requested values to every
        # current section keeps Word/LibreOffice rendering aligned while the
        # settings-level container remains the document default.
        document = _document_tree(pkg)
        for section in document.getroot().iter(W + "sectPr"):
            section_container = _ensure_property_container(section, info, SECTPR_ORDER)
            section_changed = False
            for name, value in values.items():
                if value is not None:
                    section_changed = (
                        _set_property_if_missing(section_container, name, str(value))
                        or section_changed
                    )
            if section_changed:
                mirrored_sections += 1
        pkg.put_tree("word/document.xml", document)
    return {
        "op": "configure", "kind": info.kind, "scope": scope,
        "changed": True, "mirrored_sections": mirrored_sections,
    }


def _default_configuration(pkg: DocxPackage, info: KindInfo) -> None:
    operation = {
        "op": "configure",
        "kind": info.kind,
        "scope": {"type": "document"},
        "number_format": "decimal",
        "start": 1,
        "restart": "continuous",
        "position": info.default_position,
    }
    _configure(pkg, operation)


def _kind(operation: dict[str, Any]) -> KindInfo:
    kind = operation.get("kind")
    if kind not in KINDS:
        raise CitationError("kind must be 'footnote' or 'endnote'")
    return KINDS[kind]


def _paragraph_input(operation: dict[str, Any]) -> list[str]:
    paragraphs = operation.get("paragraphs")
    if (
        not isinstance(paragraphs, list) or not paragraphs
        or any(not isinstance(value, str) for value in paragraphs)
        or not any(value for value in paragraphs)
    ):
        raise CitationError("paragraphs must be a non-empty array containing text")
    return paragraphs


def _add(pkg: DocxPackage, operation: dict[str, Any]) -> dict[str, Any]:
    info = _kind(operation)
    paragraphs = _paragraph_input(operation)
    anchor = operation.get("anchor")
    if not isinstance(anchor, dict):
        raise CitationError("add requires an anchor object")
    had_notes_or_config = _existing_note_state(pkg, info) or _has_note_configuration(pkg, info)
    document = _document_tree(pkg)
    paragraph, segments, start, end = _locate_anchor(document, anchor)
    notes = _ensure_notes_part(pkg, info)
    _ensure_styles(pkg, info)
    note_id = _next_note_id(notes.getroot(), info)
    notes.getroot().append(_note_node(info, note_id, paragraphs))
    position = anchor.get("position", "after")
    _insert_at_boundary(
        paragraph, segments, start if position == "before" else end,
        _reference_run(info, note_id),
    )
    pkg.put_tree("word/document.xml", document)
    pkg.put_tree(info.part, notes)
    if not had_notes_or_config:
        _default_configuration(pkg, info)
    return {"op": "add", "kind": info.kind, "id": note_id, "paragraphs": len(paragraphs)}


def _find_definition(pkg: DocxPackage, info: KindInfo, note_id: int) -> tuple[etree._ElementTree, etree._Element]:
    if not pkg.has(info.part):
        raise CitationError(f"{info.part} is missing")
    tree = pkg.tree(info.part)
    matches = [
        node for node in tree.getroot().findall(W + info.singular)
        if node.get(W + "id") == str(note_id)
    ]
    if len(matches) != 1:
        raise CitationError(f"expected one {info.kind} definition with ID {note_id}, got {len(matches)}")
    if note_id <= 0 or matches[0].get(W + "type"):
        raise CitationError("reserved/special notes cannot be updated or deleted")
    return tree, matches[0]


def _note_id(operation: dict[str, Any]) -> int:
    value = operation.get("id")
    if not isinstance(value, int) or value < 1:
        raise CitationError("id must be a positive integer returned by inspect")
    return value


def _update(pkg: DocxPackage, operation: dict[str, Any]) -> dict[str, Any]:
    info = _kind(operation)
    note_id = _note_id(operation)
    paragraphs = _paragraph_input(operation)
    tree, note = _find_definition(pkg, info, note_id)
    if not _supported_note(note, info):
        raise CitationError(f"{info.kind} ID {note_id} contains unsupported rich content")
    replacement = _note_node(info, note_id, paragraphs)
    note.getparent().replace(note, replacement)
    _ensure_styles(pkg, info)
    pkg.put_tree(info.part, tree)
    return {"op": "update", "kind": info.kind, "id": note_id, "paragraphs": len(paragraphs)}


def _delete(pkg: DocxPackage, operation: dict[str, Any]) -> dict[str, Any]:
    info = _kind(operation)
    note_id = _note_id(operation)
    tree, note = _find_definition(pkg, info, note_id)
    note.getparent().remove(note)
    document = _document_tree(pkg)
    references = [
        node for node in document.getroot().iter(W + info.ref)
        if node.get(W + "id") == str(note_id)
    ]
    for reference in references:
        run = reference.getparent()
        if run is not None and run.tag == W + "r":
            run.remove(reference)
            if all(child.tag == W + "rPr" for child in run):
                run.getparent().remove(run)
        else:
            reference.getparent().remove(reference)
    pkg.put_tree(info.part, tree)
    pkg.put_tree("word/document.xml", document)
    return {"op": "delete", "kind": info.kind, "id": note_id, "references_removed": len(references)}


def _property_dict(container: etree._Element | None) -> dict[str, Any] | None:
    if container is None:
        return None
    result: dict[str, Any] = {}
    for name in ("pos", "numFmt", "numStart", "numRestart"):
        node = container.find(W + name)
        if node is not None:
            value: Any = node.get(W + "val")
            if name == "numStart" and value is not None:
                try:
                    value = int(value)
                except ValueError:
                    pass
            result[name] = value
    return result


def _paragraph_context(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(W + "t"))


def _reference_offset(paragraph: etree._Element, reference: etree._Element) -> int | None:
    offset = 0
    for node in paragraph.iter():
        if node is reference:
            return offset
        if node.tag == W + "t":
            offset += len(node.text or "")
    return None


def _inspect_kind(pkg: DocxPackage, info: KindInfo) -> dict[str, Any]:
    definitions = []
    if pkg.has(info.part):
        tree = pkg.tree(info.part)
        for note in _user_notes(tree.getroot(), info):
            note_id = int(note.get(W + "id"))
            definitions.append({
                "id": note_id,
                "paragraphs": _note_paragraphs(note),
                "complex_content": not _supported_note(note, info),
            })
    document = _document_tree(pkg)
    body = document.getroot().find("w:body", namespaces=NS)
    paragraphs = list(body.iter(W + "p")) if body is not None else []
    paragraph_indexes = {id(node): index + 1 for index, node in enumerate(paragraphs)}
    references = []
    for reference in document.getroot().iter(W + info.ref):
        paragraph = reference
        while paragraph is not None and paragraph.tag != W + "p":
            paragraph = paragraph.getparent()
        context = _paragraph_context(paragraph) if paragraph is not None else ""
        offset = _reference_offset(paragraph, reference) if paragraph is not None else None
        references.append({
            "id": _parse_int(reference.get(W + "id")),
            "paragraph": paragraph_indexes.get(id(paragraph)) if paragraph is not None else None,
            "char_offset": offset,
            "before": context[max(0, (offset or 0) - 40):(offset or 0)] if offset is not None else "",
            "after": context[offset:offset + 40] if offset is not None else "",
            "context": context,
        })

    document_config = None
    if pkg.has("word/settings.xml"):
        settings = pkg.tree("word/settings.xml").getroot()
        document_config = _property_dict(settings.find(W + info.property_name))
    section_configs = []
    for index, section in enumerate(document.getroot().iter(W + "sectPr"), start=1):
        value = _property_dict(section.find(W + info.property_name))
        if value is not None:
            section_configs.append({"section": index, **value})
    return {
        "part_present": pkg.has(info.part),
        "definitions": definitions,
        "references": references,
        "configuration": {
            "document": document_config,
            "sections": section_configs,
            "implicit_default": {
                "position": info.default_position,
                "numFmt": "decimal" if info.kind == "footnote" else "lowerRoman",
                "numStart": 1,
                "numRestart": "continuous",
            },
        },
    }


def _parse_int(value: str | None) -> int | str | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return value


def _issue(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def _validate_property_container(
    container: etree._Element,
    info: KindInfo,
    location: str,
    *,
    allow_reserved_refs: bool = False,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    positions = []
    for child in container:
        name = _local(child)
        if name in NOTE_PR_ORDER:
            positions.append(NOTE_PR_ORDER.index(name))
    if positions != sorted(positions):
        issues.append(_issue("error", "NOTE_PROPERTY_ORDER", f"{location} child order is invalid"))
    values = {}
    for name in ("pos", "numFmt", "numStart", "numRestart"):
        matches = container.findall(W + name)
        if len(matches) > 1:
            issues.append(_issue(
                "error", "NOTE_PROPERTY_DUPLICATE",
                f"{location} contains duplicate {name}",
            ))
        values[name] = matches[0] if matches else None
    reserved_refs = container.findall(W + info.singular)
    if reserved_refs and not allow_reserved_refs:
        issues.append(_issue(
            "error", "NOTE_PROPERTY_RESERVED_REF",
            f"{location} cannot contain {info.singular} separator references",
        ))
    elif reserved_refs:
        ids = [node.get(W + "id") for node in reserved_refs]
        duplicates = sorted(value for value, count in Counter(ids).items() if value and count > 1)
        if duplicates or any(value not in {"-1", "0"} for value in ids):
            issues.append(_issue(
                "error", "NOTE_PROPERTY_RESERVED_REF",
                f"{location} has invalid/duplicate separator references",
            ))
    if values["pos"] is not None and values["pos"].get(W + "val") not in info.positions:
        issues.append(_issue("error", "NOTE_POSITION", f"{location} has invalid position"))
    if values["numFmt"] is not None:
        value = values["numFmt"].get(W + "val")
        if not value:
            issues.append(_issue("error", "NOTE_NUMBER_FORMAT", f"{location} has empty numFmt"))
        elif value not in SAFE_NUMBER_FORMATS:
            issues.append(_issue("warning", "NOTE_NUMBER_FORMAT_UNKNOWN", f"{location} uses unrecognized numFmt {value!r}"))
    if values["numStart"] is not None:
        try:
            start = int(values["numStart"].get(W + "val", ""))
        except ValueError:
            start = 0
        if start < 1:
            issues.append(_issue("error", "NOTE_NUMBER_START", f"{location} has invalid numStart"))
    if values["numRestart"] is not None and values["numRestart"].get(W + "val") not in RESTART_VALUES:
        issues.append(_issue("error", "NOTE_NUMBER_RESTART", f"{location} has invalid numRestart"))
    return issues


def _validate_relationship_and_type(pkg: DocxPackage, info: KindInfo) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    rels = _relationships(pkg).getroot().findall(PKG_REL + "Relationship")
    matches = [node for node in rels if node.get("Type") == info.relationship_type]
    if pkg.has(info.part):
        if len(matches) != 1:
            issues.append(_issue("error", "NOTE_RELATIONSHIP", f"{info.part} requires exactly one relationship"))
        elif (
            matches[0].get("TargetMode", "Internal") != "Internal"
            or _canonical_relationship_target(matches[0].get("Target") or "") != info.part
        ):
            issues.append(_issue("error", "NOTE_RELATIONSHIP_TARGET", f"{info.part} relationship target is invalid"))
    elif matches:
        issues.append(_issue("error", "ORPHAN_NOTE_RELATIONSHIP", f"relationship exists but {info.part} is missing"))
    tree = _content_types(pkg)
    part_name = "/" + info.part
    overrides = [
        node for node in tree.getroot().findall(CT + "Override")
        if urllib.parse.unquote(node.get("PartName") or "") == part_name
    ]
    if pkg.has(info.part):
        if len(overrides) != 1 or overrides[0].get("ContentType") != info.content_type:
            issues.append(_issue("error", "NOTE_CONTENT_TYPE", f"{info.part} Content Type is missing or conflicting"))
    elif overrides:
        issues.append(_issue("error", "ORPHAN_NOTE_CONTENT_TYPE", f"Content Type exists but {info.part} is missing"))
    return issues


def _validate_notes(pkg: DocxPackage) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    for name in sorted(pkg.names()):
        if name.endswith(".xml") or name.endswith(".rels"):
            try:
                _xml(pkg.read(name), name)
            except CitationError as exc:
                issues.append(_issue("error", "XML_PARSE", str(exc)))
    if issues:
        # Later semantic checks assume parsed trees. Return every parse failure
        # together instead of raising a secondary, less useful exception.
        return {"ok": False, "errors": issues, "warnings": []}
    try:
        document = _document_tree(pkg)
    except CitationError as exc:
        return {"ok": False, "errors": [_issue("error", "DOCUMENT", str(exc))], "warnings": []}
    body = document.getroot().find("w:body", namespaces=NS)
    if body is None:
        issues.append(_issue("error", "BODY_MISSING", "word/document.xml has no w:body"))
    else:
        direct_sections = [index for index, node in enumerate(body) if node.tag == W + "sectPr"]
        if len(direct_sections) > 1 or (direct_sections and direct_sections[0] != len(body) - 1):
            issues.append(_issue("error", "SECTPR_ORDER", "direct body sectPr must be unique and last"))

    relationship_nodes = _relationships(pkg).getroot().findall(PKG_REL + "Relationship")
    relationship_ids = [node.get("Id") for node in relationship_nodes]
    if any(not value for value in relationship_ids):
        issues.append(_issue(
            "error", "RELATIONSHIP_ID", "document relationships contain an empty ID",
        ))
    duplicate_relationship_ids = sorted(
        value for value, count in Counter(relationship_ids).items() if value and count > 1
    )
    if duplicate_relationship_ids:
        issues.append(_issue(
            "error", "RELATIONSHIP_ID",
            f"document relationships contain duplicate IDs: {duplicate_relationship_ids}",
        ))

    for info in KINDS.values():
        issues.extend(_validate_relationship_and_type(pkg, info))
        reference_ids: list[int] = []
        for reference in document.getroot().iter(W + info.ref):
            try:
                value = int(reference.get(W + "id", ""))
            except ValueError:
                issues.append(_issue("error", "NOTE_REFERENCE_ID", f"invalid {info.ref} ID"))
                continue
            if value <= 0:
                issues.append(_issue("error", "NOTE_REFERENCE_ID", f"{info.ref} ID must be positive"))
            reference_ids.append(value)

        definition_ids: list[int] = []
        if pkg.has(info.part):
            tree = pkg.tree(info.part)
            root = tree.getroot()
            if root.tag != W + info.plural:
                issues.append(_issue("error", "NOTE_ROOT", f"{info.part} has the wrong root"))
            else:
                all_ids: list[int] = []
                for note in root.findall(W + info.singular):
                    try:
                        note_id = int(note.get(W + "id", ""))
                    except ValueError:
                        issues.append(_issue("error", "NOTE_DEFINITION_ID", f"{info.part} has an invalid ID"))
                        continue
                    all_ids.append(note_id)
                    if note_id > 0 and not note.get(W + "type"):
                        definition_ids.append(note_id)
                        paragraphs = note.findall(W + "p")
                        if not paragraphs:
                            issues.append(_issue("error", "NOTE_EMPTY", f"{info.kind} ID {note_id} has no paragraph"))
                        elif paragraphs[0].find(f".//{W}{info.mark}") is None:
                            issues.append(_issue("error", "NOTE_MARK_MISSING", f"{info.kind} ID {note_id} lacks {info.mark}"))
                        if not _supported_note(note, info):
                            issues.append(_issue("warning", "NOTE_COMPLEX_CONTENT", f"{info.kind} ID {note_id} contains rich/unknown content"))
                    elif note_id < -1:
                        issues.append(_issue("error", "NOTE_RESERVED_ID", f"{info.part} has unsupported negative ID {note_id}"))
                duplicates = sorted(value for value, count in Counter(all_ids).items() if count > 1)
                if duplicates:
                    issues.append(_issue("error", "NOTE_DUPLICATE_ID", f"{info.part} duplicate IDs: {duplicates}"))
                expected = {
                    -1: ("separator", "separator"),
                    0: ("continuationSeparator", "continuationSeparator"),
                }
                for reserved, (note_type, marker) in expected.items():
                    matches = [node for node in root.findall(W + info.singular) if node.get(W + "id") == str(reserved)]
                    if len(matches) != 1 or matches[0].get(W + "type") != note_type or matches[0].find(f".//{W}{marker}") is None:
                        issues.append(_issue("error", "NOTE_SEPARATOR", f"{info.part} reserved ID {reserved} is missing or invalid"))

        definitions = set(definition_ids)
        references = set(reference_ids)
        missing = sorted(references - definitions)
        orphaned = sorted(definitions - references)
        if missing:
            issues.append(_issue("error", "NOTE_REFERENCE_MISSING", f"{info.kind} references missing definitions: {missing}"))
        if orphaned:
            issues.append(_issue("error", "NOTE_DEFINITION_ORPHAN", f"unreferenced {info.kind} definitions: {orphaned}"))
        repeated = sorted(value for value, count in Counter(reference_ids).items() if count > 1)
        if repeated:
            issues.append(_issue("warning", "NOTE_MULTIPLE_REFERENCES", f"{info.kind} IDs referenced multiple times: {repeated}"))

        if definition_ids:
            if not pkg.has("word/styles.xml"):
                issues.append(_issue(
                    "warning", "NOTE_STYLE_MISSING",
                    f"{info.kind} definitions exist but word/styles.xml is missing",
                ))
            else:
                styles_root = pkg.tree("word/styles.xml").getroot()
                expected_styles = {
                    info.paragraph_style: "paragraph",
                    info.reference_style: "character",
                }
                for style_id, style_type in expected_styles.items():
                    matches = [
                        node for node in styles_root.findall(W + "style")
                        if node.get(W + "styleId") == style_id
                    ]
                    if not matches:
                        issues.append(_issue(
                            "warning", "NOTE_STYLE_MISSING",
                            f"{info.kind} style {style_id} is missing",
                        ))
                    elif len(matches) > 1 or matches[0].get(W + "type") != style_type:
                        issues.append(_issue(
                            "error", "NOTE_STYLE_CONFLICT",
                            f"{info.kind} style {style_id} is duplicate or has the wrong type",
                        ))

        if pkg.has("word/settings.xml"):
            settings = pkg.tree("word/settings.xml").getroot()
            containers = settings.findall(W + info.property_name)
            if len(containers) > 1:
                issues.append(_issue("error", "NOTE_PROPERTY_DUPLICATE", f"duplicate document {info.property_name}"))
            elif containers:
                issues.extend(_validate_property_container(
                    containers[0], info, f"settings/{info.property_name}",
                    allow_reserved_refs=True,
                ))
        for index, section in enumerate(document.getroot().iter(W + "sectPr"), start=1):
            containers = section.findall(W + info.property_name)
            if len(containers) > 1:
                issues.append(_issue("error", "NOTE_PROPERTY_DUPLICATE", f"section {index} has duplicate {info.property_name}"))
            elif containers:
                issues.extend(_validate_property_container(
                    containers[0], info, f"section[{index}]/{info.property_name}"
                ))

    errors = [item for item in issues if item["level"] == "error"]
    warnings = [item for item in issues if item["level"] == "warning"]
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def inspect_package(pkg: DocxPackage, scope: str = "all") -> dict[str, Any]:
    validation = validate_package(pkg, scope)

    def safe(info: KindInfo) -> dict[str, Any]:
        try:
            return _inspect_kind(pkg, info)
        except CitationError as exc:
            return {
                "part_present": pkg.has(info.part),
                "definitions": [],
                "references": [],
                "configuration": None,
                "unavailable": str(exc),
            }

    return {
        "version": 1,
        "source": str(pkg.source),
        "validation_scope": scope,
        "footnotes": safe(KINDS["footnote"]),
        "endnotes": safe(KINDS["endnote"]),
        "cross_references": _xref_report(pkg) if scope != "notes" else None,
        "validation": validation,
    }


def _load_spec(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CitationError(f"cannot read operation spec {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise CitationError("spec.version must be 1")
    operations = value.get("operations")
    if not isinstance(operations, list) or not operations:
        raise CitationError("spec.operations must be a non-empty array")
    if any(not isinstance(operation, dict) for operation in operations):
        raise CitationError("each operation must be an object")
    return value


_xref_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,39}\Z")
_xref_REF = re.compile(r"\s*REF\s+([A-Za-z_][A-Za-z0-9_]*)\s+\\([nr])\s+\\h\s*", re.I)
_xref_PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
             "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd",
             "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
             "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
             "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap",
             "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]


def _xref_fail(message: str) -> None:
    raise CitationError(message)


def _xref_body_of(document):
    body = document.getroot().find(W + "body")
    if body is None:
        _xref_fail("document has no body")
    return body


def _xref_value(parent, path, default=None):
    node = parent.find(path, NS)
    return node.get(W + "val") if node is not None else default


def _xref_xml_check(pkg):
    for name in pkg.names():
        if name.endswith((".xml", ".rels")):
            pkg.tree(name)
    doc = _document_tree(pkg)
    body = _xref_body_of(doc)
    sections = body.findall(W + "sectPr")
    if len(sections) > 1 or (sections and sections[0] is not body[-1]):
        _xref_fail("body sectPr must be unique and last")
    return doc


def _xref_bookmark_paragraph(document, name):
    starts = document.xpath("//w:bookmarkStart[@w:name=$name]", namespaces=NS, name=name)
    if len(starts) != 1:
        _xref_fail(f"bookmark {name!r}: expected one start, found {len(starts)}")
    start = starts[0]
    ident = start.get(W + "id")
    if not ident or len(document.xpath("//w:bookmarkStart[@w:id=$id]", namespaces=NS, id=ident)) != 1:
        _xref_fail(f"bookmark {name!r}: duplicate/missing ID")
    ends = document.xpath("//w:bookmarkEnd[@w:id=$id]", namespaces=NS, id=ident)
    p = start.getparent()
    if len(ends) != 1 or ends[0].getparent() is not p or p.tag != W + "p":
        _xref_fail(f"bookmark {name!r}: expected a single-paragraph range")
    if p.getparent() is not _xref_body_of(document) or p.index(start) >= p.index(ends[0]):
        _xref_fail(f"bookmark {name!r}: unsupported container or reversed range")
    return p


def _xref_paragraph_label(pkg, document, paragraph):
    """Resolve only explicit decimal [%1] lists; reject guessed/inherited formats."""
    num_id = _xref_value(paragraph, "w:pPr/w:numPr/w:numId")
    level = _xref_value(paragraph, "w:pPr/w:numPr/w:ilvl", "0")
    if not num_id or level != "0" or not pkg.has("word/numbering.xml"):
        _xref_fail("reference target must use an explicit single-level numbered list")
    numbering = pkg.tree("word/numbering.xml")
    nums = numbering.xpath("/w:numbering/w:num[@w:numId=$id]", namespaces=NS, id=num_id)
    if len(nums) != 1:
        _xref_fail(f"missing/duplicate numId {num_id}")
    num = nums[0]
    aid = _xref_value(num, "w:abstractNumId")
    abstracts = numbering.xpath("/w:numbering/w:abstractNum[@w:abstractNumId=$id]", namespaces=NS, id=aid or "")
    if len(abstracts) != 1:
        _xref_fail("missing/duplicate abstract numbering")
    abstract = abstracts[0]
    levels = abstract.findall(W + "lvl")
    if (len(levels) != 1 or levels[0].get(W + "ilvl") != "0"
            or abstract.find(W + "numStyleLink") is not None
            or abstract.find(W + "styleLink") is not None):
        _xref_fail("only explicit single-level lists are supported")
    lvl = levels[0]
    if _xref_value(lvl, "w:numFmt") != "decimal" or _xref_value(lvl, "w:lvlText") != "[%1]":
        _xref_fail("reference numbering must be decimal with lvlText='[%1]'")
    if lvl.find(W + "isLgl") is not None or lvl.find(W + "lvlRestart") is not None:
        _xref_fail("unsupported list restart/legal numbering")
    start = _xref_value(lvl, "w:start", "1")
    overrides = num.findall(W + "lvlOverride")
    if overrides:
        if (len(overrides) != 1 or overrides[0].get(W + "ilvl") != "0"
                or len(overrides[0]) != 1 or overrides[0][0].tag != W + "startOverride"):
            _xref_fail("unsupported level override")
        start = _xref_value(overrides[0], "w:startOverride")
    try:
        count = int(start) - 1
    except (TypeError, ValueError):
        _xref_fail("invalid list starting number")
    if count < 0:
        _xref_fail("list starting number must be positive")
    # Style-inherited list members would make direct counting unreliable.
    if pkg.has("word/styles.xml") and pkg.tree("word/styles.xml").xpath(
        "//w:numPr/w:numId[@w:val=$id]", namespaces=NS, id=num_id
    ):
        _xref_fail("list is also referenced through styles; native editor refresh required")
    for p in _xref_body_of(document).iter(W + "p"):
        if _xref_value(p, "w:pPr/w:numPr/w:numId") != num_id:
            continue
        if p.getparent() is not _xref_body_of(document) or _xref_value(p, "w:pPr/w:numPr/w:ilvl", "0") != "0":
            _xref_fail("list contains a non-body or multilevel member")
        count += 1
        if p is paragraph:
            return f"[{count}]"
    _xref_fail("reference target is outside the main body")


def _xref_fields(document):
    """Scan complex and simple fields. Never edit nested/cross-paragraph fields."""
    stack = []
    result = []
    for node in _xref_body_of(document).iter():
        if node.tag == W + "fldSimple":
            result.append({"instruction": node.get(W + "instr", ""), "simple": node})
        elif node.tag == W + "fldChar":
            kind = node.get(W + "fldCharType")
            if kind == "begin":
                if stack:
                    stack[-1]["nested"] = True
                stack.append({"instruction": "", "begin": node, "nested": bool(stack)})
            elif kind == "separate" and stack:
                stack[-1]["separate"] = node
            elif kind == "end" and stack:
                field = stack.pop()
                field["end"] = node
                result.append(field)
        elif node.tag == W + "instrText" and stack and "separate" not in stack[-1]:
            stack[-1]["instruction"] += node.text or ""
    if stack:
        _xref_fail("unclosed field in document")
    return result


def _xref_field_result(field):
    simple = field.get("simple")
    if simple is not None:
        if simple.getparent().tag != W + "p":
            _xref_fail("unsupported simple field container")
        runs = list(simple)
    else:
        if field.get("nested") or "separate" not in field:
            _xref_fail("nested or result-less REF field is unsupported")
        sep, end = field["separate"].getparent(), field["end"].getparent()
        parent = sep.getparent()
        begin = field["begin"].getparent()
        if (parent.tag != W + "p" or end.getparent() is not parent
                or begin.getparent() is not parent or parent.index(sep) >= parent.index(end)):
            _xref_fail("cross-paragraph REF fields are unsupported")
        if any(child.tag not in {W + "rPr", W + "fldChar"} for run in (begin, sep, end) for child in run):
            _xref_fail("mixed field-boundary runs are unsupported")
        runs = list(parent)[parent.index(sep) + 1:parent.index(end)]
    if not runs or any(r.tag != W + "r" for r in runs):
        _xref_fail("REF result must consist of text runs")
    if any(c.tag not in {W + "rPr", W + "t"} for r in runs for c in r):
        _xref_fail("REF result contains rich content")
    texts = [n for r in runs for n in r.findall(W + "t")]
    if not texts:
        _xref_fail("REF result has no text cache")
    return texts


def _xref_ref_fields(document):
    for field in _xref_fields(document):
        instruction = field["instruction"]
        if not re.match(r"\s*REF\s", instruction, re.I):
            continue
        match = _xref_REF.fullmatch(instruction)
        if match is None:
            # These may reference ordinary text, captions, or hierarchical lists.
            yield field, None
        else:
            yield field, match[1]


def _xref_report(pkg):
    try:
        document = _xref_xml_check(pkg)
        reference_fields = list(_xref_ref_fields(document))
    except CitationError as exc:
        return {"ok": False, "references": [], "errors": [str(exc)], "warnings": []}
    errors, warnings, refs = [], [], []
    for field, name in reference_fields:
        if name is None:
            warnings.append(f"unsupported REF left unchanged: {field['instruction'].strip()}")
            continue
        try:
            p = _xref_bookmark_paragraph(document, name)
            label = _xref_paragraph_label(pkg, document, p)
            cached = "".join(n.text or "" for n in _xref_field_result(field))
            refs.append({"bookmark": name, "instruction": field['instruction'].strip(),
                         "cached": cached, "expected": label})
            if cached != label:
                errors.append(f"stale reference {name}: {cached!r} != {label!r}; run refresh")
        except CitationError as exc:
            errors.append(str(exc))
    return {"ok": not errors, "references": refs, "errors": errors, "warnings": warnings,
            "scope": "single-level decimal bracketed bibliography REF fields; not full Word validation"}


def _xref_text_size(pkg, paragraph):
    """Resolve the leading bibliography text's size, without guessing a default."""
    runs = [r for r in paragraph.findall(W + "r")
            if any((t.text or "").strip() for t in r.findall(W + "t"))]
    if not runs:
        _xref_fail("reference entry has no ordinary text to derive its number size from")
    run = runs[0]
    direct = _xref_value(run, "w:rPr/w:sz")
    if direct is not None:
        return direct
    if not pkg.has("word/styles.xml"):
        return None
    styles = pkg.tree("word/styles.xml")

    def style_size(style_id):
        seen = set()
        while style_id:
            if style_id in seen:
                _xref_fail("cyclic style inheritance while resolving reference size")
            seen.add(style_id)
            matches = styles.xpath("/w:styles/w:style[@w:styleId=$id]", namespaces=NS, id=style_id)
            if len(matches) != 1:
                _xref_fail("missing or duplicate style while resolving reference size")
            size = _xref_value(matches[0], "w:rPr/w:sz")
            if size is not None:
                return size
            style_id = _xref_value(matches[0], "w:basedOn")
        return None

    size = style_size(_xref_value(run, "w:rPr/w:rStyle"))
    if size is not None:
        return size
    paragraph_style = _xref_value(paragraph, "w:pPr/w:pStyle")
    if paragraph_style is None:
        defaults = styles.xpath('/w:styles/w:style[@w:type="paragraph"][@w:default="1"]/@w:styleId', namespaces=NS)
        paragraph_style = defaults[0] if len(defaults) == 1 else None
    size = style_size(paragraph_style)
    return size if size is not None else _xref_value(styles.getroot(), "w:docDefaults/w:rPrDefault/w:rPr/w:sz")


def _xref_sync_number_size(pkg, paragraph):
    size = _xref_text_size(pkg, paragraph)
    if size is None:
        return False  # Both text and number keep the application's inherited default.
    if not size.isdecimal() or int(size) <= 0:
        _xref_fail("invalid reference text size")
    # A level-level override takes precedence over paragraph-mark formatting.
    # Do not change a shared list definition to fix one bibliography entry.
    numbering = pkg.tree("word/numbering.xml")
    nid = _xref_value(paragraph, "w:pPr/w:numPr/w:numId")
    aids = numbering.xpath('/w:numbering/w:num[@w:numId=$id]/w:abstractNumId/@w:val', namespaces=NS, id=nid)
    if len(aids) != 1:
        _xref_fail("missing/duplicate numbering binding")
    rprs = numbering.xpath('/w:numbering/w:abstractNum[@w:abstractNumId=$id]/w:lvl[@w:ilvl="0"]/w:rPr', namespaces=NS, id=aids[0])
    for rpr in rprs:
        if rpr.find(W + "rStyle") is not None or _xref_value(rpr, "w:sz", size) != size:
            _xref_fail("number size is overridden by the list level; resolve that explicit format before syncing")
    pp = paragraph.find(W + "pPr")
    rpr = pp.find(W + "rPr")
    if rpr is None:
        rpr = etree.Element(W + "rPr")
        _insert_ordered(pp, rpr, _xref_PPR_ORDER)
    sizes = rpr.findall(W + "sz")
    if len(sizes) > 1:
        _xref_fail("duplicate paragraph-mark size")
    if sizes and sizes[0].get(W + "val") == size:
        return False
    node = sizes[0] if sizes else etree.Element(W + "sz")
    node.set(W + "val", size)
    if not sizes:
        _insert_ordered(rpr, node, ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
                                  "strike", "dstrike", "outline", "shadow", "emboss", "imprint", "noProof",
                                  "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
                                  "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd",
                                  "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout",
                                  "specVanish", "oMath", "rPrChange"])
    return True


def _xref_number_entries(pkg, document, op):
    entries = op.get("entries")
    if not isinstance(entries, list) or not entries:
        _xref_fail("number.entries must be a non-empty list of {text, bookmark}")
    selected = []
    existing_names = set(document.xpath("//w:bookmarkStart/@w:name", namespaces=NS))
    for entry in entries:
        if not isinstance(entry, dict):
            _xref_fail("each entry must be an object")
        name = entry.get("bookmark")
        if not isinstance(name, str) or not _xref_NAME.fullmatch(name) or name in existing_names:
            _xref_fail("bookmark must be a unique Word bookmark name (max 40 characters)")
        existing_names.add(name)
        p, _, _, _ = _locate_anchor(document, {"text": entry.get("text")})
        if p.getparent() is not _xref_body_of(document) or p in [v[0] for v in selected]:
            _xref_fail("each bibliography entry must be a distinct main-body paragraph")
        # Existing numbered/bounded paragraphs should be cited directly, not rebound.
        if p.xpath(".//w:bookmarkStart|.//w:bookmarkEnd|.//w:fldChar|.//w:fldSimple|./w:pPr/w:numPr", namespaces=NS):
            _xref_fail("number expects unnumbered paragraphs without bookmarks or fields; cite existing entries directly")
        if pkg.has("word/styles.xml"):
            styles = pkg.tree("word/styles.xml")
            style_id = _xref_value(p, "w:pPr/w:pStyle")
            seen = set()
            while style_id:
                if style_id in seen:
                    _xref_fail("cyclic paragraph style inheritance")
                seen.add(style_id)
                matches = styles.xpath("/w:styles/w:style[@w:styleId=$id]", namespaces=NS, id=style_id)
                if len(matches) != 1:
                    _xref_fail("missing or duplicate paragraph style")
                if matches[0].find("w:pPr/w:numPr", NS) is not None:
                    _xref_fail("bibliography paragraph inherits numbering; cannot rebind")
                style_id = _xref_value(matches[0], "w:basedOn")
        selected.append((p, name))
    part = "word/numbering.xml"
    numbering = pkg.tree(part) if pkg.has(part) else etree.ElementTree(etree.Element(W + "numbering", nsmap={"w": W_NS}))
    root = numbering.getroot()
    if root.tag != W + "numbering":
        _xref_fail("unexpected numbering root")
    aid = max([int(v) for v in root.xpath("w:abstractNum/@w:abstractNumId", namespaces=NS)], default=-1) + 1
    nid = max([int(v) for v in root.xpath("w:num/@w:numId", namespaces=NS)], default=0) + 1
    abstract = etree.Element(W + "abstractNum", {W + "abstractNumId": str(aid)})
    etree.SubElement(abstract, W + "multiLevelType").set(W + "val", "singleLevel")
    lvl = etree.SubElement(abstract, W + "lvl", {W + "ilvl": "0"})
    for name, val in [("start", "1"), ("numFmt", "decimal"), ("lvlText", "[%1]"), ("lvlJc", "left")]:
        etree.SubElement(lvl, W + name).set(W + "val", val)
    pp = etree.SubElement(lvl, W + "pPr")
    tabs = etree.SubElement(pp, W + "tabs")
    etree.SubElement(tabs, W + "tab", {W + "val": "num", W + "pos": "420"})
    etree.SubElement(pp, W + "ind", {W + "left": "420", W + "hanging": "420"})
    _insert_ordered(root, abstract, ["numPicBullet", "abstractNum", "num", "numIdMacAtCleanup"])
    num = etree.Element(W + "num", {W + "numId": str(nid)})
    etree.SubElement(num, W + "abstractNumId").set(W + "val", str(aid))
    _insert_ordered(root, num, ["numPicBullet", "abstractNum", "num", "numIdMacAtCleanup"])
    bid = max([int(v) for v in document.xpath("//w:bookmarkStart/@w:id|//w:bookmarkEnd/@w:id", namespaces=NS)], default=-1) + 1
    for p, name in selected:
        pp = p.find(W + "pPr")
        if pp is None:
            pp = etree.Element(W + "pPr")
            p.insert(0, pp)
        np = etree.Element(W + "numPr")
        etree.SubElement(np, W + "ilvl").set(W + "val", "0")
        etree.SubElement(np, W + "numId").set(W + "val", str(nid))
        _insert_ordered(pp, np, _xref_PPR_ORDER)
        p.insert(1, etree.Element(W + "bookmarkStart", {W + "id": str(bid), W + "name": name}))
        p.append(etree.Element(W + "bookmarkEnd", {W + "id": str(bid)}))
        bid += 1
    pkg.put_tree(part, numbering)
    _ensure_content_type(pkg, part, f"{CT_BASE}.numbering+xml")
    _ensure_relationship(pkg, f"{REL_BASE}/numbering", part)
    for p, _ in selected:
        _xref_sync_number_size(pkg, p)
    return {"op": "number", "num_id": nid, "bookmarks": [n for _, n in selected]}


def _xref_cite(pkg, document, op):
    name = op.get("bookmark")
    if not isinstance(name, str) or not _xref_NAME.fullmatch(name):
        _xref_fail("cite.bookmark must be a valid Word bookmark name")
    target = _xref_bookmark_paragraph(document, name)
    label = _xref_paragraph_label(pkg, document, target)
    anchor = op.get("anchor")
    if not isinstance(anchor, dict):
        _xref_fail("cite.anchor must be an object")
    p, segments, start, end = _locate_anchor(document, anchor)
    if p.getparent() is not _xref_body_of(document) or p is target:
        _xref_fail("citation must be in an ordinary main-body paragraph outside its target")
    superscript = op.get("superscript", True)
    if type(superscript) is not bool:
        _xref_fail("superscript must be boolean")
    boundary = start if anchor.get("position", "after") == "before" else end
    seg = next(s for s in segments if s.safe and s.start <= boundary <= s.end)
    original = seg.run.find(W + "rPr")
    rpr = copy.deepcopy(original) if original is not None else etree.Element(W + "rPr")
    for v in rpr.findall(W + "vertAlign"):
        rpr.remove(v)
    if superscript:
        etree.SubElement(rpr, W + "vertAlign").set(W + "val", "superscript")
    def run(child):
        r = etree.Element(W + "r")
        r.append(copy.deepcopy(rpr))
        r.append(child)
        return r
    begin = etree.Element(W + "fldChar", {W + "fldCharType": "begin", W + "dirty": "true"})
    instruction = etree.Element(W + "instrText", {XML_SPACE: "preserve"})
    instruction.text = f" REF {name} \\n \\h "
    text = etree.Element(W + "t")
    text.text = label
    runs = [run(begin), run(instruction), run(etree.Element(W + "fldChar", {W + "fldCharType": "separate"})),
            run(text), run(etree.Element(W + "fldChar", {W + "fldCharType": "end"}))]
    _insert_at_boundary(p, segments, boundary, runs[0])
    index = p.index(runs[0])
    for offset, r in enumerate(runs[1:], 1):
        p.insert(index + offset, r)
    return {"op": "cite", "bookmark": name, "label": label}


def _xref_refresh(pkg, document, operation=None):
    sync_size = (operation or {}).get("sync_number_size", False)
    if type(sync_size) is not bool:
        _xref_fail("sync_number_size must be boolean")
    count = 0
    targets = set()
    for field, name in _xref_ref_fields(document):
        if name is None:
            continue
        p = _xref_bookmark_paragraph(document, name)
        targets.add(p)
        label = _xref_paragraph_label(pkg, document, p)
        texts = _xref_field_result(field)
        _set_text(texts[0], label)
        for text in texts[1:]:
            _set_text(text, "")
        count += 1
    result = {"op": "refresh", "fields": count}
    if sync_size:
        result["number_sizes_synced"] = sum(_xref_sync_number_size(pkg, p) for p in targets)
    return result



def validate_package(pkg: DocxPackage, scope: str = "all") -> dict[str, Any]:
    if scope not in {"all", "notes", "references"}:
        raise CitationError(f"unsupported validation scope: {scope!r}")
    errors, warnings = [], []
    if scope in {"all", "notes"}:
        result = _validate_notes(pkg)
        errors.extend(result["errors"])
        warnings.extend(result["warnings"])
    if scope in {"all", "references"} and not any(e["code"] == "XML_PARSE" for e in errors):
        result = _xref_report(pkg)
        errors.extend(_issue("error", "CROSS_REFERENCE", m) for m in result["errors"])
        warnings.extend(_issue("warning", "CROSS_REFERENCE_UNSUPPORTED", m) for m in result["warnings"])
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def apply_spec(pkg: DocxPackage, spec: dict[str, Any]) -> dict[str, Any]:
    if (not isinstance(spec, dict) or type(spec.get("version")) is not int or spec["version"] != 1
            or not isinstance(spec.get("operations"), list) or not spec["operations"]
            or any(not isinstance(op, dict) for op in spec["operations"])):
        raise CitationError("spec requires version 1 and a non-empty array of operation objects")
    note_handlers = {"add": _add, "update": _update, "delete": _delete, "configure": _configure}
    reference_handlers = {"number": _xref_number_entries, "cite": _xref_cite}
    touches_notes = any(op.get("op") in note_handlers for op in spec["operations"])
    touches_references = any(op.get("op") in {"number", "cite", "refresh"} for op in spec["operations"])
    # The note validator intentionally supports a narrower subset of legacy note
    # packages. Bibliography-only edits preserve those parts without rewriting them.
    _xref_xml_check(pkg)
    results = []
    for index, operation in enumerate(spec["operations"], start=1):
        name = operation.get("op")
        try:
            if name in note_handlers:
                result = note_handlers[name](pkg, operation)
            else:
                document = _document_tree(pkg)
                if name in reference_handlers:
                    result = reference_handlers[name](pkg, document, operation)
                elif name == "refresh":
                    result = _xref_refresh(pkg, document, operation)
                else:
                    raise CitationError(f"unsupported op {name!r}")
                pkg.put_tree("word/document.xml", document)
            results.append(result)
        except CitationError as exc:
            raise CitationError(f"operation {index} ({name}): {exc}") from exc
    scope = "all" if touches_notes and touches_references else ("notes" if touches_notes else "references")
    validation = validate_package(pkg, scope)
    if not validation["ok"]:
        raise CitationError("result failed validation: " + validation["errors"][0]["message"])
    return {"changed": True, "operations": results, "validation": validation}


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="read notes, bibliography REF fields, and settings")
    inspect.add_argument("input", type=Path)
    validate = sub.add_parser("validate", help="check notes and bibliography references")
    validate.add_argument("input", type=Path)
    for command in (inspect, validate):
        command.add_argument("--scope", choices=["all", "notes", "references"], default="all",
                             help="validation scope; references leaves legacy note parts untouched")
    apply = sub.add_parser("apply", help="apply a versioned JSON operation batch transactionally")
    apply.add_argument("input", type=Path)
    apply.add_argument("--spec", type=Path, required=True)
    destination = apply.add_mutually_exclusive_group()
    destination.add_argument("--out", type=Path)
    destination.add_argument("--in-place", action="store_true")
    apply.add_argument("--dry-run", action="store_true")
    apply.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        pkg = DocxPackage(args.input.resolve())
        if args.command == "inspect":
            result = inspect_package(pkg, args.scope)
            _print(result)
            return 0 if result["validation"]["ok"] else 1
        if args.command == "validate":
            result = validate_package(pkg, args.scope)
            _print(result)
            return 0 if result["ok"] else 1

        spec = _load_spec(args.spec.resolve())
        result = apply_spec(pkg, spec)
        if args.dry_run:
            result["dry_run"] = True
            result["output"] = None
        else:
            if not args.in_place and args.out is None:
                raise CitationError("apply requires --out or --in-place unless --dry-run is set")
            destination = args.input.resolve() if args.in_place else args.out.resolve()
            if not args.in_place and destination == args.input.resolve():
                raise CitationError("use --in-place when input and output are the same path")
            pkg.write(destination, force=args.force or args.in_place)
            result["dry_run"] = False
            result["output"] = str(destination)
        _print(result)
        return 0
    except (CitationError, OSError, ValueError, TypeError) as exc:
        _print({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
