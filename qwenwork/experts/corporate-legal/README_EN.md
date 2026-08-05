# Corporate Legal

<!-- [optimization:scenario] Rewritten plugin description to clarify AI value-add and target use cases -->
A comprehensive corporate legal assistant that helps in-house counsel work efficiently on day-to-day legal matters. Covers six high-frequency scenarios: legal document drafting, corporate resolution generation, similar case search and outcome prediction, compliance review, company background checks, and legal risk assessment. Built on the framework of the 2024 PRC Company Law (公司法) and the PRC Civil Code (民法典).

> **Disclaimer:** This plugin supports professional legal workflows and does not replace legal advice. All outputs should be reviewed by a licensed attorney before being used for decision-making.

## Capability Overview

<!-- [optimization:MCP] Added ALWAYS/SUPERCHARGED capability tier diagram -->
```
+----------------------------------------------------------+
|  ALWAYS (Standalone)                                      |
|  * Legal document drafting (demand letters / complaints / |
|    defense statements / legal opinions)                   |
|  * Corporate resolutions and articles of association      |
|    amendments                                             |
|  * Similar case analysis and outcome prediction           |
|  * Compliance review (privacy / advertising / licensing / |
|    data security)                                         |
|  * Legal risk matrix assessment                           |
|  * Company background check and analysis                  |
+----------------------------------------------------------+
```

## Target Users

- **In-House Counsel** -- Day-to-day legal document drafting, compliance review, and case research
- **General Counsel** -- Comprehensive legal affairs management, risk assessment, and decision support
- **Compliance Manager** -- Business compliance review and regulatory policy tracking
- **CEO / Managing Director** -- Counterparty due diligence and major-matter risk assessment

## Skills

<!-- [optimization:knowledge] Added detailed feature descriptions for each Skill -->

| Skill | Description |
|-------|-------------|
| Legal Documents | Enter facts and claims to auto-select the document type (demand letter / complaint / defense statement / agency brief / legal opinion) and generate a standards-compliant first draft |
| Corporate Resolution | Enter the resolution matter to auto-determine the resolution type and voting threshold, then generate a shareholders' or board resolution with supporting articles of association amendments |
| Case Lookup | Enter a case description to match similar rulings, predict likely outcomes, and receive litigation strategy recommendations |
| Risk Assessment | Enter a business matter to build a legal risk matrix (likelihood x severity x controllability) and receive a tiered response plan |
| Compliance Review | Enter a business matter for review across privacy, advertising, licensing, data security, and other compliance domains, with a remediation checklist as output |
| Company Background Check | Enter a company name for a comprehensive analysis of registration data, equity structure, litigation history, and operational risk, with a quantified risk rating report |

## Quick Commands

| Command | Purpose |
|---------|---------|
| `/legal-documents` | Draft a legal document |
| `/corporate-resolution` | Generate a corporate resolution |
| `/case-lookup` | Search and analyze similar cases |
| `/risk-assessment` | Perform a legal risk assessment |
| `/compliance-review` | Run a compliance review |
| `/company-background-check` | Conduct a company background check |

## MCP Enhancement

This plugin works fully standalone without any MCP connectors.
