# Evolving learning artifacts

A teachable figure is usually generated once. An evolving artifact changes its own structure between learning rounds: it gains a representation, a probe, or a new task, or it loses a scaffold. These changes respond to evidence from the learner. This file is the contract between the artifact, the evidence it exports, and whatever plans and applies the next version.

The contract does not depend on who does the planning. Today the planner is a coding agent in the loop (Claude Code, Codex, or similar): it reads the exported evidence, writes a patch, and runs `scripts/evolve-apply.mjs`. A hosted runtime could fill the same role later by calling a model API, as could a host such as an artifact platform that can ask a model and save new versions. Either one would produce and consume the same evidence and patch formats, and would run the same validation.

Pilot: [`examples/evolve/geometry-slices/`](../examples/evolve/geometry-slices/) (v1 → evidence-1 → patch-1 → v2).

## What counts as evolution

| Change | Kind | Example |
| --- | --- | --- |
| A component that did not exist in the previous version | **structural** | A tile view of r², a numeric table, a new probe |
| A scaffold removed or restored | **structural** (changes what the learner can see or do) | Hide `A = πr²` so the readout cannot be copied |
| A preserved answer or initial value | **value** | Carry the learner's prediction into v2 |
| Moving a slider, opening a hidden `<details>`, or replaying an animation | not evolution | — |

Revealing something that was already authored and hidden in v1 is **adaptation**, not generation. Report it as adaptation. Never describe a preauthored branch as generated.

## Artifact requirements

An evolvable artifact is an ordinary lesson (one truth model; predict → try → explain → transfer). It also adds the following.

- **State block** in `<script type="application/json" id="artifact-state">`:
  - `artifact_id` and `version`.
  - `components`: each component's id, slot, version added, and invariants.
  - `scaffolds`: each one `visible` or `hidden`.
  - `preserved`: answers carried over from earlier versions.
  - `bindings`: maps an answer key to the selector of its input.
  - `validation`: the self-check expression, a control, and sample values.
  - `lineage`.
- **Slots**, given as paired comments. Components are inserted only between these markers:
  ```html
  <!-- evolve:slot figure --> … <!-- /evolve:slot figure -->   (left pane, beside the figure)
  <!-- evolve:slot steps -->  … <!-- /evolve:slot steps -->    (right pane, before transfer)
  <!-- evolve:slot css -->    … <!-- /evolve:slot css -->      (head)
  <!-- evolve:slot script --> … <!-- /evolve:slot script -->   (end of body)
  ```
- **Scaffolds** are marked with `data-scaffold="<id>"`. A hidden scaffold carries the `hidden` attribute.
- **Runtime** exposes `evolve` with these members:
  - `register(id, {render, read, answers})`: `render(state)` runs after every lesson render.
  - `read(id)`: the component's observable values, used by invariants.
  - `log(type, data)`.
  - `evidence()`.
- **Model access:** the lesson's model functions are exposed on `window.lesson`, for example `lesson.derive(h)` and `lesson.selfCheck()`. Components must compute from these, never from their own copy of the math.
- **Continuity:** when `version > 1`, the page says what changed and why, in the learner's language. It restores preserved answers and marks them as carried over.
- **Export:** an "Export learning evidence" control downloads the evidence JSON and can also copy it.

## Evidence (`teachable-figures/evidence@1`)

```json
{
  "schema": "teachable-figures/evidence@1",
  "artifact": { "id": "geometry-slices", "version": 1, "components": [], "scaffolds_visible": ["formula-hint"] },
  "after_change": null,
  "session": { "started": "ISO-8601", "lang": "en", "viewport": "wide" },
  "events": [ { "t": 8420, "type": "prediction", "value": "4" }, { "t": 74210, "type": "explanation", "text": "…" } ],
  "answers": { "prediction": "4", "explanation": "…", "transfer": "3" },
  "privacy": "No name or account. Typed text is kept as typed; audio is never stored."
}
```

- **`events`:** `t` is milliseconds since the page opened. The types are `prediction`, `set`, `trial`, `check`, `explanation`, `transfer`, `probe`, `reset` and `export`; components may add types of their own.
- **`after_change`:** links this evidence to the version change it follows. Use it to fill that change's `outcome`.
- **No personal data:** no names, accounts, IP addresses or device identifiers.
  - Speech input is optional. Only the learner-corrected transcript enters `explanation`; raw audio is never stored or exported.
  - With children, the adult or school decides whether evidence leaves the device at all.
- **Evidence is observation, not understanding.** Interaction counts never mean mastery.

## Patch (`teachable-figures/patch@1`)

```json
{
  "schema": "teachable-figures/patch@1",
  "artifact_id": "geometry-slices", "from_version": 1, "to_version": 2, "created": "2026-11-01",
  "evidence_ref": "evidence-1.json",
  "hypothesis": { "statement": {"zh": "…", "en": "…"}, "confidence": "low | moderate | high",
                  "supporting": ["…"], "against": ["…"], "alternatives": ["…"] },
  "decision": { "action": "…", "expected_signal": "…", "fallback": "…" },
  "preserve": ["prediction", "explanation"],
  "operations": [
    { "op": "add_representation", "target": "slot:figure", "reason": {"zh": "…", "en": "…"},
      "component": { "id": "area-tiles", "markup": "@components/area-tiles.html", "css": "@components/area-tiles.css",
                     "js": "@components/area-tiles.js",
                     "invariants": [ { "id": "…", "description": "…", "expr": "<JS boolean expression>" } ] } },
    { "op": "remove_scaffold", "target": "scaffold:formula-hint", "reason": {"zh": "…", "en": "…"} }
  ]
}
```

- **Component sources:** `markup`, `css` and `js` hold inline text, or `@path` relative to the patch file.
- **Component JS:** runs after the lesson script, wrapped in its own scope. It may use `lesson`, `evolve`, `tr` and `say`.
- **`preserve`:** copies `answers[key]` from the evidence into `state.preserved`. Each key must have a binding.

### Operations

| op | kind | target | implemented in `evolve-apply.mjs` |
| --- | --- | --- | --- |
| `add_representation` | structural | `slot:<name>` | yes |
| `replace_representation` | structural | `slot:<name>` (same component id) | yes |
| `add_layer`, `add_interaction`, `add_probe`, `generate_transfer_task` | structural | `slot:<name>` | yes (same insertion path) |
| `remove_component` | structural | `component:<id>` | yes |
| `remove_scaffold`, `restore_scaffold` | structural | `scaffold:<id>` | yes |
| `set_value` | value | `preserved:<key>` | yes |
| `reconfigure_layout` | structural | — | **not yet** (rejected as unsupported) |

## Validation (all must pass, or nothing is written)

`node scripts/evolve-apply.mjs <artifact.html> <patch.json> <out.html>` applies the patch to a candidate file, then opens the candidate in headless Chrome and checks:

1. **Identity:** the patch schema, artifact id, version continuity (`from == current`, `to == current + 1`), and that the evidence belongs to this version.
2. **The base lesson's own check** (`validation.self_check`, for example `lesson.selfCheck()`).
3. **Every declared invariant of every component**, not only the new ones, at each value in `validation.samples`, driven through the real control.
4. **Preserved answers** appear in their inputs.
5. **Scaffold visibility** matches the state.
6. **No page errors** and **no network requests**, at 1440×900, 1280×720 and 360×800.
7. **Layout:** no horizontal overflow, and every component is laid out within the viewport at those three sizes.

If validation passes, the candidate becomes `<out.html>` and a `<out>.report.json` is written; the report includes the structural diff. If it fails, the candidate is deleted, the previous version stays untouched, the report lists the failing checks, and the exit code is 1. That is the rollback: a version that has not been validated never replaces a valid one.

**Invariants are the hard part.** A generated component is only as trustworthy as its invariants. Each invariant should tie something the learner sees to the shared truth model: printed numbers, drawn counts, answer keys. A component with no invariants passes no check that matters.

## Lineage

`state.lineage` is append-only. Each entry contains:
- `version`, `from` and `created`.
- `why`: the hypothesis statement, bilingual.
- `confidence` and `decision`.
- `operations`: op, kind, target, component and reason.
- `evidence` and `patch`: each a ref plus sha256 prefix.
- `preserved`.
- `outcome`.

`outcome` starts as `null`. When the next evidence arrives (its `after_change` points here), the planner records whether the expected signal appeared before planning further, for example: `{ "evidence_ref": "evidence-2.json", "expected_signal_seen": true, "note": "…" }`.

## Planner procedure (agent or runtime)

1. **Read** the evidence and the artifact state. Note what was visible when each answer was given.
2. **Hypothesize** what the learner seems to think. Include the evidence for and against, an alternative explanation, and a confidence level. Do not claim to know the learner's mind.
3. **Decide** one pedagogical action. Name the signal that would show it worked and the fallback if it doesn't. Prefer a new representation that exposes the mechanism over repeating the same one with more text.
4. **Generate** the component(s). They read the truth model, they are bilingual, and they declare invariants that would catch a plausible-looking error.
5. **Apply and validate** with `evolve-apply.mjs`. On failure, fix the component and rerun. Never weaken an invariant just to pass.
6. **Hand back** the new version with its "what changed" note. When the next evidence arrives, fill in `outcome` first.

## Limits of the current implementation

- **One round in the pilot:** the learner, the evidence and the hypothesis are a scripted example, not data from a real learner.
- **Patching is text insertion into marked slots.** It works for components that live beside the figure. It cannot yet restructure the base figure itself; `reconfigure_layout` is unsupported.
- **Invariant expressions run with `eval` inside the page under test.** Patches are trusted input written by the planner, not by learners.
- **No learner model persists across artifacts.** Each version carries only its own lineage and preserved answers.
