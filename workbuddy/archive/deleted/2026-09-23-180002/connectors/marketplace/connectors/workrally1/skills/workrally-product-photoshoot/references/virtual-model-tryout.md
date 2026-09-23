# Mode: virtual-model-tryout

Fashion-grade product imagery where a product is worn or used by an AI-rendered model. Replaces the cost of a fashion shoot for DTC brands selling clothing, accessories, jewelry, eyewear, watches, bags, hats, footwear.

## What this mode does (and does NOT do)

**Does**: Renders a fresh AI model wearing or using the product in a fashion-shoot context, controlled by detailed prompt description (model demographics, pose, expression, environment).

**Does NOT**: Train an identity. Does not remember a model between generations. Does not use Soul ID. Every generation describes the model from scratch through the prompt.

This means: each batch of images can show the same "type" of model (e.g. "woman in late twenties, dark hair, athletic build") but they will not be the literal same person.

## Try-Out Presets

| Preset | Use for | Visual signature |
|---|---|---|
| `studio-clean` | E-commerce catalog, on-model main image | Seamless backdrop, soft frontal lighting, neutral pose |
| `editorial-fashion` | Lookbook, campaign, magazine-style | Atmospheric environment, dramatic pose, dynamic lighting |
| `street-style` | Casual brands, urban DTC | Real city environment, candid pose, natural daylight |
| `outdoor-natural` | Outdoor, athleisure, lifestyle brands | Forest, beach, mountain, golden hour, natural pose |
| `home-lifestyle` | Loungewear, sleepwear, home goods on body | Cozy interior, relaxed pose, warm lamp light |
| `closeup-detail` | Jewelry, watches, eyewear, beauty on body part | Tight crop on product area, shallow DoF |
| `runway-style` | Fashion-forward editorial | Studio runway feel, dramatic lighting, confident pose |
| `flat-lay-on-body` | Top-down view of body wearing product | Aerial view of body with product, on a flat surface |

## Prompt Template

```
[PRODUCT]
{{Exact product description from reference or known conversation context}}, worn / displayed on the model's {{specific body area}}.

[MODEL]
{{Detailed model archetype: gender presentation, approximate age range, ethnicity if specified, hair color/style, build, height implied, skin tone}}. Natural realistic features, anatomically correct, professional model proportions.

[POSE]
{{Specific pose: standing three-quarter, walking confident, leaning, sitting, action pose, candid moment}}. {{Hand positions}}, {{eye direction}}, {{expression}}.

[FRAMING]
{{Full body / three-quarter / waist-up / closeup on product area}}, {{rule of thirds placement}}.

[ENVIRONMENT]
{{Specific backdrop or location per preset}}.

[WARDROBE / STYLING]
{{What else the model is wearing besides the product — neutral coordinated wardrobe / fashion-forward layered / minimal}}, complementing the featured product without competing.

[LIGHTING]
{{Specific lighting setup — see Lighting Setups below}}. {{Direction, quality, color temp}}. {{Skin highlight behavior}}.

[LENS & CAMERA]
Shot on {{50mm natural / 85mm portrait / 35mm environmental}}, aperture {{f/2.8 to f/5.6}}, sharp focus on {{product area}}, depth of field {{shallow / medium}}.

[SKIN & DETAIL]
Realistic skin texture with natural pores, no smoothing, no plasticity. Hair has individual strand detail. Hands and fingers anatomically correct.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 matching fashion entries in photographer-references.md}}. Editorial fashion photography. Never include the source names.

[PRODUCT FIDELITY DIRECTIVE]
The product must remain identical to the reference — same color, material, design details, proportions, branding placement. The model wears it without altering it.

[QUALITY MARKERS]
Magazine-cover quality, hyper-realistic, professional fashion photography standard.

[AVOID]
{{universal + anti-uncanny + anti-text-warp}}
no clothing items that fight the featured product, no oversexualized poses,
no warped product geometry, no altered product color.

resolution: 2k
```

## Photographer references

- **studio-clean**: Mert & Marcus, Sølve Sundsbø, Steven Klein
- **editorial-fashion**: Tim Walker, Mert & Marcus, Steven Meisel
- **street-style**: Sandra Semburg, Phil Oh, Adam Katz Sinding
- **outdoor-natural**: Cass Bird, Jamie Hawkesworth, Ryan McGinley
- **home-lifestyle**: Petra Collins, Cass Bird, Jamie Hawkesworth
- **closeup-detail**: Sølve Sundsbø, David Sims, Mert & Marcus
- **runway-style**: Steven Meisel, Mert & Marcus, Inez & Vinoodh
- **flat-lay-on-body**: Charlie Engman, Petra Collins, Wolfgang Tillmans

## Lighting Setups

- **studio-clean**: Large softbox key 45° camera-left, fill bounce camera-right, hair light, 5500K, even soft shadow
- **editorial-fashion**: Single hard key with gel or grid, deep shadow, dramatic separation, 4500-5500K
- **street-style**: Available daylight with reflector fill, 5000K, candid feel
- **outdoor-natural**: Golden hour backlight with reflector fill, 4500K mixed warm, atmospheric haze
- **home-lifestyle**: Window light with practical lamp fill, 3500K warm, soft cozy
- **closeup-detail**: Beauty dish or soft directional, narrow DoF, sharp catchlight, 5500K
- **runway-style**: Strong key with rim, slight haze, dramatic falloff, 5000K
- **flat-lay-on-body**: Even soft top-down lighting, minimal shadow, 5000K neutral

## Body and pose anatomy rules

Critical for avoiding AI uncanny output:

- **Hands**: specify finger position explicitly — "relaxed fingers loosely curled at side", "hand on hip with thumb out", "hand holding strap with natural grip"
- **Feet**: specify shoe and ground contact — "feet planted shoulder-width, weight on back leg"
- **Face**: specify eye direction and expression — eyes in the wrong direction is the most common tell
- **Posture**: specify spine curve and shoulder placement — natural posture not stiff
- **Proportions**: prompt for "natural human proportions, anatomically correct"

## Product fidelity rules

The product is the hero. The model is the canvas:

- Pass the product reference image whenever possible
- Explicitly state in prompt: "product remains identical to reference — preserve color, texture, branding, design details"
- For closeups, framing should clearly show the product without being obscured
- For wide shots, product still needs to be visible and identifiable

## Aspect Ratio

| Use case | Ratio |
|---|---|
| E-commerce on-model main | `3:4` |
| Lookbook editorial | `3:4` or `3:4` |
| Instagram feed | `3:4` |
| Pinterest | `3:4` |
| Story / TikTok | `9:16` |
| Wide editorial | `16:9` |

Default `3:4`.

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. A confirmed product image is
required and must be reused across every first-pass variant.

## Quality gates

- [ ] Product matches the reference exactly (color, design, branding)
- [ ] Model anatomy is correct (hands, fingers, face symmetry)
- [ ] Pose is natural and brand-appropriate
- [ ] Skin texture is realistic, not plastic
- [ ] Lighting matches preset specification
- [ ] Wardrobe complements the product, doesn't compete
- [ ] Framing showcases the product clearly
- [ ] Aspect ratio matches use case
- [ ] Prompt ends with `resolution: 2k`
