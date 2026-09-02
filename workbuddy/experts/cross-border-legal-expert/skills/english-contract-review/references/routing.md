# Contract Task Routing

| User intent | Route |
|---|---|
| Review, risk, fairness, enforceability, unfavorable terms | `english-contract-review` |
| Modify an existing contract without requesting a new output | `english-contract-review` |
| Draft a new contract, new version, rewrite, or fresh agreement | `english-contract-drafting` |
| Extract or quote existing clauses without evaluation | extraction tool |
| Compare two versions | comparison tool |
| Translate only | translation tool |
| Summarize only | summarization tool |
| Convert PDF or DOCX format only | document conversion tool |

Tie-breakers:

1. Version comparison overrides review.
2. Evaluation words such as risk, unfair, reasonable, enforceable, or compliant override extraction words.
3. New-output signals such as a new agreement, new version, rewrite, or fresh draft override review.

Ask at most once, and only when:

1. A file is provided without any task.
2. The request has no usable objective.
3. Two mutually incompatible deliverables are requested and their sequence
   cannot be inferred safely.

## Deliverable Decision Route

1. If the user specifies `revisions_only`, `comments_only`, or `both`, use it.
2. If no mode is specified, default to `both`. When another consolidated
   question is already necessary, include the three Redline choices in it.
3. Initial review produces Report, Redline, and decision state only.
4. After Redline delivery, collect decisions by `issue_id`. Treat an
   unqualified `没问题`, `可以，出 Clean`, or equivalent approval as accepting
   all proposed text changes.
5. Keep Clean blocked while any high/medium issue or proposed text edit is
   pending. A retained original risk requires a written acceptance note.
6. Custom wording creates a revised Redline and returns to confirmation.
7. Bilingual generation is available only after confirmed Clean generation.

Full-review indicators include `能不能签`, `是否有利`, `不利条款`, `合规`,
`风险`, and a request to modify the existing document. Clause-only indicators
name or quote a specific clause and request an evaluation.

## Contract Family Routing

Classify by operative obligations and
economic substance rather than the document title.

1. Select exactly one primary family.
2. For a mixed agreement, add no more than three secondary families.
3. Always load the 12 universal rules.
4. Load the six cards for each selected family.
5. Load `jurisdiction-overlays.md` only when the governing law,
   performance location, party location, data flow, asset, or regulated
   activity makes them relevant.
6. If confidence is low, ask once and present the two or three most likely
   families with the fact that would distinguish them.

| Family ID | Primary economic substance |
|---|---|
| `nda` | Controlled disclosure and use of confidential information |
| `professional_services` | Human-led consulting or professional deliverables |
| `saas_cloud` | Recurring hosted software or cloud access |
| `data_processing` | Processing or sharing personal or regulated data |
| `license_ip` | Permission to use identified software or IP assets |
| `technology_development` | Creation of software or technical deliverables |
| `procurement_goods` | Purchase and sale of goods |
| `manufacturing_oem` | Production, tooling, quality systems, OEM or ODM |
| `logistics_transport` | Transport, freight forwarding, custody, or warehousing |
| `distribution_reseller` | Resale, territory, channels, and distribution |
| `partnership_joint_venture` | Shared contributions, governance, and collaboration |
| `workforce` | Employment, executive, contractor, or freelancer relationship |
| `commercial_lease` | Commercial use and occupation of real property |
| `finance_security` | Debt, credit, guarantee, collateral, or security |
| `investment_ma` | Equity, conversion, shareholder rights, or acquisition |
| `construction_engineering` | Construction, engineering, design-build, or EPC |
| `marketing_advertising` | Advertising, campaign, influencer, or sponsorship work |
| `platform_marketplace` | Multi-user platform, marketplace, or terms of service |
| `settlement_release` | Resolution, release, waiver, or dismissal of claims |
| `government_public` | Public procurement, government flow-downs, or teaming |

Common mixed routes:

- SaaS agreement with a DPA: primary `saas_cloud`, secondary `data_processing`.
- Custom hosted implementation: primary `technology_development`, secondary
  `saas_cloud` and `data_processing`.
- OEM supply with customer tooling: primary `manufacturing_oem`, secondary
  `procurement_goods` and `license_ip`.
- Convertible financing: primary `investment_ma`, secondary
  `finance_security`.
- Government software subcontract: primary `government_public`, secondary
  `technology_development`, `saas_cloud`, or `data_processing` as applicable.
