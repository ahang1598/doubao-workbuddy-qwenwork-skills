# Essential Kit selection

The visual concept is not a separate abstract direction. It is the combined result of the user's selected palette, logo mark, and typography.

Each generated element remains draft only until the user selects that element. Approved palette, logo, and typography slots persist independently.

## Input analysis

Build options from:

- Brand/product brief
- Audience, positioning, and tone supplied by the user
- User preferences and comments
- Uploaded references, screenshots, logos, fonts, colors, or existing assets

Invite uploads before starting. Ask what the user specifically likes about each reference: palette, typography, composition, shape language, material, or overall aesthetic. If they give no explanation, use the overall character as inspiration without copying distinctive elements.

## Step 1 — Palette options

For every interactive new-identity flow that needs a logo, start here and complete this review before Step 2. Intake phrases such as “pastel,” “blue,” or “warm neutrals” are preferences used to build the options, not a selected palette. Skip this review only when the user supplied an authoritative palette or explicitly selected exact palette colors, or when the user requested auto/no-question mode. In auto/no-question mode, build one exact palette from the brief and call `approve_palette` before Step 2; continue only after the state script confirms success. Never merely describe that palette as locked.

Create 2–3 considered palette options from the brief and references. Each option must include:

- Named flat colors with exact hex values
- Background and text colors
- Optional gradients only when relevant
- One-sentence rationale
- Small usage examples
- 2–3 rough logo mechanism seeds showing what the palette could support

For a new identity that includes a later logo stage, include 2–3 `logo_ideas`. For a palette-only request, set `logo_ideas: []` (or omit it): do not introduce logo concepts or a next-stage logo promise.

Render all options in editable HTML with `<skill dir>/scripts/brandkit.py preview`, then publish them per `inline-widgets.md` (board PNG screenshots shown inline + editable HTML links). Do not generate image-model duplicates and do not send filenames alone.

Every palette review object must set `stage: "palette"`. Omit `display_font`, `body_font`, `logo_svg`, `headline`, and `body`; `logo_ideas` contains 2–3 entries only for a requested logo stage, and is empty for palette-only work. The palette board must not display a typography specimen, placeholder font pairing, or wordmark. Typography appears only after the user selects a logo.

Load `inline-widgets.md`. Render every board locally, screenshot each to PNG, show the PNG, and give the HTML path as the editable file. For 2–3 options, stack the complete option blocks vertically in one message.

After showing the assets, send a normal assistant message:

> Take your time reviewing the palettes. Reply with the option you prefer and any colors you want changed, added, or removed.

Do not use a structured question tool or a multiple-choice list. Wait for the user's ordinary next message.

When the user selects a palette, immediately call the Brandkit state script's `approve_palette` action with that exact palette and the selection message as approval evidence. Continue only if the original request needs another missing slot or output.

## Step 2 — Logo mark options

Enter this step only after Step 1 produced a user-selected and persisted palette, or after an authoritative/explicitly selected palette was already available. Never treat general color preferences from intake as palette selection.

For this entire internal sequence, send at most one short user-facing status: “I’m generating three logo options now.” After it, send no other process/status text until the finished review. Do not mention Design Brain, mechanisms, enhancer prompts, model lookup, generation parameters, or intermediate validation.

Using the selected draft palette plus Brandkit Design Brain:

1. Design Brain returns exactly three original logo mechanisms.
2. Apply `logo-prompt-enhancer.md` once per mechanism to produce its enhanced prompt.
3. Pick one model from `canvas_image_model_list` for the whole set, then submit **one
   `canvas_generate_image` call per candidate** with `count: 1`, `aspect_ratio: "1:1"`, the highest
   supported `resolution`, and its own enhanced prompt. The selected logo colors go **inside the
   prompt** as exact hex with roles — there are no `colors` / `background_color` parameters. Use the
   one, two, or three logo colors the concept needs; never pad to three. Exceed three only when the
   user explicitly requested more.
4. Poll each returned `task_ids` entry with `canvas_get_task` every 3 seconds and use the result
   URLs directly. Do not pass them through the HTML preview script.
5. Show all three per the logo review in `inline-widgets.md`. This review is mandatory in
   interactive and explicit auto/no-question modes; a list of bare URLs is not a review. Results are
   **raster, not SVG** — see `logo.md`.

When interaction is allowed, send a normal message asking the user to review and comment. In explicit auto/no-question mode, do not ask a follow-up question. In interactive mode, do not self-select or start typography before the user responds. In explicit auto/no-question mode, choose the strongest candidate, persist it with the user's auto-mode authorization as approval evidence, and continue only the requested deliverables.

When the user selects a logo, immediately call the Brandkit state script's `approve_logo` action with the exact generated asset (its result URL and id) and name. A logo-only request is complete at this point; typography is not mandatory.

## Step 3 — Typography options

Using Design Brain with the selected draft palette and selected mark:

- Propose 2–3 suitable font pairs.
- Use user-uploaded licensed fonts when supplied; otherwise use verified Google Fonts and include official download links.
- Render the real brand name and short sample copy through `<skill dir>/scripts/brandkit.py preview`.
- Show the selected mark next to each wordmark treatment so type/mark cohesion is visible.
- Use one contrasting `text_color` for both display and body samples; it must not equal the background color.
- Return a visible preview and downloadable HTML. Present both through the typography review in `inline-widgets.md`.

Every typography review object must set `stage: "typography"` and include `display_font`, `body_font`, `logo_svg`, and one shared contrasting `text_color`.

Ask for feedback in a normal message and wait. Do not use a choice list.

When the user selects a type pair, immediately call the Brandkit state script's `approve_typography` action with the exact approved font metadata and specimen.

## Optional combined Essential Kit HTML

Render a combined board only when all three slots are approved and the user requested a full identity/Brandkit or asks to see them together. Otherwise show the available individual review boards. Use `<skill dir>/scripts/brandkit.py preview` with one `stage: "essential"` review containing the approved logo, palette, and type slots.

Publish the returned HTML board per `inline-widgets.md` (inline PNG + full-screen/editable HTML links). This board is a presentation view, not another approval gate. Do not ask the user to approve the system again.

## Continue the original request

Once the slots required by the first-message deliverables are approved, load those output modules and continue. Never force missing unrelated slots or ask the user to choose scope again.
