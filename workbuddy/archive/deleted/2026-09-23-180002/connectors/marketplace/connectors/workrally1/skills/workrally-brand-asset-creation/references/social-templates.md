# Social media graphics

Create once the slots used by the requested social graphic are approved.

## Required question

Require approved logo and palette for branded no-text graphics. Add approved typography only when readable text appears. Read those modules separately; never force typography for a no-text post.

Before generation, ask once for:

- Platform, aspect ratio, and number of outputs
- Exact text that must appear; “no text” is a valid answer
- Visual mode:
  - plain branded background/poster
  - mockup photography/application
- Any supplied photography or product assets

Preserve copy verbatim. Never invent sale language, CTA, claims, prices, contact details, or placeholder copy.

## Output contract

Social-media deliverables are flattened PNG/JPG graphics, not editable templates. Never promise or create PPTX, SVG, PSD, Figma, Canva, or layered files for this module.

Supported modules:

- square post (`1:1`)
- vertical feed post — WorkRally has **no `4:5`**; generate `3:4` and crop to 4:5 locally when the
  platform demands it, telling the user you cropped
- `9:16` story
- carousel cover/body/CTA cards
- channel banner/cover (`16:9`, or `21:9` for an ultra-wide header)

## Text route (decide before generating)

**In-image text rendering has not been validated on WorkRally.** Default to the deterministic route
and only bake text into the generation when the user explicitly asks for it.

### Deterministic route (default)

1. Generate the branded background/scene **without any copy** — the prompt ends with
   `画面中没有任何文字、标签或水印。`
2. Typeset the exact copy locally over that render with the approved fonts: an SVG or HTML layer
   rasterized with `rsvg-convert` / ImageMagick, or a full-page Playwright screenshot of an HTML
   layout. This gives real letterforms, exact copy, and zero regeneration cost.
3. Deliver the flattened PNG/JPG. Keep the layout source next to it so a copy change is a re-render,
   not a regeneration.

State plainly which route you used. Never present a model-rendered word as typeset in the approved
font.

### Baked route (only on explicit request)

Pick a model from `canvas_image_model_list` whose `kontext_config.max_input_images` covers your
references and whose `resolution_options` include 2K (enum `5`). Pass in `input_images`, in order:

- exact approved logo variant
- approved typography specimen (a raster PNG of the board)
- any official product/photo reference

Refer to them in the prompt as「第一张图片」「第二张图片」「第三张图片」. Only raster image URLs are
valid — never an SVG. The prompt must state:

- Exact literal copy, character for character, in the user's original wording
- Display/body font family names and which text uses each
- Logo placement, scale, clear space, and color variant
- Text placement, hierarchy, alignment, line breaks, and contrast
- Exact palette roles with hex values
- Requested aspect ratio

Then read every rendered character against the source copy. One wrong or missing glyph fails the
asset.

## Mockup photography/application

1. Create or use the mockup photograph first with its target surface blank. Follow `mockups.md` for the base scene.
2. Pass that exact mockup URL first in `input_images`.
3. Pass the approved logo variant second.
4. Pass the approved typography specimen third.
5. The image-to-image call adds the exact copy, logo, and approved typography to the blank surface —
   subject to the same text-route decision above.

Preserve「第一张图片」's camera, crop, people, pose, lighting, materials, folds, shadows, perspective, environment, and background exactly. Change only the controlled social artwork/application.

## Typography fidelity

The approved typography specimen is mandatory whenever text appears. Name the exact display/body families in the prompt; never infer typography from the logo or palette.

After generation, check the output against the specimen. Retry once when the letterform character is visibly substituted. If the model still cannot reproduce the approved typography, switch to the deterministic route or report the limitation — do not present the output as exact.

## Consistency and QA

- Exact copy and spelling
- Correct platform ratio
- Approved logo geometry and color variant
- Approved display/body typography character
- Readable hierarchy and text contrast
- Approved palette only
- No pseudo-text, extra logos, invented CTA, or unsupported claims
- All outputs in one set share the same Brand Lock

## Approval

Show all final graphics in chat and wait for ordinary feedback. Save the approved set through `approve_brandbook_element` with a stable key such as `social-media-graphics` and `required_slots: ["logo","palette"]`; add `"typography"` only for text-bearing graphics.
