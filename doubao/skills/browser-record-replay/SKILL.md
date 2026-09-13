---
name: browser-record-replay
description: Develop, record, debug, and deliver reusable browser RPA Skills with the browser built into Doubao. Use for same-computer Local Direct workflows only.
---

# Browser Record & Replay · 豆包内置版

This Skill controls the browser built into Doubao on the same computer as the Agent. The browser extension is a client-managed component; never ask the user to install, load, reload, or remove it, and never open the extension manager.

## User-visible reply boundary — applies at every stage

Internal workflow instructions are not a user-facing progress script. Never
turn an internal checklist, planned tool call, document name, command, or
inspection activity into a first-person user update. This applies before and
after recording, while preparing the task description, after confirmation,
and during delivery.

Immediately after recording stops, say only:
**“演示已记录。我正在整理任务说明，现在不需要你操作。”**

While reviewing the demonstration, use only:
**“我正在核对演示中的操作和结果，现在不需要你操作。”**

When the task description is ready, say only:
**“任务说明已整理好。请查看目标、任务入参、自动完成步骤和结果；没有问题请回复‘确认’。”**

Do not say or paraphrase PRD, implementation contract, selector, preflight,
Starter, API document, structure snapshot, evidence inventory, or an internal
review plan to an ordinary user. Ask a user question only for a business choice
or a human-only action such as login, CAPTCHA, authorization, or confirmation.

## Non-negotiable flow

Before requirement intake, recording, implementation, or delivery, read
`references/recording-to-production.md`. It is the Local product contract for
evidence review, task-description confirmation, implementation, semantic
validation, and delivery acceptance.

### Doubao recording handoff

After `local record start` reports both `ui_ready=true` and `sync_ready=true`,
say exactly: **“录制已开始。请按平时的方式完成操作演示。演示结束后先不要关闭浏览器，只回复“完成”。”**
给用户的结束提示词只能是“完成”两个字。不得要求“停止录制”“录制完成”或
“演示完成”，也不得说“直接告诉我停止录制”。用户回复后必须立即运行
`local record stop`，等待所有产物保存成功后，才能评审任务或告知用户可以关闭浏览器。

### Mandatory Windows execution contract

On Windows, before generating or executing any command for this Skill, read
`references/windows-powershell.md` completely. The following rules are
non-negotiable and override shell examples elsewhere in this Skill:

1. Resolve the platform-projected `rpa-dev-local.exe` from `PATH` and invoke
   that native executable with a PowerShell argument array; do not route it
   through Python. Never use inline Python to construct or launch a Windows command.
2. Write JSON and multiline values to UTF-8 files and pass their paths through
   the matching `--*-file` options. Never pass their contents through
   PowerShell command text or a native argument array.
3. Run long-lived commands as detached processes and poll durable output files;
   do not depend on an ephemeral task ID.
4. In a Windows background Workspace, never call `local debug screenshot`,
   `api.screenshot()`, or `api.cdp('Page.captureScreenshot', ...)`. Chromium
   surface capture can remain pending while the blue Tab Group is collapsed
   and block later browser commands. Use recorded screenshots, `api.snapshot()`,
   `api.inspectSelector()`, or JSON-safe `api.evaluate()` results instead.
   Visible recording and an explicit human-only action are the only Windows
   modes where live screenshot capture is allowed. The runtime rejects a
   prohibited call with `LOCAL_SCREENSHOT_UNAVAILABLE_IN_BACKGROUND`; do not
   retry it or activate the RPA Tab as a workaround.

**Highest-priority browser-isolation constraint:** except for visible recording
and an explicit human-only action,
never activate, focus, expand, or bring an RPA Tab or window to the foreground.
This rule overrides exploration convenience and implementation shortcuts.
Keep the blue RPA Tab Group collapsed during task-description work, page exploration,
development, debugging, retries, validation, exported-Skill runs, and delivery.
Use CDP `Emulation.setFocusEmulationEnabled`, idle override, and active
lifecycle emulation when a page needs foreground semantics; never use
`Page.bringToFront`, a foreground workspace option, or real Tab activation.

1. Resolve the platform-projected `rpa-dev-local` executable from `PATH` and set
   `RPA_DEV` to that exact absolute path for each shell invocation. Do not look
   for a binary in this Skill, user data, or another Agent Skill directory.
2. Run `"$RPA_DEV" local setup status`. This is a mandatory environment
   preflight before collecting task inputs or connecting a browser. The CLI selects the current host
   and enforces its minimum version (Doubao 2.28.8; DoubaoWork 2.28.11). Evaluate the version gate before `healthy`: if
   `app_version_gate_code=DOUBAO_VERSION_UNSUPPORTED`, reply with exactly one
   sentence: the CLI's host-specific `user_message` (豆包 or 豆包工作). Then stop
   immediately. Do not ask a question, offer alternatives, mention a dev/test
   environment, or reveal any override or internal diagnostic. Never run bootstrap,
   repair, session start, recording, or a business command after this result.
   If version detection fails (`app_version_detected=false`), keep diagnostics
   and continue without user confirmation or blocking replay. If `ready=true`, reuse the
   current installation.
3. Only when the version gate has passed and the remaining installation is not
   healthy, run `"$RPA_DEV" local bootstrap` once.
   It atomically installs the current platform binary and embedded assets into
   the Doubao user-data stable Runtime and registers the Native Messaging Host.
   Never edit the manifest manually or point it at a session-scoped sandbox path.
4. After bootstrap, wait briefly and retry status. `healthy=true` with
   `ready=false` means the client-managed extension is still reconnecting. If it
   remains unavailable, ask the user to update Doubao to the latest version or
   fully quit and restart Doubao; do not ask them to
   install, reload, or remove the extension. Then run `doctor --mode local` and
   continue only after the real Relay, protocol, capability, and debugger probe succeeds.
5. For an explicit recording request, create a project, start its Local
   session, then start recording immediately. Recording is visible. After it
   stops, all exploration, development, validation, retries, and formal calls
   must stay in the background and must not activate the user's Tabs even
   briefly.
6. Stop recording. Immediately tell the user only: **“演示已记录。我正在整理任务说明，现在不需要你操作。”** Then inspect every required screenshot and normalized business
   step internally. The generated review template includes evidence-bound input
   candidates and any deterministic field proposals. As the semantic field
   author, replace or complete `input_proposals` in a separate `--review-file`:
   every recorded input candidate must have one descriptive snake_case field
   name, a user-facing name, required/default rule, and its recorded-step
   binding. Never use `input_text` or `field_1`. When the field meaning is
   supported by evidence, use the recorded value as the proposed default and
   ask the user to confirm whether it is reasonable. If the evidence cannot
   support a stable field meaning, ask the user
   one consolidated question instead of submitting the review. Use
   `--accept-generated` only when every generated proposal is already semantic
   and complete. Present only the generated task description and wait for
   explicit confirmation before `local intake confirm`. Ask the user only to
   reply **确认**; that reply always applies to the latest user-facing version
   awaiting confirmation. Never expose or ask the user to copy a digest, token,
   hash, version, internal document name, or review plan.
   If the user requests a task-description change after review or confirmation,
   never edit `user-prd.vN.md` in place. Pass the complete revision with
   `--prd-text` or a separate `--prd-file`, call `local intake revise`, complete
   a new review only when the command reports a semantic change, then present
   the new task description and request **确认** once. `local intake revise` also regenerates the matching
   versioned implementation contract; any previously read contract is stale.
7. After confirmation and before opening or editing `src/local-rpa.js`, run
   `local intake contract --project PROJECT` and read the complete returned
   contract. The command also generates `selector-preflight.vN.json` and advisory
   `implementation-starter.vN.js`; it filters redundant/noisy events, keeps
   recorded evidence inline, and fails closed until business assertions are
   implemented. Inspect `selector_preflight_document` first. Never copy a
   `BLOCKED` action; resolve it from the recorded target/ancestor/scope evidence
   and validate the replacement locator. Review `FRAGILE` actions before use.
   The command never overwrites `src/local-rpa.js`. Review the Starter beside the
   contract and copy only verified business logic. Run the contract command
   again after every task-description revision. Implement the smallest workflow that proves
   the confirmed task description; recorded selectors and Starter calls are evidence, not
   production truth. Require semantic identity before choosing among repeated
   candidates. Add bounded waits, explicit postconditions and failure classes,
   multi-Tab handling, and `finally` cleanup.
   On interaction failure, follow the structured runtime diagnosis before
   adding fallbacks: use `recommended_locator` when it matches the recorded
   identity; never remove a modal or mask merely because it appeared in
   `hit_targets`. When an input value matches but its recorded
   search/autocomplete/filter result does not appear, compare the input strategy
   once (`fill` versus `type`) before changing selectors or bypassing the
   recorded path. If `stop_blind_retry=true`, stop full reruns and use the
   reported current-step repair.
   **Local Runtime API contract:** the injected `api` object is the RPA Dev
   Local Runtime API. Its Locator and common options are intentionally
   Puppeteer-like, but it is not a complete Puppeteer or Playwright
   compatibility wrapper. Never infer an unlisted `api.*` signature from
   browser automation experience. Before writing or changing an `api.*` call, read the
   matching method section in `references/local-rpa-api.md` and verify its
   method name, arguments, return value, and timeout semantics; do not reload
   unrelated API sections. Do not pass a
   Puppeteer- or Playwright-style options object unless that exact Local API
   signature explicitly accepts it. If a required signature is absent or
   ambiguous, inspect the injected runner implementation or report the
   contract gap; never guess.
   `api.evaluate(expression)` returns the expression's exact JSON-safe value in
   every Local transport: objects are not decorated and arrays/scalars are not
   wrapped. Return only primitives, arrays, and plain business objects; map DOM
   nodes or framework internals to the required fields inside the expression.
   Prefer it for page extraction; use `api.cdp(...)` only for a raw
   CDP capability. Use `api.click`, `api.fill`, `api.type`, and `api.press` for framework controls because
   they dispatch trusted browser input in background mode. Default to the
   recorded UI path. Direct `api.navigate` is an optional optimization only
   when evidence beyond one recorded URL proves a public, stable,
   parameterized route across representative values. After navigating, assert
   page identity and the requested filter state. Keep a trusted UI fallback;
   never guess a URL pattern or treat one successful recording as stability
   proof.
   For a recorded key action with a stable target, use
   `api.locator(selector, options).press(key)` so the runtime resolves and
   focuses the recorded control before sending a complete key event. Use
   top-level `api.press(key)` only when the current focus is itself proven.
8. Run `local deliver run` with representative real input and an explicit
   semantic result contract. It runs the business RPA once in development and
   once from a source-independent isolated Skill copy. Delivery is
   complete only when both semantic checks pass and cleanup
   leaves no Workspace, leased Tab, debugger attachment, or development Tab
   Group. The neutral directory and archive remain under
   the Doubao user-data directory under `rpa-dev/exports/skills`. The CLI deliberately does not choose or write an
   Agent registry. It returns `delivery_status=ready_for_agent_install`,
   `delivery_complete=false`, and repeats the required installer handoff in
   `install_prompt`, `next_action`, and `agent_action_required`, while also
   emitting a `local_delivery_action_required` progress event. Invoke the
   current Agent's Skill installation capability with the returned artifact,
   confirm that `/<skill-name>` is discoverable, and run the returned
   `usage_prompt`, passing the returned `installation_verification_args`
   (`--cleanup-scope SCOPE`) to `node scripts/run.js` for this installation check.
   Preserve the browser environment throughout development, repair/retry,
   isolated validation, and installed-Skill validation. A failed delivery command
   does not mean the user cancelled the task; do not clean up merely because it failed.
   After installed-Skill validation passes, execute the returned
   `final_browser_cleanup.command` in the installed Skill directory before
   reporting delivery complete. Also attempt this cleanup if the user explicitly
   cancels delivery. If cancellation occurs before export/installation, use the
   `cancel_cleanup_command` from the retained-environment progress event instead.
   Check the receipt: attempting cleanup is required, but an old
   plugin, unreachable browser, or cleanup failure must not invalidate successful
   business validation. Report any skipped/failed cleanup accurately; never rerun
   business actions or restart the browser just to clean up. If continuing repair
   or retry, retain the environment and defer this final step. Never persist these
   temporary validation arguments in the delivered Skill's ordinary usage instructions.
   Do not report delivery complete before installation and validation pass and
   final cleanup has been attempted.

## Core commands

```bash
"$RPA_DEV" local setup status
"$RPA_DEV" local bootstrap
"$RPA_DEV" doctor --mode local
"$RPA_DEV" local app create --dir /absolute/path/to/project --name example
"$RPA_DEV" local session start --project /absolute/path/to/project
"$RPA_DEV" local record start --project /absolute/path/to/project --title "用户演示"
"$RPA_DEV" local record stop --project /absolute/path/to/project
"$RPA_DEV" local intake status --project /absolute/path/to/project
"$RPA_DEV" local intake review --project /absolute/path/to/project --accept-generated
"$RPA_DEV" local intake revise --project /absolute/path/to/project \
  --prd-file /absolute/path/to/revised-prd.md --change-summary "用户确认的修改"
"$RPA_DEV" local intake confirm --project /absolute/path/to/project
"$RPA_DEV" local intake contract --project /absolute/path/to/project
"$RPA_DEV" local run --project /absolute/path/to/project --param-file /absolute/path/to/params.json
"$RPA_DEV" local run --project /absolute/path/to/project --param-file /absolute/path/to/params.json --from-step 3
"$RPA_DEV" local deliver run --project /absolute/path/to/project \
  --skill-name example-local --display-name "示例自动化" \
  --default-prompt '请使用 /example-local，通过豆包AI浏览器完成任务。' \
  --param-file /absolute/path/to/representative-params.json \
  --validated-field validated --result-list-field items
```

`local session start` is idempotent for the same healthy project session: call
it once, and safely reuse the returned session on a repeated invocation. Use
`--replace` only to recover or deliberately change that session. `local run`
is single-flight per project. If it returns `LOCAL_RUN_IN_PROGRESS`, do not
retry or launch another runner; use the reported run ID, start time, and trace
path, then wait for that run to finish. Different projects may still run
concurrently through their independent Workspaces.

`--validated-field` names a top-level field whose value must be the literal
boolean `true` on every run; it defaults to `validated`, must never name an
array, and cannot be the generic field `success`. It must be set only after the
PRD completion invariant passes. `--result-list-field`, when supplied, names a different top-level,
non-empty array. `--default-prompt` must literally contain the exact
`/<skill-name>` reference; when omitted, the CLI generates a valid prompt.
Never copy an exported business Skill directly into a hard-coded Agent
registry. Its runner uses the Agent-neutral runtime installed under
the Doubao user-data directory under `rpa-dev/local-preview/agent-runtime`; it does not discover runtime code
through another Agent's Skill directory.

Use `local intake --help`, `local debug --help`, `local workspace --help`,
`local recording --help`, and `local production --help` for the development
surfaces. `local prd` is only the compatibility path when the user explicitly
declines recording and supplies a complete PRD; never use it to bypass a
recorded unified intake. Meaningful
recorded actions must replay without a side-effect confirmation interruption.
Do not add `api.confirmSideEffect(...)` to new implementations. Older Skills
may still call it, but the runtime treats it as a non-blocking compatibility
marker. Login, CAPTCHA, or a user-only step must call
`api.waitForUserAction(...)`.

## User language

Say **豆包**, **豆包浏览器自动化助手**, **可用**, **使用中**,
**允许使用豆包内置浏览器**, **停止允许使用**, and **结束当前任务**. The extension may show several connected
tasks at once; each project keeps its own blue Tab Group and ordinary browser
operations are scheduled safely. Recording and user-only interaction remain
one-at-a-time foreground work. Do not expose ports, process IDs,
Native Messaging, Bridge, tokens, workspace IDs, or debugger protocol details
unless the user explicitly asks for technical diagnosis.

For ordinary-user replies, state the current progress, whether the user needs
to act, and one next action in that order. Use **任务说明**, **自动完成步骤**,
and **结果核对** instead of PRD, user journey, or implementation/validation
terminology. Do not paste commands, JSON, error codes, internal paths, or raw
diagnostic output. When the assistant is recovering automatically, say it is
“正在恢复浏览器自动化助手，请稍候”; ask the user only for login, CAPTCHA,
explicit authorization, confirmation, or a product action that cannot recover
automatically. Never give the user a first-person checklist of internal review
or implementation work. Give a plain-language conclusion before any technical
detail when the user explicitly requests diagnosis.

### Result presentation contract

When a successful business result contains a collection of records, always
render the actual records as a Markdown table. Use one record per row and the
confirmed business output fields as columns. Do not replace the table with a
bullet list, numbered list, prose summary, raw JSON, or a field-schema list such
as “每条记录包含”. A field definition is not a returned result.

When the result is one structured record with two or more business fields,
render a two-column Markdown table with `字段` and `结果`. Keep URL values
complete and render them as clickable Markdown links when supported. Render
nested scalar lists compactly inside the cell; never expose `success`,
`validated`, traces, IDs, or other internal validation fields as business
columns. A short conclusion may appear before the table and a short result
verification note may appear after it, but the table is mandatory. Only an
actually empty result may omit the table; in that case state that no matching
result was found and give the user-understandable reason instead of inventing
rows.

### After task-description confirmation

After the user replies **确认**, say only: **“任务说明已确认。我正在根据你的演示准备自动化，现在不需要你操作。”** Then perform confirmation and all implementation-preparation commands silently. Never narrate reading or generating internal documents, page-location checks, preparation code, API material, page snapshots, or a `BLOCKED`/`FRAGILE` result. Use one of these user-facing updates instead:

- while checking recorded page operations: **“我正在核对页面操作是否清晰，现在不需要你操作。”**
- when a recorded operation needs more internal analysis: **“有少数页面操作需要进一步核对。我会继续根据你的演示处理，现在不需要你操作。”**
- only when the user must decide something: ask one business-language question about the page action or expected result.

Never output the literal term `PRD` in user-visible text, including replies,
progress updates, status cards, titles, or tool-call narration. Always replace
it with **任务说明**. When describing the implementation basis, say exactly
**“基于录制证据和任务说明”**, never **“基于录制证据和 PRD”**. Internal file
names, commands, and machine-readable fields may continue to use `prd`.

These replacements are presentation-only. Confirmation, evidence checks, implementation contracts, selector safety checks, and API validation remain mandatory internal steps.

## Privacy and Doubao boundary

- Doubao browser data, recordings, screenshots, and Trace stay on this computer.
- Never print or persist passwords, verification codes, cookies, or local
  authentication tokens in a generated business Skill.
- Control only causally leased Tabs in the blue automation Tab Group.
- This package is Local Direct-only. Do not look for or install remote adapters,
  cloud sessions, clusters, proxies, or internal credentials.
- Do not run `local setup uninstall` in the ordinary product flow. The browser
  extension is owned and updated by the Doubao client.

## Shared client distribution

This exact Skill and CLI are shared by Doubao and DoubaoWork through ActionHub. Run from the current host's local task directory. The CLI resolves host identity from platform context, the owning Runtime, task directory, and caller ancestry; never choose based on which applications are installed or running. Only forward RPA_DEV_LOCAL_HOST_ID when supplied by trusted host execution metadata; never invent it to bypass a mismatch. If identity is missing or conflicting, stop and return the CLI guidance. Use the selected host's product name consistently in all messages, including upgrade and restart guidance. Doubao instructions above apply to the selected product; never switch products, data roots, or ports during recovery.

<!-- skill_created_at: 2026-09-12T18:24:28+08:00 -->
