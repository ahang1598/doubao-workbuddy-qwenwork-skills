# 02 · monitor — 通知明细查询 & 催办

> 通知发送状态查询、未填写名单查询、再次提醒。**运行时高频操作**，催办场景的主入口。

---

## 速查表

| 想做什么 | 命令 |
| :--- | :--- |
| 查"某店通知发出去了吗" | [`monitor query --store-name <名> --task-id <ID>`](#查询通知发送状态) |
| 查"还有哪些店没填表" | [`dispatch notifications --filter unfilled --task-id <ID>`](#查询未填写名单催办场景)（或兼容别名 `dispatch list-pending`） |
| 查"某段时间内的通知" | [`dispatch notifications --notified-from ... --notified-to ...`](#dispatch-notifications) |
| 查"通知后超过 N 分钟还没填的店" | [`dispatch notifications --filter unfilled --stayed-over-minutes N`](#dispatch-notifications) |
| 重新通知未填写的人（带半小时冷却） | 跳到 [01-dispatch.md#二次催办--only-pending](./01-dispatch.md#二次催办--only-pending) |

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py monitor --help` / `uv run python scripts/cli.py dispatch notifications --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点。

### monitor query

- **查询对象**：「动态通知表」（`{任务表名}-通知`），**不是固定表**；`--task-id` 决定用哪张通知表
- **业务边界**：本命令仅查通知发送状态；查门店**提交状态**走 `dispatch instances`（见 [01-dispatch.md#查询任务实例记录](./01-dispatch.md#查询任务实例记录)）

### dispatch notifications（催办场景推荐）

- **`--filter` 4 种取值语义**（**Agent 决策核心**）：
  - `sent` → 已通知（不论填没填）
  - `filled` → 已通知**且**已填表
  - `unfilled` → 已通知**但**未填表（**催办场景核心**）
  - `failed` → 通知失败（用于排查送达问题）
- **业务场景映射**：
  - 「还有谁没填」→ `--filter unfilled`
  - 「通知后超过 N 分钟还没填的店」→ `--filter unfilled --stayed-over-minutes N`
  - 「某段时间内的通知」→ `--notified-from / --notified-to "YYYY-MM-DD HH:mm"`
- **输出**：`{task_id, count, members: [{store_id, store_name, manager_name, notify_status, notified_at, send_count, ...}, ...]}`
- **判定规则**：`unfilled` = 通知表中 `notify_status = sent` 的门店 ∧ 动态任务表中无对应 `store_id` 的已提交记录

### dispatch list-pending（兼容别名）

- 等价于 `dispatch notifications --filter unfilled`，输出格式相同
- 老脚本用，新文档优先用 `dispatch notifications --filter unfilled`

---

## 查询通知发送状态

**触发信号**：用户问"某店通知发出去了吗 / 还有多少通知失败的"。

| 想查什么 | 命令骨架 | 关键决策点 |
| :--- | :--- | :--- |
| 某店通知有没有发 | `monitor query --store-name <名> --task-id <ID>` | — |
| 失败的通知 | `monitor query --notify-status failed --task-id <ID>` | `--notify-status` 取值见 -h |

完整参数：`uv run python scripts/cli.py monitor query --help`。

> 查询门店**提交状态**需要直接查动态任务表（记录存在即视为已提交），
> 用 `dispatch instances`，详见 [01-dispatch.md#查询任务实例记录](./01-dispatch.md#查询任务实例记录)。

---

## 查询未填写名单（催办场景）

**触发信号**：用户问"还有谁没填" / "查一下未填写名单"。

| 想查什么 | 命令骨架 | 关键决策点 |
| :--- | :--- | :--- |
| 谁还没填（推荐写法，语义最明确） | `dispatch notifications --task-id <ID> --filter unfilled` | `--filter` 4 取值见 -h |
| 同上（兼容别名） | `dispatch list-pending --task-id <ID>` | 等价于上一条 |
| 通知后超过 N 分钟仍未填的店 | `dispatch notifications --task-id <ID> --filter unfilled --stayed-over-minutes 30` | `N` 表示滞留分钟数；用于催办决策 |

完整参数 / 时间窗 / 输出字段：`uv run python scripts/cli.py dispatch notifications --help`。

判定规则：「通知表中 `notify_status = sent` 的门店」&「动态任务表中无对应 `store_id` 的已提交记录」。

输出字段：`store_id` / `store_name` / `manager_name` / `notified_at` / `send_count` / `stayed_minutes`。

---

## 再次提醒

**触发信号**：用户说"再催一遍还没提交的店"。

> CLI **不再提供独立的 `remind` 子命令**。再次提醒由以下两种方式完成：

### 方式 1：手动一键催办（推荐）

直接走 `dispatch notify --only-pending`，CLI 自动算出"已通知未填写"的成员并复用同一份模板，
带半小时冷却保护。详见 [01-dispatch.md#二次催办--only-pending](./01-dispatch.md#二次催办--only-pending)。

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id TASK_xxx --only-pending
```

> 周期触发：`dispatch notify --only-pending` 是一次性调用；
> 严禁 Skill 内自写循环 / daemon 做定时催办，详见 `../shared/hard-constraints.md#H6`。

---

## 相关参考

- 二次催办（冷却保护 + `--only-pending` 默认行为）：[01-dispatch.md#二次催办--only-pending](./01-dispatch.md#二次催办--only-pending)
- 提醒消息复用派发模板：`../shared/placeholders.md#提醒消息自动复用派发模板`
- 动态通知表字段：`../shared/data-model.md#动态通知表`
