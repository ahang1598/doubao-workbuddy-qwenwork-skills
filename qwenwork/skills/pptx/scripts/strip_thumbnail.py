#!/usr/bin/env python3
"""Strip the blank placeholder thumbnail from an existing .pptx (in place).

python-pptx's built-in template ships a blank ``docProps/thumbnail.jpeg``. When a
deck is saved with a bare ``prs.save()`` (or a buggy save wrapper) this placeholder
is kept, and product preview cards render it as a plain white image. This tool
removes the thumbnail part *and* its ``_rels/.rels`` relationship, so the preview
falls back to a real first-slide render / text summary.

It only rewrites files that actually carry a thumbnail, and never touches slide
content, layouts, themes, media, or any other package part.

Usage:
    python strip_thumbnail.py <deck.pptx> [more.pptx ...]
"""

import os
import re
import shutil
import sys
import zipfile

THUMB_PREFIX = "docprops/thumbnail."
THUMB_REL_RE = re.compile(rb'<Relationship[^>]*Type="[^"]*/thumbnail"[^>]*/>')


def strip_thumbnail(path: str) -> bool:
    """Remove the placeholder thumbnail from ``path``. Returns True if modified."""
    if not path.lower().endswith(".pptx"):
        print(f"skip (not .pptx): {path}")
        return False
    if not os.path.isfile(path):
        print(f"skip (not found): {path}")
        return False

    with zipfile.ZipFile(path, "r") as zin:
        names = zin.namelist()
    if not any(n.lower().startswith(THUMB_PREFIX) for n in names):
        print(f"ok (no thumbnail): {path}")
        return False

    tmp = path + ".tmp"
    with zipfile.ZipFile(path, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            name = info.filename
            # 1) drop the blank thumbnail entry
            if name.lower().startswith(THUMB_PREFIX):
                continue
            data = zin.read(name)
            # 2) remove the thumbnail relationship from the package .rels
            if name == "_rels/.rels":
                data = THUMB_REL_RE.sub(b"", data)
            zout.writestr(info, data)
    shutil.move(tmp, path)
    print(f"stripped thumbnail: {path}")
    return True


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    changed = 0
    for p in argv[1:]:
        try:
            if strip_thumbnail(p):
                changed += 1
        except Exception as exc:  # noqa: BLE001 - report and continue with other files
            print(f"error: {p}: {exc}")
    print(f"done: {changed} file(s) modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
