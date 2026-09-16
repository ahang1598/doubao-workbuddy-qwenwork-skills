# Brandkit logo prompt enhancer

The final prompt-construction layer between Brandkit Design Brain and `canvas_generate_image`. There is no server-side enhancer tool: **you apply this contract yourself**, exactly once per Design Brain candidate, converting one structured logo-candidate specification into one precise prompt with the highest possible first-pass success rate.

WorkRally has no vector model, so the target is a **flat vector-*looking* raster image**: crisp
edges, solid fills, no photographic language. Write the prompt in Chinese; the WorkRally models are
Chinese-first.

Design Brain has already made the creative decisions. Do not replace, reinterpret, broaden, or add a second concept. Do not narrate this step to the user.

## Input contract

Assemble one structured candidate specification per mechanism before writing its prompt:

```json
{
  "brand_context": {
    "name": "context only; never render it",
    "offering": "...",
    "industry": "...",
    "positioning": "...",
    "audience": "...",
    "values": ["..."]
  },
  "visual_axes": {
    "restrained_expressive": 50,
    "geometric_organic": 50,
    "familiar_experimental": 50
  },
  "candidate": {
    "mark_type": "lettermark_monogram | pictorial | abstract | mascot | emblem",
    "central_idea": "...",
    "visual_mechanism": "...",
    "distinctive_element": "specific silhouette, negative-space device, motif treatment, or unexpected locked color pairing",
    "shape_logic": "...",
    "treatment": "flat_vector | monoline | vector_gradient | hand_drawn_vector",
    "style_register": "...",
    "user_style_directive": "explicit user-requested style, or null",
    "composition": "..."
  },
  "palette": {
    "count": "1, 2, or 3 as required by the locked concept; greater only when user_requested_more_than_three is true",
    "user_requested_more_than_three": false,
    "roles": ["primary", "accent", "background"]
  },
  "reference_signals": ["formal qualities only"],
  "forbidden_elements": ["..."]
}
```

Treat supplied creative decisions as authoritative. If a nonessential detail is missing, infer the smallest sensible default without changing the central idea.

## Output contract

The result of this step is exactly one continuous enhanced prompt string per candidate — no bullet points inside the prompt, no explanation, no debug text.

The prompt must follow this order:

mark type → central subject/mechanism → shape logic → style register → palette behavior → composition → constraint tail

Every clause must materially affect the drawing.

The central subject/mechanism portion must state exactly one visual idea in one clause. Do not add a second metaphor, alternative, “and/or” construction, or hybrid concept.

## Stage boundary — symbol only

This flow creates a symbol/mark before typography selection.

Never include:

- brand name
- wordmark
- tagline
- descriptor
- invented letters
- any other readable words

The only exception is a lettermark/monogram candidate: the explicitly supplied initials inside `candidate.visual_mechanism` are permitted. For lettermarks and monograms, “no text” means no additional words, taglines, descriptors, or unrelated lettering.

Every candidate constraint tail must include the literal phrase `无文字`. It does not need to be the final phrase.

## Mark type

Preserve `candidate.mark_type` exactly.

Allowed types:

- lettermark_monogram — explicitly supplied initials or interwoven letterforms
- pictorial — one recognizable literal object
- abstract — a concept rendered as nonrepresentational geometry
- mascot — one character/creature with a clear scalable expression
- emblem — a text-free symbol contained within a badge/seal boundary

If `mark_type` is unexpectedly missing, infer it from `visual_mechanism`. Default to abstract, never wordmark or combination mark.

## Treatment

Preserve `candidate.treatment` exactly.

Preserve `candidate.style_register` and `candidate.user_style_directive`. When the user supplied a particular style, name that formal style directly in the prompt and translate it into compatible drawing decisions. Do not dilute it into a generic “modern,” “minimal,” or “premium” treatment. Live brand/designer references remain subject to REFERENCE SAFETY below.

- **flat_vector:** Solid fills, clean SVG paths, no surface effects.
- **monoline:** Uniform stroke weight, rounded caps, no fills.
- **vector_gradient:** Vector-safe linear, radial, or duotone gradient with the locked stop count.
- **hand_drawn_vector:** Allowed only when supplied explicitly. Preserve intentional stroke variation and a clear silhouette. Do not promise minimal anchor points.

Dimensional/3D treatment is forbidden.

## Structural priorities

Define:

1. one dominant unified silhouette
2. concrete geometric or organic construction logic
3. symmetry or intentional asymmetry
4. positive and negative-space behavior
5. stroke/fill behavior
6. internal detail limit
7. small-size scalability
8. centered isolated presentation

Prefer one coherent mechanism over several decorative ideas.

## Distinctiveness and complexity floor

Every enhanced prompt must contain at least one concrete distinctive element:

- a specifically described silhouette
- a specific negative-space device
- a particular motif treatment
- an unexpected but locked color-role pairing

Generic adjectives do not satisfy this requirement. “Simple,” “clean,” and “minimal” are allowed only when the prompt also defines an ownable construction decision. Never return a generic swoosh, blob, orbit, shield, spark, leaf, letter-in-circle, or interchangeable startup symbol without a brief-specific mechanism.

Describe the distinctive element concretely enough that another designer could sketch its structure without guessing.

Preserve `candidate.distinctive_element` and make it explicit in the prompt.

## One concept per logo

The prompt must express one central visual idea only. Never physically merge, morph, or fuse two metaphors (for example, cloud + mountain, leaf + flame, or letter + animal) unless the user's own request explicitly describes that exact fusion. A single motif may use negative space or geometric transformation; that does not authorize adding a second symbolic subject.

## Visual axes

Translate axes into drawing decisions:

- `restrained_expressive` controls intensity, contrast, and detail density
- `geometric_organic` controls construction, curves, and regularity
- `familiar_experimental` controls category recognition and novelty

Do not print values or mention axes in the output.

## Palette

The palette is locked. Do not invent, replace, expand, or reinterpret it.

Use one, two, or three colors according to the locked concept; three is a maximum, not a target or default. Never add colors merely to reach three. Count the background when it participates visually. More than three are allowed only when `palette.user_requested_more_than_three` is true. Never infer that exception from a colorful reference or industry convention.

`canvas_generate_image` has no color parameters, so the locked hex values **must appear in the
prompt**, once, as a single closing palette clause with explicit roles — for example
`配色锁定：主色 #101820，强调色 #00AEEF，背景 #FFFFFF，只用这三种颜色`. Do not scatter color codes
through the prose, do not add Pantone/CMYK notation, and do not introduce a color that is not in the
locked subset.

State:

- strict color count
- role relationships
- solid or gradient behavior
- background relationship

Use role language such as “locked primary tone,” “locked accent,” and “locked background.” Do not invent color names that were not supplied.

## Reference safety

Never output a live brand, studio, artist, or designer name.

Translate `reference_signals` into formal qualities only: geometry, contrast, density, rhythm, form register, material impression, energy.

Never reproduce a reference’s logo mechanism, distinctive shape, composition, or artwork.

## Vector language

For flat_vector, monoline, and vector_gradient, never use: lens, camera, lighting, depth of field, photorealistic, cinematic, material rendering, grain, paper texture, shadows, mockup, scene.

Define drawing logic, not presentation photography.

## Constraint tails

Write the tail in Chinese, matching the rest of the prompt. The intent is unchanged: force flat,
traceable shapes with no photographic treatment.

- **flat_vector:** `扁平矢量风格，边缘干净锐利，纯色填充，无阴影，无材质，无文字，形状简洁、轮廓数量少，居中构图，纯色背景。`
- **monoline:** `单线条矢量风格，线宽均匀，圆头线帽，不做填充，无阴影，无材质，无文字，形状简洁、轮廓数量少，居中构图，纯色背景。`
- **vector_gradient:** `扁平矢量风格，只使用指定的锁定渐变，无阴影，无材质，无文字，形状简洁、轮廓数量少，居中构图，纯色背景。`
- **hand_drawn_vector:** `手绘矢量笔触，保留刻意的笔画粗细变化，剪影清晰可缩放，无阴影，无文字，居中构图，纯色背景。`

Every tail must contain the literal phrase `无文字` (this is the Chinese form of the mandatory
“no text” constraint).

## Forbidden elements

Honor every `forbidden_elements` entry literally. Never replace one forbidden cliché with another generic symbol.

## Silent validation

Before submitting each generation request, silently verify:

- prompt follows the supplied `central_idea` and `visual_mechanism`
- central mechanism is one visual idea stated in one clause
- no metaphors are fused unless the user explicitly requested that exact fusion
- `mark_type` and `treatment` are unchanged
- explicit user style is present and not generalized away
- there is one coherent mechanism
- at least one concrete distinctive element clears the complexity floor
- no brand/designer names appear
- no words appear except explicitly permitted monogram initials
- the phrase `无文字` appears in the constraint tail
- the locked hex values appear exactly once, in the closing palette clause, with roles
- palette uses at most three colors unless the explicit user override is true
- palette is not padded with unnecessary colors
- palette count and role behavior are strict
- geometry stays simple enough that the raster result could be traced as vector later
- forbidden elements are absent
- no camera or unsupported texture language appears

If any check fails, rewrite the prompt before submitting it.
