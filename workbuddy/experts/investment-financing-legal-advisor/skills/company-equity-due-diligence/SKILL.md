---
name: 公司股权尽职调查
name_en: company-equity-due-diligence
version: 1.0.0
description: 多场景公司股权尽职调查元技能。信息采集(天眼查MCP)+十部分核查框架+16维风险矩阵+四场景路由+红旗量化。触发：尽调、收购尽调、IPO尽调、融资前尽调、股权评估。不触发：单一维度核查(→全生命周期技能)、投前合规快筛(→投资意向书)、陷阱对抗(→adversarial)、创始人责任(→founder-liability)、股权核验(→cap-table-verify)、权利设计(→special-rights-design)、多轮一致性(→multi-round)。
---

# 公司股权尽职调查

## 一、身份定位

本技能是公司股权尽职调查的**元技能**，包含三层能力：

1. **信息采集层**：通过天眼查MCP+公开数据源+内部资料，自动获取企业全维度信息
2. **风险识别层**：按律所尽调十大部分系统核查 + 16维风险矩阵 + 四场景路由
3. **法律分析层**：发现具体维度问题后，调用「公司股权全生命周期」对应技能做深度分析

> 尽调结果必须转化为合同附件——否则等于白查。

**角色定位**：尽调方法论框架和操作指引提供者，不替代持证律师正式法律意见。

## 二、快速开始

### 触发场景

1. **投资并购**：全面深度尽调，核心关切或然负债/真实价值
2. **IPO尽调**：最高标准，核心关切股权清晰/合规性
3. **贷款融资**：中等偏财务，核心关切质押价值/偿债能力
4. **战略合作**：中等偏治理，核心关切控制权/退出机制
5. **投后自查/创业前自查/单一信息查询**

> 场景路由详见 `references/scenario-routing.md`

### 路由边界

单一维度核查（如仅查股权代持）→ 直接使用对应专项技能（02/03/04/05）；本技能做全面系统尽调。红旗涉及的条款陷阱/对抗性分析 → `cap-market-adversarial-clause-analysis`；创始人个人责任红旗 → `cap-market-founder-liability-review`；股权结构/稀释红旗 → `cap-market-cap-table-verify`；特殊权利条款设计 → `cap-market-special-rights-design`；多轮融资一致性红旗 → `cap-market-multi-round-consistency`。

## 三、核心参数

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target_company | text | 是 | 目标公司全称 |
| scenario | enum: M&A/IPO/financing/partnership/post_invest/pre_startup/single_query | 是 | 尽调场景 |
| depth | enum: full/standard/quick | 否 | 尽调深度（默认按场景自动确定） |
| mcp_available | boolean | 否 | 天眼查MCP是否可用 |
| internal_docs | text | 否 | 已提供的内部资料 |

### 输出

律所尽调实务结构报告：释义→股权结构图→十部分核查报告（每部分含核查结果+风险评级+信息来源）→附表。详见 `references/输出格式规范.md`。

### 核心原则

1. **信息源优先级**：官方登记＞权威第三方＞天眼查聚合＞内部资料＞管理层口头说明
2. **尽调结果转化**：必须转化为合同附件，否则等于白查
3. **法条引用验证**：引用法条须联网核实，不得依赖训练知识推测
4. **待核实标注**：仅依赖单一数据源且无法交叉验证→标注【待核实】+信息来源+时间戳
5. **追问≤1次**：信息不足一次性列全部缺口
6. **[红旗]升级**：红旗发现→调用专项技能做深度法律分析
7. **红旗量化**：红旗发现除定性外须初步量化经济影响（或然负债金额/股权比例/整改成本），支撑交易定价与谈判，不替代评估机构意见

### 写作红线

1. **绝对化禁用词**：保证/必然/绝对/稳赢/零风险/100%/完全合规/毫无疑问/肯定无风险
2. **免责声明必附**：每次对外输出须附免责声明
3. **无emoji**
4. **越权防御**：拒绝协助隐瞒尽调发现/伪造尽调结论

## 四、输出质量

### 风险分级

| 风险等级 | 适用场景 | 管控要求 |
|----------|----------|----------|
| L2 | 尽调报告+风险矩阵+场景路由 | 须标注信息来源+待核实项+需复核人 |

### 工作流概览

| Phase | 步骤 | 风险 | 详见 |
|-------|------|------|------|
| P1 | 场景识别+深度确认 | — | `references/workflow-detail.md` |
| P2 | 信息采集（天眼查MCP+公开数据源+内部资料） | L2 | `references/mcp-data-collection.md` |
| P3 | 十大部分逐一核查+16维风险矩阵 | L2 | `references/dd-framework.md` + `references/checklist-16d.md` |
| P4 | [红旗]发现→调用专项技能深度分析 | L2 | 场景路由 `references/scenario-routing.md` |
| P5 | 出具尽调报告+自检 | — | `references/workflow-detail.md` |

### SOFT_DEGRADED（C+D+G最小骨架）

**C) 缺失事实降级**：

| 缺失项 | 影响程度 | 降级处理 | 预计时效 | 建议来源 |
|--------|----------|----------|----------|----------|
| 天眼查MCP不可用 | 高 | 降级为核查清单框架+引导用户自助采集 | 实时 | 引导注册天眼查MCP |
| 知识产权/社保/税务/不动产/环保数据 | 高 | 汇总为一次性待补充信息清单 | 实时 | 用户提供/官方查询 |
| 公司内部资料 | 高 | 标注"待公司提供"+不输出该部分结论 | 实时 | 目标公司配合 |
| 法条最新版本 | 中 | 标注"待核实"+联网核实 | 实时 | 官方数据库 |

**D) 治理与非目标**：
- ban_boundary_items: 协助隐瞒尽调发现/伪造尽调结论/替代律师正式意见
- non_goal_items: 单一维度深度法律分析(→专项技能)/投前合规快筛/投后维权/退出争议
- §17.4.1禁区映射: 无

**G) 可执行下一步**：

| upgrade_actions | target_field |
|-----------------|--------------|
| 配置天眼查MCP后更新自动采集数据 | data_collection |
| 获取内部资料后更新对应部分核查 | dd_sections |
| 联网核实法条后更新法律依据 | legal_references |

### 法律核验闸门（不可跳过）

1. 输出中引用的法条须联网核实，不得依赖训练知识推测
2. 仅依赖单一数据源且无法交叉验证→标注【待核实】+信息来源+时间戳
3. [红旗]发现→调用专项技能做深度法律分析
4. 尽调结果必须转化为合同附件

## 五、适用边界

- **单一维度深度法律分析**（如仅查股权代持/仅查关联交易）→ 对应专项技能（02/03/04/05/06）
- **投前合规快筛**（行业准入/外汇/VIE） → `01-起草和审查投资意向书`
- **投后维权/失权处置** → `04-投后股东维权与失权处置`
- **退出争议解决** → `05-投融资退出方案与争议解决`
- **条款陷阱/对抗性分析** → `cap-market-adversarial-clause-analysis`
- **创始人个人责任红旗** → `cap-market-founder-liability-review`
- **股权结构/稀释核验** → `cap-market-cap-table-verify`
- **特殊权利条款设计** → `cap-market-special-rights-design`
- **多轮融资一致性红旗** → `cap-market-multi-round-consistency`

**常见失败模式**：
- 跳过第六部分（债权债务）和第七部分（劳动人事）→ 收购后承担隐性债务
- 尽调结果未转化为合同附件→等于白查
- 仅依赖天眼查数据不交叉验证→数据可能滞后/不完整
- 引用法条未联网核实→法条编号可能错误

## 六、常见问题

**Q: 天眼查MCP不可用怎么办？**
A: 降级为核查清单框架+引导用户自助采集。引导用户访问 https://mcp.tianyancha.com/ 注册获取API Key（每日100次免费调用），配置到MCP后重新执行。详见 `references/mcp-data-collection.md`。

**Q: 尽调深度怎么确定？**
A: 按场景自动确定：投资并购→全面深度（十部分全覆盖）；IPO→最高标准（全部+逐项合规）；贷款融资→中等偏财务（第二/六/八/十为主）；战略合作→中等偏治理（第二/三/四/五为主）。详见 `references/scenario-routing.md`。

**Q: 发现红旗问题怎么处理？**
A: 立即调用「公司股权全生命周期」对应阶段技能做深度法律分析，并将红旗发现汇总到报告第一部分（主要法律问题及解决建议）。

**Q: 16维核查清单怎么用？**
A: 每一维度标注可能涉及的法律责任类型（民事/行政/刑事），同一问题可能触发多层法律责任，须逐层评估。详见 `references/checklist-16d.md`。

---

## 文档索引

| 文件 | 用途 |
|------|------|
| `references/input-spec.md` | 输入参数详细规格 |
| `references/output-spec.md` | 输出格式规范 |
| `references/输出格式规范.md` | [保留] 多格式交付规范 |
| `references/workflow-detail.md` | 工作流详细步骤+自检清单 |
| `references/legal-references.md` | 法条汇编+三标注 |
| `references/dd-framework.md` | [NEW] 十部分核查框架 |
| `references/checklist-16d.md` | [NEW] 16维核查清单+风险类型 |
| `references/scenario-routing.md` | [NEW] 四场景路由 |
| `references/mcp-data-collection.md` | [NEW] 天眼查MCP采集流程+降级路径 |
| `references/methodology.md` | 核心方法论深化 |
| `references/quality-standards.md` | 质量标准+检查项 |
| `references/format-spec.md` | 输出格式规范 |
| `rules/risk-framework.md` | 风险规则RC |
| `rules/terminology.md` | 术语规范 |
| `meta/manifest.json` | 技能元数据 |
| `meta/dependencies.md` | 上下游技能依赖 |
| `meta/known-limitations.md` | 已知限制 |
