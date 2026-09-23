# Brandbook

Create the Brandbook when logo, palette, and typography are each approved. Never ask for an additional combined Essential Kit approval.

## Required inputs

Read the approved kit from the brand job's working directory (see `handoff.md`):

```bash
python3 <skill dir>/scripts/brandkit.py state --action get_essential_kit
```

Require these separately approved slots:

- approved logo — an SVG when the user supplied one, otherwise the approved raster PNG. The builder
  rasterizes both to a 2000×2000 square, so a generated raster mark is fine here.
- approved palette (1–5 primary colors)
- approved display/body typography
- approved brand concept/summary copy supplied by the user
- optional approved mockups

`logo.asset` and every mockup entry may be a local path or an HTTPS URL. **Download WorkRally
results to local files first** and pass those paths — short links expire after about 5 hours and a
build that starts before the link dies can still fail partway through.

Do not invent mission, values, claims, product variants, prices, statistics, or brand-story copy.

## Preflight — this build can be unavailable

The bundled build script is the only canonical Brandbook path, and it has hard external
dependencies. Check them **before** telling the user a brandbook is coming:

| Need | Check | If missing |
|---|---|---|
| `docs.google.com` and `fonts.googleapis.com` reachable | `curl -sI https://docs.google.com` | The build cannot run. Say so plainly. |
| `soffice` (LibreOffice) | `command -v soffice` | `brew install --cask libreoffice`, or stop |
| `pdffonts` (Poppler) | `command -v pdffonts` | `brew install poppler`, or stop |
| `fc-cache` / `fc-match` (fontconfig) | `command -v fc-cache` | `brew install fontconfig`, or stop |
| `rsvg-convert` + ImageMagick | `command -v rsvg-convert magick` | `brew install librsvg imagemagick`, or stop |

The canonical template and the approved Google Fonts are downloaded from Google at build time. On a
network that cannot reach Google, **the brandbook cannot be produced by this skill.** Say exactly
that, offer the alternatives the user actually has (a non-canonical deck via
`presentation-deck.md`, or the individual approved assets), and **never claim a PPTX or PDF was
generated when it was not.**

## Canonical template

Use the supplied PPTX as the exact source template:

```text
https://docs.google.com/presentation/d/1rAfUJ-PbZ4S-h3puYSUHpE5UIcdKyRw1/export/pptx
```

Reference PDF:

```text
https://drive.google.com/uc?export=download&id=146zm9NXkGAxgKgQrGL7JywoqeRxXnWmk
```

The bundled Brandkit build script owns this fixed URL and the versioned template contract. Do not download, inspect, recreate, or edit the template manually.

## Interaction policy

Do the work quietly. At most, tell the user once that the brandbook is being prepared. Do not narrate template download, shape inspection, terminal commands, implementation choices, logo conversion, or slide-by-slide progress. Tool activity may appear in the interface automatically; do not duplicate it in assistant prose.

## Local build

Write one JSON input with this complete shape. Replace values, not keys or nesting:

```json
{
  "brand_name": "Northline",
  "concept_summary": "A precise identity built around directional movement and calm technical confidence.",
  "palette_summary": "Ink and Paper establish clarity while Signal Blue marks moments of action.",
  "secondary_logo_url": "",
  "mockups": [
    {
      "url": "https://replace-with-approved-mockup.png"
    }
  ],
  "revision": 1
}
```

Call the builder exactly once, from the brand job's working directory, as a **backgrounded local
shell command** — the template download, font resolution, and LibreOffice conversion routinely
exceed a foreground timeout. Redirect its output to a log and poll that log rather than blocking:

```bash
python3 <skill dir>/scripts/brandkit.py brandbook-build \
  --input brandkit/brandbook.json > brandkit/build-result.json
```

The script reads separately approved logo, palette, and typography slots directly from `.brandkit/state.json`; do not duplicate them in the input. It downloads only the fixed canonical template, performs the deterministic build and QA, resolves the exact approved fonts, and converts the exact PPTX bytes into the matching verified PDF.

After the command exits 0, read `files[0]` (PPTX) and `files[1]` (PDF) from `brandkit/build-result.json` with `jq -r`. Those are local paths and they are the deliverable. Push them into the WorkRally asset library with `upload_file` (+ `asset_create`) only when the user asks for that.

## Fixed seven-slide structure

Preserve slide size, masters, layout, margins, grids, text-box positions, image zones, alignments, and hierarchy. Also preserve every element's exact x/y position, width, height, crop, rotation, stacking order, font size, paragraph spacing, line spacing, and alignment unless a conditional rule below explicitly requires duplication/removal.

1. **Cover**
   - Brand Guidelines
   - Real brand/product name

2. **Branding concept**
   - Approved concept summary
   - Approved palette rationale

3. **Primary logo**
   - Exact approved SVG

4. **Logo system**
   - Primary logo
   - Show a secondary slot only when the user supplied or explicitly requested an approved alternate/monochrome/reverse version
   - Place an approved secondary as a transparent PNG with no background rectangle
   - If no secondary is approved, remove its label and image slot; do not generate one automatically
   - Never invent a secondary logo

5. **Primary palette**
   - Replace every template swatch with approved colors
   - Replace names, RGB values, and hex values
   - Keep title/rationale boxes in their exact template positions
   - Keep each color name, RGB value, and hex value close together directly beneath its swatch; preserve the template's compact vertical spacing
   - Set each swatch label independently to a readable contrasting color; the darkest swatch must use light text
   - Do not add swatch borders. Add a minimal keyline only when the swatch color matches the slide background and would otherwise disappear.
   - Fit all approved colors into the existing palette component/grid without changing the slide's overall hierarchy

6. **Typography**
   - Approved display font
   - Approved body font
   - Use the real fonts throughout the document
   - Show both font specimens at exactly the same point size and in equal-height text boxes
   - Keep both baselines/positions aligned to the template
   - Never shrink only one specimen. If either overflows, reduce both together or shorten the approved specimen copy
   - Render and inspect the slide to prove that neither name/specimen is clipped, substituted, overlapped, or partially off-canvas

7. **Mockups**
   - Exactly two approved mockups per slide

## Conditional mockup slides

- No approved mockups → remove Slide 7.
- One mockup → use the first image zone and remove the second; do not redesign the template grid.
- Two mockups → use one mockup slide.
- More than two → duplicate the exact mockup slide for every additional pair.
- Never place generated-but-unapproved mockups in the brandbook.

## Brand-specific styling

The canonical template controls geometry. The separately approved foundation slots control styling:

- Replace template colors with approved palette colors.
- Replace template fonts with approved fonts.
- Set every slide title in the approved display font, retain the template's exact font size, use normal letter spacing, expand its box within margins, disable wrapping, and keep it on one line.
- Choose an approved title color with at least 3:1 contrast against the slide background; title and background may never be identical.
- Keep body copy in the approved body font without auto-shrinking.
- Render the exact approved logo into distortion-safe square media slots; never stretch it or regenerate its geometry.
- Crop mockup images to the template's 3:4 slots before placement; never stretch width and height independently.
- Use approved copy only.
- Preserve readable contrast.
- Do not add decorative motifs or sections not present in the template.

## Output

Deliver:

- editable `.pptx`
- matching `.pdf`

Render page previews for internal QA only. Do not send the brandbook page by page and do not embed slide previews in the final response.

The bundled renderer runs LibreOffice locally and verifies embedded fonts with Fontconfig and Poppler. Never generate a separate ReportLab/custom PDF and never hand-write a PowerPoint script as a substitute. If conversion is unavailable or times out, stop and report the script error — do not describe an unbuilt PDF as delivered.

A template/contract/style mismatch is deterministic. Do not retry it, present “retry Brandbook” as a next step, or dump the locked Brandkit contents into the response. Report the error in one concise sentence and stop.

The script resolves the exact approved TTF/OTF/WOFF/WOFF2 files from their public or `google:` sources before conversion. Conversion fails if Fontconfig substitutes a family or if `pdffonts` cannot confirm both approved families in the PDF. The user still needs those fonts installed to edit/view the PPTX faithfully.

Use stable names:

```text
<brand>-brand-guidelines-v<revision>.pptx
<brand>-brand-guidelines-v<revision>.pdf
```

## QA and approval

Before delivery:

1. Render every slide.
2. Check clipping, overflow, font substitution, image crop, and alignment.
3. Reject any wrapped/overlapping title or title below 3:1 background contrast.
4. Verify logo geometry and palette values.
5. Confirm the PDF visually matches the PPTX.
6. Remove all template placeholder text.

The final response contains only:

1. one PPTX download link
2. one PDF download link
3. one concise warning naming the display/body fonts the user must install for correct editable-PPTX display (include official download links when known)

Do not show page cards, inline images, contact sheets, or screenshots.

Wait for explicit approval. Only then write an `approve_brandbook_element` payload with `required_slots` set to `["logo", "palette", "typography"]` and call the Brandkit state script.
