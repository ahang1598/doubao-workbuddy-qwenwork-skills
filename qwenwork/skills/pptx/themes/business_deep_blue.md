# Theme — Business Deep Blue

**Voice**: authoritative; restraint; KPI cards; gold rules.
**Fit**: investor decks, QBR, earnings, financial reviews, strategy
decks; default fallback when the prompt is generic.
**Don't fit**: city / culture / poetry / lifestyle / marketing.

## Palette

| Slot | Hex | Name |
|---|---|---|
| primary | `#0F2044` | navy |
| secondary | `#C8A55A` | gold |
| accent | `#A6332A` | soft red |
| muted | `#766E64` | warm gray |
| bg | `#F5F2EC` | ivory |
| on_bg | `#1C2028` | near-black |

## Fonts

- header: `Source Serif 4`
- body: `Inter`

## image_style suffix

> `corporate architecture, blue glass facade, dusk light, cool tones,
> no text, no logos`

Append this to every `image_prompt` in the deck.

## Grammar

### Cover — hero photo

Two-panel split. LEFT navy panel `(0, 0, 7.3, 7.5)` filled `#0F2044`,
holding the title block. RIGHT ivory panel `(7.3, 0, 6.04, 7.5)`
filled `#F5F2EC` carries the hero photo at
`(7.90, 1.50, 4.80, 4.50)`, square corners only — obtained through
an image capability available in the current host. One vertical gold hairline at `x = 7.3`
separating the panels; one gold horizontal rule at
`(8.40, 6.50, 2.50, 0.04)` under the photo.

The navy panel slot table:

| Slot | Position (in) | Style |
|---|---|---|
| eyebrow | `(0.72, 0.72, 5.90, 0.30)` | gold small-caps, tracked |
| title | `(0.72, 2.20, 6.30, 1.30)` | white serif ~54pt |
| subtitle | `(0.72, 3.50, 6.30, 0.80)` | gold ~32pt |
| body | `(0.72, 5.00, 6.30, 1.40)` | ivory `#EAE6DC` ~16pt |
| footer | `(0.72, 6.72, 6.30, 0.28)` | caption row |

### Agenda

0.9″ navy top bar + gold page number on the right.

### KPI

4 large stat cards across the slide. Gold `+` deltas, soft-red `−`
deltas, square corners.

### Closer

Full navy bg + centered "Thank You" + thin gold hairline below.

## ⚠ Right-panel discipline

The right panel's only job is the hero photo. Do not fill it with
palette swatches, color blocks, KPI cards, charts, or other
decorative content — the navy panel carries the title and KPIs;
the right panel carries the photo. If the photo can't be fetched,
follow the placeholder rule in `from_scratch.md § Fetching real
photos` so the user knows the slot needs filling.

## Forbid

- Rounded corners (square only)
- Shadows
- Gradients

These reinforce the executive-deck tone; rounded rectangles on an
investor cover instantly read as AI-generated.
