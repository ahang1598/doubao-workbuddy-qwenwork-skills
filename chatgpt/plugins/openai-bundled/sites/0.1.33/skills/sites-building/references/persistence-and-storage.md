# Persistence and Storage

## Choosing Persistence and Storage

When the user asks for storage, persistence, saved state, accounts, records,
history, progress, or data that should survive across sessions, default to
platform-backed persistence rather than browser-only storage.

Use D1 for persistent structured state that needs to survive page reloads or
sessions, especially when it represents product data rather than transient UI
state.

Typical D1 fits include:

- Users, profiles, settings, tasks, notes, posts, comments, scores, progress,
  leaderboards, and workflow state.
- Relational data that needs filtering, sorting, joins, indexing, ownership
  checks, or durable ids.
- Metadata for uploaded or generated files.

Use R2 for uploads, documents, images, videos, audio, exports, generated assets,
and other blobs.

Use D1 and R2 together when D1 stores metadata and R2 stores bytes, such as file
ownership, filenames, content type, processing status, or searchable fields.

Use browser storage only for device-local, non-authoritative UI preferences such
as dismissed banners, theme choice, or temporary draft state. Do not use
`localStorage`, `sessionStorage`, or in-memory state as the source of truth for
user data that the product is expected to remember.

Leave unused bindings `null`. Do not add persistence or object storage
speculatively, but when the product requires durable state, prefer platform
storage over browser-only storage.

## Adding Persistence and Storage

Use this flow after choosing the storage shape the product needs.

1. Set the needed logical bindings in `.openai/hosting.json`:
   - use `d1`, usually `DB`, when D1 is required.
   - use `r2` when R2 is required.
   - leave unused bindings `null`.
2. For D1-backed state:
   - put schema definitions in `db/schema.ts`.
   - keep D1 access behind a small helper instead of reading the runtime binding
     throughout route handlers.
   - use prepared statements on the raw D1 binding for application queries and runtime initialization. To execute one multiline statement such as `CREATE TABLE`, use `await env.DB.prepare(schemaSql).run()` instead of `env.DB.exec(schemaSql)`. The `exec()` API treats newline-separated input as separate queries and should be reserved for maintenance and one-shot tasks.
   - pass exactly one SQL statement to each `prepare()` call. A single statement may span multiple lines; do not combine multiple semicolon-delimited statements in one prepared SQL string.
   - when one operation needs multiple statements, prepare them separately and execute them with `batch([...])`, for example:

     ```ts
     const d1 = env.DB;
     await d1.batch([
       d1.prepare("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY)"),
       d1.prepare("CREATE INDEX IF NOT EXISTS notes_id_idx ON notes (id)"),
     ]);
     ```

   - generate and inspect Drizzle SQL after schema changes.
   - save generated migration files with the site source.
3. For R2-backed files:
   - keep large file payloads in R2 rather than D1.
   - store searchable, relational, or ownership metadata in D1 when the product
     needs it.
4. Keep the implementation tied to the requested product workflow rather than
   adding generic storage abstractions the site does not yet use.

Do not satisfy a durable-state request with `localStorage`, `sessionStorage`, or
in-memory state unless the user explicitly wants device-local behavior.
