# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -r requirements.txt
```

## Running Commands

All commands go through the unified CLI entry point:

```bash
python3 cli.py <command> [options]
```

Common commands:
```bash
python3 cli.py get_ak                                        # browser-based AK acquisition
python3 cli.py configure <AK>                                # set AK
python3 cli.py configure --status                            # check AK status
python3 cli.py configure --clear                             # remove AK
```

All commands output JSON: `{"success": bool, "markdown": str, "data": {...}}`

## Architecture

### Two Credential Types

**AK (Access Key)** — used for signing all outbound API requests via HMAC-SHA256 (`scripts/_auth.py`). Stored at `<workspace>/.1688-AK/.ak_store.json`. Required before any API call.

**OAuth Token** — user-level 1688 API authorization via OAuth 2.1 + PKCE. Stored in macOS Keychain (preferred) or `<workspace>/.1688-oauth/.token_store.json` as fallback. Managed by `scripts/token_manager.py`.

### Core Modules

| Module | Purpose |
|---|---|
| `cli.py` | Entry point; routes to built-in OAuth handlers or auto-discovered capabilities |
| `scripts/_const.py` | All constants: endpoints, file paths, env var names |
| `scripts/_auth.py` | AK parsing + HMAC-SHA256 request signing |
| `scripts/_http.py` | `api_post()`: signs requests, retries on network errors (3×, exponential backoff), maps errors to exception types |
| `scripts/_errors.py` | Exception hierarchy: `SkillError` → `AuthError`, `ParamError`, `RateLimitError`, `ServiceError`, `GatewayAuthError` |
| `scripts/_output.py` | `make_output()` / `print_output()` / `print_error()` for standardized JSON responses |
| `scripts/secure_store.py` | Token storage: Keychain first, file fallback; probes availability on first use |
| `scripts/encrypted_store.py` | File-based token storage (chmod 600, atomic write via temp file) |
| `scripts/token_manager.py` | Token lifecycle: load, check expiry, silent refresh, revoke, clear |
| `scripts/scope_manager.py` | Scope list with 24h file cache |
| `scripts/authorize.py` | OAuth flow orchestration: spawns local callback server, opens browser, waits for redirect |
| `scripts/callback_server.py` | Local HTTP server at `localhost:10000+` that handles `/callback`, `/api/exchange`, `/api/save-ak` |
| `scripts/pkce.py` | PKCE code_verifier / code_challenge generation (RFC 7636, S256 only) |
| `scripts/_tracker.py` | Usage telemetry: `report_skill_usage()` called after every command, silently ignores failures |

### Capability Plugin System

Capabilities are auto-discovered: any `scripts/capabilities/<name>/cmd.py` with `COMMAND_NAME` and `main()` is registered as a CLI command. The `configure` capability follows this pattern.

To add a new capability:
1. Create `scripts/capabilities/<name>/cmd.py` — define `COMMAND_NAME`, `COMMAND_DESC`, and `main()`
2. Create `scripts/capabilities/<name>/service.py` — business logic calling `api_post()`
3. Add `__init__.py` in the directory

### OAuth Flow

`authorize.py` runs as a **subprocess** (not imported): `cli.py` spawns it and captures stdout. The flow: generate PKCE pair → start `CallbackServer` (ports 10000–10009) → open browser → wait for callback → exchange code for token → store via `secure_store`.

### Workspace Path Resolution

`_const.py` resolves the workspace directory at import time:
1. `$AGENT_WORK_ROOT/workspace`
2. Walk up from cwd looking for a directory named `workspace`
3. Walk up looking for `.skills` sibling directory
4. Fallback: cwd

Token and AK data files live under this workspace path.

### API Gateway

`_http.api_post()` targets `https://skills-gateway.1688.com`. The gateway returns `GatewayAuthError` for token-related errors (`1688_token_expired`, `1688_invalid_token`, etc.), which signals the agent to re-authorize.

### Telemetry

`.env` in project root configures `SKILL_NAME`, `SKILL_VERSION`, `SKILL_CHANNEL` for usage reporting. System env vars take precedence over `.env`.
