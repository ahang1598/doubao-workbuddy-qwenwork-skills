# IM Channels Management Guide

This guide covers managing IM (Instant Messaging) channels through the QwenWork Connector: listing channels, enabling/disabling, restarting, QR code authentication flows, and pairing management.

## Keys

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork.channels` | query, open | All channels overview |
| `qwenwork.channels.{channelId}` | query, enable, disable, execute | Single channel operations |
| `qwenwork.channels.{channelId}.pairings` | query, execute, remove | Channel pairing management |

## Channel Configuration CRUD Is UI-only

Channel configuration CRUD is intentionally UI-only. The Connector can query masked configuration, enable or disable an already configured channel, restart a channel, run QR authentication flows, and manage pairings. It must not proxy channel config `update`, `remove`, `configure`, `edit`, or `delete` actions.

Use `mcp__qw-builtin__qw_action({ key: "qwenwork.channels", action: "open" })` when the user needs to edit credentials, secrets, access policy, progress-update settings, or delete a channel configuration. The user must review and confirm those changes in the Channels UI.

## Visibility And Gate Policy

Channel visibility follows the shared `im-platform-visibility.ts` policy used by main process, renderer, settings, sidebar, and badge/tray counting. Remote-gated platforms are fail-closed: when a remote gate is absent or false, the platform is hidden from `qwenwork.channels` results instead of appearing as a disabled placeholder.

Microsoft Teams (`msteams`) is remote-gated. When its gate is closed, querying the channel detail returns "Channel not found", and write-like operations such as enable, disable, restart, or QR execution return `MSTEAMS_FEATURE_DISABLED`. Do not suggest hidden Teams channel operations unless the channel appears in `qwenwork.channels`.

## Supported Channels

| Channel ID | Label | QR Auth | Notes |
|------------|-------|---------|-------|
| `dingtalk` | DingTalk | Yes | URL-based QR, uses `deviceCode` for polling; supports pairing mode |
| `feishu` | Feishu | Yes | URL-based QR, uses `deviceCode` for polling; supports pairing mode |
| `lark` | Lark | Yes | URL-based QR, uses `deviceCode` for polling; supports pairing mode |
| `weixin` | WeChat | Yes | Base64 image QR, uses `qrcode` for polling |
| `wecom-bot` | WeCom Bot | Yes | URL-based QR, uses `scode` for polling |
| `xiaoq` | XiaoQ | No | Simple enable/disable; does not support pairing codes |

---

## List All Channels

```
mcp__qw-builtin__qw_query({ key: "qwenwork.channels" })
```

**Response structure:**

```json
{
  "success": true,
  "data": {
    "summary": {
      "total": 5,
      "connected": 2,
      "stopped": 1,
      "failed": 0,
      "unconfigured": 2
    },
    "channels": [
      {
        "id": "feishu",
        "label": "Feishu (Lark)",
        "status": "connected",
        "error": null,
        "enabled": true,
        "configured": true,
        "accessPolicy": "pairing",
        "supportsQR": true,
        "capabilities": { ... }
      }
    ]
  }
}
```

**Status values:** `connected`, `stopped`, `failed`, `unconfigured`.

**Access policy values:** `open` (anyone can message), `pairing` (requires pairing code).

---

## Query Channel Detail

```
mcp__qw-builtin__qw_query({ key: "qwenwork.channels.feishu" })
```

Returns detailed info including masked configuration (secrets are hidden), capabilities, access policy, and progress update settings.

---

## Enable / Disable a Channel

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu",
  action: "enable"
})
```

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu",
  action: "disable"
})
```

- **Enable**: Saves config and starts the channel. If startup fails, automatically rolls back `enabled` to `false` and returns the error.
- **Disable**: Saves config and stops the channel.
- Channel must be **configured** before it can be enabled. Unconfigured channels return an error.

---

## Restart a Channel

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu",
  action: "execute",
  params: { action: "restart" }
})
```

Stops and restarts the channel. Useful for recovering from transient errors.

---

## QR Code Authentication

QR authentication is a multi-step flow used to connect channels that require scanning a QR code. Supported channels: `feishu`, `weixin`, `wecom-bot`.

### Step 1: Start QR Session

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.<channelId>",
  action: "execute",
  params: { action: "startQR" }
})
```

**Response varies by channel:**

#### Feishu

```json
{
  "success": true,
  "data": {
    "channelId": "feishu",
    "qrType": "url",
    "verificationUrl": "https://...",
    "deviceCode": "abc123",
    "pollInterval": 5,
    "expireIn": 600,
    "hint": "Render this URL as a QR code or open it in browser. Then use pollQR with deviceCode to check status."
  }
}
```

Display the `verificationUrl` as a QR code or clickable link. Save `deviceCode` for polling.

#### WeChat

```json
{
  "success": true,
  "data": {
    "channelId": "weixin",
    "qrType": "base64Image",
    "qrcode": "qr-identifier",
    "qrcodeImg": "data:image/png;base64,...",
    "hint": "Display the base64 image to user. Then use pollQR with qrcode to check status."
  }
}
```

Display the `qrcodeImg` base64 image. Save `qrcode` for polling.

#### WeCom Bot

```json
{
  "success": true,
  "data": {
    "channelId": "wecom-bot",
    "qrType": "url",
    "authUrl": "https://...",
    "scode": "xyz789",
    "hint": "Render this URL as a QR code or open it in browser. Then use pollQR with scode to check status."
  }
}
```

Display the `authUrl` as a QR code or link. Save `scode` for polling.

### Step 2: Poll QR Status

Poll repeatedly until the user scans and confirms.

#### Feishu polling

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu",
  action: "execute",
  params: { action: "pollQR", deviceCode: "abc123" }
})
```

#### WeChat polling

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.weixin",
  action: "execute",
  params: { action: "pollQR", qrcode: "qr-identifier" }
})
```

#### WeCom Bot polling

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.wecom-bot",
  action: "execute",
  params: { action: "pollQR", scode: "xyz789" }
})
```

### Poll Response Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `pending` | Waiting for user to scan | Continue polling |
| `scanned` | QR scanned, awaiting confirmation (WeChat only) | Continue polling |
| `slow_down` | Polling too fast (Feishu only) | Increase poll interval |
| `confirmed` / `success` | Authentication complete | Stop polling, channel is configured |
| `expired` | QR code expired | Start a new QR session |
| `denied` | User denied authorization (Feishu only) | Inform user, optionally retry |

On successful confirmation, the Connector automatically:
- Saves the credentials to channel config
- Sets `enabled: true`
- Starts the channel

### QR Auth Workflow Summary

```
1. startQR  ->  Get QR URL/image + polling token
2. Show QR to user
3. pollQR   ->  Check status (loop with appropriate interval)
4. On "confirmed/success" -> Done! Channel is live.
   On "expired" -> Restart from step 1.
```

---

## Pairing Management

Pairing controls which IM users/groups can interact with this QwenWork instance. It only applies to channels that support pairing mode: `dingtalk`, `feishu`, and `lark`.

`weixin`, `wecom-bot`, and `xiaoq` always use `accessPolicy: "open"` in the Connector control plane and do not support pairing codes.

### List Pairings

```
mcp__qw-builtin__qw_query({ key: "qwenwork.channels.feishu.pairings" })
```

**Response:**

```json
{
  "success": true,
  "data": {
    "channelId": "feishu",
    "accessPolicy": "pairing",
    "pairings": [
      {
        "id": "pairing-uuid",
        "channelId": "feishu",
        "robotId": "bot-id",
        "bindingKey": "hash...",
        "conversationType": "direct",
        "subjectName": "John",
        "pairedAt": "2025-01-15T10:00:00.000Z"
      }
    ],
    "pendingRequests": [
      {
        "channelId": "feishu",
        "conversationId": "conv-id",
        "conversationType": "group",
        "conversationName": "Team Chat",
        "senderName": "Alice",
        "senderId": "user-id",
        "senderStaffId": "staff-id",
        "messageContent": "Hello",
        "timestamp": 1706600000000
      }
    ],
    "summary": {
      "totalPairings": 3,
      "totalPending": 1
    }
  }
}
```

### Generate Pairing Code

Generate a temporary code that an IM user can send as a message to pair with this instance.

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu.pairings",
  action: "execute",
  params: { action: "generateCode" }
})
```

**Response:**

```json
{
  "success": true,
  "data": {
    "code": "123456",
    "expiresAt": 1706600600000,
    "expiresIn": 600,
    "formattedCode": "千问办公配对码：123456",
    "hint": "Share this code with the IM user. They can send it as a message to pair with this instance. Code expires in 10 minutes."
  }
}
```

Only works when the channel's `accessPolicy` is `"pairing"`.

### Approve a Pending Request

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu.pairings",
  action: "execute",
  params: {
    action: "approve",
    senderId: "user-id",
    conversationId: "conv-id",
    senderStaffId: "staff-id",
    conversationType: "direct",
    conversationName: "John"
  }
})
```

**Required params:**

| Param | Type | Description |
|-------|------|-------------|
| `senderId` | string | The sender's user ID |
| `conversationId` | string | The conversation ID |

**Optional params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `senderStaffId` | string | - | Staff ID (for enterprise channels) |
| `conversationType` | string | "direct" | `"direct"` or `"group"` |
| `conversationName` | string | - | Display name for the pairing |

After approval, any cached message from the sender is automatically delivered.

### Ignore a Pending Request

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu.pairings",
  action: "execute",
  params: {
    action: "ignore",
    senderId: "user-id",
    conversationId: "conv-id",
    senderStaffId: "staff-id",
    conversationType: "direct"
  }
})
```

Removes the pending request without creating a pairing.

### Remove a Pairing

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.channels.feishu.pairings",
  action: "remove",
  params: { pairingId: "pairing-uuid" }
})
```

---

## Workflow: Set Up a New Feishu Channel via QR

1. **Start QR**:
   ```
   action({ key: "qwenwork.channels.feishu", action: "execute", params: { action: "startQR" } })
   ```

2. **Display** the `verificationUrl` to the user as a QR code or link.

3. **Poll** for confirmation (every 5 seconds):
   ```
   action({ key: "qwenwork.channels.feishu", action: "execute", params: { action: "pollQR", deviceCode: "..." } })
   ```

4. On `status: "confirmed"` -- channel is configured and running.

5. **Verify** channel status:
   ```
   query({ key: "qwenwork.channels.feishu" })
   ```

6. **Generate pairing code** for users to connect:
   ```
   action({ key: "qwenwork.channels.feishu.pairings", action: "execute", params: { action: "generateCode" } })
   ```

7. Share the pairing code with the desired IM users.

## Workflow: Manage Pending Pairing Requests

1. **Check** for pending requests:
   ```
   query({ key: "qwenwork.channels.feishu.pairings" })
   ```

2. **Review** `pendingRequests` array -- each contains sender info and message content.

3. **Approve** legitimate requests:
   ```
   action({ key: "qwenwork.channels.feishu.pairings", action: "execute", params: { action: "approve", senderId: "...", conversationId: "..." } })
   ```

4. **Ignore** unwanted requests:
   ```
   action({ key: "qwenwork.channels.feishu.pairings", action: "execute", params: { action: "ignore", senderId: "...", conversationId: "..." } })
   ```

---

## Notes

- Channel configuration (credentials, etc.) must be set up before enabling. Use the QwenWork settings UI or QR authentication for initial setup.
- Configuration secrets are always masked in query responses (shown as bullet characters).
- QR codes have a limited lifetime (typically 10 minutes). If expired, start a new session.
- Pairing codes also expire after 10 minutes.
- The `execute` action on channels is multiplexed: use `params.action` to specify the sub-operation (`restart`, `startQR`, `pollQR`).
- The `execute` action on pairings is also multiplexed: use `params.action` for `generateCode`, `approve`, or `ignore`.
