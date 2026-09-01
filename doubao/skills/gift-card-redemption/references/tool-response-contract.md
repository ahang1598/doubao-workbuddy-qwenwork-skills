# 工具返回契约

在解释 `gift_card_redemption` 的 PREPARE 或 REDEEM 返回前完整读取本文件。

## 判定优先级

始终先读取顶层 `isError`，再读取与当前 `action` 对应的数据。`structuredContent` 是业务事实来源；`content[].text`、`suggestedMessage` 和错误文案只用于面向用户表达，不能覆盖结构化判定。

| 阶段 | 判定条件 | 含义 | 后续动作 |
|---|---|---|---|
| `PREPARE` | `isError=false`、`giftCardData.valid=true` | 业务成功，兑换码有效 | 校验字段、生成 `packageLabel` 并请求确认 |
| `PREPARE` | `isError=false`、`giftCardData.valid=false` | 业务结果明确，但不可兑换 | 展示 `unavailableReason`，不得调用 REDEEM |
| `PREPARE` | `isError=true`、`giftCardData=null` | 工具执行异常，兑换码状态未知 | 按错误字段说明，不得宣称有效或无效 |
| `REDEEM` | `isError=false`、`redemptionData.status="SUCCEEDED"` | 业务成功，已兑换 | 使用成功模板，本次结束 |
| `REDEEM` | `isError=false`、`redemptionData.status` 非空且不为 `SUCCEEDED` | 下游给出明确业务结果，但未兑换成功 | 按状态和建议文案说明，本次结束 |
| `REDEEM` | `isError=true`、`redemptionData=null` | 工具执行异常，兑换结果未知 | 禁止重复提交，本次结束 |

## 通用不变量

- 业务成功和业务未成功的 `errorCode` 均为 `0`，且 `isError=false`。`valid=false`、`ALREADY_REDEEMED` 或其他非成功业务状态不是工具异常。
- 工具异常由 `isError=true` 标识，并通过 `errorCode`、`errorType`、`errorMsg`、`retryable`、`retryAfterSec` 和 `suggestedFix` 描述；对应业务数据应为 `null`。
- 工具入参 `action` 只接受字符串枚举 `"PREPARE"` 和 `"REDEEM"`。`code` 与 `image_url` 必须二选一；REDEEM 还必须携带同次可兑换 PREPARE 返回的 `redeem_token`。
- PREPARE 工具异常表示兑换码状态未知。REDEEM 工具异常默认表示兑换结果未知；只有契约明确保证在副作用前返回的 `40000`、`51001`、`51002`、`51004` 可以按对应安全恢复路径处理。不得根据文案、历史结果或用户预期猜测业务状态。
- 若 `isError=false` 但当前 action 对应的数据为 `null`，或 `isError=true` 但仍携带业务数据，视为结构矛盾并采取安全停止动作。

## 已知工具错误矩阵

只有 `errorCode` 和 `errorType` 与下表严格匹配时，才执行对应的精准分流。code/type 不匹配、未知错误码或未知错误类型均按 `INTERNAL_ERROR` 的安全策略处理，不猜测错误含义。

| `errorCode` | `errorType` | 主要阶段 | Skill 行为 |
|---:|---|---|---|
| `40000` | `INVALID_ARGUMENT` | PREPARE 或 REDEEM | 不重放相同调用。PREPARE 时重新收集唯一输入；REDEEM 时视为 Skill 编排/参数构造异常，使待确认状态失效，不要求用户理解或提供 token |
| `51001` | `RUNTIME_CONTEXT_MISSING` | PREPARE 或 REDEEM | 不自动重试；使原上下文失效，提示恢复登录或运行时上下文后从 PREPARE 重新开始 |
| `51002` | `QR_CODE_RESOLUTION_FAILED` | 图片输入 | 不使用同一图片重试；使原上下文失效，请用户重新上传清晰二维码或改用文本兑换码 |
| `52001` | `GIFT_CARD_DETAIL_QUERY_FAILED` | PREPARE | 不判断兑换码有效性；仅当 `retryable=true` 时按 `retryAfterSec` 使用相同输入重试一次 |
| `52002` | `PAID_USER_QUERY_FAILED` | PREPARE | 不进入确认；仅当 `retryable=true` 时按 `retryAfterSec` 使用相同输入重试一次 |
| `51003` | `GIFT_CARD_REDEMPTION_FAILED` | REDEEM | 不适用；按下述 REDEEM 工具异常规则处理 |
| `51004` | `REDEEM_TOKEN_INVALID` | REDEEM | 明确未进入兑换下游；丢弃旧 token，以当前原始输入重新 PREPARE、重新展示确认信息并再次等待明确确认 |
| `52999` | `INTERNAL_ERROR` | PREPARE 或 REDEEM | PREPARE 仅在 `retryable=true` 时按建议等待后重试一次，否则停止 |

补充约束：

- `40000`、`51001`、`51002` 的同一请求自动重试均应为 `retryable=false`；恢复上下文或更换图片后属于新的 PREPARE 流程，不是原请求自动重试。
- `52001`、`52002` 返回 `retryable=true` 时必须提供正数 `retryAfterSec` 和具体 `suggestedFix`；否则不自动重试。
- `52002` 即使已经取得礼品卡详情，也不能确定 `isPaidUser`，不得生成免费用户或付费用户确认文案，且不得调用 REDEEM。
- 任一工具异常都应令当前 action 对应的业务数据为 `null`。不要利用不完整的残留业务字段继续流程。
- `51004` 是 REDEEM 工具异常中的特例：工具在兑换副作用前拒绝 token，不能按结果未知处理。不得使用同一 token 重试 REDEEM；重新 PREPARE 后也必须再次获得用户明确确认。
- REDEEM 缺少 token 返回 `40000`，通常是 Skill 编排或参数构造错误。不要要求用户提供 token、检查 token 或为内部错误负责；不得补空值后直接重试 REDEEM。
- `51003` 表示兑换结果未知，无论 `retryable` 如何都不得自动重试。其他无法证明发生在兑换副作用前的 REDEEM 工具异常也按结果未知策略停止。

## PREPARE 字段与套餐格式

PREPARE 可兑换结果必须包含：

- `giftCardData.valid=true`
- 非空 `giftCardData.skuName`
- 有效 `giftCardData.periodType`
- 有效 `giftCardData.periodNum`
- 布尔值 `giftCardData.isPaidUser`
- 非空 `giftCardData.redeem_token`

生成套餐展示文案 `packageLabel`，竖线两侧不加空格：

- `periodType="DAY"` 且 `periodNum` 为正整数：`<skuName>|<periodNum>天`。
- `periodType="MONTH"` 或兼容旧返回 `periodType="Month"`，且 `periodNum=1`：按等价周期 30 天展示为 `<skuName>|30天`，不得展示成“1个月”。
- 示例：`skuName="豆包个人订阅标准套餐"`、`periodType="DAY"`、`periodNum=30`，或相同 `skuName`、`periodType="Month"`、`periodNum=1`，均生成 `豆包个人订阅标准套餐|30天`。

不根据 `content[].text` 猜测套餐名称或周期。返回值不符合任一已支持组合时，不猜测单位或换算关系，不进入确认状态。

## PREPARE 结果处理

- `valid=true` 且关键字段和 `redeem_token` 完整：原样保存 token，并保存原始输入、字段类型、业务字段和 `packageLabel`，进入等待确认。不得解析、修改、解释或展示 token。
- `valid=false`：使用 `unavailableReason` 说明原因；此时 `redeem_token` 应为 `null`，不得进入确认或调用 REDEEM。这是业务结果，不称为工具失败。
- `isError=true`：先按“已知工具错误矩阵”校验 code/type 并选择行为。只有矩阵明确允许且 `retryable=true` 时，才可按 `retryAfterSec` 等待后使用完全相同的原始输入自动重试 PREPARE 至多一次；不得立即或无限重试。无法等待时告知建议时间并停止。
- 关键字段缺失或结构矛盾：说明暂时无法安全确认，不得调用 REDEEM。

## REDEEM 结果处理

- 只有 `isError=false` 且 `redemptionData.status="SUCCEEDED"` 表示兑换成功。
- `isError=false` 且状态为 `ALREADY_REDEEMED` 或其他非 `SUCCEEDED` 值，是明确的业务未成功结果，不得称为工具失败。
- 明确的处理中状态属于业务结果；不得通过再次调用 REDEEM 轮询。
- `51004 / REDEEM_TOKEN_INVALID`：兑换尚未执行。丢弃旧 token，使用当前原始输入重新 PREPARE，重新展示完整确认信息，并等待用户再次明确确认；不使用同一 token 重试 REDEEM。
- `40000 / INVALID_ARGUMENT`：视为 Skill 编排异常，不把 token 细节或修复责任交给用户，不直接重试 REDEEM。使待确认状态失效；如要继续，只能从 PREPARE 和确认门禁重新开始。
- `51003 / GIFT_CARD_REDEMPTION_FAILED`：兑换结果未知，不声称成功或失败，明确不要重复提交，并建议稍后查看会员状态。
- 其他 `isError=true` 或无法判断是否已产生副作用的异常：按兑换结果未知处理，即使 `retryable=true` 也不得自动重试 REDEEM。
- 结构矛盾或缺少 `redemptionData.status`：按兑换结果未知处理，提示不要重复提交，并建议稍后查看会员状态或按工具建议处理。
