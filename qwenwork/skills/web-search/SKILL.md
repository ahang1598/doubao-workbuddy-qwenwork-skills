---
name: web-search
description: Search the web for current information and return structured titles, URLs, source text, dates, and ranks. Use for open-ended web research, recent events, articles, and fact lookup.
---

# Web Search

Use the `qwenwork_web_search` MCP tool. Do not read credentials, token files, or model service environment variables, and do not call a search backend directly.

## Workflow

1. Send one focused topic in `query`; keep it within 70 characters.
2. Use `time_range` only when the user needs results from the last day, week, or month.
3. Start with a small `max_results`; broaden or rewrite the query once if results are empty.
4. Preserve returned URLs exactly. Cite the sources used in the answer.
5. Fetch a known result URL with the available page-reading capability when the result excerpt is insufficient.

The tool returns structured JSON with `provider`, `query`, and `results`. Each result can contain `title`, `url`, `content`, `snippet`, `mainBody`, `publishedAt`, `siteName`, `icon`, `refer`, `score`, and `rank`.
