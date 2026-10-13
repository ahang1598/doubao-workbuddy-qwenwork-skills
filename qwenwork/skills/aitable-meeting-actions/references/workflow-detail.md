# workflow-detail — 完整工作流步骤与命令示例

本文件是 `aitable-meeting-actions` 的详细命令参考。所有命令与参数均以本机 `dws <command> --help` 实际输出为准；下文中尖括号 `<...>` 内为需要从前序命令返回值中提取的占位值，严禁凭空填写。

## Module A: 准备与会议定位

### A1. 获取当前用户信息

```bash
dws contact user get-self --format json
```

- 提取：本人 `userId`、姓名、`corpId`
- corpId 用于 Module E 人员字段写入；userId 用于 Module F 待办 executors，也用于「我负责的未完成」视图的筛选条件
- 注意：必须用 `get-self`（别名 `self`/`me`/`whoami`），禁止 `user get --ids me`
- 多组织（多企业）用户：先 `dws profile list --format json` 列出已登录身份，确认目标组织后对全链路命令统一附加 `--profile <corpId:userId>`

### A2. 双源检索会议并列候选

用户已给出会议纪要内容或明确会议时直接使用，跳过本步。否则列历史会议供选，必须覆盖"我参与的所有会议"（双源合并）：

源 1：听记（有内容、可提取），默认时间窗最近一周：

```bash
dws minutes list all \
  --start "2026-08-10T00:00:00+08:00" --end "2026-08-17T17:00:00+08:00" \
  --limit 30 \
  --format json
```

**`--limit` 必须显式传**：不传时默认仅返回 10 条，一周会议超过 10 场就会静默截断候选——这与本技能"覆盖我参与的所有会议"的承诺直接冲突。

源 2：我参与的日程会议（同时间窗）：

```bash
dws calendar event list \
  --start "2026-08-10T00:00:00+08:00" --end "2026-08-17T17:00:00+08:00" \
  --limit 100 --format json
```

合并规则：

- 两源按时间重叠 + 标题相似去重，听记源优先（携带 taskUuid，可提取）
- 仅在日程源出现的会议照常列出，标注「无听记，暂不可提取」；用户选中时引导开启 AI 听记或请发起人共享
- 能力边界：无日程且无听记的临时视频会议，开放平台无查询接口，无法列出，需如实告知
- 用户给了会议名线索 → minutes 源追加 `--query "产品周会"`，calendar 源拉回后按标题本地过滤；用户指定了时间段 → 两源同步改 `--start/--end`

批量补齐候选人数（一次调用，禁止逐个 get info 轮询）：

```bash
dws minutes get batch --ids <uuid1,uuid2,uuid3> --format json
```

- batch 仅限听记创建者调用：非本人发起的共享听记报 `user is not minutes creator` → 人数降级：日程源用 calendar 参会人数补位，仍无则显示"—"；不阻断、不逐个轮询补人数；
但**提取不受影响**：共享听记单条 `get info/todos/summary/transcription` 全部可用（已实测），严禁引申为"非本人不可处理"；这类听记拿不到听记状态时不标「转写中」，按「有听记」进入提取，内容空再走空内容兜底并注明"转写可能未完成"
- 返回字段含**听记状态**：非「转写完成」的会议标注「转写中，暂不可提取」，与"无听记"同等处理——刚结束的会议常处于此态，此时硬拉 todos/summary 会拿到空内容并被误判为"本场无行动项"
- 展示候选四要素：`序号. 主题 — 时间 (时长) — 人数`，可提取性标注「有听记 / 转写中 / 无听记」；以选择卡片（多选）提问，**选项总数上限 10 项**（含末位「其他」），超出时取前 9 项并在「其他（请填写）」说明中注明"共 N 场"；禁止用末尾文字引导打字回复
- `--limit`：minutes 不传默认 10（取 30 起），calendar 取 100；结果多页时用 `--cursor <token>` 翻页至覆盖完整时间窗，仍被截断则如实标注
- 一周内双源均无结果 → 提示扩大时间范围（如最近一个月）或提供会议名
- 多候选时等用户选择后才继续；多选时对每个（有听记的）taskUuid 各自执行 Module B→C，合并进入 Module D→E

## Module B: 行动项原料提取

对选定的 `<taskUuid>` 依次执行：

```bash
dws minutes get info --id <taskUuid> --format json          # 会议标题、会议日期
dws minutes get todos --id <taskUuid> --format json         # 系统提取的待办（主料）
dws minutes get summary --id <taskUuid> --format json       # AI 摘要 Markdown（上下文）
```

- `get todos` 返回：待办内容、待办唯一 ID、参与人信息、待办时间——参与人信息是责任人解析的第一来源
- `get summary` 返回 Markdown，涵盖会议主题、核心结论、关键讨论点
- 兜底（仅当 todos 为空且摘要无行动项线索，且已征得用户同意）：

```bash
dws minutes get transcription --id <taskUuid> --format json
```

- 转写原文可能非常长，取回后只截取与任务分配相关的段落参与分析，不要全文复述给用户

## Module C: 六字段结构化与责任人解析

纯 AI 分析步骤（无命令），产出下列六字段行动项列表（标准四件套 + 协作人 + 关联议题）：

```
{ 行动项(动宾结构), 负责人, 截止日期(YYYY-MM-DD或空), 状态(默认未开始), 协作人[], 关联议题, 来源标识, 判断理由, 适合度(建议/不建议), 推断项[] }
```

来源标识（本版新增，查重的唯一依据）：

- 来自 `get todos` 的条目 → `<taskUuid>#<todoId>`（todoId 取 `get todos` 返回的待办唯一 ID）
- 仅由 `get summary` 提取的条目（无稳定 todoId）→ `<taskUuid>#summary`
- 为何不用标题做查重依据：标题经 AI 推断补全，同一场会两次运行可能产出"整理 Q2 报告"与"整理 Q2 数据报告"两种字面，靠字面比对会漏判成新条目而重复写入

日期换算（最易出错，单列规则）：

- **基准 = `get info` 返回的会议开始时间，不是今天**。例：会议在 08-13（周三），摘要说"下周三" → 换为 08-20；即使执行时已是 08-21，仍写 08-20 并在回执标注「已过期」
- "尽快/ASAP/越快越好" → **不折算**，截止日期留空，进回执「待确认清单」

责任人/协作人解析顺序：

1. 在 `get todos` 返回的参与人信息中按姓名精确匹配 → 直接得到 userId
2. 匹配不到时：

```bash
dws contact user search --query "张三" --format json
```

- 唯一命中 → 采用其 userId；多个命中 → 列出候选（姓名+部门）请用户选择
- **仍匹配不到 → 不臆造**：不写 user cell，姓名降级写入备注列（"负责人待认领：王五"），并进回执「未匹配人员清单」

推断标注：text 字段（行动项/关联议题）的推断值加后缀「（推断）」；日期/人员/单选存不了后缀，推断依据集中进回执。

## Module D: 定位/创建追踪表

### D1. 目标表两级选择（用户未明确目标表时，询问不可跳过）

用户已在指令中给出表名/链接 → 跳过询问（唯一例外）：表名直接 `base search --query "<表名>"`，链接则解析出 baseId 后 `base get` 验证。

否则先探测疑似既有跟踪表（**探测命中 ≠ 自动选中，命中只改变推荐项，必须照常抛出第一级选择等用户选定**）：

```bash
dws aitable base search --query "行动项" --format json
```

然后用客户端选择卡片（单选）抛出第一级选择，严禁在正文里写成文字列表（探测命中时列为推荐项，未命中则不出现该项）：

```
行动项写到哪张表？
1. 添加到《项目行动项跟踪》（推荐）
2. 新建表格
3. 添加到其他已有表格
4. 其他（请填写）
```

用户选"添加到其他已有表格"时，进入第二级：

```bash
dws aitable base list --limit 10 --format json
```

- 将返回的 Base 作为选择卡片的选项，末位固定加「其他（请填写）」项，说明为"输入不在列表中的表格名称"；禁止用末尾文字提示替代「其他」项，严禁在正文里写成文字列表
- 注意：`base list` 仅返回最近访问的 Base（每页最多 10 个，可 `--cursor` 翻页），不是全部；列表没有不代表表不存在
- 用户在「其他」中输入表名 → `base search --query "<表名>"`；仍搜不到 → 请用户确认名称或提供表格链接；禁止拿相似名的表当命中直接写

选中 Base 后定位目标表（先用轻量的 `base get` 取表目录，再只拉目标表的字段）：

```bash
dws aitable base get --base-id <baseId> --format json
dws aitable table get --base-id <baseId> --table-ids <tableId> --format json
```

- `base get` 只返回 baseName 与 tables/dashboards 的 summary（不含字段详情），是拿 tableId 的轻量入口；仅一张数据表直接用，多张则再出一张选择卡片让用户选表
- `table get` 不传 `--table-ids` 会返回 Base 下**全部表**的字段与视图目录，造成上下文突增；已知 tableId 时必须显式传入
- 返回的 `fields` 含 fieldId/fieldName/type；按"名称+类型"匹配标准 schema，缺字段则补齐：

```bash
dws aitable field create --base-id <baseId> --table-id <tableId> \
  --name "协作人" --type user \
  --config '{"multiple":true}' \
  --format json
```

- 复用本版之前建的旧表时，「来源标识」列一定缺失，同样用 `field create --type text` 补齐（**不做任何存量数据迁移**）；若因权限补不上，降级为旧查重口径（标题 + 备注含会议名）并告知用户查重可靠性下降
- 若人员/日期/单选三类字段在既有表中是 text 类型：筛选/到期提醒/看板会失效，必须向用户提示降级后果，同意后才降级写入

### D2. 新建 Base + 追踪表（无可复用表时，需用户确认）

```bash
dws aitable base create --name "会议行动项跟踪" --format json
```

- 提取返回的 `baseId`；名称 1-50 字符
- 如需建到指定知识库目录，追加 `--folder-id <dentryUuid>`（节点 ID 通过文档相关服务获取，不得编造）

表名规则：单会议 → 「<会议主题>·行动项」；多会议合并 → 「会议行动项汇总-YYYYMMDD」；≤100 字符且不含 `/ \ ? * [ ] :`，重名由服务端自动续号。

```bash
dws aitable table create --base-id <baseId> --name "产品项目周会·行动项" --fields '[
  {"fieldName":"行动项","type":"text"},
  {"fieldName":"负责人","type":"user","config":{"multiple":false}},
  {"fieldName":"协作人","type":"user","config":{"multiple":true}},
  {"fieldName":"截止日期","type":"date","config":{"formatter":"YYYY-MM-DD"}},
  {"fieldName":"状态","type":"singleSelect","config":{"options":[{"name":"未开始"},{"name":"进行中"},{"name":"已完成"},{"name":"已取消"}]}},
  {"fieldName":"关联议题","type":"text"},
  {"fieldName":"备注","type":"text"},
  {"fieldName":"来源标识","type":"text"}
]' --format json
```

- 六字段 + 系统保留列（备注、来源标识）共 **8 个字段**（≤ 单次 15 上限）；**人员/日期/单选三类字段类型必须严格正确**，否则筛选/提醒/看板全废
- 「来源标识」仅适用于本版及之后新建的表；旧表走 D1 的 `field create` 补齐路径，不做存量迁移
- 建表后必须再执行一次 `table get --table-ids <tableId>` 获取每个字段的 **fieldId**——record create 的 cells key 只能用 fieldId

### D3. 新建表后补建视图

新建的表只有一张默认 Grid，开箱体验差；固定补建两个视图（`view create` 支持 Grid / Kanban / Gantt / Calendar / Gallery）：

```bash
# 第 0 步（幂等）：读回本表视图全量目录；同名视图已存在则跳过创建、复用既有 viewId
dws aitable view get --base-id <baseId> --table-id <tableId> --format json

# 先读回同 Base 任一既有视图的真实 config 作为样板，严禁凭空构造 filter/sort/group 结构
dws aitable view create --base-id <baseId> --table-id <tableId> \
  --view-type Kanban --name "状态看板" \
  --config '<按样板改写，group 指向「状态」fieldId>' \
  --format json
```

| 视图名 | viewType | config 要点 |
|---|---|---|
| 状态看板 | `Kanban` | 按「状态」fieldId 分组；可隐藏「来源标识」列 |
| 我负责的未完成 | `Grid` | 筛选负责人 = A1 拿到的本人 userId、状态非已完成/已取消；按截止日期升序 |

- **幂等**：建前查目录、同名跳过；建后再读回一次目录确认无同名视图。重跑/重试绝不允许建出第二个「状态看板」
- 「我负责的未完成」负责人取值只能来自 A1 `get-self`；`get-self` 空或异常时禁止借其他数据的 userId 猜"本人"，降级为不建该视图并告知用户
- 筛选写入后必须自检：`view get filter` 读回确认条件已落且操作符为合法 token。条件值格式已实测：负责人 `any_of` + `[{"userId":"<userId>","corpId":"<corpId>"}]` 对象数组（服务端归一化为 uid；写 userId 字符串不命中）、状态 `ne` + 选项名（归一化为选项 ID）；多条件 AND 合法 token 已实测正确求值。
**严禁 `is`/`isnot`**（错误拼写别名，view config 不归一化 → UI 裸显示 IS/ISNOT）；filter 外层须数组包裹。禁止用 `record query` 核对人员条件（报 INTERNAL_ERROR）；读回仍见 is/isnot 字面量时立即 `view update --config` 重写
- 平台边界：CLI 筛选无"当前用户/包含我"动态值，该视图钉死为本次执行者；同事打开需自行改筛选。回执一句话说明
- 构造失败时降级为只建「状态看板」（仅需 group 一项），并告知用户筛选视图需在表格里手动配置；**不得因建视图失败阻断主流程**
- 补建视图同时是字段类型的反向验证：若「状态」不是 singleSelect，Kanban 无法按其分组，此时应回头确认字段类型
- 注意与禁区区分：看板**视图**（Kanban view）属于本技能能力；仪表盘/图表（`dashboard` / `chart`）属于禁区，不得调用

## Module E: 复盘遗留项 + 确认与写入

### E1. 查重（仅复用既有表时）

```bash
dws aitable record query --base-id <baseId> --table-id <tableId> \
  --filters '{"operator":"and","operands":[{"operator":"contain","operands":["<来源标识fieldId>","<本次taskUuid>"]}]}' \
  --field-ids "<来源标识fieldId>,<行动项fieldId>" \
  --all --format json
```

- 以「来源标识」`contain <taskUuid>` 一次拉回该会议已入表的全部记录（taskUuid 全局唯一，不会被同名会议误伤）
- **必须传 `--field-ids` 只取两列**：不限列会把全表全字段拉回，表越大上下文开销越高
- 比对口径：`<taskUuid>#<todoId>` 精确相等 → 重复；`<taskUuid>#summary` 退化为同一 taskUuid 内行动项标题相同 → 重复。重复项跳过并在回执标注"已存在"
- filters 最外层必须是 `and`/`or`；text 字段可用 `eq`/`contain`
- 旧表无「来源标识」列且补不上时，降级为旧口径：备注列 `contain` 会议名 + 行动项标题相同

### E2. 拉回上次遗留项（目标表已有历史记录时）

```bash
dws aitable record query --base-id <baseId> --table-id <tableId> \
  --filters '{"operator":"and","operands":[{"operator":"before","operands":["<截止日期fieldId>","2026-08-24"]}]}' \
  --field-ids "<行动项>,<负责人>,<截止日期>,<状态>,<来源标识>" \
  --all --format json
```

- 为何要做复盘：本技能若只写不更新，表内状态会永远停在"未开始"，几周后退化成一堆无人维护的死数据；而周会真实场景的第一件事就是"上次那几件做完了没"
- 日期字段只能用 `date_eq`/`before`/`after`/`not_before`/`not_after`（通用 `eq`/`lte` 对 date 无效会返回 0 条）；不支持区间与相对时间，要区间用 `not_before` + `not_after` 组合
- 状态过滤在**本地**做（筛出「未开始/进行中」），并排除来源标识属于本次会议的条目
- 能力边界（如实告知）：截止日期留空的未完成项不会被 `before` 命中，不在复盘范围；首次向空表写入时跳过本步

### E3. 展示预览并等待用户确认

按 SKILL.md「展示格式」输出三区列表（建议入表 / 不建议入表 / 上次遗留）。用户确认（可调整、可从"不建议"区捞回）后才执行写入。

**遗留项更新与新增写入是两个独立确认**：先抛写入确认卡片，再抛遗留项多选卡片；用户可以只写新增、不动遗留项。

### E4. 批量写入

```bash
dws aitable record create --base-id <baseId> --table-id <tableId> --records '[
  {"cells":{
    "<行动项fieldId>":"整理 Q2 数据报告",
    "<负责人fieldId>":[{"userId":"<张三userId>","corpId":"<corpId>"}],
    "<协作人fieldId>":[{"userId":"<李四userId>","corpId":"<corpId>"}],
    "<截止日期fieldId>":"2026-08-21",
    "<状态fieldId>":"未开始",
    "<关联议题fieldId>":"Q2 经营分析",
    "<备注fieldId>":"来源会议：《产品项目周会》(2026-08-16)",
    "<来源标识fieldId>":"<taskUuid>#<todoId>"
  }},
  {"cells":{
    "<行动项fieldId>":"输出竞品分析初稿（推断）",
    "<截止日期fieldId>":"2026-08-24",
    "<状态fieldId>":"未开始",
    "<关联议题fieldId>":"竞品讨论",
    "<备注fieldId>":"来源会议：《产品项目周会》(2026-08-16)；负责人待认领：王五（通讯录无唯一命中）",
    "<来源标识fieldId>":"<taskUuid>#summary"
  }}
]' --format json
```

写入格式要点（以 `record create --help` 为准）：

- `text` → 字符串，推断值带「（推断）」后缀；`singleSelect` → 选项名字面量（如 `"未开始"`），不要传 option ID
- `date` → `"2026-08-21"` 或 RFC3339；未解析出截止时间（含"尽快"类）**直接不写该 cell**，不要写空串，更不要硬编日期
- `user` → `[{"userId":"...","corpId":"..."}]`；未匹配到人则不写该 cell，姓名降级进备注列（见第二条示例）
- 备注列固定以「来源会议：《主题》(日期)」开头，多会议合并时供人阅读区分来源
- 「来源标识」每条必填，不得留空（它是下次查重与复盘的唯一依据）；多会议合并时各条带自己的 taskUuid
- 单次最多 100 条；JSON 超长时改用 `--records-file <path>`
- 返回的 recordId 用于回执汇报

### E5. 回写遗留项状态（用户勾选后）

```bash
dws aitable record update --base-id <baseId> --table-id <tableId> --records '[
  {"recordId":"<遗留项recordId>","cells":{"<状态fieldId>":"已完成"}}
]' --format json
```

- 只传需修改的字段，未传字段保持原值；单次最多 100 条
- 状态值必须是 `table get` 返回的实际选项名字面量（如 `"已完成"`），不得传 option ID，不得自造选项名
- recordId 必须来自 E2 的真实返回；部分失败时逐条报告原因，不得静默吞掉

### E6. 输出回执

推断项、待确认项、未匹配人员集中在此列出（日期/人员/单选字段存不了后缀，依据全部落在这里）：

```
已写入 3 条行动项到《产品项目周会·行动项》，跳过 1 条（已存在）：
https://alidocs.dingtalk.com/i/nodes/<baseId>

📊 已为新表补建视图: 「状态看板」（按状态分列）、「我负责的未完成」

🔄 遗留项更新: 2 条 → 已完成（1 条保持进行中）

📌 推断项（请核对）:
- #1 截止日期 2026-08-21 — 依据: 摘要"周五评审前"，按会议日期(08-16)那周的周五换算
- #3 行动项标题 — 依据: 摘要竞品讨论段落，todos 原文仅"行，我来吧"

⏳ 待确认:
- #2 截止日期留空 — 会上只说"尽快"，请定具体期限

👤 未匹配人员:
- #3 "王五" — 通讯录无唯一命中，已写入备注列"负责人待认领：王五"
```

多会议合并时，以上各区按会议分组展示。

## Module F: （可选）创建钉钉待办

回执后用选择卡片（单选）单独询问（"1. 创建待办（列出将给谁建几条） 2. 不创建，仅表格跟踪"）。用户同意后，对每条**有负责人且状态为未开始/进行中**的行动项：

```bash
dws todo task create \
  --title "整理 Q2 数据报告（产品项目周会）" \
  --executors <张三userId> \
  --due "2026-08-21T18:00:00+08:00" \
  --priority 20 \
  --format json
```

- `--executors` 必填，逗号分隔多个 userId（负责人 + 协作人可一并传入）；userId 必须来自 get-self / user search / 听记参与人的真实返回
- `--priority`：10 低 / 20 普通 / 30 较高 / 40 紧急；默认 20，会上明确表述紧急的取 30
- `--due` 必须是 ISO-8601 带时区；行动项只有日期时统一取当天 18:00:00+08:00（时区以本人所在时区为准）；截止留空（含"尽快"类）的待办不传 `--due`
- 没有负责人的行动项跳过建待办，并在回执中说明
- 状态为**已完成/已取消**的行动项一律跳过（含刚在 E5 被标为已完成的遗留项），否则会给已做完的事情发提醒

## 常见坑位速查

| 坑 | 现象 | 规避 |
|---|---|---|
| `minutes list all` 不传 `--limit` | 一周超 10 场时候选静默缺少，用户以为看到的是全部 | 默认只返 10 条，必须显式传 `--limit`（取 30 起）并 `--cursor` 翻页 |
| 听记转写未完成就提取 | todos/summary 为空，误报"本场无行动项" | 先看 `get batch` 返回的听记状态，非转写完成则标注「转写中」不提取 |
| cells 用了 fieldName | 写入报错或字段值丢失 | 建表/复用后必须 `table get` 取 fieldId 再写 |
| `table get` 不传 `--table-ids` | 返回全部表的字段与视图，上下文突增 | 已从 `base get` 拿到 tableId 时必须显式传入 |
| 查重 `record query` 不限列 | 全表全字段拉回，表越大越慢 | 必须传 `--field-ids` 只取必要列 |
| 靠标题字面查重 | AI 推断产出不同字面，重复写入两遍 | 改用「来源标识」`<taskUuid>#<todoId>` 精确比对 |
| 只写不更新 | 表内全是"未开始"，几周后成死数据 | 写入前做 E2 遗留项复盘，用 `record update` 回写状态 |
| 日期字段用 `eq`/`lte` 过滤 | 返回 0 条但不报错，看上去像"没有遗留项" | date 只能用 `date_eq`/`before`/`after`/`not_before`/`not_after` |
| user 字段缺 corpId | record create 局部失败 | corpId 统一取自 A1 `get-self` 返回 |
| singleSelect 传了 option ID | 值写不进或建出脏选项 | 传选项名字面量 |
| 日期以今天为基准换算 | "下周三"算成执行日那周，日期集体偏移 | **基准必须是会议日期**（get info 开始时间），同类技能最常见错误 |
| "尽快"被硬编成日期 | 表里出现造假截止时间 | 不折算，留空进回执待确认清单 |
| 未匹配姓名被臆造成员 | 错误地 @ 到同名他人 | 不写 user cell，姓名降级进备注列 + 回执清单 |
| 日期传相对时间 | 写入失败或值错误 | 以会议日期为基准换算成 YYYY-MM-DD |
| 把 Kanban 视图当成禁区而不建 | 新表只有光秃的默认 Grid，开箱体验差 | 看板**视图**属于本技能；只有 `dashboard`/`chart` 是禁区 |
| 重试/重跑无条件建视图 | 表里出现两个同名「状态看板」 | 建前 `view get` 读目录、同名跳过；建后读回确认 |
| 「我负责的」筛选借 userId 猜本人 | 视图钉死错人，打开是别人的任务 | 负责人只取 `get-self`；空则不建该视图并告知 |
| filterUp/lookup 字段写值 | 只读字段，写入必失败 | 复用旧表遇此类字段直接跳过 |
| 给已完成项建待办 | 用户收到已做完事项的提醒 | Module F 只对状态为未开始/进行中且有负责人的条目建 |
| transcription 全文进上下文 | 上下文爆炸、回复变慢 | 只在必要时拉取且只分析任务相关段落 |
| 多组织未指定 `--profile` | 行动项写进错误企业的表 | 先 `profile list` 确认组织，全链路统一带 `--profile` |
