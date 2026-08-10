# 交付流程：内部产物 → 门禁 → display markdown → 飞书文档

本节是"呈现渲染"（`output-rendering.md`）和"数据分级与引用"（`data-grading-and-citation.md`）之间的粘合层，也是**执行纪律**本身——照抄本节定义的阶段顺序和门禁，不要因为"已经把分析想清楚了"就跳过中间产物直接写最终回复。跳步是这个 Skill 最容易失败的地方：分析可以做得很好，但如果不落地成事实表、不跑门禁，最终交付就会缺来源、缺免责声明，或者带着未经查验的语气问题直接发给用户。

---

## 一、内部产物目录与恢复入口文件（必须最先创建）

任务一开始、还没做任何检索之前，先创建内部产物目录：

```
_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/
```

目录名本身就是约束：**其中任何文件都不是交付物**，不得在最终回复中展示、列出、上传、摘要或提及。典型文件：

```
_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/
├── 00_RESUME_HERE__NEXT_STEP.md          # 恢复入口文件，见下
├── DO_NOT_DELIVER__facts.json            # 事实表
├── DO_NOT_DELIVER__NEEDS_FINALIZE__source.md   # 源稿（含 {fact:...} 绑定）
├── charts/                                # render_charts.py 生成的图表 PNG
└── FINAL_REPLY_BODY.md                    # finalize_report.py 的输出（display markdown）
```

创建目录后**立刻**创建恢复入口文件 `00_RESUME_HERE__NEXT_STEP.md`，并在此后每进入新阶段、写完源稿、跑完门禁前后都更新它。如果上下文被压缩后需要继续任务，任何动作之前必须先读取这个文件，按里面记录的"下一步必须执行"续接，不要凭记忆重新开始。这个文件本身也是内部产物，不得在最终回复中展示或提及。

固定模板：

```markdown
# Resume Here

当前模式：单条深度解读 / 批量监控摘要
当前状态：____
禁止交付：____
下一步必须执行：____
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

**执行纪律：必须按下面第二节定义的阶段顺序执行，不得跳过、合并或压缩任何阶段。每个阶段的产出是下一阶段的输入前提——跳步会导致分析深度不足或交付缺陷。**

---

## 二、阶段总览

```
阶段 1  检索取证（按 SKILL.md 第三步 + linked-signals.md）
阶段 2  写事实表 DO_NOT_DELIVER__facts.json（含 claims）
阶段 3  按命中的 playbook 写源稿 DO_NOT_DELIVER__NEEDS_FINALIZE__source.md（含 {fact:claim_id} 绑定 + 图表 + 数据来源/风险提示骨架）
阶段 4  跑 scripts/finalize_report.py → 门禁 1（facts）+ 门禁 2（lint）→ 生成 FINAL_REPLY_BODY.md
阶段 5  创建飞书文档 + 对话输出（固定三段式）
```

---

## 三、阶段 2：写事实表

按 `facts-template.md` 填 `DO_NOT_DELIVER__facts.json`。正文、表格、后续关注阈值中可能支撑结论的关键数字或关键事实判断，都应有独立 `claim_id`。

取数纪律：
- 公司公告原文的数字必须来自取证到的原文，不得凭印象转述。
- 互动平台回复视为官方表态但不是正式公告，登记为 `hard_fact` 时如实标来源为互动平台。
- 券商研报、媒体、投资者评论区（同花顺/东方财富/雪球/头条等）中的判断不得登记为 `hard_fact`，只能登记为 `broker_estimate`、`market_view` 等，并在正文中保留「券商估算」「媒体报道」「投资者评论区讨论」这类限定语。

**不要单独跑 `scripts/check_facts.py`。** 它是 `finalize_report.py` 的内部 helper；单独跑只会多一次脚本授权确认，不增加校验收益。事实表写完后直接进入阶段 3 写源稿；结构性问题（claim_id 格式、缺 source/usage_type、hard_fact 来源分级不一致等）由阶段 4 finalize 内部门禁 1 拦截——报错就回事实表改完，再重跑 finalize，不要绕过。

---

## 四、阶段 3：写源稿

源稿是给读者的成品，不是研究笔记的整理稿。写作规则见 `writing-style.md`、`output-formats.md`；这里只强调和交付流程直接相关的三点。

### 4.1 事实绑定规则

支撑结论的正文数字、表格关键数字、后续关注阈值、关键事实判断，在**完整数字/判断写出之后**绑定 `{fact:claim_id}`：

```markdown
标的公司2025年净利润4187万元，同比增长189.5%。{fact:np_2025}
```

- `{fact:...}` 绑定标记只存在于源稿，`finalize_report.py` 会在 display markdown 中自动转换成普通文本 `[n]` 来源标记，并按同一编号重写文末「数据来源」。**源稿不要手写 `[n]` 或 `[^n]`**，写了会被门禁 2 拦下。
- `{fact:...}` 只能引用 `claims[].claim_id`，不允许引用中文事实名或不存在的 id；未知或格式错误的引用会导致门禁 2 报错。
- `usage_type=broker_estimate/broker_forecast/market_view/author_inference` 的 claim，正文必须保留「券商估算/机构预计/投资者评论区讨论/可能指向」等限定语，不得写成确定事实——门禁 2 会核查这一点并给出建议改写。

### 4.2 源稿必须已经包含的骨架（不是靠脚本生成的）

`finalize_report.py` 只负责把 `{fact:...}` 转换成编号、把编号列表填进已有的骨架里，**不负责生成免责声明文字，也不负责把来源按分类分组**。所以源稿写完时必须已经包含：

```markdown
## 数据来源

文中引用对应以下来源：

### 风险提示与免责声明：

- 以上内容为 AI 自动生成或 AI 辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。
- 以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误。历史数据、历史业绩、回测结果及情景假设均不代表未来表现。
- 用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖本分析输出而作出的决策及其后果，由用户自行承担。
```

「文中引用对应以下来源：」下面留空即可，`finalize_report.py` 会把编号列表插入这里；「风险提示与免责声明」的具体文字是模型写的，脚本只定位标题、原样保留，不会覆盖或重新生成。**不要写「未获取清单」**——缺口在正文用「数据不足/待核实」点到为止即可，免责声明已覆盖信息缺漏；若源稿误写了该区块，display 生成时会剥掉。批量监控摘要模式篇幅更短，至少保留「风险提示与免责声明」区块，「数据来源」视信息量精简。

### 4.3 图表在写源稿之前生成

`scripts/render_charts.py`（见 `output-rendering.md`）负责把图表数据渲染成 PNG，这一步在写源稿**之前**做——源稿里直接用 `![标题](charts/xxx.png)` 引用已经生成好的图片路径。

写完源稿后，更新恢复入口文件：

```markdown
当前状态：源稿已完成，尚未跑 finalize。
禁止交付：DO_NOT_DELIVER__NEEDS_FINALIZE__source.md（含 {fact:...} 审计标记）
下一步必须执行：python3 scripts/finalize_report.py _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__source.md _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

---

## 五、阶段 4：跑 finalize_report.py（门禁 2 + 生成 display markdown）

只运行下面这一条命令，不要拆开跑 `normalize_report.py` / `check_facts.py` / `lint_report.py` / `make_display_markdown.py`——它们是内部 helper：

```bash
python3 scripts/finalize_report.py \
  _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__NEEDS_FINALIZE__source.md \
  _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/DO_NOT_DELIVER__facts.json \
  --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

内部依次执行：

1. `normalize_report.py`：把源稿里的草稿直角引号「」『』，以及英文直引号包裹的中文短语（如 `"战略转型"`），原地转换成中文弯引号。
2. `check_facts.py`：**门禁 1**，校验 facts.json 结构（这是事实表的唯一正式校验入口，不要在写事实表后单独再跑一遍）。
3. `lint_report.py`：**门禁 2，硬门禁**。检查语气三句式违规、无名锚表述、自有评级、无锚的「超/低于预期」、内部术语泄露（`facts.json`、`finalize_report`、`playbook`、`Tier 1/2/3` 等）、`{fact:...}` 被当占位符使用、未知 fact 引用、券商/媒体/推断类表述是否保留限定语等。**有 ERROR 级问题时退出码非零，命令会直接失败中止，不会生成新的 display markdown**——回源稿改完问题再重跑，不能跳过或绕过。WARNING 不阻断，但要逐条判断：误报可放行，真实问题按建议改写后重跑。
4. `make_display_markdown.py`：把 `{fact:claim_id}` 按第一次出现顺序转换成 `[n]`（同一来源去重共用编号），填进第四节写好的骨架里，生成 `FINAL_REPLY_BODY.md`。

命令成功（退出码 0）之后，`FINAL_REPLY_BODY.md` 就是可以直接展示给用户、也是要用来创建飞书文档的正文，**不需要再做任何二次编辑或摘录**。

finalize 成功后，更新恢复入口文件：

```markdown
当前状态：FINAL_REPLY_BODY.md 已生成，下一步是创建飞书文档并输出正文。
禁止交付：所有 _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/ 路径和文件名；尤其禁止输出源稿。
下一步必须执行：用 FINAL_REPLY_BODY.md 全文创建飞书在线文档，然后在最终回复中先输出固定风险提示语，再粘贴 FINAL_REPLY_BODY.md 正文，最后附飞书文档。
最终正文来源：_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md
```

---

## 六、阶段 5：创建飞书文档 + 对话输出

### 6.1 创建飞书文档

用 `FINAL_REPLY_BODY.md` 的全文作为正文，调用**当前运行环境内置的飞书文档/云文档创建能力**（如豆包 App 内直接把一段 Markdown 转成在线文档的原生工具）创建文档。飞书文档的内容质量标准和 `FINAL_REPLY_BODY.md` 完全一致——它是正式交付物，不是简化版。

如果当前运行环境没有这种原生能力（如本 Skill 被部署到不提供该能力的环境，例如仅有 IDE/CLI 工具而无内置云文档能力的环境），退化到直接调用已封装好的 `lark-doc` 技能（底层为 `lark-cli`）完成实际的文档创建/内容写入，写入内容同样是 `FINAL_REPLY_BODY.md` 全文；生成后通过 `NotifyHuman` 工具交付在线 URL。两条路径二选一，取决于当前环境提供哪种能力。

无论走哪条路径，飞书文档生成失败时都不能让整个任务失败——固定风险提示语和 `FINAL_REPLY_BODY.md` 正文依然要完整输出给用户，第三段如实说明"飞书文档生成失败，原因是 XX"，不要静默跳过也不要因此不回复。

### 6.2 对话输出（固定三段式，不可变更顺序）

最终回复固定格式：

```text
回答基于AI 生成，仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。

<FINAL_REPLY_BODY.md 全文内容>

飞书文档：<附上的飞书文档链接>
```

不得输出的内容：中间文件列表、"已生成 XX 文件""已保存到 XX 路径"之类的交付清单或过程播报，以及 `_INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/`、`DO_NOT_DELIVER__facts.json`、`finalize_report.py` 这类内部目录名/文件名/脚本名。除非用户明确要求查看中间产物或过程，否则只输出上面三段。

---

## 七、可选：导出 Word/DOCX

只有用户明确提出"要 Word 文件""导出 docx"之类的诉求时，才在生成 `FINAL_REPLY_BODY.md` 时多传一个参数：

```bash
python3 scripts/finalize_report.py <源稿> <facts.json> \
  --display-output _INTERNAL_DO_NOT_DELIVER__READ_00_RESUME_FIRST/FINAL_REPLY_BODY.md \
  --docx-output <output.docx>
```

这不是默认交付物，跑完之后依然要遵守"不展示中间文件路径"的原则，只需要把生成的文件按用户实际能接收的方式交付。

---

## 八、常见错误排查

- **门禁 2 报错"最终 Markdown 仍含草稿引号「」/『』"或"中文词句被英文直引号包裹"**：说明 `normalize_report.py` 那一步没有正确转换（常见原因是嵌套代码块干扰了引号识别，或引号不成对）；一般重跑 `finalize_report.py` 即可自动修正。不要逐条手改引号——那是 normalize 的职责。
- **门禁 2 报错"正文不得使用 [^n] 脚注角标"**：把源稿里的 `[^n]` 删掉，改成在对应数字/判断后绑定 `{fact:claim_id}`。
- **门禁 2 报错"未知 fact 引用"**：说明正文引用的 `claim_id` 事实表里没有——先补登记事实表，不要删掉正文里的引用来"绕过"报错（删掉等于把这个数字变成无来源数字，违反硬约束）。
- **门禁 2 报错"fact 绑定不能替代正文数字或表格值"**：`{fact:...}` 被当成了数值占位符（如「净利润为 {fact:np_2025}」），改成先写完整数字再绑定。
- **门禁 2 报错"内部流程词/内部分类标签出现在成品报告"**：把 `facts.json`、`playbook`、`Tier 1/2/3`、`finalize_report` 等内部术语改写成读者可理解的自然语言。
- **门禁 2 提示"超/低于预期措辞但 facts.json 无对应锚"**：说明用了「超预期」类表述但事实表里没有登记一致预期数字作为锚点——补一条锚点 claim，或把表述改成不依赖预期锚的直接陈述。
- **文末"数据来源"清单没有生成，只剩标题**：检查源稿的「数据来源」骨架和「文中引用对应以下来源：」这行文字是否原样保留（不能被改写或删掉），脚本靠精确匹配这两处定位插入点。
