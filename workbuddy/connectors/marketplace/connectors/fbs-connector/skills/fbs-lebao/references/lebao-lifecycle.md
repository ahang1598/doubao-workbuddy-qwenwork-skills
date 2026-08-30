# 乐包参数与副作用合同

参数 schema 以当前 `tools/list` 为准；本文件只固定安全所需的最小合同。

## `lebao_status`（只读）

- 至少提供 `voucherId`、`serverBindingId`、`anonymousUserCodeHash` 之一。
- 三者全缺时没有查询对象，应停止并说明需要先完成身份或绑定步骤。

## `lebao_claim`（奖励写入）

- 仅在服务端已明确推进到领取阶段时使用。
- 必须有可验证的 `sessionRef` / `sessionToken` 或当前 schema 接受的等效会话身份。
- 失败不得当作已领取，也不得无条件重试。

## `lebao_redeem`（凭证兑换写入）

当前必填字段共 9 个：

- `voucherId`
- `sourceSkillCode`
- `sourceEventCode`
- `rewardRuleCode`
- `anonymousUserCodeHash`
- `issuer`
- `nonce`
- `payloadEncoded`
- `signature`

这些字段必须来自同一份可信凭证；缺失、跨凭证拼接或自行生成时停止兑换。

## `lebao_drop`

- 服务端管理的确定性掉落工具。
- 本包已通过 `disabledTools` 禁用，WorkBuddy 工具面不得向模型暴露它。
- 只有新的连接器版本完成安全复核并重新审核后，才可调整禁用状态。
