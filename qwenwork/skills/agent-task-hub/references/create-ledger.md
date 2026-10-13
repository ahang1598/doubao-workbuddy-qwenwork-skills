# 创建台账确定性流程（create-ledger）

> 个人 / 团队两种台账的**完整创建命令序列**。个人台账仍按本文逐条执行；团队台账初始化/分享优先用 `scripts/create-ledger.py team plan` 生成本地产物和前台命令计划，本文的分步命令作为脚本产物的解释与排障路径。
> 所有 `dws` 写操作必须由 agent 前台直接执行，命令首词为 `dws`，加 `--format json` 解析返回值；不要用 Python subprocess、run_in_background、nohup、`&` 或 shell 脚本批跑包装 dws。Python 只允许做本地算账和产物准备。不硬编码 baseId/tableId/fieldId，运行时解析，并用 `memory` 记住坐标。
> 下文出现的 `python3 scripts/...` 均以本 skill 安装目录为基准，执行前先 `cd` 到该目录。

---

## 一、个人台账创建（同步用，不含交接字段）

### 步骤 1：复用优先，找已有个人台账

```bash
dws aitable base search --query "千问办公个人任务台账" --format json
dws aitable base search --query "千问办公任务台账" --format json
# 优先命中个人专用名；旧名仅做兼容。确认是个人台账 → 解析 baseId + 一个 tableId，跳到步骤 4
# 未命中 → 步骤 2 新建
```

### 步骤 2：新建 Base

```bash
dws aitable base create --name "千问办公个人任务台账" --format json
# 返回 baseId，记为 <BASE_ID>
# 建成功后跑 dws aitable base get --base-id <BASE_ID> --format json，
# 把随 Base 自动创建的默认空「数据表」tableId 记为 <DEFAULT_TABLE_ID>（步骤 6 清理用）
```

### 步骤 3：建「任务台账」表（个人 12 字段，第一个必须是 text 主字段）

```bash
dws aitable table create --base-id <BASE_ID> --name "任务台账" --fields '[
  {"fieldName":"任务标题","type":"text"},
  {"fieldName":"状态","type":"singleSelect","config":{"options":[{"name":"进行中"},{"name":"等待确认"},{"name":"已完成"},{"name":"已取消"},{"name":"失败"},{"name":"中断"},{"name":"暂停"}]}},
  {"fieldName":"任务类型","type":"singleSelect","config":{"options":[{"name":"其他"}]}},
  {"fieldName":"优先级","type":"singleSelect","config":{"options":[{"name":"高"},{"name":"中"},{"name":"低"}]}},
  {"fieldName":"产出物","type":"attachment"},
  {"fieldName":"工作文件","type":"attachment"},
  {"fieldName":"Agent类型","type":"singleSelect","config":{"options":[{"name":"qwenwork"},{"name":"codex"},{"name":"qoder"},{"name":"claudecode"},{"name":"qoderwork"},{"name":"其他"}]}},
  {"fieldName":"任务ID","type":"text"},
  {"fieldName":"创建时间","type":"date","config":{"formatter":"YYYY-MM-DD HH:mm"}},
  {"fieldName":"更新时间","type":"date","config":{"formatter":"YYYY-MM-DD HH:mm"}},
  {"fieldName":"最后同步时间","type":"date","config":{"formatter":"YYYY-MM-DD HH:mm"}},
  {"fieldName":"创建人","type":"user","config":{"multiple":false}}
]' --format json
# 返回 tableId，记为 <TABLE_ID>
# 任务类型选项不要写死：同步打标时按每条任务的实际内容生成贴合的分类（singleSelect 写入新 name 会自动建选项），初始只留「其他」兜底。
```

### 步骤 4：拿 fieldId 映射并记住坐标

```bash
dws aitable table get --base-id <BASE_ID> --table-id <TABLE_ID> --format json
# 解析每个 fieldId/fieldName/type，用 memory 存：baseId + tableId + fieldId 映射
# 返回存成 <TABLE_GET_JSON>，步骤 6 的 personal views 脚本要用
```

### 步骤 5：确认同步范围 + 打标方式 + 附件策略

```bash
python3 scripts/agent-tasks-listing/agent_discovery.py
# 列出可用 agent。用 AskUserQuestion 确认三项，并把结果记到 memory：
# ①「要同步哪些 agent 的台账」（首选项=探测到的推荐集，千问办公默认勾选）
# ② 同步时间窗口：首选项=「近一天」（推荐默认），其他选项可给近三天/近七天/全量
# ③ 产出物/工作文件策略：全部上传 / 只传 ≤10MB / 不同步（建台账时问一次并记住；手动同步可临时改）
# 任务类型、优先级不再问：每次同步时由模型按任务标题+详情自动打标（任务类型按实际内容动态分类，不写死固定枚举）。
```

### 步骤 6：视图布置与默认表清理

```bash
python3 scripts/create-ledger.py personal views \
  --base-id <BASE_ID> --table-id <TABLE_ID> \
  --table-get-json <TABLE_GET_JSON> --default-table-id <DEFAULT_TABLE_ID>
# 生成 views-plan.md，前台逐条执行：建「状态看板」→ 按状态分组 → 删默认空「数据表」
# 复用已有 Base 时若没有名为「数据表」的表，不传 --default-table-id
```

### 步骤 7：首次全量基线同步（可选，用户明确要求才做）

走「定时同步流程」，但首次用全量（`qwenwork.tasks` 翻页拿全量、本地 agent 用裸 `--list`），建立基线。之后日常一律近一天增量。

### 步骤 8：建每日定时同步

用内置 cron 工具（`qwenwork_cron_manage_job`，不是 dws）建每日任务，schedule 建议 `kind=cron, expr="0 9 * * *"`（每天一次，时间可按用户要求改），payload 走「定时同步流程」。**不要设分钟级高频**。

### 步骤 9：验证

```bash
# 个人台账不得有任何自动化
dws aitable workflow list --base-id <BASE_ID> --format json
# 期望 recordCount == 0；若不为 0，检查是否误建，误建则清理

# 能读表
dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> --limit 1 --format json
```

---

## 二、团队台账创建（交接用，含交接字段）

> 本章是**初始化/分享分支**：只建 Base、表、字段、自动化、权限和安装指引。不要创建任何任务父记录或 `【交接】` 子记录；那些只属于 `operations.md` 的交接分支。

### 首选：确认意图后先生成本地产物与前台命令计划

用户意图已经明确为“创建/复用团队台账、分享给同事、发到群里、给同事安装使用”时，先解析必要参数，然后优先运行本地脚本生成字段 JSON 和前台命令计划：

```bash
# 本地生成：不调用 dws，不创建线上资源
python3 scripts/create-ledger.py team plan \
  --share-users <userId列表> \
  --group-cid <团队群cid>
```

参数说明：

- 已有团队 Base 时传 `--base-id <BASE_ID>`；已知表 ID 时可再传 `--table-id <TABLE_ID>`。
- `--share-users` 传 userId 逗号分隔；人名需先用 `dws aisearch person` 解析，脚本不猜人。
- `--group-cid` 只在用户给出明确群或唯一群命中时传；否则不要宽泛搜群，也不要创建待认领群通知。
- 脚本输出 `team-fields.json`、可选 `parent-field-config.json` 和 `foreground-dws-plan.md`。
- agent 读取 `foreground-dws-plan.md` 后，逐条以前台 `dws ...` 命令执行；不得把 plan 放进 Python、shell 脚本或后台批跑。
- field create 之后跑一次 `table get`（唯一需要的一次，fieldId/optionId/views 都在它的返回里），把返回保存为 `<TABLE_GET_JSON>`，再运行：

```bash
python3 scripts/create-ledger.py team workflows \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --table-get-json <TABLE_GET_JSON> \
  --group-cid <团队群cid>
```

- 该命令只生成 workflow DSL；随后仍由 agent 前台执行 `dws aitable workflow create --dsl @<DSL_JSON>`。
- plan 已含视图布置与默认表清理步骤（base get 拿 `<DEFAULT_TABLE_ID>`、`team views` 直接从 `<TABLE_GET_JSON>` 解析 Grid viewId，不需要额外 view get，生成 views-plan.md 后逐条执行）。
- 整个初始化/分享分支不会创建任务父记录或 `【交接】` 子记录。

### 步骤 1：问用户团队是否已有接续表格

- 用户明确说“重新生成/新建团队台账” → 不再询问是否复用，直接步骤 2 新建。
- 已有 → 请用户提供 AI表格 链接或 Base ID，解析出 baseId（再 `table get` / `resolve-table` 拿 tableId），跳到步骤 4。
- 没有 → 步骤 2 新建。

### 步骤 2：新建 Base

```bash
dws aitable base create --name "千问办公团队接续台账" --format json
# 返回 baseId，记为 <BASE_ID>
# 建成功后跑 dws aitable base get --base-id <BASE_ID> --format json，
# 把随 Base 自动创建的默认空「数据表」tableId 记为 <DEFAULT_TABLE_ID>（步骤 8 清理用）
```

### 步骤 3：建「任务台账」表（团队 13 字段）

```bash
dws aitable table create --base-id <BASE_ID> --name "任务台账" --fields '[
  {"fieldName":"任务标题","type":"text"},
  {"fieldName":"任务组","type":"text"},
  {"fieldName":"交接状态","type":"singleSelect","config":{"options":[{"name":"未交接"},{"name":"待认领"},{"name":"交接中"},{"name":"已接手"},{"name":"已完成"}]}},
  {"fieldName":"任务交接对象","type":"user","config":{"multiple":false}},
  {"fieldName":"状态","type":"singleSelect","config":{"options":[{"name":"进行中"},{"name":"等待确认"},{"name":"已完成"},{"name":"已取消"},{"name":"失败"},{"name":"中断"},{"name":"暂停"}]}},
  {"fieldName":"一句话摘要","type":"text"},
  {"fieldName":"交接摘要","type":"text"},
  {"fieldName":"产出物","type":"attachment"},
  {"fieldName":"工作文件","type":"attachment"},
  {"fieldName":"Agent类型","type":"singleSelect","config":{"options":[{"name":"qwenwork"},{"name":"codex"},{"name":"qoder"},{"name":"claudecode"},{"name":"qoderwork"},{"name":"其他"}]}},
  {"fieldName":"任务ID","type":"text"},
  {"fieldName":"通知文案","type":"richText"},
  {"fieldName":"创建人","type":"user","config":{"multiple":false}}
]' --format json
# 返回 tableId，记为 <TABLE_ID>
```

### 步骤 4：补「父记录」字段（自关联，建表后补）

先回读字段，避免重复创建同名「父记录」：

```bash
dws aitable table get --base-id <BASE_ID> --table-id <TABLE_ID> --format json
# 若已有且只有 1 个 fieldName=父记录、type=unidirectionalLink、linkedTableId=<TABLE_ID>：
#   - config.multiple=false：直接复用该 fieldId，不再创建。
#   - config.multiple=true：不要新建同名字段；记录为待迁移，后续写入仍只传 1 个 linkedRecordId。
# 若没有，再创建。
# 若已有多个同名「父记录」，不要继续写子记录；先提示用户线上表存在重复父记录字段，需要清理或选择一个 canonical fieldId。
```

```bash
dws aitable field create --base-id <BASE_ID> --table-id <TABLE_ID> \
  --name "父记录" --type unidirectionalLink \
  --config '{"linkedTableId":"<本表TABLE_ID>","multiple":false}' --format json
# 若返回「主键不存在不允许创建关联字段」，先确认 tableId 正确、表已建好，再重试
```

### 步骤 5：拿 fieldId 映射并记住坐标

```bash
dws aitable table get --base-id <BASE_ID> --table-id <TABLE_ID> --format json
# 解析 fieldId 映射，用 memory 存：baseId + tableId + fieldId 映射
# 返回存成 <TABLE_GET_JSON>，步骤 8 的 team views 脚本要用
```

### 步骤 6：建表后立即问「共享给谁」

用 AskUserQuestion 问：人 / 群 / 暂不共享。

- 如果用户在原始请求里已经指定共享对象（如“分享给羽承”），跳过 AskUserQuestion，直接按“人”路径执行。
- 人 → `dws drive permission add --node <BASE_ID> --users <userId列表> --role EDITOR --format json`。
  - `--node` 接受 baseId 或节点 URL；AI表格 baseId 可直接传（已 dry-run 验证）。
  - `--role` 可选 `MANAGER` / `EDITOR` / `DOWNLOADER` / `READER`；交接对象建议 `EDITOR`（要能读写），普通成员按用户选择。
  - 这是「文档空间节点」权限，不是钉盘文件权限；`--users` 只传人（userId），没有直接群参数。
- 群 → 当前 `drive permission add` 无群参数，不要自动解析群成员批量授权（有误授权风险）；提示用户打开表格手动分享给群。
- 用户只说“分享到群里”但没有明确群名或 `openConversationId` 时，不要用宽泛关键词搜索并猜测发送；直接把群发送列为“需确认群名/群 ID”。只有给出明确群名且唯一命中时，才发真实群消息。
- 暂不共享 → 只返回表格链接。

### 步骤 7：补齐自动化（硬规则，新建/复用都一样）

```bash
# 先检查
dws aitable workflow list --base-id <BASE_ID> --format json
```

- 缺「交接任务通知」→ 优先用脚本渲染 DSL，避免手工替换慢且易漏：

```bash
python3 scripts/render-workflow-dsl.py handoff \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --assignee-field-id <任务交接对象fieldId> \
  --notice-field-id <通知文案fieldId> \
  --out /tmp/agent-task-hub-handoff-workflow.json
```

也可以手工用 `templates/handoff-notify-workflow.json` 模板，把 `<...>` 占位符替换成本表真实 fieldId，写临时 JSON，然后：

```bash
dws aitable workflow create --base-id <BASE_ID> \
  --dsl @/tmp/agent-task-hub-handoff-workflow.json --locale zh-CN --format json
# data.valid=true 才算成功；valid=false 读 issues 修正
```

- 已有「交接任务通知」不能只看名字：必须确认它是新版语义（`WhenRecordCreated`、监听创建时已填的「任务交接对象」、正文直接引用「通知文案」richText 字段）。若仍是 `WhenRecordUpdated` 或正文仍是拼接 text/ref 片段，标记为旧版待迁移；不要在最终结果里说“自动化已补齐”。
- 创建/更新自动化前，检查临时 DSL 不得残留 `<...>` 占位符：

```bash
rg '<[^>]+>' <临时JSON文件>
# 期望无输出；若仍有输出，先替换完再 create/update workflow
```

- 「待认领群通知」→ 仅当用户提供了团队群（拿到群 cid）才建。优先用：

```bash
python3 scripts/render-workflow-dsl.py claim \
  --base-id <BASE_ID> \
  --table-id <TABLE_ID> \
  --notice-field-id <通知文案fieldId> \
  --status-field-id <交接状态fieldId> \
  --pending-option-id <待认领optionId> \
  --group-cid <团队群cid> \
  --out /tmp/agent-task-hub-claim-workflow.json
```

没有明确群就不建。
- 「交接任务通知」必须是 `WhenRecordCreated` 触发，并监听创建时已填的「任务交接对象」；不要建成只监听「记录更新」的自动化。
- 通知正文直接引用「通知文案」richText 字段（markdown 渲染）；完整六块「交接摘要」留在表格里查看，「一句话摘要」只做台账列表检索。
- 父任务不要写「任务交接对象」；只有交接子记录/待认领记录写接手人，避免父子记录重复触发通知。

### 步骤 8：视图布置与默认表清理

```bash
python3 scripts/create-ledger.py team views \
  --base-id <BASE_ID> --table-id <TABLE_ID> \
  --table-get-json <TABLE_GET_JSON> \
  --default-table-id <DEFAULT_TABLE_ID>
# Grid viewId 直接从 <TABLE_GET_JSON> 的 views 里解析，不需要额外跑 view get
# 生成 views-plan.md，前台逐条执行：
# Grid 按「任务组」分组并重排列序、隐藏任务组列 → 建「交接看板」→ 看板按「交接状态」分组 → 删默认空「数据表」
# 复用已有 Base 时若没有名为「数据表」的表，不传 --default-table-id
```

> 父子在 API 层不是真层级（unidirectionalLink 只是字段关联），Grid 按隐藏的「任务组」分组后，父与子归到同一组、父不再孤立；「交接看板」按交接状态分列，一眼看到待认领/交接中/已接手。

### 步骤 9：验证

```bash
# 确认交接通知已存在且 RUNNING；若工具能读 DSL，还要核对为 WhenRecordCreated 新版语义
dws aitable workflow list --base-id <BASE_ID> --format json
# 期望至少 1 条「交接任务通知」且 status=RUNNING

# 能读表
dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> --limit 1 --format json
```

### 步骤 10：安装指引（分享后必做，但真实触达需确认）

生成安装指引草稿并在最终回复里给出。只有用户明确要求“发给对方/发到群里”时，才打包 skill 并真实发送消息或附件。确切命令与文案见 [templates/install-notice.md](../templates/install-notice.md)。测试阶段发 `.zip` 安装包（仅 zip，包内必须存在 `agent-task-hub/SKILL.md` 外层目录路径）；上架后改发技能市场引导。

### 步骤 11：初始化分支收尾

如果用户的原始目标只是“创建团队台账 / 分享给同事 / 发到群里”，执行到这里即完成。最终回复只报告：

- 已创建/复用的团队台账链接和 baseId；
- 已建/已验证的自动化；
- 已授权的人；
- 群发送是否已完成，若未完成则说明缺明确群名/群 ID；
- 未创建任何任务父记录或 `【交接】` 子记录。

不要为了“测试交接能力”自动创建当前任务的父记录或给共享对象创建子记录。

---

## 硬规则

- 每步执行后读返回确认成功，再下一步；不要并行乱序。
- 互不依赖的只读查询可以并行；写操作必须串行。
- `<BASE_ID>` / `<TABLE_ID>` / fieldId 一律运行时解析，不凭印象硬编码。
- 个人台账**不得建自动化**；团队台账**必须附「交接任务通知」自动化**。
- 团队模式**绝不建定时同步任务**（隐私红线）。
- 初始化/分享团队台账时不得创建任务记录；只有明确交接意图才进入 `operations.md`。
