# 破产业务专家团（Bankruptcy Business Expert）

面向破产管理人团队和律所破产法律师的 WorkBuddy 专家团，覆盖中国大陆破产清算、破产重整与和解全流程：多案件管理、接管债务人、财产调查与追收、债权申报与审查、职工安置、债权人会议、分配方案、重整计划草案及管理人履职报告。

- **专家类型**：Team 型专家团（1 主理人 + 9 成员）
- **主理人 ID**：`bankruptcy-team-lead`
- **行业分类**：`11-SecurityCompliance`（法务安全）

## 目录结构

```
bankruptcy-business-expert/
├── .codebuddy-plugin/
│   └── plugin.json                  # ★ 配置文件（teamInfo/members/skills/展示字段）
├── avatars/                         # ★ 头像目录（11 张，512×512）
│   ├── team.png                     #    团队头像
│   ├── team-lead.png                #    主理人头像
│   └── member-*.png                 #    9 张成员头像
├── agents/                          # ★ Agent 定义
│   ├── bankruptcy-team-lead.md      #    主理人（{team}-team-lead，含团队协作铁律 + SOP 工作流 + 交付门禁）
│   ├── member-case-manager.md
│   ├── member-claim-review.md
│   ├── member-asset-tracing.md
│   ├── member-distribution-calc.md
│   ├── member-legal-research.md
│   ├── member-reorg-plan.md
│   ├── member-procedure-support.md
│   ├── member-verification.md
│   └── member-employee-resettlement.md
├── skills/                          #    共享技能（20 个：破产领域 10 + 通用工具 10）
│   └── {skill-name}/
│       ├── SKILL.md
│       ├── references/
│       ├── scripts/
│       └── templates/
├── settings.json                    # ★ 设置主理人（"agent": "bankruptcy-team-lead"）
└── README.md                        #    说明文档
```

## 团队成员

| 成员 | 角色 | 职责 |
|---|---|---|
| bankruptcy-team-lead | 主理人 | 调度中枢、报告编排、交付门禁 |
| member-case-manager | 案件管理员 | 多案件建档、材料归集、进度跟踪、期限看板 |
| member-claim-review | 债权审查员 | 八类债权分类、优先顺位、抵销权审查、金额核验 |
| member-asset-tracing | 资产追踪员 | 接管清单、流水分析、关联交易、撤销权线索 |
| member-distribution-calc | 分配计算员 | 分配顺位、清偿率测算、分配方案草案 |
| member-legal-research | 破产法律分析员 | 破产法检索、债权性质认定、撤销权/抵销权分析 |
| member-reorg-plan | 重整与和解方案编制员 | 重整计划、和解协议、清算地板测试 |
| member-procedure-support | 会议与程序支持员 | 债权人会议材料、表决方案、程序合规 |
| member-verification | 破产成果校验员 | 金额一致性、优先级复核、法条核验 |
| member-employee-resettlement | 职工安置专员 | 职工债权、经济补偿、社保清算、群体风险 |

## 工作流

- 破产案件全流程（债权审查 + 资产追踪 + 法律研究 → 分配计算 → 校验）
- 债权审查快速 / 资产追踪或专项研究 / 分配方案 / 重整计划 / 和解协议
- 职工安置 / 债权人会议 / 履职报告 / 案件管理

## 迁移说明

本包由旧格式（`agent.json` + `prompt.md` + `subagents/*.md`）迁移而来，符合《WorkBuddy 专家开发规范 v2.4》。

- 旧 `agent.json.workflows` → 主理人 MD「SOP 工作流」章节
- 旧 `agent.json.deliveryPolicy` → 主理人 MD「交付门禁铁律」章节
- 旧 `agent.json.onboardingProfile` → 主理人 MD「入职初始化」章节
- 旧 `subagents/*.md` 末尾共享契约 → 主理人 MD「团队协作机制（铁律）」章节
- 旧 modelName / tools 字段 → 舍弃（模型与工具由系统统一分配）

> **待替换项**：`avatars/` 下为占位头像，正式上架前需替换为符合规范的 512×512 专业头像。
> **外部依赖风险**：`fadada-laws-and-regulations-retrieval`、`fadada-legal-case-search`、`fadada-special-ocr`、`fadada-web-search` 等 skill 可能依赖法大大平台内部服务（searchLawInfo/searchLawCase），迁移到外部平台后若不可用，成员会按「待核查」降级处理。
