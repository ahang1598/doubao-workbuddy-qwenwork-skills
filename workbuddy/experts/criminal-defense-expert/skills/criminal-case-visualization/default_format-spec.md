# 排版格式 — 刑事案件可视化

> **I-Practical 排版参数表（§17.18 第三层）**

## 1. 字体

| 参数 | 值 | 说明 |
|------|----|------|
| 字体栈 | `"PingFang SC", "Microsoft YaHei", SimSun, FangSong, "Noto Sans SC", serif` | 优先使用系统字体，含宋体/仿宋 fallback |
| 字号5级 | xl:20px / lg:16px / base:14px / sm:12px / xs:11px | 标题/正文/注释三级差 |
| 法条引用字体（律师版） | 楷体 10pt 灰色 | 法条编号用 `〔刑诉法第XX条〕` 包裹 |

## 2. 行距

| 参数 | 值 | 适用场景 |
|------|----|---------|
| 正文行距 | 1.65 | 律师版标准 |
| 家属版行距 | 1.8 | 家属版适度加大，便于非专业人士阅读 |
| 标题行距 | 1.35 | 页面标题、区块标题 |
| 表格行距 | 1.4 | 数据表格 |
| 注释行距 | 1.5 | 免责声明、页脚 |

## 3. 页面

| 参数 | 值 |
|------|-----|
| 纸型 | A4 portrait |
| 打印页边距 | top:15mm, left/right/bottom:20mm |
| 最大宽度 | 1100px（.page-container，v3.0.0 从 820px 提升 34%） |
| 基线网格 | 8px（所有margin/padding对齐4px/8px倍数） |

## 4. 色板

### 4.1 五色语义色板

| 颜色 | light | medium | dark | text | 用途 |
|------|-------|--------|------|------|------|
| primary（深蓝） | `#eff6ff` | `#3b82f6` | `#1e3a8a` | `#ffffff` | 页眉分隔线、表格表头、图表标题 |
| accent（灰绿） | `#dcfce7` | `#22c55e` | `#166534` | — | 家属版分析区、律师确认区 |
| warning（琥珀） | `#fffbeb` | `#d97706` | `#92400e` | — | 免责声明顶部、非预测标注 |
| danger（红） | `#fef2f2` | `#dc2626` | `#991b1b` | — | L2免责声明左边框、Mermaid错误提示 |
| info（灰蓝） | `#f8fafc` | `#64748b` | `#1e293b` | — | 图例背景、源码折叠区背景、页眉/页脚 |

### 4.2 灰度系统

| 灰度 | 色值 | 用途 |
|------|------|------|
| gray-50 | `#f8fafc` | 分析区背景 |
| gray-100 | `#f1f5f9` | 页眉/页脚分隔线 |
| gray-200 | `#e2e8f0` | 表格边框、区块分隔线、图表容器边框 |
| gray-300 | `#cbd5e1` | 页脚文字、版本水印、按钮边框 |
| gray-400 | `#94a3b8` | 工具栏文字、元信息、注释文字 |
| gray-500 | `#64748b` | 副标题、图表说明、工具栏按钮文字 |
| gray-700 | `#334155` | 正文文字 |
| gray-900 | `#0f172a` | 页面标题、区块标题 |

## 5. Mermaid主题

| 主题 | 适用 | primaryColor | primaryTextColor | primaryBorderColor | lineColor | secondaryColor | tertiaryColor |
|------|------|-------------|-----------------|-------------------|-----------|---------------|--------------|
| 法律 | 律师版 | `#f8fafc` | `#1e293b` | `#6b7280` | `#6b7280` | `#f1f5f9` | `#f8fafc` |
| 商务 | 家属版 | `#f0f9ff` | `#0c4a6e` | `#0284c7` | `#0284c7` | `#e0f2fe` | `#f0f9ff` |

> fontSize 统一为 `'18px'`（v3.0.0 从 14px 提升，含 gantt 独立字号 14px）

## 6. 受众差异化排版

| 元素 | 律师版 | 家属版 |
|------|--------|--------|
| 页面标题后缀 | `——律师版` | `——家属版` |
| 正文字号/行高 | 14px / 行高1.65 | 14px / 行高1.8 |
| 法条引用 | `〔刑诉法第XX条〕`楷体10pt灰色 | 脚注通俗解释（不标法条编号） |
| 图表标题 | `图N-type：专业名称` | `图N：通俗名称` |
| 免责声明 | 页脚一行（L1） | 首页顶部黄色警告栏（family-disclaimer-top）+ 页脚（L2） |
| Mermaid主题 | 法律（灰色系） | 商务（蓝色系） |
| 律师确认区 | 不显示 | 末尾显示含签字确认区 |
| 辩护策略矩阵 | 显示 | 不显示 |
| 非预测标注 | 含"可能性范围，非预测结果" | 含"可能范围"+非预测声明 |

## 7. 图表渲染规范

| 规范项 | 要求 |
|--------|------|
| 渲染引擎 | mermaid.js v10 CDN |
| 降级备选 | 源码折叠区可复制到 mermaid.live |
| 表格渲染 | HTML `<table class="data-table">` |
| 错误处理 | `.mermaid-error.visible` + parseError + load检测 |
| 无JS降级 | `<noscript>` 提示含 mermaid.live 链接 |
| Mermaid容器 | `.mermaid-wrap` 包裹 `.mermaid`，紧跟 `.mermaid-error` div |
| 源码折叠 | `<details class="source-section">`，打印隐藏 |

## 8. 打印适配

| 规则 | 实现 |
|------|------|
| A4纸张 | `@page { size: A4 portrait; margin: 15mm 20mm; }` |
| 隐藏工具栏 | `.toolbar { display: none !important; }` |
| 隐藏源码折叠区 | `.source-section { display: none !important; }` |
| 去除图表边框 | `.mermaid-wrap { border:none; background:#fff; }` |
| 保留页眉页脚 | `.doc-header-info` / `.doc-footer` 保留 |
| 版本水印降透明度 | `.template-version-watermark { opacity:0.4; color:#c0c0c0; }` |
| 斑马纹去色 | `.data-table tbody tr:nth-child(even) { background:transparent; }` |

## 9. HTML模板 HARD_BLOCK 约束

| 约束 | 说明 |
|------|------|
| 模板骨架 | `assets/html-template.html`（唯一权威） |
| CSS 锁定 | `<!-- HARD_BLOCK:DONT_MODIFY_START -->...<!-- HARD_BLOCK:DONT_MODIFY_END -->` 区间内 CSS 不可修改 |
| CSS 参考副本 | `assets/html-style.css`（CSS修改需同步更新） |
| 内容插槽 | 10 个 `<!-- CONTENT_SLOT:xxx -->` 占位符 |
| LLM 职责 | 填充 SLOT + 替换 themeVariables，不修改 HARD_BLOCK 内任何 CSS |
| X1-X10 | 10 条禁用行为清单（见 output-spec.md §7.3） |

## 10. Mermaid 渲染健壮性规范（v2.2.0 新增，v3.0.0 最新）

> 本节是 v2.2.0 关键变更，v3.0.0 最终版本（渲染参数修正 + CSS 容器放宽 + 信息密度控制）。生成 Mermaid 代码前必须按本节执行。

### 10.1 流程图布局策略

| 节点数 | 方向 | subgraph | 备注 |
|--------|------|---------|------|
| ≤5 | `graph TD` | 不需要 | 单列 |
| 6-8 | `graph LR` + 3 subgraph | 强制分段 | 横向布局 |
| 9-12 | `graph LR` + 4-5 subgraph | 强制分段 | 需缩放控件 |
| >12 | 拆为多图 | 必须 | 单图节点≤12 |

**禁止**：≥6 节点用 `graph TD` 单列布局（导致画布拉长至 3000+px）。

### 10.2 Gantt 时间跨度（v3.0.0 强化：section ≤ 2）

> **强制规范**（与 chart-specifications.md §3.0 一致）：详细三档决策与双图表架构见 `chart-specifications.md` §3.0 + §3.0.1 + §3.0.2。

| 跨度档位 | 适用范围 | 图表架构 | axisFormat | section 数 |
|---------|---------|---------|-----------|-----------|
| 短档 ≤3 月 | 单阶段 | 单 gantt | `%m-%d` | ≤2 |
| 中档 3-12 月 | 一审全流程 | 单 gantt + `excludes weekends` | `%Y-%m` | ≤2 |
| 长档 >12 月 | 已判决+刑期 | **强制双 gantt**（图 A 强制措施 + 图 B 刑期） | 各自独立 | 各≤2 |

> **v3.0.0 新增**：gantt section ≤ 2（强制措施阶段 + 关键节点，法定期限对比改为 HTML `<table class="data-table">` 注解）。

**长档双图表规则**：
- 输入"已判决"+"刑期 X 年" → **必须**输出图 A 强制措施 + 图 B 刑期执行
- 刑期执行段**禁止**放入图 A
- 刑期执行段**禁止**改用 HTML 表格（v2.2.0 错误做法）
- 两个图表必须在同一 `.chart-block` 内嵌套 `<h5>` 子标题分隔

### 10.3 节点标签字符限制

| 图表 | 单节点行数 | 单节点字符数 | 超出处理 |
|------|-----------|------------|---------|
| case_flow | ≤4 行 | ≤30 字符/行 | 拆分节点 |
| sentencing_path | ≤3 行 | ≤25 字符/行 | 简化 |
| rights_map | ≤2 行 | ≤20 字符/行 | 短词+表格 |
| defense_matrix | 短语 | ≤4 词 | 英文标签+中文表 |
| timeline | 单条 | ≤10 字符 | 简化或拆条 |
| pie | 标签 | ≤20 字符 | 简化 |

### 10.4 渲染失败降级路径

```
Mermaid 渲染失败
  ↓
触发 mermaid.parseError 回调
  ↓
.mermaid-error.visible 显隐激活
  ↓
LLM 读取错误信息
  ↓
尝试自动修复（应用本节规则）
  ↓
仍失败 → 输出源数据表格
  ↓
标注 "图表渲染失败，仅展示源数据"
```

### 10.5 模板必需 Hooks

HTML 模板必须包含：

- `mermaid.parseError` 回调（注册使 `.mermaid-error` 显隐真正生效）
- `window.addEventListener('load')` 后 1.5 秒检测无 SVG 渲染的图表
- 图表缩放按钮（`zoomMermaid()` 函数）
- `.mermaid-wrap` 容器 `max-height: 2400px`（v3.0.0 从 1200px 提升，避免长图表截断）

完整规范见 `chart-specifications.md` §0 和 `workflow-detail.md` Phase 4。
