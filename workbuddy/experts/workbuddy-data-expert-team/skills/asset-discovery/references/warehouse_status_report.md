# Warehouse status report

**When**: handover, stocktake, audit, workspace inventory — not single-table lookups.
**Who**: usually `Agent("discovery")` (+ `datasource-discovery` if external matters).

## Base scout

```bash
wedatacli inventory
```

This defaults to compact `quick`: exact table totals by catalog plus small samples for
other facets. Use `--catalog <C> --thoroughness medium` only when per-schema counts are
needed; use `very_thorough` only for sampled table names in a named catalog.

Read `truncated` before treating any `items` list as complete. `-n/--top` caps non-table
samples only. The result is still a base map: deepen goal-relevant gaps with
`get` / `search` / `cat`; lineage uses `get lineage` / `explore-lineage`.

## Tables with data

```bash
wedatacli get tables --catalog C --has-data --summary   # named
wedatacli get tables --has-data --summary               # warehouse-wide
```

`records > 0`. `--summary` = tallies (`by_catalog` / `by_schema`) + ranked `items` (top 100 by records; `truncated=true` when capped). No Bash loops.

## Whether to file a report

| Complexity | Do |
|------------|----|
| Small / Q&A | Chat Summary only |
| User asks for report / shareable doc | `Write` `~/.wedata/artifact/engineering/asset_report_<ts>.md` |
| Broad multi-facet stocktake | Prefer short file + `artifact_path` |

**Report body** — still **catalog → schema → table**, but **Top-N tables only** (default Top 20 by `records` overall, or Top N per catalog when scoped). Never dump every has-data table.

0. **Scout date** — run `date '+%Y-%m-%d'` (local timezone) and paste the output; do not invent or reuse an old date
1. Overview — `by_catalog` counts
2. Detail — C → S → T for the Top-N tables (include records / files_size when present)
3. Coverage / Gaps — what was scanned; how to deepen one catalog/schema

Full list for a **named** catalog/schema only when the user explicitly asks.
Parent relays Summary; does not re-`Read` the artifact.
