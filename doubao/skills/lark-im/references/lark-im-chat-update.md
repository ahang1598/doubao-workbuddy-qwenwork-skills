# im +chat-update

Update a group's name or description. Supports both **TAT (bot)** and **UAT (user)** identity.

This skill maps to the shortcut: `lark-cli im +chat-update` (internally calls `PUT /open-apis/im/v1/chats/:chat_id`).

## Commands

```bash
# Update the group name
lark-cli im +chat-update --chat-id oc_xxx --name "New Group Name"

# Update the group description
lark-cli im +chat-update --chat-id oc_xxx --description "Updated group description"

# Update multiple fields at once
lark-cli im +chat-update --chat-id oc_xxx \
  --name "Q2 Project Team" \
  --description "Owns Q2 goal tracking"

# Preview the request without executing it
lark-cli im +chat-update --chat-id oc_xxx --name "Test" --dry-run
```

## Parameters

### Required

| Parameter | Description |
|------|------|
| `--chat-id <oc_xxx>` | Group ID |

### Optional Fields

| Parameter | Limits | Description |
|------|------|------|
| `--name <name>` | Max 60 characters | Group name |
| `--description <text>` | Max 100 characters | Group description |

### Global Parameters

| Parameter | Description |
|------|------|
| `--format json` | Output as JSON (default) |
| `--dry-run` | Preview the request without executing it |

## Usage Scenarios

### Scenario 1: Rename a group and update its description

```bash
lark-cli im +chat-update --chat-id oc_xxx \
  --name "Q2 Project Team" \
  --description "Owns Q2 goal tracking"
```

## Common Errors and Troubleshooting

| Symptom | Root Cause | Solution |
|---------|---------|---------|
| `invalid --chat-id: expected chat ID (oc_xxx)` | Invalid chat_id format | Use a valid `oc_xxx` chat ID |
| `--name exceeds the maximum of 60 characters` | Group name too long | Shorten the name to 60 characters or fewer |
| `--description exceeds the maximum of 100 characters` | Group description too long | Shorten the description to 100 characters or fewer |
| `at least one field must be specified to update` | No update field was provided | Specify at least one field to update |
| Permission denied (99991679) | Missing `im:chat:update` permission | Ask the agent platform to grant `im:chat:update` |
## AI Usage Guidance

### Permission Check

The caller must have permission to update the target group. If ownership or admin status is unclear, query the group first and confirm `owner_id` and manager information before updating.

## References

- [lark-im](../SKILL.md) - all IM commands
