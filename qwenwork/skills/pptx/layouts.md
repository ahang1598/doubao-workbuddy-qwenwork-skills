# Slide Layouts (13.333 × 7.5 in)

Verified slot tables for slide composition. Slide layout is unforgiving
— the canvas is 13.333″ × 7.5″, EMU conversions are easy to get
off-by-one on, and a card that's 0.1″ too wide will silently overlap
its neighbor in the rendered output but look fine in code.
**Prefer the slot tables below over deriving coordinates by hand**
when one of these layouts fits your slide. For layouts not listed:
derive carefully and then verify with `view_issues.py check_overlap`
before delivery.

These layouts describe slot geometry only, not visual style. Palette, type,
and cover composition come from the selected or invented direction in
[visual-directions.md](visual-directions.md), optionally informed by
`frontend-design` when available.

## Canvas

```
W = 13.333  H = 7.5             # inches
Safe margins: side = 0.6  top = 0.55  bottom = 0.55
Inner area:   Iw = 12.133  Ih = 6.40
```

## Layouts

```python
# Layout A — full-bleed title (cover)
TITLE_BOX  = (0.60, 0.55, 12.133, 1.10)          # x, y, w, h (inches)
SUB_BOX    = (0.60, 1.80, 12.133, 0.80)

# Layout B — 50/50 text-left + image-right
B_TITLE    = (0.60, 0.55,  5.80, 1.10)
B_BODY     = (0.60, 1.80,  5.80, 5.15)
B_IMAGE    = (6.85, 0.00,  6.483, 7.50)          # full-bleed right half

# Layout C — top title + 3 cards in a row (metric_card / swot etc.)
C_TITLE    = (0.60, 0.55, 12.133, 1.10)
C_CARD_1   = (0.60, 2.00,  3.84, 4.95)           # 0.3" gutters
C_CARD_2   = (4.74, 2.00,  3.84, 4.95)
C_CARD_3   = (8.88, 2.00,  3.84, 4.95)

# Layout D — top title + 2 cards in a row (comparison)
D_TITLE    = (0.60, 0.55, 12.133, 1.10)
D_CARD_L   = (0.60, 2.00,  5.86, 4.95)
D_CARD_R   = (6.86, 2.00,  5.86, 4.95)

# Layout E — top title + text-left + image-right (40% image)
E_TITLE    = (0.60, 0.55, 12.133, 1.10)
E_BODY     = (0.60, 2.00,  6.80, 4.95)
E_IMAGE    = (7.65, 2.00,  5.08, 4.95)
```

## Combinations to avoid

- **Don't pair Layout C (3 cards) with a big image.** Cards occupy the
  entire bottom strip; any image >2″ wide eats a card. Use Layout B
  or E for image + text instead.
- **Bounds check on every shape.** `x + w ≤ 13.333` and `y + h ≤ 7.5`,
  always. A shape that hangs off the canvas renders fine in PowerPoint
  but truncates in PDF / image export.
- **No deliberate overlap unless designed in.** If you want a hero
  photo with a floating title, that's fine — `check_overlap` will flag
  it as `info`. Make sure z-order puts the photo first so the title
  reads on top.

## Custom cover composition

The generic A–E layouts cover most content slides but not distinctive cover
pages. If the deck's direction calls for a signature composition (a split
panel, a hairline frame, a full-bleed hero with an offset title block, etc.),
lay it out directly with primitive shapes. Pick coordinates that keep to the
safe margins above and pass `view_issues.py check_overlap`; invent a different
composition when that better serves the story.
