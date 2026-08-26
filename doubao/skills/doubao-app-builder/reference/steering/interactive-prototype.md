---
name: interactive-prototype
description: 创建具备真实交互的可运行应用原型。触发词：interactive prototype, 交互原型, 可交互原型, 动态原型, 原型演示, 交互演示, working app
metadata:
  display-names:
    zh-CN: 交互原型
    en-US: Interactive Prototype
---

# 交互原型

创建一个完全可交互的原型，具备真实的状态管理和页面切换。用原生 JS 实现动态行为：应用状态放在普通对象（或带 subscribe/notify 的极简 store）里，状态变化时重渲染受影响的 DOM。包含悬停状态、点击交互、表单验证、动画过渡和多步导航流程。用起来要像真正能运行的应用，而不是静态效果图。

## 页内路由（单文件约束）

产物是单个 `index.html`，多「页面」用页内路由实现：每个页面是一个顶层视图容器（如 `<section data-route="detail">`），用 hash 路由（`location.hash` + `hashchange` 监听）切换显示；视图间传参走 hash query（如 `#detail?id=3`），跨会话要保留的状态放 localStorage。不拆多个 HTML 文件，不引入 router 库，不用 `type="module"`。

## 响应式适配

先判断 brief 的目标场景，走不同策略：

**面向终端用户的产品**（官网、营销页、C 端应用、展示型页面）——必须适配移动端。用 `@media (max-width: 768px)` 做断点，375px 宽度下无水平滚动、无内容不可读、无元素互相遮挡：

- **侧边栏**：窄屏默认收起，汉堡按钮切换；展开时 `position: fixed` + 半透明遮罩覆盖内容，不挤压主区域。
- **顶部导航**：导航项超出视口宽度时折叠为汉堡菜单，不允许换行堆叠或水平溢出。
- **网格与卡片**：用 CSS Grid `auto-fit` / `minmax()` 或 Flexbox `flex-wrap`，窄屏自动堆叠为单列；卡片内数字和文字不因容器变窄而截断。
- **固定定位元素**：浮动按钮、悬浮面板等 `position: fixed/absolute` 元素用 `right: 16px` 等安全边距约束在视口内，不允许超出屏幕边缘。

**面向桌面的场景**（管理后台、内部工具、数据密集型仪表盘）——不需要重排为移动端布局，但必须设 `min-width`（通常 1024px–1200px），窄于此宽度时整体水平滚动，而不是让布局被挤压变形。

brief 未指明时默认按终端用户产品处理。
