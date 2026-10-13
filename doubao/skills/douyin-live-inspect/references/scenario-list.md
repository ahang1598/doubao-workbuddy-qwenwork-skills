# quality/+scenario-list

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+scenario-list' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

`ScenarioType=2` 由内置运行时自动填充。

## When

- 查询所选项目实际配置的全部直播场景，按产品边界分页并选择。

## Avoid when

- 项目尚未确定时先选择项目；不把直播场景 ID 用于视频任务。

## Prerequisites

- 已确定本次账号、环境与可访问的直播项目。

## Tips

- 无场景属于配置缺失，新建检测按产品边界的回退规则转 Lite，并保留控制台配置入口，唯一场景自动使用，多个场景每批 10 个并支持下一批。
- 场景接口不返回 TaskCount，不为补字段遍历任务列表，不编造任务数。
- 创建前查询所选场景详情并使用整套规则；同名场景按候选序号和描述消歧，不展示内部 ID。

## Examples

`node scripts/api.mjs --operation 'quality/+scenario-list' < params.json`。
