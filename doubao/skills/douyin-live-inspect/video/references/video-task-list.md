# content/+video-task-list

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-task-list' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 按项目、场景、时间、状态或任务名筛选视频质检任务。

## Avoid when

- 已有唯一 `TaskId` 时优先使用任务详情。

## Prerequisites

- 准备唯一的视频质检 `ProjectName`；时间范围必须有效。

## Tips

- 名称匹配不唯一时展示稳定 `TaskId` 候选，不按返回顺序选择。

## Examples

```text
node ../scripts/api.mjs --operation 'content/+video-task-list' < params.json
```
