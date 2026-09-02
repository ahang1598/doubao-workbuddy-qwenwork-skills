# Platform discovery commands

> ⛔ Only `inventory` / `get` / `search` / `cat` / `ll` / `ls` — never `Describe…` / `List…` or `get task`.

## Verbs

| You know… | Use |
|-----------|-----|
| Workspace stocktake / multi-facet inventory | `inventory` — read `not_covered_by_default` (lineage never included); then deepen with get/search/cat/lineage |
| Fuzzy name / intent | `search table` / `search asset` |
| Catalog · schema · id | `get <resource> …` |
| Tables known to contain data | `get tables --has-data --summary` (warehouse-wide) or `--catalog C [--schema S] --has-data --summary` |
| Full table detail | `get table --catalog C --schema S --table T` (default: exists + columns; `--output json` for programs) |
| Leaf `uri` | `cat <uri>` |
| One-hop lineage | `get lineage --catalog C --schema S --table T -d INPUT\|OUTPUT` |
| Compute resources (read-only enumeration) | `get compute-resources [--keyword <kw>] [--resource-type <csv>] [--status <csv>]` |
| Multi-hop / layer map / E2E diagram | `explore-lineage --from-inventory --catalog C` (see `lineage_exploration.md`) |

## Inventory (preferred multi-facet base scout)

```bash
wedatacli inventory                                      # quick, compact base map
wedatacli inventory --catalog <C> --thoroughness medium # add per-schema counts
```

Use `very_thorough` only for a named catalog when sampled table names are actually needed.
`-n/--top` caps non-table item samples; it does not make table counting partial.
After the base map, deepen only goal-relevant gaps; never shell-loop catalogs/schemas.

## Browse

```bash
wedatacli get catalogs
wedatacli get schemas --catalog <C>
wedatacli get tables --catalog <C> --schema <S>
wedatacli get tables --catalog <C> --schema <S> --has-data
wedatacli get tables --catalog <C> --has-data --summary
wedatacli get tables --has-data --summary                 # warehouse-wide
wedatacli get table --catalog <C> --schema <S> --table <T>
wedatacli cat table/<C>.<S>.<T>
```

Catalog / schema / table results carry `connection_id` + `connection_type` when the catalog is linked to a connection; both are absent for platform-managed (METALAKE) catalogs. Downstream pre-checks that must reject linked catalogs read `connection_id` from here.

## Search

```bash
wedatacli search table <kw>
wedatacli search table --schema <S>
wedatacli search table <kw> --schema <S>
wedatacli search table --table <T> --schema <S>
wedatacli search table <C>.<S>.<T> --mode exact
wedatacli search asset <kw>
wedatacli get workflows --keyword <kw>
wedatacli get integration-tasks --keyword <kw>
wedatacli get files --keyword <kw>
wedatacli get compute-resources [--keyword <kw>] [--resource-type <csv>] [--status <csv>]
```

Compute-resource enumeration is read-only; SubmitJob or any write → `unity-catalog-manage`.

## Flow

```
Workspace inventory / status / report?
                        → inventory [--thoroughness …] → deepen hotspots
User named catalog?     → get schemas --catalog <name>
Tables with data (named)? → get tables --catalog C --has-data --summary
Tables with data (warehouse-wide)?
                        → get tables --has-data --summary   # one call; no Bash loops
User named table / FQN? → get table or cat (one step)
Table name only?        → search table <name> → get table
Reuse / fuzzy?          → search table → detail top hits
Lineage?                → get lineage -d INPUT|OUTPUT
Sync task mapping?      → get integration-tasks --keyword <kw>
SQL / scripts?          → search asset or get files
```

`--has-data` = `records > 0`. Prefer `--summary` (tallies + top ~100 `items` by records; `truncated` when capped).
Do not invent `--with-stats`, shell-loop catalogs/`GetTable`, scrape truncated `/tmp` JSON,
or use `COUNT(*)` as the first discovery step.

## When stuck

- Thin search → `get tables` on likely schemas or sibling catalogs
- Still empty after search + list → report not found with commands tried
- Lineage OUTPUT = 0 → valid answer: no downstream

## Handoff

After inventory, schema, lineage, or reuse list, summarize and stop. Design and sync follow only when the user asks next.
