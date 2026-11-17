# CNS Methodology Extraction Protocol

This reference operationalizes Phase 3: how to read a high-impact (CNS-tier or
equivalent) paper and convert its analysis into a transferable "recipe" the agent can
apply to the user's ESC/aging multi-omics data. The goal is not summary — it is
method transfer.

## 1. Selection of Reference Papers

- Prefer papers that (a) use the same or adjacent omics layers, (b) study ESC,
  reprogramming, senescence, or aging, and (c) reach a mechanistic conclusion with
  multi-omics convergence.
- For each selected paper, record: PMID, journal, omics layers, sample contrast,
  and the headline mechanism. All claims here must carry a PMID.

## 2. The Extraction Template (fill per paper)

For every reference paper, distill these fields into a structured note:

1. **Biological question / contrast** — what was compared (e.g. ESC vs
   differentiated; young vs old; senescent vs proliferating).
2. **Omics layers used** — which of RNA-seq / ChIP-seq / MeDIP-WGBS / miRNA, and why.
3. **Integration method** — how layers were combined (e.g. "DE genes intersected
   with H3K27ac gain near TSS"; "miRNA–mRNA anti-correlation network").
4. **Statistical test & thresholds** — exact test, FDR cutoff, fold-change floor,
   sample size, validation cohort.
5. **Validation strategy** — orthogonal assays (qPCR, ChIP-qPCR, CRISPR, bulk/
   single-cell confirmation).
6. **Mechanism claim** — the falsifiable statement the paper ends with.
7. **Transferable recipe** — a 3–5 step procedure reusable on the user's data.

## 3. Mapping Recipe → User Data

After extraction, produce a **Method Adaptation Plan**:

- Which steps are directly reusable (same omics, similar contrast)?
- Where does the user's data diverge (missing layer, different species/build)?
- What is the minimal gap-closing action (download a public dataset, substitute a
  layer, relax a threshold)?
- WhatPMID-verified prior expectation should the user's result be compared against?

Write the plan before running pipelines (Phase 4). Do not silently substitute a
method without noting the divergence.

## 4. Convergence Pattern to Imitate

CNS multi-omics papers that land a mechanism typically follow this shape; the agent
should steer the user's project toward it:

1. A **differential phenotype** appears consistently across ≥2 omics layers.
2. A **regulator** (TF / epigenetic writer / miRNA) explains the concordance.
3. **Perturbation or orthogonal validation** confirms direction.
4. A **clinical/translational** link (biomarker, target, age association) closes it.

When the user's data only reaches step 1–2, the agent should explicitly state the
missing step-3/4 evidence needed for a strong paper.

## 5. Anti-Patterns to Avoid

- Do not borrow a method whose sample size or layer the user cannot match without
  noting it.
- Do not over-claim a mechanism the user's data only weakly supports; state
  confidence and required validation.
- Never present a literature value (effect size, frequency, survival HR) without a
  PMID.
- Do not invent a "CNS paper" or its method — only extract from papers the user
  provides or that are retrieved and verifiable.
