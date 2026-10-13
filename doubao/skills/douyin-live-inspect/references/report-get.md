# quality/+report-get

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+report-get' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->


## When

- 读取单个质检任务的报告和分析结果。

## Avoid when

- 任务未结束或报告仍在生成时不要把空结果解释为无风险。
- 已确认任务结束后，报告接口返回 `ReportNotFoundError`、空结果或仍在生成时，不立即重试。

## Prerequisites

- 准备唯一 `ProjectName` 和 `TaskId`，必要时先查询任务状态。

## 豆包工作交付（优先执行）

按 [豆包工作交付](doubao-delivery.md#直播与视频质检远端报告) 读取、核验并交付本次质检报告。直播复盘统一进入 [默认收尾入口](ecommerce-review.md#默认收尾入口)。

## Tips

- 执行前恢复 [原任务上下文](auth-recovery.md#原账号与任务绑定)，先查询任务状态；检测中不读取空报告作为通过依据。
- 状态与报告读取错误按 [服务端报告读取约束](doubao-delivery.md#服务端报告读取约束) 区分；报告等待按 [任务结束监听](task-completion-watch.md#返回结果与复盘接续) 的有界规则处理，单次查询不自动循环。
- 监听已有 `review_preparation` 时直接复用；独立复盘的准备、分析与 finalize 只按 [内容复盘](ecommerce-review.md) 执行。

## Examples

从主 Skill 根目录执行，业务参数仅通过 stdin。下面是虚构身份的离线参数校验；实际执行必须使用可信原任务身份并移除 `dry_run`。

```bash
printf '%s\n' '{"environment":"online","profile":"example","account_id":"123","project_name":"example-project","task_id":42,"dry_run":true}' | node scripts/api.mjs --operation 'quality/+report-get'
```

准备与收尾示例见 [内容复盘](ecommerce-review.md#默认收尾入口)，已上传复盘读取见 [获取复盘 JSON](ecommerce-review/manual.md#按项目与任务获取复盘-json)。
