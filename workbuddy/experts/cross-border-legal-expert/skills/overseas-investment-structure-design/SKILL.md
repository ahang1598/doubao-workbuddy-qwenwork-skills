---
name: overseas-investment-structure-design
version: 1.0.0
name_en: overseas-investment-structure-design
description: >
  设计中国企业出海投资的多层控股架构。触发：境外控股架构搭建/ODI资金路径规划/多层SPV方案。不触发：单国公司注册咨询/境内股权架构调整/红筹上市架构——调用对应专项技能。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 企业出海投资架构设计

## 模块一：技能定位与核心原则

**角色定位**：涉外投资法律架构设计助手——基于企业投资目的、规模、目标国，设计境内外多层控股架构并输出可执行的设立路径与合规清单。

**免责声明**：本技能为AI辅助工具，产出内容不构成正式法律意见。东道国法规信息基于公开检索，可能存在滞后或偏差，使用者应结合具体业务需求咨询目标国执业律师及税务顾问。

**适用法域**：中国企业对外投资（ODI）架构设计，覆盖中国侧审批合规 + 东道国准入合规 + 中间控股地选择

**风险等级**：L2（见 `meta/manifest.json`）

**核心原则**：

| # | 原则 | 说明 |
|---|------|------|
| 1 | 多层架构优先 | 默认设计"中国母公司→中间控股SPV→东道国运营实体"三层架构，优化税负与退出便利 |
| 2 | 控股地6维评估 | 税负/协定网络/设立成本/维护成本/退出便利/合规难度六维度加权比选 |
| 3 | ODI法规全覆盖 | 发改委+商务部+外汇局审批路径 + 国务院837号令（安全审查/穿透式审查/居民个人监管），不可遗漏 |
| 4 | 预提税国内法优先 | 综合税负测算须优先查证东道国国内法实际征收税率，协定税率仅为上限参考（如越南国内法0%） |
| 5 | 制裁/安全审查前置 | P0阶段制裁清单核查 + P1阶段安全审查评估（CFIUS/EU FDI/东道国审查），阻断级前置 |
| 6 | 置信度三级标注 | 已核实/参考来源/需当地律师确认（HTML内联色标），不编造法规 |
| 7 | 降级不静默 | 东道国信息不足时触发SOFT_DEGRADED，输出C+D+G最小骨架 |

---

## 模块二：快速开始

**一句话定位**：输入投资目的+目标国+规模，输出多层控股架构图（Mermaid）+ 设立路径 + 综合税负测算 + 各环节合规清单

**最小示例**：

```
用户输入：我们计划在越南设立制造工厂，投资规模约2000万美元，希望优化税负并便于未来退出
预期输出：中国母公司→香港SPV→越南WFOE三层架构图 + 香港设立/越南ODI登记步骤 + 综合税负测算 + 合规清单
```

---

## 模块三：工作流概览

**6 Phase管线**（详见 `references/workflow-detail.md`）：

| Phase | 名称 | 风险 | 产出 |
|-------|------|------|------|
| P0 | 需求确认与约束识别（含制裁核查） | L1 | 需求确认书 + 制裁风险判定 |
| P1 | 东道国准入分析（含安全审查） | L2 | 准入可行性结论 + 安全审查风险等级 |
| P2 | 控股地比选与架构设计 | L2 | 架构方案（含Mermaid图） |
| P3 | 设立路径与税负测算 | L2 | 设立步骤+税负矩阵 |
| P4 | 合规清单生成 | L2 | ODI审批+东道国合规清单 |
| P5 | 报告组装与自检 | L1 | 最终方案报告 |

**关键约束**：
- ODI法规全覆盖（发改委+商务部+外汇局+国务院837号令安全审查/穿透式审查）
- 东道国外商投资准入负面清单
- 中间控股地实质运营要求（经济实质法/BEPS）
- 制裁清单核查（联合国/美国OFAC/欧盟/中国管制名单）
- 安全审查风险评估（CFIUS/EU FDI/东道国安全审查）
- 预提税国内法优先原则（东道国国内法税率优先于协定税率）

**SOFT_DEGRADED**：当东道国法规信息不足时，输出C层（缺失项清单）+D层（限制声明）+G层（建议咨询当地律师），不静默吞错。

---

## 模块四：输入输出概要

**输入**：投资目的+目标国+规模+（可选）控股地候选/退出计划/行业

**核心参数**：

| 参数 | 类型 | 法律含义 | 必填 |
|------|------|---------|------|
| target_country | string | 投资目标国（东道国） | 是 |
| investment_purpose | string | 投资目的（枚举：manufacturing/sales_office/R&D/regional_holding/holding） | 是 |
| investment_amount | string | 投资规模（USD或CNY） | 是 |
| holding_jurisdiction | string[] | 中间控股地候选（默认推荐：HK/SG/BVI/Cayman） | 否 |
| exit_plan | string | 退出计划（枚举：IPO/trade_sale/liquidation/undetermined） | 否 |
| repatriation_plan | string | 利润汇回计划（枚举：dividend/royalty/management_fee/mixed） | 否 |
| industry_sector | string | 行业（影响准入限制+税收优惠） | 否 |
| existing_structure | string | 现有境外架构（如有） | 否 |

**核心法律依据**：见 `references/legal-references.md`

**输出**（O1-O7，主格式HTML，辅格式Markdown，详见 `references/output-spec.md`）：
- O1 执行摘要（≤400字，Richee c20一页结论+c06结论卡）
- O2 投资架构图（Mermaid多层架构图，HTML内联渲染）
- O3 控股地比选矩阵（Richee c01基础表格）
- O4 设立路径与时间线（Richee c09时间轴+c01步骤表）
- O5 综合税负测算矩阵（Richee c01基础表格）
- O6 合规清单（中国侧ODI+东道国准入+中间控股地，Richee c05风险清单表）
- O7 风险提示与建议（Richee c05风险清单+c06结论卡）

**HTML排版规范**：见 `references/html-format-spec.md`（9章节，C-Professional + 纯内联样式铁律 + Richee组件体系）

---

## 模块五：常见问题

**Q1**：与 cross-border-tax-planning 有什么区别？——本技能设计投资控股架构（SPV层级+设立路径+准入合规），后者专注税负优化（协定适用+转让定价+CFC）。本技能输出架构方案，后者输出税务测算。

**Q2**：架构必须三层吗？——默认推荐三层（中国母公司→中间控股SPV→东道国运营实体），但根据投资规模和目标国可简化为两层或扩展为四层。P2阶段会基于6维评估推荐最优层级。

**Q3**：ODI审批需要多久？——发改委备案1-3个月/核准3-6个月，商务部2-3个月，外管局外汇登记1-2周，约3-9个月。实际周期取决于投资规模和行业敏感度。

**Q4**：能否直接用于投资决策？——不能。本技能输出架构设计方案和合规清单，不替代目标国律师和税务顾问的专业意见。东道国准入和税务结论须由当地执业律师/税务顾问确认。

---

## 模块六：文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 输入规范 | `references/input-spec.md` | 参数详细约束 |
| 输出规范 | `references/output-spec.md` | 输出结构与格式 |
| HTML排版规范 | `references/html-format-spec.md` | C-Professional排版+Richee组件体系 |
| HTML模板 | `templates/html-template.html` | 自包含HTML模板（CONTENT_SLOT占位符路由器） |
| 工作流详细 | `references/workflow-detail.md` | 6 Phase执行步骤 |
| 法律依据 | `references/legal-references.md` | 中国侧+东道国侧+双边法规 |
| 方法论 | `references/methodology.md` | 架构设计原理+控股地选择逻辑 |
| 质量标准 | `references/quality-standards.md` | 四维评价体系 |
| 使用说明 | `USAGE.md` | 使用场景与示例 |
| 示例 | `development/examples/example-001.md` | 越南建厂标准示例 |
| 边界示例 | `development/examples/edge-case-001.md` | 严格外汇管制场景 |
