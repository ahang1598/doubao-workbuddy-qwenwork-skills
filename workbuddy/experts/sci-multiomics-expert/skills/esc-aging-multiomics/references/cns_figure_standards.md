# CNS Figure & Typesetting Standards

This reference operationalizes Global Requirement 5: every figure and the final
document must meet current **Nature / Cell / Science**-class standards. Values below
reflect the journals' current author guidelines (consult the target journal's
"Prepare Manuscript" / "Figure" page at submission time — these are the baselines).

## 1. Universal Rules (apply to all three journals)

- **Panel labels:** uppercase `A, B, C …` in a bold sans-serif font, placed at the
  upper-left of each panel. Keep them consistent in size across the whole figure.
- **Typography:** sans-serif (Arial or Helvetica) throughout the figure and the
  manuscript. Minimum legible size after reduction is **7 pt** (Nature); prefer
  7–8 pt for axis/label text, 8–10 pt for panel labels.
- **Resolution:** raster exports at **≥300 dpi** (line art / schematic may go to
  600 dpi). Prefer **vector** output (PDF / EPS) so text stays crisp at any zoom.
- **Color:** RGB color space. Use a **color-blind-safe** palette (e.g. seaborn
  `colorblind`, `viridis`, or blue/orange pairs). Avoid red–green-only encoding.
- **Chart-junk minimization:** remove unnecessary gridlines, 3-D effects, heavy
  borders, and redundant legends. Keep one consistent scale bar with a unit label
  on every microscopy / spatial panel.
- **Consistency:** same palette, font, and line weights across all figures in a
  paper; a single unified legend convention.
- **Legends:** figure legends live in the manuscript text (Nature/Cell style), not
  burned into the image. Keep short in-figure annotations minimal.
- **Line weights:** ≥0.5 pt visible after reduction; uniform across panels.

## 2. Journal-Specific Dimensions

| Journal | Single column | Double column | Full page (max) |
|---------|--------------|--------------|-----------------|
| Nature  | 89 mm (3.5 in) | 183 mm (7.2 in) | 247 mm (9.7 in) |
| Cell    | 90 mm           | 190 mm          | 180 mm (text area) |
| Science | 5.5 cm (~2.16 in) | 11.4 cm     | 12.1 cm × ~28 cm |

- Size every composite so its width matches the intended placement (single vs
  double column). Height should keep panels legible, not exceed the page.
- Maximum file size: Nature ~10 MB per figure file; keep vectors lean.

## 3. Per-Omics Visualization Conventions

- **Volcano / MA plots:** up = warm (red `#D62728`), down = cool (blue `#1F77B4`);
  threshold lines for FDR and |log2FC| explicitly drawn.
- **Heatmaps:** row/column clustering with a documented distance metric; annotated
  sample groups on the axis; diverging colormap (e.g. `RdBu_r`) centered on zero.
- **UMAP / t-SNE (single-cell):** consistent point size, legend for cell clusters,
  optional gene/trait overlay; state the random seed and perplexity/resolution.
- **Networks:** node size = degree, edge = interaction type, layout reproducible
  (fixed seed); legend for node/edge encoding.
- **GSEA / ridge plots:** the enrichment statistic and FDR labeled on each strip.
- **Bar / dot plots:** error bars with n and test statistic noted in the caption.

Document the chosen up/down color mapping once in `theme_config.md` and reuse it.

## 4. Python Implementation (matplotlib / scanpy / seaborn)

Set a journal-grade base once per project (e.g. in a shared `figure_rc.py`):

```python
import matplotlib
matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.format": "pdf",
    "axes.linewidth": 0.8,
})

# Panel label helper
def panel_label(ax, text="A", x=-0.02, y=1.02, fs=9):
    ax.text(x, y, text, transform=ax.transAxes, fontweight="bold",
            fontsize=fs, va="bottom", ha="left")
```

- **Export both vector + raster:** `fig.savefig("figX_A.pdf", bbox_inches="tight")`
  and `fig.savefig("figX_A.png", dpi=300, bbox_inches="tight")`.
- **Arial on headless/Linux:** register Arial if present, else DejaVu Sans is an
  acceptable sans-serif fallback; never silently switch to a serif font.
- **scanpy:** `sc.settings.set_figure_params(dpi=300, fontsize=8, facecolor="white")`
  and save with `save=".pdf"`.
- **seaborn palettes:** `sns.color_palette("colorblind")` or
  `sns.color_palette("viridis", as_cmap=True)` for diverging maps.
- **Composite figure:** assemble panels with `matplotlib.gridspec` (or `PIL`/`svgutils`
  for vector assembly) so the final `figX_composite.pdf` matches the target column
  width exactly.

## 5. Document Typesetting (final manuscript)

- Use the target journal's Word/LaTeX template; mirror its heading levels, caption
  style, and reference format.
- Tables: Publication-ready Markdown/Word with caption, footnotes for statistics,
  and a clear header hierarchy; avoid vertical rules (Nature/Cell style).
- Every numeric literature claim carries a PMID in the references table.
- Offer export to `.docx` (tencent-docx) and an academic `.pptx` template; both must
  inherit the same palette, font, and panel-label convention as the figures.

## 6. Sub-Figure Composition Logic (CNS narrative arc)

Global Requirement 8 requires every main figure to read like a Nature/Cell/Science
panel set. Use the following composition spine and layout rules when drafting or
reviewing a Figure Plan:

- **Narrative arc (panel order):** (a) DEFINE — the input assets, contrast, or study
  design that frames the figure; (b) CORE — the primary descriptive / differential
  evidence that answers the claim; (c) MECHANISM — resolution of how/why (a network,
  motif, occupancy, or trajectory view); (d) VALIDATE — an orthogonal dataset,
  independent cohort, or perturbation; (e) INTEGRATE — a summary linking sub-findings
  or bridging to the next figure.
- **Sizing:** the panel carrying the KEY result is the largest; validations and
  meta/QC panels are smaller and placed to the right or bottom. Never give a control
  the same footprint as the headline result.
- **Grid:** assemble with `matplotlib.gridspec` (or multi-panel scanpy) so panels
  align on a baseline, share scales where meaningful, and keep consistent gutters.
- **One idea per panel:** a panel tests exactly one sub-hypothesis or shows one
  control. If two ideas compete for one panel, split or drop one.
- **Controls sit with their assay:** batch/mixing diagnostics, QC, and negative
  controls belong next to the assay they qualify, not in a separate decorative panel
  unless essential to the claim.
- **Supplementary discipline:** anything that only proves the analysis ran — full gene
  lists, code/environment manifests, extended QC — belongs in Supplementary, never as
  a main filler panel.
