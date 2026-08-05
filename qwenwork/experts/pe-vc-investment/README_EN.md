# Private Equity

End-to-end PE/VC toolkit covering deal screening, due diligence checklists, term sheet review, investment committee memos, return modeling, and exit analysis.

> **Disclaimer:** This plugin supports professional workflows and does not replace professional advice. All outputs should be reviewed by qualified professionals before being used for decision-making.

## Target Users

- **Investment Managers** -- Core tool for deal screening and due diligence
- **Managing Directors** -- IC material preparation and risk oversight
- **Partners** -- Rapid evaluation of investment opportunities
- **Portfolio Management** -- Exit analysis and return tracking

## Quick Commands

| Command | Description | Typical Input |
|---------|-------------|---------------|
| `/deal-screening` | Rapid BP/CIM screening with a one-page six-dimension scoring memo | Upload a BP, e.g.: Screen this SaaS project BP |
| `/due-diligence-checklist` | Generate a structured DD checklist (financial / legal / commercial / technical + sector-specific) | Describe the project, e.g.: EdTech SaaS, Series B, Delaware C-Corp |
| `/term-sheet-review` | Clause-by-clause TS/SPA review with PRC compliance checks and negotiation guidance | Upload a Term Sheet or SPA, e.g.: Review this Series B Term Sheet |
| `/investment-memo` | Generate an IC Memo with investment thesis, valuation analysis, and term summary | Enter project details, e.g.: Compile IC materials for XX project, DD report attached |
| `/return-modeling` | IRR / MOIC / DPI modeling with a 25-cell sensitivity table | Describe the deal, e.g.: Invest $5M at $30M pre, expect 10x PS exit in 5 years |
| `/exit-analysis` | Compare five exit pathways (IPO / M&A / secondary / buyback) with time and cost estimates | Describe the portfolio company, e.g.: Company A, invested 2022, SaaS, fund expires 2027 |

## Typical Workflow

```
Source deal -> /deal-screening (quick filter) -> /due-diligence-checklist (launch DD) -> /term-sheet-review (review deal docs)
                                                                                              |
                      /exit-analysis (post-investment) <- /return-modeling (model returns) <- /investment-memo (go to IC)
```

## Connectors (Optional Enhancement)

This plugin works independently and requires no MCP connectors. All features operate on text and files without external dependencies.
