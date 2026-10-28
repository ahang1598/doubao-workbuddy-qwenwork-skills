---
name: prompt-engineering-expert
description: Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents
display_name: "prompt-engineering-expert"
display_name_en: "prompt-engineering-expert"
description_zh: "Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents"
description_en: "Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents"
visibility: "public"
version: 1.0.1
---

# Prompt Engineering Expert Skill

This skill equips Claude with deep expertise in prompt engineering, custom instructions design, and prompt optimization. It provides comprehensive guidance on crafting effective AI prompts, designing agent instructions, and iteratively improving prompt performance.

## Capabilities

- **Prompt Writing Best Practices**: Expert guidance on clear, direct prompts with proper structure and formatting
- **Custom Instructions Design**: Creating effective system prompts and custom instructions for AI agents
- **Prompt Optimization**: Analyzing, refining, and improving existing prompts for better performance
- **Advanced Techniques**: Chain-of-thought prompting, few-shot examples, XML tags, role-based prompting
- **Evaluation & Testing**: Developing test cases and success criteria for prompt evaluation
- **Anti-patterns Recognition**: Identifying and correcting common prompt engineering mistakes
- **Context Management**: Optimizing token usage and context window management
- **Multimodal Prompting**: Guidance on vision, embeddings, and file-based prompts

## Mandatory Gate: Optimizing / Rewriting an Existing Prompt

Applies whenever the user asks to optimize, rewrite, fix, polish, strengthen, broaden or tighten an existing prompt / system prompt / custom instructions. Pure typo or formatting fixes may use the light mode in `references/optimization-workflow.md`. Load that file for the checklist formats and delivery template. Run all steps **before saving any file and before the final reply**.

1. **Visible criteria ledger (before rewriting)**: show a C-numbered list of every criterion in the source and every hard condition from the user. For each item record: the object set, the dimensions required for each object, universal quantifiers (each / both / all), ranking and counts, thresholds, numeric precision, source constraints, and exceptions. When a rule covers several objects, give each object its own entry. Do not let one example stand in for the full object × dimension set.
2. **Ambiguity and authorization**: list underspecified or conflicting items, such as time window, judgment basis, data source, runtime-injected text, subjective intensity, or contradictory meta-requests. Vague requests ("optimize", "make it broader", "more accurate") do not authorize changing a hard criterion. List each proposed change to a C-item as a concrete confirmation question and wait for an answer. If the user forbids questions, keep the original criterion and state that.
3. **Bounded change**: make only the changes the user named or confirmed. Do not invent facts, settings, sources, sections, or requirements. List new ideas separately as *optional suggestions*, never as mandatory rules in the rewrite. Do not delete, loosen, narrow, or add exceptions to any C-item without authorization.
4. **Change ledger and re-verification (after rewriting)**: map every C-item to its location in the new draft and mark it `kept / rewritten / deleted / added`, with the reason and the authorization source. Re-check the full object × dimension combinations against the draft. Then check internal consistency, meaning each key term has one definition throughout. If behavior depends on runtime-injected content, state that prompt-side wording can only mitigate the problem and specify the change needed on the injection side.
5. **Stop conditions**: if any C-item is lost, narrowed, or given a new exception without authorization, or if the ledger and the draft disagree, do not save or deliver. Fix the draft or ask the user.
6. **Honest delivery**: include the ledger, a per-requirement hit table, assumptions, reproducible test cases, and an uncertainty statement. Containing a rule in text is not the same as a verified effect. Mark gains in accuracy, completeness, and similar qualities as `pending verification` unless they were actually executed and observed. Never claim "all constraints preserved", "fixed", or "no problems" unless the ledger and tests support it.

## Use Cases

- Refining vague or ineffective prompts
- Creating specialized system prompts for specific domains
- Designing custom instructions for AI agents and skills
- Optimizing prompts for consistency and reliability
- Teaching prompt engineering best practices
- Debugging prompt performance issues
- Creating prompt templates for reusable workflows
