---
name: alert-info-fetcher
description: 专家的数据获取能力。`get_user_and_org_info`、`get_org_detail`、`get_pending_project_list` 均由 `query_todo_*.py` 经共享客户端调用，AI 禁止裸调。供预警专家获取机构信息、证件预警清单与备案号项目预警分组。
---

# 预警专家 · 数据获取能力

## ⛔ MCP 调用封装说明（AI 禁止裸调 MCP 工具）

> 本 skill 对**数据类** MCP 工具的封装分两类：
> - ⭐ **`get_user_and_org_info`**：**由查询脚本经 `mcp_client` 内部调用**（`query_todo_summary.py` / `query_todo_detail.py`），AI 禁直调（文档见 `references/tools/get_user_and_org_info.md`）。
> - ✅ **`get_org_detail` / `get_pending_project_list`**：**已封装进 `references/scripts/query_todo_summary.py` / `query_todo_detail.py`**，AI **只通过 `execute_command` 运行脚本拿结果，禁止裸调**。其字段契约与调用规范已并入脚本 docstring 注释（唯一真相源，非独立 .md 文档）。
>
> 脚本已内置：参数构造（字段类型 / 嵌套结构 / repeated 裸数组等）、入口守卫（has_pending_review / 审批中）、一致性校验（no≠old_no / 图片域名）、失败上抛（绝不降级）。脚本 docstring 注释为字段契约与调用规范的权威文档（唯一真相源），改动脚本须同步更新注释。


## 概述

专家内部使用的 MCP 数据获取能力封装。**统一封装**以下场景的 MCP 工具调用：

- ⭐ **首次查询脚本内调用** `get_user_and_org_info`：机构准入判定 + 拿 `org_no` / `org_name` / `type_of_organization`（由 `query_todo_summary.py` / `query_todo_detail.py` 内部经 `mcp_client` 调用，AI 禁直调）
- 获取机构详情（含 `cert_warning` 证件预警清单）
- 获取项目级预警分组（含 `warning_types=[1]` 备案号即将过期）

>📌 **机构类型只有一个概念**：`get_user_and_org_info.type_of_organization` 与 `get_org_detail.institution_type` **是同一个东西**（同值域、同语义）。**优先用脚本输出 `org.type_of_organization`**（来自 `get_user_and_org_info`，失败时脚本已回退为 `institution_type`），不必为了机构类型额外调接口。

## 触发场景

由预警专家在以下情境加载：

- **首次查询**：运行查询脚本（脚本内调 `get_user_and_org_info` 做准入 + 取上下文，输出 `org` 字段）
- **查询计数**意图：运行 `references/scripts/query_todo_summary.py` 直接拿到组装好的 `title`/`subtitle`（脚本内并行调 `get_user_and_org_info` + `get_org_detail` + `get_pending_project_list`）；详情用 `query_todo_detail.py [--scope cert|record|both]`
- **处理证件更新**意图：需要机构编号、机构类型（决定证件字段规则）、当前证件明细等基础信息时
- **处理备案号更新**意图：需要项目级备案号完整分组明细（由 `query_todo_detail.py --scope record` 一次性拉全提供）

## 工具清单

| 工具名 | 用途 | 参考文档 |
|--------|-----|---------|
| `get_user_and_org_info` | ⭐ **由查询脚本经 `mcp_client` 内部调用（AI 禁直调）**：机构准入判定（`org_no` 为空则专家不可用）+ 提供 `org_no` / `org_name` / `type_of_organization` 等上下文（脚本输出 `org` 字段） | `references/tools/get_user_and_org_info.md` |
| `get_org_detail` | 拿机构详情 + `cert_warning` 证件预警清单（机构类型优先用脚本 `org.type_of_organization`）| ✅ 已封装进 `references/scripts/query_todo_summary.py` / `query_todo_detail.py`，AI 禁裸调；字段契约见脚本注释 |
| `get_pending_project_list` | 拿项目级预警分组（备案号即将过期等）| ✅ 已封装进 `references/scripts/query_todo_summary.py` / `query_todo_detail.py`，AI 禁裸调；字段契约见脚本注释 |

## 查询计数意图（AI 仅做编排，调用脚本拿结果）

> ⛔ AI 禁止裸调 `get_org_detail` / `get_pending_project_list`，一律运行封装脚本。

机构上下文（已由脚本在首次查询时随 `org` 字段一并返回）：`org_no` / `org_name` / `type_of_organization`。

查询计数（运行脚本，一步到位）：

```bash
cd skills/alert-info-fetcher/references/scripts && python3 query_todo_summary.py
```

脚本内部已并行调 `get_org_detail` 与 `get_pending_project_list` 两个数据源（参数与分页由脚本内封装，AI 无需感知），
并按下方"查询计数意图的返回体"规范**逐字符**组装好 `title` / `subtitle` / `kind` / `has_pending_review`，直接返回：

```json
{ "title": "证件更新", "subtitle": "<逐字符模板>", "kind": "cert | record | both | none", "has_pending_review": false }
```

- AI **原样消费** `title` / `subtitle` / `kind` 填入可点击列表，**严禁**自行编造/润色任何字（逐字符模板见下方）。
- `kind` 供 AI 决定后续流程分支：`cert` → 走证件更新流程；`record` → 走备案号更新流程；`both` → 两类都有待办、须弹窗二选一；`none` → 无待办。
- `has_pending_review`：证件审批中守卫（`true` → 证件入口暂不可用），**仅供 AI 内部分支判断，不进 Leader 菜单**。
- 具体哪些证件 / 哪些项目备案号要更新，用 `query_todo_detail.py [--scope cert|record|both]` 获取（脚本内已分页拉全、排序、过滤）。

**说明**：机构信息已由首次查询脚本随 `org` 字段一并返回（`org_no` / `org_name` / `type_of_organization`），**无需额外调用**。若在处理证件更新的开场话术中需要"张三，您好，[机构名]的证件..."之类的话术，直接取脚本输出 `org.org_name`（`get_org_detail` 已封装进脚本、AI 禁裸调，⛔ 不要为拿机构名去裸调它）。

## 查询计数意图的返回体（由脚本生成，AI 原样消费）

> ⚠️ 预警专家在查询计数意图下**只**返回以下扁平四字段（与 `query_todo_summary.py` 实际输出一致）：

```json
{ "title": "证件更新", "subtitle": "法人身份证已过期, 请尽快更新证件, 我来协助你更新", "kind": "cert", "has_pending_review": false }
```

- `kind`：`cert` → 走证件更新流程；`record` → 走备案号更新流程；`both` → 两类都有待办、须弹窗二选一；`none` → 无待办。供 AI 决定后续分支。
- `has_pending_review`：证件审批中守卫（`true` → 证件入口暂不可用，不影响备案号更新）；**仅供 AI 内部分支判断，不进 Leader 菜单**（Leader 菜单仅消费 `title`/`subtitle`/`kind`）。
- `title` / `subtitle` 由脚本**逐字符**生成（`cert` 优先级 > `record`、只取最紧迫 1 条、`has_pending_review` 审批中文案等规则均在脚本内实现），AI **严禁**自行计算或改写。
- ⛔ **`cert_count` / `record_count` / `cert_list` / `record_list` 等结构化字段不出现在本意图返回值中**——它们是 `query_todo_detail.py` 的内部工作结构（供「处理证件/备案号更新」流程拉全量明细用），见下方「详情字段 schema」。

## todo_card 组装（可点击列表专用）

> ⛔⛔ 一旦遇到"需要用户从多个选项中选一个"的决策点（如任务一/任务零：证件与备案号都有待办），**必须调用 `AskUserQuestion`** 把选项弹出。

本 skill 负责**逐字符生成** `title`/`subtitle` 文案；调用方（本专家）把这两个字段**原样**填入 `AskUserQuestion` 的 `options[].label`/`description`，**MUST NOT 自行编造/润色**。

> ## ⛔⛔ 头等铁律：title / subtitle 是**逐字符固定的模板**，严禁自由发挥
>
> **返回 JSON 只有 `title`、`subtitle`、`kind`、`has_pending_review` 四个扁平字段（不含 `key` / `items` / `count` / `cert_list` / `record_list` 等）**——`title`/`subtitle` 由脚本**逐字符**生成，AI MUST 原样消费，MUST NOT 做任何"润色"、"优化"、"信息增强"。（`has_pending_review` 仅供 AI 内部分支，不进 Leader 菜单）
>
> **五条绝对禁令**（每条都对应过真实事故）：
> 1. ❌ **禁止在一条 subtitle 里拼多个条目**（哪怕有 5 个项目到期，subtitle 也只描述**最紧迫的那一条**；其余明细用户点进去后由处理流程分页展示）
> 2. ❌ **禁止增删模板中的任何字**（不许加"请尽快更新备案号"这类不在模板里的尾巴；也不许删模板里的"的"、"在"）
> 3. ❌ **禁止替换同义词**（"到期"不许写成"过期"；"天后到期"不许写成"天后过期"）
> 4. ❌ **禁止增删标点或改变标点全半角**（模板里是半角逗号+空格 `, `，不许换成全角 `，`；模板里没有 `；` 就不许出现 `；`）
> 5. ❌ **禁止自行增删占位符**（`{project_no}` 必须出现且必须是真实项目 ID；不许自己给项目名套`「」`）
>
> **自查方法**：把你生成的 subtitle 和模板逐字符比对，**只有占位符位置可以不同**，其他每一个字、每一个空格、每一个标点都必须完全一致。

统一结构（扁平四字段：title / subtitle / kind / has_pending_review，由 Leader 自行补 `key`）：

```json
{
  "title": "<菜单主标题, 严格取自脚本生成的固定值>",
  "subtitle": "<单行摘要, 严格由脚本逐字符生成>",
  "kind": "cert | record | both | none",
  "has_pending_review": true | false
}
```

**约定**：
- **返回 JSON 只有 `title`/`subtitle`/`kind`/`has_pending_review` 四个字段，没有 `key`/`count`/`disabled` 之类的控制字段**——是否展示、是否有前置限制，全靠 `title`/`subtitle` 是否为空及 subtitle 文案内容来传达（`has_pending_review` 仅供 AI 内部分支，不进菜单）
- **本 skill（alert-expert）固定只生成 1 条 `title`/`subtitle`/`kind`**——因为**用户视角只需要一个"证件与备案号"入口**，具体是证件还是备案号由本专家在「处理证件与备案号」步骤内部询问/决定，无需在入口层拆成两项（`kind=both` 时由本专家自己弹窗二选一）
- **优先级：证件 > 备案号**（由 `query_todo_summary.py` 按此规则算出，AI 不重算）：`kind=cert` / `kind=record` / `kind=both` 已直接给出分流结论；两者都无待办 → `kind=none`、`title`/`subtitle` 留空
- `title` 为空 → 本专家 / Leader MUST 视为"该类无待办"，从可点击列表中 **跳过该行**（等价于不下发）
- 本 skill 仅负责单条 title/subtitle/kind 内容；独立入口下由本专家直接把它呈现为可点击选项；被 Leader 调度时由 Leader 自行补 `key="alert"`

### `cert` 组装规则（脚本输出 spec · 仅供核对，AI 不计算）

> ⚠️ 以下 `title`/`subtitle` **全部由 `query_todo_summary.py` 逐字符生成**，AI 只原样消费、**严禁**自行计算或改写。本表仅作为**人肉核对脚本输出是否符合规范**的参考（验证 oracle），不是 AI 执行步骤。

**取"最紧迫的证件"作为 subtitle 素材**——`cert_list` 已按 `expired`+`remaining_day` 升序排序，**只取 `cert_list[0]` 这一条**（脚本内实现）。

| 条件 | `title` | `subtitle` |
|-----|--------|-----------|
| `cert_count === 0` | `""` | `""` |
| `cert_count > 0` 且 `has_pending_review === false` 且 `cert_list[0].expired === false` | `"证件更新"` | 模板 A |
| `cert_count > 0` 且 `has_pending_review === false` 且 `cert_list[0].expired === true` | `"证件更新"` | 模板 B |
| `cert_count > 0` 且 `has_pending_review === true` | `"证件更新"` | `"当前机构信息有申请单待审批, 审批完成后才能提交证件更新。"`（固定文案） |

- **title 固定值**：`证件更新`
- **模板 A（未过期）**：`{cert_type_label}在 {remaining_day} 天后到期, 请尽快更新证件, 我来协助你更新`
- **模板 B（已过期）**：`{cert_type_label}已过期, 请尽快更新证件, 我来协助你更新`
- **占位符**：`{cert_type_label}`←`cert_list[0].cert_type_label`（映射见下文「cert_type 映射」）；`{remaining_day}`←`cert_list[0].remaining_day`

> 逐字符禁改的细则（半角逗号+空格、禁拼多条、禁同义词替换等）见上方「头等铁律」，此处不再重复。

### `record` 组装规则（脚本输出 spec · 仅供核对，AI 不计算）

> ⚠️ 以下 `title`/`subtitle` **全部由 `query_todo_summary.py` 逐字符生成**，AI 只原样消费、**严禁**自行计算或改写。本表仅作核对参考，不是 AI 执行步骤。

**取"最紧迫的项目"作为 subtitle 素材**——`record_list[0]`（脚本内只取首项，哪怕 `record_count` 是 5）。

| 条件 | `title` | `subtitle` |
|-----|--------|-----------|
| `record_count === 0` | `""` | `""` |
| `record_count > 0` | `"备案号更新"` | 下方模板 |

- **title 固定值**：`备案号更新`
- **subtitle 模板**（**无尾巴**，与证件不同）：`{project_no} {project_name} 的备案号在 {pending_stop_days} 天后到期`
- **占位符**：`{project_no}`←`record_list[0].project_no`（**项目 ID，必须有**）；`{project_name}`←`record_list[0].project_name`（**裸文本，不加 `「」`**）；`{pending_stop_days}`←`record_list[0].pending_stop_days`

**其他约束**：
- **备案号 subtitle 不受 `has_pending_review` 影响**（机构级审批中锁定只针对证件）
- 若首个项目恰好是 `fund_raising_program_audit_status === 2`（审批中）而其他项目可更新，subtitle 仍取该首项——展示只是文案，用户点入后 Skill 会按项目级守卫拦截审批中项目

**注意（供处理流程消费详情时参考）**：
- `record_count` 是**项目数**（不是预警条目数）；**审批中项目照常计入**（保持"到期数"原始语义），`updatable` 字段供后续 Skill 决策"是否可发起更新流程"
- **不返回机构整体待办计数**：独立入口无需"全部待办"汇总，用户点入对应流程后再按需拉取
- **备案号更新流程需要项目级字段**（由 `query_todo_detail.py --scope record` 拉全）：`fund_raising_program_id` 用作 `update_org_record_number` 的 `id` 入参；`fund_raising_program_no` 用作 `no` 一致性校验基准；`fund_raising_program_audit_status` 用作**项目级审批中守卫**（`===2` 时拦截）。（v2 已从 `warns[].id` 迁移到项目级 `fund_raising_program_id`；`warning_id` 是预警条目主键，本流程不使用）

**`audit_status_label` 组装规则**（由脚本计算，供详情展示；`updatable = status != 2`）：

| `fund_raising_program_audit_status` | 语义常量 | `audit_status_label` | `updatable` |
|------------------------------------|---------|---------------------|-------------|
| `1` | `AUDIT_APPROVED` | `"已通过"` | `true` |
| `2` | `AUDIT_PENDING` | `"审批中"`| `false` |
| `3` | `AUDIT_REJECTED` | `"已驳回"` | `true`（用户可重新提交）|

## 详情字段 schema（脚本内部转换，供处理流程消费 · 参考用）

> ⚠️ 以下转换（`cert_warning.items` → `cert_list`、`cert_type_label` 映射、`expired` 判定、排序）**全部在 `query_todo_detail.py` / `query_todo_summary.py` 内由代码实现**，并已在脚本 docstring 声明为唯一真相源。此处仅作**人肉核对参考**，AI 不重算、不重写。

`get_org_detail` 返回的 `cert_warning.items` 每一条形如：

```json
{ "cert_type": 1, "end_date": "2026-09-01", "remaining_day": 25 }
```

转换为预警专家统一的 `cert_list` 结构（脚本输出，供处理流程展示）：

```json
{ "cert_id": null, "cert_type_code": 1, "cert_type_label": "社会组织法人登记证书", "expire_date": "2026-09-01", "remaining_day": 25, "expired": false }
```

**cert_type 与 cert_type_label 的映射**（与 `OrgCertType` 枚举一致，脚本 `_cert_type_label` 实现）：

| cert_type 值 | label（用户可读名称）| 说明 |
|--------------|--------------------|-----|
| 1 | 社会组织法人登记证书 | `charitable_person` |
| 2 | 慈善组织公开募捐资格证书 | `charitable_public`，仅公募机构会出现 |
| 3 | 法人身份证 或 专项基金负责人身份证 | `corporation_id_card`；结合 institution_type 联合判定：`institution_type ∈ {1,2}` 时为机构法人身份证，`institution_type == 3` 时为专项基金负责人身份证 |

**expired 字段**（脚本计算）：`remaining_day == -1` → `expired: true`；`remaining_day > 0` → `expired: false`

**排序约定**（脚本内已实现）：
- 证件预警清单：按 `(expired ? -1 : remaining_day)` 升序，已过期永远排最前
- 备案号项目预警清单：后端通常按 `pending_stop_days` 升序，脚本拉全后如需明确顺序再排一次

## 非超管场景

- 后端约定：**`cert_warning` 仅当调用账号在其所属机构内是超管时才返回**（权限判断由后端完成，预警专家**不主动读用户角色字段**，只按 nil 处理）
- 非超管调用时 `cert_warning` 为 nil，本skill 视为"无证件预警"（`cert_count: 0, cert_list: []`）
- `get_pending_project_list` **不受**超管权限影响，非超管也能拿到项目级预警
- **不主动向用户暗示"因您不是超管所以看不到"**，避免泄露内部权限信息

## 老字段的兼容性

`get_org_detail` 也返回旧字段 `detailed.certificate_validity_day` 和 `detailed.charitable_public_day`。**预警专家应优先使用 `cert_warning`**，理由：

- `cert_warning` 是"预警清单"（只装 <=90 天条目），已经做过窗口过滤
- 老字段是"证件剩余天数"（含长期 999999、已过期 -1），需要调用方自己过滤

**⚠️ 老字段禁止用于**：
- 决定是否展示证件到期项（应用 `cert_warning` 判断）
- 决定分派菜单里"证件/备案号更新"是否展示

## 铁律

###⛔头等铁律：接口不可用时严禁降级

**MCP 工具报错、RPC 未注册、超时、返回空/异常时，必须立即上抛错误**，绝不允许：

- ❌ 尝试用**其他 MCP 工具**拼凑同一份数据（如`get_pending_project_list` 挂了就用 `get_project_list + get_project_detail` 拼凑备案号数据）
- ❌ 尝试用**其他数据源接口**（如 `get_org_todo_list` / `GetTodoInfoForSkill`）代替本skill 声明的白名单
- ❌ 通过 `execute_command` 写 Python 脚本、发起 HTTP 请求、爬网页（除非对应 Skill 明确列出脚本及严格触发条件，例如用户已提供有效慈善中国详情页链接并明确选择查询）
- ❌ 静默继续跑：把接口错误吞掉，用"合理默认值"（如 count=0）返回

**唯一允许的响应**：如实返回错误 JSON：

```json
{
  "error": "<tool_name> 调用失败",
  "reason": "<原始错误信息>",
  "attempted_tool": "<tool_name>",
  "retry_suggestion": "该接口暂不可用，请稍后重试。请勿使用其他接口补齐数据。"
}
```

**为什么这条铁律头等**：接口挂掉时的静默降级会导致：
1. **字段口径不一致**：`get_project_list.fundras_state` ≠ `get_pending_project_list.projects[].fund_raising_program_audit_status`，语义未必对齐
2. **用户看到假成功**：以为"3个项目要更新"，实际漏掉了应有的项目
3. **审批状态被错标**：把"审批中"标成"已通过"会引发用户点选后误操作
4. **调试地狱**：Skill 层看似正常运行，但数据来源与文档偏离，问题极难定位

### ⛔ MCP 工具白名单

本 skill **只能**使用以下 3 个 MCP 工具，其他工具即使能返回类似数据也**严禁**使用：

-✅ `get_user_and_org_info`
- ✅ `get_org_detail`
- ✅ `get_pending_project_list`

**严禁绕道**：
- ❌ `get_org_todo_list` / `GetTodoInfoForSkill`
- ❌ `get_project_list` + `get_project_detail`（这些是其他专家场景的工具）
- ❌ `get_process_list` / `get_process_detail`
- ❌ `query_data` / `get_data_by_template`
- ❌ 任何未在本文件"工具清单"章节列出的工具

### 其他铁律

**以下数据口径约束已由 `query_todo_*.py` 在代码内强制（详见脚本 docstring 铁律），AI 与维护者以此为准，本文不再重复**：`cert_warning` 为 nil 视为无预警（非报错）、`cert_type`→label 映射不许自创、`remaining_day==-1` 即已过期、`warns.length` 不得加总代替 `pending_stop_project_count`、不得传空 `warning_types`、不得混用两接口的 days 语义、`has_pending_review` 仅作用于证件（不作用于备案号）、`fund_raising_program_audit_status` 必须透传、审批中项目不扣减 `record_count`、查数阶段不传 `page_size:100`。

**AI 行为铁律（脚本无法代劳，必须遵守）**：
- ❌ 返回 `items` 数组 / `key` / `count` 等字段（本专家 / Leader 仅依赖 `title` / `subtitle` / `kind` 组装可点击列表）；也**不允许**调用方自行编造 title/subtitle
- ❌ **在一条 subtitle 里拼多个条目**（subtitle **只描述最紧迫的一条**，其余明细由用户点进去后的处理流程分页展示）
- ❌ **增删模板中的任何字**（如给备案号 subtitle 加"请尽快更新备案号"尾巴，或删掉"的"、"在"）
- ❌ **替换同义词**（"到期"写成"过期"、"天后到期"写成"天后过期"）
- ❌ **改变标点全半角**（模板是半角 `, `，不许换成全角 `，`；模板无 `；` 就不许出现）
- ❌ **丢失 `{project_no}` 项目 ID**（备案号 subtitle 必须以真实项目 ID 开头）
- ❌ 不能对非超管用户过多解释权限逻辑（数据主权）

## 参考文件

- `references/tools/get_user_and_org_info.md` — ⭐ 由查询脚本经 `mcp_client` 内部调用的用户与机构基础信息 MCP 工具
- `references/scripts/query_todo_summary.py` / `query_todo_detail.py` — ✅ 封装脚本，也是 `get_org_detail` / `get_pending_project_list` 的**唯一契约真相源**（字段语义、铁律见脚本 docstring 注释）；AI 只跑脚本、禁裸调
