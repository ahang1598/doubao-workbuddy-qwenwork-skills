# OA 流程效率与表单统计（内网增量）

仅企业钉钉管理员可用；普通审批查询和处理先读 [oa.md](oa.md)。下面保留 MR 16 的接口说明；历史服务端实测描述是作者证据，不等于本次已复测线上数据。执行时以当前 leaf Help/Schema 和真实返回为准，统一使用 `--format json`。

### 查询流程效率指标目录

> **IMPORTANT：** 仅企业钉钉管理员可调用，非管理员服务端返回「权限不足」。这是 `query-efficiency-metric` 的前置命令：先用它拿到合法的 `metricId` 与该指标支持的 `timeCycle`，再去取数据。

```
Usage:
  dws oa approval list-efficiency-metrics [flags]
Example:
  dws oa approval list-efficiency-metrics
  dws oa approval list-efficiency-metrics --metric-ids "<metricId1>,<metricId2>"
Flags:
      --metric-ids string   指标 ID 列表，多个用逗号分隔（可选；不传返回精简指标目录）
```
MCP 工具: `list_process_efficiency_metrics`；参数: `metricIds`（string 数组，可选）。不带参数调用返回精简目录（metricId、名称、业务含义、数据形态）；传入 `metricIds` 后追加 `fields` 与支持的 `timeCycles` 等完整详情，未识别的 metricId 会被静默忽略。返回的 `metricId` / `timeCycle` 直接用于 `query-efficiency-metric` 的 `--chart-id` / `--time-cycle`。

### 查询流程效率指标数据

> **IMPORTANT：** 仅企业钉钉管理员可调用。`--chart-id` 必须是 `list-efficiency-metrics` 返回的 `metricId`；`--time-cycle` 是闭合枚举，且各指标支持的周期以 `list-efficiency-metrics` 返回为准。

```
Usage:
  dws oa approval query-efficiency-metric [flags]
Example:
  dws oa approval query-efficiency-metric --chart-id <metricId> --time-cycle last30days
  dws oa approval query-efficiency-metric --chart-id <metricId> --time-cycle this_month --keyword <关键字> --limit 10
  # 高级用法：传入完整下钻/分页 JSON
  dws oa approval query-efficiency-metric --chart-id <metricId> --time-cycle last7days --chart-query '{"keyword":"差旅","limit":20}'
Flags:
      --chart-id string                指标 ID，取自 list-efficiency-metrics 返回的 metricId (必填)
      --time-cycle string              时间周期：this_week、last7days、last_week、last14days、this_month、last30days、last_month (必填)
      --chart-query string             完整下钻/分页参数 JSON（高级模式，与简单模式互斥）
      --ding-user-id string            按人员维度下钻，传组织内 staffId；是否生效因指标而异（可选）
      --process-template-code string   按审批模板维度下钻的 processCode；是否生效因指标而异（可选）
      --keyword string                 按名称模糊搜索的关键字（可选）
      --limit string                   返回行数，服务端默认 30（可选）
      --cursor string                  分页游标，传上一页 props.cursorKey 指定字段的值（字符串）；首页可省略（可选）
```
MCP 工具: `query_process_efficiency_metric`；参数: `chartId`、`timeCycle` 必填，`chartQuery` 为可选的下钻/分页对象（键为 `ding_user_id`、`process_template_code`、`process_code`、`keyword`、`limit`、`cursor`）。简单模式的五个下钻 flag 会自动折叠进 `chartQuery`，与 `--chart-query` 互斥。返回形态随指标而变：指标卡、趋势图、排行榜、饼图、明细表或说明文案。

实测要点（`chartQuery` 在 MCP inputSchema 中是 `properties` 为空的不透明对象，各键语义由服务端该指标的 SQL 模板决定；以下为真实链路 + 服务端 SQL 模板双向核对结果）：

- **游标是字符串，不是数字**：服务端 SQL 作 `process_submit_time < ':cursor'` 的字符串比较，默认值 `"999999999999"`。取值必须是返回体 `props.cursorKey` 指定字段的值（明细表通常是 `process_submit_time`，形如 `"2026-09-02 16:14:57"`）。传数字**不报错但等价于不过滤**——字典序上任何时间戳都小于纯数字串，于是永远停在首页；翻页失效时先检查游标类型。
- **页大小**：不传 `limit` 默认 30 行；SQL 中是 `limit :limit`（不带引号），简单模式 `--limit` 会以数字下发，实测支持到 100 以上。走 `--chart-query` 时 `limit` 也请传 JSON 数字而非字符串。
- **下钻键分三类，不要一概而论**：
  - `keyword`（30 个指标支持）：真正的可选过滤，SQL 用 `/*keyword and process_title like '%:keyword%'*/` 条件注释包裹，不传时该条件不参与查询；传不匹配的关键字返回 0 行。
  - `process_template_code`（仅 `corp#detail#proc_inst_eff#Table`、`proc_inst_status_complete_filter#Table`、`proc_inst_status_running_filter#Table`）与 `ding_user_id`（仅 `corp#detail#user_inst_eff#Table`、`user_inst_status_complete_filter#Table`、`user_inst_status_running_filter#Table`、`inst_go_down_all/complete/running#table`）：在这些指标上是**裸占位符，等同必填**——不传会让 SQL 残留字面量 `:key`，**静默返回 0 行**而不报错；在其余指标上传了则完全无效（服务端只做字符串替换，多余键被忽略）。
  - `process_code`（仅 `inst_go_down_all/complete/running#table`）：与 `process_template_code` 是**不同的键**，没有独立 flag，需用 `--chart-query '{"process_code":"PROC-..."}'` 传。已验证生效（30 行 → 10 行单一模板；不存在的 code → 0 行）。
- **`--ding-user-id` 传组织内 staffId，排行榜返回的 `ding_user_id` 可以直接回灌**：服务端先按 staffId 在组织内解析成 uid（覆盖离职员工——审批单的发起人/审批人不排除已离职），因此纯数字、带前导零、甚至 22 位超出 Long 范围的 staffId 都能正常返回数据。同一组织内实测 6 个纯数字 staffId（含 `68674200835816`、`013723314234860683`、`0244544159151353836778`）全部由 0 行变为 30 行，且不同人的结果集 `business_id` 两两不相交。解析不到时的退化分级见下方三级行为矩阵。
- **返回字段名随 `timeCycle` 变化**：后缀与周期一一对应（`this_week`→`_cw`、`last7days`→`_7d`、`last_week`→`_c1w`、`last14days`→`_14d`、`this_month`→`_cm`、`last30days`→`_30d`、`last_month`→`_c1m`），例如 `process_inst_cnt_cw` 与 `process_inst_cnt_30d`。取数前先读返回体的 `metaList[].fieldId`（自描述，含 `displayName`、`hidden`），**不要硬编码字段名**，否则换周期就会取到 null。
- **已知服务端缺陷**：`corp#detail#inst_go_down_running#table` 的 SQL 模板在 `':cursor'` 后多了一个游离的 `and`，两个可选条件都不传时最终 SQL 变成 `and and (...)`，基线调用即报 `token AND` 语法错误（形如 `ERROR. pos 786, line 1, column 784, token AND`，pos/column 随传入的可选条件数量变化，实测也出现过 `pos 720, column 718`）；同族的 `inst_go_down_all#table`、`inst_go_down_complete#table` 没有这个问题，可正常查询。遇到该错误应换指标或反馈服务端，而非调整自己的参数；CLI 会以结构化错误呈现并带 `trace_id`。该缺陷位于服务端 Diamond 配置 `ecds_efficient_chart_query_config.json` 的 SQL 模板中，**不随应用代码发布修复**，需单独走配置发布。

`--ding-user-id` 取值的三级行为矩阵（决定 0 行到底是哪种原因，遇到 0 行先按此分诊）：

| 传入值 | 服务端处理 | 可观察结果 |
|---|---|---|
| 组织内真实存在的 staffId（纯数字、带前导零、22 位超 Long 范围都算） | `staffId2Uid` 在组织内解析成 uid 后再拼进 SQL | 正常返回该人数据；不同人的结果集两两不相交 |
| 解析不到，且纯数字能解析成正 Long | 兜底把原值当 uid 拼进 SQL，只打 warn 日志 | **静默返回 0 行且不报错**——最容易误判成"这个人没数据" |
| 解析不到，且非数字或纯数字超出 Long 范围 | 参数校验失败 | 报参数错误 `illegal.args.not-empty`（旧行为是 `5000005`「系统开小差了，请稍后再试」，看不出是参数问题） |

因此 0 行有三种互不相同的原因，不要合并处理：① 该指标漏传了等同必填的下钻键（SQL 残留字面量 `:key`）；② `--ding-user-id` 传的值不是该组织内真实存在的 staffId，落到矩阵第二级被当 uid 兜底；③ 该周期内确实没有数据。区分方法：先用排行榜原样回灌 `ding_user_id` 复现（能出行说明链路正常），再换已知有数据的人或缩短下钻条件验证。

### 查询表单可统计字段

> **IMPORTANT：** 仅企业钉钉管理员可调用。这是 `query-statistic-data` 的前置命令：先用它拿到某审批表单可统计字段的 `schemaFieldId`（即返回的 `fieldName`），再去取数。

```
Usage:
  dws oa approval list-statistic-fields [flags]
Example:
  dws oa approval list-statistic-fields --form-code <formCode>
Flags:
      --form-code string   审批表单 formCode (必填)
```
MCP 工具: `list_form_statistic_fields`；参数: `formCode`（必填）。返回该表单当前可用于统计的字段清单，每个字段含 `fieldName`（唯一标识，直接用作 `query-statistic-data` 的 `--schema-field-id`）、`displayName`（显示名）、`componentName`（组件类型）、`fieldValueType`（值类型：Long/Double/BigDecimal 等数值型才可 SUM/AVG/MIN/MAX，文本/选择型用 COUNT/COUNT_DISTINCT）；列表额外含合成字段 `dataId`，表示按表单提交条数统计（配 `--aggregate-type COUNT`）。formCode 与 processCode 同为 `PROC-` 前缀，可从 `list-forms` / `search-forms` 获取。

### 查询表单统计数据

> **IMPORTANT：** 仅企业钉钉管理员可调用。`--schema-field-id` 必须是 `list-statistic-fields` 返回的 `schemaFieldId`；`--chart-type` 与 `--aggregate-type` 均为闭合枚举。

```
Usage:
  dws oa approval query-statistic-data [flags]
Example:
  dws oa approval query-statistic-data --form-code <formCode> --chart-type smart-app-indicator-item --schema-field-id <schemaFieldId> --aggregate-type COUNT
  dws oa approval query-statistic-data --form-code <formCode> --chart-type smart-app-line-chart --schema-field-id <schemaFieldId> --aggregate-type SUM --start-date 2026-08-01 --end-date 2026-08-31
  # 高级用法：传入完整 chartQueryRequest JSON
  dws oa approval query-statistic-data --request '{"formCode":"PROC-xxx","chartType":"smart-app-table-view","schemaFieldId":"dataId","aggregateType":"COUNT"}'
Flags:
      --form-code string             审批表单 formCode（简单模式使用；与 --request 互斥）
      --chart-type string            图表类型：smart-app-indicator-item / smart-app-indicator-card / smart-app-line-chart / smart-app-table-view / smart-app-list-chart（简单模式使用；与 --request 互斥）
      --schema-field-id string       统计字段 ID，取自 list-statistic-fields 的 fieldName；传 dataId 按提交条数统计（简单模式使用；与 --request 互斥）
      --aggregate-type string        聚合方式：SUM / AVG / MIN / MAX / COUNT / COUNT_DISTINCT（简单模式使用；与 --request 互斥）
      --start-date string            开始日期 yyyy-MM-dd（smart-app-line-chart 必填）(可选)
      --end-date string              结束日期 yyyy-MM-dd（smart-app-line-chart 必填）(可选)
      --user-ids string              指定查看的用户 staffId 列表，多个用逗号分隔；不传时管理员查看全量数据 (可选)
      --offset int                   分页偏移，smart-app-table-view / smart-app-list-chart 用 (可选)
      --limit int                    分页大小，最大 100，smart-app-table-view / smart-app-list-chart 用 (可选)
      --request string               完整请求 JSON（高级模式；与简单模式参数互斥）
```
MCP 工具: `query_form_statistic_data`；参数封装在 `chartQueryRequest`（formCode、chartType、schemaFieldId、aggregateType 必填；startDate、endDate、userIds 可选；offset、limit 折叠进嵌套的 `state` 子对象，用于 smart-app-table-view / smart-app-list-chart 分页）。简单模式各 flag 会自动折叠进 `chartQueryRequest`，与 `--request` 互斥。数据口径固定：仅统计审批通过且未作废的实例，按创建时间过滤；`--user-ids` 可指定查看的用户 staffId 列表（管理员下钻）。`--chart-type` 决定返回形态：smart-app-indicator-item / smart-app-indicator-card 为单值指标，smart-app-line-chart 为按日趋势（需 `--start-date` + `--end-date`），smart-app-table-view 为明细表格，smart-app-list-chart 为按日倒序列表。`--aggregate-type` 中 SUM / AVG / MIN / MAX 仅数值字段可用，COUNT / COUNT_DISTINCT 任意字段可用，字段与聚合方式的兼容性由服务端判定。

> **验证状态（预发）**：`list_form_statistic_fields` 已在预发网关验证可用；`query_form_statistic_data` 的 `chartType` 枚举已按刷新后的 live 契约更正为 `smart-app-` 前缀（此前对裸值 `tools/call` 返回 `no such chart`，根因即缺少该前缀），并移除了 live 契约中已不存在的 `allowViewAllData` / `relatedFormCode` / `relatedDirection` / `hideIndicatorLabel`。CLI 侧枚举与折叠逻辑以工具描述这一权威契约为准，建议在真实 `formCode` 上按 evidence 复测各 chartType。


## 注意事项

- `list-efficiency-metrics` / `query-efficiency-metric` 都**仅企业钉钉管理员可调用**，非管理员服务端返回「权限不足，请联系管理员」，不是参数问题，不要重试或改参数
- `query-efficiency-metric` 的 `--chart-id` 不能凭空猜测，必须先由 `list-efficiency-metrics` 取得 `metricId`；`--time-cycle` 是闭合枚举（this_week / last7days / last_week / last14days / this_month / last30days / last_month），但**每个指标实际支持的周期不同**，以 `list-efficiency-metrics --metric-ids` 返回的 `timeCycles` 为准
- `query-efficiency-metric` 的返回形态随指标而变（指标卡 / 趋势图 / 排行榜 / 饼图 / 明细表 / 说明文案），不要假定固定字段；只有明细表形态才支持 `--limit` + `--cursor` 翻页。**数据字段名带周期后缀**（`this_week`→`_cw`、`last7days`→`_7d`、`last_week`→`_c1w`、`last14days`→`_14d`、`this_month`→`_cm`、`last30days`→`_30d`、`last_month`→`_c1m`），换周期就换字段名，取数前先读返回体 `metaList[].fieldId`，硬编码字段名会取到 null
- `query-efficiency-metric` 的 `--chart-query` 与五个简单下钻 flag（`--ding-user-id` / `--process-template-code` / `--keyword` / `--limit` / `--cursor`）互斥；常规下钻优先用简单 flag，只有需要一次传多个下钻键时才用 `--chart-query`
- `query-efficiency-metric` 的游标是**字符串**，取上一页返回体 `props.cursorKey` 指定字段的值（如明细表的 `process_submit_time`）；服务端作字符串比较且默认值为 `999999999999`，传数字不报错但等价于不过滤，表现为翻页永远停在首页。不传 `--limit` 时服务端默认返回 30 行
- `query-efficiency-metric` 的下钻键**是否生效完全取决于目标指标的 SQL 模板**，分三类：`--keyword` 是真正的可选过滤（30 个指标支持）；`--process-template-code`（仅 `proc_inst_*` 三个指标）与 `--ding-user-id`（仅 `user_inst_*`、`inst_go_down_*` 六个指标）在这些指标上**等同必填，不传就静默返回 0 行**，在其余指标上传了则完全无效；`inst_go_down_*` 还另支持一个不同的键 `process_code`（无独立 flag，需走 `--chart-query`）。因此下钻后必须核对返回行是否真的收敛；遇到 0 行先分清是"没数据"、"漏传了该指标的必填下钻键"，还是"`--ding-user-id` 传的值不是该组织内真实存在的 staffId"
- `query-efficiency-metric` 的 `--ding-user-id` 传组织内 staffId，指标返回的 `ding_user_id` **可以直接回灌**：服务端按 staffId 在组织内解析成 uid，纯数字、带前导零、超 Long 范围的 staffId 都生效。解析不到时才退化——纯数字兜底当 uid 查询（仍可能静默 0 行），非数字或超 Long 范围报参数错误 `illegal.args.not-empty`
- `corp#detail#inst_go_down_running#table` 有服务端 SQL 模板缺陷（游离 `and`），不带任何参数的基线调用就报 `token AND` 语法错误；同族的 `inst_go_down_all#table` / `inst_go_down_complete#table` 正常。遇到这类错误应换指标或反馈服务端，而非改自己的参数；该模板存于服务端 Diamond 配置，不随应用代码发布修复
- `list-statistic-fields` / `query-statistic-data` 都**仅企业钉钉管理员可调用**，非管理员服务端返回「权限不足」，不是参数问题，不要重试或改参数
- `query-statistic-data` 的 `--schema-field-id` 不能凭空猜测，必须先由 `list-statistic-fields` 取得 `schemaFieldId`；`--chart-type`（smart-app-indicator-item / smart-app-indicator-card / smart-app-line-chart / smart-app-table-view / smart-app-list-chart）与 `--aggregate-type`（SUM / AVG / MIN / MAX / COUNT / COUNT_DISTINCT）均为闭合枚举，CLI 侧会拦截拼写错误
- `query-statistic-data` 的 `--chart-type smart-app-line-chart`（按日趋势）必须同时提供 `--start-date` 与 `--end-date`（`yyyy-MM-dd`）；`--offset` / `--limit` 仅对 smart-app-table-view / smart-app-list-chart 分页有意义，会折叠进 `chartQueryRequest.state`，`--limit` 上限 100
- `query-statistic-data` 的 `--request` 与全部简单模式 flag 互斥；常规取数优先用简单 flag，只有需要一次传完整 `chartQueryRequest` 时才用 `--request`
- **预发验证状态**：`list_form_statistic_fields` 已在预发验证可用；`query_form_statistic_data` 的 `chartType` 已按 live 契约更正为 `smart-app-` 前缀（此前裸值返回 `no such chart` 即因缺前缀），并移除 live 契约中已不存在的 `allowViewAllData` 等字段，建议在真实 `formCode` 上复测
