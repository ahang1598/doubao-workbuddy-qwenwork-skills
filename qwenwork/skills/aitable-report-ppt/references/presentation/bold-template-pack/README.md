# Bold Template Pack

This pack brings the `beautiful-html-templates` design systems into the
`frontend-slides` skill without making them the default for every deck.

## What To Read

1. Read `bold-template-pack/selection-index-lite.json` first (13KB, contains only
   matching dimensions). Fall back to the full `selection-index.json` (39KB) only
   when `selection-index-lite.json` does not contain enough information.
2. Shortlist candidates from metadata only:
   - `mood`
   - `tone`
   - `formality`
   - `default_visual_density`
   - `content_capacity`
   - `supported_density_modes`
   - `scheme`
3. For title-slide previews, read only the relevant candidate `preview.md`
   files.
4. After the user chooses a bold template, read exactly that one template's
   full `design.md`.
5. Do not read every `design.md` in the pack.
6. Do not read or copy `template.html` from the source template library unless a
   selected `design.md` is missing a critical implementation detail.

The full source metadata index is not bundled in the user-facing skill. Normal
generation should use `selection-index.json` only.

## Density Fields (schema 2.0)

The old single `density` field is **removed**. It was never defined, and its
values contradicted the templates' own `design.md` on roughly a third of the
pack — Bold Poster was indexed `low` while its design doc calls it
"high — populist and packed"; Monochrome was indexed `high` while its design doc
says "sparse". Selecting a theme by that field produced reports that were both
too sparse and too small.

Two orthogonal axes replace it. They are **not** interchangeable:

| Field | Question it answers | Values |
|---|---|---|
| `default_visual_density` | How full does this theme look by default? | `low` · `medium-low` · `medium` · `medium-high` · `high` |
| `content_capacity` | How much information can it carry while keeping its type sizes and style? | `low` · `medium` · `medium-high` · `high` |
| `supported_density_modes` | Which spec density modes it may be used for | `speaker-led` and/or `reading-first` |

Why two axes: a theme can look airy yet hold dense content. Monochrome is
visually `sparse` but its own design doc states it still holds a 12-row table —
`default_visual_density: low`, `content_capacity: medium`. Soft Editorial states
both in one sentence: "medium-high inside cards, generous between cards."

### Selection rule

- A `reading-first` report **must** pick a theme whose `supported_density_modes`
  includes `reading-first` (equivalently, `content_capacity` is `high` or
  `medium-high`). 13 of the 34 templates qualify.
- A low `default_visual_density` does **not** disqualify a theme from
  `reading-first`. It means the theme's sparse register belongs on cover,
  section, and statement slides, while data slides must use that theme's dense
  layouts. Signal is the worked example: it breathes by default, yet carries
  full-height chart pages when its dense editorial layouts are used.
- Never copy a cover-style sparse composition onto every slide of a
  `reading-first` report.

### Provenance

Each entry carries `density_philosophy_source`, the verbatim label from that
template's `design.md`. Both axes were derived from that paragraph — do not edit
either value without re-reading the source paragraph.

Three templates (Creative Mode, Editorial Tri-Tone, People's Platform) have no
Density philosophy paragraph. They carry `needs_density_audit: true` with null
values rather than guessed ones, and default to `speaker-led` only until a
human audit fills them in.

## How To Use In Frontend Slides

Preview mix:

- 1 safe option from `STYLE_PRESETS.md`
- at least 1 bold option from this pack
- 1 wildcard option, which may be another bold template from this pack or a
  self-generated custom design

Adjust the tone inside that default mix:

- For board, legal, regulatory, healthcare, investor-update, or highly formal
  internal decks, make the safe option very restrained and choose calmer,
  higher-formality bold templates. The wildcard should feel authoritative and
  specific, not merely decorative.
- For bold, editorial, expressive, experimental, or highly designed decks, keep
  the safe option as a readable fallback, choose one strong bold template, and
  use the wildcard for either a second adventurous template or a custom design
  that better matches the user's occasion and vibe.

If the wildcard is custom, it must follow Frontend Slides' no-slop aesthetics:
distinctive typography, a committed palette, a recognizable layout system, a
context-specific visual idea, fixed 16:9 stage behavior, and no visible process
labels such as "custom", "wildcard", "template", or "preview".

## Implementation Contract

`design.md` is the design-system reference. Treat it as a style recipe, not as
content to copy. `preview.md` is only a lightweight style card for generating
the three title-slide options.

Preview slides must be real title slides for the user's deck. Do not render
template names, option labels, file names, paths, `preview.md`, "generated
from", or user requirement notes on the slide itself.

When generating final slides:

- Keep `frontend-slides` output as one self-contained HTML file.
- Include the full contents of `viewport-base.css`.
- Generate every deck as a fixed 1920×1080 stage scaled uniformly to the
  viewport. This applies even if the source template was originally
  viewport-fluid.
- Treat `vw`, `vh`, and `clamp()` values in a source `design.md` as design
  proportions to translate into fixed 1920×1080 stage coordinates.
- Preserve the selected template's fonts, palette, decorative vocabulary,
  spacing rhythm, and component grammar.
- Keep the user's actual slide content primary. The template style should shape
  presentation, not override message or structure.
- Verify rendered output for both text overflow and panel overlap. A card can
  pass `scrollHeight` checks while still being covered by another grid panel.
