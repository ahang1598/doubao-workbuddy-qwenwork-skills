---
name: lark-project
description: |
  飞书项目（Meego/Meegle）操作工具。支持查询和管理工作项、节点流转、视图查询、个人待办、排期统计等功能。 Use when user needs to work with Feishu/Lark Meego project management — including querying work items, creating/updating work items, completing workflow nodes, checking views, listing todos, analyzing schedules/workloads, or searching with MQL. 关键词：飞书项目、meego、meegle、工作项、需求、任务、缺陷、排期、视图、待办、节点。
---

# 飞书项目 (Meego/Meegle) 操作指南

本技能通过 Meegle CLI 来操作飞书项目数据。输出语言跟随用户输入语言，默认中文。

> 各命令的调用示例见 [references/api-examples.md](references/api-examples.md)。
> **CLI 使用指南**（命令结构、参数传递、命令发现）：见 [references/cli-guide.md](references/cli-guide.md)

---

## Project 空间域

### project.search

搜索空间信息，将空间名转换为 project_key 或验证空间是否存在。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 projectKey、simpleName 或空间名称 |

---

## WorkItem 工作项域

### workitem.create

创建工作项实例。**务必先用 `workitem.meta-fields` 获取字段信息，`workitem.meta-roles` 获取角色信息。模板 ID 是必填项。**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_type | string | 是 | 工作项类型 |
| project_key | string | 否 | 空间标识 |
| fields | array | 否 | 字段值列表，每项含 field_key 和 field_value |
| url | string | 否 | 可从链接解析空间信息 |

### workitem.get

按 ID/名称查询工作项概况。不传 fields 时仅返回固定基础字段；如需自定义字段数据，先调 `workitem.meta-fields` 获取字段 key 后传入 fields。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID 或名称 |
| project_key | string | 否 | 空间 key |
| fields | array | 否 | 要查询的 field_key 或 field_name |
| url | string | 否 | 工作项实例链接，可自动解析 |

### workitem.update

修改指定实例的字段值或角色。节点字段更新请用 `workflow.update-node`。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID 或名称 |
| project_key | string | 否 | 空间 key |
| fields | array | 否 | 要更新的字段列表，每项含 field_key 和 field_value |
| role_operate | array | 否 | 角色操作，每项含 op(add/remove)、role_key、user_keys |
| url | string | 否 | 可从链接解析信息 |

**角色更新**：不能通过 fields 更新角色，必须用 `role_operate`。role_key 通过 `workitem.meta-roles` 获取，user_keys 通过 `user.search` 获取。

### workitem.query

使用 MQL 查询工作项数据。语法详见 [references/mql-syntax.md](references/mql-syntax.md)。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间标识（支持名称、simpleName、projectKey） |
| mql | string | 是（翻页时可用 session_id 替代） | MQL 查询语句（完整 SQL） |
| session_id | string | 否 | 分页会话 ID，传入后不解析 MQL 直接翻页 |
| group_pagination_list | array | 否 | 分页信息，首次查询可不传 |

**要点**：
- 务必先用 `workitem.meta-fields` 查询字段类型和结构，查不到直接报错不要继续
- 如涉及角色信息，用 `workitem.meta-roles` 获取角色结构
- SELECT 后属性不宜过多，**优先使用字段 key**（如 `name`、`priority`、`status`）而非字段名称（如 `任务名称`）
- 返回按页返回，需全量数据时必须使用翻页参数

### workitem.list-op-records

查看工作项操作记录。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_id | string | 是 | 工作项 ID |

### workitem.meta-types

获取指定空间下所有工作项类型列表。用户描述模糊时用此命令确认合法 type_key。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 projectKey |

### workitem.meta-fields

获取指定空间和工作项类型的可用字段配置（不含禁用字段和角色配置）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_type | string | 是 | 工作项类型 key 或名称 |
| page_num | number | 是 | 页数，每页 50 条，从 1 开始 |
| field_keys | array | 否 | 精确匹配字段 key 或名称 |
| field_query | string | 否 | 模糊查询字段 key 和名称 |
| field_types | array | 否 | 按字段类型筛选 |

### workitem.meta-roles

获取指定工作项类型的角色列表。用于查询/创建/更新工作项前确认合法 role_key。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_type | string | 是 | 工作项类型 key 或名称 |
| page_num | number | 是 | 页数，每页 50 条，从 1 开始 |
| role_keys | array | 否 | 精确匹配角色 key 或名称 |
| role_query | string | 否 | 模糊查询角色 key 和名称 |

### workitem.meta-create-fields

查看创建工作项时可用的字段及类型。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |

---

## WorkFlow 工作流域

### workflow.transition

仅用于节点流工作项，操作节点完成流转或回滚。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID |
| action | string | 否 | confirm（流转） / rollback（回滚） |
| node_id | string | 否 | 节点 ID |
| node_ids | array | 否 | 节点名称或节点 ID 列表 |
| rollback_reason | string | 否 | 回滚原因，action=rollback 时需填写 |
| project_key | string | 否 | 空间 key |

### workflow.transition-state

仅用于状态流工作项，流转工作项状态。先用 `workflow.list-state-transitions` 获取可流转状态及 transition_id。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID |
| transition_id | string | 否 | 状态流转 ID，从 `workflow.list-state-transitions` 获取 |
| project_key | string | 否 | 空间 key |

### workflow.get-node

获取工作项中指定节点或所有节点的完整详情。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID 或名称 |
| node_id_list | array | 否 | 节点 ID 列表，传空或 `_all` 获取所有节点 |
| field_key_list | array | 否 | 节点字段 key，传空或 `_all` 获取所有字段 |
| need_sub_task | boolean | 否 | 是否需要节点子项（子任务） |
| page_num | number | 否 | 节点信息一次最多 20 个，按页返回 |
| project_key | string | 否 | 空间 key |
| url | string | 否 | 链接，可自动解析 |

### workflow.update-node

修改节点（排期、负责人、自定义字段等）。排期/差异化排期/负责人不要同时修改。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID |
| node_id | string | 是 | 节点 ID |

### workflow.list-state-transitions

查看工作项可流转的状态列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_id | string | 是 | 工作项 ID |
| work_item_type | string | 是 | 工作项类型 |
| user_key | string | 是 | 用户标识 |

### workflow.list-state-required

查看流转所需的必填信息。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_id | string | 是 | 工作项 ID |
| state_key | string | 是 | 目标状态 key |

### workflow.meta-node-fields

查看节点字段配置。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_type | string | 是 | 工作项类型 |

---

## MyWork 工作台域

### mywork.todo

按 action 类型查询当前用户的工作项列表。无需 MQL 即可查询待办/已办。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | todo(待办)/done(已办)/overdue(逾期)/this_week(本周待办) |
| page_num | number | 是 | 页码，从 1 开始，每页 50 条 |
| asset_key | string | 否 | 工作区 key（格式 Asset_xxx），仅在报错需要选择时传 |

**注意**：需完整结果时，从 page_num=1 开始连续查询直到没有更多数据。

---

## WorkHour 工时域

### workhour.list-schedule

获取指定人员在时间区间内的排期与工作量明细。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| user_keys | array | 是 | 用户标识（名称/邮箱/userkey），**每次最多 20 个** |
| start_time | string | 是 | 开始时间，格式 YYYY-MM-DD |
| end_time | string | 是 | 结束时间，格式 YYYY-MM-DD，**单次跨度最大 3 个月** |
| work_item_type_keys | array | 否 | 工作项类型列表，查询所有传入 `_all` |

**调用约束**（必须遵守）：
1. 每次最多 20 个用户，多人拆分批次并行
2. 单次跨度 ≤ 3 个月，超出按月拆分
3. 所有批次完成后再汇总，未完整获取前不得输出结论

### workhour.list-records

查看工作项的工时登记记录。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_type | string | 是 | 工作项类型 |
| work_item_id | string | 是 | 工作项 ID |

---

## UserGroup 人员域

### user.search

批量查询用户基础信息。用于将姓名/邮箱转换为 userkey。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_keys | array | 是 | userKey、Email 或名字，最多 20 个 |
| project_key | string | 否 | 空间 key |

### user.me

查看当前用户信息。无需参数。

> **MQL 中**可直接用 `current_login_user()` 函数，无需提前获取用户信息。如需获取当前用户的 userkey/姓名等详细信息，可用 `user.search` 传入 `current_login_user()` 作为参数。

### team.list

查看空间下的团队列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 否 | 空间 key |

### team.list-members

查看团队成员列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| team_id | string | 是 | 团队 ID |

---

## View 视图域

### view.get

根据视图 ID 获取该视图下的工作项列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| view_id | string | 是 | 视图 ID |
| project_key | string | 否 | 空间 key |
| page_num | number | 否 | 分页页数起点 |
| fields | array | 否 | 要查询的字段 |
| url | string | 否 | 视图链接，可自动解析 |

### view.search

按名称搜索视图。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| view_scope | string | 是 | 视图范围 |
| key_word | string | 是 | 关键词 |

### view.create-fixed

创建固定视图。上限 200 个工作项。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| name | string | 是 | 视图名称 |
| work_item_type | string | 是 | 工作项类型 |
| work_item_id_list | array | 是 | 工作项 ID 列表 |

### view.update-fixed

更新固定视图。add/remove_work_item_ids 二选一。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| view_id | string | 是 | 视图 ID |
| work_item_type | string | 是 | 工作项类型 |

---

## Chart 度量域

### chart.get

查看图表详情。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| chart_id | string | 是 | 图表 ID |

### chart.list

查看视图下的图表列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| view_id | string | 是 | 视图 ID |

---

## Comment 评论域

### comment.add

添加评论。支持 markdown。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| work_item_id | string | 是 | 工作项 ID |
| comment_content | string | 是 | 评论内容 |

### comment.list

查看评论列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_id | string | 是 | 工作项 ID |

---

## SubTask 子任务域

### subtask.update

创建/修改/完成/回滚子任务。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| node_id | string | 是 | 节点 ID |
| work_item_id | string | 是 | 工作项 ID |
| action | string | 是 | create/update/confirm/rollback |

---

## Relation 关系域

### relation.list

查看关联的工作项列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |
| work_item_id | string | 是 | 工作项 ID |
| relation_field_key | string | 否 | 关联关系字段 key，从 `relation.meta-definitions` 获取 |
| relation_id | string | 否 | 关联关系 ID，从 `relation.meta-definitions` 获取 |
| node_id | string | 否 | 节点 ID，查询某节点下的关联时传入 |
| page_num | number | 否 | 分页页码，从 1 开始 |
| page_size | number | 否 | 每页数量，最大 50 |

### relation.meta-definitions

查看空间下的关联关系定义。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_key | string | 是 | 空间 key |

---

## 字段值格式（field_value）

`workitem.create` / `workitem.update` 中 field_value 的格式因字段类型而异：

| 字段类型 | 格式 | 示例 |
|---------|------|------|
| template | 模板 ID（**创建必填**） | `145405865`。用 `workitem.meta-fields(field_keys=["template"])` 获取 |
| text / multi-pure-text / link / bool / number | 单个字面值 | `"测试工作项"` |
| user | 单个 userkey | `"7509072868295085608"` |
| multi-user | userkey 数组 | `["7509072868295085608","7509072868295085609"]` |
| select / radio / tree-select | 枚举项 option_id | `"437794"`。先从字段配置获取枚举值 |
| multi-select | option_id 数组，支持 free_add | `[{"option_id":"111"},{"option_id":"222"}]` |
| multi-text | markdown 格式 | `"**加粗**内容"` |
| date | 毫秒时间戳（天精度） | `1722182400000` |
| schedule | 时间戳数组 [开始, 结束] | `[1722182400000,1722355199999]` |
| precise_date | 对象 {start_time, end_time} | `{"start_time":1722182400000,"end_time":1722355199999}` |
| workitem_related_select | 关联工作项 ID | `145405865` |
| workitem_related_multi_select | 关联 ID 数组（**数字类型**） | `[145405865,145405866]` |
| role_owners（仅创建时） | 角色-人员数组 | `[{"role":"RD","owners":["userkey1"]}]` |

> 更新角色时不用 fields，用 `workitem.update` 的 `role_operate` 参数。

---

## 常用场景速查

| 场景 | 推荐命令 | 说明 |
|------|----------|------|
| 验证空间 | `project.search` | 空间名 → project_key |
| 查询工作项类型 | `workitem.meta-types` | 确认合法 type_key |
| 查询字段配置 | `workitem.meta-fields` | 字段 key、枚举值、类型 |
| 人名→userkey | `user.search` | 批量转换，最多 20 个 |
| 当前用户信息 | `user.me` | 无需参数 |
| 复杂条件查询 | `workitem.query` | 支持条件筛选、时间范围、团队等 |
| 查我的工作项 | `mywork.todo` | 直接获取当前用户的待办/已办 |
| 团队排期统计 | `workhour.list-schedule` | 每次 ≤20 人，≤3 月 |
| 创建需求/任务 | `workitem.create` | 需先确认字段信息和模板 ID |
| 修改状态/负责人 | `workitem.update` | 字段用 fields，角色用 role_operate |
| 完成/回滚节点（节点流） | `workflow.transition` | action=confirm 或 rollback |
| 流转状态（状态流） | `workflow.transition-state` | 先用 `workflow.list-state-transitions` 获取 transition_id |
| 查看视图数据 | `view.get` | 获取视图下的工作项列表 |

## URL 参数处理

用户可能直接提供飞书项目链接，大部分命令支持 `url` 参数自动解析：
- `project_key`、`work_item_type`、`work_item_id`、`view_id`

**常见 URL 动作**：
- 详情页 URL + 无明确意图 → `workitem.get(url=...)`
- 详情页 URL + "修改XX为YY" → `workitem.update(url=..., fields=...)`
- 详情页 URL + "完成/流转" → 先 `workitem.get(url=...)` 获取 node_id → `workflow.transition(action="confirm")`
- 详情页 URL + "回滚" → 同上 → `workflow.transition(action="rollback", rollback_reason=...)`
- 视图页 URL → `view.get(url=...)`

## 通用规范

### 请求处理流程

收到用户输入后，按以下步骤处理：

**1. 参数提取**：从自然语言中提取关键参数：
- 空间名、工作项类型、时间范围、人员、筛选条件等
- 正确区分空间名与筛选维度（如「XX空间下YY业务线的缺陷」中 XX 是空间名，YY 是筛选条件）
- 含 URL 时直接传入命令的 `url` 参数，跳过后续确认步骤

**2. 参数确认**（禁止猜测）：
- **空间**：用 `project.search` 探测 → 唯一则用，多个则让用户选，无匹配则问用户
- **工作项类型**：用 `workitem.meta-types` 获取类型列表 → 唯一相关则用，多个则让用户选
- **人员**：用 `user.search` 转换人名 → 匹配到多个用户时，**禁止自行选择**，展示完整列表让用户指定；无歧义的不需确认
- **缺失的必要参数**：直接问用户，多项缺失时合并为一条消息询问
- **探测 ≠ 猜测**：探测结果不唯一时，必须展示并询问用户，禁止自行选择

> 个人待办（`mywork.todo`）和 URL 直接操作无需确认步骤。

**3. 元数据收集**（无需用户参与）：
- 调用 `workitem.meta-fields` 获取字段定义（key、类型、枚举值）
  - 需要特定字段时用 `field_keys` 精确查询（如 `field_keys=["template"]`）
  - 不确定字段名时用 `field_query` 模糊查询
- 如涉及角色，并行调用 `workitem.meta-roles`
- **从字段配置中提取关键信息**：
  - 状态字段：type 为 `_work_item_status`，含「完成」「关闭」「终止」的值为完成态
  - 排期字段：type 为 `schedule`，MQL 中用 `__排期字段名_开始时间` / `__排期字段名_结束时间`
  - 优先级字段：key 为 `priority` 或 name 含「优先级」

> 简单直调场景（如 `comment.add`、`workitem.list-op-records` 等只需 project_key + work_item_id 的操作）可跳过此步骤。

**4. 执行**：调用目标命令完成操作，按下方「并行调用」和「大结果处理」规范执行。

### 并行调用

无依赖的命令调用应并行发起。

**必须串行**（前者输出是后者输入）：
- `project.search` → `workitem.meta-fields` → `workitem.query`
- `workitem.get` → `workflow.transition` / `workitem.update`
- `workitem.meta-fields` → `workitem.create`

**可并行**：
- `workitem.meta-fields` 和 `workitem.meta-roles`（同类型）
- 多种工作项类型的 `workitem.meta-fields`（如 story + issue）
- 各条件的 count 查询、多人排期分批查询

### 大结果处理

- **分批查询**：`workhour.list-schedule` 多人时拆成每批 ≤ 20 人并行
- **精简 SELECT**：只选必要字段，避免富文本等大体积字段
- **按需翻页**：先读首页获取总数，按需翻页

### 错误处理

- 失败后分析错误信息，针对性修正后重试
- **连续 3 次同类失败后停止**，向用户说明原因，询问如何继续

### 通用自愈规则（最多自动重试 2 次）

提取报错中的 `err_msg` 或 `inner_err`，按以下规则修复：

| 报错特征 | 自愈动作 |
|---------|---------|
| `cannot unmarshal object...`（数据格式错误） | 仅改变格式（数字↔字符串、单值↔数组、对象↔纯字符串），值不变 |
| `不满足层级配置`（级联层级错误） | 查 `children` 树，**展示末级叶子节点让用户选择** |
| `invalid select option(s)`（枚举值不合法） | 从 `possible values` 匹配；能唯一匹配则修正重试，否则询问用户 |

### 通用熔断规则（立即终止，禁止盲目重试）

| 条件 | 说明 |
|------|------|
| 空间未找到 | `project.search` 失败超过 3 次 |
| 权限不足 | 接口返回 Permission Denied |

**高频错误速查**：

| 错误现象 | 修复方式 |
|---------|---------|
| 找不到空间 | 用 `project.search` 验证，确认 project_key |
| 找不到工作项类型 | 用 `workitem.meta-types` 确认合法 type_key |
| 权限错误 | 确认当前用户是否有对应空间的访问权限 |
| MQL 查询失败 | 确认 FROM 用 `` `空间名`.`工作项类型` `` 格式 |
| 数组字段比较报错 | 改用 `array_contains` 或 `any_match` |
| node not found | 先 `workitem.get` 获取真实 node_id，禁止猜测 |
| mywork.todo 需选择工作区 | 根据报错中的工作区列表，将 asset_key（Asset_xxx）传入重试 |
| 人名/团队名重复 | 用 `<id:xxxx>` 消歧语法（见 MQL 语法参考） |
| 节点流转失败 | 节点流用 `workflow.transition`；状态流用 `workflow.transition-state`（需先 `workflow.list-state-transitions` 获取 transition_id，再 `workflow.list-state-required` 获取必填项） |
| 创建工作项缺少模板 | `workitem.meta-fields(field_keys=["template"])` 获取 |
| 角色更新失败 | 不用 fields，用 `workitem.update` 的 `role_operate` 参数 |
| 人名→userkey 失败 | 用 `user.search` 批量查询 |

**补充错误速查**（低频但需注意）：

| 错误现象 | 原因 | 修复方式 |
|---------|------|---------|
| MQL 返回为空但数据存在 | 字段名用了英文 field_key | 调用 `workitem.meta-fields` 确认字段名 |
| 日期区间字段查询失败 | 直接查询了区间字段 | 用子字段 `` `__字段名_开始时间` `` |
| 角色查询无结果 | 未加 `__` 前缀 | 用 `` `__{角色名}` `` 格式 |
| 空间名不唯一 | 中文名匹配到多个空间 | 用 `project.search` 验证后用 project_key 重新调用 |
| 人员字段写入失败 | field_value 格式不对 | user 类型传单个 userkey，multi-user 传 userkey 数组 |
| 字段名不正确 | 字段 key 拼写错误 | 先 `workitem.meta-fields` 确认 |
