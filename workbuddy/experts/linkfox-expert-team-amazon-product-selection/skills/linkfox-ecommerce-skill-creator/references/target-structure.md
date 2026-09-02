# 生成产物的目录结构规范

按本规范创建生成的目标 skill。所有路径相对于目标 skill 根目录。

## 输出位置默认

默认写到**当前 agent 的用户级 skills 目录**（用户主目录下的全局位置，跟着用户走、跨项目可用），除非用户提出其他要求。

agent 在阶段 0 决定产物目录后，向用户复述一句确认（"我会把它建在 <路径>，对吗？"），用户否决再调整。

### 通用约束

- 目录冲突时不静默覆盖：如果选定位置已存在同名目录，停下来告诉用户，让其决定如何处理。
- **中间产物**（`interview.md`、`mapping.md`、`dag.md`、`试跑提示词.md`，方法论萃取分支另有 `methodology.md`、`platform-coverage.md`、`raw-materials/`）写到**产物目录下的 `.draft/`**，与 skill 绑定不污染 cwd；多 skill 并行不互相覆盖。
- **运行期产出**（报告 / 数据 / 媒体）一律落到 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/{reports|data|media}/`，详见 `output-contract.md` §1。**禁止**让用户传 `--out-dir` 改主路径、禁止写 `/tmp`。

---

## 目录结构

```
<target-skill-name>/
├── .draft/                     生成期临时草稿，跟随产物目录；产物完成后可保留作为档案，也可删
│   ├── raw-materials/          方法论萃取分支：用户原始资料落盘（仅资料驱动时有）
│   ├── methodology.md          方法论萃取分支：结构化方法论 + 平台适用性（仅资料驱动时有）
│   ├── platform-coverage.md    方法论萃取分支：平台 × 步骤 数据支持矩阵（仅资料驱动时有）
│   ├── interview.md            访谈纪要（步骤 1 写）
│   ├── mapping.md              步骤映射定稿（步骤 2 写）
│   ├── dag.md                  DAG 校验图（步骤 3 写）
│   └── 试跑提示词.md           合成的试跑提示词（阶段 5 写）
├── SKILL.md                    必有，遵循 workflow-skill-template.md
├── scripts/
│   ├── response_io.py          必有：从本 skill 复制过来，原样不改
│   ├── linkfox_paths.py        必有：从 linkfoxagent-v2/_shared/linkfox_paths.py 复制过来，原样不改；所有落盘走它的 resolve_*_path
│   ├── validate_product_payload.py  商品列表产物推荐：从本 skill 复制，校验 { products } 载荷
│   └── <step_N>_<verb>.py      可选：步骤特有的编排/转换脚本
└── references/
    ├── steps/                  长流程必有：每步一个详情文件，SKILL.md 大纲指向它，按步加载
    │   ├── S1.md               步骤 1 详情（输入/操作/输出/落盘/参数）
    │   ├── S2.md               步骤 2 详情
    │   └── S<N>.md             ……
    ├── workflow.md             必有：业务流程详述与字段需求清单
    ├── data-fields.md          必有：所有步骤的输入/输出字段汇总表
    ├── report-template.md      访谈中用户要求生成报告时必有
    ├── output-schema.md        Tier 2/3 必有：传输 + 载荷契约（从 meta-skill 的 output-schema-template.md 内联改写）
    └── examples/               可选：典型对话示例 / 跑通后的样例输出
        └── *.md / *.json
```

> **大纲化原则（治长流程注意力失焦）**：`SKILL.md` 是**大纲**——执行编排 + 流水线总览表（每步一行，含 `依赖`/`用途`/指向 `steps/S<N>.md`）；每步的血肉细节落在 `references/steps/S<N>.md`，agent 执行到该步才 Read，只把当前步细节加载进上下文。拆分门槛与单步文件格式见 `workflow-skill-template.md` §3。短流程（≤ 3 步且每步几行）可不拆 `steps/`，详情内联在 SKILL.md。

## 命名规则

- **目标 skill 名**：全小写、连字符分隔；优先以"业务动作 + 节奏"命名，如 `selection-weekly`、`keyword-refresh-weekly`、`fba-replenish-daily`。前缀不强制 `linkfox-`，仅当用户明确要求并入 LinkFox 套件时才加。
- **目录名 = frontmatter `name` = 交付 slug**：三者必须完全一致；只能使用小写字母、数字和连字符 `-`（正则：`^[a-z0-9-]+$`），不得包含大写、下划线、空格、中文或其它符号。
- **步骤脚本**：`step_<N>_<动词缩写>.py`，例如 `step_2_aggregate.py`。
- **报告模板**：`report-template.md`（一份），内含两套样式块（md / html），由 SKILL.md 在收尾步骤里引用。
- **报告产物**：运行时通过 `linkfox_paths.resolve_report_path(slug, ts, ext)` 落到 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/reports/<slug>-<ts>.<ext>`；`<session>` 取自 `SESSION_ID` 环境变量。**不要**写进 skill 自身目录、`/tmp` 或用户级别 skills 目录。

## 各文件最低要求

### SKILL.md

- frontmatter：`name` 与目录名一致，且只能包含小写字母、数字和 `-`；`description` 中英短语齐备，覆盖至少 5 个同义改写，并刻意"推一把"（详见 `workflow-skill-template.md` 的 description 写作要点）。
- 主体：7 段固定章节
  1. 适用场景与不适用场景
  2. 一次性参数（站点、时间窗、ASIN/关键词输入等）
  3. 已挂载能力约束（实际调用的公共 skill 清单；未挂载能力只能作为安装提示，不得写成当前可执行步骤）
  4. 流水线步骤——**大纲层**：执行编排 + 流水线总览表（每步一行：标题 / 一句话 / `依赖` / `用途` / 指向 `steps/S<N>.md`）。单步血肉（输入 / 操作 / 输出 / 落盘）落在 `references/steps/S<N>.md`，长流程必拆、短流程可内联。
  5. 报告产物（仅当用户要报告时存在）
  6. 自检 checklist（针对该业务流程的轻量版）
  7. 局限性

详细样板见 `workflow-skill-template.md`。

### scripts/response_io.py

直接复制本 skill 的 `scripts/response_io.py`，**不要修改、不要重命名**。生成产物时核验文件 hash 一致。

### scripts/linkfox_paths.py

直接复制 `linkfoxagent-v2/_shared/linkfox_paths.py`，**不要修改、不要重命名**。`_shared` 是路径协议的唯一权威源；如果路径规范调整，只更新 `_shared` 并重新复制到产物。`quick_validate.py` 会用 hash 校验产物副本是否与 `_shared` 一致。

### scripts/step_<N>_<verb>.py（可选）

只在以下情况新增：
- 跨多个 skill 调用的结果需要做 join、归一、去重时。
- 输出形态需要从 JSON 转 csv/markdown 表用于报告。
- 业务规则计算（毛利率、断货风险分等）。

不要把"调用某个 linkfox skill"这种动作写成脚本——agent 直接调即可。

### references/workflow.md

把访谈纪要清洗后落盘。结构：
- 业务目标
- 输入参数清单
- 步骤拆解（编号、动作、上下游、所需字段）
- 报告诉求（若有）
- 已知局限 / TBD

### references/data-fields.md

汇总每一步的输入字段、输出字段、字段中英对照、来源 skill。

供 agent 在运行时快速找字段，不重复阅读 SKILL.md。

### references/report-template.md（条件必有）

仅当访谈得出"需要报告"时生成。模板内必须含：
- 元信息块（生成时间、参数快照、数据来源、局限性说明）
- md 样式块、html 样式块
- 章节占位由业务驱动，不预设业务章节

详细规范见 `workflow-skill-template.md` 的"报告样式"章节。

## DAG 校验图

生成产物之前必须在脑中画出（或在 `.draft/dag.md` 里画出）这张图：

```
[输入参数]
    ↓
[步骤 1] ──→ [步骤 2] ──→ [步骤 3] ──→ ...
    ↓                          ↓
 [报告章节 A]          [报告章节 B / 决策]
```

每个节点至少一条出边连到下游节点或终端（报告/决策/动作）。任何"孤岛步骤"必须合并或删除。
