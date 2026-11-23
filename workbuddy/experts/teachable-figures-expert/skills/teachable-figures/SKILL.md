---
name: teachable-figures
description: Turn lessons, articles, chapters, or technical ideas into interactive teaching figures using predict → try → explain. Create reusable 2D widgets, working isometric SVG objects, mechanical assemblies and cutaways, exploded views, or true 3D turning models when spatial motion explains the concept. Use for explorable learning graphics, mechanism simulations, and mechanical or spatial explainers; retain the host app's lesson contracts and accessibility. Starts with a short guided interview unless the user asks to generate directly. Not for plain data charts, dashboards, slide decks, static illustrations, or whole courses.
---

# Teachable figures

A teachable figure makes one mechanism visible and manipulable. The learner predicts a result, changes a cause, observes its effect, and explains what happened. Place it after the sentence where the claim lands, or give a standalone figure that sentence as its introduction.

This skill fuses the original teaching method with iso-figure's working SVG objects and Anatomy's mechanical geometry, depth ordering, shaders, and optional true 3D runtime. **Teaching determines the model; the subject determines the required shape and material; the model drives the picture and its readouts.** Check both teaching correctness and visual fidelity.

**This skill builds learning exercises and illustrations, not teaching.** Teaching, in the sense of lecturing or presenting an explanation, belongs to the teacher, parent, or text. A figure supports *learning*: scaffolding and sensemaking while the learner predicts, operates, notices, and explains. Design every build for that, and read [learning design](references/learning-design.md) before writing the spec.

**Audience changes the build.**
- **Teacher or parent (presenter).** They already have goals, a sequence, and a knowledge path, and they scaffold live: voiceover, questioning, watching what learners do, directing attention. Default to an **illustration / classroom exercise**: a large legible figure, little embedded explanation, a class prediction prompt, a focus guide the presenter can toggle, and ordered highlights to step through while talking.
- **Solo self-learner.** Nobody else scaffolds, so the artifact must: a short background-knowledge probe first, embedded misconception-specific feedback, fading into independent practice, then transfer.
- **Teach layer, only on request:** an ordered look sequence ("look here → you see this; now look there → …") plus an explanation tied to the learner's existing schema.

**Learner workspace.** When the user's project has a `teachable-figures/` workspace (`LESSONS.md`, `LEARNER.md`, `LEARNING-PLAN.md`), read it **at the start of the session, before asking anything**, and update it after delivery. If it is absent, offer to create it from [the templates](assets/templates/). See [learner workspace](references/learner-workspace.md).

For AI English Shift, first read [the app adapter](references/ai-english-shift.md). Its contracts apply only there. Otherwise inspect the host project's conventions. Paths in this skill are relative to its own directory, including when invoked through a symlink.

## Scope

Use this skill when a learner should **operate** one mechanism: a cause they can change, an effect they can observe, and a prediction that can turn out wrong. Structure-only subjects qualify when inspection, cutaway, or assembly order is the lesson.

Decline or redirect when the request is mainly:

- a data chart, dashboard, or report figure with nothing to predict — use a charting approach;
- a slide deck, poster, infographic, or static illustration;
- a whole course or curriculum — offer one figure per mechanism, chosen with the user;
- an accuracy claim beyond a teaching model: clinical anatomy, engineering simulation, CAD, physics engines, or historical reconstruction presented as fact;
- learning-outcome evidence. A working figure is a design; it has not been tested with learners.

When a request straddles the boundary, say which part this skill covers and build only that part.

## 0. Choose the interaction mode

**Guided mode (default).** First read the learner workspace if one exists; skip every question it already answers. Then ask one compact round of questions — at most five, each with a recommended default the user can accept with one word. Ask only what the request, the workspace, and the host project leave open:

1. **Audience and learner:** presenter (teacher/parent narrating) or self-learner; who the learner or class is; study language.
2. **Claim and misconception:** the sentence to understand and the wrong prediction to disprove. Propose one if the source implies it.
3. **Target:** standalone offline HTML, or an existing app (which framework and lesson schema).
4. **Fidelity:** schematic, recognizable detail, or true 3D — with the renderer you would pick and why (see section 2).
5. **Interaction depth:** the 2–4 controls and the readout you plan to use.

**Self-learner probe.** For a self-learner whose prior knowledge of this topic is unknown, add 2–4 short diagnostic questions in the same round. Each question checks one prerequisite or surfaces one likely misconception. Make them answerable in a word or a choice; one should be a quick prediction. Use the answers to choose the starting point, the amount of scaffolding (experienced learners get less; see expertise reversal in the learning-design guide), and whether a prerequisite needs its own figure first. Record them as evidence, not verdicts.

Then state a short plan — audience build, claim, misconception, `kind`, renderer, controls — and build once the user confirms or adjusts it. If the concept has no place in `LEARNING-PLAN.md`, you may also propose a small knowledge-point subgraph (3–7 points: prerequisites, the target, one or two next points). The user can accept, edit, or skip it; never expand it into a course. Do not ask about facts you can read from the source or the host project; do not ask a second round unless an answer changes the mechanism.

**Direct mode.** Skip the interview when the user says so ("just build it", "skip questions", "直接生成") or the request already names the claim, learner, target, and fidelity. Apply defaults — the workspace's audience and profile if present, otherwise a self-learner build; one figure; standalone offline HTML; the request's language; the simplest renderer that meets the subject's fidelity — and list each assumption, including assumed prior knowledge, in the delivery note so the user can correct it afterward.

## 1. Find the teachable mechanism

Read the source and identify:

- **Claim and anchor:** the precise sentence the learner should understand.
- **Cause and effect:** the input that changes and the observable output it changes.
- **Misconception:** a plausible wrong prediction that operating the figure can disprove.
- **Truth model:** the rule, state transition, equation, or constraints connecting the two. Separate sourced facts from illustrative parameters.

Name the learner's goal and define unfamiliar quantities beside their readouts. For stochastic claims, hold other inputs fixed and distinguish expected distributions from sampled outcomes. One random result cannot disprove a general probability claim.

For a descriptive text, use a process the learner can step through or an assembly whose choices have observable consequences. A structure-only request can use inspection, cutaway, or assembly order; do not invent physical causality just to add a slider. Default to one figure; use two when the text teaches two separable mechanisms.

## 2. Choose mechanism and renderer separately

`kind` describes what is taught. The renderer describes how it is shown. An isometric cache remains a cache model, and a 3D gear train remains a ratio model. Do not replace a working teaching pattern merely to obtain a style.

Before selecting a projection, read [representation and renderer selection](references/rendering-selection.md). Record the subject reference, recognizable landmarks, required material/structural cues, inspection actions, and the actual implementation source. Select an upstream skill by its capabilities, not its name:

- **iso-figure:** functional box-like devices, face-local keys, switches, drawers, and displays. Read [Simple iso](references/simple-iso.md).
- **Anatomy:** crafted rigid mechanisms, connected pipes/joints, real section walls, layered assemblies and mechanical inspection. Read [Mechanical craft](references/mechanical-craft.md), including the upstream craft reference. Its primitive kit is not a medical organ generator or cloth renderer.
- **Organic anatomy or textiles:** obtain suitable reference geometry or author a faithful illustration/mesh, then choose a renderer capable of that shape. Use Anatomy's inspection and craft principles where relevant. Do not turn organs into balls or cloth into boxes to fit a kit. State when and why a custom renderer is needed.

| Mechanism shape | Existing kind vocabulary |
|---|---|
| Setting changes a distribution | `sampler` |
| Text splits into priced units | `tokens` |
| Distance represents similarity | `embedding` |
| Sequence elements attend to others | `attention` |
| Architecture sizes can be changed | `architecture` |
| A curve responds to training choices | `training` |
| A limited container chooses what to retain | `context` |
| Documents are split and retrieved | `chunker` |
| Output passes or fails checks | `validator` |
| Choices combine into an artifact | `builder` |
| A process has steps and failure points | `flow` |
| A loop acts until a stopping condition | `agent` |
| A cutoff trades errors | `threshold` |
| Alternatives trade off across axes | `frontier` |
| Weighted criteria drive a decision | `scorer` |
| Money enters and leaves a system | `economics` |

Spatial mechanisms may justify new kinds such as `assembly`, `kinematics`, `section`, or `spatial`. These are design suggestions, **not pre-registered widgets**. Reuse an existing kind if it already models the concept; otherwise extend the real type, registry, and validation together.

| Rendering mode | Choose when | Read next |
|---|---|---|
| `svg-2d` | Curves, distributions, labels, or a small process show causality clearly | [Teaching and spec](references/teaching-and-spec.md) |
| `iso-lite` | Pressable keys, switches, drawers, or screens can produce useful output with simple box geometry | [Simple iso](references/simple-iso.md) |
| `iso-mechanical` | Supports, joints, springs, pipes, gears, layers, or a cutaway reveal how a mechanism works | [Mechanical craft](references/mechanical-craft.md) |
| `turning-3d` | Rotation, articulation, or changing depth/occlusion is itself part of the explanation | [Spatial and 3D](references/spatial-and-3d.md) |
| Reference mesh renderer | Organic or irregular surfaces need source geometry, smooth lighting and per-pixel depth | [Representation selection](references/rendering-selection.md), [Spatial and 3D](references/spatial-and-3d.md) |
| Optional WebGL layer | Light, fluid, heat, or waves need a field that SVG cannot convey adequately | [Spatial and 3D](references/spatial-and-3d.md), WebGL section |

Choose the simplest renderer that meets **both** the requested fidelity and interaction. A schematic is appropriate when requested or sufficient for the task; a recognizably detailed subject cannot be replaced with a placeholder merely because its controls work. An isometric projection is not proof of true 3D. Explicitly requested 3D or mechanical detail should use the matching mode.

## 3. Write the teaching spec before geometry

Read [teaching-and-spec.md](references/teaching-and-spec.md) for the reusable contract and mapping examples. Preserve the host's existing schema.

- `anchor`: the claim's sentence or segment ID.
- `title`: the question the figure answers.
- `lead`: one line naming the first useful action.
- `predict`: short options, one best `answer`, including the misconception.
- `config`: this text's scenario, parameters, and content.
- `insight`: observed cause → effect, tied to the claim.
- `caveat`: assumptions, illustrative values, and where the analogy stops.
- `frame`: a sentence frame in the requested study language; English in AI English Shift.

Also answer the learning-design checklist in [learning-design.md](references/learning-design.md) §9:
- the audience;
- prior-knowledge assumptions, each with its source (probed / stated / assumed);
- the schema link and the schema change;
- what the predict stage hides;
- a **focus plan** naming the figure parts for each step;
- a **look sequence**, only if a teach layer was requested;
- a **dual-coding map** (term ↔ part ↔ readout);
- the scaffolds and when they fade;
- a feedback map from each wrong answer to its misconception.

For a mechanical or spatial figure, additionally plan the concept-to-part mapping, observable readout, coordinates/units, moving groups and joints, legal ranges, and reset state. These may live in a design note or supported `config`; do not silently add top-level fields to a fixed app schema.

In a design note, name the action and observation that count as a meaningful try, what a satisfactory causal explanation must say, and one new case the learner predicts afterward. Reuse the host's feedback controls; do not impose a hidden reveal lock or change its schema.

## 4. Build from one model

Keep lesson copy in config and the mechanism reusable. Pure model functions determine state, motion targets, readouts, prediction results, and accessible summaries. Geometry and UI observe this state; they do not maintain a second explanation.

For `iso-lite`, use face-local SVG shapes and one projection matrix. For crafted rigid mechanisms supported by Anatomy, use the bundled kit rather than recreating its primitives. For irregular reference meshes or cloth surfaces, use the renderer selected above; do not claim that toolkit provenance supplies domain accuracy. Technical assets are ready to copy under [assets/anatomy](assets/anatomy); lightweight working objects are under [assets/iso-figure/examples](assets/iso-figure/examples).

- Precompute static geometry. Move rigid groups; rebuild geometry only when shape, orientation, or occlusion actually changes.
- Make parts physically legible: supports touch their mounts, shafts share axes, moving parts respect travel limits, and pipes end at ports. Real machines use real relationships; analogies state their mapping and limits.
- Use opaque surfaces and correct depth order. Check assembled, intermediate, and apart states; a convincing final pose does not prove the transition.
- Mechanical detail should help recognition or explanation. Scale density to the lesson; there is no universal minimum part count.
- Establish a recognizable silhouette, characteristic structures, surface curvature and appropriate materials before adding secondary controls. Cutaways reveal thickness and actual interiors; folded cloth has overlapping faces and valleys. A disclaimer does not make a placeholder meet a request for detail.
- Use restrained tones and a focal accent. Keep explanations around the stage; short labels, legends, or paired plots are appropriate when learners need them. Preserve product theme tokens and semantic colors.
- Direct attention instead of showing everything at once. At the predict stage show only what the prediction needs. Mark figure parts with `data-part` and give each panel step `data-focus`, so the shell's focus guide dims the rest. Use `<ol class="look">` for ordered highlights. Link text terms and legends to parts with `data-ref` (dual coding). The API is in [learning-design.md](references/learning-design.md) §8; outside the lesson shell, implement the same behaviour with the host's components.
- In an existing lesson frame, render only the stage. Do not nest another prediction form, caption card, or writing exercise inside it.

Choose standalone HTML/SVG or the host framework. For React, read [the bundled React guide](assets/anatomy/references/react.md), adapting its server/client split to the actual app. Vite React has no automatic server component layer. Do not import Node-only geometry builders into browser code.

## 5. Make it operable as a lesson

Aim for 2–4 teaching controls and a first discovery in under a minute, with extra inspection tools available when useful. Every primary action has pointer/touch and keyboard or native-control equivalents, plus reset. Controls change model state and an observable output; a button that merely jiggles a part is not a teaching action.

Pause/reset are available for time-based models. Stop continuous rendering offscreen and clean up observers, animation frames, and input on unmount. Under reduced motion, show stable states and allow stepping; input must still reveal the mechanism. Do not autoplay a tour that answers the prediction before the learner tries it. An optional demo begins after prediction or on request.

Keep keyboard shortcuts scoped to the focused figure, away from text inputs and lesson writing fields. Use real buttons, sliders with values, and checkboxes. Put an accessible description and textual result beside the visual; throttle live announcements to meaningful state changes. A focusable SVG with `role="img"` alone does not make its controls accessible.

## 6. Verify teaching and visual fidelity

Read [verification.md](references/verification.md). Validate schema, anchors, languages, IDs and registered kinds. Choose the misconception, operate the figure, and confirm its failure is visible. Verify expected model results at reset, endpoints, and meaningful transitions.

Inspect desktop and 360px mobile, the host's supported themes, pointer/keyboard, reduced motion, and reset. Mechanical work adds junction close-ups, contact/clearance and paint-order checks; 3D adds angle/pose coverage and measured performance; WebGL adds fallback and transition checks. Only report checks actually run. A quick or partial audit is not a full audit.

Accept teaching correctness and visual fidelity separately. Check the silhouette and structural landmarks against the subject reference, then inspect material/volume cues and the assembled, intermediate and opened states at useful scale. Controls, numerical tests and zero console errors cannot establish that a torso looks human or pleats look like folded fabric. The [selection guide](references/rendering-selection.md) includes routing cases and visual rejection criteria.

The teaching acceptance check is whether the control changes the answer, the result challenges the misconception, the model states its limits, the first comparison stays small, and the learner can explain a new case.

Deliver the figure/spec/source appropriate to the request and briefly state the claim, useful controls, assumptions, and verification. If a learner workspace exists, update `LESSONS.md`, link the lesson in `LEARNING-PLAN.md` (status `introduced`, never `secure` without learner-produced evidence), and add dated observations to `LEARNER.md`; tell the user what changed. Creating a lesson figure does not authorize changing unrelated product pages or publishing to an external gallery.

## 7. Optional: evolve the artifact from learner evidence

Only when asked to continue a lesson from a learner's record. Read [evolving-artifacts.md](references/evolving-artifacts.md). Treat the exported evidence as observations, write a hypothesis with its uncertainty, and choose one pedagogical action. Express it as a typed patch whose new components read the same truth model and declare executable invariants. Apply it with `scripts/evolve-apply.mjs`, which writes the next version only if validation passes. Never claim to know the learner's mind, and never present a toggle of preauthored content as generation. [The cone pilot](examples/evolve/geometry-slices/) shows one round.

## Resources and provenance

- [Offline example directory](examples/index.html) links fifteen complete bilingual lessons and [how it works](examples/how-it-works.html), a figure that teaches this workflow. All share one two-pane lesson shell: figure and readouts on the left, steps and controls on the right. [Cone sections](examples/geometry-slices.html), [chest anatomy](examples/human-anatomy.html), [seasons](examples/seasons.html) and [Moon phases](examples/moon-phases.html) demonstrate actual 3D rotation, [a four-stroke engine](examples/four-stroke-engine.html) is a 3D Anatomy-kit cutaway, [rocket launch](examples/rocket-launch.html) uses an ideal flight model, [Transformer data flow](examples/transformer-flow.html) exposes toy calculations, and [a Ming robe](examples/chinese-clothing.html) separates historical evidence from schematic construction. [Ship of Theseus](examples/ship-of-theseus.html) shows how a philosophy lesson can teach an argument's structure (competing criteria) without declaring a winner, and [entropy](examples/information-entropy.html) ties an abstract quantity to a countable one (yes/no questions). Read each example's limits before adapting it.
- [Complete gear-ratio lesson](examples/gear-ratio.html) shows prediction, two comparable trials, explanation, and a transfer question in one offline page. It uses a schematic ideal model rather than a tooth-contact solver.
- [Learning design](references/learning-design.md) turns schema theory, scaffolding, cognitive load, signaling, and dual coding into build rules and a spec checklist. [Learner workspace](references/learner-workspace.md) defines the local `LESSONS.md` / `LEARNER.md` / `LEARNING-PLAN.md` files, with [templates, an agent snippet, and a filled sample](assets/templates/).
- [Sources and fusion decisions](references/sources-and-fusion.md) explains what is bundled, licenses, and how conflicting upstream conventions were resolved.
- [Source manifest](references/source-manifest.json) pins the downloaded revisions.
- Read only the selected mode's guides. Upstream technical references provide APIs and geometry recipes; this entrypoint governs the combined teaching workflow.
