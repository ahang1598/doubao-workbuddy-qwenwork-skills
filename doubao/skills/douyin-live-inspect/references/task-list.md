# quality/+task-list

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+task-list' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

`TaskType=2` 自动填充，日期过滤按本地自然日规范化。

## When

- 按项目、名称、状态、场景、活动或日期查找直播质检任务。

## Avoid when

- 不用于列出普通直播间或视频审核任务。

## Prerequisites

- 准备唯一 `ProjectName`；状态值只使用 Schema 枚举。

## Tips

- 分页由 Agent 编排：读取 Schema 中的 `page_number`、`page_size` 等实际字段，逐页通过 JSON stdin 请求；依据实际总数／页数或空页停止，去重并遵守服务限流。不使用未支持的 `--page-all` 或 `--page-delay` 参数。

## Examples

```text
node scripts/api.mjs --operation 'quality/+task-list' < params.json
```
