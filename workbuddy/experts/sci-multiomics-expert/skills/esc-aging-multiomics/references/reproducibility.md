# Per-Figure Reproducibility Contract

This reference operationalizes Global Requirements 3 (per-figure reproducibility)
and 4 (real data only). It defines the directory layout, naming, and one-click
re-run rule that make every figure traceable and reproducible.

## 1. Directory Contract

Every project root follows this structure. Each figure is a **self-contained,
re-runnable unit** — its raw inputs, the matrices used for plotting, the code, and
the outputs all live together.

```
project_root/
  theme_config.md        # THEME declaration (name, axis, key regulators, omics)
  research_log.md        # hypotheses, decisions, PMIDs, dead ends, mechanism pick
  data_manifest.md       # accessions, sample counts, checksums, download dates
  FIGURE_PLAN.md         # Phase 1 outline; per-figure status resolved at the end
  figures/
    fig1_<short_name>/
      raw_data/          # verified original inputs (or checksumed pointers) used
      matrices/          # intermediate expression/quant matrices fed to plotting
                         # (csv / parquet / h5ad) — the audit trail for every panel
      code/              # numbered scripts (01_…, 02_…) that build this figure
      output/            # final panels (figX_A.pdf/.png …) + figX_composite.pdf
      fig1_log.md        # per-figure notes: decision, stats, PMIDs, status tag
    fig2_<short_name>/
      ...
  pipelines/             # optional shared pipeline scripts reused across figures
```

## 2. What Goes Where (the traceability chain)

For **every panel** in a figure, the lineage must be unambiguous:

```
raw_data/  --(code/01_…)-->  matrices/  --(code/02_…)-->  output/figX_A.pdf
```

- **`raw_data/`** — the exact files the figure depends on (aligned BAMs, count
  matrices, metadata). If the file is large or external, store a checksumed pointer
  (path + MD5 + accession) rather than copying, but the pointer must resolve.
- **`matrices/`** — the precise data frame / AnnData object handed to the plotting
  function. This is the proof that a figure came from real computed data; a figure
  with no corresponding `matrices/` entry is invalid.
- **`code/`** — every script that transforms `raw_data/` → `matrices/` → `output/`.
  Scripts are numbered in execution order and each logs: input paths, tool versions,
  random seed, and key parameters (at top of file or to `figX_log.md`).
- **`output/`** — final panels at CNS specs (see `cns_figure_standards.md`): each
  panel file plus a composite `figX_composite.pdf` sized to the target column width.

## 3. One-Click Re-Run Rule

- Each `figures/figX/code/` folder contains a `run.py` (or `run.sh`) that, with no
  arguments, regenerates `output/` from `raw_data/`.
- A figure is **not "done"** until `code/` run on `raw_data/` reproduces `output/`
  byte-for-byte in the numbers (visual may differ by rasterization, but the plotted
  values must match the `matrices/`).
- Pin every tool version (e.g. `scanpy==1.10.x`, `pyDESeq2==0.4.x`) in
  `data_manifest.md` / a `requirements.txt` at the project root.

## 4. Real-Data-Only Enforcement (Global Requirement 4)

- Never synthesize, mock, smooth-over, or invent values, distributions, correlations,
  or trends to complete a panel.
- If a panel cannot be produced from real data (missing layer, n too small, QC
  failed), mark it `BLOCKED` in `figX_log.md` and omit it — do not substitute
  placeholder numbers.
- The `matrices/` file is the single source of truth; every `output/` panel must
  load from it, never from hard-coded literals.

## 5. Naming & Status Conventions

- Figure folders: `fig1_<short_name>`, `fig2_<short_name>` (snake_case, short).
- Panels: `figX_A.pdf`, `figX_B.png`, … and `figX_composite.pdf`.
- `figX_log.md` records a **status tag** matching the Phase 1 plan:
  `locked` (finalized) or, for mechanism figures, `TBD-mechanism` until Phase 7
  resolves the target, then `locked`.
- `FIGURE_PLAN.md` is the living Phase 1 document: it starts with `TBD-mechanism`
  tags and is updated as statuses resolve.

## 6. Figure Plan Template (Phase 1 deliverable)

```markdown
# Figure Plan — <THEME>

## Fig 1 — <biological claim>
- Panels:
  - A: <analysis item> | omics: <layer> | test: <name + threshold> | viz: <type>
  - B: <analysis item> | omics: <layer> | test: <name + threshold> | viz: <type>
- Data needs: <accessions / matrices>
- Status: locked

## Fig 2 — <mechanism claim — TARGET TBD>
- Panels:
  - A: <upstream evidence> | omics: <layer> | test: … | viz: network
  - B: <convergent evidence> | omics: <layer> | test: … | viz: heatmap
- Data needs: <accessions / matrices>
- Status: TBD-mechanism   # resolved in Phase 7 from Phase 6 ranked table

## Fig 3 — <clinical/translational validation>
- Panels: …
- Status: locked
```

The agent presents this plan, waits for explicit user confirmation, and only then
runs any analysis code (Global Requirement 1). Mechanism figures stay `TBD-mechanism`
until Phase 6 preliminary mining produces the ranked candidate table that Phase 7
uses to pick the main line (Global Requirement 2).
