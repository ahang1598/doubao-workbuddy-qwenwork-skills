# Packaging

Design packaging once the slots used by the requested artwork are approved.

Require approved logo and palette. Require typography only when readable copy appears. Read those modules separately; do not block copy-free packaging or a packaging mockup on unused typography.

## Required inputs

- package type and dimensions/dieline
- material and printing constraints
- exact product/flavor names
- required legal/regulatory copy
- barcode/nutrition/certification assets
- hierarchy and variants

Do not invent claims, ingredients, certifications, dosage, nutrition, pricing, or regulatory content.

## Build

- Create label/panel artwork deterministically in SVG or other requested editable format.
- Use exact approved logo, fonts, and palette. A logo generated in this skill is a raster PNG
  (see `logo.md`); embed it at high resolution and disclose that the artwork is not a vector print
  master.
- Typeset all copy locally with the approved fonts. Do **not** ask an image model to render
  packaging text — in-image text quality is unverified on WorkRally.
- Keep copy editable.
- Preserve dieline folds, cut lines, bleed, and safe zones. Keep technical guides in an explicitly hidden group (for example `display="none"`) in artwork and clean previews; show them only in a separately labeled technical proof when requested. Custom attributes such as `data-print="false"` do not prevent SVG rendering or printing.
- Use one system across variants; vary only approved product information and designated color roles.

For presentation mockups, follow `mockups.md` after the packaging artwork is approved. The mockup is not the editable packaging source.

## QA and approval

Check dimensions, bleed, copy, barcode zones, contrast, variant consistency, and physical plausibility. Inspect the actual preview, not only source attributes.

An RGB SVG with `data-color-mode="CMYK"`, generic `device-cmyk()` declarations, or a formula-derived CMYK table is not a validated CMYK print master. Without the supplier ICC/output profile and conversion/separation proof, label these values provisional and disclose that the editable SVG still needs color-managed prepress. Do not claim press-ready/production QA passed from metadata alone; request the missing print profile when a final CMYK master is required.

Save approved packaging artwork and mockups as separate state elements with their exact `required_slots`.
