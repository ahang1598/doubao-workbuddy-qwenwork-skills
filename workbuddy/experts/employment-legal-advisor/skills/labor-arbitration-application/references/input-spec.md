# 输入规格 | 劳动争议仲裁申请书

> 版本: 3.3.0 | 风险等级: L2

## 1. 必需参数

| 参数 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `applicant` | object | 申请人信息 | 含 name(必填)/id_number(必填)/contact(必填)/gender/ethnicity/birth_date/address/service_address |
| `respondent` | object | 被申请人信息 | 含 company_name(必填)/legal_representative(必填)/address(必填)/contact(P0级)/unified_social_credit_code/actual_business_address/service_address |
| `arbitration_claims` | array | 仲裁请求数组 | ≥1项，每项含 type/amount/description，推荐含 priority/formula/legal_basis/period |
| `facts_and_reasons` | string | 事实与理由 | ≥100字，含入职/工作/争议/解除等关键时间节点 |
| `evidence_list` | array | 证据清单 | ≥1项，每项含 name/purpose/category |

### applicant 子项

> O1渲染顺序：姓名，性别，民族，××××年×月×日生，住××省××市××小区×栋×号，公民身份号码××，联系电话××××。（所有信息要真实有效）

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `name` | string | 申请人姓名 | 必填 |
| `gender` | string | 性别 | 选填，如"男""女" |
| `ethnicity` | string | 民族 | 选填，如"汉族""回族"，调解仲裁法第28条法定要素 |
| `birth_date` | string | 出生年月日 | 选填（可从身份证号推算），格式"XXXX年X月X日"，调解仲裁法第28条法定要素 |
| `id_number` | string | 公民身份号码 | 必填，18位，O1输出使用"公民身份号码"而非"身份证号" |
| `address` | string | 住址 | 精确到门牌号，如"××省××市××小区×栋×号" |
| `service_address` | string | 文书送达地址 | **重要**：仲裁委送达文书用，可与住址不同 |
| `contact` | string | 联系电话 | 必填 |

### respondent 子项

> O1渲染（被申请人信息）：××××××公司，统一社会信用代码××××，住所地：××市××路××号，联系电话××××。（名称完整并准确无误，不能写简称；信息要真实有效，保证法律文书能够送达到单位）
> O1渲染（法定代表人信息）：法定代表人：×××，职务。（另起一段，紧接被申请人信息段之后）

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `company_name` | string | 单位名称 | 必填，与工商登记一致，**不能写简称** |
| `legal_representative` | string | 法定代表人 | 必填 |
| `legal_rep_position` | string | 法定代表人职务 | 选填，如"总经理""执行董事"，O1输出格式"法定代表人：×××，职务" |
| `address` | string | 住所地 | 必填，精确到门牌号，O1输出使用"住所地"而非"注册地址" |
| `contact` | string | 联系电话 | **重要**：立案送达必备，P0级交互补全项 |
| `unified_social_credit_code` | string | 统一社会信用代码 | **重要**：仲裁委立案必填 |
| `actual_business_address` | string | 实际经营地址 | 如与注册地址不同须填写 |
| `service_address` | string | 文书送达地址 | 如与注册地址/实际经营地址不同须填写 |

### arbitration_claims 子项

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `type` | string | 请求类型 | payment/confirmation/behavior/compensation/annual_leave/overtime/allowance/notice_period/insurance_loss |
| `amount` | number | 请求金额 | 精确到元，payment/compensation等金钱请求必填 |
| `description` | string | 请求描述 | ≤100字，金额须与amount一致 |
| `priority` | string | 请求优先级 | primary(主位)/secondary(备位)，默认primary |
| `formula` | string | 计算公式 | 如"8,000元/月×3.5年×2倍"，金钱请求强烈推荐 |
| `legal_basis` | string | 法律依据 | 对应法条编号，如"劳动合同法第48条" |
| `period` | string | 涉及期间 | 如"2024年11月至2025年1月" |

### evidence_list 子项

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `name` | string | 证据名称 | 具体明确，如"2024年1月至6月银行流水" |
| `purpose` | string | 证明目的 | ≤50字，与仲裁请求关联 |
| `category` | string | 证据分类 | identity(身份)/fact(事实)/auxiliary(辅助)，默认fact |
| `evidence_holder` | string | 证据持有人 | applicant(申请人持有)/respondent(被申请人持有)/third_party(第三方持有)，默认applicant。如为respondent：在申请书中须提出"该证据由被申请人掌握，应由其提供" |
| `source` | string | 证据来源 | 电子证据须标注（如"微信聊天记录-与HR张某"） |
| `original_preserved` | boolean | 原始载体是否保留 | 电子证据须标注 |

## 2. 可选参数

| 参数 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `labor_relation_start` | string | 劳动关系起始日期 | 格式 YYYY-MM-DD |
| `labor_relation_end` | string | 劳动关系终止日期 | 格式 YYYY-MM-DD |
| `monthly_salary` | number | 月工资标准 | 精确到元，须明确是应发还是实发 |
| `work_years` | number | 工作年限 | 保留2位小数 |
| `applicant_role` | string | 申请方角色 | employee/employer，默认employee |
| `arbitration_committee` | string | 管辖仲裁委员会全称 | 须与劳动合同履行地或用人单位所在地对应 |
| `contract_type` | string | 合同类型 | fixed_term/open_ended/completed_task/part_time |
| `social_insurance_status` | string | 社保缴纳状态 | full/partial/none |
| `social_insurance_base` | number | 社保缴纳基数 | 用于社保损失计算，精确到元，选填 |
| `wage_payment_method` | string | 工资发放方式 | bank_transfer(银行转账)/cash(现金)/wechat_alipay(微信支付宝)，影响证据收集方向 |
| `working_hours_system` | string | 工时制度 | standard(标准工时)/comprehensive(综合计算工时)/flexible(不定时工作制)，影响加班费计算方式 |
| `agent_info` | object | 委托代理人信息 | 含 name/firm/license_number/contact/authorization_scope，如委托律师代理须填写；如有两个代理人，每个代理人独立一段 |
| `wage_arrears_period` | object | 欠薪期间 | 含 start_month/end_month/months_count |
| `jurisdiction_preference` | string | 管辖偏好 | performance_location(履行地)/employer_location(所在地) |
| `limitation_defense` | string | 时效抗辩预估 | safe/warning/critical，P0评估用 |
| `burden_of_proof_assessment` | object | 举证能力评估 | 含 strong_items/weak_items/missing_items |
| `salary_composition` | object | 工资构成 | 含 base_salary/bonus/allowance/overtime_pay/other |
| `hourly_wage` | number | 小时工资 | 用于加班费计算：月工资÷21.75÷8 |
| `annual_leave_days` | number | 应休年休假天数 | 根据工作年限确定 |
| `annual_leave_taken` | number | 已休年休假天数 | 用于计算未休年休假工资 |

## 3. 输入形态

支持6种输入形态：
1. **自然语言**：自由文本描述争议事实与仲裁请求
2. **结构化JSON**：按上述参数格式直接提供
3. **仲裁请求清单**：逐项列举请求，附简要事实
4. **律师意见书**：律师撰写的申请策略与请求
5. **对话式**：一问一答逐步提供
6. **混合模式**：部分结构化+部分自然语言

## 4. 交互补全

当缺少必需参数时，技能交互补全（最多3轮）：

| 缺失项 | 补全问题 | 优先级 |
|--------|---------|--------|
| 申请人身份信息 | "请提供申请人姓名、公民身份号码和联系电话" | P0 |
| 申请人文书送达地址 | "请提供申请人文书送达地址（仲裁委送达文书用）" | P0 |
| 被申请人信息 | "请提供被申请人单位名称（完整全称，不能写简称）、统一社会信用代码、住所地和联系电话" | P0 |
| 法定代表人信息 | "请提供法定代表人姓名和职务" | P0 |
| 被申请人实际经营地址 | "请提供被申请人实际经营地址（如与注册地址不同）" | P1 |
| 仲裁请求 | "请明确仲裁请求，每项须含具体金额和计算依据" | P0 |
| 事实与理由 | "请简述争议事实（入职时间、争议经过、解除原因等）" | P1 |
| 证据材料 | "请列出现有证据及证明目的" | P1 |
| 工资标准 | "请提供月工资标准（含基本工资、绩效、津贴等），确认是应发还是实发" | P2 |
| 管辖选择 | "劳动合同履行地和用人单位所在地分别在何处？（影响管辖选择）" | P2 |

## 5. 输入验证规则

| 规则 | 级别 | 说明 |
|------|------|------|
| 仲裁请求金额须精确到元 | 阻断 | 模糊金额需交互确认 |
| 事实与理由≥100字 | 警告 | 不足时触发C块降级 |
| 被申请人须为单位 | 阻断 | 劳动争议被申请人为用人单位 |
| 须属劳动争议范围 | 阻断 | 非劳动争议拒绝处理 |
| 仲裁时效检查 | 警告 | 超1年时效时提示，不拒绝 |
| 送达地址是否已提供 | 警告 | 缺失时提示补充 |
| 统一社会信用代码 | 警告 | 缺失时提示补充，仲裁委立案可能要求 |
| 请求类型是否在9类范围内 | 警告 | 不在范围内时按最接近类型处理 |
