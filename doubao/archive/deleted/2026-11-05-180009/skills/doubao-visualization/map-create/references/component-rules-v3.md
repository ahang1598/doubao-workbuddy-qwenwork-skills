# 组件规则与无截图验收（revision 3）

## 可用范围

只支持显式 revision 3。Builder 核对 Catalog、Runtime URL 与 SHA-256；本地变更不等于发布，不得改锁绕过门禁。

## 三层输入，不增加完整 props 树

MapSpec 是事实及依据；Plan 是有界组件节点、数据绑定和展示意图；Compiler 生成最终 Render Graph props。模型不填坐标到 Plan，不输出任意子组件、DOM、CSS 或函数。

- MapSpec revision 3 增加 task:{purpose,evidence,primaryContent}。依据含 id/origin/reference/supports/objectIds；origin 为 user-request/adopted-data/source-fact，reference 指向请求段落或采用的数据记录。主要内容引用 place/route/region ID。
- 分组成员有 order 时必须有 orderPurpose:visit|display|rank；visit 另需 orderEvidenceRef。中转用 transfer:{incomingRouteId,outgoingRouteId} 表达连接；同一交通方案内部换乘另填 incomingSegmentIndex/outgoingSegmentIndex，对应原始 segments 中真实交通段的递增索引。集合代表位置兼容 representative:{placeId,evidenceRef}；行程可省略，由引擎按明确访问顺序（否则成员输入顺序）默认取首个有效真实地点并记录依据。
- Plan 增加 organization:{dimension,evidenceRefs,viewPurposes}。dimension 是 distribution/route/segments/alternatives/itinerary/days/thematic；每个 viewPurposes 项含 reason/evidenceRefs。新规则不依赖标题、行业或 ID 子串。
- 多视图的总览选择通过 organization.overview 记录 content/collection/none、reason；前两者另填 viewId，collection 再填 spatialReason。多个详情缺少总览且没有显式省略理由会失败；不能用声明代替真实的总览节点和详情链接。判断准则与侧栏职责统一见 [View 策略](view-strategy.md)。
- 每个 View 必填 componentNodes，可为空（按结构化关系使用确定性默认组件）。使用根表分析 layers/filters/metrics 和受控 UI sections；不使用旧 group/member/routePresentation；regionPresentation 仅保留指标声明。

单个可执行 Plan 节点示例（绑定对象必须存在于当前 View）：

```json
{
  "id": "visit-labels",
  "componentId": "numbered-marker",
  "binding": { "source": "members", "memberIds": ["m-b"] },
  "presentation": { "variant": "normal", "showLabel": true },
  "actions": [{ "type": "select-element", "target": "self" }]
}
```

绑定仅允许 group、group.members、members、places、routes、regions 六种有限形式。展示字段仅 variant/showLabel/showArrow/meaning；showArrow 只适用于 arrow，布尔值 false 表示实线不绘制箭头，省略默认 true，不支持 dash 组件或虚线间隔。variant 必须为组件支持的基础形态，不能将 selected 当基础 Plan。显式不适用组件报错，不静默替换。输出元素带 planNodeId/businessRef，把事实、样式、动作转换成 props。完整可运行输入见 [MapSpec 示例](../examples/current-route.spec.json) 与 [Presentation Plan 示例](../examples/current-route.plan.json)；各组件的实际 props JSON 见 Catalog 内嵌 guidance。

## 能力与交互归属

| 层 | 唯一职责 |
| --- | --- |
| 组件 definition/Catalog | 公开 ID、允许角色、必需 props、基础形态、选中与碰撞能力 |
| 组件 USAGE/示例 | 适用、不适用、搭配、交互，以及能实际测量的 props |
| 模型 | 根据请求与事实填写组织依据、选择合法节点；仅在有明确偏好时覆盖 UI sections |
| Compiler | 按阅读职责组合默认 UI、解析绑定、校验角色与关系、派生 props、单一系列编码、记录转换身份 |
| Runtime | 地图/侧栏/程序调用共享选择状态，取消恢复，执行宿主批准的动作 |
| 独立 checker | 从原始事实独立比对 props，读取真实 DOM/绘制几何并触发交互 |

POI 使用专用 selected 图标，名称紧凑容器反色，description 不同步高亮；collapsed 选中展开，取消恢复基础布局。编号点圆底与名称使用强调色和对比文字；普通途经点、起终点、中转点只反色名称标签，锚点不变。集合卡无地图选中形态。测量和绘制消费同一最终形态，不改变已确认碰撞算法与隐藏规则。

## 校验与报告

1. Spec 自校验：结构、引用、坐标/几何、顺序意义、依据适用范围、日程/备选/拆 View 条件。
2. Spec→Plan：组织与组件角色、绑定范围、不重复绑定、集合代表位置。
3. Plan→props：实际组件、variant、showLabel、showArrow 与绑定展开一致；Catalog、资源能力、版本匹配。
4. Spec→props：名称、坐标、分段及几何真实性、编号、区域、主要内容无丢失；侧栏站点的访问身份、名称、描述、顺序、关联元素与配色逐项核对，拒绝空列表及截断；不只相信 Compiler 自报 expected。
5. 浏览器：真实点击页面入口验证所有 View 可达且能返回初始 View；再检查真实元素和 UI、几何和视野、选择/恢复、侧栏联动、缩放、资源及字体就绪。程序直接激活 View 只用于内容检查，不代替导航证据；已有分析筛选和数据指标验证继续执行。

报告记录规则、责任层、路径、对象/节点 ID、预期与实际摘要哈希。绑定 Spec/Plan/Graph/Catalog、Compiler、校验器、HTML 字节身份。failed/not-run/旧报告不能当 passed；修改代码或产物需重新验收。

revision 3 的 deterministic-v2 不截图、不模型看图、不写 visual-review.json。它不声称评测审美、瓦片像素完整性或 GPU 像素正确性，也不能机械证明来源真实或自然语言理解正确。正式交付使用当前产物绑定的 startup-v1 启动报告；full 留作开发回归。

以下为维护阶段的交付门禁命令，不代替 `create-map` 的 HTML 发布。成功后正常回答用户需求，并在回复末尾原样附上唯一的地图 renderer；统一遵循 [验收与交付](../SKILL.md#验收与交付)。

```bash
node "$SKILL_DIR/scripts/check-html.mjs" --html build/map.html --spec canonical-map-spec.json --plan presentation-plan.json --compiler-report build/compiler-report.json --catalog /absolute/path/to/catalog.json --mode startup --report build/check-report.json
node "$SKILL_DIR/scripts/emit-doubao-renderer.mjs" --html build/map.html --check build/check-report.json
```

本地开发复现：node tools/test-component-rules-browser.mjs --components-dir /absolute/path/to/content-map-kit。使用真实 SDK、本地不可变哈希资源，不发布、不改锁。本地 HTML 不可通过正式 emitter 的本地资源门禁，这不是发布授权。
总览与侧栏的完整编译回归：`node tools/test-view-reading.mjs`；加 `--browser` 使用已锁定的 CDN 和真实 SDK 验收集合入口、day/day-detail 列表、选择与恢复，不截图、不发布。
