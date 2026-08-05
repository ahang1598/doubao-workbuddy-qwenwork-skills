---
name: pptx
version: 2.0.2
description: "Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions \"deck,\" \"slides,\" \"presentation,\" or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill."
description_zh: "当 .pptx 文件以任何方式涉及时使用此技能——无论是作为输入、输出还是两者兼有。包括：创建幻灯片、演示文稿或路演材料；读取、解析或提取任何 .pptx 文件中的文本（即使提取的内容将用于其他地方，如邮件或摘要）；编辑、修改或更新现有演示文稿；合并或拆分幻灯片文件；使用模板、布局、演讲者备注或批注。当用户提及\"幻灯片\"、\"演示文稿\"、\"PPT\"或引用 .pptx 文件名时触发，无论他们计划如何使用内容。只要需要打开、创建或操作 .pptx 文件，就使用此技能。"
---

# PPTX creation, editing, and analysis

Under the hood a `.pptx` is just a ZIP of XML parts. Let the task pick the approach:

| Task | Approach |
|---|---|
| **Create** a fresh deck | Author a `pptxgenjs` script — mind the gotchas below |
| **Edit** an existing deck, or fill a template | unzip → hand-edit `ppt/slides/slideN.xml` → zip back up |
| **Read** content | `markitdown deck.pptx` (each slide is one block under a `<!-- Slide number: N -->` marker); for a visual overview: `python scripts/contact_sheet.py deck.pptx` |

## Scripts

All paths below are relative to this skill's directory. Anything not listed is ordinary Python, `node`, or shell.

| Script | What it does |
|---|---|
| `scripts/contact_sheet.py deck.pptx [prefix]` | Renders a labeled grid of every slide so you can eyeball template layouts. `.pptx` only. Always give it a `prefix`; the default is `thumbnails`, and reusing it clobbers the grid from any other deck processed in the same folder |
| `scripts/deck_clone.py unpacked/ slide2.xml [--after slideN.xml]` | Clones a slide (or a `slideLayoutN.xml`) and performs every package registration for you. Can also operate on a `.pptx` directly when you pass `-o out.pptx` |
| `scripts/deck_prune.py unpacked/` | Deletes slides, media, and rels nothing points at anymore. Run it **only once `<p:sldIdLst>` is settled** |
| `scripts/oxml/package_audit.py deck.pptx [--original src.pptx]` | Runs schema, relationship, content-type, chart, and slide checks; every failure spells out its fix. For a template-derived deck, add `--original` so the schema checks are diffed against the template and its own XSD quirks aren't blamed on you |
| `scripts/oxml/lo_bridge.py --headless --convert-to pdf deck.pptx` | A LibreOffice wrapper — calling bare `soffice` hangs inside this sandbox |

## Creating with pptxgenjs — gotchas

`pptxgenjs` ships preinstalled — skip `npm install` and `require('pptxgenjs')` straight away. Only if that require throws should you run `npm install pptxgenjs`. You already know the API; what follows are the traps:

- **Set `pres.layout` before you add any slide.** The default canvas is `LAYOUT_16x9` = **10" × 5.625"**, not 13.3" wide. Anything placed past the edge is written out, not clamped — the shape simply never appears. (`LAYOUT_WIDE` gives you 13.3" × 7.5".)
- **Hex colors: no `#`, no 8 digits.** Write `color: "FF0000"`. Both `"#FF0000"` and an alpha baked into the hex (`"00000020"`) **corrupt the file**. For see-through effects use `transparency: 0-100` on fills and images, and `opacity: 0.0-1.0` on shadows — each is quietly dropped on the wrong one.
- **pptxgenjs rewrites option objects in place** (values become EMU on first use). Never hand the same `shadow`/options object to two `add*` calls — construct a new one every time.
- **A shadow `offset` must be ≥ 0** — a negative value corrupts the file. To throw a shadow upward, pair `angle: 270` with a positive offset.
- **`letterSpacing` does nothing** — the option you want is `charSpacing`.
- **Lists:** put `bullet: true` on every item, never a literal `•` (you'll get doubled bullets). Add `breakLine: true` to every array item but the last. Separate bulleted paragraphs with `paraSpaceAfter`, not `lineSpacing` (which leaves gaping gaps).
- **Exactly one `new pptxgen()` per output file** — don't recycle an instance.
- **`rectRadius` applies only to `ROUNDED_RECTANGLE`**, not `RECTANGLE`.
- **No gradient fills** — drop in a gradient image as the background instead.
- **Text boxes carry built-in inner padding** — set `margin: 0` any time text has to line up with a shape, rule, or icon sharing its x.
- **Speaker notes belong in `slide.addNotes("...")`** (plain text, one call per slide) — never in an on-slide text box.
- **Keep charts native.** Reach for `addChart()` for anything PowerPoint can plot (pass an array of `{type, data, options}` for combos). For native features the library doesn't surface (trendlines, error bars), compute the extra series yourself or post-process the emitted OOXML — never substitute a rendered picture. Only chart kinds PowerPoint has no native form for (Sankey, network, chord) should go in as images.
- **Charts render bare by default** — no title, no data labels, a stale palette. Turn on `showTitle` + `title`, `showValue: true` + `dataLabelPosition`, `chartColors: [...]` from your palette, and calm the frame (`catAxisLabelColor`/`valAxisLabelColor`, `valGridLine: { color, size }`, `catGridLine: { style: "none" }`, and `showLegend: false` for a lone series).
- **On a stacked bar or column chart, `dataLabelPosition` has to be `ctr`, `inEnd`, or `inBase`.** `outEnd` **corrupts the file**.
- **A combo series that uses `secondaryValAxis`/`secondaryCatAxis` needs both `valAxes` and `catAxes` in the chart options, two entries apiece.** Leave them out and pptxgenjs emits axis *ids* it never declares, so PowerPoint **throws the chart away** and flags the file as corrupt. Supplying `valAxes` alone won't cut it.
- **Once `writeFile()` returns, run `python scripts/oxml/package_audit.py deck.pptx`.** It catches the two chart faults above plus the slide-XML defects PowerPoint rejects, and names the fix for each. Repair them in your generator — don't hand-edit the packed XML.
- **Never shuffle the children of `<p:presentation>`.** pptxgenjs writes `<p:notesMasterIdLst>` immediately after `<p:sldIdLst>` and aims both masters at a single theme part. PowerPoint is fine with that — move the element and the very same deck stops opening.
- **Icons:** render `react-icons` to SVG (`ReactDOMServer.renderToStaticMarkup`), rasterize with `sharp` at ≥256px, and add via `addImage({ data: "image/png;base64," + buf.toString("base64") })` — the `image/png;base64,` prefix is mandatory (`react-icons`, `react`, `react-dom`, and `sharp` are preinstalled — only `npm install react-icons react react-dom sharp` if a require fails).

## Editing existing decks and templates

Choose layouts first: `python scripts/contact_sheet.py template.pptx template-thumbs` renders a labeled grid of every slide and prints the file(s) it wrote — `template-thumbs.jpg`, or `template-thumbs-N.jpg` once a deck runs past 12 slides. **Always supply that second argument, named for the deck.** It falls back to `thumbnails`, so two decks thumbnailed in the same folder quietly overwrite each other's grids — and the first deck's are just gone (this is for layout scouting only; visual QA needs the full-resolution renders from [Converting to Images](#converting-to-images), and it takes `.pptx` only, so copy a `.potx` to a `.pptx` name first). Pair it with `markitdown` to map each content section onto a template slide, and mix your layouts up — don't drop every section onto the same title-and-bullets slide.

```bash
python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall('unpacked')" deck.pptx
python scripts/deck_clone.py unpacked/ slide2.xml --after slide2.xml   # duplicate a slide (or slideLayoutN.xml); prints the new slide's path
# reorder / delete slides = edit <p:sldIdLst> in ppt/presentation.xml
python scripts/deck_prune.py unpacked/                                 # after deletions: removes orphaned slides, media, rels
# edit slide content in ppt/slides/slideN.xml
(cd unpacked && { [ -e ../out.pptx ] && mv ../out.pptx "$(mktemp -d)/out.pptx"; }; zip -Xr ../out.pptx .)   # move any stale out.pptx to a temp dir (not rm), then zip from INSIDE the dir
python scripts/oxml/package_audit.py out.pptx --original deck.pptx
```

- **Finish all structural work — add, delete, reorder — before you touch any slide's content.** `deck_clone.py` copies a slide file verbatim, so duplicating after an edit clones the edited version; and `deck_prune.py` removes any slide missing from `<p:sldIdLst>`, including one you just authored.
- **Never duplicate a slide file by hand** — `deck_clone.py` performs every registration a new slide requires and reports what it produced (`Created ppt/slides/slide17.xml from slide2.xml`). It also runs straight on a file: `deck_clone.py deck.pptx slide2.xml -o out.pptx` — **pass `-o`, or it overwrites the input deck in place.** A cloned slide still *references* its source's chart/SmartArt/embedded-object parts instead of copying them, so editing one slide's chart changes the other's.
- **If you go with `python-pptx`**, three things it can't do: duplicate a slide (its sole entry point is `add_slide(layout)`), keep formatting through `text_frame.text = "..."` (that flattens the paragraph into one unstyled run — assign `run.text` instead), or read the SVG/EMF that most template art uses (`add_picture` raises `UnidentifiedImageError`).
- Legacy `.ppt` has to be converted first: `python scripts/oxml/lo_bridge.py --headless --convert-to pptx file.ppt`. `.potx` templates unpack and repack the same way — keep the `.potx` extension on the output.
- To reuse a template's icon or image, duplicate a slide or layout that already holds it.

When populating a template:

- If you script an XML transform, parse with `defusedxml.minidom` — round-tripping OOXML through `xml.etree.ElementTree` rewrites namespace prefixes and corrupts the deck.
- **Template slots ≠ your source items.** If the template shows 4 team members and you have 3, delete the 4th member's whole group (image + text boxes), not just its text — then hunt for orphaned visuals during QA.
- One `<a:p>` per list item — never merge items into a single paragraph. Copy the sibling `<a:pPr>` to keep the spacing, and put `b="1"` on the `<a:rPr>` of titles, section headers, and inline labels (`Status:`, `Owner:`).
- Let bullets inherit from the layout; add `<a:buChar>`, `<a:buAutoNum>` (numbered), or `<a:buNone>` only to override — never a literal `•` in the text.
- Text with a leading or trailing space needs `xml:space="preserve"` on its `<a:t>`.

## Design Ideas

**Don't ship boring slides.** Plain bullets on white won't move anyone. Pull ideas from the list below for every slide.

### Before Starting

- **Choose a bold, topic-driven color palette**: it should feel built for THIS subject. If your colors would drop cleanly into a totally different deck, they aren't specific enough.
- **Dominance, not equality**: let one color carry 60-70% of the visual weight, back it with 1-2 supporting tones, and keep one sharp accent. Never split the weight evenly.
- **Play dark against light**: dark backgrounds for title and closing slides, light for the content in between (a "sandwich") — or go dark throughout for a premium feel.
- **Commit to one visual motif**: choose a single distinctive element and repeat it — rounded photo frames, icons inside colored circles. Carry it through every slide. **Don't make a color bar or accent stripe your motif** (see the Avoid list).

### Color Palettes

Match the colors to your topic — don't reach for generic blue. Treat these as starting points:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### For Each Slide

**Give every slide a visual element** — an image, chart, icon, or shape. Text-only slides vanish from memory.

**Layout options:**
- Two-column (text on the left, illustration on the right)
- Icon + text rows (icon in a colored circle, bold header, description beneath)
- 2x2 or 2x3 grid (image on one side, a grid of content blocks on the other)
- Half-bleed image (filling the full left or right side) with a content overlay

**Data display:**
- Big stat callouts (60-72pt numbers with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles beside section headers
- Italic accent text for standout stats or taglines

### Typography

**The font names you write into the .pptx are rendered by the user's PowerPoint, not by this environment.** Your visual QA renders through LibreOffice, which substitutes fonts it lacks — and for some fonts the stand-in has different metrics, so your QA preview can show overflow (or fit) the real deck won't. To keep QA trustworthy:

- **Safe fonts** (true-to-width in QA *and* bundled with Office): **Arial, Calibri, Cambria, Times New Roman, Courier New, Bookman Old Style, Century Schoolbook**. Use them for body copy and anywhere fit matters.
- **Headers with character at zero QA risk**: pair a safe-list serif header (Cambria, Bookman Old Style, Century Schoolbook) with a safe-list sans body (Calibri or Arial). You get contrast without losing reliable overflow checks.
- **If the user asks for a font off the safe list** (say Georgia or Trebuchet MS): use it where they asked, but give those containers ~10% extra slack and don't trust QA text-fit on them — the preview of that font is only approximate. Absent a request, prefer safe-list fonts for body text.
- **QA-unreliable fonts** (the substitute has different metrics — overflow checks may lie): Georgia, Trebuchet MS, Impact, Arial Black, Garamond, Consolas, Palatino Linotype. Calibri Light substitution varies by environment; treat it as QA-unreliable. Fine for titles/accents with slack; don't trust QA text-fit on them.
- **Never default to Aptos** — Office's post-2023 default has no metric-compatible substitute here *and* is absent from older Office installs, so it's unreliable on both ends.

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- Keep margins of at least 0.5"
- Leave 0.3-0.5" between content blocks
- Give it room to breathe — don't cram every inch

### Avoid (Common Mistakes)

- **Don't reuse one layout** — rotate through columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; reserve centering for titles
- **Don't skimp on size contrast** — titles need 36pt+ to separate from 14-16pt body
- **Don't fall back on blue** — pick colors tied to the specific topic
- **Don't mix spacing at random** — settle on 0.3" or 0.5" gaps and hold to it
- **Don't polish one slide and leave the rest bare** — commit across the deck or keep it simple everywhere
- **Don't build text-only slides** — add images, icons, charts, or shapes; skip the plain title + bullets
- **Don't forget text-box padding** — when aligning rules or shapes to text edges, set `margin: 0` on the box or offset the shape to cover the padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light-on-light or dark-on-dark
- **NEVER run accent lines under titles** — a giveaway of AI-generated slides; use whitespace or a background color instead
- **NEVER add decorative color bars or accent stripes** — this covers header/footer bars spanning the slide, vertical sidebar stripes along an edge, thin accent stripes on a card or block, and "single-side borders" on rectangles. They read as AI filler. To set a card apart, use a subtle background tint, a drop shadow, or an icon — not an edge stripe.
- **Don't default to cream/beige backgrounds** — with none specified, use white (`FFFFFF`) or the user's brand palette; steer clear of warm-neutral defaults like `F5F5DC`, `FAF0E6`, `FAEBD7`, `FFF8E1`
- **Don't ship text that overruns its shape** — if it doesn't fit, shrink the font, split across slides, or grow the container; never leave content clipped or spilling past its bounds

## QA (Required)

Your first render almost always has a few genuine issues — overlaps, overflow, misalignment. Track those down, fix them, re-render only the slides you changed, and stop.

### Content QA

```bash
markitdown output.pptx
```

Scan for missing content, typos, and wrong order.

**With templates, hunt for leftover placeholder text:**

```bash
markitdown output.pptx | grep -iE "\bx{3,}\b|lorem|ipsum|\bTODO|\[insert|this.*(page|slide).*layout"
```

If grep returns anything, fix it before you call the job done.

### File QA (required)

P0 issues (overflow, file corruption, missing user content, invented numbers, typos, orphan CJK breaks) block delivery. Fix and rerun. P1 (weak hierarchy, repeated layouts, generic icons) should be fixed unless explicitly out of scope. P2 (minor alignment, spacing drift) is polish.

Never claim the deck is done while a P0 remains.

## Step 5 — Deliver

Call the `qwenwork_file_present_files` tool with the generated `.pptx` file path. This automatically copies the file to the outputs folder and makes it visible in the artifacts panel. Then write a one-paragraph QA note listing which checks ran and any non-blocking caveats (e.g., "visual spot-check skipped for a 6-slide internal deck"). Do not write a long postamble.

## Design quick reference

One dominant color (60–70% weight), one or two support tones, one sharp accent. Commit to a motif: side accent bar, numbered chip, framed image, or recurring data card. Keep heading font and body font distinct. Default safe pairs:

- Latin: Calibri / Calibri Light, Arial / Arial Narrow, Georgia / Calibri.
- CJK: Microsoft YaHei / Microsoft YaHei Light, Source Han Sans Bold / Source Han Sans Regular, PingFang SC Semibold / PingFang SC Regular.

Avoid AI-slop patterns: thin accent lines under titles, fully centered body text, identical 2×2 card grids on every slide, pure-color circular pseudo-icons, generic gradient blobs, orphan CJK characters at line ends, dense bullet slides without any visual structure.

## python-pptx essentials

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.5), Inches(12.1), Inches(1.1))
tf = tb.text_frame
tf.word_wrap = True
tf.auto_size = MSO_AUTO_SIZE.NONE
p = tf.paragraphs[0]
p.alignment = PP_ALIGN.LEFT
r = p.add_run()
r.text = "Slide title"
r.font.name = "Calibri"
r.font.size = Pt(36)
r.font.bold = True
r.font.color.rgb = RGBColor(0x1E, 0x27, 0x61)

save_pptx(prs, "outputs/Your-Topic-Name.pptx")  # 根据主题命名，必须存到 outputs/ 下
```

**Always save with `save_pptx()`, never `prs.save()` directly.** python-pptx's built-in
template ships a blank `docProps/thumbnail.jpeg`; a bare `prs.save()` keeps it, so the
product preview card renders a white image instead of a real preview. Define and use this
wrapper — it strips that placeholder thumbnail and its `_rels/.rels` reference:

```python
def save_pptx(prs, path):
    """Save a .pptx and strip the blank placeholder thumbnail that python-pptx
    inherits from its built-in template. Use this instead of prs.save() —
    otherwise the product preview card shows a white image."""
    import os, re, zipfile, shutil
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    prs.save(path)
    tmp = path + ".tmp"
    with zipfile.ZipFile(path, "r") as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            name = info.filename
            # 1) drop the blank thumbnail entry (match docProps/thumbnail.* only;
            #    do NOT also require 'slide1' — that never matches and leaves the white image)
            if name.lower().startswith("docprops/thumbnail."):
                continue
            data = zin.read(name)
            # 2) remove the thumbnail relationship from the package .rels
            if name == "_rels/.rels":
                data = re.sub(
                    rb'<Relationship[^>]*Type="[^"]*/thumbnail"[^>]*/>', b"", data
                )
            zout.writestr(info, data)
    shutil.move(tmp, path)
```

```bash
python scripts/oxml/package_audit.py output.pptx                      # built from scratch
python scripts/oxml/package_audit.py output.pptx --original src.pptx  # built from a template
```

**If the deck came from a template, always pass `--original`.** A template can itself
carry parts the XSD rejects, so a bare run may report failures you never caused — and
a real regression can hide among them. `--original` baselines
the schema and slide checks against the template, suppressing errors it already had.
The structural checks — relationships, content types, charts — ignore `--original` and
report template-inherited problems either way, so read those on their own merits.

pptxgenjs emits chart XML PowerPoint refuses to open while every other tool
accepts it: python-pptx opens those decks, LibreOffice renders them, the XSD
passes them. Every failure names its fix. Fix it in the generator and rebuild.

### Visual QA

Convert the slides to images (see [Converting to Images](#converting-to-images)) and study every one. After staring at the generating code you tend to see what you meant rather than what rendered, so look at the images fresh (a subagent works well if you have one). User-visible defects to hunt for:

- **Text overflow or text clipped at a box or slide edge — check this first.** It's the most common defect and always user-visible. (For a font the previewer renders unreliably per Typography, its preview is approximate: trust the ~10% slack you left, not the apparent fit.)
- Overlapping elements (text through shapes, lines through words, stacked items)
- Source citations or footers colliding with the content above them
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (a big empty patch here, cramped over there)
- Too little margin from the slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray on a cream background)
- Template decoration knocked out of place after text replacement — e.g., a title underline sized for one line while the replaced title wrapped to two
- Low-contrast icons (e.g., dark icons on a dark background with no contrasting circle)
- Text boxes so narrow the text wraps excessively
- Leftover placeholder content

Call `qwenwork_file_present_files` with the final `.pptx` path, then write a one-paragraph QA note. Never deliver a deck with P0 issues. State explicitly which inline QA checks ran and which were skipped.
## Converting to Images

Turn a presentation into per-slide images for visual inspection:

```bash
python scripts/oxml/lo_bridge.py --headless --convert-to pdf output.pptx
mv slide-*.jpg "$(mktemp -d)/" 2>/dev/null || true   # move any stale renders to a temp dir (not rm); harmless if none exist
pdftoppm -jpeg -r 150 output.pdf slide
ls -1 "$PWD"/slide-*.jpg
```

**Hand the absolute paths printed above straight to the view tool.** The `mv` step moves stale images from earlier runs into a temp dir (not `rm`, so it never trips the shell delete gate). `pdftoppm` zero-pads by page count: `slide-1.jpg` for decks under 10 pages, `slide-01.jpg` for 10-99, `slide-001.jpg` for 100+.

**After any fix, rerun all four commands above** — the PDF has to be rebuilt from the edited `.pptx` before `pdftoppm` can reflect your changes.

## Dependencies

`pptxgenjs` (npm, preinstalled — install only if `require('pptxgenjs')` fails) · `markitdown[pptx]`, `Pillow`, `defusedxml`, `lxml` (pip — text dump, contact sheet, prune, audit) · LibreOffice (`soffice`, auto-configured for sandboxed environments via `scripts/oxml/lo_bridge.py`) · `pdftoppm` (Poppler)
