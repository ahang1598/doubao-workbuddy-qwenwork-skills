# Root Frequency Analysis & Negative Phrase Extraction Logic

This reference encodes the algorithms and decision rules adopted from the discussion.

## 1. Root Frequency Analysis (词根词频)

### Goals
- Accelerate 词性 assignment.
- Surface high-value modifiers for Title / Bullets.
- Feed negative-root extraction by comparing positive vs negative sets.

### Algorithm
1. **Normalize**
   - Lower-case
   - Trim extra spaces
   - Optional light plural normalization (dresses → dress) — apply consistently or not at all
2. **Tokenize**
   - Split on whitespace
3. **Generate n-grams**
   - 1-gram: every token
   - 2-gram: every consecutive pair (preserve order)  
     Example: `summer dresses for women` →  
     `summer dresses`, `dresses for`, `for women`
4. **Count**
   - Raw frequency
   - Optional search-volume-weighted frequency = Σ (search volume of keywords containing the n-gram)
5. **Filter**
   - Remove pure stop 2-grams that carry no intent (`of the`, `and a`, etc.)
   - Keep intent-bearing phrases (`for women`, `with pockets`, `plus size`, `tummy control`)
6. **Output**
   - Separate tables for 肯定词库 and 否定词库
   - Sort by frequency or weighted frequency descending
   - Include both 1-gram and 2-gram (label the type)

### Interpretation Rules
- Roots dominant in 肯定词库 → strong 词性 / placement signals
- Roots dominant in 否定词库 → primary candidates for phrase negation
- Roots frequent in both → usually core product language; protect them

## 2. Negation Strength Metric

```
negation_strength = neg_count / (pos_count + 1)
```

Weighted variant (preferred when volume data exists):
```
negation_strength_weighted = neg_weight / (pos_weight + 1)
```
where weight = sum of search volumes of keywords containing the n-gram.

## 3. Decision Rules for Promoting a Root / 2-gram to Phrase Negative

Apply in this order:

1. **Force-list hit** → High-priority Negative Phrase  
   Examples: cheap, free, used, for men, for boys, for kids, maternity, dog, cat, repair, refurbished, wholesale, diy

2. **Protect-list hit** → Never auto-promote  
   Examples (adjust per product): dress, summer, women, casual, beach, midi, sundress, vacation (when they are central to the offer)

3. **High-priority auto**  
   - negation_strength ≥ 3  
   - support (neg_count) ≥ 3 (or 5 for very large lists)  
   - not on protect-list  
   → High-priority Negative Phrase (prefer 2-gram when available)

4. **Medium-priority**  
   - strength 1.5–3  
   - or high support but moderate strength  
   → Flag for human review

5. **Low / rare**  
   - Only exact-negative the original full keywords  
   - Do not promote the root

6. **Semantic conflict boost**  
   Even if strength is moderate, promote when the root clearly indicates:
   - Different audience (men, kids, maternity, pet)
   - Opposite or missing function (tummy control when product has none)
   - Strong low-intent (cheap, free, used)

7. **Prefer 2-gram over 1-gram** when both qualify — lower collateral damage.

## 4. Output Layers for Negatives

Always produce three layers:

| Layer | Content | Use |
|-------|---------|-----|
| High-priority Negative Phrase | Strong 2-grams / force-list 1-grams | Add as Negative Phrase in campaigns |
| Medium-priority | Borderline roots | Human confirm before adding |
| Exact-negative full keywords | Original low-relevancy / 无效曝光 phrases | Negative Exact |

Optionally mark which full keywords are already covered by a promoted phrase root to avoid redundant maintenance.

## 5. Force-list & Protect-list (starting templates)

**Force (always consider for phrase negative):**
- cheap, free, used, refurbished, repair, replacement, diy, wholesale
- for men, for boys, for kids, for him, maternity, pregnant
- dog, cat, pet, puppy
- broken, damaged

**Protect (do not auto-promote even if strength high):**
- Core product nouns and primary modifiers that define the offer
- Example for summer dresses: dress, dresses, summer, sundress, women, womens, casual, beach, midi, maxi, vacation

Update both lists per product category before running extraction.

## 6. Practical Implementation Notes

- Run root analysis **after** the positive/negative split so the two sets are clean.
- When input is SIF-style, map 转化表现标记 = 无效曝光词 or low 流量特征 directly into the negative set.
- Re-run extraction whenever the user corrects the positive/negative split.
- 2-gram generation must preserve order; `for men` ≠ `men for`.
- Stop-word handling must be conservative — many “for X” and “with Y” phrases are high-value.
