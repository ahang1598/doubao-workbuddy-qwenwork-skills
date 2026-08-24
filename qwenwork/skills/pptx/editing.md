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

Run all three:

```bash
python -m markitdown template.pptx          # content / structure
python scripts/view_issues.py template.pptx # overlaps, overflow, contrast, off-slide
python scripts/thumbnail.py template.pptx   # visual — actually look at it
```

A template is **good** when nothing on the page is fighting itself —
consistent grid, type hierarchy holds, deliberate palette, every
slide's visuals carry information. Reuse as-is. Don't restyle.

A template is **weak** when any of these hold:

- `view_issues.py` returns warnings the author would have fixed
  (overlaps, alignment drift, low contrast).
- Text-heavy pages have 0–1 visuals where the content's shape calls
  for a matrix / timeline / KPI row / decision card. Generic
  bullets-only on a deck that's about comparing options, phased work,
  performance, or a decision is execution debt, not minimalism.
- Decorative shapes (lone circles, ornaments) carry no information
  and don't build a motif — placeholder filler.
- Type contrast is flat (one weight, one size carries the page).

Judge per slide; strong cover + weak content pages is common.

### Surface the verdict before mapping content

When the template is weak — *especially* when the user emphasized
strict adherence — name the verdict before silently filling content
or silently rebuilding. One short message: which pages you'll preserve
exactly (cover, dividers, anything deliberate), which weak pages you'll
upgrade *in the template's own colors and fonts*, and an opt-out for
the user who wants the bullets kept verbatim. If the user says keep
them, that's a deliberate call — honor it. If the template comes back
good, skip this and just map content.

### Upgrading a weak template while keeping its style

The goal is "same deck, better executed," not "a new theme." Lift
the template's design tokens and feed them to the components:

1. **Sample the template's palette + fonts** — its dominant fill, its
   accent, its title face, its body face. Build a `helpers.Style`
   from those values (don't import a `themes/` palette; that would
   re-brand the deck):

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

---

## Template-Based Workflow

When using an existing presentation as a template:

1. **Analyze existing slides**:
   ```bash
   python -m markitdown template.pptx
   ```
   Review markitdown output to see layouts (slide titles, placeholder text, structural cues).

2. **Plan slide mapping**: For each content section, choose a template slide.

   ⚠️ **USE VARIED LAYOUTS** — monotonous presentations are a common failure mode. Don't default to basic title + bullet slides. Actively seek out:
   - Multi-column layouts (2-column, 3-column)
   - Image + text combinations
   - Full-bleed images with text overlay
   - Quote or callout slides
   - Section dividers
   - Stat/number callouts
   - Icon grids or icon + text rows

   **Avoid:** Repeating the same text-heavy layout for every slide.

   Match content type to layout style (e.g., key points → bullet slide, team info → multi-column, testimonials → quote slide).

3. **Unpack once through the stable package entry point**:
   ```bash
   python scripts/edit_package.py unpack template.pptx unpacked/
   ```

4. **Build presentation** (do this yourself, not with subagents):
   - Delete unwanted slides (remove from `<p:sldIdLst>`)
   - Duplicate slides you want to reuse (`deck_clone.py`)
   - Reorder slides in `<p:sldIdLst>`
   - **Complete all structural changes before step 5**

5. **Edit content**: Update text in each `slide{N}.xml`.
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
1. Read the slide's XML
2. Identify ALL placeholder content—text, images, charts, icons, captions
3. Replace each placeholder with final content

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
- **Longer replacements**: May overflow or wrap unexpectedly — verify via markitdown that all the intended text survives
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
