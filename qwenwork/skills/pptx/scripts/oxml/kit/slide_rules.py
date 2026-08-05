"""Recognise the slide-XML defects PowerPoint refuses to open the file over.

lxml reports a wide spectrum of schema complaints; most are cosmetic and Office
opens the deck regardless. This module is an allow-through denylist: only the
message signatures listed below are treated as fatal, so an unfamiliar error is
ignored (a miss) rather than raised as a false alarm.
"""

from __future__ import annotations

import re

SLIDE_PART_PATTERN = re.compile(
    r"ppt/(slides|slideLayouts|slideMasters|notesSlides|notesMasters|handoutMasters)"
    r"/[^/]+\.xml"
)

# (message signature, plain-language explanation). Order is not significant; the
# first signature that matches a given error wins.
SLIDE_FAULT_TABLE: tuple[tuple[re.Pattern[str], str], ...] = (
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
    """True when the string reads like an lxml schema verdict, not a crash."""
    return error.startswith("Element ")


def fatal_slide_faults(errors: set[str]) -> list[str]:
    """Keep only the errors that map to a known fatal defect, annotated."""
    findings: list[str] = []
    for error in sorted(errors):
        for signature, meaning in SLIDE_FAULT_TABLE:
            if signature.search(error):
                findings.append(f"{meaning}: {error}")
                break
    return findings
