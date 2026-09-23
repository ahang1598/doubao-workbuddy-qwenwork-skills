# Refinement Pass Protocol

Run a focused refinement for a defect observed in actual image content or a
specific user-requested correction. Viewing is optional; without it, do not
claim a visual audit or invent defects.

## When to run

When an existing viewer is available, audit the completed result against the
selected mode's quality gates. Otherwise deliver it with visual QA unverified.
A specific user correction may be applied without viewing; ask what to change
when the correction is vague.

## Step 1 — Audit

Use the host's existing image-viewing capability, if available, as described in
`SKILL.md`. Only assess gates supported by visible image content. Leave the
audit unverified when pixels are unavailable; metadata is not a visual PASS.

## Step 2 — Identify the weakest area

Choose the user-specified correction or the single biggest observed issue.
Do not invent a weakness when viewing is unavailable. Common categories:

- **Lighting flat** — no clear direction, shadows too soft, no rim or separation
- **Plastic surface** — texture looks rendered not photographed
- **Warped text** — label letters mangled or AI-fictional
- **Anatomy off** — fingers, eyes, ears, hairline issues on people
- **Composition imbalance** — subject off-anchor, weak focal hierarchy
- **Palette drift** — colors don't match known brand context
- **Stock feel** — composition feels generic / over-staged
- **AI sheen** — that telltale rendered-looking smoothness
- **Aesthetic half-applied** (restyle only) — source style still bleeding through
- **Flat color band** — model rendered an empty solid-color or dull gradient strip (often happens when user requested text-overlay space and the model interpreted it too literally)

Pick ONE — the highest-impact issue.

## Step 3 — Run refinement generation

Submit a new generation referencing the latest completed job for the same index, with a focused fix prompt. Structure:

```
Refine the previous image. Keep composition, subject, framing, and overall scene IDENTICAL.
Only change: {{specific photographic instruction targeting the weakest area}}.
{{Mode-specific preservation directive}}.
```

### Fix-prompt language by issue type

**Lighting flat:**
> Add directional key light from camera-left at 45°, 4500K, with stronger rim separation on the opposite side. Deepen contact shadow at the base. Increase tonal range between highlight and shadow.

**Plastic surface:**
> Refine surface to show realistic micro-texture. Add tactile detail — visible weave / brushstroke / pore / grain depending on material. Remove rendered-looking sheen.

**Warped text:**
> Sharpen the product label text to fully legible commercial-print quality. Letters must be crisp and intact, not warped or merged.

**Anatomy off:**
> Correct the {{specific body part — fingers / hands / face / eye placement}}. Anatomically correct human proportions, natural realistic detail. Preserve facial likeness.

**Composition imbalance:**
> Reposition subject toward {{specific anchor — left third / right third}}. Strengthen focal hierarchy, focal anchor moved off dead-center.

**Palette drift:**
> Shift palette toward {{specific known brand colors}}. Reduce {{drifting color}} dominance. Bring {{brand accent}} forward.

**Stock feel:**
> Move away from generic staging. Add lived-in detail, intentional asymmetry, and one specific narrative cue {{name a cue}}. Photographic, not staged-stock aesthetic.

**AI sheen:**
> Remove rendered-looking sheen. Add film-grain photographic feel. Realistic skin texture with natural micro-imperfection. Hyper-realistic, not hyper-smooth.

**Aesthetic half-applied (restyle):**
> Source unchanged. Push aesthetic harder toward {{preset specifics — palette, surface, light, mood}}. Stronger {{specific element}} commitment. Source's previous aesthetic completely gone.

**Flat color band:**
> Replace the flat solid-color {{top / bottom / left / right}} area with natural scene continuation — extend the actual environment (sky, blurred background, surface texture, atmospheric gradient) into that area. The frame must read as one cohesive scene, no artificial empty rectangles.

## Step 4 — Submit refinement

Use the runtime orchestration in `SKILL.md`. Wait for the first-pass result,
then attach the latest completed result as the single `image` reference for the
same stable index. Preserve the first pass's aspect ratio, use `count:1`, and
end the focused fix prompt with `resolution: 2k`.

## Step 5 — Re-audit

If viewing is available, run the quality gates checklist on the refined output.
Otherwise deliver it with the visual result unverified. For an observed issue:

- **Major issue remains:** run a second refinement (max 2 refinements total)
- **All gates pass:** deliver
- **Different mode entirely needed:** explain the mismatch and ask before starting a new scope

## Refinement budget

- 1 first-pass generation
- Up to 2 refinements
- Total: max 3 generations per final output

All submissions, including failures and retries, count toward this three-generation limit. If the budget is exhausted, show the best completed version and disclose the remaining issue; never reset the counter with a new prompt.

## When NOT to run a refinement

- No pixels and no specific user correction → deliver with visual QA unverified
- First pass passes ALL inspected quality gates → deliver
- The output's "weakness" is subjective taste, not a quality gate failure → deliver and ask user
- The refinement would change subject or composition (not just polish them) → that's a fresh generation, not a refinement

## Carousel and ad-pack refinement

When viewing multi-image deliverables, audit the SET first, then individual slides:

1. Audit set-level coherence (palette consistency, lighting consistency, surface consistency across slides)
2. If a single slide breaks the set, refine ONLY that slide — don't regenerate the whole pack
3. Use the visual system from the original outline as the preservation directive

## Quality gate failure log

When delivering, briefly name the observed defect or requested correction.
Only say a defect was fixed if the result was actually inspected; otherwise
state that the correction was submitted but its visual result is unverified.

Example: "First pass had flat lighting on the left side; refined with stronger rim separation."
