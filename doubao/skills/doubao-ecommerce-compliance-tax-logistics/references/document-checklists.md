# Document Checklists

## Product Compliance / Admission

- Product specification sheet.
- Ingredient/material composition.
- Test report or certificate if category requires it.
- Label and warning text.
- Product photos, packaging photos, user manual.
- Platform category approval or restriction notice.
- SDS or exemption sheet for chemicals, liquids, batteries, aerosols, cosmetics, cleaners, and similar goods.

## IP / Brand

- Brand authorization letter.
- Supplier invoice and distributor chain.
- Trademark/patent search screenshots.
- Product design ownership or license.
- Packaging/logo/artwork source.

## Tax

- Seller legal entity and country.
- Tax IDs and registration jurisdictions.
- Marketplace tax reports.
- Warehouse/FBA/3PL locations.
- Sales volume and transaction counts by jurisdiction.
- B2B VAT IDs and VIES validation evidence for EU B2B.
- Refund/void records.

## Customs / Logistics

- Commercial Invoice.
- Packing List.
- HS code candidates and classification evidence.
- Country of Origin.
- Declared value and currency.
- Incoterms / DDP-DDU setting.
- Receiver name, address, phone, email.
- Weight/dimensions by SKU and carton.
- Carrier or 3PL quote.
- Import permits, COO, or trade agreement documents when applicable.

## Backend Evidence

- Seller Center restricted-product or category approval screen.
- Account Health / violation notice.
- FBA dangerous goods classification.
- Inventory Performance / capacity / stranded inventory screens.
- Shopify duties/tax settings and product customs fields.
- Platform order/tax/fulfillment exports.

## China Import

- Chinese importer/consignee and trade-mode evidence.
- Commercial Invoice and Packing List aligned to SKU master.
- Country-of-origin evidence separated from export/ship-from country.
- Candidate HS and declaration-element worksheet.
- CCC catalogue/rule check and official certificate query for the exact model/factory.
- Current applicable GB standard and implementation-status evidence.
- Chinese label, manual, warning and packaging review.
- Import permits or product-specific approvals when applicable.
- Import VAT/consumption-tax calculation and customs payment evidence.
- Brand authorization, invoice chain and customs IP review.

## File Delivery Quality

- Reconciliation table with SKU, units, value, origin, invoice, weight, batch cost, tax and landed-cost controls.
- Calculation ledger with formulas, units, allocation bases, rounding and source locations.
- Narrative, Excel, CSV and Word consistency result.
- Generated files reopened and checked for formulas, totals, column alignment, encoding, watermarks, AIGC metadata, local paths and debug traces.
- Formula errors scanned before claiming final delivery: `#NAME?`, `#VALUE!`, `#REF!`, `#DIV/0!`, broken external links, missing formulas where formulas are required, formula explanations accidentally written as formulas, and summary cells that no longer reference the calculation sheet.
- Carton, unit, weight, dimension, volume, value, tax, landed-cost, and contribution math checked from detail to summary. Impossible combinations, such as carton math that does not equal stated units, block final delivery.
- Derived totals should come from formulas or a shared calculation model. Do not hard-code derived totals unless the user explicitly asks for a static report.
- If any file still has unresolved formula errors, inconsistent totals, wrong carton math, missing source mapping, or mismatched narrative-vs-file decisions, call it a draft or repair it before delivery.

## Cost And Formula Discipline

Separate and label every numerical layer:

| Layer | Examples / rule |
|---|---|
| Product and origin cost | Product cost, packaging, inspection, domestic freight, export declaration, pickup. |
| International freight | Air/sea/rail/truck freight, fuel surcharge, insurance, dimensional weight, carrier quote assumptions. |
| Customs and tax | Customs value, duty base, duty, import VAT/GST base, import VAT/GST cash outlay, brokerage, disbursement. |
| Platform and warehouse | Inbound, placement, storage, fulfillment, removal, disposal, return, loss, aged inventory. |
| Compliance cost | One-time certification, testing, registration, representative, attorney/advisor, label or packaging remediation. |
| Commercial result | Net landed cost, sales net revenue, contribution before amortization, contribution after amortization, and price threshold. |

Rules:

- Customs value, duty base, import VAT/GST base, cash outlay, recoverable tax assumption, net landed cost, sales net revenue, contribution before amortization, contribution after amortization, and price threshold must not be mixed.
- One-time compliance costs may be shown as a separate scenario or amortized sensitivity, but the non-amortized operating contribution must remain visible when requested.
- Do not invent exchange rates, freight rates, duty rates, tax rates, thresholds, dimensional-weight rules, surcharge rules, or variance thresholds. Use provided data, official fee tables, carrier quotes, or mark as assumption.
- Imported tax recoverability must be stated as a condition tied to registration, correct importer/tax identity, usable import tax evidence, and advisor confirmation where needed.
