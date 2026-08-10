# Cross-File Reconciliation And Delivery Gates

Read this file for any task involving multiple attachments, spreadsheets, invoices, packing lists, SKU masters, tax tables, logistics quotations, numerical models, generated Excel/CSV/Word files, or multi-round updates.

## 1. Source Inventory And Hierarchy

Create an inventory with `source_id`, file name, sheet/section, version/date, role, authority status, and superseded-by relationship.

Default hierarchy:

1. Explicit task controls and formulas.
2. Latest formal document effective at the task's review cutoff.
3. Signed/stamped or system-exported evidence.
4. Earlier formal versions retained as history.
5. Chat, old drafts, supplier statements and quotations as clues unless explicitly confirmed.

Never silently choose between conflicting sources. Record the conflict and the closing action.

## 2. Normalized SKU Evidence Ledger

Use one row per `SKU × evidence item`.

| SKU | Item/model | Evidence type | Status | Exact coverage | Source/location | Version/date | Affected batch | Closing evidence |
|---|---|---|---|---|---|---|---|---|

Allowed status values: `Verified`, `Missing`, `Mismatch`, `Pending`, `Superseded`, `Not applicable`.

Rules:

- Treat each SKU and model independently.
- Do not copy status across similar products.
- A document closes only the item, model, manufacturer/factory, version and scope it explicitly covers.
- `Under review` is not approval.
- UN38.3 evidence does not automatically close SDS/MSDS or battery-declaration evidence.
- Keep old evidence as `Superseded`; do not delete it in multi-round tasks.

Example: if D-SMART lacks UN38.3 and a battery declaration while A-TA5 has complete battery documents but lacks brand authorization, preserve those distinct statuses. Do not label both electronic-airbag products identically.

## 3. Mandatory Cross-File Reconciliation

At minimum reconcile:

| Control | Detail source | Independent comparison |
|---|---|---|
| Unique SKU count | SKU master/detail rows | Invoice and packing-list SKU sets |
| Total units | Sum of SKU quantities | Invoice, packing list and batch totals |
| Total merchandise value | Sum of quantity × unit price | Commercial Invoice total |
| Country-of-origin counts | Per-SKU origin field | Invoice/COO/specification evidence |
| Invoice amount | Invoice lines | Calculation ledger and declared value |
| Packing-list weight | Carton/SKU weight detail | Shipment/batch totals; distinguish measured from estimated |
| Batch costs | Quote and allocation detail | Sum of batch costs and project total |
| Duty and import taxes | Per-SKU tax calculation | Tax summary |
| Total landed cost | Merchandise + allocated freight/insurance + tax + domestic charges | Batch totals and project total |
| Sales and gross margin | Per-SKU sales value and landed cost | Project summary |

Mark each control `PASS`, `FAIL`, or `UNRESOLVED`, with difference and source locations.

## 4. Calculation Ledger

For each derived value, retain:

- formula;
- input values and units;
- input source;
- allocation basis;
- rounding rule;
- result;
- reconciliation status.

Do not mix currencies or units implicitly. Allocation bases must follow the task: for example, value, weight, or volume. The sum of allocated amounts must equal the source total within the declared rounding tolerance.

Missing independent measurements remain `待独立复称` or equivalent. Do not proportionally split a batch weight or invent a date, rate, fee, certification cycle, or route unless the user explicitly requests a labeled assumption scenario.

## 5. Task-Specific Control Totals

When the prompt, source files, or evaluation instructions provide control totals, treat them as task-specific reconciliation anchors. Do not hard-code controls from prior cases into new tasks.

Possible controls include:

- unique SKU count;
- total units;
- country-of-origin counts;
- total merchandise value;
- invoice amount;
- packing-list weight or carton count;
- batch freight/warehouse/logistics cost;
- duty, import VAT/GST, sales tax or other tax totals;
- total landed cost;
- sales value, gross margin, contribution margin, or budget variance.

For every control, recompute the value from authoritative detail and compare it with the independent source. If a task-specific control differs from the recalculated detail, stop. Locate and fix the source, formula, allocation, unit, currency, rounding, or status error before producing a final answer.

## 6. Cross-Deliverable Consistency

Build the narrative response, Excel, CSV and Word report from the same normalized facts and calculation ledger.

Before delivery verify:

- every core total is identical across all deliverables;
- SKU and batch status, risk level, owner and deadline are identical;
- units, currency, decimals and rounding are consistent;
- table headers match row widths and field order;
- derived Excel values use formulas where practical and totals reference detail;
- CSV encoding, columns and row counts are valid;
- the Word executive summary matches the workbook and CSV totals;
- old/superseded states do not appear as current;
- no AI watermark, AIGC label, local absolute path, debugging log, script error, or repair trace remains in the user-facing files.

## 7. Hard Stop Gate

Do not issue the final answer, final release decision, or delivery claim if any of these is true:

- a core control is `FAIL` or `UNRESOLVED`;
- detail and summary totals disagree;
- origin and ship-from were conflated;
- a SKU status was generalized without coverage evidence;
- narrative, Excel, CSV and Word disagree;
- a generated table has schema/column misalignment;
- a required output file was not opened and checked after generation.

When blocked, report the failed control and required correction instead of presenting an apparently complete result.
