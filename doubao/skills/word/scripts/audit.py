#!/usr/bin/env python3
"""Audit Word OOXML content, format, and structure, optionally against a source.

There are only two modes:

* ``audit TARGET`` validates one newly-created document.
* ``audit TARGET --source SOURCE`` runs the same detectors on both files,
  suppresses unchanged non-fatal source findings, and also checks confidently
  added chapters against the source's consistent same-role formatting.

The complete JSON report is always printed to stdout; there is no report file.

The command performs package, OOXML, and optional word-count checks. Rendering
and visual review are separate workflow steps and are intentionally outside this
audit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import posixpath
import re
import sys
import unicodedata
import zlib
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile

try:
    from lxml import etree
except ImportError:
    etree = None  # type: ignore[assignment]

# The font resolution is self-contained in this module. Ensure this directory is
# importable whether audit.py is run as a file, a module, or imported from another
# working directory (kept for parity with the rest of the toolchain).
sys.path.insert(0, str(Path(__file__).resolve().parent))

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
V = "urn:schemas-microsoft-com:vml"
O = "urn:schemas-microsoft-com:office:office"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
DGM = "http://schemas.openxmlformats.org/drawingml/2006/diagram"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
STRICT_NAMESPACE_MAP = {
    "http://purl.oclc.org/ooxml/wordprocessingml/main": W,
    "http://purl.oclc.org/ooxml/officeDocument/relationships": R,
    "http://purl.oclc.org/ooxml/drawingml/main": A,
    "http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing": WP,
    "http://purl.oclc.org/ooxml/drawingml/chart": C,
    "http://purl.oclc.org/ooxml/drawingml/diagram": DGM,
}

NS = {
    "w": W,
    "r": R,
    "rel": REL,
    "w14": W14,
    "wp": WP,
    "a": A,
    "v": V,
    "o": O,
    "c": C,
    "dgm": DGM,
    "mc": MC,
}
UNDERSTOOD_MC_NAMESPACES = {
    W,
    R,
    WP,
    A,
    V,
    O,
    C,
    DGM,
    W14,
    "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "http://schemas.microsoft.com/office/word/2012/wordml",
    "http://schemas.microsoft.com/office/word/2018/wordml/cex",
    "http://schemas.microsoft.com/office/word/2016/wordml/cid",
    *STRICT_NAMESPACE_MAP.keys(),
}
# ISO/IEC 29500 schema sequences for the three table-property containers.
# Only known w: children participate in the relative-order check. This keeps
# extension elements and future/unknown WordprocessingML children from becoming
# false positives while still detecting every inversion among modeled children.
OOXML_PROPERTY_ORDER: dict[str, tuple[str, tuple[str, ...]]] = {
    "tblPr": (
        "E_OOXML_TBLPR_ORDER",
        (
            "tblStyle",
            "tblpPr",
            "tblOverlap",
            "bidiVisual",
            "tblStyleRowBandSize",
            "tblStyleColBandSize",
            "tblW",
            "jc",
            "tblCellSpacing",
            "tblInd",
            "tblBorders",
            "shd",
            "tblLayout",
            "tblCellMar",
            "tblLook",
            "tblCaption",
            "tblDescription",
            "tblPrChange",
        ),
    ),
    "tcPr": (
        "E_OOXML_TCPR_ORDER",
        (
            "cnfStyle",
            "tcW",
            "gridSpan",
            "hMerge",
            "vMerge",
            "tcBorders",
            "shd",
            "noWrap",
            "tcMar",
            "textDirection",
            "tcFitText",
            "vAlign",
            "hideMark",
            "headers",
            "cellIns",
            "cellDel",
            "cellMerge",
            "tcPrChange",
        ),
    ),
}
OOXML_PROPERTY_ORDER_REPAIR_HINT = (
    "Rebuild the reported property container in OOXML schema order. Do not blindly "
    "append property nodes; use a schema-aware API or insert each node before the "
    "first later-ranked child, regenerate the DOCX, and rerun the complete audit."
)

FATAL_PACKAGE_CODES = {
    "E_DOCX_OPEN",
    "E_ZIP_CRC",
    "E_ZIP_MEMBER_DUPLICATE",
    "E_PART_MISSING",
    "E_CONTENT_TYPE_INVALID",
    "E_XML_INVALID",
    "E_DOCUMENT_ROOT_INVALID",
}
# Fatal package findings remain unsuppressible because they make either the
# audit input itself or a source/target comparison unreliable. Every other
# detector finding participates in source-baseline subtraction in --source
# mode, including OOXML validity, content-policy, table, font, and word-count
# findings. Standalone mode continues to report all findings.
STORY_RE = re.compile(
    r"^word/(?:document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml$"
)
FIXED_STORY_RE = re.compile(r"^word/(?:header|footer)\d+\.xml$")
DELIVERABLE_TEXT_PART_RE = re.compile(
    r"^word/(?:document|header\d+|footer\d+|footnotes|endnotes)\.xml$"
)
LITERAL_STYLE_NAMES = {
    "code",
    "codeblock",
    "codechar",
    "htmlpreformatted",
    "preformattedtext",
    "sourcecode",
    "代码",
    "代码块",
    "代码字符",
    "源代码",
    "预格式化文本",
}
LITERAL_SDT_TAGS = {"audit:code", "audit:literal"}
TOC_FIELD_RE = re.compile(r"^\s*TOC(?=\s|\\|$)", re.IGNORECASE)
TOC_SDT_GALLERIES = {"table of contents", "目录"}
QUOTE_REPAIR_SAFETY_NOTE = (
    "Do not modify TOC fields, their placeholder text, or cached TOC entries "
    "when fixing quotes. Edit only the reported non-TOC w:t text nodes; never "
    "assign paragraph.text or run.text or rebuild entire paragraphs/runs for "
    "quote-only repairs. Preserve all field instructions, field boundaries, "
    "and hyperlinks."
)
CHINESE_LETTER_RATIO_THRESHOLD_NUMERATOR = 1
CHINESE_LETTER_RATIO_THRESHOLD_DENOMINATOR = 2
WORD_COUNT_CHINESE_PUNCTUATION = frozenset(
    "，。！？；：、（）《》〈〉“”‘’【】「」『』〔〕…—～·￥"
)
WORD_COUNT_ENGLISH_PUNCTUATION = frozenset(
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
)
WORD_COUNT_URL_TOKEN_RE = re.compile(r"^https?://[!-~]+")
WORD_COUNT_ASCII_COMPOUND_RE = re.compile(
    r"^[A-Za-z0-9]+(?:[._/@:-][A-Za-z0-9]+)+"
)
HAN_CODEPOINT_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x2F800, 0x2FA1F),
    (0x30000, 0x323AF),
)

# Built-in legacy-font blacklist: exact family names that modern Microsoft Word
# (macOS included) and clean Windows installs lack, so Word silently substitutes
# another face while the DOCX still records the legacy name. Values are the
# canonical replacement families. Matching folds case/width via family_identity;
# it deliberately does NOT strip arbitrary charset suffixes, so only names listed
# here are flagged.
FORBIDDEN_LEGACY_FONTS = {
    "楷体_GB2312": "楷体",
    "KaiTi_GB2312": "楷体",
    "仿宋_GB2312": "仿宋",
    "FangSong_GB2312": "仿宋",
    "黑体_GB2312": "黑体",
    "宋体_GB2312": "宋体",
    "方正黑体_GBK": "方正黑体",
}


class AuditError(ValueError):
    pass


def qn(namespace: str, local: str) -> str:
    return "{%s}%s" % (namespace, local)


def wqn(local: str) -> str:
    return qn(W, local)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_hash(value: Any) -> str:
    data = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(data)


def issue(
    severity: str,
    code: str,
    location: str,
    message: str,
    expected: Any = None,
    actual: Any = None,
    repair_hint: str | None = None,
    evidence: Any = None,
    blocking: bool | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "location": location,
        "message": message,
    }
    if expected is not None:
        item["expected"] = expected
    if actual is not None:
        item["actual"] = actual
    if repair_hint is not None:
        item["repair_hint"] = repair_hint
    if evidence is not None:
        item["evidence"] = evidence
    if blocking is not None:
        item["blocking"] = blocking
    return item


REPAIR_HINTS = {
    "E_ZIP_CRC": (
        "Recover or regenerate the DOCX package so every ZIP member passes CRC validation, then rerun audit."
    ),
    "E_ZIP_MEMBER_DUPLICATE": (
        "Rebuild the DOCX ZIP with exactly one entry for the reported part, then rerun audit."
    ),
    "E_PART_MISSING": (
        "Regenerate the DOCX with the required OOXML part and its content-type/relationship entries."
    ),
    "E_CONTENT_TYPE_INVALID": (
        "Declare the main document part in [Content_Types].xml with the "
        "WordprocessingML main-document content type (via a matching Default "
        "extension or an Override for its part name) so consumers open it as a "
        "Word document."
    ),
    "E_XML_INVALID": (
        "Repair or regenerate the reported XML part so it is well-formed OOXML, then rerun audit."
    ),
    "E_RELATIONSHIP_ID_INVALID": (
        "Assign a non-empty relationship Id in the reported .rels part, update its references, and rerun audit."
    ),
    "E_RELATIONSHIP_ID_DUPLICATE": (
        "Assign a unique Id to each Relationship in the reported .rels part and update every affected r:id/r:embed/r:link reference."
    ),
    "E_RELATIONSHIP_TYPE_INVALID": (
        "Set the relationship Type to a non-empty absolute URI that matches the referenced OOXML element."
    ),
    "E_RELATIONSHIP_TARGET_INVALID": (
        "Set a valid Target on the reported relationship or remove the unused relationship."
    ),
    "E_RELATIONSHIP_TARGET_OUTSIDE_PACKAGE": (
        "Replace the escaping internal Target with a valid in-package part path, or mark a genuinely external target as External."
    ),
    "E_RELATIONSHIP_TARGET_MISSING": (
        "Restore the referenced OOXML part or remove the unused relationship and its referring element."
    ),
    "E_RELATIONSHIP_REFERENCE_BROKEN": (
        "Declare the referenced relationship in the owning part's .rels file or remove the stale OOXML reference."
    ),
    "E_OFFICE_DOCUMENT_RELATIONSHIP_INVALID": (
        "Keep exactly one package-level officeDocument relationship pointing to the main Word document part."
    ),
    "E_OOXML_TBLPR_ORDER": OOXML_PROPERTY_ORDER_REPAIR_HINT,
    "E_OOXML_TCPR_ORDER": OOXML_PROPERTY_ORDER_REPAIR_HINT,
    "E_OOXML_DOCPR_ID_DUPLICATE": (
        "Assign a different non-negative integer wp:docPr/@id to every DrawingML object "
        "across document.xml, headers, footers, footnotes, endnotes, and comments, then rerun audit."
    ),
    "E_OOXML_DOCPR_ID_INVALID": (
        "Assign a non-negative integer wp:docPr/@id to the reported DrawingML object, then rerun audit."
    ),
    "E_NUMBERING_ABSTRACT_REFERENCE_BROKEN": (
        "Restore the referenced w:abstractNum definition or point the numbering instance to an existing abstractNumId."
    ),
    "E_NUMBERING_REFERENCE_BROKEN": (
        "Restore the referenced numbering instance or assign the paragraph an existing numId/ilvl pair."
    ),
    "E_PAGE_SIZE_INVALID": (
        "Use an unsigned OOXML twips or physical-measure token for page width and height."
    ),
    "E_TABLE_GRID_WIDTH_INVALID": (
        "Replace the invalid w:gridCol width with an unsigned OOXML twips or "
        "physical-measure token; 0 or an omitted width is allowed."
    ),
    "E_TABLE_PARAGRAPH_FIRST_LINE_INDENT": (
        "Set the effective first-line indent to zero for the reported table "
        "paragraph. Prefer a dedicated table-text paragraph style; otherwise set "
        "w:firstLine or w:firstLineChars to 0 directly on the paragraph."
    ),
    "E_FIELD_TYPE": (
        "Use only begin, separate, or end for w:fldCharType and preserve a balanced field sequence."
    ),
    "E_FIELD_UNBALANCED": (
        "Repair the field begin/separate/end sequence in the reported story part."
    ),
    "E_BOOKMARK_UNBALANCED": (
        "Restore a matching bookmarkStart/bookmarkEnd pair for the reported bookmark Id."
    ),
    "E_CHINESE_ASCII_DOUBLE_QUOTE": (
        "Replace the ASCII double quote with the context-appropriate Chinese opening "
        "or closing double quote. Use U+2033 DOUBLE PRIME instead when the character "
        "represents inches or arcseconds. " + QUOTE_REPAIR_SAFETY_NOTE
    ),
    "E_WORD_COUNT_OUT_OF_RANGE": (
        "Adjust the visible main-document text until word_count is within the "
        "requested inclusive min/max range, then rerun the complete audit."
    ),
    "E_FORBIDDEN_FONT_FAMILY": (
        "The resolved font family is a legacy name modern Microsoft Word lacks and "
        "silently substitutes. Replace it with the suggested canonical family (for "
        "example 楷体_GB2312 -> 楷体, 仿宋_GB2312 -> 仿宋) on the reported style, run, "
        "or theme mapping so Word renders the intended face."
    ),
    "E_FONT_EXPLICIT_VALUE_SHADOWED": (
        "The explicit font and theme font on the same effective w:rFonts layer "
        "resolve to different families. Remove the stale selector or align the "
        "theme mapping and explicit value with the intended font."
    ),
    "E_FONT_CJK_SCRIPT_MISMATCH": (
        "Chinese text resolves through a theme reference to a Japanese/Korean-script "
        "font (usually because themeFontLang eastAsia is ja-JP/ko-KR). Set an explicit "
        "Chinese eastAsia font on the affected style or run, or change themeFontLang "
        "eastAsia to Chinese (for example zh-CN/zh-TW)."
    ),
    "E_DOCUMENT_ROOT_INVALID": (
        "Restore a valid WordprocessingML w:document root in the main document part."
    ),
    "E_COMPARE_ADDED_CONTENT_STYLE_MISMATCH": (
        "Apply the source document's unanimous same-role body or heading formatting "
        "to the newly inserted chapter paragraph."
    ),
}


def enrich_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for finding in findings:
        item = dict(finding)
        item["severity"] = "error"
        item["blocking"] = True
        hint = REPAIR_HINTS.get(str(item.get("code")))
        if hint and not item.get("repair_hint"):
            item["repair_hint"] = hint
        if not item.get("repair_hint"):
            item["repair_hint"] = (
                "Correct the reported OOXML format or structure defect, regenerate the DOCX, and rerun audit."
            )
        enriched.append(item)
    return enriched


def filter_unchanged_baseline_findings(
    source_findings: list[dict[str, Any]],
    target_findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove only non-fatal target findings that are identical in the source.

    Findings are compared as a multiset rather than a set. One baseline finding
    suppresses at most one canonical-JSON-equivalent finding in the target,
    so a newly duplicated defect is still reported. Fatal package findings are
    never suppressed because they make the audit input or comparison unreliable.
    All other findings use the same source/target detector output and are
    baseline-suppressed when their canonical JSON is identical. This makes the
    source contract uniform across structural and content-policy checks while
    still reporting new locations, changed values, and additional duplicates.
    """
    never_suppress = FATAL_PACKAGE_CODES
    baseline_counts = Counter(
        stable_json_hash(item)
        for item in source_findings
        if item.get("code") not in never_suppress
    )
    remaining: list[dict[str, Any]] = []
    for item in target_findings:
        if item.get("code") in never_suppress:
            remaining.append(item)
            continue
        fingerprint = stable_json_hash(item)
        if baseline_counts[fingerprint] > 0:
            baseline_counts[fingerprint] -= 1
            continue
        remaining.append(item)
    return remaining


def integer_token(value: Any) -> str | None:
    """Canonical numeric identity, retaining XML integer lexical restrictions."""
    text = str(value).strip() if value is not None else ""
    if not re.fullmatch(r"[+-]?[0-9]+", text):
        return None
    try:
        return str(int(text))
    except ValueError:
        return None


def int_value(element: etree._Element | None, attribute: str = "val") -> int | None:
    token = integer_token(element.get(wqn(attribute))) if element is not None else None
    return int(token) if token is not None else None


UNSIGNED_MEASURE_RE = re.compile(
    r"[0-9]+(?:\.[0-9]+)?(?:mm|cm|in|pt|pc|pi)\Z"
)


def is_unsigned_measure(value: Any) -> bool:
    """Return whether a token is in the ST_TwipsMeasure lexical/value space."""
    token = integer_token(value)
    if token is not None:
        return 0 <= int(token) <= (1 << 64) - 1
    return bool(UNSIGNED_MEASURE_RE.fullmatch(str(value or "").strip()))


def attr_value(element: etree._Element | None, attribute: str = "val") -> str | None:
    if element is None:
        return None
    return element.get(wqn(attribute))


def on_off_value(element: etree._Element | None) -> bool | None:
    if element is None:
        return None
    raw = element.get(wqn("val"))
    if raw is None:
        return True
    return raw.lower() not in {"0", "false", "off", "no"}


def on_off_attribute(element: etree._Element | None, attribute: str) -> bool | None:
    if element is None:
        return None
    raw = element.get(wqn(attribute))
    if raw is None:
        return None
    return raw.lower() not in {"0", "false", "off", "no"}


def parse_xml(data: bytes, part: str) -> etree._Element:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise AuditError("invalid XML in %s: %s" % (part, exc)) from exc
    # OOXML parts must not carry a DTD. A document type / internal entity subset
    # is both a security concern and a canonicalization hazard: an unexpanded
    # entity reference node makes the downstream c14n/c14n2 hashing raise, and
    # that exception is not part of the controlled finding flow. Reject it here
    # as invalid XML so it becomes a deterministic E_XML_INVALID instead.
    doc_info = root.getroottree().docinfo
    if doc_info is not None and (doc_info.doctype or doc_info.internalDTD is not None):
        raise AuditError("XML in %s declares a DTD, which OOXML forbids" % part)
    if any(node.tag is etree.Entity for node in root.iter()):
        raise AuditError("XML in %s contains an entity reference" % part)
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        for strict, transitional in STRICT_NAMESPACE_MAP.items():
            strict_prefix = "{%s}" % strict
            if node.tag.startswith(strict_prefix):
                node.tag = node.tag.replace(
                    strict_prefix, "{%s}" % transitional, 1
                )
            for name in list(node.attrib):
                if name.startswith(strict_prefix):
                    node.set(
                        name.replace(strict_prefix, "{%s}" % transitional, 1),
                        node.attrib.pop(name),
                    )
    return root


def markup_compatibility_view(root: etree._Element) -> etree._Element:
    """Return the modern-Word semantic branch of each mc:AlternateContent.

    Choice and Fallback are alternative representations, not simultaneous
    content. Walking both can invent duplicate bookmarks, drawings, fields, and
    relationship references. The first Choice whose required namespaces are
    understood wins; otherwise the Fallback is used.
    """
    clone = etree.fromstring(etree.tostring(root))
    while True:
        alternate_contents = clone.xpath(".//mc:AlternateContent", namespaces=NS)
        if not alternate_contents:
            break
        for alternate in alternate_contents:
            selected: etree._Element | None = None
            for choice in alternate.findall(qn(MC, "Choice")):
                required_prefixes = str(choice.get("Requires") or "").split()
                required_namespaces = [choice.nsmap.get(prefix) for prefix in required_prefixes]
                if (
                    required_prefixes
                    and all(namespace in UNDERSTOOD_MC_NAMESPACES for namespace in required_namespaces)
                ):
                    selected = choice
                    break
            if selected is None:
                selected = alternate.find(qn(MC, "Fallback"))
            parent = alternate.getparent()
            if parent is None:
                continue
            offset = parent.index(alternate)
            if selected is not None:
                for child in list(selected):
                    parent.insert(offset, copy.deepcopy(child))
                    offset += 1
            parent.remove(alternate)
    return clone


def canonical_xml_hash(root: etree._Element) -> str:
    try:
        data = etree.tostring(root, method="c14n", with_comments=True)
    except (etree.C14NError, ValueError):
        try:
            data = etree.tostring(root, method="c14n2", with_comments=True)
        except (etree.C14NError, ValueError, AttributeError) as exc:
            # Both canonicalizers can choke on exotic nodes (e.g. entity
            # references). Surface it as controlled invalid XML rather than
            # letting an unexpected exception escape the audit.
            raise AuditError("cannot canonicalize XML: %s" % exc) from exc
    return sha256_bytes(data)


def element_hash(element: etree._Element | None) -> str | None:
    return canonical_xml_hash(element) if element is not None else None


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def read_margins(root: etree._Element, path: str) -> dict[str, int]:
    out: dict[str, int] = {}
    margins = root.find(path, NS)
    if margins is None:
        return out
    for tag in ("top", "start", "left", "bottom", "end", "right"):
        value = int_value(margins.find("w:%s" % tag, NS), "w")
        if value is not None:
            out[tag] = value
    return out


def word_attributes(
    element: etree._Element | None, names: tuple[str, ...]
) -> dict[str, str]:
    if element is None:
        return {}
    return {
        name: value
        for name in names
        if (value := element.get(wqn(name))) is not None
    }


def parse_shading(element: etree._Element | None) -> dict[str, str]:
    return word_attributes(
        element,
        ("val", "color", "fill", "themeColor", "themeTint", "themeShade"),
    )


def parse_borders(element: etree._Element | None) -> dict[str, dict[str, str]]:
    if element is None:
        return {}
    result: dict[str, dict[str, str]] = {}
    for child in element:
        if not isinstance(child.tag, str) or etree.QName(child).namespace != W:
            continue
        result[etree.QName(child).localname] = word_attributes(
            child,
            (
                "val",
                "sz",
                "space",
                "color",
                "themeColor",
                "themeTint",
                "themeShade",
                "frame",
                "shadow",
            ),
        )
    return result


def parse_cnf_style(element: etree._Element | None) -> dict[str, bool]:
    """Return the enabled conditional-format flags from a w:cnfStyle element.

    w:cnfStyle can carry either individual boolean attributes (w:firstRow=...)
    or a positional bitmask in @w:val. Both forms are decoded into a flag map so
    a row/cell/paragraph can force a conditional region on directly.
    """
    if element is None:
        return {}
    # Bit positions per ECMA-376 for the cnfStyle / tblLook bitmask string.
    bit_flags = [
        ("firstRow", 0),
        ("lastRow", 1),
        ("firstColumn", 2),
        ("lastColumn", 3),
        ("oddVBand", 4),
        ("evenVBand", 5),
        ("oddHBand", 6),
        ("evenHBand", 7),
        ("firstRowFirstColumn", 8),
        ("firstRowLastColumn", 9),
        ("lastRowFirstColumn", 10),
        ("lastRowLastColumn", 11),
    ]
    flags: dict[str, bool] = {}
    raw_val = element.get(wqn("val"))
    if raw_val:
        for name, position in bit_flags:
            if position < len(raw_val) and raw_val[position] == "1":
                flags[name] = True
    for name, _ in bit_flags:
        explicit = element.get(wqn(name))
        if explicit is not None:
            flags[name] = explicit.strip().lower() not in {"0", "false", "off", "no"}
    return {name: value for name, value in flags.items() if value}


def parse_table_properties(tbl_pr: etree._Element | None) -> dict[str, Any]:
    if tbl_pr is None:
        return {}
    out: dict[str, Any] = {}
    width = tbl_pr.find("w:tblW", NS)
    if width is not None:
        width_type = width.get(wqn("type"))
        width_value = int_value(width, "w")
        if width_type is not None:
            out["width_type"] = width_type
        if width_value is not None:
            out["width_dxa"] = width_value
    indent = tbl_pr.find("w:tblInd", NS)
    if indent is not None:
        indent_type = indent.get(wqn("type"))
        indent_value = int_value(indent, "w")
        if indent_type is not None:
            out["indent_type"] = indent_type
        if indent_value is not None:
            out["indent_dxa"] = indent_value
    layout = tbl_pr.find("w:tblLayout", NS)
    layout_type = layout.get(wqn("type")) if layout is not None else None
    if layout_type is not None:
        out["layout"] = layout_type
    alignment = attr_value(tbl_pr.find("w:jc", NS))
    if alignment is not None:
        out["alignment"] = alignment
    overlap = attr_value(tbl_pr.find("w:tblOverlap", NS))
    if overlap is not None:
        out["overlap"] = overlap
    bidi_visual = on_off_value(tbl_pr.find("w:bidiVisual", NS))
    if bidi_visual is not None:
        out["bidi_visual"] = bidi_visual
    row_band_size = int_value(tbl_pr.find("w:tblStyleRowBandSize", NS))
    if row_band_size is not None:
        out["row_band_size"] = row_band_size
    column_band_size = int_value(tbl_pr.find("w:tblStyleColBandSize", NS))
    if column_band_size is not None:
        out["column_band_size"] = column_band_size
    cell_spacing = tbl_pr.find("w:tblCellSpacing", NS)
    if cell_spacing is not None:
        out["cell_spacing"] = word_attributes(cell_spacing, ("w", "type"))
    margins = read_margins(tbl_pr, "w:tblCellMar")
    if margins:
        out["cell_margins_dxa"] = margins
    borders = tbl_pr.find("w:tblBorders", NS)
    if borders is not None:
        out["borders"] = parse_borders(borders)
    shading = parse_shading(tbl_pr.find("w:shd", NS))
    if shading:
        out["shading"] = shading
    table_look = word_attributes(
        tbl_pr.find("w:tblLook", NS),
        (
            "val",
            "firstRow",
            "lastRow",
            "firstColumn",
            "lastColumn",
            "noHBand",
            "noVBand",
        ),
    )
    if table_look:
        out["look"] = table_look
    positioning = word_attributes(
        tbl_pr.find("w:tblpPr", NS),
        (
            "leftFromText",
            "rightFromText",
            "topFromText",
            "bottomFromText",
            "vertAnchor",
            "horzAnchor",
            "tblpX",
            "tblpY",
            "tblpXSpec",
            "tblpYSpec",
        ),
    )
    if positioning:
        out["positioning"] = positioning
    return out


def parse_rpr(rpr: etree._Element | None) -> dict[str, Any]:
    if rpr is None:
        return {}
    out: dict[str, Any] = {}
    fonts = rpr.find("w:rFonts", NS)
    if fonts is not None:
        mapping = {
            "ascii": "font_ascii",
            "hAnsi": "font_hansi",
            "eastAsia": "font_east_asia",
            "cs": "font_complex_script",
            "asciiTheme": "font_ascii_theme",
            "hAnsiTheme": "font_hansi_theme",
            "eastAsiaTheme": "font_east_asia_theme",
            "cstheme": "font_complex_script_theme",
        }
        for attr, key in mapping.items():
            value = fonts.get(wqn(attr))
            if value is not None:
                out[key] = value
        hint = fonts.get(wqn("hint"))
        if hint is not None:
            out["font_hint"] = hint
    character_style = attr_value(rpr.find("w:rStyle", NS))
    if character_style is not None:
        out["character_style_id"] = character_style
    complex_script = on_off_value(rpr.find("w:cs", NS))
    if complex_script is not None:
        out["complex_script"] = complex_script
    right_to_left = on_off_value(rpr.find("w:rtl", NS))
    if right_to_left is not None:
        out["right_to_left"] = right_to_left
    size = int_value(rpr.find("w:sz", NS))
    if size is not None:
        out["size_half_points"] = size
    size_cs = int_value(rpr.find("w:szCs", NS))
    if size_cs is not None:
        out["size_complex_script_half_points"] = size_cs
    for tag, key in (
        ("b", "bold"),
        ("bCs", "bold_complex_script"),
        ("i", "italic"),
        ("iCs", "italic_complex_script"),
        ("strike", "strike"),
        ("dstrike", "double_strike"),
        ("caps", "caps"),
        ("smallCaps", "small_caps"),
        ("vanish", "hidden"),
    ):
        value = on_off_value(rpr.find("w:%s" % tag, NS))
        if value is not None:
            out[key] = value
    underline = rpr.find("w:u", NS)
    if underline is not None:
        out["underline"] = attr_value(underline) or "single"
    color = attr_value(rpr.find("w:color", NS))
    if color is not None:
        out["color"] = color.upper()
    highlight = attr_value(rpr.find("w:highlight", NS))
    if highlight is not None:
        out["highlight"] = highlight
    vertical_align = attr_value(rpr.find("w:vertAlign", NS))
    if vertical_align is not None:
        out["vertical_align"] = vertical_align
    for tag, key in (
        ("spacing", "character_spacing_twips"),
        ("position", "position_half_points"),
        ("w", "scale_percent"),
        ("kern", "kerning_half_points"),
    ):
        value = int_value(rpr.find("w:%s" % tag, NS))
        if value is not None:
            out[key] = value
    shading = parse_shading(rpr.find("w:shd", NS))
    if shading:
        out["shading"] = shading
    language = word_attributes(rpr.find("w:lang", NS), ("val", "eastAsia", "bidi"))
    if language:
        out["language"] = language
    return out


def parse_ppr(ppr: etree._Element | None) -> dict[str, Any]:
    if ppr is None:
        return {}
    out: dict[str, Any] = {}
    alignment = attr_value(ppr.find("w:jc", NS))
    if alignment is not None:
        out["alignment"] = alignment
    spacing = ppr.find("w:spacing", NS)
    if spacing is not None:
        spacing_map = {
            "before": "space_before_twips",
            "after": "space_after_twips",
            "line": "line_twips",
        }
        for attr, key in spacing_map.items():
            value = int_value(spacing, attr)
            if value is not None:
                out[key] = value
        line_rule = spacing.get(wqn("lineRule"))
        if line_rule is not None:
            out["line_rule"] = line_rule
    indent = ppr.find("w:ind", NS)
    if indent is not None:
        indent_map = {
            "left": "left_indent_dxa",
            "right": "right_indent_dxa",
            "firstLine": "first_line_dxa",
            "hanging": "hanging_dxa",
            "firstLineChars": "first_line_chars",
            "hangingChars": "hanging_chars",
        }
        for attr, key in indent_map.items():
            value = int_value(indent, attr)
            if value is not None:
                out[key] = value
    tabs = []
    for tab in ppr.findall("w:tabs/w:tab", NS):
        tabs.append(
            {
                "value": tab.get(wqn("val")),
                "position_dxa": int_value(tab, "pos"),
            }
        )
    if tabs:
        out["tabs"] = tabs
    for tag, key in (
        ("keepNext", "keep_next"),
        ("keepLines", "keep_lines"),
        ("pageBreakBefore", "page_break_before"),
        ("widowControl", "widow_control"),
        ("contextualSpacing", "contextual_spacing"),
        ("suppressLineNumbers", "suppress_line_numbers"),
        ("mirrorIndents", "mirror_indents"),
        ("bidi", "right_to_left"),
    ):
        value = on_off_value(ppr.find("w:%s" % tag, NS))
        if value is not None:
            out[key] = value
    borders = parse_borders(ppr.find("w:pBdr", NS))
    if borders:
        out["borders"] = borders
    shading = parse_shading(ppr.find("w:shd", NS))
    if shading:
        out["shading"] = shading
    text_alignment = attr_value(ppr.find("w:textAlignment", NS))
    if text_alignment is not None:
        out["text_alignment"] = text_alignment
    text_direction = attr_value(ppr.find("w:textDirection", NS))
    if text_direction is not None:
        out["text_direction"] = text_direction
    outline_level = int_value(ppr.find("w:outlineLvl", NS))
    if outline_level is not None:
        out["outline_level"] = outline_level
    num_pr = ppr.find("w:numPr", NS)
    if num_pr is not None:
        num_id_element = num_pr.find("w:numId", NS)
        level_element = num_pr.find("w:ilvl", NS)
        num_id_token = attr_value(num_id_element)
        level_token = attr_value(level_element)
        num_id = int_value(num_id_element)
        level = int_value(level_element)
        if num_id_token is not None:
            out["num_id_token"] = num_id_token
        if level_token is not None:
            out["num_level_token"] = level_token
        if num_id is not None:
            out["num_id"] = num_id
        if level is not None:
            out["num_level"] = level
    return out


def extract_styles(xml_roots: dict[str, etree._Element]) -> dict[str, Any]:
    root = xml_roots.get("word/styles.xml")
    if root is None:
        return {"defaults": {"rPr": {}, "pPr": {}}, "styles": {}}
    defaults = root.find("w:docDefaults", NS)
    default_rpr = defaults.find("w:rPrDefault/w:rPr", NS) if defaults is not None else None
    default_ppr = defaults.find("w:pPrDefault/w:pPr", NS) if defaults is not None else None
    records: dict[str, Any] = {}
    default_style_ids: dict[str, str] = {}
    for style in root.findall("w:style", NS):
        style_id = style.get(wqn("styleId"))
        if not style_id:
            continue
        style_type = style.get(wqn("type"))
        is_default = on_off_attribute(style, "default") is True
        if style_type and is_default:
            default_style_ids[style_type] = style_id
        name = attr_value(style.find("w:name", NS))
        table_properties = parse_table_properties(style.find("w:tblPr", NS))
        first_row_style = style.find("w:tblStylePr[@w:type='firstRow']", NS)
        first_row_fill = (
            attr_value(first_row_style.find("w:tcPr/w:shd", NS), "fill")
            if first_row_style is not None
            else None
        )
        if first_row_fill is not None:
            table_properties["first_row_fill"] = first_row_fill
        conditional_table_properties: dict[str, Any] = {}
        for conditional in style.findall("w:tblStylePr", NS):
            condition = conditional.get(wqn("type"))
            if not condition:
                continue
            conditional_table_properties[condition] = {
                "rPr": parse_rpr(conditional.find("w:rPr", NS)),
                "pPr": parse_ppr(conditional.find("w:pPr", NS)),
                "table": parse_table_properties(conditional.find("w:tblPr", NS)),
            }
        records[style_id] = {
            "style_id": style_id,
            "type": style_type,
            "default": is_default,
            "name": name,
            "based_on": attr_value(style.find("w:basedOn", NS)),
            "next": attr_value(style.find("w:next", NS)),
            "linked": attr_value(style.find("w:link", NS)),
            "quick_format": style.find("w:qFormat", NS) is not None,
            "properties": {
                "rPr": parse_rpr(style.find("w:rPr", NS)),
                "pPr": parse_ppr(style.find("w:pPr", NS)),
                "table": table_properties,
            },
            "conditional_table_properties": conditional_table_properties,
        }
    return {
        "defaults": {"rPr": parse_rpr(default_rpr), "pPr": parse_ppr(default_ppr)},
        "default_style_ids": default_style_ids,
        "styles": records,
    }


def resolve_style_id(style_manifest: dict[str, Any], style_id: str) -> str | None:
    records = style_manifest.get("styles", {})
    # OOXML references w:styleId, not a display name. Fuzzy matching can hide
    # broken references and collapses non-ASCII IDs such as Chinese names to "".
    return style_id if style_id in records else None


def effective_style(style_manifest: dict[str, Any], style_id: str) -> dict[str, Any] | None:
    records = style_manifest.get("styles", {})
    style_id = resolve_style_id(style_manifest, style_id)
    if style_id is None:
        return None

    seen: set[str] = set()

    def visit(current: str | None) -> dict[str, Any]:
        if not current or current in seen or current not in records:
            return {"rPr": {}, "pPr": {}}
        seen.add(current)
        record = records[current]
        inherited = visit(record.get("based_on"))
        return deep_merge(inherited, record.get("properties", {}))

    defaults = style_manifest.get("defaults", {"rPr": {}, "pPr": {}})
    return deep_merge(defaults, visit(style_id))


def effective_table_properties(
    style_manifest: dict[str, Any], table: dict[str, Any]
) -> dict[str, Any]:
    style_id = table.get("style_id") or style_manifest.get("default_style_ids", {}).get(
        "table"
    )
    style = effective_style(style_manifest, str(style_id)) if style_id else None
    effective = copy.deepcopy(style.get("table", {})) if style else {}
    direct = table.get("properties", {})
    for key, value in direct.items():
        if key in {"cell_margins_dxa", "borders"}:
            continue
        effective[key] = copy.deepcopy(value)
    margins = copy.deepcopy(effective.get("cell_margins_dxa", {}))
    margins.update(direct.get("cell_margins_dxa", {}))
    if margins:
        effective["cell_margins_dxa"] = margins
    borders = copy.deepcopy(effective.get("borders", {}))
    borders.update(direct.get("borders", {}))
    if borders:
        effective["borders"] = borders
    return effective


def story_parts(names: list[str]) -> list[str]:
    return sorted(name for name in names if STORY_RE.match(name))


def paragraph_text(paragraph: etree._Element) -> str:
    return "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))


def run_word_count_text(run: etree._Element) -> str:
    """Return visible text controls owned by this run's logical paragraph.

    Text boxes place an inner w:p/w:r below an outer drawing run. Filtering by
    nearest paragraph and nearest run prevents the inner text from being counted
    once through the outer run and again through its own run.
    """
    owner_paragraphs = run.xpath("ancestor::w:p[1]", namespaces=NS)
    owner_paragraph = owner_paragraphs[0] if owner_paragraphs else None
    pieces: list[str] = []
    nodes = run.xpath(
        ".//w:t | .//w:tab | .//w:br | .//w:cr | "
        ".//w:noBreakHyphen | .//w:softHyphen",
        namespaces=NS,
    )
    for node in nodes:
        nearest_runs = node.xpath("ancestor::w:r[1]", namespaces=NS)
        nearest_paragraphs = node.xpath("ancestor::w:p[1]", namespaces=NS)
        if (
            not nearest_runs
            or nearest_runs[0] is not run
            or not nearest_paragraphs
            or nearest_paragraphs[0] is not owner_paragraph
        ):
            continue
        local_name = etree.QName(node).localname
        if local_name == "t":
            pieces.append(node.text or "")
        elif local_name in {"tab", "br", "cr"}:
            pieces.append(" ")
        elif local_name == "noBreakHyphen":
            pieces.append("\u2011")
        elif local_name == "softHyphen":
            pieces.append("\u00ad")
    return "".join(pieces)


def paragraph_revision_text_state(paragraph: etree._Element) -> str:
    """Classify the text used for paragraph matching by revision provenance."""
    visible_text_nodes = [
        node
        for node in paragraph.xpath(".//w:t", namespaces=NS)
        if node.text not in (None, "")
    ]
    deleted_text_nodes = [
        node
        for node in paragraph.xpath(".//w:delText", namespaces=NS)
        if node.text not in (None, "")
    ]
    if (
        visible_text_nodes
        and not deleted_text_nodes
        and all(
            node.xpath("ancestor::w:ins", namespaces=NS)
            for node in visible_text_nodes
        )
    ):
        return "inserted"
    if deleted_text_nodes and not visible_text_nodes:
        return "deleted"
    return "existing"


def toc_result_text_nodes(root: etree._Element) -> set[etree._Element]:
    """Identify TOC display text without treating nearby prose as a directory.

    Complex fields can span runs/paragraphs and contain nested PAGEREF fields.
    Collect their text only after ``separate`` and commit it only at a matching
    ``end``: an unclosed TOC must not exempt the rest of the story. Simple TOC
    fields and explicit TOC building-block SDTs have XML-bounded result ranges.
    A heading named "目录" or a TOC-like style alone is not sufficient evidence.
    This metadata is used only by the ASCII-quote policy, not other detectors.
    """
    excluded: set[etree._Element] = set()
    independent_stories = {
        wqn(name) for name in ("body", "txbxContent", "footnote", "endnote", "comment")
    }
    deleted_containers = {wqn("del"), wqn("moveFrom")}

    def visit(node: etree._Element, stack: list[dict[str, Any]]) -> None:
        if node.tag in deleted_containers:
            return
        if node.tag in independent_stories:
            stack = []

        is_simple = node.tag == wqn("fldSimple")
        is_toc_sdt = False
        if node.tag == wqn("sdt"):
            gallery = node.find("w:sdtPr/w:docPartObj/w:docPartGallery", NS)
            is_toc_sdt = (
                str(attr_value(gallery) or "").strip().casefold()
                in TOC_SDT_GALLERIES
            )
        if is_simple or is_toc_sdt:
            frame = {
                "kind": "container",
                "toc": is_toc_sdt or bool(
                    TOC_FIELD_RE.match(str(node.get(wqn("instr")) or ""))
                ),
                "nodes": [],
            }
            depth = len(stack)
            stack.append(frame)
            for child in node:
                visit(child, stack)
            # Unclosed complex fields inside an XML-bounded container cannot
            # consume following body text outside that container.
            del stack[depth:]
            if frame["toc"]:
                excluded.update(frame["nodes"])
            return

        if node.tag == wqn("fldChar"):
            field_type = node.get(wqn("fldCharType"))
            if field_type == "begin":
                stack.append({
                    "kind": "complex", "instruction": [], "separated": False,
                    "toc": False, "nodes": [],
                })
            elif stack and stack[-1]["kind"] == "complex":
                frame = stack[-1]
                if field_type == "separate" and not frame["separated"]:
                    frame["separated"] = True
                    frame["toc"] = bool(
                        TOC_FIELD_RE.match("".join(frame["instruction"]))
                    )
                elif field_type == "end":
                    stack.pop()
                    if frame["toc"]:
                        excluded.update(frame["nodes"])
            return
        if node.tag == wqn("instrText"):
            if (
                stack and stack[-1]["kind"] == "complex"
                and not stack[-1]["separated"]
            ):
                stack[-1]["instruction"].append(node.text or "")
            return
        if node.tag == wqn("t"):
            for frame in stack:
                if frame["toc"]:
                    frame["nodes"].append(node)
            return
        for child in node:
            visit(child, stack)

    visit(root, [])
    return excluded


def extract_paragraphs(part: str, root: etree._Element) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tree = root.getroottree()
    toc_text_nodes = toc_result_text_nodes(root)
    table_contexts: dict[str, dict[str, Any]] = {}
    for table_index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1):
        table_path = tree.getpath(table)
        rows = table.findall("w:tr", NS)
        grid_column_count = len(table.findall("w:tblGrid/w:gridCol", NS))
        if not grid_column_count:
            grid_column_count = max(
                (
                    sum(
                        int_value(cell.find("w:tcPr/w:gridSpan", NS)) or 1
                        for cell in row.findall("w:tc", NS)
                    )
                    for row in rows
                ),
                default=0,
            )
        row_contexts: dict[str, dict[str, Any]] = {}
        row_cell_counts: list[int] = []
        table_has_horizontal_merge = False
        table_has_vertical_merge = False
        for row_index, row in enumerate(rows, 1):
            cells = row.findall("w:tc", NS)
            row_cell_counts.append(len(cells))
            column_start = 1
            cell_contexts: dict[str, dict[str, int]] = {}
            for cell_index, cell in enumerate(cells, 1):
                span = int_value(cell.find("w:tcPr/w:gridSpan", NS)) or 1
                if span > 1 or cell.find("w:tcPr/w:hMerge", NS) is not None:
                    table_has_horizontal_merge = True
                if cell.find("w:tcPr/w:vMerge", NS) is not None:
                    table_has_vertical_merge = True
                cell_contexts[tree.getpath(cell)] = {
                    "cell_index": cell_index,
                    "cell_count": len(cells),
                    "grid_column_start": column_start,
                    "grid_column_end": column_start + span - 1,
                    "grid_span": span,
                    "cnf_style": parse_cnf_style(cell.find("w:tcPr/w:cnfStyle", NS)),
                }
                column_start += span
            row_contexts[tree.getpath(row)] = {
                "row_index": row_index,
                "row_count": len(rows),
                "cnf_style": parse_cnf_style(row.find("w:trPr/w:cnfStyle", NS)),
                "cells": cell_contexts,
            }
        # A "regular data table" must be at least 2 rows x 2 columns, have the
        # same number of cells in every row, and have no merged cells (no
        # horizontal gridSpan/hMerge, no vertical vMerge). Anything else is a layout
        # device rather than a data table: 1-row/1-column tables are callout /
        # emphasis boxes or vertical lists, and ragged/merged tables are forms
        # (学位论文封面、备案表 等). They use cells to arrange content, not to hold
        # tabular data, so the first-line-indent rule does not apply.
        uniform_rows = len(set(row_cell_counts)) == 1 and bool(row_cell_counts)
        column_count = grid_column_count or (
            row_cell_counts[0] if uniform_rows else 0
        )
        meets_min_dimensions = len(rows) >= 2 and column_count >= 2
        is_regular_table = (
            meets_min_dimensions
            and uniform_rows
            and not table_has_horizontal_merge
            and not table_has_vertical_merge
        )
        table_contexts[table_path] = {
            "table_index": table_index,
            "table_xpath": table_path,
            "style_id": attr_value(table.find("w:tblPr/w:tblStyle", NS)),
            "properties": parse_table_properties(table.find("w:tblPr", NS)),
            "grid_column_count": grid_column_count,
            "is_regular_table": is_regular_table,
            "meets_min_dimensions": meets_min_dimensions,
            "has_horizontal_merge": table_has_horizontal_merge,
            "has_vertical_merge": table_has_vertical_merge,
            "uniform_row_cell_count": uniform_rows,
            "rows": row_contexts,
        }
    for index, paragraph in enumerate(root.xpath(".//w:p", namespaces=NS), 1):
        ppr = paragraph.find("w:pPr", NS)
        style = attr_value(ppr.find("w:pStyle", NS)) if ppr is not None else None
        num_pr = ppr.find("w:numPr", NS) if ppr is not None else None
        num_id = int_value(num_pr.find("w:numId", NS)) if num_pr is not None else None
        num_level = int_value(num_pr.find("w:ilvl", NS)) if num_pr is not None else None
        runs = []
        for run_index, run in enumerate(paragraph.xpath(".//w:r", namespaces=NS), 1):
            run_text = "".join(run.xpath("./w:t/text()", namespaces=NS))
            toc_text_ranges: list[list[int]] = []
            text_offset = 0
            for text_node in run.findall("w:t", NS):
                text_end = text_offset + len(text_node.text or "")
                if text_node in toc_text_nodes and text_end > text_offset:
                    if toc_text_ranges and toc_text_ranges[-1][1] == text_offset:
                        toc_text_ranges[-1][1] = text_end
                    else:
                        toc_text_ranges.append([text_offset, text_end])
                text_offset = text_end
            count_text = run_word_count_text(run)
            owner_paragraphs = run.xpath("ancestor::w:p[1]", namespaces=NS)
            run_sdt_tags = run.xpath(
                "ancestor::w:sdt[1]/w:sdtPr/w:tag/@w:val", namespaces=NS
            )
            runs.append(
                {
                    "index": run_index,
                    "text": run_text,
                    "word_count_text": count_text,
                    "word_count_visible": not bool(
                        run.xpath(
                            "ancestor::w:del | ancestor::w:moveFrom",
                            namespaces=NS,
                        )
                    ),
                    "rPr": parse_rpr(run.find("w:rPr", NS)),
                    "xpath": tree.getpath(run),
                    "owner_paragraph_xpath": (
                        tree.getpath(owner_paragraphs[0]) if owner_paragraphs else None
                    ),
                    "sdt_tag": run_sdt_tags[0] if run_sdt_tags else None,
                }
            )
            if toc_text_ranges:
                runs[-1]["toc_text_ranges"] = toc_text_ranges
        sdt_tags = paragraph.xpath(
            "ancestor::w:sdt[1]/w:sdtPr/w:tag/@w:val", namespaces=NS
        )
        bookmarks = paragraph.xpath(".//w:bookmarkStart/@w:name", namespaces=NS)
        text = paragraph_text(paragraph)
        revision_text_state = paragraph_revision_text_state(paragraph)
        table_context = None
        table_ancestors = paragraph.xpath("ancestor::w:tbl[1]", namespaces=NS)
        row_ancestors = paragraph.xpath("ancestor::w:tr[1]", namespaces=NS)
        cell_ancestors = paragraph.xpath("ancestor::w:tc[1]", namespaces=NS)
        if table_ancestors and row_ancestors and cell_ancestors:
            table_path = tree.getpath(table_ancestors[0])
            row_path = tree.getpath(row_ancestors[0])
            cell_path = tree.getpath(cell_ancestors[0])
            stored_table = table_contexts.get(table_path, {})
            stored_row = stored_table.get("rows", {}).get(row_path, {})
            stored_cell = stored_row.get("cells", {}).get(cell_path, {})
            table_context = {
                key: value
                for key, value in stored_table.items()
                if key != "rows"
            }
            table_context.update(
                {
                    key: value
                    for key, value in stored_row.items()
                    if key not in ("cells", "cnf_style")
                }
            )
            table_context.update(
                {
                    key: value
                    for key, value in stored_cell.items()
                    if key != "cnf_style"
                }
            )
            # A paragraph's conditional format can be forced on at the row, cell
            # or paragraph level. Merge all three (plus the paragraph's own
            # w:pPr/w:cnfStyle) so applicable_table_style_conditions sees every
            # explicitly enabled region, not just the cell's.
            merged_cnf: dict[str, bool] = {}
            merged_cnf.update(stored_row.get("cnf_style") or {})
            merged_cnf.update(stored_cell.get("cnf_style") or {})
            if ppr is not None:
                merged_cnf.update(parse_cnf_style(ppr.find("w:cnfStyle", NS)))
            table_context["cnf_style"] = merged_cnf
        modeled_structure = {
            "breaks": [
                {
                    "type": item.get(wqn("type")) or "textWrapping",
                    "clear": item.get(wqn("clear")),
                }
                for item in paragraph.findall(".//w:br", NS)
            ],
            "tab_count": len(paragraph.findall(".//w:tab", NS)),
            "hyperlink_count": len(paragraph.findall(".//w:hyperlink", NS)),
            "drawing_count": len(paragraph.findall(".//w:drawing", NS)),
            "field_endpoints": [
                item.get(wqn("fldCharType"))
                for item in paragraph.findall(".//w:fldChar", NS)
            ],
            "footnote_reference_count": len(
                paragraph.findall(".//w:footnoteReference", NS)
            ),
            "endnote_reference_count": len(
                paragraph.findall(".//w:endnoteReference", NS)
            ),
            "comment_reference_count": len(
                paragraph.findall(".//w:commentReference", NS)
            ),
        }
        records.append(
            {
                "part": part,
                "index": index,
                "location": "%s#p%d" % (part, index),
                "xpath": tree.getpath(paragraph),
                "para_id": paragraph.get(qn(W14, "paraId")),
                "text": text,
                "text_sha256": sha256_bytes(text.encode("utf-8")),
                "revision_text_state": revision_text_state,
                "paragraph_mark_inserted": paragraph.find("w:pPr/w:rPr/w:ins", NS) is not None,
                "revision_replacement": bool(paragraph.findall(".//w:delText", NS)),
                "revision_moved": bool(paragraph.xpath(
                    ".//w:moveFrom | .//w:moveTo | ancestor::w:moveFrom | ancestor::w:moveTo",
                    namespaces=NS,
                )),
                "style_id": style,
                "num_id": num_id,
                "num_level": num_level,
                "pPr": parse_ppr(ppr),
                "runs": runs,
                "modeled_structure": modeled_structure,
                "bookmarks": bookmarks,
                "sdt_tag": sdt_tags[0] if sdt_tags else None,
                "in_table": bool(paragraph.xpath("ancestor::w:tc", namespaces=NS)),
                "in_textbox": bool(
                    paragraph.xpath("ancestor::w:txbxContent", namespaces=NS)
                ),
                "table_context": table_context,
            }
        )
    return records






def structural_hash(
    element: etree._Element,
    clear_text: bool = False,
    clear_format: bool = False,
) -> str:
    clone = etree.fromstring(etree.tostring(element))
    if clear_text:
        for text_node in clone.xpath(".//w:t", namespaces=NS):
            text_node.text = ""
    if clear_format:
        for properties in clone.xpath(".//w:pPr | .//w:rPr", namespaces=NS):
            parent = properties.getparent()
            if parent is not None:
                parent.remove(properties)
    for node in clone.iter():
        for name in list(node.attrib):
            local = etree.QName(name).localname
            namespace = etree.QName(name).namespace
            if (namespace == W and local.startswith("rsid")) or (
                namespace == W14 and local in {"paraId", "textId"}
            ):
                del node.attrib[name]
            elif namespace == R:
                node.attrib[name] = "RELATIONSHIP_%s" % local
    for proof_error in clone.xpath(".//w:proofErr", namespaces=NS):
        parent = proof_error.getparent()
        if parent is not None:
            parent.remove(proof_error)
    for rsids in clone.xpath(".//w:rsids", namespaces=NS):
        parent = rsids.getparent()
        if parent is not None:
            parent.remove(rsids)
    return canonical_xml_hash(clone)


def ooxml_property_order_findings(
    part: str, root: etree._Element
) -> list[dict[str, Any]]:
    """Find schema-order inversions in table property containers.

    The check compares only recognized WordprocessingML children. Extension
    namespaces and unknown w: children are left untouched and do not affect the
    result, avoiding claims about schema positions the auditor does not model.
    """
    findings: list[dict[str, Any]] = []
    tree = root.getroottree()
    table_indexes: dict[str, int] = {}
    row_indexes: dict[str, int] = {}
    cell_indexes: dict[str, int] = {}

    for table_index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1):
        table_path = tree.getpath(table)
        table_indexes[table_path] = table_index
        rows = []
        for row in table.xpath(".//w:tr", namespaces=NS):
            ancestors = row.xpath("ancestor::w:tbl[1]", namespaces=NS)
            if ancestors and tree.getpath(ancestors[0]) == table_path:
                rows.append(row)
        for row_index, row in enumerate(rows, 1):
            row_path = tree.getpath(row)
            row_indexes[row_path] = row_index
            cells = []
            for cell in row.xpath(".//w:tc", namespaces=NS):
                ancestors = cell.xpath("ancestor::w:tr[1]", namespaces=NS)
                if ancestors and tree.getpath(ancestors[0]) == row_path:
                    cells.append(cell)
            for cell_index, cell in enumerate(cells, 1):
                cell_indexes[tree.getpath(cell)] = cell_index

    # w:trPr is intentionally excluded: CT_TrPrBase is an unbounded xsd:choice,
    # so its base children have no required order (a valid
    # <w:tblHeader/><w:cantSplit/> must not be flagged). Only the sequence-typed
    # containers w:tblPr and w:tcPr carry an enforceable order.
    containers = root.xpath(
        ".//w:tblPr | .//w:tcPr", namespaces=NS
    )
    for container in containers:
        container_name = etree.QName(container).localname
        code, allowed_order = OOXML_PROPERTY_ORDER[container_name]
        rank = {name: index for index, name in enumerate(allowed_order)}
        actual_local = []
        for child in container:
            if not isinstance(child.tag, str):
                continue
            child_name = etree.QName(child)
            if child_name.namespace == W and child_name.localname in rank:
                actual_local.append(child_name.localname)

        inversion: tuple[int, int] | None = None
        for later_index in range(1, len(actual_local)):
            later_rank = rank[actual_local[later_index]]
            for earlier_index in range(later_index - 1, -1, -1):
                if rank[actual_local[earlier_index]] > later_rank:
                    inversion = (earlier_index, later_index)
                    break
            if inversion is not None:
                break
        if inversion is None:
            continue

        expected_local = sorted(actual_local, key=rank.__getitem__)
        actual = ["w:%s" % name for name in actual_local]
        expected = ["w:%s" % name for name in expected_local]
        earlier_index, later_index = inversion
        container_path = tree.getpath(container)
        evidence: dict[str, Any] = {
            "part": part,
            "xpath": container_path,
            "container": "w:%s" % container_name,
            "actual": actual,
            "expected": expected,
            "first_inversion": {
                "observed_earlier": "w:%s" % actual_local[earlier_index],
                "out_of_order_node": "w:%s" % actual_local[later_index],
                "observed_positions": [earlier_index + 1, later_index + 1],
                "required_order": [
                    "w:%s" % actual_local[later_index],
                    "w:%s" % actual_local[earlier_index],
                ],
            },
        }

        table_ancestors = container.xpath("ancestor::w:tbl[1]", namespaces=NS)
        row_ancestors = container.xpath("ancestor::w:tr[1]", namespaces=NS)
        cell_ancestors = container.xpath("ancestor::w:tc[1]", namespaces=NS)
        location_parts = []
        if table_ancestors:
            table_index = table_indexes.get(tree.getpath(table_ancestors[0]))
            if table_index is not None:
                evidence["table_index"] = table_index
                location_parts.append("table%d" % table_index)
        if row_ancestors:
            row_index = row_indexes.get(tree.getpath(row_ancestors[0]))
            if row_index is not None:
                evidence["row_index"] = row_index
                location_parts.append("row%d" % row_index)
        if cell_ancestors:
            cell_index = cell_indexes.get(tree.getpath(cell_ancestors[0]))
            if cell_index is not None:
                evidence["cell_index"] = cell_index
                location_parts.append("cell%d" % cell_index)
        if location_parts:
            location = "%s#%s/%s" % (
                part,
                "/".join(location_parts),
                container_name,
            )
        else:
            location = "%s:%s" % (part, container_path)

        findings.append(
            issue(
                "error",
                code,
                location,
                "w:%s children are out of OOXML schema order" % container_name,
                expected=expected,
                actual=actual,
                repair_hint=OOXML_PROPERTY_ORDER_REPAIR_HINT,
                evidence=evidence,
                blocking=True,
            )
        )
    return findings


def extract_tables(part: str, root: etree._Element) -> list[dict[str, Any]]:
    """Keep only table metadata consumed by the current CLI checks."""
    return [
        {
            "part": part,
            "location": "%s#table%d" % (part, index),
            "style_id": attr_value(table.find("w:tblPr/w:tblStyle", NS)),
            "grid_width_tokens": [
                column.get(wqn("w")) for column in table.findall("w:tblGrid/w:gridCol", NS)
            ],
        }
        for index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1)
    ]


def extract_sections(document: etree._Element) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, section in enumerate(
        document.xpath(
            ".//w:sectPr[not(ancestor::w:sectPrChange)]", namespaces=NS
        ),
        1,
    ):
        size = section.find("w:pgSz", NS)
        margins = section.find("w:pgMar", NS)
        section_type = section.find("w:type", NS)
        cols = section.find("w:cols", NS)
        page_numbering = section.find("w:pgNumType", NS)
        width = int_value(size, "w")
        height = int_value(size, "h")
        orientation = size.get(wqn("orient")) if size is not None else None
        if orientation is None and width is not None and height is not None:
            orientation = "landscape" if width > height else "portrait"
        margin_values: dict[str, int | None] = {}
        for name in ("top", "right", "bottom", "left", "header", "footer", "gutter"):
            margin_values["%s_dxa" % name] = int_value(margins, name)
        records.append(
            {
                "index": index,
                "page": {
                    "width_dxa": width,
                    "height_dxa": height,
                    "width_token": size.get(wqn("w")) if size is not None else None,
                    "height_token": size.get(wqn("h")) if size is not None else None,
                    "orientation": orientation,
                    "margins": margin_values,
                },
                "start_type": attr_value(section_type) or "nextPage",
                "different_first_page": section.find("w:titlePg", NS) is not None,
                "columns": {
                    "count": int_value(cols, "num") if cols is not None else None,
                    "space_dxa": int_value(cols, "space") if cols is not None else None,
                    "separator": on_off_attribute(cols, "sep"),
                },
                "page_numbering": word_attributes(
                    page_numbering, ("start", "fmt", "chapStyle", "chapSep")
                ),
                "vertical_alignment": attr_value(section.find("w:vAlign", NS)),
                "text_direction": attr_value(section.find("w:textDirection", NS)),
                "document_grid": word_attributes(
                    section.find("w:docGrid", NS), ("type", "linePitch", "charSpace")
                ),
                "line_numbering": word_attributes(
                    section.find("w:lnNumType", NS),
                    ("countBy", "start", "distance", "restart"),
                ),
                "page_borders": parse_borders(section.find("w:pgBorders", NS)),
                "header_references": [
                    {"type": item.get(wqn("type")), "rId": item.get(qn(R, "id"))}
                    for item in section.findall("w:headerReference", NS)
                ],
                "footer_references": [
                    {"type": item.get(wqn("type")), "rId": item.get(qn(R, "id"))}
                    for item in section.findall("w:footerReference", NS)
                ],
            }
        )
    return records


def add_effective_story_references(sections: list[dict[str, Any]]) -> None:
    """Resolve omitted header/footer references through section inheritance."""
    inherited: dict[str, dict[str, dict[str, Any]]] = {
        "header": {},
        "footer": {},
    }
    for section in sections:
        for family in ("header", "footer"):
            effective = dict(inherited[family])
            for reference in section.get("%s_references" % family, []):
                reference_type = str(reference.get("type") or "default")
                effective[reference_type] = {
                    "type": reference_type,
                    "rId": reference.get("rId"),
                }
            section["effective_%s_references" % family] = [
                effective[reference_type]
                for reference_type in sorted(effective)
            ]
            inherited[family] = effective


def parse_numbering_level(level: etree._Element) -> dict[str, Any]:
    return {
        "format": attr_value(level.find("w:numFmt", NS)),
        "text": attr_value(level.find("w:lvlText", NS)),
        "start": int_value(level.find("w:start", NS)),
        "pPr": parse_ppr(level.find("w:pPr", NS)),
        "rPr": parse_rpr(level.find("w:rPr", NS)),
    }


def extract_numbering(xml_roots: dict[str, etree._Element]) -> dict[str, Any]:
    root = xml_roots.get("word/numbering.xml")
    if root is None:
        return {
            "abstract_numbers": {},
            "numbers": {},
            "invalid_abstract_ids": [],
            "duplicate_abstract_ids": [],
            "invalid_num_ids": [],
            "duplicate_num_ids": [],
        }
    abstract: dict[str, Any] = {}
    invalid_abstract_ids: list[Any] = []
    duplicate_abstract_ids: list[str] = []
    for item in root.findall("w:abstractNum", NS):
        raw_ident = item.get(wqn("abstractNumId"))
        ident = integer_token(raw_ident)
        if ident is None:
            invalid_abstract_ids.append(raw_ident)
            continue
        if ident in abstract:
            duplicate_abstract_ids.append(ident)
        levels = {}
        for level in item.findall("w:lvl", NS):
            ilvl = integer_token(level.get(wqn("ilvl")))
            levels[str(ilvl)] = parse_numbering_level(level)
        abstract[str(ident)] = {"levels": levels, "xml_sha256": element_hash(item)}
    numbers: dict[str, Any] = {}
    invalid_num_ids: list[Any] = []
    duplicate_num_ids: list[str] = []
    for item in root.findall("w:num", NS):
        raw_ident = item.get(wqn("numId"))
        ident = integer_token(raw_ident)
        if ident is None:
            invalid_num_ids.append(raw_ident)
            continue
        if ident in numbers:
            duplicate_num_ids.append(ident)
        overrides: dict[str, dict[str, Any]] = {}
        for override in item.findall("w:lvlOverride", NS):
            ilvl = integer_token(override.get(wqn("ilvl")))
            if ilvl is None:
                continue
            record: dict[str, Any] = {}
            start_override = int_value(override.find("w:startOverride", NS))
            if start_override is not None:
                record["start_override"] = start_override
            level = override.find("w:lvl", NS)
            if level is not None:
                record["level"] = parse_numbering_level(level)
            overrides[str(ilvl)] = record
        numbers[str(ident)] = {
            "abstract_num_id": int_value(item.find("w:abstractNumId", NS)),
            "overrides": overrides,
        }
    return {
        "abstract_numbers": abstract,
        "numbers": numbers,
        "invalid_abstract_ids": invalid_abstract_ids,
        "duplicate_abstract_ids": duplicate_abstract_ids,
        "invalid_num_ids": invalid_num_ids,
        "duplicate_num_ids": duplicate_num_ids,
    }


def relationship_source_part(rels_part: str) -> str:
    if rels_part == "_rels/.rels":
        return ""
    path = PurePosixPath(rels_part)
    filename = path.name[:-5] if path.name.endswith(".rels") else path.name
    parent = path.parent.parent
    return posixpath.join(parent.as_posix(), filename).lstrip("./")


def resolve_relationship_target(rels_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    source = relationship_source_part(rels_part)
    base = posixpath.dirname(source)
    return posixpath.normpath(posixpath.join(base, target))


def relationship_part_for_source(source_part: str) -> str:
    path = PurePosixPath(source_part)
    return posixpath.join(
        path.parent.as_posix(), "_rels", "%s.rels" % path.name
    ).lstrip("./")


def is_xml_ncname(value: Any) -> bool:
    """Validate the XML NCName lexical space used by OPC relationship IDs."""
    text = str(value or "")
    if not text or ":" in text:
        return False

    def name_start(character: str) -> bool:
        return character == "_" or unicodedata.category(character) in {"Lu", "Ll", "Lt", "Lm", "Lo", "Nl"}

    def name_character(character: str) -> bool:
        return (
            name_start(character)
            or unicodedata.category(character) in {"Mn", "Mc", "Nd", "Pc"}
            or character in ".-\u00b7\u203f\u2040"
        )

    return name_start(text[0]) and all(name_character(character) for character in text[1:])


def is_absolute_relationship_type(value: Any) -> bool:
    text = str(value or "")
    if not text or any(character.isspace() or ord(character) < 0x20 for character in text):
        return False
    try:
        return bool(urlsplit(text).scheme)
    except ValueError:
        return False


def relationship_reference_contract(
    node: etree._Element, attribute_local_name: str
) -> tuple[tuple[str, ...], str | None]:
    """Return the required relationship type suffix and target mode if modeled."""
    element = etree.QName(node)
    key = (element.namespace, element.localname, attribute_local_name)
    contracts = {
        (W, "headerReference", "id"): (("header",), "Internal"),
        (W, "footerReference", "id"): (("footer",), "Internal"),
        (W, "altChunk", "id"): (("aFChunk",), "Internal"),
        (W, "attachedTemplate", "id"): (("attachedTemplate",), None),
        (W, "printerSettings", "id"): (("printerSettings",), "Internal"),
        (W, "hyperlink", "id"): (("hyperlink",), None),
        (A, "blip", "embed"): (("image",), "Internal"),
        (A, "blip", "link"): (("image",), "External"),
        (C, "chart", "id"): (("chart",), "Internal"),
        (DGM, "relIds", "dm"): (("diagramData",), "Internal"),
        (DGM, "relIds", "lo"): (("diagramLayout",), "Internal"),
        (DGM, "relIds", "qs"): (("diagramQuickStyle",), "Internal"),
        (DGM, "relIds", "cs"): (("diagramColors",), "Internal"),
        (O, "OLEObject", "id"): (("oleObject", "package"), "Internal"),
        (V, "imagedata", "id"): (("image",), "Internal"),
    }
    return contracts.get(key, ((), None))


def required_relationship_attributes(node: etree._Element) -> tuple[str, ...]:
    required = {
        (W, "headerReference"): ("id",),
        (W, "footerReference"): ("id",),
        (W, "altChunk"): ("id",),
        (W, "attachedTemplate"): ("id",),
        (W, "printerSettings"): ("id",),
        (DGM, "relIds"): ("dm", "lo", "qs", "cs"),
        (O, "OLEObject"): ("id",),
    }
    name = etree.QName(node)
    if (name.namespace, name.localname) == (C, "chart"):
        parent = node.getparent()
        if parent is not None:
            parent_name = etree.QName(parent)
            if (parent_name.namespace, parent_name.localname) == (A, "graphicData"):
                return ("id",)
        return ()
    return required.get((name.namespace, name.localname), ())


def extract_relationships(
    xml_roots: dict[str, etree._Element], names: set[str]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = {}
    findings: list[dict[str, Any]] = []
    for part, root in sorted(xml_roots.items()):
        if not part.endswith(".rels"):
            continue
        rows: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        root_name = etree.QName(root)
        if root_name.namespace != REL or root_name.localname != "Relationships":
            findings.append(
                issue(
                    "error",
                    "E_XML_INVALID",
                    part,
                    "relationships part has an invalid root element",
                    expected="{.../relationships}Relationships",
                    actual=root.tag,
                )
            )
            records[part] = rows
            continue
        for rel in root.findall("rel:Relationship", NS):
            row = {
                "id": (
                    rel.get("Id").strip() if rel.get("Id") is not None else None
                ),
                "type": (
                    rel.get("Type").strip()
                    if rel.get("Type") is not None
                    else None
                ),
                "target": (
                    rel.get("Target").strip()
                    if rel.get("Target") is not None
                    else None
                ),
                "target_mode": (
                    rel.get("TargetMode").strip()
                    if rel.get("TargetMode") is not None
                    else None
                ),
            }
            rows.append(row)
            relationship_id = row["id"]
            if not is_xml_ncname(relationship_id):
                findings.append(
                    issue(
                        "error",
                        "E_RELATIONSHIP_ID_INVALID",
                        "%s:%s" % (part, relationship_id or "<missing>"),
                        "relationship Id is missing or is not a valid XML NCName",
                        actual=relationship_id,
                    )
                )
            elif relationship_id in seen_ids:
                findings.append(
                    issue(
                        "error",
                        "E_RELATIONSHIP_ID_DUPLICATE",
                        "%s:%s" % (part, relationship_id),
                        "relationship Id must be unique within its .rels part",
                    )
                )
            else:
                seen_ids.add(relationship_id)
            relationship_type = row["type"]
            if not is_absolute_relationship_type(relationship_type):
                findings.append(
                    issue(
                        "error",
                        "E_RELATIONSHIP_TYPE_INVALID",
                        "%s:%s" % (part, row["id"]),
                        "relationship Type must be a non-empty absolute URI",
                        actual=relationship_type,
                    )
                )
            target_mode = row["target_mode"]
            if target_mode not in (None, "Internal", "External"):
                findings.append(
                    issue(
                        "error",
                        "E_RELATIONSHIP_TARGET_INVALID",
                        "%s:%s" % (part, row["id"]),
                        "relationship TargetMode must be Internal, External, or omitted",
                        actual=target_mode,
                    )
                )
            target = row["target"]
            if not target:
                findings.append(
                    issue(
                        "error",
                        "E_RELATIONSHIP_TARGET_INVALID",
                        "%s:%s" % (part, row["id"]),
                        "relationship is missing its required Target",
                        actual=target,
                    )
                )
            elif target_mode in (None, "Internal"):
                resolved = resolve_relationship_target(part, target)
                if resolved == ".." or resolved.startswith("../"):
                    findings.append(
                        issue(
                            "error",
                            "E_RELATIONSHIP_TARGET_OUTSIDE_PACKAGE",
                            "%s:%s" % (part, row["id"]),
                            "internal relationship target escapes the OOXML package",
                            actual=target,
                        )
                    )
                elif resolved not in names:
                    findings.append(
                        issue(
                            "error",
                            "E_RELATIONSHIP_TARGET_MISSING",
                            "%s:%s" % (part, row["id"]),
                            "internal relationship target is missing",
                            actual=resolved,
                        )
                    )
        records[part] = sorted(rows, key=lambda row: str(row.get("id")))
    root_office_documents = [
        item
        for item in records.get("_rels/.rels", [])
        if str(item.get("type") or "") in {
            R + "/officeDocument",
            "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
        }
    ]
    office_document_valid = (
        len(root_office_documents) == 1
        and root_office_documents[0].get("target_mode") in (None, "Internal")
        and resolve_relationship_target(
            "_rels/.rels", str(root_office_documents[0].get("target") or "")
        )
        == "word/document.xml"
    )
    if not office_document_valid:
        findings.append(
            issue(
                "error",
                "E_OFFICE_DOCUMENT_RELATIONSHIP_INVALID",
                "_rels/.rels",
                "package must declare exactly one internal officeDocument "
                "relationship to word/document.xml",
                expected={
                    "count": 1,
                    "target": "word/document.xml",
                    "target_mode": "Internal or omitted",
                },
                actual=root_office_documents,
            )
        )
    return records, findings


def relationship_reference_findings(
    xml_roots: dict[str, etree._Element],
    relationships: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Verify every OOXML relationship attribute names a declared relationship."""
    findings: list[dict[str, Any]] = []
    for part, root in sorted(xml_roots.items()):
        if part.endswith(".rels"):
            continue
        referenced: list[tuple[str, str, etree._Element, str]] = []
        tree = root.getroottree()
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            element = etree.QName(node)
            required_attributes = required_relationship_attributes(node)
            for required_attribute in required_attributes:
                value = node.get(qn(R, required_attribute))
                if value:
                    continue
                findings.append(
                    issue(
                        "error",
                        "E_RELATIONSHIP_REFERENCE_BROKEN",
                        "%s:%s" % (part, tree.getpath(node)),
                        "OOXML element is missing a required relationship reference",
                        expected={"attribute": "r:%s" % required_attribute},
                        actual={"relationship_id": value},
                    )
                )
            for attribute_name, value in node.attrib.items():
                qname = etree.QName(attribute_name)
                if (
                    qname.namespace != R
                    or qname.localname not in {"id", "embed", "link", "dm", "lo", "qs", "cs"}
                    or element.namespace not in UNDERSTOOD_MC_NAMESPACES
                ):
                    continue
                if not value:
                    if (element.namespace, element.localname) == (A, "blip") and qname.localname in {"embed", "link"}:
                        continue
                    if qname.localname not in required_attributes:
                        findings.append(
                            issue(
                                "error",
                                "E_RELATIONSHIP_REFERENCE_BROKEN",
                                "%s:%s" % (part, tree.getpath(node)),
                                "OOXML relationship reference is empty",
                                expected={"attribute": "r:%s" % qname.localname},
                                actual={"relationship_id": value},
                            )
                        )
                    continue
                referenced.append(
                    (value, tree.getpath(node), node, qname.localname)
                    )
        if not referenced:
            continue
        rels_part = relationship_part_for_source(part)
        declared = {
            str(item.get("id")): item
            for item in relationships.get(rels_part, [])
            if item.get("id")
        }
        for relationship_id, xpath, node, attribute_local_name in referenced:
            relationship = declared.get(relationship_id)
            expected_types, expected_mode = relationship_reference_contract(
                node, attribute_local_name
            )
            mode = (
                relationship.get("target_mode") or "Internal"
                if relationship is not None
                else None
            )
            allowed_types = (
                {
                    R + "/" + expected_type
                    for expected_type in expected_types
                }
                | {
                    "http://purl.oclc.org/ooxml/officeDocument/relationships/"
                    + expected_type
                    for expected_type in expected_types
                }
                if expected_types
                else set()
            )
            type_matches = relationship is not None and (
                not allowed_types or relationship.get("type") in allowed_types
            )
            mode_matches = (
                relationship is not None
                and (expected_mode is None or mode == expected_mode)
            )
            if relationship is not None and type_matches and mode_matches:
                continue
            findings.append(
                issue(
                    "error",
                    "E_RELATIONSHIP_REFERENCE_BROKEN",
                    "%s:%s" % (part, xpath),
                    "OOXML relationship reference is undeclared or has the wrong type/mode",
                    expected={
                        "rels_part": rels_part,
                        "declared_id": relationship_id,
                        "type_suffixes": list(expected_types),
                        "target_mode": expected_mode,
                    },
                    actual={
                        "relationship_id": relationship_id,
                        "relationship": relationship,
                    },
                )
            )
    return findings


def story_comparison_parts(
    sections: list[dict[str, Any]],
    relationships: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    """Map physical header/footer parts to stable effective-role identities."""
    relationship_rows = {
        str(item.get("id")): item
        for item in relationships.get("word/_rels/document.xml.rels", [])
        if item.get("id")
    }
    roles: dict[str, set[str]] = {}
    role_variants: dict[tuple[str, str], dict[str, int]] = {}
    for section in sections:
        for family, references in (
            ("header", section.get("effective_header_references", [])),
            ("footer", section.get("effective_footer_references", [])),
        ):
            for reference in references:
                relationship = relationship_rows.get(str(reference.get("rId") or ""))
                if not relationship or relationship.get("target_mode") == "External":
                    continue
                target = relationship.get("target")
                if not isinstance(target, str):
                    continue
                physical_part = resolve_relationship_target(
                    "word/_rels/document.xml.rels", target
                )
                reference_type = str(reference.get("type") or "default")
                variants = role_variants.setdefault((family, reference_type), {})
                if physical_part not in variants:
                    variants[physical_part] = len(variants) + 1
                role = "%s:%s:variant%d" % (
                    family,
                    reference_type,
                    variants[physical_part],
                )
                roles.setdefault(physical_part, set()).add(role)
    return {
        part: "fixed:%s" % "|".join(sorted(values))
        for part, values in roles.items()
    }


def extract_theme_fonts(
    xml_roots: dict[str, etree._Element],
    relationships: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Record the document theme font scheme and its XML-only language selectors."""
    theme_part = None
    rels_part = "word/_rels/document.xml.rels"
    for relationship in relationships.get(rels_part, []):
        relationship_type = str(relationship.get("type") or "")
        target = relationship.get("target")
        if (
            relationship_type.endswith("/theme")
            and isinstance(target, str)
            and relationship.get("target_mode") != "External"
        ):
            theme_part = resolve_relationship_target(rels_part, target)
            break
    if theme_part is None:
        candidates = sorted(
            part
            for part in xml_roots
            if part.startswith("word/theme/")
            and etree.QName(xml_roots[part]).localname == "theme"
        )
        if len(candidates) == 1:
            theme_part = candidates[0]

    schemes: dict[str, Any] = {}
    root = xml_roots.get(theme_part) if theme_part else None
    font_scheme = root.find(".//a:fontScheme", NS) if root is not None else None
    if font_scheme is not None:
        for family, tag in (("major", "majorFont"), ("minor", "minorFont")):
            collection = font_scheme.find("a:%s" % tag, NS)
            if collection is None:
                continue
            supplemental = {
                item.get("script"): item.get("typeface")
                for item in collection.findall("a:font", NS)
                if item.get("script") and item.get("typeface")
            }
            schemes[family] = {
                "latin": (
                    collection.find("a:latin", NS).get("typeface")
                    if collection.find("a:latin", NS) is not None
                    else None
                ),
                "east_asia": (
                    collection.find("a:ea", NS).get("typeface")
                    if collection.find("a:ea", NS) is not None
                    else None
                ),
                "complex_script": (
                    collection.find("a:cs", NS).get("typeface")
                    if collection.find("a:cs", NS) is not None
                    else None
                ),
                "supplemental": supplemental,
            }

    languages: dict[str, str] = {}
    settings = xml_roots.get("word/settings.xml")
    theme_language = settings.find("w:themeFontLang", NS) if settings is not None else None
    if theme_language is not None:
        for attr, key in (
            ("val", "language_ascii"),
            ("eastAsia", "language_east_asia"),
            ("bidi", "language_bidi"),
        ):
            value = theme_language.get(wqn(attr))
            if value:
                languages[key] = value

    return {"part": theme_part, "schemes": schemes, "languages": languages}


def extract_drawings(part: str, root: etree._Element) -> list[dict[str, Any]]:
    """Extract drawing identity and invalid size tokens without coercion errors."""
    records: list[dict[str, Any]] = []
    for kind, xpath in (("inline", ".//wp:inline"), ("anchor", ".//wp:anchor")):
        for index, drawing in enumerate(root.xpath(xpath, namespaces=NS), 1):
            extent = drawing.find("wp:extent", NS)
            invalid_extent = {}
            for axis in ("cx", "cy"):
                raw = extent.get(axis) if extent is not None else None
                token = integer_token(raw)
                if raw is not None and (token is None or int(token) < 0):
                    invalid_extent[axis] = raw
            doc_pr = drawing.find("wp:docPr", NS)
            raw_id = doc_pr.get("id") if doc_pr is not None else None
            token = integer_token(raw_id)
            identifier = int(token) if token is not None else raw_id
            records.append({
                "part": part,
                "location": "%s#%s%d" % (part, kind, index),
                "doc_pr_id": identifier,
                "invalid_extent": invalid_extent,
            })
    return records


def drawing_id_findings(drawings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Require wp:docPr/@id to be unique across every Word story part."""
    by_id: dict[int | str, list[dict[str, Any]]] = {}
    findings: list[dict[str, Any]] = []
    for drawing in drawings:
        if drawing.get("invalid_extent"):
            findings.append(issue(
                "error", "E_XML_INVALID", str(drawing.get("location")),
                "drawing extent must use non-negative integer coordinates",
                actual=drawing["invalid_extent"],
            ))
        identifier = drawing.get("doc_pr_id")
        if not isinstance(identifier, int) or not 0 <= identifier <= (1 << 32) - 1:
            findings.append(
                issue(
                    "error",
                    "E_OOXML_DOCPR_ID_INVALID",
                    str(drawing.get("location")),
                    "wp:docPr/@id must be an unsigned 32-bit integer",
                    actual=identifier,
                    blocking=True,
                )
            )
            continue
        by_id.setdefault(identifier, []).append(drawing)

    for identifier, matches in sorted(by_id.items(), key=lambda item: str(item[0])):
        if len(matches) < 2:
            continue
        locations = [str(item.get("location")) for item in matches]
        findings.append(
            issue(
                "error",
                "E_OOXML_DOCPR_ID_DUPLICATE",
                "wp:docPr@id:%s" % identifier,
                "wp:docPr/@id must be globally unique across the DOCX",
                expected={"id": identifier, "count": 1},
                actual={"id": identifier, "count": len(matches), "locations": locations},
                evidence={"id": identifier, "locations": locations},
                blocking=True,
            )
        )
    return findings


def extract_fields(
    part: str, root: etree._Element
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for index, node in enumerate(root.xpath(".//w:fldChar", namespaces=NS), 1):
        field_type = node.get(wqn("fldCharType"))
        records.append(
            {
                "part": part,
                "kind": "complex_endpoint",
                "index": index,
                "field_type": field_type,
            }
        )
        if field_type == "begin":
            stack.append({"index": index, "separated": False})
        elif field_type == "separate":
            if not stack:
                findings.append(
                    issue(
                        "error",
                        "E_FIELD_UNBALANCED",
                        "%s#fldChar%d" % (part, index),
                        "field separator has no open field",
                    )
                )
            elif stack[-1]["separated"]:
                findings.append(
                    issue(
                        "error",
                        "E_FIELD_UNBALANCED",
                        "%s#fldChar%d" % (part, index),
                        "field has more than one separator",
                    )
                )
            else:
                stack[-1]["separated"] = True
        elif field_type == "end":
            if stack:
                stack.pop()
            else:
                findings.append(
                    issue(
                        "error",
                        "E_FIELD_UNBALANCED",
                        "%s#fldChar%d" % (part, index),
                        "field end has no matching begin",
                    )
                )
        else:
            findings.append(
                issue(
                    "error",
                    "E_FIELD_TYPE",
                    "%s#fldChar%d" % (part, index),
                    "field endpoint has an invalid type",
                    actual=field_type,
                )
            )
    for open_field in stack:
        findings.append(
            issue(
                "error",
                "E_FIELD_UNBALANCED",
                "%s#fldChar%d" % (part, open_field["index"]),
                "field begin has no matching end",
            )
        )
    for index, instruction in enumerate(
        root.xpath(".//w:instrText/text()", namespaces=NS), 1
    ):
        records.append(
            {
                "part": part,
                "kind": "instruction",
                "index": index,
                "instruction": instruction.strip(),
            }
        )
    for index, field in enumerate(root.xpath(".//w:fldSimple", namespaces=NS), 1):
        records.append(
            {
                "part": part,
                "kind": "simple",
                "index": index,
                "instruction": str(field.get(wqn("instr")) or "").strip(),
            }
        )
    return records, findings


def extract_bookmarks(
    part: str, root: etree._Element
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    starts: Counter[str] = Counter()
    ends: Counter[str] = Counter()
    invalid_identifiers: set[str] = set()
    for kind, xpath in (("start", ".//w:bookmarkStart"), ("end", ".//w:bookmarkEnd")):
        for index, node in enumerate(root.xpath(xpath, namespaces=NS), 1):
            raw_identifier = str(node.get(wqn("id")) or "")
            canonical = integer_token(raw_identifier)
            identifier = canonical if canonical is not None else raw_identifier
            if canonical is None:
                invalid_identifiers.add(identifier)
            if kind == "start" and node.get(wqn("name")) is None:
                findings.append(
                    issue(
                        "error",
                        "E_BOOKMARK_UNBALANCED",
                        "%s#bookmark:%s" % (part, identifier or "<missing>"),
                        "bookmarkStart is missing its required w:name",
                    )
                )
            if kind == "start":
                starts[identifier] += 1
            else:
                ends[identifier] += 1
            records.append(
                {
                    "part": part,
                    "kind": kind,
                    "index": index,
                    "id": identifier,
                    "raw_id": raw_identifier,
                    "name": node.get(wqn("name")) if kind == "start" else None,
                }
            )
    # A single bookmark ID must have exactly one start and one matching end.
    # Equal start/end *counts* are not enough: two starts and two ends sharing
    # one ID keep counts balanced yet destroy the 1:1 pairing that jumps and
    # cross-references rely on, so the reported range becomes ambiguous. Check
    # empty IDs, per-ID uniqueness of both start and end, and (in a single
    # document-order walk) that no end precedes its start.
    open_ids: Counter[str] = Counter()
    ordering_reported: set[str] = set()
    for node in root.xpath(".//w:bookmarkStart | .//w:bookmarkEnd", namespaces=NS):
        raw_identifier = str(node.get(wqn("id")) or "")
        canonical = integer_token(raw_identifier)
        identifier = canonical if canonical is not None else raw_identifier
        if etree.QName(node).localname == "bookmarkStart":
            open_ids[identifier] += 1
        elif open_ids[identifier] <= 0:
            if identifier not in ordering_reported:
                ordering_reported.add(identifier)
                findings.append(
                    issue(
                        "error",
                        "E_BOOKMARK_UNBALANCED",
                        "%s#bookmark:%s" % (part, identifier),
                        "bookmarkEnd appears before its matching bookmarkStart",
                        expected="bookmarkStart before bookmarkEnd",
                        actual="bookmarkEnd first",
                    )
                )
        else:
            open_ids[identifier] -= 1
    for identifier in sorted(set(starts) | set(ends)):
        if identifier in invalid_identifiers:
            findings.append(
                issue(
                    "error",
                    "E_BOOKMARK_UNBALANCED",
                    "%s#bookmark:%s" % (part, identifier or "<missing>"),
                    "bookmark w:id must be an integer",
                    expected="ST_DecimalNumber",
                    actual=identifier,
                )
            )
            continue
        if starts[identifier] != ends[identifier]:
            findings.append(
                issue(
                    "error",
                    "E_BOOKMARK_UNBALANCED",
                    "%s#bookmark:%s" % (part, identifier),
                    "bookmark start/end counts do not match",
                    expected=starts[identifier],
                    actual=ends[identifier],
                )
            )
            continue
        if starts[identifier] > 1 or ends[identifier] > 1:
            findings.append(
                issue(
                    "error",
                    "E_BOOKMARK_UNBALANCED",
                    "%s#bookmark:%s" % (part, identifier),
                    "bookmark id is used by more than one start/end pair",
                    expected=1,
                    actual=starts[identifier],
                )
            )
    return records, findings


def numbering_reference_findings(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only deterministic broken-numbering errors.

    Stylistic preferences such as heading order, direct formatting, fake headings,
    and manually typed list markers are not document-integrity errors.
    """
    findings: list[dict[str, Any]] = []
    style_manifest = manifest.get("styles", {})
    numbering_manifest = manifest.get("numbering", {})
    numbering = numbering_manifest.get("numbers", {})
    abstract_numbers = numbering_manifest.get("abstract_numbers", {})
    for identifier in numbering_manifest.get("invalid_abstract_ids", []):
        findings.append(
            issue(
                "error",
                "E_NUMBERING_ABSTRACT_REFERENCE_BROKEN",
                "word/numbering.xml",
                "abstractNumId is missing or is not an integer",
                actual=identifier,
            )
        )
    for identifier in numbering_manifest.get("duplicate_abstract_ids", []):
        findings.append(
            issue(
                "error",
                "E_NUMBERING_ABSTRACT_REFERENCE_BROKEN",
                "word/numbering.xml#abstractNumId:%s" % identifier,
                "abstractNumId must be unique",
                actual=identifier,
            )
        )
    for identifier in numbering_manifest.get("invalid_num_ids", []):
        findings.append(
            issue(
                "error",
                "E_NUMBERING_REFERENCE_BROKEN",
                "word/numbering.xml",
                "numId is missing or is not an integer",
                actual=identifier,
            )
        )
    for identifier in numbering_manifest.get("duplicate_num_ids", []):
        findings.append(
            issue(
                "error",
                "E_NUMBERING_REFERENCE_BROKEN",
                "word/numbering.xml#numId:%s" % identifier,
                "numId must be unique",
                actual=identifier,
            )
        )
    for num_id, record in numbering.items():
        abstract_id = record.get("abstract_num_id")
        if abstract_id is None or str(abstract_id) not in abstract_numbers:
            findings.append(
                issue(
                    "error",
                    "E_NUMBERING_ABSTRACT_REFERENCE_BROKEN",
                    "word/numbering.xml#numId:%s" % num_id,
                    "numbering instance references an undefined abstractNumId",
                    actual=abstract_id,
                )
            )
    for paragraph in manifest.get("paragraphs", []):
        direct_ppr = paragraph.get("pPr", {})
        num_id_token = direct_ppr.get("num_id_token")
        num_level_token = direct_ppr.get("num_level_token")
        if num_id_token is not None and integer_token(num_id_token) is None:
            findings.append(
                issue(
                    "error",
                    "E_NUMBERING_REFERENCE_BROKEN",
                    paragraph["location"],
                    "paragraph numId is not an integer",
                    actual=num_id_token,
                )
            )
            continue
        if num_level_token is not None and integer_token(num_level_token) is None:
            findings.append(
                issue(
                    "error",
                    "E_NUMBERING_REFERENCE_BROKEN",
                    paragraph["location"],
                    "paragraph numbering level is not an integer",
                    actual=num_level_token,
                )
            )
            continue
        num_id = paragraph.get("num_id")
        if num_id is None:
            style_id = paragraph_style_id(style_manifest, paragraph)
            effective = effective_style(style_manifest, style_id) if style_id else None
            if effective:
                effective_ppr = effective.get("pPr", {})
                effective_num_id_token = effective_ppr.get("num_id_token")
                if effective_num_id_token is not None and integer_token(effective_num_id_token) is None:
                    findings.append(
                        issue(
                            "error",
                            "E_NUMBERING_REFERENCE_BROKEN",
                            paragraph["location"],
                            "effective style numId is not an integer",
                            actual=effective_num_id_token,
                        )
                    )
                    continue
                num_id = effective_ppr.get("num_id")
        if num_id not in (None, 0) and str(num_id) not in numbering:
            findings.append(
                issue(
                    "error",
                    "E_NUMBERING_REFERENCE_BROKEN",
                    paragraph["location"],
                    "paragraph references an undefined numId",
                    actual=num_id,
                )
            )
    return findings


def geometry_findings(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Report schema-invalid unsigned page and table-grid measurements."""
    findings: list[dict[str, Any]] = []
    for section in manifest.get("sections", []):
        index = section.get("index")
        page = section.get("page", {})
        invalid_page_tokens = {
            name: page.get(name)
            for name in ("width_token", "height_token")
            if page.get(name) is not None
            and not is_unsigned_measure(page.get(name))
        }
        if invalid_page_tokens:
            findings.append(
                issue(
                    "error",
                    "E_PAGE_SIZE_INVALID",
                    "section[%s]" % index,
                    "page width and height must be valid unsigned OOXML measurements",
                    actual=invalid_page_tokens,
                )
            )

    for table in manifest.get("tables", []):
        invalid_columns = [
            {"index": index, "width": token}
            for index, token in enumerate(table.get("grid_width_tokens", []), 1)
            if token is not None and not is_unsigned_measure(token)
        ]
        if invalid_columns:
            findings.append(
                issue(
                    "error",
                    "E_TABLE_GRID_WIDTH_INVALID",
                    str(table.get("location")),
                    "table grid columns must use valid unsigned OOXML measurements",
                    actual=invalid_columns,
                )
            )
    return findings


def content_type_findings(
    content_types_root: etree._Element | None,
    name_set: set[str],
) -> list[dict[str, Any]]:
    """Verify the main document part is declared with a Word content type.

    Parse the OPC content-type map, reject malformed/duplicate declarations,
    require every package part to resolve to a type, and confirm that
    word/document.xml resolves to a WordprocessingML main-document type.
    """
    if content_types_root is None or "word/document.xml" not in name_set:
        return []
    findings: list[dict[str, Any]] = []
    root_name = etree.QName(content_types_root)
    if (
        root_name.namespace
        != "http://schemas.openxmlformats.org/package/2006/content-types"
        or root_name.localname != "Types"
    ):
        return [
            issue(
                "error",
                "E_CONTENT_TYPE_INVALID",
                "[Content_Types].xml",
                "content-types part has an invalid root element",
                expected="{.../content-types}Types",
                actual=content_types_root.tag,
            )
        ]
    main_types = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        # Templates share the same body root; accept the macro/template variants
        # so a legitimately .dotx-shaped package is not misreported.
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
        "application/vnd.ms-word.document.macroEnabled.main+xml",
        "application/vnd.ms-word.template.macroEnabledTemplate.main+xml",
    }
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for node in content_types_root:
        if not isinstance(node.tag, str):
            continue
        local = etree.QName(node).localname
        if local == "Default":
            extension = str(node.get("Extension") or "").strip().lower()
            content_type = str(node.get("ContentType") or "").strip()
            if not extension or not content_type or extension in defaults:
                findings.append(
                    issue(
                        "error",
                        "E_CONTENT_TYPE_INVALID",
                        "[Content_Types].xml",
                        "Default declarations require a unique non-empty Extension and ContentType",
                        actual={"extension": extension, "content_type": content_type},
                    )
                )
            else:
                defaults[extension] = content_type
        elif local == "Override":
            part_name = str(node.get("PartName") or "").strip()
            normalized = part_name.lstrip("/")
            content_type = str(node.get("ContentType") or "").strip()
            if (
                not part_name.startswith("/")
                or not normalized
                or not content_type
                or normalized in overrides
            ):
                findings.append(
                    issue(
                        "error",
                        "E_CONTENT_TYPE_INVALID",
                        "[Content_Types].xml",
                        "Override declarations require a unique absolute PartName and non-empty ContentType",
                        actual={"part_name": part_name, "content_type": content_type},
                    )
                )
            else:
                overrides[normalized] = content_type
    resolved = overrides.get("word/document.xml")
    if resolved is None:
        resolved = defaults.get("xml")
    if resolved not in main_types:
        findings.append(
            issue(
                "error",
                "E_CONTENT_TYPE_INVALID",
                "[Content_Types].xml",
                "main document part is not declared with a WordprocessingML "
                "main-document content type",
                actual=resolved,
                expected=sorted(main_types),
            )
        )
    for part_name in sorted(name_set - {"[Content_Types].xml"}):
        if part_name in overrides:
            continue
        extension = (
            "rels"
            if part_name.endswith(".rels")
            else PurePosixPath(part_name).suffix.lstrip(".").lower()
        )
        if extension and extension in defaults:
            continue
        findings.append(
            issue(
                "error",
                "E_CONTENT_TYPE_INVALID",
                "[Content_Types].xml",
                "package part has no applicable content-type declaration",
                actual=part_name,
            )
        )
    return findings


def inspect_docx(path: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not path.exists():
        raise AuditError("DOCX does not exist: %s" % path)
    try:
        with ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                return {
                    "file": {
                        "path": str(path.resolve()),
                        "size": path.stat().st_size,
                        "sha256": sha256_file(path),
                    },
                    "findings": [
                        issue(
                            "error",
                            "E_ZIP_CRC",
                            bad_member,
                            "ZIP CRC check failed",
                        )
                    ],
                }
            names = [item.filename for item in archive.infolist() if not item.is_dir()]
            duplicate_members = sorted(
                name for name, count in Counter(names).items() if count > 1
            )
            for name in duplicate_members:
                findings.append(
                    issue(
                        "error",
                        "E_ZIP_MEMBER_DUPLICATE",
                        name,
                        "OOXML package contains duplicate ZIP members",
                        actual=Counter(names)[name],
                    )
                )
            name_set = set(names)
            required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
            for missing in sorted(required - name_set):
                findings.append(issue("error", "E_PART_MISSING", missing, "required OOXML part is missing"))

            xml_roots: dict[str, etree._Element] = {}
            parts: dict[str, dict[str, Any]] = {}
            for name in sorted(names):
                data = archive.read(name)
                entry: dict[str, Any] = {"size": len(data), "sha256": sha256_bytes(data)}
                if name.endswith((".xml", ".rels")):
                    try:
                        root = parse_xml(data, name)
                        xml_roots[name] = root
                        entry["canonical_sha256"] = canonical_xml_hash(root)
                        entry["structure_sha256"] = structural_hash(
                            root, clear_text=True
                        )
                    except AuditError as exc:
                        findings.append(issue("error", "E_XML_INVALID", name, str(exc)))
                parts[name] = entry

            semantic_roots = {
                name: (
                    markup_compatibility_view(root)
                    if not name.endswith(".rels") and name != "[Content_Types].xml"
                    else root
                )
                for name, root in xml_roots.items()
            }
            document = semantic_roots.get("word/document.xml")
            if document is not None and document.tag != wqn("document"):
                findings.append(
                    issue(
                        "error",
                        "E_DOCUMENT_ROOT_INVALID",
                        "word/document.xml",
                        "main document part is not a WordprocessingML w:document",
                        actual=etree.QName(document).localname,
                        expected="w:document",
                    )
                )
            elif document is not None and len(document.findall("w:body", NS)) != 1:
                findings.append(
                    issue(
                        "error",
                        "E_DOCUMENT_ROOT_INVALID",
                        "word/document.xml",
                        "main document must contain exactly one direct w:body",
                        expected=1,
                        actual=len(document.findall("w:body", NS)),
                    )
                )
            findings.extend(
                content_type_findings(xml_roots.get("[Content_Types].xml"), name_set)
            )
            sections = extract_sections(document) if document is not None else []
            add_effective_story_references(sections)
            styles = extract_styles(semantic_roots)
            numbering = extract_numbering(semantic_roots)
            relationships, rel_findings = extract_relationships(xml_roots, name_set)
            findings.extend(rel_findings)
            findings.extend(
                relationship_reference_findings(semantic_roots, relationships)
            )
            theme_fonts = extract_theme_fonts(semantic_roots, relationships)
            for part, root in sorted(semantic_roots.items()):
                findings.extend(ooxml_property_order_findings(part, root))

            paragraphs: list[dict[str, Any]] = []
            tables: list[dict[str, Any]] = []
            drawings: list[dict[str, Any]] = []
            fields: list[dict[str, Any]] = []
            bookmarks: list[dict[str, Any]] = []
            for part in story_parts(names):
                root = semantic_roots.get(part)
                if root is None:
                    continue
                paragraphs.extend(extract_paragraphs(part, root))
                tables.extend(extract_tables(part, root))
                drawings.extend(extract_drawings(part, root))
                part_fields, field_findings = extract_fields(part, root)
                fields.extend(part_fields)
                findings.extend(field_findings)
                part_bookmarks, bookmark_findings = extract_bookmarks(part, root)
                bookmarks.extend(part_bookmarks)
                findings.extend(bookmark_findings)

            comparison_parts = story_comparison_parts(sections, relationships)
            for collection in (
                paragraphs,
                tables,
                drawings,
                fields,
                bookmarks,
            ):
                for record in collection:
                    physical_part = str(record.get("part") or "")
                    if physical_part in comparison_parts:
                        record["comparison_part"] = comparison_parts[physical_part]
                    elif FIXED_STORY_RE.match(physical_part):
                        record["comparison_part"] = "unreferenced:%s" % physical_part

            findings.extend(drawing_id_findings(drawings))

            manifest = {
                "file": {
                    "path": str(path.resolve()),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                },
                "parts": parts,
                "sections": sections,
                "styles": styles,
                "numbering": numbering,
                "theme_fonts": theme_fonts,
                "relationships": relationships,
                "paragraphs": paragraphs,
                "tables": tables,
                "drawings": drawings,
                "fields": fields,
                "bookmarks": bookmarks,
                "summary": {
                    "part_count": len(parts),
                    "section_count": len(sections),
                    "paragraph_count": len(paragraphs),
                    "table_count": len(tables),
                    "drawing_count": len(drawings),
                    "field_count": len(fields),
                    "bookmark_count": len(bookmarks),
                },
            }
            findings.extend(numbering_reference_findings(manifest))
            findings.extend(geometry_findings(manifest))
            manifest["findings"] = findings
            return manifest
    except (BadZipFile, OSError, NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        # NotImplementedError is raised by zipfile.testzip/read when a member
        # uses an unsupported compression method; treat it as an unreadable
        # package rather than letting it escape as an uncontrolled crash.
        return {
            "file": {"path": str(path.resolve())},
            "findings": [issue("error", "E_DOCX_OPEN", str(path), str(exc))],
        }


def paragraph_style_id(
    style_manifest: dict[str, Any], paragraph: dict[str, Any]
) -> str | None:
    raw_style_id = paragraph.get("style_id") or style_manifest.get(
        "default_style_ids", {}
    ).get("paragraph", "Normal")
    return resolve_style_id(style_manifest, str(raw_style_id))


def normalized_style_marker(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or ""), flags=re.UNICODE).casefold()


def style_chain_has_literal_semantics(
    style_manifest: dict[str, Any], style_id: Any
) -> bool:
    resolved = resolve_style_id(style_manifest, str(style_id)) if style_id else None
    records = style_manifest.get("styles", {})
    seen: set[str] = set()
    while resolved and resolved not in seen:
        seen.add(resolved)
        record = records.get(resolved, {})
        markers = {
            normalized_style_marker(resolved),
            normalized_style_marker(record.get("name")),
        }
        if markers & LITERAL_STYLE_NAMES:
            return True
        based_on = record.get("based_on")
        resolved = resolve_style_id(style_manifest, str(based_on)) if based_on else None
    return False


def is_han_character(character: str) -> bool:
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in HAN_CODEPOINT_RANGES)


def paragraph_is_deliverable_content(paragraph: dict[str, Any]) -> bool:
    """Whether a paragraph is actually rendered deliverable body text.

    Final-content policy checks (Chinese ASCII quotes, table first-line indent)
    must run only on content a reader can see. A header/footer part that no
    section references is dead furniture: inspect_docx marks such records with a
    ``comparison_part`` of ``unreferenced:<part>``. Excluding them here keeps an
    orphan header's stale fonts/quotes from blocking an otherwise valid body.
    """
    part = str(paragraph.get("part") or "")
    if not DELIVERABLE_TEXT_PART_RE.match(part):
        return False
    comparison_part = str(paragraph.get("comparison_part") or "")
    if comparison_part.startswith("unreferenced:"):
        return False
    return True


def chinese_letter_statistics(text: str) -> dict[str, int | float]:
    letter_count = 0
    han_character_count = 0
    for character in text:
        if not unicodedata.category(character).startswith("L"):
            continue
        letter_count += 1
        if is_han_character(character):
            han_character_count += 1
    ratio = han_character_count / letter_count if letter_count else 0.0
    return {
        "han_character_count": han_character_count,
        "letter_count": letter_count,
        "han_letter_ratio": round(ratio, 6),
    }


def text_context(text: str, offset: int, radius: int = 24) -> str:
    start = max(0, offset - radius)
    end = min(len(text), offset + radius + 1)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return "%s%s%s" % (prefix, text[start:end], suffix)


def non_toc_run_text(run: dict[str, Any]) -> str:
    """Exclude only TOC spans; keep original offsets in the run record."""
    text = str(run.get("text") or "")
    chunks: list[str] = []
    cursor = 0
    for start, end in run.get("toc_text_ranges", []):
        chunks.append(text[cursor:start])
        cursor = end
    chunks.append(text[cursor:])
    return "".join(chunks)


def chinese_ascii_double_quote_findings(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Find U+0022 in visible, non-literal, non-TOC Chinese paragraph text.

    A paragraph is Chinese when Han characters are more than 50 percent of all
    Unicode letters in non-exempt visible runs owned by that logical paragraph.
    Digits, punctuation, symbols, and whitespace do not affect the ratio. Field
    instructions are excluded because run text records only w:t, not
    w:instrText. TOC placeholders/cached entries are excluded by structural text
    ranges, including when they share a run with non-TOC prose. Deleted revision
    text is likewise excluded because Word stores it in w:delText.
    """
    findings: list[dict[str, Any]] = []
    style_manifest = manifest.get("styles", {})
    summary = {
        "performed": True,
        "definition": (
            "U+0022 in non-TOC, non-literal visible text of a logical paragraph "
            "whose eligible Han/Unicode-letter ratio is strictly greater than 0.5"
        ),
        "han_letter_ratio_threshold": (
            CHINESE_LETTER_RATIO_THRESHOLD_NUMERATOR
            / CHINESE_LETTER_RATIO_THRESHOLD_DENOMINATOR
        ),
        "threshold_operator": ">",
        "paragraphs_examined": 0,
        "chinese_paragraph_count": 0,
        "non_chinese_paragraph_count": 0,
        "paragraphs_without_letters": 0,
        "excluded_literal_paragraph_count": 0,
        "excluded_literal_run_count": 0,
        "excluded_toc_run_count": 0,
        "excluded_toc_character_count": 0,
        "finding_count": 0,
    }

    for paragraph in manifest.get("paragraphs", []):
        if not paragraph_is_deliverable_content(paragraph):
            continue
        summary["paragraphs_examined"] += 1

        paragraph_tag = str(paragraph.get("sdt_tag") or "").casefold()
        paragraph_style = paragraph_style_id(style_manifest, paragraph)
        if (
            paragraph_tag in LITERAL_SDT_TAGS
            or style_chain_has_literal_semantics(style_manifest, paragraph_style)
        ):
            summary["excluded_literal_paragraph_count"] += 1
            continue

        paragraph_xpath = paragraph.get("xpath")
        owned_runs = [
            run
            for run in paragraph.get("runs", [])
            if not run.get("owner_paragraph_xpath")
            or run.get("owner_paragraph_xpath") == paragraph_xpath
        ]
        eligible_runs: list[dict[str, Any]] = []
        for run in owned_runs:
            run_properties = run.get("rPr", {})
            run_tag = str(run.get("sdt_tag") or "").casefold()
            if (
                effective_run_hidden(style_manifest, paragraph_style, run)
                or run_tag in LITERAL_SDT_TAGS
                or style_chain_has_literal_semantics(
                    style_manifest, run_properties.get("character_style_id")
                )
            ):
                summary["excluded_literal_run_count"] += 1
                continue
            toc_ranges = run.get("toc_text_ranges", [])
            if toc_ranges:
                summary["excluded_toc_run_count"] += 1
                summary["excluded_toc_character_count"] += sum(
                    end - start for start, end in toc_ranges
                )
                if not non_toc_run_text(run):
                    continue
            eligible_runs.append(run)

        eligible_text = "".join(non_toc_run_text(run) for run in eligible_runs)
        language_statistics = chinese_letter_statistics(eligible_text)
        han_character_count = int(language_statistics["han_character_count"])
        letter_count = int(language_statistics["letter_count"])
        if letter_count == 0:
            summary["paragraphs_without_letters"] += 1
            continue
        # Integer comparison keeps the strict 50-percent boundary exact even
        # for very long paragraphs; the rounded ratio is reporting evidence only.
        if (
            han_character_count * CHINESE_LETTER_RATIO_THRESHOLD_DENOMINATOR
            <= letter_count * CHINESE_LETTER_RATIO_THRESHOLD_NUMERATOR
        ):
            summary["non_chinese_paragraph_count"] += 1
            continue
        summary["chinese_paragraph_count"] += 1

        full_text = "".join(str(run.get("text") or "") for run in owned_runs)
        run_start = 0
        eligible_run_ids = {id(run) for run in eligible_runs}
        for run in owned_runs:
            run_text = str(run.get("text") or "")
            run_properties = run.get("rPr", {})
            if id(run) in eligible_run_ids:
                for character_offset, character in enumerate(run_text):
                    if character != '"' or any(
                        start <= character_offset < end
                        for start, end in run.get("toc_text_ranges", [])
                    ):
                        continue
                    paragraph_offset = run_start + character_offset
                    findings.append(
                        issue(
                            "error",
                            "E_CHINESE_ASCII_DOUBLE_QUOTE",
                            "%s/run%s/char%s"
                            % (
                                paragraph.get("location"),
                                run.get("index"),
                                character_offset + 1,
                            ),
                            "Chinese paragraph contains an ASCII double quote",
                            expected={
                                "opening_quote": "\u201c",
                                "closing_quote": "\u201d",
                            },
                            actual={"character": '"', "codepoint": "U+0022"},
                            evidence={
                                "context": text_context(full_text, paragraph_offset),
                                "paragraph_xpath": paragraph_xpath,
                                "run_xpath": run.get("xpath"),
                                "paragraph_character_offset": paragraph_offset,
                                "run_character_offset": character_offset,
                                "paragraph_style_id": paragraph.get("style_id"),
                                "run_character_style_id": run_properties.get(
                                    "character_style_id"
                                ),
                                **language_statistics,
                            },
                        )
                    )
            run_start += len(run_text)

    summary["finding_count"] = len(findings)
    return findings, summary


def effective_run_hidden(
    style_manifest: dict[str, Any],
    paragraph_style: Any,
    run: dict[str, Any],
) -> bool:
    """Use style-toggle semantics, with direct run visibility taking precedence."""
    return bool(effective_run_properties(
        {"styles": style_manifest}, {"style_id": paragraph_style}, run
    ).get("hidden", False))


class WordCountCounter:
    """Python port of larksuite/cli docxparse/wordcount.go."""

    def __init__(self) -> None:
        self.word_count = 0
        self.char_count = 0
        self.breakdown = {
            "han_chars": 0,
            "english_words": 0,
            "number_words": 0,
            "chinese_punctuations": 0,
            "english_letters": 0,
            "digits": 0,
            "english_punctuations": 0,
            "symbol_words": 0,
            "symbol_chars": 0,
        }
        self.lexeme: str | None = None
        self.lexeme_has_digit = False
        self.symbol_run_length = 0
        self.at_boundary = True

    def count_segments(self, segments: list[tuple[str, bool]]) -> dict[str, Any]:
        for text, is_code in segments:
            self.end_unit()
            self.at_boundary = True
            if is_code:
                self.write_code(text)
            else:
                self.write(text)
            self.end_unit()
            self.at_boundary = True
        self.end_unit()
        return {
            "word_count": self.word_count,
            "char_count": self.char_count,
            "breakdown": dict(self.breakdown),
        }

    def write(self, value: str) -> None:
        offset = 0
        while offset < len(value):
            character = value[offset]
            if self.lexeme is None and character.isascii() and character.isalnum():
                token = match_word_count_ascii_compound(value[offset:])
                if token:
                    self.write_ascii_compound(token)
                    offset += len(token)
                    continue
            if (
                character == "/"
                and offset > 0
                and offset + 1 < len(value)
                and is_han_character(value[offset - 1])
                and is_han_character(value[offset + 1])
            ):
                self.end_unit()
                self.breakdown["english_punctuations"] += 1
                self.breakdown["symbol_words"] += 1
                self.word_count += 1
                self.char_count += 1
                self.at_boundary = False
                offset += 1
                continue
            self.write_character(character, code=False)
            offset += 1

    def write_code(self, value: str) -> None:
        for character in value:
            self.write_character(character, code=True)

    def write_character(self, character: str, *, code: bool) -> None:
        if character.isspace():
            self.end_unit()
            self.at_boundary = True
            return
        if is_han_character(character):
            self.end_lexeme()
            self.end_symbol_run(False)
            self.breakdown["han_chars"] += 1
            self.word_count += 1
            self.char_count += 1
            self.at_boundary = False
            return
        if character.isascii() and character.isalpha():
            self.end_symbol_run(False)
            self.breakdown["english_letters"] += 1
            self.char_count += 1
            if self.lexeme is None or self.lexeme == "number":
                self.lexeme = "english"
            self.at_boundary = False
            return
        if character.isascii() and character.isdigit():
            self.end_symbol_run(False)
            self.breakdown["digits"] += 1
            self.char_count += 1
            self.lexeme_has_digit = True
            if self.lexeme is None:
                self.lexeme = "number"
            self.at_boundary = False
            return
        if is_word_count_chinese_punctuation(character):
            self.end_lexeme()
            self.end_symbol_run(False)
            self.breakdown["chinese_punctuations"] += 1
            self.word_count += 1
            self.char_count += 1
            self.at_boundary = False
            return
        if character in WORD_COUNT_ENGLISH_PUNCTUATION:
            if code:
                keeps_lexeme = self.lexeme == "english" and character in {"'", "-"}
            else:
                keeps_lexeme = (
                    self.lexeme == "english"
                    and (
                        character in {"'", "-"}
                        or self.lexeme_has_digit
                        and character == "."
                    )
                ) or (
                    self.lexeme == "number"
                    and character in {".", ",", "-"}
                )
            if not keeps_lexeme:
                had_lexeme = self.lexeme is not None
                self.end_lexeme()
                if not had_lexeme and (
                    self.symbol_run_length > 0 or self.at_boundary
                ):
                    self.symbol_run_length += 1
            self.breakdown["english_punctuations"] += 1
            self.char_count += 1
            if keeps_lexeme:
                self.at_boundary = False
            return
        if unicodedata.category(character).startswith("S"):
            self.end_lexeme()
            self.end_symbol_run(False)
            units = len(character.encode("utf-16-le")) // 2
            self.breakdown["symbol_words"] += 1
            self.breakdown["symbol_chars"] += units
            self.word_count += 1
            self.char_count += units
            self.at_boundary = False
            return
        self.end_lexeme()
        self.end_symbol_run(False)
        self.at_boundary = False

    def write_ascii_compound(self, token: str) -> None:
        self.end_unit()
        self.breakdown["english_words"] += 1
        self.word_count += 1
        for character in token:
            if character.isascii() and character.isalpha():
                self.breakdown["english_letters"] += 1
                self.char_count += 1
            elif character.isascii() and character.isdigit():
                self.breakdown["digits"] += 1
                self.char_count += 1
            elif character in WORD_COUNT_ENGLISH_PUNCTUATION:
                self.breakdown["english_punctuations"] += 1
                self.char_count += 1
        self.at_boundary = False

    def end_unit(self) -> None:
        self.end_lexeme()
        self.end_symbol_run(True)

    def end_lexeme(self) -> None:
        if self.lexeme == "english":
            self.breakdown["english_words"] += 1
            self.word_count += 1
        elif self.lexeme == "number":
            self.breakdown["number_words"] += 1
            self.word_count += 1
        self.lexeme = None
        self.lexeme_has_digit = False

    def end_symbol_run(self, count_word: bool) -> None:
        if self.symbol_run_length > 0 and count_word:
            self.breakdown["symbol_words"] += 1
            self.word_count += 1
        if self.symbol_run_length > 0:
            self.at_boundary = False
        self.symbol_run_length = 0


def match_word_count_ascii_compound(value: str) -> str:
    match = WORD_COUNT_URL_TOKEN_RE.match(value)
    if match is not None:
        return match.group(0)
    match = WORD_COUNT_ASCII_COMPOUND_RE.match(value)
    if match is None:
        return ""
    token = match.group(0)
    return token if any(character.isascii() and character.isalpha() for character in token) else ""


def is_word_count_chinese_punctuation(character: str) -> bool:
    if character in WORD_COUNT_CHINESE_PUNCTUATION:
        return True
    return (
        unicodedata.category(character).startswith("P")
        and unicodedata.east_asian_width(character) in {"W", "F"}
    )


def word_count_profile(manifest: dict[str, Any]) -> dict[str, Any]:
    """Count visible text in the main document story using the CLI contract."""
    style_manifest = manifest.get("styles", {})
    segments: list[tuple[str, bool]] = []
    paragraph_count = 0
    visible_run_count = 0
    hidden_run_count = 0
    revision_run_count_excluded = 0
    duplicate_textbox_run_count_excluded = 0

    for paragraph in manifest.get("paragraphs", []):
        if paragraph.get("part") != "word/document.xml":
            continue
        paragraph_xpath = paragraph.get("xpath")
        paragraph_style = paragraph_style_id(style_manifest, paragraph)
        paragraph_tag = str(paragraph.get("sdt_tag") or "").casefold()
        code_segment = (
            paragraph_tag in LITERAL_SDT_TAGS
            or style_chain_has_literal_semantics(style_manifest, paragraph_style)
        )
        pieces: list[str] = []
        for run in paragraph.get("runs", []):
            owner_xpath = run.get("owner_paragraph_xpath")
            if owner_xpath and owner_xpath != paragraph_xpath:
                duplicate_textbox_run_count_excluded += 1
                continue
            if not run.get("word_count_visible", True):
                revision_run_count_excluded += 1
                continue
            if effective_run_hidden(style_manifest, paragraph_style, run):
                hidden_run_count += 1
                continue
            text = str(run.get("word_count_text") or "")
            if not text:
                continue
            pieces.append(text)
            visible_run_count += 1
        text = "".join(pieces)
        if text.strip():
            segments.append((text, code_segment))
            paragraph_count += 1

    profile = WordCountCounter().count_segments(segments)
    profile.update(
        {
            "contract": "larksuite-cli-docxparse-wordcount-v1",
            "scope": "word/document.xml visible text",
            "revision_view": "final",
            "paragraph_count": paragraph_count,
            "visible_run_count": visible_run_count,
            "hidden_run_count": hidden_run_count,
            "revision_run_count_excluded": revision_run_count_excluded,
            "duplicate_textbox_run_count_excluded": (
                duplicate_textbox_run_count_excluded
            ),
            "automatic_numbering_markers_included": False,
            "excluded_stories": [
                "headers",
                "footers",
                "footnotes",
                "endnotes",
                "comments",
            ],
        }
    )
    return profile


def word_count_findings(
    manifest: dict[str, Any],
    minimum: int | None,
    maximum: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profile = word_count_profile(manifest)
    configured = minimum is not None or maximum is not None
    check = {
        "performed": True,
        "configured": configured,
        "inclusive": True,
        "expected": {"min": minimum, "max": maximum},
        **profile,
    }
    below_minimum = minimum is not None and profile["word_count"] < minimum
    above_maximum = maximum is not None and profile["word_count"] > maximum
    check["passed"] = not below_minimum and not above_maximum
    if not configured or check["passed"]:
        return [], check
    if minimum is not None and maximum is not None:
        repair_hint = (
            "Adjust visible main-document word_count to the inclusive "
            "%d-%d range." % (minimum, maximum)
        )
    elif minimum is not None:
        repair_hint = (
            "Increase visible main-document word_count to at least %d." % minimum
        )
    else:
        repair_hint = (
            "Reduce visible main-document word_count to at most %d." % maximum
        )
    return [
        issue(
            "error",
            "E_WORD_COUNT_OUT_OF_RANGE",
            "word/document.xml",
            "word_count does not satisfy the requested inclusive range",
            expected={"min": minimum, "max": maximum},
            actual=profile["word_count"],
            repair_hint=repair_hint,
            evidence={
                "char_count": profile["char_count"],
                "breakdown": profile["breakdown"],
                "scope": profile["scope"],
                "revision_view": profile["revision_view"],
            },
        )
    ], check


def effective_numbering_level(
    numbering: dict[str, Any], num_id: Any, level: Any
) -> dict[str, Any] | None:
    if num_id in (None, 0):
        return None
    number = numbering.get("numbers", {}).get(str(num_id))
    if not isinstance(number, dict):
        return None
    abstract_id = number.get("abstract_num_id")
    abstract = numbering.get("abstract_numbers", {}).get(str(abstract_id))
    if not isinstance(abstract, dict):
        return None
    level_key = str(level or 0)
    base = copy.deepcopy(abstract.get("levels", {}).get(level_key, {}))
    override = number.get("overrides", {}).get(level_key, {})
    override_level = override.get("level")
    if isinstance(override_level, dict):
        base = deep_merge(base, override_level)
    if "start_override" in override:
        base["start"] = override["start_override"]
    return base or None












def paragraph_numbering_snapshot(
    manifest: dict[str, Any], paragraph: dict[str, Any]
) -> dict[str, Any] | None:
    style_manifest = manifest.get("styles", {})
    num_id = paragraph.get("num_id")
    level = paragraph.get("num_level", 0)
    if num_id is None:
        style_id = paragraph_style_id(style_manifest, paragraph)
        style = effective_style(style_manifest, style_id) if style_id else None
        style_ppr = style.get("pPr", {}) if style else {}
        num_id = style_ppr.get("num_id")
        level = style_ppr.get("num_level", 0)
    if num_id in (None, 0):
        return None
    numbering = manifest.get("numbering", {})
    if str(num_id) not in numbering.get("numbers", {}):
        return {"broken_num_id": num_id, "level": level}
    level_record = effective_numbering_level(numbering, num_id, level) or {}
    return {
        "level": level,
        "format": level_record.get("format"),
        "text": level_record.get("text"),
        "start": level_record.get("start"),
        "pPr": level_record.get("pPr", {}),
        "rPr": level_record.get("rPr", {}),
    }


def style_ppr_layers(
    style_manifest: dict[str, Any],
    style_id: Any,
    source_prefix: str,
) -> list[tuple[str, dict[str, Any]]]:
    """Return a style's paragraph-property layers from child to ancestor."""
    records = style_manifest.get("styles", {})
    resolved = resolve_style_id(style_manifest, str(style_id)) if style_id else None
    layers: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    while resolved and resolved not in seen:
        seen.add(resolved)
        record = records.get(resolved, {})
        ppr = record.get("properties", {}).get("pPr", {})
        if ppr:
            layers.append(("%s:%s" % (source_prefix, resolved), ppr))
        based_on = record.get("based_on")
        resolved = resolve_style_id(style_manifest, str(based_on)) if based_on else None
    return layers


def table_look_flag(look: dict[str, Any], name: str, mask: int) -> bool:
    explicit = look.get(name)
    if explicit is not None:
        return str(explicit).strip().lower() not in {"0", "false", "off", "no"}
    raw_value = str(look.get("val") or "")
    try:
        return bool(int(raw_value, 16) & mask)
    except ValueError:
        return False


def applicable_table_style_conditions(
    style_manifest: dict[str, Any],
    table_context: dict[str, Any],
) -> list[str]:
    """Return active conditional table-style regions from most to least specific."""
    # The tblLook flags and band sizes may be defined on the table style (and
    # inherited through basedOn), not only on the table's direct tblPr. Merge the
    # style chain with the direct properties so an inherited tblLook or a directly
    # set band size both participate; direct properties win on conflict.
    merged_properties = effective_table_properties(
        style_manifest,
        {
            "style_id": table_context.get("style_id"),
            "properties": table_context.get("properties", {}),
        },
    )
    look = merged_properties.get("look", {})
    row_index = int(table_context.get("row_index") or 0)
    row_count = int(table_context.get("row_count") or 0)
    cell_index = int(table_context.get("cell_index") or 0)
    cell_count = int(table_context.get("cell_count") or 0)
    grid_start = int(table_context.get("grid_column_start") or cell_index)
    grid_end = int(table_context.get("grid_column_end") or cell_index)
    grid_count = int(table_context.get("grid_column_count") or cell_count)

    first_row_enabled = table_look_flag(look, "firstRow", 0x0020)
    last_row_enabled = table_look_flag(look, "lastRow", 0x0040)
    first_column_enabled = table_look_flag(look, "firstColumn", 0x0080)
    last_column_enabled = table_look_flag(look, "lastColumn", 0x0100)
    no_horizontal_banding = table_look_flag(look, "noHBand", 0x0200)
    no_vertical_banding = table_look_flag(look, "noVBand", 0x0400)

    # An explicit w:cnfStyle on the paragraph, cell or row force-enables a
    # conditional region regardless of tblLook (OOXML lets a row/cell opt into a
    # conditional format directly). OR those explicit flags in.
    cnf = table_context.get("cnf_style") or {}

    def region_active(look_enabled: bool, cnf_key: str) -> bool:
        return bool(look_enabled or cnf.get(cnf_key))

    on_first_row = region_active(first_row_enabled and row_index == 1, "firstRow")
    on_last_row = region_active(
        last_row_enabled and row_count > 0 and row_index == row_count, "lastRow"
    )
    on_first_column = region_active(
        first_column_enabled and grid_start == 1, "firstColumn"
    )
    on_last_column = region_active(
        last_column_enabled and grid_count > 0 and grid_end == grid_count, "lastColumn"
    )

    # Emit from highest to lowest precedence; the consumer stops at the first
    # layer that defines a property. Corners are most specific, then last/first
    # row, then last/first column (matching Word's conditional-format override
    # order where the later-applied, more specific region wins).
    conditions: list[str] = []
    if on_last_row and on_last_column:
        conditions.append("seCell")
    if on_last_row and on_first_column:
        conditions.append("swCell")
    if on_first_row and on_last_column:
        conditions.append("neCell")
    if on_first_row and on_first_column:
        conditions.append("nwCell")
    if on_last_row:
        conditions.append("lastRow")
    if on_first_row:
        conditions.append("firstRow")
    if on_last_column:
        conditions.append("lastCol")
    if on_first_column:
        conditions.append("firstCol")

    row_band_size = max(int(merged_properties.get("row_band_size") or 1), 1)
    column_band_size = max(int(merged_properties.get("column_band_size") or 1), 1)

    # Conditions are returned from highest to lowest precedence because consumers
    # stop at the first layer defining a property. Word applies horizontal bands
    # before vertical bands, so vertical bands must appear first in this reversed
    # lookup order.
    if not no_vertical_banding and grid_start:
        band_start = 2 if first_column_enabled else 1
        band_end = grid_count - 1 if last_column_enabled else grid_count
        if band_start <= grid_start <= band_end:
            band = ((grid_start - band_start) // column_band_size) % 2
            conditions.append("band1Vert" if band == 0 else "band2Vert")
    if not no_horizontal_banding and row_index:
        band_start = 2 if first_row_enabled else 1
        band_end = row_count - 1 if last_row_enabled else row_count
        if band_start <= row_index <= band_end:
            band = ((row_index - band_start) // row_band_size) % 2
            conditions.append("band1Horz" if band == 0 else "band2Horz")

    conditions.append("wholeTable")
    return conditions


def table_style_ppr_layers(
    style_manifest: dict[str, Any], table_context: dict[str, Any],
    property_group: str = "pPr",
) -> list[tuple[str, dict[str, Any]]]:
    table_style_id = table_context.get("style_id") or style_manifest.get(
        "default_style_ids", {}
    ).get("table")
    records = style_manifest.get("styles", {})
    resolved = (
        resolve_style_id(style_manifest, str(table_style_id)) if table_style_id else None
    )
    style_chain: list[str] = []
    seen: set[str] = set()
    while resolved and resolved not in seen:
        seen.add(resolved)
        style_chain.append(resolved)
        based_on = records.get(resolved, {}).get("based_on")
        resolved = resolve_style_id(style_manifest, str(based_on)) if based_on else None

    layers: list[tuple[str, dict[str, Any]]] = []
    for condition in applicable_table_style_conditions(style_manifest, table_context):
        for current in style_chain:
            ppr = (
                records.get(current, {})
                .get("conditional_table_properties", {})
                .get(condition, {})
                .get(property_group, {})
            )
            if ppr:
                layers.append(
                    ("table_style:%s:%s" % (current, condition), ppr)
                )
    for current in style_chain:
        ppr = records.get(current, {}).get("properties", {}).get(property_group, {})
        if ppr:
            layers.append(("table_style:%s" % current, ppr))
    return layers


def effective_first_line_indent(
    manifest: dict[str, Any], paragraph: dict[str, Any]
) -> dict[str, Any]:
    """Resolve the highest-priority first-line or hanging indentation control."""
    style_manifest = manifest.get("styles", {})
    layers: list[tuple[str, dict[str, Any]]] = [
        ("direct", paragraph.get("pPr", {}))
    ]
    numbering = paragraph_numbering_snapshot(manifest, paragraph)
    if numbering and numbering.get("pPr"):
        layers.append(("numbering", numbering["pPr"]))
    paragraph_style = paragraph_style_id(style_manifest, paragraph)
    layers.extend(
        style_ppr_layers(style_manifest, paragraph_style, "paragraph_style")
    )
    table_context = paragraph.get("table_context") or {}
    if table_context:
        layers.extend(table_style_ppr_layers(style_manifest, table_context))
    defaults = style_manifest.get("defaults", {}).get("pPr", {})
    if defaults:
        layers.append(("doc_defaults", defaults))

    for source, ppr in layers:
        present = {
            key: ppr[key]
            for key in (
                "first_line_dxa",
                "first_line_chars",
                "hanging_dxa",
                "hanging_chars",
            )
            if key in ppr
        }
        if not present:
            continue
        if "hanging_chars" in present or "hanging_dxa" in present:
            return {
                "first_line_dxa": 0,
                "first_line_chars": 0,
                "source": source,
                "control": "hanging",
                "source_pPr": ppr,
            }
        if "first_line_chars" in present:
            return {
                "first_line_dxa": 0,
                "first_line_chars": int(present["first_line_chars"]),
                "source": source,
                "control": "first_line_chars",
                "source_pPr": ppr,
            }
        return {
            "first_line_dxa": int(present.get("first_line_dxa") or 0),
            "first_line_chars": 0,
            "source": source,
            "control": "first_line_dxa",
            "source_pPr": ppr,
        }
    return {
        "first_line_dxa": 0,
        "first_line_chars": 0,
        "source": "implicit_default",
        "control": "none",
        "source_pPr": {},
    }


def effective_paragraph_alignment(
    manifest: dict[str, Any], paragraph: dict[str, Any]
) -> str:
    """Resolve the effective horizontal alignment (w:jc), defaulting to left.

    Walks the same priority order as first-line indent resolution: direct format
    -> numbering -> paragraph style chain -> table style -> docDefaults. OOXML
    values map roughly as: left/start -> left, center -> center, right/end ->
    right, both/distribute -> justified. A missing value means the OOXML default,
    which is left.
    """
    style_manifest = manifest.get("styles", {})
    layers: list[dict[str, Any]] = [paragraph.get("pPr", {})]
    numbering = paragraph_numbering_snapshot(manifest, paragraph)
    if numbering and numbering.get("pPr"):
        layers.append(numbering["pPr"])
    paragraph_style = paragraph_style_id(style_manifest, paragraph)
    layers.extend(
        ppr for _, ppr in style_ppr_layers(style_manifest, paragraph_style, "paragraph_style")
    )
    table_context = paragraph.get("table_context") or {}
    if table_context:
        layers.extend(
            ppr for _, ppr in table_style_ppr_layers(style_manifest, table_context)
        )
    defaults = style_manifest.get("defaults", {}).get("pPr", {})
    if defaults:
        layers.append(defaults)
    for ppr in layers:
        alignment = ppr.get("alignment")
        if alignment:
            normalized = {
                "start": "left",
                "left": "left",
                "center": "center",
                "right": "right",
                "end": "right",
                "both": "justified",
                "distribute": "justified",
            }.get(str(alignment), str(alignment))
            return normalized
    return "left"


# Only left-aligned or justified table text shows a visible first-line indent.
# For centered or right-aligned cells the indent produces no meaningful offset,
# so flagging it would be a false positive (e.g. centered checkbox rows).
INDENT_SENSITIVE_ALIGNMENTS = {"left", "justified"}

# A "first-line indent" is a running-body-paragraph concept (indent the first line
# of prose by ~2 characters). Table cells, however, overwhelmingly hold short
# labels, headers, fill-in blanks and form rows that use the first-line indent as
# a *layout* nudge, not as prose formatting. Flagging those is a false positive,
# so we only treat a cell paragraph as running body text (and therefore subject to
# the rule) when its non-whitespace length reaches this threshold.
TABLE_INDENT_BODY_MIN_CHARS = 20

# Running prose also carries sentence punctuation (句读). A cell paragraph with no
# punctuation at all is almost always a label / header / value / URL, not body
# text, so it is exempt regardless of length. ASCII ".", "/", ":" and ";" are
# intentionally excluded so that URLs, file paths, times, ratios and bare decimals
# do not count as punctuation; Chinese full-width 。：；、 remain strong prose marks.
TABLE_BODY_PUNCTUATION = set(
    "，。、；：？！“”‘’（）《》【】…—〜·「」『』〖〗〈〉"  # CJK punctuation
    ",?!()"  # ASCII sentence punctuation (excludes '.', '/', ':' and ';')
)

# Form / checkbox / tick glyphs. A cell paragraph containing any of these is a
# form row (选项、勾选位), not running body text, and is exempt regardless of length.
# NOTE: U+221A (√) is intentionally NOT included. It is the mathematical radical
# sign and appears in genuine prose (e.g. 计算√2); treating it as a checkbox glyph
# wrongly exempts whole prose paragraphs from the indent rule. Real checkbox rows
# still qualify via the checkmark ticks below or the short-label / no-punctuation
# gates.
TABLE_FORM_GLYPHS = set(
    "\u2610\u2611\u2612"  # ☐ ☑ ☒
    "\u25a1\u25a0\u25fb\u25fc\u25fd\u25fe\u25ab\u25aa"  # □ ■ ◻ ◼ ◽ ◾ ▫ ▪
    "\u2b1c\u2b1b"  # ⬜ ⬛
    "\u2713\u2714\u2717\u2718"  # ✓ ✔ ✗ ✘
    "\u25c7\u25c6\u25cb\u25cf\u25ef\u25c8"  # ◇ ◆ ○ ● ◯ ◈
    "\u2b50\u2606\u2605"  # ⭐ ☆ ★
)


def _table_has_body_punctuation(text: str) -> bool:
    """Whether the text carries any sentence punctuation (marks running prose)."""
    return any(ch in TABLE_BODY_PUNCTUATION for ch in str(text or ""))


def _table_indent_content_length(text: str) -> int:
    """Non-whitespace character count used to tell prose from short labels."""
    return len("".join(str(text or "").split()))


def _is_single_cell_table(table_context: dict[str, Any] | None) -> bool:
    """True when the paragraph's nearest table is a 1x1 (single-cell) table.

    A one-row/one-column table is almost never a data table; it is a shaded
    "callout"/emphasis box that wraps a body paragraph, so the "table cells do not
    use first-line indent" rule does not apply. ``row_count`` and
    ``grid_column_count`` come from the nearest ancestor table, so nested tables
    are handled correctly. ``cell_count`` (cells in the paragraph's own row) is
    used as a fallback when the grid column count is unavailable.
    """
    if not table_context:
        return False
    row_count = table_context.get("row_count")
    if row_count != 1:
        return False
    grid_columns = table_context.get("grid_column_count")
    if grid_columns is not None:
        return grid_columns == 1
    return table_context.get("cell_count") == 1


def table_paragraph_first_line_indent_findings(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    summary = {
        "performed": True,
        "definition": (
            "left-aligned or justified running body text (non-whitespace length "
            ">= %d, carries sentence punctuation, and has no form/checkbox glyph) "
            "inside a *regular data table* has zero effective first-line indent; a "
            "regular data table is at least 2 rows x 2 columns, every row has the "
            "same cell count, and there is no horizontal gridSpan or vertical "
            "vMerge. Tables smaller than 2x2 (single-cell callout boxes, single-row "
            "headers, single-column lists) and ragged/merged form-layout tables are "
            "exempt, as are centered/right-aligned cells, short labels/headers/"
            "fill-in blanks, punctuation-free labels/URLs and form rows, because a "
            "first-line indent there is a layout nudge, not prose formatting"
            % TABLE_INDENT_BODY_MIN_CHARS
        ),
        "body_min_chars": TABLE_INDENT_BODY_MIN_CHARS,
        "paragraphs_examined": 0,
        "empty_paragraphs_skipped": 0,
        "textbox_paragraphs_skipped": 0,
        "single_cell_table_skipped": 0,
        "irregular_table_skipped": 0,
        "centered_or_right_aligned_skipped": 0,
        "form_row_skipped": 0,
        "short_label_skipped": 0,
        "no_punctuation_skipped": 0,
        "direct_finding_count": 0,
        "inherited_finding_count": 0,
        "finding_count": 0,
    }
    for paragraph in manifest.get("paragraphs", []):
        if not paragraph_is_deliverable_content(paragraph) or not paragraph.get("in_table"):
            continue
        if paragraph.get("in_textbox"):
            summary["textbox_paragraphs_skipped"] += 1
            continue
        text = str(paragraph.get("text") or "")
        if not text.strip():
            summary["empty_paragraphs_skipped"] += 1
            continue
        summary["paragraphs_examined"] += 1
        table_context = paragraph.get("table_context") or {}
        if _is_single_cell_table(table_context):
            # 1x1 tables are shaded callout/emphasis boxes wrapping body text,
            # not data tables, so the no-first-line-indent rule does not apply.
            summary["single_cell_table_skipped"] += 1
            continue
        if not table_context.get("is_regular_table", True):
            # Form-layout tables (ragged rows / merged cells) use cells to arrange
            # a form, not to hold tabular data; the rule targets regular data
            # tables only, so exempt the whole irregular/form table.
            summary["irregular_table_skipped"] += 1
            continue
        alignment = effective_paragraph_alignment(manifest, paragraph)
        if alignment not in INDENT_SENSITIVE_ALIGNMENTS:
            # Centered / right-aligned cells: a first-line indent is not visible.
            summary["centered_or_right_aligned_skipped"] += 1
            continue
        if any(glyph in TABLE_FORM_GLYPHS for glyph in text):
            # Checkbox / option rows use the indent to lay out choices, not prose.
            summary["form_row_skipped"] += 1
            continue
        if _table_indent_content_length(text) < TABLE_INDENT_BODY_MIN_CHARS:
            # Short labels, headers and fill-in blanks are not running body text.
            summary["short_label_skipped"] += 1
            continue
        if not _table_has_body_punctuation(text):
            # Running prose carries sentence punctuation; text without any is a
            # label / header / value / URL, not body text.
            summary["no_punctuation_skipped"] += 1
            continue
        effective = effective_first_line_indent(manifest, paragraph)
        first_line_dxa = int(effective.get("first_line_dxa") or 0)
        first_line_chars = int(effective.get("first_line_chars") or 0)
        if first_line_dxa == 0 and first_line_chars == 0:
            continue
        source = str(effective.get("source") or "unknown")
        source_kind = "direct" if source == "direct" else "inherited"
        summary["%s_finding_count" % source_kind] += 1
        table_context = paragraph.get("table_context") or {}
        findings.append(
            issue(
                "error",
                "E_TABLE_PARAGRAPH_FIRST_LINE_INDENT",
                str(paragraph.get("location") or "unknown"),
                "table paragraph has a non-zero effective first-line indent",
                expected={"first_line_dxa": 0, "first_line_chars": 0},
                actual={
                    "first_line_dxa": first_line_dxa,
                    "first_line_chars": first_line_chars,
                    "source": source,
                    "control": effective.get("control"),
                    "alignment": alignment,
                },
                evidence={
                    "text": paragraph.get("text"),
                    "paragraph_xpath": paragraph.get("xpath"),
                    "paragraph_style_id": paragraph.get("style_id"),
                    "resolved_paragraph_style_id": paragraph_style_id(
                        manifest.get("styles", {}), paragraph
                    ),
                    "direct_pPr": paragraph.get("pPr", {}),
                    "source_pPr": effective.get("source_pPr", {}),
                    "table_index": table_context.get("table_index"),
                    "row_index": table_context.get("row_index"),
                    "cell_index": table_context.get("cell_index"),
                    "table_style_id": table_context.get("style_id"),
                },
            )
        )
    summary["finding_count"] = len(findings)
    return findings, summary


def font_family_identity(name: str) -> str:
    """Case/width-folded family identity for exact-name comparisons."""
    return unicodedata.normalize("NFC", str(name).strip()).casefold()


def script_for_language(language: str | None) -> str | None:
    """Map a themeFontLang value to the ISO 15924 script it selects.

    Ported from the WordprocessingML theme-language selector: only the language
    tag drives which supplemental theme font a theme reference resolves to. A
    bare ``zh`` deliberately does not choose Hans/Hant.
    """
    if not language:
        return None
    parts = language.replace("_", "-").lower().split("-")
    explicit = {
        "hans": "Hans", "hant": "Hant", "latn": "Latn", "cyrl": "Cyrl",
        "arab": "Arab", "deva": "Deva", "mong": "Mong",
    }
    for part in parts[1:]:
        if part in explicit:
            return explicit[part]
    if parts[0] == "zh":
        if any(p in ("tw", "hk", "mo") for p in parts[1:]):
            return "Hant"
        if any(p in ("cn", "sg") for p in parts[1:]):
            return "Hans"
        return None
    scripts = {
        "ja": "Jpan", "ko": "Hang", "ar": "Arab", "fa": "Arab", "ur": "Arab",
        "he": "Hebr", "yi": "Hebr", "hi": "Deva", "mr": "Deva", "ne": "Deva",
        "bn": "Beng", "pa": "Guru", "gu": "Gujr", "or": "Orya", "ta": "Taml",
        "te": "Telu", "kn": "Knda", "ml": "Mlym", "si": "Sinh", "th": "Thai",
        "lo": "Laoo", "km": "Khmr", "my": "Mymr", "bo": "Tibt", "el": "Grek",
        "ru": "Cyrl", "uk": "Cyrl", "bg": "Cyrl", "mk": "Cyrl", "hy": "Armn",
        "ka": "Geor", "am": "Ethi", "iu": "Cans", "chr": "Cher",
    }
    return scripts.get(parts[0])


def resolve_eastasia_theme_font(
    theme_fonts: dict[str, Any], token: Any
) -> dict[str, Any]:
    """Resolve a majorEastAsia/minorEastAsia theme token to a concrete family.

    Mirrors Word's theme resolution: themeFontLang(eastAsia) picks an ISO 15924
    script; a matching supplemental ``<a:font script=...>`` wins over the plain
    ``<a:ea>`` typeface. The returned ``script`` records which script drove the
    supplemental choice so the caller can detect a Chinese/Japanese mismatch.
    """
    match = re.fullmatch(r"(major|minor)(EastAsia)", str(token))
    if not match:
        return {"state": "unresolved", "reason": "invalid_theme_token", "token": token}
    scheme = (theme_fonts.get("schemes", {}) or {}).get(match.group(1))
    if not scheme:
        return {"state": "unresolved", "reason": "missing_theme_collection", "token": token}
    language = (theme_fonts.get("languages", {}) or {}).get("language_east_asia")
    script = script_for_language(language)
    if language and not script:
        return {
            "state": "unresolved", "reason": "unsupported_theme_language",
            "token": token, "language": language,
        }
    if script:
        face = (scheme.get("supplemental", {}) or {}).get(script)
        if face and face.strip():
            return {
                "state": "resolved", "family": face.strip(), "mapping": "supplemental",
                "script": script, "language": language, "token": token,
            }
    primary = scheme.get("east_asia")
    if primary and primary.strip():
        return {
            "state": "resolved", "family": primary.strip(), "mapping": "ea",
            "script": script, "language": language, "token": token,
        }
    return {
        "state": "unresolved", "reason": "empty_theme_font",
        "token": token, "language": language, "script": script,
    }


def _style_rpr_chain(
    style_manifest: dict[str, Any], style_id: Any
) -> list[tuple[dict[str, Any], str]]:
    """Own rPr of each style along the basedOn chain, nearest ancestor first."""
    records = style_manifest.get("styles", {})
    resolved = resolve_style_id(style_manifest, str(style_id)) if style_id else None
    chain: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = set()
    while resolved and resolved not in seen:
        seen.add(resolved)
        record = records.get(resolved, {})
        chain.append(
            (record.get("properties", {}).get("rPr", {}) or {}, "style:%s" % resolved)
        )
        based_on = record.get("based_on")
        resolved = resolve_style_id(style_manifest, str(based_on)) if based_on else None
    return chain


def resolve_run_font(
    manifest: dict[str, Any], paragraph: dict[str, Any], run: dict[str, Any], slot: str
) -> dict[str, Any]:
    """The first defining layer wins; theme beats explicit at that same layer."""
    theme_fonts = manifest.get("theme_fonts", {})
    for rpr, source in run_property_layers(manifest, paragraph, run):
        theme = rpr.get("font_%s_theme" % slot)
        explicit = rpr.get("font_%s" % slot)
        if theme is not None:
            if slot == "east_asia":
                resolution = resolve_eastasia_theme_font(theme_fonts, theme)
            else:
                matched = re.fullmatch(r"(major|minor)(Ascii|HAnsi|Bidi)", str(theme))
                family = theme_fonts.get("schemes", {}).get(matched[1], {}).get(
                    "complex_script" if matched[2] == "Bidi" else "latin"
                ) if matched else None
                resolution = {"state": "resolved", "family": family, "token": theme} if family else {
                    "state": "unresolved", "reason": "unresolved_theme_font", "token": theme,
                }
            resolution.update(
                {"source": source, "selector": "theme", "shadowed_explicit": explicit}
            )
            return resolution
        if explicit is not None and explicit.strip():
            return {
                "state": "resolved", "family": explicit.strip(),
                "selector": "explicit", "source": source,
            }
    return {"state": "unresolved", "reason": "application_default", "source": "application_default"}


NON_CHINESE_CJK_SCRIPTS = {"Jpan": "日文", "Hang": "韩文"}


def font_findings(
    manifest: dict[str, Any],
    *,
    report_cjk_mismatch: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Check effective fonts and same-layer explicit/theme contradictions.

    ``report_cjk_mismatch`` gates only E_FONT_CJK_SCRIPT_MISMATCH. Source-compare
    mode must call this detector with the same setting for source and target so
    unchanged theme/font findings can be removed by baseline subtraction.
    """
    theme_fonts = manifest.get("theme_fonts", {})
    schemes = theme_fonts.get("schemes", {}) or {}

    def chinese_theme_alternatives() -> dict[str, str]:
        # Chinese faces the theme already defines, offered as the concrete fix.
        alternatives: dict[str, str] = {}
        for family in ("minor", "major"):
            supplemental = (schemes.get(family, {}) or {}).get("supplemental", {}) or {}
            for script in ("Hans", "Hant"):
                face = supplemental.get(script)
                if face and face.strip():
                    alternatives.setdefault(script, face.strip())
        return alternatives

    aggregated: dict[tuple, dict[str, Any]] = {}
    text_run_count = 0
    han_run_count = 0
    resolved_run_count = 0
    shadowed_run_count = 0
    cjk_mismatch_run_count = 0

    for paragraph in manifest.get("paragraphs", []):
        for run in paragraph.get("runs", []):
            text = str(run.get("text") or "")
            if not text.strip():
                continue
            text_run_count += 1
            contains_han = any(is_han_character(character) for character in text)
            if contains_han:
                han_run_count += 1
            properties = effective_run_properties(manifest, paragraph, run)
            run_resolved = False
            for slot in sorted(used_run_font_slots(text, properties)):
                resolution = resolve_run_font(manifest, paragraph, run, slot)
                if resolution.get("state") != "resolved":
                    continue
                run_resolved = True
                family = str(resolution["family"])
                identity = font_family_identity(family)
                source = resolution.get("source") or "unknown"
                explicit = resolution.get("shadowed_explicit")
                explicit_identity = (
                    font_family_identity(str(explicit))
                    if explicit is not None and str(explicit).strip()
                    else None
                )
                if explicit_identity and explicit_identity != identity:
                    shadowed_run_count += 1
                    key = (
                        "E_FONT_EXPLICIT_VALUE_SHADOWED",
                        source,
                        slot,
                        explicit_identity,
                        identity,
                        resolution.get("token"),
                    )
                    group = aggregated.get(key)
                    if group is None:
                        aggregated[key] = {
                            "code": "E_FONT_EXPLICIT_VALUE_SHADOWED",
                            "source": source,
                            "slot": slot,
                            "explicit_font": str(explicit).strip(),
                            "family": family,
                            "theme_token": resolution.get("token"),
                            "occurrences": 1,
                            "sample_location": paragraph.get("location"),
                            "sample_text": text[:80],
                        }
                    else:
                        group["occurrences"] += 1
                if not contains_han or slot not in {"east_asia", "complex_script"}:
                    continue
                replacement = next(
                    (
                        value
                        for key, value in FORBIDDEN_LEGACY_FONTS.items()
                        if font_family_identity(key) == identity
                    ),
                    None,
                )
                if replacement is not None:
                    key = ("E_FORBIDDEN_FONT_FAMILY", source, slot, identity)
                    group = aggregated.get(key)
                    if group is None:
                        aggregated[key] = {
                            "code": "E_FORBIDDEN_FONT_FAMILY",
                            "source": source,
                            "slot": slot,
                            "family": family,
                            "replacement": replacement,
                            "occurrences": 1,
                            "sample_location": paragraph.get("location"),
                            "sample_text": text[:80],
                        }
                    else:
                        group["occurrences"] += 1
                    continue
                # Chinese text painted with a Japanese/Korean-script theme font,
                # typically because themeFontLang(eastAsia) is ja-JP/ko-KR. This
                # is independent of the shadow check: it fires when the theme
                # itself selects the wrong-language face. A same-layer explicit
                # value is already reported as E_FONT_EXPLICIT_VALUE_SHADOWED, so
                # skip CJK there to avoid double-reporting one run.
                script = resolution.get("script")
                if (
                    report_cjk_mismatch
                    and slot == "east_asia"
                    and resolution.get("selector") == "theme"
                    and script in NON_CHINESE_CJK_SCRIPTS
                    and explicit_identity is None
                ):
                    cjk_mismatch_run_count += 1
                    key = ("E_FONT_CJK_SCRIPT_MISMATCH", source, identity, script)
                    group = aggregated.get(key)
                    if group is None:
                        aggregated[key] = {
                            "code": "E_FONT_CJK_SCRIPT_MISMATCH",
                            "source": source,
                            "slot": slot,
                            "family": family,
                            "script": script,
                            "language": resolution.get("language"),
                            "token": resolution.get("token"),
                            "mapping": resolution.get("mapping"),
                            "selector": resolution.get("selector"),
                            "occurrences": 1,
                            "sample_location": paragraph.get("location"),
                            "sample_text": text[:80],
                        }
                    else:
                        group["occurrences"] += 1
            if run_resolved:
                resolved_run_count += 1

    findings: list[dict[str, Any]] = []
    for group in aggregated.values():
        if group["code"] == "E_FORBIDDEN_FONT_FAMILY":
            findings.append(issue(
                "error", "E_FORBIDDEN_FONT_FAMILY", str(group["source"]),
                "resolved font family is a legacy name modern Word cannot render",
                actual=group["family"], expected=group["replacement"],
                evidence=dict(group),
                blocking=True,
            ))
            continue
        if group["code"] == "E_FONT_CJK_SCRIPT_MISMATCH":
            alternatives = chinese_theme_alternatives()
            script_label = NON_CHINESE_CJK_SCRIPTS.get(group["script"], group["script"])
            hint = (
                "中文文本经 themeFontLang(eastAsia=%s) 被主题映射为%s脚本字体“%s”。"
                "请在命中的样式或 run 上显式设置中文 eastAsia 字体，"
                "或将 themeFontLang 的 eastAsia 改为中文(如 zh-CN/zh-TW)。"
                % (group.get("language"), script_label, group["family"])
            )
            if alternatives:
                hint += " 该主题已内置中文字体：%s。" % "，".join(
                    "%s→%s" % (script, face) for script, face in alternatives.items()
                )
            findings.append(issue(
                "error", "E_FONT_CJK_SCRIPT_MISMATCH", str(group["source"]),
                "Chinese text resolves to a Japanese/Korean-script font under the theme",
                actual=group["family"],
                expected={"chinese_theme_fonts": alternatives} if alternatives else None,
                repair_hint=hint,
                evidence=dict(group),
                blocking=True,
            ))
            continue
        findings.append(issue(
            "error", "E_FONT_EXPLICIT_VALUE_SHADOWED", str(group["source"]),
            "explicit font is shadowed by a different theme-resolved font "
            "on the same effective w:rFonts layer",
            expected={"explicit_font": group["explicit_font"]},
            actual={"effective_font": group["family"]},
            evidence=dict(group),
            blocking=True,
        ))

    check = {
        "performed": True,
        "text_run_count": text_run_count,
        "han_run_count": han_run_count,
        "resolved_run_count": resolved_run_count,
        "shadowed_run_count": shadowed_run_count,
        "cjk_mismatch_run_count": cjk_mismatch_run_count,
        "cjk_mismatch_checked": report_cjk_mismatch,
        "font_error_count": len(findings),
    }
    return findings, check


def document_policy_findings(
    manifest: dict[str, Any],
    word_count_minimum: int | None,
    word_count_maximum: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run every non-package detector identically for source and target.

    Keeping these calls behind one function prevents a future rule from being
    added only to the target side and silently bypassing --source baseline
    subtraction, which was the cause of the legacy-font false positive.
    """
    quote_findings, quote_check = chinese_ascii_double_quote_findings(manifest)
    table_indent_findings, table_indent_check = (
        table_paragraph_first_line_indent_findings(manifest)
    )
    font_finding_list, font_audit_check = font_findings(
        manifest,
        report_cjk_mismatch=True,
    )
    word_findings, word_count_check = word_count_findings(
        manifest,
        word_count_minimum,
        word_count_maximum,
    )
    return (
        quote_findings
        + table_indent_findings
        + font_finding_list
        + word_findings,
        {
            "chinese_ascii_double_quotes": quote_check,
            "table_paragraph_first_line_indent": table_indent_check,
            "font_audit": font_audit_check,
            "word_count": word_count_check,
        },
    )










ADDED_STYLE_MIN_SOURCE_PEERS = {"body": 3, "heading": 2}
ADDED_STYLE_PPR_KEYS = (
    "alignment",
    "space_before_twips",
    "space_after_twips",
    "line_twips",
    "line_rule",
    "left_indent_dxa",
    "right_indent_dxa",
    "first_line_dxa",
    "hanging_dxa",
    "first_line_chars",
    "hanging_chars",
    "keep_next",
    "keep_lines",
    "page_break_before",
    "widow_control",
    "text_alignment",
)
ADDED_STYLE_RPR_KEYS = (
    "size_half_points",
    "color",
    "highlight",
    "character_spacing_twips",
)
ADDED_STYLE_RPR_BOOLEAN_KEYS = ("bold", "italic")
ADDED_STYLE_PPR_BOOLEAN_KEYS = (
    "keep_next",
    "keep_lines",
    "page_break_before",
    "widow_control",
)
NON_BODY_PREFIX_RE = re.compile(
    r"^\s*(?:注|备注|说明|提示|示例|图|表)(?:\s*\d+(?:[.-]\d+)*)?\s*[:：]"
)


def comparable_body_paragraphs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return visible top-level body paragraphs eligible for insertion analysis."""
    return [
        paragraph
        for paragraph in manifest.get("paragraphs", [])
        if paragraph.get("part") == "word/document.xml"
        and not paragraph.get("in_table")
        and not paragraph.get("in_textbox")
        and paragraph.get("revision_text_state") != "deleted"
        and not paragraph.get("revision_moved")
        and bool(str(paragraph.get("text") or "").strip())
    ]


def confident_added_paragraph_indexes(
    source: list[dict[str, Any]], target: list[dict[str, Any]]
) -> set[int]:
    """Find only insertions proved by revision markup or adjacent source anchors."""
    source_ids: dict[str, list[int]] = {}
    target_ids: dict[str, list[int]] = {}
    source_text: dict[str, list[int]] = {}
    target_text: dict[str, list[int]] = {}
    for index, paragraph in enumerate(source):
        identifier = str(paragraph.get("para_id") or "")
        if identifier:
            source_ids.setdefault(identifier, []).append(index)
        text_hash = str(paragraph.get("text_sha256") or "")
        if text_hash:
            source_text.setdefault(text_hash, []).append(index)
    for index, paragraph in enumerate(target):
        identifier = str(paragraph.get("para_id") or "")
        if identifier:
            target_ids.setdefault(identifier, []).append(index)
        text_hash = str(paragraph.get("text_sha256") or "")
        if text_hash:
            target_text.setdefault(text_hash, []).append(index)

    anchors: dict[int, int] = {}
    for identifier in set(source_ids) & set(target_ids):
        if len(source_ids[identifier]) == len(target_ids[identifier]) == 1:
            anchors[target_ids[identifier][0]] = source_ids[identifier][0]
    for text_hash in set(source_text) & set(target_text):
        if len(source_text[text_hash]) == len(target_text[text_hash]) == 1:
            target_index = target_text[text_hash][0]
            source_index = source_text[text_hash][0]
            if target_index not in anchors and source_index not in anchors.values():
                anchors[target_index] = source_index

    candidates = {
        index
        for index, paragraph in enumerate(target)
        if index not in anchors
        and not paragraph.get("revision_replacement")
        and not paragraph.get("revision_moved")
        and paragraph.get("text_sha256") not in source_text
        and paragraph.get("para_id") not in source_ids
    }
    added = {
        index for index in candidates
        if target[index].get("paragraph_mark_inserted")
        and target[index].get("revision_text_state") == "inserted"
    }
    # Untracked gaps qualify only if every source paragraph is retained once,
    # in order. Missing or duplicated identities can also represent replacements.
    ordered = sorted(anchors.items())
    if [source_index for _, source_index in ordered] != list(range(len(source))):
        return added
    if ordered:
        first_target, first_source = ordered[0]
        if first_source == 0:
            added.update(candidates.intersection(range(0, first_target)))
        for (left_target, left_source), (right_target, right_source) in zip(
            ordered, ordered[1:]
        ):
            if right_source == left_source + 1:
                added.update(candidates.intersection(range(left_target + 1, right_target)))
        last_target, last_source = ordered[-1]
        if last_source == len(source) - 1:
            added.update(candidates.intersection(range(last_target + 1, len(target))))
    return added


def paragraph_style_role(
    manifest: dict[str, Any], paragraph: dict[str, Any]
) -> str | None:
    """Classify only structurally explicit headings and unambiguous prose."""
    style_manifest = manifest.get("styles", {})
    style_id = paragraph_style_id(style_manifest, paragraph)
    style = effective_style(style_manifest, style_id) if style_id else None
    effective_ppr = deep_merge(
        style.get("pPr", {}) if style else {}, paragraph.get("pPr", {})
    )
    outline_level = effective_ppr.get("outline_level")
    if isinstance(outline_level, int) and 0 <= outline_level <= 8:
        return "heading:%d" % outline_level
    text = str(paragraph.get("text") or "")
    compact_length = len("".join(text.split()))
    if (
        compact_length >= TABLE_INDENT_BODY_MIN_CHARS
        and _table_has_body_punctuation(text)
        and effective_ppr.get("outline_level") is None
        and not NON_BODY_PREFIX_RE.match(text)
    ):
        return "body"
    return None


def run_property_layers(
    manifest: dict[str, Any],
    paragraph: dict[str, Any],
    run: dict[str, Any],
) -> list[tuple[dict[str, Any], str]]:
    style_manifest = manifest.get("styles", {})
    run_rpr = run.get("rPr", {}) or {}
    layers: list[tuple[dict[str, Any], str]] = [(run_rpr, "run")]
    character_style = run_rpr.get("character_style_id") or style_manifest.get("default_style_ids", {}).get("character")
    if character_style:
        layers += _style_rpr_chain(style_manifest, character_style)
    paragraph_style = paragraph_style_id(style_manifest, paragraph)
    if paragraph_style:
        layers += _style_rpr_chain(style_manifest, paragraph_style)
    if paragraph.get("table_context"):
        layers.extend(
            (properties, source)
            for source, properties in table_style_ppr_layers(
                style_manifest, paragraph["table_context"], "rPr"
            )
        )
    layers.append(
        (style_manifest.get("defaults", {}).get("rPr", {}) or {}, "docDefaults")
    )
    return layers


def effective_run_properties(
    manifest: dict[str, Any],
    paragraph: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for layer, source in reversed(run_property_layers(manifest, paragraph, run)):
        toggles = {
            key: not bool(properties.get(key, False))
            for key in STYLE_TOGGLE_PROPERTIES
            if layer.get(key) is True
        } if source.startswith(("style:", "table_style:")) else {}
        unchanged = {
            key: properties.get(key, False)
            for key in STYLE_TOGGLE_PROPERTIES
            if layer.get(key) is False
        } if source.startswith(("style:", "table_style:")) else {}
        properties = deep_merge(properties, layer)
        properties.update(unchanged)
        properties.update(toggles)
    return properties


STYLE_TOGGLE_PROPERTIES = {
    "bold", "bold_complex_script", "italic", "italic_complex_script",
    "caps", "small_caps", "strike", "hidden",
}


def resolve_run_font_slot(
    manifest: dict[str, Any],
    paragraph: dict[str, Any],
    run: dict[str, Any],
    slot: str,
) -> str | None:
    resolution = resolve_run_font(manifest, paragraph, run, slot)
    return font_family_identity(resolution["family"]) if resolution.get("state") == "resolved" else None


def used_run_font_slots(text: str, properties: dict[str, Any]) -> set[str]:
    """Only assert character slots whose selection is unambiguous here."""
    if properties.get("complex_script") or properties.get("right_to_left"):
        return {"complex_script"}
    slots: set[str] = set()
    for character in text:
        if character.isspace():
            continue
        point = ord(character)
        if point < 128:
            slots.add("ascii")
        elif is_han_character(character) or 0x3000 <= point <= 0x31FF or 0xAC00 <= point <= 0xD7AF:
            slots.add("east_asia")
        elif 0x0100 <= point <= 0x02AF and properties.get("font_hint") != "eastAsia":
            slots.add("hansi")
    return slots


def comparable_style_signature(
    manifest: dict[str, Any], paragraph: dict[str, Any]
) -> dict[str, Any] | None:
    runs = [
        run
        for run in paragraph.get("runs", [])
        if bool(str(run.get("text") or "").strip())
        and run.get("word_count_visible", True)
        and not effective_run_properties(manifest, paragraph, run).get("hidden", False)
    ]
    if not runs:
        return None
    style_manifest = manifest.get("styles", {})
    style_id = paragraph_style_id(style_manifest, paragraph)
    style = effective_style(style_manifest, style_id) if style_id else None
    effective_ppr = deep_merge(
        style.get("pPr", {}) if style else {}, paragraph.get("pPr", {})
    )
    run_signatures = []
    font_values: dict[str, set[str]] = {}
    for run in runs:
        effective_rpr = effective_run_properties(manifest, paragraph, run)
        text = str(run.get("text") or "")
        slots = used_run_font_slots(text, effective_rpr)
        if slots == {"complex_script"}:
            for regular, complex_key in (
                ("size_half_points", "size_complex_script_half_points"),
                ("bold", "bold_complex_script"),
                ("italic", "italic_complex_script"),
            ):
                effective_rpr[regular] = effective_rpr.get(complex_key)
        signature: dict[str, Any] = {
            key: effective_rpr.get(key)
            for key in ADDED_STYLE_RPR_KEYS
            if effective_rpr.get(key) is not None
        }
        signature.update(
            {
                key: bool(effective_rpr.get(key, False))
                for key in ADDED_STYLE_RPR_BOOLEAN_KEYS
            }
        )
        signature["underline"] = effective_rpr.get("underline") or "none"
        for slot in slots:
            family = resolve_run_font_slot(manifest, paragraph, run, slot)
            if family:
                font_values.setdefault(slot, set()).add(family)
        run_signatures.append(signature)
    if any(signature != run_signatures[0] for signature in run_signatures[1:]):
        return None
    if any(len(values) != 1 for values in font_values.values()):
        return None
    run_signatures[0].update({
        "font_%s" % slot: next(iter(values)) for slot, values in font_values.items()
    })
    result = {
        "pPr.%s" % key: effective_ppr[key]
        for key in ADDED_STYLE_PPR_KEYS
        if effective_ppr.get(key) is not None
    }
    result.update(
        {
            "pPr.%s" % key: bool(effective_ppr.get(key, False))
            for key in ADDED_STYLE_PPR_BOOLEAN_KEYS
        }
    )
    result.update({"rPr.%s" % key: value for key, value in run_signatures[0].items()})
    return result


def unanimous_style_baseline(
    signatures: list[dict[str, Any] | None], minimum_peers: int
) -> dict[str, Any]:
    if len(signatures) < minimum_peers or any(signature is None for signature in signatures):
        return {}
    # Differing source attributes invalidate the role, not only that attribute.
    keys = set.union(*(set(signature) for signature in signatures))
    for key in keys:
        values = [signature[key] for signature in signatures if key in signature]
        if any(value != values[0] for value in values[1:]):
            return {}
    common_keys = set.intersection(*(set(signature) for signature in signatures))
    return {key: signatures[0][key] for key in sorted(common_keys)}


def added_content_style_findings(
    source_manifest: dict[str, Any], target_manifest: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Check only confidently inserted chapter blocks against unanimous peers."""
    source = comparable_body_paragraphs(source_manifest)
    target = comparable_body_paragraphs(target_manifest)
    added = confident_added_paragraph_indexes(source, target)
    blocks: list[list[int]] = []
    for index in sorted(added):
        if not blocks or index != blocks[-1][-1] + 1:
            blocks.append([index])
        else:
            blocks[-1].append(index)

    eligible_blocks = []
    for block in blocks:
        roles = {paragraph_style_role(target_manifest, target[index]) for index in block}
        if "body" in roles and any(
            role is not None and role.startswith("heading:") for role in roles
        ):
            eligible_blocks.append(block)

    source_by_role: dict[str, list[tuple[dict[str, Any], dict[str, Any] | None]]] = {}
    for paragraph in source:
        role = paragraph_style_role(source_manifest, paragraph)
        signature = comparable_style_signature(source_manifest, paragraph)
        if role:
            source_by_role.setdefault(role, []).append((paragraph, signature))

    findings: list[dict[str, Any]] = []
    compared = 0
    for block in eligible_blocks:
        for index in block:
            paragraph = target[index]
            role = paragraph_style_role(target_manifest, paragraph)
            signature = comparable_style_signature(target_manifest, paragraph)
            if role is None or signature is None:
                continue
            role_family = "heading" if role.startswith("heading:") else role
            peers = source_by_role.get(role, [])
            baseline = unanimous_style_baseline(
                [peer_signature for _, peer_signature in peers],
                ADDED_STYLE_MIN_SOURCE_PEERS[role_family],
            )
            if not baseline:
                continue
            compared += 1
            differences = {
                key: {"expected": value, "actual": signature[key]}
                for key, value in baseline.items()
                if key in signature and signature[key] != value
            }
            if not differences:
                continue
            findings.append(
                issue(
                    "error",
                    "E_COMPARE_ADDED_CONTENT_STYLE_MISMATCH",
                    str(paragraph.get("location") or "word/document.xml"),
                    "confidently inserted chapter content differs from the "
                    "source document's unanimous same-role formatting",
                    expected=baseline,
                    actual={key: signature[key] for key in differences},
                    evidence={
                        "role": role,
                        "differing_properties": differences,
                        "source_peer_count": len(peers),
                        "source_sample_locations": [
                            peer.get("location") for peer, _ in peers[:3]
                        ],
                        "insertion_proof": "inserted paragraph mark or fully retained ordered source",
                        "text": paragraph.get("text"),
                    },
                )
            )
    return findings, {
        "confident_added_count": len(added),
        "eligible_chapter_blocks": len(eligible_blocks),
        "compared_paragraph_count": compared,
        "finding_count": len(findings),
    }


def compare_source_to_target(
    source_manifest: dict[str, Any], target_manifest: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Keep the explicitly requested insertion-consistency policy only."""
    findings, summary = added_content_style_findings(source_manifest, target_manifest)
    return findings, [], {
        "performed": True,
        "added_content_style": summary,
        "finding_count": len(findings),
    }


# Budget the report using a stdlib-only heuristic, not a tokenizer guarantee.
# Preserve error_summary even when detailed evidence must be trimmed.
REPORT_TOKEN_BUDGET = 3000
MAX_GROUP_SAMPLE_LOCATIONS = 3


def estimate_tokens(value: Any) -> int:
    """Heuristic token estimate for a JSON-serializable value (stdlib only).

    CJK/full-width characters count as one token each; every other run of text
    counts one token per three characters (rounded up). The report is emitted
    with indent=2, so the same indentation is applied here for parity.
    """
    text = json.dumps(value, ensure_ascii=False, indent=2)
    cjk = 0
    other = 0
    for character in text:
        codepoint = ord(character)
        if codepoint > 0x2E80 and (
            0x3400 <= codepoint <= 0x9FFF
            or 0xF900 <= codepoint <= 0xFAFF
            or 0x3000 <= codepoint <= 0x30FF
            or 0xFF00 <= codepoint <= 0xFFEF
            or 0x20000 <= codepoint <= 0x3FFFF
        ):
            cjk += 1
        else:
            other += 1
    return cjk + -(-other // 3)


def aggregate_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold findings that share one root cause into one group across every code.

    A root cause is (code, message, expected, actual, repair_hint); location is
    never part of the key, so all instances of the same defect and same fix -
    every ASCII quote, every broken style reference, every legacy-font run -
    collapse into a single group carrying ``occurrences`` and up to
    MAX_GROUP_SAMPLE_LOCATIONS sample locations. Distinct defects and distinct
    fixes stay separate, so the actionable contract is preserved while volume no
    longer scales with the number of instances.
    """
    order: list[tuple] = []
    grouped: dict[tuple, dict[str, Any]] = {}
    for item in findings:
        key = (
            item.get("code"),
            item.get("message"),
            stable_json_hash(item.get("expected")),
            stable_json_hash(item.get("actual")),
            item.get("repair_hint"),
        )
        group = grouped.get(key)
        if group is None:
            collapsed = dict(item)
            collapsed["occurrences"] = 1
            collapsed["sample_locations"] = (
                [item.get("location")] if item.get("location") is not None else []
            )
            grouped[key] = collapsed
            order.append(key)
        else:
            group["occurrences"] += 1
            location = item.get("location")
            if (
                location is not None
                and len(group["sample_locations"]) < MAX_GROUP_SAMPLE_LOCATIONS
            ):
                group["sample_locations"].append(location)
    result: list[dict[str, Any]] = []
    for key in order:
        group = grouped[key]
        # A group's own ``location`` becomes ambiguous once folded; sample_locations
        # already carries representative positions plus the total occurrences.
        group.pop("location", None)
        if group["occurrences"] == 1 and len(group["sample_locations"]) <= 1:
            group["location"] = (
                group["sample_locations"][0] if group["sample_locations"] else None
            )
            group.pop("sample_locations", None)
        result.append(group)
    return result


def summarize_by_code(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact, always-affordable summary that survives every trimming level."""
    by_code: dict[str, int] = {}
    for item in findings:
        code = str(item.get("code"))
        by_code[code] = by_code.get(code, 0) + 1
    return {
        "total_findings": len(findings),
        "distinct_codes": len(by_code),
        "by_code": dict(sorted(by_code.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _trim_group(group: dict[str, Any], level: int) -> dict[str, Any]:
    """Return a group thinned to the given trim level (higher = smaller)."""
    if level <= 0:
        return group
    trimmed = dict(group)
    if level >= 1:
        # Level 1: drop the bulky per-instance evidence; keep the fix and samples.
        trimmed.pop("evidence", None)
    if level >= 2:
        # Level 2: keep only what identifies the defect and how many there are.
        for field in ("expected", "actual", "repair_hint", "sample_locations"):
            trimmed.pop(field, None)
    return trimmed


def build_bounded_errors(
    groups: list[dict[str, Any]], summary: dict[str, Any], budget: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fit the aggregated groups under ``budget`` estimated tokens.

    Progressive, non-destructive-first trimming. Whatever happens, the compact
    ``summary`` (per-code counts and totals) is always retained, so the report
    never loses the fact that a defect exists - only per-instance verbosity is
    shed. Returns the emitted groups and a report_budget note describing what,
    if anything, was trimmed.
    """
    note: dict[str, Any] = {
        "token_budget": budget,
        "estimator": "stdlib-cjk-aware-upper-bound",
        "trim_level": 0,
    }
    # Level 0: everything. Levels 1-2: thin each group. Level 3: summary only.
    for level in (0, 1, 2):
        candidate = [_trim_group(group, level) for group in groups]
        if estimate_tokens({"errors": candidate, "error_summary": summary}) <= budget:
            note["trim_level"] = level
            if level:
                note["detail"] = (
                    "per-instance evidence trimmed to fit the token budget; "
                    "error_summary.by_code retains full per-code counts"
                )
            return candidate, note
    # Level 3 hard fallback: drop errors[] entirely; the summary alone must fit,
    # and it is tiny by construction (one integer per distinct code).
    note["trim_level"] = 3
    note["detail"] = (
        "errors[] omitted to satisfy the token budget; see error_summary.by_code "
        "for the full per-code finding counts"
    )
    return [], note


# Fields worth keeping when the checks telemetry must be compacted to stay under
# budget. Everything else (definitions, skip counters, breakdowns) is diagnostic
# and can be shed without losing whether a check ran or passed.
COMPACT_CHECK_FIELDS = (
    "performed",
    "passed",
    "configured",
    "finding_count",
    "font_error_count",
    "word_count",
    "char_count",
    "expected",
    "blocking_failure",
    "reason",
)


def compact_checks(checks: dict[str, Any]) -> dict[str, Any]:
    """Shrink each check to its essential status fields under the token budget."""
    compact: dict[str, Any] = {}
    for name, value in checks.items():
        if isinstance(value, dict):
            compact[name] = {
                field: value[field]
                for field in COMPACT_CHECK_FIELDS
                if field in value
            }
        else:
            compact[name] = value
    return compact


def load_edit_plan(path: Path | None) -> dict[str, Any] | None:
    """Load optional rules; require a code and at least one location predicate."""
    if path is None:
        return None
    if not path.is_file():
        raise AuditError("--edit-plan file does not exist: %s" % path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AuditError("failed to read --edit-plan JSON: %s" % exc)
    if not isinstance(data, dict) or not isinstance(data.get("planned_changes"), list):
        raise AuditError(
            "--edit-plan JSON must be an object with a 'planned_changes' array"
        )
    compiled_rules: list[dict[str, Any]] = []
    for index, rule in enumerate(data["planned_changes"]):
        if not isinstance(rule, dict) or not isinstance(rule.get("code"), str) or not rule["code"].strip():
            raise AuditError(
                "planned_changes[%d] must be an object with a 'code' string" % index
            )
        for key in ("location", "location_prefix"):
            if key in rule and rule[key] is not None:
                if not isinstance(rule[key], str) or not rule[key].strip():
                    raise AuditError("planned_changes[%d].%s must be a nonempty string" % (index, key))
        compiled: dict[str, Any] = {"code": rule["code"]}
        if "location" in rule and rule["location"] is not None:
            compiled["location"] = str(rule["location"])
        if "location_prefix" in rule and rule["location_prefix"] is not None:
            compiled["location_prefix"] = str(rule["location_prefix"])
        if "location" not in compiled and "location_prefix" not in compiled:
            raise AuditError(
                "planned_changes[%d] must set 'location' or 'location_prefix'; "
                "code-only wildcard rules are not allowed" % index
            )
        compiled_rules.append(compiled)
    return {"path": str(path), "rules": compiled_rules}


# These findings express formatting/content policy, not package integrity.
# Editing an object never authorizes broken references, identities or fields.
PLAN_WAIVABLE_CODES = frozenset({
    "E_COMPARE_ADDED_CONTENT_STYLE_MISMATCH",
    "E_CHINESE_ASCII_DOUBLE_QUOTE",
    "E_TABLE_PARAGRAPH_FIRST_LINE_INDENT",
})


def _finding_matches_plan(finding: dict[str, Any], plan: dict[str, Any]) -> bool:
    code = str(finding.get("code") or "")
    # Use an allowlist so new integrity checks cannot silently become waivable.
    if code not in PLAN_WAIVABLE_CODES:
        return False
    location = str(finding.get("location") or "")
    for rule in plan["rules"]:
        if rule["code"] != code:
            continue
        if "location" in rule and rule["location"] != location:
            continue
        if "location_prefix" in rule:
            prefix = rule["location_prefix"]
            if not location.startswith(prefix):
                continue
            # Locations use '#' between a part and its paragraph, and '/' for
            # descendants. Match whole components: p1 must not absorb p10,
            # nor run1/char1 absorb run10/char10. Explicit trailing separators
            # still select descendants, as existing prefix plans expect.
            if (
                location != prefix
                and prefix[-1:] not in {"/", "#"}
                and location[len(prefix):len(prefix) + 1] not in {"/", "#"}
            ):
                continue
        return True
    return False


def command_audit(args: argparse.Namespace) -> int:
    if args.source is not None and args.source.resolve() == args.docx.resolve():
        raise AuditError("--source must be a different DOCX from the target")
    word_count_minimum = getattr(args, "word_count_min", None)
    word_count_maximum = getattr(args, "word_count_max", None)
    if word_count_minimum is not None and word_count_minimum <= 0:
        raise AuditError("--word-count-min must be a positive integer")
    if word_count_maximum is not None and word_count_maximum <= 0:
        raise AuditError("--word-count-max must be a positive integer")
    if (
        word_count_minimum is not None
        and word_count_maximum is not None
        and word_count_minimum > word_count_maximum
    ):
        raise AuditError("--word-count-min must not exceed --word-count-max")

    target_manifest = inspect_docx(args.docx)
    target_fatal = [
        item
        for item in target_manifest.get("findings", [])
        if item.get("code") in FATAL_PACKAGE_CODES
    ]
    findings = list(target_manifest.get("findings", []))
    mode = "source_compare" if args.source is not None else "standalone"
    source_manifest: dict[str, Any] | None = None
    source_fatal: list[dict[str, Any]] = []
    source_comparison_performed = False
    quote_check = {
        "performed": False,
        "reason": "target DOCX is not valid enough for a complete text check",
    }
    table_indent_check = {
        "performed": False,
        "reason": "target DOCX is not valid enough for a complete table-text check",
    }
    font_audit_check = {
        "performed": False,
        "reason": "target DOCX is not valid enough for a complete font check",
    }
    word_count_check = {
        "performed": False,
        "configured": (
            word_count_minimum is not None or word_count_maximum is not None
        ),
        "reason": "target DOCX is not valid enough for a complete word-count check",
    }

    if not target_fatal:
        target_policy_findings, target_policy_checks = document_policy_findings(
            target_manifest,
            word_count_minimum,
            word_count_maximum,
        )
        findings.extend(target_policy_findings)
        quote_check = target_policy_checks["chinese_ascii_double_quotes"]
        table_indent_check = target_policy_checks[
            "table_paragraph_first_line_indent"
        ]
        font_audit_check = target_policy_checks["font_audit"]
        word_count_check = target_policy_checks["word_count"]

    if args.source is not None:
        source_manifest = inspect_docx(args.source)
        source_fatal = [
            item
            for item in source_manifest.get("findings", [])
            if item.get("code") in FATAL_PACKAGE_CODES
        ]
        for source_error in source_fatal:
            copied = dict(source_error)
            copied["location"] = "source:%s" % source_error.get("location", "")
            copied["message"] = "source DOCX is not usable for comparison: %s" % str(
                source_error.get("message") or "invalid source"
            )
            findings.append(copied)
        if not source_fatal and not target_fatal:
            source_findings = list(source_manifest.get("findings", []))
            source_policy_findings, _ = document_policy_findings(
                source_manifest,
                word_count_minimum,
                word_count_maximum,
            )
            source_findings.extend(source_policy_findings)
            findings = filter_unchanged_baseline_findings(
                source_findings, findings
            )
            compare_findings, _, _ = compare_source_to_target(
                source_manifest, target_manifest
            )
            findings.extend(compare_findings)
            source_comparison_performed = True

    active = enrich_findings(findings)
    raw_errors = [item for item in active if item.get("severity") == "error"]
    # Without a plan, all errors retain the existing blocking behavior.
    edit_plan = load_edit_plan(getattr(args, "edit_plan", None))
    in_plan_errors: list[dict[str, Any]] = []
    out_of_plan_errors: list[dict[str, Any]] = []
    if edit_plan is not None:
        for item in raw_errors:
            matched = _finding_matches_plan(item, edit_plan)
            item["in_plan"] = matched
            (in_plan_errors if matched else out_of_plan_errors).append(item)
    blocking_errors = out_of_plan_errors if edit_plan is not None else raw_errors
    error_summary = summarize_by_code(blocking_errors)
    error_groups = aggregate_findings(blocking_errors)
    input_invalid = bool(target_fatal or source_fatal)
    if input_invalid:
        automated_status = "invalid"
    elif blocking_errors:
        automated_status = "failed"
    else:
        automated_status = "passed"

    checks = {
        "source_comparison": {"performed": source_comparison_performed},
        "chinese_ascii_double_quotes": quote_check,
        "table_paragraph_first_line_indent": table_indent_check,
        "font_audit": font_audit_check,
        "word_count": word_count_check,
    }
    report = {
        "schema_version": 5,
        "reporting_policy": "errors_only",
        "mode": mode,
        "target": target_manifest.get("file", {}),
        "source": source_manifest.get("file", {}) if source_manifest else None,
        "automated_status": automated_status,
        "automated_checks_passed": automated_status == "passed",
        # error_count is the true number of findings, never the group count, so
        # aggregation never hides how many defects exist.
        "error_count": len(raw_errors),
        "error_summary": error_summary,
        "errors": error_groups,
        "checks": checks,
        "input_valid": not input_invalid,
        "execution_completed": True,
    }
    if error_summary["by_code"].get("E_CHINESE_ASCII_DOUBLE_QUOTE"):
        # Keep repair safety outside errors[] so group/evidence trimming can
        # never remove it while quote findings still remain in the report.
        report["repair_guidance"] = {
            "E_CHINESE_ASCII_DOUBLE_QUOTE": QUOTE_REPAIR_SAFETY_NOTE,
        }
    if edit_plan is not None:
        report["edit_plan"] = {
            "path": edit_plan["path"],
            "rule_count": len(edit_plan["rules"]),
            "in_plan_error_count": len(in_plan_errors),
            "out_of_plan_error_count": len(out_of_plan_errors),
            "in_plan_error_summary": summarize_by_code(in_plan_errors),
        }
    # Enforce the hard token budget on the whole report. errors[] is fitted into
    # the room left by the fixed sections (metadata, checks, error_summary). The
    # escalation prefers keeping information: first fit errors against full
    # checks; if that forces the errors to vanish while verbose checks telemetry
    # is still holding room, compact the checks and refit so aggregated error
    # groups can be kept instead. report_budget records the final trim level and
    # whether checks were compacted.
    def fit_errors(current_checks: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        report["checks"] = current_checks
        report.pop("report_budget", None)
        fixed = estimate_tokens({k: v for k, v in report.items() if k != "errors"})
        return build_bounded_errors(
            error_groups, error_summary, max(REPORT_TOKEN_BUDGET - fixed, 0)
        )

    bounded_errors, budget_note = fit_errors(checks)
    if budget_note["trim_level"] >= 3:
        # errors[] would be dropped; try again with compacted checks to recover
        # room for at least the aggregated group stubs.
        recovered_errors, recovered_note = fit_errors(compact_checks(checks))
        if recovered_note["trim_level"] < 3:
            bounded_errors, budget_note = recovered_errors, recovered_note
            budget_note["checks_compacted"] = True
        else:
            report["checks"] = checks
    report["errors"] = bounded_errors
    report["report_budget"] = budget_note
    # Absolute guarantee: whatever remains must be <= budget. If even the summary
    # + full checks overflow, compact checks and drop errors[] outright.
    if estimate_tokens(report) > REPORT_TOKEN_BUDGET:
        report["checks"] = compact_checks(report["checks"])
        report["errors"] = []
        budget_note["trim_level"] = 3
        budget_note["checks_compacted"] = True
        budget_note["detail"] = (
            "errors[] omitted to satisfy the token budget; see error_summary.by_code "
            "for the full per-code finding counts"
        )
    # The report is already trimmed to <=REPORT_TOKEN_BUDGET tokens, so the whole
    # thing fits in a single tool result. Print it verbatim on stdout so the
    # caller can act on it immediately, without any report file.
    print(
        "[%s] mode=%s errors=%d%s"
        % (
            automated_status.upper(),
            mode,
            len(raw_errors),
            (
                " in_plan=%d out_of_plan=%d"
                % (len(in_plan_errors), len(out_of_plan_errors))
                if edit_plan is not None
                else ""
            ),
        )
    )
    print("----- BEGIN AUDIT REPORT JSON (complete; do not read any file) -----")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("----- END AUDIT REPORT JSON -----")
    if input_invalid:
        return 2
    return 0 if not blocking_errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="audit a final DOCX")
    audit.add_argument("docx", type=Path)
    audit.add_argument(
        "--source",
        type=Path,
        help="optional template or pre-edit DOCX for format/structure comparison",
    )
    audit.add_argument(
        "--word-count-min",
        type=int,
        help=(
            "optional inclusive minimum visible-body word_count; may be used "
            "alone or with --word-count-max"
        ),
    )
    audit.add_argument(
        "--word-count-max",
        type=int,
        help=(
            "optional inclusive maximum visible-body word_count; may be used "
            "alone or with --word-count-min"
        ),
    )
    audit.add_argument(
        "--edit-plan",
        type=Path,
        default=None,
        help=(
            "optional plan JSON declaring intended changes (canvas OOXML "
            "editing). When provided, each finding is classified in_plan / "
            "out_of_plan; the header line gains in_plan / out_of_plan counts, "
            "errors[] keeps only out_of_plan findings and exit is non-zero "
            "only for out_of_plan errors."
        ),
    )
    audit.set_defaults(func=command_audit)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if etree is None:
            raise AuditError("lxml is required for this subcommand")
        status = args.func(args)
    except AuditError as exc:
        print("[INPUT ERROR] %s" % exc, file=sys.stderr)
        status = 2
    raise SystemExit(status)


if __name__ == "__main__":
    main()
