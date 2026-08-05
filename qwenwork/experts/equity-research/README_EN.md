# Equity Research

End-to-end equity research toolkit for sell-side and buy-side analysts, covering deep-dive reports, industry research, annual report analysis, earnings reviews, field research notes, morning briefings, and research digests.

> **Disclaimer:** This plugin assists professional workflows and does not replace professional judgment. All outputs should be reviewed by qualified professionals before being used in decision-making.

## Capability Tiers

```
+------------------------------------------------------+
|  Core Capabilities (standalone)                       |
|  - Structured extraction and analysis of annual       |
|    reports, filings, and field research notes          |
|  - Sell-side-style deep-dive and industry report      |
|    frameworks                                         |
|  - Standardized outputs for earnings reviews,         |
|    research digests, and morning briefings             |
+------------------------------------------------------+
```

## Target Users

- **Sector Analyst** -- Primary tool for deep-dive reports and industry research
- **Portfolio Manager** -- Information-processing assistant for investment decisions
- **Head of Research** -- Morning briefing and research management
- **PE/VC Analyst** -- Field research notes and industry tracking

## Skill Workflow

```
Field Research Notes --> Deep-Dive Report --> Earnings Review (ongoing tracking)
  ^                           ^                     |
Annual Report Reader --> Industry Research    Research Digest (cross-check peers)
                                                    |
                                              Morning Briefing (consolidated output)
```

## Quick Commands

| Command | Description | Typical Input |
|---------|-------------|---------------|
| `/deep-dive-report` | Company deep-dive research report (initiation / update) | Enter a company name and upload materials, e.g.: BYD, with latest annual report and field notes |
| `/industry-research` | Industry landscape research report | Enter an industry name, e.g.: Solar value chain or Humanoid robotics |
| `/annual-report-reader` | China A-share annual report quick read and investment memo | Upload an annual report PDF, e.g.: Tesla 2024 annual report |
| `/earnings-review` | Rapid earnings release commentary | Upload an earnings release PDF, e.g.: CATL 2024Q3 preliminary results |
| `/field-research-notes` | Standardized field research notes | Upload field notes or call transcript, e.g.: Company X site visit notes |
| `/morning-briefing` | Morning briefing preparation | Enter coverage sector and materials, e.g.: New energy sector, with yesterday closing data |
| `/research-digest` | Extract and compare core views from research reports | Upload 1-10 research report PDFs, e.g.: 3 deep-dive reports on CATL |
| `/comparable-analysis` | Comparable company valuation analysis | Enter a target company name, e.g.: CATL, lithium battery sector comps |

## MCP Enhancement

This plugin works standalone and does not require any MCP connectors.
