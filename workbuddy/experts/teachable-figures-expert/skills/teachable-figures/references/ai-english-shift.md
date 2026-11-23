# Teachable figures in AI English Shift

How the method in `SKILL.md` is implemented in this app. Read this before writing or changing a figure here.

## Where things live

| What | Path |
|---|---|
| Spec type, `Text`, `pick()` | `src/explore/types.ts` |
| Frame (predict / reveal / insight / sentence frame / caveat) | `src/explore/Figure.tsx` |
| Shared styles and tokens | `src/explore/explore.css` |
| Widget renderers (one per interaction pattern) | `src/explore/widgets/<Name>.tsx` + `<name>.css` |
| Registry (kind → lazy widget) | `src/explore/registry.ts` |
| Per-lesson specs | `src/explore/specs/<LESSON>.ts`, collected in `specs/index.ts` |
| Lesson text | `src/library/articles.json` (segments `id`, `en`, `ja`); Chinese in `src/academy/zh.json` |
| Validation | `tests/explore.test.mjs`, `tests/explore-behavior.test.mjs` when present |
| Reference implementation | `widgets/Sampler.tsx` + `specs/F05.ts` |

Adding figures to a lesson is almost always **config only**: write `specs/<LESSON>.ts`, add it to `specs/index.ts`. Build a new widget only when no pattern in `SKILL.md` fits.

## The spec contract

Follow `FigureSpec` in `types.ts`. `anchor` is a segment id from `articles.json` — the figure renders directly after that sentence, so it must be the sentence where the claim lands.

All learner-facing copy uses `Text` and supplies `{en, zh, ja, ko}` for lesson specs — all four languages, or the explore test fails. The current TypeScript type permits optional `ko` with an English fallback, but the spec test is stricter. English example content (prompts, tokens, outputs) stays English; it is the reading material.

`config` carries the lesson's **own scenario** (its company, its policy, its numbers), never generic lorem.

## Widget contract

- Default-export a component taking `WidgetProps<Config>`; export the `Config` type. Lesson content lives in config, never in the widget.
- Chrome labels go in a local `Copy` dictionary (en/zh/ja/ko), read through `pick()`.
- Use the shared classes rather than new ones: `ex-controls`, `ex-control` (label > span(name + `<output>`) + `input[type=range]`), `ex-toggle`, `ex-row`, `ex-btn` (`.is-on`), `ex-readouts` (`b` = value), `ex-note`, `ex-pill.ok/.warn/.bad`, `ex-svg`, `ex-num`.
- Tokens from `explore.css`: `--ex-blue` `#343ddd`, `--ex-blue-2`, `--ex-blue-soft`, `--ex-lime` `#ddf76b`, `--ex-ink`, `--ex-muted`, `--ex-line`, `--ex-paper`, `--ex-ok` / `-warn` / `-bad` (+ `-soft`).
- Your widget renders **only the interactive stage**. `Figure.tsx` already renders the title, predict options, reveal/insight, sentence frame textarea and caveat.
- Register the kind in `registry.ts`: `kind: lazy(() => import("./widgets/Name"))`, so a lesson downloads only the figures it uses.

## Checking it here

- `npm test` runs `tests/explore.test.mjs`: anchors exist in `articles.json`, `answer` indexes are in range, every `Text` has all four languages, kinds are registered, ids are unique.
- Inspect the current behavior tests too. They may check control bounds, finite outputs, all four languages, prediction option counts and the sentence-frame blank. Update any fixed fixture count when deliberately adding figures; do not remove the content checks.
- Run the host's production build. A test that loads a widget in Node can pass while a Node-only import breaks its browser bundle.
- Open `/#read/<LESSON>` and play the figure as a skeptical learner: pick the misconception, move the controls, confirm the answer is *visible*. Check at 360px.

## Page integration rules

When work affects this app's landing page, learning map / Concepts, Read sidebar, or video handoff, read [the user journey feedback](ai-english-shift-journey-feedback-2026-09-20.md). It records the user's page responsibilities, layout concerns, Video Sensei handoff requirements, and screenshot evidence.

Keep predict → try → explain inside the lesson experience. The learning map is for exploring concepts and relationships; do not add the figure's writing exercise to map details. Practice on the map and in the notebook is the separate `src/atlas/Practice.tsx` surface, with its own scenarios and self-checks.

These are AI English Shift-specific rules, not restrictions on figures built for other products.

## Isometric, mechanical and 3D stages

The fused skill adds rendering techniques, not pre-installed app widgets. Inspect the current `FigureSpec`, `WidgetProps`, kind field and registry before integrating a new renderer. A mechanism kind and a rendering mode are separate decisions; do not add an unsupported `renderer` top-level field to existing specs. Do not assume `kind` is an enum; it may be a plain string validated against the registry.

- Prefer the current kind and config when the same mechanism is already implemented. A visual replacement must preserve its learning behavior.
- A genuinely new assembly/kinematics/spatial pattern needs its config type, lazy registry entry and matching validation, plus a kind-type change only if the host restricts that field. Merely naming it in a skill does not register it.
- The stage stays inside `Figure.tsx`; do not copy Anatomy's full `Plate` or iso-figure's caption panel if it would duplicate title/predict/reveal/frame/caveat. Supply a stage-local readout for the widget and an accessible description.
- Scope kit styles/tokens to the widget and map them to `--ex-*` theme variables. Do not override `:root`, the whole article, or shared controls. Retain all four chrome languages via `Copy` and `pick()`.
- The explore widgets run in the browser, even when a Next.js shell serves the app. Precompute Node-only geometry at build time to browser-safe data, or use browser-safe geometry modules. A server component recipe cannot be copied into the client widget import chain. Inspect the current runtime boundary before adapting upstream React examples.
- Keep camera/selection/exploded state apart from lesson/model state. Pause a mechanism while apart unless it explicitly remains an inspection display of coupled state.
- Do not run idle tours before prediction. Scope shortcuts to the focused stage so English sentence writing, search and page navigation remain usable. Under reduced motion, native controls still step the mechanism and update its readout.

For implementation recipes read [mechanical-craft.md](mechanical-craft.md) or [spatial-and-3d.md](spatial-and-3d.md), then check the actual app files. This skill update itself does not change application source, register kinds, or publish a page.
