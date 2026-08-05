# 聚焦分析模式工作流

对用户的具体财报问题给出深度回答，并通过 **`python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 生成飞书文档源稿，再调用内置飞书文档/云文档能力创建飞书在线文档**。

**内部产物目录：** 所有工作文件必须写入 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/`。开始工作前先创建该目录；目录名就是约束：其中任何文件都不得在最终回复中展示、列出、上传、摘要或作为交付物。

**恢复入口文件：** 创建目录后立刻创建 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/00_RESUME_HERE__NEXT_STEP.md`。如果上下文压缩后继续工作，任何动作前必须先读取这个文件。每进入新步骤、写完源稿、运行 finalize 前后，都要更新它。该文件不得在最终回复中展示、摘要或提及。

恢复入口文件固定包含：

```markdown
# Resume Here

当前模式：聚焦模式
当前状态：____
禁止交付：____
下一步必须执行：____
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

**执行纪律：必须严格按本文件定义的阶段顺序执行，不得跳过、合并或压缩任何阶段。每个阶段的产出是下一阶段的输入前提——跳步会导致分析深度不足。**

## 目录

- 第一步到第二步：搜索了解公司，写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md`
- 第三步：定向取数、写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json`、推进因果推理
- 第四步到第五步：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md`，转成读者正文
- 第六步到第八步：自查、后处理、对话输出

---

## 第一步：搜索了解公司

读 `industry-playbooks.md` 确定原型，再读命中的 `playbooks/*.md`。读 `market-profiles.md` 确定口径。读范例 `exemplars/focused-exemplar.md`——校准深度标准和最终产出形态。

然后搜索：公司基本面、本季财报数据、近期动态。第一轮最多搜索 5 次；目标是在预算内形成足够写 brief 的基本认知，预算用完后不得继续扩展性搜索。

---

## 第二步：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md`（基于搜索结果）

**基于第一步搜到的信息，写出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md` 文件。** 这是强制落地的内部中间产物，不写出来不得进入下一步。文件路径包含 `DO_NOT_DELIVER`，不得在最终回复中提及或交付。

**Brief 是活文档**：第三步取数过程中如果发现新假设或需要调整判断，必须回来更新 brief（规则见第三步）。Brief 的价值不仅是「计划」，更是「思维轨迹的诚实记录」。

它分两层：

### A. 内核（这家公司的核心叙事逻辑）

1. **市场档案**：上市地、利润用语、币种
2. **原型与收入函数**：收入怎么产生的（出货量×ASP / GMV×take rate / …）
3. **核心 KPI**（3-5 个，与问题最相关的）
4. **市场关注点（本问题）**：用户问的具体问题 + 隐含矛盾（「放在一起不舒服」的那对数字/现象）

### B. 聚焦叠加（本模式特有）

5. **问题相关的拆分维度**：基于收入函数 + 具体问题，确定怎么拆。例：
   - 收入环比问题 + 产品型 → 量×价拆分验证
   - 毛利率问题 + 产品型 → 成本增速 vs 收入增速 → 再拆到产品结构
   - 利润问题 + 订阅型 → 费用率（销售/研发/管理）哪个在动
6. **同行表现**：跟谁比 + 同行表现如何，是否有差异（同行信息很多时候可以提供「是否合理的判断」）
7. **机制候选 ≥3 条**（确保假设空间够宽：除了显而易见的业务因素，还要想过口径变化、会计重分类、一次性项目、并表变化、备货节奏差异等）。假设列表全是卖方快评会写的东西 = 假设空间不够宽，退回重列。
8. **每条机制候选标注当前深度**（深度1/深度2/深度3），以及「补到深度3还缺什么信息」。这是第三步定向搜索的直接 trigger——你搜什么取决于你在哪条假设的哪个深度卡住了。

示例：
```
机制 A：B 产品占比提升 → 当前深度：深度2（知道占比在升、成本结构更重）→ 补到深度3还缺：上游 HBM 供应商集中度数据 + 公司在封装产能分配中的优先级 → 定向搜索方向：HBM 供需格局、先进封装产能分配
机制 B：上游涨价 → 当前深度：深度1（公司提了「产能紧张」）→ 补到深度3还缺：为什么不能切换/自建 → 定向搜索方向：代工供应商可选范围、切换成本
机制 C：收入确认口径变化 → 当前深度：深度1（未排除）→ 搜索方向：对比上期营业成本构成是否有新增项
```

这份 brief 决定后续该定向搜什么、怎么拆、跟谁比、验证哪些假设。**第三步不是漫无目的地搜索，而是逐条把机制候选从当前深度补到深度3。**

---

## 第三步：定向取数 + 写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` + 推理

由 brief 中每条机制候选的「当前深度」和「补到深度3缺什么」驱动定向搜索。循环：拿数据 → 尝试解释 → 判断到了哪个深度 → 没到深度3则定向补查 → 继续推理。当所有保留的机制候选都至少到达深度3（或因数据不可得而标注「单一解释」），本步骤结束。

**必须同步写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json`，不写 facts 不得进入下一步。** 读 `facts-template.md`，把可能支撑正文结论的关键数字和关键判断登记到 `claims`。每条 claim 只需要写清：

- `claim_id`
- `text`
- `source`
- `url`（没有公开链接时可省略）
- `usage_type`

`usage_type` 控制正文语气：

- 定期报告/公告数字：`hard_fact`
- 公司新闻/管理层表述：`company_statement` 或 `management_guidance`
- 券商研报/一致预期/市占率估算：`broker_estimate` 或 `broker_forecast`
- 雪球/头条/论坛/媒体讨论：只能作为 `market_view` 线索，不能支撑硬事实
- 作者计算值：`usage_type:"author_calculation"`，`calculation` 必填

**Brief 更新规则（取数过程中触发）：**

研究过程中出现以下情况时，必须回到 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md` 更新：

1. **发现新假设**：搜索中出现了 brief 未列出的机制解释 → 追加到机制候选列表，标注 `[新增于取数阶段]` + 当前深度 + 补查缺口。
2. **拆分维度需要调整**：原定的拆分路径走不通或数据揭示了更好的拆法 → 更新第 5 条，保留原拆分并标注「已替换」及原因。
3. **假设被排除**：某条机制候选被证据明确否定 → 不得删除，在原条目后追加 `→ 已排除：[排除依据]`。

**禁止操作：**
- 不得删除任何已写入的机制候选（只能标注状态变化）
- 不得在无新证据的情况下降低某条假设的优先级

Brief 的修改痕迹本身就是分析诚实性的证明——它记录了「你以为是什么 → 实际发现了什么」的认知演变。

**取数纪律：**
- 三大报表数字来自定期报告原文，不用媒体转引
- 每个数字标来源和日期
- 结构占比类数据用券商测算区间值（如「40%-45%，券商甲 2026-04-12」），禁止用媒体精确点位
- 预期锚需具名来源+日期；无锚则声明
- 每个方向最多 3 轮搜索，找不到就停
- 同一指标跨期间必须分成不同 claim：例如 `overseas_share_2024` 和 `overseas_share_2025`，不得用旧期间数字代表当前期间
- 二级来源中的判断不得登记为 `hard_fact`；正文只能写成「券商估算/媒体报道/市场讨论」

**事实门禁：**

```bash
python3 scripts/check_facts.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json
```

退出码必须为 0；若失败，修正 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 后重跑。

**推理沿深度1→深度4推进，每个论证维度至少推到深度3：**
- 深度1｜定位：哪个科目在动
- 深度2｜归因：什么业务活动驱动了它
- 深度3｜约束：为什么公司不能消解这个变化（竞争格局、产业链位置、客户议价权等）
- 深度4｜前瞻：结构性还是暂时性 + 证伪条件

**深度3是聚焦模式的底线，不是可选项。** 读者会根据你的论证做投资判断。停在深度2 = 你只说了「成本涨了」但没说「为什么公司无力转嫁」，读者无法评估这件事的严重性。每个独立论证维度都必须回答「为什么公司在这个维度上受制」——这才构成对公司能力边界的判断。

每层：分解 → 列竞争性假设 → 找区分证据。遇到卡点查阅 `reasoning-framework.md`（三步循环、陷阱速查）。

**何时停：**
- 解释有公司数据直接验证 → 停
- 只有一种解释无法验证 → 按「单一解释」档位处理
- 推不下去且搜不到 → 在「数据局限」中说明影响

---

## 第四步：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md`（把底稿转成读者主线）

动笔前：回到 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md` 的机制候选清单（含取数阶段新增的），每条标注最终状态：已验证/已排除/证据不足。检查：
- 原始候选中凭空消失的（既没标「已排除」也没标「证据不足」）= 你偷懒了，退回去
- 取数阶段新增的假设也必须有最终状态——不能「加了但没跟进」
- 每条主线的核心证据数字应能对应到 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 的 `claims.claim_id`；不能对应的，先判断是不是关键证据：是则补 claim，不是则在自查中放行

**基于更新后的 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md`，写出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md` 文件。** 这是强制落地的内部中间产物，不写出来不得进入下一步。它的作用不是继续列机制，而是把研究底稿重组为读者能顺着读的 2-4 条主线。不得在最终回复中提及或交付该文件。

`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md` 固定使用以下结构：

```markdown
# 成文大纲

## 一句话答案
[直接回答用户问题，不超过 2 句。只写结论和关键判据。]

## 主线重组

### 主线 1：[读者问题式标题]
- 合并哪些机制候选：____
- 核心数字：____
- 对应 claim_id：____
- 因果链：现象 → 业务原因 → 公司受制因素 → 对用户问题的裁决
- 正文中不出现的底稿内容：____

### 主线 2：[读者问题式标题]
- 合并哪些机制候选：____
- 核心数字：____
- 对应 claim_id：____
- 因果链：现象 → 业务原因 → 公司受制因素 → 对用户问题的裁决
- 正文中不出现的底稿内容：____

## 证据强度转写
- 已证明：正文写成「有管理层说明和分项数据共同支撑」，不写「已证明/已证实」
- 合理推断：正文写成「与数据方向一致，但缺少公司精确拆分」，不写「合理推断」
- 单一解释：正文写成「只能作为一种可能解释，后续看 X 区分」，不写「单一解释」

## 篇幅取舍
- 主写：____
- 一句话带过：____
- 放入数据局限：____
- 删除不写：____

## 正文禁用句式
- 机制一/机制二/机制 A
- 现象描述
- 具体表现
- 为什么公司不能消解这个变化
- 结论：已证实/合理推断/单一解释
```

**合并原则：**
- 不按机制数量成节，按读者理解问题的顺序成节。
- 多个机制指向同一个读者问题时，合并为一条主线；低影响因素并入一句话、数据局限或删除。
- 主线标题必须是判断句或读者问题式标题，不得写「机制一」「因素分析」「原因拆解」。
- `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md` 可以出现内部词，因为它不是成品；下一步正文不得照抄它的字段名。

---

## 第五步：写答案

只能基于 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md` 写正文。`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md` 是研究底稿，不是正文模板；不得把机制候选逐条搬进正文。正文源稿固定写入 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md`，不得写成 `analysis.md` 或其他看起来可交付的文件名。

**事实绑定要求：** 源 markdown 中，支撑结论的正文数字、表格关键数字、后续关注阈值、关键事实判断应在句末或表格行末绑定 `{fact:claim_id}`。多个事实写 `{fact:id1,id2}`。这些 `{fact:...}` 标记只给 lint 使用，最终 display markdown 和飞书文档会自动转换成普通文本 `[n]` 来源标记。`{fact:...}` 只能引用 `claims[].claim_id`，不得引用 `other_facts.name` 或中文事实名；关键 `other_facts` 若要入正文，先补一条 `claims`。`{fact:...}` 不是数值占位符，不会自动输出 claim 内容；禁止写 `自由现金流为{fact:fcf_2026}`、`资本开支达{fact:capex_2026}` 或表格单元格只写 `{fact:capex_2026}`。必须先在正文写出完整数值/判断，再绑定来源，例如 `资本开支达 1,263.79 亿元，同比增长 47%。{fact:capex_2026}`。源稿不要手写 `[n]` 或 `[^n]` 这类脚注角标；所有引用来源由 finalize 按 facts 的 `claims[].source/url` 写入文末「数据来源」。无法绑定到 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 的 `claims` 的数字，如果是关键证据就回到第三步补 claim；如果只是年份、序号、时间窗口或非证据性表述，可保留，并在 lint 警告中复核。未知或非规范 fact 引用会导致 finalize 失败。

示例：

```markdown
国外销售占比从 2024 年的 53.49% 降至 2025 年的 49.44%。{fact:overseas_share_2024,overseas_share_2025}
有券商估算公司在该细分市场份额约 40%-45%，但公司年报未披露该口径。{fact:market_share_estimate}
```

**输出结构：**

```
# [公司 + 问题结论型标题]

## [结论 + 关键判据]

[一句话核心逻辑]

---

## 1. [维度 A]
[数字 → 拆分 → 业务原因 → 公司为什么受制于此，对公司的经营健康是否有影响]

## 2. [维度 B]
[…同上，每个维度都要回答公司为什么受制于此]

## 3. [前瞻判断]
[趋势性 vs 暂时性 + 依据]

---

## 数据局限
- [什么拆分拿不到 + 影响哪个判断]

## 后续关注
1. **[指标 + 阈值]**（时间窗口）——达到则说明 X；未达到则需重新审视 Y

## 数据来源
1. [来源名，日期]

### 风险提示与免责声明
```

**写法要求：**
- 全文只能有一个 `#` 标题，写「公司 + 用户问题 + 核心结论」，例如 `# XX 公司毛利率下降不是经营恶化，关键看 B 产品放量后的单位毛利修复`。
- `## [结论 + 关键判据]` 保留原来的开头结论块，不只是「回答是/否」。
- 每个论证维度来自 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md` 的主线重组，而不是来自 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md` 的机制候选编号
- 每个论证维度独立成节，一段只讲一个逻辑环节
- **每个论证维度必须言之有物：有数据拆分 → 有业务原因 → 有公司受制因素。** 「数据罗列」不是论证——如果你只写了「收入 X 亿、同比 +Y%、毛利率 Z%」然后就跳到下一个维度，你没有在分析，你在复述。每个维度的核心是回答「为什么是这样，以及公司能不能改变它」。
- **正文中至少包含一个数据表格。** 分析过程中必然涉及数据变化、对比或矛盾——用表格将关键数据结构化呈现，让读者一眼看到「数字之间的关系」。表格的具体位置和内容由你根据分析逻辑自行决定，常见用法包括但不限于：多期指标对比（呈现趋势）、拆分维度的量化展示（呈现结构）、同行横向对比（呈现差异）、假设验证的证据汇总（呈现矛盾或一致性）。表格应服务于论证，不是装饰——如果表格删掉后读者不损失信息，换一个位置或换一种呈现方式。
- 源稿不要手写来源角标；finalize 会由 `{fact:claim_id}` 自动生成正文 `[n]` 和文末对应来源
- 正文源稿必须保留 `{fact:claim_id}` 直到运行 finalize；不要手动删除
- 结论强度通过措辞自然传达，不暴露内部术语
- **内部推理标签只存在于你的思考过程中，严禁出现在正文。** 包括但不限于：深度0/深度1/深度2/深度3/深度4、当前深度、补到深度、机制候选、假设空间、结论分档、门禁、收入函数。正文直接写分析内容本身，不加任何框架标签。例：不写「深度3｜约束：苹果丧失议价特权」，直接写「苹果已丧失议价特权，因为……」
- **底稿句式严禁出现在正文。** 不写「机制一/机制二」「现象描述」「具体表现」「为什么公司不能消解这个变化」「结论：已证实/合理推断/单一解释」。这些只能存在于底稿或大纲，正文要改成自然叙述。
- 语气：像懂行的朋友在解释，不是在填模板
- 派生数字只写结论，不写中间计算步骤（如 `1,964.58÷1,980−1`）。读者只需要知道结果。
- 环比直接写「环比 +X%」，不加括号注释上期基数（如 `vs Q3 的 XXX 亿元`）。
- 论证维度的 `##` 标题带序号（`## 1. xxx`），辅助章节（数据局限/后续关注/数据来源）使用不带序号的 `##`；文末风险提示使用 `### 风险提示与免责声明`。

**范例：** `exemplars/focused-exemplar.md`

---

## 第六步：读者视角自查（创建飞书文档前必做）

创建飞书文档前，以**对财报分析感兴趣但不了解你内部工作流的读者**身份通读全文，逐段检查：

1. **是否有内部术语残留？** 搜索以下标签形态：深度0、深度1、深度2、深度3、深度4、当前深度、补到深度、机制候选、假设空间、结论分档、门禁、收入函数、brief。出现任何一个 = 必须改写为自然语言。
2. **是否有底稿句式残留？** 搜索：机制一、机制二、机制 A、现象描述、具体表现、为什么公司不能消解、结论：已证实、结论：合理推断、结论：单一解释。出现任何一个 = 必须改写为自然语言。
3. **每个段落读起来像分析文章，还是像在填框架模板？** 如果某段读起来是「标签：内容」的格式，改为连贯的分析叙述。
4. **措辞强度是否与证据匹配？** 没有充分证据的结论不应使用确定性表述。
5. **事实绑定警告是否已复核？** 核心证据数字、表格关键行、支撑性判断是否有 `{fact:claim_id}`；是否错误引用了 `other_facts.name`；未绑定的数字是否确认为非关键证据；券商/媒体/作者推断是否用了限定语。若 lint 输出「来源/语气复核」并给出「建议改写」，除非能明确判断为误报，否则按建议改写或补充等价限制语。

发现问题 → 修改后再进入下一步。

完成自查后，必须更新 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/00_RESUME_HERE__NEXT_STEP.md`：

```markdown
当前状态：源稿已完成自查，但尚未生成最终正文。
禁止交付：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md（含 {fact:...} 审计标记）
下一步必须执行：python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

---

## 第七步：后处理并创建飞书文档（不可跳过）

先只运行下面这一条命令。不要拆开运行 `make_display_markdown.py` 或 `normalize_report.py` 来完成交付；这些脚本是 `finalize_report.py` 的内部 helper。不要默认运行 `make_docx.py`，除非用户明确要求 Word/DOCX 导出。

```bash
python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

该命令会规范化源 markdown、重跑 `check_facts.py`、运行 lint，再生成无 `{fact:...}` 标记的 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md`。若命令成功但仍有 warning，先复核 warning：误报可忽略；真实的期间、来源语气或建议改写问题必须修改后重跑 finalize。

finalize 成功后，必须更新恢复入口文件：

```markdown
当前状态：FINAL_REPLY_BODY.md 已生成，下一步是创建飞书文档并输出正文。
禁止交付：所有 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/` 路径和文件名；尤其禁止输出 DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md。
下一步必须执行：用 FINAL_REPLY_BODY.md 的全文创建飞书在线文档，然后在最终回复中先粘贴 FINAL_REPLY_BODY.md 正文内容，再附飞书文档。
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

然后调用豆包 App 内置飞书文档/云文档能力，以 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 的全文作为正文创建飞书在线文档。触发时明确表达：

> 请使用飞书文档/云文档创建能力，将以下 markdown 内容创建为飞书在线文档，并附上创建好的飞书文档。

**此步骤为必须执行的最终动作。** 未生成 display markdown 或未附上飞书文档 = 未完成交付。

飞书文档的内容质量标准与源 markdown 完全一致——它是正式交付物，不是简化版。Display markdown 是飞书文档的创建源：把内部 `{fact:...}` 绑定转换成普通文本 `[n]` 来源标记，保留文末数据来源和未获取清单。

---

## 第八步：对话输出（第七步之后执行）

最终对话回复必须先输出固定风险提示语「回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。」；再原样输出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 的全文内容；最后附上飞书文档。可以输出分析正文和其中的核心结论，但不得输出中间文件名、路径或文件清单。

**注意：这一步是「固定风险提示语 + 复制 display 正文 + 附上飞书文档」，不是「列出文件」。** 不得输出 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__analysis-brief.md`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__reader-outline.md`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__analysis-source.md`、`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md` 的文件名、路径或下载说明；不得输出 brief、outline、facts、source markdown 的内容或摘要；但必须输出 display markdown 的正文内容本身。

最终回复固定格式：

```text
回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。

<display markdown 全文>

飞书文档：<附上的飞书文档>
```
