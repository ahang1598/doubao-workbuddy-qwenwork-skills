# 正式版调用埋点

事件 Key 统一维护在 `runtime/telemetry-events.json`；脚本引用 `EVENTS.formal`，服务操作使用 `EVENTS.operations` 映射。通过 `runCommand` 包装业务，公共 SDK 入口负责发送。用法见 [统一埋点接口](telemetry.md)。本次精简只影响 Lite，正式版动作与统计口径保持原样。

正式版由当前 Skill 内的 `runtime/operations.mjs` 直接调用线上 OpenAPI，并在每次实际操作边界记录一次 `cli_command_executed`。复盘、轮询等外层脚本把记录责任交给实际操作，避免同一次请求重复记录；不同轮询仍是不同调用。无需安装任何外部控播命令。

| 维度 | 字段 | 规则 |
| --- | --- | --- |
| 版本 | skill_version | 主 SKILL.md 的 metadata.version |
| 版本类型 | extra.inspection_mode | formal |
| 功能 | extra.feature | 创建为 live_inspection / video_inspection / video_batch；报告和截图为 quality_report；其他质检查询为 task_management；复盘准备请求为 live_recap |
| 流程 | extra.workflow_kind | quality 为 live；视频为 video_single；显式批量视频为 video_batch |
| 行业 | extra.scenario_category | ecommerce / finance / automotive / other / unknown |

同时保留 product=douyin-live-inspect、schema_version=2、record_type=command。时间、调用标识、结果、宿主、设备标识和合法的操作者信息沿用上游 SDK 合同。账号只来自本次业务实际读取的独立账号凭证，多账号冲突时不归因；不读取其他产品的账号缓存。

`BYTEDLIVE_INSPECT_SCENARIO_CATEGORY`、`BYTEDLIVE_INSPECT_WORKFLOW_KIND`、`BYTEDLIVE_INSPECT_FEATURE` 只传已核验枚举，不传请求正文、路径、媒体、规则原文或凭证。复盘准备的内部请求继承 live_recap。每次任务重新设置上下文，不根据项目名或任务 ID 猜测、不增加额外查询。

`BYTEDLIVE_TELEMETRY_DISABLED=1|true`、Schema、help、dry-run 和确认计划不计入使用。SDK 失败不阻断业务，不重放写入。调用成功不等于任务完成；正式版不凭空补发远端任务生命周期事件。
