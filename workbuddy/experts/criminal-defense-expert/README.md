# Criminal Defense Expert（刑事辩护专家团）

面向中国大陆刑事辩护律师和涉刑事务法务的 Agent Team，按案件阶段、文种、输出场景与特殊程序标签调度材料分析、辩护研究、文书起草、庭审支持和成果校验，覆盖侦查、审查批捕、审查起诉、一审、二审及未成年人、简易速裁、认罪认罚、非法证据排除与特殊程序。

## 类型

Team 型（多角色协作团队）· 规范版本：WorkBuddy 专家包规范 v2.0

## 团队成员

| 成员 ID | 花名 | 职业 | 职责 |
|---------|------|------|------|
| criminal-defense-team-lead | 辩明远 | 首席辩护调度官 | 意图识别、上下文冻结、任务路由、状态恢复、结果整合 |
| criminal-material-analyst | 甄明察 | 材料与证据分析师 | 建案、材料索引、阅卷笔录、证据三性与证据链分析、讯问与电子证据分析 |
| criminal-research-strategist | 闫慎思 | 辩护策略研究员 | 构成要件、辩护路径、量刑、认罪认罚、会见沟通和法规类案研究 |
| criminal-drafting-specialist | 章文达 | 刑事文书起草师 | 按阶段、文种和输出场景起草刑事程序与辩护文书 |
| criminal-trial-support | 智庭锋 | 庭审质证专员 | 质证提纲、刑事发问与举证、庭审模拟与庭后复盘 |
| criminal-verification-officer | 校严明 | 交付校验官 | 正式交付前确定性校验，区分警告、补充输入与根本阻断 |

## 核心设计

- **薄主控，厚能力**：主理人不绑定专业 Skill，只做路由与整合；实体能力由主理人加载责任成员的绑定 Skill 完成。
- **技能调度型协作**：成员角色由 `agents/*.md` 定义（人格、能力边界、工作流与输出规范），专业产出由主理人加载成员绑定技能执行，不依赖 Agent 工具 spawn 子进程（插件 `agents/` 目录未注册为可 spawn 类型）。
- **以案件为上下文边界**：首次收到材料时冻结唯一 `matter_id`，案件目录隔离。
- **以阶段、场景、标签做最小路由**：三组语义决定程序位置、致送机关和 Skill 装配。
- **一个任务只有一个责任角色**：材料、研究、起草、庭审、校验责任隔离，校验角色只校不创。
- **模型判断与确定性校验分层**：LLM 负责事实组织与文本起草，脚本负责文件可打开性、模板回执、文种机关错配等可机械检查事项。
- **宽容降级**：草稿允许占位和待核验项，缺料不变成死循环。

## 动态路径

- **路径 A（零技能加载）**：能力说明、材料清单、基础流程导航。
- **路径 B（单成员技能）**：精确法律咨询、个案策略、量刑分析。
- **路径 C（单份文书短链）**：建案 → 起草/庭审 → 按需校验。
- **路径 D（完整案件）**：材料分析 → 研究策略 → 文书/庭审 → 成果校验。

## 技能清单

绑定 42 项技能（34 项刑事专项 + 8 项共享工具），覆盖案件材料、案件研判、法律文书、案件沟通、咨询谈案全链条。

**刑事专项（34 项）**：criminal-appeal-second-instance-drafting、criminal-arrest-review、criminal-bail-application、criminal-case-management、criminal-case-reading-notes、criminal-case-strategy-analysis、criminal-case-trial-mock-training、criminal-case-visualization、criminal-communication-guide、criminal-court-cross-examination-outline-drafting、criminal-custody-review-application-drafting、criminal-defense-speech-trial、criminal-document-delivery-check、criminal-electronic-evidence-analysis、criminal-evidence-analysis-report、criminal-evidence-request、criminal-family-guide、criminal-illegal-evidence-exclusion-drafting、criminal-interrogation-analysis、criminal-investigation-defense、criminal-juvenile-document-drafting、criminal-material-intake-gate、criminal-meeting-guide、criminal-non-prosecution、criminal-plea-negotiation、criminal-pretrial-procedure-document-drafting、criminal-prosecution-defense-opinion-drafting、criminal-quotation-proposal、criminal-sentence-calc、criminal-sentencing-analysis、criminal-simplified-fast-track-document-drafting、criminal-special-procedure-document-drafting、criminal-trial-questioning-evidence-outline、criminal-witness-appearance

**共享工具（8 项）**：fadada-laws-and-regulations-retrieval（法规检索）、fadada-legal-case-search（类案检索）、fadada-professional-contract-review（合同审查）、fadada-special-ocr（OCR 识别）、global-legal-research（全球法律研究）、lawyer-practice-risk-dynamic-screening（执业风险筛查）、pdf-generation-editing-tool（PDF 生成）、word-document-processing（Word 处理）

## MCP / 连接器依赖

- **法大大 MCP（richee-mcp-server）**：`fadada-laws-and-regulations-retrieval`（searchLawInfo）、`fadada-legal-case-search`（searchLawCase）、`fadada-professional-contract-review`（合同审查流程）依赖。需在运行环境预配置。
- **LDH MCP（LegalDataHunter）**：`global-legal-research` 依赖，用于境外、跨境与多法域法律资料检索。需在运行环境预配置。

MCP 未配置时，相关 Skill 应返回 `not_configured` 状态并按各自降级策略处理，不影响其余刑事专项能力。

## 使用示例

- 帮我分析这个刑事案件的证据链和辩护路径
- 起草一份取保候审申请书
- 制作一审质证提纲和发问提纲

## 目录结构

```
criminal-defense-expert/
├── .codebuddy-plugin/
│   └── plugin.json              # 配置文件
├── avatars/                     # 头像目录（team.png + 6 张成员头像）
├── agents/                      # Agent 定义（主理人 + 5 成员）
├── skills/                      # 共享技能（42 项）
├── settings.json                # 设置主理人
└── README.md                    # 说明文档
```

## 头像

7 张头像（1 张团队 + 6 张成员）已生成在 `avatars/` 目录下，统一漫画风格、dark grey-blue 背景（11-SecurityCompliance 分类色调）、512×512 PNG。每位成员头像配独立代表色和职业图标：

| 成员 | 代表色 | 职业图标 |
|------|--------|---------|
| 辩明远（主理人） | 金色 | 天平 |
| 甄明察（材料分析） | 青绿 | 放大镜 |
| 闫慎思（研究策略） | 蓝色 | 法典 |
| 章文达（文书起草） | 绿色 | 文书+笔 |
| 智庭锋（庭审支持） | 橙色 | 法槌 |
| 校严明（成果校验） | 红色 | 盾牌+对勾 |

团队头像（team.png）为 AI 生成原创。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

1. 将 `criminal-defense-expert/` 整个目录放到专家目录下：

```
~/.workbuddy/plugins/marketplaces/my-experts/plugins/criminal-defense-expert/
```

2. 使用 expert-manager 技能的注册脚本使其在专家中心可见：

```bash
python3 <expert-manager>/scripts/register_expert.py <expert-dir> --session-id <your-session-id>
```

3. 校验专家包：

```bash
python3 <expert-manager>/scripts/validate_expert.py <expert-dir>
```

## 打包分享

使用 expert-manager 技能的打包脚本生成 zip：

```bash
python3 <expert-manager>/scripts/package_expert.py <expert-dir>
```

## 版权

© 2026 法大大（Fadada）。本专家包内容受知识产权保护，未经许可不得复制、分发或用于商业用途。
