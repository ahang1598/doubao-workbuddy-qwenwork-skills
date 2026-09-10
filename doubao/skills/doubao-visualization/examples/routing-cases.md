# 路由案例

本文件用于回归测试，不是运行时必读。

## 应触发

| 用户请求 | 主模式 | 基础加载 | 条件追加 |
| --- | --- | --- | --- |
| “把这组季度收入做成趋势图。” | ECharts | `mode-echarts.md` | 无 |
| “做一个带 visualMap 的移动端热力图。” | ECharts | `mode-echarts.md` | `echarts-option-spec.md` |
| “解释 RAG 从切片到回答的流程，画清楚。” | 静态 HTML/SVG | `mode-html-svg.md` | 无 |
| “做一张移动端高密度组织关系图。” | 静态 HTML/SVG | `mode-html-svg.md` | `renderer-trigger-design.md`、`renderer-output-mobile.md` |
| “拖动频率观察波形怎么变。” | 交互 HTML/SVG | `mode-html-svg.md` | `renderer-stability-math.md`、`renderer-interaction-geometry.md` |
| “逐步演示 BFS 队列变化。” | 交互 HTML/SVG | `mode-html-svg.md` | `renderer-stability-math.md`、`renderer-interaction-geometry.md` |
| “框出图中的接口位置。” | 原图静态叠加 | `mode-image-overlay.md` | 无 |
| “识别并框出图中的 8 个核心部件。” | 原图静态叠加 | `mode-image-overlay.md` | coord ≥3，同时读取两个 image-overlay spec |
| “沿迷宫标出完整路径。” | 原图静态叠加 | `mode-image-overlay.md` | 两个 image-overlay spec |
| “参考设备照片画成简化结构示意。” | 静态 HTML/SVG | `mode-html-svg.md` | 标明“示意” |
| “先标传感器位置，再画温度趋势。” | 原图叠加 + ECharts | 两个主模式文件 | `composition.md` |

## 不应触发或应降级

- “把这段话润色得更自然。” → 纯文字。
- “解释一下什么是递归，两句话即可。” → 纯文字通常足够。
- “导出一份 PPT。” → 使用 PPT 文件能力，不用 renderer 冒充。
- “在地图上画出这几个城市的路线。” → 禁止地图可视化，给文字路线或查询方案。
- “根据这条真实股价画走势，但没有数据源。” → 请求数据或提供明确标注的模板，不编造。
- “生成一张电影海报风艺术插画。” → 不由本 Skill 承接。
- “给我做一个头像或壁纸。” → 不由本 Skill 承接。
- “画一张写实产品广告图。” → 不由本 Skill 承接。

## 边界与组合

### 上传图片但不一定要用

用户：“我上传了一张海报，帮我概括文案。”

处理：图片用于读取内容；文字总结已足够时不生成可视化。

### 原图保持还是结构示意

用户：“基于这张产品图做一张结构图。”

处理：如果“结构图”要求精确对应，保持原图或先确认；如果用户只要简化结构示意，允许提取直接可见结构自绘 SVG，并标注“示意”。

### 数据与机制同时存在

用户：“画销量趋势，并解释为什么促销后上升。”

处理：ECharts 承担销量数据；原因只有在有可靠证据时才用静态 HTML/SVG 或文字解释，不把推测画成事实。

### 原图交互而非静态标注

用户：“点击照片上的每个接口显示用途和注意事项。”

处理：使用一个原图 HTML/SVG 交互模块，同时支持 tap/click；不要再输出重复静态标注图。

### 静态而非无意义交互

用户：“画出一份审批流程。”

处理：使用静态 HTML/SVG 流程图。除非用户要逐步演示状态变化，否则不添加播放按钮或动画。
