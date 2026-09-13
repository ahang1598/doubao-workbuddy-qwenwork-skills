# Local recording-to-production contract

Read this file before requirement intake, recording, implementation, or
delivery. Local Direct uses the same evidence, PRD, implementation, and
semantic-acceptance standards as the remote browser workflow; only browser
transport and privacy boundaries differ.

## Foreground isolation is the highest constraint

Apart from visible recording and an
explicit human-only action, never activate, focus, expand, or bring an RPA Tab
or window to the foreground. Apply this during evidence review, live-page
exploration, implementation, debugging, retries, development runs, exported
Skill runs, cold starts, and delivery. Prefer recorded structure evidence; when
live inspection is necessary, keep the Tab Group collapsed and use CDP focus,
idle, and lifecycle emulation. Never call `Page.bringToFront` or request a
foreground development workspace. A technique that steals foreground is
invalid even if it makes the business run pass.

## Intake decision

Recording is the default requirement-intake path. If the user explicitly asks
to start recording, create the project, start its Local session, and start the
recorder immediately without asking what should be recorded or inserting a
separate login gate. If recording is explicitly declined, accept only a
complete PRD covering the goal, sites, ordered journey, inputs/defaults,
authentication, Tab behavior, selection rules, outputs, semantic completion,
failure boundaries, and formal invocation expectations.

The compatibility `local prd` commands are only for that complete written-PRD
path. Once a recording creates unified intake state, use `local intake`
exclusively. Never create or confirm a second Local PRD to bypass an unfinished
recording review.

## 豆包内置启动与重连

豆包浏览器自动化助手由豆包作为组件扩展加载。不得打开扩展管理页，不得要求用户启用开发者模式、加载目录或重新加载扩展。先检查 `local setup status`，并要求豆包客户端版本不低于 2.28.8；版本过低时只能原样回复“当前豆包版本过低，请升级豆包至最新版后重试。”并立即停止。不得向用户提问、提供其他继续方式、提及 dev/测试环境、版本覆盖或内部诊断。短暂等待自动恢复后仍不健康时，请用户升级豆包至最新版，或完全退出后重新打开豆包。普通用户没有手动安装步骤。

## 豆包录制交接硬约束

`local record start` 返回 `ui_ready=true` 且 `sync_ready=true` 后，必须原样告诉用户：**“录制已开始。请按平时的方式完成操作演示。演示结束后先不要关闭浏览器，只回复“完成”。”** 给用户的结束提示词只能是“完成”两个字；不得提示“停止录制”“录制完成”“演示完成”或其他口令。用户回复后必须先调用 `local record stop` 并等待产物完整保存，之后才能整理任务说明或开发；保存成功前不得告诉用户可以关闭浏览器。

## Recording and evidence review

`local record stop` downloads all Local artifacts and automatically creates:

- `evidence-inventory.json` from context, normalized steps, userflow, raw
  events, step evidence, screenshots, checkpoints, and both Recorder exports;
- `intent-brief.vN.md/json`, which records inferred business intent and
  alternatives;
- `user-prd.vN.md`, which contains only user-verifiable product behavior;
- `implementation-contract.vN.md/json`, which binds implementation and
  acceptance to recorded evidence;
- `semantic-review.vN.template.json`, which identifies every required business
  step and screenshot.

Post-action evidence and the final checkpoint reference bounded snapshots in
the recording's `structure-snapshots/` directory. A structure snapshot contains
visible interactive controls, bounded semantic landmarks, plus sampled repeated regions such as result
cards. Semantic landmarks preserve visible singleton business evidence such as
headings, labels, identity links, values, metrics, and stable attributed text
that would otherwise be lost because it is neither interactive nor repeated.
Repeated regions preserve the observed DOM count, bounded child-node
structure, direct versus aggregate text, safe attributes, relative selector
candidates, generalized selector patterns proven by multiple sibling items,
field examples, scroll completeness, and links. Step evidence keeps
only `structure_snapshot_path`; intake resolves that reference transparently.
Inline structure snapshots are not part of the recording schema. Use this
evidence first when implementing extraction. Explore the live page only when
the recorded structure is absent, ambiguous, or no longer matches a fresh
semantic assertion.

Immediately after recording stops, tell an ordinary user only:
**“演示已记录。我正在整理任务说明，现在不需要你操作。”** Do not describe
the evidence inventory, internal document, review plan, screenshots, page
structure, or the next command. Then, without another user-facing progress
checklist, read every required normalized step, inspect every required
screenshot at its exact path, and compare the post-action state with the
inferred intent, outputs, completion invariant, Tab graph, and failure
boundaries. The generated review proposal already contains every step and exact
screenshot digest. After inspection, accept it directly:

```bash
"$RPA_DEV" local intake review --project PROJECT --accept-generated
```

Use `--review-file` to override an incorrect inferred intent or completion
invariant **and** to submit the Agent's `input_proposals`. Each proposal must
bind one or more recorded input candidates by `candidate_id`, provide a stable
semantic `name`, a user-facing `display_name`, a required/default rule; treat evidence-backed values as proposed defaults and ask the user to confirm whether they are reasonable, and a
step binding. `input_text`, `input_text_7`, `field_1`, and similar generic
names are invalid. When the field meaning is supported by evidence, treat the
recorded value as the proposed runtime default and ask the user to confirm
whether it is reasonable. If an input candidate cannot be named from the
available evidence, do not submit a generic
fallback: ask the user what it means and whether it is required or has an
explicit default.

The review must cover the current recording digest, every required screenshot
SHA-256, every normalized business step, primary intent, completion invariant,
the task-description change summary, and every input candidate. Evidence gaps
become consolidated task-description questions; they do not authorize silently
weakening the product contract. Confirmation, implementation, replay, delivery,
and isolated validation are blocked until every recorded input has an approved
semantic binding.

Use the inventory as factual evidence, not final product semantics. Recorded
selectors are evidence only. Authentication actions remain trace evidence and
a runtime precondition, but credential input, SSO redirects, CAPTCHA, and login
submission must not become business inputs or replay steps.

## Intent and task-description inference

Infer useful parameters, loops, outputs, and completion semantics from labels,
typed values, URLs, screenshots, post-action state, and the final checkpoint.
Deduplicate parameters by evidence source and business meaning: keep a clear
domain name such as `energy_types`, not both it and a generic `categories`
parameter supported by the same clicks.

Treat repeated click/open/close behavior only as a possible batch-information
candidate. Multiple different clicks alone never create `scope`, `limit`, or a
list output. Infer a collection only when at least two item clicks have
item-bound destination evidence, such as distinct target URLs or post-click
page identity/content that names the clicked item. A document title is fixed
page context, not a runtime `scope` parameter. Generate `limit` only together
with a proven list-output contract. If the clicks may instead be steps in one
operation, keep them as workflow evidence and ask one intent question rather
than inventing collection parameters. A sparse recording must
still infer the strongest safe initial result—normally source URL/title,
visible business summary, selected item identity, and semantic processing
status—instead of ending at `final_url` or claiming that no input exists.

The user-facing task description contains goal, site/context, configurable
inputs, ordered journey, authentication boundary, Tab behavior, selection
rules, outputs, completion, failure boundaries, and material product questions.
It must not expose raw event IDs, selectors, cookies, tokens, internal paths,
or inference confidence. The internal implementation document contains those
technical details. The confirmed task description wins if the two documents
conflict; refresh the internal implementation document before coding.

After successful review, show the user only the clickable **任务说明**, the
complete consolidated question list, and ask them to reply **确认**. Explain it
as the goal, information they can provide, automatic steps, and expected
result; do not expose the internal PRD name or version. Their reply applies to
the latest version currently presented and awaiting confirmation.
Never expose internal digests, tokens, hashes, versioned confirmation strings,
or internal document names. Do not expose the intent analysis or internal
implementation document unless requested.
After explicit confirmation run:

```bash
"$RPA_DEV" local intake confirm --project PROJECT
```

Before that command, tell the user only: **“任务说明已确认。我正在根据你的演示准备自动化，现在不需要你操作。”** After it, obtain and read the implementation contract, preflight, Starter, API sections, and recording evidence without narrating those internal reads. Never say PRD, contract, selector, preflight, Starter, API, structure snapshot, `BLOCKED`, or `FRAGILE` to an ordinary user. If more internal analysis is needed, say: **“有少数页面操作需要进一步核对。我会继续根据你的演示处理，现在不需要你操作。”** Ask a user question only if a business decision or a human-only action is genuinely required.

Never implement or execute business code while unified intake is unconfirmed.

## Task-description revisions after handoff

Never edit a reviewed or confirmed `user-prd.vN.md` in place. When the user
asks for changes, pass the complete revised Markdown directly (or use a
separate `--prd-file`):

```bash
"$RPA_DEV" local intake revise --project PROJECT \
  --prd-file /absolute/path/to/revised-prd.md \
  --change-summary "consolidated user-requested changes"
```

The command creates `user-prd.v(N+1).md`, regenerates
`implementation-contract.v(N+1).md/json`, records the revision chain, and
updates both current digests. Any contract read before the revision is stale.
Editorial revisions reuse the accepted evidence
review; changes to goal, inputs, journey, outputs/completion, authentication,
or failure boundaries return to semantic review. In both cases, present only
the final revised **任务说明** and ask the user to reply **确认**. Do not
ask the user to resolve a digest mismatch caused by the Agent's own edit.

## Implementation contract

Immediately after task-description confirmation and before reading or modifying business
code, run `local intake contract --project PROJECT` and read its complete
returned content. The command acknowledges the exact version and digest. Run
it again after every `local intake revise`; never reuse a prior contract from
memory. The same command generates `implementation-starter.vN.js` and
`selector-preflight.vN.json`. Each
meaningful business action becomes an advisory `api.step()` with parameter
binding and its selector evidence, element fingerprint, rect, screenshot,
structure snapshot path, DOM delta, and recorded postcondition inline.

The site-agnostic preflight grades locator actions as `STABLE`, `CONDITIONAL`,
`FRAGILE`, or `BLOCKED` from uniqueness, selector stability, semantic identity,
actionable/container evidence, ancestor candidates, and a unique scope. Read
the returned `selector_preflight_document` before the Starter. Never copy a
`BLOCKED` action; derive a replacement from its target/ancestor/scope evidence
and validate it with `local debug inspect-selector`. Review every `FRAGILE`
action before use. A task-description revision invalidates this report and the next contract
read regenerates it.

The Starter filters key-up events, redundant focus clicks, and other
non-business recording noise. Unsafe root, positional, non-unique, or
container-like targets remain visible as fail-closed evidence instead of being
silently replayed. Repeated candidates require a unique recorded
identity match; an avatar/icon alone is never identity. The Starter is always
side-by-side evidence and never replaces the project entry. Its result is
fail-closed (`validated=false`) until the implementation adds and passes the
task description's semantic completion checks.

The contract separately reports `action_replay_ready` and
`output_extraction_ready`. For extraction workflows, every required field in
the current task description is mapped to recorded semantic landmarks or
repeated-field evidence. A `candidate` or `missing` required field is an
evidence gap: do not guess a selector or substitute a different recorded field.
The current task description, including a revised version's output table and
completion invariant, is the business fact source even when the original intent
inference disagrees.

Implement `src/local-rpa.js` from the confirmed task description and internal
implementation document. Convert literal demonstration data into typed inputs. Use semantic
locators and fresh-state identity checks, bounded waits, action-specific
postconditions, stable classified errors, and `finally` cleanup. Support the
recorded multi-Tab graph with the Local runtime helpers; control only causally
leased Tabs.

The injected `api` object is the RPA Dev Local Runtime API. Its Locator and
common option shapes are intentionally Puppeteer-like, but it is not a full
Puppeteer or Playwright compatibility wrapper. Before
writing or modifying an `api.*` call, read that method's section in
`local-rpa-api.md` and verify its exact name, argument order, types, return
value, and timeout semantics. Do not load unrelated method sections. Never translate a Puppeteer or Playwright call by analogy, and never
invent an options object that the documented Local signature does not accept.
If the required call is absent or ambiguous, inspect the injected runner
implementation or report the contract gap instead of guessing.

The Local runtime APIs are transport-neutral. `api.evaluate(expression)`
returns the expression's exact JSON-safe value: an object remains that object,
an array remains an array, and a scalar remains a scalar. Transport metadata
must never appear inside business results. Map DOM nodes and framework objects
to the required text, attributes, rects, IDs, arrays, or plain objects inside
the expression; never return raw page objects. Prefer `api.evaluate` for ordinary
page extraction and reserve `api.cdp` for raw protocol capabilities. Use
`api.click`, `api.fill`, and `api.type` for component controls; they dispatch trusted browser
input while keeping the Tab in the background. Replay the recorded UI path by
default. Direct navigation is only an optional optimization when evidence
beyond one recorded URL proves a public, stable, parameterized route across
representative values. It must assert page identity and the requested filter or
pagination state, and retain a trusted UI fallback. Never infer a URL template
from one successful recording, a temporary token, experiment state, or
session-specific URL.

Every successful result must contain machine-checkable semantic evidence. For
an extraction task, return a non-empty result list plus a boolean validation
field after checking required identities, relevance, and required output
fields. For a non-list task, return a boolean validation field and the
business-specific outputs proven by the completion invariant. A non-throwing
click, final URL, or `success=true` alone is not acceptance.

The user-visible presentation is also part of acceptance. A successful result
list must be rendered as a Markdown table with one business record per row and
the confirmed output fields as columns. A single structured result with two or
more business fields must use a two-column `字段` / `结果` table. Never substitute
bullets, prose, raw JSON, or a “每条记录包含” field-definition list for the
actual result rows. Keep complete URL values as links when supported and omit
internal fields such as `success`, `validated`, traces, and runtime IDs. Only a
genuinely empty result may omit the table and explain the empty outcome.

Use `api.waitForUserAction(...)` only for login, CAPTCHA, passkey, or another
human-only step. Do not add side-effect confirmation pauses to generated
business code: the current product priority is uninterrupted replay of the
recorded actions. `api.confirmSideEffect(...)` exists only as a non-blocking
compatibility marker for older generated Skills.

## Fast selector loop

Do not rerun the whole workflow merely to inspect one selector. Keep the
background Workspace and page state, then use `local debug inspect-selector`.
Its result includes match count, every bounded match's text/classes/attributes,
rect and center, visibility, obstruction status, and the center-point hit
target. A failed inspection identifies whether CSS, scope, semantic filtering,
visibility, or page loading is the likely boundary and reports bounded matches
outside the requested scope. `local debug click` returns its actual click point plus before/after URL,
title, dialog count, target survival, and page-change deltas.

For a retained page already positioned after earlier business steps, use
`local run --from-step N` as a development-only shortcut. It skips earlier
`api.step()` blocks; do not use it when later JavaScript variables depend on a
skipped step, and never use it for formal delivery validation.
Failed development runs return `failed_business_step`, `resume_from_step`, and
a copyable `resume_command`; use that command while the retained page state is
still valid instead of restarting navigation.

Execution lifecycle is project-scoped. Repeating `local session start` for the
same healthy project reuses the existing session. Only one `local run` may be
active for that project; `LOCAL_RUN_IN_PROGRESS` is an immediate rejection,
not a signal to retry in parallel. Inspect the error's `run_id`, `started_at`,
and `trace_dir`, and wait for the owner to complete. Runs from other projects
remain independent and may execute concurrently.

## Framework interaction recipes

- React/Vue controls: use `api.locator(css, options).click()` or `api.click`,
  never `element.click()`. Locator options can bind recorded text/name,
  visibility, uniqueness, scope, index, and geometry without page-side helper
  code. The runtime
  dispatches `mouseMoved → mousePressed → mouseReleased` and reports the
  center-point hit target. On `LOCAL_SELECTOR_OBSCURED`, inspect `hit_target`;
  close the proven overlay or choose a visible semantic descendant instead of
  falling back blindly to coordinates.
- Search/dropdown panels: inspect the visible panel container first, then scope
  the item selector under that container. Require one visible match, click it,
  and verify `target_disappeared`, dialog-count change, or a business-visible
  result before continuing.
- Multiple editable regions: scope by a stable recorded context boundary and recorded
  rect/label, validate uniqueness, then use `api.fill` for ordinary replacement. The runtime
  selects the editor contents in the page realm and performs one trusted replacement;
  do not generate Ctrl/Cmd+A, Backspace, raw CDP, or synthetic input-event boilerplate.
  Composition metadata does not select an API by itself. For an initially empty
  search/autocomplete/live-filter control with a recorded result-side effect, the
  starter uses `type(value, { delay: 100 })`; for rich editor replacement it uses
  `fill`, including incremental fill when replacement itself must be observed
  character by character. Treat "value matches but expected result is absent" as
  an input-effect failure and test the recorded input strategy before changing selectors.
- Keyboard submission: when recording evidence identifies the input/editor,
  call `api.locator(selector, identityOptions).press(key)`. Use top-level
  `api.press(key)` only when the current focused element was just proven. Never
  hand-build `Input.dispatchKeyEvent`; the runtime supplies Puppeteer-like key
  codes and text required for native click/form-submit defaults.

## Delivery gate

Use representative real input with `local deliver run`. Declare the result
field that proves validation and, for list-producing tasks, the required
non-empty list field:

```bash
"$RPA_DEV" local deliver run --project PROJECT \
  --skill-name example-local --display-name "示例自动化" \
  --default-prompt '请使用 /example-local，通过豆包AI浏览器完成任务。' \
  --param-file /absolute/path/to/representative-params.json \
  --validated-field validated --result-list-field items
```

The semantic contract is exact: `--validated-field` names a top-level field
whose value is the boolean `true`, never an array, merely truthy value, or the
generic execution field `success`. It defaults to `validated` and may become
true only after the PRD completion invariant is checked. `--result-list-field`, when present, names a different
top-level array that must be non-empty. `--default-prompt` must literally
contain the exact `/<skill-name>` token; omit it to use the valid generated
default. These inputs are validated before any delivery run or promotion.

The gate must prove one development run and one source-independent isolated
Skill run, an immutable PRD-bound Release, portable source-free
output, semantic results on both runs, and complete workspace/Tab/debugger
cleanup. Do not report delivery merely because commands returned without
throwing. A successful command intentionally returns
`delivery_status=ready_for_agent_install`, `delivery_complete=false`, and
`installation.required_before_completion=true`. The output must include a neutral
`artifact_path`, deterministic `archive_path` and digest, `install_prompt`, and
`usage_prompt`. Neither artifact path is an Agent registry. The CLI repeats the
installer handoff in `install_prompt`, `next_action`, and
`agent_action_required`, and emits `local_delivery_action_required` so it
remains visible even when the Skill instructions have fallen out of context.
The Agent must invoke its own Skill installer, verify `/<skill-name>` is
discoverable, and run `usage_prompt` with the returned
`installation_verification_args` (`--cleanup-scope SCOPE`) before reporting
completion. Preserve the browser through development, retries, isolated validation,
and installation validation. Do not treat a failed command as cancellation.
After installation validation succeeds, or the user explicitly cancels delivery,
execute `final_browser_cleanup.command` in the installed Skill directory and check
its receipt. If explicitly cancelled before installation, use the returned
`cancel_cleanup_command` instead. The cleanup attempt is required; cleanup success is optional for
legacy-plugin compatibility. Do not claim cleanup succeeded when it was skipped
or failed, and do not rerun business actions or relaunch the browser for cleanup.
While fixing or retrying, defer cleanup. Keep these temporary validation arguments
out of the delivered Skill's ordinary invocation instructions. The exported runner resolves the stable Runtime installed by bootstrap under `豆包用户数据目录/rpa-dev/local-preview/agent-runtime`; it never resolves runtime code through another Agent's Skill registry.
The CLI emits `local_delivery_stage_started/completed` progress events for each
long-running gate. Report these stages to the user instead of leaving a single
silent command running for several minutes.
