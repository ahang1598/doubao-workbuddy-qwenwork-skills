# 报告模式工作流

生成完整季度点评报告。定位是**解释性点评**，不是投资建议。交付物：对话中输出 report display 正文全文 + 附上飞书在线文档。最终对话不列中间产物清单。

**内部产物目录：** 所有工作文件必须写入 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/`。开始工作前先创建该目录；目录名就是约束：其中任何文件都不得在最终回复中展示、列出、上传、摘要或作为交付物。

**恢复入口文件：** 创建目录后立刻创建 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/00_RESUME_HERE__NEXT_STEP.md`。如果上下文压缩后继续工作，任何动作前必须先读取这个文件。每进入新阶段、写完源稿、运行 finalize 前后，都要更新它。该文件不得在最终回复中展示、摘要或提及。

恢复入口文件固定包含：

```markdown
# Resume Here

当前模式：报告模式
当前状态：____
禁止交付：____
下一步必须执行：____
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

**执行纪律：必须严格按本文件定义的阶段顺序执行，不得跳过、合并或压缩任何阶段。每个阶段的产出是下一阶段的输入前提——跳步会导致分析深度不足。**

## 目录

- 报告边界与工作流总览
- 阶段 0-2：初始化、公司研究、写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md`
- 阶段 3-5：取数、写作决策、定向补查
- 阶段 6-7：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md`、后处理、创建飞书文档与交付

---

## 报告的边界

正文每个论断只能是三类之一：
1. **数字驱动的解释**——用底稿数字拆解，只写结论数字，不暴露计算过程
2. **具名机构的转引**——「XX 机构（YYYY-MM-DD，出处）」
3. **「后续应关注 X」式的开放提示**——注明用什么公开数据验证

禁止：「我们认为/预计/判断」、自有评级、目标价、估值倍数。

---

## 工作流总览

```
阶段 0  初始化：加载配置与校准标准
阶段 1  公司研究：搜索公司信息与市场预期
阶段 2  写 _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md（事实性认知摘要）
阶段 3  广撒网取数 → _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json（含 claims）→ 门禁 1
阶段 4  写作决策 → _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md（含机制分析与当前深度）
阶段 5  定向补查 → 更新 _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json → 重跑门禁 1
阶段 6  写 _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md（含读者视角自查）
阶段 7  后处理与交付（只运行 finalize_report.py）
```

---

### 阶段 0：初始化

加载运行环境和质量标准，不做任何搜索。

1. 声明今天日期，不使用训练记忆中的数据。
2. 读 `market-profiles.md` 确定上市地档案（利润用语、币种、披露平台）。
3. 读 `industry-playbooks.md` + 命中的 playbook。
4. 读范例校准深度标准：
   - `exemplars/report-exemplar.md`
   - `exemplars/anti-patterns.md`

产出：除恢复入口文件状态更新外，无内容文件产出。执行者已加载所有配置，可以开始研究。

---

### 阶段 1：公司研究

带着阶段 0 加载的行业框架去搜索，目标是搜到足够信息来写 brief。第一轮最多搜索 5 次，预算用完后不得继续扩展性搜索。

1. 搜索：公司业务模式、近期动态、本季财报基本数据、市场讨论焦点。
2. **尽可能搜集各券商研报内容**——财报前的盈利预测、核心假设、关注点；财报后的点评与评级变动。目标是获得市场对该公司的一致预期和分歧点。

无法联网则终止并告知用户。

---

### 阶段 2：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md`

基于阶段 1 搜到的信息，产出事实性认知摘要。Brief 的定位是**记录你目前知道什么**，不是做分析判断。该文件是内部中间产物，不得在最终回复中提及或交付。

内容：
- **市场档案**：上市地、利润用语、币种
- **原型与收入函数**
- **5-8 个核心 KPI**
- **个本期市场关注点**（财报前市场真正在问的问题）——每个关注点写清楚：问题是什么、目前已知的信息有哪些、还缺什么信息。
- **市场预期摘要**：各指标一致预期（收入/利润/EPS，具名来源+日期）、核心假设分歧、券商关注的关键变量

这份 brief 和市场预期在阶段 4 写作决策时直接使用。

---

### 阶段 3：广撒网取数

按 `data-sources.md` 搜集，用 `facts-template.md` 填 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json`。默认先填 `claims`：正文、表格、图表和后续关注阈值中可能支撑结论的关键数字或关键事实判断，都应有独立 `claim_id`。只有需要复算同比/环比/预期偏离时，再补 `actual/history/consensus/guidance` 等完整报告块。

**取数纪律：**
- 三大报表数字必须来自定期报告原文或权威数据库
- 一致预期按指标分别记录（收入/利润/EPS 各自有锚或各自标 null）
- 媒体只能补充经营性事实和说明会叙述
- 表格中出现同比、环比、变化率、偏离等派生比例时，必须搜索找到支撑该比例的原始数据
- 同一指标跨期间必须拆成不同 claim，例如 `overseas_share_2024` 与 `overseas_share_2025`
- 券商研报、媒体、雪球/头条等二级来源中的判断不得登记为 `hard_fact`；只能登记为 `broker_estimate`、`market_view` 等，并在正文中保留「券商估算」「媒体报道」「市场讨论」这类限定语

**门禁 1：** `python3 scripts/check_facts.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 退出码 0。

---

### 阶段 4：写作决策

现在你手里有 brief（认知框架）和 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json`（完整数据），可以开始做分析判断了。

产出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md`（模板见 `analysis-moves.md`）：

1. **关注点机制分析**——回到 brief 的关注点，现在用 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 的数据做机制假设：
   - 每个关注点列出机制候选（≥2 条）
   - 标注当前深度
   - 写清「补到深度3还缺什么信息」和对应的取数方向

   示例：
   ```
   关注点 1：毛利率环比下降是否可持续？
     机制 A：产品结构切换（高成本新品占比提升）→ 当前深度：深度2 → 补到深度3还缺：上游供应商集中度、公司议价能力数据 → 取数方向：HBM 供需、封装产能分配
     机制 B：一次性成本（新产线爬坡）→ 当前深度：深度1 → 补到深度3还缺：产能利用率趋势、爬坡周期参考 → 取数方向：公司产能披露、同行爬坡经验
   ```

2. **主线**（本季唯一核心特征）→ 决定篇幅分配
3. **锚点清单**（逐指标：有锚/无锚。无锚 = 禁用「超/低于预期」）
4. **对质对筛选**（按 playbook 清单过，每对标注：展开/一句话通过/不适用。展开必须过重大性门槛）
5. **证据缺口清单**（已有/缺失但可得/缺失且不可得）
6. **条件件取舍**（机构观点是否成章、缺口测算是否触发、图表是否需要）

篇幅跟随内容——展开的对质有几组就写几组，不设配额也不设上限。没有值得展开的对质 = 这份报告不值得写，直接告诉用户「本季无重大新信息」即可。

---

### 阶段 5：定向补查

补查由两类缺口驱动：
1. **证据缺口**：writing-plan 中标注「缺失但可得」的证据
2. **深度缺口**：展开的对质对应的机制候选仍停在深度2以下——需要补查竞争格局、产业链位置、客户议价权等深度3所需信息

每个缺口最多 2 轮。典型对象：券商量价假设、同行可比数据、行业第三方数据、上下游供需格局。

补入 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 后重跑门禁 1。补不到的 → 对应结论降档。本阶段后不再回头搜索。

**终止条件**：所有拟展开的对质，其核心机制解释至少到达深度3（或因数据不可得而标注「单一解释」并降档措辞）。

---

### 阶段 6：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md`

读 `report-structure.md`（结构）、`analysis-moves.md`（动作写法）、`reasoning-framework.md`（推理标准）。

#### 写作核心原则

`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md` 是给读者的成品源稿，不是中间产物的整理稿。`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md` 和 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md` 是你的研究笔记和写作决策，读者永远不会看到它们。源稿必须用读者语言从零叙述。

1. **只写结论，不写过程。** brief 里列了三条可能解释、排除了两条——report 只保留经验证的解释作为论点。被排除的假设不出现，除非排除本身对读者理解有帮助（「不是 X 而是 Y」一句话带过）。
2. **禁止照搬中间产物的句式。** 如果源稿某段话和 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md` / `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md` 长得一样，或者只是把「解释 A：」换成了段落首句，退回去重写。
3. **章节标题必须是判断句，不是维度名。** 正确：`AI 商业化拐点确立，但利润率改善仍需验证`。错误：`AI 与云业务分析`、`关注点 1 回答`。
4. **每段的叙事结构是「现象→归因→约束→前瞻」，不是「假设 A/B/C→验证→结论」。** 读者要看因果故事，不是看你的研究日志。

#### 事实绑定规则

源稿应把支撑结论的正文数字、表格关键数字、后续关注阈值、关键事实判断绑定到 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 的 `claims`：

```markdown
国外销售占比从 2024 年的 53.49% 降至 2025 年的 49.44%。{fact:overseas_share_2024,overseas_share_2025}
有券商估算公司在该细分市场份额约 40%-45%，但公司年报未披露该口径。{fact:market_share_estimate}
```

- `{fact:...}` 绑定标记只存在于源稿，`finalize_report.py` 会在 display markdown 中自动转换成普通文本 `[n]` 来源标记，并按同一编号重写文末「数据来源」。源稿不要手写 `[n]` 或 `[^n]`。
- `{fact:...}` 只能引用 `claims[].claim_id`，不得引用 `other_facts.name` 或中文事实名。关键 `other_facts` 若要入正文，先补一条 `claims`；未知或非规范 fact 引用会导致 finalize 失败。
- 无法绑定到 `claims` 的数字，先判断是不是关键证据：是则回到阶段 3 或阶段 5 补 facts；不是则可保留，并在 lint 警告中复核。
- `usage_type=broker_estimate/broker_forecast/market_view/author_inference` 的 claim，正文必须用「券商估算/机构预计/市场讨论/可能指向」等限定语，不得写成确定事实。

#### 表述规范

- **引用**：文末「数据来源」编号列表，每条带可点击链接。
- **派生数字**：只写结论，不写中间计算过程。正确：`单季资本性支出约 267 亿元`。错误：`单季资本性支出约 267 亿元（94.1−(−173.0)）`。
- **环比**：直接写「环比 +X%」，不加括号注释上期基数。
- **内部标签**：深度0/深度1/深度2/深度3/深度4、当前深度、补到深度、机制候选、假设空间、结论分档、门禁、收入函数——这些严禁出现在正文中。直接写分析内容本身。

#### 读者视角自查（写完后立即执行）

以**对财报分析感兴趣但不了解你内部工作流的读者**身份通读全文，逐项检查：

1. **内部术语残留？** 搜索标签形态：深度0、深度1、深度2、深度3、深度4、当前深度、补到深度、机制候选、假设空间、结论分档、门禁、收入函数、brief。出现任何一个 = 必须改写。
2. **照搬中间产物？** 把 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md` 与 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md` 对照，如果某段的句式、措辞、结构与 brief 高度雷同，用读者能理解的因果叙事重写。
3. **像分析文章还是像填模板？** 如果某段读起来是「标签：内容」的格式，改为连贯叙述。
4. **措辞强度与证据匹配？** 没有充分证据的结论不应使用确定性表述。
5. **正文关键数字与 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` / check_facts 输出一致？** 核心证据数字是否有 `{fact:claim_id}`；是否错误引用了 `other_facts.name`；`usage_type` 与正文语气是否匹配，例如券商估算、媒体报道、作者推断是否保留了限定语。若 lint 输出「来源/语气复核」并给出「建议改写」，除非能明确判断为误报，否则按建议改写或补充等价限制语。
6. **展开的对质真过了门槛？没有删掉后不影响主线理解的段落？**
7. **三个关注点都交代了裁决状态？**

发现问题 → 修改 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md`，改完再进入阶段 7。

写完源稿并完成自查后，必须更新 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/00_RESUME_HERE__NEXT_STEP.md`：

```markdown
当前状态：源稿已完成自查，但尚未生成最终正文。
禁止交付：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md（含 {fact:...} 审计标记）
下一步必须执行：python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

---

### 阶段 7：后处理与交付

依次执行以下步骤，全部完成才算交付：

**步骤 1：后处理并生成飞书文档源稿**

只运行下面这一条命令。不要拆开运行 `make_display_markdown.py` 或 `normalize_report.py` 来完成交付；这些脚本是 `finalize_report.py` 的内部 helper。不要默认运行 `make_docx.py`，除非用户明确要求 Word/DOCX 导出。`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 是把内部 `{fact:...}` 绑定转换为 `[n]` 来源标记后的飞书文档源稿，不是交付物文件。

```bash
python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

该命令会规范化 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md`、重跑 `check_facts.py`、运行 lint 门禁 2，再生成无 `{fact:...}` 标记的 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md`。`finalize_report.py` 退出码必须为 0。若事实门禁或 lint 硬错误失败，脚本会中止，不生成新的 display markdown；事实绑定、期间和来源语气类提示通常是警告，需要在阶段 6 的读者视角自查中由模型复核是否修改。命令成功但仍有 warning 时，不得直接忽略：误报可放行；真实的期间、来源语气或建议改写问题必须修改后重跑 finalize。

finalize 成功后，必须更新恢复入口文件：

```markdown
当前状态：FINAL_REPLY_BODY.md 已生成，下一步是创建飞书文档并输出正文。
禁止交付：所有 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/` 路径和文件名；尤其禁止输出 DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md。
下一步必须执行：用 FINAL_REPLY_BODY.md 的全文创建飞书在线文档，然后在最终回复中先输出固定风险提示语，再粘贴 FINAL_REPLY_BODY.md 正文内容，最后附飞书文档。
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

**步骤 2：调用内置能力创建飞书文档**

调用内置飞书文档/云文档能力，以 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 的全文作为正文创建飞书在线文档。触发时明确表达：

> 请使用飞书文档/云文档创建能力，将以下 markdown 内容创建为飞书在线文档，并附上创建好的飞书文档。

飞书文档的内容质量标准与 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md` 完全一致——它是正式交付物，不是简化版。Display markdown 是飞书文档的创建源：把内部 `{fact:...}` 绑定转换成普通文本 `[n]` 来源标记，保留文末数据来源和未获取清单。

**步骤 3：对话输出**

最终对话回复必须先输出固定风险提示语「回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。」；再原样输出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 的全文内容；最后附上飞书文档。可以输出报告正文和其中的核心结论，但不得输出中间文件名、路径或文件清单。

**注意：这一步是「固定风险提示语 + 复制 display 正文 + 附上飞书文档」，不是「列出文件」。** 不得输出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.md`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 的文件名、路径或下载说明；不得输出 brief、writing-plan、facts、source markdown 的内容或摘要；但必须输出 display markdown 的正文内容本身。

最终回复固定格式：

```text
回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。

<display markdown 全文>

飞书文档：<附上的飞书文档>
```
