# RPA Dev Local Runtime API

This document is the authoritative public contract for the `api` object
injected into generated `src/local-rpa.js` business code. Locator actions and
common option objects are intentionally Puppeteer-like, but this is not a full
Puppeteer or Playwright compatibility wrapper.

Argument forms not listed here are unsupported. Never translate Puppeteer or
Playwright calls by analogy. Before writing or changing an `api.*` call, locate
only that method's section below and verify its exact name, argument order,
types, return value, and timeout semantics. Do not reread unrelated sections.
If a required signature is missing or ambiguous, report the contract gap; do
not inspect private runtime implementation or guess from another framework.

All timeout values are milliseconds. Unless documented below, methods return a
JSON-safe runtime result and reject with a classified error on failure.

## Project isolation and scheduling

Each local project owns an independent browser workspace and blue Tab Group.
Multiple projects may remain connected to the same browser at once. Their API
commands are serialized by the extension, so callers do not need to coordinate
CDP access and one project's selectors, current Tab, Trace, or cleanup cannot
affect another project. Ending a task releases only that project's leased Tabs.

Recording and `api.waitForUserAction(...)` are foreground interactions and are
globally exclusive. While one project is recording or waiting for the user,
another project stays connected but a command that also requires foreground
interaction rejects with `LOCAL_FOREGROUND_BUSY`. Ordinary background API calls
continue to use the same API contract; do not add application-level locks or
share workspace IDs between projects.

## Trace and business errors

```ts
api.step<T>(
  name: string,
  action: () => Promise<T> | T,
  options?: { evidence?: boolean },
): Promise<T>

api.businessError(
  code: string,
  message: string,
  details?: unknown,
): Error
```

`api.step` requires a non-empty business step name and a callable action.
Evidence capture defaults to enabled. Calls nested inside that step still get
Trace rows but share the step's single before/after DOM and screenshot capture.
Throw the value returned by
`api.businessError`; its code must match `[A-Z][A-Z0-9_]{2,63}`.

## Tabs and popups

```ts
api.pages(): Promise<PageSummary[]>
api.switchTab(tabId: number): Promise<PageSummary>
api.closeTab(tabId: number): Promise<unknown>
api.waitForPopup(openerTabId: number, timeoutMs?: number): Promise<PageSummary>
api.clickAndWaitForPopup(selector: string, timeoutMs?: number): Promise<PageSummary>
api.pressAndWaitForPopup(key?: string, timeoutMs?: number): Promise<PageSummary>
```

The default popup timeout is `10000`. These methods operate only on Tabs leased
to the current automation workspace. `pages` marks exactly one leased Tab as
`current`; compare Tab IDs captured before an action when proving that a popup
is new. `switchTab` changes only the background automation target and never
activates a visible browser Tab. `closeTab` rejects for a Tab outside the
workspace. `clickAndWaitForPopup` and `pressAndWaitForPopup` install the popup
observer before dispatching their trusted action, avoiding the usual
action/wait race. The press variant uses the current focused element; use
`locator(...).press()` when the recording identifies the target.
An explicit `waitForPopup` call reserves the next bounded same-window page for
the supplied opener. This also covers modern `target="_blank"` pages that omit
opener metadata; do not keep more than one unrelated popup wait outstanding.

## Navigation, waiting, and inspection

```ts
api.navigate(url: string, timeoutMs?: number): Promise<PageSummary>
api.waitForUrl(pattern: string, timeoutMs?: number): Promise<PageSummary>
api.waitForSelector(
  target: string | LocalLocatorTarget,
  options?: { timeout?: number; visible?: boolean },
): Promise<SelectorInspection>
api.inspectSelector(target: string | LocalLocatorTarget): Promise<SelectorInspection>
api.snapshot(): Promise<PageSnapshot>
api.sleep(durationMs: number): Promise<void>
```

Navigation and selector waits default to `30000`. `waitForUrl` accepts a
wildcard string or a slash-delimited regular-expression string. For
`waitForSelector`, visibility is required unless `options.visible` is exactly
`false`. `navigate` validates an HTTP(S) URL and waits for the leased target to
reach the requested document. `snapshot` returns a bounded page summary, not a
DOM object graph. `sleep` is only a deterministic delay; it does not establish
page readiness. Prefer bounded semantic waits over `sleep`.

`inspectSelector` is the preferred fast probe. It returns `count`, `unique`,
and a bounded `matches` array. Each match includes text, classes, safe
attributes, `rect`, center coordinates, visibility, `obscured`, and the
center-point `hit_target`, plus `selector_suggestions`. An obscured click error
includes the blocking `hit_targets` and suggested recovery actions. Do not run
a complete workflow just to discover these properties. Failed inspection error
details also contain structured `diagnosis` evidence: the failed matching stage, global and
scoped counts, semantic/visible counts, outside-scope matches, bounded loading
evidence, and bounded candidates matching the requested text or accessible name.

## Page interaction and extraction

```ts
type LocalLocatorOptions = {
  scope?: string;
  text?: string;
  exactText?: boolean;
  role?: string;
  name?: string;
  exactName?: boolean;
  visible?: boolean;
  requireUnique?: boolean;
  index?: number;
  near?: { x: number; y: number; maxDistance?: number };
};

api.locator(selector: string, options?: LocalLocatorOptions): {
  click(options?: { clickCount?: number; delay?: number; timeout?: number }): Promise<ClickResult>;
  fill(value: unknown, options?: { strategy?: "fast" | "incremental"; delay?: number; timeout?: number }): Promise<FillResult>;
  type(value: unknown, options?: { delay?: number; timeout?: number }): Promise<TypeResult>;
  press(key: string, options?: { delay?: number; timeout?: number }): Promise<PressResult>;
  wait(options?: { timeout?: number; visible?: boolean }): Promise<SelectorInspection>;
  inspect(): Promise<SelectorInspection>;
};

api.click(target: string | LocalLocatorTarget, options?: { clickCount?: number; delay?: number; timeout?: number }): Promise<ClickResult>
api.fill(target: string | LocalLocatorTarget, value: unknown, options?: { strategy?: "fast" | "incremental"; delay?: number; timeout?: number }): Promise<FillResult>
api.type(target: string | LocalLocatorTarget, value: unknown, options?: { delay?: number; timeout?: number }): Promise<TypeResult>
api.press(key: string, options?: { delay?: number; timeout?: number }): Promise<PressResult>
api.evaluate(expression: string): Promise<unknown>
api.cdp(method: string, params?: Record<string, unknown>): Promise<unknown>
```

`api.locator` is the preferred implementation surface. It binds semantic
identity and recorded geometry once, then exposes familiar `click`, `fill`,
`type`, `wait`, and `inspect` actions. `text` and `name` use contains matching
unless their corresponding `exact*` flag is true. `requireUnique` fails closed
instead of choosing among ambiguous candidates; `near` ranks candidates by
recorded center, and `index` is applied only after all other filters.

`api.click`, `api.fill`, `api.type`, and `api.press` dispatch trusted browser
input while keeping the Tab in the background. Locator actions and their
top-level equivalents share the same implementation; Locator adds target
identity, scope, uniqueness, and geometry rather than a second interaction
engine. `click`, `fill`, and `type` wait up to `5000` ms by default for a target
that is present, visible, and unobscured. Set their action `timeout` explicitly
when a recorded transition has a different bounded readiness window.

`click` evaluates all bounded CSS matches, scrolls when needed, checks five
candidate hit points, rejects disabled targets, and retries only transient
not-found, not-visible, or obscured states. Its result contains only JSON-safe
target and hit-target summaries, never DOM objects, plus
`actionability_attempts` and `page_change` diagnostics. A successful click
means a trusted pointer sequence reached the selected target; it is not by
itself the business completion assertion.

`fill` replaces the current value. For a
contenteditable/Slate editor it uses the Selection API to select the editor contents and
trusted incremental insertion. Use fill strategy `incremental`
when recording evidence shows composition/incremental input is required to drive
autocomplete or other per-input reactions; it still replaces rather than appends.
Both strategies avoid background-tab keyboard shortcuts and duplicate synthetic events.
`type` appends text one character at a time and defaults
to a `25` ms inter-character delay. For an initially empty search, autocomplete,
or live-filter editor whose business behavior depends on per-character insertion,
use `type` even though the recorded edit is technically a replacement. The
recorded before-value, context, and post-input page effect decide this; composition
metadata alone does not imply `fill`. `api.evaluate` accepts a JavaScript expression string, not
a function plus positional arguments, and returns that expression's exact
JSON-safe value. Deep JSON-safe objects are serialized in the page before they
cross CDP, avoiding Chrome's object-reference depth limit. DOM nodes, Window,
framework internals, functions, symbols, BigInt, non-finite numbers, and cyclic
objects fail as `LOCAL_EVALUATE_RESULT_NOT_JSON_SAFE`; map them to the required
text, attributes, rects, IDs, arrays, or plain objects inside the expression.
Use `api.cdp` only when the higher-level Local API cannot
express a required raw Chrome DevTools Protocol operation.
All three interaction methods return verified target-value metadata where
applicable plus a `page_change` summary covering URL/title/dialog-count,
body-length, and interactive-element-count changes. These are diagnostic
signals, not proof that a business search, submission, or send succeeded.
Use `api.fill` for ordinary value replacement and rich-text composer replacement.
Use `api.type` for intentional append and for initially empty search/autocomplete/live-filter
inputs that must preserve per-character trusted side effects. Always bind the input
to its recorded postcondition; a matching editor value alone does not prove that a
search, suggestion, or filter was triggered.

`press` sends a complete Puppeteer-like Chrome key description including
`key`, `code`, virtual key codes, text, location, and a paired key-up. It
supports Enter, Tab, Escape, Backspace, Delete, Insert, navigation keys, Space,
the four modifier keys, F1-F12, and single characters. Top-level `api.press`
uses the current focused element. `locator(...).press()` first resolves and
focuses that target and fails with `LOCAL_SELECTOR_FOCUS_FAILED` if focus cannot
be established before its bounded action timeout. Its result identifies the focused target and reports the exact
key description and page-change diagnostics. When a real,
uncancelled Enter submission targets a new Tab with a GET form, `press` also
adopts the browser-created Tab or recreates the same form URL if Chrome's popup
blocker suppressed it; `opened_page` reports that Tab. This fallback never runs
for same-Tab, POST, AJAX, or `preventDefault()` submissions. Do not replace it with raw
`Input.dispatchKeyEvent` calls.

`evaluate` is for JSON-safe extraction and page inspection, not for synthetic
click/input fallbacks. `cdp` is an explicit escape hatch and returns Chrome's
raw JSON-safe protocol result; prefer a higher-level method whenever one
exists.

In a background workspace, `click` and target-bound Enter also guard ordinary
new-page navigation. Trusted click/key events still reach page handlers, while
uncancelled HTTP(S) `target="_blank"` links, GET forms, and synchronous
`window.open()` calls are opened as inactive leased Tabs. The action result
reports the first one as `opened_page`; `click` additionally reports
`opened_pages`. This prevents a site-created Tab from taking over the user's
foreground browser. Use `clickAndWaitForPopup` when opening a new page is a
required postcondition and the caller wants a bounded failure if none appears.

## Evidence, events, files, and downloads

```ts
api.screenshot(options?: {
  format?: "jpeg" | "png";
  quality?: number;
}): Promise<ScreenshotResult>

api.debugEvents(kind?: string): Promise<DebugEventResult>
api.uploadFiles(selector: string, files: string[]): Promise<UploadResult>
api.waitForDownload(startedAfter?: number, timeoutMs?: number): Promise<DownloadResult>
```

Screenshot format defaults to `jpeg` and quality defaults to `70`. On Windows,
`screenshot` is unavailable when the Workspace is in background mode and fails
immediately with `LOCAL_SCREENSHOT_UNAVAILABLE_IN_BACKGROUND`; use `snapshot`,
`inspectSelector`, or JSON-safe `evaluate` evidence instead. Do not bypass this
guard with `api.cdp('Page.captureScreenshot', ...)`, and do not activate the RPA
Tab as a workaround. Visible recording and explicit human-action modes may
capture screenshots. macOS background screenshot behavior is unchanged.
`screenshot` captures only the current leased target. `debugEvents`
returns bounded runtime console/dialog/network diagnostics and may be filtered
by kind. `uploadFiles` requires a file input selector plus explicit paths and
fails if the target is not a usable file input.
`waitForDownload` defaults `startedAfter` to the call time and its timeout to
`60000`. File paths must be explicit local paths supplied for the task; never
embed credentials or unrelated private paths in generated business code.

## Human action and legacy compatibility

```ts
api.waitForUserAction(message: string, timeoutMs?: number): Promise<unknown>
api.confirmSideEffect(
  kind: string,
  summary: string,
  timeoutMs?: number,
): Promise<unknown>
```

`waitForUserAction` defaults to `300000` and is only for login, CAPTCHA,
passkey, or another human-only step. `confirmSideEffect` is a deprecated,
non-blocking compatibility marker: it immediately returns
`{ continued: true, confirmation_required: false }`. Do not add it to newly
generated code. It remains available so older Skills replay without pausing.

## Common signature mistakes

| Unsupported guessed call | Correct Local call |
| --- | --- |
| `api.waitForSelector(selector, { timeout: 30000 })` | Supported Puppeteer-like Local form |
| `api.waitForSelector(selector, { state: "attached" })` | Unsupported `state`; use `{ timeout: 30000, visible: false }` |
| `api.navigate(url, { waitUntil: "networkidle0" })` | `api.navigate(url, 30000)` |
| `api.evaluate(fn, value)` | Build an explicit expression string and call `api.evaluate(expression)` |
| `api.click(selector, { clickCount: 2 })` | Supported Puppeteer-like Local form |
| `api.type(selector, text, { delay: 25 })` | Supported Puppeteer-like Local form |
| `api.keyboard.press(key)` | `api.press(key)`; this runtime intentionally keeps the established flat name |
| raw `Input.dispatchKeyEvent` | `api.press(key)` or `api.locator(selector).press(key)` |

An options object is valid only where this document explicitly shows one, such
as the third argument of `waitForSelector`, `step` options, or `screenshot`.
