# 子 Agent 任务包与证据交接合约

本合约用于真正的上下文隔离。主 Agent 不把完整会话或其他 Skill 说明塞给成员；每次只通过 AgentTool 传递一个结构化任务包。成员只加载自己的声明与 Skill，完成后返回结构化交接文件。

## 调用原则

1. 主 Agent 创建阶段目录下的 `task_packet.json`，再通过 AgentTool 调用清单中指定的成员 Agent。
2. 任务包只包含本阶段目标、已封存输入的路径与 SHA-256、输出要求和必要限制。
3. 子 Agent 不读取主 Agent 的完整对话，不加载其他成员 Skill，不创建或调用其他 Agent。
4. 子 Agent 把业务产物写入阶段目录，并生成 `member_handoff.json`。
5. 主 Agent只读取交接摘要和证据路径；守卫校验任务包、交接身份、文件哈希和阶段绑定后才允许封存。
6. `invocation_id` 必须来自宿主的真实 AgentTool 调用回执。宿主无法提供调用 ID 时，填入明确的本地测试 ID，但只能标记为模拟/本地验证，不能宣称已在 WorkBuddy 完成多 Agent 调用。

## `task_packet.json`

```json
{
  "schema_version": 1,
  "member_id": "factor-engineer",
  "stage": "02_factor_candidates",
  "objective": "把已封存的复现公式转为至少四个可执行候选",
  "input_evidence": [
    {
      "path": "01_source_replication/factor_formula.md",
      "sha256": "64位小写SHA-256"
    }
  ],
  "required_outputs": [
    "02_factor_candidates/candidates.jsonl",
    "02_factor_candidates/candidate_review.md"
  ],
  "constraints": [
    "不得用模型记忆补写数据",
    "不得修改已封存输入"
  ]
}
```

要求：

- `member_id` 和 `stage` 必须与 `agents/team.json` 的路由一致。
- `objective`、`required_outputs` 和 `constraints` 不能为空。
- 每个输入文件必须存在，且当前 SHA-256 与任务包完全一致。
- 任务包只能引用本次 `<RUN_DIR>` 内的相对路径。

## `member_handoff.json`

```json
{
  "schema_version": 1,
  "member_id": "factor-engineer",
  "skill": "skill-factor-mining-pandaai",
  "stage": "02_factor_candidates",
  "invocation_id": "宿主返回的真实AgentTool调用ID",
  "context_isolated": true,
  "status": "completed",
  "conclusion": "形成4个有实质差异且通过字段与未来函数检查的候选",
  "reservations": "尚未经过收费平台实跑",
  "evidence": [
    {
      "path": "02_factor_candidates/candidates.jsonl",
      "sha256": "64位小写SHA-256"
    },
    {
      "path": "02_factor_candidates/candidate_review.md",
      "sha256": "64位小写SHA-256"
    }
  ]
}
```

要求：

- 可封存阶段的 `status` 只能是 `completed`。
- `context_isolated` 必须为 `true`。
- 成员、Skill 和阶段必须与团队清单一致，不能由主 Agent 临时换角色。
- `conclusion` 和 `reservations` 必须明确；失败或阻断也要留下交接，但不得封存为完成。
- `evidence` 必须至少覆盖该阶段所有必需业务产物，路径和 SHA-256 必须与磁盘文件一致。

## 主 Agent 的最小上下文

主 Agent 只保留以下信息：

- 当前研究参数与审批状态；
- 已封存阶段回执；
- 每位成员的 `conclusion`、`reservations`、证据路径和哈希；
- 阶段状态与下一位成员的任务包。

原始研报、完整候选推导、平台原始 JSON、统计明细和 HTML 不复制进主 Agent 对话；需要复核时按证据路径读取。
