# 异步任务查询

## 能力用途

查询异步任务状态与结果

## Agent 行为（必读）

豆包场景下 `--poll-complete` **不等于**「一定等到终态才退出」：单次调用最长轮询 **9 分钟**，到点后 CLI **正常退出**（`exit_code 0`），并返回**最后一次** Cloud 查询结果。

| 现象 | 是否正常 | Agent 应做什么 |
| --- | --- | --- |
| `exit_code 0` 且 `status` 为 `running` 或 `queued` | **正常**（9 分钟轮询窗口结束，任务仍在后端执行） | 告知用户仍在处理；用**同一 `task_id`** 再次执行 `query-task --poll-complete`，直到 `completed` / `failed` / `canceled` |
| `exit_code 0` 且 `status` 为 `completed` | 正常（成功终态） | 读取并返回业务结果 |
| `success: false` 或 `status` 为 `failed` / `canceled` | 正常（失败终态） | 按错误信息处理，不要重复轮询同一失败任务 |

**禁止**将「命令已成功退出 + 任务仍 running」描述为状态异常、状态同步故障或显示 bug；**禁止**为此排查 Env Platform 或重复提交任务。长耗时任务（如 8K / professional 画质增强）通常需要**多轮** `query-task`。

## 参数填写规则

- task_id 必须来自真实异步任务受理结果；可选轮询参数仅在用户明确指定，或可从用户意图准确确定时填写，不得伪造。
- 豆包场景下单次 `query-task` 轮询总时长不超过 **9 分钟**。`poll_interval_seconds × max_poll_attempts` 不得超过该上限；超过时 CLI 会按 9 分钟自动退出，并返回最后一次查询结果（`status` 可能仍为 `running` 或 `queued`）。若 9 分钟内未达终态，应再次发起 `query-task`。
- 暂不支持通过 CLI 调整该 9 分钟轮询上限；不要向用户建议或伪造相关 flag。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli shared query-task`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- 布尔参数（`--poll-complete`）只能写成 `--poll-complete=true` 或 `--poll-complete=false`，也可用裸 `--poll-complete`（等价 true）；禁止空格传值 `--poll-complete true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 使用 `--poll-complete` 或 `--max-poll-attempts` 时，单次调用最长轮询 9 分钟；超时后 CLI 正常退出并返回最后一次查询结果（`status` 可能仍为 `running`/`queued`），**不是错误**；用同一 `task_id` 再次查询即可。

### 调用示例

单次查询（不轮询）：

```bash
mediakit-cli shared query-task \
  --task-id <task_id>
```

持续轮询（单次最长 9 分钟；未达终态时重复执行，**task_id 不变**）：

```bash
mediakit-cli shared query-task \
  --task-id <task_id> \
  --poll-complete
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `max_poll_attempts` | `--max-poll-attempts` | integer | 否 | 0 | 最小值: 0 | 最多轮询次数；0 表示只查询一次。与 `poll_interval_seconds` 的乘积不得超过豆包场景 9 分钟轮询上限。 |
| `poll_complete` | `--poll-complete` | boolean | 否 | false | - | 持续轮询直到终态或达到豆包 9 分钟上限。上限到达时 CLI 正常退出（非错误），返回最后一次查询结果；任务可能仍在 running，需再次 query-task。 |
| `poll_interval_seconds` | `--poll-interval-seconds` | number | 否 | 10 | 大于: 0 | 轮询间隔，单位为秒；必须大于 0，仅在持续轮询时使用。豆包场景下单次轮询总时长不超过 9 分钟。 |
| `task_id` | `--task-id` | string | 是 | - | - | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `error` | any | 否 | Cloud | 失败终态的原始错误内容；仅在实际失败且后端返回时出现。 |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端实际返回非空值时出现。 |
| `status` | string | 否 | Cloud | 任务状态；completed 为成功终态，failed、canceled 或 cancelled 为失败终态。 |
| `success` | boolean | 否 | Cloud | 失败终态返回 false；其他状态仅在后端实际返回时出现。 |
| `task_id` | string | 否 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态和异步提交不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli shared query-task --help
mediakit-cli shared query-task --schema
```
