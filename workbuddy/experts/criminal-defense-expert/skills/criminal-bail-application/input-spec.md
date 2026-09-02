# 输入规格

> 本文件定义 criminal-bail-application 技能的完整输入参数规格
> 遵循 base/governance/ssot-compiler.md §17（SSOT）：输入宽容度契约

## 1. 必需输入

### 1.1 案件基本信息

| 字段 | 类型 | 枚举值 | 说明 | 验证规则 |
|------|------|--------|------|----------|
| `suspect_name` | string | - | 被申请人姓名 | 非空 |
| `alleged_crime` | string | - | 涉嫌罪名 | 非空 |
| `case_stage` | enum | 侦查/审查起诉/审判 | 案件阶段 | 必须为枚举值 |

### 1.2 申请信息

| 字段 | 类型 | 说明 | 验证规则 |
|------|------|------|----------|
| `case_description` | string | 案件基本情况描述 | 自由文本，描述关键事实 |

> **💡 字段边界提示**：`case_description` 字段虽然名为"案件基本情况"，但其内容**既会被写入申请书"一、案件基本情况"段（仅4/5要素）**，也**会被拆解映射到"二、符合取保候审法定条件"或"二、逮捕后情况变化"中作为论证素材**。建议用户在自然语言描述中：
> - **必填基本要素**（将进入"一"段）：涉嫌罪名、拘留日期、羁押机关、羁押场所（逮捕后+逮捕决定书文号、逮捕日期）
> - **可选论证素材**（将进入"二"段或单独子项）：入职时间/任职公司/岗位/任职时长、涉案金额细节、案发后退赔/取得谅解、认罪认罚/认罪态度、家庭情况/健康状况、个人经历等
>
> 字段边界详见 `output-spec.md` §1.1 "案件基本情况"段位黑名单要素表。

## 2. 可选输入

### 2.1 被申请人信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `suspect_gender` | string | [待补充] | 性别 |
| `suspect_birthdate` | string | [待补充] | 出生日期，YYYY-MM-DD |
| `suspect_id` | string | [待补充] | 身份证号 |
| `suspect_address` | string | [待补充] | 住所地 |
| `suspect_occupation` | string | [待补充] | 职业 |
| `suspect_family` | string | [待补充] | 家庭情况 |

### 2.2 羁押信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `detention_date` | string | [待补充] | 羁押日期，YYYY-MM-DD |
| `detention_type` | enum | 刑事拘留/逮捕 | 强制措施类型（**逮捕时触发条件性规则**：第95条论证+逮捕决定书文号+羁押必要性审查并行推荐） |
| `detention_location` | string | [待补充] | 羁押地点（看守所名称） |
| `arrest_warrant_no` | string | [待补充] | 逮捕决定书文号（**逮捕后必填**） |
| `arrest_date` | string | [待补充] | 逮捕日期，YYYY-MM-DD（逮捕后必填） |
| `custody_duration` | number | [待计算] | 已羁押天数（根据日期自动计算） |

### 2.3 办案机关信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `handling_authority` | string | 根据阶段推断 | 办案机关全称 |
| `prosecutor_name` | string | [待补充] | 承办检察官姓名（审查起诉阶段） |
| `judge_name` | string | [待补充] | 承办法官姓名（审判阶段） |

### 2.4 申请人信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `applicant_name` | string | [待补充] | 申请人姓名 |
| `applicant_relationship` | string | [待补充] | 与被申请人关系 |
| `applicant_is_lawyer` | boolean | false | 是否为辩护律师 |
| `lawyer_firm` | string | [待补充] | 律师事务所名称 |
| `lawyer_phone` | string | [待补充] | 律师联系电话 |

### 2.5 保证方式

| 字段 | 类型 | 枚举值 | 默认值 | 说明 |
|------|------|--------|--------|------|
| `guarantee_method` | enum | 人保/财保 | 人保 | 保证方式（二选一，第68条） |
| `guarantor_name` | string | - | [待补充] | 保证人姓名（人保时） |
| `guarantor_relationship` | string | - | [待补充] | 与被申请人关系 |
| `guarantor_income` | string | - | [待补充] | 月均收入 |
| `bail_amount` | number | - | [待补充] | 保证金金额（财保时，单位元） |

### 2.6 特殊情形

| 字段 | 类型 | 说明 | 优先级 |
|------|------|------|--------|
| `special_circumstances` | object | 特殊有利情形 | — |
| `special_circumstances.has_repentance` | boolean | 认罪认罚 | **P0策略最高**——第81条第2款正向因素 |
| `special_circumstances.has_restitution` | boolean | 已退赃退赔 | **P0策略最高**——取保获批最有效路径 |
| `special_circumstances.restitution_amount` | number | 退赃金额（元） | P1——论证具体性 |
| `special_circumstances.has_reconciliation` | boolean | 已取得谅解 | P1——降低社会危险性评估 |
| `special_circumstances.has_no_prior` | boolean | 无前科劣迹 | P1 |
| `special_circumstances.has_family_support` | boolean | 家庭需其照料 | P2 |
| `special_circumstances.has_illness` | boolean | 患病需治疗 | P2 |
| `special_circumstances.has_fixed_residence` | boolean | 有固定住所 | P2 |
| `special_circumstances.has_stable_job` | boolean | 有稳定工作 | P2 |
| `special_circumstances.other` | string | 其他有利情节 | P3 |

### 2.7 证明材料

| 字段 | 类型 | 说明 |
|------|------|------|
| `evidence_list` | array[string] | 已有的证明材料清单 |
| `evidence_to_submit` | array[string] | 可提交的证明材料清单 |

## 3. 输入宽容度契约

### 3.1 最小输入识别

技能在接收到以下任一输入时应触发最小输入模式：

| 最小输入 | 触发条件 |
|----------|----------|
| 仅嫌疑人姓名+罪名 | 生成通用模板，待补充信息 |
| 仅"取保"关键词 | 询问案件基本信息 |
| 仅案件描述 | 提取关键信息生成申请书 |

### 3.2 信息补全策略

对于缺失字段，按以下优先级补全：

1. **从案件描述中提取**：自然语言处理提取关键信息
2. **推理补全**：根据已知信息推理（如已有退赃→自动标注"已退赃"）
3. **占位符标注**：无法提取的信息用 `[待补充]` 标注

### 3.3 交互补全限制

交互补全最多3轮，超过后强制进入 SOFT_DEGRADED 模式。

## 4. 场景适配规则

### 4.1 阶段适配

| 阶段 | 致送机关 | 申请书侧重点 | 逮捕后条件性规则 |
|------|----------|-------------|---------|
| 侦查 | XX市公安局XX分局 | 时效性（拘留后尽早提交）、紧急性 | 如已逮捕→触发第95条论证 |
| 审查起诉 | XX市人民检察院 | 证据已固定、论证更充分 | 如已逮捕→触发第95条论证 |
| 审判 | XX市中级人民法院/区人民法院 | 量刑预判、社会危险性持续论证 | 如已逮捕→触发第95条论证 |

### 4.2 逮捕后条件性规则触发条件

| 输入条件 | 触发规则 | 说明 |
|----------|------|------|
| `detention_type` = "逮捕" | **条件性规则** | 增设第95条论证+逮捕决定书文号+羁押必要性审查并行推荐 |
| `detention_type` = "拘留" | 不触发 | 仅第67条论证 |
| `detention_type` 未指定 | **推断** | 根据`case_stage`+`detention_date`推断：审查起诉/审判阶段且detention_date>37天前→推断为逮捕→触发条件性规则；侦查阶段或detention_date≤37天前→推断为拘留 |
| 推断失败 | **不触发（默认）** | 标注"[建议补充逮捕信息以启用第95条论证]" |

### 4.3 羁押时长适配

| 羁押时长 | 论证策略调整 |
|----------|-------------|
| < 30天 | 强调申请紧迫性、黄金期 |
| 30-60天 | 强调已过羁押必要性论证窗口 |
| > 60天 | 强调长期羁押对当事人权益的损害 |

---

*本文件遵循 base/governance/ssot-compiler.md §17（SSOT）：输入宽容度契约*
