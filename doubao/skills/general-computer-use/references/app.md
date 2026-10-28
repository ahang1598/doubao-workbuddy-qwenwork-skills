# App reference

**Tool name to invoke:** `general_computer_use`

This reference belongs to the Skill named `general-computer-use`; that Skill name is not callable. Use the tool name above exactly, with no `_tool` suffix. Before submitting any `gcu` or `app` example, check that the tool-name field is `general_computer_use` and place the Python source in its `code` argument.

The prebound `gcu` object and App variables belong to that tool's persistent Python session; do not execute these examples in a shell, standalone Python, another Python/REPL tool, or a different computer-use tool. For an unknown-tool error, correct the tool name before changing Python code or App bindings. If the available definitions do not include `general_computer_use`, report the missing tool.

On macOS, select with `gcu.get_app("Example App")` using an app name, path or bundle ID; a window title is not an app identifier. Selection can launch the app in the background and displays its initial AX state. It takes a string and an optional discovered `window_id`, and has no observe or emit argument. Follow the returned App capabilities; absent capabilities are unknown. `gcu.computer.target` is `"mac"`.

App inventory records contain `id` and optional `displayName`, `lastUsedDate`, `useCount`, `isRunning`, `paths`; optional fields are omitted when unavailable. When `paths` lists several installations, select the intended full path, because the shared bundle ID is ambiguous. `useCount` counts how many times an app has been opened and `lastUsedDate` records its latest opening; the inventory is ordered by `lastUsedDate`. To find the app an action opened, see the Skill.

An App binding stays with its app when a link or action opens another app; rereading it, even with `disable_diffing=True`, still observes the source, and its indices stay scoped to that app. Find and bind the destination as described in the Skill, and read its initial state before input. A newly opened or frontmost app may belong to the user or another agent.

## Keyboard and text

`get_app(...)` returns an App even for Electron apps or embedded web content. App keyboard methods use current focus and take no index: `app.type_text("text")`, `app.press_key("Return")`, `app.paste("text")`.

With the default native policy, keyboard actions use the current focus within the selected window, including after Tab navigation. Indexed actions refetch and validate the target's own attributes; a parent label changing does not invalidate it, and a uniquely matching rebuilt control stays usable within its web document, while a same-named control on another page does not inherit the index. A failed click is never replayed.

`WINDOW_NOT_FOCUSED` means the app reports a different keyboard window, not that the app must be frontmost: observe the intended window and focus its intended control before keyboard input. `KEYBOARD_FOCUS_UNVERIFIED` means focus information stayed unavailable, not that another window has focus: read `get_state(disable_diffing=True)` through the same binding and report the condition if it persists. Neither error authorizes replaying earlier input. Reading a covered window does not give it keyboard focus.

`type_text` sends Unicode character key events, with line breaks sent as Return; `paste` invokes the app's clipboard handler, which may transform the content. App `paste(text, format=...)` uses the system pasteboard and restores the user's previous contents unless a newer user copy intervenes; formats are `text`, `md` and `html`. Prefer paste for formatted and multiline text when the editor supports it.

To replace all text in a focused editor, select, paste, and observe in one call:

```python
app.press_key("super+a")
app.paste("Replacement text")
app.get_state()
```

If the task concerns only a text range, select that range instead. For a label or canvas object, first enter text-editing mode and inspect the editor or caret. Press Return only when it is known to commit that editor; outside editing it can create another item. Missing AX text alone does not establish failed input.

Self-drawn fields may leave AX focus on the window even while editing, so window focus alone does not establish that a field will receive text. Inspect the field's editing state before selecting its contents and verify its actual value after committing. If a shortcut acts on other content instead, stop typing; use the explicit window `Raise` recovery below when permitted, inspect the new state, then enter the intended field. Do not infer a changed value from successful key dispatch or unchanged AX.

`settable` identifies controls eligible for direct AXValue replacement; it does not identify a text editor. Web text editors, including ordinary webpage input and textarea controls, are excluded because AXValue can change their displayed text without updating the page's input state: click to focus, then use `app.paste(text)`, selecting existing contents first when replacing them. Native controls keep focus-independent `set_value`. An exposed action is not proof that the control is enabled or that the app will handle it; verify the resulting state. `enabled unknown` and `selection unknown` mean the app did not publish that state, not that it is disabled or unselected; when it matters, verify the visible effect.

## Window selection and recovery

Use `gcu.list_windows("Example App")` to inspect same-app windows and select by the returned ID, not by assuming that the frontmost window is the task window:

```python
windows = gcu.list_windows("Example App")
```

After reading the list, replace `123` with the intended window's actual ID:

```python
app = gcu.get_app("Example App", window_id=123)
```

A selected window pins AX, screenshots and pointer input to that window without raising it; keyboard input still requires focus in it. Window records contain `id`, `app`, `pid`, `title`, `is_focused`, `is_main` and `is_minimized`. Window IDs come from live discovery and are not stable app identifiers. When several processes run from one installation, `APP_AMBIGUOUS` requires this window selection, and the returned App stays with the selected process.

An unpinned binding follows the app's current window, including its dialogs; a changed window returns full AX and a window-change notice instead of a diff. A pinned binding keeps its window and fails rather than falling back when that window closes. For a pinned binding, an `APP_WINDOW_CHANGED` notice that offers `current_window_id` has verified that window in this session: if it is the intended target, select it with `gcu.get_app(app_name, window_id=<current_window_id>)`. Otherwise, or after `STALE_WINDOW` or `WINDOW_NOT_FOCUSED`, inspect `gcu.list_windows(app_name)`; if the pinned window remains the target, read its state and check keyboard focus before input. End the call after an action that may open another window, and refresh the screenshot after a geometry change before coordinate input. Do not replay a failed batch wholesale; check `action_summary`, because earlier actions may already have happened.

An `ACTION_OUTCOME_UNCONFIRMED` result stops the cell and attempts a bounded AX refresh through the same binding. If `observation_refreshed` is true, inspect the included current state and choose the next action from its indices. The action remains unconfirmed; the refresh does not authorize replay. If the refresh failed, the original receipt includes `observation_refresh_error`; observe before deciding what to do next.

An AX target does not need to appear in the screenshot to be used by index; the backend handles supported reveal actions. `ELEMENT_OUTSIDE_OBSERVED_WINDOW` means the live parent chain and window owner place the element in a different window: identify the intended window from `gcu.list_windows(app_name)`, bind only a returned ID, and choose a fresh element there. `ELEMENT_SCOPE_UNVERIFIED` means the window or attachment could not be verified, not that the element belongs elsewhere: reread `get_state(disable_diffing=True)` on the same binding, and report it if scope stays unavailable.

`WINDOW_AX_UNAVAILABLE` and `WINDOW_SERVER_UNAVAILABLE` are read failures, not proof that the app has no windows. Keep an existing binding and retry its observation; if `get_app()` failed before assignment, use `gcu.list_windows(app_name)` and select a returned ID. Report persistent failures instead of repeatedly rebinding or reopening the app, and do not alternate `get_app()` and `list_windows()` or invent a window ID. An empty window list is distinct from a failed read.

After closing the last window, an unpinned App may return `APP_NOT_SURFACE`. Inspect `gcu.list_windows(app_name)`; if it successfully returns an empty list and the task still needs the app, make one fresh `gcu.get_app(app_name)` selection. Normal preparation verifies whether the running app is windowless before requesting its normal UI. Refreshes and discovery never reopen it. If that selection still fails, report the result instead of looping or resetting the session; existing preparation stops still apply.

## Background and covered windows

A minimized, hidden or off-Space window may still expose current AX while retaining old rendered pixels. `SCREENSHOT_WINDOW_NOT_VISIBLE` returns AX without a screenshot. If a visual result is needed, use the observed window's advertised `Raise`, then read a new screenshot; the failed capture does not mean prior input failed.

Native observations read covered windows without bringing them forward. With `window_order_restoration` enabled, ordinary background input restores the user's focused window above a target that raises itself. `web_window_render_preparation=False` disables automatic exposure for reads. A covered app may accept input while keeping an old rendered frame, and web views may keep stale AX layout or popup contents. Check AX values, document identity and URL; do not submit an old form again or alternate clicks, scrolling, dragging and Escape to force an update.

If the requested result remains unverified because a covered web view or self-drawn surface is not updating, inspect full AX once and use the current window's advertised `Raise` when `exposed_secondary_raise` permits it. For a regular application window this verifies window focus and may activate its app when AXRaise alone is ineffective; it does not restore the covering window afterward. Ordinary reads and inputs do not automatically expose the window or change input policy. Choose the window index from the current AX tree:

```python
app.perform_secondary_action(window_index, "Raise")
app.get_state(screenshot=True)
```

Read this result in a separate model turn before further input, and do not replay the original action in that recovery call. If Raise is unavailable or the recovery still cannot establish the result, explain the concrete blocker. Respect an explicit user requirement to keep the window covered. No generic activate-and-restore API exists.

`app.drag(...)` requires the destination and its immediate approach to receive input in the selected window; the source can be covered. `DRAG_DESTINATION_OCCLUDED` and `DRAG_DESTINATION_UNVERIFIED` refuse before the drag begins, also for in-window selection and slider drags. If exposing the destination is permitted and the window advertises `Raise`, invoke it, observe again and plan a fresh drag; if obstruction persists, report it instead of cycling through Raise and drag. Otherwise use a semantic control or report the limitation. Do not repeat a covered drag, use another activation route or switch to desktop input. A completed drag does not prove a drop; verify the destination.

## Controls and output

The app-access gate may ask the host for authorization when selecting an unapproved app; existing user authorization and the effective host policy decide whether more confirmation is needed. A refused app must not be observed or controlled through another identifier, session or automation route. App GUI access is separate from the host's independently authorized command and file work: a refusal limited to Computer Use access to an app does not revoke ordinary non-GUI work, which follows the host's rules, and the availability of a shell does not grant permission. A user or host refusal covering the underlying resource, operation or task applies across tools; never use another tool to perform the denied operation, and do not treat an ambiguous refusal as permission to switch routes. `APP_ACCESS_DENIED` with `permission_scope="app_gui"` identifies the daemon's app GUI policy, and `next="stop"` stops that access, not unrelated authorized work. Generic `ACTION_REFUSED`, system permission errors and unavailable approval transport do not establish a GUI-only scope. This guide grants no additional access.

Follow the returned menu/desktop capabilities in the App documentation block; availability depends on the configured daemon policy. When `system_menu_input` is true, click an observed menu title or popup control, then observe its open menu before targeting a command; menu input may affect global focus or window order. `MENU_INPUT_RESTRICTED` means the configured policy forbids that menu operation: use an in-window control or verified shortcut instead of repeating it. App-wide menus act on the app's active window. If a menu action reports `WINDOW_NOT_FOCUSED`, observe the intended window again and, when bringing it forward suits the task, use its advertised `Raise` before choosing the menu target; do not reuse menu indexes from another window. Before returning from an open menu to document editing, close it with Escape or its advertised `Cancel` secondary action and observe that it closed. Then select the intended cell or editor and verify the committed value; dismissing a menu does not restore the intended selection.

App keyboard input is delivered to the selected application. It does not invoke macOS global shortcuts such as Cmd+Shift+3/4/5, switch applications, or operate the system screenshot overlay. App screenshots cover the app window or composed menu canvas, not the desktop; for image files and system screenshots, see the Skill.

In a native file panel, `children_unavailable` describes an unreadable region, not an empty directory. If the intended absolute path is known, Cmd+Shift+G opens Go to Folder: replace its path and press Return. Verify the selected filename and path before clicking Open or Save. Do not guess filenames or keep rereading the panel to recover a missing file list.

## App signatures

App inherits the shared Target methods. Its keyboard methods use current focus and have no element-index argument.

<!-- api:app:start -->
```text
App:
  .click(target, *, mouse_button='left', click_count=1)
  .drag(from_, to)
  .get_state(*, screenshot=False, disable_diffing=None, emit=True)
  .paste(text, *, format='text')
  .perform_secondary_action(element_index, action)
  .press_key(key)
  .scroll(target, direction, distance=None)
  .select_text(element_index, text, *, prefix=None, suffix=None, selection_type='text')
  .set_value(element_index, value)
  .type_text(text)
```
<!-- api:app:end -->

