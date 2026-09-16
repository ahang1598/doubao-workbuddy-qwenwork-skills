# Posters and banners

Create once the slots used by the requested poster/banner are approved.

For text-bearing branded layouts, require separately approved logo, palette, and typography. If a requested asset genuinely omits one of these, read only the slots it uses.

## Inputs

- intended channel/use
- dimensions/aspect ratio
- exact headline/body/CTA
- print or digital
- supplied imagery
- required bleed/safe area

## Build

- Vector/layout-led work → editable SVG.
- Easy office/editor editing → one-slide PPTX.
- Digital implementation → HTML/CSS when requested.

Typography, logo, shapes, and layout remain deterministic. Image models may create only replaceable photography/background imagery.

Never bake the final logo or exact copy into a generated image.

## QA and approval

Check dimensions, safe areas, spelling, contrast, font rendering, logo source, and print/export requirements. Check every painted part of the placed logo against its immediate background: an unchanged blue mark on a matching blue stripe can disappear even though source geometry is correct. Move the intact logo to a contrasting approved surface; do not recolor or redraw it without approval.

Show the visual in chat plus editable download. Save only an explicitly approved asset through `approve_brandbook_element` with a stable descriptive key and its exact `required_slots`.
