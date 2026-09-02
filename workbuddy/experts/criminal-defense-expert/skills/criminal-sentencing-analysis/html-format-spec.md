# HTML 输出排版规范

> 本文件定义 criminal-sentencing-analysis 技能 HTML 输出的完整排版规范。
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
- [7. Mermaid 量刑区间图规范](#7-mermaid-量刑区间图规范)
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
  - `class="mermaid"` — Mermaid 库硬性要求
  - `class="mermaid-wrap"` — Mermaid 容器
  - `class="mermaid-error"` — Mermaid 渲染失败降级提示区
  - `class="print-table"` — 打印降级表格
  - `class="source-section"` — 源码折叠区
- **HARD_BLOCK 骨架专用 class**（模板内置，LLM 禁止使用或模仿）：`side-nav`/`main-content`/`toolbar`/`toolbar-btn`/`no-print`/`template-version-watermark`/`page-break-before`/`active`/`visible`

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
| 🟢从轻/有利 | `background:#EDF7F0;` | 从轻情节/缓刑条件符合 |
| ⚠️从重/需关注 | `background:#FFFBEB;` | 从重情节/地区差异 |
| 🔴禁止/不利 | `background:#FFF5F5;` | 禁止缓刑情形/不利因素 |
| 🔵待核实 | `background:#F0F7F8;` | 需核实当地规定 |
| 法定刑区间 | `background:#F8FAFC;` | 灰色基准区间 |

### 3.3 模块标题

```html
<section id="module-N" style="margin-bottom:28px;">
  <h2 style="font-size:16px;font-weight:600;color:#1A202C;border-bottom:1px solid #E2E8F0;padding-bottom:8px;margin-top:28px;margin-bottom:16px;line-height:1.35;">一、法定刑分析</h2>
  <!-- 模块内容 -->
</section>
```

### 3.4 高级模块折叠

```html
<details style="margin:0.8em 0;">
  <summary style="font-weight:bold;font-size:12pt;color:#005f73;cursor:pointer;padding:8px 0;border-bottom:1px solid #E2E8F0;">五、缓刑可能性评估</summary>
  <div style="padding:0.5em 0;">
    <!-- 模块内容 -->
  </div>
</details>
```

## 4. 六模块内联样式规范

### 4.1 模块一：法定刑分析 — 法定刑幅度表

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">罪名</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">法条依据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">量刑档次</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">法定刑幅度</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#F8FAFC;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">盗窃罪</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">刑法第264条</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">数额较大</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">三年以下有期徒刑/拘役/管制</td>
    </tr>
  </tbody>
</table>
```

### 4.2 模块二：基准刑确定

通用表格（§3.1），无特殊着色。

### 4.3 模块三：情节调节交互表

从重/从轻/减轻三类分别行，含累计调节方向箭头：

```html
<h3 style="font-size:13pt;font-weight:600;color:#C53030;margin:16px 0 8px 0;">从重情节</h3>
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">情节</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">调节比例</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">法条依据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">条文性质</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">说明</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#FFF5F5;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">累犯</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;color:#C53030;font-weight:bold;">+10%~+30%</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">刑法第65条</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">应当</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">法定从重</td>
    </tr>
  </tbody>
</table>

<h3 style="font-size:13pt;font-weight:600;color:#0A6E42;margin:16px 0 8px 0;">从轻/减轻情节</h3>
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">情节</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">调节比例</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">法条依据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">条文性质</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">说明</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">坦白</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;color:#0A6E42;font-weight:bold;">-20%以下</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">刑法第67条第3款</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">可以</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">授权性从轻</td>
    </tr>
  </tbody>
</table>
```

**行级着色规则**：从重情节行 `background:#FFF5F5;`，从轻情节行 `background:#EDF7F0;`，减轻情节行 `background:#F0F7F8;`。

**条文性质标签**：

| 性质 | `<span>` style |
|------|---------------|
| 应当（命令性） | `display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;` |
| 可以（授权性） | `display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;` |

**综合调节计算块**：

```html
<div style="background:#F0F7F8;border-left:4px solid #005f73;border-radius:4px;padding:12px 16px;margin:12px 0;">
  <p style="font-size:11pt;font-weight:bold;color:#005f73;margin:0 0 8px 0;">📊 综合调节计算</p>
  <p style="font-size:10.5pt;color:#1A202C;margin:0;line-height:1.8;">
    基准刑 <strong>[X个月]</strong> × (1 + 从重 <span style="color:#C53030;">[+Y%]</span> - 从轻 <span style="color:#0A6E42;">[-Z%]</span>) = <strong>预计刑期 [N个月]</strong>
  </p>
</div>
```

### 4.4 模块四：量刑区间可视化图

纯HTML CSS水平柱状图（法定刑/调节后/预测三色）：

```html
<div style="margin:16px 0;padding:12px 0;">
  <!-- 法定刑区间 -->
  <div style="margin-bottom:8px;">
    <span style="display:inline-block;width:100px;font-size:10pt;color:#64748B;text-align:right;padding-right:8px;">法定刑</span>
    <span style="display:inline-block;width:300px;height:24px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:3px;position:relative;">
      <span style="position:absolute;left:0;top:0;height:100%;background:#64748B;border-radius:3px;width:100%;"></span>
      <span style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);color:#fff;font-size:9pt;font-weight:bold;">6个月 - 3年</span>
    </span>
  </div>
  <!-- 调节后区间 -->
  <div style="margin-bottom:8px;">
    <span style="display:inline-block;width:100px;font-size:10pt;color:#005f73;text-align:right;padding-right:8px;">调节后</span>
    <span style="display:inline-block;width:300px;height:24px;background:#F0F7F8;border:1px solid #005f73;border-radius:3px;position:relative;">
      <span style="position:absolute;left:10%;top:0;height:100%;background:#005f73;border-radius:3px;width:30%;"></span>
      <span style="position:absolute;left:25%;top:50%;transform:translate(-50%,-50%);color:#fff;font-size:9pt;font-weight:bold;">8-12个月</span>
    </span>
  </div>
  <!-- 预测区间 -->
  <div style="margin-bottom:8px;">
    <span style="display:inline-block;width:100px;font-size:10pt;color:#0A6E42;text-align:right;padding-right:8px;">预测</span>
    <span style="display:inline-block;width:300px;height:24px;background:#EDF7F0;border:1px solid #0A6E42;border-radius:3px;position:relative;">
      <span style="position:absolute;left:15%;top:0;height:100%;background:#0A6E42;border-radius:3px;width:20%;"></span>
      <span style="position:absolute;left:25%;top:50%;transform:translate(-50%,-50%);color:#fff;font-size:9pt;font-weight:bold;">6-10个月</span>
    </span>
  </div>
</div>
```

### 4.5 模块五：缓刑可能性评估 — 五条件逐项审查表

> 刑法第72条：1个前提条件 + 4个实质条件 = 5项逐项审查

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:40px;">#</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">条件</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">是否符合</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">分析说明</th>
    </tr>
  </thead>
  <tbody>
    <!-- 前提条件 -->
    <tr style="background:#F0F7F8;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">1</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;"><strong>前提条件</strong>：被判处拘役/三年以下有期徒刑</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 是</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">预计刑期6-10个月，符合"三年以下"条件</td>
    </tr>
    <!-- 实质条件(一) -->
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">2</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">(一) 犯罪情节较轻</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 是</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">初犯+金额不大+全额退赃+谅解</td>
    </tr>
    <!-- 实质条件(二) -->
    <tr>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">3</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">(二) 有悔罪表现</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 是</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">如实供述+退赃+谅解</td>
    </tr>
    <!-- 实质条件(三) -->
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">4</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">(三) 没有再犯罪的危险</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 是</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">初犯+有稳定工作+固定住所</td>
    </tr>
    <!-- 实质条件(四) -->
    <tr>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">5</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">(四) 对所居住社区没有重大不良影响</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 是</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">需社区矫正评估确认</td>
    </tr>
  </tbody>
</table>
```

**行级着色**：前提条件行 `background:#F0F7F8;`（蓝色，区分前提与实质），符合条件的实质条件行 `background:#EDF7F0;`（绿色），不符合条件行 `background:#FFF5F5;`（红色）。

**禁止缓刑情形提示**：

```html
<div style="background:#FFF5F5;border-left:4px solid #C53030;border-radius:4px;padding:12px 16px;margin:12px 0;">
  <p style="font-size:11pt;font-weight:bold;color:#C53030;margin:0 0 4px 0;">🚫 禁止缓刑情形</p>
  <p style="font-size:10.5pt;color:#1A202C;margin:0;">累犯不适用缓刑（刑法第74条）</p>
</div>
```

### 4.6 模块六：风险提示

```html
<div style="background:#FFF5F5;border-left:3px solid #C53030;border-radius:4px;padding:12px 16px;margin:12px 0;">
  <p style="font-size:10pt;color:#1A202C;margin:0 0 4px 0;font-weight:bold;">⚠️ L2 中风险提示</p>
  <p style="font-size:9.5pt;color:#64748B;margin:0;line-height:1.6;">量刑预测仅为参考，不替代法官裁判，不承诺量刑结果。地区差异可能影响实际量刑。</p>
</div>
```

## 5. 信息卡片模板

> 遵循 `html-spec.md` §19.5 I-Practical 信息卡片

```html
<!-- 案件信息卡片 -->
<div style="background:#F0F7F8;border-radius:6px;padding:1em 1.2em;margin:0.8em 0;border-left:4px solid #005f73;">
  <p style="font-size:11pt;font-weight:bold;color:#005f73;margin:0 0 0.4em 0;">📋 案件信息</p>
  <!-- 卡片内容 -->
</div>
```

### 5.1 卡片类型

| 卡片 | accent 色 | icon | 边框 style |
|------|----------|------|-----------|
| case-info | `#005f73` | 📋 | `border-left:4px solid #005f73;` |
| sentencing-result | `#EE9B00` | 💡 | `border-left:4px solid #EE9B00;` |
| probation-risk | `#C53030` | 🔴 | `border-left:4px solid #C53030;` |
| favorable | `#0A6E42` | 🟢 | `border-left:4px solid #0A6E42;` |
| regional-note | `#D97706` | 🔍 | `border-left:4px solid #D97706;` |

## 6. 风险标记/徽章模板

### 6.1 行内风险徽章

```html
<!-- ✅ 绿色：从轻/符合条件 -->
<span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">✅ 从轻</span>

<!-- ⚠️ 琥珀：需关注/地区差异 -->
<span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:10pt;font-weight:bold;">⚠️ 待核实</span>

<!-- ❌ 红色：从重/禁止 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">❌ 从重</span>
```

### 6.2 条文性质徽章

```html
<!-- 命令性"应当" -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">应当</span>

<!-- 授权性"可以" -->
<span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">可以</span>

<!-- 禁止性"不得" -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">不得</span>
```

## 7. Mermaid 量刑区间图规范

### 7.1 Mermaid 容器（可选，若需要可视化量刑逻辑链）

```html
<div class="mermaid-wrap" style="background:#fff;border:1px solid #E2E8F0;padding:16px;margin-bottom:0;overflow-x:auto;">
  <pre class="mermaid">
graph LR
    A["法定刑幅度<br>6个月-3年"] --> B["基准刑<br>19.5个月"]
    B --> C["从重调节<br>累犯+20%"]
    B --> D["从轻调节<br>坦白-20%<br>退赃-30%"]
    C --> E["调节后<br>约8个月"]
    D --> E
    E --> F["预测区间<br>6-10个月"]
  </pre>
</div>
<div class="mermaid-error" style="background:#FFF5F5;border:1px solid #fca5a5;border-radius:4px;padding:12px 16px;margin:12px 0;font-size:12px;color:#991b1b;line-height:1.6;display:none;">
  ⚠️ 量刑逻辑图渲染失败。请展开下方"查看 Mermaid 源码"区域，复制代码到 <a href="https://mermaid.live" target="_blank">mermaid.live</a> 在线渲染。
</div>
```

### 7.2 降级表格

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
| **standard** | 模块一~六 | 基础模块展开，高级模块（五~六）默认折叠 |
| **deep** | 模块一~六 | 全部展开 |

- **standard 模式**：模块五~六用 `<details>`（无 `open` 属性）
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
| SLOT-0 | `PAGE_TITLE` | "量刑预测与辩护分析" | 页面主标题（h1） |
| SLOT-1 | `SUBTITLE` | "[被告人] · [涉嫌罪名] · [管辖地区]" | 副标题 |
| SLOT-1' | `PAGE_META` | "量刑分析 \| 分析人：XXX \| [生成时间]" | 元信息行 |
| SLOT-2 | `CASE_INFO` | 案件信息 HTML 块 | 案件信息+量刑参数（使用内联样式） |
| SLOT-3 | `MODULE_1_TO_6` | 六模块内容 HTML 块 | 法定刑分析→风险提示（使用内联样式） |
| SLOT-4 | `DISCLAIMER_STYLE` | L2 免责声明样式 | L2="border-left:3px solid #C53030;background:#fef9f9;" |
| 工具栏 | `GENERATED_AT` | YYYY-MM-DD HH:mm:ss | 生成时间戳（工具栏+页脚水印，2处同值） |

**CONTENT_SLOT 填充铁律**：
- 所有 HTML 元素使用 `style="..."` 内联样式
- 禁止使用 CSS class 进行样式控制（功能类名白名单见 §1）
- 禁止创建 `<style>` 块或 `<link>` 标签
- 禁止修改 HARD_BLOCK 内任何代码

## 11. 降级输出规则

### 11.1 S1 降级（最强约束）

触发：`defendant_name` 或 `alleged_crime` 或 `case_facts` 缺失。

输出：不生成 HTML，仅输出 Markdown 纯文本错误提示。

### 11.2 S2 降级（中度）

触发：情节信息缺失过半。

输出：HTML 完整生成基础模块（一~三），高级模块（四~六）标注 `[待补充：需要更完整的情节信息]`，灰色边框：`border:1px solid #E2E8F0;background:#F8FAFC;color:#64748B;padding:12px;`。

### 11.3 S3 降级（轻度）

触发：管辖地区缺失。

输出：HTML 完整生成，地区差异标注 `[适用全国标准，需核实当地规定]`，蓝色文字：`color:#005f73;`。

## 12. 禁止使用的类名清单

> 以下 CSS class 名已从模板中移除。LLM 在 CONTENT_SLOT 中**禁止**使用任何 class 进行样式控制（功能类名白名单见 §1）。

| 禁止的 class | 原用途 | 替代方案 |
|-------------|--------|---------|
| `.data-table` | 数据表格 | `<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">` |
| `.row-heavy` | 从重行 | `<tr style="background:#FFF5F5;">` |
| `.row-mitigate` | 从轻行 | `<tr style="background:#EDF7F0;">` |
| `.row-confirm` | ✅符合行 | `<tr style="background:#EDF7F0;">` |
| `.row-warning` | ⚠️待核实行 | `<tr style="background:#FFFBEB;">` |
| `.row-violation` | ❌不符合行 | `<tr style="background:#FFF5F5;">` |
| `.badge` / `.badge-*` | 徽章 | `<span style="display:inline-block;padding:1px 8px;border-radius:3px;font-size:10pt;font-weight:bold;">` |
| `.tag-*` | 条文性质标签 | 见 §6.2 内联样式模板 |
| `.info-card` | 信息卡片 | 见 §5 内联样式模板 |
| `.module-block` | 模块区块 | `<section style="margin-bottom:28px;">` |
| `.module-heading` | 模块标题 | `<h2 style="font-size:16px;font-weight:600;...">` |
| `.page-header` / `.page-title` / `.page-subtitle` / `.page-meta` | 页面标题区 | 已内置在模板中 |
| `.legend-bar` / `.legend-item` | 图例区 | 已内置在模板中 |
| `.disclaimer-footer` / `.disclaimer-l2` | 免责声明 | 已内置在模板中 |
| `.mermaid-wrap` / `.mermaid-error` | Mermaid容器 | **功能类名白名单**（见 §1），允许按 §7.1 复制；禁止自创其他容器 class |
| `.source-section` | 源码折叠 | **功能类名白名单**（见 §1），仅限 `@media print` 隐藏 |
| `.print-table` | 打印降级表格 | **功能类名白名单**（见 §1），允许按 §7.2 用于打印降级 |
| `.text-muted` / `.text-warn` / `.text-critical` | 文字颜色 | `color:#64748B;` / `color:#D97706;` / `color:#C53030;` |

**总原则**：如果不确定某个 class 是否合法，**不要使用**，改用内联 `style="..."`。功能类名白名单见 §1。

---

*本文件遵循 compiler/ssot.md §17（SSOT）：产物最小化原则 + base/rule/format-html/ §1.1 内联样式铁律*
*richee_components: [c04]*
