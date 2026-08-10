# HS, Tariff And Customs Workflow

## HS / Tariff Required Fields

| Field | Why it matters |
|---|---|
| Product name in English and local language | Search and customs description |
| Material / composition | Chapter and heading selection |
| Function / use / working principle | Classification rule |
| Product form and specs | Distinguish similar categories |
| Origin country | Tariff and trade measures |
| Destination country | Import tariff schedule |
| Declared value and currency | Duty/tax calculation |
| Quantity / unit | Specific duty or statistical unit |
| Candidate HS or supplier code | Starting point only |
| Photos/spec sheet/manual | Support broker or binding ruling request |

## Classification Workflow

1. Extract fields and identify classification uncertainties.
2. Search official tariff schedule or customs rulings for similar goods.
3. Compare candidate headings by material, use, and notes.
4. Mark candidate HS codes with confidence and unresolved fields.
5. Ask customs broker or submit binding ruling when value/risk is high.
6. Never present a final HS code or duty rate as certain unless official/broker evidence is supplied.

## Customs Documents

| Document | Core fields |
|---|---|
| Commercial Invoice | Seller/exporter, buyer/importer, phone, detailed product description, HS, COO, quantity, unit value, total value, currency, Incoterms, reason for export |
| Packing List | Cartons, quantity, weight, dimensions, SKU, package count |
| Certificate of Origin | Manufacturing country, producer/exporter, trade agreement claim if any |
| CN22/CN23 | Postal customs declaration, value, contents, HS/description where applicable |
| SDS / Dangerous Goods docs | Ingredients, UN number, hazard class, transport restrictions, exemption sheet |

## DDP / DDU

| Term | Meaning | Risk |
|---|---|---|
| DDP | Seller collects/pays duties/taxes before delivery | Better customer experience; seller bears classification/cost risk |
| DDU / DAP | Buyer may pay duties/taxes on delivery | Lower seller setup burden; refusal and surprise-fee risk |

## DDP / DAP / IOR Gate

Do not treat DDP, freight-forwarder handling, platform warehousing, Amazon FBA, or a carrier quote as proof that import responsibility is legally solved.

For every DDP/DAP/warehouse route, explicitly split:

| Layer | Required check |
|---|---|
| Cost / risk allocation | Incoterms or commercial quote responsibility. |
| Importer of Record | Named legal entity, authority to import, and relationship to seller. |
| Customs representation | Direct/indirect representative, broker, Power of Attorney if relevant, and who submits entries. |
| Tax identity and evidence | EORI/VAT/GST/Sales Tax ID, MRN/entry number, import VAT/GST invoice, tax deductibility assumptions, and whether the seller can obtain usable records. |
| Declaration integrity | HS candidate, origin, value, description, quantity, and whether any low declaration, sample misdescription, borrowed tax number, shared EORI, or platform-as-IOR claim appears. |

If these layers are not documented, call the route unresolved even if the freight quote says `DDP`.

Red flags that block shipment until resolved:

- Amazon, a marketplace, or a 3PL is named as IOR without official written evidence that this is allowed for the specific route.
- The quote relies on a shared EORI/VAT/GST number, borrowed tax number, no import tax record, or no usable MRN/entry record.
- The broker, carrier, or supplier suggests low declaration, sample misdescription, wrong origin, vague description, or HS code reuse without product-specific review.
- The seller cannot identify who will own customs, tax, recall, return, or audit obligations after import.

Output the route status as `closed / open / not applicable / needs broker or tax-advisor confirmation`.

## Response Considerations

When relevant, make the answer clear on:

- candidate HS/customs reasoning with source and caveat;
- required documents and missing fields;
- landed cost fields, without fabricating final cost;
- official or broker verification next step.
