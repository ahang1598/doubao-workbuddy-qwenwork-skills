# HTML 排版规范

> format_seriousness: C-Professional
> 视觉方案: B 经典沉稳（主色#1b3a5c/强调色#b8860b/分隔线#d4cfc5/浅灰背景#f5f3ef）
> 引用体系: base/rule/format-html/
> 输出格式: **纯 HTML**（不再保留 Markdown 格式）
> Richee 组件: c06(结论卡) + c09(时间轴) + c12(风险矩阵) + c13(流程图)

---

## 目录

- [一、引用声明](#一引用声明)
- [二、偏离声明](#二偏离声明)
- [三、HTML 骨架](#三html-骨架)
- [四、内联样式速查表（方案B）](#四内联样式速查表方案b)
- [五、Richee 组件集成](#五richee-组件集成)
- [六、策略分析专属组件渲染规则](#六策略分析专属组件渲染规则)
- [七、打印/PDF 导出适配](#七打印pdf-导出适配)
- [八、模板占位符](#八模板占位符)

---

## 一、引用声明

- 页面布局遵照 `core/page-layout.md` §1.2（C-Professional布局：2.5cm 2.6cm 2.0cm 2.8cm）
- 字体方案遵照 `core/font-scheme.md` §1.2（宋体12pt正文 + 黑体14pt标题）
- 色彩遵照 `color/legal-color-system.md` §5 方案B（经典沉稳）
- HTML渲染遵照 `format/html-spec.md` §3.2（方案B完整配色）+ §4.2（C-Professional元素样式）+ §12（执行摘要）+ §13（文档控制页）
- 图表遵照 `format/html-spec.md` §17（Mermaid集成+离线降级）
- 免责声明遵照 `templates/disclaimer-templates.md`
- 类型参照 `QUICK-REFERENCE.md` §2.2 客户交付报告类 → 策略分析报告
- Richee 组件参照 `components/README.md` §3.1 策略分析报告推荐：c06/c12/c13/c09
- 内联样式铁律遵照 `format/html-spec.md` §1.1（所有排版使用 `style=""` 内联样式）

---

## 二、偏离声明

无偏离项。C-Professional 策略分析报告按标准路径渲染。

---

## 三、HTML 骨架

> 基于 `html-spec.md` §2.1 + C-Professional 参数 + 方案B配色

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{DOC_TITLE}}</title>
  <style>
    body { counter-reset: page-counter; }
    .page-break { page-break-before: always; counter-increment: page-counter; }
    .page-number::after { content: counter(page-counter); }
    @page {
      size: A4 portrait;
      margin: 2.5cm 2.6cm 2.0cm 2.8cm;
    }
    @page :first {
      @top-left { content: none; }
      @top-right { content: none; }
      @bottom-center { content: none; }
    }
    @media print {
      .screen-only { display: none !important; }
      .print-only { display: block !important; }
      body { margin: 0; padding: 0; }
    }
    @media screen {
      body { background: #f5f3ef; padding: 1em; }
    }
  </style>
</head>
<body style="margin:0;padding:0;font-family:'宋体','仿宋',serif;font-size:12pt;line-height:1.5;color:#1A1A1A;background:#fffffd;">
  <article style="max-width:156mm;margin:0 auto;padding:0;">
    <!-- 页眉（屏幕模式） -->
    <div class="screen-only" style="display:flex;justify-content:space-between;align-items:center;font-family:'宋体',serif;font-size:10.5pt;color:#7a7a7a;border-bottom:2.5pt solid #1b3a5c;padding-bottom:2pt;margin-bottom:1em;">
      <span>{{HEADER_LEFT}}</span>
      <span>{{HEADER_RIGHT}}</span>
    </div>

    {{DOCUMENT_CONTENT}}

    <!-- 页脚 -->
    <div style="text-align:center;font-family:'宋体',serif;font-size:10.5pt;color:#7a7a7a;margin-top:2em;">
      第 <span class="page-number"></span> 页
    </div>
  </article>
</body>
</html>
```

---

## 四、内联样式速查表（方案B）

### 4.1 基础元素

| 元素 | 完整 style 属性 |
|------|----------------|
| `<h1>` 报告标题 | `style="font-family:'方正小标宋简体','小标宋体','黑体','宋体',serif;font-size:26pt;font-weight:bold;text-align:center;color:#1b3a5c;margin:1em 0;"` |
| `<h2>` 一级标题 | `style="font-family:'黑体','宋体',serif;font-size:16pt;font-weight:bold;color:#1b3a5c;border-bottom:1.5pt solid #1b3a5c;padding-bottom:0.3em;margin:1.5em 0 0.8em 0;text-indent:0;"` |
| `<h3>` 二级标题 | `style="font-family:'黑体','宋体',serif;font-size:13pt;font-weight:bold;color:#1b3a5c;margin:0.8em 0 0.3em 0;text-indent:0;"` |
| `<p>` 正文 | `style="text-indent:2em;margin:0.3em 0;text-align:justify;"` |
| `<blockquote>` | `style="margin:1em 0;padding:0.8em 1em;border-left:3pt solid #1b3a5c;background:#f5f3ef;font-size:11pt;color:#333;"` |
| `<hr>` 分隔线 | `style="border:none;border-top:1px solid #d4cfc5;margin:2em 0;"` |

### 4.2 表格（三线表）

| 元素 | 完整 style 属性 |
|------|----------------|
| `<table>` | `style="border-collapse:collapse;width:100%;margin:1em 0;"` |
| `<th>` | `style="border-top:1.5pt solid #1b3a5c;border-bottom:0.75pt solid #1b3a5c;padding:6px 8px;font-weight:bold;text-align:left;font-size:10.5pt;background:#f5f3ef;color:#1b3a5c;"` |
| `<td>` | `style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;font-size:10.5pt;"` |
| `<td>` 末行 | `style="border-bottom:1.5pt solid #1b3a5c;padding:6px 8px;font-size:10.5pt;"` |

### 4.3 强调方式

| 方式 | 允许 | HTML写法 |
|------|------|----------|
| 加粗 | ✅ | `<span style="font-weight:bold;">关键词</span>` |
| 红色风险标注 | ✅ | `<span style="color:#dc2626;">高风险</span>` |
| 背景高亮（关键结论） | ⚠️ | `<span style="background:#fef3c7;">关键结论</span>`（仅关键结论） |
| 斜体 | ❌ | 禁止使用 |

### 4.4 风险色标注

| 等级 | 背景色 | 文字色 | 用途 |
|------|--------|--------|------|
| 低风险/高可行性 | `#ecfdf3` | `#039855` | 策略可行性高 |
| 中风险/中可行性 | `#fffaeb` | `#b54708` | 策略需注意 |
| 高风险/低可行性 | `#fef3f2` | `#d92d20` | 策略风险较大 |

---

## 五、Richee 组件集成

### 5.1 声明

```yaml
richee_components: [c06, c09, c12, c13]
```

### 5.2 组件使用规则

| 组件 | 文件 | 报告位置 | 品牌方案适配 |
|------|------|----------|-------------|
| c06 结论卡 | `components/c06-conclusion-card.md` | 执行摘要区 + 推荐方案区 | 方案B替换：`#0a1628`→`#1b3a5c`，`#e2e5ea`→`#d4cfc5`，`rgba(197,155,39,0.10)`→`rgba(184,134,11,0.10)` |
| c12 风险矩阵 | `components/c12-risk-matrix.md` | 策略选项区 | 方案B替换：`#0a1628`→`#1b3a5c`，`#e2e5ea`→`#d4cfc5` |
| c13 流程图 | `components/c13-flow-chart.md` | 阶段行动计划区（策略实施路径） | 方案B替换：`#0a1628`→`#1b3a5c`，`#818594`→`#7a7a7a`，`#e2e5ea`→`#d4cfc5` |
| c09 时间轴 | `components/c09-timeline.md` | 阶段行动计划区（关键节点时间线） | 方案B替换：`#0a1628`→`#1b3a5c`，`#818594`→`#7a7a7a`，`#c59b27`→`#b8860b`，`#e8d080`不变 |

### 5.3 组件数据填充规范

**c06 结论卡**：
- 标题：`综合判断` / `推荐策略` / `核心结论`
- 标签：`可行性评估` / `风险等级` / `策略倾向`
- 标签色按风险等级选择（中风险=#fffaeb+#b54708 / 高风险=#fef3f2+#d92d20 / 低风险=#ecfdf3+#039855）
- 正文：策略核心判断一句话

**c12 风险矩阵**：
- 列头：证明难度低/中/高
- 行头：辩护可行性高/中/低
- 格子内容：具体策略情形（如"证据不足无罪辩护""认罪认罚从宽"等）
- 格子配色按 §4.4 风险色标准

**c13 流程图**：
- 节点数：3-5步（修改 grid-template-columns）
- 节点标题：策略步骤名称
- 节点描述：步骤说明

**c09 时间轴**：
- 项数：4-6个阶段
- 阶段标题：`第X阶段｜[阶段名称]`
- 阶段描述：具体行动内容

---

## 六、策略分析专属组件渲染规则

### 6.1 策略对比交互表

多策略对比表格，每列为一种策略，行为评估维度：

```html
<table style="border-collapse:collapse;width:100%;margin:1em 0;font-size:10.5pt;">
  <tr>
    <th style="border-top:1.5pt solid #1b3a5c;border-bottom:0.75pt solid #1b3a5c;padding:6px 8px;font-weight:bold;text-align:left;background:#f5f3ef;color:#1b3a5c;">维度</th>
    <th style="border-top:1.5pt solid #1b3a5c;border-bottom:0.75pt solid #1b3a5c;padding:6px 8px;font-weight:bold;text-align:center;background:#f5f3ef;color:#1b3a5c;">策略A：{{STRATEGY_A_NAME}}</th>
    <th style="border-top:1.5pt solid #1b3a5c;border-bottom:0.75pt solid #1b3a5c;padding:6px 8px;font-weight:bold;text-align:center;background:#f5f3ef;color:#1b3a5c;">策略B：{{STRATEGY_B_NAME}}</th>
    <th style="border-top:1.5pt solid #1b3a5c;border-bottom:0.75pt solid #1b3a5c;padding:6px 8px;font-weight:bold;text-align:center;background:#f5f3ef;color:#1b3a5c;">策略C：{{STRATEGY_C_NAME}}</th>
  </tr>
  <tr>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;font-weight:bold;">辩护层次</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;">{{A_LEVEL}}</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;">{{B_LEVEL}}</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;">{{C_LEVEL}}</td>
  </tr>
  <!-- 可行性行——三色标注 -->
  <tr>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;font-weight:bold;">可行性</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:3px;background:{{A_FEAS_BG}};color:{{A_FEAS_COLOR}};font-weight:bold;">{{A_FEAS}}</span></td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:3px;background:{{B_FEAS_BG}};color:{{B_FEAS_COLOR}};font-weight:bold;">{{B_FEAS}}</span></td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:3px;background:{{C_FEAS_BG}};color:{{C_FEAS_COLOR}};font-weight:bold;">{{C_FEAS}}</span></td>
  </tr>
  <tr>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;font-weight:bold;">核心论点</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;">{{A_ARGUMENT}}</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;">{{B_ARGUMENT}}</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;">{{C_ARGUMENT}}</td>
  </tr>
  <tr>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;font-weight:bold;">风险等级</td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:3px;background:{{A_RISK_BG}};color:{{A_RISK_COLOR}};font-weight:bold;">{{A_RISK}}</span></td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:3px;background:{{B_RISK_BG}};color:{{B_RISK_COLOR}};font-weight:bold;">{{B_RISK}}</span></td>
    <td style="border-bottom:0.75pt solid #d4cfc5;padding:6px 8px;text-align:center;"><span style="display:inline-block;padding:2px 8px;border-radius:3px;background:{{C_RISK_BG}};color:{{C_RISK_COLOR}};font-weight:bold;">{{C_RISK}}</span></td>
  </tr>
  <tr>
    <td style="border-bottom:1.5pt solid #1b3a5c;padding:6px 8px;font-weight:bold;">推荐度</td>
    <td style="border-bottom:1.5pt solid #1b3a5c;padding:6px 8px;text-align:center;">{{A_RECOMMEND}}</td>
    <td style="border-bottom:1.5pt solid #1b3a5c;padding:6px 8px;text-align:center;">{{B_RECOMMEND}}</td>
    <td style="border-bottom:1.5pt solid #1b3a5c;padding:6px 8px;text-align:center;">{{C_RECOMMEND}}</td>
  </tr>
</table>
```

**三色标注规则**：

| 评估值 | 背景色 | 文字色 |
|--------|--------|--------|
| 高（可行性高/风险低） | `#ecfdf3` | `#039855` |
| 中（可行性中/风险中） | `#fffaeb` | `#b54708` |
| 低（可行性低/风险高） | `#fef3f2` | `#d92d20` |

### 6.2 执行摘要

使用 **c06 结论卡**（Richee 组件）承载核心判断，遵照 `html-spec.md` §12 结构布局，方案B配色：

- **核心结论**：使用 c06 结论卡（`components/c06-conclusion-card.md`），方案B色值替换
- **关键发现标题**：`color:#4A7FB5`
- **建议行动标题**：`color:#b8860b`
- **风险概览表格**：按 §4.4 风险色标准
- 执行摘要整体结构遵照 `html-spec.md` §12（结论卡 + 关键发现 + 风险概览 + 建议行动）

### 6.3 文档控制页

遵照 `html-spec.md` §13，使用方案B配色：

- 标题：`color:#1b3a5c`
- 表头：`background:#f5f3ef;color:#1b3a5c;border-top:1.5pt solid #1b3a5c`

### 6.4 免责声明

使用 `templates/disclaimer-templates.md` 策略分析报告专用免责声明，渲染为 HTML：

```html
<div style="margin-top:2em;padding:1em;border-top:1px solid #d4cfc5;font-size:10pt;color:#7a7a7a;">
  <p style="text-indent:0;margin:0.3em 0;"><strong>免责声明</strong></p>
  <p style="text-indent:0;margin:0.3em 0;">本策略分析报告仅供律师辩护决策参考，不构成法律意见，不替代律师独立判断。报告基于委托人提供的案件材料编制，材料的完整性、真实性由委托人负责。</p>
  <p style="text-indent:0;margin:0.3em 0;">本报告中的可行性评估和风险分析基于当前可获得的信息，不构成对案件结果的承诺或保证。</p>
</div>
```

---

## 七、打印/PDF 导出适配

遵照 `html-spec.md` §6：

- 推荐方式：浏览器 Ctrl+P → 另存为 PDF
- `@page` 边距：2.5cm 2.6cm 2.0cm 2.8cm（C-Professional标准）
- `.page-break` 类用于分页控制
- `.screen-only` 打印时自动隐藏
- 浏览器兼容性：Chrome/Edge/Firefox 均可

---

## 八、模板占位符

| 占位符 | 替换内容 | 示例 |
|--------|----------|------|
| `{{DOC_TITLE}}` | 报告标题 | 刑事案件策略分析报告 |
| `{{HEADER_LEFT}}` | 页眉左 | 策略分析报告 |
| `{{HEADER_RIGHT}}` | 页眉右 | {{LAW_FIRM_NAME}} |
| `{{LAW_FIRM_NAME}}` | 律所全称 | 北京市金杜律师事务所 |
| `{{DOC_VERSION}}` | 文档版本 | V1.0 |
| `{{CONFIDENTIALITY}}` | 密级标记 | 机密 / 内部参考 |
| `{{PROJECT_CODE}}` | 项目/文档编号 | PROJ-2025-001 |
| `{{CLIENT_NAME}}` | 委托人 | 张某 |
| `{{SUSPECT_NAME}}` | 被告人/犯罪嫌疑人 | 张某 |
| `{{ALLEGED_CRIME}}` | 涉嫌罪名 | 诈骗罪 |
| `{{CASE_STAGE}}` | 案件阶段 | 审查起诉 |
| `{{GENERATION_DATE}}` | 生成日期 | 2026-06-10 |
| `{{STRATEGY_A/B/C_NAME}}` | 策略名称 | 事实之辩 |
| `{{A/B/C_FEAS}}` | 可行性评估 | 高/中/低 |
| `{{A/B/C_FEAS_BG}}` | 可行性背景色 | #ecfdf3/#fffaeb/#fef3f2 |
| `{{A/B/C_FEAS_COLOR}}` | 可行性文字色 | #039855/#b54708/#d92d20 |
| `{{A/B/C_RISK}}` | 风险等级 | L1/L2/L3 |
| `{{A/B/C_RISK_BG}}` | 风险背景色 | #ecfdf3/#fffaeb/#fef3f2 |
| `{{A/B/C_RISK_COLOR}}` | 风险文字色 | #039855/#b54708/#d92d20 |

---

*本文件遵循 format-html/ 体系，C-Professional + 方案B经典沉稳路径*
