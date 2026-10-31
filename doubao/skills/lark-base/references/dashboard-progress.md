# 进度图

## 对象与入口

使用 +dashboard-block-create（提交完整配置）、+dashboard-block-update（只提交变化字段）、+dashboard-block-get（返回完整生效配置）。外层 type 是 progress；data_config.progress.type 是 value 或 date。纯自定义的数值或日期模式也要求 Base 至少有一张表，但不填顶层 table_name。

## 创建数值进度

先用 +table-list、+field-list 确认表名和字段名。current、target 都必填，两侧可以引用不同表和不同筛选，每侧取一种来源：

- 自定义数值：`{"type":"custom","value":100}`，允许有限的 0、负数和小数。
- 字段来源：`{"type":"field","table_name":"订单表"}` 再加 `"count_all":true`（记录数）或 `"series":[{"field_name":"金额","rollup":"SUM"}]`（字段聚合）。

每侧 count_all:true 与 series 二选一；series 恰好一项，rollup 只能是 SUM、MAX、MIN、AVERAGE。记录数不用字段 COUNTA。
field 来源可带 filter，按 [通用筛选规则](dashboard-filter-conditions.md) 写：conjunction 为 and / or，conditions 1～50 项，每个值数组最多 200 项；不支持嵌套筛选、分组、视图范围和额外数据源。创建时不筛选就省略 filter，不接受 `filter:null`。

创建示例：`--type progress --data-config '{"progress":{"type":"value","current":{"type":"field","table_name":"订单表","count_all":true,"filter":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":["已完成"]}]}},"target":{"type":"custom","value":100}}}'`。

## 创建日期进度

- current：`{"type":"custom","value":1790000000000}`，或 `{"type":"relative","value":"today"}`（相对值 today / yesterday）。
- target：`{"type":"custom","range":[1789000000000,1791000000000]}`，或 relative 的 month / quarter / year。
- dateFormat：可省略，服务端默认 YYYY-MM-DD；枚举为 YYYY-MM-DD、YYYY/MM/DD、MM-DD、MM/DD/YYYY、DD/MM/YYYY。

两侧可混用相对和自定义时间。时间戳是安全整数毫秒值；range 必须有两个端点且起点小于终点。相对日期保持相对语义。日期进度不支持 field 来源；数值进度聚合日期字段也不会变成日期模式。

## 形状、格式与颜色

数据仍放在 `data_config.progress`，样式放在 `data_config.viewModel.rules`，不增加 `style`；通用合并与清空规则见 [自定义样式](dashboard-style.md)。数值、日期模式都支持 `shape=bar|semiRing|circle`，服务端同步对应形态，不要求同时写 `chartKind`。

一次创建半环数值进度图，并分别设置数值精度和进度百分比精度：

```bash
lark-cli base +dashboard-block-create \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --name '半环进度' --type progress --as user \
  --data-config '{"progress":{"type":"value","current":{"type":"custom","value":37.125},"target":{"type":"custom","value":100}},"viewModel":{"rules":{"progress":{"shape":"semiRing","color":"#3366FF","opacity":0.4},"formatInfo":{"formatName":"digital","precision":2,"percentPrecision":1}}}}'
```

`precision` 控制当前／目标数值，`percentPrecision` 控制进度百分比，两者分开设置，均为 0–9 的整数；透明度取 0–1。上例数值为 37.13，进度为 37.1%。格式名支持 `digital/digital_without_separator/scientific/percentage_rounded/cyn_rounded/dollar_rounded`；`percentage_rounded` 把数值本身按百分比显示，见下节，且不能同时指定数值单位。

以下是 `+dashboard-block-update --data-config` 的纯样式补丁，命令还需提供 Base、Dashboard、Block ID 及 `--as user`：

| 场景 | 补丁 |
|---|---|
| 修改形状 | `{"viewModel":{"rules":{"progress":{"shape":"circle"}}}}` |
| 修改百分比精度 | `{"viewModel":{"rules":{"formatInfo":{"percentPrecision":3}}}}` |
| 当前值／目标值文字颜色 | `{"viewModel":{"rules":{"progress":{"curFontColor":"#3366FF","curFontOpacity":0.6,"targetFontColor":"#34C759","targetFontOpacity":1}}}}` |
| 百分比文字颜色 | `{"viewModel":{"rules":{"progress":{"percentFontColor":"#F54A45","percentFontOpacity":1}}}}` |
| 日期范围文字颜色 | `{"viewModel":{"rules":{"progress":{"rangeFontColor":"#8E44AD","rangeFontOpacity":0.6}}}}` |

按进度百分比配置色区间：

```json
{"viewModel":{"rules":{"progress":{"isAreaColor":true,"areaType":"percent","colors":[{"range":[0,30],"color":"#F54A45","opacity":1},{"range":[30,70],"color":"#FFC60A","opacity":1},{"range":[70,100],"color":"#34C759","opacity":1}]}}}}
```

百分比区间用 0–100，不归一到 0–1；`opacity` 用 0–1。数值模式也可用 `areaType:number` 按当前绝对值匹配，例如 current=75、target=200 时用范围 `[50,100]`，而不是按 37.5% 匹配。每段起点必须小于终点，区间须有序且不重叠；`colors` 更新时整体替换。切回单色可传 `isAreaColor:false` 并设置 `color/opacity`。

日期进度用原有 `progress.type=date/current/target/dateFormat` 配置数据，也可设置形状、单色／百分比色区间和文字颜色；不支持数值格式、数值单位及 `areaType:number`。

### 百分比格式与进度百分比不是同一项

先确认用户要改哪种显示，不为满足回执关键词而改变业务单位：

| 用户要求 | 配置位置与含义 |
|---|---|
| 进度完成率保留一位小数 | `viewModel.rules.formatInfo.percentPrecision:1`；只控制 current / target 得到的进度百分比精度 |
| 当前值／目标值本身显示为百分比 | `viewModel.rules.formatInfo.formatName:"percentage_rounded"`，配合 `precision` 控制数值小数位；输入仍为比例小数 |
| 当前值／目标值是金额、数量 | 保留对应数值格式；不能仅为显示完成率而改为百分比格式 |

例如 current=37.125、target=100，`formatName:"digital",precision:2,percentPrecision:1` 表示数值 37.13／100.00、进度 37.1%；current=0.37125、target=1 且用户要百分比数值时，`formatName:"percentage_rounded",precision:2,percentPrecision:1` 表示数值 37.13%／100.00%、进度 37.1%。不要把比例乘以 100 后再套百分比格式。

只调整完成率精度的最小补丁：

```json
{"viewModel":{"rules":{"formatInfo":{"percentPrecision":1}}}}
```

明确要求当前值／目标值显示为百分比时的补丁：

```json
{"viewModel":{"rules":{"formatInfo":{"formatName":"percentage_rounded","precision":1,"percentPrecision":1}}}}
```

独立 `+dashboard-block-get` 回读 `data_config.viewModel.rules.formatInfo`，分别核对格式、数值精度与进度百分比精度，并核对 current／target 的来源与单位。保留返回 JSON 作为配置证据；需要实际显示效果时另验页面，配置成功不等于渲染已验证。日期模式不写这些数值格式字段。

## 局部更新

更新没有外层 `--type`。CLI 不先获取再合并，也不补默认值；服务端根据已有组件判断省略的模式、来源和表。

- target 当前为自定义数值时，改目标值传 `{"progress":{"target":{"value":200000}}}`。
- current 为 field 来源时，传 `{"progress":{"current":{"filter":null}}}` 清空其筛选，保留指标和 target。
- 传新的 current.series 会整体替换并移除 count_all；传 current.count_all:true 会移除 series；两者都保留同表筛选。
- 日期模式下改格式传 `{"progress":{"dateFormat":"YYYY/MM/DD"}}`，两侧保留；日期 target 为 relative 时改范围传 `{"progress":{"target":{"value":"quarter"}}}`。
- `{}`、`{"progress":{}}`、`{"progress":{"current":{}}}` 不改变配置。

### 合并、替换与清空

同来源、同表时：未传 filter 保留原值，传对象整体替换，传 null 清空；即使提交完整对象，省略 filter 也不表示清空。conditions、series、range 都整体替换；空条件和只有一个端点的范围无效。不传 dateFormat 保留原格式，恢复默认须显式传 YYYY-MM-DD。除清空筛选外，不用 null 删除必填配置；未知字段和跨模式字段由服务端拒绝。

## 切换来源、表和模式

切换时另一侧保留，须显式提交：

- 某侧 field → custom：传 `{"type":"custom","value":200}`。
- 某侧 custom → field：传 type:"field"、表名、count_all 或完整 series；不启用隐藏的旧查询。
- 某侧换表：传新表名和新统计方式；未传筛选则清除该侧旧筛选。
- 日期某侧 relative ↔ custom：传新 type 和完整 value 或 range；dateFormat 保留。
- 整体 value ↔ date：传 progress.type 和完整 current、target；展示配置保留，切到 date 时省略格式用默认值。

不根据传入字段隐式切换来源；传相同类型或同一表仍按局部更新。两侧共享表时，改一侧的表不影响另一侧。count_all:false、空 series、两种指标同传都无效。

## 获取与返回结构

用 +dashboard-block-get 读 data.block.data_config.progress；创建和更新的响应也返回回读结果。清空后省略 filter；相对日期不展开为固定日期；隐藏查询和固定值不返回。默认日期格式和筛选值可能被归一化，不一定与输入相同。这里只读配置，不算进度百分比。

## 输入文件与校验选项

创建和更新都支持 `--data-config @config.json`。`--dry-run` 展示实际请求体；`--no-validate` 跳过本地语义校验，但仍检查 JSON 对象语法，服务端也仍会校验。进度图只在 Dashboard 支持，不开放为 BaseApp 页面组件。
