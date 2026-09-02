# Skill 1 · 附录 03：跨期校验规则（S1 / S2）

> **触发阅读条件**：执行 merge / 跨期校验 / 规则告警排查时。

## 规则 S1：本期上期 vs 上期本期一致性

**场景**：本期年报中披露的"上期数据"，应与上期年报中披露的"本期数据"一致。

**处理流程**：
1. 对每个指标，将本期年报中的上期列数值，与上期年报中的本期列数值进行比对
2. 如果两者不一致，生成 `⚠️ 跨期数据不一致` 提示，记录：
   - 指标名称
   - 本期年报中的上期值
   - 上期年报中的本期值
   - 差异金额/差异率
3. 同时检索本期年报附注中是否有"追溯调整""会计政策变更""重述"等口径变化说明
4. 如找到口径变化说明，在提示中附上原文
5. 如未找到口径变化说明，标注 `⚠️ 未找到口径变化解释，需人工确认`

**输出格式**（在 `~/RetailAnalysis/data/standard/<bank>.json` 的 `by_period.<period>.warnings` 中，或单独追加一条 `alerts` 数组）：

```json
{
  "alert_type": "cross_period_inconsistency",
  "bank": "某某银行",
  "metric": "零售分部营业净收入",
  "current_report_prior_value": 85000,
  "prior_report_current_value": 83500,
  "difference": 1500,
  "difference_pct": "1.80%",
  "calibration_change_found": true,
  "calibration_change_text": "因会计准则调整，对2024年度比较数据进行追溯重述...",
  "source_page": 256
}
```

## 规则 S2：细项加总校验

**场景**：各细项数据加总后应等于合计数。

**典型项**：
- 个人存款活期 + 定期 ≈ 个人存款合计
- 信用卡 + 按揭 + 消费 + 经营 + 其他 ≈ 个人贷款合计

**处理**：差异率 > 0.5% 生成 `⚠️ 细项加总不等于合计`（由编排器内置执行，无需 Agent 手动触发）。

## 两道校验（自动执行）

1. **单指标校验**（`fine_extractor.validate_extraction`）：
   - value 类型、单位一致性、`valid_range` 量程校验
   - 不合规自动降级 confidence + 追加 warning
2. **规则 S2 细项加总校验**（编排器内置）

**产物**：`~/RetailAnalysis/data/partial/standard_<bank>_<period>.json`

```json
{
  "bank": "某某银行", "period": "2025年度",
  "metrics": [...],
  "warnings": [ "⚠️ 细项加总不等于合计（规则 S2）：..." ]
}
```
