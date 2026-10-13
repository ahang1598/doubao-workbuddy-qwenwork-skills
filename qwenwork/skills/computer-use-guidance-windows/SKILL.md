---
name: computer-use-guidance-windows
version: 0.9.0
description: "Operation guidance for automating the Windows desktop via Computer Use: open apps, read on-screen state through the UIA accessibility tree, click / type / press shortcut keys / scroll / drag / invoke semantic UIA actions, and execute platform-specific recipes across apps, windows, files, system settings, terminal, office suites, and developer tools."
description_zh: "Windows 平台 Computer Use 桌面自动化操作指南：通过读屏（UIA 无障碍树）配合点击 / 文本输入 / 快捷键 / 滚动 / 拖拽 / 语义动作等 UI 操作完成本机应用自动化，覆盖应用、窗口、文件、系统设置、终端、办公、开发工具等常见场景的操作范式与最佳实践。"
---

# Computer Use Guidance (Windows)

This skill provides Windows-specific operation guidance for desktop automation via the native C#/Win32 Computer Use MCP server. Read the **Lazy-load Bootstrap** and **Tool Reference** sections below before taking any action — the Windows interaction paradigm (UIA-tree-first, focus-stealing, SendInput-based) differs from macOS and any generic desktop automation guide.

---

## Lazy-load Bootstrap (MCP 懒加载模式)

If your runtime exposes MCP tools through the lazy-load meta tools (`qw_mcp_list` / `qw_mcp_get` / `qw_mcp_call`) instead of listing every tool directly, load the full Computer Use tool contract before executing any automation step:

1. Call `qw_mcp_list({keyword: "computer-use"})` to enumerate all Computer Use tools exposed by this connector.
2. For every returned tool, call `qw_mcp_get({toolName})` to cache its input schema (argument names, required fields, enums).
3. Only after every Computer Use tool schema is loaded, start the task — do not guess argument shapes from this skill document alone.

Why this matters: this skill describes *when* to use which tool and *why* — it deliberately does not enumerate full input schemas. The authoritative schema always lives on the MCP server, reachable via `qw_mcp_get`. In direct (non-lazy) mode, schemas are already visible in the tool list and this bootstrap can be skipped.

---

## Tool Reference (paradigm, not schema)

On Windows, Computer Use is powered by a native C# MCP server built on UI Automation (UIA) and Win32 SendInput. This section describes how to combine those tools effectively — not the input schema of each tool. For argument-level details (required fields, enums, types), rely on the schema the runtime provides (lazy-load mode: `qw_mcp_get`; direct mode: the tool list).

The Windows toolset is organized around a small, fixed verb set:

- **Discovery / entry:** `list_installed_apps`, `get_window_state` — see "Opening an app" below.
- **App launching:** `launch_app` — launch by AUMID via Windows Shell.
- **Pointer:** `click`, `drag`, `scroll` — see "element_index paradigm" for addressing rules.
- **Keyboard:** `type_text`, `press_key` — see "Text entry" and "Keyboard shortcuts".

Everything downstream assumes you already know each tool's argument contract (either from the lazy-load bootstrap or from a direct tool list).

### Interaction priority: type_text → click → press_key

When more than one tool can reach the same outcome, pick the shortest, most deterministic path in this order. Treat this as the default; deviate only with a concrete reason.

1. **`type_text` first for any textual input.** If the goal is "put characters into a field" — search box, URL bar, chat input, calculator expression, terminal command, form field, code editor — call `type_text`. One call replaces N clicks or N `press_key` calls and is layout-independent. See "Text entry" below for details.
2. **`click` next for any single-target activation.** If the action is "press a button / tap an icon / activate a menu item / toggle a checkbox / pick a row / focus a field", a single `click({element_index})` is almost always better than emulating the same thing through a keyboard shortcut. Do not reach for `press_key` just because the human docs list a shortcut — if the target is already in the UIA tree, click it.
3. **`press_key` only when the intent is genuinely keyboard-only.** Reserve `press_key` for:
   - Shortcuts with no menu/UI equivalent (`Ctrl+Shift+Escape` Task Manager, `Win+R` Run dialog, `Win+D` show desktop).
   - Modal dismissal (`Escape`) or keyboard navigation (`Tab`, arrow keys) inside an already-focused UI.
   - Composite shortcuts that collapse a multi-step menu path into one keystroke.

   For semantic UIA actions (expand a combo box, invoke a button, toggle a checkbox), use `click({element_index})` which targets the element center — this handles most expand/toggle/invoke scenarios.

**Anti-patterns to avoid:**
- `press_key` loops that imitate what a single `type_text` would do (e.g. `press_key "1"` → `press_key "2"` → `press_key "3"` instead of `type_text({text: "123"})`).
- Tabbing through fields (`press_key "Tab"` × N) to reach a target when a single `click({element_index})` already focuses it.
- Sending `Ctrl+N` / `Ctrl+O` / `Ctrl+,` when the matching menu item is visible and clickable.

### Session management (fully automatic)

The Windows server manages the session **internally** — the agent does NOT need to call any session lifecycle tools.

- **Auto-activate:** The first tool call automatically activates the session and shows the on-screen stop orb.
- **Auto-deactivate:** After 30 seconds of no tool calls (idle timeout), the session automatically deactivates. After timeout, the next tool call will auto-reactivate.
- **User stop (hard gate):** The user can click the stop orb at any time to immediately end the session. After a user stop, all subsequent tool calls return a `user_stopped` error. When the user later sends a new message, the host automatically restores the session — the agent does NOT need to do anything special; just call the business tools again.

What this means for the agent: just call the business tools directly. No setup or teardown needed. If any tool returns an error starting with `user_stopped:`, stop immediately, tell the user you've stopped, wait for their next instruction.

### Mandatory first step for every new user instruction

Every time the user gives a new task or instruction involving Computer Use, **always** call `get_window_state()` first — before any action — to observe the current screen: what app is in the foreground, what UI elements are visible, what the screenshot shows.

You do NOT need to call any session-lifecycle tool. The session is managed entirely by the host: it auto-activates on your first tool call, and auto-restores when the user sends a new message.

Only after seeing the current state should you decide what actions to take. **Never** start clicking, typing, or pressing keys based on assumptions — always look first.

This "observe before act" pattern also applies mid-task: after any action that might change the UI significantly (app switch, navigation, dialog popup), call `get_window_state()` again before the next action.

### Propose a plan and wait for the user's approval before acting (build user trust)

Computer Use takes over the user's real mouse and keyboard, so the user must never be surprised by what happens on their screen. Before you start executing a multi-step automation, you MUST first present a plan AND obtain the user's explicit approval. Do not call any action tool (click / type_text / press_key / scroll / drag / launch_app) until the user has agreed.

**When to announce:** Any task that takes more than one or two tool calls, or any task that opens apps, changes settings, sends messages, edits files, or otherwise affects the user's system. A single trivial action (e.g. one click the user explicitly asked for) does not need a plan.

**What a good plan looks like:** A short, numbered list in plain language describing the high-level steps — which app you will open and what you will do in it — written so a non-technical user can follow along. Keep it to 3-6 concise steps; do not enumerate every individual click or keystroke.

Example, for "帮我在记事本里写一段话并保存":

> 我的计划：
> 1. 打开记事本
> 2. 输入你要的文字
> 3. 用 Ctrl+S 保存到桌面

Then **stop and wait** for the user to approve. Only after the user explicitly agrees (e.g. "好" / "可以" / "开始吧" / "go ahead") should you start calling the action tools. If the user asks for changes, revise the plan and seek approval again. If the user declines, do not act.

After finishing, briefly confirm the outcome (what changed) based on the final screenshot.

**Exception — no approval needed:** A single trivial action the user has already explicitly and unambiguously requested (e.g. they said "click the OK button" — just do it). When in doubt, ask.

**Why this matters:** Requiring approval before acting puts the user in control of their own machine. They see your intent before the screen starts moving, can correct a wrong plan before any damage is done, and never feel that the agent is acting behind their back. This makes the automation feel safe and trustworthy rather than opaque.

### Focus model: all operations activate the target window

Unlike macOS (which has a background-launch silent path), Windows Computer Use **always brings the target window to the foreground** before interacting. This is by design:

- Every tool call that targets a window will activate it (SetForegroundWindow).
- The user's current focus will be interrupted — plan interactions mindfully.
- There is no `request_user_assistance` tool; if a step requires human intervention (UAC prompt, CAPTCHA, biometrics), inform the user via natural language.

---

## Opening an app: always `list_installed_apps` before the first `get_window_state`

The canonical way to enter an app at the start of a task (or when switching to a new app mid-task) is `list_installed_apps` → `launch_app` → `get_window_state`, in that order.

1. **First call `list_installed_apps`.** This is a free, zero-UI query that returns app display names + AUMIDs from the Windows Start Menu (shell:AppsFolder). Use it to pick the right AUMID. The `filter` argument is optional and does case-insensitive substring matching — pass a short keyword in the user's UI language (e.g. `"计算"` on Chinese Windows, `"calc"` on English Windows). Omit `filter` to list everything.
2. **Then call `launch_app({aumid: "<AUMID from step 1>"})`.** This invokes `explorer.exe shell:AppsFolder\<AUMID>` — the same path the Start Menu uses. If the app is already running, Windows activates the existing window; if not, it starts a new instance. The call returns immediately; the window may take 0.5–2s to appear.
3. **Then call `get_window_state()` (no arguments).** Returns the current foreground window's title, process name, screenshot, and numbered UIA element tree. This is the single snapshot you operate against for the rest of the turn.

**Why this order matters:**
- **No name guessing.** AUMIDs are stable identifiers issued by Windows; you never have to translate "记事本" ↔ "Notepad" or worry about UWP host process aliasing.
- **Reliable for UWP / MSIX.** `shell:AppsFolder\<AUMID>` is the official launch path.
- **Cheap discovery.** `list_installed_apps` does not screenshot or walk UIA — safe to call at task start.
- **No coupling between tools.** `launch_app` does not return a handle. State is always observed via `get_window_state` against the foreground window, matching what the user sees on screen.

**Fallback:** if `launch_app` succeeds but the foreground window is not the expected app, call `press_key({key: "alt+tab"})` or click the taskbar icon to bring it forward, then re-call `get_window_state`.

**Skip `list_installed_apps` and `launch_app`** when the target app is already in the foreground from earlier in the task — just call `get_window_state` to get a fresh snapshot.

---

## element_index paradigm

Windows Computer Use is **UIA-tree first**, not pixel first. All `element_index` values resolve against the **current foreground window** (the same window `get_window_state` snapshotted):

1. Bring the target app to the foreground (via `launch_app`, `Alt+Tab`, taskbar click, etc.).
2. Call `get_window_state()` to receive both a screenshot **and** a numbered UIA element tree of that window.
3. Read the tree to find the target element's `element_index`.
4. Call `click` / `scroll` / `drag` with that `element_index`.
5. Fall back to pixel coordinates (`click` with `x`/`y`) only when the target has no UIA element (e.g. custom-drawn canvas, game UI, browser page content).

### element_index support by tool

| Tool | element_index usage |
|------|--------------------|
| `click` | `element_index` — click center of element. Also supports batch via `element_indices="1,2,3"`. |
| `scroll` | `element_index` — scroll at center of element (mutually exclusive with x/y). |
| `drag` | `start_element_index` / `end_element_index` — drag from/to element centers. Start and end can independently use element or coordinates. |
| `type_text` | N/A — focus the target field with `click({element_index})` first, then call `type_text`. |
| `press_key` | N/A — operates on the currently focused element. |

Why prefer `element_index`:
- Stable across window moves and DPI scaling
- Works on elements that are visually obscured but present in UIA
- Screenshot coordinates drift the moment the UI reflows; element indexes don't
- UIA indexes are regenerated each `get_window_state` call — always use the freshest tree

**Important — foreground-window-bound:**
- `element_index` is **only valid against whatever window was in the foreground when `get_window_state` was called.** If a click causes a different window to come forward (dialog popup, app switch, navigation), the previous indexes are invalid.
- After **any** UI change (popup, navigation, content load, foreground switch), re-call `get_window_state` to get fresh indexes.

### Screenshot and coordinate space (trust the pixels)

Screenshots are returned at the screen's **native resolution** with **no scaling, no compression, no aspect-ratio distortion**. The `image_width`/`image_height` always equal `screen_width`/`screen_height` — they describe the same pixel grid.

Coordinates in `click({x, y})`, `scroll({x, y})`, `drag({start_x, ...})` map **1:1 to physical screen pixels**. If you read a button at pixel (450, 320) in the screenshot, click `{x: 450, y: 320}` and you will hit it exactly. There is no DPI conversion, no reference frame remapping, no "image space vs screen space" distinction.

This means: when UIA does not expose a target (browser page content, custom-drawn canvas, game UI), reading the pixel coordinate off the screenshot and clicking it is **just as reliable as `element_index`** — not a "fallback" or "second-best" option. Trust the screenshot pixels.

---

## Text entry: prefer `type_text`

`type_text` is the default for any task that ends up putting characters into the machine. It beats two alternative approaches that look tempting but are worse:

**A. `type_text` beats clicking character buttons one by one.**

Many apps expose on-screen character buttons (calculator number pad, on-screen keyboard, dial pad) and accept real keyboard input at the same time. In that case:
- `click "1" → click "2" → click "3" → click "+"` costs N tool calls and is fragile to layout changes.
- `type_text({text: "123+"})` is one call, layout-independent.

Rule: if the app would accept the same input from a physical keyboard, type it. Only click UI buttons when the button press has a side effect the keyboard does not.

**B. `type_text` has two paths:**
- **Default (clipboard):** Copies text to clipboard and pastes via `Ctrl+V`. Fast for any length, works with virtually all applications.
- **Unicode events (`use_unicode=true`):** Sends `KEYEVENTF_UNICODE` events per character. Use when clipboard paste doesn't work (apps that intercept Ctrl+V, or when clipboard content must be preserved).

**Key behaviors:**
- **IME handling:** Input Method Editor is automatically disabled before typing and restored after completion. No manual IME management needed.
- **Focus requirement:** Ensure the target field is focused (via `click` on it) before calling `type_text`.

**Rule of thumb:** if a human would type it, the agent should `type_text` it — not click-per-character, not per-keystroke via `press_key`.

---

## Keyboard shortcuts via `press_key`

Reach for `press_key` only after ruling out `type_text` (for any text input) and `click` (for any visible UIA target). See the "Interaction priority" section above — `press_key` is the last-resort verb, reserved for genuine keyboard-only intent.

Common patterns on Windows:

| Intent | `press_key` call |
|--------|-----------------|
| Copy | `press_key({key: "ctrl+c"})` |
| Paste | `press_key({key: "ctrl+v"})` |
| Undo | `press_key({key: "ctrl+z"})` |
| New tab | `press_key({key: "ctrl+t"})` |
| Close tab | `press_key({key: "ctrl+w"})` |
| Switch app | `press_key({key: "alt+tab"})` |
| Show desktop | `press_key({key: "win+d"})` |
| Task Manager | `press_key({key: "ctrl+shift+escape"})` |
| Run dialog | `press_key({key: "win+r"})` |

Notes:
- `win` maps to the Windows key. `ctrl`, `alt`, `shift` are the standard modifiers.
- Keys joined with `+`. Special keys: `enter`, `escape`, `tab`, `space`, `backspace`, `delete`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`, `f1`–`f12`.
- For semantic UIA actions (expand, toggle, invoke), use `click({element_index})` to target the element center.

---

## Key behavioral characteristics

- **No standalone `screenshot` tool.** Screenshots are embedded in `get_window_state` responses and in every action tool's return value. Re-call `get_window_state` when you need a fresh view with element indexes.
- **No `mouse_move` / `cursor_position` / `wait` / `list_displays`.** Focus is driven by `launch_app` / `Alt+Tab` / taskbar clicks; observation is driven by `get_window_state`.
- **`get_window_state` is foreground-only.** It always reflects whatever Windows currently considers the foreground window. Bring a different window forward first if needed.
- **Auto-state after every action.** Every action tool (`click` / `type_text` / `press_key` / `scroll` / `drag` / `launch_app`) returns: a fresh full-screen screenshot, the post-action cursor position, the foreground window title + process name, and the current UIA element tree. You can read the visual outcome immediately without calling `get_window_state`.
- **Browser limitation.** Edge / Chrome / Chromium browsers do NOT expose web page content in UIA (only browser chrome — address bar, tabs, toolbar). For web page content, rely on screenshots + coordinate clicks + keyboard shortcuts.

---

## Typical flow

```
list_installed_apps({filter: "记事本"})              // step 0: discover AUMID
launch_app({aumid: "<AUMID from step 0>"})         // step 1: launch app
get_window_state()                                  // step 2: screenshot + UIA tree
click({element_index: "5"})                         // step 3: click a UI element
type_text({text: "Hello, World!"})                  // step 4: type into focused field
press_key({key: "ctrl+s"})                          // step 5: save file
get_window_state()                                  // step 6: verify result
```

The `list_installed_apps` → `launch_app` → `get_window_state` opening triple is the **only sanctioned way to enter an app** at the start of a task — see the "Opening an app" section above for why.

---

## Worked example: Windows Calculator (type over click)

Task: compute `123 + 456 =` in the built-in Calculator app.

**❌ Bad — click every button:**

```
list_installed_apps({filter: "计算"})
launch_app({aumid: "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"})
get_window_state()
click({element_index: "<1>"})
click({element_index: "<2>"})
click({element_index: "<3>"})
click({element_index: "<Plus>"})
click({element_index: "<4>"})
click({element_index: "<5>"})
click({element_index: "<6>"})
click({element_index: "<Equals>"})
get_window_state()                              // verify
```

11 tool calls, 8 of which are individual button clicks. Any button relayout breaks the chain.

**✅ Good — type the whole expression:**

```
list_installed_apps({filter: "计算"})
launch_app({aumid: "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"})
get_window_state()
type_text({text: "123+456=", use_unicode: true})
get_window_state()                              // verify result shows 579
```

Calculator receives real keyboard events via `type_text` with `use_unicode=true`, same path a human using the physical keyboard would take. Apply the same pattern to search boxes, URL bars, chat inputs, code editors, and any input that accepts keyboard.

---

## Common Windows Operations

This section covers key steps for common desktop operations on Windows. Each operation describes the concept and critical steps — use `get_window_state()` to obtain the foreground window's UIA tree and identify exact targets.

### 1. App Management

#### Launch an App via `list_installed_apps` + `launch_app` (preferred)
- Call `list_installed_apps({filter: "<keyword>"})` to discover the target's AUMID.
- Call `launch_app({aumid: "<AUMID>"})` to launch or activate.
- Wait 0.5–2 seconds, then `get_window_state()` to confirm.

#### Launch via Start Menu (fallback)
- Press `Win` key to open Start Menu
- Type the app name, press `Enter` to launch the top result
- Use when the app is not in `list_installed_apps` output

#### Launch via Run Dialog (fallback for portable apps)
- Press `Win+R`, type executable name or full path, press `Enter`

#### Switch Between Apps
- Press `Alt+Tab` to show the task switcher overlay
- Or call `launch_app({aumid})` again — Windows activates existing window
- After switching, always `get_window_state()` to refresh

#### Close an App
- Press `Alt+F4` to close the current foreground window
- Or click the X button via `element_index`

#### Task Manager
- Press `Ctrl+Shift+Escape` to open Task Manager directly

### 2. Window Management

#### Minimize / Maximize / Close
- **Minimize**: `Win+Down` (maximized → restore; restored → minimize)
- **Maximize**: `Win+Up`
- **Close**: `Alt+F4`
- Title bar buttons are accessible via UIA `element_index`

#### Snap Windows (Split Screen)
- **Snap left**: `Win+Left`
- **Snap right**: `Win+Right`
- **Snap to quadrant**: `Win+Left` then `Win+Up` (top-left)

#### Virtual Desktops
- **New desktop**: `Win+Ctrl+D`
- **Switch left/right**: `Win+Ctrl+Left` / `Win+Ctrl+Right`
- **Close current desktop**: `Win+Ctrl+F4`
- **Task View**: `Win+Tab`

### 3. File Operations (Explorer)

#### Open File Explorer
- Press `Win+E` or click the File Explorer icon on the taskbar

#### Navigate to Common Locations
- **Address bar**: `Ctrl+L`, type path, press `Enter`
- **Desktop/Downloads/Documents**: left navigation pane
- **This PC**: see all drives

#### File Operations
- **Copy/Paste/Cut**: `Ctrl+C` / `Ctrl+V` / `Ctrl+X`
- **Delete**: `Delete` (Recycle Bin) or `Shift+Delete` (permanent)
- **Rename**: Select file, press `F2`, type new name, press `Enter`
- **New Folder**: `Ctrl+Shift+N`
- **Select All**: `Ctrl+A`
- **Search**: `Ctrl+F`

### 4. System Settings

#### Open Settings
- Press `Win+I` to open Windows Settings
- Or `list_installed_apps({filter: "设置"})` then `launch_app`

#### Common Settings

| Setting | Navigation Path |
|---------|----------------|
| Wi-Fi / Network | Settings > Network & Internet > Wi-Fi |
| Bluetooth | Settings > Bluetooth & devices |
| Display | Settings > System > Display |
| Sound | Settings > System > Sound |
| Apps & Features | Settings > Apps > Installed apps |
| Windows Update | Settings > Windows Update |

Use the search field at the top of Settings to quickly find any setting.

### 5. Text Editing (Universal)

#### Basic Operations
- **Copy/Paste/Cut**: `Ctrl+C` / `Ctrl+V` / `Ctrl+X`
- **Undo/Redo**: `Ctrl+Z` / `Ctrl+Y`
- **Select All**: `Ctrl+A`

#### Text Selection
- **Character by character**: `Shift+Left/Right`
- **Word by word**: `Ctrl+Shift+Left/Right`
- **To start/end of line**: `Shift+Home` / `Shift+End`
- **To start/end of document**: `Ctrl+Shift+Home` / `Ctrl+Shift+End`

#### Find and Replace
- **Find**: `Ctrl+F`
- **Replace**: `Ctrl+H`

### 6. Browser Operations (Edge / Chrome)

**Important:** Chromium browsers do NOT expose web page content in UIA — only browser chrome (address bar, tabs, toolbar buttons). For page content, rely on screenshots + coordinate clicks + keyboard shortcuts.

#### Tab Management
- **New tab**: `Ctrl+T`
- **Close tab**: `Ctrl+W`
- **Reopen closed tab**: `Ctrl+Shift+T`
- **Switch tabs**: `Ctrl+1`–`Ctrl+8` (Ctrl+9 = last tab)
- **Next/Prev tab**: `Ctrl+Tab` / `Ctrl+Shift+Tab`

#### Navigation
- **Focus address bar**: `Ctrl+L` (or `Alt+D` or `F6`)
- **Back/Forward**: `Alt+Left` / `Alt+Right`
- **Refresh**: `F5` or `Ctrl+R`
- **Hard refresh**: `Ctrl+Shift+R`

#### Other
- **Developer Tools**: `F12` or `Ctrl+Shift+I`
- **Zoom in/out/reset**: `Ctrl+=` / `Ctrl+-` / `Ctrl+0`
- **Full screen**: `F11`

### 7. Terminal Operations (PowerShell / CMD / Windows Terminal)

#### Open Terminal
- Press `Win`, type "Terminal", press `Enter`
- Or `Win+X` → Terminal
- For Admin: search and choose "Run as administrator"

#### Terminal Basics (Windows Terminal)
- **New tab**: `Ctrl+Shift+T`
- **Close tab**: `Ctrl+Shift+W`
- **Split pane horizontal**: `Alt+Shift+-`
- **Split pane vertical**: `Alt+Shift+=`
- **Switch panes**: `Alt+Arrow`

#### Command Control
- **Interrupt command**: `Ctrl+C`
- **End of input**: `Ctrl+Z` then `Enter`
- **Clear screen**: `cls` + `Enter` or `Ctrl+L`

### 8. Office Software (Word / Excel / PowerPoint)

#### Microsoft Word
- **Save / Save As**: `Ctrl+S` / `F12`
- **Bold/Italic/Underline**: `Ctrl+B` / `Ctrl+I` / `Ctrl+U`
- **Find/Replace**: `Ctrl+F` / `Ctrl+H`
- Navigate via Ribbon tabs using `element_index`

#### Microsoft Excel
- **Edit cell**: `F2` or double-click
- **Confirm entry**: `Enter` (moves down) or `Tab` (moves right)
- **Insert formula**: `=` then formula (e.g. `=SUM(A1:A10)`)
- **AutoSum**: `Alt+=`
- **Switch sheets**: `Ctrl+PageUp` / `Ctrl+PageDown`
- **Go to cell**: `Ctrl+G` or click Name Box, type reference, `Enter`

#### Microsoft PowerPoint
- **New slide**: `Ctrl+M`
- **Start slideshow**: `F5` (beginning) / `Shift+F5` (current slide)
- **Exit slideshow**: `Escape`

### 9. Dev Tools (VSCode)

- **Command Palette**: `Ctrl+Shift+P`
- **Quick Open file**: `Ctrl+P`
- **Toggle Sidebar**: `Ctrl+B`
- **Toggle integrated terminal**: `` Ctrl+` ``
- **New terminal**: `` Ctrl+Shift+` ``
- **Split editor**: `Ctrl+\`
- **Go to definition**: `F12` or `Ctrl+Click`
- **Find in files**: `Ctrl+Shift+F`
- **Find and replace**: `Ctrl+H`
- **Toggle line comment**: `Ctrl+/`
- **Move line up/down**: `Alt+Up/Down`
- **Multi-cursor**: `Alt+Click`
- **Format document**: `Shift+Alt+F`
- **Go to line**: `Ctrl+G`

---

## Known Limitations

- **DPI scaling:** Per-Monitor V2 DPI awareness is enabled — screenshot pixels and click coordinates are 1:1 with the physical screen. No conversion needed.
- **UIA coverage:** Some custom-drawn controls (game UIs, embedded canvas, DirectX overlays) do not expose UIA elements. Fall back to coordinate-based interaction.
- **Browser web content:** Chromium browsers (Edge, Chrome) do not expose page DOM via UIA. For web page interaction, use screenshots + coordinates + keyboard shortcuts.
- **Admin privilege windows:** Non-elevated processes cannot interact with UAC dialogs or windows running as Administrator. Inform the user if encountered.
- **Clipboard contention:** Default `type_text` path uses the clipboard. If the user has important clipboard content, use `use_unicode=true` to avoid overwriting it.
- **IME handling:** `type_text` automatically disables and restores IME. No manual intervention needed.
