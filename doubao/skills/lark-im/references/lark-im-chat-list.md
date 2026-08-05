# im +chat-list

List chats the current user is a member of. **Not a search API — there is no `--query` parameter; the call always returns the full member list, paginated.** For keyword-based lookup (e.g. find a group by name or by member), use [`+chat-search`](lark-im-chat-search.md) instead.

**Defaults to groups only**; pass `--types=p2p,group` (or `--types p2p --types group`) to also include p2p single chats. Supports pagination, sort order, and muted-chat filtering.

This skill maps to the shortcut: `lark-cli im +chat-list` (internally calls `GET /open-apis/im/v1/chats`).

## Commands

```bash
# List the user's chats (default sort: create_time, ascending)
lark-cli im +chat-list

# Sort by recent activity (most recently active first)
lark-cli im +chat-list --sort active_time

# Limit page size
lark-cli im +chat-list --page-size 50

# Pagination
lark-cli im +chat-list --page-token "xxx"

# Drop muted chats
lark-cli im +chat-list --exclude-muted

# JSON output
lark-cli im +chat-list --format json

# Preview the request without executing it
lark-cli im +chat-list --dry-run

# Include p2p single chats — comma form
lark-cli im +chat-list --types p2p,group

# Same, using repeat flag instead of CSV
lark-cli im +chat-list --types p2p --types group

# Only p2p single chats
lark-cli im +chat-list --types p2p
```

## Parameters

| Parameter | Required | Limits | Description |
|------|------|------|------|
| `--user-id-type <type>` | No | `open_id` (default), `union_id`, `user_id` | ID type used for `owner_id` in the response |
| `--types <strings>` | No | `group`, `p2p` (comma-separated or repeated) | Chat types to include. Omitted = groups only (backward compatible). |
| `--sort <field>` | No | `create_time` (default, ascending), `active_time` (descending) | Result ordering |
| `--page-size <n>` | No | 1-100, default 20 | Number of results per page |
| `--page-token <token>` | No | - | Pagination token from the previous response |
| `--exclude-muted` | No | - | Drop chats the current user has muted (do-not-disturb); see "Filtering muted chats" below |
| `--format json` | No | - | Output as JSON |
| `--dry-run` | No | - | Preview the request without executing it |

## Output Fields

| Field | Description |
|------|------|
| `chat_id` | Chat ID (`oc_xxx` format) |
| `name` | Chat name |
| `description` | Chat description |
| `owner_id` | Owner ID (type controlled by `--user-id-type`) |
| `external` | Whether the chat is external |
| `chat_status` | Chat status (`normal` / `dissolved` / `dissolved_save`) |
| `chat_mode` | Chat mode discriminator: `group` (regular) / `topic` (topic group) / `p2p` (single chat) |
| `p2p_target_type` | Peer type, e.g., `user` |
| `p2p_target_id` | Peer ID (type controlled by `--user-id-type`) |

## Including p2p single chats

Default behavior lists groups only — same as before this feature. To include p2p, pass `--types`:

| User intent | Call |
|---|---|
| "list my groups" / 我的群 / 我加入了哪些群 | (default, omit `--types`) |
| "list my p2p chats" / 我的单聊 / 我跟谁有 1v1 | `--types p2p` |
| "all my chats" / 全部聊天 / 所有会话 (ambiguous) | `--types p2p,group` |

For p2p rows in the response: `name` is the peer's display name, `owner_id` follows group semantics, `chat_mode = "p2p"`, and `p2p_target_type` / `p2p_target_id` identify the peer.

## Filtering muted chats

`--exclude-muted` drops chats the current user has set to do-not-disturb. After the list call, the CLI batches the page's chat_ids through `POST /open-apis/im/v1/chat_user_setting/batch_get_mute_status` and filters client-side.

When the flag is set, the JSON envelope gains a `filter` sub-object (absent otherwise, so existing consumers are unaffected); `fetched_count == returned_count + filtered_count` always holds:

```json
{
  "chats": [...],
  "filter": {
    "applied": "exclude_muted",
    "fetched_count": 20,
    "returned_count": 17,
    "filtered_count": 3,
    "hint": "Filtered out 3 muted chat(s) on this page (17 remaining); use --page-token to fetch more."
  }
}
```

## Usage Scenarios

### Scenario 1: List my recent chats

```bash
lark-cli im +chat-list --sort active_time --page-size 10
```

### Scenario 2: List my non-muted chats sorted by activity

```bash
lark-cli im +chat-list --sort active_time --exclude-muted
```

### Scenario 3: Iterate all my chats programmatically

```bash
TOKEN=""
while :; do
  RESP=$(lark-cli im +chat-list --page-size 100 --page-token "$TOKEN" --format json)
  echo "$RESP" | jq -r '.data.chats[].chat_id'
  HAS_MORE=$(echo "$RESP" | jq -r '.data.has_more')
  [ "$HAS_MORE" = "true" ] || break
  TOKEN=$(echo "$RESP" | jq -r '.data.page_token')
done
```

## Common Errors and Troubleshooting

| Symptom | Root Cause | Solution |
|---------|---------|---------|
| `--page-size must be an integer between 1 and 100` | page-size is out of range or not an integer | Use an integer between 1 and 100 |
| Permission denied (99991679) | The current user is not authorized for `im:chat:read` | Have the agent platform grant the current user the `im:chat:read` scope |
