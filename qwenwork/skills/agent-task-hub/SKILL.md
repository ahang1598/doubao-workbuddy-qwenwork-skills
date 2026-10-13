---
name: agent-task-hub
displayName: 千问办公任务台账
name_en: agent-task-hub
description: |
  把千问办公的 agent 任务沉淀到钉钉 AI表格，形成跨 agent、跨窗口的「任务台账 + 交接登记表」。 支持创建/初始化个人台账（定时增量同步）与团队接续台账（仅 handoff 触发写摘要，保护隐私）。 当用户需要创建团队 Agent 台账、创建个人任务台账、定时沉淀/同步任务、交接、交接分支/模块/任务给某人、接手交接任务、认领任务、续接、接着做、开新会话续接、handoff、resume、查询待接续任务时使用。
description_en: Sync QwenWork agent tasks to a DingTalk AI table as a cross-agent task ledger and handoff register. Use for task sync, handoff, resume, or looking up resumable tasks.
argument-hint: 任务关键词或交接对象
install_source: official
install_method: download
skill_id: official_o3CIrQWe
enabled_at: 1791893823613
version: 1.0.0
name_zh: 千问办公任务台账
---

# Agent Task Hub

把千问办公的 agent 任务沉淀到钉钉 AI表格，形成跨 agent、跨窗口的统一看板与交接登记表。一个 skill，两种模式，两个触发分支。

**不要硬编码任何 baseId / tableId / fieldId**。这些是实例相关、团队相关的，运行时现场解析；本 skill 只规定标准表名与字段名。

## 适用场景

- **个人任务沉淀**：把你（以及本机其他 agent，如 codex/qoder/claudecode）的任务自动同步到钉钉 AI表格，形成可检索的任务台账——标题、状态、产出物附件、一句话摘要一目了然，不再散落在各会话里。
- **团队任务交接**：把进行中的任务交接给指定同事或放到团队群待认领。交接摘要（目标/当前状态/已完成/下一步/关键决策/风险）+ 产出物附件 + 钉钉通知卡片一步到位，接手人新开会话说一句话即可续接。
- **跨窗口续接**：会话上下文满了或换了台机器，凭台账里的任务ID与交接摘要接着做，不从头开始。

## 前置依赖

本技能依赖 **dws**（钉钉全产品 CLI，内置连接器）读写钉钉 AI表格、通讯录与群消息。

- 用途：创建/读写 AI表格台账、上传附件、搜索同事 userId、发送安装指引、创建通知自动化。
- 类别：builtin。
- 认证方式：PAT 行为授权（首次调用 dws 时由用户在客户端完成授权）。

### Step 0 — dws 就绪性检查（每次执行前必做）

1. 前台跑 `dws profile list --format json` 探活。
2. 根据返回分支处理：
   - 正常返回账号列表 → 直接进入业务流程。
   - 认证失败/无账号 → 输出提示语引导用户在客户端完成 dws 授权，**暂停等待用户操作，不要重试轮询**。
   - 用户明确拒绝授权 → 礼貌说明「没有钉钉连接我无法读写台账」，建议改用导出本地 Markdown 的替代方案，不要硬闯。

## 首次使用：先确定模式（必须用 AskUserQuestion 问用户）

问：这个台账用于什么场景？选项：

1. **个人台账（推荐）**：每日同步我的千问办公任务 + 本机各 agent 任务（可自选同步范围）。handoff 走团队台账，个人台账只做同步。
2. **团队接续台账**：只在 handoff 触发时写交接摘要，**不做定时同步**（保护个人隐私），团队共用一张表。

如果用户意图已经明确（例如“创建团队台账”“重新生成团队台账”“创建个人台账”“同步我的任务台账”），直接进入对应模式，**不要为了走流程再二次确认**。只有模式不明确时才 AskUserQuestion。

## 意图分支边界（非常重要）

**初始化/分享分支**和**交接分支**必须分开：

- 用户说“创建团队台账 / 新建团队台账 / 分享团队台账 / 分享给某人 / 发到群里 / 给同事安装使用”时，属于**团队台账初始化/分享**，只做建表、补字段、建自动化、授权、安装指引；**绝不创建父任务记录，也绝不创建 `【交接】` 子记录**。
- 用户说“把这个任务交接给 X / 这个任务让 X 接着做 / handoff 给 X / 续接当前任务 / 接着做这个任务”时，才属于**交接分支**，才允许读取 `operations.md` 并创建父任务/子记录。
- 用户说“交接分支B 给 X / 把 A 模块交接给 X / 分支 B 给 X”这类省略句时，默认也属于**交接分支**：应把当前任务中对应工作包写入团队台账交接子记录，而不是只生成一段交接口径。只有用户明确说“只帮我写交接文案/口径/说明，不写台账”时，才只输出文本。
- “分享给 X”只表示给 X 文档权限或安装指引，不等于“把当前任务交接给 X”。
- “发到群里 / 分享到群里”若没有明确群名或 `openConversationId`，不要搜索一堆候选群后猜测发送；直接返回“需确认群名/群 ID”。只有用户给出明确群名或唯一候选时才发真实群消息。

## 命名规则（区分个人/团队文档）

- 个人 Base 名称：`千问办公个人任务台账`
- 团队 Base 名称：`千问办公团队接续台账`
- 表名保持稳定：`任务台账`
- 兼容旧名：查找已有台账时同时搜索旧名 `千问办公任务台账`，但新建时必须使用上面的个人/团队专用 Base 名称。

## 标准 Schema（个人/团队两套，字段名稳定，fieldId 运行时用 `dws aitable field get` 查）

**个人台账**（同步用，一条任务一行，不含交接字段）：

任务标题(text)、状态(singleSelect：进行中/等待确认/已完成/已取消/失败/中断/暂停)、任务类型(singleSelect，选项按任务实际内容动态生成，初始仅「其他」兜底)、优先级(singleSelect：高/中/低)、产出物(attachment)、工作文件(attachment)、Agent类型(singleSelect：qwenwork/codex/qoder/claudecode/qoderwork/其他)、任务ID(text)、创建时间(date)、更新时间(date)、最后同步时间(date)、创建人(user)。

**团队台账**（交接用，在个人基础字段上追加交接字段）：

任务标题(text)、任务组(text，隐藏分组键)、交接状态(singleSelect：未交接/待认领/交接中/已接手/已完成)、任务交接对象(user)、状态(singleSelect：进行中/等待确认/已完成/已取消/失败/中断/暂停)、一句话摘要(text)、交接摘要(text)、产出物(attachment)、工作文件(attachment)、Agent类型(singleSelect：qwenwork/codex/qoder/claudecode/qoderwork/其他)、任务ID(text)、通知文案(richText)、创建人(user)、父记录(unidirectionalLink 自关联，multiple=false)。

- 去重键 = 「任务ID + Agent类型 + 创建人」联合，跨机器/跨实例不撞；旧表若仍叫「千问办公ID」，先兼容读取，后续迁移时改名为「任务ID」。
- `qwenwork.tasks` 返回的 `chatId` 写入「任务ID」、Agent类型写 `qwenwork`；本机 probe 返回的 `chatId` **去掉 agent 前缀写裸 ID** 入「任务ID」（前缀只用于 probe 命令寻址，不写进台账）、`agent` 写入「Agent类型」。
- 「创建人」每次同步/交接都填当前登录用户；「任务交接对象」**只写交接子记录/待认领记录**，父任务不要写交接人，避免父子两条记录都触发通知；个人台账不建此字段。
- 「父记录」是**团队台账**的自关联 unidirectionalLink（linkedTableId=本表，multiple=false），每条子记录只能挂一个父任务；一个父任务可通过多条子记录分发给多人。个人台账不建。
- 「任务组」是团队台账的隐藏分组键，值为 `<父任务标题>|<任务ID后6位>`，父与所有子同值；Grid 用它分组，父不会孤立。
- 团队台账的「状态」只属于接手后的工作进度：待认领 / 交接中（未接手）时父与子都不写「状态」，接手后由接手人在子记录回填，父在所有子完成后才写「已完成」。
- 「交接状态」「交接摘要」**仅团队台账**存在；个人台账不做交接，不建这俩字段。

## 个人模式

个人台账的**完整创建命令序列**见 [references/create-ledger.md](./references/create-ledger.md)，逐条执行、不要自由发挥。摘要：

1. 找或建 Base + 建「任务台账」表（个人 12 字段，无交接字段）。
2. `table get` 拿 fieldId，`memory` 记住 baseId + tableId + fieldId 映射。
3. 探测本机 agent（`agent_discovery.py`）+ AskUserQuestion 确认同步范围：**同步哪些 agent**（首选项=探测到的推荐集，千问办公默认含在内）+ **时间窗口**（首选项=「近一天」推荐默认）+ **产出物/工作文件策略**（全部上传 / 只传 ≤10MB / 不同步，建台账时问一次并记住）。`memory` 记住三项。任务类型、优先级不问，由同步时模型自动打标。
4. 用内置 cron 建每日定时同步（默认每天一次，不要分钟级）。
5. 按需更新：用户说「更新台账 / 同步 agent 任务 / 收集本地任务」时，手动跑一次「定时同步流程」。
6. 验证：`workflow list` 应为空（个人台账不建任何自动化）。

个人模式不交接给他人——交接/续接/认领一律走团队模式 + 团队台账。

## 团队模式

团队台账初始化/分享在确认用户意图后，优先用本 skill 自带脚本生成确定性产物和前台命令计划：

```bash
python3 scripts/create-ledger.py team plan --share-users <userId列表> [--base-id <已有BASE_ID>] [--group-cid <团队群cid>]
```

脚本只做本地算账：生成团队字段 JSON、父字段配置、自动化 DSL 渲染入口和 `foreground-dws-plan.md`；**绝不调用 `dws`**。随后由 agent 按 plan 逐条以前台 `dws ...` 命令执行建/复用 Base、建/复用「任务台账」表、补「父记录」字段、创建自动化、授权、回读验证；**不会创建任务父记录或 `【交接】` 子记录**。只有需要排查字段/自动化细节时，才按 [references/create-ledger.md](./references/create-ledger.md) 分步执行。摘要：

1. 若用户明确说“重新生成/新建团队台账”，直接新建；否则问用户团队是否已有接续表格（已有→用户给 baseId；没有→新建）。
2. 建 Base + 建「任务台账」表（团队字段）+ 补「父记录」字段。
3. `table get` 拿 fieldId，`memory` 记住坐标。
4. 建表后处理共享：用户已指定共享对象时直接分享；未指定时才问「共享给谁」（人/群/暂不共享）。分享后返回安装指引草稿；只有用户明确要求发送时，才真实发消息或附件给对方。
5. **必须补齐自动化（硬规则）**：`workflow list` 检查，缺则建「交接任务通知」；有团队群才建「待认领群通知」。
6. 验证：`workflow list` 确认交接通知 RUNNING。
7. 若本次只是创建/分享团队台账，到这里就结束；不要继续创建当前 Codex 任务父记录，也不要给共享对象创建 `【交接】` 子记录。

**隐私红线（硬规则）**：团队模式**绝不建定时同步任务**，只在用户明确说"交接/续接/接着做"时写交接摘要。
交接时走「交接流程」。

## 硬约束（两种模式都遵守）

0. **执行体验优先**：默认少说、快做。用户可见进度只在阶段切换、等待超过约 30 秒、需要用户决策、或最终结果时输出；不要逐条播报每个命令。最终回复用“已完成 / 未做 / 需确认”三块即可。
1. **dws 必须前台直跑**：所有需要 dws 鉴权的命令必须由 agent 以前台命令直接执行，命令首词为 `dws`；禁止 Python subprocess、run_in_background、nohup、`&`、shell 脚本批跑或其它包装。Python 只能做本地算账和产物准备（字段 JSON、record JSON、workflow DSL、diff、文件 size/mime 等），不能直接调用 dws。只读本机 agent 探测脚本（python3，不依赖 dws auth）可后台跑，避免长扫描阻塞其它任务。
2. **附件禁用钉盘**：附件字段走 `dws aitable attachment upload` 三步（拿 uploadUrl+fileToken → curl PUT → fileToken 写入），钉盘 drive 的 fileId 写不进 attachment 字段。
3. **幂等去重**：以「任务ID + Agent类型 + 创建人」为联合键，先读台账已有 (任务ID, Agent类型, 创建人) 集合再 diff，跑多少次不重复。旧表若仍为「千问办公ID」，读取时按「任务ID」等价字段兼容。
4. **状态映射**：qwenwork status → 台账「状态」的映射表见 [references/task-pull.md](./references/task-pull.md)，不要凭印象转。
5. **按需读参考**：不要启动时把所有 references 都读完。按分支读取最少必要文件：建表读 `create-ledger.md`；共享给人/群时读 `create-ledger.md`（步骤 6）；建自动化时读 `workflow-notify.md` 和模板；附件/人员写入时读 `people-attachment.md`；同步任务时读 `task-pull.md` 和 `agent-tasks-listing.md`；只有明确交接/认领/接手时才读 `operations.md`，创建/分享团队台账时不要读。
6. **确定性操作逐条执行**：交接/认领/接手/附件/建自动化的确切命令在 [references/operations.md](./references/operations.md)，逐条直接执行，不许改写、省略或"自由发挥"。
7. **团队台账必须附自动化**：交接通知自动化必建；建完用 `workflow list` 校验存在，缺则补。个人台账不建任何自动化（个人只同步，不交接）。
8. **并行边界**：写操作（建 Base、建表、建字段、建/改记录、建自动化、授权）保持串行并回读确认；互不依赖的只读查询可以并行，例如当前身份查询、人员搜索、已有台账搜索。
9. **交接/接手/认领前必须重新加载 skill 并现查坐标**：任何交接/认领/接手动作，先 invoke `agent-task-hub`、按 [references/operations.md](./references/operations.md)「前置：解析坐标」用 `dws aitable table get` 现场拿 baseId/tableId/fieldId，再逐条执行；禁止凭上下文记忆里的旧坐标、旧字段名或旧流程直写。尤其禁止没跑 `check-handoff-ready.py` 就先 `record create`、再回头补「通知文案」（会发出空通知卡片且无法重发）。

## 定时同步流程（仅个人模式）

> 默认只同步「近一天」的任务，不做全量回扫；时间窗口以个人模式第 3 步用户选择为准，未选时默认近一天；选了全量或用户明确要求全量时才翻页拿全量。

1. 读 `qwenwork.tasks`，**按个人模式第 3 步选定的时间窗口过滤（默认近一天，按 `updatedAt`）**，选了全量才翻页拿全量；并**跳过标题含「定时同步」的同步任务自身**（cron 触发的自动化同步无业务产出，避免台账被刷屏）。命令与返回结构见 [references/task-pull.md](./references/task-pull.md)。
2. 本地 agent 任务拉取：用 `agent_task_probe.py --list --agent <选中的agent> --since-days <选定天数，默认 1>` 只拉个人模式第 3 步用户选中的 agent、选定时间窗口（`--since-days` 是 probe 的参数，`agent_discovery.py` 不支持），**不要拉全部**；用 `run_in_background` 后台执行，完成通知后再继续。输出对齐 qwenwork.tasks 且带 `outputFiles`（path/exists）。见 [references/agent-tasks-listing.md](./references/agent-tasks-listing.md)。
3. 读台账已有「任务ID + Agent类型 + 创建人」集合，diff 决定 create/update。字段写入值格式与高频错误见 [references/aitable-write.md](./references/aitable-write.md)。
4. 写「创建人」= 当前登录用户（`dws contact user get-self` 拿 corpId + `dws aisearch person` 拿 userId，写 user 字段）。见 [references/people-attachment.md](./references/people-attachment.md)。
5. 给**每条**任务打标「任务类型」和「优先级」（必做，不再只挑高价值任务）：读标题 + 详情，任务类型按该任务的实际内容生成贴合分类（不要固定成开发/调研/文档，singleSelect 写新 name 自动建选项），优先级在 高/中/低 里选。
6. 产出物上传（必做，不是可选）：本机 agent 任务用 `agent_task_probe.py --detail "<agent>:<sessionId>"` 拿 outputFiles；千问办公任务读 `qwenwork.tasks.<chatId>` 详情，从 Write/Edit toolCalls 解析写入文件路径。过滤 outputs/、uploads/、临时目录后逐文件用 Bash 校验存在，存在才上传附件写「产出物」。
7. 工作文件（源码/工作文件，同样必做）：优先用 probe 的 outputFiles（`--detail` 才带 exists=true）或上面解析出的源文件路径，上传写「工作文件」。附件三步见 [references/people-attachment.md](./references/people-attachment.md)；拿不到文件时留空。
8. 刷新「最后同步时间」。

## 交接流程（仅团队模式，必须用团队台账）

触发词：交接、续接、接着做、开新会话续接、handoff、resume、继续做 XX。

> 确切 bash 命令见 [references/operations.md](./references/operations.md)，下面只是执行顺序。

0. 确认用的是**团队台账**坐标；**不要用个人台账**。
1. 确定「当前任务」的任务ID（qwenwork 为裸 chatId；本机 agent 为 probe chatId 去掉前缀的裸 session ID；前缀不得写进台账）。若用户指另一个 qwenwork 任务，先从 `qwenwork.tasks` 拿到其 chatId。
2. 用「任务ID + Agent类型」在团队台账**精确匹配**父记录（按 fieldId 精确过滤，**不靠关键词搜标题**）。
   - 命中 → 取该父 recordId。
   - 未命中 → 先为当前任务建一条父记录（任务ID=当前裸 ID 不带前缀，Agent类型=当前 agent），再继续。
3. 交接对象：用户指定目标人 → 交接中；未指定 → 待认领。
4. 先扫描并上传产出物/工作文件（operations.md §0c：只上传实际存在的文件），再由发起人创建 `【交接】` 子记录（单个父记录链接、交接对象、短摘要、任务组、交接状态、完整交接摘要、通知文案、产出物/工作文件附件；任务ID/Agent类型 留空，留给接手人回填），最后更新父任务汇总状态——命令见 operations.md §0c/§1/§2。
   - 创建子记录前必须确认「父记录」字段唯一；如线上表出现多个同名「父记录」，先停止并提示清理/选择，不要任选字段写入。
   - 子记录标题用 `【交接】<父任务标题>`；同时写「一句话摘要=180字以内短说明」「任务组=与父同值（父任务标题|任务ID后6位）」「交接摘要=六块+元信息+子结构完整摘要（见 templates/handoff-summary.md）」「产出物/工作文件=已有 fileToken 附件」。创建前必须跑 `scripts/check-handoff-ready.py`（指定人 `handoff`、待认领 `claim`；开发任务加 `--dev`）让它生成 `--cells-out` 完整 cells（通知文案已内嵌），随后 `record create --records-file` 读该文件创建；PASS 前禁止 `record create`，禁止先建记录再补通知文案；不写「状态」（未接手无状态）。
   - 开发任务在「交接摘要」的交接元信息块里必填仓库 URL + 分支 + 基线 commit，并在【已完成/已产出】里给交付物清单和验证结果；缺一即摘要不合格，独立字段不建。
   - 父任务只做汇总：更新「交接状态/交接摘要」即可，不要写「任务交接对象」。
5. 通知自动化发给交接对象；交接通知必须由 `WhenRecordCreated` 在子记录创建时触发，消息正文引用「通知文案」richText 字段（markdown 渲染，含接手方式 prompt），不要手工提示接手人回填。父记录更新只做汇总，不作为通知触发兜底。
6. 接手人回填子记录时必须同时写自己的「任务ID + Agent类型」；子记录完成后，只有当同父所有子记录都完成时，父任务才标记「已完成」。

**子记录由谁创建（明确约定）**：由**发起交接的人**在交接时创建待接手子记录；**接手的人**接手后只回填（自己的任务ID + Agent类型 + 状态 + 交接状态），不自己新建子记录。

## 接手流程（仅团队模式，接手人执行）

触发词：接手、接续、继续这个交接任务、使用 agent-task-hub 接手「任务标题」。

1. 优先定位交接子记录：
   - 用户提供记录链接/rowUrl → 从链接解析 recordId，精确接手该子记录。
   - 用户说 `使用 agent-task-hub 接手「<任务标题>」` → 在团队台账里查「任务交接对象=当前用户」且「交接状态=交接中/已接手前」的子记录，再用任务标题关键词匹配。
   - 唯一命中 → 接手；多条命中 → 让用户选择；未命中 → 提示用户点击通知卡片「去查看」后把记录链接发给 agent。
2. 接手时执行 operations.md §4：把接手人的「任务ID + Agent类型」回填到该子记录，状态/交接状态更新为「已接手」，再联动父任务为「已接手」。
3. 接手人不要新建 `【交接】` 子记录；接手只更新发起人已经创建的那条子记录。

## 认领流程（仅团队模式，团队台账）

1. 在**团队台账**查「交接状态=待认领」的任务。
2. 成员说「认领 XX」→ 定位待认领记录：优先解析通知卡片链接的 recordId；标题搜索同时命中父与【交接】子时认领子记录（父是汇总载体不得被认领；无父无子的顶层孤儿可直接认领本身）→ 按 operations.md §3 写「任务交接对象」=认领人、「交接状态」=交接中，并联动父记录为「交接中」。
3. 后续接续走「交接流程」的接手/完成逻辑（operations.md §4/§5）。

认领只用于“本人主动认领”。如果发起人/管理员要把待认领任务指派给另一个人，不要直接更新旧待认领记录的「任务交接对象」；应新建一条指定人的 `【交接】` 子记录，让 `WhenRecordCreated` 通知自动化正常触达。

## 交接摘要模板

摘要必须让接收方**无需回到本地、无需原始对话**就能独立续接。固定六块外壳 + 头部「交接元信息」+ 尾部「接手方式」，六块内部含已确认/推断/未知、交付物清单、验证、先读材料等子块。**开发任务必填仓库/分支/commit、交付物清单、验证结果，缺一即摘要不合格**；生成后用 `scripts/validate-handoff-summary.py`（开发任务加 `--dev`）自检通过再写台账。完整结构与措辞见 [templates/handoff-summary.md](./templates/handoff-summary.md)。

**产出物引用规则**：一律引用台账「产出物」字段的附件（文件名/大小/OSS 链接或 fileToken），**不要引用本地文件路径**——接收方可能不在同一台机器，也可能是其他品牌的 agent。只有确认接收方就是本机、本工具时，才可附加本地路径并注明"仅本机有效"。

## 常见错误与恢复

- **dws 认证失败 / PAT 过期**：回到 Step 0 重新走授权分支，引导用户在客户端完成授权；不要绕过或静默重试。
- **`record create/update` stdout 为空**：可能已写成功（已实测）。用 `record query` 回读确认后再决定是否重跑，**不要盲目重跑**（会产生重复记录）。
- **richText 字段直写纯文本被拒**（InvalidArgument: value is invalid for field）：「通知文案」等 richText 字段必须写 `{"markdown":"..."}` 结构，不能直接传字符串。
- **base/table 404（getDentryDTO returns null）**：台账 Base 被改名/删除/移权。重新 `base search` 定位当前 Base，禁止继续用记忆里的旧坐标。
- **建表后字段/自动化不生效**：先 `table get` 回读 fieldId、`workflow list` 回读自动化状态，以线上实际为准，不要凭创建返回值推断。
- **通知卡片正文为空**：交接子记录创建时没写「通知文案」。该自动化只在创建瞬间触发一次，补写不重发；必须走 `check-handoff-ready.py --cells-out` 让通知文案随创建原子写入。

## 验证

- 同步：跑一次后台账记录与 `qwenwork.tasks` 状态一致，重复跑不产生重复行。
- 附件：`record query` 回读「产出物」能看到附件 filename/size/url。
- 交接：新窗口仅凭摘要 + 附件引用 + 任务ID/Agent类型 能说清"做到哪、下一步做什么"。
- 状态流转：发起交接后父任务=交接中、子记录=交接中；接手后子记录=已接手且写入接手人的任务ID/Agent类型，父任务=已接手；完成后若同父所有子记录均已完成，父任务=已完成。

## 目录结构（按生态接入白皮书规范）

- `SKILL.md` — 入口与执行流程
- `references/` — 长规则与领域知识（命令参考、字段规范、自动化 DSL 说明）
- `scripts/agent-tasks-listing/` — 本机其他 agent 任务探测脚本（可执行）
- `scripts/create-ledger.py` — 团队台账初始化/分享的本地产物与前台 dws 命令计划生成器，不调用 dws
- `scripts/render-workflow-dsl.py` — 自动化 DSL 模板渲染与占位符校验，建团队台账时优先使用
- `scripts/render-notice.py` — 通知文案（richText markdown）确定性渲染器，模板单一事实源，输出原样嵌入 cells；内置 sanitize 中和渲染器 autolink（裸写 .md/.py 文件名与裸 URL 包反引号、显式链接折叠）
- `scripts/validate-handoff-summary.py` — 交接摘要结构校验器（`check-handoff-ready.py` 的组件，开发任务加 `--dev`）
- `scripts/check-handoff-ready.py` — 交接前就绪检查 + 一次性生成完整 record-create cells（通知文案已随 cells 内嵌，输出 `--cells-out`），create 前必跑，PASS 前禁止建子记录
- `scripts/handoff-flow-selftest.py` — 本地交接状态机自测，不连接线上表
- `templates/` — 输出模板（交接通知 DSL、待认领群通知 DSL、交接摘要六块模板）
- `examples/` — 具体示例（团队台账交接通知 DSL 实例）

## 命令参考（references，按需读取）

- [references/create-ledger.md](./references/create-ledger.md) — 个人/团队台账创建的完整确定性命令序列（首选入口）
- [references/task-pull.md](./references/task-pull.md) — 千问办公 task 拉取：qw_query 查询、分页、详情、状态映射、幂等去重
- [references/aitable-write.md](./references/aitable-write.md) — AI表格字段写入值格式 + 高频错误
- [references/people-attachment.md](./references/people-attachment.md) — 创建人/任务交接对象（user 字段）获取与写入 + 产出物/工作文件（attachment）OSS 三步上传
- [references/workflow-notify.md](./references/workflow-notify.md) — 交接通知自动化（workflow-dsl/v1 确定性模板）
- [references/agent-tasks-listing.md](./references/agent-tasks-listing.md) — 本机其他 agent 任务探测脚本用法
- [references/operations.md](./references/operations.md) — 交接/认领/接手/附件/建自动化的确切 bash 命令
- [templates/](./templates/) — 交接/待认领通知 DSL、交接摘要模板
- [examples/](./examples/) — 团队台账交接通知 DSL 实例
