"""Low-level helpers for poking at the parts of an OPC (Office) package.

Everything here works on raw part names and bytes rather than on any object
model, so the pieces can be shared by the schema auditors and the standalone
rule modules without dragging in a heavier dependency.
"""

import os
import posixpath
import re
import stat
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

# Which concrete file extensions belong to which OOXML sub-family.
OOXML_SUFFIX_FAMILY = {
    ".docx": "docx",
    ".dotx": "docx",
    ".pptx": "pptx",
    ".potx": "pptx",
    ".xlsx": "xlsx",
    ".xltx": "xlsx",
}

# Something like "http:" / "mailto:" at the very start of a target string.
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")

SLIDE_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)

# Whitespace the XML spec lets a parser collapse when xml:space is not "preserve".
WS_CHARS = " \t\r\n"


def resolve_part_target(target: str, source_part: str, target_mode: str = "") -> str | None:
    """Turn a relationship Target into an absolute (package-root) part name.

    Returns None for anything that does not name an in-package part (empty
    targets, external mode, or absolute URIs).
    """
    if not target:
        return None
    if target_mode.lower() == "external":
        return None
    if _URI_SCHEME_RE.match(target):
        return None

    target = urllib.parse.unquote(target)

    if "\\" in target:
        raise ValueError(f"relationship target is not a POSIX part name: {target!r}")

    if target.startswith("/"):
        pending = target.lstrip("/")
    else:
        pending = posixpath.join(posixpath.dirname(source_part), target)

    collected: list[str] = []
    for chunk in posixpath.normpath(pending).split("/"):
        if chunk in ("", "."):
            continue
        if chunk == "..":
            if not collected:
                raise ValueError(f"relationship target escapes the package: {target!r}")
            collected.pop()
        else:
            collected.append(chunk)

    if not collected:
        raise ValueError(f"relationship target resolves to nothing: {target!r}")
    return "/".join(collected)


def rels_owner_part(rels_file: Path, unpacked_dir: Path) -> str:
    """Given a ``*.rels`` path, name the part whose relationships it holds."""
    owner_dir = rels_file.parent.parent.relative_to(unpacked_dir)
    return posixpath.join(owner_dir.as_posix(), rels_file.name[: -len(".rels")]).lstrip("./")


def decode_part(data: bytes) -> str:
    """Decode part bytes as UTF-8, tolerating stray bytes rather than crashing."""
    return data.decode("utf-8", "surrogateescape")


def normalized_text(text: str, preserve: bool) -> str:
    """Return the visible text of a run, honouring xml:space semantics."""
    return text if preserve else text.strip(WS_CHARS)


def extract_zip_safely(zf: zipfile.ZipFile, dest: Path) -> None:
    """Unzip *zf* into *dest*, refusing symlinks and path-traversal entries."""
    dest = dest.resolve()
    for member in zf.infolist():
        if stat.S_ISLNK(member.external_attr >> 16):
            raise ValueError(f"symlink archive entry not allowed: {member.filename!r}")
        landing = (dest / member.filename).resolve()
        if not landing.is_relative_to(dest):
            raise ValueError(f"unsafe archive entry: {member.filename!r}")
        zf.extract(member, dest)


def repack_zip(src_dir: Path, out_path: Path) -> None:
    """Zip *src_dir* back into an OPC package at *out_path*, atomically.

    ``[Content_Types].xml`` is written first and stored (not deflated) to match
    what Office writers do, and the finished archive is swapped into place so a
    half-written file can never replace the original.
    """
    payload = sorted(p for p in src_dir.rglob("*") if p.is_file())
    content_types = src_dir / "[Content_Types].xml"
    handle, staging_name = tempfile.mkstemp(
        prefix=out_path.name + ".", suffix=".tmp", dir=out_path.parent
    )
    staging = Path(staging_name)
    try:
        with os.fdopen(handle, "wb") as fh:
            with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as zf:
                if content_types.exists():
                    zf.write(
                        content_types,
                        content_types.relative_to(src_dir),
                        compress_type=zipfile.ZIP_STORED,
                    )
                for entry in payload:
                    if entry == content_types:
                        continue
                    zf.write(entry, entry.relative_to(src_dir))
        if out_path.exists():
            perm = out_path.stat().st_mode & 0o777
        else:
            umask = os.umask(0)
            os.umask(umask)
            perm = 0o666 & ~umask
        os.chmod(staging, perm)
        os.replace(staging, out_path)
    finally:
        if staging.exists():
            staging.unlink()
