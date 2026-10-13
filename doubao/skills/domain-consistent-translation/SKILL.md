---
name: domain-consistent-translation
description: Use when the user requests professional translation, bidirectional translation, business communication translation, technical document/manual translation, attachment or image translation, terminology unification, style-consistent polishing, or format-preserving translation, especially with keywords such as 专业翻译、术语统一、双向翻译、商务沟通、技术文档、说明书翻译、附件翻译、格式保留.
---

# Domain Consistent Translation

## Workflow

### 1. Confirm direction, context, and deliverable

Identify the source language, target language, document type, industry, and whether the user wants translation, polishing, terminology explanation, consistency checking, or an editable artifact.

Concrete conventions:
- If the user says the page "全是翻译成英文", treat every visible text block on that page as needing English output unless they mark an exception.
- If the user asks for a business phrase translation only, output `1` ready-to-send version and do not add explanations unless the phrase contains ambiguity.
- If the source is already in the requested target language, say so and offer the likely intended alternative, such as English translation for a Chinese marketing title.
- For medical-device manuals, distinguish product-scope edits such as `外科预期用途` from prior `口腔` or `医美` context; remove or flag inconsistent remnants instead of blending indications.

### 2. Inherit or reset terminology and style

Carry forward the user's current terminology table, style, and formatting preferences across turns, but reset context when the user explicitly says the new manual or product should not refer to earlier dialogue.

Concrete conventions:
- Preserve user-designated terms exactly, including `handlepiece`, `control switch`, `SMA905`, `Disposable Fiber Tip`, `Silicone Sheath`, `Control Switch`, `Whitening Tip`, `Therapy Tip`, and `Light Guide Tip`.
- When the user says `handlepiece` is a manual-specific term, do not rewrite it as `handpiece`, `handle`, or `handheld unit`.
- Keep `Cleaning, Disinfection and Sterilization` as the referenced chapter title when adding cautions about sterilized accessories.
- When later uploads contain only images or attachments after an initial instruction such as translating a manual into Russian or English, continue the same target language and format unless the user changes it.

### 3. Extract protected entities before translating

Before drafting, list mentally or explicitly the entities that must survive unchanged or be normalized consistently.

Concrete conventions:
- Preserve model names, connector standards, and interface labels such as `SMA905`, `STOP`, `DOB`, `DOI`, `DOE`, and `Passport No.`.
- Preserve quantities, dates, colors, style numbers, table headings, figure labels, unit symbols, capitalization, and placeholders; do not convert or omit them unless the user requests localization.
- In outer-trade or textile order messages, keep color, quantity,款号 and shipping/date details intact because changing any one of these changes the business commitment.
- In operation instructions, keep mechanical direction words such as `clockwise`, `counterclockwise`, `tighten fully`, `insert firmly`, `click`, and `fully tightened` aligned with the original sequence.

### 4. Draft using the domain register

Translate or polish according to the document's register: concise and sendable for business chat, formal and controlled for manuals/regulatory text, and terminology-forward for legal, GLP, aviation, automotive, industrial, medical, and specification-table content.

Concrete conventions:
- For medical-device operation manuals, prefer controlled instruction forms such as `Ensure the tip is fully tightened`, `Laser output while the tip is not properly tightened may result in damage to the device`, and `Only use a sterilized Silicone Sheath`.
- For `Light Guide Tip` variants, express `Straight` and `Bent` as two models or variants and state that only the light guide rod shape differs when the user provides that constraint.
- For passport-field abbreviations, map `出生日期` to `Date of Birth / DOB`, `护照号` to `Passport Number / Passport No.`, `护照签发日期` to `Date of Issue / DOI`, and `护照有效期` to `Date of Expiry / DOE`.
- For legal, immigration, medical, or compliance text, translate and explain uncertain terms, but do not present the output as legal or medical advice.

### 5. Preserve structure and format

Match the original structure unless the user asks for rewriting: paragraphs remain paragraphs, numbered warnings remain numbered warnings, and tables remain tables.

Concrete conventions:
- Preserve numbered adverse-event lists such as `1) Pain`, `2) Gum bleeding`, `3) Tooth sensitivity`; do not merge them into a single paragraph.
- Preserve warning labels such as `Caution:` and `Note:` and keep them distinct when their functions differ.
- For OCR/specification images, reproduce tables as Markdown tables when possible and preserve interface names, standards, and unit symbols in the original cells.
- For PPT or document translation, replace text by paragraph/table cell while preserving layout; after generation, check for residual source-language text and unmatched text boxes.

### 6. Handle attachments, images, and unreadable inputs

For images, screenshots, PDFs, DOCX, or PPT, read or OCR the content first, then translate in batches that preserve the original order and local context.

Concrete conventions:
- Prefer the provided local attachment path over a remote link when both are present; if local reading fails, use the link or ask for a clearer file.
- For a multi-image continuation, process each page/image in order and keep the same terminology table; do not restart terminology on image `2` or page `3`.
- If an image is unreadable, too low-resolution, or the text is cropped, state which part cannot be read and translate only the legible text instead of inventing missing words.
- If a video or large file cannot be processed directly, ask for `SRT` or `TXT` subtitle export, compressed audio, or segmented materials before translating.

### 7. Explain only what helps the user's next action

Add notes only when the task needs them: terminology alternatives, ambiguity, safety implications, or user-requested understandability checks.

Concrete conventions:
- If the user asks whether an English instruction is understandable to overseas readers, answer `可懂/不可懂` first, then give the smallest corrected version.
- If correcting a typo such as `漆区别`, silently interpret it as `其区别` and mention the correction only when it affects meaning.
- For image operation captions such as `拧松取下`, provide a short caption-style phrase, not a full explanatory paragraph.
- For ordinary hotel, ticketing, or order messages, avoid prefaces like "Here is the translation"; give the sendable text directly.

### 8. Final consistency check and handoff

Before final delivery, check terminology, entities, numbers, warning labels, target language, and tone across the current output and relevant prior turns.

Concrete conventions:
- Verify every protected term from step `2` appears with the same spelling and capitalization throughout the answer.
- Verify product scope has not drifted: if the current manual is only `外科`, do not leave `oral`, `aesthetic`, `dermatology`, or `body contouring` language unless the user explicitly requested it.
- If the user wants an editable PPT/DOCX or image text replacement, state that translation content is ready and ask or proceed according to available tools, but do not alter technical meaning for layout convenience.
- When a temporary term decision is likely to matter later, state it briefly, e.g. "后续我将沿用 `handlepiece` 不译。"

## Boundaries

- Do not omit, expand, or rewrite key information unless the user explicitly asks for polishing, replacement, or adaptation.
- Do not translate protected terms, model numbers, connector names, placeholders, units, brand names, or user-fixed terminology such as `handlepiece`, `SMA905`, `Silicone Sheath`, `Control Switch`, and `Cleaning, Disinfection and Sterilization`.
- Do not break numbering, tables, warning labels, figure captions, paragraph structure, or operation order; keep lists such as `1) Pain`, `2) Gum bleeding`, and `3) Tooth sensitivity` as separate items.
- If the target language is unclear, the text is already in the target language, the source is missing, or OCR is unreliable, explain the issue and ask or offer a reasonable next step.
- For legal, medical, and compliance materials, provide translation and terminology explanation only; include uncertainty where relevant and do not claim professional legal/medical judgment.

## Tools

- Use OCR/attachment reading for images, screenshots, PDFs, DOCX, and PPT before translating.
- Use a temporary terminology table for cross-turn consistency; include protected terms such as `handlepiece`, `SMA905`, and `Silicone Sheath` when present.
- Use structured output for tables, numbered lists, figure captions, warnings, and bilingual term lists.

## Example

User: `翻译并润色：先将Silicone Sheath套在手柄前端，调整位置，使 Silicone Sheath 上的按键凸起与手柄 Control Switch 的位置一致...`

Response:
`Slide the Silicone Sheath onto the front of the handlepiece and align the sheath button protrusion with the Control Switch. Push the front end of the Silicone Sheath backward to expose the notch at the front of the handlepiece. Align the rear protrusion of the Whitening Tip or Light Guide Tip with the handlepiece notch and insert firmly until a "click" sound is heard, indicating that the Tip is fully seated. Release and adjust the Silicone Sheath so that its front end fully covers the Tip-handlepiece junction and the Control Switch can be operated normally with clear tactile feedback.`

Terminology held constant: `Silicone Sheath`, `Control Switch`, `Whitening Tip`, `Light Guide Tip`, `Tip`, and `handlepiece`.
