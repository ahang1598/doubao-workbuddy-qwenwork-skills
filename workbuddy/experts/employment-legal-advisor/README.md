# 劳动人事专家团

面向企业HR、法务和劳动法律师的法律专家团，覆盖中国大陆劳动用工诊断、用工合规体检、劳动合同与人事制度审查、补偿赔偿计算、员工安置方案、劳动仲裁与诉讼文书的全流程服务，锁定地域裁判口径并保证金额公式可复核。

- **专家类型**：Team 型（多角色协作团队）
- **专家 ID**：`employment-legal-advisor`
- **行业分类**：法务安全（11-SecurityCompliance）

## 团队架构

```
劳动人事专家团（主理人：齐合法 - 劳动法务总监）
├── 用工诊断分析员（史实清 - employment-fact-analyst）
│   劳动关系事实轴、争议焦点、证据三性、材料缺口
├── 法规口径研究员（罗有据 - employment-research-specialist）
│   劳动法规、地方裁判口径、类案倾向、效力时效核验
├── 补偿赔偿计算员（贾算准 - employment-compensation-calc）
│   经济补偿/赔偿金/二倍工资/加班费/工伤待遇逐步可复核测算
├── 劳动文书起草员（温必达 - employment-drafting-specialist）
│   合同/解除协议/安置方案/制度/仲裁诉讼文书、三档谈判方案
└── 成果质量核验员（严过关 - employment-verification-officer）
    意图达成核验、金额重算、法源校验、跨阶段一致性、执业红线扫描
```

## 标准工作流程（SOP）

### 路由决策

主理人收到用户问题后，按复杂度和风险等级选择路径：

| 路径 | 调用数 | 适用场景 |
|------|--------|---------|
| 对话快车道 | 0 | 能力说明、程序常识、材料清单、已有成果追问 |
| 单专家路径 | 1 | 单一维度的诊断、研究或快速测算 |
| 标准路径 | 2-3 | 研究/事实 + 起草/测算 + 核验 |
| 完整路径 | 5 | 争议案件、批量安置、经济性裁员等复杂事项 |

### 预设 Workflow

| Workflow | 触发条件 | Phase 编排 |
|----------|---------|-----------|
| `employment_diagnosis` | 事实梳理/材料缺口/争议焦点 | 史实清单独执行 |
| `research_only` | 单一劳动法问题或地方口径研究 | 罗有据单独执行 |
| `compensation_quick` | 输入充分的单项测算 | 贾算准执行，按风险决定是否追加严过关 |
| `employment_risk_assessment` | "能否解除/有哪些风险"个案判断 | 史实清+罗有据（并行）-> 严过关/主理人整合 |
| `employment_document` | 合同/制度/协议/争议文书起草 | 事实/研究前置 -> 温必达起草 -> 严过关核验 |
| `employment_dispute_full` | 争议案件/批量安置/经济性裁员/复杂工伤 | 史实清+罗有据 -> 贾算准 -> 温必达 -> 严过关 -> 主理人汇编 |

## 绑定的技能

| 技能 | 用途 |
|------|------|
| labor-arbitration-application | 劳动争议仲裁申请书生成 |
| labor-dispatch-compliance-review | 劳务派遣五层穿透式合规审查 |
| labor-dispute-rights-protection-scheme-comparison | 劳动争议多维权方案对比报告 |
| labor-employment-system-generation | 企业劳动用工制度文件包生成 |

## 适用场景

1. 处理劳动争议应诉、起诉与上诉，输出事实轴、争议焦点、补偿测算和文书初稿
2. 对企业开展用工合规体检，排查合同、制度、社保、加班、竞业等隐患并出整改建议
3. 审查和起草劳动合同、规章制度、员工手册及保密/竞业限制专项条款
4. 设计批量解除、经济性裁员和公司解散员工安置方案及配套协议包
5. 按锁定地域口径测算经济补偿、违法解除赔偿金、二倍工资、加班费和工伤待遇

## 能力边界

- 仅限中国大陆法劳动用工事项；跨境用工、外籍员工只做识别并提示转交
- 所有补偿金额均按规则口径测算，绑定明确地域，不预测胜诉率或裁判最终支持额
- 所有输出均为 AI 辅助生成的律师工作底稿，解除、签署、放弃抗辩和启动裁员安置程序须由用人单位或授权人确认
- 不得默认套用 at-will employment、FLSA、FMLA、WARN 等美国劳动法框架
- 不得虚构法条、文号、案号或地方口径，无法核验时统一标记"待核查"

## 高风险人工复核闸门

以下事项不得由 Agent 直接完成最终决策或自动外发：

- 解除、终止、辞退、停职、降薪、调岗、纪律处分
- 经济性裁员、批量安置、员工代表或工会相关程序
- 协议签署、权利放弃、和解、仲裁/诉讼提交
- 孕期/产期/哺乳期、医疗期、工伤、职业病、工会人员等特殊保护场景
- 最终补偿金额、竞业限制启动或停止、重大社保补缴方案

## 文件结构

```
employment-legal-advisor/
├── .codebuddy-plugin/
│   └── plugin.json                              # 专家包配置
├── agents/
│   ├── employment-team-lead.md                  # 主理人（齐合法）
│   ├── employment-fact-analyst.md               # 用工诊断分析员（史实清）
│   ├── employment-research-specialist.md         # 法规口径研究员（罗有据）
│   ├── employment-compensation-calc.md           # 补偿赔偿计算员（贾算准）
│   ├── employment-drafting-specialist.md         # 劳动文书起草员（温必达）
│   └── employment-verification-officer.md        # 成果质量核验员（严过关）
├── avatars/                                      # 头像（7张：团队+主理人+5团员）
├── skills/
│   ├── labor-arbitration-application/            # 劳动仲裁申请书生成
│   ├── labor-dispatch-compliance-review/         # 劳务派遣合规审查
│   ├── labor-dispute-rights-protection-scheme-comparison/  # 维权方案对比
│   └── labor-employment-system-generation/       # 劳动用工制度生成
├── settings.json
└── README.md
```

## 头像

头像通过 ImageGen 自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512x512 px
- 大小：单张不超过 500KB
- 同一团队画风一致，各角色通过外观特征、配饰和背景元素差异化

## 推荐提示词

- 帮我分析一个劳动争议案件
- 计算员工解除的经济补偿金
- 审查并起草劳动合同
