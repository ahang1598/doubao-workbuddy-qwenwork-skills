# Tool Score → Tag Mapping Guide

Use this reference to convert raw tool outputs into the standard tags of the skill. Always record the original tool value in the “Tool Relevancy / Grade” or Notes column.

## 相关度 Mapping

### SellerSprite / Sif 筛查相关性 (preferred)
| Tool grade / occupancy | Skill 相关度 tag | Action bias |
|------------------------|------------------|-------------|
| 高相关 (≥60%) | 高相关 | Title + Exact, P1 candidate |
| 中相关 (20–60%) | 中相关 | Bullets / Phrase, P2 |
| 低相关 (5–20%) | 低相关 | Backend or test only |
| 不相关 (<5%) | 不相关 | Negative candidate |

SellerSprite 相关度分数 (0.5–100): treat ≥50–60 as high (calibrate by category), 20–50 medium, <20 low. Prefer the occupancy-based 筛查结果 when both exist.

### Jungle Scout Relevancy Score
Map relatively inside the list or use approximate bands (e.g. ≥80 high, 50–80 medium, <50 low). Always sanity-check page-1 results for final confirmation on P1 candidates.

### ABA signal
If Top 3 clicked ASINs are mostly your product type / direct competitors → boost toward 高相关. Large mismatch → demote.

### Sif-specific fields (high value)
- 转化表现标记: 购买转化词 → strong positive / P1 bias; 无效曝光词 → strong negative candidate
- 流量特征: 主词 / 精准词 / 精准长尾词 → use as supporting signal for 词性 and priority
- 周搜索量 + 流量占比: primary volume input when ABA SFR is empty
- 展示位置 / 数据来源 / 种子词: keep in Notes or Source for traceability

## 流量层级 Mapping

### ABA Search Frequency Rank (SFR) — preferred
| SFR range (typical) | Skill 流量层级 | Notes |
|---------------------|----------------|-------|
| ≤ 50,000 | 高流量 | Tighten to ≤20–30k in ultra-competitive categories |
| 50,000 – 200,000 | 中流量 | Adjust by category size |
| > 200,000 | 低流量/长尾 | |

SFR is ordinal (1 = most searched). Pair with tool monthly searches for absolute sense.

### Tool Monthly Searches / ABA Rank
Use relative ranking within the exported list + absolute thresholds (example: ≥5,000 high, 500–5,000 medium, <500 low). Different categories need different cutoffs.

## 优先级 Scoring Logic

Priority ≈ 相关度 weight (highest) + 流量 weight + conversion signal (Purchase Rate / ABA Conversion Share / proven STR converters)

- 高相关 + 中高流量 + good conversion → **P1**
- 中相关 or 高相关 + mid volume → **P2**
- Remaining useful long-tail / low volume → **P3**
- 不相关 / clear waste → Negative (do not assign P1–P3)

## Sif-specific traffic labels (record in Notes or extra column)

- 主词 / 核心大词
- 精准长尾词
- 出单词
- 流失词
- 无效曝光词
- 泛需求词

These are complementary to 词性 and help PPC & monitoring decisions.

## Word-frequency / Root analysis (SellerSprite & Sif)

Use the high-frequency roots to accelerate 词性 assignment:
- Dominant product-name roots → 核心产品词 / 类目大词
- Material, color, size, tech roots → 属性词
- Benefit / problem roots → 功能卖点词
- Location / occasion roots → 场景词
- Audience roots → 人群词

Manual review only needed for ambiguous or multi-root phrases.

## Conflict resolution

1. Relevancy: SellerSprite/Sif occupancy grade > Jungle Scout score > pure judgment
2. Volume: ABA SFR > tool monthly searches
3. When scores conflict, keep both values in Notes and choose the more conservative tag for P1 decisions
4. Always surface low-confidence or conflicting rows for human review
