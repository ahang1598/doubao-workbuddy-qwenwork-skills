# content/+video-scenario-list

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-scenario-list' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 为视频质检任务解析已有审核场景。

## Avoid when

- 不用于直播质检场景，也不创建或修改场景。

## Prerequisites

- 准备唯一的视频质检 `ProjectName`。

## Tips

- 使用候选序号、场景名称、描述及可用规则数供选择；内部 `ScenarioId` 仅保留在执行上下文，不展示或要求输入。选择流程见下方权威链接。

## Examples

```text
node ../scripts/api.mjs --operation 'content/+video-scenario-list' < params.json
```

按 [项目与场景选择](../../references/product-boundary.md#项目与场景选择) 展示所选项目内全部视频场景。唯一场景自动使用，多个每批 10 个供选择并支持下一批；同名按序号和描述消歧。无场景属于配置缺失，新建检测按产品边界的回退规则转 Lite，并保留控制台配置入口；禁止复用直播场景编号。
