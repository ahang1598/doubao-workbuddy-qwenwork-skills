# Audit Log Query Reference - `system_catalog.wedata.audit_log`

> Load this file from [unity-catalog-manage/SKILL.md](../SKILL.md) only on demand. Read SKILL.md section `2.16 Audit-log hard constraints` first: mandatory `event_date` filter, default 7-day range, sole path for usage inventory, and column-name anti-hallucination are authoritative there. This file only provides command templates and SQL skeletons.

## Invocation

The main agent builds SQL from user intent and executes it through `wedatacli query-sql`.

### Session-scoped prerequisite: resolve the analysis compute resource ID (run once per session)

Every `wedatacli query-sql` in this file MUST pass `--sql-type 1 --compute-resource $UCM_ANALYSIS_RES_ID`. Skipping either flag lets the server pick a default compute resource whose Spark session may not have `system_catalog` registered, producing false `only support namespace with 1 level` / `TABLE_OR_VIEW_NOT_FOUND` / `Doesn't support multi level namespaces` errors on a valid three-part name. Resolve `$UCM_ANALYSIS_RES_ID` once at session start and reuse it across every query below:

```bash
# Step 1: call ListComputeResourceOptions, capture response to a temp file
_UCM_TMP=$(mktemp)
printf '%s' "{\"WorkspaceId\":\"$TENCENTCLOUD_WORKSPACE_ID\",\"Page\":{\"PageNumber\":1,\"PageSize\":100},\"ResourceTypes\":[3]}" \
  | wedatacli ListComputeResourceOptions - > "$_UCM_TMP"

# Step 2: pick the first Resource with AvailableStatus==1 AND BasicInfo.ExecAvailableStatus==1 AND BasicInfo.ResourceType==3
UCM_ANALYSIS_RES_ID=$(python3 -c "
import json
data = json.load(open('$_UCM_TMP'))
resources = (data.get('Response', {}).get('Data', {}) or {}).get('Resources') or []
for r in resources:
    b = r.get('BasicInfo') or {}
    if r.get('AvailableStatus') in (1, '1') and b.get('ExecAvailableStatus') in (1, '1') and b.get('ResourceType') in (3, '3'):
        print((b.get('ResourceId') or r.get('ResourceId') or '').strip())
        break
")
rm -f "$_UCM_TMP"
test -n "$UCM_ANALYSIS_RES_ID" || { echo 'no available analysis compute resource; stop and report to user' >&2; exit 1; }
```

If `$UCM_ANALYSIS_RES_ID` cannot be resolved (empty result or workspace has no analysis resource), stop and report to the user; do NOT fall back to running `wedatacli query-sql` without `--compute-resource`.

### Standard template

```bash
cat > /tmp/audit_query.sql << 'EOF'
SELECT *
FROM system_catalog.wedata.audit_log
WHERE event_date BETWEEN date_sub(current_date(), 7) AND current_date()
  -- add filters from the user request here
LIMIT 100
EOF

wedatacli query-sql \
  --sql-file /tmp/audit_query.sql \
  --sql-type 1 \
  --compute-resource "$UCM_ANALYSIS_RES_ID" \
  --output json
```

### Time-window replacements

| User wording | SQL WHERE condition |
|---|---|
| last 3 days | `event_date BETWEEN date_sub(current_date(), 3) AND current_date()` |
| last 30 days | `event_date BETWEEN date_sub(current_date(), 30) AND current_date()` |
| last 90 days, common for cold-table inventory | `event_date BETWEEN date_sub(current_date(), 90) AND current_date()` |
| 2026-06-01 to 2026-06-15 | `event_date BETWEEN '2026-06-01' AND '2026-06-15'` |
| today | `event_date = current_date()` |
| yesterday | `event_date = date_sub(current_date(), 1)` |
| no range specified | `event_date BETWEEN date_sub(current_date(), 7) AND current_date()` |

General audit queries should usually stay within 31 days. Cold-table and usage-inventory queries may use a 90-day business window but must not exceed 90 days because partition scan cost grows too high.

---

## Column-name anti-hallucination rule

This file intentionally does not hardcode the full `audit_log` schema. Columns may change across versions, and hardcoding causes bad SQL such as `AnalysisException: cannot resolve column` and repeated rewrites.

The only authoritative source is:

```sql
DESCRIBE system_catalog.wedata.audit_log
```

Workflow:

1. Before the first audit-log query in a session, probe real columns.

    ```bash
    cat > /tmp/audit_describe.sql << 'EOF'
    DESCRIBE system_catalog.wedata.audit_log
    EOF
    wedatacli query-sql \
      --sql-file /tmp/audit_describe.sql \
      --sql-type 1 \
      --compute-resource "$UCM_ANALYSIS_RES_ID" \
      --output json
    ```

    Parse real column names from the returned `Schema` or CSV. If DESCRIBE returns only generic columns such as `col_name,data_type,comment` and its CSV contains only the header, run a zero-row projection instead and use the returned `Schema`:

    ```bash
    cat > /tmp/audit_schema.sql << 'EOF'
    SELECT *
    FROM system_catalog.wedata.audit_log
    WHERE event_date BETWEEN date_sub(current_date(), 7) AND current_date()
    LIMIT 0
    EOF
    wedatacli query-sql \
      --sql-file /tmp/audit_schema.sql \
      --sql-type 1 \
      --compute-resource "$UCM_ANALYSIS_RES_ID" \
      --output json
    ```

    The confirmed column set for `system_catalog.wedata.audit_log` is: `id`, `owner_uin`, `app_id`, `event_time`, `event_date`, `uin`, `user_name`, `request_id`, `service_name`, `action_name`, `module_name`, `request_uri`, `request_params`, `response_status`, `error_message`, `created_at`. Still run the probe above at session start to detect drift; if it disagrees, DESCRIBE wins.

    **Reality check on resource-identity columns**: `audit_log` does NOT expose independent columns like `event_type` / `object_type` / `object_name` / `resource_full_name` / `resource_type`. Any prompt or older skeleton that references such names must be treated as hallucination. Resource identity is embedded in `action_name` (operation like `CreateTable`, `GetTable`), `request_uri`, and JSON `request_params`. Extract full names / catalog / schema / table from `request_params` using `get_json_object(request_params, '$.CatalogName')`, `$.SchemaName`, `$.TableName`, `$.FullName`, `$.FullNames[0]`, etc.; the exact key depends on the target `action_name`. Filter operations by `action_name` regex (e.g. `action_name RLIKE '(Create|Get|Update|Delete)(Table|View|Volume|Model)'`) instead of a non-existent resource-type column.

2. When building business SQL, replace placeholders such as `<event_time_col>`, `<action_name_col>`, `<operator_col>` with DESCRIBE-confirmed column names. There is no independent resource-identity column; parse `request_params` JSON with `get_json_object(request_params, '$.CatalogName')` / `'$.SchemaName'` / `'$.TableName'` / `'$.FullName'` / `'$.FullNames[0]'` to reconstruct the full name. Filter by `action_name` regex to scope the resource kind (Table/View/Volume/Model), not a non-existent `<resource_type_col>`.

3. If `cannot resolve column` occurs, immediately return to step 1. Do not guess column names or retry blindly.

SKILL.md treats invented column names as a baseline violation: never put unverified names into SQL.

---

## SQL skeleton A: user behavior audit

For prompts such as `user_001 operations in recent N days`:

```sql
SELECT
    event_time,
    action_name,
    service_name,
    user_name,
    request_uri,
    -- Reconstruct target full name from request_params JSON; adjust JSON path per action.
    coalesce(
        get_json_object(request_params, '$.FullName'),
        concat_ws('.',
            get_json_object(request_params, '$.CatalogName'),
            get_json_object(request_params, '$.SchemaName'),
            get_json_object(request_params, '$.TableName')
        )
    ) AS target_full_name
FROM system_catalog.wedata.audit_log
WHERE event_date BETWEEN date_sub(current_date(), 7) AND current_date()
  AND user_name = 'user_001'
ORDER BY event_time DESC
LIMIT 500
```

## SQL skeleton B: cold / unused table inventory

For prompts such as `tables with no operations in the past N days, sorted by storage size`.

This is the forced path from [SKILL.md](../SKILL.md) section `2.16`: do not use `.snapshots`, `.files`, or `wedatacli inventory` traversal.

Allowed three-step convergence only; the commands and SQL below follow the audit-log contract and must not introduce undescribed system views.

**Step 1**: run `DESCRIBE system_catalog.wedata.audit_log` under the column-name anti-hallucination rule, then confirm the real columns are `action_name`, `request_params`, `user_name`, `event_time`, etc. Do NOT map placeholders such as `<resource_full_name_col>` or `<resource_type_col>` — those columns do not exist. Resource identity must be extracted from `request_params` JSON.

**Step 2**: use one `audit_log` aggregation query to collect the set of table full names that had operations in the last N days; hold that active set in local memory after reading the CSV.

```sql
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
WHERE event_date BETWEEN date_sub(current_date(), 90) AND current_date()
  -- Scope to table-kind actions; verify enum by sampling action_name first.
  AND action_name RLIKE '(Create|Get|Update|Delete|Check)Table(s|Comment|Name|ColumnComment|ColumnsComment)?'
  AND get_json_object(request_params, '$.CatalogName') = '<catalog>'
  AND get_json_object(request_params, '$.SchemaName')  = '<schema>'
```

**Step 3**: use `wedatacli get tables` once to list all tables in the target schema. This maps to backend `ListTableNames`. If storage size or update time is needed, call `wedatacli GetTable` only for candidate tables. Never probe each table with `SubmitJob`. In local Python or awk, diff this list against the active set from step 2; names absent from the active set are cold tables. Sort by storage-size fields returned by `GetTable` when needed.

```bash
wedatacli get tables --catalog <catalog> --schema <schema> [--keyword <kw>]
```

Non-negotiable red lines, to avoid multi-million-token failures:

- Do not run per-table `SELECT * FROM <tbl>.snapshots` or `<tbl>.files`; this was an observed bad path with hundreds of turns and invalid results.
- Do not pull all assets through `wedatacli inventory` and then probe `last_modified` with per-table `SubmitJob`.
- Do not JOIN `information_schema.tables`, `information_schema.*`, or other system views not backed by repo DESCRIBE evidence. The authoritative table list here is `wedatacli get tables` (`ListTableNames`) plus `wedatacli GetTable`, not SQL system views.
- The only allowed chain is: one `audit_log` aggregation SQL + one `get tables` API + one local diff, plus optional targeted `GetTable` for storage size.

## SQL skeleton C: asset popularity ranking

For prompts such as `top/bottom K accessed tables in recent N days`:

```sql
SELECT
    lower(
        coalesce(
            get_json_object(request_params, '$.FullName'),
            concat_ws('.',
                get_json_object(request_params, '$.CatalogName'),
                get_json_object(request_params, '$.SchemaName'),
                get_json_object(request_params, '$.TableName')
            )
        )
    )                                  AS full_name,
    COUNT(*)                           AS access_cnt,
    COUNT(DISTINCT user_name)          AS distinct_users
FROM system_catalog.wedata.audit_log
WHERE event_date BETWEEN date_sub(current_date(), 30) AND current_date()
  AND action_name RLIKE '(Get|Search)Table(s)?'
GROUP BY 1
HAVING full_name IS NOT NULL
ORDER BY access_cnt DESC   -- use ASC for least accessed
LIMIT 10
```

---

## Result handling

Successful `wedatacli query-sql --output json` returns one JSON object with the following shape:

```json
{
  "Status": "SUCCESS",
  "TaskId": "sql.query-8034478a4a95515d",
  "CsvPath": "/Users/<user>/.wedata/query-sql-results/<TaskId>/<sequence>.csv",
  "Schema": [{"Name": "<column>", "Type": "<hive_type>"}],
  "CostMs": 1454
}
```

- `Status`: `SUCCESS`, `FAILED`, or `TIMEOUT`. If not `SUCCESS`, do not retry; show `Message` to the user.
- `CsvPath`: absolute local CSV result path. The main agent reads it; first CSV row is the header from `Schema[].Name`.
- `Schema`: column metadata; `Name` is the column name and `Type` is a Hive type string such as `INT_TYPE` or `STRING_TYPE`.
- `CostMs`: SQL execution time in milliseconds, useful for observing slow queries.

After the first schema probe, read the CSV when useful and keep the column list in session context. No artifact is needed for it. Later audit-log queries in the same session may reuse the cached field list to avoid repeated probing.

## Failure handling

- SQL missing `event_date` filter: refuse execution and regenerate.
- `PERMISSION_DENIED` or `TABLE_NOT_FOUND`: report directly; do not retry.
- `Status: FAILED` with `AnalysisException: cannot resolve column`: return to DESCRIBE and rebuild; do not guess. If the same SQL skeleton plus same column-name failure repeats three times, stop and report as specified in SKILL.md decision rules.
- Other `Status: FAILED`: show `Message` to the user and do not retry.