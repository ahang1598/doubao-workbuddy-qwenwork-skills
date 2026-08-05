# SQLite

Use indexes to reduce the rows SQLite scans for common queries. Create them from actual query patterns rather than speculatively because every index consumes storage and adds work to inserts, updates, and deletes. SQLite maintains indexes automatically as referenced rows change.

## Choose and Create Indexes

- Index columns used regularly in query predicates, columns that must be unique, or column combinations queried together.
- Do not add a redundant index for the rowid or an `INTEGER PRIMARY KEY`, which aliases the rowid.
- Use descriptive names such as `idx_<table>_<columns>`.
- Use `CREATE UNIQUE INDEX` when SQLite must enforce uniqueness.

```sql
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
ON orders(customer_id);
```

After creating an index, run `PRAGMA optimize` so SQLite collects statistics that help its query planner choose efficient plans.

## Use Multi-Column and Partial Indexes

Order multi-column indexes around the queries they must serve. SQLite can use the index when a query includes all indexed columns or a leftmost prefix. An index on `(customer_id, transaction_date)` supports predicates on `customer_id` alone or both columns, but not on `transaction_date` alone.

Use a partial index to omit rows that common queries do not need. This can reduce index size and the work required to maintain it:

```sql
CREATE INDEX IF NOT EXISTS idx_orders_open_status
ON orders(status)
WHERE status != 'complete';
```

## Inspect and Verify Indexes

List index definitions from the SQLite schema:

```sql
SELECT name, type, sql
FROM sqlite_schema
WHERE type = 'index';
```

Use `EXPLAIN QUERY PLAN` with representative queries and confirm the plan reports `USING INDEX <name>`:

```sql
EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE customer_id = ?;
```

SQLite cannot modify an existing index definition. Drop and recreate the index when its columns or predicate must change. Do not create indexes that reference other tables or use non-deterministic functions.
