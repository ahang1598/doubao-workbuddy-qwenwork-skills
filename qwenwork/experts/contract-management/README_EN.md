# Contract Management

A full-lifecycle contract management assistant: helps you review contract risks, draft contract first drafts, compare contract version differences, rapidly triage NDAs, look up legal provisions, and manage contract expiry reminders. Built on the Civil Code of the PRC (Contract Book) and related judicial interpretations, covering common enterprise contract scenarios.

> **Disclaimer:** This plugin assists professional workflows and does not replace legal advice. All outputs should be reviewed by a licensed attorney before being used for decision-making.

## Capability Overview

```
+-----------------------------------------------------------+
|  Core Capabilities (works independently)                   |
|  * Contract risk review (red/yellow/green grading)         |
|  * Contract first draft generation (Word output)           |
|  * Redline comparison of two contract versions             |
|  * Rapid NDA triage (sign / revise / negotiate)            |
|  * Legal provision lookup with practical interpretation    |
|  * Contract expiry reminders and ledger management         |
+-----------------------------------------------------------+
|  Enhanced Capabilities (with connectors)                   |
|  + Notion -> Publish contracts and reports to Notion       |
|    for collaborative review                                |
+-----------------------------------------------------------+
```

## Target Users

- **In-house Counsel** -- Core tool for day-to-day contract review and management
- **General Counsel** -- Quickly assess contract risks and set negotiation strategy
- **Procurement Managers** -- Supplier contract review and negotiation preparation
- **Founders / CEOs** -- First line of defense for contract review when there is no in-house legal team

## Skills

| Skill | Description |
|-------|-------------|
| Contract Review | Upload a contract, review each clause for risks with red/yellow/green grading, and output revision suggestions with a three-tier negotiation strategy |
| Contract Drafting | Describe the deal context to generate a professionally drafted contract in Word format, with key clauses annotated with legal authority |
| Contract Comparison | Upload two contract versions for clause-level semantic comparison, with impact grading, linkage analysis, and negotiation recommendations |
| NDA Screening | Upload an NDA for rapid screening of eight key clauses, delivering a sign / revise / negotiate triage verdict in 30 seconds |
| Legal Lookup | Enter a business question or keyword to retrieve matching legal provisions, judicial interpretations, and key points from landmark cases |
| Contract Tracker | Enter contract date information to automatically generate expiry reminders, renewal alerts, and performance milestone tracking |

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/contract-review` | Review contract risks |
| `/contract-drafting` | Draft a contract first draft |
| `/contract-comparison` | Compare contract versions |
| `/nda-screening` | Rapid NDA triage |
| `/legal-lookup` | Legal provision lookup |
| `/contract-tracker` | Contract ledger management |

## MCP Enhancements

This plugin works fully independently without any MCP. Connecting the following MCP unlocks real-time data enhancements:

| Category | Configured Service | Enhanced Capability |
|----------|-------------------|---------------------|
| Document Collaboration | Notion | Publish contracts and reports to Notion for collaborative review |
