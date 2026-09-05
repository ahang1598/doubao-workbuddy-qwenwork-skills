---
name: computer-use-automation
description: Use this Windows Computer Use skill whenever the user wants to open, switch to, or operate a desktop app or local GUI and complete a task in it—even when they never mention "computer use" explicitly. Trigger on requests such as opening Calculator/计算器/计算机 app to compute expressions, using another app, changing Windows Settings, handling file pickers, or operating a user-specified local browser session. This includes controls, menus, dialogs, and windows. Use computer_use_tool plane="cu" with seed_computer_use, observe the current screen before coordinate actions, verify the outcome, and request user takeover for login or other manual-only steps. Not for BU page automation.
---

## The tool

`computer_use_tool` runs Python **on the computer you are operating** — its screen, its
files, its apps. It is not a sandbox and not your own machine.

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

Since nothing survives a call, anything you need later goes onto the machine (a
file) or into your own message — a value you computed is only usable in the call
that computed it.

`title` is shown to a human as the activity label. Write the intent in a few words
("Fill the year column"), not the mechanism ("call cu.click four times").

## Required user takeover

When a step requires the user to act personally—for example signing in, entering
credentials, completing a CAPTCHA or MFA challenge, granting consent, or taking
manual control of the current app or browser—call the session's user-takeover
tool (currently `interaction.request_action`). Calling the tool is required: do
not merely ask the user in chat, keep retrying automation, or work around the
gate.

After control returns, assume the UI may have changed. Re-observe the exact app or
desktop before any further action and derive new coordinates from that new
observation. If no user-takeover tool is available, report the blocker and stop
instead of claiming that a plain-text instruction transferred control.

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

The two public application methods are:

* `list_apps()` → complete `AppCatalog[App]`; each App is only `{name}`, and
  every name in one listing is unique ignoring case
* `launch_app(name)` → launch one exact `App.name` from the current listing,
  then return `status="ready"` with matching window evidence or
  `status="accepted_unverified"` when Windows accepted the request but no
  matching visible window was confirmed yet

`name` is the application's own Start-menu name. When two of them share one, the
listing qualifies both — `Calculator (Store)` and `Calculator (Desktop)` — so
every application in a listing has exactly one spelling. The match is exact: a
differently-cased name, a padded one, or part of one is refused. It is never a
path, an executable, an AppID/AUMID, or a launch target. Keep the selected name
in your own message for the later launch cell.

`AppCatalog` is a normal complete list for iteration, indexing, slicing, and local
filtering. Its raw `repr` is bounded to a short preview, but the underlying list is
not truncated. Keep it in `apps`, filter in Python, and print only `matches`; an
app beyond the preview remains discoverable by local code.

Every `list_apps()` call creates a new discovery generation and supersedes the
previous listing's bindings; a new session invalidates them too. `launch_app`
rejects missing, unknown, or changed-descriptor names, and it rejects a
differently-cased or partial name, a URI, a bare executable, or a path even when
Windows itself could launch it. `list_apps()` → `launch_app(exact App.name)` is
the only way an application gets opened.

For Win32 applications, `launch_app` uses the resolved executable, arguments,
and working directory from the live catalog; packaged apps use AppsFolder. It
returns `status="ready"` only after a matching visible window appears. An
accepted request that is still unconfirmed returns `accepted_unverified`; this
is not an error and must not be launched a second time. Observe the whole screen
and wait for the existing request instead. To switch to an app that is already
open, use `cu.screenshot()`,
`cu.hotkey("alt", "tab")`, then take another screenshot; do not use
`launch_app` as a focus operation.

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

Opening a menu, opening a dialog, switching tabs and scrolling all fall in this
group. Do the state-changing action, take a frame, and end the cell there. Writing
both halves in one cell cannot work — the second coordinate has not been observed
yet.

## The helpers

```
cu.click(x, y)              cu.left_double(x, y)      cu.triple_click(x, y)
cu.right_single(x, y)       cu.hover(x, y)            cu.drag(x1, y1, x2, y2)
cu.scroll(x, y, delta)      cu.type(text)             cu.hotkey(*keys)
cu.press(key)               cu.key_down(key)          cu.key_up(key)
cu.wait(seconds)
cu.screenshot(tag=None)     cu.list_apps()            cu.launch_app(name)
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
  bytes, and `.width` / `.height` on that value give you the screen size.
* Windows paths: use a raw string such as `r"C:\Users\Public\report.txt"`, doubled
  backslashes such as `"C:\\Users\\Public\\report.txt"`, or `os.path.join` — never
  paste `C:\Users\...` into an ordinary Python string (`\U` starts an escape).

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