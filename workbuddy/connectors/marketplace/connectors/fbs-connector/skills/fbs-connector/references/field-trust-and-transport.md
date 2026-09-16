# 字段、信任、失败与传输边界

## 运行时真源

每次会话先使用宿主实际暴露的 `tools/list`。发行时保存的 schema、本文档和服务描述只用于差分与安全前置，不能增加当前工具不存在的参数。

字段仅在三项同时成立时发送：调用方确实掌握；来源允许用于该目的；当前 input schema 接受。`additionalProperties=false` 时禁止试探额外字段。

## 动态字段

现有字段包括产品/包/入口、渠道、意图、交互、场景、binding 和幂等材料。`attributionContext`、`installInstanceId`、账户主体、持久化状态统一投影等均为待服务与宿主实现的候选，不得提前发送或描述为已支持。

未知、冲突和不适用必须分开：

- `unknown`：字段适用但没有可靠值。
- `not_applicable`：本动作不属于该业务域。
- `conflict`：声明、登记或服务规范化结果不一致。

客户端声明只保持 `claimed`；工具可见为 `observed`；登记表匹配为 `registered`；只有对应回执才可称 `verified`。

## 凭证来源

- `accessCode`：用户为当前激活步骤明确提供。
- `sessionRef` / `sessionToken`：服务端在同一授权业务链返回，或当前 schema 接受且来源可验证。
- 乐包凭证：同一 issuer 产生的完整 voucher、nonce、payload 和 signature。
- MCP session、SSE event ID、JSON-RPC request ID、trace、匿名 hash 和 server binding 均不是账户认证凭证。

任何凭证只进入被授权工具参数，不进入普通回复、调试输出、归因事件或持久研究报告。

## 失败和重试

| 动作 | 策略 |
| --- | --- |
| discovery / `tools/list` | 仅在宿主实际支持时做有界只读重试；保留次数和总预算 |
| `skill_whoami` / 场景读取 | 未证明匿名 binding 可安全复用前不自动重放；重新读取时保留同一上下文 |
| `skill_consume` | 仅同一 binding、同一真实成果、同一服务幂等键可重试或回读 |
| activate / finish / logout | 丢响应保持未决；不自动重放，先确认状态和用户意图 |
| claim / redeem | 不自动重试；先按同一 binding 查询状态 |

HTTP 200、SSE 建连或 JSON-RPC 成功包络均不能替代工具和业务成功字段。`timeout=60000` 是连接配置，不是所有工具或长流生命周期的统一预算。

## 版本轴

- connector package：`2026.9.10`
- legacy connector contract header：`1.2.9`
- expert package：各专家自己的当前版本
- host、MCP protocol 和 service release：由各自运行时事实产生

这些字段不得互相推导或填充。
