# 证据合约

所有路径均相对于单次 `<RUN_DIR>`。业务证据必须来自本次运行，不允许从示例目录复制。

| 阶段 | 必需文件 | 关键约束 | 必需命令标签 |
|---|---|---|---|
| `00_intake` | `request.json`, `approval.json`, `skill_inventory.json`, `environment_preflight.json` | 模式和参数固定；本地/平台股票池分离；预检未过期；五个 Skill 和关键脚本哈希齐全 | `skill_inventory` |
| `01_source_replication` | 通用：`task_packet.json`, `manifest.json`, `final_delivery_summary.md`, `factor_formula.md`, `member_handoff.json`；快速/标准另需 `data_call_receipt.json`, `compact_backtest.json` | 指定子 Agent 独立执行；manifest 完成；真实数据源与运行历史非空；快速/标准须有正行数接口回执和至少 20 期实际回测；交接哈希一致 | `source_quality_gate` |
| `02_factor_candidates` | `task_packet.json`, `candidates.jsonl`, `candidate_review.md`, `member_handoff.json` | 指定子 Agent 独立执行；标准版至少 4 个、审计版至少 10 个唯一候选，公式、方向、假设与参数齐全 | 无 |
| `03_platform_preflight` | `task_packet.json`, `preflight.json`, `balance.json`, `approval_snapshot.json`, `member_handoff.json` | PandaAI 子 Agent 独立执行；认证、余额、CLI 全通过；收费批准绑定当前候选 SHA-256、候选 ID 和预算 | `platform_bootstrap`, `platform_balance` |
| `04_platform_execution` | `task_packet.json`, `run_ids.txt`, `result-cache/summary.json`, `candidates.report.csv`, 原始结果 JSON, `member_handoff.json` | PandaAI 子 Agent 再次独立执行；每个 run ID 有成功结果，汇总无失败 | `platform_factor_run`, `platform_collect_results` |
| `05_statistical_audit` | `task_packet.json`, `selected_returns.csv`, `trials_matrix.csv`, `overfit_report.json`, `member_handoff.json` | 审计子 Agent 独立执行；固定 `date,return`；至少 30 期、至少 10 个真实试验、PBO 非空 | `overfit_report` |
| `06_tearsheet` | `task_packet.json`, `tearsheet.json`, `tearsheet.html`, `member_handoff.json` | 报告子 Agent 独立执行；期数与已审计收益样本一致，HTML 自包含 | `tearsheet` |
| `07_final_review` | `expert_handoffs.json`, `final_report.md` | 标准/审计恰好五个真实成员；快速版恰好一个资料复现成员；调用 ID 与证据路径存在；结论符合模式 | 无 |

快速版只激活 `00_intake`、`01_source_replication`、`07_final_review`。标准版和审计版激活全部八阶段。未激活阶段既不是“可选跳过”，也不能被调用；守卫不会为它创建状态。

`data_call_receipt.json` 必须登记：接口/方法、实际参数、成功状态、正行数、数据日期范围和关键字段。`compact_backtest.json` 必须登记：`executed=true`、至少 20 期、至少滞后 1 期、非负交易成本、真实数据源、图表数量和 `total_return`、`annualized_return`、`sharpe`、`max_drawdown`。缺少任一项均不能写“已验证”。

## 子 Agent 调用证据

每个业务阶段都必须包含 `task_packet.json` 和 `member_handoff.json`。守卫校验：

- 成员 ID、绑定 Skill 和阶段与 `agents/team.json` 的固定路由一致；
- `context_isolated=true`；
- `invocation_id` 非空；
- 任务包输入和成员交接证据的 SHA-256 与磁盘文件一致；
- 交接证据覆盖阶段全部必需业务文件。

这证明本地交接结构自洽。只有宿主平台真实返回的 AgentTool 调用 ID 才能进一步证明线上发生了子 Agent 调用；`local-fixture-*` 或 `local-smoke-*` 只能用于本地测试。

## 命令回执

`workflow_guard.py exec` 会在以下目录写入回执和日志：

```text
command_receipts/<stage>/<timestamp>-<label>.json
command_logs/<stage>/<timestamp>-<label>.stdout.log
command_logs/<stage>/<timestamp>-<label>.stderr.log
```

回执包含：

- 实际 argv；
- 启止时间；
- 退出码；
- stdout/stderr 日志路径及 SHA-256；
- 是否通过命令白名单。

失败命令同样保留，但不满足阶段所需标签。

## 阶段回执

`seal` 校验文件内容后，生成 `stage_receipts/<stage>.json`，其中记录每个证据文件的：

- 相对路径；
- 字节数；
- SHA-256；
- CSV 行数、列数与可识别日期范围；
- JSON 顶层类型。

`finalize` 会重新计算哈希。封存后修改任何证据，最终验证都会失败，必须重新封存该阶段及其后续阶段。

## 完成回执

`completion_receipt.json` 至少包含：

- task ID 和 run ID；
- 当前模式所有激活阶段回执的 SHA-256；
- 当前模式真实调用的成员 Agent ID，以及专家团依赖的五个 Skill 名称；
- 最终结论；
- 过拟合审计 PASS/FAIL；快速版明确为 `null`，不得伪造；
- 生成时间。

这个文件证明流程证据在最终验证时自洽，不证明未来收益，也不能替代平台侧 `tool_choice=required`。

## 明确禁止

- 把 Markdown 中的“已执行”当回执。
- 用伪造或随机生成的数据通过业务验证。
- 只保留最佳候选，删除失败试验。
- 用 PandaAI 逐股因子值 CSV 代替策略收益。
- 把命令退出码非零描述为“数据为空”。
- 把过拟合审计 FAIL 改写成 PASS。
