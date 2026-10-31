# 仪表盘全局筛选 Reference

## 对象与入口

global_filters 保存在 Dashboard 容器上。路径里的 dashboard_id 是容器 ID，不是图表组件的 block_id。全局筛选、组件 data_config.filter、Table View 筛选分别配置。

## 接口条件与请求约定

目标环境须已部署路由，且当前身份可调用。优先用 CLI 已发布的类型化命令，用 lark-cli base --help 和命令 --help 确认入口；元数据未收录时用 lark-cli api。不猜 +dashboard-* 命令，不给 +dashboard-update 加未声明参数。
GET 和 PATCH 共用 /global_filter 路径，JSON 字段名是复数 global_filters。请求体直接提交 JSON 对象，不包装成 Payload 字符串，不带网关注入的用户、租户、应用信息。

## 读取配置

```bash
lark-cli api GET '/open-apis/base/v3/bases/<base_token>/dashboards/<dashboard_id>/global_filter'
```

GET 不需要请求体或 query 参数。成功时 data 为 `{"dashboard_id":"<dashboard_id>","global_filters":[]}`。
只有请求成功、dashboard_id 与目标一致、global_filters 明确是数组时，才能判断当前配置。[] 表示没有全局筛选；失败、缺字段或 null 都不能当作空配置。GET 报无法完整导出时，按 [全局筛选失败恢复](#全局筛选失败恢复) 处理。

## 设置配置

顶层只能有 global_filters，值为非 null 数组；空 body、{}、null、非数组以及额外的 name、theme 等顶层字段都会被拒绝。api 的 dry-run 只验证请求构造，不代替服务端校验。
PATCH 用数组整体替换当前配置，不按表名合并；不能把 View 的 tuple 筛选转成本接口的条件。表名、字段名、字段类型须与目标 Base 一致。

```json
{"global_filters":[{"table_name":"订单表","filter":{"conjunction":"and","conditions":[{"field_name":"金额","operator":"isGreater","value":1000}]}}]}
```

把上面的请求对象（不是 CLI 的 ok/data 输出）存为 filters.json 后执行；也可用 `--data '<JSON 对象>'` 或 `--data -` 从 stdin 读取：

```bash
lark-cli api PATCH '/open-apis/base/v3/bases/<base_token>/dashboards/<dashboard_id>/global_filter' --data @filters.json
```

## 清空配置

明确要清空时提交空数组 `--data '{"global_filters":[]}'`；不用 null、省略字段或空请求体表示清空。

## 返回结构与归一化

GET 和 PATCH 都用标准 ok/data 返回 dashboard_id 和 global_filters。PATCH 返回服务端处理后的配置，值可能被归一化（如 1000 返回为 ["1000"]）。展示或继续编辑时以返回配置为准，不把提交值当结果。

## 全局筛选失败恢复

GET 报 `Global filters cannot be represented completely with the current schema and access permissions` 时，配置无法完整导出，也无法安全备份。不要用 PATCH 或清空来试探修复；先检查字段访问权限，或在仪表盘里调整配置。联调写入用同一 Base 的临时仪表盘，验证后清理。
其他失败按 CLI 返回的错误、提示和 log ID 处理。权限失败时检查当前用户的 scope 或资源权限，凭证或 scope 缺失由 agent 平台补齐；路径未部署和资源不存在要分别核对。失败响应不能证明已设置或已清空。
