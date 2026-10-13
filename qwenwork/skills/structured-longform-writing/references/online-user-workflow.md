# QoderWork Online User Workflow

This reference is for long-form writing requests from QoderWork online users. It translates the QoderWork product context into writing behavior. It is not an internal architecture guide.

## Core rule

QoderWork is the execution environment. This skill provides the writing process and quality bar. Facts must come from user-provided materials, available tool results, readable files, webpages, session context, or explicit assumptions.

Do not invent:

- metrics, rankings, user counts, conversion rates, benchmark results, or experiment outcomes
- customer names, internal cases, quotes, references, or citations
- product roadmap commitments or launch dates
- facts supposedly found in attachments or webpages that were not actually read

## Common user paths

### Weak one-line request

The user gives a short request such as "帮我写份方案", "写个汇报", or "整理成报告".

Handle it as follows:

1. If the topic is clear enough, produce a useful first draft and mark assumptions.
2. If the topic itself is missing, ask for the topic, audience, and source material.
3. If the user says not to ask questions, produce a fillable draft with `关键假设` and `建议补充的数据/材料`.

### Direct writing request

The user asks for a blog, report, proposal, plan, PRD, technical design, internal briefing, or decision document without many details.

Handle it as follows:

1. Infer the document type and audience from the request.
2. If enough context exists, draft directly and state key assumptions at the end.
3. If context is thin but the structure is still useful, write a structured draft with placeholders framed as "建议补充的数据/材料".
4. If the request is too vague to avoid distortion, ask a small set of high-impact questions or provide a fillable framework.

### Materials-based writing

The user references uploaded files, meeting notes, chat records, bullet points, existing drafts, research excerpts, webpages, screenshots, or previous conversation context.

Handle it as follows:

1. Use the provided materials before general knowledge.
2. If tools are available and the material is not already in context, read or inspect it before making claims.
3. Separate "材料事实", "分析判断", and "建议动作" in reports and proposals.
4. When material quality is uneven, summarize what was usable and what remains missing.

### Multi-turn refinement

The user asks to expand one section, shorten a draft, make it more formal, make it more natural, add risks, add acceptance criteria, or change the audience.

Handle it as follows:

1. Preserve the user's confirmed facts and structure unless the requested change requires restructuring.
2. Apply the new audience and length constraints directly.
3. Do not add new facts while rewriting for style.
4. If the user asks for a shorter version, keep the conclusion and action items before trimming background.

### Tool-gathered evidence

The user asks to base the document on webpages, research, browser observations, product data, or external tools.

Handle it as follows:

1. Gather evidence first when tools are available and the question depends on current or specific facts.
2. Convert raw tool outputs into user-readable findings before writing the final document.
3. Do not expose raw logs, selector details, runtime traces, or internal tool mechanics unless the user asks for technical debugging.
4. If evidence gathering fails, state the gap and draft only the parts that can be supported.

### Audience-specific writing

QoderWork users often ask for documents for leaders, teams, customers, partners, or reviewers.

Default choices:

- Leaders: conclusion first, impact, tradeoffs, risks, required decision.
- Team execution: goals, scope, owners or roles, timeline, acceptance criteria, risks.
- Customers or partners: value, scenarios, boundaries, delivery approach, risk control.
- Technical reviewers: constraints, architecture, data flow, interfaces, failure modes, verification.
- Public readers: viewpoint, explanation, examples, takeaways, non-internal language.

### Problem review or RCA

The user asks for a review, incident report, root-cause analysis, troubleshooting summary, or postmortem.

Handle it as follows:

1. Start with the current conclusion if the material supports one.
2. Separate observed symptoms, impact, timeline, root-cause hypotheses, evidence, fixes, owners, and validation.
3. If root cause is not proven, say "根因假设" rather than "根因".
4. Do not invent impact scope, user count, duration, or recovery time.

### External publication

The user asks for a white paper, customer-facing proposal, official article, public blog, or partner material.

Handle it as follows:

1. Apply stricter factual safety than for internal drafts.
2. Avoid internal names, unreleased roadmap, private metrics, or customer references unless supplied and intended for release.
3. When evidence is missing, provide a framework or draft with explicit verification notes.

## Material sufficiency

### Enough context

Proceed to a final draft when the user gives a clear topic, audience, purpose, and enough source material or constraints.

### Partially missing context

Proceed with assumptions when missing details do not change the core document direction. Add a short "关键假设" section.

Examples:

- The audience is not named, but the topic implies product and engineering readers.
- The user asks for a project plan but does not provide exact dates.
- The user provides notes but no metrics.

### Severely missing context

Ask questions or provide a fillable framework when assumptions would create false content.

Examples:

- "帮我写一份报告" with no topic.
- "写一个对外白皮书" with no industry, data source, or claim boundary.
- "基于附件总结" when the attachment is not available or cannot be read.

## Output behavior

Default to the final usable document. Do not show the internal writing brief, unless the user asks for planning first or the request is too risky to draft.

Add these sections only when useful:

- `关键假设`: when reasonable assumptions were made.
- `建议补充的数据/材料`: when evidence is missing.
- `待确认问题`: when the user must decide before the document can be accurate.

Keep the user's likely destination in mind. A QoderWork online user usually wants a document they can send, paste, review, or continue editing, not an explanation of how the agent worked.
