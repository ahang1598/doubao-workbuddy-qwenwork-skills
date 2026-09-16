# Mode: closeup-product-with-person

Tight crop showing the **product as the hero** with hands, partial face, or skin context — beauty application, holding, demonstrating, face-product interaction. The person provides context and emotion; the product carries the frame.

## Why this is its own genre

Different from `lifestyle-scene` (wide environment) and `virtual-model-tryout` (full body fashion). This mode is specifically:
- Closeup framing — tight crop on product + adjacent body part
- Product is always the visual anchor
- Person is partial — never the focal subject, always context
- High-end DTC beauty / skincare / fragrance / supplement / wellness aesthetic

## Closeup Presets

| Preset | Use for | Visual signature |
|---|---|---|
| `serum-application` | Skincare, beauty oils, treatments | Hand applying product to face, dropper or spatula visible, glowing skin texture |
| `lipstick-on-lips` | Lip products, lip care, gloss | Tight closeup on lips, product near or applied, sharp catchlight |
| `hand-holding-vertical` | Beauty bottles, fragrance, skincare | Hand cradling product vertically, wrist visible, soft light on glass |
| `pour-into-palm` | Cream, lotion, oil, supplement | Liquid or product poured into open palm, rich texture visible |
| `eye-makeup-closeup` | Mascara, shadow, liner | Eye area in tight crop, product nearby or applied, lash detail |
| `texture-on-skin` | Cream, balm, scrub, foundation | Product swatched or applied on hand/cheek, ingredient texture visible |
| `dropper-mid-air` | Serums, oils with droppers | Dropper hovering near skin with single drop suspended, clinical premium feel |
| `hands-cradling-jar` | Body products, candles, jars | Two hands cradling open jar, fingers in product, indulgent ritual |
| `face-touch-product` | Skincare results, glowing skin | Hand resting on cheek, product nearby, product association with skin result |
| `mouth-bite-or-sip` | Food, beverage, supplements | Lips/teeth interacting with product (sip, bite, taste), sensory focus |

## Prompt Template

```
[FRAMING]
Tight closeup composition. Product is the hero of the frame, occupying {{rough percentage 40-60%}} of visible area. {{Specific crop — face from nose to chin / hands cradling product / palm with poured product / eye area with product nearby}}.

[PRODUCT]
{{Exact product description from reference or known conversation context}}, {{material/finish details}}, {{label/branding visible if applicable}}, sharp focus on product.

[PERSON CONTEXT]
{{Specific body part visible — hands with natural skin texture / lips with realistic detail / cheek with glowing skin / eye area with lash detail}}. Person is partial context, not the focal subject. {{Skin tone aligned with brand audience or specified}}.

[INTERACTION]
{{Specific action — applying, holding, pouring, touching, demonstrating}}. Natural, unstaged, ritualistic feel.

[LIGHTING]
{{Specific lighting setup — see Lighting Setups below}}. {{Direction, quality, color temp}}. Sharp catchlight on product surface. Realistic skin highlight without plasticity.

[LENS & CAMERA]
Shot on {{100mm macro / 85mm portrait}}, aperture {{f/2.8 to f/4}}, shallow DoF, sharp focus on product surface, gentle bokeh on skin background.

[SKIN & DETAIL]
Realistic skin texture with natural pores and micro-imperfections, no smoothing, no plasticity. Hands and fingers anatomically correct. Hair detail crisp if visible.

[COLOR PALETTE]
{{2-3 dominant tones aligned with known brand context}}. Warm or cool dominance per brand. Product colors faithful to reference.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 matching beauty/closeup entries in photographer-references.md}}. Editorial beauty photography, premium DTC standard. Never include the source names.

[PRODUCT FIDELITY DIRECTIVE]
Product remains identical to reference — same color, material, design, branding. Person is supporting context. Product is the visual anchor.

[QUALITY MARKERS]
Magazine-cover quality, hyper-detailed, photorealistic, premium beauty editorial standard, no AI artifacts.

[AVOID]
{{universal + anti-uncanny + anti-text-warp}}
no full face dominating the frame, no person taking focus from product,
no plastic skin, no airbrush look, no warped fingers,
no over-staged feeling, no clinical sterile feel where warmth needed.

resolution: 2k
```

## Photographer references

- **serum-application / face-touch / texture-on-skin**: Sølve Sundsbø, Mert & Marcus, Aubrie Pick
- **lipstick-on-lips / eye-makeup**: David Sims, Mert & Marcus, Inez & Vinoodh
- **hand-holding / hands-cradling**: Carl Kleiner, Aubrie Pick, Aaron Tilley
- **pour-into-palm / dropper-mid-air**: Aaron Tilley, Sølve Sundsbø, Hugh Kretschmer
- **mouth-bite-or-sip**: Linda Pugliese, Christopher Testani, Bobbi Lin

## Lighting Setups

- **serum-application**: Soft beauty dish key from camera-front, slight under-fill, 5000K, gentle catchlight on glass and skin
- **lipstick-on-lips / eye-makeup**: Beauty dish or ring light frontal, 5500K, sharp catchlight on lips/eye, even skin tone
- **hand-holding-vertical**: Window light camera-side, 4500K, rim separation behind product, soft fill on hand
- **pour-into-palm**: Top-down softbox key, 5000K, sharp falloff highlighting liquid texture, hand in shadow
- **dropper-mid-air**: Hard directional key with grid, 5000K, freezes droplet in sharp focus, deep shadow background
- **hands-cradling-jar**: Soft warm window light, 3500K, intimate ritual feel, gentle highlight on jar rim
- **texture-on-skin**: Side raking light to reveal texture, 5000K, sharp shadow detail in product surface
- **face-touch-product**: Soft front-fill with key 45° camera-left, 4500K, glowing skin highlight
- **mouth-bite-or-sip**: Practical warm light or window key, 4000K, appetizing highlight on product

## Aspect Ratio

| Use case | Ratio |
|---|---|
| Instagram feed | `3:4` (default) |
| E-commerce closeup | `1:1` |
| Pinterest | `3:4` |
| Story / TikTok | `9:16` |
| Editorial wide | `4:3` or `16:9` |

Default `3:4`.

## Composition rules

- **Product first, person second** — if the person dominates the frame, recompose
- **Product occupies 40–60% of visible area** — never less than 30%, never more than 70%
- **Rule of thirds for product placement** — never dead-center unless dramatic intent
- **Hands shown? Specify finger position** — relaxed natural grip, not stiff
- **Face partial only** — never full face, only nose-to-chin, eye area, lips, or cheek
- **Background blur supports product** — gentle bokeh, not muddy, not distracting
- **Skin texture realistic** — pores, fine hairs, natural imperfection — never airbrushed

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. A confirmed product image is
required and must be attached to every first-pass request with role `image`.
Reuse that exact reference across variants.

## Quality gates

- [ ] Product is clearly the visual anchor (40–60% of frame)
- [ ] Person is partial context, not focal subject
- [ ] Product matches reference exactly (color, design, branding)
- [ ] Anatomy correct (hands, fingers, lips, eyes — no AI distortion)
- [ ] Skin texture realistic, not plastic or airbrushed
- [ ] Lighting matches preset specification
- [ ] Sharp focus on product surface
- [ ] Known brand colors integrated
- [ ] Aspect ratio matches use case
- [ ] Prompt ends with `resolution: 2k`
