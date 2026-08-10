# Handoff Rules

| Trigger | Handoff target | What this skill should still provide |
|---|---|---|
| Finished video asset, editing, captions, voiceover assembly, motion, export | Creative video workflow | grounded video brief, script, assets, no-go claims, acceptance criteria |
| Finished product image, scene image, selling-point image, cover, static ad | Creative design workflow | grounded image brief, copy, specs, preserve/avoid, platform rules |
| Ad budget, campaign setup, Spark Ads scaling, Meta/Google/TikTok/Amazon account optimization | Outside this skill; do not route to a named ads skill unless a current ads/growth skill is available | content angles, creative test matrix, asset package, confirmed metric definitions and data limitations |
| Listing/PDP, title, bullets, attributes, product-page conversion, main image compliance | `doubao-listing-localization` | content implication and asset needs |
| Product eligibility, regulated claim, certification, IP, tax, customs, dangerous goods | `doubao-ecommerce-compliance-tax-logistics` | risky wording and content claim list |
| Product/category opportunity or market choice | `doubao-product-research` | content feasibility notes after candidates exist |

## Boundary Rules

- If the user asks “写 5 条 TikTok 脚本”, solve here.
- If the user asks “把这 5 条脚本生成视频”, create video packages and hand off to creative video.
- If the user asks “做一套 Amazon UK 礼品图素材”, create design packages and hand off to creative design.
- If the user asks “这些素材怎么投放/预算多少”, hand off to ads after defining creative variables.
- Before an ads handoff, run the lightweight checks in `performance-safety.md`: formula consistency, contribution-cost completeness, data maturity, attribution limits, and conclusion-threshold-action consistency.
- If high-risk claims appear, do not generate aggressive content before compliance review.
