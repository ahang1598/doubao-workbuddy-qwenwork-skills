# im +chat-create

Create a group chat with user identity (`--as user`). You can specify the group name, description, members (users/bots), owner, chat type (private/public), and group mode. Set `--chat-mode topic` to create a topic chat.

This skill maps to the shortcut: `lark-cli im +chat-create` (internally calls `POST /open-apis/im/v1/chats`).

- `--as user` requires the `im:chat:create_by_user` scope.

## Commands

```bash
# Create a private group (default)
lark-cli im +chat-create --name "My Group"

# Create a public group (name is required and must be at least 2 characters)
lark-cli im +chat-create --name "Public Group" --type public

# Create a topic chat
lark-cli im +chat-create --name "Topic Group" --chat-mode topic

# Specify the group owner
lark-cli im +chat-create --name "My Group" --owner ou_xxx

# Invite user members (comma-separated open_ids, up to 50)
lark-cli im +chat-create --name "My Group" --users "ou_aaa,ou_bbb"

# Invite bot members (comma-separated app IDs, up to 5)
lark-cli im +chat-create --name "My Group" --bots "cli_aaa,cli_bbb"

# Invite both users and bots
lark-cli im +chat-create --name "My Group" --users "ou_aaa" --bots "cli_aaa"

# JSON output
lark-cli im +chat-create --name "My Group" --format json

# Create a group and invite a user
lark-cli im +chat-create --name "My Group" --users "ou_aaa,ou_bbb"

# Preview the request without creating anything
lark-cli im +chat-create --name "My Group" --dry-run
```

## Parameters

| Parameter | Required | Limits | Description |
|------|------|------|------|
| `--name <name>` | Required for public groups | Max 60 characters; at least 2 characters for public groups | Group name (`"(no subject)"` for private groups if omitted) |
| `--description <text>` | No | Max 100 characters | Group description |
| `--users <ids>` | No | Up to 50, format `ou_xxx` | Comma-separated user open_ids |
| `--bots <ids>` | No | Up to 5, format `cli_xxx` | Comma-separated bot app IDs |
| `--owner <open_id>` | No | Format `ou_xxx` | Owner open_id (defaults to the authorized user) |
| `--type <type>` | No | `private` (default) or `public` | Group type. Default to `private`; pass `public` only when the user explicitly asks for a discoverable/public group. |
| `--chat-mode <mode>` | No | `group` (default) or `topic` | Group mode; `topic` creates a topic chat (not the same as `group_message_type=thread`). When the user asks for a topic chat, pass `topic` explicitly — do not rely on the default. |
| `--format json` | No | - | Output as JSON |
| `--as <identity>` | No | `user` | Identity type |
| `--dry-run` | No | - | Preview the request without executing it |

> **`--chat-mode topic` vs "normal group with topic-message mode"**: `--chat-mode topic` here creates a 话题群 — the entire group is a topic chat. This is different from "normal group (`chat_mode=group`) + topic-message mode (`group_message_type=thread`)". This CLI exposes only `chat_mode`; `group_message_type` is intentionally not surfaced.

## AI Usage Guidance

Create the group and invite members in one step:

```bash
lark-cli im +chat-create --name "<group name>" --users "ou_aaa,ou_bbb"
```

The authorized user is automatically the group creator and member. If some members cannot be reached, `succeed_type=1` semantics apply on member-management flows: reachable users are added and unreachable ones are returned in `invalid_id_list` instead of failing the whole request — check `invalid_id_list` and report which members could not be added.

## Output Fields

| Field | Description |
|------|------|
| `chat_id` | The new group's ID (`oc_xxx` format) |
| `name` | Group name |
| `chat_type` | Group type (`private` / `public`) |
| `owner_id` | Owner ID (may be empty when a bot creates the group and `--owner` is not specified) |
| `external` | Whether the group is external |
| `share_link` | Group share link (omitted if retrieval fails) |

## Usage Scenarios

### Scenario 1: Create a group and specify the owner

```bash
lark-cli im +chat-create --name "Project Discussion Group" --owner ou_xxx
```

### Scenario 2: Create a group and invite users and a bot

```bash
lark-cli im +chat-create --name "Project Discussion Group" \
  --owner ou_xxx \
  --users "ou_aaa,ou_bbb" \
  --bots "cli_aaa"
```

### Scenario 3: Create a group and send a welcome message

```bash
CHAT_ID=$(lark-cli im +chat-create --name "New Group" --format json | jq -r '.data.chat_id')
lark-cli im +messages-send --chat-id "$CHAT_ID" --text "Welcome, everyone!"
```

## Common Errors and Troubleshooting

| Symptom | Root Cause | Solution |
|---------|---------|---------|
| Permission denied (99991672) | The app does not have `im:chat:create` (bot) or `im:chat:create_by_user` (user) permission enabled | Enable the required permission for the app in the Open Platform console |
| `--name is required for public groups and must be at least 2 characters` | A public group was created without a name or with a name shorter than 2 characters | Provide a name with at least 2 characters |
| `--name exceeds the maximum of 60 characters` | The group name is too long | Shorten the name to 60 characters or fewer |
| `--description exceeds the maximum of 100 characters` | The group description is too long | Shorten the description to 100 characters or fewer |
| `--users exceeds the maximum of 50` | Too many user members were provided | Split the operation into batches and add more members later |
| `--bots exceeds the maximum of 5` | Too many bot members were provided | Invite at most 5 bots at once |
| `invalid user id: expected open_id (ou_xxx)` | Invalid user ID format | Use the `ou_xxx` format for users |
| `invalid bot id: expected app ID (cli_xxx)` | Invalid bot ID format | Use the `cli_xxx` format for bots |
| `invalid --owner: expected open_id (ou_xxx)` | Invalid owner ID format | Use the `ou_xxx` format for the owner |
| `bot is invisible to user` (232043) | A target member is mutually invisible to the caller | Add such members later via a member-management flow after the group is created |

## References

- [lark-im](../SKILL.md) - all IM commands
