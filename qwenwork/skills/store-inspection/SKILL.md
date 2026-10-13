---
name: store-inspection
version: 1.0.0
description: 门店督导与巡检自动化——通过钉钉 AI 表格管理巡店模版/门店清单/任务派发/统计报表/AI图片审核/HTML报告。所有操作通过 `uv run python scripts/cli.py` CLI 执行。【核心行为约束——违反将导致严重业务事故】(1) 创建模板只确认一次：如果用户已明确字段名称和类型则直接执行 `template preview`（必须带 --scene）生成完整预览作为唯一确认环节，不要在 preview 前多加确认；将 CLI 输出的 user_facing_preview【原封不动】展示给用户（含完整派发消息模板），用户确认后再执行 `template create`（通过 --dispatch-message 传入消息模板）。严禁跳过 preview、严禁省略消息模板展示。(2) dispatch init（建表）与 dispatch notify（发通知）是独立命令，各自需要独立的用户授权；用户说"创建任务"只允许执行 init，执行后必须停下来报告结果；只有用户明确说"派发/通知/发送"才允许 notify。(3) form_url 为空时硬停，绝对禁止在无有效表单链接时执行 notify。(4) 禁止绕过 CLI 直接调用 dws 命令操作业务数据或发消息。(5) 禁止自写定时脚本/循环/daemon。触发词：巡店、巡检、门店督导、门店任务派发、陈列检查、AI审核、督导报告。非门店巡检场景不触发。
install_source: official
install_method: download
skill_id: official_M4sX7k8w
enabled_at: 1791893812901
name_zh: 门店巡检助手
---

# 门店任务中心自动派发系统 Skill

本 Skill 用于管理钉钉 AI 表格上的门店巡店任务，所有能力通过 `uv run python scripts/cli.py` CLI 调用。
本文件是**路由器**：只回答「**何时触发、必须遵守什么、按什么顺序工作、去哪本子文档查细节**」。
具体参数、字段、占位符、场景处方一律在 `references/` 的 3 个子目录里。

## 何时触发

满足以下任一条件时启用本 Skill：

- 用户提到"巡店任务 / 门店巡检 / 门店任务派发 / 门店任务中心"等业务概念
- 用户要求在钉钉 AI 表格中**创建/查询/更新巡店模版**或**维护门店清单**
- 用户希望**手动触发派发**、**给店长发提醒**、**生成汇总报表**、**查询通知明细**、**生成巡店/巡检报告（HTML）**
- 用户要求**绑定/切换/重置 AI 表格**（涉及 `门店清单 / 巡店模版 / 任务记录` 3 张固定表）
- 用户希望**起草 / 重写 / 改写派发或提醒消息文案**（提醒消息复用派发模板，不再有独立字段），由 Agent 起草后**一稿即写入**模板；后续仅在用户**明确说出修改点**时才二次更新
- 用户问**统计/数据**类问题（哪些模板用得多 / 完成率 / 门店表现 / 趋势）
- 用户希望**把当前巡店配置分享给同事/团队成员**，或**收到他人分享的巡店配置**（含 BASE_ID 的语句）
- 用户提供了**人员名称**需要查询用户信息（如 userId），用于门店店长指定等场景

## 不要触发

- 与门店巡店无关的 AI 表格操作（直接使用通用 `dws` 命令即可）
- 通用编程、写作、数据分析任务
- 非钉钉生态的任务派发场景

## 4 步标准工作流

### 步骤 1：检查初始化

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py init validate
```

- `is_passed: true` → 进入下一步
- 未初始化 / base_id 缺失 → 进入 [`references/setup/01-init.md#首次使用`](./references/setup/01-init.md#首次使用)
- 字段缺失 / 类型不匹配 → 提示用户跑 `init url <BASE_ID> --auto-repair` 补齐

### 步骤 2：根据用户意图路由到子文档

按操作频次，文档分两栈：

| 类型 | 入口 | 何时用 |
| :--- | :--- | :--- |
| **配置时**（一次性 / 偶发） | [`references/setup/README.md`](./references/setup/README.md) | 绑定 AI表格 / 维护门店 / 维护模板 / 起草消息文案 / 分享配置 |
| **运行时**（高频 / 周期性） | [`references/runtime/README.md`](./references/runtime/README.md) | 派发 / 查询进度 / 催办 / 报表 / 统计 |
| **共享参考** | [`references/shared/`](./references/shared/) | 术语 / 硬约束 / 占位符 / 字段字典 |

每个入口里都有「场景 → 文档」「命令 → 处方」速查表，按用户的诉求选 1 个子文档进入即可。

> **用户名称 → userId 查询**：当用户提供了人员名称（如店长姓名）而非 userId 时，先通过通讯录查询获取 userId，再用于后续命令：
> ```bash
> dws contact user search --query "张三" --format json
> ```
> 从返回的 `result[0].userId` 中提取 userId。详见 [`02-store.md#步骤-1先通过通讯录查询店长信息`](./references/setup/02-store.md#步骤-1先通过通讯录查询店长信息)。
>
> **获取当前用户信息**：需要获取当前登录用户的 userId、corpId 等信息时：
> ```bash
> dws contact user get-self --format json
> ```
> 返回 `result[0].orgEmployeeModel` 中包含 `userId`、`corpId`、`orgUserName` 等字段。

### 步骤 3：构造命令前查参数（先 -h，再读决策点）

CLI 参数的**事实唯一来源是 `--help` 输出**；子文档只承担「Agent 决策逻辑」（互斥关系、默认行为、业务场景映射、输出结构）。

**取参数三级查法**（按需深入）：

```bash
# 一级：列出所有 command
cd <SKILL_DIR> && uv run python scripts/cli.py --help
# 二级：列出某 command 的 subcommand
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch --help
# 三级：列出某 subcommand 的所有参数及其 help
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch init --help
```

正确顺序：**先进入对应子文档的「场景处方」看清楚业务流程 → 跑 `-h` 拿到最新参数清单 → 再按子文档「关键决策点」组装命令**。

> **不要凭印象拼参数；也不要照搬子文档里旧的参数表**——参数以 `-h` 输出为准。

### 步骤 4：高危操作前先二次确认

`init unbind` / `store delete` 等：向用户复述「我即将执行 X，会删除 Y，确认请回复"确认"」，
拿到肯定回复后再执行。详见 `references/shared/hard-constraints.md#H5`。

## Critical Rules（必读，详见 hard-constraints.md）

- **H1** 不要重复跑 `dispatch init` 重新派发——拿到 `form_url` 后用 `dispatch notify --task-id <ID> --form-url <URL>` 复用现有任务（避免重复表）。`--reuse new` 必须配 `--force-new`。详见 [`#H1`](./references/shared/hard-constraints.md#H1)
- **H2** 不要绕过 CLI——禁用 `dws aitable` 原生命令读写业务数据，禁写脚本胶水代码。CLI 缺能力时直接告诉用户『当前 CLI 不支持』。详见 [`#H2`](./references/shared/hard-constraints.md#H2)
- **H3** 三张固定表（`门店清单` / `巡店模版` / `任务记录`）名称禁改；改了系统失能。详见 [`#H3`](./references/shared/hard-constraints.md#H3)
- **H5** `init reset` / `store delete` 等高危操作执行前必须复述「我即将执行 X，会删除 Y，确认请回复"确认"」。详见 [`#H5`](./references/shared/hard-constraints.md#H5)
- **H6** Skill 内**严禁**写循环 / daemon / `nohup` / 后台脚本做定时执行；CLI 一次性调用，周期触发由用户的 Agent 宿主环境配置。详见 [`#H6`](./references/shared/hard-constraints.md#H6)
- **H8** 多个启用模板时若用户未指定模板，必须先 `template list` 让用户确认；只有一个时直接用并告知用户。详见 [`#H8`](./references/shared/hard-constraints.md#H8)
- **H9** `dispatch init`（建表）和 `dispatch notify`（通知）是**独立命令，各自需要独立的用户授权**。"创建任务"只允许执行 `dispatch init`，执行完**必须停下来报告结果并等待用户指令**；只有用户**明确说"派发/通知/发送"**后才允许执行 `dispatch notify`。详见 [`#H9`](./references/shared/hard-constraints.md#H9)
- **H10** 创建模版时，自定义字段名称**必须由用户提供**（Agent 禁止自行编造），每个字段的类型**必须经用户明确确认**（Agent 禁止自行推断）。交互**必须使用自然语言对话**，**禁止使用 `ask_question` / `ask_human` 表单工具**收集或确认字段信息。**只确认一次原则**：如果用户已明确提供字段名称和类型，应直接执行 `template preview`（含 `--scene`）生成完整预览作为唯一确认环节，**不要在 preview 之前多加一轮确认**。将 CLI 输出的 `user_facing_preview` 原封不动展示给用户（含完整派发消息模板），用户确认后再执行 `template create`（通过 `--dispatch-message` 传入确认后的消息模板）。严禁跳过 preview、严禁省略消息模板展示。详见 [`#H10`](./references/shared/hard-constraints.md#H10)
- **H11** 当模板包含 `ai_review: true` 的字段时，`dispatch init` 完成后 Agent 必须验证 AI 审核字段是否创建成功，并向用户报告状态。详见 [`#H11`](./references/shared/hard-constraints.md#H11)
- **H12** `form_url` 为空时**必须硬停**，绝对禁止在无有效表单链接时执行 `dispatch notify`。无有效链接的派发会导致店长收到无法打开的死链接，造成严重业务事故。详见 [`#H12`](./references/shared/hard-constraints.md#H12)
- **H13** 表单分享链接（`form_url`）**只能**通过 `dispatch init` 自动提取或用户手动粘贴获取。Agent **绝对禁止**以任何理由自行拼接、猜测或硬编码表单 URL——`shareUuid` 由系统生成，无法通过 `baseId`/`tableId`/`viewId` 推导；错误链接一旦派发给店长**不可撤回**。详见 [`#H13`](./references/shared/hard-constraints.md#H13)
- **H14** `dispatch notify` **必须显式指定发送范围**（`--all` / `--target-store-ids` / `--tags` / `--only-pending` 四选一），不带范围参数 CLI 直接报错。用户说"通知所有"→ `--all`；指定具体门店或店长 → 先 `store list` 查 `store_id` 再 `--target-store-ids`；**绝对禁止**在用户指定了发送对象时使用 `--all`。详见 [`01-dispatch.md#dispatch-notify`](./references/runtime/01-dispatch.md#dispatch-notify派发入口主命令)
- **H15** 向店长发送任何业务消息（派发/提醒/催办）**必须且只能**通过 `dispatch notify` 完成。**绝对禁止**直接调用 `dws chat message send` 手动发消息——绕过 CLI 会导致通知记录不写入、去重/冷却保护失效、统计全部失真。用户提供了消息格式时，**必须先** `template update --dispatch-message` 写入模板表，**再** `dispatch notify` 派发。详见 [`#H15`](./references/shared/hard-constraints.md#H15)

## 子技能：report-generator（HTML 巡检报告）

> [!IMPORTANT]
> 当用户要求「**生成巡店报告 / 巡检报告 / 导出报告 / 出一份报告**」时，
> **必须使用本技能自带的 `skills/report-generator/` 子技能**，
> **禁止使用 `data-report` 等外部技能或自行拼接 HTML**。

完整操作流程和命令参数见 [`skills/report-generator/SKILL.md`](./skills/report-generator/SKILL.md)。

**快速流程概览**（4 步）：

> **跨平台路径说明**：示例中 `<TEMP>` 为系统临时目录占位符，请根据操作系统替换：
> - **推荐**：当前 workspace 下 `./tmp/`（Agent 环境中 shell 重定向可能被安全策略阻止时使用）
> - macOS/Linux：`/tmp`（或 `$TMPDIR`）
> - Windows PowerShell：`$env:TEMP`

```bash
# 1. 导出字段定义（⚠️ 每次必须重新导出，禁止复用旧文件！解绑/重新派发后字段 ID 会变化）
dws aitable field list --base-id <BASE_ID> --table-id <TABLE_ID> --format json > <TEMP>/fields.json

# 2. 导出巡检记录（⚠️ 每次必须重新导出）
dws aitable record list --base-id <BASE_ID> --table-id <TABLE_ID> --format json > <TEMP>/data.json

# 3. 调用子技能生成 HTML（注意 --mode 选择正确的模板！）
#    单店报告：--mode single-store  |  多店报告：--mode multi-store  |  自动：--mode auto（默认）
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py generate-report <TEMP>/data.json --fields <TEMP>/fields.json --output <TEMP>/report.html --mode auto

# 4. 内嵌图片 + 自动压缩（必须！OSS 签名链接会过期，压缩默认启用无需加 --compress）
cd <SKILL_DIR>/skills/report-generator && python3 scripts/cli.py embed-images --input <TEMP>/report.html --base-id <BASE_ID> --table-id <TABLE_ID> --skill-cli <主技能CLI路径> --fields <TEMP>/fields.json
```

> **模板分流规则**：单店报告使用卡片网格布局（渐变 header + 总结分析 + 图片放大），
> 多店报告使用 KPI 概览 + 共性问题分析布局。详见子技能文档。

推送报告时使用**钉钉文档上传 + 授权 + 单条消息**方案（文案摘要与文档链接合为一条消息），详见子技能文档步骤 5。

## 子文档索引

| 路径 | 用途 |
| :--- | :--- |
| [`references/setup/`](./references/setup/) | **配置时**命令族（init / store / template / share）+ 对应处方 |
| [`references/runtime/`](./references/runtime/) | **运行时**命令族（dispatch / monitor / summary / stats）+ 对应处方 |
| [`references/shared/`](./references/shared/) | **共享参考**入口（术语 / 硬约束 / 占位符 / 字段字典 速查） |
| [`references/shared/glossary.md`](./references/shared/glossary.md) | 术语表 / 系统架构 / ID 与时间约定 / 配置文件位置 |
| [`references/shared/hard-constraints.md`](./references/shared/hard-constraints.md) | **硬约束唯一来源**（H1 ~ H6 完整规则） |
| [`references/shared/placeholders.md`](./references/shared/placeholders.md) | 消息占位符表 + Markdown 渲染规则 + extra_info / 提醒消息复用机制 |
| [`references/shared/data-model.md`](./references/shared/data-model.md) | 全部表 / 字段定义 + 统计口径 |
| [`skills/report-generator/SKILL.md`](./skills/report-generator/SKILL.md) | **HTML 巡检报告生成**子技能（数据导出 → 生成 HTML → 推送） |
