#!/usr/bin/env python3
"""Validate and build a deterministic one-wrapper-directory release ZIP."""

from __future__ import annotations

import stat
import sys
import zipfile
from pathlib import Path

from validate_suite import SUITE_ROOT, validate


SKIP_PARTS = {"dist", "__pycache__"}
SKIP_NAMES = {".DS_Store"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def iter_release_files(root: Path):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or SKIP_PARTS.intersection(relative.parts) or path.name in SKIP_NAMES or path.suffix == ".pyc":
            continue
        yield path, relative


def build():
    errors = validate(SUITE_ROOT)
    if errors:
        raise SystemExit("validation failed before packaging:\n- " + "\n- ".join(errors))
    target = SUITE_ROOT / "dist" / f"{SUITE_ROOT.name}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in iter_release_files(SUITE_ROOT):
            info = zipfile.ZipInfo(f"{SUITE_ROOT.name}/{relative.as_posix()}", FIXED_TIME)
            mode = 0o755 if path.suffix == ".py" else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    if target.stat().st_size > 50 * 1024 * 1024:
        raise SystemExit("release ZIP exceeds 50 MB")
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
        required = f"{SUITE_ROOT.name}/.qoder-plugin/plugin.json"
        if required not in names:
            raise SystemExit("release ZIP is missing the plugin manifest")
        if any(not name.startswith(f"{SUITE_ROOT.name}/") for name in names):
            raise SystemExit("release ZIP has more than one wrapper root")
    print(f"built {target} ({target.stat().st_size} bytes, {len(names)} files)")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(exc, file=sys.stderr)
        raise
