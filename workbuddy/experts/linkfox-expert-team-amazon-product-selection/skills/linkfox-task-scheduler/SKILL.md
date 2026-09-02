---
name: linkfox-task-scheduler
description: 管理 LinkFoxAgent 的定时任务（周期性自动执行的提示词任务）。一个 skill 覆盖六个操作——新增定时任务、更新定时任务、更新任务启用/停用状态、删除定时任务、查询定时任务列表、立即创建 N 分钟/小时后的一次性提醒。用户提到"创建/新增一个定时任务"、"让 Agent 每天/每周/每月定时帮我跑"、"修改我的定时任务"、"启用/停用/暂停某个定时任务"、"删除定时任务"、"看看我有哪些定时任务/任务列表"、"定时提醒/定时汇总/周期性任务"、"N分钟/N小时后提醒我"、"X分钟后发飞书/钉钉提醒"、"schedule a task"、"remind me in X minutes"、"recurring/cron task"、"create/update/delete/list scheduled task"时触发。任务支持每天/每周/每月/不重复四种调度方式，并可配置邮件、钉钉、飞书、自定义 WebHook 通知。
---

# LinkFox 定时任务管理

管理 LinkFoxAgent 的**定时任务**：把一段提示词内容（任务内容）按设定的周期自动交给 Agent 执行，并可在完成后通过邮件 / 钉钉 / 飞书 / 自定义 WebHook 通知用户。

本 skill 用**一个脚本 + action 参数**统一覆盖五个操作：

| action | 含义 | 后端端点 |
|---|---|---|
| `create` | 新增定时任务 | `POST /task/add4api` |
| `update` | 更新定时任务（全量字段） | `POST /task/update4api` |
| `update-status` | 仅切换启用/停用状态 | `POST /task/updateStatus4api` |
| `delete` | 删除定时任务（支持批量） | `POST /task/delete4api` |
| `list` | 分页查询定时任务列表 | `POST /task/list4api` |
| `remind` | 快速创建 N 分钟/小时后的一次性提醒（客户端自动算目标时刻，转为 `create`） | 内部转 `POST /task/add4api` |

## 核心概念

- **任务内容（`promptContent`）**：定时触发时交给 Agent 执行的提示词，最长 60000 字符。
- **调度（`execType` + `execPoint` + `execTime`）**：决定何时执行。
  - `execType`：`1`=每天、`2`=每周、`3`=每月、`4`=不重复（一次性）。（`5`=每分钟，当前环境通常未开放，使用前确认。）
  - `execTime`：执行时刻，`HH:mm`，如 `"09:00"`。
  - `execPoint`：周期点，含义随 `execType` 变化（见下方「调度规则」）。
- **状态（`taskStatus`）**：布尔。`true`=启用（按周期执行），`false`=停用。
- **通知（`noticeList`）**：**非必填，默认 `[]`**，配置任务执行结果的推送渠道（邮件 / 钉钉 / 飞书 / 自定义 WebHook）。不传或传空数组均表示不配置通知。

> **重要：不要传 `memberId`。** 该字段由后端从鉴权 token 自动注入，调用方传了也会被覆盖。

完整参数表（类型、必填、默认值、枚举、正则约束）、响应字段结构与错误码，见 [`references/api.md`](references/api.md)。

## 提醒模式（remind）

当用户说"N 分钟/小时后提醒我做某事"时，直接使用 `remind` action，**脚本在客户端自动计算目标时刻**，无需手动算时间。

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `delayMinutes` | number | 条件必填 | 延迟分钟数（与 `delayHours` 可叠加） |
| `delayHours` | number | 条件必填 | 延迟小时数（与 `delayMinutes` 可叠加） |
| `message` | string | 是 | 提醒内容，作为 Agent 在目标时刻执行的提示词；**建议直接写提醒原文**，如 `"请立即发送提醒：该去尿尿了！"` |
| `title` | string | 否 | 任务标题，默认 `"定时提醒"` |
| `feishuWebhook` | string | 条件必填 | 飞书机器人 Webhook 地址，Agent 执行后结果将推送到此；`feishuWebhook` 与 `webhookUrl` 二者至少传一个（`noticeList` 为必填，remind 通过该字段构造） |
| `webhookUrl` | string | 条件必填 | `feishuWebhook` 的别名；二者至少传一个 |

> - `delayMinutes` 与 `delayHours` 至少传一个且总和 > 0。
> - 目标时刻精度为分钟（`HH:mm`），实际触发可能晚 ≤1 分钟。
> - 若延迟后跨过午夜，`execPoint` 自动变为次日日期。
> - 飞书 Webhook 地址格式：`https://open.feishu.cn/open-apis/bot/v2/hook/<UUID>`。
> - `remind` 在客户端转换为 `execType=4`（不重复）的 `create` 调用，创建成功后回显任务 id 与计划执行时刻。

**构造 `message` 的指引**：提醒类任务的 `message` 建议以"请立即输出以下提醒内容，不要添加额外分析："开头，后接提醒正文。这样 Agent 在执行时会直接输出提醒，推送到 Feishu 的内容才是干净的提醒消息。

## 调度规则（execType ↔ execPoint ↔ execTime）

| execType | 含义 | execPoint | execTime | 说明 |
|---|---|---|---|---|
| `1` | 每天 | 不使用（留空） | `HH:mm` | 每天在 execTime 执行，例：每天 `09:00` |
| `2` | 每周 | 星期，逗号分隔，`1`=周一…`7`=周日，例 `"1,3,5"` | `HH:mm` | 每周指定几天的 execTime 执行 |
| `3` | 每月 | 日期，逗号分隔，例 `"1,15"` | `HH:mm` | 每月指定几号的 execTime 执行 |
| `4` | 不重复 | 具体日期 `YYYY-MM-DD`，例 `"2026-06-01"` | `HH:mm` | 一次性执行；`execPoint+execTime` 必须晚于当前时间，否则报错 |

## 调用方式

- **Python 脚本**：`python scripts/task_scheduler.py <action> '<JSON 参数>' [--inline]`
  - `<action>` ∈ `create | update | update-status | delete | list`
  - `<JSON 参数>` 为该操作的请求体（不含 `memberId`）

**输出策略（脚本默认行为）**：
- **始终**将完整响应写入 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/linkfox-task-scheduler-<timestamp>.json`（`<session>` 取自环境变量 `SESSION_ID`；**禁止写入 /tmp**，当前目录不可写则报错）
- 响应体 ≤ 8 KB：落盘后把完整 JSON 打印到 stdout
- 响应体 > 8 KB：落盘后 stdout 只输出摘要（顶层字段、常见计数如 `total`/`costToken`、最大列表字段的长度 + 前 3 条样本）
- 加 `--inline` 强制全量打印到 stdout（同样落盘）
- `delete` 接口后端无返回体，脚本会输出操作成功提示

## 使用指引

1. **识别意图**：从用户输入判断属于五个 action 中的哪一个（新增 / 改内容 / 仅改开关 / 删除 / 查列表）。
2. **构造调度**：把"每天/每周/每月/某天一次"翻译成 `execType` + `execPoint` + `execTime`，校验 `4`（不重复）的时间必须在未来。
3. **`update` 是全量更新**：会用传入的字段整体覆盖原任务（包括 `noticeList`），所以更新前应先用 `list` 拿到现有任务的完整字段，改动后再整体提交，避免丢字段。
4. **只改开关用 `update-status`**：启用/停用单个任务时优先用它，比 `update` 更轻量。注意状态必须真的发生变化（重复设同一状态后端会报错）。
5. **通知地址校验**：`noticeList` 为非必填，默认 `[]`（不通知）。若用户有配置通知渠道，钉钉/飞书 WebHook 有固定格式（见 `references/api.md`），构造前先核对，否则后端会拒绝。
6. **删除是批量**：`delete` 的 `ids` 是数组，单个删除也要包成 `["id1"]`。

### 示例

**1. 新增——每天 09:00 跑一个汇总任务，钉钉通知**
```json
{
  "title": "每日销售汇总",
  "promptContent": "汇总昨天的亚马逊美国站销售数据，输出 Top 10 商品",
  "taskStatus": true,
  "execType": 1,
  "execTime": "09:00",
  "noticeList": [
    {"noticeType": 2, "address": "https://oapi.dingtalk.com/robot/send?access_token=abc123def", "sign": ""}
  ]
}
```
`python scripts/task_scheduler.py create '<上面的 JSON>'`

**2. 新增——每周一三五 10:30 执行，飞书通知**
```json
{"title": "周报提醒", "promptContent": "生成本周竞品动态简报", "taskStatus": true, "execType": 2, "execPoint": "1,3,5", "execTime": "10:30", "noticeList": [{"noticeType": 3, "address": "https://open.feishu.cn/open-apis/bot/v2/hook/<YOUR_HOOK>", "sign": ""}]}
```

**3. 新增——2026-06-01 08:00 执行一次（不重复），钉钉通知**
```json
{"title": "618 预热分析", "promptContent": "分析 618 大促前的类目趋势", "taskStatus": true, "execType": 4, "execPoint": "2026-06-01", "execTime": "08:00", "noticeList": [{"noticeType": 2, "address": "https://oapi.dingtalk.com/robot/send?access_token=<YOUR_TOKEN>", "sign": ""}]}
```

**4. 更新——把某任务改为每月 1 号执行（全量字段，先 list 再改）**
```json
{"id": "task-12345", "title": "月度复盘", "promptContent": "生成上月经营复盘报告", "taskStatus": true, "execType": 3, "execPoint": "1", "execTime": "09:00", "noticeList": [{"noticeType": 3, "address": "https://open.feishu.cn/open-apis/bot/v2/hook/<YOUR_HOOK>", "sign": ""}]}
```
`python scripts/task_scheduler.py update '<上面的 JSON>'`

**5. 停用 / 启用某个任务**
```json
{"id": "task-12345", "taskStatus": false}
```
`python scripts/task_scheduler.py update-status '<上面的 JSON>'`

**6. 批量删除**
```json
{"ids": ["task-12345", "task-67890"]}
```
`python scripts/task_scheduler.py delete '<上面的 JSON>'`

**7. remind——5 分钟后飞书提醒去尿尿**
```json
{
  "delayMinutes": 5,
  "message": "请立即输出以下提醒内容，不要添加额外分析：\n⏰ 提醒时间到！该去尿尿了！",
  "title": "尿尿提醒",
  "feishuWebhook": "https://open.feishu.cn/open-apis/bot/v2/hook/d07890cf-5b29-4461-b8c5-9227ccd2fe5d"
}
```
`python scripts/task_scheduler.py remind '<上面的 JSON>'`

> 脚本自动计算"当前时刻 + 5 分钟"作为执行时间，无需手动填写 execPoint / execTime。

**8. 查询列表——筛选「生效中」+ 关键词 + 分页**
```json
{"taskStatus": 1, "keyword": "汇总", "page": 1, "pageSize": 20}
```
`python scripts/task_scheduler.py list '<上面的 JSON>'`

> 注意：`list` 入参的 `taskStatus` 是**整数**筛选值（`1`=生效中、`2`=已停用、`3`=已完结、不传=全部），与 `create/update` 里布尔型的 `taskStatus` 含义不同。

### 组合示例：用户没给 id 时，先 list 找到 id 再切换状态

`update-status` 必须传任务 `id`。但用户通常说的是"把**每日销售汇总**那个任务停掉"，并不知道 id。这时先 `list` 按关键词查出来，从结果里取 `id`，再调 `update-status`。

**第 1 步——按标题关键词查（只查生效中的）**
```json
{"taskStatus": 1, "keyword": "每日销售汇总", "page": 1, "pageSize": 20}
```
`python scripts/task_scheduler.py list '<上面的 JSON>'`

从返回的 `items` 中定位目标任务，拿到它的 `id`（例如 `"task-12345"`）：
- 命中**唯一**一条 → 直接用它的 id。
- 命中**多条** → 把候选（id、标题、当前状态、调度）列给用户确认是哪一个，不要擅自批量操作。
- **没命中** → 可能已停用，去掉 `taskStatus` 重查全部，或提示用户核对名称。

**第 2 步——用上一步拿到的 id 停用它**
```json
{"id": "task-12345", "taskStatus": false}
```
`python scripts/task_scheduler.py update-status '<上面的 JSON>'`

> 提示：第 2 步的 `taskStatus` 必须与当前状态不同（重复设同一状态后端会报"状态没有更新"）。第 1 步用 `taskStatus:1` 过滤"生效中"，能保证查回来的任务确实可被停用；反向（停用→启用）则用 `taskStatus:2` 过滤"已停用"。启用（false→true）时后端还会校验执行时间未过期。

## 展示规则

1. `list` 结果用表格展示：标题、任务内容摘要、状态（生效中/已停用/已完结）、调度（翻译成"每天 09:00"这类人话）、通知渠道、创建时间。
2. 时间戳字段（`createTime`/`lastUpdateTime`，单位 ms）转成可读日期。
3. `create`/`update`/`update-status` 成功后，回显任务 id、标题、新的调度与状态，让用户确认。
4. `delete` 成功后明确告知已删除的任务数量。

## 限制

- `promptContent` 最长 60000 字符。
- `execType=4`（不重复）的执行时间必须晚于当前时间。
- 通知地址（钉钉/飞书）必须符合固定格式，否则被拒。
- 不要传 `memberId`（后端按 token 注入）。
- `agentVersion` 默认 `2`，且更新时不可切换（只能在创建时决定）。

## 适用与不适用

**适用**：
- 让 Agent 周期性 / 定时自动执行某段提示词任务
- 管理（增删改查）用户已有的定时任务及其调度、通知

**不适用**：
- 立即执行一次性任务、即时问答 → 直接用对应数据/分析工具或主 Agent，不要建定时任务
- 查询任务的**执行记录/运行结果**（runStatus、失败原因等）→ 本 skill 不覆盖该接口

## 反馈

参见 `references/api.md` 中的 Feedback API。满足不符、不满、赞扬或改进点时自动上报。
