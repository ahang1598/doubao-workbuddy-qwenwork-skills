---
name: visualize
description: "Create visualizations and interactive tools directly in conversation. Use when asked to show how something works, make simulators or labs, maps, plots, charts or graphs, comparisons, UI mockups, scenarios, adjustable inputs, and exploration beyond regular text."
---

# Visualize

- A request for a new standalone file, website, app page, component, or other
  project change is not an in-conversation visualization request, even when the
  deliverable contains charts or interactive content.
- A request to preview, explain, or explore a proposed interface in the
  conversation is an in-conversation visualization request.
- Create a visual only when the user needs to see or explore it in the
  conversation and it materially improves the explanation. Do not create an
  inline visual merely because the request involves data, charts, or an
  interactive page.
- Use Mermaid when labeled nodes and edges fully explain a static structure;
  return a normal fenced Mermaid block and no visualization file. Use HTML for
  dynamics, spatial motion, adjustable inputs, and other visuals.
- Work silently unless blocked or the user explicitly asks for progress. Never
  send commentary or progress updates while reading this skill or writing or
  updating the file; the final response must be your first user-facing message.
- In user-facing prose, describe only what the visual helps the user see or
  decide. Keep it concise and do not repeat information already clear from the
  visual. Never announce this skill, a visualization surface, widgets, HTML,
  SVG, scripts, local files, inline data, or implementation details.

## Context compaction

Copy into every compaction summary:
`Reload the full visualize skill before creating or updating a visualization.`

## Inline HTML output contract

### File

- For each new or updated visualization, choose a concise ASCII
  lowercase-hyphenated title and write a new `<title>.html` in the thread-scoped
  visualization directory listed in the writable roots
  (`.codex/visualizations/YYYY/MM/DD/<thread-id>`).
- Build the visual in the conversation. Use the open project when the user asks
  for a site, app page, component, or change to existing project files.

### Fragment

- Write only an HTML fragment: no `<!doctype>`, `<html>`, `<head>`, or `<body>`.
- Write literal markup: use `<div class="card">Hi</div>` plus a real newline,
  never `<div class=\"card\">Hi</div>\n`. Never embed the fragment in an inline
  Python, JavaScript, or shell string. Read it back; rewrite literal `\"` or
  `\n`.
- Keep CSS and JavaScript in the fragment only when base classes are
  insufficient. Load static resources only from the CDN allowlist. Never use
  `fetch`, XHR, WebSocket, or other API calls.
- Give the fragment root a unique ID and select it with
  `document.getElementById(...)`. Never derive the root from
  `document.currentScript`; scripts may sit outside the root.
- Keep visualizations under 2 MB. Aggregate, bin, downsample, reduce precision,
  or drop unused fields from large inline datasets.
- Check that JavaScript has no undefined identifiers, every queried element
  exists, and the primary interaction updates the visual. The bundled
  `python3 scripts/render.py <absolute-fragment-path> [<destination>.html] [--serve]`
  can wrap a fragment as standalone HTML or temporarily serve it for browser
  inspection when a preview would help with layout, theme, or runtime behavior.

### Content and response

- Keep the fragment focused on the visualization. Do not include explanatory
  paragraphs, formulas, instructions, or narrative callouts. Include only
  necessary labels, legends, values, and accessible text alternatives.
- Use the normal response flow. Put any necessary concise explanation outside
  the fragment, and add this exact directive on its own line where the visual
  should appear:

```text
::codex-inline-vis{file="<title>.html"}
```

- Emit only the directive for the fragment. Never announce the fragment as an
  artifact, website, output, attachment, link, or download, and never add a
  Markdown link to it.

### External resources

- The CSP allows only `cdnjs.cloudflare.com`, `esm.sh`, `cdn.jsdelivr.net`,
  `unpkg.com`, `fonts.googleapis.com`, `fonts.gstatic.com`, and
  `fonts.bunny.net`. Other origins are blocked and fail silently.

## Exporting an existing visualization

- Keep the fragment as the editable inline source. When the user explicitly asks
  to save, export, or publish a visualization that is already shown in the
  conversation, render it with
  `python3 scripts/render.py <absolute-fragment-path> <destination>.html`.
- Apply this export flow only when the user explicitly asks to turn the existing
  inline source or visualization into a website. For a general website request,
  build a new responsive site in the output directory or open project, using
  Sites when appropriate, without applying this skill's guidance.
- If the visualization calls `window.openai`, replace that host-only interaction
  before using the standalone HTML outside Codex.
- When the user asks to publish or host an existing visualization and the Sites
  skills are available, use `sites-building` to choose the project and write the
  rendered standalone document as `index.html`, then use `sites-hosting`.
- If Sites is unavailable, offer the standalone HTML without claiming it was
  published.

## Composition

Choose the smallest composition that fits.

- Prefer interaction detail over permanent panels, toolbars, repeated legends,
  or long stacks. Add only requested controls, use one mechanism per state, and
  never invent search, filter, or reset controls.
- Keep filters, selections, and other presentation-only interactions local. For
  drill-down actions that ask Codex to investigate or explain selected data,
  call `await window.openai.sendFollowUpMessage({ prompt, title })`, where the
  optional `title` is a concise confirmation-dialog heading of up to 250
  characters. Include the selected values and requested investigation in the
  prompt, and label the action clearly.
- Show only metrics that explain the requested behavior. Put live values in
  control headers or on the visual before cards. Treat maxima as ceilings, not
  targets. Never invent qualitative scores, status cards, or secondary fact
  grids to fill space.

### UI mockups

- "In the widget" means the in-conversation visualization, not a widget inside
  the depicted product.
- Use product and platform context already available in the conversation;
  don't search the project to render a mockup. Match the product's chrome,
  navigation, typography, colors, and content. If its design is unavailable,
  infer one from the platform and request.
- NEVER use visualization CSS variables or utility classes inside a mockup
  (for example, `--card`, `--font-size-base`, `.card`, or `.btn`). Define
  root-scoped, product-specific colors, typography, surfaces, and controls
  instead. This rule overrides all general visualization guidance.
- Keep only the surrounding conversation surface transparent. Give product
  windows, cards, menus, and popovers opaque backgrounds, and stack overlays
  above the product content.
- Follow the host's active appearance with product-specific
  `light-dark(<light>, <dark>)` colors unless a fixed theme is requested.
- **Contained mockup:** Frame a component, dialog, small feature, or mobile
  screen as a compact product surface.
- **Full-page mockup:** Render a desktop window, application shell, or page at
  full width without an additional visualization card.
- Put app-wide navigation and pickers in the app chrome, and local controls in
  their component. Omit single-option pickers. Show realistic states, not
  invented dashboards, filler cards, or oversized icons.

### Interactive explainer or simulation

- Use compact controls or status, one compact dominant visual, and at most one
  single-line selected-state detail. Default to no summary cards; allow up to
  three only when changing metrics are central.
- Crop empty space; prefer wide and shallow unless intrinsically square. For
  step-throughs, add only requested step controls and update one current visual;
  never add parameter controls, formulas, metric cards, or side-by-side steps
  unless asked.

### Graphs and plots

- For named numeric data and one-off analyses, start with the plot. Put values
  and takeaways on its marks, axes, or annotations. Never add a KPI row,
  controls, cards, or panels unless those UI elements are explicitly requested.
- For sequences or parallel work, use aligned lanes on one time axis. Encode
  phase and resource in the marks; annotate totals, waits, and bottlenecks on
  the axis or lanes, not above the plot.
- For distributions or multi-metric comparisons, use shared-scale facets or
  small multiples. Render every requested dimension simultaneously; never hide
  one behind a toggle.

### Maps

- Let the map dominate the composition. Use at most one compact
  selection/detail area and only requested controls.
- Always project published GeoJSON/TopoJSON and sourced longitude/latitude with
  `d3-geo`; never hard-code or hand-draw geographic outlines. Use schematic maps
  only when asked.
- For world countries, import
  `https://esm.sh/@d3-maps/atlas@1.0.0/world/countries/countries-110m` and convert
  it with `topojson-client@3.1.0` using
  `feature(world, world.objects.features).features`. Join input ISO3 directly to
  `feature.properties.id`, which is already ISO3; do not convert it to numbers.
- For US states or counties, use
  `https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json/+esm`. For ZIP/ZCTA
  or city boundaries, download official Census or local open-data GeoJSON; do
  not guess sibling atlas paths or import raw JSON as JavaScript.
- Keep maps geographically legible: for local points, fetch published
  neighborhood, street, or comparable geometry; a blank field or lone
  administrative outline is not a basemap. Show the full city or region behind
  points or partial choropleths, and frame the locations with modest padding.
- Include the verified geometry in the final HTML. Open it before replying and
  fix blank basemaps, failed imports, missing labels, or unprojected points.

### Dense categorical grid

- Use one compact horizontal selected-item summary, then a grid with exactly one
  readable identifier per cell, then one small legend. Render only that
  identifier as visible cell text; put all other metadata in an accessible label
  or one summary line, not badges or fact grids. Allow only selection unless
  asked.

### Part-to-whole or time allocation

- Use compact metrics and one stacked chart of category allocation per period.
  Never substitute totals-only bars or duplicate it as a heatmap and totals
  chart.

## Layout and accessibility

- Use semantic HTML, keyboard-accessible controls, and concise labels.
- Keep the top-level surface transparent and unframed, and fill the available
  conversation width. Design for 736px and support widths down to 320px.
- At every supported width, text, controls, cards, toolbars, and dynamic content
  must fit without overlap or clipping. Reflow by stacking or wrapping; use
  `.table-responsive` only when table columns cannot fit. The host sizes the
  frame to its content, so avoid fixed outer widths, other horizontal overflow,
  internal scrolling, `position: fixed`, and viewport-height layouts.
- Keep native tab order; never add `tabindex`.
- Use native `button`, `input`, `select`, and `textarea` elements with matching
  utilities; never recreate controls.
- Keep browser or utility focus styles; never override them.

## Typography

- Scale type with `--font-size-base`. Use normal text by default and
  `.text-small` only for secondary annotations (never below 11px).
- `h1`, `h2`, and `h3` are available; use them sparingly. Never render a title or
  restate the prompt inside the fragment; put titles and explanation in Markdown
  above the directive.
- Use only weights `400` and `500`. Never set custom font sizes or line heights.

## Color

- Make every fill, stroke, text, border, shadow, chart, and canvas color
  theme-aware. Never hardcode light or dark palettes such as white panels,
  off-white backgrounds, black text, slate strokes, or Tailwind color literals.
- Keep text readable against its actual background. Muted or secondary colors
  must retain clear contrast; never use `.text-muted` inside `.card` or another
  filled container unless its background preserves that contrast.
- Available theme variables include `--background`, `--foreground`, `--card`,
  `--card-foreground`, `--popover`, `--popover-foreground`, `--primary`,
  `--primary-foreground`, `--secondary`, `--secondary-foreground`, `--muted`,
  `--muted-foreground`, `--accent`, `--accent-foreground`, `--destructive`,
  `--border`, `--input`, and `--ring`. Use `currentColor` inside SVG.
- Use `--viz-series-1` for one measure or active state. Use `--viz-series-2`
  through `--viz-series-6` only for important persistent category, series, or
  status identity; never give every peer a different color by default.
  - For categorical tiles or nodes, prefer a soft low-opacity series fill with a
    neutral or transparent border; never color every outline.
  - Keep mappings stable and pair color with labels, shapes, or line styles.
  - Secondary series colors are theme-derived; never assume hues or use them
    decoratively.
- When color encodes a category or series, apply it consistently to the
  corresponding visual marks—not just the legend—and keep large-area fills
  subtle.
- Use series colors only for chart lines, marks, and legend swatches. Never use
  them for text; use `--foreground` or `--muted-foreground` for labels and
  values.
- Keep chart grids and inactive structure thin and neutral. Use 1-2px neutral
  structural paths; never thicken, dash, or double-stroke the whole structure.
- In each color pair, the base token is a surface and its
  `-foreground` token is the content on that surface. Use `.btn-primary` for
  high-emphasis actions; its neutral fill is supplied by the utility. Use
  `--primary` and `--primary-foreground` for filled selected, active, or pressed
  controls. Reserve `--accent` and `--accent-foreground` for subtle interactive
  surfaces and soft highlights. Buttons with
  `aria-pressed="true"`, `aria-selected="true"`, or `.is-selected` already use
  the primary pairing.

## Design system

- Let utilities own geometry, appearance, and interaction. Use the matching
  utility for every button and form control. Never restyle utilities,
  descendants, or pseudo-elements: no custom sizes, spacing, borders, radii,
  shadows, colors, or interaction states.

### Surfaces and layout

- `.card`: The only card-like HTML surface. Use its base class unchanged for a
  necessary numeric summary, selected-item summary, or bounded interactive
  field. Before adding a fill, border, radius, or shadow to any layout container,
  either use `.card` or leave it transparent and unframed; never recreate card
  chrome on rows, panels, tiles, sections, or wrappers. Keep charts, maps,
  diagrams, tables, controls, and the whole visualization unframed. Never nest
  cards; show 2-4 summaries near the top only when useful. Structural groupings
  and repeated content are not bounded interactive fields. Organize them with
  layout or visual marks, not container chrome.
- `.viz-stat`: Use a summary `.card` with one muted label, one
  `.viz-stat-value`, and at most one short context or delta line.
- `.viz-grid`: Use for peer metrics or choices instead of a custom grid. It
  creates as many equal-width columns as fit and stacks when narrow. Never use it
  for the whole visual or a horizontally scrolling card row. Keep groups to 2-3
  columns at 736px and controls in a separate row.
- `.viz-row`: Use as a wrapping horizontal group with centered related values or
  inline actions that may wrap when narrow.
- `.viz-tile`: Add to a selectable dense-grid `.btn`; it stretches to fill its
  grid cell, preserves category fill, and uses an accent ring instead of solid
  selection. Never add another selected, pressed, border, outline, or shadow
  rule.
- `.viz-badge`: Use as a compact display-only accent pill for a short status,
  category, or value; never as a button.
- `.viz-controls`: Use as a wrapping row for controls affecting the same
  visualization. Keep button groups compact. Put labeled fields directly inside
  as `.form-label`; fields form at most two columns and stack when narrow.

### Controls

- `.btn`: Use for a content-sized secondary action. Add `.btn-primary` for one
  main action per control group or `.btn-ghost` for low emphasis.
- `.btn-block`: Add to a `.btn` only when the action should intentionally fill
  the available inline space. Never use it for ordinary row actions.
- `<a>`: Use for links. Add `.btn` to style a link as a button.
- `[data-tooltip]`: Use for concise supplementary plain text on static or dynamic
  triggers; the sandbox creates `.tooltip` elements. Keep essential content
  visible and triggers labeled. Never use `title`, custom markup, or
  initialization. Example:
  `<button type="button" data-tooltip="Reset view">Reset</button>`.
- `[data-tooltip-placement]`: Optionally prefer `top` (default), `right`,
  `bottom`, or `left`; collision handling may flip it.
- `.form-check`: Wrap a native checkbox or radio; pair `.form-check-input` and
  `.form-check-label` with matching `id` and `for`.
- `.form-switch`: Add to `.form-check` around a native checkbox.
- `.form-control`: Pair a native text, file, or color input—or a textarea—with
  `.form-label`.
- `.form-control-color`: Add to `.form-control` for a compact native color
  input.
- `.form-select`: Pair a native select with `.form-label`.
- `.form-range`: Pair a native range with a visible label; put its current value
  and units immediately before it.

### Tables

- `.table`: Use on a semantic table for a quiet, unframed data view. It provides
  wrapping cells and subtle horizontal dividers without vertical gridlines. Use
  sentence case for headers.
- `.table-responsive`: Wrap a table when its columns cannot fit at narrow
  widths. It contains horizontal overflow without clipping the visualization.
- `.table-sm`: Add to `.table` when more rows need to fit; it reduces cell
  padding without shrinking text.
- `.text-end`, `.text-center`, and `.text-nowrap`: Use inside `.table` for
  numeric/end alignment, centered values, or values that must stay on one line.
  Numeric cells use tabular figures when end-aligned.

### Text

- `.text-small`: Use for the smallest host-scaled secondary chart labels and
  annotations, never below 11px or for essential content.
- `.text-muted`: Use for secondary units, captions, timestamps, and context,
  never essential values or labels.
- `.text-destructive`: Use only for error or validation text the user needs to
  notice or act on.
- `<code>`: Use for inline commands, file names, symbols, or short references;
  put multiline code in `<pre><code>`.
- `.sr-only`: Use for visually hidden accessible text.

## Charts

- Prefer inline SVG for simple charts; use a version-pinned approved-CDN library
  only when it materially reduces complexity.
- Use a tooltip unless it would distract from a simple, directly labeled chart.
  Use `class="tooltip"` without surface CSS; add only positioning and visibility.
  Choose the best `position: relative` parent; convert the hovered mark into that
  parent's CSS pixel space before setting absolute `left`/`top`. Measure and
  clamp the box to the plot—never pointer coordinates. Show label, value, and
  units; mirror them in a visible keyboard fallback.
- Animate transitions between chart states so lines and marks move to their new
  values, resampling paths when point counts differ. Do not animate initial
  appearance or use fade-only effects; never loop motion, and honor
  `prefers-reduced-motion`.
- Scope SVG styles to the chart class. Never target every `svg` in a container
  that also contains Lucide icons.
- Include labeled axes, units, and directly labeled important values. Give every
  chart, SVG, canvas, and widget a concise screen-reader summary using a role and
  accessible name or description, SVG `<title>`/`<desc>`, fallback text, or an
  `.sr-only` heading or description.
- Reserve space for the longest formatted label at every supported width. Axis
  ticks are secondary and may use `.text-small` when space is tight. Never
  overlap or clip text against marks, axes, legends, labels, or edges; move or
  reduce labels rather than squeeze them.
- Add a legend only when multiple series cannot be labeled directly.
- Pair color with shape or text so meaning never depends on color alone.

## Icons and mockups

- Use the sandbox-provided global `lucide`. Add an icon name with `data-lucide`:

  ```html
  <i data-lucide="search" aria-hidden="true"></i>
  ```

- Lucide replaces the placeholder in place with an inline SVG. Icons are 16px
  and inherit `currentColor`.
- Mark decorative icons `aria-hidden="true"`. Put action icons inside labeled
  controls; use a visible label or `aria-label` for icon-only actions.
- Let the sandbox initialize static icons after the fragment without blocking
  first render. After adding icons dynamically, use
  `lucide.createIcons({ attrs: { width: 16, height: 16 } })`.
- Never load Lucide or another icon library from the network.
- Use visibly labeled buttons and inputs for small interactions. Keep all
  presentation-only interaction local to the fragment and make the first render
  useful before input changes.
- Use semantic controls, realistic spacing, and restrained chrome for mockups.
  Never fake product screenshots when inspectable UI is needed.
