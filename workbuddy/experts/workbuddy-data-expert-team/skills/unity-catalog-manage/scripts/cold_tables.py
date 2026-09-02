#!/usr/bin/env python3
"""Compact audit-log driven cold-table inventory recipe."""

from __future__ import annotations

_RECIPE_NOTES = """
recipe: unity-catalog-manage / cold-tables inventory

Freezes the "cold-table inventory / last N days unused" chain in SKILL.md
section 2.16 "Audit-log hard constraints":
  ListTables (name-only via `get tables`)
  -> audit_log SQL (with event_date + get_json_object)
  -> LEFT ANTI JOIN in-agent
  -> optional ListLineages OUTPUT filter (drop tables that still have
     downstream consumers)

Contract firewall (contract-verified against the runtime CLI):
  * The only valid path is: one `get tables` + one aggregate `audit_log` SQL
    + local diff. `.snapshots` / `.files` / per-table SubmitJob loops burn
    millions of tokens -- forbidden.
  * `audit_log` MUST filter by `event_date` (partition). Default window is
    7 days; the cold-table window is typically up to 90 days.
  * `audit_log` has NO `event_type` / `object_name` / `resource_full_name`
    columns -- those are hallucinations. Resource identity is extracted via
    `get_json_object(request_params, ...)`.
  * `action_name` uses a regex to match Table-family operations
    (Create/Get/Update/Delete/Check).
  * `query-sql` MUST use the `--sql` or `--sql-file` flag (positional args
    are rejected).
  * When excluding tables that still have downstream consumers, use
    Direction=`OUTPUT` (uppercase).

Usage:
    python3 cold_tables.py --catalog <catalog> --schema <schema> --days 90 \
                           [--exclude-with-downstream] [--pretty]
"""


import argparse
import json
import sys
from typing import Any

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (  # noqa: E402
    call_action,
    get_tables,
    query_sql,
    WedataCliError,
)


_SQL_TEMPLATE = """
SELECT DISTINCT lower(
    coalesce(
        get_json_object(request_params, '$.FullName'),
        concat_ws('.',
            get_json_object(request_params, '$.CatalogName'),
            get_json_object(request_params, '$.SchemaName'),
            get_json_object(request_params, '$.TableName')
        )
    )
) AS full_name
FROM system_catalog.wedata.audit_log
WHERE event_date BETWEEN date_sub(current_date(), {days}) AND current_date()
  AND action_name RLIKE '(Create|Get|Update|Delete|Check)Table(s|Comment|Name|ColumnComment|ColumnsComment)?'
  AND get_json_object(request_params, '$.CatalogName') = '{catalog}'
  AND get_json_object(request_params, '$.SchemaName')  = '{schema}'
""".strip()


def _has_downstream(full_name: str) -> bool:
    """Return True if the table has any downstream lineage (OUTPUT direction)."""
    payload = {
        "ResourceName": full_name,
        "ResourceType": "TABLE",
        "Direction": "OUTPUT",
        "Page": {"PageNumber": 1, "PageSize": 1},
    }
    try:
        resp = call_action("ListLineages", payload)
    except WedataCliError:
        return False  # Silently treat as "no downstream" so a single lineage
        #              probe failure does not abort the whole inventory sweep.
    data = resp.get("Data") or {}
    return int(data.get("TotalCount") or 0) > 0


def cold_tables(
    catalog: str,
    schema: str,
    days: int = 90,
    exclude_with_downstream: bool = False,
    keyword: str | None = None,
) -> dict[str, Any]:
    if days < 1 or days > 90:
        raise ValueError("days must be within [1, 90] (audit_log partition budget)")

    # Step 0: audit_log availability pre-flight — one zero-row probe.
    # `system_catalog.wedata.audit_log` is the standard path but not every
    # workspace has it registered / permissioned. Fail fast with a
    # structured error instead of dumping a raw engine stacktrace.
    probe = query_sql(
        "SELECT 1 FROM system_catalog.wedata.audit_log "
        "WHERE event_date = current_date() LIMIT 0"
    )
    if probe.status != "SUCCESS":
        return {
            "Catalog": catalog,
            "Schema": schema,
            "Days": days,
            "AuditLogUnavailable": True,
            "TotalTables": 0,
            "ActiveTables": 0,
            "ColdTables": [],
            "ExcludeWithDownstream": exclude_with_downstream,
            "DownstreamProbe": {},
            "CsvPath": None,
            "CostMs": None,
            "Note": (
                "system_catalog.wedata.audit_log is unavailable in this "
                "workspace (unregistered catalog or missing "
                "Security-Administrator / audit-read permission). "
                "Cold-table inventory cannot run. Ask an administrator to "
                "grant audit-log read access, or fall back to manual "
                "usage checks via the compute engine."
            ),
            "ProbeError": probe.message or f"status={probe.status}",
        }

    # Step 1: candidate set — one name-only ListTableNames call
    names = get_tables(catalog, schema, keyword=keyword)
    candidates = {f"{catalog}.{schema}.{n}".lower() for n in names if n}

    # Step 2: active set — one audit_log aggregation SQL
    sql = _SQL_TEMPLATE.format(days=days, catalog=catalog, schema=schema)
    r = query_sql(sql)
    if r.status != "SUCCESS":
        raise WedataCliError(
            "query-sql", 0, r.csv_path or "", r.message or f"status={r.status}"
        )
    active = {row.get("full_name", "").lower() for row in r.rows() if row.get("full_name")}

    # Step 3: local LEFT ANTI JOIN
    cold = sorted(candidates - active)

    downstream_filter: dict[str, bool] = {}
    if exclude_with_downstream and cold:
        # Only probe OUTPUT for cold candidates -- avoids a full-table scan.
        cold_filtered: list[str] = []
        for fn in cold:
            has = _has_downstream(fn)
            downstream_filter[fn] = has
            if not has:
                cold_filtered.append(fn)
        cold = cold_filtered

    return {
        "Catalog": catalog,
        "Schema": schema,
        "Days": days,
        "TotalTables": len(candidates),
        "ActiveTables": len(active & candidates),
        "ColdTables": cold,
        "ExcludeWithDownstream": exclude_with_downstream,
        "DownstreamProbe": downstream_filter,
        "CsvPath": r.csv_path,
        "CostMs": r.cost_ms,
    }


def _render_pretty(result: dict[str, Any]) -> str:
    if result.get("AuditLogUnavailable"):
        note = result.get("Note", "")
        probe_err = result.get("ProbeError")
        tail = f"\nProbe error: {probe_err}" if probe_err else ""
        return (
            f"⚠ Cold-table inventory unavailable for "
            f"{result['Catalog']}.{result['Schema']}: audit_log not usable in "
            f"this workspace.\n{note}{tail}"
        )
    cold_tables = result["ColdTables"]
    display_limit = len(cold_tables) if len(cold_tables) <= 20 else 10
    lines: list[str] = [
        f"Cold-table inventory: {result['Catalog']}.{result['Schema']} "
        f"(window={result['Days']}d)",
        f"  Total={result['TotalTables']}  Active={result['ActiveTables']}  "
        f"Cold={len(cold_tables)}  "
        f"ExcludeWithDownstream={result['ExcludeWithDownstream']}",
        "",
        "| # | Cold table |",
        "|---|---|",
    ]
    for i, fn in enumerate(cold_tables[:display_limit], 1):
        lines.append(f"| {i} | {fn} |")
    if not cold_tables:
        lines.append("| — | (none) |")
    elif len(cold_tables) > display_limit:
        lines.append(f"| ... | remaining {len(cold_tables) - display_limit} rows omitted from preview |")
        if result.get("CsvPath"):
            lines.append(f"\nFull active-set CSV: {result['CsvPath']}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Audit-log driven cold-table inventory.")
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--days", type=int, default=90,
                   help="lookback window (1..90 days, default 90)")
    p.add_argument("--exclude-with-downstream", action="store_true",
                   help="drop tables with downstream lineage (Direction=OUTPUT)")
    p.add_argument("--keyword", default=None, help="ListTableNames filter")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    try:
        result = cold_tables(
            args.catalog,
            args.schema,
            days=args.days,
            exclude_with_downstream=args.exclude_with_downstream,
            keyword=args.keyword,
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
