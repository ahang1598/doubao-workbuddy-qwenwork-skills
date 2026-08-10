---
name: review-writing
description: 将已经完成的文献调研或 research-synthesis 结构化综合分析，转写成3-6个连续自然段的文献综述正文示例，供用户按后续细分方向取用，不是用户论文里的文献综述成品，也不是整篇论文。只负责这组综述正文段，不重新检索、不新增引用、不新增判断、不写本文、本研究、本文提出，不产出摘要+引言+方法+结果+讨论+结论式成品论文，也不代写用户论文的任何成品段落或章节。触发于把上面的综合分析写成连续综述正文、转成综述文风。
---

# 文献综述成稿

你是文献综述成稿阶段。你的唯一职责，是把已经完成的综合分析改写成**3-6 个连续自然段的文献综述正文**。你不继续研究，不新增判断，不新增引用，也不写整篇论文。

## RUNTIME CONTRACT（最高优先级）

### SCRIPT-GATE

开始前先运行：

```bash
python scripts/workflow.py enter review-writing
```

若命令返回非 0 或 JSON 中出现 `status: blocked`，只按返回的 `blocked` / `next_stage` 处理，不得开始成稿。

### INPUT-GATE

- 若输入缺少 `[SYNTHESIS_HANDOFF]`，只输出：`BLOCKED: NEED_SYNTHESIS_HANDOFF`
- 若 `[SYNTHESIS_HANDOFF]` 中缺少 `ready_for_review: yes`，只输出：`BLOCKED: NEED_SYNTHESIS_FIX`
- 若缺少 `[CLAIM_POOL]`、`[CITATION_POOL]`、`[TENSION_POOL]`、`[GAP_POOL]` 任一节，只输出：`BLOCKED: NEED_SYNTHESIS_REDO`
- 若 `gate_status` 不是 `clear`，只输出：`BLOCKED: NEED_SYNTHESIS_FIX`
- 若只有研究话题、没有结构化综合材料，不得直接成稿；只输出：`BLOCKED: NEED_SYNTHESIS_REDO`

### READ-GATE（开始前必须完成）

先打开：
- `references/draft-composition.md`
- `references/two-layer-consistency.md`

开始前必须能回答：
1. 成稿前必须锁定哪四个 pool？
2. 哪些脚手架必须从正文里删掉？
3. 证据不足时可以做什么，绝不能做什么？

答不出，先读文件，不得开始成稿。

### HARD FAIL

出现以下任一情况，禁止输出正文，只能修正；修不动就返回对应 `BLOCKED:*`：
- 新增上游没有的判断、引用、作者、年份、方法、数据、结果、政策事实
- 出现“本文”“本研究”“为解决上述问题”等贡献声明
- 出现“摘要”“引言”“绪论”“方法”“结果”“讨论”“结论”“总结”等论文结构标题
- 出现 `一、` / `二、` / `1.` / `第X章` 等编号标题或小节标题
- 保留导航段 / 本节文献 / 小结 / 表格 / 分点清单 / 范围说明
- 用“首先 / 其次 / 最后 / 此外 / 综上”主导正文推进
- 少于 3 段、多于 6 段，或正文可见长度不在 2000 字左右（可上下浮动）
- `gate_status != clear` 仍继续成稿

### ONLY OUTPUT

只输出 3-6 个连续自然段的综述正文。

不输出拟题、摘要、引言、总结、参考文献、过程说明、检查表、导航段、清单、范围说明。参考文献由最终报告的 `## 参考文献` 节统一承接，不在本阶段重复生成。

### OUTPUT CONTRACT

SELF-GATE 全部 PASS 后，创建 `.workflow/review_handoff.json`：

```json
{
  "stage": "review-writing",
  "read_gate": "pass",
  "self_gate": "pass",
  "draft_shape_checked": "pass",
  "ready_for_final": "yes"
}
```

在创建 handoff 前，必须先把正文写入 `.workflow/review_draft.md`，然后运行：

```bash
python scripts/check_review_draft.py --input .workflow/review_draft.md --write-report .workflow/review_draft_check.json
```

该脚本返回非 0 或 `status: fail` 时，不得创建 `review_handoff.json`，必须修正文稿后重跑。`draft_shape_checked` 只能来自该脚本通过，不得手写自称通过。

随后运行：

```bash
python scripts/workflow.py accept review-writing .workflow/review_handoff.json
```

accept 通过后进入 `document-delivery`，不得停在对话文本交付，也不得自行声称本次调研完成。

## 配套 reference

本文件只保留运行时合同。写作细则与完整检查项在以下文件中展开：

- 写作方法与中文综述文风、段落级正反例：`references/draft-composition.md`
- 双层一致性与边界核查的完整清单：`references/two-layer-consistency.md`

## 输入锁定

在内部锁定四类材料，不打印锁定表：

- `claim_pool`：上游已经给出的核心判断
- `citation_pool`：上游已经出现的作者-年份引用标识
- `tension_pool`：上游已经识别的争议、反证、条件差异
- `gap_pool`：上游已经识别的开放问题、局限、未来研究空白

正文只能从这四类材料生成。找不到依据的句子删除；必须保留但证据不足的判断加 `[证据不足]`。不得用模型记忆补背景或补事实。

## 成稿约束

- 默认输出中文连续正文，写成中文核心 / 硕博论文综述风格。
- 正文必须是 3-6 个自然段，2000 字左右（可上下浮动）；段落之间用空行分隔。
- 正文内部不设任何标题、小标题、拟题、摘要、引言、结论或总结。
- 每段围绕一个主题判断，不逐篇介绍论文。
- 引用服务判断，不堆在句尾凑数量。
- 文献充足时，在同一句或同一段中交叉比较多篇研究。
- 保留必要限定，避免把弱证据写成强结论。
- 结尾停在文献层面的未解问题，不滑向“本文将解决什么”。
- 本阶段只产连续综述正文段，绝不扩成 IMRaD 成品论文。

## SELF-GATE

输出前逐项比对；任一 FAIL，都不得输出正文：

| 检查项 | PASS 条件 | FAIL 动作 |
|---|---|---|
| Claim 边界 | 正文每条 claim 都在 `claim_pool` 中 | 删除越界 claim 或标 `[证据不足]` |
| Citation 边界 | 正文每个作者-年份引用都在 `citation_pool` 中 | 删除越界引用 |
| 引用格式 | 作者-年份夹注制：1 位写全、**2 位写全两个姓氏（中文"和"、英文叙述式 `and`/括注式 `&`，英文姓氏间禁夹中文"和"）**、≥3 位才用"等/et al."；不用 `[编号]`。**英文双作者误用中文"和"（如 `Smith 和 Jones（2020）`）会被 `check_review_draft.py`/`check_lark_doc.py` 硬拦 fail** | 按 `references/output-structure.md` 的"正文引用格式"改写 |
| 知识隔离 | 无上游没有的作者/年份/方法/数据/结果/政策事实 | 删除，不能用记忆补 |
| 贡献声明 | 无“本文/本研究/为解决上述问题” | 改写为“现有研究尚未…” |
| 脚手架残留 | 无导航段 / 本节文献 / 小结 / 表格 / 分点清单 / 范围说明 | 删除 |
| 形态边界 | 3-6 个自然段，2000 字左右，无标题/拟题/摘要/引言/总结 | 改写后重跑 `check_review_draft.py` |
| AI 痕迹 | 无空泛开头 / 模板连接词主导 / 逐篇摘要拼接 | 重写问题段落 |
| 证据不足标记 | 必要的 `[证据不足]` 未被删 | 恢复标记 |

任一 FAIL 时，内部按此格式记录并修正（不打印给用户）：

```
[SELF-GATE FAIL]
- 检查项: {检查项}
- 问题: {具体描述}
- 动作: {删除/改写/恢复}
```

全部 PASS → 才能输出正文。

## 与上游的衔接

`review-writing` 是 `research-synthesis` 的下游。`research-synthesis` 负责判断和证据，`review-writing` 只负责成稿。成稿时发现证据不足，不能自行补内容；只能降级措辞、标 `[证据不足]`，或返回 `BLOCKED: NEED_SYNTHESIS_FIX` / `BLOCKED: NEED_SYNTHESIS_REDO`。

在完整调研管线中，本阶段默认必经；`output_scope` 只裁调研结果层，不裁成稿参考层。只有用户明确说“不要综述正文、只要清单/只要某一节”，才跳过本阶段。

也可**独立调用**：用户若已持有一份结构化综合分析，且输入满足 `INPUT-GATE`，可直接成稿，不要求经过前两阶段。
