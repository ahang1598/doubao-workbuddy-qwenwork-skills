---
name: app-component-list
description: App 列表共享CLI数据、字段、交互、页面按钮及更新协议；各subtype独立维护。
---

# 列表共享协议

列表是记录展示，combined只是同一记录的字段组合，不做数值聚合。每表格最多关联一个Base，须与App同Workspace。必读 [数据语义](app-data-common.md)；类型尺寸与字段密度分别读 [standard](component-list-standard.md)、[grouped](component-list-grouped.md)、[collapsible](component-list-collapsible.md)、[card](component-list-card.md)、[detail](component-list-detail.md)。

## 创建与字段

`+app-block-create --type list --sub-type <类型> --data-config`；默认standard不可换。仅base_token/table_name必填，其余columns/fields/filter/sort_by/group_by/card_config/detail_config可省略保留默认。新建真实schema显式字段，直接展示→可见列、详情→内容/入口、组合→子字段；底表字段不自动外露，增量未点名保持，[]不兜底。

### 先固定列表可见字段

默认完整新建的首页主列表执行 [首页字段计数](app-visual-quality.md#首页主列表字段计数)：初始可见、同一列表、真实业务字段ID去重；详情区域不凑数。用户指定类型/字段集合与已有局部修改按该节边界处理。

管理/跟进列表先映射需求→真实字段ID/名→可见列，再生成columns/fields。标识/正文/状态及所需负责人/金额/时间优先，点名项不被默认挤掉；多字段用合适样式/组合/宽度，不删必需项。

- 要看“处理到哪一步”：处理状态同时写入可见列；`group_by/filter` 只负责分组/范围，不代替逐条查看状态。
- 要跟进“反馈内容、分类、处理状态”：三者均有真实可见承载，不只留分类和状态，正文另藏在详情里。
- 要查看对象的规格/成分等关键属性：按原需求的查看范围列入可见字段；仅要求底表存在则保留底表义务，不自动推成展示要求。明确要求只在详情看时按详情契约验收。

block-get核visibleFields/columns展开子字段与映射，创建/allowViewDetail不证明内容；详情配置另回读、缺证据列缺口，修改只点名项保留其它字段/排序/分组/范围。

| 键 | 结构 |
| --- | --- |
| columns 单字段 | `[{"type":"field","field_name":"订单编号"}]` |
| columns 组合列 | `[{"type":"combined","field_names":["客户","金额"],"image_size":"small","highlight_first_field":true,"show_field_name":true}]` |
| fields（card/detail） | `["订单编号","客户","金额"]`，不传role/visible对象 |
| sort_by | `[{"field_name":"金额","order":"desc"}]` |
| group_by（standard/grouped/collapsible） | `[{"field_name":"状态","order":"asc"}]` |
| filter | `{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":"待处理"}]}` |

combined至少一个字段，image_size为small/large；省略显示参数保留已有。字段不得重复入树、组合不嵌套；图片角色仅真实附件或确认附件输出，不重复作正文。不要把SDK字段句柄/内部visibility树拼成CLI JSON。传入可选filter须conjunction及1～50conditions，其它类型按公开schema；不能假设detail/card必须title、grouped只能一个group_by。

```bash
lark-cli base +app-block-create \
  --app-token <app_token> --page-id <page_id> \
  --name "待处理订单" --type list --sub-type standard \
  --data-config '{"base_token":"<base_token>","table_name":"订单","columns":[{"type":"field","field_name":"订单编号"},{"type":"combined","field_names":["客户","金额"]}],"filter":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":"待处理"}]},"sort_by":[{"field_name":"金额","order":"desc"}]}' \
  --interaction-config '{"interaction_config":{"allowViewDetail":true}}' --as user
```

表名、字段、条件替换成真实schema。更新只传点名Patch，数组/对象按当前协议替换；切源必须按新schema重建source-bound字段、图片、范围、排序与动作，不依赖旧字段。只更新顶层filter可传`{"filter":{...}}`，无需type。

## 记录详情、新增与动作

列表相关操作默认先用列表内建新增、详情、row_actions等自定义操作，不单独生成重复按钮组件。新增入口不用默认“新增记录”，按对象设置createRecordButtonText，如“新增客户”“新增工单”；未授权新增不为满足文案规则开启写入。用户点名Form或需要独立页面跳转时按下方入口契约执行，列表操作不能替代明确要求的Form入口。

列表参数包在interaction_config方法内：`--interaction-config '{"interaction_config":{"allowViewDetail":true,"allowCreateRecord":true,"createRecordButtonText":"新增订单","allowDeleteRecord":false}}'`。三个allow为布尔，文案为字符串；未传保持，false关闭。本地查看：`+app-block-update --print-schema --flag-name interaction-config`。

普通/卡片/分组等需打开具体记录时开启allowViewDetail；detail内建右侧详情可承接普通查看/编辑，明确独立详情入口才另开。普通跟进或字段更新不强造业务按钮。detail内建详情已有按钮不重复配置。不把Button字段当正文，不把页面跳转当带当前记录的动作。

逐记录操作（审核、退回、确认、阶段推进等）用 `row_actions`：在 `--interaction-config` 层中与 `interaction_config` **同级**，值为字符串数组，元素是底表**已存在的按钮字段**（Button，fieldType 3001）的字段名或字段 ID：

```bash
lark-cli base +app-block-update \
  --app-token <app_token> --page-id <page_id> --block-id <block_id> \
  --interaction-config '{"interaction_config":{"allowViewDetail":true},"row_actions":["审批","驳回"]}' --as user
```

- 按钮字段必须在配置前已存在于底表，且其背后的 Workflow/动作已就绪；字段不存在或不是 Button 类型会被服务端拒绝。缺字段时报告最小 Table/Workflow 依赖，不凭空造字段，不用详情开关冒充。
- 数组顺序即记录上操作按钮的展示顺序；同一字段重复引用按 fieldId 去重。
- 空数组 `[]` 清空全部逐记录操作；不传保留现状；不接受 null；`row_actions` 不能嵌进 `interaction_config` 的开关对象内。

核目标表/匹配Form，要求的Form均用 [根按钮](component-button.md) 跳真实分享URL，不以列表新增替代；无匹配Form且授权内建可allowCreateRecord。报名/报修/申请语义明确，缺承载交最小Form/Workflow不编资源。入口/表回读，权限/配置/实际提交分证；展示列表不自动新增，删除仅明确授权。

逐业务动词核App Page/真实入口/目标表，两表录入各验；详情用allowViewDetail+内容、新增用allowCreateRecord/Form、推进用记录动作，不相互抵扣。未点名开关保持，聊天Form链接不算App入口。

审核、退回、阶段推进、升级、归档必须有真实匹配字段动作或Workflow，核对目标、条件与运行结果，普通新增/详情开关不代表流程已实现。写权限仍由Base/App控制。

逐动作核当前记录→允许条件→动作/写字段→下一状态→责任人/通知。row_actions仅暴露既有Button不建流程；自动分配须写人员字段，不通知代替，不适用不强造字段。缺依赖按 [Workflow](../../scenes/workflow.md) 交接后回原App，定义/入口/运行分验。

## 列表顶部页面按钮

data_config.page_buttons为`[{"name":"查看分析","page_id":"<真实同App页面ID>"}]`。这是列表级跨页入口，不携带当前记录；同名追加/更新保留按钮ID，省略或空数组均保留，当前没有删除操作。目标不可用或回读丢失时报告失败，不新增其它组件顶替。

写后独立block-get核对类型、名称、字段密度、图片角色、范围、分组、排序、交互（含 `row_actions` 引用字段与顺序）与实际按钮目标，再structure核对位置及父级；逐记录按钮还要核对其 Button 字段在底表真实存在且在记录上可见；保存配置与详情/新增/动作实际运行分别验收。新建/本轮列表修改的宽fill及根组合高fill见 [页面布局](../../scenes/app-mode/layout.md)，不使用height auto。
