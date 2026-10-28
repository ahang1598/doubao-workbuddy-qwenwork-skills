# 电子签参考

电子签（esign）CLI 用于显式调用电子签 MCP 服务。

## 服务与工具

- MCP 服务：`G-CONN-10397AF14A4A210565FE000H`
- 默认 MCP 工具：`list_my_sign_tasks`
- 查询签署流详情工具：`query_contract_esign_flow_detail`
- 创建签署流工具：`create_contract_esign_flow`

## 命令示例

```bash
# 查询我的签署任务
dws esign task list

# 按状态过滤
dws esign task list --status 1 --limit 20

# 透传额外参数
dws esign task list --args '{"bizId":"xxx"}'

# 查询签署流详情
dws esign flow detail --sign-flow-id "SFxxxx" --request-id "req-xxxx"

# 创建签署流（简单示例）
dws esign flow create --sign-flow-name "采购合同签署" --auto-start

# 创建签署流（完整示例）
dws esign flow create \
  --sign-flow-name "采购合同签署" \
  --auto-start \
  --corp-id "dingxxxx" \
  --signers '[{"signerType":"PERSONAL","signerInfo":{"psnName":"张三","psnMobile":"13800138000"}}]' \
  --sign-docs '[{"fileId":"FILE_ID","spaceId":123}]'

# 透传 JSON 创建签署流（--args 传扁平业务字段；OpenCreateSignFlowRequest 外层由 CLI 自动包装，勿自行包一层）
dws esign flow create --args '{"signFlowConfig":{"signFlowName":"采购合同"},"signers":[]}'
```
