# Styling tokens (qwenwork palette)

Mirrors the QwenWork web app design. You should not need to override these
unless asked — they're applied automatically.

## Colours

| Role | Value |
|---|---|
| Page background | `#ffffff` |
| Secondary surface (code, table head) | `#f4f3f0` / `#f4f5f2` |
| Primary text | `#3d3d39` |
| Secondary text (60% alpha) | `rgba(61, 61, 57, 0.6)` |
| Muted text | `#757069` |
| Border (component) | `#e9e9e7` |
| Border (soft) | `rgba(126, 126, 87, 0.16)` |
| Brand accent | `#f27348` (orange) |
| Code text | `#56534e` |

### Callout accents
- `note` icon `#5b8aa6`
- `tip` icon `#3a7a44`
- `warning` icon `#b8862c`
- `danger` icon + title `#b03a3a`

## Typography

| Role | Family |
|---|---|
| Body / Latin | `Inter` (static woff2) |
| Chinese | `Noto Sans SC` |
| Japanese | `Noto Sans JP` |
| Monospace / code | `JetBrains Mono` |

Body font-size: **11 pt**. Line-height: **1.75** for body, **1.45** for code,
**1.3** for headings.

Heading sizes:
- h1 1.85em, h2 1.4em (with bottom border), h3 1.18em, h4 1.02em,
  h5 0.95em (muted), h6 0.88em (secondary, uppercase, letter-spacing).

## Page geometry

- Page sizes: A4 (default) and Letter (`-p Letter`).
- Margins: top 16 mm, bottom 18 mm, left/right 18 mm.
- Header (page 1 only): QwenWork wordmark + thin divider.
- Footer (every page): centred `N / total` page numbers.

## Borders & radius

- Default radius: `8 px`.
- Large radius (cards): `12 px`.
- Small radius (inline elements): `4 px`.
