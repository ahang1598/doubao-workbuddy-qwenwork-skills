# Group Chat Identity Rules

> Warning: Group operations run as the authorized user. The most common source of failure is acting without the required owner/admin privileges. Confirm the user's role in the group before performing privileged actions.

Group-chat operations run as the authorized **user** (UAT). Whether an action succeeds depends on the user's own role in the target chat.

## Identity Selection by Operation

| Operation | Requirement |
|------|-----------------------------------|
| Create group (`+chat-create`) | The authorized user becomes the creator and a member |
| Add members (member-management flow) | The authorized user must already be in the target chat |
| Update group (`+chat-update`) | Permission changes require the authorized user to be the owner or an admin; owner transfer requires the owner |

## Inferring the Owner

When an owner-level action is needed and the owner is unknown, query the group first and check `owner_id`:

1. If the authorized user created the group and `--owner` was **not** specified -> the owner is the current user
2. If `owner_id` is the currently authorized user -> the user can perform owner-level changes
3. Still unclear -> ask the user to confirm who owns the group before making owner-level changes

### When the Owner Is Not the Current User

If the query shows that `owner_id` is not the currently authorized user, the current identity does not have owner privileges. In that case:

- **Owner-only actions such as owner transfer:** require the actual owner to perform the action; have the owner run the operation themselves.
- Explain the limitation clearly to the user instead of retrying blindly.

## Common Pitfalls

### Inviting Members During Group Creation

If `--users` includes users who are mutually invisible to the authorized user, the request may fail. Use two steps instead:

1. Create the group first, excluding invisible users: `lark-cli im +chat-create --name "Group Name"`
2. Add users later with a member-management flow

### Insufficient Privileges

- **232016 / 232002 / 232017:** the current user is not the owner or an admin -> the action requires owner/admin privileges
- **232011:** the current user is not in the group -> join the group first

## References

- [lark-im](../SKILL.md) - all IM commands
