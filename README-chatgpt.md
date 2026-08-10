# ChatGPT Skills And Experts

本文件由 `scripts/sync_platform.py --platform chatgpt` 自动生成，整理 `chatgpt/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`chatgpt/`
- 定时任务：`ChatgptSkillsDailySync`，每天 18:00 运行
- 当前索引条目数：19
- 当前索引文件数：977
- 最近变更：[2026-08-10-160232](chatgpt/change-logs/2026-08-10-160232.md) - ChatGPT 本次同步新增 399 个文件、修改 6 个文件、删除 392 个文件。 新增条目：plugins/openai-bundled/browser/26.803.41515, plugins/openai-bundled/computer-use/26.803.41515, plugins/openai-bundled/visualize/...

## 数据来源

- `skills` <= `/mnt/c/Users/15805/.codex/skills/.system`
- `plugins` <= `/mnt/c/Users/15805/.codex/plugins/cache`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [System Skills](chatgpt/skills/SUMMARY.md) — `skills/` 功能导航
- [Plugin Cache](chatgpt/plugins/SUMMARY.md) — `plugins/` 功能导航

## 分类索引

### System Skills

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| imagegen | `chatgpt/skills/imagegen` | skill | 12 | Generate or edit raster images when the task benefits from AI-created bitmap visuals such as photos, illustrations, textures, sprites, mockups, or transparent-background cutouts. Use when Codex should create a brand-n... |
| openai-docs | `chatgpt/skills/openai-docs` | skill | 17 | Use for Codex models/pricing, scheduled tasks, skills, settings, setup, troubleshooting, customization, automations, and self-knowledge—including 'you,' 'your,' 'this app,' or 'this coding agent' when they refer to Co... |
| plugin-creator | `chatgpt/skills/plugin-creator` | skill | 10 | Create and scaffold plugin directories for Codex with a required `.codex-plugin/plugin.json`, optional plugin folders/files, valid manifest defaults, and personal-marketplace entries by default. Use when Codex needs t... |
| review-agent | `chatgpt/skills/review-agent` | skill | 2 | Perform a read-only, defect-first review of a specified code change and return every actionable finding. Use when another agent delegates review of uncommitted changes, a base-branch diff, a commit, or custom review i... |
| skill-creator | `chatgpt/skills/skill-creator` | skill | 9 | Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integ... |
| skill-installer | `chatgpt/skills/skill-installer` | skill | 8 | Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private... |

### Plugin Cache

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| browser | `chatgpt/plugins/openai-bundled/browser/26.803.41515` | openai-bundled | 380 | Browser / browser-use plugin Aliases: @browser, @browser-use, browser-use, Browser, in-app browser. Use Browser, the ChatGPT in-app browser, when the user asks to open, inspect, navigate, test, click, type, or screens... Version: 26.803.41515. |
| computer-use | `chatgpt/plugins/openai-bundled/computer-use/26.803.41515` | openai-bundled | 6 | Control desktop apps on Windows from ChatGPT through Computer Use. Version: 26.803.41515. |
| visualize | `chatgpt/plugins/openai-bundled/visualize/1.0.20` | openai-bundled | 8 | Create interactive charts, maps, diagrams, simulations, 3D models, data explorers, and UI previews directly in Codex. Version: 1.0.20. |
| app-698be8fbe10481919ab1df169cc86def | `chatgpt/plugins/openai-curated-remote/app-698be8fbe10481919ab1df169cc86def/3.0.0` | openai-curated-remote | 2 | Resume enables ChatGPT to analyze, improve, and generate professional, ATS-friendly resumes. Upload a PDF or DOCX resume to identify key gaps, strengthen experience bullets, and refine impact with targeted suggestions... Version: 3.0.0. |
| data-analytics | `chatgpt/plugins/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599` | openai-curated-remote | 201 | Answer product and business questions with data Version: 0.2.8-13ceeea1f599. |
| github | `chatgpt/plugins/openai-curated-remote/github/0.1.8-2841cf9749ae` | openai-curated-remote | 26 | Inspect repositories, triage pull requests and issues, debug CI, and publish changes through a hybrid GitHub connector and CLI workflow. Version: 0.1.8-2841cf9749ae. |
| slack | `chatgpt/plugins/openai-curated-remote/slack/0.1.6` | openai-curated-remote | 10 | Work with Slack using the configured Slack integration. Version: 0.1.6. |
| supabase | `chatgpt/plugins/openai-curated-remote/supabase/1.0.0` | openai-curated-remote | 47 | Manage Supabase projects directly through ChatGPT. Execute SQL queries on PostgreSQL databases, design and modify table schemas, deploy serverless edge functions, and configure user authentication. Access real-time lo... Version: 1.0.0. |
| documents | `chatgpt/plugins/openai-primary-runtime/documents/26.805.11740` | openai-primary-runtime | 82 | Create and edit document artifacts in Codex, including Word files and Google Docs. Version: 26.805.11740. |
| pdf | `chatgpt/plugins/openai-primary-runtime/pdf/26.805.11740` | openai-primary-runtime | 8 | Read, create, inspect, render, and verify PDF files in Codex. Version: 26.805.11740. |
| presentations | `chatgpt/plugins/openai-primary-runtime/presentations/26.805.11740` | openai-primary-runtime | 117 | Create, edit, render, verify, and export presentation slide decks. Use when Codex needs to build or modify a deck, slidedeck, presentation deck, slide deck, slides, PowerPoint, Google Slides, PPT, PPTX, .ppt, or .pptx... Version: 26.805.11740. |
| spreadsheets | `chatgpt/plugins/openai-primary-runtime/spreadsheets/26.805.11740` | openai-primary-runtime | 27 | Create, edit, analyze, visualize, render, and export spreadsheets, Microsoft Excel or Google Sheets-ready workbooks in Codex. Version: 26.805.11740. |
| template-creator | `chatgpt/plugins/openai-primary-runtime/template-creator/26.805.11740` | openai-primary-runtime | 5 | Create and update personal templates from files, ImageGen or Product Design images, emails, and Slack messages. Version: 26.805.11740. |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-08-10-160232 | [2026-08-10-160232](chatgpt/change-logs/2026-08-10-160232.md) | ChatGPT 本次同步新增 399 个文件、修改 6 个文件、删除 392 个文件。 新增条目：plugins/openai-bundled/browser/26.803.41515, plugins/openai-bundled/computer-use/26.803.41515, plugins/openai-bundled/visualize/... |
| 2026-08-07-084720 | [2026-08-07-084720](chatgpt/change-logs/2026-08-07-084720.md) | ChatGPT 本次同步新增 239 个文件、修改 0 个文件、删除 239 个文件。 新增条目：plugins/openai-primary-runtime/documents/26.805.11740, plugins/openai-primary-runtime/pdf/26.805.11740, plugins/openai-primary-r... |
| 2026-08-06-110921 | [2026-08-06-110921](chatgpt/change-logs/2026-08-06-110921.md) | ChatGPT 本次同步新增 3 个文件、修改 0 个文件、删除 152 个文件。 新增条目：plugins/openai-curated-remote/app-698be8fbe10481919ab1df169cc86def, plugins/openai-curated-remote/app-698be8fbe10481919ab1df169cc8... |
| 2026-08-05-232542 | [2026-08-05-232542](chatgpt/change-logs/2026-08-05-232542.md) | ChatGPT 本次同步新增 1125 个文件、修改 0 个文件、删除 0 个文件。 新增条目：plugins/openai-bundled/browser/26.727.51351, plugins/openai-bundled/computer-use/26.727.51351, plugins/openai-bundled/sites/0.1.3... |
