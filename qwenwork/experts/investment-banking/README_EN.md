# Investment Banking

AI-powered investment banking assistant covering six core workflows: IPO prospectus drafting, M&A advisory reports, bond offering memoranda, regulatory response to exchange inquiries, roadshow materials, and financial modeling.

> **Disclaimer:** This plugin assists professional workflows and does not replace professional judgment. All outputs should be reviewed by qualified professionals before being used in decision-making.

## Target Users

- **IB Deal Manager** -- End-to-end execution and coordination of IPO / M&A / bond deals
- **Sponsor Representative** -- Registration-based review material oversight and disclosure quality control
- **IB Analyst** -- Working paper preparation, financial modeling, and data analysis
- **Bond Underwriter** -- Offering memorandum drafting and roadshow preparation

## Typical Workflow

```
Financial Modeling --> Prospectus / Bond Offering / M&A Advisory --> Regulatory Response --> Roadshow Materials
  (valuation basis)      (filing documents)                        (review feedback)       (marketing)
```

## Skills

| Skill | Description | Typical Input |
|-------|-------------|---------------|
| prospectus | Generate IPO prospectus chapter drafts per registration-based disclosure rules; adapts to STAR Market / ChiNext / Main Board / BSE | Enter company info, e.g.: XX Tech plans IPO on NASDAQ, core business: chip design |
| ma-advisory | Generate M&A restructuring report drafts per the Major Asset Restructuring Rules; includes pricing analysis and earnout design | Describe the deal, e.g.: Company A to acquire 100% of Company B via share issuance |
| bond-offering | Generate offering memorandum drafts per exchange / interbank market rules; includes debt-service capacity analysis | Enter issuer and instrument, e.g.: XX Group plans to issue $150M 3-year corporate bonds |
| regulatory-response | Respond to exchange inquiry letters item-by-item: factual statement + reasonableness analysis + peer comparison + verification opinion | Upload an exchange inquiry letter, e.g.: SEC first-round comment letter.pdf |
| roadshow-materials | Generate IPO / bond / M&A / follow-on roadshow slide outlines, page-by-page scripts, and Q&A playbooks | Enter deal info, e.g.: XX Pharma IPO roadshow, institutional investors, 40 minutes |
| financial-modeling | Build a CAS three-statement linked forecast model with DCF valuation, comps analysis, and sensitivity testing | Upload financial data or enter company name, e.g.: XX Tech past 3 years financials |

## Quick Commands

| Command | Description |
|---------|-------------|
| `/prospectus` | Provide company info and target board to generate prospectus chapter drafts |
| `/ma-advisory` | Provide deal background and target info to generate an M&A restructuring report draft |
| `/bond-offering` | Provide issuer info and bond type to generate an offering memorandum draft |
| `/regulatory-response` | Upload an inquiry letter to generate item-by-item responses in regulatory format |
| `/roadshow-materials` | Provide deal info and roadshow type to generate a slide outline and script |
| `/financial-modeling` | Upload financials or enter a company name to build a three-statement + DCF model |

## MCP Enhancement

This plugin works standalone and does not require any MCP connectors.
