# Connectors Management Guide

This guide covers managing connectors through the QwenWork Connector: Apple connectors (Reminders, Contacts, Notes, Mail, Calendar, Maps), Microsoft 365, Browser connector, DingTalk (DWS) connector, Feishu (Lark) connector, and Computer Use.

## Keys

When the user says "open" or Chinese "打开" for a connector, treat it as enable/turn on when the connector supports `enable`. Use `open` only for explicit UI navigation such as opening a settings page.

**QwenWork self switch:** The Connectors UI shows a `QwenWork Connector` switch (Chinese UI: `千问办公连接器`), but that switch only controls whether the built-in `qw` Connector is registered in the MCP Pool. It is not an Agent-manageable connector entity. Do not invent or call `qwenwork.settings.connector.builtin.qoderwork`, `qwenwork.settings.connector.self`, or similar keys.

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork.settings.connector` | query, open | All Agent-manageable connector entities (builtin integrations + Market MCP + custom MCP). Does not include the QwenWork Connector self switch. Supports keyword param. |
| `qwenwork.settings.connector.builtin.apple` | query, open | Apple connectors list |
| `qwenwork.settings.connector.builtin.apple.{id}` | query, enable, disable | Single Apple connector toggle |
| `qwenwork.settings.connector.builtin.ms365` | query, open, connect, disconnect | Microsoft 365 connector status |
| `qwenwork.settings.connector.builtin.ms365.{subId}` | query, enable, disable | Microsoft 365 sub-connector toggle |
| `qwenwork.settings.connector.builtin.browser` | query, open, enable, disable | Browser connector status and toggle |
| `qwenwork.settings.connector.builtin.dws` | query, open, connect, disconnect, enable, disable, install, uninstall | DingTalk connector (install, auth, login/logout, enable/disable) |
| `qwenwork.settings.connector.builtin.lark` | query, open, enable, disable, execute | Feishu (Lark) connector (download/register through enable, soft toggle, logout/reauth via execute) |
| `qwenwork.settings.connector.builtin.computer_use` | query, open, enable, disable | Computer Use connector status. The enable action returns a safety notice; the user must turn it on manually. |

---

## Overview All Connectors

Get a combined status of all connector types.

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector" })
```

Supports keyword filtering:

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector", params: { keyword: "apple" } })
```

**Response structure:**

```json
{
  "success": true,
  "data": {
    "items": [
      { "key": "qwenwork.settings.connector.builtin.apple", "name": "apple", "displayName": "Apple", "type": "builtin", "enabled": true },
      { "key": "qwenwork.settings.connector.builtin.ms365", "name": "ms365", "displayName": "Microsoft 365", "type": "builtin", "enabled": true },
      { "key": "qwenwork.settings.connector.builtin.browser", "name": "browser", "displayName": "Browser", "type": "builtin", "enabled": true },
      { "key": "qwenwork.settings.connector.builtin.dws", "name": "dws", "displayName": "DingTalk", "type": "builtin", "enabled": true, "status": "connected" },
      { "key": "qwenwork.settings.connector.builtin.lark", "name": "lark", "displayName": "Feishu", "type": "builtin", "enabled": true, "status": "connected" },
      { "key": "qwenwork.settings.connector.market.notion", "name": "notion", "displayName": "Notion", "type": "market", "enabled": true },
      { "key": "qwenwork.settings.connector.custom.my-server", "name": "my-server", "displayName": "my-server", "type": "custom", "enabled": true }
    ]
  }
}
```

> **Note:** The connector overview aggregates Agent-manageable builtin, market, and custom connector entities. Each item includes a `key` field for direct navigation and a `type` field to distinguish the source.

---

## Apple Connectors

Apple connectors provide access to native macOS applications. **Only available on macOS.**

### Available Apple Connectors

| Connector ID | Name | Description |
|-------------|------|-------------|
| `apple_reminders` | Reminders | Access Apple Reminders |
| `apple_contacts` | Contacts | Access Apple Contacts |
| `apple_notes` | Notes | Access Apple Notes |
| `apple_mail` | Mail | Access Apple Mail |
| `apple_calendar` | Calendar | Access Apple Calendar |
| `apple_maps` | Maps | Access Apple Maps |

### List Apple Connectors

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.apple" })
```

Returns the macOS check and a list of all Apple connectors with their status.

### Query Single Apple Connector

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.apple.apple_reminders" })
```

Returns detailed status for a specific Apple connector.

### Enable / Disable Apple Connector

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.builtin.apple.apple_reminders",
  action: "enable"
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.builtin.apple.apple_reminders",
  action: "disable"
})
```

### Workflow: Enable Multiple Apple Connectors

1. **Check** which connectors are available:
   ```
   query({ key: "qwenwork.settings.connector.builtin.apple" })
   ```

2. **Verify** macOS platform (`isMacOS: true`).

3. **Enable** desired connectors one by one:
   ```
   action({ key: "qwenwork.settings.connector.builtin.apple.apple_reminders", action: "enable" })
   action({ key: "qwenwork.settings.connector.builtin.apple.apple_calendar", action: "enable" })
   ```

4. **Verify** status:
   ```
   query({ key: "qwenwork.settings.connector.builtin.apple" })
   ```

> **Note:** Some Apple connectors may require macOS system permissions (e.g., Full Disk Access, Contacts access). If enabling fails, check permissions via `query({ key: "qwenwork.settings.permissions" })`.

---

## Microsoft 365 Connector

The Microsoft 365 connector provides access to Outlook, OneDrive, and other Microsoft services.

### Query Status

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.ms365" })
```

### Open Settings (Navigation Only)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.ms365", action: "open" })
```

> **Note:** Use this only when the user asks to navigate to the Microsoft 365 settings UI. Microsoft 365 account connection should use `connect`; sub-connector toggles should use `enable` / `disable`.

---

## Browser Connector

The browser connector provides web browsing capabilities (navigate, screenshot, click, type).

### Query Status

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.browser" })
```

**Response:**

```json
{
  "success": true,
  "data": {
    "connected": true,
    "status": "connected",
    "tools": ["navigate", "screenshot", "click", "type"]
  }
}
```

### Open Settings (Navigation Only)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.browser", action: "open" })
```

> **Note:** Use this only when the user asks to navigate to the Browser connector settings UI. If the user says to open/turn on the Browser connector, use `enable`.

---

## Computer Use Connector

Computer Use provides desktop automation tools. It has a stricter safety boundary than other connectors: Agent may inspect status, call enable to return the safety notice, disable the connector, or navigate to settings, but must not enable desktop control. The user must turn it on manually in QwenWork.

### Query Status

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.computer_use" })
```

The response includes `enabled`, `registered`, `runtimeReady`, `installed`, platform fields, and `agentControl.canEnable: false`.

### Enable Request (Safety Notice Only)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.computer_use", action: "enable" })
```

This returns a safety notice. It does not install, enable, or register desktop control tools.

### Disable

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.computer_use", action: "disable" })
```

### Open Settings (Navigation Only)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.computer_use", action: "open" })
```

Use `open` only to navigate to the Connectors page so the user can enable Computer Use manually.

---

## DingTalk (DWS) Connector

The DingTalk connector provides access to DingTalk workspace features (calendar, contacts, approval, attendance, todo, group chat, bot messaging, documents, drive, etc.).

### Query Status

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.dws" })
```

**Response:**

```json
{
  "success": true,
  "data": {
    "name": "dws",
    "displayName": "DingTalk",
    "platformSupported": true,
    "installed": true,
    "skillInstalled": true,
    "enabled": true,
    "authenticated": true,
    "userName": "John",
    "orgName": "Acme Corp",
    "version": "1.2.0"
  }
}
```

### Connect (Login)

Initiate DingTalk OAuth login. Opens the system browser for authentication.

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.dws", action: "connect" })
```

If already authenticated, returns current user info without re-login.

### Disconnect (Logout)

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.dws", action: "disconnect" })
```

### Enable / Disable (Install / Uninstall)

Enable (or install) installs the DWS binary + skill and registers the `dws_bash` tool. Disable (or uninstall) is a soft toggle (preserves installed files).

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.dws", action: "install" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.dws", action: "enable" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.dws", action: "uninstall" })
```

```
mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.dws", action: "disable" })
```

> **Note:** `install` is a semantic alias for `enable`; `uninstall` is a semantic alias for `disable`. Both forms are accepted.

### Workflow: Login DingTalk

1. **Check** current status:
   ```
   query({ key: "qwenwork.settings.connector.builtin.dws" })
   ```

2. If `installed: false` or `enabled: false`, **enable** first:
   ```
   action({ key: "qwenwork.settings.connector.builtin.dws", action: "enable" })
   ```

3. If `authenticated: false`, **connect**:
   ```
   action({ key: "qwenwork.settings.connector.builtin.dws", action: "connect" })
   ```

4. **Poll** status until `authenticated: true`:
   ```
   query({ key: "qwenwork.settings.connector.builtin.dws" })
   ```

> **Note:** The DingTalk connector is also the prerequisite for the "dws" skill. If the user asks to use DingTalk features (calendar, contacts, etc.) but is not logged in, guide them through this login workflow first.

---

## Feishu (Lark) Connector

Use `qwenwork.settings.connector.builtin.lark` for Feishu (Lark) connector status and setup. It provides Feishu (Lark) workspace access through the local `lark-cli` command bridge and installed `lark-*` skills.

| User intent | Call | Notes |
|-------------|------|-------|
| Check status | `mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.builtin.lark" })` | Inspect `platformSupported`, `installed`, `skillInstalled`, `enabled`, `configured`, `authenticated`, `userName`, `tenantName`, `version`, `setupStatus`, and `setupError`. |
| Turn on / prepare Feishu (Lark) | `mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.lark", action: "enable" })` | Use when `installed`, `enabled`, or `configured` is false. It downloads/registers local resources, starts required configuration/auth, then poll query. |
| Turn off Feishu (Lark) | `mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.lark", action: "disable" })` | Soft toggle; preserves local resources. |
| Logout | `mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.lark", action: "execute", params: { action: "logout" } })` | Logs out without deleting local resources. |
| Reauth | `mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.lark", action: "execute", params: { action: "reauth" } })` | Use when `authenticated` is false; poll query until authenticated. |
| Open settings | `mcp__qw-builtin__qw_action({ key: "qwenwork.settings.connector.builtin.lark", action: "open" })` | Navigation only, or inspect settings after an enable/configuration error; use `enable` when the user asks to turn on Feishu (Lark). |

If `platformSupported` is false, explain that Feishu (Lark) is unavailable on the current platform. Feishu (Lark) does not expose top-level `connect`, `disconnect`, `install`, or `uninstall` actions.

---

## Notes

- Apple connectors are **macOS only**. On other platforms, the query returns `isMacOS: false` with an empty connector list.
- `open` means UI navigation only. For connectors that support toggles, use `enable` / `disable` when the user asks to open/turn on or close/turn off a connector.
- Computer Use is the exception: `enable` only returns a safety notice; only the user may turn on Computer Use desktop control.
- Apple connector IDs use the `apple_` prefix (e.g., `apple_reminders`, not `reminders`).
- If an Apple connector fails to enable, check macOS system permissions first -- many connectors require specific privacy permissions to access native app data.
- DingTalk connector requires `enable` (install) before `connect` (login). Use `query` to check the full state including installation, authentication, and version.
