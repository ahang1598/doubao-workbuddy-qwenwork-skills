# 统一审查报告 · credit-due-diligence-report（对公贷前尽调专家团）

> 审查工具：unified-reviewer（形状层脚本 + 金融敏感词扫描 + LLM 语义判断）
> 审查日期：2026-08-26
> 包类型：expert / team（专家团，5 名 Agent：1 主理人 + 4 成员）

---

## 一、总览

| 级别 | 数量 | 结论 |
|------|------|------|
| 🔴 BLOCKER | **0** | ✅ 无阻断项 |
| 🟡 WARNING | **0** | ✅ 无警告项 |
| 🔵 SUGGESTION | **6** | 建议优化（不阻断） |
| 金融敏感词 | 0 hits | ✅ 通过 |

**最终判定：✅ 通过（PASS），可上架/交付。**

---

## 二、形状层检查（脚本自动完成）

| 检查项 | 结果 |
|--------|------|
| plugin.json 结构 / 字段完整性 | ✅ 通过 |
| 一致性约束（agentName ↔ agents 文件 ↔ settings.json ↔ members[].id ↔ teamInfo.memberAgents） | ✅ 全部一致 |
| 主理人命名（`dd-team-lead`，非通用 `team-lead`） | ✅ 已加前缀 |
| skills[] 路径存在且含 SKILL.md | ✅ 通过 |
| 头像（6 张，全部 512×512 RGBA PNG） | ✅ 通过 |
| frontmatter 无 `tools` 字段（工具由系统分配） | ✅ 通过 |
| 金融敏感词黑名单扫描 | ✅ 0 命中（无承诺收益/操纵市场/非法集资/洗钱等红线词） |

---

## 三、语义判断（LLM 逐项结论）

### AI-B01 · 主理人团队协作铁律（required）→ ✅ PASS

| 必备要素 | 位置 | 结果 |
|----------|------|------|
| 「团队协作机制（铁律）」章节 | dd-team-lead.md §二 | ✅ |
| 4 条协作铁律（建立团队/调度成员/消息中转/成员结论为准） | §三 | ✅ 全齐 |
| 5 条红线（禁跳 TeamCreate/禁代写/禁跳阶段/禁直连/禁 spawn 自己） | §四 | ✅ 全齐 |
| 协作规则（TeamCreate→Agent spawn→SendMessage 回传 + name 参数） | §五 | ✅ 含 `name` 参数 |

### AI-B07 · 成员 Prompt 完整性（required）→ ✅ PASS（4/4）

| 成员 | 角色定义 | 擅长领域(3-5) | 分析框架 | 数据获取 | 输出模板 | SendMessage 回传 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| data-collector | ✅ | ✅(5) | ✅(11项清单) | ✅ | ✅ | ✅ |
| financial-analyst | ✅ | ✅(5) | ✅ | ✅ | ✅ | ✅ |
| report-writer | ✅ | ✅(5) | ✅ | ✅ | ✅ | ✅ |
| compliance-officer | ✅ | ✅(5) | ✅ | ✅ | ✅ | ✅ |

### AI-C07 · frontmatter 完整性（required）→ ✅ PASS

5 个 Agent 的 frontmatter 均含 `displayName` + `profession` 双语字段。

### AI-E01 · 金融合规（required）→ ✅ PASS（附说明）

| 检查项 | 结果 |
|--------|------|
| defaultInitPrompt 无「能不能买/该买吗/推荐」等决策措辞 | ✅ |
| displayDescription / description 无投资建议、买卖信号、操作路线图暗示 | ✅ |
| 数据来源披露要求 | ✅（报告抬头强制「数据来源声明」+ 每个数字标注来源） |
| 免责声明 | ✅ 域内适配 |

> **说明**：本包属**对公信贷风控域**（贷前尽调），并非「股票/基金/投资分析」专家团，故 CODEBUDDY.md §十八 的四要素投资免责声明（不构成投资建议/不构成个股推荐）**不适用**。包内已具备域内等价的合规闭环：
> - 「数据来源声明」＝ 公开信息要素 ✅
> - 「AI 辅助生成，需信贷员人工核实后使用」＝ AI 生成要素 ✅
> - 「严禁编造数据」「💼 待行内补充」「不替代行内正式尽调」＝ 更严格的信贷风控约束 ✅

### AI-C08 · 平台能力声明（recommended）→ ✅ PASS

未发现「本地 AI / 本地模型 / 离线运行 / 不联网 / 零数据外传」等与平台云端推理方式不符的承诺。数据源（企查查/天眼查/信用中国等）均为真实的公开网络数据源，非本地运行声明。

### AI-G01 · 安全与通用性（recommended）→ ✅ PASS

- 真实凭据/密钥硬编码：无
- 越权读取/数据外传/危险命令：无（包内无 scripts/bin）
- 内网域名 / 个人路径 / 平台路径残留 / CDN @latest：均无
- 数据源全部为公开通用源，可移植性好

### AI-Q01 · 深度质量评审（recommended）→ ✅ 良好（6 项 SUGGESTION）

11 维度逐项评估结果见下节 SUGGESTION 清单。

---

## 四、SUGGESTION 清单（6 条，均不阻断）

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| S1 | 建议 | agents/dd-team-lead.md | 主理人缺「成员能力清单 + 典型问法/单 agent 直调路由表」（规范 §4.4.1 / §4.4.3） | 在成员表中补充「典型问法」列，帮助主理人判断什么问题该调谁 |
| S2 | 建议 | agents/dd-team-lead.md | 缺「预设 Workflow」的 Phase 触发条件 + 输入输出依赖标注（§4.4.2） | 将 §五标准流程升级为带触发条件/Phase 串并行/输入输出依赖的 Workflow |
| S3 | 建议 | skills/*/assets/demo-samples/ 3 份 demo | demo 末尾仅有「Demo 演示，不替代行内正式贷前尽调」，缺与 Agent prompt 一致的「AI 辅助生成，需信贷员人工核实后使用」免责落款 | 为 3 份 demo 统一补上免责落款，与 report-writer/compliance-officer 的输出规范对齐 |
| S4 | 建议 | plugin.json | displayDescription.zh 约 55 字，略超规范建议的 40–50 字区间 | 精简中文描述至 40–50 字 |
| S5 | 建议 | 全部 Agent + SKILL.md | （可选加固）报告第十二章含「建议授信要素」等授信决策倾向内容 | 可在免责声明中追加「不构成授信审批结论」字样，进一步隔离决策责任（当前「人工核实」已基本覆盖） |
| S6 | 建议 | 包根目录 | 缺 README.md（规范推荐项） | 补充 README 说明团队分工、使用方式、与 `credit-pre-loan-process` 技能的边界 |

---

## 五、附注：审查规范自身的一处不一致

审查依据两份规范在「子任务命名」上存在冲突：
- `WorkBuddy专家开发规范.md` §5.2.1：`name` 参数传**中文角色名**
- `CODEBUDDY.md` §4.4：`name` 参数传**英文 Agent ID（MD 文件名）**，明确「禁止使用中文名或自创名称」

本包在 dd-team-lead.md §五采用英文 Agent ID（`name: "data-collector"`），符合 CODEBUDDY.md §4.4（更具体、且能确保 UI 通过 `members[].id` 精确匹配 displayName），**判定合规**。建议后续统一两份规范表述，消除歧义。

---

## 六、结论

**该专家团包质量高、结构完整、合规意识强，无任何 BLOCKER 或 WARNING，可直接交付。**

核心亮点：
1. 主理人 4 铁律 + 5 红线 + 标准流程完整写入，防「主理人代写/跳流程」设计到位；
2. 四成员职责边界清晰、输出模板结构化、均含 SendMessage 回传要求；
3. 信贷合规闭环完备（数据来源声明 + 严禁编造 + 待行内补充 + 免责声明）；
4. 模板/参考/demo 三层分离，可移植性好，无内网依赖、无凭据硬编码。

6 条 SUGGESTION 均为优化项，可在下一版迭代中补齐（尤其 S1/S2/S3）。

---

## 七、v1.1.0 整体优化记录（2026-08-26）

在 6 条 SUGGESTION 全部修复（v1.0.0 当日完成）的基础上，对照 expert-manager 规范（plugin-json-spec / team-spec）做全包深扫，又发现并修复以下问题，版本升至 **1.1.0**：

| # | 位置 | 问题 | 处理 |
|---|------|------|------|
| O1 | plugin.json | **Team 型 profession 与 displayName 不一致**（profession.zh="对公信贷尽调项目组" ≠ displayName.zh="对公贷前尽调专家团"），违反 plugin-json-spec「Team 型须与 displayName 一致」 | profession 中英双语对齐 displayName |
| O2 | plugin.json | 顶层 description 为 5 句英文长段，超出「英文一句话描述」规范 | 压缩为一句话（保留核心信息：5 Agent、12 章+6 附表、四角色、严禁编造） |
| O3 | rules/*.md §一.1 | SendMessage recipient 写作 `main/team-lead`，与全包英文 Agent ID 口径（CODEBUDDY §4.4）不一致，存在 spawn 寻址失败风险 | 统一为 `dd-team-lead` |
| O4 | rules/*.md §二.3 | 免责声明仍是旧版短句，S5 修复时遗漏 rules 文件 | 升级为完整版（含「不构成授信审批结论，最终以行内有权审批机构意见为准」），与 5 个 Agent + 3 份 demo 完全对齐 |
| O5 | agents/dd-team-lead.md §五 | 缺 team-spec 协作规则两点：`subagent_type` 与 `name` 同传 Agent ID；每阶段完成向用户通报进度 | 已补入 §五，并指向 §九 Workflow 表避免双源维护 |
| O6 | README.md | S6 原始建议中的「与 credit-pre-loan-process 技能的边界」未落地 | 新增「五、与其他技能的边界」章节，目录结构补 REVIEW-REPORT 说明 |

**回归校验**：自研一致性脚本 41 项全部 PASS（profession=displayName、描述 40-50 字、tags/quickPrompts=3、defaultInitPrompt=quickPrompts[0]、agentName↔agents↔settings↔members↔teamInfo 全链一致、资源文件齐备、frontmatter 无 tools、rules 口径、版本 1.1.0）。

**遗留可选项（未改动，待用户决策）**：team-spec 建议成员 `name` 采用谐音花名风格（如「齐活林」），当前成员 name 与 displayName 同为职能名（信息核查员等）。改名会改变 UI 展示身份，故保留现状。

---

## 八、v1.1.1 命名规范修复记录（2026-08-26）

针对上轮「遗留可选项（花名）」的决策反转：用户复核后确认**职能名 displayName 过不了审**（CODEBUDDY §9.1 花名规范：Team 型成员 displayName.zh 禁止纯职能词、禁止与 profession 重复；§9.2 主理人 profession 禁止通用概念词），本轮按 expert-reviewer 工具包复核并修复，版本升至 **1.1.1**：

| # | 成员（Agent ID 不变） | displayName.zh 变更 | displayName.en 变更 | 巧思 |
|---|----------------------|--------------------|--------------------|------|
| N1 | dd-team-lead | 尽调总指挥 → **陈实** | → Chen | 查实/诚实——尽调之本在于核实事实 |
| N2 | data-collector | 信息核查员 → **罗辑** | → Luo | 逻辑——信息核查讲究严谨逻辑 |
| N3 | financial-analyst | 财务分析师 → **钱明** | → Qian | 钱要查明白——财务分析明察秋毫 |
| N4 | report-writer | 报告撰写员 → **毕成** | → Bi | 必成——报告必然成稿 |
| N5 | compliance-officer | 合规审查员 → **何桂** | → He | 谐音「合规」——合规审查员 |
| N6 | dd-team-lead profession | 调度编排 → **尽调总监**（en: DD Director） | — | §9.2 主理人 profession 须体现业务定位，非通用 title |

**同步范围**：plugin.json `members[].name/displayName`、5 个 agents/*.md frontmatter `displayName`、README 团队成员表；**Agent ID / 文件名 / frontmatter name / settings.json / teamInfo 均未动**（一致性约束不受影响）。

**回归校验**：
- normalize.py：0 修改 0 警告；review.py：structure_blockers=0；
- 一致性终检 10 项全 ✅（agentName↔settings↔members↔agents 文件名↔frontmatter name、无 tools、5 名成员 displayName ≠ profession 零重复）；
- version 同步 1.1.1（plugin.json + SKILL.md）。
