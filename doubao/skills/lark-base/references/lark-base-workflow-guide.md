# Workflow guide

本文档是 Workflow 的入口指南，帮助选择步骤组合、理解创建/更新边界，并引导到 steps JSON SSOT。

> **配套文档**:
> - Workflow 的数据结构参考：[lark-base-workflow-schema.md](lark-base-workflow-schema.md)
> - 创建/更新时重点构造 `title` 和 `steps`；复杂度集中在 `steps[].type/data/next`
> - 启停状态使用专用的 enable / disable 命令管理，不要把创建成功当成已经启用
> - `+workflow-update` 是完整替换：从 `+workflow-get` 结果保留 `title`、`status`、`steps`，但请求体中的 `status` 不负责切换运行态；实际启停只使用 `+workflow-enable` / `+workflow-disable`，并以随后 get 的状态为准

## 交付红线

### 先确定目标运行态

计划中为本次明确目标的每个 Workflow 记录 `workflow_id`（新建时先记为待返回）、用户意图和 `target_status`。先按请求的整体最终交付意图解析同一目标最后一次明确的运行态指令，而不是按句中关键词机械抢先：明确启用或恢复取 `enabled`，明确停用、交付为草稿/预览或暂不启用取 `disabled`，明确保持当前启停状态取 `preserve`；同一目标有多次冲突指令时，以最后一次无歧义的指令为准。例如“先检查，确认后启用”最终是 `enabled`，“修改触发时间，但保持当前启停状态”最终是 `preserve`。

没有明确运行态指令时，再按表格从上到下匹配默认值，命中即停止：

| 用户意图 | `target_status` | 允许的状态动作 |
|---|---|---|
| 整体最终意图只是读取、检查、审计或解释 | `none` | 不创建、不更新、不启停 |
| 既有 Workflow 仅修改名称、描述或消息文案，未明确要求启停，且不改变触发时间、触发条件、接收人、动作类型或动作目标 | `preserve` | 保留首次 get 读到的运行态，不调用 enable/disable |
| 其余以执行语气要求新增或配置提醒、通知、自动发送、定时执行或触发后动作，或修改其触发时间、条件、接收人、动作类型或动作目标；即使没写“启用”也视为要求生效 | `enabled` | 完成定义后确保启用 |

只有用户本次明确指定或要求创建的 Workflow 才能进入该表；发现其他 disabled Workflow 不构成启用授权。祈使或执行语气本身不能把上表的纯定义编辑提升为 `enabled`：当前为 disabled 的既有 Workflow 若只改名称、描述或消息文案，仍取 `preserve`。静态文本、公式、视图和 Dashboard 不能代替用户明确要求的主动通知。

### 不可跳过的完成谓词

Workflow 子任务必须同时满足以下两项，才能标记完成或进入最终答复：

1. **定义后置条件：** 同一目标 ID 中本次请求涉及的全部可写定义字段与用户要求一致，包括适用的名称、描述、消息标题与正文、触发器、触发时间/时间配置（日期、时刻、周期、星期、间隔、起止时间和提醒偏移）、条件、接收人、动作类型和动作目标。
2. **状态后置条件：** 对 `enabled` / `disabled`，不截断 `status` 的 `+workflow-get` 必须证明返回的 `status` 等于 `target_status`；`preserve` 必须证明返回的 `status` 等于首次 get 的状态；`none` 不适用状态等式，其后置条件是没有执行任何创建、更新或启停写操作。

定义已经吻合或无需执行 `+workflow-update`，不能消除独立的运行态差异。`+workflow-create` 成功后默认返回 `disabled`；当 `target_status=enabled` 时，这只是中间态，必须继续调用 `+workflow-enable` 并对同一 ID `+workflow-get`。当明确要求主动提醒却不存在目标 Workflow 时，应创建并完成上述闭环，不能用说明文字、公式、视图或 Dashboard 冒充。

`+workflow-update` 是完整替换：从 `+workflow-get` 结果保留 `title`、`status`、`steps`，但请求体中的 `status` 不负责切换运行态；实际启停只使用 `+workflow-enable` / `+workflow-disable`。对同一失败原因只做一次定向修复和一次复验；仍不满足任一后置条件时明确报告未完成项，不得继续循环或虚假宣告完成。

---

## 快速开始

### 最简单的 Workflow

新增记录时发送消息通知：

```json
{
  "client_token": "1704067200",
  "title": "新订单自动通知",
  "steps": [
    {
      "id": "trigger_1",
      "type": "AddRecordTrigger",
      "title": "监控新订单",
      "next": "action_1",
      "data": {
        "table_name": "订单表",
        "watched_field_name": "订单号"
      }
    },
    {
      "id": "action_1",
      "type": "LarkMessageAction",
      "title": "发送通知",
      "next": null,
      "data": {
        "receiver": [{ "value_type": "user", "value": {"id": "ou_xxxx", "name": "张三"} }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "新订单提醒" }],
        "content": [
          { "value_type": "text", "value": "收到新订单" }
        ],
        "btn_list": []
      }
    }
  ]
}
```

---

## 场景速查表

| 场景 | 步骤组合 | 示例 |
|------|---------|------|
| 新增触发+通知 | AddRecordTrigger → LarkMessageAction | [下方](#示例1-新增记录触发--发送消息) |
| 按钮点击+调用外部接口+写入日志 | ButtonTrigger → HTTPClientAction → AddRecordAction | [下方](#示例-6-按钮触发--调用外部接口--写入同步日志) |
| 定时+循环 | TimerTrigger → FindRecordAction → Loop → LarkMessageAction | [下方](#示例2-定时触发--查找记录--循环遍历--发送消息) |
| 条件判断 | ... → IfElseBranch → 分支处理 | [下方](#示例3-条件分支-ifelsebranch) |
| 多路分类 | ... → SwitchBranch → 多分支处理 | [下方](#示例4-多路分支-switchbranch) |
| 复杂组合 | 定时+查找+循环+分支+消息 | [下方](#示例5-组合场景-定时查找循环分支消息) |

## 能力边界与意图识别

- 用户说“一按 / 一键 / 点一下就知道 / 按钮触发”时，优先评估 `ButtonTrigger`。如果结果需要沉淀给用户看，Workflow 应将判断结果写回表字段、日志表或消息，而不是只交付一段说明或普通看板。
- 记录新增/修改触发和定时扫描都可能实现提醒；选择前先判断用户要实时提醒还是周期巡检。若用定时扫描替代实时提醒，需要在交付里说明触发频率。

### 接收人来源门禁

消息接收人只能来自用户明确点名且可唯一解析的人员/群、用户明确指定的人员/群字段，或本轮此前已经确认的真实对象；“通知我/本人”属于对当前用户的明确授权。泛化职责称谓或模糊群组描述若无法唯一映射到真实对象，不得用当前用户、Base 创建人、记录创建人或任意默认账号兜底，也不得把示例 ID 写入正式配置。

接收人不明确时必须先澄清；澄清完成前不创建带伪造 `receiver` 的 Workflow，不启用不完整 Workflow。若已创建草稿则保持 `disabled`，并在最终答复中明确接收人仍待确认。回读时逐项核对 `receiver` 的来源和 `send_to_everyone`，防止扩大外发范围。

### 条件类型验收

创建或更新任何含条件的 Workflow 前，先用 `+field-list` 确认左值字段的真实类型，再按 [Workflow 数据结构](lark-base-workflow-schema.md) 的“条件值类型与非空约束”选择 `operator`、`value_type` 和右值。需要右值的 operator 禁止 `null`、空数组和空字符串；数值条件必须是非空有限 number，日期条件必须是合法 date，选项条件必须引用真实选项。

阈值丢失是静默失败：右值写成空数组或空字符串后，工作流仍会按时触发、状态仍是 `enabled`，只是永远匹配不到记录，不会有任何报错。同一需求的 View 筛选常常是对的，**不要因为视图配对了就认为工作流也对**，两者各自独立构造。

`+workflow-get` 回读时必须检查服务端保存后的完整 condition，而不是只看 Workflow 名称或状态。用户需求里有几个边界，保存后的 conditions 里就该有几个非空右值；逐项对照 `field_name / operator / value / value_type`，任一项不一致都保持或恢复 `disabled`。条件可用 `+record-list --filter-json` 表达且存在代表性数据时，用同口径的只读筛选确认命中范围；没有代表性数据时只验证保存条件。

同一条件定向修复一次后仍无法原样回读时，不再重复提交同一种数值或日期条件；改用能稳定回读的文本/布尔派生字段表达同一业务谓词，再重新预检。派生字段仍不能正确保存或验证时，只将该 Workflow 验收项标记 `blocked` 并保持 `disabled`；继续完成不依赖它的其他交付物，不把该 Workflow 列入已完成项，也不得把局部阻塞扩大为整个 Base 任务失败。

---

## 生命周期：创建不等于生效

要求提醒、自动通知、到期处理或状态联动“能够工作”时，按以下闭环交付；不要停在创建成功：

开始创建前先从用户原话登记每条流程的名称、触发时机/方向、条件、动作和接收人或目标记录。多条流程必须逐条保存 create 返回的 workflow_id，并分别走完下面的闭环；列表数量相符但任一条仍为 disabled、条件或动作不符，都不能视为完整交付。

```bash
# 1. 创建：新 workflow 默认 disabled
lark-cli base +workflow-create --as user --base-token <base_token> --json @workflow.json

# 2. 启用前预检：workflow 仍为 disabled，无真实触发副作用
lark-cli base +workflow-get --as user --base-token <base_token> --workflow-id <wkf_id>

# 3. 启用：只有用户明确要求草稿或保持禁用时才跳过
lark-cli base +workflow-enable --as user --base-token <base_token> --workflow-id <wkf_id>

# 4. 生效确认：同时验证 enabled 状态和最终定义
lark-cli base +workflow-list --as user --base-token <base_token> --status enabled
lark-cli base +workflow-get --as user --base-token <base_token> --workflow-id <wkf_id>
```

启用前的 `get` 必须逐项核对：trigger 的表、字段、条件和提前/推后方向符合题意；`next`、分支和引用指向真实 step；消息接收人、目标记录和写入动作来自真实字段与用户授权，不会扩大外发或写入范围。预检通过后才 enable，随后确认目标 workflow 出现在 enabled 列表。若启用后发现任何不符，先立即 `+workflow-disable` 并用 `+workflow-list --status disabled` 回查，再 update、重新执行启用前预检，最后 enable；`+workflow-update` 本身不会改变启停状态。

不要从“表里有日期/状态字段”自行推断并创建 workflow；只有用户明确要求提醒、自动化、状态联动或某项流程能够工作时才创建并启用。用户要求草稿或保持禁用时，保留 disabled，并在交付结果中明确说明该流程尚不会触发。

---
## 完整示例

### 示例 1: 新增记录触发 + 发送消息

**场景**: 当订单表新增记录时，发送飞书消息通知负责人。

```json
{
  "client_token": "1704067201",
  "title": "新订单自动通知",
  "steps": [
    {
      "id": "step_trigger",
      "type": "AddRecordTrigger",
      "title": "新增订单时触发",
      "next": "step_notify",
      "data": {
        "table_name": "订单表",
        "watched_field_name": "订单号",
        "condition_list": null
      }
    },
    {
      "id": "step_notify",
      "type": "LarkMessageAction",
      "title": "发送订单通知",
      "next": null,
      "data": {
        "receiver": [{ "value_type": "ref", "value": "$.step_trigger.fldManager" }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "新订单提醒" }],
        "content": [
          { "value_type": "text", "value": "客户 " },
          { "value_type": "ref", "value": "$.step_trigger.fldCustomer" },
          { "value_type": "text", "value": " 创建了新订单，金额：¥" },
          { "value_type": "ref", "value": "$.step_trigger.fldAmount" }
        ],
        "btn_list": [
          {
            "text": "查看订单",
            "btn_action": "openLink",
            "link": [{ "value_type": "ref", "value": "$.step_trigger.recordLink" }]
          }
        ]
      }
    }
  ]
}
```

**关键点**:
- `AddRecordTrigger` 监控 `table_name` 表的 `watched_field_name` 字段
- 使用 `ref` 引用触发器输出的字段值（注意是 fieldId，不是字段名）
- `recordLink` 是触发器内置输出，表示记录链接

---

### 示例 2: 定时触发 + 查找记录 + 循环遍历 + 发送消息

**场景**: 每天早上 9 点，查找所有待处理订单，给每个客户发送提醒。

```json
{
  "client_token": "1704067202",
  "title": "每日待处理订单提醒",
  "steps": [
    {
      "id": "step_timer",
      "type": "TimerTrigger",
      "title": "每天早上9点触发",
      "next": "step_find_orders",
      "data": {
        "rule": "DAILY",
        "start_time": "2025-01-01 09:00",
        "is_never_end": true
      }
    },
    {
      "id": "step_find_orders",
      "type": "FindRecordAction",
      "title": "查找所有待处理订单",
      "next": "step_loop_customers",
      "data": {
        "table_name": "订单表",
        "field_names": ["客户名称", "订单金额", "客户联系方式"],
        "should_proceed_when_no_results": false,
        "filter_info": {
          "conjunction": "and",
          "conditions": [
            {
              "field_name": "状态",
              "operator": "is",
              "value": [{ "value_type": "option", "value": { "name": "待处理" } }]
            }
          ]
        }
      }
    },
    {
      "id": "step_loop_customers",
      "type": "Loop",
      "title": "遍历每个订单",
      "children": {
        "links": [
          { "kind": "loop_start", "to": "step_send_reminder" }
        ]
      },
      "next": null,
      "data": {
        "loop_mode": "continue",
        "max_loop_times": 100,
        "data": [{
          "value_type": "ref",
          "value": "$.step_find_orders.fieldRecords"
        }]
      }
    },
    {
      "id": "step_send_reminder",
      "type": "LarkMessageAction",
      "title": "发送催办消息",
      "next": null,
      "data": {
        "receiver": [{
          "value_type": "ref",
          "value": "$.step_loop_customers.item.fldContact"
        }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "订单处理提醒" }],
        "content": [
          { "value_type": "text", "value": "您好，您的订单 " },
          { "value_type": "ref", "value": "$.step_loop_customers.item.fldName" },
          { "value_type": "text", "value": " 金额 ¥" },
          { "value_type": "ref", "value": "$.step_loop_customers.item.fldAmount" },
          { "value_type": "text", "value": " 正在处理中。" }
        ],
        "btn_list": []
      }
    }
  ]
}
```

**关键点**:
- `Loop.data` 必须传入 `ref` 类型的数据源（通常是 FindRecordAction 的 `fieldRecords`）
- `Loop.children.links` 必须包含 `kind: "loop_start"` 的链接指向循环体
- 循环体内用 `$.{loopStepId}.item.{fieldId}` 引用当前遍历记录的字段
- `$.{loopStepId}.index` 获取当前索引（从 0 开始）

---

### 示例 3: 条件分支（IfElseBranch）

**场景**: 根据订单金额判断，大额订单通知主管审批，小额订单自动通过。

```json
{
  "client_token": "1704067203",
  "title": "订单金额自动判断",
  "steps": [
    {
      "id": "step_trigger",
      "type": "AddRecordTrigger",
      "title": "新增订单时触发",
      "next": "step_check_amount",
      "data": {
        "table_name": "订单表",
        "watched_field_name": "订单金额"
      }
    },
    {
      "id": "step_check_amount",
      "type": "IfElseBranch",
      "title": "判断是否为大额订单",
      "children": {
        "links": [
          { "kind": "if_true", "to": "step_notify_manager", "label": "high", "desc": "金额>=10000" },
          { "kind": "if_false", "to": "step_auto_approve", "label": "normal", "desc": "金额<10000" }
        ]
      },
      "next": "step_log",
      "data": {
        "condition": {
          "conjunction": "or",
          "conditions": [
            {
              "conjunction": "and",
              "conditions": [
                {
                  "left_value": { "value_type": "ref", "value": "$.step_trigger.fldAmount" },
                  "operator": "isGreaterEqual",
                  "right_value": [{ "value_type": "number", "value": 10000 }]
                }
              ]
            }
          ]
        }
      }
    },
    {
      "id": "step_notify_manager",
      "type": "LarkMessageAction",
      "title": "通知主管审批大额订单",
      "next": "step_log",
      "data": {
        "receiver": [{ "value_type": "user", "value": {"id": "ou_manager", "name": "主管"} }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "大额订单待审批" }],
        "content": [
          { "value_type": "text", "value": "有大额订单 ¥" },
          { "value_type": "ref", "value": "$.step_trigger.fldAmount" },
          { "value_type": "text", "value": " 需要您审批" }
        ],
        "btn_list": []
      }
    },
    {
      "id": "step_auto_approve",
      "type": "SetRecordAction",
      "title": "自动标记小额订单为已审核",
      "next": "step_log",
      "data": {
        "table_name": "订单表",
        "ref_info": { "step_id": "step_trigger" },
        "field_values": [
          {
            "field_name": "审批状态",
            "value": [{ "value_type": "option", "value": { "name": "已自动审核" } }]
          }
        ]
      }
    },
    {
      "id": "step_log",
      "type": "GenerateAiTextAction",
      "title": "生成订单处理日志",
      "next": null,
      "data": {
        "prompt": [
          { "value_type": "text", "value": "请生成订单处理日志，金额：" },
          { "value_type": "ref", "value": "$.step_trigger.fldAmount" }
        ]
      }
    }
  ]
}
```

**关键点**:
- `IfElseBranch.children.links` 必须包含 `if_true` 和 `if_false` 两个分支
- `next` 指向两个分支汇合后的步骤（可选，为 null 则分支结束）
- `condition` 使用 OrGroup 结构，支持 `(A and B) or (C and D)` 的复杂条件
- 分支内可以用 `ref_info` 引用触发记录，用 `filter_info` 批量筛选记录

---

### 示例 4: 多路分支（SwitchBranch）

**场景**: 根据订单优先级（P0/P1/P2）执行不同的处理流程。

```json
{
  "client_token": "1704067204",
  "title": "按优先级分类处理订单",
  "steps": [
    {
      "id": "step_trigger",
      "type": "AddRecordTrigger",
      "title": "新增订单时触发",
      "next": "step_classify",
      "data": {
        "table_name": "订单表",
        "watched_field_name": "优先级"
      }
    },
    {
      "id": "step_classify",
      "type": "SwitchBranch",
      "title": "按优先级分类",
      "children": {
        "links": [
          { "kind": "case", "to": "step_p0_handler", "label": "p0", "desc": "P0-紧急" },
          { "kind": "case", "to": "step_p1_handler", "label": "p1", "desc": "P1-高优先级" },
          { "kind": "case", "to": "step_p2_handler", "label": "p2", "desc": "P2-普通" },
          { "kind": "case", "to": "step_other_handler", "label": "other", "desc": "其他" }
        ]
      },
      "next": null,
      "data": {
        "mode": "exclusive",
        "no_match_action": "classifyToOther",
        "child_branch_list": [
          {
            "name": "P0-紧急",
            "condition": {
              "conjunction": "or",
              "conditions": [
                {
                  "conjunction": "and",
                  "conditions": [
                    {
                      "left_value": { "value_type": "ref", "value": "$.step_trigger.fldPriority" },
                      "operator": "is",
                      "right_value": [{ "value_type": "option", "value": { "name": "P0" } }]
                    }
                  ]
                }
              ]
            }
          },
          {
            "name": "P1-高优先级",
            "condition": {
              "conjunction": "or",
              "conditions": [
                {
                  "conjunction": "and",
                  "conditions": [
                    {
                      "left_value": { "value_type": "ref", "value": "$.step_trigger.fldPriority" },
                      "operator": "is",
                      "right_value": [{ "value_type": "option", "value": { "name": "P1" } }]
                    }
                  ]
                }
              ]
            }
          },
          {
            "name": "P2-普通",
            "condition": {
              "conjunction": "or",
              "conditions": [
                {
                  "conjunction": "and",
                  "conditions": [
                    {
                      "left_value": { "value_type": "ref", "value": "$.step_trigger.fldPriority" },
                      "operator": "is",
                      "right_value": [{ "value_type": "option", "value": { "name": "P2" } }]
                    }
                  ]
                }
              ]
            }
          }
        ]
      }
    },
    {
      "id": "step_p0_handler",
      "type": "LarkMessageAction",
      "title": "P0紧急处理",
      "next": null,
      "data": {
        "receiver": [{ "value_type": "user", "value": {"id": "ou_director", "name": "总监"} }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "🚨 P0 紧急订单" }],
        "content": [{ "value_type": "text", "value": "有新的 P0 紧急订单需要立即处理" }],
        "btn_list": []
      }
    },
    {
      "id": "step_p1_handler",
      "type": "SetRecordAction",
      "title": "标记高优先级",
      "next": null,
      "data": {
        "table_name": "订单表",
        "ref_info": { "step_id": "step_trigger" },
        "field_values": [
          { "field_name": "处理状态", "value": [{ "value_type": "text", "value": "高优先级待处理" }] }
        ]
      }
    },
    {
      "id": "step_p2_handler",
      "type": "Delay",
      "title": "普通订单延迟处理",
      "next": null,
      "data": { "duration": 60 }
    },
    {
      "id": "step_other_handler",
      "type": "SetRecordAction",
      "title": "标记其他订单",
      "next": null,
      "data": {
        "table_name": "订单表",
        "ref_info": { "step_id": "step_trigger" },
        "field_values": [
          { "field_name": "处理状态", "value": [{ "value_type": "text", "value": "待分类" }] }
        ]
      }
    }
  ]
}
```

**关键点**:
- `SwitchBranch` 适合 3 路及以上的分支场景（少于 3 路用 `IfElseBranch` 更简洁）
- `children.links` 中 `kind: "case"` 的 `label` 对应 `child_branch_list` 中的条件
- `mode: "exclusive"` 表示排他执行（第一个匹配的分支执行后停止）
- `no_match_action: "classifyToOther"` 表示无匹配时走最后一个 `case`（兜底分支）

---

### 示例 5: 组合场景（定时+查找+循环+分支+消息）

**场景**: 每天早上 9 点，查找昨天的订单，按金额分级，给不同级别的销售发送不同的通知。

```json
{
  "client_token": "1704067205",
  "title": "每日订单分级通知",
  "steps": [
    {
      "id": "step_timer",
      "type": "TimerTrigger",
      "title": "每天早上9点触发",
      "next": "step_find_orders",
      "data": {
        "rule": "DAILY",
        "start_time": "2025-01-01 09:00",
        "is_never_end": true
      }
    },
    {
      "id": "step_find_orders",
      "type": "FindRecordAction",
      "title": "查找昨天所有订单",
      "next": "step_loop",
      "data": {
        "table_name": "订单表",
        "field_names": ["订单号", "客户名称", "金额", "销售负责人"],
        "should_proceed_when_no_results": false,
        "filter_info": {
          "conjunction": "and",
          "conditions": [
            { "field_name": "创建时间", "operator": "isGreaterEqual", "value": [{ "value_type": "date", "value": "yesterday" }] }
          ]
        }
      }
    },
    {
      "id": "step_loop",
      "type": "Loop",
      "title": "遍历每个订单",
      "children": {
        "links": [
          { "kind": "loop_start", "to": "step_classify" }
        ]
      },
      "next": "step_summary",
      "data": {
        "loop_mode": "continue",
        "max_loop_times": 500,
        "data": [{ "value_type": "ref", "value": "$.step_find_orders.fieldRecords" }]
      }
    },
    {
      "id": "step_classify",
      "type": "SwitchBranch",
      "title": "按金额分类",
      "children": {
        "links": [
          { "kind": "case", "to": "step_vip_notify", "label": "vip", "desc": "VIP >= 10万" },
          { "kind": "case", "to": "step_normal_notify", "label": "normal", "desc": "普通 < 10万" }
        ]
      },
      "next": null,
      "data": {
        "mode": "exclusive",
        "no_match_action": "fail",
        "child_branch_list": [
          {
            "name": "VIP订单",
            "condition": {
              "conjunction": "or",
              "conditions": [
                {
                  "conjunction": "and",
                  "conditions": [
                    {
                      "left_value": { "value_type": "ref", "value": "$.step_loop.item.fldAmount" },
                      "operator": "isGreaterEqual",
                      "right_value": [{ "value_type": "number", "value": 100000 }]
                    }
                  ]
                }
              ]
            }
          },
          {
            "name": "普通订单",
            "condition": {
              "conjunction": "or",
              "conditions": [
                {
                  "conjunction": "and",
                  "conditions": [
                    {
                      "left_value": { "value_type": "ref", "value": "$.step_loop.item.fldAmount" },
                      "operator": "isLess",
                      "right_value": [{ "value_type": "number", "value": 100000 }]
                    }
                  ]
                }
              ]
            }
          }
        ]
      }
    },
    {
      "id": "step_vip_notify",
      "type": "LarkMessageAction",
      "title": "VIP订单通知",
      "next": null,
      "data": {
        "receiver": [{ "value_type": "ref", "value": "$.step_loop.item.fldSales" }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "🌟 VIP大额订单" }],
        "content": [
          { "value_type": "text", "value": "恭喜！您有一笔 VIP 订单 ¥" },
          { "value_type": "ref", "value": "$.step_loop.item.fldAmount" },
          { "value_type": "text", "value": "，客户：" },
          { "value_type": "ref", "value": "$.step_loop.item.fldCustomer" }
        ],
        "btn_list": []
      }
    },
    {
      "id": "step_normal_notify",
      "type": "LarkMessageAction",
      "title": "普通订单通知",
      "next": null,
      "data": {
        "receiver": [{ "value_type": "ref", "value": "$.step_loop.item.fldSales" }],
        "send_to_everyone": false,
        "title": [{ "value_type": "text", "value": "新订单通知" }],
        "content": [
          { "value_type": "text", "value": "您有一笔新订单 ¥" },
          { "value_type": "ref", "value": "$.step_loop.item.fldAmount" }
        ],
        "btn_list": []
      }
    },
    {
      "id": "step_summary",
      "type": "GenerateAiTextAction",
      "title": "生成日报",
      "next": null,
      "data": {
        "prompt": [
          { "value_type": "text", "value": "请生成昨日订单处理日报" }
        ]
      }
    }
  ]
}
```

---

### 示例 6: 按钮触发 + 调用外部接口 + 写入同步日志

**场景**: 在「客户线索表」里给每条记录配置一个“同步到 CRM”按钮。销售点击按钮后，Workflow 调用外部 CRM 接口同步当前线索，再在「同步日志表」新增一条记录，方便后续审计和排查。

```json
{
  "client_token": "1704067206",
  "title": "线索一键同步到 CRM",
  "steps": [
    {
      "id": "step_button_trigger",
      "type": "ButtonTrigger",
      "title": "点击同步到 CRM 按钮时触发",
      "next": "step_call_crm_api",
      "data": {
        "button_type": "buttonField",
        "table_name": "客户线索表"
      }
    },
    {
      "id": "step_call_crm_api",
      "type": "HTTPClientAction",
      "title": "调用 CRM 同步接口",
      "next": "step_add_sync_log",
      "data": {
        "method": "POST",
        "url": [
          { "value_type": "text", "value": "https://api.example-crm.com/v1/leads/sync" }
        ],
        "headers": [
          { "key": "Content-Type", "value": [{ "value_type": "text", "value": "application/json" }] },
          { "key": "X-System", "value": [{ "value_type": "text", "value": "lark_base_workflow" }] }
        ],
        "body_type": "raw",
        "raw_body": [
          { "value_type": "text", "value": "{\"lead_name\":\"" },
          { "value_type": "ref", "value": "$.step_button_trigger.fldLeadName" },
          { "value_type": "text", "value": "\",\"mobile\":\"" },
          { "value_type": "ref", "value": "$.step_button_trigger.fldMobile" },
          { "value_type": "text", "value": "\",\"company\":\"" },
          { "value_type": "ref", "value": "$.step_button_trigger.fldCompany" },
          { "value_type": "text", "value": "\",\"owner\":\"" },
          { "value_type": "ref", "value": "$.step_button_trigger.fldOwner" },
          { "value_type": "text", "value": "\",\"source_record_id\":\"" },
          { "value_type": "ref", "value": "$.step_button_trigger.recordId" },
          { "value_type": "text", "value": "\"}" }
        ],
        "response_type": "json",
        "response_value": "{\"success\":true,\"message\":\"lead synced successfully\"}"
      }
    },
    {
      "id": "step_add_sync_log",
      "type": "AddRecordAction",
      "title": "写入同步日志",
      "next": null,
      "data": {
        "table_name": "同步日志表",
        "field_values": [
          {
            "field_name": "线索名称",
            "value": [{ "value_type": "ref", "value": "$.step_button_trigger.fldLeadName" }]
          },
          {
            "field_name": "手机号",
            "value": [{ "value_type": "ref", "value": "$.step_button_trigger.fldMobile" }]
          },
          {
            "field_name": "公司名称",
            "value": [{ "value_type": "ref", "value": "$.step_button_trigger.fldCompany" }]
          },
          {
            "field_name": "负责人",
            "value": [{ "value_type": "ref", "value": "$.step_button_trigger.fldOwner" }]
          },
          {
            "field_name": "来源记录ID",
            "value": [{ "value_type": "ref", "value": "$.step_button_trigger.recordId" }]
          },
          {
            "field_name": "同步状态",
            "value": [{ "value_type": "text", "value": "已提交 CRM 同步" }]
          },
          {
            "field_name": "同步是否成功",
            "value": [{ "value_type": "ref", "value": "$.step_call_crm_api.body.success" }]
          },
          {
            "field_name": "同步结果说明",
            "value": [{ "value_type": "ref", "value": "$.step_call_crm_api.body.message" }]
          },
          {
            "field_name": "备注",
            "value": [{ "value_type": "text", "value": "由按钮触发自动发起同步请求" }]
          }
        ]
      }
    }
  ]
}
```

**关键点**:
- `ButtonTrigger` 适合“人工确认后再执行”的场景，比如同步 CRM、推送 ERP、发起审批等
- `button_type: "buttonField"` 表示按钮挂在记录上，因此可以直接引用当前记录的字段和值
- `HTTPClientAction.raw_body` 可以通过 `text + ref + text` 的方式动态拼接 JSON 请求体
- `HTTPClientAction` 的输出引用规则是：`response_type=none` 时不可引用；`response_type=text` 时只能用 `$.stepId` 引整个文本；`response_type=json` 时用 `$.stepId.body` 引整个 body、用 `$.stepId.body.字段名` 引 body 中字段，同时 `$.stepId.status_code` 表示 HTTP 返回状态码
- `HTTPClientAction.response_value` 中声明了哪些字段，后续节点就只能引用这些字段；例如 `$.step_call_crm_api.body.success`、`$.step_call_crm_api.body.message`
- `AddRecordAction` 常用于写日志表、操作审计表、同步结果表，便于追踪谁在什么时候触发了外部调用
- 示例里的 `fldLeadName` / `fldMobile` / `fldCompany` / `fldOwner` 只是占位的 fieldId，请以实际表字段 ID 为准

---

## 构造技巧

### Loop 构造要点

1. **数据源**: `Loop.data` 必须传入 `ref` 类型，通常是 `FindRecordAction` 的 `fieldRecords`
2. **循环体**: `children.links` 必须包含 `kind: "loop_start"` 指向循环体入口
3. **引用**: 循环体内用 `$.{loopStepId}.item.{fieldId}` 引用当前元素
4. **索引**: 用 `$.{loopStepId}.index` 获取当前索引（从 0 开始）

### 分支构造要点

1. **IfElseBranch**:
   - 适合二元判断（是/否、大于/小于）
   - `children.links` 必须包含 `if_true` 和 `if_false`
   - 可以用 `next` 指向汇合点

2. **SwitchBranch**:
   - 适合多路分类（3路及以上）
   - `label` 对应 `child_branch_list` 中的条件顺序
   - 建议加一个兜底分支（其他）

### 字段值构造

| 字段类型 | value_type | 示例 |
|---------|------------|------|
| 文本 | `text` | `{"value_type": "text", "value": "张三"}` |
| 数字 | `number` | `{"value_type": "number", "value": 100}` |
| 单选 | `option` | `{"value_type": "option", "value": {"name": "已完成"}}` |
| 人员 | `user` | `{"value_type": "user", "value": {"id": "ou_xxxx"}}` |
| 引用 | `ref` | `{"value_type": "ref", "value": "$.step_1.fldxxx"}` |

---

## 常见错误避免

### Top 10 高频错误

| # | 错误信息 | 原因 | 解决方案 |
|---|---------|------|---------|
| 1 | `path "xxx" does not exist in the output path tree` | ref 引用路径错误或 stepId 不存在 | 检查 stepId 是否在 steps 数组中；使用 fieldId 而非字段名；确保路径以 `$.` 开头 |
| 2 | `recordInfo.conditions must be non-empty` | `condition_list` 为空数组 `[]` | 改用 `null` 或省略该字段 |
| 3 | `At least one of filter info and ref info is required` | SetRecordAction/FindRecordAction 缺少定位条件 | 必须提供 `filter_info` 或 `ref_info` 之一 |
| 4 | `client token is empty` | 缺少 `client_token` | 每次请求传入唯一值（时间戳或随机字符串） |
| 5 | `valueType 'text' not allowed for fieldType '3'` | select 类型字段值格式错误 | 改用 `option` 类型 |
| 6 | `Undefined Step Type` | 使用了不支持的 StepType | 使用 `AddRecordTrigger` 而非 `CreateRecordTrigger` |
| 7 | `prompt references an unknown reference from step` | 引用的 stepId 不存在 | 确保引用的 step 在同一 workflow 的 steps 数组中 |
| 8 | `[2200] Internal Error` | 1. steps[].id 重复 2. next/children.links 引用了不存在的 step | 确保所有 step id 唯一；检查引用关系 |
| 9 | 工作流结构不完整 | Branch/Loop 节点缺少 `children` | 仅 Branch（IfElseBranch/SwitchBranch）和 Loop 节点需要 `children`，Trigger/Action 节点无需设置 |
| 10 | 嵌套分支过于复杂 | 多层 IfElseBranch 嵌套 | 3+ 路分支用 SwitchBranch 替代嵌套 IfElseBranch |

### 其他常见错误

**1. condition_list 为空数组**
```json
// ❌ 错误
{ "condition_list": [] }

// ✅ 正确
{ "condition_list": null }
// 或省略该字段
```

**2. filter_info 和 ref_info 同时提供**
```json
// ❌ 错误
{ "filter_info": {...}, "ref_info": {...} }

// ✅ 正确（二选一）
{ "filter_info": {...}, "ref_info": null }
{ "filter_info": null, "ref_info": {...} }
```

**3. 使用字段名而非 fieldId**
```json
// ❌ 错误
{ "value": "$.step_1.客户名称" }

// ✅ 正确
{ "value": "$.step_1.fldXXXXXXXX" }
```

---

## 参考

- [lark-base-workflow-schema.md](lark-base-workflow-schema.md) — 字段定义参考
- 创建/更新前先确认真实表名、字段名和目标 workflow ID；`steps` 结构按 schema 构造，不凭自然语言猜 `type`
