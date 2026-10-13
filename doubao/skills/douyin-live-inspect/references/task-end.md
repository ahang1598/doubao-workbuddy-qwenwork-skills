# quality/+task-end

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+task-end' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->


## When

- 用户明确要求提前结束一个仍在运行的直播质检任务。

## Avoid when

- 目标任务不唯一、已结束或用户只是要结束直播间时不要执行。

## Prerequisites

- 先查询并核对唯一 `ProjectName`、`TaskId` 和当前任务状态。
- 首次执行必须停在 exit 10，获得明确确认后仅复用同一命令返回的一次性令牌。
- 远端工作台使用控制台登录与自身结束保护，不走内置运行时的本地通知或 exit 10 协议。对话结束任务仍遵循内置运行时的确认门禁。
- 对话确认使用：`是否结束质检任务“<任务名称>”？结束后将停止采集新的质检内容，但不会结束抖音直播。` 正常情况下不显示任务编号、内部状态或确认令牌；只有同名任务消歧或用户明确索要时才补充编号。

## Tips

- `yes:true` 不能代替 `confirm_token`；未知网络结果不得重放。
- 实际 `EndTask` 明确返回成功（`Result.Status=true`）后，远端操作台通过自身轮询同步，不调用本地通知，不启动或恢复本地工作台；继续原任务的只读查询和远端报告交付，绝不重发结束请求。
- 结束成功不是最终交付；复用当前 [结束监听](task-completion-watch.md) 观察真实终态，按其返回结果继续报告及复盘。监听、报告预算和断点状态均由该文档维护，不重新创建、不重发结束请求。
- 操作台仅查询已生成复盘，不执行模型分析、不唤醒 Agent。进度按真实结果表达，不承诺固定完成时间；最终回复与中断说明遵循 [交付](doubao-delivery.md)。

## Examples

```text
node scripts/api.mjs --operation 'quality/+task-end' < params.json
```

## 显式确认计划

优先使用 `plan:true` 获取 exit 10 的确认计划；它不调用 EndTask。`plan:true` 不能与 `dry_run:true` 或 `confirm_token` 同用。用户确认后移除 `plan:true`，复用同一任务参数及令牌执行一次。纯 dry-run 不签发令牌。这些字段通过 JSON stdin 提交，按精确 Schema 使用；认证、网络或业务错误不得触发回退。
