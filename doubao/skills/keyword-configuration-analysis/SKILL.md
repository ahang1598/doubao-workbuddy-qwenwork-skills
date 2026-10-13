---
name: keyword-configuration-analysis
description: Use when the user asks for keyword configuration, keyword screening, ad diagnosis, bidding suggestions, spreadsheet analysis, configuration updates, lexicon maintenance, Search Term optimization, negative keywords, or campaign performance analysis from lists, config files, Excel/CSV sheets, screenshots, or reports.
---

# Keyword Configuration Analysis

Use this skill to turn keyword lists, ad reports, backend configs, or spreadsheet data into executable keyword updates, Search Term drafts, campaign layers, negative-word lists, or performance conclusions.

## Workflow

### 1. Confirm platform, scope, and deliverable before finalizing

- Confirm at least: platform/site, product or business object, keyword purpose, analysis window, input source, output format, and whether the task is read-only analysis or config editing.
- Concrete conventions from evidence:
  - For 小红书聚光 analysis, respect the user's module boundary: if they say only analyze `聚光数据汇总` for `7.9-8.3` weekly data, do not mix in `聚光定向消耗` for the same date range until they ask for targeting analysis.
  - For 聚光 reporting, if the user says `cpuv` is the main KPI, rank optimizations by lower `cpuv` first; use other fields as diagnostics, not the primary score.
  - For Amazon Search Term work, confirm site/language and whether the field is backend `Search Term` rather than title, bullets, description, or product highlights. Search Term is for supplemental traffic terms that cannot fit front-end copy, not for repeating every visible term.
  - For Amazon Italy ads, confirm target language and product sizing before accepting keywords: a Montessori bed with `120×200` and `140×200` should not automatically negate `matrimoniale`, because `140×200` can map to small double-bed searches.

### 2. Read structure and locate the authoritative fields

- Inspect workbook sheets, screenshots, table headers, config variables, and current keyword arrays before extracting or editing.
- Concrete conventions from evidence:
  - In 聚光 keyword reports, expected analysis columns include `搜索主题`, `消费`, `展现量`, `点击量`, `ctr`, `cpc`, `cpm`, `进店uv`, `转化率`, `cpuv`, and `小红星任务期阅读UV`; preserve rows where computed columns display `#DIV/0!` as zero-denominator cases rather than treating them as text metrics.
  - In 聚光 keyword-planning data, the comparable planning fields are `关键词`, `推荐理由`, `竞争指数`, `月搜索指数`, and `市场出价`; cross-check these against actual delivery fields by exact keyword text.
  - In keyword collection scripts, update only the target keyword list such as the war-news list. If there are separate AI and war keyword lists, keep AI keywords unchanged when the user only says `美伊战争类关键词仅保留...`.
  - In Amazon listing/Search Term work, read `SKU主数据表.xlsx`, product selling-point/spec sheets, and keyword files such as `花瓶关键词.xlsx` together; compare candidate backend terms against front-end fields: `标题`, `商品亮点`, `五点说明`, and `产品描述`.

### 3. Clean keywords and metrics with explicit formulas

- Normalize keyword text, language, currency, percentages, and invalid spreadsheet values before calculating or comparing.
- Concrete conventions from evidence:
  - 聚光 `CTR` is `点击量 / 展现量`; when `展现量=0`, report it as zero-denominator or `#DIV/0!`, not as a real 0% performance signal.
  - 聚光 `CPC` is `消费 / 点击量`; when `点击量=0`, do not rank the row by CPC because the source may show `#DIV/0!`.
  - 聚光 `转化率` is `进店uv / 点击量`; this is the rate used in evidence where `华伦料理棒` had high conversion because many clicks became `进店uv`.
  - 聚光 `cpuv` is `消费 / 进店uv`; lower is better. When `进店uv=0`, mark `cpuv` as undefined/zero-conversion instead of using infinity in a ranked table.
  - When checking planning-vs-actual cost, compute actual-to-planning CPC ratio from actual `cpc` divided by planning `市场出价`; do not compare planning `市场出价` to `cpuv`.

### 4. Filter by relevance, language, and campaign intent

- Separate core, expansion, test, negative, and excluded terms by product fit and intent before looking only at volume or bid price.
- Concrete conventions from evidence:
  - For 华伦料理棒, `料理棒`, `华伦料理棒`, and `料理棒推荐` are direct category/brand terms; `辅食工具`-type terms are broader and need actual `cpuv`/`进店uv` validation before scaling.
  - For 华伦料理棒, competitor terms like `博朗料理棒` are not core brand terms; if used, label them as competitor conquest/test words and explain the risk and creative angle.
  - For Amazon vase Search Terms, avoid repeating front-end-covered terms when the title/bullets/description already contain them, such as `Ceramic`, `Pottery Vase`, `Watertight`, `Modern Coastal`, `housewarming`, `wedding`, `holiday`, `entryway`, `shelf`, `mantel fireplace`, `dining table`, and `kitchen counter`.
  - For Amazon Italy bed ads, discard non-target-language or wrong-product terms unless the user explicitly wants them. Examples from evidence: `toddler bed travel` is not a Montessori floor bed term; `culla`, `lettino neonato`, `materasso`, `letto contenitore`, `divano letto`, `letto a castello`, and `usato` are negative candidates when not sold.

### 5. Layer outputs and actions by match type or use case

- Make the output directly usable: separate add/keep/remove, exact/phrase/broad, positive/negative, or core/long-tail/test terms.
- Concrete conventions from evidence:
  - For Amazon Italy advertising, use `精准`, `词组`, and `广泛` as distinct match-type layers; for negatives, separate `否定词组` from `否定精准`.
  - For negative keywords in the Italy bed case, put broad unsuitable categories in `否定词组` and reserve `否定精准` for exact blockers such as `ikea`, `materasso`, and `culla`.
  - For 聚光 keyword optimization, compare planning keywords and actual keywords in three groups: intersection terms already delivered, planning terms not yet delivered, and actual terms absent from planning data.
  - For Search Term drafting, combine data-supported terms with exploration terms only after classifying which are front-end duplicates, language variants, Spanish variants such as `jarrones`/`floreros`/`centro de mesa`, style terms, placement terms, and botanical-use terms.

### 6. Edit configs or generate importable artifacts safely

- If the task modifies files, use precise replacement and only touch the requested keyword list or specified field.
- Concrete conventions from evidence:
  - For the war-news classifier, replacing the war list changed the list from `74` to `51` keywords while AI keywords stayed at `79`; always validate target-list count and unchanged sibling-list count after editing.
  - When the user says a list should “仅保留” specific items, the old list is not a merge base: remove unlisted items such as `石油`, `原油`, `OPEC`, `欧佩克`, `油价`, `天然气`, `布伦特`, and `WTI` even if they are semantically related.
  - When creating keyword tables for ads, keep bid currency and match type together: examples include `€0.11`, `€0.23`, `€0.26`, `词组`, `精准`, and `广泛`; do not output a keyword without its intended matching or bidding handling when the user is configuring a campaign.
  - If exporting a spreadsheet or list, keep one row per keyword unless the user asks for grouped prose; include rule/status columns such as `新增`, `保留`, `暂停`, `否定`, `测试`, or `待验证`.

### 7. Validate quantities, conflicts, and claim boundaries

- Before final delivery, verify counts, formulas, duplicates, conflicts, and whether each conclusion is fact, assumption, or next test.
- Concrete conventions from evidence:
  - For config updates, print or summarize the final keyword count, newly added items, removed items, and unaffected keyword groups; mention that historical records are not reclassified unless the system actually backfills them.
  - For 聚光 analysis, validate that totals reconcile with source totals such as `总计` rows by recomputing `消费`, `展现量`, `点击量`, `进店uv`, and derived `cpuv`; do not average row-level `cpuv` to get total `cpuv`.
  - For Search Term choices, check that excluded terms are excluded because of a stated rule: front-end duplicate, poor relevance, off-position style such as `farmhouse rustic vintage` for a modern coastal vase, competitor risk, wrong language, or missing evidence.
  - For bid or budget recommendations, separate observed facts (`actual cpc` lower than `市场出价`, `进店uv=0`, `cpuv` undefined) from hypotheses (`broad match may be drifting`, `decision-stage users may convert`) and from tests to run.

## Boundaries and prohibitions

- Do not produce a final keyword plan before confirming platform, site, purpose, and scope when those are missing; for 聚光, distinguish `聚光数据汇总` from `聚光定向消耗` and honor the stated window such as `7.9-8.3`.
- Do not ignore sheet names, headers, field definitions, date ranges, or user-stated exclusions; if source fields like `搜索主题`, `消费`, `展现量`, `点击量`, `进店uv`, `cpuv`, `月搜索指数`, or `市场出价` are absent, state the limitation instead of calculating substitutes.
- Do not invent metrics, search volume, CPC, ACOS, ROAS, SOC/SOV, or conversion data when the source lacks them; `#DIV/0!` in `cpuv` or `cpc` means the denominator is zero, not a usable numeric value.
- Do not put competitor, off-language, or visibly unrelated terms into core targeting unless the user explicitly requests conquesting or exploration; keep `博朗料理棒` as competitor-test, not core brand traffic for `华伦料理棒`.
- Do not update unrelated config logic, sibling keyword groups, schedules, document IDs, or scripts when only keywords are requested; in the war-news case, `美伊战争` keywords changed from `74` to `51`, while AI keywords remained `79`.
- Do not use summary or pre-aggregated tables as the sole authority when row-level data is available; recompute totals from rows with `消费`, `点击量`, and `进店uv`, then use `总计` only to reconcile.

## Minimal example

User asks: “这个是聚光平台关键词规划工具的数据，结合我们投的关键词分析，品牌是华伦料理棒。”

Response shape:
1. Confirm sources: planning fields `月搜索指数/市场出价/竞争指数` and actual fields `搜索主题/消费/点击量/进店uv/cpc/cpuv`.
2. Recompute formulas: `cpc=消费/点击量`, `cpuv=消费/进店uv`, `转化率=进店uv/点击量`.
3. Split terms into: already delivered intersection terms, planning-only opportunities, actual-only terms.
4. Mark actions: add budget to low-`cpuv` direct terms, test competitor/decision terms separately, pause zero-`进店uv` broad terms, and list assumptions separately from facts.
