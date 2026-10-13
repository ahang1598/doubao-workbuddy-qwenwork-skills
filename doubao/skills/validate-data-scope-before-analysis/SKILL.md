---
name: validate-data-scope-before-analysis
description: Use when the user asks to compute, plot, tabulate, summarize, rewrite methods, or generate conclusions from data/files/reports and the task involves 数据口径, 单位核对, 读取附件, 字段结构, 元数据校验, 时间范围, 占比重算, 用户更正, 作图前校验, or updated/merged data sources.
---

# Validate Data Scope Before Analysis

Use this skill before any calculation, chart, table, model, method rewrite, or conclusion that depends on data in attachments, local files, spreadsheets, reports, images, NetCDF files, CSVs, or prior conversation state.

## Workflow

### 1. Confirm the authoritative source

1. Read the latest local or uploaded source before computing. If the user says they found a new Excel/source, switch to that source even if prior plots or extracted tables exist.
2. Record the authoritative file, version, and path in working notes or the response: examples from evidence include `20260813周报_LHB.pptx`, `演示文稿2.pptx`, `LASSO_Key_Genes.txt`, `LASSO_coef.csv`, `KEGG_GO_enrichment_results.csv`, and local paths such as `D:\py\forbeps\批量\outp.py`.
3. For the P-model workflow, treat `D:\py\forbeps\批量\outp.py` as the producer that normalizes P-model and BEPS outputs into `E:` for downstream statistics/plots; do not mix older `E:` outputs with a newer rerun without checking which run produced them.
4. When multiple attachments are expected, read all of them and compare for duplicates or missing inputs before extracting numbers; do not infer missing chart data from a repeated attachment.

### 2. Inspect structure, units, time, and metadata

1. For NetCDF or model outputs, inspect dimensions, variables, `units`, `time`, missing values, and sample value ranges before using them in AI/生态模型 calculations; the CRU/P-model evidence specifically required checking metadata rather than assuming the file could be used correctly.
2. For building-area charts, preserve `单位：亿㎡` and the scope `含居住、商业、公服、工业、物流、其他六类合计`; a `2017-2025` total line must be the sum of those six categories, not a separately guessed trend.
3. For enrichment results, keep `source`, GO/KEGG ID, and genes together: examples include `GO:0004674` under `GO:MF` for Protein Serine/Threonine Kinase Activity with `PLK3, MAPK8, MAPK1`, and `GO:0034614` under `GO:BP` for Cellular Response to ROS with `MAPK8, MAPK1, FOS`.
4. For Enrichr-style outputs, preserve the library/version fields `GO_Biological_Process_2023`, `GO_Cellular_Component_2023`, `GO_Molecular_Function_2023`, and `KEGG_2021_Human`; do not collapse them into a generic GO/KEGG label if reproducibility matters.

### 3. Recompute small checks before full analysis

1. Recompute totals, percentages, TopN, thresholds, and date coverage on a small slice before generating final charts. Building totals should check the six-category sum; pie/donut charts should check category percentages add to `100%` unless the source defines another denominator.
2. For GeneRatio or annotation proportions, the denominator must be explicit: use annotated proteins as the denominator, or add an `Unannotated` category; unannotated proteins being excluded is a valid reason that displayed GeneRatio values do not sum to `100%`.
3. For Enrichr output, compute `gene_ratio` as `intersection_count / len(GENES)`, where `GENES` is loaded from `LASSO_Key_Genes.txt`; if `LASSO_coef.csv` is missing, any default coefficient such as `0.3` is only for node sizing and must not be treated as biological evidence.
4. For time-series CSVs, sample `列名`, encoding, and date strings first; if parsing fails, fix the template and then check record count, total generation, and month distribution before calculating hourly/monthly differences.

### 4. Reconcile versions, corrections, and incompatible scopes

1. User corrections override old results, old plots, and outside knowledge. Evidence examples include `工业2022年应该是3.9,2023年应是4.1`; update only the affected rows/series and then rerun totals, percentages, and charts that depend on them.
2. For P-model comparisons, `V1.0` means monthly averages, not smoothed data; `subdaily_mengoli2023`, daily P-model, and `v1.1.1`-based `fw` should not be described as the same time scale or soil-water mode.
3. For the `fw` workflow, `D:\py\forbeps\批量\fw_splash计算.py` calculates the `fw` CSV used by `D:\py\forbeps\批量\fw_RE_箱线图_双图版.py`; if the user says `fw` is unchanged between daily and subdaily P-model, keep that correction unless new data contradicts it.
4. When categories are merged, such as a flavor/category merge in menu engineering or adding/removing modules in a topology chart, adjust only the named category/module and keep the original data source, style, and unaffected series.

### 5. Compute, plot, or write only after scope is locked

1. Once the source and scope are locked, run the formal calculation, model, chart, or writing pass and preserve intermediate outputs where useful, such as cleaned tables, chart-ready data, or cached `KEGG_GO_enrichment_results.csv`.
2. For building forecasts or trends, distinguish historical charting from forecasting: `2017-2025` is observed history, while `2017-2035` includes projection and must state the model choice and its limits.
3. For chart rendering, choose deterministic charting for exact text and values. In ECharts, if all category labels must show, set `axisLabel.interval=0`; if a period is intentionally broken, insert null/empty values so the line does not connect across the gap.
4. If sample size is too small, missingness is severe, or categories are unordered/non-comparable, separate the limitation instead of forcing a comparison; examples include filtering tiny boxplot groups and using bars rather than line charts for unordered medical categories.

### 6. Deliver with traceable scope and limitations

1. In the final table, chart note, or prose, include source, time span, unit, denominator, statistical scope, and user corrections that changed the result. For example: `单位：亿㎡ | 含居住、商业、公服、工业、物流、其他六类合计 | 2017-2025`.
2. For enrichment/network figures, keep full names and identifiers in the caption or notes even if node labels use short forms: `Ser/Thr Kinase Activity (GO:0004674, GO:MF)` is traceable, while `Ser/Thr` alone is not.
3. For financial/marketing analysis, do not estimate a `放量上限` until required fields such as `消耗`, conversions, `GMV`, cost basis, `ROI2` formula, and fixed parameters are known or explicitly assumed.
4. If any field, unit, time boundary, denominator, or merge rule remains uncertain, state the exact assumption or ask for confirmation before presenting numeric conclusions as final.

## Boundaries

- Never calculate, plot, tabulate, or write conclusions before reading or confirming the newest authoritative source.
- Do not mix different versions, units, time ranges, denominators, or merge rules in one number.
- Detail/raw data are the calculation authority; derived summaries are only cross-checks. If they disagree, report the difference and use the detail/raw source.
- Do not invent p-values, significance marks, missing categories, or forecast results from aggregate tables that cannot support them.
- Keep user corrections above prior output: `工业2022=3.9` and `工业2023=4.1` must replace previously recognized values wherever those rows are used.

## Example

User: “我重新找到数据源 Excel 表格了，需要根据这个表格重新更新之前的模型及图形。先帮我做一张各类建筑历年变化的图。”

Response pattern:
1. Read the new Excel/image source first and mark it as replacing previous chart OCR.
2. Extract categories `居住`, `商业`, `公服`, `工业`, `物流`, `其他`, years `2017-2025`, and unit `亿㎡`.
3. Recompute the total as the six-category sum, applying corrections such as `工业2022=3.9` and `工业2023=4.1` if supplied.
4. Generate the chart only after the totals match the extracted table, and include `单位：亿㎡` plus the source/time scope in the subtitle.
