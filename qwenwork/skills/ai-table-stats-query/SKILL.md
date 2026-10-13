---
name: ai-table-stats-query
description: 使用本机 dws CLI 准确回答指定 AI 表格中的计数、求和、平均值、分组统计、Top N、中位数、去重计数、完整率、比率、百分比、分位数、排名和数据分布问题。用户询问“多少家门店”“有索赔单的门店共有多少家”“多少个客户、商品或员工”等自然语言唯一实体计数时也应触发，即使只提供钉钉 AI 表格链接。整个任务只能读取上游绑定、人设 notable 引用或用户明确链接指定的唯一 Base；禁止列出、搜索、猜测或切换其他 Base。缺少明确 baseId，或指定 Base 不可访问、无匹配数据表时，必须停止并请求补充信息或报告问题。
compatibility: Requires the local dws CLI with the aitable service. The current DWS query surface provides record filtering, sorting, field projection, and complete pagination; statistical aggregation is performed locally over the complete returned record set.
install_source: official
install_method: download
skill_id: official_c7v3mazk
enabled_at: 1791893797479
version: 1.1.0
name_zh: AI表格数据分析助手
---

# AI 表格统计查询（DWS）

使用 `dws aitable` 读取实时结构和记录，再由本地 Agent 计算统计结果。AI 表格操作严格只读，不创建或修改字段、记录、视图和 Base。机器人绑定流程仅设置通信通道，不修改 AI 表格数据。

## 入口选择（AskUserQuestion）

首次触发本 Skill 时，按以下优先级判断是否询问入口，两条规则冲突时以本段为准：

1. 用户已在千问办公对话中直接提出统计问题（如附带 AI 表格链接并说明要查什么）→ 视为默认选项 A，直接执行查询，不再询问入口。
2. 用户只表达"要用这个技能/要绑定机器人"，未附带具体统计问题 → 使用 AskUserQuestion 询问入口：

- 问题："你想在哪里使用 AI 表格统计查询？"
- 选项 A："在千问办公里直接问" — 在当前千问办公对话中直接提问，agent 立即执行查询并返回结果。
- 选项 B："通过钉钉群机器人问" — 先完成机器人绑定到群，之后在钉钉群里 @机器人 提问，查询结果通过机器人回复到群。

用户选择 A 时，跳过绑定流程，直接进入"Base 边界"。

用户选择 B 时，先执行下方"钉钉群机器人绑定流程"，完成后再进入"Base 边界"执行统计查询；查询结果通过 `dws chat message send-by-bot` 发送到已绑定的群。

### 钉钉群机器人绑定流程

以下步骤仅在用户选择"通过钉钉群机器人问"时执行。绑定流程涉及群管理和消息发送，但不修改 AI 表格数据本身。

#### 1. 查找已有机器人

```bash
dws chat bot search --format json
```

`chat bot search` 仅返回当前用户自己创建的机器人，每项包含 `robotCode`（send-by-bot 必需）。

- 有结果：用 AskUserQuestion 列出机器人名称让用户选择要绑定的那一个，提取其 `robotCode`，跳到步骤 3。
- 无结果：继续步骤 2。

#### 2. 创建新机器人（仅在用户没有已有机器人时）

先通过 DWS 创建企业内部应用骨架：

```bash
dws devapp +create --name "AI表格统计查询" --desc "钉钉群内统计查询机器人" --format json
```

此命令需要用户具有开放平台开发者身份。如果返回 `503 当前用户没有开发者身份`，提示用户联系钉钉组织管理员在 open-dev.dingtalk.com 为其添加开发者权限，获取权限后重新触发本流程。

创建成功后返回 `unifiedAppId`，但此时应用还没有机器人能力。剩余网页配置（开启机器人能力、开通权限、发布版本）必须按「电脑自动化优先、单步人工引导兜底」执行，**禁止把全部配置步骤作为纯文字列表一次性输出让用户自行完成**。

##### 2a. 电脑自动化操作（优先路径）

会话中具备浏览器控制 / 电脑操作 / 截图能力时，agent 必须自己完成网页配置，而不是让用户做：

1. 打开 open-dev.dingtalk.com，进入 `unifiedAppId` 对应的「AI表格统计查询」应用。
2. 左侧「机器人与消息推送」→ 开启机器人能力 → 填写机器人名称和描述（与创建应用时一致）。
3. 「权限管理」→ 确保已开通：群消息发送、群会话管理、通讯录读取。
4. 「版本管理与发布」→ 创建版本 → 发布（企业内部应用无需审核）。

要求：

- 每完成一步用页面状态验证；发布完成后执行 `dws chat bot search --format json` 确认 `robotCode` 已出现。
- 遇到扫码登录、验证码、二次确认等无法自动完成的环节，截图或说明当前卡点，用 AskUserQuestion 请用户协助该单一动作，协助完成后继续自动化，不要把剩余流程转成文字说明。
- 自动化失败的具体步骤回退到 2b 对应单步引导，其余步骤仍尽量自动化。

##### 2b. 单步人工引导（仅在无法电脑操作时）

会话中没有浏览器控制能力，或自动化被登录/权限阻断且无法恢复时，用 AskUserQuestion 逐 步引导，规则：

0. 引导开始前，agent 必须先用 shell 命令把目标页面在用户默认浏览器中打开，而不是让用户自己输入网址导航：macOS 用 `open "<URL>"`，Windows 用 `start "<URL>"`。打开顺序：
   1. 应用管理列表页（开发引导页/首页用户找不到应用，必须用此页定位应用）：`https://open-dev.dingtalk.com/fe/app?hash=%23%2Fcorp%2Fapp#/corp/app`，让用户在列表中点击刚创建的应用名进入详情。
   2. 已知 `unifiedAppId` 时可再尝试直达 `https://open-dev.dingtalk.com/app/<unifiedAppId>`，打不开或落在引导页则回退应用管理列表页。
   3. 禁止只打开 `https://open-dev.dingtalk.com` 首页让用户自己找入口。后续每一步凡是涉及打开新页面的，都由 agent 用 shell 打开。

1. 每次只给一个步骤的具体操作，用 AskUserQuestion 提出，选项固定为「已完成，下一步」和「卡住了，需要帮助」。
2. 引导优先采用「图文方式」：用户提供过平台截图时，在对应步骤的提问描述里引用截图内容标注操作位置（菜单名/按钮名/开关名）；会话有截图能力时也可自行截图辅助。没有截图素材时退回纯文字，但必须包含具体菜单名、按钮名和预期结果。
2. 第 1 步：打开 open-dev.dingtalk.com → 进入刚创建的应用。用户确认后再给第 2 步：开启机器人能力。依次第 3 步：权限管理开通三项权限；第 4 步：版本发布。
3. 每步描述必须包含具体的左侧菜单名称、开关/按钮名称和预期结果，不使用抽象描述；具备截图能力时附截图标注操作位置。
4. 用户选「卡住了」时，询问卡住的具体位置（页面名/按钮名），给出针对该卡点的下一步指引，不要重复整个步骤列表。
5. 用户未确认完成前不得推进到下一步。

发布完成后，重新执行 `dws chat bot search --format json` 获取新建机器人的 `robotCode`。若 `robotCode` 未出现，说明网页配置未完成，回到 2a/2b 定位并补齐缺失的步骤，不要带病进入后续群绑定。

#### 3. 查找或创建目标群

用户已提供群名时搜索：

```bash
dws chat search --query "<群名关键词>" --format json
```

从返回结果中提取 `openConversationId`。搜索返回多个群时，列出候选群让用户确认目标群，不要自行假定。

用户没有现成的群时，可用以下命令新建群，当前用户自动成为群主：

```bash
dws chat group create --name "<群名>" --users <userId1>,<userId2> --format json
```

`--users` 最多 20 人，用户本身会自动加入无需包含。

#### 4. 将机器人添加到群

```bash
dws chat group members add-bot --robot-code <robotCode> --id <openConversationId> --format json
```

如果返回"机器人不存在"错误，先执行 `dws chat group bots --group <openConversationId> --format json` 检查机器人是否已在群内。已在群内则跳过此步。

#### 5. 验证绑定并发送测试消息

```bash
dws chat group bots --group <openConversationId> --format json
```

确认机器人出现在群机器人列表后，发送测试消息确认链路通畅：

```bash
dws chat message send-by-bot \
  --robot-code <robotCode> \
  --group <openConversationId> \
  --title "绑定成功" \
  --text "AI 表格统计查询已绑定到本群。现在你可以在群里 @我 提问统计问题了，例如：'这个表格里有多少条记录？'" \
  --format json
```

#### 6. 记录绑定关系

将以下信息记录到上下文中，供后续统计查询结果推送使用：

- `robotCode`：机器人标识
- `openConversationId`：群会话 ID
- 群名和绑定的 Base 链接

后续用户在群里 @机器人 提问统计问题时，agent 执行完查询后通过以下命令将结果回复到群：

```bash
dws chat message send-by-bot \
  --robot-code <robotCode> \
  --group <openConversationId> \
  --title "<统计结果标题>" \
  --text "<查询结果Markdown>" \
  --format json
```

## Base 边界

以下规则优先于所有查询和降级策略：

1. `baseId` 只能来自上游明确绑定、人设中的合法 AI 表格引用，或用户明确提供的 AI 表格链接。
2. 解析后立即冻结该 `baseId`；所有 DWS 命令都必须使用同一个值。
3. 禁止调用 `dws aitable base list`、`dws aitable base search`、`dws aitable list`、`dws aitable search`，以及任何列出最近 Base、搜索或发现 Base 的快捷命令。
4. 没有明确 `baseId` 时，不运行任何 `dws aitable` 命令，直接请用户提供目标 AI 表格链接或检查上游绑定。
5. 指定 Base 不存在、不可访问或缺少目标表/字段时，只能在该 Base 内澄清；不能尝试其他 Base。
6. 如果误执行了 Base 发现命令，不得使用其结果继续任务，应立即停止并说明边界被破坏。

### notable 绑定

人设或上游上下文中的以下格式是合法绑定：

```text
@[AI表格](notable://ai-table?baseId=<baseId>)
```

对查询参数做标准 URL 解码并读取非空 `baseId`。展示文字不是 Base 名称。出现多个不同 `baseId` 且没有明确本次目标时先询问，不能逐个尝试。

## DWS 能力边界

当前本机 DWS 版本没有独立的整表统计或分组聚合子命令。不要虚构统计命令，也不要通过 `dws api` 猜测未确认的接口。

统计流程统一为：

1. 用 DWS 获取 Base、表和字段元数据。
2. 用 `dws aitable record query` 在服务端完成可表达的过滤、字段裁剪和排序。
3. 标量、去重、分组、比率、排名、分位数和逐行派生指标都在完整返回记录集上本地计算。
4. 需要完整范围时使用 `--all --page-limit 0`。默认 `--page-limit 50` 最多只覆盖 5000 条记录，不能用于完整统计。
5. 结果只有在自动分页确实遍历到结束且没有权限或传输错误时才能声称覆盖全部匹配记录。

统计任务不得读取通用文档内容、页面快照或导出的不明版本文件代替 DWS 实时记录查询。

## 命令映射

| 操作 | DWS 命令 |
| --- | --- |
| 获取指定 Base 目录 | `dws aitable base get --base-id <BASE_ID>` |
| 获取表、字段和视图目录 | `dws aitable table get --base-id <BASE_ID> [--table-ids <TABLE_IDS>]` |
| 获取字段完整配置 | `dws aitable field get --base-id <BASE_ID> --table-id <TABLE_ID> [--field-ids <FIELD_IDS>]` |
| 搜索选项 | `dws aitable field search-options --base-id <BASE_ID> --table-id <TABLE_ID> --field-id <FIELD_ID> [--keyword <TEXT>]` |
| 查询或遍历记录 | `dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> ...` |
| 获取视图详情 | `dws aitable view get --base-id <BASE_ID> --table-id <TABLE_ID> [--view-ids <VIEW_IDS>]` |

参数不确定时查看对应命令的 `--help`，不能沿用旧接口参数名称。

## 标准流程

### 1. 读取指定 Base

首次 AI 表格命令必须是：

```bash
dws aitable base get --base-id <FROZEN_BASE_ID>
```

随后读取表结构。链接中有 `sheetId` 时优先把它作为候选 `tableId`：

```bash
dws aitable table get --base-id <FROZEN_BASE_ID> --table-ids <TABLE_ID>
```

没有 `sheetId` 时可读取同一 Base 内全部数据表并按名称和结构定位。确认 table、fields 和 views 都属于冻结 Base。

### 2. 建立字段映射

将用户概念映射到字段名称、`fieldId` 和类型。涉及选项、公式、日期格式或其他完整配置时执行：

```bash
dws aitable field get \
  --base-id <FROZEN_BASE_ID> \
  --table-id <TABLE_ID> \
  --field-ids <FIELD_IDS>
```

字段映射必须唯一且语义一致。字段同名但类型或业务含义不匹配时不能直接使用；多个合理候选无法区分时提出一个简短问题。

### 3. 确定答案单位

在读取记录前先区分：

- **记录行**：“多少条订单/记录/帖子”统计匹配行数。
- **唯一实体**：“多少家门店/客户/商品”对实体字段去重，同一实体多行只算一次。
- **分组指标**：“各门店平均值/每个平台合计”先按字段分组再计算指标。
- **记录明细**：“列出订单/前 10 条”返回真实记录行。
- **逐行派生指标**：“平均生产周期/总金额”先对每条记录计算日期差或乘积，再聚合。

### 4. 设计最小字段查询

只查询完成问题所需的条件字段、分组字段、数值字段和展示字段。完整统计使用：

```bash
dws aitable record query \
  --base-id <FROZEN_BASE_ID> \
  --table-id <TABLE_ID> \
  --field-ids '<FIELD_ID_1>,<FIELD_ID_2>' \
  --filters '<FILTER_JSON>' \
  --all \
  --page-limit 0
```

省略不需要的 `--filters`。公式、引用和关联字段只有在 `--field-ids` 中显式指定才会返回。

过滤结构：

```json
{
  "operator":"and",
  "operands":[
    {"operator":"eq","operands":["<FIELD_ID>","<VALUE>"]}
  ]
}
```

支持的常用操作符包括：

- 通用：`eq`、`ne`、`exist`、`un_exist`
- 数字：`lt`、`gt`、`lte`、`gte`
- 文本：`contain`、`exclusive`
- 多选：`all_of`、`any_of`、`none_of`
- 日期：`date_eq`、`before`、`after`、`not_before`、`not_after`

注意：

- 单选和多选过滤值使用选项名称字面量，不使用 option ID。
- 日期字段不能使用通用 `eq/gte/lte`；范围使用 `not_before` 与 `not_after` 组合。
- 数字比较值传 JSON 数字，不传数字字符串。
- “有索赔单”等语义不能只用 `exist`；数值字段通常使用 `gt 0`。

## 本地统计规则

### 记录计数

完整遍历后统计返回记录数。若响应提供明确的全量 `total`，可与本地行数交叉验证；单页数量不能当作总数。

### 唯一实体计数

查询条件字段和实体字段，服务端过滤后对实体值本地去重。默认排除空值；必要时规范化首尾空格，但不要擅自合并大小写、别名或不同门店编码。报告所用规范化规则。

### 求和、平均值和范围

只对可解析数值参与计算：

- `SUM`：所有有效数值相加。
- `AVG`：有效数值总和除以有效数值数量，不用匹配行数作分母。
- `MIN/MAX/RANGE`：基于有效值；`RANGE = MAX - MIN`。
- 空值、非法值和非有限值排除，并报告有效样本数与被排除数量。

货币和百分比先确认存储单位。百分比字段若以 `0.15` 表示 15%，计算时保留原始数值，展示时再格式化。

### 分组统计和排名

完整查询分组字段及全部指标字段，在本地按规范化分组键聚合。多级排名应在同一完整分组结果上完成，避免两个阶段使用不同样本范围。

分组 Top N 不依赖服务端记录排序；先计算完整分组结果，再按指标排序。指标相同时使用稳定、可解释的次级顺序，并说明是否包含并列。

### 中位数和分位数

对完整有效数值排序：

- 中位数：奇数取中间值；偶数默认取中间两值平均。
- 分位数：先确认或说明所用约定，例如最近秩法或线性插值。
- 不能根据第一页或抽样估算“精确”分位数。

### 去重率、完整率和条件比率

- 去重率：唯一非空值数量 ÷ 非空值数量。
- 完整率：非空值数量 ÷ 匹配记录数量。
- 任意条件比率：分子和分母必须来自同一冻结 Base、同一表、同一字段口径和同一次完整数据快照；能在一次查询结果中计算时不要分两次查询。
- 分母为零时返回“无法计算”，不能返回 0%。

### 逐行派生指标

当前 DWS 没有聚合命令，因此允许对完整查询结果做本地逐行计算，但必须明确口径：

1. 只查询参与公式的源字段和必要条件字段。
2. 对每行验证类型、缺失值和异常值。
3. 日期差先统一时区；确认按自然日、精确小时、含首尾天数还是工作日计算。
4. 单价乘数量等运算使用原始数值，不先做展示舍入。
5. 聚合时报告有效行数、排除行数和公式口径。
6. 无法确定计算口径时先询问，不创建公式字段替代澄清。

若表中已有语义匹配的公式字段，可读取少量源字段和公式字段核对口径；但公式样本异常或缺失时应改用明确的源字段本地计算，不能把空结果解释为零。

## 明细和列表查询

原始 Top N 明细可让服务端排序并限制返回量：

```bash
dws aitable record query \
  --base-id <FROZEN_BASE_ID> \
  --table-id <TABLE_ID> \
  --field-ids '<DISPLAY_FIELD_IDS>' \
  --filters '<FILTER_JSON>' \
  --sort '[{"fieldId":"<METRIC_FIELD_ID>","direction":"desc"}]' \
  --limit 10
```

“前 10 条记录”严格返回 10 条；“前 10 个名次并包含并列”需要继续检查边界值。

用户未指定列表展示数量时：

1. 用完整查询确认准确总数，但最终只展示前 20 条。
2. 超过 20 条时说明总数、折叠数量和“如需完整展示请明确说展示全部”。
3. 用户明确说“全部、完整展示、不折叠”时展示完整结果；受回复长度或权限限制时如实说明。
4. 展示上限不影响统计范围。

发生折叠时提供当前原始 AI 表格链接。优先复用用户提供的同一 Base、Table、View 链接；否则从当前元数据确认 `tableId/viewId` 后构造：

```text
https://alidocs.dingtalk.com/i/nodes/<baseId>?iframeQuery=sheetId%3D<tableId>%26viewId%3D<viewId>
```

不能猜测 `viewId`，也不能为了补链接搜索其他 Base。

## 完整性和失败处理

- `--all` 未遍历到空 cursor、命令报错或触及非零 `--page-limit`：结果不完整，不能声称是全表统计。
- 大表查询成本很高时可以提前提示，但不能用第一页估算精确结果。
- 字段不存在或类型不兼容：停止或请求澄清，不用名称相近字段替代。
- 数值或日期解析失败：排除并报告数量；若异常比例可能改变结论，明确警告。
- 记录在查询过程中持续变化：无法获得一致快照时说明统计时间和潜在漂移。
- 权限不足：报告指定 Base 的读取权限问题，不切换 Base。
- 全程禁止调用任何创建、更新或删除命令，即使用户允许新建公式字段。

## 回复格式

先给结论，再简要说明：

- 统计范围和生效过滤条件。
- 记录数、有效样本数或唯一实体口径。
- 货币、百分比、日期和小数的合适格式。
- 分组或 Top N 使用紧凑表格。
- 缺失值、异常值、分位数约定或逐行公式会实质影响结果时说明口径。
- 列表折叠时报告准确总数、折叠数和原始表格链接。

不要向用户展示内部字段 ID、Base ID、原始 DWS 响应或本地临时数据文件。

用户通过钉钉群机器人提问时，将完整回复通过以下命令发送到绑定的群，不在千问办公对话中重复展示：

```bash
dws chat message send-by-bot \
  --robot-code <robotCode> \
  --group <openConversationId> \
  --title "<统计结果标题>" \
  --text "<Markdown格式的查询结果>" \
  --format json
```

消息内容按 Markdown 渲染；换行必须使用真实换行符（U+000A）而非字面量 \n，且需用空行做段落分隔或行尾两空格+换行做硬换行。

## Skill 自检场景

1. “有索赔单的门店共有多少家”：用数值 `gt 0` 过滤，完整查询门店字段后本地去重。
2. “所有订单平均客单价和总营业额”：完整查询两个数值字段，分别计算有效样本 AVG 和 SUM。
3. “下单转化率前五门店中的入店转化率前三”：一次完整查询门店和两个指标，本地分组并完成两级排名。
4. “营业额最高 10 条明细”：服务端字段裁剪、降序和 `limit 10`，不做分组聚合。
5. “平均生产周期”：查询状态和两个日期字段，按明确日期差口径逐行计算后求平均，不创建公式字段。
6. 未提供 Base：不运行 DWS，直接请求链接。
7. Base 内没有目标表或字段：停止并报告，不搜索或切换 Base。
8. 完整统计超过 5000 条：必须使用 `--all --page-limit 0`，不能接受默认页数上限。
9. 用户选择"通过钉钉群机器人问"且已有机器人：bot search 返回结果 → AskUserQuestion 选机器人 → chat search/create group → add-bot → group bots 验证 → send-by-bot 测试消息，完成后进入 Base 边界。
10. 用户选择"通过钉钉群机器人问"但没有机器人：bot search 返回空 → devapp +create 创建应用骨架 → 返回 503 时提示找管理员开开发者权限 → 创建成功后网页配置机器人能力并发布：优先用浏览器自动化自己完成（每步验证，卡点单动作求助），无法自动化时用 AskUserQuestion 单步引导（一次只给一个步骤，含具体菜单/按钮名，禁止一次性输出全部文字步骤）→ 重新 bot search 获取 robotCode，未出现则定位补齐缺失步骤 → 继续群绑定。
11. 机器人已在群内：add-bot 报"机器人不存在"时，用 group bots 确认已在群内，跳过添加直接发送测试消息。
12. 钉钉群内提问后结果推送：完成统计查询后，通过 send-by-bot 将 Markdown 格式的结果发送到绑定的群，不在千问办公对话中重复展示。
