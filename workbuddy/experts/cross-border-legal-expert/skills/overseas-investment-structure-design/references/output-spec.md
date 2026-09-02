# 输出规范 — overseas-investment-structure-design

> 版本：v1.2.0 | 主格式：HTML | 辅格式：Markdown

## 0. 格式声明

**始终输出 HTML 格式**（C-Professional + 纯内联样式 + Richee 组件），同时提供 Markdown 辅格式（编辑/审阅用，不含色标仅含文字标注）。

HTML 排版遵循 `references/html-format-spec.md`，模板位于 `templates/html-template.html`。

### 双格式差异说明

| 维度 | HTML（主格式） | Markdown（辅格式） |
|------|--------------|------------------|
| 风险标注 | Richee Token 内联色标 | 文字标注（`[高风险]`/`[中风险]`等） |
| 表格 | Richee c01/c05 组件 | 原生 Markdown 表格 |
| 架构图 | Mermaid JS 渲染 | Mermaid 代码块 |
| 时间轴 | Richee c09 组件 | 步骤表格 |
| 结论卡 | Richee c06/c20 组件 | 加粗引文块 |
| 交付级 | 浏览器打开即渲染 + 打印/PDF | 纯文本审阅用 |

---

## 1. HTML报告标准结构

```html
<!-- CONTENT_SLOT:PAGE_TITLE -->        <!-- 页面标题："企业出海投资架构设计方案" -->
<!-- CONTENT_SLOT:SUBTITLE -->          <!-- 副标题："目标国[XX]投资架构设计报告" -->
<!-- CONTENT_SLOT:PAGE_META -->         <!-- 元信息行 -->
<!-- CONTENT_SLOT:GENERATED_AT -->      <!-- 生成时间 -->

<!-- CONTENT_SLOT:O1_EXECUTIVE_SUMMARY -->   <!-- O1 执行摘要（c20一页结论+c06结论卡） -->
<!-- CONTENT_SLOT:O2_STRUCTURE_DIAGRAM -->   <!-- O2 投资架构图（Mermaid+实体说明表） -->
<!-- CONTENT_SLOT:O3_JURISDICTION_MATRIX --> <!-- O3 控股地比选矩阵（c01基础表格） -->
<!-- CONTENT_SLOT:O4_TIMELINE -->            <!-- O4 设立路径与时间线（c09时间轴+c01步骤表） -->
<!-- CONTENT_SLOT:O5_TAX_MATRIX -->          <!-- O5 综合税负测算矩阵（c01基础表格） -->
<!-- CONTENT_SLOT:O6_COMPLIANCE_LIST -->     <!-- O6 合规清单（c05风险清单表） -->
<!-- CONTENT_SLOT:O7_RISK_ADVICE -->         <!-- O7 风险提示与建议（c05风险清单+c06结论卡） -->
<!-- CONTENT_SLOT:DISCLAIMER -->             <!-- 免责声明（固定模板） -->
```

---

## 2. 各输出块详细规格

### 2.1 O1 执行摘要

**HTML组件**：c20 一页结论（概览卡） + c06 结论卡（核心判断分析）  
**字数**：≤400字  

**Richee c20 一页结论结构**：

```html
<div style="background:#ffffff;border:1px solid #e2e5ea;border-radius:12px;padding:20px;">
  <h3 style="font-size:20px;font-weight:600;color:#0a0d12;margin:0 0 14px 0;">
    [投资概况]：[目标国XX] / [投资目的XX] / [投资规模XX]
  </h3>
  <!-- 4个指标卡 -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
    <div style="..."><div style="font-size:12px;color:#6b7280;">推荐架构</div><div style="font-size:20px;font-weight:600;">[三层SPV]</div><div style="font-size:12px;color:#6b7280;">[控股地]</div></div>
    <div style="..."><div style="font-size:12px;color:#6b7280;">设立周期</div><div style="font-size:20px;font-weight:600;">[约N个月]</div><div style="font-size:12px;color:#6b7280;">全部环节</div></div>
    <div style="..."><div style="font-size:12px;color:#6b7280;">综合有效税率</div><div style="font-size:20px;font-weight:600;">[XX%]</div><div style="font-size:12px;color:#6b7280;">[方案名称]</div></div>
    <div style="..."><div style="font-size:12px;color:#6b7280;">置信度</div><div style="font-size:20px;font-weight:600;">[高/中/低]</div><div style="font-size:12px;color:#6b7280;">[数据来源说明]</div></div>
  </div>
</div>
```

**Richee c06 结论卡——关键发现**：

```html
<div style="border:1px solid #e2e5ea;background:linear-gradient(90deg,rgba(50,213,131,0.10),rgba(255,255,255,0.98));border-radius:12px;padding:18px 20px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <strong style="font-size:16px;font-weight:600;color:#0a0d12;">关键发现</strong>
    <span style="padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:[按置信度选取色];color:[按置信度选取色];">置信度：[高/中/低]</span>
  </div>
  <ol style="font-size:14px;line-height:1.85;color:#0a0d12;padding-left:20px;margin:0;">
    <li><span style="color:#039855;">●</span> [发现1]（[投资概况/架构/税负/合规]）</li>
    <li><span style="color:#b54708;">●</span> [发现2]</li>
    <li><span style="color:#d92d20;">●</span> [发现3]</li>
  </ol>
  <div style="margin-top:10px;font-size:13px;color:#6b7280;border-top:1px solid #e2e5ea;padding-top:8px;">
    <span style="color:#b54708;">⚠</span> 时效性提示：[如有中/高风险数据，列出可能变化的法规/税率]
  </div>
</div>
```

---

### 2.2 O2 投资架构图

**HTML组件**：Mermaid graph TD（内联渲染） + Richee c01 实体说明表

**Mermaid 架构图**（在 `class="mermaid-wrap"` 容器中渲染）：

```
graph TD
    A[中国母公司<br/>CN Co., Ltd.<br/>有限责任公司] -->|ODI资金XXX万USD| B[控股地SPV<br/>HK/SG Holding Ltd.<br/>私人有限公司]
    B -->|注册资本| C[东道国运营实体<br/>VN/TH/ID Co., Ltd.<br/>WFOE]
    C -->|股息汇回| B
    B -->|股息汇回| A
```

> **Mermaid 要求**：每节点标注公司名称+注册地+公司类型+功能，箭头标注资金性质与流向，三层结构强制。

**Richee c01 实体说明表**：

| 层级 | 实体名称 | 注册地 | 公司类型 | 功能 | 注册资本 |
|------|---------|--------|---------|------|---------|
| L0 | 中国母公司 | 中国 | 有限责任公司 | 投资主体/最终受益人 | — |
| L1 | [控股地]SPV | [注册地] | [公司类型] | 中间控股/资金通道 | [金额] |
| L2 | [东道国]运营实体 | [注册地] | [公司类型] | [运营功能] | [金额] |

---

### 2.3 O3 控股地比选矩阵

**HTML组件**：Richee c01 基础表格（深色表头）

```
列：控股地 | 税负优化(30%) | 协定网络(20%) | 设立成本(15%) | 维护成本(15%) | 退出便利(10%) | 合规难度(10%) | 加权总分
行：≥3候选地（展示国旗emoji标志）
推荐结论：在表格下方以c06结论卡形式输出推荐理由
```

**权重说明**：默认权重基于 `investment_purpose=manufacturing`；其他目的（sales_office/R&D/regional_holding/holding）调整权重配比并在评分方法中说明。

---

### 2.4 O4 设立路径与时间线

**HTML组件**：Richee c09 时间轴（阶段推进） + c01 步骤表

**c09 时间轴**（阶段级）：

```
Phase 1：中国侧ODI审批（发改委+商务部+外汇局）→ T+0~T+1月
Phase 2：控股地SPV设立+开户 → T+1~T+2月
Phase 3：东道国投资许可/企业注册 → T+2~T+4月
Phase 4：资金注入+验资 → T+4~T+5月
```

**c01 步骤表**（步骤级）：

| 步骤 | 事项 | 主管机关 | 预计耗时 | 前置条件 | 风险等级 |
|------|------|---------|---------|---------|---------|
| [序号] | [事项描述] | [机关名称] | [耗时] | [前置条件] | [HTML内联色标标签] |

> 风险等级标签使用 HTML 内联 badge：高=`#fef3f2`+`#d92d20` / 中=`#fffaeb`+`#b54708` / 低=`#ecfdf3`+`#039855`

---

### 2.5 O5 综合税负测算矩阵

**HTML组件**：Richee c01 基础表格（多方案对比 + 利润汇回路径 + 退出税负）

**架构方案对比表**：

| 税负项 | 方案A: 直投[目标国] | 方案B: [控股地]→[目标国]（推荐） | 方案C: [备选地]→[目标国] |
|--------|-------------------|------------------------------|-------------------------|
| 东道国企业所得税 | [税率%] | [税率%]（[优惠说明]） | [税率%] |
| 股息预提税（东道国→控股地） | [税率%]（<span style="color:#b54708;">⚠</span>[国内法说明]） | [税率%]（[协定依据]） | [税率%] |
| 控股地企业所得税 | — | [税率%] | [税率%] |
| 股息预提税（控股地→中国） | — | [协定税率%]（[协定条款]） | [协定税率%] |
| **综合有效税率** | **[XX%]** | **[XX%]** | **[XX%]** |
| 资本利得税（退出时） | [税率%] | [税率%]（[路径]） | [税率%] |

> ⚠ 关键规则：股息预提税须优先查证东道国国内法实际征收税率，协定税率仅为上限参考。例：越南国内法对外国法人股东股息预提=0%，中越协定10%/港越协定5%仅为上限。
> 每项税率后须标注置信度：<span style="color:#039855;">●</span>已核实 / <span style="color:#b54708;">●</span>参考来源 / <span style="color:#d92d20;">●</span>需当地确认

**利润汇回路径税负表**（推荐方案）：

| 路径 | 税负 | 依据 | 置信度 |
|------|------|------|--------|
| 东道国→控股地（股息） | [%]预提 | [国内法/协定条款] | [色标] |
| 控股地→中国（股息） | [%]预提 | [协定名称]第[X]条 | [色标] |
| **综合汇回税负** | **[%]** | [注解] | — |

---

### 2.6 O6 合规清单

**HTML组件**：Richee c05 风险清单表（三侧分表，每侧独立表格）

**中国侧ODI审批**：

| # | 事项 | 法规依据 | 时限 | 风险等级 | 说明 |
|---|------|---------|------|---------|------|
| [序号] | [事项] | [法规名称] | [时限要求] | [HTML内联色标标签] | [补充说明] |

**东道国准入**：

| # | 事项 | 法规依据 | 风险等级 | 说明 |
|---|------|---------|---------|------|
| [序号] | [事项] | [法规名称] | [HTML内联色标标签] | [补充说明] |

**中间控股地合规**：

| # | 事项 | 法规依据 | 风险等级 | 说明 |
|---|------|---------|---------|------|
| [序号] | [事项] | [法规名称] | [HTML内联色标标签] | [补充说明] |

> 风险等级标签：高=阻断级/中=需关注/低=标准合规。区分"投资前必须完成"vs"投资后持续合规"。

---

### 2.7 O7 风险提示与建议

**HTML组件**：Richee c05 风险清单表（架构/准入/汇率三分类） + c06 结论卡（下一步建议）

**架构风险**（c05）：

| 风险项 | 风险后果 | 风险等级 | 缓解措施 |
|--------|---------|---------|---------|
| 经济实质法 | [后果描述] | [标签] | [具体措施] |
| CFC反避税 | [后果描述] | [标签] | [具体措施] |
| CRS信息交换 | [后果描述] | [标签] | [合规说明] |

**准入风险** & **汇率/政治风险** 同上结构。

**下一步建议**（c06 结论卡样式）：

```html
<div style="border:1px solid #e2e5ea;background:linear-gradient(90deg,rgba(23,92,211,0.08),rgba(255,255,255,0.98));border-radius:12px;padding:18px 20px;">
  <strong style="font-size:16px;font-weight:600;color:#0a0d12;display:block;margin-bottom:10px;">下一步建议</strong>
  <ol style="font-size:14px;line-height:1.85;color:#0a0d12;padding-left:20px;margin:0;">
    <li><span style="color:#d92d20;">●</span> [必须委托目标国律师确认……]</li>
    <li><span style="color:#b54708;">●</span> [建议在T+N月前完成……]</li>
    <li><span style="color:#175cd3;">●</span> [建议咨询税务顾问……]</li>
  </ol>
</div>
```

---

## 3. 风险标注规范

### 3.0 双格式标注对照

| 语义 | HTML 主格式 | Markdown 辅格式 |
|------|------------|----------------|
| 已核实（低风险） | `<span style="color:#039855;">●</span>` | `[已核实]` |
| 参考来源（中风险） | `<span style="color:#b54708;">●</span>` | `[参考来源]` |
| 需当地确认（高风险） | `<span style="color:#d92d20;">●</span>` | `[需当地确认]` |
| 警告提示 | `<span style="color:#b54708;">⚠</span>` | `⚠` |
| 阻断 | `<span style="background:#fef3f2;color:#d92d20;">阻断</span>` | `[阻断]` |
| 限制 | `<span style="background:#fffaeb;color:#b54708;">限制</span>` | `[限制]` |
| 允许 | `<span style="background:#ecfdf3;color:#039855;">允许</span>` | `[允许]` |
| 高风险（L3） | `<span style="background:#fef3f2;color:#d92d20;">高</span>` | `[高风险]` |
| 中风险（L2） | `<span style="background:#fffaeb;color:#b54708;">中</span>` | `[中风险]` |
| 低风险（L1） | `<span style="background:#ecfdf3;color:#039855;">低</span>` | `[低风险]` |

**C-Professional 严禁使用 emoji（🔴🟡🟢⚠️），HTML 主格式用 Richee Token 内联色标，Markdown 辅格式用方括号文字标注。**

### 3.1 HTML 主格式 — 行内置信度标记

| 语义 | HTML代码 |
|------|---------|
| 已核实（低风险） | `<span style="color:#039855;">●</span>` |
| 参考来源（中风险） | `<span style="color:#b54708;">●</span>` |
| 需当地确认（高风险） | `<span style="color:#d92d20;">●</span>` |
| 警告提示 | `<span style="color:#b54708;">⚠</span>` |

### 3.2 HTML 主格式 — 表格内风险等级标签

| 风险等级 | HTML badge 模板 |
|---------|----------------|
| 高（L3） | `<span style="display:inline-flex;align-items:center;justify-content:center;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#fef3f2;color:#d92d20;">高</span>` |
| 中（L2） | `<span style="display:inline-flex;align-items:center;justify-content:center;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#fffaeb;color:#b54708;">中</span>` |
| 低（L1） | `<span style="display:inline-flex;align-items:center;justify-content:center;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;background:#ecfdf3;color:#039855;">低</span>` |

### 3.3 Markdown 辅格式 — 文字标注

Markdown 辅格式不含 HTML 色标，使用方括号文字标注：

| 语义 | 文字标注 |
|------|---------|
| 已核实 | `[已核实]` |
| 参考来源 | `[参考来源]` |
| 需当地确认 | `[需当地确认]` |
| 警告提示 | `⚠` |
| 阻断 | `[阻断]` |
| 限制 | `[限制]` |
| 允许 | `[允许]` |
| 高风险（L3） | `[高风险]` |
| 中风险（L2） | `[中风险]` |
| 低风险（L1） | `[低风险]` |

---

## 4. 写作红线

- **WR-01**：税率数据须注明协定条款号+检索日期，禁止编造
- **WR-02**：东道国法规不确定时标注 HTML 色标（`<span style="color:#d92d20;">●</span>`），不编造法条
- **WR-03**：金额须注明币种+汇率日期
- **WR-04**：Mermaid 架构图须标注每个实体的注册地+功能+公司类型
- **WR-05**：税负测算须列明计算路径（非仅给结果）
- **WR-06**：合规清单须区分"投资前必须完成"vs"投资后持续合规"
- **WR-07**：禁止使用任何 emoji 风险标记（🔴🟡🟢⚠️），全部使用 HTML 内联色标（C-Professional 强制要求）
- **WR-08**：HTML 所有元素使用内联 `style="..."`，禁止 CSS class 体系（§1.3 范式唯一性条款）

---

## 5. 质量检查项

- [ ] O1 执行摘要≤400字
- [ ] O2 架构图含全部层级实体+资金流向
- [ ] O3 比选矩阵含≥3个候选+加权评分
- [ ] O4 设立步骤含中国侧+东道国侧全流程
- [ ] O5 税负测算含多方案对比+计算路径
- [ ] O6 合规清单覆盖三侧（中国/东道国/控股地）
- [ ] O7 风险提示含下一步具体建议
- [ ] 风险标注使用 HTML 内联色标（非 emoji）
- [ ] 金额注明币种
- [ ] 免责声明完整
- [ ] 无残留 CONTENT_SLOT 占位符
- [ ] 所有元素使用 `style="..."` 内联样式
- [ ] @media print 规则完整
