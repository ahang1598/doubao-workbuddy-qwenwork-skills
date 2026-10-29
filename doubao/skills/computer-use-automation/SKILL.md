---
name: computer-use-automation
description: Use this Windows Computer Use skill whenever the user wants to open, switch to, or operate a desktop app or local GUI and complete a task in it—even when they never mention "computer use" explicitly. Trigger on requests such as opening Calculator/计算器/计算机 app to compute expressions, using another app, changing Windows Settings, handling file pickers, or operating a user-specified local browser session. Also use it when the user names a desktop app for the job (用 WPS/Excel/剪映/FreeCAD 做…), even if scripts or another skill produce the file, since the result must open in that app. This includes controls, menus, dialogs, and windows. Use computer_use_tool plane="cu" with seed_computer_use, observe the current screen before coordinate actions, verify the outcome, and request user takeover for login or other manual-only steps. Not for BU page automation.
---

## The tool

`computer_use_tool` runs Python **on the computer you are operating** — its screen, its
files, its apps. It is not a sandbox and not your own machine.

```
computer_use_tool(plane="cu", code="...", title="Open notification settings")
```

`plane` declares which library the cell drives; a desktop cell declares `"cu"`,
and it is checked against the code. A cell that calls no plane library at all is
refused: file, parsing and shell work goes to `Read` / `Write` / `Glob` / `Grep`
and the shell tool — for a longer program, `Write` a `.py` file and run it there.

The desktop library is already installed:

```python
import seed_computer_use as cu   # the desktop, 0-1000 screen coordinates
```

The whole standard library works too. That matters more than it sounds: checking a
file you just saved, polling for a download, looping over rows, computing
coordinates — all of it belongs **in the same call as the `cu` actions it serves**,
not spread across several. A loop that fills twelve cells is one call, not twelve.
Opening an application is no exception: discovery and launch belong in the same
call.

Python variables do not survive a call. Store values you need later in a file or
in your own message.

`title` is shown to a human as the activity label. Write the intent in a few words
("Fill the year column"), not the mechanism ("call cu.click four times").

## Keep the browser plane fixed

`cu` controls browsers installed on the Windows desktop. `bu` controls a separate
product browser and cannot access the local browser's window or session.

For each browser workflow, choose one plane and keep it fixed. If the user requests
a local or installed browser (such as Chrome, Edge, or Firefox on the desktop), or
the task depends on an existing desktop browser window or profile:

* Use `cu` for every browser action until the task is complete. A webpage displayed
  in that browser remains a `cu` target.
* Do not use `bu` to perform, inspect, continue, retry, or verify any part of the
  workflow.
* If the local browser is unavailable or blocked, report the blocker or ask before
  changing planes; never switch silently.

If the user explicitly requests the product browser, use `bu` instead and keep that
browser workflow on `bu`.

## Required user takeover

When a step requires the user to act personally—for example signing in, entering
credentials, an SMS or email verification code, a QR-code scan, completing a CAPTCHA
or MFA challenge, granting in-app consent, or taking manual control of the current app
or browser—call the session's user-takeover tool (currently
`interaction.request_action`) as soon as the gate appears. Calling the tool is
required: do not merely ask the user in chat, keep retrying automation, wait for the
user to grab the mouse, or work around the gate.

After control returns, assume the UI may have changed. Re-observe the exact app or
desktop before any further action and derive new coordinates from that new
observation. If no user-takeover tool is available, report the blocker and stop
instead of claiming that a plain-text instruction transferred control.

For any CU call, follow the runtime's pause/resume signals when the user intervenes.
After resumption, re-observe before acting. If desktop-control permission is denied
or the user stops the CU session, including with physical Escape, end computer
control and report completed work. Do not retry or switch desktops to bypass the
stop. An Escape key injected by `cu` to close a menu is not a physical user stop.

Each `CU_USER_INTERRUPTED` is such a pause. If the same task is interrupted three
times, the user wants their computer back: stop CU actions, say what is done and what
is left, and ask whether to continue on main, continue in pip, or stop.

Do not answer Doubao's (豆包) own CU permission prompts; granting control is the
user's decision. To change a Doubao setting, give the user the manual steps instead of
changing it yourself. Never edit Doubao's config files, databases or registry entries.

## Switch desktops

`cu.switch_desktop(desktop)` requires exactly `"pip"` or `"main"`. Both use `plane="cu"`; desktop selection is separate from the `cu`/`bu` browser plane.

* **pip** starts as a clean virtual desktop, like immediately after boot. A new conversation starts in pip. Apps open on main have not started here; their windows, playback and in-memory state are not inherited. Launch the apps needed for the task. The user keeps their mouse and keyboard, and PIP windows stay in PIP.
* **main** is the user's visible desktop; operating it takes over their mouse and keyboard.

Both share files on disk. Windows and unsaved work do not transfer; shared files do not imply shared app profiles, login state or settings. A document left open in PIP can prevent the user from opening it on main until the editor releases it.

### 1. Choose the first desktop

Default to pip. Judge the workflow by two questions: does a step need something the user already has on main, and must the result stay on the user's screen? Answer from what the request says or what you have observed, not from what an app might need. If either answer is yes, main is needed for that step; section 3a decides when to switch. Otherwise use pip.

**Main is needed for a step that requires:**

* The user's current main-desktop window, dialog, page or unsaved work, including screenshots of that existing screen.
* Showing the operation on the user's screen, or leaving a window, app or playing media there for immediate use.
* The user's own signed-in session, account data or entitlements, when the request itself depends on them: "用我的会员看", "发到我的抖音", "我微信里的聊天记录", files only in their desktop cloud-drive client. Choose main directly; do not try PIP to recreate that session. An app that *might* need sign-in or membership does not count: start in pip, and if it asks for sign-in there, use Required user takeover. For a service that also has a web version (cloud drive, mail), use the `bu` product browser if it is already signed in, unless the user named the desktop client or their local browser.
* Changing settings the user relies on beyond this task when the effect of changing them in PIP is unconfirmed: Windows system settings, default apps, or normal browser/app configuration such as bookmarks, pinned tabs or vertical tabs.
* A document the user will keep editing right after you finish, asks to see open, or that depends on their Office/WPS account, cloud sync or templates.
* An explicit configuration requiring main.

**Otherwise use pip**, including for:

* Information reported back in chat.
* Files delivered without an open editor: screenshots, exports, downloads, and documents the user only wants saved, such as "生成一个 txt 存到桌面".
* Making a file with a local app when the user only needs the result: a video in 剪映, a model in FreeCAD, a deck in WPS.

Before handing off a PIP file, save it. Only after the save succeeds, close its task-owned document/editor window to release the file. Confirm the file exists at the saved path and give its full path; do not claim the file was released unless you actually checked.

A file or screenshot deliverable does not override a main requirement elsewhere in the workflow. Using an installed app/browser, file picker, local files or `plane="cu"`, saving to Desktop, checking a file in Explorer, or the user saying "my computer", "本地", "电脑上的", "桌面上的 XX 软件/文件" or "导出/保存到桌面" does not alone require main: "桌面" there means the Desktop folder or a shortcut, not the main screen.

### 2. Keep the current desktop in later turns

The client keeps the desktop where the previous turn ended, including after a fallback to main. In a later turn, continue there (**main → main; pip → pip**), for follow-ups and new requests alike, and change desktops only for a reason in section 3. Do not call `cu.switch_desktop` to re-select the current desktop: begin the turn with `cu.screenshot()` and continue the existing task window when present. When you report results, state which desktop you used, so later turns can tell which one is current.

### 3. Change desktops only when needed

* **pip → main:** a request needs main under section 1, or a CU call reports a PIP limitation: initialization failure, pending reboot, no second app instance, or another explicit limitation. Follow runtime codes or the report's meaning, not an exact error phrase.
* **main → pip:** when the user asks, such as "回到虚拟桌面" or "别占用我鼠标", or when the steps that need main are done and verified (section 3a).

For a task on PIP, actually try it. A missed click, slow app or missing window is an ordinary failure: re-observe and retry there.

Before moving to a different desktop, save needed work to disk, close task-owned document windows to release the files, then reopen them there. Windows and unsaved progress do not carry over; returning to PIP may not restore them.

Before a desktop change, briefly tell the user which desktop you will use and whether it takes over their mouse and keyboard. Before switching to main, give the reason in one sentence (the section 1 requirement that applies, or the PIP limitation that was reported) and a rough estimate of how long you will use main; for pip → main, also mention that unsaved progress will not transfer. Do not routinely ask the user to choose a mode.

### 3a. Keep main short

Main blocks the user's mouse and keyboard for as long as you hold it, including while you think, write code or run the shell.

* **Prepare first.** Do investigation, installs and downloads through the shell, content generation and skill reading before `cu.switch_desktop("main")`, then switch right before the first GUI action that needs main.
* **Use main only for the steps that need it.** Do the rest in pip and switch to main only for the step that needs it, such as showing the result, changing a setting, signing in or publishing.
* **Leave when done.** Once that step is verified, switch back to pip before any further work or ending the turn, unless the user asked you to stay on main. Check files with the shell or `Read` instead of reopening screens you already verified.
* **Shell and COM count.** Attaching to a running app through COM, or opening a document or URI on the user's desktop with `Start-Process`, acts on main: announce it the same way and keep it short.

### 4. Select, screenshot, then act

When you change desktops, call `cu.switch_desktop` followed by `cu.screenshot()`. End the cell and inspect the image before further actions:

```python
import seed_computer_use as cu
cu.switch_desktop("main")  # Use "pip" when that is the chosen desktop.
cu.screenshot()
```

Discard earlier coordinates. Before launching an app in a new turn or after a desktop change, rerun `cu.list_apps()` and launch only a name from that new listing.

The API waits for desktop readiness and required control permission. After a failed selection, do not assume the target is active.

## Looking at the screen

```python
import seed_computer_use as cu     # every call, not just the first
cu.click(504, 358)
cu.screenshot()          # <- the frame comes back as an image in this result
```

Asking for the screen is the single biggest habit to change. Acting without ever
looking is the most common way to fail: you will click a menu item that moved, type
into a window that never took focus, and never find out.

Observe when the next decision depends on what is on screen. Do **not** take a
frame after every single action — a batch of actions followed by one frame is
usually right, and images are expensive.

## Coordinates

`cu` uses **0-1000 on both axes** over the whole screen: `(0,0)` top-left,
`(1000,1000)` bottom-right, `(500,500)` dead centre. Read a target's position off
a screenshot as a fraction of the image and give it in those units. Never pass raw
pixels.

## Apps and launching

`launch_app(name)` only accepts an exact `App.name` bound by a `list_apps()` call
in this session, so discovery comes first — in the same cell is fine:

```python
import seed_computer_use as cu
apps = cu.list_apps()
matches = [app for app in apps if "notepad" in app.name.casefold()]
if len(matches) != 1:
    print(matches[:5])
    raise RuntimeError("expected exactly one match")
result = cu.launch_app(matches[0].name)
print(result)                 # status="ready" or "accepted_unverified"
cu.screenshot()               # mandatory fresh whole-desktop observation
```

Print the candidates you filtered down to, as above — the launch itself is
verified against the catalog, but a wrong *choice* is only visible to you.

* `list_apps()` returns the complete `AppCatalog[App]`. Each App is only `{name}`, the
  application's own Start-menu name. Names in one listing are unique ignoring case;
  when two apps share a name, the listing qualifies both, such as `Calculator (Store)`
  and `Calculator (Desktop)`. The catalog's `repr` shows only a short preview, but the
  list is complete: filter it in Python and print only the matches.
* `launch_app(name)` refuses anything but an exact name from the latest listing: a
  differently-cased, padded or partial name, a path, an executable, an AppID/AUMID or
  a URI, even when Windows could launch it. A new `list_apps()` call or a new session
  replaces the previous bindings. Keep the selected name in your own message for a
  later launch cell.
* `launch_app` returns `status="ready"` once a matching visible window appears, or
  `status="accepted_unverified"` when Windows accepted the request but no window is
  confirmed yet. `accepted_unverified` is not an error: do not launch a second time;
  observe the whole screen and wait for it.

`list_apps()` → `launch_app(exact App.name)` is the only way an application gets
opened. To switch to an app that is already open, use `cu.screenshot()`,
`cu.hotkey("alt", "tab")`, then take another screenshot; do not use `launch_app` as
a focus operation.

A `cu.screenshot()` covers the **whole screen**. Observe again after focus,
layout, menu, dialog, or application changes before deriving another coordinate.

## Batching coordinates: when it is safe

Batching is why this tool exists, but coordinates come from a specific frame and
some actions invalidate them.

**Safe** — the actions do not change the layout:

```python
import seed_computer_use as cu
cells = [(77, 306, "2015"), (77, 322, "2016"), (77, 338, "2017")]
for x, y, v in cells:
    cu.click(x, y)
    cu.type(v)
    cu.hotkey("enter")
cu.screenshot()
```

**Not safe** — the action changes what is on screen, so anything after it needs a
*new* frame:

```python
cu.click(120, 40)      # opens a menu
cu.click(140, 95)      # WRONG: this coordinate did not exist when you looked
```

Opening a menu, opening a dialog, switching desktops or tabs, and scrolling all
fall in this group. Do the state-changing action, take a frame, and end the cell
there. Writing both halves in one cell cannot work — the second coordinate has not been observed
yet.

## The helpers

```
cu.click(x, y)              cu.left_double(x, y)      cu.triple_click(x, y)
cu.right_single(x, y)       cu.hover(x, y)            cu.drag(x1, y1, x2, y2)
cu.scroll(x, y, delta)      cu.type(text)             cu.hotkey(*keys)
cu.press(key)               cu.key_down(key)          cu.key_up(key)
cu.wait(seconds)
cu.screenshot(tag=None)     cu.list_apps()            cu.launch_app(name)
cu.switch_desktop(desktop)
cu.get_clipboard()          cu.set_clipboard(text)    cu.copy_selection()
```

* `cu.type("hi\n")` — a trailing newline presses Enter. Non-ASCII text (Chinese,
  say) is handled for you, as is text too long to type key-by-key.
* `cu.copy_selection()` presses Ctrl+C and hands back what was caught — the
  cheapest way to check a selection landed where you meant. Use `cu.get_clipboard`
  rather than tkinter, raw ctypes, or `Get-Clipboard`; those all misbehave here.
* `cu.scroll(x, y, delta)` accepts a non-zero integer from `-10` to `10`;
  positive scrolls up and negative scrolls down. Exact aliases `"up"`,
  `"down"`, `"left"`, and `"right"` are also supported, for example
  `cu.scroll(500, 500, "right")`. There is no `amount=` keyword here; that one
  belongs to the page API.
* `cu.hotkey("enter")` taps one key; `cu.hotkey("ctrl", "s")` taps a
  combination. Pass each key separately rather than writing `"ctrl+s"`.
  `cu.press(key)` also taps one key. To hold a key across actions, pair
  `cu.key_down(key)` with `cu.key_up(key)`.
* `cu.wait(seconds)` is measured in seconds (maximum `180`). Millisecond-style
  values such as `1000` are rejected; use `cu.wait(1)` instead.
* `cu.hover(x, y)` moves the pointer without clicking; `cu.move` and
  `cu.move_mouse` are the same function.
* `cu.screenshot(tag="after")` — the tag only matters when one cell takes more
  than one frame; plain `cu.screenshot()` is the normal call. It returns the PNG
  frame: `.width` / `.height` give you the screen size, and `.save(path)` writes it
  to a file. Use `cu.screenshot().save(path)` for screenshot deliverables; PIL and
  `ImageGrab` may not be installed.
* Windows paths: use a raw string such as `r"C:\Users\Public\report.txt"`, doubled
  backslashes such as `"C:\\Users\\Public\\report.txt"`, or `os.path.join` — never
  paste `C:\Users\...` into an ordinary Python string (`\U` starts an escape).

## When the user names the app

If the user names an app for the job (WPS, Excel, 剪映, FreeCAD), the result must open
correctly in that app; the work itself does not have to happen in its GUI. Prefer CLI,
MCP or scripts when they can produce the result, and use the app's GUI for the steps
they cannot do. If the app seems missing, check with the shell whether it is installed.
Before you report done, open the result in that app and check it. Do this in pip and
close it afterwards: start the app with `launch_app` and use its Open dialog, because
`Start-Process` or COM from the shell opens it on main.

If a GUI step hits a paywall, missing feature or error, investigate before giving it
up: an export paywall often lists the member-only items, so replace those with free
ones first. If you still cannot deliver a result that opens in the named app, or one
from the source the user named, ask before delivering a substitute. Never switch app or
source silently.

## Verify by reading, not only by looking

A screenshot tells you what a window is showing; the file system tells you what
actually happened. When you have just saved, exported or downloaded something, read
it back in the same cell:

```python
import os, time
import seed_computer_use as cu
cu.hotkey("ctrl", "s")
cu.wait(2)
p = os.path.join(os.environ["USERPROFILE"], "Documents", "report.xlsx")
print("saved:", os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)
```

That check costs nothing, needs no image, and catches the case where the save
dialog silently went somewhere else.

Do not report a step as done until you have read its result back. For a GUI setting,
reopening its page and reading the value is enough; no registry check is needed. A
setting changed outside the app's UI (a config file, the registry) counts only once the
app shows the new value, which may need a restart.

## Changing the user's machine

Change only what the task needs.

* Before you change a setting or file the user already had (system, browser or app
  settings, the wallpaper, an existing document), note its original value. Before you
  save over an existing document, put a backup copy in a temporary folder.
* Close or delete only windows and files this task created. Never bulk-close windows or
  bulk-delete files by pattern.
* Keep scratch files in a temporary folder, not on the Desktop or in the home folder.
  Say so before installing packages into the user's Python or apps.
* In the final reply, list every setting you changed and whether you restored it; do
  not say nothing changed unless you checked.