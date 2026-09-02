# 完整执行 SOP

本 SOP 的目标是让一个能力一般、容易省略步骤的宿主模型也只能沿着可检查的路径工作。主 Agent 只负责编排，业务角色由独立上下文的子 Agent 执行。文字承诺不产生阶段状态，只有成员交接与本地守卫共同通过才产生状态。

## 三档路线

- `fast`：3–5 分钟，只走 `00_intake → 01_source_replication → 07_final_review`。必须有真实数据调用回执和至少 20 期的紧凑回测，不收费，不做候选、平台与统计审计。
- `standard`：10–20 分钟，默认模式，走完整八阶段。定向复现、至少 4 个候选、PandaAI 实跑和完整审计。
- `audit`：30–60 分钟，走完整八阶段。全文复现、至少 10 个候选、更完整的图表和审计留痕。

路线由 `scripts/mode_profiles.py` 固定，守卫只接受该路线中的阶段。所有模式都要求真实数据、实际执行和证据回执。

## 0. 运行目录与状态

每个研究任务使用全新的 `<RUN_DIR>`。禁止复用其他任务的 `workflow_state.json` 或 `completion_receipt.json`。先在运行目录外准备 `request.json`，其中分开填写 `local_replication_universe` 和 `platform_universe`；PandaAI 当前平台口径固定为 `沪深全A`。

```bash
python scripts/environment_preflight.py --mode <MODE> --request <REQUEST_JSON> --out <PREFLIGHT_JSON> --skill skill-report-replication=<PATH> --skill skill-factor-mining-pandaai=<PATH> --skill skill-pandaai-factor-online=<PATH> --skill skill-backtest-overfit=<PATH> --skill skill-strategy-tearsheet-report=<PATH>
python scripts/workflow_guard.py init --run-dir <RUN_DIR> --task-id <TASK_ID> --mode <MODE> --preflight-json <PREFLIGHT_JSON>
```

预检只读取运行能力和经白名单过滤的余额字段，不读取、保存或回显 token。环境与请求哈希未变化时复用模式对应 TTL 的缓存；预检失败或过期不能初始化。

初始化后状态只能按以下顺序变化：

```text
PENDING -> RUNNING/WAITING_APPROVAL -> VERIFIED
                                \-> BLOCKED
```

`VERIFIED` 由守卫写入；模型不得手工编辑 `workflow_state.json`。

## 0.1 子 Agent 上下文隔离

团队和阶段路由以 `agents/team.json` 为准。每个业务阶段开始前，主 Agent 必须：

1. 为该阶段创建 `task_packet.json`，只引用已封存输入的相对路径和 SHA-256；
2. 通过 AgentTool 调用清单中指定成员，不在主上下文中加载成员 Skill；
3. 把宿主返回的真实调用 ID 交给成员写入 `member_handoff.json`；
4. 只读取成员的结论、保留意见和证据路径，不把原始产物整段复制进主对话；
5. 由守卫在 `seal` 时校验任务包、成员身份、Skill、阶段、上下文隔离标志和证据哈希。

格式见 `references/member-handoff-schema.md`。本地结构测试可使用带 `local-fixture-` 前缀的调用 ID，但它不证明 WorkBuddy 已真实调用成员。

## 1. 受理与预算冻结

创建：

- `00_intake/request.json`
- `00_intake/approval.json`
- `00_intake/skill_inventory.json`
- `00_intake/environment_preflight.json`（由初始化复制，禁止手工伪造）

请求必须固定执行模式、研究命题、来源、本地复现股票池、PandaAI 平台股票池、起止日、调仓周期、样本外区间、交易成本和算力预算。`local_replication_universe` 可以是本地样本；`platform_universe` 在收费模式必须是 `沪深全A`，二者不得互相覆盖。`approval.json` 记录用户已经委托这次研究范围，必须包含用户原文、时间、`approved: true` 和完全相同的参数快照；它不授权消耗 PandaAI 算力。

先用本包脚本读取五个已安装 Skill 的 `SKILL.md` 和关键执行脚本，并生成哈希清单：

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 00_intake --label skill_inventory -- python <AGENT_ROOT>/scripts/build_skill_inventory.py --out 00_intake/skill_inventory.json --skill skill-report-replication=<PATH> --skill skill-factor-mining-pandaai=<PATH> --skill skill-pandaai-factor-online=<PATH> --skill skill-backtest-overfit=<PATH> --skill skill-strategy-tearsheet-report=<PATH>
```

若用户尚未批准收费运行，仍可完成无成本来源研究和候选设计；但不得创建虚假的收费批准。状态在候选交付后停在 `WAITING_APPROVAL`，不进入平台预检。

封存：

```bash
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 00_intake
```

## 2. 资料复现研究员

主 Agent 创建 `01_source_replication/task_packet.json`，通过 AgentTool 调用 `source-replication-researcher`。该成员使用 `skill-report-replication`。优先使用用户提供的原文；如只有研究命题，先找到可公开核验的原始论文或研报并记录 URL、标题、作者和发布日期。

真实产物映射到：

- `01_source_replication/manifest.json`
- `01_source_replication/final_delivery_summary.md`
- `01_source_replication/factor_formula.md`
- `01_source_replication/data_call_receipt.json`（快速版和标准版）
- `01_source_replication/compact_backtest.json`（快速版和标准版）

复现项目内部仍保留原 Skill 的完整目录。把最终三份交接文件复制或引用到本阶段，不能只写摘要而丢掉底层项目。

快速版和标准版使用紧凑质量门，要求接口、实际参数、状态、行数、日期范围、关键字段，以及真实回测期数、滞后、成本和指标：

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 01_source_replication --label source_quality_gate -- python <AGENT_ROOT>/scripts/compact_quality_gate.py --stage-dir <RUN_DIR>/01_source_replication --mode <fast|standard>
```

审计版使用来源 Skill 的完整质量门：

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 01_source_replication --label source_quality_gate -- python <REPORT_SKILL>/scripts/quality_gate_check.py <REPLICATION_PROJECT>
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 01_source_replication
```

质量门失败即停止。不得用合成数据证明因子有效。

成员最后生成 `01_source_replication/member_handoff.json`，其证据必须覆盖当前模式的全部必需业务文件。快速版封存本阶段后直接进入第 8 节主研究员会诊，禁止调用中间五个未激活阶段。

## 3. 因子工程师

主 Agent 创建 `02_factor_candidates/task_packet.json`，只传递已封存公式、来源摘要及其哈希，再通过 AgentTool 调用 `factor-engineer`。该成员使用 `skill-factor-mining-pandaai` 把复现公式翻译为 PandaAI 可执行候选。标准版至少提出 4 个、审计版至少 10 个有实质差异的候选，不能只改窗口数字制造重复。

每行 `02_factor_candidates/candidates.jsonl` 至少包含：

```json
{"candidate_id":"F001","formula":"...","direction":1,"hypothesis":"...","parameters":{"window":20},"source_anchor":"页码/章节/用户命题","decision":"proposed"}
```

同时生成 `candidate_review.md`，说明排除重复、方向、字段可得性、未来函数、股票池和成本假设。

成员最后生成 `02_factor_candidates/member_handoff.json`。

```bash
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 02_factor_candidates
```

## 4. 收费前预检与再次批准

主 Agent 创建 `03_platform_preflight/task_packet.json`，通过 AgentTool 调用 `pandaai-experimenter`。该成员使用 `skill-pandaai-factor-online`。登录由用户在官方 CLI 中交互完成，禁止把密码、验证码、token 放进命令回执。

守卫执行：

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 03_platform_preflight --label platform_bootstrap -- python <ONLINE_SKILL>/scripts/bootstrap.py
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 03_platform_preflight --label platform_balance --stdout-file 03_platform_preflight/balance.json -- pandaai-cli --json balance
```

创建 `preflight.json` 与 `approval_snapshot.json`。收费批准必须与候选 ID、`candidates.jsonl` 的 SHA-256、区间、调仓、预计消耗和预算一致。候选被修改后，旧批准自动失效。

成员最后生成 `03_platform_preflight/member_handoff.json`。未获收费批准时只返回 `WAITING_APPROVAL`，不得把本阶段封存为已完成。

```bash
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 03_platform_preflight
```

认证失败、余额不足或批准缺失时返回 `BLOCKED_EXTERNAL` 或 `WAITING_APPROVAL`。

## 5. PandaAI 实验员

主 Agent 在确认收费批准已封存后创建 `04_platform_execution/task_packet.json`，再次通过 AgentTool 调用 `pandaai-experimenter`。可以使用批量脚本或逐个运行，但必须由守卫启动：

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 04_platform_execution --label platform_factor_run -- python <AGENT_ROOT>/scripts/run_candidates.py 02_factor_candidates/candidates.jsonl --candidates-sha256 <APPROVED_SHA256> --state-out 04_platform_execution/execution_state.json --start <YYYYMMDD> --end <YYYYMMDD> --cycle <1-10> --round-trip <APPROVED_COST> --group-number 10
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 04_platform_execution --label platform_collect_results -- python <AGENT_ROOT>/scripts/collect_results.py 04_platform_execution/execution_state.json --out-dir 04_platform_execution/result-cache --run-ids-out 04_platform_execution/run_ids.txt --report-out 04_platform_execution/candidates.report.csv
```

必须保留：

- `run_ids.txt`
- `result-cache/summary.json`
- 每个 run ID 对应的原始 JSON
- `candidates.report.csv`

`factor_result --download` 的 CSV 是逐股因子值，只用于因子诊断。它不能直接作为策略收益喂给过拟合或 tearsheet。

成员最后生成 `04_platform_execution/member_handoff.json`，必须引用 run ID 汇总、原始结果和候选报告。

```bash
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 04_platform_execution
```

任何候选失败都要保留；若 `summary.json` 中存在失败项，本阶段不封存。

## 6. 过拟合审计官

主 Agent 创建 `05_statistical_audit/task_packet.json`，只传递真实回测/平台证据路径、收益矩阵路径及哈希，再通过 AgentTool 调用 `overfit-auditor`。成员从真实回测底稿导出：

- `selected_returns.csv`：最终选中配置的逐期净收益，固定列名为 `date,return`，至少 30 期。单数 `return` 同时兼容过拟合审查与 tearsheet，禁止改成 `returns` 后让 tearsheet 误判为净值。
- `trials_matrix.csv`：所有实际尝试配置在相同日期上的收益矩阵，至少 10 列；不得只保留赢家。

必须核对日期对齐、成本口径和缺失值处理。运行：

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 05_statistical_audit --label overfit_report -- python <OVERFIT_SKILL>/scripts/overfit_report.py --returns 05_statistical_audit/selected_returns.csv --trials 05_statistical_audit/trials_matrix.csv --n-trials <HONEST_TOTAL_TRIALS> --out 05_statistical_audit/overfit_report.json
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 05_statistical_audit
```

守卫要求 PBO 非空。报告 `passed=false` 仍表示审计执行完成，但会在最终结论中触发 `RESEARCH_REJECTED`。

成员最后生成 `05_statistical_audit/member_handoff.json`。审计失败结论必须原样交接，主 Agent 不得要求改写。

## 7. 绩效报告师

主 Agent 创建 `06_tearsheet/task_packet.json`，只传递已审计收益文件路径与哈希，再通过 AgentTool 调用 `performance-reporter`。成员必须使用与过拟合审查相同的 `selected_returns.csv`，不得切换到更漂亮的另一条曲线。

```bash
python scripts/workflow_guard.py exec --run-dir <RUN_DIR> --stage 06_tearsheet --label tearsheet -- python <TEARSHEET_SKILL>/scripts/tearsheet.py --returns 05_statistical_audit/selected_returns.csv --ppy 252 --out 06_tearsheet/tearsheet.json --html 06_tearsheet/tearsheet.html
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 06_tearsheet
```

如果基准数据不可用，报告可以明确降级；如果策略收益本身不可用，不能生成报告。

成员最后生成 `06_tearsheet/member_handoff.json`。

## 8. 主研究员会诊

创建：

- `07_final_review/expert_handoffs.json`
- `07_final_review/final_report.md`

标准版和审计版的 `expert_handoffs.json` 必须恰好包含 `agents/team.json` 中五个成员；快速版只能包含 `source-replication-researcher`。每个条目同时包含 `member_id`、唯一绑定 `skill`、真实 `invocation_ids`、`status`、`conclusion`、`reservations` 和证据文件列表。主 Agent 只能从激活阶段的 `member_handoff.json` 聚合，不能代写成员意见。

统一结论规则：

- 所有执行完成且过拟合报告 `passed=true`：`PROMOTE_TO_OOS`，仅表示可以继续独立样本外研究。
- 所有执行完成但任一核心研究门失败：`RESEARCH_REJECTED`。
- 任何必需证据或外部条件缺失：`BLOCKED`。
- 快速版完成真实数据和紧凑回测：`FAST_VALIDATED`，只表示可以进入标准版或审计版继续研究。

```bash
python scripts/workflow_guard.py seal --run-dir <RUN_DIR> --stage 07_final_review
python scripts/workflow_guard.py finalize --run-dir <RUN_DIR>
```

只有最后一条命令返回 0 才允许对用户说“本次研究已完成”。

## 9. 无数据与失败复查

不能把异常、认证失败、参数错误或非交易日误写为“无数据”。只有真实接口或程序成功返回零行时，才能进入无数据协议：

1. 核对代码、日期格式、股票池和交易日。
2. 放宽日期窗口。
3. 移除非必填过滤条件。
4. 使用文档登记的备用参数重试一次。
5. 两次成功调用都为零行，才写“该口径无数据”，并附两次命令回执。

## 10. 宿主平台限制

本地守卫能阻止“缺文件却宣布完成”，但提示词本身不能强迫所有第三方宿主一定发起工具调用。部署到 WorkBuddy、豆包或其他宿主时，若平台提供 `tool_choice=required`、流程节点或服务端拦截，应同时开启，并把 `finalize` 作为对外回复前的服务端条件。
