# App 数据源、指标与筛选

数据组件创建/来源、字段、筛选、指标、排序修改读命中章节，纯名/样式不读。App CLI按当前schema/真实Base表字段输出，不执行SDK方法、不猜关联标量。

**按任务必须继续读取**（不能以本页摘要代替）：

| 任务 | 必读文件 |
| --- | --- |
| 点名指标、比率、余额、去重、跨层统计 | [指标口径](app-metric-recipes.md)，比率先读 [比率配置](app-metric-recipes.md#比率类指标先定口径再落实指定组件)；分子分母来自不同实体时读 [跨表比率指标配置](app-metric-recipes.md#示例跨表比率退款率) |
| 固定范围、跨页筛选、我的/本人 | [范围合同](app-scope-contract.md)；状态值另读本页状态范围 |
| 临期/逾期、走势、最近/本月、月周粒度 | [时间配方](app-time-recipes.md)，范围覆盖同时读范围合同 |

截断续读正文，不凭链接标题猜规则。

## 标准 App 图表共享协议

标准图与 statistics 使用多源 ChartDataConfig；Dashboard 扁平单源结构不能直接套用。每源字段取值与规范化复用 [普通图表配置](../dashboard-chart-config.md)，筛选操作符和值读 [筛选条件](../dashboard-filter-conditions.md)。

| 顶层键 | 结构与约束 |
| --- | --- |
| base_token | 必填，所有源共用同一 Base；取数命令另带 --base-token |
| data_sources | 至少一个元素的有序数组；每源 table_name 必填，series 与 count_all=true 二选一，group_by 最多2项 |
| data_source_mode | aggregate 默认合并横轴；compare 按源拆系列 |
| sort | `{type:group|value|record,order?:asc|desc}`；statistics 不允许 |

每源的 series[].rollup 大写，group_by[].sort 小写；statistics 禁止 group_by。主源支持 view_name，与 filter 互斥，次源暂不支持 view_name。ranking 虽也使用 data_sources，但有 [自己的单源约束](component-ranking.md)；progress/countdown/pivot/nps 等不使用标准图结构。

```json
{"base_token":"<base_token>","data_sources":[{"table_name":"订单","count_all":true,"group_by":[{"field_name":"地区","mode":"integrated","sort":{"type":"value","order":"desc"}}]}]}
```

```json
{"base_token":"<base_token>","data_source_mode":"compare","data_sources":[{"table_name":"销售表","group_by":[{"field_name":"月份","sort":{"type":"group","order":"asc"}}],"series":[{"field_name":"销售额","rollup":"SUM"}]},{"table_name":"成本表","group_by":[{"field_name":"月份","sort":{"type":"group","order":"asc"}}],"series":[{"field_name":"成本","rollup":"SUM"}]}],"sort":{"type":"group","order":"asc"}}
```

data_sources完整有序替换，换Base须同时带完整源；换表按新schema重建维度/指标/筛选/排序，不继承旧字段；展示修改省略数据层。

filter用conjunction+对象conditions，保留AND/OR/资格/时间，不用logic/元组/containsAny/intersects。日期/ExactDate双边界按配方；拒绝只修形状，不删filter/series/group_by/time_range，超出组合能力补最小公式或blocked。

单选多值是候选集合，不是两等值AND。核真实选项后列表顶层filter（图/卡放data_sources）：

```json
{"filter":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":["进行中","已停滞"]},{"field_name":"截止日期","operator":"is","value":"CurrentWeek"}]}}
```

本周任一状态命中，其它状态/周外排除，无样例仅配置证据；已完成数保留资格AND（可0），不删/换指标。按 [范围合同](app-scope-contract.md) 覆盖全部源，例不替代完整配置。

## 业务口径

- 一行一目标才count_all，N点名指标保留N series/聚合；SUM/AVERAGE核Number或Formula/Lookup最终数值，不用Checkbox当0/1。series仅SUM/AVERAGE/MAX/MIN，不COUNT/COUNTA。
- 计量范围/聚合分开，“已/曾/过/截至/历史”按真实状态/阶段/时间，不全生命周期计数，未知谓词列缺口。
- 比率完整分母、0/1均值限完整对象集；金额比不平均逐行，重复总体比用MAX等单值不SUM。百分比仅展示不除法，固定汇总不承诺任意切片重算；缺数值字段交最小Table依赖，保留指定组件。
- 固定条件逐组件，完整AND/OR，日期公开关键字/ExactDate毫秒、年季双边界；本人不用固定执行者，缺动态协议列缺口。
- integrated整体多选分组、enumerated拆选项，第二维度独立；多源同Base/表不同/数据不重复，不承诺自动去重。
- 切片器不代固定范围，真实作用/结果另验，创建不证明联动。

### 点名比率：先补依赖，再落实指定组件

必读 [指标口径](app-metric-recipes.md#比率类指标先定口径再落实指定组件)，保留原指标、完整分母与指定组件，不能用count替代。点名进度条时用 [progress](component-progress.md#点名进度条时保留组件与口径)，不因“完成率”改成 statistics。

### 当前访问者筛选

必读 [当前访问者](app-scope-contract.md#当前访问者筛选)，使用公开动态selector并独立回读。

### 从业务词到配置

必读 [业务词映射](app-metric-recipes.md#从业务词到配置)，记录对象、资格、计算与检查。

### 时间语义的最小操作配方

必读 [时间语义配方](app-time-recipes.md#时间语义的最小操作配方)，状态不替代时间边界。

### 范围覆盖与时间窗口

必读 [范围覆盖合同](app-scope-contract.md#范围覆盖与时间窗口)，枚举授权范围内旧/新消费者并逐源回读。

### App 比率验收

必读 [比率验收](app-metric-recipes.md#app-比率验收)，计算与展示分别验证。

### App 状态范围

状态筛选前读真实完整选项，点名值精确匹配：只看进行中仅该值，还没开始仅对应未开始值，多值保留集合不加待启动/暂停等近邻；无对应核映射/澄清，不选近义替代。

未点名具体值的未完成/未处理才按完整值域判谓词，证据证明不符才排，未知待核实不计确认数/分母。正列全部命中不只排单终态；点名真实待处理仍精确。逐受约束组件配置，标题/其它组件不抵扣。

## 清空与回读

清空主 filter 用 `--interaction-config '{"clear_fields":["filter"]}'`，对应目标类型公开 clearWhere；仅清主源，不清全部副源。不用 null、空条件、isNotEmpty 冒充清空。

标准图表的分组和整体排序可按下列入口分别清空；先读取目标完整配置，使用同一App/Page/widget ID，只提交本轮操作：

```bash
# column/bar等标准图：清整体排序；不把sort.type改成record或none
lark-cli base +app-block-update --app-token <app_token> --page-id <page_id> --block-id <widget_id> --interaction-config '{"clear_fields":["sort"]}' --as user
# pie/ring等标准图：清主分组；不换源、不新建同名图
lark-cli base +app-block-update --app-token <app_token> --page-id <page_id> --block-id <widget_id> --interaction-config '{"clear_fields":["groups"]}' --as user
```

block-get核分组无业务维度/整体sort已清及源/指标/filter/保留项；维度默认序非整体排序残留。list/view用自身group_by:[]/sort_by:[]，多源/特殊类型先核清空范围；拒绝保留缺口，不把clear_fields放data_config。

标准图可保留全部源/正确槽位、仅去目标filter提交完整data_sources；Node完整主源省略filter执行clear，其它顶层Patch省略data_sources保持。独立回读为准。

block-get核表/字段/聚合/范围/维度/格式，get-data用chart_token与独立记录/计算对账；配置/结果分证，请求回显不证明口径。
