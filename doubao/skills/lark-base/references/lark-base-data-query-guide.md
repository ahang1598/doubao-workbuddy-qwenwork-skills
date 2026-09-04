# Base data-query guide

This guide is the entry point for `+data-query`. Use it for common single-table aggregation fewshots and command selection. If the task is a simple group/count/sum/avg/min/max/TopN query and the needed fields are already known, this guide is enough; do not read the full DSL only to confirm the aggregation name.

Read [lark-base-data-analysis-sop.md](lark-base-data-analysis-sop.md) when the task requires cross-table joins, full-table export, local recomputation, row-level backtracking after aggregation, or a final narrative with global conclusions. For complete DSL fields, uncommon field-type/operator details, response details, or error recovery, use [lark-base-data-query.md](lark-base-data-query.md) as the DSL SSOT.

## When to use

Use `+data-query` when the user asks for server-side:

- group by / aggregation
- aggregation functions: `sum`, `avg`, `min`, `max`, `count`, `count_all`, `distinct_count`
- filtered aggregation
- sorted Top N or Bottom N
- global statistical conclusions

Use the aggregation function names above exactly in DSL. Do not write natural-language aliases such as `average` or `distinct count`.

`+data-query` can return dimension field rows, but those rows are grouped by dimension values and do not include `record_id`. Use `+record-list`, `+record-search`, or `+record-get` for row-level output, record identity, or full raw record details.

High-frequency limits and operator facts:

- `pagination.limit` is a result cap, maximum 5000; `+data-query` does not support offset paging.
- Datetime fields in `+data-query` support only `is`, `isEmpty`, `isNotEmpty`, `isGreater`, and `isLess`; do not use `isGreaterEqual` or `isLessEqual` for datetime.
- For continuous calendar windows such as months, quarters, or years, build non-overlapping ranges with open operators in the document timezone: when datetime values may include a time-of-day, use `isGreater` on the window start's local midnight and `isLess` on the next window start's local midnight. Do not use UTC midnight. After splitting adjacent windows, verify their counts sum to the same query with the segment condition removed.
- If `+data-query` returns `ok=true` but an aggregate measure is `null`, treat it as a field-type compatibility signal: check `+field-list` and the aggregation type table in the DSL SSOT before exporting records; fall back to one projected `+record-list` scan only after confirming the measure cannot be computed server-side.
- Need more than 5000 raw rows or one-pass local joins? Use `+record-list --format json --limit 200 --offset <n>` and the analysis SOP's full-export rule.

## Common Fewshots

Count records by a category field:

```bash
lark-cli base +data-query \
  --base-token <base_token> \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"Status","alias":"status"}],"measures":[{"field_name":"Status","aggregation":"count","alias":"count"}],"shaper":{"format":"flat"}}'
```

Sum a number field by category and return Top 10:

```bash
lark-cli base +data-query \
  --base-token <base_token> \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"Region","alias":"region"}],"measures":[{"field_name":"Amount","aggregation":"sum","alias":"total_amount"}],"sort":[{"field_name":"total_amount","order":"desc"}],"pagination":{"limit":10},"shaper":{"format":"flat"}}'
```

Aggregate only records matching a filter:

```bash
lark-cli base +data-query \
  --base-token <base_token> \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"Owner","alias":"owner"}],"measures":[{"field_name":"Amount","aggregation":"sum","alias":"total_amount"}],"filters":{"type":1,"conjunction":"and","conditions":[{"field_name":"Status","operator":"is","value":["Done"]}]},"shaper":{"format":"flat"}}'
```

Use `tableName` when the table ID is unavailable but the table name is known:

```bash
lark-cli base +data-query \
  --base-token <base_token> \
  --dsl '{"datasource":{"type":"table","table":{"tableName":"Orders"}},"measures":[{"field_name":"Amount","aggregation":"sum","alias":"total_amount"}],"shaper":{"format":"flat"}}'
```

## Routing to the DSL SSOT

Read [lark-base-data-query.md](lark-base-data-query.md) when you need:

- the full DSL field reference
- supported aggregations and field types
- filter operator details
- pagination and result limits
- response shape and error recovery
