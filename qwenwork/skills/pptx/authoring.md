# Authoring Pitfalls

Recorded scars from authoring `.pptx` files via python-pptx — the
kind of bug where the code looks right but the rendered slide is
broken. Read this when you're about to add shapes, textboxes,
images, or charts to a slide, whether you're building from scratch
or editing a template.

This isn't a checklist; treat the entries as *taste calibration*.
Each one explains *why* the trap exists so you can recognize it in
unfamiliar code.

## Coordinates and units

**Keep coordinate math in one unit.** Convert layout literals with `Inches()`,
`Emu()`, or `Cm()` and do not mix converted lengths with unlabeled raw integers.
Before saving, compare content-bearing shapes and their containers with the
slide canvas. Retained template chrome is an internal safe zone, even on a
blank layout.

## Text

**Smart quotes.** Type `"` and `'` get auto-corrected by some
editors but not others — use `helpers.smart_quotes()` for runs that
include quoted material, or write `\u201C` / `\u201D` directly.
Mixed straight + curly within one deck reads as inconsistent.

**Empty `<a:ea>` is fine for CJK.** Modern PowerPoint auto-substitutes
when the East-Asian font slot is empty. Don't preemptively patch
every text run with a Noto / Source Han name — that causes flicker
if the named font isn't enumerated. Only patch when a user reports
tofu, with a font name they confirmed in the picker.

**Wrap prose, not atomic display text.** Set `text_frame.word_wrap = True` for
prose, bullets, and descriptions. For KPI values, value-plus-unit strings,
dates, IDs, and short labels that must stay on one line, size the text against
usable width first. If the string cannot fit at a readable size, widen the box,
reduce the card count, or shorten the display string; do not solve it with
wrapping or autofit.

**`charSpacing` (`spc`) ≤ 200** (= 2.0pt). Above that, PowerPoint
renders runs as single-character vertical columns instead of a
tracked line. Wide-tracking layouts (Swiss titles, ink-wash 节气 /
唐诗) are where this bites.

**Don't center body text.** Set informational prose paragraphs explicitly to
left alignment; do not rely on a template or shape default. Center only
deliberately short display text such as titles, KPI values, or labels.

## Shapes and components

**Don't reuse style dicts across components.** Components may mutate
(apply palette overrides per shape). Pass a fresh dict per call if
you need to vary tokens; if you pass the same dict to multiple
components, don't expect later reads to match what you set
originally.

**Title slide ≠ blank.** `slide_layouts[0]` (title layout) carries
placeholder geometry from the master. Set
`slide.shapes.title.text` rather than adding a parallel textbox —
the parallel one will overlap the placeholder.

**Kill the inherited theme shadow on hand-drawn shapes.** python-pptx
`add_shape` shapes pick up the presentation theme's default style,
which on most templates carries an outer shadow — the soft drop that
reads as "AI-generated." There's no high-level toggle, so use
`helpers.no_shadow(shape)` (it injects an empty `<a:effectLst/>` that
overrides the inherited one). Components already do this; only
hand-drawn `add_shape` calls need the explicit call. Keep corners
square (`MSO_SHAPE.RECTANGLE`) unless a pill/capsule is the
deliberate design — `ROUNDED_RECTANGLE` everywhere is the other
"AI-generated" tell.

## Charts

**Chart data is live.** `add_chart` serializes data as an embedded
spreadsheet. Don't patch chart XML directly afterwards — rebuild
via the chart object's `replace_data()` instead, or the spreadsheet
and the rendered chart will drift.

## Images

**Don't fake pictorial content with shapes.** When a slide needs a
photo, map, screenshot, illustration, or logo, generate a real
image — see
[from_scratch.md § Fetching real photos](from_scratch.md#fetching-real-photos).
Rectangles + text labels read as a wireframe stand-in even when
the geometry is clean. If generation isn't possible, summarize in
text or drop the slide.

**Don't stretch images.** `add_picture(path, x, y, width=W, height=H)`
resizes to exactly `W × H`; if that's not the native ratio, faces
flatten and the slide reads as broken before the title is even read.
A composition slot (cover, divider, hero) also must not be
*inset* — leaving dead space inside it breaks the page composition.

The pattern for a composition slot is size-to-cover, then crop the
overflow so the visible rectangle equals the slot:

```python
pic = slide.shapes.add_picture(p, Inches(x), Inches(y),
                               width=Inches(w), height=Inches(h))
# Compute crop fractions from native vs slot aspect.
pic.crop_left = 0.05
pic.crop_right = 0.05    # crop_top / crop_bottom likewise
```

If the slot's ratio has no close match in the available aspects
(Layout B is the usual offender), accept a deliberate overlap — a
title bar, hairline frame, or footer band sits over the image's
edge. `view_issues.py check_overlap` flags "shape on image" at
`info`; that's expected.

For an in-content figure where surrounding whitespace is fine
(a photo inside body content, not a composition slot), passing only
`width=` to preserve native aspect is acceptable.

**Inset images sit evenly inside their frame.** Equal gaps on all
four sides. An image that touches one edge while leaving a gap on
the opposite edge reads as a misplacement.

**No accent lines under titles.** A thin colored bar directly under
a title is a hallmark of AI-generated slides — viewers register it
as decorative filler before they read the title. Use whitespace,
background color, or a visible weight contrast in the title itself.

**Watch text-box padding when aligning to other shapes.** python-pptx
text boxes ship with internal padding (≈0.05–0.1″ per side). When
you want a textbox edge to line up flush with a shape edge, either
set the box's internal margins to 0 or offset the shape by the
padding amount. Otherwise the alignment looks "almost right" — the
worst kind of wrong.

**Don't fix overflow with `normAutofit`.** When text doesn't fit
its box, the python-pptx temptation is `text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_SHAPE_FONT`
or setting `<a:normAutofit>` on the body. PowerPoint will shrink the
font to 70–80% to fit, which masks the overflow in QA but ships at
illegible sizes. Real fix: (a) trim content, (b) widen the box, or
(c) split across slides. `view_issues.py` flags normAutofit-masked
overflow as `info` precisely because agents keep using it as a
band-aid.

**Low contrast ships even when the eye misses it.** Light text on
light bg, dark text on dark bg, or icons that match their
container's fill all fail accessibility and read as broken to most
viewers. `view_issues.py` runs a WCAG check; trust it. If a
finding fires on what looked fine in your editor, the rendered
slide is the ground truth, not the design tool.

**Give each slide a deliberate visual hierarchy.** An image, chart,
component, or strong typographic composition should give the viewer's eye a
clear landing point. Do not add decoration merely to satisfy a quota; a
purposeful statement slide can be stronger than an irrelevant image. For
image-led covers, section dividers, hero pages, or quote slides, see
[from_scratch.md § Fetching real photos](from_scratch.md#fetching-real-photos).

## Cross-slide rhythm

Let information architecture determine whether compositions repeat or vary.
Repetition can improve comparison; variation is useful only when it improves
comprehension. Run `deck_style.py --rhythm` on the finished deck as evidence,
never as a quota or a requirement to add photos, cards, or components.
