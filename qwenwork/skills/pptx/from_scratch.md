# Creating from Scratch (python-pptx)

No reference deck, no brand template — just a topic and a blank
canvas. Author with python-pptx; real OOXML, fully editable in
PowerPoint, no conversion tells. If the caller supplied a `.pptx`,
you're in [editing.md](editing.md) territory instead.

## Workflow

1. **Pick a theme.** Start blank with `Presentation()` and pick from
   [themes.md](themes.md) — an index of 7 archetypes (business deep
   blue, magazine editorial, ink wash, swiss, …). The
   index is just the picker; after choosing, read the matching
   `themes/<id>.md` for palette, fonts, image_style, grammar,
   scar-tissue, and forbid rules. Each archetype is a *starting
   point*, not a slot you must select; invent your own when none fit.
   For slot geometry that works across themes, see
   [layouts.md](layouts.md).
2. **Plan slide layouts** before writing code. For each slide,
   decide: which layout slot table from [layouts.md](layouts.md), what
   content goes where, and whether you need a **component** for a
   hard shape (gantt, funnel, swot, etc.) or just primitives. If at
   at least one generated image would add value, establish the shared image-slot
   manifest and consider the adaptive foreground fork-join in
   [SKILL.md](SKILL.md#adaptive-foreground-fork-join-for-generated-images)
   before authoring. Prefer it when authoring and image work can overlap, while
   keeping a direct or multi-wave path available when that better completes the
   task.
3. **Author slides** with python-pptx primitives + `components/`
   helpers + `helpers.py` for text/run formatting.
4. **Save** to a working path, then run the QA loop documented in
   [SKILL.md](SKILL.md#qa-required): content QA → structural QA
   (`view_issues.py`) → adaptive visual QA (overview grids first, then enough
   targeted full-resolution slides to resolve actual risk).

## Before you start: ask once if uncertain

Don't chain-ask. If the prompt leaves you with two or more genuinely
uncertain starting choices (theme + page count, topic focus + style,
etc.), fold them into a single `ask_user_question` rather than asking
sequentially or guessing each in turn. A single ask reads as
consultation; two or three reads as an interrogation. With zero
uncertain choices, skip the ask entirely and start working.

## When to use a component vs primitives

Hard visual shapes (gantt, funnel, radar, swot, flywheel, layered
diagram, timeline, allocation bars, flow matrix, metric card, quote
block, comparison) live in `components/`. Multi-shape composition is
fiddly to align by hand, and these shapes drift fast — a component
call produces 8–15 grouped shapes with verified geometry, where
hand-stacking the same diagram with `add_shape` typically lands at
40+ shapes with subtle misalignments. Plain text, titles, bullets,
single images, two-column body, simple tables, and basic
bar/line/pie charts go through python-pptx primitives directly.

The catalog is small on purpose — 12 starters, no more. For the
decision flowchart, "use when / not for" notes, and content schemas,
read [components.md](components.md). For exact signatures, read the
matching `components/<name>.py` (the source is the ground truth).

## python-pptx essentials

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from helpers import save_pptx

prs = Presentation()  # blank — set canvas + theme yourself
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)  # 16:9 widescreen
slide_w, slide_h = prs.slide_width, prs.slide_height  # EMU; 1 inch = 914400

# the blank Presentation ships generic layouts; for a from-scratch deck
# we typically pick layout 6 (truly blank) and place everything ourselves
layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(layout)

# add a free shape
shape = slide.shapes.add_shape(
    MSO_SHAPE.ROUNDED_RECTANGLE,
    Inches(0.5), Inches(1.5), Inches(4), Inches(2),
)
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
shape.line.fill.background()  # no border

# add a text box
tb = slide.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(3.6), Inches(1.6))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.alignment = PP_ALIGN.LEFT
run = p.add_run()
run.text = "Revenue up 42% YoY"
run.font.size = Pt(28)
run.font.bold = True
run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

save_pptx(prs, "output.pptx")
```

### Units

- 1 inch = 914400 EMU = 72 pt
- Slide coordinates: EMU (use `Inches(x)`, `Emu(x)`, or `Cm(x)`)
- Font size: points (`Pt(x)`)
- Default 16:9 slide: 10" × 5.625" = 9144000 × 5143500 EMU
- 16:9 widescreen (the canvas everything in this skill is tuned for):
  13.333" × 7.5" = 12192000 × 6858000 EMU. Set explicitly on a blank
  `Presentation()` — `python-pptx`'s default is the older 10" × 5.625".

### Layouts on a blank presentation

A blank `Presentation()` ships generic placeholder layouts. For
from-scratch authoring, prefer layout 6 (truly blank) and place
everything yourself using slot geometry from
[layouts.md](layouts.md) — the masters/placeholder typography you'd
inherit from a brand template aren't there, so there's little to be
gained by binding to layouts 0–5.

## Component usage

```python
from components import add_metric_card
from helpers import FontPair, Palette, Style

style = Style(
    palette=Palette(
        primary=RGBColor(0x1E, 0x27, 0x61),
        secondary=RGBColor(0xCA, 0xDC, 0xFC),
        accent=RGBColor(0xFF, 0x6A, 0x00),
        muted=RGBColor(0x6B, 0x72, 0x80),
        bg=RGBColor(0xF7, 0xF8, 0xFA),
        on_bg=RGBColor(0x11, 0x18, 0x27),
    ),
    fonts=FontPair(header="Cambria", body="Arial"),
)

slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

add_metric_card(
    slide,
    origin=(Inches(0.6), Inches(1.4)),
    size=(Inches(3.8), Inches(2.2)),
    content={"kicker": "ARR", "value": "$12.4M", "desc": "+18% YoY"},
    style=style,
)
```

Each component takes `(slide, origin, size, content, style)` and
returns the group it added. See [components.md](components.md) and
`components/<name>.py` for
the exact signatures of all 12 starters.

## helpers.py — text / palette / font conveniences

```python
from helpers import smart_quotes, apply_palette, apply_font_pair, set_text

set_text(shape, "the “Agreement”", size=18, bold=True, color=palette["primary"])
# smart-quotes are preserved correctly in the OOXML
```

Use these for any text run more elaborate than a single line. They
keep the OOXML clean (proper `<a:rPr>` attributes, no stray empty
runs, correct `<a:ea>` handling for CJK).

## Fetching real photos

**Cover, section dividers, hero pages, and quote slides take a real
photo by default.** Body content slides can satisfy "every slide
needs a visual" with a component, chart, KPI row, or icon — those
don't need a photo. The anchor pages do. A topic-driven deck (a
city, a product, a factory floor, a person, a building, a launch)
without a single fetched photo is broken — re-do. The default flips
only when the chosen theme's grammar opts out explicitly (e.g. a
diagram-only theme, a type-as-image theme, a negative-space theme);
follow the theme file you read.

Use an image generation or licensed image-search capability available in the
current host. Save every selected image to a local task path before embedding
it; never leave an expiring URL in the deck. The pattern:

1. **One `image_style` suffix per deck.** Each theme file declares one
   (e.g. `themes/business_deep_blue.md`). Append it to every prompt
   so the deck's photos share a look.
2. **Aspect from layout.** `16:9` for full-bleed covers and the
   image halves of Layouts B / E; `1:1` for square inserts; `9:16`
   only when the layout is vertical.
3. **Download before saving the .pptx.** The CLI returns ephemeral
   URLs (`/ephemeral/` paths) that stop resolving shortly after
   generation. Curl into `assets/` first, then `add_picture` the
   local path.

For a multi-image deck, prefer the adaptive foreground fork-join in
[references/bounded-foreground-fork-join.md](references/bounded-foreground-fork-join.md):
overlap PPT authoring with as many high-value single-image tasks as the host can
safely run. Continue remaining slots in priority-ordered waves or use a suitable
licensed search/user asset; the first wave is not a total-image limit. Keep
first attempts cheap. The parent owns recovery for provider failures and for an
`anchor` image that final-slide evidence shows is materially unusable. A
successful image is not regenerated merely for its watermark, dimensions,
aspect, crop loss, or minor style variance.

Do not mistake the host's `Parallel` label on several direct `ImageGen` calls
for this topology. In the current QwenWork runtime that grouped ImageGen path is
processed serially and blocks parent authoring; describe it as batched
generation. True workflow overlap requires separate PPT-authoring and image
Agent branches followed by a join.

Preplan a deterministic fallback for every image slot before dispatch. An
anchor or supporting slot may use a same-size muted placeholder rectangle only
in the in-flight draft. Its planned final fallback must be a complete no-image
layout, such as a paper-text cover, quote block, component, or text-led
composition with no empty frame or slot label. Do not invent the fallback after
a failure; quality pressure is what causes unbounded retry loops.

After the retry budget is exhausted, use the preplanned complete fallback and
report it.
Never substitute a hand-drawn picture (PIL, matplotlib, python-pptx shapes) or
a decorative geometric shape (circle + initials, swatch grid) as if it were the
requested image.

### Fit returned images without regeneration

Compute the slot's aspect (`w / h`) before generating. Image
generators expose different shape parameters — aspect, pixel size,
resolution preset — under flag names that vary by provider and change
over time. A value the generator doesn't recognise is silently
ignored and you get its default shape. Inspect the live parameters
of the active image capability, then pick the value closest to your
slot's ratio.

Official ImageGen output may contain a service watermark. Unless the user
explicitly requests watermark-free assets, accept it as expected output: do not
inspect it repeatedly, remove it, crop only to hide it, or regenerate the image
because it is visible. If watermark-free output is explicitly required, do not
repeat the same official generation path; use an available licensed or
user-provided asset, or state the limitation.

When a usable image returns at a different size or aspect, keep it and adapt the
slide. Prefer, in order:

1. For a mild mismatch, use a moderate subject-preserving cover crop.
2. For a large mismatch, adjust the image slot and rebalance nearby content
   within the planned grid.
3. When the slot cannot move safely, use contain treatment with an intentional,
   theme-coordinated background instead of accidental empty space.
4. Use the preplanned no-image fallback only when none of these treatments
   preserves a readable composition.

Never stretch the image or regenerate it solely because its returned pixels or
aspect differ from the request. The `view_issues.py` "shape on image" info
finding is expected when a theme shape overlaps a cover-cropped image.

Slot ratios in this skill — for others, do the math:

| Slot | Ratio (w/h) |
|---|---|
| Layout A full-bleed cover (13.333 × 7.5) | 1.778 |
| Layout B image-right half (6.483 × 7.5) | 0.864 |
| Layout E image-right (5.08 × 4.95) | 1.026 |
| Magazine Editorial cover photo (6.05 × 6.40) | 0.945 |

## Fetching brand logos

A brand or website logo (customer logo wall, partner strip, cover
mark) is a deterministic asset, not a generated image — fetch the
real mark from the site's own servers via
`scripts/get_logo.py`. It works from China-reachable networks
(site `<link>` icons → `/favicon.ico` → domestic favicon API
fallback; no Clearbit / Google s2 / Brandfetch needed).

```python
from scripts.get_logo import fetch_logo, fetch_logos, LogoFetchError

# single
try:
    logo_path = fetch_logo("stripe.com", out_dir="assets/logos")
    slide.shapes.add_picture(logo_path, x, y, height=Emu(457200))  # size by height
except LogoFetchError:
    pass  # degrade to the plain text brand name — never a fake-from-shapes logo

# logo wall, fetched in parallel
results = fetch_logos([
    {"domain": "stripe.com", "out": "assets/logos/stripe.png"},
    {"domain": "notion.so",  "out": "assets/logos/notion.png"},
    {"domain": "figma.com",  "out": "assets/logos/figma.png"},
], concurrency=4)
for r in results:
    if r["ok"]:
        slide.shapes.add_picture(r["path"], ...)
```

Logos come back square-ish (favicon / apple-touch-icon, often
180–512px). In a row, size by **height** and let width follow native
aspect — mixed-shape marks line up on a common baseline that way.

## Authoring pitfalls

Recorded scars from python-pptx authoring (units, text, shapes,
charts, images) live in [authoring.md](authoring.md). Read it before
adding shapes / textboxes / images / charts on a blank canvas — most
of the entries apply equally to template editing.

## When you need raw XML

python-pptx exposes the underlying lxml element via `shape._element`.
Use it as an escape hatch when the high-level API can't express a
construct (gradient stops, complex chart formatting, custom geometry
adjustments). Examples are in [editing.md](editing.md#smart-quotes)
and the components themselves.

## What this skill does **not** do

- **HTML → PPTX.** Always leaves tells (image-per-slide, font drift,
  CSS-subset substitutions). We ship real OOXML for editability.
- **pptxgenjs as the default.** Keep python-pptx + components as the
  theme-led default. Use the [pptxgenjs adapter](pptxgenjs.md) for native
  complex charts or an existing generator where changing adapters would add
  risk.
- **Cloud authoring.** Cloud capabilities accelerate inspect, structural
  validation, conversion, and rendering; editable authoring remains local.
- **Component catalog growth.** Keep components ~12. Anything beyond,
  use primitives. Catalog quality caps deck quality.
