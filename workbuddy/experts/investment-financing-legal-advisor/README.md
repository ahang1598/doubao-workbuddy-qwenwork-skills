# 投融资法律顾问专家团（Investment & Financing Legal Advisor Team）

> WorkBuddy 专家包 · expertType: **team** · v1.0.0
>
> 面向企业法务与投融资律师，覆盖中国大陆股权投资、并购重组、增资、老股转让、交易文件、交割与投后治理的全流程法律辅助，内嵌执业安全红线与资产保护门禁。

## 专家类型

**Team 型（专家团）**：1 名主理人 + 5 名专业成员。用户始终只与主理人对话，主理人按 **L0–L3 分层路由**调度成员——简单问题零调度，单项专业问题单次调度，正式/高风险任务才进入独立核验与全流程（参考《开发方案总结》"一个窗口、四级路由、五个专业角色"架构）。

## 团队成员

| 角色 | Agent ID | 花名 | 职业头衔 | 绑定技能 |
|------|----------|------|----------|----------|
| 主理人 | investment-financing-lead | 融执衡 | 首席投融资调度官 | —（只调度不执行） |
| 成员 | due-diligence-analyst | 沈溯真 | 投融资尽调分析员 | company-equity-due-diligence, due-diligence-material-checklist-generator, holder-confirmation-and-risk-mitigation, cap-table-verify-and-dilution-simulate, company-governance-diagnosis-and-compliance-review, ip-asset-ledger-risk-assessment, fadada-professional-contract-information-extraction, fadada-special-ocr, word-document-processing, pdf-generation-editing-tool, excel-generation-editing-tool |
| 成员 | regulatory-research-analyst | 苏鉴规 | 投融资法规研究员 | fadada-laws-and-regulations-retrieval, fadada-legal-case-search, global-legal-research |
| 成员 | document-drafting-specialist | 章拟衡 | 投融资文件起草员 | investment-agreement-review, draft-and-review-investment-intent, investor-special-rights-clause-design, transaction-clause-adversarial-analysis, cap-market-founder-liability-review, cap-market-multi-round-consistency, corporate-governance-rules-drafting, fadada-professional-contract-review, fadada-professional-contract-drafting, word-document-processing, pdf-generation-editing-tool, excel-generation-editing-tool |
| 成员 | closing-management-specialist | 毕守成 | 投融资交割管理员 | post-holder-protection, company-governance-diagnosis-and-compliance-review, cap-table-verify-and-dilution-simulate, investment-exit-dispute-resolution, fadada-professional-contract-review, fadada-laws-and-regulations-retrieval, word-document-processing, excel-generation-editing-tool, pdf-generation-editing-tool |
| 成员 | quality-verification-officer | 严校之 | 投融资成果核验员 | fadada-laws-and-regulations-retrieval, fadada-legal-case-search |

## L0–L3 分层路由

| 级别 | 适用情形 | 子 Agent 调用 |
|---|---|---:|
| L0 即时沟通 | 常识问答、能力说明、材料清单、路径分流、既有成果解读 | 0 |
| L1 单项快速 | 单一法规问题、单条款分析、单文件快速审查 | 1 |
| L2 标准专业 | 正式 docx/xlsx 制品、多条款联动、要求独立复核 | 2 |
| L3 高风险/全流程 | 高金额、控制权交易、外资/国资/反垄断、完整尽调或全流程 | 3–5 |

8 条工作流：`investment_consultation_instant` / `investment_answer_quick` / `investment_review_quick` / `investment_review_standard` / `investment_due_diligence` / `investment_transaction_document` / `investment_transaction_full` / `closing_management`。每条工作流有独立的必需技能证据、必需制品与核验要求（按工作流门禁，非全局一刀切）。

## 技能清单（25 项，复制自技能市场）

| 来源分类 | 技能 |
|---------|------|
| 资本市场（14） | cap-market-founder-liability-review, cap-market-multi-round-consistency, cap-table-verify-and-dilution-simulate, company-equity-due-diligence, company-governance-diagnosis-and-compliance-review, draft-and-review-investment-intent, due-diligence-material-checklist-generator, holder-confirmation-and-risk-mitigation, investment-agreement-review, investment-exit-dispute-resolution, ip-asset-ledger-risk-assessment, investor-special-rights-clause-design, post-holder-protection, transaction-clause-adversarial-analysis |
| 公司设立与治理（1） | corporate-governance-rules-drafting |
| 合同（3） | fadada-professional-contract-information-extraction, fadada-professional-contract-review, fadada-professional-contract-drafting |
| 常用工具·办公（4） | fadada-special-ocr, word-document-processing, pdf-generation-editing-tool, excel-generation-editing-tool |
| 常用工具·法律检索（2） | fadada-laws-and-regulations-retrieval, fadada-legal-case-search |
| 涉外与跨境（1） | global-legal-research |

> 与原始 `richee-resources/agents/investment-financing-legal-advisor/agent.json` 的差异：原引用的 `fadada-web-search` 不存在于技能市场，已剔除（研究员保留法规/类案/全球法律研究三项检索能力）。

## 目录结构

```
investment-financing-legal-advisor/
├── .codebuddy-plugin/
│   └── plugin.json          # 专家团配置（teamInfo + members + 25 skills）
├── agents/
│   ├── investment-financing-lead.md       # 主理人（L0-L3 路由 + 工作流门禁）
│   ├── due-diligence-analyst.md           # 尽调分析员
│   ├── regulatory-research-analyst.md     # 法规研究员
│   ├── document-drafting-specialist.md    # 文件起草员
│   ├── closing-management-specialist.md   # 交割管理员
│   └── quality-verification-officer.md    # 成果核验员
├── skills/                  # 25 项绑定技能（自技能市场复制）
├── avatars/                 # 6 个成员头像（512x512 PNG）
├── settings.json
└── README.md
```

## 设计要点（对照《开发方案总结》P0/P1/P2）

1. **交付政策按工作流拆分**：不再用一套全局 `coreDelivery` 约束所有任务，L0 无制品要求、L1 结论+自检、L2/L3 才要求独立核验（P0-1/P0-2）。
2. **能力闭环修复**：研究员默认产出结构化研究结论（中间件），正式 Word 报告仅由具备文档能力的成员产出；核验员固定产出不可见 `verification_record`，不再依赖未绑定的 Word 技能（P0-3/P0-4）。
3. **运行包边界**：发布 zip 不留在本源目录（P0-5）。
4. **L0/L1 快速路径**：新增即时沟通与单项快速路由，快速审查为单趟自检，高风险标志命中时升级（P1）。
5. **交割按需拆出**：仅用户要求交割管理或交易进入签约/交割时调用 closing（P1-3）。
6. **入职轻量化**：必填仅 2 项（投资方身份、交易类型），其余可跳过（P2-5）。

## 边界与转交

- 仅限中国大陆法；FDI/ODI、外资准入、VIE 的中国法监管部分可做，境外法与境外架构文件转交跨境法律专家。
- 已发生投后诉讼/仲裁转民商事诉讼专家；财务/税务尽调、估值与投资决策不在范围内。
- 签署、申报、打款、CP 豁免等动作一律保留人工决策。

## 头像

头像位于 `avatars/` 目录，由 PIL 脚本生成，可手动替换（PNG，512x512，≤500KB）。
