# 确定性操作命令（operations）

> 交接 / 认领 / 接手 / 完成 / 附件上传 / 建自动化 的**确切 bash 命令**。
> 执行原则：**逐条直接执行，不要改写、不要省略、不要"自由发挥"**。cells 的 key 一律是 fieldId，不是字段名。
> 下文出现的 `python3 scripts/...` 均以本 skill 安装目录为基准，执行前先 `cd` 到该目录。
> **所有坐标都不硬编码**：`<BASE_ID>`、`<TABLE_ID>`、`<...fieldId>`、`<corpId>`、`<userId>` 都是运行时变量，先执行「§前置：解析坐标」拿到真实值再逐条替换。

团队台账坐标：baseId=`<BASE_ID>`，tableId=`<TABLE_ID>`（当前实例的坐标由你们记忆/现场 `table get` 决定，文档只保留占位符）。

| 字段 | 运行时占位符 | 类型 |
|---|---|---|
| 任务标题 | `<任务标题fieldId>` | text |
| 任务组 | `<任务组fieldId>` | text |
| 状态 | `<状态fieldId>` | singleSelect |
| 任务ID（旧表可能仍叫千问办公ID） | `<任务IDfieldId>` | text |
| 任务交接对象 | `<任务交接对象fieldId>` | user |
| 创建人 | `<创建人fieldId>` | user |
| 交接摘要 | `<交接摘要fieldId>` | text |
| 通知文案 | `<通知文案fieldId>` | richText |
| 交接状态 | `<交接状态fieldId>` | singleSelect |
| 父记录 | `<父记录fieldId>` | unidirectionalLink |

新 schema 还包含「Agent类型」字段，占位符 `<Agent类型fieldId>`；若线上表已有该字段，执行前用 `table get` 解析到 fieldId，并在父记录/接手回填时一并写入 `qwenwork` / `codex` / `qoder` / `claudecode` / `qoderwork`。
「一句话摘要」字段占位符 `<一句话摘要fieldId>`，交接子记录必须写入不超过 180 字的短摘要，供台账列表检索用。「交接摘要」写六块+元信息+子结构完整摘要（结构见 templates/handoff-summary.md，开发任务必填仓库/分支/commit、交付物清单、验证）。「通知文案」与「交接摘要」在创建子记录前一起过 `scripts/check-handoff-ready.py`（开发任务加 `--dev`），PASS 后由该脚本把通知文案随其它 cells 一起生成到 `create-cells.json`，`record create` 直接读该文件；通知文案是自动化通知卡片的正文，必须与创建记录同一条 `record create` 原子写入。

## 前置：解析坐标

执行交接/认领/接手/完成/附件/建自动化前，必须先回读本表 schema，把上面所有占位符解析成真实 fieldId：

```bash
dws aitable table get --base-id <BASE_ID> --table-id <TABLE_ID> --format json
# 用返回的 fieldName 反查每个字段的 fieldId；找不到的字段按 create-ledger.md 补建后再解析。
```

执行交接前必须解析唯一的「父记录」字段：

```bash
dws aitable table get --base-id <BASE_ID> --table-id <TABLE_ID> --format json
# 找 fieldName=父记录 且 type=unidirectionalLink 且 linkedTableId=本表 的字段；新表应为 multiple=false。
# 只有 1 个：使用该 fieldId，记为 <父记录fieldId>。
# 有多个：不要继续创建子记录；先提示用户清理重复字段，或根据已有记录 linkedRecordIds 使用量选择 canonical fieldId。
# 没有：按 create-ledger.md 补建后再继续。
# 若唯一字段是 multiple=true，兼容写入但只传 1 个 linkedRecordId，并记录为待迁移。
```

user 字段值：`[{"userId":"<userId>","corpId":"<corpId>"}]`（单选也数组）
父记录字段值：`{"linkedRecordIds":["<父recordId>"]}`（父记录字段 multiple=false，只传一个父 recordId）
任务组字段值：`"<父任务标题>|<任务ID后6位>"`（父与子同值，用于分组；唯一性靠标题 + 后6位）。
「状态」只属于已接手后的工作进度：待认领 / 交接中（未接手）时父、子都不写「状态」，接手后才由接手人在子记录回填，父任务在所有子完成后才写「已完成」。

---

## 0. 精确匹配父记录 + 未命中先建父记录

### 0a. 用任务ID精确匹配（不搜标题）

```bash
dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> \
  --query "<当前任务ID>" --format json
# 命中后取 recordId 作为父 recordId；未命中走 0b
```

### 0b. 未命中先建父记录

```bash
dws aitable record create --base-id <BASE_ID> --table-id <TABLE_ID> \
  --records '[{"cells":{
    "<任务标题fieldId>":"<当前任务标题>",
    "<任务组fieldId>":"<任务组=父任务标题|任务ID后6位>",
    "<任务IDfieldId>":"<当前任务ID：裸 session ID，不带 agent 前缀>",
    "<Agent类型fieldId>":"<当前agent类型>",
    "<创建人fieldId>":[{"userId":"<当前userId>","corpId":"<corpId>"}],
    "<交接状态fieldId>":"未交接"
  }}]' --format json
# 返回的 recordId 就是父 recordId
# 注：父记录暂不写「状态」——未接手无状态，接手后由接手人回填并联动。
```

### 0c. 收集并上传产出物/工作文件（交接前必做）

交接子记录必须带上「产出物」和「工作文件」，否则接手方拿不到实际交付。逐个收集真实存在的文件并上传：

```bash
# 本机 agent：拿 outputFiles（exists=true 的 path）
python3 scripts/agent-tasks-listing/agent_task_probe.py --detail "<agent>:<sessionId>" --format json

# 千问办公任务：读详情，从 messages 的 Write/Edit toolCalls 解析写入文件路径
#（排除 outputs/、uploads/、临时目录），再用 Bash 校验文件真实存在）

# 每个存在的文件走 people-attachment.md「附件三步」上传，收集 fileToken
# 交付物（报告/产物）→「产出物」；源码/工作文件 →「工作文件」，二者可重叠
```

---

## 1. 交接（有目标人）：建子记录 + 更新父任务

### 1a. 建交接子记录

这一步是通知自动化触发点：创建记录时就写入「任务交接对象」；不要依赖后续更新父任务来触发通知。通知文案必须与创建记录同一条 `record create` 原子写入，禁止先建后补。

先跑本地就绪检查（不联网，交接摘要校验 + 通知文案渲染 + 组装完整 cells 到 `create-cells.json`，通知文案已内嵌）。PASS 后直接 `record create` 读该文件：

```bash
python3 scripts/check-handoff-ready.py handoff \
  --title "【交接】<父任务标题>" \
  --summary "<一句话摘要>" \
  --handoff-summary-file <交接摘要文本文件> \
  [--dev] \
  --group "<父任务标题>|<任务ID后6位>" \
  --parent-record-id <父recordId> \
  --creator '{"userId":"<当前userId>","corpId":"<corpId>"}' \
  --assignee '{"userId":"<目标userId>","corpId":"<corpId>"}' \
  --fields '<字段名→fieldId 映射 JSON>' \
  [--outputs-file-tokens "<产出物fileToken，逗号分隔>"] \
  [--workfiles-file-tokens "<工作文件fileToken，逗号分隔>"] \
  --cells-out create-cells.json
# 字段名→fieldId 映射 JSON 必含：任务标题/任务组/交接状态/任务交接对象/创建人/一句话摘要/交接摘要/通知文案/父记录；
# 产出物/工作文件可选（有附件或该字段存在时补上对应 fieldId）。PASS 即产出 create-cells.json，不要跳过。

dws aitable record create \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records-file create-cells.json \
  --format json
# 无产出/无工作文件时脚本已自动省略对应 field，不要手动补空数组。
```

### 1b. 更新父任务（只做汇总，不做通知触发）

父任务不要写「任务交接对象」，否则当前或后续自动化配置稍有变化时，可能父子两条记录都给同一个人发通知。

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<父recordId>","cells":{
    "<交接状态fieldId>":"交接中",
    "<交接摘要fieldId>":"<六块+元信息完整摘要，见 templates/handoff-summary.md；开发任务必填仓库/验证/交付物>"
  }}]' --format json
```

---

## 2. 交接（待认领，无目标人）

### 2a. 建交接子记录（任务交接对象留空，状态=待认领）

创建子记录前必须先跑本地就绪检查（不联网，交接摘要校验 + 通知文案渲染 + 组装完整 cells 到 `create-cells.json`，通知文案已内嵌）。PASS 后直接 `record create` 读该文件：

```bash
python3 scripts/check-handoff-ready.py claim \
  --title "【交接】<父任务标题>" \
  --summary "<一句话摘要>" \
  --handoff-summary-file <交接摘要文本文件> \
  --group "<父任务标题>|<任务ID后6位>" \
  --parent-record-id <父recordId> \
  --creator '{"userId":"<当前userId>","corpId":"<corpId>"}' \
  --fields '<字段名→fieldId 映射 JSON>' \
  [--outputs-file-tokens "<产出物fileToken，逗号分隔>"] \
  [--workfiles-file-tokens "<工作文件fileToken，逗号分隔>"] \
  --cells-out create-cells.json
# 待认领不传 --assignee，脚本自动省略「任务交接对象」、交接状态写「待认领」。

dws aitable record create \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records-file create-cells.json \
  --format json
```

### 2b. 更新父任务（状态=待认领）

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<父recordId>","cells":{
    "<交接状态fieldId>":"待认领",
    "<交接摘要fieldId>":"<六块+元信息完整摘要，见 templates/handoff-summary.md；开发任务必填仓库/验证/交付物>"
  }}]' --format json
```

---

## 3. 认领（待认领 → 交接中）

此流程只用于“本人主动认领”。如果发起人/管理员要把待认领任务指派给别人，不要直接更新旧待认领记录的「任务交接对象」；应按 §1 新建一条指定人的 `【交接】` 子记录，否则 `WhenRecordCreated` 指定人通知不会触发。

认领与接手是两步：认领只写「任务交接对象」+「交接状态=交接中」，此时「任务ID/Agent类型」必须留空。若认领人认领后立即开工、同时回填了自己的「任务ID + Agent类型」，则已越过认领、等价于接手，「交接状态」必须直接写「已接手」，不要停在「交接中」（已实测：agent 认领时顺手回填 taskId 却留「交接中」，状态滞后一步）。

先定位待认领记录（父与子可能同时是待认领，别认领错）：

- 有通知卡片 rowUrl/记录链接 → 解析 recordId 精确认领（群通知由子记录创建触发，链接指向子记录）。
- 标题搜索同时命中「父（待认领）」+「【交接】子（待认领）」时（§2b 会把父也写成待认领，且父子标题高度相似）→ 认领带【交接】前缀/父记录字段非空的子记录；父任务是汇总载体，不得被认领。
- 命中无父链接、无子记录的顶层记录（历史孤儿）→ 可直接认领它本身。

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<待认领recordId>","cells":{
    "<任务交接对象fieldId>":[{"userId":"<认领人userId>","corpId":"<corpId>"}],
    "<交接状态fieldId>":"交接中"
  }}]' --format json
```

父任务联动（父的交接状态始终镜像最新子记录，否则父会停在「待认领」而子已「交接中」）：

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<父recordId>","cells":{"<交接状态fieldId>":"交接中"}}]' --format json
```

若认领即开工（等价接手）：子记录按 §4 写「已接手」+ 自己的任务ID/Agent类型，父联动也按 §4 写「已接手」。认领的记录无父（顶层孤儿）时跳过父联动。

---

## 4. 接手（接手人回填子记录，不新建子记录）

接手前先定位子记录：

- 有通知卡片 rowUrl/记录链接 → 解析 recordId，精确更新该子记录。
- 用户说 `使用 agent-task-hub 接手「<任务标题>」` → 先按「任务交接对象=当前用户」「交接状态=交接中/待接手」筛子记录，再用标题关键词匹配；唯一命中才继续，多条命中让用户选择。
- 不要因为只有任务标题就新建子记录；接手只更新发起人已经创建的 `【交接】` 子记录。

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<子记录recordId>","cells":{
    "<任务IDfieldId>":"<接手人的任务ID>",
    "<Agent类型fieldId>":"<接手人的agent类型>",
    "<状态fieldId>":"进行中",
    "<交接状态fieldId>":"已接手"
  }}]' --format json
```

父任务联动：

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<父recordId>","cells":{"<交接状态fieldId>":"已接手"}}]' --format json
```

---

## 5. 完成

### 5a. 更新子记录为完成

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<子记录recordId>","cells":{"<状态fieldId>":"已完成","<交接状态fieldId>":"已完成"}}]' --format json
```

### 5b. 回读同父子记录，必要时更新父任务

完成后必须回读同一个父任务下的所有子记录：

```bash
dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> \
  --query "<父任务标题或父recordId>" --format json
# 客户端按「父记录」fieldId 精确过滤 linkedRecordIds 包含 <父recordId> 的子记录。
```

- 如果该父任务下所有子记录的「交接状态」都为「已完成」，再把父任务更新为完成：

```bash
dws aitable record update \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --records '[{"recordId":"<父recordId>","cells":{"<状态fieldId>":"已完成","<交接状态fieldId>":"已完成"}}]' --format json
```

- 如果还有子记录处于「待认领 / 交接中 / 已接手」，父任务不要标记完成，保持当前汇总状态。

---

## 6. 附件上传（产出物/工作文件，三步）

```bash
# ① 拿 uploadUrl + fileToken（未识别/复合扩展名必须 --mime-type）
dws aitable attachment upload --base-id <BASE_ID> --file-name <文件名> --size <字节数> --mime-type <text/plain|application/zip> --format json

# ② curl PUT 上传（Content-Type 对照表见 references/people-attachment.md）
curl -sS -X PUT "<uploadUrl>" -H "Content-Type: <mime>" --data-binary @<本地文件路径> -w "HTTP %{http_code}\n"

# ③ 写 fileToken 到附件字段
dws aitable record update --base-id <BASE_ID> --table-id <TABLE_ID> \
  --records '[{"recordId":"<recordId>","cells":{"<产出物|工作文件fieldId>":[{"fileToken":"<fileToken>"}]}}]' --format json
```

---

## 7. 建交接通知自动化

DSL 模板见 `templates/handoff-notify-workflow.json`（含 `<...>` 占位符，**不能直接创建**）。
先用 `table get` 结果渲染出实例 DSL，再创建（DSL 语义/节点说明见 `references/workflow-notify.md`）：

```bash
# ① 渲染（需要先把 table get 结果存成 JSON 文件）
python3 scripts/create-ledger.py team workflows \
  --base-id <BASE_ID> --table-id <TABLE_ID> --table-get-json <TABLE_GET_JSON> [--group-cid <群cid>]
# 输出 handoffDslJson / claimDslJson 路径与对应 workflowCreateCommand

# ② 用渲染后的 DSL 创建（路径用 ① 输出的 handoffDslJson，不是 templates/ 下的模板）
dws aitable workflow create --base-id <BASE_ID> \
  --dsl @<渲染后的handoff-notify-workflow.json> --locale zh-CN --format json
# 返回 valid=true 才算成功；valid=false 读 issues 修正
```


---

## 硬规则

- 上述命令里 `<...>` 是运行时变量，先查/确认再填，其余部分**原样执行**。
- 交接前先确认表里有且只有一个可用「父记录」字段；没有就先 `field create` 补，有多个则停止并提示清理/选择，不要随手任选一个继续写。
- 新建指定人交接子记录时必须同时写「任务交接对象」「一句话摘要」和「通知文案」；「通知文案」是 `WhenRecordCreated` 自动化发送的正文，一律由 `scripts/render-notice.py` 生成并原样嵌入（样式已实机验证：加粗标签 + 引用块 prompt），禁止自由组装。
- 渲染器（Markdown 预览/通知卡片）在 markdown 解析后跑 linkify：裸写 `SKILL.md`、`run_all.py` 这类后缀恰为国家码顶级域的文件名会被自动加超链接，实机（2026-08）仅行内代码可抑制。`render-notice.py` 的 sanitize 会自动把摘要中此类词元与裸 URL 包反引号、折叠显式 markdown 链接；任务标题不 sanitize（接手 prompt 需原标题定位记录），标题应避免裸写此类文件名。
- 创建交接子记录前必须跑 `scripts/check-handoff-ready.py`（指定人用 `handoff`、待认领用 `claim`；开发任务加 `--dev`）并 PASS，让它生成 `--cells-out create-cells.json`（通知文案已随 cells 内嵌），随后用 `dws aitable record create ... --records-file create-cells.json` 创建；PASS 前禁止 `record create`，禁止先建记录再补「通知文案」，避免发出空通知卡片。
- 父任务不要写「任务交接对象」；父任务只承载原始任务、状态和汇总摘要，具体接手人只在子记录上。
- 父记录创建和接手回填都必须写「Agent类型」；接手人回填的是自己的 agent 类型，不沿用发起人的 agent 类型。
- 子记录完成后，只有当同父所有子记录都完成时，父任务才更新为「已完成」。
- 新建待认领入口必须走 §0（保证父记录）+ §2（建【交接】子记录）：群通知由子记录创建触发（WhenRecordCreated），通知本身不创建任何记录；不要直接建顶层待认领记录，历史孤儿记录可继续在其本身认领。
- 父任务交接状态始终镜像最新子记录：认领→交接中、接手→已接手、全部子完成→已完成；不得让父状态滞后一步（已实测：子已交接中、父仍待认领）。
- 每一步执行后读返回确认成功，再下一步；不要并行乱序。
- `dws aitable record create/update` 可能 stdout 完全为空但实际已写成功（已实测）。返回为空时用 `record query` 回读确认，**不要盲目重跑**（会产生重复记录）。