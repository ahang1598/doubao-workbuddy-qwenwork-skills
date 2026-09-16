# Action envelope、交付与消费合同

## 接收

`skill_whoami` 的返回只有在当前工具回执明确成功时才可驱动下一步。下一工具、参数、binding、幂等材料和可选状态回读必须来自同一返回 envelope。

## 原样转发

当服务明确返回 `actionEnvelope` 时：

1. 当前 `tools/list` 必须包含 envelope 指定工具。
2. `toolArguments` 必须通过该工具当前 input schema。
3. 参数整体原样传递，不增删、不改名、不改大小写、不把外部候选字段混入。
4. envelope 缺字段、工具不存在、schema 不匹配或 binding 冲突时停止；保留可读的 unknown/conflict，不选择“最像”的专家继续写。
5. envelope 指向 consume、激活、完结、登出、领取或兑换等写操作时，仍须满足对应 mainline/session/lebao 的用户意图、真实交付、凭证和未决写规则；服务建议不单独构成写授权。

`actionEnvelope` 是服务返回结构的通称。本 Skill 不声明固定新增字段；实际名称与字段始终服从当前 schema。

## 真实交付

场景内容返回不是首值完成。先在聊天中形成用户可使用的成果；连接器失败时仍应完成不依赖连接器的本地首值。

只有成果已经真实交付，且 envelope 给出同一 binding 的消费参数时，才调用 `skill_consume`。事件类型限当前 schema 接受且与成果相符的 `first_value_completed` 或 `continued_use_completed`。

## 未决消费

- 明确业务拒绝：报告失败，不写完成。
- 连接超时/丢响应：标记 `consume_outcome_unknown`，保留原幂等键；不得生成新键重放。
- 当前能力提供状态回读：只按服务给定参数回读，再决定是否用同一键继续。
- 无状态回读：停止自动动作，请用户看到明确的未确认状态。
