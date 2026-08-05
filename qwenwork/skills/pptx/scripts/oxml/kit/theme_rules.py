"""Detect masters that share a theme part the way PowerPoint refuses to open.

Reporting only. The remedy is always to move <p:notesMasterIdLst> back to
directly after <p:sldIdLst> in ppt/presentation.xml, which makes the shared
reference inert again.
"""

from __future__ import annotations

import posixpath
import re
from typing import Mapping

from . import decode_part

THEME_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"

NOTES_MASTER_PREFIX = "ppt/notesMasters/"

_PRESENTATION_PART = "ppt/presentation.xml"

_MASTER_PART = re.compile(
    r"^ppt/(?P<group>slideMasters|notesMasters|handoutMasters)/"
    r"(?:slide|notes|handout)Master(?P<num>\d+)\.xml$"
)
_GROUP_RANK = {"slideMasters": 0, "notesMasters": 1, "handoutMasters": 2}

_RELATIONSHIP = re.compile(
    r"<Relationship\b[^>]*?(?:/>|>.*?</Relationship\s*>)", re.DOTALL
)
_STRIP_IGNORABLE = re.compile(r"<!--.*?-->|<\?.*?\?>", re.DOTALL)
_ELEMENT_AFTER_SLDIDLST = re.compile(
    r"<p:sldIdLst\b(?:[^>]*/>|[^>]*>.*?</p:sldIdLst\s*>)\s*(<[^>\s/]+)", re.DOTALL
)


def _ordering(name: str) -> tuple[int, int]:
    m = _MASTER_PART.match(name)
    assert m is not None
    return (_GROUP_RANK[m.group("group")], int(m.group("num")))


def _rels_for(part: str) -> str:
    directory, base = posixpath.split(part)
    return f"{directory}/_rels/{base}.rels"


def _absolutize(rels_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    part_dir = posixpath.dirname(posixpath.dirname(rels_path))
    return posixpath.normpath(posixpath.join(part_dir, target))


def _theme_of(files: Mapping[str, bytes], master: str):
    rels_path = _rels_for(master)
    rels = files.get(rels_path)
    if rels is None:
        return None
    for element in _RELATIONSHIP.findall(decode_part(rels)):
        if f'Type="{THEME_REL_TYPE}"' not in element:
            continue
        target = re.search(r'\bTarget="([^"]+)"', element)
        if target is None:
            continue
        return rels_path, element, _absolutize(rels_path, target.group(1))
    return None


def _all_masters(files: Mapping[str, bytes]) -> list[str]:
    return sorted((n for n in files if _MASTER_PART.match(n)), key=_ordering)


def _notes_share_is_inert(files: Mapping[str, bytes]) -> bool:
    data = files.get(_PRESENTATION_PART)
    if data is None:
        return False
    match = _ELEMENT_AFTER_SLDIDLST.search(_STRIP_IGNORABLE.sub("", decode_part(data)))
    return match is not None and match.group(1) == "<p:notesMasterIdLst"


def _collisions(files: Mapping[str, bytes]):
    first_owner: dict[str, str] = {}
    for master in _all_masters(files):
        found = _theme_of(files, master)
        if found is None:
            continue
        rels_path, element, theme = found
        if theme not in files:
            continue
        if theme in first_owner:
            yield master, rels_path, element, theme, first_owner[theme]
        else:
            first_owner[theme] = master


def _inert_here(master: str, notes_inert: bool) -> bool:
    return notes_inert and master.startswith(NOTES_MASTER_PREFIX)


def all_theme_collisions(files: Mapping[str, bytes]) -> list[str]:
    """Every master that reuses an earlier master's theme part."""
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _collisions(files)
    ]


def active_theme_collisions(files: Mapping[str, bytes]) -> list[str]:
    """Only the collisions PowerPoint actually chokes on (skipping inert ones)."""
    notes_inert = _notes_share_is_inert(files)
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _collisions(files)
        if not _inert_here(master, notes_inert)
    ]
