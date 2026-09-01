# Structured Error Handling

Every failed CLI command writes one JSON object to stderr. Read
`error_code`, `retryable`, and `next_action`; do not branch on translated
message text or an old numeric API code.

```json
{
  "schema_version": "xparse_error.v1",
  "error_code": "FILE_TOO_LARGE",
  "message": "file exceeds the current service limit",
  "actual_value": {"size_bytes": 12582912},
  "limit": {"source": "service", "max_file_size_bytes": 10485760},
  "retryable": false,
  "next_action": "REDUCE_FILE",
  "request_id": "optional-request-id",
  "task_id": "optional-task-id"
}
```

## Field contract

| Field | Agent rule |
|-------|------------|
| `error_code` | Stable decision key. Prefer it over `message` or `details.api_code`. |
| `message` | Concise user-facing explanation. It can be localized. |
| `actual_value` | Current file size, page count, required pages, attempts, or another observed value. It is `null` when unavailable. |
| `limit` | Current service/account capability. Only use a value with `source: service`; never replace it with a remembered constant. It is `null` when the service did not report a limit. |
| `retryable` | `true` means the same arguments can be retried safely. `false` means fix, wait, authenticate, reduce, or ask first. |
| `next_action` | Stable action enum such as `FIX_INPUT`, `REDUCE_FILE`, `REDUCE_PAGES`, `WAIT_AND_RETRY`, `AUTHENTICATE`, `UPGRADE_OR_USE_PAID`, or `CONTACT_SUPPORT`. |
| `upgrade_url` | Optional purchase/upgrade URL. Showing it does not authorize a paid retry. |
| `request_id`, `task_id` | Preserve when reporting or escalating a failure. |
| `details` | Additional diagnostics, including an upstream numeric `api_code` or batch `failures`. Do not use details to override base fields. |

## Stable codes and decisions

| `error_code` | Decision |
|--------------|----------|
| `FILE_NOT_FOUND` | Stop and obtain the correct accessible path. |
| `EMPTY_FILE` | Stop and obtain a non-empty file. |
| `UNSUPPORTED_FILE_TYPE` | Stop or convert to a supported type. Never silently switch to a paid route. |
| `FILE_TOO_LARGE` | Read `actual_value` and the service-sourced `limit`; reduce/split the physical file or ask before an explicit paid retry. `--page-range` does not reduce upload bytes. |
| `PAGE_LIMIT_EXCEEDED` | Reduce the page selection using the reported limit. |
| `PAID_QUOTA_REQUIRED` | Stop. Explain current daily/package values and reset time, then wait for explicit paid approval. |
| `CAPABILITY_QUERY_FAILED` | Do not invent quota or limits. Retry only when `retryable=true`; otherwise report `request_id`. |
| `SPLIT_FAILED` | Stop; do not parse an incomplete segment set. Preserve the original file. |
| `MERGE_FAILED` | Stop; do not present partial output as a complete document. Surface segment/task identifiers. |
| `RETRY_EXHAUSTED` | The CLI already used its bounded retry budget. Do not immediately repeat the same command. Follow `next_action` and preserve `request_id`. |
| `RATE_LIMITED` / `NETWORK_ERROR` / `SERVICE_ERROR` | Retry only when `retryable=true`; respect `WAIT_AND_RETRY`. |
| `AUTHENTICATION_FAILED` / `OAUTH_FAILED` | In WorkBuddy, ask the user to reconnect the Connector. Never request or print tokens. |
| `INVALID_ARGUMENT`, `INVALID_PAGE_RANGE`, `INVALID_PASSWORD` | Correct the input, then run once with the corrected arguments. |
| `BATCH_PARTIAL_FAILURE` | Inspect every `details.failures[]` item. Never hide failed inputs or claim the batch fully succeeded. |

## Quota and paid boundary

Run `quota --output json` when explaining `PAID_QUOTA_REQUIRED`. Routing uses
the server's current `daily_pages_remaining` and, only when returned for an
authenticated request, `free_package.free_remain_count`. The historical
`free_count` field is display-only and must not be used as remaining quota.

Authentication is not approval to spend. Never turn `--api auto` or `--api
free` into `--api paid` after an error. Wait for the user's explicit approval,
even when `upgrade_url` is present.

When the user explicitly chooses to purchase credits, use the `upgrade_url`
returned by the current service. If it is absent, direct the user to the account's
regional support or portal; never invent or substitute another region's URL.

## Retry boundary

The CLI automatically retries recognized transient parse failures with a
bounded backoff. Therefore:

- when `retryable=true`, follow `next_action` and retry at most once at the Agent
  layer;
- when `error_code=RETRY_EXHAUSTED`, do not immediately retry again;
- when `retryable=false`, changing only the timing is not a valid recovery;
- never silently skip a failed parse or failed batch item.

## Reporting template

Tell the user what failed, the real observed value, the current service limit,
and the required next action. Include `request_id`/`task_id` when present. Do
not paste credentials, verbose HTTP headers, or a stale limit from this Skill.
