# Output Templates

Use compact tables by default. If the user asks only for final copy, provide final copy first and then a short risk/validation note.

## Task Understanding

| Field | Identified | Missing / assumption | Impact |
|---|---|---|---|
| Platform |  |  |  |
| Site / language |  |  |  |
| Product / category |  |  |  |
| Core attributes |  |  |  |
| Keyword source |  |  |  |
| Requested fields |  |  |  |
| Risk items |  |  |  |

## Source / Verification Plan

| Need | Best source | Fields to extract | Access caveat |
|---|---|---|---|
| Keyword demand | Seller Center / Brand Analytics / search terms / third-party keyword tool | query, rank, impressions, clicks, purchases |  |
| Competitor language | PDP/search pages | title, bullets, reviews, images, A+ modules |  |
| Platform rules | Official help / Seller University | field rules, prohibited claims, image rules |  |
| Product facts | User files / official brand/manufacturer page | material, size, color, pack, compatibility, claims |  |

## Product Fact Extraction

| Field | Value | Source | Confidence | Needed for |
|---|---|---|---|---|
| Product name |  |  |  | Title |
| Core function |  |  |  | Title/Bullet |
| Material |  |  |  | Bullet/Attributes |
| Size / capacity |  |  |  | Title/Bullet |
| Color / pattern |  |  |  | Title/Variants |
| Pack quantity |  |  |  | Title/Bullet |
| Compatibility |  |  |  | Title/Bullet |
| Occasion / audience |  |  |  | Tags/A+ |
| Sensitive claim |  |  |  | Risk check |

## Claim Ledger

| Proposed claim | Source | Evidence scope | Status: verified/conditional/blocked | Final handling |
|---|---|---|---|---|
|  |  | Parent / child SKU / model-year / tested sample |  |  |

## Variant / Model Matrix

| Child SKU / model | Current selected? | Default verified? | Size / weight | Material / package | Test / certification scope | Compatibility / standard | Field level or unresolved gap |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Listing Draft Table

| Field | Draft | Rationale | Validation gap |
|---|---|---|---|
| Title |  |  |  |
| Bullet 1 |  |  |  |
| Bullet 2 |  |  |  |
| Bullet 3 |  |  |  |
| Bullet 4 |  |  |  |
| Bullet 5 |  |  |  |
| Description |  |  |  |
| Backend / tags |  |  |  |

## A+ / Image Brief

| Slot | Goal | Copy / visual direction | Product proof needed |
|---|---|---|---|
| Hero |  |  |  |
| Feature module |  |  |  |
| Scenario module |  |  |  |
| Comparison module |  |  |  |
| Brand / trust module |  |  |  |

## Localization And Risk Check

| Check | Result | Suggested action |
|---|---|---|
| Local buyer language |  |  |
| Units / sizes |  |  |
| Occasion / culture fit |  |  |
| Keyword stuffing |  |  |
| Brand / IP terms |  |  |
| Certification / safety / medical claims |  |  |
| Price / promotion / contact terms |  |  |
| Platform data gaps |  |  |

## Final Quality Gate

| Gate | Pass / blocked | Evidence or correction |
|---|---|---|
| Requested fields complete |  |  |
| Parent/child/model scope correct |  |  |
| Final claims are verified |  |  |
| Backend terms deduplicated and risk-checked |  |  |
| Exact limits / byte count checked when required |  |  |
| Copy, tables, files, and summary agree |  |  |
| Mixed-task handoffs stated |  |  |

## Final Response Skeleton

```markdown
**Task Understanding**
...

**Source Plan**
| Need | Source | Fields | Caveat |
|---|---|---|---|

**Keyword Map**
| Type | Keyword | Use | Confidence | Risk |
|---|---|---|---|---|

**Listing Draft**
| Field | Draft | Rationale | Validation |
|---|---|---|---|

**Localization / Risk Check**
...

**Next Validation Steps**
1. ...
2. ...

**Final Quality Gate**
...
```
