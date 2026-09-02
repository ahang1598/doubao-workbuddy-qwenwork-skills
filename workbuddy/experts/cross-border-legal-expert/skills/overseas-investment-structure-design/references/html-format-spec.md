# HTML 排版规范 — 企业出海投资架构设计

> 版本：v1.2.0 | 格式严肃度：C-Professional | 样式策略：纯内联+Richee 组件
> 遵循 base/rule/format-html/format/html-spec.md §1.3 范式唯一性条款

---

## 一、样式策略声明

| 项目 | 值 | 依据 |
|------|-----|------|
| 格式严肃度 | C-Professional | 客户/律师交付级专业报告 |
| 样式策略 | 纯内联+Richee 组件 | html-spec.md §1.3 范式唯一性条款 |
| 视觉权威 | Richee Design Token | base/rule/format-html/core/design-tokens.md |
| 字体栈 | `'PingFang SC','Inter',-apple-system,sans-serif` | design-tokens.md §6 |
| 主输出格式 | HTML（始终输出） | 浏览器打开即渲染，支持打印/PDF |
| 辅格式 | Markdown | 编辑/审阅用，不含色标仅含文字标注 |

### 禁止范式

| ❌ 禁止 | 原因 |
|---------|------|
| HARD_BLOCK 集中 CSS | 元素与样式分离，破坏自包含性（§1.3） |
| 外部 CSS 文件引用 | 依赖外部资源，复制粘贴丢失排版 |
| 元素级 CSS class 体系 | 同 HARD_BLOCK，元素与样式分离 |
| 自创色值 | 必须取自 Richee Design Token |
| Emoji 风险标记 | C-Professional 禁止 🔴🟡🟢⚠️，须用 HTML 内联色标 |

> **@media print class 白名单**：`<style>` 块内 `@media print` 中允许使用以下 class 选择器控制打印行为（属§1.2例外）：`.side-nav` / `.toolbar` / `.no-print` / `.screen-only` / `.source-section` / `.main-content` / `.page-break-before` / `.mermaid-wrap` / `.print-table` / `.template-version-watermark` / `.page-footer`。这些 class 仅用于 `@media print` 中的 `display:none` / `margin` / `opacity` 控制，不用于元素级样式控制。

---

## 二、页面参数（C-Professional）

| 参数 | 值 | 来源 |
|------|-----|------|
| @page margin | 2.5cm 2.6cm 2.0cm 2.8cm | html-spec.md §2.2 |
| body font-family | `'PingFang SC','Inter',-apple-system,sans-serif` | design-tokens.md §6 |
| body font-size | 12pt | html-spec.md §2.2 |
| body line-height | 1.8 | html-spec.md §2.2 |
| article max-width | 156mm | html-spec.md §2.2 |
| 页眉 | 企业出海投资架构设计报告 | html-spec.md §2.2 |

---

## 三、Richee 组件引用清单

```yaml
richee_components: [c01, c05, c06, c09, c20]
```

| 组件 | 名称 | 用途 | 使用位置 |
|------|------|------|----------|
| c01 | 基础表格 | 控股地比选矩阵/税负测算/合规清单/实体说明表 | O2 / O3 / O4 / O5 / O6 |
| c05 | 风险清单表 | 合规风险标注/风险提示 | O6 / O7 |
| c06 | 结论卡 | 执行摘要核心结论/下一步建议 | O1 / O7 |
| c09 | 时间轴 | 设立路径阶段推进 | O4 |
| c20 | 一页结论 | 执行摘要概览（首页） | O1 |

> 组件模板详见 base/rule/format-html/components/ 对应 .md 文件

---

## 四、色值速查（Richee Design Token）

| 用途 | 色值 | 来源 Token |
|------|------|-----------|
| 标题/正文文字 | `#0a0d12` | `--text` |
| 注释/次要文字 | `#6b7280` | `--muted` |
| 分隔线/边框 | `#e2e5ea` | `--line` |
| 页面背景 | `#f6f7f9` | `--bg` |
| 卡片/表格背景 | `#ffffff` | `--white` |
| 高风险/红 | 文字 `#d92d20` / 浅底 `#fef3f2` | `--red` / `--redbg` |
| 中风险/琥珀 | 文字 `#b54708` / 浅底 `#fffaeb` | `--amber` / `--amberbg` |
| 低风险/绿 | 文字 `#039855` / 浅底 `#ecfdf3` | `--green` / `--greenbg` |
| 信息/蓝 | 文字 `#175cd3` / 浅底 `#eff8ff` | `--info` / `--infobg` |
| 表头深色 | `#0a0d12`（背景）/ `#ffffff`（文字） | `--text` / `--white` |

### emoji → HTML内联色标映射（风险等级标注）

| 原 emoji | 含义 | HTML内联色标 | 用法示例 |
|----------|------|-------------|---------|
| 🔴 | 需当地确认/高风险 | `<span style="color:#d92d20;">●</span>` | 法条不确定/税率待确认 |
| 🟡 | 参考来源/中风险 | `<span style="color:#b54708;">●</span>` | 二次来源/需复核 |
| 🟢 | 已核实/低风险 | `<span style="color:#039855;">●</span>` | 法条原文/官方确认 |
| ⚠️ | 警告提示 | `<span style="color:#b54708;">⚠</span>` | 时效性/汇率波动警告 |

### 风险等级标签色映射（HTML内联 badge）

| 风险等级 | 标签样式 | 适用场景 |
|---------|---------|---------|
| 高（L3/🔴） | `background:#fef3f2;color:#d92d20;` | 阻断级合规事项 |
| 中（L2/🟡） | `background:#fffaeb;color:#b54708;` | 需关注的事项 |
| 低（L1/🟢） | `background:#ecfdf3;color:#039855;` | 标准合规事项 |

---

## 五、占位符清单

HTML 模板 (`templates/html-template.html`) 使用 CONTENT_SLOT 占位符路由：

| 占位符 | 说明 | 填充内容 |
|--------|------|----------|
| `<!-- CONTENT_SLOT:PAGE_TITLE -->` | 页面标题 | "企业出海投资架构设计方案" |
| `<!-- CONTENT_SLOT:SUBTITLE -->` | 副标题 | "目标国[XX]投资架构设计报告" |
| `<!-- CONTENT_SLOT:PAGE_META -->` | 元信息 | 目标国+投资目的+投资规模+分析日期+版本 |
| `<!-- CONTENT_SLOT:GENERATED_AT -->` | 生成时间 | YYYY-MM-DD |
| `<!-- CONTENT_SLOT:O1_EXECUTIVE_SUMMARY -->` | O1 执行摘要 | c20 一页结论 + c06 结论卡（关键发现+置信度） |
| `<!-- CONTENT_SLOT:O2_STRUCTURE_DIAGRAM -->` | O2 投资架构图 | Mermaid graph TD + c01 实体说明表 |
| `<!-- CONTENT_SLOT:O3_JURISDICTION_MATRIX -->` | O3 控股地比选矩阵 | c01 基础表格（候选地×6维加权评分） |
| `<!-- CONTENT_SLOT:O4_TIMELINE -->` | O4 设立路径与时间线 | c09 时间轴（阶段推进） + c01 步骤表 |
| `<!-- CONTENT_SLOT:O5_TAX_MATRIX -->` | O5 综合税负测算矩阵 | c01 基础表格（多方案对比+计算路径） |
| `<!-- CONTENT_SLOT:O6_COMPLIANCE_LIST -->` | O6 合规清单 | c05 风险清单表（中国侧/东道国/控股地三侧） |
| `<!-- CONTENT_SLOT:O7_RISK_ADVICE -->` | O7 风险提示与建议 | c05 风险清单表 + c06 结论卡（架构/准入/汇率风险+下一步建议） |
| `<!-- CONTENT_SLOT:DISCLAIMER -->` | 免责声明 | 红色左边框警示样式（固定内容） |

---

## 六、LLM 生成职责

| 职责 | 说明 |
|------|------|
| ✅ 填充 CONTENT_SLOT | 用真实分析内容替换占位符 |
| ✅ 内联样式 | 所有元素使用 `style="..."`，色值取自 Richee Token |
| ✅ Richee 组件 | 复制 components/ 对应组件模板，替换数据 |
| ✅ 风险色标 | 原 emoji（🔴🟡🟢⚠️）全部替换为 HTML 内联色标 |
| ✅ Mermaid 图表 | 架构图使用 Mermaid graph TD 内联渲染 |
| ❌ 修改 `<style>` 块 | `<style>` 仅含 @page/@media print/页码计数器/Mermaid 初始化（§1.2 例外） |
| ❌ 自创 HTML 布局 | 按模板结构填充，不自由发挥 |
| ❌ 在 CONTENT_SLOT 中创建 `<style>` | 禁止元素级 CSS class |
| ❌ 使用 emoji 风险标记 | C-Professional 全面禁止 🔴🟡🟢⚠️ |

---

## 七、打印/PDF 适配

| 规则 | 说明 |
|------|------|
| `@media print` 隐藏 | 侧栏导航/工具栏/版本水印/Richee图例/页脚 |
| `@media print` 展开 | 折叠区（`details`）打印时展开 |
| 打印颜色保留 | `table thead/tr/td` 设置 `print-color-adjust:exact` |
| 页码 | CSS 计数器自动页码，首页无页眉页脚 |
| Mermaid 图表 | 打印时显示降级表格 |

---

## 八、Mermaid 图表集成

投资架构图（O2）使用 Mermaid graph TD 渲染多层 SPV 架构：

```javascript
mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    primaryColor: '#eff8ff',
    primaryTextColor: '#0a0d12',
    primaryBorderColor: '#e2e5ea',
    lineColor: '#6b7280',
    fontSize: '12px'
  }
});
```

**Mermaid 图结构要求**：
- 每层实体节点标注：公司名称+注册地+公司类型+功能
- 箭头标注：资金流向（ODI资金/注册资本/股息汇回/股权转让）
- 三层架构强制：L0 中国母公司 → L1 中间控股SPV → L2 东道国运营实体

**降级机制**：
- Mermaid CDN 加载失败 → 显示 `<noscript>` 提示
- 渲染失败 → 显示降级文本架构说明
- 离线环境 → 提示复制源码到 mermaid.live 在线渲染

---

## 九、质量检查清单

| # | 检查项 | 标准 | 级别 |
|---|--------|------|------|
| 1 | 内联样式铁律 | 所有元素 `style="..."`，无 CSS class 控制样式 | 🔴阻断 |
| 2 | 色值合规 | 色值取自 Richee Design Token | 🔴阻断 |
| 3 | 字体栈合规 | `'PingFang SC','Inter',-apple-system,sans-serif` | ⚠️警告 |
| 4 | 占位符已填充 | 无残留 `CONTENT_SLOT` 占位符 | 🔴阻断 |
| 5 | 免责声明已附 | 固定红色左边框警示样式 | 🔴阻断 |
| 6 | 打印适配 | `@media print` 规则完整 | ⚠️警告 |
| 7 | 侧栏导航 | 七模块+免责声明导航链接 | 💡建议 |
| 8 | Mermaid 降级 | `<noscript>` + 降级表格 | 💡建议 |
| 9 | Emoji 零残留 | 全文无 🔴🟡🟢⚠️ emoji 风险标记 | 🔴阻断 |
| 10 | 风险色标正确 | 所有风险标注使用 HTML 内联色标 | 🔴阻断 |
| 11 | O1 执行摘要 ≤400字 | 首页摘要简洁完整 | ⚠️警告 |
| 12 | O2 架构图含三层+资金流向 | Mermaid 图结构完整 | 🔴阻断 |
| 13 | O5 税负测算含多方案对比 | ≥2方案+计算路径 | 🔴阻断 |

---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
