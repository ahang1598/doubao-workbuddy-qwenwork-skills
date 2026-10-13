---
name: gongwen-format
description: Format, review, or rewrite Chinese official documents according to the requirements in GB/T 9704-2012 and the local file `公文标准格式.doc`. Use this skill for 公文排版, 公文格式审查, 通知/请示/报告/函/纪要/命令（令）规范化, or when converting a draft into standard党政机关公文格式.
---

# Gongwen Format

## Overview

Use this skill to turn a draft into a compliant Chinese official document, or to review an existing document against the standard in `公文标准格式.doc`.

Read [references/formatting_guidelines.md](references/formatting_guidelines.md) before making layout decisions. It contains the extracted rules from `公文标准格式.doc`.

## When To Use

- Formatting or checking `doc` / `docx` / plain-text drafts into standard 公文格式
- Rewriting notices, reports, requests, replies, letters, meeting minutes, or orders into compliant layout
- Reviewing whether an existing document matches the national standard
- Producing a formatting checklist before a human finishes the document in Word/WPS

## Workflow

1. Identify the document type:
   - Standard 公文
   - 信函格式
   - 命令（令）格式
   - 纪要格式
2. Extract or confirm the core elements:
   - 发文机关
   - 发文字号
   - 标题
   - 主送机关
   - 正文层级
   - 附件说明 / 附件
   - 署名、日期、印章或签发人
   - 抄送、印发机关、印发日期
3. Apply the layout rules in `references/formatting_guidelines.md`.
4. If the source data is incomplete, do not invent factual elements such as 发文字号、密级、签发人、抄送机关. Mark them as missing and continue.
5. When direct binary Word editing is not practical, output:
   - a normalized final text structure
   - an explicit formatting checklist for Word/WPS execution
   - any unresolved missing metadata

## Output Requirements

For review tasks, return:

- Non-compliant items
- Correct standard for each item
- A corrected version or exact revision instruction

For drafting or rewriting tasks, return:

- The normalized document text in final order
- The layout instructions needed to reproduce it in Word/WPS
- Any assumptions you made

## Rules To Enforce

- Prefer explicit user or organization template rules over the generic national standard.
- If no local rule conflicts, use the requirements extracted from `公文标准格式.doc`.
- Keep wording formal, concise, and administrative in tone.
- Preserve factual content; do not silently rewrite policy meaning.
- Ensure the first page contains body text.

### Hierarchy Numbering (层次序号)

Must use the following format (GB/T 9704-2012):
- Level 1: `一、`, `二、`, `三、`... (中文数字+顿号)
- Level 2: `（一）`, `（二）`, `（三）`... （全角括号+中文数字）
- Level 3: `1.`, `2.`, `3.`... (阿拉伯数字+英文句点)
- Level 4: `（1）`, `（2）`, `（3）`... （全角括号+阿拉伯数字）

**Do NOT use Roman numerals (I, II, III) or other formats.**

### Hierarchy Fonts (层次字体)

- Level 1: `3号黑体` (Heiti / SimHei)
- Level 2: `3号楷体` (Kai / KaiTi)
- Level 3 and 4: `3号仿宋` (Fangsong / FangSong_GB2312)

### Page Numbers (页码)

- Font: `4号半角宋体` Arabic numerals
- Format: `— 1 —` (一字线 + 页码 + 一字线)
- Position: below the core text area bottom edge
- Alignment: odd pages right-aligned, even pages left-aligned

## Bundled Resources

- [references/formatting_guidelines.md](references/formatting_guidelines.md): concise rulebook extracted from `公文标准格式.doc`
- [scripts/gongwen_checklist.py](scripts/gongwen_checklist.py): prints a checklist for standard, letter, order, or minutes format
