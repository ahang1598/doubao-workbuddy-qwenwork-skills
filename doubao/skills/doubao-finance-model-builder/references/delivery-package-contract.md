# 建模交付包协议

正式任务把主要交付物与审计附件分开。不得用附件数量代替模型质量。

## 必需文件

- `execution-plan.json`：范围、证据、模型和质量门计划；
- `data-source-ledger.json`：逐字段数据来源、链接、期间、口径、调整和冲突选择；
- `assumption-evidence-matrix.json`：历史数据、业务驱动、预测逻辑、模型参数和失效条件的证据链；
- 所有正式任务增加 `announcement-sweep.json`、官方公告证据目录及 `announcement-sweep-validation.json`；
- 正式DCF或可比公司任务增加 `equity-evidence.json`、本地 `evidence/` 目录及 `equity-evidence-validation.json`；
- 模块标准化输入 JSON；
- 模块确定性计算输出 JSON；
- 计算验证 JSON；
- 三表、DCF、LBO或可比公司正式任务的公式工作簿；LBO与可比公司默认只交付一个用户可见Excel，主要报告只能在用户明确要求时作为辅助交付物；
- `delivery-audit.json` 与交付验证 JSON；所有工作流另须生成 `artifact-audit.json`，公式工作簿同时生成`workbook-inspect.json`并由直接审计器重新打开检查，报告与确定性计算哈希绑定；
- `run-record.json`：阶段、状态、警告、硬失败和脚本版本；
- `artifact-manifest.json`：文件角色、大小和 SHA-256；
- `formula-contract.json`：业务字段、公式语义、单位、允许依赖和禁止依赖；
- `model-contract.json`：prompt必需驱动、关键公式路径、场景映射、维度恒等式、反向DCF闭环和模型检查单元格；
- `cell-map.json`：冻结布局中字段ID到工作表单元格或命名区域的映射；
- `cell-lineage.json`：关键输入、公式和输出的实际追溯，必须由最终工作簿回读生成，不得人工填写；
- `formula-semantic-audit.json`：错引、文本引用、循环依赖、单位和公式合约审计。
- `model-audit.json`：统一模型审计结果，绑定最终工作簿哈希；不得以工作簿内手填PASS替代。
- `quality/`：按`references/model-and-artifact-controls.md`生成G0至G5、统一质量报告、结论发布决定和哈希清单。

## 主要交付物

三表、DCF、LBO和可比公司正式任务只能以公式工作簿作为默认主要交付物。LBO与可比公司默认用户交付面收敛为一个Excel，结论、方法、来源、风险和审计说明写入工作簿；执行计划、JSON、日志和来源台账仅作为机器复核附件。只有用户明确要求额外格式时才附独立报告，且不取消工作簿义务。

## 统一质量结果

原子验证结果不再由执行者汇总手填`stage-results.json`。运行：

```bash
python3 scripts/quality/run_quality_gates.py \
  --root <任务目录> \
  --workflow dcf \
  --hero outputs/model.xlsx \
  --output-dir quality
```

统一执行器只读取原子验证文件和最终工作簿，不修改主要交付物。它生成`g0-task.json`至`g5-delivery.json`、`quality-report.json`、`release-decision.json`和`artifact-manifest.json`。任何硬失败使总体状态为`FAIL`；没有失败但检查或证据缺失时为`INCOMPLETE`。旧`finalize_delivery_package.py`仅用于兼容已有任务，不再作为新任务的结论权限来源。

## 单元格追溯

`cell-lineage.json` 每条记录至少包含：

`field | sheet | cell_or_range | role | source_ids | assumption_ids | scenario | notes`

角色使用 `input`、`formula`、`check` 或 `output`。估值基准日、WACC、永续增长率、分证券股数/价格、企业价值、股权价值、每股价值和模型状态必须有追溯记录。

## 打包检查

- 文件真实存在，大小非零，哈希可复算；
- 清单路径使用交付包内相对路径；
- 主要交付物状态与交付验证一致；
- 最新公告增量检索覆盖至信息截止日，所有发现项已处置且验证为 `PASS`；
- 工作簿无外部链接、无公式错误、无模板示例冒充公司数据；
- 关键公式实际依赖与语义合约一致，无文本标签参与数值运算、无自引用或循环依赖、无错误单位和错误期间引用；
- `workbook-inspect.json`的工作簿哈希与主要交付工作簿一致，隐藏区域、错误值和数据验证已纳入检查；
- `cell-lineage.json` 引用的工作表和单元格真实存在；
- 所有用户可见工作表完成视觉检查。
- G0至G5全部为`PASS`，`release-decision.json.conclusion_allowed=true`；否则不得在报告或最终回答中显示被压制的估值和回报结论。

<!-- END OF FILE: delivery-package-contract.md -->
