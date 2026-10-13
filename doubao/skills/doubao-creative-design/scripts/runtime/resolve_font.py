#!/usr/bin/env python3
"""Resolve, optionally fetch, and verify a catalogued font."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import re
import shutil
import struct
import unicodedata
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[2]
CATALOG_DIR = ROOT / "assets" / "fonts" / "catalogs"
CDN_MANIFEST = ROOT / "assets" / "fonts" / "font-cdn-manifest.json"
WEB_FONT_MANIFEST = ROOT / "assets" / "fonts" / "web-font-manifest.json"
CURATED_POOL = ROOT / "assets" / "fonts" / "font-curated-pool.json"
FONT_SUFFIXES = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
FONT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"wOFF", b"wOF2")
TRUSTED_CDN_HOST = "lf-flow-web-cdn.doubao.com"
PERMISSIVE_LICENSE_MARKERS = ("ofl", "apache", "ubuntu font license", "ufl")


def load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        records.extend(data.get("records", []))
    return records


def load_manifest() -> dict[str, Any]:
    if not CDN_MANIFEST.exists():
        return {"files": []}
    data = json.loads(CDN_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data.get("files"), list):
        raise SystemExit("font CDN manifest must contain a files list")
    return data


def load_curated_pool() -> dict[str, Any]:
    return json.loads(CURATED_POOL.read_text(encoding="utf-8"))


def normalize_query(query: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", query).casefold().split())


def select(records: list[dict[str, Any]], query: str) -> dict[str, Any]:
    # Explicit catalog IDs take precedence over curated aliases for other variants.
    by_id = [item for item in records if item.get("id") == query.strip()]
    if len(by_id) == 1:
        return by_id[0]
    normalized = normalize_query(query)
    alias_ids = {
        font["catalog_id"]
        for font in load_curated_pool()["fonts"]
        if normalized and normalized in {
            normalize_query(name)
            for name in [font["display_name"], *font.get("aliases", [])]
        }
    }
    if len(alias_ids) > 1:
        raise SystemExit("font alias is ambiguous: " + json.dumps(sorted(alias_ids, key=lambda value: value or "")))
    if alias_ids:
        matches = [item for item in records if item.get("id") in alias_ids]
        if len(matches) == 1:
            return matches[0]
        raise SystemExit("curated font catalog ID is missing or duplicated")
    exact = [
        item for item in records
        if normalized and normalize_query(str(item.get("name", ""))) == normalized
    ]
    if len(exact) == 1:
        return exact[0]
    partial = [
        item for item in records
        if normalized and normalized in normalize_query(str(item.get("name", "")))
    ]
    candidates = exact or partial
    if len(candidates) == 1:
        return candidates[0]
    matches = [
        {"id": item.get("id"), "name": item.get("name"), "language": item.get("language")}
        for item in candidates[:20]
    ]
    raise SystemExit("font query is ambiguous or missing: " + json.dumps(matches, ensure_ascii=False))


def expected_relative_paths(record: dict[str, Any]) -> list[Path]:
    return [
        Path(item)
        for item in record.get("local_paths", [])
        if isinstance(item, str) and Path(item).suffix.lower() in FONT_SUFFIXES
    ]


def safe_target(root: Path, relative_path: Path) -> Path:
    target = (root / relative_path).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise SystemExit(f"unsafe font destination: {relative_path}")
    return target


def local_files(record: dict[str, Any], storage_root: Path) -> list[Path]:
    exact = [
        safe_target(storage_root, relative)
        for relative in expected_relative_paths(record)
        if safe_target(storage_root, relative).is_file()
    ]
    package_dir = record.get("package_dir")
    if isinstance(package_dir, str):
        directory = safe_target(storage_root, Path(package_dir))
        if directory.exists():
            for path in directory.rglob("*"):
                if path.is_file() and path.suffix.lower() in FONT_SUFFIXES:
                    exact.append(safe_target(directory, path))
    return sorted(set(exact))


def manifest_entries(manifest: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    record_id = record.get("id")
    expected = {path.as_posix() for path in expected_relative_paths(record)}
    return [
        item
        for item in manifest.get("files", [])
        if isinstance(item, dict)
        and item.get("verified") is True
        and item.get("catalog_id") == record_id
        and item.get("local_path") in expected
    ]


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != TRUSTED_CDN_HOST:
        raise ValueError(f"untrusted font CDN URL: {url}")
    # Preserve only existing, legal escapes. Never unquote: %2F is not a slash.
    path = re.sub(r"%(?![0-9A-Fa-f]{2})", "%25", parts.path)
    path = quote(path, safe="/%")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def md5_of(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_font_magic(path: Path) -> bool:
    with path.open("rb") as stream:
        header = stream.read(4)
    return header in FONT_MAGIC


def license_allows_automatic_fetch(record: dict[str, Any]) -> bool:
    if record.get("open_source") is not True:
        return False
    license_name = str(record.get("license", "")).casefold()
    return any(marker in license_name for marker in PERMISSIVE_LICENSE_MARKERS)


def probe_entry(entry: dict[str, Any]) -> dict[str, Any]:
    url = safe_url(str(entry.get("cdn_url", "")))
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "doubao-creative-design-font-resolver/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        final_url = response.geturl()
        safe_url(final_url)
        content_length = response.headers.get("Content-Length")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
        expected_size = entry.get("size_bytes")
        size_ok = not isinstance(expected_size, int) or content_length == str(expected_size)
        type_ok = content_type in {
            "application/font-sfnt", "font/ttf", "font/otf", "application/octet-stream",
            "font/woff", "font/woff2", "application/font-woff",
        }
        return {
            "url": final_url,
            "http_status": response.status,
            "content_length": int(content_length) if content_length and content_length.isdigit() else None,
            "content_type": content_type,
            "size_ok": size_ok,
            "content_type_ok": type_ok,
            "verified": response.status == 200 and size_ok and type_ok,
        }


def fetch_entries(
    entries: list[dict[str, Any]],
    storage_root: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entry in entries:
        relative = Path(str(entry["local_path"]))
        destination = safe_target(storage_root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = safe_url(str(entry["cdn_url"]))
        request = urllib.request.Request(url, headers={"User-Agent": "doubao-creative-design-font-resolver/1.0"})
        fd, name = tempfile.mkstemp(prefix=".font-fetch-", suffix=".part", dir=destination.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
                safe_url(response.geturl())
                shutil.copyfileobj(response, output)
            expected_size = entry.get("size_bytes")
            if isinstance(expected_size, int) and temporary.stat().st_size != expected_size:
                raise ValueError(
                    f"size mismatch: expected {expected_size}, got {temporary.stat().st_size}"
                )
            expected_md5 = entry.get("md5")
            actual_md5 = md5_of(temporary)
            if isinstance(expected_md5, str) and actual_md5 != expected_md5:
                raise ValueError(f"md5 mismatch: expected {expected_md5}, got {actual_md5}")
            if not check_font_magic(temporary):
                raise ValueError("downloaded object is not a supported font binary")
            # Link commits a fully downloaded file atomically without replacing late arrivals.
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if destination.is_symlink() or not destination.is_file() or sha256_of(destination) != sha256_of(temporary):
                    raise ValueError(f"existing font destination has different content: {destination}")
        finally:
            temporary.unlink(missing_ok=True)
        results.append(
            {
                "local_path": relative.as_posix(),
                "absolute_path": str(destination),
                "cdn_url": url,
                "size_bytes": destination.stat().st_size,
                "md5": md5_of(destination),
                "status": "downloaded",
            }
        )
    return results


def register(record: dict[str, Any], package: Path, storage_root: Path) -> None:
    package_dir = record.get("package_dir")
    if not isinstance(package_dir, str):
        raise SystemExit("catalog record has no package_dir")
    added: list[Path] = []
    try:
        destination = safe_target(storage_root, Path(package_dir))
        if destination.exists() and not destination.is_dir():
            raise ValueError(f"font package destination is not a directory: {destination}")
        package = package.resolve(strict=True)
        sources: list[tuple[Path, Path]] = []

        def walk(directory: Path, ancestors: set[Path]) -> None:
            resolved = directory.resolve(strict=True)
            if resolved in ancestors:
                raise ValueError(f"font package contains a symlink cycle: {directory}")
            for source in sorted(directory.iterdir()):
                actual = source.resolve(strict=True)
                if actual != package and package not in actual.parents:
                    raise ValueError(f"font package symlink escapes package: {source}")
                if source.is_dir():
                    walk(source, ancestors | {resolved})
                elif source.is_file() and source.suffix.lower() in FONT_SUFFIXES:
                    sources.append((source, source.relative_to(package)))

        if package.is_dir():
            walk(package, set())
        elif package.is_file() and package.suffix.lower() in FONT_SUFFIXES:
            sources.append((package, Path(package.name)))
        else:
            raise ValueError("register-package accepts a font file or directory containing font files")
        if not sources:
            raise ValueError("no supported font files found in package")

        # Complete the entire preflight before creating directories or copying files.
        plan: list[tuple[Path, Path, str, bool]] = []
        targets: set[Path] = set()
        for source, relative in sources:
            actual_source = source.resolve(strict=True)
            if package.is_dir() and package not in actual_source.parents:
                raise ValueError(f"font package symlink escapes package: {source}")
            logical_target = destination / relative
            if logical_target.is_symlink() and not logical_target.exists():
                raise ValueError(f"dangling font destination symlink: {logical_target}")
            target = safe_target(destination, relative)
            safe_target(storage_root, target)
            if target == destination or target in targets:
                raise ValueError(f"conflicting font destinations: {target}")
            for parent in target.parents:
                if parent.exists() and not parent.is_dir():
                    raise ValueError(f"font destination parent is not a directory: {parent}")
            digest = sha256_of(actual_source)
            exists = target.exists()
            if exists and (not target.is_file() or sha256_of(target) != digest):
                raise ValueError(f"existing font destination has different content: {target}")
            targets.add(target)
            plan.append((actual_source, target, digest, exists))
        for target in targets:
            if any(parent in targets for parent in target.parents):
                raise ValueError(f"font file/directory destination conflict: {target}")

        for source, target, digest, exists in plan:
            if safe_target(storage_root, target) != target or safe_target(destination, target) != target:
                raise ValueError(f"font destination changed after preflight: {target}")
            if exists:
                if not target.is_file() or sha256_of(target) != digest:
                    raise ValueError(f"font destination changed after preflight: {target}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation never overwrites a destination, including a late conflict.
            with target.open("xb") as output:
                added.append(target)
                with source.open("rb") as input_stream:
                    shutil.copyfileobj(input_stream, output)
            if sha256_of(target) != digest:
                raise ValueError(f"font source changed during registration: {source}")
            shutil.copystat(source, target)
    except BaseException as error:
        cleanup_errors = []
        for target in reversed(added):
            try:
                target.unlink(missing_ok=True)
            except OSError as cleanup_error:
                cleanup_errors.append(f"{target}: {cleanup_error}")
        if cleanup_errors:
            raise SystemExit(
                f"register-package failed: {error}; cleanup failed: " + "; ".join(cleanup_errors)
            ) from error
        if isinstance(error, (OSError, ValueError, RuntimeError)):
            raise SystemExit(f"register-package failed: {error}") from error
        raise


def unpack_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def unpack_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def sfnt_offsets(data: bytes) -> list[int]:
    if data[:4] == b"ttcf":
        count = unpack_u32(data, 8)
        return [unpack_u32(data, 12 + index * 4) for index in range(count)]
    if data[:4] in {b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"}:
        return [0]
    return []


def validate_sfnt_face(data: bytes, base: int) -> None:
    """Reject truncated metadata before the existing SFNT readers consume it."""
    if base < 0 or base + 12 > len(data) or data[base:base + 4] not in {
        b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"
    }:
        raise ValueError("invalid or truncated SFNT face header")
    count = unpack_u16(data, base + 4)
    if not count or base + 12 + count * 16 > len(data):
        raise ValueError("invalid or truncated SFNT table directory")
    tables: dict[bytes, tuple[int, int]] = {}
    for index in range(count):
        record = base + 12 + index * 16
        tag, _, offset, length = struct.unpack_from(">4sIII", data, record)
        if tag in tables or offset + length > len(data):
            raise ValueError(f"invalid SFNT table: {tag!r}")
        tables[tag] = (offset, length)
    if b"name" not in tables or b"cmap" not in tables:
        raise ValueError("SFNT face lacks name or cmap metadata")

    if b"maxp" not in tables or tables[b"maxp"][1] < 6:
        raise ValueError("missing or truncated maxp table")
    maxp, maxp_length = tables[b"maxp"]
    version = unpack_u32(data, maxp)
    glyph_count = unpack_u16(data, maxp + 4)
    if not glyph_count or version not in {0x00005000, 0x00010000} or (version == 0x00010000 and maxp_length < 32):
        raise ValueError("invalid maxp glyph count or version")
    if b"glyf" in tables:
        if b"head" not in tables or tables[b"head"][1] < 54 or b"loca" not in tables:
            raise ValueError("missing head/loca for TrueType outlines")
        location_format = struct.unpack_from(">h", data, tables[b"head"][0] + 50)[0]
        if location_format not in {0, 1}:
            raise ValueError("invalid loca format")
        width = 2 if location_format == 0 else 4
        loca, length = tables[b"loca"]
        if length < (glyph_count + 1) * width:
            raise ValueError("truncated loca table")
        previous = 0
        for index in range(glyph_count + 1):
            value = unpack_u16(data, loca + index * width) * 2 if width == 2 else unpack_u32(data, loca + index * width)
            if value < previous or value > tables[b"glyf"][1]:
                raise ValueError("invalid glyph outline bounds")
            previous = value
    elif b"CFF " not in tables and b"CFF2" not in tables:
        raise ValueError("missing glyph outline table")

    offset, length = tables[b"name"]
    if length < 6:
        raise ValueError("truncated name table")
    count = unpack_u16(data, offset + 2)
    strings = unpack_u16(data, offset + 4)
    if 6 + count * 12 > length or strings < 6 + count * 12 or strings > length:
        raise ValueError("invalid name table record/string bounds")
    for index in range(count):
        record = offset + 6 + index * 12
        size, relative = struct.unpack_from(">HH", data, record + 8)
        if strings + relative + size > length:
            raise ValueError("name string extends beyond its table")

    offset, length = tables[b"cmap"]
    if length < 4 or unpack_u16(data, offset) != 0:
        raise ValueError("invalid cmap header")
    count = unpack_u16(data, offset + 2)
    if not count or 4 + count * 8 > length:
        raise ValueError("truncated cmap encoding records")
    for index in range(count):
        platform, encoding, relative = struct.unpack_from(">HHI", data, offset + 4 + index * 8)
        if relative < 4 + count * 8 or relative + 2 > length:
            raise ValueError("invalid cmap subtable offset")
        if not (platform == 0 or (platform == 3 and encoding in {1, 10})):
            continue
        subtable = offset + relative
        font_format = unpack_u16(data, subtable)
        if font_format == 4:
            if relative + 16 > length:
                raise ValueError("truncated format 4 cmap")
            size = unpack_u16(data, subtable + 2)
            segment_bytes = unpack_u16(data, subtable + 6)
            segments = segment_bytes // 2
            if not segments or segment_bytes % 2 or size < 16 + 8 * segments or relative + size > length:
                raise ValueError("invalid format 4 cmap bounds")
            end_codes = subtable + 14
            start_codes = end_codes + 2 * segments + 2
            ranges = start_codes + 4 * segments
            previous_end = -1
            for segment in range(segments):
                start = unpack_u16(data, start_codes + 2 * segment)
                end = unpack_u16(data, end_codes + 2 * segment)
                position = ranges + 2 * segment
                distance = unpack_u16(data, position)
                if start > end or start <= previous_end or distance % 2:
                    raise ValueError("invalid format 4 cmap segment")
                if distance and (position + distance < ranges + 2 * segments or
                                 position + distance + 2 * (end - start + 1) > subtable + size):
                    raise ValueError("format 4 glyph array extends beyond its subtable")
                delta = struct.unpack_from(">h", data, start_codes + 2 * segments + 2 * segment)[0]
                for codepoint in range(start, end + 1):
                    raw = unpack_u16(data, position + distance + 2 * (codepoint - start)) if distance else codepoint
                    glyph = ((raw + delta) & 0xFFFF) if (raw or not distance) else 0
                    if glyph >= glyph_count:
                        raise ValueError("format 4 glyph ID exceeds maxp.numGlyphs")
                previous_end = end
        elif font_format == 12:
            if relative + 16 > length:
                raise ValueError("truncated format 12 cmap")
            size = unpack_u32(data, subtable + 4)
            groups = unpack_u32(data, subtable + 12)
            if size < 16 + 12 * groups or relative + size > length:
                raise ValueError("invalid format 12 cmap bounds")
            previous_end = -1
            for group in range(groups):
                start, end, first_glyph = struct.unpack_from(">III", data, subtable + 16 + group * 12)
                if start > end or start <= previous_end or end > 0x10FFFF:
                    raise ValueError("invalid format 12 cmap group")
                if first_glyph + end - start >= glyph_count:
                    raise ValueError("format 12 glyph ID exceeds maxp.numGlyphs")
                previous_end = end


def sfnt_tables(data: bytes, base: int) -> dict[bytes, tuple[int, int]]:
    validate_sfnt_face(data, base)
    count = unpack_u16(data, base + 4)
    tables: dict[bytes, tuple[int, int]] = {}
    for index in range(count):
        record = base + 12 + index * 16
        tag = data[record : record + 4]
        offset = unpack_u32(data, record + 8)
        length = unpack_u32(data, record + 12)
        if offset + length <= len(data):
            tables[tag] = (offset, length)
    return tables


def decode_name(data: bytes, platform_id: int) -> str:
    encodings = ("utf-16-be",) if platform_id in {0, 3} else ("mac_roman", "utf-8")
    for encoding in encodings:
        try:
            return data.decode(encoding).strip("\x00 ")
        except UnicodeDecodeError:
            continue
    return ""


def family_names(data: bytes, tables: dict[bytes, tuple[int, int]]) -> set[str]:
    location = tables.get(b"name")
    if not location:
        return set()
    offset, length = location
    if offset + length > len(data) or length < 6:
        return set()
    count = unpack_u16(data, offset + 2)
    string_offset = offset + unpack_u16(data, offset + 4)
    unicode_values: dict[int, set[str]] = {16: set(), 1: set()}
    fallback_values: dict[int, set[str]] = {16: set(), 1: set()}
    for index in range(count):
        record = offset + 6 + index * 12
        if record + 12 > offset + length:
            break
        fields = struct.unpack_from(">HHHHHH", data, record)
        platform_id, name_id, size, relative = fields[0], fields[3], fields[4], fields[5]
        if name_id not in unicode_values:
            continue
        start = string_offset + relative
        end = start + size
        if end > offset + length or end > len(data):
            continue
        value = decode_name(data[start:end], platform_id)
        if value:
            target = unicode_values if platform_id in {0, 3} else fallback_values
            target[name_id].add(value)
    return (
        unicode_values[16]
        or unicode_values[1]
        or fallback_values[16]
        or fallback_values[1]
    )


def cmap_subtables(data: bytes, tables: dict[bytes, tuple[int, int]]) -> list[int]:
    location = tables.get(b"cmap")
    if not location:
        return []
    offset, length = location
    if offset + length > len(data) or length < 4:
        return []
    count = unpack_u16(data, offset + 2)
    result: list[int] = []
    for index in range(count):
        record = offset + 4 + index * 8
        if record + 8 > offset + length:
            break
        platform_id, encoding_id, relative = struct.unpack_from(">HHI", data, record)
        subtable = offset + relative
        if subtable + 2 <= len(data) and (
            platform_id == 0 or (platform_id == 3 and encoding_id in {1, 10})
        ):
            result.append(subtable)
    return sorted(set(result))


def cmap_format_4_has(data: bytes, offset: int, codepoint: int) -> bool:
    if codepoint > 0xFFFF or offset + 16 > len(data):
        return False
    length = unpack_u16(data, offset + 2)
    if offset + length > len(data):
        return False
    segment_count = unpack_u16(data, offset + 6) // 2
    end_codes = offset + 14
    start_codes = end_codes + 2 * segment_count + 2
    deltas = start_codes + 2 * segment_count
    range_offsets = deltas + 2 * segment_count
    for index in range(segment_count):
        end_code = unpack_u16(data, end_codes + 2 * index)
        if codepoint > end_code:
            continue
        start_code = unpack_u16(data, start_codes + 2 * index)
        if codepoint < start_code:
            return False
        delta = struct.unpack_from(">h", data, deltas + 2 * index)[0]
        range_offset_position = range_offsets + 2 * index
        range_offset = unpack_u16(data, range_offset_position)
        if range_offset == 0:
            return ((codepoint + delta) & 0xFFFF) != 0
        glyph_position = range_offset_position + range_offset + 2 * (codepoint - start_code)
        if glyph_position + 2 > offset + length:
            return False
        glyph = unpack_u16(data, glyph_position)
        return glyph != 0 and ((glyph + delta) & 0xFFFF) != 0
    return False


def cmap_format_12_has(data: bytes, offset: int, codepoint: int) -> bool:
    if offset + 16 > len(data):
        return False
    length = unpack_u32(data, offset + 4)
    if offset + length > len(data):
        return False
    count = unpack_u32(data, offset + 12)
    low, high = 0, count - 1
    while low <= high:
        middle = (low + high) // 2
        group = offset + 16 + middle * 12
        if group + 12 > offset + length:
            return False
        start, end, start_glyph = struct.unpack_from(">III", data, group)
        if codepoint < start:
            high = middle - 1
        elif codepoint > end:
            low = middle + 1
        else:
            return start_glyph + codepoint - start != 0
    return False


def font_supports(data: bytes, tables: dict[bytes, tuple[int, int]], codepoint: int) -> bool:
    for offset in cmap_subtables(data, tables):
        font_format = unpack_u16(data, offset)
        if font_format == 12 and cmap_format_12_has(data, offset, codepoint):
            return True
        if font_format == 4 and cmap_format_4_has(data, offset, codepoint):
            return True
    return False


def webfont_sfnt(data: bytes) -> bytes:
    """Decode webfonts only; native SFNT/TTC files retain the original readers."""
    if data[:4] not in {b"wOFF", b"wOF2"}:
        return data
    try:
        from fontTools.ttLib import TTFont
    except ImportError as error:
        raise ValueError("WOFF/WOFF2 metadata requires fontTools[woff]") from error
    if data[:4] == b"wOF2":
        try:
            from fontTools.ttLib.woff2 import haveBrotli
        except ImportError as error:
            raise ValueError("WOFF2 metadata requires fontTools[woff] and Brotli") from error
        if not haveBrotli:
            raise ValueError("WOFF2 metadata requires Brotli support from fontTools[woff]")
    try:
        with TTFont(BytesIO(data)) as font:
            font.flavor = None
            output = BytesIO()
            font.save(output)
            return output.getvalue()
    except Exception as error:
        raise ValueError(f"cannot decode webfont to SFNT: {type(error).__name__}: {error}") from error


def font_metadata(paths: list[Path], text: str | None) -> dict[str, Any]:
    if not paths:
        return {
            "resolved_family_names": [],
            "coverage_status": "unavailable",
            "glyph_coverage": None,
            "missing_characters": [],
        }
    required = {
        ord(character)
        for character in text or ""
        if not character.isspace() and not unicodedata.category(character).startswith("C")
    }
    covered: set[int] = set(required)
    families: set[str] = set()
    unsupported_files: list[str] = []
    diagnostics: list[dict[str, str]] = []
    for path in paths:
        face_offset = None
        try:
            data = webfont_sfnt(path.read_bytes())
            offsets = sfnt_offsets(data)
            if not offsets:
                raise ValueError("unsupported or damaged font: no SFNT faces")
            file_families: set[str] = set()
            file_covered = set(required)
            for face_offset in offsets:
                tables = sfnt_tables(data, face_offset)
                names = family_names(data, tables)
                if not names:
                    raise ValueError("font face has no readable family name")
                file_families.update(names)
                # Every face must cover the text; complementary faces cannot hide gaps.
                file_covered.intersection_update(
                    codepoint for codepoint in required if font_supports(data, tables, codepoint)
                )
            families.update(file_families)
            covered.intersection_update(file_covered)
        except Exception as error:
            unsupported_files.append(str(path))
            context = f"SFNT face at offset {face_offset}: " if face_offset is not None else ""
            diagnostics.append({
                "path": str(path),
                "error": context + f"{type(error).__name__}: {error}",
            })
    if unsupported_files:
        coverage_status = "not_supported"
        coverage = None
        missing: list[str] = []
    elif text is None:
        coverage_status = "not_checked"
        coverage = None
        missing = []
    else:
        missing_points = sorted(required - covered)
        missing = [chr(codepoint) for codepoint in missing_points]
        coverage = 1.0 if not required else len(covered) / len(required)
        coverage_status = "complete" if not missing else "missing_glyphs"
    return {
        "resolved_family_names": sorted(families),
        "coverage_status": coverage_status,
        "glyph_coverage": coverage,
        "missing_characters": missing,
        "unsupported_font_files": unsupported_files,
        "font_diagnostics": diagnostics,
    }


def load_web_manifest() -> dict[str, Any]:
    """Load the browser-facing catalog shared with the Infinite Canvas frontend."""
    if not WEB_FONT_MANIFEST.exists():
        raise ValueError("web font manifest is missing")
    data = json.loads(WEB_FONT_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("families"), list) or not data["families"]:
        raise ValueError("web font manifest must contain a nonempty families list")
    for family in data["families"]:
        if not isinstance(family, dict) or not isinstance(family.get("faces"), list) or not family["faces"]:
            raise ValueError("web font family must contain a nonempty faces list")
        if not all(isinstance(face, dict) for face in family["faces"]):
            raise ValueError("web font faces must be objects")
    return data


def select_web_family(manifest: dict[str, Any], query: str) -> dict[str, Any]:
    normalized = query.casefold().strip()
    families = [item for item in manifest.get("families", []) if isinstance(item, dict)]
    exact = [
        item
        for item in families
        if normalized
        in {
            str(item.get("id", "")).casefold().strip(),
            str(item.get("label", "")).casefold().strip(),
            str(item.get("css_family", "")).casefold().strip(),
        }
    ]
    if len(exact) == 1:
        return exact[0]
    partial = [
        item
        for item in families
        if normalized
        and any(
            normalized in str(item.get(key, "")).casefold()
            for key in ("id", "label", "css_family")
        )
    ]
    candidates = exact or partial
    if len(candidates) == 1:
        return candidates[0]
    matches = [
        {
            "id": item.get("id"),
            "label": item.get("label"),
            "css_family": item.get("css_family"),
        }
        for item in candidates[:20]
    ]
    raise ValueError(
        "web font query is ambiguous or missing: "
        + json.dumps(matches, ensure_ascii=False)
    )


def select_web_face(
    family: dict[str, Any],
    weight: int | None,
    style: str,
) -> dict[str, Any]:
    faces = [item for item in family.get("faces", []) if isinstance(item, dict)]
    if weight is None:
        default_id = family.get("default_face_id")
        default = [item for item in faces if item.get("id") == default_id]
        if len(default) == 1:
            return default[0]
        raise ValueError(f"web font {family.get('id')} has no valid default face")
    matches = [
        item
        for item in faces
        if item.get("weight") == weight and item.get("style") == style
    ]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(
        f"web font {family.get('id')} does not provide weight={weight} style={style}"
    )


def css_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_web_font_contract(
    family: dict[str, Any], face: dict[str, Any]
) -> dict[str, Any]:
    if face.get("verified") is not True:
        raise ValueError(f"web font face {face.get('id')} is not verified")
    url = safe_url(str(face.get("url", "")))
    font_family = str(family.get("css_family", "")).strip()
    font_format = str(face.get("format", "")).strip()
    style = str(face.get("style", "normal")).strip()
    weight = face.get("weight")
    if not font_family or font_format not in {"opentype", "truetype", "woff2"}:
        raise ValueError(f"web font face {face.get('id')} has an invalid CSS contract")
    weight_range = face.get("weight_range")
    if type(weight) is not int or not 1 <= weight <= 1000 or style not in {"normal", "italic", "oblique"}:
        raise ValueError("invalid web font weight or style")
    css_weight = str(weight)
    if weight_range is not None:
        if not isinstance(weight_range, dict):
            raise ValueError("invalid web font weight range")
        low, high = weight_range.get("min"), weight_range.get("max")
        if type(low) is not int or type(high) is not int or not 1 <= low <= weight <= high <= 1000:
            raise ValueError("invalid web font weight range")
        css_weight = f"{low} {high}"
    fallbacks = [str(item) for item in family.get("fallbacks", [])]
    generic_families = {"cursive", "fantasy", "monospace", "sans-serif", "serif", "system-ui"}
    stack = [css_string(font_family)] + [
        item if item in generic_families else css_string(item) for item in fallbacks
    ]
    font_face_css = "\n".join(
        [
            "@font-face {",
            f"  font-family: {css_string(font_family)};",
            f"  src: url({css_string(url)}) format({css_string(font_format)});",
            f"  font-weight: {css_weight};",
            f"  font-style: {style};",
            "  font-display: swap;",
            "}",
        ]
    )
    return {
        "family_id": family.get("id"),
        "face_id": face.get("id"),
        "font_family": font_family,
        "font_weight": weight,
        "font_weight_range": weight_range,
        "font_style": style,
        "source": {
            "url": url,
            "format": font_format,
            "crossorigin": "anonymous",
        },
        "font_face_css": font_face_css,
        "font_stack": ", ".join(stack),
    }


def resolve_html(args: argparse.Namespace) -> int:
    """Resolve one allowlisted browser font without downloading it locally."""
    if args.fetch or args.register_package or args.cache_root or args.allow_license_risk:
        raise SystemExit(
            "HTML target uses verified CDN files directly; local package options belong to --target canvas"
        )
    if args.weight is None:
        raise SystemExit("HTML target requires --weight for deterministic face selection")
    try:
        manifest = load_web_manifest()
        family = select_web_family(manifest, args.query)
        face = select_web_face(family, args.weight, args.style)
        contract = build_web_font_contract(family, face)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error)) from error

    probe_results: list[dict[str, Any]] = []
    should_probe = args.check_cdn or args.require_ready
    if should_probe:
        try:
            probe_results.append(probe_entry({"cdn_url": face["url"]}))
        except Exception as error:
            probe_results.append(
                {"url": face.get("url"), "verified": False, "error": str(error)}
            )

    cdn_ready = bool(probe_results) and all(item.get("verified") is True for item in probe_results)
    result = {
        "target": "html",
        "id": family.get("id"),
        "label": family.get("label"),
        "css_family": family.get("css_family"),
        "language_group": family.get("language_group"),
        "package_status": "cdn_ready" if cdn_ready else ("cdn_check_failed" if should_probe else "cdn_listed_not_rechecked"),
        "local_paths": [],
        "absolute_paths": [],
        "cdn_files": [face],
        "cdn_probe": probe_results,
        # Web 模式不下载字体二进制，因此这里只声明未执行逐字 cmap 检查；
        # 真实缺字由渲染验证和 manifest 回退栈兜底，不能伪报 complete。
        "coverage_status": "not_checked",
        "glyph_coverage": None,
        "missing_characters": [],
        "requested_text": args.text,
        "unready_action": None if cdn_ready else "request_user_confirmation",
        "font_contract_entry": None,
        "web_font_contract_entry": contract,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if should_probe and not cdn_ready:
        return 4
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Curated alias, exact font name, unique substring, or catalog id")
    parser.add_argument("--register-package", type=Path, help="Register an acquired font file or directory")
    parser.add_argument("--fetch", action="store_true", help="Download verified CDN files into the local package path")
    parser.add_argument("--check-cdn", action="store_true", help="Probe verified CDN entries without downloading")
    parser.add_argument("--text", help="Real text used to verify glyph coverage after local resolution")
    parser.add_argument("--cache-root", type=Path, help="Alternative root for downloaded packages and testing")
    parser.add_argument("--allow-license-risk", action="store_true", help="Allow fetch when catalog licensing is not permissive")
    parser.add_argument("--require-ready", action="store_true", help="Canvas: require licensed local contract and checked text coverage. HTML: require successful CDN probe; browser rendering and glyph coverage still require verification")
    parser.add_argument("--target", choices=("canvas", "html"), default="canvas")
    parser.add_argument("--weight", type=int, help="Exact HTML font weight")
    parser.add_argument("--style", choices=("normal", "italic"), default="normal")
    args = parser.parse_args()
    if args.target == "html":
        return resolve_html(args)

    storage_root = args.cache_root.resolve() if args.cache_root else ROOT
    record = select(load_records(), args.query)
    curated = next(
        (font for font in load_curated_pool()["fonts"] if font["catalog_id"] == record["id"]),
        None,
    )
    license_ok = license_allows_automatic_fetch(record)
    manifest = load_manifest()
    entries = manifest_entries(manifest, record)

    if args.register_package:
        register(record, args.register_package.resolve(), storage_root)

    probe_results: list[dict[str, Any]] = []
    if args.check_cdn:
        if not entries:
            probe_results = [{"verified": False, "error": "no verified CDN entry"}]
        else:
            for entry in entries:
                try:
                    probe_results.append(probe_entry(entry))
                except Exception as error:
                    probe_results.append({"url": entry.get("cdn_url"), "verified": False, "error": str(error)})

    download_results: list[dict[str, Any]] = []
    fetch_error: str | None = None
    if args.fetch:
        if not entries:
            fetch_error = "no verified CDN entry for this catalog record"
        elif not args.allow_license_risk and not license_ok:
            fetch_error = "automatic fetch blocked by license policy"
        else:
            try:
                download_results = fetch_entries(entries, storage_root)
            except Exception as error:
                fetch_error = str(error)

    paths = local_files(record, storage_root)
    metadata = font_metadata(paths, args.text)
    if paths:
        package_status = ("invalid" if metadata.get("unsupported_font_files") else
                          "blocked_by_license" if not license_ok else "local_present")
    elif entries:
        package_status = "cdn_available"
    else:
        package_status = "not_installed"
    contract_ready = bool(
        paths
        and license_ok
        and metadata["resolved_family_names"]
        and metadata["coverage_status"] == "complete"
        and not metadata.get("unsupported_font_files")
        and not fetch_error
    )
    result = {
        **record,
        "display_name": curated["display_name"] if curated else record.get("name"),
        "catalog_package_status": record.get("package_status"),
        "package_status": package_status,
        "local_paths": [str(path.relative_to(storage_root)) for path in paths],
        "absolute_paths": [str(path) for path in paths],
        "cdn_files": entries,
        "cdn_probe": probe_results,
        "download_results": download_results,
        "fetch_error": fetch_error,
        **metadata,
        "license_status": "catalog_permissive" if license_ok else "review_required",
        "contract_ready": contract_ready,
        "unready_action": None if contract_ready else "request_user_confirmation",
        "render_status": "not_checked",
        "target_environment_status": "not_checked",
        "next_step": (
            "Local resolution is candidate evidence only. Verify the exact family and actual text "
            "in the shot.py / target HTML rendering environment, wait for document.fonts.ready "
            "and inspect the actual rendered family. If the exact requested font is not ready, request "
            "user confirmation before choosing another family. Record the verified family and any "
            "approved fallback in the existing validation record and final HTML; do not create a "
            "standalone font-contract.json unless the task explicitly requires one. Do not embed local "
            "paths, CDN URLs or unapproved @font-face declarations."
        ),
        "font_contract_entry": {
            "family": metadata["resolved_family_names"][0],
            "source": "local",
            "paths": [str(path) for path in paths],
            "catalog_id": record.get("id"),
        } if contract_ready else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if fetch_error:
        return 3
    if args.check_cdn and not all(item.get("verified") is True for item in probe_results):
        return 4
    if args.require_ready and not paths:
        return 2
    if args.require_ready and not license_ok:
        return 6
    if args.require_ready and metadata["coverage_status"] != "complete":
        return 5
    if args.require_ready and not metadata["resolved_family_names"]:
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
