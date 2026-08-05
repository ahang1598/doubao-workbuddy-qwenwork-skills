# MCP Server Management Guide

This guide covers managing MCP (Model Context Protocol) servers through the QwenWork Connector. MCP servers are managed under two sub-namespaces of `connector`:

- **Connector Market list** (`connector.market`): The market view can include builtin product connectors and Market MCP servers. Always use each returned item's `key` for follow-up operations.
- **Market MCP detail** (`connector.market.{name}`): Single Market MCP servers (e.g. Notion, Linear, qibook). Do not use this pattern for builtin product connectors such as Microsoft 365, DingTalk, Feishu, Browser, Apple, or Computer Use.
- **Custom MCP** (`connector.custom.*`): User-added MCP servers (stdio or SSE/HTTP).

## Keys

When the user says "open" or Chinese "打开" for an MCP server, treat it as enabling/installing the server by default. Use `open` only for explicit UI navigation such as opening the Connector settings page or a server detail page.

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork.settings.connector.market` | query, open | Connector Market list. Items can be builtin product connectors or Market MCP servers. Supports keyword param. |
| `qwenwork.settings.connector.market.{name}` | query, open, enable, disable, install, uninstall, execute | Single Market MCP server only (install/uninstall = enable/disable). Builtin product connectors use the returned `key`, usually under `connector.builtin.*`. |
| `qwenwork.settings.connector.custom` | query, open, add | Custom (user-added) MCP servers list. Supports keyword param and add action. |
| `qwenwork.settings.connector.custom.{name}` | query, open, update, enable, disable, remove, execute | Single custom MCP server CRUD |

---

## Connector Market And Market MCP Servers

`qwenwork.settings.connector.market` returns the Connector Market view. The list may include:

- `type: "builtin"` items: product/native connectors such as Microsoft 365, DingTalk, Feishu, Browser, Apple, or Computer Use. Use the returned `key` for follow-up operations.
- `type: "market"` items: Market MCP servers such as Notion, Linear, or qibook. These can be installed (enabled) or uninstalled (disabled) through `qwenwork.settings.connector.market.{name}`.

Do not construct a follow-up key from `name` unless the item is `type: "market"`. Prefer the exact `key` returned by the list.

### List Connector Market Items

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.market" })
```

Supports keyword filtering:

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.market", params: { keyword: "notion" } })
```

**Response structure:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "ms365",
        "displayName": "Microsoft 365",
        "type": "builtin",
        "enabled": true,
        "status": "connected",
        "key": "qwenwork.settings.connector.builtin.ms365"
      },
      {
        "name": "notion",
        "displayName": "Notion",
        "type": "market",
        "enabled": true,
        "status": "connected",
        "key": "qwenwork.settings.connector.market.notion"
      }
    ],
    "totalCount": 10,
    "enabledCount": 3
  }
}
```

### Query Single Market Server

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.market.notion" })
```

**Response includes:**

- `name`, `displayName`, `enabled`, `status`
- `tools[]`: Array of `{ name, description }` for all tools provided by this server
- `error`: Error message if connection failed
- `authUrl`: OAuth URL if the server requires authentication
- `key`: The full key path for this server

### Install / Uninstall (Enable / Disable)

`install` and `uninstall` are semantic aliases for `enable` and `disable`, designed for Market MCP servers:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.market.notion",
  action: "install"
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.market.notion",
  action: "uninstall"
})
```

You can also use `enable` / `disable` directly — they are equivalent.

### Execute (OAuth Authentication)

Some market servers require OAuth. Use execute with `operation: "auth"` to start the OAuth flow:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.market.notion",
  action: "execute",
  params: { operation: "auth" }
})
```

To reset OAuth credentials:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.market.notion",
  action: "execute",
  params: { operation: "reset" }
})
```

---

## Custom MCP Servers

Custom MCP servers are user-added servers configured via stdio (command + args) or SSE/HTTP (URL).

### List Custom MCP Servers

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.custom" })
```

Supports keyword filtering:

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.custom", params: { keyword: "filesystem" } })
```

### Add a New Custom Server

#### Stdio-based server (command + args)

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom",
  action: "add",
  params: {
    name: "my-mcp-server",
    config: {
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
      env: {
        SOME_VAR: "value"
      }
    }
  }
})
```

#### SSE/Streamable HTTP server (URL)

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom",
  action: "add",
  params: {
    name: "remote-server",
    config: {
      url: "https://example.com/mcp/sse"
    }
  }
})
```

**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `name` | string | Unique server identifier |
| `config` | object | Server configuration (see below) |

**Config fields (stdio):**

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | Executable command (e.g. `npx`, `node`, `python`) |
| `args` | string[] | Command arguments |
| `env` | object | Optional environment variables |

**Config fields (SSE/HTTP):**

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Server endpoint URL |

After adding, the response includes the server's key:

```json
{
  "success": true,
  "data": { "name": "my-mcp-server", "key": "qwenwork.settings.connector.custom.my-mcp-server" }
}
```

The MCP pool automatically reloads and attempts to connect. Check the status with a follow-up query.

### Query Server Detail

```
mcp__qw-builtin__qw_query({ key: "qwenwork.settings.connector.custom.my-server" })
```

**Response includes:**

- `name`, `enabled`, `status`
- `tools[]`: Array of `{ name, description }` for all tools provided by this server
- `error`: Error message if connection failed
- `config`: Safe configuration (command, args, url, env key names -- no secrets)

### Enable / Disable a Server

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom.my-server",
  action: "enable"
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom.my-server",
  action: "disable"
})
```

Toggling triggers an automatic MCP pool reload in the background.

### Update Server Configuration

Replace the server's config while preserving internal fields (`enabled`, `_builtinId`, `_oauth`):

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom.my-server",
  action: "update",
  params: {
    config: {
      command: "npx",
      args: ["-y", "updated-server@latest"]
    }
  }
})
```

The update merges the new config with preserved internal fields, then triggers a pool reload.

### Remove a Server

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom.my-server",
  action: "remove"
})
```

Permanently removes the server from configuration and triggers a pool reload.

### Execute (OAuth Authentication)

Custom servers that support OAuth can use execute with `operation: "auth"`:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.settings.connector.custom.my-server",
  action: "execute",
  params: { operation: "auth" }
})
```

---

## Workflow: Add and Verify a New Custom Server

1. **Add** the server:
   ```
   action({ key: "qwenwork.settings.connector.custom", action: "add", params: {
     name: "filesystem",
     config: { command: "npx", args: ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/docs"] }
   }})
   ```

2. **Wait** a moment for the connection to establish (the pool reloads asynchronously).

3. **Verify** the connection and available tools:
   ```
   query({ key: "qwenwork.settings.connector.custom.filesystem" })
   ```
   Check that `status` is `"connected"` and `tools` lists the expected tools.

4. If `status` is `"error"`, check the `error` field for details. Common issues:
   - Command not found: Verify the `command` path
   - Connection refused: For SSE servers, verify the URL is accessible
   - Missing environment variables: Add required env vars to the config

## Workflow: Troubleshoot a Failing Server

1. **Query** the server to get error details:
   ```
   query({ key: "qwenwork.settings.connector.custom.my-server" })
   ```

2. **If config needs fixing**, update it:
   ```
   action({ key: "qwenwork.settings.connector.custom.my-server", action: "update", params: { config: { ... } } })
   ```

3. **If server needs restart**, disable then re-enable:
   ```
   action({ key: "qwenwork.settings.connector.custom.my-server", action: "disable" })
   action({ key: "qwenwork.settings.connector.custom.my-server", action: "enable" })
   ```

4. **Verify** status after fix:
   ```
   query({ key: "qwenwork.settings.connector.custom.my-server" })
   ```

## Workflow: Install a Market MCP Server

1. **Browse** available Connector Market items:
   ```
   query({ key: "qwenwork.settings.connector.market" })
   ```

2. **Install** the desired Market MCP server using the returned `key`:
   ```
   action({ key: "qwenwork.settings.connector.market.notion", action: "install" })
   ```

3. **If OAuth is required**, start the auth flow:
   ```
   action({ key: "qwenwork.settings.connector.market.notion", action: "execute", params: { operation: "auth" } })
   ```

4. **Verify** connection:
   ```
   query({ key: "qwenwork.settings.connector.market.notion" })
   ```

---

## Notes

- Custom server names must be unique.
- Market MCP servers cannot be removed or reconfigured -- only installed (enabled) or uninstalled (disabled).
- The Connector Market list can include builtin product connectors. Those items are not Market MCP servers; use their returned `key` under `connector.builtin.*`.
- The `env` field in query responses only shows key names (not values) to avoid leaking secrets.
- All add/update/remove/toggle operations trigger an asynchronous pool reload. The server may take a few seconds to connect after changes.
- **Status values:** `connected`, `connecting`, `disconnected`, `error`, `pending`, `disabled`, `unknown`.
