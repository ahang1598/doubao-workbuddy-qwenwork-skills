# 输入规格 — cross-border-spa-sha-drafting

> 本节遵循 base/governance/ssot-compiler.md §17（SSOT）：input-spec 定义

## 1. 必填参数

| # | 字段名 | 类型 | 法律含义 | 校验规则 |
|---|--------|------|---------|---------|
| 1 | transaction_type | enum | 交易类型决定文件路由（SPA vs SHA）及核心条款结构 | 枚举：股权收购SPA/资产收购SPA/合并/SHA |
| 2 | buyer_info | text | 买方名称、注册地、上市状态（影响审批与披露条款设计） | 非空，≥10字符，含买方名称 |
| 3 | seller_info | text | 卖方名称、注册地、持股架构（影响陈述保证范围与赔偿条款设计） | 非空，≥10字符，含卖方名称 |
| 4 | transaction_amount | text | 交易对价金额及币种（影响定价条款、赔偿上限、托管金额） | 非空，含金额和币种 |
| 5 | negotiation_stance | enum | 谈判立场决定条款保护倾向 | 枚举：buyer_protect/seller_protect/balanced |
| 6 | target_jurisdiction | enum | 目标法域决定适用法律和条款合规要求 | 枚举：CN内地/CN香港/BVI/Cayman/USA/多法域组合 |

## 2. 可选参数

| # | 字段名 | 类型 | 法律含义 | 默认值 |
|---|--------|------|---------|--------|
| 7 | closing_conditions | text | 用户自定义的交割先决条件清单 | 空（使用默认交割条件） |
| 8 | key_risk_areas | text | 特别关注风险领域（增强对应条款深度） | 空 |
| 9 | deal_structure | text | 交易结构细节（支付方式/对价调整/托管安排/Earn-out） | 空 |
| 10 | warranty_categories | text | 陈述保证范围偏好（扩展/标准/缩小） | standard |
| 11 | indemnification_cap | text | 赠偿上限偏好（交易金额百分比/固定金额/无上限） | 空（按谈判立场自动设定） |
| 12 | target_company_info | text | 目标公司详细信息（名称/注册地/主营业务/股权结构） | 空 |
| 13 | existing_agreements | text | 已有相关协议（优先购买权协议/期权协议/现有SHA） | 空 |

## 3. 枚举值定义

### 3.1 transaction_type

| 值 | 文件路由 | 核心条款结构 | 说明 |
|----|---------|------------|------|
| 股权收购SPA | SPA路径 | 12章结构 | 标准股权收购，含定价/陈述保证/赔偿/交割/终止 |
| 资产收购SPA | SPA路径 | 12章结构（资产版） | 资产转让版本，资产清单替代股权描述，含资产权属陈述 |
| 合并 | SPA路径 | 12章结构（合并版） | 合并协议版本，含合并对价/债权人通知/反垄断 |
| SHA | SHA路径 | 10章结构 | 股东协议，含股东权利/董事会/分红/转让限制/退出机制 |

### 3.2 negotiation_stance

| 值 | 条款倾向 | 典型调整 |
|----|---------|---------|
| buyer_protect | 买方保护 | 陈述保证范围扩大+赔偿条款强化卖方责任+交割条件增加+终止权扩大+卖方限制竞争 |
| seller_protect | 卖方保护 | 陈述保证范围缩小+赔偿上限设封顶+交割条件简化+终止权限制+买方付款保障 |
| balanced | 中性平衡 | 兼顾双方利益，关键条款提供双方替代方案供选择 |

### 3.3 target_jurisdiction

| 值 | 适用法律侧重 | 特殊条款需求 |
|----|-----------|------------|
| CN内地 | 中国公司法(2023修订)+民法典合同编+外商投资安全审查办法(2020年第37号令)+经营者集中申报标准(2024修订) | ODI审批(发改委第11号令+商务部第3号令分工)/反垄断申报(2024修订门槛)/外商投资安全审查/数据合规 |
| CN香港 | 香港公司条例(第622章)+合约法 | [需离岸法域律师核实]标注 |
| BVI | BVI Business Companies Act 2004 (2024修正案) | 离岸公司股权转让/BVI董事职责/受益所有权申报VIRRGIN/逾期罚款新规 |
| Cayman | Cayman Islands Companies Act | 开曼公司章程/类别股/合并条款 |
| USA | FIRRMA (2018) + CFIUS 2026执行趋势 | 涉美并购CFIUS审查/NSA条款/TID强制申报/数据可及性审查——标注"[需美国律师核实]" |
| 多法域组合 | 按各层架构分别适用 | 标注每层架构适用法域+逐层条款设计 |

### 3.4 warranty_categories

| 值 | 适用场景 | 条款深度 |
|----|---------|---------|
| expanded | 买方保护或高风险交易 | 扩展陈述保证（+5-10条专项陈述），含知识产权/数据合规/反垄断专项 |
| standard | 一般交易 | 标准陈述保证包（15-20条基本陈述） |
| narrowed | 卖方保护或低风险交易 | 缩小陈述保证（仅核心5-8条基本陈述），排除前瞻性陈述 |

## 4. 输入验证规则

- HR-01：transaction_type 必须在枚举范围内
- HR-02：buyer_info 非空且≥10字符
- HR-03：seller_info 非空且≥10字符
- HR-04：transaction_amount 非空且含金额和币种
- HR-05：negotiation_stance 必须在枚举范围内
- HR-06：target_jurisdiction 必须在枚举范围内

## 5. 宽容摄取规则

当用户提供自然语言描述而非结构化参数时：
- 自动提取 buyer_info/seller_info（从买卖双方描述提取名称和注册地）
- 自动推断 transaction_type（从"股权收购/资产收购/合并/股东协议"关键词推断）
- 默认 negotiation_stance=balanced，如用户明确说"保护买方/卖方"则调整
- 自动推断 target_jurisdiction（从公司注册地或持股架构推断）
- 默认 warranty_categories=standard
- key_risk_areas 从用户描述的风险关注点提取
- deal_structure 从支付方式/托管/Earn-out描述提取