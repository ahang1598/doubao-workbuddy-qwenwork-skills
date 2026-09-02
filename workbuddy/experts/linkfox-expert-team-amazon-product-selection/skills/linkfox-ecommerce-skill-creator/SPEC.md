# 团队电商 Skill 撰写规范（人读版）

> 适用范围：电商业务 + 团队内部 + Claude Code skill。
> 配套机器化指引在 `SKILL.md` + `references/`，本文是供作者快速对齐的一页纸。

---

## 1. 定位与边界

**本规范只产、只优化 Tier 2 / Tier 3 业务流程 skill。Tier 1 wrapper / 通用工具 skill 的创建、优化、校验一律走 `linkfox-skill-creator`；本 skill 只调用 Tier 1，不生产。**

**Tier 一句话版**：Tier 是这个 skill **内部有几道工序**。Tier 1 = 薄封装无编排；Tier 2 = 多步骤编排；Tier 3 = 完整业务 SOP。

| 层 | 一句话定义 | 类比 | 例子 |
|---|---|---|---|
| **Tier 1** | 底层 API / 数据源薄封装，无业务编排 | 食材 | `linkfox-amazon-product-detail`（真实） |
| **Tier 2** | 综合场景能力，内部多步骤编排（不限于 API 编排） | 半成品 | *示意名* `amazon-listing-replicator` |
| **Tier 3** | 端到端业务 SOP | 一道菜 | *示意名* `weekly-sourcing-workflow` |

> ⚠ 标注 *示意名* 的仅作类比，**不要假定可调用**。

**Tier 1 vs Tier 2 实操判别**：纯参数透传 + 单调用 → Tier 1；含条件分支 / 多阶段加工 / 模型选 / 输出策略等内部决策（即便外部调用一次）→ Tier 2。

层次叠放：

```
Tier 0  本 skill（撰写标准 + 创建工作流）
Tier 3  复刻型业务 SOP（"周度选品"）
Tier 2  跨数据源组合能力（"listing-rewrite-amazon"、"kw-matrix-amazon"）
Tier 1  Linkfox 封装的 80+ 数据源 wrapper（linkfox-amazon-product-detail 等）
```

不做 skill 的情形（写之前先排除）：

- 一次性分析 / 单点解读 / 咨询式问答 → 直接执行。
- **新建** 无内部编排的薄封装 → 这是 Tier 1，由 vendor 维护，不进本规范创建流程。
- 优化已有 **Tier 2/3 流程 skill** → 走本规范模式 3（frontmatter / 结构 / 落盘 / 错误降级 / 并发），不必走六环全套。优化 Tier 1 wrapper / 通用工具 skill → 走 `linkfox-skill-creator`。
- 浏览器探索/抓取 → 走 `browser-act-skill-forge`，不进本规范。
- MCP / Anthropic 插件 → 不在本规范覆盖。

---

## 2. 三种操作模式（任选其一，共用同一套生命周期）

```
用户的诉求
│
├─ 业务从零搭：选品 / 复盘 / 监控 …               → 模式 1：新建
│    └─ 带了资料/方法论文档/历史样本                → 模式 1·方法论萃取分支
│
├─ 已有 Tier 2/3 skill 但要 fork（换平台/换打分）  → 模式 2：复刻
│
└─ 现有 skill 局部改动（业务行为或规范层面）        → 模式 3：微调优化
```

| 模式 | 入口信号 | 主信息源 | 主要难点 |
|------|---------|---------|---------|
| 1 新建 | "帮我做一个 X 的 skill" | 业务访谈 + `linkfoxagent-v2/` 实时全集 + Tier 1 目录 + 配方表 | 选对原料链路 |
| 1·方法论萃取 | "基于这份资料/方法论做 skill"、"把 SOP/知识库沉淀成 skill" | 用户资料 → 萃取方法论 → 接回阶段 2 | 通用化处理 + 不臆造 + 平台数据缺口盘点 |
| 2 复刻 | "照着 Y 做一个 Z" | 源 skill + 差异点 | 识别哪些固定 / 哪些要变 |
| 3 微调优化 | "把 W 的 X 改成 Y" / "优化这条 skill" / "补 frontmatter 触发词" | 现有 skill + 用户指令 + 本规范通用部分 | 变更面识别 + 改动面控制 |

模式 3 只作用于 **Tier 2 / Tier 3 流程 skill**；Tier 1 wrapper / 通用工具 skill 的规范层打磨走 `linkfox-skill-creator`。

模式入口决策树与访谈剧本见 `references/interview-playbook.md`；资料驱动的方法论萃取分支见 `references/methodology-extraction.md`。

---

## 3. 一个 skill 的目录形态

```
<skill-name>/
├── SKILL.md         # 必需。frontmatter + 主体说明
├── references/      # 可选。延迟加载的子文档、模板、长说明
├── scripts/         # 可选。可执行脚本（Python 主导）
└── examples/        # 可选。试跑提示词、样例输入输出
```

约束：

- `<skill-name>` = 目录名 = frontmatter 的 `name`，三者必须完全一致；只能使用小写字母、数字和连字符 `-`（正则：`^[a-z0-9-]+$`），不得包含大写、下划线、空格、中文或其它符号。
- Tier 2 命名建议带平台后缀（`listing-rewrite-amazon`、`kw-matrix-amazon`）。
- Tier 3 复刻型用业务名（`weekly-selection-amazon`），中文别名进 frontmatter description。

---

## 4. 能力发现：v2 实时全集 + 导航索引（新建/复刻必读）

`linkfoxagent-v2/` 实时目录是能力发现 SOT。`references/tier1-*` 与 `tier1-recipes.yaml` 是基于 v2 的二次摘要 / 导航缓存，用于分类、平台收窄和高频链路匹配；它们可能滞后，不能覆盖实时目录和 `SKILL.md` frontmatter。创建阶段必须先扫描 v2 实时全集作为设计参考，再用导航索引辅助筛选；但当前运行只能调用目标 agent 已挂载的 skill，未挂载能力不得假定可用。

```bash
python scripts/list_v2_skills.py --view inventory --format markdown
python scripts/list_v2_skills.py --view catalog --query amazon --format markdown
python scripts/list_v2_skills.py --view recipes-validation --strict-recipes
```

| 文件 | 索引轴 | 何时进 |
|------|-------|------|
| `references/tier1-recipes.yaml` | **业务配方**（intent → primitive chain） | 高频链路快捷匹配 |
| `references/tier1-catalog.md` | **能力主表**（17 桶：详情/搜索/关键词/评论/选品 …） | 按能力桶辅助收窄 |
| `references/tier1-by-platform.md` | **按平台收窄** | 用户已点名平台 |
| `references/tier1-by-vendor.md` | **按数据源索引**（22 家厂商） | 用户点名数据源 |

**硬规则**：

- 先扫 `linkfoxagent-v2/` 实时全集，获得当前可用 skill 池。
- 用配方表匹配高频 chain，但每个 slug 必须在实时全集中存在。
- 用能力桶 / 平台索引辅助收窄；导航索引不能覆盖实时全集和对应 `SKILL.md` frontmatter。
- 同能力多个候选时，依次比较：覆盖站点 → 数据维度（详情/历史/估算）→ 计费量级。
- **禁止让用户在两个 Tier 1 数据源之间裸选**。agent 必须自己定方案后讲给用户确认。
- 用户讲业务，agent 选工具——所有「用户对话」都用业务后果维度，不用技术动作维度。
- 最终流程只能承诺调用当前 agent 已挂载的公共 skill；设计时看过但未挂载的候选只能作为安装提示，不能写成当前可执行步骤。

---

## 5. Frontmatter 必须做对（最容易踩坑）

```yaml
---
name: <skill-name，与目录名一致；只能用小写字母、数字和 '-'>
description: <见下>
license: <可选>
allowed-tools: <可选>
metadata: <可选>
compatibility: <可选，≤ 500 字符>
---
```

**只允许这 6 个字段**，其它字段会被 validator 报错。

`description` 三件套（缺一不可）：

1. **第一句**：用户最自然语言写的核心场景（"做一个周度选品流程的 skill"）。
2. **5–10 个同义改写**：覆盖中英两种说法（"sourcing weekly"、"产品周复盘"、"competitor monitoring"），写在同一段里。
3. **反向补漏一句**：刻意推一把对抗欠触发，类似"即使用户只说'帮我每周看看竞品'也应触发"或 "even if the user phrases it as casual monitoring"。

约束：单段、单句结构、≤ 1024 字符、禁用 `<` `>`。

正反例见 `references/frontmatter-spec.md`。

---

## 6. SKILL.md 主体必须包含什么

| 章节 | Tier 2 组合型 | Tier 3 复刻型 |
|------|--------------|--------------|
| 适用与不适用 | ✓ | ✓ |
| 一次性参数（站点/类目/阈值） | ✓ | ✓ |
| 流水线步骤（输入·操作·输出·**用途**） | ✓ | ✓ |
| 调用的 Tier 1 链路（按执行顺序） | ✓ | ✓ |
| 输出 schema | ✓ | ✓ |
| 报告产物模板 | 可选 | ✓ |
| 自检 checklist | ✓ | ✓ |
| 局限性 | ✓ | ✓ |

**「用途」字段是硬约束**：每个步骤都要写明输出"被谁消费"——要么进下游步骤，要么进报告章节。没有归宿的步骤删掉。

**报告产物 handoff 是硬约束**：任何含「报告产物」章节的 skill，**必须**在该章节末尾植入一段 handoff，明示由 `linkfox-report-generator` 接管样式 / 排版 / md & html 导出。本 skill 只准备业务数据，不复制报告样式或 html 模板。模板见 `references/workflow-skill-template.md` §4。

**未挂载能力处理是硬约束**：创建 / 复刻 / 优化 Tier 2/3 skill 时，如果流程需要的公共 skill 当前 agent 未挂载，不能把该步骤写成当前可执行能力。必须在方案中标记为“需先安装后可用”，并提示用户可通过“技能广场”或 `https://skill.linkfox.com/` 安装所需 skill；安装后可从用户自己的 `skills/` 路径访问。也可改用已挂载能力重做流程；不得承诺运行时自动加载、自动修改 `dependencies.json` 或让用户处理 git。

主模板：`references/workflow-skill-template.md`。Tier 1 wrapper / 通用工具 skill 的创建走 `linkfox-skill-creator`，不在本规范。

---

## 7. 脚本封装与验证

scripts/ 内每个 .py 文件代表一个原子能力，命名 kebab-case，与 SKILL.md 步骤名对齐。

**封装方式**：

- Python 直接干活（HTTP 调用 Tier 1、数据处理、落盘）—— 主流。
- Python emit JS 字符串供浏览器 eval —— 走 browser-act-skill-forge，不在本规范。

**强制：每个 scripts/*.py 必须做三步回环验证**：

1. `python scripts/foo.py {正确参数}` → 输出非空、结构合法。
2. 真实跑通一次（端到端调 Tier 1）—— 数据匹配预期。
3. 模拟错误参数（不存在的 ASIN、错误站点） → 返回 `{error: true, message: ...}`，不崩溃。

跑 `python scripts/verify_skill_scripts.py <skill 目录>` 一条命令统一执行。

详见 `references/verification-guide.md`。

---

## 8. 大响应必须落盘

什么时候**强制落盘**：

- 字段数 ≥ 10 / 含数组返回 / 含分页 / 含长文本（描述、评论、HTML、时间序列）
- 输出会被下游步骤复用（流程型的跨步数据流）

满足任一条 → 在该步骤说明里嵌入落盘段落，统一通过产物自带的 `scripts/response_io.py`（与本仓库 hash 一致，validator 校验）。

模板：`references/large-response-snippet.md`。

---

## 9. 生命周期：六个环节（三模式共用）

```
生成 → 测试 → 验证 → 评估 → 优化 → 迭代
```

### 9.1 生成

按模式选模板填空：

- 模式 1（新建）：先扫 `linkfoxagent-v2/` 实时全集 → recipes → 能力主表 / 平台索引 → 对照当前 agent 已挂载能力筛掉不可执行候选 → 复制 `workflow-skill-template.md` 填。
- 模式 2（复刻）：把源 skill 完整复制，按差异点逐章改；保留 frontmatter 里 5–10 同义词的原值，替换不当的那几个。
- 模式 3（微调优化）：先体检（`quick_validate.py` + `self-check.md`）→ 把 finding + 用户诉求统一按变更面分类 → 逐项修；业务/口径疑问列给用户确认后再动；触及流水线 DAG 必须重跑评估。

### 9.2 测试（trial prompts）

agent 在当前对话里当场跑 2–3 条 prompt 验证，三种类型必须搭配：

| 类型 | 用意 |
|------|------|
| **核心** | 最典型用法跑通——验证 happy path |
| **边界** | 极端值 / 空结果 / 失败路径——验证降级 |
| **欠触发探针** | 用户用最简短随意的口吻说同样诉求——验证反向补漏起作用 |

> **不落盘到产物**：trial prompts 只是 agent 自检手段，不写成 `examples/trial-prompts.md` 提交进产物 skill。产物 skill 的 `examples/` 留给真实输入输出样本。
> **唯一例外**：本 meta-skill 自己保留 `examples/trial-prompts.md`——它验的是 meta-skill（创建工作流）自身能否被正确触发。

### 9.3 验证

执行 §7 的三步回环。每个 scripts/*.py 都要过。

### 9.4 评估

**静态层**：`references/self-check.md` checklist，4 组结构（frontmatter / 结构 / 内容 / Tier 特定）。
跑 `python scripts/quick_validate.py --type A <skill>` 自动校验大半，其中包含 `response_io.py` 与 `_shared/linkfox_paths.py` 的 hash 校验。

**动态层**：试跑期 agent 自检 + 用户确认。

### 9.5 优化（反馈三分类）

| 类别 | 来源信号 | 处理 |
|------|---------|------|
| 业务理解错误 | "这步不该有"、"权重不对" | 回访谈步骤修 |
| 写法瑕疵 | "标题要粗体"、"日期格式" | 直接改产物 |
| 触发问题 | "我说 X 它没反应" | 改 frontmatter description |

### 9.6 迭代（单条试跑闭环）

```
跑一条 → agent 自检 → 呈现结果 → 用户反馈 → 重跑（如需）→ 用户明确 OK → 下一条
```

**关键约束**：沉默 / "还行" / "差不多" 不算满意——必须再问具体哪里要改，直到拿到明确的"这条 OK，下一条"信号。

详见 `references/trial-and-iterate.md`。

---

## 10. 自检 checklist（必跑）

每个 skill 交付前过一遍 `references/self-check.md`。关键项：

- [ ] frontmatter 只用允许字段，name = 目录名，且只能包含小写字母、数字和 `-`；description 双语 + 反向补漏。
- [ ] Tier 已确认（2 / 3），主体章节齐全（参考 §6 矩阵）。
- [ ] 每个 scripts/*.py 通过三步回环验证。
- [ ] 大响应步骤嵌入落盘段落，`response_io.py` hash 一致。
- [ ] 流水线 DAG 自检通过（每步至少一条出边、每个交付字段至少一条入边）。
- [ ] 所有步骤使用的公共 skill 均已在当前 agent 挂载；未挂载能力已标记为需用户通过技能广场或 `https://skill.linkfox.com/` 安装，未写成当前可执行步骤。
- [ ] 含「报告产物」章节的 skill：章节末尾含 `linkfox-report-generator` handoff 段落，没有自造报告样式 / html。

最后一步：`python scripts/quick_validate.py --type A <skill 目录>` 静态校验通过。

---

## 11. 交付路径

- 项目级自定义 skill：`/root/.linkfox/workspaces/.claude/skills/<name>/`，创建 / 保存自定义 skill 时放这里。
- 系统级 skill：`/root/.linkfox/.ce/skills/<name>/`，平台内置的 `linkfox-*` 系列在这里，只读，按需调用即可。
- 目录已存在 → **停下来问用户**，不静默覆盖。
- 团队仓库交付：把 skill 目录提交到约定的中心仓库，不要散落在各人的 `~/.claude/`。

打包工具非强制；如需要，参考 `skill-creator/scripts/package_skill.py`。

---

## 12. 反模式（红线）

- **流程类**：堆砌看起来相关、实际没人消费的查询步骤；DAG 不连通；让用户在两个 Tier 1 数据源间裸选。
- **复刻类**：照搬源 skill 的 description 5–10 同义词不替换；改了平台没改样例 ASIN/站点。
- **微调类**：动了流水线却跳过评估环节；改 description 不重跑欠触发探针。
- **报告产物**：本 skill 内复制报告样式 / html 骨架 / 配色 / 元信息块；不向 `linkfox-report-generator` handoff；handoff 段落漏写或写成"建议"而非"必须"。
- **通用**：description 写一行 ID 而非触发文案；frontmatter 出现非许可字段；中英文混杂在字段名 / JSON keys 里。

---

## 13. 双语策略

- **写作语言**：中文为主。说明、章节标题、用户可见对话、报告外观——中文。
- **保留英文**：frontmatter 字段名、JSON keys、参数名、文件名、技术术语（API endpoint、selector、schema）。
- **触发词**：双语并行。

---

## 14. 参考文件索引

- 决策与流程
  - `SKILL.md` —— 完整生成流水线（三模式分支）
  - `references/interview-playbook.md` —— 三模式访谈剧本
  - `references/methodology-extraction.md` —— 方法论萃取分支（资料 → 方法论 → 通用化 → 平台缺口盘点）
- Tier 1 目录
- `scripts/list_v2_skills.py` —— 扫描 `linkfoxagent-v2/` 实时全集，支持 inventory/catalog/platform/vendor 视图、generated 索引写出和 recipes slug 校验
  - `references/tier1-recipes.yaml` —— 业务配方（intent → chain）
  - `references/tier1-catalog.md` —— 能力主表
  - `references/tier1-by-platform.md` —— 平台索引
  - `references/tier1-by-vendor.md` —— 厂商索引
- 模板
  - `references/workflow-skill-template.md` —— Tier 2/3 流程主模板
  - `references/frontmatter-spec.md` —— description 正反例
- 通用规范
  - `references/encapsulation-guide.md` —— 脚本封装规范
  - `references/verification-guide.md` —— 三步回环验证
  - `references/trial-and-iterate.md` —— 试跑与迭代
  - `references/self-check.md` —— 自检 checklist
  - `references/large-response-snippet.md` —— 大响应落盘段落
  - `references/target-structure.md` —— 目录结构细则
- 工具
  - `scripts/quick_validate.py` —— frontmatter + 结构静态校验
  - `scripts/verify_skill_scripts.py` —— 三步回环验证执行器
  - `scripts/response_io.py` —— 大响应落盘 / 字段投影

---

## 15. FAQ

**Q：我的需求是不是该做 skill？**
A：流程将来还要重复跑吗？是 → 做。一次性 → 直接执行。

**Q：调用一个 Tier 1 就够了，我还要做 Tier 2 吗？**
A：不要。直接让用户调 Tier 1。Tier 2 的价值在于「跨数据源组合 + 决策 + 报告」，单调用没有沉淀价值。

**Q：复刻模式下，源 skill 的 5–10 同义词要不要改？**
A：要。每个同义词都要审查是否仍贴合新场景；不贴的换掉，再补 1–2 个新场景的口语化说法。

**Q：现存 skill 不符合标准要不要改？**
A：标准只对今后新建/重大修订生效；存量在主动重构时再迁移。
