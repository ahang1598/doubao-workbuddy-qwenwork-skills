# quality/+scenario-get

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+scenario-get' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->


## When

- 已知项目和场景 ID，需要查看场景规则详情。

## Avoid when

- 只有场景名称且无法唯一解析 ID 时先调用场景列表。

## Prerequisites

- 准备唯一 `ProjectName` 和 `ScenarioId`。

## Tips

- 场景详情用于解释规则，不自动修改场景配置。

## Examples

```text
node scripts/api.mjs --operation 'quality/+scenario-get' < params.json
```
