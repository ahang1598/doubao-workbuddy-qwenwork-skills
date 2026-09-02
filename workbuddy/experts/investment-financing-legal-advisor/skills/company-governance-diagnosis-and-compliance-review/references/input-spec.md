# 输入规格

## 任务类型（task_type）

| 值 | 子流程 | 说明 |
|----|--------|------|
| `review_resolution` | A | 决议效力审查/章程权力分配审查 |
| `diagnose_veto` | B | 一票否决权诊断 |
| `check_non_competition` | C1 | 同业竞争合规检查 |
| `check_related_party` | C2 | 关联交易合规检查 |

## 通用输入参数（所有任务类型必填）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | enum | 是 | 任务类型（见上表） |
| company_info | object | 是 | 公司基本信息（见下方company_info结构） |
| diagnosis_purpose | enum | 否 | 诊断目的：`pre_investment`(投前尽调)/`post_investment`(投后管理)/`dispute_preparation`(争议准备)/`ipo_coaching`(IPO辅导)。影响输出深度和侧重点 |

### company_info 结构

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 公司全称 |
| company_type | 是 | 公司类型：有限责任公司/股份有限公司（影响决议规则：第66条vs第110条） |
| establish_date | 是 | 公司成立日期（影响新旧法适用判断：2024.7.1前成立适用旧法过渡期规则） |
| equity_structure | 是 | 股权结构（各股东持股比例+出资方式） |
| charter_text | 是 | 公司章程全文或相关条款 |
| registration_date | 否 | 工商登记日期（影响否决权对抗效力：晚于登记的章程修改不得对抗善意第三人） |
| shareholder_info | 否 | 股东构成详情（PE机构持股情况/关联关系/委派董事情况） |
| board_info | 否 | 董事会构成（董事人数/各方委派/独立董事情况） |

## 子流程A专用参数（review_resolution）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| resolution_text | text | 是 | 决议全文文本 |
| resolution_date | date | 是 | 决议作出日期（影响除斥期间/时效计算：不成立1年/可撤销60日） |
| resolution_type | enum | 是 | 决议类型：`shareholders`(股东会决议)/`board`(董事会决议)（适用不同职权规则） |
| convening_info | object | 是 | 召集程序信息：召集人/通知时间/通知方式（影响程序合规判断） |
| attendance_info | object | 是 | 出席情况：出席人数/代表表决权数（影响成立判断：是否达标） |
| voting_info | object | 是 | 表决情况：赞成/反对/弃权票数（影响通过比例判断） |

## 子流程B专用参数（diagnose_veto）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| veto_provisions | object | 是 | 否决权条款内容（见下方veto_provisions结构） |

### veto_provisions 结构

| 字段 | 必填 | 说明 |
|------|------|------|
| provision_text | 是 | 否决权条款全文 |
| source | 是 | 否决权来源：`charter`(章程)/`shareholder_agreement`(股东协议)/`investment_agreement`(投资协议)（效力层级不同：章程>股东协议>投资协议） |
| setup_date | 是 | 设置时间（是否晚于工商登记→影响对抗善意第三人效力） |
| scope | 是 | 否决权适用范围（重大事项清单） |
| subject | 是 | 享有否决权的主体（个别股东/董事） |
| exercise_history | 否 | 历史行使记录（僵局风险评估依据） |

## 子流程C1专用参数（check_non_competition）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| non_competition_info | object | 是 | 同业竞争信息（见下方结构） |

### non_competition_info 结构

| 字段 | 必填 | 说明 |
|------|------|------|
| competitor_identity | 是 | 竞争方身份（股东/董事/高管/PE机构） |
| competing_business | 是 | 竞争业务描述（经营同类业务的具体情况） |
| shareholder_consent | 否 | 是否经股东会/股东大会同意（同意记录/决议编号） |
| position_held | 是 | 竞争方在公司担任的职务（影响"利用职务便利"判断） |
| actual_operation_evidence | 否 | 实际经营证据（营业执照/经营记录/客户重合等） |
| pe_exception_info | 否 | PE机构例外信息（持股比例/控股地位/投资性质/是否委派董事） |

## 子流程C2专用参数（check_related_party）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| related_party_transactions | object | 是 | 关联交易信息（见下方结构） |

### related_party_transactions 结构

| 字段 | 必填 | 说明 |
|------|------|------|
| counterparty | 是 | 交易对方身份 |
| related_relationship | 是 | 关联关系描述（控制关系/重大影响关系） |
| transaction_amount | 是 | 交易金额（影响分层审批判断：小额董事会/大额股东会） |
| pricing_basis | 是 | 定价依据（市场价/评估价/协议价→影响公允性判断） |
| transaction_date | 是 | 交易时间（影响诉讼时效起算） |
| transaction_type | 是 | 交易类型（采购/销售/资金拆借/担保/转让等） |
| internal_approval | 否 | 内部审批情况（是否经董事会/股东会决议/关联方是否回避） |
| disclosure_status | 否 | 信息披露情况（是否向董事会/股东会披露） |

## 追问策略

- 追问≤1次：信息不足时一次性列全部缺口
- 仅在以下情况追问：无任务表达 / 缺关键事实 / 产物互斥
- 诊断目的(diagnosis_purpose)未明确时，根据已有信息推断但不追问
