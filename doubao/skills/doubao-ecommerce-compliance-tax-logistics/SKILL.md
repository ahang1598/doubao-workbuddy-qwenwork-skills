---
name: doubao-ecommerce-compliance-tax-logistics
description: Cross-border ecommerce compliance, tax, IP, customs, tariff, HS code, fulfillment, warehousing, China import, and clearance workflow for marketplace and independent-store sellers. Use when the user asks whether a product can be sold, listed, imported, exported, shipped, fulfilled, or cleared; whether it needs certification, labeling, authorization, trademark/IP review, VAT/GST/Sales Tax, OSS/IOSS/Nexus, China Customs/CCC/GB standards, HS classification, tariff, commercial invoice, COO, DDP/DDU, FBA/FBM, overseas warehouse, 3PL, dangerous goods, restricted/prohibited product review, customs documentation, or SKU/invoice/packing-list/logistics/tax file reconciliation. This skill is source-first and evidence-bound; do not provide final legal, tax, IP, customs, HS, tariff, platform-policy, or numerical conclusions without required evidence and validation.
---

# Cross-Border Ecommerce Compliance Risk, Tax And Logistics Clearance

## Scope

This skill combines three linked cross-border workflows:

1. **Compliance and product eligibility.** Product admission, prohibited/restricted products, certification, labeling, claims, safety, dangerous goods, and platform policy risk.
2. **Tax and IP risk.** VAT/GST/Sales Tax, OSS/IOSS, Nexus, Marketplace Facilitator, trademark, patent, copyright, brand authorization, gray market, and counterfeit risk.
3. **Customs and logistics clearance.** HS code, tariff, landed cost, Commercial Invoice, COO, CN22/CN23, DDP/DDU, FBA/FBM, overseas warehouse, 3PL, inventory/fulfillment constraints, and customs documents.

Treat these as one merchant workflow around a product, country, platform, and fulfillment route. Use references to route details instead of splitting the task into separate skills.

## Core Workflow

1. **Select the execution mode.** Use advisory mode for ordinary questions. Use evidence-bound file mode whenever the request includes spreadsheets, invoices, packing lists, SKU masters, quotations, multiple attachments, numerical models, generated Word/Excel/CSV files, or updates to a prior deliverable. Combined tasks must complete the evidence-bound facts and calculations before giving compliance or logistics conclusions.
   - **Verify before concluding.** Any decision-critical statement about platform rules, tax rates, registration thresholds, mandatory certifications, HS/tariff, dangerous goods transport, import rules, or official filing status must be tied to an official or first-party source path and a verification date. If the source cannot be checked in the current run, label the item as unverified and provide the validation owner/path instead of stating it as final.
2. **Classify the business path.** Identify product eligibility, restricted/prohibited product, certification/labeling, claims, IP/brand authorization, tax, HS/tariff, customs documents, DDP/DDU, fulfillment/warehouse, China import, or a combined “can we sell and ship this?” task.
3. **Extract the decision-critical trade fields.** Collect only the fields needed for the user's question, such as product name, material, use, platform, target country/site, origin, ship-from, warehouse location, seller entity, value, weight, dimensions, brand/IP elements, fulfillment mode, and evidence provided. Use `references/response-reference-patterns.md` as optional reasoning aids for complex or file-heavy work, not as a mandatory response shape. Never equate ship-from/export country with country of origin.
4. **Reconcile files before analysis.** In evidence-bound file mode, read `references/cross-file-reconciliation.md`. Build a source inventory, normalized SKU evidence ledger, discrepancy table, calculation ledger, and control-total table before writing the conclusion.
5. **Run admission and restriction pre-screen.** Before optimizing logistics, check whether each SKU may be prohibited, restricted, certified, hazardous, infringing, claim-sensitive, or blocked by missing evidence. Read `references/risk-taxonomy.md`. Do not apply one SKU's document status to another SKU merely because the products are similar.
6. **Choose official source paths.** Read `references/source-map.md`. For China as the import destination, also read `references/china-import-playbook.md`. Prefer official government, customs, tax authority, platform policy, Seller Center, trademark/patent database, carrier, or first-party seller evidence.
7. **Route only to needed references.** Use `references/tax-ip-playbooks.md` for tax/IP, `references/hs-tariff-customs-workflow.md` for HS/tariff/customs/DDP/DAP/IOR, and `references/fulfillment-playbooks.md` for FBA/FBM/warehouse/3PL. For battery, wireless, skin-contact, children's, electrical, food/cosmetics/liquid/powder/chemical, or other high-risk products, read `references/high-risk-product-check-trees.md`. Do not load or reproduce generic risk material that does not affect the task.
8. **Separate facts, assumptions, calculations, and unknowns.** Record the source of every decision-critical fact. Public pages, Accio/WorkBuddy, third-party tools, and competitor behavior are candidates unless verified. Missing values remain missing; do not infer weights, dates, rates, certification coverage, or document status without an explicit assumption requested by the user.
9. **Assign risk and evidence status.** Use `references/risk-taxonomy.md`. Apply the user's P0/P1/observation definitions when provided. Record risk per SKU and affected shipment batch, together with the exact evidence required to close it.
   - **Respect user gates.** If the prompt defines release gates, stop conditions, P0/P1 closure rules, or “do not ship before X” constraints, those rules override any generic playbook. Do not invent relaxed thresholds such as “close 6 of 8 P1 items” or recommend trial shipment, partial shipment, DAP/DDP shipment, warehouse transfer, FBA inbound, or listing launch while any user-defined blocking gate remains unresolved.
10. **Build deliverables from one fact model.** Generate any requested text response, Excel, CSV, or Word report from the same reconciled facts and calculation ledger. Use `references/document-checklists.md` for cost/formula discipline and file-delivery quality gates. Use `references/response-reference-patterns.md` only when a table or structured handoff will make the answer clearer.
11. **Pass the final gates.** Recompute control totals from detail, compare every cross-deliverable total and status, validate table schemas and formulas, and stop if a core total or SKU status is inconsistent. Do not issue a final release recommendation or final numerical answer while a gate fails.
   - **Validate generated files before claiming completion.** For Excel/CSV/Word deliverables, scan for formula errors such as `#NAME?`, `#VALUE!`, `#REF!`, missing formulas where formulas are required, formula explanations accidentally written as formulas, hard-coded derived totals, inconsistent summary/detail values, impossible carton/unit math, and visible generation artifacts. If any error remains, report the file as draft or repair it before delivery.
12. **Give prioritized actions and hand off.** Resolve admission/IP/tax blockers first, then HS/tariff/customs, then fulfillment. Use `references/handoff-rules.md` only after the relevant risk boundaries are clear.

## Mandatory Decision Gates

Before recommending listing, commercial shipment, FBA/warehouse inbound, overseas warehouse transfer, DDP/DAP route execution, or paid launch, check these gates in order:

1. **User-defined gates.** Follow the prompt's release/hold/P0/P1 rules exactly. If the user says P0/P1 must be closed before shipment, no trial shipment or partial shipment is allowed until those gates close.
2. **Product and platform eligibility.** Restricted/prohibited status, certification coverage, labeling, claims, IP authorization, dangerous goods classification, platform backend approval, and product-document match must be closed for the affected SKU/batch.
3. **Importer and tax chain.** IOR/EORI/VAT/GST/Sales Tax/Nexus/OSS/IOSS/Marketplace Facilitator assumptions must be separated by route and channel. Inventory in marketplace warehouses, 3PL, FBA, local stock, direct mail, and independent-store sales cannot be collapsed into one tax conclusion.
4. **Customs and valuation.** HS code, origin, declared value, invoice, packing list, Incoterms, import VAT/GST base, broker/carrier requirements, and low-value import rules must be validated or clearly marked as candidates.
5. **Dangerous goods and fulfillment.** Battery/liquid/powder/chemical/magnet/pressurized/medical/children or other risk attributes require SKU/batch-specific evidence, carrier acceptance, and platform warehouse approval where applicable.
6. **File and calculation integrity.** If any generated workbook/report contains unresolved formula errors, inconsistent totals, wrong carton math, missing source mapping, or mismatched narrative-vs-file decisions, the deliverable cannot be called final.

If any gate fails, output `HOLD`, `NO-GO`, or `CONDITIONAL TEST` only as allowed by the user's definitions, and list the exact closing evidence, owner, and verification path.

## Detailed Reference Routing

- For DDP/DAP/IOR, customs representation, EORI/VAT/GST evidence, MRN/import-tax records, low declaration, sample misdescription, borrowed tax numbers, shared EORI, or platform-as-IOR claims, read `references/hs-tariff-customs-workflow.md`.
- For battery, wireless, skin-contact, children's, electrical, food/cosmetics/liquid/powder/chemical, or other high-risk product attributes, read `references/high-risk-product-check-trees.md`.
- For Excel/CSV/Word deliverables, formula validation, carton math, cost layers, amortization, generated-file artifacts, and cross-deliverable consistency, read `references/document-checklists.md`.
- Use `references/response-reference-patterns.md` as optional reusable thinking and table shapes. Do not force every answer into every pattern.

## Input Rules

- Target country/region and platform are required for specific compliance, tax, import, or platform-policy guidance. If missing, provide a generic checklist and ask for them.
- Product details are required: commercial name, material, ingredients, function, target user, risk attributes such as battery/liquid/powder/food/cosmetics/medical/children/electronics, and brand/IP elements.
- HS/tariff/customs tasks require origin country, destination country, product description, material/use, declared value, currency, quantity, and preferably candidate HS or supplier specs.
- Tax tasks require seller entity, marketplace/independent store, ship-from/warehouse location, customer destination, sales volume/transaction count, B2B/B2C, tax IDs, and whether the platform collects/remits tax.
- Fulfillment tasks require platform, fulfillment mode, weight/dimensions, packaging, inventory volume, sales velocity, return expectation, dangerous goods status, and target service level.
- China import tasks require the Chinese importer/consignee, trade mode, origin, ship-from country, SKU-level product attributes, proposed HS, transaction terms, invoice, packing list, CCC/standard/label status, IP authorization chain, and destination sales channel.
- Evidence-bound file tasks require an input-file inventory and source hierarchy. Chat records, old drafts, supplier claims, and quotations are clues unless the task explicitly designates them as authoritative.
- Do not invent official rules, tax rates, HS codes, duty rates, platform approval status, certification requirements, IP clearance, account status, freight cost, or delivery time.

## Quality Bar

A good answer:

- Identifies the dominant path and any cross-path dependencies.
- States the decision-critical facts and missing information in the lightest clear format.
- Cites official or first-party verification paths before high-risk recommendations.
- Uses risk levels and clearly separates candidates from verified facts.
- Reconciles SKU count, total units, total merchandise value, origin counts, invoice totals, packing-list weight, batch costs, taxes, landed cost, sales value, and margin whenever those fields exist.
- Keeps SKU-level evidence status separate and traceable to source file, location, version, and date.
- Makes the narrative, Excel, CSV, and Word report agree on every decision-critical number and status.
- Gives document and backend evidence checklists that a seller can use.
- Avoids final legal, tax, IP, customs, HS, tariff, or platform-policy conclusions unless the user supplied official evidence.
- Produces a prioritized action plan with handoff boundaries.

Avoid:

- Answering “can sell / cannot sell / no tax / no infringement / HS is definitely X” without official evidence.
- Treating Accio, WorkBuddy, third-party tools, competitor listings, or public marketplace pages as policy authority.
- Mixing tax, IP, customs, and logistics into generic advice without field extraction.
- Recommending inventory shipment, FBA/warehouse, listing, or ads before resolving P0/P1 compliance blockers.
- Providing legal, tax, broker, or attorney-level advice as a final professional conclusion.
- Producing a polished final answer while any core detail-to-summary reconciliation fails.
- Copying one SKU's UN38.3, SDS/MSDS, battery declaration, CCC, authorization, or approval status to another SKU without explicit coverage evidence.
- Hard-coding derived totals in generated files when formulas or a shared calculation model can preserve auditability.

## Response Style

Use this skill and its references as reasoning aids, not few-shot examples or fixed report formats. Keep ordinary advisory answers proportional to the request. Do not force every generic risk section, table, or template into simple questions.

For simple advisory tasks, a concise answer usually covers:

- conclusion or recommended posture;
- key reasons or blockers;
- missing evidence or verification path;
- next actions.

For complex, multi-SKU, multi-country, multi-channel, or high-risk tasks, choose only the useful dimensions from:

- task understanding and selected path;
- decision-critical fields and missing information;
- official source / verification path;
- compliance, tax, IP, admission, HS, customs, and fulfillment risks;
- required documents and backend evidence;
- prioritized next actions and unresolved handoff risks.

For evidence-bound file mode, make sure the response or deliverable is backed by:

- input source and version inventory;
- cross-file reconciliation and discrepancy tracking;
- SKU evidence/status reasoning;
- calculation ledger and control-total validation.

Before delivery, run an internal consistency check covering the text response, Excel, CSV, and Word report when those deliverables exist. Report only the final validation result to the user; do not expose scripts, debugging logs, or repair traces.

## Handoff Rules

- Product opportunity, market demand, competitor selection, and profit validation: `doubao-product-research`.
- Listing title, bullets, PDP optimization, keywords, images, localized copy, and claims-safe copy rewrite: `doubao-listing-localization`.
- PPC, bids, match types, ACOS/TACOS, ad groups, Google Shopping campaigns, and paid/offsite growth: outside this skill; do not route to a named skill unless a current ads/growth skill is available.
- TikTok scripts, UGC, creator briefs, short-video materials, and TTS/voiceover: `doubao-cross-border-growth-content`.
