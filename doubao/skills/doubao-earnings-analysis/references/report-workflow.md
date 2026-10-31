# 报告模式工作流

生成完整季度点评报告。定位是**解释性点评**，不是投资建议。交付物：文本框简短作答 + 独立 HTML 报告（优先发布为飞书妙搭 HTML 页面）。最终对话不粘贴报告全文。

**内部产物目录：** 所有工作文件必须写入 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/`。开始工作前先创建该目录；目录名就是约束：其中任何文件都不得在最终回复中展示、列出、上传、摘要或作为交付物。

**恢复入口文件：** 创建目录后立刻创建 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/00_RESUME_HERE__NEXT_STEP.md`。如果上下文压缩后继续工作，任何动作前必须先读取这个文件。每进入新阶段、写完源稿、运行 finalize 前后，都要更新它。该文件不得在最终回复中展示、摘要或提及。

恢复入口文件固定包含：

```markdown
# Resume Here

当前模式：报告模式
当前状态：____
禁止交付：____
下一步必须执行：____
最终源稿：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html
最终页面来源：FINAL_REPORT_HTML/index.html
```

**执行纪律：必须严格按本文件定义的阶段顺序执行，不得跳过、合并或压缩任何阶段。每个阶段的产出是下一阶段的输入前提——跳步会导致分析深度不足。**

## 目录

- 报告边界与工作流总览
- 阶段 0-2：初始化、公司研究、写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md`
- 阶段 3-5：取数、写作决策、定向补查
- 阶段 6-7：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html`、HTML 核验与交付

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
阶段 6  写 _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html（含读者视角自查）
阶段 7  HTML 核验与交付（只运行 finalize_html_report.py）
```

---

### 阶段 0：初始化

加载运行环境和质量标准，不做任何搜索。

1. 声明今天日期，不使用训练记忆中的数据。
2. 读 `market-profiles.md` 确定上市地档案（利润用语、币种、披露平台）。
3. 读 `industry-playbooks.md` + 命中的 playbook。
4. 记录本次适用的市场口径和行业原型。范例留到写正文前再读。

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

### 阶段 6：写 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html`

读 `report-structure.md`（内容结构）、`analysis-moves.md`（动作写法）和 `exemplars/report-exemplar.md`（成品质量）；范例的 Markdown 排版不作为 HTML 模板。此时再读 `html-style.md`，复制 `assets/report-starter.html` 的视觉外壳为 HTML 源稿，按本工作流原有的内容要求编写正文。`assets/report-layout-preview.html` 仅供查看可选组件，不规定章节、顺序或组件数量。不要另起一套空白 CSS。遇到对应的旧问题时读 `exemplars/anti-patterns.md`；推理卡住时才读 `reasoning-framework.md`。

组织数据呈现时，检查事实表中是否有多期趋势、业务结构或同口径横向对比；如果画图能让关键关系更快被看懂，按 `html-style.md` 用已核验的数据制作图表，并在图后解释它支持什么判断。图表是可选的表达方式，不增加分析章节要求。

#### 写作核心原则

`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html` 是给读者的成品源稿，不是中间产物的整理稿。`_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md` 和 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md` 是你的研究笔记和写作决策，读者永远不会看到它们。源稿必须用读者语言从零叙述。

1. **只写结论，不写过程。** brief 里列了三条可能解释、排除了两条——report 只保留经验证的解释作为论点。被排除的假设不出现，除非排除本身对读者理解有帮助（「不是 X 而是 Y」一句话带过）。
2. **禁止照搬中间产物的句式。** 如果源稿某段话和 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md` / `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__writing-plan.md` 长得一样，或者只是把「解释 A：」换成了段落首句，退回去重写。
3. **章节标题必须是判断句，不是维度名。** 正确：`AI 商业化拐点确立，但利润率改善仍需验证`。错误：`AI 与云业务分析`、`关注点 1 回答`。
4. **每段的叙事结构是「现象→归因→约束→前瞻」，不是「假设 A/B/C→验证→结论」。** 读者要看因果故事，不是看你的研究日志。

#### 事实绑定规则

HTML 源稿应把支撑结论的正文数字、表格关键数字、后续关注阈值、关键事实判断绑定到 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` 的 `claims`：

```html
<p>国外销售占比从 2024 年的 53.49% 降至 2025 年的 49.44%。{fact:overseas_share_2024,overseas_share_2025}</p>
<p>有券商估算公司在该细分市场份额约 40%-45%，但公司年报未披露该口径。{fact:market_share_estimate}</p>
```

- `{fact:...}` 绑定标记只存在于源稿，`finalize_html_report.py` 会转换成可点击 `[n]` 来源标记，并按同一编号生成「数据来源」。源稿不要手写 `[n]` 或 `[^n]`。
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
2. **照搬中间产物？** 把 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html` 与 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__company-brief.md` 对照，如果某段的句式、措辞、结构与 brief 高度雷同，用读者能理解的因果叙事重写。
3. **像分析文章还是像填模板？** 如果某段读起来是「标签：内容」的格式，改为连贯叙述。
4. **措辞强度与证据匹配？** 没有充分证据的结论不应使用确定性表述。
5. **正文关键数字与 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json` / check_facts 输出一致？** 核心证据数字是否有 `{fact:claim_id}`；是否错误引用了 `other_facts.name`；`usage_type` 与正文语气是否匹配，例如券商估算、媒体报道、作者推断是否保留了限定语。若 lint 输出「来源/语气复核」并给出「建议改写」，除非能明确判断为误报，否则按建议改写或补充等价限制语。
6. **展开的对质真过了门槛？没有删掉后不影响主线理解的段落？**
7. **三个关注点都交代了裁决状态？**

发现问题 → 修改 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html`，改完再进入阶段 7。

写完 HTML 源稿并完成自查后，必须更新 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/00_RESUME_HERE__NEXT_STEP.md`：

```text
当前状态：HTML 源稿已完成自查，但尚未生成最终页面。
禁止交付：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html（含 {fact:...} 审计标记）
下一步必须执行：运行 python3 scripts/finalize_html_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --output FINAL_REPORT_HTML/index.html
最终源稿：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html
最终页面来源：FINAL_REPORT_HTML/index.html
```
---

### 阶段 7：HTML 核验与交付

1. 只运行下面这一个默认交付入口：它核验事实表，对 HTML 可见文字运行原有 lint，并把 `{fact:...}` 转为可点击来源标记。失败时修正源稿后重跑。不要默认导出 DOCX。

```bash
python3 scripts/finalize_html_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__report-source.html _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --output FINAL_REPORT_HTML/index.html
```

2. 打开 `FINAL_REPORT_HTML/index.html`，按 `html-style.md` 在桌面和手机宽度做读者视角检查：首屏有明确判断，正文与数据易读，文末来源链接和风险提示可见；不得出现 `{fact:...}`、`【...】` 占位符、空组件或内部文件名。实际采用的组件须包含有效内容，不为凑版式重复数字。若有图表，确认它们在独立 HTML 中可见。HTML 才是完整报告，不得用简短回答替代。
3. 优先使用可用的飞书妙搭 HTML 发布能力发布 `FINAL_REPORT_HTML/index.html`，并取得可访问链接。若当前环境不支持 HTML 发布，直接附上该 HTML 文件并说明尚未发布。不要创建飞书云文档来替代 HTML。
4. 最终文本框先放固定风险提示语，再用 2-4 句话概括主结论、1-2 个关键证据和最重要的判断局限，最后给 HTML 链接或附件。不要粘贴完整报告，也不要列中间产物。文本框中出现的数字也必须来自事实表并与 HTML 一致。

最终回复示例：

```text
回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。

[2-4 句话直接回答，含关键证据与局限。]

完整分析（HTML）：<页面链接或 HTML 附件>
```
