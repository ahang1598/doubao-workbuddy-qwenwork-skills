# Base data analysis SOP

Base 数据查询与分析任务的执行契约。覆盖记录读取、筛选、排序、Top/Bottom N、聚合统计、分组聚合、多表关联、临时分析和查询后写入前的目标定位。

本文只管查询选路和正确性边界；具体操作前先读真实结构和现状，复杂 JSON 再跳到 reference：

- `+data-query`: entry guide [lark-base-data-query-guide.md](lark-base-data-query-guide.md), full DSL SSOT [lark-base-data-query.md](lark-base-data-query.md)
- 视图筛选: [lark-base-view-set-filter.md](lark-base-view-set-filter.md)
- 记录读取: `+record-list` / `+record-search` / `+record-get`，先确认字段 ID、字段名、分页和投影范围

## 0. Hard Rules

- 全局问题不能用默认 `+record-list --limit N` 片面地回答。
- `jq` / shell / 本地代码是在个人电脑或当前运行环境中处理已返回数据，只适合小范围结果；超过 200 行默认不推荐本地统计、排序或求极值，应改用 Base 云端查询服务的 filter/sort/aggregate。
- “最高、最低、最新、最早、Top、Bottom、总数、全部、异常、最大、最小、最多、最少、优先级最高”等全局语义，必须在 Base 云端查询服务中完成筛选、排序或聚合。
- 一次性原始记录查询优先用 `+record-list` / `+record-search` 的 filter/sort；聚合分析优先用 `+data-query`。
- `+record-search` 用于关键词检索字段的展示文本；金额、状态、日期、空值、关联等结构化条件继续用 `--filter-json` 表达。
- 不要依赖已有视图，除非用户明确指定该视图，或你已读取并验证其 filter/sort/projection 符合当前问题。
- 已有 Base 的分析默认只读；新建 Base、表、字段、视图、dashboard 或修改记录都需要用户明确要求。
- 极值、字段存在或常见业务习惯只能触发复核，不能自行排除记录、改变分母或缩窄主指标。缩窄口径必须来自用户明确要求、用户指定且已核验的任务范围或 View、字段公式或已确认的业务定义。
- 授权不足时保留原始口径为主结论，并把疑点和敏感性结果分开报告。
- 交付输出必须使用用户可读的真实字段值；内部 ID、`record_id`、关联记录 ID、open_id、编码字段只可作为连接键或定位键，不能替代最终输出，除非用户明确要求输出这些键值。
- 每次读取必须做最小投影，并包含后续解释、回查或写入需要的业务 key。
- 分组、计数、求和、均值、TopN、占比、对比谁更多/更高等结构化结论，必须由 `+data-query` 或可复核的程序化聚合产生；不要在思考或回复里手工数行、手工累加，也不要从自然语言预览里估算。
- 派生比率、单位值或加权均值在计算前先固定统计粒度、分子、分母和权重，并在输出中标明口径。`sum(分子) / sum(分母)` 表示总体加权结果，`avg(分子_i / 分母_i)` 表示统计单元等权平均。用户明确询问这类指标且存在多种合理权重，或开放式对比已在同一统计粒度下把可形成业务含义明确的比率/单位值的分子和分母都作为主要维度时，默认并列给出两种结果；用户表述、字段公式或已确认业务定义指定主口径时，将其作为主结果，另一口径仍具业务含义时再标为敏感性对照。不得省略按上述规则应并列或对照且会实质影响数值或结论的口径，也不得在最终输出中静默切换；只有数字字段存在但比率语义未确认时不自行派生。
- 不要静默剔除疑似异常值或自行改变样本范围。默认结论使用全量符合条件的数据；如怀疑数据异常，只能额外给“剔除疑似异常”的对照口径，并说明剔除依据和两套结果差异。
- 最终答案里的每个数字都要有证据：包括合计、计数、占比、排名附带指标和“其中 N 条/人/项”等解读性数字。数字必须来自本次查询返回，或能从本次已返回明细逐项复算；无支撑的数字不要写入。

### 字段充分性门禁

筛选、统计或创建分析视图前，先把用户目标改写为可验证的**业务谓词**，再判断现有字段是否足以证明它。阶段状态、局部状态、流程中间值或语义相邻字段不能直接证明最终业务状态。

1. 明确目标谓词，例如“待收余额 > 0”“实际归还时间为空”“订单尚未完成”。
2. 用 `+field-list` / `+field-get` 和完整记录读取确认候选字段的定义、完整值域及组合关系。
3. 为完整候选值域建立 `值 | Include / Exclude / Unknown | 字段证据` 对账；只有字段证据能直接证明不满足目标的值才可 `Exclude`，无法证明的值必须标记 `Unknown`。
4. `Unknown` 不能静默丢弃：字段不足但用户已明确给出业务关系时，创建可复核的源字段或派生字段；关系未明确时先澄清；无法补齐时保留全部候选并分组展示差异。
5. 写入后分别复算 Include、Exclude 和 Unknown 的子类数量，并与持久视图和最终回答核对；任一子类遗漏或口径不一致时不得交付。

Few-shot：用户说“定金收一部分的和一分没付的都还没付清”，现有字段只有 `定金支付状态=已支付/未支付`。`已支付`只是**阶段状态**，不能证明`全款已结清`。已知定金只占部分时，应同时保留“未支付定金”和“已支付定金待尾款”，可新增“欠款类型/待收金额”字段后在一个视图分组，或创建两个互补视图；不得只筛 `定金支付状态=未支付`。若定金比例、总额或尾款是否结清并不明确，先补充总金额/已收金额/尾款状态或向用户澄清，不得猜算待收金额。

## 查询、产物与回答一致性

统计、汇总、排名、TopN 或图表任务必须维护一份可复核的计算口径：数据源表、过滤范围、结果粒度、聚合字段、聚合函数和确定性查询结果。不能用原始记录的分组、排序或预览顺序冒充分组聚合结果。

当同一任务还要创建 Dashboard、汇总表、视图或其他物化结果时：

1. 先用 `+data-query` 或可复核程序化计算得到目标结果。
2. 用对应读取命令取得物化产物的实际数据；Dashboard 使用 `+dashboard-block-get-data`，结果表或视图使用记录读取。
3. 将最终回答中的全部数值与确定性查询和物化产物逐项比较。
4. 查询结果、物化产物和最终回答必须使用相同的 source、range、grain 和 measure。任意两者不一致时不得交付，先定向修复并复验；仍不一致则明确报告未完成。

搭建或修改 Base 时，用户要求分组、排序、排名、汇总或“最后这样看”，就已经明确要求物化，不需要再出现“创建视图”四个字。先确定交付形态：

- 要在原始记录上持续分组、筛选或排序：创建持久 View，并回读对应 `group`、`filter`、`sort`。
- 要展示聚合后的分组值、排名或图形：创建 Dashboard 或汇总表，并回读计算数据。
- 同一请求既要求建表又要求上述展示结构时，`+data-query` 只是计算与验收步骤，查询输出不能替代持久产物；最终答复中的 Markdown 表格也不能替代。
- 只有纯查询任务，且用户没有要求改造 Base、长期查看或“最后这样看”时，才只返回查询结果。

## 1. Intent -> Tool Path

| 用户意图 | 首选路径 | 关键规则 |
| --- | --- | --- |
| 看几条、预览、示例 | `+record-list --limit N --field-id ...` | 保持局部语义；不要推广为全局结论 |
| 已知 `record_id` | `+record-get` | 直接读取；不要 search/list 反查 |
| 明确关键词 | `+record-search --keyword ... --search-field ... --field-id ...` | 必须显式指定 `--search-field`；可叠加 `--filter-json` |
| 按条件找原始记录 | `+record-list --filter-json ...` | `filter-json` 与视图筛选结构一致，支持文本、数字、日期、选项、人员、群组、关联等值 |
| 排序 / TopN 原始记录 | `+record-list --filter-json ... --sort-json ... --limit N` | 最高/最新用 `desc:true`，最低/最早用 `desc:false`；数组顺序表达优先级；最多 10 个排序条件 |
| 聚合 / 分组 / 分组排序 | `+data-query` | 使用 filters/dimensions/measures/sort/limit |
| 聚合后输出逐条记录 | `+data-query` 得到业务 key 或候选字段组合 -> `+record-list --filter-json` / `+record-get` 回查 | `+data-query` 维度行按字段组合去重且不返回 `record_id` |
| 多表 / 多跳关联 | 以候选数最小的事实表为驱动表，沿业务 key 或 link `record_id` 逐跳回查 | 读出 link 单元格里的关联 `record_id` 后，到被关联表批量 `+record-get` 展示字段 |
| 查询后写入 / 视图化 | 先用本 SOP 得到可复核的目标记录 id 集合 | 再进入记录写入或视图配置；高价值可复用查询可沉淀为持久视图 |

## 2. Execution Patterns

### 2.1 结构化原始记录与 TopN

使用 `+record-list` 的 filter/sort 路径：

1. `+field-list` 确认筛选字段、排序字段、展示字段、业务 key。
2. 筛选只用 `--filter-json` 或 `--filter-json @file`。
3. 排序用 `--sort-json`。
4. `--field-id` 做最小投影，`--limit` 控制返回数量。

Example: string/number 条件 + TopN：

```bash
lark-cli base +record-list \
  --base-token <base_token> \
  --table-id <table_id> \
  --filter-json '{"logic":"and","conditions":[["Title","==","Launch plan"],["Score",">=",80]]}' \
  --sort-json '[{"field":"Updated","desc":true}]' \
  --field-id Name \
  --field-id Title \
  --field-id Score \
  --limit 20
```

Example: 复杂筛选从文件读取：

```bash
lark-cli base +record-list \
  --base-token <base_token> \
  --table-id <table_id> \
  --filter-json @filter.json \
  --sort-json '[{"field":"Priority","desc":true}]' \
  --field-id Name \
  --field-id Tags \
  --limit 50
```

`filter-json` 与视图筛选结构一致。下面只列常用 fewshot；字段类型、operator、value 形状拿不准，或需要人员、群组、关联、空值、地理位置、formula / lookup 等完整筛选时，先读 [lark-base-view-set-filter.md](lark-base-view-set-filter.md)，再把同样的 filter JSON 传给 `--filter-json`。

文本 `==`：字段值等于目标文本。
```json
{"logic":"and","conditions":[["Title","==","Launch plan"]]}
```

文本包含 / like：文本字段包含目标片段；operator 写 `intersects`。
```json
{"logic":"and","conditions":[["Title","intersects","urgent"]]}
```

数字 `==`：字段值等于目标数字。
```json
{"logic":"and","conditions":[["Score","==",95]]}
```

日期 `==`：字段值等于目标日期；datetime / created_at / updated_at 用 `ExactDate(...)`。
```json
{"logic":"and","conditions":[["Due Date","==","ExactDate(2026-06-02)"]]}
```

选项 `==`：字段值匹配单个选项；选项值使用选项名数组，单个选项也写数组。
```json
{"logic":"and","conditions":[["Priority","==",["P0"]]]}
```

选项 `intersects`：字段值与给定选项集合有交集，常用于多选或“命中任一选项”。
```json
{"logic":"and","conditions":[["Tags","intersects",["P0","Blocked"]]]}
```

`--sort-json` 传排序数组，数组顺序就是优先级，`desc:true` 为降序，`desc:false` 为升序，最多 10 个排序条件。

### 2.2 关键词检索后叠加结构化条件

使用 `+record-search` 做关键词命中，结构化条件仍用 `--filter-json` 下推：

```bash
lark-cli base +record-search \
  --base-token <base_token> \
  --table-id <table_id> \
  --keyword Alice \
  --search-field Name \
  --filter-json '{"logic":"and","conditions":[["Status","!=","Done"]]}' \
  --sort-json '[{"field":"Updated","desc":true}]' \
  --field-id Name \
  --field-id Status \
  --limit 20
```

不要把 `+record-search` 当成金额、状态、日期、空值、关联字段的结构化筛选入口；这些条件继续写成 `--filter-json`。

### 2.3 聚合分析与 TopN

使用 `+data-query`：

- 让 Base 云端查询服务完成 filters、dimensions、measures、sort、pagination.limit。
- `pagination.limit` 是 Base 云端查询服务中的结果限制，不是本地分页扫描。
- 常用聚合 fewshot 先读 [lark-base-data-query-guide.md](lark-base-data-query-guide.md)；字段类型、日期 value、DSL shape 以 [lark-base-data-query.md](lark-base-data-query.md) 为准。
- `+data-query` 可返回聚合结果或维度字段行；维度字段行按字段组合去重且不返回 `record_id`，不能当逐条原始记录结果使用。
- 如果 `+data-query` 返回 `ok=true` 但某个聚合 measure 为 null，先按 DSL SSOT 的 null measure 恢复顺序确认字段类型和聚合兼容性；确认不支持云端聚合后，再做一次最小投影的 `+record-list` 分页导出并本地复算。
- 需要输出逐条记录、记录定位或完整行级字段时，先用 `+data-query` 得到业务 key、分组值或候选字段组合，再用 `+record-list --filter-json` / `+record-get` 回查。

Example: 分组计数：

```bash
lark-cli base +data-query \
  --base-token <base_token> \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"Status","alias":"status"}],"measures":[{"field_name":"Status","aggregation":"count","alias":"count"}],"shaper":{"format":"flat"}}'
```

Example: 过滤后汇总并取 TopN：

```bash
lark-cli base +data-query \
  --base-token <base_token> \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"Owner","alias":"owner"}],"measures":[{"field_name":"Amount","aggregation":"sum","alias":"total_amount"}],"filters":{"type":1,"conjunction":"and","conditions":[{"field_name":"Status","operator":"is","value":["Done"]}]},"sort":[{"field_name":"total_amount","order":"desc"}],"pagination":{"limit":10},"shaper":{"format":"flat"}}'
```

### 2.4 大表去重、跨表匹配与分组比例对比

当任务需要“按业务主键去重后再分组”“判断一张表的记录在另一张表是否有匹配”“分组内满足条件的记录占比”“两个分组之间的比例对比与差值排序”这类复合统计时，先拆成可复核的中间集合，避免反复拉取多张大表：

1. 先读字段结构，只保留后续计算必需的 key、分组字段、状态字段和数值字段；不要读取备注、描述、附件等无关大字段。
2. 能下推到 Base 的过滤、去重、分组、计数、求和、排序和 TopN，优先用 `+data-query` 一次完成。
3. `+data-query` 无法直接表达“按 key 保留最高/最新一条”、“另一张表是否存在匹配记录”，或因字段类型不兼容导致目标 measure 为 null 时，再用 `+record-list` 分页读取精简投影到本地复算；每张大表只扫描一次，后续复用本地 key 集合，不要为了每个分组重复查全表。
4. 跨表存在性比例用同一业务 key 建集合：先得到分母集合，再得到满足条件的分子 key 集合，最后按分组求交集计数和比例。输出前报告分母、分子、比例和差值的口径。
5. 若需要找差值最大或指标最突出的分组，先算出全部分组的分母和分子，再统一排序；不要只比较样例分组或前几页。

### 2.5 视图化与复用

一次性查询先用 `+record-list` / `+record-search` 的 filter/sort 验证。需要用户长期打开、共享或复用时，再把同一套 filter/sort 沉淀为视图。

Example: 将已验证的筛选排序写入视图：

```bash
lark-cli base +view-set-filter \
  --base-token <base_token> \
  --table-id <table_id> \
  --view-id <view_id> \
  --json @filter.json

lark-cli base +view-set-sort \
  --base-token <base_token> \
  --table-id <table_id> \
  --view-id <view_id> \
  --json '{"sort_config":[{"field":"Priority","desc":true}]}'
```

手动配置和视图配置的优先级：

1. `--filter-json` 覆盖 `--view-id` 保存的 view filter JSON。
2. `--sort-json` 覆盖 `--view-id` 保存的 view sort config。
3. 没有手动 filter/sort 时，`--view-id` 使用视图自身保存的 filter/sort。

### 2.6 关系查询与回查

- link 单元格通常是关联表 `record_id` 数组，不是用户可读内容，只是连接键。
- 先用 `+field-list` 确认 link 字段的 `link_table`、业务唯一键和展示字段。
- 从驱动表拿到候选记录后，用关联 `record_id` 到关联表 `+record-get` 批量读取记录内容。
- 多跳关系逐跳建立 `record_id/key -> 用户可读字段` 映射；最终用户可读的信息。

禁止：

- 把 link `record_id` 当最终输出。
- 用 `+record-search` 搜 link `record_id`。
- 基于 ID、自增编号、link 值做语义猜测；禁止依赖字段先验、样本记忆补全交付输出。

## 3. Range & Pagination Contract

- `+record-list` 默认页、固定 `--limit`、本地 `jq`、shell 管道、手工浏览输出，都只覆盖已读取范围；单页 `--limit` 最大为 200，写 500 会失败。
- `has_more=true` 或返回行数等于 page size，都表示可能还有未读取数据；`+record-list --format json` 响应没有 page_token / next_page_token，翻页只用 `--offset`。
- 对全局问题，只有 Base 云端查询服务已经通过 filter/sort/aggregate 收敛目标范围，或 `+data-query` 已在云端完成聚合、排序和限制时，才可以用有限返回形成结论。
- 必须全量导出时，串行调用 `+record-list --format json --limit 200 --offset <n>`；每页用 `data.fields` 建列索引读取 `data.data` 行数组，`offset += len(data.data)`，直到 `data.has_more=false`。不要并发调用 `+record-list`。

## 4. Final Answer Check

形成交付输出前必须能确认：

- 问题范围是局部样例、单点定位、全局原始记录、聚合分析、多表关联，还是查询后写入。
- 筛选、排序、聚合是否发生在 Base 云端查询服务中，而不是本地 `jq` / shell 中。
- 如果使用 `jq` / shell，本地输入是否是 200 行以内的小范围结果；超过 200 行是否已改用 Base 云端查询服务查询。
- 如果使用 `+record-list` / `+record-search`，是否处理了 `has_more`，且投影包含业务 key 和解释字段。
- 如果涉及关系查询，是否按 `record_id` 或业务 key 精确回查，交付输出是否来自关联表真实字段。
- 交付输出能追溯到表、字段、筛选条件、排序/聚合条件和连接键。
- 对比分析的数值是否来自同一套可复核的聚合口径；不要混用“应收/已收/总额”等不同业务口径。字段语义不足时先声明限制或澄清，不要自行补齐缺失业务含义。
- 交付输出中出现的每个数字是否都能对应到本次查询返回行，或由已返回明细明确复算得出。合计值要在输出前按明细逐项复算一次；分组内二次筛选数量、占比或“其中 N 项”要追加 `+data-query` 分组计数，或用 `+record-list --filter-json` 精确过滤后计数，不得从已有聚合结果猜测或凭印象补充。
- 主结论数字和分析解读数字使用同一证据标准；如果某个解释性数字没有查询或复算支撑，改写为不含该数字的定性表述，或继续查询后再输出。

任一项无法确认时，继续查询或明确说明只能得到局部结论。
