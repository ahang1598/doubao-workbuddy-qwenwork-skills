# quality/+task-get

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+task-get' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->


## When

- 已知任务 ID，需要查询质检任务详情或状态。

## Avoid when

- 只有任务名称且不唯一时先调用任务列表。

## Prerequisites

- 准备唯一 `ProjectName` 和 `TaskId`。

## Tips

- 报告为空或准备结束任务前，先用本命令核对任务状态。
- 底层任务状态只用于内部判断；用户可见映射为：1“等待检测”、2“检测中”、3/4“检测已完成”、5“检测失败”，未知值为“状态同步中”。不得输出“机审”“人审”“待人审”或数字枚举。

## Examples

```text
node scripts/api.mjs --operation 'quality/+task-get' < params.json
```
