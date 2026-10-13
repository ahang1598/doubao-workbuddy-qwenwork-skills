---
name: travel-memory-card-duo
description: "Transform one user-supplied travel, street, landscape, lifestyle, portrait, or pet photo into a coordinated two-image deliverable: one complete horizontal collectible travel memory card and one separate transparent-background PNG containing the exact same six die-cut sticker motifs. Use when Codex needs to P图, stylize a photo as a tactile gouache/cut-paper memory card, provide reusable transparent stickers, make a sticker pack or sticker sheet, or deliver both a finished card and transparent PNG assets. Preserve recognition through one source-derived identification anchor; never retain unintended photography, incidental text, signatures, or watermarks."
---

# Travel Memory Card Duo

Turn one source photo into two matched bitmap deliverables:

1. A finished 3:2 travel memory card.
2. A 3:2 transparent PNG sticker sheet containing the same six sticker motifs.

Use the image generation/editing tool for both images. Do not simulate the illustration with filters or code. Use local processing only to remove a flat chroma-key background and validate transparency.

## Workflow

1. Inspect the source photo at full useful detail.
2. Identify the scene structure, emotional center, dominant spatial gesture, and one compact identification anchor.
3. Select exactly six meaningful source-derived sticker motifs and exactly three concise English keyword phrases.
4. Decide whether one source-visible text item genuinely identifies the place. Default to `NONE`; reject advertising, menus, prices, directions, timestamps, and product labels.
5. Read [references/style-guide.md](references/style-guide.md).
6. Generate the complete memory card first. Treat its six stickers as the visual master for the second image.
7. Inspect the card. Regenerate once if the medium, layout, sticker count, keywords, or readable text is wrong.
8. Generate a separate sticker sheet from the source photo and finished card. Include exactly the same six motifs, shapes, colors, medium, and warm-white cut borders.
9. Produce transparency with the built-in image-generation transparency workflow: generate the sheet on one uniform removable chroma-key color, then run the installed `remove_chroma_key.py` helper. Choose a key color absent from the stickers; prefer `#ff00ff` for foliage-heavy scenes and `#00ff00` otherwise.
10. Validate the final PNG. It must be RGBA, all four corners must have alpha 0, the six stickers must remain fully opaque apart from antialiased edges, and no key-color fringe may remain. Retry removal once with a slightly stronger tolerance or `--edge-contract 1` if needed.

## Deliverable 1: complete memory card

- Use one 3:2 horizontal canvas on warm off-white uncoated paper with a continuous 4–5% outer margin.
- Build the left 66–68% as one large near-square unframed illustration above a shallow exposed-paper keyword footer. Do not add an outline, keyline, mat, inner card, rounded frame, or shadow around the illustration.
- Center exactly three short scene-derived English keyword phrases once beneath the illustration, separated by centered dots: `[keyword 1] · [keyword 2] · [keyword 3]`.
- Place exactly six separate die-cut stickers in the right 30–32%. Use the full composition height, an uneven size hierarchy, relaxed spacing, thick irregular warm-white hand-cut borders, and subtle flat paper shadows.
- Preserve the identification anchor through silhouette, proportion, placement, relationship, and signature colors in the same medium as the whole card.
- Add no title, caption, date, writing area, postal marks, address lines, subtitle, watermark, or signature.

## Deliverable 2: transparent sticker PNG

- Use a separate 3:2 horizontal canvas.
- Include exactly the same six stickers from the finished card; do not redesign, replace, split, merge, or add motifs.
- Arrange the stickers in two relaxed rows with generous transparent space. Keep every sticker fully visible, separated, and uncropped.
- Preserve the thick irregular warm-white die-cut border around every sticker.
- Remove the card paper, shadows, footer, keywords, title, labels, and all readable text.
- Do not add an overall sheet, panel, frame, texture, floor plane, reflection, or cast/contact shadow.
- Deliver a real PNG with an Alpha channel. A checkerboard, black, or white preview background is not part of the file.

For chroma-key generation, explicitly require a perfectly uniform flat background with no lighting variation, texture, gradients, shadows, reflections, or key color inside the sticker art. Use the installed helper:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input <chroma-source.png> \
  --out <transparent-stickers.png> \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 60 \
  --despill
```

If the helper needs Pillow, load the Codex workspace dependency runtime and use its Python executable. If soft-matte removal leaves a fringe, retry once with `--edge-contract 1`; if hard-key removal is cleaner for opaque paper stickers, use a sampled key color and a moderate tolerance. Never claim transparency before checking the Alpha channel.

## Shared art direction

- Rebuild the scene from 5–8 broad source-derived matte color families.
- Make the first read 3–6 oversized blunt shapes and quiet negative space.
- Use opaque gouache, cut-paper, risograph, or screen-print-like fills with fine uniform paper tooth, chalky hand-cut edges, light pigment variation, and soft misregistration.
- Compress foliage into 1–3 lumpy tonal masses; reduce buildings and terrain to planes; reduce people and animals to compact faceless silhouettes.
- Use flat colored shadows rather than gradients. Keep near-black sparse.
- Keep the mood observational, spacious, humane, slow, and lightly nostalgic.
- Avoid photorealism, photographic patches, marker strokes, watercolor washes, wet blooms, glossy 3D, dramatic lighting, detailed leaves or anatomy, polished vectors, anime, clip art, and unrelated objects.

## Motif and keyword rules

- Choose six visible motifs with useful variety: a main-subject fragment, a grouped or paired variation when present, an environmental form, a structural fragment, a functional object, and a small atmospheric or scale cue.
- Treat a group visible as one sticker when selected as a grouped motif.
- Keep all six motifs coarse, source-derived, and stylistically identical across both deliverables.
- Remove lettering when a sticker repeats a landmark sign.
- Write three precise English keyword phrases grounded in the scene, light, object, or spatial feeling. Prefer `Crater Smoke`, `Blue Summit`, or `Quiet Ridge` over generic words such as `Travel` or `Beautiful`.

## Quality checks

### Complete card

- The scene is identifiable at a glance but reads first as large shapes and quiet space.
- The left illustration dominates and is completely unframed.
- The right column contains exactly six separated stickers with a clear size hierarchy.
- Exactly three English keyword phrases appear once beneath the left image.
- No unintended readable text, watermark, signature, or photographic patch remains.

### Transparent PNG

- The file format is PNG and the image mode is RGBA.
- All four corner alpha values are 0.
- Exactly six sticker objects remain; none is cropped, touching, or duplicated.
- The sticker designs match those on the card and retain warm-white cut borders.
- No paper sheet, colored background, key-color halo, shadow, label, or extra fragment remains.

## Delivery

Show both finished images and provide two separate file links. Label them clearly as `完整旅行记忆卡` and `透明底贴纸 PNG`. Briefly name the identification anchor, the six sticker motifs, the three English keyword phrases, and both saved paths. State that a dark or checkerboard preview behind the PNG represents transparency only after Alpha validation succeeds.
