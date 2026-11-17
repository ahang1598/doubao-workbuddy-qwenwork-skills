# CNS Recipe Book — Extracted Analysis Recipes

Real, PMID-verified recipes distilled from high-impact papers for use in Phase 3
(method adaptation). Each entry follows the extraction template in
`cns_methodology.md`: **contrast → omics layers → integration method → statistics →
validation → mechanism → transferable recipe**. Every numeric claim traces to its
PMID. Before applying a recipe to the user's data, run the Method Adaptation Plan
(see `cns_methodology.md`) and note any divergence.

> Theme note: these recipes are written for the default ESC/aging theme. To reuse
> this skill for a different theme, swap the worked example in `SKILL.md`'s THEME
> block and replace the domain-specific recipes below — the workflow is theme-agnostic.

## Recipe 1 — Foundational reprogramming factors (ESC ↔ immortality)
- **Paper:** Takahashi & Yamanaka, *Cell* 2006. PMID **16904174**.
- **Contrast:** mouse embryonic/adult fibroblasts → induced pluripotent stem cells (iPSCs) via 4 factors.
- **Omics layers:** mostly functional/genetic screening (retroviral factor delivery); transcriptomic marker validation (ESC marker genes).
- **Integration method:** candidate-gene winnowing — start from 24 ES-cell candidate genes, remove one-at-a-time to identify the essential core.
- **Statistics / thresholds:** reporter-based selection (Fbx15 activation); pluripotency validated by teratoma formation (3 germ layers) and blastocyst contribution.
- **Validation:** teratoma in nude mice; chimera contribution; marker-gene expression.
- **Mechanism claim:** Oct4, Sox2, Klf4, c-Myc (OSKM) alone suffice to revert a somatic cell to a latent embryonic state — the molecular basis of *controlled immortality*.
- **Transferable recipe:** (1) Define the phenotype contrast. (2) Enumerate candidate regulators. (3) Systematic knock-out/add-back to find the minimal sufficient set. (4) Validate with an orthogonal functional assay.

## Recipe 2 — In vivo partial reprogramming reverses aging hallmarks
- **Paper:** Ocampo et al., *Cell* 2016. PMID **27984723**.
- **Contrast:** progeria (premature-aging) mouse model and old wild-type mice ± cyclic short-term OSKM expression.
- **Omics layers:** transcriptomics (bulk RNA-seq of aged vs rejuvenated tissues); epigenetic readouts (DNAm age, Lamin B1, γH2AX).
- **Integration method:** compare age-associated phenotypes before/after cyclic OSKM; track epigenetic age acceleration reversal.
- **Statistics / thresholds:** cyclic regime critical (2 days ON / 5 days OFF); excessive OSKM → weight loss/cancer, so dose titration is a safety gate.
- **Validation:** lifespan extension in progeria model; improved metabolic-disease recovery and muscle-injury regeneration in old wild-type mice.
- **Mechanism claim:** transient epigenetic remodeling (not full reprogramming) reverses aging hallmarks in vivo — epigenetic dysregulation is a *driver* of mammalian aging.
- **Transferable recipe:** (1) Pick a reversible (epigenetic) axis rather than genetic. (2) Use cyclic/partial perturbation to avoid oncogenic dedifferentiation. (3) Measure both cellular and physiological phenotypes. (4) Titrate dose as a hard safety gate.

## Recipe 3 — Epigenetic clock as an age phenotype
- **Paper:** Horvath, *Genome Biology* 2013. PMID **24138928**.
- **Contrast:** chronological age vs DNA methylation (DNAm) age across 51 healthy tissues/cell types; 20 cancer types vs normal.
- **Omics layers:** DNA methylation arrays (Illumina 450K/27K); integrated with TCGA cancer methylomes.
- **Integration method:** elastic-net-style penalized regression on 353 CpG sites → age predictor; compute age acceleration = DNAm age − chronological age.
- **Statistics / thresholds:** trained on ~8,000 samples / 82 datasets; correlation 0.97 (training); median absolute error 2.9 years (verified in source). All 20 cancer types show significant age acceleration (mean ~36 years).
- **Validation:** DNAm age ≈ 0 in ESC/iPSC; correlates with passage number; heritable age acceleration; generalizes to chimpanzee.
- **Mechanism claim:** DNAm age reflects a cumulative epigenetic maintenance system; accelerated DNAm age links immortality-control loss (cancer) and aging.
- **Transferable recipe:** (1) Build/apply a published clock on the user's beta values using the exact 353-CpG coefficient set (cite PMID). (2) Compute age acceleration per sample. (3) Test whether the nominated mechanism moves acceleration. (4) Report error bounds.

## Recipe 4 — Single-cell aging atlas (cell-type-resolved)
- **Paper:** Tabula Muris Senis (The Tabula Muris Consortium), *Nature* 2020. PMID **32669714**.
- **Contrast:** young vs old mice across the lifespan; 23 tissues/organs.
- **Omics layers:** single-cell RNA-seq (scRNA-seq) across many cell types; companion bulk RNA + plasma proteomics (Schaum et al., same consortium).
- **Integration method:** cell-type annotation → per-cell-type age signatures; cross-tissue comparison of hallmark manifestation (senescence, genomic instability, immune change).
- **Statistics / thresholds:** identify cell-specific age-related changes and shifts in cellular composition per organ; highlight cell types most responsive (e.g., adipose MSCs, HSCs, hepatocytes).
- **Validation:** cross-species (human/mouse) cell-type mapping; bulk+single-cell concordance for immune-cell accumulation in adipose.
- **Mechanism claim:** aging is cell-type-specific and asynchronous across organs; immune activation first detectable in middle-aged adipose.
- **Transferable recipe:** (1) Annotate cell types. (2) Compute per-cell-type differential expression by age. (3) Rank cell types by responsiveness. (4) Integrate with bulk to find systemic (plasma proteome) correlates.

## Recipe 5 — Single-cell ATAC-seq method (scATAC)
- **Paper:** Buenrostro et al., *Nature* 2015. PMID **26083756**; data GSE65360.
- **Contrast:** method paper — aggregate hundreds of single-cell ATAC profiles vs bulk; 8 cell types.
- **Omics layers:** scATAC-seq (Tn5 tagmentation on Fluidigm C1); later integrated with scRNA where available.
- **Integration method:** per-cell accessibility variance decomposed into trans-factor (TF) and cis-element associations; cis-variance recapitulates chromosome compartments de novo.
- **Statistics / thresholds:** hundreds of single cells; variant sites systematically linked to TF motifs; perturbation (cell-cycle / TF signaling) evokes stimulus-specific variability changes.
- **Validation:** aggregate scATAC ≈ bulk accessibility; targeted perturbations confirm causality of variability.
- **Mechanism claim:** regulatory (accessibility) variation is driven by specific TF combinations; links single-cell regulome variation to 3D genome organization.
- **Transferable recipe:** (1) Generate scATAC (10x or Fluidigm). (2) Call peaks per cell / aggregate. (3) Decompose accessibility variance → TF motif enrichment. (4) Perturb candidate TF to confirm.

## Recipe 6 — Single-cell multiome (ATAC + RNA in same cell)
- **Paper:** Cao et al. (sci-CAR), *Science* 2018. PMID **30166440**; data GSE117089.
- **Contrast:** 4,825 cells (dexamethasone time series) + 11,296 adult mouse kidney cells; jointly profiled.
- **Omics layers:** co-assay of chromatin accessibility (ATAC) and mRNA (RNA-seq) in the *same* cell via combinatorial indexing.
- **Integration method:** link cis-regulatory sites to target genes by **covariance** of accessibility and expression across many single cells; reconstruct ATAC profiles of RNA-defined cell types; compare pseudotemporal dynamics of the two layers.
- **Statistics / thresholds:** thousands of cells; covariance-based enhancer–gene linking (no separate eQTL needed).
- **Validation:** dexamethasone time-series shows coordinated accessibility/expression dynamics; kidney cell-type resolution.
- **Mechanism claim:** within-cell covariation is a powerful, assumption-light way to assign regulatory elements to genes without perturbation.
- **Transferable recipe:** (1) Obtain a same-cell multiome (10x Multiome or sci-CAR). (2) Joint-embed cells (RNA + ATAC). (3) Compute peak–gene covariance per cell cluster. (4) Prioritize regulators whose accessibility co-varies with target expression.

## How to use these in Phase 3
1. Choose the recipe(s) whose contrast/layers match the user's question.
2. Fill the Method Adaptation Plan: which steps are reusable, what diverges, the
   minimal gap-closing action.
3. Cite the PMID for any borrowed method or prior expectation.
4. Keep the recipe list extendable — add new papers as the user validates them.
