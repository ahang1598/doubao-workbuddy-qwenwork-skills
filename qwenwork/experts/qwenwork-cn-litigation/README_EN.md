# Chinese Civil & Commercial Litigation Toolkit

> Qoder for CN Litigation — A full-lifecycle litigation toolkit for practicing attorneys and in-house counsel

## Overview

This plugin provides comprehensive workflow support for Chinese civil and commercial litigation, from case analysis to document generation, covering both plaintiff and defendant perspectives. Based on the claim-basis method (Anspruchsgrundlage) and court-report technique (Relationstechnik), it transforms legal methodology into practical, actionable tools.

**Target Users**: Practicing attorneys, in-house legal counsel

**Total Skills**: 20

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Configuration & Routing Layer (3)                │
│  Litigation Hub ─── Onboarding Interview ─── Quick Config    │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────────┐
│ Analytical     │  │ Document        │  │ Case Management  │
│ Work (6)       │  │ Drafting (7)    │  │ (3)              │
│               │  │                │  │                  │
│· Visualization │  │· Complaint      │  │· Case Manager    │
│· Fact Analysis │  │· Defense Brief  │  │· Case Review     │
│· Element A/D   │  │· Evidence Cat.  │  │· Knowledge Base  │
│· Property Inv. │  │· Cross-Exam     │  │                  │
│· Legal Research│  │· Trial Outline  │  │ COLLAB.*+qmind   │
│· New Law Interp│  │· Closing Arg.   │  │ In-conversation  │
│               │  │· Procedural Docs│  │ fallback         │
└───────────────┘  └───────┬────────┘  └────────┬─────────┘
                           │ Must pass before     │ Review report must
                           │ output               │ pass before output
                           ▼                      ▼
                  ┌──────────────────────────────────┐
                  │     Output Gate · Quality Fence (1)    │
                  │     · Legal Verification (LAW.*)       │
                  └──────────────────────────────────┘
```

> **Legal Verification** guards the "exit" (verifies all legal citations line-by-line before any formal document is delivered). Uploaded files are automatically parsed into Markdown before entering analysis workflows (no separate trigger needed).

---

## Workflow Connections

```
Document Parsing ── Upload files (PDF/images/Word/PPT) auto-parsed to Markdown before analysis/drafting (user-configurable parsing backend, built-in pypdf/Read fallback)

Fact Analysis ──produces──→ Main fact document (md) ⇒ links: Relationship Chart (HTML) + Timeline (HTML) + embedded chronicle
     │
     ↓
Element Attack/Defense Analysis ──depends on──→ Fact Analysis
     │
     ↓
┌────┼────┬────────┐
│    │    │        │
Complaint  Defense Brief  Evidence Catalog  Cross-Examination

└────┬────┘
     ↓
  Trial Outline (with examination question list)
     │
     ↓ (pre/post-trial)
Closing Argument (pre-trial brief + post-trial supplemental brief, covers first/second/retrial)

Procedural Documents ── Eight-family router (preservation/evidence/party & claim changes/trial procedure/enforcement/filing/other/jurisdiction objection), includes jurisdiction objection
Property Investigation ── Independent (can connect to Procedural Documents' preservation/online asset control)
Legal Research Report ── Independent (research conclusions can feed into Element A/D / Complaint / Defense Brief)
New Law Interpretation ── Independent (old-vs-new comparison-driven firm-level regulatory interpretation, can connect to Legal Research Report / Element A/D)

Legal Verification ── Quality fence: any skill that produces formal documents must pass Legal Verification for line-by-line statute/article/case citation verification before delivering md output (and subsequent Word conversion); only passes after all citations verified accurate

— Case Management Section (spans entire case lifecycle, attorney/counsel dual-mode, COLLAB.* platform + qmind) —
Case Manager ──intake (attorney: conflict-check gate / counsel: external-counsel evaluation)──→ Deadline computation (compute initial deadlines · create four-tier todo · optional scheduled reminders)
                 │
Receive judgment/close ──→ Case Review (trial review / judgment analysis / closing review)──→ Case Manager (close + archive)
                                                              │
                                                              ↓
Litigation Knowledge Base ──deposit──→ Legal Research Report / New Law Interpretation / Case Review outputs deposited into qmind/DingTalk Docs (retrievable for future cases)
```

---

## Installation

Place this directory in a location accessible by QoderWork, then install the plugin in QoderWork:

```
Settings → Plugin Management → Install Local Plugin → Select this directory
```

Or copy the directory to `~/.qoderwork/plugins-custom/qwenwork-cn-litigation/`.

---

## First Use

After installation, it's recommended to run `/onboarding-interview` to complete your practice profile configuration. The suite will personalize all subsequent skills based on your role (counsel/attorney), stance preference (plaintiff/defendant), risk calibration, and other settings.

If you skip the onboarding, all skills still function normally, but without personalized recommendations.

---

## MCP Dependencies (Optional Enhancement · Platform-Agnostic · Multi-Vendor Failover)

All MCP dependencies in this plugin are **optional** — you can produce complete drafts without connecting any MCP. The four backend categories (legal research / business information / document parsing / collaboration platform) are all **platform-agnostic**: each skill invokes only by capability slot (`LAW.*`/`BIZ.*`/`PARSE.*`/`COLLAB.*`), probes connected MCPs at runtime via `qw_mcp_list`, and **auto-failovers** when multiple vendors of the same type are configured. See `qoder.md` "External Capability Backends" and `connectors.md` for capability-to-vendor mappings. Enhanced capabilities after connection:

| Capability Backend | Capability Slot | Available Vendors (Swappable/Failover) | Fallback When Missing |
|---------|---------|---------|---------|
| Legal Research | `LAW.*` (statute/regulation/case search · detail · semantic · citation verification) | Yuandian / PKULaw (use one or both for failover) | Annotate `[L4-Statute-Unverified]` |
| Business Information | `BIZ.*` (entity verification · equity · investment · risk · IPR · associations) | Qichacha / Tianyancha / Qixin etc. (auto-adapts by actual function) | WebSearch fallback, annotate `[L4-Entity-Info-Unverified]` |
| Visualization | — | None (built-in HTML/SVG output, zero external dependencies) | — |
| Web Search (SEARCH.*) | `SEARCH.web_search` / `SEARCH.ai_search` | Runtime detection (GoogleWebSearch / IflowWebSearch / IflowAiSearch / Tavily etc.) | WebFetch fallback |
| Document Parsing | `PARSE.to_markdown` | User-selected backend (MinerU / Alibaba Cloud Bailian / markdownify / self-hosted alternatives, multi-backend + failover) | See fallback chain below |
| Collaboration Platform | `COLLAB.*` (sheets/documents/contacts/calendar/email) | DingTalk (via dws) / Feishu (via lark-cli) / similar OA; choose one | Local JSON+Markdown fallback |

**Configuration**: Enable the corresponding MCP service in QoderWork's "Connectors" settings — no plugin file modifications needed. The suite auto-detects connected backends at runtime; multiple vendors of the same type auto-failover.

---

## Skill Catalog

### Configuration & Management

| Skill | Description |
|------|------|
| `/litigation-hub` | Intelligent routing + workflow orchestration + panoramic overview |
| `/onboarding-interview` | First-use practice profile configuration |
| `/quick-config` | Single-item quick modification of any qoder.md setting without re-running onboarding |

### Analytical Work

| Skill | Description |
|------|------|
| `/litigation-visualization` | Four-step charting method + single-file HTML interactive charts (SVG, zero external dependencies) |
| `/fact-analysis` | Main fact document (md): links to Legal Relationship Chart (HTML) + Legal Facts Timeline (HTML) + embedded chronicle |
| `/element-attack-defense` | Claim-basis attack/defense analysis (core analysis engine) |
| `/property-investigation` | "Four-Channel Preservation Map" architecture (Direct Lock / Investigation Tracking / Creditor Interception / Associated Penetration), preservation priority matrix + litigation concurrence analysis + action roadmap |
| `/legal-research-report` | Dual-perspective (attorney/counsel) legal research report, LAW.* backend (Yuandian/PKULaw swappable + failover) retrieval & verification, md-first output |
| `/new-law-interpretation` | Old-vs-new comparison-driven firm-level regulatory interpretation; reads profile for industry perspective, asks application target/depth/implementation, md primary with optional HTML/Word export |

### Document Drafting

| Skill | Description |
|------|------|
| `/complaint` | First-instance complaint / second-instance appeal / retrial application / arbitration application / arbitration counter-application |
| `/defense-brief` | First-instance defense / appeal response / retrial response / arbitration response / arbitration counter-claim response |
| `/evidence-catalog` | Evidence ordering, grouping, and drafting (text level) |
| `/cross-examination` | Item-by-item "three attributes" cross-examination opinion |
| `/trial-outline` | Trial preparation plan + court examination question list |
| `/closing-argument` | Unified closing argument drafting: pre-trial brief + post-trial supplemental brief, covers first/second/retrial |
| `/procedural-documents` | Procedural documents eight-family router (preservation / evidence / party & claim changes / trial procedure / enforcement / filing / other / jurisdiction objection), 40+ document types |

### Case Management (Attorney/Counsel Dual-Mode)

| Skill | Description |
|------|------|
| `/case-manager` | Full case lifecycle management (intake/follow-up/deadlines/panorama/close/archive), attorney/counsel dual-mode — attorneys include conflict-of-interest gate (Lawyers Law §39) and retainer management; counsel includes external counsel management. Minimum-necessary field set adapts to all scenarios; includes Civil Procedure Law deadline computation + enforcement/preservation deadline tracking, four-tier todo and optional scheduled reminders; collaboration platform structured sheets (`COLLAB.sheet_*`, DingTalk/Feishu/similar) preferred, local file fallback |
| `/case-review` | Three-level coverage: trial review (5 dimensions) / judgment analysis (6 dimensions) / closing review report (10 items + 4-dimension reflection); self-handled (deep review with ledger + facts + process docs) vs. non-self-handled (limited-info review) dual-depth; counsel mode adds external counsel evaluation; review report must pass `/legal-verification` before output |
| `/litigation-knowledge-base` | Three sections: case notes / work notes / legal knowledge base, primarily qmind semantic retrieval + collaboration platform documents (`COLLAB.doc_*`) as team collaboration alternative; onboarding-guided configuration |

### Quality Fence · Output Gate

| Skill | Description |
|------|------|
| `/legal-verification` | **Mandatory gate before every file output**: verifies all statute/article/case citations line-by-line via LAW.* backend (Yuandian/PKULaw swappable + failover), determines "accurate / timeliness risk / semantic inconsistency / not found", passes only after all verified; can also independently verify any text |

---

## Design Principles

1. **Lightweight Skeleton**: Provides methodological core and document capability framework without over-prescribing, leaving room for user growth
2. **Graceful Degradation**: Every MCP dependency has a fallback path; complete drafts can be produced without any MCP
3. **User-Configurable**: Personalized via onboarding interview + qoder.md; subsequent quick changes via `/quick-config`
4. **Platform-Agnostic**: Not bound to any specific MCP vendor; auto-detects at runtime
5. **Methodology Self-Contained**: Core analysis engine has built-in methodology; not dependent on external resources
6. **Traceable**: Four-tier source traceability label system; citation reliability is transparent

---

## Methodological Foundation

The plugin's core analysis engine (Element Attack/Defense Analysis) employs the following methodological framework:

- **Claim-Basis Method (Anspruchsgrundlage)**: Reverse-searches normative basis from the legal effect of claims, reviews element-by-element
- **Court-Report Technique (Relationstechnik)**: Plaintiff phase → Defendant phase → Counter-defense → Re-counter-defense → Evidence phase, progressive review
- **Three-Layer Review Structure**: Right has arisen → Right has not been extinguished → Right is exercisable; progressive layers where negation at any layer negates the whole

---

## File Structure

```
qwenwork-cn-litigation/
├── .qoder-plugin/
│   └── plugin.json              ← Plugin metadata
├── skills/
│   ├── litigation-hub/SKILL.md
│   ├── onboarding-interview/SKILL.md
│   ├── litigation-visualization/SKILL.md
│   ├── fact-analysis/SKILL.md
│   ├── element-attack-defense/SKILL.md
│   ├── property-investigation/SKILL.md
│   ├── legal-research-report/SKILL.md
│   ├── new-law-interpretation/SKILL.md
│   ├── complaint/SKILL.md
│   ├── defense-brief/SKILL.md
│   ├── evidence-catalog/SKILL.md
│   ├── cross-examination/SKILL.md
│   ├── trial-outline/SKILL.md
│   ├── closing-argument/SKILL.md
│   ├── procedural-documents/SKILL.md (+ references/00-general-standards·01~08 eight families)
│   ├── case-manager/SKILL.md
│   ├── case-review/SKILL.md
│   ├── litigation-knowledge-base/SKILL.md
│   ├── legal-verification/SKILL.md
│   └── quick-config/SKILL.md
├── matters/                     ← Matter-level configuration (Matter Profile)
│   └── matter-template.md       ← Matter config template (copied as {slug}/matter.md during intake)
├── qoder.md                     ← Practice profile (generated by onboarding interview)
├── connectors.md                ← Connector/MCP dependency documentation
└── README.md                    ← This file
```

---

## Author & License

This project was originally developed by You Chu (游初) and released under the Apache License 2.0. See [LICENSE](./LICENSE).
