# 版本与样本外治理

每个版本记录父版本、唯一变更、冻结时间、数据指纹、代码hash、参数hash和状态。无工件时称“按规格重建候选”，不称恢复成功。

训练集可拟合；验证集可选择；holdout只在全部规则冻结后查看一次。任何被查看或调参的数据都标已见，无法恢复未见身份。

预注册的单因素敏感性可以在最终样本比较一次，但查看后不得继续搜索。结果只能描述该区间差异，不称永久最优或归因于单一参数。

答案中直接提供可复制 manifest，**写全即算交付，不必另附文件**；只有承诺了文件或用户点名要文件时，才另外产出 manifest 文件并在正文写出文件名。例如：

```json
{
  "version": "V46-10d",
  "parent": null,
  "change_from_parent": null,
  "spec": {"quality_weight": 0.6, "momentum_weight": 0.4, "rebalance_days": 10},
  "data": {"train": "2020-2023", "validation": "2024", "final_test": "2025H1"},
  "sample_roles": {"2024": "seen_and_tuned", "2025H1": "seen_after_preregistered_once"},
  "code_hash": null,
  "data_hash": null,
  "environment": null,
  "registration_time": null,
  "artifacts": [],
  "verification_status": "not_reproduced",
  "missing_reason": "source code, daily NAV and trade ledger not provided"
}
```

另建 V46-20d，仅修改 `rebalance_days`，其余字段一致。不得称换手变化“机械成立”或收益差是“噪声”，只能写摘要观察且原因/显著性无法验证。

验收依赖精确规格、交易台账、独立实现和确定性勾稽，不以训练期“量级合理”人工校准。
