---
name: evidence-based-rubric-scoring
description: Use when the user asks to score, rescore, deduct points, convert bands, audit evidence, rank results, or draft evaluation wording from a 评分表, 评分标准, 评审维度, 档次规则, 扣分依据, 重新评分, 附件/批注/异常反馈, 四舍五入, 分档表述, or 复核结果.
---

# Evidence-Based Rubric Scoring

Use this skill to turn scoring rules and source materials into traceable scores, deductions, ranking tables, review notes, or evaluation wording. The core rule is: parse the rubric first, inventory every evidence source, map facts to criteria, calculate exactly by the stated rule, then audit the result before delivery.

## 1. Confirm the scoring task and dispute points

- Classify the request as one or more of `初评`, `复评`, `重新评分`, `扣分复核`, `档次换算`, `排名统计`, `评价话术生成`, or `写回表格` before doing any scoring.
- If the user mentions missed bases such as `年度绩效目标的批注要求` or `汇一级时发现异常二级项目反馈`, treat that as a rescore trigger: reopen the evidence inventory instead of defending the previous score.
- Lock the scoring object and scope: do not reuse evidence across different `项目`, `剧集`, `论文`, `课时`, `医生`, `投标人`, or different time/version ranges unless the rubric explicitly permits it.
- When comparing batches, preserve the unit named by the user: examples in the evidence use `10个项目`, `50集`, `DR/CT/MR`, `5课时`, and `12个维度`; mixing these units changes denominators and rankings.

## 2. Parse rubric rules into a scoring schema

- Extract for each row or dimension: `评分项`, `标准分` or满分, `权重`, `档次`, `扣分条件`, `否决项`, `证明材料`, `取整/四舍五入`, and `汇总规则`.
- Keep scoring items separate from gating rules: `一票否决` or `否决项` is not an ordinary deduction; report it before subtotaling and do not hide it inside a low score.
- For tender/legal scoring wording, include a `0分情形` and `证明材料` for each add-score item; do not write only “优/良/一般” without a boundary or evidence requirement.
- For band wording, preserve the rubric’s档次 language: `好`, `较好`, `一般`, `优秀`, `合格`, `不合格`, `A-D` must map to their actual score interval, not to a nicer-sounding phrase.
- If the rubric gives total allocation constraints, record them numerically before distributing points, e.g. `总分100`, `大项为5倍数`, and同一大项内小项分差`≤1`.

## 3. Inventory and validate all evidence sources

- Build an evidence ledger with columns `来源`, `对象`, `位置`, `字段/页码/单元格`, `可用于哪些评分项`, and `疑点`.
- Do not stop at the visible worksheet area: evidence showed a missed `附件3.xx大学2027年绩效目标修改建议表.xlsx` containing expert comments for `10个项目`; its `L列"调整原因"` and `M列"新发现问题"` changed the rescore basis.
- Inspect hidden or secondary evidence when prompted by critique: examples include spreadsheet `单元格批注` such as `G16`, feedback files with `11列` when only `9列` were read, `批注`, `异常反馈`, image rules, PDF目录页码, and historical versions.
- For image or screenshot rubrics, extract visible parameters before scoring and mark uncertain OCR values as `待确认`; do not infer missing thresholds from similar rubrics.
- For large PDFs or Word files, identify `目录`, `技术部分起止页`, tables, and appendices first; score only after the relevant pages/sections are read.

## 4. Extract facts and map them to criteria

- Create a table with `评分项-事实-证据位置-满足档次/扣分条件-结论`; every score or deduction must point to a source row, page, image region, original sentence, database record, or user-provided correction.
- For绩效/项目材料, map expert feedback to the exact project and indicator; do not apply one project’s `调整原因` or `新发现问题` to another of the `10个项目`.
- For text review tasks, quote the source when identifying hard defects: examples include作文按 `内容/语言/结构/书写` 分项、新闻稿按 `标题/导语/结构/事实/文风` 分项、教学设计按 `5课时` and `6维评分` 分项.
- For system or content scoring, require dimension-level differentiation: in the剧本 evidence, `overall_score = 12个维度的平均分` and each dimension’s score had to be supported by `main_issues` or `strengths`; repeated identical episode scores require evidence review, not acceptance.
- If a criterion requires current external facts such as `NMPA`, `说明书`, `临床试验`, `注册分类`, `适应症`, or `RCT数`, cite the source and date; if unavailable, mark the item unscored or provisional.

## 5. Calculate, deduct, convert, rank, or write back

- Follow the user/rubric rounding rule exactly: when the rule says `四舍五入到小数点后1位`, keep intermediate values and round only the final target field, such as `overall_score`.
- For a multi-dimension average, calculate from components: e.g. `overall_score = 12个维度的平均分`; do not assign the total by intuition even if the total “looks reasonable.”
- When batch-ranking quality-control tables, convert the scoring column to numeric first, then filter by the stated cutoff; evidence used `评分<10` to produce扣分/低分明细 and then calculate `扣分率` and分值分布.
- When merging modalities or files such as `DR`, `CT`, and `MR`, add a `来源` column before combining so doctor rankings and low-score records remain traceable to the original sheet/file.
- For redistributed scoring forms, verify `总分100`, large-item totals, `5倍数` constraints, and same-large-item balance `≤1`; after writing back, recompute totals from cells rather than trusting visible合计.

## 6. Audit anomalies and conflicts before delivery

- Compare recomputed subtotals with any table `合计` rows, but treat detail rows as the source for recalculation; if `表头合计`, visible合计, or an item exceeds满分, report the row and corrected impact.
- Check for missing evidence coverage: if a row has a deduction such as `第13行扣了0.5分`, the corresponding problem/opinion column such as `G列` must contain the reason before delivery.
- Flag score distributions that are too uniform: examples include multiple episodes all scoring `8.2` or every dimension falling in `7.5-8.5`; require dimension-specific evidence, with high/low signals such as `≥9` or `≤6.5` only when supported.
- Audit duplicate deductions: one defect may support one扣分项 unless the rubric explicitly says it affects multiple dimensions; never deduct twice under two labels with the same evidence sentence.
- When rule conflict, field ambiguity, inaccessible attachments, or evidence absence remains, write it as `无法确认/需补充` instead of filling a favorable or unfavorable score.

## 7. Deliver traceable results and evaluation wording

- Output the final table with at least `对象`, `评分项`, `标准分/权重`, `得分/扣分`, `依据`, `证据位置`, `异常/待确认`, and `建议`; include subtotal/total/rank only after calculation checks pass.
- For rescore tasks, state what changed: e.g. “新增纳入 `附件3.xx大学2027年绩效目标修改建议表.xlsx` 的 `L列`/`M列` 后，哪些项目或行被重评.”
- For evaluation wording, generate versions only after score bands are fixed: `综合版`, `分维度版`, and `简洁版` must match actual档次, and `一般` cannot be phrased as `较好`.
- For editable file delivery, preserve the original format and identify automatic versus judgmental fields: examples are `得分`/`总分` as calculated fields and `问题建议`/`审核意见` as judgment fields.
- If ranking or统计 is requested, include denominator and filter: e.g. `DR/CT/MR合并后`, `评分<10`, total cases, low-score count, `扣分率`, and rank rule.

## Boundaries

- No score without evidence; no subjective upgrading or downgrading to make language smoother.
- No missing `批注`, `异常反馈`, supplemental attachments, images, historical versions, or user corrections.
- No cross-project or cross-version borrowing: `项目A` evidence cannot score `项目B`, and an older file cannot override the latest uploaded rule image or attachment.
- No confusion between `评分项`, `否决项`, `档次项`, `换算项`, and `证明材料`.
- No invented rounding or thresholds: if `四舍五入`, `取整`, interval boundary, or invalid-offer handling is absent, explicitly ask or mark pending.
- Do not recommend using precomputed or summary tables as the scoring authority; use detailed rows/material evidence for calculations and use summaries only for reconciliation.

## Tools and artifacts

- Use document readers for Word/PDF正文、表格、目录、批注 and comments; use image reading/OCR for rubric screenshots and parameter images.
- Use spreadsheet or script calculation for batch scoring, sorting, distribution, and write-back when there are many rows or files.
- Use source labels whenever merging files, modalities, projects, or versions.
- Keep intermediate calculation tables when totals, rankings, `评分<10`, `扣分率`, `12个维度平均`, or `总分100` allocation are involved.

## Example

User asks: “你没有按照年度绩效目标的批注要求还有汇一级时发现异常二级项目反馈来打分吗？”

Do:
1. Reopen the source list and search for `年度绩效目标`, `批注`, `异常反馈`, and extra sheets/columns.
2. Add `附件3.xx大学2027年绩效目标修改建议表.xlsx` to the evidence ledger if present, including `L列"调整原因"` and `M列"新发现问题"`.
3. Map each comment to its exact project among `10个项目`, rescore only affected indicators, and fill any deduction reason such as `G列` when `第13行扣了0.5分`.
4. Recalculate totals, list changed rows, and deliver the revised files or table with explicit source citations.
