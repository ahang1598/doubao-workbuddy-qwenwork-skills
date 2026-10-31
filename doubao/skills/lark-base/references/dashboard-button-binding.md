# 仪表盘按钮工作流绑定 Reference

## 对象与入口

用同一 Base 下的 base_token、dashboard_id、block_id 定位 Dashboard 按钮；目标组件必须是 type=button，容器 ID 不能代替组件 ID。表格按钮字段用 +button-rule-bind/get/unbind（参数 table_id、field_id），不适用于仪表盘组件。

## 按钮组件配置

button 组件不需要 table_name、series、count_all，文案用 label。创建用 `--type button --data-config '{"label":"运行工作流"}'`，无需 --no-validate；更新文案只传含 label 的 --data-config，不补数据源或指标。
CLI 不给按钮字段加必填或非空限制，由服务端校验；data_config 仍须是合法 JSON 对象，number_format 仍只限 statistics。

## 绑定接口与请求约定

目标环境须已部署下列 GET/PUT 路由，且当前身份可调用。优先用 lark-cli base --help 里已发布的类型化命令；元数据未收录时用下面的 API。不猜 +dashboard-button-* 命令，不给字段按钮命令加未声明参数。
GET 无请求体、无 query 参数。PUT 直接提交 JSON 对象，不包装成 Payload 字符串，不提交网关注入的用户、租户、应用或 Meta 信息。

```bash
button_rule_path='/open-apis/base/v3/bases/<base_token>/dashboards/<dashboard_id>/blocks/<block_id>/button_rule'
lark-cli api GET "$button_rule_path"
lark-cli api PUT "$button_rule_path" --data '{"workflow_id":"wkf_xxx"}'
lark-cli api PUT "$button_rule_path" --data '{"workflow_id":""}'
```

## 查询绑定

先核对 ok=true 和 data 里的两个目标 ID：

```json
{"dashboard_id":"<dashboard_id>","block_id":"<block_id>","bound":true,"target":{"type":"workflow","id":"wkf_xxx"}}
```

| 返回值 | 含义 |
|---|---|
| bound=false，target=null | 未绑定 |
| bound=true，target.type=workflow，target.id 为公开 wkf ID | 已绑定该工作流 |
| bound=true，target.type=unknown，无 id | 旧类型绑定，此接口无法解析目标类型 |

失败、缺字段或其他组合都不能当作未绑定。V2 工作流缺合法公开 ID 时服务端报错，不会降级成 bound=false。
GET 查的是实际 ButtonRule 关系。data_config.workflow_id 是快照值，可能是内部 ID；它不能代替 target.id，内部数字 ID 也不能拼成公开 ID。

## 绑定或更换工作流

workflow_id 必须是当前 Base 中 +workflow-list/get/create 返回的公开 ID：以 wkf 开头、长度大于 3、不含空白。已有绑定时 PUT 会更换关系。只提交 workflow_id，不附加 label、data_config；样式和文本走组件配置。
也可用 `--data @button-rule.json` 或 `--data -` 从文件或 stdin 读同一对象。成功返回 bound=true 和服务端确认的 target。

## 解绑

解绑仍用 PUT，必须保留 workflow_id 键且值为精确的空字符串。省略字段、空请求体、null、数字、空白字符串都会被拒绝。成功返回 bound=false、target=null；重复解绑仍保持未绑定。解绑不删除按钮或工作流。

## 仪表盘按钮的触发器

为仪表盘按钮创建工作流时，触发器用 ButtonTrigger，data 为 `{"button_type":"buttonElement"}`；完整 steps 见 [Workflow schema](workflow-schema.md)。buttonElement 不填 table_name，只提供 time、user、buttonName 等基础属性，没有表格按钮的当前记录字段、recordId、recordLink。
组件创建、绑定关系、启停状态分别处理：绑定不自动启用工作流，解绑也不代表停用。

## 技术限制与恢复入口

--dry-run 只核对方法、路径和请求体，不调用服务端，不能证明路由已部署、ID 有效、权限足够或关系已改变。类型化命令依赖上游元数据发布，其响应应保留 bound 和可为 null 的 target，不平铺成 workflow_id。

## 按钮绑定失败恢复

保留已有按钮和工作流 ID，按 CLI 返回的错误、hint、log ID 排查。写入失败或结果不确定时，先 GET 读当前关系再决定是否重试；不重建按钮或工作流，不宣称解绑成功。
权限错误按响应查当前用户的 scope 或资源权限；凭证或 scope 缺失由 agent 平台补齐，不能照抄表格按钮的 base:field:* 权限。
