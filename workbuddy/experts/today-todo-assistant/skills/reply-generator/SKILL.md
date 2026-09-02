---
name: reply-generator
description: "AI 生成建议回复。基于留言内容 + 上下文 + 风险等级，调用用户在 WorkBuddy 中选择的模型生成建议回复。project 类型用「评论+项目信息+该项目最近5条进展（无进展则仅项目信息）」，process 类型用「评论+进展信息+所属项目信息」综合生成。高风险留言需引用项目公开信息，无上下文时生成核查中口径。多条留言分组批量生成（一次调用产出一组）+ 组间并行。"
---

# AI 建议回复生成

> **⚠️ 已内联**：本 Skill 的生成规则（策略表、事实使用规则、长度约束、分组并行）已内联进 `agents/comment-assistant.md` 的 Phase 2，运行时**不再加载本 Skill**（减少一轮 Skill 加载交互，并避免命名空间加载失败回退）。本文档及 `references/prompt-templates/` 仅作 Prompt 模板与示例的参考存档；若两处规则冲突，以 agent 主文档 Phase 2 为准。

## 概述

本 Skill 负责为待回复留言生成 AI 建议回复，是留言回复流程的核心环节。

**核心功能**：
- 基于留言内容 + 上下文 + 风险等级生成建议回复
- **上下文组合按类型区分**：project 类型 = 评论 + 项目信息（project_detail）+ 该项目最近 5 条进展（process_list，无进展为空数组）；process 类型 = 评论 + 进展信息（process_detail）+ 所属项目信息（project_detail）
- 调用用户在 WorkBuddy 中选择的模型（非 Agent 内置）
- 支持高风险/无风险两种生成策略

**关键约束**：
- 输出长度 < 256 个 Unicode 字符（严格小于 256，按 Unicode 字符数计算而非字节数；与批量回复接口限制一致）
- 高风险：不出现无来源的具体事实
- 无上下文：不出现具体金额/日期/人数/比例/承诺
- AI 生成内容仅供参考，不直接作为最终回复
- 所有具体事实必须来自与当前留言关联且已发布的数据，并逐项记录来源（见「事实使用规则」）

## 触发场景

Agent 在 Phase 4（AI 生成建议回复）时加载本 Skill。

## 输入格式

```json
{
  "comment": {
    "comment_id": 123456789,
    "content": "钱都去哪了？一直没看到进展更新，是不是骗人的？",
    "object_type": "project",
    "object_id": "224328",
    "project_name": "春蕾计划她们想上学",
    "nick_name": "爱心网友A",
    "created_at": 1756000000,
    "risk_audit_status": 4,
    "risk_audit_reason": "质疑资金去向"
  },
  "context": {
    "type": "project",
    "project_detail": {
      "project_name": "春蕾计划她们想上学",
      "project_intro": "...",
      "closing_date": "2026-12-31",
      "fundras_filing_code": "..."
    },
    "process_list": [
      {
        "id": 1001,
        "content_title": "2026年7月进展报告",
        "desc": "本月完成...",
        "publish_time": 1786000000
      }
    ]
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `comment` | object | 是 | 留言数据 |
| `comment.comment_id` | uint64 | 是 | 评论 ID |
| `comment.content` | string | 是 | 留言内容 |
| `comment.object_type` | string | 是 | 对象类型：`project` / `process` |
| `comment.object_id` | string | 是 | 对象 ID |
| `comment.project_name` | string | 是 | 项目名称 |
| `comment.nick_name` | string | 是 | 用户昵称（与 proto 字段名一致） |
| `comment.risk_audit_status` | uint32 | 是 | 风控状态：4-AI拦截 即高风险，其他为无风险（与 proto 字段名一致） |
| `comment.risk_audit_reason` | string | 否 | 风控拦截原因（risk_audit_status=4 时必填，与 proto 字段名一致） |
| `context` | object | 否 | 上下文数据 |
| `context.type` | string | 是 | 上下文类型：`project` / `process` |
| `context.project_detail` | object | 否 | 项目详情：type=project 时为该项目详情；type=process 时为进展所属项目详情 |
| `context.process_list` | array | 否 | 该项目最近 5 条进展（type=project 时，最多 5 条；无进展/拉取失败时为空数组，仅用 project_detail 生成） |
| `context.process_detail` | object | 否 | 进展详情（type=process 时） |

## 工作流程

1. **策略选择**：根据 `risk_audit_status`（=4 为高风险）和 `context` 是否存在，为每条留言选择生成策略
2. **项目匹配校验**：校验 `context` 来源与当前留言 `object_id` 一致；不一致或路由无法确认时，按"无上下文"策略降级为"核查中"口径，且不得使用该 context 的任何数据
3. **分组**：将留言列表按 ≤20 条/组 分组（同组内策略可以不同，Prompt 中逐条标注风险等级与有无上下文）
4. **批量 Prompt 组装**：每组组装一个批量 Prompt，要求模型一次输出该组全部留言的建议回复（JSON 数组，元素含 comment_id + ai_suggestion + sources）
5. **并行模型调用**：各组**并行发起**模型调用（禁止逐条/逐组串行）；运行环境不支持并行时至少保证批量生成，不得退化为单条单次调用
6. **事实来源记录**：回复中每引用一项具体事实，记录其来源类型/对象标识/更新时间到 `sources`
7. **长度校验**：每条输出 < 256 个 Unicode 字符（按字符数计，含标点与 emoji），超长时截断
8. **返回结果**：汇总各组结果，返回全部建议回复及事实来源记录

**性能约定**：
- 单条留言生成耗时可秒级，逐条串行不可接受，**必须**分组批量 + 并行
- 推荐组大小 20 条（组太大易超模型输出长度限制、单条质量下降；组太小并行收益低）
- 某组调用失败时仅该组重试或置空 `ai_suggestion`，不影响其他组

## 生成策略

| 场景 | 输入组合 | 生成策略 |
|------|---------|---------|
| 高风险 + project 有上下文 | comment.content + comment.risk_audit_reason + project_detail + process_list（该项目最近 5 条进展，无进展为空数组） | 语气以说明事实、回应问题、明确后续为主，仅引用 project_detail 与 process_list 中真实存在的字段值（进展引用逐条对应 id），并逐项记录 `sources` |
| 高风险 + process 有上下文 | comment.content + comment.risk_audit_reason + process_detail + project_detail（所属项目） | 综合进展内容与所属项目信息回应，仅引用两者中真实存在的字段值，逐项记录 `sources` |
| 高风险 + 无上下文 | comment.content + comment.risk_audit_reason | "核查中"口径，不出现具体金额/日期/人数/承诺 |
| 无风险 + project 有上下文 | comment.content + project_detail + process_list（该项目最近 5 条进展，无进展为空数组） | 简洁回复，仅引用 project_detail 与 process_list 中真实存在的字段值（进展引用逐条对应 id），并逐项记录 `sources` |
| 无风险 + process 有上下文 | comment.content + process_detail + project_detail（所属项目） | 简洁回复，综合进展内容与所属项目信息，仅引用真实存在的字段值，逐项记录 `sources` |
| 无风险 + 无上下文 | comment.content | 简洁回复，"核查中"口径 |
| 任意风险 + 项目不匹配 | context 来源与留言 object_id 不一致或路由无法确认 | 等同"无上下文"处理：不使用该来源，"核查中"口径 |

> **project 上下文组合**：项目（project）类型评论的「有上下文」= `project_detail`（项目信息）+ `process_list`（该项目最近 5 条进展，由 `get_process_list` 拉取）。`process_list` 为空数组（无进展或拉取失败）时仅用 `project_detail` 生成；`project_detail` 缺失时按"无上下文"处理。
>
> **process 上下文组合**：进展（process）类型评论的「有上下文」= `process_detail`（该条进展）+ `project_detail`（该进展所属项目，由评论自带 `project_id` 拉取）。两者任一缺失时按已有部分生成，均缺失则按"无上下文"处理。

## 事实使用规则（产品规则 4.1，必须遵守）

| 规则项 | 处理要求 |
|--------|---------|
| 具体事实 | 金额、日期、人数、地区、进度比例、凭证状态、地址、联系方式、完成时点等，只能来自**与当前留言关联且已发布**的数据（即输入 `context` 中真实存在的字段值，禁止凭常识/示例补写） |
| 来源记录 | 每项具体事实必须记录来源类型、来源对象标识和来源更新时间，填入输出 `sources` 数组，供校验与审计；无事实引用时 `sources` 为空数组 |
| 信息缺失 | 缺少可引用事实时，只确认已收到问题并说明后续核查或查看路径（如"可在项目进展页查看"），不补写具体数值或时点 |
| 项目不匹配 | 项目路由无法确认（`object_id` 与 `context` 来源不一致或 context 缺失）时，不使用该来源，草稿进入"核查中"口径 |
| 公开口径 | 只使用平台能够返回且机构当前有权使用的已发布内容；内部草稿和 Demo 示例数据不进入生产回复 |
| 承诺表述 | 只有上下文数据中明确存在相应计划或时点时，才使用"将在某日更新/完成"等承诺性表述；否则只能说"会持续同步进展"类非承诺口径 |

## 输出格式

```json
{
  "comment_id": 123456789,
  "ai_suggestion": "您好，感谢您的关注和监督！「春蕾计划她们想上学」项目正在按备案计划执行（募捐备案号：XXX），最新执行情况会在项目进展页持续公示，欢迎您随时查看。",
  "sources": [
    {
      "fact": "募捐备案号：XXX",
      "source_type": "project_detail",
      "source_id": "224328",
      "updated_at": "2026-08-01T00:00:00+08:00"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `comment_id` | uint64 | 评论 ID（与输入一致，用于关联挂载） |
| `ai_suggestion` | string | AI 生成的建议回复（1~255 个 Unicode 字符，即严格 < 256），生成失败时为空串 |
| `sources` | array | 事实来源记录，每项含 `fact`（引用的事实原文）、`source_type`（来源类型：project_detail 项目详情 / process_detail 进展详情 / process_list 项目最近进展列表，此时 `source_id` 填所引用进展条目的 id）、`source_id`（来源对象标识）、`updated_at`（来源更新时间）；无事实引用时为空数组。**仅供 Agent 内部校验与审计，不进入 UI 协议**——comment-task-manager 组装展示数据时不得将 `sources` 挂载到 list 元素 |

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| 模型调用失败 | `ai_suggestion` 返回空串 |
| 输出超长 | 截断至 255 个 Unicode 字符以内（严格 < 256） |
| 无上下文 | 使用"核查中"口径生成 |

## 依赖

- 用户在 WorkBuddy 中选择的模型（非 Agent 内置）

## 参考文档

- [high-risk.md](references/prompt-templates/high-risk.md)
- [no-risk.md](references/prompt-templates/no-risk.md)
