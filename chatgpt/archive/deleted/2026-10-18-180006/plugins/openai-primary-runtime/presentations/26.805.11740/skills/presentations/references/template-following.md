# Template-Following Mode

Use when the user provides an existing PPTX, asks to follow a presentation, or
attaches a PPTX that is clearly or implicitly a template.

This workflow augments the main skill's Shared Workflow Instructions. Continue
to use its Environment, Implementation, Quality Assessment, Deliverables, and
citations requirements. Before authoring, read
`artifact_tool_docs/API_QUICK_START.md`,
`artifact_tool_docs/api/references/master.spec.md`,
`artifact_tool_docs/api/references/layout.spec.md`,
`artifact_tool_docs/api/references/inspect.md`, and
`artifact_tool_docs/api/references/cookbook/imported-deck.md`.

This is the entire template-following mode. Do not run template codegen, do not
build or consume a reusable template registry, and do not rebuild a fresh deck
from palette, fonts, screenshots, or vibes. Use a source slide inventory only:
inspect every source slide, choose source slides for the requested output,
duplicate those source slides, and edit the copied elements in place.

Preserve the source deck's master → layout → slide hierarchy. Edit slides for
one-offs, layouts for repeated changes, and masters only for intentional global
changes. Do not flatten inherited masters or layouts into slide-local overlays.

Store every template-following intermediate named in this reference under
`$TMP_DIR`. Only `FINAL_PPTX` may be written outside `$TMP_DIR`.

## Exact Clone/Edit Contract

1. Copy/import the source PPTX.
2. Inspect every source slide render and layout.
3. Create `template-frame-map.json` mapping every output slide to a source
   slide.
4. Build `template-starter.pptx` by duplicating mapped source slides.
5. Apply the requested edits while preserving the source deck's structure and
   styling.
6. Preserve the source template's typography exactly: keep original font
   family, font size, weight, line spacing, paragraph spacing, text insets,
   alignment, and vertical anchor for every edited text box/table cell unless
   the user explicitly asks to restyle or resize. If new copy does not fit,
   shorten the copy, choose a more suitable source layout, or split content
   across another cloned slide; do not silently shrink text to make it fit.
7. Audit inherited placeholders, including `sldNum`, `dt`, and `ftr`, and
   either fill them intentionally or delete them. Treat visible default prompt
   text such as `Slide Number`, `Date`, and `Footer` as an empty inherited
   placeholder; never leave empty PowerPoint placeholders in the final deck,
   even if PNG renders hide them.
8. Export PNGs, layout JSON, and PPTX for QA.
9. Add or preserve `[Sources]` blocks in speaker notes for externally sourced
   assets and non-trivial claims.
10. Deliver the edited copy using the main skill's citation requirements and
    mention the sources cited or used.

The production load/export path is artifact-tool:

```js
const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePptx));
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(outputPptx);
```

Use artifact-tool and headless package tooling only. If artifact-tool cannot
inspect, duplicate, render, or export the source deck, report the blocker. Do
not fall back to a theme-matched rebuild.

## Source Slide Inventory

Before planning final copy, run:

```bash
node "$SKILL_DIR/template_following_scripts/inspect_template_deck.mjs" \
  --workspace "$TMP_DIR" \
  --pptx "<source.pptx>"
```

Review all source slide PNGs, layout JSON files, `template-inspect.ndjson`,
extracted media, font evidence, and `template-manifest.json`. Do not sample only
one or two representative slides.

Then create under `$TMP_DIR`:

- `template-audit.txt`: source structure, reusable slide types, inherited
  placeholders, brand/assets, typography/spacing rules, and insertion contract.
- `template-frame-map.json`: the full source slide inventory and the selected
  source slide for every output slide.
- `deviation-log.txt`: each intentional departure from a copied source slide,
  with reason and affected slides.

`template-frame-map.json` must include:

```json
{
  "outputSlides": [
    {
      "outputSlide": 1,
      "sourceSlide": 3,
      "narrativeRole": "opening thesis",
      "reuseMode": "duplicate-slide",
      "editTargets": []
    }
  ],
  "omittedSourceSlides": [
    { "sourceSlide": 4, "reason": "appendix pattern not needed" }
  ]
}
```

Every output slide requires a `sourceSlide`. Source slides may be reused multiple
times. If a source slide is omitted from the final narrative, record why in the
audit or frame map.

## Build The Starter Deck

After `template-frame-map.json` is complete, run:

```bash
node "$SKILL_DIR/template_following_scripts/prepare_template_starter_deck.mjs" \
  --workspace "$TMP_DIR" \
  --pptx "<source.pptx>" \
  --map "$TMP_DIR/template-frame-map.json" \
  --out "$TMP_DIR/template-starter.pptx" \
  --preview-dir "$TMP_DIR/template-starter-preview" \
  --layout-dir "$TMP_DIR/template-starter-layout" \
  --contact-sheet "$TMP_DIR/template-starter-contact-sheet.png"
```

The starter deck script calls `validate_template_plan.mjs` to validate
`template-frame-map.json` before duplication. For template-following,
`editTargets` must resolve to inherited source elements with `shapeId`,
`shapeIds`, `sourceElementId`, or `sourceElementIds`.
`action: "add"` is rejected by default because it usually creates new content
over copied placeholders. It also never counts as clearing a placeholder:
every inherited structural placeholder, including empty PowerPoint placeholders
with OOXML `<p:ph>` metadata and no visible text in the rendered PNG, must be
filled through the inherited element or explicitly deleted. If the chosen source
slide lacks usable inherited slots, remap to another source slide or report a
blocker.

Use the starter PPTX as the authoring base. Edit copied placeholders, textboxes,
charts, tables, and images by placeholder or resolved element IDs from
`template-inspect.ndjson` whenever possible. Fill inherited component slots; do
not lay a parallel custom design over the copied template slide.

For mapped source slides, do not use `presentation.slides.add()` to build a new
slide. Import the copied/starter PPTX with artifact-tool, edit the existing
duplicated slides, and export through `PresentationFile.exportPptx`.

If a copied slide cannot be edited cleanly, choose a different source slide and
rerun the starter deck script. If no source slide can support the requested
content, report the blocker and the closest source slide options.

## Edit Rules

`editTargets: []` means preserve-only. Do not add narrative text, charts,
tables, images, panels, callouts, or boxes to that slide unless the validated
frame map explicitly allows a new primitive with a bounded zone and reason. New
primitives must not cover inherited template content.

Brand, logo, bumper, divider, separator, chrome, section, and blank slides are
preserve-only patterns unless the source slide contains inherited content slots
that are explicitly filled or deleted. Do not use the large empty brand side of
a bumper as a canvas just because it has visual whitespace.

## Placeholder Clearing Rules

Default every inherited shape, image, table, chart, layout element, master
element, and text object to `keep`. Only rewrite, clear, or delete an inherited
object when it is explicitly classified as `rewrite`, `replace`, or `delete` in
the slide's `template-frame-map.json` `editTargets` or in a separate edit plan
derived from `template-inspect.ndjson` / layout JSON.

Actual placeholders are structural PowerPoint placeholders, such as elements
with resolved placeholder metadata or OOXML `<p:ph>` entries, and source objects
explicitly marked for editing in the map/edit plan. Visible sample content such
as `Name goes here`, `Title goes here`, `Slide Number`, `Date`, `Footer`, and
template instruction notes may be cleared only when that specific object is
classified as a placeholder or authoring note.

Empty structural placeholders still count. If a copied shape has placeholder
metadata but no text, classify it in the edit plan and handle it with
`rewrite`, `rewrite-and-reposition`, `replace`, `delete`, or
`fill-placeholder`. `keep` and `add` do not satisfy placeholder handling because
PowerPoint can show default edit-mode prompts such as `Click to add title` even
when slide PNG renders look clean.

Do not clear text by broad text heuristics. Never run logic equivalent to
`if (text.trim()) shape.text = ""`, and never blank every text-bearing shape on
a copied slide. OpenAI wordmarks, brand text, page chrome, footers, source rails,
section markers, and master/layout furniture may be editable text objects; keep
them unless the edit plan explicitly says to change or delete that exact object.

For data edits:

- Compute first, design second.
- Show formulas or calculation definitions in notes or appendix when useful.
- Rank and conclude from the computed result, not visual intuition.
- Insert the result into an inherited table/chart/metric frame whenever
  practical.

For media edits:

- Verify identity/source before using headshots or logos.
- Never replace missing logos, app icons, mascots, or product UI with
  hand-drawn lookalikes or pseudo-official marks.
- Normalize crops, background treatment, and image size.
- Do not damage existing slide alignment.

For new real-world subjects, products, screenshots, people, places, events, or
evidence, resolve public or official raster assets and swap them into inherited
frames. Do not generate fake screenshots, fake UI, fake logos, fake product
images, fake evidence, or generated approximations of real entities.

## QA

1. Export slide PNGs, layout JSON, PPTX, and the montage with artifact-tool. The
   canonical presentation artifact export writes per-slide renders and a montage
   by default. Set `montage: false` only if a montage is not useful for this
   run.
2. Review each slide against the mapped source pattern, `content.json` or the
   content plan, and rendered output.
3. Check:
   - hierarchy and primary read,
   - text clipping and overflow,
   - font resolution,
   - chart/table legibility,
   - image crop and mask fidelity,
   - source accuracy,
   - spacing rhythm,
   - slide-to-slide pacing,
   - editable token and asset structure,
   - no blanket text clearing or unplanned deletion of brand chrome, logos,
     footers, page markers, master/layout furniture, or source rails,
   - no unfilled inherited placeholders, including `sldNum`, `dt`, `ftr`, or
     visible default prompt text such as `Slide Number`, `Date`, or `Footer`.
     This placeholder check must inspect the final exported PPTX XML, not only
     rendered PNGs. For every `ppt/slides/slide*.xml`, fail QA if any `<p:sp>`
     containing `<p:ph>` has an empty or whitespace-only text body, unless that
     exact placeholder is intentionally filled or deleted in the edit plan. Do
     not pass this gate by overlaying new text boxes on top of empty
     placeholders.
   - required inherited logos and brand marks are visible in the final exported
     PPTX render. If a required logo from the source template is missing after
     import/export, place the authentic extracted source asset onto the slide
     itself.
4. Before delivery, run:

```bash
node "$SKILL_DIR/template_following_scripts/check_template_fidelity.mjs" \
  --workspace "$TMP_DIR" \
  --starter-pptx "$TMP_DIR/template-starter.pptx" \
  --final-pptx "$FINAL_PPTX" \
  --map "$TMP_DIR/template-frame-map.json" \
  --starter-layout-dir "$TMP_DIR/template-starter-layout" \
  --final-layout-dir "$LAYOUT_DIR/final" \
  --edit-dir "$TMP_DIR"
```

If it fails, fix the map or edit inherited elements directly. Do not switch to
overlays, visual rebuilds, Python PPTX mutation, or direct OOXML mutation.

5. Run one slide-scoped QA review per slide for multi-slide decks, then
   integrate the findings into a final polish pass.
