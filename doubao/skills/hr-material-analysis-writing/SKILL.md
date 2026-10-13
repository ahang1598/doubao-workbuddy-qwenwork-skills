---
name: hr-material-analysis-writing
description: Use when the user asks to process HR-related materials by drafting, rewriting, fact-checking, summarizing constraints, counting lists, comparing payroll/attendance data, generating formal documents, or iterating official HR/organization texts. Trigger keywords include 公文起草, 材料改写, 事实核对, 约束汇总, 名单统计, 方案重写, 正式稿生成, 多轮迭代, 考评方案, 工会选举, 绩效指标, 工资比对, 考勤统计.
---

# HR Material Analysis and Writing

Use this skill for HR and organization-management deliverables where the answer must stay grounded in supplied materials: official documents, performance plans, union election texts, payroll/attendance comparisons, staffing lists, candidate/resume materials, HR policies, and iterative formal rewrites.

## 1. Identify the task and delivery type

Classify the request before drafting: 公文/议案/工作方案, 汇报材料/方案重写, 履历或简历精简, 名单统计, 薪酬或考勤比对, 绩效指标/PBC, 组织风险分析, or 约束汇总.

Concrete conventions:
- For 工会增补选举材料, preserve the document role: `议案` asks representatives to审议/确认, `选举办法` defines voting rules, and `前置上工会委员会审议的工作方案` sets the internal committee process before the大会.
- For绩效管理材料, map content into the user-provided policy frame rather than inventing a new one: examples include `分类设标`, `分级考评`, `双向绑定`, `3+1考核体系`, `岗位认领+个人承诺+差异化设定`.
- For table/calculation tasks, identify the unit that changes the result: `姓名` for payroll matching, `部门/学历/方向` for校招名单统计, `岗位/人数/职级` for组织架构, and horizontal date headers plus `OT1/OT2` for考勤区间统计.

## 2. Recover materials and previous constraints

Collect the original text, attachments, quoted prior drafts, user corrections, formatting preferences, prohibited phrases, and known unresolved blanks before producing a final artifact.

Concrete conventions:
- Treat explicit user deletions as locked constraints: `不要五位一体`, `不要服务对象`, `800万元不提了`, `99%数据不加回`, and `第四部分洁净实验室缺改造效果：不加回` must not reappear in later drafts.
- For工会材料, carry forward fixed facts and dates separately: `原有代表31名`, `3名代表离职`, `实有代表28名`, `增补代表3名`, `增补工会委员会委员1名`, `8月4日`启动代表增补, `8月11日`启动委员增补, `8月底`大会暂定.
- For facts under dispute, trace the source before rewriting: `收入800余万元` was challenged as unsupported, so delete or mark it待确认 instead of smoothing it into the text.

## 3. Extract facts, constraints, and calculation口径

Build a source ledger with four labels: 原文事实, 用户新增事实, 合理推断, 待用户确认. Do not merge these labels in the final text unless the user explicitly confirms.

Concrete conventions:
- For工会选举, record procedure thresholds exactly: meetings require attendance reaching `应到会代表三分之二以上`; a candidate is elected only if赞成票 `超过应到会代表半数`; `监票人1名` and `计票人1名` are elected/pushed by the meeting and `候选人不得担任监票人、计票人`.
- For代表结构, keep percentage constraints numeric: `中层以上管理人员代表占比不超过20%`, `一线职工代表占比不低于60%`, `女职工代表占比不低于30%`, and note whether增补后仍满足.
- For岗位分类考评, preserve supplied weights because changing them changes scoring: 机关综合科室 `40/30/15/15`, 基层监管分局 `40/30/15/15`, 行政执法业务科室 `50/25/15/10`, 政务服务窗口 `50/30/10/10`.
- For工资实发数对账, normalize both sides before comparing: clean `姓名`备注/空格/日期, handle异体字/别名, compare金额 only after both columns are `round2` to分, then classify as金额差异、人员缺失、姓名差异、尾差.

## 4. Cross-check and gate uncertain content

Before drafting or calculating, reconcile conflicts across materials. If a critical field is missing, ask a targeted question or list the assumption; do not silently finalize.

Concrete conventions:
- If a方案 uses weekday labels, verify date consistency instead of copying: evidence included `2026年8月12日（星期三）` and `2026年8月11日（星期二）`; check that calendar labels match the date before output.
- For project/fact materials, do not upgrade status beyond the source: `8.11日开标了` is not `招投标完成`; `计划年内运抵现场安装调试` differs from `已运抵呼和浩特`; use the latest confirmed wording only.
- For payroll and attendance, rerun total checks after cleaning: totals by `姓名` match count, unmatched names, and `round2` amount differences must reconcile with the reported exceptions.
- For考勤公式, confirm horizontal headers are real Excel dates before using date filters;区间统计 should combine date-range conditions with班次 conditions through `SUMPRODUCT`, and output `OT1`/`OT2` separately.

## 5. Structure the deliverable

Choose a structure that matches the document type, then fill only with supported content.

Concrete conventions:
- 公文/议案 usually follows `依据—背景—事项/程序—恳请事项—落款日期`;工会方案 adds `增补名额`, `代表条件`, `候选人产生`, `选举方式`, `时间安排`, `工作要求`.
- 绩效汇报 should use a total-sub structure; for the supplied performance plan, write around `分类设标：优化岗位指标权重配置`, `分级考评：细化干部层级考评标准`, and `双向绑定：深化团队个人绩效联动`, and add `政治素质考核` only where the user requested `3+1考核体系`.
- 统计表 should use dimensions from the material, not generic labels:校招名单按 `部门/学历/方向` 聚合;组织架构按 `岗位/人数/职级` 抽取;企业调研名单按领导原文和用户补充的 `三档标准` 写建议列.
- 简历/专家履历精简 keeps only material tied to the target: for硅乳液访谈, retain `公司/职位/产品/下游应用/研发协作`, and remove弱相关的业绩、团队、回款.

## 6. Generate text, tables, or formulas

Draft in a formal but usable style. When calculating, expose the matching and precision rules so the user can audit the result.

Concrete conventions:
- In official HR/organization texts, avoid parallel wording defects the user flagged: do not write paired clichés like `开创...新模式，探索...新路径` if they sound redundant; fix punctuation where one sentence incorrectly joins `2024年10月获管委会批复` and `落实经费410万元` with only a semicolon.
- For工会委员补选, use `无记名投票` and `差额选举`; when `应选1名`, `正式候选人2名` satisfies the supplied differential setup, while `初步人选3名` remains a candidate-generation fact.
- For工资对账 outputs, include at least these columns when exceptions exist: `姓名`, `左侧金额`, `右侧金额`, `差额`, `异常类型`; amount comparison uses `round2` on both sides before `差额`.
- For考勤区间公式, make cell ranges replaceable and state old-version Excel compatibility if using `SUMPRODUCT`; do not assume dynamic array functions are available.

## 7. Final QC and handoff

Before delivery, check factual totals, chronological order, role names, percentages, document titles, and user-stated禁忌. Include risks and待确认项 when they affect legality, counting, or official wording.

Concrete conventions:
- 工会材料 QC must verify `31-3=28`,增补后代表数 `28+3=31`, `公示5个工作日`, `任期与第二届工会会员代表大会届期一致`, and whether `消防技术事业部1名/认证（双碳）事业部1名/计量检测事业部1名` all have names filled.
- 绩效指标 QC must ensure the four岗位权重 groups each sum to `100%`; if adding `政治素质考核` to a `3+1考核体系`, state whether it is independent or included in existing weights.
- 文稿 QC must check title hierarchy,称谓,间隔号, date format, and grammar; if the user says a sentence is半句话, complete the predicate rather than only deleting the unsupported number.
- For legal/procedural HR text, state that the draft is based on supplied materials and common procedure; when法规适用不确定, ask the user to verify with the union, HR legal counsel, or主管部门.

## 8. Iterate without losing constraints

When the user corrects the draft, first identify which constraint changed, then update the artifact and preserve all still-active constraints.

Concrete conventions:
- If the user says `重新说`, `内容全换`, or `小标题换一下`, change structure and wording, but keep fixed facts like `12315投诉处置质效`, `两品一械`, `2026年5月提拔9名干部`, or already-confirmed names unless the user also deletes them.
- If the user challenges accuracy (`你写的，不知道在哪个材料里看到的`), stop polishing and re-open the source ledger: unsupported figures such as `800余万元` move to待确认/删除, not to a rephrased factual claim.
- If the user supplies newer status wording, prefer it over the previous draft: `探测器和望远镜主体均已研制完成，测试合格交付` plus `望远镜主体已运到呼和浩特` supersedes earlier generic `计划年内运抵现场安装调试`.

## Boundaries

- Do not invent facts, headcounts, quotas, dates, legal bases, performance achievements, names, salaries, or attendance records.
- Keep personal information minimal: use `姓名` only when matching payroll/list data requires it; avoid exposing unrelated salary,履历,身份证,家庭 or contact details.
- Official HR, union, personnel, and制度 drafts are not legal opinions; flag uncertain法规 or程序 items for verification.
- For data tasks, always state cleaning口径, matching key, precision rule, and exception categories.
- If materials are missing, structures are unclear, or口径 conflicts, ask for the missing file/field or list assumptions instead of producing a false final.

## Example

User asks: “根据两个议案拟一个前置上工会委员会审议的工作方案，8月底开大会，时间暂定。”

Response approach:
1. Extract fixed facts:增补代表 `3名`,增补委员 `1名`,代表名额分配到 `消防技术事业部/认证（双碳）事业部/计量检测事业部`, `8月4日` and `8月11日` as two启动节点.
2. Build the方案 as committee pre-review material, not a大会表决议案.
3. Preserve procedure thresholds: `三分之二以上` attendance, `超过应到会代表半数` elected, `5个工作日`公示.
4. Mark blanks such as missing代表姓名 or正式候选人名单 as待填，不编造.
