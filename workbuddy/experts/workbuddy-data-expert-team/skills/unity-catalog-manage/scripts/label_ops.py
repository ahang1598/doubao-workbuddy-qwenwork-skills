#!/usr/bin/env python3
"""Compact read-only ListLabels exploration recipe."""

from __future__ import annotations

_RECIPE_NOTES = """
recipe: unity-catalog-manage / label exploration (read-only default)

Freezes the read-only slice of the high-hallucination Label API chain from
SKILL.md section 2.11:
  ListLabels(Shared=true, Types=[...], KeyWord="...", Page{})
  -> slim projection {Id, Name, Type, SourceType, Values(<=4 samples), Description}
  -> optional --group-by-type covers "what business/BI/masking labels exist
     in this workspace" intent

Contract firewall (contract-verified against the runtime CLI):
  * Pagination is **nested** as `Page:{PageNumber,PageSize}`, NOT top-level
    PageNumber / PageSize.
  * The response items live under `Data.Labels`, NOT `Data.Items`.
  * `Shared=true` is required to see all workspace-visible labels
    (SKILL section 2.11).
  * `KeyWord` is case-sensitive: both K and W are capitalised. LLMs commonly
    misspell it as `keyword` / `Keyword` and get zero hits.
  * `Types` is an int array with the following business dictionary:
      1=business  2=category  3=BI  4=masking  6=department  7=project  ...
    The Chinese labels below (TypeLabel) mirror the server-side dictionary
    values verbatim; do NOT translate them.
  * WorkspaceId is auto-injected by the CLI; recipe does not pass it.
  * A single page of 20 items already spills ~26KB on stdout, and the full
    ws dump is ~100KB. This recipe slims that down to <5KB (about 20x).

Write-path operations are NOT part of this recipe: CreateLabels /
UpdateLabels / DeleteLabels / BatchVoteAssetTag go through the SKILL
section 3 confirmation gate. The main agent must present a preview,
request the user's confirm, and hand-roll wedatacli. This guards against
batch mis-write from the script layer.

Usage:
    # Full read-only exploration (Type=4 masking excluded by default to keep
    # the boundary with the data-classification skill clean).
    python3 label_ops.py --pretty

    # Keyword filter (KeyWord is a fuzzy match).
    python3 label_ops.py --keyword order --pretty

    # Type filter (comma-separated ints, e.g. 1=business + 3=BI).
    python3 label_ops.py --types 1,3 --pretty

    # Type-histogram (aggregate stats instead of raw list).
    python3 label_ops.py --group-by-type
"""


import argparse
import json
import sys
from typing import Any

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import WedataCliError, list_labels  # noqa: E402


_TYPE_LABEL = {
    # Internal display dictionary for the int-valued `Type` field returned by
    # ListLabels. Server-side data is the int; the string label below is a
    # local rendering hint only. The mapping mirrors the platform business
    # dictionary but uses English keywords per repo convention.
    1: "business",
    2: "category",
    3: "BI",
    4: "masking",
    5: "report",
    6: "department",
    7: "project",
    8: "purpose",
    9: "core-asset",
    10: "governance",
    11: "custom",
    12: "attribute",
}


def _slim_label(lbl: dict[str, Any]) -> dict[str, Any]:
    values = lbl.get("Values") or []
    sample = []
    for v in values[:4]:
        if isinstance(v, dict):
            sample.append(v.get("Value") or v.get("Name") or "")
        else:
            sample.append(str(v))
    return {
        "Id": lbl.get("Id") or lbl.get("LabelId") or "",
        "Name": lbl.get("Name") or "",
        "Type": lbl.get("Type"),
        "TypeLabel": _TYPE_LABEL.get(lbl.get("Type") or -1, "?"),
        "SourceType": lbl.get("SourceType"),
        "SampleValues": [s for s in sample if s],
        "ValueCount": len(values),
        "Description": (lbl.get("Description") or "")[:120],
    }


def explore_labels(
    keyword: str | None = None,
    label_types: list[int] | None = None,
    page_size: int = 50,
    max_pages: int = 10,
    include_masking: bool = False,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    raw = list_labels(
        workspace_id=workspace_id,
        keyword=keyword,
        label_types=label_types,
        page_size=page_size,
        max_pages=max_pages,
        shared=True,
    )
    labels = raw["Labels"]
    slimmed = [_slim_label(x) for x in labels]
    if not include_masking and not label_types:
        # Exclude Type=4 masking labels by default to keep the boundary with
        # the data-classification skill; caller can opt-in via --include-masking.
        slimmed = [x for x in slimmed if x["Type"] != 4]
    return {
        "TotalReturned": raw["TotalCount"],
        "AfterFilter": len(slimmed),
        "Labels": slimmed,
    }


def group_by_type(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hist: dict[int, int] = {}
    for l in labels:
        t = l.get("Type") or -1
        hist[t] = hist.get(t, 0) + 1
    return [
        {"Type": t, "TypeLabel": _TYPE_LABEL.get(t, "?"), "Count": n}
        for t, n in sorted(hist.items(), key=lambda x: -x[1])
    ]


def _render_pretty(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(
        f"ListLabels → total={result['TotalReturned']} after_filter={result['AfterFilter']}"
    )
    lines.append("")
    lines.append("**Candidate labels**")
    lines.append("| Name | Type | Sample values | Id |")
    lines.append("|---|---|---|---|")
    labels = result["Labels"]
    display_limit = len(labels) if len(labels) <= 20 else 10
    for l in labels[:display_limit]:
        samples = ", ".join(l["SampleValues"]) if l["SampleValues"] else ""
        if len(samples) > 40:
            samples = samples[:37] + "..."
        lines.append(
            f"| {l['Name']} | {l['TypeLabel']}({l['Type']}) | {samples} | {l['Id']} |"
        )
    if len(labels) > display_limit:
        lines.append(f"| ... | remaining {len(labels) - display_limit} rows omitted from preview | | |")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="ListLabels recipe (read-only exploration).")
    p.add_argument("--keyword", default=None, help="ListLabels.KeyWord fuzzy match")
    p.add_argument(
        "--types",
        default="",
        help="Comma-separated int Types filter, e.g. 1,3 (default: all except 4 masking)",
    )
    p.add_argument("--page-size", type=int, default=50)
    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument(
        "--include-masking",
        action="store_true",
        help="Include Type=4 masking labels (default excluded to keep boundary with data-classification)",
    )
    p.add_argument(
        "--group-by-type",
        action="store_true",
        help="Output type histogram instead of raw label list",
    )
    p.add_argument(
        "--workspace-id",
        default=None,
        help="Override the CLI-auto-injected WorkspaceId (only for cross-workspace probes)",
    )
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    types = [int(t) for t in args.types.split(",") if t.strip().isdigit()]

    try:
        result = explore_labels(
            keyword=args.keyword,
            label_types=types or None,
            page_size=args.page_size,
            max_pages=args.max_pages,
            include_masking=args.include_masking,
            workspace_id=args.workspace_id,
        )
    except WedataCliError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.group_by_type:
        hist = group_by_type(result["Labels"])
        out = {
            "TotalReturned": result["TotalReturned"],
            "AfterFilter": result["AfterFilter"],
            "TypeHistogram": hist,
        }
        if args.pretty:
            print(f"Type histogram (total={result['AfterFilter']})")
            print("| Type | TypeLabel | Count |")
            print("|---|---|---|")
            for h in hist:
                print(f"| {h['Type']} | {h['TypeLabel']} | {h['Count']} |")
        else:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if args.pretty:
        print(_render_pretty(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
