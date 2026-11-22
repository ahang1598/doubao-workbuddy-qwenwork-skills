---
name: app-component-view
description: App 表格、看板、画册、甘特和日历视图的尺寸及专属View协议。
---

# 视图 view

未指定记录形态优先List；明确grid/kanban/gallery/gantt/calendar或List不能满足才用view。默认容器宽×20，推荐W24～48、H≥16；显式宽fill，根级组合决定高fill，不height auto，用户合法尺寸优先。

术语：grid view是“表格视图/表格视图组件”，与list/standard不同。点名表格视图/视图组件/网格视图必用view+grid，规划/答复不把list叫视图；模糊表格/清单/列表/记录表默认List，歧义影响交付先澄清。type/sub_type不可修改，建错仅删除重建。

data_config.base_token/table_name必填，table_name可名或ID，view_type默认grid，不传sub_type。组件创建独立Base View，不复用现成View；更新来源/类型会替换专属View并在提交成功后尽力回收旧View。

可选filter（最多50条）、group_by/sort_by（各最多1字段）、visible_fields、cover_field（gallery）、time_range（calendar/gantt，start_field_name/end_field_name/title_field_name原子对象）。gallery 不支持 group_by，calendar 不支持 group_by/sort_by。来源、字段、日期按真实schema，不能用近似视图替换指定形态。

按 [选型](app-component-selection.md) 核原话→Page→view/view_type→源→配置。grid显式写；看板分列核真实字段并写group_by回读，kanban/标题不抵扣。创建/重试保留形态/分组，缺能力/字段blocked不退list；visible_fields仅明确展示项，不强加全表。

临期/逾期/周期按 [时间配方](app-time-recipes.md#时间语义的最小操作配方) 保存真实时间谓词，数值比较数字标量；失败查字段输出/协议，不只剩状态，block-get核有效筛选双边界。

calendar/gantt显式time_range开始/结束/标题，回读业务含义/方向；单日期按协议同真实日期，不编端点。缺真实区间/能力列缺口，默认推断、近似名称、有条带不证明正确。

看板明确只按 A、B、C 分列时，group_by 绑定该状态字段，filter 同时保留点名集合，不多出其它列；gallery 的照片/封面绑定真实附件 cover_field。日历使用原话点名日期，字段不兼容时保留缺口，不换相邻日期或给存量记录批量复制日期。

Gallery 选择“无封面”不是空字符串字段值。更新时使用
`--display-config '{"clear_fields":["cover_field"]}'`，Builder 会调用 `coverField(null)`；
省略 cover_field 表示保留旧值。

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> \
  --name "订单看板" --type view \
  --data-config '{"base_token":"<base_token>","table_name":"订单","view_type":"kanban"}'
```

## 视图组件的五种标准配置

替换真实占位符执行：group_by/sort_by≤1，group_by仅grid/kanban/gantt、sort_by不用于calendar；cover_field仅gallery；time_range仅gantt/calendar，三字段必填。逐项回读，不只核存在。

**1. 看板 + 分列 + 筛选**

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> --name '合作进度看板' --type view \
  --data-config '{"base_token":"<base_token>","table_name":"UP主数据列表","view_type":"kanban","group_by":[{"field_name":"沟通进度"}],"visible_fields":["达人名称","沟通进度","报价"],"filter":{"conjunction":"and","conditions":[{"field_name":"一级类目","operator":"contains","value":"母婴宠物"}]}}' --as user
```

回读：`view_type=kanban`；`group_by` 只有 1 项且等于点名字段；`filter` 完整保留点名集合。

**2. 画册 + 封面 + 可见字段**

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> --name '当季新款画册' --type view \
  --data-config '{"base_token":"<base_token>","table_name":"商品","view_type":"gallery","cover_field":"商品图","visible_fields":["商品名","价格","上架日期"],"filter":{"conjunction":"and","conditions":[{"field_name":"季节","operator":"is","value":"当季"}]}}' --as user
```

回读：`cover_field` 是真实附件字段；`visible_fields` 覆盖点名信息；画册不支持 group_by。

**3. 甘特 + 起止日期**

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> --name '专利申请进展' --type view \
  --data-config '{"base_token":"<base_token>","table_name":"专利","view_type":"gantt","time_range":{"start_field_name":"申请日期","end_field_name":"授权日期","title_field_name":"专利名称"},"visible_fields":["专利名称","申请人","状态"]}' --as user
```

回读：起止为真实日期字段，标题绑定真实“专利名称”，方向为申请→授权；甘特不支持 cover_field。

**4. 日历 + 日期**

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> --name '维保日历' --type view \
  --data-config '{"base_token":"<base_token>","table_name":"设备台账","view_type":"calendar","time_range":{"start_field_name":"下次保养日期","end_field_name":"下次保养日期","title_field_name":"设备名称"},"filter":{"conjunction":"and","conditions":[{"field_name":"设备状态","operator":"isNot","value":"已报废"}]}}' --as user
```

回读：日期用原话点名的业务日期（维保用“下次保养日期”，不用报修时间）；单日期日历 start 与 end 用同一个真实字段，不编第二个日期；日历不支持 group_by。

**5. 表格视图 + 筛选**

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> --name '待开播场次' --type view \
  --data-config '{"base_token":"<base_token>","table_name":"直播场次","view_type":"grid","visible_fields":["场次名称","直播日期","平台"],"filter":{"conjunction":"and","conditions":[{"field_name":"场次状态","operator":"is","value":"待开播"}]}}' --as user
```

回读：`view_type=grid`；`filter` 精确等于点名状态集合，不扩到“待启动、暂停”等相邻值。

五段配置共用一条验收标准：独立执行 `+app-block-get`，必须读回同样的 `view_type`、`filter`、`group_by`、`cover_field`、`time_range`。只写入成功或只确认组件存在，都不算完成。

## 复制单个 View：按公开配置新建

block-copy不支持View或后代含View容器；单View仅同App按公开配置重建，不是快照克隆、不承诺整树无损。

1. block-get保留原始源，核目标Page/唯一新名；仅取公开data_config的base_token/table_name/view_type/filter/group_by/sort_by/visible_fields/cover_field/time_range，核真实字段/数量/类型；不更新/删除源组件或View。
2. 列保留项/缺口：读取可多级分组/多列排序，创建各≤1；gallery无分组、calendar无分组/排序，description/手工行序/rank等不可重建。无法表达则停止并报告，用户明确接受缺口才按约定建，不丢规则/隐藏字段后称完全复制。
3. 一次block-create --type view提交完整公开data-config（源筛选/分组/排序/显隐/专属项），不先空壳后补。样式/交互仅公开字段；目标布局按 [单位](app-block-config.md#布局输入与回读单位) 另生成。不回放整包get/内部ID/快照/像素，不先建Base View再view_id挂载。
4. 保存真实ID，独立block-get核新widget_id≠源及完整上述配置，再读源确认身份/配置未变；structure核目标页/父级/尺寸。公开回读无专属View ID，只证明新组件/公开配置/源状态，底层资源隔离未验证，不凭新widget/chart称实证。超时先get/list，不盲重发。

源恰为下例公开配置时一次创建；实际生成完整源配置，不照抄覆盖条件：

```bash
lark-cli base +app-block-get --app-token <app_token> --page-id <source_page_id> --block-id <source_block_id> --as user
lark-cli base +app-block-create --app-token <app_token> --page-id <target_page_id> --name '进行中订单副本' --type view \
  --data-config '{"base_token":"<base_token>","table_name":"订单","view_type":"grid","filter":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":"进行中"}]},"group_by":[{"field_name":"状态","order":"asc"}],"sort_by":[{"field_name":"开始","order":"desc"}],"visible_fields":["名称","状态"]}' --as user
lark-cli base +app-block-get --app-token <app_token> --page-id <target_page_id> --block-id <new_block_id> --as user
lark-cli base +app-block-get --app-token <app_token> --page-id <source_page_id> --block-id <source_block_id> --as user
```

不支持app-block-get-data；独立block-get核对View组件的公开配置、来源、类型、筛选和模式，运行展示需要页面证据。宽高填充只按 [页面布局](../../scenes/app-mode/layout.md) 判定，容器内部不触发根唯一候选规则。

分列先核实体/真实字段，不以排期表“进度”代替沟通进度；跨表核公开关系/Lookup及授权，回读源表/分组/状态集合，近名不证明等价。
