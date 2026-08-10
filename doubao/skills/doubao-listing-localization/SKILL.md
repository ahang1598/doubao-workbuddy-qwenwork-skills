---
name: doubao-listing-localization
description: Cross-border ecommerce Listing and Product Optimization for Amazon, TEMU, Walmart Marketplace, TikTok Shop, Shopify, AliExpress, Etsy, Google Shopping, Shopee, Lazada, Ozon, and other marketplace or independent-store product pages. Use when the user asks to create, rewrite, translate, localize, audit, diagnose, or optimize product titles, bullet points, descriptions, A+ Content, backend search terms, tags, attributes, feed titles, PDP/detail pages, main images, image briefs, product images, category/attributes, variants, size charts, price display, coupons/promotions, Buy Box/Featured Offer readiness, listing quality, item setup, conversion, click potential, unpublished/suppressed products, or keyword-stuffed supplier titles. This skill combines listing SEO/localization with product-page optimization diagnosis and must check official product requirements, platform policy paths, and available Seller Center evidence before making platform-specific recommendations.
---

# Cross-Border Listing And Product Optimization

## Scope

This skill covers two tightly connected work modes:

1. **Listing creation and localization.** Turn product facts, supplier titles, screenshots, competitor pages, or Chinese copy into platform-ready titles, bullets, descriptions, A+ content, tags, attributes, backend search terms, feed fields, and image briefs.
2. **Product optimization diagnosis.** Diagnose and improve the sellability of a product page or item setup across PDP content, main image, attributes, variants, price display, coupons/promotions, Buy Box/Featured Offer readiness, inventory-visible issues, listing quality, and product suppression symptoms.

Treat Listing SEO as one part of Product Optimization. Do not split these tasks into separate skills. When a diagnosis shows that content fields need rewriting, complete the rewrite inside this skill.

## Core Workflow

1. **Classify the product task.** Identify whether the user needs listing copy, keyword research, localization, PDP audit, main image/image brief, attribute/category setup, variant/size-chart fix, price/offer diagnosis, conversion/click diagnosis, suppression/unpublished triage, or a combined product optimization plan.
2. **Extract platform and product context.** Pull out platform, target country/site, language, product/category, brand, specs, material, size, color, pack quantity, variants, fulfillment mode, price/promo state, issue symptom, objective, links, screenshots, exports, competitor examples, and requested output fields.
3. **Choose evidence paths before writing.** Read `references/source-map.md` for listing evidence and `references/product-optimization-source-map.md` for official product/page/offer evidence. Decide whether to use Seller Center, Seller University, Marketplace Learn, policy center, official help, API docs, public PDP/search pages, user files, competitor pages, ads reports, or keyword tools.
4. **Check official product requirements.** For product-page diagnosis or platform-specific claims, read `references/product-policy-checklists.md`. Official platform requirements and Seller Center notices beat competitor behavior and generic ecommerce experience.
5. **Extract product facts and current state.** Separate verified facts from assumptions. Build a table for product identity, title, images, bullets, description, A+ content, attributes, category, variants, size chart, price, coupons, rating/reviews, stock/fulfillment-visible state, offer status, traffic/conversion metrics, and unresolved backend-only fields. Record evidence scope as product family, parent, child SKU, or tested sample; do not silently generalize narrower evidence.
6. **Build the keyword and positioning map.** Read `references/keyword-taxonomy.md`. Create core keywords, attribute keywords, use-case terms, audience terms, occasion/gift terms, long-tail terms, backend/tags, and blocked or risky words. Avoid keyword stuffing.
7. **Benchmark competitors when available.** Extract 3-5 direct competitors or category leaders across title, image, price, offer, rating/reviews, bullets, A+ structure, attributes, variant setup, and review pain points. Use competitors for gap discovery, not as policy authority or copy source.
8. **Diagnose root causes when optimizing an existing product.** Read `references/product-diagnosis-playbooks.md`. Separate likely causes into traffic, click, trust, price, content, image, policy, inventory/fulfillment, category/attributes, offer, and data/reporting issues.
9. **Generate platform-ready improvements.** Read `references/platform-listing-rules.md`, `references/output-templates.md`, and `references/product-optimization-output-templates.md`. Produce the requested copy, field table, diagnosis table, image brief, and prioritized optimization plan. Complete every requested field or mark it `blocked: missing evidence`; do not omit weakly supported sections without saying so.
10. **Localize beyond translation.** Adapt buyer language, local category names, units, sizing, occasions, gift framing, benefit order, marketplace style, and claim boundaries for the target country/site.
11. **Run risk and handoff checks.** Read `references/risk-and-handoff.md`. Flag brand/IP terms, certification/medical claims, prohibited claims, price/promo/contact information, unsupported live data, policy uncertainty, and backend-only assumptions.
12. **Give validation steps.** Recommend the smallest next verification: check Seller Center notice, pull listing quality report, review Brand Analytics/Search Query Performance, compare PDP/search screenshots, test title/image, monitor CTR/CVR/sessions/orders, or gather missing backend exports.

## Mandatory Quality Gates

Run all applicable gates before presenting final copy or a completed diagnosis.

### 1. Evidence And Claim Gate

- Create a claim ledger for material, dimensions, weight, packaging, compatibility, certification/test results, safety, comfort, durability, performance, audience, and use-case claims.
- For each claim, record its source and scope: product family, parent, child SKU, model/year, or tested sample.
- Use a claim in shared parent copy only when the evidence covers every included child. Keep sample-specific test results and child-specific facts out of shared copy.
- Delete or qualify claims such as `comfortable all day`, `secure`, `safe`, `compatible`, or unsupported use scenes unless direct evidence supports the exact wording.
- Treat review pain points as research signals, not product facts. Do not turn them into affirmative claims without product evidence.
- Maintain a `verified`, `conditional`, and `blocked` claim whitelist. Final buyer-facing copy may use only `verified` claims; place conditional claims in validation notes.

### 2. Parent, Child, And Multi-Model Gate

- Distinguish the current selected child, text visible on the current page, actual default landing child, and seller-configured default. Do not infer one from another.
- Determine for each field whether the platform stores it at parent, child, or shared family level. Check title, bullets, description, images, dimensions, weight, compatibility, and backend terms separately.
- When child-level maintenance is available, write or map child-specific copy and assets. When it is unavailable or unverified, use neutral family-level wording or explicitly name all supported variants.
- Never anchor shared copy or images to one child's dimensions, weight, package contents, test result, or compatibility.
- Do not merge nearby models, model years, item codes, standards, or compatibility rules from a product name alone. Build a SKU/model matrix and mark unresolved differences.

### 3. Listing Completeness And Search-Term Gate

- Check the user's requested deliverables one by one. For a full Amazon listing, include title, 3-5 bullets or the category-allowed count, description, backend search terms, keyword layering, image sequence/brief, and risk notes unless the user narrows scope.
- Keep backend terms relevant and evidence-supported. Exclude brand/trademark terms without authorization, repeated visible-title terms, subjective claims, punctuation where disallowed, and speculative audiences, body locations, or use cases.
- Validate exact platform limits using the current official rule when limits matter. For byte-limited fields, calculate encoded bytes from the final text, state the encoding/method, and do not substitute a character count.

### 4. Final Consistency Gate

- Re-read the final copy, tables, attachments, and summary as one deliverable.
- Confirm variant facts, claim scope, field limits, SKU count, recommendations, and status labels agree everywhere.
- Remove contradictory actions such as "leave unchanged" in one section and "replace now" in another.
- Never claim that a file, formula check, platform validation, or upload-ready output is complete unless it was actually created and checked.

### 5. Mixed-Task Boundary Gate

- Identify when the request also requires PPC/bidding, inventory/replenishment, procurement allocation, margin/forecast modeling, logistics, tax, or legal eligibility.
- Complete the listing-side work that is supported, then explicitly route each remaining workstream to the appropriate skill or agent. State that the overall task is not complete until those workstreams return.
- Do not improvise spreadsheet formulas, replenishment decisions, ad budgets, or financial conclusions inside this skill and present them as validated business outputs.

## Input Rules

- Platform and target country/site are the highest-value inputs. If missing and the answer depends on platform rules or local language, ask a concise question. If proceeding asynchronously, default to `Amazon US` only when the query implies Amazon; otherwise use `global marketplace` and mark assumptions.
- Product/category is required for final listing copy. If missing, give an input checklist and template rather than inventing product details.
- For product diagnosis, ask for the product link, screenshot, item ID/ASIN/SKU, visible symptom, Seller Center notice, or export only when that evidence materially changes the answer.
- Treat user-provided links, screenshots, titles, spreadsheets, and Seller Center exports as first-party input, but label unverified attributes and backend-only gaps.
- A page showing a child-specific title or image does not prove which child opens by default. Label `current selected child`, `visible page state`, and `default child` separately.
- Public PDP pages can support visible content diagnosis, but they do not prove backend states such as suppression reason, Featured Offer status, listing quality score, inventory health, or account status.
- If the user provides a Chinese supplier title, first extract product attributes and buyer-facing value, then rewrite. Do not translate it literally.
- Do not invent search volume, live keyword rank, sales rank, policy status, account status, Buy Box/Featured Offer status, suppression reason, traffic, conversion, or official requirements.

## Quality Bar

A good answer:

- Starts with task understanding, key assumptions, missing inputs, and the selected work mode.
- Names the platform/site, product/category, and diagnosis or copywriting target.
- Uses official/source paths before platform-specific recommendations.
- Outputs structured tables for product facts, current-state fields, keyword map, listing fields, diagnosis, and prioritized actions as needed.
- Separates final copy, rationale, validation gaps, and backend-only unknowns.
- Preserves parent/child/model evidence scope and never applies a child- or sample-specific fact to the whole family.
- Completes all requested listing fields and passes the evidence, variation, search-term, and final consistency gates.
- Adapts language to platform and country/site instead of literal translation.
- Flags brand/IP, certification, medical, absolute, promotional, contact, or unsupported claims.
- Gives a concrete validation loop and metrics to recheck.

Avoid:

- Keyword-stuffed titles that read like search dumps.
- Fabricated keyword volume, ranking, sales, policy, account status, Buy Box/Featured Offer status, or official platform requirements.
- Diagnosing from generic ecommerce experience while ignoring official requirements.
- Treating competitor behavior as proof that something is compliant.
- Calling a policy violation, price cause, suppression reason, or offer issue certain without backend evidence.
- Generic marketing copy that ignores platform, site, category, product attributes, and buyer language.
- Copying competitor content as a fix.
- Solving legal/tax/IP/customs, fulfillment strategy, PPC campaign structure, or short-video scripting inside this skill when the request should be handed off.

## Default Output Sections

Use this structure unless the user asks for a different format:

1. **Task understanding and assumptions**
2. **Source / official verification plan**
3. **Product fact and current-state extraction**
4. **Keyword / positioning map**
5. **Listing or PDP optimization output**
6. **Diagnosis and prioritized action plan**
7. **Localization, policy, and risk check**
8. **Next validation steps**
9. **Final quality-gate result**

For pure listing generation, sections 3-5 may be the main output. For product diagnosis, sections 2, 3, 6, and 8 are mandatory.

## Handoff Rules

- If the user is deciding whether to enter a product/category, hand off to `doubao-product-research`.
- If the user asks whether a product can legally be listed, certified, imported, taxed, shipped, or avoids infringement, hand off to `doubao-ecommerce-compliance-tax-logistics`.
- If the user asks about FBA/FBM setup, overseas warehouse strategy, customs, HS codes, DDP/DDU, or shipping cost optimization, hand off to `doubao-ecommerce-compliance-tax-logistics`.
- If the user asks for PPC structure, bids, match types, ACOS/TACOS, ad groups, Google Shopping campaigns, or paid/offsite traffic strategy, mark it as outside this skill and do not route to a named skill unless a current ads/growth skill is available.
- If the user asks for TikTok scripts, UGC briefs, creator content, TTS voiceover, or short-video material after listing positioning is clear, hand off to `doubao-cross-border-growth-content`.
- If one request combines listing work with ads, inventory, procurement, finance, forecasting, or logistics, provide the listing deliverable and a workstream handoff table. Do not describe the integrated task as complete until the responsible skills or agent have validated their parts.
