# Lessons

<!-- teachable-figures workspace · schema v1 · SAMPLE for an adult self-learner (illustrative, not real data). -->

Registry of every 2D/3D lesson created for this learner or class.

| id | title | concepts | renderer | audience | file | created | status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cone-sections | Halve the cone's height: is the slice half as big? | area-scales-with-square similar-shapes | turning-3d | self-learner | lessons/cone-sections.html | 2026-10-05 | used | Predicted ×2 first; independent practice 2/3 first try. v2 added area tiles (see notes). |
| entropy-questions | Can you average less than one question per answer? | surprise-log entropy-average source-coding | svg-2d | self-learner | lessons/entropy-questions.html | 2026-10-12 | used | Predicted "at least 1"; reached 0.90 with pairs; transfer (recompress) correct. |
| bayes-base-rate | You test positive: are you 90% likely to be sick? | conditional-probability base-rate bayes-odds | svg-2d | self-learner | lessons/bayes-base-rate.html | 2026-10-20 | used | Predicted ~90% (inverse); practice case 3 (odds) missed once, then correct. |

## Lesson notes

### cone-sections

- **Claim:** The slice radius scales linearly with height; its area scales with the square.
- **Misconception targeted:** linear-scaling
- **Builds on:** ratios (assumed secure)
- **Versions:** v1 2026-10-05 — initial; v2 2026-10-06 — added r×r area tiles after the explanation said "area doubles too" (evolve patch-1)
- **Evidence:** v1 explanation lacked squaring; on v2 the tile probe was correct and the explanation mentioned "k × k squares".

### bayes-base-rate

- **Claim:** P(sick | positive) depends on the base rate, not only on test accuracy.
- **Misconception targeted:** inverse-conditional
- **Builds on:** conditional-probability
- **Versions:** v1 2026-10-20
- **Evidence:** first estimate 90 (inverse); after counting the grid, estimated 10; odds-form practice needed one retry (multiplied the probability instead of the odds).
