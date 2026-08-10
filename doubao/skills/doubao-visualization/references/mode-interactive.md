# HTML/SVG 交互解释

## 读取门

生成任何 renderer 前，**必须完整读取**：

1. `mode-interactive.md`
2. `renderer-trigger-design.md`
3. `renderer-stability-math.md`
4. `renderer-interaction-geometry.md`
5. `renderer-output-mobile.md`
6. `shared-quality.md`

没有读完不得开始写 HTML/JS。这些文件保留原通用可视化 Skill 的设计令牌、稳定性、公式、几何、交互形态、移动端与完整 renderer 示例；其中普通数据图协议以统一路由和 `mode-echarts.md` 为准。

## 适用范围

用于必须通过操作或播放才能理解的内容：参数变化、函数变换、算法步骤、状态机、物理过程、动态几何、多视图联动，以及基于用户原图的点击讲解、逐步高亮或部件切换。

静态图已足够时不要增加交互。普通精确数据图优先使用原生 ECharts option，不套 HTML。

## 素材形态

- `no_source_asset`：用 HTML/SVG/Canvas 自绘结构。
- `preserve_user_image`：将用户原图作为 `<img>` 底图，在上方叠加 SVG/DOM 交互层；不得改变原图证据。
- `use_structured_data`：可在交互中绘制定量反馈；需要标准数据图时可嵌入 ECharts，但只限交互确实需要 DOM 或多视图联动的场景。
- `reference_user_image` 不等于交互底图；若用户要重绘，走生成式配图。

## 输出与 HTML 约束

- 使用 `html type="renderer"`，首块外层为 `<html style="margin:0;padding:0;">` 和透明 div。
- 不使用 DOCTYPE、head、body、TEXT；CSS 全部内联，除非极少量伪元素必须使用 style。
- 根容器自然撑高；禁止 `100vh`、`height:100%`、根固定大高度和依赖视口的 `vh/vw/vmin/vmax`。
- 脚本用 IIFE + try/catch + DOM 判空，直接执行，不监听 `DOMContentLoaded`。
- 优先纯 HTML/SVG/Canvas；外部库只有在明显减少复杂度时使用，并提供加载失败提示或静态替代。
- 地图库和地图组件一律禁止。

## 交互选择

- 连续参数 → slider，并实时显示数值和单位。
- 几何或向量变化 → 拖拽锚点，同时保持题设约束。
- 算法/证明步骤 → 上一步、下一步、播放、暂停、重置。
- 多模式对比 → 按钮组或 select，明确当前状态。
- 原图部件讲解 → 可点击区域 + 外部说明区；不要把长文字全压在图上。
- 多视图关系 → 同步高亮并说明联动方向。

## 必须满足

- 交互元素不小于 44×44px，支持 click/tap；hover 只作桌面增强。
- 动画可暂停、可重置，不持续高频空转。
- 操作后提供即时视觉变化和文字/数值反馈。
- 控件不覆盖核心图形；窄屏时上下排列而非横向挤压。
- 初始静态状态就能理解主结论；JS 失败时至少显示文字说明、底图或静态结构。
- 几何图示保持垂直、平行、相切、中点等约束；无法稳定保持时改为静态 SVG。
- 用户原图参与时，保持比例，叠加层与原图同一舞台坐标系。
