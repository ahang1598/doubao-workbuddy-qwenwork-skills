# content/+video-scenario-get

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-scenario-get' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 查看单个视频质检场景及其规则信息。

## Avoid when

- `ScenarioId` 未确定时先查询列表，不按名称相似度猜测。

## Prerequisites

- 准备唯一 `ProjectName` 和 `ScenarioId`。

## Tips

- 只解释接口返回的规则，不补造未返回的判断逻辑。

## Examples

```text
node ../scripts/api.mjs --operation 'content/+video-scenario-get' < params.json
```
