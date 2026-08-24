# Native-chart authoring with pptxgenjs

Use this adapter when an existing generator already uses pptxgenjs, or when a
deck needs native PowerPoint chart combinations that are materially easier to
express with `addChart()`. Use the default `python-pptx` workflow in
[from_scratch.md](from_scratch.md) for theme-led decks and the bundled visual
components. Do not switch adapters merely because one dependency is already
installed.

If pptxgenjs is missing and this adapter is required, install the fixed
`pptxgenjs` dependency in the current task/workspace. Do not install a
caller-selected package.

## Authoring invariants

- Set `pres.layout` before adding slides. `LAYOUT_WIDE` is 13.333 × 7.5 in;
  the default `LAYOUT_16x9` canvas is only 10 × 5.625 in.
- Use six-digit hex colors without `#`. Eight-digit alpha colors and values
  such as `#FF0000` can corrupt the output. Use `transparency` for fills/images
  and `opacity` for shadows.
- Create fresh option and shadow objects for each call. pptxgenjs mutates
  option objects into EMU values.
- Keep shadow offset non-negative; use angle 270 for an upward shadow.
- Use `charSpacing`, not `letterSpacing`. Set `margin: 0` where text must align
  with adjacent geometry.
- Put `bullet: true` on each list item and never insert a literal bullet glyph.
  Separate paragraphs with `paraSpaceAfter`.
- Use exactly one `new pptxgen()` instance per output deck.
- `rectRadius` only affects `ROUNDED_RECTANGLE`; it does not round a rectangle.
- Put speaker notes in `slide.addNotes()` rather than on-slide text boxes.

## Native chart rules

- Keep PowerPoint-native chart kinds native. Use images only for graphs with no
  native PowerPoint form, such as Sankey, chord, or network diagrams.
- Configure chart title, values, palette, axes, grid lines, and legend
  deliberately; the defaults are not presentation-ready.
- On stacked bar/column charts, `dataLabelPosition` must be `ctr`, `inEnd`, or
  `inBase`. `outEnd` can create a file PowerPoint rejects.
- Combo series using secondary value/category axes require two entries in both
  `valAxes` and `catAxes`. Missing axis declarations can make PowerPoint drop
  the chart even when LibreOffice and python-pptx accept the file.
- For native features not surfaced by the library, compute an additional data
  series or post-process only the emitted chart OOXML. Do not rasterize the
  whole chart.

## Required finish

Run the same final gate as the python-pptx adapter:

```bash
python scripts/strip_thumbnail.py output.pptx
python scripts/validate_pptx.py output.pptx --pretty
python scripts/view_issues.py output.pptx
python scripts/oxml/package_audit.py output.pptx
```

Repair the generator and rebuild when the audit fails. Never hand-patch the
packed output as the final source of truth.
