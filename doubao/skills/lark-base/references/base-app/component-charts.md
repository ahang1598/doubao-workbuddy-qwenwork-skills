---
name: app-component-charts
description: App 原生标准图表的选型、尺寸、展示方法和安全更新；创建或修改柱、条、折线等标准图表时读取。
---

# App 标准图表

柱状、条形、折线、面积、组合、饼、环、散点、漏斗、词云、雷达统一在本文件维护。数据源、聚合、筛选、排序与多源必读 [公共数据](app-data-common.md)；statistics/ranking/AI 按 [组件索引](app-component-selection.md) 加载各自文件。

## 原子尺寸

| 类型 | 默认W×H | 推荐W | 推荐H | 比例 |
| --- | --- | --- | --- | --- |
| 除漏斗外的标准图表 | 16×16 | 12～36 | 14～24 | 优先W≥H，避免过窄竖条 |
| 漏斗 funnel | 16×20 | 8～24 | 12～24 | 优先W≤H，不强行与横向图等宽 |

无覆盖时必须显式落实默认尺寸；组排版、首页模板和用户合法尺寸优先。标准图不默认宽高fill，不使用height auto；整行用根布局w表达。同行、主次比例和布局验收见 [页面布局](../../scenes/app-mode/layout.md)。

## 类型与展示差异

| CLI type | 业务表达与专属规则 |
| --- | --- |
| column | 柱状图/柱形图；纵向分类数值比较。stacked为none/stack/percentage，百分比堆叠只改视觉、不改变原值 |
| bar | 条形图/横向条形图；横向分类比较。stacked同上，TopN需求使用ranking |
| line | 连续趋势；line_style为line/smooth/ladder，新建默认smooth，已有未要求线型时保留 |
| area | 连续趋势或构成变化；stacked/line_style按要求，折线smooth默认不自动套面积图 |
| combo | 多度量保留多个series；combo_visual仅用于同一指标按Select/Stage选项切column/line/area/scatter，不能替代多个指标，不与comboLayout容器混用 |
| pie | 分类占比；pie_aggregate控制“汇总相同类别”，与group_by.mode独立；pie_stroke设置扇区描边色 |
| ring | 环心总数与占比；pie_total布尔控制环心总数，pie_aggregate=false取消相同类别汇总 |
| scatter | 按真实维度与数值指标表达关系，使用标准ChartDataConfig，不猜AI的xField/yField；样本不足不虚构点位 |
| funnel | 真实阶段维度及指标，核对阶段顺序；不为首页填高臆造转化关系 |
| wordCloud | 文本维度加count_all记录数，核对文本字段与频次；不替代TopN，不编关键词 |
| radar | 真实可比较维度与指标，radar_style为line/area/point；不拼量纲不兼容的指标 |

新建原生line且未指定线型时显式 `--display-config '{"line_style":"smooth"}'`。基础/普通直线、平滑、阶梯分别line/smooth/ladder；已有图未要求线型时省略并保留，此默认不适用于AI。

环形图“开启图表选项总数”仅 `--display-config '{"pie_total":true}'`，不新增statistics、不重绑数据、不重排；类别汇总开关也只改展示。

## 写前口径、写后逐项对账

- 按 [选型](app-component-selection.md) 逐项定Page/type/来源粒度/维度/度量/格式；分类与计量对象分清，count_all仅一行一目标，关联数量须真实数值，不用类别数/主表行数或series COUNT/COUNTA代理。
- 点名柱状固定column、条形固定bar，创建/重试保持，独立block-get核type；名称、数值或别页同型不抵扣。
- funnel核同一总体真实累计阶段/计数/顺序，互斥现态不等价；缺来源交最小依赖并blocked，不换流程改名。
- 比率按 [验收](app-metric-recipes.md#app-比率验收) 核分母/范围/尺度，真实比值1=100%后配精度，允许>100%，格式不代替除法。
- 报错查schema重试原口径，不数记录/换维度/漏图；逐ID配置、可取数实际值分验，创建成功/数量够不算通过。

可见分类/维度、度量含义、单位另需渲染证据；group_by/名称不证明可见，缺证据标未验证，不猜axis键。

## 同表两个累计数值转为漏斗阶段

仅同一总体/资格的两个可加总累计阶段（如触达/转化）适用，去重人数/互斥现态不套用；优先复用已验动态阶段表。funnel两series可能只返回首度量，两measures不证明两阶段；一次失败不判平台无能力，不换两卡。

需阶段表先核同Base最小结构/两维度记录授权，无授权/权限blocked、不扩既有事实表。必读 [公式/Lookup](../../scenes/field-formula-lookup.md) 与 [Lookup配置](../field-lookup-config.md) 及公式协议，核主字段/Number/范围/可加总性。本例活动事实、文本主字段活动名称、Number触达人数/转化人数，替换真实身份/名/ID。

where为已确认全集，真实主文本empty OR non_empty覆盖空/非空，不固化ID；有时间/状态等资格时两个Lookup同用完整真实资格替换恒真，不只筛非空/套别表状态。Lookup仅一层AND/OR，复杂组合用已验计算路径或blocked，不放宽。

1. 建表仅含阶段主字段，再创建两个动态 Lookup。`sum` 为 Lookup 小写枚举；图表 `SUM` 为大写枚举。`<阶段表id>` 使用建表真实返回的 ID。

```bash
lark-cli base +table-create --base-token '<base_token>' --name '转化阶段汇总' --fields '[{"name":"阶段","type":"text"}]' --as user
lark-cli base +field-create --base-token '<base_token>' --table-id '<阶段表id>' --i-have-read-guide --json '[{"name":"动态触达合计","type":"lookup","from":"活动事实","select":"触达人数","aggregate":"sum","where":{"logic":"or","conditions":[["活动名称","empty"],["活动名称","non_empty"]]}},{"name":"动态转化合计","type":"lookup","from":"活动事实","select":"转化人数","aggregate":"sum","where":{"logic":"or","conditions":[["活动名称","empty"],["活动名称","non_empty"]]}}]' --as user
```

用返回字段ID分别核Lookup，再单独建Formula；依赖与Formula不同批，不能假定即时解析。

```bash
lark-cli base +field-get --base-token '<base_token>' --table-id '<阶段表id>' --field-id '<触达Lookup字段id>' --as user
lark-cli base +field-get --base-token '<base_token>' --table-id '<阶段表id>' --field-id '<转化Lookup字段id>' --as user
lark-cli base +field-create --base-token '<base_token>' --table-id '<阶段表id>' --i-have-read-guide --json '{"name":"阶段数值","type":"formula","expression":"IF([阶段]=\"触达\",[动态触达合计],[动态转化合计])"}' --as user
```

2. 只写两个阶段维度，不向 Lookup/Formula 写业务数值；保持阶段集合恰为“触达 / 转化”，否则 Formula 的后分支不代表新增阶段。

```bash
lark-cli base +record-batch-create --base-token '<base_token>' --table-id '<阶段表id>' --json '{"create_records":[{"阶段":"触达"},{"阶段":"转化"}]}' --as user
```

3. field-get核Lookup/Formula定义、record-list核两行计算类型/值并与同资格事实对账，再绑定单指标+阶段维度。已有漏斗update保留ID，新建：

```bash
lark-cli base +app-block-create --app-token '<app_token>' --page-id '<page_id>' --name '触达到转化漏斗' --type funnel --data-config '{"base_token":"<base_token>","data_sources":[{"table_name":"转化阶段汇总","series":[{"field_name":"阶段数值","rollup":"SUM"}],"group_by":[{"field_name":"阶段","mode":"integrated","sort":{"type":"view","order":"asc"}}]}]}' --as user
lark-cli base +app-block-get --app-token '<app_token>' --page-id '<page_id>' --block-id '<widget_id>' --as user
lark-cli base +app-block-get-data --app-token '<app_token>' --base-token '<base_token>' --block-id '<chart_token>' --as user
```

view/asc为来源行序，不是人数降序，插入序不代替核验；get-data.main_data须两阶段/值/顺序正确，两measures、空或首阶段不通过。前端两层/顺序另验，缺渲染仅报数据层。

防再次累计：观看100/报名20须100/20，首层120失败；对照源、get-data、渲染区分计算/渲染异常。顺序错只修有证据配置；无公开累计控制则blocked，记录100/20≠120，不编isAccumulated、不把100改80，保存不算正确。

持续重算仅在授权诊断副本改/增样例验证，不改既有事实表；无授权记unknown。dry-run只检查请求，不验表解析/计算/重算/两层数据/渲染；授权、类型或计算缺口保留原漏斗义务，不填静态数/换组件。

## 趋势图先准备时间事实

布局前必读 [时间事实配方](app-time-recipes.md#趋势图先准备时间事实)：真实事件/观测、时间维度/粒度先落实再绑定，客户/人员/等级对比不算走势。新建依授权补依赖/Mock，既有局部守范围，缺源不勾完成。

## 数据与安全更新

create --type创建，update --type仅支持上表11标准图原位互转，其它type及全部sub_type不可改，不发未公开sub_type/删旧建新。换前记widget_id/chart_token/父级/矩形，换后独立回读身份/目标type/口径及未点名配置；仅提交type与点名字段，不重排。help缺type按 [恢复](app-commands.md#常见恢复) 保留版本/help及阻点。

展示变体用display_config对应组件正式方法，上表枚举不套其它组件，不因无sub_type退回默认；combo_visual选项映射column/line/area/scatter，pie_total/aggregate布尔、pie_stroke CSS色。

组合图按指标配置形态、左右轴和颜色时使用对象形式，例如
`--display-config '{"combo_visual":{"销售额":{"shape":"line","axis":"right","style":{"color":"#1A73E8"}}}}'`。
不要使用 `display_config.series` 或 `data_config.series[].type`。

第二group_by分类对比不替主横轴；stacked仅视觉，多series保留并列度量。趋势锁真实日期/粒度/升序及逐源资格/完整窗口/聚合，人员等只作第二维度。改名/维度/变体不等于换型，阻点按边界；指标/筛选按 [业务映射](app-metric-recipes.md#从业务词到配置)。

数字格式用 display_config：`{"format_percent":{"precision":1}}`、`{"format_currency":["人民币",1]}`、`{"format_number":{"separator":true,"precision":1}}`。格式只改变展示，不改变原值、统计或排序。多参数数组展开，完整规则见 [页面 API](app-page-api.md)。

仅点名槽位更新，标题/线型不重写源/指标；block-get核类型/口径/范围/分母/排序/展示，structure核矩形/模式，get-data核值；样式变动另确认数据/布局保持。

### 参数失败后的原型与排序保留

单表多指标combo用单源多series，不强加aggregate；报至少两源先修请求，不降line/换表，多源资格各自保留。

达人数降序用对应group_by.sort的value/desc，group按成员、reverse仅方向不等价；漏斗按阶段序/资格，不默认人数降序。实际取数/系列序交叉验，sort存在不算通过。
