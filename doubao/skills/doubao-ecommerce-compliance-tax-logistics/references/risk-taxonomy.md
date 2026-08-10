# Risk Taxonomy

## Risk Levels

| Level | Meaning | Required response |
|---|---|---|
| P0 | Direct blocker for the affected SKU or batch under the current evidence; shipment, booking, clearance, stocking, listing, or sale cannot proceed | Stop the affected action; state affected SKU/batch, failed evidence, exact closing evidence and owner |
| P1 | Conditional blocker that can be closed by a specified formal document, platform result, written confirmation, or route change; it remains blocking until closed | State affected SKU/batch, exact closing condition, owner and verification source |
| P2 | Manageable risk or optimization issue | Give field fix, policy check, and monitoring step |
| P3 | Information gap | Ask for specific missing fields and provide generic checklist |

If the user defines P0, P1, observation items, or a release gate, use the user's definitions instead of this default taxonomy. Do not elevate every important issue to P0.

## Calibration Notes

Use these as default calibration anchors when the user has not defined risk levels. They are reasoning aids, not exhaustive rules.

- **P0 examples:** evidence mismatch or missing evidence that directly blocks the affected shipment, booking, import, platform warehouse intake, listing, or sale. Examples include UN38.3 not covering the production cell/model for a lithium-battery shipment; dangerous goods classification not approved for the route; platform hazmat status still `Under review` when warehouse intake depends on classification; illegal low declaration, wrong origin, borrowed EORI/VAT, or no identifiable IOR for the import route; missing mandatory approval/certificate/registration required before sale or import for the exact SKU/batch.
- **P1 examples:** formal evidence gaps that can be closed before release without necessarily changing the core route. Examples include a DoC or label using the wrong brand/model but correctable with a revised signed file; final broker CN/TARIC/HS written confirmation pending after candidate analysis; packaging/manual/local-language corrections; route-specific tax or EPR evidence that must be confirmed before commercial shipment or stocking.
- **P2 examples:** execution quality, monitoring, or optimization issues that do not block the affected batch after P0/P1 gates are closed. Examples include improving document naming, adding internal owner/deadline fields, refining return SOPs, or comparing cheaper logistics options.
- **P3 examples:** missing non-decision-critical fields where a generic checklist is acceptable until the user supplies details.

When a fact affects only one batch, do not block unrelated batches unless capacity, tax, document, or platform dependencies connect them. When evidence supports only “not currently committable,” do not convert it into a new promised launch date.

## Risk Categories

| Category | Signals | Evidence to request |
|---|---|---|
| Prohibited/restricted products | Alcohol, drugs, medical devices, supplements, food, cosmetics, children products, weapons, plants, batteries, liquids, powders, dangerous goods, recalled items | Platform policy page, category approval screen, product specs, SDS, certificate |
| Certification / safety | CE/FCC/UL/CPC/Prop 65/EAC, food contact, cosmetics, electronics, toys, PPE, medical claims | Test report, certificate, lab, label, technical file |
| Claims / advertising compliance | Whitening, cure, anti-aging, antibacterial, medical, guaranteed results, “FDA approved”, environmental claims | Claim text, ingredients, substantiation, local ad rules, platform policy |
| IP / brand | Brand names, logos, characters, patented design, supplier “inspired by”, gray market, no authorization | Trademark/patent search, authorization letter, invoice chain, owner info |
| Tax | VAT/GST/Sales Tax, OSS/IOSS, Nexus, warehouse in market, platform vs independent store | Seller entity, tax IDs, sales/transactions, warehouse location, platform facilitator status |
| HS / tariff | Generic product description, unclear material/use, multiple possible codes, high duty category | Specs, material composition, function, origin/destination, candidate HS, broker feedback |
| Customs / import restriction | Missing COO, undervaluation, vague invoice, sanctions, restricted import, special permit | Commercial Invoice, COO, import permits, sanctions screening, broker request |
| Logistics / fulfillment | FBA hazmat, lithium battery, oversized item, low-value DDU surprise, return risk, warehouse capacity | Weight/dimensions, SDS, fulfillment mode, carrier rules, Seller Center inventory screens |

## Hard Rules

- Official policy beats competitor practice.
- Public product pages do not prove backend eligibility, tax setup, FBA approval, or customs clearance.
- HS/tariff and tax outputs are candidates unless confirmed by official source, customs broker, tax advisor, or platform backend.
- IP search is a risk signal, not a legal clearance opinion.
- If P0/P1 risk exists, make it visible before listing, ads, shipment, or inventory recommendations.
- Record risks per SKU and affected batch. A B-batch issue must not block A unless the evidence or capacity dependency actually affects A.
- Close a risk only with evidence that explicitly covers the relevant SKU/model, manufacturer/factory, version and time cutoff.
- `Under review` is not `Approved` or `Classified`; UN38.3 does not prove SDS/MSDS coverage; an invoice does not automatically prove market authorization.
- If a deadline is not supportable, say it cannot currently be committed. Do not invent a replacement date.
