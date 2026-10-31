# Base 命令调用与恢复约定

本页维护命令确认、输入输出与技术错误处理；授权、完成态、同因恢复预算见[主入口](../SKILL.md)，目标决策与业务验收见对应 Scene。
## 命令确认

命令或参数不确定时，读取精确子命令 `--help`，确认 Usage 指向该命令；父级帮助退出 0 不证明子命令存在。复用本环境已确认且仍有效的参数信息，不反复探测。

帮助或 dry-run 只验证本地调用，不证明 API 支持。遇到明确的未知字段或能力错误，保留错误并按对应 Reference 核对支持条件；不得猜命令、移植其他命令参数或删减业务约束。
## 参数与输出

Base、表、字段、选项、ID 必须来自本次任务的可信返回；未确认目标时先按 [Base Token 与 ID 解析](../SKILL.md#base-定位与读取)定位。
裸字符串 flag（如 `--description`）传真实换行：`$'第一行\n第二行'`；`'...'`、`"..."` 中的 `\n` 会原样落库。JSON 参数（如 `--json`、`--questions`）必须传 `\n` 转义，传真实换行会解析失败。写后回读；出现字面 `\n` 即失败并重写。
### 响应解析

分别保留 stdout、stderr、退出码，不用 2>&1 混入 JSON。普通 JSON 响应先确认退出成功且 ok=true；--jq 等投影结果按表达式解析，不要求原信封。Record NDJSON 按[读取协议](record-read.md#解析返回与完整分页)检查 manifest 与完整分页。
按命令契约读取实际层级；不得盲读 data/items/blocks 或把失败当空数据。解析失败只修解析，不重放成功写入；写入结果未知时先按恢复规则确认实际状态。

### 返回键速查

以下是成功输出的实测层级；表外命令按对应 Reference 读取。

| 命令 | 实际结构 |
|---|---|
| `+base-create` / `+base-get` | `data.base.base_token` / `data.base.is_advanced` |
| `+table-create` / `+table-list` | `data.table.id` / `data.tables[].{id,name}` |
| `+field-create` / `+field-list` | create 只建 1 个字段（单对象或单元素数组）返回 `data.field.{id,name,type}`，建 2 个及以上返回 `data.fields[]`；统一取 ID：`--jq '(.data.fields // [.data.field])[] \| {id,name,type}'`；`data.created` 是布尔。list 读 `data.fields[].{id,name,type}` |
| `+record-list --format json` | `data.{data,fields,field_id_list,record_id_list,has_more}`，`data.data` 每行是数组 |
| `+record-list` 默认 | 顶层 manifest `{records_count,has_more,record_file,manifest_file,columns}`，无 `data` 层 |
| `+record-batch-create` | `data.record_id_list[]` |
| `+view-create` / `+view-list` | `data.views[0].id` / `data.views[]` |
| `+form-create` / `+form-questions-list` | `data.{id,name}` / `data.questions[].{id,title,type,required}` |
| `+dashboard-create` | `data.dashboard.{dashboard_id,name,theme}`，取 ID：`--jq '.data.dashboard.dashboard_id'` |
| `+dashboard-block-create` / `+dashboard-block-list` | `data.block.block_id` / `data.items[].{block_id,name,type,position}` |
| `+dashboard-block-get-data` | `data.dimensions[].alias`；`data.main_data[]` 每项以 alias 为键 `{"<alias>":{"value":...}}`；先 dump 再取 |
| `+dashboard-layout` | `data.layout[]`（整盘最终坐标）、`data.written_block_ids`、`data.tidied_block_ids`、`data.grid_cols` |
| `+role-create` / `+role-get` / `+role-list` | `data.data` 是字符串化 JSON（jq 用 `fromjson`，Python 用 `json.loads`）；`+role-list` 解开后 `base_roles[]` 每项仍是 JSON 字符串，再 `fromjson` 一次 |
| `+workflow-create` / `+workflow-list` / `+workflow-get` | `data.workflow_id` / `data.items[]` / `data.{workflow_id,title,status,steps}` |

### 命令写法速查

只替换以下成功写法中的 ID 和值；表外命令先查精确子命令 --help。+record-batch-create、+view-create 均以 lark-cli base 开头，带 --base-token "$BASE_TOKEN" --table-id "$TABLE_ID" 与 --as user。

| 命令 | 写法、限制与判定 |
|---|---|
| +record-list 数量／抽样 | --format json --limit 200 --jq '.data.data \| length'；--jq 只配 --format json。data.data 行数组与 data.fields、data.field_id_list、data.record_id_list 同序，行内无 record_id。 |
| 按字段名取列 | --jq '(.data.fields\|index("数量")) as $i \| .data.data[] \| .[$i]'；支持完整 jq：as、map、切片、select、join。读法见[记录读取](record-read.md#常用读取写法)。 |
| jq 对象键 | 裸中文键会被拒：{日期:.[0]} 报 unexpected token；写 {"日期":.[0]} 或英文键。 |
| +record-list 参数 | 只有 --filter-json、--sort-json、--field-id（可重复）、--view-id、--limit、--offset、--format、--output、--jq；无 --sort/--filter/--fields/--field-ids。 |
| +record-list 全量 | 默认 NDJSON：stdout 是多行 manifest（record_file、records_count、has_more），记录在 record_file 里逐行；manifest 整体 json.load，不套 data 层。只看条数：\| grep -o '"records_count":[0-9]*'。 |
| +record-batch-create | 只有 --json，无 --records/--data：--json '{"create_records":[{"名称":"A","单选":["待处理"],"负责人":[{"id":"ou_xxx"}],"关联表":[{"id":"recxxx"}],"日期":"2026-10-21 08:00:00","数量":3}]}' |
| batch-create 前置／原子性 | 先 +field-list 取字段名和选项列表；选项不够先 +field-update 加。任一条记录出错，整批都不写。 |
| batch-create not_found | 触发：字段名不存在、单选／多选选项不存在、人员 ID 不存在、table_id 不存在；不触发：关联记录 ID 错误、数字写成字符串、日期只到天。 |
| +record-batch-update | --json '{"update_records":{"recxxx":{"状态":["完成"]}}}' |
| +table-create / +base-create --fields | 每项 {"name","type"}，可选 style/options/link_table；无 property/formatter/default_value/date；双向关联必带 bidirectional_link_field_name；select 的 options 每项写 {"name":"选项"}，写成字符串数组会被拒。+table-create 必带 --name 和非空 --fields；--table-name 只属 +base-create。模板见[字段 JSON 模板](table-commands.md#字段-json-模板)。 |
| +field-create | 只有 --json，一律传数组 '[{...}]'，单字段也包数组；无 --name/--type。formula、lookup 必带 --i-have-read-guide；formula 用 expression 且不收 style；lookup 必带 where。金额、价格的 number 字段带 currency 样式，电话的 text 字段带 phone 样式，见[字段选型](../scenes/field.md)；formula 带 style 报 Unrecognized key(s) in object: 'style'。返回结构与取 ID 见上方返回键速查。示例见[创建字段](field-commands.md#调用示例)。 |
| +field-update | --field-id --yes --json；JSON 是完整字段定义（覆盖写），必带 name 和 type，只传 style、options 或 multiple 会报 Invalid discriminator value；无 --name。 |
| +view-create | --json `'{"name":"<视图名>","type":"kanban"}'`；type=grid/kanban/gallery/calendar/gantt；无 --name/--type，键不是 view_name/view_type。 |
| +view-set-sort/-group/-visible-fields/-timebar | --table-id --view-id 加 --json，依次为 {"sort_config":[{"field":"金额","desc":true}]}、{"group_config":[{"field":"状态","desc":false}]}、{"visible_fields":["标题","状态"]}。 |
| +view-set-filter | --json '{"logic":"and","conditions":[["状态","intersects",["进行中"]]]}'，不包 filter_config 外层。条件写法见[视图筛选](view-filter.md)。 |
| timebar JSON | {"start_time":"开始日期","end_time":"结束日期","title":"标题"}；三项必填，起止只能是日期字段或创建时间。 |
| +form-create | --table-id --name `"<表单名>"`，无 --json；创建前 +view-list 查同名 form。 |
| +form-share-update | 必带 --table-id --form-id。每次只带一个设置项，分条依次调用 --enabled=true、--access-scope tenant（invite/tenant/anyone）、--require-login=true；布尔用等号；无 --shared/--json。见[分享设置示例](form-share.md#分享设置示例)。 |
| +form-questions-* | 均必带 --table-id --form-id；新表单含全部可用字段。更新：+form-questions-update --questions '[{"id":"fldX","title":"...","required":true}]'，无 --question-id。 |
| 删除表单题 | +form-questions-delete --question-ids '["fldX"]' --keep-field --yes，≤10 个。公式／查找／自动编号字段不能新加为题目；`+form-questions-list` 已列出的照常按 id 删除。 |
| +dashboard-create | --base-token --name，可选 --theme-style；取 ID：--jq '.data.dashboard.dashboard_id'。同名再建报 API error [1]；创建报错或取到 null 时先 +dashboard-list 查是否已建，不重建。 |
| +dashboard-block-create | 必带 --dashboard-id。先按[Dashboard 开工必读](../scenes/dashboard.md#开工必读)写范围、粒度、指标、排序；调用 --name --type --data-config '{...}' --position '{"x":<x>,"y":<y>,"w":<w>,"h":<h>}'（坐标按视觉规范的组件清单和尺寸表定）--jq '.data.block.block_id'。 |
| dashboard create 配置 | 表名放 data_config.table_name；无 --table-id/--json。data_config 形态见[常用形态示例](dashboard-chart-config.md#常用形态示例)。 |
| +dashboard-block-list | 必带 --dashboard-id；返回 data.items[]（block_id/name/type/position），不是 data.blocks。 |
| +dashboard-layout | 必带 --dashboard-id 和 --layout '[{"block_id":"<block_id>","x":<x>,"y":<y>,"w":<w>,"h":<h>},...]'（坐标按视觉规范的组件清单和尺寸表定）；坐标只走 --layout，不包 blocks，须含盘上全部组件。get-data 报 API error [1] 时同一组件只重读一次，仍报错就改用 +dashboard-block-get 核对配置并在答复说明，不串 sleep。 |
| +role-create 前置 | 先按[Permission 开工必读](../scenes/permission.md#开工必读)逐句映射角色、表、能力、记录范围；+base-get 查 data.base.is_advanced，false 时执行 +advperm-enable（不收 --yes）。 |
| +role-create 调用 | 只有 --json，无 --name；不支持 @file，用 "$(cat f.json)"；取 ID：--jq '.data.data \| fromjson \| .role_id'。 |
| role API error [1] 触发 | table_rule_map/dashboard_rule_map/field_perms 引用不存在的表名、看板名、字段名（表用名称而非 table_id）；非法 perm；表项缺 perm/view_rule/record_rule/field_rule 任一项（read_only 也须全）；角色名重复。 |
| role 不触发 | perm:"manage"、真实看板的 dashboard_rule_map、specify 只列部分字段、省略 base_rule_map。序列见[建角色命令序列](permission-role-commands.md#从零建角色的命令序列)。 |
| +role-update / +role-list | update：--role-id --yes --json，JSON 必带当前 role_name/role_type；list：--jq '.data.data \| fromjson \| .base_roles[] \| fromjson \| {role_id,role_name,role_type}'。 |
| role member | 仅用户点名具体人员时用 +role-member-add --role-id --user-id ou_xxx，无 --member-ids。Base Owner（当前用户）不能加入自定义角色；返回 errCode:4 MsgCannotSpread 时不重试。 |
| +workflow-create 前置／调用 | 先按[Workflow 开工必读](../scenes/workflow.md#开工必读)确定触发、动作、写入目标、接收人（只发通知不算完成）。只有 --json，支持 @file；顶层 `{"client_token":"<唯一>","title":"...","steps":[...]}`。 |
| workflow step／trigger | step 含 id/type/title/next/data，next 是字符串或 null。AddRecordTrigger 必带 table_name、非空 watched_field_name，空值报 Watch Field is empty；SetRecordTrigger 用 `field_watch_info:[{"field_name":"<字段>"}]`。 |
| ReminderTrigger | data 必带 table_name、field_name（日期字段）、unit（MINUTE/HOUR/DAY/WEEK/MONTH）、offset、hour、minute；缺 unit 报 unit 'undefined'。 |
| workflow 条件 | 条件和 filter_info 的 value 都是数组：[{"value_type":"option","value":{"name":"x"}}]。operator 只有 is/isNot/containsAny/doesNotContainAny/containsAll/isEmpty/isNotEmpty/isGreater/isGreaterEqual/isLess/isLessEqual。最小请求体见[创建示例](workflow-commands.md#最小请求体)。 |
## 通用恢复

| 错误 | 动作 |
|---|---|
| exit=127 / binary 不存在 | 暂停业务调用，只做一次路径和 `--version` 复验；仅用工具明确提供的机制恢复，不复制／替换 binary，不改 PATH／软链／加载器。仍失败则报告环境阻塞；恢复后只重试可确认未启动的单条请求。 |
| 文件路径或输入方式被拒 | 使用允许任务目录内的一致 cwd 和相对路径；`@file` / stdin 以精确命令帮助为准；不得靠切目录、软链、复制受限文件绕过校验。 |
| unknown flag / JSON、schema、枚举错误 | 按[命令确认](#命令确认)和对应 Reference，在主入口预算内修正；不得移植其他命令参数或删除用户要求。 |
| 写入 timeout / 502 / 重名 | 先 get/list 核对原目标。已生效则复用；只有确认未生效才重试原请求；仍未知则报告受阻，不改名再建。 |
| `1254291` | 并发写冲突；串行写入，按[主入口等待与重试规则](../SKILL.md#异常恢复与停止条件)处理，保持原目标并先确认已完成结果。 |
## 专项错误索引

人员／选项／资源 `not_found` 时，按 message/hint 核对真实 ID、完整选项、可见性；提示可能只列部分选项，不猜近似值或换身份。参数错误与任务路径／授权问题仍受主入口恢复预算约束。
### 定位与权限

参数错误按 Base 解析协议修正；读取路径或权限问题按 [Base 定位与权限恢复](../scenes/base.md#定位与权限恢复)判断。

| 错误或条件 | 恢复 |
|---|---|
| `param baseToken is invalid` / `base_token invalid` / `NOTEXIST`；Wiki 链接报 not found | 按 [Base 参数错误](base-resolve.md#返回-id-与错误)核对 token 来源与本次可信返回。 |
| `+base-block-list` 报 `missing_scope(base:block:read)` | 区分非必要目录探测与必需目录权限。 |
| 其他工具打开 `/base/` 链接报无权限、需授权或无法读取 | 回到 Base 读取路径。 |
| `91403` | 无权访问该 Base；按实际错误处理授权。 |
| scope／授权不足；出现 `permission_violations`／`hint` | 保留实际错误与提示，按 Base 恢复入口判断所需权限及平台已有授权方式。 |
### 字段与记录

| 错误或条件 | 含义与恢复 |
|---|---|
| `1254045` | 字段名不存在；按[字段与记录错误](record-write.md#字段与记录错误)重新核对字段。 |
| `1254015`；日期／人员／超链接格式错误 | 字段值类型或格式不匹配；按[字段与记录错误](record-write.md#字段与记录错误)核对 schema 与 CellValue。 |
| formula / lookup：`validation_error: validation_error` | 字段名与已有字段重名；先 `+field-list` 查重。 |
| formula / lookup：`compilation failed` | 表达式语法错误，如 `<>` 应改 `!=`；按[公式表达式](field-formula-expression.md)或 [Lookup 配置](field-lookup-config.md)修正。修正请求不能替代计算任务的依赖准备与实际值验证。 |
| `ignored_fields` / `READONLY` | 存在只读字段；按[字段与记录错误](record-write.md#字段与记录错误)修正写入目标。 |
| `1254104` | 批量超过 200；按[字段与记录错误](record-write.md#字段与记录错误)分批。 |
日期、人员、超链接等字段值的完整格式见 [CellValue](record-cell-values.md)。
