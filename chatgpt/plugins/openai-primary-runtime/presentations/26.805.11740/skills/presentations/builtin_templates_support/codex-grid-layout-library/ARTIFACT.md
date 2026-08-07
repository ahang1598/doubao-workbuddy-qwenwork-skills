---
artifactSpecVersion: alpha
kind: presentation
name: Codex Grid Layout Library
description: Design presentation-native decks with a monochrome 26-layout system spanning covers, agendas, image splits, evidence tables, process sequences, charts, and metric grids.
tokens: ../../assets/builtin_templates/codex-grid-layout-library/design_tokens.json
content: ../../assets/builtin_templates/codex-grid-layout-library/content.json
---

# Overview

Use this layout library when a deck needs a restrained, white-background visual system with strong typographic hierarchy and a broad range of presentation-native structures. Select one of the 26 layouts by content role and density before adapting copy. Do not reduce the system to repeated cards or a single two-column silhouette.

# Theme And Colors

Keep the canvas white, primary type black, and structural panels light gray. Reserve color for user evidence, charts, or one deliberate highlight; the layout system itself should remain neutral.

# Typography

Use Helvetica Neue when available and a metric-compatible sans-serif fallback otherwise. Titles range from 39px to 96px in the exact reconstructions.

# Layout And Density

The exact reconstruction layer contains one module per layout implemented as plain JavaScript modules that build artifact-tool Compose node trees without JSX. Use the registry's roles, slots, density budget, and typography budget to choose a layout, then adapt its content while preserving the composition's hierarchy and spacing.

# Charts

Give charts the dominant evidence region. Use a restrained interpretation rail only when it adds meaning. Keep series order and annotations explicit.

# Shapes, Lines, And Effects

Use square gray panels, thin rules, and whitespace. Avoid decorative gradients, heavy shadows, and ornamental rounding.

# Tables

Tables are evidence objects. Keep headers restrained, align values consistently, and use row grouping or emphasis rather than shrinking type below the budget.

# Image And Icon Assets

Gray regions are semantic media slots, not final artwork. Fill them with exact user-provided evidence or prompt-backed imagery appropriate to the request. No uploaded Office bytes or extracted media are retained.

# Reusable Scripts

Use `../scripts/create-presentation.mjs` with the static asset root to materialize the complete 26-slide reconstruction. Use `../../assets/builtin_templates/codex-grid-layout-library/artifact-tool-compose/template-registry.json` to select individual exact modules. The modules deliberately contain no JSX.

# Validation

All 26 exact JavaScript modules must parse and render through artifact-tool. The static asset archive must contain no Markdown, agent prompt, reusable runner, Office file, original filename, transient evidence path, source screenshot, or raw extraction record.
