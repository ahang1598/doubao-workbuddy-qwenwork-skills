# BaseApp 真实标识、返回与恢复

App命令为 `lark-cli base +app-* / +workspace-*`，参数/枚举/基础示例看精确help，复杂JSON读对应协议。interaction-config可用 `--print-schema --flag-name <flag>`，不假定全部flag有schema。

## 调用前核对与返回

### 命令 flag 速查（先定位再写配置；flag 名 ≠ 响应字段名）

| 命令 | 必填/常用 flag | 高频错误 |
| --- | --- | --- |
| `+app-block-create` | `--app-token --page-id --name --type`；可选 `--sub-type --data-config` | 漏 `--page-id`；data_config 不按组件协议 |
| `+app-block-get` | `--app-token --page-id --block-id` | 用 `--widget-id`（不合法） |
| `+app-block-update` | `--app-token --page-id --block-id`；配置 `--data-config`/`--ai-config` | 用 `--widget-id` |
| `+app-block-get-data` | `--app-token --base-token --block-id`；图表优先 `--chart-token` | 拿组件 ID 当取数 token |
| `+app-block-list` | `--app-token --page-id` | — |
| `+app-page-create` | `--app-token --name`；可选 `--node-type --page-group-id --icon` | 重名前未先查重 |
| `+workspace-move-in` | `--workspace-token --entity-token` | 用 `--base-token`（不合法） |

定位/更新用--block-id，响应才叫widget_id/block_id。写前读 [公共配置](app-block-config.md)，目录移入用entity_token。

| 对象 | 真实标识与边界 |
| --- | --- |
| Workspace | `workspace_token`；目录用 workspace-entity-list，移入的 `entity_token` 是真实 Base 或 App |
| App | `app_token`；与关联 Base 的 `base_token` 不同；App 创建只建空应用 |
| Page / PageGroup | Page 用 `page_id`；组返回 `page_group_id`，组/树的名称寻址命令用唯一业务名称 |
| 组件 | 响应字段 `widget_id`/`block_id`；命令定位统一用 flag `--block-id`（不是 `--widget-id`） |
| 图表计算结果 | 用返回的 `chart_token`；get-data 优先写 `--chart-token`，兼容 `--block-id` 同样接收 chart token |

核退出码/ok=true后解析未投影路径；JSON/投影/Record NDJSON区别按 [调用契约](../shared-cli-invocation.md#响应解析)。

| 命令 | 成功返回路径 | 使用 |
| --- | --- | --- |
| app-create | `data.app.app_token`、`data.workspace_token` | 不返回默认 Page ID；保存 App 后补读 get |
| app-get | `data.app_token`、`data.pages`、`data.ref` | ref 为 Base token → 已引用 Table 名称数组，未引用 Base 不出现 |
| page-list / page-tree-list / block-list | `data.items`、`data.has_more`、`data.page_token` | 需要完整集合时串行翻页到结束 |
| page-get | `data.page.widgets` | 组件摘要；完整配置另读 block-get |
| block-create / block-get | `data.block.widget_id`、`data.block.chart_token` 及配置各层 | 保存两类 ID，不假定 `data.blocks` 存在 |
| structure-get | `data.navigation`、`data.pages[].widgets`、`data.appearance` | 完整导航、页面、递归容器与布局；该命令没有 page-id |
| block-get-data | `data` 中的计算结果 | 按 [结果格式](../dashboard-chart-result.md#返回结构总览) 解析；AI 按同文 AI Block 结果 |

写入即生效、无暂存/自动回滚；保留原stdout/stderr/退出码。解析失败/超时先get/list，不重发创建取token；投影无完整信封，兼容ID原样复用。

## ref 表名解析

`+app-get` 的 `data.ref` 是 `base_token -> table_name[]`，不是表 ID 列表，也不存在 `ref.base_token` 字段。需要权限表全集或 AI Block 来源时，按以下规则定位：

1. 对所需的每个 `ref` key 调用 `+table-list --base-token <base_token>`，取得该 Base 的完整 `data.tables`。逐个用 `ref[base_token]` 中的表名精确匹配 `tables[].name`；每个名称必须只匹配一个真实 `id`，保留 `base_token + table_id + name`。Base 中未被 `ref` 引用的表不加入 App 表全集。
2. 已知目标表 ID 时，先在已确定的 Base 表列表中按 `id` 找到真实 `name`，再确认该名称属于对应的 `ref[base_token]`。AI 的 `data_sources[0]` 使用该 Base key 和真实 `table_name`；不能拿 ID 直接匹配 `ref` value。只有一个 Base key 时也必须核对目标表。
3. 跨 Base 同名表按各自 `base_token` 分别解析；目标 Base 未确定且多个 Base 都有同名目标时，停止该项并澄清，不取第一个 key。同一 Base 内表名缺失或匹配不唯一时也停止该项，不猜 ID、不静默跳过。集合授权和仅修改未来默认档依赖完整既有表全集，任一项未解析完成时不得继续相关权限写入。

例如 `ref={"baseA":["订单","客户"]}`，`table-list` 返回 `tblOrders/订单`、`tblCustomers/客户`、`tblSalary/工资`：App 表全集是前两张；按 `name` 匹配后分别保留 `tblOrders`、`tblCustomers`，不包含工资表，也不能因 ID 与表名不同而得到空全集。

## 定位与数据读取

- /app/链接url-resolve复用真实App/Workspace/Page，无全局app-list，仅已知Workspace列type=baseapp。
- Page空名表示无权限，停止该页读写；unsupported只认列表摘要，不get/get-data/update。
- 图表Base取本组件data_config.base_token，AI取ai_config.data_sources[0].base_token，不任取ref；非图表有chart_token不代表可取数。
- list/view/text/button/容器不套图表取数，列表/视图按配置真实来源读效果，配置/计算/运行/渲染分证。

### 同名与嵌套目标的正向示例

完整树/structure定位App→Page→父容器/pane→widget→chart_token，同名不同页不抵扣。分析页去分组只验该ID，不拿首页判失败；嵌入表格改widget.name不改外tabPane，点名页签才改pane。首页看板核type/归属，progress不换statistics；仅名/样式不重配源，缺粉丝量不换商品数排序。

## 创建与更新边界

- 同Workspace单Base列表，创建/移入/默认页复用按 [create](../../scenes/app-mode/create.md#第-3-步创建-app-与页面)。
- Page/组共享大小写敏感名称空间，trim、≤100字符、不含 `/ \ ? * [ ] :`；同页组件名唯一，先完整读取消歧。
- 组≤2层、禁止自环/移后代，导航目标互斥；组删除级联子树，先核授权/完整子树，cascade/yes，留≥1Page。
- 主题/背景独立，顶部vertical/侧边horizontal，Page布局另管；更新仅显式字段，未点名保持。
- 五层Patch/清空/数组按 [公共配置](app-block-config.md)，省略保持/null不清空；同页串行，data_sources完整有序替换。
- 11标准图可原位互转，核widget/chart、父级、矩形、保留项；其它type/全部sub_type不能改。AI建/patch/Base约束读 [AI宿主](component-ai-chart.md)，不用普通data_config。
- 同页 `+app-block-move`；普通非View完整子树无View时同App跨页 `+app-block-copy --target-page-id`。单View按 [公开重建](component-view.md#复制单个-view按公开配置新建) get→一次完整create→get（目标页/新名、保留源）；含View容器不copy/承诺整树无损。目标回读后仅明确搬走且授权删除才删普通源。跨App、App克隆、Page复制不支持，不造壳。

## 删除应用

删除交lark-drive：`lark-cli drive +delete --file-token <app_token> --type bitable --yes`，先App get/Workspace核目标/授权，Drive中App/Base均bitable。Drive files patch的new_title仅改App标题。

## 常见恢复

固定原目标、类型、父级、来源、资格、时间、指标、动作与布局，保留完整错误；先查已生效部分，再修已证明错误的参数。

| 现象 | 处理 |
| --- | --- |
| partial / 结果未知 | get/list 核实际状态，仅续做未生效项；不重发整批 |
| Skill 与 CLI 不一致 | 保存实际命令、可读取的 version/哈希和原始 help/错误；版本未知就明确未知，保留 blocked，不换历史 binary 或改 Profile |
| Page/组/组件重名 | 完整读目录，核类型/父级并复用已创建 ID；同名组不能当 Page |
| 组内 Page 创建失败 | 先核是否已存在；已存在则 page-update parent-id 归组并回读，不去掉原归组要求求成功 |
| 列表 Base 不在同 Workspace | 核真实归属，按授权解决来源；不擅自移动已有资源 |
| 配置被拒 | 按错误和对应协议修形状，保留完整 filter/series/group_by/time_range；不删条件或换源换指标 |
| 配置正常但页报错/错数据 | 固定App/Page/widget/chart、源Base/表、身份/时点，比block-get/get-data/真实页；取数对但渲染错、打开配置才恢复分别留证，不换源/删filter，未定位报未完成/缺链路证据 |
| 原组件更新/换型受阻 | 保留原资源与缺口，不新建替代组件冒充修改 |
| AI NotSupported | 核 ai_chart、ai-config 与部署能力，保留原要求，不降级普通图表 |

App 的缺少能力不能用 dashboard 命令、OpenAPI 或其它域同名对象绕过；ACL 拒绝保留为环境/权限阻塞。末次交付按 [回读要点](app-checks.md)。

## AI 存量编辑兼容

AI Block（含存量 VChart）的 patch 与取数按 [AI Block 协议](../ai-block.md)，保持原 ID、来源和未点名配置。
