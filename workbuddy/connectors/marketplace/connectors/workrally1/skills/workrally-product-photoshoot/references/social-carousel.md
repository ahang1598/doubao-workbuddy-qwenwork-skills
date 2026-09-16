# Mode: social-carousel

3–10 connected slides for Instagram, LinkedIn, or Facebook where each slide is part of one connected narrative — not a set of unrelated images.

## Why carousels are their own genre

A carousel must:
- Maintain identical visual system across all slides (palette, surface, lighting, composition rules)
- Have a clear narrative arc — hook → body → payoff/CTA
- Carry visual continuity (color, surface, spacing) so swipes feel intentional

Generic single-image generation does not produce this — this mode orchestrates the slide sequence as one design problem.

## Carousel Presets

| Preset | Use for | Slide structure |
|---|---|---|
| `product-launch` | New product reveal, DTC launches | Hook → reveal → benefit 1 → benefit 2 → social proof → CTA |
| `educational-tips` | "5 mistakes", "7 tips", how-to | Hook → tip 1 → tip 2 → … → summary/CTA |
| `before-during-after` | Transformation, process, results | Before → step 1 → step 2 → step 3 → after → CTA |
| `list-roundup` | Gift guides, product roundups, curated picks | Cover → item 1 → item 2 → … → CTA |
| `storytelling-narrative` | Brand story, founder story, values | Hook → setup → conflict/insight → resolution → CTA |
| `comparison` | This vs that, options breakdown | Hook → option A → option B → comparison → recommendation |
| `feature-deep-dive` | Single product, multiple feature shots | Hero → feature 1 → feature 2 → in-use → CTA |
| `process-walkthrough` | How a product is made / how a service works | Hook → step 1 → step 2 → step 3 → step 4 → final |

## Visual System (FIXED across slides)

Before generating the first slide, lock these specifications. Every slide uses these exact values. **This is what creates carousel coherence.**

```
[VISUAL SYSTEM — applies to all slides]

Palette: {{2-3 dominant tones from known brand context}}
Surface/backdrop: {{specific texture or color used across slides — linen, marble, paper, painted wall, gradient}}
Lighting: {{exact lighting setup repeated on every slide — direction, quality, Kelvin}}
Camera height/angle: {{45° / top-down / eye-level — pick one and lock it}}
Composition rule: {{rule of thirds / centered / asymmetric off-center — lock it}}
Style reference: {{concrete craft descriptors extracted from 2-3 matching photographer entries — same on every slide; never include their names}}
```

## Per-slide Prompt Template

For each slide, repeat the visual system block, then add slide-specific content:

```
[VISUAL SYSTEM]
{{Locked specifications copied verbatim into every slide prompt}}

[SLIDE {{N}} of {{TOTAL}}: {{Slide title from outline}}]

[CONTENT]
{{Specific content for this slide — what's shown, framed, emphasized}}.

[COMPOSITION VARIATION]
{{How this slide's framing differs while staying within the locked composition rule}}.

[QUALITY MARKERS]
Magazine quality, hyper-detailed, photorealistic, slide {{N}} of a connected carousel — must match visual system of slides 1-{{N-1}}.

[AVOID]
{{universal + anti-stock-feel}}
no inconsistent palette across slides, no varying lighting between slides,
no different surfaces between slides, no broken visual continuity.

resolution: 2k
```

## Typography handling per slide

If user provided concrete text for any slide (e.g. "Slide 1 should say 'New Collection'") — see Case 1 in `references/typography.md`.
If user said they'll add text later — see Case 2 in `references/typography.md` (apply consistently across all slides).
Otherwise — compose freely.

## Slide outline (do this FIRST)

Before any generation, draft a slide-by-slide outline. Example for 5-slide product launch:

```
Slide 1: Hook — product hero shot with intrigue
Slide 2: Reveal — clean product shot, full visibility
Slide 3: Key benefit 1 — product detail closeup
Slide 4: Key benefit 2 — product in use, hands holding, lifestyle moment
Slide 5: CTA — product hero with strong final composition
```

Confirm with the user before generating.

## Photographer references for consistency

Pick ONE consistent style reference set for the entire carousel — same set across all slides, never mix.

- **Lifestyle / DTC**: Linda Pugliese, Aubrie Pick, Beth Kirby
- **Product / clean**: Carl Kleiner, Aaron Tilley, Bobby Doherty
- **Editorial / fashion**: Cass Bird, Tim Walker, Mert & Marcus
- **Beauty**: Sølve Sundsbø, Mert & Marcus, Aubrie Pick
- **Food / beverage**: Linda Pugliese, Christopher Testani, Aaron Tilley
- **Tech / modern**: Spencer Lowell, Aaron Tilley, Joe Pugliese

## Aspect Ratio

| Platform | Ratio |
|---|---|
| Instagram (preferred) | `3:4` |
| Instagram (legacy) | `1:1` |
| LinkedIn (preferred) | `1:1` |
| Facebook | `1:1` or `3:4` |
| TikTok carousel | `9:16` |

Default `3:4` for IG, `1:1` for LinkedIn.

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. Give every slide a stable index
and repeat the locked visual-system block in each prompt. Keep those indices
through refinement so the user can target a slide later.

## Refinement for carousels

When visual inspection is available, audit slides as a SET first, then individually:

1. Lay out all slides side by side mentally — does palette feel continuous?
2. Is lighting direction the same on every slide?
3. Does the surface/backdrop carry through?
4. Does the narrative arc work in order?

If a single slide breaks the system, regenerate ONLY that slide referencing the visual system. Do not regenerate the whole carousel.

## Quality gates

- [ ] All slides share identical palette
- [ ] All slides share identical lighting direction and quality
- [ ] All slides share identical surface / backdrop
- [ ] Narrative arc follows the chosen preset
- [ ] No slide breaks the visual system
- [ ] All slides at the same aspect ratio
- [ ] Brand colors integrated throughout
- [ ] Typography (if any) renders correctly per the three-case rule
- [ ] Prompt ends with `resolution: 2k`
