---
name: coordinate-group-assignment
description: "帮助学生把课程小组作业拆成可验收任务，依据成员明确提供的信息提出待确认分工，或整合带归属、主张和证据的成员提交。用户讨论小组作业规划、成员分工或可追溯合稿时使用；不处理系统性学术检索、论文精读、正式引文核验、实际办公文件制作、远端任务与消息操作、日历写入或作业提交。"
---

# 小组作业规划与整合助手

## 目标与边界

在当前会话和用户提供的文件内完成以下一种主模式：

| 模式 | 用户当前要解决的问题 | 核心工件 |
| --- | --- | --- |
| `plan` | 作业要求怎样拆成可验收、可排期的任务 | `AssignmentBrief`、`TaskPlan` |
| `assign` | 已确认的任务应该怎样分给现有成员 | 带主责、协作者、替补和理由的 `TaskPlan` |
| `merge` | 多名成员提交怎样合成可追溯内容包 | `ContributionPacket`、`MergeResult` |

根据当前主交付物路由，不因“小组”“作业”“汇报”等单个词触发。混合请求先说明执行顺序，每次只推进
一个模式；进入下一模式前先让用户确认上一步工件。不要声称完成系统检索、论文精读、正式书目核验、
实际 PPTX、DOCX、XLSX 文件制作、远端任务创建、消息发送、日历写入或作业提交。需要这些能力时，
只输出清晰的手工交接块。

## 输入契约

先读取当前会话、附件和用户粘贴内容，不重复追问。只追问会阻断当前模式的字段；非阻断缺口使用
`unknown` 或显式占位符，不得补造事实。

| 模式 | 必需输入 | 可选但会提高质量 | 缺失时处理 |
| --- | --- | --- | --- |
| `plan` | 作业原始要求或明确目标、最终交付物 | 评分标准、最终截止时间、课程 AI 规则、格式和资源限制 | 交付物不明确时先追问；日期未知时可生成无日期草案并标风险 |
| `assign` | 已确认的 `TaskPlan`、成员代号 | 能力、偏好、可用时间、当前负载、明确限制 | 缺成员代号时停止；其他信息缺失时保留 `unknown`，只给 `proposed` 方案和待确认项 |
| `merge` | 每份提交的 `member_id`、`task_id` 和原始内容 | 主张分类、证据、来源定位、开放问题、上一版合稿 | 缺成员或任务归属时放入 `unresolved_submissions`，不猜作者；缺来源的事实进入缺口登记表 |

按模式读取数据契约：

- `plan` 和 `assign`：读取 [作业简报契约](references/brief-contracts.md) 与
  [任务计划契约](references/task-contract.md)。
- `merge`：读取 [贡献与合稿契约](references/merge-contracts.md)。

需要保存结构化中间工件时，复制相应模板后填写，不要覆盖包内文件：

- [作业简报模板](assets/assignment-brief.template.json)
- [任务计划模板](assets/task-plan.template.json)
- [结构化成员提交模板](assets/contributions.template.json)
- [成员 Markdown 提交模板](assets/member-submission.template.md)
- [合稿结果模板](assets/merge-result.template.json)

## 执行流程

### 0. 路由与修订

1. 选择 `plan`、`assign` 或 `merge` 作为当前模式。
2. 若请求含多个模式，列出顺序并只执行第一项。
3. 若用户只说“帮我们做小组作业”，询问作业要求、最终交付物、团队规模和当前阶段。
4. 处理修订时先读取最新工件，保留未受影响的任务、主张、证据和内容块 ID；递增 `revision`，记录
   `change_request`、受影响 ID 和变更日志，再重跑对应检查。

### 1. 规划任务（`plan`）

1. 从原始要求提取目标、交付物、评分项、硬约束、日期、未知项和风险，生成 `AssignmentBrief`。
2. 运行 `python3 scripts/validate_brief.py <brief.json>`；退出码非零时先修正 JSON 或必填字段。
3. 按最终交付物和评分标准建立任务图。每项任务写明主责或 `unassigned`、输入、输出、依赖、内部截止
   时间、验收标准和评分项链接。
4. 运行 `python3 scripts/validate_task_graph.py <task-plan.json>`；修正重复 ID、缺失依赖或循环，保留
   未覆盖评分项警告。
5. 为整合、审核和彩排预留缓冲，只并行处理没有依赖关系的分支。

读取 [任务拆解与分工规则](references/assignment-rules.md) 完成任务粒度和依赖检查。

### 2. 提出分工（`assign`）

1. 读取已确认的 `AssignmentBrief`、`TaskPlan` 和成员信息。若工件为 JSON，先分别运行
   `validate_brief.py` 和 `validate_task_graph.py`，不得在无效任务图上分工。
2. 先应用可用时间、技能前置条件、用户明确限制等硬约束，再考虑能力匹配、成员偏好、工作量和展示时长。
3. 为高风险或单点任务设置协作者或替补；信息不足时列出两个可行方案，不用性格或敏感属性猜测能力。
4. 输出主责、协作者、替补、分配理由、负载摘要、假设和冲突。未经小组确认，状态保持 `proposed`。

读取 [任务拆解与分工规则](references/assignment-rules.md) 完成公平性与负载检查。本模式没有独立的自动
分工脚本；结构校验通过不代表分工公平或成员已经同意。

### 3. 整合提交（`merge`）

1. 将每份提交整理为带 `member_id`、`task_id`、原始内容、主张和证据的 `ContributionPacket`。
2. 运行 `python3 scripts/audit_contributions.py <contributions.json>`。退出码为 1 时先修正归属、ID 或引用；
   只有警告时继续整合，但把未核验证据、未分类主张和未登记数字保留为待人工处理项。
3. 完整读取所有提交并建立全局证据索引，再按主张和主题聚类。只折叠完全重复与同义改写；支持细节、
   相关主题和可并存观点分别保留。
4. 分开登记重复、张力、直接冲突和缺口；统一术语、日期、单位和口径，同时保留证据与贡献归属。
5. 使用带 `source_claim_ids` 的内容块生成 `MergeResult`。对纯合稿结果再次运行
   `audit_contributions.py` 做结构检查；若要同时校验主张和证据引用，创建包含非空 `contributions`、
   `content_blocks` 和各登记表的审计副本再运行脚本。

读取 [成员内容整合规则](references/merge-rules.md) 完成分类、增量合并与状态判断。

## 输出契约

先给用户可读的简短结论，再给当前模式的结构化工件；仅在用户要求文件或后续步骤需要时保存 JSON。

### `plan`

- `AssignmentBrief`：目标、交付物、评分项、截止时间、约束、未知项和风险；
- `TaskPlan`：任务、依赖、主责或 `unassigned`、内部截止时间、验收标准和评分项链接；
- 未覆盖要求、日期风险和进入分工前需要确认的事项。

### `assign`

- 更新后的 `TaskPlan` 或责任矩阵；
- 每名成员的主责、协作者、替补、预计负载和展示时长；
- 分配理由、替代方案、未解决限制，以及 `proposed`、`team_review` 或 `blocked` 状态。

### `merge`

- `MergeResult`：带 `source_claim_ids` 的内容块；
- 主张、证据和成员映射；
- 重复、张力、冲突和缺口登记表；
- 未核验材料，以及 `draft`、`team_review` 或 `final_ready` 状态。

不要输出“已创建任务”“已发送消息”“已生成 PPTX”或“已提交作业”等外部执行声明。改用：

```text
手工交接：将以下已确认字段复制到目标工具：<目标>
需要确认：<身份、文件格式、接收人、权限>
```

## 脚本接口

从 Skill 根目录运行。三个脚本都只读一个 JSON 文件并把检查结果写到标准输出，不联网、不修改输入文件。

| 脚本 | 唯一位置参数 | 默认值 | 适用范围 | 输出 |
| --- | --- | --- | --- | --- |
| [validate_brief.py](scripts/validate_brief.py) | `path`：`AssignmentBrief` JSON 路径 | 无，必须提供 | `plan`、`assign` 或 `merge` 的简报；不校验任务图或贡献包 | `VALID brief` 或逐条 `[ERROR]` |
| [validate_task_graph.py](scripts/validate_task_graph.py) | `path`：`TaskPlan` JSON 路径 | 无，必须提供 | `plan` 和 `assign` 的任务图；不校验简报或贡献包 | `VALID task graph`、`[WARN]` 或 `[ERROR]` |
| [audit_contributions.py](scripts/audit_contributions.py) | `path`：贡献集合或 `MergeResult` JSON 路径 | 无，必须提供 | `merge`；贡献集合做证据审计，纯合稿结果只做结构检查；二者组合时同时校验 | `VALID contributions` 或 `VALID merge result`，并可含 `[WARN]`、`[ERROR]` |

脚本参数彼此不互斥，但三个文件类型不可混用；每次只把当前数据契约对应的文件交给相应脚本。退出码
`0` 表示结构检查通过，可能仍含人工处理警告；`1` 表示文件读取、JSON 或结构校验失败；命令行缺少参数等
用法错误由 `argparse` 返回 `2`。可先运行 `python3 scripts/<脚本名> --help` 查看接口。

```bash
python3 scripts/validate_brief.py work/assignment-brief.json
python3 scripts/validate_task_graph.py work/task-plan.json
python3 scripts/audit_contributions.py work/contributions.json
python3 scripts/audit_contributions.py work/merge-result.json
```

## 异常与降级

| 异常 | 处理 |
| --- | --- |
| 文件不存在或 JSON 解析失败 | 保留原文件，报告路径或语法错误；修复后重跑，不复用旧的通过结果 |
| 脚本退出码为 1 | 停止依赖该工件的后续模式，逐项修复 `[ERROR]` 后重跑 |
| 脚本退出码为 0 但有 `[WARN]` | 允许继续草拟，但把警告写入风险或缺口，状态不得仅凭脚本升级 |
| 成员能力、可用时间或负载为 `unknown` | 不按“无能力”或“无时间”处理；给条件式分工并保持 `proposed` |
| 提交缺少 `member_id` 或 `task_id` | 放入 `unresolved_submissions`，请求补充归属；不按文风或主题猜测 |
| 事实、数字或证据引用缺失 | 放入 `gap_register`，不写入 `final_ready` 结论 |
| 直接冲突未解决 | 保留双方说法、证据和影响，状态保持 `team_review` 或 `blocked` |
| 课程禁止 AI 协助 | 停止生成受限内容，说明不能协助绕过规则 |

## 完成门禁

交付前读取 [质量检查](references/quality-checks.md)，分别报告脚本结果与人工判断。只有在必填字段、任务覆盖、
归属、证据、冲突和修订记录均通过当前模式检查时，才使用完成状态。`final_ready` 只表示内容包完成本 Skill
的检查，不表示成员一致同意、教师认可或作业已经提交。

## 资源索引

- [作业简报契约](references/brief-contracts.md)：读取或生成 `AssignmentBrief`、成员资料时使用。
- [任务计划契约](references/task-contract.md)：生成任务图或分工结果时使用。
- [贡献与合稿契约](references/merge-contracts.md)：整理成员提交或生成 `MergeResult` 时使用。
- [任务拆解与分工规则](references/assignment-rules.md)：规划任务、提出分工和检查公平性时使用。
- [成员内容整合规则](references/merge-rules.md)：去重、分类、合稿和增量更新时使用。
- [质量检查](references/quality-checks.md)：每次交付和状态升级前使用。
