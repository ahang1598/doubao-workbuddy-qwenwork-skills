# 工作流详述 — 刑事报价方案

> 本文件遵循 compiler/ssot.md §17（SSOT）：可维护度约束·按需拆分

---

## Phase 1: 输入验证与案件画像  [L1]

### 1.1 子步骤

```
Step 1.1: 自然语言提取
  FROM 用户输入 EXTRACT suspected_crime, case_stage, complexity, special_case_type, client_role, jurisdiction
  → 俗称映射（如"醉驾"→危险驾驶罪、"非吸"→非法吸收公众存款罪）
  → 特殊案件类型关键词识别（涉黑/涉恶/监察委/毒品/共同犯罪/无罪/认罪认罚）

Step 1.2: 必需字段校验
  IF suspected_crime 不可识别:
    ASK 1轮："请提供具体的刑法罪名，如盗窃罪、故意伤害罪等"
    IF 追问后仍无法识别: HARD_REJECT
  IF case_stage ∉ {侦查, 审查起诉, 一审, 二审, 申诉, 死刑复核}:
    ASK 1轮："请提供案件所处阶段"
    IF 追问后仍无: DEFAULT "一审" + TAG "⚠️ 阶段信息待确认"

Step 1.3: 当事人角色路由
  IF client_role = "被害人(代理)":
    SET service_template = "victim_representation"  // 使用§2.2.6专属服务项目
  ELSE:
    SET service_template = "defense"  // 使用§2.2.1-2.2.5辩护视角服务项目

Step 1.4: 自定义收费标准检查
  IF custom_fee_standards 已提供:
    EXTRACT stage_fees, complexity_multiplier, hourly_rate, additional_rules
    SET fee_source_priority = "custom"
  ELSE:
    OUTPUT "💡 您可以提供律所/律师的自有收费标准，技能将优先按您的标准进行定价。后续使用时也可随时提供或更新。如无需提供，请忽略此提示。"
    SET fee_source_priority = "regional_or_reference"

Step 1.5: 特殊案件类型识别
  IF special_case_type 非空:
    FOR EACH type IN special_case_type:
      TAG 案件画像 WITH type
    // 涉黑涉恶 → 标记执业风险高、需律所审批
    // 职务犯罪 → 标记监察委调查阶段不属于刑事诉讼
    // 认罪认罚 → 标记量刑协商为核心工作

Step 1.6: 案件画像构建
  OUTPUT 画像: {suspected_crime, case_stage, complexity, special_case_type, amount_involved, jurisdiction, client_role, service_template, custom_fee_standards?, fee_source_priority}
```

### 1.2 门控（必须通过才能进入 Phase 2）

- VERIFY suspected_crime 可识别 → 不通过则 HARD_REJECT
- VERIFY case_stage ∈ 6阶段枚举 → 不通过则追问→默认+标注→继续

### 1.3 降级路径（命令式）

```
IF suspected_crime 无法识别:
  ASK 1轮 → 仍无法识别 → HARD_REJECT
IF case_stage 缺失:
  DEFAULT "一审" + TAG "⚠️ 阶段信息待确认" → DEGRADED-L1 继续
IF client_role 未明确:
  DEFAULT "嫌疑人/被告人(辩护)" → DEGRADED-L1 继续
```

---

## Phase 2: 合规校验与风险代理审查  [L2]

### 2.1 子步骤

```
Step 2.1: 案件类型确认
  → 确认为刑事案件（本技能仅适用于刑事案件）
  → 非刑事案件 → hard_reject + 提示使用对应领域技能

Step 2.2: 风险代理禁止确认
  → 刑事案件 → 风险代理禁止 = true
  → 输出：风险代理禁止标记
  → 用户要求风险代理 → hard_reject + 法律依据

Step 2.3: 收费方式合规范围
  → 允许方式：固定收费 / 计时收费 / 分段固定收费
  → 禁止方式：风险代理收费
  → 输出：{allowed_fee_types: [固定, 计时, 分段固定], prohibited: [风险代理]}

Step 2.4: 自定义收费标准合规审查 [L3]
  → 仅当 custom_fee_standards 非空时执行
  → 逐项检查用户标准中是否存在违法条目：
    → 风险代理条款 → ⚠️标识："该条款违反《律师服务收费管理办法》第12条，刑事案件禁止风险代理收费"，拒绝执行
    → 低于当地最低收费保障 → ⚠️标识："该费用低于{地区}律协最低收费标准，建议调整至¥{最低值}以上"
    → 无依据过高收费 → ⚠️标识："该费用显著高于当地市场水平，存在被投诉风险"
    → 歧视性定价 → ⚠️标识："同类案件差异化定价缺乏合理依据，建议核实"
  → 合规条目标记为 usable = true，违法条目标记为 usable = false + reason
  → 输出：custom_standards_compliance_report

Step 2.5: 地区合规检查
  → jurisdiction 是否可识别？
    → 是 → 标注需参考当地律协指引
    → 否 → 标注"未提供地区，费用估算为全国参考区间"
```

### 2.2 门控（必须通过才能进入 Phase 3）

- VERIFY 案件类型 = 刑事 → 不通过则 HARD_REJECT
- VERIFY 风险代理禁止已确认 → 不通过则阻断
- VERIFY 自定义标准合规审查已完成（如有custom_fee_standards）

### 2.3 降级路径（命令式）

```
IF 非刑事案件:
  HARD_REJECT + GUIDE TO 对应领域技能
IF 用户要求风险代理:
  BLOCK + 输出法律依据（第12条+第（四）项）+ 替代收费方式 → DEGRADED-L3
IF jurisdiction 无法识别:
  TAG "未提供地区，费用估算为全国参考区间" → DEGRADED-L1 继续
```

---

## Phase 3: 服务范围与阶段拆解  [L1]

### 3.1 子步骤

```
Step 3.1: 阶段识别与服务模板路由
  → client_role 确定为"辩护"还是"被害人(代理)"？
    → 辩护 → 使用 output-spec §2.2.1-2.2.5 服务模板
    → 被害人代理 → 使用 output-spec §2.2.6 专属模板
  → case_stage 是否包含多个阶段？→ 单阶段/多阶段

Step 3.2: 服务项目匹配
  → 根据阶段 + 服务模板匹配标准服务项目（见 output-spec.md §2.2）
  → 根据 special_case_type 进行适配调整：
    → 认罪认罚 → 强调量刑协商工作
    → 涉黑涉恶 → 增加会见次数预估 + 标注执业风险
    → 职务犯罪 → 监察委阶段标注服务受限
    → 共同犯罪 → 增加同案犯供述比对工作量
    → 无罪辩护 → 增加调查取证 + 专家论证
  → 根据罪名和复杂度调整：
    → 复杂案件 → 增加服务项
    → 简单案件 → 可能减少部分服务项

Step 3.3: 服务内容描述
  → 为每个服务项目生成工作内容描述
  → 标注服务方式（会见/阅卷/出庭/调查/沟通）
  → 估算工作量（参考值，标注"待律师确认"）
```

### 3.2 门控（必须通过才能进入 Phase 4）

- VERIFY 至少覆盖1个阶段的完整服务项目
- VERIFY 服务模板与 client_role 匹配（辩护→§2.2.1-2.2.5 / 被害人代理→§2.2.6）
- VERIFY 死刑复核阶段有对应服务项目（如 case_stage 含"死刑复核"）

### 3.3 降级路径（命令式）

```
IF client_role = "被害人(代理)" AND case_stage ∉ 审查起诉/一审/二审:
  TAG "被害人代理仅适用于审查起诉、一审、二审阶段" → DEGRADED-L2
IF 阶段信息不完整:
  USE 默认服务范围 + TAG "待确认" → DEGRADED-L1 继续
IF 复杂度无法判断:
  DEFAULT "中等" + TAG "复杂度待确认" → DEGRADED-L1 继续
```

---

## Phase 4: 费用估算与结构设计  [L2]

### 4.1 子步骤

```
Step 4.1: 费率来源确定（三级优先）
  → 第一优先级：用户自定义收费标准（custom_fee_standards）
    → 有 → 使用用户标准中合规条目（置信度 high，来源标注 custom_fee_standards）
    → 用户标准未覆盖的阶段 → 降级到第二优先级
  → 第二优先级：当地律协收费指引（置信度 medium，来源标注 regional_guideline）
    → 无当地指引 → 降级到第三优先级
  → 第三优先级：全国典型参考区间（置信度 low，来源标注 reference_range）
  → 注意：用户标准中违法条目（usable=false）不执行，改用降级来源

Step 4.2: 各阶段费用估算 [LLM推理]
  → 根据费率来源+阶段+复杂度估算
  → 应用律师资历系数（lawyer_experience → methodology §1.7 资历系数表）
  → 应用地区调整系数（jurisdiction → methodology §1.7 地区系数表）
  → 计算公式：最终费率 = 基准费率 × 资历系数 × 地区系数 × 特殊案件类型系数
  → 每项费用标注来源和置信度
  → 费用格式：¥XX,XXX（千分位）
  → ⚠️ 信息不足时区间必须加宽（至少±30%），禁止输出"精确"数字

Step 4.3: 费用结构设计
  → 根据 fee_preference 确定费用结构
  → 固定收费：每阶段一个固定金额
  → 计时收费：每阶段预估小时数×小时费率
  → 分段固定收费：每阶段固定金额+可能调整条款

Step 4.4: 费用汇总
  → 各阶段费用相加 → 总费用
  → 多阶段是否有优惠空间 → 提示"全流程委托可根据实际情况协商"

Step 4.5: 支付节点设计
  → 单阶段：签约付30-40% + 阶段关键节点后付余款
  → 多阶段：各阶段首付比例见 methodology §4.2.1
  → 全流程：首付30-40% + 各阶段开始付20-30%，可协商8-9折优惠
  → 全流程解约补差：已服务×110% + 未服务全额退
  → 标注"支付方式以委托合同约定为准"
  → O6风险提示中预告方案→合同衔接要点
```

### 4.2 门控（必须通过才能进入 Phase 5）

- VERIFY 费用估算有明确来源标注（custom_fee_standards / regional_guideline / reference_range）
- VERIFY 每项费用标注置信度（high / medium / low）
- VERIFY 特殊案件类型调整已应用（如有 special_case_type）
- VERIFY 律师资历系数已应用或标注"资历系数未应用"（如有 lawyer_experience）
- VERIFY 地区调整系数已应用或标注"地区系数未应用"（如有 jurisdiction）
- VERIFY 信息不足时费用区间已加宽（±30%以上）
- VERIFY 不得引用已失效的"政府指导价"作为定价依据

### 4.3 降级路径（命令式）

```
IF 无任何费率参考（无自定义标准 + 无地区指引）:
  OUTPUT 框架性方案（有服务范围无具体金额）→ 费用栏标注"需补充地区信息后估算"
  → DEGRADED-L2
IF 涉案金额不明:
  SKIP 金额相关费用计算 + TAG "未含涉案金额相关调整" → DEGRADED-L1 继续
```

---

## Phase 5: 方案组装与质检  [L2]

### 5.1 子步骤

```
Step 5.1: 方案组装
  → 按顺序组装：O1抬头→O2概况→O3服务范围→O4费用→O5风险代理禁止→O6风险提示→O7必检清单
  → 条件输出块按触发条件插入

Step 5.2: 格式排版
  → C-Professional 客户级排版
  → 标题层级：# → ## → ###
  → 费用表格：阶段/服务/计费方式/费用/依据
  → ⚠️风险代理禁止：引用块醒目标注
  → 金额：¥千分位格式

Step 5.3: 合规复核
  → 检查O5风险代理禁止声明存在
  → 检查费用来源标注完整
  → 检查免责声明完整
  → 检查律师必检清单存在

Step 5.4: 质检输出
  → 全部检查通过 → 输出完整方案
  → 有检查未通过 → 回退修复 → 重新组装
```

### 5.2 门控（全部通过才输出）

- VERIFY O5 风险代理禁止声明存在 + 法条编号正确
- VERIFY 费用每项有来源标注（custom_fee_standards / regional_guideline / reference_range）
- VERIFY 免责声明完整 + 含退费规则摘要
- VERIFY 律师必检清单存在 + 含特殊类型/被害人代理检查项
- VERIFY C5 自定义标准合规审查已输出（如有 custom_fee_standards）

### 5.3 降级路径（命令式）

```
IF 任一门控未通过:
  ROLLBACK TO 对应 Phase → 修复 → RE-ASSEMBLE
IF 修复后仍不通过:
  OUTPUT SOFT_DEGRADED 骨架（O1 + O5 + O6 + O7） + TAG "部分内容需律师手动补充"
```

---

## 快速路径

**触发条件**：用户输入包含 `suspected_crime` + `case_stage` + `jurisdiction`

**执行**：Phase 1→2→3→4→5，跳过 Phase 1 的追问和 Phase 4 的联网检索

---

## 完整路径

**触发条件**：默认路径

**执行**：Phase 1→2→3→4→5，包含所有追问和检索步骤
