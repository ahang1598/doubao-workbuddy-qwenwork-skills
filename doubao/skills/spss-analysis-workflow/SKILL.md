---
name: spss-analysis-workflow
description: Use when the user asks for SPSS statistical analysis from data files, Excel, SPSS output, or screenshots, especially with keywords such as SPSS语法, 变量名核对, 问卷量化, 缺失值处理, 统计方法选择, 论文返修, 结果不一致, or 截图报错.
---

# SPSS Analysis Workflow

Use this workflow for medical, education, psychology, public-health, nursing, agriculture, and other research tasks that need variable inspection, SPSS syntax or menu steps, output verification, and manuscript-ready reporting.

## 1. Ingest files, screenshots, and study design

1. Read the latest attached data file, variable view, SPSS output, or screenshot before giving final syntax or conclusions.
2. Extract a working audit sheet: file/version, sample size, row identifier, variable names, labels, value labels, missing codes, grouping/time structure, and the user's stated research question.
3. For screenshots, first transcribe the visible error/output text and current SPSS dialog; then give the smallest next action.

Concrete conventions:
- In the Go/No-go evidence, wide data used `Subject`, `major`, `Sex`, `RTgo_1`~`RTgo_4`, `ACCgo_1`~`ACCgo_4`, `ACCnogo_1`~`ACCnogo_4`, `AWE_1`~`AWE_4`, and `PTM_1`~`PTM_4`; do not write long-format syntax until confirming how these four suffixes map to the four conditions.
- The observed four-condition mapping was condition 1=红色歌曲/红歌, 2=中性歌曲/中歌, 3=红色器乐/红器, 4=中性器乐/中器; if the user says the variable names changed, update labels and prose to the latest names before reusing an old template.
- For Mplus/SPSS missing handling in the same trace, `MISSING ARE ALL (-99)` was explicitly used; treat blank cells, text like `(跳过)`, and numeric `-99` as different missing/value-label situations until the file confirms otherwise.

## 2. Build the variable map and quantitative coding plan

1. Map variables into outcome, grouping factor, covariate, mediator, moderator, repeated-measure time/condition, questionnaire item, manipulation-check item, and attention-check item.
2. Preserve original text columns when recoding; create numeric target variables with clear variable labels and value labels.
3. For scale or questionnaire work, document item membership, reverse scoring, excluded checks, score range, and whether totals or means are used.

Concrete conventions:
- For the AOFAS ankle questionnaire, `follow_day` codes `(跳过)` as `0` for 初诊/baseline, and `第1天`, `第2天`, `第3天`, `第5天`, `第7天` as 1, 2, 3, 5, 7; coding `(跳过)` as missing changes baseline counts and downstream nonparametric tests.
- For AOFAS scoring, `aofas_total` is the sum of nine dimensions: `aofas_pain + aofas_function + aofas_walkdist + aofas_walksurface + aofas_gait + aofas_dorsiflex + aofas_hindfoot + aofas_stability + aofas_alignment`, with theoretical maximum 100; if the questionnaire has an original total column, use it only to cross-check large coding mistakes.
- Evidence-specific AOFAS item names include `pain_score` for pain and `function_score` for function/support; pain options were scored 40/30/20/10 and function/support options 10/5/0, so do not recode them as simple 1/2/3/4 Likert values.
- For affected-side VAS, `vas_affected = vas_left` when `side = 1` and `vas_affected = vas_right` when `side = 2`; averaging left/right VAS or always taking one side changes the analysis target.
- For questionnaire models with `TRU`, `AMO`, `IMP`, and `NFC`, exclude attention-check/manipulation-check items before computing scale means, reverse-score reverse items first, then compute scale scores such as `MEAN(...)`.

## 3. Check data quality and effective sample size

1. Run frequencies/descriptives before method selection: unique values, missing counts, impossible ranges, duplicate IDs, row counts per group/time, and whether filters or deleted rows are active.
2. State the deletion rule that each analysis uses: listwise deletion, pairwise/indicator-specific deletion, or complete-case analysis.
3. If SPSS reports “不存在有效个案”, inspect whether all candidate variables are strings, value labels were entered without numeric values, user-missing values exclude all rows, filters/weights/split-file are active, or listwise deletion removes every row.

Concrete conventions:
- For manuscript revision around CEA、降钙素、被膜累及、脉管侵犯、神经侵犯, the evidence used complete case analysis and annotated each variable's effective N and missing cases below Table 1; do not report a single denominator for every clinicopathological indicator if variables have different missingness.
- For baseline sex comparison in the simulated clinical dataset, first filter to completed cases, then tabulate `group × gender` and verify Pearson chi-square/P before writing the paper sentence; using all generated rows instead of completed cases changes counts and percentages.
- When results differ from a previous run, check data source version, deleted rows, missing processing, filters, and variable coding before recalculating; one evidence trace located the discrepancy at an incorrectly deleted sample row.

## 4. Match statistical method to design and assumptions

1. Choose the method from the research design and variable types, not from the user's preferred button: descriptive statistics, t-test/ANOVA, nonparametric test, chi-square/Fisher, correlation, linear/logistic regression, ROC, repeated-measures GLM, mixed model, PCA/factor analysis, cluster analysis, or mediation/moderation model.
2. State the method rationale and prerequisite checks: normality, homogeneity, paired/repeated structure, sparse categories, multicollinearity, model encoding direction, or factorability.
3. When the user's proposed method is inappropriate, explain the design mismatch and provide the closest valid SPSS route.

Concrete conventions:
- For a 2×2×2 repeated-measures accuracy template with N=58, do not reuse old prose if the user changes the design to SCIAT with only “相容/不相容”; update the within-subject factors and df from the current condition structure.
- For the speed manipulation evidence with 3 repeated levels and N=24, the correct repeated-measures df was `F(2, 46)`, not `F(3, 476)`; derive df from `k-1` and `(k-1)*(n-1)` before accepting a manuscript template.
- For KAP or questionnaire group comparisons, use Levene to choose equal-variance vs unequal-variance t-test output, use ANOVA only for 3+ groups, and perform post-hoc comparisons only after a significant omnibus test.
- For EFA/survey validity screenshots, read `KMO` and `Bartlett` first, then inspect total variance explained, factor number, rotated component matrix, low loading/cross-loading items, and rerun after item changes.
- For sparse multinomial/logistic outputs, inspect case-processing summaries and likelihood-ratio tests before interpreting coefficients; merge sparse categories or simplify predictors when estimates are unstable.

## 5. Produce executable SPSS syntax or menu steps

1. Prefer reproducible SPSS syntax; add menu paths when the user is learning SPSS or sends screenshots of the interface.
2. Include import, recoding, variable/value labels, missing values, compute/restructure commands, assumption checks, and final analysis commands as separate blocks.
3. When targeting another statistical tool from SPSS-prepared data, still keep the SPSS data preparation traceable.

Concrete conventions:
- For Go/No-go moderated mediation, long format used `Subject major Sex condition X W AWE PTM RTgo ACCgo ACCnogo QianAWE XW condition_label`; `X = 1` for songs and `0` for instrumental, `W = 1` for red and `0` for neutral, and `XW = X*W`.
- For the Mplus twolevel model, `CLUSTER = Subject`, `WITHIN = X W XW`, `AWE ON X W XW`, and each outcome (`PTM`, `RTgo`, `ACCgo`, `ACCnogo`) should be swapped one at a time in the outcome position; do not split “one variable one dataset” if the user asks to keep all variables in one long file.
- If a screenshot/error says `BOOTSTRAP is not allowed with TYPE=TWOLEVEL`, remove bootstrap for that twolevel model and use the compatible estimator/output route shown by the user's current syntax rather than retrying the same command.
- For AOFAS and VAS recoding, generate numeric variables (`follow_day`, `pain_score`, `function_score`, `aofas_total`, `vas_affected`) and labels before running Explore or nonparametric tests; running Explore on raw Chinese text columns can produce no valid cases.

## 6. Verify output and reconcile inconsistencies

1. Read the returned SPSS output or screenshot; extract only visible or computed statistics: N, M, SD/SE, test statistic, df, p, CI, effect size, model coefficients, and table labels.
2. Cross-check output against the data and manuscript table/prose: same variable, same coding direction, same sample, same deletion rule, same rounding.
3. If output is unavailable, provide expected workflow and verification points, not fabricated results.

Concrete conventions:
- For repeated-measures writeups, extract `F`, df, `p`, and partial eta-squared (`η²p`/`η²`) for each main effect and interaction; do not copy a template result when variable names, condition labels, or dfs differ.
- For screenshot-based Cohen's d, first extract `N`, means, SD, and `t`, then choose the formula by test type; do not confuse the CI for a mean difference with a CI for `d`.
- For LMM/Sci table extraction, pull EMM, MD, CI, P, and fixed effects from the SPSS output; mark missing items explicitly instead of filling blanks from memory.
- For figures/tables, verify raw `M/SD/SE` against visible bar heights, error bars, axes, and manuscript table values before claiming the chart matches.

## 7. Write manuscript text, table notes, and revision replies

1. Convert verified outputs into methods text, results paragraphs, tables, figure notes, and reviewer replies.
2. Preserve actual statistical direction, significance, N, p formatting, CI, units, group labels, and missing-data notes.
3. For translation or polishing, keep technical terms and statistical claims equivalent to the source; do not add unverified causal or independent-risk claims.

Concrete conventions:
- For complete-case revision replies, include both the method and table note: variables such as CEA、降钙素、被膜累及、脉管侵犯、神经侵犯 had missingness, and each table row should show effective sample size/missing cases when denominators differ.
- For Logistic forest-plot text, treat OR=1 as the no-effect line; only describe an independent risk factor when the 95% CI does not cross 1 and the output P supports it.
- For moderated mediation prose, align labels exactly: evidence used `歌曲类型（0=红色歌曲，1=中性歌曲）`, `音乐训练经历（0=无音乐训练，1=有音乐训练）`, mediator `敬畏情绪`, and outcomes such as `Go反应时` or `Go正确率`; if current coding uses `X/W` differently, rewrite all interpretations accordingly.

## Boundaries and refusals

- Do not give final syntax, statistical conclusions, or manuscript-ready text before checking variable names, coding, missingness, and effective N.
- Do not invent SPSS output values. Without output, give only steps, syntax, and a checklist of what to verify after running it.
- Do not detach method choice from study design. Explain why the selected test/model matches the outcome type, group/time structure, and assumptions.
- Do not ignore filters, split-file, weights, deleted rows, user-missing values, or listwise/pairwise deletion rules.
- Refuse requests to alter or fabricate data solely to obtain significance; redirect to valid cleaning, sensitivity analysis, model correction, or transparent reporting.
- For screenshots of errors, diagnose from the visible text and current dialog first; avoid broad reinstall/software-version advice unless the minimal fix fails.

Concrete conventions:
- If the task involves the AOFAS file, do not run final nonparametric tests until `follow_day`, `pain_score`, `function_score`, `aofas_total`, and `vas_affected` are numeric and verified by frequencies.
- If the model syntax contains `TYPE=TWOLEVEL`, do not keep `BOOTSTRAP` after the output says `BOOTSTRAP is not allowed with TYPE=TWOLEVEL`.
- Do not treat `Subject`-clustered Go/No-go rows as independent observations when `condition`, `X`, `W`, `XW`, `AWE`, `PTM`, `RTgo`, `ACCgo`, and `ACCnogo` are repeated within the same person.

## Minimal example

User: “这个 AOFAS Excel 用 SPSS 做非参数检验，为什么探索提示不存在有效个案？”

Response pattern:
1. Read the Excel and list actual columns/options.
2. Confirm whether `aofas_total` is numeric; if not, recode raw items first.
3. Code `(跳过)` in `follow_day` as 0 for baseline, not missing.
4. Compute `pain_score`, `function_score`, the remaining seven AOFAS dimensions, and `aofas_total` as the nine-dimension sum.
5. Use frequencies to verify nonmissing `aofas_total` and `follow_day`, then run Explore/nonparametric tests with the correct deletion rule.
6. Only after SPSS output returns, write the result sentence with the observed statistic, P value, and effective N.
