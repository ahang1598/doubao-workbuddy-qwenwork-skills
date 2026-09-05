---
name: create-skill
version: 1.2.0
description: Guides users through creating effective Agent Skills for QwenWork. Use when the user wants to create, write, or author a new skill, or asks about skill structure, best practices, or SKILL.md format.
description_zh: 引导用户为 QwenWork 创建有效的 Agent 技能。当用户想要创建、编写或制作新技能，或询问技能结构、最佳实践或 SKILL.md 格式时使用。
---

# Creating Skills in QwenWork

This skill guides you through creating effective Agent Skills for QwenWork. Skills are markdown files that teach the agent how to perform specific tasks: reviewing PRs using team standards, generating commit messages in a preferred format, querying database schemas, or any specialized workflow.

## Language and Display Contract

Reply in the user's conversation language, but keep conversation language separate from the app UI language and the skill's output language.

- The directory and `name` are technical identifiers. Always use ASCII kebab-case.
- Every user-visible skill must include explicit English and Chinese display names, descriptions, and argument hints.
- Compatibility/default fields use English so the Global English app has a safe fallback.
- In the Global English app, write the `SKILL.md` body in English even when the conversation is Chinese.
- A user request for Chinese skill output affects the skill instructions and runtime output only; it does not make technical identifiers or English display metadata Chinese.

## Before You Begin: Gather Requirements

Before creating a skill, gather essential information from the user about:

1. **Purpose and scope**: What specific task or workflow should this skill help with?
2. **Trigger scenarios**: When should the agent automatically apply this skill?
3. **Key domain knowledge**: What specialized information does the agent need that it wouldn't already know?
4. **Output format preferences**: Are there specific templates, formats, or styles required?
5. **Existing patterns**: Are there existing examples or conventions to follow?

### Inferring from Context

If you have previous conversation context, infer the skill from what was discussed. You can create skills based on workflows, patterns, or domain knowledge that emerged in the conversation.

### Gathering Additional Information

If you need clarification, use the AskUserQuestion tool when available:

```
Example AskUserQuestion usage:
- "Should this skill include executable scripts?" with options like ["Yes", "No"]
```

If the AskUserQuestion tool is not available, ask these questions conversationally.

---

## Skill File Structure

### Directory Layout

Skills are stored as directories containing a `SKILL.md` file:

```
skill-name/
├── SKILL.md              # Required - main instructions
├── .skill-metadata.yaml  # Required - recommended queries shown in the UI
├── reference.md          # Optional - detailed documentation
├── examples.md           # Optional - usage examples
└── scripts/              # Optional - utility scripts
    ├── validate.py
    └── helper.sh
```

### Storage Location

Skills are stored as personal skills under the user's home directory. The exact path depends on the runtime environment:

| Environment | Path |
|-------------|------|
| Host (macOS/Linux) | ~/.qwenworkcn/skills/skill-name/ |
| Host (Windows) | %USERPROFILE%\\.qwenworkcn\skills\skill-name\ |
| VM / Container | /root/.qwenworkcn/skills/skill-name/ |

**Environment detection**: Use the `--resource-dir` value provided by the SDK at runtime, which resolves to the correct platform-specific path automatically. If you need to detect manually:
- **Windows**: Check if `process.platform === "win32"` or if the path separator is `\`. The skills directory is `%USERPROFILE%\.qwenworkcn\skills\`.
- **VM / Container**: Check whether `/root/.qwenworkcn` exists. If it does, use `/root/.qwenworkcn/skills/`.
- **Otherwise** (macOS/Linux host): Use `~/.qwenworkcn/skills/`.

### SKILL.md Structure

Every skill requires a `SKILL.md` file with YAML frontmatter and markdown body:

```markdown
---
name: your-skill-name
name_en: Your Skill Name
name_zh: 你的技能名称
description: Brief English description of what this skill does and when to use it
description_en: Brief English description of what this skill does and when to use it
description_zh: 说明这个技能做什么以及何时使用
argument-hint: Describe the task or attach the relevant files
argument-hint-en: Describe the task or attach the relevant files
argument-hint-zh: 描述任务或附上相关文件
user-invocable: true
---

# Your Skill Name

## Instructions
Clear, step-by-step guidance for the agent.

## Examples
Concrete examples of using this skill.
```

### Required Metadata Fields

| Field | Requirements | Purpose |
|-------|--------------|---------|
| `name` | Max 64 chars, ASCII lowercase letters/numbers/hyphens only | Technical identifier for the skill |
| `name_en` / `name_zh` | Non-empty for user-visible skills | Explicit localized display names |
| `description` | Max 1024 chars, non-empty English text | Compatibility/default discovery description |
| `description_en` / `description_zh` | Non-empty for user-visible skills | Explicit localized discovery descriptions |
| `argument-hint` | Non-empty English text for user-visible skills | Compatibility/default Quick Command hint |
| `argument-hint-en` / `argument-hint-zh` | Non-empty for user-visible skills | Explicit localized Quick Command hints |
| `user-invocable` | `true` unless the skill is internal-only | Controls whether the skill appears in user menus |

---

## Recommended Queries (.skill-metadata.yaml)

Every skill you create must also ship a `.skill-metadata.yaml` file next to `SKILL.md` (note the leading dot). QwenWork reads it when the user clicks **Use** on the skill card and prefills the recommended query into the input box. Without this file the product falls back to a generic query that carries none of the skill's context.

Generate the queries from the skill description, and provide **both Chinese and English** for every field:

```yaml
examples:
  - id: kebab-case-id
    title:
      zh: 中文标题
      en: English Title
    description:
      zh: 一句话说明这个 query 适用的场景
      en: One line describing when this query applies
    prompt:
      zh: |-
        多行中文 query
      en: |-
        Multi-line English query
```

**Write one concrete query per major capability the skill has - normally 2 to 5 examples.** Each `prompt` is the text a user would actually type, with `{{placeholder}}` slots only for what the user must supply: file paths, output path, target format, business parameters. The built-in `pdf`, `docx`, and `xlsx` skills each ship 4-5 examples; read `~/.qwenworkcn/skills/pdf/.skill-metadata.yaml` for a worked example.

A PDF toolkit skill, for instance, gets one example per capability - `extract-text`, `extract-tables`, `fill-form`, `merge-split` - each written out like this:

```yaml
  - id: extract-text
    title:
      zh: 提取文本内容
      en: Extract Text Content
    description:
      zh: 从 PDF 中提取正文，支持多栏排版
      en: Extract body text from a PDF, including multi-column layouts
    prompt:
      zh: |-
        请从这份 PDF 中提取文本：

        PDF 文件：{{PDF 文件路径}}
        页码范围：{{可选，如 1-10}}

        请保留多栏排版的阅读顺序，并把结果写入 {{输出文件路径}}。
      en: |-
        Please extract the text from this PDF:

        PDF file: {{PDF file path}}
        Page range: {{optional, e.g. 1-10}}

        Preserve reading order for multi-column layouts and write the result to {{output file path}}.
```

**The only exception** is a skill that takes no user-supplied input at all: a guidance skill that shapes behaviour across unrelated tasks, or a theme or skin skill. Those ship the single default query instead. Test it honestly - if you can write even one sentence a user would type to point this skill at their own file or target, the exception does not apply.

Do not reach for the default query because a skill has many capabilities. Many capabilities means **more examples, not a vaguer one**. Shipping the default query for a skill that has real tasks wastes the file: the user sees the same generic text as a skill with no metadata at all.

For the full format, placeholder rules, and the exact default query text, see [metadata-reference.md](metadata-reference.md).

---

## Writing Effective Descriptions

The description is **critical** for skill discovery. The agent uses it to decide when to apply your skill.

### Description Best Practices

1. **Write in third person** (the description is injected into the system prompt):
   - Good: "Processes Excel files and generates reports"
   - Avoid: "I can help you process Excel files"
   - Avoid: "You can use this to process Excel files"

2. **Be specific and include trigger terms**:
   - Good: "Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
   - Vague: "Helps with documents"

3. **Include both WHAT and WHEN**:
   - WHAT: What the skill does (specific capabilities)
   - WHEN: When the agent should use it (trigger scenarios)

### Description Examples

```yaml
# PDF Processing
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.

# Excel Analysis
description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.

# Git Commit Helper
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.

# Code Review
description: Review code for quality, security, and best practices following team standards. Use when reviewing pull requests, code changes, or when the user asks for a code review.
```

---

## Core Authoring Principles

### 1. Concise is Key

The context window is shared with conversation history, other skills, and requests. Every token competes for space.

**Default assumption**: The agent is already very smart. Only add context it doesn't already have.

Challenge each piece of information:
- "Does the agent really need this explanation?"
- "Can I assume the agent knows this?"
- "Does this paragraph justify its token cost?"

**Good (concise)**:
```markdown
## Extract PDF text

Use pdfplumber for text extraction:

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

**Bad (verbose)**:
```markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are many libraries available for PDF processing, but we
recommend pdfplumber because it's easy to use and handles most cases well...
```

### 2. Keep SKILL.md Under 500 Lines

For optimal performance, the main SKILL.md file should be concise. Use progressive disclosure for detailed content.

### 3. Progressive Disclosure

Put essential information in SKILL.md; detailed reference material in separate files that the agent reads only when needed.

```markdown
# PDF Processing

## Quick start
[Essential instructions here]

## Additional resources
- For complete API details, see [reference.md](reference.md)
- For usage examples, see [examples.md](examples.md)
```

**Keep references one level deep** - link directly from SKILL.md to reference files. Deeply nested references may result in partial reads.

### 4. Set Appropriate Degrees of Freedom

Match specificity to the task's fragility:

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| **High** (text instructions) | Multiple valid approaches, context-dependent | Code review guidelines |
| **Medium** (pseudocode/templates) | Preferred pattern with acceptable variation | Report generation |
| **Low** (specific scripts) | Fragile operations, consistency critical | Database migrations |

---

## Common Patterns

### Template Pattern

Provide output format templates:

```markdown
## Report structure

Use this template:

```markdown
# [Analysis Title]

## Executive summary
[One-paragraph overview of key findings]

## Key findings
- Finding 1 with supporting data
- Finding 2 with supporting data

## Recommendations
1. Specific actionable recommendation
2. Specific actionable recommendation
```
```

### Examples Pattern

For skills where output quality depends on seeing examples:

```markdown
## Commit message format

**Example 1:**
Input: Added user authentication with JWT tokens
Output:
```
feat(auth): implement JWT-based authentication

Add login endpoint and token validation middleware
```

**Example 2:**
Input: Fixed bug where dates displayed incorrectly
Output:
```
fix(reports): correct date formatting in timezone conversion

Use UTC timestamps consistently across report generation
```
```

### Workflow Pattern

Break complex operations into clear steps with checklists:

```markdown
## Form filling workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 1: Analyze the form
- [ ] Step 2: Create field mapping
- [ ] Step 3: Validate mapping
- [ ] Step 4: Fill the form
- [ ] Step 5: Verify output
```

**Step 1: Analyze the form**
Run: `python scripts/analyze_form.py input.pdf`
...
```

### Conditional Workflow Pattern

Guide through decision points:

```markdown
## Document modification workflow

1. Determine the modification type:

   **Creating new content?** -> Follow "Creation workflow" below
   **Editing existing content?** -> Follow "Editing workflow" below

2. Creation workflow:
   - Use docx-js library
   - Build document from scratch
   ...
```

### Feedback Loop Pattern

For quality-critical tasks, implement validation loops:

```markdown
## Document editing process

1. Make your edits
2. **Validate immediately**: `python scripts/validate.py output/`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. **Only proceed when validation passes**
```

---

## Utility Scripts

Pre-made scripts offer advantages over generated code:
- More reliable than generated code
- Save tokens (no code in context)
- Save time (no code generation)
- Ensure consistency across uses

```markdown
## Utility scripts

**analyze_form.py**: Extract all form fields from PDF
```bash
python scripts/analyze_form.py input.pdf > fields.json
```

**validate.py**: Check for errors
```bash
python scripts/validate.py fields.json
# Returns: "OK" or lists conflicts
```
```

Make clear whether the agent should **execute** the script (most common) or **read** it as reference.

---

## Anti-Patterns to Avoid

### 1. Windows-Style Paths
- Use: `scripts/helper.py`
- Avoid: `scripts\helper.py`

### 2. Too Many Options
```markdown
# Bad - confusing
"You can use pypdf, or pdfplumber, or PyMuPDF, or..."

# Good - provide a default with escape hatch
"Use pdfplumber for text extraction.
For scanned PDFs requiring OCR, use pdf2image with pytesseract instead."
```

### 3. Time-Sensitive Information
```markdown
# Bad - will become outdated
"If you're doing this before August 2025, use the old API."

# Good - use an "old patterns" section
## Current method
Use the v2 API endpoint.

## Old patterns (deprecated)
<details>
<summary>Legacy v1 API</summary>
...
</details>
```

### 4. Inconsistent Terminology
Choose one term and use it throughout:
- Always "API endpoint" (not mixing "URL", "route", "path")
- Always "field" (not mixing "box", "element", "control")

### 5. Vague Skill Names
- Good: `processing-pdfs`, `analyzing-spreadsheets`
- Avoid: `helper`, `utils`, `tools`

---

## Skill Creation Workflow

When helping a user create a skill, follow this process:

### Phase 1: Discovery

Gather information about:
1. The skill's purpose and primary use case
2. Trigger scenarios
3. Any specific requirements or constraints
4. Existing examples or patterns to follow

If you have access to the AskUserQuestion tool, use it for efficient structured gathering. Otherwise, ask conversationally.

### Phase 2: Design

1. Draft the skill name (lowercase, hyphens, max 64 chars)
2. Write complete English and Chinese display metadata with English compatibility defaults
3. Outline the main sections needed
4. Identify if supporting files or scripts are needed

### Phase 3: Implementation

1. Create the directory structure
2. Write the SKILL.md file with frontmatter
3. Write the `.skill-metadata.yaml` file with one bilingual query per major capability
4. Create any supporting reference files
5. Create any utility scripts if needed

### Phase 4: Verification

1. Verify the SKILL.md is under 500 lines
2. Check that the description is specific and includes trigger terms
3. Ensure consistent terminology throughout
4. Verify all file references are one level deep
5. Verify `.skill-metadata.yaml` parses as YAML and every field has both `zh` and `en`
6. Test that the skill can be discovered and applied

---

## Complete Example

Here's a complete example of a well-structured skill:

**Directory structure:**
```
code-review/
├── SKILL.md
├── .skill-metadata.yaml
├── STANDARDS.md
└── examples.md
```

**SKILL.md:**
```markdown
---
name: code-review
name_en: Code Review
name_zh: 代码审查
description: Review code for quality, security, and maintainability following team standards. Use when reviewing pull requests, examining code changes, or when the user asks for a code review.
description_en: Review code for quality, security, and maintainability following team standards. Use when reviewing pull requests, examining code changes, or when the user asks for a code review.
description_zh: 按团队标准审查代码质量、安全性和可维护性。用于审查拉取请求、检查代码变更或用户要求代码审查时。
argument-hint: Paste a diff or attach the files to review
argument-hint-en: Paste a diff or attach the files to review
argument-hint-zh: 粘贴差异内容或附上待审查文件
user-invocable: true
---

# Code Review

## Quick Start

When reviewing code:

1. Check for correctness and potential bugs
2. Verify security best practices
3. Assess code readability and maintainability
4. Ensure tests are adequate

## Review Checklist

- [ ] Logic is correct and handles edge cases
- [ ] No security vulnerabilities (SQL injection, XSS, etc.)
- [ ] Code follows project style conventions
- [ ] Functions are appropriately sized and focused
- [ ] Error handling is comprehensive
- [ ] Tests cover the changes

## Providing Feedback

Format feedback as:
- **Critical**: Must fix before merge
- **Suggestion**: Consider improving
- **Nice to have**: Optional enhancement

## Additional Resources

- For detailed coding standards, see [STANDARDS.md](STANDARDS.md)
- For example reviews, see [examples.md](examples.md)
```

---

## Summary Checklist

Before finalizing a skill, verify:

### Core Quality
- [ ] Description is specific and includes key terms
- [ ] Description includes both WHAT and WHEN
- [ ] Written in third person
- [ ] SKILL.md body is under 500 lines
- [ ] Consistent terminology throughout
- [ ] Examples are concrete, not abstract

### Structure
- [ ] Directory and `name` use ASCII kebab-case technical identifiers
- [ ] User-visible metadata includes complete English and Chinese names, descriptions, and argument hints
- [ ] Compatibility/default display metadata is English
- [ ] File references are one level deep
- [ ] Progressive disclosure used appropriately
- [ ] Workflows have clear steps
- [ ] No time-sensitive information
- [ ] `.skill-metadata.yaml` ships alongside SKILL.md with `zh` and `en` for every field
- [ ] One concrete query per major capability, with placeholders only where the user must supply information
- [ ] The default query is used only for skills that take no user input at all

### If Including Scripts
- [ ] Scripts solve problems rather than punt
- [ ] Required packages are documented
- [ ] Error handling is explicit and helpful
- [ ] No Windows-style paths
