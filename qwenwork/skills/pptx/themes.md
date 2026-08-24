# Theme Taste Doc — Index

A taste reference for picking palette, fonts, and visual grammar when
no brand template fits. **This is not a catalog you must select from.**
The 7 archetypes below cover the common ground; invent a new one when
the topic asks for something none of them serve.

After picking an archetype, read the per-theme file for palette hex
values, fonts, image-style suffix, grammar, scar-tissue warnings, and
forbid rules. The per-theme files are the load-bearing docs — this
file just helps you pick.

---

## Pick an archetype

| Archetype | Use when… | Don't use when… | File |
|---|---|---|---|
| **Business Deep Blue** | Investor decks, QBR, earnings, financial reviews, strategy. Default fallback for generic prompts. | City / culture / poetry / lifestyle / marketing. | [themes/business_deep_blue.md](themes/business_deep_blue.md) |
| **Magazine Editorial** | Feature stories, **city / travel / culture intros**, long-reads, print-style essays. | Dense data dashboards, financial reports. | [themes/magazine_editorial.md](themes/magazine_editorial.md) |
| **Dark Editorial Photo** | Cinematic launches, luxury, photo essays, fashion editorials. | Anything without strong photography to drive it. | [themes/dark_editorial_photo.md](themes/dark_editorial_photo.md) |
| **Ink Wash** | Classical Chinese poetry (古诗词), 节气, 国学, 国画, 国风, 水墨. | Modern intros, products, investor decks, data reports. | [themes/ink_wash.md](themes/ink_wash.md) |
| **Swiss** | Type-driven, gallery / poster / brand book, manifestos. Yellow flavor or IKB flavor. | Financial decks, classical content, anything needing warmth. | [themes/swiss.md](themes/swiss.md) |
| **ESG / Sustainability** | ESG reports, green-tech, NGO storytelling, mission-driven. | Aggressive sales, financial dashboards. | [themes/esg.md](themes/esg.md) |
| **Academic / Research** | Academic talks, research summaries, technical papers. | Marketing, lifestyle, anything that wants to feel "designed." | [themes/academic.md](themes/academic.md) |

After picking: **read the linked per-theme file**. It has palette,
fonts, image_style, grammar, and scar-tissue you'll need to author
the deck. Don't author from the table above alone.

For slot geometry that works across themes (3-card row, 50/50 split,
text + image), see [layouts.md](layouts.md).

### When more than one archetype fits, ask once

Most prompts pick themselves. Some genuinely sit between two
archetypes where the choice shifts the whole deck — e.g. a city
intro that could lean Magazine Editorial (cultural / lifestyle) or
Business Deep Blue (urban-finance) depending on audience.

When that happens, present the 2–3 plausible archetypes with a
one-line reason each and ask the user to pick. Don't list all 7 —
the value is narrowing. Don't ask about font names, hex colors, or
page counts; just the archetype.

---

## Wiring (same for every archetype)

Every theme file gives you a palette and a font pair. Wire them up
the same way:

```python
from helpers import Style, Palette, FontPair
from pptx.dml.color import RGBColor

def _rgb(h: str) -> RGBColor:
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

# Copy from the theme file you read.
style = Style(
    palette=Palette(
        primary=_rgb("0F2044"),
        secondary=_rgb("C8A55A"),
        accent=_rgb("A6332A"),
        muted=_rgb("766E64"),
        bg=_rgb("F5F2EC"),
        on_bg=_rgb("1C2028"),
    ),
    fonts=FontPair(header="Source Serif 4", body="Inter"),
)

# Declare the deck's image_style ONCE; append to every image_prompt.
image_style = (
    "corporate architecture, blue glass facade, dusk light, cool tones, "
    "no text, no logos"
)
prompt = f"Shanghai pudong skyline at dusk — {image_style}"
```

Pass `style` to every `add_xxx(slide, origin, size, content, style)`
call. Components read `style.palette.{primary,secondary,…}` and
`style.fonts.{header,body}`.

### Font portability

Theme font names express design intent, not a license to make rendering
platform-dependent. Before authoring, check the fonts available in the active
renderer and on the target platform. If a theme font is missing, keep its
serif/sans role and use a metric-safe fallback:

| Theme intent | Portable fallback |
|---|---|
| Inter or another neutral sans | Arial or Calibri |
| Source Serif 4, Playfair Display, or Lora | Cambria |
| CJK sans | Microsoft YaHei on Windows; PingFang SC on macOS; Noto Sans CJK SC on Linux |
| CJK serif | SimSun on Windows; Songti SC on macOS; Noto Serif CJK SC on Linux |

Give non-portable display fonts extra width and height slack. Keep body text on
the portable fallback whenever fit matters.

---

## Inventing your own archetype

If none of the seven fit (e.g. "70s sci-fi fanzine", "kindergarten
recap", "wabi-sabi tea ceremony"), invent the palette, fonts, and
grammar fresh. Three rules:

1. **Pick 4–6 colors with one dominant.** Primary at 60–70% visual
   weight, one or two supporting tones, one sharp accent. Equal-weight
   palettes look unintentional.
2. **Pick a font pair with contrast.** One display, one body. Same
   family is fine if you vary weight and size.
3. **Write the grammar down.** Even 3–4 sentences telling future-you
   how cover / body / closer should look. Without it, the deck drifts
   slide-to-slide and you'll feel the inconsistency in QA.

Then declare an `image_style` suffix (one phrase, append to every
image prompt) and pick from the verified slot tables in
[layouts.md](layouts.md). Done.

---

## What's *not* prescriptive

- Exact palette hex / font names from a theme file — swap them when
  the topic asks. The grammar matters more than the swatches.
- The archetype list — invent one if the prompt fits none.
- Keyword routing — there's no `pick_theme()`. You decide.

---

## What lives in `helpers.py`, not here

`helpers.py` exports `Style`, `Palette`, `FontPair` — the dataclasses
every component reads. The per-theme files tell you *what to put
inside* them; `helpers.py` tells you *how to wire them up*. There is
no `themes.py` on purpose: archetypes are taste, not configuration.
