# 硬约束（唯一来源）

> 全局生效。本文件是 Skill 中**所有硬约束的唯一来源**，SKILL.md 与各子文档只做"一句话摘要 + 链接到这里"，
> 严禁在其它文档复制完整规则，避免漂移。

---

<a id="H1"></a>
## H1. 禁止绕过 CLI：不得直接使用 `dws` / `aitable` 原生命令操作业务数据

> [!CAUTION]
> 本 Skill 的所有功能必须**只通过 `uv run python scripts/cli.py` CLI 子命令**完成。
> **绝对禁止**以下行为：
> - 直接调用 `dws` 原生命令（如 `dws aitable record list / create / update` 等）读写业务数据表
> - **直接调用 `dws chat message send` 向店长发送消息**——所有派发/提醒消息**必须且只能**通过 `dispatch notify` 发送（详见 [H15](#H15)）
> - 直接调用 `aitable` 命令或通过 AI 表格 API 绕过 CLI 操作业务数据
> - 新增任何 Python / Shell / Node 等脚本文件（包括"临时"或"一次性"使用）
> - 编写胶水代码、批处理脚本、ad-hoc 查询脚本来弥补 CLI 缺失的能力
> - 通过组合 `python -c` / `awk` / `jq` 等命令拼装出 CLI 没提供的能力

**为什么禁止**：`dws` / `aitable` 原生命令不了解本系统的字段映射（fieldName→fieldId）、去重保护、
冷却机制、任务记录回写等内部逻辑，直接调用会导致数据污染、重复派发、统计口径混乱等严重故障。
**`dws chat message send` 绕过 `dispatch notify` 发消息**会导致：通知记录不写入、去重保护失效、
冷却机制被绕过、`DispatchSummary` 统计不准确、后续催办/查询/报表全部失真。

**当现有 CLI 子命令不能满足用户需求时**，正确做法是：

1. 先核对 `references/setup/` 与 `references/runtime/` 下对应命令族文档，确认确实没有可用命令
2. 直接告诉用户「**当前 CLI 不支持该能力，本任务无法完成**」，并简述：
   - 需要哪个新增子命令 / 新增参数才能支持
   - 建议用户在 `store-inspection-skills-group` 仓库提需求扩展 CLI
3. **严禁**自作主张写脚本或拼 `dws` / `aitable` 命令"先帮用户跑一次"

---

<a id="H2"></a>
## H2. 3 张固定表名禁止修改

`门店清单` / `巡店模版` / `任务记录` 是系统识别表的唯一稳定标识。

用户要求重命名其中任何一张时，必须先警示后果（"系统将无法识别，所有功能失效"），
获得明确确认后才执行。

> 派发时系统自动创建的动态数据表**不属于固定表**，请勿与固定表混淆。

---

<a id="H3"></a>
## H3. 删除 / 重置必须二次确认

`init unbind --confirm`、`store delete --yes` 等高危命令必须由用户明确说"是 / 确认 / yes"后才执行。

向用户复述话术：
> 「我即将执行 X，会删除 Y，确认请回复"确认"」

---

<a id="H4"></a>
## H4. 禁止 Skill 内自写定时脚本 / daemon / 后台进程

Skill 内**严禁**写循环、写 daemon、`nohup ... &`、`while true` 等任何形式的定时执行。
CLI 子命令一律一次性调用，跑完即退。

**用户问「如何让任务每天自动派发」时，明确告知**：

> 「本 Skill 不内置定时器，所有派发 / 提醒 / 汇总均为手动单次调用。
> 如需周期触发，请在你的 Agent 宿主环境（或任何外部调度器）中配置周期调用对应 CLI 子命令。」

不再列具体定时方案的命令样板——手动派发命令本身已在 `01-dispatch.md` / `02-monitor.md` / `03-summary.md` 中。

---

<a id="H5"></a>
## H5. 多模板时必须先确认

当系统中存在**多个巡店模版**时，若用户的指令中**未明确指定模版名称或模版 ID**，
Agent **必须先列出所有可用模版并向用户确认**，不得自行猜测或默认选择。

**触发场景举例**：
- 用户说"帮我派发今天的任务"，但未说明是哪个模版
- 用户说"生成汇总报表"，但未指定模版
- 用户说"查询未填写名单"，但未指定模版

**正确做法**：
1. 执行 `uv run python scripts/cli.py template list` 获取所有启用的模版列表
2. 将模版列表（ID + 名称）呈现给用户，询问"请问您希望对哪个模版执行此操作？"
3. 等待用户明确回复后，再继续执行后续命令

**例外**：若系统中**只有一个启用的模版**，可直接使用该模版，无需确认，但应在执行前告知用户
"检测到唯一模版 `{模版名称}`，将使用该模版继续"。

---

<a id="H9"></a>
## H9. `dispatch init` 与 `dispatch notify` 是两个独立动作，各自需要独立的用户授权

> [!CAUTION]
> `dispatch init`（建表）和 `dispatch notify`（发送通知）是**物理隔离的两个独立命令**，
> 各自都需要**用户明确的、独立的授权**才能执行。
> **绝对禁止**把两者当成一个"派发流程"一口气执行。

### 核心规则：`dispatch init` ≠ `dispatch notify`

| 命令 | 做什么 | 影响范围 | 何时允许执行 |
| :--- | :--- | :--- | :--- |
| `dispatch init` | 建/复用任务表 + 通知表 | 仅建表，**不发消息** | 用户说"创建任务"时 |
| `dispatch notify` | 向店长发送通知消息 | **直接影响一线店长** | 用户**明确说"派发/通知/发送"**时 |

### 语义判定规则（Agent 必须严格遵循）

以下用户表述**只允许执行 `dispatch init`**，**禁止执行 `dispatch notify`**：
- "创建任务" / "创建门店督导任务" / "建一个巡检任务"
- "解析 Excel 并创建任务" / "帮我配置好模板和任务"
- "准备好今天的任务"（准备 ≠ 派发）

以下用户表述**才允许执行 `dispatch notify`**：
- "帮我派发今天的任务" / "现在派发"
- "通知所有门店" / "发给所有店长"
- "给未填写的店再催一次"

**用户意图模糊时**（如"今天的任务怎么样了"），应先回答查询结果，**绝对不得推断为"帮我派发"**。

### 禁止的行为

- ❌ 用户说"创建任务"，Agent 执行完 `dispatch init` 后**自行继续执行 `dispatch notify`**
- ❌ Agent 在 `dispatch init` 成功后，以"流程连贯"为由自动跳到 `dispatch notify`
- ❌ Agent 基于时间、日期、周期等条件自行判断"该派发了"并执行
- ❌ Agent 在执行其他操作（如查询、汇总）的过程中"顺便"触发派发
- ❌ Agent 预测用户意图后抢先派发（如"用户可能想派发，我先帮他跑一次"）

### 正确做法

1. **执行 `dispatch init` 后必须停下来**——向用户报告建表结果，然后**等待用户下一步指令**。报告内容**必须包含**：
   - `task_id`（任务 ID）
   - `form_url` 状态（非空 → 展示链接；为空 → 按 [H12](#H12) 处理）
   - AI 审核字段创建状态（成功/降级/失败）
   - **AI 表格链接**（可点击）：从 `dispatch init` 输出的 `task_table_id` 拼接，格式为 `https://docs.dingtalk.com/i/nodes/{base_id}`。**必须展示此链接**，让用户能直接打开查看创建的表格
2. **只有用户明确说出"派发/通知/发送"类指令后**，才执行 `dispatch notify`
3. **定时/周期派发需求**——告知用户本 Skill 不内置定时器（见 [H6](#H6)），所有派发均为用户手动单次触发

---

<a id="H12"></a>
## H12. `form_url` 为空时必须硬停，禁止在无有效表单链接时派发

> [!CAUTION]
> 当 `dispatch init` 输出的 `form_url` 为空时，Agent **必须立即停下来等待用户处理**，
> **绝对禁止**在 `form_url` 为空的情况下执行 `dispatch notify`。
> 无有效表单链接的派发会导致店长收到**无法打开的死链接**，造成严重的业务事故。

### 为什么是硬约束？

`form_url` 为空意味着表单视图**尚未成功发布分享**。此时派发通知：
- 店长收到的表单链接**无法打开**（404 或权限错误）
- 预写的任务实例行**无法与表单提交关联**（主键匹配失败）
- **已发出的通知无法撤回**，必须重新派发，造成重复骚扰
- 整个任务变成"废任务"，必须人工善后

### 正确做法

1. `dispatch init` 完成后，**首先检查输出中 `form_url` 是否非空**
2. **`form_url` 非空** → 报告给用户，等待用户说"派发"后才执行 `dispatch notify`（见 [H9](#H9)）
3. **`form_url` 为空** → 按以下话术告知用户并**停下来等待**：

   > 「任务表已创建成功（task_id: `{task_id}`），但表单分享链接自动获取失败。
   > 请您在 AI 表格中打开表单视图，点击右上角**分享**按钮开启分享，完成后回复「已发布」即可。
   > ⚠️ 在表单发布之前，我不会执行派发，避免店长收到无效链接。」

4. 用户确认表单已发布后，**重新执行 `dispatch init`**（系统会自动通过 `extract_form_share_url` 从视图详情的 `formInfo.shareUuid` 提取分享链接），**不需要用户复制粘贴任何链接**
5. 如果重新执行后 `form_url` 仍为空，才要求用户手动复制分享链接，通过 `dispatch notify --task-id <ID> --form-url <链接>` 传入

### 禁止的行为

- ❌ `form_url` 为空时仍执行 `dispatch notify`（"先派发了再修复"）
- ❌ 使用无 prefill 的原始编辑链接（`/i/nodes/`）代替表单分享链接
- ❌ 跳过 `form_url` 检查直接进入派发流程
- ❌ **Agent 自行拼接/猜测分享链接格式**（`shareUuid` 由系统生成，无法通过 baseId/tableId/viewId 推导）
- ❌ 要求用户复制粘贴分享链接作为首选方案（应优先让系统自动获取）

---

<a id="H10"></a>
## H10. 自定义字段名称和类型必须由用户提供/确认，禁止 Agent 自行编造或推断

> [!CAUTION]
> 创建巡店模版时：
> 1. **检查项名称必须由用户提供**——Agent **绝对禁止**根据品牌名称、行业特征等信息自行编造检查项
> 2. **每个自定义字段的类型必须经用户明确确认**——Agent **绝对禁止**根据字段名称的语义自行推断字段类型
> 3. **交互必须使用自然语言对话**——**禁止使用 `ask_question` / `ask_human` 等表单工具**来收集或确认字段信息，必须通过普通对话消息与用户交互

### 为什么禁止编造检查项？

Agent 会根据品牌名称做语义推理（如"爱乐美式汉堡" → 餐饮行业 → 臆测"门口环境卫生/收银台情况/每日菜品沽清"），但实际上：
- 用户心中有自己的巡检标准，Agent 编造的检查项**必然不准确**
- 用 `ask_question` 表单预填了错误的检查项后，用户**无法在表单中输入自己想要的字段**，只能被迫接受或放弃
- 这会导致**极差的使用体验**——用户根本没有机会提供正确的检查项

### 为什么禁止推断字段类型？

Agent 会根据字段名称做语义推理（如"整洁度" → 判断题 → `singleSelect`），但实际上用户可能希望店长**拍照上传**并由 AI 自动审核，而非简单勾选。这种推断会导致：
- 巡检字段被错误地建成 `singleSelect` 而非 `attachment`
- AI 审核字段无法创建（因为 `ai_review` 仅对 `attachment` 类型生效）
- 丧失 AI 自动审核能力，巡检退化为人工勾选

### 正确做法（两步对话式交互）

**第一步：收集检查项名称**——如果用户只说了"创建 XX 巡店任务"但没给出检查项，**必须先用自然语言对话询问**：

```
请告诉我这次巡店需要检查哪些项目？
例如：鲜食柜陈列、收银台整洁度、客流情况……
您可以直接列出所有检查项名称，我来帮您配置。
```

**绝对不要**自己编造检查项名称然后反问用户"是否确认"。

**第二步：确认字段类型（条件硬停）**——根据用户提供的信息完整程度，有两种路径：

**路径 A（信息充足，直接 preview）**：如果用户在请求中**已明确提供了字段名称和类型**（如"检查项有 XX、YY，每项需要拍照并AI审核"），Agent 应**直接跳到第三步执行 `template preview`**，无需再单独确认字段配置。用户已经说清楚了，不要反复确认浪费交互轮次。

**路径 B（信息不充足，先确认再 preview）**：如果用户只列出了检查项名称但**没有明确字段类型**，Agent 需以表格形式展示建议的字段配置，等用户确认后再进入第三步。

> **核心原则：只确认一次。** `template preview` 的完整预览就是最终确认环节，
> 不要在 preview 之前再加一轮多余的确认。减少交互轮次是好的用户体验。

**第三步：执行 `template preview` 获取完整预览（含派发消息模板）**——Agent **必须**：

1. 执行 `template preview --name "..." --custom-fields '[...]' --scene <场景>`
2. CLI 会输出 `status: "pending_confirm"` 的 JSON，其中包含：
   - `user_facing_preview`：**格式化好的完整确认文本**（配置概要 + 派发消息模板）
   - `dispatch_message_template`：**根据场景自动生成的派发消息模板**（完整 Markdown）
3. Agent **必须将 `user_facing_preview` 的完整内容【原封不动】展示给用户**（禁止精简、省略或改写）
4. 等待用户确认，或根据用户修改意见调整后重新执行 `template preview`

**第四步：用户确认后执行 `template create` 正式创建**：

```bash
template create --name "..." --custom-fields '[...]' --dispatch-message "..." [其他参数]
```

其中 `--dispatch-message` 的值来自第三步 `template preview` 输出的 `dispatch_message_template`。

> [!CAUTION]
> **`template preview` 必须带 `--scene` 参数**：巡店场景传 `--scene inspection`，早会场景传 `--scene morning-meeting`，
> 盘点场景传 `--scene inventory`。不传 `--scene` 则使用通用默认模板（可能不够贴合场景）。
>
> **严禁跳过 `template preview` 直接执行 `template create`**——如果 Agent 跳过预览步骤，
> 用户将**完全看不到派发消息模板**，也就无法确认或修改。这违反了"用户必须看到才能确认"的原则。
>
> **只确认一次原则**——`template preview` 展示的完整预览就是唯一的确认环节。
> 如果用户已在请求中明确了字段名称和类型，Agent 应直接执行 preview，不要在 preview 之前多加一轮确认。
> 多余的确认会浪费用户时间，严重影响体验。

**默认偏向 `attachment` + `ai_review`**——对于巡检场景中的检查项，默认建议 `attachment`（拍照上传 + AI 审核）。只有用户明确表示"不需要拍照"或"只需勾选"时才用 `singleSelect`。

### 禁止的行为

- ❌ 用户只说了"创建巡店任务"，Agent 自己编造"门口环境卫生/收银台情况"等检查项
- ❌ 使用 `ask_question` / `ask_human` 等表单工具来收集或确认字段信息
- ❌ 把 Agent 编造的检查项预填到表单中让用户确认
- ❌ 根据字段名含"照片/图片"就用 `attachment`，不含就用 `singleSelect`
- ❌ 根据字段名的语义（如"是否""整洁度""规范"）推断为判断题用 `singleSelect`
- ❌ 不向用户展示字段类型就直接创建
- ❌ **跳过 `template preview` 直接执行 `template create`（用户看不到消息模板）**
- ❌ **执行 `template preview` 时不带 `--scene` 参数（导致消息模板不贴合场景）**
- ❌ **不展示 `user_facing_preview` 完整内容就直接创建（精简/省略/改写均视为违规）**

---

<a id="H11"></a>
## H11. `dispatch init` 后必须验证 AI 审核字段创建结果

> [!CAUTION]
> 当模板包含 `ai_review: true` 的字段时，`dispatch init` 完成后 Agent **必须验证** AI 审核字段是否创建成功。

**为什么？** AI 审核字段的创建依赖多个步骤（获取 fieldId → 构建 aiConfig → 调用 API），任何一步出错都可能导致创建失败。代码中有降级策略（失败→纯文本字段），但如果连降级都没触发（如参数不正确），就什么都不会创建。Agent 不能把技能当黑盒——必须验证关键结果。

**正确做法**：

1. `dispatch init` 成功后，检查输出日志中是否有 AI 审核字段相关的警告或错误
2. 如果模板包含 `ai_review: true` 的附件字段，主动告知用户 AI 审核字段的创建状态：
   - 成功：「✅ 已为 X 个检查项创建 AI 审核字段」
   - 降级：「⚠️ AI 审核字段创建失败，已降级为纯文本字段，你可以后续在 AI 表格中手动升级为 AI 字段」
   - 缺失：「❌ 未检测到 AI 审核字段，可能需要手动补建」
3. 如果需要手动补建 AI 审核字段，必须先通过 `dws aitable field list` 获取附件字段的 `fieldId`，确保 `aiConfig.prompt` 中的 `fieldRef` 正确引用了对应附件字段

---

<a id="H13"></a>
## H13. Agent 绝对禁止手动拼接/猜测/硬编码表单分享链接

> [!CAUTION]
> 表单分享链接（`form_url`）**只能**通过以下两种方式获取：
> 1. `dispatch init` 自动提取（内部调用 `extract_form_share_url`）
> 2. 用户手动复制粘贴（最终降级方案）
>
> Agent **绝对禁止**以任何理由自行拼接、猜测或硬编码表单 URL。

### 为什么？

Agent 在自动提取失败后，会尝试根据 `shareUuid` 或 `baseId/tableId/viewId` 等信息"帮忙"手动拼接链接，但这些拼接**必然出错**：

- `shareUuid` 的正确拼接格式是 `https://docs.dingtalk.com/notable/share/form/{shareUuid}?source=link`，Agent 容易错误拼接成 `alidocs.dingtalk.com/i/notable/...` 或其他格式
- `baseId`/`tableId`/`viewId` **无法推导出** `shareUuid`，这是两套独立的标识体系
- 错误的链接会被派发给店长，造成**不可撤回的业务事故**（已发通知无法撤回）

### 唯一合法的链接获取路径

```
dispatch init
  └→ _reuse_or_create_form_view()
       └→ _extract_form_link(detail)          ← 从视图 API 响应中提取
            └→ extract_form_share_url(detail)  ← fallback: 从 formInfo.shareUuid 拼接
```

如果 `dispatch init` 返回的 `form_url` 为空，按 [H12](#H12) 的流程处理（引导用户发布表单 → 重新 init → 最终降级让用户粘贴）。

### 禁止的行为

- ❌ Agent 根据 `shareUuid` 自行拼接 URL（即使格式看起来"正确"）
- ❌ Agent 根据 `baseId`/`tableId`/`viewId` 推导/拼接 URL
- ❌ Agent 参考钉钉文档 Base 通用 URL 格式（如 `alidocs.dingtalk.com/i/nodes/...`）拼接
- ❌ Agent 在 `dispatch init` 失败后"帮忙修复"链接而不重新执行 init
- ❌ Agent 在对话中输出未经系统验证的表单 URL 给用户

### 幻觉根因分析（Agent 必读）

Agent 反复出现拼接 `/i/notable/share/form/` 或使用 `alidocs.dingtalk.com` 域名的错误，根因如下：

1. **代码库中存在 `/i/nodes/` 路径**（Base 编辑链接），Agent 将其与表单链接路径混淆，
   "创造"出不存在的 `/i/notable/` 路径
2. **`alidocs.dingtalk.com` 是内网域名**，代码库中已全部替换为 `docs.dingtalk.com`。
   如果 Agent 在输出中使用了 `alidocs` 域名，说明是幻觉而非脚本输出
3. **表单链接和编辑链接是两套完全独立的 URL 体系**，不可混用：
   - 表单分享链接：`https://docs.dingtalk.com/notable/share/form/{shareUuid}?source=link`
   - Base 编辑链接：`https://docs.dingtalk.com/i/nodes/{baseId}?iframeQuery=...`

> **自检规则**：Agent 在输出任何钉钉 URL 之前，必须自检：
> - ❌ 包含 `/i/notable/` → 不存在的路径，停止输出
> - ❌ 包含 `alidocs.dingtalk.com` → 内网域名，已被禁用
> - ❌ 包含 `/i/nodes/` 但用于表单场景 → 类型混淆

### 代码防护机制

代码中已内置链接格式校验（`_validate_form_link`），会在链接提取和拼接时自动拦截：
- 包含 `/i/notable/` 的链接 → 直接报错
- 包含 `alidocs.dingtalk.com` 的链接 → 直接报错
- 包含 `/i/nodes/` 的链接用于表单场景 → 直接报错

### 正确的补救流程

1. `dispatch init` 返回 `form_url` 为空 → **按 H12 流程处理**，不要尝试手动修复
2. 用户确认表单已发布 → **重新执行 `dispatch init`**，让系统自动提取
3. 仍然为空 → 要求用户手动复制分享链接，通过 `dispatch notify --form-url <链接>` 传入
4. **任何情况下 Agent 都不要自己"生成"一个链接**

---

<a id="H14"></a>
## H14. dispatch notify 发送范围必须与用户意图精确匹配

> [!CAUTION]
> `dispatch notify` **必须显式指定发送范围**，不带范围参数 CLI 直接报错拒绝执行。
> `--all` / `--target-store-ids` / `--tags` / `--only-pending` **四选一**（互斥）。

### 决策规则

| 用户表述 | 必须使用的参数 | 禁止行为 |
|---------|--------------|---------|
| "通知**所有**门店" / "派发给**全部**" / 未指定范围 | **`--all`** | ❌ 禁止不带范围参数（CLI 会报错） |
| "只通知**XX店**" / "发给**某某店长**" / 指定了具体门店或人 | **`--target-store-ids <store_id>`** | ❌ 禁止用 `--all` 代替导致全量派发 |
| "通知**未填写的**" / "催一下没交的" | **`--only-pending`** | ❌ 禁止不加此参数导致重复通知已完成的人 |
| "通知**华北区**的门店" / 按标签 | **`--tags <标签>`** | ❌ 禁止用 `--all` 代替导致全量派发 |

### 操作流程

当用户指定了具体门店或店长时：

1. **先查 store_id**：通过 `store list` 或 `store list --query <关键词>` 找到对应门店的 `store_id`
2. **再带参派发**：`dispatch notify --task-id <ID> --target-store-ids <store_id1>,<store_id2>`

当用户说"通知所有门店"或未指定范围时：

- 使用 `--all` 显式全量派发：`dispatch notify --task-id <ID> --all`

### 严重后果

在用户指定了具体发送对象时使用 `--all` 会导致**所有门店的店长同时收到通知**，
这属于**骚扰行为**，且已发送的消息**不可撤回**。

---

<a id="H15"></a>
## H15. 派发/提醒消息必须且只能通过 dispatch notify 发送

> [!CAUTION]
> 向店长发送任何业务消息（派发通知、催办提醒等）**必须且只能**通过
> `dispatch notify` 命令完成。**绝对禁止**直接调用 `dws chat message send`
> 手动构造消息并发送给店长。

### 禁止的行为

- ❌ 直接调用 `dws chat message send --open-dingtalk-id <ID> "消息内容"` 向店长发消息
- ❌ 用户提供了消息格式后，手动拼接消息内容并通过 `dws chat message send` 发送
- ❌ 认为"dispatch notify 太复杂/太慢"而选择直接发消息"先跑通"
- ❌ 在 `dispatch init` 后不经过 `dispatch notify` 就直接发消息

### 为什么禁止

`dispatch notify` 内部封装了以下关键逻辑，直接 `dws chat message send` 会**全部丢失**：

1. **通知记录写入**：每条通知写入通知明细表，用于后续查询、催办、统计
2. **去重保护**：`notification_id` 唯一键去重，防止重复通知
3. **冷却机制**：半小时内不重复骚扰同一店长
4. **表单链接个性化**：为每家门店生成带 prefill 参数的专属表单链接
5. **DispatchSummary 统计**：输出 success/failed/skipped 汇总，用于向用户报告结果
6. **任务状态回写**：更新任务记录的派发日志和状态

### 正确流程

当用户提供了消息格式/模板要求时，**必须按以下顺序执行**：

1. **先写入模板**：`template update --template-id <ID> --dispatch-message-file <TEMP>/msg.md`
2. **再派发**：`dispatch notify --task-id <ID> --all`（或 `--target-store-ids`）
3. `dispatch notify` 内部会自动读取模板的 `dispatch_message` 字段，渲染占位符后发送

**绝对禁止跳过步骤 1 直接用 `dws chat message send` 手动发消息。**
