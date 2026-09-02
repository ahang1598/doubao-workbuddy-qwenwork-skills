# 劳动争议维权方案对比 - 风险框架

> 版本: 3.1.0 | 风险等级: L2

## 1. 风险等级：L2

L2风险等级说明：本技能涉及向当事人推荐维权方案，虽不替代律师独立判断，但方案选择直接影响当事人权益。L2级别仅需头部免责声明，不要求段落级标注（SSOT §17.16 R5），保持报告可读性。

## 2. Phase 风险标注

| Phase | 风险等级 | 风险描述 | 控制措施 |
|-------|---------|---------|---------|
| P1 输入验证与九类分类 | L1 | 信息提取不到位 | 交互补全≤3轮 |
| P2 五维方案候选集构建 | L2 | 方案遗漏/通道不完全/请求权未覆盖 | 9通道×5族请求权×4策略强制全覆盖检查 |
| P3 六维对比矩阵构建 | L2 | 胜败概率误判/金额估算偏差 | 三区间估算+概率定性标注+关键因素说明 |
| P4 受众适配与HTML组装 | L2 | 受众语言不当/误导当事人 | 客户化语言转换+免责声明+质量自检 |
| P5 合规红线检查 | L1 | 红线遗漏 | 14条写作红线逐条自检 |
| P6 质量检查 | L1 | 格式/法条/受众适配问题 | 35+10+10项自检 |

## 3. 风险控制规则（8条RC）

### RC-01: 时效红线控制
- trigger_condition: 任一方案时效接近临界（≤30天）或已超时效
- severity: high
- effect_on_output: 红色警告框+倒计时天数+告知"超时效将丧失权利"

### RC-02: 仲裁前置原则控制
- trigger_condition: 推荐方案跳过仲裁直接诉讼
- severity: high
- effect_on_output: 标注例外情形+完整法律依据+告知法院不予受理后果

### RC-03: 受众错配控制
- trigger_condition: 报告中出现律师内部术语未附通俗解释
- severity: medium
- effect_on_output: 术语替换为客户化语言或附加通俗解释括号

### RC-04: 金额估算失控
- trigger_condition: 预期金额给出单一确定数字
- severity: medium
- effect_on_output: 改为三区间标注（最佳/一般/最差）+估算假设前提说明

### RC-05: 证据缺口免责
- trigger_condition: 证据不足（完整度★★☆☆及以下）
- severity: high
- effect_on_output: 在每个方案对比中标注"以下预测基于■的假设前提，实际结果因■决定性证据缺失可能大幅偏离"

### RC-06: 执行不可行预警
- trigger_condition: 对方经营异常/注销/无偿付能力
- severity: high
- effect_on_output: 在所有方案中红色标注"■：对方偿付能力存疑，胜诉后可能面临执行困难"+保全建议

### RC-07: 方案遗漏自检
- trigger_condition: Phase 2构建的方案数<3
- severity: high
- effect_on_output: 强制重新审查9通道×5族请求权，补全遗漏方案

### RC-08: 过度承诺控制
- trigger_condition: 报告中出现"肯定""一定""保证""必然"等绝对化用语
- severity: medium
- effect_on_output: 替换为"基于现有证据和法律规定的预期""参考类案的常见结果"

## 4. SOFT_DEGRADED C+D+G

当输入不足（完整度★☆☆☆或★★☆☆）时，输出最小骨架：

### C) Missing Facts Checklist

| 缺失项 | 影响程度 | 建议来源 |
|--------|---------|---------|
| 争议基本事实 | boundary | 当事人叙述/书面材料 |
| 证据情况 | evaluation | 合同/工资记录/聊天记录/通知书 |
| 时效状态 | boundary | 争议发生日期/仲裁申请日期 |
| 当事人身份 | boundary | 劳动者/企业方 |
| 对方信息 | evaluation | 企查查/天眼查/当事人了解 |
| 工龄与工资 | evaluation | 劳动合同/银行流水 |
| 诉求详细说明 | content_detail | 当事人明确诉求优先级/底线 |

### D) Governance & Non-Goals
- ban_boundary_items：保证胜诉、确定结果、推荐具体方案而不说明前提条件、跳过仲裁前置
- non_goal_items：教唆信访、煽动群体性事件、具体法律文书起草（用对应技能）、案件策略分析（用labor-dispute-strategy）

### G) Actionable Next Steps
- upgrade_actions：补充争议基本事实、收集关键证据（合同/工资记录/解除通知书）、确认时效状态、查询对方经营状况
- target_fields：dispute_facts / evidence / time_status / party_role / counterparty_info / seniority_and_wage

## 5. 格式降级表

| 格式能力 | FULL | DEGRADED-L1 | DEGRADED-L2 |
|---------|------|-------------|-------------|
| 六维对比矩阵 | ✓ | 三维简化 | 不生成 |
| 三区间金额 | ✓ | 单一参考金额 | 仅标注"数据不足无法估算" |
| 风险色谱 | ✓ | 双色（红色+默认） | 仅文字 |
| HTML折叠面板 | ✓ | ✓ | 纯文本 |
| 操作指引 | ✓ | 简化 | 仅通道名称 |
