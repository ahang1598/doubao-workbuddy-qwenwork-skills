---
name: structured-longform-writing
description: Use for structured long-form writing, including blogs, reports, proposals, plans, PRDs, competitive analyses, research summaries, technical design docs, internal briefings, and decision documents. Trigger when the user asks to write, draft, expand, organize, polish into, or turn rough notes, attachments, webpages, or gathered materials into a complete long-form document. Do not use for simple rewriting, one-paragraph summaries, title brainstorming, short messages, translation-only tasks, or purely creative fiction.
install_source: official
install_method: download
skill_id: official_42WXRNi8
enabled_at: 1791893733460
version: 1.0.0
name_zh: 长文本写作专家
---

# Structured Longform Writing

## Purpose

Use this skill to turn long-form writing from a one-shot generation task into a structured writing workflow. The goal is to produce documents that are clear, audience-aware, evidence-conscious, logically organized, and directly usable for blogs, reports, proposals, plans, PRDs, competitive analyses, research summaries, technical design docs, internal briefings, and decision documents.

In QoderWork, users may ask from a chat box, select this skill from the skill center, upload files, reference webpages, or provide scattered notes. Treat QoderWork as the execution environment: the skill supplies the writing method, while facts must come from user materials, available tools, or clearly stated assumptions.

## When to use

Use this skill when the user asks for any of the following:

- A blog post, article, technical blog, guide, tutorial, or thought-leadership piece.
- A report, research summary, market analysis, competitive analysis, investigation report, or status analysis.
- A proposal, plan, strategy document, implementation plan, construction plan, product plan, or project plan.
- A PRD, technical design doc, decision document, internal briefing, review material, or long-form document assembled from rough notes.
- Expansion of scattered ideas, meeting notes, bullet points, user materials, or context into a coherent long-form document.
- A QoderWork online-user request to turn attachments, webpages, meeting notes, customer interviews, research findings, or tool-gathered evidence into a usable long-form deliverable.

## When not to use

Do not use this skill for:

- Simple rewriting or polishing of a short paragraph.
- One-paragraph summaries.
- Title brainstorming only.
- Short messages, notices, chat replies, social posts, or push copy.
- Translation-only tasks.
- Purely creative fiction, poetry, or literary writing where structure and evidence are not the main quality drivers.

## Operating principles

1. Plan before drafting.
2. Structure before expression.
3. Judge before polishing.
4. Prefer user-provided materials over general model knowledge.
5. Never fabricate facts, data, citations, references, customer cases, benchmark results, or company-specific details.
6. If important information is missing but reasonable assumptions are possible, write with explicit assumptions.
7. If essential information is missing and assumptions would distort the document, ask three to five key questions or provide a fillable framework.
8. Reports and proposals must include conclusions or recommendations, not only information listing.
9. Proposals and plans must include implementation path, risks, and acceptance criteria when the topic requires execution.
10. For QoderWork online users, do not expose QoderWork internal runtime details unless the user explicitly asks for technical implementation.
11. The final answer should be useful to the target reader without exposing unnecessary internal process.

## Workflow

Follow this workflow for every long-form writing request.

### 1. Task classification

Classify the request into one primary document type:

- `blog`
- `report`
- `proposal_or_plan`
- `prd`
- `competitive_analysis`
- `technical_design`
- `internal_briefing`
- `other_longform`

If multiple types apply, choose the type that best matches the expected reader action. For example, if the document must drive execution, route as `proposal_or_plan`; if it must produce judgment from facts, route as `report`; if it must persuade or explain to readers, route as `blog`.

### 2. Context sufficiency check

Assess whether the user supplied enough context for a useful document.

- Enough context: proceed directly.
- Partially missing context: infer reasonable defaults and state key assumptions near the end.
- Severely missing context: ask three to five targeted questions or provide a fillable structure instead of inventing content.

Use `references/workflow.md` for detailed context, audience, and brief construction rules.

For QoderWork online-user requests, also use `references/online-user-workflow.md` when the user asks from a QoderWork context, provides attachments or webpages, references tool-gathered material, asks for a document to send/review/share, or asks for a draft based on scattered notes.

### 3. Writing brief

Create an internal writing brief before drafting:

- document type
- target audience
- purpose
- desired reader action
- core message
- source materials
- assumptions
- constraints
- required sections
- evidence needs
- major risks

Do not output this brief unless the user asks for the planning process or the best next step is to confirm direction before writing.

### 4. Outline

Create an outline that serves the document goal. Do not mechanically apply a template if the user’s situation calls for a different structure. Each top-level section should have a clear function.

### 5. Research and evidence handling

Use user-provided materials first. If external information is required and tools are available, gather reliable sources before drafting. If sources are unavailable, avoid specific claims that require evidence. Use “建议补充的数据/材料” for missing evidence rather than making up numbers.

Always distinguish:

- facts supplied by the user
- analysis or judgment
- assumptions
- recommended additions

### 6. Reference routing

Read the relevant reference files when the task matches the type:

- Blog, article, tutorial, thought-leadership: `references/blog-template.md`
- Report, research summary, investigation, analysis: `references/report-template.md`
- Proposal, plan, strategy, implementation plan: `references/proposal-template.md`

For QoderWork online-user deliverables, read:

- `references/online-user-workflow.md`
- `references/output-patterns.md`

For every long-form task, also use:

- `references/workflow.md`
- `references/quality-rubric.md`
- `references/style-guide.md`

For trigger and regression checks during skill evaluation only, use:

- `references/eval-cases.md`

If the draft is generic, repetitive, over-polished, or the user asks for natural expression, use:

- `references/anti-ai-writing.md`

### 7. Draft generation

Draft section by section. Maintain logical progression between sections. Use tables, lists, or diagrams only when they improve clarity. Avoid decorative structure that adds length without improving usefulness.

For Chinese output, default to professional, concrete, and structured language. Avoid excessive slogans such as “全面赋能”“显著提升”“持续优化” unless they are backed by concrete mechanisms.

### 8. Quality review

Before final delivery, review the draft against `references/quality-rubric.md`. If any of the following failures appear, revise internally before responding:

- off-topic content
- missing conclusion
- weak or unclear central message
- repeated paragraphs
- generic statements without object or mechanism
- unsupported facts or numbers
- proposal without implementation path
- report without analysis and recommendation
- blog without viewpoint or reader value
- style mismatch for the target audience

### 9. Final answer

By default, output the final draft directly. Do not expose the internal brief, intermediate outline, or self-review unless useful to the user or explicitly requested.

If important assumptions were made, add a short section at the end named “关键假设”. If evidence is missing, add “建议补充的数据/材料”. If the user asked for a draft that needs follow-up customization, add only the most important next refinement suggestion.
