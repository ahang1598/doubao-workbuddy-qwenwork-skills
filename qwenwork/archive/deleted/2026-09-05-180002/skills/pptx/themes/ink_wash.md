# Theme — Ink Wash

**Voice**: classical Chinese; ink-wash painting; seal stamp; vertical
couplet.
**Fit**: classical Chinese **poetry** (古诗词 / 唐诗 / 宋词), 节气, 国学,
国画, 国风, 水墨, traditional culture.
**Don't fit**: modern city introductions, product launches, investor
decks, travel intros, data reports — the single-character vertical
layout + vermilion seal will ruin those. If a prompt mixes classical
*and* modern (e.g. "唐诗 NLP 项目复盘"), pick one of the modern
archetypes and use ink-wash *imagery* sparingly.

## Palette

| Slot | Hex | Name |
|---|---|---|
| primary | `#282624` | ink |
| secondary | `#AA2E28` | vermilion (seal) |
| accent | `#A08044` | gold |
| muted | `#766E60` | warm gray |
| bg | `#F2EADA` | rice paper |
| on_bg | `#282624` | ink |

## Fonts

- header: `Noto Serif SC`
- body: `Noto Serif SC`

(One face throughout; weight handles hierarchy.)

## image_style suffix

> `ink wash painting, rice paper texture, vast negative space, single
> vermilion accent, muted sepia, no text, no faces`

## Grammar

Full paper bg `#F2EADA`.

- **Cover**: tracked gold eyebrow + 84pt horizontal title + small
  vermilion seal at lower-right.
- **Body**: single column right-aligned, generous top margin, one
  ink-wash motif per spread.
- **Closer**: empty paper + small vermilion seal.

## ⚠ charSpacing cap (critical for this theme)

**Cap `charSpacing` (`spc`) at 200** (= 2.0pt). Larger values render
as single-character vertical columns in PowerPoint. Safe range:
`0–200`.

This applies to every theme but bites ink-wash hardest because
classical Chinese typography invites tracking — when 节气 / 唐诗 /
宋词 titles are tempting to space out for elegance, the renderer
rebels above 200. Stay under it; if you want more breathing room,
use larger font size, not larger spacing.

## Forbid

- Rounded corners
- Shadows
- Gradients
- Multi-color palettes (one ink + one accent + paper; that's it)
- Sans-serif body fonts
