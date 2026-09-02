# 输入字段定义

> 版本：2.0.0 | 配套技能：export-control-compliance-system-gen

---

## 1. 必填字段

### 1.1 company_type（企业类型）

| 属性 | 值 |
|------|-----|
| 类型 | string |
| 必填 | 是 |
| 可选值 | manufacturer / trader / tech_service / software / research_institute / mixed |
| 说明 | 企业类型决定合规制度适用法规范围和重点——生产企业关注ECCN分类+技术参数管控；贸易商关注交易筛选+最终用途核查；软件公司关注视同出口+技术出口管控 |

**输入规则**：
- 生产企业(manufacturer)：关注ECCN分类、许可证申请、技术参数管控
- 贸易商(trader)：关注交易筛选、最终用途核查、制裁清单筛查
- 技术服务(tech_service)：关注视同出口管控、技术出口管控
- 软件公司(software)：关注视同出口、开源软件管控
- 研究机构(research_institute)：关注基础研究豁免、技术出口管控
- 混合型(mixed)：多种类型特征叠加

### 1.2 product_lines（主要产品线描述）

| 属性 | 值 |
|------|-----|
| 类型 | text |
| 必填 | 是 |
| 长度限制 | ≤3000字符 |
| 说明 | 产品线描述决定ECCN分类覆盖范围——建议包含产品名称、功能描述、关键技术参数、已知ECCN编码 |

**输入规则**：
- 每条产品线应包含：产品名称 + 功能描述 + 关键技术参数（如精度/频率/速度/材料）
- 如已知ECCN编码，一并提供（来自#46技能的输出）
- 多产品线时按受控等级从高到低排列

### 1.3 export_destinations（出口目的地清单）

| 属性 | 值 |
|------|-----|
| 类型 | string[] |
| 必填 | 是 |
| 格式 | 国家/地区代码或名称列表 |
| 说明 | 出口目的地决定Country Group管控要求——15 CFR §738 Supplement No.1商业国家列表 |

**输入规则**：
- 使用国家代码（如US/JP/KR/NL/IL）或国家名称
- 如涉及再出口/转运，需标注中间国家
- 注意：目的地 Country Group（E:1/E:2/D:1/D:2/D:3等）决定许可证要求和例外适用性

---

## 2. 选填字段

### 2.1 existing_eccn_results（已有ECCN分类结果）

| 属性 | 值 |
|------|-----|
| 类型 | text |
| 必填 | 否 |
| 来源 | export-control-item-classification(#46)技能输出 |
| 说明 | 已有ECCN分类结果——本技能将引用而非重复分类，在SOP中标注"参照已有ECCN分类结果" |

### 2.2 sanctions_screening_setup（已有制裁筛查方案）

| 属性 | 值 |
|------|-----|
| 类型 | text |
| 必填 | 否 |
| 来源 | sanctions-list-batch-screening(#47)技能输出 |
| 说明 | 已有制裁筛查方案——本技能在SOP中引用筛查流程而非重新设计 |

### 2.3 company_size（企业规模）

| 属性 | 值 |
|------|-----|
| 类型 | string |
| 必填 | 否 |
| 可选值 | large / medium / small |
| 影响 | 合规组织架构复杂度和SOP分工细化程度 |

### 2.4 industry_sector（行业领域）

| 属性 | 值 |
|------|-----|
| 类型 | string |
| 必填 | 否 |
| 可选值 | semiconductor / telecom / aerospace / chemical / software / financial / energy / other |
| 影响 | ECCN管控重点（如半导体→0-3类/通信→5类/航空航天→0-9类） |

### 2.5 current_compliance_status（当前合规现状）

| 属性 | 值 |
|------|-----|
| 类型 | string |
| 必填 | 否 |
| 可选值 | none / partial / needs_update |
| 影响 | 生成策略——全新生成 vs 补充完善 vs 更新替换 |

### 2.6 specific_concerns（特别关注事项）

| 属性 | 值 |
|------|-----|
| 类型 | text |
| 必填 | 否 |
| 说明 | 用户特别关注的合规风险点（如近期BIS执法趋势/特定产品管控变化/已知红旗场景） |

---

## 3. 输入模式

### Mode A：完整输入

用户提供全部必填+选填字段，直接进入合规制度生成。

### Mode B：最小输入

用户仅提供 company_type + product_lines + export_destinations，其余字段由技能根据企业画像自动推断。

### Mode C：自然语言输入

用户用自然语言描述需求（如"我们是做芯片的公司，出口到日本和韩国，需要一套出口管制合规制度"），自动提取参数。

---

## 4. 输入验证规则

| 规则ID | 检查项 | 失败动作 |
|--------|--------|---------|
| V1 | company_type 非空且为合法枚举值 | 🔴阻断 |
| V2 | product_lines 非空 | 🔴阻断 |
| V3 | export_destinations 非空且≥1个目的地 | 🔴阻断 |
| V4 | export_destinations中的国家代码可映射到Country Group | 🟡确认（无法映射时标注"需手动确认管控组别"） |
| V5 | existing_eccn_results与product_lines内容一致性 | 🟢提示（不一致时不影响生成，仅标注） |