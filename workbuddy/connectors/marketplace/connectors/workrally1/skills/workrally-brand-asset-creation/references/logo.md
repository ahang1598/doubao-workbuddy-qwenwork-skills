# Logo system

Load this module only when the user asks to create, extend, document, or apply a logo. A request for other branded graphics does not authorize a redesign.

## WorkRally vector limitation (read first)

WorkRally has **no vector/SVG image model**. Every logo generated here is a **raster PNG**, not
editable vector geometry. This changes three things versus a vector-native flow:

- Never promise, imply, or deliver an SVG for a *generated* mark. Never claim "editable vector."
- The deterministic `logo-export` route (recolor, one-color, monochrome, 2048 PNG pair) needs a real
  SVG source, so it applies **only to a user-supplied official SVG**.
- When the user needs true vector output for a new mark, say so up front and offer the honest
  options: use the raster mark as a design reference and have a designer redraw it, or supply their
  own vector source.

Because the mark is raster, ask the model for a **flat, high-contrast, centered symbol on a plain
background at the highest resolution the model offers** so the user has the cleanest possible source
for a later manual trace.

## Route

### Existing official logo

Use the supplied file as authoritative.

1. Analyze source geometry, variants, colors, clear space, and minimum-size guidance from source files/brandbook.
2. Upload once and record the ID in the Brand Lock.
3. Reuse or deterministically place the exact asset.
4. Generate only requested variants/applications.

Never ask an image model to redraw a logo merely to change its background, size, placement, or colorway. Use SVG/PPTX/image compositing when the source supports it.

### Partial logo system

Examples: only a primary logo exists; no monochrome/reverse version, symbol, clear-space rule, or lockup.

- Preserve the primary mark.
- Propose only missing variants.
- Derive variants from source geometry rather than inventing a second style.
- Ask before separating a symbol from a wordmark if the source does not demonstrate that they may be used independently.

### New logo

Run only when explicitly requested.

1. In an interactive new-identity flow, complete the palette review in `concept-boards.md` first. Require a user-selected and persisted palette before generating logo candidates. Color/style preferences from intake are not palette selection. Only explicit auto/no-question mode may select the palette internally; it must call `approve_palette` and receive a successful state response before generating logo candidates.
2. Load `brandkit-design-brain.md` and run `PROPOSE_LOGO_MECHANISMS` with the brief, references, visual axes, and selected palette.
3. Require exactly three distinct symbol-only candidate specifications.
4. Apply `logo-prompt-enhancer.md` exactly once per candidate, building one complete structured candidate input per application.
5. Call `canvas_image_model_list` and pick one model for the whole set — prefer the highest
   `resolution_options` value (6 = 4K) and, when several qualify, the one whose name reads as the
   higher-quality tier rather than the "极速 / lite" tier. Then submit **one `canvas_generate_image`
   call per candidate** with `count: 1`, `aspect_ratio: "1:1"`, the highest supported `resolution`,
   and its own enhanced prompt. Never use `count: 3` to stand in for three distinct prompts, and
   never switch models mid-set.
6. Poll every returned `task_ids` entry with `canvas_get_task` every 3 seconds. Read `output_assets`
   when `state` is 4.
7. Show all three results per the logo review in `inline-widgets.md` in every mode, including
   explicit auto/no-question mode. Then send a normal message inviting the user to review and
   comment when interaction is allowed.
8. When the user selects one, immediately save that exact asset with the Brandkit state script's
   `approve_logo` action. Continue to typography only when the original request requires text/type;
   a logo-only request does not.

## Enhancer contract

For each of the three Design Brain mechanisms, assemble the complete structured candidate input defined in `logo-prompt-enhancer.md`:

```text
{
  brand_context: {
    name,
    offering,
    industry,
    positioning,
    audience,
    values
  },
  visual_axes: {
    restrained_expressive,
    geometric_organic,
    familiar_experimental
  },
  candidate: {
    mark_type,
    central_idea,
    visual_mechanism,
    distinctive_element,
    shape_logic,
    treatment,
    style_register,
    user_style_directive,
    composition
  },
  palette: {
    count,
    user_requested_more_than_three,
    roles
  },
  reference_signals,
  forbidden_elements
}
```

Apply that reference's full contract to produce one enhanced prompt per candidate. Use only that enhanced prompt as the candidate's prompt. Never merge the three enhanced prompts into one request.

`canvas_generate_image` has **no `colors` / `background_color` parameters**, so the locked palette
must be stated inside the prompt. Write the exact hex values in the prompt with their roles, in
Chinese, at the end of the palette clause — for example
`配色锁定：主色 #101820，强调色 #00AEEF，背景 #FFFFFF，只用这三种颜色`. Do not let the color
statement expand into a second concept, and do not add colors that are not in the locked subset.

Set `user_requested_more_than_three: true` only when the user explicitly asks for a logo with more than three colors. Otherwise pass exactly the one, two, or three logo colors the concept requires, even if the broader brand palette contains more. Never add colors merely to reach three.

In explicit auto/no-question mode, score the three candidates for brief fit, distinctiveness, and legibility; select the strongest without opening a question.

## Exactly three comparable candidates

All three must:

- Come from the same model, chosen from `canvas_image_model_list` for this set
- Use the same aspect ratio (`1:1`), resolution, palette statement, and background treatment
- Belong to the selected draft palette and user-defined direction
- Differ in mark construction, not presentation quality
- Stay simple enough that the raster result could later be traced faithfully as vector geometry
- Express one visual concept only; never fuse two metaphors unless the user's own request explicitly described that exact fusion
- Include one concrete distinctive silhouette, negative-space device, motif treatment, or unexpected locked color-role pairing
- Preserve any explicit user-requested style in the candidate and enhanced prompt
- Use one, two, or three logo colors as the concept requires; three is a maximum, not a default, unless the user explicitly requested more
- Avoid generic swooshes, arbitrary initials, stock startup symbols, tiny details, gradients/effects unless concept-critical, and mockup scenes

Typography is selected afterward. Every enhancer prompt must include “no text” in its constraint tail. Monograms may contain only their explicitly requested initials.

If prompt enhancement or the generation call fails, retry once with the same candidate specification. If it fails again, stop and report the error. Do not silently switch to a different model. Select a winner on the user's behalf only in explicit auto/no-question mode.

During typography selection, the mark and wordmark must feel like one lockup:

- Match stroke/weight and corner character
- Balance mark height against cap/x-height
- Use deliberate gap and optical alignment
- Avoid a detailed/heavy mark beside a weak or unrelated wordmark

Never reproduce or cite a reference mark as the target.

## Color revision and optional variant export

### Generated (raster) mark

Approval requires only the selected raster result. Reuse its exact URL everywhere downstream —
`input_images` takes URLs, so no export step is needed to feed mockups or social graphics.

A color-only change on a generated raster mark is **not deterministic**. Say so, then offer the two
honest routes: regenerate that candidate with the palette clause updated (the geometry will shift
slightly), or accept the current colorway. Do not describe a regenerated mark as "the same logo
recolored."

Monochrome/reverse variants of a raster mark are likewise regenerations, not derivatives. Do not
announce, prepare, generate, or save them unless the user explicitly requested them, and disclose
that they are not pixel-identical to the color mark.

### User-supplied official SVG

Only this route is deterministic. When logo files or a confirmed production method require export:

1. Load [exact logo-export payloads](logo-export-payloads.md), then keep the exact supplied SVG as the geometry source.
2. Write `brandkit/logo-export.json`, then run `python3 <skill dir>/scripts/brandkit.py logo-export` with `include_monochrome: false` by default. This creates only the approved color SVG and transparent 2048×2048 PNG.
3. Set `include_monochrome: true` only after an explicit request for monochrome/reverse files or when a user-confirmed output requires one-color production. Then set `primary_color` to the dominant approved source color.
4. Pass `replacements` only for a requested full-color revision.
5. Do not call an image model for a color-only change on an SVG.

The script needs `rsvg-convert` and ImageMagick on PATH for its PNG pair. If either is missing it
stops with an explicit error — install them (`brew install librsvg imagemagick`) or deliver the SVG
alone and say the PNG export did not run.

The script fingerprints every generated variant. Any geometry mismatch is a hard stop. Optional black/white variants are deterministic derivatives of the approved color SVG, not separate concepts or image-model recolors.

For a user-requested solid palette-color/one-color variant, pass that target hex once as `single_color`. Do not reinterpret filled shapes as holes, add masks/knockouts, change fill rules, or convert strokes/paths to preserve contrast. If overlapping paints merge in one color, disclose that outcome; topology changes require separate explicit approval. The script recolors every actual SVG paint automatically and adds the SVG/transparent PNG pair. Never inspect source paints or construct per-fill `replacements` for a monochrome variant.

The script accepts hex, `rgb()`, and `rgba()` paint values and removes a detected full-canvas background. A failed color match reports the available source colors itself. If export still fails, stop and report the exact error. Never inspect or create copies with ad-hoc shell commands, `grep`, `sed`, regex scripts, or manual SVG rewriting.

Exported files stay on the local disk. Push one to WorkRally with `upload_file` (+ `asset_create`)
only when the user wants it in the asset library, or when a later generation step needs it as an
`input_images` URL — and use the PNG for that, never the SVG.

## System deliverables

Produce only requested items:

- Primary horizontal lockup
- Secondary/stacked lockup
- Symbol/monogram
- Wordmark
- Small-size/favicon treatment
- Clear-space diagram
- Minimum-size guidance
- Approved backgrounds
- Incorrect-use examples

## Clear space and minimum size

For an existing identity, copy official rules. If none exist, propose rules and mark them `inferred`:

- Define a repeatable unit `x` from a stable feature (symbol width, cap height, or dominant stroke), not an arbitrary pixel count.
- Apply `x` consistently around each lockup.
- Test at intended digital and print sizes.
- Create a simplified small-size treatment only with user approval; do not silently remove details from the primary mark.

## Output formats

Generated mark:

- Three raster candidates at the highest resolution the chosen model supports
- The approved raster result URL, reused unchanged everywhere downstream
- **No SVG.** Do not promise vector, AI, EPS, Figma, Canva, or PSD.

User-supplied official SVG:

- Full-color SVG and 2048×2048 PNG exports
- Black/white SVG and PNG variants only when explicitly requested or production-required
- PPTX brand-guide pages when requested

SVG wordmarks remain editable text and require the approved font to be installed.

## Logo QA

- Exact spelling and glyph order
- No altered proportions or invented details
- No unintended gradients, shadows, bevels, or effects
- Correct palette and contrast
- Black and white variants exported from a supplied SVG have the exact approved geometry and one solid color
- Exactly three candidates, one generation call each, with identical model and parameters
- A generated mark was never described as SVG, vector, or deterministically recolored
- Selected mark and later wordmark treatment look optically complete together
- Legible silhouette at small size
- Clear-space and minimum-size examples match the actual asset
- Every mockup/template uses the approved anchor, not a regenerated copy
