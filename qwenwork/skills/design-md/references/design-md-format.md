# DESIGN.md 格式说明

每个 DESIGN.md 遵循 Google Stitch DESIGN.md 格式，包含以下 9 大章节。AI Agent 在生成 UI 时应逐章节解读并应用。

## 1. Visual Theme & Atmosphere（视觉主题与氛围）

定义整体设计哲学、情绪和密度。

**生成 UI 时**：确定页面的整体基调（暗色/亮色、密集/稀疏、严肃/活泼），作为所有后续决策的基础。

## 2. Color Palette & Roles（色彩体系与角色）

提供语义化颜色名 + HEX 值 + 功能角色。

**生成 UI 时**：
- 直接使用文档中的精确 HEX 值，不要近似替代
- 按语义角色使用颜色（primary 用于 CTA、background 用于底色等）
- 注意区分 light/dark 模式的颜色映射

## 3. Typography Rules（排版规则）

定义字体族、完整的字号层级表（h1-h6、body、caption 等）。

**生成 UI 时**：
- 使用指定的字体族（含 fallback）
- 严格遵循字号层级，不要自行发明中间值
- 注意 font-weight、line-height、letter-spacing 等细节

## 4. Component Stylings（组件样式）

定义按钮、卡片、输入框、导航栏等组件的具体样式和状态（default/hover/active/disabled）。

**生成 UI 时**：
- 按钮的圆角、内边距、字号必须与文档一致
- 实现所有交互状态（hover、focus、active）
- 卡片的阴影、边框、内边距按文档设定

## 5. Layout Principles（布局原则）

定义间距比例尺、网格系统、留白哲学。

**生成 UI 时**：
- 使用文档定义的间距比例（如 4px 基准的倍数）
- 容器最大宽度、内边距按文档设定
- 遵循留白哲学（宽松 vs 紧凑）

## 6. Depth & Elevation（深度与层级）

定义阴影系统、表面层级区分。

**生成 UI 时**：
- 使用文档中定义的 box-shadow 值
- 按层级关系设置 z-index 和阴影深度
- 注意表面颜色的微妙差异（如 surface-0 vs surface-1）

## 7. Do's and Don'ts（设计护栏）

明确的设计规范和反模式。

**生成 UI 时**：
- 这是最重要的约束章节，必须严格遵守
- Don'ts 中列出的模式绝对不能出现在生成的代码中
- Do's 中的模式应主动应用

## 8. Responsive Behavior（响应式行为）

定义断点、触摸目标尺寸、折叠策略。

**生成 UI 时**：
- 使用文档定义的断点值
- 移动端触摸目标不小于文档规定的最小尺寸
- 导航栏、网格等在不同断点的折叠方式

## 9. Agent Prompt Guide（Agent 提示指南）

提供快速颜色参考和即用型 prompt。

**生成 UI 时**：
- 可直接使用其中的 prompt 模板
- 快速颜色参考表可作为编码时的速查
