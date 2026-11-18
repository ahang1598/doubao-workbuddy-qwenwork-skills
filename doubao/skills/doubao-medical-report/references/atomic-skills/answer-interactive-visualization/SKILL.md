---
name: answer-interactive-visualization
description: "用参数、步骤或视图切换揭示有意义的状态和过程。在参数、步骤或有效视图切换能帮助探索实际问题时使用；不为短列表添加无收益的交互。"
metadata:
  version: 1.0.2-visual-value.20261109
---

# 回答中的交互与算法演示

执行时遵守 [SVG 执行与确认边界](../../svg-visualization.md#执行与确认边界)：静态图直接构造 SVG，不以修改绘图脚本为前置；已有工具权限内的临时计算与检查不另发对话授权确认，平台强制审批及浏览器许可仍须遵守。


本包使用 [SVG 共用规范](../../svg-visualization.md)：优先静态 SVG，必要交互通过 HTML 控件更新 SVG。程序化矢量示意替代生成式配图，不调用图片生成或编辑工具、不用 Canvas 或位图回退。宿主无法展示时保留文字和表格。


## 正式交付边界

本轮正式交付只保留一种格式、默认一份成品。内容、图表及说明的位置按原任务和宿主能力处理，不要求将说明、记录或图表合并进文档。配置、底稿、预览及运行依赖继续内部生成和核验，不默认另附下载文件；宿主必需的资源上传/写入照常执行。额外格式、源文件或独立文档仅按用户明确要求提供。保留实际显示/插入及内容核验，不以少交文件代替检查。

用参数、步骤或视图切换揭示有意义的状态和过程。

## 输入与输出

输入：初始状态、变量范围、状态规则、反馈和目标宿主。

交付：可交互演示、即时文字/数值反馈与静态回退。

边界：交互必须增加理解；不把 hover 或装饰动画设为核心答案，不冒充真实 UI 操作结果。

## 生成前先判断收益

先读[可视化取舍](references/visual-value.md)。只有图形能让实际比较、关系、时间间隔或状态变化更清楚，才生成；仅把已有Markdown表格换成卡片、编号列表或等距时间线时，保留原表达。相同数据可以通过有效编码帮助理解，不要求补造新信息。用户明确要求图示时选择有用图形并减少重复正文。

## 执行

1. 先按可视化取舍确认交互带来的实际判断或探索收益，再读取 mode-html-svg.md、renderer-stability-math.md；拖拽/播放/几何/多视图联动再读 renderer-interaction-geometry.md。先验证交互是否揭示新信息。
2. 把输入范围、状态迁移与派生量定义清楚；初始静态状态就能说明核心结论。算法步骤、暂停、重置和边界状态保持一致。
3. 按实际宿主协议实现。原包 renderer 脚本使用 IIFE、try/catch 和 DOM 判空，不等待 DOMContentLoaded；解析错误需在执行前检查，不能依赖 try/catch 捕获。
4. 控件支持 click/tap 和有意义的即时反馈；几何关系由计算保证，拖动只修改自由变量，退化状态阻止或明确提示。
5. 动画可暂停/重置，外部资源失败保留静态内容或可读提示；真实地理需求不在此分支自绘替代地图。

## 工具、宿主与授权

使用前读取 [依赖与交付协议](references/delivery-contract.md)。依赖列的是所需能力，不证明工具已安装、MCP 已连接或当前账号有权限。优先 API、连接器和官方 CLI；浏览器 UI、无头浏览器或截图自动化前，说明必要性并取得用户对当前任务的明确许可。用户已授权的文档操作在其范围内直接完成，不因使用此包而扩大到分享、上传私有素材或联系他人。

## 按需参考

- [mode-html-svg.md](references/mode-html-svg.md)：按执行步骤中的条件读取。
- [renderer-stability-math.md](references/renderer-stability-math.md)：按执行步骤中的条件读取。
- [renderer-interaction-geometry.md](references/renderer-interaction-geometry.md)：按执行步骤中的条件读取。
- [renderer-trigger-design.md](references/renderer-trigger-design.md)：按执行步骤中的条件读取。
- [renderer-output-mobile.md](references/renderer-output-mobile.md)：按执行步骤中的条件读取。
