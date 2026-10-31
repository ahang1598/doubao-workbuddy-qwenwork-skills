# 仪表盘组件命令 Reference

## 组件命令范围

| 命令 | 参数与返回 |
|---|---|
| `+dashboard-block-list` | `--base-token`、`--dashboard-id`；返回组件清单和分页信息，组件含 `block_id`、`name`、`type`、`position` |
| `+dashboard-block-get` | 上述参数加 `--block-id`；从 `data.block` 读名称、类型、位置和配置 |
| `+dashboard-block-get-data` | 只需 `--base-token`、`--block-id`，不需要 `--dashboard-id`；返回计算结果，不含组件元数据，按 [结果协议](dashboard-chart-result.md) 解析 |

`data_config` 结构由 `type` 决定，从 [类型入口](dashboard-chart-config.md#支持的组件类型type-枚举) 选专属协议。`view` 的详情返回视图引用，用其中的 `tableId`、`viewId` 读记录，见 [视图协议](dashboard-view.md)。坐标的读取与输入见 [布局协议](dashboard-layout.md)。

## 组件列表与分页

`--page-size` 默认 20，取值 1–100；完整枚举用 100。返回 `has_more=true` 时，把本页 `page_token` 传给下一次 `--page-token`，直到 `has_more=false`。用静态 `--jq` 投影时保留这两个分页字段和所需字段；外部名称不拼进 shell 或 JQ 代码。

## 创建、更新与删除

创建或追加组件后按 [统一布局流程](../scenes/dashboard.md#统一布局流程) 收尾；命令返回不能替代指标、结果和最终坐标验收。

- 创建用 `+dashboard-block-create --base-token --dashboard-id`，必填 `--name`、`--type`。取 ID 加 `--jq '.data.block.block_id'`，不要把 `2>&1` 的输出交给 JSON 解析。本月等范围在 `data_config.filter` 里对日期字段写 `{"field_name":"<日期字段>","operator":"is","value":["CurrentMonth"]}`。配置用 `--data-config` 提交，必填字段按类型协议；位置可选，见 [坐标输入](dashboard-layout.md#组件坐标---position)。
- 更新用 `+dashboard-block-update`，定位参数再加 `--block-id`；可改 `--name`、`--data-config`、`--linkage`、`--position`。外层 `type` 不可改；倒计时内部模式切换按 [倒计时更新协议](dashboard-countdown.md#更新语义)。
- 普通图表配置更新按 [更新语义](dashboard-chart-config.md#更新语义)，特殊组件按专属协议；联动单独按 [联动协议](dashboard-linkage.md)，不整包回传 Get 结果。
- 删除用 `+dashboard-block-delete --base-token <base_token> --dashboard-id <dashboard_id> --block-id <block_id> --yes`；`--yes` 是高风险写入的确认参数。

## 多个组件串行读取

下例只用于已确认支持计算结果的图表。ID 逐字取自本次可信响应，在一个 shell 调用内串行执行，每条命令各输出一个 JSON；不把名称或未验证文本当 shell 代码。

```bash
set -euo pipefail
block_ids=("<block_id_1>" "<block_id_2>")
for block_id in "${block_ids[@]}"; do
  lark-cli base +dashboard-block-get --base-token "<base_token>" --dashboard-id "<dashboard_id>" --block-id "$block_id"
  lark-cli base +dashboard-block-get-data --base-token "<base_token>" --block-id "$block_id"
done
```

只需配置或只需结果时保留对应命令。`text` 只读详情正文；`view` 按视图记录协议读取；其他类型按专属协议，不套用计算结果命令。

## text 类型特殊结构

`text` 组件展示富文本，不需要数据源配置（无 `table_name`、`series`、`group_by`、`filter`）。唯一字段 `text` 为必填 string。

支持的 Markdown：`#`、`##`、`###` 一到三级标题；`**加粗**`、`*斜体*`、`~~删除线~~`；`1.` 有序列表、`-` 无序列表。链接、图片、代码块、表格等其他语法都不支持。
