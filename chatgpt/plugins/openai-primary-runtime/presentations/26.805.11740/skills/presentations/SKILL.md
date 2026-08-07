---
name: Presentations
description: Read, create or edit PowerPoint or Google Slides decks. Use for presentation, slide deck, PowerPoint, PPT, PPTX, or Google Slides requests.
---

## Google Slides Routing

- **Existing native Google Slides deck**: use the Google Drive plugin's Google Slides skill. Do not round-trip through a local PPTX unless the user asks.
- **Net-new native Google Slides deck**: read `routing/google_slides.md`, create and verify a local PPTX with this skill, then import it as a native Google Slides deck.
- **PowerPoint or local deck**: continue with the local workflow below.

## Available Resources

- `style_guidelines.md`: REQUIRED for deck planning, narrative, copy, layout, typography, and visual consistency.
- `routing/google_slides.md`: REQUIRED for every net-new native Google Slides deliverable.
- `references/template-following.md`: REQUIRED when a user-provided PPTX supplies the layout, style, or template.
- `template_following_scripts/`: Inspection, frame-map validation, starter-deck, contact-sheet, and fidelity helpers for template following.
- `builtin_templates_support/`: Guidance, manifests, prompts, and reusable runners for bundled templates.
- `assets/builtin_templates/codex-grid-layout-library/`: Runtime-mounted previews, design tokens, layout registry, and 26 exact plain-JavaScript Codex Grid layout modules.
- `artifact_tool_docs/`: Artifact Tool API documentation and coding examples. Read `artifact_tool_docs/API_QUICK_START.md` first.
- `container_tools/`: Rendering, montage, image, workspace, and overflow helpers.

The following helper scripts are located in the `container_tools/` directory:

- `ensure_raster_image.py`: Ensure images are rasterized; convert to PNG if needed; quick usage `--input_files <img_path1> ...`.
- `render_slides.py`: Render a PowerPoint file into a folder of PNG slides using default sizing; quick usage: `<input.pptx>`. Output files are named `slide-1.png`, `slide-2.png`, ... in a directory with the same name as the input file.
- `create_montage.py`: Build a tiled montage from images in a directory (for viewing multiple image assets or rendered slides at once); quick usage: `--input_dir <imgs_dir> --output_file <montage.png>`. It supports most image formats with auto conversion under the hood.
- `slides_test.py`: Detect content overflowing the original slide canvas; usage: `<input.pptx>`.

## Visual Workflow Routing

For every local PPTX workflow, choose exactly one visual route. The first matching route wins:

1. **User-provided PPTX, reference deck, or template**: treat an existing PPTX being edited as the visual source too. Read `references/template-following.md`, inspect every source slide, duplicate selected source slides, and edit inherited elements in place. Do not mix in Codex Grid or another template.
2. **Explicit custom visual direction without a reference deck**: create the deck from scratch using the requested theme, brand treatment, mood, or formatting. Do not use Codex Grid.
3. **No visual direction**: use the bundled Codex Grid layout library as the default composition reference. Before planning, read `builtin_templates_support/codex-grid-layout-library/ARTIFACT.md`, `assets/builtin_templates/codex-grid-layout-library/design_tokens.json`, and `assets/builtin_templates/codex-grid-layout-library/artifact-tool-compose/template-registry.json`; inspect `assets/builtin_templates/codex-grid-layout-library/assets/previews/layout-library.png`; then open only the shortlisted exact layout modules. Preserve each selected layout's hierarchy and media frames while replacing sample content, and vary adjacent silhouettes.

The shared `builtin_templates_support/scripts/create-presentation.mjs` runner materializes all 26 layouts for validation; it is not a request to emit all 26 layouts in the user's deck. User-provided references and explicit visual direction always override Codex Grid.

## Important Instructions

- [HARD REQUIREMENT] Audience-facing copy: visible slide content must be written for the intended audience, not for the person or model producing the deck. Do not expose planning notes, timing scaffolds, talk tracks, content-selection commentary, or other internal process language unless the user explicitly requests it.
- Include [Sources] blocks in the speaker notes for every externally sourced asset and every externally sourced non-trivial claim.
- Info density: avoid cramming low-value details onto a single slide. Prefer lower-density slides with high-value content.
  - Title slide: keep the title slide minimal and simple. Avoid cramming in too much information.
- Layout: keep things clean and simple. Avoid low-quality visuals, but also avoid excessive white space. By default, use equal left and right margins on each slide.
- [HARD REQUIREMENT] Overlap: always pay attention to programmatic overlap warnings. Do not assume that overlapping elements in diagrams are intentional, and do not ignore overlap warnings without inspecting them. You MUST fix all unintended overlap errors before delivering the slides. This is critical.
- [HARD REQUIREMENT] Font size: when a template is provided, match its font sizes. When no template or style guidance is given, you MUST use at least 50pt for deck titles, 35pt for slide titles, 24pt for mid-level text such as subheadings, callout headers, and text-box titles, and 16pt for body text.
- Text layout: when there is too much text, shorten it before shrinking the font size. Inspect visually for unexpected text wrapping. NEVER allow a title/banner text box intended for one line to wrap to two lines.
- Narrative copy must fit the chosen layout: shorten it or change layouts rather than adding density or shrinking type.
- Visual assets:
  - [HARD REQUIREMENT] DO NOT use Python to draw images; DO NOT use programmatic vector shapes for visuals; DO NOT use programmatic drawings of any sort. Use image search or image_gen tool instead!
  - [HARD REQUIREMENT] Minimize the use of diagrams. Add them only when requested or when a single diagram materially improves the clarity of complex concepts. Diagram implementation rules: use native PowerPoint shapes for simple diagrams; use Graphviz for complex relational/topological/network-like diagrams; use image_gen for highly aesthetic, illustrative, or scientific infographic diagrams (e.g. chemical structures, circuit diagrams, etc.). When using native PowerPoint shapes with connectors, create connectors (arrows/edges) before creating entity nodes, so edges appear behind nodes and never cross through node shapes or labels. If this ordering is awkward during early iteration, you may create nodes first in the initial draft, then switch to connectors-first in the revised code.
  - Before sourcing or generating visuals, be mindful of the desired aspect ratio, placement, and cropping options on the slide. For example, if you intend to place text to the left of the image containing a person, you should ask image_gen to put the person on the right side of the image.
  - By default, DO NOT reuse the same image more than once (unless it's a background).
  - Prepare visuals for both the main concept and decorative support.
  - Inspect final image crops at full-slide size and replace assets that are blurry, distorted, poorly framed, or visually inconsistent with the deck.
  - Keep diagram labels concise, maintain clear hierarchy, and use consistent connector semantics.
- Default styling: use one composition instead of a collection of UI panels. UI-like styling typically includes card grids, pills, badges, button-like text boxes, tab or navigation patterns, repeated modular panels, dense dashboard-style layouts, and other component-library aesthetics that imply interactivity. Use stylized text boxes sparingly, favoring a flat structure on the canvas.

## Shared Workflow Instructions

### Planning

- Apply `style_guidelines.md` to define the communication job, narrative arc, slide sequence, and visual approach.
- Apply the selected visual route above. Treat user-provided images as content, reusable assets, and explicit visual constraints without weakening a source deck's template contract.
- For existing or template-based decks, preserve the master → layout → slide hierarchy instead of flattening inherited elements. Discover masters and layouts with `presentation.inspect({ kind: "layout" })` (`type: "master"` identifies masters); inspect full master state through `presentation.masters.items`, `master.elements`, `master.placeholders.summary()`, and `master.toProto()`. Find child layouts by `parentLayoutId`, reuse them with `slide.setLayout(layout)`, and fill slide placeholders locally. Edit slides for one-offs, layouts for repeated changes, and masters only for intentional global changes; render representative descendant slides afterward. Read `artifact_tool_docs/api/references/master.spec.md`, `artifact_tool_docs/api/references/layout.spec.md`, `artifact_tool_docs/api/references/inspect.md`, and `artifact_tool_docs/api/references/cookbook/imported-deck.md`.
- Keep source and asset provenance in `$TMP_DIR/source-notes.txt`.

### Environment

Work in a writable, conversation-specific or tmp directory. Follow any working-directory and output-path instructions supplied by Codex.

Set:

- `SKILL_DIR=<absolute path to this skill>`
- `TMP_DIR=<absolute path to a temporary build directory within the working directory>`
- `FINAL_PPTX=<absolute path to the final .pptx>`

An explicit user destination always wins. Otherwise, place `FINAL_PPTX` in the host-preferred output location. Use absolute paths in scripts and handoffs. Put intermediate files under `$TMP_DIR` and only final deliverables at the output location.

Use `.txt` for generated intermediate prose in `$TMP_DIR`, including plans, source notes, prompt records, design notes, QA ledgers, and fallback reasons. Reserve `.md` for installed skill resources. Do not create generated planning files such as `slide-plan.md`.

### Implementation

You MUST use `@oai/artifact-tool` from JavaScript ES modules to implement the slide deck.

Read the local docs before coding:

- `artifact_tool_docs/API_QUICK_START.md`
- `artifact_tool_docs/api/API_DOCS.md`

Create an ES module source file (`.mjs`) under `$TMP_DIR` and export the final PowerPoint deck (`.pptx`) to `$FINAL_PPTX`. Do not leave TypeScript-only syntax such as type annotations, `type` declarations, or `interface` declarations in the submitted `.mjs` source.

You MUST NOT use `python-pptx` or the old Python `artifact_tool` API.

Initialize the workspace before running a generated presentation module:

```bash
node "$SKILL_DIR/container_tools/setup_artifact_tool_workspace.mjs" \
  --workspace "$TMP_DIR"
```

### Quality Assessment

Before delivery:

1. Render every final slide.
2. Inspect each slide individually at full size; use a contact sheet only for deck-level flow and consistency.
3. Fix unintended overlap, clipping, wrapping, broken connectors, unresolved placeholders, inconsistent footers or page markers, and chart/data mismatches.
4. Confirm the deck satisfies the user request and the narrative remains coherent.
5. Verify researched claims and sourced assets are traceable and cite sources when research informed the deck.

### Deliverables

Return a short user-visible summary of the completed deck. Mention sources cited or used when research informed the deck. Do not attach scratch plans, previews, layout JSON, or temporary assets unless the user asks.

#### Citations format

Place :codex-file-citation{...} inline in prose without wrapping it in backticks or a code block, not in a trailing list. Use `purpose="source"` for Q&A/no-op and `purpose="output"` for create/edit.

- [HARD REQUIREMENT] Create/edit: cite each final deck exactly once with a plain output citation. Summarize representative changes; do not cite every slide or add a separate filename, path, or Markdown link. Example: `Created :codex-file-citation{path="/abs/path/launch-plan.pptx" purpose="output"}, highlighting the rollout and owners.`
- Q&A: inspect the complete relevant slide, including callouts, question wording, chart/table titles, totals/sample sizes, and source/methodology footers. Answer directly, group same-slide claims, and cite that slide once. For concrete chart/table/image/diagram/callout evidence, include exact inspected `slide_id`, `object_id`, and a useful label when available.

For non-in-place edits, preserve the source and export a copy; if unchanged, cite the source plainly.

Use only locators verified against the latest render/inspection:

:codex-file-citation{path="/abs/path/deck.pptx" purpose="source" artifact_kind="presentation" slide_number="3"}
:codex-file-citation{path="/abs/path/deck.pptx" purpose="source" artifact_kind="presentation" slide_number="1" slide_id="sl/gs5z1kshq0xv" object_id="ch/pz9t1r3ka8vn" label="ARR by segment chart"}

If IDs are not exact, stop at `slide_number`; never guess or cite intermediates unless asked.
