"""Sift slide-XML schema errors down to the ones PowerPoint actually rejects.

The match table is a denylist over lxml's error messages: an error class we do
not recognise is treated as a miss (no false alarm) rather than a failure.
"""


from __future__ import annotations

import re

SLIDE_PART_PATTERN = re.compile(
    r"ppt/(slides|slideLayouts|slideMasters|notesSlides|notesMasters|handoutMasters)"
    r"/[^/]+\.xml"
)

REFUSED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\}tableStyleId': This element is not expected"),
        "two <a:tableStyleId> in one <a:tblPr> (the schema allows one)",
    ),
    (
        re.compile(r"\}srgbClr', attribute 'val'"),
        "a colour that is not six hex digits",
    ),
    (
        re.compile(r"\}txBody': Missing child element"),
        "a <p:txBody> with no children",
    ),
    (
        re.compile(r"\}miter', attribute 'lim'"),
        'a line join with lim="NaN"',
    ),
    (
        re.compile(r"\}uLnTx': This element is not expected"),
        "<a:uLnTx> in a position the schema forbids",
    ),
    (
        re.compile(r"\}overrideClrMapping': This element is not expected"),
        "<p:overrideClrMapping> in a position the schema forbids",
    ),
    (
        re.compile(r"\}nvGrpSpPr': Missing child element"),
        "a <p:nvGrpSpPr> with no children",
    ),
)


def is_schema_message(error: str) -> bool:
    return error.startswith("Element ")


def refused_slide_errors(errors: set[str]) -> list[str]:
    hits = []
    for error in sorted(errors):
        for pattern, meaning in REFUSED_PATTERNS:
            if pattern.search(error):
                hits.append(f"{meaning}: {error}")
                break
    return hits
