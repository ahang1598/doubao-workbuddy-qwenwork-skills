#!/usr/bin/env python3
"""Print a concise formatting checklist for common gongwen document types."""

from __future__ import annotations

import argparse
import sys

CHECKLISTS = {
    "standard": [
        "A4 page, top margin 37 mm, left binding margin 28 mm, core area 156 x 225 mm.",
        "Default body font is 3rd-size Fangsong; title uses 2nd-size Xiaobiao Song.",
        "Use 22 lines per page and 28 characters per line when possible.",
        "Place issuing authority mark in red and center it near the top of page one.",
        "Put document number two lines below the authority mark; add signatory on the same line when required.",
        "Insert a red separator line 4 mm below the document number.",
        "Title goes two lines below the red line; main recipient goes one line below the title.",
        "Body starts one line below the main recipient; first page must show body text.",
        "Attachment note, signature, date, seal, note, and footer follow the standard order.",
        "Footer includes copied units, issuing office, print date, and proper separator lines when applicable.",
    ],
    "letter": [
        "Authority mark is centered 30 mm from page top.",
        "Use red double lines at top and bottom, each 170 mm and centered.",
        "Document number is placed at the upper right below the top double line.",
        "Optional sequence number, secrecy, and urgency are placed at the upper left below the top double line.",
        "Title is centered two lines below the last top element.",
        "First page does not show page number.",
        "Footer record does not include issuing office or print date.",
    ],
    "order": [
        "Authority mark is centered 20 mm from the top of the core text area.",
        "Authority mark text should include 命令 or 令.",
        "Order number is centered two lines below the authority mark.",
        "Body starts two lines below the order number.",
        "Signature block follows the signed-by-approver layout.",
    ],
    "minutes": [
        "Header mark should be XXXXX纪要, centered near top.",
        "Attendee lists can include 出席, 请假, 列席 labels.",
        "Labels use 3rd-size Heiti; names and units use 3rd-size Fangsong.",
        "Attendee lines align after the full-width colon.",
        "Other body, attachment, and footer rules follow the standard format unless customized.",
    ],
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--type",
        choices=sorted(CHECKLISTS),
        default="standard",
        help="Document format type.",
    )
    args = parser.parse_args()

    for index, line in enumerate(CHECKLISTS[args.type], start=1):
        sys.stdout.write(f"{index}. {line}\n")

if __name__ == "__main__":
    main()
