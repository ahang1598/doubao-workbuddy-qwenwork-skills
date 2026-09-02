---
name: asset-discovery
layer: L3
type: execution
stage: discovery
tags: [data-development]
user-invocable: false
description: >
  Read-only in-platform (lakehouse) scout via wedatacli: catalog inventory, table
  schema/columns, fuzzy table search, Studio SQL/files, workflows, sync tasks,
  compute resources (read-only enumeration), one-hop lineage, warehouse status.
  Inline: known-coordinate ≤2-step lookups (FQN get/cat, one search→top1, one
  schema list, named-catalog table list). Agent("discovery"): warehouse-wide /
  multi-catalog / has-data scans / inventory / multi-facet / fuzzy reuse across
  assets / lineage beyond one known hop / ≥3 probes — even if one CLI.
  Boundary: user-named connection → datasource-discovery (a CONNECTION-source
  catalog still stays here); SubmitJob or any write on compute resources →
  unity-catalog-manage; design / sync / DDL stay with the parent.
  Lineage boundary: exploration / layered
  pipeline map / mermaid diagram stay here; ETL ProcessName / recursive depth
  >2 / external-table pre-gate / governance output (§2.14 table) →
  unity-catalog-manage.
---

# asset-discovery

Read-only platform metadata via `wedatacli`. Fewest steps; paste `uri` / `cat_command` from results.

**CLI**: `inventory` / `get` / `search` / `cat` / `ll` / `ls` only — never `Describe*` / `List*` PascalCase APIs; never `get task` (use `get workflow-task` / `get integration-tasks`).

Summarize and stop; hand off design, sync, or DDL only when the user asks next.

**Inline vs `Agent("discovery")`**: known-coordinate ≤2-step point lookup → inline; warehouse-wide / has-data / inventory / multi-facet / ≥3 probes (even one large CLI) → `Agent("discovery")`.

**Boundary**: this skill owns the catalog tree (`catalog.schema.table`), including catalogs whose `source` is `CONNECTION`. Hand off to `datasource-discovery` only when the user names a 连接 / 数据源 / `databuddy://connection/…`.

## Shortest path

| User wants | Command |
|------------|---------|
| Stocktake / status / workspace inventory | `inventory` → deepen as needed. Prefer `Agent("discovery")`. Connections: `datasource-discovery`. |
| Known table / FQN | `get table` or `cat table/C.S.T` |
| Batch tables with columns | `get tables --with-columns --catalog C --schema S [--tables "t1,t2"]` |
| Table name only | `search table` → `get table` on top hit |
| Named catalog | `get schemas --catalog <C>` → `get tables` |
| Tables with data | `get tables [--catalog C] --has-data --summary` (omit `--catalog` = warehouse-wide). Prefer `Agent("discovery")`. |
| Fuzzy reuse / SQL / workflows / sync | `search table` / `search asset` / `get workflows` / `get integration-tasks` |
| Compute resources (read-only enumeration) | `get compute-resources [--keyword <kw>] [--resource-type <csv>] [--status <csv>]`. Write / SubmitJob → `unity-catalog-manage`. |
| Lineage | `explore-lineage --format pipeline\|mermaid` or `get lineage -d INPUT\|OUTPUT`. Need ETL `ProcessName` / depth >2 / external-table pre-gate / §2.14 governance table → `unity-catalog-manage`. |

No Bash loops over catalogs/schemas. No brute-force enumeration across catalogs (even via sequential tool calls). Prefer `--summary` when listings are large. Known FQN: `get table` only — `search table` 0 hits ≠ table missing.

Details: [commands.md](references/commands.md) · lineage: [lineage_exploration.md](references/lineage_exploration.md) · stocktake: [warehouse_status_report.md](references/warehouse_status_report.md)

For an incomplete FQN, use the most specific `search table` filters available; search
before asking when coordinates are inferable, and return at most three full-FQN candidates
when ambiguous. Exact command forms live in [commands.md](references/commands.md).
### Persisting discovered tables (cache-first)

Every table discovered via `get table` or `cat table` **must** be persisted as `.json` under `/Workspace/relative-tables/<catalog>.<schema>.<table_name>.json`, so the recalled schemas are available to downstream consumers (e.g. `sql-codegen-agent`, `studio-development`). Check the cache first so the same table isn't re-fetched/overwritten if it's already there (e.g. from an earlier step in this session):

```bash
mkdir -p /Workspace/relative-tables
TARGET="/Workspace/relative-tables/<C>.<S>.<T>.json"
[ -f "$TARGET" ] || wedatacli get table --catalog <C> --schema <S> --table <T> --output json > "$TARGET"
```

Downstream consumers (e.g. `sql-codegen-agent`) must also cache-check `$TARGET` before recalling the same table again (see `sql-codegen/SKILL.md` §1.0).

## Table locating (incomplete FQN)

Tables are identified by `catalog.schema.table`. When user provides partial info, choose freely among:

**Available means** (no fixed priority — pick what fits the context):

| Known info | Command | Notes |
|------------|---------|-------|
| schema only | `search table --schema <s>` | Cross-catalog, one-step |
| table name only | `search table <keyword>` | Global fuzzy |
| schema + fuzzy table | `search table <kw> --schema <s>` | Scoped fuzzy |
| schema + exact table | `search table --table <t> --schema <s>` | Exact match |
| full FQN | `get table --catalog <c> --schema <s> --table <t>` | Direct fetch |
| catalog + schema | `get tables --catalog <c> --schema <s>` | List all in scope |
| qualified name string | `search table <c>.<s>.<t> --mode exact` | Auto-parse FQN |
| insufficient info | Ask user for missing segment | Interaction |

**Decision principles:**
- Info sufficient → search/get directly, don't ask user
- Info insufficient but inferable → search first, then confirm if ambiguous
- Info severely lacking → ask user before acting
- Multiple matches → list candidates (with full FQN), let user pick
- Never enumerate catalogs/schemas one-by-one to locate a target

## When stuck

- Empty search → `get tables` on likely schemas or another catalog
- ODS lineage INPUT=0 → often raw intake; check `intake_paths` or `get integration-tasks`
- Large output → `--summary`; never paste full recursive JSON

## Budget

- Inline: ≤ 2 known-coordinate tool calls (hard cap 3); if the next step needs more → `Agent("discovery")`
- Broader recon: prefer `Agent("discovery")`; parent relays Summary (+ `artifact_path`), does not re-scout
- 🔴 需要多张表的字段结构时，**必须**用 `get tables --with-columns`（1 次调用），禁止逐表 `get table` 串行获取

## Output

`asset_search_result`: name, type, coordinates, match reason, reuse note. Cap at top 3 hits.
Report file by complexity — see `warehouse_status_report.md`.
