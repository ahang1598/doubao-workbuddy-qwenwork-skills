# quality/+screenshot-list

先遵循 [产品边界](product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node scripts/api.mjs --operation 'quality/+screenshot-list' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->


## When

- 查询一个直播质检任务的质检截图。

## Avoid when

- 任务创建已超过 30 天时本接口不支持。

## Prerequisites

- 准备唯一 `ProjectName` 和 `TaskId`。

## Tips

- 截图 URL 有效期为 7 天；需要留存时及时下载到用户指定位置。

## Examples

```text
node scripts/api.mjs --operation 'quality/+screenshot-list' < params.json
```
