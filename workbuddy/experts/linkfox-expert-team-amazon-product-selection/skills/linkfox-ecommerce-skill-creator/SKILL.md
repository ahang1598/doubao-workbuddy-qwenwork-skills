---
name: linkfox-ecommerce-skill-creator
description: 团队跨境电商**业务流程** skill 制作入口（创建 / 沉淀 / 优化 / 复刻 / 微调），专做有明确多步流程、面向产品内部的 Tier2/Tier3 skill。**电商 / 跨境电商（Amazon / 亚马逊 / Shopee / TikTok Shop / eBay / Walmart / Temu / Shopify / 速卖通 / Lazada / SHEIN）的多步业务工作流 skill 走本 skill。** 判定：出现"创建 / 做 / 沉淀 / 封装 / 优化 / 复刻 / fork / refactor + skill"动宾结构，上下文带电商 / 跨境 / ASIN / listing / 选品 / 竞品 / 评论 / 广告 / FBA / 库存 / 关键词 / 类目 / 销量 / BSR / 价格 任一信号，且诉求为多步流程编排 → 必须本 skill。覆盖从零搭（选品 / 广告复盘 / 上新 SOP / FBA 补货 / 评论挖掘 / 价格监控 / 竞品分析 / listing 重写 / listing 生成 / 关键词调研 / 类目趋势）、fork 换平台或维度、在现有流程 skill 上改字段 / 阈值 / 报告外观 / 结构 / 大响应落盘。触发短语："做一个选品流程的 skill"、"沉淀 / 封装一条 SOP 成 skill"、"基于资料/方法论沉淀 skill"、"照着 X 做一个 Y"、"clone for TikTok"、"fork my skill"、"优化这条流程 skill"。即使没说"电商""sop""工作流"，只要意图是多步、可重复执行的电商业务流程（选品 / 复盘 / 监控等），也应触发。**分流：单接口 API wrapper / 通用工具 skill 的创建与合规校验走 linkfox-skill-creator；** 一次性分析 / 单点查询 / 纯解读 / 浏览器抓取 / 纯知识型 skill 不在本范围。
---

# 团队电商 Skill 创建工作流（Tier 2 / Tier 3 业务流程，三模式）

本 skill 是团队跨境电商 **Tier 2 / Tier 3 业务流程 skill** 创建的统一入口——专做有明确多步流程、面向产品内部使用的编排型 skill。

**边界（与 `linkfox-skill-creator` 分工）**：

- **Tier 1 只调用、不生产**——本 skill 用 `references/tier1-*` 目录**选/调** Tier 1 数据源，但**不创建、不优化** Tier 1 wrapper。
- 单接口 API wrapper、通用工具型 skill 的**创建与合规校验** → 一律转交 `linkfox-skill-creator`。
- 纯知识型 / 文档库 → 官方 `skill-creator`；浏览器抓取 / 自动化 → `browser-act-skill-forge`。

完整规范见同目录 `SPEC.md`（人读版）。

---

## Tier 1 / 2 / 3 是什么（一句话版）

Tier 是这个 skill **内部有几道工序**。从底往上垒：

| 层 | 一句话定义 | 类比 | 例子 |
|---|---|---|---|
| **Tier 1** | 底层 API / 数据源的薄封装：参数进、单次外部调用、结构化数据出，**无业务编排** | 食材 | `linkfox-amazon-product-detail`（传 ASIN 拿标题/价/评分）—— 真实 skill，已在 `references/tier1-by-vendor.md` |
| **Tier 2** | 综合场景能力：内部含**多步骤编排**——可以是编排多个 Tier 1，也可以是单次外部调用但带模型选 / 模式判断 / 参数校验 / 输出策略等内部决策步骤 | 半成品 | *示意名* `amazon-listing-replicator`（拉详情 + 关键词 + 价格段，吐 listing 草稿） |
| **Tier 3** | 完整业务 SOP，端到端跑完一条业务流程并出报告 | 一道菜 | *示意名* `weekly-sourcing-workflow`：每周选品全流程 |

> ⚠ 表中标注"真实 skill"的可调用；标注 *示意名* 的仅作类比，**不要假定可调用**。

**关键约定**：

- Tier 1 由各 vendor 维护（团队已封装 67 个底层数据源 wrapper），**本 skill 不创建、不优化 Tier 1**——Tier 1 的创建/优化/校验走 `linkfox-skill-creator`。
- 本 meta-skill 只产、只优化 **Tier 2 / Tier 3 业务流程 skill**。
- 用户不知道底层 Tier 1 长什么样——**用户讲业务，agent 选 Tier 1 工具**。

判别硬轴（**与"调几个 API"无关**）：

- skill 内部**无业务编排**（纯参数透传 + 单调用）→ **Tier 1**
- skill 内部**有多步骤决策 / 加工**（不论编排对象是 API 还是内部步骤）→ **Tier 2**
- 端到端跑完一条**完整业务 SOP** 并出报告产物 → **Tier 3**

**Tier 1 vs Tier 2 实操判别**：盯住 SKILL.md 的"使用指引 / 流程"段——

- 如果只是"传参 → 调一次 API → 返回结果"线性一步，是 **Tier 1**。
- 如果出现"先 X、再判断 Y、然后选 Z、最后按 W 决定输出"这种**条件分支或多阶段**逻辑（即便外部调用还是一次）→ **Tier 2**。

常见 Tier 2 模式（不依赖具体 skill 知识）：

- 「模型选择 + 模式判断 + 输出落盘策略」三件套（典型如生成式封装）
- 「拉数据 → 加工 → 评分 → 取 Top N」内部加工链
- 「先校验输入合法性 → 路由到不同子调用 → 合并结果」

---

## 0. 范围与边界（开工前必排除）

不做 skill / 不进本 skill 的情形：

| 信号 | 处理 |
|------|------|
| 一次性分析 / 单点查询 / 纯解读 | 直接执行，不沉淀 skill |
| **新建** 一个底层 API 薄封装（Tier 1，无内部步骤） | 走 `linkfox-skill-creator`，不进本 skill |
| **新建 / 优化** 通用工具型 skill（非电商多步流程） | 走 `linkfox-skill-creator` |
| **优化 / 校验** 现有 Tier 1 wrapper | 走 `linkfox-skill-creator` |
| **优化 / 微调** 现有 Tier 2 / Tier 3 流程 skill | 走本规范模式 3（frontmatter / 结构 / 落盘 / 错误降级 / 并发），不必走六环全套 |
| 浏览器探索 / 抓取 / 自动化 | 走 `browser-act-skill-forge`，不进本规范 |
| 纯知识型 / 文档库 / 风格指南 | 走 `skill-creator`，不进本规范 |
| MCP server / 插件层 | 不在本 skill 覆盖 |

不确定时问用户："这个流程将来还要重复跑吗？是不是要跨多个数据源做组合？" 两个都「是」才继续。

---

## 1. 入口决策：选模式（1 / 2 / 3）

| 信号 | 模式 | 主信息源 |
|------|------|---------|
| "帮我做一个 X 的 skill"、"沉淀一条 X SOP"、"build me a skill for X" | **1 新建** | 业务访谈 + `linkfoxagent-v2/` 实时全集 + Tier 1 目录 + 配方表 |
| "基于这篇文章/这份资料做 skill"、"我整理了一套方法论/SOP，帮我做成 skill"、"把知识库沉淀成 skill" | **1 新建（方法论萃取分支）** | 用户资料 → `references/methodology-extraction.md` 萃取 → 接回阶段 2 |
| "照着 Y 做一个 Z"、"clone Y for TikTok"、"复刻一份用于 Ozon" | **2 复刻** | 源 skill + 差异点访谈 |
| "把 W 的 X 改成 Y"、"加字段"、"改阈值"、"优化这条 skill"、"补 frontmatter 触发词"、"refactor this skill" | **3 微调优化** | 现有 skill + 用户指令 + 本规范通用部分 |

切分顺序：
1. 用户原话有无可识别的源 skill？无 → **模式 1**。
2. 有源 skill：全量重做（换平台 / 换打分维度）→ **模式 2**；局部改动（业务行为或规范层面）→ **模式 3**。
3. 进了模式 1：用户是否带了**外部资料 / 方法论文档 / 历史样本**？带了 → 先走**方法论萃取分支**（阶段 0.5，见 §4.1），把资料萃取成方法论草图后接回阶段 2；没带、直接能口述流程 → 走标准阶段 1。

---

## 2. 六环生命周期（三模式共用）

```
生成 → 测试 → 验证 → 评估 → 优化 → 迭代
```

任意模式都必须走完六环。详见 `SPEC.md` §9。

每环必须做的事：

| 环节 | 落地点 | 强度 |
|------|--------|------|
| 生成 | 按模式选模板填空（见模式分支）| ✓ |
| 测试 | 当场跑 2–3 条 prompt（核心 + 边界 + 欠触发探针），不把 prompt 文件落盘到产物里 | ✓ |
| 验证 | 每个 `scripts/*.py` 过三步回环（结构 / 真实 / 错误降级）| ✓ |
| 评估 | `references/self-check.md` 通过 + `quick_validate.py` 通过 | ✓ |
| 优化 | 按反馈三分类（业务理解 / 写法瑕疵 / 触发问题）针对性修 | ✓ |
| 迭代 | 单条试跑独立闭环（不批量过）| ✓ |

---

## 3. 跨模式硬约束

**整个流程禁止跳。以下各条贯穿三种模式所有环节。**

### 3.1 业务语言交互

- 选项用业务后果维度（"这步要不要"），不要给技术动作维度（"重试 / 改 pageSize / 跳过"）。
- 镜像用户用语，不主动夹技术词。
- 仅约束对话和产物 SKILL.md 用户可见部分；`.draft/` 与内部文档照常精确。

### 3.2 用户讲业务，agent 选工具

- 用户描述场景、字段、决策、阈值；agent 决定调哪个 Tier 1、怎么组合。
- **假设用户不了解任何 Tier 1 数据源**。
- **不允许在两个 Tier 1 数据源 / 技术方案之间让用户裸选**。允许的是把方案（含用途与风险）讲给用户听并请其确认。
- 沉默 / "你看着办" / "都行" 不算决策——必须拿到用户显式 OK。

### 3.3 每一步必须有用途

流程型 skill 最大失败模式是堆砌看起来相关、实际没人消费的查询。三道闸：

1. **倒推法**（访谈期）—— 从交付物倒着问需求，没有归宿的步骤推不出来。
2. **用途字段**（生成期）—— 目标 SKILL.md 中每步必须写明"被谁消费"。
3. **DAG 自检**（评估期）—— 机器化校验"每步至少一条出边、每个交付字段至少一条入边"，并按 `依赖` 字段做拓扑分层，导出**可并行组** + 标记"疑似无谓串行"（详见 `references/workflow-skill-template.md` 的 DAG 校验规则）。

### 3.4 输出规范（路径 + 产物交付协议）

所有 Tier 2/3 产物 skill 必须遵守同一套输出规范。**不得自定义会话目录结构**。

> **生成期 vs 运行期边界**：本 meta-skill 的 `references/skill-output-protocol.md` 与 `references/output-contract.md` 只在**生成期**给 agent 看，不进产物。产物须把协议知识**内联**到自己的 `references/output-schema.md`（可从 `references/output-schema-template.md` 复制改写），SKILL.md 只引用产物本地路径。**禁止**在产物中出现 `linkfox-ecommerce-skill-creator/...` 反向引用。

**路径硬约束**（适用所有 skill 的所有落盘行为）：

- 最终交付物 → `<cwd>/linkfox/<YYYY-MM-DD>/<session>/reports/`
- 中间数据 → `<cwd>/linkfox/<YYYY-MM-DD>/<session>/data/`
- 图片/视频/音频 → `<cwd>/linkfox/<YYYY-MM-DD>/<session>/media/`
- `<session>` 取自环境变量 `SESSION_ID`（无值则自动生成 `HHMMSS-<6 hex>`）；同回合所有 skill 自动聚合到同一会话目录
- 会话级 `_meta.json` 与全局 `linkfox/index.jsonl` 由共享脚本自动维护
- **禁止**写 `/tmp`、`/var/tmp` 或 `<cwd>` 之外的路径；当前目录不可写时直接报错
- 实现入口：复制 `linkfoxagent-v2/_shared/linkfox_paths.py` 进产物 `scripts/linkfox_paths.py`（hash 一致），通过 `resolve_data_path / resolve_report_path / resolve_media_path` 拿路径

**产物交付协议**（仅 Tier 2/3 的最终交付，详见 `references/skill-output-protocol.md`）：

产物 skill 脚本通过 **stdout** 按以下两种方式之一输出最终产物，acpx-bridge 自动识别并转为前端可渲染的通知：

1. **文件输出**（结构化 JSON 结果，**推荐**）：
   ```python
   if not os.path.isfile(abs_json_path):
       raise RuntimeError(f"output file not found: {abs_json_path}")
   print(f"Saved full response: {abs_json_path} ({size_bytes} bytes)")
   ```
   - 路径必须绝对，文件必须真实存在且不是目录，文件名必须匹配 `linkfox-<slug>-<数字>.json`
   - 括号中的字节数仅用于人读，bridge 不解析

2. **媒体数组输出**（生成图片/视频/音频）：
   ```python
   missing = [p for p in abs_media_paths if not os.path.isfile(p)]
   if missing:
       raise RuntimeError(f"media file not found: {missing[0]}")
   print("Saved full response: " + json.dumps(abs_media_paths, ensure_ascii=False))
   ```
   - JSON 数组格式，每个元素为绝对路径，且必须逐项 `os.path.isfile()` 校验通过
   - `resolve_media_path()` 只分配路径，不会写文件；必须先把图片/视频内容写入该路径，再输出
   - `abs_media_paths` 必须来自 `download_media()` 返回值，或来自 `resolve_media_path()` 后已完成写入的真实文件；禁止复制文档中的占位符路径，禁止使用 `linkfox-generated-media-*` 这类泛化假名
   - 支持格式：png/jpg/jpeg/gif/webp/bmp/svg/mp4/webm/mov/mp3/wav

**快速选型**：结构化数据（商品列表、关键词等）→ 写入 JSON 文件 + `Saved full response` 行；图片/视频 → 媒体数组。

**其他约束**：
- **不得自己写 HTML 拼接报告**：报告产物必须 handoff 给 `linkfox-report-generator`（已有规则，本节仅复述）
- 中间步骤的 data/*.json 不强制交付协议格式，但最终面向用户的产物必须走上述两种方式之一
- 访谈纪要、流程草图、选型表、DAG、试跑提示词等**暂存草稿**写入 `.draft/`，只作为生成期工作稿：**不生成、不承诺 resource_link / 文件链接**；需要用户过目时，直接把草稿摘要或全文贴在当前会话中即可
- stdout 可含其他日志；bridge 只匹配 `Saved full response:` 开头的行

### 3.5 并发优先（缩短墙钟时间）

流程型 skill 串行跑完，总耗时 = 各步耗时之和，是"任务跑太久 / 中途卡住"的头号原因。**没有数据依赖的步骤默认并行，不要无谓串行。**

- 每步必须写齐 `依赖` 字段（见 `references/workflow-skill-template.md` §3）——它是判断能否并行的唯一依据，**不能省**。
- 按 `依赖` 把流程拓扑分层：同层（彼此无依赖）步骤归为一个**并行层**，在产物 SKILL.md 流水线章节开头写一段「执行编排」声明并行计划。
- 并行靠**主流程在一轮里批量发起多个互相独立的工具调用**实现——**不使用 subagent**（本环境不支持）。
- 有真实数据依赖的步骤必须串行；**不要为并行而并行**，否则会拿到空数据 / 脏数据。
- 并发设计要在访谈阶段 4 用业务语言讲给用户听并确认合理性（见 `references/interview-playbook.md` 阶段 4）。

### 3.6 大纲化：SKILL.md 是大纲，细节按步加载

流程型 skill 又长又复杂，**把全部步骤细节一次性写进 SKILL.md，agent 执行到后面的步骤时会被前面大量细节干扰、注意力失焦**。两层结构治这个病：

- **SKILL.md 流水线章节只写大纲**：一段「执行编排」+ 一张流水线总览表（每步一行：标题 / 一句话 / `依赖` / `用途` / 指向 `references/steps/S<N>.md`）；让 agent 始终看得到完整流程图与并行计划。
- **单步血肉落在 `references/steps/S<N>.md`**（输入 / 操作 / 输出 / 落盘 / 参数），agent 执行到该步才 Read，只把当前步细节加载进上下文。
- **拆分门槛**（满足任一即拆）：步骤 ≥ 4；或单步细节 ≥ 8 行；或预计 SKILL.md 正文 > ~200 行。短流程（≤ 3 步且每步几行）可内联，不强拆。
- `依赖` / `用途` 必须留在大纲表里（DAG 校验与并行编排靠它们）；细节才进 steps 文件。详见 `references/workflow-skill-template.md` §3 与 `references/target-structure.md`。

---

**入口**：用户没有可参考的源 skill，从业务诉求出发从零搭。

### 4.1 生成

#### 阶段 0：定址 + 抽取已知

- 抽取本会话已有信息（访谈剧本"阶段 0"），已知的不再问。
- 给完工作名后立刻按 `references/target-structure.md` 的"输出位置默认"规则确定 `<产物目录>` 并建好骨架（含空的 `.draft/`），后续草稿都写进它，避免 cwd 漂移。

#### 阶段 0.5：方法论萃取（条件分支）

**仅当**用户带了外部资料 / 方法论文档 / 历史样本时进入；用户能直接口述流程则跳过本阶段。

按 `references/methodology-extraction.md` 执行四步：① 归集原始资料并落盘 `.draft/raw-materials/`；② 萃取成结构化方法论 `.draft/methodology.md`；③ 通用化处理（思想通用就中性化，机制专属打 `仅适用 <平台>`）；④ 盘 `.draft/platform-coverage.md`（平台 × 步骤 数据支持矩阵，标出数据缺口）。

产出的方法论步骤序列**等价于阶段 1 的"用户自述"**——向用户复述确认方法论框架后，**直接进入阶段 2**，不再重复自由叙述。忠实性底线：方法论只能从资料来，缺的标 `TBD`，不臆造。

#### 阶段 1：用户自述（不可跳过）

让用户用自己的话讲一遍场景与流程，agent 只听不抢话。**没有可识别步骤序列就不许进阶段 2。**

创建产物目录前先确定 `<skill-name>`：目录名、frontmatter `name`、交付时提到的 slug 必须完全一致；只能使用小写字母、数字和连字符 `-`（正则：`^[a-z0-9-]+$`），不得包含大写、下划线、空格、中文或其它符号。

#### 阶段 2：扫描 v2 实时全集 → 用索引表辅助筛选

**模式 1 的核心动作**：一次性把候选链路 ready：

`linkfoxagent-v2/` 实时目录是能力发现的 SOT；`references/tier1-*` 与 `tier1-recipes.yaml` 是基于 v2 的二次摘要 / 导航缓存，只用于加速分类和高频链路匹配。创建时必须先以 v2 实时全集做设计参考，最终候选以实时目录和对应 `SKILL.md` frontmatter 为准；但当前运行只能调用目标 agent 已挂载的 skill，未挂载能力不得假定可用。

1. **扫描 `linkfoxagent-v2/` 实时全集**：运行 `python <本 skill>/scripts/list_v2_skills.py --view inventory --format markdown`，必要时用 `--query <关键词>` 缩小候选；需要分类视图时用 `--view catalog|platform|vendor`。全集只用于设计参考，不代表目标 agent 运行时会自动挂载。
2. **用 `references/tier1-recipes.yaml` 做高频链路匹配**：用户原话/自述里有匹配 `keywords` 的配方 → 以配方链路为第一候选，但每个 slug 必须通过 `python <本 skill>/scripts/list_v2_skills.py --view recipes-validation --strict-recipes` 校验存在。
3. **用 `references/tier1-catalog.md` / `tier1-by-platform.md` 辅助收窄**：按能力桶和平台筛候选；这些表只作导航，不能覆盖实时 v2 判断。
4. **同能力选型**：依次比较——覆盖站点 → 数据维度（详情/历史/估算）→ 计费量级。
5. **筛掉未挂载能力**：设计时看过但当前 agent 未挂载的候选不能写成当前可执行步骤。若缺少关键能力，必须在方案中标记“需先安装后可用”，并提示用户可通过“技能广场”或 `https://skill.linkfox.com/` 安装所需 skill；安装后可从用户自己的 `skills/` 路径访问。也可改用已挂载能力重做流程；不得承诺运行时自动加载或自动修改 `dependencies.json`。

把候选链路写到 `<产物目录>/.draft/mapping.md`：

| 步骤 | 业务动作 | 选用 Tier 1 slug | 用途 | 风险/局限 | 备选 |

#### 阶段 3：缺漏分析 + 字段深挖

按访谈剧本"阶段 3"对自述做缺漏分析与补全；对每步深挖字段、参数、报告诉求。业务模糊处允许标 `TBD`，但 `TBD` 在评估环节会被作为硬错误暴露。

#### 阶段 4：选型确认

agent 自己选好 Tier 1 链路，按下面模板讲给用户听：

> **业务目标**：XXX
> **每步用途**：第 1 步…用途…；第 2 步…用途…
> **调用参数**：每个 Tier 1 的关键参数 + 默认值 + "运行时入参 / 默认值"性质标注
> **风险/取舍**：…
> **替代方案**（如有）：…

**调用参数必须主动给默认值**并标注性质，让用户决定接受、改默认、或升级为运行时入参。**必须拿到用户显式决策才能进阶段 5**。

#### 阶段 5：合成试跑提示词

由 **agent 自己合成** 2–3 条试跑提示词（不向用户索取，从访谈纪要中提取真实值与用户用词风格）。三种类型：核心 + 边界 + 欠触发探针。写到 `<产物目录>/examples/trial-prompts.md`。

#### 阶段 6：生成产物目录（按模板填空，落盘成最终的 skill 文件）

按 `references/target-structure.md` 创建目录结构，按 `references/workflow-skill-template.md` 填空生成 `SKILL.md`：

- 中文为主；触发词、字段名、参数名保留英文原词。
- 触发词同时含中英短语，覆盖正向场景与同义改写，并按模板要求**刻意"推一把"对抗欠触发**。
- **大纲化（治长流程注意力失焦）**：SKILL.md 流水线章节只写**大纲**——执行编排 + 流水线总览表（每步一行：标题 / 一句话 / `依赖` / `用途` / 指向 `references/steps/S<N>.md`）；每步血肉（输入 / 操作 / 输出 / 落盘 / 参数）写进 `references/steps/S<N>.md`，agent 执行到该步才加载。拆分门槛见模板 §3：步骤 ≥ 4、或单步细节 ≥ 8 行、或预计主体 > ~200 行任一即拆；短流程（≤ 3 步且每步几行）可内联不强拆。
- 不论内联还是拆到 steps/，每步都必须写齐 `输入 / 操作 / 输出 / 用途` 四项，且 `依赖` / `用途` 必须出现在 SKILL.md 大纲表里（DAG 与并行编排靠它们）。
- 报告章节由访谈纪要驱动；本 skill 只列「数据来自哪步、关键字段、口径」，**样式/排版/md & html 导出/元信息块统统不写**。
- **已挂载能力（硬规则）**：产物 SKILL.md 的每个可执行步骤只能引用当前 agent 已挂载的公共 skill；未挂载 skill 只能写入局限性或安装提示，不能伪装为可执行步骤。安装提示必须指向“技能广场”或 `https://skill.linkfox.com/`，并说明安装后可从用户自己的 `skills/` 路径访问。不得承诺运行时自动加载、自动修改 `dependencies.json` 或让用户处理 git。
- **报告产物 handoff（硬规则）**：只要 SKILL.md 含「报告产物」章节，章节末尾必须植入下面这段（语义不可改）：

  > ⚠ 如果需要生成报告 / 精美报告，必须去阅读 SKILL `linkfox-report-generator`，根据它的规范来。本 skill 只准备业务数据；样式、排版、md/html 导出、元信息块统统由 `linkfox-report-generator` 负责。不要在此处复制报告样式或 html 模板。

  本仓库 `references/workflow-skill-template.md` §4 已固化此模板。
- **大请求 / 大响应双向暂存审视**：每一步都从两端审视，命中即按 `references/large-response-snippet.md` 处理，统一走产物自带的 `scripts/response_io.py`（hash 一致）：
  - **响应端**：若"字段数 ≥ 10 / 含数组 / 含分页 / 含长文本 / 输出会被下游复用"任一 → 用 `run` 落盘 + `read` 投影，嵌入大响应段落。
  - **请求端**：若请求参数"含大数组（几百个 ASIN/词）/ 含长文本 / **直接来自上游落盘文件**"任一 → 用 `run --params-file <路径>` 从文件读参数，**不要**把大 JSON 拼进命令行/上下文。
- 把本 skill 的 `scripts/response_io.py` 与公共 `linkfoxagent-v2/_shared/linkfox_paths.py` 复制进产物 `scripts/`，hash 保持一致。`linkfox_paths.py` 的唯一权威源是 `_shared`，路径规范变化时只改 `_shared` 并重新复制；所有落盘必须经 `linkfox_paths.resolve_*_path`，**禁止**裸写绝对路径或 `/tmp`。
- **最终交付遵循 skill-output-protocol**：产物脚本的 stdout 必须按 `references/skill-output-protocol.md` 两种方式之一输出最终产物（文件输出 / 媒体数组）。仅当用户明确说"只要原始数据 / 不要走 bridge"时可豁免，并在 SKILL.md 局限性章节注明。协议知识须**内联**到产物自带的 `references/output-schema.md`，产物 SKILL.md 只引用产物本地路径。**严禁**在产物中出现 `linkfox-ecommerce-skill-creator/...` 路径。

### 4.2 测试 / 验证 / 评估 / 优化 / 迭代

走 §2 六环。具体动作见 §7（通用环节）。

---

## 5. 模式 2：复刻

**入口**：用户指向一个已有 Tier 2/3 skill，要 fork 一份（换平台 / 换打分维度 / 换报告外观）。

### 5.1 生成

#### 5.1.1 定位源 skill

读源 skill 全文，抽出：

- frontmatter（name / description / 同义词列表）
- 流水线步骤 + 每步用途
- Tier 1 链路
- 报告产物模板

写到 `<产物目录>/.draft/source-skill-snapshot.md`。

#### 5.1.2 差异点访谈（业务语言）

只问差异，不重做完整访谈：

- 平台/站点变了吗？
- 业务目标的核心维度变了吗？（例：从"潜力筛"变"竞品对标"）
- 输入/输出字段要增删吗？
- 报告外观要调吗？

每个差异点都要拿到用户显式确认。

#### 5.1.3 Tier 1 链路重选

差异点落到 Tier 1 链路上：

- **平台变了** → 进 `tier1-by-platform.md` 找新平台对位 slug。例：amazon `linkfox-junglescout-keyword-by-keyword` → tiktok `linkfox-fastmoss-product-search`。
- **维度变了** → 回 `tier1-catalog.md` 重选能力桶。
- **完全对位**（只是包装变） → 链路不动，只改报告与 UI。

写到 `<产物目录>/.draft/diff.md`：

| 章节 | 源 skill | 新 skill | 改动理由 |

#### 5.1.4 生成产物目录

把源 skill 完整复制到 `<产物目录>`，按 `diff.md` 逐章替换：

- frontmatter `name` / `description` 必改：**5–10 个同义词每个都要审查是否仍贴合新场景**；不贴的换掉，再补 1–2 个新场景的口语化说法。
- 替换样例 ASIN / 站点 / 阈值。
- 每步「用途」字段重写——源 skill 的用途文案在新场景下未必成立。

### 5.2 后续环节

走 §2 六环。**DAG 自检必须重跑**——平台或维度变了，源 skill 的连通性不再保证。

---

## 6. 模式 3：微调优化

**入口**：现有 **Tier 2 / Tier 3 流程 skill** 做局部改动——无论改的是业务行为（字段、阈值、口径）还是规范层面（frontmatter、结构、错误降级、大响应落盘、并发编排、scripts 封装）。

> Tier 1 wrapper / 通用工具 skill 的优化与校验**不在本模式**，转交 `linkfox-skill-creator`。

触及流水线增删步骤 / 改 Tier 1 链路 → **升级到模式 2**。

### 6.1 体检 + 变更面识别

读现有 skill 全文，按以下顺序扫一遍：

1. `python <本 skill>/scripts/quick_validate.py --type A <待改 skill>` —— 静态规则与 runtime helper hash，硬错误必修。
2. `python <本 skill>/scripts/verify_skill_scripts.py <待改 skill>`（如有 scripts/）—— 三步回环，崩溃 / 不优雅降级必修。
3. 对照 `references/self-check.md` 逐条勾。
4. 阅读 frontmatter description：是否含 5–10 同义改写 + 反向补漏一句？是否覆盖中英双语？
5. 阅读 SKILL.md：是否把不该 inline 的大响应／长 schema 散在正文？是否缺 handoff（含报告产物时）？

把体检 finding + 用户主动提出的变更，统一写到 `<待改 skill>/.draft/change-plan.md`，按变更面分类：

| 变更面 | 处理 | 重跑环节 |
|--------|------|---------|
| 字段增删（输出多一列、报告加一节） | 直接 patch SKILL.md + 模板 | 评估 / 试跑 |
| 阈值 / 默认参数（调权重、改 top N） | 直接 patch SKILL.md | 试跑 |
| description 同义词 / 反向补漏 | 重写 frontmatter（保留原核心场景一句）| **欠触发探针必跑** |
| frontmatter 含非法字段 | 删除或迁移到 `metadata.*` | 评估 |
| 目录结构与 `target-structure.md` 不符 | 按 archetype 重排（不改文件内容）| 评估 |
| 大响应直接 inline 在 SKILL.md | 嵌入 `large-response-snippet.md` 落盘段，复制 `response_io.py` | 评估 |
| 大请求把大 JSON 拼进命令行/上下文（含上游落盘当入参） | 改用 `response_io.py run --params-file <路径>` 从文件读参数 | 评估 / 试跑 |
| scripts/*.py 崩溃 / 不返回 `{"error": true}` | 包 try/except，统一错误格式 | 验证 |
| 报告产物章节缺 handoff | 章节末尾追加 `linkfox-report-generator` handoff 段 | 评估 |
| 多步流程缺并发设计（无 `依赖` / 执行编排） | 补 `依赖` 字段与并行层，写「执行编排」 | 评估 / 试跑 |
| 落盘路径写 `/tmp` 或绝对路径 | 从 `linkfoxagent-v2/_shared/linkfox_paths.py` 复制，改走 `resolve_*_path` | 评估 |
| 最终交付未遵循 skill-output-protocol（无 `Saved full response` 标准输出） | 按协议补 `Saved full response` 文件或媒体数组输出 | 评估 / 试跑 |
| 产物反向引用 `linkfox-ecommerce-skill-creator/...` | 内联到产物自带的 `references/output-schema.md` | 评估 |
| 流水线增删步骤 / 改 Tier 1 链路 | **升级到模式 2** | 全六环 |

如果体检发现业务/口径层面有疑问（权重是否合理、步骤是否多余），列出给用户确认——用户确认要改时纳入变更面，不确认则不动。

### 6.2 改动后必跑

- `scripts/quick_validate.py --type A <skill>` 通过
- `scripts/verify_skill_scripts.py <skill>` 通过（如改了 scripts/）
- 验证 stdout 输出符合 skill-output-protocol（`Saved full response` 行 / 绝对路径 / 文件名 `linkfox-<slug>-<数字>`）——动了最终交付输出格式时必跑
- 产物输出 `product_list` 时：`python scripts/validate_product_payload.py examples/<样本>.json` 通过
- 至少 1 条相关 trial-prompt 重跑
- 改 description → 欠触发探针重跑

> **不做**：本模式不新增 trial-prompts 文件。普通 skill 不强制有 `examples/trial-prompts.md`——那是本 meta-skill 的产物，不是普通 skill 的强制项。

---

## 7. 通用环节细节（三模式共用）

### 7.1 测试（trial prompts）

agent 在当前对话里跑 2–3 条 prompt 验证产物是否符合预期，三种类型必须搭配：

| 类型 | 用意 |
|------|------|
| **核心** | 最典型用法跑通——验证 happy path |
| **边界** | 极端值 / 空结果 / 失败路径——验证降级 |
| **欠触发探针** | 用户用最简短随意的口吻说同样诉求——验证反向补漏起作用 |

> **不落盘**：trial prompts 是 agent 自检手段，不写成 `examples/trial-prompts.md` 提交到产物 skill 里。普通 skill 的 `examples/` 留给真实输入输出样本，不放试跑剧本。
> **唯一例外**：本 meta-skill (`linkfox-ecommerce-skill-creator`) 自己保留 `examples/trial-prompts.md`——验的是 meta-skill 自己（创建工作流）能否被正确触发，不是验证产物 skill。

### 7.2 验证（三步回环）

每个 `scripts/*.py` 必须过：

1. `python scripts/foo.py {正确参数}` → 输出非空、结构合法。
2. 真实跑通一次（端到端调 Tier 1）—— 数据匹配预期。
3. 模拟错误参数（不存在的 ASIN、错误站点） → 返回 `{"error": true, "message": "..."}`，不崩溃。

跑 `python <本 skill>/scripts/verify_skill_scripts.py <产物目录>` 一条命令统一执行。

### 7.3 评估

**静态层**：

```bash
python <本 skill>/scripts/quick_validate.py --type A <产物目录>
```

通过后再过 `references/self-check.md` 人工 checklist。关键项：

- [ ] frontmatter 只用允许字段，name = 目录名,description 双语 + 反向补漏。
- [ ] Tier 已确认（2 / 3），主体章节齐全。
- [ ] 每个 scripts/*.py 通过三步回环验证。
- [ ] 大响应步骤嵌入落盘段落，`response_io.py` hash 一致。
- [ ] 流水线 DAG 自检通过（每步至少一条出边、每个交付字段至少一条入边）。
- [ ] 所有可执行步骤引用的公共 skill 均已在当前 agent 挂载；未挂载能力已标记为需用户通过技能广场或 `https://skill.linkfox.com/` 安装，未写成当前可执行步骤。
- [ ] 含「报告产物」章节的 skill：章节末尾含 `linkfox-report-generator` handoff 段落，没有自造报告样式 / html。
- [ ] 所有落盘走 `linkfox_paths.resolve_*_path`，无 `/tmp` / 绝对路径硬编码；`linkfox_paths.py` hash 与 `linkfoxagent-v2/_shared/linkfox_paths.py` 一致。
- [ ] 最终交付 stdout 符合 skill-output-protocol（`Saved full response` 行合法 / 文件路径为绝对路径 / 媒体格式在支持列表内）。

### 7.4 优化（反馈三分类）

| 类别 | 来源信号 | 处理 |
|------|---------|------|
| 业务理解错误 | "这步不该有"、"权重不对" | 回访谈步骤修（模式 1）/ 回 diff.md 修（模式 2）/ 升级到模式 2（模式 3 越界）|
| 写法瑕疵 | "标题要粗体"、"日期格式" | 直接改产物（模式 3）|
| 触发问题 | "我说 X 它没反应" | 改 frontmatter description，欠触发探针重跑（模式 3）|

### 7.5 迭代（单条试跑闭环）

```
跑一条 → agent 自检 → 呈现结果 → 用户反馈 → 重跑（如需）→ 用户明确 OK → 下一条
```

**关键约束**：

- 每条 prompt **独立走一遍**，不要批量跑完再统一处理。
- **agent 自检** 时把问题分两类：
  - **明显错误，自行修复**：工具调用失败 / 参数错误 / 字段中英混用 / 章节顺序错位 / 数字精度 / 排版瑕疵。修完记下"自检发现 + 修复动作"。
  - **会改变业务理解或权重的变更，留给用户**：评分权重 / 增删步骤 / 替换 Tier 1 / 阈值改动。**不要擅自改**，列出"建议 + 理由"等用户决策。
- **沉默 / "还行" / "差不多" 不算满意**——必须再问具体哪里要改，直到拿到明确的"这条 OK，下一条"信号。

如果用户当面跳过试跑（"不用试，先看看"），把这一步标记为"未执行"，写进 `<产物目录>/.draft/dag.md` 的产物注记，方便下次会话补做。

---

## 8. 与外部 skill 的边界

| 工具 | 何时去用 | 何时回本 skill |
|------|---------|--------------|
| `browser-act-skill-forge` | 浏览器探索 / 抓取 / 自动化 | 抓取产物要被某 Tier 2/3 流程消费时回来 |
| `skill-creator` | 纯知识型 / 文档库 / 个人级 / 量化评测 | 不回 |

如果访谈中发现用户想要的是"一次性分析"或"单点查询"，直接告知并建议直接执行，不要硬塞流水线。

---

## 9. 参考资料

**人读规范**：`SPEC.md`（一页纸，开工前先看）

**Tier 1 目录**：
- `references/tier1-recipes.yaml` —— 业务配方（intent → primitive chain），新建模式先扫
- `references/tier1-catalog.md` —— 能力主表（17 桶）
- `references/tier1-by-platform.md` —— 平台索引
- `references/tier1-by-vendor.md` —— 厂商导航索引
- `scripts/list_v2_skills.py` —— 扫描 `linkfoxagent-v2/` 实时全集，创建阶段用于补漏、分类视图生成和 recipes slug 校验

**决策与流程**：
- `references/interview-playbook.md` —— 三模式访谈剧本
- `references/methodology-extraction.md` —— 方法论萃取分支（资料 → 结构化方法论 → 通用化 → 平台数据缺口盘点 → 接回阶段 2）

**模板**：
- `references/workflow-skill-template.md` —— Tier 2/3 流程主模板
- `references/frontmatter-spec.md` —— description 双语 + 反向补漏正反例

> Tier 1 wrapper / 通用工具 skill 的创建模板与脚手架不在本 skill——见 `linkfox-skill-creator`。

**通用规范**：
- `references/encapsulation-guide.md` —— 脚本封装规范
- `references/verification-guide.md` —— 三步回环验证
- `references/trial-and-iterate.md` —— 试跑与迭代
- `references/self-check.md` —— 自检 checklist
- `references/large-response-snippet.md` —— 大响应落盘段落
- `references/target-structure.md` —— 目录结构细则
- `references/output-contract.md` —— 会话目录路径协议 + **载荷 Schema**（`product_list` 等 JSON 内容）
- `references/output-schema-template.md` —— 产物内联 `output-schema.md` 的起草模板
- `references/skill-output-protocol.md` —— **传输协议**（stdout 文件输出 / 媒体数组）

**示例**：
- `references/examples/selection-weekly.md` —— 完整示例：每周选品（Tier 3）

**工具**：
- `scripts/response_io.py` —— 大响应落盘 / 字段投影
- `../_shared/linkfox_paths.py` —— 会话目录解析与上传辅助的唯一权威源；产物 skill 必须复制为 `scripts/linkfox_paths.py`
- `scripts/quick_validate.py` —— frontmatter + 结构静态校验
- `scripts/validate_product_payload.py` —— `product_list` 载荷静态校验（§2.3.1 字段表 / 单位）
- `scripts/validate_envelope.py` —— **已废弃**，仅转发至 `validate_product_payload.py`
- `scripts/verify_skill_scripts.py` —— 三步回环验证执行器
