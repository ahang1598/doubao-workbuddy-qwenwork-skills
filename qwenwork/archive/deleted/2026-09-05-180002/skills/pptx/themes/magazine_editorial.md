# Theme — Magazine Editorial

**Voice**: editorial; drop caps; pull quotes; 3-col feel; type-led.
**Fit**: feature stories, **city / travel / culture intros**,
long-reads, print-style essays, Monocle-ish.
**Don't fit**: dense data dashboards, financial reports.

## Palette

| Slot | Hex | Name |
|---|---|---|
| primary | `#A02820` | brick |
| secondary | `#141414` | ink |
| accent | `#8A5A28` | champagne |
| muted | `#766E64` | warm gray |
| bg | `#FAF6F0` | ivory |
| on_bg | `#141414` | ink |

## Fonts

- header: `Playfair Display`
- body: `Lora`

## image_style suffix

> `editorial photograph, natural window light, film grain, muted warm
> palette, shallow depth of field, no text, no logos, no watermarks`

## Grammar

### Cover

A page-spanning hairline frame at margin `0.42″`, drawn as **four
thin LINES** (not a filled shape). Use either:

```python
slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
# or:
shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, ...)
shape.fill.background()
shape.line.color.rgb = RGBColor(0x14, 0x14, 0x14)
shape.line.width = Pt(0.75)
```

Frame coordinates (each is a single line):

| Side | from | to |
|---|---|---|
| top | `(0.42, 0.38)` | `(12.92, 0.38)` |
| bottom | `(0.42, 7.12)` | `(12.92, 7.12)` |
| left | `(0.42, 0.38)` | `(0.42, 7.12)` |
| right | `(12.92, 0.38)` | `(12.92, 7.12)` |

Photo sits **inside** the frame on the right half:
`(6.85, 0.55, 6.05, 6.40)`. Do not full-bleed past the frame — it
breaks the editorial container.

Left-half text slots (all inside the frame margin):

| Slot | Position (in) | Style |
|---|---|---|
| eyebrow | `(0.78, 0.78, 4.80, 0.30)` | tracked small-caps issue meta |
| title | `(0.78, 1.50, 5.50, 1.40)` | serif display |
| subtitle | `(0.78, 3.00, 5.30, 0.60)` | |
| body | `(0.80, 4.20, 4.85, 2.00)` | |
| footer | `(0.80, 6.50, 4.00, 0.30)` | |

### Body

140pt brick-red drop cap + 2-column body + thin vertical rule between
columns (also a connector line, **not** a filled rect).

### Quote

Half photo + italic 38pt pull-quote + brick-red attack mark.

### Closer

Dark final page + italic 120pt + champagne meta line.

## ⚠ Filled-frame warning

**DO NOT** draw the cover frame as a filled `MSO_SHAPE.RECTANGLE`
with `fill.solid() + fill.fore_color.rgb = #141414`. A filled
rectangle the size of the frame paints a giant ink-black block over
the entire canvas and hides every textbox you place inside it. This
has happened more than once in practice — the bug is silent until
visual QA because the slide XML looks fine.

Confirmation check before you save: every "frame / rule / hairline"
shape in the deck should be either an `add_connector` or a rectangle
with `fill.background()`. There should be no solid-filled shape
larger than a small accent bar.

## ⚠ Type-led, not card-led

Magazine layouts work because of generous whitespace and 1–2 strong
visual elements per slide. **Avoid stacking 6+ rounded rectangles or
ovals as decoration** — that's a card-grid layout, which reads as
"slick SaaS landing page" and breaks the editorial illusion. If you
find yourself adding shape #7 to fill the slide, the slide is
over-designed; remove half and let the type breathe.

## Forbid

- Rounded corners (square only)
- Shadows
- Gradients

Unless the topic explicitly calls for soft warmth — in that case
relax `forbid` and write down the exception in a comment.
