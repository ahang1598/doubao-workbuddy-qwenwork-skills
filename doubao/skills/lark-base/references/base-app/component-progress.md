---
name: app-component-progress
description: App 进度图的默认尺寸、分子目标口径、日期模式与格式。
---

# 进度图 progress

默认16×8，推荐W8～24、H8～12，不默认fill/auto；模板、组排版和用户合法尺寸优先。表达当前/目标、实际/计划或分子/分母，“率”不能覆盖用户指定statistics。

## 点名进度条时保留组件与口径

用户说“用进度条盯回款完成率”，必须使用 `type=progress`、`shape=bar`，保留“回款完成率”的业务含义，不改成“回款率”指标卡。先核完成口径是已回款金额/应回款金额，还是已完成合同数/应完成合同数，再配置两侧真实来源、字段、聚合、资格与周期；金额和合同数不混算，不能平均逐笔金额比率或编固定目标。无法确认口径时列出缺口，不宣称已验证。

例如已确认按金额计算，合同回款表中的“已回款金额”和“应回款金额”均为数值、同一合同不重复计入，则数据配置为：

```json
{"base_token":"<base_token>","table_name":"合同回款表","current":{"mode":"field","field_name":"已回款金额","rollup":"SUM"},"target":{"mode":"field","field_name":"应回款金额","rollup":"SUM"},"shape":"bar","value_type":"number"}
```

这是已确认口径后的示例，不替代真实表字段与范围。独立 block-get 核 `type=progress`、`shape=bar`、current/target 的来源、聚合及完整条件；再分别验原值格式与完成率，实际页面应呈现条形进度。只看到百分比、标题或创建成功不算满足；真实零分母按产品结果报告。

## 数据与展示协议

顶层base_token/table_name和current/target；mode=value/count_all/field，target.table_name可另表。shape为bar/semi_ring/circle，value_type为number/date；百分比和货币使用展示格式，不添加percent/currency枚举。分别核实两侧来源、范围、单位、周期和聚合，通常相同rollup但以业务为准；两侧筛选不要求相同。百分比30%原值0.3，货币币种一致。

```json
{"base_token":"<base_token>","table_name":"任务","current":{"mode":"field","field_name":"已完成","rollup":"SUM"},"target":{"mode":"value","value":100},"shape":"bar","value_type":"number"}
```

新建/改口径按原值量纲显式选择 [数字格式](component-charts.md)，分别回读原值格式和完成率。示例：current=20、target=100 且原值是数量时，原值显示 20/100，完成率显示 20%；原值本身为比例时才使用百分比原值格式。仅改其它属性保留原格式。current/target对象整体替换，改某侧保留该侧必要模式/字段/聚合，另一侧省略保留。分别核对view_name或filter，不丢目标范围。

日期模式用value_type=date+date_option，不伪造数值模拟日期；格式YYYY-MM-DD/ YYYY/MM/DD/ MM-DD/ MM/DD/YYYY/ DD/MM/YYYY。当前CLI仍要求current/target，若不能合法适配真实日期协议就报告缺口。独立回读两侧实际口径、格式、模式及数值。

## 修复计数被显示成百分比的正例

报名完成进度真实current=3、target=10，完成率30%正确，但原值显示成300%/1000%时，只修原值展示格式：

```bash
lark-cli base +app-block-update --app-token <app_token> --page-id <page_id> --block-id <progress_id> --display-config '{"format_number":{"separator":true,"precision":0}}' --as user
```

独立block-get核数量格式及原current/target来源、字段、聚合、筛选均保留，再对照真实结果与页面确认3/10和30%。不把3改成0.03、不把目标改成1，也不因进度总百分比正确就忽略原值错误。金额原值可用公开format_currency：已回款200、合同金额1000显示200/1000或货币格式，完成率20%；原值本身为比例时才用format_percent。仅改名称或其它属性时保留原格式，不主动套本例。
