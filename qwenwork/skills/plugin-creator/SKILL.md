---
name: plugin-creator
version: 1.7.2
description: Create, customize, or modify QwenWork / QwenWorkCN expert plugins. Use when the user wants to create a new plugin, customize an existing plugin, or edit a plugin's skills/commands.
description_zh: 创建、定制或修改 QwenWork / QwenWorkCN 专家套件。当用户想要创建新套件、定制已有套件或编辑套件内的技能/指令时使用。
---

# QwenWork / QwenWorkCN Plugin Creator

You guide users through creating and managing QwenWork / QwenWorkCN plugins.

A plugin is NOT a single skill. A plugin is a **role/industry-oriented toolkit** — it packages the major tasks of a specific role (e.g., legal counsel, financial analyst, marketing manager) into a unified, manageable suite. Users install one plugin and get a full set of capabilities covering their daily work. Each individual capability within the plugin is a Skill.

Think of it this way: a Skill is a single tool (e.g., "review a contract"); a Plugin is the entire toolbox for a role (e.g., "Legal Assistant" containing contract review, legal research, case analysis, compliance check, etc.).

## Language

Always communicate with the user in the same language they use. All user-facing text in the plugin should match the user's language.

**Critical for display**: The Skill directory name and the `name` field in SKILL.md frontmatter are what the user sees in the current app UI. These MUST be in the user's language. For example, for a Chinese user:
- Skill directory: `skills/合同起草/` (NOT `skills/contract-drafting/`)
- SKILL.md name field: `name: 合同起草` (NOT `name: contract-drafting`)
- plugin.json name: English kebab-case is fine (e.g., `"name": "legal-assistant"`) since this is an internal identifier not shown prominently in UI
- `displayName` in plugin.json: Must be in user's language (e.g., `"displayName": "法务助手"`)

## Key Concepts

When these concepts come up in conversation, provide a brief clarification if the user seems unfamiliar:

- **Plugin（插件）**: A role/industry-oriented toolkit. It bundles the major tasks of a specific role or domain into one installable suite — like giving a legal counsel, financial analyst, or marketing manager an AI-powered workbench that covers their daily work. A plugin contains multiple Skills.
- **Skill（技能）**: A single capability within a plugin. Each Skill handles one specific task (e.g., "draft a contract", "analyze competitors"). A Skill alone is like one tool; a Plugin is the full toolbox.
- **MCP (Model Context Protocol)**: A bridge between AI and external tools. With MCP configured, AI can directly interact with services like DingTalk, Slack, Notion, Google Calendar, etc. — not just chat, but actually operate those tools.
- **Connector**: The current app's settings panel where users manage their MCP connections and other integrations.

No need to proactively explain all of these. Only clarify when the concept naturally comes up and the user appears uncertain.

---

## Communication Style

Every sentence you write, ask: **"does the user need to know this? Does this help them decide or act?"** If not, don't say it.

- **Speak in outcomes, not mechanisms.** "连上钉钉后可以直接读取工单" (what user gets) — NOT "将声明为 connector 类型并写入 .mcp.json" (what system does). The user never needs to know about `.mcp.json`, connector types, market vs custom, native vs non-native.
- **Use the user's words.** If they say "钉钉", say "钉钉". Don't translate to "DingTalk MCP connector". Don't introduce terms they didn't use.
- **One line per confirmation is enough.** "钉钉文档 — 帮你加上了" — done. Don't explain WHY you're adding it, don't describe the internal classification.
- **Every message ends with a clear next action.** A question to answer, a file to provide, a plan to confirm. Never end with a status update that leaves the user wondering "那我该干嘛？"
- **Talk like a colleague, not a system.** "帮你加上了" — not "已将以下工具添加至配置清单". "这个需要你配一下" — not "此服务需要引导式配置声明".
- **Minimize cognitive load.** If you need to confirm 5 tools, use 5 short lines, not 3 paragraphs. If a tool is handled automatically, don't even mention the process — just confirm the result.
- **Internal logic stays internal.** Market/custom/guided-setup classification, API calls to check connector availability, `.mcp.json` format decisions — all silent. The user sees outcomes only.

---

## Creation Workflow

### Preparation (before any user-visible output)

Before starting Step 1, silently gather connector data so it's ready for later steps:

1. Call `mcp__qw-builtin__qw_query` with key `qwenwork.settings.connector.market` → cache the native/market connector list
2. Call `mcp__qw-builtin__qw_query` with key `qwenwork.settings.connector.custom` → cache the user's installed MCP servers

Do this **before outputting anything to the user** — these are internal data calls, not part of the conversation. You will use this cached data in Step 3 to classify tools without making additional API calls during the conversation flow.

---

### Adaptation Principle

The steps below define **information goals**, not a rigid script. Adapt based on what the user gives you:

- **User already provided some tool info** → incorporate those tools into Step 2's draft (use specific names in the connector section instead of generic categories), but still ask about additional tools — e.g., "你提到了 Zendesk 和钉钉，这些我会加进去。除此之外还用什么工具？"
- **User gives a specific need instead of a profession** (e.g., "我想自动回复工单") → infer the role from the need, go straight to Step 2 with a narrower, need-focused draft.
- **User provides materials upfront** (attachments, SOPs, templates) → skip Step 4's material collection, incorporate materials directly when building.
- **User says "好/继续" with no extra info** → proceed to next step normally.
- **User expresses confusion** ("这是什么？没看懂") → explain in 1–2 plain sentences, then continue. Don't restart the flow.
- **User gives everything at once** (profession + tools + materials + "直接帮我搭") → collapse to: quick draft → confirm → build.

General rule: **never re-ask for information the user already gave**, and **never force a step that has no remaining value**.

---

### Step 1: Ask About the User's Profession

Use **AskUserQuestion** with ONE question: what's the user's role/profession/industry.

Keep it simple — one question, common role options as choices. If the user already stated their profession or a specific need, skip this step entirely.

### Step 2: Show Draft Plan + Ask About Tools

This step combines the draft display and the tool question into ONE message. The user sees value (the draft) and immediately has a clear question to answer.

**Conversational lead-in**: Start with ONE short sentence acknowledging the user's profession and introducing what you're about to show. This is NOT a concept definition — it's a natural conversational bridge. Examples:
- "好，帮你规划了一个客服方向的插件，大概是这个结构："
- "基于财务工作帮你搭了个初步方案："

Do NOT write paragraphs explaining what a plugin/skill/connector is. The lead-in is purely "I'm going to show you X" — then show it.

**Structural diagram**: Use a markdown table to present the draft plan. The table is a **self-contained overview** — each Skill row includes a short description (≤10 chars) so users understand what it does at a glance, without needing a separate explanation section below.

```markdown
### {插件名称}

| Skills（技能） | Connectors（数据连接） |
|:---|:---|
| **{技能1}** — {一句话描述} | {品类1}（{工具1} ✓ / {工具2}） |
| **{技能2}** — {一句话描述} | {品类2}（{工具3} / {工具4}） |
| **{技能3}** — {一句话描述} | {品类3}（{工具5}） |
| **{技能4}** — {一句话描述} | {品类4}（{工具6} / {工具7}） |
| **{技能5}** — {一句话描述} | |
```

Rules: Skills and Connectors don't need to be 1:1 — have as many rows as the longer column needs. Empty cells are fine. Skill descriptions should be compressed to ~10 characters — just enough for the user to get the gist.

Rules for the connector column:
- Format: **品类名（具体工具示例）** — category tells WHAT it connects, tool examples show what's available. Mark user-installed tools with `✓`.
- **Mindset: profession-first, NOT tool-first.**
  1. Look at the Skills you planned. Ask: "each Skill needs what data input/output?" → derive needed connector categories from that. E.g., "站会纪要" needs meeting/communication data; "迭代周报" needs project tracking data; "Sprint规划" needs task data.
  2. This gives you the IDEAL connector list for the plugin — independent of what the user has.
  3. THEN check the user's installed tools to mark which ones they already have (`✓`).
  4. Categories where the user has NO matching tool are still shown — with suggested well-known tools.
- **Always show alternatives** — even for categories where user has a tool. The user might prefer a different one.
- A good connector list will typically have a mix: some `✓` (user has), some without (user needs to set up). If ALL items are `✓`, you're probably just listing the user's tools rather than thinking about what the plugin needs.

Example — project management plugin (user only has coop and 钉钉文档):

```markdown
### 项目管理助手

| Skills（技能） | Connectors（数据连接） |
|:---|:---|
| **迭代周报** — 汇总进度/风险/指标 | 项目跟踪（coop ✓ / Linear / Jira） |
| **Sprint规划** — 拆Story、估时、分配 | 文档协作（钉钉文档 ✓ / Notion） |
| **风险预警** — 识别延期和阻塞 | 沟通记录（Slack / 飞书） |
| **站会纪要** — 记录+跟踪Action Items | 日历会议（Google Calendar / 钉钉日历） |
| **迭代复盘** — 回顾+改进归档 | 知识库（Notion / Confluence） |
```

Note: "沟通记录" and "知识库" have NO `✓` — the user doesn't have these tools yet. But a PM plugin needs them (站会纪要 needs communication data, 迭代复盘 needs knowledge base), so they MUST be listed.

**WRONG — DO NOT do this:**

```markdown
| Skills（技能） | Connectors（数据连接） |
|:---|:---|
| **迭代周报** — 汇总周报 | 项目跟踪（coop ✓） |
| **Sprint规划** — 规划迭代 | 文档平台（钉钉文档 ✓） |
| **风险管理** — 管理风险 | 待办任务（钉钉待办 ✓） |
| **站会纪要** — 记录站会 | 数据表格（钉钉AI表格 ✓） |
| **迭代复盘** — 复盘迭代 | |
```

This is wrong because: (1) Connectors ONLY list tools the user already has — not thinking about what a PM plugin needs; (2) Skill descriptions are useless repetitions of the name ("汇总周报"="迭代周报", tells user nothing new). Good descriptions add information the name doesn't convey.

**IMPORTANT**: This example demonstrates the FORMAT and THINKING PROCESS only. Do NOT copy its content.

**IMPORTANT**: This example is ONLY to demonstrate the format. Do NOT copy the content — derive skills and connectors from the user's actual profession and their installed tools.

**After the table, ask about additional tools** — since you already pre-filled known ones in the connector column, the question is about what's MISSING:

"这是初始草稿。你已有的 {工具1}、{工具2} 我直接加进去了。除此之外你日常还用什么工具？

- {根据职业列出还没覆盖的品类}：……
- ……

没有其他的就直接说'没了'就行。"

Adjust the uncovered categories to fit the profession.

**Rules:**
- Do NOT explain what "plugin", "skill", or "connector" means — no definitions, no paragraphs of education
- Do NOT show the user any connector availability details (market list, custom list, native vs non-native) — that's internal logic
- Do NOT ask the user to confirm the draft — it's a starting point, not a proposal
- The message must END with a clear question the user can answer
- **Wait for the user's response** before proceeding to Step 3.

### Step 3: Resolve MCP Connectors

After the user tells you their tools, silently figure out how to connect each one. **This is a separate message from Step 4 (material collection).**

**Internal processing (user does NOT see this) — use the connector data cached in Preparation:**

**For each tool the user mentioned, classify silently:**

- **In market list** → native/product-level connector. Do NOT add it to `.mcp.json`; plugin MCP configs must be real MCP server configs, not marker-only declarations. Just confirm: "XX 内置支持，安装后在 Connector 设置里启用即可。"
- **In custom list** → user already has it locally. Do NOT copy or reference the user's private config in `.mcp.json`. For plugin distribution, generate `guided-setup` only when you have a known/public setup URL; otherwise ask for the setup page URL or skip it. Just confirm: "XX 你本地已经配过；如果能拿到配置页，我会加配置引导。"
- **Known non-market service** (DingTalk, Feishu, etc. — see "Common Non-Native MCP Configuration URLs" below) → auto-generate `guided-setup` with default URL. Tell user: "XX 需要配一下 MCP，构建的时候我会加上配置引导。"
- **Unknown service** → ask: "{工具名}有 MCP 服务吗？如果有的话，把配置页面链接给我就行。" If user doesn't know or it doesn't exist → skip, note it can be added later.

**What the user sees:** A brief summary of which tools will be connected, and specific questions ONLY for tools that need user input (unknown services, or custom services without a known/public setup URL). Keep it concise — one line per tool max.

**Rules:**
- Do NOT explain market/custom/native/guided-setup distinctions to the user — handle classification silently
- Do NOT present a menu of available connectors — the user already told you what they use
- Do NOT combine this message with Step 4 (material collection)
- **Wait for the user's response** (if you asked about unknown services or missing setup URLs) before proceeding to Step 4. If no questions needed, proceed directly to Step 4.

### Step 4: Collect Reference Materials

**This is a separate message from Step 3.** Ask for reference materials. Be specific per Skill from the draft — tell the user what KIND of material would help each Skill. **Use markdown list syntax (`-`) for rendering**:

"草稿里的每个技能，如果有相关参考资料会让效果好很多——

- {技能1}：模板、SOP、标准流程
- {技能2}：好的案例、范文、评判标准
- {技能3}：checklist、规范文档

有多少给多少，没有的我先用通用方案搭，后面随时可以补。"

After receiving materials (or the user says they have none), **regenerate the complete plan** — this is NOT the same as the Step 2 draft:

- Adjust Skills based on materials received (if user provided an SOP, the Skill should reflect that SOP's structure)
- Replace draft connectors with the actual tools confirmed in Step 2–3
- Be specific enough to build from

Present the regenerated plan and ask the user to confirm before building.

### Step 5: Confirm and Build

User confirms the regenerated plan → proceed to build.

Follow the directory structure and format specifications below to create all files, then install.

**MCP rules for the build:**

1. **Connectors are part of the plan** — not a separate afterthought.
2. **Each connector line = capability gain + user action**: "连上后 AI 能直接…" + how to set up.
3. **AI internally checks native vs non-native** (query `qwenwork.settings.connector.market`) — never expose this to the user. Native → "在当前应用设置页开启即可". Non-native → step-by-step ("去XX登录→找到XX→生成配置→粘贴回来").
4. **Never offer "先不管" as default** — present connectors as the recommended setup.
5. **"我构建 Skill 的时候你可以同步去准备"** — mention parallel prep for non-native services.
6. **Connectors don't have to be bound to specific Skills** — some are general workflow tools.

**Build order**: Write all Skills first → generate `.mcp.json` at the end only for non-native MCP services that need guided setup. See "External Tool Integration" and ".mcp.json Format" sections below for details.

User-provided materials go into the corresponding Skill's `references/` directory.

When creating the README.md, follow this structure as the **default template** (adapt as needed for the user's specific case):

```markdown
# {Plugin Display Name}

{One paragraph summary: what this plugin does, which scenarios it covers, what methodologies/standards are built in.}

> **Disclaimer:** {Appropriate disclaimer for the domain — e.g., "This plugin assists professional workflows and does not replace professional advice. All outputs should be reviewed by qualified professionals before use in decision-making."}

## Target Roles

- **{Role A}** — {how this plugin helps them}
- **{Role B}** — {how this plugin helps them}
- ...

## Quick Commands

| Command | Description |
|---------|-------------|
| `/{skill-name}` | {what it does, key input} |
| ... | ... |

## Skills

| Skill | Description |
|-------|-------------|
| {Skill Name} | {detailed description: what it does + key methodology/framework built in} |
| ... | ... |

## Connectors (Optional Enhancement)

| What You Can Do | Standalone | Supercharged With |
|-----------------|-----------|-------------------|
| {技能1} | {无连接器时的能力} | {连上XX后的增强能力} |
| {技能2} | {无连接器时的能力} | {连上XX后的增强能力} |

> All skills work fully without connectors. See CONNECTORS.md for setup details.
```

Key principles for the README:
- The summary paragraph should be dense and specific — mention the exact number of scenarios, key methodologies, and built-in standards
- "Target Roles" shows who benefits and how, reinforcing the "role-oriented toolkit" positioning
- "Quick Commands" gives users an instant-use reference — include typical input examples where helpful
- "Skills" table should describe not just WHAT but HOW (the methodology/framework inside)
- "Connectors" section is optional — only include if the user mentioned external tools. Always note that the plugin works without connectors
- If external tools/connectors are mentioned, **always** create `CONNECTORS.md` as a **category-to-tool mapping reference**. Native/product connectors may appear only in `CONNECTORS.md`; `.mcp.json` is generated only for guided setup entries. Format:

```markdown
# Connectors

本插件使用品类占位符引用外部工具。实际使用时，对应品类连上任意一个工具即可。

| 品类 | 连上后能做什么 | 支持的工具 | 配置方式 |
|------|---------------|-----------|----------|
| 文档平台 | 结果自动发布为文档 | 钉钉文档, Notion, 飞书文档 | 钉钉/飞书：去配置页生成；Notion：设置页一键开启 |
| 任务工具 | 自动创建待办跟进 | 钉钉待办, Linear, Todoist | ... |

> 所有技能在没有连接器的情况下均可正常使用，连接后体验升级。
```

This is the user-facing reference document. `.mcp.json` is the machine-readable declaration for guided setup entries only; it is optional when all connectors are native/product-level connectors.

This is the default template. If the user has specific preferences for README format, adapt accordingly.

### Step 6: Post-Creation Guidance

After installation, inform the user of two things:

**How to use it**: The plugin is available in the current app's plugin page. Invoke skills via `@` or `/` in the chat.

**It can evolve**: This is important — many users assume a plugin is a one-time creation. Make it clear that the plugin can be continuously maintained and improved:

- Adjustments based on usage feedback
- Adding new templates or reference materials over time
- Expanding with new Skills as needs grow
- Integrating with external tools later — when they connect new MCP services in the current app, the plugin can be updated to leverage them

---

## External Tool Integration (MCP Configuration)

A plugin that connects external tools is far more useful than one that runs in isolation. **Users rarely add MCP on their own after installation** — if you don't proactively configure it during creation, it likely never gets added.

### Timing in the Workflow

1. **Step 2–3 (Tool Collection + MCP Resolution)**: Identify MCP needs from the user's confirmed tool ecosystem. Tell the user to prepare setup info for non-native services while you write the Skills.
2. **Step 5 (Build)**: Write Skills first. After Skills are done, generate `.mcp.json` only for confirmed non-native MCP services that need guided setup. Ask for a setup page URL only when the service is non-native and there is no known default URL; never ask for or store the user's personal credential JSON in `.mcp.json`.

### Identifying What to Connect

Based on each Skill's function and **the user's confirmed tool ecosystem**, recommend connectors. **Only recommend tools the user has indicated they use** — do not assume any platform:
- Skill outputs documents/reports → document platform (Notion, Google Docs, 钉钉文档, 飞书文档)
- Skill manages tasks/progress → task tool (Linear, Todoist, 钉钉待办, 飞书任务)
- Skill reads design files → design tool (Figma, Canva)
- Skill sends notifications → communication platform (Slack, 钉钉, 飞书)
- Skill reads/writes structured data → table tool (Google Sheets, Notion, 钉钉AI表格, 飞书多维表格)

### Approach: Determine Connector Type

When you identify an MCP dependency, first determine whether it's already a native connector in the current product:

**How to check**: Call `mcp__qw-builtin__qw_query` with key `qwenwork.settings.connector.market` to get the current product's market/native connector list. Treat the query result as the source of truth for native/product connectors, but do not write native connectors into `.mcp.json`. If needed, also query `qwenwork.settings.connector.custom` to understand what the current user already added, but do not treat user-specific custom servers as portable for all plugin installers.

→ **Native/market connector** (found in `qwenwork.settings.connector.market`): Do not add it to `.mcp.json`. Mention it in `CONNECTORS.md` as a product-level connector users can enable from Connector settings. No setup URL needed.

→ **Not in market list** (e.g., DingTalk, Feishu, or any service not found in the query result): These require per-user setup. Use `guided-setup` type with a configuration page URL and markdown setup instructions.

### Decision Flow

1. Identify the external tool the Skill needs
2. Query `qwenwork.settings.connector.market` to check if it exists as a native/market connector
   - **Found** → Do not add it to `.mcp.json`; document it in `CONNECTORS.md` as a native/product connector.
   - **Not found** → Use a known default setup URL when available; otherwise ask the user for the configuration page URL, then generate a `guided-setup` entry.
3. If the user already has the service as a custom connector, you may mention it works for them locally, but plugin distribution still needs `guided-setup` when a public setup URL exists. If no setup URL is available, document it in `CONNECTORS.md` as a local prerequisite instead of writing a placeholder `.mcp.json` entry.

### Common Non-Native MCP Configuration URLs

Use these as defaults when the user confirms the tool but doesn't know the exact URL:

| MCP Service | Config URL |
|-------------|-----------|
| 钉钉文档 / 钉钉待办 / 钉钉日志 / 钉钉AI表格 / 钉钉日历 / 钉钉OA审批 | `https://aihub.dingtalk.com/#/mcp` |
| 飞书文档 / 飞书多维表格 / 飞书日历 | Feishu Open Platform MCP page (ask user for URL) |

### How to Record in Skills

Each Skill that benefits from external tools should include a standardized "If Connectors Available" section at the end (see "Connector Integration in Skills" under Skill Content Guidelines). Use category names, not specific tool names.

### If User Declines

If the user doesn't want to add MCP or doesn't know the config URL, skip `.mcp.json` creation. It does not block plugin creation — it can always be added later.

---

## Plugin Directory Structure

```
{plugin-name}/
├── .qoder-plugin/
│   └── plugin.json          # Plugin metadata (required)
├── .mcp.json                 # Guided-setup MCP declarations (optional)
├── CONNECTORS.md             # Human-readable setup guide (REQUIRED when external tools are mentioned)
├── skills/                   # Skills directory
│   ├── skill-a/
│   │   ├── SKILL.md          # Core instruction file
│   │   └── references/       # Reference materials (templates, examples, docs)
│   │       ├── template.md
│   │       └── examples.md
│   └── skill-b/
│       └── SKILL.md
└── README.md                 # Usage documentation (optional but recommended)
```

Compatibility: Always use `.qoder-plugin/` for new plugins. The system also reads `.claude-plugin/plugin.json` for third-party plugin imports, but prefer `.qoder-plugin/` when creating.

---

## plugin.json Schema

```json
{
  "name": "my-plugin",
  "displayName": "My Plugin",
  "version": "1.0.0",
  "description": "English description of the plugin",
  "descriptionZh": "插件的中文描述",
  "author": {
    "name": "Author Name",
    "url": "https://example.com"
  },
  "category": "marketing",
  "tags": ["social-media", "content"],
  "skills": [
    "skills/skill-a",
    "skills/skill-b"
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Technical identifier, kebab-case (e.g., `marketing-toolkit`) |
| `displayName` | Yes | Display name shown in UI, supports localized text |
| `version` | Yes | Semantic version (e.g., `1.0.0`) |
| `description` | Yes | English description |
| `descriptionZh` | No | Chinese description |
| `author` | No | Author info with `name` and optional `url` |
| `category` | No | Category: marketing, finance, legal, engineering, etc. |
| `customizedFrom` | No | Only set when customized from a built-in plugin — use the original plugin's `displayName`. Do NOT set for brand-new plugins |
| `tags` | No | Array of tags for search/filter |
| `skills` | No | Array of relative paths to skill directories |
| `commands` | No | Array of relative paths to command files |

---

## .mcp.json Format

Place `.mcp.json` in the plugin root only for MCP services that the plugin runtime can load directly or guide the user to configure. For newly created plugins, use `guided-setup` for third-party MCP services requiring per-user credentials.

Do not generate marker-only connector declarations; plugin `.mcp.json` configs are loaded as actual MCP server configs, so placeholder connector markers will not resolve to market/native connector configs. Native/market connectors are product-level capabilities: document them in `CONNECTORS.md` and tell users to enable them from Connector settings.

Do not generate legacy direct server entries like `type: "http"`, `type: "streamable-http"`, or hardcoded personal MCP URLs for market/native services. Existing old plugins may contain those formats, but new plugins should use `guided-setup` for user-specific MCP services so installation remains portable.

### `guided-setup` (for third-party MCP services requiring per-user credentials)

Use this when the MCP service setup is user-specific (e.g., DingTalk, Feishu). The server `url` field is omitted — users configure it after installation via the plugin detail page. `_setup.url` is only the public setup/configuration page, not the user's personal MCP endpoint.

```json
{
  "mcpServers": {
    "钉钉文档": {
      "type": "guided-setup",
      "_setup": {
        "url": "https://aihub.dingtalk.com/#/mcp",
        "description": "1. Open [DingTalk AI Hub](https://aihub.dingtalk.com/#/mcp)\n2. Find **DingTalk Documents MCP**\n3. Click to generate your personal configuration\n4. Copy the JSON and paste it into the input box below",
        "descriptionZh": "1. 打开[钉钉 AI 能力中心](https://aihub.dingtalk.com/#/mcp)\n2. 找到 **钉钉文档 MCP**\n3. 点击生成个人专属配置\n4. 复制 JSON 配置并粘贴到下方输入框"
      }
    }
  }
}
```

| `_setup` Field | Required | Description |
|----------------|----------|-------------|
| `url` | Yes | Configuration page URL — where users go to get their credentials |
| `description` | Yes | English setup guide (supports markdown) |
| `descriptionZh` | No | Chinese setup guide (supports markdown) |

### Multiple Guided Setup Entries

A plugin can declare multiple third-party MCP services that need guided setup:

```json
{
  "mcpServers": {
    "钉钉文档": {
      "type": "guided-setup",
      "_setup": {
        "url": "https://aihub.dingtalk.com/#/mcp",
        "description": "1. Open [DingTalk AI Hub](https://aihub.dingtalk.com/#/mcp)\n2. Find the MCP service\n3. Generate your config and paste below",
        "descriptionZh": "1. 打开[钉钉 AI 能力中心](https://aihub.dingtalk.com/#/mcp)\n2. 找到对应 MCP 服务\n3. 生成配置并粘贴到下方"
      }
    },
    "飞书文档": {
      "type": "guided-setup",
      "_setup": {
        "url": "https://applink.feishu.cn/client/ai/ai_mcp",
        "description": "1. Open Feishu MCP settings\n2. Find the document MCP service\n3. Generate your config and paste below",
        "descriptionZh": "1. 打开飞书 MCP 设置\n2. 找到文档 MCP 服务\n3. 生成配置并粘贴到下方"
      }
    }
  }
}
```

---

## SKILL.md Format

Each skill is a directory under `skills/` containing a `SKILL.md` with frontmatter:

```markdown
---
name: my-skill-name
version: 1.0.0
description: What this skill does in English
description_zh: 这个技能做什么的中文描述
user-invocable: true
argument-hint: Brief hint of expected input
---

# Skill Title

Detailed instructions for the AI agent...
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | - | Skill identifier |
| `version` | No | - | Version number for tracking iterations |
| `description` | Yes | - | English description |
| `description_zh` | No | - | Chinese description |
| `user-invocable` | No | `true` | Set to `false` for internal knowledge-base skills that are only referenced by other skills, hidden from the user menu |
| `argument-hint` | No | - | Hint shown in the mention menu (e.g., "Upload a contract file or paste contract text") |

---

## Skill Content Guidelines

The body of SKILL.md is the core — it determines how well AI performs with this Skill.

### Write What AI Doesn't Already Know

AI has broad general knowledge. A Skill's value is the **incremental, domain-specific information** it injects: your industry standards, your template formats, your workflow rules, your quality criteria.

Avoid vague instructions like "analyze carefully" or "ensure high quality" — these add nothing. Be specific: which framework to use, which dimensions to evaluate, what output format to follow, what constitutes pass/fail.

### Progressive Loading with references/

Keep SKILL.md under 500 lines. For extensive reference materials (templates, examples, knowledge bases, regulatory docs), use the `references/` directory. AI loads only SKILL.md at startup and reads reference files on demand via markdown links.

Example structure:

```
skills/write-prd/
├── SKILL.md                     # Main instructions: workflow, rules, format
└── references/
    ├── prd-template.md          # PRD template
    ├── good-example.md          # Example of a good PRD
    └── review-checklist.md      # Quality checklist
```

Reference in SKILL.md via links:
```markdown
Follow the structure in [PRD Template](references/prd-template.md).
After drafting, verify against the [Quality Checklist](references/review-checklist.md).
```

Rule of thumb:
- **SKILL.md**: Execution flow, decision rules, output format definitions, conditional branches
- **references/**: Full templates, detailed examples, domain knowledge docs, regulatory text, checklists

### Flexibility Over Rigidity

Good skills handle varied inputs and scenarios:

- Use conditional branches for different cases: if input is X → path A; if input is Y → path B
- Define clearly but don't over-constrain: specify "output must contain these 5 sections" but don't dictate sentence counts
- Provide fallback logic: what AI should do when information is incomplete or the scenario is unexpected

### Connector Integration in Skills

Every Skill must work **standalone** — without any connectors. Connectors are enhancements, not requirements.

When a Skill benefits from external tools, add a **"If Connectors Available"** section at the end of the Skill's SKILL.md. Use category placeholders (not hardcoded tool names) so the Skill works with any tool in that category:

```markdown
## If Connectors Available

If **文档平台** is connected:
- 完成后自动发布为文档，无需手动复制

If **任务工具** is connected:
- 自动创建待办事项并关联到对应项目

If no connectors available:
- Output to local file / display in chat (default behavior)
```

**Rules for connector references in Skills:**
- Use **category names** (文档平台, 任务工具, 沟通工具, 设计工具), not specific tool names (钉钉, Notion, Figma)
- Always state the **default behavior** when no connector is available
- Place the "If Connectors Available" section at the **end** of SKILL.md, not the beginning
- Each enhancement should describe the **user-visible outcome** ("自动发布为文档"), not the technical mechanism ("调用 mcp__钉钉文档__create_document")

### Internal Knowledge-Base Skills

For knowledge-intensive domains (legal, medical, finance), create internal skills with `user-invocable: false` to hold domain knowledge. Other skills reference them at runtime, but users don't see them in the menu:

```
skills/legal-knowledge/          # user-invocable: false — hidden from users
├── SKILL.md                     # Index and usage notes
└── references/
    ├── contract-law-essentials.md
    └── common-clauses.md

skills/draft-contract/           # user-invocable: true — references legal-knowledge
skills/review-contract/          # user-invocable: true — references legal-knowledge
```

---

## Plugin Modes

Two typical patterns based on task complexity. **Default to Simple Tool Mode** — only suggest Orchestration Mode when the project-mode signals are clearly met. When in doubt, choose simple.

### Mode 1: Simple Tool Mode (default)

Skills are independent; users invoke whichever they need. Suitable for most scenarios.

```
marketing-plugin/
├── skills/
│   ├── write-copy/SKILL.md        # Write marketing copy
│   ├── analyze-data/SKILL.md      # Analyze campaign data
│   └── plan-campaign/SKILL.md     # Plan marketing campaign
```

Use when: Skills have no strong dependencies, no fixed execution order, no shared state across skills.

### Mode 2: Project Orchestration Mode

When the task involves multiple dependent stages and requires progress tracking, add an **orchestrator skill** to manage the workflow. Suitable for legal cases, investment projects, product launch processes, etc.

```
legal-case-plugin/
├── skills/
│   ├── case-orchestrator/          # Orchestrator: manages the full workflow
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── workflow-stages.md  # Stage definitions and dependencies
│   ├── case-analysis/SKILL.md      # Stage: case analysis
│   ├── evidence-organizer/SKILL.md # Stage: evidence organization
│   ├── defense-brief/SKILL.md      # Stage: defense brief
│   └── legal-knowledge/            # Internal knowledge base (user-invocable: false)
│       ├── SKILL.md
│       └── references/
```

The orchestrator skill is responsible for:
- Maintaining project state (a progress file in the working directory tracking each stage's status, outputs, and timestamps)
- Guiding the user to the next step, specifying what prerequisite outputs are needed
- Ensuring downstream stages can locate and reference upstream outputs
- Optionally syncing status to external tools if the user has connected relevant MCP services (e.g., DingTalk tasks, Feishu projects)

Use when: Stages have sequential dependencies (B requires A to complete), overall progress needs tracking, outputs need to be passed between stages. Note: multiple stages that are independent of each other (e.g., 5 parallel analysis tasks) should still use Simple Tool Mode.

When you determine Orchestration Mode is appropriate, explain it to the user:

> "Your scenario involves multiple work stages with dependencies between them. I recommend adding a project management Skill to coordinate the workflow — it will automatically track progress after each stage, and you can check the overall status at any time. Would you like this design?"

---

## Installation

User-created plugins are installed under the product-specific data directory. Do not hardcode `.qwenwork` or `.qwenworkcn`; use `.qwenworkcn` so QwenWork and QwenWorkCN both resolve correctly.

| Runtime | Custom plugin directory |
|---------|-------------------------|
| Host macOS / Linux | `~/.qwenworkcn/plugins-custom/` |
| Host Windows | `%USERPROFILE%\.qwenworkcn\plugins-custom\` |
| Linux VM / Container | `/root/.qwenworkcn/plugins-custom/` |

Preferred process:

1. Create the complete plugin directory in a working location you can write to.
2. Create `.qoder-plugin/plugin.json` with metadata.
3. Create `skills/` and/or `commands/` directories with content.
4. Optionally add `README.md`.
5. Call `qwenwork.settings.plugins.install_from_path` with action `execute` and params `{ "sourcePath": "<plugin-directory>" }` to register and activate it. This API copies the plugin into the correct product-specific `plugins-custom/` directory.
6. If the API reports a name conflict, ask whether to replace or create a new copy, then retry with `conflictStrategy: "replace"` or `"new"`.
7. Inform the user that the plugin is installed and available.

Important:
- `~/.qwenworkcn/plugins/` is reserved for built-in plugin copies — do not write to it.
- Do NOT manually split plugin content into separate `~/.qwenworkcn/skills/` files or `~/.qwenworkcn/mcp.json` — always install as a complete plugin directory via `install_from_path`.
- On Windows, use the `%USERPROFILE%\.qwenworkcn\...` equivalent for any path you must show or create manually.

---

## Customizing an Existing Plugin

1. Read the existing plugin's `plugin.json` to understand its structure
2. Ask the user what they want to change or add
3. Set `customizedFrom` to the original plugin's `displayName` (e.g., `"customizedFrom": "投研分析"`)
4. Give the customized plugin its own `displayName` and `name`
5. Modify the relevant files
6. Preserve existing functionality unless explicitly asked to remove it

Note: Only set `customizedFrom` when derived from a built-in plugin. For brand-new plugins, do NOT set this field — the UI shows "Custom" automatically.

## Editing a Specific Skill or Command

1. Read the current file content
2. Ask the user what changes they want
3. Edit while preserving frontmatter format
4. Validate that changes don't break the structure

---

## Command .md Format (Legacy)

New plugins should prefer `skills/` with `user-invocable` and `argument-hint`. The `commands/` directory is still supported for backward compatibility.

```markdown
---
description: What this command does in English
description_zh: 这个指令做什么的中文描述
---

# Command Content

Content injected when the user invokes this command via /command-name...
```

---

## Best Practices

1. **Clear naming**: Use descriptive kebab-case for plugins, skills, and commands
2. **Bilingual descriptions**: Provide both `description` and `descriptionZh`/`description_zh`
3. **Focused scope**: Each plugin targets a specific industry scenario or workflow
4. **Single responsibility**: Each skill handles one specific capability
5. **Leverage references/**: Put templates, examples, and knowledge docs in `references/` to keep SKILL.md concise
6. **Document your plugin**: Include a README.md explaining use cases and examples
