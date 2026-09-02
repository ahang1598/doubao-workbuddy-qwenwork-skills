# Field source contract

Normalize every field source with `scripts/pandaai_field_catalog.py` before
candidate generation. The genetic engine consumes the resulting compact JSON,
not the original workbook or long prompt content.

## Accepted modes

1. Excel: one or more sheets with a field-name column such as `字段`, `field`,
   `name`, or `code`; optional `类型/type` and `描述/description` columns.
2. TXT/CSV/TSV: one field per line or a delimited table with the same headers.
3. JSON: an array of field objects or `{ "fields": [...] }`.
4. Direct input: comma-separated names passed with `--fields`.
5. Pure blind: omit sources or pass `--pure-blind`; use documented market
   fields `CLOSE,OPEN,HIGH,LOW,VOLUME,AMOUNT,TURNOVER,MARKET_CAP`.

Examples:

```bash
python scripts/pandaai_field_catalog.py --input fields.xlsx --output fields.json
python scripts/pandaai_field_catalog.py --input fields.txt --output fields.json
python scripts/pandaai_field_catalog.py --fields "ratio_pe_ttm,is_n_income" --output fields.json
python scripts/pandaai_field_catalog.py --pure-blind --output fields.json
```

Use `--expand-mrq` only when the supplied documentation confirms `_mrq_1` to
`_mrq_12` fields. Expansion can multiply the search space substantially.

## Safety and search rules

- Keep only valid identifier-shaped numeric/unknown fields; exclude symbol/date.
- Preserve source, category, type, and description in candidate records.
- Sample across categories instead of exhausting one workbook sheet first.
- Confirm platform availability through a small smoke batch before a large run.
- Do not infer point-in-time safety from a field name. Financial fields require
  explicit publication-lag and survivorship review.
- Never place forward labels or future-return fields in the feature pool.
