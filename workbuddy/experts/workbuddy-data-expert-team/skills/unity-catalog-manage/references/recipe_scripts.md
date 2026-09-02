# unity-catalog-manage / scripts

Python recipes that freeze the SKILL.md chains that are (a) high-frequency,
(b) high-hallucination, and (c) expensive in tokens. Every recipe below is
contract-verified against the runtime CLI.

## Why recipes exist

The baseline path (LLM hand-rolling wedatacli) performs worst in these
patterns:

1. **Paging / recursive expansion** -- the LLM forgets pagination or invents
   `MaxResults` / `MaxDepth` fields that do not exist.
2. **Spill handling** -- responses over 16 KiB spill to `/tmp/*.json`; if the
   LLM `read_file`s the spill, it swallows the whole payload back into
   context.
3. **Composed chains** -- e.g. `ListTables -> audit_log -> LEFT ANTI JOIN ->
   ListLineages OUTPUT`. One misstep triggers dozens of correction turns.

Each recipe freezes one such chain as Python: the LLM invokes a single
command, cutting turns, stdout bytes, and spill dependency.

Pretty-output contract: recipes follow the SKILL.md short-table threshold.
They show all rows when the result has <=20 rows; otherwise they show the
first 10 rows and an omitted-row count. JSON output remains complete but slim.

## Recipe -> intent map

| Recipe | Intent keywords | Related SKILL section |
|---|---|---|
| `lineage.py` | upstream / downstream / lineage / recursive expansion | section 2.0 index Lineage row, section 2 cheatsheet ListLineages |
| `cold_tables.py` | cold tables / unused tables / N-day no-op / exclude tables that still have downstream consumers | section 2.16 audit-log hard constraints |
| `asset_search.py` | table search / recommendation / field probe / "which tables contain both column A and column B" | section 2.0 index Search row, section 2.14 Candidate tables |
| `label_ops.py` | label read-only exploration / business / BI / category labels / label distribution (write path still goes through the section 3 confirm gate) | section 2.0 index Tag row, section 2.11 Label API contracts |

Shared plumbing: `common.py` (CLI wrapper -- spill auto-handling, stderr
separation, `query-sql` / CsvPath parsing, plus contract-frozen primitives
`get_table` / `search_asset` / `list_labels`).

**WorkspaceId policy**: the CLI auto-injects it (prints `[auto-inject]
WorkspaceId="..."` on stderr). Recipes do NOT re-read the config file. Pass
`--workspace-id <ID>` only for explicit cross-workspace probes.

## Recipe usage

Each recipe shells out to `wedatacli` via `subprocess`. Authentication,
workspace auto-injection, and cross-workspace overrides follow the same
contract every other caller in this skill uses (see SKILL.md section 2.17
"Environment-metadata assumption"). No recipe re-reads the CLI config file.

### lineage.py

```bash
# Single-layer downstream
python3 lineage.py --resource <catalog>.<schema>.<table> \
    --direction OUTPUT --pretty

# Two-layer recursive downstream
python3 lineage.py --resource <catalog>.<schema>.<table> \
    --direction OUTPUT --max-depth 2 --pretty

# Upstream (Direction=INPUT, uppercase; any other value — lowercase / UPSTREAM
# / DOWNSTREAM — is a parameter error, do NOT retry as service outage)
python3 lineage.py --resource <catalog>.<schema>.<table> \
    --direction INPUT --pretty
```

The `--pretty` output follows the SKILL section 2.14 lineage-expansion table
schema: `# / ResourceName / ResourceType / ProcessName`. The default JSON
output also carries `ProcessStats` (e.g. `CODE_STUDIO/SQL=22,
WORK_FLOW_TASK/SQL=2`) for quick producer-type distribution.

Linked-Catalog pre-gate (SKILL.md §2.10 / §2.14; catalog-driven, four-form resolver):

```bash
# BEFORE invoking this recipe (main-agent preferred path):
#   Call common.resolve_and_pregate(<user_input>, mode=<M>) — handles all
#   four input forms in one call. `mode` ∈ {hybrid|exact|semantic}; when
#   omitted, the helper picks per form:
#     ① 3-part FQN         → mode ignored (zero probes)
#     ② 2-part schema.table → hybrid  (search table T --schema S --mode hybrid --verbose)
#     ③ single identifier  → hybrid  (search table T --mode hybrid --verbose)
#     ④ semantic phrase    → semantic (search table "<phrase>" --mode semantic --verbose)
#   ③ vs ④ auto-detection: identifier-shape (letters/digits/_/-) → hybrid;
#   whitespace / CJK / punctuation → semantic. Callers may override with an
#   explicit `mode=`. is_linked_catalog(<catalog>) then reads
#   `wedatacli get catalogs` and asserts source=="CONNECTION" (Linked)
#   vs "METALAKE" (internal). Verdict handling:
#     - verdict=="proceed"    → call lineage.py --skip-pregate (upstream ok)
#     - verdict=="refuse"     → emit refusal one-liner (see below); stop.
#     - verdict=="ambiguous"  → surface up to 3 candidates; ask user to pick.
#     - verdict=="not_found"  → ask user for the missing segment.
#   Refusal template on refuse:
#     ⚠ 外部表暂不支持表血缘分析能力（Linked Catalog: <CatalogName>）。
#
# BANNED probes (all fail in real env — do NOT use):
#   * `GetCatalog` PascalCase Action / `wedatacli get catalog --name`
#     → CatalogNotFound for Linked Catalogs.
#   * `wedatacli get catalog <name>` (positional singular)
#     → unknown or unexpected argument.
#   * `search table --verbose` field `connection_id`
#     → also populated for METALAKE tables; unreliable.
#
# Recipe self-protection: lineage.py embeds a LIGHT gate in main() on the
# 3-part --resource (a single `get catalogs` lookup, unavoidable even with
# --skip-pregate). --skip-pregate only skips the expensive four-form
# search resolver; it does NOT bypass the Linked-Catalog check. On
# refusal, lineage.py exits 0 with the refusal one-liner on stdout and
# `[LINKED_CATALOG]` on stderr — shell wrappers must NOT treat this as a
# failure.
#
# Backend backstop is SCOPE-QUALIFIED: `UnsupportedOperationForLinkedCatalog`
# is raised ONLY for Linked Catalogs registered in `get catalogs`; direct-
# connection catalogs that are NOT registered silently return empty
# lineage instead. That silent-empty case is why the client-side pre-gate
# above MUST NOT be skipped for arbitrary hand-crafted callers.
python3 lineage.py --resource <c.s.t> --direction OUTPUT --pretty
```

### cold_tables.py

```bash
# 90-day cold-tables window (default)
python3 cold_tables.py --catalog C --schema S --pretty

# 7-day window + exclude tables that still have downstream consumers
python3 cold_tables.py --catalog C --schema S --days 7 --exclude-with-downstream --pretty
```

### asset_search.py

```bash
# Keyword recall (default AssetTypes=[TABLE]; limit hard-capped at 100)
python3 asset_search.py --keyword order --limit 15 --pretty

# Per-table GetTable to pull column names (covers "recommend a table" /
# "find a candidate table")
python3 asset_search.py --keyword order --limit 5 --with-fields --pretty

# Strict local filter: table must contain ALL of the required columns.
# This stays compact by default and returns MatchedRequired/MissingRequired;
# add --with-fields only when the caller needs every column in stdout.
python3 asset_search.py --keyword order \
    --require-fields order_purchase_timestamp,order_approved_at --pretty
```

Execution chain:
1. `SearchAsset {Keyword, AssetTypes, MaxResults<=100}` once (WorkspaceId
   auto-injected by CLI as STRING).
2. Slim each server-side hit (~5.6KB) to `{FullName, AssetGuid, AssetType,
   Comment, Owner, Popularity}` (<200B).
3. When `--with-fields` / `--require-fields` is set, call `GetTable
   {CatalogName, SchemaName, TableName}` per candidate to inspect columns.
   `--require-fields` emits only `MatchedRequired` / `MissingRequired` unless
   `--with-fields` is also specified.

### label_ops.py

```bash
# All workspace-visible labels (Type=4 masking excluded by default to keep
# the boundary with the data-classification skill clean)
python3 label_ops.py --pretty

# Keyword probe
python3 label_ops.py --keyword order --pretty

# Business + BI labels only
python3 label_ops.py --types 1,3 --pretty

# Type histogram
python3 label_ops.py --group-by-type
```

Execution chain:
1. `ListLabels {Shared:true, Page:{PageNumber,PageSize}, [KeyWord|Types]}`
   paginated (WorkspaceId auto-injected).
2. Slim each label to `{Id, Name, Type, TypeLabel, SourceType,
   SampleValues(<=4), ValueCount, Description}`.
3. `--group-by-type` is a local histogram -- no extra API calls.

**Write path is NOT covered by this recipe**: `CreateLabels` / `UpdateLabels`
/ `DeleteLabels` / `BatchVoteAssetTag` all go through the SKILL section 3
confirmation gate. The main agent must show a preview, get the user's
confirm, and hand-roll wedatacli. This guards against batch mis-write from
the script layer.

### cold_tables.py execution chain

Aligned with the only-legal path in SKILL section 2.16:
1. `wedatacli get tables --catalog C --schema S` for the candidate set (one
   call; NOT a SubmitJob loop).
2. `wedatacli query-sql --sql "<audit_log SQL>"` for the active set (one
   call; MUST filter by `event_date` partition).
3. Local Python LEFT ANTI JOIN for cold candidates.
4. With `--exclude-with-downstream`, probe each candidate via `ListLineages
   Direction=OUTPUT PageSize=1`.

Parameter constraint: `--days` in [1, 90] (audit_log partition budget cap).

## Contract firewall (anti-hallucination)

Every rule below is verified in the real environment. The recipe layer
enforces them so callers do not need to worry.

| Contract | Enforced in | Hallucination symptom (forbidden) |
|---|---|---|
| `Direction` only accepts uppercase `INPUT` / `OUTPUT` | `lineage.py._list_lineages_page` | UPSTREAM / DOWNSTREAM / lowercase — server rejects as a parameter error (do NOT retry as outage) |
| `ListLineages.WorkspaceId` is auto-injected by CLI — do not pass explicitly | `common.call_action` payload | Passing it makes the CLI reject the call |
| `ListLineages.ResourceName` must be 3-part | argparse (no client check; server rejects) | Missing catalog or schema |
| `CurrentResource.ResourceName / ResourceType` is the real field name | `lineage.py` items assembly | `Name / Type` is a hallucination |
| `Processes[].ProcessType / ProcessSubType` is the real field name | `lineage.py` process_stats | `Type / SubType` is a hallucination |
| `wedatacli get tables` returns lowercase-key JSON `items[].name` | `common.get_tables` | `Items / Name` is the Action-family convention, not the `get` family |
| `query-sql` must use `--sql` / `--sql-file` flag | `common.query_sql` | Positional args (`wedatacli query-sql "SELECT ..."`) are rejected |
| `audit_log` has no `event_type / object_name / resource_full_name` columns | `cold_tables._SQL_TEMPLATE` | Use `get_json_object(request_params, '$.FullName')`; do NOT invent columns |
| `audit_log` MUST filter by `event_date` partition | `cold_tables._SQL_TEMPLATE` | Otherwise the server refuses to execute |
| `Direction=OUTPUT` decides "has downstream" | `cold_tables._has_downstream` | Do not write DOWNSTREAM |
| `SearchAsset.WorkspaceId` is auto-injected by CLI as a **string** | `common.search_asset` payload | Numeric override fails with `json.Unmarshal` error |
| `SearchAsset` does not return `TotalCount` | `common.search_asset` -- only exposes `Items + NextPageToken` | Assuming TotalCount causes infinite paging |
| `SearchAsset.MaxResults` hard-capped at 100 server-side | `common.search_asset` input validation | >100 rejected |
| `GetTable` primary key = 4-tuple `{WorkspaceId, CatalogName, SchemaName, TableName}` | `common.get_table` | AssetGuid / FullName rejected |
| `GetTable` response has one extra layer `Response.Data.Table.*` | `common.get_table` already unwraps it | Reading `.Response.Data.*` returns empty |
| `ListLabels` pagination is nested `Page:{PageNumber,PageSize}` | `common.list_labels` | Top-level PageNumber / PageSize is ignored |
| `ListLabels` response field is `Data.Labels` (NOT `Data.Items`) | `common.list_labels` | Reading `Items` returns empty |
| `ListLabels.KeyWord` is capital K + capital W | `common.list_labels` | `keyword` / `Keyword` returns zero hits |

## Anti-patterns (forbidden)

- x `SELECT * FROM <tbl>.snapshots` / `.files` loops to detect cold tables.
- x `SubmitJob` per-table probes for `last_modified`.
- x `read_file` on a spill file (the `.file` field inside `{truncated:true,
  file:..., ...}`) -- pulls the full payload back into context.
- x Probing lineage-family Actions such as `ListLineage` / `GetLineage` /
  `QueryLineage` when only `ListLineages` exists.
- x Repeatedly running runtime schema lookup for the same Action (idempotent within
  the session).

## Relationship to SKILL.md

Recipes are the **preferred path** for the matching intent. Only fall back
to hand-rolled wedatacli when the recipe does not cover the parameter
combination the user needs. Contract-drift risk is absorbed by this
directory: when a server field / enum changes, we only patch the recipe --
SKILL.md content stays stable.

Regression-shape observations (contract shape only, no environment-specific
figures):

| Scenario | Command | Stable assertion |
|---|---|---|
| Lineage OUTPUT | `lineage.py --resource <3-part> --direction OUTPUT` | Returns `Items[]`, full `Processes[]`, and `ProcessStats` without dropping duplicate-process rows |
| Lineage INPUT | same but `--direction INPUT` | Uses uppercase `INPUT`; empty result is represented explicitly, non-empty result keeps all process details |
| Lineage recursive depth=2 | same but `--direction OUTPUT --max-depth 2` | Expands breadth-first with visited-set protection and layer output |
| Cold-table inventory | `cold_tables.py --catalog C --schema S --days N` | Uses one `get tables`, one partition-filtered `audit_log` SQL, and local diff; `--pretty` previews first 10 rows when >20; pre-flights audit_log availability |
| Cold-table + exclude downstream | same but `--exclude-with-downstream` | Probes only cold candidates with `ListLineages Direction=OUTPUT` |
| Search basic recall | `asset_search.py --keyword <kw> --limit N` | Returns slim candidate items and avoids full `SearchAsset` spill |
| Strict field filter | `asset_search.py --keyword <kw> --require-fields col1,col2` | Returns compact `MatchedRequired` / `MissingRequired`; no full `Columns` unless `--with-fields` is set |
| Label exploration | `label_ops.py --pretty` | Uses `ListLabels {Shared:true, Page:{...}}`, slims values, and excludes Type=4 masking by default |
| Label type histogram | `label_ops.py --group-by-type` | Groups by returned integer `Type` without hard-coding counts |
