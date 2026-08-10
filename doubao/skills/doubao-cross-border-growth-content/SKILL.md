---
name: doubao-cross-border-growth-content
description: Evidence-grounded cross-border ecommerce content operations for short-video and livestream scripts, UGC or creator briefs, multilingual captions, localized content angles, image/video briefs, content calendars, hook matrices, creative tests, Spark or creator reuse, and production handoffs. Use for content-first or mixed content-and-growth requests on TikTok Shop, Instagram/Reels, Meta, Amazon, Shopify, Shopee, Lazada, AliExpress, Ozon, and similar channels. For ads-only budget, bid, account-structure, scaling, or pause decisions, validate evidence and creative implications only; do not route to a named ads skill unless a current ads/growth skill is available.
---

# Cross-Border Content Ops V2.1

Follow the steps below in order. Do not skip a gate because the answer seems obvious.

## 1. Choose Exactly One Mode

| Mode | Use when | This skill may do |
|---|---|---|
| `content_primary` | The main deliverable is a script, content plan, creator brief, localization, image/video brief, or creative test | Complete the requested content work |
| `mixed` | Content plus PDP, authorization, tracking, or advertising diagnosis | Complete content work; give only evidence-safe growth diagnosis |
| `ads_primary` | The main deliverable is budget, bids, campaign structure, scaling, channel allocation, or stop-loss | Validate metrics and creative implications only; do not route detailed actions to a named ads skill unless a current ads/growth skill is available |

Do not turn an `ads_primary` request into a long content plan. Do not give detailed account actions merely because content is mentioned.

## 2. Build Two Short Internal Lists

Before drafting, extract:

1. `required_deliverables`: every explicit item the user requested.
2. `evidence_ledger`: facts using only these states:
   - `confirmed`: stated in the current user input, identified attachment, visible evidence, or authoritative product document;
   - `assumption`: a labeled working hypothesis;
   - `missing`: not provided or not verified.

Final marketing copy, scripts, image text, and product briefs may use only `confirmed` product facts, offers, accessories, proof, rights, and platform status. Assumptions may appear only in analysis. Missing fields stay `null`, `[待确认]`, or outside the final copy.

Never fill a blank with category knowledge, a previous-turn suggestion, an industry average, or a plausible product feature.

## 3. Read Only the Required References

Always read:

- `references/evidence-and-quality-gates.md`

Then route:

- Performance metrics, budget, scaling, pause, channel comparison, or paid amplification: `references/performance-safety.md`
- Scripts and content angles: `references/content-playbooks.md` and `references/script-templates.md`
- Claims or sensitive categories: `references/category-claim-risk.md`
- Market or language adaptation: `references/localization-and-market-lenses.md`
- Spark, UGC, creator, or paid reuse: `references/creative-video-handoff.md` and `references/creator-brief.md`
- Image assets: `references/creative-design-handoff.md`
- Platform material specs, feed/image/video material requirements, or channel-specific asset checks: `references/platform-material-rules.md`
- Structured output tables, evidence ledgers, creative test plans, or downstream generation packages: `references/output-templates.md`
- Platform procedures or policy claims: `references/source-map.md`
- Detailed handoff matrix: `references/handoff-rules.md`
- Repeated evaluation failures or ambiguous cases: `references/failure-patterns.md`

## 4. Apply Non-Negotiable Gates

### Fact Gate

- Every number, material, capability, duration, accessory, offer, review, certification, performance claim, right, and platform status must trace to `confirmed` evidence.
- Do not invent fast charging, seconds-level output, easy/self-cleaning, blade count, battery life, included cable/manual, waterproofing, ingredient compatibility, free shipping, returns, reviews, or local price.
- A requested final script with missing operating facts must use a safe scene or visible confirmed specification, not a guessed demo.

### Platform And Rights Gate

- Treat Spark/Partnership authorization, code flow, account type, territory, duration, edit rights, music rights, and approval as path-specific.
- State an official rule only with an official URL, applicable market/account path, and check date. Otherwise label it `待后台/官方确认`.
- Platform approval does not prove product truth, translation quality, legal compliance, or usage rights.

### Localization Gate

Label localized copy as exactly one of:

- `machine_draft`;
- `bilingual_meaning_checked`;
- `native_reviewed`.

Do not imply native review unless a named reviewer or user-provided confirmation exists.

### Performance Gate

When any CTR/CPC/CVR/CPA/ROAS/ACOS, budget, scaling, or pause decision appears:

1. Define numerator, denominator, currency, reporting/attribution window, aggregation level, and maturity.
2. Reverse-check the supplied metrics.
3. Treat gross margin and contribution margin as different.
4. If material variable costs are incomplete, show only a scenario formula; do not claim a verified break-even point.
5. Any increase in total budget is scaling, regardless of labels such as “validation increase”.
6. If the unit is immature, inconsistent, below the verified profitability gate, or lacks a safety margin, total budget must not increase.
7. Do not invent universal bid changes, sample sizes, observation days, conversion counts, loading-time targets, or scaling percentages.
8. Without creative-level data, do not name a winning or losing creative.

For every recommended budget or status action, fill:

`conclusion → required evidence/threshold → current state → permitted action`

If the four parts do not agree, revise the action before answering.

## 5. Produce the Smallest Complete Answer

Prioritize explicit user deliverables over generic background. Use tables only when they prevent ambiguity.

For mixed requests:

1. state the task mode and primary bottleneck;
2. provide the requested content deliverables;
3. add the minimum safe performance or rights diagnosis;
4. route deeper account, listing, compliance, or production work.

Do not change several material variables in one test and then attribute the result to one of them. Separate observation, interpretation, decision, and next isolating test.

## 6. Run a Binary Final Check

Do not deliver until every applicable item passes:

- `PASS` — all requested deliverables are present;
- `PASS` — final claims are a subset of confirmed evidence;
- `PASS` — formulas reconcile or conflicts are explicitly blocking;
- `PASS` — thresholds, conclusions, and actions agree;
- `PASS` — no below-gate or immature unit receives more total budget;
- `PASS` — dynamic rules have source context or are marked for verification;
- `PASS` — localization and rights status are honest;
- `PASS` — generated files or assets are actually verified before claiming completion.

If an item fails, provide a safe partial result and the smallest missing-information list instead of pretending completion.

## Output Contract

Use only the sections required by the task:

1. mode, conclusion, and high-impact missing fields;
2. requested script, matrix, brief, calendar, or handoff;
3. evidence/claim notes and localization/rights status;
4. performance gate table when applicable;
5. concise next action or handoff;
6. deliverable checklist for multi-part requests.

## Handoffs

- Finished video, editing, captions, voice, motion, or export: creative video workflow.
- Finished ecommerce image, cover, product scene, or static ad: creative design workflow.
- Budget, bids, campaign structure, ACOS/ROAS/CPA optimization, scaling, or account stop-loss: outside this skill; do not route to a named ads skill unless a current ads/growth skill is available.
- Listing/PDP copy, attributes, main-image compliance, or conversion diagnosis: `doubao-listing-localization`.
- Claims, certification, IP, product eligibility, tax, customs, or dangerous goods: `doubao-ecommerce-compliance-tax-logistics`.
- Product/category opportunity: `doubao-product-research`.
