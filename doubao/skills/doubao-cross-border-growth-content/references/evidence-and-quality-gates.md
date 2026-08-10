# Evidence And Quality Gates

Use this file for every task. Keep the artifacts short enough to follow mechanically.

## 1. Required Deliverables

Before answering, list every explicit user request.

| id | requested deliverable | status |
|---|---|---|
| D1 |  | pending / complete |

For multi-part tasks, do not spend the response budget on optional background before all `D` items are covered.

## 2. Evidence Ledger

Use only three states.

| fact_id | field or claim | value | state | source |
|---|---|---|---|---|
| F1 |  |  | confirmed / assumption / missing | user / attachment / visible evidence / authoritative document |

Rules:

- Final scripts, captions, image text, product briefs, and creator `must say` fields may use only `confirmed`.
- `assumption` may support a hypothesis or test design, but not a factual product statement.
- `missing` remains `null`, `[待确认]`, or outside final copy.
- Previous-turn model output is not evidence.
- Category knowledge is not product evidence.
- A public listing can support visible listing facts, but not backend status, certifications, rights, or true included accessories unless independently confirmed.

## 3. Claim Ledger

For claim-sensitive outputs, map each final claim before delivery.

| claim_id | final wording | supporting fact_id | allowed |
|---|---|---|---|
| C1 |  | F1 | yes / no |

Delete or rewrite every row with `allowed=no`.

Always scan for:

- numbers and time claims;
- materials, blade count, capacity, charging time, battery life;
- cleaning, waterproofing, safety, compatibility, food or ingredient capability;
- included cable, manual, spare parts, gifts, discounts;
- reviews, sales, awards, certifications and platform approval;
- health, weight-loss, nutrition and performance results;
- shipping, returns, warranties and local price.

Do not soften an unsupported claim with “usually”, “generally”, “category standard”, or “if true” and then leave it inside final marketing copy.

## 4. Rights And Platform State

| field | status | evidence or next verification |
|---|---|---|
| paid media permission | confirmed / missing |  |
| platform and territory | confirmed / missing |  |
| duration and takedown | confirmed / missing |  |
| edit and derivative rights | confirmed / missing |  |
| music and third-party IP | confirmed / missing |  |
| technical authorization route | confirmed / missing |  |
| platform review or eligibility | confirmed / missing |  |

Do not call an asset `ready`, `approved`, `compliant`, or `Spark-ready` while any material row is missing.

## 5. Localization Status

Use exactly one label per language:

- `machine_draft`: generated but not independently checked;
- `bilingual_meaning_checked`: meaning checked across both languages;
- `native_reviewed`: reviewed by a named native reviewer or explicitly confirmed by the user.

Do not use “natural”, “native”, “ready to publish”, or equivalent unless the evidence supports it.

## 6. Final Binary Gate

Mark each applicable item `PASS` or revise:

1. All `D` rows are complete.
2. Every final claim has an allowed `C` row.
3. Unknown product fields stayed out of final copy.
4. Platform procedures have an official source context or are marked for verification.
5. Rights and localization status are stated honestly.
6. Performance formulas and actions pass `performance-safety.md`.
7. No file, chart, asset, approval, or review is claimed unless verified.

If a material gate cannot pass, provide the safe partial deliverable and the smallest missing-information list.
