"""Flag chart XML that the schema accepts but PowerPoint still refuses to draw.

Detection only: each fault has more than one plausible repair, and only the
author knows which was intended, so we describe the problem and stop there.
"""


from __future__ import annotations

import re
from typing import Mapping

from . import decode_part


_CHART_PART_PATTERN = re.compile(r"ppt/charts/chart\d+\.xml")

_GROUPING_RE = re.compile(r"""<c:grouping\b[^>]*?\bval=["'](\w+)["']""")
_LABEL_POS_RE = re.compile(r"""<c:dLblPos\b[^>]*?\bval=["'](\w+)["']""")


def _ext_lst_spans(text: str) -> list[tuple[int, int]]:
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


def _without_ext_lst(text: str) -> str:
    pieces, cursor = [], 0
    for lo, hi in _ext_lst_spans(text):
        pieces.append(text[cursor:lo])
        cursor = hi
    pieces.append(text[cursor:])
    return "".join(pieces)


_BAR_BLOCK_RE = re.compile(r"<c:(bar3DChart|barChart)\b[^>]*(?<!/)>.*?</c:\1\s*>", re.DOTALL)

STACKED_KINDS = frozenset({"stacked", "percentStacked"})
BANNED_ON_STACKED = frozenset({"outEnd"})
ALLOWED_ON_STACKED = ("ctr", "inEnd", "inBase")


def _stacked_label_defects(part: str, xml: str) -> list[str]:
    defects: list[str] = []
    for match in _BAR_BLOCK_RE.finditer(xml):
        block = _without_ext_lst(match.group(0))
        group = match.group(1)

        grouping = _GROUPING_RE.search(block)
        if grouping is None or grouping.group(1) not in STACKED_KINDS:
            continue

        bad = [p for p in _LABEL_POS_RE.findall(block) if p in BANNED_ON_STACKED]
        for pos in sorted(set(bad)):
            defects.append(
                f'{part}: {bad.count(pos)} data label(s) use dLblPos="{pos}" on a '
                f"{grouping.group(1)} {group}; PowerPoint allows only "
                f"{', '.join(ALLOWED_ON_STACKED)} there"
            )
    return defects



_CHART_BLOCK_RE = re.compile(r"<c:(\w+Chart)\b[^>]*(?<!/)>.*?</c:\1\s*>", re.DOTALL)

_AXID_REF_RE = re.compile(
    r"""\s*<c:axId\b[^>]*?\bval=["'](-?\d+)["']\s*(?:/>|>\s*</c:axId\s*>)"""
)

_AXIS_DECL_RE = re.compile(
    r"""<c:(catAx|valAx|serAx|dateAx)\b[^>]*(?<!/)>\s*<c:axId\b[^>]*?\bval=["'](-?\d+)["']"""
)

AXIS_CAP = {
    "barChart": 2, "lineChart": 2, "areaChart": 2, "scatterChart": 2,
    "bubbleChart": 2, "radarChart": 2, "stockChart": 2,
    "bar3DChart": 3, "line3DChart": 3, "area3DChart": 3,
    "surfaceChart": 3, "surface3DChart": 3,
}

AXIS_FLOOR = {
    "barChart": 2, "lineChart": 2, "areaChart": 2, "scatterChart": 2,
    "bubbleChart": 2, "radarChart": 2, "stockChart": 2,
    "bar3DChart": 2, "area3DChart": 2, "surfaceChart": 2,
    "line3DChart": 3, "surface3DChart": 3,
}


def _declared_axes(xml: str) -> dict[str, list[str]]:
    axes: dict[str, list[str]] = {}
    for kind, axid in _AXIS_DECL_RE.findall(xml):
        axes.setdefault(kind, []).append(axid)
    return axes


def _canonical_axis_ids(axes: dict[str, list[str]], limit: int) -> list[str] | None:
    category = axes.get("catAx", []) + axes.get("dateAx", [])
    value = axes.get("valAx", [])
    series = axes.get("serAx", [])
    if len(category) != 1 or len(value) != 1 or len(series) > 1:
        return None
    ids = [category[0], value[0]]
    if limit >= 3 and series:
        ids.append(series[0])
    return ids


def _unresolved_axis_ids(kind: str, block: str, axes: dict[str, list[str]]) -> list[str] | None:
    if kind not in AXIS_CAP:
        return None
    ids = _AXID_REF_RE.findall(block)
    declared = {i for group in axes.values() for i in group}
    if len([i for i in ids if i in declared]) >= 2:
        return None
    return ids


def _axis_reference_defects(part: str, xml: str) -> list[str]:
    axes = _declared_axes(xml)
    defects: list[str] = []
    declared = {i for group in axes.values() for i in group}
    for match in _CHART_BLOCK_RE.finditer(xml):
        kind, block = match.group(1), match.group(0)
        ids = _unresolved_axis_ids(kind, block, axes)
        if ids is None:
            continue
        if not ids:
            defects.append(
                f"{part}: <c:{kind}> declares no <c:axId> this part can resolve; a chart "
                f"group needs {AXIS_FLOOR[kind]}, and PowerPoint discards one with fewer"
            )
            continue
        dead = [i for i in ids if i not in declared]
        canonical = _canonical_axis_ids(axes, AXIS_CAP[kind])
        if canonical is not None and len(canonical) >= AXIS_FLOOR[kind]:
            hint = f"Fix: point them at the axes this part declares ({', '.join(canonical)})"
        else:
            hint = ("Fix: the part declares several axes of a kind -- declare the "
                    "secondary axes the series expects, or drop them")
        detail = (f"of which {', '.join(dead)} name no declared axis"
                  if dead else f"only {len(ids)} of which this part declares")
        defects.append(
            f"{part}: <c:{kind}> references axId {', '.join(ids)}, {detail}, "
            f"leaving fewer than two live axes; PowerPoint discards the chart. {hint}"
        )
    return defects


CHART_CHECKS = (_stacked_label_defects, _axis_reference_defects)


def collect_chart_defects(files: Mapping[str, bytes]) -> list[str]:
    defects: list[str] = []
    for part in sorted(n for n in files if _CHART_PART_PATTERN.fullmatch(n)):
        xml = decode_part(files[part])
        for check in CHART_CHECKS:
            defects.extend(check(part, xml))
    return defects
