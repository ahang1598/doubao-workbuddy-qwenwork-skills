---
name: pptx
version: 2.3.1
description: "Use this skill any time a PowerPoint .pptx or legacy .ppt file is involved as input, output, or both. This includes creating decks; reading or extracting slide content; editing presentations; combining or splitting slides; and working with templates, layouts, speaker notes, comments, charts, actions, or fonts. Trigger whenever the user mentions a deck, slides, presentation, PPT, or a .ppt/.pptx filename. Normalize legacy .ppt input before using PPTX workflows."
description_zh: "当 .pptx 文件以任何方式涉及时使用此技能——无论是作为输入、输出还是两者兼有。包括：创建幻灯片、演示文稿或路演材料；读取、解析或提取任何 .pptx 文件中的文本（即使提取的内容将用于其他地方，如邮件或摘要）；编辑、修改或更新现有演示文稿；合并或拆分幻灯片文件；使用模板、布局、演讲者备注或批注。当用户提及\"幻灯片\"、\"演示文稿\"、\"PPT\"或引用 .pptx 文件名时触发，无论他们计划如何使用内容。只要需要打开、创建或操作 .pptx 文件，就使用此技能。"
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX Skill

## Quick Reference

| Task | Guide |
|------|-------|
| Normalize legacy `.ppt` | Read [references/legacy-ppt.md](references/legacy-ppt.md); use `scripts/prepare_legacy_ppt.py` before any PPTX tool |
| Read/analyze content | `python scripts/inspect_pptx.py presentation.pptx --pretty`; use `python -m markitdown presentation.pptx` when a prose dump is useful |
| Edit or create from template | Read [editing.md](editing.md) |
| Create from scratch | Read [from_scratch.md](from_scratch.md) |
| Authoring scars (any mode that adds shapes/text/images) | Read [authoring.md](authoring.md) |
| Pick a theme (when no template fits) | Read [themes.md](themes.md) — index of 7 archetypes; per-theme details in `themes/` |
| Slot geometry for slide composition | Read [layouts.md](layouts.md) |
| Hard visual shapes (gantt, swot, funnel, …) | Read [components.md](components.md) — when to use each + content schema |
| Native/complex PowerPoint charts or an existing pptxgenjs generator | Read [pptxgenjs.md](pptxgenjs.md); keep the same final QA gates |
| Fetch real photos for slides | Read [from_scratch.md § Fetching real photos](from_scratch.md#fetching-real-photos) — use an image capability available in the current host and embed a local copy |
| Parallel PPT authoring and generated images | Read [references/bounded-foreground-fork-join.md](references/bounded-foreground-fork-join.md) — adaptive foreground forks, priority waves, evidence-based recovery, deterministic join |
| Fetch a brand / website logo | `from scripts.get_logo import fetch_logo` — pulls the real mark from the site's own servers (China-reachable; no Clearbit / Google s2 / Brandfetch). Never fake a logo from shapes — degrade to plain text on failure. |

---

## Execution Policy

Call the bundled semantic entry points directly and let them select a validated
execution path. Do not begin with broad environment, credential, CLI, font, or
package inventories.

| Need | Entry point |
|---|---|
| Inspect | `python scripts/inspect_pptx.py presentation.pptx --pretty` |
| Validate | `python scripts/validate_pptx.py presentation.pptx --pretty` |
| Render overview | `python scripts/thumbnail.py presentation.pptx "$PPTX_TEMP_DIR/overview"` |
| Edit package safely | `python scripts/edit_package.py unpack ...`; edit; `python scripts/edit_package.py pack ... --original ...` |
| Run deterministic QA | `python scripts/qa_pptx.py output.pptx --pretty`; add `--original template.pptx` for template-derived work |
| Normalize legacy input | `python scripts/prepare_legacy_ppt.py ...` |

### Task temporary workspace

Before running any authoring, conversion, rendering, inspection, or QA command
that creates files, create one fresh host-managed temporary directory for the
current task and record its absolute path as `PPTX_TEMP_DIR`. Keep it outside
the caller's output directory.

- Write build scripts, draft decks, unpacked OOXML, generated assets, converted
  PDFs, slide renders, contact sheets, and QA logs under `PPTX_TEMP_DIR`.
- Pass an explicit path under `PPTX_TEMP_DIR` to tools that accept an output
  path; do not rely on their current-directory defaults for intermediate files.
- Put only the final `.pptx` and artifacts the user explicitly asked to retain
  in the host-designated output directory (for example, `outputs/`).
- Treat `work/...` paths shown in supporting references as logical task-work
  paths and resolve them under `PPTX_TEMP_DIR`.
- Do not make successful delivery depend on deleting `PPTX_TEMP_DIR`. Leave it
  to the host or operating system lifecycle unless the host already provides a
  finalizer. Never move, overwrite, or delete caller-supplied files.

- Keep successful capability checks silent. Do not narrate credential names,
  installed packages, executable names, or backend routing.
- Surface only a blocker or choice that requires user action, phrased in task
  terms such as “editable conversion is unavailable” or “visual preview is
  unavailable.” Never print credential values.
- Allow one validated fallback for a recoverable capability failure; do not
  loop between routes. A failed preferred route does not end the task when a
  trusted alternative can still complete it.
- Invalid or corrupt input and unsupported caller parameters are terminal.
- Keep editable authoring and the final structural/package gates intact on
  every route.

---

## Legacy `.ppt` normalization

Legacy `.ppt` is a binary OLE format, not an OOXML package. Before inspection,
editing, rendering, or QA, read
[references/legacy-ppt.md](references/legacy-ppt.md) and run exactly one
normalization route:

- For visible content, appearance, OCR, summary, or another read-only result,
  convert once to PDF with `scripts/prepare_legacy_ppt.py --to pdf`.
- For editing, original font names, hyperlinks/actions, native charts,
  animations, or OOXML inspection, convert once to editable PPTX with
  `scripts/prepare_legacy_ppt.py --to pptx`.
- Let the script perform bounded capability selection and fallback. A preferred
  route ending does not end the user task; follow the bounded discovery rules
  in the reference, validate any alternative result, and only then request a
  `.pptx` source.
- Do not unzip `.ppt`, scan raw binary records, or use repeated render/crop
  attempts to reconstruct native PowerPoint semantics.

---

## Reading Content

```bash
# Deterministic cloud-first inventory
python scripts/inspect_pptx.py presentation.pptx --pretty

# Prose-oriented text extraction
python -m markitdown presentation.pptx

# Visual overview
python scripts/thumbnail.py presentation.pptx "$PPTX_TEMP_DIR/overview"

# Raw XML when editing
python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
  presentation.pptx "$PPTX_TEMP_DIR/unpacked"
```

---

## Editing Workflow

**Read [editing.md](editing.md) for full details.**

0. **QA the template first.** It's good or weak — your job is to tell.
   If good, reuse as-is and respect its design. If weak, upgrade the
   broken slides with `components/` *in the template's own palette and
   fonts*. See [editing.md § Step 0](editing.md#step-0-qa-the-template-before-reusing-it).
1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

---

## Creating from Scratch

**Read [from_scratch.md](from_scratch.md) for full details.**

No reference deck — blank `Presentation()` + a theme picked from
[themes.md](themes.md). Use `components/` for hard visual shapes
(gantt, funnel, radar, swot, etc.) and python-pptx primitives
directly for the easy stuff. Real OOXML, fully editable in
PowerPoint. For native/complex charts or an existing generator, retain the
local [pptxgenjs adapter](pptxgenjs.md). If the caller supplied a `.pptx`,
that's editing — see above.

---

## Adaptive foreground fork-join for generated images

Use this path only when a from-scratch deck genuinely benefits from generated
images. Do not add image generation to text-, chart-, component-, or
template-driven work that already satisfies the visual requirements. When the
`Agent` tool is available, fork-join is the default high-efficiency option, not
a hard requirement: choose the topology that best preserves quality, tool
availability, and task completion. Read
[references/bounded-foreground-fork-join.md](references/bounded-foreground-fork-join.md)
before dispatch.

**Current runtime note:** a group of direct `ImageGen` calls may be displayed as
`Parallel`, but QwenWork currently processes that grouped ImageGen path
serially and the parent does not advance PPT authoring while it waits. Treat it
as batched serial generation, never as fork-join or proof of concurrency. When
authoring can proceed without the images and at least two image slots are
planned, use the `Agent` fork-join path if available; fall back to direct
generation only when delegation is unavailable or fails.

- Form one compact manifest: each slot's `anchor` / `supporting` / `optional`
  role, prompt, requested size, exact box, paths, crop-loss threshold, attempt
  limit, and final fallback. Put canvas direction, target aspect, preferred
  subject placement, and text-safe region into the prompt as soft design intent;
  refine later-wave records when earlier results justify it.
- Prefer dispatching one PPT-authoring Agent and the highest-value image slots
  together. Use the concurrency the host safely provides. If there are more
  slots than the first wave can hold, continue with priority-ordered waves or a
  suitable licensed search/user-asset route; never discard a slot merely
  because the first wave is full.
- Require the authoring Agent to write and run the build script immediately and
  return an openable placeholder draft without waiting for images. It must then
  record `authoring-result.json` with `scripts/authoring_result.py`; writing only
  the script is incomplete.
- Each first-wave image Agent normally calls `ImageGen` once, checks the file
  and dimensions,
  and computes `crop_loss = 1 - min(source_ratio / slot_ratio, slot_ratio /
  source_ratio)`. A value above the slot threshold is a usable,
  non-retryable `constraint_mismatch`, not a new image-processing flow.
- The parent owns recovery. Retry a provider failure with no usable artifact;
  after final-slide visual evidence, it may also replace or regenerate a
  materially unusable `anchor` image whose subject, theme, or composition
  cannot be repaired by layout. Watermarks, returned dimensions, crop loss, and
  minor style variance alone are not enough. Keep attempts evidence-based and
  bounded, and overlap recovery with independent draft QA when useful.
- Join once, verify `authoring-result.json`, and adapt usable mismatches through
  normal layout judgment. A missing or invalid authoring result means the
  authoring branch failed even if its prose says it completed; the parent must
  immediately execute the same established plan once on the ordinary local authoring
  path before binding images.
  Placeholders are draft-only; exhausted slots must use complete,
  theme-consistent no-image fallbacks before the normal final QA.
- If `Agent` is unavailable, initial dispatch fails, or a small task is clearer
  without delegation, use direct parent execution without claiming concurrency.

Official ImageGen watermarks are expected unless the user explicitly requested
otherwise. Never regenerate or edit an image solely to hide that watermark.

---

## Design principles

The per-theme grammar files own the specific taste calls (palette,
fonts, layout rhythm). A few principles cut across every theme:

- **Dominance over equality.** One color carries 60–70% of the visual
  weight, with one or two supporting tones and one sharp accent.
  Equal-weight palettes look unintentional.
- **Sandwich the deck.** Dark cover + light body + dark closer is the
  default read; or commit fully to dark for a premium feel. Don't
  alternate randomly.
- **Commit to one motif.** Pick a single distinctive element (rounded
  image frames, hairline rules, color-blocked sections, etc.) and
  carry it across every slide. Mixing motifs reads as drafted, not
  designed.
- **Make empty space intentional.** Size cards and frames to their actual
  content and visual role. A border around short text is not, by itself, a
  meaningful visual. Avoid tall, mostly empty containers that resemble
  unfilled image slots; use a compact composition, rebalance the content, or
  leave purposeful open space unframed.
- **Ship complete layouts.** Draft image placeholders are allowed only while
  parallel work is in flight. Before final QA, bind the asset or redesign the
  slide as a complete no-image composition; never deliver a slot label, empty
  frame, or placeholder-like panel.

Type sizing — useful as a quick check; per-theme grammars may
override:

| Element | Size |
|---------|------|
| Slide title | 36–44pt bold |
| Section header | 20–24pt bold |
| Body text | 14–16pt |
| Captions | 10–12pt muted |

For palette + font choices, read [themes.md](themes.md) and the
matching `themes/<id>.md`. For layout slot tables and bounds, read
[layouts.md](layouts.md). For per-shape authoring traps (low
contrast, normAutofit overflow, accent-line-under-title, text-box
padding), read [authoring.md](authoring.md).

---

## QA (Required)

Inspect critically, but keep the pass bounded. A careful review may legitimately
find no visual issue. Do not manufacture findings or extend QA merely to force
a fix-and-verify cycle.

### Content QA

```bash
python -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

### Structural QA

```bash
python scripts/qa_pptx.py output.pptx --pretty
```

For a template-derived deck, preserve the original as the structural baseline:

```bash
python scripts/qa_pptx.py output.pptx --original template.pptx --pretty
```

The single entry point keeps the cloud/local preflight, deterministic layout
checks, and final local PowerPoint/XSD/chart gate. It reports broken rels, text
overflow, off-slide geometry, duplicate slide IDs, unreferenced media, WCAG
contrast, font hierarchy, palette adherence, and package validity without
forcing the Agent to merge three output formats. Use the individual scripts
only for focused diagnosis (`scripts/validate_pptx.py`,
`scripts/view_issues.py`, and `scripts/oxml/package_audit.py`). Fix blocking
findings before visual QA.

### Visual QA

Use a risk-adaptive, staged, read-only review. Visual QA judges rendered
appearance; it must not repeat the deterministic measurements already produced
by `validate_pptx.py`, `view_issues.py`, or `package_audit.py`.

1. Create readable overview grids with no more than six slides each:

   ```bash
   python scripts/thumbnail.py output.pptx "$PPTX_TEMP_DIR/qa-overview" \
     --cols 3 --tile-width 640 --max-slides-per-grid 6
   ```

2. Inspect every overview grid once for cross-slide consistency and obvious
   defects.
3. Inspect full-resolution renders for high-risk slides: the cover and closer,
   slides containing generated/user images, slides named by structural QA, and
   slides visibly flagged in the overview. Eight slides is a useful default
   batch, not a quality ceiling. Expand or split the detail set when the deck is
   long, image-dense, visually heterogeneous, or the overview/structural QA
   leaves material uncertainty.
4. If a slide is fixed, re-render and re-inspect only that slide. Rebuild the
   overview only when the fix changes the deck-wide visual system.

Create the targeted grid directly instead of cropping or re-rendering the full
deck manually:

```bash
python scripts/thumbnail.py output.pptx "$PPTX_TEMP_DIR/qa-detail" \
  --slides 1,4,8 --cols 3 --tile-width 900
```

If a subagent tool is available, dispatch one dedicated fresh-eyes Agent. Do
not duplicate the same inspection in the parent while it runs. Pass the
following hard limits verbatim because a general-purpose child may not inherit
this Skill:

```
Perform a bounded visual QA of this rendered deck. This is an observation-only
task, not a programmatic image-analysis task.

Hard limits:
- Use Read only. Do not call Bash, Python, OCR, PIL, OpenCV, Grep, Edit, or Write.
- Do not crop, zoom, create derived images, sample pixels, measure bounding
  boxes, calculate contrast ratios, or inspect OOXML.
- Trust the supplied structural-QA results for exact geometry, overflow,
  package integrity, and WCAG measurements. Do not re-measure them.
- Start with two Read batches: first all overview grids in parallel, then the
  supplied high-risk/full-resolution slides in parallel. Add targeted batches
  only for concrete unresolved risks exposed by those views or structural QA.
  The evidenced risk determines the detail-page and batch count; there is no
  preset quality ceiling. Do not re-read unchanged views or start a repetitive
  proof loop.
- If an observation is uncertain, label it uncertain and return. Do not start
  a proof loop.

Look for:
- visible overlap, clipping, or unreadable text
- visibly uneven alignment, spacing, or visual hierarchy
- broken, severely mis-cropped, or stretched images
- Treat official ImageGen watermarks as expected, not as defects, unless the
  user explicitly requested watermark-free assets. Do not start watermark
  removal, cropping, or regeneration work merely because the mark is visible.
- inconsistent palette, typography, or repeated-component treatment
- visible placeholders, placeholder-like mostly empty containers, oversized
  cards whose content is stranded in one corner, or rendering artifacts

Overview grids:
- /path/to/qa-overview-1.jpg
- /path/to/qa-overview-2.jpg

High-risk full-resolution slides (start with the highest-risk batch):
- /path/to/slide-01.png (cover; expected: ...)
- /path/to/slide-04.png (generated image; expected: ...)

Return a concise per-slide issue list with severity and visible evidence. If a
slide has no visible issue, say "none". Do not repair the deck.
```

If no subagent is available, follow the same two-stage review yourself. The
rendered image is the visual source of truth. Do not extract images, sample
pixels, compare hashes, or write ad hoc analysis scripts. One careful look per
artifact is enough.

### Verification Loop

1. Generate slides → Content QA → Structural QA → Render → Risk-adaptive visual QA
2. List visible issues; if none are found, stop after the bounded pass
3. Fix confirmed issues in the reusable source
4. Re-render and re-verify affected slides only
5. Stop when the affected-slide pass reveals no new issue

---

## Converting to Images

Convert presentations to individual slide images for visual inspection:

```bash
python scripts/thumbnail.py output.pptx "$PPTX_TEMP_DIR/qa-overview" \
  --cols 3 --tile-width 640 --max-slides-per-grid 6
python scripts/oxml/lo_bridge.py --headless --convert-to pdf \
  --outdir "$PPTX_TEMP_DIR" output.pptx
pdftoppm -jpeg -r 150 "$PPTX_TEMP_DIR/output.pdf" \
  "$PPTX_TEMP_DIR/slide"
```

`thumbnail.py` prefers cloud rendering and is the fast overview path. The
bounded QA settings create readable 3x2 grids instead of shrinking a 12-slide
deck into one low-detail image. The following two commands create
full-resolution `slide-01.jpg`, `slide-02.jpg`, etc. for targeted local visual
QA; do not read every full-resolution slide by default.

To re-render specific slides after fixes:

```bash
pdftoppm -jpeg -r 150 -f N -l N "$PPTX_TEMP_DIR/output.pdf" \
  "$PPTX_TEMP_DIR/slide-fixed"
```

---

## Dependency Recovery

Run the semantic entry point first and recover only from a concrete missing
capability. Reuse compatible workspace tooling; do not perform speculative
installation or broad environment discovery. If recovery needs user action,
state the affected task capability and available choices without exposing
internal credentials, executable names, or routing details.
