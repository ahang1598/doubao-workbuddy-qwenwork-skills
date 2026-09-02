---
name: amazon-keyword-library-builder
description: Build a complete Amazon keyword library from mined tool data. Accept SIF, ABA, SellerSprite, Jungle Scout or mixed exports, then classify and tag with 词性, 流量层级, 相关度, 优先级, 建议位置. Automatically split 肯定词库 and 否定词库, run 1-gram and 2-gram root frequency analysis, and extract phrase-level negative roots. Use when sellers need full keyword library after mining, 关键词词库建设, 打标分类, 否定词根, 埋词词库, or when feeding SIF or ABA results into structured tagging. Triggers on 词库建设, 关键词打标, 肯定否定分流, 词根词频, negative phrase extraction, keyword library from tools.
---

# Amazon Keyword Library Builder

## Overview

End-to-end pipeline that turns **raw mined keyword data** into a production-ready keyword library.

**Design principle**
- Mining stays upstream (SIF reverse lookup, ABA, search-suggestion expansion, SellerSprite, reviews). This skill does **not** re-mine.
- This skill only **consumes** the mined results and applies tool-score-first classification + positive/negative split + root analysis + negative-phrase extraction.
- Main tagged table stays **simple**. Extra sheets deliver the operational value (肯定/否定词库, 词根词频, 否定词根建议).

**Core outputs**
1. Simple tagged master table
2. 肯定词库
3. 否定词库
4. 词根词频 (positive + negative, 1-gram + 2-gram)
5. 否定词根建议 (high / medium priority phrase negatives + exact negatives)

## When to use

- User already has a SIF export, ABA list, SellerSprite keyword list, or mixed mining result
- User finished keyword mining and needs structured tagging + negative roots
- User wants a complete library for Title / Bullets / Backend / PPC Exact-Phrase + Negative

## Instructions

### 0. Required context (ask if missing)

1. **Product core**
   - Product name, key features, target audience, main scenarios
   - Own brand (if any)
   - 3–8 competitor ASINs (strongly preferred)

2. **Input data**
   - File or table from SIF / ABA / SellerSprite / Jungle Scout / Search Term Report / mixed
   - Confirm which columns are present (see mapping below)

3. **Goal**
   - Default = full multi-sheet library
   - Or listing-only / PPC-only / negative-focused

Do not invent relevancy or volume. If critical columns are absent, note low confidence and still produce best-effort tags.

### 1. Input field mapping (SIF-first, then others)

Prefer these columns when present (Chinese or English names):

| Logical field | Common source columns |
|---------------|-----------------------|
| Keyword | 关键词, Keyword, Search Term, Customer Search Term |
| Volume | 周搜索量, Searches, Monthly Searches, ABA SFR, Search Frequency Rank |
| Relevancy signal | 转化表现标记, 相关度, Relevancy Score, 页面占比, occupancy |
| Traffic type | 流量特征 (主词 / 精准词 / 精准长尾词 / 出单词 / 无效曝光词) |
| Rank | 自然排名, Organic Rank |
| Traffic share | 流量占比, 自然流量占比 |
| Conversion | 点击转化率, Purchase Rate, ABA 转化占比 |
| Source | 数据来源, 扩展来源, 种子词, Source |
| Position | 展示位置 (自然搜索 / SP 等) |

**Sif 转化表现标记 → 相关度 bias**
- 购买转化词 / 高质量转化词 / 稳定转化词 → strong positive bias
- 转化流失词 → keep, mark for optimization
- 无效曝光词 → strong negative candidate

Preserve original tool values in Notes or extra columns. Never overwrite them.

### 2. Clean

- Deduplicate exact and near-duplicates
- Drop zero-volume nonsense or clear wrong-category terms
- Keep misspellings and variants (route to Backend later)
- Keep all original tool scores and labels

### 3. Multi-dimensional tagging (tool scores first)

#### 3.1 相关度
Order of preference:
1. Sif / SellerSprite occupancy or 转化表现标记
2. Explicit relevancy grade / score
3. ABA Top-3 ASIN similarity
4. Product-context judgment (mark low confidence)

Grades: 高相关 / 中相关 / 低相关 / 不相关

#### 3.2 流量层级
Prefer ABA SFR:
- 高流量 ≈ SFR ≤ 50k (tighten in ultra-competitive categories)
- 中流量 ≈ 50k–200k
- 低流量/长尾 ≈ > 200k

Else use 周搜索量 / Monthly Searches with relative ranking inside the list.

#### 3.3 词性
Use root frequency first when available, then product context.

Main tags: 核心产品词, 类目大词, 属性词, 功能卖点词, 场景词, 人群词, 规格参数词, 长尾修饰词, 自有品牌词, 竞品品牌词, 关联互补词, 礼品词, 否定词

See `references/taxonomy-details.md`.

#### 3.4 优先级
- P1 = 高相关 + 中高流量 + conversion signal → Title + Exact PPC
- P2 = 中相关 or high-relevancy mid-volume → Bullets / Phrase
- P3 = long-tail high-relevancy or experimental → Backend / Broad

#### 3.5 建议位置
Title / 五点 / 描述A+ / 后台 / Exact PPC / Phrase / Broad / Negative

See `references/placement-mapping.md`.

### 4. Positive / Negative split

- **肯定词库**: 高相关 + 中相关 (+ any strong purchase-conversion terms that still fit the product)
- **否定词库**: 低相关 + 不相关 + 无效曝光词 + clear semantic mismatches

This split is the input to root analysis and negative extraction.

### 5. Root frequency analysis (1-gram + 2-gram)

Run separately on 肯定词库 and 否定词库.

Algorithm (see `references/root-and-negative-logic.md`):
1. Normalize (lower-case, trim)
2. Tokenize on spaces
3. Generate 1-grams and ordered 2-grams
4. Count frequency (optionally search-volume weighted)
5. Filter pure stop combinations carefully; keep intent phrases (`for women`, `with pockets`, `plus size`)
6. Output sorted tables labeled 1-gram / 2-gram

### 6. Automated negative root & 2-gram phrase extraction

Core metric:
```
negation_strength = neg_count / (pos_count + 1)
```
(or volume-weighted)

Decision order:
1. Force-list hit → high-priority phrase negative
2. Protect-list hit → never auto-promote
3. strength ≥ 3 and support ≥ 3 (or 5) → high-priority
4. strength 1.5–3 → medium, human confirm
5. Semantic conflict (wrong audience, opposite function, low intent) → boost
6. Prefer 2-gram over 1-gram when both qualify

Output three layers:
- High-priority Negative Phrase
- Medium-priority (review)
- Exact-negative full keywords

Update force/protect lists per product category before extraction. Templates in `references/root-and-negative-logic.md`.

### 7. Output Excel structure (required)

**Sheet 1 — Tagged Keywords (simple core, never drop)**

| Keyword | 词性 | 流量层级 | 相关度 | 优先级 | 建议位置 | Search Volume / ABA Rank | Notes | Source |

Sort by 优先级 → 流量层级 → 相关度.

**Sheet 2 — Summary**
- Counts by 词性 / 相关度 / 优先级
- Title seed list
- Backend candidates
- Confidence / logic notes for top terms

**Sheet 3 — 肯定词库**
Positive keywords + original useful tool fields when available.

**Sheet 4 — 否定词库**
Negative keywords + original useful tool fields.

**Sheet 5 — 词根词频_肯定**
1-gram + 2-gram from positive set.

**Sheet 6 — 词根词频_否定**
1-gram + 2-gram from negative set.

**Sheet 7 — 否定词根建议**
Ranked phrase negatives with strength, support, examples, priority, 1-gram/2-gram flag + exact-negative full list (or reference).

If user only wants the simple table, deliver Sheet 1 + Summary. Default is the full library.

### 8. Special rules

- Competitor brands → PPC only, never organic Title/Backend
- Own brand → careful, usually not in Backend search terms
- New ASIN / thin data → bias to high-relevancy long-tail first
- Tool score conflicts → prefer Sif/SellerSprite conversion or occupancy for relevancy + ABA SFR for volume; record conflict in Notes
- Chinese + English keywords supported; keep tag language consistent with user

### 9. Iteration

After delivery:
- Accept user corrections on borderline rows
- Re-run root analysis and negative extraction if the positive/negative split changes
- Optionally draft Title / Bullets from P1+P2
- Export Backend-only list (byte-aware ≤249 bytes)

## References

- `references/taxonomy-details.md` — 词性 examples
- `references/placement-mapping.md` — placement rules
- `references/tool-score-mapping.md` — ABA / SellerSprite / Jungle Scout / Sif mapping
- `references/root-and-negative-logic.md` — full 1-gram/2-gram algorithm, negation strength, force/protect lists, decision rules
- `assets/keyword-tagging-template.xlsx` — base template (extend with extra sheets)

## Integration note for upstream mining

This skill expects **already mined** keyword rows. Typical upstream sources:
- SIF ASIN reverse lookup (转化表现标记, 流量特征, 周搜索量, 自然排名…)
- ABA Brand Analytics (SFR, click share, conversion share)
- SellerSprite / Jungle Scout keyword exports
- Search Term Report converters
- Search-suggestion expansion results (T1/T2/T3 style)

Do not re-implement mining inside this skill. Accept the data, map columns, tag, split, analyze roots, extract negatives, and deliver the library.
