# Editing Presentations

If the source is legacy `.ppt`, first follow
[references/legacy-ppt.md](references/legacy-ppt.md) and normalize it to
editable `.pptx`. Do not start template QA, unpacking, or binary inspection
until that conversion succeeds.

When you're authoring shapes, textboxes, images, or charts in a
template, also read [authoring.md](authoring.md) — recorded scars
that apply to template editing as much as to from-scratch.

## Step 0: QA the template before reusing it

Don't skip this — especially when the user has emphasized strict
adherence. Mapping content onto a broken template silently produces a
broken deck. "Follow the template" means honor its **brand identity**
(palette, fonts, logo, footer/header, page numbering, slide size,
masters, section order); it does not mean inherit its **execution**
(broken alignment, decorative-only shapes, content pages that don't
fit the content's shape). Brand identity is the user's intent; broken
execution is not.

Run all four:

```bash
python -m markitdown template.pptx           # content / structure
python scripts/deck_style.py template.pptx --capacity --pages <FINAL_PLANNED_SLIDE_COUNT>
                                             # ← the decisive test
python scripts/view_issues.py template.pptx  # overlaps, overflow, contrast, off-slide
python scripts/thumbnail.py template.pptx    # visual — actually look at it
```

Here, `<FINAL_PLANNED_SLIDE_COUNT>` is the current outline's total slide count,
including structural slides; do not substitute an earlier request, a guessed
count, or content-page count. Rerun once if the outline materially changes.

**Capacity informs the workflow. Read it first.** `--capacity` counts
the template's *distinct* content-page layouts (collapsing near-
duplicates like `内文-2` / `1_内文-2`, and excluding cover, agenda,
divider, closing and blank) and compares that against the pages you
need. It returns one of four baseline verdicts; use the content's actual
information architecture to confirm or override the recommendation:

The capacity JSON also records each source slide's actual layout part and
inherited visual shapes. Treat that map—not slide-local XML, visible text, or a
guessed slide index—as structural truth. Before adding native shapes to a
retained source slide, inspect its entry; otherwise start from a layout verified
as blank.

| verdict | meaning | what you do |
|---|---|---|
| `strict` | enough distinct content layouts for every page | reuse the layouts, fill their placeholders |
| `mixed` | enough for most pages | reuse where the information architecture matches; build the rest natively |
| `coarse` | brand chrome is reusable, content geometry isn't | keep brand, rebuild content pages natively — see [§ When the template's layouts can't carry the content](#when-the-templates-layouts-cant-carry-the-content) |
| `none` | no reusable content layouts at all | style reference only; compose every content page natively |

A template with two content layouts usually cannot carry sixteen varied pages,
no matter how clean its OOXML is. **This is a property of the template's
structure, not of its execution quality** — which is why it gets its
own check and its own script.

**`view_issues.py` cannot answer this question.** It reports
correctness — is the file broken? A well-built template with thin
layouts returns *zero* findings and is still unable to carry your
deck. Never infer "this template is strong, so I'll reuse its layouts"
from a clean `view_issues.py` report. That inference produced a
16-page deck out of two repeated layouts.

A template is **good** when nothing on the page is fighting itself —
consistent grid, type hierarchy holds, deliberate palette, every
slide's visuals carry information. Reuse as-is. Don't restyle. (Good
execution and sufficient capacity are independent: a template can be
beautifully built *and* `coarse`.)

Beyond capacity, a template is **weak** when any of these hold:

- Text-heavy pages have 0–1 visuals where the content's shape calls
  for a matrix / timeline / KPI row / decision card. Generic
  bullets-only on a deck that's about comparing options, phased work,
  performance, or a decision is execution debt, not minimalism.
- Decorative shapes (lone circles, ornaments) carry no information
  and don't build a motif — placeholder filler.
- Type contrast is flat (one weight, one size carries the page).
- `view_issues.py` returns warnings the author would have fixed
  (overlaps, alignment drift, low contrast). Fix these on the pages
  you keep; they're independent of the capacity verdict.

Judge per slide; strong cover + weak content pages is common. A deck
with a strong brand chrome (cover, dividers, page numbers, logos) and
weak content layouts is the standard case for a Chinese enterprise
template — treat it as **coarse-reference**: keep brand, rebuild
content geometry.

### Surface the verdict before mapping content

When the capacity verdict is `mixed`, `coarse` or `none` and the resulting
choice materially changes what the user asked to preserve — *especially* when
the user emphasized strict adherence — name the verdict before proceeding.
One short message: which pages you'll preserve
exactly (cover, dividers, anything deliberate), which weak pages you'll
upgrade *in the template's own colors and fonts*, and an opt-out for
the user who wants the bullets kept verbatim. **"严格沿用" means honor
the brand identity, not the execution debt** — if you say nothing and
just repeat the template's two content layouts eight times, the user
gets a monotonous deck they didn't ask for. If the user says keep the
template layouts verbatim, that's a deliberate call — honor it and
warn that pages 4/7/10/13 will look identical. If capacity comes back
`strict` and the template looks good, skip this and just map content.

### Upgrading a weak template while keeping its style

The goal is "same deck, better executed," not a redesign. Lift
the template's design tokens and feed them to the components:

1. **Sample the template's palette + fonts** from retained template shapes —
   its dominant fill, accent, title face, body face, and text colors. Every
   newly authored text run must set its font family and color from those
   sampled values rather than relying on application or theme defaults. Build
   a `helpers.Style` from those values (don't run `frontend-design` and don't
   invent a new palette; that would re-brand the deck):

   ```python
   from helpers import Style, Palette, FontPair
   from pptx.dml.color import RGBColor
   tmpl_style = Style(
       palette=Palette(
           primary=RGBColor(0x.., 0x.., 0x..),  # sampled from the template
           secondary=..., accent=..., muted=..., bg=..., on_bg=...,
       ),
       fonts=FontPair(header="<template title font>", body="<template body font>"),
   )
   ```

2. **Replace only the broken hand-built visuals.** A slide stacking
   raw rectangles into a fake KPI strip / timeline / matrix → swap
   it for the matching component (`add_metric_card`, `add_timeline`,
   `add_flow_matrix`, …) called with `tmpl_style`. The component
   renders square, flat, aligned, *in the template's own colors and
   fonts*.

3. **Leave the good slides alone.** Covers, section dividers, and
   anything that already reads as deliberate stay untouched. Only
   the broken slides get the component treatment.

4. **Preserve structural identity** — same slide size, same
   masters/layouts, same logo placement, same section order. You're
   polishing execution, not rebranding.

Re-run `view_issues.py` after the upgrade and confirm the fixes
landed without introducing new findings.

### When the template's layouts can't carry the content

Distinct from "the template has broken visuals" (§ Upgrading above):
the template's layouts are *fine* individually, but there aren't
enough of them for your content. Symptom: you have 8 content pages
of different material — a KPI page, an evaluation matrix, a phased
plan, a comparison, a risk table — but the template only has 2
content-page layouts (say, "big-number-circle" and "left-bullets").
Mapping content forces four repeats of "big-number-circle" and four
of "left-bullets", and the deck reads as monotonous even though
each page individually preserves the brand.

Don't repeat a template layout beyond what the content genuinely
justifies. The rule:

- **Reuse a template layout when the content page has the same
  information architecture** as the layout was designed for. Two KPI
  pages both showing "one headline number + one supporting number"
  is fine. Two KPI pages where one is percent-completion and the
  other is vendor-count crammed into the same big-circle shape is
  not.
- **When the content page has a different information architecture from any
  template layout**, use the blank layout named by the capacity report and
  verified by its inherited-visual inventory; never guess a layout index or
  reuse a source slide that only looks blank. Add a native component styled
  with the template's palette + fonts:

  ```python
  # From the sampled tmpl_style above.
  blank_layout = prs.slide_layouts[<blank_layout_index>]
  slide = prs.slides.add_slide(blank_layout)
  # The blank layout still ships the template's chrome (page number,
  # logo, footer). Native component uses template colors:
  add_flow_matrix(slide, origin=(Inches(0.6), Inches(1.4)),
                  size=(Inches(12), Inches(5.5)),
                  content=..., style=tmpl_style)
  ```

  The result reads as the template's own design — same palette,
  fonts, page number, logo — but with a composition shaped to the
  actual content (matrix / timeline / process / responsibility /
  comparison / metric strip).

- **Component-to-content mapping cheatsheet.** Guides which native
  component to use when a template layout doesn't fit:

  | Content shape | Component |
  |---|---|
  | Sequential / phased steps (3–6) | `add_timeline` |
  | Vendors × criteria × scores | `add_flow_matrix` |
  | Options against each other (2–4) | `add_comparison` |
  | Strengths / weaknesses / risks / actions | `add_swot` |
  | Single big number + supporting detail | `add_metric_card` |
  | Time-boxed tasks with owners | `add_gantt` |
  | Concentric layered model | `add_layered_diagram` / `add_flywheel` |
  | Weighted allocation (budget, time) | `add_allocation_bars` |
  | Part-to-whole with contribution or change | Native chart or `add_allocation_bars` plus callouts |
  | 3–6 metrics with unlike units | Metric-card composition; do not force a shared-axis chart |
  | Multi-dimensional score (3–8 axes) | `add_radar` |
  | Narrowing/prioritization | `add_funnel` |
  | Highlighted quotation / thesis | `add_quote_block` |

  See [components.md](components.md) for signatures.

- **Preserve chrome that's on the master, not the layout.** The
  blank layout inherits the master's page number, logo, footer band.
  Don't hand-draw those — they're already there.

- **When the content page fits no component either**, that's the
  case for a designed-from-scratch page. Same rule: use the blank
  layout + hand-built shapes in the template's colors.

`deck_style.py --rhythm` may still report hints if repetition persists —
treat `layout_reuse` and `content_obligation` as evidence to compare against
the render and planned message, not automatic proof that the template cannot
hold the content. Push pages to native components only when the actual
information architecture warrants it.

---

## Template-Based Workflow

When using an existing presentation as a template:

1. **Analyze existing slides**:
   ```bash
   python -m markitdown template.pptx
   ```
   Review markitdown output to see layouts (slide titles, placeholder text, structural cues).

2. **Plan content before slide mapping.** Give each advertised section a
   substantive destination unless it is intentionally statement-only, then fit
   structural slides within the requested bounds. Match or repeat a layout when
   it serves the information architecture; use a native composition when it
   does not. Placeholder count and layout variety are not goals. For data- or
   structure-heavy pages, plan the semantic visual before cloning.

3. **Unpack once through the stable package entry point**:
   ```bash
   python scripts/edit_package.py unpack template.pptx unpacked/
   ```

4. **Build presentation** (do this yourself, not with subagents):
   - Delete unwanted slides (remove from `<p:sldIdLst>`)
   - Duplicate slides you want to reuse (`deck_clone.py`)
   - Reorder slides in `<p:sldIdLst>`
   - **Complete all structural changes before step 5**

5. **Complete each mapped page**: replace final text and build any planned
   chart, table, component, image, or typographic composition. Text survival
   alone is not completion. If no semantic visual improves comprehension, keep
   the whitespace deliberately and verify it in the render.
   **Use subagents here if available** — slides are separate XML files, so subagents can edit in parallel.

6. **Pack once.** The entry point prunes, audits against the original, and
   writes the output atomically:
   ```bash
   python scripts/edit_package.py pack unpacked/ output.pptx --original template.pptx
   ```

Do not create `prune2`, `prune3`, or repeated unpack directories to recover
from a command mistake. Fix the one workspace or unpack again to a fresh path.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `edit_package.py` | Stable unpack and atomic prune/audit/pack interface; use this for the normal workflow |
| `deck_clone.py` | Duplicate a slide or layout and register every required package relationship |
| `deck_prune.py` | Remove slides/resources no longer reachable after `<p:sldIdLst>` is settled |
| `add_slide.py` | Compatibility helper for the latest local baseline; prefer `deck_clone.py` for complete registration |
| `clean.py` | Compatibility cleanup helper; prefer `deck_prune.py` for the validated standalone workflow |
| `oxml/package_audit.py` | Final schema, relationship, content-type, chart, and slide gate |

### Unpack

```bash
python scripts/edit_package.py unpack input.pptx unpacked/
```

Do not rewrite all XML just to pretty-print it; preserve untouched OOXML bytes.

### deck_clone.py

```bash
python scripts/deck_clone.py unpacked/ slide2.xml --after slide2.xml
python scripts/deck_clone.py unpacked/ slideLayout2.xml
```

The helper creates the new slide and performs package registration. A cloned
slide still shares chart/SmartArt/embedded-object parts with its source; edit
those shared resources deliberately.

### deck_prune.py

```bash
python scripts/deck_prune.py unpacked/
```

Run only after slide order/deletion is final. It removes unreachable slides,
media, and relationships.

### Pack and audit

```bash
python scripts/edit_package.py pack unpacked/ output.pptx --original input.pptx
```

This is the normal high-level interface. `deck_prune.py` and
`oxml/package_audit.py` remain available for focused diagnosis, but do not
manually repeat their sequence during ordinary editing. Fix audit failures in
the edit/generator and rebuild; do not suppress the final gate.

---

## Slide Operations

Slide order is in `ppt/presentation.xml` → `<p:sldIdLst>`.

**Reorder**: Rearrange `<p:sldId>` elements.

**Delete**: Remove `<p:sldId>`, then run `deck_prune.py`.

**Add**: Use `deck_clone.py`. Never manually copy slide files—the script handles
Content Types, presentation relationships, and slide IDs that manual copying
misses.

---

## Editing Content

**Subagents:** If available, use them here (after completing step 4). Each slide is a separate XML file, so subagents can edit in parallel. In your prompt to subagents, include:
- The slide file path(s) to edit
- **"Use the Edit tool for all changes"**
- The formatting rules and common pitfalls below

For each slide:
1. Read the slide together with its referenced layout and source render
2. Distinguish content slots from decoration and persistent brand chrome;
   placeholder metadata alone does not determine the role
3. Bind each source fact once, preserve intentional chrome, and remove unused
   content groups as a whole

**Use the Edit tool, not sed or Python scripts.** The Edit tool forces specificity about what to replace and where, yielding better reliability.

### Formatting Rules

- **Bold all headers, subheadings, and inline labels**: Use `b="1"` on `<a:rPr>`. This includes:
  - Slide titles
  - Section headers within a slide
  - Inline labels like (e.g.: "Status:", "Description:") at the start of a line
- **Never use unicode bullets (•)**: Use proper list formatting with `<a:buChar>` or `<a:buAutoNum>`
- **Bullet consistency**: Let bullets inherit from the layout. Only specify `<a:buChar>` or `<a:buNone>`.

---

## Common Pitfalls

### Template Adaptation

When source content has fewer items than the template:
- **Remove excess elements entirely** (images, shapes, text boxes), don't just clear text
- Check for orphaned visuals after clearing text content

When replacing text with different length content:
- **Shorter replacements**: Usually safe
- **Longer replacements**: May overflow or wrap unexpectedly. Markitdown proves the text survived, not that it fits; structural QA and rendered QA decide fit.
- Consider truncating or splitting content to fit the template's design constraints

**Template slots ≠ Source items**: If template has 4 team members but source has 3 users, delete the 4th member's entire group (image + text boxes), not just the text.

### Multi-Item Content

If source has multiple items (numbered lists, multiple sections), create separate `<a:p>` elements for each — **never concatenate into one string**.

**❌ WRONG** — all items in one paragraph:
```xml
<a:p>
  <a:r><a:rPr .../><a:t>Step 1: Do the first thing. Step 2: Do the second thing.</a:t></a:r>
</a:p>
```

**✅ CORRECT** — separate paragraphs with bold headers:
```xml
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" b="1" .../><a:t>Step 1</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" .../><a:t>Do the first thing.</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="en-US" sz="2799" b="1" .../><a:t>Step 2</a:t></a:r>
</a:p>
<!-- continue pattern -->
```

Copy `<a:pPr>` from the original paragraph to preserve line spacing. Use `b="1"` on headers.

### Smart Quotes

Handled automatically by unpack/pack. But the Edit tool converts smart quotes to ASCII.

**When adding new text with quotes, use XML entities:**

```xml
<a:t>the &#x201C;Agreement&#x201D;</a:t>
```

| Character | Name | Unicode | XML Entity |
|-----------|------|---------|------------|
| `“` | Left double quote | U+201C | `&#x201C;` |
| `”` | Right double quote | U+201D | `&#x201D;` |
| `‘` | Left single quote | U+2018 | `&#x2018;` |
| `’` | Right single quote | U+2019 | `&#x2019;` |

### Other

- **Whitespace**: Use `xml:space="preserve"` on `<a:t>` with leading/trailing spaces
- **XML parsing**: Use `defusedxml.minidom`, not `xml.etree.ElementTree` (corrupts namespaces)
