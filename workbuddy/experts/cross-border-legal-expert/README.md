# 跨境法律服务专家团（cross-border-legal-expert）

面向涉外律师和出海/外资企业法务的 **Agent Team（专家团）**，覆盖外国法与多法域比较、ECLI/CELEX/案号精确引用核验、境外许可牌照与市场准入、英文/双语合同审查与真实 OOXML 红线、ODI/FDI 与跨境并购架构、制裁与出口管制筛查、供应链及数据出境合规和国际争议协同。

架构方案（单 Agent 前台 + Agent Team 后台按需升级）详见
`richee-resources/agents/cross-border-legal-expert/开发方案总结.md`。

## 包结构

```text
cross-border-legal-expert/
├── .codebuddy-plugin/plugin.json   # 插件清单（expertType: team，6 Agent / 14 Skill）
├── settings.json                   # 默认入口 Agent
├── README.md
├── agents/
│   ├── cross-border-lead.md                 # 主 Agent：快速沟通 + L0-L2 分级路由 + 交付门禁
│   ├── subagent-crossborder-material.md     # 涉外材料与法域识别员（按需启动）
│   ├── subagent-crossborder-research.md     # 跨境法律研究与法域比较员
│   ├── subagent-crossborder-screening.md    # 制裁与跨境合规筛查员
│   ├── subagent-crossborder-drafting.md     # 涉外交易文件与双语起草员
│   └── subagent-crossborder-verification.md # 涉外成果与双语校验员（独立门禁）
├── avatars/                        # 6 个成员头像
└── skills/                         # 14 项绑定技能（见下表）
```

## 团队成员

| 成员 | 花名 | 角色 | 启动条件 |
|---|---|---|---|
| cross-border-lead | 阚涉衡 | 主 Agent：意图识别、澄清、路由、门禁核对、结果整合；不绑定专业 Skill | 所有请求 |
| subagent-crossborder-material | 文溯界 | OCR、多文件归集、主体/日期/条款/法域连接点提取 | 仅扫描件、多文件或要素不清时 |
| subagent-crossborder-research | 欧鉴法 | 外国法、判例、精确引用、境外许可、多法域比较 | 动态法源或具体境外规则 |
| subagent-crossborder-screening | 雷慎裁 | 制裁、出口管制、供应链、数据出境筛查 | 主体、物项、供应链或数据路径筛查 |
| subagent-crossborder-drafting | 章译衡 | 合同审查、红线、SPA/SHA、ODI 架构、翻译 | 正式起草或合同审查 |
| subagent-crossborder-verification | 严校境 | 意图、法域、引用、Skill 证据、制品和高风险门禁 | 正式交付或高风险结论 |

## 固定工作流

| workflowId | 用途 | 路由 | 最大子任务 |
|---|---|---|---:|
| `contract_review_full` | 整份英文/双语合同审查、红线修订与交付校验 | 干净材料：drafting+screening+research 并行 → verification；复杂材料先 material | 5 |
| `contract_review_quick` | 单条款或用户明确指定的快速审查 | drafting → verification | 2 |
| `legal_report` | ODI/FDI、跨境并购、数据出境等分析报告 | research（可并行 screening）→ drafting → verification | 4 |
| `legal_research` | 外国法、判例、精确引用、境外牌照与单点准入研究 | research → verification | 2 |
| `compliance_screening` | 制裁、出口管制、供应链和数据出境专项筛查 | screening → verification | 2 |

主 Agent 快速沟通（direct_dialogue，零子代理）：概念/流程问答、能力边界、材料清单、路由分流、既有成果解释。要求现行法、来源、具体法域结论、正式文件时立即升级。

## 绑定技能（14 项）

| 技能 ID | 绑定角色 | 来源 |
|---|---|---|
| global-legal-research | research（主通道） | 技能市场/涉外与跨境 |
| cross-border-spa-sha-drafting | drafting | 技能市场/涉外与跨境 |
| overseas-investment-structure-design | drafting | 技能市场/涉外与跨境 |
| legal-translation | drafting、verification | 技能市场/涉外与跨境 |
| export-control-compliance-system-design | screening | 技能市场/涉外与跨境 |
| supply-chain-compliance-review | screening | 技能市场/涉外与跨境 |
| data-export-security-assessment-report | screening | 技能市场/涉外与跨境 |
| international-trade-policy-change-early-warning | screening | 技能市场/涉外与跨境 |
| fadada-professional-contract-information-extraction | material | 技能市场/合同 |
| english-contract-review | drafting（审查强制首调） | 对齐 commercial-contract-expert 同版本 |
| word-document-processing | material、research、drafting、verification | 通用文档能力（同其他专家包版本） |
| pdf-generation-editing-tool | material、drafting、verification | 通用文档能力（同其他专家包版本） |
| html-document-generation | research（HTML 报告） | 通用文档能力（同其他专家包版本） |
| excel-table-processing | material | 通用表格能力 |

技能 ID 治理：只使用 canonical Skill ID；`html-document-generation`、`global-legal-research` 均为规范 ID，非规范历史别名不进入本包。

## 交付门禁（摘要）

- `contract_review_full` 必须同时具备 `english-contract-review` 与 `global-legal-research` 成功证据；`review_report` 可打开，`redline_contract` 含真实 OOXML `<w:ins>/<w:del>` 修订，含 `verification_record` 与"可签/修改后可签/暂缓"决策树。
- `legal_research` 派发前必须选定报告格式（Word/HTML/两者）与研究深度（快速 3–4 分钟/标准 5–7 分钟/深入 8–10 分钟）；主题研究走"法域解析 → source/filter → 单法域 precise-search → get"，精确引用走"resolve(reference) → get"。
- 未清零高风险（制裁命中、疑似命中、待核查）不得返回 passed/completed。
- 首次门禁失败用 `resumeSubSessionId` 定点恢复原子会话；补齐一次仍失败则 `policy_blocked`。
- 主 Agent 只消费 `userVisibleArtifacts`；Markdown 母版、structured_findings、verification_record 与验证 sidecar 均为内部制品。

## 转交边界

- 纯中国大陆中文单份合同审查/起草 → `commercial-contract-expert`
- 境内常法合规体系 → `enterprise-compliance-counsel-expert`
- 境内劳动用工制度 → `employment-legal-advisor`
- 境外诉讼出庭、正式外国法意见签署 → 当地执业律师或获授权专业机构

## 维护说明

- avatars/ 当前复用 investment-financing-legal-advisor 头像作为过渡占位，待替换为跨境专家专属唯一版本。
- 源方案与提示词基线：`richee-resources/agents/cross-border-legal-expert/`（agent.json、prompt.md、subagents/*.md）。
