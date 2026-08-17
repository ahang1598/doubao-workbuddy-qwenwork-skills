---
name: qw-pages-supabase
description: Prepare Supabase-compatible persistent storage for a dynamic QW Page. Use with qw-pages when a webpage needs database tables, server-side persistence, Supabase access, or database-backed APIs.
---

# QW Pages Supabase

Use this skill only for a dynamic webpage that needs persistent data.

1. Call `qwenwork_pages_provision_database` exactly once with a concise, meaningful `name` in the user's task language to create or reuse the current session's dynamic Page and wait until both the database state and runtime Supabase configuration are ready. Keep its returned domain for migrations and do not provision again during the same publishing workflow.
2. Generate idempotent schema migrations (`CREATE TABLE IF NOT EXISTS`, safe `ALTER` guards where possible) and apply them with `qwenwork_pages_apply_migration`. Use unqualified table names such as `checkins`; never qualify an object with `public.` or create objects in `public`. The service executes SQL in the Page-owned tenant schema.
3. Validate the migration result and inspect the application's Supabase calls without starting the generated server or issuing direct database probes. The desktop Agent never receives runtime database credentials, and routine verification must not use `Bash`, `curl`, repeated public polling, or test writes. Perform live read/write diagnosis only when the user explicitly requests it.
4. Publish through `qw-pages` only when the user explicitly requests publishing; use `qwenwork_pages_publish` with `category: "dynamic"`, `entrypoint`, `port`, and `with_database: true`.

The Page runtime injects `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_INSTANCE_ID` only after the database is ready. These values are never returned to the Agent or Renderer. Do not request Page/Barn tokens, call Page/Barn HTTP endpoints, or search for Pages MCP tools. Do not use direct PostgreSQL connections, expose credentials in browser code, or run destructive data operations or migration DML for verification.
