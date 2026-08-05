"""Shared low-level helpers for reading and rewriting OOXML packages.

Everything here is dependency-light and side-effect free (apart from the two
zip helpers that touch disk). The higher layers -- the auditors and the
command-line entry points -- lean on this module rather than duplicating the
OPC part-name arithmetic.
"""

import os
import posixpath
import re
import stat
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

# Suffix -> logical document family. Templates map to the same family as their
# editable counterpart so callers can treat .potx like .pptx and so on.
PACKAGE_FAMILIES = {
    ".docx": "docx",
    ".dotx": "docx",
    ".pptx": "pptx",
    ".potx": "pptx",
    ".xlsx": "xlsx",
    ".xltx": "xlsx",
}

REL_SLIDE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"

# Characters XML treats as insignificant whitespace when xml:space is default.
WS_CHARS = " \t\r\n"

_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def resolve_part(target: str, source_part: str, target_mode: str = "") -> str | None:
    """Turn a relationship Target into an absolute package part name.

    Returns None for the cases that name nothing inside the package: empty
    targets, ones flagged External, and absolute URIs (http:, mailto:, ...).
    """
    if not target or target_mode.lower() == "external" or _URI_SCHEME.match(target):
        return None

    target = urllib.parse.unquote(target)
    if "\\" in target:
        raise ValueError(f"relationship target is not a POSIX part name: {target!r}")

    rooted = target.startswith("/")
    joined = target.lstrip("/") if rooted else posixpath.join(
        posixpath.dirname(source_part), target
    )

    resolved: list[str] = []
    for segment in posixpath.normpath(joined).split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if not resolved:
                raise ValueError(f"relationship target escapes the package: {target!r}")
            resolved.pop()
        else:
            resolved.append(segment)

    if not resolved:
        raise ValueError(f"relationship target resolves to nothing: {target!r}")
    return "/".join(resolved)


def rels_owner_part(rels_file: Path, unpacked_dir: Path) -> str:
    """Given a .rels file, name the part it describes (its owner)."""
    owner_dir = rels_file.parent.parent.relative_to(unpacked_dir)
    stem = rels_file.name[: -len(".rels")]
    return posixpath.join(owner_dir.as_posix(), stem).lstrip("./")


def decode_part(data: bytes) -> str:
    """Decode raw part bytes to text, keeping undecodable bytes recoverable."""
    return data.decode("utf-8", "surrogateescape")


def normalize_ws(text: str, preserve: bool) -> str:
    """Apply xml:space semantics: strip edge whitespace unless preserve is set."""
    return text if preserve else text.strip(WS_CHARS)


def unzip_guarded(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract a zip, rejecting symlink entries and any path escaping dest."""
    dest = dest.resolve()
    for member in zf.infolist():
        if stat.S_ISLNK(member.external_attr >> 16):
            raise ValueError(f"symlink archive entry not allowed: {member.filename!r}")
        landing = (dest / member.filename).resolve()
        if not landing.is_relative_to(dest):
            raise ValueError(f"unsafe archive entry: {member.filename!r}")
        zf.extract(member, dest)


def repack(src_dir: Path, out_path: Path) -> None:
    """Zip an unpacked package back up, atomically, mirroring OPC conventions.

    [Content_Types].xml is written first and stored uncompressed, matching how
    Office writers lay out the archive; the result is swapped into place via a
    temp file so a failure never leaves a half-written deck behind.
    """
    payload = sorted(p for p in src_dir.rglob("*") if p.is_file())
    content_types = src_dir / "[Content_Types].xml"

    handle, tmp_name = tempfile.mkstemp(
        prefix=out_path.name + ".", suffix=".tmp", dir=out_path.parent
    )
    staging = Path(tmp_name)
    try:
        with os.fdopen(handle, "wb") as fh:
            with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as zf:
                if content_types.exists():
                    zf.write(
                        content_types,
                        content_types.relative_to(src_dir),
                        compress_type=zipfile.ZIP_STORED,
                    )
                for member in payload:
                    if member == content_types:
                        continue
                    zf.write(member, member.relative_to(src_dir))

        if out_path.exists():
            perms = out_path.stat().st_mode & 0o777
        else:
            current = os.umask(0)
            os.umask(current)
            perms = 0o666 & ~current
        os.chmod(staging, perms)
        os.replace(staging, out_path)
    finally:
        if staging.exists():
            staging.unlink()
