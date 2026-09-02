# HTML 输出排版规范

> 本文件定义 criminal-interrogation-analysis 技能 HTML 输出的完整排版规范。
> 严肃度：**I-Practical**（内部级），遵循 `base/rule/format-html/format/html-spec.md` §19。
> 视觉方案：**C-现代轻量**（BCG 风格：青灰 `#005F73` + 暖橙 `#EE9B00`）。
> 双轨原则：HTML 不是对 Markdown 的重新排版，而是在生成阶段直接按 HTML 结构输出，内容与 Markdown O1 完全一致。

---

## 目录

- [1. 严肃度参数](#1-严肃度参数)
- [2. 七色语义色板](#2-七色语义色板)
- [3. 页面结构骨架](#3-页面结构骨架)
- [4. 侧栏导航规范](#4-侧栏导航规范)
- [5. 十层表格视觉化规则](#5-十层表格视觉化规则)
- [6. 信息卡片规范](#6-信息卡片规范)
- [7. 风险标记规范](#7-风险标记规范)
- [8. 深度模式折叠映射](#8-深度模式折叠映射)
- [9. 打印适配参数](#9-打印适配参数)
- [10. 占位符清单](#10-占位符清单)
- [11. 降级输出规则](#11-降级输出规则)

---

## 1. 严肃度参数

| 参数 | 值 | 来源 |
|------|-----|------|
| 严肃度级别 | **I-Practical** | 内部产物，允许 Emoji/折叠/卡片 |
| 视觉方案 | **C-现代轻量**（BCG 风格） | `html-spec.md` §19.5 |
| 主色 | `#005F73`（青灰） | 标题/分隔线/表头/关键标记 |
| 强调色 | `#EE9B00`（暖橙） | 风险标记/警告/信息卡片 accent |
| @page margin | `2.0cm 1.5cm 1.5cm 3.0cm` | I-Practical 标准（左侧留 3cm 装订边距） |
| body font | `微软雅黑, 11pt` | I-Practical 标准 |
| line-height | `1.6`（屏幕）/ `1.8`（打印） | 增强可读性 |
| article max-width | `auto` | I-Practical 不限制 |
| 允许元素 | Emoji 风险标记 / 可折叠区域 / 任务清单 / 信息卡片 | `html-spec.md` §19 |

## 2. 七色语义色板

> I-Practical 级别采用 7 色体系，覆盖十层分析的全部视觉信号。

| 颜色名 | Hex | 用途 | 使用场景 |
|--------|-----|------|---------|
| **primary-dark** | `#005F73` | 主色-深 | 大标题/一级分隔线/表头背景/导航选中 |
| **primary-light** | `#F0F7F8` | 主色-浅 | 信息卡片背景/斑马纹偶数行 |
| **accent-orange** | `#EE9B00` | 强调橙 | 风险标记/警告图标/信息卡片 accent border |
| **accent-orange-light** | `#FFF8EE` | 强调橙-浅 | 风险行高亮背景 |
| **success-green** | `#0A6E42` | 通过绿 | 印证 ✅ / 合规 / 一致 / 稳定 / 趋势下降 |
| **success-green-light** | `#EDF7F0` | 通过绿-浅 | 印证行/合规行/一致行背景 |
| **warning-amber** | `#D97706` | 警告琥珀 | 部分印证 ⚠️ / 瑕疵 / 部分一致 / 中等风险 |
| **warning-amber-light** | `#FFFBEB` | 警告琥珀-浅 | 瑕疵行/部分一致行背景 |
| **danger-red** | `#C53030` | 危险红 | 无印证 ❌ / 违法 / 矛盾 / 高风险 / 趋势上升 |
| **danger-red-light** | `#FFF5F5` | 危险红-浅 | 违法行/矛盾行/高风险行背景 |
| **neutral-gray** | `#64748B` | 中性灰 | 辅助文字/页码/页脚/置信度标注 |
| **neutral-light** | `#F8FAFC` | 中性灰-浅 | 斑马纹奇数行/折叠区背景 |
| **border-gray** | `#E2E8F0` | 边框灰 | 表格分隔线/卡片边框 |
| **text-dark** | `#1A202C` | 正文黑 | 正文文字 |

## 3. 页面结构骨架

```
┌─────────────────────────────────────────────────────┐
│  toolbar（屏幕可见/打印隐藏）          [打印] [折叠]    │
├──────────┬──────────────────────────────────────────┤
│          │  page-header                              │
│          │  讯问笔录深度分析报告                        │
│  side-   │  案件信息 / 笔录清单 / 分析参数              │
│  nav     ├──────────────────────────────────────────┤
│  固定    │  section-block × 10                        │
│  左侧    │  第1层: 供述演变轨迹分析                     │
│  10层    │  第2层: 供述×客观证据精确印证矩阵             │
│  目录    │  第3层: 翻供层次化分析                       │
│          │  第4层: 讯问语境还原与违法线索识别             │
│          │  第5层: 同步录音录像×笔录内容对照              │
│          │  第6层: 多人供述交叉印证                     │
│          │  第7层: 隐性诱供/指供模式识别                 │
│          │  第8层: 供述可采性法律评估                    │
│          │  第9层: 供述→辩护策略系统映射                 │
│          │  第10层: 动态变化风险评估                    │
│          ├──────────────────────────────────────────┤
│          │  结论与建议                                 │
│          │  律师必检清单                               │
│          │  免责声明                                   │
│          │  页脚 + 版本水印                            │
└──────────┴──────────────────────────────────────────┘
```

### 3.1 侧栏导航

- **宽度**：240px 固定
- **位置**：`position:fixed`，左侧贴边
- **内容**：10 层锚点链接 + 结论与建议 + 律师必检清单
- **激活态**：当前可视层高亮（`#F0F7F8` 背景 + `#005F73` 左边框）
- **打印**：`display:none` 隐藏

### 3.2 主内容区

- **左边距**：`margin-left:256px`（侧栏 240px + 16px 间距）
- **每层包装**：`<section id="layer-N">` 锚点
- **层标题**：`<h2>` + 分隔线 + 层摘要

## 4. 侧栏导航规范

```html
<nav style="position:fixed;left:0;top:0;width:240px;height:100vh;overflow-y:auto;
  background:#F8FAFC;border-right:1px solid #E2E8F0;padding:16px 0;
  font-family:'微软雅黑',sans-serif;font-size:11pt;z-index:100;">
  <div style="padding:8px 16px;font-weight:bold;color:#005F73;font-size:13pt;
    border-bottom:1px solid #E2E8F0;margin-bottom:8px;">
    报告导航
  </div>
  <a href="#layer-1" style="display:block;padding:6px 16px;color:#1A202C;
    text-decoration:none;border-left:3px solid transparent;">
    第1层：供述演变轨迹
  </a>
  <!-- ... 第2~10层 ... -->
  <a href="#conclusion" style="display:block;padding:6px 16px;color:#1A202C;
    text-decoration:none;border-left:3px solid transparent;">
    结论与建议
  </a>
  <a href="#checklist" style="display:block;padding:6px 16px;color:#1A202C;
    text-decoration:none;border-left:3px solid transparent;">
    律师必检清单
  </a>
</nav>
```

## 5. 十层表格视觉化规则

### 5.1 通用表格规范

| 元素 | 样式 |
|------|------|
| `<table>` | `width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;` |
| `<thead>` | `background:#005F73;color:#fff;font-weight:bold;` |
| `<th>` | `padding:8px 10px;text-align:left;white-space:nowrap;` |
| `<td>` | `padding:7px 10px;border-bottom:1px solid #E2E8F0;` |
| 斑马纹 | 偶数行 `background:#F8FAFC` |

### 5.2 各层行级着色规则

#### 第1层：供述演变轨迹分析

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 演变类型 = "稳定" | `row-stable` | 无额外着色 |
| 演变类型 = "渐变" | `row-gradient` | `#FFF8EE` |
| 演变类型 = "突变" | `row-mutation` | `#FFF5F5` |
| 演变类型 = "翻供" | `row-recant` | `#FFF5F5` + 粗体 |

#### 第2层：印证矩阵

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 印证状态 = ✅印证 | `row-confirmed` | `#EDF7F0` |
| 印证状态 = ⚠️部分印证 | `row-partial` | `#FFFBEB` |
| 印证状态 = ❌无印证 | `row-missing` | `#FFF5F5` |
| 有供无证危险区 | `row-risk-high` | `#FFF5F5` + 左边框 `3px solid #C53030` |
| 有证无供危险区 | `row-risk-medium` | `#FFFBEB` + 左边框 `3px solid #D97706` |

#### 第3层：翻供分析

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 可信度 = 高 | `row-cred-high` | `#EDF7F0` |
| 可信度 = 中 | `row-cred-medium` | `#FFFBEB` |
| 可信度 = 低 | `row-cred-low` | `#FFF5F5` |
| 本案适用 = 是 | 粗体 + icon 标记 | `font-weight:bold` |

#### 第4层：程序合规

| 条件 | `<td>` 内联着色 | 含义 |
|------|---------------|------|
| 合规 | `background:#EDF7F0;color:#0A6E42;padding:2px 6px;border-radius:2px;` | 绿色标签 |
| 瑕疵 | `background:#FFFBEB;color:#D97706;padding:2px 6px;border-radius:2px;` | 琥珀标签 |
| 违法 | `background:#FFF5F5;color:#C53030;padding:2px 6px;border-radius:2px;` | 红色标签 |

#### 第5层：录音录像对照

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 差异类型 = "选择性记录" | `row-selective` | `#FFF8EE` |
| 差异类型 = "概括性记录" | `row-summary-type` | `#FFFBEB` |
| 差异类型 = "诱供指供" | `row-coercion` | `#FFF5F5` |
| 差异类型 = "时间不一致" | `row-time-diff` | `#F0F7F8` |
| 辩护价值 = 高 | `row-defense-high` | 粗体 + 左边框 `3px solid #0A6E42` |

#### 第6层：多人交叉印证

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 一致性 = "一致" | `row-consistent` | `#EDF7F0` |
| 一致性 = "部分一致" | `row-semi-consistent` | `#FFFBEB` |
| 一致性 = "矛盾" | `row-contradiction` | `#FFF5F5` |
| 高度一致警示 | `row-high-consistency-alert` | `#FFF5F5` + 粗体 + 🔴 icon |

#### 第7层：诱供识别

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 模式 = "信息注入型" | `row-info-injection` | `#FFF5F5` |
| 模式 = "渐进修正型" | `row-gradual-correction` | `#FFFBEB` |
| 模式 = "模板雷同型" | `row-template` | `#FFF8EE` |
| 模式 = "威胁暗示型" | `row-threat` | `#FFF5F5` + 左边框 `3px solid #C53030` |

#### 第8层：可采性评估

| 条件 | `<tr>` class | 行背景色 |
|------|-------------|---------|
| 法律后果 = "应当排除" | `row-exclude` | `#FFF5F5` + 粗体 + 左边框 `3px solid #C53030` |
| 法律后果 = "瑕疵需补正" | `row-fixable` | `#FFFBEB` |
| 灰色地带 | `row-gray-zone` | `#FFF8EE` |

#### 第9层：策略映射

| 行背景 | 无特殊着色，使用斑马纹。策略表正常表格样式。 |

#### 第10层：动态风险

| 条件 | `<td>` 内联着色 | 含义 |
|------|---------------|------|
| 趋势 = "上升" | `#C53030` + `🔴` | 风险上升 |
| 趋势 = "平稳" | `#D97706` + `🟡` | 风险平稳 |
| 趋势 = "下降" | `#0A6E42` + `🟢` | 风险下降 |

## 6. 信息卡片规范

> 遵循 `html-spec.md` §19.5 I-Practical 信息卡片，打印携带场景用较厚 padding。

```html
<div style="background:#F0F7F8;border-radius:6px;padding:1em 1.2em;margin:0.8em 0;
  border-left:4px solid #005F73;">
  <p style="font-family:'微软雅黑',sans-serif;font-size:11pt;font-weight:bold;
    color:#005F73;margin:0 0 0.4em 0;">📋 案件概览</p>
  <!-- 卡片内容 -->
</div>
```

### 6.1 卡片类型

| 卡片 | 用途 | accent 色 | icon |
|------|------|----------|------|
| case-overview | 案件概览 | `#005F73` | 📋 |
| key-finding | 关键发现 | `#EE9B00` | 💡 |
| risk-alert | 风险警示 | `#C53030` | ⚠️ |
| evidence-gap | 证据缺口 | `#D97706` | 🔍 |
| strategy-recommend | 策略推荐 | `#0A6E42` | 🎯 |

## 7. 风险标记规范

### 7.1 行内风险徽章

```html
<!-- 绿色：低风险 / 合规 / 印证 -->
<span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;
  border-radius:3px;font-size:10pt;font-weight:bold;">✅ 印证</span>

<!-- 琥珀：中等风险 / 瑕疵 / 部分印证 -->
<span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;
  border-radius:3px;font-size:10pt;font-weight:bold;">⚠️ 瑕疵</span>

<!-- 红色：高风险 / 违法 / 无印证 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;
  border-radius:3px;font-size:10pt;font-weight:bold;">❌ 无印证</span>
```

### 7.2 置信度标注

```html
<span style="font-size:9.5pt;color:#64748B;">[置信度：<strong style="color:#005F73;">高</strong>]</span>
<span style="font-size:9.5pt;color:#64748B;">[置信度：<strong style="color:#D97706;">中</strong>]</span>
<span style="font-size:9.5pt;color:#64748B;">[置信度：<strong style="color:#C53030;">低</strong>]</span>
```

## 8. 深度模式折叠映射

| 深度模式 | 覆盖层 | 折叠策略 |
|---------|--------|---------|
| **quick** | 第1~2层 | 全部展开，第3~10层不渲染 |
| **standard** | 第1~6层 | 全部展开，第7层（如无条件输入）不渲染，第8~10层折叠 |
| **deep** | 第1~10层 | 全部展开，条件输出层按实际输入决定 |

### 8.1 折叠实现

```html
<!-- 折叠层（standard 模式下第8~10层） -->
<details style="margin:0.8em 0;" open>
  <summary style="font-weight:bold;font-size:12pt;color:#005F73;cursor:pointer;
    padding:8px 0;border-bottom:1px solid #E2E8F0;">
    第8层：供述可采性法律评估
  </summary>
  <div style="padding:0.5em 0;">
    <!-- 层内容 -->
  </div>
</details>
```

- **standard 模式**：第8~10层默认折叠（`<details>` 无 `open` 属性）
- **deep 模式**：所有层默认展开（`<details open>`）
- **quick 模式**：只输出第1~2层，无折叠

## 9. 打印适配参数

```css
@page {
  size: A4 portrait;
  margin: 2.0cm 1.5cm 1.5cm 3.0cm; /* I-Practical 标准 */
}

@media print {
  /* 隐藏屏幕元素 */
  .side-nav { display: none !important; }
  .toolbar { display: none !important; }
  .no-print { display: none !important; }

  /* 打印增强 */
  body {
    font-family: '微软雅黑', '宋体', serif;
    font-size: 11pt;
    line-height: 1.8;
    color: #000;
    margin: 0;
    padding: 0;
  }

  /* 确保背景色打印 */
  table thead { background: #005F73 !important; color: #fff !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }

  .row-confirmed, .row-partial, .row-missing,
  .row-risk-high, .row-risk-medium,
  .row-cred-high, .row-cred-medium, .row-cred-low,
  .row-stable, .row-gradient, .row-mutation, .row-recant {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* 主内容区取消左边距 */
  .main-content { margin-left: 0 !important; }

  /* 分页策略：每层从新页开始（deep 模式） */
  .page-break-before { page-break-before: always; }
}
```

## 10. 占位符清单

> 模板采用 HARD_BLOCK/CONTENT_SLOT 模式。LLM 仅填充以下 7 个 CONTENT_SLOT 占位符，禁止修改 HARD_BLOCK 内任何 CSS。
> 注：侧栏导航高亮由模板内 JS 脚本自动计算，无需 LLM 填充。

| 序号 | 占位符 | 填充内容 | 说明 |
|------|--------|---------|------|
| SLOT-0 | `PAGE_TITLE` | "讯问笔录深度分析报告" | 页面标题 |
| SLOT-1 | `GENERATED_AT` | YYYY-MM-DD HH:mm:ss | 生成时间戳（模板中 3 处引用均同值） |
| SLOT-2 | `CASE_OVERVIEW` | 案件概览 HTML 块 | 案件信息 + 笔录清单 + 分析参数 |
| SLOT-3 | `LAYER_1_TO_10` | 十层分析内容 HTML 块 | 按深度模式输出的各层 section |
| SLOT-4 | `CONCLUSION` | 结论与建议 HTML 块 | 关键发现 + 下游技能推荐 |
| SLOT-5 | `CHECKLIST` | 律师必检清单 HTML 块 | ☐ 待核实事项 |
| SLOT-6 | `ANALYSIS_META` | 分析元信息 | 分析深度 / 诉讼阶段 / 草稿声明 |

## 11. 降级输出规则

### 11.1 S1 降级（最强约束）

触发：`case_name` 或 `interrogation_text` 缺失。

输出：不生成 HTML，仅输出 Markdown 纯文本错误提示。

### 11.2 S2 降级（中度）

触发：笔录不完整 / 仅 1 份笔录。

输出：HTML 完整生成，缺失层标注 `[待补充：需要≥2份笔录]`，层级 block 使用灰色边框。

### 11.3 S3 降级（轻度）

触发：选填输入缺失（无录音录像转写 / 无同案犯供述等）。

输出：HTML 完整生成，条件输出层（第5/6/7层）标注 `[未提供相关材料，跳过本层分析]`，层级 block 正常渲染但内容区标灰。

---

*本文件遵循 compiler/ssot.md §17（SSOT）：产物最小化原则*
