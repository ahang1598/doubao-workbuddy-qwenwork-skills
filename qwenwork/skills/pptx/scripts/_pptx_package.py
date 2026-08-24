"""Local parity adapter for qwenwork-fc-pptx metadata operations."""

from __future__ import annotations

import json
import posixpath
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET


MAX_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 512 << 20
MAX_XML_BYTES = 16 << 20
MAX_ISSUES = 128
MAX_SLIDES = 300
MAX_TEXT_BYTES_PER_SLIDE = 4 << 10
MAX_TOTAL_TEXT_BYTES = 24 << 10
MAX_TOTAL_FONT_BYTES = 16 << 10
MAX_COMPRESSION_RATIO = 250
MAX_INSPECTION_METADATA_BYTES = 112 << 10
XML_DECLARATION = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
RELATIONSHIP_TYPE_SUFFIXES = {
    "chart": "/chart",
    "comments": "/comments",
    "image": "/image",
    "notes": "/notesSlide",
    "slide": "/slide",
    "slide_layout": "/slideLayout",
    "theme": "/theme",
}
REQUIRED_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
}
SLIDE_NAME = re.compile(r"ppt/slides/slide([1-9][0-9]*)\.xml")


class PackageInvalid(ValueError):
    """The package cannot be safely or meaningfully inspected."""


def _issue(issues: list[dict[str, str]], code: str, message: str, part: str = "") -> None:
    if len(issues) >= MAX_ISSUES:
        return
    item = {"severity": "error", "code": code, "message": message}
    if part:
        item["part"] = part
    issues.append(item)


def _safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name and "\x00" not in name


def _read_xml(archive: zipfile.ZipFile, name: str, issues: list[dict[str, str]]) -> ET.Element | None:
    try:
        info = archive.getinfo(name)
    except KeyError:
        _issue(issues, "PART_MISSING", "required OOXML part is missing", name)
        return None
    if info.file_size > MAX_XML_BYTES:
        _issue(issues, "XML_PART_TOO_LARGE", "XML part exceeds its limit", name)
        return None
    try:
        payload = archive.read(info)
    except (OSError, RuntimeError, zipfile.BadZipFile):
        _issue(issues, "PART_READ_FAILED", "OOXML part could not be read", name)
        return None
    if XML_DECLARATION.search(payload) is not None:
        _issue(issues, "XML_DTD_FORBIDDEN", "DTD and entity declarations are forbidden", name)
        return None
    try:
        return ET.fromstring(payload)
    except ET.ParseError:
        _issue(issues, "XML_INVALID", "OOXML part is not well-formed XML", name)
        return None


def _source_for_rels(name: str) -> str:
    if name == "_rels/.rels":
        return ""
    directory, filename = posixpath.split(name)
    if not directory.endswith("/_rels") or not filename.endswith(".rels"):
        return ""
    return posixpath.join(directory[:-6], filename[:-5]).lstrip("/")


def _resolve_target(source: str, target: str) -> str:
    base = posixpath.dirname(source)
    return posixpath.normpath(posixpath.join(base, target)).lstrip("/")


def _relationships(
    archive: zipfile.ZipFile,
    names: set[str],
    issues: list[dict[str, str]],
) -> dict[str, dict[str, dict[str, str]]]:
    result: dict[str, dict[str, dict[str, str]]] = {}
    for name in sorted(item for item in names if item.endswith(".rels")):
        root = _read_xml(archive, name, issues)
        if root is None:
            continue
        source = _source_for_rels(name)
        by_id: dict[str, dict[str, str]] = {}
        for relationship in root.findall("pr:Relationship", NS):
            rel_id = relationship.get("Id", "")
            target = relationship.get("Target", "")
            rel_type = relationship.get("Type", "")
            mode = relationship.get("TargetMode", "Internal")
            if not rel_id or rel_id in by_id:
                _issue(issues, "RELATIONSHIP_ID_INVALID", "relationship ID is missing or duplicated", name)
                continue
            item = {"type": rel_type, "target": target, "mode": mode}
            if mode != "External":
                resolved = _resolve_target(source, target)
                item["resolved"] = resolved
                if not _safe_name(resolved) or resolved not in names:
                    _issue(issues, "RELATIONSHIP_TARGET_MISSING", "internal relationship target is missing", name)
            by_id[rel_id] = item
        result[source] = by_id
    return result


def _content_types(
    archive: zipfile.ZipFile,
    names: set[str],
    issues: list[dict[str, str]],
) -> None:
    root = _read_xml(archive, "[Content_Types].xml", issues)
    if root is None:
        return
    defaults = {item.get("Extension", "").lower() for item in root.findall("ct:Default", NS)}
    overrides = {item.get("PartName", "").lstrip("/") for item in root.findall("ct:Override", NS)}
    for name in sorted(names):
        if name.endswith("/") or name == "[Content_Types].xml" or name.endswith(".rels"):
            continue
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if name not in overrides and extension not in defaults:
            _issue(issues, "CONTENT_TYPE_MISSING", "part has no matching content type", name)


def _bounded_text(nodes: list[str], remaining: int) -> tuple[list[str], int, bool]:
    output: list[str] = []
    used = 0
    truncated = False
    limit = min(MAX_TEXT_BYTES_PER_SLIDE, max(0, remaining))
    for value in nodes:
        normalized = " ".join(value.split())
        if not normalized:
            continue
        encoded = normalized.encode("utf-8")
        if used + len(encoded) > limit:
            truncated = True
            break
        output.append(normalized)
        used += len(encoded)
    return output, used, truncated


def _resource_counts(names: set[str]) -> dict[str, int]:
    prefixes = {
        "charts": "ppt/charts/",
        "embeddings": "ppt/embeddings/",
        "layouts": "ppt/slideLayouts/",
        "masters": "ppt/slideMasters/",
        "media": "ppt/media/",
        "notes": "ppt/notesSlides/",
        "themes": "ppt/theme/",
    }
    return {key: sum(1 for name in names if name.startswith(prefix) and not name.endswith(".rels")) for key, prefix in prefixes.items()}


def _metadata_size(value: dict[str, Any]) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _fit_inspection_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if _metadata_size(value) <= MAX_INSPECTION_METADATA_BYTES:
        return value
    value["metadata_truncated"] = True
    slides = value["slides"]
    for field in ("fonts", "text", "relationships"):
        for slide in slides:
            if slide.get(field):
                slide[field] = [] if field != "relationships" else {}
        if _metadata_size(value) <= MAX_INSPECTION_METADATA_BYTES:
            return value
    if len(value["issues"]) > 32:
        value["issues"] = value["issues"][:32]
        value["issue_summary"]["truncated"] = True
    if _metadata_size(value) <= MAX_INSPECTION_METADATA_BYTES:
        return value
    for field in ("title", "part"):
        for slide in slides:
            slide[field] = ""
        if _metadata_size(value) <= MAX_INSPECTION_METADATA_BYTES:
            return value
    raise PackageInvalid("PPTX inspection metadata exceeds its bounded result limit")


def inspect_package(path: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackageInvalid("input is not a readable PPTX ZIP package") from exc
    with archive:
        infos = archive.infolist()
        if not 1 <= len(infos) <= MAX_ENTRIES:
            raise PackageInvalid("PPTX ZIP entry count exceeds its limit")
        names: set[str] = set()
        total_uncompressed = 0
        for info in infos:
            if not _safe_name(info.filename) or info.filename in names:
                raise PackageInvalid("PPTX ZIP contains an unsafe or duplicate entry")
            if info.flag_bits & 0x1:
                raise PackageInvalid("encrypted PPTX packages are unsupported")
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise PackageInvalid("PPTX decompressed size exceeds its limit")
            if info.file_size > 1 << 20 and info.file_size > max(1, info.compress_size) * MAX_COMPRESSION_RATIO:
                raise PackageInvalid("PPTX ZIP compression ratio exceeds its limit")
            names.add(info.filename)
        for required in sorted(REQUIRED_PARTS - names):
            _issue(issues, "PART_MISSING", "required OOXML part is missing", required)
        _content_types(archive, names, issues)
        rels = _relationships(archive, names, issues)
        presentation = _read_xml(archive, "ppt/presentation.xml", issues)
        presentation_rels = rels.get("ppt/presentation.xml", {})
        slide_records: list[dict[str, Any]] = []
        slide_ids: set[str] = set()
        total_text = 0
        total_fonts = 0
        if presentation is not None:
            size = presentation.find("p:sldSz", NS)
            width = int(size.get("cx", "0")) if size is not None and size.get("cx", "").isdigit() else 0
            height = int(size.get("cy", "0")) if size is not None and size.get("cy", "").isdigit() else 0
            slide_list = presentation.findall("p:sldIdLst/p:sldId", NS)
            if len(slide_list) > MAX_SLIDES:
                raise PackageInvalid("PPTX slide count exceeds its limit")
            for index, slide_id in enumerate(slide_list, start=1):
                numeric_id = slide_id.get("id", "")
                relationship_id = slide_id.get(f"{{{NS['r']}}}id", "")
                if not numeric_id or numeric_id in slide_ids:
                    _issue(issues, "SLIDE_ID_INVALID", "slide ID is missing or duplicated", "ppt/presentation.xml")
                slide_ids.add(numeric_id)
                relationship = presentation_rels.get(relationship_id)
                slide_part = relationship.get("resolved", "") if relationship else ""
                if not relationship or not relationship.get("type", "").endswith("/slide") or slide_part not in names:
                    _issue(issues, "SLIDE_RELATIONSHIP_INVALID", "slide reference does not resolve to a slide", "ppt/presentation.xml")
                    slide_records.append({"index": index, "slide_id": numeric_id, "part": slide_part, "hidden": False, "text": []})
                    continue
                root = _read_xml(archive, slide_part, issues)
                texts: list[str] = []
                hidden = False
                fonts: set[str] = set()
                fonts_truncated = False
                if root is not None:
                    raw_text = [node.text or "" for node in root.findall(".//a:t", NS)]
                    texts, used, truncated = _bounded_text(raw_text, MAX_TOTAL_TEXT_BYTES - total_text)
                    total_text += used
                    hidden = root.get("show", "1") in {"0", "false", "off"}
                    for node in root.iter():
                        typeface = node.get("typeface", "").strip()
                        if typeface:
                            bounded_typeface = typeface[:128]
                            encoded_size = len(bounded_typeface.encode("utf-8"))
                            if (
                                len(fonts) < 32
                                and bounded_typeface not in fonts
                                and total_fonts + encoded_size <= MAX_TOTAL_FONT_BYTES
                            ):
                                fonts.add(bounded_typeface)
                                total_fonts += encoded_size
                            elif bounded_typeface not in fonts:
                                fonts_truncated = True
                else:
                    truncated = False
                slide_rels = rels.get(slide_part, {})
                kinds = Counter()
                for item in slide_rels.values():
                    for label, suffix in RELATIONSHIP_TYPE_SUFFIXES.items():
                        if item.get("type", "").endswith(suffix):
                            kinds[label] += 1
                            break
                record: dict[str, Any] = {
                    "index": index,
                    "slide_id": numeric_id,
                    "part": slide_part,
                    "hidden": hidden,
                    "title": texts[0][:512] if texts else "",
                    "text": texts,
                    "fonts": sorted(fonts),
                    "relationships": dict(sorted(kinds.items())),
                }
                if truncated:
                    record["text_truncated"] = True
                if fonts_truncated:
                    record["fonts_truncated"] = True
                slide_records.append(record)
        else:
            width = height = 0
        physical_slides = sorted(name for name in names if SLIDE_NAME.fullmatch(name))
        referenced = {record["part"] for record in slide_records if record["part"]}
        for orphan in sorted(set(physical_slides) - referenced):
            _issue(issues, "ORPHAN_SLIDE", "slide part is not referenced by the presentation", orphan)
        errors = sum(1 for issue in issues if issue["severity"] == "error")
        return _fit_inspection_metadata({
            "schema_version": "qwenwork.pptx.inspect/v1",
            "valid": errors == 0,
            "document": {
                "slide_count": len(slide_records),
                "hidden_slide_count": sum(1 for record in slide_records if record["hidden"]),
                "width_emu": width,
                "height_emu": height,
                "zip_entries": len(infos),
                "uncompressed_bytes": total_uncompressed,
            },
            "resources": _resource_counts(names),
            "slides": slide_records,
            "issues": issues,
            "issue_summary": {"errors": errors, "truncated": len(issues) >= MAX_ISSUES},
            "engine": {"name": "qwenwork-pptx-ooxml", "version": "1"},
        })


def validate_package(path: Path) -> dict[str, Any]:
    try:
        inspection = inspect_package(path)
    except PackageInvalid as exc:
        return {
            "schema_version": "qwenwork.pptx.validation/v1",
            "valid": False,
            "issues": [{"severity": "error", "code": "PPTX_INVALID", "message": str(exc)}],
            "issue_summary": {"errors": 1, "truncated": False},
            "engine": {"name": "qwenwork-pptx-ooxml", "version": "1"},
        }
    result = {
        "schema_version": "qwenwork.pptx.validation/v1",
        "valid": inspection["valid"],
        "document": inspection["document"],
        "resources": inspection["resources"],
        "issues": inspection["issues"],
        "issue_summary": inspection["issue_summary"],
        "engine": inspection["engine"],
    }
    if inspection.get("metadata_truncated") is True:
        result["metadata_truncated"] = True
    return result
