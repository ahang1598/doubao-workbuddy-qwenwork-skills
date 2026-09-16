# style-catalog.md — the local style catalog

WorkRally has **no server-side preset service**. The Higgsfield original called
`get_faceless_channel_presets` to list cards and `resolve_faceless_channel_preset` to turn a
card into a style-reference media id. Neither exists here, so this file IS the catalog:
every shipped style is a Markdown file with a pinned STYLE FORMULA, and that formula plus
its canonical donor images are the whole style. Nothing is hot-updatable — a new style
means a new file in this directory.

Read this file in Phase 0 Round 2, offer the entries for the locked channel type by name,
and quote each one-liner **verbatim** from its own style file. Never improvise a style
description, never name a real studio, brand or IP.

## Entries

| Style | Style file | Home channel | Anchor |
|---|---|---|---|
| **Editorial Motion Graphics** | `style-editorial-collage.md` | Explainer + History (house default for both) | FORMULA + 1 canonical ref |
| **Stickman Cartoon** | `prompts.md §0` (generic webcomic formula) | Explainer (second main direction) | FORMULA only, no ref |
| **Paper Diorama** | `style-paper-diorama.md` | History (named alternate) | FORMULA + 1 canonical ref |
| **Mannequin** | `style-mannequin.md` | History (named alternate) | FORMULA + 2 canonical refs + LOCKED CAST |
| **Watercolor Chronicle** | `history-longform.md` | History long-form (≥10 min / documentary) | FORMULA + 1 canonical ref |
| **Studio 3D** | `kids-styles.md` | Kids (default) | FORMULA + 2 canonical refs |
| **Pastel Flat 2D** | `kids-styles.md` | Kids | FORMULA + 3 canonical refs |
| **Colorful 3D** | `kids-styles.md` | Kids | FORMULA + 2 canonical refs |
| **Hand-drawn Ink** | `kids-styles.md` | Kids | FORMULA + 4 canonical refs |
| **Poster Vector** | `kids-styles.md` | Kids | FORMULA + 3 canonical refs |
| **Frame by frame** (direction) | `picture-flow.md` | Picture Story — locks the stills MECHANICS | Flat 2D Papercraft FORMULA |
| **Fairy Tale & Myth** (direction) | `style-cinematic-storybook.md` | Fairy Tale & Myth — locks on-twos + mysterious-calm bed | FORMULA + 3 canonical refs |
| **Custom** | — | any | the user's own ≤3 style images, or a free description |

Per-channel defaults, the CROSS-CHANNEL STYLE RULE, and the long-form auto-lock all live
in `intake-and-dispatch.md` Round 2. This file only answers "which styles exist and where
is each one written down".

## Canonical reference images

Every canonical ref URL in the style files lives on a CDN that is **not** in WorkRally's
`input_images` allowlist. For each ref:

```bash
curl -fsSL -o ref1.jpg '<canonical url>'
```

then `upload_file(file_path="<abs path>/ref1.jpg")` and use the returned WorkRally URL in
`input_images`. A ref that will not download is not fatal: the pinned FORMULA alone is a
valid anchor — generate the style key from the formula and tell the user the style is
formula-only for this run. Never substitute a different image and never claim a canonical
donor was used when it was not.

## Styles that did NOT survive the port

The Higgsfield catalog also carried thirteen cards with **no style file**: Fluffy Toy, 3D
Papercraft, Mixed Media, Whiteboard Doodle, Pixel Art, Claymotion, Low Poly, Isometric
Flat Vector, 3D Mix, 2D Illustrator, Dynamic Motion Design, Vintage Documentary, Custom
Template. Their entire definition was server-hosted card art: the agent resolved the card
to a `media_id` and derived a formula from the picture. Without that service there is
nothing to derive, so they are gone.

If a user names one, say plainly that it is not available in this plugin, offer the closest
shipped style, and write the formula from the user's own description. Do **not** invent a
formula and present it as that preset.
