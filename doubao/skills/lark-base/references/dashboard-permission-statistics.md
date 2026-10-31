# 仪表盘访问者权限统计协议
## 对象与入口
`is_adv_perm_enable`（跟随访问者权限统计）、`is_advanced`（Base 高级权限总开关）、`dashboard_rule_map`（角色仪表盘权限）独立，互不替代。
## 接口条件
路径中的 `dashboard_id` 是 Base 内仪表盘的 block ID，不是内部组件 ID。这是新接口，目标环境必须已部署对应 HTTP 路由并授予调用身份所需权限。
优先用已发布的类型化命令（以 `--help` 确认）；未收录时按下列路径用 `lark-cli api` 联调。不要猜测不存在的 `+dashboard-advperm-*` 命令；dry-run 成功不证明接口部署或权限生效。
## 读取开关
```bash
lark-cli api GET '/open-apis/base/v3/bases/<base_token>/dashboards/<dashboard_id>/adv_perm'
```
成功返回 `ok: true`，值为 `data.is_adv_perm_enable`；仅 false 明确关闭。失败、缺字段或类型错误不得视为 false。
## 设置开关
```bash
lark-cli api PATCH '/open-apis/base/v3/bases/<base_token>/dashboards/<dashboard_id>/adv_perm' --data '{"is_adv_perm_enable":true}'
lark-cli api PATCH '/open-apis/base/v3/bases/<base_token>/dashboards/<dashboard_id>/adv_perm' --data '{"is_adv_perm_enable":false}'
```
请求字段必填：开启用 JSON 布尔 `true`，关闭显式传 `false`；不能省略，也不能用字符串 `"false"` 或 `null`。`--dry-run` 只检查请求构造。
## 写入返回与失败含义
PATCH 成功返回 `ok: true, data: {}`；不返回当前值，须 GET 验证，不得把提交值当返回状态。
## 统计权限开关失败恢复
- Base 高级权限未开：用 `+base-get` 确认；只有用户已授权修改总开关才执行 `+advperm-enable`。
- 身份无权操作：按错误响应检查 scope、资源权限；凭证或 scope 缺失由 agent 平台补齐，保留当前用户身份。
- 租户权益不足：说明服务端权益限制，不反复重试。
- 资源不存在：核对所属 Base、仪表盘 block ID，不用内部组件 ID。
按 CLI 失败输出的业务错误码、提示行动。GET 失败不表示关闭；PATCH 失败不表示状态已改变。
