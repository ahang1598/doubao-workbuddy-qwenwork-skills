# linkfox-ecommerce-skill-creator

> 团队电商 skill 撰写标准 + 创建工作流 + 模板 + 校验工具，一站式交付。
> 让产品经理在 vibe coding 时按统一规范产出 / 复刻 / 微调电商 skill。

---

## 1. 解决什么问题

团队进入「agent 交互后的 skill 开发」阶段，遇到三个具体痛点：

1. **同一业务流不同人写法不同**：选品、复刻、监控等流程目录结构、字段命名、触发文案各一套，agent 唤起率参差。
2. **底层工具重复发明**：明明 Linkfox 已经把 80+ 电商数据源封装成 Tier 1 skill，新作者还在重写 wrapper。
3. **写完即交付**：没有统一的测试 / 验证 / 评估 / 迭代闭环；交付质量全看作者经验。

本 skill **不是又一个 skill 工具**，而是团队 skill 撰写规范的载体——它既是规范文档（人读），也是创建工作流（agent 调用），还是模板和校验工具（直接复用）。

> **范围（与 `linkfox-skill-creator` 分工）**：本 skill 专做**跨境电商 Tier 2 / Tier 3 业务流程 skill**（有明确多步流程、面向产品内部）。单接口 API wrapper（Tier 1）、通用工具型 skill 的创建 / 优化 / 校验一律走 `linkfox-skill-creator`——本 skill 只**调用** Tier 1，不**生产** Tier 1。

---

## 2. Tier 模型：本 skill 在哪一层

**一句话版**：Tier 是这个 skill **内部有几道工序**。Tier 1 = 底层薄封装无编排；Tier 2 = 内部含多步骤编排；Tier 3 = 完整业务 SOP。

| 层 | 一句话定义 | 类比 | 例子 |
|---|---|---|---|
| **Tier 1** | 底层 API / 数据源薄封装：参数进、单调用、结构化数据出，无业务编排 | 食材 | `linkfox-amazon-product-detail`（真实） |
| **Tier 2** | 综合场景能力：内部含多步骤编排（可编排 Tier 1，也可以单调用但带模型选 / 模式判断 / 参数校验 / 输出策略等内部决策步骤） | 半成品 | *示意名* `amazon-listing-replicator` |
| **Tier 3** | 完整业务 SOP，端到端跑完一条业务流程 | 一道菜 | *示意名* `weekly-sourcing-workflow` |

> ⚠ 标注 *示意名* 的仅作类比，**不要假定可调用**。

**Tier 1 vs Tier 2 实操判别**：盯住 SKILL.md 的"使用指引"段——线性"传参 → 调一次 → 返回结果" 即 Tier 1；出现"先 X、再判断 Y、然后选 Z" 这种**条件分支或多阶段**逻辑（哪怕外部调用还是一次） 即 Tier 2。

层次叠放：

```
Tier 0  ← 本 skill：撰写标准 + 创建工作流（meta）
        │
        ▼
Tier 3  复刻型：业务 SOP（"周度选品报告复刻"）
Tier 2  组合型：跨数据源的业务能力（listing-rewrite-amazon、kw-matrix-amazon）
Tier 1  原子型：Linkfox 封装的 80+ 数据源 wrapper（linkfox-amazon-product-detail 等）
```

**约束**：

- 本 skill 只产、只优化 **Tier 2 / Tier 3 业务流程 skill**；Tier 1 wrapper / 通用工具 skill 的创建、优化、校验走 `linkfox-skill-creator`。
- Tier 1 是底层原料，由 vendor 维护，本 skill **只调用、不生产**。完整目录见 `references/tier1-catalog.md`。
- 用户不知道 Tier 1 长什么样——**用户讲业务，agent 选 Tier 1 工具**。

---

## 3. 三种操作模式

任何用户诉求落到三种模式之一，**都走同一套生命周期**。

```
用户的诉求
│
├─ 业务从零搭：选品 / 复盘 / 监控等 → 模式 1：新建
│
├─ 已有 Tier 2/3 skill 但要 fork：换平台 / 换打分维度 → 模式 2：复刻
│
└─ 现有 skill 局部改动（业务行为或规范层面） → 模式 3：微调优化
```

| 模式 | 入口信号 | 信息源 | 主要难点 |
|------|---------|--------|---------|
| 1 新建 | "帮我做一个 X 的 skill" | 业务访谈 + `linkfoxagent-v2/` 实时全集 + Tier 1 目录 + 配方表 | 选对原料链路 |
| 2 复刻 | "照着 Y 做一个 Z" | 源 skill + 差异点 | 识别哪些固定 / 哪些要变 |
| 3 微调优化 | "把 W 的 X 改成 Y" / "优化这条 skill" / "补 frontmatter 触发词" | 现有 skill + 用户指令 + 本规范通用部分 | 变更面识别 + 改动面控制 |

三种模式的入口决策树和访谈剧本见 `SPEC.md` 与 `references/interview-playbook.md`。

---

## 4. 生命周期：六个环节

无论哪种模式，都必须走完六环：

```
生成 → 测试 → 验证 → 评估 → 优化 → 迭代
```

| 环节 | 关键产物 | 强制度 |
|------|---------|------|
| **生成** | SKILL.md + scripts/ + references/（按模式裁剪） | ✓ |
| **测试** | `examples/trial-prompts.md`：核心 + 边界 + 欠触发探针 | ✓ |
| **验证** | 每个 `scripts/*.py` 过三步回环（结构 / 真实 / 错误降级） | ✓ |
| **评估** | `references/self-check.md` 通过 + `quick_validate.py` 通过 | ✓ |
| **优化** | 按反馈三分类（业务理解 / 写法瑕疵 / 触发问题）针对性修 | ✓ |
| **迭代** | 单条试跑独立闭环（不批量过） | ✓ |

为什么这么设计、每个环节的具体玩法，全在 `SPEC.md`。

---

## 5. 能力发现：实时全集 + 导航索引

新建 / 复刻模式的第一步都是「找原料」。

`linkfoxagent-v2/` 实时目录是能力发现 SOT。`references/tier1-*` 与 `tier1-recipes.yaml` 是基于 v2 的二次摘要 / 导航缓存，用于分类、平台收窄和高频链路匹配；它们可能滞后，不能覆盖实时目录和 `SKILL.md` frontmatter。创建时先扫描 v2 实时全集作为设计参考，再用导航索引辅助筛选；但当前运行只能调用目标 agent 已挂载的 skill。若流程依赖未挂载能力，必须标记为暂不可执行，并提示用户可通过“技能广场”或 `https://skill.linkfox.com/` 安装所需 skill；安装后可从用户自己的 `skills/` 路径访问。不得承诺运行时自动加载。

```bash
python scripts/list_v2_skills.py --view inventory --format markdown
python scripts/list_v2_skills.py --view catalog --query amazon --format markdown
python scripts/list_v2_skills.py --view recipes-validation --strict-recipes
```

导航索引提供四个相互索引的视图：

| 文件 | 用途 | 何时进 |
|------|------|------|
| `references/tier1-catalog.md` | **能力主表**（17 桶：详情 / 搜索 / 关键词 / 评论 / 选品 …） | 用户讲业务能力，先来这里 |
| `references/tier1-by-platform.md` | **按平台索引**（Amazon / TikTok / Ozon / 1688 / Shopee / eBay / Walmart / Etsy） | 用户已点名平台 |
| `references/tier1-by-vendor.md` | **按数据源索引**（22 家厂商 SOT） | 用户点名数据源 |
| `references/tier1-recipes.yaml` | **业务配方表**（12 条高频 intent → primitive chain） | 命中即抄链路，免现搭 |

**用法**：先扫 v2 实时全集 → 用配方表匹配高频链路 → 用能力主表 / 平台索引辅助收窄。**禁止让用户在两个 Tier 1 数据源之间裸选**——agent 必须自己定方案后讲给用户确认。

---

## 6. 三个底层假设

整个标准建立在这三个假设上。理解它们就理解了所有取舍。

### 假设 1：skill 不是万能锤

一次性分析、单点解读、咨询式问答——直接执行就行，沉淀成 skill 反而增加维护成本和触发噪音。**做 skill 的真实信号是「重复执行」+「多人共享」**。

→ 决策树第一关："这个流程将来还要重复跑吗？" 否 → 不做 skill。

### 假设 2：用户不懂技术，作者不懂业务

写 skill 的作者熟悉技术（API、selector、JS），但可能不懂业务（选品节奏、广告策略）。被 skill 服务的用户（产品经理在 vibe coding）熟悉业务，但不懂技术。

→ 所有「用户对话」的地方强制 **业务语言交互**：选项用业务后果维度（"这步要不要"），不用技术动作维度（"重试 / 改 pageSize / 跳过"）。
→ 用户讲业务，agent 选工具。**假设用户不了解任何 Tier 1 数据源**。

### 假设 3：默认欠触发，必须主动推一把

agent 偏保守——`description` 写得稍模糊就根本不被唤起。

→ frontmatter `description` 强制「反向补漏一句」："即使用户只说……也应触发"。
→ 试跑必须包含「欠触发探针」——用最简短随意的口吻验证。

---

## 7. 怎么用（5 分钟上手）

### 角色 1：产品经理在 vibe coding

直接对 Claude Code 说三种诉求之一：

- "帮我做一个 X 的 skill" → 走模式 1
- "照着 Y 做一个 Z" → 走模式 2
- "把 W 的 X 改成 Y" / "优化这" → 走模式 3

agent 会自动调用本 skill：业务语言访谈 → 给方案 → 你确认 → 生成 → 测试 → 评估 → 交付。

### 角色 2：写 skill 的作者

1. 读 `SPEC.md`（一页人读规范）。
2. 选模式（1/2/3），按对应模板填空。
3. 跑 `python scripts/quick_validate.py <你的 skill>`。
4. 跑 `python scripts/verify_skill_scripts.py <你的 skill>`。
5. 用 `examples/trial-prompts.md` 里的提示词做 2-3 轮试跑。
6. 过 `references/self-check.md`。

### 角色 3：维护标准的人

- 改规范 → `SPEC.md` + `SKILL.md`。
- 加 Tier 1 → 先确保 `scripts/list_v2_skills.py` 能在实时全集里扫到；如需更新可读索引，跑 `scripts/list_v2_skills.py --write-indexes <目录>` 生成视图后再替换导航文件。
- 改校验逻辑 → `scripts/quick_validate.py` / `verify_skill_scripts.py`。

---

## 8. 文件地图

```
linkfox-ecommerce-skill-creator/
├── README.md                          # 本文（定位 + Tier 模型 + 三模式 + 生命周期）
├── SPEC.md                            # 一页人读规范
├── SKILL.md                           # agent 执行入口
│
├── references/                        # 细节文档
│   ├── tier1-catalog.md               # Tier 1 主表（按能力 17 桶）
│   ├── tier1-by-platform.md           # Tier 1 按平台索引
│   ├── tier1-by-vendor.md             # Tier 1 按厂商索引
│   ├── tier1-recipes.yaml             # 高频业务配方（intent → primitive chain）
│   │
│   ├── interview-playbook.md          # 三模式访谈剧本
│   ├── target-structure.md            # 目录结构规范
│   ├── frontmatter-spec.md            # description 双语 + 反向补漏
│   ├── encapsulation-guide.md         # scripts 封装规范
│   ├── verification-guide.md          # 三步回环验证
│   ├── trial-and-iterate.md           # 试跑迭代（反馈三分类）
│   ├── self-check.md                  # 自检 checklist
│   ├── large-response-snippet.md      # 大响应落盘段落模板
│   │
│   ├── workflow-skill-template.md     # Tier 2/3 流程模板（主用）
│   └── examples/
│       └── selection-weekly.md        # 完整示例：每周选品（Tier 3）
│
└── scripts/
    ├── list_v2_skills.py              # 扫描 v2 实时全集 / 生成索引 / 校验 recipes
    ├── response_io.py                 # 大响应落盘 / 字段投影
    ├── quick_validate.py              # frontmatter + 结构静态校验
    └── verify_skill_scripts.py        # 三步回环验证执行器
```

---

## 9. 标准未覆盖的（已知盲区）

| 缺漏 | 原因 |
|------|------|
| **回归测试** | 修 skill 后只重跑当条 prompt，不自动跑历史所有 prompt。 |
| **量化触发率指标** | 没度量「100 条用户消息中 N 条触发」。靠欠触发探针定性检查。 |
| **安全审查** | 标准只说"不要硬编码 key"——依赖漏洞、注入风险、权限边界不在范围。 |
| **运维监控** | skill 部署后的错误率 / 调用频次 / 响应时长统计不在范围。 |
| **MCP / 插件层** | 仅适用 Claude Code skill；其它形态不覆盖。 |

需要这些能力时，独立工具承担，不要硬塞进本标准。

---

## 10. 何时该升级标准

- 团队 skill 数量 > 30，回归测试成本超过收益 → 引入 evals.json + grader（参考 `skill-creator/references/schemas.md`）。
- 触发率成为反复痛点 → 加触发率监控。
- 出现安全事故 → 补安全审查章节。
- Tier 1 数量 > 150 或频繁改名 → 以 `scripts/list_v2_skills.py` 的实时 inventory 为 SOT，把 `tier1-*` 固化为 generated 索引，不再人工维护。
