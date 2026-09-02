# 知识产权专家团 (IP Expert Team)

> 知识产权 Agent-Team，覆盖商标注册、商标维权、商标诉讼、专利分析与著作权侵权分析全流程。

## 专家类型

Team 型（专家团），1 名主理人 + 5 名专业成员。

## 调度机制（技能调度型）

本专家团采用**技能调度型协作**：成员角色文件（`agents/*.md`）定义各成员的人格、能力边界、工作流与输出规范；专业产出由主理人**加载成员绑定技能**（`skills/` 目录）执行完成，**不依赖 Agent 工具 spawn 子进程**。

> **背景说明**：运行时 Agent spawn 仅认内置类型（general-purpose / Explore / Plan 等）与用户自定义 agents 目录（`~/.workbuddy/agents/`、`.codebuddy/agents/`）；插件 `agents/` 目录未注册为可 spawn 的 agent 类型，直接以成员 ID spawn 会报 `Task agent <id> is not available`。因此本包将成员声明为技能调度型——成员绑定技能随包分发、可独立加载，保证包自包含、跨环境可运行。

调度规则：按下文「团队成员」表的"绑定技能"列，主理人加载对应技能并按成员角色工作流执行；成员之间不直连，信息流经主理人中转。

## 团队成员

| 角色 | Agent ID | 花名 | 职业头衔 | 绑定技能 |
|------|----------|------|----------|----------|
| 主理人 | ip-team-lead | 权秉衡 | 首席知识产权调度官 | — |
| 成员 | trademark-registration-advisor | 申可成 | 商标注册申请顾问 | trademark-assistant |
| 成员 | trademark-enforcement-strategist | 策守真 | 商标维权策略师 | tm-infringement-strategy, trademark-infringement-compensation-calculation, trademark-infringement-evidence-checklist-generator |
| 成员 | trademark-litigation-specialist | 质庭锋 | 商标诉讼庭审专员 | tm-infringement-cross-exam, tm-infringement-trial-prep |
| 成员 | patent-analysis-specialist | 甄利达 | 专利分析分析师 | patent-analysis |
| 成员 | copyright-analysis-specialist | 著鉴清 | 著作权侵权分析师 | copyright-substantial-similarity-analysis |

## 技能清单

| 技能目录 | 说明 |
|---------|------|
| copyright-substantial-similarity-analysis | 著作权侵权"实质性相似+接触可能性"分析 |
| patent-analysis | 专利分析（7类场景） |
| tm-infringement-cross-exam | 商标侵权质证提纲 |
| tm-infringement-strategy | 商标侵权诉讼策略制定 |
| tm-infringement-trial-prep | 商标侵权庭审提纲 |
| trademark-assistant | 商标申请助手（类别规划+可注册性初筛+申请材料） |
| trademark-infringement-compensation-calculation | 商标侵权赔偿测算 |
| trademark-infringement-evidence-checklist-generator | 商标侵权证据清单生成 |

## SOP 工作流

> 以下路径中"调用/调度成员"均指：**加载该成员绑定技能并按成员角色工作流执行**（技能 identifier 见上表"绑定技能"列），由主理人负责编排、执行与汇编。

### 路径 A：即时回应（无子调用）
能力说明、材料清单、任务路由等，主理人直接回答。

### 路径 B：单技能快速咨询
单一领域的精确咨询，加载对应成员绑定技能执行。

### 路径 C：商标侵权诉讼短链
Phase 1: trademark-enforcement-strategist（加载 `tm-infringement-strategy` + `trademark-infringement-compensation-calculation` + `trademark-infringement-evidence-checklist-generator`）→ Phase 2: trademark-litigation-specialist（加载 `tm-infringement-cross-exam` + `tm-infringement-trial-prep`）

### 路径 D：完整案件
Phase 1（并行）: 按领域加载对应成员绑定技能执行各专业分析 → Phase 2（串行）: 商标诉讼场景进入庭审准备 → 主理人汇编

## 内置 MCP / 连接器依赖

本专家团运行时依赖内置 MCP 服务「法大大睿契」（`richee-mcp-server`），声明方式为：

- `plugin.json` → `dependencies.mcpServers` 指向插件根目录的 `.mcp.json`（推荐方式一）；
- `.mcp.json` 中声明 `richee-mcp-server`（streamableHttp，`https://claw.richee.cn/claw-api/mcp/workbuddy`），并附 `x-workbuddy` 元信息（displayName / description）。

用户召唤本专家团前，WorkBuddy 会弹出内联引导卡片，引导完成「法大大睿契」连接后才进入对话；连接后统一在「连接器 → 自定义连接器」中管理。

## 头像

头像位于 `avatars/` 目录，已通过 ImageGen 生成完毕，规格 512×512 PNG，全部 ≤500KB。各角色对应文件如下：

| 文件 | 角色 |
|------|------|
| `team.png` | 团队头像 |
| `ip-team-lead.png` | 权秉衡（主理人） |
| `trademark-registration-advisor.png` | 申可成 |
| `trademark-enforcement-strategist.png` | 策守真 |
| `trademark-litigation-specialist.png` | 质庭锋 |
| `patent-analysis-specialist.png` | 甄利达 |
| `copyright-analysis-specialist.png` | 著鉴清 |

原始生成提示词见 `avatars/avatar-prompts.md`，可手动替换（PNG/JPG，512×512，≤500KB）。

## 免责声明

本专家团产物由 AI 辅助生成，仅供参考，不构成正式法律意见，不能替代具有执业资格的律师。

## 作者

RicheeAI (legal@richeeai.com)
