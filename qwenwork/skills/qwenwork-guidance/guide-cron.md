# Scheduled Tasks (Cron) Management Guide

This guide covers managing scheduled tasks through the QwenWork Connector: listing tasks, viewing details and execution logs, enabling/disabling, triggering immediate execution, and deleting tasks.

> **Important:** Creating new scheduled tasks is done via the separate `qoder_cron` tool, NOT via the Connector. The Connector is for querying and managing existing tasks.

## Keys

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork.cron` | query, open | Task list + summary stats |
| `qwenwork.cron.runlogs` | query | Read-only execution logs (filterable, paginated) with conversation navigation metadata |
| `qwenwork.cron.{taskId}` | query, enable, disable, execute, remove | Single task operations |

> **Note:** `runlogs` is a reserved keyword with exact match priority. It will never be treated as a wildcard `{taskId}` value.

> **Run-log policy:** Cron run logs are read-only through `qwenwork.cron.runlogs`. Actions such as `rerun`, `stop`, `execute`, `remove`, or `open` are not exposed through `qwenwork.cron.runlogs`. Cron write/control operations are handled by `qoder_cron` and existing task-level boundaries. Query results may include `subChatId` and `conversation` navigation metadata, but these fields are not Connector write actions.

---

## List All Tasks with Summary

Returns all scheduled tasks with a statistical summary.

```
mcp__qw-builtin__qw_query({ key: "qwenwork.cron" })
```

**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | number | 20 | Results per page (max 100) |
| `offset` | number | 0 | Pagination offset |
| `sort` | string | "created_desc" | Sort order: `"created_desc"` or `"created_asc"` |

**Response structure:**

```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": "uuid-...",
        "name": "Daily report",
        "description": "Generate daily status report",
        "enabled": true,
        "schedule": {
          "kind": "cron",
          "expr": "0 9 * * *",
          "tz": "Asia/Shanghai",
          "label": "Cron: 0 9 * * * (Asia/Shanghai)"
        },
        "prompt": "Generate a daily status report...",
        "model": "claude-sonnet-4-20250514",
        "nextRunAt": "2025-01-31T01:00:00.000Z",
        "lastRunAt": "2025-01-30T01:00:00.000Z",
        "lastRunStatus": "ok",
        "consecutiveErrors": 0,
        "projectName": "my-project",
        "createdAt": "2025-01-01T00:00:00.000Z"
      }
    ],
    "summary": {
      "total": 5,
      "enabled": 3,
      "disabled": 1,
      "withErrors": 1
    },
    "pagination": { "limit": 20, "offset": 0, "total": 5 }
  }
}
```

**Schedule types:**

| Kind | Fields | Label Example |
|------|--------|---------------|
| `at` | `at` (ISO datetime) | `One-time: 2025-02-01T09:00:00Z` |
| `every` | `everyMs` (milliseconds) | `Every 30 minute(s)` |
| `cron` | `expr`, `tz?` | `Cron: 0 9 * * * (Asia/Shanghai)` |

---

## Query Task Detail

Returns full task information including the recent 5 execution logs.

```
mcp__qw-builtin__qw_query({ key: "qwenwork.cron.<taskId>" })
```

**Response includes:**

- All fields from the list view, plus:
- `contextDirs`: Working directories for the task
- `missedRunPolicy`: What happens when a scheduled run is missed
- `lastError`: Error message from the last failed run (parsed for readability)
- `lastDurationMs`: Duration of the last run in milliseconds
- `project`: `{ name, path }` if associated with a project
- `updatedAt`: Last modification timestamp
- `recentRunLogs[]`: Last 5 execution records with `{ id, runAt, durationMs, status, error, trigger, chatId }`

---

## Query Execution Logs

Query execution history across all tasks, with optional filtering.

```
mcp__qw-builtin__qw_query({
  key: "qwenwork.cron.runlogs",
  params: {
    taskId: "uuid-...",
    status: "error",
    limit: 10,
    offset: 0
  }
})
```

**Optional params:**

| Param | Type | Description |
|-------|------|-------------|
| `taskId` | string | Filter logs for a specific task |
| `status` | string | Filter by status: `"running"`, `"ok"`, `"error"` |
| `limit` | number | Results per page (default 20, max 100) |
| `offset` | number | Pagination offset |

**Response structure:**

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "log-uuid",
        "taskId": "task-uuid",
        "taskName": "Daily report",
        "chatId": "chat-uuid",
        "subChatId": "subchat-uuid",
        "conversation": {
          "canNavigate": true,
          "chatId": "chat-uuid",
          "subChatId": "subchat-uuid",
          "deeplink": "qoder-work://notification-click?chatId=chat-uuid&subChatId=subchat-uuid"
        },
        "runAt": "2025-01-30T01:00:00.000Z",
        "durationMs": 15000,
        "status": "ok",
        "error": null,
        "trigger": "scheduler"
      }
    ],
    "pagination": { "limit": 20, "offset": 0, "total": 42 },
    "policy": {
      "runLogActions": "read_only",
      "supportedActions": ["query"],
      "unsupportedActions": ["rerun", "stop", "execute", "remove", "open"],
      "writeSurface": "qoder_cron",
      "note": "Cron write operations are handled by qoder_cron, not qwenwork.cron.runlogs."
    }
  }
}
```

**Log status values:** `running`, `ok`, `error`.

**Trigger values:** `scheduler` (automatic), `manual` (user-triggered), `connector` (triggered via this Connector).

**Conversation navigation:** `conversation` and `subChatId` help the client navigate to the related run conversation when available. This navigation metadata does not mean the Connector supports `open`, `stop`, or `rerun` on `qwenwork.cron.runlogs`.

---

## Enable / Disable a Task

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.cron.<taskId>",
  action: "enable"
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.cron.<taskId>",
  action: "disable"
})
```

- **Enable**: Recalculates `nextRunAt` based on the schedule and adds the task to the scheduler.
- **Disable**: Removes the task from the scheduler and clears `nextRunAt`.

---

## Run a Task Immediately

Trigger a one-off execution of a task, regardless of its schedule or enabled state.

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.cron.<taskId>",
  action: "execute"
})
```

**Response:** `{ success, data: { id, name, chatId }, message }`.

The `chatId` can be used to track the execution. The task runs in the background; the response returns immediately.

---

## Delete a Task

Permanently removes a task and all its execution logs (CASCADE delete).

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.cron.<taskId>",
  action: "remove"
})
```

---

## Workflow: Diagnose and Fix Failing Tasks

1. **Check overview** to find tasks with errors:
   ```
   query({ key: "qwenwork.cron" })
   ```
   Look at `summary.withErrors` and individual tasks where `lastRunStatus: "error"`.

2. **Get details** for a failing task:
   ```
   query({ key: "qwenwork.cron.<taskId>" })
   ```
   Check `lastError` and `recentRunLogs` for error patterns.

3. **Check execution logs** for the task:
   ```
   query({ key: "qwenwork.cron.runlogs", params: { taskId: "<taskId>", status: "error" } })
   ```

4. **Fix and re-enable** if the task was auto-disabled due to consecutive errors:
   ```
   action({ key: "qwenwork.cron.<taskId>", action: "enable" })
   ```

5. **Test** by triggering an immediate run:
   ```
   action({ key: "qwenwork.cron.<taskId>", action: "execute" })
   ```

6. **Verify** the result:
   ```
   query({ key: "qwenwork.cron.<taskId>" })
   ```

## Workflow: Clean Up Disabled Tasks

1. **List** all tasks:
   ```
   query({ key: "qwenwork.cron" })
   ```

2. **Identify** disabled tasks from the results (where `enabled: false`).

3. **Delete** tasks that are no longer needed:
   ```
   action({ key: "qwenwork.cron.<taskId>", action: "remove" })
   ```

---

## Notes

- **Creating tasks** is NOT supported via the Connector. Use the `qoder_cron` tool to create new scheduled tasks.
- Task IDs are UUIDs. Always use the exact ID from query results.
- The `error` field in run logs may contain structured data (e.g., missed execution info). The Connector parses it into a human-readable string automatically.
- Consecutive errors are tracked in `consecutiveErrors`. The application may auto-disable tasks after repeated failures.
- The `chatId` in run logs links to the conversation where the task executed. This can help trace what happened during execution.
