# Site Selection Advisor

A role-level AI toolkit for **store site selection**. Built on Amap's five-dimension site model, it breaks the full journey — from "no idea where to open" to "site confirmed with an investment proposal" — into four independently triggerable skills.

---

## Who it is for

- **Chain-brand expansion / development managers** screening, scoring and documenting candidate sites at scale
- **Regional franchisees and independent founders** holding 1–3 candidate units, deciding whether to sign
- **Investment decision-makers** who need a data-backed proposal as the basis for approval

Typical persona: "An expansion manager in a 3–20 person team at a chain tea-drink brand, visiting 5–10 candidate units per week and submitting 2–5 site proposals per month to the decision committee."

---

## The five dimensions

| Dimension | What it measures |
|-----------|------------------|
| **Footfall aggregation** | Size and activity of the consumer population nearby — is the traffic base sufficient |
| **Prospect match** | Fit between the local population and the target category — are these your customers |
| **Peer competition** | Density of same-category supply and competitive pressure — is the market saturated |
| **Accessibility** | Ease of arrival and transit conditions — can customers get there easily |
| **Commercial maturity** | Commercial atmosphere, category richness and spending capacity — is the environment mature |

---

## Skills included

| Skill | When to use | Input | Output |
|-------|-------------|-------|--------|
| **Trade-area recommendation** | No candidate site yet, only a city/district | District + category | Scored and ranked trade-area shortlist with feature tags, drillable to five-dimension detail |
| **Site evaluation** | One specific location to health-check | Location + category + radius | Overall score, star rating, peer percentile, five-dimension interpretation and advice |
| **Multi-site comparison** | 2+ candidate units to choose between | Multiple locations + category | Like-for-like comparison table, revenue comparison, payback estimate, SWOT, primary recommendation |
| **Feasibility report** | Formal material for management or investors | Existing evaluation data | Eight-chapter proposal (overview / assessment / market / plan / budget / P&L / risk / conclusion) |

### Typical workflow

```
Trade-area rec. ──► Site evaluation ──┬──► Feasibility report
(narrow the area)  (single-site check)│
                                      │
             Multi-site comparison ───┘
             (head-to-head choice)
```

All four skills can be triggered **independently**. The only hard dependency: the feasibility report requires evaluation data produced by site evaluation or multi-site comparison.

---

## Systems it connects to

This kit relies on the **Amap store-intelligence site-selection gateway** for assessment data, authenticated via OAuth. On first use the browser is opened automatically to complete login; the credential is stored locally as a session token. Users never need to enter any API key manually.

⚠️ This data source is **not yet published as a standard wukong Connector (MCP Server)** — the skills currently call the gateway directly. See [CONNECTORS.md](./CONNECTORS.md) for the gap and the planned migration.

---

## Degradation when not connected

| Situation | Behaviour |
|-----------|-----------|
| OAuth not completed | States clearly that site data cannot be retrieved without authorisation; optionally continues with qualitative advice only, explicitly flagged as unsupported by data |
| Gateway unreachable | States that the site-data service is temporarily unavailable, reports how far it got, suggests retrying later |
| POI not found | Asks for a more precise store name, mall name or full address instead of guessing a nearby POI |
| A dimension returns no data | Interprets only the returned dimensions; missing ones are labelled "no data returned this run" |
| Quota exhausted | Prompts for top-up; identical queries are idempotent by parameter MD5 and are not double-charged |

**Core principle**: under no circumstances are five-dimension scores or prospect volumes fabricated from general knowledge. If the data is unavailable, it says so.

---

## Data semantics you should know

- **Score and star rating are two different systems**: score measures *closeness to the model of high-quality sites in the category*; star rating measures *the relative rank of that metric's volume within the city*. A mismatch between them is normal and neither may be inferred from the other.
- **The overall score is not a sum or average of dimension scores** — it is computed against the high-quality-site model.
- **In revenue and payback estimates**, prospect volume is measured data while conversion rate, average ticket and costs are industry assumptions — outputs always distinguish the two.
- Assessment data is indicative. Use it to set direction, then combine with on-site inspection and property terms.

---

## Ownership and terms

This kit and all content obtained through Amap service APIs belong to Amap, which reserves all rights. See the Amap Cloud Map SKILL Ownership and Use Statement (https://terms.amap.com/legal-agreement/terms/b_end_product_protocol/20260415144415692/20260415144415692.html). Using this kit constitutes acceptance of that statement.
