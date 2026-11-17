# Standard Multi-Omics Pipelines (Python-First)

Tool and workflow reference for Phases 2–4. **Environment contract: Python 3.13.12
only; no R.** Where the field-standard tool is R-only, a Python substitute is given
and must be stated when used. Prefer CLI tools invoked via the Bash tool; use Python
libraries for statistics and plotting.

## 0. Common Pre-Flight (all layers)

- Verify raw data integrity first (see `scripts/download_omics.py` / Phase 2).
- Record: genome build (e.g. GRCh38), annotation version (GENCODE/Ensembl), tool
  versions, and random seeds in `research_log.md`.
- QC gate policy: do not proceed to differential analysis on any sample below the
  layer-specific QC floor (see each section).

## 1. RNA-seq

Pipeline: QC → trim → align → quantify → count matrix → differential expression.

- **QC / trim:** `fastp` (CLI) for adapter/quality trimming and QC reports.
- **Align:** `STAR` (2-pass) or `HISAT2` (CLI). Index against GRCh38.
- **Quantify:** `featureCounts` (CLI, Subread) for gene counts; or `salmon` (CLI,
  quasi-alignment, faster, no genome index needed).
- **Differential expression — Python path:**
  - `pyDESeq2` (Python reimplementation of DESeq2's negative-binomial model) for
    count-based DE with size-factor normalization. **Substitute for DESeq2 (R).**
  - `edgePy` / `DESeq2`-equivalent not required; for non-count or small designs use
    `scipy.stats` (Mann–Whitney / limma-style via `limma` is R-only → use
    `statsmodels` instead).
- **Thresholds:** FDR < 0.05 (Benjamini–Hochberg) and |log2FC| ≥ 1 (adjust per
  project); report both.
- **QC floor:** mapping rate > 70%, duplicate rate reasonable, > 15M mapped reads
  (recommend > 30M for human).

## 2. ChIP-seq

Pipeline: QC → trim → align → peak call → annotate → differential binding (if ≥2
conditions).

- **Align:** `Bowtie2` (CLI) with up to 2 mismatches; PCR/dup mark with `picard`
  MarkDuplicates or `samtools markdup`.
- **Peak calling:** `MACS2` (CLI, callpeak) for narrow (TF/H3K4me3/H3K27ac) and
  broad (H3K27me3/H3K9me3) peaks. Set `--broad` for repressive marks.
- **Blacklist:** apply ENCODE blacklist (hg38) to remove artifact regions.
- **Annotation:** `HOMER` annotatePeaks or `chippeakanno` (R-only → use
  `pybedtools` + custom overlap with GENCODE for nearest-gene/feature assignment).
- **Differential binding:** `DiffBind` is R-only → use `csaw` conceptually via custom
  `scipy`/edge-case, or pairwise MACS2 + overlap + Fisher test in Python.
- **QC floor:** FRiP > 0.01 (narrow) / > 0.05 (broad), NSC > 1.05, high
  IP/input enrichment; IgG/input control required.

## 3. MeDIP / DNA Methylation

Pipeline: QC → align (Bismark for WGBS; standard for MeDIP) → call → DMR.

- **MeDIP-seq:** align with `Bowtie2`; call enriched regions with `MACS2`
  (treat as broad); compare groups for differential methylated regions (DMRs).
- **WGBS (optional, gold standard):** `Bismark` + `MethylKit`-style → Python
  substitute: parse Bismark cov.gz with `pandas`, call DMRs via sliding-window
  logistic/DSS-style in `statsmodels` (`DSS` is R-only).
- **Annotation & age clocks:** compute Horvath/PhenoAge features from CpG beta
  values; there is no pure-Python clock package — implement the published coefficient
  dot-product on CpG subsets, citing the clock PMID.
- **QC floor:** CpG coverage depth > 10× at clock CpGs; MeDIP enrichment vs input.

## 4. miRNA-seq (small RNA)

Pipeline: QC → adapter trim → align → quantify → DE → target integration.

- **Trim:** `cutadapt` (CLI) for 3′ adapters.
- **Align / quantify:** `bowtie1` against miRBase mature/precursor; or `mirdeep2`
  (Perl/Python suite) for novel miRNA discovery.
- **DE:** `DESeq2`-equivalent via `pyDESeq2` on count matrices; or `edgeR`-style via
  `statsmodels`.
- **Target integration:** use `TargetScan` / `miRDB` predictions; test
  miRNA–mRNA anti-correlation in the RNA-seq layer (Phase 5).

## 5. Integration & Visualization (Phase 4–5)

- **Consensus ranking:** intersect DE genes with ChIP target / DMR / miRNA-target
  sets using `pybedtools` / `pandas` set operations.
- **Networks:** `networkx` (Python) for regulator–target graphs; export to Cytoscape
  or plot with `matplotlib`/`seaborn`.
- **Visualization:** `matplotlib`, `seaborn`, `plotly` (interactive). For genomic
  tracks, `pyGenomeTracks` (CLI/Python). Heatmaps via `seaborn.clustermap`.
- **Pathway:** `gseapy` (Python implementation of GSEA/Enrichr) — substitute for
  clusterProfiler (R).

## 6. Single-Cell Layers (scRNA-seq / scATAC-seq / Multiome)

All Python-first. Single-cell is an extra-resolution layer that feeds Phases 3–4
(cell-type-resolved phenotypes, within-cell regulatory covariation). It complements
— not replaces — the bulk layers in sections 1–4.

### 6.1 scRNA-seq
- **Preprocess / QC:** `scanpy` (Python) — filter cells by counts/genes/MT%,
  normalize (log1p), HVG selection, scaling, PCA, neighbor graph, Leiden clustering,
  UMAP.
- **Batch / condition integration:** `scanpy` `ingest`, `bbknn` (Python), or
  `pyharmony` (Python port of Harmony).
- **DE within clusters:** `scanpy.tl.rank_genes_groups` (t-test / Wilcoxon /
  logistic). For cross-condition DE that respects count statistics, aggregate to
  **pseudobulk** and run `pyDESeq2` (substitute for DESeq2/R).
- **Trajectory:** `scanpy.tl.paga`; `scvelo` (RNA velocity, Python).
- **QC floor:** ≥ 500 genes/cell, < 20% mitochondrial reads, doublet removal with
  `scrublet` (Python) or `scanpy` doublet score.

### 6.2 scATAC-seq
- **Python path:** `snapATAC2` (Python, scalable) or `muon` (Python, multiome-friendly).
  **Substitute for ArchR, which is R-only.**
- **Workflow:** peak calling per cell/aggregate; TF motif enrichment via `MOODS` /
  `muon`; LSI + UMAP; annotate clusters using gene-activity scores.
- **Integration with scRNA:** `muon` jointly embeds both modalities and links peaks
  to genes by within-cell covariance (see Recipe 6 / sci-CAR in `references/recipes.md`).
- **QC floor:** per-cell TSS enrichment > 2, fragment-count threshold; FRiP on
  aggregate.

### 6.3 10x Multiome (same-cell ATAC + RNA)
- **Tool:** `muon` (Python) reads 10x Multiome output; `scvi-tools` (`scVI` / `scANVI`)
  for joint latent integration.
- **Regulator nomination:** compute peak–gene covariance per cluster, enrich TF
  motifs in variable peaks, cross-check against bulk ChIP/ATAC from Phases 2–4.

### 6.4 sc ↔ bulk integration
- Map single-cell clusters onto bulk DEGs/DMRs: a bulk DE gene whose cell-type
  specificity (scRNA) explains the bulk signal is a stronger candidate.
- Use `scanpy` → `pandas` to intersect sc marker genes with bulk significant sets.

### 6.5 Statistics for single-cell
- Cluster-level DE: Wilcoxon / t-test with Benjamini–Hochberg correction; for
  count-based, pseudobulk + `pyDESeq2`.
- Report effect size (logFC / fold) and adjusted p; avoid significance calls on
  clusters with fewer than ~10 cells.

## 7. Multiple Testing & Statistics (all layers)

- Default correction: Benjamini–Hochberg FDR.
- Report effect size (log2FC / methylation delta / peak fold-enrichment) alongside
  adjusted p.
- For small-n, prefer non-parametric tests (`scipy.stats.manwhitneyu`,
  `scipy.stats.kruskal`) and state the choice.
- Never report a "significant" call without both effect size and adjusted p.
