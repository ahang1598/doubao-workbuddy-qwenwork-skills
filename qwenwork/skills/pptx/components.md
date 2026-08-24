# Components

Twelve designer-tuned visual components for slides where shape
alignment math gets fiddly. Use them when one matches your content;
use python-pptx primitives directly otherwise.

```python
from components import (
    add_metric_card, add_quote_block, add_comparison,
    add_swot, add_radar, add_funnel,
    add_gantt, add_timeline, add_allocation_bars,
    add_flywheel, add_layered_diagram, add_flow_matrix,
)
```

All components share the same call shape:

```python
add_xxx(slide, origin, size, content_arg, style, *, ...)
```

- `slide` — python-pptx `Slide`
- `origin` / `size` — `(Inches(x), Inches(y))` / `(Inches(w), Inches(h))`
- `style` — a `helpers.Style(palette, fonts)`. See [helpers.py](helpers.py)
  for the dataclasses; copy palette + fonts from a theme file under
  [themes/](themes/).
- content arg name varies (`content`, `panels`, `steps`, `rows`, …)

For exact signatures and optional kwargs, read the matching
`components/<name>.py` — the source is the ground truth and stays in
sync with itself. This doc covers *when* to reach for each component
and the content-shape it expects.

**House style (already enforced in code):** every component renders
cards, nodes, bars, and bands square-cornered and flat — no rounded
corners, no inherited theme shadow. Columns are distributed via
`col_edges` so the last column lands on the layout's right margin
exactly. The one intentional exception is `add_allocation_bars`,
whose progress tracks stay capsule-rounded (a deliberate progress-bar
idiom) — but still flat, no shadow.

---

## When NOT to use a component

Use python-pptx primitives directly for plain text, titles, bullets,
single images, two-column body, simple tables, basic bar/line/pie
charts, single icon callouts. Components are for hard visual shapes
where multi-shape composition is easy to get wrong — if you're about
to call `add_shape(MSO_SHAPE.RECTANGLE, …)` four times in a row to
build something, check the catalog first.

---

## Decision flowchart

```
Need to show…
├─ a single big KPI number?          → add_metric_card (place 2-4 in a row)
├─ a pull quote / CEO message?       → add_quote_block
├─ 2-4 options side by side?         → add_comparison
├─ SWOT or 2×2 impact matrix?        → add_swot
├─ multi-axis score / capability?    → add_radar
├─ conversion / stage funnel?        → add_funnel
├─ project schedule with bars?       → add_gantt
├─ phased roadmap with milestones?   → add_timeline
├─ budget / percentage breakdown?    → add_allocation_bars
├─ ecosystem orbiting a core?        → add_flywheel
├─ concentric layers (core → outer)? → add_layered_diagram
└─ multi-layer architecture?         → add_flow_matrix
```

If none fit, use primitives — forcing the wrong component is worse
than building it directly.

---

## Components

### `add_metric_card` — single big KPI

**Use when**: one slide spot shows one headline figure ("$12.4B
revenue", "+42% YoY", "5.4亿 MAU"). Place 2–4 side by side for a
KPI strip.
**Not for**: multi-line stat tables (use a real table), narrative
text blocks.

**content**: `{"kicker": str | None, "value": str (required), "desc": str | None}`
**variants**: `"tech"` (light card, default) · `"primary"` (brand-color bg, white text)

Notes
- `desc` supports `\n` for multi-line. Auto-greens `+/growth` keywords,
  auto-reds `-/decrease` keywords.
- One `variant="primary"` per slide. Using primary on every card kills
  the emphasis the variant is meant to provide.

---

### `add_quote_block` — pull quote / strategy callout

**Use when**: a quote, CEO message, design principle, or strategy
callout needs visual separation from body text.
**Not for**: long paragraphs (those are just body), short tagline
under a title (just style the run).

**content**: `{"kicker": str | None, "title": str | None, "copy": str (required), "author": str | None, "role": str | None}`
**variants**: `"line"` (soft bg + brand-color left rule) · `"dark"`

Notes
- Narrow tall box (`w < h`): the kicker is auto-hidden to avoid three
  text layers crammed sideways.
- For testimonials, pair `author` + `role`.

---

### `add_comparison` — 2-4 panels side by side

**Use when**: actual comparisons — old vs new, competitor vs us,
traditional vs recommended, plan A vs plan B.
**Not for**: parallel concepts. A card grid is the right shape for
"three things we offer"; comparison implies one wins.

**panels**: 2–4 entries, each:
```
{"kicker": str | None,
 "title": str (required),
 "tagline": str | None,
 "featured": bool | None,   # marks the "recommended" panel
 "items": [{"title": str, "desc": str | None, "number": str|int | None}, ...],
 "scale": {"value": str, "unit": str} | None}
```

Notes
- 2 panels → horizontal with center VS badge.
- 3 panels → horizontal, no badge.
- 4 panels → 2×2 grid.
- `featured=True` always renders rightmost; the renderer reorders.

---

### `add_swot` — 2×2 quadrant matrix

**Use when**: SWOT, opportunity/risk grid, probability×impact matrix,
investment decision matrix.
**Not for**: a generic 4-card grid — quadrants imply axes that
encode meaning.

**quadrants**: accepts SWOT keys, SWOT keys with titles, positional
`(highHigh, highLow, lowHigh, lowLow)`, or a 4-element array. See
the source for the exact shapes.

Notes
- 3–5 bullets per quadrant is the sweet spot.
- Recommended size: ≥ 8″ × 6.5″ — anything smaller crams the bullets.

---

### `add_radar` — multi-dimensional score

**Use when**: 4–6 dimension scoring (capability map, competitor
comparison across categories, evaluation criteria).
**Not for**: single-dimension comparison (use a bar chart), 2–3
dimensions (a radar with 3 spokes looks like a triangle, not a chart).

**dimensions**: `[{"name": str, "score": float, "desc": str | None}, ...]` — 4–6 entries.
**kwargs**: `rings`, `max_score`, `show_notes`.

Notes
- Wide container (`w ≥ 8″`): chart left, notes right.
- Single series only — multi-series radars get unreadable; use a chart.
- The data area is the brand color at ~28% **true opacity**
  (`<a:alpha>` via `helpers.set_fill_alpha`), so the rings + axes
  read through it. Tune with the `set_fill_alpha(poly, 28)` call in
  `components/radar.py` if you need it lighter or denser.

---

### `add_funnel` — conversion / stage funnel

**Use when**: stages with shrinking volume (TAM-SAM-SOM, conversion
pipeline, qualification stages).
**Not for**: equal-size stages (that's a process, use timeline /
flow_matrix), or anything growing.

**steps**: `[{"label": str, "value": str, "width": str | float}, ...]`
— `width` is `"26%"` or `0.26`, you control the taper.
**kwargs**: `title`, `note`, `orientation` (`"narrow_top"` default,
`"narrow_bottom"` classic Western).

Notes
- Caller-controlled per-step width — no auto-linear taper. If you
  want a smooth gradient of widths, compute them yourself.
- Color depth ramps light→dark from top to bottom.

---

### `add_gantt` — project schedule with monthly bars

**Use when**: project plan with task bars across a time axis,
optionally showing planned-vs-actual.
**Not for**: roadmaps where each phase is a discussion item — those
read better with `add_timeline`.

**groups (grouped mode)**:
```
[{"label": "Phase A",
  "desc": str | None,
  "tasks": [{"label": "Design",
             "plannedStart": int, "plannedEnd": int,
             "actualStart": int,  "actualEnd": int,
             "tone": "soft" | "dark" | None,
             "value": str | None     # short label inside actual bar
            }, ...]}]
```
**tasks (ungrouped mode)**: same task schema, flat list.
**kwargs**: `columns` (default `1月..12月`), `variant`, `legend`,
`legend_labels`.

Notes
- Tasks need `plannedStart/plannedEnd` and/or `actualStart/actualEnd`;
  `start`/`end` is a shorthand.
- Don't pass a title in the component — add a separate heading textbox
  above. The component owns the chart area only.

---

### `add_timeline` — phased milestones + delivery cards

**Use when**: phased roadmap with explicit deliverables, exit gates,
and a date axis. Heavier than `add_gantt`; better for executive decks
where each phase is a discussion item.
**Not for**: detailed task-level scheduling (use gantt).

**phases**: 3–6 entries:
```
{"label": "Q1",
 "title": "Discovery",
 "duration": "8 weeks" | None,
 "tone": "strong" | "dark" | None,
 "deliverables": [str, ...],
 "exit_gate": str | None}
```
**kwargs**: `boundary_dates` (length = `len(phases) + 1`).

Notes
- Three vertical bands: date axis · phase bars · delivery cards.
- Use `tone="dark"` on the current phase to mark "you are here."
- `boundary_dates` is off-by-one with `phases` — N phases need N+1
  boundaries. Easy to miscount.

---

### `add_allocation_bars` — percentage breakdown

**Use when**: budget split, revenue mix, time allocation, market share
breakdown. Each item gets a labeled progress bar.
**Not for**: 7+ slices (use a chart), changes over time (use lines).

**items**: 2–6 entries:
```
{"label": str,
 "value": str,                   # free-form right-aligned text, e.g. "¥19 万 · 31.7%"
 "percent": float,               # 0-100, drives bar length
 "tone": "accent" | "primary" | "green" | "soft" | "muted" | None,
 "color": RGBColor | None}       # explicit override
```
**kwargs**: `title`, `subtitle`, `note`.

Notes
- `value` is data, not a headline — caption sizing, not KPI-large.
- `note` shows as a footer (allocation principle / source / caveat).

---

### `add_flywheel` — center asset + orbiting nodes

**Use when**: a core asset/value + 3–6 supporting forces that reinforce
each other in a cycle.
**Not for**: hierarchies — those go in `add_layered_diagram` or
`add_flow_matrix`.

**center**: `{"title": str, "label": str | None}` (label is the
"CORE ASSET" kicker)
**nodes**: 3–6 entries: `{"label": "01", "title": str, "desc": str | None, "index": int | None}` — title is 8–14 CJK chars or roughly the same width in English.
**kwargs**: `start_angle_deg`, `direction` (`"clockwise"` / `"counterclockwise"`).

Notes
- Node count drives radial layout; widen the container for 5–6 nodes
  or labels collide.

---

### `add_layered_diagram` — concentric circles

**Use when**: nested layers from outer to inner (capability stack
with core → outer, system depth, "core surrounded by shells").
**Not for**: flat sequences (use a row of cards), hierarchies
without nesting (use `add_flow_matrix`).

**layers (outer → inner)**: 2–6 entries: `{"title": str, "tone": "strong" | None}`.
**kwargs**: `title`, `desc`.

Notes
- Concentric circles, not stacked rectangles — verify in the rendered
  output.
- Innermost layer can opt in to `tone="strong"` for emphasis. Outer
  ring lightest, inner darkest, solid fills only.

---

### `add_flow_matrix` — multi-layer architecture

**Use when**: explicit layered architecture / business ecosystem /
capability structure (输入层 / 理解层 / 匹配层 / 输出层).
**Not for**: a generic card grid — there must be a real layer
hierarchy with each row meaning something.

**rows**:
```
[{"leftLabel": "理解层",
  "nodes": [{"title": str, "desc": str | None}, ...]},
 ...]
```
2–4 nodes per row (5 max). Wrap into multiple rows if you have more.
**kwargs**: `title`, `platform` (`{"label": str, "desc": str | None}` — bottom strip).

Notes
- Rows have tinted band backgrounds; nodes inherit per-row depth.

---

## Footprint check

A correctly-built deck has these signals on visual-heavy slides:

- `<p:grpSp>` count > 0 — every component wraps its output in a group.
- Total `<p:sp>` per visual slide ≈ 8–20.
- Visible alignment is clean across rows / cells.

Hand-stacked rectangles produce 40–50 shapes per slide with no
groups; the matching component produces 8–15 with correct geometry.
If the deck shows `grpSp=0` everywhere with high shape counts on the
visual slides, swap the hand-built shapes for the matching `add_xxx`
call before delivery.
