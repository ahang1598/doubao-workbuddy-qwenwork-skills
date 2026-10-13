# quality/+project-list

先遵循 [项目与场景选择](product-boundary.md#项目与场景选择)。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+project-list' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 为本次质检查询当前账号可访问的项目；新建项目后用户要求继续时重新查询。

## Avoid when

- 已有任务续办使用原项目，不重新选择，不跨账号或环境探测。

## Prerequisites

-内置运行时能力与本次环境认证就绪。

## Tips

- 用户候选表仅展示序号、项目展示名称、创建时间和场景数量（缺失字段省略）；禁止展示任务数，即使接口返回也不输出，不额外查询任务列表补数。
- 按返回 ProjectType=2 筛选，按产品边界分页；确认结束后才判定 0/1 个项目，多个每批展示 10 个并支持下一批。
- 无项目属于配置缺失，新建检测按产品边界的回退规则转 Lite，并保留同环境控制台配置入口；仅查询时交付空列表。唯一项目自动使用；查询失败不等于无项目。

## Examples

```text
node scripts/api.mjs --operation 'quality/+project-list' < params.json
```
