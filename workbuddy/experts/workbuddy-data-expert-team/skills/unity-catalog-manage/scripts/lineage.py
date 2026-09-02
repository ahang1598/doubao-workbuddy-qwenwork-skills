#!/usr/bin/env python3
"""Compact ListLineages single-layer and recursive expansion recipe."""

from __future__ import annotations

_RECIPE_NOTES = """
recipe: unity-catalog-manage / lineage expansion

Freezes the "Lineage / Activity / Search" high-frequency chain in SKILL.md
section 2 API index:
  ListLineages(Direction=INPUT|OUTPUT) -> paginated fold -> jq-shape slim
  -> optional recursive expansion

Contract firewall (contract-verified against the runtime CLI):
  * The only valid Action name is `ListLineages` (plural, capital L).
    ListLineage / GetLineage / ListUpstream* all return `unknown tool` --
    do NOT probe alternatives.
  * Direction only accepts uppercase `INPUT` (upstream) / `OUTPUT`
    (downstream); other values are rejected as parameter errors (server
    may respond as either HTTP 503 with empty body or
    `InvalidParameterValue.DirectionInvalid`) -- treat as parameter
    error, do NOT retry as service outage.
  * `WorkspaceId` is auto-injected by the CLI; do NOT pass it
    explicitly. ResourceName must be 3-part (catalog.schema.table);
    ResourceType must be uppercase enum (TABLE / VIEW / ...).
  * TotalCount=0 -> stop, do not retry with different params.

Linked-catalog (external-table) gate:
  * See SKILL.md §2.10 / §2.14. BEFORE invoking this recipe, the main
    agent SHOULD run the shared 4-form pre-gate via
    `common.resolve_and_pregate(user_input)` (or at minimum
    `common.is_linked_catalog(<catalog>)` when the FQN is already
    fully-qualified). The gate uses `wedatacli get catalogs` and reads
    the per-item `source` field: `source=="CONNECTION"` = Linked
    Catalog (refuse), `source=="METALAKE"` = internal (proceed). Banned
    resolution paths (all fail in real env): `GetCatalog` PascalCase
    Action, `wedatacli get catalog --name`, `search table` field
    `connection_id`.
  * Refusal template (§2.14): `⚠ 外部表暂不支持表血缘分析能力
    （Linked Catalog: <CatalogName>）。`
  * Recipe self-protection: `main()` runs the gate on the 3-part
    `--resource` before calling `ListLineages`, so hand-rolled CLI
    callers cannot bypass it. `--skip-pregate` is a light-mode flag: it
    skips the expensive search-driven four-form resolver (assumed to
    have run upstream via `common.resolve_and_pregate`) but STILL runs
    the cheap `get catalogs` lookup on the 3-part FQN — so a Linked
    Catalog can never slip through. Refusal path exits 0 with the
    refusal one-liner on stdout (expected terminal behaviour, not an
    error).
  * If the pre-gate is bypassed and the backend does surface
    `UnsupportedOperationForLinkedCatalog` (only for Linked Catalogs
    registered in catalog metadata), this recipe forwards the error
    verbatim — do NOT retry, do NOT synthesize. Note: for direct-
    connection catalogs that are NOT registered in `get catalogs`, the
    backend silently returns empty lineage instead of raising this code,
    which is exactly why the client-side pre-gate cannot be skipped.

Usage:
    python3 lineage.py --resource <catalog>.<schema>.<table> \
                       --direction OUTPUT --max-depth 2

Output: JSON on stdout (ready for the agent to consume); --pretty renders a
human-readable table.
"""


import argparse
import json
import sys
from typing import Any

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (  # noqa: E402
    call_action,
    is_linked_catalog,
    WedataCliError,
)


_ALLOWED_DIRECTIONS = {"INPUT", "OUTPUT"}
_DEFAULT_PAGE_SIZE = 50


def _list_lineages_page(
    resource_name: str,
    resource_type: str,
    direction: str,
    page_number: int,
    page_size: int,
) -> dict[str, Any]:
    payload = {
        "ResourceName": resource_name,
        "ResourceType": resource_type,
        "Direction": direction,
        "Page": {"PageNumber": page_number, "PageSize": page_size},
    }
    response = call_action("ListLineages", payload)
    error = response.get("Error")
    if error:
        raise WedataCliError(
            "ListLineages",
            0,
            json.dumps(response, ensure_ascii=False),
            error.get("Message") or json.dumps(error),
        )
    # Real env observation: some resources are not indexed by the lineage
    # service yet -> Response.Data is null (not {"Items": []}). Treat that
    # as an empty layer so callers can honestly report "no lineage in this
    # environment" instead of raising or fabricating.
    return response.get("Data") or {}


def list_lineage(
    resource_name: str,
    direction: str,
    resource_type: str = "TABLE",
    page_size: int = _DEFAULT_PAGE_SIZE,
    max_pages: int = 20,
) -> dict[str, Any]:
    """Expand one lineage layer: merges paging, returns slimmed fields only."""
    direction = direction.upper()
    if direction not in _ALLOWED_DIRECTIONS:
        raise ValueError(f"direction must be INPUT or OUTPUT, got {direction!r}")

    items: list[dict[str, Any]] = []
    total: Any = 0
    processes_stats: dict[str, int] = {}
    for page in range(1, max_pages + 1):
        data = _list_lineages_page(resource_name, resource_type, direction, page, page_size)
        raw_items = data.get("Items") or []
        total = data.get("TotalCount", total)
        for it in raw_items:
            cur = it.get("CurrentResource") or {}
            procs = it.get("Processes") or []
            # JSON output keeps EVERY Process so downstream consumers (agents,
            # jq pipelines, evaluators) can see the full set of sync/ETL jobs
            # per lineage item. Pretty-table rendering still collapses to the
            # first ProcessName per SKILL §2.14 output contract.
            full_processes = [
                {
                    "ProcessName": p.get("ProcessName") or "",
                    "ProcessType": p.get("ProcessType") or "",
                    "ProcessSubType": p.get("ProcessSubType") or "",
                }
                for p in procs
            ]
            primary = next(
                (p for p in full_processes if p["ProcessName"]),
                full_processes[0] if full_processes else {
                    "ProcessName": "", "ProcessType": "", "ProcessSubType": ""
                },
            )
            for p in full_processes:
                key = (
                    f'{p["ProcessType"]}/{p["ProcessSubType"]}'
                    .strip("/") or "UNKNOWN"
                )
                processes_stats[key] = processes_stats.get(key, 0) + 1
            items.append(
                {
                    "ResourceName": cur.get("ResourceName"),
                    "ResourceType": cur.get("ResourceType"),
                    # Backward-compatible flat fields = primary process (§2.14).
                    "ProcessName": primary["ProcessName"],
                    "ProcessType": primary["ProcessType"],
                    "ProcessSubType": primary["ProcessSubType"],
                    # Full list for callers that need every sync/ETL job.
                    "ProcessCount": len(full_processes),
                    "Processes": full_processes,
                }
            )
        if not raw_items or len(raw_items) < page_size:
            break
    # Normalise TotalCount: server returns it as a string ("9") or null when
    # the resource is unknown to the lineage service.
    try:
        total_int = int(total) if total is not None else 0
    except (TypeError, ValueError):
        total_int = 0
    return {
        "ResourceName": resource_name,
        "ResourceType": resource_type,
        "Direction": direction,
        "TotalCount": total_int,
        "ItemCount": len(items),
        "Empty": len(items) == 0,
        "Items": items,
        "ProcessStats": processes_stats,
    }


def expand_lineage(
    resource_name: str,
    direction: str,
    resource_type: str = "TABLE",
    max_depth: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    """Recursively expand lineage up to `max_depth` (default 1 == single layer)."""
    if max_depth < 1:
        raise ValueError("max-depth must be >= 1")
    visited: set[tuple[str, str]] = set()
    layers: list[dict[str, Any]] = []
    frontier: list[tuple[str, str]] = [(resource_name, resource_type)]
    for depth in range(1, max_depth + 1):
        next_frontier: list[tuple[str, str]] = []
        layer_items: list[dict[str, Any]] = []
        for rn, rt in frontier:
            if (rn, rt) in visited:
                continue
            visited.add((rn, rt))
            single = list_lineage(rn, direction, rt, page_size=page_size)
            for it in single["Items"]:
                enriched = dict(it)
                enriched["Depth"] = depth
                enriched["Parent"] = rn
                layer_items.append(enriched)
                if it["ResourceName"] and it["ResourceType"]:
                    next_frontier.append((it["ResourceName"], it["ResourceType"]))
        layers.append({"Depth": depth, "Items": layer_items})
        if not next_frontier:
            break
        frontier = next_frontier
    return {
        "Root": resource_name,
        "RootType": resource_type,
        "Direction": direction,
        "MaxDepth": max_depth,
        "Layers": layers,
        "TotalNodes": len(visited),
    }


def _render_pretty(result: dict[str, Any]) -> str:
    lines: list[str] = []
    if "Layers" in result:  # multi-depth
        lines.append(
            f"Root {result['Root']} ({result['RootType']}) | Direction={result['Direction']} "
            f"| MaxDepth={result['MaxDepth']} | Nodes={result['TotalNodes']}"
        )
        for layer in result["Layers"]:
            lines.append(f"\nDepth {layer['Depth']} (rows={len(layer['Items'])})")
            if not layer["Items"]:
                lines.append("(no lineage returned by the server for this layer)")
                continue
            lines.append("| # | ResourceName | ResourceType | ProcessName | #Procs |")
            lines.append("|---|---|---|---|---|")
            for i, it in enumerate(layer["Items"], 1):
                lines.append(
                    f"| {i} | {it['ResourceName']} | {it['ResourceType']} | "
                    f"{it['ProcessName']} | {it.get('ProcessCount', 1)} |"
                )
    else:
        heading = "Upstream" if result["Direction"] == "INPUT" else "Downstream"
        lines.append(
            f"{heading} of {result['ResourceName']} ({result['ResourceType']}) "
            f"— TotalCount={result['TotalCount']} · ItemCount={result['ItemCount']}"
        )
        if result.get("Empty"):
            lines.append(
                "(no lineage returned by the server for this resource; "
                "the lineage service may not have indexed it yet)"
            )
            return "\n".join(lines)
        lines.append("| # | ResourceName | ResourceType | ProcessName | #Procs |")
        lines.append("|---|---|---|---|---|")
        for i, it in enumerate(result["Items"], 1):
            lines.append(
                f"| {i} | {it['ResourceName']} | {it['ResourceType']} | "
                f"{it['ProcessName']} | {it.get('ProcessCount', 1)} |"
            )
        if result["ProcessStats"]:
            lines.append("\nProcess stats: " + ", ".join(
                f"{k}={v}" for k, v in sorted(result["ProcessStats"].items())
            ))
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="ListLineages recipe (single + recursive).")
    p.add_argument("--resource", required=True, help="3-part FullName, e.g. cat.sch.tbl")
    p.add_argument("--direction", required=True, choices=["INPUT", "OUTPUT"])
    # ResourceType observed values: TABLE / VIEW / VOLUME / MODEL / EXTERNAL.
    # Do not hard-restrict; server-side enum may expand and unknown values
    # surface as a server-side parameter error, which is easier to diagnose
    # than a client-side argparse choices error.
    p.add_argument("--resource-type", default="TABLE")
    p.add_argument("--max-depth", type=int, default=1)
    p.add_argument("--page-size", type=int, default=_DEFAULT_PAGE_SIZE)
    p.add_argument("--pretty", action="store_true", help="human-readable table output")
    p.add_argument(
        "--skip-pregate",
        action="store_true",
        help=(
            "internal: main agent already ran resolve_and_pregate upstream. "
            "This skips the expensive search-driven ambiguity resolution but "
            "still runs the cheap `get catalogs` lookup on the 3-part resource "
            "so a Linked Catalog can never bypass the refusal gate."
        ),
    )
    args = p.parse_args()

    # Recipe self-protection: enforce the Linked-Catalog pre-gate on the
    # 3-part resource. See SKILL.md §2.10. `--skip-pregate` degrades to a
    # LIGHT gate (single `get catalogs` call), it does NOT fully bypass —
    # otherwise a hand-rolled caller wiring `--skip-pregate` could silently
    # bypass the refusal on Linked Catalogs. The 3-part FQN check is O(1) on
    # top of one cached catalog list, so it's essentially free.
    parts = args.resource.split(".")
    if len(parts) == 3 and all(parts):
        try:
            gate = is_linked_catalog(parts[0])
        except WedataCliError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        if gate["linked"]:
            # Refusal is EXPECTED terminal behaviour, not a failure. Emit the
            # one-liner on stdout and exit 0 so shell wrappers / main agents
            # do not treat it as a crash. Detection tag `[LINKED_CATALOG]`
            # (also mirrored in stderr) lets automation distinguish refusal
            # from a normal empty-lineage result if it cares.
            msg = (
                f"⚠ 外部表暂不支持表血缘分析能力（Linked Catalog: {gate['CatalogName']}）。"
            )
            print(msg)
            print(f"[LINKED_CATALOG] catalog={gate['CatalogName']} source={gate['source']}", file=sys.stderr)
            return 0
    elif not args.skip_pregate:
        # Non-3-part input reached the recipe directly — upstream did NOT run
        # resolve_and_pregate. This is a caller misuse; instruct them to run
        # the four-form resolver first rather than silently guessing.
        print(
            "ERROR: --resource must be a 3-part FQN <catalog>.<schema>.<table>. "
            "For 2-part / single-name / semantic input, run "
            "common.resolve_and_pregate(<user_input>) upstream and pass the "
            "resolved FQN here.",
            file=sys.stderr,
        )
        return 2

    try:
        if args.max_depth == 1:
            result = list_lineage(
                args.resource,
                args.direction,
                args.resource_type,
                page_size=args.page_size,
            )
        else:
            result = expand_lineage(
                args.resource,
                args.direction,
                args.resource_type,
                max_depth=args.max_depth,
                page_size=args.page_size,
            )
    except WedataCliError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.pretty:
        print(_render_pretty(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
