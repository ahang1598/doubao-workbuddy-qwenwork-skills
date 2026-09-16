# Mockups

Create believable applications of the Brand Lock. Preserve the approved logo and colors; do not let the scene generator invent branding.

Before planning, require only an approved logo through the Brandkit state script's `state --action get_logo` action. Read approved palette/visual axes when available or when color/application decisions need them. Require typography only when readable text must appear. Use the exact approved logo asset ID returned by state everywhere; never substitute a newer generation or a recreated mark.

Mockups are rendered images, not fully editable layered documents. If the user needs editable source artwork, use that asset's dedicated reference (for example `packaging.md` or `social-templates.md`) first.

## Plan the application from brand input

Use the approved Brand Lock, user brief, persisted visual axes, preferences, and uploaded references before choosing mockup objects, materials, framing, or art direction.

- Choose applications people in that category credibly use.
- Extract useful composition/material cues from user-provided references.
- Never recreate a reference's exact scene, layout, or branded object.

Each mockup needs one clear art-directed idea tied to this brand. “Put the logo on a generic object” is not a concept.

## Anti-slop rules

Avoid the common synthetic/generic look:

- Arbitrary gradients or neon glows unrelated to the Brand Lock
- Plastic sheen on every material
- Floating products and physically meaningless props
- Excessive bloom, haze, depth of field, or cinematic lighting
- Generic marble/pedestal “luxury” staging
- Fake microcopy, pseudo-labels, invented claims, or decorative UI
- Impossible folds, embossing, reflections, print edges, or scale
- Too many props competing with the branded surface
- Warped logos or a different visual device in every mockup

Prefer believable materials, restrained lighting, purposeful negative space, specific environments, and one focal branded application.

## Model selection

Call `canvas_image_model_list` before the first mockup and pick one model for the whole set:

- `kontext_config.max_input_images` must be at least as large as the number of references you plan
  to pass (base scene + logo + optional artwork)
- `resolution_options` should include 2K (enum `5`); prefer 4K (enum `6`) when the model offers it
- prefer the higher-quality tier over the "极速 / lite" tier

Never hardcode a model id, and never switch models inside one mockup set. Pass `quality` only when
that model returned a non-empty `infer_quality_options`.

## Ask for aspect ratio

Before submitting any mockup job, ask which ratio the user wants unless their current request already states it. Offer common supported choices such as 1:1, 4:3, 3:4, 16:9, and 9:16; validate the answer against the `aspect_ratios` the model actually returned. For several mockups, use one ratio for the set unless the user assigns ratios per item. Lock the selected ratio across every stage.

WorkRally supports `21:9 16:9 4:3 2:1 1:1 1:2 3:4 9:16` and **has no `4:5`, `2:3`, or `3:2`**. When a
platform demands one of those, generate the nearest supported ratio (`3:4` for `4:5` and `2:3`,
`4:3` for `3:2`), crop locally with ffmpeg or ImageMagick, and tell the user you cropped.

### Existing photograph

When the user explicitly supplies the exact photograph to mock up, pass it as the **first** entry of
`input_images` and the selected logo variant as the **second**, then refer to them in the prompt as
「第一张图片」and「第二张图片」. Preserve subject, camera, lighting, materials, folds, shadows,
perspective, crop, background, and selected ratio.

## Logo variant routing

Call the Brandkit state script's `state --action get_logo` action and use one of its exact approved variant assets:

- Full-color logo: smooth surfaces and production methods that credibly support accurate multicolor printing.
- Black monochrome logo: light kraft paper, natural cardboard, pale fabric, stamps, dark-ink screen printing, engraving masks, and light uncoated stock.
- White monochrome logo: dark paper, dark boxes, dark fabric, reverse marks, light-ink screen printing, and dark signage.
- Embossing, debossing, foil, laser engraving, and one-color printing always use a monochrome variant. Never send the full-color mark as the application reference for those processes.

Only after the user confirms a mockup whose physical production requires one-color/reverse artwork,
run `python3 <skill dir>/scripts/brandkit.py logo-export` with `include_monochrome: true` and the
approved color SVG when the required variant is absent — this route needs a **user-supplied official
SVG**. For a mark generated in this skill there is no SVG, so a monochrome variant is a regeneration
with a monochrome palette clause, not a deterministic derivative; say so before producing it. Never
pre-generate monochrome assets for future mockups, and never hand-edit SVG.

## Mockup prompt contract

References go in `input_images` as an ordered array of **URLs**; the prompt refers to them by
position —「第一张图片」for the first,「第二张图片」for the second, and so on. For a new scene, pass
the selected logo variant first; add approved product/artwork references after it. For an existing
photograph, the photograph is first and the logo second. State each image's role explicitly in the
prompt. Only raster image URLs are valid — never an SVG. Local files go through `upload_file` first;
`input_images` does not take local paths.

Write the prompt in Chinese. The block structure below is the contract; keep the blocks, write the
content in Chinese.

```text
[生成一张成品级品牌应用图]
<具体的物件/应用场景、可信的环境、镜头、材质、光线、构图，以及一个属于这个品牌的
明确美术想法>

[权威 logo]
<第N张图片> 是审定通过的<全彩/黑色/白色>logo。保持它的字形、剪影、几何形状、比例、
内部负空间与精确颜色不变。不要重绘、简化、裁切、拉伸、描边或添加效果。

[放置锁定]
目标表面：<具体的物件面板/表面/材质>。
位置：<精确的对齐与位置，如水平居中、上三分之一、视觉中心对齐面板>。
尺寸：logo 占目标表面的 <具体比例>，同时保留 <具体的留白边距>。
方向：对齐 <面板边缘/接缝/基线>；跟随表面透视，但不改变 logo 自身比例。
颜色：严格使用给定的 <全彩/黑色/白色> 版本，并说明它与材质/背景的对比为何成立。

[物理应用方式]
用 <可信的印刷/压凸/烫金/雕刻/油墨行为> 呈现 logo。
尊重褶皱、纹理走向、透视、遮挡、反射、尺度与制造工艺限制。

画面中没有多余的 logo、伪文字、编造的标签、变形的标志、悬浮的印刷、
不相关的道具、随意的渐变、塑料反光，也没有套路化的奢侈品摆拍。
```

The prompt must contain concrete placement, scale, alignment, clear-space, color-variant, and material-application instructions. “Place the logo on the bag/box” is insufficient.

Submit one `canvas_generate_image` call per mockup with `count: 1`, poll each `task_ids` entry with
`canvas_get_task` every 3 seconds, and reuse the finished result URL as-is; do not re-upload the
same result.

## Conditional text/detail route

If the final mockup contains any readable text—wordmark, brand name, tagline, packaging label, signage, product copy, or interface text—**do not ask the image model to render it in one pass**:

1. Generate the same-ratio scene with the target surface blank and no logo, letters, pseudo-text, or invented graphics.
2. Run a second image-to-image call: the exact base scene URL first in `input_images`, the approved logo/artwork reference second.
3. The second prompt preserves「第一张图片」's camera, crop, objects, lighting, material, folds, shadows, perspective, and background exactly.
4. State the exact literal text, logo variant, placement, scale, alignment, clear space, color, and physical print/application behavior. Keep the user's copy verbatim; never translate or paraphrase text that will be rendered.
5. Keep the ratio identical to the user-approved ratio.

**In-image text rendering quality is unverified on WorkRally.** When the text must be exact, prefer
the deterministic route: keep the surface blank and typeset the copy locally over the render (see
`typography.md` §5). Only bake text into the generation when the user explicitly asks for it, and
check the result character by character.

## Deterministic compositing

Prefer deterministic placement over generative editing when:

- The target is a flat poster, screen, card, sign, or front-facing package
- The source logo already has transparency
- No physical deformation, folds, reflections, or occlusion are required

Use image/SVG tooling to scale and place the official logo exactly. Preserve clear space and color. Add masks/perspective only when they can be controlled reliably.

Use the image model directly when the branding must interact with:

- Fabric folds
- Curved packaging
- Embossing/debossing
- Foil, print texture, reflections, or surface wear
- Occlusion and realistic perspective

If the model corrupts the logo, retry once with stronger placement, geometry, and color constraints while keeping the same references and the same model. If it fails again, stop and use deterministic compositing when possible.

## Mockup-specific guidance

### Packaging

- Use the actual dieline/package proportions when supplied.
- Preserve material, closure, label area, and required legal/copy regions.
- Do not invent claims, ingredients, certifications, or regulatory text.

### Apparel/merch

- Use the image model for the finished branded person/garment mockup.
- Define print/embroidery location, size, and material behavior.
- Preserve the person and garment between variants.

### Signage/environment

- Respect viewing distance, perspective, mounting, and lighting.
- Use the correct approved logo version for background contrast.

### Device/screen

- Treat the screen graphic as a separate editable asset from its dedicated module when possible, then composite it into the device.
- Do not ask GPT to invent interface copy that should be exact.

## Variant discipline

For several mockups:

- Lock one base scene per mockup family.
- Vary only the requested application or colorway.
- Keep camera, lighting, material, and composition fixed for comparison sets.
- Do not generate a new person or environment for every colorway.

## Mockup QA

- Official logo matches the reference exactly
- No misspelling, extra glyph, warped geometry, or invented mark
- Correct colorway and sufficient contrast
- Physical application follows folds/perspective/material
- No floating print, impossible reflections, or duplicated graphics
- One brand-specific art-directed idea; not a generic logo-on-object scene
- Materials, props, lighting, and setting are credible for the industry
- No arbitrary gradients, plastic sheen, bloom, fake microcopy, or generic luxury staging
- When an existing photograph was supplied, every non-target scene element is unchanged
- Product/package proportions match supplied references
- All mockups use the same Brand Lock
- Rendered output is clearly labeled as non-editable unless a separate editable overlay/template is also delivered

After QA, ask the user to approve the final mockup or set. Only then save it with the Brandkit state script's `approve_brandbook_element` action and `required_slots: ["logo"]`; add palette/typography only when the mockup actually used them. Generated or model-praised mockups are drafts until that approval.
