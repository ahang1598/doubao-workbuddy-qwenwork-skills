# AI 大模型专家团 1.1.1

五人专家团通过 AI-HIVE 的 100+ 顶尖模型能力，完成策划、实时选型、经确认的生成、技术质检和整合交付。

## 团队

| Agent | 职责 |
|---|---|
| 王总监 | 建团队、调度、用户确认、整合交付 |
| 郝策划 | 事实与素材台账、创意、Prompt |
| 惠选模 | 实时模型、路由、价格和首选 |
| 包落地 | 只执行已确认调用并跟踪原任务 |
| 严质检 | Prompt、状态、结果 URL 和元数据 QA |

## 五个业务阶段

Phase 0 仅检查 Connector 使用时机，不计入阶段数。

1. 需求策划。
2. 实时选型。
3. 用户确认与执行。
4. 技术质检与用户视觉验收。
5. 整合交付。

## Seedance 2.5 PE

- 由 Lead 在当前对话第一次使用时询问单一最佳版或 A/B 对照版。
- Planner 记录 `taskType`、`peMode`、事实台账、素材职责、未采用素材和 Prompt。
- Scout 不修改 Prompt；Executor 只执行用户选定版本。
- A/B 默认只输出两个 Prompt；真实双跑需要确认两次调用的总预估费用。

## 付费与 QA

- 每个新付费任务都要重新展示模型、路由、参数和价格并获得确认。
- `PENDING`、`SUBMITTED`、`PROCESSING` 只查询原 `taskId`。
- `FAILED` 展示 `failure.code`、`failure.summary`、`failure.suggestion`。
- 没有媒体预览能力时，QA 不声称看过画面或声音，交付标记“待用户视觉验收”。

## Connector 依赖

- 需要 Connector 在运行时实际暴露 `@infimind-next/ai-hive-mcp` 0.2.5 工具契约；不按 Connector 展示版本猜测字段。
- 音频参考要求 `generate_video` schema 包含 `audioMediaIds`，否则停止音频执行并提示更新 Connector。
- 具体可用模型、路由、价格和参数以实时 `list_models` 为准；100+ 为平台整体营销能力表达。

## 目录

```text
ai-expert-studio/
├── .codebuddy-plugin/plugin.json
├── settings.json
├── agents/                         # Lead + 4 位成员
├── skills/
│   ├── ai-expert-studio-orchestrator/
│   │   └── references/             # 团队与 Seedance 2.5 PE 资料
│   ├── image-creator/
│   ├── text-creator/
│   ├── video-creator/
│   ├── user-onboarding/
│   └── references/                 # 共享 Connector 契约
├── avatars/
```
