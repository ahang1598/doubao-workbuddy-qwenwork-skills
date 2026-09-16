# Signage

Create signage once its required slots are separately approved.

Require logo and palette; require typography when copy/wayfinding text appears. Read only those state slots.

Require:

- sign type and environment
- physical dimensions
- viewing distance
- fabrication/illumination constraints
- exact copy and directional information
- supplied site photos or plans

Do not invent wayfinding destinations, measurements, safety information, or fabrication specifications.

Build deterministic editable sign artwork in SVG/PDF-compatible vector form, and typeset all copy locally with the approved fonts — never let an image model render sign text. Use approved logo, fonts, and palette. Prioritize legibility at the required distance over decorative detail.

A logo generated in this skill is a raster PNG (see `logo.md`). Embed it at high resolution and disclose that fabrication normally needs a vector master.

If a visual-in-context preview is requested, follow `mockups.md`; keep the editable sign artwork as a separate source asset.

Check scale, contrast, minimum stroke size, clear space, mounting constraints, and environmental visibility. Save artwork and approved mockup as separate state elements with their exact `required_slots`.
