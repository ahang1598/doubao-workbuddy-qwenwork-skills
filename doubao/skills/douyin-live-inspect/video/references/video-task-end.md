# content/+video-task-end

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-task-end' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 用户明确要求结束状态允许的视频质检任务。

## Avoid when

- 任务不是待机审状态、目标不唯一或写入结果未知时停止。

## Prerequisites

- 先用 `+video-task-get` 核对唯一 `ProjectName`、`TaskId` 和当前状态。
- 先 dry-run；首次实际执行停在 exit 10，取得明确确认后只复用原命令的一次性令牌。

## Tips

- `yes:true` 不能代替 `confirm_token`；结束结果未知时只允许后续只读查询。

## Examples

```text
node ../scripts/api.mjs --operation 'content/+video-task-end' < params.json
```
