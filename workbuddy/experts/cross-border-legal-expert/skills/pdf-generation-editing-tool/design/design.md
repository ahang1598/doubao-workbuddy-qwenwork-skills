# Design System

The aesthetic layer. Read this before touching any script.
This file answers "what should it look like and why."

---

## The one rule

Every design decision must be **rooted in the document's content and purpose**.
Dark teal + cream is not "professional". Serif + beige is not "elegant".
A color chosen because it fits the content will always outperform a color chosen
because it seems safe.

---

## Palette logic

`palette.py` takes a short content description and outputs `tokens.json`.
Here is the reasoning it applies:

### Mood → base palette

| Content signal                      | Mood          | Background               | Accent               | Text                     |
| -------------------------------------| ---------------| --------------------------| ----------------------| --------------------------|
| Research, science, analysis         | Authoritative | `#0F1F2E` deep ink       | `#00B4A6` teal       | `#F0EDE6` warm white     |
| Business, strategy, finance         | Confident     | `#1C1C2B` near-black     | `#E8A020` amber      | `#F5F2EC` cream          |
| Creative, portfolio, design         | Expressive    | `#1A0A2E` deep violet    | `#FF6B6B` coral      | `#FAF5FF` lavender white |
| Education, academic paper           | Scholarly     | `#FAFAF7` warm white     | `#2C4A7C` navy       | `#1A1A2E` dark           |
| Healthcare, wellness                | Calm          | `#F5F9F8` pale mint      | `#2D8B72` forest     | `#1E3830` deep green     |
| Resume / personal                   | Clean         | `#FFFFFF` white          | pick from content    | `#111111` near-black     |
| General / unknown                   | Neutral       | `#F8F6F1` warm off-white | `#3D3D3D` dark gray  | `#1A1A1A` black          |
| Formal publications, annual reports | Magazine      | `#F2F0EC` warm linen     | `#1C3557` deep navy  | `#0D1A2B` near-black     |
| Premium/dark reports, tech reviews  | Darkroom      | `#151C27` deep navy      | `#4A6FA5` steel blue | `#F0EDE6` warm white     |
| Technical docs, developer reports   | Terminal      | `#0D1117` near-black     | `#39D353` neon green | `#E6EDF3` cool white     |
| Portfolios, creative, photography   | Poster        | `#FFFFFF` white          | `#0A0A0A` near-black | `#0A0A0A` near-black     |

### Accent selection rules

- **Only one accent color.** Appears only on: cover geometric elements, section rules, callout left borders, table header background, page header rule.
- Accent must contrast ≥4.5:1 (WCAG AA) against the cover background; don't default to blue (most overused AI accent).

### Color pairing anti-patterns (never use these)

禁用：紫色渐变白底（默认 AI 味）、藏青+金（企业俗套）、纯黑背景（打印差）、>3 色（视觉噪声）、正文用强调色（破坏可读性）。

---

## Typography system

### Font pairing logic

Two typefaces maximum. Always.

| Role | Criteria | Good choices (system-safe) |
|---|---|---|
| Display (cover title, H1) | Distinctive, strong contrast, high weight | Times New Roman, Georgia (serif) |
| Text (body, captions, UI) | Highly readable at 10–11pt | Helvetica, Arial (sans) |

Cover fonts are loaded live via `@import url(...)` in the cover HTML (rendered by reportlab); body pages always use system fonts (Times-Bold/Helvetica) — offline-safe.

Pairs by mood (cover HTML only — body always uses system fonts): Authoritative `Playfair Display`/`IBM Plex Sans`; Confident `Syne`/`Nunito Sans`; Expressive `Fraunces`/`Inter`; Scholarly `EB Garamond`/`Source Sans 3`; Clean `DM Serif Display`/`DM Sans`; Restrained `Cormorant Garamond`/`Jost`; Bold `Barlow Condensed`/`Barlow`; Dynamic `Montserrat`; Classical `Cormorant`/`Crimson Pro`; Editorial `Bebas Neue`/`Libre Franklin`; Body fallback `Times-Bold`/`Helvetica`.

### Type scale

All sizes in points. This scale is used by `palette.py` to populate `tokens.json`.

| Token | Size | Leading | Usage |
|---|---|---|---|
| `display` | 54pt | 1.0 | Cover title |
| `h1` | 22pt | 1.3 | Section headings |
| `h2` | 15pt | 1.4 | Subsection headings |
| `h3` | 11.5pt | 1.5 | Sub-subsection |
| `body` | 10.5pt | 1.6 | Main prose |
| `caption` | 8.5pt | 1.4 | Figure/table captions |
| `meta` | 8pt | 1.3 | Header/footer text |

### Spacing system

Margins and rhythm are what separate "looks designed" from "looks printed".

| Token | Value | Notes |
|---|---|---|
| `margin_outer` | 2.8cm | Left/right page margin |
| `margin_top` | 2.8cm | Top page margin |
| `margin_bottom` | 2.5cm | Bottom page margin |
| `section_gap` | 26pt | Space before H1 |
| `para_gap` | 8pt | Space after paragraph |
| `line_gap` | 17pt | Leading for body text |

Never use ReportLab's default margins (too tight). Always set explicitly.

---

## Cover design

The cover is the most important page. It determines whether a reader trusts the document.

### Thirteen cover patterns

`cover.py` selects one based on `tokens.json["cover_pattern"]`.

| Pattern | Used for | Layout |
|---|---|---|
| `fullbleed` | report, general | full-bleed background + large left title + accent rule |
| `split` | proposal | 42% solid panel + 58% off-white, hard accent divider |
| `typographic` | resume, academic | oversized display type, accent first word |
| `atmospheric` | portfolio | near-black + radial accent glow |
| `minimal` | minimal | white + 8px accent bar only |
| `stripe` | stripe | three horizontal bands |
| `diagonal` | diagonal | SVG diagonal cut |
| `frame` | frame | inset rectangular border, classical |
| `editorial` | editorial | ghost letter + condensed uppercase title |
| `magazine` | magazine | centered stack, serif title, optional hero |
| `darkroom` | darkroom | magazine layout on deep navy |
| `terminal` | terminal | near-black + neon green monospace + grid |
| `poster` | poster | 52px sidebar + 96px condensed title |

### Optional token: `cover_image`

Patterns `magazine`, `darkroom`, and `poster` accept an optional `cover_image`
token containing an absolute URL or `file://` path to an image.
The image renders via `<img src="...">` — fetched at render time.
If omitted, the image area is simply skipped (layout adjusts gracefully).

### Cover CSS requirements

These three rules must appear in every cover HTML file or the output will have
white borders / incorrect dimensions:

```css
body { margin: 0; padding: 0; }
html, body { width: 794px; height: 1123px; overflow: hidden; }
```

No `@page` rules needed — handled via the `write_pdf()` call.
Do NOT use CSS `background-image` for textures — use inline SVG or `<canvas>`.
Always use `position: absolute` + `z-index` for layered elements.

### What always kills a cover

白底居中标题+细线、渐变色（读作 PPT 而非印刷）、文字投影、多强调色、emoji/图标字体（可能静默失败）。

---

## Inner page rules

### What "restraint" means in practice

Every design decision should remove something, not add something.
The page is done when there is nothing left to remove.

- Accent color appears on section rules only — not on headings, not on bullets
- No card components (bordered boxes with colored headers)
- No rounded corners on anything except callout boxes (4px max)
- No shadows anywhere
- Tables: header row in accent, alternating row tint, no grid lines except outer box
- Callout boxes: left border in accent (4px), very light tint background, no icon

### Page header / footer

Header: document title (left, 7.5pt, muted) + accent rule (1.5pt, full width below)
Footer: author name (left, 7.5pt, muted) + page number (right, 7.5pt, muted) + light rule above

---

## Quality bar

A PDF passes if a designer would not be embarrassed to hand it to a client.
Concretely:

- Cover has a clear visual identity that is not "generic AI output"
- Body text is readable at arm's length without squinting
- Every page looks like it belongs to the same document
- No element bleeds off the edge or overlaps another
- Page numbers are present and correct
- The accent color appears fewer than 8 times per page on average

---

## Block type reference

全部 body block 类型及字段定义见 `SKILL.md` 的「content.json block types」表；渲染样式（accent 规则、表格斑马纹、标题不孤立等）统一由 `render_body.py` 处理，配色与字体一律取自 `tokens.json`，不得硬编码。

