---
name: general-computer-use
description: Operate macOS apps using the exact tool name general_computer_use, with persistent Python, accessibility observations and screenshots.
---

# General Computer Use

## Exact tool name

- **Tool name to invoke:** `general_computer_use`
- **Skill name:** `general-computer-use` (documentation, not a callable name)

Copy the tool name exactly from the available tool definition. Do not append `_tool`: `general_computer_use_tool` is an incorrect name, not an alias. Before submitting each call, check that its tool-name field is exactly `general_computer_use`.

For example, invoke `general_computer_use` with this JSON argument object, replacing the illustrative app name with the requested app:

```json
{"code": "app = gcu.get_app('Example App')"}
```

Execute all `gcu` and App examples through its `code` argument in the same persistent Python session. Do not run these examples in a shell, standalone Python, another Python/REPL tool, or a different computer-use tool. If a call is rejected with an unknown-tool error, check and correct the tool name before changing the Python code or App binding. A rejected misspelling does not establish that the required tool is unavailable. If the available definitions do not include `general_computer_use`, report the missing tool.

This tool runs synchronous Python in a **persistent session**. `gcu` is already bound; keep using the same App variables across calls instead of repeating `import gcu` or `get_app` as per-call setup.

Prefer a purpose-built tool, API or CLI for work the user has not tied to a particular app or method. For UI work, read this Skill and the relevant [App reference](references/app.md) before selecting a target. An Electron app or embedded web view selected with `get_app` is still an App. Runtime output supplies current configuration and capabilities.

## Work to the request

The request defines what done means. Before acting, identify every explicit requirement: the outcome, the means the user specified, and any exact values or constraints.

- **Honor the specified means.** When the user specifies how a step should be done, such as an app, tool, format or method, treat it as a requirement. If one way of using it fails, try other ways within it before concluding it cannot be done, and switch to other means only with the user's agreement.
- **Keep exact requirements exact.** Quantities, names, values, ranges and text from the request are requirements, not suggestions. Apply them as given, and cover every item the request lists or implies.
- **Work from what is actually there.** Base actions and answers on what you observe. Carry existing content over from its source instead of reconstructing it, and never fill a gap with assumed content. When a task continues earlier work, start from its latest result.
- **Work around obstacles before stopping.** When something blocks progress, look for another legitimate path. Involve the user only for what requires them, such as credentials, payment, permissions or a decision.
- **Verify the result itself.** Confirm the outcome by observing the final state or the produced artifact as the user will see it, including how it looks when appearance matters.
- **Self-check before the final reply.** Reread the request and confirm each requirement against evidence you observed. If anything is missing, unverified or done differently than asked, keep working; report a gap only when it cannot be closed.
- **Report precisely.** Say what was done and where the results are, and state plainly what is incomplete, substituted or unverified. Never claim a result you did not observe.

## Select once, then reuse

For a named app, the first tool call selects it and displays its initial AX state:

```python
app = gcu.get_app("Example App")
```

Read that result. If it shows settable fields 21 and 24 and a Save button 31, the next call can fill the form, save and display the result:

```python
app.set_value(21, "Ada")
app.set_value(24, "Shanghai")
app.click(31)
app.get_state()
```

Replace the illustrative names, indices and values with the actual task and observation. Select again only to change target or window, or to recover a lost binding.

On first use or after a Python session reset, choose one entry point and let it return before acting, so you can read the effective policy, capabilities and initial state:

- Unknown target: `gcu.get_state()`.
- Named app: `app = gcu.get_app("Example App")`.
- Specific app window: discover with `gcu.list_windows("Example App")`, then select the intended returned ID with `gcu.get_app("Example App", window_id=...)`.

## Observe, decide, act

For native Apps, batch deterministic actions and the resulting `app.get_state()` into one call, such as filling known form fields and saving. Keyboard input and commands that act on the selection go to whatever is focused or selected when they run; if an earlier action in the same call may move focus or the selection, such as Return in a field or a click on a container, end the call and check first. When the next action needs new UI information, such as an unfamiliar dialog's controls, end the call with `get_state()` and read the result. A failed call does not undo earlier actions, and a dispatched action is not proof that the app completed it.

Use `get_state()` for routine observation and verification. Request `screenshot=True` for visual information AX lacks, such as layout, fonts, colors or what an image shows, or for an image the user requested, not to double-check a non-visual result. AX-exposed controls still use element indices. Keep `emit` enabled for screenshots (`screenshot=True, emit=False` is rejected with `SCREENSHOT_DISPLAY_REQUIRED`), and do not save or capture screenshots to reopen them with Read or another tool.

`get_state()` returns `{"state": str, "screenshot"?: bytes}`. AX defaults to a diff, also with `screenshot=True`: apply it to the previous tree for the same target. `no change` means unchanged, not empty, and proves neither success nor failure; unchanged AX does not imply unchanged pixels. Use `disable_diffing=True` for full current AX, for example when the target's context is missing. AX may include offscreen controls and omit visible custom-drawn ones. Use the observation's `Target` app and window ID; a dialog or document title is **not an app identifier**, and an unpinned App follows the app's current window.

### Images for the user

An observation's `"screenshot"` shows only the selected window, as GCU captured it. For an image file, decide from the request what it must show and how it must be made; if an image of that window fits, save the bytes of a displayed observation, such as `result = app.get_state(screenshot=True)`.

A request for the system screenshot tool, the full screen or the desktop needs a system capture: `screencapture -x <file>` for the full screen, or `screencapture -x -l <window_id> <file>` for one window, using the observation's `Target` window ID. Make sure nothing the user wants excluded is visible, then check the saved image. If `screencapture` fails, for example with `could not create image from display` because the shell lacks Screen Recording permission, report that and ask before delivering a GCU image instead.

### When an action opens another app

A binding stays on its own app. A link, an Open, Share or Export action, or a preview can bring up another app while the source looks unchanged. Before retrying, call `gcu.get_state()` and compare its app inventory with the one from before the action. `useCount` counts how many times each app has been opened and `lastUsedDate` records its latest opening, and the inventory is ordered by `lastUsedDate`, most recent first. The app whose `useCount` went up or whose `lastUsedDate` is now the most recent, or whose `isRunning` became true, is where the action went. Select it with `gcu.get_app(...)` and read its initial state before input; the source binding does not switch by itself. An app the user opened meanwhile can look the same, so check that the destination's initial state matches your action. `gcu.get_state()` discovers targets; it is not an App observation.

## Recover before retrying

After `STALE_ELEMENT` or `STALE_OBSERVATION`, use the current AX state included with the error; a native indexed click rereads automatically and marks it with `observation_refreshed: true`. Otherwise request a recovery observation in its own call:

```python
app.get_state(disable_diffing=True)
```

Inspect it before the next action; reading into a variable and acting on an old index in the same call is not recovery. If the requested result is already present, stop instead of repeating the action.

For `APP_WINDOW_CHANGED`, `FOCUS_CHANGED`, `WINDOW_NOT_FOCUSED` or a stale window, check the observed window identity before continuing. For `APP_NOT_FOUND`, use an app identifier from inventory, not a page or window title; for `APP_NOT_RUNNING`, check process availability before relaunching. The App reference covers pinned windows and keyboard focus.

## Choose an input target

Use an AX element index when AX identifies the target by role, label and ancestry and supports the interaction, even if the target is also visible in a screenshot. A screenshot, a coordinate annotation, a stale index, `no change` or one unchanged click does not mean AX is unavailable; recover full AX instead of switching to coordinates. An indexed click on an element without a press action lands at its center, so a page-sized container is not a substitute for a button or a cell. Before typing into a grid, canvas or document, select the intended cell or place the caret through its own element or the app's navigation control, and confirm where input will land.

If AX does not expose the control, as on a self-drawn surface, or the correct control cannot perform the interaction, use its position in a fresh screenshot and inspect the result. This applies only to that control, and window, focus and policy checks still apply. Coordinates are relative by default and can be configured as absolute: use the runtime's units, never infer points from element numbers, and do not change operator policy to bypass a refusal. An explicit `elements_only` policy forbids coordinate input but still allows screenshots.

An unchanged screenshot can be an old frame even when input succeeded, and covered web views can keep stale AX layout or popup contents. Compare AX content, values and URL before retrying, and do not repeat input just to update the image. If the result stays unverified because a covered web view or self-drawn surface is not updating, use the window's advertised `Raise` secondary action when permitted, then inspect `get_state(screenshot=True)` before deciding what remains, without replaying the original action in that call. Respect an explicit requirement to keep the window covered, and report the blocker if exposure is unavailable or does not resolve it.

Stop when the returned state establishes the requested result; AX confirmation suffices when it provides the evidence. Toolbar and inspector states describe the current selection, which may not be what you meant, so confirm it. Commands that act on a selection, such as sort, replace or format, change everything selected; check the result for unintended changes. Attempting an action is not completion: if an approach leaves the state unchanged twice or only reaches an intermediate page, change approach, and if you still cannot establish the result, explain the concrete blocker and what you tried.

## API essentials

Methods and parameters use snake_case; ordinary options are keyword-only, so omit unused ones instead of passing an options dictionary or `{}`. There are no Element handles, Frame records or extra public helper methods.

- Observations and discovery display automatically; omit `emit` normally. For AX-only processing, read silently and display what you need, such as `result = app.get_state(emit=False, disable_diffing=True)` then `gcu.write(result["state"])`; a trailing observation value is not echoed. Silent reads still advance the diff baseline, and the next displayed observation restores context they skipped.
- `click` and `scroll` take an AX index or a two-number point; `None` is not a target. The first `scroll` argument is the target, never the distance: `app.scroll(42, "down", 1)` scrolls element 42 by one page. Click keywords are `mouse_button` (`left`, `right`, `middle`) and `click_count`; scroll directions are `up`, `down`, `left`, `right`.
- App keyboard methods use current focus: `app.type_text("text")`, `app.press_key("Return")`, `app.paste("text")`.
- App `set_value` replaces a native control's complete value without focusing or committing its editor, so later keyboard input still goes to the previously focused element; click the field first when you need its own Return or editing behavior. Web text editors need a click to focus and `app.paste(text)`, after selecting any text being replaced. Enter and observe text-editing mode before replacing a label or canvas object's text. Return can commit an editor or create another item.
- `select_text` uses `prefix`/`suffix` to disambiguate and `selection_type` (`text`, `cursor_before`, `cursor_after`) to select text or place the caret. `perform_secondary_action` requires an action exposed by that element; do not guess action names.
- `press_key` uses xdotool-style names such as `Return`, `Tab`, `super+c`, `Up`, `KP_0` or `PageDown`. Paste formats are `text`, `md` and `html`.
- Observation methods already wait appropriately. Do not add `time.sleep(...)` before them.

## Context and session recovery

After context compression or a task summary, reread this Skill and the relevant reference if those instructions are missing; `gcu.rewrite_documentation()` returns their paths and current configuration without changing bindings or UI. Context compression does not reset Python: reuse surviving bindings and read `get_state(disable_diffing=True)` before acting. Finish background Python work before returning, and follow any `state_reset` notice.

## Shared signatures

<!-- api:shared:start -->
```text
CUA:
  .computer
  .get_app(target, *, window_id=None)
  .get_state(*, emit=True)
  .list_apps(*, emit=True)
  .list_windows(app, *, emit=True)
  .rewrite_documentation()

Target:
  .click(target, *, mouse_button='left', click_count=1)
  .drag(from_, to)
  .get_state(*, screenshot=False, disable_diffing=None, emit=True)
  .perform_secondary_action(element_index, action)
  .scroll(target, direction, pages=None)
  .select_text(element_index, text, *, prefix=None, suffix=None, selection_type='text')
  .set_value(element_index, value)
```
<!-- api:shared:end -->

