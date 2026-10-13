# 翻译工作流细则

本文给出每一步的详细规范。各模式共享步骤如下：

- **快翻**：直接翻译（不走本文中的步骤）
- **普通**：Step 1（分析）→ 翻译
- **精翻**：Step 1（分析）→ Step 2（提示词）→ Step 3（起稿）→ Step 4（审校：术语 + 独立审校 + 回译）→ Step 5（修订，可迭代）→ Step 6（润色）
- **普通 → 升级**：普通模式之后，用户可继续 Step 4 → Step 5 → Step 6

所有中间产物以文件形式保存在输出目录中。

## Step 1：内容分析

翻译前先分析源材料。把分析保存到输出目录的 `analysis.md`。

### 1.1 内容摘要

- 内容讲什么？核心论点是什么？
- 作者背景、立场与写作语境
- 原文的目的与目标读者

### 1.2 术语

- 列出技术术语、专有名词、品牌、缩写
- 与已加载术语表交叉核对
- 不在术语表中的，确定标准译法
- 整理成术语表

### 1.3 语气与风格

- 正式还是口语？是否有幽默、隐喻、文化典故？
- 给定目标读者，译文适合什么语域？

### 1.4 翻译难点

识别可能造成翻译困难的地方：

- **理解断点**：目标读者可能不理解的术语或引用——记录需要怎样的解释
- **修辞**：无法字面对译的隐喻、习语、表达——记录意图含义和目标语处理方式（意译 / 替换 / 保留）
- **结构难点**：长复杂句、文字游戏、双关、需要创造性改写的幽默

**保存 `analysis.md`**：
```
## 内容摘要
[核心论点、作者、语境、目的]

## 术语
[术语 → 译文，...]

## 语气与风格
[评估]

## 翻译难点
- [术语 / 段落] → [难点类型] → [建议方法]
- ...
```

## Step 2：组装翻译提示词

主 Agent 读取 `analysis.md`，用 [references/subagent-prompt-template.md](subagent-prompt-template.md) 组装完整翻译提示词。从分析中内联以下内容：

- **目标风格**：解析后的风格预设 + §1.3 的原文声音
- **内容背景**：§1.1 的摘要
- **术语表**：合并后的术语表（含 §1.2 抽取出的术语）
- **翻译难点**：§1.4 的全部难点

保存到 `prompt.md`。该提示词由子 Agent（分块时）或主 Agent 自身（不分块时）使用。

## Step 3：初稿

保存到输出目录的 `draft.md`。

分块内容由子 Agent 产出本草稿（合并自各 chunk 的译文）。不分块时由主 Agent 直接产出。

按 `prompt.md` 翻译全文。应用 SKILL.md 中的全部 **翻译原则**。

## Step 4：关键审校

审校拆成三部分，避免起草者的盲区：

- **4a**：脚本式术语合规检查（确定性）
- **4b**：独立审校子 Agent（对抗式角色，对起草者推理盲读）
- **4c**：抽样回译核验（独立子 Agent）

三者均汇入 `review.md`，按严重度分级（P0/P1/P2）。**只诊断——本步不重写**。

**并发**：4a 必须先于 4b 完成（审校者要读 `glossary-check.txt`）。4c 只需要 `draft.md`，因此与 4a+4b **并行**启动——省一轮等待。

审校者 + 回译者提示词模板：[reviewer-subagent-prompt.md](reviewer-subagent-prompt.md)。

### 4a. 术语合规检查（脚本）

启动审校者前先跑这个。产出确定性的术语级报告——审校者读它并打严重度标签。

```
python3 {baseDir}/scripts/glossary_check.py \
  --source {source_file} \
  --draft  {output_dir}/draft.md \
  --glossary {glossary_path_1} [--glossary {glossary_path_2} ...] \
  --output {output_dir}/glossary-check.txt
```

把所有贡献给 `prompt.md` 的术语表都传进去（内置 + PREFERENCES.md 的术语表文件 + 任意 `--glossary`）。报告类别：`untranslated` / `missing` / `under` / `over` / `ok`。除 `ok` 外，都是候选批评项——具体严重度由审校者判断（通常是 P0/P1）。

### 4b. 独立审校（子 Agent）

按 `reviewer-subagent-prompt.md` 的 Part 1 启动**一个**审校子 Agent。审校者：

- 只看：源文、`draft.md`、`glossary-check.txt`、`prompt.md`
- **不看**：起草者的任何思考、之前的批评、主 Agent 的上下文
- 扮演对抗角色——找问题，不重写
- 每条问题打 P0 / P1 / P2（严重度定义见下文）
- 按规定结构保存到 `review.md`

审校者的清单覆盖 **准确性**、**目标语母语感**（按方向特化的标记：CJK 翻译腔、英文死译等）、**注释与文化适配**。完整准则见 `reviewer-subagent-prompt.md` 的 §A/B/C。

### 4c. 回译抽样核验（子 Agent）

主 Agent 从 `draft.md` 中挑 3–7 句：

- 最长的句子
- 最具习语性 / 隐喻最多的
- 术语密集（一句中含多个术语表条目）
- 在 `analysis.md` 中被标记为难点的段落里的句子

按 `reviewer-subagent-prompt.md` Part 2 启动**一个**回译子 Agent。它把抽样句子**字面**回译为源语言，并保存到 `back-translation.md`。

主 Agent（或在后续审校轮次中由审校子 Agent）把每条回译与源句对照，将漂移项以适当严重度追加到 `review.md` 的 "回译交叉核验" 一节。

### 4d. 严重度定义

每条问题**必须**打标签。Step 5 的修订行为由严重度驱动。

| 标签 | 含义 | 例子 |
|------|------|------|
| **P0** | 严重——事实 / 语义错误 | 数字错、否定反转、专名误译、内容静默增删、术语 `untranslated` 违规 |
| **P1** | 主要——细心读者会注意到的意义或自然度偏移 | 死译句、漏掉必要注释、术语 `under` / `missing`、主张被弱化、强调点丢失 |
| **P2** | 次要——润色 / 风格 | 可以更优雅、备选措辞、冗余连词 |

### 4e. 批评文件格式

`review.md` 由审校子 Agent 产出。结构以 [reviewer-subagent-prompt.md](reviewer-subagent-prompt.md) 的 §"输出格式" 为准——任一文件改动时另一份要同步更新。

主 Agent 读 `## 汇总` 块来决定迭代 gate：

- `Gate: ready-for-polish`（P0 = 0 且 P1 = 0）→ 进入 Step 6
- `Gate: must-iterate` → 走 Step 5b

## Step 5：修订

按批评修订译文，保存到 `revision.md`。

### 5a. 应用修订（按严重度）

- **P0 + P1 问题**：必须**全部**修。**不要**因为 "改起来别扭" 而跳过——重构这句话
- **P2 问题**：判断题。确实让文笔更好就改；只是审校者偏好就跳过。目标采纳率 ≥ 50%，倾向于改

读 `draft.md` + `review.md`，产出 `revision.md`。

### 5b. 迭代循环

保存 `revision.md` 后：

1. 在 `revision.md` 上重新启动审校子 Agent（同样的 prompt，对此前批评盲读）。输出保存为 `review-round2.md`
2. 检查第二轮批评的 gate：
   - `ready-for-polish` → 进入 Step 6
   - `must-iterate` → 再做一轮修订：读 `revision.md` + `review-round2.md`，保存为 `revision-round2.md`。再审校为 `review-round3.md`
3. **修订最多 2 轮**（即最多到 `revision-round2.md` / `review-round3.md`）。若 gate 仍未通过：
   - 上报用户："经过 2 轮修订，审校仍标记 N 个 P0/P1。打开 `review-round3.md` 查看。是继续润色、手工迭代、还是中止？"
   - **不要**静默继续到润色

迭代成本：**审校者**每轮重新启动，但**回译者只跑一次**（Step 4c）。仅当第 1 轮批评以漂移为主时才重跑回译——否则第 1 轮的回译仍然有效。

最终修订文件（`revision.md` 或 `revision-round2.md`）作为 Step 6 的输入。

## Step 6：润色

最终版本保存到 `translation.md`。

输入：Step 5 的最新修订文件（`revision.md`，若有迭代则为 `revision-round2.md`）。

为出版质量做最后一遍：

- 把整篇译文当成独立作品来读——是否像目标语言原创？
- 抹平剩余的粗糙过渡
- 保证整篇叙事声音和风格一致
- 最后一次术语一致性核查
- 验证格式是否完整保留

## 子 Agent 职责

三个独立子 Agent 角色：

| 角色 | Step | 看到 | 工作 |
|------|------|------|------|
| **起草者** | 3 | `prompt.md` + 自己的 chunk（或整份源文） | 产出初稿。每 chunk 一个，并行 |
| **审校者** | 4b | 源文 + `draft.md` + `prompt.md` + `glossary-check.txt` | 对抗式批评，打 P0/P1/P2。每轮重新启动 |
| **回译者** | 4c | 仅来自 `draft.md` 的抽样句子 | 字面回译，用于交叉核验 |

主 Agent 编排：跑分析、组装提示词、启动子 Agent、跑术语脚本、应用修订、做最终润色。审校者与起草者**有意分开**调用——审校者**永不**看到起草者的推理。

## 分块下的精翻

当内容超过分块阈值且使用精翻模式时：

1. 主 Agent 先在**整篇**文档上跑分析（Step 1）→ `analysis.md`
2. 主 Agent 组装翻译提示词 → `prompt.md`
3. 切分 chunks → `chunks/`
4. 每 chunk 一个起草者子 Agent 并行（各自读 `prompt.md`）→ 合并为 `draft.md`
5. Step 4a：跑 `glossary_check.py` → `glossary-check.txt`
6. Step 4b：在合并后的 `draft.md` 上启动独立审校子 Agent → `review.md`
7. Step 4c：在抽样句子上启动回译子 Agent → `back-translation.md`；主 Agent 把漂移项追加到 `review.md`
8. Step 5：修订循环（最多 2 轮，gate = P0/P1 = 0）→ `revision.md` [或 `revision-round2.md`]
9. Step 6：主 Agent 润色 → `translation.md`
10. 最后一次跨 chunk 一致性扫读：术语、叙事流畅度、chunk 边界处的过渡
