# HTML 输出排版规范 v2.2.0

> 本文件定义 criminal-communication-guide 技能 HTML 输出的完整排版规范。
> 严肃度：**I-Practical**（内部级），遵循 `base/rule/format-html/format/html-spec.md` §19。
> 视觉方案：**C-现代轻量**（BCG 风格：青灰 `#005F73` + 暖橙 `#EE9B00`）。
> 纯 HTML 输出：唯一产物为 HTML 文件，不输出 Markdown。
> **v2.2.0 架构升级**：三层信息架构（仪表盘→详情→工具）+ Mermaid CDN 图表引擎。

---

## 目录

- [1. 严肃度参数](#1-严肃度参数)
- [2. 三层信息架构](#2-三层信息架构)
- [3. 七色语义色板](#3-七色语义色板)
- [4. 页面结构骨架](#4-页面结构骨架)
- [5. 侧栏导航规范](#5-侧栏导航规范)
- [6. Mermaid 图表引擎规则](#6-mermaid-图表引擎规则)
- [7. L1 仪表盘规范](#7-l1-仪表盘规范)
- [8. L2 详情层模块图表化规则](#8-l2-详情层模块图表化规则)
- [9. L3 工具层规范](#9-l3-工具层规范)
- [10. CSS 专用组件规范](#10-css-专用组件规范)
- [11. 占位符清单](#11-占位符清单)
- [12. 打印适配参数](#12-打印适配参数)
- [13. 降级输出规则](#13-降级输出规则)

---

## 1. 严肃度参数

| 参数 | 值 | 来源 |
|------|-----|------|
| 严肃度级别 | **I-Practical** | 内部产物，允许 Emoji/折叠/卡片/图表 |
| 视觉方案 | **C-现代轻量**（BCG 风格） | `html-spec.md` §19.5 |
| 主色 | `#005F73`（青灰） | 标题/分隔线/表头/导航选中 |
| 强调色 | `#EE9B00`（暖橙） | 风险标记/警告/信息卡片 accent |
| 图表引擎 | **Mermaid v11 CDN** | jsdelivr CDN，LLM 仅填充 Mermaid 源码 |
| @page margin | `2.0cm 1.5cm 1.5cm 3.0cm` | I-Practical 标准 |
| body font | `微软雅黑, 11pt` | 统一使用 pt 单位 |
| line-height | `1.6`（屏幕）/ `1.8`（打印） | |
| 允许元素 | Mermaid 图表 / Emoji / 折叠/卡片/侧栏 / CSS 进度环/热力图/光谱条 | |

---

## 2. 三层信息架构

v2.2.0 将页面从"顺序阅读的电子书"重构为"三层操作台"：

```
┌─────────────────────────────────────────┐
│  L1 仪表盘层 (Dashboard)    ← 30秒扫完   │
│  策略总图(flowchart) 风险热力图(CSS Grid) │
│  准备进度环 今日行动卡片                  │
├─────────────────────────────────────────┤
│  L2 详情层 (Details)        ← 深入了解    │
│  O1 准备清单 O2 红线决策树 O5 甘特图      │
├─────────────────────────────────────────┤
│  L3 工具层 (Tools)          ← 通话中用    │
│  O3 潜台词决策树 O4 力度光谱条 C1 场景图  │
└─────────────────────────────────────────┘
```

### 2.1 三层使用场景对照

| 场景 | 层 | 动作 |
|------|-----|------|
| 打电话前快速确认 | L1 | 扫策略总图→看热力图→确认行动卡片 |
| 需深入了解某话题 | L2 | 展开模块详情→阅读完整内容 |
| 通话中查潜台词 | L3 | 在决策树上找根节点→跟箭头→看应对 |
| 通话中调整力度 | L3 | 看光谱条上的推荐位置→上下微调 |

---

## 3. 七色语义色板

| 颜色名 | Hex | 用途 | 使用场景 |
|--------|-----|------|---------|
| **primary-dark** | `#005F73` | 主色-深 | 大标题/分隔线/表头背景/导航 |
| **primary-light** | `#F0F7F8` | 主色-浅 | 信息卡片背景/斑马纹 |
| **accent-orange** | `#EE9B00` | 强调橙 | 警告/必检清单/行动卡片 accent |
| **accent-orange-light** | `#FFF8EE` | 强调橙-浅 | 橙色行高亮 |
| **success-green** | `#0A6E42` | 安全绿 | ✅安全替代/温和力度/低风险 |
| **success-green-light** | `#EDF7F0` | 安全绿-浅 | 安全行背景 |
| **warning-amber** | `#D97706` | 警告琥珀 | ⚠️中等风险/需注意 |
| **warning-amber-light** | `#FFFBEB` | 警告琥珀-浅 | 警告行背景 |
| **danger-red** | `#C53030` | 危险红 | 🔴红线/高强度/高风险 |
| **danger-red-light** | `#FFF5F5` | 危险红-浅 | 红线行背景 |
| **neutral-gray** | `#64748B` | 中性灰 | 辅助文字/时间轴已过 |
| **neutral-light** | `#F8FAFC` | 中性灰-浅 | 斑马纹/折叠区背景 |
| **border-gray** | `#E2E8F0` | 边框灰 | 表格分隔线/卡片边框 |
| **text-dark** | `#1A202C` | 正文黑 | 正文 |

### 3.1 力度三档专用色

| 力度档 | 深色 | 浅色 | 含义 |
|--------|------|------|------|
| 温和 | `#0A6E42` | `#EDF7F0` | 探询式、合作性 |
| 坚定 | `#005F73` | `#F0F7F8` | 权利主张式、有理有据 |
| 强硬 | `#C53030` | `#FFF5F5` | 程序施压式、不留退路 |

### 3.2 热力图专用色（5 级）

| 等级 | 颜色 | 含义 |
|------|------|------|
| L0 安全 | `#EDF7F0`（绿浅） | 无风险，可自由沟通 |
| L1 注意 | `#FFFBEB`（琥珀浅） | 需谨慎措辞 |
| L2 警告 | `#FFF8EE`（橙浅） | 需充分准备 |
| L3 高风险 | `#FFF5F5`（红浅） | 强烈不推荐 |
| L4 禁区 | `#C53030`（红深） | 绝对禁止 |

---

## 4. 页面结构骨架

```
┌──────────────────────────────────────────────────────────┐
│  toolbar（屏幕可见/打印隐藏）               [折叠侧栏] [打印] │
├─────┬────────────────────────────────────────────────────┤
│  ≡  │  ╔══════════════════════════════════════════════╗  │
│  📊 │  ║  L1 仪表盘                                    ║  │
│  📋 │  ║  ┌──────────────┐ ┌──────────┐ ┌──────────┐║  │
│  🚫 │  ║  │策略总图       │ │风险热力图  │ │今日行动   │║  │
│  🗣️ │  ║  │(MERMAID_SLOT) │ │(CSS Grid) │ │(卡片)     │║  │
│  📏 │  ║  └──────────────┘ └──────────┘ └──────────┘║  │
│  ⏱️ │  ╚══════════════════════════════════════════════╝  │
│  📖 │  ────────────────────────────────────────────────  │
│  ✏️ │  L2 详情层                                          │
│     │  O1 准备进度环 + 卡片墙                             │
│     │  O2 红线替代决策树 (MERMAID_SLOT) + 清单表格         │
│     │  O5 甘特图时间窗 (MERMAID_SLOT)                     │
│     ├────────────────────────────────────────────────────│
│     │  L3 工具层                                          │
│     │  O3 潜台词决策树 (MERMAID_SLOT) + 折叠详情           │
│     │  O4 力度光谱条 (CSS linear-gradient) + 场景映射      │
│     │  C1 场景流程图 ×N (MERMAID_SLOT) + 折叠详情         │
│     │  O7 沟通记录表单                                     │
│     ├────────────────────────────────────────────────────│
│     │  免责声明 + 律师必检清单 + 版本水印                    │
└─────┴────────────────────────────────────────────────────┘
```

---

## 5. 侧栏导航规范

### 5.1 折叠模式

- **默认态**：50px 宽图标列（仅显示 Emoji 图标：📊📋🚫🗣️📏⏱️📖✏️）
- **展开态**：hover 时展开到 240px，显示完整文字标签
- **过渡动画**：`transition: width 0.25s ease`
- **打印**：`display:none` 隐藏

### 5.2 侧栏图标→模块映射

| 图标 | 锚点 | 目标模块 |
|------|------|---------|
| 📊 | `#dashboard` | L1 仪表盘 |
| 📋 | `#module-o1` | O1 准备清单 |
| 🚫 | `#module-o2` | O2 红线清单 |
| 🗣️ | `#module-o3` | O3 潜台词词典 |
| 📏 | `#module-o4` | O4 力度校准 |
| ⏱️ | `#module-o5` | O5 时间窗口 |
| 📖 | `#module-c1` | C1 特殊场景 |
| ✏️ | `#module-o7` | O7 沟通记录 |

---

## 6. Mermaid 图表引擎规则

### 6.1 CDN 引入

```html
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
```

**初始化**（模板内置，LLM 不可修改）：
```js
mermaid.initialize({ startOnLoad: true, theme: 'base',
  themeVariables: {
    primaryColor: '#F0F7F8', primaryBorderColor: '#005F73',
    primaryTextColor: '#1A202C', lineColor: '#64748B',
    secondaryColor: '#FFF8EE', tertiaryColor: '#EDF7F0',
    fontSize: '12px'
  }
});
```

### 6.2 LLM 职责

LLM **仅填充** `<!-- MERMAID_SLOT:xxx -->` 占位符内的 Mermaid 源码。禁止修改 `<script>` 初始化块。

**MERMAID_SLOT 格式**：
```html
<!-- MERMAID_SLOT:MS-1_START -->
<div class="mermaid">
flowchart TD
  A[开始] --> B{判断}
  B -->|是| C[行动1]
  B -->|否| D[行动2]
</div>
<!-- MERMAID_SLOT:MS-1_END -->
```

### 6.3 6 张 Mermaid 图表清单

| SLOT | 图表 | 类型 | 位置 | 方向 | 节点数上限 | 说明 |
|------|------|------|------|------|-----------|------|
| MS-1 | 通信策略总图 | `flowchart TD` | L1 仪表盘 | 纵向 | 20 | 一图看懂：谁→说什么→不能碰→下一步→被拒怎么办 |
| MS-2 | 红线-替代决策树 | `flowchart LR` | O2 | 横向 | 25 | "话题→对象→红线→安全替代" 决策路径 |
| MS-3 | 潜台词决策树 | `flowchart TD` | O3 | 纵向 | 30 | "对方说→3种可能含义→每种应对" |
| MS-5 | 甘特图时间窗 | `gantt` | O5 | 横向 | — | 沟通行动/法律节点/备选路径 3 轨道 |
| MS-6a | 场景流程图-主要 | `flowchart TD` | C1 | 纵向 | 15 | 第一个特殊场景的分步流程图 |
| MS-6b | 场景流程图-次要 | `flowchart TD` | C1 | 纵向 | 15 | 第二个特殊场景的分步流程图 |

### 6.4 Mermaid 语法约束

1. **节点文本禁止使用 `()`**，使用 `[]` 或 `{}`
2. **分支条件文本**使用 `|是|` / `|否|` 格式
3. **flowchart 必须首行声明方向**：`flowchart TD` 或 `flowchart LR`
4. **gantt 图表**必须使用 `dateFormat YYYY-MM-DD` 格式
5. **节点内文字**控制在 15 字以内，超长用 `\n` 换行
6. **禁止使用 HTML 标签**在 Mermaid 源码内（如 `<br/>`），用 `\n` 替代

### 6.5 CDN 降级

CDN 不可用时，Mermaid 图无法渲染。模板内置降级逻辑：
- 显示 `<div class="mermaid-fallback">` 备用纯文本
- 备用文本内容由 `<!-- MERMAID_SLOT:MS-x_FALLBACK -->` 占位符控制
- LLM 为每个图表填充对应的纯文本替代（150 字内摘要）

---

## 7. L1 仪表盘规范

仪表盘为三层信息架构的第一层，位于页面标题区下方，包含 3 个核心可视化组件。

### 7.1 仪表盘布局

```html
<div id="dashboard" class="dashboard">
  <div class="dashboard-grid">
    <div class="dashboard-card dashboard-card--wide">
      <!-- MERMAID_SLOT:MS-1 策略总图 -->
    </div>
    <div class="dashboard-card">
      <!-- 风险热力图 (CSS Grid) -->
    </div>
    <div class="dashboard-card dashboard-card--actions">
      <!-- 今日行动卡片 ×3 -->
    </div>
  </div>
  <div class="dashboard-progress">
    <!-- 4 个准备进度环 -->
  </div>
</div>
```

**Grid 布局**：`grid-template-columns: 1.6fr 1fr 1fr`（三栏不等宽）

### 7.2 MS-1 通信策略总图

`flowchart TD` 纵向流程图。要求覆盖：
- **起点**：当前沟通目标（如"取保候审申请"）
- **第一层**：沟通对象 + 最佳时机
- **第二层**：核心论点 + 支持证据
- **第三层**：不可触碰的红线（红色节点，用 `#FFF5F5` 底色标注）
- **第四层**：预期回应 + 应对
- **第五层**：被拒后的备选路径

缩略展示在仪表盘卡片中，点击可展开全屏。

### 7.3 风险热力图 (CSS Grid)

6×3 矩阵：横向=沟通话题（认罪认罚/定性争议/程序推进/家属沟通/证据讨论/投诉威胁），纵向=沟通对象（公安/检察院/法院）。

每格颜色=风险等级：
- L0 安全 → `#EDF7F0` + `✓` 文字
- L1 注意 → `#FFFBEB` + `⚠` 文字
- L2 警告 → `#FFF8EE` + `⚡` 文字
- L3 高风险 → `#FFF5F5` + `✗` 文字
- L4 禁区 → `#C53030` + `🚫` 文字（白色）

**LLM 填充方式**：在 CONTENT_SLOT:HEATMAP 中为每个 `<td>` 填入 `class="heat-l0"` ~ `heat-l4`。

### 7.4 今日行动卡片

3 张带优先级颜色的行动卡片：
1. **🔴 立即**：今天必须完成的沟通准备（红色左边框）
2. **🟡 今日**：今天应推进的事项（琥珀色左边框）
3. **🟢 本周**：本周应关注的窗口（绿色左边框）

每张卡片含：行动标题 + 一句话描述 + 截止时间（如有）。

### 7.5 准备进度环

4 个 CSS conic-gradient 环形进度条，表示 4 类准备的完成度：
- **材料**（`--force-gentle` 绿）：必备材料准备
- **法条**（`--force-firm` 青）：法条检索完成
- **预判**（`--accent-orange` 橙）：对方关注点预判
- **预案**（`--danger-red` 红）：最坏情况预案

LLM 填充方式：在每个进度环的 `--progress-percent` CSS 变量中填入 0-100 的值。

---

## 8. L2 详情层模块图表化规则

### 8.1 O1 沟通前准备清单

**旧方案**：4 段式可勾选清单
**新方案**：进度环（已上移到 L1 仪表盘）+ 折叠详情卡片墙

```html
<details class="prep-detail">
  <summary>📋 必备材料（4/4 已准备）</summary>
  <ul class="checklist"><li>...</li></ul>
</details>
```

四类详情都用 `<details>` 折叠，summary 显示完成状态。

### 8.2 O2 沟通红线清单

**旧方案**：6 张红绿对比卡片
**新方案**：**MS-2 红线-替代决策树**（flowchart LR）+ 折叠清单表格

MS-2 决策树结构：
```
起点[我想讨论XXX话题] → 分支{沟通对象是谁？}
  → 公安 → 分支{这个话题对公安安全吗？}
    → 是 → [可直接沟通 + 建议力度]
    → 否 → [红线：具体禁止行为] → [安全替代：具体可说的话]
  → 检察院 → ...
  → 法院 → ...
```

决策树下方折叠完整红线清单表格（`details`），供精确查阅。

### 8.3 O3 潜台词解读词典 → 移至 L3 工具层

### 8.4 O4 力度校准指南 → 移至 L3 工具层

### 8.5 O5 黄金时间窗口

**旧方案**：竖线时间轴 + 下方汇总表
**新方案**：**MS-5 甘特图**（Mermaid gantt）取代时间轴和汇总表

甘特图 3 条并行轨道：
1. **沟通行动**：取保申请提交→跟进→约见检察官
2. **法律节点**：拘留日→提请批捕日→批捕审查期满日
3. **备选路径**：羁押必要性审查→申诉控告

LLM 根据 `key_dates` 填充具体日期。无 key_dates 时用阶段描述替代日期。

---

## 9. L3 工具层规范

### 9.1 O3 潜台词决策树

**MS-3 潜台词决策树**（flowchart TD）为 L3 核心——通话中快速查询工具。

结构：
```
根节点[对方说："案件还在侦查中"] → 分支{含义判断}
  → 70% [即将提请批捕] → [应对：立即准备取保材料]
  → 20% [搪塞推脱] → [应对：追问具体进展]
  → 10% [案件停滞] → [应对：了解停滞原因]
```

决策树下方折叠完整表格（旧方案 5 列格式保留在 details 内）。

**约束**：每类沟通对象至少 5 条解读；根节点必须是对方原话；概率标注必填；应对必须是可执行动作。

### 9.2 O4 力度光谱条

**纯 CSS 实现**（不依赖 Mermaid）：

```
┌──────────────────────────────────────────────────────┐
│  温和 ◀━━━━━━━━━━━━━━━━━▲━━━━━━━━━━━━━━━━━▶ 强硬      │
│  (合作性)            ↑推荐位置          (施压式)        │
│  ┌────────┐   ┌────────┐    ┌────────┐               │
│  │温和适用  │   │坚定适用  │    │强硬适用  │               │
│  │场景     │   │场景     │    │场景     │               │
│  └────────┘   └────────┘    └────────┘               │
└──────────────────────────────────────────────────────┘
```

- 光谱条：`background: linear-gradient(to right, #0A6E42, #005F73 50%, #C53030)`
- 推荐位置标记：三角指示器（`▲`），`position: absolute; left: NN%`
- LLM 通过 CSS 变量 `--force-position` 填入百分比（温和=15% / 坚定=50% / 强硬=85%）
- 下方 3 个场景适用卡片保持旧方案三档卡片样式

### 9.3 C1 特殊场景应对

**旧方案**：4 个折叠卡片（步骤编号列表）
**新方案**：**场景流程图**（流程图 + 折叠详情）

每个命中场景生成一张迷你 `flowchart TD`：
- 6+场景中取前 2 个生成 MS-6a/MS-6b 流程图
- 流程图结构：触发条件 → 第一步 → 第二步 → 分支{成功/失败} → 后续
- 流程图下方折叠完整的步骤话术详情

---

## 10. CSS 专用组件规范

### 10.1 进度环 (conic-gradient)

```css
.progress-ring {
  width: 60px; height: 60px;
  border-radius: 50%;
  background: conic-gradient(
    var(--ring-color) calc(var(--progress-percent, 0) * 3.6deg),
    #E2E8F0 calc(var(--progress-percent, 0) * 3.6deg)
  );
  /* 中心白色圆形成环形 */
  mask: radial-gradient(transparent 58%, #000 60%);
}
```

### 10.2 风险热力图 CSS Grid

```css
.heatmap-grid {
  display: grid;
  grid-template-columns: auto repeat(6, 1fr);
  gap: 2px;
  font-size: 9pt;
}
.heat-cell {
  padding: 6px 4px;
  text-align: center;
  border-radius: 2px;
}
.heat-l0 { background: #EDF7F0; color: #0A6E42; }
.heat-l1 { background: #FFFBEB; color: #D97706; }
.heat-l2 { background: #FFF8EE; color: #EE9B00; }
.heat-l3 { background: #FFF5F5; color: #C53030; }
.heat-l4 { background: #C53030; color: #fff; }
```

### 10.3 力度光谱条

```css
.force-spectrum {
  position: relative;
  height: 24px;
  border-radius: 12px;
  background: linear-gradient(to right, #0A6E42, #005F73 50%, #C53030);
  margin: 16px 0 8px 0;
}
.force-marker {
  position: absolute;
  top: -6px;
  left: var(--force-position, 50%);
  transform: translateX(-50%);
  color: var(--text-dark);
  font-size: 16px;
  line-height: 1;
}
.force-marker::after {
  content: '推荐';
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 8pt;
  font-weight: bold;
  color: var(--danger-red);
  white-space: nowrap;
}
```

### 10.4 保密水印 (@media print)

```css
@media print {
  body::after {
    content: '仅供授权人员查阅 | 案件编号：' attr(data-case-id);
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-30deg);
    font-size: 48pt;
    color: rgba(0,0,0,0.04);
    white-space: nowrap;
    z-index: 9999;
    pointer-events: none;
    font-family: '微软雅黑', sans-serif;
  }
}
```

### 10.5 Mermaid 图表容器

```css
.mermaid-container {
  margin: 1em 0;
  padding: 0.8em;
  background: #fff;
  border: 1px solid var(--border-gray);
  border-radius: 6px;
  overflow-x: auto;
}
.mermaid-fallback {
  display: none;
  padding: 1em;
  color: var(--neutral-gray);
  font-style: italic;
  border: 1px dashed var(--border-gray);
  border-radius: 4px;
}
/* CDN 加载失败时 JS 切换显示 */
```

---

## 11. 占位符清单

### 11.1 CONTENT_SLOT（HTML 内容填充，共 22 个）

| 序号 | 占位符 | 填充内容 | 说明 |
|------|--------|---------|------|
| SLOT-0 | `PAGE_TITLE` | "刑事辩护沟通指引" | 页面标题 h1 |
| SLOT-1 | `SUBTITLE` | "[沟通对象] · [诉讼阶段] · [沟通目标]" | 副标题 |
| SLOT-1' | `PAGE_META` | "涉嫌罪名：XXX | 生成时间" | 元信息行 |
| SLOT-2 | `O1_PREPARATION` | O1 折叠详情 HTML | §8.1 |
| SLOT-3 | `O2_REDLINES` | O2 折叠清单表格 HTML | §8.2 |
| SLOT-4 | `O3_SUBTEXT` | O3 折叠潜台词表格（5列含置信度） | §9.1 |
| SLOT-5 | `O4_FORCE` | O4 三档力度场景卡片 HTML | §9.2 |
| SLOT-6 | `O5_TIMELINE` | O5 折叠时间节点汇总 HTML | §8.5 |
| SLOT-7 | `C1_SCENARIO` | C1 折叠步骤话术 HTML（条件） | §9.3，无场景填 `<!-- 无特殊场景 -->` |
| SLOT-8 | `O7_RECORD` | O7 沟通记录表单 HTML | 旧 §5.7 |
| SLOT-9 | `DISCLAIMER_LEVEL` | L1 / L2 | 免责声明分级 |
| SLOT-10 | `CASE_ID` | 案件编号 | body `data-case-id` 属性值，格式 `GD-YYYY-NNNN` |
| SLOT-11 | `HEATMAP_ROW_POLICE` | 公安行 6 个 `<div class="heat-cell heat-lX">` | §7.3 |
| SLOT-12 | `HEATMAP_ROW_PROCURATOR` | 检察院行 6 个 heat-cell | §7.3 |
| SLOT-13 | `HEATMAP_ROW_COURT` | 法院行 6 个 heat-cell | §7.3 |
| SLOT-14 | `ACTION_CARDS` | 3 张行动卡片 HTML | §7.4 |
| SLOT-15 | `PROGRESS_MATERIAL` | 必备材料完成度 % | 0-100 |
| SLOT-16 | `PROGRESS_LAW` | 法条检索完成度 % | 0-100 |
| SLOT-17 | `PROGRESS_PREDICT` | 关注点预判完成度 % | 0-100 |
| SLOT-18 | `PROGRESS_WORST` | 最坏预案完成度 % | 0-100 |
| SLOT-19 | `FORCE_POSITION` | 力度光谱推荐位置 % | 温和=15 / 坚定=50 / 强硬=85 |
| 工具栏 | `GENERATED_AT` | YYYY-MM-DD HH:mm:ss | 生成时间戳 |

### 11.2 MERMAID_SLOT（Mermaid 源码填充）

| 序号 | 占位符 | 类型 | 位置 | 说明 |
|------|--------|------|------|------|
| MS-1 | `MS-1_STRATEGY` | `flowchart TD` | L1 仪表盘 | 通信策略总图 |
| MS-2 | `MS-2_REDLINE` | `flowchart LR` | O2 | 红线-替代决策树 |
| MS-3 | `MS-3_SUBTEXT` | `flowchart TD` | O3 | 潜台词决策树 |
| MS-5 | `MS-5_GANTT` | `gantt` | O5 | 甘特图时间窗 |
| MS-6a | `MS-6a_SCENARIO` | `flowchart TD` | C1 | 场景流程图-主要 |
| MS-6b | `MS-6b_SCENARIO` | `flowchart TD` | C1 | 场景流程图-次要 |

### 11.3 MERMAID_FALLBACK（CDN 降级纯文本）

| 序号 | 占位符 | 说明 |
|------|--------|------|
| FB-1 | `MS-1_FALLBACK` | MS-1 的纯文本替代（≤150字） |
| FB-2 | `MS-2_FALLBACK` | MS-2 的纯文本替代 |
| FB-3 | `MS-3_FALLBACK` | MS-3 的纯文本替代 |
| FB-5 | `MS-5_FALLBACK` | MS-5 的纯文本替代 |
| FB-6a | `MS-6a_FALLBACK` | MS-6a 的纯文本替代 |
| FB-6b | `MS-6b_FALLBACK` | MS-6b 的纯文本替代 |

---

## 12. 打印适配参数

```css
@media print {
  .side-nav { display: none !important; }
  .toolbar { display: none !important; }
  .no-print { display: none !important; }

  body {
    font-family: '微软雅黑', '宋体', serif;
    font-size: 11pt;
    line-height: 1.8;
    color: #000;
    margin: 0;
    padding: 0;
  }

  .main-content { margin-left: 16px !important; }

  /* 打印时保留 Mermaid 渲染的 SVG */
  .mermaid svg {
    max-width: 100%;
    height: auto;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  table thead {
    background: #005F73 !important; color: #fff !important;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }

  .redline-card, .redline-safe, .force-card,
  .info-card, .lawyer-checklist, .disclaimer-footer,
  .heat-cell, .dashboard-card {
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }

  /* 打印时强制展开所有折叠区 */
  details { display: block !important; }
  details > div { display: block !important; }

  /* 保密水印 */
  body::after {
    content: '仅供授权人员查阅 | 案件编号：' attr(data-case-id);
    position: fixed;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-30deg);
    font-size: 48pt;
    color: rgba(0,0,0,0.04);
    white-space: nowrap;
    z-index: 9999;
    pointer-events: none;
  }

  .template-version-watermark { opacity: 0.4; }

  @page {
    @top-center {
      content: "刑事辩护沟通指引 | 内部参考";
      font-size: 9px; color: #999;
    }
  }
}
```

---

## 13. 降级输出规则

### 13.1 SOFT_DEGRADED（信息不足）

输出 C+D+G 最小骨架，HTML 结构不变，内容精简：
- **[C]** 待补充事实清单 → 替代 L1 仪表盘全部图表
- **[D]** 治理与禁区声明 → 替代 O2 红线
- **[G]** 可执行下一步 → 底部补充信息提示

降级时不生成 Mermaid 图表（MERMAID_SLOT 填入 `<!-- DEGRADED -->`）。

### 13.2 S1 降级（最强约束）

触发：`communication_target` 和 `case_stage` 均无法识别。  
输出：不生成 HTML，仅输出纯文本错误提示。

### 13.3 S2 降级（中度）

触发：推荐字段缺失过半。  
输出：HTML 完整生成，但 O3 潜台词和 O4 力度标注 `[推断]`，使用琥珀色边框。Mermaid 图表正常生成但节点标注 `[推断]`。

### 13.4 Mermaid CDN 降级

CDN 加载失败时，JS 自动将 `.mermaid-container` 内的 `svg` 替换为 `.mermaid-fallback` 纯文本。打印前确保图表已渲染完毕。

---

*v2.2.0 三层架构+Mermaid图表引擎 | 本文件遵循 compiler/ssot.md §17（SSOT）*
