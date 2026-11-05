# Presentation Plan — revision 3

总览也可以仅声明整体 `regionIds` 和真实代表 `placeIds`，不加入会自动展开全部成员的 `groupIds`。普通点导航用 `views.<id>.pointEntries: [{placeId, targetViewId}]`，目标必须包含该实际地点；它不生成集合卡，不迁移坐标，也不把目标内所有面叠到总览。详情 View 独立声明本组点线面，来源或史料不能证明边界时仍须标为示意。

模型自行编写 Plan 时，总览决策见 [View 策略](view-strategy.md)：`organization.overview` 分开记录阅读目的 purpose（navigate/spatial）与地图表现 mode（content/collection/none）、理由和实际 viewId；collection 额外提供 spatialReason。多组总览只投影 `view.groups` 摘要，条目通过 `activate-view` 连接同组独立子视图，不依赖地图集合元素；不再声明展平全部成员的 stops/routes section。

只接受显式 contractRevision:3，与 MapSpec 同版本、同 mapSpecId。缺省版本、旧 presentations、迁移参数均拒绝。先阅读本文件，不能先照旧例生成再通过编译报错修复。

区域图参考 [current-region.spec.json](../examples/current-region.spec.json) 与 [current-region.plan.json](../examples/current-region.plan.json)。

Plan 保存展示意图与有限绑定，不复制坐标，不输出完整 props、任意 children、DOM、CSS、JSONPath 或回调。最终 props 由 Compiler 派生。可直接编译的配对输入：[current-route.spec.json](../examples/current-route.spec.json)、[current-route.plan.json](../examples/current-route.plan.json)。

## 必填结构

用户指定区域颜色时必须落实到 `colorStrategy`，不能只写进摘要或组件节点名称。使用 `assignBy:"region"`，`assignments` 以区域 ID 为键且覆盖全部区域，值为六位十六进制颜色或 `{ "value":"#ADD8E6", "label":"重点区域", "selectedBy":"user" }`；其余区域同样显式声明，例如 `{ "value":"#D3D3D3", "label":"其他区域", "selectedBy":"user" }`。同一 label 表示同一配色分类，共用图例与系列色，不改变区域身份。显式配色默认不透明，需要透出底图时再声明 `fillOpacity`（0–1）。只有自然语言色名时选取对应色值，不将精确指定的色值改为主题色；显式配色优先于 palette，缺省才用默认调色板。区域 ID、颜色或分类冲突必须修正，不能忽略后继续交付。

根字段：contractRevision、planVersion:"1.0"、mapSpecId、dataSources、encodings、organization、views。
organization 包含 dimension、evidenceRefs、viewPurposes；每个 purpose 包含 reason/evidenceRefs。
每个 views[id] 包含 componentNodes、layers、filters、metrics。ui 可省略，由 Compiler 组合；如提供 ui，sections 为受控覆盖。无分析需求时数组为空，不能省略成旧协议。
多个 View 需明确总览决策：`organization.overview` 的 mode 为 content/collection/none，reason 解释阅读目的；content/collection 另指定实际 overview 的 viewId，collection 再填 spatialReason 解释代表位置与空间区分。多个详情且没有 overview 时必须声明 none 及省略理由，不能仅漏写 View。单 View 无需额外总览。

多组线路/日程默认提供独立内容 View；同屏完整展示时，声明各组阅读位置 `readingScopes: inline`。以分组 ID 为键，`viewId` 指向包含该组的 View；该 View 须实际展示分组摘要、全部路线名称及已有描述、全部成员点，仅列出 ID 不够。Compiler 将路线名称与已有描述合入分组比较列表，并展示成员点；不额外堆叠同一批路线树。只有真实父子关系需要阅读时才使用层级列表。

```json
{"organization":{"readingScopes":{"group-a":{"mode":"inline","viewId":"network","reason":"当前范围可同时完整阅读，不需要单线详情"}}}}
```

此为 organization 局部示例；其余必填字段仍需填写。独立详情不需要填写 readingScopes。多 View 缺失 Tabs 时 Compiler 补默认导航；显式错误导航拒绝。摘要有唯一子 View 时用 activate-view；无导航目标且无地图元素时用 `actions:[]`；不能给所有列表无条件配置 select-element。

先按 [通用组织规则](view-strategy.md) 决定阅读结构，再选组件。dimension 支持 distribution/route/segments/alternatives/itinerary/days/thematic。

## 地图节点

```json
{
  "id":"visit-labels",
  "componentId":"numbered-marker",
  "binding":{"source":"group.members","groupId":"g"},
  "presentation":{"variant":"normal","showLabel":true},
  "actions":[{"type":"select-element","target":"self"}]
}
```

binding 仅接受 group、group.members、members、places、routes、regions，引用当前 View 内的稳定 ID，不重复绑定。componentNodes 可为空，Compiler 按事实关系给出确定性默认。显式不适用组件报错，不静默替换。

presentation 支持 variant/showLabel/showArrow/meaning/selectionFocus；showArrow 仅用于 arrow，省略默认 true，false 表示不绘制箭头的实线，不支持虚线间隔。variant 仅在组件支持时填写，polygon 等无基础变体时省略；selected 是交互态，不作为基础形态。props 示例以 Catalog guidance 为准，不把节点绑定当作组件 props。

地理专题线使用 `geographic-line` 绑定 routes，类别来自 Route.geographicFeature。区域自身名称通过 `label` 显示（由 region.name 与 labelPosition 生成）；polygon 的 `showLabel` 控制名称显隐，可选中的普通区域面默认在选中时弱化其他元素，取消选中恢复，无需填写 `selectionFocus`。

- visit 整条路线使用编号点，首尾也编号。
- 交通线路用起点/普通途经点/终点；真实换乘需连接关系。共享网络节点在总览中无唯一端点角色，单线详情再确定角色。
- 航空示意用飞机线，铁路用火车线并区分高铁/普铁；真实航迹不能改成弧线。
- 区域使用 regions 绑定；分级设色保留 regionPresentation 作为指标/分级声明，不传坐标。
- 选中形态和碰撞默认能力由组件负责，模型不逐点指定颜色或算法参数。

## 集合入口

集合卡推荐遵循 [View 策略](view-strategy.md)，不是所有分组或密集点的统一表达。仅当任务需要地理入口、有稳定代表位置、有独立详情时使用。聚合分组不重复展开成员与路线，独立点线面及分析层仍可保留。行程 Spec 可省略 representative，由工程默认选取首个有效真实成员并记录依据；显式代表位置仍须通过依据校验。完整 Plan 的每卡须显式声明（基础 Plan 由程序生成）：

```json
{"collectionEntries":[{"groupId":"g","targetViewId":"detail"}]}
```

目标必须是同组独立内容 View，允许 day、day-detail、group-detail 等，不按 kind 名称限制；目标不能仍是集合卡。独立校验器通过合法入口检查详情中的完整内容；不能把路线强塞回入口总览，也不能用卡片掩盖详情缺失。多个卡的代表坐标不能完全相同，其他空间区分依据见通用组织规则。

## 分析、筛选与指标

根 dataSources 引用实体和 fieldId；encodings 声明统计与尺度；View layers 引用 sourceId/encodingId。filters/metrics 显式关联同一有效源。完整字段与边界见 [当前数据协议](data-contract.md)、contracts/analysis-declarations.schema.json。

统一 heatmap 支持 continuous/hexbin/hexbin-3d，区域汇总用 choropleth。热力图无需填写 `modes`，程序统一提供连续热力、蜂窝 2D 和蜂窝 3D。`defaultMode` 仅在需要指定初始模式时填写。柱高由程序自动计算并随地图缩放，无需填写 `hexbin.height`。连续权重和蜂窝统计值独立；缺省权重为 1。源缺失默认报错，显式 skip 才排除并报告质量。不把缺失或负数改成零。
四类筛选 enum/number-range/time-range/text；六类指标 count/distinct-count/sum/average/min/max。默认全源颜色/柱高尺度稳定，显式 filtered 才重标定。空筛选保留相机。
预设仅使用 Catalog 的真实 ID；未知能力或资源不匹配报错，不改锁。

## UI、样式与布局

默认不手工枚举 ui.sections。Compiler 从可读数据、访问顺序、图层能力和 View 数量组合 UI。需要覆盖时提供非递归 ui.sections，binding 必须在该组件 supportedSources 内。多个 View 才用 semi.tabs；访问顺序/时间才用 semi.timeline；semi.list 支持 view.groups/view.routes/view.stops/view.recommendations。导航和详情关闭动作不可被覆盖移除；空内容不渲染空壳。摘要、指标、图例和详情各有职责，不重复同一事实。长文本不伪装成大号数值。
`ui.sections.actions` 使用字符串数组，如 `["select-element"]`；地图节点 `componentNodes.actions` 使用对象数组，如 `[{"type":"select-element","target":"self"}]`。无交互时填 `[]`。

按 [侧栏阅读职责](view-strategy.md#ui-阅读层级与动作) 选择常驻列表与选中详情。单个有明确 visit 顺序的内容范围应配置 semi.timeline + view.stops + select-element；遗漏时 Compiler 补充此默认并记录诊断。成员按访问身份保留，不能用 maxItems 截断或把多个分组拼成一条序列。摘要/指标等无事实的可选区块会省略；站点绑定为空是错误，不是成功的空态。selected.properties 仅负责选中后详情，不能代替常驻列表。

stylePreference/shellPreference 只表达受控偏好。点线、图例、侧栏从同一系列编码取色，不逐对象配色。viewportIntent 支持 fit-elements/focus-element/focus-radius/fit-region/fixed-camera/preserve-camera，用户明确镜头要求不可静默改写。

当前分类配色支持 `assignBy: group|route`。`category` 尚未实现，编译返回 `COLOR_CATEGORY_UNSUPPORTED`，不得将它当作可用选项反复尝试。餐饮、住宿和推荐信息统一进入推荐列表，保留已有距离、用时与地址；没有数据时不补写。

layoutIntent 可在根与 View 声明。默认使用组件碰撞能力，模型不能关闭布局、偏移、降级或辅助隐藏。用户覆盖必须在同一作用域声明 selectedBy:"user" 和具体 reason；子级标注不能为父级限制背书。实体隐藏还须组件允许和有限 selector 授权。

完整机器合同：[presentation-plan.schema.json](../contracts/presentation-plan.schema.json)。生成后先编译校验，再构建。
