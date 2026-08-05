---
name: qwenwork-guidance
version: 1.0.8
description: Routing guide for the built-in QwenWork Connector tools (mcp__qw-builtin__qw_query / mcp__qw-builtin__qw_action). Load ONLY right before calling them to view or manage QwenWork's OWN tasks/sessions or app configuration, or when a qw tool result explicitly asks. Before loading, always check whether another skill or tool can do the job — if so, use that instead. Unless the user explicitly asks, never use it to view skills, plugins, MCP servers, or third-party connectors. Never load in any non-essential scenario (content creation, PPT/docs, coding, research, web tasks), even when the topic is QwenWork itself. If in doubt, do not load.
description_zh: 内置千问办公 Connector 工具（mcp__qw-builtin__qw_query / mcp__qw-builtin__qw_action）的路由指南。仅在「即将调用这两个工具查看或管理 QwenWork 自身的任务/会话或应用配置」或 qw 工具结果明确要求时才加载。加载前必须先思考能否用其他 skill 或 tool 替代，能替代就不用本技能；除非用户明确要求，否则不通过本技能查看技能、插件、MCP 服务及第三方连接器。其他非必要场景（内容创作、PPT/文档、编码、调研、联网任务）一律不加载，即使主题就是 QwenWork/千问办公本身；拿不准时不要加载。
---

# QwenWork Connector Guidance

QwenWork exposes its full configuration capabilities through a built-in MCP Connector. You interact with it using two tools:

- **`mcp__qw-builtin__qw_query`** -- Read-only queries. Input: `{ key }`.
- **`mcp__qw-builtin__qw_action`** -- Execute operations. Input: `{ key, action, params? }`.

All operations use a **dot-separated key hierarchy** (e.g. `qwenwork.settings.connector.market.github`). Start with `query({ key: "qwenwork" })` to discover all available keys. When a query result returns a `key` field, use that exact key for follow-up operations instead of constructing one from `name`.

## Brand And Connector Key Boundary

- **User-visible product name**: use QwenWork in English-facing guidance and 千问办公 in Chinese-facing user text.
- **Connector protocol keys**: use the `qwenwork.*` namespace in all keys, code examples, and tool calls. Treat older QoderWork-prefixed key strings as compatibility-only input, not as guidance for new calls.
- **Tool names**: keep `mcp__qw-builtin__qw_query`, `mcp__qw-builtin__qw_action`, and legacy `qoder_*` task tool names unchanged.
- **Self switch UI name**: refer to the product UI switch as `QwenWork Connector` in English guidance and `千问办公连接器` in Chinese user-facing text.

---

Prefer the QwenWork Connector for QwenWork application state. Use low-level task tools such as `qwenwork_task_list_all`, `qwenwork_task_get_detail`, `qwenwork_task_cancel`, `qwenwork_task_send_message`, or `qwenwork_task_submit_response` only when the Connector keys are unavailable or the user explicitly asks for those low-level tools.

## High-Priority Task Routing

When the user asks about latest/recent/current QwenWork tasks, what was done, whether work is complete/done, task status/progress, stuck/running tasks, historical sessions, or continuing an old task:

1. Query `qwenwork.tasks` first.
2. Query `qwenwork.tasks.{chatId}` for the target task before summarizing detail or taking action.
3. Use `execute` on `qwenwork.tasks.{chatId}` for `stop`, `send_message`, or `respond`.
4. Do not use memory/awareness as the primary source for QwenWork task status or completion. Use it only as secondary background after the Connector task query, or if the Connector is unavailable.

---

## Basic Concepts

- **QwenWork Connector**: the built-in control plane for the QwenWork app. It exposes app state and app operations through `qwenwork.*` keys.
- **Connector key**: a dot-separated resource path. Query the parent key before acting on a child key when unsure.
- **Action vocabulary**: use `query` for state, `open` only for UI navigation, and semantic actions like `enable`, `disable`, `install`, `remove`, `execute`, or `connect` for real operations.
- **Chat / task**: a top-level QwenWork conversation shown as a task in the sidebar. It has a stable `chatId` and can be queried through `qwenwork.tasks.{chatId}`.
- **SubChat**: the execution thread for a chat turn. A chat may have multiple subChats over time.
- **QwenWork task list**: `qwenwork.tasks` lists QwenWork tasks/chats across history by default. Pass `sourceChatId` only when the user specifically asks for sub-tasks created by one source chat.
- **Source chat**: the chat that created another QwenWork task. It is a filter, not the default scope.
- **AskUser task**: a task paused on an `AskUserQuestion` tool call. Inspect the task detail first, then respond with `operation: "respond", response: "answer"`.

Do not confuse QwenWork tasks with scheduled cron tasks:

- Use `qwenwork.tasks` for QwenWork tasks/chats and historical sessions. Use `params.sourceChatId` only for source-scoped sub-tasks.
- Use `qwenwork.cron` and `qwenwork.cron.runlogs` for scheduled tasks and their run history.

## Complete Key Reference

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork` | query | App global status (version, platform, all available keys) |
| `qwenwork.settings` | query, open | Settings overview (all setting categories) |
| `qwenwork.settings.connector` | query, open | All Agent-manageable connector entities (builtin integrations + Market MCP + custom MCP). Does not include the QwenWork Connector self switch. Supports keyword param. |
| `qwenwork.settings.connector.builtin.apple` | query, open | Apple connectors list |
| `qwenwork.settings.connector.builtin.apple.{id}` | query, enable, disable | Single Apple connector toggle |
| `qwenwork.settings.connector.builtin.ms365` | query, open, connect, disconnect | Microsoft 365 connector status |
| `qwenwork.settings.connector.builtin.ms365.{subId}` | query, enable, disable | Microsoft 365 sub-connector toggle |
| `qwenwork.settings.connector.builtin.browser` | query, open, enable, disable | Browser connector status and toggle |
| `qwenwork.settings.connector.builtin.dws` | query, open, connect, disconnect, enable, disable, install, uninstall | DingTalk connector (install/uninstall, auth, login/logout, enable/disable) |
| `qwenwork.settings.connector.builtin.lark` | query, open, enable, disable, execute | Feishu (Lark) connector (download/register through enable, soft toggle, logout/reauth via execute) |
| `qwenwork.settings.connector.builtin.computer_use` | query, open, enable, disable | Computer Use connector status. The enable action returns a safety notice; the user must turn it on manually. |
| `qwenwork.settings.connector.market` | query, open | Connector Market list. Items can be builtin product connectors or Market MCP servers. Supports keyword param. |
| `qwenwork.settings.connector.market.{name}` | query, open, enable, disable, install, uninstall, execute | Single Market MCP server only (install/uninstall = enable/disable). Do not use this pattern for builtin market items; use the returned `key`. |
| `qwenwork.settings.connector.custom` | query, open, add | Custom (user-added) MCP servers list. Supports keyword param and add action. |
| `qwenwork.settings.connector.custom.{name}` | query, open, update, enable, disable, remove, execute | Custom MCP server CRUD |
| `qwenwork.settings.preferences` | query, open, update | User preferences (auto-launch, MCP lazy load, prevent sleep, etc.) |
| `qwenwork.settings.profile` | query, open | User profile (account info, subscription tier) |
| `qwenwork.settings.system` | query, open, update | System settings (auto-launch, prevent sleep, close window action) |
| `qwenwork.settings.keyboard` | query, open | Keyboard shortcuts (all configurable actions and bindings) |
| `qwenwork.settings.appshot` | query, open, update | App Snapshot shortcut settings |
| `qwenwork.settings.appUpdate` | query, open, execute | App version and manual update check. `execute` only checks for updates; install/restart remains user-confirmed in UI. |
| `qwenwork.settings.voiceInput` | query, open, update, enable, disable | Global voice input shortcut and transcription settings |
| `qwenwork.settings.vm` | query, open, enable, disable | Secure workspace (status, version, enable/disable) |
| `qwenwork.settings.experimental` | query, open, update | Experimental feature toggles (MCP lazy load, Prompt Suggestions, QuickPick) |
| `qwenwork.settings.permissions` | query, open, execute | macOS system permissions (6 permission types) |
| `qwenwork.settings.plugins` | query, open | Installed expert suites/plugins list |
| `qwenwork.settings.plugins.{folderName}` | query, enable, disable, remove | Single expert suite/plugin operations |
| `qwenwork.settings.skills` | query, open | Installed + builtin skills list |
| `qwenwork.settings.skills.market` | query, execute | Skill marketplace (search, install) |
| `qwenwork.settings.skills.{folderName}` | query, enable, disable, remove | Single skill operations |
| `qwenwork.usage` | query | Credit usage (plan, add-on, Teams shared, remaining %) |
| `qwenwork.tasks` | query | QwenWork tasks/chats across history by default. Supports pagination and sourceChatId filtering. |
| `qwenwork.tasks.{chatId}` | query, execute | Single QwenWork task/chat detail and operations: stop, send_message, respond |
| `qwenwork.cron` | query, open | Scheduled tasks list + summary stats |
| `qwenwork.cron.runlogs` | query | Task execution logs (filter by taskId, status; pagination) |
| `qwenwork.cron.{taskId}` | query, enable, disable, execute, remove | Single task operations |
| `qwenwork.channels` | query, open | IM channels overview (status, capabilities, errors) |
| `qwenwork.channels.{channelId}` | query, enable, disable, execute | Single channel (detail, toggle, restart, QR auth) |
| `qwenwork.channels.{channelId}.pairings` | query, execute, remove | Channel pairing management |
| `qwenwork.feedback` | open | Open feedback dialog (prefill content, user reviews and submits) |

Channel configuration CRUD is intentionally UI-only. Do not invent `update`, `remove`, `configure`, or `delete` actions for `qwenwork.channels.{channelId}` channel configuration; use `action: "open"` on `qwenwork.channels` so the user can edit credentials, secrets, access policy, or delete channel config in the Channels UI.

---

## UI-Only / Hidden Settings Boundary

Some Settings tabs are intentionally not exposed through QwenWork Connector:

| Settings tab | Product boundary |
|--------------|------------------|
| Commands | Hidden feature. UI-only and must not be exposed to Agent/model. |
| Models | Hidden feature. UI-only and must not be exposed to Agent/model. |
| Desk | The product concept is Desk. The legacy `legokit` tab id is an implementation detail and remains UI-only until a Desk capability contract is defined. Do not call it LegoKit in user-facing Connector guidance. |

Do not invent `qwenwork.settings.commands`, `qwenwork.settings.models`, or `qwenwork.settings.legokit` keys. Start from `query({ key: "qwenwork" })` when unsure.

---

## Scenario Routing

For complex operations, read the corresponding guide file before proceeding:

| User Intent | Guide File |
|-------------|------------|
| Install/uninstall skills, search skill market, enable/disable skills | `guide-skills.md` |
| Add/remove/configure MCP servers, check MCP connection status | `guide-mcp.md` |
| Manage scheduled/cron tasks, check execution logs, run tasks | `guide-cron.md` |
| View/operate QwenWork tasks/chats, historical sessions, sub-tasks, stop a running task, send a task message, respond to AskUser | `guide-tasks.md` |
| Manage IM channels (DingTalk/Feishu/WeChat/WeCom), QR authentication, pairing | `guide-channels.md` |
| Manage builtin connectors (Apple/Microsoft 365/Browser/DingTalk (DWS)/Feishu (Lark)/Computer Use), login DingTalk or Feishu (Lark) | `guide-connectors.md` |
| Settings (preferences, system, VM, keyboard, permissions, experimental, profile, usage) | Documented inline below |

---

## Common Action Patterns

### Action Selection Rule

Do not map "open" or Chinese "打开" to the `open` action by default. For a feature, connector, MCP server, plugin, or skill, "open/打开" usually means turning it on:

- Use `enable` for installed features, connectors, custom MCP servers, plugins, and skills.
- Use `install` for Market MCP servers when the user asks to open/turn on/use an uninstalled Market MCP server. If the item came from `qwenwork.settings.connector.market`, use its returned `key` first; only `type: "market"` items use `qwenwork.settings.connector.market.{name}`.
- Use `open` only when the user clearly asks to navigate to a page, settings tab, dialog, or UI location, such as "open the settings page", "go to Connector settings", "show me the Plugins page", or "打开设置页".
- After a query, do not call `open` just to show the result. The QwenWork card already gives the user a visual result and an Open button when navigation is available.

### Query

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector" })
```

### Enable / Disable

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.custom.my-server", action: "enable" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.custom.my-server", action: "disable" })
```

### Computer Use Special Rule

Computer Use is intentionally different from other connectors. You may query its state, call enable to return the safety notice, disable it, or open the Connectors page for the user. The enable action does not turn on desktop control; it explains that the user must turn Computer Use on manually.

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.computer_use" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.computer_use", action: "enable" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.computer_use", action: "disable" })
```

### Install / Uninstall (Market MCP)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.market.notion", action: "install" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.market.notion", action: "uninstall" })
```

### Open Settings Page (Navigation Only)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector", action: "open" })
```

### Update

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.preferences",
  action: "update",
  params: { autoLaunchEnabled: false }
})
```

### Execute

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom",
  action: "add",
  params: { name: "my-server", config: { command: "npx", args: ["-y", "some-mcp-server"] } }
})
```

### QwenWork Tasks

Use this first for requests like "latest task", "recent tasks", "what did I/you do", "is it complete", "why is it stuck", "continue that old task", or "answer the AskUser task":

```
mcp__qw-builtin__qw_query({ key: "qwenwork.tasks" })
```

```
mcp__qw-builtin__qw_query({
  key: "qwenwork.tasks",
  params: { limit: 20, offset: 0, includeArchived: true }
})
```

```
mcp__qw-builtin__qw_query({
  key: "qwenwork.tasks",
  params: { sourceChatId: "source-chat-id" }
})
```

```
mcp__qw-builtin__qw_query({ key: "qwenwork.tasks.<chatId>", params: { limit: 5 } })
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: { operation: "stop" }
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: { operation: "send_message", message: "Continue with option A" }
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: {
    operation: "respond",
    response: "answer",
    answers: { "Question header": "Selected option label" }
  }
})
```

### Remove

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.custom.my-server", action: "remove" })
```

---

## Settings Quick Reference

These settings keys are straightforward query/update operations and do not require a separate guide.

### Preferences (`qwenwork.settings.preferences`)

Query returns all preference items. Update with key-value pairs:

| Setting Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `autoLaunchEnabled` | boolean | true | Launch at system startup |
| `mcpLazyLoad` | boolean | true | MCP lazy loading |
| `preventSleepEnabled` | boolean | false | Prevent system sleep |
| `quickPickEnabled` | boolean | false | QuickPick global shortcut window |
| `closeWindowAction` | string | "ask" | Close window behavior: "ask" / "minimize" / "quit" |

```
// Update example
action({ key: "qwenwork.settings.preferences", action: "update", params: { preventSleepEnabled: true } })
```

### Profile (`qwenwork.settings.profile`)

Read-only. Returns account info and subscription tier.

```
query({ key: "qwenwork.settings.profile" })
```

### System (`qwenwork.settings.system`)

Query and update system-level settings (auto-launch, prevent sleep, close window action).

```
action({ key: "qwenwork.settings.system", action: "update", params: { preventSleepEnabled: true } })
```

### Keyboard (`qwenwork.settings.keyboard`)

Read-only. Returns all configurable keyboard shortcuts and their current bindings.

```
query({ key: "qwenwork.settings.keyboard" })
```

### App Update (`qwenwork.settings.appUpdate`)

Query returns the current version, update runtime state, and whether update checks are available. Execute only performs the same manual update check as the Settings tab; installing/restarting an update stays in the user-confirmed update UI.

```
query({ key: "qwenwork.settings.appUpdate" })
action({ key: "qwenwork.settings.appUpdate", action: "execute", params: { operation: "checkForUpdates" } })
```

### Voice Input (`qwenwork.settings.voiceInput`)

Query returns the voice input enable state, overlay state, speaker recognition state, shortcut mode, single-key keycode, combo shortcut, and current Fn-key status. Update supports `enabled`, `overlayEnabled`, `voiceprintEnabled`, `mode`, `singleKeycode`, and `shortcut`. Update accepts exactly one setting field per call; send separate update actions for multi-step changes.

```
query({ key: "qwenwork.settings.voiceInput" })
action({ key: "qwenwork.settings.voiceInput", action: "enable" })
action({ key: "qwenwork.settings.voiceInput", action: "update", params: { voiceprintEnabled: true } })
action({ key: "qwenwork.settings.voiceInput", action: "update", params: { mode: "combo" } })
action({ key: "qwenwork.settings.voiceInput", action: "update", params: { shortcut: "ctrl+shift+space" } })
```

### Secure Workspace (`qwenwork.settings.vm`)

Query secure workspace status and version. Enable or disable it:

```
query({ key: "qwenwork.settings.vm" })
action({ key: "qwenwork.settings.vm", action: "enable" })
action({ key: "qwenwork.settings.vm", action: "disable" })
```

### Experimental Features (`qwenwork.settings.experimental`)

Query and toggle experimental feature flags:

```
query({ key: "qwenwork.settings.experimental" })
action({ key: "qwenwork.settings.experimental", action: "update", params: { promptSuggestionsEnabled: true } })
```

### Permissions (`qwenwork.settings.permissions`)

macOS only. Query status of 6 permission types: `fullDiskAccess`, `screenCapture`, `accessibility`, `automation`, `notification`, `location`.

```
// Check all permissions
query({ key: "qwenwork.settings.permissions" })

// Request accessibility access (triggers system prompt)
action({ key: "qwenwork.settings.permissions", action: "execute", params: { operation: "requestAccess", type: "accessibility" } })

// Open system settings for a specific permission
action({ key: "qwenwork.settings.permissions", action: "execute", params: { operation: "openSystemSettings", type: "fullDiskAccess" } })
```

### Credit Usage (`qwenwork.usage`)

Read-only. Returns plan credits, add-on credits, Teams shared resource pack, and aggregate remaining percentage.

```
query({ key: "qwenwork.usage" })
```

### Feedback (`qwenwork.feedback`)

Opens the feedback dialog in QwenWork UI. Optionally prefill content for user to review. The user must manually review and submit -- the agent cannot submit directly.

```
// Open empty feedback dialog
action({ key: "qwenwork.feedback", action: "open" })

// Open with prefilled content
action({ key: "qwenwork.feedback", action: "open", params: { content: "Description of the issue..." } })
```

---

## Important Notes

1. **Connectors include MCP**: Connector Market listing lives at `connector.market`, but individual `connector.market.{name}` keys are only for Market MCP servers. Builtin product connectors returned by the Market list keep their own `connector.builtin.*` keys. Custom MCP servers live under `connector.custom.*`. There is no separate `qwenwork.settings.mcp` namespace.
2. **Collection add action**: add a custom MCP server with `key: "qwenwork.settings.connector.custom"` and `action: "add"`; do not use a separate add key.
3. **Wildcard parameters**: `{param}` in a key pattern matches any single segment. The extracted value is passed to the handler (e.g. querying `qwenwork.settings.connector.market.github` extracts `name = "github"`).
4. **Segment count must match**: `qwenwork.settings.connector.market` will NOT match `qwenwork.settings.connector.market.github` -- they have different segment counts.
5. **Error handling**: All responses follow `{ success: boolean, data?, message?, error? }`. On failure, check the `error` field for details.
6. **Discovery**: When unsure about available keys, start with `query({ key: "qwenwork" })` to get the full list of registered keys and their supported actions.
7. **install/uninstall**: These are semantic aliases for enable/disable, used only with Market MCP servers (`connector.market.{name}`) unless a builtin connector explicitly documents install/uninstall support on its returned `key`.
8. **QwenWork task scope**: `qwenwork.tasks` defaults to all non-deleted QwenWork tasks/chats, including historical sessions. Only use `params.sourceChatId` when the user asks for sub-tasks created by a specific source chat.
9. **AskUser response safety**: always query `qwenwork.tasks.{chatId}` before responding. Only call `respond` after the detail shows a pending AskUser or permission request.
10. **Do not use memory as a task-status fallback**: when the user asks "latest task", "what did I do", or "is it complete", use `qwenwork.tasks` and then `qwenwork.tasks.{chatId}`. Memory/awareness is for durable preferences and summaries, not authoritative task state.
