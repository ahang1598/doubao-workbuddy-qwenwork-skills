---
name: dingtalk-msg-task-tracker-aitable
displayName: 钉钉消息任务追踪-AI表格
name_en: dingtalk-msg-task-tracker-aitable
description: 汇总最近24小时(或指定窗口)钉钉里的双向任务流转,来源固定为5路:群里@我/我发出的单聊任务/别人发我的单聊任务/DING/待办。归类合并同一问题的跨轮讨论,跨天未闭环的问题更新原行不新建,生成日报摘要并推送Markdown卡片到钉钉。当用户说"看下今天钉钉里别人反馈给我的问题""汇总最近一天的反馈到表格""今天我派了什么任务给别人""收下24小时内的问题反馈""检索未完成任务+最新反馈"或类似需求时触发。
description_en: Aggregates bidirectional task flow from DingTalk over the last 24 hours from 5 sources(group @mentions, outgoing DMs, incoming DMs, DING, TODOs). Merges multi-round discussions, updates existing rows for unresolved items, generates digest and pushes to DingTalk.
argument-hint: 时间窗口(默认最近24小时)
argument-hint-en: Time window (default last 24 hours)
user-invocable: "true"
version: 1.1.0
install_source: official
install_method: download
skill_id: official_AQ0A3s0L
enabled_at: 1791893826502
name_zh: 聊天消息任务追踪-AI表格
---

# 钉钉消息任务追踪-AI表格

把最近 24 小时（或用户指定窗口）钉钉里所有反馈/任务派发给当前用户的消息，去重合并后写入指定 AI 表格，并按"已完成 / 处理中 / 未回复"分级汇报，最终推送日报到钉钉。

## 适用场景

- "看下今天钉钉里别人反馈给我的问题" / "24 小时内谁给我提了问题"
- "把今天钉钉反馈的问题写到 <Base 链接>"
- "每天下午 6 点自动汇总今天的反馈"
- "检索表里未完成的任务，并把今天新的反馈追加进去"
- "看下表里 P0 卡了几天没进展 / 帮我催一下"
- "把所有 P0 还在进展的任务催办给负责人"
- "今天我派了什么任务给别人"
- "收下 24 小时内的问题反馈 + 我的派发"

## 前置依赖

本技能依赖 **DingTalk（DWS 钉钉工作空间）** 连接器（key: `qwenwork.settings.connector.builtin.dws`）。

- 用途：消息采集（群聊/@/单聊/DING/待办）、联系人搜索、附件下载、AI 表格读写、消息推送
- 类别：builtin
- 认证方式：OAuth（通过 dws profile 绑定钉钉组织）

### Step 0 — 连接器就绪性检查（必做，每次执行前）

1. 调用 `qw_query` 查询连接器状态：
   key = "qwenwork.settings.connector.builtin.dws"
2. 根据返回字段分支处理：

| 状态组合 | 处置动作 |
|---|---|
| installed=false | 调 qw_action execute install，或 open 打开连接器设置页引导安装 |
| enabled=false 且 agentCanEnable=true | 调 qw_action enable |
| enabled=false 且 agentCanEnable=false | 调 qw_action open 设置页，输出提示语，暂停等待用户开启，不要重试轮询 |
| enabled=true 且 status≠connected | 调 qw_action connect（OAuth），或提示用户完成钉钉授权认证 |
| enabled=true 且 status=connected | 进入第 3 步 |

3. 每次分支处理后，重新 query 一次确认状态，再决定是否推进。
4. 连接器就绪后，执行 `dws profile list --format json` 取当前 corpId（写 user 字段必需）和 userName（用户花名）；若返回的 profile 无活跃组织，提示用户先完成钉钉授权绑定。
5. 若用户明确拒绝开通，礼貌说明"没有该连接器我无法拉取钉钉消息，能否由你手动粘贴消息内容作为替代？"，不要硬闯。

## 快路径清单（先看这里，能省 40% 时间）

执行任何一次前，先把下面 8 条"正反例"过一眼：

1. `dws chat message list` **只支持** `--time + --direction newer/older` 单边界窗口；`--start/--end` 会被拦截。想拿 24h 全量就 `--time <WINDOW_START> --direction newer`，然后按 `openMessageId` 去重。
2. `dws chat message list --user <userId>` 里的 `<userId>` **必须是数字 userId**（如 `106482`），**不是** `senderOpenDingTalkId`（`Dn6...` 开头）；传错会报 `peerUid is required`。数字 userId 从 `dws contact user search --query <花名>` 拿。
3. `dws chat message list --group <cid>` 才是群聊；`--open-dingtalk-id` 是备用参数，优先用 `--group`。
4. `dws chat message download-media --resource-id` 遇到 `$iwEc...` 开头的 mediaId **必须用单引号**包裹，否则 shell 会把 `$iwEc` 当变量吞掉；`@lQL...` 开头的可以不管，但统一单引号最保险。
5. `dws aitable record create --records` 内联 JSON 在受管 shell 里会因 `{}` 或 `@` 被展开而失败。默认走 **`--records-file <abs-path>`**：先用 `python3 -c "import json; json.dump(data, open(...))"` 生成干净 JSON，再传 file 路径，不要用 heredoc 拼多行 JSON。
6. `dws aitable attachment upload` 返回的 `uploadUrl` 里 `Expires` 只有约 60 秒，`upload → curl PUT` 之间**不要插入其他耗时命令**；一次失败就重新 apply upload，别在旧 URL 上重试。
7. **批量更新优化（性能关键）**：`dws aitable record update` **支持批量更新**，把所有待更新记录合并到 1 个 JSON 文件，1 次调用完成。不要逐条 write JSON + update（会浪费 N×2 次串行 bash 调用）。
8. **python subprocess 里调 dws 不会真正执行**（只返回 pending 占位），必须 Bash 直调。

**group 字段写入格式（易错点）**：AI 表格里 group 字段的 key 是 `openConversationId`，**不是** `cid`。通过 `--records-file` 写入时直接写数组（不加 `{"value": ...}` 包装）：

```json
{"cO9UArX": [{"openConversationId": "cidXXX=="}]}
```

写入后 UI 会自动显示群聊名称。群聊消息必须填此字段，单聊消息可不填。

**group 字段 create 后需 update 补写**：`record create` 时 group 字段写入后回读可能为空，必须对所有含群聊的记录逐条执行 `record update` 补写 `cO9UArX`，格式同 create。

**优先级字段 create 时必须写入**：`muPF9HZ` 是单选，直接写选项 ID 字符串（P0=`uo2m63vEUU`、P1=`sSLG7oqZxU`、P2=`u28B5DtRnl`）。判定规则：含 P0/高优/阻塞/故障/客户/线上 → P0；bug/功能异常 → P1；咨询/已闭环 → P2。

**不建新表**：任务统一追加到固定表 `dqUs6bi`（fieldId 硬编码，见步骤 4）。Base 丢失才用 `dws aitable base create --name "钉钉任务日报" --template-id 1826` 重建（模板继承全部 ID）。

## 前置输入

1. Base 与表：当前固定为 `lyQod3RxJKe9QjOMil5rjx31Wkb4Mw9r`（名称"钉钉任务日报"）/ `dqUs6bi`，不需要问用户；仅当用户原文明确指定写到别的 Base 时才用用户给的。**如果 Base 不可访问（报错 BASE_NOT_FOUND / INVALID_BASE_ID），立即用 `dws aitable base create --name "钉钉任务日报" --template-id 1826` 重建，然后 `table get` 确认日期字段 fieldId。**
2. 时间窗口：默认"最近 24 小时"，允许用户指定。
3. 固定追加到「钉钉任务日报」（dqUs6bi），不再建新表；fieldId/选项 ID 全部硬编码（见步骤 4），**但日期字段 fieldId 每次重建后可能变化，必须 table get 动态确认**。
4. 定时任务：用户已明确不需要，默认跳过；仅用户主动要求时才按 8.3 创建。

## 执行步骤

### Step 1：确定当前身份和时间窗口

```bash
date '+%Y-%m-%d %H:%M:%S %z'
dws profile list --format json
```

从 `profile list` 取当前 `corpId`（写 `user` 字段必需）和 `userName`（用户花名）。

### Step 2：并行拉取 5 个来源

来源覆盖必须完整，缺一不可（**不拉未读会话、不拉特别关注**，噪声大且用户不关心）：

```bash
# 1) 群里@我的消息（跨群）
dws chat message list-mentions \
  --start "<WINDOW_START_ISO>" --end "<WINDOW_END_ISO>" \
  --limit 100 --cursor 0 --format json

# 2) DING 消息列表
dws ding +list --type ALL --format json

# 3) 待办列表（别人指给我的任务）
dws todo task list --size 50 --status TODO --format json

# 4) 我发出的单聊（收集"我派发给别人"的任务）
dws chat message list-by-sender --sender-user-id <MY_USER_ID> \
  --start "<WINDOW_START_ISO>" --end "<WINDOW_END_ISO>" --limit 100 --format json

# 5) 别人发我的单聊（收集"别人派发给我"的任务）
dws chat message list --user <PEER_USER_ID> \
  --time "<WINDOW_START>" --direction newer --limit 100 --format json
```

对每个"1/3/4/5 里出现过、但还没完整对话上下文的群聊/单聊"，再补拉一次全量。

**连接器调用约定**：本连接器的工具经 dws CLI 暴露，直接 Bash 调用对应命令即可；若以 MCP 工具形式调用，先 `qwenwork_mcp_tool_list` 找工具，再 `qwenwork_mcp_tool_get` 取 schema，最后 `qwenwork_mcp_tool_call` 执行。遇到 401/403/token 失效/钉钉授权过期，回到 Step 0 重新走认证分支，不要在失效会话上反复重试。

**关键坑**：
- `chat message list` 单次上限约 93-100 条，`hasMore` 可能恒 true；消息量大要多时间窗分段查询，再按 `openMessageId` 去重。
- `list-mentions` 需要 ISO-8601 时间格式（如 `2026-08-16T16:04:00+08:00`）。
- `list-all`/`chat message list` 用的时间格式是 `YYYY-MM-DD HH:mm:ss`。
- `ding +list` 用 `--cursor`+`--type`，`todo task list` 用 `--size`+`--page`。

### Step 3：按窗口过滤 + 按问题归类合并 + 构建附件清单

- 严格保留 `createTime` 落在窗口内的消息。
- 24 小时内无新增的来源（如待办、DING）明确说明"无新增"，不占用记录。
- 归类规则：
  - 同一问题的多轮讨论（提问→追问→排查→结论）合并为 1 条记录。
  - 纯寒暄/表情回应/"好的收到"不单独成条。
  - "别人 @我的追问" + "跟进的历史 bug"合并；`最新进展` 字段聚合最新状态。
  - 单聊追问 + 后续截图/补充合并；截图可作为该记录的附件。
  - `反馈人` 优先写"最新发起追问的人"或"主要复现方"，多人时用 `/` 分隔并在 `反馈人名称` 字段说明。

**构建附件清单（必做，不可跳过）**：归类合并完成后，扫描所有保留消息的 content 字段，用正则 `mediaId=([^)\s]+)` 提取每个 mediaId，建立如下映射：

```
附件清单 = [
  {mediaId, openMessageId, openConversationId, 归属记录摘要, sender, createTime}
]
```

此清单是 Step 6 附件处理的输入。**如果清单非空，则 Step 6 必须执行；清单为空才能跳过 Step 6。** 把清单条数显式输出（如"检测到 N 张图片附件，需处理"），不要静默跳过。

### Step 4：固定表追加（不建新表，ID 硬编码）

所有任务写入固定表，fieldId/选项 ID 永久不变，直接硬编码，无需每次 table get：

- Base：`lyQod3RxJKe9QjOMil5rjx31Wkb4Mw9r`（名称"钉钉任务日报"）
- 表：`dqUs6bi`「钉钉任务日报」
- fieldId：**日期字段需动态确认**（见下方说明）｜方向=`dVBW3We`｜任务/问题摘要=`KLP99tv`｜详细内容=`6hJ2h9A`｜对方=`TG65buT`｜对方名称=`lGQjiHY`｜来源=`XY9hgbt`｜来源群/单聊=`cO9UArX`｜最新时间=`dKh2alZ`｜最新进展=`x0RJRgv`｜状态=`BDwWcfK`｜消息条数=`KUp3qYU`｜附件=`X86pbLC`｜优先级=`muPF9HZ`
- **日期字段 fieldId 动态确认**：每次执行前用 `dws aitable table get --base-id <BASE_ID> --table-id dqUs6bi --format json` 查一次，找 type=date 的字段。当前值为 `8pWqEMn`（名称"日期"）。模板 1826 重建后此 ID 会变（历史值：WCk1Ut1 → mXHl9cL → MmrOhpp → 8pWqEMn），**不能硬编码，必须每次动态取**。
- 选项 ID：方向 别人派发给我=`t98U5f2hiY`、我派发给别人=`Zdr3zYX8EO`；状态 待处理=`XiDBm2DtBF`、处理中=`dT0kSp265M`、待答复=`fzpf8wDf18`、已完成=`60awy4EzOK`；来源 群聊-@我=`tQ0z3nRqRV`、群聊-其他=`tiVvs6sUvd`、单聊=`QshSxJyx5p`、待办=`PGBjAGbuwA`、DING=`Y2632hogNk`；优先级 P0=`uo2m63vEUU`、P1=`sSLG7oqZxU`、P2=`u28B5DtRnl`

**优先级赋值规则（create 时必须写入）**：摘要含 P0/高优/阻塞/故障/客户/线上 → P0；影响用户使用的 bug/功能异常 → P1；咨询/答疑/已闭环 → P2。写入格式（单选，直接写选项 ID 字符串）：

```json
{"muPF9HZ": "uo2m63vEUU"}
```

**group 字段写入格式（易错点，必须严格按此格式）**：

- key 必须是 `openConversationId`，不是 `cid`
- 值是消息里的 `openConversationId` 字段值，通常以 `cid` 开头、`==` 结尾
- 写入格式：

```json
{"cO9UArX": [{"openConversationId": "cidXXX=="}]}
```

- **create 后必须 update 补写**：record create 时 group 字段写入后回读可能为空，必须对所有含群聊的记录逐条执行 record update 补写。update 格式与 create 完全相同：

```json
[{"recordId": "recXXX", "cells": {"cO9UArX": [{"openConversationId": "cidXXX=="}]}}]
```

- 回读时服务端会返回 cid（数字）和 name（群聊名称），这是正常的，写入时只需传 openConversationId。

**灾备后 fieldId 变化**：模板 1826 重建后，日期字段 fieldId 会变（历史：WCk1Ut1 → mXHl9cL → MmrOhpp → 8pWqEMn），**必须 table get 动态确认**，其余字段不变。

跨天规则：同一问题昨天已建行、今天仍有进展的，**不新建行**，用 `dws aitable +find-record` 或 `record query` 关键词找到 recordId 后 `record update` 更新最新进展/最新时间/状态，日期保持首次。只有窗口内的新问题才 record create。

**灾备**：Base 万一丢失，用 `dws aitable base create --name "钉钉任务日报" --template-id 1826` 一键重建——模板继承上述全部 tableId/fieldId/选项 ID/视图/仪表盘 ID（实测）；重建后只需补建聚合表 `SzlmKuE`（模板不含它）。重建后必须 `table get` 动态确认日期字段 fieldId。

### Step 5：解析反馈人身份

```bash
dws contact user search --query '<SENDER_NAME>' --format json
```

- 多个结果时优先 `openDingTalkId` 与消息里 `senderOpenDingTalkId` 匹配的那条。
- 无法通过 openDingTalkId 匹配时选与当前 profile corpName 一致的结果。
- user 字段写入固定用 `[{"userId":"<ID>","corpId":"<CURRENT_CORP_ID>"}]`。

### Step 6：检测、下载消息附件并上传 AI 表格（必做，不可跳过）

> **强制规则**：如果 Step 3 构建的附件清单非空，本步骤**必须执行**。不允许在附件清单非空时跳过本步骤直接进入 Step 7。只有在附件清单确认为空（"检测到 0 张图片附件"）时才可跳过。
>
> **download-media 可用性**：`dws chat message download-media` 当前对 `$iwEc...` 和 `@lQL...` 两种格式的 mediaId 均可正常下载。如果下载失败，重试 1 次；仍失败则记录失败的 mediaId 并在日报中标注"附件下载失败"，但**不能因此跳过整个 Step 6**——其他成功的附件仍需正常上传写入。

**6.1 检测图片附件**

消息内容中含 `[图片消息](mediaId=...)` 的即为图片附件。mediaId 有两种格式：
- `$iwEc...` 开头：必须用单引号包裹，否则 shell 会把 `$iwEc` 当变量吞掉
- `@lQL...` 开头：可以不管，但统一单引号最保险

提取方式：从消息 content 字段中正则匹配 `mediaId=([^)\s]+)`，每条消息可能含多张图片。

**6.2 下载到本地**

```bash
dws chat message download-media \
  --type mediaId --resource-id '<MEDIA_ID>' \
  --message-id '<OPEN_MESSAGE_ID>' \
  --open-conversation-id '<OPEN_CONVERSATION_ID>' \
  --output '<LOCAL_DIR>/<sender>_<HHMMSS>.jpg'
```

**6.3 查大小 + MIME**

```bash
ls -la <LOCAL_FILE>
file --mime-type <LOCAL_FILE>
```

**6.4 申请上传到 AI 表格**

```bash
dws aitable attachment upload --base-id <BASE_ID> \
  --file-name '<NAME>.jpg' --size <BYTES> --mime-type 'image/jpeg'
```

返回 JSON 中含 uploadUrl 和 fileToken。uploadUrl 有效期仅约 60 秒，必须在 60 秒内完成 PUT 上传。

**6.5 PUT 上传**

```bash
curl --fail-with-body -X PUT '<UPLOAD_URL>' \
  -H 'Content-Type: image/jpeg' --data-binary '@<LOCAL_FILE>'
```

必须等 PUT 返回 HTTP 200 才能把 fileToken 写入记录。不允许把外链/uploadUrl 直接塞进附件字段。

**6.6 把 fileToken 写入记录的附件字段**

附件字段 fieldId 为 `X86pbLC`，写入格式为 fileToken 数组：

```json
{"X86pbLC": ["fileToken1", "fileToken2"]}
```

- 如果 create 时已有 fileToken，直接放入 cells
- 如果 create 后才上传完，用 record update 补写（和 group 字段补写同理）
- 同一问题的多张图片，fileToken 放在同一个数组里

**性能注意**：upload 到 PUT 之间不要插入其他耗时命令；一次失败就重新 apply upload，别在旧 URL 上重试。

### Step 7：写入记录 + 回读验证

> **create 前强制关卡**：在调用 `record create` 之前，必须确认以下条件全部满足：
> 1. Step 3 构建的附件清单中每个 mediaId 都已完成 download → upload → PUT，且 fileToken 已收集。
> 2. 如果附件清单非空但 fileToken 未收集，**不允许执行 record create**——必须先回头完成 Step 6。
> 3. create JSON 中每个含附件的记录，`X86pbLC` 字段必须填入对应的 fileToken 数组。
> 4. 输出确认语句："附件清单 N 张，已处理 N 张，fileToken N 个，可以 create"——未输出此确认不允许 create。

- 每条问题独立一行；同一问题跨轮讨论合并为一行，附件数组里可以放多个 token。
- fieldId 用步骤 4 硬编码映射；每条记录必须带日期字段（Step 4 动态确认的 fieldId，窗口当天）和优先级 `muPF9HZ`。
- create JSON 完整示例（含全部字段，日期字段 fieldId 以 `8pWqEMn` 为例）：

```json
[{"cells": {
  "8pWqEMn": "2026-08-18",
  "dVBW3We": "t98U5f2hiY",
  "KLP99tv": "任务摘要文本",
  "6hJ2h9A": "详细内容文本",
  "TG65buT": [{"userId": "0420601885", "corpId": "dingd8e1123006514592"}],
  "lGQjiHY": "颜虎",
  "XY9hgbt": "tQ0z3nRqRV",
  "cO9UArX": [{"openConversationId": "cid8nu4hzpAYUI55qoSb1VmIw=="}],
  "dKh2alZ": "2026-08-18 16:25:02",
  "x0RJRgv": "最新进展文本",
  "BDwWcfK": "dT0kSp265M",
  "KUp3qYU": "3",
  "X86pbLC": ["fileToken1", "fileToken2"],
  "muPF9HZ": "uo2m63vEUU"
}}]
```

- record create 返回后立即：
  1. 对所有含群聊的记录逐条 record update 补写 cO9UArX（group 字段 create 时写入可能丢失）
  2. 然后回读验证：

```bash
dws aitable record query --base-id <BASE_ID> --table-id <TABLE_ID> \
  --record-ids <IDS_CSV> --field-ids <ALL_FIELD_IDS_CSV> --format json
```

验证：user 字段带出 userId+corpId、group 字段带 openConversationId、attachment 数组文件名与本地一致、状态/来源单选选项正确。

### Step 8：生成日报摘要 + P0 停滞识别 + 推送

**8.1 生成日报摘要**

回复格式（严格按此结构）：

```
最近 24 小时任务概览（WINDOW_START ~ WINDOW_END）：
- 总计：X 条
- 已完成/已闭环：A 条
- 处理中：B 条
- 待处理/待答复（未回复）：C 条
- 待办 & DING：有 D 条 / 24h 内无新增

明细表：https://alidocs.dingtalk.com/i/nodes/7NkDwLng8Za7QYkeHaynxmLbJKMEvZBY?entrance=data&sheetId=dqUs6bi
仪表盘：https://alidocs.dingtalk.com/i/nodes/7NkDwLng8Za7QYkeHaynxmLbJKMEvZBY?entrance=data&applicationId=dashboard-e8e0b16c-8e02-46df-914d-d17ffbafb3ad

| # | 任务/问题摘要 | 对方 | 方向 | 状态 |
| ... 每条一行 ... |
```

**8.2 P0 停滞识别（关键能力，每次都要做）**

无论用户是否要求，都要跑一次 P0 停滞扫描，把命中项在日报之后单独用醒目段落列出。

扫描范围：全表所有状态属于 待处理/待答复/处理中 的记录（含两个方向）。

P0 判定规则（满足任一即视为 P0/停滞）：
- 记录里最新时间距今天大于等于 2 个自然日仍未闭环。
- 记录摘要/详细内容含关键词：P0、高优、阻塞、卡住、老板、Boss、领导、发版、上线、客户、线上、故障、预发白名单、审批、不能用、不可用、供应商跑路。
- 方向=我派发给别人 且状态=待答复 且对方大于等于 2 个自然日未回复。
- 方向=别人派发给我 且状态=待答复 且当前用户大于等于 1 个工作日未回复对方（对老板/直属上级/客户尤其严格）。
- 用户在日报窗口内明确说过「催」「拉一下」「跟一下」「快点」「今天要」的对象。

**上下文验证（强制）**：DING/@消息只是触发信号，判断状态前必须查同一对话同一话题的后续消息。如果后续消息显示对方已自行解决（如"我知道了""不用问了""已解决"等闭环信号），或我已回复且对方确认收到，则标记为已闭环，不能标 P0/待答复。

对每个 P0 记录必须计算：
- stalledDays：today - 最新时间的自然日数。
- stalledLabel：已停滞 N 天 或 已 N 小时无进展（不足 24h 时按小时算）。
- owner：需要被催办的那个人。方向=我派发给别人时 owner=对方；方向=别人派发给我时 owner=当前用户自己。
- recommendedChannel：默认单聊；如果对方 24h 内在单聊有回复但没结论，用待办形式加时限；如果之前多次单聊已读不回，用待办+抄送对方直属的组合建议。

P0 段落输出格式：

```
P0 停滞任务（共 N 条）——建议今天就催：

| # | 任务摘要 | 责任方 | 状态 | 已停滞 | 建议渠道 |
| 1 | 摘要 | 对方花名 | 状态 | 已停滞 3 天 | 单聊 |
| 2 | 摘要 | 对方花名 | 状态 | 已 18 小时 | 待办(24h内) |

其中 M 条我派发给别人的可以一键催办；K 条别人派我的需要你亲自回。
```

只要 P0 列表里有「我派发给别人」方向的记录，就必须继续走 8.3。

**8.3 询问是否开定时任务（AskUserQuestion）**

先查当前是否已有定时任务（qwenwork_cron_manage_job action=list）。如已有则跳过此步，直接走 8.4。

如没有，弹一个 AskUserQuestion 询问是否每天下午 6 点自动跟进。选项：
- 开，每工作日 18:00 自动跑 → 建 cron job（cron 表达式 `0 18 * * 1-5`）。
- 不开，我自己跑 → 继续走 8.4。

**8.4 提供一键催办入口（AskUserQuestion）**

无人值守模式（定时任务/cron 触发、或用户不在场）：不弹 8.4，按先不催只汇总处理；P0 清单随推送内容发出。

交互模式下弹 AskUserQuestion，选项：
- 一键催办所有 P0（单聊私信）
- 一键催办所有 P0（创建带截止时间的待办）
- 先只催其中一部分（我来挑）
- 先不催，只汇总

用户选择"我来挑"时，再弹一次 AskUserQuestion（multiSelect=true），把每条 P0 摘要作为选项让用户勾选。

**8.5 钉钉自推送日报（每次执行都必须做）**

无论交互模式还是无人值守模式，步骤 8.4 结束后必须用 `dws chat message send --user <MY_USER_ID>` 给自己发完整日报消息。**合并为 1 条完整消息发送**，使用 Markdown 表格让钉钉渲染成卡片样式。

格式要求：
- 概览、别人派发给我、我派发给别人、P0 停滞各用独立 Markdown 表格，用 `---` 分隔。
- 用 --title 设标题（如"📊 24h任务日报（MM-DD HH:MM ~ MM-DD HH:MM）"），--text 传完整内容。
- 任务明细按方向分组，每组内按状态排序（处理中→待处理→待答复→已闭环）。
- P0 停滞段只在有命中项时才包含。
- 末尾附上明细表链接。

完整消息模板：

```
**统计概览**

| 总计 | 已闭环 | 处理中 | 待处理/待答复 | 待办&DING |
| --- | --- | --- | --- | --- |
| X | A | B | C | 无新增/D条 |

---

**🔻 别人派发给我（N条）**

| # | 任务摘要 | 对方 | 状态 | 最新时间 |
| --- | --- | --- | --- | --- |
| 1 | 摘要 | 花名 | 状态 | MM-DD HH:MM |

---

**🔺 我派发给别人（N条）**

| # | 任务摘要 | 对方 | 状态 | 最新时间 |
| --- | --- | --- | --- | --- |
| 1 | 摘要 | 花名 | 状态 | MM-DD HH:MM |

---

✅ 当前窗口内无P0停滞任务

📋 [明细表](BASE_URL?entrance=data&sheetId=dqUs6bi)
```

如有 P0 停滞任务，替换最后的"✅ 当前窗口内无P0停滞任务"为：

```
---

**⚠️ P0 停滞任务详情（共 N 条）**

| 任务摘要 | 责任方 | 状态 | 已停滞 | 命中原因 |
| --- | --- | --- | --- | --- |
| 摘要 | 对方/我方 | 状态 | N天 | 判定依据 |

催办已执行：催办方式简述

📋 [明细表](BASE_URL?entrance=data&sheetId=dqUs6bi)
```

## 输出格式

执行完成后，输出一句话摘要 + 写入记录数 + 用到的能力名（DWS），便于用户复盘。例如：

> 已汇总 24h 内 12 条任务（新增 5 / 更新 7），写入「钉钉任务日报明细」，日报已推送至钉钉单聊。依赖：DWS CLI。

## 性能优化（关键，能省 50% 执行时间）

核心原则：减少串行 bash 调用次数，能并行的并行，能合并的合并。

1. **批量更新合并**：所有 record update 操作合并到 1 个 JSON 文件，1 次调用完成。示例：

```python
records = [
  {"recordId": "rec1", "cells": {"BDwWcfK": "60awy4EzOK", "x0RJRgv": "已闭环"}},
  {"recordId": "rec2", "cells": {"BDwWcfK": "dT0kSp265M", "x0RJRgv": "跟进中"}},
]
json.dump(records, open('/tmp/updates.json', 'w'), ensure_ascii=False)
```

```bash
dws aitable record update --base-id <BASE_ID> --table-id <TABLE_ID> --records-file /tmp/updates.json
```

2. **批量创建合并**：所有 record create 操作合并到 1 个 JSON 文件，1 次调用完成。
3. **联系人搜索优化**：优先从消息的 senderOpenDingTalkId 匹配已有联系人，减少 contact user search 调用次数。
4. **群聊拉取优化**：只拉取 mentions 涉及的群 + 表中有未闭环记录的群，不要拉取所有群的全量历史。
5. **日期字段一次写对**：create 时直接用 Step 4 动态确认的日期字段 ID，避免后续补写。
6. **并行阶段最大化**：5 路数据采集、联系人搜索、单聊上下文补拉都应并行执行。

## 常见错误与恢复

| 错误现象 | 原因 | 恢复方法 |
|---|---|---|
| peerUid is required | --user 传了 openDingTalkId 而非数字 userId | 用 dws contact user search 取数字 userId 后重试 |
| shell 变量吞掉 mediaId | $iwEc... 未加单引号 | 所有 mediaId 统一单引号包裹 |
| record create JSON 解析失败 | 受管 shell 展开了花括号或@ | 改用 --records-file + python3 写文件 |
| upload PUT 403/超时 | uploadUrl 已过 60s 有效期 | 重新 apply upload，不要复用旧 URL |
| group 字段回读为空 | create 时 group 写入丢失 | 逐条 record update 补写 cO9UArX |
| FORBIDDEN / PERMISSION_DENIED | Base 权限不足 | 立即停止，不切换到其他 Base，提示用户检查权限 |
| hasMore 恒 true | 单次上限 93-100 条 | 分时间窗查询 + openMessageId 去重 |
| Base 丢失 | 误删或权限变更 | dws aitable base create --name "钉钉任务日报" --template-id 1826 重建，补建聚合表 SzlmKuE，重建后 table get 确认日期字段 fieldId |
| 误创建新表 | 误用 table create | 只用固定表 dqUs6bi，不建新表 |
| 记录附件字段为空 | 消息含 mediaId 但跳过了 Step 6（附件下载→上传→fileToken） | 回头执行 Step 6：对每个 mediaId 走 download → upload → PUT(200) → fileToken，再 record update 补写 X86pbLC |
| UNKNOWN_KEY | qw_query/qw_action 的连接器 key 写错 | 正确形态是 qwenwork.settings.connector.builtin.dws |
| INVALID_INPUT on install | 连接器操作动作混用 | builtin 类连接器用 qw_action enable/connect，不走 market 安装流程 |
| 认证超时 | OAuth 授权被中断或本地回调被拦截 | 提示用户手动完成钉钉授权，不要死等；回 Step 0 重新 connect |
| dws 命令返回 401/token 失效 | 钉钉授权过期 | 回 Step 0 走 qw_action connect 重新认证，不要在失效会话上重试 |

## 降级路径

当 DWS CLI 不可用或钉钉服务异常时：
- 不虚构数据，不尝试用其他工具替代拉取钉钉消息。
- 明确告知用户"DWS 不可用，无法自动拉取钉钉消息"。
- 提供替代方案：请用户手动粘贴需要汇总的消息内容，技能仍可完成归类、写入表格和生成日报的后续流程。

## 验证清单

- [ ] **附件清单已构建（Step 3）**：扫描所有保留消息的 content 字段，提取全部 mediaId，输出"检测到 N 张图片附件"。清单非空则 Step 6 必须执行。
- [ ] **附件已完整处理（Step 6）**：清单中每个 mediaId 已 download → upload → PUT(HTTP 200) → fileToken 收集。create 前已输出"附件清单 N 张，已处理 N 张，fileToken N 个，可以 create"。
- [ ] **附件字段已写入（Step 7）**：每条含图片的记录 `X86pbLC` 字段已填入 fileToken 数组，回读文件名/大小与本地一致。
- [ ] 5 个来源（群里@我 / 我发出的单聊任务 / 别人发我的单聊任务 / DING / 待办）都拉取过。
- [ ] 同一问题跨轮合并为 1 条。
- [ ] 每条记录的 user 字段带 corpId、group 字段带 openConversationId（create 后需逐条 update 补写 group）。
- [ ] 日报按"总计/已完成/处理中/未回复"输出。
- [ ] 明细表链接 + 仪表盘链接都在日报里、可点击。
- [ ] 每条新记录写了日期字段 WCk1Ut1 和优先级字段 muPF9HZ；跨天未闭环问题用 record update 更新原行而非新建。
- [ ] 已检查定时任务状态（已有则跳过，无则询问用户）。
- [ ] P0 扫描已检查完整上下文（DING/@只是触发信号，需看后续消息确认是否闭环）。
- [ ] 已用 dws chat message send --user MY_USER_ID 给自己推送完整日报，消息分 4~5 条发送，每条使用 Markdown 表格渲染卡片样式。
