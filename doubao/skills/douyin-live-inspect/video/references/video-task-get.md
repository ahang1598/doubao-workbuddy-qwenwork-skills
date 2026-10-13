# content/+video-task-get

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-task-get' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 核对视频质检任务详情、状态或后续操作前置条件。

## Avoid when

- `TaskId` 未确定时先查询任务列表。

## Prerequisites

- 准备唯一 `ProjectName` 和 `TaskId`。

## Tips

- 状态未完成时不要把缺少报告解释为审核通过。

## Examples

```text
node ../scripts/api.mjs --operation 'content/+video-task-get' < params.json
```
