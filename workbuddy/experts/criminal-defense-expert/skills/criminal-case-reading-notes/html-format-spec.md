# HTML 输出排版规范

> 本文件定义 criminal-case-reading-notes 技能 HTML 输出的完整排版规范。
> 严肃度：**I-Practical**（内部级），遵循 `base/rule/format-html/format/html-spec.md` §19。
> 视觉方案：**C-现代轻量**（方案C色值：青灰 `#005f73` + 暖橙 `#EE9B00`）。
> 双轨原则：HTML 不是对 Markdown 的重新排版，而是可视化增强版，内容与 Markdown O1 完全一致。
> **内联样式铁律**：所有排版格式使用 `style="..."` 内联，不依赖 CSS class（遵循 `html-spec.md` §1.1）。

---

## 目录

- [1. 内联样式铁律](#1-内联样式铁律)
- [2. 七色语义色板](#2-七色语义色板)
- [3. 通用内联样式模板](#3-通用内联样式模板)
- [4. 十二模块内联样式规范](#4-十二模块内联样式规范)
- [5. 信息卡片模板](#5-信息卡片模板)
- [6. 五色批注内联样式](#6-五色批注内联样式)
- [7. 风险标记/徽章模板](#7-风险标记徽章模板)
- [8. Mermaid 图表规范](#8-mermaid-图表规范)
- [9. 深度模式折叠映射](#9-深度模式折叠映射)
- [10. 打印适配](#10-打印适配)
- [11. 占位符清单](#11-占位符清单)
- [12. 降级输出规则](#12-降级输出规则)
- [13. 禁止使用的类名清单](#13-禁止使用的类名清单)

---

## 1. 内联样式铁律

> 遵循 `base/rule/format-html/format/html-spec.md` §1.1

**所有排版格式使用内联样式**（`style="..."`），直接写在对应 HTML 元素上。

- ✅ `<tr style="background:#FFF8EE;">`
- ❌ `<tr class="row-excerpt">` + 外部 CSS

**理由**：
1. HTML 文件复制粘贴到任何环境均保持排版，不依赖外部样式表
2. 消除 LLM 自创无效 CSS class 的风险
3. 与 `base/rule/format-html/` 体系完全对齐

**例外**（仅保留在 HARD_BLOCK `<style>` 中）：
- `@page` 打印页面规则
- `@media print` 打印适配
- Mermaid 初始化脚本
- 侧栏导航交互脚本

**LLM 生成规则**：
- LLM 填充 CONTENT_SLOT 时，所有 HTML 元素必须使用 `style="..."` 内联样式
- LLM **禁止**在 CONTENT_SLOT 中创建 `<style>` 块或 `<link>` 标签
- LLM **禁止**使用 CSS class 进行样式控制（见 §13 禁止清单）
- **功能类名白名单**（非样式 class，允许在 CONTENT_SLOT 中使用）：
  - `class="mermaid"` — Mermaid 库硬性要求，图表语法 `<pre>` 必须使用
  - `class="mermaid-wrap"` — Mermaid 容器（配合 HARD_BLOCK 中 `@media print` 隐藏 + JS 错误处理选择器）
  - `class="mermaid-error"` — Mermaid 渲染失败降级提示区
  - `class="print-table"` — 打印降级表格（配合 HARD_BLOCK 中 `@media print` 切换显示/隐藏）
  - `class="source-section"` — 源码折叠区（配合 HARD_BLOCK 中 `@media print` 隐藏）
- **HARD_BLOCK 骨架专用 class**（模板内置，LLM 禁止在 CONTENT_SLOT 中使用或模仿）：`side-nav`/`main-content`/`toolbar`/`toolbar-btn`/`no-print`/`template-version-watermark`/`page-break-before`/`active`/`visible`

## 2. 七色语义色板

> I-Practical 级别采用 7 色体系，方案C色值。

| 颜色名 | Hex | 用途 | 内联样式示例 |
|--------|-----|------|------------|
| **primary-dark** | `#005f73` | 主色-深 | `color:#005f73;` / `background:#005f73;color:#fff;` |
| **primary-light** | `#F0F7F8` | 主色-浅 | `background:#F0F7F8;` |
| **accent-orange** | `#EE9B00` | 强调橙 | `color:#EE9B00;` / `border-left:4px solid #EE9B00;` |
| **accent-orange-light** | `#FFF8EE` | 强调橙-浅 | `background:#FFF8EE;` |
| **success-green** | `#0A6E42` | 通过绿 | `color:#0A6E42;` |
| **success-green-light** | `#EDF7F0` | 通过绿-浅 | `background:#EDF7F0;` |
| **warning-amber** | `#D97706` | 警告琥珀 | `color:#D97706;` |
| **warning-amber-light** | `#FFFBEB` | 警告琥珀-浅 | `background:#FFFBEB;` |
| **danger-red** | `#C53030` | 危险红 | `color:#C53030;` |
| **danger-red-light** | `#FFF5F5` | 危险红-浅 | `background:#FFF5F5;` |
| **neutral-gray** | `#64748B` | 中性灰 | `color:#64748B;` |
| **neutral-light** | `#F8FAFC` | 中性灰-浅 | `background:#F8FAFC;` |
| **border-gray** | `#E2E8F0` | 边框灰 | `border-bottom:1px solid #E2E8F0;` |
| **text-dark** | `#1A202C` | 正文黑 | `color:#1A202C;` |

## 3. 通用内联样式模板

### 3.1 基础表格（参考 Richee c01-basic-table，方案C色值）

```html
<div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
    <thead>
      <tr>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">列名1</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">列名2</th>
      </tr>
    </thead>
    <tbody>
      <tr style="background:#F8FAFC;">
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">数据1</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">数据2</td>
      </tr>
      <tr>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">数据1</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">数据2</td>
      </tr>
    </tbody>
  </table>
</div>
```

**斑马纹**：偶数行加 `style="background:#F8FAFC;"`，奇数行不加。

### 3.2 行级着色速查

| 语义 | 行 style | 说明 |
|------|---------|------|
| 🟡摘录 | `background:#FFF8EE;` | 关键事实摘录 |
| 🔴矛盾 | `background:#FFF5F5;` | 证据间矛盾 |
| 🟢有利 | `background:#EDF7F0;` | 对辩护有利 |
| 🔵待补 | `background:#F0F7F8;` | 需补充核实 |
| ⚫无关 | （无额外着色） | 与辩护无关 |
| ✅印证 | `background:#EDF7F0;` | 证据链完整 |
| ⚠️部分印证 | `background:#FFFBEB;` | 部分支撑 |
| ❌无印证 | `background:#FFF5F5;` | 无证据支撑 |
| 致命断裂 | `background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;` | 逻辑链致命断裂 |
| 重要断裂 | `background:#FFFBEB;border-left:3px solid #D97706;` | 逻辑链重要断裂 |
| 辩护价值★★★ | `background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;` | 高价值突破点 |
| 辩护价值★★ | `background:#FFFBEB;` | 中价值突破点 |
| 辩护价值★ | `background:#FFF8EE;` | 低价值突破点 |

### 3.3 模块标题

```html
<section id="module-N" style="margin-bottom:28px;">
  <h2 style="font-size:16px;font-weight:600;color:#1A202C;border-bottom:1px solid #E2E8F0;padding-bottom:8px;margin-top:28px;margin-bottom:16px;line-height:1.35;">一、案件概况</h2>
  <!-- 模块内容 -->
</section>
```

### 3.4 高级模块折叠

```html
<details style="margin:0.8em 0;">
  <summary style="font-weight:bold;font-size:12pt;color:#005f73;cursor:pointer;padding:8px 0;border-bottom:1px solid #E2E8F0;">七、卷宗↔笔录对位索引</summary>
  <div style="padding:0.5em 0;">
    <!-- 模块内容 -->
  </div>
</details>
```

## 4. 十二模块内联样式规范

### 4.0 证据编号索引表（模块一（三）材料清单）

7列标准格式，参考 Richee c01-basic-table + c04-evidence-catalog：

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:40px;">序号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">全称</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">简称</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">形式</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">卷宗位置</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:120px;">阅卷重点</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#F8FAFC;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">1</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">E-Oral-01</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">李某陈述笔录</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">李某陈述</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">言词</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">第1卷P5-15</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">核心事实陈述</td>
    </tr>
  </tbody>
</table>
```

**行级着色**：按证据类型分类，每个分类段的第一行加 `background:#F8FAFC;`（斑马纹）。

### 4.1 模块二：事实梳理 — 时间线表格

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">时间</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">事件</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">证据来源</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">五色批注</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#FFF8EE;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">2025-05-10</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">签订协议</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">E-Phy-03</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">第2卷P5</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;"><span style="font-size:1.1em;">🟡</span> 摘录</td>
    </tr>
  </tbody>
</table>
```

**行级着色**：根据五色批注类型着色（见 §3.2）。

### 4.2 模块三：证据要点 — 证据目录表（参考 Richee c04-evidence-catalog）

**核心变更**：从 evidence-card div 卡片改为格式化表格。

每类证据一个子表，5列标准格式：

```html
<h3 style="font-size:13pt;font-weight:600;color:#1A202C;margin:16px 0 8px 0;">（一）物证/书证</h3>
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">证据名称</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">卷宗页码</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">要点/批注</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:100px;">下游标签</th>
    </tr>
  </thead>
  <tbody>
    <!-- 🟡摘录行 -->
    <tr style="background:#FFF8EE;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">E-Phy-01</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">《芯片采购合作框架协议》</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">第1卷P23-28</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="font-size:1.1em;">🟡</span> <strong>摘录</strong>：2023年5月10日签订，约定甲方供应芯片1000片<br>
        <span style="font-size:1.1em;">🟢</span> <strong>有利</strong>：协议本身无异常条款，属正常商业交易<br>
        <span style="font-size:1.1em;">🔵</span> <strong>待补</strong>：协议签订过程是否有其他见证人
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:1px 6px;background:#FFF8EE;color:#EE9B00;border-radius:3px;font-size:9pt;">辩护价值:中</span>
      </td>
    </tr>
    <!-- 🔴矛盾行 -->
    <tr style="background:#FFF5F5;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">E-Phy-02</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">银行转账凭证</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">第2卷P5-8</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="font-size:1.1em;">🔴</span> <strong>矛盾</strong>：转账金额85万 vs 协议约定100万，差额15万无合理解释
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">质证切入点</span>
      </td>
    </tr>
  </tbody>
</table>
```

**行级着色规则**：每行根据**最严重**的五色批注类型着色（🔴 > 🟡 > 🟢 > 🔵 > ⚫），一条证据有多条批注时在 `要点/批注` 列内用 `<br>` 分行，每行前加对应 Emoji + 加粗标签。

**批注格式**：`<span style="font-size:1.1em;">🟡</span> <strong>摘录</strong>：内容`

### 4.3 模块四：程序信息 — 强制措施/诉讼程序/程序问题

通用表格（§3.1），程序问题行按问题严重度着色：
- 程序违法 → `background:#FFF5F5;`
- 程序瑕疵 → `background:#FFFBEB;`
- 程序正常 → 无额外着色

### 4.4 模块五：辩护线索

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:40px;">#</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">有利事实/证据弱点/取证建议</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">价值</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:100px;">标签</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">1</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">85万元确用于芯片采购</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">E-Exp-02</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">★★★</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 6px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:9pt;">辩护价值:高</span>
      </td>
    </tr>
  </tbody>
</table>
```

### 4.5 模块六：待核实事项 — 任务清单

```html
<div style="margin:0.5em 0;">
  <p style="margin:0.3em 0;"><span style="font-family:'Consolas',monospace;">☐</span> 核实协议签订时是否有其他在场人 <span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">庭审查询</span></p>
  <p style="margin:0.3em 0;"><span style="font-family:'Consolas',monospace;">☐</span> 补充调取张某手机微信记录 <span style="display:inline-block;padding:1px 6px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:9pt;">补充证据</span></p>
</div>
```

### 4.6 模块七：对位索引

通用表格（§3.1），无特殊着色。

### 4.7 模块八：控方逻辑链还原

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">控方主张</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">支撑证据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">印证状态</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">断裂点</th>
    </tr>
  </thead>
  <tbody>
    <!-- ✅印证行 -->
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">虚构投资项目</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">微信聊天记录</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">E-Video-01</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;"><span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">✅ 印证</span></td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">—</td>
    </tr>
    <!-- ❌无印证+致命断裂行 -->
    <tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;font-weight:bold;">非法占有目的</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">（无直接证据）</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">—</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;"><span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">❌ 无印证</span></td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;font-weight:bold;">🔴 致命断裂：无证据证明被告人具有非法占有目的</td>
    </tr>
  </tbody>
</table>
```

### 4.8 模块九：言词证据九宫格

单元格内联着色标签：

| 状态 | 单元格内 `<span>` style |
|------|------------------------|
| 一致 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;` |
| 部分一致 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;` |
| 矛盾 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;` |
| 缺失 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#F8FAFC;color:#64748B;` |

### 4.9 模块十：证据三性初筛

单元格内联着色标签：

| 评估 | `<span>` style |
|------|---------------|
| ✅ 无明显问题 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;` |
| ⚠️ 存在疑问 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;` |
| ❌ 存在明显问题 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;` |

### 4.10 模块十一：辩方突破点矩阵

行级着色按辩护价值（见 §3.2）。

### 4.11 模块十二：团队协作区

通用表格（§3.1），无特殊着色。

## 5. 信息卡片模板

> 遵循 `html-spec.md` §19.5 I-Practical 信息卡片

```html
<!-- 案件概况卡片 -->
<div style="background:#F0F7F8;border-radius:6px;padding:1em 1.2em;margin:0.8em 0;border-left:4px solid #005f73;">
  <p style="font-size:11pt;font-weight:bold;color:#005f73;margin:0 0 0.4em 0;">📋 案件概况</p>
  <!-- 卡片内容 -->
</div>
```

### 5.1 卡片类型

| 卡片 | accent 色 | icon | 边框 style |
|------|----------|------|-----------|
| case-overview | `#005f73` | 📋 | `border-left:4px solid #005f73;` |
| key-finding | `#EE9B00` | 💡 | `border-left:4px solid #EE9B00;` |
| contradiction | `#C53030` | 🔴 | `border-left:4px solid #C53030;` |
| favorable | `#0A6E42` | 🟢 | `border-left:4px solid #0A6E42;` |
| evidence-gap | `#D97706` | 🔍 | `border-left:4px solid #D97706;` |
| breakthrough | `#EE9B00` | 🎯 | `border-left:4px solid #EE9B00;` |

## 6. 五色批注内联样式

> 将 Markdown 中的五色 Emoji 批注转换为视觉更突出的表格行着色 + 行内标签

### 6.1 行级着色（详见 §3.2 行级着色速查表）

> 五色批注行级着色规则以 §3.2 为 SSOT。此处不再重复，仅补充行列标签的 Emoji 格式规范。

### 6.2 行内标签（用于模块三要点/批注列内）

```html
<span style="font-size:1.1em;">🟡</span> <strong>摘录</strong>：[摘录内容]
<span style="font-size:1.1em;">🔴</span> <strong>矛盾</strong>：[矛盾描述]
<span style="font-size:1.1em;">🟢</span> <strong>有利</strong>：[有利信息]
<span style="font-size:1.1em;">🔵</span> <strong>待补</strong>：[待补信息]
```

## 7. 风险标记/徽章模板

### 7.1 行内风险徽章

```html
<!-- ✅ 绿色：低风险/印证/合规 -->
<span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">✅ 印证</span>

<!-- ⚠️ 琥珀：中等风险/部分印证/瑕疵 -->
<span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:10pt;font-weight:bold;">⚠️ 部分印证</span>

<!-- ❌ 红色：高风险/无印证/矛盾 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">❌ 无印证</span>
```

### 7.2 下游对接标签徽章

```html
<!-- 质证切入点 -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">质证切入点</span>

<!-- 辩护价值:高 -->
<span style="display:inline-block;padding:1px 6px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:9pt;">辩护价值:高</span>

<!-- 辩护价值:中 -->
<span style="display:inline-block;padding:1px 6px;background:#FFF8EE;color:#EE9B00;border-radius:3px;font-size:9pt;">辩护价值:中</span>

<!-- 庭审查询 -->
<span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">庭审查询</span>

<!-- 补充证据 -->
<span style="display:inline-block;padding:1px 6px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:9pt;">补充证据</span>

<!-- 程序违法 -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">程序违法</span>
```

### 7.3 证明力标签（参考 Richee c04-evidence-catalog）

```html
<!-- 强 -->
<span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#FFF5F5;color:#C53030;">强</span>

<!-- 中 -->
<span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#FFFBEB;color:#D97706;">中</span>

<!-- 弱 -->
<span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#EDF7F0;color:#0A6E42;">弱</span>
```

## 8. Mermaid 图表规范

### 8.1 Mermaid 容器

```html
<div class="mermaid-wrap" style="background:#fff;border:1px solid #E2E8F0;padding:16px;margin-bottom:0;overflow-x:auto;">
  <pre class="mermaid">
timeline
    title 案件关键时间线
    section 侦查阶段
        2025-05-10 : 李某转账30万 (E-Phy-03)
  </pre>
</div>
<div class="mermaid-error" style="background:#FFF5F5;border:1px solid #fca5a5;border-radius:4px;padding:12px 16px;margin:12px 0;font-size:12px;color:#991b1b;line-height:1.6;display:none;">
  ⚠️ 时间线图渲染失败。请展开下方"查看 Mermaid 源码"区域，复制代码到 <a href="https://mermaid.live" target="_blank">mermaid.live</a> 在线渲染。
</div>
```

### 8.2 Mermaid 初始化参数

已在 html-template.html HARD_BLOCK 中定义，LLM 无需重复。

### 8.3 降级表格

打印时 Mermaid 隐藏，显示降级表格：

```html
<table class="print-table" style="display:none;width:100%;border-collapse:collapse;font-size:10.5pt;">
  <!-- 同源数据的表格版本 -->
</table>
```

## 9. 深度模式折叠映射

| 深度模式 | 覆盖模块 | 折叠策略 |
|---------|---------|---------|
| **quick** | 模块一~六 | 全部展开，模块七~十二不渲染 |
| **standard** | 模块一~六+七~十二 | 基础模块展开，高级模块默认折叠 |
| **deep** | 模块一~十二 | 全部展开 |

- **standard 模式**：模块七~十二用 `<details>`（无 `open` 属性）
- **deep 模式**：所有模块用 `<details open>`
- **quick 模式**：只输出模块一~六，高级模块不渲染

## 10. 打印适配

已内置在 html-template.html HARD_BLOCK 的 `@media print` 中。

打印时关键行为：
- 侧栏导航隐藏
- 工具栏隐藏
- Mermaid 图表隐藏，显示降级表格
- 折叠区展开
- 表头/行级着色确保打印（`-webkit-print-color-adjust: exact;`）
- 主内容区取消左边距

## 11. 占位符清单

> **SSOT**（唯一事实源）：本 §11 为占位符清单的唯一真实来源。output-spec.md §2.4 引用此处。

| 序号 | 占位符 | 填充内容 | 说明 |
|------|--------|---------|------|
| SLOT-0 | `PAGE_TITLE` | "阅卷笔录" | 页面主标题（h1） |
| SLOT-1 | `SUBTITLE` | "[案件名称] · [阶段] · [组织方式]" | 副标题 |
| SLOT-1' | `PAGE_META` | "阅卷视角：defense \| 阅卷人：XXX \| [生成时间]" | 元信息行 |
| SLOT-2 | `CASE_OVERVIEW` | 案件概况 HTML 块 | 案件信息+阅卷参数（使用内联样式） |
| SLOT-3 | `MODULE_1_TO_6` | 基础六模块内容 HTML 块 | 案件概况→待核实事项（使用内联样式） |
| SLOT-4 | `MODULE_7_TO_12` | 高级六模块内容 HTML 块 | 对位索引→团队协作区（使用内联样式） |
| SLOT-5 | `DISCLAIMER_STYLE` | L1/L2 免责声明样式 | L1="" / L2="border-left:3px solid #C53030;background:#fef9f9;" |
| 工具栏 | `GENERATED_AT` | YYYY-MM-DD HH:mm:ss | 生成时间戳（工具栏+页脚水印，2处同值） |

**CONTENT_SLOT 填充铁律**：
- 所有 HTML 元素使用 `style="..."` 内联样式
- 禁止使用 CSS class 进行样式控制（功能类名白名单见 §1.1）
- 禁止创建 `<style>` 块或 `<link>` 标签
- 禁止修改 HARD_BLOCK 内任何代码

## 12. 降级输出规则

### 12.1 S1 降级（最强约束）

触发：`case_name` 或 `case_materials` 缺失。

输出：不生成 HTML，仅输出 Markdown 纯文本错误提示。

### 12.2 S2 降级（中度）

触发：推荐字段缺失过半 / 卷宗描述过于简略。

输出：HTML 完整生成基础模块（一~六），高级模块（七~十二）标注 `[待补充：需要更完整的卷宗描述]`，灰色边框：`border:1px solid #E2E8F0;background:#F8FAFC;color:#64748B;padding:12px;`。

### 12.3 S3 降级（轻度）

触发：选填输入缺失（如无鉴定意见/无视听资料）。

输出：HTML 完整生成，条件输出模块标注 `[未提供相关材料，跳过本模块]`，灰色文字：`color:#64748B;`。

## 13. 禁止使用的类名清单

> 以下 CSS class 名已从模板中移除。LLM 在 CONTENT_SLOT 中**禁止**使用任何 class 进行样式控制（功能类名白名单见 §1.1）。

| 禁止的 class | 原用途 | 替代方案 |
|-------------|--------|---------|
| `.data-table` | 数据表格 | `<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">` |
| `.row-excerpt` | 🟡摘录行 | `<tr style="background:#FFF8EE;">` |
| `.row-contradiction` | 🔴矛盾行 | `<tr style="background:#FFF5F5;">` |
| `.row-favorable` | 🟢有利行 | `<tr style="background:#EDF7F0;">` |
| `.row-supplement` | 🔵待补行 | `<tr style="background:#F0F7F8;">` |
| `.row-confirmed` | ✅印证行 | `<tr style="background:#EDF7F0;">` |
| `.row-partial` | ⚠️部分行 | `<tr style="background:#FFFBEB;">` |
| `.row-missing` | ❌无印证行 | `<tr style="background:#FFF5F5;">` |
| `.row-fatal-break` | 致命断裂行 | `<tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">` |
| `.row-important-break` | 重要断裂行 | `<tr style="background:#FFFBEB;border-left:3px solid #D97706;">` |
| `.row-value-high` | 辩护价值★★★ | `<tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">` |
| `.row-value-medium` | 辩护价值★★ | `<tr style="background:#FFFBEB;">` |
| `.row-value-low` | 辩护价值★ | `<tr style="background:#FFF8EE;">` |
| `.badge` / `.badge-*` | 徽章 | `<span style="display:inline-block;padding:1px 8px;border-radius:3px;font-size:10pt;font-weight:bold;">` |
| `.tag-*` | 下游标签 | 见 §7.2 内联样式模板 |
| `.evidence-card` | 证据卡片 | **已废弃** → 使用 §4.2 证据表格 |
| `.info-card` | 信息卡片 | 见 §5 内联样式模板 |
| `.evidence-short` | 证据简称 | `color:#005f73;font-size:10pt;` |
| `.module-block` | 模块区块 | `<section style="margin-bottom:28px;">` |
| `.module-heading` | 模块标题 | `<h2 style="font-size:16px;font-weight:600;...">` |
| `.page-header` / `.page-title` / `.page-subtitle` / `.page-meta` | 页面标题区 | 已内置在模板中 |
| `.legend-bar` / `.legend-item` | 图例区 | 已内置在模板中 |
| `.disclaimer-footer` / `.disclaimer-l1` / `.disclaimer-l2` | 免责声明 | 已内置在模板中 |
| `.mermaid-wrap` / `.mermaid-error` | Mermaid容器 | **功能类名白名单**（见 §1.1），允许按 §8.1 复制；禁止自创其他容器 class |
| `.source-section` | 源码折叠 | **功能类名白名单**（见 §1.1），允许用于源码折叠区（仅限 `@media print` 隐藏）；禁止用于其他场景 |
| `.print-table` | 打印降级表格 | **功能类名白名单**（见 §1.1），允许按 §8.3 用于打印降级表格；禁止用于其他场景 |
| `.text-muted` / `.text-warn` / `.text-critical` | 文字颜色 | `color:#64748B;` / `color:#D97706;` / `color:#C53030;` |

**总原则**：如果不确定某个 class 是否合法，**不要使用**，改用内联 `style="..."`。功能类名白名单见 §1.1。

---

*本文件遵循 compiler/ssot.md §17（SSOT）：产物最小化原则 + base/rule/format-html/ §1.1 内联样式铁律*
*richee_components: [c04]*
