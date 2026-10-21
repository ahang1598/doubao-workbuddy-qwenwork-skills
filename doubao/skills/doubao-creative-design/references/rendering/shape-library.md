# 图形库协议

本文件负责 HTML 原生图形的选择语义和组合原则；最终实现约束与 HTML 示例以 `../html/coding-rendering.md` 为准。

## 选择原则

- 容器、背景、标签底、进度块：优先 `rect` 或 `round-rect`。
- 节点、头像占位、状态点：按真实语义选择 `circle` 或 `ellipse`。
- 流程判断、结构节点：可用 `diamond`、`triangle`、`hexagon` 等明确几何语义。
- 指向关系和分隔：使用带边框的 DOM、内嵌 SVG `line/path` 或真实字符；实体箭头块可用 DOM／SVG 组合。
- 复杂自由轮廓、撕边、不对称圆角优先使用内嵌 SVG；真实材质使用已核验透明图片，不用随机基础形状冒充。

## 组合协议

- 图形层不烘焙 Coding 文字；卡片、按钮和标签使用同一语义 DOM 容器与真实文本子节点组合。
- 同一组件的圆角、描边、阴影方向和内边距保持一致，并在 最终 HTML 中记录为可复用 token。
- 阴影使用内联 `box-shadow`／`filter`，或由已绑定模板展开的 DOM／SVG 层；不要堆叠随机光晕。
- 比例敏感图形必须保持建议宽高关系；圆和五角星通常使用等宽高。
- 大背景使用较低 z-index，信息和交互提示使用较高 z-index。

## 图形 token

需要复用时在 最终 HTML 中记录：`shape_role`、`implementation`（`dom | inline_svg | verified_image`）、尺寸、圆角／路径、填充、描边、透明度、状态变体、消费者和 z-order。token 是规划层约定；编译 HTML 时必须展开为真实元素及 CSS／内嵌 SVG，不能把 token 名当作未定义的运行时依赖。
