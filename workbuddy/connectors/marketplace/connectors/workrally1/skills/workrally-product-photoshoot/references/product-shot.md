# Mode: product-shot

Studio-quality product photography on neutral, seamless, or controlled backgrounds. Catalog images, packshots, e-commerce listings.

## Style Presets

| Preset | Use for | Visual signature |
|---|---|---|
| `clean-studio` | Universal e-commerce, Shopify, catalog | Seamless white-to-light-grey gradient, soft frontal key, minimal shadow |
| `dramatic-studio` | Premium brands, hero shots, fragrance, electronics | Hard rim light, deep shadows, single light source, moody backdrop |
| `minimal-design` | Modern DTC, clean aesthetic brands | Pastel or single-color seamless, geometric simplicity, high negative space |
| `etsy-handmade` | Handcrafted goods, artisan products, small batch | Warm natural light, linen / wood / stone surfaces, organic shadow |
| `luxury-editorial` | High-end fashion, jewelry, perfume | Polished surface reflections, marble or velvet, jewel-tone backdrop |
| `vibrant-color` | Beauty, food packaging, lifestyle DTC | Saturated solid background, bold color blocking, modern flat composition |
| `floating-product` | Hero shots, dramatic display, suspended product | Product appears suspended mid-air, motion blur on accents, surreal staging |
| `ingredient-flatlay` | Beauty, food, supplements showing what's inside | Top-down composition with raw ingredients arranged around product |

## Prompt Template

```
[SUBJECT]
Hero shot of {{exact product description from reference or user input}}, {{material/finish details}}, {{label/branding visible if applicable}}.

[COMPOSITION]
{{Camera angle}}, {{framing}}, {{rule-of-thirds placement}}, {{negative space directive}}.

[LIGHTING]
{{Lighting setup with direction and quality from photography-vocabulary.md}}. {{Color temperature in Kelvin}}. {{Shadow behavior}}.

[LENS & CAMERA]
Shot on {{focal length}} lens, aperture {{f-stop}}, {{depth of field directive}}, sharp focus on {{specific area}}.

[MATERIALS & TEXTURE]
{{Surface treatments}}, {{reflections}}, {{micro-details}}.

[COLOR PALETTE]
Dominant tones: {{2-3 colors aligned with known brand context}}. {{Contrast directive}}.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 matching entries in photographer-references.md}}. Commercial product photography, magazine editorial quality. Never include the source names.

[BRAND INTEGRATION]
{{Known brand colors}}, {{brand mood — clean / warm / edgy / refined}}.

[QUALITY MARKERS]
Tack-sharp, hyper-detailed, photorealistic, commercial-grade.

[AVOID]
{{universal + anti-text-warp from negative-prompts.md}}

resolution: 2k
```

## Photographer references (pick from photographer-references.md)

- **clean-studio / minimal-design**: Carl Kleiner, Aaron Tilley, Bobby Doherty
- **dramatic-studio / luxury-editorial**: Irving Penn, Sølve Sundsbø, Hugh Kretschmer
- **etsy-handmade**: Linda Pugliese, Beth Kirby, Aubrie Pick
- **vibrant-color**: Bobby Doherty, Maciek Jasik, Kyle Bean
- **floating-product**: Aaron Tilley, Hugh Kretschmer, Carl Kleiner
- **ingredient-flatlay**: Carl Kleiner, Linda Pugliese, Brittany Ambridge

## Aspect Ratio

| Use case | Ratio |
|---|---|
| Shopify / catalog main | `1:1` |
| IG e-commerce post | `3:4` |
| Web product page hero | `3:4` or `3:4` |
| Pinterest-friendly | `3:4` |
| Wide editorial | `16:9` |

Default `1:1` if unspecified.

## Quality gates

- [ ] Product recognizable, matches reference if provided
- [ ] Lighting has clear direction and quality, not flat
- [ ] Shadows physically plausible
- [ ] Label / text on product is sharp and unwarped
- [ ] No AI artifacts on edges or reflections
- [ ] Background intentional, not muddy
- [ ] Color palette aligns with known brand context
- [ ] Prompt ends with `resolution: 2k`

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. Use the aspect ratio selected by
the rules above and keep one stable index per requested variant.
