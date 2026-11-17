# Clinical Translation & Outlet Mapping

This reference supports Phase 8: connecting a validated ESC/aging mechanism to a
clinical or translational angle so the research loop closes with an application
outlet. Use it after a mechanism survives Phase 7 deep-dive.

## 1. The Two Translational Arcs of the Unified Theory

| Arc | Mechanism anchor | Outlet types |
|-----|------------------|--------------|
| **Controlled ↔ uncontrolled immortality** | ESC self-renewal programs co-opted by tumors (OCT4/SOX2/NANOG, telomerase, epigenetic plasticity) | Oncogenic dependency / target, reprogramming-based cell therapy safety, biomarker of dedifferentiation |
| **Cell-death trajectory (aging)** | Senescence, telomere attrition, epigenetic age acceleration, SASP, mitochondrial decline | Geroprotector target, epigenetic-age biomarker, senescence-clearing (senolytic) stratification, aging-intervention endpoint |

## 2. Public Clinical Omics for Validation

When validating a signature's direction or prognostic value, prefer these
Python-accessible, citation-stable resources (record access dates):

- **TCGA** — tumor transcriptome / methylation / miRNA across cancer types; test
  whether the nominated ESC-like program correlates with grade / survival.
- **GTEx** — normal-tissue expression; baseline for "is this program tissue-specific?"
- **Aging cohorts** — e.g. longitudinal DNAm studies for epigenetic-age acceleration;
  test whether the mechanism reverses age acceleration.
- **GEO clinical series** — search by disease + omics; use as independent cohort.

Retrieve via the same `scripts/download_omics.py` path or via the
`GEOquery`-equivalent Python (`geopandas` not needed; use `urllib` + parsing, or the
GEO REST API). Cite each cohort's generating publication (PMID).

## 3. Outlet Typing (pick the sharpest)

For the main-line mechanism, state exactly which outlet it supports:

- **Biomarker** — measurable (expression / methylation / miRNA) with diagnostic or
  prognostic value; report AUC / HR with confidence interval.
- **Therapeutic target** — a node whose perturbation reverses the phenotype; cite
  preclinical evidence PMID.
- **Companion diagnostic** — predicts response to an existing intervention.
- **Geroprotector endpoint** — a metric (epigenetic age, SASP, function) that an
  intervention should move; frame as a trial endpoint.

## 4. Closing the Loop — Minimum Evidence Checklist

Before claiming a translational outlet, confirm:

- [ ] Mechanism direction replicates in ≥1 independent public cohort.
- [ ] Outlet type is explicitly named (not "could be useful").
- [ ] At least one PMID supports the biological plausibility of the outlet.
- [ ] Required clinical validation study is specified (what cohort, what endpoint).
- [ ] The link back to the unified axis is stated (immortality control vs cell-death
      path).

## 5. Narrative Template (for Phase 8)

> "The [main-line regulator] drives a [ESC-like / senescence] program by
> [epigenetic / transcriptional / post-transcriptional] mechanism. This positions it
> as a [biomarker / target] for [disease/aging context], where loss of controlled
> immortality vs progression of the cell-death trajectory predicts [outcome]."
