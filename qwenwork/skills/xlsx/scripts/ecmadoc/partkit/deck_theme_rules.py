"""Spot masters that share a single theme part in a way PowerPoint won't open.

This module only reports; the remedy (moving ``<p:notesMasterIdLst>`` back to
directly after ``<p:sldIdLst>`` in ``ppt/presentation.xml``) is left to the
caller.
"""


from __future__ import annotations

import posixpath
import re
from typing import Mapping

from . import decode_part

THEME_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
)

_MASTER_PART_RE = re.compile(
    r"^ppt/(?P<group>slideMasters|notesMasters|handoutMasters)/"
    r"(?:slide|notes|handout)Master(?P<num>\d+)\.xml$"
)
_GROUP_RANK = {"slideMasters": 0, "notesMasters": 1, "handoutMasters": 2}

_REL_ELEMENT_RE = re.compile(
    r"<Relationship\b[^>]*?(?:/>|>.*?</Relationship\s*>)", re.DOTALL
)


def _master_sort_key(name: str) -> tuple[int, int]:
    matched = _MASTER_PART_RE.match(name)
    assert matched is not None
    return (_GROUP_RANK[matched.group("group")], int(matched.group("num")))


def _rels_for(part: str) -> str:
    directory, base = posixpath.split(part)
    return f"{directory}/_rels/{base}.rels"


def _resolve_target(rels_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    part_dir = posixpath.dirname(posixpath.dirname(rels_path))
    return posixpath.normpath(posixpath.join(part_dir, target))


def _theme_link(files: Mapping[str, bytes], master: str):
    rels_path = _rels_for(master)
    rels = files.get(rels_path)
    if rels is None:
        return None
    for element in _REL_ELEMENT_RE.findall(decode_part(rels)):
        if f'Type="{THEME_RELATIONSHIP}"' not in element:
            continue
        target = re.search(r'\bTarget="([^"]+)"', element)
        if target is None:
            continue
        return rels_path, element, _resolve_target(rels_path, target.group(1))
    return None


def _all_masters(files: Mapping[str, bytes]) -> list[str]:
    return sorted((n for n in files if _MASTER_PART_RE.match(n)), key=_master_sort_key)


_PRESENTATION_PART = "ppt/presentation.xml"
_NOTES_MASTER_PREFIX = "ppt/notesMasters/"
_NOISE_RE = re.compile(r"<!--.*?-->|<\?.*?\?>", re.DOTALL)
_NEXT_AFTER_SLDIDLST_RE = re.compile(
    r"<p:sldIdLst\b(?:[^>]*/>|[^>]*>.*?</p:sldIdLst\s*>)\s*(<[^>\s/]+)", re.DOTALL
)


def _notes_share_is_harmless(files: Mapping[str, bytes]) -> bool:
    data = files.get(_PRESENTATION_PART)
    if data is None:
        return False
    match = _NEXT_AFTER_SLDIDLST_RE.search(_NOISE_RE.sub("", decode_part(data)))
    return match is not None and match.group(1) == "<p:notesMasterIdLst"


def _iter_theme_collisions(files: Mapping[str, bytes]):
    seen: dict[str, str] = {}
    for master in _all_masters(files):
        link = _theme_link(files, master)
        if link is None:
            continue
        rels_path, element, theme = link
        if theme not in files:
            continue
        if theme in seen:
            yield master, rels_path, element, theme, seen[theme]
        else:
            seen[theme] = master


def _is_harmless(master: str, harmless_notes: bool) -> bool:
    return harmless_notes and master.startswith(_NOTES_MASTER_PREFIX)


def all_theme_collisions(files: Mapping[str, bytes]) -> list[str]:
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _iter_theme_collisions(files)
    ]


def active_theme_collisions(files: Mapping[str, bytes]) -> list[str]:
    harmless_notes = _notes_share_is_harmless(files)
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _iter_theme_collisions(files)
        if not _is_harmless(master, harmless_notes)
    ]
