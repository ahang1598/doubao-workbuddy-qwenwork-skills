# HTML 输出排版规范

> 本文件定义 criminal-evidence-analysis 技能 HTML 输出的完整排版规范。
> 严肃度：**I-Practical**（内部级），遵循 `base/rule/format-html/format/html-spec.md` §19。
> 视觉方案：**C-现代轻量**（方案C色值：青灰 `#005f73` + 暖橙 `#EE9B00`）。
> 双轨原则：HTML 不是对 Markdown 的重新排版，而是可视化增强版，内容与 Markdown O1 完全一致。
> **内联样式铁律**：所有排版格式使用 `style="..."` 内联，不依赖 CSS class（遵循 `html-spec.md` §1.1）。

---

## 目录

- [1. 内联样式铁律](#1-内联样式铁律)
- [2. 七色语义色板](#2-七色语义色板)
- [3. 通用内联样式模板](#3-通用内联样式模板)
- [4. 六模块内联样式规范](#4-六模块内联样式规范)
- [5. 信息卡片模板](#5-信息卡片模板)
- [6. 风险标记/徽章模板](#6-风险标记徽章模板)
- [7. Mermaid 证据链图规范](#7-mermaid-证据链图规范)
- [8. 深度模式折叠映射](#8-深度模式折叠映射)
- [9. 打印适配](#9-打印适配)
- [10. 占位符清单](#10-占位符清单)
- [11. 降级输出规则](#11-降级输出规则)
- [12. 禁止使用的类名清单](#12-禁止使用的类名清单)

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
- LLM **禁止**使用 CSS class 进行样式控制（见 §12 禁止清单）
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
| 🟢合规/无瑕疵 | `background:#EDF7F0;` | 三性评估通过 |
| ⚠️存疑 | `background:#FFFBEB;` | 程序瑕疵/关联度弱 |
| 🔴违法/有风险 | `background:#FFF5F5;` | 取证违法/证据链断裂 |
| 🔵待补充 | `background:#F0F7F8;` | 需补证核实 |
| 致命缺陷 | `background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;` | 证据链致命断裂 |
| 重要缺陷 | `background:#FFFBEB;border-left:3px solid #D97706;` | 证据链重要缺口 |

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
  <summary style="font-weight:bold;font-size:12pt;color:#005f73;cursor:pointer;padding:8px 0;border-bottom:1px solid #E2E8F0;">五、补证方向</summary>
  <div style="padding:0.5em 0;">
    <!-- 模块内容 -->
  </div>
</details>
```

## 4. 六模块内联样式规范

### 4.1 模块一：案件概况 — 证据概览表格

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:40px;">序号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">证据名称</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">形式</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">控/辩方</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#F8FAFC;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">1</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">E-Oral-01</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">被害人陈述笔录</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">言词</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">控方</td>
    </tr>
  </tbody>
</table>
```

**行级着色**：按证据类型分类段，每个分类段第一行加 `background:#F8FAFC;`（斑马纹）。

### 4.2 模块二：证据三性评估 — 交互表

六列标准格式，参考 `html-spec.md` §16.1 证据表格：

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">证据编号</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">证据名称</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">客观性</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">关联性</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">合法性</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">总体评分</th>
    </tr>
  </thead>
  <tbody>
    <!-- 🟢合规行 -->
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">E-Phy-01</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">银行转账凭证</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 真实</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 直接</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 合规</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#FFF5F5;color:#C53030;">强</span>
      </td>
    </tr>
    <!-- 🔴违法行 -->
    <tr style="background:#FFF5F5;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">E-Oral-03</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">证人王某询问笔录</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;">⚠️ 矛盾</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 间接</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;">❌ 违法</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
        <span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#EDF7F0;color:#0A6E42;">弱</span>
      </td>
    </tr>
  </tbody>
</table>
```

**行级着色规则**：每行根据**最严重**的三性评估结果着色（🔴违法 > ⚠️存疑 > 🟢合规）。

**三性评估标签**：

| 评估 | `<span>` style |
|------|---------------|
| ✅ 无明显问题 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;` |
| ⚠️ 存在疑问 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;` |
| ❌ 存在明显问题 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;` |

**证明力标签**：

```html
<!-- 强 -->
<span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#FFF5F5;color:#C53030;">强</span>

<!-- 中 -->
<span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#FFFBEB;color:#D97706;">中</span>

<!-- 弱 -->
<span style="display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#EDF7F0;color:#0A6E42;">弱</span>
```

### 4.3 模块三：证据链分析 — 印证关系表

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">待证事实</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">支撑证据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:90px;">印证状态</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">断裂点</th>
    </tr>
  </thead>
  <tbody>
    <!-- ✅印证行 -->
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">资金往来事实</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">银行流水 + 被害人陈述</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">✅ 印证</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">—</td>
    </tr>
    <!-- ❌无印证+致命断裂行 -->
    <tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;font-weight:bold;">非法占有目的</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">（无直接证据）</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">❌ 无印证</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;font-weight:bold;">🔴 致命断裂：无证据证明被告人具有非法占有目的</td>
    </tr>
  </tbody>
</table>
```

### 4.4 模块四：质证要点

通用表格（§3.1），质证切入点行按风险严重度着色：
- 程序违法 → `background:#FFF5F5;`
- 证据存疑 → `background:#FFFBEB;`
- 辩护有利 → `background:#EDF7F0;`

### 4.5 模块五：补证方向 — 任务清单

```html
<div style="margin:0.5em 0;">
  <p style="margin:0.3em 0;"><span style="font-family:'Consolas',monospace;">☐</span> 补充调取被告人银行流水 <span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">补充证据</span></p>
  <p style="margin:0.3em 0;"><span style="font-family:'Consolas',monospace;">☐</span> 核实证人王某与被害人的关系 <span style="display:inline-block;padding:1px 6px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:9pt;">庭审查询</span></p>
</div>
```

### 4.6 模块六：不利证据风险提示

```html
<div style="background:#FFF5F5;border-left:4px solid #C53030;border-radius:4px;padding:12px 16px;margin:12px 0;">
  <p style="font-size:11pt;font-weight:bold;color:#C53030;margin:0 0 8px 0;">⚠️ 不利证据风险提示</p>
  <p style="font-size:10.5pt;color:#1A202C;margin:0 0 4px 0;"><strong>E-Oral-03 证人王某询问笔录</strong>：虽存在取证程序瑕疵，但对核心事实有直接证明力。</p>
  <p style="font-size:10.5pt;color:#64748B;margin:0;">应对策略：申请非法证据排除 + 补强辩方证据</p>
</div>
```

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
| evidence-risk | `#C53030` | 🔴 | `border-left:4px solid #C53030;` |
| evidence-gap | `#D97706` | 🔍 | `border-left:4px solid #D97706;` |
| favorable | `#0A6E42` | 🟢 | `border-left:4px solid #0A6E42;` |
| key-finding | `#EE9B00` | 💡 | `border-left:4px solid #EE9B00;` |

## 6. 风险标记/徽章模板

### 6.1 行内风险徽章

```html
<!-- ✅ 绿色：低风险/印证/合规 -->
<span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">✅ 印证</span>

<!-- ⚠️ 琥珀：中等风险/部分印证/瑕疵 -->
<span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:10pt;font-weight:bold;">⚠️ 部分印证</span>

<!-- ❌ 红色：高风险/无印证/矛盾 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">❌ 无印证</span>
```

### 6.2 下游对接标签徽章

```html
<!-- 质证切入点 -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">质证切入点</span>

<!-- 排除建议 -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">排除建议</span>

<!-- 补充证据 -->
<span style="display:inline-block;padding:1px 6px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:9pt;">补充证据</span>

<!-- 庭审查询 -->
<span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">庭审查询</span>
```

## 7. Mermaid 证据链图规范

### 7.1 Mermaid 容器

```html
<div class="mermaid-wrap" style="background:#fff;border:1px solid #E2E8F0;padding:16px;margin-bottom:0;overflow-x:auto;">
  <pre class="mermaid">
graph TD
    subgraph 核心证据
        E1["E-Phy-01 银行转账凭证"]
        E2["E-Oral-01 被害人陈述"]
    end
    subgraph 辅助证据
        E3["E-Doc-01 合同文本"]
    end
    subgraph 外围证据
        E4["E-Elec-01 微信记录"]
    end
    E1 -->|印证| E2
    E1 -->|佐证| E3
    E3 -.->|关联弱| E4
  </pre>
</div>
<div class="mermaid-error" style="background:#FFF5F5;border:1px solid #fca5a5;border-radius:4px;padding:12px 16px;margin:12px 0;font-size:12px;color:#991b1b;line-height:1.6;display:none;">
  ⚠️ 证据链图渲染失败。请展开下方"查看 Mermaid 源码"区域，复制代码到 <a href="https://mermaid.live" target="_blank">mermaid.live</a> 在线渲染。
</div>
```

**节点着色规则**（按证据类型）：
- 言词证据 → `fill:#FFF8EE,stroke:#EE9B00`（暖橙色系）
- 实物证据 → `fill:#EDF7F0,stroke:#0A6E42`（绿色系）
- 书证 → `fill:#F0F7F8,stroke:#005f73`（青灰色系）
- 电子数据 → `fill:#F8FAFC,stroke:#64748B`（灰色系）

**连线规则**：
- 实线 `-->` = 印证关系
- 虚线 `-.->` = 关联弱/需补强
- 红色粗线 `==>||❌||` = 矛盾/断裂

### 7.2 Mermaid 初始化参数

已在 html-template.html HARD_BLOCK 中定义，LLM 无需重复。

### 7.3 降级表格

打印时 Mermaid 隐藏，显示降级表格：

```html
<table class="print-table" style="display:none;width:100%;border-collapse:collapse;font-size:10.5pt;">
  <!-- 同源数据的表格版本 -->
</table>
```

## 8. 深度模式折叠映射

| 深度模式 | 覆盖模块 | 折叠策略 |
|---------|---------|---------|
| **quick** | 模块一~三 | 全部展开，模块四~六不渲染 |
| **standard** | 模块一~六 | 基础模块展开，高级模块（四~六）默认折叠 |
| **deep** | 模块一~六 | 全部展开 |

- **standard 模式**：模块四~六用 `<details>`（无 `open` 属性）
- **deep 模式**：所有模块用 `<details open>`
- **quick 模式**：只输出模块一~三，高级模块不渲染

## 9. 打印适配

已内置在 html-template.html HARD_BLOCK 的 `@media print` 中。

打印时关键行为：
- 侧栏导航隐藏
- 工具栏隐藏
- Mermaid 图表隐藏，显示降级表格
- 折叠区展开
- 表头/行级着色确保打印（`-webkit-print-color-adjust: exact;`）
- 主内容区取消左边距

## 10. 占位符清单

> **SSOT**（唯一事实源）：本 §10 为占位符清单的唯一真实来源。output-spec.md 引用此处。

| 序号 | 占位符 | 填充内容 | 说明 |
|------|--------|---------|------|
| SLOT-0 | `PAGE_TITLE` | "刑事证据分析报告" | 页面主标题（h1） |
| SLOT-1 | `SUBTITLE` | "[案件名称] · [涉嫌罪名] · [分析视角]" | 副标题 |
| SLOT-1' | `PAGE_META` | "分析视角：defense \| 分析人：XXX \| [生成时间]" | 元信息行 |
| SLOT-2 | `CASE_OVERVIEW` | 案件概况 HTML 块 | 案件信息+证据概览（使用内联样式） |
| SLOT-3 | `MODULE_1_TO_6` | 六模块内容 HTML 块 | 案件概况→不利证据风险提示（使用内联样式） |
| SLOT-4 | `DISCLAIMER_STYLE` | L2 免责声明样式 | L2="border-left:3px solid #C53030;background:#fef9f9;" |
| 工具栏 | `GENERATED_AT` | YYYY-MM-DD HH:mm:ss | 生成时间戳（工具栏+页脚水印，2处同值） |

**CONTENT_SLOT 填充铁律**：
- 所有 HTML 元素使用 `style="..."` 内联样式
- 禁止使用 CSS class 进行样式控制（功能类名白名单见 §1）
- 禁止创建 `<style>` 块或 `<link>` 标签
- 禁止修改 HARD_BLOCK 内任何代码

## 11. 降级输出规则

### 11.1 S1 降级（最强约束）

触发：`case_name` 或 `evidence_list` 缺失。

输出：不生成 HTML，仅输出 Markdown 纯文本错误提示。

### 11.2 S2 降级（中度）

触发：推荐字段缺失过半 / 证据描述过于简略。

输出：HTML 完整生成基础模块（一~三），高级模块（四~六）标注 `[待补充：需要更完整的证据描述]`，灰色边框：`border:1px solid #E2E8F0;background:#F8FAFC;color:#64748B;padding:12px;`。

### 11.3 S3 降级（轻度）

触发：选填输入缺失（如无鉴定意见/无电子数据）。

输出：HTML 完整生成，条件输出模块标注 `[未提供相关证据，跳过本模块]`，灰色文字：`color:#64748B;`。

## 12. 禁止使用的类名清单

> 以下 CSS class 名已从模板中移除。LLM 在 CONTENT_SLOT 中**禁止**使用任何 class 进行样式控制（功能类名白名单见 §1）。

| 禁止的 class | 原用途 | 替代方案 |
|-------------|--------|---------|
| `.data-table` | 数据表格 | `<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">` |
| `.row-compliant` | 🟢合规行 | `<tr style="background:#EDF7F0;">` |
| `.row-suspect` | ⚠️存疑行 | `<tr style="background:#FFFBEB;">` |
| `.row-violation` | 🔴违法行 | `<tr style="background:#FFF5F5;">` |
| `.row-confirmed` | ✅印证行 | `<tr style="background:#EDF7F0;">` |
| `.row-partial` | ⚠️部分行 | `<tr style="background:#FFFBEB;">` |
| `.row-missing` | ❌无印证行 | `<tr style="background:#FFF5F5;">` |
| `.row-fatal-break` | 致命断裂行 | `<tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">` |
| `.badge` / `.badge-*` | 徽章 | `<span style="display:inline-block;padding:1px 8px;border-radius:3px;font-size:10pt;font-weight:bold;">` |
| `.tag-*` | 下游标签 | 见 §6.2 内联样式模板 |
| `.info-card` | 信息卡片 | 见 §5 内联样式模板 |
| `.evidence-card` | 证据卡片 | **已废弃** → 使用 §4.2 证据表格 |
| `.module-block` | 模块区块 | `<section style="margin-bottom:28px;">` |
| `.module-heading` | 模块标题 | `<h2 style="font-size:16px;font-weight:600;...">` |
| `.page-header` / `.page-title` / `.page-subtitle` / `.page-meta` | 页面标题区 | 已内置在模板中 |
| `.legend-bar` / `.legend-item` | 图例区 | 已内置在模板中 |
| `.disclaimer-footer` / `.disclaimer-l1` / `.disclaimer-l2` | 免责声明 | 已内置在模板中 |
| `.mermaid-wrap` / `.mermaid-error` | Mermaid容器 | **功能类名白名单**（见 §1），允许按 §7.1 复制；禁止自创其他容器 class |
| `.source-section` | 源码折叠 | **功能类名白名单**（见 §1），允许用于源码折叠区（仅限 `@media print` 隐藏）；禁止用于其他场景 |
| `.print-table` | 打印降级表格 | **功能类名白名单**（见 §1），允许按 §7.3 用于打印降级表格；禁止用于其他场景 |
| `.text-muted` / `.text-warn` / `.text-critical` | 文字颜色 | `color:#64748B;` / `color:#D97706;` / `color:#C53030;` |

**总原则**：如果不确定某个 class 是否合法，**不要使用**，改用内联 `style="..."`。功能类名白名单见 §1。

---

*本文件遵循 compiler/ssot.md §17（SSOT）：产物最小化原则 + base/rule/format-html/ §1.1 内联样式铁律*
*richee_components: [c04]*
