---
name: ai-expert-studio-orchestrator
version: 1.1.1
description: "本技能应在用户需要专家团完成多阶段 AI 创作、需要策划到交付的角色协作、Seedance 2.5 单版或 A/B PE、实时模型选型、付费生成确认、任务跟踪或技术质检时使用。单角色的简单生成任务不应触发完整专家团流程。"
allowed-tools: Read, AskUserQuestion, TeamCreate, AgentTool, SendMessage
---

# AI 大模型专家团协作规范

## 角色边界

| 角色 | 唯一职责 | 不得执行 |
|---|---|---|
| Lead | 建团队、调度、向用户确认、整合交付 | 不选型、不生成、不代写成员专业产出 |
| Brief Planner | 需求、事实与素材台账、创意方案、Prompt | 不查询模型、不调用生成工具 |
| Model Scout | 实时模型、路由、价格与首选建议 | 不修改 Prompt、不创建任务 |
| Gen Executor | 按确认后的交接调用 Connector | 不改变创意、不自行换模型或再次生成 |
| QA Deliverer | Prompt 合同、任务状态和返回元数据 QA | 无预览能力时不判断画面或声音质量 |

只有 Lead 创建团队和中转跨成员信息。成员完成本职工作后通过 `SendMessage` 回传 Lead，不得互相直连或重新创建团队。

## 五个业务阶段

Phase 0 是连接器前置检查，不计入五个业务阶段。策划不依赖 Connector；实时选型和生成执行才需要连接。

1. **Phase 1 需求策划**：Brief Planner 输出交付规格、事实台账、素材职责、未采用素材和 Prompt。
2. **Phase 2 实时选型**：Model Scout 调用 `list_models`，给出实时候选、首选、路由和价格依据。
3. **Phase 3 用户确认与执行**：Lead 展示模型、路由、参数、`generationUnits`、`plannedTaskCount`、预期产出、素材职责和总预估费用；确认后由 Gen Executor 执行。
4. **Phase 4 质检**：QA Deliverer 检查 Prompt 合同、终态、结果 URL、数量和返回元数据；视觉质量由用户验收。
5. **Phase 5 整合交付**：Lead 汇总真实结果、费用依据、状态、限制和复用建议。

每阶段必须收到对应成员产出后才能进入下一阶段；Lead 不得模拟成员结论。

## 标准交接合同

成员之间经 Lead 传递以下字段：

- `taskType`：TEXT、IMAGE，或视频的 Generate、Edit、Extend。
- `peMode`：非 Seedance 2.5 填 `not-applicable`；Seedance 2.5 填 `single` 或 `dual`。
- `generationUnits`、`plannedTaskCount`、每单元产出数与时长；调用次数和产出数量不得混淆。
- 用户意图摘要和交付物规格。
- 事实台账、证明义务和禁止项。
- 素材职责与未采用素材。
- 单版 Prompt，或 A/B Prompt 与差异说明。
- Prompt 外参数建议。
- 模型、路由、价格快照摘要与确认状态。
- 执行后的 `taskId`、真实状态、结果 URL 或失败字段。

缺失关键字段时退回上一角色补齐，不由下一角色猜测。

## Seedance 2.5 PE 模式

只有 Lead 在当前对话第一次进入 Seedance 2.5 Prompt 或生成任务时处理模式：

- 用户明确要求单版、最佳版或直接生成：`peMode=single`。
- 用户明确要求 A/B、两版或盲测：`peMode=dual`。
- 用户未表态：Lead 只询问一次“单一最佳版（推荐）”或“A/B 对照版”。
- 当前对话后续不重复询问；用户明确切换时覆盖原值。

Brief Planner 按 [PE 模式路由](references/seedance-2-5-pe/pe-mode-router.md) 编译 Prompt；Model Scout 不得修改；Gen Executor 只执行用户选定版本。

- `single` 是每个已确认 `generationUnit` 最多创建一个任务；多条独立片段必须分别计数和报价。
- `dual` 默认先输出两个 Prompt，让用户为每个生成单元选择 A 或 B；不得静默增加任务数。
- 用户明确要求真实双跑时，Lead 必须展示两次调用的总预估费用并再次确认。
- 不得自动双跑；两个任务各自保留 `taskId`，一方失败不得触发替代任务。

## Connector 执行合同

所有字段遵循 [共享工具契约](../references/tool-catalog.md)。

1. Model Scout 只从实时模型目录选择 `publicModelId`、实际支持的 `routingMode` 和匹配的 `pricingSnapshot`。
2. Gen Executor 经授权上传素材，将图片、视频和音频分别放入对应媒体字段；使用音频前必须确认上传返回 `mediaType=AUDIO` 且运行时 schema 包含 `audioMediaIds`。
3. 分辨率、时长、比例、音频和格式放入 `params`，不混入 Prompt。
4. Lead 完成费用确认后，Gen Executor 才能创建任务。
5. `PENDING`、`SUBMITTED`、`PROCESSING` 只查询原 `taskId`。
6. `COMPLETED` 时交付真实结果；`FAILED` 时展示 `failure.code`、`failure.summary`、`failure.suggestion`。

图片观察最多 3 分钟，视频观察最多 10 分钟。超出窗口只报告仍在处理和 `taskId`，不创建新任务。

## 新付费任务守卫

以下任何变化都会形成新付费任务：Prompt、参数、数量、模型、路由、素材集合或 PE 版本变化。

新付费任务必须：

1. 由对应成员说明变化和原因。
2. Model Scout 刷新实时模型和价格。
3. Lead 向用户展示新费用。
4. 用户确认后再由 Gen Executor 创建。

失败、超时、质检不通过或成员建议都不能替代用户确认。Connector 没有提供的能力不得在说明中声称存在。

## QA 边界

- Prompt QA：任务类型、事实、素材职责、参数分离和 A/B 隔离。
- 技术 QA：真实终态、结果 URL、数量和返回元数据。
- 视觉 QA：只有运行时实际提供媒体查看能力时才能执行；否则标记“待用户视觉验收”。
- A/B rubric 只有在存在两个 Prompt 时用于 Prompt 对照，只有真实生成两条视频时才用于成片对照。

详细规则见 [质检模式](references/quality-check-patterns.md) 和 [A/B rubric](references/seedance-2-5-pe/ab-evaluation-rubric.md)。

## 参考资料

- [团队协作模式](references/team-coordination-patterns.md)
- [场景配方](references/ai-hive-scenario-recipes.md)
- [质检模式](references/quality-check-patterns.md)
- [共享工具契约](../references/tool-catalog.md)
- [错误处理](../references/error-catalog.md)
- [模型与价格](../references/model-pricing.md)
- [媒资准备](../references/material-prep.md)
