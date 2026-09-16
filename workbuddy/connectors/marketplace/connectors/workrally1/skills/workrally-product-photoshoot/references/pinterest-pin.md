# Mode: pinterest-pin

Vertical 3:4 visuals tuned to Pinterest's specific aesthetic — moodboard quality, warmth, layered storytelling.

## Why Pinterest is its own genre

Pinterest is not Instagram. Pins succeed on:
- Vertical 3:4 format dominates the feed
- Top portion must hook attention because of mobile crop behavior
- Warm, organic, hand-crafted aesthetic
- Save behavior driven by aspirational utility
- Color palettes lean muted, earthy, dusty pastels — not saturated Instagram look

## Pin Presets

| Preset | Use for | Visual signature |
|---|---|---|
| `lifestyle-aspirational` | Home, travel, fashion, wellness | Soft natural light, curated environment, hand-crafted feel |
| `product-feature-vertical` | Product spotlight for affiliate or DTC | Product on textured surface with warm context |
| `recipe-cover` | Food blog pins | Top-down or 45° angle of dish, ingredients around, warm light |
| `editorial-flat-lay` | Style guides, gift guides | Flat-lay with multiple objects, generous spacing |
| `before-after-stacked` | DIY, makeover, transformation | Two stacked panels, divided clearly |
| `mood-board-grid` | Brand inspiration, design ideas | 3-4 image collage feeling within one image |
| `quote-on-photo` | Inspirational, educational | Atmospheric photo with mood-led composition |
| `tutorial-step-pin` | How-to guides | Single-frame summary with implied steps |

## Prompt Template

```
[FORMAT]
Vertical 3:4 Pinterest pin composition.

[SUBJECT]
{{Subject description — product / scene / flat-lay arrangement}}.

[COMPOSITION]
{{Specific framing for vertical}}, {{focal placement using rule of thirds}}, {{strong visual hierarchy from top to bottom}}, hand-crafted not stock feel.

[AESTHETIC]
Pinterest-native style: warm, hand-crafted, lived-in. {{Specific aesthetic — cottagecore / clean girl / scandinavian / dark academia / coastal grandmother / quiet luxury}}.

[LIGHTING]
{{Soft natural window light / golden hour glow / soft overcast / candlelit warmth}}. Color temp {{warm 3200-4500K typical}}. Gentle highlight rolloff.

[SURFACE & TEXTURE]
{{Linen, raw wood, marble, ceramic, woven texture}}. Tactile, lived-in finish — never sterile.

[COLOR PALETTE]
Pinterest-friendly muted palette: {{2-3 dominant tones — sage, cream, terracotta, dusty rose, oat, ochre, muted navy, warm grey}}. Aligned with known brand context.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 matching entries in photographer-references.md}}. Editorial Pinterest aesthetic. Never include the source names.

[QUALITY MARKERS]
Save-worthy, scroll-stopping, magazine-quality, hyper-detailed textures, photorealistic.

[AVOID]
{{universal + anti-stock-feel}}
no oversaturated colors, no neon, no Instagram-grid square framing,
no horizontal-leaning compositions, no dated stock photo aesthetics, no sterile feel.

resolution: 2k
```

## Typography handling

If user provided concrete text — see Case 1 in `references/typography.md`.
If user said they'll add text later — see Case 2 in `references/typography.md`.
Otherwise — compose freely with rich texture and detail throughout the frame.

## Pinterest-friendly palettes

- **Earthy neutral**: cream, oat, soft sage, warm terracotta
- **Coastal soft**: dusty blue, sand, white, weathered wood
- **Cottagecore**: sage, rose, cream, dried flax
- **Quiet luxury**: warm grey, soft camel, muted navy, parchment
- **Scandinavian**: cool white, pale grey, raw wood, black accent
- **Autumn warm**: ochre, rust, deep green, butter cream
- **Dark academia**: deep brown, oxblood, parchment, ivy green
- **Clean girl**: vanilla, blush, taupe, soft gold

## Photographer references

- **Lifestyle / wellness**: Beth Kirby, Brittany Ambridge, Pia Ulin
- **Food / recipe**: Linda Pugliese, Bobbi Lin, Aubrie Pick
- **Fashion / outfit**: Cass Bird, Jamie Beck, Sandra Semburg
- **Home / interior**: James Merrell, Heidi Caillier, Athena Calderone
- **Mood / dreamy**: Tim Walker, Petra Collins, Jamie Hawkesworth
- **Flat-lay / curated**: Bobby Doherty, Carl Kleiner, Brittany Wright

## Aspect Ratio

Always `3:4` for standard Pinterest pins. Other valid ratios:
- `3:4` — standard pin (default)
- `1:2.1` — long pin (storytelling, infographics)
- `1:1` — square pin (rarely used, lower performance)

## Composition rules

- Subject anchor placed using rule of thirds, vertical hierarchy clear from top to bottom
- Strong visual entry point at the top to stop the scroll
- Multiple objects: group with intentional spacing, not overlap
- Texture in the background carries warmth — linen, wood grain, soft paper, plaster wall
- Pinterest rewards hand-crafted feel — avoid sterile studio polish

## Quality gates

- [ ] Vertical 3:4 composition
- [ ] Palette is muted and Pinterest-appropriate (not saturated Instagram look)
- [ ] Composition feels hand-crafted, not stock
- [ ] Subject is focal anchor with clear vertical hierarchy
- [ ] Known brand colors integrated
- [ ] No oversaturated or sterile look
- [ ] Tactile surface texture present
- [ ] Typography (if any) renders correctly per the three-case rule
- [ ] Prompt ends with `resolution: 2k`

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. Every pin request uses `3:4`.
