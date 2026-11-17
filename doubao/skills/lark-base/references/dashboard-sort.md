# Dashboard 公共排序

先确定排序对象。柱状图的类别在横轴、指标在纵轴；条形图相反，按字段职责选择配置。

| 排序对象 | 写入位置 | 倒序含义 |
|---|---|---|
| 类别 Category 字段值 | `group_by[0].sort={type:"group",order:"desc"}` | C → B → A |
| 分组系列 Product 字段值 | `group_by[1].sort={type:"group",order:"desc"}` | R → Q → P（字段含 P/Q/R 时），不按 Amount 排名 |
| 对应分组的记录出现顺序 | `group_by[i].sort={type:"view",order:"asc"|"desc"}` | 保留／反转来源顺序 |
| 类别的指标汇总值 | 顶层 `sort={type:"value",by:{...},order:"desc"}` | 金额从大到小 |

指标排序适用于普通图表和排行榜。单表、单类别、单指标可用 `by:{type:"field",field_name:"Amount",rollup:"SUM"}`，计数用 `by:{type:"count"}`；只有这两种唯一系列场景可省略 by。单表多指标或分组聚合不支持指标排行，仍可按字段值／记录顺序排列。多源 value 排序必须用 `by:{type:"source",source_id:"<最新Get返回值>"}`；来源 ID 不按位置拼接，汇总展示不改变此要求。

公共排序只适用于 column/bar/line/area/combo/scatter/radar/pie/ring/ranking 及其内部别名；其他组件不接受公共 sort／limit_size，透视表使用独立协议，切片器方向使用自身 order。漏斗与词云可按类别字段排序，不使用顶层指标排序。

`order` 明确写 asc／desc。同一目标不同时提交字段排序和值排序。`limit_size` 为 1–500；创建时非空数量须搭配指标 sort，排行榜会补缺省倒序前十。普通图表不传数量则不截取；更新可只传数量并保留现有排序。高级合计、组内等排行仅在目标宿主已验证支持时使用。

## 创建

按 Amount 汇总值倒序；普通柱状图和排行榜共用：

```json
{"table_name":"Orders","group_by":[{"field_name":"Category"}],"series":[{"field_name":"Amount","rollup":"SUM"}],"sort":{"type":"value","by":{"type":"field","field_name":"Amount","rollup":"SUM"},"order":"desc"},"limit_size":10}
```

## 更新并保留其他配置

`group_by` 整体替换。只改 Product 时，先 Get，原样保留第一分组及其他未改属性，不固定设置 Category 为 view asc。以下示例针对第二分组确为 Product 的现有组件；Get／jq 失败或输出为空时不执行 Update：

```bash
patch=$(lark-cli base +dashboard-block-get --base-token "$BASE" --dashboard-id "$DASHBOARD" --block-id "$BLOCK" --as user --json --jq '
  .data.block.data_config.group_by
  | if length == 2 and .[1].field_name == "Product" then .
    else error("先确认 Category/Product 分组") end
  | .[1].sort = {type:"group",order:"desc"}
  | {group_by:.}') &&
[ -n "$patch" ] &&
lark-cli base +dashboard-block-update --base-token "$BASE" --dashboard-id "$DASHBOARD" --block-id "$BLOCK" --data-config "$patch" --as user --json
```

指标排序对象整体替换；省略 sort／limit_size 保留，`sort:null` 清除值排序和截取，`limit_size:null` 只清除截取。更换指标使旧引用失效时同时替换或清除 sort。只修改排序不用另传轴反转样式；公共方向与原生样式冲突时以公共方向为准。

## 排序验收用例

回读确认排序归属、方向、来源和未改分组保持一致。专项验证再看面板依据、正／倒序及图表实际顺序；dry-run、保存成功或 Top 1 成员正确不能证明显示顺序，不自行重排 Get-data 结果。
