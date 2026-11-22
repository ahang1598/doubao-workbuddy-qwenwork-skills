---
name: app-component-ai-chart
description: App AI图宿主的默认尺寸、独立协议、布局、有效配置与结果回读。
---

# AI图 ai_chart

选型、family、字段角色、`data_sources`、`spec` 与编辑规则完全沿用 [AI Block](../ai-block.md)，源 Base 选择见其 [宿主差异](../ai-block.md#宿主差异)；本页只写 App 宿主特有部分。旧 `aiBlock + data_config` 不能替代 `ai_chart + --ai-config`。

## 创建

```bash
lark-cli base +app-block-create \
  --app-token <app_token> \
  --page-id <page_id> \
  --name "渠道转化" \
  --type ai_chart \
  --ai-config '{"chart_type":"sankey","sub_chart_type":"sankey","engine":"ECharts","spec":{"tooltip":{"trigger":"item"},"series":[{"type":"sankey","orient":"horizontal"}]},"data_sources":[{"base_token":"<base_token>","table_name":"投放明细","dimensions":[{"field":"渠道"},{"field":"转化结果"}],"measures":[{"field":"金额","aggregation":"sum"}]}]}' --as user
```

- 先用 `+table-list`／`+field-list` 确认真实表名、字段与类型；`field` 必须是真实字段，不用“记录数”这类展示名或自造字段。
- `name` 在 Page 内唯一；`widget_id`/`block_id` 与 `chart_token` 只取真实返回，不按 ID 前缀构造。

## 布局

App 宿主默认 16×16，推荐 W12～36、H14～24，优先 W≥H。`+app-block-create` 没有位置/尺寸参数，也不存在 `--size-mode`；创建后用 `+app-block-update --layout-config`（整页用 `+app-page-update --layout-config`）：

```bash
lark-cli base +app-block-update --app-token <app_token> --page-id <page_id> --block-id <block_id> \
  --layout-config '{"size_mode":{"width":"fixed","height":"fixed"},"position":{"x":0,"y":12,"w":24,"h":18}}' --as user
```

整行用页面 w 表达；只有用户明确要求且 [布局协议](../../scenes/app-mode/layout.md) 允许时才用 `width:fill`，不默认高 fill 或 auto，不沿用其它组件的高 fill 规则，也不参与根列表/视图/透视表唯一候选计数。根组件按 48 栅格与无重叠校验，写后 `+app-structure-get` 回读坐标与模式。

## 编辑、回读与结果

- 编辑：先 `+app-block-get` 读当前 `ai_config`，再按 [AI Block 编辑](../ai-block.md#编辑) 提交 patch。改标题、方向、样式或 AI 内部 subtype 都改原组件，不新建第二个组件；只改 `spec` 时不重配数据源。
- 配置回读：核对 `ai_config` 的 `chart_type`／`sub_chart_type`／`engine`／`dimensions`／`measures`／`spec`，不拿 `data_config` 判断；创建/更新回显不能证明视觉已生效，配置成功也不等于结果正确，get-data 有结果也不宣称渲染已端到端验证。
- 结果：`+app-block-get-data --app-token <app_token> --base-token <源 Base> --block-id <chart_token>`。`--block-id` 是 chart_token 而不是 widget_id；`--base-token` 与 `ai_config.data_sources[0].base_token` 一致。按 [AI Block 结果](../dashboard-chart-result.md#ai-block-结果) 解析。
- 普通图表与 AI 图不可互转，选错只能经用户明确授权删除重建。
