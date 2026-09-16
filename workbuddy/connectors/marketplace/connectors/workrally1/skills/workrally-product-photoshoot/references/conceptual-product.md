# Mode: conceptual-product

Surreal, CGI-style, premium product imagery — levitating products, frozen splashes, sculptural arrangements, abstract compositions. Used by premium DTC, fragrance, beauty, tech, and luxury brands.

## Why this is its own genre

Standard `product-shot` is realistic photography. This mode is **deliberately unreal**:
- Product defies gravity (floating, suspended, levitating)
- Motion is frozen in impossible ways (splash mid-air, droplet hanging)
- Composition is sculptural and geometric, not naturalistic
- Lighting is dramatic and stylized, not documentary
- CGI-render aesthetic without losing photorealistic detail
- Premium positioning — this look signals "expensive product"

## Conceptual Presets

| Preset | Use for | Visual signature |
|---|---|---|
| `levitating-suspended` | Fragrance, skincare, tech, luxury goods | Product floating mid-air, soft shadow below, clean background |
| `splash-frozen-motion` | Beverages, cleansers, oils, water-based products | Liquid frozen in mid-air burst around product, dramatic motion |
| `abstract-cgi-render` | Premium DTC, fragrance, tech, jewelry | Hyper-clean studio CGI look, surreal materials (marble, chrome, liquid metal) |
| `sculptural-arrangement` | Beauty, supplements, food, premium goods | Products stacked or arranged as geometric sculpture, architectural feel |
| `liquid-pour-suspension` | Beauty oils, fragrances, food oils, sauces | Liquid pouring from product frozen mid-air in elegant ribbon shape |
| `broken-deconstructed` | Beauty, food, supplements, fragrance | Product disassembled or "exploded view" with ingredients/components floating around |
| `floating-elements` | Beauty, food, beverages, premium goods | Decorative elements (petals, leaves, crystals, fabric, citrus) suspended around product |
| `surreal-environment` | Premium fragrance, fashion, conceptual brands | Product in impossible environment — clouds, water surface, mirrored room, infinity space |
| `geometric-pedestal` | Fragrance, jewelry, watches, electronics | Product on minimal geometric pedestal with dramatic single-source light |
| `chrome-liquid-metal` | Tech, fragrance, fashion accessories | Product on or beside chrome / liquid metal / mirror surfaces with reflection play |

## Prompt Template

```
[CONCEPT]
{{Conceptual preset description in 1-2 sentences. State explicitly that the composition is surreal / impossible / CGI-rendered photorealism — not documentary photography.}}

[PRODUCT]
{{Exact product description from reference or known conversation context}}, {{material/finish details}}, {{label/branding visible}}, sharp realistic detail despite the surreal context.

[COMPOSITION]
{{Geometric / sculptural / floating / suspended composition}}, {{specific surreal element — frozen droplet / suspended liquid / impossible angle / floating decor}}, dramatic visual hierarchy.

[PHYSICS DEFIANCE]
{{Specific defiance of natural physics — product floating with no visible support / liquid suspended in air with no fall / objects arranged impossibly / shadow that doesn't match light source for stylization}}.

[LIGHTING]
{{Dramatic stylized lighting — see Lighting Setups below}}. {{Hard direction with controlled shadow / single source / multi-light geometric}}. Color temp {{usually 5000-5500K cool clean}}. Sharp catchlights on glass, metal, liquid.

[BACKGROUND & ENVIRONMENT]
{{Clean studio gradient / abstract surreal environment / geometric backdrop / infinity space}}. Background supports the surreal feel without competing with product.

[MATERIALS & TEXTURES]
{{Marble, chrome, liquid metal, polished glass, water, smoke, satin, velvet — pick textures that elevate premium feel}}. Hyper-realistic surface detail.

[LENS & CAMERA]
Shot on {{50mm clean / 85mm portrait / 100mm macro for detail work}}, aperture {{f/8 to f/11 for deep DoF in sculptural / f/2.8 for selective focus}}, sharp focus throughout product, photorealistic CGI-render quality.

[COLOR PALETTE]
{{2-3 dominant tones aligned with known brand context}}. {{High contrast for premium feel / monochromatic for elegance / single accent against neutral}}.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 matching entries in photographer-references.md}}. Premium conceptual product photography, CGI-render aesthetic, editorial commercial standard. Never include the source names.

[BRAND INTEGRATION]
{{Known brand colors and mood — premium / refined / experimental / luxury}}.

[QUALITY MARKERS]
Hyper-realistic CGI quality, magazine editorial standard, tack-sharp surface detail, dramatic lighting precision, premium commercial photography.

[AVOID]
{{universal + anti-text-warp}}
no cartoonish render, no obvious AI tells, no plastic look on product,
no half-committed surreal — fully surreal or fully realistic, never in-between,
no cluttered composition, no random floating objects without intent,
no logos or text other than the product's own branding,
no warped product geometry, no melted product details.

resolution: 2k
```

## Photographer references

These photographers define the conceptual / surreal commercial product genre:

- **levitating-suspended / abstract-cgi**: Aaron Tilley, Hugh Kretschmer, Dan Tobin Smith
- **splash-frozen-motion / liquid-pour**: Aaron Tilley, Hugh Kretschmer, Sølve Sundsbø
- **sculptural-arrangement / geometric-pedestal**: Carl Kleiner, Bobby Doherty, Dan Tobin Smith
- **broken-deconstructed**: Carl Kleiner, Hugh Kretschmer, Aaron Tilley
- **floating-elements / surreal-environment**: Tim Walker, Aaron Tilley, Hugh Kretschmer
- **chrome-liquid-metal**: Aaron Tilley, Maciek Jasik, Dan Tobin Smith

## Lighting Setups

- **levitating-suspended**: Single soft key from above-front 45°, deep shadow background, soft contact shadow under floating product, 5000K
- **splash-frozen-motion**: Hard strobe with high-speed freeze, multiple flashes for splash separation, 5500K daylight, sharp shadow definition
- **abstract-cgi-render**: Multi-source studio lighting with controlled bounce, even key with rim separation, 5500K clean daylight, mirror-like reflections
- **sculptural-arrangement**: Single dramatic key with grid, deep architectural shadow, 5000K, monumental feel
- **liquid-pour-suspension**: Hard backlight to define liquid, rim separation, 5000K, freeze every droplet sharp
- **broken-deconstructed**: Even soft top-down lighting, minimal shadow, 5500K, clinical clarity
- **floating-elements**: Soft directional key with multiple subtle fills, 4500K, ethereal feel
- **surreal-environment**: Lighting motivated by impossible source — glow from inside subject, light from below, refracted color through liquid, 5000K cool
- **geometric-pedestal**: Single hard key with strong shadow, museum-style precision, 5000K
- **chrome-liquid-metal**: Soft dome lighting for clean reflection control, 5500K daylight, sharp specular highlights

## Aspect Ratio

| Use case | Ratio |
|---|---|
| Editorial / hero / catalog premium | `1:1` |
| Magazine-style portrait | `3:4` |
| Instagram feed | `3:4` |
| Pinterest | `3:4` |
| Story / TikTok premium | `9:16` |
| Wide editorial / banner | `16:9` |

Default `1:1` for conceptual standalone, `3:4` for editorial use.

## Composition principles for conceptual mode

- **Commit to the surreal** — half-applied surreal looks worse than realistic. Either fully levitate, fully splash, fully sculptural — never partially.
- **Negative space is intentional** — unlike text-overlay zones, conceptual mode uses negative space for premium feel and dramatic isolation. This is different from "reserved text space".
- **Sharp product detail despite surreal context** — the product itself must remain photorealistic and crisp; only the staging is unreal.
- **Limit floating elements** — 1 main surreal element (the product floating) plus 2–4 supporting elements (droplets, petals, geometry). More than that = clutter.
- **Geometry matters** — conceptual mode rewards geometric composition (triangles, golden ratio, symmetry, repetition).

## Brand fit guidance

Conceptual mode is **not for every brand**. Strong fit:
- Premium fragrance and beauty
- Luxury watches, jewelry
- Tech with premium positioning (audio, devices)
- Editorial fashion accessories
- High-end DTC (skincare, supplements, food)

Weak fit:
- Casual everyday CPG
- Budget / value brands
- Bohemian / handcrafted aesthetics
- Warm rustic brands

If known brand context indicates warm / rustic / handcrafted positioning, suggest `lifestyle-scene` or `product-shot` instead — conceptual will fight the brand.

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. Attach one confirmed product
reference to every first-pass request when available; for a sufficiently exact
text description, omit `medias` and use text-to-image.

## Quality gates

- [ ] Composition is fully surreal / committed (not half-realistic)
- [ ] Product detail is sharp and photorealistic despite the surreal staging
- [ ] Product matches reference (color, design, branding) exactly
- [ ] Lighting is dramatic and intentional, not flat
- [ ] No clutter — surreal elements are limited and intentional
- [ ] Premium feel achieved — composition signals expensive
- [ ] Known brand colors integrated
- [ ] Aspect ratio matches use case
- [ ] Prompt ends with `resolution: 2k`
