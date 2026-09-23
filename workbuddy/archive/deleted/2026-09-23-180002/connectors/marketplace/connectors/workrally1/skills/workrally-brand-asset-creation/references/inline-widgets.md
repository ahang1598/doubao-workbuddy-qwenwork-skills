# Review boards in a local IDE agent

Every Brandkit review stage is a deterministic HTML board rendered by the bundled script, plus a
PNG the user can actually look at. There are no chat widgets, no reserved upload URLs and no
`media_upload` / `media_confirm` round trip in this environment.

## Publishing a review board

In the brand job's working directory (see `handoff.md`), run:

```bash
python3 <skill dir>/scripts/brandkit.py preview --input brandkit/reviews.json > brandkit/preview-result.json
```

Read each actual HTML path from `files[i].file` in that JSON (`jq -r`); never guess paths. Then
produce a PNG of each board so the user — and your own vision check — can see it:

```bash
npx playwright screenshot --viewport-size=1200,900 --full-page --wait-for-timeout=2000 \
  "file://<actual HTML path>" "brandkit/review-1.png"
```

For typography boards, confirm the intended webfonts actually loaded and inspect the screenshot for
substitution; waiting alone is not proof of font fidelity. A failed or blocked font load requires
correction before review, not approval of a fallback face.

**If Playwright / Chromium is unavailable** (`npm i -g playwright && npx playwright install chromium`
fails, or the machine has no network for Google Fonts), say so plainly and hand over the HTML file
path for the user to open in their own browser. Do not describe an HTML file you never rendered as
if you had seen it, and do not replace the deterministic board with a generated image.

## Whole-artboard SVG previews

An SVG with physical dimensions such as `width="600mm"` renders at about 2268 CSS pixels at 96 dpi.
A smaller browser viewport crops it; setting viewport dimensions does not resize the artwork. For a
complete PNG, rasterize the whole SVG with an explicit output width and preserved aspect ratio (for
example `rsvg-convert --width 1800 --output preview.png artwork.svg`), or scale an inline SVG inside
a fitted HTML wrapper before taking a full-page screenshot. Load or install the approved fonts
before rendering text.

Inspect the resulting PNG, including the right and bottom edges: all copy, arrows, bleed/trim
boundaries and design elements must be visible. Pixel dimensions, SVG metadata, or a successful
screenshot command alone are not visual QA.

## Rules

- Present each option as its board PNG followed by the editable HTML path:

  ```markdown
  ### Option 1 — <name>
  ![<name> board](<absolute local PNG path>)
  Editable HTML: `<absolute local HTML path>`
  ```

- Chat clients that render local images will show the PNG inline; those that do not still get a
  path the user can open. Replace every placeholder with the real path.
- For 2–3 options, repeat the complete block, stacked vertically in one message.
- The PNG is a faithful screenshot of the deterministic HTML board — never a generated image,
  collage, or re-drawn approximation.
- Do not create fake buttons or selection controls. In interactive mode, ask for feedback in normal
  chat after the review and STOP. In explicit auto/no-question mode, show the review without asking,
  persist the chosen slot, and continue.
- Never print filenames without also rendering or attempting to render the associated visual, except
  final brandbook delivery, which intentionally contains only PPTX and PDF links.
- Do not make the user open each file just to understand what it is.

Before writing a preview input, load [exact preview payloads](preview-payloads.md) and copy the
complete shape for that stage.

## Logo candidate review

The HTML preview script does not handle logo creation or comparison. Submit one
`canvas_generate_image` call per candidate, poll each `task_ids` entry with `canvas_get_task` every
3 seconds, and show the three finished candidates together with their labels. Hosts that support
MCP Apps render the generation card automatically; there is no separate display tool to call.

Logo candidates in WorkRally are **raster images, not SVG** — see `logo.md`. Do not offer an SVG
download for a generated mark, and do not claim vector geometry you do not have.

## Logo color-revision/export review

The `logo-export` route only applies to an SVG the user supplied (see `logo.md`). When
`python3 <skill dir>/scripts/brandkit.py logo-export` returns the color pair and any explicitly
requested monochrome/reverse or single-color SVG/2048 PNG pairs:

- With `delivery: "internal"`, show only the selected full-color preview and do not list the
  internal files.
- With `delivery: "user"`, show each PNG and give the path of every returned SVG and PNG variant.
- State that geometry is unchanged and the PNG is a review/export preview.
- Never show only PNG filenames or hide the SVG variants.

Files stay on the local disk. Push one to WorkRally with `upload_file` (+ `asset_create`) only when
the user wants it in the asset library, or when a later generation step needs it as an
`input_images` URL.

## Review messages

After palette review:

> Take your time. Reply with the palette you prefer and any colors you want changed.

After logo review:

> Take your time reviewing the three marks. Reply with the direction you prefer and any shape or
> balance changes.

After typography review:

> Review how each type pair works with the selected mark and palette. Reply with your preferred
> direction or changes.

After showing the combined Essential Kit review:

> Here are your selected logo, palette, and typography together. Tell me if you want to revise an
> element.

In interactive mode, each review message ends the turn. In explicit auto/no-question mode, omit
these questions and persist the selected slot before continuing. The combined kit is a presentation
of existing approvals, not an additional approval gate.
