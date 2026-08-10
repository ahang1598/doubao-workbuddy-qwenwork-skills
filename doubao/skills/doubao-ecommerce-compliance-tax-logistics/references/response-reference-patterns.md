# Response Reference Patterns

These are optional reasoning and response patterns for complex, evidence-bound, multi-SKU, or handoff-heavy tasks. They are not few-shot examples and not fixed report formats. Use the ideas, fields, or table shapes only when they make the answer clearer.

## Unified Trade Field Table

| Field | Current value | Status | Why it matters | Next action |
|---|---|---|---|---|
| Product / use |  | Provided / Missing | Eligibility, HS, category |  |
| Material / ingredients |  | Provided / Missing | Certification, HS, dangerous goods |  |
| Platform / target country |  | Provided / Missing | Policy, tax, import rules |  |
| Origin / ship-from |  | Provided / Missing | Tariff, COO, logistics |  |
| Seller entity / warehouse |  | Provided / Missing | Tax, Nexus, fulfillment |  |
| Value / weight / dimensions |  | Provided / Missing | Landed cost, warehouse, carrier |  |
| Brand / IP elements |  | Provided / Missing | Trademark, authorization |  |

## Official Source Table

| Topic | Source path | Fields to verify | Access caveat | Status |
|---|---|---|---|---|
| Platform restriction | Seller Center / policy page | Prohibited/restricted, approval docs | May require login |  |
| HS/tariff | Customs/tariff database | Candidate code, notes, rate | Broker confirmation needed |  |
| Tax | Tax authority/platform report | Nexus/VAT/marketplace facilitator | Advisor confirmation needed |  |
| IP | Trademark/patent database | Live mark, owner, goods/services | Not legal clearance |  |

## Risk Table

| SKU / batch | Risk | Type | Evidence status and source | Level | Closing evidence | Action owner |
|---|---|---|---|---|---|---|
|  |  | Compliance / tax / IP / customs / logistics |  | P0/P1/P2/P3 |  | Seller / broker / advisor / attorney / lab |

## Customs / Fulfillment Table

| Option | Required fields | Candidate result | Risk | Verification |
|---|---|---|---|---|
| HS/tariff | Origin, destination, product specs |  | Classification uncertainty | Official schedule/broker |
| DDP/DDU | Value, HS, carrier, destination |  | Customer surprise/cost risk | Carrier/platform |
| FBA/warehouse | Size, hazmat, capacity, sales velocity |  | Storage/approval risk | Seller Center |

## Prioritized Actions

1. Resolve P0/P1 product eligibility, restricted product, IP, tax, or dangerous goods risks.
2. Complete missing product and trade fields.
3. Verify HS/tariff/customs with official source or broker.
4. Choose fulfillment route and collect carrier/warehouse quotes.
5. Hand off to listing, ads, content, or product research after risk boundaries are clear.

## Cross-File Reconciliation Table

| Control | Detail result | Independent result | Difference | Source locations | Status |
|---|---:|---:|---:|---|---|
| SKU count |  |  |  | SKU master / invoice / packing list | PASS / FAIL / UNRESOLVED |
| Total units |  |  |  |  |  |
| Total merchandise value |  |  |  |  |  |
| Origin counts |  |  |  |  |  |
| Invoice amount |  |  |  |  |  |
| Packing-list weight |  |  |  |  |  |
| Batch costs |  |  |  |  |  |
| Taxes and landed cost |  |  |  |  |  |

## Cross-Deliverable Consistency Table

| Field / status | Narrative | Excel | CSV | Word | Status |
|---|---|---|---|---|---|
| Core totals |  |  |  |  | PASS / FAIL |
| SKU evidence status |  |  |  |  |  |
| Batch release decision |  |  |  |  |  |
| Owner and deadline |  |  |  |  |  |
