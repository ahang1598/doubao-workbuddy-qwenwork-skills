# GPR Introduction Pattern Example

This example is distilled from a user-provided passage about ground penetrating radar (GPR). It is a structure sample for evidence-driven Introduction and Related Work writing; do not copy its subject matter into unrelated papers.

## Argument Chain

1. Establish the domain and application breadth.
   - The passage opens by defining GPR as a nondestructive detection method and immediately anchors it with classic sources and application examples.
   - Pattern: "Technology X is used in A/B/C applications; therefore, performance problem Y matters."

2. Explain why the technical subproblem matters.
   - The passage narrows from GPR applications to forward modeling and inversion.
   - It gives two reasons: interpreting complex data and supporting full waveform inversion.
   - Pattern: "Subproblem Y is not auxiliary; it is a prerequisite for downstream task Z."

3. Classify existing methods by technical family.
   - The passage separates ray tracing from wave-equation methods, then names MoM, FDTD, and FEM.
   - It does not list papers randomly; it builds a method taxonomy.
   - Pattern: "Existing methods fall into family A and family B. Family A lacks condition C, while family B dominates because it preserves property D."

4. Identify the computational bottleneck.
   - The passage explains that accurate 3D electromagnetic modeling remains expensive, especially when inversion requires many forward solves.
   - Pattern: "The accepted accurate method is useful but too costly under realistic iteration or deployment constraints."

5. Introduce machine learning as a response, then limit it.
   - The passage notes that ML can provide real-time approximations, but traditional networks fail to capture complex target-ground-antenna interactions.
   - Pattern: "New route M addresses cost, but current M variants still fail under condition C."

6. Land on the proposed contribution.
   - The passage ends by naming the proposed composite model, data source, dimensionality reduction, and modeling rationale.
   - Pattern: "This paper proposes method P because it directly targets the bottleneck identified in steps 3-5."

## Reusable Paragraph Blueprint

```markdown
P1 Domain context:
Claim: Technology/problem area matters in several real applications.
Evidence: classic definitions + representative applications.

P2 Technical necessity:
Claim: A specific computational or modeling subproblem controls downstream performance.
Evidence: method/inversion literature.

P3 Existing method taxonomy:
Claim: Mainstream methods split into families with different strengths.
Evidence: grouped citations.

P4 Bottleneck:
Claim: The strongest conventional method is accurate but too expensive or limited.
Evidence: complexity, runtime, or deployment constraints.

P5 Learning-based attempts:
Claim: Learning methods reduce cost but existing forms miss important interactions or generalization.
Evidence: recent ML applications and their limits.

P6 Proposed work:
Claim: The proposed method is designed around the bottleneck, not merely added as a new model name.
Evidence: method components tied to prior limitations.
```

## What This Prevents

- Background paragraphs with no citations.
- Related Work sections that summarize papers one by one without a gap.
- Proposed methods introduced before the reader understands the bottleneck.
- User editing requirements leaking into the manuscript body.
