# HTML 排版规范 v2.1.0

## 概述

本技能输出 HTML 格式的刑事家属程序指引，须满足"浏览器打开→打印→交付"的端到端体验。本规范定义 HTML 模板的排版参数、CSS 架构和打印适配规则。

**v2.1 核心变更**：视觉层级从三色（紧急/重要/参考）重构为四色语义系统（禁止/行动/关注/参考），解决"积极行为与禁止行为视觉不可区分"的致命 UX 问题。

## 页面规格

| 参数 | 速览卡 | 极简版 | 标准版 |
|------|--------|--------|--------|
| 页面尺寸 | 半页 A4（210mm × 148mm） | A4（210mm × 297mm） | A4 |
| 边距 | 上下 12mm，左右 15mm | 上下 20mm，左右 25mm | 同左 |
| 字体标题 | 微软雅黑/SimHei 18px | 16-17px | 17px |
| 字体正文 | 微软雅黑/SimHei 11-12px | 宋体/SimSun 14px | 宋体/SimSun 14px |
| 行距 | 1.6 | 1.8 | 1.8 |
| 板块间距 | — | 14px | 20px |

## 视觉层级系统（四色·语义明确）

### 设计原则

1. **红色 = 禁止**——仅用于"不能做"，全球通用"停止"语义
2. **绿色 = 行动**——用于"应该做"，全球通用"通行"语义
3. **琥珀 = 关注**——用于"需要知道"，暗示"注意"
4. **灰色 = 参考**——用于"可了解"，暗示"可选阅读"
5. **阶段色不渗透**——仅用于阶段卡和少量强调，不占据主导

### CSS 变量定义

```css
:root {
  --color-danger: #D32F2F;          /* 禁止·严禁 */
  --color-danger-bg: #FFF5F5;
  --color-action: #2E7D32;          /* 行动·可做 */
  --color-action-bg: #F1F8E9;
  --color-attention: #E65100;       /* 关注·重要 */
  --color-attention-bg: #FFF8E1;
  --color-reference: #616161;       /* 参考·可阅 */
  --color-reference-bg: #F5F5F5;
  --color-reference-border: #E0E0E0;
}
```

### 四色层级 CSS

```css
/* 🔴 禁止层——仅用于"不能做" */
.danger {
  background: #FFF5F5;
  border-left: 4px solid #D32F2F;
  padding: 12px 16px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}

/* 🟢 行动层——用于"应该做" */
.action {
  background: #F1F8E9;
  border-left: 4px solid #2E7D32;
  padding: 12px 16px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}

/* 🟠 关注层——用于"需要知道" */
.attention {
  background: #FFF8E1;
  border-left: 4px solid #E65100;
  padding: 12px 16px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}

/* ⚪ 参考层——用于"可了解" */
.reference {
  background: #F5F5F5;
  border-left: 4px solid #E0E0E0;
  padding: 12px 16px;
  margin: 12px 0;
  border-radius: 0 4px 4px 0;
}
```

### 四色徽章

```css
.badge-danger { background: #D32F2F; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 3px; }
.badge-action { background: #2E7D32; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 3px; }
.badge-attention { background: #E65100; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 3px; }
.badge-reference { background: #616161; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 3px; }
```

### 板块→四色映射

| 板块 | 语义 | CSS 类 | 徽章 | 徽章文字 |
|------|------|--------|------|---------|
| O4 家属能做什么 | 🟢 行动 | `.action` | `badge-action` | "行动" |
| O5 家属不能做什么 | 🔴 禁止 | `.danger` | `badge-danger` | "严禁" |
| O2 阶段卡 | 🟠 关注 | `.attention` | — | — |
| O3 律师能做什么 | 🟠 关注 | `.attention` | `badge-attention` | "关注" |
| O6 时间节点 | 🟠 关注 | `.attention` | `badge-attention` | "关注" |
| O7 三阶段总览 | 🟠 关注 | — | `badge-attention` | "关注" |
| O9 取保候审 | 🟠 关注 | `.attention` | `badge-attention` | "关注" |
| O8 会见规则 | ⚪ 参考 | `.reference` + 折叠 | `badge-reference` | "参考" |
| O10 送物送钱 | ⚪ 参考 | `.reference` + 折叠 | `badge-reference` | "参考" |
| O11 罪名简介 | ⚪ 参考 | `.reference` + 折叠 | `badge-reference` | "参考" |
| O12 常见问题 | ⚪ 参考 | `.reference` + 折叠 | `badge-reference` | "参考" |

### 案件标签四色化

```css
.case-tag.done { background: #E8F5E9; color: #2E7D32; border: 1px solid rgba(46,125,50,0.2); }
.case-tag.attention { background: #FFF3E0; color: #E65100; border: 1px solid rgba(230,81,0,0.2); }
.case-tag.highlight { background: #FFF8E1; color: #F57F17; border: 1px solid rgba(245,127,23,0.2); }
.case-tag.warning { background: #FFF5F5; color: #D32F2F; border: 1px solid rgba(211,47,47,0.2); }
```

## 阶段色（仅用于阶段标识）

阶段色用于阶段卡、三阶段总览色块、当前流程节点边框，**不渗透到板块标题和正文**。

```css
--stage-red: #E74C3C;      /* 侦查 */
--stage-amber: #F39C12;    /* 审查起诉 */
--stage-green: #27AE60;    /* 审判 */
```

**约束**：
- 板块标题下划线使用 `#E0E0E0`（中性灰），不使用阶段色
- 页眉分割线使用 `#E0E0E0`，不使用阶段色
- 流程图高亮使用 `var(--color-attention)`（琥珀色），不用红色

## 表格样式

```css
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th {
  background: #FFF;           /* 白底——消除色块内灰色冲突 */
  font-family: 'SimHei', 'Microsoft YaHei', sans-serif;
  font-weight: bold;
  text-align: left;
  padding: 6px 10px;
  border-bottom: 2px solid #E0E0E0;   /* 仅底部边框 */
  font-size: 12px;
  color: #555;
}
.data-table td {
  padding: 6px 10px;
  border-bottom: 1px solid #EEE;       /* 轻底线 */
  vertical-align: top;
}
.data-table tr:last-child td { border-bottom: none; }
```

## 流程图组件

```css
.flow-chart { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; padding: 12px; background: #FAFAFA; border-radius: 6px; }
.flow-node { text-align: center; padding: 8px 14px; border-radius: 6px; min-width: 80px; font-size: 12px; }
.flow-node.current { border: 2px solid var(--stage-color); background: #FFF; font-weight: bold; }
.flow-node.future { border: 1px dashed #BBB; background: #FFF; }
.flow-node .node-action { color: var(--color-attention); }   /* 琥珀色，非红色 */
.flow-note .highlight { color: var(--color-attention); font-weight: bold; }  /* "金色窗口"→琥珀色 */
```

## 折叠详情（默认关闭）

```css
.collapsible { margin: 8px 0; border: 1px solid #EEE; border-radius: 4px; }
.collapsible summary { padding: 8px 14px; font-weight: bold; cursor: pointer; list-style: none; font-size: 13px; background: #FAFAFA; }
.collapsible summary::before { content: '▶ '; font-size: 10px; color: #999; }
.collapsible[open] summary::before { content: '▼ '; }
```

**约束**：O8/O10/O11/O12 默认关闭（不加 `open` 属性）。打印时自动展开。

## 律所品牌区

```
页眉左侧：{{LAW_FIRM_LOGO}}（宽≤120px，高自适应）
页眉右侧：{{LAW_FIRM_NAME}}（14px 加粗，#555 中性色）
页脚居中：{{LAW_FIRM_NAME}} | 联系方式：______________（留白供手写）
```

## 阶段高亮卡 CSS

```css
.stage-card {
  border-left: 6px solid var(--stage-color);
  padding: 12px 16px;
  margin: 16px 0;
  background: linear-gradient(90deg, rgba(0,0,0,0.02), transparent);  /* 中性渐变 */
}
.stage-card h3 { color: var(--stage-color); font-size: 17px; }
```

## 打印适配

### @media print 规则

```css
@media print {
  @page { size: A4; margin: 20mm 25mm; }

  .page { width: auto; padding: 0; margin: 0; }

  /* 板块不分页 */
  .section { page-break-inside: avoid; }

  /* 阶段卡：添加边框补偿阴影 */
  .stage-card { border: 2px solid var(--stage-color); }
  .stage-block.current { box-shadow: none; border-width: 4px; }

  /* 水印 */
  .watermark { display: block; }
  .no-print { display: none; }

  /* 折叠内容展开 */
  .collapsible .content { display: block !important; }
  .faq-answer { display: block !important; }

  /* 黑白打印兼容：色块添加边框 */
  .danger { border: 1px solid #999; }
  .action { border: 1px solid #999; }
  .attention { border: 1px solid #999; }
  .reference { border: 1px solid #999; }
}
```

## 占位符清单

### 速览卡模板（pocket.html）

| 占位符 | 填充内容 | 说明 |
|--------|---------|------|
| `{{LAW_FIRM_LOGO}}` | 律所 Logo `<img>` 标签 | 无配置时隐藏 |
| `{{LAW_FIRM_NAME}}` | 律所名称文本 | 无配置时显示标题 |
| `{{STAGE_COLOR}}` | 当前阶段色值 | #E74C3C/#F39C12/#27AE60 |
| `{{STAGE_NAME}}` | 当前阶段名称 | 侦查/审查起诉/审判 |
| `{{SUSPECT_NAME}}` | 嫌疑人称谓 | 默认"嫌疑人" |
| `{{LAWYER_QUICK_LIST}}` | 律师工作速览 | 3项关键词 |
| `{{FAMILY_QUICK_LIST}}` | 家属行动速览 | 2项关键词 |
| `{{DONT_QUICK_LIST}}` | 禁止行为速览 | 3项关键词 |
| `{{DEADLINE}}` | 最紧急时间节点 | 如"4月14日前" |
| `{{DEADLINE_DESC}}` | 时间节点说明 | 如"取保申请黄金窗口" |

### 极简版模板（minimal.html）

| 占位符 | 填充内容 | 说明 |
|--------|---------|------|
| `{{LAW_FIRM_LOGO}}` | 律所 Logo `<img>` 标签 | 无配置时隐藏 |
| `{{LAW_FIRM_NAME}}` | 律所名称文本 | 无配置时显示标题 |
| `{{STAGE_NAME}}` | 当前阶段名称 | 侦查/审查起诉/审判 |
| `{{STAGE_COLOR}}` | 当前阶段色值 | #E74C3C/#F39C12/#27AE60 |
| `{{STAGE_DESC}}` | 一句话阶段说明 | ≤60字 |
| `{{LAWYER_ACTIONS_TABLE}}` | 律师工作表格 | HTML table |
| `{{FAMILY_CAN_DO_TABLE}}` | 家属行动表格 | HTML table |
| `{{FAMILY_CANNOT_DO_TABLE}}` | 禁止行为表格 | HTML table |
| `{{NEXT_TIMELINE_FLOW}}` | 时间节点流程图 | HTML flow-chart |
| `{{DISCLAIMER}}` | 免责声明 | 固定文本 |

### 标准版模板（standard.html）

在极简版占位符基础上增加：

| 占位符 | 填充内容 | 说明 |
|--------|---------|------|
| `{{DOC_SUBTITLE}}` | 文档副标题 | 嫌疑人·罪名·阶段·日期 |
| `{{THREE_STAGE_TIMELINE}}` | 三阶段时间线 | CSS色块横排 |
| `{{MEETING_RULES}}` | 会见规则详解 | 折叠内容 |
| `{{BAIL_CONDITIONS_TABLE}}` | 取保候审对照表 | HTML table |
| `{{VISITING_RULES}}` | 送物送钱规则 | 折叠内容 |
| `{{CHARGE_INFO_COLLAPSIBLE}}` | 罪名简介折叠块 | 条件输出 |
| `{{FAQ_SECTION_COMPACT}}` | 精简 Q&A（5个） | 折叠FAQ |

## 三档渲染策略

- **速览卡**：pocket.html，半页 A4，5 图块横排（四色语义）
- **极简版**：minimal.html，1 页，O2-O6 + 页脚
- **标准版**：standard.html，2-3 页，O2-O12，O8/O10/O11/O12 默认折叠

选择 `depth=pocket` → 仅渲染速览模板；`depth=minimal` → 极简模板；`depth=standard` → 标准模板

## v2.0→v2.1 迁移指南

| 旧类名 | 新类名 | 语义变化 |
|--------|--------|---------|
| `.urgent` | `.danger` | 红色从"紧急"改为"禁止"，仅用于 O5 |
| `.important` | `.attention` | 琥珀色从"重要"改为"关注"，用于 O3/O6/O9 |
| — | `.action` | **新增**绿色"行动"层，用于 O4 |
| `.reference` | `.reference` | 不变 |
| `.badge-urgent` | `.badge-danger` | "必做"→"严禁" |
| `.badge-important` | `.badge-attention` | "重要"→"关注" |
| — | `.badge-action` | **新增** "行动" |
