# Skill 2 · 附录 03：校验规则 T1 / T2 / T3

> **触发阅读条件**：执行 merge / 跨期校验 / 规则告警排查时。

## 规则 T1：反推校验——本期值与变动推算的上期值 vs 上期披露值

**场景**：文字描述中同时披露了"本期规模"和"本期变化"，可据此反推出上期规模。如果反推值与上期年报中披露的值不一致，说明口径可能发生变化。

**处理**：
1. 对每个同时具有 `period_end_value` 和 `change_value` 的指标，计算：
   `反推上期值 = period_end_value - change_value`（或 `= period_end_value / (1 + change_pct/100)`）
2. 与上期年报中提取的同一指标值进行比对
3. 如差异超过 1%，生成 `⚠️ 反推上期值不一致` 告警，记录：
   - 指标名称
   - 本期披露的规模值和变动值
   - 反推的上期值
   - 上期年报中的披露值
   - 差异金额/差异率
4. 同时在本期年报文本中搜索是否有口径调整说明
5. 如找到，附上口径变化原文；如未找到，标注 `⚠️ 疑似口径变化，未找到解释`

**输出格式**（在 `$RA/data/text/<bank>.json` 的 `by_period.<period>.alerts` 数组中）：

```json
{
  "alert_type": "derived_prior_inconsistency",
  "bank": "某某银行",
  "metric": "零售AUM",
  "current_value": 45000,
  "current_change": 3500,
  "derived_prior_value": 41500,
  "actual_prior_value": 42000,
  "difference": -500,
  "difference_pct": "-1.19%",
  "calibration_change_found": false,
  "note": "疑似口径变化，未找到解释"
}
```

## 规则 T2：停披提示——上期披露但本期未披露

**场景**：某银行上期年报中披露了某项文字指标（如信用卡流通卡量），但本期年报中未找到该指标的披露。

**处理**：
1. 在 `merge` 阶段，通过 `--prior-partial` 传入上期 partial JSON 触发此校验
2. 对上期有值、本期 metrics 中未出现的指标，生成告警
3. 记录：指标名称、上期披露值、上期来源页码

**输出格式**：

```json
{
  "alert_type": "disclosure_discontinued",
  "bank": "某某银行",
  "metric": "信用卡有效卡量",
  "prior_period": "2024年度",
  "prior_value": 6800,
  "prior_unit": "万张",
  "prior_source_page": 45,
  "current_period": "2025年度",
  "current_value": null,
  "note": "上期(2024年度)披露该指标，本期(2025年度)未找到对应披露"
}
```

## 规则 T3：口径变化关联检索

当规则 T1 或 T2 触发时，主 Agent 在本期年报的以下位置搜索口径变化说明：
- 零售业务章节的脚注/注释
- "重要会计政策变更"章节
- "本期与上期数据差异说明"
- 管理层讨论与分析的"口径说明"段落

## 执行时机

- **T2**：在 `prepare_text_extraction.py merge` 阶段自动执行（需要 `--prior-partial` 参数）
- **T1、T3**：跨期视野，由**主 Agent**在所有 member / 子代理完成后统一执行（详见主 SKILL.md 的 Step 5）
