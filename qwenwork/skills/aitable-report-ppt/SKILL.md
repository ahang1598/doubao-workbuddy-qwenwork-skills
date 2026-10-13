---
name: aitable-report-ppt
displayName: AI表格汇报PPT
name_en: aitable-report-ppt
description: |
  从钉钉 AI 表格、多维表、数据表或已有 Word/PPT/HTML 生成内容先确认、可追溯、可下钻、可导出 PDF 的单文件 PPT 式可视化报告（默认固定 16:9 演示稿），图表可下钻回钉钉原始记录。 当用户提到把 AI 表格做成 PPT、汇报 PPT、管理报告、可视化报告、HTML 报告、仪表盘、数据汇报页面、下钻报告、打印报告，或只说"做个汇报PPT""做个汇报页面""把这个表可视化""生成仪表盘"时使用； 也用于把 PPT 转为动画 HTML 或增强已有 HTML 演示。内置完整主题库和演示引擎，不依赖其他 skill。
description_en: |
  Turn DingTalk AI-table data (or existing Word/PPT/HTML) into a single-file, PPT-style visual report on a fixed 16:9 stage — content confirmed before styling, every number traceable, charts drill down to source records, exportable to PDF. Use when the user asks for a PPT, dashboard, management report, HTML report, presentation-style webpage, drill-down report, or printable report from table data; also converts PPT to animated HTML or enhances existing HTML presentations.
argument-hint: AI 表格链接或数据文件（CSV/JSON/XLSX）
install_source: official
install_method: download
skill_id: official_T1Wt3utj
enabled_at: 1791893809835
version: 1.1.0
name_zh: AI表格汇报PPT
---

# AI表格汇报PPT

把业务数据变成一份先确认内容、再正式设计，且能汇报、追问和核验的 HTML，而不是直接把原始表格"画得好看"。本 skill 是单体能力包：AI 表格读取、数据画像、指标证据、内容蓝图、图表与下钻、46 套内置视觉方向、自定义主题、16:9 演示、PPT 转换、PDF/部署和自动验收均在本目录内完成。

运行环境需要 Python 3 和 Node.js；实时读取钉钉 AI 表格需要已登录的 DWS CLI，也可以改用导出的 CSV/JSON；自动化 HTML 验收需要 Chromium 兼容浏览器。本 skill 不依赖其他 skill。

## 核心原则

1. **真实性优先于完整感。**没有来源的数据、标签、职级关系、原因或结论不要生成；显示"暂无依据"比补造内容更可靠。
2. **先设计验证，再设计页面。**每项指标、图表、结论和交互在进入页面前都要明确验证方式。
3. **汇总必须能追到记录。**只要用户权限允许，默认建立"总览 → 分组 → 记录 → 钉钉原始明细"的链路。
4. **先确认讲什么，再确认长什么样。**用户只需确认故事主线和页面序列；数字正确性由程序验证。
5. **主题预览只解决审美选择。**预览不设计、不展示、不验收下钻，也不生成完整报告。
6. **只生成需要的形态。**默认生成固定 16:9 演示稿；连续阅读长页只有用户明确要求时才启用。
7. **默认只读。**写表、发布、公开分享、上传或权限变更必须有用户明确授权。
8. **确认必须进入宿主等待态。**优先调用宿主原生结构化提问工具并停止执行。
9. **统一运行时，只统一逻辑不统一长相。**聚合、成员过滤、图表挂载、舞台与键盘等正确性攸关逻辑由内置 `assets/components/report-runtime.js` 提供，主题通过显式挂载协议接入，不强制共享页面 DOM 或视觉组件；禁止在页面里重写这些逻辑的第二份实现。
10. **runtime 不给自己打分。**验收期望值由页面外的 Python oracle 独立计算；页面的 `verificationSnapshot()` 只报告观察值，是否通过只由 `validate_visual_report.js` 判定。

全流程底线约束见 `references/reporting/quality-redlines.md`。

## 能力模式

- **A：AI 表格 → 可视化演示/报告**：主模式，执行完整数据、证据、内容确认和主题确认流程。
- **B：已有数据文件 → 可视化报告**：CSV/JSON/XLSX 已提供，跳过 DWS 定位但保留数据画像与验证。
- **C：PPT/PPTX → 动画 HTML**：读取 `references/presentation/frontend-slides-engine.md` 的 PPT Conversion 流程。
- **D：增强已有 HTML**：保留原内容、图表和交互，按内置演示引擎的 Enhancement 规则修改并回归验证。
- **E：纯演示稿**：使用内置完整 Frontend Slides 流程。

## 资源路由

按当前阶段完整读取所列文件，不要一次性加载所有资源：

| 阶段 | 必读资源 |
|---|---|
| AI 表格定位和读取 | `references/reporting/aitable-access.md` |
| 数据事实、指标和结论 | `references/reporting/evidence-and-metrics.md` |
| 生成报告规格 | `references/reporting/report-spec.md` |
| 核心框架与内容确认 | `references/reporting/content-blueprint.md` |
| 任何需要用户决定的关口 | `references/reporting/confirmation-interaction.md` |
| 正式报告下钻、权限和脱敏 | 用户选定主题后读取 `references/reporting/drilldown-and-privacy.md` |
| 风格预览选择 | `references/presentation/bold-template-pack/selection-index-lite.json` + `references/presentation/STYLE_PRESETS.md` |
| 风格预览生成、演示、PPT、导出 | `references/presentation/frontend-slides-engine.md`，再按其中路由读取同目录资源 |
| 选中 Bold 模板后 | 该模板的 `preview.md`（预览用）或 `design.md`（正式生成用），从 `selection-index-lite.json` 的 `preview_md` 路径定位 |
| 最终验收 | `references/reporting/validation.md` |
| 聚合/过滤/排序/空值的精确语义 | `references/reporting/semantics.md` |
| 质量红线（随时参考） | `references/reporting/quality-redlines.md` |

## 标准工作流

### 阶段 0：确认输入与交付边界

优先从用户现有信息中提取，不重复提问。只有无法推断且会改变结果时，通过宿主原生结构化提问工具集中确认。详见 `confirmation-interaction.md` 的"输入边界确认"。

### 阶段 1：读取和盘点数据

AI 表格链接按 `references/reporting/aitable-access.md` 处理。本 skill 已内置读取脚本，不调用其他 skill：

```bash
python3 scripts/fetch_dingtalk_aitable.py \
  --url '<AI表格URL>' \
  --output-dir <snapshot-dir>
```

**千问办公硬约束：**优先执行上述内置脚本，不得先由模型手工拼接多组 DWS 命令"试接口"。脚本不可用时才按 `aitable-access.md` 的人工命令路径执行，并先读取 leaf Schema/Help。禁止使用不存在的 `--max-page-size`、超过 100 的 `--limit`，或把 `contains` 写成过滤操作符；全量记录固定使用 `--limit 100 --all --page-limit 0`。

然后运行数据画像：

```bash
python3 scripts/profile_aitable_snapshot.py --records <records.json> --fields <fields.json> --output <profile.json>
```

错误处理和降级规则见 `aitable-access.md`。

### 阶段 2：建立证据台账

按 `references/reporting/evidence-and-metrics.md` 将展示内容分成 `data_fact` / `rule_calculation` / `human_conclusion` / `ai_inference` 四类。每项必须包含来源、公式、验证方式；无法映射来源的标记为阻塞项。

### 阶段 3：生成报告规格

按 `references/reporting/report-spec.md` 创建 `report-spec.json`。运行：

```bash
python3 scripts/validate_report_spec.py <report-spec.json>
```

### 阶段 4：生成核心框架与内容蓝图

完整读取 `references/reporting/content-blueprint.md`。从已验证的事实规格生成 `content-blueprint.json`。

**确认环节的输出分两层：**

**第一层：故事线总览（默认展示，用户确认的唯一对象）**

用户确认的是"讲什么、怎么讲"，不是数字对不对。呈现时只展示：

- 一句话核心观点
- 页面序列：只有编号和标题，标注叙事节奏（开场/关键发现/收尾）
- 预计页数和交付形态

如果宿主支持可视化组件（如 `show_widget`），用编号卡片或流程图展示页面序列，让用户一眼看出整体结构。纯文本宿主用编号列表。

**第二层：按需查阅（不默认展示）**

完整数据保存在 `content-blueprint.json` 中，包括每页的管理问题、图表类型、关键数字、来源、下钻入口。用户说"展开看看"或"看具体内容"时再呈现。

**确认时不展示：**数据口径、下钻能力说明、验证方式、空值处理——这些由程序自动验证。

运行验证后发起确认：

```bash
python3 scripts/validate_content_blueprint.py content-blueprint.json
```

按 `confirmation-interaction.md` 发起"内容蓝图确认"并进入等待态。用户明确批准后保存 `content-approval.json`。

### 阶段 5：生成三套风格预览

读取 `references/presentation/bold-template-pack/selection-index-lite.json`（精简索引，只含匹配维度）和 `references/presentation/STYLE_PRESETS.md`。完整索引 `selection-index.json` 只在 lite 版信息不足时读取。

**密度筛选是硬条件（索引 schema 2.0）。**`modes.presentation.density` 为 `reading-first` 时，候选主题的 `supported_density_modes` 必须包含 `reading-first`（等价于 `content_capacity` 为 `high` 或 `medium-high`），34 套中有 13 套满足。旧的单一 `density` 字段已废弃——它与各模板 `design.md` 的 Density philosophy 在约三分之一的模板上互相冲突，按它选型会选出装不下数据的主题。字段定义见 `bold-template-pack/README.md` 的 Density Fields 一节。

`default_visual_density` 低**不**构成排除理由：它描述的是该主题的默认调性，意味着稀疏构图属于封面、章节和金句页，数据页必须改用该主题自带的密集版式。**禁止把封面式的稀疏构图套到 `reading-first` 报告的每一页。**

**主题的文字配色必须先过对比度。**选中主题后，按该主题在**每种表面**（深色页、浅色卡片）上的实际文字色核对对比度：正文 ≥4.5:1，大字 ≥3:1（"大字"按实显尺寸算，即 1920 画布上普通字 ≥36px、粗体 ≥28px）。深色页上放浅色卡片时，卡片内文字必须换成该表面的深色字，**不能沿用深色页的浅色字**——这是同色系撞车最常见的来源。强调色不豁免：某个颜色在深色底上合格，不等于在浅色卡片上也合格。

默认选三套：一套安全预设、一套 Bold、一套自定义或第二套 Bold。三套预览是三个独立、固定 1920×1080 的单页 HTML。预览规则详见 `frontend-slides-engine.md` 的 Style Discovery。

**多余的高度不许摊给行。**容器装不满时，两种"填满"都判失败：把剩余高度灌进行与行之间（`align-content:space-between`，行距从声明的 gap 撑到几倍），或灌进行框本身（`grid-auto-rows:1fr`，行框撑到内容的三倍高、一行字悬在空框里）。列表用 `align-content:start` 配 `grid-auto-rows:max-content`，多余空间留在末尾即可。想填满就加内容或换版式，不是拉开间距。自带底色或边框的行框（热力图色块、指标卡）豁免——刷了漆的面积是明确的设计意图；但不要靠给空行加底色来绕过，那只是把空白换了个颜色。

**预览必须包含一页真实数据页。**`reading-first` 报告的预览若只有标题页，无法暴露"真实数据塞进去以后有多空、对比度够不够"——必须用蓝图里最密的那一页（图表数或表格行数最多的）真实渲染，否则主题选择关口形同虚设。

这是第二个不可跳过的用户选择关口，只能在内容确认通过后开始。展示预览后按 `confirmation-interaction.md` 发起"主题选择"并进入等待态。

### 阶段 6：设计正式报告信息架构与下钻

只在用户选定主题后读取 `references/reporting/drilldown-and-privacy.md`。规则详见该文件。正式报告使用 `assets/components/standard-drilldown.css` 和 `assets/components/standard-drilldown.js`。

### 阶段 7：生成完整 HTML

先生成独立验算基准（oracle），再运行正式生成门禁：

```bash
python3 scripts/build_verification_oracle.py \
  --snapshot-dir snapshot/ --spec report-spec.json \
  --output verification-oracle.json
python3 scripts/validate_generation_gate.py \
  --spec report-spec.json \
  --blueprint content-blueprint.json \
  --content-approval content-approval.json \
  --design-selection design-selection.json \
  --manifest snapshot/manifest.json \
  --oracle verification-oracle.json
```

生成要求：

- **内联三个运行库**：`assets/vendor/echarts.min.js`、`assets/components/report-runtime.js`、`assets/components/standard-drilldown.js`。在 HTML 中放置 `<!-- INLINE:echarts -->` 等标记后用 `python3 scripts/inline_report_assets.py` 统一内联并取得资源哈希。
- **主题只写 DOM、布局与动画**；图表挂载、下钻绑定、翻页舞台一律调用 runtime 的显式挂载 API（`runtime.mountChart(el, id)` / `runtime.bindDrilldown(el, id)` / `runtime.createDeckController({stage, slides})`），禁止重写聚合、filter_ast、舞台缩放的第二份实现。
- **图表内文字由 CSS 变量控制**：`--chart-axis-font-size`（坐标轴刻度）、`--chart-label-font-size`（数据标签、饼图标签、图例）、`--chart-tooltip-font-size`。取值按 1920 画布尺寸书写，runtime 默认 21px（在 1280 窗口实显 14px）。**不设这些变量就会得到默认值，不会掉进 ECharts 的 12px**——那在缩放后只有 8px。主题可以调高，调低会被验收拦截。
- **图表容器高度不得写死**。主图用 `flex:1` 或显式的大高度（两栏 ≥360px、单栏/全宽 ≥420px，均为 1920 画布尺寸）。固定小高度（如 250px）会在面板里留下大片死空白，验收会失败。
- **文字必须在它实际所处的表面上达标对比度**：正文 ≥4.5:1、大字 ≥3:1（按实显尺寸判定）。深色页里的浅色卡片必须换深色文字，强调色不豁免。
- **可下钻的热力图必须逐格可寻址**：每格要有自己的元素（DOM 或 SVG，标 `data-heatmap-cell`，或 SVG 上带 `data-cell-x`/`data-cell-y`）、自己的热区和自己的双字段 `filter_ast`（如区域 AND 月份）。纯 canvas 每格既无可点元素也无法检查遮挡，且单个字符串 `category` 表达不了二维坐标。**纯展示、不需要下钻的热力图**用 `drilldown_required:false` 显式豁免后可以继续用 canvas——约束的是可寻址性，不是禁用某个渲染库。
- **点击热区必须等于提示热区**。若图表有悬浮提示，其可点击范围必须与提示触发范围一致——不能出现"整列都能悬浮出数值、却只有几像素的点能点开下钻"。折线/散点等小符号图形依赖 runtime 的绘图区级点击映射，不要只依赖 series 自身的点击事件。
- 页面内嵌 `REPORT_FINGERPRINTS`（快照/规格哈希、语义与合同版本、runtime 资源哈希）。
- 默认只生成固定 1920×1080 演示稿；下钻弹窗挂载在舞台之外。
- 基础参考渲染器 `scripts/build_visual_report.py` 是该协议的参考实现（仅 internal 等级），可直接使用或作为主题代码的对照样例。

完整演示能力、PPT 转换、部署和 PDF 导出规则均在 `references/presentation/frontend-slides-engine.md` 中。

### 阶段 8：独立验证

按 `references/reporting/validation.md` 验收。运行：

```bash
node scripts/validate_visual_report.js <report.html> report-spec.json --oracle verification-oracle.json
node scripts/validate_visual_report.js <preview.html> --preview
```

验收先逐项核对页面与 oracle 的版本指纹，任何一项不一致即以 `FINGERPRINT_MISMATCH` 失败（不降级为 warning）；指纹一致后再独立比较 oracle 期望值与页面 `verificationSnapshot()` 观察值。

### 阶段 9：交付与可选发布

交付目录默认包含 `report.html`、`report-spec.json`、`content-blueprint.json`、`content-approval.json`、`design-selection.json`、`verification-oracle.json`、`verification.json`。**`member-keymap.json` 是内部构建产物，禁止进入交付目录**（门禁的 `--delivery-dir` 参数会检查）。发布前必须再次确认。

## 内置完整 Frontend Slides 能力声明

本 skill 内置并保留原 Frontend Slides 的以下完整能力：新建演示、PPT 转换、已有 HTML 增强、12 套安全预设、34 套 Bold 模板、自定义主题、固定 16:9 舞台、动画、编辑模式、部署和 PDF 导出。原项目的 MIT License 位于 `references/presentation/LICENSE`；ECharts 的 Apache License 位于 `assets/vendor/ECHARTS-LICENSE.txt`。
