# Literature & High-Quality Omics Data Landscape (Phase 0 Protocol)

This reference operationalizes **Phase 0**: from a user-declared THEME, survey
current top-journal literature, extract the *usable public omics data* embedded in
those papers, integrate multiple papers, and refine the theme into a feasible,
innovative direction with a preliminary analysis plan. The defining move of this
phase is treating the **high-quality omics data shipped by the literature** as a
first-class output, not an afterthought.

## 1. Search Strategy

- **Target venues:** Nature, Science, Cell and sisters (Nat Genet, Nat Aging, Nat Cell
  Biol, Cancer Cell, Immunity, Cell Stem Cell, Mol Cell, Dev Cell, Nat Methods,
  Nat Biotechnol); plus domain leaders (Aging Cell, Cell Reports, Genome Biology,
  Genome Research, Nucleic Acids Res, eLife).
- **Tools:** WebSearch (current web) and PubMed (eutils) for retrieval; read the
  paper's Methods / Data Availability section directly. Record every query string.
- **Query template:** iterate
  `"<THEME>" [RNA-seq | ATAC-seq | ChIP-seq | DNA methylation | miRNA | single-cell |
  multi-omics] [mechanism | biomarker | aging | reprogramming | senescence]`.
- **Per hit, record:** PMID, journal, year, omics layers used, sample contrast, and
  the headline finding. Every literature claim must remain PMID-verifiable.

## 2. Parsing the Usable High-Quality Omics Data

- **Extract accessions** from Methods / Data Availability: GEO (`GSE` study / `GSM`
  sample), ENCODE (`ENCSR`), EGA (`EGAStudy`), ArrayExpress (`E-MTAB`), 10x datasets,
  single-cell atlases (Tabula Muris, HuBMAP, Tabula Sapiens), and processed matrices
  on Zenodo / figshare / the authors' site.
- **Characterize each dataset:** omics type, species & genome build, sample contrast
  (e.g. young vs old, ESC vs differentiated, senescent vs proliferating), replicate
  count `n`, modality (bulk / single-cell), and a **quality flag** (raw vs processed,
  public vs restricted, whether QC was reported).
- **Prioritize "high-quality":** raw or well-annotated processed data with documented
  QC. These form the actionable data pool for later phases.
- **Cross-link** each dataset to the paper's biological claim, so a later figure can
  cite both the result and its underlying accession.

## 3. Multi-Paper Integration

- Build a **consolidated table:**
  `accession | paper (PMID) | omics | contrast | n | quality | biological claim`.
- Identify three things: (a) **overlapping cohorts / samples** shared across papers;
  (b) **complementary omics layers** that together enable integration (e.g. one paper
  has ATAC, another has RNA-seq on the same model); (c) **gaps** where a needed layer
  is missing.
- This integrated map is what makes a refined direction *feasible*: the real,
  combinable data already exist — the agent is not proposing experiments that must be
  done from scratch.

## 4. Feasibility × Innovation Scoring

For each candidate refined direction, score two axes (0–5):

- **Feasibility:** data already exist / downloadable? methods transferable in the
  Python-only environment? adequate `n` / power? QC acceptable?
- **Innovation:** novel integration of layers? new contrast? addresses a
  literature-flagged gap? clinical / translational novelty?

Rank candidates by the product **Feasibility × Innovation** and present the top 2–4.

## 5. Output — Theme Refinement & Data Landscape Report

```markdown
# Phase 0 — Theme Refinement & Data Landscape
THEME (user): …

## Candidate refined directions (ranked by Feasibility × Innovation)
1. <direction> — feasibility X/5, innovation Y/5 — rationale (PMID …)
2. <direction> — …

## Consolidated high-quality omics datasets
| accession | PMID | omics | contrast | n | quality | claim |
|-----------|------|-------|----------|---|---------|-------|

## Gap analysis
- missing layer: … ; proposed public substitute: …

## Preliminary analysis-plan sketch (per top direction)
- Fig 1 candidate: …
- Fig 2 candidate (mechanism, TARGET TBD): …
```

Present this report and let the user pick (or approve) the refined direction **before**
proceeding to Phase 1. Never invent papers or accessions — only use retrieved,
verifiable sources.
