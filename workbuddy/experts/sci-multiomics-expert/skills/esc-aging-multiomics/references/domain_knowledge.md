# Domain Knowledge: ESC / Tumor / Aging Unified Theory

This reference supplies the biological and conceptual context the agent needs to
interpret multi-omics results for the unified framework: **ESC = controlled
immortality, tumor = uncontrolled immortality, aging = cell-death trajectory.**

Load this when the user's question touches mechanism interpretation, candidate
regulator prioritization, or narrative framing. Keep all specific numeric/mechanism
claims PMID-verifiable.

## 1. The Unified Axis

| State | Core property | Cell-fate outcome | Omics signature to expect |
|-------|---------------|-------------------|---------------------------|
| ESC (embryonic stem cell) | Controlled immortality — self-renewal + pluripotency under tight regulatory control | Symmetric/asymmetric division, differentiation on cue | Open chromatin at pluripotency loci (OCT4/SOX2/NANOG), bivalent promoters, high telomerase, hypomethylated repeat elements |
| Tumor | Uncontrolled immortality — checkpoint evasion, telomere maintenance, metabolic rewiring | Unchecked proliferation, invasion | Activated oncogenic TFs, loss of tumor suppressors, aberrant methylation, miRNA dysregulation, Warburg shift |
| Aging / senescence | Cell-death trajectory — accumulated damage, telomere attrition, mitochondrial dysfunction, SASP | Cell-cycle arrest, senescence, apoptosis | DNAm age acceleration, mitochondrial D-loop changes, senescence-associated secretory phenotype (SASP) upregulation, loss of rejuvenation capacity |

The agent's job is to find where a measured phenotype sits on this axis and which
regulator pushes it.

## 2. Key Pluripotency / Reprogramming Regulators (verify per project)

- **Core TF circuit:** OCT4 (POU5F1), SOX2, NANOG — mutual reinforcement; ChIP-seq
  anchors for ESC open chromatin. (PMID needed per specific claim.)
- **Epigenetic landscape:** H3K4me3 (active promoters), H3K27me3 (Polycomb
  repression), H3K9me3 / DNA methylation (heterochromatin/silencing), bivalent
  domains at lineage genes in ESC.
- **Telomere / immortality:** TERT, shelterin complex; ALT in tumors.
- **Reprogramming / Yamanaka:** OCT4, SOX2, KLF4, c-MYC (OSKM); partial
  reprogramming as a geroprotective angle.

## 3. Aging & Senescence Markers

- **Senescence:** p16^INK4a^ (CDKN2A), p21, SA-β-gal, γH2AX foci, Lamin B1 loss.
- **Epigenetic aging:** Horvath / Hannum / PhenoAge clocks; accelerated DNAm age as a
  cross-tissue aging phenotype; MeDIP/WGBS are the primary layers.
- **SASP:** IL-6, IL-8, MMPs — paracrine drivers linking senescence to tissue decline.
- **Mitochondria:** mtDNA deletions, OXPHOS decline, ROS.

## 4. Multi-Omics Layering for This Domain

| Layer | Question it answers | Typical mark / assay |
|-------|---------------------|----------------------|
| RNA-seq | What is differentially expressed? | PolyA / total RNA |
| ChIP-seq | Which TF/epigenetic writer binds where? | H3K27ac, H3K4me3, H3K27me3, H3K9me3, OCT4/SOX2/NANOG, p300 |
| MeDIP / WGBS | Where is methylation altered? | 5mC; DMR analysis |
| miRNA-seq | Post-transcriptional repression? | small RNA; target anti-correlation |

## 5. Interpretation Heuristics

- A gene **DE + nearby gain of H3K27ac / loss of H3K27me3 + hypomethylated** → likely
  activated by coordinated epigenetic opening (consistent with ESC-like programs).
- A tumor suppressor **up as miRNA target with reciprocal miRNA up** → post-
  transcriptional repression candidate.
- An aging signature **reversed by partial reprogramming** in the literature → strong
  translational narrative (controlled-immortality rejuvenation).

Always tie a nominated mechanism back to its position on the unified axis and to at
least one PMID.
