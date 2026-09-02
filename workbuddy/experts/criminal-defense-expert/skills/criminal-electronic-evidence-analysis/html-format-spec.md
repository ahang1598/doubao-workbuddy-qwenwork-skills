# HTML 输出排版规范

> 本文件定义 criminal-electronic-evidence-analysis 技能 HTML 输出的完整排版规范。
> 严肃度：**I-Practical**（内部级），遵循 `base/rule/format-html/format/html-spec.md` §19。
> 视觉方案：**C-现代轻量**（方案C色值：青灰 `#005f73` + 暖橙 `#EE9B00`）。
> 双轨原则：HTML 不是对 Markdown 的重新排版，而是可视化增强版，内容与 Markdown 5件套完全一致。
> **内联样式铁律**：所有排版格式使用 `style="..."` 内联，不依赖 CSS class（遵循 `html-spec.md` §1.1）。

---

## 目录

- [1. 内联样式铁律](#1-内联样式铁律)
- [2. 七色语义色板](#2-七色语义色板)
- [3. 页面结构骨架](#3-页面结构骨架)
- [4. 五大输出块内联样式规范](#4-五大输出块内联样式规范)
- [5. 信息卡片模板](#5-信息卡片模板)
- [6. 风险标记/徽章模板](#6-风险标记徽章模板)
- [7. Mermaid 图表规范](#7-mermaid-图表规范)
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

## 3. 页面结构骨架

```
┌─────────────────────────────────────────────────────┐
│  toolbar（屏幕可见/打印隐藏）              [打印] [折叠]  │
├──────────┬──────────────────────────────────────────┤
│          │  page-header                              │
│          │  刑事电子证据分析报告                        │
│  side-   │  案件信息 / 证据清单 / 分析参数              │
│  nav     ├──────────────────────────────────────────┤
│  固定    │  section-block × 5                        │
│  左侧    │  一、案件基本信息                           │
│  5块     │  二、电子证据解构清单                        │
│  目录    │  三、12维度评估（A/B/C三组）                 │
│          │  四、主体-行为-资金三维映射                   │
│          │  五、可执行下游动作清单                       │
│          ├──────────────────────────────────────────┤
│          │  免责声明                                   │
│          │  页脚 + 版本水印                            │
└──────────┴──────────────────────────────────────────┘
```

### 3.1 侧栏导航

- **宽度**：240px 固定
- **位置**：`position:fixed`，左侧贴边
- **内容**：5 大输出块锚点链接
- **激活态**：当前可视块高亮（`#F0F7F8` 背景 + `#005f73` 左边框）
- **打印**：`display:none` 隐藏

### 3.2 主内容区

- **左边距**：`margin-left:256px`（侧栏 240px + 16px 间距）
- **每块包装**：`<section id="block-N">` 锚点
- **块标题**：`<h2>` + 分隔线 + 块摘要

## 4. 五大输出块内联样式规范

### 4.1 O1：电子证据解构清单表格

> 参考 Richee c04-evidence-catalog（证据目录表）

11列标准格式：

```html
<div style="overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
    <thead>
      <tr>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:40px;">编号</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">名称</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">载体</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:70px;">收集方式</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">完整性</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:100px;">哈希值</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">关键内容</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">主体映射</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">时间戳</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">辩护可用点</th>
        <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">风险等级</th>
      </tr>
    </thead>
    <tbody>
      <!-- 完整性行 -->
      <tr style="background:#EDF7F0;">
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">E01</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">扣押手机（华为Mate40）</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">手机</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">扣押</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
          <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">完整</span>
        </td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;font-family:'Consolas',monospace;font-size:9.5pt;">a1b2c3...</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">微信聊天记录</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">已确认</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">2025.03-05</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">—</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
          <span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">低</span>
        </td>
      </tr>
      <!-- 存疑行 -->
      <tr style="background:#FFFBEB;">
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">E02</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">微信截图12张</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">截图</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">现场提取</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
          <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;">存疑</span>
        </td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;color:#C53030;font-weight:bold;">未提供</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">诈骗话术</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">待验证</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">2025.04</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">无哈希值→原始性可质疑</td>
        <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top;">
          <span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:10pt;font-weight:bold;">中</span>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

**行级着色规则**：

| 风险等级 | 行 style | 说明 |
|---------|---------|------|
| 低 | `background:#EDF7F0;` | 完整性良好+取证合规 |
| 中 | `background:#FFFBEB;` | 瑕疵可补正/主体待验证 |
| 高 | `background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;` | 无哈希值/程序违法/关联断裂 |

**哈希值列格式**：
- 有值：`<span style="font-family:'Consolas',monospace;font-size:9.5pt;">a1b2c3...</span>`
- 未提供：`<span style="color:#C53030;font-weight:bold;">未提供</span>`

**完整性列标签**：

| 状态 | `<span>` style |
|------|---------------|
| 完整 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;` |
| 待验证 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;` |
| 存疑 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;` |
| 缺失 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;` |

### 4.2 O2：12维度评估报告

12维度按A/B/C三组分区，每组用视觉分组区分：

```html
<!-- A组：证据基础维度 -->
<section id="dim-a" style="margin-bottom:24px;">
  <h2 style="font-size:16px;font-weight:600;color:#1A202C;border-bottom:2px solid #005f73;padding-bottom:8px;margin-top:28px;margin-bottom:16px;line-height:1.35;">A组：证据基础维度（能不能用）</h2>

  <!-- A1 载体识别 -->
  <div style="background:#F8FAFC;border-radius:6px;padding:1em 1.2em;margin:0.8em 0;border-left:4px solid #005f73;">
    <h3 style="font-size:13pt;font-weight:600;color:#005f73;margin:0 0 0.5em 0;">A1 载体识别</h3>
    <p style="margin:0.3em 0;"><strong>评估结论：</strong><span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">合规</span></p>
    <p style="margin:0.3em 0;"><strong>事实依据：</strong>扣押清单列明华为Mate40手机1部，封存状态完好</p>
    <p style="margin:0.3em 0;"><strong>风险等级：</strong><span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">低</span></p>
    <p style="margin:0.3em 0;"><strong>应对建议：</strong>—</p>
  </div>

  <!-- A2-A4 同理 -->
</section>

<!-- B组：内容解构维度 -->
<section id="dim-b" style="margin-bottom:24px;">
  <h2 style="font-size:16px;font-weight:600;color:#1A202C;border-bottom:2px solid #EE9B00;padding-bottom:8px;margin-top:28px;margin-bottom:16px;line-height:1.35;">B组：内容解构维度（说了什么）</h2>
  <!-- B5-B8 -->
</section>

<!-- C组：辩护点发现维度 -->
<section id="dim-c" style="margin-bottom:24px;">
  <h2 style="font-size:16px;font-weight:600;color:#1A202C;border-bottom:2px solid #C53030;padding-bottom:8px;margin-top:28px;margin-bottom:16px;line-height:1.35;">C组：辩护点发现维度（对辩方有什么用）</h2>
  <!-- C9-C12 -->
</section>
```

**A/B/C三组视觉区分**：
- A组：标题下边框 `2px solid #005f73`（主色），卡片accent `#005f73`
- B组：标题下边框 `2px solid #EE9B00`（强调橙），卡片accent `#EE9B00`
- C组：标题下边框 `2px solid #C53030`（危险红），卡片accent `#C53030`

**每个维度使用信息卡片**（见 §5），评估结论标签：

| 结论 | `<span>` style |
|------|---------------|
| 合规 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;` |
| 存疑 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFFBEB;color:#D97706;` |
| 不合规 | `display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;` |

**取证程序审查表**（A3专用，参考 Richee c05-risk-list）：

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">审查项</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">法条依据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:80px;">状态</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">备注</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#EDF7F0;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">二名以上侦查人员</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">2016规定第7条</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#EDF7F0;color:#0A6E42;">✅ 合规</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">—</td>
    </tr>
    <tr style="background:#FFF5F5;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">见证人在场</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">2016规定第15条</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:2px 6px;border-radius:2px;background:#FFF5F5;color:#C53030;">❌ 不合规</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">无见证人签名，且无同步录像</td>
    </tr>
  </tbody>
</table>
```

### 4.3 O3：主体-行为-资金三维映射

#### 4.3.1 人物关系图（Mermaid）

```html
<div class="mermaid-wrap" style="background:#fff;border:1px solid #E2E8F0;padding:16px;margin-bottom:0;overflow-x:auto;">
  <pre class="mermaid">
graph TD
    A[嫌疑人张某] -->|微信好友| B[受害人李某]
    A -->|转账| C[第三方账户王某]
    A -->|支付宝| D[收款账户赵某]
  </pre>
</div>
<div class="mermaid-error" style="background:#FFF5F5;border:1px solid #fca5a5;border-radius:4px;padding:12px 16px;margin:12px 0;font-size:12px;color:#991b1b;line-height:1.6;display:none;">
  ⚠️ 人物关系图渲染失败。请展开下方"查看 Mermaid 源码"区域，复制代码到 <a href="https://mermaid.live" target="_blank">mermaid.live</a> 在线渲染。
</div>
```

#### 4.3.2 时间线重建

```html
<div class="mermaid-wrap" style="background:#fff;border:1px solid #E2E8F0;padding:16px;margin-bottom:0;overflow-x:auto;">
  <pre class="mermaid">
timeline
    title 电子数据时间线
    section 资金流
        2025-03-10 : 转账5万元 (E01)
    section 信息流
        2025-03-08 : 微信发送诈骗话术 (E02)
  </pre>
</div>
```

#### 4.3.3 资金流分析

使用通用表格（见 §4.1 样式），行级着色按风险等级。

### 4.4 O4：可执行下游动作清单

> 参考 Richee c05-risk-list（风险清单表）

```html
<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">
  <thead>
    <tr>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:70px;">动作类型</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:60px;">涉及证据</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;">具体建议</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:120px;">下游技能参考</th>
      <th style="padding:8px 10px;text-align:left;white-space:nowrap;background:#005f73;color:#fff;font-weight:bold;width:50px;">优先级</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">排除</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">E02</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">微信截图无哈希值，原始性存疑，依据2016规定第28条申请排除</td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">criminal-evidence-exclusion</span>
      </td>
      <td style="padding:7px 10px;border-bottom:1px solid #E2E8F0;">
        <span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">P0</span>
      </td>
    </tr>
  </tbody>
</table>
```

**行级着色**：
- P0（阻断级）：`background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;`
- P1（重要）：`background:#FFFBEB;`
- P2（建议）：`background:#FFF8EE;`

### 4.5 O5：条件输出块

鉴定意见专项审查（C1）和罪名专攻审查提示（C2）使用 `<details>` 折叠：

```html
<details style="margin:0.8em 0;" open>
  <summary style="font-weight:bold;font-size:12pt;color:#005f73;cursor:pointer;padding:8px 0;border-bottom:1px solid #E2E8F0;">鉴定意见专项审查（C1）</summary>
  <div style="padding:0.5em 0;">
    <!-- 审查内容 -->
  </div>
</details>
```

## 5. 信息卡片模板

> 遵循 `html-spec.md` §19.5 I-Practical 信息卡片

```html
<!-- 案件基本信息卡片 -->
<div style="background:#F0F7F8;border-radius:6px;padding:1em 1.2em;margin:0.8em 0;border-left:4px solid #005f73;">
  <p style="font-size:11pt;font-weight:bold;color:#005f73;margin:0 0 0.4em 0;">📋 案件基本信息</p>
  <!-- 卡片内容 -->
</div>
```

### 5.1 卡片类型

| 卡片 | 用途 | accent 色 | icon | 边框 style |
|------|------|----------|------|-----------|
| case-info | 案件基本信息 | `#005f73` | 📋 | `border-left:4px solid #005f73;` |
| evidence-deconstruct | 证据解构摘要 | `#005f73` | 🔍 | `border-left:4px solid #005f73;` |
| dimension-assessment | 维度评估结论 | `#EE9B00` | 💡 | `border-left:4px solid #EE9B00;` |
| risk-alert | 风险警示 | `#C53030` | ⚠️ | `border-left:4px solid #C53030;` |
| defense-point | 辩护点发现 | `#0A6E42` | 🎯 | `border-left:4px solid #0A6E42;` |
| evidence-gap | 证据缺口 | `#D97706` | 🔎 | `border-left:4px solid #D97706;` |

### 5.2 维度评估卡片按组accent

| 维度组 | accent 色 | 卡片背景 | 标题下边框 |
|--------|----------|---------|----------|
| A组 | `#005f73` | `#F0F7F8` | `2px solid #005f73` |
| B组 | `#EE9B00` | `#FFF8EE` | `2px solid #EE9B00` |
| C组 | `#C53030` | `#FFF5F5` | `2px solid #C53030` |

## 6. 风险标记/徽章模板

### 6.1 风险等级徽章

```html
<!-- 低风险 -->
<span style="display:inline-block;padding:1px 8px;background:#EDF7F0;color:#0A6E42;border-radius:3px;font-size:10pt;font-weight:bold;">低</span>

<!-- 中风险 -->
<span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:10pt;font-weight:bold;">中</span>

<!-- 高风险 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">高</span>
```

### 6.2 优先级徽章

```html
<!-- P0 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:10pt;font-weight:bold;">P0</span>

<!-- P1 -->
<span style="display:inline-block;padding:1px 8px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:10pt;font-weight:bold;">P1</span>

<!-- P2 -->
<span style="display:inline-block;padding:1px 8px;background:#FFF8EE;color:#EE9B00;border-radius:3px;font-size:10pt;font-weight:bold;">P2</span>
```

### 6.3 下游技能标签

```html
<!-- 排除申请 -->
<span style="display:inline-block;padding:1px 6px;background:#FFF5F5;color:#C53030;border-radius:3px;font-size:9pt;">criminal-evidence-exclusion</span>

<!-- 质证提纲 -->
<span style="display:inline-block;padding:1px 6px;background:#FFFBEB;color:#D97706;border-radius:3px;font-size:9pt;">criminal-cross-examination</span>

<!-- 调取证据 -->
<span style="display:inline-block;padding:1px 6px;background:#F0F7F8;color:#005f73;border-radius:3px;font-size:9pt;">criminal-evidence-request</span>
```

### 6.4 瑕疵vs非法标记

```html
<!-- 第27条瑕疵（可补正） -->
<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:10pt;font-weight:bold;background:#FFFBEB;color:#D97706;">⚠️ 瑕疵（第27条，可补正）</span>

<!-- 第28条非法（不得作为定案根据） -->
<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:10pt;font-weight:bold;background:#FFF5F5;color:#C53030;">❌ 非法（第28条，不得作为定案根据）</span>
```

## 7. Mermaid 图表规范

> 遵循 `base/rule/format-html/format/mermaid-spec.md`

### 7.1 Mermaid 容器

```html
<div class="mermaid-wrap" style="background:#fff;border:1px solid #E2E8F0;padding:16px;margin-bottom:0;overflow-x:auto;">
  <pre class="mermaid">
  [Mermaid 语法]
  </pre>
</div>
<div class="mermaid-error" style="background:#FFF5F5;border:1px solid #fca5a5;border-radius:4px;padding:12px 16px;margin:12px 0;font-size:12px;color:#991b1b;line-height:1.6;display:none;">
  ⚠️ 图表渲染失败。请展开下方"查看 Mermaid 源码"区域，复制代码到 <a href="https://mermaid.live" target="_blank">mermaid.live</a> 在线渲染。
</div>
```

### 7.2 Mermaid 语法规范

- 人物关系图：使用 `graph TD`，节点用 `[中文名]`，连线标注关系
- 时间线：使用 `timeline`，按资金流/信息流分段
- 资金流：使用 `graph LR`，从左到右表示资金流向

### 7.3 降级表格

打印时 Mermaid 隐藏，显示降级表格：

```html
<table class="print-table" style="display:none;width:100%;border-collapse:collapse;font-size:10.5pt;">
  <!-- 同源数据的表格版本 -->
</table>
```

## 8. 深度模式折叠映射

| 深度模式 | 覆盖块 | 折叠策略 |
|---------|--------|---------|
| **quick** | 一~二 | 仅基本信息+解构清单，三~五不渲染 |
| **standard** | 一~五 | 基础块展开，条件输出块（C1/C2/C3）默认折叠 |
| **deep** | 一~五+条件 | 全部展开 |

- **standard 模式**：条件输出块用 `<details>`（无 `open` 属性）
- **deep 模式**：所有块用 `<details open>`
- **quick 模式**：只输出一~二，不生成12维度和三维映射

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

> 模板采用 HARD_BLOCK/CONTENT_SLOT 模式。LLM 仅填充以下 CONTENT_SLOT 占位符，禁止修改 HARD_BLOCK 内任何代码。

| 序号 | 占位符 | 填充内容 | 说明 |
|------|--------|---------|------|
| SLOT-0 | `PAGE_TITLE` | "刑事电子证据分析报告" | 页面主标题（h1） |
| SLOT-1 | `SUBTITLE` | "[案件名称] · [涉嫌罪名] · [罪名路由]" | 副标题 |
| SLOT-1' | `PAGE_META` | "分析日期：XXX \| 辩护视角：XXX \| [生成时间]" | 元信息行 |
| SLOT-2 | `CASE_INFO` | 案件基本信息 HTML 块 | 案件信息+证据统计（使用内联样式） |
| SLOT-3 | `BLOCK_1_TO_5` | 五大输出块内容 HTML 块 | 解构清单+12维度+三维映射+下游动作（使用内联样式） |
| SLOT-4 | `CONDITIONAL_BLOCKS` | 条件输出块 HTML 块 | C1鉴定审查+C2罪名专攻+C3删除恢复（使用内联样式） |
| SLOT-5 | `DISCLAIMER_STYLE` | L2 免责声明样式 | `border-left:3px solid #C53030;background:#fef9f9;` |
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

输出：HTML 完整生成基础块（一~二），12维度评估（三）标注 `[待补充：需要更完整的证据描述]`，三维映射和下游动作为简化版。缺失块使用灰色边框：`border:1px solid #E2E8F0;background:#F8FAFC;color:#64748B;padding:12px;`。

### 11.3 S3 降级（轻度）

触发：选填输入缺失（无鉴定意见/无哈希值/无扣押清单等）。

输出：HTML 完整生成，条件输出块标注 `[未提供相关材料，跳过本模块]`，灰色文字：`color:#64748B;`。

## 12. 禁止使用的类名清单

> 以下 CSS class 名 LLM 在 CONTENT_SLOT 中**禁止**使用。所有样式使用内联 `style="..."`。

| 禁止的 class | 原用途 | 替代方案 |
|-------------|--------|---------|
| `.data-table` | 数据表格 | `<table style="width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.5;">` |
| `.row-high-risk` | 高风险行 | `<tr style="background:#FFF5F5;font-weight:bold;border-left:3px solid #C53030;">` |
| `.row-medium-risk` | 中风险行 | `<tr style="background:#FFFBEB;">` |
| `.row-low-risk` | 低风险行 | `<tr style="background:#EDF7F0;">` |
| `.badge` / `.badge-*` | 徽章 | `<span style="display:inline-block;padding:1px 8px;border-radius:3px;font-size:10pt;font-weight:bold;">` |
| `.tag-*` | 标签 | 见 §6.3 内联样式模板 |
| `.info-card` | 信息卡片 | 见 §5 内联样式模板 |
| `.evidence-table` | 证据表格 | 见 §4.1 内联样式模板 |
| `.dimension-card` | 维度卡片 | 见 §4.2 内联样式模板 |
| `.hash-value` | 哈希值显示 | `font-family:'Consolas',monospace;font-size:9.5pt;` |
| `.module-block` | 模块区块 | `<section style="margin-bottom:28px;">` |
| `.module-heading` | 模块标题 | `<h2 style="font-size:16px;font-weight:600;...">` |
| `.text-muted` / `.text-warn` / `.text-critical` | 文字颜色 | `color:#64748B;` / `color:#D97706;` / `color:#C53030;` |

**总原则**：如果不确定某个 class 是否合法，**不要使用**，改用内联 `style="..."`。功能类名白名单见 §1。

---

*本文件遵循 compiler/ssot.md §17（SSOT）：产物最小化原则 + base/rule/format-html/ §1.1 内联样式铁律*
*richee_components: [c04-evidence-catalog, c05-risk-list]*
