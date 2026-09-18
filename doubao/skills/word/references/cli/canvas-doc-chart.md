# 本地 Word 图表

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

## 前置读取

- 读取前先加载 [`canvas-doc-fetch.md`](canvas-doc-fetch.md)；更新再读 [`canvas-doc-update.md`](canvas-doc-update.md)。
- 完整读取 [`canvas-doc-chart.md`](../xml/canvas-doc-chart.md)，按其中的数据白名单和 XML 占位语法准备内容。
- 创建与挂载、读取与替换必须串行；pending `data_id` 只能成功挂载一次，已有图表则沿用当前 Fetch 返回的 `data_id`，不得猜测或使用已失效的引用。

## 命令

| 指令 | 说明 | 必需参数 |
|---|---|---|
| `chart_data_create` | 预创建数据，返回一次性 pending `data_id`，不修改正文 | `--chart-option '{"data":{...}}'` |
| `chart_data_replace` | 按版本完整替换数据，保留 chart record/位置 | `--chart-option '{"data_id":"...","expected_data_version":N,"data":{...}}'` |

- **参数**：图表数据指令不接受 `--revision-id`、`--block-id`、`--content`、`--pattern` 或 `--table-option`。
- **数据格式**：`--chart-option` 接受单层 JSON 对象，`data` 也使用对象。JSON 文本须先解析为对象，不对整个对象二次编码。前端支持 JSON 文本型 `data`，但部分 CLI 构建只接受对象；统一使用对象即可兼容，无需切换 OOXML。
- **大小限制**：数据最多 196608 UTF-8 bytes，整个更新请求最多 262144 bytes。

## 读取当前图表数据

普通 Fetch 返回图表占位；资源不完整时会省略 `data-id` 并返回 warning，此时只能修改尺寸或删除，不能读取或替换图表数据。

完整数据按 `data-id` 读取：

```bash
lark-cli docs +local-fetch --doc "<token>" \
  --scope chart_data --data-id "<data_id>"
```

响应沿用 `docs +local-fetch` 信封，图表数据位于：

```json
{
  "ok": true,
  "data": {
    "document": {
      "document_id": "doccn_xxx"
    },
    "result": "success",
    "updated_blocks_count": 0,
    "command_result": {
      "data_id": "opaque_data_id",
      "data_version": 3,
      "data": {}
    },
    "warnings": []
  }
}
```

图表读取使用 `format=xml` 信封，不返回 DocxXML content；数据位于 `data.command_result`。该 scope 不带 block、页码或深度参数，detail 不参与读取，建议省略。不得从后端请求结构推导额外 CLI 参数。

## 新建

1. 创建数据：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command chart_data_create \
  --chart-option '{"data":{"chart_type":"column","chart_subtype":"clustered","categories":["Q1","Q2"],"series":[{"name":"收入","values":[120,200]}]}}'
```

`chart_data_create` 不接受 `revision_id`，也不接受 `--block-id`、`--content`、`--pattern`、`--table-option`。
成功回执的新数据引用位于 `data.command_result={data_id,data_version}`。

2. 使用返回的 `data.command_result.data_id` 插入：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after --block-id "<anchor_block_id>" \
  --content '<chart data-id="<data_id>" width="432pt" height="252pt"/>'
```

`data-id` 绑定当前文档、5 分钟过期且只能成功消费一次；每个文档最多 64 个未消费 ID。插入后重新 Fetch 获取新 chart record id，不能从 `new_blocks` 获取。

## 替换数据

替换前通过 `--scope chart_data` 取得当前 `data_id`、`data_version` 和完整数据；已有覆盖目标且未发生数据变化的读取可直接使用。此 scope 建立内部读取基线，但不返回文档 revision；数据替换使用 `expected_data_version` 校验图表版本，不能用图表数据代替位置、尺寸或正文更新所需的完整 XML 证据。以此准备完整目标态：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command chart_data_replace \
  --chart-option '{"data_id":"<data_id>","expected_data_version":3,"data":{...}}'
```

`chart_data_replace` 不接受 `--revision-id`。成功后使用响应 `data.command_result.data_id` 重新 Fetch，验证完整数据并取得最新 `data_version`；该回读可作为下一次数据替换的依据，Update 回执本身不能替代它。旧版本、共享或跨文档 ID 均失败；不支持 series/category/style patch。

图表外观也属于 `data` 的完整目标态。当前 Word 已支持的主题色、背景/边框、默认文字、主副标题样式、
坐标轴范围与网格线、雷达形状与逐系列填充、圆环孔径和扇区分离，都应在 Fetch 结果上修改对应
canonical 字段后调用 `chart_data_replace`。不要把 `style_update` 用于图表 theme，也不要因字段属于外观设置
就直接进入 OOXML。若当前客户端明确返回字段不允许或 `CHART_CAPABILITY_UNAVAILABLE`，保留错误和版本证据，
不要自行改写所有图表或通过不透明私有 rule 绕过。

## 尺寸与删除

- 尺寸：以 chart record id 执行 `block_replace`，保留 Fetch 返回的 `id` 和已有 `data-id`，只改 `width` / `height`。
- 删除：以 chart record id 执行 `block_delete`。
- 尺寸和布局约束见 [`canvas-doc-chart.md`](../xml/canvas-doc-chart.md#xml-占位)。
- `CHART_CAPABILITY_UNAVAILABLE` 表示当前客户端未发布图表能力，不转用私有接口。

===== 全文完 =====
