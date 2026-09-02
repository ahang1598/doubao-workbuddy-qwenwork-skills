# 输入规格 — data-export-security-assessment-report

## 1. 输入模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| Mode A | 结构化参数输入 | 企业合规律师，有明确数据出境场景描述 |
| Mode B | 自然语言描述 | 业务人员首次使用，描述模糊 |
| Mode C | 组合输入（结构化+自然语言补充） | 已有#24/#25/#26/#27产出，需要补充出境专项信息 |

## 2. 必填参数（6 个）

| # | 参数 | 类型 | 法律含义 | 验证规则 |
|---|------|------|---------|---------|
| 1 | data_processor_profile | text | 数据处理者基本情况，决定主体适格性和适用法规 | 非空，至少包含：主体名称+组织形式+注册地+主营业务 |
| 2 | data_export_scenario | text | 数据出境业务场景描述，决定评估范围 | 非空，至少包含：出境目的+传输方式+频率 |
| 3 | export_data_types_quantities | text | 出境数据类型/数量/范围 | 非空，必须含具体数量（不接受"大量""约XX"模糊表述）；敏感信息须单独标注 |
| 4 | overseas_recipient_info | text | 境外接收方基本信息及安全能力描述 | 非空，至少包含：接收方名称+所在国+主营业务 |
| 5 | data_security_measures | text | 已采取的数据安全保护措施现状 | 非空，至少包含：管理措施概述+技术措施概述 |
| 6 | export_purpose_necessity | text | 数据出境目的和必要性说明 | 非空，至少包含：出境目的+必要性理由 |

## 3. 可选参数（8 个）

| # | 参数 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 7 | overseas_legal_env | text | "" | 境外接收方所在国法律环境信息；空值时M6标注"待补充·需境外律师核实" |
| 8 | export_contract_terms | text | "" | 与境外接收方签订的合同安全条款；空值时M8标注"待补充·需提供合同文本" |
| 9 | is_ciio | boolean | false | 是否为关键信息基础设施运营者 |
| 10 | industry_sector | string | "未指定" | 行业领域 |
| 11 | existing_compliance_docs | text | "" | 已有合规文件（PIA报告/分类分级/隐私政策等），可用#24/#25/#26/#27产出 |
| 12 | report_depth | enum | "full" | 报告深度：full（50-100页）/ framework_only（仅框架+缺口清单） |
| 13 | data_transfer_method | enum | "未指定" | 传输方式：API/文件传输/云端访问/邮件/其他 |
| 14 | incident_history | text | "" | 数据安全事件历史 |

## 4. 输入验证逻辑

```
IF 6个必填参数缺失 ≥ 3 个 → SOFT_DEGRADED（仅输出框架+数据缺口清单）
IF 6个必填参数缺失 1-2 个 → 追问补全（最多3轮交互）
IF 敏感信息数量模糊 → 要求具体数字（不接受"约3万"）
IF overseas_legal_env 为空（可选） → M6标注"待补充·需境外律师核实"，不影响其他模块，不计入降级判定
IF export_contract_terms 为空（可选） → M8标注"待补充·需提供合同文本"，不影响其他模块，不计入降级判定
```

## 5. 与上游技能衔接

| 上游技能 | 产出 | 本技能使用方式 |
|---------|------|-------------|
| #24 data-export-path-decision | 路径判断结果 | 验证是否确实需要安全评估路径 |
| #25 data-compliance-gap-analysis | 合规差距清单 | 提取data_security_measures缺口项 |
| #26 data-pia-report | PIA报告 | 作为existing_compliance_docs引用 |
| #27 export-control-item-classification | 出口管制分类 | 核查是否涉及出口管制物项 |
