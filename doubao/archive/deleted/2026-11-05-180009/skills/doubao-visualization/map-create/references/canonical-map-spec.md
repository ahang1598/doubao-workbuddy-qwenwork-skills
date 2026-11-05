# Canonical MapSpec — revision 3

只接受显式 contractRevision:3，缺省、旧版本和迁移均拒绝。MapSpec 只保存事实、关系与依据，不保存组件、CSS 或最终 props。

完整配对示例见 [current-route.spec.json](../examples/current-route.spec.json) 与同目录 Plan；区域图参考 [current-region.spec.json](../examples/current-region.spec.json) 及配对 Plan。根字段包括 specVersion、contractRevision、id、title、coordinateSystem、sources、entities、groups、views、task。

task 必须声明 purpose、primaryContent 和 evidence。依据包含 id/origin/reference/supports/objectIds，引用真实请求或数据记录，不能为通过校验编造依据。`primaryContent.kind` 仅为 `place/route/region`。`supports` 仅为 `schedule/visit-order/alternatives/view-split/representative-position`；无适用关系时 `evidence` 填 `[]`，需这些依据的组织仍须提供。详见 [组件规则](component-rules-v3.md)。

多 View 时，每个 `organization.viewPurposes[viewId].evidenceRefs` 都须引用支持 `view-split` 的依据，该依据的 `objectIds` 须包含对应 View ID 或 `spec.id`；仅填写 `organization.evidenceRefs` 不够。

Place 是可复用实体。Group Member 表示 Place 在某个分组中的一次使用，保存 role、order、time 和 routeIds。坐标相同不自动表示同一 Place；相同 placeId 必须复用同一实体。

Member 的角色来自业务关系，实际组件按当前 View 的拓扑与 orderPurpose 决定。order 有值须声明 visit/display/rank，visit 另须 orderEvidenceRef。transfer 引用 incomingRouteId/outgoingRouteId；同一方案内部换乘可额外提供 incomingSegmentIndex/outgoingSegmentIndex，引用该路线 properties.segments 中真实、递增的交通段索引。折点不等于换乘。往返共点用不同 Member ID，复用同一 Place。

路线 `geometry.status` 支持：

- `resolved`：可信规划或测绘轨迹。
- `supplied`：用户或业务数据直接提供。
- `simplified`：从可信轨迹抽稀。
- `schematic`：只表达连接或方向。
- `unavailable`：没有可绘制几何。

`derivation` 记录如何得到几何，例如 `user-geojson`、`web-dataset`、`endpoint-connection`。状态与视觉组件相互独立。

`Route.relation` 明确线表达 `visit-order`（访问顺序）、`transport`（独立交通段）、`network`（网络连接）或 `connection`（其他连接）。缺省使用中性连接；不会仅从 mode 推断铁路、航空或访问语义。成员均有访问顺序时按游览连接处理，即使 mode 误填 train。独立交通段不要把景点访问列表当作站点；网络节点无序，不能从 memberIds 数组首尾生成起终点。起终点需要显式 origin/destination 角色及当前可见线路的拓扑一致性。

专用交通线还须符合几何证据：航空弧线只用于 transport/flight/schematic；铁路专用表达只用于 transport/train 或 high_speed 的非示意路径，并须通过 geometry.sourceRefs 指向路径来源。其他情形保持普通线和原始交通说明；坐标数量不能证明路径真实性。混合交通按实际分段处理，不把整条路线套上某一种交通样式。来源引用有效只能证明可追溯，不能替代对来源内容的核实。

地理专题线在 Route 填写 `geographicFeature: mountain | river | boundary`（山脉／河流／专题分界），使用 `mode: none`、`relation: connection` 并提供几何坐标；无关联地点时 `memberIds: []`，不用于交通路线。普通区域可填写 `labelPosition: [lng, lat]`，用于区域自身名称的标注位置。

提供路线坐标时必须声明 `LineString/MultiLineString`；每段至少两个合法坐标，所有分段保留，不能删段或跨段补连接。面环至少四个坐标、三个不同顶点且首尾闭合；Compiler 不自动闭合或修补错误几何。

`source.provider` 仅为 `user/file/web/api/connector/demo`。来源记录 URL、标题、发布方、获取时间等；Place、Route、Region 通过 `sourceRefs` 指向来源。不要记录令牌和私有文件全文。

Region 必须声明 `areaRole: boundary | coverage | corridor | uncertainty`。推导范围使用 `inferred:true`，UI 必须标注为“范围示意”；不能仅因路线首尾接近就自动闭合成面。Region 可通过 `relations.routeIds/placeIds` 显式关联路线和地点，Compiler 据此生成关系索引，不从空间相交猜测业务从属关系。

### 真实距离圆形范围

用户明确要求“某地点周边 N 公里”时，使用 Region 的 Circle 几何，不再让模型生成近似圆的 Polygon 顶点：

```json
{"id":"nearby","name":"参照点周边3公里","areaRole":"coverage","geometry":{"type":"Circle","centerPlaceId":"reference","radiusMeters":3000},"sourceRefs":["user-range"]}
```

`centerPlaceId` 必须引用 `entities.places` 中有可靠坐标的真实地点；示例 ID 需替换为本次事实。`radiusMeters` 必填有限正数，公里乘 1000，米原样传入；数值依据来自用户或引用数据，记录在区域 `sourceRefs`，中心坐标依据记录在 Place。缺少半径时确认范围；提出建议必须明确为建议并获得确认，禁止按地图缩放、点密度或随意默认值填数。

Circle 是平均地球模型上的地表距离圆，不是路网等时圈或真实服务边界。Plan 的区域组件选择 `circle`；无显式选择时 Compiler 自动选择它。中心和半径只存于 Spec，不复制到 Plan。名称缺省锚定圆心，允许用 `labelPosition` 指定真实标签位置。地图缩放只改变投影，不改变距离。当前不支持越过 ±180° 或触及 ±85°，会明确报错。

保留行政边界、真实多边形、不规则圈选的 Polygon/MultiPolygon。旧 Polygon 不按外观自动改为 Circle；只有明确的中心和半径依据才能改写事实。`viewportIntent.focus-radius` 只控制镜头，不会生成圆形面。

Route 与 Group Member 的 `routeIds` 是点线关系的事实来源。共享地点复用同一 Place；同一地点可属于多条路线，但侧栏详情仍以 `contentKey` 去重。

`Route.memberIds` 与显式 `Member.routeIds` 必须相互一致；省略后者可由路线引用推导，显式空数组不等于省略。冲突在全局校验，不能因为不在当前 View 就忽略。关系可跨 View，投影只显示当前范围内的端点。

## 可计算属性

需要参与筛选或统计的事实属性通过 `metadata.fieldDefinitions` 声明 `entityType`、一级 `property`、`valueType`、`label`，可附 `unit/sourceRefs`。类型支持 `string/number/boolean/datetime`；值仍保存在对应实体的 `properties`，不复制数据。

字段必须显式声明稳定 id 与 sourceRefs；不根据 label 或数组位置推导身份。fieldId 用于数据源、筛选和指标，同一实体属性不得重复声明。

缺失保持缺失或 `null`，不是 0；数值字符串不自动转成 number，时间必须带时区。同一实体类型的同名属性不能重复声明，来源 ID 必须存在。不支持 JSONPath、嵌套属性路径或表达式。

## 详情字段约定

`view.summary` 描述总览级信息，`group.summary` 描述某个分组或方案，Place、Member、Route 的 `properties` 描述各自事实。均可使用：

- `description`：简短介绍。
- `metrics`：优先用 `[{"label":"路线","value":3,"unit":"条","note":"可选说明"}]` 分离数值与单位；纯文本仍可使用 `value:"约半天，含游览"`。Compiler 保留 0，按明确类型派生展示，不从描述句猜测数值或精度。
- `distance`、`duration`、`recommendedDuration`、`budget`：常用指标的快捷字段。
- `schedule`、`transport`、`notes`、`highlights`：文本或结构化条目数组。
- `recommendations`：`[{"category":"类别","title":"名称","description":"推荐理由","distance":"可选","duration":"可选","address":"可选"}]`。

旅游场景可以在 `food`、`lodging` 和 `recommendations` 中表达餐饮、住宿与备选点；其他场景根据任务语义使用通用字段。只保存已有或可追溯事实，不从视觉需要反推业务内容。

完整机器约束见 `contracts/canonical-map-spec.schema.json`。
