"""Hash-based output dir resolution.

The contract is simple: given an input file, produce a deterministic
output directory so that repeat ``preview render`` calls on an unchanged
file return the same path. The model can rely on the path being stable
across calls.

We hash the *full file content* (not mtime), so any byte change
invalidates the cache. For typical artifact sizes (≤ 50 MB) the SHA-256
cost is dwarfed by the rendering cost itself; using mtime would be
faster but unsafe under git checkouts and tar extraction.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from . import _common

# Files larger than this are hashed in 64KB-prefix mode + size sentinel,
# trading off determinism for speed. 100 MB is well above the typical
# artifact budget; anything bigger is almost certainly not a deliverable.
_FULL_HASH_MAX_BYTES = 100 * 1024 * 1024


def _hash_file_full(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _hash_file_prefix(path: Path, size: int) -> str:
    """Fallback for huge files: 64KB prefix + 64KB suffix + size."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read(65536))
        if size > 131072:
            fh.seek(max(0, size - 65536))
            h.update(fh.read(65536))
    h.update(str(size).encode())
    return h.hexdigest()


def compute_source_hash(path: str | Path) -> str:
    """Return a 12-hex-char content hash for ``path``.

    Raises FileNotFoundError if the path does not exist.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"not a file: {p}")
    size = p.stat().st_size
    if size <= _FULL_HASH_MAX_BYTES:
        digest = _hash_file_full(p)
    else:
        digest = _hash_file_prefix(p, size)
    return digest[:12]


def default_output_root() -> Path:
    """Resolve the default ``.preview/`` directory.

    Lookup order:
      1. ``ARTIFACT_PREVIEW_HOME`` environment variable
      2. CWD ``./.preview/`` if CWD is writable
      3. ``$HOME/.preview/`` as a last resort
    """
    env = os.environ.get("ARTIFACT_PREVIEW_HOME")
    if env:
        return Path(_common.logical_abspath(env))
    # logical_cwd(), not Path.cwd(): the latter collapses the workspace symlink
    # and the sandbox bind mount, so every path we report back would carry a
    # prefix the caller never used.
    cwd = Path(_common.logical_cwd())
    if os.access(cwd, os.W_OK):
        return cwd / ".preview"
    return Path(_common.logical_abspath(Path.home() / ".preview"))


def resolve_output_dir(
    source_path: str | Path,
    output_root: str | Path | None = None,
    *,
    source_hash: str | None = None,
) -> tuple[Path, str]:
    """Compute (output_dir, source_hash) for a given input file.

    ``output_root`` defaults to :func:`default_output_root` when None.
    The output dir is ``<root>/<hash>/`` and is NOT created here —
    :func:`dispatch.render` does that.
    """
    src = Path(source_path)
    sh = source_hash or compute_source_hash(src)
    root = (Path(_common.logical_abspath(output_root)) if output_root
            else default_output_root())
    out_dir = root / sh
    return out_dir, sh
