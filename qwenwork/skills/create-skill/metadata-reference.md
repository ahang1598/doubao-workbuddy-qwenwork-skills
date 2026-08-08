# .skill-metadata.yaml Reference

This file documents the recommended-query metadata that ships with every skill.

## Purpose

`.skill-metadata.yaml` lives next to `SKILL.md` (note the leading dot) and holds the recommended queries for the skill. When the user clicks **Use** on a skill card, QwenWork reads this file, prefills `@[skill:skill-name]` plus the selected query into the input box, and opens a new conversation.

- One example -> that query is prefilled directly.
- Multiple examples -> the user picks one from a selection dialog first.
- File missing or unparsable -> the product falls back to a generic query that carries none of the skill's context. Always ship the file.

## File Format

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

Rules:

- `examples` is a list; each item needs `id`, `title`, `description`, `prompt`.
- `title`, `description`, and `prompt` each require **both** `zh` and `en`. Never ship a single-language file.
- The two languages must express the same request. The English text is a translation, not a different task.
- `id` is kebab-case and unique within the file.
- Use the `|-` block scalar for multi-line prompts so trailing newlines are trimmed.
- Keep `title` short enough to read in a list (a few words). Keep `description` to one line.
- Do not repeat the skill name in the query; the skill mention is inserted automatically.

## Choosing the Query Content

The default expectation is **one concrete query per major capability the skill has**, normally 2 to 5 examples. Every built-in skill follows this: `pdf`, `docx`, `xlsx`, and `find-skills` each ship 4-5 examples. Read `~/.qwenworkcn/skills/pdf/.skill-metadata.yaml` to see it in practice.

Only one narrow case departs from this - a skill that takes no user-supplied input at all. Everything else gets concrete queries.

### Standard: one concrete query per capability

List the skill's capabilities, then write one example for each. A PDF toolkit skill supporting text extraction, table extraction, form filling, and merge/split gets four examples with ids like `extract-text`, `extract-tables`, `fill-form`, `merge-split`.

Each query is the text a user would actually type, with `{{placeholder}}` slots for the parts only the user can supply:

```yaml
examples:
  - id: md-to-docx
    title:
      zh: Markdown 转 Word
      en: Markdown to Word
    description:
      zh: 将撰写好的 Markdown 渲染为 .docx 文档
      en: Render a finished Markdown file into a .docx document
    prompt:
      zh: |-
        请把这份 Markdown 转成 Word 文档：

        Markdown 文件：{{Markdown 文件路径}}
        输出路径：{{输出文件路径}}

        要求：
        1. 保留标题层级、列表和表格
        2. 应用中文排版默认值
      en: |-
        Please convert this Markdown into a Word document:

        Markdown file: {{Markdown file path}}
        Output path: {{output file path}}

        Requirements:
        1. Preserve heading levels, lists, and tables
        2. Apply Chinese typography defaults
```

Placeholder rules:

- Syntax is `{{...}}`, and the content describes what to fill in: `{{Markdown 文件路径}}`, not `{{input}}`.
- Localize the placeholder text along with the surrounding query.
- Only use placeholders for information the skill cannot infer: file paths, output paths, target format, business parameters. Everything the skill already knows how to do belongs in the query as plain text.
- Keep it to 1-4 placeholders. A query that is mostly placeholders gives the user nothing to start from.

### Exception: the default query

Use this only for a skill that takes no user-supplied input at all: a guidance skill that shapes behaviour across unrelated tasks, or a theme or skin skill. If you can write even one sentence a user would type to point the skill at their own file or target, this case does not apply.

**Two failure modes to avoid**, both of which produce a file the user cannot tell apart from having no metadata at all:

- Reaching for the default query because the skill *sounds* broad. A skill named after a capability - code review, translation, test generation - has real tasks and gets concrete queries. A `code-review` skill should ship something like "请帮我审查这段代码：\n\n代码位置：{{PR 链接或文件路径}}".
- Reaching for the default query because the skill has *many* capabilities. A `pdf-processor` skill that extracts text, extracts tables, fills forms, and merges documents needs **four examples**, not one vague one. More capabilities means more examples, never a vaguer query.

When the exception genuinely applies, use the product default query verbatim:

```yaml
examples:
  - id: default
    title:
      zh: 通用使用指南
      en: General Usage Guide
    description:
      zh: 适用于所有技能的通用使用模板
      en: Universal usage template for all skills
    prompt:
      zh: 请描述你想完成的任务和期望结果。也可以附上相关文件，并说明输出格式或其他要求
      en: Describe the task you want to complete and your expected outcome. You can also attach relevant files and specify the output format or any other requirements.
```

Keep this text as-is so the skill stays consistent with the product's built-in default.

## Verification

Before finishing:

- [ ] The file is named `.skill-metadata.yaml` (leading dot) and sits next to `SKILL.md`
- [ ] It parses as valid YAML
- [ ] Every `title`, `description`, and `prompt` has both `zh` and `en`
- [ ] There is one example per major capability, unless the skill takes no user input at all
- [ ] Concrete queries contain placeholders only where the user must supply information
- [ ] If the default query is used, its text is unchanged
