#!/usr/bin/env python3
"""Compact SearchAsset + optional GetTable field-probe recipe."""

from __future__ import annotations

_RECIPE_NOTES = """
recipe: unity-catalog-manage / asset search + field recall

Freezes the high-frequency "Search / table recommendation / field probe" chain
from SKILL.md section 2 API index:
  SearchAsset(keyword, AssetTypes=[TABLE], MaxResults<=100)
  -> slim projection {FullName, AssetGuid, AssetType, Comment}
  -> optional --with-fields: per-table GetTable pulls {Name, Type, Comment}
  -> optional --require-fields=col_a,col_b: strict local column filter

Contract firewall (contract-verified against the runtime CLI):
  * `SearchAsset.WorkspaceId` is auto-injected by the CLI as a STRING; recipes
    do not pass it. Numeric values fail with `json: cannot unmarshal number
    into Go struct field SearchAssetRequest.WorkspaceId of type string` if a
    caller ever overrides it.
  * `SearchAsset` does NOT return `TotalCount`; use `NextPageToken` to page.
  * `MaxResults` is hard-capped at 100 server-side.
  * `GetTable` primary key is the 4-tuple {WorkspaceId, CatalogName,
    SchemaName, TableName} -- AssetGuid / FullName are rejected. The response
    is wrapped as `Data.Table.*` (one extra layer).
  * `AssetGuid` returned by SearchAsset is the only reliable identity for the
    write path (favorite / view / BatchVoteAssetTag). Copy it verbatim.

Usage:
    # Scenario 1: LLM hand-rolled SearchAsset spills 28KB for just 5 hits.
    # Switch to the recipe:
    python3 asset_search.py --keyword order --limit 15

    # Scenario 2: find tables that contain BOTH columns:
    python3 asset_search.py --keyword order --with-fields \
        --require-fields order_purchase_timestamp,order_approved_at

Output: JSON on stdout; --pretty renders the human-readable table aligned with
SKILL section 2.14 "Candidate tables".
"""

import argparse
import json
import sys
from typing import Any

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (  # noqa: E402
    get_table,
    search_asset,
    WedataCliError,
)


_DEFAULT_PAGE = 20


def _split_fullname(fullname: str) -> tuple[str, str, str] | None:
    parts = (fullname or "").split(".")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def _slim_item(it: dict[str, Any]) -> dict[str, Any]:
    """A single server-side SearchAsset hit is ~5.6KB; slimmed to <200B."""
    full_name = it.get("FullName") or ""
    catalog = full_name.split(".", 1)[0] if "." in full_name else ""
    return {
        "FullName": full_name,
        "Catalog": catalog,
        "AssetGuid": it.get("AssetGuid") or "",
        "AssetType": it.get("AssetType") or "",
        "Comment": (it.get("Description") or it.get("Comment") or "")[:200],
        "Owner": (it.get("Owner") or {}).get("UserName")
        if isinstance(it.get("Owner"), dict)
        else (it.get("Owner") or ""),
        "Popularity": it.get("Popularity"),
    }


def _slim_columns(table_obj: dict[str, Any]) -> list[dict[str, Any]]:
    cols = table_obj.get("Columns") or []
    return [
        {
            "Name": c.get("Name") or "",
            "Type": c.get("Type") or c.get("DataType") or "",
            "Comment": (c.get("Comment") or "")[:80],
        }
        for c in cols
    ]


def search_and_probe(
    keyword: str,
    limit: int = _DEFAULT_PAGE,
    asset_types: list[str] | None = None,
    with_fields: bool = False,
    require_fields: list[str] | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """SearchAsset recall -> optional GetTable field pull -> optional strict filter."""
    requested_limit = int(limit)
    limit = max(1, min(requested_limit, 100))
    if requested_limit != limit:
        # Be *visibly* lenient: recipe layer clamps to the server-side cap
        # instead of raising, but we surface the fact so callers notice.
        print(
            f"[note] --limit={requested_limit} clamped to {limit} "
            f"(SearchAsset.MaxResults server-side hard cap is 100); "
            f"use NextPageToken to page further.",
            file=sys.stderr,
        )
    types = asset_types or ["TABLE"]

    raw = search_asset(
        keyword=keyword,
        workspace_id=workspace_id,
        asset_types=types,
        max_results=limit,
    )
    items = [_slim_item(it) for it in raw["Items"]]

    result: dict[str, Any] = {
        "Keyword": keyword,
        "AssetTypes": types,
        "Limit": limit,
        "Count": len(items),
        "NextPageToken": raw["NextPageToken"],
        "Items": items,
    }

    if not with_fields and not require_fields:
        return result

    # Only TABLE hits can be enriched via GetTable; VIEW/MODEL would return
    # InvalidParameter -- skip them silently.
    require_lower = {f.lower() for f in (require_fields or [])}
    enriched: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []

    def append_unprobed(slim_item: dict[str, Any], reason: str) -> None:
        row = dict(slim_item)
        if require_lower:
            row["MatchedRequired"] = None
            row["MissingRequired"] = None
            row["ProbeStatus"] = reason
        enriched.append(row)

    for slim in items:
        if slim["AssetType"] != "TABLE":
            append_unprobed(slim, "skipped_non_table")
            continue
        parts = _split_fullname(slim["FullName"])
        if not parts:
            append_unprobed(slim, "invalid_full_name")
            continue
        try:
            table_obj = get_table(parts[0], parts[1], parts[2], workspace_id=workspace_id)
        except WedataCliError:
            # Permission or exceptional table -- skip rather than aborting the batch.
            append_unprobed(slim, "get_table_failed")
            continue
        cols = _slim_columns(table_obj)
        col_names_lower = {c["Name"].lower() for c in cols}
        missing = sorted(f for f in require_lower if f not in col_names_lower)
        matched_required = sorted(f for f in require_lower if f in col_names_lower)
        row = {
            **slim,
            "TableComment": (table_obj.get("Comment") or "")[:200],
        }
        if with_fields:
            row["Columns"] = cols
        if require_lower:
            row["MatchedRequired"] = matched_required
            row["MissingRequired"] = missing
        enriched.append(row)
        if require_lower and not missing:
            matched.append(enriched[-1])

    result["Items"] = enriched
    if require_lower:
        result["RequireFields"] = sorted(require_lower)
        result["MatchedCount"] = len(matched)
        result["Matched"] = matched
    return result


def _render_pretty(result: dict[str, Any]) -> str:
    """Renders the SKILL section 2.14 "Candidate tables" column layout."""
    lines: list[str] = []
    lines.append(
        f"Search '{result['Keyword']}' (types={','.join(result['AssetTypes'])} "
        f"limit={result['Limit']}) -> {result['Count']} hits"
        + (" (more via NextPageToken)" if result.get("NextPageToken") else "")
    )
    lines.append("")
    lines.append("**Candidate tables**")
    lines.append("| Table FullName | Catalog | Comment | Popularity |")
    lines.append("|---|---|---|---|")
    items = result["Items"]
    display_limit = len(items) if len(items) <= 20 else 10
    for it in items[:display_limit]:
        cmt = (it.get("TableComment") or it.get("Comment") or "").replace("\n", " ")
        if len(cmt) > 30:
            cmt = cmt[:27] + "..."
        pop = it.get("Popularity")
        lines.append(
            f"| {it['FullName']} | {it.get('Catalog','')} | {cmt} | "
            f"{pop if pop is not None else ''} |"
        )
    if len(items) > display_limit:
        lines.append(f"| ... | | remaining {len(items) - display_limit} rows omitted from preview | |")

    if "MatchedCount" in result:
        lines.append("")
        lines.append(
            f"Require-fields {result['RequireFields']} -> "
            f"{result['MatchedCount']} table(s) satisfy all fields:"
        )
        for it in result["Matched"]:
            lines.append(f"  - {it['FullName']}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="SearchAsset recipe (recall + optional field probe).")
    p.add_argument("--keyword", required=True, help="Search keyword (SearchAsset.Keyword)")
    p.add_argument("--limit", type=int, default=_DEFAULT_PAGE, help="MaxResults (1..100; values >100 are auto-clamped with a stderr note)")
    p.add_argument(
        "--asset-types",
        default="TABLE",
        help="Comma-separated AssetTypes filter, e.g. TABLE,VIEW (default TABLE)",
    )
    p.add_argument(
        "--with-fields",
        action="store_true",
        help="GetTable each TABLE hit and include Columns (slim shape) in output",
    )
    p.add_argument(
        "--require-fields",
        default="",
        help="Comma-separated column names that MUST all exist for a table to match",
    )
    p.add_argument(
        "--workspace-id",
        default=None,
        help="Override the CLI-auto-injected WorkspaceId (only for cross-workspace probes)",
    )
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    types = [t.strip().upper() for t in args.asset_types.split(",") if t.strip()]
    req = [f.strip() for f in args.require_fields.split(",") if f.strip()]

    try:
        result = search_and_probe(
            keyword=args.keyword,
            limit=args.limit,
            asset_types=types,
            with_fields=args.with_fields,
            require_fields=req,
            workspace_id=args.workspace_id,
        )
    except WedataCliError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.pretty:
        print(_render_pretty(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
