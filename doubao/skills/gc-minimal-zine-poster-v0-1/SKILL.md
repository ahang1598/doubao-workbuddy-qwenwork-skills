---
name: gc-minimal-zine-poster-v0-1
description: Generate Minimal Zine Poster v0.1 poetic paper-poster prompts and the matching generated image. Use when the user gives a theme, sentence, object, mood, article idea, photo, or content brief and wants a quiet Japanese/Korean zine-like editorial poster with large negative space, aged paper texture, experimental typography, restrained color accents, and a generated bitmap image.
---

# Minimal Zine Poster v0.1

Turn the user's content into both:

1. a final image-generation prompt, and
2. a generated raster image made from that prompt.

## Mode Policy

Use **Standard Mode** for all generation. Use the Standard Mode Prompt Compiler in this `SKILL.md` to convert the user's content into a compact, imageable, high-fidelity prompt. If the user asks for higher quality, strengthen the prompt using the rules below.

## Standard Mode Prompt Compiler

Default generation should compile only the parts that become pixels in the final image prompt.

### Visual Rules Used by the Prompt Compiler

Use these rule groups as prompt material:

- **风格总述:** use only the visual identity and anti-identity: poetic minimal paper poster, huge negative space, old paper, tiny anchor, sparse type, one clear high-chroma anchor, zine/editorial mood.
- **核心视觉规则:** use the concrete renderable rules for canvas, composition, background, image anchor, typography, color, texture, lighting, and mood.
- **稳定共性:** use as non-negotiable must-haves: vertical 3:5 paper canvas, small cluster, scanned-paper view, old print defects, serif/typewriter text, and a saturated color anchor visible at thumbnail size.
- **可替换变量:** use as slot choices: object, photo/cutout/silhouette/block type, accent color, text line, date/weather, position, paper tone.
- **反向约束:** use as negative prompt material.
- **Prompt 结构模板:** use its field order, not its sample wording.

Do not use these as default prompt material:

- source path, sample count, README/metadata notes, or analysis scope
- long explanatory prose about why the style works
- sample-specific signatures, dates, captions, objects, or text
- example prompts as text to imitate line by line
- checklist phrasing unless it becomes a concrete visual constraint

### First-Principles Prompt Fields

Every Standard Mode prompt must answer these rendering questions in this order:

1. **Canvas:** What is the output frame and base surface?
   - tall vertical 3:5 phone-poster; full-frame aged paper; no border, no mockup.

2. **Attention Geometry:** Where does the eye go and how much is empty?
   - 70%-90% plain paper; one visual cluster occupying about 8%-25%; placed center, upper-middle, lower-middle, lower-left, or upper-right; no edge-hugging.

3. **Image Anchor:** What is the one imageable subject?
   - convert the user's theme into one object, fragment, photo crop, specimen, cutout, silhouette, old printed illustration, texture window, or small conceptual relation.

4. **Anchor Treatment:** What material process makes the anchor belong to paper?
   - grayscale photos and paper fragments may use low contrast, photocopy softness, torn edge, softened edge, halftone, scanline, risograph grain, xerox wear, ink bleed, or slight misregistration. Do not apply low saturation or low contrast to the chosen color anchor.

5. **Typography System:** How does text behave visually?
   - small serif/typewriter/monospaced type; one short readable phrase; optional tiny date/location/weather and signature; semi-legible microtext or fragmented letters; text can drift, press against the image edge, blur, or misregister.

6. **Color Logic:** What is the restrained accent strategy?
   - paper tones plus gray/black support one unmistakably high-chroma anchor. Prefer cobalt or ultramarine; rotate through cyan, violet, magenta-pink, lemon yellow, pear green, orange, or tomato red. The color may be the subject, a flat silhouette, an irregular cutout, a substantial block, a partial-color photo region, or bold fragmented type. It must not be reduced automatically to a tiny dot or hairline.

7. **Reproduction Texture:** What print/scanning process defines the whole image?
   - flat orthographic scanned-paper appearance; matte absorbent paper; diffuse light; low-to-medium contrast; no hard shadow; no 3D depth.

8. **Emotional Temperature:** What should the viewer feel before identifying the object?
   - quiet, poetic, nostalgic, sparse, diary-like, archival, distant, memory-like, Japanese/Korean indie zine or minimal editorial.

9. **Hard Avoids:** What must not appear?
   - full-bleed scene, commercial headline, product ad, logo/CTA, glossy mockup, clean UI white, cinematic lighting, 3D, neon, cute cartoon, fashion editorial drama, dense scrapbook, too many colors, long clean text.

### Standard Color Engine

This section defines the color strategy for Standard Mode.

- Default to one visibly saturated, opaque chromatic ink anchor. Use wording such as `fully saturated cobalt-blue risograph ink`, `opaque ultramarine cutout`, `vivid pear-green flat silhouette`, or `clean tomato-red printed block`.
- Keep the paper, grayscale photo, microtext, and secondary marks subdued. Preserve saturation in the color anchor even when adding grain, halftone, ink bleed, or misregistration.
- The high-chroma area should occupy roughly 0.8%-2.5% of the whole canvas or 15%-35% of the small visual cluster. It must remain visible when the image is viewed as a thumbnail.
- Color can carry the subject itself. Prefer a colored tree, fruit, shell, flower, geometric cutout, window, poster fragment, or image panel over a gray object with one colored registration tick.
- For a single image, use a substantial color anchor by default. For batches, at least 60% of images must use a colored subject, cutout, or block; the remaining images may use dots, hairlines, or colored type for rhythm.
- Do not use `near-monochrome`, `no strong accent`, `pale accent`, `muted accent`, `faded accent`, or `pastel accent` unless the user explicitly requests monochrome, muted, or pastel output.
- Do not describe the entire image as low saturation. Apply `low contrast` and `muted grayscale` only to paper, photos, and secondary ink.
- Use only one main high-chroma hue per image. A tiny secondary hue is allowed only when it supports the subject and does not make the poster commercially colorful.

### Standard Prompt Shape

Write the final Standard Mode prompt as four compact paragraphs:

1. canvas + paper + negative space + cluster size/location
2. subject metaphor + anchor type + anchor treatment
3. typography + accent strategy + print defects
4. flat scan mood + avoid-list

In paragraph 3, state the exact high-chroma hue, its material form, and its approximate visual share. This structure is more important than reciting every rule. Prefer a concrete, imageable prompt over a long style essay.

## Variation Engine

Before writing the prompt, choose one option from each axis. Randomness must change visual grammar, not only position. If recent outputs used the same layout or anchor, choose a different one.

### Layout Family

- **center-fragment:** tiny central image or object with surrounding air
- **lower-left-float:** small anchor in the lower-left quadrant, lots of empty top space
- **upper-right-block:** small color/photo block in the upper-right with loose text drift
- **dual-panel:** two small overlapping or adjacent panels with a narrow gap
- **irregular-cutout:** torn or organic paper shape carrying image or type
- **type-led:** typography is the main visual anchor, image secondary or absent
- **dot-orbit:** dots, letters, or hairline create an orbit around a small subject
- **single-specimen:** one isolated object or mark with almost no support graphics

### Image Anchor

- tiny faded photo
- torn-paper clipping
- flat silhouette
- solid color block
- old printed illustration
- object specimen
- translucent geometric overlay
- abstract texture window

### Typography Mode

- fragmented floating letters
- short phrase pressed against image edge
- archive microtext with date/weather
- diagonal scattered words
- low-contrast gray ghost text
- headline-as-object with rough letterpress
- text inside a color block or cutout
- almost textless, only a tiny caption

### Texture Mode

- xerox softness
- risograph grain
- letterpress ink bleed
- halftone degradation
- film grain photo
- scan noise and paper fibers
- aged paper mottling
- soft motion blur on selected text

### Mood Mode

- quiet
- summer
- solitude
- childhood
- seaside
- afternoon
- night
- memory
- slight surrealism

## Workflow

1. Determine mode.
   - Use Standard Mode.

2. Parse the user's content.
   - Identify the core subject, mood, exact text if supplied, possible visual metaphor, and any reference image role.
   - For an article or complex idea, extract one central imageable idea rather than summarizing the whole argument.
   - If no image text is supplied, invent one short poetic English or Chinese phrase.

3. Select a variation recipe.
   - In Standard Mode, pick layout, image anchor, typography, texture, and mood from the Variation Engine, then choose color through the Standard Color Engine. Do not select `near-monochrome` unless the user explicitly asks for it.
   - Do not default to "tiny photo + blue dots + microtext" unless it truly fits.
   - If the recipe becomes too dense, simplify typography or color treatment first.

4. Write the final image prompt.
   - In Standard Mode, use the Standard Mode Prompt Compiler to compile the user's content into the four-paragraph prompt shape: canvas, anchor, typography/accent/print, flat-scan mood and avoid-list.
   - Specify exact in-image text only when useful. Keep it short because image models distort long text.
   - Make the prompt decisive: say where the anchor sits, how large it is, how text behaves, what accent appears, and how the print/scan texture looks.

5. Generate the image.
   - Use the built-in image generation capability by default.
   - Do not stop after prompt-only unless the user explicitly asks for prompt-only.
   - If the result obviously violates the selected mode or recipe, tighten the prompt and regenerate once.
   - In Standard Mode, inspect the result at thumbnail scale. If the high-chroma anchor is absent, washed out, or reduced to an imperceptible mark, regenerate once with stronger color wording and a larger colored area.

6. Return the image and prompt.

## Negative Constraints

Always avoid:

- full-bleed subject or scene
- commercial poster headline hierarchy
- product ad layout, logo lockup, CTA, or brand campaign feeling
- clean digital UI background
- glossy paper mockup or heavy paper shadow
- 3D rendering, cinematic lighting, hard shadows, depth of field, neon, cyberpunk
- cute cartoon, kawaii illustration, anime poster, fashion editorial drama
- too many objects, stickers, colors, captions, or decorative textures
- high-resolution stock-photo realism
- long, clean, perfectly readable text blocks

## Output Format

````markdown
**生成图**

![Minimal Zine Poster v0.1 style poster](absolute-image-path-or-rendered-image)

**最终 Prompt**

```text
[final prompt used for image generation]
```

**说明**

- Mode: Standard
- Recipe: [layout / anchor / typography / accent / texture / mood]
- [one short note about the content interpretation]
````

If generated images render directly without a file path, show the image normally and still include the final prompt.

## Quality Gate

Before finalizing, check:

- Did the run use the Standard Mode Prompt Compiler?
- Did the run choose a variation recipe across layout, anchor, typography, accent, texture, and mood?
- Is the structure materially different from recent visible outputs?
- Does the image remain a sparse vertical paper poster?
- Does 70%-90% of the poster read as paper?
- Is the subject cluster roughly 8%-25% of the canvas?
- Is there one clear visual metaphor rather than a whole illustrated scene?
- Does the anchor have old-photo, clipping, print, scan, or paper-specimen treatment?
- Are typography and microtext part of the composition?
- Is there only one restrained accent strategy?
- In Standard Mode, is the high-chroma anchor clearly visible at thumbnail size?
- In Standard Mode, does saturated color occupy about 0.8%-2.5% of the canvas or 15%-35% of the visual cluster?
- In Standard Mode, did the prompt avoid weakening the color anchor with `pale`, `muted`, `faded`, `pastel`, `low saturation`, or `near-monochrome` wording?
- Did the prompt avoid full-bleed, commercial, 3D, neon, cinematic, cartoon, cute, brand, and generic template aesthetics?
- Did you actually generate the image?

## Example Requests

- "用 $minimal-zine-poster-v0.1 做一张关于雨天的图"
- "用 $minimal-zine-poster-v0.1 标准模式，做一张关于旧书的图"
- "用这张照片做一张同风格 poster"
