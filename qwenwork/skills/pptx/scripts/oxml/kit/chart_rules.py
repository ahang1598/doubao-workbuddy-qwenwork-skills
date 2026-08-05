"""Flag chart XML that the schema accepts but PowerPoint quietly discards.

Two faults are covered:
  1. stacked bar/column data labels positioned where Office only allows a few
     values;
  2. chart groups whose <c:axId> references do not resolve to two live axes.

Detection only -- each fault has more than one valid repair, and only the
author knows which was intended.
"""

from __future__ import annotations

import re
from typing import Mapping

from . import decode_part

_CHART_PART = re.compile(r"ppt/charts/chart\d+\.xml")

_GROUPING = re.compile(r"""<c:grouping\b[^>]*?\bval=["'](\w+)["']""")
_DLBL_POS = re.compile(r"""<c:dLblPos\b[^>]*?\bval=["'](\w+)["']""")
_BAR_GROUP = re.compile(r"<c:(bar3DChart|barChart)\b[^>]*(?<!/)>.*?</c:\1\s*>", re.DOTALL)

_STACKED_GROUPINGS = frozenset({"stacked", "percentStacked"})
_FORBIDDEN_ON_STACKED = frozenset({"outEnd"})
_ALLOWED_ON_STACKED = ("ctr", "inEnd", "inBase")

_ANY_CHART_GROUP = re.compile(r"<c:(\w+Chart)\b[^>]*(?<!/)>.*?</c:\1\s*>", re.DOTALL)
_AXID = re.compile(
    r"""\s*<c:axId\b[^>]*?\bval=["'](-?\d+)["']\s*(?:/>|>\s*</c:axId\s*>)"""
)
_AXIS_DECL = re.compile(
    r"""<c:(catAx|valAx|serAx|dateAx)\b[^>]*(?<!/)>\s*<c:axId\b[^>]*?\bval=["'](-?\d+)["']"""
)

# How many axes a group may declare, and the minimum it must resolve to.
_AXID_CEILING = {
    "barChart": 2, "lineChart": 2, "areaChart": 2, "scatterChart": 2,
    "bubbleChart": 2, "radarChart": 2, "stockChart": 2,
    "bar3DChart": 3, "line3DChart": 3, "area3DChart": 3,
    "surfaceChart": 3, "surface3DChart": 3,
}
_AXID_FLOOR = {
    "barChart": 2, "lineChart": 2, "areaChart": 2, "scatterChart": 2,
    "bubbleChart": 2, "radarChart": 2, "stockChart": 2,
    "bar3DChart": 2, "area3DChart": 2, "surfaceChart": 2,
    "line3DChart": 3, "surface3DChart": 3,
}


def _extlst_spans(text: str) -> list[tuple[int, int]]:
    """Byte spans of top-level <c:extLst>...</c:extLst> regions (nesting-aware)."""
    spans: list[tuple[int, int]] = []
    depth = 0
    start = 0
    for match in re.finditer(r"<(/?)c:extLst\b[^>]*?(/?)>", text):
        closing, self_closing = match.group(1), match.group(2)
        if self_closing:
            continue
        if closing:
            depth -= 1
            if depth == 0:
                spans.append((start, match.end()))
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    return spans


def _without_extlst(text: str) -> str:
    kept, cursor = [], 0
    for lo, hi in _extlst_spans(text):
        kept.append(text[cursor:lo])
        cursor = hi
    kept.append(text[cursor:])
    return "".join(kept)


def _stacked_label_faults(part: str, xml: str) -> list[str]:
    faults: list[str] = []
    for match in _BAR_GROUP.finditer(xml):
        block = _without_extlst(match.group(0))
        group = match.group(1)

        grouping = _GROUPING.search(block)
        if grouping is None or grouping.group(1) not in _STACKED_GROUPINGS:
            continue

        offenders = [p for p in _DLBL_POS.findall(block) if p in _FORBIDDEN_ON_STACKED]
        for pos in sorted(set(offenders)):
            faults.append(
                f'{part}: {offenders.count(pos)} data label(s) use dLblPos="{pos}" on a '
                f"{grouping.group(1)} {group}; PowerPoint allows only "
                f"{', '.join(_ALLOWED_ON_STACKED)} there"
            )
    return faults


def _declared_axes(xml: str) -> dict[str, list[str]]:
    axes: dict[str, list[str]] = {}
    for kind, axid in _AXIS_DECL.findall(xml):
        axes.setdefault(kind, []).append(axid)
    return axes


def _canonical_ids(axes: dict[str, list[str]], ceiling: int) -> list[str] | None:
    category = axes.get("catAx", []) + axes.get("dateAx", [])
    value = axes.get("valAx", [])
    series = axes.get("serAx", [])
    if len(category) != 1 or len(value) != 1 or len(series) > 1:
        return None
    ids = [category[0], value[0]]
    if ceiling >= 3 and series:
        ids.append(series[0])
    return ids


def _unresolved_axes(kind: str, block: str, axes: dict[str, list[str]]) -> list[str] | None:
    if kind not in _AXID_CEILING:
        return None
    ids = _AXID.findall(block)
    declared = {i for group in axes.values() for i in group}
    if len([i for i in ids if i in declared]) >= 2:
        return None
    return ids


def _axis_reference_faults(part: str, xml: str) -> list[str]:
    axes = _declared_axes(xml)
    declared = {i for group in axes.values() for i in group}
    faults: list[str] = []
    for match in _ANY_CHART_GROUP.finditer(xml):
        kind, block = match.group(1), match.group(0)
        ids = _unresolved_axes(kind, block, axes)
        if ids is None:
            continue
        if not ids:
            faults.append(
                f"{part}: <c:{kind}> declares no <c:axId> this part can resolve; a chart "
                f"group needs {_AXID_FLOOR[kind]}, and PowerPoint discards one with fewer"
            )
            continue
        dead = [i for i in ids if i not in declared]
        canonical = _canonical_ids(axes, _AXID_CEILING[kind])
        if canonical is not None and len(canonical) >= _AXID_FLOOR[kind]:
            hint = f"Fix: point them at the axes this part declares ({', '.join(canonical)})"
        else:
            hint = ("Fix: the part declares several axes of a kind -- declare the "
                    "secondary axes the series expects, or drop them")
        detail = (f"of which {', '.join(dead)} name no declared axis"
                  if dead else f"only {len(ids)} of which this part declares")
        faults.append(
            f"{part}: <c:{kind}> references axId {', '.join(ids)}, {detail}, "
            f"leaving fewer than two live axes; PowerPoint discards the chart. {hint}"
        )
    return faults


_CHART_CHECKS = (_stacked_label_faults, _axis_reference_faults)


def scan_chart_faults(files: Mapping[str, bytes]) -> list[str]:
    """Run every chart check across the package's chart parts."""
    faults: list[str] = []
    for part in sorted(n for n in files if _CHART_PART.fullmatch(n)):
        xml = decode_part(files[part])
        for check in _CHART_CHECKS:
            faults.extend(check(part, xml))
    return faults
