# LinkFox 定时任务管理 API 参考

本页为 `linkfox-task-scheduler` 技能调用的底层接口规格。SKILL.md 面向"怎么用"的决策层，本文档面向"接口精确格式"。

## 调用规范（五个接口通用）

- **请求地址前缀**：`{BASE_URL}`，默认 `https://tool-gateway.linkfox.com`，可用环境变量 `LINKFOX_TOOL_GATEWAY` 覆盖（如测试环境 `https://test-sz-tool-gateway.linkfox.com`）。
- **请求方式**：POST，Content-Type: application/json
- **认证方式**：Header `Authorization: <api_key>`，api_key 从环境变量 `LINKFOX_AGENT_API_KEY` 读取。未配置时提示用户前往 https://skill.linkfox.com/linkfoxskills/guide.htm 申请。
- **`memberId` 由后端从 token 注入**，调用方不要传该字段（传了会被覆盖）。

| 操作 | 端点 | 入参 | 返回 |
|---|---|---|---|
| 新增 | `POST /task/add4api` | AddTask | TaskVo |
| 更新 | `POST /task/update4api` | UpdateTask | TaskVo |
| 更新状态 | `POST /task/updateStatus4api` | UpdateTaskStatus | TaskVo |
| 删除 | `POST /task/delete4api` | DeleteTask | 无（void） |
| 列表 | `POST /task/list4api` | TaskList | PageVo\<TaskListVo\> |

---

## 1. 新增定时任务 `POST /task/add4api`

### 请求参数（AddTask）

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|----|------|------|
| title | string | 是  |  | 任务标题 |
| promptContent | string | 是  |  | 任务内容（提示词），最长 60000 字符 |
| taskStatus | boolean | 是  |  | 状态：`true`=启用，`false`=停用 |
| execType | integer | 是  |  | 执行类型：`1`=每天 / `2`=每周 / `3`=每月 / `4`=不重复（`5`=每分钟，当前环境通常未开放） |
| execPoint | string | 否  |  | 周期点，含义随 execType 变化（见「调度规则」表） |
| execTime | string | 否  |  | 执行时刻，格式 `HH:mm`，如 `"09:00"`（execType=1/2/3/4 需要） |
| noticeList | array[Notice] | 否  | `[]` | 通知渠道列表，见下方 Notice 结构；不传或传空数组表示不配置通知 |
| taskTagId | string | 否  |  | 任务标签 id |
| agentVersion | integer | 否  | 2 | Agent 版本，默认 `2` |
| subAgent | string | 否  |  | agentVersion=2（默认）时生效；子 Agent 路由 code；null 或 `"super"` 表示超级 Agent 智能路由 |

### 调度规则（execType ↔ execPoint ↔ execTime）

| execType | 含义 | execPoint | execTime | 约束 |
|---|---|---|---|---|
| 1 | 每天 | 留空 | `HH:mm` | — |
| 2 | 每周 | 星期 `1`=周一…`7`=周日，逗号分隔，例 `"1,3,5"` | `HH:mm` | — |
| 3 | 每月 | 日期，逗号分隔，例 `"1,15"` | `HH:mm` | — |
| 4 | 不重复 | 具体日期 `YYYY-MM-DD`，例 `"2026-06-01"` | `HH:mm` | `execPoint+execTime` 必须晚于当前时间 |

### Notice 结构（noticeList 数组元素）

| 字段 | 类型 | 必填 | 说明 | 取值/格式 |
|------|------|------|------|----------|
| noticeType | integer | 是 | 通知类型 | `1`=邮件，`2`=钉钉，`3`=飞书，`4`=自定义 WebHook |
| address | string | 是 | 通知地址 | 邮箱地址或 WebHook URL（见下方正则） |
| sign | string | 否 | 加签密钥 | 钉钉/飞书的加签 secret（如启用加签） |

**地址格式校验**：
- 钉钉（noticeType=2）：`^https://oapi\.dingtalk\.com/robot/send\?access_token=[a-fA-F0-9]+(&keyword=[^&]*)?$`
- 飞书（noticeType=3）：`^https://open\.feishu\.cn/open-apis/bot/v2/hook/[a-fA-F0-9-]+$`
- 邮件（noticeType=1）：填收件邮箱地址
- 自定义 WebHook（noticeType=4）：填可 POST 的 URL

### 响应（TaskVo）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 任务 id |
| title | string | 标题 |
| promptContent | string | 任务内容 |
| taskStatus | boolean | 状态：true=启用，false=停用 |
| stopType | integer | 关闭类型：`1`=停用，`2`=完结（taskStatus=false 时有意义） |
| execType | integer | 执行类型 |
| execPoint | string | 周期点 |
| execTime | string | 执行时刻 |
| taskTagId | string | 任务标签 id |
| model | string | 模型名称 |
| createUser | string | 创建人（memberId） |
| updateUser | string | 修改人 |
| lastUpdateDate | string | 最后更新时间（日期对象序列化） |
| lastUpdateTime | integer | 最后更新时间戳（ms） |
| agentVersion | integer | Agent 版本：1=V1，2=V2 |
| subAgent | string | V2 子 Agent 路由 code，null 表示超级 Agent 智能路由 |

---

## 2. 更新定时任务 `POST /task/update4api`

**全量更新**：传入字段整体覆盖原任务（含 noticeList）。更新前建议先 `list` 取回完整字段再改。

### 请求参数（UpdateTask）

在「新增」全部字段基础上，**额外必填 `id`**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 任务 id |
| title | string | 是 | 标题 |
| promptContent | string | 是 | 任务内容，最长 60000 |
| taskStatus | boolean | 是 | true=启用，false=停用 |
| execType | integer | 是 | 执行类型（同新增） |
| execPoint | string | 否 | 周期点（同新增） |
| execTime | string | 否 | 执行时刻 `HH:mm` |
| noticeList | array[Notice] | 否 | 完全替换原通知列表；不传或传空数组表示清空通知配置，默认 `[]` |
| taskTagId | string | 否 | 任务标签 id |
| subAgent | string | 否 | 仅 V2 任务可调整；V1 不支持 |

> `agentVersion` 不允许通过 update 切换（只能创建时决定）。若 `taskStatus` 从 false 改为 true（重新启用），后端会校验执行时间未过期。

### 响应

同「新增」的 TaskVo。

---

## 3. 更新任务状态 `POST /task/updateStatus4api`

仅切换启用/停用，比 update 轻量。

### 请求参数（UpdateTaskStatus）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 任务 id |
| taskStatus | boolean | 是 | true=启用，false=停用 |

> 状态必须真的变化（重复设同一状态会报"状态没有更新"）。从 false→true（启用）时校验执行时间未过期。

### 响应

同「新增」的 TaskVo。

---

## 4. 删除定时任务 `POST /task/delete4api`

### 请求参数（DeleteTask）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | array[string] | 是 | 任务 id 列表（单个删除也用数组：`["task-1"]`） |

### 响应

后端返回类型为 void，无业务响应体。删除同时清理任务关联的通知配置。所有 id 需存在且属于当前用户。

---

## 5. 定时任务列表 `POST /task/list4api`

### 请求参数（TaskList）

| 参数 | 类型 | 必填 | 默认 | 说明                                                         |
|------|------|------|----|------------------------------------------------------------|
| page | integer | 是 | 1  | 页码，从 `1` 开始，范围 `[1, 1000]`；传 `0` 或超出范围后端返回 400          |
| pageSize | integer | 是 | 10 | 每页数量                                                       |
| taskStatus | integer | 否 | 1  | 状态筛选：`1`=生效中，`2`=已停用，`3`=已完结（不传=全部）。**注意是整数，与新增/更新里的布尔不同** |
| keyword | string | 否 |    | 关键字，模糊匹配 title 与 promptContent                             |
| id | string | 否 |    | 精确查询指定任务 id                                                |
| taskTagId | string | 否 |    | 标签筛选；`"default"`=未分类，不传=全部                                 |
| agentVersion | integer | 否 |    | 版本筛选：`1`=V1，`2`=V2，不传=全部                                   |

**状态映射**（整数 → 底层）：`1` 生效中 = taskStatus(true)；`2` 已停用 = taskStatus(false)+stopType(1)；`3` 已完结 = taskStatus(false)+stopType(2)。结果按创建时间倒序。

### 响应（PageVo\<TaskListVo\>）

| 字段 | 类型 | 说明 |
|------|------|------|
| items | array[TaskListVo] | 任务列表 |
| total | integer | 总记录数 |
| pageNum | integer | 当前页码 |
| pageSize | integer | 每页数量 |
| pages | integer | 总页数 |

**TaskListVo 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 任务 id |
| title | string | 标题 |
| promptContent | string | 任务内容 |
| taskStatus | boolean | true=启用，false=停用 |
| stopType | integer | 关闭类型：1=停用，2=完结 |
| execType | integer | 执行类型：1每天/2每周/3每月/4不重复 |
| execPoint | string | 周期点 |
| execTime | string | 执行时刻 |
| taskNoticeArray | array | 通知列表（JSON 数组，结构同 Notice） |
| taskTagId | string | 任务标签 id |
| model | string | 模型 |
| uid | string | 创建人 uid |
| createUser | string | 创建人 |
| updateUser | string | 修改人 |
| createDate | string | 创建时间（日期对象序列化） |
| createTime | integer | 创建时间戳（ms） |
| lastUpdateDate | string | 最后更新时间 |
| lastUpdateTime | integer | 最后更新时间戳（ms） |
| agentVersion | integer | Agent 版本 |
| subAgent | string | V2 子 Agent 路由 code |

---

## 错误处理

HTTP 200 时业务成功与否看响应体 `errcode`/`errorCode`（200=成功）；鉴权失败返回 `errcode=401`。

| errcode | 含义 | 处理 |
|---------|------|------|
| 200 | 成功 | 正常解析业务字段 |
| 401 | 认证失败（用户中心鉴权失败） | 检查 `Authorization`（`LINKFOX_AGENT_API_KEY`）是否正确/未过期 |
| 其他 | 业务异常 | 参考 `errmsg`/`errorMsg` 字段 |

常见业务报错信息：任务不存在、当前环境不支持该执行类型、执行时间格式错误 / 预设执行时间已过期（execType=4）、钉钉/飞书 webhook 地址格式不正确、状态没有更新、通知地址不能为空。

错误响应示例：
```json
{"errcode": 401, "errmsg": "用户中心鉴权失败。"}
```

## curl 示例

```bash
# 新增（每天 09:00）
curl -X POST https://tool-gateway.linkfox.com/task/add4api \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"每日汇总","promptContent":"汇总昨日销售","taskStatus":true,"execType":1,"execTime":"09:00"}'

# 列表（生效中，第一页）
curl -X POST https://tool-gateway.linkfox.com/task/list4api \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"taskStatus":1,"page":1,"pageSize":20}'
```

---

## Feedback API

> 该端点与上方任务 API 分离，请勿混用 base URL。

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-task-scheduler",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "Task created successfully, user was satisfied."
}
```

**字段规则：**
- `skillName`：使用 SKILL.md frontmatter 的 `name`（`linkfox-task-scheduler`）
- `sentiment`：`POSITIVE`（赞扬）/ `NEUTRAL`（建议无情绪）/ `NEGATIVE`（不满或错误）
- `category`：`BUG`（异常或数据错误）/ `COMPLAINT`（不满）/ `SUGGESTION`（改进建议）/ `OTHER`
- `content`：说明用户说了什么/期望什么、实际发生了什么、为什么是问题/赞赏
