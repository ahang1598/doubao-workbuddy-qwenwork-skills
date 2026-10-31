# 倒计时

## 对象与入口

复用 +dashboard-block-create（要求完整配置）和 +dashboard-block-update（接受局部配置）。`--type countdown` 是组件类型；data_config.type 是可切换的 fixed / field 模式。

公开字段用 camelCase（非 snake_case）：targetTime、aggregateType、additionalDatasources、tableName、countAll、groupBy、fieldName。CLI 不改字段名、枚举大小写，也不补默认值。

## 创建固定时间倒计时

targetTime 必填，为非负整数毫秒时间戳；0 和过去时间都允许。fixed 不接受 aggregateType、additionalDatasources，null 和空数组也不行。Base 至少要有一张表供底层渲染占位，该表不进公开配置。

创建传 `--type countdown --data-config '{"type":"fixed","targetTime":1798732800000}'`。

## 创建字段倒计时

日期字段提供目标时间；field 不接受 targetTime。

- aggregateType：必填；MIN 取最早日期，MAX 取最晚日期。
- additionalDatasources：必填，恰好一个数据源；其中 tableName 必填，为真实非空表名。
- countAll / series：二选一；countAll 只能为 true；series 为 1～20 项，每项必填 fieldName 和 rollup（SUM、MAX、MIN、AVERAGE）。
- groupBy：必填，恰好一个；fieldName 必须是日期、创建时间或修改时间字段。mode 可选 integrated / enumerated，省略为 integrated；sort 可选，其中 type 必填（group、value、view），order 可选（asc、desc）。
- filter：可选；conjunction 为 and / or，conditions 为 1～50 项，每项含 fieldName、operator 和操作符需要的 value；创建不接受 filter:null。

筛选操作符和值沿用普通图表的字段类型规则，但字段名键用 fieldName。CLI 校验结构；表名解析、字段类型、筛选值由后端判断。

完整示例（可存为文件后传 `--data-config @countdown.json`）：

```json
{"type":"field","aggregateType":"MIN","additionalDatasources":[{"tableName":"任务表","countAll":true,
 "groupBy":[{"fieldName":"截止时间"}],
 "filter":{"conjunction":"and","conditions":[{"fieldName":"状态","operator":"isNot","value":"已完成"}]}}]}
```

## 更新语义

### 同模式局部更新

- 省略 type 或传相同模式：沿用当前模式，按局部更新。
- fixed 只传 targetTime：保留其他配置；field 传 targetTime 会被拒绝。
- field 只传 aggregateType：保留数据源、日期字段、指标、筛选。
- 传 additionalDatasources：必须恰好一项，按该对象的字段合并；`[{}]` 不修改。
- 传 groupBy / series：数组整体替换；groupBy 项仍需 fieldName，省略 mode 用 integrated，省略 sort 不继承旧值。
- 同模式同表更新 filter：省略则保留；对象整体替换；null 清空；空 conditions 不表示清空。
- 切换指标方式：countAll:true 移除旧 series；非空 series 移除旧 countAll；两者同传、countAll:false 或空 series 都会被拒绝。

例：fixed 只改目标时间传 `'{"targetTime":1798732800000}'`；field 只清空筛选传 `'{"additionalDatasources":[{"filter":null}]}'`。

### 切换模式与数据源

- 切到 fixed：显式传 `{"type":"fixed","targetTime":...}`。
- 切到 field：显式传含 aggregateType 和唯一数据源的完整配置；不继承历史隐藏筛选。
- field 换表：传完整新数据源（tableName、唯一日期 groupBy、countAll:true 或非空 series）；可省略 type、aggregateType；省略新 filter 即不筛选。
- 只有解析后的表 ID 改变才算换表；传回同一表名仍按局部更新。

### 输入保留与提交约束

data_config:{} 不修改配置；省略 data_config 可只改 name 或 position。data_config 不能是 null、数组或其他非对象值。
CLI 原样保留补丁里的省略字段、空对象、null、0、false，由后端结合当前组件校验模式切换、换表完整性和字段引用。更新前先获取配置确认现状，只提交要改的字段。从获取结果里删掉 filter 再提交不能清空筛选，必须显式传 filter:null。

## 获取与写入响应

+dashboard-block-get 的 data.block.data_config 返回当前模式完整配置：fixed 含 type、targetTime；field 含 type、aggregateType、additionalDatasources。创建和更新也回读完整 block，分别附带 data.created:true、data.updated:true。
回读会归一化默认 mode、排序或筛选值，不一定与请求相同；清空后省略 filter。隐藏固定时间、占位数据源、units/title/animation 等未开放展示配置不属于公开 data_config。
