# Lawyer Casework Head Butler

A civil and commercial litigation assistant for practicing attorneys in China. **23 capabilities** cover one continuous workflow: intake → retrieval → analysis → evidence → drafting → hearing → enforcement → closing.

Three things separate it from a pile of loose skills: **one entry point** (the casework hub recognises intent and orchestrates pipelines), **one profile** (a 5-minute onboarding interview, after which you are never asked again who you are, what tone your documents take, or where your docket lives), and **one gate** (every formal document passes citation verification before delivery — script-level checks, no pass means no delivery).

> **Disclaimer**: This plugin assists attorney work; it does not replace professional judgement. All deliverables must be reviewed by the handling attorney. Deadline calculations are for reference only — the controlling dates are those stated in court documents and confirmed by the handling attorney.

---

## Who It Is For

- **Practising attorneys** — full-lifecycle litigation work, from intake quoting to closing and archiving
- **In-house counsel** — outside litigation management, external counsel coordination, litigation risk assessment
- **Paralegals** — material parsing, evidence organisation, retrieval and first drafts

---

## Skills (23)

The "Command" column is what you say in chat; the "Directory" column is the identifier used inside the package — cross-references between skills use directory names.

### Entry & Configuration

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Casework Hub | `lawd-casework-hub` | Suite entry: intent routing, skill overview, pipeline orchestration, data-connection health check | Routing plan (in chat) |
| Onboarding Interview | `lawd-onboarding-interview` | Builds the attorney profile in 5 minutes, shared by the whole suite | `办案画像.md` (casework profile) |

### Intake & Materials

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Intake Checklist | `lawd-intake-checklist` | Cause-of-action based checklist of what to ask in the client meeting | Checklist with structured JSON |
| Service Proposal & Quote | `lawd-lawyer-quotation-generator` | Service scope and fee proposal at intake (fee calculation included) | Firm-standard fee proposal |

### Retrieval

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Statute Retrieval | `lawd-regulation-retrieval` | Statute and provision retrieval with query rewriting | Insight summary + statute list (10 by default) |
| Case-Law Retrieval & Report | `lawd-case-retrieval` | Three modes: similar-case retrieval / full judgment text by docket number / formal retrieval report | Chat or .md; judgment text in Markdown+PDF; report as script-validated .docx |

### Analysis

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Case Legal Analysis Report | `lawd-analysis-report` | Comprehensive legal analysis of the case | Formatted Word document |
| Claim Analysis & Strategy | `lawd-complaint-analyzer` | Cause of action elements, disputed issues, attack/defence strategy | Full or brief disputed-issue analysis |
| Litigation Risk & Recovery | `lawd-litigation-risk` | Win-probability range plus counterparty solvency and recovery feasibility | Assessment report (.md default, .docx optional) |
| Corporate Due Diligence | `lawd-company-info` | Counterparty verification, business scope and licence gaps, asset leads | Due diligence report |

### Evidence

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Integrated Evidence Strategy | `lawd-civil-evidence-enhanced` | Three-property analysis / proof architecture / evidence-chain mapping | Evidence report .docx |
| Evidence Schedule | `lawd-evidence-list-generator` | Court-ready evidence schedule | Evidence schedule in Word |
| Evidence Timeline | `lawd-evidence-timeline-generator` | Fact and evidence chronology | Timeline Markdown + interactive HTML |

### Drafting

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Statement of Claim | `lawd-civil-complaint` | Drafts the complaint by six cause-of-action families; flags jurisdiction risk when an arbitration clause is found | Court-format Word |
| Statement of Defence | `lawd-defense-statement-draft` | Defence statement, optional element-based court format | Narrative defence + drafting notes |
| Cross-Examination Opinion | `lawd-cross-examination-opinion-generator` | Item-by-item three-property challenge | Cross-examination opinion + rebuttal suggestions |
| Closing Argument | `lawd-civlit-pleading-brief` | Pre-hearing and post-hearing briefs across first instance, appeal and retrial | Formal Word brief + Markdown outline |
| Notice of Appeal | `lawd-civil-appeal-petition-generator` | Civil notice of appeal | Notice of appeal .docx |
| Enforcement Application | `lawd-civlit-enforcement-application` | Full enforcement application set | Word document set + Markdown preview |

### Hearing

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Hearing Preparation | `lawd-civlit-preparation` | Orchestrator: integrates evidence analysis, disputed issues, questioning and bench simulation | Hearing preparation report; questioning strategy report when only questioning is needed |
| Bench Simulation | `lawd-civlit-judge-simulation` | Predicts outcome from the adjudicator's perspective | Bench simulation report in Word |

### Quality Gate

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Citation Verification | `lawd-legal-citation-verifier` | **Output gate**: verifies every statute and case citation before delivery | Verification report: authoritative text, effective date, validity status, accuracy verdict, corrected text |

### Case Management

| Command | Directory | Purpose | Deliverable |
|---|---|---|---|
| Case Manager | `lawd-case-manager` | Intake / updates / deadline calculation and alerts / portfolio briefing / closing / archiving | Case file, docket, deadline to-dos, archive index |

---

## Typical Pipelines

| Scenario | Skill sequence |
|---|---|
| New matter arrives | Case Manager (intake) → Intake Checklist → Case Material Parsing |
| Preparing to sue | Claim Analysis & Strategy → Statute / Case-Law Retrieval → Statement of Claim → Evidence Schedule |
| Served with a complaint | Case Material Parsing → Claim Analysis & Strategy → Integrated Evidence Strategy → Statement of Defence |
| Formal analysis output | Case Legal Analysis Report → Litigation Risk & Recovery |
| Before the hearing | Hearing Preparation → Bench Simulation → Cross-Examination Opinion |
| After the hearing | Closing Argument (supplementary brief) |
| After judgment | Notice of Appeal or Enforcement Application → Case Manager (closing) |
| Checking the counterparty | Corporate Due Diligence → Litigation Risk & Recovery |

Orchestration rules: at most 4 steps at a time, confirmation after each step, citation verification before any formal document leaves, and the hub writes results back to the case docket.

---

## Data Connections (Optional)

| What you want | Without a connector | With a connector |
|---|---|---|
| Look up statutes and cases | **Stops and tells you which data source to connect** — it will not assemble statutes from general web search | Every citation verified and traceable, safe to file with the court |
| Check counterparty registration and litigation risk | Proceeds but marks `[L4-主体信息待核验]` | Registration, shareholders and litigation records verified directly |
| Team docket collaboration | Falls back to local files, marked "local mode" | Shared online docket for the whole team |

The suite runs without any connector, but authoritative-citation capabilities refuse to degrade — by design: **it would rather stop than hand you a fabricated statute.** See [CONNECTORS.md](CONNECTORS.md).

---

## Deliverables & Formatting

- All deliverables are written to `outputs/` in the workspace (the only directory the UI scans); orchestrator sub-outputs to `outputs/sub/`; case files to `cases/{case-short-name}/`
- **Markdown first, through the verification gate, then Word on request** — no Word conversion without a verified Markdown draft
- Court filings follow the formal document preset (FangSong body at 小三, 28pt fixed line spacing, A4, 3.7cm top/bottom, 2.8cm left/right margins)
- All conventions live in `办案画像.md`, which you can open and edit directly

---

## Two Limitations To Know

1. **Docket write-back requires one explicitly bound matter.** The hub triggers it during orchestration; a directly invoked skill submits the same standard case event when the case manager is available. Ad-hoc drafts and ambiguous matters do not create docket noise.
2. **Procedural deadlines are auxiliary estimates.** The script performs calendar arithmetic; rules awaiting verification are clearly marked, known-risk rules are blocked, and no holiday extension is returned when the target year's calendar data is missing. The lawyer must still verify the final deadline against the court document.

---

## Version

**v0.01 · launch line-up.** Three newly built framework skills (Casework Hub / Onboarding Interview / Case Manager) plus 20 shipped skills.
