# 路由案例

本文件用于回归测试，不是运行时必读。

## 应触发

| 用户请求 | 分支 / 主模式 | 基础加载 | 条件追加 |
| --- | --- | --- | --- |
| “在地图上画出这几个城市的路线。” | 地图 `map-create` | `map-create/SKILL.md` | 按地图入口读取所需参考，不加载非地图 renderer 规范 |
| “在望京上班，比较附近适合租房的区域和距离。” | 地图 `map-create` | `map-create/SKILL.md` | 按地图入口补充可信地点与区域数据，不强排成行程 |
| “把这组季度收入做成趋势图。” | ECharts | `mode-echarts.md` | 无 |
| “把日期×小时访问量做成带 visualMap 的移动端热力图。” | ECharts | `mode-echarts.md` | `echarts-option-spec.md` |
| “解释 RAG 从切片到回答的流程，画清楚。” | 静态 HTML/SVG | `mode-html-svg.md` | 无 |
| “做一张移动端高密度组织关系图。” | 静态 HTML/SVG | `mode-html-svg.md` | `renderer-trigger-design.md`、`renderer-output-mobile.md` |
| “拖动频率观察波形怎么变。” | 交互 HTML/SVG | `mode-html-svg.md` | `renderer-stability-math.md`、`renderer-interaction-geometry.md` |
| “逐步演示 BFS 队列变化。” | 交互 HTML/SVG | `mode-html-svg.md` | `renderer-stability-math.md`、`renderer-interaction-geometry.md` |
| “框出图中的接口位置。” | 原图静态叠加 | `mode-image-overlay.md` | 无 |
| “识别并框出图中的 8 个核心部件。” | 原图静态叠加 | `mode-image-overlay.md` | coord ≥3，同时读取两个 image-overlay spec |
| “沿迷宫标出完整路径。” | 原图静态叠加 | `mode-image-overlay.md` | 两个 image-overlay spec |
| “参考设备照片画成简化结构示意。” | 静态 HTML/SVG | `mode-html-svg.md` | 标明“示意” |
| “先标传感器位置，再画温度趋势。” | 原图叠加 + ECharts | 两个主模式文件 | `composition.md` |
| “解释《动物庄园》的权力腐化机制，配一张象征性知识插画。” | 生成式知识配图 | `mode-generated-illustration.md` | 必读 `generated-prompt-rules.md`、`generated-style-guide.md`、`generated-tool-contracts.md`、`shared-quality.md` |
| “参考设备照片，重绘成教材式剖面知识图。” | 生成式知识配图 | 同上 | 原图仅作参考，明确解释性重绘 |
| “画销量趋势，并用知识插画解释已核验的促销机制。” | ECharts + 生成式知识配图 | 两个主模式及生成分支依赖 | `composition.md`；数值只由 ECharts 承担 |

## 不应触发或应降级

- “把这段话润色得更自然。” → 纯文字。
- “解释一下什么是递归，两句话即可。” → 纯文字通常足够。
- “导出一份 PPT。” → 使用 PPT 文件能力，不用 renderer 冒充。
- “根据这条真实股价画走势，但没有数据源。” → 请求数据或提供明确标注的模板，不编造。
- “生成一张电影海报风艺术插画。” → 不由本 Skill 承接。
- “给我做一个头像或壁纸。” → 不由本 Skill 承接。
- “画一张写实产品广告图。” → 不由本 Skill 承接。
- “用生成图准确标注这张事故照片的碰撞位置。” → 原图叠加，保留原图证据。
- “用生图画出这组数据的精确占比。” → ECharts，不由生成图承担精确比例。
- “生成知识配图，但没有可用图片生成工具。” → 保留文字；结构可靠时可改用静态 HTML/SVG。

## 边界与组合

### 上传图片但不一定要用

用户：“我上传了一张海报，帮我概括文案。”

处理：图片用于读取内容；文字总结已足够时不生成可视化。

### 原图保持还是结构示意

用户：“基于这张产品图做一张结构图。”

处理：如果“结构图”要求精确对应，保持原图或先确认；如果用户只要简化结构示意，允许提取直接可见结构自绘 SVG，并标注“示意”。
用户明确允许教材式解释性重绘时，选择生成式知识配图，并标明原图仅作为参考。

### 数据与机制同时存在

用户：“画销量趋势，并解释为什么促销后上升。”

处理：ECharts 承担销量数据；原因只有在有可靠证据时才用静态 HTML/SVG 或文字解释，不把推测画成事实。

### 原图交互而非静态标注

用户：“点击照片上的每个接口显示用途和注意事项。”

处理：使用一个原图 HTML/SVG 交互模块，同时支持 tap/click；不要再输出重复静态标注图。

### 静态而非无意义交互

用户：“画出一份审批流程。”

处理：使用静态 HTML/SVG 流程图。除非用户要逐步演示状态变化，否则不添加播放按钮或动画。

## 地图路由边界

- “杭州三日游，安排景点和每天的路线” → map-create，不要求用户明确说“地图”；“只要文字，不要地图” → text_only。不能仅因出现“旅游”或地名就触发地图。
- “西湖周边咖啡馆分布”“遵义区县着色”“省级GDP地图” → map-create。
- “在望京上班，预算5000，哪些区域适合租房，离公司多远？” → map-create；区域、距离和租金需有依据，不把候选区域强排为行程。
- “展示长江干流与主要支流”“秦岭、淮河及南北分界在哪里？” → map-create；按有来源的地理形态表达，不调用出行路线工具推造河道或山脉。
- “比较北京和上海的平均房租，只要柱状图” → echarts；“租房合同注意什么”“河流为什么会弯曲”不因题材带区域或河流就转地图，按内容选择文字或图解。
- “日期×小时访问量热力图” → echarts；“技术路线图” → html_svg。
- “圈出地图截图中的图例” → static_image_overlay，无需地理定位不转交。
- “在这张地图截图上描出已经画出的路线，不重新规划” → static_image_overlay，保留原图证据；“将截图中的地点定位到可缩放地图上” → map-create，按子入口核验位置数据。
- “只接受 ECharts geo/map option，不要换技术方案” → 说明本 Skill 不支持该实现，不把 map-create 产物声称为 ECharts option。
- “地图之外还要一个独立的数值图表” → 明确当前地图分支不参与多模式组合；正文可补充数据表，但不声称已经完成用户要求的第二张图。
- 包内地图文件缺失或地图服务不可用 → 说明具体缺项，保留可核验文字，不假装已调用成功。
- 地图成功交付 → 遵循 map-create 原生验收与交付规则，正常回答用户需求，末尾原样附上一个成功 renderer；不追加其他可视化模块。
