---
name: "patent-figure-drawer"
description: "生成符合国知局标准的专利附图（矢量SVG→300DPI TIFF），支持系统架构图、流程图、信号时序图、硬件同步时序图、雷达图、对比柱状图等10种类型。白底黑线、Arial字体、文字可编辑、无渐变无阴影。当需要生成或重新绘制专利附图时调用。"
allowed-tools: Read, Write, Glob, RunCommand

version: "2.0.1"
---

# 专利附图绘制器

## 一、适用场景

- 交底书撰写完成后需要生成专业附图
- 现有附图不符合国知局标准（彩色/渐变/低分辨率）需要重绘
- 需要补充特定类型附图（如硬件同步时序图、信号流程图）
- PCT国际申请需要双语图注

## 二、国知局附图标准

### 2.1 格式标准

| 项目 | 要求 |
|------|------|
| 纸张 | A4（210mm × 297mm） |
| 分辨率 | ≥300 DPI |
| 色彩 | 黑白或灰度，严禁彩色 |
| 背景 | 纯白色 |
| 线条 | 纯黑色，无渐变、无阴影、无3D效果 |
| 字体 | Arial 或 宋体，字号≥8pt |
| 格式 | 源文件SVG + 提交文件TIFF |

### 2.2 禁止事项

- ❌ 彩色、渐变色、阴影、3D效果
- ❌ 水印、页眉页脚
- ❌ 文字转曲（必须可编辑）
- ❌ 锯齿、模糊
- ❌ 图中包含非必要装饰元素

## 三、支持的附图类型

| 类型 | 适用场景 | 技术方案 |
|------|---------|---------|
| 系统架构图 | 整体模块关系、数据流 | Mermaid → SVG优化 |
| 方法流程图 | 方法步骤、算法流程 | Mermaid → SVG优化 |
| 信号时序图 | 信号处理、信道感知时序 | Mermaid sequenceDiagram |
| 硬件同步时序图 | 微秒级硬件同步触发信号 | 自定义时序图（侵权取证用） |
| 雷达图 | 多维度性能对比 | 自定义SVG雷达图 |
| 对比柱状图 | 实验数据对比 | 自定义SVG柱状图 |
| 趋势曲线图 | 误报率/准确率趋势 | 自定义SVG曲线图 |
| 表格图 | 参数对比表 | SVG表格 |

## 四、绘图工作流

1. **接收需求**：说明书中的"附图说明" + 技术方案要点
2. **确定附图清单**：列出图号、图名、类型
3. **生成SVG源文件**：
   - 架构图/流程图：Mermaid → 优化SVG
   - 数据图表：自定义SVG
   - 时序图：Mermaid sequenceDiagram
4. **合规检查**（逐项检查）：
   - [ ] 白底黑线
   - [ ] 无渐变/阴影/3D
   - [ ] 字体Arial/宋体，≥8pt
   - [ ] 文字可编辑
   - [ ] 线条清晰无锯齿
   - [ ] 图号图注正确
5. **导出TIFF**：300 DPI，A4，LZW无损压缩
6. **质量检查**：放大400%检查线条清晰度

## 五、输出文件

| 文件 | 格式 | 用途 |
|------|------|------|
| 图1_系统架构图.svg | SVG | 源文件，可编辑修改 |
| 图1_系统架构图.tif | TIFF | 国知局提交用 |
| ... | ... | ... |
| 附图清单.md | Markdown | 图号、图名、对应说明书位置 |

## 六、Graphviz 优先策略

复杂架构图优先使用 Graphviz（比Mermaid更专业）：

- 节点对齐更规整
- 边线路由更合理
- 子图嵌套更灵活
- 输出矢量SVG质量更高

## 七、注意事项

- 完成后通过 SendMessage 将附图包（SVG + TIFF + 附图清单）回传主理人
- 所有附图必须可在 Word 中正常显示和编辑
- 硬件同步时序图必须标注微秒级时间刻度，便于侵权取证

## 可选工具与参考文档（使用者按需调用）

> 以下工具和参考文档已集成到本skill目录中，使用者根据需要决定是否调用。不需要就跳过，需要就调用。

### 工具脚本（tools/目录）

| 工具 | 来源 | 用途 | 调用方式 |
|------|------|------|----------|
| `mermaid_render.py` | patent-disclosure-skill | Mermaid图转PNG+DOCX | `python tools/mermaid_render.py -i input.md -o output.md` |
| `plot_templates.py` | nature-figure | 10种科研图表模板（柱状/折线/热力/散点/雷达/分布/森林/面积/图像/网络） | `python tools/plot_templates.py --type bar --data data.csv` |
| `validate_figure.py` | nature-figure | 图表合规校验（DPI/尺寸/配色） | `python tools/validate_figure.py figure.py` |
| `nature_figure_backend.py` | nature-figure | Python/R后端选择与记忆 | `python tools/nature_figure_backend.py get/set` |
| `generate_openrouter_schematic.py` | nature-figure | AI生成机制示意图/图形摘要 | `python tools/generate_openrouter_schematic.py --prompt "..."` |
| `render_flowchart_svg.py` | nature-paper-to-patent | 流程图SVG渲染（专利附图专用） | `python tools/render_flowchart_svg.py --steps "..."` |

### 参考文档（references/目录）

| 文档 | 来源 | 用途 |
|------|------|------|
| `patent-figure-guide.md` | nature-paper-to-patent | 专利附图规范指南 |
| `chart-types.md` | nature-figure | 10种图表类型选择指南 |
| `common-patterns.md` | nature-figure | 常见图表布局模式 |
| `design-theory.md` | nature-figure | 配色/字体/导出设计理论 |
| `figure-contract.md` | nature-figure | 图表契约（结论→证据→类型→导出） |
| `figure-legend-conventions.md` | nature-figure | 图例标注规范 |
| `template-catalog.md` | nature-figure | Python CSV模板目录 |
| `qa-contract.md` | nature-figure | 交付前QA检查清单 |
| `asset-adaptation.md` | nature-figure | 模板适配与数据映射 |
| `backend-selection.md` | nature-figure | Python/R后端选择决策 |
| `nature-2026-observations.md` | nature-figure | Nature 2026版面观察 |
| `tutorials.md` / `demos.md` | nature-figure | 教程与示例 |
| `api.md` | nature-figure | Python调色板和辅助API |
| `r-workflow.md` / `r-template-index.md` | nature-figure | R语言工作流和模板索引 |
| `openrouter-image-generation.md` | nature-figure | OpenRouter AI生图路由 |

### 静态资源（assets/目录）

| 资源 | 说明 |
|------|------|
| `chart-atlas/` | 10种图表类型示例图（atlas-01到atlas-10） |
| `gallery/` | 5张Nature级别科研图示例 |

### 静态层文档（references/static/）

| 文档 | 用途 |
|------|------|
| `core/contract.md` | 图表契约核心规则 |
| `core/stance.md` | 默认操作立场 |
| `fragments/backend/python.md` | Python后端快速入门 |
| `fragments/backend/r.md` | R后端快速入门 |
